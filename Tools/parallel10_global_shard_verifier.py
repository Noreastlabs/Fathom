#!/usr/bin/env python3
"""Verify ordered schema1 workbook shards against the reviewed 659 foundation."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = Path("Build/parallel-10/global-shard-verifier-r03")
LOCAL7 = Path("Build/parallel-10/level007-shard-reference-r02")
TRANSACTION7 = Path("Build/parallel-10/level007-schema1-overlay-r01/transaction.json")
PROPOSAL7 = Path("Build/parallel-10/level007-source-proposal-adapter-r01/proposal-01.json")
FOUNDATION = Path("Content/controls/curriculum-v1")
FOUNDATION_PINS = {
    "package": "766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255",
    "registry": "5d265859e1e8a5a530a0e53d88b019a1c920f3bba6cccb4ef0fef2f7640007e5",
    "profile": "21009e3596f325a4b9f73c9532b71cd361703e0f682b40088ff58bff7ba57c8a",
    "generation": "fc6cec9f9d67eb82c97c5f4c3fb95d285178fb7fce7bd147d9ae0296d21b4c1c",
    "catalog_coverage": "d8e492101c97c60add858799c77da4db3f0c528d348c9cf66105c2dc37df4eeb",
}
FOUNDATION_NAMES = {"package": "package.json", "registry": "identity-registry.json",
                    "profile": "expected-profile.json", "generation": "generation.json",
                    "catalog_coverage": "workbook-coverage.json"}
SHARD_ROLES = ("package", "registry", "profile", "native_report", "identity_baseline",
               "allocation_baseline", "lineage_baseline", "candidate_allocation",
               "source_proposal", "source_map")
LOCAL_NAMES = {"package": "package.json", "registry": "identity-registry.json",
               "profile": "expected-profile.json", "native_report": "native-report.json",
               "identity_baseline": "identity-baseline.json",
               "allocation_baseline": "allocation-baseline.json",
               "lineage_baseline": "lineage-baseline.json",
               "candidate_allocation": "candidate-allocation.json"}
AUTHORITY_ROLES = {"identity_baseline", "allocation_baseline", "lineage_baseline",
                   "candidate_identity_allocation"}


class GlobalError(ValueError):
    pass


def require(ok: bool, code: str) -> None:
    if not ok:
        raise GlobalError(code)


def encoded(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest(root: Path, relative: str) -> str:
    return sha(safe_path(root, relative).read_bytes())


def safe_path(root: Path, value: str) -> Path:
    p = Path(value)
    require(value and not p.is_absolute() and ".." not in p.parts and "." not in p.parts and
            not value.startswith("/") and "\\" not in value, "PATH_UNSAFE")
    resolved = (root / p).resolve()
    require(resolved.is_relative_to(root.resolve()) and resolved.is_file(), "PATH_UNSAFE")
    return resolved


def load_artifact(root: Path, ref: dict) -> dict:
    require(set(ref) == {"path", "sha256"} and len(ref["sha256"]) == 64 and
            digest(root, ref["path"]) == ref["sha256"], "ARTIFACT_PIN")
    return json.loads(safe_path(root, ref["path"]).read_text())


def ref(root: Path, relative: Path) -> dict:
    return {"path": str(relative), "sha256": digest(root, str(relative))}


def number(identity: str, kind: str) -> int:
    prefix = f"fg:{kind}:"
    require(identity.startswith(prefix) and identity[len(prefix):].isdigit(), "IDENTITY_FORMAT")
    return int(identity[len(prefix):])


def source_map_level7(root: Path) -> dict:
    transaction = json.loads(safe_path(root, str(TRANSACTION7)).read_text())
    entries = [{"record_id": x["item_id"], "source_local_key": x["source_local_key"],
                "source_refs": [x["txt"], x["pdf"]],
                "source_record_sha256": x["source_record_sha256"]}
               for x in transaction["source_map"]]
    return {"schema": "global-shard-source-map.1", "workbook_id": "fg:workbook:000007",
            "source_proposal_sha256": digest(root, str(PROPOSAL7)), "entries": entries}


def pilot_manifest(root: Path) -> tuple[dict, dict]:
    source_map = source_map_level7(root)
    foundation = {role: ref(root, FOUNDATION / name) for role, name in FOUNDATION_NAMES.items()}
    require(all(foundation[k]["sha256"] == pin for k, pin in FOUNDATION_PINS.items()), "FOUNDATION_PIN")
    artifacts = {role: ref(root, LOCAL7 / name) for role, name in LOCAL_NAMES.items()}
    artifacts["source_proposal"] = ref(root, PROPOSAL7)
    source_map_path = OUT / "level007-source-map.json"
    artifacts["source_map"] = {"path": str(source_map_path), "sha256": sha(encoded(source_map))}
    manifest = {"schema": "global-curriculum-shard-manifest.1", "foundation": foundation,
                "shards": [{"workbook_id": "fg:workbook:000007", "legacy_level": 7,
                            "artifacts": artifacts}],
                "validated_workbooks": [7], "catalog_workbooks": 105,
                "aggregate_complete": False, "admitted": False}
    return source_map, manifest


def check_local(shard: dict, docs: dict, catalog: dict, foundation_course: dict) -> dict:
    workbook = shard["workbook_id"]
    level = shard["legacy_level"]
    require(number(workbook, "workbook") == level and 1 <= level <= 105, "WORKBOOK_IDENTITY")
    entry = [x for x in catalog["entries"] if x["workbook_id"] == workbook]
    require(len(entry) == 1 and all(entry[0][k] is False for k in
                                   ("admitted", "runtime_eligible", "imported", "runtime_admitted")),
            "CATALOG_STATUS")
    pkg, reg, prof, report = (docs[k] for k in ("package", "registry", "profile", "native_report"))
    ib, ab, lb, alloc = (docs[k] for k in ("identity_baseline", "allocation_baseline",
                                 "lineage_baseline", "candidate_allocation"))
    proposal, source_map = docs["source_proposal"], docs["source_map"]
    require(all("workbook_catalog" not in x for x in (pkg, reg, prof)), "LOCAL_CATALOG")
    require(prof["reference_package"] == pkg and prof["reference_registry"] == reg,
            "LOCAL_PROFILE_AUTHORITY")
    require(ib["entities"] == [foundation_course] and ab["records"] == {} and lb["records"] == {} and
            ib["identity_version"] == reg["identity_version"] and ib["rules"] == reg["rules"],
            "LOCAL_BASELINE")
    roles = {}
    for a in prof["authority_artifacts"]:
        if a["role"] in AUTHORITY_ROLES:
            require(a["role"] not in roles, "LOCAL_AUTHORITY_DUPLICATE")
            roles[a["role"]] = (a["path"], a["sha256"])
    expected = {r: (shard["artifacts"][r]["path"], shard["artifacts"][r]["sha256"])
                for r in ("identity_baseline", "allocation_baseline", "lineage_baseline")}
    expected["candidate_identity_allocation"] = (
        shard["artifacts"]["candidate_allocation"]["path"],
        shard["artifacts"]["candidate_allocation"]["sha256"])
    require(roles == expected, "LOCAL_AUTHORITY_BINDING")
    records, entities, sources = pkg["records"], reg["entities"], pkg["sources"]
    require(records and entities[0] == foundation_course and
            all(r["workbook_id"] == workbook and r["legacy_level"] == level and
                r["lineage"] == {"kind": "new"} and r["content_revision"] == 1 and
                r["runtime_eligible"] is False and all(e["onset_q"] is None and
                e["duration_q"] is None for e in r["events"]) for r in records),
            "LOCAL_LINEAGE_OR_ADMISSION")
    require(all(e["parent"] == foundation_course["id"] for e in entities[1:]
                if e["kind"] == "workbook") and
            [e["id"] for e in entities if e["kind"] == "workbook"] == [workbook],
            "LOCAL_WORKBOOK_ENTITY")
    record_ids = {r["id"] for r in records}
    require(len(record_ids) == len(records) and set(alloc["records"]) == record_ids,
            "LOCAL_ALLOCATION_COVERAGE")
    entity_ids = {e["id"] for e in entities}
    require(len(entity_ids) == len(entities) and
            {e["id"] for e in entities if e["kind"] == "item"} == record_ids,
            "LOCAL_ENTITY_COVERAGE")
    event_ids = [e["event_id"] for r in records for e in r["events"]]
    variant_ids = {v["id"] for r in records for v in r["variants"]}
    require(len(event_ids) == len(set(event_ids)) and
            set(prof["event_sources"]) == set(event_ids) and
            all(v in sources for v in prof["event_sources"].values()), "LOCAL_EVENT_SOURCE")
    require({e["id"] for e in entities if e["kind"] == "variant"} == variant_ids,
            "LOCAL_VARIANT_COVERAGE")
    for r in records:
        a = alloc["records"][r["id"]]
        require(a["legacy_level"] == level and
                set(a["occurrences"].values()) == {e["event_id"] for e in r["events"]} and
                set(a["variants"].values()) == {v["id"] for v in r["variants"]} and
                all(s in sources for s in r["source_refs"]), "LOCAL_ALLOCATION_OR_SOURCE")
    require(source_map["schema"] == "global-shard-source-map.1" and
            source_map["workbook_id"] == workbook and
            source_map["source_proposal_sha256"] == shard["artifacts"]["source_proposal"]["sha256"],
            "SOURCE_MAP_AUTHORITY")
    proposal_rows = {x["source_local_key"]: x for x in proposal["records"]}
    map_rows = source_map["entries"]
    require(len(proposal_rows) == len(proposal["records"]) and
            len(map_rows) == len(records) == len(proposal_rows) and
            {x["record_id"] for x in map_rows} == record_ids and
            len({x["source_local_key"] for x in map_rows}) == len(map_rows), "SOURCE_MAP_COVERAGE")
    by_id = {r["id"]: r for r in records}
    for row in map_rows:
        key = row["source_local_key"]
        require(key in proposal_rows and
                row["source_record_sha256"] == proposal_rows[key]["source_record_sha256"] and
                row["source_refs"] == [proposal_rows[key]["source_refs"]["txt"],
                                       proposal_rows[key]["source_refs"]["pdf"]] and
                all(s in by_id[row["record_id"]]["source_refs"] for s in row["source_refs"]),
                "SOURCE_MAP_PROPOSAL")
    coverage = report["coverage"]
    require(report["exit_code"] == 2 and report["valid_reference"] is True and
            report["curriculum_playback_authorized"] is False and
            all(report[k] == shard["artifacts"][role]["sha256"] for k, role in
                (("package_sha256", "package"), ("registry_sha256", "registry"),
                 ("profile_sha256", "profile"), ("expected_profile_sha256", "profile"))) and
            coverage["observed_records"] == coverage["expected_records"] == len(records) and
            coverage["observed_entities"] == coverage["expected_entities"] == len(entities) and
            coverage["observed_passages"] == coverage["expected_passages"] == len(sources) and
            coverage["events"] == len(event_ids) and coverage["variants"] == len(variant_ids) and
            {x["id"] for x in report["records"]} == record_ids and
            all(x["valid_reference"] is True for x in report["records"]) and
            not any(x["severity"] == "error" for x in report["issues"]), "NATIVE_SHARD_INVALID")
    return {"workbook": workbook, "level": level, "record_ids": record_ids,
            "entities": [{"id": e["id"], "kind": e["kind"]} for e in entities[1:]],
            "event_ids": event_ids, "source_ids": set(sources),
            "source_keys": {x["source_local_key"] for x in map_rows},
            "counts": {"records": len(records), "entities": len(entities)-1,
                       "events": len(event_ids), "sources": len(sources), "variants": len(variant_ids)}}


def check_union(foundation: dict, shards: list[dict], catalog: dict) -> dict:
    used = {kind: set() for kind in ("course", "workbook", "module", "item", "variant")}
    ids = set()
    for e in foundation["registry"]["entities"]:
        require(e["id"] not in ids, "FOUNDATION_ENTITY_DUPLICATE")
        ids.add(e["id"])
        used[e["kind"]].add(number(e["id"], e["kind"]))
    record_ids = {r["id"] for r in foundation["package"]["records"]}
    event_ids = {e["event_id"] for r in foundation["package"]["records"] for e in r["events"]}
    source_ids = set(foundation["package"]["sources"])
    source_keys = set()
    reserved = {kind: [] for kind in ("module", "item", "variant")}
    for entry in catalog["entries"]:
        bounds = entry.get("reserved_playable_identity_ranges", {})
        for kind, plural in (("module", "modules"), ("item", "items"), ("variant", "variants")):
            if plural in bounds:
                low, high = (number(x, kind) for x in bounds[plural])
                reserved[kind].append((low, high))
    floor = {kind: max(used[kind] | {h for _, h in reserved[kind]}) for kind in reserved}
    workbooks = set()
    counts = {k: 0 for k in ("records", "entities", "events", "sources", "variants")}
    for shard in shards:
        require(shard["workbook"] not in workbooks and shard["workbook"] not in ids,
                "GLOBAL_DUPLICATE_WORKBOOK")
        workbooks.add(shard["workbook"])
        for e in shard["entities"]:
            ident, kind = e["id"], e["kind"]
            require(ident not in ids, "GLOBAL_DUPLICATE_ENTITY")
            n = number(ident, kind)
            if kind in floor:
                require(n > floor[kind] and all(not low <= n <= high for low, high in reserved[kind]),
                        "GLOBAL_RESERVED_OR_ORDER")
            ids.add(ident)
            used[kind].add(n)
        for kind in floor:
            floor[kind] = max(used[kind] | {floor[kind]})
        new_records = shard["record_ids"]
        require(not record_ids.intersection(new_records), "GLOBAL_DUPLICATE_RECORD")
        record_ids.update(new_records)
        require(not event_ids.intersection(shard["event_ids"]), "GLOBAL_DUPLICATE_EVENT")
        event_ids.update(shard["event_ids"])
        require(not source_ids.intersection(shard["source_ids"]), "GLOBAL_DUPLICATE_SOURCE")
        source_ids.update(shard["source_ids"])
        require(not source_keys.intersection(shard["source_keys"]), "GLOBAL_DUPLICATE_SOURCE_KEY")
        source_keys.update(shard["source_keys"])
        for k in counts:
            counts[k] += shard["counts"][k]
    return {"validated_workbooks": sorted(number(x, "workbook") for x in workbooks),
            "shard_count": len(shards), "new_counts": counts,
            "next_allocation_floor": {kind: floor[kind] + 1 for kind in floor},
            "aggregate_complete": len(workbooks) == len(catalog["entries"])}


def verify(root: Path, manifest: dict) -> dict:
    require(manifest["schema"] == "global-curriculum-shard-manifest.1" and
            manifest["admitted"] is False and isinstance(manifest["aggregate_complete"], bool) and
            isinstance(manifest["shards"], list) and len(manifest["shards"]) >= 1,
            "MANIFEST_AUTHORITY")
    foundation = {}
    for role, name in FOUNDATION_NAMES.items():
        expected = {"path": str(FOUNDATION / name), "sha256": FOUNDATION_PINS[role]}
        require(manifest["foundation"][role] == expected, "FOUNDATION_PIN")
        foundation[role] = load_artifact(root, expected)
    base_pkg, base_reg, base_prof = (foundation[k] for k in ("package", "registry", "profile"))
    require(len(base_pkg["records"]) == 659 and len(base_reg["entities"]) == 6336 and
            base_prof["reference_package"] == {k: v for k, v in base_pkg.items() if k != "workbook_catalog"} and
            base_prof["reference_registry"] == {k: v for k, v in base_reg.items() if k != "workbook_catalog"} and
            base_pkg["workbook_catalog"] == base_reg["workbook_catalog"] == base_prof["workbook_catalog"] and
            len(base_reg["workbook_catalog"]["entries"]) == 105,
            "FOUNDATION_AUTHORITY")
    catalog = base_reg["workbook_catalog"]
    course = [e for e in base_reg["entities"] if e["kind"] == "course"]
    require(len(course) == 1, "FOUNDATION_COURSE")
    # Keep only identifiers and counts after each workbook. Full shard package,
    # profile, report and source proposal objects are released before the next.
    foundation.pop("profile")
    foundation.pop("generation")
    foundation.pop("catalog_coverage")
    del base_prof
    checked = []
    for shard in manifest["shards"]:
        refs = shard["artifacts"]
        require(set(refs) == set(SHARD_ROLES), "SHARD_ARTIFACT_ROLES")
        docs = {role: load_artifact(root, refs[role]) for role in SHARD_ROLES}
        checked.append(check_local(shard, docs, catalog, course[0]))
        del docs
    union = check_union(foundation, checked, catalog)
    require(manifest["validated_workbooks"] == union["validated_workbooks"] and
            manifest["catalog_workbooks"] == 105 and
            manifest["aggregate_complete"] is union["aggregate_complete"],
            "MANIFEST_COVERAGE")
    return {"status": "verified_preparatory_global_manifest", **union,
            "admitted": False, "native_scope": "independent_local_shards_only"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build-pilot", "verify"))
    parser.add_argument("--manifest", default=str(OUT / "manifest.json"))
    args = parser.parse_args()
    if args.command == "build-pilot":
        source_map, manifest = pilot_manifest(ROOT)
        target = ROOT / OUT
        target.mkdir(parents=True, exist_ok=True)
        for name, data in (("level007-source-map.json", source_map), ("manifest.json", manifest)):
            p = target / name
            require(not p.exists() and not p.is_symlink(), "OUTPUT_EXISTS")
            p.write_bytes(encoded(data))
        summary = verify(ROOT, manifest)
        (target / "summary.json").write_bytes(encoded(summary))
        print(json.dumps(summary, sort_keys=True))
    else:
        path = safe_path(ROOT, args.manifest)
        manifest = json.loads(path.read_text())
        print(json.dumps(verify(ROOT, manifest), sort_keys=True))


if __name__ == "__main__":
    main()
