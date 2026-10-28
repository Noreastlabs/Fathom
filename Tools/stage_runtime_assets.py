#!/usr/bin/env python3
"""Verify/copy the exact clean runtime transport and retained curriculum payload.

Archived evidence remains metadata-only; typed predecessor projections are
separately hash-bound. This command does not certify publication rights.
"""
from pathlib import Path
import argparse
import hashlib
import json
import shutil


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve(strict=True)
    assets = root / "RuntimeAssets"
    records = json.loads((root / "RuntimeAssets.manifest.json").read_text())["files"]
    expected = set()
    for entry in records:
        name = Path(entry["path"])
        if name.is_absolute() or any(part in (".", "..") for part in name.parts):
            raise ValueError("unsafe runtime path")
        source = assets / name
        if source.is_symlink() or not source.is_file() or source.stat().st_size != entry["bytes"] or digest(source) != entry["sha256"]:
            raise ValueError("runtime input differs: " + str(name))
        expected.add(name.as_posix())
    actual = {p.relative_to(assets).as_posix() for p in assets.rglob("*") if p.is_file()}
    if any(p.is_symlink() for p in assets.rglob("*")) or actual != expected:
        raise ValueError("runtime input file set differs")
    if not args.check_only:
        if args.output is None:
            raise ValueError("--output required when copying")
        target = args.output.resolve(strict=True)
        for entry in records:
            relative = Path(entry["path"])
            destination = target / relative
            if destination.is_symlink():
                raise ValueError("linked runtime output")
            if destination.exists():
                if not destination.is_file() or digest(destination) != entry["sha256"]:
                    raise ValueError("existing runtime output differs; use a new build directory")
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(assets / relative, destination)
        copied = {p.relative_to(target).as_posix() for p in target.rglob("*") if p.is_file()}
        if copied - expected - {"RecentFilesMenuTemplate.nib"}:
            raise ValueError("unexpected runtime output members")
    print(f"Verified {len(records)} exact clean runtime transport files")


if __name__ == "__main__":
    main()
