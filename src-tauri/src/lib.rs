#[tauri::command]
fn desktop_runtime_status() -> String {
    format!(
        concat!(
            r#"{{"state":"ready","version":"{}","#,
            r#""desktopShell":true,"sidecar":"pending","database":"foundation"}}"#
        ),
        env!("CARGO_PKG_VERSION")
    )
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![desktop_runtime_status])
        .run(tauri::generate_context!())
        .expect("New Eden Foundry could not start");
}
