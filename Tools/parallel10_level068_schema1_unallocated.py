#!/usr/bin/env python3
"""Build pinned whole-Level68 source tones as unallocated schema1 fields."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from curriculum_level068_whole_candidate import build_candidate, CELL_COUNTS, DEGREE, EXPECTED, OPEN, PC


ROOT = Path(__file__).resolve().parents[1]
OUT_REL = Path("Build/parallel-10/level068-schema1-unallocated-r01")
INPUTS = {
    "Tools/curriculum_level068_whole_candidate.py": "f20d63a16f36b451e2814ddb1039fb3d3c1fbd86eaac889025c7b4b00383abd0",
    "Results/parallel-11/curriculum/20260923T170000Z-2.3-level068-whole-r01-results.md": "1cd5cf76d32f4f29059c91d066d5a2ee9873baa2d88efe8bf7c0d50b008b0e20",
    "Build/parallel-11/2.3.1.2.1-level068-whole-r01/candidate-d.json": "a7255f87cc5267b30a7e3acc83201f7bb4dd4a3d2fb16c0c5d81dac5c5b92507",
    "Build/parallel-11/2.3.1.2.1-level068-whole-r01/candidate-e.json": "a7255f87cc5267b30a7e3acc83201f7bb4dd4a3d2fb16c0c5d81dac5c5b92507",
    "Content/controls/curriculum-v1/package.json": "766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255",
    "Content/controls/curriculum-v1/identity-registry.json": "5d265859e1e8a5a530a0e53d88b019a1c920f3bba6cccb4ef0fef2f7640007e5",
    "Content/controls/curriculum-v1/generation.json": "fc6cec9f9d67eb82c97c5f4c3fb95d285178fb7fce7bd147d9ae0296d21b4c1c",
    "Results/parallel-01/exercises/inventory/20260922T180500Z-2.3-curriculum-v1-source-inventory-evidence/curriculum-source-map.json": "bad5581a04f43ba8baf14db430449e1ccff5cf88f0f7e42198328073b27053d6",
    "Notes/music/guitar project/TXT version/Guitar_Exercises_Section_VIII_Level_68_E_Phrygian_Dominant_Diminished_Seventh_Symmetry_Altered_Dominant_Colors_and_Harmonic_Minor_Improvisation_Synthesis.txt": "e270fa9365dfd6e061ce4fd7807df1ba0d82fc52b867dc1b29ec180cb7923f2b",
    "Notes/music/guitar project/PDF version/Guitar_Exercises_Section_VIII_Level_68_E_Phrygian_Dominant_Diminished_Seventh_Symmetry_Altered_Dominant_Colors_and_Harmonic_Minor_Improvisation_Synthesis.pdf": "4db7d55cd64c1b038dfce68dfc3eda60fc82077fcf21532d96ad79457031a378",
}
UNRESOLVED = ["canonical workbook/module/item/event/variant IDs and lineage",
              "F1 printed final B versus PDF final-E instruction, pending Curriculum review",
              "K improvised pass notes and recovery-card string/fret choices",
              "numeric quarter onset/duration, fixed BPM and performed pick/accent",
              "human mastery and runtime admission"]


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
    d = raw["Build/parallel-11/2.3.1.2.1-level068-whole-r01/candidate-d.json"]
    e = raw["Build/parallel-11/2.3.1.2.1-level068-whole-r01/candidate-e.json"]
    if d != e:
        raise ValueError("P11 sealed candidate twins differ")
    candidate = json.loads(d)
    if candidate != json.loads(json.dumps(build_candidate(root))):
        raise ValueError("P11 candidate differs from original TXT/PDF/map replay")
    foundation = json.loads(raw["Content/controls/curriculum-v1/package.json"])
    registry = json.loads(raw["Content/controls/curriculum-v1/identity-registry.json"])
    generation = json.loads(raw["Content/controls/curriculum-v1/generation.json"])
    if len(foundation["records"]) != 659 or generation["records"] != 659:
        raise ValueError("current659 foundation drift")
    return candidate, foundation, registry


def identity_boundary(foundation: dict, registry: dict) -> dict:
    workbook = "fg:workbook:000068"
    if any(r.get("legacy_level") == 68 or r.get("workbook_id") == workbook for r in foundation["records"]):
        raise ValueError("unexpected canonical Level68 record")
    if any(e.get("id") == workbook for e in registry["entities"]):
        raise ValueError("unexpected Level68 registry entity")
    entry = next((e for e in foundation["workbook_catalog"]["entries"] if e.get("workbook_id") == workbook), None)
    if (not entry or entry.get("representative_item_id") is not None or
        entry.get("whole_workbook_complete") is not False or entry.get("admitted") is not False or
        entry.get("conversion_status") != "not_converted"):
        raise ValueError("Level68 source-only catalog drift")
    return entry


def _check_source_event(event: dict) -> None:
    name, string, fret = event["note"], event["string"], event["fret"]
    if (name not in PC or string not in OPEN or not isinstance(fret, int) or not 0 <= fret <= 20 or
        event["pitch_class"] != PC[name] or (OPEN[string] + fret) % 12 != PC[name]):
        raise ValueError("source note/TAB pitch drift")
    if event["degree"] != DEGREE[name] or not event["degree_slot_raw"].startswith(DEGREE[name]):
        raise ValueError("source harmonic-minor degree drift")
    if not isinstance(event["source_column"], int) or not isinstance(event["source_bar_ordinal"], int):
        raise ValueError("source printed position drift")


def _event(letter: str, unit_number: int, ordinal: int, txt_ref: str, pdf_ref: str,
           source_tone: dict, unit_type: str) -> dict:
    return {"source_component": letter, "source_unit_number": unit_number,
            "source_local_ordinal": ordinal, "source_unit_type": unit_type,
            "source_txt_ref": txt_ref, "source_pdf_ref": pdf_ref, "source_tone": source_tone,
            "performed_member_pitches": None,
            "schema1_fields": {"event_id": None, "kind": "contact", "contact": "pitched",
                               "pick": None, "pitch_binding": None, "onset_q": None,
                               "duration_q": None}}


def project(candidate: dict, foundation: dict, registry: dict) -> tuple[dict, dict]:
    entry = identity_boundary(foundation, registry)
    if (candidate.get("schema") != "fathom.level068.detached-source-candidate.1" or
        candidate.get("wbs") != "2.3.1.2.1" or candidate.get("status") != "non_admitted" or
        candidate.get("admitted") is not False or any(candidate.get(k) is not None for k in (
            "canonical_id", "exercise_id", "onset_q", "duration_q", "fixed_bpm",
            "executable_events", "sounding_midi_events"))):
        raise ValueError("Level68 source identity/performance drift")
    if candidate.get("printed_tones_by_module") != EXPECTED or candidate.get("printed_sounding_tones") != 630:
        raise ValueError("630-tone source workload drift")
    if list(candidate["modules"]) != list("ABCDEFGHIJ") or list(candidate["source_sections"]) != list("ABCDEFGHIJK"):
        raise ValueError("Level68 module sequence drift")
    guidance = candidate["guidance"]
    if len(guidance["txt_full_lines"]) != 871 or len(guidance["pdf_full_extracted_pages"]) != 20:
        raise ValueError("whole-source guidance drift")
    conflicts = candidate["source_ambiguities"]
    if (len(conflicts) != 1 or conflicts[0]["kind"] != "F1_PDF_final_E_instruction_conflicts_with_printed_final_B" or
        conflicts[0]["status"] != "pending_curriculum_review" or conflicts[0]["printed_final_note"] != "B" or
        conflicts[0]["pdf_ref"] != "L68-PDF-p10-L7" or
        conflicts[0]["txt_ref"] != candidate["modules"]["F"][0]["txt_ref"] or
        conflicts[0]["pdf_instruction"] != guidance["pdf_full_extracted_pages"][9][6] or
        "resolve the final E clearly" not in conflicts[0]["pdf_instruction"]):
        raise ValueError("F1 source conflict drift")
    if [d["kind"] for d in candidate["source_differences"]] != [
        "PDF_I_combines_call_answer_note_rows", "PDF_K_adds_capstone_rubric_and_phrase_constraints",
        "PDF_only_recovery_ear_tests_and_practice_log"]:
        raise ValueError("PDF-specific guidance drift")
    capstone = candidate["capstone"]
    if (len(capstone["four_bar_groups_raw"]) != 4 or len(capstone["pass_constraints_raw"]) != 3 or
        capstone["pdf_rubric_page_ref"] != "L68-PDF-p18" or
        "one full-beat rest every four bars" not in capstone["rest_and_close_raw"]):
        raise ValueError("K capstone direction drift")
    records = []
    total = 0
    unit_total = 0
    for letter in "ABCDEFGHIJK":
        section = candidate["source_sections"][letter]
        units = candidate["modules"][letter] if letter != "K" else candidate["recovery_cards"]
        if len(units) != (CELL_COUNTS[letter] if letter != "K" else 12):
            raise ValueError(f"{letter} source unit count drift")
        events = []
        variants = []
        for unit_number, unit in enumerate(units, 1):
            start = len(events) + 1
            if letter == "K":
                if unit["printed_tones"] != 2 or unit["weak_note"] not in PC or unit["target_note"] not in PC:
                    raise ValueError("K recovery pair drift")
                tones = [{"note": unit["weak_note"], "role_raw": unit["weak_role"], "string": None,
                          "fret": None, "pitch_class": None, "source_position": "weak"},
                         {"note": unit["target_note"], "role_raw": unit["target_role"], "string": None,
                          "fret": None, "pitch_class": None, "source_position": "target"}]
                unit_type = "recovery_pair"
                pdf_ref = unit["pdf_ref"]
            else:
                if unit["printed_tones"] != len(unit["events"]):
                    raise ValueError(f"{letter} printed tone count drift")
                for source_event in unit["events"]:
                    _check_source_event(source_event)
                if [e["note"] for e in unit["events"]] != unit["note_names"]:
                    raise ValueError(f"{letter} note order drift")
                tones = unit["events"]
                unit_type = "tab_cell"
                pdf_ref = unit["pdf_ref"]
            for tone in tones:
                events.append(_event(letter, unit_number, len(events) + 1, unit["txt_ref"],
                                     pdf_ref, tone, unit_type))
            variants.append({"id": None, "source_unit_number": unit_number,
                             "source_unit_type": unit_type, "source_unit": unit,
                             "source_event_ordinals": list(range(start, len(events) + 1)),
                             "event_ids": None, "runtime_eligible": False})
            unit_total += 1
        if len(events) != EXPECTED[letter]:
            raise ValueError(f"{letter} projected tone count drift")
        total += len(events)
        records.append({"source_component": letter, "source_heading": section["heading"],
                        "source_txt_ref": section["txt_ref"], "source_section": section,
                        "identity_state": "unallocated",
                        "schema1_fields": {"id": None, "workbook_id": None, "module_id": None,
                                           "legacy_level": 68, "title": f"Level 68 component {letter}",
                                           "kind": "mixed", "content_revision": None, "lineage": None,
                                           "source_refs": None, "events": events, "variants": variants,
                                           "runtime_eligible": False, "resource_requirements": [],
                                           "timing": {"status": "unresolved", "unit": "quarter", "fixed_bpm": None},
                                           "ambiguities": UNRESOLVED}})
    if total != 630 or unit_total != 79 or records[5]["schema1_fields"]["events"][7]["source_tone"]["note"] != "B":
        raise ValueError("whole-Level68 workload/F1 endpoint drift")
    if any(e["source_tone"]["string"] is not None or e["source_tone"]["fret"] is not None
           for e in records[10]["schema1_fields"]["events"]):
        raise ValueError("invented K recovery contact")
    proposal = {"proposal_version": "level068-unallocated-schema1-fields.1", "wbs_id": "2.3.1.2.1",
                "classification": "Build-only, nonimportable schema1 field proposal", "legacy_level": 68,
                "canonical_ids_allocated": False, "schema1_importable": False,
                "whole_workbook_complete": False, "runtime_eligible": False, "admitted": False,
                "counts": {"provisional_components": 11, "attack_units": 79, "tab_cells": 67,
                           "recovery_pairs": 12, "printed_sounding_tones": 630},
                "source": candidate["source"], "source_ambiguities": conflicts,
                "source_differences": candidate["source_differences"],
                "capstone": capstone, "guidance": guidance, "records": records}
    handoff = {"handoff_version": "level068-allocation-handoff.1", "wbs_id": "2.3.1.2.1",
               "catalog_workbook_id": entry["workbook_id"], "catalog_role": entry["catalog_role"],
               "existing_level068_records": 0, "existing_level068_workbook_entities": 0,
               "printed_sounding_tones": 630, "attack_units": 79,
               "F1_conflict_status": "pending_curriculum_review",
               "proposed_component_partition": list("ABCDEFGHIJK"),
               "canonical_ids_allocated": False, "admitted": False,
               "required_decisions": ["Curriculum resolves F1 printed-final-B versus PDF-final-E instruction without source rewriting.",
                   "Allocate stable identities after registry reservations are sealed.",
                   "Specify timing, pick and any improvised-pass note choices before native import or admission."]}
    return proposal, handoff


def products(root: Path) -> dict[str, object]:
    candidate, foundation, registry = read_inputs(root)
    proposal, handoff = project(candidate, foundation, registry)
    manifest = {"manifest_version": "level068-input-pins.1", "inputs": [
        {"path": rel, "bytes": (root / rel).stat().st_size, "sha256": sha} for rel, sha in INPUTS.items()]}
    summary = {"summary_version": "level068-schema1-unallocated-summary.1",
               "proposal_sha256": digest(encoded(proposal)), "handoff_sha256": digest(encoded(handoff)),
               "printed_sounding_tones": 630, "attack_units": 79,
               "native_run": False, "runtime_eligible": False, "admitted": False}
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
    print(f"LEVEL68 {mode.upper()} PASS tones=630 units=79 admitted=false")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("build", "verify"))
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    run(args.mode, args.root.resolve())


if __name__ == "__main__":
    main()
