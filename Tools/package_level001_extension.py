#!/usr/bin/env python3
"""Package only the frozen 108-unit Level1 authority and pinned producer decision."""
import argparse
import hashlib
import json
from pathlib import Path


def package(root: Path, output: Path) -> None:
    source = root / "Content/runtime/level001-extension-v1"
    raw = (source / "manifest.json").read_bytes()
    manifest = json.loads(raw)
    if manifest["version"] != "level001-extension-bundle.1" or len(manifest["files"]) != 19:
        raise ValueError("Unsupported Level1 extension manifest")
    files = {"manifest.json": raw}
    local = {"decision.json", "agent-curriculum-decision.md", "installed-empty-resource-plan.json"}
    for entry in manifest["files"]:
        name = entry["path"]
        rel = Path(name)
        if rel.is_absolute() or any(part in ("", ".", "..") for part in name.split("/")) or "\\" in name:
            raise ValueError("Unsafe extension path")
        path = (source if name in local else root) / rel
        if any(part.is_symlink() for part in [path, *path.parents]):
            raise ValueError("Extension symlink refused")
        data = path.read_bytes()
        if len(data) != entry["bytes"] or hashlib.sha256(data).hexdigest() != entry["sha256"]:
            raise ValueError("Changed Level1 authority asset: " + name)
        if name in files:
            raise ValueError("Duplicate extension asset")
        files[name] = data
    if not output.is_absolute() or any(part.is_symlink() for part in [output, *output.parents]):
        raise ValueError("Absolute nonsymlink output required")
    if output.exists():
        actual = {str(path.relative_to(output)) for path in output.rglob("*") if path.is_file() or path.is_symlink()}
        if actual != set(files) or any((output / path).is_symlink() or (output / path).read_bytes() != data for path, data in files.items()):
            raise ValueError("Existing Level1 bundle differs; retain it and choose a fresh build")
    else:
        output.mkdir(parents=True)
        for name, data in files.items():
            destination = output / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("xb") as stream:
                stream.write(data)
    print("Verified exact Level1 extension", len(files), "files", sum(map(len, files.values())), "bytes")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    package(args.source_root.resolve(strict=True), args.output)
