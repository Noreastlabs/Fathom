#!/usr/bin/env python3
"""Seal only a same-owner native Fathom build for private integrity testing."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import subprocess
import sys

BUNDLE_ID = "local.fathom.guitar"
MACH_O_MAGIC = {bytes.fromhex(value) for value in
                ("feedface", "cefaedfe", "feedfacf", "cffaedfe",
                 "cafebabe", "bebafeca", "cafebabf", "bfbafeca")}
# Existing nonadmitted, read-only shard data; never sign or execute this resource.
# Authority: package_curriculum_shards.py INVENTORY_SHA 1ad666cf...e553676,
# bundle-inventory.json files["bin/fathom_content_validate"].
DATA_VALIDATOR_PATH = "Contents/Resources/curriculum-shards/bundle/bin/fathom_content_validate"
DATA_VALIDATOR_BYTES = 1952840
DATA_VALIDATOR_SHA = "a85c1b25d8cded12cbe273e4620bd5f33a711d06311d29583a0fdbed7748f714"


def is_mach_o(path: Path) -> bool:
    with path.open("rb") as stream:
        return stream.read(4) in MACH_O_MAGIC


def guarded_bundle(raw: str) -> Path:
    bundle = Path(raw)
    root = Path(__file__).resolve().parent.parent
    if sys.platform != "darwin":
        raise ValueError("Private bundle sealing requires macOS.")
    if not bundle.is_absolute() or not bundle.is_dir() or bundle.is_symlink():
        raise ValueError("Expected an existing absolute native bundle directory.")
    resolved = bundle.resolve(strict=True)
    if resolved != bundle or not resolved.is_relative_to(root / "Build"):
        raise ValueError("Expected a real private artifact under this checkout's Build directory.")
    if bundle.name != "Fathom.app" or bundle.parent.parent.name != "Fathom_artefacts":
        raise ValueError("Only the native Fathom build output is eligible; preserved packages are excluded.")
    if bundle.parent.name not in {"Debug", "Release", "RelWithDebInfo", "MinSizeRel"}:
        raise ValueError("Unexpected native build configuration directory.")
    info_path = bundle / "Contents/Info.plist"
    executable = bundle / "Contents/MacOS/Fathom"
    resources = bundle / "Contents/Resources"
    for path in (bundle, bundle / "Contents", info_path, executable, resources):
        if path.is_symlink() or path.stat().st_uid != os.geteuid():
            raise ValueError("Bundle, metadata, executable and resources must be real same-owner paths.")
    if not info_path.is_file() or not executable.is_file() or not resources.is_dir():
        raise ValueError("Completed metadata, executable and resources are required.")
    if executable.stat().st_nlink != 1:
        raise ValueError("The mutable executable must not share a hard link with another artifact.")
    if not is_mach_o(executable):
        raise ValueError("The intended Fathom executable must be Mach-O.")
    info = plistlib.loads(info_path.read_bytes())
    if info.get("CFBundleIdentifier") != BUNDLE_ID or info.get("CFBundleExecutable") != "Fathom":
        raise ValueError("Existing Fathom bundle/executable identity differs.")
    # Seal the application only. Preserve the exact historical read-only validator
    # as inventory-bound data; other native members need a separate reviewed recipe.
    for path in bundle.rglob("*"):
        if path.is_symlink() or path.stat().st_uid != os.geteuid():
            raise ValueError("Every bundle member must be a real same-owner path.")
        if path != bundle and (path.suffix.lower() in {".app", ".framework", ".dylib", ".xpc", ".appex", ".so", ".bundle"}):
            raise ValueError("Nested code is outside this private sealing recipe.")
        if path.parent == executable.parent and path != executable:
            raise ValueError("Only Fathom belongs in this bundle's MacOS executable directory.")
        if path.is_file() and path != executable and is_mach_o(path):
            if (path.relative_to(bundle).as_posix() != DATA_VALIDATOR_PATH or
                    path.stat().st_size != DATA_VALIDATOR_BYTES or
                    hashlib.sha256(path.read_bytes()).hexdigest() != DATA_VALIDATOR_SHA):
                raise ValueError("Unexpected or changed native resource is outside this private sealing recipe.")
        if not path.is_file() and not path.is_dir():
            raise ValueError("Special filesystem members are outside this private sealing recipe.")
    return bundle


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", help="Absolute native Fathom build output")
    args = parser.parse_args()
    try:
        bundle = guarded_bundle(args.bundle)
        sign = ["/usr/bin/codesign", "--force", "--sign", "-", "--timestamp=none",
                "--identifier", BUNDLE_ID, str(bundle)]
        verify = ["/usr/bin/codesign", "--verify", "--deep", "--strict", str(bundle)]
        subprocess.run(sign, check=True)
        subprocess.run(verify, check=True)
        print(json.dumps({"status": "private_integrity_verified",
                          "bundle": str(bundle), "bundle_id": BUNDLE_ID,
                          "signature": "ad hoc, no timestamp or external identity",
                          "sign_command": sign, "verify_command": verify,
                          "qualification": "Gatekeeper, install/run, transfer and release remain separate"}))
        return 0
    except (ValueError, OSError, plistlib.InvalidFileException, subprocess.CalledProcessError) as error:
        print(f"Private bundle integrity refused/failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
