#!/usr/bin/env python3
"""Build a non-admitted, Build-only reconciliation of 11 reviewed curriculum IDs.

This tool never edits Content or authority evidence. It refuses changed inputs and
any identity, allocation, source or record conflict before creating an output.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path


INPUTS = {
    "current_package": ("Content/controls/curriculum-v1/package.json", "319240faabc77f1d6962f5442c142401d7e841afcf5779c8893e24302302207e"),
    "current_registry": ("Content/controls/curriculum-v1/identity-registry.json", "2c5a58533bf91adc8dd70d0cdbe7dfbd9619d0dd3844767ca617621f2df66205"),
    "current_profile": ("Content/controls/curriculum-v1/expected-profile.json", "4ee6c5998404123326dd425eb057314c0da5e3aafa180e28e74a5b75186ab2c4"),
    "current_generation": ("Content/controls/curriculum-v1/generation.json", "d957486e44b5a99e73bf544df8a10f50003e084cedc0cdb4f96355e57383d753"),
    "control_package": ("Content/controls/representative-v1/package.json", "0ecd2b1466a7b16e10ca6221299b3b1b21c197ff13cd5df9f038e307673aea8b"),
    "control_registry": ("Content/controls/representative-v1/identity-registry.json", "fa64b6d9e0a937415c5c52ff96e050de89f5eb31b989e0fd3e4b97eb9adfb6a8"),
    "control_profile": ("Content/controls/representative-v1/expected-profile.json", "22c82db322f36d78e744b3445173f7d0a3f4f686ead209293c2416f0db308aed"),
    "reviewed_report": ("Results/primary/20260912T104210Z-2.3.1.1.1-r01-evidence/proof-validation01/report.json", "cc70656830b9eda8673676c51ea4f8a7aff9dc47e291d230bff52d3f95c7e4ca"),
    "r13_registry": ("Results/primary/20260912T202956Z-2.3.1.1.1-r13-evidence/allocation01/cumulative-registry.json", "ceef5633b0fba148189f277a046763301ba5d7cd70bab5d0701b07d1e3af2791"),
    "r13_allocation": ("Results/primary/20260912T202956Z-2.3.1.1.1-r13-evidence/allocation01/cumulative-allocation.json", "3b3f6217fc35ac091201f99efcc43763a7def134b152cd22b1e5d3141cd61a59"),
    "r13_lineage": ("Results/primary/20260912T202956Z-2.3.1.1.1-r13-evidence/handoff01/lineage-baseline.json", "2205ba66ddfd002dd3402b33272be949b5c8a22d83932c4e7c8b4345f48bfdf4"),
    "r14_registry": ("Results/primary/20260912T204759Z-2.3.1.1.1-r14-evidence/allocation01/cumulative-registry.json", "b104b7e6653b41b58ba76b3409499e0fe3193a244effe739964f347384db8b1f"),
    "r14_allocation": ("Results/primary/20260912T204759Z-2.3.1.1.1-r14-evidence/allocation01/cumulative-allocation.json", "c3af58329f0b7ad1cfa9252eae05d7dfafe27218bfdb4b693eb0b2be2794c73f"),
}
MISSING = tuple(f"fg:item:{number:06d}" for number in range(3, 14))
VERSION = "curriculum-v1-reconciled-551-candidate.1"
BASELINE_PATHS = {
    "identity_baseline": INPUTS["r13_registry"][0].replace("Results/primary/", "Results/"),
    "allocation_baseline": INPUTS["r13_allocation"][0].replace("Results/primary/", "Results/"),
    "lineage_baseline": INPUTS["r13_lineage"][0].replace("Results/primary/", "Results/"),
}
ALLOCATION_PATH = INPUTS["r14_allocation"][0].replace("Results/primary/", "Results/")


class ReconciliationError(ValueError):
    """An exact source, identity or allocation precondition failed."""


def require(ok: bool, code: str, detail: str) -> None:
    if not ok:
        raise ReconciliationError(f"{code}: {detail}")


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def encoded(value: object) -> bytes:
    return canonical(value) + b"\n"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def indexed(items: list[dict], key: str, label: str) -> dict[str, dict]:
    result: dict[str, dict] = {}
    for item in items:
        identity = item[key]
        require(identity not in result, "DUPLICATE_ID", f"{label} {identity}")
        result[identity] = item
    return result


def source_root(root: Path) -> Path:
    root = root.resolve()
    actual = subprocess.check_output(["git", "rev-parse", "--show-toplevel"], cwd=root, text=True).strip()
    require(root == Path(actual).resolve(), "ROOT", "supplied root is not the Git top level")
    return root


def load_inputs(root: Path) -> tuple[dict[str, dict], dict[str, dict]]:
    data: dict[str, dict] = {}
    manifest: dict[str, dict] = {}
    for name, (relative, expected) in INPUTS.items():
        path = root / relative
        raw = path.read_bytes()
        actual = digest(raw)
        require(actual == expected, "INPUT_DRIFT", f"{relative}: {actual} != {expected}")
        data[name] = json.loads(raw)
        manifest[name] = {"path": relative, "bytes": len(raw), "sha256": actual}
    return data, manifest


def compose(data: dict[str, dict]) -> dict[str, dict]:
    current = data["current_package"]
    registry = data["current_registry"]
    profile = data["current_profile"]
    controls = data["control_package"]
    control_registry = data["control_registry"]
    control_profile = data["control_profile"]
    report = data["reviewed_report"]
    r13_entities = indexed(data["r13_registry"]["entities"], "id", "r13 entity")
    r14_entities = indexed(data["r14_registry"]["entities"], "id", "r14 entity")
    current_records = indexed(current["records"], "id", "current record")
    report_records = indexed(report["records"], "id", "reviewed record")
    current_entities = indexed(registry["entities"], "id", "current entity")
    control_entities = indexed(control_registry["entities"], "id", "control entity")
    require(len(current_records) == 540 and len(current_entities) == 5633, "CURRENT_SCOPE", "expected 540 records / 5633 entities")
    require(profile["reference_package"] == {k: v for k, v in current.items() if k != "workbook_catalog"}
            and profile["reference_registry"] == {k: v for k, v in registry.items() if k != "workbook_catalog"}
            and profile["workbook_catalog"] == current["workbook_catalog"] == registry["workbook_catalog"],
            "CURRENT_PROFILE", "reference package/registry/catalog do not bind current values")
    require(len(report_records) == 120 and len(data["r13_allocation"]["records"]) == 515,
            "REVIEW_SCOPE", "reviewed r01/r13 record counts changed")

    historic: list[dict] = []
    history_events: set[str] = set()
    history_variants: set[str] = set()
    needed_sources: set[str] = set()
    r13_allocations = data["r13_allocation"]["records"]
    lineage = data["r13_lineage"]["records"]
    for identity in MISSING:
        require(identity not in current_records, "TARGET_PRESENT", identity)
        row = report_records.get(identity)
        require(row is not None, "REVIEW_MISSING", identity)
        record = row["preserved_record"]
        require(record["id"] == identity and record["content_revision"] == 3,
                "REVIEW_IDENTITY", identity)
        hash_ = digest(canonical(record))
        require(hash_ == row["record_sha256"] == lineage[identity]["record_sha256"] and
                record["content_revision"] == lineage[identity]["content_revision"],
                "LINEAGE_CONFLICT", identity)
        require(record.get("runtime_eligible") is False and record.get("status") == "converted_candidate",
                "ADMISSION_CONFLICT", identity)
        allocation = r13_allocations[identity]
        events = {event["event_id"] for event in record["events"]}
        variants = {variant["id"] for variant in record["variants"]}
        require(len(events) == len(record["events"]) and len(variants) == len(record["variants"]),
                "RECORD_DUPLICATE", identity)
        require(events == set(allocation["occurrences"].values()) and
                variants == set(allocation["variants"].values()) and
                record["legacy_level"] == allocation["legacy_level"],
                "ALLOCATION_CONFLICT", identity)
        require(not history_events.intersection(events) and not history_variants.intersection(variants),
                "HISTORY_COLLISION", identity)
        history_events.update(events)
        history_variants.update(variants)
        needed_sources.update(record["source_refs"])
        historic.append(record)

    current_event_ids = [event["event_id"] for row in current["records"] for event in row["events"]]
    current_variant_ids = [variant["id"] for row in current["records"] for variant in row["variants"]]
    require(len(current_event_ids) == len(set(current_event_ids)) and
            len(current_variant_ids) == len(set(current_variant_ids)), "CURRENT_DUPLICATE", "event or variant")
    require(not history_events.intersection(current_event_ids), "EVENT_COLLISION",
            str(sorted(history_events.intersection(current_event_ids))[:3]))
    require(not history_variants.intersection(current_variant_ids), "VARIANT_COLLISION",
            str(sorted(history_variants.intersection(current_variant_ids))[:3]))

    old_sources = controls["sources"]
    sources = dict(current["sources"])
    for ref in sorted(needed_sources):
        require(ref in old_sources, "SOURCE_MISSING", ref)
        require(ref not in sources or sources[ref] == old_sources[ref], "SOURCE_CONFLICT", ref)
        sources[ref] = old_sources[ref]
    require(len(sources) == 657, "SOURCE_SCOPE", f"expected 657 passages, got {len(sources)}")
    event_sources = dict(profile["event_sources"])
    for event in sorted(history_events):
        ref = control_profile["event_sources"].get(event)
        require(ref in needed_sources and ref in sources, "EVENT_SOURCE", event)
        require(event not in event_sources, "EVENT_SOURCE_COLLISION", event)
        event_sources[event] = ref
    require(set(event_sources) == set(current_event_ids).union(history_events),
            "EVENT_SOURCE_COVERAGE", "event mapping differs from exact union")

    added_entities: dict[str, dict] = {}
    for identity in MISSING:
        require(identity in control_entities and identity in r13_entities, "ENTITY_MISSING", identity)
        item = control_entities[identity]
        module = control_entities[item["parent"]]
        workbook = control_entities[module["parent"]]
        for entity in (workbook, module, item):
            added_entities[entity["id"]] = entity
        for variant in next(row for row in historic if row["id"] == identity)["variants"]:
            entity = control_entities[variant["id"]]
            require(entity["parent"] == identity, "ENTITY_PARENT", variant["id"])
            added_entities[variant["id"]] = entity
    added_entities = {id_: value for id_, value in added_entities.items() if id_ not in current_entities}
    require(len(added_entities) == 54, "ENTITY_SCOPE", f"expected 54 missing entities, got {len(added_entities)}")
    for identity, entity in added_entities.items():
        require(entity == r13_entities.get(identity) == r14_entities.get(identity), "ENTITY_CONFLICT", identity)
    for identity, entity in current_entities.items():
        require(entity == r14_entities.get(identity), "CURRENT_ENTITY_CONFLICT", identity)
    require(set(current_entities).union(added_entities) == set(r14_entities),
            "R14_ENTITY_COVERAGE", "reviewed r14 head differs from exact entity union")

    records = sorted([*current["records"], *historic], key=lambda row: row["id"])
    all_record_ids = {row["id"] for row in records}
    require(len(records) == 551 and all_record_ids == set(data["r14_allocation"]["records"]),
            "R14_ALLOCATION_COVERAGE", "551-record union differs from r14 allocation")
    for row in records:
        allocation = data["r14_allocation"]["records"][row["id"]]
        require({e["event_id"] for e in row["events"]} == set(allocation["occurrences"].values()) and
                {v["id"] for v in row["variants"]} == set(allocation["variants"].values()) and
                row["legacy_level"] == allocation["legacy_level"], "R14_ALLOCATION_CONFLICT", row["id"])
        require(row.get("runtime_eligible") is False, "ADMISSION_CONFLICT", row["id"])

    package = dict(current, content_version=VERSION, sources=sources, records=records)
    new_registry = dict(registry, entities=data["r14_registry"]["entities"])
    expected_profile = dict(profile,
                            reference_package={k: v for k, v in package.items() if k != "workbook_catalog"},
                            reference_registry={k: v for k, v in new_registry.items() if k != "workbook_catalog"},
                            event_sources=event_sources,
                            classification="converted_candidate_reference")
    selected: list[dict] = []
    excluded: list[dict] = []
    for artifact in profile["authority_artifacts"]:
        role, path = artifact["role"], artifact["path"]
        keep = True
        if role in BASELINE_PATHS:
            keep = path == BASELINE_PATHS[role]
        elif role == "candidate_identity_allocation":
            keep = False
        elif role == "predecessor_validation" and path.endswith("/lineage01/base-report.json"):
            keep = False  # Superseded by reviewed r01 120-record proof; bytes remain immutable.
        (selected if keep else excluded).append(artifact)
    selected.append({"path": ALLOCATION_PATH, "role": "candidate_identity_allocation",
                     "sha256": INPUTS["r14_allocation"][1]})
    require(len({a["path"] for a in selected}) == len(selected), "AUTHORITY_DUPLICATE", "selected paths")
    for role in (*BASELINE_PATHS, "candidate_identity_allocation"):
        require(sum(a["role"] == role for a in selected) == 1, "BASELINE_ROLE", role)
    require(sum(a["role"] == "predecessor_validation" for a in selected) == 13,
            "PREDECESSOR_SCOPE", "expected r01-r13 disjoint reports")
    expected_profile["authority_artifacts"] = selected

    generation = dict(data["current_generation"])
    generation.update(records=551, events=len(current_event_ids) + len(history_events),
                      variants=len(current_variant_ids) + len(history_variants), current_entities=5687,
                      passages=len(sources), workbooks=sorted({row["legacy_level"] for row in records}),
                      classification="Build-only reviewed-ID reconciliation candidate; no human/runtime admission")
    generation["identities"] = {
        "package.json": digest(encoded(package)), "identity-registry.json": digest(encoded(new_registry)),
        "expected-profile.json": digest(encoded(expected_profile)),
    }
    generation["reconciliation"] = {"version": VERSION, "restored_ids": list(MISSING),
                                    "current_records_preserved": 540, "historical_revision": 3,
                                    "active_baseline": "r13 cumulative", "allocation": "r14 cumulative",
                                    "runtime_admitted": False, "human_curriculum_review": "Pending"}
    selection = {"version": "parallel10-active-authority-selection.1", "candidate_only": True,
                 "selected": selected, "excluded_historical": excluded,
                 "reason": "Reviewed r01 proof supersedes the duplicate 14-record base report; r13 is the latest complete predecessor baseline and r14 cumulative allocation covers all 551 IDs. Historical files and roles in the current profile are unchanged."}
    return {"package.json": package, "identity-registry.json": new_registry,
            "expected-profile.json": expected_profile, "generation.json": generation,
            "authority-selection.json": selection}


def write_candidate(output: Path, candidate: dict[str, dict], manifest: dict[str, dict]) -> None:
    require(not output.exists(), "OUTPUT_EXISTS", str(output))
    output.mkdir(parents=True)
    for name, value in candidate.items():
        (output / name).write_bytes(encoded(value))
    identities = {name: {"bytes": len(encoded(value)), "sha256": digest(encoded(value))}
                  for name, value in candidate.items()}
    (output / "input-output-identities.json").write_bytes(encoded({
        "version": VERSION, "inputs": manifest, "outputs": identities,
        "classification": "Build-only non-admitted reconciliation; no canonical Content edit",
    }))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        root = source_root(args.root)
        output = args.output.resolve()
        build_root = (root / "Build/parallel-10").resolve()
        require(output.is_relative_to(build_root) and output != build_root,
                "OUTPUT_SCOPE", "candidate must be in Build/parallel-10")
        data, manifest = load_inputs(root)
        candidate = compose(data)
        write_candidate(output, candidate, manifest)
        print(f"RECONCILIATION PASS records=551 entities=5687 sources=657 output={output}")
        return 0
    except (ReconciliationError, OSError, KeyError, TypeError) as error:
        print(f"RECONCILIATION REFUSED {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
