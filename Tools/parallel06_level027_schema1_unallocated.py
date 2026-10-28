#!/usr/bin/env python3
"""Project sealed Level27 ordered thirds into detached unallocated schema1 fields."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from curriculum_level027_whole_candidate import build_candidate


ROOT = Path(__file__).resolve().parents[1]
OUT_REL = Path("Build/parallel-06/level027-schema1-unallocated-r01")
INPUTS = {
    "Build/parallel-04/2.3.1.1.1-level027-whole-r03/candidate-01.json": "ae6ee46eaff95344dae27791bb8ab5a7ec3a2ba0a29a83da93c391601daf1ad2",
    "Tools/curriculum_level027_whole_candidate.py": "3856f7ef3d567824c9c6ec58e87cf7ce4605b6bb0e8e58bffc9de89c47df74d6",
    "Content/controls/curriculum-v1/package.json": "766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255",
    "Content/controls/curriculum-v1/identity-registry.json": "5d265859e1e8a5a530a0e53d88b019a1c920f3bba6cccb4ef0fef2f7640007e5",
    "Results/primary/20260912T100538Z-2.1.1.2.1-r02-evidence/schema-freeze.json": "0659fa962a5c933a2bcf3045772b6fe5b05b4deefb3511f5dcb68af51088de95",
}
KEYS = ("A", "Bb", "B", "C", "C#", "D", "Eb", "E", "F", "F#", "G", "G#", "A")
DEGREES = ("1", "2", "b3", "4", "5", "b6", "b7", "8", "9", "b10", "11", "12", "b13", "b14", "15")
OPEN = {"E": (1, 40), "A": (2, 45), "D": (3, 50), "G": (4, 55),
        "B": (5, 59), "e": (6, 64)}
PC = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3,
      "E": 4, "Fb": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7,
      "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11, "Cb": 11}
DIFFERENCE_IDS = (
    "rung_13_route_label_presentation", "tempo_downshift_trigger_specificity",
    "pause_duration_specificity", "descending_string_path_summary",
    "practice_phase_grouping",
)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def encoded(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False,
                       separators=(",", ":")) + "\n").encode()


def read_inputs(root: Path) -> tuple[dict, dict, dict]:
    raw = {}
    for rel, expected in INPUTS.items():
        path = root / rel
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"missing or symlink input: {rel}")
        data = path.read_bytes()
        if digest(data) != expected:
            raise ValueError(f"input drift: {rel}")
        raw[rel] = data
    candidate = json.loads(raw[next(iter(INPUTS))])
    if candidate != build_candidate():
        raise ValueError("sealed candidate differs from original TXT/PDF replay")
    package = json.loads(raw[list(INPUTS)[2]])
    registry = json.loads(raw[list(INPUTS)[3]])
    freeze = json.loads(raw[list(INPUTS)[4]])
    if freeze.get("decision") != "Technical schema1 FROZEN" or freeze.get("schema_version") != "1.0.0-curriculum-candidate":
        raise ValueError("schema freeze drift")
    return candidate, package, registry


def identity_boundary(package: dict, registry: dict) -> dict:
    wid = "fg:workbook:000027"
    if any(r.get("legacy_level") == 27 or r.get("workbook_id") == wid
           for r in package["records"]):
        raise ValueError("unexpected canonical Level27 record")
    if any(e.get("id") == wid for e in registry["entities"]):
        raise ValueError("unexpected Level27 registry entity")
    entries = [e for e in package["workbook_catalog"]["entries"]
               if e.get("workbook_id") == wid]
    if len(entries) != 1:
        raise ValueError("Level27 catalog identity drift")
    entry = entries[0]
    if (entry.get("conversion_status") != "not_converted"
            or entry.get("whole_workbook_complete") is not False
            or entry.get("admitted") is not False
            or entry.get("runtime_eligible") is not False
            or entry.get("representative_item_id") is not None):
        raise ValueError("Level27 source-only catalog drift")
    return entry


def event(contact: dict, record: dict, direction: str, pair_number: int) -> dict:
    if contact["onset_q"] is not None or contact["duration_q"] is not None:
        raise ValueError("source contact timing drift")
    string, fret, degree = contact["string"], contact["fret"], contact["degree_label"]
    if string not in OPEN or type(fret) is not int or fret < 0 or degree not in DEGREES:
        raise ValueError("source contact degree/TAB drift")
    spelling = record["scale_tones_two_octaves"][DEGREES.index(degree)]
    string_number, base = OPEN[string]
    midi = base + fret
    if spelling not in PC or midi != contact["midi_pitch"] or midi % 12 != PC[spelling]:
        raise ValueError("source contact note/TAB pitch mismatch")
    if contact["finger_digit"] not in (1, 2, 3, 4):
        raise ValueError("source contact finger drift")
    return {
        "source_contact": contact, "source_spelling": spelling,
        "source_rung": record["rung"], "source_direction": direction,
        "source_pair_number": pair_number, "source_refs": record["source_refs"],
        "performed_result": None,
        "schema1_fields": {
            "event_id": None, "kind": "note", "attack": None,
            "spelling": spelling, "midi": midi, "string": string_number,
            "fret": fret, "finger": contact["finger_digit"],
            "degree_contexts": {}, "onset_q": None, "duration_q": None,
            "tie_from": None,
        },
    }


def project(candidate: dict, package: dict, registry: dict) -> tuple[dict, dict]:
    catalog = identity_boundary(package, registry)
    if (candidate.get("schema") != "fathom-level027-detached-candidate-v1"
            or candidate.get("schema_version") != 1
            or candidate.get("wbs_id") != "2.3.1.1.1"
            or candidate.get("level") != 27
            or candidate.get("candidate_status") != "detached_pending_review"
            or len(candidate.get("records", [])) != 13):
        raise ValueError("whole Level27 source scope drift")
    scope = candidate["scope"]
    for key in ("admitted", "canonical_ids_assigned", "imported", "parent_acceptance",
                "performed_or_recorded_practice", "runtime_admitted", "runtime_eligible",
                "whole_workbook_complete"):
        if scope.get(key) is not False:
            raise ValueError(f"source scope admission drift: {key}")
    coverage = candidate["coverage"]
    if (coverage["rung_count"] != 13 or coverage["pair_count"] != 338
            or coverage["note_contact_count"] != 676
            or coverage["minor_third_pair_count"] != 208
            or coverage["major_third_pair_count"] != 130):
        raise ValueError("whole source coverage drift")
    differences = candidate["source_discrepancies"]
    if ([x["id"] for x in differences] != list(DIFFERENCE_IDS)
            or not all(x["status"].endswith("pending_review") for x in differences)):
        raise ValueError("five source differences drift")
    label = differences[0]
    if (label["txt_ref"]["line"] != 99
            or label["txt_ref"]["text"] != "A natural minor - octave"
            or label["pdf_ref"]["page"] != 2
            or label["pdf_ref"]["text"] != "A natural minor (octave)"):
        raise ValueError("rung-13 TXT/PDF label difference drift")
    route = candidate["sequence_facts"]["full_round_trip_instruction"]
    if (route["cells_per_round"] != 25 or route["notes_per_cell"] != 52
            or route["instructed_note_count"] != 1300
            or route["performed"] is not False
            or route["route"] != "rungs 01-13, then rungs 12-01; do not replay rung 13"):
        raise ValueError("25-cell route/count drift")
    if (candidate["source_map_state"]["review"] != "Pending"
            or candidate["source_map_state"]["conversion_status"] != "not_converted"
            or candidate["source_map_state"]["representative_item_id"] is not None
            or any(candidate["source_map_state"][k] for k in
                   ("stable_ids_assigned", "runtime_eligible", "imported", "admitted"))):
        raise ValueError("source map admission drift")
    records = []
    pair_total = contact_total = 0
    quality_total = {"m3": 0, "M3": 0}
    for ordinal, source in enumerate(candidate["records"], 1):
        if (source["rung"] != ordinal or source["root_pitch"] != KEYS[ordinal - 1]
                or source["root_fret"] != ordinal + 4
                or source["source_cell_note_count"] != 52
                or len(source["scale_tones_two_octaves"]) != 15
                or len(source["directions"]) != 2):
            raise ValueError("rung source scope drift")
        for key in ("admitted", "imported", "runtime_eligible", "runtime_admitted"):
            if source.get(key) is not False:
                raise ValueError("rung admission drift")
        for key in ("canonical_item_id", "canonical_variant_id", "fixed_bpm", "note_per_click", "onset_q", "duration_q"):
            if source.get(key) is not None:
                raise ValueError("rung identity/timing drift")
        if [d["direction"] for d in source["directions"]] != ["ascending", "descending"]:
            raise ValueError("rung direction order drift")
        events = []
        pairs = []
        for direction in source["directions"]:
            if len(direction["pairs"]) != 13:
                raise ValueError("rung pair count drift")
            for pair_no, pair in enumerate(direction["pairs"], 1):
                if (pair["pair_number"] != pair_no or len(pair["contacts"]) != 2
                        or pair["interval_quality"] not in quality_total):
                    raise ValueError("ordered pair scope drift")
                start = len(events) + 1
                for slot_no, contact in enumerate(pair["contacts"], 1):
                    if (contact["slot_order"] != slot_no
                            or contact["degree_label"] != pair["degree_pair"][slot_no - 1]
                            or contact["finger_digit"] != pair["finger_pair"][slot_no - 1]
                            or contact["string"] != pair["string_path"][slot_no - 1]):
                        raise ValueError("ordered pair/contact parity drift")
                    events.append(event(contact, source, direction["direction"], pair_no))
                if abs(events[-1]["schema1_fields"]["midi"] - events[-2]["schema1_fields"]["midi"]) != (3 if pair["interval_quality"] == "m3" else 4):
                    raise ValueError("third quality/pitch drift")
                pairs.append({"source_direction": direction["direction"],
                              "source_pair": pair,
                              "source_event_ordinals": [start, start + 1]})
                quality_total[pair["interval_quality"]] += 1
        if len(events) != 52 or [e["source_contact"]["degree_label"] for e in events[25:27]] != ["15", "15"]:
            raise ValueError("rung event/high-root-turn drift")
        pair_total += len(pairs)
        contact_total += len(events)
        records.append({
            "source_component": f"rung-{ordinal:02d}", "identity_state": "unallocated",
            "source_rung": {k: v for k, v in source.items() if k != "directions"},
            "source_directions": [{k: v for k, v in d.items() if k != "pairs"} for d in source["directions"]],
            "source_pairs": pairs,
            "schema1_fields": {
                "id": None, "workbook_id": None, "module_id": None,
                "legacy_level": 27, "title": source["key_name"], "kind": "note_sequence",
                "content_revision": None, "lineage": None, "runtime_eligible": False,
                "source_refs": None, "events": events,
                "variants": [{"id": None, "source_rung": ordinal,
                              "source_event_ordinals": list(range(1, 53)),
                              "event_ids": None, "runtime_eligible": False}],
                "resource_requirements": [],
                "timing": {"status": "unresolved", "unit": "quarter", "fixed_bpm": None},
                "ambiguities": ["canonical identities and lineage unallocated",
                                "quarter-note onset/duration and fixed BPM unresolved",
                                "five TXT/PDF source differences remain Pending"],
            },
        })
    if pair_total != 338 or contact_total != 676 or quality_total != {"m3": 208, "M3": 130}:
        raise ValueError("whole pair/contact/quality parity drift")
    sequence = list(range(1, 14)) + list(range(12, 0, -1))
    proposal = {
        "proposal_version": "level027-unallocated-schema1-fields.1", "wbs_id": "2.3.1.1.1",
        "classification": "Build-only, nonimportable schema1 field proposal",
        "legacy_level": 27, "canonical_ids_allocated": False,
        "schema1_importable": False, "whole_workbook_complete": False,
        "runtime_eligible": False, "admitted": False,
        "counts": {"provisional_rung_records": 13, "ordered_third_pairs": 338,
                   "rung_note_contacts": 676, "minor_third_pairs": 208,
                   "major_third_pairs": 130, "route_cells": 25,
                   "route_source_described_contacts": 1300,
                   "route_new_unique_note_events": 0},
        "source": candidate["source"], "source_catalog_level": catalog,
        "source_map_state": candidate["source_map_state"],
        "source_discrepancies": differences,
        "instruction_sections": candidate["instruction_sections"],
        "pdf_projection_checks": candidate["pdf_projection_checks"],
        "sequence_facts": candidate["sequence_facts"],
        "route_reference": candidate["route_reference"],
        "route_application": [{"route_cell": i, "source_rung": rung,
                               "source_event_ordinals": list(range(1, 53))}
                              for i, rung in enumerate(sequence, 1)],
        "records": records,
    }
    handoff = {
        "handoff_version": "level027-allocation-handoff.1", "wbs_id": "2.3.1.1.1",
        "catalog_workbook_id": catalog["workbook_id"],
        "existing_level027_records": 0, "existing_level027_workbook_entities": 0,
        "rung_records": 13, "ordered_third_pairs": 338,
        "rung_note_contacts": 676, "route_cells": 25,
        "route_source_described_contacts": 1300,
        "source_differences_pending": list(DIFFERENCE_IDS),
        "canonical_ids_allocated": False, "admitted": False,
        "required_decisions": [
            "Disposition all five TXT/PDF source differences without silently canonicalizing the rung-13 label.",
            "Allocate stable workbook/module/item/event/variant identities and revision lineage.",
            "Decide 25-cell route occurrence identity without creating extra authored rung notes.",
            "Resolve onset/duration, fixed BPM and Practice semantics before native import.",
            "Complete musical correctness and Curriculum review of all 13 rungs and route.",
        ],
    }
    return proposal, handoff


def products(root: Path) -> dict[str, object]:
    candidate, package, registry = read_inputs(root)
    proposal, handoff = project(candidate, package, registry)
    manifest = {"manifest_version": "level027-input-pins.1", "inputs": [
        {"path": rel, "bytes": (root / rel).stat().st_size, "sha256": sha}
        for rel, sha in INPUTS.items()]}
    summary = {"summary_version": "level027-schema1-unallocated-summary.1",
               "proposal_sha256": digest(encoded(proposal)),
               "handoff_sha256": digest(encoded(handoff)),
               "rung_records": 13, "ordered_third_pairs": 338,
               "rung_note_contacts": 676, "source_differences_pending": 5,
               "route_cells": 25, "route_source_described_contacts": 1300,
               "native_run": False, "runtime_eligible": False, "admitted": False}
    return {"field-proposal.json": proposal, "allocation-handoff.json": handoff,
            "input-manifest.json": manifest, "summary.json": summary}


def run(mode: str, root: Path) -> None:
    git_root = Path(subprocess.run(["git", "rev-parse", "--show-toplevel"],
                                   cwd=root, capture_output=True, text=True,
                                   check=True).stdout.strip()).resolve(strict=True)
    if root != git_root:
        raise ValueError("root must equal Git top level")
    built = products(root)
    out = root
    for part in OUT_REL.parts:
        out /= part
        if out.is_symlink():
            raise ValueError("output symlink path")
    if mode == "build":
        if out.exists():
            raise ValueError("output already exists")
        out.mkdir(parents=True)
        for name, value in built.items():
            with (out / name).open("xb") as f:
                f.write(encoded(value))
    else:
        contents = {p.name for p in out.iterdir()}
        if contents not in (set(built), set(built) | {"focused-tests.log"}):
            raise ValueError("output file set drift")
        if "focused-tests.log" in contents and (out / "focused-tests.log").is_symlink():
            raise ValueError("output test log symlink")
        for name, value in built.items():
            path = out / name
            if path.is_symlink() or path.read_bytes() != encoded(value):
                raise ValueError(f"output drift: {name}")
    print("LEVEL27 " + mode.upper() + " PASS rungs=13 pairs=338 contacts=676 route=1300 differences=5 admitted=false")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("mode", choices=("build", "verify"))
    ap.add_argument("--root", type=Path, default=ROOT)
    args = ap.parse_args()
    run(args.mode, args.root.resolve(strict=True))


if __name__ == "__main__":
    main()
