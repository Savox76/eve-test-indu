use serde::{Deserialize, Serialize};
use std::io::{BufRead, BufReader, Write};
use std::process::{Child, Command, Stdio};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{mpsc, Mutex};
use std::thread;
use std::time::{Duration, Instant};
use tauri::{AppHandle, Manager, RunEvent, State};

const SIDECAR_PROTOCOL_VERSION: u8 = 1;
const DATABASE_LOCATION: &str = "data/foundry.sqlite3";
const SIDECAR_READY_TIMEOUT: Duration = Duration::from_secs(25);
const SIDECAR_SHUTDOWN_TIMEOUT: Duration = Duration::from_secs(4);
const WINDOWS_CREATE_NO_WINDOW: u32 = 0x0800_0000;

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
struct RuntimeSnapshot {
    state: &'static str,
    version: &'static str,
    desktop_shell: bool,
    single_instance: bool,
    sidecar: &'static str,
    database: &'static str,
    database_location: &'static str,
    schema_version: Option<u32>,
    error_code: Option<&'static str>,
}

impl RuntimeSnapshot {
    fn starting() -> Self {
        Self {
            state: "ready",
            version: env!("CARGO_PKG_VERSION"),
            desktop_shell: true,
            single_instance: true,
            sidecar: "starting",
            database: "starting",
            database_location: DATABASE_LOCATION,
            schema_version: None,
            error_code: None,
        }
    }

    fn ready(schema_version: u32) -> Self {
        Self {
            sidecar: "ready",
            database: "ready",
            schema_version: Some(schema_version),
            ..Self::starting()
        }
    }

    fn failed(error_code: &'static str) -> Self {
        Self {
            sidecar: "error",
            database: "error",
            error_code: Some(error_code),
            ..Self::starting()
        }
    }
}

struct SidecarProcess {
    child: Child,
    _session_token: String,
    _port: u16,
}

struct RuntimeState {
    snapshot: Mutex<RuntimeSnapshot>,
    sidecar: Mutex<Option<SidecarProcess>>,
    shutting_down: AtomicBool,
}

impl RuntimeState {
    fn new() -> Self {
        Self {
            snapshot: Mutex::new(RuntimeSnapshot::starting()),
            sidecar: Mutex::new(None),
            shutting_down: AtomicBool::new(false),
        }
    }

    fn set_snapshot(&self, snapshot: RuntimeSnapshot) {
        *self.snapshot.lock().unwrap_or_else(|error| error.into_inner()) = snapshot;
    }
}

#[derive(Deserialize)]
struct SidecarReady {
    event: String,
    protocol: u8,
    host: String,
    port: u16,
    database: SidecarDatabaseReady,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
struct SidecarDatabaseReady {
    state: String,
    schema_version: u32,
    location: String,
}

fn session_token() -> Result<String, &'static str> {
    let mut random_bytes = [0_u8; 32];
    getrandom::fill(&mut random_bytes).map_err(|_| "session-token-failed")?;
    Ok(random_bytes
        .iter()
        .map(|byte| format!("{byte:02x}"))
        .collect())
}

fn terminate_child(child: &mut Child) {
    let _ = child.kill();
    let _ = child.wait();
}

fn launch_sidecar(app: &AppHandle) -> Result<(SidecarProcess, u32), &'static str> {
    let program_directory = std::env::current_exe()
        .map_err(|_| "program-directory-unavailable")?
        .parent()
        .ok_or("program-directory-unavailable")?
        .to_path_buf();
    let sidecar_path = app
        .path()
        .resource_dir()
        .map_err(|_| "sidecar-resource-unavailable")?
        .join("foundry-sidecar.exe");
    if !sidecar_path.is_file() {
        return Err("sidecar-not-found");
    }

    let token = session_token()?;
    let mut command = Command::new(sidecar_path);
    command
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::null());
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        command.creation_flags(WINDOWS_CREATE_NO_WINDOW);
    }

    let mut child = command.spawn().map_err(|_| "sidecar-spawn-failed")?;
    let result = (|| {
        let startup_message = serde_json::json!({
            "protocol": SIDECAR_PROTOCOL_VERSION,
            "sessionToken": token.clone(),
            "programDirectory": program_directory,
        });
        let child_stdin = child.stdin.as_mut().ok_or("sidecar-stdin-unavailable")?;
        serde_json::to_writer(&mut *child_stdin, &startup_message)
            .map_err(|_| "sidecar-startup-write-failed")?;
        child_stdin
            .write_all(b"\n")
            .and_then(|_| child_stdin.flush())
            .map_err(|_| "sidecar-startup-write-failed")?;

        let child_stdout = child.stdout.take().ok_or("sidecar-stdout-unavailable")?;
        let (sender, receiver) = mpsc::sync_channel(1);
        thread::spawn(move || {
            let mut readiness_line = String::new();
            let result = BufReader::new(child_stdout).read_line(&mut readiness_line);
            let _ = sender.send(result.map(|_| readiness_line));
        });

        let readiness_line = receiver
            .recv_timeout(SIDECAR_READY_TIMEOUT)
            .map_err(|_| "sidecar-ready-timeout")?
            .map_err(|_| "sidecar-ready-read-failed")?;
        let ready: SidecarReady =
            serde_json::from_str(&readiness_line).map_err(|_| "sidecar-ready-invalid")?;
        if ready.event != "ready"
            || ready.protocol != SIDECAR_PROTOCOL_VERSION
            || ready.host != "127.0.0.1"
            || ready.port == 0
            || ready.database.state != "ready"
            || ready.database.location != DATABASE_LOCATION
        {
            return Err("sidecar-ready-invalid");
        }

        Ok((ready.port, ready.database.schema_version))
    })();

    match result {
        Ok((port, schema_version)) => Ok((
            SidecarProcess {
                child,
                _session_token: token,
                _port: port,
            },
            schema_version,
        )),
        Err(error_code) => {
            terminate_child(&mut child);
            Err(error_code)
        }
    }
}

fn start_sidecar(app: AppHandle) {
    let state = app.state::<RuntimeState>();
    if state.shutting_down.load(Ordering::Acquire) {
        return;
    }

    match launch_sidecar(&app) {
        Ok((mut process, schema_version)) => {
            if state.shutting_down.load(Ordering::Acquire) {
                terminate_child(&mut process.child);
                return;
            }
            *state.sidecar.lock().unwrap_or_else(|error| error.into_inner()) = Some(process);
            state.set_snapshot(RuntimeSnapshot::ready(schema_version));
        }
        Err(error_code) => state.set_snapshot(RuntimeSnapshot::failed(error_code)),
    }
}

fn stop_sidecar(app: &AppHandle) {
    let state = app.state::<RuntimeState>();
    if state.shutting_down.swap(true, Ordering::AcqRel) {
        return;
    }

    let mut process = state
        .sidecar
        .lock()
        .unwrap_or_else(|error| error.into_inner())
        .take();
    if let Some(process) = process.as_mut() {
        if let Some(stdin) = process.child.stdin.as_mut() {
            let _ = stdin.write_all(b"{\"command\":\"shutdown\"}\n");
            let _ = stdin.flush();
        }

        let deadline = Instant::now() + SIDECAR_SHUTDOWN_TIMEOUT;
        while Instant::now() < deadline {
            match process.child.try_wait() {
                Ok(Some(_)) => return,
                Ok(None) => thread::sleep(Duration::from_millis(50)),
                Err(_) => break,
            }
        }
        terminate_child(&mut process.child);
    }
}

fn refresh_sidecar_status(state: &RuntimeState) {
    if state.shutting_down.load(Ordering::Acquire) {
        return;
    }
    let exited = state
        .sidecar
        .lock()
        .unwrap_or_else(|error| error.into_inner())
        .as_mut()
        .is_some_and(|process| matches!(process.child.try_wait(), Ok(Some(_)) | Err(_)));
    if exited {
        state.set_snapshot(RuntimeSnapshot::failed("sidecar-exited"));
    }
}

#[tauri::command]
fn desktop_runtime_status(state: State<'_, RuntimeState>) -> String {
    refresh_sidecar_status(&state);
    serde_json::to_string(
        &*state
            .snapshot
            .lock()
            .unwrap_or_else(|error| error.into_inner()),
    )
    .unwrap_or_else(|_| {
        r#"{"state":"ready","version":"unknown","desktopShell":true,"singleInstance":true,"sidecar":"error","database":"error","databaseLocation":"data/foundry.sqlite3","schemaVersion":null,"errorCode":"status-serialization-failed"}"#.to_owned()
    })
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let builder = tauri::Builder::default();

    #[cfg(windows)]
    let builder = builder.plugin(tauri_plugin_single_instance::init(|app, _args, _cwd| {
        if let Some(window) = app.get_webview_window("main") {
            let _ = window.unminimize();
            let _ = window.show();
            let _ = window.set_focus();
        }
    }));

    let application = builder
        .manage(RuntimeState::new())
        .setup(|app| {
            let app_handle = app.handle().clone();
            thread::spawn(move || start_sidecar(app_handle));
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![desktop_runtime_status])
        .build(tauri::generate_context!())
        .expect("New Eden Foundry could not start");

    application.run(|app, event| {
        if matches!(event, RunEvent::Exit | RunEvent::ExitRequested { .. }) {
            stop_sidecar(app);
        }
    });
}
