"""PyInstaller entry point for the New Eden Foundry sidecar."""

from new_eden_foundry_backend.sidecar import main


if __name__ == "__main__":
    raise SystemExit(main())
