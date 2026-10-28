#!/usr/bin/env python3
"""Bounded metadata for one explicitly pinned Fathom build; never launches the App.

All App/build/source paths and the fresh output directory must be in --root.
The output parent must already exist. Historical resource metadata is optional
and remains explicitly cached; this command never walks or hashes resources.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import datetime as dt
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import plistlib
import re
import shlex
import stat
import subprocess
import tempfile
from typing import Callable

SHA = re.compile(r"[0-9a-f]{64}\Z")
COMMAND_TIMEOUT_SECONDS = 15.0
MAX_COMMAND_BYTES = 1024 * 1024
MAX_METADATA_BYTES = 2 * 1024 * 1024
MAX_OUTPUT_DOCUMENT_BYTES = 4 * 1024 * 1024


class AuditError(ValueError):
    """Fail closed without publishing metadata from an ambiguous observation."""


@dataclass(frozen=True)
class Request:
    root: Path
    build: Path
    app: Path
    expected_executable_sha256: str
    out: Path
    historical_resource_ref: Path | None = None


@dataclass(frozen=True)
class Snapshot:
    path: Path
    size: int
    sha256: str
    stat_key: tuple[int, int, int, int]
    data: bytes | None

    def identity(self, root: Path) -> dict:
        return {"path": self.path.relative_to(root).as_posix(),
                "bytes": self.size, "sha256": self.sha256}


@dataclass(frozen=True)
class CommandResult:
    argv: tuple[str, ...]
    exit_code: int
    stdout: str
    stderr: str


Runner = Callable[[tuple[str, ...], Path, float], CommandResult]


def _stat_key(s: os.stat_result) -> tuple[int, int, int, int]:
    return s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns


def no_symlink_ancestors(path: Path, *, allow_missing_leaf: bool = False) -> None:
    current = Path(path.anchor)
    for i, part in enumerate(path.parts[1:]):
        current /= part
        try:
            info = current.lstat()
        except FileNotFoundError as exc:
            if allow_missing_leaf and i == len(path.parts) - 2:
                return
            raise AuditError(f"Missing input/parent: {current}") from exc
        if stat.S_ISLNK(info.st_mode):
            raise AuditError(f"Symlink input/output refused: {current}")
        if i < len(path.parts) - 2 and not stat.S_ISDIR(info.st_mode):
            raise AuditError(f"Non-directory input parent: {current}")


def owned_path(root: Path, raw: Path, *, fresh: bool = False) -> Path:
    if ".." in raw.parts:
        raise AuditError(f"Parent traversal refused: {raw}")
    path = raw if raw.is_absolute() else root / raw
    path = Path(os.path.abspath(path))
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise AuditError(f"Path escapes --root: {raw}") from exc
    no_symlink_ancestors(path, allow_missing_leaf=fresh)
    if fresh and path.exists():
        raise AuditError(f"--out must be a fresh directory: {path}")
    return path


def casefold_descendant(path: Path, ancestor: Path) -> bool:
    """Conservative component comparison for case-insensitive filesystem aliases."""
    parts = tuple(p.casefold() for p in path.parts)
    base = tuple(p.casefold() for p in ancestor.parts)
    return len(parts) >= len(base) and parts[:len(base)] == base


def normalize_request(request: Request) -> Request:
    if not SHA.fullmatch(request.expected_executable_sha256):
        raise AuditError("Expected executable SHA-256 must be 64 lowercase hex characters")
    if ".." in request.root.parts:
        raise AuditError("Parent traversal in --root refused")
    root = Path(os.path.abspath(request.root))
    no_symlink_ancestors(root)
    if not root.is_dir():
        raise AuditError("--root must be an existing directory")
    build = owned_path(root, request.build)
    app = owned_path(root, request.app)
    out = owned_path(root, request.out, fresh=True)
    if not build.is_dir() or not app.is_dir():
        raise AuditError("--build and --app must be existing directories")
    try:
        app.relative_to(build)
    except ValueError as exc:
        raise AuditError("--app must be inside --build") from exc
    # Publishing must not alter the inspected bundle/build or repository controls.
    if casefold_descendant(out, build) or casefold_descendant(out, app):
        raise AuditError("--out must be outside the inspected build/App")
    relative = out.relative_to(root)
    if relative.parts and relative.parts[0].casefold() in {
        ".git", ".agents", ".codex", "source", "tests", "tools",
        "dependencies", "content", "docs"}:
        raise AuditError("--out cannot publish into source or repository controls")
    historical = (owned_path(root, request.historical_resource_ref)
                  if request.historical_resource_ref is not None else None)
    return Request(root, build, app, request.expected_executable_sha256, out, historical)


def snapshot(path: Path, *, capture: bool = False) -> Snapshot:
    no_symlink_ancestors(path)
    try:
        before = path.lstat()
        if not stat.S_ISREG(before.st_mode):
            raise AuditError(f"Nonregular input refused: {path}")
        if capture and before.st_size > MAX_METADATA_BYTES:
            raise AuditError(f"Metadata input exceeds bounded size: {path}")
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        digest = hashlib.sha256()
        chunks = []
        with os.fdopen(descriptor, "rb") as stream:
            opened = os.fstat(stream.fileno())
            if _stat_key(opened) != _stat_key(before):
                raise AuditError(f"Input replaced before read: {path}")
            captured_size = 0
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
                if capture:
                    captured_size += len(block)
                    if captured_size > MAX_METADATA_BYTES:
                        raise AuditError(f"Metadata grew beyond bounded size: {path}")
                    chunks.append(block)
            closed = os.fstat(stream.fileno())
        after = path.lstat()
        if any(_stat_key(s) != _stat_key(before) for s in (closed, after)):
            raise AuditError(f"Input changed during read: {path}")
        no_symlink_ancestors(path)
        return Snapshot(path, after.st_size, digest.hexdigest(), _stat_key(after),
                        b"".join(chunks) if capture else None)
    except OSError as exc:
        raise AuditError(f"Unable to read exact input {path}: {exc}") from exc


def command_runner(argv: tuple[str, ...], root: Path, timeout: float) -> CommandResult:
    """No shell; 15-second deadline. Temporary stream sizes are checked after exit."""
    try:
        with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
            result = subprocess.run(list(argv), cwd=root, stdout=stdout, stderr=stderr,
                                    timeout=timeout, check=False)
            if stdout.tell() > MAX_COMMAND_BYTES or stderr.tell() > MAX_COMMAND_BYTES:
                raise AuditError("Metadata command exceeded bounded output size")
            stdout.seek(0)
            stderr.seek(0)
            return CommandResult(argv, result.returncode,
                                 stdout.read().decode("utf-8"), stderr.read().decode("utf-8"))
    except (OSError, UnicodeError, subprocess.TimeoutExpired) as exc:
        raise AuditError(f"Metadata command failed/timed out: {argv[0]}: {exc}") from exc


def checked_command(runner: Runner, argv: tuple[str, ...], root: Path) -> CommandResult:
    try:
        result = runner(argv, root, COMMAND_TIMEOUT_SECONDS)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise AuditError(f"Metadata command failed/timed out: {argv[0]}: {exc}") from exc
    if result.argv != argv:
        raise AuditError("Command runner returned a different argv")
    if result.exit_code != 0:
        raise AuditError(f"Metadata command exited {result.exit_code}: {argv}")
    if any(len(text.encode("utf-8")) > MAX_COMMAND_BYTES
           for text in (result.stdout, result.stderr)):
        raise AuditError("Metadata command exceeded bounded output size")
    return result


def parse_otool_dependency_records(text: str, executable: Path) -> list[dict]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != str(executable) + ":":
        raise AuditError("otool -L executable header is missing/contradictory")
    dependencies = []
    numeric = r"[0-9]+(?:\.[0-9]+){0,2}"
    pattern = re.compile(r"^\s+(.+?)\s+\(compatibility version (" + numeric
                         + r"), current version (" + numeric + r")(, weak)?\)\s*$")
    for line in lines[1:]:
        match = pattern.fullmatch(line)
        if match is None:
            raise AuditError(f"Unparsed otool -L dependency row: {line!r}")
        path = match.group(1)
        if (not path or any(ord(c) < 32 for c in path)
                or not path.startswith(("/", "@rpath/", "@loader_path/", "@executable_path/"))):
            raise AuditError(f"Invalid otool -L dependency path: {path!r}")
        dependencies.append({"path": path, "compatibility_version": match.group(2),
                             "current_version": match.group(3), "weak": match.group(4) is not None})
    if not dependencies:
        raise AuditError("otool -L dependency list is empty")
    return dependencies


def parse_otool_dependencies(text: str, executable: Path) -> list[str]:
    return [r["path"] for r in parse_otool_dependency_records(text, executable)]


def serialize_document(value: object, label: str) -> str:
    """Validate JSON types and bound serialization before creating output files."""
    chunks = []
    size = 1  # Final newline.
    try:
        encoder = json.JSONEncoder(indent=2, ensure_ascii=False, allow_nan=False)
        for chunk in encoder.iterencode(value):
            size += len(chunk.encode("utf-8"))
            if size > MAX_OUTPUT_DOCUMENT_BYTES:
                raise AuditError(f"Serialized {label} exceeds bounded document size")
            chunks.append(chunk)
    except AuditError:
        raise
    except (TypeError, ValueError, UnicodeError, RecursionError, OverflowError) as exc:
        raise AuditError(f"Unsupported JSON value in {label}: {exc}") from exc
    return "".join(chunks) + "\n"


def parse_load_version(text: str, executable: Path) -> dict:
    lines = text.splitlines()
    if not lines or lines[0].strip() != str(executable) + ":":
        raise AuditError("otool -l executable header is missing/contradictory")
    blocks = re.split(r"(?m)^Load command [0-9]+\s*$", "\n".join(lines[1:]))[1:]
    versions = [b for b in blocks if re.search(
        r"(?m)^\s*cmd (LC_BUILD_VERSION|LC_VERSION_MIN_MACOSX)\s*$", b)]
    if len(versions) != 1:
        raise AuditError("Expected exactly one Mach-O platform version command")
    block = versions[0]
    modern = "LC_BUILD_VERSION" in block
    minimum_field = "minos" if modern else "version"
    minimum = re.findall(r"(?m)^\s*" + minimum_field + r" ([0-9]+(?:\.[0-9]+){1,2})\s*$", block)
    sdk = re.findall(r"(?m)^\s*sdk ([0-9]+(?:\.[0-9]+){1,2})\s*$", block)
    if len(minimum) != 1 or len(sdk) != 1:
        raise AuditError("Missing/ambiguous Mach-O minimum/SDK fields")
    if modern and re.findall(r"(?m)^\s*platform (\S+)\s*$", block) != ["1"]:
        raise AuditError("Expected macOS LC_BUILD_VERSION platform 1")
    return {"load_command": "LC_BUILD_VERSION" if modern else "LC_VERSION_MIN_MACOSX",
            "configured_load_command_minimum": minimum[0], "build_sdk": sdk[0],
            "minimum_supported_OS_observed": False}


def parse_cache(data: bytes, root: Path, build: Path) -> dict:
    try:
        text = data.decode("utf-8")
    except UnicodeError as exc:
        raise AuditError("CMakeCache is not UTF-8") from exc
    values: dict[str, str] = {}
    wanted = {"CMAKE_HOME_DIRECTORY", "Fathom_SOURCE_DIR", "Fathom_BINARY_DIR",
              "CMAKE_BUILD_TYPE", "CMAKE_OSX_DEPLOYMENT_TARGET", "CMAKE_OSX_SYSROOT"}
    for line in text.splitlines():
        match = re.fullmatch(r"([^:#]+):[^=]+=(.*)", line)
        if match and match.group(1) in wanted:
            key, value = match.groups()
            if key in values:
                raise AuditError(f"Duplicate/ambiguous CMakeCache key: {key}")
            values[key] = value
    expected = {"CMAKE_HOME_DIRECTORY": root, "Fathom_SOURCE_DIR": root,
                "Fathom_BINARY_DIR": build}
    for key, path in expected.items():
        if values.get(key) != str(path):
            raise AuditError(f"CMakeCache missing/contradictory {key}")
    if not values.get("CMAKE_BUILD_TYPE"):
        raise AuditError("CMakeCache build configuration missing/empty")
    return values


def parse_link(data: bytes, root: Path, build: Path, executable: Path) -> dict:
    try:
        argv = shlex.split(data.decode("utf-8"), posix=True)
    except (UnicodeError, ValueError) as exc:
        raise AuditError("Invalid literal link recipe") from exc
    if not argv or not Path(argv[0]).is_absolute() or any(
            token in {";", "&&", "||", "|", ">", "<"} for token in argv):
        raise AuditError("Link recipe is not one literal compiler argv")
    positions = [i for i, arg in enumerate(argv) if arg == "-o"]
    if len(positions) != 1 or positions[0] + 1 >= len(argv):
        raise AuditError("Link recipe requires exactly one explicit -o output")
    destination = owned_path(root, build / argv[positions[0] + 1])
    if destination != executable:
        raise AuditError("Link recipe -o output contradicts --app executable")
    archives = sorted(set(arg for arg in argv if re.fullmatch(r"libfathom_[A-Za-z0-9_]+\.a", arg)))
    if not archives:
        raise AuditError("No parsed Fathom archives in link recipe")
    return {"compiler_argv_observed_not_executed": argv,
            "unique_project_static_archives_in_recipe": archives,
            "SQLite_static_link_recipe_present": "libfathom_sqlite.a" in archives}


def parse_compile_definitions(data: bytes) -> dict:
    try:
        groups = {}
        wanted = {"JUCE_WEB_BROWSER", "JUCE_USE_CURL"}
        for line in data.decode("utf-8").splitlines():
            match = re.fullmatch(r"(C|CXX|OBJCXX)_DEFINES\s*=\s*(.*)", line)
            if not match:
                continue
            language, text = match.groups()
            if language in groups:
                raise AuditError("Duplicate compile-definition group")
            group = {}
            for token in shlex.split(text):
                definition = re.fullmatch(r"-D([^=]+)=(.*)", token)
                if definition and definition.group(1) in wanted:
                    key, value = definition.groups()
                    if key in group and group[key] != value:
                        raise AuditError(f"Contradictory compile definition: {key}")
                    group[key] = value
            groups[language] = group
        if not groups:
            raise AuditError("No parsed compile-definition groups")
        for key in wanted:
            observed = {g[key] for g in groups.values() if key in g}
            if len(observed) > 1:
                raise AuditError(f"Contradictory compile definition across languages: {key}")
        return {"observed_language_definition_groups": groups,
                "JUCE_web_browser_explicitly_zero_in_all_observed_groups":
                    all(g.get("JUCE_WEB_BROWSER") == "0" for g in groups.values()),
                "JUCE_curl_explicitly_zero_in_all_observed_groups":
                    all(g.get("JUCE_USE_CURL") == "0" for g in groups.values())}
    except (UnicodeError, ValueError) as exc:
        raise AuditError(f"Invalid compile-definition metadata: {exc}") from exc


def parse_historical_ref(data: bytes) -> dict:
    try:
        value = json.loads(data)
        ref = value["artifact_ref"]
        path = ref["path"]
        pure = PurePosixPath(path)
        when = dt.datetime.fromisoformat(value["as_of_utc"].replace("Z", "+00:00"))
        valid = (isinstance(path, str) and path and not pure.is_absolute()
                 and all(p not in {"", ".", ".."} for p in path.split("/"))
                 and "\\" not in path and "\x00" not in path
                 and type(ref["bytes"]) is int and ref["bytes"] >= 0
                 and isinstance(ref["sha256"], str) and SHA.fullmatch(ref["sha256"])
                 and isinstance(value["resource_sha256"], str)
                 and SHA.fullmatch(value["resource_sha256"]) and when.utcoffset() == dt.timedelta(0))
        if not valid:
            raise ValueError("Invalid historical resource identity")
        return {"artifact_ref": {k: ref[k] for k in ("path", "bytes", "sha256")},
                "resource_sha256": value["resource_sha256"], "as_of_utc": value["as_of_utc"],
                "basis": "historical_cached_metadata_only; referenced artifact not reread"}
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        raise AuditError("Invalid historical resource-ref metadata") from exc


def collect(request: Request, *, runner: Runner = command_runner) -> tuple[Request, dict, list[dict]]:
    request = normalize_request(request)
    root, build, app = request.root, request.build, request.app
    started = dt.datetime.now(dt.timezone.utc).isoformat()
    before: dict[Path, Snapshot] = {}
    plist_path = owned_path(root, app / "Contents/Info.plist")
    before[plist_path] = snapshot(plist_path, capture=True)
    try:
        plist = plistlib.loads(before[plist_path].data)
    except (plistlib.InvalidFileException, ValueError, TypeError) as exc:
        raise AuditError("Invalid guarded Info.plist") from exc
    if not isinstance(plist, dict):
        raise AuditError("Info.plist must be a dictionary")
    # Legal plist bytes/dates have no issued JSON representation in this CLI.
    # Reject them explicitly before commands or publication rather than silently
    # discarding typed meaning or failing after writing a partial result.
    serialize_document(plist, "guarded Info.plist")
    basename = plist.get("CFBundleExecutable")
    if (not isinstance(basename, str) or not basename or basename in {".", ".."}
            or any(c in basename for c in ("/", "\\", "\x00", "\n", "\r"))):
        raise AuditError("Info.plist executable basename missing/invalid")
    executable = owned_path(root, app / "Contents/MacOS" / basename)
    cache_path = build / "CMakeCache.txt"
    flags_path = build / "CMakeFiles/Fathom.dir/flags.make"
    link_path = build / "CMakeFiles/Fathom.dir/link.txt"
    paths = [executable, app / "Contents/PkgInfo", cache_path, flags_path, link_path,
             root / "CMakeLists.txt", root / "CMakePresets.json",
             root / "Dependencies/lock.json", root / "Dependencies/NOTICE.md"]
    if request.historical_resource_ref is not None:
        paths.append(request.historical_resource_ref)
    capture_paths = {cache_path, flags_path, link_path, request.historical_resource_ref}
    for path in paths:
        path = owned_path(root, path)
        if path in before:
            raise AuditError("Historical resource input aliases another guarded input")
        before[path] = snapshot(path, capture=path in capture_paths)
    if before[executable].sha256 != request.expected_executable_sha256:
        raise AuditError("Selected executable SHA-256 drift; do not retarget automatically")
    cache = parse_cache(before[cache_path].data, root, build)
    recipe = parse_link(before[link_path].data, root, build, executable)
    definitions = parse_compile_definitions(before[flags_path].data)
    historical = (parse_historical_ref(before[request.historical_resource_ref].data)
                  if request.historical_resource_ref is not None else None)
    commands = [
        ("/usr/bin/git", "-C", str(root), "rev-parse", "--show-toplevel"),
        ("/usr/bin/sw_vers",), ("/usr/bin/uname", "-m"),
        ("/usr/bin/file", str(executable)), ("/usr/bin/lipo", "-archs", str(executable)),
        ("/usr/bin/otool", "-L", str(executable)), ("/usr/bin/otool", "-l", str(executable)),
        ("/usr/bin/codesign", "-d", "--verbose=4", str(app)),
    ]
    results = [checked_command(runner, commands[0], root)]
    if results[0].stdout.strip() != str(root):
        raise AuditError("--root contradicts the Git checkout top level")
    results.extend(checked_command(runner, command, root) for command in commands[1:])
    architectures = results[4].stdout.strip().split()
    if not architectures or any(a not in {"arm64", "arm64e", "x86_64", "i386"} for a in architectures):
        raise AuditError("Missing/unparsed lipo architectures")
    dependency_records = parse_otool_dependency_records(results[5].stdout, executable)
    dependencies = [r["path"] for r in dependency_records]
    version = parse_load_version(results[6].stdout, executable)
    signature_display = results[7].stderr + results[7].stdout
    if not signature_display.strip():
        raise AuditError("Missing codesign display output; no signature fact inferred")
    for path, old in before.items():
        current = snapshot(path)
        if (current.size, current.sha256, current.stat_key) != (old.size, old.sha256, old.stat_key):
            raise AuditError(f"Guarded input changed during collection: {path}")
    # Use captured guarded bytes above; no plist/cache/link reread after this guard.
    finished = dt.datetime.now(dt.timezone.utc).isoformat()
    metadata = {
        "schema": "fathom.bounded-release-build-metadata.1",
        "started_utc": started, "finished_utc": finished,
        "selected_executable": before[executable].identity(root),
        "Info_plist": plist, "architectures": architectures,
        "build_cache_selection": cache, "MachO_build_version": version,
        "link_recipe": recipe, "dynamic_load_paths": dependencies,
        "dynamic_load_records": dependency_records,
        "dynamic_load_path_count": len(dependencies),
        "all_dynamic_load_paths_in_system_directories": all(
            p.startswith(("/System/Library/", "/usr/lib/")) for p in dependencies),
        "compile_definitions": definitions,
        "signature_display_only": signature_display,
        "fresh_guarded_input_refs": [s.identity(root) for s in before.values()],
        "inputs_before_after_equal": True, "metadata_commands": len(results),
        "command_timeout_seconds": COMMAND_TIMEOUT_SECONDS,
        "temporary_command_stream_limit_bytes_checked_after_exit": MAX_COMMAND_BYTES,
        "command_streams_actively_byte_capped_during_execution": False,
        "historical_resource_metadata": historical,
        "resource_walks": 0, "whole_resources_rehashed": False,
        "current_whole_bundle_equality_claim": False,
        "product_builds_launches_tests_GUI_profile_actions": 0,
        "strict_signature_verification_run": False, "Gatekeeper_assessment_run": False,
        "acceptance_increment": 0,
        "limits": ["Display/build facts only; no signing/trust/redistribution decision.",
                   "No minimum-supported-OS, clean-install, offline/request or listening observation.",
                   "Current artifact facts apply only at this guarded snapshot; cached resources are not fresh equality proof."],
    }
    readback = [{"argv": list(r.argv), "exit_code": r.exit_code,
                 "stdout": r.stdout, "stderr": r.stderr} for r in results]
    return request, metadata, readback


def publish(request: Request, metadata: dict, readback: list[dict]) -> None:
    # Recheck parent custody and freshness at publication, including concurrent output creation.
    owned_path(request.root, request.out, fresh=True)
    serialized = [("metadata-command-readback.json", serialize_document(readback, "command readback")),
                  ("current-build-metadata.json", serialize_document(metadata, "metadata"))]
    try:
        request.out.mkdir()
    except OSError as exc:
        raise AuditError(f"Fresh output creation failed: {request.out}: {exc}") from exc
    descriptor = None
    try:
        descriptor = os.open(request.out, os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0))
        if _stat_key(os.fstat(descriptor)) != _stat_key(request.out.lstat()):
            raise AuditError("Owned output directory changed before publication")
        for name, text in serialized:
            leaf = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
                           0o600, dir_fd=descriptor)
            with os.fdopen(leaf, "w", encoding="utf-8") as stream:
                stream.write(text)
    except OSError as exc:
        raise AuditError(f"Incomplete owned output at {request.out}: {exc}") from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)


def main(argv: list[str] | None = None, *, runner: Runner = command_runner) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--build", required=True, type=Path)
    parser.add_argument("--app", required=True, type=Path)
    parser.add_argument("--expected-executable-sha256", required=True)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--historical-resource-ref", type=Path)
    args = parser.parse_args(argv)
    try:
        request, metadata, readback = collect(Request(**vars(args)), runner=runner)
        publish(request, metadata, readback)
    except (AuditError, UnicodeError) as exc:
        print(f"METADATA STOP: {exc}", file=__import__("sys").stderr)
        return 2
    print(f"METADATA OBSERVED {request.out} commands={len(readback)} "
          f"inputs={len(metadata['fresh_guarded_input_refs'])} resources_walked=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
