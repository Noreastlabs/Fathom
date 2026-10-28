#!/usr/bin/env python3
"""Build source-bound, unallocated Level50 schema1 attack fields."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from curriculum_level050_whole_candidate import COUNTS, ITEM_COUNTS, build_candidate


ROOT = Path(__file__).resolve().parents[1]
OUT_REL = Path("Build/parallel-10/level050-schema1-unallocated-r01")
INPUTS = {
    "Tools/curriculum_level050_whole_candidate.py": "48d919eb7861025a3d03dd0e6ae371414d166cd31d3cfe6f6de8617897bd9009",
    "Results/parallel-11/curriculum/20260923T155500Z-2.3-level050-whole-r01-results.md": "3724a15e4cd6f019bde793e37d2526eb2db63283722a680c9965d4a4bbec34b4",
    "Build/parallel-11/2.3.1.2.1-level050-whole-r01/candidate-g.json": "1b6947df37e8b2269adade149b5ce7d8794b284ef9332a65805214b51eb84660",
    "Content/controls/curriculum-v1/package.json": "766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255",
    "Content/controls/curriculum-v1/identity-registry.json": "5d265859e1e8a5a530a0e53d88b019a1c920f3bba6cccb4ef0fef2f7640007e5",
    "Content/controls/curriculum-v1/generation.json": "fc6cec9f9d67eb82c97c5f4c3fb95d285178fb7fce7bd147d9ae0296d21b4c1c",
    "Notes/music/guitar project/TXT version/Guitar_Exercises_Section_VI_Level_50_Chord_Transitions_Common_Finger_and_Guide_Finger_Movement_Anticipated_Changes_and_Uninterrupted_Progressions.txt": "c2a1e88fdc69545f17f7439b109fdad6a4b652285704ea730d0b8dae89a4306e",
    "Notes/music/guitar project/PDF version/Guitar_Exercises_Section_VI_Level_50_Chord_Transitions_Common_Finger_and_Guide_Finger_Movement_Anticipated_Changes_and_Uninterrupted_Progressions.pdf": "eec11800419be73416833d09a0bd46b42785cc050afc716b44d3b0129d0e2afc",
    "Results/parallel-01/exercises/inventory/20260922T180500Z-2.3-curriculum-v1-source-inventory-evidence/curriculum-source-map.json": "bad5581a04f43ba8baf14db430449e1ccff5cf88f0f7e42198328073b27053d6",
}
UNRESOLVED = [
    "canonical workbook/module/item/event/variant IDs and lineage",
    "performed chord voicing and H4 bass MIDI",
    "quarter-note onset/duration, fixed starting BPM and note-per-click",
    "optional F repeat, E pass alternatives and PDF-only test/mastery interpretation",
]


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def encoded(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")


def pinned(root: Path, rel: str, sha: str) -> bytes:
    raw = (root / rel).read_bytes()
    if digest(raw) != sha:
        raise ValueError(f"input drift: {rel}")
    return raw


def read_inputs(root: Path) -> tuple[dict, dict, dict]:
    raw = {rel: pinned(root, rel, sha) for rel, sha in INPUTS.items()}
    candidate = json.loads(raw["Build/parallel-11/2.3.1.2.1-level050-whole-r01/candidate-g.json"])
    if candidate != build_candidate(root):
        raise ValueError("P11 Level50 candidate differs from original TXT/PDF replay")
    foundation = json.loads(raw["Content/controls/curriculum-v1/package.json"])
    registry = json.loads(raw["Content/controls/curriculum-v1/identity-registry.json"])
    generation = json.loads(raw["Content/controls/curriculum-v1/generation.json"])
    if len(foundation["records"]) != 659 or generation["records"] != 659:
        raise ValueError("current659 foundation drift")
    return candidate, foundation, registry


def identity_boundary(foundation: dict, registry: dict) -> dict:
    if any(r.get("legacy_level") == 50 or r.get("workbook_id") == "fg:workbook:000050" for r in foundation["records"]):
        raise ValueError("unexpected canonical Level50 record")
    if any(e.get("id") == "fg:workbook:000050" for e in registry["entities"]):
        raise ValueError("unexpected Level50 registry entity")
    entry = next((x for x in foundation["workbook_catalog"]["entries"] if x.get("workbook_id") == "fg:workbook:000050"), None)
    if not entry or entry.get("representative_item_id") is not None or entry.get("whole_workbook_complete") is not False or entry.get("admitted") is not False or entry.get("conversion_status") != "not_converted":
        raise ValueError("Level50 source-only catalog drift")
    return entry


def _forms(symbol: str, references: dict) -> list[str]:
    if symbol == "MUTE":
        return []
    if symbol not in references["standard"]:
        raise ValueError(f"unknown printed chord symbol: {symbol}")
    forms = [symbol]
    if symbol + "-alt" in references["alternate"]:
        forms.append(symbol + "-alt")
    return forms


def _event(module: str, item: dict, unit_index: int, ordinal: int, symbol: str | None, attack: str | None,
           txt_ref: str, pdf_page: int, references: dict) -> dict:
    if symbol is not None and symbol != "MUTE":
        forms = _forms(symbol, references)
    else:
        forms = []
    if attack not in ("D", "U", "x", "B", None):
        raise ValueError("unsupported source attack symbol")
    contact = "muted" if attack == "x" or symbol == "MUTE" else "pitched" if attack in ("D", "U", "B") else None
    return {"source_local_ordinal": ordinal, "source_module": module, "source_unit_number": unit_index,
            "source_unit_label": item.get("title", item.get("name")), "source_txt_ref": txt_ref,
            "source_pdf_page": pdf_page, "printed_attack_symbol": attack,
            "printed_chord_symbol": symbol, "candidate_source_forms": forms,
            "resolved_fingering": None, "sounding_member_pitches": None,
            "bass_note_midi": None,
            "schema1_fields": {"event_id": None, "kind": "contact", "contact": contact,
                               "pick": attack if attack in ("D", "U") else None,
                               "pitch_binding": None, "onset_q": None, "duration_q": None}}


def _unit_events(module: str, item: dict, unit_index: int, references: dict, default_page: int) -> list[dict]:
    page = item.get("pdf_page", default_page)
    ref = item["txt_ref"]
    if module == "H":
        symbols = item["attack_symbols_per_bar"] * 4
        chords = [chord for chord in item["four_bar_progression"] for _ in range(4)]
    elif module == "J":
        symbols = [None] * 64  # J's Chd rows print chord slots; pass alternatives do not fix a single stroke sequence.
        chords = [chord for system in item["systems"] for chord in system["chord_symbols"]]
    else:
        symbols = item["attack_symbols"]
        chords = item["chord_symbols"]
    if len(symbols) != item["printed_attacks"] or len(chords) != item["printed_attacks"]:
        raise ValueError(f"{module} source attack/chord count drift")
    if module == "H" and item["name"] == "H4" and symbols != ["B", "D", "B", "D"] * 4:
        raise ValueError("H4 bass/chord source pattern drift")
    if module == "F" and item.get("optional_repeat_raw") != "One two-bar burst, full relaxation, then repeat.":
        raise ValueError("F optional-repeat source instruction drift")
    return [_event(module, item, unit_index, i, chord, attack, ref, page, references)
            for i, (chord, attack) in enumerate(zip(chords, symbols), 1)]


def project(candidate: dict, foundation: dict, registry: dict) -> tuple[dict, dict]:
    boundary = identity_boundary(foundation, registry)
    if candidate.get("schema") != "fathom.level050.detached-source-candidate.1" or candidate.get("wbs") != "2.3.1.2.1" or candidate.get("status") != "non_admitted":
        raise ValueError("Level50 source candidate scope drift")
    if candidate.get("admitted") is not False or any(candidate.get(k) is not None for k in (
        "canonical_id", "exercise_id", "onset_q", "duration_q", "fixed_bpm", "audible_voicing_events",
        "bass_note_midi_for_H4", "optional_repeat_attack_count")):
        raise ValueError("source candidate invented identity/performance")
    if candidate.get("silent_landings") != 80 or candidate.get("notated_attack_total") != 768 or candidate.get("notated_attacks_by_module") != {k: COUNTS[k] for k in "BCDEFGHIJ"}:
        raise ValueError("80/768 source workload drift")
    if list(candidate["modules"]) != list(COUNTS) or any(len(candidate["modules"][k]) != ITEM_COUNTS[k] for k in COUNTS):
        raise ValueError("module/unit order drift")
    refs = candidate["chord_reference"]
    if set(refs) != {"standard", "alternate"} or set(refs["alternate"]) != {"E-alt", "Em-alt"} or len(refs["standard"]) != 8:
        raise ValueError("source chord forms drift")
    if any("midi" in str(key).lower() for group in refs.values() for shape in group.values() for key in shape):
        raise ValueError("invented chord MIDI in source forms")
    differences = candidate["source_differences"]
    required = {"alternate_fingering_header_vs_symbol_grid", "PDF_only_E_pass_1_confirmation", "PDF_only_clean_transition_tests", "PDF_only_completion_audit_and_log"}
    if not required.issubset({d["kind"] for d in differences}):
        raise ValueError("source-specific differences lost")
    records = []
    total_attacks = 0
    for module, units in candidate["modules"].items():
        section = candidate["module_sections"][module]
        pages = section["pdf_pages"]
        if not pages or any(p < 1 or p > 20 for p in pages):
            raise ValueError("source PDF page drift")
        if module == "A":
            if len(units) != 10 or sum(u["silent_landings"] for u in units) != 80 or any(u["silent_landings"] != 8 for u in units):
                raise ValueError("silent-landing count drift")
            silent_tasks = [{"source_transition": u["transition"], "motion": u["motion"], "silent_landings": u["silent_landings"],
                             "source_txt_ref": u["txt_ref"], "source_pdf_pages": pages, "audible_events": []} for u in units]
            events = []
            variants = []
        else:
            silent_tasks = []
            events = []
            variants = []
            for unit_index, item in enumerate(units, 1):
                if item.get("printed_attacks") is None:
                    raise ValueError("missing printed attack count")
                generated = _unit_events(module, item, unit_index, refs, pages[0])
                if item.get("pdf_page", pages[0]) not in pages:
                    raise ValueError("unit PDF page outside section")
                if module == "J" and any(len(system["chord_symbols"]) != 16 or system["printed_attacks"] != 16 for system in item["systems"]):
                    raise ValueError("J system drift")
                start = len(events) + 1
                events.extend(generated)
                variants.append({"id": None, "source_unit_number": unit_index,
                                 "label": item.get("title", item.get("name")), "source_txt_ref": item["txt_ref"],
                                 "source_pdf_page": item.get("pdf_page", pages[0]),
                                 "source_event_ordinals": list(range(start, len(events) + 1)),
                                 "event_ids": None, "runtime_eligible": False})
            if len(events) != COUNTS[module]:
                raise ValueError(f"{module} notated attack count drift")
            total_attacks += len(events)
        records.append({"source_component": module, "source_heading": section["heading"],
                        "source_txt_ref": section["txt_ref"], "source_pdf_pages": pages,
                        "identity_state": "unallocated", "silent_landing_tasks": silent_tasks,
                        "schema1_fields": {"id": None, "workbook_id": None, "module_id": None, "legacy_level": 50,
                            "title": f"Level 50 component {module}", "kind": "mixed", "content_revision": None,
                            "lineage": None, "runtime_eligible": False, "source_refs": None,
                            "events": events, "variants": variants, "resource_requirements": [],
                            "timing": {"status": "unresolved", "unit": "quarter", "fixed_bpm": None,
                                       "basis": "Printed windows and relative advancement do not supply performed timing."},
                            "ambiguities": UNRESOLVED}})
    if total_attacks != 768 or sum(len(r["silent_landing_tasks"]) for r in records) != 10:
        raise ValueError("whole-Level50 projection totals drift")
    h4 = records[7]["schema1_fields"]["events"][-16:]
    if [e["printed_attack_symbol"] for e in h4] != ["B", "D", "B", "D"] * 4 or any(e["bass_note_midi"] is not None for e in h4):
        raise ValueError("H4 bass authority drift")
    proposal = {"proposal_version": "level050-unallocated-schema1-fields.1", "wbs_id": "2.3.1.2.1", "legacy_level": 50,
                "classification": "Build-only, nonimportable schema1 field proposal", "canonical_ids_allocated": False,
                "schema1_importable": False, "whole_workbook_complete": False, "runtime_eligible": False,
                "admitted": False, "counts": {"components": 10, "source_units": 62, "silent_landings": 80,
                                              "notated_attacks": 768, "chord_forms": 10},
                "source": candidate["source"], "chord_reference": refs, "source_differences": differences,
                "guidance": candidate["guidance"], "records": records}
    handoff = {"handoff_version": "level050-allocation-handoff.1", "wbs_id": "2.3.1.2.1",
               "catalog_workbook_id": boundary["workbook_id"], "catalog_role": boundary["catalog_role"],
               "existing_level050_records": 0, "existing_level050_workbook_entities": 0,
               "silent_landings_not_events": 80, "notated_attacks": 768,
               "proposed_component_partition": list(COUNTS), "canonical_ids_allocated": False,
               "required_decisions": ["Allocate workbook/module/item/event/variant identities after current reservations are sealed.",
                 "Review alternate fingering selection, H4 bass pitch, E pass choices, F repeat and PDF-only tests.",
                 "Approve source-specific timing and audible voicings before any native import or runtime admission."],
               "admitted": False}
    return proposal, handoff


def products(root: Path) -> dict[str, object]:
    candidate, foundation, registry = read_inputs(root)
    proposal, handoff = project(candidate, foundation, registry)
    manifest = {"manifest_version": "level050-input-pins.1", "inputs": [
        {"path": rel, "bytes": (root / rel).stat().st_size, "sha256": sha} for rel, sha in INPUTS.items()]}
    summary = {"summary_version": "level050-schema1-unallocated-summary.1",
               "proposal_sha256": digest(encoded(proposal)), "handoff_sha256": digest(encoded(handoff)),
               "components": 10, "silent_landings": 80, "notated_attacks": 768,
               "native_run": False, "admitted": False, "runtime_eligible": False}
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
    print(f"LEVEL50 {mode.upper()} PASS components=10 landings=80 attacks=768 admitted=false")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("build", "verify"))
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    run(args.mode, args.root.resolve())


if __name__ == "__main__":
    main()
