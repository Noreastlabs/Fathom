#!/usr/bin/env python3
"""Build source-bound, unallocated whole-Level56 schema1 attack fields."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from curriculum_level056_whole_candidate import build_candidate


ROOT = Path(__file__).resolve().parents[1]
OUT_REL = Path("Build/parallel-10/level056-schema1-unallocated-r01")
INPUTS = {
    "Tools/curriculum_level056_whole_candidate.py": "3a328b6be5cc5f2318098dae7c72ad3b9880983efc314f4810a29e883b47e2ea",
    "Results/parallel-11/curriculum/20260923T161100Z-2.3-level056-whole-r01-results.md": "fcc58cf0d8400e999e64607a0b675548a270af45ae3a9f6acb6ce01c4837f4fb",
    "Build/parallel-11/2.3.1.2.1-level056-whole-r01/candidate-c.json": "01833c3c2ed37afcf8da30ecd13becddbdfde52fd98f62c6a5454548b5f0bb7b",
    "Content/controls/curriculum-v1/package.json": "766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255",
    "Content/controls/curriculum-v1/identity-registry.json": "5d265859e1e8a5a530a0e53d88b019a1c920f3bba6cccb4ef0fef2f7640007e5",
    "Content/controls/curriculum-v1/generation.json": "fc6cec9f9d67eb82c97c5f4c3fb95d285178fb7fce7bd147d9ae0296d21b4c1c",
    "Notes/music/guitar project/TXT version/Guitar_Exercises_Section_VI_Level_56_Natural_Minor_Harmony_Minor_Key_Progressions_and_Raised_Seventh_Dominant_Preparation.txt": "77c6cf5aa49b3e078f93990b4350abda7dbff38b73b23736df1e5f6df2a729f9",
    "Notes/music/guitar project/PDF version/Guitar_Exercises_Section_VI_Level_56_Natural_Minor_Harmony_Minor_Key_Progressions_and_Raised_Seventh_Dominant_Preparation.pdf": "4cf52fd867a32b9c267de5041ef0c34219cd9563495bb0634c7301affcc69564",
    "Results/parallel-01/exercises/inventory/20260922T180500Z-2.3-curriculum-v1-source-inventory-evidence/curriculum-source-map.json": "bad5581a04f43ba8baf14db430449e1ccff5cf88f0f7e42198328073b27053d6",
}
ATTACK_COUNTS = {"B": 168, "C": 96, "D": 96, "E": 96, "F": 96, "G": 96, "H": 96, "I": 96, "K": 96}
UNRESOLVED = ["canonical workbook/module/item/event/variant IDs and lineage",
              "performed full-chord voicing, member pitches and pick direction",
              "quarter-note onset/duration and fixed BPM",
              "Curriculum resolution of four VI function-label conflicts and human mastery"]


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def encoded(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def pinned(root: Path, rel: str, sha: str) -> bytes:
    raw = (root / rel).read_bytes()
    if digest(raw) != sha:
        raise ValueError(f"input drift: {rel}")
    return raw


def read_inputs(root: Path) -> tuple[dict, dict, dict]:
    raw = {rel: pinned(root, rel, sha) for rel, sha in INPUTS.items()}
    candidate = json.loads(raw["Build/parallel-11/2.3.1.2.1-level056-whole-r01/candidate-c.json"])
    if candidate != json.loads(json.dumps(build_candidate(root))):
        raise ValueError("P11 Level56 candidate differs from original TXT/PDF/map replay")
    foundation = json.loads(raw["Content/controls/curriculum-v1/package.json"])
    registry = json.loads(raw["Content/controls/curriculum-v1/identity-registry.json"])
    generation = json.loads(raw["Content/controls/curriculum-v1/generation.json"])
    if len(foundation["records"]) != 659 or generation["records"] != 659:
        raise ValueError("current659 foundation drift")
    return candidate, foundation, registry


def identity_boundary(foundation: dict, registry: dict) -> dict:
    workbook = "fg:workbook:000056"
    if any(r.get("legacy_level") == 56 or r.get("workbook_id") == workbook for r in foundation["records"]):
        raise ValueError("unexpected canonical Level56 record")
    if any(e.get("id") == workbook for e in registry["entities"]):
        raise ValueError("unexpected Level56 registry entity")
    entry = next((x for x in foundation["workbook_catalog"]["entries"] if x.get("workbook_id") == workbook), None)
    if (not entry or entry.get("representative_item_id") is not None or entry.get("whole_workbook_complete") is not False
        or entry.get("admitted") is not False or entry.get("conversion_status") != "not_converted"):
        raise ValueError("Level56 source-only catalog drift")
    return entry


def _event(module: str, unit_number: int, source_ref: str, pdf_page: int,
           key: str, chord: str, roman: str | None, function: str | None,
           attack_type: str, voicing_source: object, source_tone: dict | None = None,
           bar_number: int | None = None) -> dict:
    if attack_type not in ("blocked_triad", "individual_voice", "rhythm_chord"):
        raise ValueError("unmapped printed attack type")
    return {"source_module": module, "source_unit_number": unit_number, "source_local_ordinal": None,
            "source_txt_ref": source_ref, "source_pdf_page": pdf_page, "source_key": key,
            "source_bar_number": bar_number, "printed_chord_symbol": chord,
            "printed_roman": roman, "printed_function": function,
            "printed_attack_type": attack_type, "voicing_source": voicing_source,
            "source_tone": source_tone, "performed_member_pitches": None,
            "schema1_fields": {"event_id": None, "kind": "contact", "contact": "pitched", "pick": None,
                               "pitch_binding": None, "onset_q": None, "duration_q": None}}


def _project_b(families: list[dict]) -> list[tuple[dict, list[dict]]]:
    result = []
    if len(families) != 6:
        raise ValueError("B six-key family drift")
    for unit_number, family in enumerate(families, 1):
        if len(family["triads"]) != 7 or family["printed_attacks"] != 28:
            raise ValueError("B triad/attack count drift")
        strings = family["triad_string_set"].split("-")
        if len(strings) != 3:
            raise ValueError("B triad string set drift")
        events = []
        for triad in family["triads"]:
            frets = triad["frets_low_middle_high"]
            pcs = triad["pitch_classes_low_middle_high"]
            if len(frets) != 3 or len(pcs) != 3:
                raise ValueError("B triad contact drift")
            common = ("B", unit_number, family["txt_ref"], family["pdf_page"], family["key"], triad["chord"], triad["roman"], triad["function_raw"])
            events.append(_event(*common, "blocked_triad", {"triad": triad, "rhythm_voicings_raw": family["rhythm_voicings_raw"]}, bar_number=None))
            for string, fret, pc in zip(strings, frets, pcs):
                tone = {"string": string, "printed_fret": fret, "printed_pitch_class": pc, "sounding_midi": None}
                events.append(_event(*common, "individual_voice", {"triad": triad}, source_tone=tone))
        result.append((family, events))
    return result


def _project_progressions(module: str, cells: list[dict]) -> list[tuple[dict, list[dict]]]:
    if len(cells) != 6:
        raise ValueError(f"{module} six progression cells drift")
    result = []
    for unit_number, cell in enumerate(cells, 1):
        if (cell["printed_attacks"] != 16 or cell["printed_bars"] != 4 or cell["printed_attacks_per_bar"] != 4
            or any(len(cell[k]) != 4 for k in ("chord_symbols", "roman_symbols", "function_symbols", "voicing_alternatives_raw"))):
            raise ValueError(f"{module} printed bar/attack count drift")
        events = []
        for bar, (chord, roman, function, voicing) in enumerate(zip(
            cell["chord_symbols"], cell["roman_symbols"], cell["function_symbols"], cell["voicing_alternatives_raw"]), 1):
            for _ in range(4):
                events.append(_event(module, unit_number, cell["txt_ref"], cell["pdf_page"], cell["key"],
                    chord, roman, function, "rhythm_chord", voicing, bar_number=bar))
        result.append((cell, events))
    return result


def _project_i(cells: list[dict]) -> list[tuple[dict, list[dict]]]:
    if len(cells) != 6:
        raise ValueError("I six route cells drift")
    result = []
    for unit_number, cell in enumerate(cells, 1):
        strings = cell["string_set"].split("-")
        if cell["printed_attacks"] != 16 or len(strings) != 3 or any(len(cell[k]) != 4 for k in ("chord_symbols", "inversions", "fret_triplets")):
            raise ValueError("I chord/voice count drift")
        events = []
        for bar, (chord, inversion, frets) in enumerate(zip(cell["chord_symbols"], cell["inversions"], cell["fret_triplets"]), 1):
            notes = [int(f) for f in frets.split("-")]
            if len(notes) != 3 or [row[bar - 1] for row in cell["low_middle_high_fret_sequences"]] != notes:
                raise ValueError("I printed voice/fret route drift")
            source = {"inversion": inversion, "fret_triplet": frets, "raised_seventh": cell["raised_seventh"]}
            events.append(_event("I", unit_number, cell["txt_ref"], cell["pdf_page"], cell["key"], chord, None, None,
                                 "blocked_triad", source, bar_number=bar))
            for string, fret in zip(strings, notes):
                events.append(_event("I", unit_number, cell["txt_ref"], cell["pdf_page"], cell["key"], chord, None, None,
                    "individual_voice", source, source_tone={"string": string, "printed_fret": fret, "sounding_midi": None}, bar_number=bar))
        result.append((cell, events))
    return result


def _project_k(capstone: dict) -> list[tuple[dict, list[dict]]]:
    cells = capstone["cells"]
    if len(cells) != 6 or capstone["printed_bars"] != 24 or capstone["printed_attacks"] != 96:
        raise ValueError("K capstone count drift")
    result = []
    for unit_number, cell in enumerate(cells, 1):
        if cell["printed_attacks"] != 16 or any(len(cell[k]) != 4 for k in ("bars", "chord_symbols", "roman_symbols", "function_symbols")):
            raise ValueError("K cell attack count drift")
        events = []
        for bar, chord, roman, function in zip(cell["bars"], cell["chord_symbols"], cell["roman_symbols"], cell["function_symbols"]):
            for _ in range(4):
                events.append(_event("K", unit_number, cell["txt_ref"], cell["pdf_page"], cell["key"], chord, roman,
                    function, "rhythm_chord", cell["voicing_alternatives_raw"], bar_number=bar))
        result.append((cell, events))
    return result


def project(candidate: dict, foundation: dict, registry: dict) -> tuple[dict, dict]:
    entry = identity_boundary(foundation, registry)
    if candidate.get("schema") != "fathom.level056.detached-source-candidate.1" or candidate.get("wbs") != "2.3.1.2.1" or candidate.get("status") != "non_admitted":
        raise ValueError("Level56 source candidate scope drift")
    if candidate.get("admitted") is not False or any(candidate.get(k) is not None for k in (
        "canonical_id", "exercise_id", "onset_q", "duration_q", "fixed_bpm", "executable_events",
        "unique_full_chord_voicings", "optional_pass_attack_count")):
        raise ValueError("source candidate invented identity/performance")
    if candidate.get("sounded_attack_total") != 936 or candidate.get("silent_spelling_prompts") != 42 or candidate.get("written_prompts") != 24 or candidate.get("sounded_attacks_by_module") != ATTACK_COUNTS:
        raise ValueError("936/42/24 source workload drift")
    conflicts = candidate["source_conflicts"]
    if (len(conflicts) != 4 or [c["analysis_number"] for c in conflicts] != [4, 5, 9, 10]
        or any(c["roman"] != "VI" or c["progression_label"] != "P/T" or c["analysis_label"] != "P"
               or c["status"] != "pending_curriculum_review" for c in conflicts)):
        raise ValueError("VI source function conflicts lost or normalized")
    if candidate["modules"]["A"]["silent_spelling_prompts"] != 42 or len(candidate["modules"]["A"]["silent_spelling_items"]) != 42:
        raise ValueError("A silent spelling drift")
    j = candidate["modules"]["J"]
    if j["written_prompt_count"] != 24 or len(j["analysis"]) != 12 or len(j["transpose"]) != 12:
        raise ValueError("J written prompt drift")
    if any(j["analysis"][n - 1]["answer_functions_raw"][2] != "P" for n in (4, 5, 9, 10)):
        raise ValueError("J VI answer function drift")
    modules = candidate["modules"]
    if list(modules) != list("ABCDEFGHIJK"):
        raise ValueError("module order drift")
    records = []
    total = 0
    unit_total = 0
    for module in "ABCDEFGHIJK":
        if module == "A":
            units = []
            silent_tasks, written_tasks = modules[module], None
        elif module == "J":
            units = []
            silent_tasks, written_tasks = None, modules[module]
        elif module == "B":
            units = _project_b(modules[module]); silent_tasks = written_tasks = None
        elif module in "CDEFGH":
            units = _project_progressions(module, modules[module]); silent_tasks = written_tasks = None
        elif module == "I":
            units = _project_i(modules[module]); silent_tasks = written_tasks = None
        else:
            units = _project_k(modules[module]); silent_tasks = written_tasks = None
        events = []
        variants = []
        for unit_number, (source_unit, generated) in enumerate(units, 1):
            start = len(events) + 1
            for ordinal, event in enumerate(generated, start):
                event["source_local_ordinal"] = ordinal
            events.extend(generated)
            variants.append({"id": None, "source_unit_number": unit_number, "source_unit": source_unit,
                             "source_event_ordinals": list(range(start, len(events) + 1)),
                             "event_ids": None, "runtime_eligible": False})
            unit_total += 1
        if module in ATTACK_COUNTS and len(events) != ATTACK_COUNTS[module]:
            raise ValueError(f"{module} projected attack count drift")
        total += len(events)
        section = candidate["module_sections"][module]
        records.append({"source_component": module, "source_heading": section["heading"],
                        "source_txt_ref": section["txt_ref"], "source_pdf_pages": section["pdf_pages"],
                        "identity_state": "unallocated", "silent_tasks": silent_tasks, "written_tasks": written_tasks,
                        "schema1_fields": {"id": None, "workbook_id": None, "module_id": None, "legacy_level": 56,
                            "title": f"Level 56 component {module}", "kind": "mixed", "content_revision": None,
                            "lineage": None, "runtime_eligible": False, "source_refs": None,
                            "events": events, "variants": variants, "resource_requirements": [],
                            "timing": {"status": "unresolved", "unit": "quarter", "fixed_bpm": None},
                            "ambiguities": UNRESOLVED}})
    if total != 936 or unit_total != 54 or records[0]["schema1_fields"]["events"] or records[9]["schema1_fields"]["events"]:
        raise ValueError("whole-Level56 attack/task separation drift")
    proposal = {"proposal_version": "level056-unallocated-schema1-fields.1", "wbs_id": "2.3.1.2.1",
                "classification": "Build-only, nonimportable schema1 field proposal", "legacy_level": 56,
                "canonical_ids_allocated": False, "schema1_importable": False, "whole_workbook_complete": False,
                "runtime_eligible": False, "admitted": False,
                "counts": {"provisional_components": 11, "attack_units": unit_total, "silent_spellings": 42,
                           "written_prompts": 24, "printed_attacks": total, "vi_source_conflicts": 4},
                "source": candidate["source"], "source_conflicts": conflicts,
                "source_differences": candidate["source_differences"], "guidance": candidate["guidance"],
                "records": records}
    handoff = {"handoff_version": "level056-allocation-handoff.1", "wbs_id": "2.3.1.2.1",
               "catalog_workbook_id": entry["workbook_id"], "catalog_role": entry["catalog_role"],
               "existing_level056_records": 0, "existing_level056_workbook_entities": 0,
               "printed_attacks": 936, "silent_spellings_not_events": 42,
               "written_prompts_not_events": 24, "vi_conflict_count": 4,
               "proposed_component_partition": list("ABCDEFGHIJK"), "canonical_ids_allocated": False,
               "admitted": False,
               "required_decisions": ["Review all four VI function-label conflicts with Curriculum without changing source labels.",
                   "Allocate stable identities after current registry reservations are sealed.",
                   "Authorize precise chord voicing, pick and timing before native import or runtime admission."]}
    return proposal, handoff


def products(root: Path) -> dict[str, object]:
    candidate, foundation, registry = read_inputs(root)
    proposal, handoff = project(candidate, foundation, registry)
    manifest = {"manifest_version": "level056-input-pins.1", "inputs": [
        {"path": rel, "bytes": (root / rel).stat().st_size, "sha256": sha} for rel, sha in INPUTS.items()]}
    summary = {"summary_version": "level056-schema1-unallocated-summary.1",
               "proposal_sha256": digest(encoded(proposal)), "handoff_sha256": digest(encoded(handoff)),
               "printed_attacks": 936, "silent_spellings": 42, "written_prompts": 24,
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
    print(f"LEVEL56 {mode.upper()} PASS attacks=936 silent=42 written=24 admitted=false")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("build", "verify"))
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    run(args.mode, args.root.resolve())


if __name__ == "__main__":
    main()
