"""Run a local foundation self-check without starting a network service."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Sequence

from .database import initialize_database
from .version import project_version


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check the New Eden Foundry local core.")
    parser.add_argument(
        "--database",
        type=Path,
        required=True,
        help="Path to a development or temporary SQLite database.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    database = initialize_database(arguments.database)
    result = {
        "service": "new-eden-foundry-core",
        "state": "foundation-ready",
        "version": project_version(),
        "database": asdict(database),
    }
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
