#!/usr/bin/env python3
"""Package the exact nonadmitted four-shard source bundle for read-only app discovery."""
import argparse
import hashlib
import json
from pathlib import Path

HANDOFF_SHA = "4470bee879aaef0807083b3130811fe71aa1eec3bead05cf2393dcf5956cccac"
INVENTORY_SHA = "1ad666cf363157c435d29e18a5787de1e58cfd8fbf2f3ed29edd057e5e553676"
MANIFEST_SHA = "01967090d337c7154211ddd8e6926a9d67aa1ed2a7eda0e37b662d0b52aa33e8"
SOURCE_REL = Path("Build/parallel-13/four-shard-source-bundle-r01")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def safe(root, name):
    path = Path(name)
    if not name or path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
        raise ValueError(f"unsafe bundle path: {name}")
    current = root
    for part in path.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"bundle symlink: {name}")
    if not current.is_file():
        raise ValueError(f"missing bundle file: {name}")
    return current


def checked_files(source):
    handoff_bytes = safe(source, "handoff.json").read_bytes()
    if digest(handoff_bytes) != HANDOFF_SHA:
        raise ValueError("changed shard handoff")
    handoff = json.loads(handoff_bytes)
    if handoff["schema"] != "fathom-four-shard-reader-handoff.1" or handoff["bundle_root"] != "bundle":
        raise ValueError("unexpected shard handoff")
    if handoff["path_policy"]["external_references_remaining"]:
        raise ValueError("external shard reference")
    bundle = source / "bundle"
    inventory_bytes = safe(bundle, "bundle-inventory.json").read_bytes()
    if digest(inventory_bytes) != INVENTORY_SHA:
        raise ValueError("changed shard inventory")
    inventory = json.loads(inventory_bytes)
    if inventory["schema"] != "fathom-four-shard-source-bundle.1" or any(
        inventory[key] for key in ("admitted", "aggregate_complete", "runtime_admission")
    ):
        raise ValueError("unsupported shard inventory")
    manifest_ref = handoff["manifest"]
    manifest_bytes = safe(bundle, manifest_ref["path"]).read_bytes()
    if digest(manifest_bytes) != MANIFEST_SHA or manifest_ref["sha256"] != MANIFEST_SHA:
        raise ValueError("changed global shard manifest")
    expected = {"handoff.json": (len(handoff_bytes), HANDOFF_SHA),
                "bundle/bundle-inventory.json": (len(inventory_bytes), INVENTORY_SHA)}
    for name, ref in inventory["files"].items():
        expected["bundle/" + name] = (ref["bytes"], ref["sha256"])
    actual = {"handoff.json"}
    for path in bundle.rglob("*"):
        if path.is_symlink():
            raise ValueError(f"bundle symlink: {path}")
        if path.is_file():
            actual.add(path.relative_to(source).as_posix())
    if actual != set(expected):
        raise ValueError("bundle file set differs from inventory")
    for name, (size, sha) in expected.items():
        path = safe(source, name)
        if path.stat().st_size != size or digest(path.read_bytes()) != sha:
            raise ValueError(f"changed shard asset: {name}")
    return expected


def package(source, output):
    expected = checked_files(source)
    if not output.is_absolute():
        raise ValueError("output must be absolute")
    if output.exists():
        if output.is_symlink():
            raise ValueError("existing output is a symlink")
        actual = {p.relative_to(output).as_posix() for p in output.rglob("*") if p.is_file() or p.is_symlink()}
        if actual != set(expected):
            raise ValueError("existing output file set differs")
        for name, (size, sha) in expected.items():
            path = safe(output, name)
            if path.stat().st_size != size or digest(path.read_bytes()) != sha:
                raise ValueError(f"existing output changed: {name}")
        return {"status": "verified_existing", "files": len(expected)}
    output.mkdir(parents=True)
    for name in expected:
        destination = output / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        with safe(source, name).open("rb") as reader, destination.open("xb") as writer:
            while chunk := reader.read(1024 * 1024):
                writer.write(chunk)
    return {"status": "copied_exact", "files": len(expected)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    source_root = args.source_root.resolve(strict=True)
    print(json.dumps(package(source_root / SOURCE_REL, args.output), sort_keys=True))


if __name__ == "__main__":
    main()
