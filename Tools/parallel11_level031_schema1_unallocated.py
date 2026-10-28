#!/usr/bin/env python3
"""Replay sealed Level31 source and sketch unallocated schema1 fields."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from curriculum_level031_whole_candidate import (
    DEGREES, FINGERS, FINGER_NAMES, FRET_OFFSETS, KEYS, OPEN_MIDI,
    STRINGS, TONES, build, columns, tone_pc,
)


ROOT = Path(__file__).resolve().parents[1]
OUT_REL = Path("Build/parallel-11/2.3.1.1.1-level031-schema1-unallocated-r01")
INPUTS = {
    "Tools/curriculum_level031_whole_candidate.py": "20ccdc0057fc7b60dbde413aa8e64aeec71369ec14b70bdbe9a708776547a838",
    "Results/parallel-11/curriculum/20260923T151500Z-2.3-level031-whole-r01-results.md": "d5246c1a9abdf42c66dca15613ffa17921fc5671938cc5f25bed765f05b34267",
    "Build/parallel-11/2.3.1.1.1-level031-whole-r01/candidate-final-a.json": "ba08b9c884c3b0ce71ece5ed1474cdd409c03e5ba0502604d889f2706b2a4809",
    "Build/parallel-11/2.3.1.1.1-level031-whole-r01/candidate-final-b.json": "ba08b9c884c3b0ce71ece5ed1474cdd409c03e5ba0502604d889f2706b2a4809",
    "Content/controls/curriculum-v1/package.json": "766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255",
    "Content/controls/curriculum-v1/identity-registry.json": "5d265859e1e8a5a530a0e53d88b019a1c920f3bba6cccb4ef0fef2f7640007e5",
    "Content/controls/curriculum-v1/generation.json": "fc6cec9f9d67eb82c97c5f4c3fb95d285178fb7fce7bd147d9ae0296d21b4c1c",
    "Notes/music/guitar project/TXT version/Scale_Exercises_Section_IV_Level_31_Major_Pentatonic_Two_Octave_Six_String_Neck_Ladder.txt": "491359a3d7227f4887eb2486cdaf5827ef85a7487ea57c7b21d089ad6be3bfa7",
    "Notes/music/guitar project/PDF version/Scale_Exercises_Section_IV_Level_31_Major_Pentatonic_Two_Octave_Six_String_Neck_Ladder.pdf": "1f1cbc0f1d8a996f5239769abce00f94c4267e5504e6edbb72112210a12f137e",
    "Results/parallel-01/exercises/inventory/20260922T180500Z-2.3-curriculum-v1-source-inventory-evidence/curriculum-source-map.json": "bad5581a04f43ba8baf14db430449e1ccff5cf88f0f7e42198328073b27053d6",
}
STRING_NUMBER = {"E": 1, "A": 2, "D": 3, "G": 4, "B": 5, "e": 6}
UNRESOLVED = [
    "P02 has not allocated canonical workbook, rung/item, event or variant IDs and lineage.",
    "The printed D/U starts and alternating strokes are alternatives; no performed choice is observed.",
    "Eighth-note, tempo, one-beat-pause and relocation instructions do not set onset_q, duration_q, note_per_click or fixed_bpm.",
    "PDF page-1 worked example and TXT/PDF cards place the octave separator differently; Curriculum review remains pending.",
    "No performance, mastery, native import, runtime eligibility or admission is evidenced.",
]


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def encoded(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def pinned(root: Path, rel: str, sha: str) -> bytes:
    path = root / rel
    if path.is_symlink():
        raise ValueError(f"input symlink: {rel}")
    raw = path.read_bytes()
    if digest(raw) != sha:
        raise ValueError(f"input drift: {rel}")
    return raw


def read_inputs(root: Path) -> tuple[dict, dict, dict, dict]:
    raw = {rel: pinned(root, rel, sha) for rel, sha in INPUTS.items()}
    a = raw["Build/parallel-11/2.3.1.1.1-level031-whole-r01/candidate-final-a.json"]
    b = raw["Build/parallel-11/2.3.1.1.1-level031-whole-r01/candidate-final-b.json"]
    if a != b:
        raise ValueError("sealed Level31 twins differ")
    candidate = json.loads(a)
    if candidate != json.loads(json.dumps(build(root))):
        raise ValueError("sealed Level31 source differs from original TXT/PDF replay")
    source_map = json.loads(raw["Results/parallel-01/exercises/inventory/20260922T180500Z-2.3-curriculum-v1-source-inventory-evidence/curriculum-source-map.json"])
    row = next((r for r in source_map["rows"] if r["level"] == 31), None)
    if (row is None or row.get("section") != "IV" or row.get("wbs_owner") != "2.3.1.1.1"
            or row.get("conversion_status") != "not_converted" or row.get("stable_ids_assigned") is not False
            or row.get("admitted") is not False or row.get("representative_item_id") is not None
            or row.get("txt_sha256") != candidate["source_authority"]["txt"]["sha256"]
            or row.get("pdf_sha256") != candidate["source_authority"]["pdf"]["sha256"]):
        raise ValueError("frozen source map drift")
    foundation = json.loads(raw["Content/controls/curriculum-v1/package.json"])
    registry = json.loads(raw["Content/controls/curriculum-v1/identity-registry.json"])
    generation = json.loads(raw["Content/controls/curriculum-v1/generation.json"])
    if len(foundation["records"]) != 659 or generation["records"] != 659:
        raise ValueError("current659 foundation drift")
    return candidate, row, foundation, registry


def identity_boundary(foundation: dict, registry: dict) -> dict:
    workbook = "fg:workbook:000031"
    if any(r.get("legacy_level") == 31 or r.get("workbook_id") == workbook for r in foundation["records"]):
        raise ValueError("unexpected canonical Level31 record")
    if any(e.get("id") == workbook for e in registry["entities"]):
        raise ValueError("unexpected Level31 registry entity")
    entry = next((e for e in foundation["workbook_catalog"]["entries"] if e.get("workbook_id") == workbook), None)
    if (not entry or entry.get("representative_item_id") is not None
            or entry.get("whole_workbook_complete") is not False
            or entry.get("admitted") is not False or entry.get("imported") is not False
            or entry.get("runtime_eligible") is not False
            or entry.get("conversion_status") != "not_converted"
            or entry.get("stable_identity_status") != "evidenced_source_only"):
        raise ValueError("Level31 source-only catalog drift")
    return entry


def validate_candidate(c: dict) -> None:
    if (c.get("schema") != "fathom-level031-whole-detached-source-candidate.1"
            or c.get("wbs_id") != "2.3.1.1.1" or c.get("level") != 31
            or c.get("classification") != "source_bound_non_admitted_candidate"
            or c.get("canonical_schema_validated") is not False
            or any(c.get(k) is not False for k in ("imported", "admitted", "runtime_eligible", "whole_workbook_complete"))):
        raise ValueError("source identity/admission drift")
    if c.get("counts") != {"rungs": 13, "notes_per_rung": 22, "notes_in_source_cards": 286,
                            "round_trip_cells": 25, "round_trip_note_occurrences": 550}:
        raise ValueError("13/22/286/25/550 source count drift")
    if (c.get("ascending_route") != list(range(1, 14))
            or c.get("descending_route_after_high_a") != list(range(12, 0, -1))
            or c.get("round_trip_rung_order") != list(range(1, 14)) + list(range(12, 0, -1))
            or c.get("reverse_after_rung") != 13
            or c.get("frame_shift_after_cell_frets") != {"ascending_except_turn": 1, "descending": -1}):
        raise ValueError("round-trip route/shift drift")
    if c.get("pick_start_options") != ["D", "U"] or c.get("tempo_and_picking_are_source_guidance_only") is not True:
        raise ValueError("pick/timing guidance boundary drift")
    discrepancy = c.get("source_discrepancies")
    if (not isinstance(discrepancy, list) or len(discrepancy) != 1
            or discrepancy[0].get("kind") != "octave_separator_position"
            or discrepancy[0].get("status") != "pending_curriculum_review"
            or discrepancy[0].get("resolution") is not None
            or discrepancy[0].get("sounding_tone_order_same") is not True
            or [discrepancy[0][k]["tokens_before_separator"] for k in ("txt_card", "pdf_card", "pdf_worked_example")] != [6, 6, 5]):
        raise ValueError("octave separator discrepancy drift")
    if len(c.get("records", [])) != 13:
        raise ValueError("13 rung records drift")
    for rung, r in enumerate(c["records"], 1):
        root = rung + 4
        if (r.get("rung") != rung or r.get("source_local_key") != f"L31-rung{rung:02d}"
                or r.get("key") != KEYS[rung - 1] or r.get("root_string") != "E"
                or r.get("root_fret") != root or r.get("frame_frets") != [root - 1, root + 2]
                or r.get("degrees_per_octave") != [1, 2, 3, 5, 6]
                or r.get("scale_tones_two_octaves") != TONES[rung - 1].replace("|", "").split()
                or (r.get("note_count"), r.get("up_note_count"), r.get("down_note_count")) != (22, 11, 11)
                or r.get("shift_after_complete_cell_only") is not True or r.get("within_cell_shift") is not False
                or any(r.get(k) is not None for k in ("canonical_item_id", "canonical_variant_id", "onset_q", "duration_q", "note_per_click", "fixed_bpm"))
                or any(r.get(k) is not False for k in ("runtime_eligible", "imported", "admitted"))):
            raise ValueError(f"rung geometry/identity/timing drift: {rung}")
        if len(r.get("notes", [])) != 22:
            raise ValueError(f"22 note occurrences drift: {rung}")
        deg = columns(r["printed_deg_row"], "Deg")
        finger = columns(r["printed_fng_row"], "Fng")
        tab = {s: columns(row, prefix) for s, prefix, row in zip(("e", "B", "G", "D", "A", "E"),
               ("e  ", "B  ", "G  ", "D  ", "A  ", "E  "), r["printed_tab_rows_high_to_low"], strict=True)}
        for index, n in enumerate(r["notes"]):
            expected_fret = root + FRET_OFFSETS[index]
            found = [(s, int(token.rstrip("-"))) for s, cells in tab.items()
                     if (token := cells[index]) != "---"]
            if (n.get("ordinal_in_cell") != index + 1 or n.get("printed_column") != 3 * index
                    or n.get("direction") != ("up" if index < 11 else "down")
                    or n.get("degree") != DEGREES[index] or deg[index] != f"{DEGREES[index]}--"
                    or n.get("finger_digit") != FINGERS[index] or n.get("finger_name") != FINGER_NAMES[FINGERS[index]]
                    or finger[index] != f"{FINGERS[index]}--"
                    or n.get("string") != STRINGS[index] or n.get("fret") != expected_fret
                    or found != [(STRINGS[index], expected_fret)]
                    or n.get("tone") != r["scale_tones_two_octaves"][index if index < 11 else 21 - index]
                    or (OPEN_MIDI[STRINGS[index]] + expected_fret) % 12 != tone_pc(n["tone"])
                    or n.get("pick_for_down_start") != ("D" if index % 2 == 0 else "U")
                    or n.get("pick_for_up_start") != ("U" if index % 2 == 0 else "D")
                    or n.get("onset_q") is not None or n.get("duration_q") is not None):
                raise ValueError(f"printed note/TAB/finger/pitch drift: {rung}:{index + 1}")
        if (r["notes"][10]["tone"], r["notes"][10]["string"], r["notes"][10]["fret"]) != (
                r["notes"][11]["tone"], r["notes"][11]["string"], r["notes"][11]["fret"]):
            raise ValueError(f"repeated high-root turn drift: {rung}")


def event_fields(n: dict) -> dict:
    return {"event_id": None, "kind": "note", "spelling": n["tone"],
            "string": STRING_NUMBER[n["string"]], "fret": n["fret"],
            "midi": OPEN_MIDI[n["string"]] + n["fret"], "finger": n["finger_digit"],
            "source_degree": n["degree"], "degree_contexts": {}, "tie_from": None,
            "attack": None, "onset_q": None, "duration_q": None,
            "pick": None, "accent": None, "performed": None}


def project(c: dict, row: dict, foundation: dict, registry: dict) -> tuple[dict, dict]:
    validate_candidate(c)
    entry = identity_boundary(foundation, registry)
    records = []
    for r in c["records"]:
        events = [{"source_note": n, "schema1_fields": event_fields(n)} for n in r["notes"]]
        variants = [{"id": None, "source_pick_start_option": option,
                     "source_alternate_strokes": [n["pick_for_down_start" if option == "D" else "pick_for_up_start"] for n in r["notes"]],
                     "actual_pick_start": None, "performed": None, "runtime_eligible": False}
                    for option in c["pick_start_options"]]
        records.append({"source_rung": r["rung"], "source_record": r,
                        "identity_state": "unallocated", "schema1_fields": {
                            "id": None, "workbook_id": None, "module_id": None,
                            "legacy_level": 31, "title": f"Level 31 rung {r['rung']:02d}: {r['key']} major pentatonic",
                            "kind": "scale", "content_revision": None, "lineage": None,
                            "status": "unallocated_source_projection", "runtime_eligible": False,
                            "admitted": False, "source_refs": r["source_refs"],
                            "events": events, "variants": variants,
                            "timing": {"status": "unresolved", "unit": "quarter", "onset_q": None,
                                       "duration_q": None, "fixed_bpm": None, "note_per_click": None},
                            "mastery_observed": None}})
    proposal = {
        "proposal_version": "level031-unallocated-schema1-fields.1", "wbs_id": "2.3.1.1.1",
        "classification": "Build-only, nonimportable schema1 field proposal", "legacy_level": 31,
        "canonical_ids_allocated": False, "schema1_importable": False,
        "whole_workbook_complete": False, "runtime_eligible": False, "admitted": False,
        "mastery_observed": None, "performed_route_observed": None,
        "counts": c["counts"], "source_authority": c["source_authority"],
        "source_guidance": c["source_guidance"], "source_discrepancies": c["source_discrepancies"],
        "route_source_only": {"ascending_rungs": c["ascending_route"],
                              "descending_rungs_after_high_a": c["descending_route_after_high_a"],
                              "round_trip_rung_order": c["round_trip_rung_order"],
                              "reverse_after_rung": c["reverse_after_rung"],
                              "frame_shift_after_cell_frets": c["frame_shift_after_cell_frets"],
                              "source_note_occurrences_if_played": 550,
                              "additional_canonical_events": 0, "performed": None},
        "pick_start_options_source_only": c["pick_start_options"],
        "actual_pick_start": None, "unresolved": UNRESOLVED, "records": records,
    }
    handoff = {"handoff_version": "level031-allocation-handoff.1", "wbs_id": "2.3.1.1.1",
               "catalog_workbook_id_read_only": entry["workbook_id"],
               "source_map_status_read_only": row["conversion_status"],
               "existing_level031_records": 0, "existing_level031_workbook_entities": 0,
               "provisional_rungs": 13, "printed_card_notes": 286,
               "round_trip_source_note_occurrences": 550,
               "canonical_ids_allocated": False, "admitted": False,
               "required_decisions": c["required_decisions"] + [
                   "Choose whether and how the source D/U alternatives and 25-cell route become canonical variants.",
                   "Confirm click grid, performed pick starts and observed mastery before runtime/admission."]}
    return proposal, handoff


def products(root: Path) -> dict[str, object]:
    c, row, foundation, registry = read_inputs(root)
    proposal, handoff = project(c, row, foundation, registry)
    manifest = {"manifest_version": "level031-schema1-input-pins.1", "inputs": [
        {"path": rel, "bytes": (root / rel).stat().st_size, "sha256": sha} for rel, sha in INPUTS.items()]}
    summary = {"summary_version": "level031-schema1-unallocated-summary.1",
               "proposal_sha256": digest(encoded(proposal)), "handoff_sha256": digest(encoded(handoff)),
               "rungs": 13, "printed_card_notes": 286, "route_cells": 25,
               "route_source_note_occurrences": 550, "native_run": False,
               "runtime_eligible": False, "admitted": False}
    return {"field-proposal.json": proposal, "allocation-handoff.json": handoff,
            "input-manifest.json": manifest, "summary.json": summary}


def output_dir(root: Path) -> Path:
    part = root
    for component in OUT_REL.parts:
        part /= component
        if part.is_symlink():
            raise ValueError("output symlink path")
    return part


def run(mode: str, root: Path) -> None:
    built = products(root)
    out = output_dir(root)
    if mode == "build":
        out.mkdir(parents=True, exist_ok=True)
        for name, value in built.items():
            (out / name).write_bytes(encoded(value))
    else:
        for name, value in built.items():
            path = out / name
            if path.is_symlink() or path.read_bytes() != encoded(value):
                raise ValueError(f"output drift: {name}")
    print(f"LEVEL31 {mode.upper()} PASS rungs=13 notes=286 route=25/550 admitted=false")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("build", "verify"))
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    run(args.mode, args.root.resolve())


if __name__ == "__main__":
    main()
