#!/usr/bin/env python3
"""Project pinned whole-Level70 source tones into unallocated schema1 fields."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from parallel_07_level070_whole_candidate import build_candidate, OPEN, PC, DEGREE


ROOT = Path(__file__).resolve().parents[1]
OUT_REL = Path("Build/parallel-11/2.3.1.2.1-level070-schema1-unallocated-r01")
INPUTS = {
    "Tools/parallel_07_level070_whole_candidate.py": "11cef61c7d459e3200b71348189a5dd6a9960aaff92c1c460bae90a905334dd8",
    "Results/parallel-07/conversion/20260923T164107Z-2.3.1.2.1-level070-whole-candidate-r01-results.md": "3a152bb6f1f17ea57f7d973d07bf00fda06513a3e6f791d650b97f71e6a6872f",
    "Build/parallel-07/2.3.1.2.1-level070-whole-r01/level070_whole_candidate.json": "7b5f47d5384d9158b86eca292d5d4588efcd935029f6be395667402b9e8a5bd9",
    "Build/parallel-07/2.3.1.2.1-level070-whole-r01/manifest.json": "c4af8dd74613b38adee866fad39debd295d8facdc37a16b8df405599a7171b4e",
    "Tools/curriculum_level070_batch_adapter_candidate.py": "a15d72c583f6186611e558245b80172dca6ddfa40da80e8b8e115d09a2b1b9d5",
    "Build/parallel-06/2.3-level070-moduleefgh-adapter-r05/full-a.json": "83f41e1f39422d4e67cd985c2131ada7fc1e00ad0ce3d0858422381e5307e4c8",
    "Content/controls/curriculum-v1/package.json": "766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255",
    "Content/controls/curriculum-v1/identity-registry.json": "5d265859e1e8a5a530a0e53d88b019a1c920f3bba6cccb4ef0fef2f7640007e5",
    "Content/controls/curriculum-v1/generation.json": "fc6cec9f9d67eb82c97c5f4c3fb95d285178fb7fce7bd147d9ae0296d21b4c1c",
    "Notes/music/guitar project/TXT version/Guitar_Exercises_Section_IX_Level_70_A_Melodic_Minor_Five_Position_Map_Horizontal_Routes_Directional_Descents_Seam_Transitions_and_Full_Register_Movement.txt": "13ed1a46b87e74c3b3fb78161281268f79ed710b5bd7f12195378f3b247c4b9b",
    "Notes/music/guitar project/PDF version/Guitar_Exercises_Section_IX_Level_70_A_Melodic_Minor_Five_Position_Map_Horizontal_Routes_Directional_Descents_Seam_Transitions_and_Full_Register_Movement.pdf": "4b95c98c91c35f132954f2452104280f40d8e96b46ca431344e6b4de007c764f",
    "Results/parallel-01/exercises/inventory/20260922T180500Z-2.3-curriculum-v1-source-inventory-evidence/curriculum-source-map.json": "bad5581a04f43ba8baf14db430449e1ccff5cf88f0f7e42198328073b27053d6",
}
COUNTS = {"A": 180, "B": 168, "C": 94, "D": 88, "E": 180, "F": 60, "G": 64, "H": 64}
CELLS = {"A": 5, "B": 4, "C": 6, "D": 5, "E": 10, "F": 5, "G": 4, "H": 4}
P06_KEYS = {"A": "positions", **{letter: f"module_{letter.lower()}_blocks" for letter in "BCDEFGH"}}
STRINGS = {"E": 1, "A": 2, "D": 3, "G": 4, "B": 5, "e": 6}
UNRESOLVED = [
    "Canonical workbook/module/item/event/variant IDs and lineage are not allocated.",
    "Quarter-note onset/duration, fixed BPM, pick/accent/shift realization and performed pass count are unresolved.",
    "Module F prints both descents in each 12-tone cell, while PDF p16 instructs a performed choice; no choice is observed.",
    "Seam second passes, sequence translations and capstone repetitions are supplemental to 898 printed tones.",
    "Human mastery, native import and Curriculum admission are not established.",
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
    c = json.loads(raw["Build/parallel-07/2.3.1.2.1-level070-whole-r01/level070_whole_candidate.json"])
    if c != build_candidate(root):
        raise ValueError("P07 sealed candidate differs from original TXT/PDF/source-map replay")
    p06 = json.loads(raw["Build/parallel-06/2.3-level070-moduleefgh-adapter-r05/full-a.json"])
    foundation = json.loads(raw["Content/controls/curriculum-v1/package.json"])
    registry = json.loads(raw["Content/controls/curriculum-v1/identity-registry.json"])
    generation = json.loads(raw["Content/controls/curriculum-v1/generation.json"])
    if len(foundation["records"]) != 659 or generation["records"] != 659:
        raise ValueError("current659 foundation drift")
    return c, p06, foundation, registry


def identity_boundary(foundation: dict, registry: dict) -> dict:
    workbook = "fg:workbook:000070"
    if any(r.get("legacy_level") == 70 or r.get("workbook_id") == workbook for r in foundation["records"]):
        raise ValueError("unexpected canonical Level70 record")
    if any(e.get("id") == workbook for e in registry["entities"]):
        raise ValueError("unexpected Level70 registry entity")
    entry = next((e for e in foundation["workbook_catalog"]["entries"] if e.get("workbook_id") == workbook), None)
    if (not entry or entry.get("representative_item_id") is not None or entry.get("whole_workbook_complete") is not False
            or entry.get("admitted") is not False or entry.get("conversion_status") != "not_converted"):
        raise ValueError("Level70 source-only catalog drift")
    return entry


def source_events(letter: str, cell: dict) -> list[dict]:
    return [tone for lane in cell["lanes"] for tone in lane["events"]] if letter == "B" else cell["events"]


def validate_candidate(c: dict) -> None:
    if (c.get("schema") != "fathom.level70.whole.detached_candidate.v1" or c.get("wbs") != "2.3.1.2.1"
            or c.get("level") != 70 or c.get("status") != "candidate_only" or c.get("stable_ids") is not None
            or c.get("imported") is not False or c.get("admitted") is not False):
        raise ValueError("Level70 source identity/admission drift")
    if c["workload"]["module_tones"] != COUNTS or c["workload"]["total_sounding_tones"] != 898:
        raise ValueError("898-tone source workload drift")
    if any(c["workload"][k] is not False for k in (
        "supplemental_seam_second_pass_counted", "supplemental_sequence_translations_counted", "supplemental_capstone_repeat_counted")):
        raise ValueError("supplemental pass count drift")
    if c["workload"]["module_f_both_descent_forms_written_and_counted"] is not True:
        raise ValueError("F printed descent boundary drift")
    if list(c["modules"]) != list(COUNTS):
        raise ValueError("A–H module order drift")
    for letter, module in c["modules"].items():
        if len(module["cells"]) != CELLS[letter] or module["tone_count"] != COUNTS[letter]:
            raise ValueError(f"{letter} cell/count drift")
        if sum(len(source_events(letter, cell)) for cell in module["cells"]) != COUNTS[letter]:
            raise ValueError(f"{letter} printed event count drift")
        for cell in module["cells"]:
            if len(source_events(letter, cell)) != cell["tone_count"] or not 1 <= cell["pdf_page"] <= 20:
                raise ValueError(f"{letter} cell/source page drift")
            expected_parity = "degree_finger_tab_without_note_row" if letter in "BE" else "exact_row_parity"
            if cell["pdf_grid_status"] != expected_parity:
                raise ValueError(f"{letter} PDF parity classification drift")
            for tone in source_events(letter, cell):
                if (tone["note"] not in PC or tone["string"] not in OPEN or not isinstance(tone["fret"], int)
                        or (OPEN[tone["string"]] + tone["fret"]) % 12 != PC[tone["note"]]
                        or tone["degree"] != DEGREE[tone["note"]] or tone["sounded"] is not True
                        or tone["onset_q"] is not None or tone["duration_q"] is not None):
                    raise ValueError(f"{letter} source note/TAB/timing drift")
    if len(c["source_transcription"]["txt_lines"]) != 533 or len(c["source_transcription"]["pdf_pages"]) != 20:
        raise ValueError("whole-source transcription drift")
    if len(c["source_ambiguities"]) != 1 or "choose one of two descending forms" not in c["source_ambiguities"][0]:
        raise ValueError("F descent source tension lost")
    if len(c["mastery"]["txt_lines"]) != 33 or c["mastery"]["pdf_page"] != 20:
        raise ValueError("mastery guidance drift")
    if len(c["count_boundaries"]) != 3 or len(c["pdf_only_directions"]) != 10:
        raise ValueError("supplemental/PDF directions drift")
    for cell in c["modules"]["F"]["cells"]:
        if [tone["form"] for tone in cell["events"]] != ["ASC"] * 4 + ["SYM"] * 4 + ["CLS"] * 4:
            raise ValueError("F ASC/SYM/CLS structure drift")
    if any(cell["repeat_counted_in_printed_898"] is not False for cell in c["modules"]["B"]["cells"]):
        raise ValueError("seam repeat boundary drift")


def validate_p06_parity(c: dict, p06: dict) -> None:
    if (p06.get("admitted") is not False or p06.get("canonical_package") is not False
            or p06.get("runtime_eligible") is not False or p06["counts"]["source_tones"] != 898):
        raise ValueError("P06 adapter status/count drift")
    for letter, key in P06_KEYS.items():
        source = [tone for cell in c["modules"][letter]["cells"] for tone in source_events(letter, cell)]
        projected = [tone for block in p06[key] for tone in block["record_projection"]["events"]]
        if len(source) != len(projected) or len(p06[key]) != CELLS[letter]:
            raise ValueError(f"P06 {letter} cardinality parity drift")
        for ordinal, (a, b) in enumerate(zip(source, projected, strict=True), 1):
            if (a["note"], STRINGS[a["string"]], a["fret"], OPEN[a["string"]] + a["fret"]) != (
                    b["spelling"], b["string"], b["fret"], b["midi"]):
                raise ValueError(f"P06 {letter} note/string/fret/midi parity drift at {ordinal}")


def _event(letter: str, cell_no: int, local_ordinal: int, cell: dict, tone: dict) -> dict:
    finger = tone.get("finger")
    return {
        "source_component": letter, "source_unit_number": cell_no, "source_local_ordinal": local_ordinal,
        "source_txt_ref": cell["source_ref"], "source_pdf_page": cell["pdf_page"],
        "source_pdf_grid_status": cell["pdf_grid_status"], "source_tone": tone,
        "schema1_fields": {
            "event_id": None, "kind": "note", "spelling": tone["note"], "string": STRINGS[tone["string"]],
            "fret": tone["fret"], "midi": OPEN[tone["string"]] + tone["fret"],
            "finger": int(finger) if finger is not None else None, "attack": None,
            "degree_contexts": {}, "tie_from": None, "onset_q": None, "duration_q": None,
            "pick": None, "accent": None, "performed": None,
        },
    }


def project(c: dict, p06: dict, foundation: dict, registry: dict) -> tuple[dict, dict]:
    validate_candidate(c)
    validate_p06_parity(c, p06)
    entry = identity_boundary(foundation, registry)
    records = []
    for letter, module in c["modules"].items():
        events = []
        variants = []
        for cell_no, cell in enumerate(module["cells"], 1):
            start = len(events) + 1
            for tone in source_events(letter, cell):
                events.append(_event(letter, cell_no, len(events) + 1, cell, tone))
            variants.append({"id": None, "source_unit_number": cell_no, "source_cell": cell,
                             "source_event_ordinals": list(range(start, len(events) + 1)),
                             "event_ids": None, "runtime_eligible": False,
                             "performed_pass_count": None})
        records.append({
            "source_component": letter, "source_heading": module["title"],
            "source_txt_ref": module["source_ref"], "source_raw_lines": module["raw_lines"],
            "identity_state": "unallocated",
            "schema1_fields": {
                "id": None, "workbook_id": None, "module_id": None, "legacy_level": 70,
                "title": f"Level 70 component {letter}: {module['title']}", "kind": "mixed",
                "content_revision": None, "lineage": None, "status": "unallocated_source_projection",
                "runtime_eligible": False, "admitted": False,
                "source_refs": [module["source_ref"]] + [f"L70-PDF-p{cell['pdf_page']}" for cell in module["cells"]],
                "events": events, "variants": variants, "resource_requirements": [],
                "timing": {"status": "unresolved", "unit": "quarter", "fixed_bpm": None},
                "ambiguities": UNRESOLVED,
            },
        })
    proposal = {
        "proposal_version": "level070-unallocated-schema1-fields.1", "wbs_id": "2.3.1.2.1",
        "classification": "Build-only, nonimportable schema1 field proposal", "legacy_level": 70,
        "canonical_ids_allocated": False, "schema1_importable": False,
        "whole_workbook_complete": False, "runtime_eligible": False, "admitted": False,
        "mastery_observed": None,
        "counts": {"provisional_components": 8, "source_cells": 43, "printed_sounding_tones": 898,
                   "module_tones": COUNTS, "supplemental_performed_tones": None},
        "source": c["source"], "scale": c["scale"], "workload": c["workload"],
        "pdf_only_directions": c["pdf_only_directions"], "mastery": c["mastery"],
        "count_boundaries": c["count_boundaries"], "source_ambiguities": c["source_ambiguities"],
        "source_transcription": c["source_transcription"], "timing_boundary": c["timing_boundary"],
        "p06_read_only_parity": {"source_tones": 898, "ordered_note_string_fret_midi_matches": 898,
                                 "adapter_path": "Build/parallel-06/2.3-level070-moduleefgh-adapter-r05/full-a.json"},
        "records": records,
    }
    handoff = {
        "handoff_version": "level070-allocation-handoff.1", "wbs_id": "2.3.1.2.1",
        "catalog_workbook_id_read_only": entry["workbook_id"], "existing_level070_records": 0,
        "existing_level070_workbook_entities": 0, "printed_sounding_tones": 898,
        "proposed_component_partition": list(COUNTS), "canonical_ids_allocated": False, "admitted": False,
        "required_decisions": [
            "Review whole-source coverage and Module F printed-both versus performed-choice distinction.",
            "Allocate stable identities, variants and lineage only through the canonical owner.",
            "Authorize note timing, pick/accent/shift and performed supplemental passes before native import.",
            "Review mastery and expected-profile evidence before Curriculum admission.",
        ],
    }
    return proposal, handoff


def products(root: Path) -> dict[str, object]:
    c, p06, foundation, registry = read_inputs(root)
    proposal, handoff = project(c, p06, foundation, registry)
    manifest = {"manifest_version": "level070-schema1-input-pins.1", "inputs": [
        {"path": rel, "bytes": (root / rel).stat().st_size, "sha256": sha} for rel, sha in INPUTS.items()]}
    summary = {"summary_version": "level070-schema1-unallocated-summary.1",
               "proposal_sha256": digest(encoded(proposal)), "handoff_sha256": digest(encoded(handoff)),
               "printed_sounding_tones": 898, "source_cells": 43, "p06_ordered_contact_parity": 898,
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
    print(f"LEVEL70 {mode.upper()} PASS source_tones=898 cells=43 p06_parity=898 admitted=false")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("build", "verify"))
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    run(args.mode, args.root.resolve())


if __name__ == "__main__":
    main()
