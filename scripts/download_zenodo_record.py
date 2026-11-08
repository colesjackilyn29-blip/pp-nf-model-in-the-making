#!/usr/bin/env python3
"""Download every public file listed in a Zenodo record and verify checksums."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
from urllib.request import Request, urlopen

RECORD_ID = "24050201"
API_URL = f"https://zenodo.org/api/records/{RECORD_ID}"
USER_AGENT = "pp-nf-model-materials/1.0 (Zenodo record downloader)"


def fetch(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=60) as response:
        return response.read()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data") / "zenodo" / RECORD_ID,
        help="directory for downloaded files (default: data/zenodo/24050201)",
    )
    args = parser.parse_args()

    metadata_bytes = fetch(API_URL)
    metadata = json.loads(metadata_bytes)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "record.json").write_bytes(metadata_bytes)

    entries = metadata.get("files", {}).get("entries", {})
    if not entries:
        raise SystemExit("No public file entries found in the Zenodo record metadata.")

    for key, entry in entries.items():
        # Use only the basename from the server-provided key, never a path.
        filename = PurePosixPath(key).name
        if filename in {"", ".", ".."}:
            raise SystemExit(f"Unsafe or empty filename in record metadata: {key!r}")
        url = entry.get("links", {}).get("content")
        if not url:
            raise SystemExit(f"No content URL provided for {key!r}")

        destination = args.output / filename
        data = fetch(url)
        checksum = entry.get("checksum", "")
        if checksum.startswith("md5:"):
            actual = hashlib.md5(data).hexdigest()
            expected = checksum.removeprefix("md5:")
            if actual.lower() != expected.lower():
                raise SystemExit(
                    f"Checksum mismatch for {filename}: expected {expected}, got {actual}"
                )
        destination.write_bytes(data)
        print(f"Downloaded {filename} ({len(data):,} bytes)")

    print(f"Saved {len(entries)} files and record metadata under {args.output}")


if __name__ == "__main__":
    main()
