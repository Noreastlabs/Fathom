#!/usr/bin/env python3
"""Write compact, relocatable Fathom evidence references and repository summaries.

This tool records artifact identity without copying it. If physical custody is
required, `store` places one verified object at Evidence/objects/<sha256> and
writes a small reference manifest under Results. `audit` rejects recursive
Results packaging and reports logical/allocated size and duplicate bytes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any


SCHEMA = "fathom-evidence-reference.1"
FORBIDDEN_RECURSIVE_DIRS = {"Results", ".git", "DerivedData", "node_modules"}


def fail(message: str) -> "NoReturn":
    raise SystemExit(f"evidence error: {message}")


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def hash_file(path: Path) -> tuple[int, str, int]:
    size = 0
    allocated = 0
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            size += len(chunk)
            digest.update(chunk)
    try:
        allocated = path.stat().st_blocks * 512
    except (AttributeError, OSError):
        allocated = size
    return size, digest.hexdigest(), allocated


def repo_root(value: Path) -> Path:
    root = value.resolve(strict=True)
    result = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        fail(f"not a Git checkout: {root}")
    actual = Path(result.stdout.strip()).resolve(strict=True)
    if actual != root:
        fail(f"--root must name the Git top-level directory: {actual}")
    return root


def safe_relative_path(root: Path, value: Path, label: str, must_exist: bool = True) -> Path:
    candidate = value if value.is_absolute() else root / value
    try:
        relative = candidate.relative_to(root) if candidate.is_absolute() else value
    except ValueError:
        fail(f"{label} must be expressed inside the repository: {value}")
    if ".." in relative.parts:
        fail(f"{label} may not traverse a parent path: {value}")
    current = root
    for part in relative.parts:
        if part in ("", "."):
            continue
        current = current / part
        if current.is_symlink():
            fail(f"{label} traverses a symlink: {value}")
    try:
        resolved = candidate.resolve(strict=must_exist)
        resolved.relative_to(root)
    except (OSError, ValueError):
        fail(f"{label} must resolve inside the repository: {value}")
    if candidate.is_symlink():
        fail(f"{label} may not be a symlink: {value}")
    return resolved


def safe_results_output(root: Path, value: Path) -> Path:
    output = safe_relative_path(root, value, "output path", must_exist=False)
    results_path = root / "Results"
    if results_path.is_symlink():
        fail("Results/ may not be a symlink")
    results = results_path.resolve(strict=True)
    if output == results or results not in output.parents:
        fail(f"output must be below Results/: {output}")
    if output.exists():
        fail(f"refusing to overwrite existing output: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    return output


def git_value(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        fail(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def artifact_identity(root: Path, value: str, role: str) -> dict[str, Any]:
    if not role.strip():
        fail("artifact role must be non-empty")
    path = Path(value)
    if not path.is_absolute():
        path = root / path
    if path.is_symlink():
        fail(f"artifact may not be a symlink: {value}")
    try:
        resolved = path.resolve(strict=True)
    except OSError as error:
        fail(f"cannot resolve artifact {value}: {error}")
    if path.is_absolute() and root in path.parents:
        safe_relative_path(root, path, "artifact path", must_exist=True)
    try:
        repo_relative = resolved.relative_to(root).as_posix()
        location: dict[str, str] = {"path": repo_relative}
    except ValueError:
        location = {"external_path": str(resolved)}

    if resolved.is_file():
        size, sha, allocated = hash_file(resolved)
        return {
            **location,
            "kind": "file",
            "role": role.strip(),
            "bytes": size,
            "allocated_bytes": allocated,
            "sha256": sha,
        }
    if not resolved.is_dir():
        fail(f"artifact must be a regular file or directory: {value}")

    files: list[dict[str, Any]] = []
    for child in sorted(resolved.rglob("*"), key=lambda item: item.relative_to(resolved).as_posix()):
        if child.is_symlink():
            fail(f"directory artifact contains symlink: {child}")
        if not child.is_file():
            continue
        size, sha, allocated = hash_file(child)
        files.append({
            "path": child.relative_to(resolved).as_posix(),
            "bytes": size,
            "allocated_bytes": allocated,
            "sha256": sha,
        })
    tree = hashlib.sha256()
    for item in files:
        row = f"{item['path']}\0{item['bytes']}\0{item['sha256']}\n".encode("utf-8")
        tree.update(row)
    return {
        **location,
        "kind": "directory_tree",
        "role": role.strip(),
        "bytes": sum(item["bytes"] for item in files),
        "allocated_bytes": sum(item["allocated_bytes"] for item in files),
        "file_count": len(files),
        "sha256": tree.hexdigest(),
    }


def write_json_fresh(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    with path.open("xb") as stream:
        stream.write(encoded)


def cmd_manifest(args: argparse.Namespace) -> int:
    root = repo_root(args.root)
    output = safe_results_output(root, args.output)
    if not args.artifact:
        fail("provide at least one --artifact PATH|ROLE")
    artifacts = []
    for item in args.artifact:
        if "|" not in item:
            fail("--artifact must use PATH|ROLE syntax")
        path, role = item.rsplit("|", 1)
        artifacts.append(artifact_identity(root, path, role))
    seen: set[tuple[str, str]] = set()
    for item in artifacts:
        key = (item.get("path") or item.get("external_path", ""), item["role"])
        if key in seen:
            fail(f"duplicate artifact reference: {key[0]}")
        seen.add(key)
    value = {
        "schema_version": SCHEMA,
        "git_head": git_value(root, "rev-parse", "HEAD"),
        "git_branch": git_value(root, "branch", "--show-current"),
        "artifacts": artifacts,
    }
    write_json_fresh(output, value)
    print(f"MANIFEST PASS {output} artifacts={len(artifacts)}")
    return 0


def cmd_git_summary(args: argparse.Namespace) -> int:
    root = repo_root(args.root)
    for scope in args.scope:
        path = Path(scope)
        if path.is_absolute() or ".." in path.parts or scope.startswith(":"):
            fail(f"Git summary scope must be a repository-relative literal path: {scope}")
    output = safe_results_output(root, args.output)
    command = ["git", "-C", str(root), "status", "--porcelain=v1", "-z", "--untracked-files=all"]
    if args.scope:
        command.extend(["--", *args.scope])
    result = subprocess.run(command, capture_output=True, check=False)
    if result.returncode != 0:
        fail(f"git status failed: {result.stderr.decode(errors='replace')}")
    records = [entry for entry in result.stdout.split(b"\0") if entry]
    tracked: list[dict[str, str]] = []
    untracked: list[str] = []
    rename_sources: dict[int, str] = {}
    index = 0
    while index < len(records):
        entry = records[index]
        index += 1
        if len(entry) < 4:
            continue
        xy = entry[:2].decode("ascii", errors="replace")
        path = entry[3:].decode("utf-8", errors="replace")
        if xy == "??":
            untracked.append(path)
        else:
            if "R" in xy or "C" in xy:
                if index < len(records):
                    previous_path = records[index].decode("utf-8", errors="replace")
                    tracked.append({"status": xy, "path": path, "previous_path": previous_path})
                index += 1
            else:
                tracked.append({"status": xy, "path": path})
    tracked.sort(key=lambda item: (item["path"], item["status"]))
    untracked.sort()
    value = {
        "schema_version": SCHEMA,
        "git_head": git_value(root, "rev-parse", "HEAD"),
        "git_branch": git_value(root, "branch", "--show-current"),
        "status_digest_sha256": digest_bytes(result.stdout),
        "tracked_changes": tracked,
        "untracked_file_count": len(untracked),
        "untracked_paths_sha256": digest_bytes("\n".join(untracked).encode("utf-8")),
        "untracked_paths": untracked if args.scope else None,
        "scope": args.scope or ["<repository>"],
    }
    write_json_fresh(output, value)
    print(
        f"GIT SUMMARY PASS {output} head={value['git_head']} "
        f"tracked={len(tracked)} untracked={len(untracked)} "
        f"status_sha256={value['status_digest_sha256']}"
    )
    return 0


def cmd_store(args: argparse.Namespace) -> int:
    root = repo_root(args.root)
    if not args.role.strip() or not args.reason.strip():
        fail("content-addressed retention requires a role and a concrete reason")
    source = Path(args.source)
    if not source.is_absolute():
        source = root / source
    if source.is_symlink():
        fail("content-addressed storage refuses symlink sources")
    try:
        if source.is_absolute() and root in source.parents:
            source = safe_relative_path(root, source, "source path", must_exist=True)
        else:
            source = source.resolve(strict=True)
    except OSError as error:
        fail(f"cannot resolve source: {error}")
    if source.is_symlink() or not source.is_file():
        fail("content-addressed storage accepts a regular file, not a symlink or directory")
    output = safe_relative_path(root, args.manifest, "manifest path", must_exist=False)
    results = root / "Results"
    if results.is_symlink():
        fail("Results/ may not be a symlink")
    results = results.resolve(strict=True)
    if results not in output.parents or output.is_symlink():
        fail("manifest path must be a new or existing regular file under Results/")
    if output.exists():
        try:
            manifest = json.loads(output.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            fail(f"existing reference manifest is invalid: {output}")
        if manifest.get("schema_version") != SCHEMA:
            fail(f"unsupported existing reference manifest: {output}")
    else:
        manifest = {
            "schema_version": SCHEMA,
            "git_head": git_value(root, "rev-parse", "HEAD"),
            "git_branch": git_value(root, "branch", "--show-current"),
            "artifacts": [],
        }

    size, sha, _ = hash_file(source)
    object_relative = f"Evidence/objects/{sha}"
    if any(item.get("object_path") == object_relative for item in manifest["artifacts"]):
        fail(f"object already referenced by manifest: {object_relative}")
    output.parent.mkdir(parents=True, exist_ok=True)
    objects = root / "Evidence" / "objects"
    if (root / "Evidence").is_symlink() or objects.is_symlink():
        fail("Evidence/objects may not be a symlink")
    objects.mkdir(parents=True, exist_ok=True)
    destination = objects / sha
    reused = destination.exists()
    if reused:
        if destination.is_symlink():
            fail(f"existing content-addressed object is a symlink: {destination}")
        existing_size, existing_sha, _ = hash_file(destination)
        if existing_size != size or existing_sha != sha:
            fail(f"existing content-addressed object failed verification: {destination}")
    else:
        temp = objects / f".{sha}.partial-{os.getpid()}"
        try:
            with source.open("rb") as src, temp.open("xb") as dst:
                shutil.copyfileobj(src, dst, length=1024 * 1024)
                dst.flush()
                os.fsync(dst.fileno())
            copied_size, copied_sha, _ = hash_file(temp)
            if copied_size != size or copied_sha != sha:
                fail("copied object did not match source")
            os.replace(temp, destination)
        finally:
            if temp.exists():
                temp.unlink()

    source_identity = artifact_identity(root, str(source), args.role)
    record = {
        **source_identity,
        "custody": "content_addressed_object",
        "object_path": f"Evidence/objects/{sha}",
        "object_reused": reused,
        "retention_reason": args.reason.strip(),
    }
    manifest["artifacts"].append(record)
    encoded = (json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    temporary = output.with_name(output.name + f".tmp-{os.getpid()}")
    with temporary.open("xb") as stream:
        stream.write(encoded)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, output)
    print(
        f"STORE PASS {destination} bytes={size} sha256={sha} "
        f"reused={str(reused).lower()} manifest={output}"
    )
    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    root = repo_root(args.root)
    evidence = safe_relative_path(root, args.evidence_dir, "evidence directory")
    results = (root / "Results").resolve(strict=True)
    if results not in evidence.parents or not evidence.is_dir():
        fail("evidence directory must be a directory below Results/")
    files: list[tuple[Path, int, int, str]] = []
    symlink_references: list[dict[str, Any]] = []
    recursive_directories: list[str] = []
    for current, dirs, names in os.walk(evidence, followlinks=False):
        current_path = Path(current)
        for name in list(dirs):
            child = current_path / name
            relative = child.relative_to(evidence).as_posix()
            if name in FORBIDDEN_RECURSIVE_DIRS:
                recursive_directories.append(relative)
            if child.is_symlink():
                symlink_references.append({
                    "path": relative,
                    "target": os.readlink(child),
                    "target_exists": child.exists(),
                })
        for name in names:
            path = current_path / name
            if path.is_symlink():
                symlink_references.append({
                    "path": path.relative_to(evidence).as_posix(),
                    "target": os.readlink(path),
                    "target_exists": path.exists(),
                })
                continue
            if not path.is_file():
                fail(f"evidence tree contains a non-regular artifact: {path.relative_to(evidence)}")
            size, sha, allocated = hash_file(path)
            files.append((path, size, allocated, sha))
    material_recursive = [
        directory
        for directory in recursive_directories
        if any(
            path.relative_to(evidence).as_posix() == directory
            or path.relative_to(evidence).as_posix().startswith(directory + "/")
            for path, _, _, _ in files
        )
    ]
    if material_recursive:
        fail(f"RECURSIVE_RESULTS_OR_TOOLING_TREE {sorted(material_recursive)}")

    by_hash: dict[str, list[Path]] = {}
    for path, _, _, sha in files:
        by_hash.setdefault(sha, []).append(path.relative_to(evidence))
    duplicate_groups = []
    for sha, paths in sorted(by_hash.items()):
        if len(paths) > 1:
            size = next(item[1] for item in files if item[3] == sha)
            duplicate_groups.append({
                "sha256": sha,
                "copies": len(paths),
                "duplicate_bytes": size * (len(paths) - 1),
                "paths": [path.as_posix() for path in paths],
            })
    largest = sorted(files, key=lambda item: item[1], reverse=True)[:10]
    value = {
        "schema_version": SCHEMA,
        "evidence_path": evidence.relative_to(root).as_posix(),
        "file_count": len(files),
        "logical_bytes": sum(item[1] for item in files),
        "allocated_bytes": sum(item[2] for item in files),
        "duplicate_bytes_within_package": sum(item["duplicate_bytes"] for item in duplicate_groups),
        "recursive_reference_directories": sorted(recursive_directories),
        "symlink_reference_count": len(symlink_references),
        "dangling_symlink_reference_count": sum(not item["target_exists"] for item in symlink_references),
        "symlink_reference_samples": symlink_references[:10],
        "duplicate_groups": duplicate_groups,
        "largest_files": [
            {"path": path.relative_to(evidence).as_posix(), "bytes": size, "sha256": sha}
            for path, size, _, sha in largest
        ],
    }
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    manifest = subparsers.add_parser("manifest", help="record artifact identities without copying bytes")
    manifest.add_argument("--root", type=Path, required=True)
    manifest.add_argument("--output", type=Path, required=True)
    manifest.add_argument("--artifact", action="append", default=[], metavar="PATH|ROLE")
    manifest.set_defaults(function=cmd_manifest)

    summary = subparsers.add_parser("git-summary", help="record compact Git identity and state")
    summary.add_argument("--root", type=Path, required=True)
    summary.add_argument("--output", type=Path, required=True)
    summary.add_argument("--scope", action="append", default=[], help="optional repository-relative pathspec")
    summary.set_defaults(function=cmd_git_summary)

    store = subparsers.add_parser("store", help="retain one required immutable file by SHA-256")
    store.add_argument("--root", type=Path, required=True)
    store.add_argument("--source", required=True)
    store.add_argument("--role", required=True)
    store.add_argument("--reason", required=True)
    store.add_argument("--manifest", type=Path, required=True)
    store.set_defaults(function=cmd_store)

    audit = subparsers.add_parser("audit", help="measure evidence and reject recursive Results packaging")
    audit.add_argument("--root", type=Path, required=True)
    audit.add_argument("--evidence-dir", type=Path, required=True)
    audit.set_defaults(function=cmd_audit)
    return parser


def main() -> int:
    args = make_parser().parse_args()
    return int(args.function(args))


if __name__ == "__main__":
    sys.exit(main())
