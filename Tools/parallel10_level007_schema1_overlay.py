#!/usr/bin/env python3
"""Build-only Level 7 schema1 reference overlay on the reviewed 659 predecessor."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
CURRENT = Path("Content/controls/curriculum-v1")
P12 = Path("Build/parallel-12/level009-schema1-overlay-r02b")
SOURCE_PROPOSAL = Path("Build/parallel-10/level007-source-proposal-adapter-r01/proposal-01.json")
TXT = Path("Notes/music/guitar project/TXT version/108_Finger_Permutations_Level_7_Three_String_Skip_Relay.txt")
PDF = Path("Notes/music/guitar project/PDF version/108_Finger_Permutations_Level_7_Three_String_Skip_Relay.pdf")
ALLOCATION_659 = P12 / "candidate-allocation.json"
OUT = Path("Build/parallel-10/level007-schema1-overlay-r01")
PINS = {
    CURRENT / "package.json": "766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255",
    CURRENT / "identity-registry.json": "5d265859e1e8a5a530a0e53d88b019a1c920f3bba6cccb4ef0fef2f7640007e5",
    CURRENT / "expected-profile.json": "21009e3596f325a4b9f73c9532b71cd361703e0f682b40088ff58bff7ba57c8a",
    CURRENT / "generation.json": "fc6cec9f9d67eb82c97c5f4c3fb95d285178fb7fce7bd147d9ae0296d21b4c1c",
    CURRENT / "workbook-coverage.json": "d8e492101c97c60add858799c77da4db3f0c528d348c9cf66105c2dc37df4eeb",
    P12 / "package.json": "766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255",
    P12 / "identity-registry.json": "5d265859e1e8a5a530a0e53d88b019a1c920f3bba6cccb4ef0fef2f7640007e5",
    P12 / "expected-profile.json": "21009e3596f325a4b9f73c9532b71cd361703e0f682b40088ff58bff7ba57c8a",
    ALLOCATION_659: "f5bda91a233e4747edb480641cf55c966b1f842b850917faa377035b217ee42d",
    SOURCE_PROPOSAL: "8838eaed97e30fc384d2ab8e51bc2def3f7f9f9df912d2543d64674d5dc0a5c9",
    TXT: "467d1401237e34633efc4c517fa98d8190f0b47346a7b34be9d2548924883b61",
    PDF: "5c8607cff40801acb13f5e08dd2988b2ff943593eb084de2801f05f507a6c4ea",
}
NAMES = ("proposal.json", "transaction.json", "candidate-allocation.json", "package.json",
         "identity-registry.json", "expected-profile.json", "generation.json", "summary.json")
ROUTES = (("ascending", "E", "D", "B"), ("ascending", "A", "G", "e"),
          ("descending", "e", "G", "A"), ("descending", "B", "D", "E"))
OPEN_MIDI = {"E": (1, 40), "A": (2, 45), "D": (3, 50), "G": (4, 55), "B": (5, 59), "e": (6, 64)}


class OverlayError(ValueError):
    """A pinned authority, source, identity or output check failed."""


def require(ok: bool, code: str) -> None:
    if not ok:
        raise OverlayError(code)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def encoded(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def pin_inputs(root: Path = ROOT) -> None:
    for rel, expected in PINS.items():
        actual = sha((root / rel).read_bytes())
        require(actual == expected, f"PIN_DRIFT {rel}: {actual} != {expected}")


def load(root: Path, rel: Path) -> dict:
    return json.loads((root / rel).read_text())


def suffix(identity: str) -> int:
    return int(identity.rsplit(":", 1)[1])


def allocation_floor(registry: dict, kind: str) -> int:
    plural = {"item": "items", "module": "modules", "variant": "variants"}[kind]
    allocated = max(suffix(x["id"]) for x in registry["entities"] if x["kind"] == kind)
    ends = [allocated]
    for entry in registry["workbook_catalog"]["entries"]:
        bounds = entry.get("reserved_playable_identity_ranges", {}).get(plural)
        if bounds is None:
            continue
        require(len(bounds) == 2 and all(x.startswith(f"fg:{kind}:") for x in bounds), "RESERVATION_SHAPE")
        first, last = map(suffix, bounds)
        require(first <= last, "RESERVATION_SHAPE")
        ends.append(last)
    return max(ends) + 1


def check_new_ids(registry: dict, new_entities: list[dict]) -> None:
    existing = {e["id"] for e in registry["entities"]}
    ids = [e["id"] for e in new_entities]
    require(len(ids) == len(set(ids)) and not existing.intersection(ids), "DUPLICATE_ENTITY")
    for kind in ("module", "item", "variant"):
        floor = allocation_floor(registry, kind)
        numbers = [suffix(e["id"]) for e in new_entities if e["kind"] == kind]
        require(numbers and min(numbers) >= floor, f"RESERVED_ID_COLLISION {kind}")
        plural = {"module": "modules", "item": "items", "variant": "variants"}[kind]
        for entry in registry["workbook_catalog"]["entries"]:
            bounds = entry.get("reserved_playable_identity_ranges", {}).get(plural)
            if bounds:
                first, last = map(suffix, bounds)
                require(all(not first <= n <= last for n in numbers), f"RESERVED_ID_COLLISION {kind}")


def workbook_numbers(package: dict, registry: dict) -> list[int]:
    from_records = {r["legacy_level"] for r in package["records"]}
    from_registry = {suffix(e["id"]) for e in registry["entities"] if e["kind"] == "workbook"}
    require(from_records == from_registry, "WORKBOOK_ENTITY_MISMATCH")
    return sorted(from_records)


def check_predecessor(package: dict, registry: dict, profile: dict, generation: dict, allocation: dict) -> None:
    require(len(package["records"]) == 659 and len(registry["entities"]) == 6336 and
            len(package["sources"]) == 775 and len(profile["event_sources"]) == 26845,
            "PREDECESSOR_SCOPE")
    require(len(allocation["records"]) == 659 and
            set(allocation["records"]) == {r["id"] for r in package["records"]}, "PREDECESSOR_ALLOCATION")
    require(profile["reference_package"] == {k: v for k, v in package.items() if k != "workbook_catalog"} and
            profile["reference_registry"] == {k: v for k, v in registry.items() if k != "workbook_catalog"},
            "PREDECESSOR_PROFILE")
    alloc_refs = [a for a in profile["authority_artifacts"] if a["role"] == "candidate_identity_allocation"]
    require(len(alloc_refs) == 1 and alloc_refs[0]["path"] == str(ALLOCATION_659) and
            alloc_refs[0]["sha256"] == PINS[ALLOCATION_659], "PREDECESSOR_AUTHORITY")
    require(package["workbook_catalog"] == registry["workbook_catalog"] == profile["workbook_catalog"] ==
            generation["workbook_catalog"], "CATALOG_DRIFT")
    require(generation["records"] == 659 and generation["current_entities"] == 6336 and
            generation["variants"] == 5001 and generation["events"] == 26845 and
            generation["passages"] == 775 and generation["workbooks"] == workbook_numbers(package, registry),
            "PREDECESSOR_GENERATION")
    require(all(r["legacy_level"] != 7 for r in package["records"]) and
            not any(e["id"] == "fg:workbook:000007" for e in registry["entities"]), "LEVEL7_ALREADY_ALLOCATED")
    level7 = [e for e in registry["workbook_catalog"]["entries"] if e["workbook_id"] == "fg:workbook:000007"]
    require(len(level7) == 1 and level7[0]["conversion_status"] == "not_converted" and
            level7[0]["admitted"] is False and level7[0]["runtime_eligible"] is False, "LEVEL7_CATALOG")


def source_passage(lines: list[str], first: int, last: int) -> dict:
    require(1 <= first <= last <= len(lines), "SOURCE_SPAN")
    value = "\n".join(lines[first - 1:last])
    return {"path": str(TXT), "sha256": PINS[TXT], "format": "txt", "first_line": first,
            "last_line": last, "text": value, "text_sha256": sha(value.encode())}


def source_passages(proposal: dict, lines: list[str], reader: PdfReader) -> dict[str, dict]:
    sources = {"L7-TXT1-3": source_passage(lines, 3, 3),
               "L7-TXT1-5-9": source_passage(lines, 5, 9),
               "L7-TXT1-16-24": source_passage(lines, 16, 24)}
    for page in range(2, 11):
        text = reader.pages[page - 1].extract_text()
        sources[f"L7-PDF1-p{page}"] = {"path": str(PDF), "sha256": PINS[PDF], "format": "pdf",
                                      "page": page, "text": text, "text_sha256": sha(text.encode())}
    for case in proposal["records"]:
        ref = case["source_refs"]["txt"]
        match = re.fullmatch(r"L7-TXT1-(\d+)-(\d+)", ref)
        require(match is not None and ref not in sources, "SOURCE_REF")
        first, last = map(int, match.groups())
        passage = source_passage(lines, first, last)
        require(passage["text_sha256"] == case["source_span_sha256"], "SOURCE_SPAN_DRIFT")
        page = int(case["source_refs"]["pdf"].rsplit("p", 1)[1])
        require(re.search(rf"\b{case['exercise_number']}\b\s+{case['source_code']}\b",
                          sources[f"L7-PDF1-p{page}"]["text"]) is not None, "PDF_CARD_DRIFT")
        sources[ref] = passage
    require(len(sources) == 120, "SOURCE_PASSAGE_COUNT")
    return sources


def level7_records(source: dict, registry: dict) -> tuple[list[dict], list[dict], dict, list[dict]]:
    require(source["schema"] == "fathom-source-to-schema1-proposal.1" and
            source["classification"] == "source_mapped_unallocated_nonadmitted_proposal" and
            source["coverage"] == {"record_count": 108, "route_count": 432, "contact_count": 1728,
                                   "source_coverage_verified": True, "whole_workbook_complete": False},
            "SOURCE_PROPOSAL_SCOPE")
    require(source["authority"] == {"canonical_ids_allocated": False, "runtime_eligible": False,
                                    "imported": False, "admitted": False, "native_schema1_package": False},
            "SOURCE_PROPOSAL_AUTHORITY")
    require(len(source["records"]) == 108 and len(source["set_guidance"]) == 9, "SOURCE_PROPOSAL_COUNT")
    module_floor = allocation_floor(registry, "module")
    item_floor = allocation_floor(registry, "item")
    variant_floor = allocation_floor(registry, "variant")
    entities = [{"id": "fg:workbook:000007", "kind": "workbook",
                 "label": "Legacy Level7 three-string skip relay", "parent": "fg:course:000001"}]
    records, allocation, source_map = [], {}, []
    seen = set()
    for index, case in enumerate(source["records"]):
        number = index + 1
        key = f"L7-set{index // 12 + 1:02d}-ex{number:03d}"
        require(case["source_local_key"] not in seen, "DUPLICATE_SOURCE_LOCAL_KEY")
        seen.add(case["source_local_key"])
        require(case["source_local_key"] == key and case["exercise_number"] == f"{number:03d}", "SOURCE_ORDER")
        mapped = case["record_proposal"]
        require(mapped["id"] is None and mapped["module_id"] is None and mapped["workbook_id"] is None and
                mapped["content_revision"] is None and mapped["lineage"] is None and mapped["variants"] == [] and
                mapped["runtime_eligible"] is False, "SOURCE_NOT_UNALLOCATED")
        require(mapped["timing"] == {"status": "unresolved", "unit": None,
                                     "fixed_bpm": None, "note_per_click": None}, "INVENTED_TIMING")
        require(len(mapped["events"]) == 16 and len(mapped["route_proposals"]) == 4,
                "SOURCE_CASE_COUNTS")
        module = f"fg:module:{module_floor + index:06d}"
        item = f"fg:item:{item_floor + index:06d}"
        entities.extend(({"id": module, "kind": "module", "label": f"Level7 Exercise {number:03d} {case['source_code']}",
                          "parent": "fg:workbook:000007"},
                         {"id": item, "kind": "item", "label": mapped["title"], "parent": module}))
        refs = [case["source_refs"]["txt"], case["source_refs"]["pdf"], "L7-TXT1-3",
                "L7-TXT1-5-9", "L7-TXT1-16-24"]
        events, occurrences = [], {}
        source_events = mapped["events"]
        for route_index, route in enumerate(mapped["route_proposals"]):
            direction, *played = ROUTES[route_index]
            require(route["direction"] == direction and route["played_strings"] == played and
                    route["route_ordinal"] == route_index % 2 + 1 and
                    route["silent_intervening_strings"] == 2 and
                    len(route["source_occurrence_keys"]) == 4, "ROUTE_SHAPE")
            for ordinal, source_event in enumerate(source_events[route_index * 4:(route_index + 1) * 4], 1):
                require(source_event["source_occurrence_key"] == route["source_occurrence_keys"][ordinal - 1],
                        "OCCURRENCE_ORDER")
                require(source_event["event_id"] is None and source_event["onset_q"] is None and
                        source_event["duration_q"] is None and source_event["attack"] is None, "INVENTED_TIMING")
                string_name = source_event["source_string"]
                string_number, open_pitch = OPEN_MIDI[string_name]
                require(source_event["string"] == string_number and source_event["midi"] == open_pitch + source_event["fret"] and
                        1 <= source_event["finger"] <= 4 and source_event["fret"] == 4 + source_event["finger"],
                        "SOURCE_PITCH_FINGER")
                event_id = f"{item}:event:{len(events) + 1:04d}"
                events.append({"event_id": event_id, "kind": "note", "string": string_number,
                               "fret": source_event["fret"], "midi": source_event["midi"],
                               "finger": source_event["finger"], "spelling": None,
                               "degree_contexts": {}, "onset_q": None, "duration_q": None,
                               "attack": "picked", "tie_from": None})
                occurrences[source_event["source_occurrence_key"]] = event_id
        require(len(occurrences) == 16 and len(events) == 16, "EVENT_COUNT")
        variants, variant_map = [], {}
        for pick_index, pick in enumerate(("D", "U")):
            variant_id = f"fg:variant:{variant_floor + index * 2 + pick_index:06d}"
            label = f"ascending-descending-{pick}-start"
            entities.append({"id": variant_id, "kind": "variant", "label": label, "parent": item})
            variant_map[label] = variant_id
            variants.append({"id": variant_id, "label": label, "event_ids": [e["event_id"] for e in events],
                             "source_refs": refs, "route": "ascending_then_descending",
                             "pick_start": pick, "pick_start_origin": "learner_configuration",
                             "accent_policy": "source_unspecified", "role": "notation_practice",
                             "grouping": {"kind": "unresolved", "notes_per_beat": None,
                                          "beat_unit_q": None, "marking_factor": [1, 1],
                                          "source_label": "Straight 16ths first, then triplet/quintuplet groupings; no fixed event grid"},
                             "tail_pause": None,
                             "unresolved": ["No authored fixed BPM, quarter-note beat unit or event duration."]})
        timing_gap = "Relative 10–15 BPM below clean Level6 mode and later 2/-4–6 BPM practice rules do not define fixed record BPM or event duration."
        record = {"id": item, "workbook_id": "fg:workbook:000007", "module_id": module,
                  "legacy_level": 7, "title": mapped["title"], "kind": "notation",
                  "content_revision": 1, "lineage": {"kind": "new"},
                  "status": "converted_candidate", "runtime_eligible": False,
                  "source_refs": refs, "authored_text_refs": refs,
                  "normalization": [{"kind": "representation_metadata",
                                     "basis": "P04 whole-Level7 original TXT/PDF mapping and P10 unallocated source proposal",
                                     "text": "The four printed routes play 1+2+1 across two silent-string gaps. Source directs ASCEND then DESCEND and repeats with the opposite D/U starting pick. No beat grid, default pick start or automatic mastery is inferred."}],
                  "context": {"local_code": case["source_code"], "source_local_key": key,
                              "route": "ascending E-D-B then A-G-e; descending e-G-A then B-D-E",
                              "position": "fifth", "pick_start": "D or U chosen by learner",
                              "tuning_open_midi": [40, 45, 50, 55, 59, 64]},
                  "events": events, "variants": variants,
                  "timing": {"status": "unresolved", "unit": "quarter",
                             "basis": "Straight 16ths/triplet/quintuplet and relative tempo guidance do not provide a fixed quarter-note grid",
                             "other_source_requirements": [timing_gap,
                                                           "First pass separates cells, lightly accents notes 2 and 4 and audits silent strings; second pass connects and equalizes.",
                                                           "After three clean loops add 2 BPM next session; after two noisy gaps/errors/tension reduce 4–6 BPM.",
                                                           "Advance after full set clean with both pick starts on two separate days; no automatic mastery inference."]},
                  "rubric": None, "resource_requirements": [],
                  "ambiguities": [timing_gap],
                  "control_scope": {"local_case": f"Exercise {number:03d} {case['source_code']} full printed directions",
                                    "extent": "complete_selected_case", "whole_workbook_complete": False,
                                    "source_event_count": 16, "basis_refs": refs, "unresolved": [timing_gap]}}
        records.append(record)
        allocation[item] = {"legacy_level": 7, "occurrences": occurrences, "variants": variant_map}
        source_map.append({"item_id": item, "source_local_key": key, "exercise_number": number,
                           "code": case["source_code"], "txt": case["source_refs"]["txt"],
                           "pdf": case["source_refs"]["pdf"],
                           "source_record_sha256": case["source_record_sha256"]})
    check_new_ids(registry, entities)
    require(len(records) == 108 and len(entities) == 433 and len(allocation) == 108, "NEW_SCOPE")
    return records, entities, allocation, source_map


def verify_candidate(package: dict, registry: dict, profile: dict, generation: dict,
                     predecessor: dict, pre_registry: dict, pre_profile: dict,
                     allocation: dict, proposal: dict, transaction: dict) -> None:
    require(package["records"][:659] == predecessor["records"] and
            registry["entities"][:6336] == pre_registry["entities"], "PREDECESSOR_VALUE_DRIFT")
    require(all(package["sources"].get(k) == v for k, v in predecessor["sources"].items()) and
            all(profile["event_sources"].get(k) == v for k, v in pre_profile["event_sources"].items()),
            "PREDECESSOR_SOURCE_DRIFT")
    require(package["records"][659:] == proposal["records"] and
            registry["entities"][6336:] == transaction["new_entities"], "PROPOSAL_DRIFT")
    require(len(package["records"]) == 767 and len(registry["entities"]) == 6769 and
            len(package["sources"]) == 895 and len(profile["event_sources"]) == 28573,
            "CANDIDATE_COUNTS")
    require(len(allocation["records"]) == 767 and
            set(allocation["records"]) == {r["id"] for r in package["records"]}, "ALLOCATION_COVERAGE")
    require(all(r["runtime_eligible"] is False and r["lineage"] == {"kind": "new"} and
                all(e["onset_q"] is None and e["duration_q"] is None for e in r["events"])
                for r in package["records"][659:]), "INVENTED_TIMING_OR_ADMISSION")
    require(all(profile["reference_package"].get(k) == v for k, v in package.items() if k != "workbook_catalog") and
            all(profile["reference_registry"].get(k) == v for k, v in registry.items() if k != "workbook_catalog"),
            "PROFILE_BINDING")
    require(package["workbook_catalog"] == registry["workbook_catalog"] == profile["workbook_catalog"] ==
            generation["workbook_catalog"], "CATALOG_DRIFT")
    check_new_ids(pre_registry, transaction["new_entities"])
    require(len({e["id"] for e in registry["entities"]}) == len(registry["entities"]), "DUPLICATE_ENTITY")
    require(generation["records"] == 767 and generation["current_entities"] == 6769 and
            generation["variants"] == 5217 and generation["events"] == 28573 and
            generation["passages"] == 895 and generation["workbooks"] == workbook_numbers(package, registry),
            "GENERATION_COUNT")


def derive(root: Path = ROOT) -> dict[str, dict]:
    pin_inputs(root)
    predecessor = load(root, CURRENT / "package.json")
    pre_registry = load(root, CURRENT / "identity-registry.json")
    pre_profile = load(root, CURRENT / "expected-profile.json")
    pre_generation = load(root, CURRENT / "generation.json")
    allocation_659 = load(root, ALLOCATION_659)
    source = load(root, SOURCE_PROPOSAL)
    check_predecessor(predecessor, pre_registry, pre_profile, pre_generation, allocation_659)
    records, entities, new_allocation, source_map = level7_records(source, pre_registry)
    lines = (root / TXT).read_text().splitlines()
    reader = PdfReader(str(root / PDF))
    require(len(reader.pages) == 10, "PDF_PAGES")
    added_sources = source_passages(source, lines, reader)
    proposal = {"version": "parallel10-level007-allocated-record-proposal.1",
                "classification": "build_only_nonadmitted_schema1_records",
                "predecessor_sha256": {name: PINS[CURRENT / name] for name in
                                       ("package.json", "identity-registry.json", "expected-profile.json", "generation.json")},
                "source_proposal_sha256": PINS[SOURCE_PROPOSAL], "records": records}
    transaction = {"version": "parallel10-level007-allocation-transaction.1",
                   "mode": "append_only_new_lineage", "rebase_if_baseline_changes": True,
                   "predecessor_record_count": 659, "predecessor_entity_count": 6336,
                   "floors": {kind: allocation_floor(pre_registry, kind) for kind in ("module", "item", "variant")},
                   "new_entities": entities, "records": new_allocation, "source_map": source_map}
    allocation = {"version": "control-allocation.1",
                  "authority": "P10 Build-only Level7 append-only proposal on P02 659 reference; no import or admission",
                  "records": {**allocation_659["records"], **new_allocation}}
    package = json.loads(json.dumps(predecessor))
    package["content_version"] = "curriculum-v1-level007-767-build-only-candidate.1"
    package["records"].extend(records)
    require(not set(added_sources).intersection(package["sources"]), "DUPLICATE_SOURCE_REF")
    package["sources"].update(added_sources)
    registry = json.loads(json.dumps(pre_registry))
    registry["entities"].extend(entities)
    profile = json.loads(json.dumps(pre_profile))
    profile["authority_artifacts"] = [a for a in profile["authority_artifacts"]
                                      if a["role"] != "candidate_identity_allocation"]
    profile["authority_artifacts"].append({"path": str(OUT / "candidate-allocation.json"),
                                           "role": "candidate_identity_allocation",
                                           "sha256": sha(encoded(allocation))})
    profile["reference_package"] = {k: v for k, v in package.items() if k != "workbook_catalog"}
    profile["reference_registry"] = {k: v for k, v in registry.items() if k != "workbook_catalog"}
    profile["event_sources"].update({event["event_id"]: record["source_refs"][0]
                                     for record in records for event in record["events"]})
    roles = [a["role"] for a in profile["authority_artifacts"]]
    require(roles.count("candidate_identity_allocation") == 1 and
            [a for a in profile["authority_artifacts"] if a["role"] != "candidate_identity_allocation"] ==
            [a for a in pre_profile["authority_artifacts"] if a["role"] != "candidate_identity_allocation"],
            "AUTHORITY_ROLE_DRIFT")
    generation = json.loads(json.dumps(pre_generation))
    generation.update({"records": len(package["records"]), "current_entities": len(registry["entities"]),
                       "variants": sum(len(r["variants"]) for r in package["records"]),
                       "events": sum(len(r["events"]) for r in package["records"]),
                       "passages": len(package["sources"]), "workbooks": workbook_numbers(package, registry)})
    generation["classification"] = "Build-only Level7 767-record nonadmitted reference candidate; no human/runtime admission"
    generation["identities"] = {"package.json": sha(encoded(package)),
                                "identity-registry.json": sha(encoded(registry)),
                                "expected-profile.json": sha(encoded(profile))}
    require(set(generation) == set(pre_generation) and
            generation["reconciliation"] == pre_generation["reconciliation"] and
            generation["bundle_status"] == pre_generation["bundle_status"], "GENERATION_HISTORY")
    verify_candidate(package, registry, profile, generation, predecessor, pre_registry, pre_profile,
                     allocation, proposal, transaction)
    summary = {"status": "build_only_nonadmitted_native_reference_candidate",
               "predecessor_records": 659, "new_records": 108, "total_records": 767,
               "predecessor_entities": 6336, "new_entities": 433, "total_entities": 6769,
               "new_routes": 432, "new_contacts": 1728, "new_variants": 216,
               "sources": len(package["sources"]), "events": len(profile["event_sources"]),
               "allocation_floors": transaction["floors"],
               "predecessor_sha256": proposal["predecessor_sha256"],
               "native_admission_claim": False, "rebase_if_baseline_changes": True}
    return {"proposal.json": proposal, "transaction.json": transaction,
            "candidate-allocation.json": allocation, "package.json": package,
            "identity-registry.json": registry, "expected-profile.json": profile,
            "generation.json": generation, "summary.json": summary}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "verify"))
    args = parser.parse_args()
    artifacts = derive()
    dest = ROOT / OUT
    if args.command == "build":
        dest.mkdir(parents=True, exist_ok=True)
        require(all(not (dest / name).exists() and not (dest / name).is_symlink() for name in NAMES),
                "OUTPUT_EXISTS_OR_SYMLINK")
        for name in NAMES:
            (dest / name).write_bytes(encoded(artifacts[name]))
    else:
        for name in NAMES:
            require((dest / name).read_bytes() == encoded(artifacts[name]), f"OUTPUT_DRIFT {name}")
    print(json.dumps(artifacts["summary.json"], sort_keys=True))


if __name__ == "__main__":
    main()
