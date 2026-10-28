#!/usr/bin/env python3
"""Build and verify a source-complete, nonadmitted Level10 local schema1 shard."""

from __future__ import annotations

import argparse
import copy
import json
import re
from collections import Counter
from pathlib import Path

import parallel12_level008_local_shard as l8tool
import parallel12_level010_schema1_unallocated as source

ROOT = Path(__file__).resolve().parents[1]
OUT = Path("Build/parallel-12/level010-local-shard-r01")
L8 = Path("Build/parallel-12/level008-local-shard-r01")
PROPOSAL = Path("Build/parallel-12/level010-schema1-unallocated-r01")
PINS = {
    **{p: h for p, h in l8tool.PINS.items() if p.parent in (l8tool.BASE, l8tool.L7)},
    L8 / "package.json": "588947d8420086f3259626caf704473e08242a2e543714e34bcc01cb0211c032",
    L8 / "identity-registry.json": "74affebdad7c3b46f3477c2ac8eabaa03bf2d899338b313a53551e4d5d0affc7",
    L8 / "expected-profile.json": "e2697b96d6eadc1942dcfe2870da22a364e4e6d19e967adb37566922fae95284",
    L8 / "candidate-allocation.json": "e4757064fd1b6e0f7d8b1d620edb41f3d8385df0df4f4124560cab42a5ce81ec",
    L8 / "local-summary.json": "8920d2da9af446def46dc1fa76ae2443bb3d9a40dae392f6a8b7ddc6e8189a0e",
    L8 / "native-report.json": "a5733c5065e1de86d8834c04bf306efc210acce0a921136291824656106fc9d6",
    PROPOSAL / "field-proposal.json": "0a855d720b2cf57ac831accf150a2e1474141657c5b3c99482e6483acf3afe66",
    PROPOSAL / "allocation-handoff.json": "1064daaffbb1493d6402e7af36f2bf4fecfd15a0f6680f1e2e1c3a9ed3b5adf8",
    source.TXT: source.PINS[source.TXT][1],
    source.PDF: source.PINS[source.PDF][1],
}
FILES = l8tool.FILES


class ShardError(ValueError):
    pass


def need(ok: bool, code: str) -> None:
    if not ok:
        raise ShardError(code)


def pin(root: Path) -> None:
    need(root.resolve() == ROOT.resolve(), "ROOT_DRIFT")
    for path, expected in PINS.items():
        need(l8tool.sha((root / path).read_bytes()) == expected, f"INPUT_PIN_DRIFT {path}")


def floors(base: dict, level7: dict, level8: dict) -> dict[str, int]:
    result = {}
    for kind, plural in (("module", "modules"), ("item", "items"), ("variant", "variants")):
        used = [l8tool.number(e["id"]) for reg in (base, level7, level8)
                for e in reg["entities"] if e["kind"] == kind]
        reserved = []
        for entry in base["workbook_catalog"]["entries"]:
            bounds = entry.get("reserved_playable_identity_ranges", {}).get(plural)
            if bounds:
                need(len(bounds) == 2 and all(x.startswith(f"fg:{kind}:") for x in bounds),
                     "RESERVATION_SHAPE")
                reserved.append(l8tool.number(bounds[1]))
        result[kind] = max(used + reserved) + 1
    need(result == {"module": 912, "item": 912, "variant": 6082}, "ALLOCATION_FLOOR_DRIFT")
    return result


def passage(lines: list[str], first: int, last: int) -> dict:
    need(1 <= first <= last <= len(lines), "TXT_SPAN")
    text = "\n".join(lines[first - 1:last])
    return {"path": str(source.TXT), "sha256": PINS[source.TXT], "format": "txt",
            "first_line": first, "last_line": last, "text": text,
            "text_sha256": l8tool.sha(text.encode())}


def passages(root: Path, handoff: dict) -> dict:
    from pypdf import PdfReader
    lines = (root / source.TXT).read_text().splitlines()
    pdf = PdfReader(str(root / source.PDF))
    need(len(pdf.pages) == 19, "PDF_COUNT")
    result = {"L10-TXT1-1-33": passage(lines, 1, 33)}
    for page in range(2, 20):
        text = pdf.pages[page - 1].extract_text()
        result[f"L10-PDF1-p{page}"] = {"path": str(source.PDF), "sha256": PINS[source.PDF],
                                       "format": "pdf", "page": page, "text": text,
                                       "text_sha256": l8tool.sha(text.encode())}
    for row in handoff["source_map"]:
        for mode in row["modes"]:
            match = re.fullmatch(r"L10-TXT1-(\d+)-(\d+)", mode["txt"])
            need(match is not None and mode["txt"] not in result, "SOURCE_REF")
            first, last = map(int, match.groups())
            section = passage(lines, first, last)
            need(section["text_sha256"] == mode["txt_passage_sha256"] and
                 section["text"].startswith(f"Exercise {row['exercise_number']:03d}: {row['code']}"),
                 "TXT_CARD")
            need(re.search(rf"\b{row['exercise_number']:03d}\b\s+{row['code']}\b",
                           result[mode["pdf"]]["text"]) is not None, "PDF_CARD")
            result[mode["txt"]] = section
    need(len(result) == 235, "SOURCE_COUNT")
    return result


def derive(root: Path = ROOT, proposal_override: dict | None = None) -> dict[str, dict]:
    pin(root)
    base_pkg, base_reg = (l8tool.read(root, l8tool.BASE / n) for n in
                          ("package.json", "identity-registry.json"))
    l7_pkg, l7_reg = (l8tool.read(root, l8tool.L7 / n) for n in
                      ("package.json", "identity-registry.json"))
    l8_pkg, l8_reg, l8_prof = (l8tool.read(root, L8 / n) for n in
                                ("package.json", "identity-registry.json", "expected-profile.json"))
    need(len(base_pkg["records"]) == 659 and len(l7_pkg["records"]) == 108 and
         len(l8_pkg["records"]) == 108 and l8_prof["reference_package"] == l8_pkg and
         l8_prof["reference_registry"] == l8_reg and
         "fg:workbook:000010" not in {e["id"] for reg in (base_reg, l7_reg, l8_reg)
                                      for e in reg["entities"]}, "PREDECESSOR_SCOPE")
    floor = floors(base_reg, l7_reg, l8_reg)
    expected_proposal, expected_handoff = source.build(root)
    proposal = proposal_override if proposal_override is not None else l8tool.read(root, PROPOSAL / "field-proposal.json")
    handoff = l8tool.read(root, PROPOSAL / "allocation-handoff.json")
    need(proposal == expected_proposal and handoff == expected_handoff, "SOURCE_PROPOSAL_DRIFT")
    source.verify(proposal, handoff)
    refs = passages(root, handoff)
    records, entities, allocation, event_sources, source_map = [], [], {}, {}, []
    entities.append({"id": "fg:workbook:000010", "kind": "workbook",
                     "label": "Legacy Level10 odd-count position transfer", "parent": "fg:course:000001"})
    for index, row in enumerate(proposal["records"]):
        item = f"fg:item:{floor['item'] + index:06d}"
        module = f"fg:module:{floor['module'] + index:06d}"
        fields = copy.deepcopy(row["schema1_fields"])
        handoff_row = handoff["source_map"][index]
        need(row["source_local_key"] == handoff_row["source_local_key"] and
             fields["id"] is fields["module_id"] is fields["workbook_id"] is fields["lineage"] is None,
             "SOURCE_IDENTITY")
        need(fields["source_refs"] == [handoff_row["modes"][0]["txt"], handoff_row["modes"][0]["pdf"],
                                       handoff_row["modes"][1]["txt"], handoff_row["modes"][1]["pdf"],
                                       "L10-TXT1-1-33"], "SOURCE_REFS")
        fields.update(id=item, module_id=module, workbook_id="fg:workbook:000010", lineage={"kind": "new"})
        entities.extend(({"id": module, "kind": "module", "label": f"Level10 Exercise {index + 1:03d} {row['code']}",
                          "parent": "fg:workbook:000010"},
                         {"id": item, "kind": "item", "label": fields["title"], "parent": module}))
        occurrences = {}
        for ordinal, event in enumerate(fields["events"], 1):
            need(event["event_id"] is event["onset_q"] is event["duration_q"] is None, "SOURCE_TIMING_OR_ID")
            event_id = f"{item}:event:{ordinal:04d}"
            event["event_id"] = event_id
            occurrences[f"{row['source_local_key']}:note:{ordinal:03d}"] = event_id
            event_sources[event_id] = handoff_row["modes"][0 if ordinal <= 48 else 1]["txt"]
        variants, landing_events = {}, {}
        for vi, (variant, membership) in enumerate(zip(fields["variants"], row["variant_memberships"], strict=True)):
            need(variant["id"] is variant["event_ids"] is None and variant["label"] == membership["label"] and
                 len(membership["event_local_ordinals"]) == 24 and len(membership["landing_event_local_ordinals"]) == 6,
                 "VARIANT_SOURCE")
            vid = f"fg:variant:{floor['variant'] + index * 8 + vi:06d}"
            variant["id"] = vid
            variant["event_ids"] = [fields["events"][ordinal - 1]["event_id"]
                                    for ordinal in membership["event_local_ordinals"]]
            variants[variant["label"]] = vid
            landing_events[variant["label"]] = [fields["events"][ordinal - 1]["event_id"]
                                                  for ordinal in membership["landing_event_local_ordinals"]]
            entities.append({"id": vid, "kind": "variant", "label": variant["label"], "parent": item})
        need(len(fields["events"]) == 96 and len(occurrences) == 96 and len(variants) == 8,
             "CASE_COUNT")
        records.append(fields)
        allocation[item] = {"legacy_level": 10, "occurrences": occurrences, "variants": variants}
        source_map.append({"item_id": item, **handoff_row,
                           "variant_landing_event_ids": landing_events})
    package = {k: v for k, v in l8_pkg.items() if k not in ("records", "sources")}
    package.update(content_version="curriculum-v1-level010-local-shard-build-only.1",
                   records=records, sources=refs)
    registry = {"identity_version": base_reg["identity_version"], "rules": base_reg["rules"],
                "entities": [base_reg["entities"][0], *entities]}
    identity_baseline = {"identity_version": registry["identity_version"], "rules": registry["rules"],
                         "entities": [registry["entities"][0]]}
    allocation_baseline = {"version": "control-allocation.1", "authority":
                           "Local Level10 course-only preallocation; 659, Level7 and Level8 pinned separately", "records": {}}
    lineage_baseline = {"version": "lineage-baseline.1", "records": {}}
    candidate = {"version": "control-allocation.1", "authority":
                 "P12 Level10 local shard only; global aggregate validation required; no admission", "records": allocation}
    profile = {k: v for k, v in l8_prof.items() if k not in
               ("reference_package", "reference_registry", "event_sources", "authority_artifacts")}
    profile.update(reference_package=package, reference_registry=registry, event_sources=event_sources)
    profile["authority_artifacts"] = [a for a in l8_prof["authority_artifacts"] if a["role"] in
                                      ("source_manifest", "source_acceptance", "current_schema_freeze")]
    for role, name, obj in (("identity_baseline", "identity-baseline.json", identity_baseline),
                            ("allocation_baseline", "allocation-baseline.json", allocation_baseline),
                            ("lineage_baseline", "lineage-baseline.json", lineage_baseline),
                            ("candidate_identity_allocation", "candidate-allocation.json", candidate)):
        profile["authority_artifacts"].append({"path": str(OUT / name), "role": role,
                                               "sha256": l8tool.sha(l8tool.encode(obj))})
    summary = {"schema": "parallel12-level010-local-shard-summary.1", "status": "local_reference_only",
               "foundation_sha256": {p.name: PINS[p] for p in PINS if p.parent == l8tool.BASE},
               "level007_sha256": {p.name: PINS[p] for p in PINS if p.parent == l8tool.L7},
               "level008_sha256": {p.name: PINS[p] for p in PINS if p.parent == L8},
               "source_proposal_sha256": PINS[PROPOSAL / "field-proposal.json"],
               "source_handoff_sha256": PINS[PROPOSAL / "allocation-handoff.json"],
               "allocation_floors": floor, "counts": {"records": 108, "entities": 1082,
                                                      "sources": 235, "events": 10368, "variants": 864},
               "source_map": source_map, "aggregate_complete": False,
               "admitted": False, "runtime_eligible": False}
    output = {"package.json": package, "identity-registry.json": registry,
              "expected-profile.json": profile, "candidate-allocation.json": candidate,
              "identity-baseline.json": identity_baseline, "allocation-baseline.json": allocation_baseline,
              "lineage-baseline.json": lineage_baseline, "local-summary.json": summary}
    check_global(output, (base_pkg, l7_pkg, l8_pkg), (base_reg, l7_reg, l8_reg))
    return output


def check_global(output: dict, packages: tuple[dict, ...], registries: tuple[dict, ...]) -> None:
    pkg, reg, prof, allocation = (output[n] for n in
                                  ("package.json", "identity-registry.json", "expected-profile.json", "candidate-allocation.json"))
    new = reg["entities"][1:]
    ids = [e["id"] for e in new]
    old_ids = {e["id"] for ancestor in registries for e in ancestor["entities"]}
    need(len(ids) == 1081 and len(reg["entities"]) == 1082 and len(ids) == len(set(ids)) and
         not old_ids.intersection(ids), "GLOBAL_ENTITY_COLLISION")
    base = registries[0]
    for kind, plural in (("module", "modules"), ("item", "items"), ("variant", "variants")):
        used = [l8tool.number(e["id"]) for ancestor in registries for e in ancestor["entities"] if e["kind"] == kind]
        mine = [l8tool.number(e["id"]) for e in new if e["kind"] == kind]
        need(min(mine) > max(used), f"GLOBAL_ID_ORDER {kind}")
        for entry in base["workbook_catalog"]["entries"]:
            bounds = entry.get("reserved_playable_identity_ranges", {}).get(plural)
            if bounds:
                lo, hi = map(l8tool.number, bounds)
                need(all(not lo <= x <= hi for x in mine), f"RESERVED_ID_COLLISION {kind}")
    events = [e["event_id"] for r in pkg["records"] for e in r["events"]]
    old_events = {e["event_id"] for ancestor in packages for r in ancestor["records"] for e in r["events"]}
    need(len(events) == 10368 and len(events) == len(set(events)) and
         not old_events.intersection(events), "GLOBAL_EVENT_COLLISION")
    refs = set(pkg["sources"])
    need(len(refs) == 235 and all(not refs.intersection(p["sources"]) for p in packages) and
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
    report = l8tool.read(root, OUT / "native-report.json")
    need(report["exit_code"] == 2 and report["valid_reference"] is True and
         report["curriculum_playback_authorized"] is False, "NATIVE_AUTHORITY")
    for name, key in (("package.json", "package_sha256"),
                      ("identity-registry.json", "registry_sha256"),
                      ("expected-profile.json", "profile_sha256")):
        need(report[key] == l8tool.sha(l8tool.encode(output[name])) ==
             l8tool.sha((root / OUT / name).read_bytes()), f"NATIVE_INPUT_BINDING {name}")
    need(report["coverage"] == {"events": 10368, "expected_entities": 1082,
                                "expected_passages": 235, "expected_records": 108,
                                "observed_entities": 1082, "observed_passages": 235,
                                "observed_records": 108, "variant_event_memberships": 20736,
                                "variants": 864}, "NATIVE_COVERAGE")
    issues = Counter((x["severity"], x["code"]) for x in report["issues"])
    need(issues == {("unresolved", "MODEL_unresolved_time"): 10368,
                    ("unresolved", "VARIANT_BINDING_UNRESOLVED"): 864,
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
            (ROOT / OUT / name).write_bytes(l8tool.encode(output[name]))
    else:
        for name in FILES:
            need((ROOT / OUT / name).read_bytes() == l8tool.encode(output[name]), f"OUTPUT_DRIFT {name}")
        if args.command == "verify-native":
            verify_native(ROOT, output)
    print(json.dumps({"status": "level010_local_nonadmitted_reference",
                      "counts": output["local-summary.json"]["counts"],
                      "allocation_floors": output["local-summary.json"]["allocation_floors"]}, sort_keys=True))


if __name__ == "__main__":
    main()
