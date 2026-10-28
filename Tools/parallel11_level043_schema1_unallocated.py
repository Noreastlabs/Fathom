#!/usr/bin/env python3
"""Replay whole-Level43 source and sketch unallocated schema1 fields."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from curriculum_level043_whole_blue_note_candidate import (
    CHROMATIC_SITES, DEGREE, MAP_REL, MODULE_COUNTS, MODULE_PAGES,
    OPEN, PITCH, SRC, TXT_REL, PDF_REL, build_candidate,
)


ROOT = Path(__file__).resolve().parents[1]
OUT_REL = Path("Build/parallel-11/2.3.1.1.1-level043-schema1-unallocated-r01")
INPUTS = {
    "Tools/curriculum_level043_whole_blue_note_candidate.py": "c66598bd7979e17cd0d6edfe52cec09bdfb2b9b0b2e9f35a3a1eafe8e14d18fd",
    "Results/parallel-05/exercises/conversion/20260923T154000Z-2.3.1.1.1-level043-whole-blue-note-r01-results.md": "760fc79fc66b10665840059c6948e4f1d12ee4f202f300449a94df9b58d42247",
    "Build/parallel-05/2.3.1.1.1-level043-whole-r01/candidate-b.json": "7c59443809be927bf93924cee6a7b505e7e80d02dbf7fd51179fdcb60eef5155",
    "Build/parallel-05/2.3.1.1.1-level043-whole-r01/candidate-c.json": "7c59443809be927bf93924cee6a7b505e7e80d02dbf7fd51179fdcb60eef5155",
    "Content/controls/curriculum-v1/package.json": "766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255",
    "Content/controls/curriculum-v1/identity-registry.json": "5d265859e1e8a5a530a0e53d88b019a1c920f3bba6cccb4ef0fef2f7640007e5",
    "Content/controls/curriculum-v1/generation.json": "fc6cec9f9d67eb82c97c5f4c3fb95d285178fb7fce7bd147d9ae0296d21b4c1c",
    TXT_REL: SRC[1], PDF_REL: SRC[3], MAP_REL: "bad5581a04f43ba8baf14db430449e1ccff5cf88f0f7e42198328073b27053d6",
    "Notes/music/guitar project/TXT version/Scale_Exercises_Section_V_Level_41_A_Minor_Pentatonic_Five_Position_Map_and_Connection_Fixed_Key_A.txt": "40188b431cf51581e9fe1df01b50b6bb459482fdbf322822d845c2d45a1cb00a",
    "Notes/music/guitar project/PDF version/Scale_Exercises_Section_V_Level_41_A_Minor_Pentatonic_Five_Position_Map_and_Connection_Fixed_Key_A.pdf": "97e30c02960dc260a459bb6a4c38cb4d5c36998952ae876264e839bc40f0c576",
    "Notes/music/guitar project/TXT version/Scale_Exercises_Section_V_Level_42_A_Minor_Pentatonic_Horizontal_Movement_and_Articulation_Fixed_Key_A.txt": "4d658466a731cf3de48c02cd8694651a3294d27af588a344926aa85e2d64f65b",
    "Notes/music/guitar project/PDF version/Scale_Exercises_Section_V_Level_42_A_Minor_Pentatonic_Horizontal_Movement_and_Articulation_Fixed_Key_A.pdf": "fed7a629ecf0c0ff4e7015187ce858a21d333409aedc37bde7b6561b05b5c61d",
}
OPEN_MIDI = {"E": 40, "A": 45, "D": 50, "G": 55, "B": 59, "e": 64}
STRING_NUMBER = {"E": 1, "A": 2, "D": 3, "G": 4, "B": 5, "e": 6}
UNIT_COUNTS = {"A": 4, "B": 10, "C": 6, "D": 5, "E": 6, "F": 6, "G": 4, "H": 3, "I": 6}
UNRESOLVED = [
    "P02 has not allocated canonical workbook, module/item, event or variant IDs and lineage.",
    "Printed D/U, skeleton, accent, legato, Eb-role and reverse alternatives are instructions; no actual choice is observed.",
    "One-note-per-click, triplet, sixteenth, slide subdivision, Eb-hold and tempo guidance do not assign onset_q, duration_q, note_per_click or fixed_bpm.",
    "PDF p16 post-clean variations are supplemental and await Curriculum review; they add no core contacts.",
    "No performed quality, mastery, native import, runtime eligibility or admission is evidenced.",
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
    a = raw["Build/parallel-05/2.3.1.1.1-level043-whole-r01/candidate-b.json"]
    b = raw["Build/parallel-05/2.3.1.1.1-level043-whole-r01/candidate-c.json"]
    if a != b:
        raise ValueError("sealed Level43 twins differ")
    c = json.loads(a)
    if c != build_candidate(root):
        raise ValueError("sealed Level43 candidate differs from original TXT/PDF/source-map replay")
    source_map = json.loads(raw[MAP_REL])
    row = source_map["rows"][42]
    if (row.get("level") != 43 or row.get("wbs_owner") != "2.3.1.1.1"
            or row.get("conversion_status") != "not_converted"
            or row.get("stable_ids_assigned") is not False or row.get("admitted") is not False
            or row.get("txt_sha256") != INPUTS[TXT_REL] or row.get("pdf_sha256") != INPUTS[PDF_REL]):
        raise ValueError("frozen source map row drift")
    foundation = json.loads(raw["Content/controls/curriculum-v1/package.json"])
    registry = json.loads(raw["Content/controls/curriculum-v1/identity-registry.json"])
    generation = json.loads(raw["Content/controls/curriculum-v1/generation.json"])
    if len(foundation["records"]) != 659 or generation["records"] != 659:
        raise ValueError("current659 foundation drift")
    return c, row, foundation, registry


def identity_boundary(foundation: dict, registry: dict) -> dict:
    workbook = "fg:workbook:000043"
    if any(r.get("legacy_level") == 43 or r.get("workbook_id") == workbook for r in foundation["records"]):
        raise ValueError("unexpected canonical Level43 record")
    if any(e.get("id") == workbook for e in registry["entities"]):
        raise ValueError("unexpected Level43 registry entity")
    entry = next((e for e in foundation["workbook_catalog"]["entries"] if e.get("workbook_id") == workbook), None)
    if (not entry or entry.get("representative_item_id") is not None
            or entry.get("whole_workbook_complete") is not False
            or entry.get("admitted") is not False or entry.get("imported") is not False
            or entry.get("runtime_eligible") is not False
            or entry.get("conversion_status") != "not_converted"
            or entry.get("stable_identity_status") != "evidenced_source_only"):
        raise ValueError("Level43 source-only catalog drift")
    return entry


def validate_candidate(c: dict) -> None:
    if (c.get("schema") != "fathom.detached-source-candidate.1" or c.get("section") != "V"
            or c.get("level") != 43 or c.get("wbs_id") != "2.3.1.1.1"
            or c.get("canonical_ids") is not None or c.get("review") != "Pending"
            or any(c.get(k) is not False for k in ("runtime_eligible", "imported", "admitted"))
            or c.get("performed_tempo") is not None or c.get("performed_mastery") is not None):
        raise ValueError("source identity/admission/performance drift")
    if (c.get("module_count"), c.get("sounding_tone_count"), c.get("printed_pick_attack_count")) != (9, 422, 382):
        raise ValueError("9/422/382 source count drift")
    if (c.get("scale", {}).get("tonic") != "A" or c["scale"].get("notes") != ["A", "C", "D", "Eb", "E", "G"]
            or c["scale"].get("degrees") != ["1", "b3", "4", "b5", "5", "b7"]
            or c["scale"].get("blue_note", {}).get("note") != "Eb"
            or c["scale"]["blue_note"].get("degree") != "b5"
            or c["scale"]["blue_note"].get("core_sites") != [
                {"string": s, "frets": list(frets)} for s, frets in CHROMATIC_SITES.items()]
            or c["scale"]["blue_note"].get("extension") != {"string": "A", "frets": [17, 18, 19]}):
        raise ValueError("A-blues/blue-note source geometry drift")
    exc = c.get("source_exceptions")
    if (not isinstance(exc, list) or len(exc) != 1
            or exc[0].get("code") != "PDF_ONLY_POST_CLEAN_VARIATIONS"
            or exc[0].get("status") != "Pending Curriculum review"
            or exc[0].get("source") != "PDF p16"
            or c.get("music_row_exceptions") != []):
        raise ValueError("PDF-only post-clean/source exception drift")
    guidance = c.get("printed_guidance", {})
    if (guidance.get("kind") != "printed_instruction"
            or len(guidance.get("pdf_extracted_pages", [])) != 17
            or len(guidance.get("txt_full_text", "").splitlines()) != 554
            or len(guidance.get("core_alternatives", [])) != 6
            or "Hold Eb for one, two, and four beats" not in guidance.get("pdf_only_post_clean_variations", "")):
        raise ValueError("whole-source guidance/coverage drift")
    modules = c.get("modules")
    if not isinstance(modules, list) or [m.get("module") for m in modules] != list("ABCDEFGHI"):
        raise ValueError("A-I module order drift")
    total_tones = total_attacks = 0
    for m in modules:
        letter = m["module"]
        units = m.get("units", [])
        if (m.get("unit_count") != UNIT_COUNTS[letter] or len(units) != UNIT_COUNTS[letter]
                or (m.get("sounding_tones"), m.get("printed_pick_attacks")) != MODULE_COUNTS[letter]
                or m.get("pdf_pages") != MODULE_PAGES[letter]
                or sum(u.get("sounding_tones", -1) for u in units) != MODULE_COUNTS[letter][0]
                or sum(u.get("printed_pick_attacks", -1) for u in units) != MODULE_COUNTS[letter][1]):
            raise ValueError(f"module {letter} count/page drift")
        total_tones += m["sounding_tones"]
        total_attacks += m["printed_pick_attacks"]
        if letter == "A" and ([u["sounding_tones"] for u in units] != [7, 7, 13, 13]
                or any(units[i]["contacts"][-1]["note"] != "A"
                       or units[i + 1]["contacts"][0]["note"] != "A" for i in (0, 2))):
            raise ValueError("A reference high-root reattack drift")
        if letter == "B" and [u["sounding_tones"] for u in units] != [14, 14, 15, 15, 15, 15, 14, 14, 14, 14]:
            raise ValueError("B five-position insertion count drift")
        for unit_no, u in enumerate(units, 1):
            contacts = u.get("contacts", [])
            if (u.get("module") != letter or len(contacts) != u.get("sounding_tones")
                    or sum(x.get("printed_pick_attack") is True for x in contacts) != u.get("printed_pick_attacks")
                    or u.get("pdf_page") not in MODULE_PAGES[letter]
                    or not isinstance(u.get("txt_line"), int)):
                raise ValueError(f"{letter}{unit_no} contact/count/source drift")
            for contact in contacts:
                note, string, fret = contact.get("note"), contact.get("string"), contact.get("fret")
                finger = contact.get("printed_finger")
                if (note not in PITCH or string not in OPEN_MIDI or not isinstance(fret, int)
                        or (OPEN_MIDI[string] + fret) % 12 != PITCH[note]
                        or contact.get("degree") != DEGREE[note]
                        or finger is not None and finger not in (1, 2, 3, 4)
                        or contact.get("printed_pick_attack") not in (True, False)
                        or not contact.get("printed_articulation")
                        or contact.get("performed_onset") is not None
                        or contact.get("performed_duration") is not None
                        or contact.get("performed_pick") is not None):
                    raise ValueError(f"{letter}{unit_no} note/degree/string/fret/finger/performance drift")
            if letter == "C" and u.get("printed_pick_sequence") != ["D", "U", "D", "U", "D", "U"]:
                raise ValueError(f"C{unit_no} printed pick sequence drift")
            if letter == "E" and ([x["note"] for x in contacts] != ["D", "Eb", "E", "D"] * 2
                    or any("passing" not in x["printed_articulation"] for x in contacts[:4])
                    or any("resting" not in x["printed_articulation"] for x in contacts[4:])):
                raise ValueError(f"E{unit_no} passing/resting role drift")
            if letter == "F":
                if ([x["printed_pick_attack"] for x in contacts] != [True, False, False, True, False, False]
                        or [x["note"] for x in contacts] != ["D", "Eb", "E", "E", "Eb", "D"]
                        or [x["fret"] for x in contacts] != [CHROMATIC_SITES[contacts[0]["string"]][j] for j in (0, 1, 2, 2, 1, 0)]):
                    raise ValueError(f"F{unit_no} slide/attack drift")
            if letter == "G":
                rev = u.get("reverse_variation", {})
                if ([x["printed_pick_attack"] for x in contacts] != [True, False, False, False, True, False]
                        or [x["note"] for x in contacts] != ["C", "D", "Eb", "E", "G", "A"]
                        or rev.get("kind") != "printed_instruction_without_full_TAB"
                        or rev.get("degrees") != ["1", "b7", "5", "b5", "4", "b3"]
                        or rev.get("authored_reverse_contacts") is not None):
                    raise ValueError(f"G{unit_no} seam/reverse instruction drift")
            if letter == "H":
                slots = u.get("slots", [])
                printed = [s["contact"] for s in slots if s.get("kind") == "printed_note"]
                if (len(contacts) != 6 or len(slots) not in (8, 12) or printed != contacts
                        or any(s.get("kind") not in ("printed_note", "printed_rest")
                               or s.get("kind") == "printed_rest" and s.get("contact") is not None
                               or s.get("performed_onset") is not None or s.get("performed_duration") is not None
                               for s in slots)):
                    raise ValueError(f"H{unit_no} rest/slot drift")
    if (total_tones, total_attacks) != (422, 382):
        raise ValueError("whole module source totals drift")
    if not any(x["string"] == "A" and x["fret"] in (18, 19) for m in modules for u in m["units"] for x in u["contacts"]):
        raise ValueError("A-string fret-18/19 extension lost")


def event_fields(contact: dict) -> dict:
    return {"event_id": None, "kind": "note", "spelling": contact["note"],
            "string": STRING_NUMBER[contact["string"]], "fret": contact["fret"],
            "midi": OPEN_MIDI[contact["string"]] + contact["fret"],
            "finger": contact["printed_finger"], "source_degree": contact["degree"],
            "degree_contexts": {}, "printed_pick_attack": contact["printed_pick_attack"],
            "printed_articulation": contact["printed_articulation"],
            "attack": None, "pick": None, "tie_from": None, "accent": None,
            "onset_q": None, "duration_q": None, "performed": None}


def project(c: dict, row: dict, foundation: dict, registry: dict) -> tuple[dict, dict]:
    validate_candidate(c)
    entry = identity_boundary(foundation, registry)
    records = []
    for m in c["modules"]:
        units = []
        for unit_no, u in enumerate(m["units"], 1):
            events = [{"source_contact_ordinal": i, "source_contact": x, "schema1_fields": event_fields(x)}
                      for i, x in enumerate(u["contacts"], 1)]
            slots = []
            if m["module"] == "H":
                for slot in u["slots"]:
                    slots.append({"source_slot": slot, "schema1_fields": {
                        "event_id": None, "kind": "rest" if slot["kind"] == "printed_rest" else "note",
                        "onset_q": None, "duration_q": None, "performed": None}})
            units.append({"source_unit_number": unit_no, "source_unit": u,
                          "source_pdf_page": u["pdf_page"], "source_txt_line": u["txt_line"],
                          "source_sounding_tones": u["sounding_tones"],
                          "source_printed_pick_attacks": u["printed_pick_attacks"],
                          "event_field_proposals": events, "printed_slot_field_proposals": slots,
                          "canonical_variant_id": None, "actual_option_selected": None,
                          "performed": None})
        records.append({"source_component": m["module"], "source_module": m,
                        "identity_state": "unallocated", "schema1_fields": {
                            "id": None, "workbook_id": None, "module_id": None,
                            "legacy_level": 43, "title": f"Level 43 module {m['module']}",
                            "kind": "mixed", "content_revision": None, "lineage": None,
                            "status": "unallocated_source_projection", "runtime_eligible": False,
                            "admitted": False, "events": [], "variants": [],
                            "timing": {"status": "unresolved", "unit": "quarter", "onset_q": None,
                                       "duration_q": None, "fixed_bpm": None, "note_per_click": None},
                            "mastery_observed": None},
                        "unit_field_proposals": units})
    proposal = {"proposal_version": "level043-unallocated-schema1-fields.1", "wbs_id": "2.3.1.1.1",
                "classification": "Build-only, nonimportable schema1 field proposal", "legacy_level": 43,
                "canonical_ids_allocated": False, "schema1_importable": False,
                "whole_workbook_complete": False, "runtime_eligible": False, "admitted": False,
                "performed_mastery_observed": None, "performed_option_observed": None,
                "counts": {"provisional_components": 9, "source_units": sum(UNIT_COUNTS.values()),
                           "core_sounding_tones": 422, "core_printed_pick_attacks": 382,
                           "unpicked_arrivals": 40, "supplemental_pdf_p16_core_tones": 0,
                           "module_tones_and_attacks": {k: list(v) for k, v in MODULE_COUNTS.items()}},
                "source": c["source"], "scale": c["scale"],
                "printed_guidance": c["printed_guidance"],
                "source_exceptions": c["source_exceptions"],
                "music_row_exceptions": c["music_row_exceptions"],
                "unresolved": UNRESOLVED, "records": records}
    handoff = {"handoff_version": "level043-allocation-handoff.1", "wbs_id": "2.3.1.1.1",
               "catalog_workbook_id_read_only": entry["workbook_id"],
               "source_map_status_read_only": row["conversion_status"],
               "existing_level043_records": 0, "existing_level043_workbook_entities": 0,
               "core_sounding_tones": 422, "core_printed_pick_attacks": 382,
               "canonical_ids_allocated": False, "admitted": False,
               "required_decisions": ["Review whole-source blue-note geometry and PDF-only p16 post-clean panel.",
                                      "Allocate stable workbook, module, item, event and variant identities/lineage through P02.",
                                      "Authorize timing/click, articulation and performed option semantics before native import.",
                                      "Review expected profile and performed mastery before Curriculum admission."]}
    return proposal, handoff


def products(root: Path) -> dict[str, object]:
    c, row, foundation, registry = read_inputs(root)
    proposal, handoff = project(c, row, foundation, registry)
    manifest = {"manifest_version": "level043-schema1-input-pins.1", "inputs": [
        {"path": rel, "bytes": (root / rel).stat().st_size, "sha256": sha} for rel, sha in INPUTS.items()]}
    summary = {"summary_version": "level043-schema1-unallocated-summary.1",
               "proposal_sha256": digest(encoded(proposal)), "handoff_sha256": digest(encoded(handoff)),
               "core_sounding_tones": 422, "core_printed_pick_attacks": 382,
               "native_run": False, "runtime_eligible": False, "admitted": False}
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
    print(f"LEVEL43 {mode.upper()} PASS modules=9 tones=422 attacks=382 admitted=false")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("build", "verify"))
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    run(args.mode, args.root.resolve())


if __name__ == "__main__":
    main()
