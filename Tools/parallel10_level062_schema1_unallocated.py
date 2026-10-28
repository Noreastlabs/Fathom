#!/usr/bin/env python3
"""Build source-bound, unallocated whole-Level62 schema1 tone fields."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

from parallel_07_level062_whole_candidate import build_candidate, EXPECTED, CELL_COUNTS, OPEN, PC, ROLE, NOTES


ROOT = Path(__file__).resolve().parents[1]
OUT_REL = Path("Build/parallel-10/level062-schema1-unallocated-r01")
INPUTS = {
    "Tools/parallel_07_level062_whole_candidate.py": "719dc41ed73e86f1cfa4092102b860dcb8f898a6e3f33761a038fb1c364cca53",
    "Results/parallel-07/conversion/20260923T162334Z-2.3.1.2.1-level062-whole-candidate-r01-results.md": "5dfc14660ebf203e8bb8eb59afe91647e79c08cb98e55c18d7e981d5edc594e4",
    "Build/parallel-07/2.3.1.2.1-level062-whole-r01/level062_whole_candidate.json": "f13cd189f0f56c1e0c2c79484dd7d4e35b06933783ea68914230bd3b8257558a",
    "Content/controls/curriculum-v1/package.json": "766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255",
    "Content/controls/curriculum-v1/identity-registry.json": "5d265859e1e8a5a530a0e53d88b019a1c920f3bba6cccb4ef0fef2f7640007e5",
    "Content/controls/curriculum-v1/generation.json": "fc6cec9f9d67eb82c97c5f4c3fb95d285178fb7fce7bd147d9ae0296d21b4c1c",
    "Results/parallel-01/exercises/inventory/20260922T180500Z-2.3-curriculum-v1-source-inventory-evidence/curriculum-source-map.json": "bad5581a04f43ba8baf14db430449e1ccff5cf88f0f7e42198328073b27053d6",
    "Notes/music/guitar project/TXT version/Guitar_Exercises_Section_VII_Level_62_Diagonal_Arpeggio_Connections_String_Skipping_Position_Shifts_and_Full_Neck_Chord_Tone_Motif_Development.txt": "39fca1f21a76fa206bad933fae6d5c2464bf21f2ab359e9bc6fcb8d67030eb8b",
    "Notes/music/guitar project/PDF version/Guitar_Exercises_Section_VII_Level_62_Diagonal_Arpeggio_Connections_String_Skipping_Position_Shifts_and_Full_Neck_Chord_Tone_Motif_Development.pdf": "b658be4914875592e4765c942afec45abd8f3d6459d78de378a148e400fca836",
}
UNRESOLVED = ["canonical workbook/module/item/event/variant IDs and lineage",
              "numeric onset/duration and fixed BPM; motif rest grid remains text",
              "performed pick direction, accent, route beyond printed TAB and mastery",
              "runtime admission"]


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


def read_inputs(root: Path) -> tuple[dict, dict, dict]:
    raw = {rel: pinned(root, rel, sha) for rel, sha in INPUTS.items()}
    candidate = json.loads(raw["Build/parallel-07/2.3.1.2.1-level062-whole-r01/level062_whole_candidate.json"])
    if candidate != json.loads(json.dumps(build_candidate(root))):
        raise ValueError("P07 candidate differs from original TXT/PDF/map replay")
    foundation = json.loads(raw["Content/controls/curriculum-v1/package.json"])
    registry = json.loads(raw["Content/controls/curriculum-v1/identity-registry.json"])
    generation = json.loads(raw["Content/controls/curriculum-v1/generation.json"])
    if len(foundation["records"]) != 659 or generation["records"] != 659:
        raise ValueError("current659 foundation drift")
    return candidate, foundation, registry


def identity_boundary(foundation: dict, registry: dict) -> dict:
    workbook = "fg:workbook:000062"
    if any(r.get("legacy_level") == 62 or r.get("workbook_id") == workbook for r in foundation["records"]):
        raise ValueError("unexpected canonical Level62 record")
    if any(e.get("id") == workbook for e in registry["entities"]):
        raise ValueError("unexpected Level62 registry entity")
    entry = next((e for e in foundation["workbook_catalog"]["entries"] if e.get("workbook_id") == workbook), None)
    if (not entry or entry.get("representative_item_id") is not None or
        entry.get("whole_workbook_complete") is not False or entry.get("admitted") is not False or
        entry.get("conversion_status") != "not_converted"):
        raise ValueError("Level62 source-only catalog drift")
    return entry


def source_line(ref: str) -> int:
    match = re.fullmatch(r"L62-TXT1-(\d+)(?:-\d+)?", ref)
    if not match:
        raise ValueError("invalid Level62 source reference")
    return int(match.group(1))


def ordered_units(module: dict, letter: str) -> list[tuple[str, dict]]:
    units = [("tab_grid", cell) for cell in module["cells"]]
    if letter == "J":
        units += [("recovery_card", card) for card in module["recovery_cards"]]
    return sorted(units, key=lambda pair: source_line(pair[1]["source_ref"]))


def validate_tone(tone: dict) -> None:
    if tone.get("sounded") is not True or tone.get("onset_q") is not None or tone.get("duration_q") is not None:
        raise ValueError("source tone timing/sounding boundary drift")
    string, fret, note, chord, role = (tone.get(k) for k in ("string", "fret", "note", "chord", "role"))
    if string not in OPEN or not isinstance(fret, int) or fret < 0 or fret > 20 or note not in PC or not isinstance(chord, str):
        raise ValueError("source tone field drift")
    root = NOTES.match(chord)
    if root is None or (OPEN[string] + fret) % 12 != PC[note]:
        raise ValueError("source tone pitch drift")
    if role != "app" and (role not in ROLE or (PC[root.group()] + ROLE[role]) % 12 != PC[note]):
        raise ValueError("source tone role drift")


def project(candidate: dict, foundation: dict, registry: dict) -> tuple[dict, dict]:
    entry = identity_boundary(foundation, registry)
    if (candidate.get("schema") != "fathom.level62.whole.detached_candidate.v1" or
        candidate.get("level") != 62 or candidate.get("wbs") != "2.3.1.2.1" or
        candidate.get("status") != "candidate_only" or candidate.get("stable_ids") is not None or
        candidate.get("imported") is not False or candidate.get("admitted") is not False):
        raise ValueError("Level62 source identity/admission drift")
    if candidate.get("workload") != {"module_tones": EXPECTED, "total_sounding_tones": 788,
                                      "recovery_tones": 24, "bridge_tones": 40}:
        raise ValueError("788 source workload drift")
    if candidate.get("timing_boundary") != (
        "No numeric BPM, onset, or duration is assigned; PDF motif rest grid and written quarter-note-speed instruction remain text."):
        raise ValueError("Level62 timing boundary drift")
    if len(candidate["source_transcription"]["txt_lines"]) != 874 or len(candidate["source_transcription"]["pdf_pages"]) != 20:
        raise ValueError("full-source transcription drift")
    directions = candidate["pdf_only_directions"]
    if (len(directions["connection_zones"]) != 5 or len(directions["module_page_guidance"]) != 16 or
        directions["motif_grid"] != "rest - notes 1-2 - rest - notes 3-4 - repeat through bars" or
        not directions["major_capstone_key_announcement"] or not directions["minor_capstone_pick_option"] or
        not directions["recovery_framing"] or not directions["completion_audit_and_practice_log"]):
        raise ValueError("PDF-only direction drift")
    modules = candidate["modules"]
    if list(modules) != list("ABCDEFGHIJ"):
        raise ValueError("module sequence drift")
    records = []
    total = 0
    units_total = 0
    grid_total = 0
    recovery_total = 0
    for letter in "ABCDEFGHIJ":
        module = modules[letter]
        if len(module["cells"]) != CELL_COUNTS[letter]:
            raise ValueError(f"{letter} grid count drift")
        units = ordered_units(module, letter)
        events = []
        variants = []
        for unit_number, (unit_type, unit) in enumerate(units, 1):
            tones = unit["events"]
            if len(tones) != unit["tone_count"]:
                raise ValueError(f"{letter} source-unit tone count drift")
            if unit_type == "tab_grid" and unit["pdf_grid_status"] != ("summary_only" if letter == "J" else "exact_row_parity"):
                raise ValueError("PDF grid parity-status drift")
            if unit_type == "recovery_card" and unit["tone_count"] != 2:
                raise ValueError("recovery-card tone count drift")
            start = len(events) + 1
            for tone in tones:
                validate_tone(tone)
                events.append({"source_module": letter, "source_unit_number": unit_number,
                               "source_unit_type": unit_type, "source_local_ordinal": len(events) + 1,
                               "source_txt_ref": unit["source_ref"], "source_pdf_page": unit["pdf_page"],
                               "source_pdf_grid_status": unit.get("pdf_grid_status", "summary_only"),
                               "source_tone": tone,
                               "schema1_fields": {"event_id": None, "kind": "contact", "contact": "pitched",
                                                  "pick": None, "pitch_binding": None,
                                                  "onset_q": None, "duration_q": None}})
            variants.append({"id": None, "source_unit_number": unit_number, "source_unit_type": unit_type,
                             "source_unit": unit, "source_event_ordinals": list(range(start, len(events) + 1)),
                             "event_ids": None, "runtime_eligible": False})
            units_total += 1
            grid_total += unit_type == "tab_grid"
            recovery_total += unit_type == "recovery_card"
        if len(events) != EXPECTED[letter] or module["tone_count"] != EXPECTED[letter]:
            raise ValueError(f"{letter} projected tone count drift")
        total += len(events)
        records.append({"source_component": letter, "source_module": module,
                        "identity_state": "unallocated",
                        "schema1_fields": {"id": None, "workbook_id": None, "module_id": None,
                                           "legacy_level": 62, "title": f"Level 62 component {letter}",
                                           "kind": "mixed", "content_revision": None, "lineage": None,
                                           "source_refs": None, "events": events, "variants": variants,
                                           "runtime_eligible": False, "resource_requirements": [],
                                           "timing": {"status": "unresolved", "unit": "quarter", "fixed_bpm": None},
                                           "ambiguities": UNRESOLVED}})
    if total != 788 or units_total != 83 or grid_total != 71 or recovery_total != 12:
        raise ValueError("whole-Level62 tone/unit separation drift")
    j = records[9]["schema1_fields"]
    if ([v["source_unit_type"] for v in j["variants"]] != ["recovery_card"] * 12 + ["tab_grid"] * 5 or
        sum(e["source_unit_type"] == "recovery_card" for e in j["events"]) != 24):
        raise ValueError("J recovery/bridge source order drift")
    proposal = {"proposal_version": "level062-unallocated-schema1-fields.1", "wbs_id": "2.3.1.2.1",
                "classification": "Build-only, nonimportable schema1 field proposal", "legacy_level": 62,
                "canonical_ids_allocated": False, "schema1_importable": False,
                "whole_workbook_complete": False, "runtime_eligible": False, "admitted": False,
                "counts": {"provisional_components": 10, "attack_units": 83, "tab_grids": 71,
                           "recovery_cards": 12, "printed_sounding_tones": 788,
                           "J_recovery_tones": 24, "J_bridge_tones": 40},
                "source": candidate["source"], "core_rules": candidate["core_rules"],
                "pdf_only_directions": directions, "mastery": candidate["mastery"],
                "timing_boundary": candidate["timing_boundary"],
                "source_transcription": candidate["source_transcription"], "records": records}
    handoff = {"handoff_version": "level062-allocation-handoff.1", "wbs_id": "2.3.1.2.1",
               "catalog_workbook_id": entry["workbook_id"], "catalog_role": entry["catalog_role"],
               "existing_level062_records": 0, "existing_level062_workbook_entities": 0,
               "printed_sounding_tones": 788, "attack_units": 83,
               "proposed_component_partition": list("ABCDEFGHIJ"),
               "canonical_ids_allocated": False, "admitted": False,
               "required_decisions": ["Allocate stable identities after registry reservations are sealed.",
                   "Resolve numerical timing, pick/accent and any performance policy before native import or admission."]}
    return proposal, handoff


def products(root: Path) -> dict[str, object]:
    candidate, foundation, registry = read_inputs(root)
    proposal, handoff = project(candidate, foundation, registry)
    manifest = {"manifest_version": "level062-input-pins.1", "inputs": [
        {"path": rel, "bytes": (root / rel).stat().st_size, "sha256": sha} for rel, sha in INPUTS.items()]}
    summary = {"summary_version": "level062-schema1-unallocated-summary.1",
               "proposal_sha256": digest(encoded(proposal)), "handoff_sha256": digest(encoded(handoff)),
               "printed_sounding_tones": 788, "attack_units": 83, "native_run": False,
               "runtime_eligible": False, "admitted": False}
    return {"field-proposal.json": proposal, "allocation-handoff.json": handoff,
            "input-manifest.json": manifest, "summary.json": summary}


def run(mode: str, root: Path) -> None:
    built = products(root)
    out = root / OUT_REL
    part = root
    for component in OUT_REL.parts:
        part /= component
        if part.is_symlink():
            raise ValueError("output symlink path")
    if mode == "build":
        out.mkdir(parents=True, exist_ok=True)
        for name, value in built.items():
            (out / name).write_bytes(encoded(value))
    else:
        for name, value in built.items():
            path = out / name
            if path.is_symlink() or path.read_bytes() != encoded(value):
                raise ValueError(f"output drift: {name}")
    print(f"LEVEL62 {mode.upper()} PASS tones=788 units=83 admitted=false")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("build", "verify"))
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    run(args.mode, args.root.resolve())


if __name__ == "__main__":
    main()
