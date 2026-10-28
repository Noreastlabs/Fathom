#!/usr/bin/env python3
"""Build and verify a bounded Level7 native shard plus global identity manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import parallel10_level007_schema1_overlay as prior


ROOT = Path(__file__).resolve().parents[1]
OUT = Path("Build/parallel-10/level007-shard-reference-r02")
R01 = Path("Build/parallel-10/level007-schema1-overlay-r01")
FILES = ("package.json", "identity-registry.json", "expected-profile.json",
         "candidate-allocation.json", "identity-baseline.json",
         "allocation-baseline.json", "lineage-baseline.json", "local-summary.json")
R01_PINS = {
    "package.json": "8a9f10f34de7f08ad1098a8959d30858e7156c92acf101980067725d5f0a013b",
    "identity-registry.json": "7c1567712b37ae838cfebe8a67837fb7e60d020418aff858dbf622c2e46932df",
    "expected-profile.json": "b70060ece8f62646fbff46fd4b8338176e43f66f2575cffca55236e33b87d12b",
    "candidate-allocation.json": "70c574a03db26d4d47bee738dba62c0fbff7da8400a58568549f752ccb473e27",
    "transaction.json": None,
}


class ShardError(ValueError):
    pass


def require(ok: bool, code: str) -> None:
    if not ok:
        raise ShardError(code)


def encoded(obj: object) -> bytes:
    return (json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read(root: Path, relative: Path) -> dict:
    return json.loads((root / relative).read_text())


def identity(root: Path, relative: Path) -> str:
    return sha((root / relative).read_bytes())


def derive_local(root: Path = ROOT) -> dict[str, dict]:
    prior.pin_inputs(root)
    for name, expected in R01_PINS.items():
        if expected:
            require(identity(root, R01 / name) == expected, f"R01_PIN_DRIFT {name}")
    base = read(root, prior.CURRENT / "package.json")
    base_registry = read(root, prior.CURRENT / "identity-registry.json")
    merged = read(root, R01 / "package.json")
    merged_registry = read(root, R01 / "identity-registry.json")
    merged_profile = read(root, R01 / "expected-profile.json")
    transaction = read(root, R01 / "transaction.json")
    require(merged["records"][:659] == base["records"] and
            merged_registry["entities"][:6336] == base_registry["entities"], "FOUNDATION_PREFIX")
    require(merged["records"][659:] == read(root, R01 / "proposal.json")["records"] and
            merged_registry["entities"][6336:] == transaction["new_entities"], "R01_PROPOSAL_DRIFT")
    added_records = json.loads(json.dumps(merged["records"][659:]))
    for record in added_records:
        # Standard tuning at written frets is untransposed; the schema's explicit
        # position model pairs these open-string pitches with capo zero.
        context = record["context"]
        require(context["tuning_open_midi"] == [40, 45, 50, 55, 59, 64], "TUNING_DRIFT")
        require(context.pop("source_local_key") == transaction["source_map"][int(record["id"].split(":")[-1])-696]["source_local_key"],
                "SOURCE_KEY_DRIFT")
        require("capo" not in context, "R01_CAPO_DRIFT")
        context["capo"] = 0
    package = {k: v for k, v in merged.items() if k != "workbook_catalog"}
    package["content_version"] = "curriculum-v1-level007-local-shard-build-only.1"
    package["records"] = added_records
    package["sources"] = {k: v for k, v in merged["sources"].items() if k not in base["sources"]}
    require(len(package["sources"]) == 120, "LOCAL_SOURCES")
    registry = {k: v for k, v in merged_registry.items() if k != "workbook_catalog"}
    registry["entities"] = [base_registry["entities"][0], *merged_registry["entities"][6336:]]
    require(registry["entities"][0]["id"] == "fg:course:000001", "COURSE_ROOT")
    allocation = {"version": "control-allocation.1",
                  "authority": "P10 Level7 local shard only; global identity manifest required; no admission",
                  "records": transaction["records"]}
    identity_baseline = {"identity_version": registry["identity_version"],
                         "entities": [registry["entities"][0]], "rules": registry["rules"]}
    allocation_baseline = {"version": "control-allocation.1",
                           "authority": "Local shard course-only preallocation; global 659 foundation is pinned separately",
                           "records": {}}
    lineage_baseline = {"version": "lineage-baseline.1", "records": {}}
    profile = {k: v for k, v in merged_profile.items() if k != "workbook_catalog"}
    profile["reference_package"] = package
    profile["reference_registry"] = registry
    events = {e["event_id"]: r["source_refs"][0] for r in added_records for e in r["events"]}
    require(len(events) == 1728 and all(merged_profile["event_sources"][k] == v for k, v in events.items()),
            "EVENT_SOURCE_DRIFT")
    profile["event_sources"] = events
    profile["authority_artifacts"] = [
        a for a in merged_profile["authority_artifacts"]
        if a["role"] in ("source_manifest", "source_acceptance", "current_schema_freeze")
    ]
    for role, name, content in (("identity_baseline", "identity-baseline.json", identity_baseline),
                                ("allocation_baseline", "allocation-baseline.json", allocation_baseline),
                                ("lineage_baseline", "lineage-baseline.json", lineage_baseline),
                                ("candidate_identity_allocation", "candidate-allocation.json", allocation)):
        profile["authority_artifacts"].append({"path": str(OUT / name), "role": role,
                                                "sha256": sha(encoded(content))})
    counts = {"records": len(package["records"]), "entities": len(registry["entities"]),
              "sources": len(package["sources"]), "events": len(events),
              "variants": sum(len(r["variants"]) for r in added_records)}
    require(counts == {"records": 108, "entities": 434, "sources": 120,
                       "events": 1728, "variants": 216}, "LOCAL_COUNTS")
    summary = {"status": "local_native_reference_pending_global_manifest_required",
               "counts": counts, "foundation_sha256": {n: prior.PINS[prior.CURRENT / n] for n in
                            ("package.json", "identity-registry.json", "expected-profile.json", "generation.json")},
               "source_proposal_sha256": prior.PINS[prior.SOURCE_PROPOSAL],
               "r01_package_sha256": R01_PINS["package.json"],
               "catalog_sha256": prior.PINS[prior.CURRENT / "workbook-coverage.json"],
               "admitted": False, "runtime_eligible": False, "aggregate_complete": False}
    return {"package.json": package, "identity-registry.json": registry,
            "expected-profile.json": profile, "candidate-allocation.json": allocation,
            "identity-baseline.json": identity_baseline,
            "allocation-baseline.json": allocation_baseline,
            "lineage-baseline.json": lineage_baseline, "local-summary.json": summary}


def ensure_global(root: Path, manifest: dict, report: dict) -> None:
    prior.pin_inputs(root)
    require(manifest["schema"] == "parallel10-global-shard-manifest.1" and
            manifest["admitted"] is False and manifest["aggregate_complete"] is False,
            "MANIFEST_AUTHORITY")
    foundation = manifest["foundation"]
    for name in ("package.json", "identity-registry.json", "expected-profile.json", "generation.json"):
        require(foundation[name] == prior.PINS[prior.CURRENT / name] == identity(root, prior.CURRENT / name),
                f"FOUNDATION_PIN {name}")
    require(manifest["catalog_sha256"] == prior.PINS[prior.CURRENT / "workbook-coverage.json"], "CATALOG_PIN")
    require(manifest["source_proposal_sha256"] == prior.PINS[prior.SOURCE_PROPOSAL], "SOURCE_PIN")
    shards = manifest["shards"]
    require(len(shards) == 1 and shards[0]["workbook_id"] == "fg:workbook:000007" and
            manifest["validated_workbooks"] == [7] and manifest["catalog_workbooks"] == 105,
            "SHARD_COVERAGE")
    entry = shards[0]
    for name in FILES[:-1]:
        require(entry["sha256"][name] == identity(root, OUT / name), f"SHARD_PIN {name}")
    require(entry["native_report_sha256"] == identity(root, OUT / "native-report.json"), "NATIVE_REPORT_PIN")
    pkg, reg, prof, allocation = (read(root, OUT / n) for n in
                                  ("package.json", "identity-registry.json", "expected-profile.json", "candidate-allocation.json"))
    require(report["valid_reference"] is True and report["exit_code"] == 2 and
            report["curriculum_playback_authorized"] is False and
            report["package_sha256"] == entry["sha256"]["package.json"] and
            report["registry_sha256"] == entry["sha256"]["identity-registry.json"] and
            report["profile_sha256"] == entry["sha256"]["expected-profile.json"] and
            report["coverage"]["observed_records"] == 108, "NATIVE_NOT_LOCAL_VALID")
    require(all("workbook_catalog" not in x for x in (pkg, reg, prof)), "LOCAL_CATALOG_DRIFT")
    require(pkg["records"] == prof["reference_package"]["records"] and
            reg == prof["reference_registry"] and
            set(allocation["records"]) == {r["id"] for r in pkg["records"]}, "LOCAL_AUTHORITY")
    base_package = read(root, prior.CURRENT / "package.json")
    base_registry = read(root, prior.CURRENT / "identity-registry.json")
    base_profile = read(root, prior.CURRENT / "expected-profile.json")
    transaction = read(root, R01 / "transaction.json")
    r01 = read(root, R01 / "package.json")
    require(r01["records"][:659] == base_package["records"] and
            r01["records"][659:] == [
                {**r, "context": {**{k: v for k, v in r["context"].items() if k != "capo"},
                                   "source_local_key": transaction["source_map"][i]["source_local_key"]}}
                for i, r in enumerate(pkg["records"])], "RECORD_SOURCE_PROJECTION")
    require(reg["entities"][1:] == transaction["new_entities"] and
            allocation["records"] == transaction["records"], "IDENTITY_TRANSACTION")
    # This verifier is defined over all manifest shards; the r02 pilot intentionally has one.
    all_entities = base_registry["entities"] + reg["entities"][1:]
    entity_ids = [e["id"] for e in all_entities]
    require(len(entity_ids) == len(set(entity_ids)), "GLOBAL_DUPLICATE_ENTITY")
    all_records = base_package["records"] + pkg["records"]
    record_ids = [r["id"] for r in all_records]
    require(len(record_ids) == len(set(record_ids)), "GLOBAL_DUPLICATE_RECORD")
    event_ids = [e["event_id"] for r in all_records for e in r["events"]]
    require(len(event_ids) == len(set(event_ids)), "GLOBAL_DUPLICATE_EVENT")
    source_ids = set(base_package["sources"])
    require(not source_ids.intersection(pkg["sources"]), "GLOBAL_DUPLICATE_SOURCE")
    require(all(base_profile["event_sources"][e["event_id"]] in source_ids
                for r in base_package["records"] for e in r["events"]), "FOUNDATION_SOURCE")
    require(set(prof["event_sources"]) == {e["event_id"] for r in pkg["records"] for e in r["events"]} and
            all(v in pkg["sources"] for v in prof["event_sources"].values()), "SHARD_SOURCE")
    prior.check_new_ids(base_registry, reg["entities"][1:])
    require(all(r["lineage"] == {"kind": "new"} and r["content_revision"] == 1 and
                r["runtime_eligible"] is False and
                all(e["onset_q"] is None and e["duration_q"] is None for e in r["events"])
                for r in pkg["records"]), "GLOBAL_LINEAGE_OR_ADMISSION")
    catalog = base_registry["workbook_catalog"]
    require(len(catalog["entries"]) == 105 and
            [e for e in catalog["entries"] if e["workbook_id"] == entry["workbook_id"]][0]["admitted"] is False,
            "CATALOG_STATUS")
    require(entry["entity_ids_sha256"] == sha(encoded(sorted(e["id"] for e in reg["entities"][1:]))) and
            entry["event_ids_sha256"] == sha(encoded(sorted(prof["event_sources"]))) and
            entry["source_refs_sha256"] == sha(encoded(sorted(pkg["sources"]))), "GLOBAL_SET_DIGEST")


def seal(root: Path = ROOT) -> dict:
    local = derive_local(root)
    for name in FILES:
        require((root / OUT / name).read_bytes() == encoded(local[name]), f"LOCAL_DRIFT {name}")
    report = read(root, OUT / "native-report.json")
    entry = {"workbook_id": "fg:workbook:000007",
             "sha256": {name: identity(root, OUT / name) for name in FILES[:-1]},
             "native_report_sha256": identity(root, OUT / "native-report.json"),
             "entity_ids_sha256": sha(encoded(sorted(e["id"] for e in local["identity-registry.json"]["entities"][1:]))),
             "event_ids_sha256": sha(encoded(sorted(local["expected-profile.json"]["event_sources"]))),
             "source_refs_sha256": sha(encoded(sorted(local["package.json"]["sources"])))}
    manifest = {"schema": "parallel10-global-shard-manifest.1",
                "foundation": local["local-summary.json"]["foundation_sha256"],
                "catalog_sha256": local["local-summary.json"]["catalog_sha256"],
                "source_proposal_sha256": local["local-summary.json"]["source_proposal_sha256"],
                "catalog_workbooks": 105, "validated_workbooks": [7],
                "shards": [entry], "admitted": False, "aggregate_complete": False}
    ensure_global(root, manifest, report)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "verify-local", "seal", "verify-global"))
    args = parser.parse_args()
    target = ROOT / OUT
    if args.command == "build":
        local = derive_local()
        target.mkdir(parents=True, exist_ok=True)
        require(all(not (target / n).exists() and not (target / n).is_symlink() for n in FILES), "OUTPUT_EXISTS")
        for name in FILES:
            (target / name).write_bytes(encoded(local[name]))
        print(json.dumps(local["local-summary.json"], sort_keys=True))
    elif args.command == "verify-local":
        local = derive_local()
        for name in FILES:
            require((target / name).read_bytes() == encoded(local[name]), f"LOCAL_DRIFT {name}")
        print("LOCAL VERIFY PASS")
    elif args.command == "seal":
        manifest = seal()
        path = target / "global-manifest.json"
        require(not path.exists() and not path.is_symlink(), "MANIFEST_EXISTS")
        path.write_bytes(encoded(manifest))
        print("GLOBAL SEAL PASS")
    else:
        manifest = read(ROOT, OUT / "global-manifest.json")
        require(encoded(manifest) == encoded(seal()), "MANIFEST_DRIFT")
        print("GLOBAL VERIFY PASS")


if __name__ == "__main__":
    main()
