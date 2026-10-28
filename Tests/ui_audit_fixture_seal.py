#!/usr/bin/env python3
"""Optional same-owner integrity seal of the separate test App, never Fathom.

Root must review and explicitly invoke this target. No trust/quarantine changes,
certificates, timestamp service, Gatekeeper, installation or release authority.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BUNDLE_ID = "local.fathom.ui-audit-fixture"
MACH_O_MAGIC = {bytes.fromhex(value) for value in
                ("feedface", "cefaedfe", "feedfacf", "cffaedfe", "cafebabe", "bebafeca", "cafebabf", "bfbafeca")}
# Exact historical nonadmitted read-only validator data, preserved identically
# to the existing production private-integrity recipe. It is not signed/run.
DATA_VALIDATOR_PATH = "Contents/Resources/curriculum-shards/bundle/bin/fathom_content_validate"
DATA_VALIDATOR_BYTES = 1952840
DATA_VALIDATOR_SHA = "a85c1b25d8cded12cbe273e4620bd5f33a711d06311d29583a0fdbed7748f714"


def need(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def macho(path: Path) -> bool:
    with path.open("rb") as stream:
        return stream.read(4) in MACH_O_MAGIC


def guarded_bundle(path: Path) -> Path:
    need(sys.platform == "darwin", "Fixture integrity sealing is macOS-only")
    need(path.is_absolute() and path.is_dir() and path == path.resolve(), "Existing real absolute fixture App required")
    path.relative_to(ROOT / "Build")
    need(path.name == "Fathom UI Audit Fixture.app" and path.parent.parent.name == "fathom_ui_audit_fixture_artefacts" and
         path.parent.name in {"Debug", "Release", "RelWithDebInfo", "MinSizeRel"}, "Only the separate native fixture build output is eligible")
    info = plistlib.loads((path / "Contents/Info.plist").read_bytes())
    need(info.get("CFBundleIdentifier") == BUNDLE_ID and info.get("CFBundleExecutable") == "Fathom UI Audit Fixture", "Wrong fixture App/executable identity")
    executable = path / "Contents/MacOS/Fathom UI Audit Fixture"
    need(executable.is_file() and executable.stat().st_nlink == 1 and macho(executable), "Fixture executable must be an unshared Mach-O file")
    need((path / "Contents/Resources/ui-audit-resource-pin.json").is_file(), "Reviewed resource pin required before fixture sealing")
    for member in [path, *path.rglob("*")]:
        need(not member.is_symlink() and member.stat().st_uid == os.geteuid(), "All fixture bundle members must be real same-owner paths")
        need(member.is_file() or member.is_dir(), "Special filesystem members refused")
        if member != path:
            need(member.suffix.lower() not in {".app", ".framework", ".dylib", ".xpc", ".appex", ".so", ".bundle"}, "Nested code refused")
        if member.parent == executable.parent:
            need(member == executable, "Only the named fixture executable belongs in MacOS")
        if member.is_file() and member != executable and macho(member):
            need(member.relative_to(path).as_posix() == DATA_VALIDATOR_PATH and member.stat().st_size == DATA_VALIDATOR_BYTES and
                 hashlib.sha256(member.read_bytes()).hexdigest() == DATA_VALIDATOR_SHA, "Unexpected/changed native resource refused")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    args = parser.parse_args()
    path = guarded_bundle(args.bundle)
    sign = ["/usr/bin/codesign", "--force", "--sign", "-", "--timestamp=none", "--identifier", BUNDLE_ID, str(path)]
    verify = ["/usr/bin/codesign", "--verify", "--deep", "--strict", str(path)]
    subprocess.run(sign, check=True)
    subprocess.run(verify, check=True)
    print(json.dumps({"status": "private_fixture_integrity_verified", "bundle": str(path), "bundle_id": BUNDLE_ID,
                      "signature": "ad hoc, no timestamp or external identity", "sign_command": sign, "verify_command": verify,
                      "qualification": "Test capability only; no OS trust, clean-install, listening, learner or release acceptance"}, sort_keys=True))


if __name__ == "__main__":
    main()
