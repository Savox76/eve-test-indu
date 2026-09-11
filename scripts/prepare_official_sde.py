#!/usr/bin/env python3
"""Download, verify and normalize the pinned official EVE SDE."""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from new_eden_foundry_backend.official_sde import (  # noqa: E402
    build_official_industry_bundle,
    write_official_industry_bundle,
)

MANIFEST = BACKEND / "new_eden_foundry_backend" / "resources" / "official-sde-source.json"
DESTINATION = BACKEND / "new_eden_foundry_backend" / "resources" / "official-industry-sde.json.gz"


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if set(manifest) != {"buildNumber", "sha256", "url"}:
        raise ValueError("The official SDE source manifest is invalid.")
    expected_hash = manifest["sha256"]
    with tempfile.TemporaryDirectory(prefix="new-eden-foundry-sde-") as temporary:
        archive_path = Path(temporary) / "official-sde.zip"
        with urllib.request.urlopen(manifest["url"], timeout=180) as response:
            archive_path.write_bytes(response.read())
        actual_hash = hashlib.sha256(archive_path.read_bytes()).hexdigest()
        if actual_hash != expected_hash:
            raise ValueError("The official SDE archive checksum does not match.")
        bundle = build_official_industry_bundle(archive_path)
        if bundle["build_number"] != str(manifest["buildNumber"]):
            raise ValueError("The official SDE build number does not match.")
        write_official_industry_bundle(bundle, DESTINATION)
    print(
        json.dumps(
            {
                "buildNumber": bundle["build_number"],
                "bytes": DESTINATION.stat().st_size,
                "destination": str(DESTINATION.relative_to(ROOT)),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
