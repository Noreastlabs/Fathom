#!/usr/bin/env python3
"""Allocate and verify the bounded, nonadmitted Level 8 schema1 local shard."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import parallel12_level008_schema1_unallocated as source

ROOT = Path(__file__).resolve().parents[1]
OUT = Path("Build/parallel-12/level008-local-shard-r01")
BASE = Path("Content/controls/curriculum-v1")
L7 = Path("Build/parallel-10/level007-shard-reference-r02")
L8 = Path("Build/parallel-12/level008-schema1-unallocated-r01")
PINS = {
    BASE / "package.json": "766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255",
    BASE / "identity-registry.json": "5d265859e1e8a5a530a0e53d88b019a1c920f3bba6cccb4ef0fef2f7640007e5",
    BASE / "expected-profile.json": "21009e3596f325a4b9f73c9532b71cd361703e0f682b40088ff58bff7ba57c8a",
    BASE / "generation.json": "fc6cec9f9d67eb82c97c5f4c3fb95d285178fb7fce7bd147d9ae0296d21b4c1c",
    BASE / "workbook-coverage.json": "d8e492101c97c60add858799c77da4db3f0c528d348c9cf66105c2dc37df4eeb",
    L7 / "package.json": "a9cfaa7b0c86fd8d4e089b0ba86913f6e18ca3a33f1f8cddca1897ea017f4732",
    L7 / "identity-registry.json": "486856ea8df8ddc58fb33e222c161322a422baeb202632fb7709039921e02984",
    L7 / "expected-profile.json": "9feb48ef6ae4d20cc251b56972b11ba151b8837851471fce41b26a23beb6d259",
    L7 / "candidate-allocation.json": "a94f10adff77bfcc571cf40b0f625af86e805d2e548d420d39fc97004f9ec029",
    L7 / "global-manifest.json": "c0d83b1ae546772cb2138ada6a6c0cd95de50f23beb6fc673246bcd1c8cc078a",
    L7 / "native-report.json": "7b3de6019221e365f700f76866857ececa4ba3b028ff8207191023f055bc88f8",
    L8 / "field-proposal.json": "9434ca6e21dd35a6b84e4ea2b4f699dd505d4f93901458b3651d9e097992da18",
    L8 / "allocation-handoff.json": "7461d176a7c1af46cf5c705c6cb69bd4f8395e154fba08edeb7390b57ea942b8",
    source.TXT: source.PINS[source.TXT][1],
    source.PDF: source.PINS[source.PDF][1],
}
FILES = ("package.json", "identity-registry.json", "expected-profile.json",
         "candidate-allocation.json", "identity-baseline.json",
         "allocation-baseline.json", "lineage-baseline.json", "local-summary.json")


class ShardError(ValueError):
    pass


def need(ok: bool, code: str) -> None:
    if not ok:
        raise ShardError(code)


def encode(obj: object) -> bytes:
    return (json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def read(root: Path, path: Path) -> dict:
    return json.loads((root / path).read_text())


def pin(root: Path) -> None:
    need(root.resolve() == ROOT.resolve(), "ROOT_DRIFT")
    for path, expected in PINS.items():
        need(sha((root / path).read_bytes()) == expected, f"INPUT_PIN_DRIFT {path}")


def number(identity: str) -> int:
    return int(identity.rsplit(":", 1)[1])


def floors(base_registry: dict, l7_registry: dict) -> dict[str, int]:
    result = {}
    for kind, plural in (("module", "modules"), ("item", "items"), ("variant", "variants")):
        used = [number(e["id"]) for reg in (base_registry, l7_registry)
                for e in reg["entities"] if e["kind"] == kind]
        reserved = []
        for entry in base_registry["workbook_catalog"]["entries"]:
            bounds = entry.get("reserved_playable_identity_ranges", {}).get(plural)
            if bounds:
                need(len(bounds) == 2 and all(x.startswith(f"fg:{kind}:") for x in bounds), "RESERVATION_SHAPE")
                reserved.append(number(bounds[1]))
        result[kind] = max(used + reserved) + 1
    need(result == {"module": 804, "item": 804, "variant": 5650}, "ALLOCATION_FLOOR_DRIFT")
    return result


def txt_passage(lines: list[str], first: int, last: int) -> dict:
    need(1 <= first <= last <= len(lines), "TXT_SPAN")
    text = "\n".join(lines[first - 1:last])
    return {"path": str(source.TXT), "sha256": PINS[source.TXT], "format": "txt",
            "first_line": first, "last_line": last, "text": text, "text_sha256": sha(text.encode())}


def make_sources(root: Path, proposal: dict, handoff: dict) -> dict:
    from pypdf import PdfReader
    lines = (root / source.TXT).read_text().splitlines()
    pdf = PdfReader(str(root / source.PDF))
    need(len(pdf.pages) == 10, "PDF_COUNT")
    sources = {"L8-TXT1-1-26": txt_passage(lines, 1, 26)}
    for page in range(2, 11):
        text = pdf.pages[page - 1].extract_text()
        sources[f"L8-PDF1-p{page}"] = {"path": str(source.PDF), "sha256": PINS[source.PDF],
                                        "format": "pdf", "page": page, "text": text,
                                        "text_sha256": sha(text.encode())}
    for row, entry in zip(proposal["records"], handoff["source_map"], strict=True):
        need(row["source_local_key"] == entry["source_local_key"] and row["code"] == entry["code"], "SOURCE_MAP")
        match = re.fullmatch(r"L8-TXT1-(\d+)-(\d+)", entry["txt"])
        need(match is not None and entry["txt"] not in sources, "SOURCE_REF")
        first, last = map(int, match.groups())
        passage = txt_passage(lines, first, last)
        need(passage["text_sha256"] == entry["txt_passage_sha256"], "SOURCE_SPAN_DRIFT")
        need(f"Exercise {row['exercise_number']:03d}: {row['code']}" in passage["text"], "TXT_CARD")
        need(re.search(rf"\b{row['exercise_number']:03d}\b\s+{row['code']}\b",
                       sources[entry["pdf"]]["text"]) is not None, "PDF_CARD")
        sources[entry["txt"]] = passage
    need(len(sources) == 118, "SOURCE_COUNT")
    return sources


def derive(root: Path = ROOT, proposal_override: dict | None = None) -> dict[str, dict]:
    pin(root)
    base_pkg, base_reg, base_prof = (read(root, BASE / name) for name in
                                     ("package.json", "identity-registry.json", "expected-profile.json"))
    l7_pkg, l7_reg, l7_prof, l7_alloc = (read(root, L7 / name) for name in
                                           ("package.json", "identity-registry.json", "expected-profile.json", "candidate-allocation.json"))
    l7_manifest = read(root, L7 / "global-manifest.json")
    need(l7_manifest["validated_workbooks"] == [7] and l7_manifest["aggregate_complete"] is False and
         l7_manifest["admitted"] is False and len(l7_pkg["records"]) == 108 and
         len(l7_alloc["records"]) == 108 and l7_prof["reference_package"] == l7_pkg and
         l7_prof["reference_registry"] == l7_reg, "LEVEL7_REFERENCE")
    need(len(base_pkg["records"]) == 659 and len(base_reg["entities"]) == 6336 and
         len(base_reg["workbook_catalog"]["entries"]) == 105 and
         "fg:workbook:000008" not in {e["id"] for e in base_reg["entities"] + l7_reg["entities"]},
         "FOUNDATION_SCOPE")
    floor = floors(base_reg, l7_reg)
    expected_proposal, expected_handoff = source.build(root)
    proposal = proposal_override if proposal_override is not None else read(root, L8 / "field-proposal.json")
    handoff = read(root, L8 / "allocation-handoff.json")
    need(proposal == expected_proposal and handoff == expected_handoff, "SOURCE_PROPOSAL_DRIFT")
    source.verify(proposal, handoff)
    sources = make_sources(root, proposal, handoff)
    records, entities, allocation, event_sources, source_map = [], [], {}, {}, []
    entities.append({"id": "fg:workbook:000008", "kind": "workbook",
                     "label": "Legacy Level8 two-position ladder", "parent": "fg:course:000001"})
    for index, row in enumerate(proposal["records"]):
        item = f"fg:item:{floor['item'] + index:06d}"
        module = f"fg:module:{floor['module'] + index:06d}"
        fields = json.loads(json.dumps(row["schema1_fields"]))
        need(fields["id"] is fields["module_id"] is fields["workbook_id"] is fields["lineage"] is None,
             "SOURCE_ALLOCATED")
        need(fields["source_refs"] == [handoff["source_map"][index]["txt"],
                                       handoff["source_map"][index]["pdf"], "L8-TXT1-1-26"], "SOURCE_REFS")
        fields.update(id=item, module_id=module, workbook_id="fg:workbook:000008", lineage={"kind": "new"})
        entities.extend(({"id": module, "kind": "module", "label": f"Level8 Exercise {index + 1:03d} {row['code']}",
                          "parent": "fg:workbook:000008"},
                         {"id": item, "kind": "item", "label": fields["title"], "parent": module}))
        occurrences = {}
        for ordinal, event in enumerate(fields["events"], 1):
            need(event["event_id"] is None and event["onset_q"] is event["duration_q"] is None,
                 "SOURCE_TIMING_OR_ID")
            event_id = f"{item}:event:{ordinal:04d}"
            event["event_id"] = event_id
            occurrence = f"{row['source_local_key']}:note:{ordinal:03d}"
            occurrences[occurrence] = event_id
            event_sources[event_id] = fields["source_refs"][0]
        variant_ids = {}
        for variant_index, (variant, member) in enumerate(zip(fields["variants"], row["variant_memberships"], strict=True)):
            need(variant["id"] is variant["event_ids"] is None and variant["label"] == member["label"],
                 "VARIANT_SOURCE")
            vid = f"fg:variant:{floor['variant'] + index * 4 + variant_index:06d}"
            variant["id"] = vid
            variant["event_ids"] = [fields["events"][ordinal - 1]["event_id"]
                                    for ordinal in member["event_local_ordinals"]]
            variant_ids[variant["label"]] = vid
            entities.append({"id": vid, "kind": "variant", "label": variant["label"], "parent": item})
        need(len(fields["events"]) == 96 and len(occurrences) == 96 and
             len(fields["variants"]) == 4 and all(len(v["event_ids"]) == 48 for v in fields["variants"]),
             "CASE_COVERAGE")
        records.append(fields)
        allocation[item] = {"legacy_level": 8, "occurrences": occurrences, "variants": variant_ids}
        source_map.append({"item_id": item, **handoff["source_map"][index]})
    package = {k: v for k, v in l7_pkg.items() if k not in ("records", "sources")}
    package.update(content_version="curriculum-v1-level008-local-shard-build-only.1",
                   sources=sources, records=records)
    registry = {"identity_version": base_reg["identity_version"], "rules": base_reg["rules"],
                "entities": [base_reg["entities"][0], *entities]}
    identity_baseline = {"identity_version": registry["identity_version"], "rules": registry["rules"],
                         "entities": [registry["entities"][0]]}
    allocation_baseline = {"version": "control-allocation.1", "authority":
                           "Local Level8 course-only preallocation; global 659 plus Level7 refs pinned separately", "records": {}}
    lineage_baseline = {"version": "lineage-baseline.1", "records": {}}
    candidate = {"version": "control-allocation.1", "authority":
                 "P12 Level8 local shard only; global aggregate validation required; no admission", "records": allocation}
    profile = {k: v for k, v in l7_prof.items() if k not in ("reference_package", "reference_registry", "event_sources", "authority_artifacts")}
    profile.update(reference_package=package, reference_registry=registry, event_sources=event_sources)
    profile["authority_artifacts"] = [a for a in l7_prof["authority_artifacts"] if a["role"] in
                                      ("source_manifest", "source_acceptance", "current_schema_freeze")]
    for role, name, obj in (("identity_baseline", "identity-baseline.json", identity_baseline),
                            ("allocation_baseline", "allocation-baseline.json", allocation_baseline),
                            ("lineage_baseline", "lineage-baseline.json", lineage_baseline),
                            ("candidate_identity_allocation", "candidate-allocation.json", candidate)):
        profile["authority_artifacts"].append({"path": str(OUT / name), "role": role,
                                               "sha256": sha(encode(obj))})
    summary = {"schema": "parallel12-level008-local-shard-summary.1", "status": "local_reference_only",
               "foundation_sha256": {p.name: PINS[p] for p in PINS if p.parent == BASE},
               "level007_sha256": {p.name: PINS[p] for p in PINS if p.parent == L7},
               "source_proposal_sha256": PINS[L8 / "field-proposal.json"],
               "source_handoff_sha256": PINS[L8 / "allocation-handoff.json"],
               "allocation_floors": floor, "counts": {"records": 108, "entities": 650,
                                                      "sources": 118, "events": 10368, "variants": 432},
               "source_map": source_map, "aggregate_complete": False,
               "admitted": False, "runtime_eligible": False}
    output = {"package.json": package, "identity-registry.json": registry,
              "expected-profile.json": profile, "candidate-allocation.json": candidate,
              "identity-baseline.json": identity_baseline, "allocation-baseline.json": allocation_baseline,
              "lineage-baseline.json": lineage_baseline, "local-summary.json": summary}
    check_global(output, base_pkg, base_reg, base_prof, l7_pkg, l7_reg, l7_prof)
    return output


def check_global(output: dict, base_pkg: dict, base_reg: dict, base_prof: dict,
                 l7_pkg: dict, l7_reg: dict, l7_prof: dict) -> None:
    pkg, reg, prof, alloc = (output[n] for n in
                             ("package.json", "identity-registry.json", "expected-profile.json", "candidate-allocation.json"))
    new_entities = reg["entities"][1:]
    old_ids = {e["id"] for r in (base_reg, l7_reg) for e in r["entities"]}
    ids = [e["id"] for e in new_entities]
    need(len(ids) == len(set(ids)) and not old_ids.intersection(ids), "GLOBAL_ENTITY_COLLISION")
    need(len(new_entities) == 649 and len(reg["entities"]) == 650 and len(pkg["records"]) == 108,
         "SHARD_COUNT")
    for kind in ("module", "item", "variant"):
        used = [number(e["id"]) for r in (base_reg, l7_reg) for e in r["entities"] if e["kind"] == kind]
        mine = [number(e["id"]) for e in new_entities if e["kind"] == kind]
        need(min(mine) > max(used), f"GLOBAL_ID_ORDER {kind}")
        for entry in base_reg["workbook_catalog"]["entries"]:
            bounds = entry.get("reserved_playable_identity_ranges", {}).get({"module":"modules","item":"items","variant":"variants"}[kind])
            if bounds:
                lo, hi = map(number, bounds)
                need(all(not lo <= value <= hi for value in mine), f"RESERVED_ID_COLLISION {kind}")
    events = [e["event_id"] for r in pkg["records"] for e in r["events"]]
    old_events = {e["event_id"] for p in (base_pkg, l7_pkg) for r in p["records"] for e in r["events"]}
    need(len(events) == 10368 and len(events) == len(set(events)) and not old_events.intersection(events),
         "GLOBAL_EVENT_COLLISION")
    refs = set(pkg["sources"])
    need(len(refs) == 118 and not refs.intersection(base_pkg["sources"]) and
         not refs.intersection(l7_pkg["sources"]) and set(prof["event_sources"]) == set(events) and
         all(ref in refs for ref in prof["event_sources"].values()), "GLOBAL_SOURCE_COLLISION")
    need(set(alloc["records"]) == {r["id"] for r in pkg["records"]} and
         all(r["lineage"] == {"kind": "new"} and r["runtime_eligible"] is False and
             r["content_revision"] == 1 and r["timing"]["status"] == "unresolved" and
             all(e["onset_q"] is e["duration_q"] is None for e in r["events"])
             for r in pkg["records"]), "LINEAGE_OR_TIMING")
    need(prof["reference_package"] == pkg and prof["reference_registry"] == reg and
         all("workbook_catalog" not in obj for obj in (pkg, reg, prof)) and
         output["local-summary.json"]["aggregate_complete"] is False and
         output["local-summary.json"]["admitted"] is False, "LOCAL_AUTHORITY")
    need(len(base_prof["event_sources"]) == 26845 and len(l7_prof["event_sources"]) == 1728,
         "PREDECESSOR_EVENT_SCOPE")


def verify_native(root: Path, output: dict) -> dict:
    report = read(root, OUT / "native-report.json")
    need(report["exit_code"] == 2 and report["valid_reference"] is True and
         report["curriculum_playback_authorized"] is False, "NATIVE_AUTHORITY")
    for name, key in (("package.json", "package_sha256"),
                      ("identity-registry.json", "registry_sha256"),
                      ("expected-profile.json", "profile_sha256")):
        need(report[key] == sha(encode(output[name])) == sha((root / OUT / name).read_bytes()),
             f"NATIVE_INPUT_BINDING {name}")
    need(report["coverage"] == {"events": 10368, "expected_entities": 650,
                                "expected_passages": 118, "expected_records": 108,
                                "observed_entities": 650, "observed_passages": 118,
                                "observed_records": 108, "variant_event_memberships": 20736,
                                "variants": 432}, "NATIVE_COVERAGE")
    from collections import Counter
    issues = Counter((x["severity"], x["code"]) for x in report["issues"])
    need(issues == {("unresolved", "MODEL_unresolved_time"): 10368,
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
    print(json.dumps({"status": "level008_local_nonadmitted_reference", "counts": output["local-summary.json"]["counts"],
                      "allocation_floors": output["local-summary.json"]["allocation_floors"]}, sort_keys=True))


if __name__ == "__main__":
    main()
