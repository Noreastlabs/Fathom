#!/usr/bin/env python3
"""Project sealed Level77 ear-to-hand source into unallocated schema1 fields."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = Path("Build/parallel-07/2.3.1.3.1-level077-schema1-unallocated-r01")
STEM = "Guitar_Exercises_Section_X_Level_77_Interval_Recognition_Chord_Function_Hearing_Sung_Guide_Tones_Melodic_Dictation_Call_and_Response_and_Immediate_Fretboard_Realization"
TXT = f"Notes/music/guitar project/TXT version/{STEM}.txt"
PDF = f"Notes/music/guitar project/PDF version/{STEM}.pdf"
WHOLE = "Build/parallel-07/2.3.1.3.1-level077-whole-r01/level077_whole_candidate.json"
MAP = "Results/parallel-01/exercises/inventory/20260922T180500Z-2.3-curriculum-v1-source-inventory-evidence/curriculum-source-map.json"
PACKAGE = "Content/controls/curriculum-v1/package.json"
REGISTRY = "Content/controls/curriculum-v1/identity-registry.json"
GENERATION = "Content/controls/curriculum-v1/generation.json"
INPUTS = {
    WHOLE: "090561b534862b81e65d71f3c4376ac9749194363d7cc2f8a4f4b7bf74a0fcbd",
    TXT: "54ab2490448e1fa6391ead275fe22e2fbec9be23d6e83c88001293b4be7e7236",
    PDF: "bfeaab5b0ddd52ac55063e0552b8c451d8a8029ddb073b744d8f0e76186aedce",
    MAP: "bad5581a04f43ba8baf14db430449e1ccff5cf88f0f7e42198328073b27053d6",
    PACKAGE: "766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255",
    REGISTRY: "5d265859e1e8a5a530a0e53d88b019a1c920f3bba6cccb4ef0fef2f7640007e5",
    GENERATION: "fc6cec9f9d67eb82c97c5f4c3fb95d285178fb7fce7bd147d9ae0296d21b4c1c",
}
DECLARED = {"A": 144, "B": 96, "C": 120, "D": 128, "E": 128, "F": 112, "G": 96, "H": 128}
TASKS = {"A": 51, "B": 21, "C": 13, "D": 18, "E": 18, "F": 30, "G": 32, "H": 23}
EXPLICIT = {"A": 48, "B": 0, "C": 20, "D": 53, "E": 64, "F": 28, "G": 0, "H": 64}
TABLE_MODULE = {"interval_cards": "A", "major_guides": "C", "minor_guides": "C",
                "dictation_phrases": "D", "call_response": "E", "degree_realization": "F",
                "chord_realization": "F", "model_bars": "H"}
UNRESOLVED = [
    "Canonical workbook/module/item/task/event/variant IDs and lineage are unallocated.",
    "The source-declared 952 workload does not specify 952 individual pitch contacts; only 277 are explicit.",
    "Event octave, guitar string/fret, onset/duration, fixed BPM and source audio remain unresolved.",
    "Performed responses, scores and mastery remain unobserved.",
    "Card-20 interval conflict, 18-versus-24 page-16 prompts, incomplete rhythm grids and absent capstone recording require review.",
]


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def encoded(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def read_inputs(root: Path) -> dict:
    raw = {}
    for rel, expected in INPUTS.items():
        data = (root / rel).read_bytes()
        if sha(data) != expected:
            raise ValueError(f"input drift: {rel}")
        raw[rel] = data
    parsed = {rel: json.loads(raw[rel]) for rel in (WHOLE, MAP, PACKAGE, REGISTRY, GENERATION)}
    parsed[TXT] = raw[TXT].decode("utf-8").splitlines()
    return parsed


def identity_boundary(data: dict) -> dict:
    foundation, registry, generation = data[PACKAGE], data[REGISTRY], data[GENERATION]
    workbook = "fg:workbook:000077"
    if len(foundation["records"]) != 659 or generation["records"] != 659:
        raise ValueError("current659 foundation drift")
    if any(r.get("legacy_level") == 77 or r.get("workbook_id") == workbook for r in foundation["records"]):
        raise ValueError("Level77 canonical record already exists")
    if any(e.get("id") == workbook for e in registry["entities"]):
        raise ValueError("Level77 registry entity already exists")
    entry = next((e for e in foundation["workbook_catalog"]["entries"] if e.get("workbook_id") == workbook), None)
    if (not entry or entry.get("conversion_status") != "not_converted" or entry.get("admitted") is not False
        or entry.get("representative_item_id") is not None or entry.get("whole_workbook_complete") is not False):
        raise ValueError("Level77 source-only catalog boundary drift")
    return entry


def validate_source(candidate: dict, source_map: dict, lines: list[str]) -> None:
    if (candidate.get("schema") != "fathom.detached_curriculum_source_candidate.v1"
        or candidate.get("level") != 77 or candidate.get("wbs_owner") != "2.3.1.3.1"
        or candidate.get("status") != "candidate_only" or candidate.get("admission_claim") is not False):
        raise ValueError("Level77 candidate authority/scope drift")
    for label, rel in (("txt", TXT), ("pdf", PDF)):
        pin = candidate["source_pins"][label]
        if pin["path"] != rel or pin["sha256"] != INPUTS[rel]:
            raise ValueError("Level77 source identity drift")
    archived_lines = candidate["source_archive"]["txt_lines"]
    if (len(lines) != 80 or len(archived_lines) != 80
        or any(item != {"line": i, "text": line} for i, (item, line) in enumerate(zip(archived_lines, lines), 1))):
        raise ValueError("Level77 original TXT/archive drift")
    pages = candidate["source_archive"]["pdf_pages"]
    if len(pages) != 20 or any(page.get("page") != i for i, page in enumerate(pages, 1)):
        raise ValueError("Level77 PDF page archive drift")
    if len(candidate["pdf_tables"]) != 16:
        raise ValueError("Level77 printed table count drift")
    if candidate["module_workload_declared"] != DECLARED or candidate["declared_workload_total"] != 952:
        raise ValueError("Level77 declared workload drift")
    if len(candidate["tasks"]) != 206 or len(candidate["explicit_pitch_events"]) != 277:
        raise ValueError("Level77 explicit task/event count drift")
    row = next((r for r in source_map["rows"] if r.get("level") == 77), None)
    if (row is None or row != candidate["source_map"] or row.get("txt_sha256") != INPUTS[TXT]
        or row.get("pdf_sha256") != INPUTS[PDF] or row.get("conversion_status") != "not_converted"
        or any(row.get(k) is not False for k in ("stable_ids_assigned", "runtime_eligible", "imported", "admitted"))):
        raise ValueError("Level77 frozen inventory status drift")
    tensions = candidate["source_tensions"]
    if len(tensions) != 8:
        raise ValueError("Level77 source tension ledger drift")
    first = tensions[0]
    if (first.get("printed_answer") != "m6" or first.get("computed_semitones") != 9
        or first.get("resolution") != "unresolved_source_error"):
        raise ValueError("card-20 interval conflict lost")
    if tensions[2].get("missing_prompt_numbers") != list(range(19, 25)):
        raise ValueError("page-16 prompt count conflict lost")
    if tensions[-1].get("unfamiliar_source") is not None:
        raise ValueError("capstone recording/source invented")
    if candidate["unresolved_performance_fields"] != ["source_audio", "octave", "string", "fret",
        "onset_q", "duration_q", "performed_response", "score", "canonical_task_id", "canonical_event_id"]:
        raise ValueError("Level77 unresolved performance fields drift")


def task_field(task: dict, module: str, candidate: dict, lines: list[str], global_ordinal: int) -> dict:
    expected = {"local_key", "module", "kind", "source", "fields", "canonical_task_id",
                "answer_visibility", "observed_answer", "observed_score"}
    if (set(task) != expected or task["module"] != module or task["canonical_task_id"] is not None
        or task["observed_answer"] is not None or task["observed_score"] is not None):
        raise ValueError("source task authority/order drift")
    ref = task["source"]
    page, line = ref["pdf_page"], ref["txt_line"]
    if not isinstance(page, int) or not 1 <= page <= 20:
        raise ValueError("task PDF page ref drift")
    if line is not None and (not isinstance(line, int) or not 1 <= line <= len(lines) or not lines[line - 1]):
        raise ValueError("task TXT line ref drift")
    if task["kind"] == "random_function_prompt":
        fields = task["fields"]
        if (fields.get("printed_answer") is not None or fields.get("answer_provenance") != "music_theory_inference_not_printed"
            or fields.get("specific_audio_or_octave") is not None):
            raise ValueError("random function prompt inference boundary drift")
    return {"source_global_ordinal": global_ordinal, "source_task": task,
            "schema1_fields": {"id": None, "kind": "task",
                                                  "runtime_eligible": False, "source_refs": None,
                                                  "observed_answer": None, "observed_score": None}}


def event_field(event: dict, module: str, candidate: dict) -> dict:
    expected = {"local_key", "source", "pitch_name", "pitch_class", "degree", "role",
                "octave", "string", "fret", "onset_q", "duration_q", "canonical_event_id", "performed_result"}
    if set(event) != expected or event["source"]["table"] not in TABLE_MODULE or TABLE_MODULE[event["source"]["table"]] != module:
        raise ValueError("explicit event source table/module drift")
    if any(event[key] is not None for key in ("octave", "string", "fret", "onset_q", "duration_q",
                                               "canonical_event_id", "performed_result")):
        raise ValueError("explicit event invented performance/identity")
    ref = event["source"]
    table = candidate["pdf_tables"][ref["table"]]
    if (ref["pdf_page"] != table["page"] or not isinstance(ref["row"], int)
        or not 1 <= ref["row"] <= len(table["rows"]) or not isinstance(ref["slot"], int) or ref["slot"] < 1):
        raise ValueError("explicit event PDF table/row ref drift")
    if event["pitch_name"] is not None and not isinstance(event["pitch_name"], str):
        raise ValueError("explicit pitch name drift")
    return {"source_event": event,
            "source_tone": {"printed_pitch_name": event["pitch_name"], "theory_pitch_class": event["pitch_class"],
                            "printed_degree": event["degree"], "source_role": event["role"],
                            "sounding_midi": None, "guitar_string": None, "guitar_fret": None},
            "schema1_fields": {"event_id": None, "kind": "contact", "contact": None,
                               "pick": None, "pitch_binding": None, "onset_q": None, "duration_q": None}}


def project(data: dict) -> tuple[dict, dict]:
    candidate, lines = data[WHOLE], data[TXT]
    entry = identity_boundary(data)
    validate_source(candidate, data[MAP], lines)
    records = []
    seen_tasks = []
    seen_events = []
    task_ordinals = {task["local_key"]: i for i, task in enumerate(candidate["tasks"], 1)}
    if len(task_ordinals) != 206:
        raise ValueError("source task local-key duplication")
    for module in DECLARED:
        tasks = [task for task in candidate["tasks"] if task["module"] == module]
        events = [event for event in candidate["explicit_pitch_events"]
                  if TABLE_MODULE.get(event["source"]["table"]) == module]
        if len(tasks) != TASKS[module] or len(events) != EXPLICIT[module]:
            raise ValueError("module task/explicit-event partition drift")
        source_tasks = [task_field(t, module, candidate, lines, task_ordinals[t["local_key"]]) for t in tasks]
        source_events = [event_field(e, module, candidate) for e in events]
        seen_tasks.extend(tasks)
        seen_events.extend(events)
        records.append({"source_component": module, "identity_state": "unallocated",
                        "source_declared_workload": DECLARED[module], "source_tasks": source_tasks,
                        "schema1_fields": {"id": None, "workbook_id": None, "module_id": None,
                                           "legacy_level": 77, "title": f"Level 77 component {module}",
                                           "kind": "mixed", "content_revision": None, "lineage": None,
                                           "runtime_eligible": False, "source_refs": None,
                                           "events": source_events,
                                           "variants": [{"id": None, "source_component": module,
                                                         "source_event_ordinals": list(range(1, len(events) + 1)),
                                                         "event_ids": None, "runtime_eligible": False}],
                                           "resource_requirements": [],
                                           "timing": {"status": "unresolved", "unit": "quarter", "fixed_bpm": None},
                                           "ambiguities": UNRESOLVED}})
    if (Counter(t["local_key"] for t in seen_tasks) != Counter(t["local_key"] for t in candidate["tasks"])
        or seen_events != candidate["explicit_pitch_events"]
        or len({t["local_key"] for t in seen_tasks}) != 206
        or len({e["local_key"] for e in seen_events}) != 277):
        raise ValueError("source task/event union lost or duplicated")
    prompts = [t for t in candidate["tasks"] if t["kind"] == "random_function_prompt"]
    if len(prompts) != 18:
        raise ValueError("printed random prompt count drift")
    proposal = {"proposal_version": "level077-unallocated-schema1-fields.1", "wbs_id": "2.3.1.3.1",
                "classification": "Build-only, nonimportable schema1 field proposal", "legacy_level": 77,
                "canonical_ids_allocated": False, "schema1_importable": False,
                "whole_workbook_complete": False, "runtime_eligible": False, "admitted": False,
                "counts": {"components": 8, "printed_tables": 16, "authored_tasks": 206,
                           "explicit_printed_pitch_events": 277, "source_declared_workload": 952,
                           "declared_by_module": DECLARED, "tasks_by_module": TASKS,
                           "explicit_events_by_module": EXPLICIT, "printed_random_function_prompts": 18},
                "source_pins": candidate["source_pins"], "source_map": candidate["source_map"],
                "source_archive": candidate["source_archive"], "pdf_tables": candidate["pdf_tables"],
                "source_task_order": [task["local_key"] for task in candidate["tasks"]],
                "source_tensions": candidate["source_tensions"],
                "unresolved_performance_fields": candidate["unresolved_performance_fields"],
                "records": records}
    handoff = {"handoff_version": "level077-allocation-handoff.1", "wbs_id": "2.3.1.3.1",
               "catalog_workbook_id": entry["workbook_id"], "catalog_role": entry["catalog_role"],
               "existing_level077_records": 0, "existing_level077_workbook_entities": 0,
               "proposed_component_partition": list(DECLARED), "authored_tasks": 206,
               "explicit_printed_pitch_events": 277, "source_declared_workload": 952,
               "canonical_ids_allocated": False, "admitted": False,
               "required_decisions": ["Reconcile card-20 m6/M6 and page-16 24-versus-18 prompt discrepancies.",
                                      "Decide contact multiplicity and missing realizations behind the 952-event declaration.",
                                      "Supply or waive the unfamiliar capstone recording and authorize exact rhythm grids.",
                                      "Allocate stable identities, then authorize octave, fretboard contact, timing, audio and mastery before runtime import."]}
    return proposal, handoff


def products(root: Path) -> dict[str, object]:
    proposal, handoff = project(read_inputs(root))
    manifest = {"manifest_version": "level077-input-pins.1", "inputs": [
        {"path": rel, "bytes": (root / rel).stat().st_size, "sha256": digest}
        for rel, digest in INPUTS.items()]}
    summary = {"summary_version": "level077-schema1-unallocated-summary.1",
               "proposal_sha256": sha(encoded(proposal)), "handoff_sha256": sha(encoded(handoff)),
               "authored_tasks": 206, "explicit_printed_pitch_events": 277,
               "source_declared_workload": 952,
               "native_run": False, "runtime_eligible": False, "admitted": False}
    return {"field-proposal.json": proposal, "allocation-handoff.json": handoff,
            "input-manifest.json": manifest, "summary.json": summary}


def output_dir(root: Path) -> Path:
    part = root
    for component in OUT.parts:
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
    print(f"LEVEL77 {mode.upper()} PASS tasks=206 explicit=277 declared=952 admitted=false")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("build", "verify"))
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    run(args.mode, args.root.resolve())
