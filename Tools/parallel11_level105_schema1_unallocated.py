#!/usr/bin/env python3
"""Project the sealed whole-Level105 source into unallocated schema1 task fields."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from curriculum_level105_whole_candidate import build_candidate


ROOT = Path(__file__).resolve().parents[1]
OUT_REL = Path("Build/parallel-11/2.3.1.3.1-level105-schema1-unallocated-r01")
INPUTS = {
    "Tools/curriculum_level105_whole_candidate.py": "4d894767f11a1fde8289dee4a50650059ea35aaad0c734aa0942ca1fe9333ab2",
    "Results/parallel-11/curriculum/20260923T172500Z-2.3-level105-whole-r01-results.md": "aa5b9797e7bc1a016c9f40417cd67027be1d3d1567b90eaf17d3d9a969a7cff9",
    "Build/parallel-11/2.3.1.3.1-level105-whole-r01/candidate-b.json": "00de08e0241f19c22889b8b189d64b56ecd49ab712e0ef543c481e5b09fe696a",
    "Content/controls/curriculum-v1/package.json": "766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255",
    "Content/controls/curriculum-v1/identity-registry.json": "5d265859e1e8a5a530a0e53d88b019a1c920f3bba6cccb4ef0fef2f7640007e5",
    "Content/controls/curriculum-v1/generation.json": "fc6cec9f9d67eb82c97c5f4c3fb95d285178fb7fce7bd147d9ae0296d21b4c1c",
    "Notes/music/guitar project/TXT version/Guitar_Exercises_Level_105_Final_Musicianship_Capstone_Complete_105_Level_Core_Curriculum.txt": "793cf5eab18d4501b7b1d7317caeb89b91719e4b71d7cadff9f905afb4a56bf5",
    "Notes/music/guitar project/PDF version/Guitar_Exercises_Level_105_Final_Musicianship_Capstone_Complete_105_Level_Core_Curriculum.pdf": "e8642650a58154eb0ec2985e05ea2a48bdd417d4d5fc1ac4cd08591d13538a5b",
    "Results/parallel-01/exercises/inventory/20260922T180500Z-2.3-curriculum-v1-source-inventory-evidence/curriculum-source-map.json": "bad5581a04f43ba8baf14db430449e1ccff5cf88f0f7e42198328073b27053d6",
}
WORKLOADS = {"A": 160, "B": 160, "C": 160, "D": 160, "E": 160,
             "F": 160, "G": 144, "H": 160, "I": 128, "J": 480}
MODULE_ROWS = {"A": 16, "B": 8, "C": 16, "D": 15, "E": 13,
               "F": 8, "G": 8, "H": 16, "I": 16, "J": 35}
UNRESOLVED = [
    "Canonical workbook/module/item/event/variant identities and lineage are not allocated by this proposal.",
    "No printed note attacks, member pitches, quarter-note timing, fixed BPM or performed event sequence are established.",
    "No learner answers, rubric scores, reviewer evidence, repeatability, mastery, core completion or graduation are established.",
    "PDF p27 condensed core option does not by itself prove PDF p30 finished-original graduation obligation.",
]


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def encoded(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def pinned(root: Path, rel: str, sha: str) -> bytes:
    raw = (root / rel).read_bytes()
    if digest(raw) != sha:
        raise ValueError(f"input drift: {rel}")
    return raw


def read_inputs(root: Path) -> tuple[dict, dict, dict]:
    raw = {rel: pinned(root, rel, sha) for rel, sha in INPUTS.items()}
    candidate = json.loads(raw["Build/parallel-11/2.3.1.3.1-level105-whole-r01/candidate-b.json"])
    if candidate != build_candidate(root):
        raise ValueError("sealed Level105 candidate differs from original TXT/PDF/source-map replay")
    foundation = json.loads(raw["Content/controls/curriculum-v1/package.json"])
    registry = json.loads(raw["Content/controls/curriculum-v1/identity-registry.json"])
    generation = json.loads(raw["Content/controls/curriculum-v1/generation.json"])
    if len(foundation["records"]) != 659 or generation["records"] != 659:
        raise ValueError("current659 foundation drift")
    return candidate, foundation, registry


def identity_boundary(foundation: dict, registry: dict) -> dict:
    entry = next((e for e in foundation["workbook_catalog"]["entries"]
                  if e.get("workbook_id") == "fg:workbook:000105"), None)
    if not entry or entry.get("representative_item_id") != "fg:item:000013" or entry.get("whole_workbook_complete") is not False:
        raise ValueError("Level105 selected-representative catalog drift")
    if entry.get("admitted") is not False or entry.get("runtime_eligible") is not False or entry.get("runtime_admitted") is not False:
        raise ValueError("Level105 catalog admission drift")
    records = [r for r in foundation["records"] if r.get("legacy_level") == 105]
    if len(records) != 1 or records[0].get("id") != "fg:item:000013" or records[0].get("events") != [] or records[0].get("control_scope", {}).get("whole_workbook_complete") is not False:
        raise ValueError("Level105 selected record boundary drift")
    ids = {e.get("id") for e in registry["entities"]}
    if not {"fg:workbook:000105", "fg:module:000013", "fg:item:000013"} <= ids:
        raise ValueError("Level105 registry boundary drift")
    return entry


def validate_candidate(c: dict) -> None:
    if c.get("schema") != "fathom.level105.detached-source-task-candidate.1" or c.get("wbs") != "2.3.1.3.1" or c.get("level") != 105:
        raise ValueError("Level105 source candidate scope drift")
    if c.get("status") != "non_admitted" or c.get("admitted") is not False or c.get("existing_representative_item_id_read_only") != "fg:item:000013":
        raise ValueError("Level105 source identity/admission drift")
    for key in ("canonical_id", "exercise_id", "onset_q", "duration_q", "fixed_bpm", "executable_events",
                "sounding_midi_events", "performed_event_count", "rubric_outcome", "core_complete", "graduated"):
        if c.get(key) is not None:
            raise ValueError(f"invented source outcome: {key}")
    if c.get("declared_workload_total") != 1872 or c.get("declared_workload_by_module") != WORKLOADS:
        raise ValueError("declared workload drift")
    if list(c["modules"]) != list(WORKLOADS):
        raise ValueError("A–J module order drift")
    for letter, module in c["modules"].items():
        if module["declared_events"] != WORKLOADS[letter] or module["per_task_event_allocation"] is not None:
            raise ValueError(f"{letter} invented event allocation")
        rows = [row for table in module["tables"] for row in table["rows"]]
        if len(rows) != MODULE_ROWS[letter] or any(row["declared_events_for_row"] is not None or row["performed_result"] is not None for row in rows):
            raise ValueError(f"{letter} task row drift")
    b = c["modules"]["B"]["fixed_melody_reharmonization"]
    if [n["top_note"] for n in b["top_notes"]] != ["E", "G", "C", "F#", "Bb", "A"] or b["required_supporting_harmonies_per_note"] != 3:
        raise ValueError("B fixed melody drift")
    if any(any(n[k] is not None for k in ("supporting_harmonies", "stated_chord_function", "stated_bass_direction", "note_role")) for n in b["top_notes"]):
        raise ValueError("B invented reharmonization answer")
    j = c["modules"]["J"]["reflection"]
    if len(j["questions"]) != 6 or any(q["answer"] is not None for q in j["questions"]):
        raise ValueError("J reflection drift")
    exam = c["final_exam"]
    if len(exam["schedule"]) != 8 or len(exam["detailed_blocks_1_to_7"]) != 7 or exam["scheduled_minutes"] != 60:
        raise ValueError("exam schedule drift")
    if exam["minute_windows_are_musical_onsets"] is not False or exam["actual_duration_minutes"] is not None or exam["performed_session"] is not None:
        raise ValueError("invented musical/session timing")
    if sum(len(x["rows"]) for x in exam["detailed_blocks_1_to_7"]) != 27:
        raise ValueError("exam detailed rows drift")
    graduation = c["graduation"]
    if (graduation["maximum_score"], graduation["required_score"], len(graduation["rubric"]), len(graduation["requirements"])) != (30, 24, 10, 6):
        raise ValueError("graduation rubric drift")
    if set(graduation["no_zero_domains"]) != {"Rhythm/Groove", "Ear/Transcription", "Recovery", "Performance"}:
        raise ValueError("protected domains drift")
    if graduation["recorded_scores"] is not None or graduation["recorded_reviewer"] is not None or len(graduation["repeatability_alternatives"]) != 2:
        raise ValueError("invented graduation evidence")
    if len(c["remediation"]) != 9 or len(c["core_path_transformations"]) != 12 or len(c["post_core_tracks"]) != 10:
        raise ValueError("post-exam support drift")
    if c["hard_stop"]["level_106_exists"] is not False or c["hard_stop"]["maximum_core_level"] != 105:
        raise ValueError("Level106 hard stop drift")
    conflicts = [x for x in c["source_ambiguities"] if x["kind"] == "block7_condensed_core_vs_finished_original"]
    if len(conflicts) != 1 or conflicts[0]["status"] != "pending_curriculum_review":
        raise ValueError("p27/p30 original-work ambiguity lost")
    block7 = next(x for x in exam["detailed_blocks_1_to_7"] if x["block"] == 7)
    if not any("complete original or condensed core version" in str(row["fields"]) for row in block7["rows"]):
        raise ValueError("p27 condensed option lost")
    if not any("finished original" in str(row["fields"]) for row in graduation["requirements"]):
        raise ValueError("p30 finished-original obligation lost")


def project(candidate: dict, foundation: dict, registry: dict) -> tuple[dict, dict]:
    validate_candidate(candidate)
    entry = identity_boundary(foundation, registry)
    records = []
    for letter, module in candidate["modules"].items():
        refs = [module["txt_ref"], module["pdf_overview_ref"]] + [f"L105-PDF-p{p}" for p in module["pdf_pages"]]
        task_tables = module["tables"]
        record = {
            "source_component": letter,
            "source_heading": module["name"],
            "declared_workload_events": module["declared_events"],
            "printed_task_row_count": MODULE_ROWS[letter],
            "source_pdf_pages": module["pdf_pages"],
            "source_task_tables": task_tables,
            "fixed_melody_reharmonization": module.get("fixed_melody_reharmonization"),
            "reflection": module.get("reflection"),
            "identity_state": "unallocated",
            "schema1_fields": {
                "id": None, "workbook_id": None, "module_id": None, "legacy_level": 105,
                "title": f"Level 105 component {letter}: {module['name']}", "kind": "task",
                "content_revision": None, "lineage": None, "status": "unallocated_source_projection",
                "runtime_eligible": False, "admitted": False,
                "source_refs": refs, "authored_text_refs": refs,
                "control_scope": {"extent": "whole_source_component_proposal", "local_case": letter,
                                  "source_event_count": None, "declared_workload_events": module["declared_events"],
                                  "whole_workbook_complete": False, "unresolved": UNRESOLVED},
                "events": [], "variants": [], "resource_requirements": [],
                "timing": {"status": "unresolved_not_musical_note_timing", "unit": "quarter", "fixed_bpm": None,
                           "onset_q": None, "duration_q": None},
                "rubric": candidate["graduation"] if letter == "J" else None,
                "ambiguities": UNRESOLVED,
            },
        }
        records.append(record)
    proposal = {
        "proposal_version": "level105-unallocated-schema1-fields.1", "wbs_id": "2.3.1.3.1",
        "classification": "Build-only, nonimportable schema1 task-field proposal",
        "legacy_level": 105, "canonical_ids_allocated": False, "schema1_importable": False,
        "whole_workbook_complete": False, "runtime_eligible": False, "admitted": False,
        "core_complete": None, "graduated": None, "mastery": None,
        "counts": {"provisional_components": 10, "printed_module_task_rows": 151,
                   "support_table_rows": 64, "declared_workload_events": 1872,
                   "printed_note_attacks": 0, "authored_note_events": 0,
                   "fixed_top_note_prompts": 6, "unanswered_reflection_questions": 6},
        "source": candidate["source"], "source_map_row": candidate["source_map_row"],
        "source_full_text": {"txt_lines": candidate["txt_full_lines"],
                             "pdf_extracted_pages": candidate["pdf_full_extracted_pages"]},
        "source_ambiguities": candidate["source_ambiguities"],
        "foundations": candidate["foundations"], "final_exam": candidate["final_exam"],
        "graduation": candidate["graduation"], "remediation": candidate["remediation"],
        "core_path_transformations": candidate["core_path_transformations"],
        "post_core_tracks": candidate["post_core_tracks"], "hard_stop": candidate["hard_stop"],
        "records": records,
    }
    handoff = {
        "handoff_version": "level105-allocation-handoff.1", "wbs_id": "2.3.1.3.1",
        "catalog_workbook_id_read_only": entry["workbook_id"],
        "existing_selected_item_id_read_only": "fg:item:000013",
        "existing_selected_record_count": 1, "existing_selected_record_event_count": 0,
        "proposed_component_partition": list(WORKLOADS),
        "canonical_ids_allocated": False, "admitted": False,
        "required_decisions": [
            "Review whole-workbook coverage and source task/rubric distinctions before any canonical allocation.",
            "Resolve PDF p27 condensed core exam option versus PDF p30 finished-original graduation requirement.",
            "Allocate identities and lineage only through the canonical owner; do not reuse the selected task identity for all A–J.",
            "Obtain actual learner, reviewer, repeatability and Curriculum evidence before core-completion or graduation claims.",
        ],
    }
    return proposal, handoff


def products(root: Path) -> dict[str, object]:
    candidate, foundation, registry = read_inputs(root)
    proposal, handoff = project(candidate, foundation, registry)
    manifest = {"manifest_version": "level105-schema1-input-pins.1", "inputs": [
        {"path": rel, "bytes": (root / rel).stat().st_size, "sha256": sha} for rel, sha in INPUTS.items()]}
    summary = {"summary_version": "level105-schema1-unallocated-summary.1",
               "proposal_sha256": digest(encoded(proposal)), "handoff_sha256": digest(encoded(handoff)),
               "printed_task_rows": 151, "support_table_rows": 64, "declared_workload_events": 1872,
               "authored_note_events": 0, "native_run": False, "runtime_eligible": False,
               "admitted": False, "core_complete": None, "graduated": None}
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
    print(f"LEVEL105 {mode.upper()} PASS tasks=151 support=64 declared=1872 note_events=0 admitted=false")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("build", "verify"))
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    run(args.mode, args.root.resolve())


if __name__ == "__main__":
    main()
