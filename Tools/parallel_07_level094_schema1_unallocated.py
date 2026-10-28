#!/usr/bin/env python3
"""Project sealed whole-Level94 expression source into unallocated schema1 fields."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = Path("Build/parallel-07/2.3.1.3.1-level094-schema1-unallocated-r01")
STEM = "Guitar_Exercises_Section_XIII_Level_94_Expressive_Performance_Synthesis_Emotional_Contour_Dynamic_Tonal_Orchestration_Restraint_and_Complete_Solo_Capstone"
TXT = f"Notes/music/guitar project/TXT version/{STEM}.txt"
PDF = f"Notes/music/guitar project/PDF version/{STEM}.pdf"
WHOLE = "Build/parallel-07/2.3.1.3.1-level094-whole-r01/level094_whole_candidate.json"
NARROW = "Build/parallel-06/2.3-level094-music-r01/candidate-a.json"
MAP = "Results/parallel-01/exercises/inventory/20260922T180500Z-2.3-curriculum-v1-source-inventory-evidence/curriculum-source-map.json"
PACKAGE = "Content/controls/curriculum-v1/package.json"
REGISTRY = "Content/controls/curriculum-v1/identity-registry.json"
GENERATION = "Content/controls/curriculum-v1/generation.json"
INPUTS = {
    WHOLE: "063a82d354929500457c7a549fb7401454a29442021e824bc68151f7707020ba",
    NARROW: "b3404533e4e16590313121b794008362d7f34783fe1ec57885c7d89a1fb27be6",
    TXT: "c145149fba43a2f8836ae64a7569f369aa6dcc88b0e7beefce02e0d4aeddab48",
    PDF: "1743888569b5ea38659d7310af764df0bca4c969ed9a1e633ac106d2fc67965f",
    MAP: "bad5581a04f43ba8baf14db430449e1ccff5cf88f0f7e42198328073b27053d6",
    PACKAGE: "766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255",
    REGISTRY: "5d265859e1e8a5a530a0e53d88b019a1c920f3bba6cccb4ef0fef2f7640007e5",
    GENERATION: "fc6cec9f9d67eb82c97c5f4c3fb95d285178fb7fce7bd147d9ae0296d21b4c1c",
}
DECLARED = {"A": 128, "B": 128, "C": 128, "D": 112, "E": 112,
            "F": 128, "G": 192, "H": 160, "I": 320, "J": 64}
TASKS = {"A": 22, "B": 15, "C": 14, "D": 9, "E": 7,
         "F": 13, "G": 29, "H": 17, "I": 11, "J": 9}
MARKERS = {"A": 24, "B": 0, "C": 0, "D": 0, "E": 0,
           "F": 0, "G": 32, "H": 8, "I": 40, "J": 0}
UNRESOLVED = [
    "Canonical workbook/module/item/task/event/variant IDs, content revision and lineage are unallocated.",
    "1,472 declared events are not printed as 1,472 note attacks; only 104 bar/window markers are source-supported.",
    "Specific target pitch, octave, fret/string, tempo, onset/duration, loudness and performed articulation remain unresolved.",
    "Performed result, recording, score and mastery remain unobserved.",
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
    result = {rel: json.loads(raw[rel]) for rel in (WHOLE, NARROW, MAP, PACKAGE, REGISTRY, GENERATION)}
    result[TXT] = raw[TXT].decode("utf-8").splitlines()
    return result


def identity_boundary(data: dict) -> dict:
    foundation, registry, generation = data[PACKAGE], data[REGISTRY], data[GENERATION]
    workbook = "fg:workbook:000094"
    if len(foundation["records"]) != 659 or generation["records"] != 659:
        raise ValueError("current659 foundation drift")
    if any(r.get("legacy_level") == 94 or r.get("workbook_id") == workbook for r in foundation["records"]):
        raise ValueError("Level94 canonical record already exists")
    if any(e.get("id") == workbook for e in registry["entities"]):
        raise ValueError("Level94 workbook registry entity already exists")
    entry = next((x for x in foundation["workbook_catalog"]["entries"] if x.get("workbook_id") == workbook), None)
    if (not entry or entry.get("catalog_role") != "read_only_source_preservation"
        or entry.get("conversion_status") != "not_converted" or entry.get("review") != "Pending"
        or entry.get("representative_item_id") is not None
        or any(entry.get(k) is not False for k in ("runtime_eligible", "runtime_admitted", "imported", "admitted", "whole_workbook_complete"))
        or entry.get("playable_projection", {}).get("status") != "explicitly_empty_unresolved"):
        raise ValueError("Level94 source-only catalog boundary drift")
    return entry


def validate_source(candidate: dict, narrow: dict, source_map: dict, lines: list[str]) -> None:
    if (candidate.get("schema") != "fathom.detached_curriculum_source_candidate.v1" or candidate.get("level") != 94
        or candidate.get("wbs_owner") != "2.3.1.3.1" or candidate.get("status") != "candidate_only"
        or candidate.get("admission_claim") is not False):
        raise ValueError("Level94 candidate scope/authority drift")
    for label, rel in (("txt", TXT), ("pdf", PDF)):
        pin = candidate["source_pins"][label]
        if pin["path"] != rel or pin["sha256"] != INPUTS[rel]:
            raise ValueError("Level94 original source identity drift")
    archived = candidate["source_archive"]["txt_lines"]
    if len(lines) != 44 or archived != [{"line": i, "text": line} for i, line in enumerate(lines, 1)]:
        raise ValueError("Level94 original TXT/archive drift")
    pages = candidate["source_archive"]["pdf_pages"]
    if len(pages) != 20 or any(page.get("page") != i for i, page in enumerate(pages, 1)):
        raise ValueError("Level94 PDF page archive drift")
    if (len(candidate["pdf_tables"]) != 16 or candidate["module_workload_declared"] != DECLARED
        or candidate["declared_workload_total"] != 1472 or len(candidate["tasks"]) != 146
        or len(candidate["bar_or_window_markers"]) != 104):
        raise ValueError("Level94 table/task/marker/workload drift")
    if (len(candidate["g_studies"]) != 4 or any(len(study["chords"]) != 8 or len(study["passes"]) != 6
                                                for study in candidate["g_studies"])):
        raise ValueError("G study/pass ladder drift")
    if (len(candidate["capstone_bar_plan"]) != 40
        or [x["bar"] for x in candidate["capstone_bar_plan"]] != list(range(1, 41))
        or [x["bar"] for x in candidate["capstone_bar_plan"] if x["arc_role"] == "first peak"] != list(range(13, 17))
        or [x["bar"] for x in candidate["capstone_bar_plan"] if x["arc_role"] == "second peak"] != list(range(25, 29))):
        raise ValueError("40-bar two-peak capstone drift")
    tensions = candidate["source_tensions"]
    if (len(tensions) != 3 or "1472 declared events" not in tensions[1].get("issue", "")
        or tensions[1].get("resolution") != "retain declared count separately from source-supported markers"
        or tensions[2].get("resolution") != "leave unprinted values null"):
        raise ValueError("Level94 source tension ledger drift")
    if candidate["unresolved_performance_fields"] != ["specific_target_pitch", "octave", "fret", "string",
        "tempo", "onset_q", "duration_q", "numeric_loudness", "performed_articulation", "score",
        "canonical_task_id", "canonical_event_id"]:
        raise ValueError("Level94 unresolved performance fields drift")
    row = next((r for r in source_map["rows"] if r.get("level") == 94), None)
    if (row is None or row != candidate["source_map"] or row.get("txt_sha256") != INPUTS[TXT]
        or row.get("pdf_sha256") != INPUTS[PDF] or row.get("conversion_status") != "not_converted"
        or row.get("representative_item_id") is not None or any(row.get(k) is not False for k in
            ("stable_ids_assigned", "runtime_eligible", "imported", "admitted"))):
        raise ValueError("Level94 frozen source-map boundary drift")
    arcs = candidate["pdf_tables"]["emotional_arcs"]["rows"]
    cells = narrow["module_a"]["cells"]
    if len(arcs) != len(cells) != 6 or narrow.get("canonical_ids_allocated") is not False:
        raise ValueError("P06 Module A narrow authority/arc count drift")
    windows = ("Bars 1-2", "Bars 3-4", "Bars 5-6", "Bars 7-8")
    for row_arc, cell in zip(arcs, cells):
        if row_arc["Arc"] != cell["printed_arc"] or [row_arc[w] for w in windows] != [x["printed_cell"] for x in cell["ordered_printed_windows"]]:
            raise ValueError("P06 Module A arc parity drift")


def task_field(task: dict, module: str, global_ordinal: int, lines: list[str]) -> dict:
    if (set(task) != {"local_key", "module", "kind", "source", "fields", "canonical_task_id",
                      "performed_result", "observed_score"} or task["module"] != module
        or any(task[k] is not None for k in ("canonical_task_id", "performed_result", "observed_score"))):
        raise ValueError("source task authority drift")
    page, line = task["source"]["pdf_page"], task["source"]["txt_line"]
    if not isinstance(page, int) or not 1 <= page <= 20:
        raise ValueError("task PDF page ref drift")
    if line is not None and (not isinstance(line, int) or not 1 <= line <= len(lines) or not lines[line - 1]):
        raise ValueError("task TXT line ref drift")
    return {"source_global_ordinal": global_ordinal, "source_task": task,
            "schema1_fields": {"id": None, "kind": "task", "runtime_eligible": False,
                               "source_refs": None, "performed_result": None, "observed_score": None}}


def marker_field(marker: dict, module: str) -> dict:
    expected = {"local_key", "module", "kind", "source", "bar", "chord", "target", "target_pitch_class",
                "fields", "octave", "string", "fret", "onset_q", "duration_q", "canonical_event_id", "performed_result"}
    if set(marker) != expected or marker["module"] != module:
        raise ValueError("source marker module/field drift")
    if any(marker[k] is not None for k in ("octave", "string", "fret", "onset_q", "duration_q",
                                               "canonical_event_id", "performed_result")):
        raise ValueError("source marker invented performance")
    if not isinstance(marker["bar"], int) or marker["bar"] < 1 or not 1 <= marker["source"]["pdf_page"] <= 20:
        raise ValueError("source marker bar/PDF ref drift")
    return {"source_marker": marker,
            "schema1_fields": {"event_id": None, "kind": None, "contact": None,
                               "pick": None, "pitch_binding": None, "onset_q": None, "duration_q": None}}


def project(data: dict) -> tuple[dict, dict]:
    candidate, lines = data[WHOLE], data[TXT]
    entry = identity_boundary(data)
    validate_source(candidate, data[NARROW], data[MAP], lines)
    task_ordinals = {task["local_key"]: i for i, task in enumerate(candidate["tasks"], 1)}
    marker_ordinals = {marker["local_key"]: i for i, marker in enumerate(candidate["bar_or_window_markers"], 1)}
    if len(task_ordinals) != 146 or len(marker_ordinals) != 104:
        raise ValueError("source local-key duplication")
    records = []
    seen_tasks, seen_markers = [], []
    for module in DECLARED:
        tasks = [t for t in candidate["tasks"] if t["module"] == module]
        markers = [m for m in candidate["bar_or_window_markers"] if m["module"] == module]
        if len(tasks) != TASKS[module] or len(markers) != MARKERS[module]:
            raise ValueError("module task/marker partition drift")
        source_tasks = [task_field(t, module, task_ordinals[t["local_key"]], lines) for t in tasks]
        source_markers = [marker_field(m, module) for m in markers]
        seen_tasks.extend(tasks)
        seen_markers.extend(markers)
        records.append({"source_component": module, "identity_state": "unallocated",
                        "source_declared_workload": DECLARED[module], "source_tasks": source_tasks,
                        "schema1_fields": {"id": None, "workbook_id": None, "module_id": None,
                                           "legacy_level": 94, "title": f"Level 94 component {module}",
                                           "kind": "mixed", "content_revision": None, "lineage": None,
                                           "runtime_eligible": False, "source_refs": None,
                                           "events": source_markers,
                                           "variants": [{"id": None, "source_component": module,
                                                         "source_marker_ordinals": [marker_ordinals[m["local_key"]] for m in markers],
                                                         "event_ids": None, "runtime_eligible": False}],
                                           "resource_requirements": [],
                                           "timing": {"status": "unresolved", "unit": "quarter", "fixed_bpm": None},
                                           "ambiguities": UNRESOLVED}})
    if (Counter(t["local_key"] for t in seen_tasks) != Counter(t["local_key"] for t in candidate["tasks"])
        or Counter(m["local_key"] for m in seen_markers) != Counter(m["local_key"] for m in candidate["bar_or_window_markers"])):
        raise ValueError("source task/marker union lost or duplicated")
    capstone_markers = [m for m in candidate["bar_or_window_markers"] if m["module"] == "I"]
    if ([m["bar"] for m in capstone_markers] != list(range(1, 41))
        or [(m["bar"], m["chord"], m["fields"]["arc_role"]) for m in capstone_markers]
        != [(x["bar"], x["chord"], x["arc_role"]) for x in candidate["capstone_bar_plan"]]):
        raise ValueError("capstone marker/plan parity drift")
    rubric = candidate["pdf_tables"]["completion_rubric"]["rows"]
    if len(rubric) != 8:
        raise ValueError("completion rubric drift")
    proposal = {"proposal_version": "level094-unallocated-schema1-fields.1", "wbs_id": "2.3.1.3.1",
                "classification": "Build-only, nonimportable schema1 field proposal", "legacy_level": 94,
                "canonical_ids_allocated": False, "schema1_importable": False,
                "whole_workbook_complete": False, "runtime_eligible": False, "admitted": False,
                "counts": {"components": 10, "core_tables": 16, "g_pass_ladders": 4,
                           "authored_tasks": 146, "source_supported_bar_window_markers": 104,
                           "source_declared_workload": 1472, "declared_by_module": DECLARED,
                           "tasks_by_module": TASKS, "markers_by_module": MARKERS},
                "source_pins": candidate["source_pins"], "source_map": candidate["source_map"],
                "source_archive": candidate["source_archive"], "pdf_tables": candidate["pdf_tables"],
                "read_only_narrow_evidence": candidate["read_only_narrow_evidence"],
                "source_task_order": [t["local_key"] for t in candidate["tasks"]],
                "source_marker_order": [m["local_key"] for m in candidate["bar_or_window_markers"]],
                "g_studies": candidate["g_studies"], "capstone_bar_plan": candidate["capstone_bar_plan"],
                "source_tensions": candidate["source_tensions"],
                "unresolved_performance_fields": candidate["unresolved_performance_fields"],
                "records": records}
    handoff = {"handoff_version": "level094-allocation-handoff.1", "wbs_id": "2.3.1.3.1",
               "catalog_workbook_id": entry["workbook_id"], "catalog_role": entry["catalog_role"],
               "existing_representative_item_id": None, "existing_level094_records": 0,
               "existing_level094_workbook_entities": 0, "proposed_component_partition": list(DECLARED),
               "authored_tasks": 146, "source_supported_bar_window_markers": 104,
               "source_declared_workload": 1472, "canonical_ids_allocated": False, "admitted": False,
               "required_decisions": ["Keep 1,472 workload declaration separate from 104 bar/window markers; authorize note attacks before creating playable events.",
                                      "Review all expressive choices and provide target pitches, timing, dynamic measurements and performed articulations where needed.",
                                      "Allocate stable identities after registry review, then define audio/scoring/mastery semantics before runtime admission."]}
    return proposal, handoff


def products(root: Path) -> dict[str, object]:
    proposal, handoff = project(read_inputs(root))
    manifest = {"manifest_version": "level094-input-pins.1", "inputs": [
        {"path": rel, "bytes": (root / rel).stat().st_size, "sha256": digest}
        for rel, digest in INPUTS.items()]}
    summary = {"summary_version": "level094-schema1-unallocated-summary.1",
               "proposal_sha256": sha(encoded(proposal)), "handoff_sha256": sha(encoded(handoff)),
               "authored_tasks": 146, "source_supported_bar_window_markers": 104,
               "source_declared_workload": 1472,
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
    print(f"LEVEL94 {mode.upper()} PASS tasks=146 markers=104 declared=1472 admitted=false")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("build", "verify"))
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    run(args.mode, args.root.resolve())
