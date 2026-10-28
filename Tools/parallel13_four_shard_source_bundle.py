#!/usr/bin/env python3
"""Build and independently verify the sealed P02 four-shard source bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
OUT = Path("Build/parallel-13/four-shard-source-bundle-r01")
BUNDLE = OUT / "bundle"
P02 = Path("Build/parallel-02/four-real-shard-manifest-r01")
P02_PINS = {
    "manifest.json": "01967090d337c7154211ddd8e6926a9d67aa1ed2a7eda0e37b662d0b52aa33e8",
    "summary.json": "a3072fc6074d812c3b59fd5cc002da34813be9fb98abe3efe79967b06ca140fa",
}
GLOBAL = Path("Tools/parallel10_global_shard_verifier.py")
GLOBAL_PIN = "896785c05fc95514a0e812e445498d8eb49907dada16a864f44fb91dc615a14c"
NATIVE_ORIGIN = Path("Build/parallel-10/2.3-legacy-id-reconciliation-r01/cmake/fathom_content_validate")
NATIVE_BUNDLE = Path("bin/fathom_content_validate")
NATIVE_PIN = "a85c1b25d8cded12cbe273e4620bd5f33a711d06311d29583a0fdbed7748f714"
INVENTORY = "bundle-inventory.json"
EXPECTED_COUNTS = {"records": 432, "entities": 2812, "events": 27648,
                   "sources": 596, "variants": 1944}


class BundleError(ValueError):
    pass


def need(ok: bool, code: str) -> None:
    if not ok:
        raise BundleError(code)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def encoded(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":")) + "\n").encode()


def relative(value: str) -> Path:
    p = Path(value)
    need(bool(value) and not p.is_absolute() and "\\" not in value and
         all(x not in ("", ".", "..") for x in p.parts) and
         str(p) == value, f"PATH_UNSAFE {value}")
    return p


def regular(root: Path, rel: str) -> Path:
    p = relative(rel)
    cur = root
    for part in p.parts:
        cur = cur / part
        need(not cur.is_symlink(), f"SYMLINK {rel}")
    need(cur.is_file() and cur.resolve().is_relative_to(root.resolve()),
         f"MISSING {rel}")
    return cur


def origin_file(root: Path, rel: str) -> tuple[Path, str]:
    """Resolve four historical Results aliases without following a symlink."""
    try:
        return regular(root, rel), rel
    except BundleError as exc:
        if not str(exc).startswith("MISSING ") or not rel.startswith("Results/"):
            raise
        canonical = "Results/primary/" + rel[len("Results/"):]
        return regular(root, canonical), canonical


def digest_file(path: Path) -> tuple[int, str]:
    h = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            h.update(block)
            size += len(block)
    return size, h.hexdigest()


def collect(root: Path) -> dict[str, dict]:
    """Enumerate only the transitive references used by native and global checks."""
    refs: dict[str, dict] = {}

    def add(rel: str, role: str, expected: str | None = None) -> None:
        relative(rel)
        p, provenance = origin_file(root, rel)
        size, actual = digest_file(p)
        need(expected is None or actual == expected, f"PIN_DRIFT {rel}")
        if rel in refs:
            need(refs[rel]["sha256"] == actual and refs[rel]["bytes"] == size,
                 f"DUPLICATE_DRIFT {rel}")
            refs[rel]["roles"].append(role)
        else:
            refs[rel] = {"bytes": size, "sha256": actual,
                         "source_path": provenance, "roles": [role]}

    for name, pin in P02_PINS.items():
        add(str(P02 / name), "sealed_p02_" + name, pin)
    manifest = json.loads(origin_file(root, str(P02 / "manifest.json"))[0].read_text())
    need(manifest["validated_workbooks"] == [7, 8, 10, 11] and
         manifest["admitted"] is False and manifest["aggregate_complete"] is False and
         len(manifest["shards"]) == 4, "P02_SCOPE")
    for role, ref in manifest["foundation"].items():
        add(ref["path"], "foundation_" + role, ref["sha256"])
    add(manifest["completion_contract"]["path"], "completion_contract",
        manifest["completion_contract"]["sha256"])
    source_files: set[str] = set()
    for shard in manifest["shards"]:
        level = shard["legacy_level"]
        need(level in (7, 8, 10, 11), "SHARD_LEVEL")
        artifacts = shard["artifacts"]
        for role, ref in artifacts.items():
            add(ref["path"], f"level{level:03d}_{role}", ref["sha256"])
        package = json.loads(origin_file(root, artifacts["package"]["path"])[0].read_text())
        profile = json.loads(origin_file(root, artifacts["profile"]["path"])[0].read_text())
        add(package["source_acceptance"], f"level{level:03d}_source_acceptance")
        for source in package["sources"].values():
            path = source["path"]
            need(source["format"] in ("txt", "pdf") and
                 path.startswith("Notes/") and path.lower().endswith("." + source["format"]),
                 "SOURCE_FORMAT")
            add(path, f"level{level:03d}_source_asset", source["sha256"])
            source_files.add(path)
        plan = profile["resource_plan"]
        add(plan["path"], f"level{level:03d}_resource_plan", plan["sha256"])
        for authority in profile["authority_artifacts"]:
            add(authority["path"], f"level{level:03d}_authority_{authority['role']}",
                authority["sha256"])
    need(len(source_files) == 8 and
         sum(p.lower().endswith(".txt") for p in source_files) == 4 and
         sum(p.lower().endswith(".pdf") for p in source_files) == 4,
         "SOURCE_SET")
    add(str(GLOBAL), "frozen_global_verifier", GLOBAL_PIN)
    p = regular(root, str(NATIVE_ORIGIN))
    size, actual = digest_file(p)
    need(actual == NATIVE_PIN, "NATIVE_PIN")
    refs[str(NATIVE_BUNDLE)] = {"bytes": size, "sha256": actual,
                                "source_path": str(NATIVE_ORIGIN),
                                "roles": ["frozen_native_validator"]}
    return {k: {**v, "roles": sorted(set(v["roles"]))} for k, v in sorted(refs.items())}


def inventory_for(root: Path) -> dict:
    refs = collect(root)
    return {"schema": "fathom-four-shard-source-bundle.1",
            "sealed_manifest_sha256": P02_PINS["manifest.json"],
            "sealed_summary_sha256": P02_PINS["summary.json"],
            "validated_workbooks": [7, 8, 10, 11],
            "aggregate_complete": False, "admitted": False,
            "runtime_admission": False, "files": refs}


def build() -> dict:
    need(not (ROOT / OUT).exists() and not (ROOT / OUT).is_symlink(), "OUTPUT_EXISTS")
    inventory = inventory_for(ROOT)
    bundle = ROOT / BUNDLE
    try:
        for rel, entry in inventory["files"].items():
            source = regular(ROOT, entry["source_path"])
            target = bundle / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target, follow_symlinks=False)
            need(digest_file(target) == (entry["bytes"], entry["sha256"]),
                 f"COPY_DRIFT {rel}")
        (bundle / NATIVE_BUNDLE).chmod(0o755)
        (bundle / INVENTORY).write_bytes(encoded(inventory))
    except Exception:
        shutil.rmtree(ROOT / OUT)
        raise
    return inventory


def check_bundle(bundle: Path) -> dict:
    need(bundle.is_dir() and not bundle.is_symlink(), "BUNDLE_ROOT")
    path = regular(bundle, INVENTORY)
    inventory = json.loads(path.read_text())
    need(inventory["schema"] == "fathom-four-shard-source-bundle.1" and
         inventory["sealed_manifest_sha256"] == P02_PINS["manifest.json"] and
         inventory["sealed_summary_sha256"] == P02_PINS["summary.json"] and
         inventory["validated_workbooks"] == [7, 8, 10, 11] and
         inventory["aggregate_complete"] is False and
         inventory["admitted"] is False and inventory["runtime_admission"] is False,
         "INVENTORY_SCOPE")
    refs = inventory["files"]
    need(isinstance(refs, dict) and len(refs) >= 61, "INVENTORY_FILES")
    actual_files: set[str] = set()
    for directory, dirs, files in os.walk(bundle, followlinks=False):
        for name in dirs + files:
            p = Path(directory) / name
            need(not p.is_symlink(), f"SYMLINK {p.relative_to(bundle)}")
        actual_files.update(str((Path(directory) / name).relative_to(bundle)) for name in files)
    need(actual_files == set(refs) | {INVENTORY}, "INVENTORY_CLOSED")
    for rel, ref in refs.items():
        p = regular(bundle, rel)
        need(set(ref) == {"bytes", "sha256", "source_path", "roles"} and
             digest_file(p) == (ref["bytes"], ref["sha256"]), f"ASSET_DRIFT {rel}")
    for name, pin in P02_PINS.items():
        need(refs[str(P02 / name)]["sha256"] == pin, "P02_PIN")
    need(refs[str(GLOBAL)]["sha256"] == GLOBAL_PIN and
         refs[str(NATIVE_BUNDLE)]["sha256"] == NATIVE_PIN, "VERIFIER_PIN")
    # A rewritten inventory cannot hide an omitted package source, authority or plan.
    expected = inventory_for_bundle(bundle)
    need({k: (v["bytes"], v["sha256"], v["roles"]) for k, v in refs.items()} ==
         {k: (v["bytes"], v["sha256"], v["roles"]) for k, v in expected.items()},
         "REFERENCE_CLOSURE")
    return inventory


def inventory_for_bundle(bundle: Path) -> dict[str, dict]:
    """Recompute closure inside bundle without consulting live original paths."""
    # collect() expects its native binary at the historical producer path. Supply a
    # read-only view via a narrow closure pass below rather than creating an alias.
    refs: dict[str, dict] = {}

    def add(rel: str, role: str, pin: str | None = None) -> None:
        p = regular(bundle, rel)
        size, digest = digest_file(p)
        need(pin is None or digest == pin, f"REFERENCE_PIN {rel}")
        row = refs.setdefault(rel, {"bytes": size, "sha256": digest, "roles": []})
        need(row["bytes"] == size and row["sha256"] == digest, "REFERENCE_DRIFT")
        row["roles"].append(role)

    for name, pin in P02_PINS.items():
        add(str(P02 / name), "sealed_p02_" + name, pin)
    manifest = json.loads(regular(bundle, str(P02 / "manifest.json")).read_text())
    need(manifest["validated_workbooks"] == [7, 8, 10, 11] and
         manifest["admitted"] is False and manifest["aggregate_complete"] is False,
         "MANIFEST_SCOPE")
    for role, ref in manifest["foundation"].items():
        add(ref["path"], "foundation_" + role, ref["sha256"])
    add(manifest["completion_contract"]["path"], "completion_contract",
        manifest["completion_contract"]["sha256"])
    sources = set()
    for shard in manifest["shards"]:
        level = shard["legacy_level"]
        artifacts = shard["artifacts"]
        for role, ref in artifacts.items():
            add(ref["path"], f"level{level:03d}_{role}", ref["sha256"])
        package = json.loads(regular(bundle, artifacts["package"]["path"]).read_text())
        profile = json.loads(regular(bundle, artifacts["profile"]["path"]).read_text())
        add(package["source_acceptance"], f"level{level:03d}_source_acceptance")
        for source in package["sources"].values():
            path = source["path"]
            need(source["format"] in ("txt", "pdf") and
                 path.startswith("Notes/") and path.lower().endswith("." + source["format"]),
                 "SOURCE_FORMAT")
            add(path, f"level{level:03d}_source_asset", source["sha256"])
            sources.add(path)
        plan = profile["resource_plan"]
        add(plan["path"], f"level{level:03d}_resource_plan", plan["sha256"])
        for authority in profile["authority_artifacts"]:
            add(authority["path"], f"level{level:03d}_authority_{authority['role']}",
                authority["sha256"])
    need(len(sources) == 8, "SOURCE_SET")
    add(str(GLOBAL), "frozen_global_verifier", GLOBAL_PIN)
    add(str(NATIVE_BUNDLE), "frozen_native_validator", NATIVE_PIN)
    return {k: {**v, "roles": sorted(set(v["roles"]))} for k, v in sorted(refs.items())}


def isolated_verify(bundle: Path) -> dict:
    check_bundle(bundle)
    with tempfile.TemporaryDirectory(prefix="fathom-p13-isolated-") as td:
        scratch = Path(td) / "root"
        shutil.copytree(bundle, scratch, symlinks=False)
        check_bundle(scratch)
        manifest = json.loads(regular(scratch, str(P02 / "manifest.json")).read_text())
        native_results = []
        for shard in manifest["shards"]:
            level = shard["legacy_level"]
            refs = shard["artifacts"]
            profile = refs["profile"]
            report = Path(td) / f"native-level{level:03d}.json"
            command = [str(regular(scratch, str(NATIVE_BUNDLE))),
                       "--package", str(regular(scratch, refs["package"]["path"])),
                       "--registry", str(regular(scratch, refs["registry"]["path"])),
                       "--profile", str(regular(scratch, profile["path"])),
                       "--profile-sha256", profile["sha256"],
                       "--source-root", str(scratch), "--report", str(report)]
            run = subprocess.run(command, capture_output=True, text=True, check=False)
            need(run.returncode == 2 and report.is_file(),
                 f"NATIVE_EXIT {level} {run.returncode} {run.stderr[-500:]}")
            data = json.loads(report.read_text())
            need(data["exit_code"] == 2 and data["valid_reference"] is True and
                 data["curriculum_playback_authorized"] is False and
                 data["coverage"]["observed_records"] == 108 and
                 data["profile_sha256"] == profile["sha256"] and
                 not any(x["severity"] == "error" for x in data["issues"]),
                 f"NATIVE_REPORT {level}")
            native_results.append({"level": level, "exit": run.returncode,
                                   "report_sha256": digest_file(report)[1],
                                   "valid_reference": True,
                                   "playback_authorized": False})
        command = [sys.executable, str(regular(scratch, str(GLOBAL))), "verify",
                   "--manifest", str(P02 / "manifest.json")]
        run = subprocess.run(command, cwd=scratch, capture_output=True, text=True,
                             check=False)
        need(run.returncode == 0, f"GLOBAL_EXIT {run.returncode} {run.stderr[-500:]}")
        result = json.loads(run.stdout)
        need(result["validated_workbooks"] == [7, 8, 10, 11] and
             result["new_counts"] == EXPECTED_COUNTS and
             result["next_allocation_floor"] ==
             {"item": 1128, "module": 1128, "variant": 7378} and
             result["aggregate_complete"] is False and result["admitted"] is False,
             "GLOBAL_RESULT")
        return {"status": "verified_build_only_nonadmitted",
                "source_root": "isolated temporary bundle copy",
                "native": native_results, "global": result,
                "bundle_inventory_sha256": digest_file(bundle / INVENTORY)[1],
                "bundle_file_count": len(json.loads((bundle / INVENTORY).read_text())["files"])}


def handoff(bundle: Path) -> dict:
    inventory = check_bundle(bundle)
    files = inventory["files"]
    manifest = json.loads(regular(bundle, str(P02 / "manifest.json")).read_text())
    shards = []
    sources: dict[str, dict] = {}
    for shard in manifest["shards"]:
        refs = shard["artifacts"]
        package = json.loads(regular(bundle, refs["package"]["path"]).read_text())
        profile = json.loads(regular(bundle, refs["profile"]["path"]).read_text())
        for passage in package["sources"].values():
            rel = passage["path"]
            sources[rel] = {"path": rel, "sha256": files[rel]["sha256"],
                            "bytes": files[rel]["bytes"]}
        shards.append({"legacy_level": shard["legacy_level"],
                       "workbook_id": shard["workbook_id"],
                       "artifacts": {role: {**ref, "bytes": files[ref["path"]]["bytes"]}
                                     for role, ref in refs.items()},
                       "source_acceptance": package["source_acceptance"],
                       "authority": [{"role": ref["role"], "path": ref["path"],
                                      "sha256": ref["sha256"],
                                      "bytes": files[ref["path"]]["bytes"]}
                                     for ref in profile["authority_artifacts"]],
                       "resource_plan": {**profile["resource_plan"],
                                         "bytes": files[profile["resource_plan"]["path"]]["bytes"]}})
    return {"schema": "fathom-four-shard-reader-handoff.1",
            "bundle_root": "bundle",
            "manifest": {"path": str(P02 / "manifest.json"),
                         "sha256": P02_PINS["manifest.json"],
                         "bytes": files[str(P02 / "manifest.json")]["bytes"]},
            "inventory": {"path": INVENTORY,
                          "sha256": digest_file(bundle / INVENTORY)[1]},
            "foundation": {role: {**ref, "bytes": files[ref["path"]]["bytes"]}
                           for role, ref in manifest["foundation"].items()},
            "shards": shards, "source_assets": [sources[k] for k in sorted(sources)],
            "path_policy": {"external_references_remaining": [],
                            "rebased_references": [],
                            "historical_results_aliases_copied_into_bundle": sorted(
                                k for k, v in files.items()
                                if k.startswith("Results/") and v["source_path"] != k)}}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "verify", "check", "handoff"))
    parser.add_argument("--bundle-root", type=Path, default=ROOT / BUNDLE)
    args = parser.parse_args()
    try:
        if args.command == "build":
            result = build()
            print(json.dumps({"status": "built", "file_count": len(result["files"]),
                              "inventory_sha256": digest_file(ROOT / BUNDLE / INVENTORY)[1]},
                             sort_keys=True))
        elif args.command == "check":
            result = check_bundle(args.bundle_root)
            print(json.dumps({"status": "checked", "file_count": len(result["files"])},
                             sort_keys=True))
        elif args.command == "handoff":
            result = handoff(args.bundle_root)
            path = ROOT / OUT / "handoff.json"
            raw = encoded(result)
            if path.exists():
                need(path.read_bytes() == raw, "HANDOFF_DRIFT")
            else:
                path.write_bytes(raw)
            print(json.dumps({"status": "handoff_ready", "path": str(OUT / "handoff.json"),
                              "sha256": sha(raw)}, sort_keys=True))
        else:
            print(json.dumps(isolated_verify(args.bundle_root), sort_keys=True))
    except BundleError as exc:
        parser.exit(1, f"bundle error: {exc}\n")


if __name__ == "__main__":
    main()
