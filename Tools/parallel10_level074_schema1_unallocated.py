#!/usr/bin/env python3
"""Project pinned Level74 source contacts and count-backed tasks to unallocated fields."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from curriculum_level074_whole_candidate import build, COUNTS


ROOT = Path(__file__).resolve().parents[1]
OUT_REL = Path("Build/parallel-10/level074-schema1-unallocated-r01")
INPUTS = {
    "Tools/curriculum_level074_whole_candidate.py": "37f29623ac48bfd6662f30769c795b5fa075adc0c1f57219611d24fa190ef36f",
    "Results/parallel-08/exercises/conversion/20260923T164605Z-2.3.1.3.1-level074-whole-candidate-r01-results.md": "551ed6355a81c81fae698325ea74cd1eddbb661c426d2725f3a9baa86e931954",
    "Build/parallel-08/2.3.1.3.1-level074-whole-r01/level074-candidate-a.json": "9d0a9f8b5891b6dc24acbb9246e024600001f7fb45ac299bb93b11052178543c",
    "Content/controls/curriculum-v1/package.json": "766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255",
    "Content/controls/curriculum-v1/identity-registry.json": "5d265859e1e8a5a530a0e53d88b019a1c920f3bba6cccb4ef0fef2f7640007e5",
    "Content/controls/curriculum-v1/generation.json": "fc6cec9f9d67eb82c97c5f4c3fb95d285178fb7fce7bd147d9ae0296d21b4c1c",
    "Notes/music/guitar project/TXT version/Guitar_Exercises_Section_X_Level_74_Odd_Rhythmic_Groupings_Cross_Bar_Accent_Cycles_Metric_Displacement_and_Polyrhythmic_Phrase_Control.txt": "63df8ae138ca4587315a04f239818057db44c990c3a6fac3ce9f82244a46aa28",
    "Notes/music/guitar project/PDF version/Guitar_Exercises_Section_X_Level_74_Odd_Rhythmic_Groupings_Cross_Bar_Accent_Cycles_Metric_Displacement_and_Polyrhythmic_Phrase_Control.pdf": "83ce1b9e548e28052de1487f21d70052aeeb3916829d25cc61589df69b650a72",
    "Results/parallel-01/exercises/inventory/20260922T180500Z-2.3-curriculum-v1-source-inventory-evidence/curriculum-source-map.tsv": "f526ff4d9ce3bceaf9a7cc581a3ac2aee2c74917eba984dd57913adba574c123",
}
UNRESOLVED = ["whole-workbook module/item/event/variant identities and representative lineage",
              "C3/C6 74 unspecified pitch contacts",
              "D3 36 and H 200 count-backed contacts without individual grids",
              "quarter onset/duration, assigned BPM, performed pick and full chord voicings",
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
    candidate = json.loads(raw["Build/parallel-08/2.3.1.3.1-level074-whole-r01/level074-candidate-a.json"])
    if candidate != json.loads(json.dumps(build(root))):
        raise ValueError("P08 candidate differs from original TXT/PDF/map replay")
    foundation = json.loads(raw["Content/controls/curriculum-v1/package.json"])
    registry = json.loads(raw["Content/controls/curriculum-v1/identity-registry.json"])
    generation = json.loads(raw["Content/controls/curriculum-v1/generation.json"])
    if len(foundation["records"]) != 659 or generation["records"] != 659:
        raise ValueError("current659 foundation drift")
    return candidate, foundation, registry


def identity_boundary(foundation: dict, registry: dict) -> dict:
    workbook, item = "fg:workbook:000074", "fg:item:000010"
    records = [r for r in foundation["records"] if r.get("legacy_level") == 74 or r.get("workbook_id") == workbook]
    if len(records) != 1 or records[0].get("id") != item or records[0].get("workbook_id") != workbook:
        raise ValueError("Level74 frozen representative record drift")
    entities = {e.get("id") for e in registry["entities"]}
    if workbook not in entities or item not in entities:
        raise ValueError("Level74 existing registry identity drift")
    entry = next((e for e in foundation["workbook_catalog"]["entries"] if e.get("workbook_id") == workbook), None)
    if (not entry or entry.get("representative_item_id") != item or
        entry.get("whole_workbook_complete") is not False or entry.get("admitted") is not False or
        entry.get("conversion_status") != "not_converted"):
        raise ValueError("Level74 representative catalog drift")
    return entry


def positioned_events(task: dict) -> list[dict] | None:
    events = task.get("events")
    if events is not None:
        return events
    if "bars" in task:
        return [event for bar in task["bars"] for event in bar["events"]]
    return None


def project(candidate: dict, foundation: dict, registry: dict) -> tuple[dict, dict]:
    entry = identity_boundary(foundation, registry)
    if (candidate.get("schema") != "fathom.detached.curriculum.level074.whole.r01" or
        candidate.get("wbs") != "2.3.1.3.1" or candidate.get("level") != 74 or
        candidate.get("candidate_status") != "detached_pending_P02_integration_and_curriculum_review" or
        candidate.get("new_canonical_ids_assigned") is not False or
        candidate.get("runtime_import") is not False or candidate.get("content_admitted") is not False or
        candidate.get("timing_in_seconds_or_audio_inferred") is not False):
        raise ValueError("Level74 source/admission boundary drift")
    if (candidate.get("notated_contacts_by_module") != COUNTS or candidate.get("notated_contacts") != 1168 or
        candidate.get("event_coverage") != {"individual_contacts_materialized": 932,
            "with_printed_pitch": 858, "printed_contact_with_unspecified_pitch": 74,
            "task_count_only_without_individual_grid": 236}):
        raise ValueError("1168/932/236 source workload drift")
    if len(candidate["txt_source_lines"]) != 429 or len(candidate["pdf_source_pages"]) != 20:
        raise ValueError("full-source transcription drift")
    if candidate["source_map_row"].get("representative_item_id") != "fg:item:000010":
        raise ValueError("Level74 source-map representative drift")
    if [x["task"] for x in candidate["workload_exceptions"]] != ["E5-E8", "C7", "F3", "H close"]:
        raise ValueError("PDF practice/count exceptions drift")
    if [x["module"] for x in candidate["uncertainty_ledger"]] != ["C", "D", "H", "H", "global"]:
        raise ValueError("source uncertainty ledger drift")
    modules = candidate["modules"]
    if list(modules) != list("ABCDEFGH"):
        raise ValueError("module sequence drift")
    records = []
    printed = materialized = pitched = unknown_pitch = count_backed = unit_total = 0
    for letter in "ABCDEFGH":
        tasks = modules[letter]
        events = []
        variants = []
        count_tasks = []
        module_printed = 0
        for unit_number, task in enumerate(tasks, 1):
            n = task["notated_contacts"]
            module_printed += n
            source_events = positioned_events(task)
            start = len(events) + 1
            if source_events is None:
                if not ((letter == "D" and task["task"].startswith("D3.") and n == 18) or
                        (letter == "H" and n in (48, 80, 32, 40))):
                    raise ValueError("unexpected count-only source task")
                count_tasks.append({"source_unit_number": unit_number, "source_task": task,
                                    "printed_contact_count": n, "individual_events": None,
                                    "runtime_eligible": False})
                count_backed += n
                source_ordinals = None
            else:
                if len(source_events) != n:
                    raise ValueError("positioned source-event count drift")
                for source_event in source_events:
                    if source_event.get("canonical_event_id") is not None:
                        raise ValueError("invented source event identity")
                    if source_event["pitch"] is None:
                        if letter != "C" or task["task"] not in ("C3", "C6") or source_event["fret_contact"] is not None:
                            raise ValueError("unexpected unspecified-pitch contact")
                        unknown_pitch += 1
                    else:
                        pitched += 1
                    events.append({"source_component": letter, "source_unit_number": unit_number,
                                   "source_local_ordinal": len(events) + 1,
                                   "source_txt_lines": task["source_txt_lines"],
                                   "source_pdf_pages": task["source_pdf_pages"],
                                   "source_event": source_event, "performed_member_pitches": None,
                                   "schema1_fields": {"event_id": None, "kind": "contact",
                                                      "contact": "pitched", "pick": None,
                                                      "pitch_binding": None, "onset_q": None,
                                                      "duration_q": None}})
                materialized += n
                source_ordinals = list(range(start, len(events) + 1))
            variants.append({"id": None, "source_unit_number": unit_number, "source_task": task,
                             "source_event_ordinals": source_ordinals, "event_ids": None,
                             "count_backed_contact_count": n if source_events is None else 0,
                             "runtime_eligible": False})
            unit_total += 1
        if module_printed != COUNTS[letter]:
            raise ValueError(f"{letter} printed contact count drift")
        printed += module_printed
        records.append({"source_component": letter, "identity_state": "unallocated_whole_level_fields",
                        "existing_representative_item_id": entry["representative_item_id"],
                        "count_backed_tasks": count_tasks,
                        "schema1_fields": {"id": None, "workbook_id": None, "module_id": None,
                                           "legacy_level": 74, "title": f"Level 74 component {letter}",
                                           "kind": "mixed", "content_revision": None, "lineage": None,
                                           "source_refs": None, "events": events, "variants": variants,
                                           "runtime_eligible": False, "resource_requirements": [],
                                           "timing": {"status": "unresolved", "unit": "quarter", "fixed_bpm": None},
                                           "ambiguities": UNRESOLVED}})
    if (printed, materialized, pitched, unknown_pitch, count_backed, unit_total) != (1168, 932, 858, 74, 236, 51):
        raise ValueError("whole-Level74 contact/task separation drift")
    if len(records[3]["count_backed_tasks"]) != 2 or len(records[7]["count_backed_tasks"]) != 4:
        raise ValueError("D3/H count-only boundary drift")
    proposal = {"proposal_version": "level074-unallocated-schema1-fields.1", "wbs_id": "2.3.1.3.1",
                "classification": "Build-only, nonimportable schema1 field and count-task proposal",
                "legacy_level": 74, "existing_representative_item_id": entry["representative_item_id"],
                "canonical_ids_allocated": False, "schema1_importable": False,
                "whole_workbook_complete": False, "runtime_eligible": False, "admitted": False,
                "counts": {"provisional_components": 8, "source_tasks": 51,
                           "printed_contacts": printed, "individual_event_fields": materialized,
                           "printed_pitch_events": pitched, "unspecified_pitch_events": unknown_pitch,
                           "count_backed_contacts_without_grid": count_backed},
                "source": candidate["source"], "source_map_row": candidate["source_map_row"],
                "txt_source_lines": candidate["txt_source_lines"],
                "pdf_source_pages": candidate["pdf_source_pages"],
                "count_convention": candidate["count_convention"],
                "workload_exceptions": candidate["workload_exceptions"],
                "uncertainty_ledger": candidate["uncertainty_ledger"], "records": records}
    handoff = {"handoff_version": "level074-allocation-handoff.1", "wbs_id": "2.3.1.3.1",
               "catalog_workbook_id": entry["workbook_id"], "existing_representative_item_id": entry["representative_item_id"],
               "existing_level074_records": 1, "existing_level074_workbook_entities": 1,
               "printed_contacts": 1168, "individual_event_fields": 932,
               "count_backed_contacts_without_grid": 236,
               "proposed_component_partition": list("ABCDEFGH"),
               "canonical_ids_allocated": False, "admitted": False,
               "required_decisions": ["Reconcile whole-workbook lineage with frozen representative fg:item:000010.",
                   "Resolve C3/C6 pitch and D3/H individual contact gaps without inventing source grids.",
                   "Authorize event timing, BPM, pick, final-close voicing and admission separately."]}
    return proposal, handoff


def products(root: Path) -> dict[str, object]:
    candidate, foundation, registry = read_inputs(root)
    proposal, handoff = project(candidate, foundation, registry)
    manifest = {"manifest_version": "level074-input-pins.1", "inputs": [
        {"path": rel, "bytes": (root / rel).stat().st_size, "sha256": sha} for rel, sha in INPUTS.items()]}
    summary = {"summary_version": "level074-schema1-unallocated-summary.1",
               "proposal_sha256": digest(encoded(proposal)), "handoff_sha256": digest(encoded(handoff)),
               "printed_contacts": 1168, "materialized_event_fields": 932,
               "count_backed_contacts": 236, "native_run": False,
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
    print(f"LEVEL74 {mode.upper()} PASS contacts=1168 explicit=932 count_backed=236 admitted=false")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("build", "verify"))
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    run(args.mode, args.root.resolve())


if __name__ == "__main__":
    main()
