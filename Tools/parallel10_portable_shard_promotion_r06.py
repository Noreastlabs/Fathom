#!/usr/bin/env python3
"""Rebase three native-valid workbook shards into one Build-only candidate tree."""

from __future__ import annotations

import argparse
import copy
import json
import subprocess
from pathlib import Path

import parallel10_global_shard_verifier as globalv


ROOT = Path(__file__).resolve().parents[1]
OUT = Path("Build/parallel-10/portable-shard-promotion-r06")
TREE = OUT / "candidate-tree"
SHARDS = TREE / "Content/controls/curriculum-v1/shards"
AUTH = TREE / "authority"
R05 = Path("Build/parallel-10/three-real-shard-manifest-r05/manifest.json")
R05_PIN = "1807bd7efe0e60b8941ed0b2563518957e333a71deec671ddcc5ce945bfb1f64"
GLOBAL_TOOL = Path("Tools/parallel10_global_shard_verifier.py")
GLOBAL_TOOL_PIN = "896785c05fc95514a0e812e445498d8eb49907dada16a864f44fb91dc615a14c"
NATIVE = Path("Build/parallel-10/2.3-legacy-id-reconciliation-r01/cmake/fathom_content_validate")
LOCAL_ROLES = ("identity_baseline", "allocation_baseline", "lineage_baseline",
               "candidate_identity_allocation")
HISTORICAL_ROLES = ("source_manifest", "source_acceptance", "current_schema_freeze")
ROLE_TO_NAME = {"identity_baseline": "identity-baseline.json",
                "allocation_baseline": "allocation-baseline.json",
                "lineage_baseline": "lineage-baseline.json",
                "candidate_identity_allocation": "candidate-allocation.json",
                "source_manifest": "source-manifest.json",
                "source_acceptance": "source-acceptance.md",
                "current_schema_freeze": "schema-freeze.json"}
LOCAL_FILES = {"package": "package.json", "registry": "identity-registry.json",
               "profile": "expected-profile.json", "identity_baseline": "identity-baseline.json",
               "allocation_baseline": "allocation-baseline.json",
               "lineage_baseline": "lineage-baseline.json",
               "candidate_allocation": "candidate-allocation.json",
               "source_proposal": "source-proposal.json", "source_map": "source-map.json"}


class PromotionError(ValueError):
    pass


def require(ok: bool, code: str) -> None:
    if not ok:
        raise PromotionError(code)


def historical_file(relative: str) -> Path:
    path = ROOT / relative
    if not path.is_file() and relative.startswith("Results/"):
        path = ROOT / "Results/primary" / relative[len("Results/"):]
    require(path.is_file() and path.resolve().is_relative_to(ROOT.resolve()), "HISTORICAL_SOURCE")
    return path


def load_original() -> dict:
    require(globalv.digest(ROOT, str(R05)) == R05_PIN and
            globalv.digest(ROOT, str(GLOBAL_TOOL)) == GLOBAL_TOOL_PIN, "PREDECESSOR_PIN")
    manifest = json.loads((ROOT / R05).read_text())
    require(manifest["validated_workbooks"] == [7, 8, 10] and
            len(manifest["shards"]) == 3 and manifest["admitted"] is False and
            manifest["aggregate_complete"] is False, "PREDECESSOR_SCOPE")
    for descriptor in manifest["shards"]:
        for ref in descriptor["artifacts"].values():
            require(globalv.digest(ROOT, ref["path"]) == ref["sha256"], "ORIGINAL_ARTIFACT_PIN")
    contract = manifest["completion_contract"]
    require(globalv.digest(ROOT, contract["path"]) == contract["sha256"], "COMPLETION_PIN")
    return manifest


def local_dir(level: int) -> Path:
    return SHARDS / f"level{level:03d}"


def validate_semantics(original_package: dict, promoted_package: dict,
                       original_registry: dict, promoted_registry: dict,
                       original_profile: dict, promoted_profile: dict,
                       level: int) -> None:
    require(original_package["records"] == promoted_package["records"] and
            original_package["sources"] == promoted_package["sources"] and
            {k: v for k, v in original_package.items() if k != "source_acceptance"} ==
            {k: v for k, v in promoted_package.items() if k != "source_acceptance"} and
            original_registry == promoted_registry and
            original_profile["event_sources"] == promoted_profile["event_sources"] and
            original_profile["degree_roots"] == promoted_profile["degree_roots"] and
            original_profile["resource_plan"] == promoted_profile["resource_plan"] and
            original_profile["reference_registry"] == promoted_profile["reference_registry"] and
            promoted_profile["reference_package"] == promoted_package,
            "SEMANTIC_VALUE_DRIFT")
    source_refs = {a["role"]: a for a in original_profile["authority_artifacts"]}
    target_refs = {a["role"]: a for a in promoted_profile["authority_artifacts"]}
    require(set(source_refs) == set(target_refs) == set(LOCAL_ROLES + HISTORICAL_ROLES),
            "AUTHORITY_ROLE_DRIFT")
    for role, target in target_refs.items():
        expected_path = (AUTH / ROLE_TO_NAME[role] if role in HISTORICAL_ROLES else
                         local_dir(level) / ROLE_TO_NAME[role])
        require(target["path"] == str(expected_path) and
                target["sha256"] == source_refs[role]["sha256"] and
                Path(target["path"]).is_relative_to(TREE) and
                "parallel-12" not in target["path"] and
                "Results/primary" not in target["path"], "AUTHORITY_ESCAPE_OR_DRIFT")
    require(promoted_package["source_acceptance"] == target_refs["source_acceptance"]["path"],
            "ACCEPTANCE_PATH_DRIFT")


def derive_files() -> dict[Path, bytes]:
    manifest = load_original()
    files: dict[Path, bytes] = {}
    historical: dict[str, bytes] = {}
    for descriptor in manifest["shards"]:
        level = descriptor["legacy_level"]
        refs = descriptor["artifacts"]
        original_package = globalv.load_artifact(ROOT, refs["package"])
        original_registry = globalv.load_artifact(ROOT, refs["registry"])
        original_profile = globalv.load_artifact(ROOT, refs["profile"])
        require(len(original_profile["authority_artifacts"]) == 7, "AUTHORITY_SCOPE")
        for a in original_profile["authority_artifacts"]:
            role = a["role"]
            if role in HISTORICAL_ROLES:
                raw = historical_file(a["path"]).read_bytes()
                require(globalv.sha(raw) == a["sha256"], "HISTORICAL_PIN")
                if role in historical:
                    require(historical[role] == raw, "HISTORICAL_AUTHORITY_DRIFT")
                historical[role] = raw
                files[AUTH / ROLE_TO_NAME[role]] = raw
        promoted_package = copy.deepcopy(original_package)
        promoted_package["source_acceptance"] = str(AUTH / ROLE_TO_NAME["source_acceptance"])
        promoted_profile = copy.deepcopy(original_profile)
        promoted_profile["reference_package"] = promoted_package
        for a in promoted_profile["authority_artifacts"]:
            role = a["role"]
            require(role in LOCAL_ROLES + HISTORICAL_ROLES, "AUTHORITY_ROLE_DRIFT")
            a["path"] = str(AUTH / ROLE_TO_NAME[role] if role in HISTORICAL_ROLES else
                            local_dir(level) / ROLE_TO_NAME[role])
        validate_semantics(original_package, promoted_package, original_registry,
                           original_registry, original_profile, promoted_profile, level)
        d = local_dir(level)
        files[d / "package.json"] = globalv.encoded(promoted_package)
        files[d / "identity-registry.json"] = (ROOT / refs["registry"]["path"]).read_bytes()
        files[d / "expected-profile.json"] = globalv.encoded(promoted_profile)
        for role in ("identity_baseline", "allocation_baseline", "lineage_baseline",
                     "candidate_allocation", "source_proposal", "source_map"):
            files[d / LOCAL_FILES[role]] = (ROOT / refs[role]["path"]).read_bytes()
    files[AUTH / "completion-contract.json"] = (
        ROOT / manifest["completion_contract"]["path"]).read_bytes()
    require(len(files) == 3 + 1 + 3 * 9, "CANDIDATE_FILE_SCOPE")
    return files


def verify_files() -> dict[Path, bytes]:
    expected = derive_files()
    for rel, raw in expected.items():
        require((ROOT / rel).read_bytes() == raw, f"CANDIDATE_DRIFT {rel}")
    return expected


def native_validate() -> None:
    verify_files()
    require((ROOT / NATIVE).is_file(), "NATIVE_BINARY")
    for level in (7, 8, 10):
        d = local_dir(level)
        report, stdout = ROOT / d / "native-report.json", ROOT / d / "native.stdout.log"
        require(not report.exists() and not stdout.exists() and not report.is_symlink() and
                not stdout.is_symlink(), "NATIVE_OUTPUT_EXISTS")
        profile_hash = globalv.digest(ROOT, str(d / "expected-profile.json"))
        command = [str(ROOT / NATIVE), "--package", str(ROOT / d / "package.json"),
                   "--registry", str(ROOT / d / "identity-registry.json"),
                   "--profile", str(ROOT / d / "expected-profile.json"),
                   "--profile-sha256", profile_hash, "--source-root", str(ROOT),
                   "--report", str(report)]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        stdout.write_text(result.stdout + result.stderr)
        require(result.returncode == 2 and report.is_file(), f"NATIVE_EXIT {level} {result.returncode}")
        data = json.loads(report.read_text())
        require(data["exit_code"] == 2 and data["valid_reference"] is True and
                data["curriculum_playback_authorized"] is False and
                data["coverage"]["observed_records"] == 108 and
                data["profile_sha256"] == profile_hash, f"NATIVE_REPORT {level}")


def derive_manifest() -> dict:
    verify_files()
    origin = load_original()
    descriptors = []
    for old in origin["shards"]:
        level = old["legacy_level"]
        d = local_dir(level)
        refs = {role: {"path": str(d / name), "sha256": globalv.digest(ROOT, str(d / name))}
                for role, name in LOCAL_FILES.items()}
        report_path = d / "native-report.json"
        refs["native_report"] = {"path": str(report_path),
                                 "sha256": globalv.digest(ROOT, str(report_path))}
        descriptors.append({"workbook_id": old["workbook_id"], "legacy_level": level,
                            "artifacts": refs})
    contract_path = AUTH / "completion-contract.json"
    manifest = {**origin, "shards": descriptors,
                "completion_contract": {"path": str(contract_path),
                                        "sha256": globalv.digest(ROOT, str(contract_path))},
                "promotion_origin_manifest_sha256": R05_PIN,
                "aggregate_complete": False, "admitted": False}
    return manifest


def seal() -> dict:
    manifest = derive_manifest()
    summary = globalv.verify(ROOT, manifest)
    require(summary["validated_workbooks"] == [7, 8, 10] and
            summary["new_counts"] == {"records": 324, "entities": 2163,
                                      "events": 22464, "sources": 473, "variants": 1512} and
            summary["aggregate_complete"] is False and summary["admitted"] is False,
            "PROMOTED_GLOBAL_STATUS")
    for descriptor in manifest["shards"]:
        profile = globalv.load_artifact(ROOT, descriptor["artifacts"]["profile"])
        for a in profile["authority_artifacts"]:
            require(Path(a["path"]).is_relative_to(TREE) and
                    globalv.digest(ROOT, a["path"]) == a["sha256"], "PROMOTED_AUTHORITY_REF")
    return {"status": "build_only_promoted_native_reference", **summary,
            "local_authority_self_contained": True,
            "source_assets_embedded": False,
            "full_105_workbook_source_coverage_verified": False,
            "curriculum_acceptance": "Pending", "runtime_admission": False,
            "origin_manifest_sha256": R05_PIN}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "verify-files", "native", "seal", "verify"))
    args = parser.parse_args()
    if args.command == "build":
        files = derive_files()
        require(all(not (ROOT / p).exists() and not (ROOT / p).is_symlink() for p in files),
                "OUTPUT_EXISTS")
        for rel, raw in files.items():
            dest = ROOT / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(raw)
        print(f"CANDIDATE BUILD PASS files={len(files)}")
    elif args.command == "verify-files":
        print(f"CANDIDATE VERIFY PASS files={len(verify_files())}")
    elif args.command == "native":
        native_validate()
        print("PROMOTED NATIVE PASS shards=3")
    elif args.command == "seal":
        summary = seal()
        manifest = derive_manifest()
        for name, obj in (("manifest.json", manifest), ("summary.json", summary)):
            path = ROOT / OUT / name
            require(not path.exists() and not path.is_symlink(), "SEAL_EXISTS")
            path.write_bytes(globalv.encoded(obj))
        print(json.dumps(summary, sort_keys=True))
    else:
        summary = seal()
        manifest = derive_manifest()
        require((ROOT / OUT / "manifest.json").read_bytes() == globalv.encoded(manifest) and
                (ROOT / OUT / "summary.json").read_bytes() == globalv.encoded(summary),
                "SEAL_DRIFT")
        print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
