#!/usr/bin/env python3
"""Prepare only the separate UI fixture's adapter and Build-owned resource copy.

No production/source edits, launch, profile, signing or security operations.
Native integration owner runs this through the reviewed CMake proposal.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import plistlib
import shutil

ROOT = Path(__file__).resolve().parents[1]
ADAPTER_SHA256 = "5c5b892daebdb513911d4405b796d344c7cfe7bdc453c73e393038dc65885d61"
PIN_NAME = "ui-audit-resource-pin.json"


def need(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_owned(path: Path) -> Path:
    need(path.is_absolute(), "Explicit absolute Build path required")
    need(path == path.resolve(), "Build output cannot contain symlink/relative components")
    path.relative_to(ROOT / "Build")
    return path


def real_components(path: Path, *, allow_missing: bool = False, directory: bool = False) -> None:
    """Preflight every component before reads, mkdir or destination writes."""
    need(path.is_absolute() and path == path.resolve(), "Path cannot redirect through symlink/relative components")
    for component in [*reversed(path.parents), path]:
        need(not component.is_symlink(), "Symlink path component refused")
        if component.exists():
            if component != path or directory:
                need(component.is_dir(), "Directory path component is not a real directory")
            else:
                need(component.is_file(), "File path is not a regular file")
        else:
            need(allow_missing, "Required real path component is missing")


def safe_mkdir(path: Path) -> None:
    real_components(path, allow_missing=True, directory=True)
    # Recheck each ancestor immediately before creating its next child. There is
    # no mkdir through a pre-existing redirect, including a missing leaf's parent.
    for component in [*reversed(path.parents), path]:
        need(not component.is_symlink(), "Directory creation redirect refused")
        if component.exists():
            need(component.is_dir(), "Directory creation parent is not a directory")
        else:
            component.mkdir(mode=0o700)
    real_components(path, directory=True)


def resource_target(path: Path) -> None:
    real_components(path, allow_missing=True)
    if path.exists():
        need(path.stat().st_nlink == 1, "Existing destination resource hard link refused")
        need(path.stat().st_size <= 256 * 1024 * 1024, "Existing destination resource exceeds size bound")


def adapter(source: Path, output: Path) -> None:
    need(source.resolve() == ROOT / "Source/platform/AudioOutputMac.mm", "Only the reviewed existing adapter is supported")
    need(sha(source) == ADAPTER_SHA256, "Platform adapter changed; independent material re-review required before regenerating fixture")
    build_owned(output)
    original = source.read_text()
    begin = "bool AudioOutputMac::connect(const OutputCapability& selected,output::Format fmt,RenderOutput provider,void* context,\n"
    end = "bool AudioOutputMac::send(Control c) {"
    need(original.count(begin) == 1 and original.count(end) == 1, "Reviewed adapter function boundaries changed")
    head, tail = original.split(begin, 1)
    _, after = tail.split(end, 1)
    replacement = """// Fixture-only fail-closed replacement of the native device-open entry.
std::atomic<unsigned> uiAuditForbiddenNativeConnectCalls{};
bool AudioOutputMac::connect(const OutputCapability&,output::Format,RenderOutput,void*,OutputObserver,ScheduledRender) {
    ++uiAuditForbiddenNativeConnectCalls;
    p_->lastError="UI fixture prohibits native Connect; use the owned silent software seam";
    return false;
}
"""
    generated = ("#if !defined(FATHOM_UI_AUDIT_FIXTURE)\n#error Generated adapter is fixture-only\n#endif\n"
                 + head + replacement + end + after)
    need("createAudioIODeviceType_CoreAudio" not in generated and "p.device->open" not in generated and
         "p.device->start" not in generated, "Native opening implementation was not fully removed")
    resource_target(output)
    safe_mkdir(output.parent)
    resource_target(output)
    if not output.exists() or output.read_text() != generated:
        output.write_text(generated)
    print(json.dumps({"status": "prepared-not-executed", "adapter_source_sha256": ADAPTER_SHA256,
                      "generated_sha256": sha(output), "path": str(output)}, sort_keys=True))


def bundle(path: Path, identifier: str) -> tuple[Path, Path]:
    build_owned(path)
    need(path.suffix == ".app", "Explicit Build-owned App directory required")
    real_components(path, directory=True)
    real_components(path / "Contents", directory=True)
    real_components(path / "Contents/MacOS", directory=True)
    info_path = path / "Contents/Info.plist"
    real_components(info_path)
    need(info_path.stat().st_size <= 1024 * 1024, "App metadata exceeds size bound")
    info = plistlib.loads(info_path.read_bytes())
    need(info.get("CFBundleIdentifier") == identifier, "Unexpected App identity")
    expected_executable = {"local.fathom.guitar": "Fathom", "local.fathom.ui-audit-fixture": "Fathom UI Audit Fixture"}[identifier]
    need(info.get("CFBundleExecutable") == expected_executable, "Unexpected named App executable")
    executable = path / "Contents/MacOS" / info["CFBundleExecutable"]
    real_components(executable)
    need(executable.stat().st_size <= 1024 * 1024 * 1024, "Named App executable exceeds size bound")
    resources = path / "Contents/Resources"
    real_components(resources, allow_missing=identifier == "local.fathom.ui-audit-fixture", directory=True)
    return executable, resources


def resource_copy(source_app: Path, fixture_app: Path) -> None:
    source_executable, source = bundle(source_app, "local.fathom.guitar")
    _, destination = bundle(fixture_app, "local.fathom.ui-audit-fixture")
    need(source_app != fixture_app and source.is_dir(), "Source and fixture bundles must be separate")
    source_hash = sha(source_executable)
    need(not (source / PIN_NAME).exists(), "Production resource source cannot be another fixture")
    # Preflight manifest destinations before even creating Resources.
    resource_target(destination / PIN_NAME)
    resource_target(destination / (PIN_NAME + ".tmp"))
    need(not (destination / (PIN_NAME + ".tmp")).exists(), "Previous incomplete fixture pin retained; inspect it before retry")
    previous = {}
    if (destination / PIN_NAME).exists():
        need((destination / PIN_NAME).stat().st_size <= 16 * 1024 * 1024, "Existing resource pin exceeds size bound")
        previous = json.loads((destination / PIN_NAME).read_text())
        need(previous.get("version") == "fathom-ui-audit-resources-v1", "Existing fixture resource identity is unsupported")
    known = {row["path"]: row for row in previous.get("files", [])}
    plan = []
    total = 0
    destination_total = 0
    for path in sorted(source.rglob("*")):
        real_components(path, directory=path.is_dir())
        if path.is_dir():
            continue
        need(path.is_file(), "Unexpected resource type")
        relative = path.relative_to(source)
        target = destination / relative
        size = path.stat().st_size
        total += size
        need(size <= 256 * 1024 * 1024 and total <= 2 * 1024 * 1024 * 1024, "Resource inventory exceeds fixture integrity limits")
        resource_target(target)
        if target.exists():
            destination_total += target.stat().st_size
            need(destination_total <= 2 * 1024 * 1024 * 1024, "Existing destination inventory exceeds byte bound")
        plan.append((path, relative, target, size))
        need(len(plan) <= 10000, "Resource inventory exceeds fixture file bound")
    current = {str(relative) for _, relative, _, _ in plan}
    need(set(known).issubset(current), "Source removed prior fixture resources; use a fresh candidate bundle instead of deleting evidence")
    # All path/type/link/size/total preflight completes before resource hashes or
    # any resource destination mkdir/copy. Repeat write checks at the boundary.
    files = []
    for path, relative, target, size in plan:
        digest = sha(path)
        need(path.stat().st_size == size, "Source resource size changed during inventory")
        resource_target(target)
        # A rebuild may update only files owned by the earlier fixture manifest.
        # Native JUCE artwork is not silently overwritten if untracked.
        if target.exists():
            need(str(relative) in known or sha(target) == digest, "Refuse replacing an untracked fixture resource")
        safe_mkdir(target.parent)
        resource_target(target)
        if not target.exists() or sha(target) != digest:
            shutil.copy2(path, target)
        need(target.stat().st_size == size and sha(target) == digest, "Fixture resource copy differs from selected build")
        files.append({"path": str(relative), "bytes": size, "sha256": digest})
    need(sha(source_executable) == source_hash, "Selected production executable changed during resource freeze")
    for required in ("representative-controls", "learn-source-index"):
        need((destination / required).is_dir(), "Required installed activity resources unavailable")
    pin = {"version": "fathom-ui-audit-resources-v1", "source_app": str(source_app),
           "source_executable_sha256": source_hash, "files": files, "total_bytes": total,
           "physical_or_human_review": False}
    payload = json.dumps(pin, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    temporary = destination / (PIN_NAME + ".tmp")
    safe_mkdir(destination)
    resource_target(temporary)
    resource_target(destination / PIN_NAME)
    need(not temporary.exists(), "Previous incomplete fixture pin retained; inspect it before retry")
    temporary.write_text(payload)
    temporary.replace(destination / PIN_NAME)
    print(json.dumps({"status": "resource-copy-pinned", "manifest": str(destination / PIN_NAME),
                      "resource_pin_sha256": sha(destination / PIN_NAME), "files": len(files), "total_bytes": total,
                      "source_executable_sha256": source_hash}, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="mode", required=True)
    generated = subparsers.add_parser("adapter")
    generated.add_argument("--source", type=Path, required=True)
    generated.add_argument("--output", type=Path, required=True)
    resources = subparsers.add_parser("resources")
    resources.add_argument("--source-app", type=Path, required=True)
    resources.add_argument("--fixture-app", type=Path, required=True)
    args = parser.parse_args()
    if args.mode == "adapter":
        adapter(args.source, args.output)
    else:
        resource_copy(args.source_app, args.fixture_app)


if __name__ == "__main__":
    main()
