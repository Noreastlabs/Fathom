#!/usr/bin/env python3
"""Project pinned whole-Level101 composition tasks into unallocated schema1 fields."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from curriculum_level101_whole_semantic_candidate import build


ROOT = Path(__file__).resolve().parents[1]
OUT_REL = Path("Build/parallel-11/2.3.1.3.1-level101-schema1-unallocated-r01")
INPUTS = {
    "Tools/curriculum_level101_whole_semantic_candidate.py": "d0e681d6246e75ea86926f3f5a49417b2630443d78fa2caa1756a916ac91f66e",
    "Results/parallel-06/exercises/conversion/20260923T201500Z-2.3.1.3.1-level101-whole-semantic-r01-results.md": "78f2297f6dd3fa72b0b4f6a1702e77a82b9be21aa12881e3f1657a02c4df4f12",
    "Build/parallel-06/2.3-level101-whole-semantic-r01/final-a.json": "9028b8cdc3c1d42ad4f8ff2e6a67f8cfd8827cea4145e54c7177a5a87ab7aa4b",
    "Build/parallel-06/2.3-level101-whole-semantic-r01/final-b.json": "9028b8cdc3c1d42ad4f8ff2e6a67f8cfd8827cea4145e54c7177a5a87ab7aa4b",
    "Content/controls/curriculum-v1/package.json": "766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255",
    "Content/controls/curriculum-v1/identity-registry.json": "5d265859e1e8a5a530a0e53d88b019a1c920f3bba6cccb4ef0fef2f7640007e5",
    "Content/controls/curriculum-v1/generation.json": "fc6cec9f9d67eb82c97c5f4c3fb95d285178fb7fce7bd147d9ae0296d21b4c1c",
    "Notes/music/guitar project/TXT version/Guitar_Exercises_Section_XV_Level_101_Larger_Form_Composition_AB_Sections_Verse_Chorus_Bridges_Transitions_Thematic_Return_and_32_Bar_Originals.txt": "8ad7e8e8ad58090b44da4bed3b141d45b4b76fd1d7a0182c0a22d3dd0f20c282",
    "Notes/music/guitar project/PDF version/Guitar_Exercises_Section_XV_Level_101_Larger_Form_Composition_AB_Sections_Verse_Chorus_Bridges_Transitions_Thematic_Return_and_32_Bar_Originals.pdf": "e184d9e8f8681d6d5b1ad3f9d1ab30d12b2fb7215756f2cae26b6c535f79698f",
    "Results/parallel-01/exercises/inventory/20260922T180500Z-2.3-curriculum-v1-source-inventory-evidence/curriculum-source-map.json": "bad5581a04f43ba8baf14db430449e1ccff5cf88f0f7e42198328073b27053d6",
}
WORKLOADS = {"A": 144, "B": 144, "C": 128, "D": 128, "E": 128,
             "F": 144, "G": 160, "H": 224, "I": 320, "J": 64}
ROWS = {"A": 13, "B": 12, "C": 14, "D": 13, "E": 14,
        "F": 6, "G": 10, "H": 24, "I": 4, "J": 8}
UNRESOLVED = [
    "Canonical workbook/module/item/event/variant IDs and lineage are not allocated.",
    "The 1584 declared events are aggregate workload, without per-task allocation or composed note attacks.",
    "No authored motif realization, note pitch/voicing, quarter-note onset/duration, fixed BPM or recorded take is supplied.",
    "G Section Energy Map Density, Register and Cadence cells are visually blank for all four rows.",
    "TXT/PDF capstone deliverable wording equivalence remains Pending; no performance or mastery is observed.",
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
    a = raw["Build/parallel-06/2.3-level101-whole-semantic-r01/final-a.json"]
    b = raw["Build/parallel-06/2.3-level101-whole-semantic-r01/final-b.json"]
    if a != b:
        raise ValueError("P06 sealed whole-Level101 twins differ")
    c = json.loads(a)
    if c != json.loads(json.dumps(build(root))):
        raise ValueError("sealed Level101 source differs from original TXT/PDF replay")
    source_map = json.loads(raw["Results/parallel-01/exercises/inventory/20260922T180500Z-2.3-curriculum-v1-source-inventory-evidence/curriculum-source-map.json"])
    row = next((x for x in source_map["rows"] if x["level"] == 101), None)
    if (row is None or row.get("section") != "XV" or row.get("wbs_owner") != "2.3.1.3.1"
            or row.get("conversion_status") != "not_converted" or row.get("admitted") is not False
            or row.get("stable_ids_assigned") is not False
            or any(row.get(f"{kind}_sha256") != c["source_identities"][kind]["sha256"] for kind in ("txt", "pdf"))):
        raise ValueError("Level101 frozen source-map status/identity drift")
    foundation = json.loads(raw["Content/controls/curriculum-v1/package.json"])
    registry = json.loads(raw["Content/controls/curriculum-v1/identity-registry.json"])
    generation = json.loads(raw["Content/controls/curriculum-v1/generation.json"])
    if len(foundation["records"]) != 659 or generation["records"] != 659:
        raise ValueError("current659 foundation drift")
    return c, row, foundation, registry


def identity_boundary(foundation: dict, registry: dict) -> dict:
    workbook = "fg:workbook:000101"
    if any(r.get("legacy_level") == 101 or r.get("workbook_id") == workbook for r in foundation["records"]):
        raise ValueError("unexpected canonical Level101 record")
    if any(e.get("id") == workbook for e in registry["entities"]):
        raise ValueError("unexpected Level101 registry entity")
    entry = next((e for e in foundation["workbook_catalog"]["entries"] if e.get("workbook_id") == workbook), None)
    if (not entry or entry.get("representative_item_id") is not None or entry.get("whole_workbook_complete") is not False
            or entry.get("admitted") is not False or entry.get("conversion_status") != "not_converted"):
        raise ValueError("Level101 source-only catalog drift")
    return entry


def validate_candidate(c: dict) -> None:
    if (c.get("level") != 101 or c.get("section") != "XV" or c.get("wbs") != "2.3.1.3.1"
            or c.get("status") != "Pending" or c.get("review") != "Pending"
            or c.get("detached_source_candidate") is not True or c.get("whole_source_semantic_projection") is not True
            or c.get("whole_workbook_accepted") is not False or c.get("schema1_imported") is not False
            or c.get("runtime_eligible") is not False or c.get("canonical_ids_allocated") is not False):
        raise ValueError("Level101 source scope/admission drift")
    if c["module_order"] != list(WORKLOADS) or c["declared_total_events"] != 1584 or c["extracted_task_rows"] != 118:
        raise ValueError("1584/118 module source total drift")
    if len(c["modules"]) != 10:
        raise ValueError("ten module count drift")
    for module in c["modules"]:
        letter = module["module"]
        if (letter not in WORKLOADS or module["declared_events"] != WORKLOADS[letter]
                or len(module["tasks"]) != ROWS[letter] or module["per_task_event_counts_known"] is not False
                or module["allocated_event_count"] is not None):
            raise ValueError(f"{letter} printed task/workload drift")
        for task in module["tasks"]:
            if (task["canonical_id"] is not None or task["declared_event_count_for_row"] is not None
                    or any(task[k] is not None for k in ("composed_notes", "motif_realization", "performed_timing", "recorded_take", "duration"))
                    or not isinstance(task["source"]["extracted_text_sha256"], str)):
                raise ValueError(f"{letter} invented task event/performance")
    if len(c["supporting_reference"]["rows"]) != 8 or len(c["txt_lines"]) != 51 or len(c["pdf_pages"]) != 21:
        raise ValueError("whole-source text/reference drift")
    g = next(m for m in c["modules"] if m["module"] == "G")
    energy = [t for t in g["tasks"] if t["source"]["page"] == 15]
    if len(energy) != 4 or [t["fields"]["Energy 1-5"] for t in energy] != ["2", "3", "4-5", "2-4"]:
        raise ValueError("G Section Energy Map printed values drift")
    if any(t["blank_cells_verified_from_render"] is not True or any(t["fields"][k] is not None for k in ("Density", "Register", "Cadence")) for t in energy):
        raise ValueError("G twelve blank cells were filled")
    h = [m for m in c["modules"] if m["module"] == "H"][0]
    if len(c["h_studies"]) != 4 or [s["study"] for s in c["h_studies"]] != [1, 2, 3, 4]:
        raise ValueError("H four study distinction drift")
    if {t["study"]: [x["fields"]["Pass"] for x in h["tasks"] if x["study"] == t["study"]] for t in c["h_studies"]} != {i: [str(x) for x in range(1, 7)] for i in range(1, 5)}:
        raise ValueError("H six-pass study structure drift")
    i = next(m for m in c["modules"] if m["module"] == "I")
    if [t["fields"]["Bars"] for t in i["tasks"]] != ["1-8", "9-16", "17-24", "25-32"]:
        raise ValueError("I 32-bar coverage drift")
    if [t["fields"]["Section"] for t in i["tasks"]] != ["A", "B", "Bridge", "A'"]:
        raise ValueError("I section order drift")
    deliverables = c["capstone_deliverables"]
    if (deliverables["wording_equivalence_review"] != "Pending" or deliverables["txt"] == deliverables["pdf"]
            or "motif," not in deliverables["txt"] or "motif statement" not in deliverables["pdf"]
            or "recorded take" not in deliverables["txt"] or "recorded take" not in deliverables["pdf"]):
        raise ValueError("TXT/PDF capstone wording distinction drift")
    mastery = c["mastery"]
    if mastery["minimum"] != "14/16 or better" or mastery["protected_zero_domains"] != ["identity", "form", "thematic return", "performance"]:
        raise ValueError("raw mastery gate drift")
    unresolved = c["unresolved"]
    if (unresolved["canonical_identity"] is not None or unresolved["composed_notes_and_motifs"] is not None
            or unresolved["per_task_event_counts"] is not None or unresolved["performed_timing"] is not None
            or unresolved["recorded_take"] is not None or unresolved["runtime_admission"] is not False
            or unresolved["txt_pdf_capstone_wording_equivalence"] != "Pending"):
        raise ValueError("source unresolved claims drift")


def project(c: dict, map_row: dict, foundation: dict, registry: dict) -> tuple[dict, dict]:
    validate_candidate(c)
    entry = identity_boundary(foundation, registry)
    records = []
    task_proposals = []
    for module in c["modules"]:
        letter = module["module"]
        tasks = []
        for task in module["tasks"]:
            projection = {"source_component": letter, "source_task": task,
                          "schema1_fields": {"id": None, "workbook_id": None, "module_id": None,
                                             "legacy_level": 101, "kind": "task",
                                             "content_revision": None, "lineage": None,
                                             "source_refs": [f"L101-PDF-p{task['source']['page']}-r{task['source']['row_ordinal']}"],
                                             "events": [], "variants": [], "runtime_eligible": False,
                                             "admitted": False, "performed_result": None}}
            tasks.append(projection)
            task_proposals.append(projection)
        refs = [f"L101-TXT-L{module['txt_line']}", f"L101-PDF-p{module['pdf']['page']}-r{module['pdf']['table_row']}"]
        refs += sorted({f"L101-PDF-p{t['source']['page']}" for t in module["tasks"]})
        records.append({"source_component": letter, "source_heading": module["title"],
                        "declared_workload_events": module["declared_events"],
                        "printed_task_row_count": len(tasks), "task_proposals": tasks,
                        "source_pdf_declaration": module["pdf"], "source_txt_line": module["txt_line"],
                        "identity_state": "unallocated",
                        "schema1_fields": {"id": None, "workbook_id": None, "module_id": None,
                                           "legacy_level": 101, "title": f"Level 101 component {letter}: {module['title']}",
                                           "kind": "task", "content_revision": None, "lineage": None,
                                           "status": "unallocated_source_projection", "runtime_eligible": False,
                                           "admitted": False, "source_refs": refs,
                                           "control_scope": {"extent": "whole_source_component_proposal",
                                                             "local_case": letter,
                                                             "declared_workload_events": module["declared_events"],
                                                             "source_event_count": None,
                                                             "whole_workbook_complete": False,
                                                             "unresolved": UNRESOLVED},
                                           "events": [], "variants": [], "resource_requirements": [],
                                           "timing": {"status": "unresolved", "unit": "quarter",
                                                      "fixed_bpm": None, "onset_q": None, "duration_q": None},
                                           "ambiguities": UNRESOLVED}})
    proposal = {"proposal_version": "level101-unallocated-schema1-fields.1", "wbs_id": "2.3.1.3.1",
                "classification": "Build-only, nonimportable schema1 task-field proposal",
                "legacy_level": 101, "canonical_ids_allocated": False, "schema1_importable": False,
                "whole_workbook_complete": False, "runtime_eligible": False, "admitted": False,
                "mastery_observed": None, "recorded_take_observed": None,
                "counts": {"provisional_components": 10, "printed_task_rows": 118,
                           "supporting_reference_rows": 8, "declared_workload_events": 1584,
                           "authored_note_events": 0, "energy_map_blank_cells": 12},
                "source_identities": c["source_identities"], "source_map_row": map_row,
                "txt_lines": c["txt_lines"], "pdf_pages": c["pdf_pages"],
                "supporting_reference": c["supporting_reference"], "h_studies": c["h_studies"],
                "capstone_deliverables": c["capstone_deliverables"],
                "capstone_txt_lines": c["capstone_txt_lines"], "mastery": c["mastery"],
                "unresolved_source_claims": c["unresolved"],
                "task_field_proposals": task_proposals, "records": records}
    handoff = {"handoff_version": "level101-allocation-handoff.1", "wbs_id": "2.3.1.3.1",
               "catalog_workbook_id_read_only": entry["workbook_id"],
               "existing_level101_records": 0, "existing_level101_workbook_entities": 0,
               "printed_task_rows": 118, "declared_workload_events": 1584,
               "proposed_component_partition": list(WORKLOADS),
               "canonical_ids_allocated": False, "admitted": False,
               "required_decisions": [
                   "Review TXT/PDF capstone deliverable wording equivalence without rewriting either source list.",
                   "Allocate stable identities and lineage only through the canonical owner.",
                   "Keep twelve visually blank Energy Map cells unfilled until authored composition evidence exists.",
                   "Specify composed notes, task event allocation, timing and recorded take before native import.",
                   "Obtain actual mastery scores and Curriculum disposition before completion or admission claims."]}
    return proposal, handoff


def products(root: Path) -> dict[str, object]:
    c, map_row, foundation, registry = read_inputs(root)
    proposal, handoff = project(c, map_row, foundation, registry)
    manifest = {"manifest_version": "level101-schema1-input-pins.1", "inputs": [
        {"path": rel, "bytes": (root / rel).stat().st_size, "sha256": sha} for rel, sha in INPUTS.items()]}
    summary = {"summary_version": "level101-schema1-unallocated-summary.1",
               "proposal_sha256": digest(encoded(proposal)), "handoff_sha256": digest(encoded(handoff)),
               "printed_task_rows": 118, "declared_workload_events": 1584,
               "authored_note_events": 0, "native_run": False,
               "runtime_eligible": False, "admitted": False}
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
    print("LEVEL101 " + mode.upper() + " PASS tasks=118 declared=1584 note_events=0 admitted=false")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("build", "verify"))
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    run(args.mode, args.root.resolve())


if __name__ == "__main__":
    main()
