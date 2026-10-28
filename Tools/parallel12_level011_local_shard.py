#!/usr/bin/env python3
"""Allocate and verify a nonadmitted, native-valid Level11 local shard."""

from __future__ import annotations

import argparse
import copy
import json
import re
from collections import Counter
from pathlib import Path

import parallel12_level010_local_shard as l10tool
import parallel12_level011_schema1_unallocated as source

ROOT = Path(__file__).resolve().parents[1]
OUT = Path("Build/parallel-12/level011-local-shard-r01")
L10 = Path("Build/parallel-12/level010-local-shard-r01")
PROPOSAL = Path("Build/parallel-12/level011-schema1-unallocated-r01")
R05 = Path("Build/parallel-10/three-real-shard-manifest-r05")
BASE = l10tool.l8tool.BASE
L7 = l10tool.l8tool.L7
L8 = l10tool.L8
PINS = {
    **{p: h for p, h in l10tool.PINS.items() if p.parent in (BASE, L7, L8)},
    L10 / "package.json": "b4e59b36a9dd20a8dbdc8b16a9c20c8eafb6d054665f83ec86742424c57896d0",
    L10 / "identity-registry.json": "7415e720ffab238ccd43a82e30a9f486e402d8c33f19865ae466aa308ba52594",
    L10 / "expected-profile.json": "fca1af76befb72b9fdf4b828821435817c13fd5c884bac11c6f95a9cd563c90e",
    L10 / "candidate-allocation.json": "9474561fe9a097313307be06ca0c38b707bcb7f3a17760a4a226ecf5633a5e65",
    L10 / "local-summary.json": "f7a2b732a684156ca90d2107f9dd1f9027c39262e1d5ed7c8a2f914315d21227",
    L10 / "native-report.json": "5bb9c054a7a5e77315d2f273deb26583ab2ebb46264429c52573781f94e89d1e",
    R05 / "manifest.json": "1807bd7efe0e60b8941ed0b2563518957e333a71deec671ddcc5ce945bfb1f64",
    R05 / "summary.json": "7bb44a62ce15c879a106eb2a3ad0245219fd8bbb889e3f046834550d79e058e4",
    R05 / "completion-contract.json": "794e94e0b1d7a35e8dd372f2af22f6e11e31f27d0183b7698df5aadb9a546b42",
    PROPOSAL / "field-proposal.json": "ac5babac3ab68642d1f34e88480e66ac3cf764032edbf3c19b9eb0cfbfd68cd1",
    PROPOSAL / "allocation-handoff.json": "d66796f96eb8fb3b6784ed847fdbe0f2539059d9508d6d561b5b54f73b475855",
    source.TXT: source.PINS[source.TXT][1],
    source.PDF: source.PINS[source.PDF][1],
}
FILES = l10tool.FILES
GUIDANCE = ("L11-TXT1-4-6", "L11-TXT1-9-15", "L11-TXT1-24-26",
            "L11-TXT1-29-31", "L11-TXT1-34-41", "L11-TXT1-44-45")


class ShardError(ValueError):
    pass


def need(ok: bool, code: str) -> None:
    if not ok:
        raise ShardError(code)


def encode(obj: object) -> bytes:
    return l10tool.l8tool.encode(obj)


def sha(raw: bytes) -> str:
    return l10tool.l8tool.sha(raw)


def read(root: Path, path: Path) -> dict:
    return l10tool.l8tool.read(root, path)


def number(identity: str) -> int:
    return l10tool.l8tool.number(identity)


def pin(root: Path) -> None:
    need(root.resolve() == ROOT.resolve(), "ROOT_DRIFT")
    for path, expected in PINS.items():
        need(sha((root / path).read_bytes()) == expected, f"INPUT_PIN_DRIFT {path}")


def floors(registries: tuple[dict, ...]) -> dict[str, int]:
    base = registries[0]
    result = {}
    for kind, plural in (("module", "modules"), ("item", "items"), ("variant", "variants")):
        used = [number(e["id"]) for reg in registries for e in reg["entities"] if e["kind"] == kind]
        reserved = []
        for entry in base["workbook_catalog"]["entries"]:
            bounds = entry.get("reserved_playable_identity_ranges", {}).get(plural)
            if bounds:
                need(len(bounds) == 2 and all(x.startswith(f"fg:{kind}:") for x in bounds),
                     "RESERVATION_SHAPE")
                reserved.append(number(bounds[1]))
        result[kind] = max(used + reserved) + 1
    need(result == {"module": 1020, "item": 1020, "variant": 6946}, "ALLOCATION_FLOOR_DRIFT")
    return result


def txt_passage(lines: list[str], ref: str) -> dict:
    match = re.fullmatch(r"L11-TXT1-(\d+)-(\d+)", ref)
    need(match is not None, "TXT_REF")
    first, last = map(int, match.groups())
    need(1 <= first <= last <= len(lines), "TXT_SPAN")
    text = "\n".join(lines[first - 1:last])
    return {"path": str(source.TXT), "sha256": PINS[source.TXT], "format": "txt",
            "first_line": first, "last_line": last, "text": text, "text_sha256": sha(text.encode())}


def passages(root: Path, handoff: dict) -> dict:
    from pypdf import PdfReader
    lines = (root / source.TXT).read_text().splitlines()
    pdf = PdfReader(str(root / source.PDF))
    need(len(pdf.pages) == 10, "PDF_COUNT")
    result = {ref: txt_passage(lines, ref) for ref in GUIDANCE}
    for page in range(2, 11):
        text = pdf.pages[page - 1].extract_text()
        result[f"L11-PDF1-p{page}"] = {"path": str(source.PDF), "sha256": PINS[source.PDF],
                                       "format": "pdf", "page": page, "text": text,
                                       "text_sha256": sha(text.encode())}
    for entry in handoff["source_map"]:
        ref = entry["txt"]
        need(ref not in result, "DUPLICATE_SOURCE_REF")
        section = txt_passage(lines, ref)
        need(section["text_sha256"] == entry["txt_passage_sha256"] and
             section["text"].startswith(f"Exercise {entry['exercise_number']:03d}: {entry['code']}"),
             "TXT_CARD")
        need(re.search(rf"\b{entry['exercise_number']:03d}\b\s+{entry['code']}\b",
                       result[entry["pdf"]]["text"]) is not None, "PDF_CARD")
        result[ref] = section
    need(len(result) == 123, "SOURCE_COUNT")
    return result


def derive(root: Path = ROOT, proposal_override: dict | None = None) -> dict[str, dict]:
    pin(root)
    paths = (BASE, L7, L8, L10)
    packages = tuple(read(root, path / "package.json") for path in paths)
    registries = tuple(read(root, path / "identity-registry.json") for path in paths)
    l10_profile = read(root, L10 / "expected-profile.json")
    r05 = read(root, R05 / "summary.json")
    need(r05["validated_workbooks"] == [7, 8, 10] and r05["aggregate_complete"] is False and
         r05["admitted"] is False and r05["next_allocation_floor"] ==
         {"module": 1020, "item": 1020, "variant": 6946} and
         l10_profile["reference_package"] == packages[-1] and
         l10_profile["reference_registry"] == registries[-1] and
         [len(p["records"]) for p in packages] == [659, 108, 108, 108] and
         "fg:workbook:000011" not in {e["id"] for reg in registries for e in reg["entities"]},
         "PREDECESSOR_SCOPE")
    floor = floors(registries)
    expected_proposal, expected_handoff = source.build(root)
    proposal = proposal_override if proposal_override is not None else read(root, PROPOSAL / "field-proposal.json")
    handoff = read(root, PROPOSAL / "allocation-handoff.json")
    need(proposal == expected_proposal and handoff == expected_handoff, "SOURCE_PROPOSAL_DRIFT")
    source.verify(proposal, handoff)
    refs = passages(root, handoff)
    records, entities, allocations, event_sources, source_map = [], [], {}, {}, []
    entities.append({"id": "fg:workbook:000011", "kind": "workbook",
                     "label": "Legacy Level11 three-position relay", "parent": "fg:course:000001"})
    for index, row in enumerate(proposal["records"]):
        item = f"fg:item:{floor['item'] + index:06d}"
        module = f"fg:module:{floor['module'] + index:06d}"
        fields = copy.deepcopy(row["schema1_fields"])
        handoff_row = handoff["source_map"][index]
        need(row["source_local_key"] == handoff_row["source_local_key"] and
             fields["id"] is fields["workbook_id"] is fields["module_id"] is fields["lineage"] is None and
             fields["source_refs"] == [handoff_row["txt"], handoff_row["pdf"], *GUIDANCE],
             "SOURCE_IDENTITY_OR_REFS")
        fields.update(id=item, workbook_id="fg:workbook:000011", module_id=module, lineage={"kind": "new"})
        entities.extend(({"id": module, "kind": "module", "label": f"Level11 Exercise {index + 1:03d} {row['code']}",
                          "parent": "fg:workbook:000011"},
                         {"id": item, "kind": "item", "label": fields["title"], "parent": module}))
        occurrences = {}
        for ordinal, event in enumerate(fields["events"], 1):
            need(event["event_id"] is event["onset_q"] is event["duration_q"] is None,
                 "SOURCE_TIMING_OR_ID")
            eid = f"{item}:event:{ordinal:04d}"
            event["event_id"] = eid
            occurrences[f"{row['source_local_key']}:note:{ordinal:03d}"] = eid
            event_sources[eid] = handoff_row["txt"]
        variants, landings = {}, {}
        for vi, (variant, membership) in enumerate(zip(fields["variants"], row["variant_memberships"], strict=True)):
            need(variant["id"] is variant["event_ids"] is None and variant["label"] == membership["label"] and
                 len(membership["event_local_ordinals"]) == 24 and
                 len(membership["landing_event_local_ordinals"]) == 12, "VARIANT_SOURCE")
            vid = f"fg:variant:{floor['variant'] + index * 4 + vi:06d}"
            variant["id"] = vid
            variant["event_ids"] = [fields["events"][ordinal - 1]["event_id"]
                                    for ordinal in membership["event_local_ordinals"]]
            variants[variant["label"]] = vid
            landings[variant["label"]] = [fields["events"][ordinal - 1]["event_id"]
                                           for ordinal in membership["landing_event_local_ordinals"]]
            entities.append({"id": vid, "kind": "variant", "label": variant["label"], "parent": item})
        need(len(fields["events"]) == 48 and len(occurrences) == 48 and len(variants) == 4, "CASE_COUNT")
        records.append(fields)
        allocations[item] = {"legacy_level": 11, "occurrences": occurrences, "variants": variants}
        source_map.append({"item_id": item, **handoff_row, "variant_landing_event_ids": landings})
    pkg = {k: v for k, v in packages[-1].items() if k not in ("records", "sources")}
    pkg.update(content_version="curriculum-v1-level011-local-shard-build-only.1",
               records=records, sources=refs)
    reg = {"identity_version": registries[0]["identity_version"], "rules": registries[0]["rules"],
           "entities": [registries[0]["entities"][0], *entities]}
    identity_baseline = {"identity_version": reg["identity_version"], "rules": reg["rules"],
                         "entities": [reg["entities"][0]]}
    allocation_baseline = {"version": "control-allocation.1", "authority":
                           "Local Level11 course-only preallocation; 659, Level7, Level8 and Level10 pinned separately", "records": {}}
    lineage_baseline = {"version": "lineage-baseline.1", "records": {}}
    allocation = {"version": "control-allocation.1", "authority":
                  "P12 Level11 local shard only; global aggregate validation required; no admission", "records": allocations}
    profile = {k: v for k, v in l10_profile.items() if k not in
               ("reference_package", "reference_registry", "event_sources", "authority_artifacts")}
    profile.update(reference_package=pkg, reference_registry=reg, event_sources=event_sources)
    profile["authority_artifacts"] = [a for a in l10_profile["authority_artifacts"] if a["role"] in
                                      ("source_manifest", "source_acceptance", "current_schema_freeze")]
    for role, name, obj in (("identity_baseline", "identity-baseline.json", identity_baseline),
                            ("allocation_baseline", "allocation-baseline.json", allocation_baseline),
                            ("lineage_baseline", "lineage-baseline.json", lineage_baseline),
                            ("candidate_identity_allocation", "candidate-allocation.json", allocation)):
        profile["authority_artifacts"].append({"path": str(OUT / name), "role": role,
                                               "sha256": sha(encode(obj))})
    summary = {"schema": "parallel12-level011-local-shard-summary.1", "status": "local_reference_only",
               "foundation_sha256": {p.name: PINS[p] for p in PINS if p.parent == BASE},
               "level007_sha256": {p.name: PINS[p] for p in PINS if p.parent == L7},
               "level008_sha256": {p.name: PINS[p] for p in PINS if p.parent == L8},
               "level010_sha256": {p.name: PINS[p] for p in PINS if p.parent == L10},
               "r05_manifest_sha256": PINS[R05 / "manifest.json"],
               "source_proposal_sha256": PINS[PROPOSAL / "field-proposal.json"],
               "source_handoff_sha256": PINS[PROPOSAL / "allocation-handoff.json"],
               "allocation_floors": floor,
               "counts": {"records": 108, "entities": 650, "sources": 123, "events": 5184, "variants": 432},
               "source_map": source_map, "aggregate_complete": False,
               "admitted": False, "runtime_eligible": False}
    output = {"package.json": pkg, "identity-registry.json": reg,
              "expected-profile.json": profile, "candidate-allocation.json": allocation,
              "identity-baseline.json": identity_baseline, "allocation-baseline.json": allocation_baseline,
              "lineage-baseline.json": lineage_baseline, "local-summary.json": summary}
    check_global(output, packages, registries)
    return output


def check_global(output: dict, packages: tuple[dict, ...], registries: tuple[dict, ...]) -> None:
    pkg, reg, prof, allocation = (output[n] for n in
                                  ("package.json", "identity-registry.json", "expected-profile.json", "candidate-allocation.json"))
    new = reg["entities"][1:]
    ids = [e["id"] for e in new]
    old_ids = {e["id"] for ancestor in registries for e in ancestor["entities"]}
    need(len(ids) == 649 and len(reg["entities"]) == 650 and len(ids) == len(set(ids)) and
         not old_ids.intersection(ids), "GLOBAL_ENTITY_COLLISION")
    for kind, plural in (("module", "modules"), ("item", "items"), ("variant", "variants")):
        used = [number(e["id"]) for ancestor in registries for e in ancestor["entities"] if e["kind"] == kind]
        mine = [number(e["id"]) for e in new if e["kind"] == kind]
        need(min(mine) > max(used), f"GLOBAL_ID_ORDER {kind}")
        for entry in registries[0]["workbook_catalog"]["entries"]:
            bounds = entry.get("reserved_playable_identity_ranges", {}).get(plural)
            if bounds:
                lo, hi = map(number, bounds)
                need(all(not lo <= x <= hi for x in mine), f"RESERVED_ID_COLLISION {kind}")
    events = [e["event_id"] for record in pkg["records"] for e in record["events"]]
    old_events = {e["event_id"] for ancestor in packages for record in ancestor["records"]
                  for e in record["events"]}
    need(len(events) == 5184 and len(events) == len(set(events)) and
         not old_events.intersection(events), "GLOBAL_EVENT_COLLISION")
    refs = set(pkg["sources"])
    need(len(refs) == 123 and all(not refs.intersection(p["sources"]) for p in packages) and
         set(prof["event_sources"]) == set(events) and
         all(ref in refs for ref in prof["event_sources"].values()), "GLOBAL_SOURCE_COLLISION")
    need(set(allocation["records"]) == {r["id"] for r in pkg["records"]} and
         all(r["lineage"] == {"kind": "new"} and r["content_revision"] == 1 and
             r["runtime_eligible"] is False and r["timing"]["status"] == "unresolved" and
             all(e["onset_q"] is e["duration_q"] is None for e in r["events"])
             for r in pkg["records"]), "LINEAGE_OR_TIMING")
    need(prof["reference_package"] == pkg and prof["reference_registry"] == reg and
         all("workbook_catalog" not in obj for obj in (pkg, reg, prof)) and
         output["local-summary.json"]["aggregate_complete"] is False and
         output["local-summary.json"]["admitted"] is False, "LOCAL_AUTHORITY")


def verify_native(root: Path, output: dict) -> dict:
    report = read(root, OUT / "native-report.json")
    need(report["exit_code"] == 2 and report["valid_reference"] is True and
         report["curriculum_playback_authorized"] is False, "NATIVE_AUTHORITY")
    for name, key in (("package.json", "package_sha256"),
                      ("identity-registry.json", "registry_sha256"),
                      ("expected-profile.json", "profile_sha256")):
        need(report[key] == sha(encode(output[name])) == sha((root / OUT / name).read_bytes()),
             f"NATIVE_INPUT_BINDING {name}")
    need(report["coverage"] == {"events": 5184, "expected_entities": 650,
                                "expected_passages": 123, "expected_records": 108,
                                "observed_entities": 650, "observed_passages": 123,
                                "observed_records": 108, "variant_event_memberships": 10368,
                                "variants": 432}, "NATIVE_COVERAGE")
    issues = Counter((x["severity"], x["code"]) for x in report["issues"])
    need(issues == {("unresolved", "MODEL_unresolved_time"): 5184,
                    ("unresolved", "VARIANT_BINDING_UNRESOLVED"): 432,
                    ("not_admitted", "MODEL_not_admitted"): 108}, "NATIVE_ISSUES")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("build", "verify", "verify-native"))
    args = parser.parse_args()
    output = derive()
    if args.command == "build":
        (ROOT / OUT).mkdir(parents=True, exist_ok=True)
        for name in FILES:
            (ROOT / OUT / name).write_bytes(encode(output[name]))
    else:
        for name in FILES:
            need((ROOT / OUT / name).read_bytes() == encode(output[name]), f"OUTPUT_DRIFT {name}")
        if args.command == "verify-native":
            verify_native(ROOT, output)
    print(json.dumps({"status": "level011_local_nonadmitted_reference",
                      "counts": output["local-summary.json"]["counts"],
                      "allocation_floors": output["local-summary.json"]["allocation_floors"]}, sort_keys=True))


if __name__ == "__main__":
    main()
