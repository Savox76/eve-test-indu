#!/usr/bin/env python3
"""Exercise a frozen sidecar exactly as the Tauri parent process does."""

from __future__ import annotations

import argparse
import json
import queue
import secrets
import sqlite3
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import TextIO


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--executable", type=Path, required=True)
    return parser


def read_line_with_timeout(stream: TextIO, timeout: float) -> str:
    result: queue.Queue[str] = queue.Queue(maxsize=1)
    reader = threading.Thread(target=lambda: result.put(stream.readline()), daemon=True)
    reader.start()
    try:
        line = result.get(timeout=timeout)
    except queue.Empty as error:
        raise RuntimeError("Sidecar readiness timed out.") from error
    if not line:
        raise RuntimeError("Sidecar exited before reporting readiness.")
    return line


def wait_for_health(
    opener: urllib.request.OpenerDirector,
    url: str,
    token: str,
) -> dict[str, object]:
    deadline = time.monotonic() + 12
    request = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {token}"},
    )
    while time.monotonic() < deadline:
        try:
            with opener.open(request, timeout=1) as response:
                return json.loads(response.read())
        except (OSError, urllib.error.URLError):
            time.sleep(0.05)
    raise RuntimeError("Sidecar health did not become available.")


def expect_unauthorized(
    opener: urllib.request.OpenerDirector,
    url: str,
    authorization: str | None,
) -> None:
    headers = {} if authorization is None else {"Authorization": authorization}
    request = urllib.request.Request(url, headers=headers)
    try:
        opener.open(request, timeout=3)
    except urllib.error.HTTPError as error:
        if error.code == 401:
            return
        raise RuntimeError(f"Expected HTTP 401, received {error.code}.") from error
    raise RuntimeError("An unauthenticated sidecar request was accepted.")


def main() -> int:
    arguments = build_parser().parse_args()
    executable = arguments.executable.resolve(strict=True)
    token = secrets.token_hex(32)

    with tempfile.TemporaryDirectory(prefix="new-eden-foundry-sidecar-") as temporary_directory:
        program_directory = Path(temporary_directory).resolve()
        process = subprocess.Popen(
            [str(executable)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            bufsize=1,
        )
        assert process.stdin is not None
        assert process.stdout is not None
        assert process.stderr is not None
        try:
            process.stdin.write(
                json.dumps(
                    {
                        "protocol": 1,
                        "sessionToken": token,
                        "programDirectory": str(program_directory),
                    }
                )
                + "\n"
            )
            process.stdin.flush()
            ready_line = read_line_with_timeout(process.stdout, 20)
            ready = json.loads(ready_line)
            if ready.get("event") != "ready" or ready.get("host") != "127.0.0.1":
                raise RuntimeError(f"Unexpected readiness payload: {ready!r}")
            if token in ready_line:
                raise RuntimeError("The readiness payload exposed the session token.")

            health_url = f"http://127.0.0.1:{int(ready['port'])}/health"
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            health = wait_for_health(opener, health_url, token)
            expect_unauthorized(opener, health_url, None)
            expect_unauthorized(opener, health_url, "Bearer incorrect")

            database = health.get("database")
            if not isinstance(database, dict) or database.get("location") != "data/foundry.sqlite3":
                raise RuntimeError("The sidecar reported an unexpected database location.")
            if database.get("schemaVersion") != 2 or database.get("integrity") != "ok":
                raise RuntimeError("The sidecar database health is invalid.")

            database_path = program_directory / "data" / "foundry.sqlite3"
            if not database_path.is_file():
                raise RuntimeError("The database was not created inside the program directory.")
            with sqlite3.connect(database_path) as connection:
                if connection.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                    raise RuntimeError("The created SQLite database failed quick_check.")

            process.stdin.write('{"command":"shutdown"}\n')
            process.stdin.flush()
            exit_code = process.wait(timeout=12)
            remaining_output = process.stdout.read()
            error_output = process.stderr.read()
            if exit_code != 0:
                raise RuntimeError(f"The sidecar exited with code {exit_code}: {error_output}")
            if token in remaining_output or token in error_output:
                raise RuntimeError("Sidecar output exposed the session token.")
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)
            for stream in (process.stdin, process.stdout, process.stderr):
                if stream is not None and not stream.closed:
                    stream.close()

    print("Frozen sidecar handshake, database location and shutdown verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
