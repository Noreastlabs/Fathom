#!/usr/bin/env python3
"""Project sealed Level78 tasks into nonimportable, unallocated schema1 fields."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from curriculum_level078_whole_candidate import build_candidate


ROOT = Path(__file__).resolve().parents[1]
OUT_REL = Path("Build/parallel-06/level078-schema1-unallocated-r01")
INPUTS = {
    "Build/parallel-09/2.3.1.3.1-level078-whole-r01/level078-whole-candidate-02.json": "301109e7f26bd45b7d87997a1a4331a89ffecfad47dd34ffdffe36b71fae1ddc",
    "Tools/curriculum_level078_whole_candidate.py": "d6f3404d350f7cb1b95c6751e363f81eb03f8b0baf4aac47f5495ab258314604",
    "Content/controls/curriculum-v1/package.json": "766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255",
    "Content/controls/curriculum-v1/identity-registry.json": "5d265859e1e8a5a530a0e53d88b019a1c920f3bba6cccb4ef0fef2f7640007e5",
    "Results/primary/20260912T100538Z-2.1.1.2.1-r02-evidence/schema-freeze.json": "0659fa962a5c933a2bcf3045772b6fe5b05b4deefb3511f5dcb68af51088de95",
}
COUNTS = {"A": 96, "B": 96, "C": 96, "D": 96, "E": 128, "F": 128,
          "G": 128, "H": 128}
TASK_COUNTS = {"A": 24, "B": 12, "C": 24, "D": 16, "E": 12, "F": 16,
               "G": 24, "H": 16}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def encoded(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False,
                       separators=(",", ":")) + "\n").encode()


def read_inputs(root: Path) -> tuple[dict, dict, dict]:
    raw = {}
    for rel, expected in INPUTS.items():
        path = root / rel
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"missing or symlink input: {rel}")
        data = path.read_bytes()
        if digest(data) != expected:
            raise ValueError(f"input drift: {rel}")
        raw[rel] = data
    whole = json.loads(raw[next(iter(INPUTS))])
    if whole != build_candidate():
        raise ValueError("sealed candidate differs from original TXT/PDF replay")
    package = json.loads(raw[list(INPUTS)[2]])
    registry = json.loads(raw[list(INPUTS)[3]])
    freeze = json.loads(raw[list(INPUTS)[4]])
    if freeze.get("decision") != "Technical schema1 FROZEN" or freeze.get("schema_version") != "1.0.0-curriculum-candidate":
        raise ValueError("schema freeze drift")
    return whole, package, registry


def identity_boundary(package: dict, registry: dict) -> dict:
    wid = "fg:workbook:000078"
    if any(r.get("legacy_level") == 78 or r.get("workbook_id") == wid
           for r in package["records"]):
        raise ValueError("unexpected canonical Level78 record")
    if any(e.get("id") == wid for e in registry["entities"]):
        raise ValueError("unexpected Level78 registry entity")
    entries = [e for e in package["workbook_catalog"]["entries"]
               if e.get("workbook_id") == wid]
    if len(entries) != 1:
        raise ValueError("Level78 catalog identity drift")
    entry = entries[0]
    if (entry.get("conversion_status") != "not_converted"
            or entry.get("whole_workbook_complete") is not False
            or entry.get("admitted") is not False
            or entry.get("runtime_eligible") is not False
            or entry.get("representative_item_id") is not None):
        raise ValueError("Level78 source-only catalog drift")
    return entry


def unresolved_event(slot: dict) -> dict:
    if (slot.get("status") != "source_count_slot_unresolved"
            or any(slot.get(k) is not None for k in (
                "printed_note", "string", "fret", "onset_q", "duration_q",
                "canonical_event_id", "performed_result"))):
        raise ValueError("source event unexpectedly resolved")
    if slot.get("module") not in COUNTS or not 1 <= slot.get("pdf_page", 0) <= 20:
        raise ValueError("source event boundary drift")
    return {
        "source_slot": slot,
        "performed_result": None,
        "schema1_fields": {
            "event_id": None, "kind": None, "attack": None,
            "spelling": None, "midi": None, "string": None, "fret": None,
            "finger": None, "degree_contexts": {}, "onset_q": None,
            "duration_q": None, "tie_from": None,
        },
    }


def project(whole: dict, package: dict, registry: dict) -> tuple[dict, dict]:
    catalog = identity_boundary(package, registry)
    if (whole.get("schema") != "fathom-level078-whole-detached-task-candidate-v1"
            or whole.get("wbs_id") != "2.3.1.3.1" or whole.get("level") != 78
            or whole.get("complete_written_workload_events") != 896
            or whole.get("module_written_event_counts") != COUNTS
            or list(whole.get("modules", {})) != list(COUNTS)):
        raise ValueError("whole Level78 scope/count drift")
    for key in ("admitted", "imported", "runtime_eligible", "runtime_admitted", "curriculum_signoff"):
        if whole.get(key) is not False:
            raise ValueError(f"source admission drift: {key}")
    for key in ("canonical_item_id", "canonical_variant_id", "fixed_bpm", "note_per_click", "onset_q", "duration_q", "performed_result"):
        if whole.get(key) is not None:
            raise ValueError(f"source allocation/timing drift: {key}")
    if (len(whole["source_count_ambiguities"]) != 1
            or {x["page"] for x in whole["pdf_visual_limits"]} != {16, 18, 19, 20}):
        raise ValueError("source ambiguity/visual limit drift")
    cap = whole["capstone"]
    if (cap["base_form_events"] != 64 or cap["written_module_h_events"] != 128
            or cap["pdf_events_each_pass"] != 64
            or cap["five_passes_are_written_event_multiplier"] is not False
            or len(cap["five_performance_passes"]) != 5
            or len(cap["pdf_form_cue_tasks"]) != 16
            or len(cap["ensemble_role_labs"]) != 8
            or cap["performed_score"] is not None
            or cap["pdf_worksheet"]["performed_block_scores"] is not None):
        raise ValueError("H capstone count/performance boundary drift")
    slots = whole["written_event_slots"]
    if len(slots) != 896:
        raise ValueError("written event slot count drift")
    grouped = {m: [] for m in COUNTS}
    for slot in slots:
        grouped[slot["module"]].append(unresolved_event(slot))
    if {m: len(v) for m, v in grouped.items()} != COUNTS:
        raise ValueError("module slot count drift")
    h_unassigned = [e for e in grouped["H"] if e["source_slot"]["family"] == "unallocated_written_count"]
    if (len(h_unassigned) != 64
            or [e["source_slot"]["record_slot"] for e in h_unassigned] != list(range(1, 65))
            or any(e["source_slot"]["record_txt_line"] is not None for e in h_unassigned)
            or any(e["source_slot"]["record_order"] is not None for e in h_unassigned)):
        raise ValueError("H unassigned 64-slot boundary drift")
    records = []
    total_tasks = 0
    for module in COUNTS:
        source_module = whole["modules"][module]
        tasks = source_module["records"]
        if (source_module["written_event_count"] != COUNTS[module]
                or len(tasks) != TASK_COUNTS[module]
                or source_module["module"] != module):
            raise ValueError("module task scope drift")
        a, b = source_module["txt_line_span"]
        if not 1 <= a <= b <= 218:
            raise ValueError("source TXT span drift")
        variants = []
        assigned = set()
        for source_task in tasks:
            if (source_task["module"] != module or source_task["canonical_item_id"] is not None
                    or source_task["performed_result"] is not None
                    or not a <= source_task["txt_line"] <= b
                    or source_task["pdf_page"] not in source_module["pdf_pages"]):
                raise ValueError("source task identity/provenance drift")
            ordinals = [i for i, event in enumerate(grouped[module], 1)
                        if event["source_slot"]["family"] == source_task["family"]
                        and event["source_slot"]["record_order"] == source_task["family_order"]
                        and event["source_slot"]["record_txt_line"] == source_task["txt_line"]]
            if len(ordinals) != source_task["source_described_events"]:
                raise ValueError("task/slot count parity drift")
            if assigned.intersection(ordinals):
                raise ValueError("duplicate task/slot assignment")
            assigned.update(ordinals)
            variants.append({"id": None, "source_task": source_task,
                             "source_event_ordinals": ordinals, "event_ids": None,
                             "runtime_eligible": False})
        expected_assigned = COUNTS[module] - (64 if module == "H" else 0)
        if len(assigned) != expected_assigned:
            raise ValueError("module task/slot partition drift")
        total_tasks += len(variants)
        records.append({
            "source_component": module, "identity_state": "unallocated",
            "source_module_title": source_module["title"],
            "source_txt_line_span": source_module["txt_line_span"],
            "source_pdf_pages": source_module["pdf_pages"],
            "source_pdf_task_texts": source_module["pdf_task_texts"],
            "schema1_fields": {
                "id": None, "workbook_id": None, "module_id": None,
                "legacy_level": 78, "title": source_module["title"],
                "kind": "mixed", "content_revision": None, "lineage": None,
                "runtime_eligible": False, "source_refs": None,
                "events": grouped[module], "variants": variants,
                "unassigned_source_event_ordinals": [i for i in range(1, len(grouped[module]) + 1)
                                                     if i not in assigned],
                "resource_requirements": [],
                "timing": {"status": "unresolved", "unit": "quarter", "fixed_bpm": None},
                "ambiguities": ["canonical identities and lineage unallocated",
                                "note-level event pitch, string, fret and kind unresolved",
                                "onset/duration, fixed BPM and performed result unresolved"]
                + (whole["source_count_ambiguities"] if module == "H" else []),
            },
        })
    if total_tasks != 144 or sum(len(r["schema1_fields"]["events"]) for r in records) != 896:
        raise ValueError("whole task/event parity drift")
    proposal = {
        "proposal_version": "level078-unallocated-schema1-fields.1", "wbs_id": "2.3.1.3.1",
        "classification": "Build-only, nonimportable schema1 field proposal",
        "legacy_level": 78, "canonical_ids_allocated": False,
        "schema1_importable": False, "whole_workbook_complete": False,
        "runtime_eligible": False, "admitted": False,
        "counts": {"provisional_components": 8, "authored_task_records": 144,
                   "source_described_written_event_slots": 896,
                   "module_h_unassigned_written_slots": 64,
                   "tasks_by_module": TASK_COUNTS, "events_by_module": COUNTS},
        "source": whole["source"], "source_catalog_level": catalog,
        "source_catalog_boundary": whole["catalog_boundary"],
        "source_map_boundary": whole["source_map_boundary"],
        "source_count_ambiguities": whole["source_count_ambiguities"],
        "pdf_visual_limits": whole["pdf_visual_limits"],
        "control_loop": whole["control_loop"], "capstone": cap,
        "records": records,
    }
    handoff = {
        "handoff_version": "level078-allocation-handoff.1", "wbs_id": "2.3.1.3.1",
        "catalog_workbook_id": catalog["workbook_id"],
        "existing_level078_records": 0, "existing_level078_workbook_entities": 0,
        "authored_task_records": 144, "source_described_written_event_slots": 896,
        "module_h_unassigned_written_slots": 64,
        "proposed_component_partition": list(COUNTS),
        "canonical_ids_allocated": False, "admitted": False,
        "required_decisions": [
            "Disposition H's 64 unassigned written-event slots and five-pass count wording.",
            "Review PDF page 16/18/19/20 visual overlap limits against original pages.",
            "Allocate stable workbook/module/item/event/variant identities and revision lineage.",
            "Specify playable pitch/TAB, timing, role changes and scoring before native import.",
            "Review musical correctness and mastery under Curriculum authority.",
        ],
    }
    return proposal, handoff


def products(root: Path) -> dict[str, object]:
    whole, package, registry = read_inputs(root)
    proposal, handoff = project(whole, package, registry)
    manifest = {"manifest_version": "level078-input-pins.1", "inputs": [
        {"path": rel, "bytes": (root / rel).stat().st_size, "sha256": sha}
        for rel, sha in INPUTS.items()]}
    summary = {"summary_version": "level078-schema1-unallocated-summary.1",
               "proposal_sha256": digest(encoded(proposal)),
               "handoff_sha256": digest(encoded(handoff)),
               "authored_task_records": 144,
               "source_described_written_event_slots": 896,
               "module_h_unassigned_written_slots": 64,
               "native_run": False, "runtime_eligible": False, "admitted": False}
    return {"field-proposal.json": proposal, "allocation-handoff.json": handoff,
            "input-manifest.json": manifest, "summary.json": summary}


def run(mode: str, root: Path) -> None:
    git_root = Path(subprocess.run(["git", "rev-parse", "--show-toplevel"],
                                   cwd=root, capture_output=True, text=True,
                                   check=True).stdout.strip()).resolve(strict=True)
    if root != git_root:
        raise ValueError("root must equal Git top level")
    built = products(root)
    out = root
    for part in OUT_REL.parts:
        out /= part
        if out.is_symlink():
            raise ValueError("output symlink path")
    if mode == "build":
        if out.exists():
            raise ValueError("output already exists")
        out.mkdir(parents=True)
        for name, value in built.items():
            with (out / name).open("xb") as f:
                f.write(encoded(value))
    else:
        contents = {p.name for p in out.iterdir()}
        if contents not in (set(built), set(built) | {"focused-tests.log"}):
            raise ValueError("output file set drift")
        if "focused-tests.log" in contents and (out / "focused-tests.log").is_symlink():
            raise ValueError("output test log symlink")
        for name, value in built.items():
            path = out / name
            if path.is_symlink() or path.read_bytes() != encoded(value):
                raise ValueError(f"output drift: {name}")
    print("LEVEL78 " + mode.upper() + " PASS tasks=144 slots=896 H-unassigned=64 admitted=false")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("mode", choices=("build", "verify"))
    ap.add_argument("--root", type=Path, default=ROOT)
    args = ap.parse_args()
    run(args.mode, args.root.resolve(strict=True))


if __name__ == "__main__":
    main()
