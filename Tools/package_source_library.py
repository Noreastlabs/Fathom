#!/usr/bin/env python3
"""Install and verify the sealed, source-only 105-workbook library."""
import argparse
import hashlib
import json
from pathlib import Path

SOURCE = Path("Build/parallel-06/source-library-bundle-r01")
HANDOFF_SHA = "e796142858f7649e2e3189110265b1bf7346bd055971a92f6519b446d0dc0696"
INDEX_SHA = "8c5ef69740505e92176943b94c4da25a04178e7707190f061dbba923dbbcebbf"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def checked(root, allow_workspace_artifacts=False):
    if not root.is_absolute() or not root.is_dir() or root.is_symlink():
        raise ValueError("source library root is missing or linked")
    handoff_file = root / "handoff.json"
    index_file = root / "bundle/index.json"
    if any(path.is_symlink() for path in (handoff_file, root / "bundle", index_file)):
        raise ValueError("source library index is linked")
    handoff_bytes = handoff_file.read_bytes()
    index_bytes = index_file.read_bytes()
    if digest(handoff_bytes) != HANDOFF_SHA or digest(index_bytes) != INDEX_SHA:
        raise ValueError("source library handoff or index changed")
    handoff = json.loads(handoff_bytes)
    index = json.loads(index_bytes)
    if handoff != {"schema": "fathom-source-library-handoff.1", "bundle_root": "bundle",
                   "index": {"path": "index.json", "sha256": INDEX_SHA, "bytes": len(index_bytes)}}:
        raise ValueError("source library handoff differs")
    if (index["schema"] != "fathom-source-library.1" or len(index["entries"]) != 105
            or len(index["files"]) != 210 or any(index[key] for key in
            ("admitted", "runtime_admission", "whole_workbook_complete"))):
        raise ValueError("source library index exceeds source-only scope")
    expected = {"handoff.json": (len(handoff_bytes), HANDOFF_SHA),
                "bundle/index.json": (len(index_bytes), INDEX_SHA)}
    for name, record in index["files"].items():
        path = Path(name)
        if (not name.startswith("assets/Notes/music/guitar project/") or path.is_absolute()
                or any(part in (".", "..") for part in path.parts)):
            raise ValueError("unsafe source library asset path")
        expected["bundle/" + name] = (record["bytes"], record["sha256"])
    actual = {"handoff.json"}
    for path in (root / "bundle").rglob("*"):
        if path.is_symlink():
            raise ValueError("source library symlink")
        if path.is_file():
            actual.add(path.relative_to(root).as_posix())
    if actual != set(expected):
        raise ValueError("source library asset file set changed")
    if not allow_workspace_artifacts and {p.name for p in root.iterdir()} != {"handoff.json", "bundle"}:
        raise ValueError("installed source library has extra entries")
    for name, (size, sha) in expected.items():
        data = (root / name).read_bytes()
        if len(data) != size or digest(data) != sha:
            raise ValueError("changed source library asset: " + name)
    return expected


def package(source, output):
    expected = checked(source, allow_workspace_artifacts=True)
    if not output.is_absolute():
        raise ValueError("installed source library path must be absolute")
    if output.exists():
        if output.is_symlink():
            raise ValueError("installed source library is linked")
        checked(output)
        return "verified_existing"
    output.mkdir(parents=True)
    for name in expected:
        path = output / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((source / name).read_bytes())
    checked(output)
    return "copied_exact"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    source_root = args.source_root.resolve(strict=True)
    print(json.dumps({"status": package(source_root / SOURCE, args.output), "files": 212}, sort_keys=True))


if __name__ == "__main__":
    main()
