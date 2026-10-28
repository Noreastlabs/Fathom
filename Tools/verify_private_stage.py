#!/usr/bin/env python3
"""Check the full private stage's local input manifests without running the app."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def check(root, manifest_name):
    manifest = json.loads((root / manifest_name).read_text())
    for entry in manifest["files"]:
        relative = Path(entry["path"])
        if relative.is_absolute() or any(part in (".", "..") for part in relative.parts):
            raise ValueError("unsafe input path")
        path = root / relative
        if path.is_symlink() or not path.is_file() or path.stat().st_size != entry["bytes"] or digest(path) != entry["sha256"]:
            raise ValueError("input differs: " + str(relative))
    return len(manifest["files"])


def main():
    root = Path(__file__).resolve().parents[1]
    forbidden = [root / ".git", root / "Source/optional_content", root / "Tools/generate_empty_content.py", root / "Tools/empty-content-templates"]
    if any(path.exists() for path in forbidden):
        raise ValueError("full private stage contains a Git index or restricted-only placeholder tooling")
    dependencies = check(root, "Dependencies/ActualFiles.manifest.json")
    generated = check(root, "GeneratedSources.manifest.json")
    identities = check(root, "SourceIdentityInputs.manifest.json")
    subprocess.run([sys.executable, "-B", str(root / "Tools/stage_runtime_assets.py"), "--root", str(root), "--check-only"], check=True)
    print(f"PASS: {dependencies} actual dependency files, {generated} exact generated source headers, {identities} current software-identity inputs")
    print("Clean packaging stage; archived evidence is metadata-only and predecessor projections are typed. Publication rights/terms are not certified.")


if __name__ == "__main__":
    main()
