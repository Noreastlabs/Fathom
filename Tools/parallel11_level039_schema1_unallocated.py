#!/usr/bin/env python3
"""Replay whole-Level39 source into unallocated, source-bound schema1 fields."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from curriculum_level039_whole_candidate import (
    F_ROOTS, OPEN, PDF, ROLES, TXT, build_candidate, check_rows,
)


ROOT = Path(__file__).resolve().parents[1]
OUT_REL = Path("Build/parallel-11/2.3.1.1.1-level039-schema1-unallocated-r01")
MAP_REL = "Results/parallel-01/exercises/inventory/20260922T180500Z-2.3-curriculum-v1-source-inventory-evidence/curriculum-source-map.json"
INPUTS = {
    "Tools/curriculum_level039_whole_candidate.py": "1e2be8e7bf26e213f48638aa042020ff92114aaecc26a11e60b9e3c852d4744f",
    "Results/parallel-11/curriculum/20260923T153400Z-2.3-level039-whole-r01-results.md": "8297d899355410ae53a1f5fce6cb4fed99fed76e6f40c91d715284d36f7ecf63",
    "Build/parallel-11/2.3.1.1.1-level039-whole-r01/candidate-e.json": "ecbc45cee080c422c42dd3f4e992146b04f7bdc6b11d8e2338b8079e4b80ef8e",
    "Build/parallel-11/2.3.1.1.1-level039-whole-r01/candidate-f.json": "ecbc45cee080c422c42dd3f4e992146b04f7bdc6b11d8e2338b8079e4b80ef8e",
    "Content/controls/curriculum-v1/package.json": "766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255",
    "Content/controls/curriculum-v1/identity-registry.json": "5d265859e1e8a5a530a0e53d88b019a1c920f3bba6cccb4ef0fef2f7640007e5",
    "Content/controls/curriculum-v1/generation.json": "fc6cec9f9d67eb82c97c5f4c3fb95d285178fb7fce7bd147d9ae0296d21b4c1c",
    TXT[0]: TXT[1], PDF[0]: PDF[1], MAP_REL: "bad5581a04f43ba8baf14db430449e1ccff5cf88f0f7e42198328073b27053d6",
}
COUNTS = {"A": 80, "B": 120, "C": 82, "D": 48, "E": 60, "F": 32, "G": 40}
MODULE_KEYS = {"A": "A_drone_comparison", "B": "B_dual_degree_boxes", "C": "C_root_to_root_cells",
               "D": "D_accent_relocation", "E": "E_paired_cadences", "F": "F_tonic_pivot", "G": "G_ear_cards"}
STRING_NUMBER = {"E": 1, "A": 2, "D": 3, "G": 4, "B": 5, "e": 6}
UNRESOLVED = [
    "The selected P1 representative and its revision lineage are read-only; new canonical identities/lineage are unallocated.",
    "The 462 written workload occurrences do not establish performed passes, drones, accents, holds or an ear-test score.",
    "Printed quarter-note and swing practice does not assign onset_q, duration_q, fixed_bpm or click mapping.",
    "Twenty-four TXT/PDF presentation differences and four guidance variants await Curriculum editorial review.",
    "No whole-workbook native import, runtime eligibility, mastery or admission is evidenced.",
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


def read_inputs(root: Path) -> tuple[dict, dict, dict, dict, dict]:
    raw = {rel: pinned(root, rel, sha) for rel, sha in INPUTS.items()}
    a = raw["Build/parallel-11/2.3.1.1.1-level039-whole-r01/candidate-e.json"]
    b = raw["Build/parallel-11/2.3.1.1.1-level039-whole-r01/candidate-f.json"]
    if a != b:
        raise ValueError("sealed Level39 twins differ")
    c = json.loads(a)
    if c != build_candidate(root):
        raise ValueError("sealed Level39 source differs from original TXT/PDF replay")
    source_map = json.loads(raw[MAP_REL])
    row = source_map["rows"][38]
    if (row.get("level") != 39 or row.get("section") != "V" or row.get("wbs_owner") != "2.3.1.1.1"
            or row.get("txt_sha256") != INPUTS[TXT[0]] or row.get("pdf_sha256") != INPUTS[PDF[0]]
            or row.get("conversion_status") != "converted_candidate_reference"
            or row.get("representative_item_id") != "fg:item:000006"
            or row.get("stable_ids_assigned") is not True or row.get("admitted") is not False):
        raise ValueError("frozen source map representative row drift")
    foundation = json.loads(raw["Content/controls/curriculum-v1/package.json"])
    registry = json.loads(raw["Content/controls/curriculum-v1/identity-registry.json"])
    generation = json.loads(raw["Content/controls/curriculum-v1/generation.json"])
    if len(foundation["records"]) != 659 or generation["records"] != 659:
        raise ValueError("current659 foundation drift")
    return c, row, foundation, registry, generation


def representative_boundary(foundation: dict, registry: dict) -> tuple[dict, dict]:
    selected = [r for r in foundation["records"] if r.get("legacy_level") == 39]
    if len(selected) != 1:
        raise ValueError("Level39 selected representative count drift")
    r = selected[0]
    if (r.get("id") != "fg:item:000006" or r.get("workbook_id") != "fg:workbook:000039"
            or r.get("module_id") != "fg:module:000006" or r.get("content_revision") != 3
            or r.get("status") != "converted_candidate" or r.get("runtime_eligible") is not False
            or r.get("lineage", {}).get("kind") != "revision"
            or r["lineage"].get("predecessor_revision") != 2
            or len(r.get("events", [])) != 8
            or [v.get("id") for v in r.get("variants", [])] != ["fg:variant:000038", "fg:variant:000039"]):
        raise ValueError("Level39 selected representative identity/lineage drift")
    ids = [r["workbook_id"], r["module_id"], r["id"]] + [v["id"] for v in r["variants"]]
    entities = {e["id"]: e for e in registry["entities"] if e.get("id") in ids}
    if (set(entities) != set(ids) or entities[r["module_id"]].get("parent") != r["workbook_id"]
            or entities[r["id"]].get("parent") != r["module_id"]
            or any(entities[v["id"]].get("parent") != r["id"] for v in r["variants"])):
        raise ValueError("Level39 representative registry relationship drift")
    entry = next((e for e in foundation["workbook_catalog"]["entries"] if e.get("workbook_id") == r["workbook_id"]), None)
    if (not entry or entry.get("whole_workbook_complete") is not False
            or entry.get("admitted") is not False or entry.get("imported") is not False
            or entry.get("runtime_eligible") is not False or entry.get("review") != "Pending"
            or entry.get("conversion_status") != "not_converted"):
        raise ValueError("Level39 whole-workbook catalog boundary drift")
    snapshot = {"item_id": r["id"], "module_id": r["module_id"], "workbook_id": r["workbook_id"],
                "variant_ids": [v["id"] for v in r["variants"]], "content_revision": r["content_revision"],
                "lineage": r["lineage"], "source_refs": r["source_refs"],
                "record_sha256": digest(encoded(r)), "selected_source_event_count": len(r["events"]),
                "read_only": True, "admission_implied": False}
    return r, snapshot


def degree_context(label: str) -> dict:
    if label not in ("1", "2", "3", "4", "5", "6", "b3", "b7"):
        raise ValueError(f"unsupported degree source label: {label}")
    return {"alteration": -1 if label.startswith("b") else 0,
            "ordinal": int(label.lstrip("b")), "source_label": label}


def degree_contexts(note: dict) -> dict:
    return {"A-major": degree_context(note["A_major_degree"]),
            "F#-minor": degree_context(note["F_sharp_minor_degree"])}


def validate_candidate(c: dict, selected: dict) -> None:
    if (c.get("schema") != "fathom.level039.detached-source-candidate.1"
            or c.get("wbs") != "2.3.1.1.1" or c.get("status") != "non_admitted"
            or c.get("admitted") is not False
            or any(c.get(k) is not None for k in ("canonical_id", "exercise_id", "onset_q", "duration_q", "fixed_bpm", "executable_audio_events"))):
        raise ValueError("Level39 source identity/admission/timing drift")
    if c.get("counts") != {**COUNTS, "total_written_sounding_tones": 462}:
        raise ValueError("7/462/module source count drift")
    if (c.get("shared_pitch_pool") != list(ROLES)
            or c.get("pitch_roles") != {n: {"A_major_degree": v[0], "F_sharp_minor_degree": v[1]} for n, v in ROLES.items()}
            or c.get("F_sharp_root_atlas") != [{"string": s, "fret": f} for s, f in F_ROOTS]):
        raise ValueError("dual-degree/root atlas source drift")
    if (len(c.get("source_presentation_differences", [])) != 24
            or [x["module"] for x in c["source_presentation_differences"]] != ["A"] * 5 + ["E"] * 10 + ["F"] + ["G"] * 8
            or [x["kind"] for x in c.get("source_guidance_variants", [])] != [
                "PDF_attack_weight_clarification", "PDF_partner_call_task",
                "PDF_quarter_and_swing_practice_guidance", "PDF_second_pass_final_note_two_beat_hold"]):
        raise ValueError("presentation difference/guidance variant drift")
    guidance = c.get("source_guidance", {})
    if (len(guidance.get("txt_full_lines", [])) != 520
            or len(guidance.get("pdf_full_extracted_pages", [])) != 12
            or len(c.get("mastery_gate_raw", [])) != 2
            or "7 of 8" not in c["mastery_gate_raw"][1]):
        raise ValueError("whole-source guidance/mastery coverage drift")
    modules = c.get("modules", {})
    if list(modules) != list(MODULE_KEYS.values()):
        raise ValueError("A-G module order drift")
    # Check the frozen schema1 degree_contexts object shape and its exact mapping for the selected P1 case.
    first = modules[MODULE_KEYS["A"]][0]["events"]
    if len(first) != 8 or any(degree_contexts(n) != e.get("degree_contexts") for n, e in zip(first, selected["events"], strict=True)):
        raise ValueError("frozen representative degree_contexts shape/parity drift")
    if any(set(e["degree_contexts"][k]) != {"alteration", "ordinal", "source_label"}
           for e in selected["events"] for k in ("A-major", "F#-minor")):
        raise ValueError("frozen degree_contexts object shape drift")
    raw_count = 0
    for letter, key in MODULE_KEYS.items():
        value = modules[key]
        units = value if isinstance(value, list) else [value]
        if len(units) != {"A": 5, "B": 5, "C": 6, "D": 1, "E": 5, "F": 1, "G": 8}[letter]:
            raise ValueError(f"{letter} source unit count drift")
        for unit in units:
            children = unit["cadences"] if letter == "E" else [unit]
            for child in children:
                checked = check_rows(child["raw_rows"], child["bars"], accent=letter == "D")
                if checked["events"] != child["events"]:
                    raise ValueError(f"{letter} printed row/note/TAB/finger/dual-degree drift")
                raw_count += len(child["events"])
                for note in child["events"]:
                    if (note["note"] not in ROLES or note["string"] not in OPEN
                            or (OPEN[note["string"]] + note["fret"]) % 12 != ROLES[note["note"]][2]
                            or degree_contexts(note)["A-major"]["source_label"] != note["A_major_degree"]
                            or degree_contexts(note)["F#-minor"]["source_label"] != note["F_sharp_minor_degree"]):
                        raise ValueError(f"{letter} pitch/context drift")
    if raw_count != 386:
        raise ValueError("386 printed source columns drift")
    if (modules[MODULE_KEYS["A"]][0].get("drone_contexts") != ["A", "F#"]
            or any(u.get("sounding_tones") != 16 or u.get("written_tones_per_context") != 8 for u in modules[MODULE_KEYS["A"]])
            or modules[MODULE_KEYS["D"]].get("A_accent_ordinals") != [2, 7, 12]
            or modules[MODULE_KEYS["D"]].get("F_sharp_accent_ordinals") != [1, 6, 11]
            or len(modules[MODULE_KEYS["D"]].get("pass_contexts", [])) != 4
            or modules[MODULE_KEYS["F"]].get("center_by_bar") != ["A", "A", "F#", "F#", "A", "A", "F#", "F#"]
            or [u.get("printed_answer") for u in modules[MODULE_KEYS["G"]]] != ["A-centered", "F#-centered"] * 4):
        raise ValueError("A/D/F/G source role/pass/answer drift")
    for unit in modules[MODULE_KEYS["C"]]:
        notes = unit["events"]
        half = len(notes) // 2
        if (notes[half - 1]["note"], notes[half - 1]["string"], notes[half - 1]["fret"]) != (
                notes[half]["note"], notes[half]["string"], notes[half]["fret"]):
            raise ValueError("C repeated high-root turn drift")


def event_fields(note: dict) -> dict:
    return {"event_id": None, "kind": "note", "spelling": note["note"],
            "string": STRING_NUMBER[note["string"]], "fret": note["fret"],
            "midi": OPEN[note["string"]] + note["fret"], "finger": note["finger"],
            "degree_contexts": degree_contexts(note), "attack": None, "tie_from": None,
            "onset_q": None, "duration_q": None, "pick": None, "accent": None,
            "performed": None}


def occurrences(unit: dict, contexts: list[str]) -> list[dict]:
    return [{"source_context": context, "source_note_ordinal": note["ordinal"],
             "source_note": note, "schema1_fields": event_fields(note)}
            for context in contexts for note in unit["events"]]


def project(c: dict, row: dict, foundation: dict, registry: dict) -> tuple[dict, dict]:
    selected, snapshot = representative_boundary(foundation, registry)
    validate_candidate(c, selected)
    records = []
    for letter, key in MODULE_KEYS.items():
        source = c["modules"][key]
        raw_units = source if isinstance(source, list) else [source]
        units = []
        for i, unit in enumerate(raw_units, 1):
            children = unit["cadences"] if letter == "E" else [unit]
            for j, child in enumerate(children, 1):
                contexts = child["drone_contexts"] if letter == "A" else child["pass_contexts"] if letter == "D" else [child.get("center", child.get("printed_answer", "source_line"))]
                tones = occurrences(child, contexts)
                units.append({"source_unit_number": i, "source_subunit_number": j if letter == "E" else None,
                              "source_unit": child, "source_parent": unit if letter == "E" else None,
                              "source_written_sounding_tones": len(tones),
                              "source_printed_note_columns": len(child["events"]),
                              "source_pdf_page": child["pdf_page"], "source_txt_ref": child["txt_ref"],
                              "event_field_proposals": tones, "variant_id": None,
                              "performed_passes_observed": None})
        if sum(u["source_written_sounding_tones"] for u in units) != COUNTS[letter]:
            raise ValueError(f"{letter} projected written source total drift")
        records.append({"source_component": letter, "source_module": source,
                        "identity_state": "unallocated_whole_source_extension",
                        "schema1_fields": {"id": None, "workbook_id": None, "module_id": None,
                                           "legacy_level": 39, "title": f"Level 39 module {letter}",
                                           "kind": "mixed", "content_revision": None, "lineage": None,
                                           "status": "unallocated_source_projection", "runtime_eligible": False,
                                           "admitted": False, "events": [], "variants": [],
                                           "timing": {"status": "unresolved", "unit": "quarter",
                                                      "fixed_bpm": None, "note_per_click": None},
                                           "mastery_observed": None},
                        "unit_field_proposals": units})
    proposal = {"proposal_version": "level039-unallocated-schema1-fields.1", "wbs_id": "2.3.1.1.1",
                "classification": "Build-only, nonimportable whole-source field proposal", "legacy_level": 39,
                "canonical_ids_allocated": False, "schema1_importable": False,
                "whole_workbook_complete": False, "runtime_eligible": False, "admitted": False,
                "performed_mastery_observed": None, "auditory_judgment_observed": None,
                "counts": {"provisional_components": 7, "source_printed_note_columns": 386,
                           "written_sounding_tone_occurrences": 462, "module_tones": COUNTS,
                           "extra_performed_passes_observed": None},
                "existing_selected_representative_read_only": snapshot,
                "source": c["source"], "shared_pitch_pool": c["shared_pitch_pool"],
                "pitch_roles": c["pitch_roles"], "F_sharp_root_atlas": c["F_sharp_root_atlas"],
                "source_guidance": c["source_guidance"],
                "source_presentation_differences": c["source_presentation_differences"],
                "source_guidance_variants": c["source_guidance_variants"],
                "printed_ear_answer_key": c["printed_ear_answer_key"],
                "mastery_gate_raw": c["mastery_gate_raw"],
                "unresolved": UNRESOLVED, "records": records}
    handoff = {"handoff_version": "level039-allocation-handoff.1", "wbs_id": "2.3.1.1.1",
               "source_map_representative_item_id_read_only": row["representative_item_id"],
               "existing_selected_representative_read_only": snapshot,
               "new_canonical_ids_allocated": False, "admitted": False,
               "written_sounding_tone_occurrences": 462,
               "required_decisions": ["Preserve selected P1 representative/revision lineage without overwrite.",
                                      "Review 24 presentation differences and four PDF/TXT guidance variants.",
                                      "Decide canonical partition/IDs for remaining whole workbook through P02.",
                                      "Authorize timing, audio/drone, accent, ear-test and mastery semantics before runtime/admission."]}
    return proposal, handoff


def products(root: Path) -> dict[str, object]:
    c, row, foundation, registry, _ = read_inputs(root)
    proposal, handoff = project(c, row, foundation, registry)
    manifest = {"manifest_version": "level039-schema1-input-pins.1", "inputs": [
        {"path": rel, "bytes": (root / rel).stat().st_size, "sha256": sha} for rel, sha in INPUTS.items()]}
    summary = {"summary_version": "level039-schema1-unallocated-summary.1",
               "proposal_sha256": digest(encoded(proposal)), "handoff_sha256": digest(encoded(handoff)),
               "source_printed_note_columns": 386, "written_sounding_tone_occurrences": 462,
               "selected_representative_preserved": True,
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
    print("LEVEL39 " + mode.upper() + " PASS modules=7 columns=386 written_tones=462 admitted=false")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("build", "verify"))
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    run(args.mode, args.root.resolve())


if __name__ == "__main__":
    main()
