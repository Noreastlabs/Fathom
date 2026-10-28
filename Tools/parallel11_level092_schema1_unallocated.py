#!/usr/bin/env python3
"""Project whole-Level92 PDF source tasks into unallocated schema1 fields."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from curriculum_level092_whole_candidate import build_candidate


ROOT = Path(__file__).resolve().parents[1]
OUT_REL = Path("Build/parallel-11/2.3.1.3.1-level092-schema1-unallocated-r01")
INPUTS = {
    "Tools/curriculum_level092_whole_candidate.py": "234f41b48da0c420971a1e8e283e7aa23159b39bd38b843cdd00ccd438df93d5",
    "Results/parallel-11/curriculum/20260923T170700Z-2.3-level092-whole-r01-results.md": "254bf9602c5336eabd646915224d17049d07652081d75940778eca01cd83e145",
    "Build/parallel-11/2.3.1.3.1-level092-whole-r01/candidate-b.json": "4f100dd3880d9c2844b8c903e09c85b459a1a51f4c05b9f4fac33b0a2f8c3b46",
    "Build/parallel-11/2.3.1.3.1-level092-whole-r01/candidate-c.json": "4f100dd3880d9c2844b8c903e09c85b459a1a51f4c05b9f4fac33b0a2f8c3b46",
    "Content/controls/curriculum-v1/package.json": "766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255",
    "Content/controls/curriculum-v1/identity-registry.json": "5d265859e1e8a5a530a0e53d88b019a1c920f3bba6cccb4ef0fef2f7640007e5",
    "Content/controls/curriculum-v1/generation.json": "fc6cec9f9d67eb82c97c5f4c3fb95d285178fb7fce7bd147d9ae0296d21b4c1c",
    "Notes/music/guitar project/TXT version/Guitar_Exercises_Section_XIII_Level_92_Rakes_Grace_Notes_Double_Stop_Slides_Harmonics_Volume_Swells_Muted_Attacks_and_Articulation_Chains.txt": "67ddb7a03c84f727f78ced578853b21b2ecf22eb81a72deedfe1d16bd9ab8e1a",
    "Notes/music/guitar project/PDF version/Guitar_Exercises_Section_XIII_Level_92_Rakes_Grace_Notes_Double_Stop_Slides_Harmonics_Volume_Swells_Muted_Attacks_and_Articulation_Chains.pdf": "c2068c5c2a52366fcd53526a0ae32a82a4aaabde9252be17599726bf8f01beff",
    "Results/parallel-01/exercises/inventory/20260922T180500Z-2.3-curriculum-v1-source-inventory-evidence/curriculum-source-map.json": "bad5581a04f43ba8baf14db430449e1ccff5cf88f0f7e42198328073b27053d6",
}
WORKLOADS = {"A": 128, "B": 128, "C": 144, "D": 112, "E": 112,
             "F": 112, "G": 112, "H": 160, "I": 256, "J": 64}
ROWS = {"A": 14, "B": 14, "C": 14, "D": 6, "E": 8, "F": 8,
        "G": 8, "H": 16, "I": 8, "J": 8}
SCORED = ["rake control", "ornament timing", "double-stop clarity", "harmonic production",
          "volume-swell timing", "phrase-function choice", "density control", "recovery"]
NO_ZERO = ["target timing", "harmonic clarity", "phrase-function choice", "recovery"]
AMBIGUITIES = ["PDF_only_task_expansion", "workload_without_printed_note_events",
               "mastery_scale_undefined", "mastery_no_zero_label_mismatch"]
UNRESOLVED = [
    "Canonical workbook/module/item/event/variant IDs and lineage are not allocated.",
    "The 1328 declared workload events are not 1328 printed playable attacks or allocated per task row.",
    "No exact note pitch/voicing, onset/duration, fixed BPM, performed sequence or observed capstone is established.",
    "Scored category labels and no-zero gate labels differ; no exact mapping or score descriptor is authored.",
    "No observed score, two-day repeatability, mastery, native import or Curriculum admission is established.",
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


def read_inputs(root: Path) -> tuple[dict, dict, dict]:
    raw = {rel: pinned(root, rel, sha) for rel, sha in INPUTS.items()}
    a = raw["Build/parallel-11/2.3.1.3.1-level092-whole-r01/candidate-b.json"]
    b = raw["Build/parallel-11/2.3.1.3.1-level092-whole-r01/candidate-c.json"]
    if a != b:
        raise ValueError("P11 sealed source candidate twins differ")
    c = json.loads(a)
    if c != json.loads(json.dumps(build_candidate(root))):
        raise ValueError("sealed Level92 candidate differs from original TXT/PDF/source-map replay")
    foundation = json.loads(raw["Content/controls/curriculum-v1/package.json"])
    registry = json.loads(raw["Content/controls/curriculum-v1/identity-registry.json"])
    generation = json.loads(raw["Content/controls/curriculum-v1/generation.json"])
    if len(foundation["records"]) != 659 or generation["records"] != 659:
        raise ValueError("current659 foundation drift")
    return c, foundation, registry


def identity_boundary(foundation: dict, registry: dict) -> dict:
    workbook = "fg:workbook:000092"
    if any(r.get("legacy_level") == 92 or r.get("workbook_id") == workbook for r in foundation["records"]):
        raise ValueError("unexpected canonical Level92 record")
    if any(e.get("id") == workbook for e in registry["entities"]):
        raise ValueError("unexpected Level92 registry workbook entity")
    entry = next((e for e in foundation["workbook_catalog"]["entries"] if e.get("workbook_id") == workbook), None)
    if (not entry or entry.get("representative_item_id") is not None or entry.get("whole_workbook_complete") is not False
            or entry.get("admitted") is not False or entry.get("conversion_status") != "not_converted"):
        raise ValueError("Level92 source-only catalog drift")
    unrelated_item = next((e for e in registry["entities"] if e.get("id") == "fg:item:000092"), None)
    unrelated_module = next((e for e in registry["entities"] if e.get("id") == "fg:module:000092"), None)
    if (not unrelated_item or unrelated_item.get("parent") != "fg:module:000092"
            or not unrelated_module or unrelated_module.get("parent") != "fg:workbook:000001"
            or "Exercise0803432" not in unrelated_item.get("label", "")):
        raise ValueError("numeric item 000092 unrelated lineage drift")
    return entry


def validate_candidate(c: dict) -> None:
    if (c.get("schema") != "fathom.level092.detached-source-task-candidate.1" or c.get("wbs") != "2.3.1.3.1"
            or c.get("section") != "XIII" or c.get("level") != 92
            or c.get("status") != "non_admitted" or c.get("admitted") is not False):
        raise ValueError("Level92 source scope/admission drift")
    for key in ("canonical_id", "exercise_id", "onset_q", "duration_q", "fixed_bpm", "executable_events",
                "sounding_midi_events", "performed_event_count", "rubric_outcome"):
        if c.get(key) is not None:
            raise ValueError(f"invented source performance/identity: {key}")
    if c["declared_workload_by_module"] != WORKLOADS or c["declared_workload_total"] != 1328:
        raise ValueError("1328 declared workload drift")
    if list(c["modules"]) != list(WORKLOADS):
        raise ValueError("A–J module order drift")
    for letter, module in c["modules"].items():
        if module["declared_events"] != WORKLOADS[letter] or module["per_task_event_allocation"] is not None:
            raise ValueError(f"{letter} invented event allocation")
        rows = [row for table in module["tables"] for row in table["rows"]]
        if len(rows) != ROWS[letter] or any(row["declared_events_for_row"] is not None or row["performed_events"] is not None for row in rows):
            raise ValueError(f"{letter} task row drift")
    if len(c["symbol_legend"]) != 8 or any(row["performed_events"] is not None for row in c["symbol_legend"]):
        raise ValueError("eight symbol legend rows drift")
    if len(c["txt_full_lines"]) != 44 or len(c["pdf_full_extracted_pages"]) != 16:
        raise ValueError("whole-source text archive drift")
    cap = c["capstone"]
    if cap["printed_bars"] != 32 or len(cap["section_blocks"]) != 8 or len(cap["passes"]) != 5:
        raise ValueError("capstone structure drift")
    if sum(len(block["semantic"]["chords"]) for block in cap["section_blocks"]) != 32:
        raise ValueError("32 printed capstone chords drift")
    m = c["mastery"]
    if (m["categories"] != SCORED or m["no_zero_categories"] != NO_ZERO
            or m["required_score"] != 14 or m["maximum_score"] != 16
            or m["separate_days"] != 2 or m["score_descriptors"] is not None):
        raise ValueError("raw mastery gate/category distinction drift")
    if [x["kind"] for x in c["source_ambiguities"]] != AMBIGUITIES or any(x["status"] != "pending_curriculum_review" for x in c["source_ambiguities"]):
        raise ValueError("four source ambiguities drift")
    mismatch = c["source_ambiguities"][-1]["detail"]
    if not all(word in mismatch for word in ("target timing", "harmonic clarity", "ornament timing", "harmonic production")):
        raise ValueError("no-zero label mismatch lost")


def project(c: dict, foundation: dict, registry: dict) -> tuple[dict, dict]:
    validate_candidate(c)
    entry = identity_boundary(foundation, registry)
    records = []
    task_proposals = []
    for letter, module in c["modules"].items():
        row_proposals = []
        for table in module["tables"]:
            for row in table["rows"]:
                task = {"source_component": letter, "source_page": table["page"],
                        "source_row": row, "schema1_fields": {
                            "id": None, "workbook_id": None, "module_id": None, "legacy_level": 92,
                            "kind": "task", "content_revision": None, "lineage": None,
                            "source_refs": [row["pdf_ref"]], "events": [], "variants": [],
                            "runtime_eligible": False, "admitted": False,
                            "performed_event_count": None, "observed_score": None,
                        }}
                row_proposals.append(task)
                task_proposals.append(task)
        refs = [module["txt_ref"], module["pdf_overview_ref"]] + [f"L92-PDF-p{p}" for p in module["pdf_pages"]]
        records.append({
            "source_component": letter, "source_heading": module["name"],
            "source_task_tables": module["tables"], "declared_workload_events": WORKLOADS[letter],
            "printed_task_row_count": ROWS[letter], "task_proposals": row_proposals,
            "identity_state": "unallocated",
            "schema1_fields": {
                "id": None, "workbook_id": None, "module_id": None, "legacy_level": 92,
                "title": f"Level 92 component {letter}: {module['name']}", "kind": "task",
                "content_revision": None, "lineage": None, "status": "unallocated_source_projection",
                "runtime_eligible": False, "admitted": False,
                "source_refs": refs, "authored_text_refs": refs,
                "control_scope": {"extent": "whole_source_component_proposal", "local_case": letter,
                                  "declared_workload_events": WORKLOADS[letter], "source_event_count": None,
                                  "whole_workbook_complete": False, "unresolved": UNRESOLVED},
                "events": [], "variants": [], "resource_requirements": [],
                "timing": {"status": "unresolved", "unit": "quarter", "fixed_bpm": None,
                           "onset_q": None, "duration_q": None},
                "rubric": c["mastery"] if letter == "J" else None,
                "ambiguities": UNRESOLVED,
            },
        })
    proposal = {
        "proposal_version": "level092-unallocated-schema1-fields.1", "wbs_id": "2.3.1.3.1",
        "classification": "Build-only, nonimportable schema1 task-field proposal", "legacy_level": 92,
        "canonical_ids_allocated": False, "schema1_importable": False,
        "whole_workbook_complete": False, "runtime_eligible": False, "admitted": False,
        "mastery_observed": None,
        "counts": {"provisional_components": 10, "printed_task_rows": 104, "symbol_legend_rows": 8,
                   "declared_workload_events": 1328, "authored_note_events": 0,
                   "capstone_printed_bars": 32, "capstone_printed_chords": 32,
                   "capstone_instructional_passes": 5},
        "source": c["source"], "source_map_row": c["source_map_row"],
        "txt_full_lines": c["txt_full_lines"], "pdf_full_extracted_pages": c["pdf_full_extracted_pages"],
        "symbol_legend": c["symbol_legend"], "capstone": c["capstone"], "mastery": c["mastery"],
        "source_ambiguities": c["source_ambiguities"],
        "declared_workload_by_module": c["declared_workload_by_module"],
        "unrelated_registry_numeric_item_read_only": {"id": "fg:item:000092", "source_level": 80,
                                                      "is_level092_identity": False},
        "task_field_proposals": task_proposals, "records": records,
    }
    handoff = {
        "handoff_version": "level092-allocation-handoff.1", "wbs_id": "2.3.1.3.1",
        "catalog_workbook_id_read_only": entry["workbook_id"], "existing_level092_records": 0,
        "existing_level092_workbook_entities": 0, "existing_level092_representative": None,
        "unrelated_numeric_item_000092_is_level080": True,
        "printed_task_rows": 104, "declared_workload_events": 1328,
        "proposed_component_partition": list(WORKLOADS), "canonical_ids_allocated": False, "admitted": False,
        "required_decisions": [
            "Review all four source ambiguities, especially the no-zero versus scored-category label mismatch.",
            "Allocate Level92 stable identities and lineage only through the canonical owner; do not reuse numeric item 000092.",
            "Resolve concrete playable pitch, voicing, timing and task event allocation before native import.",
            "Require observed two-day scores and performance evidence before mastery or admission claims.",
        ],
    }
    return proposal, handoff


def products(root: Path) -> dict[str, object]:
    c, foundation, registry = read_inputs(root)
    proposal, handoff = project(c, foundation, registry)
    manifest = {"manifest_version": "level092-schema1-input-pins.1", "inputs": [
        {"path": rel, "bytes": (root / rel).stat().st_size, "sha256": sha} for rel, sha in INPUTS.items()]}
    summary = {"summary_version": "level092-schema1-unallocated-summary.1",
               "proposal_sha256": digest(encoded(proposal)), "handoff_sha256": digest(encoded(handoff)),
               "printed_task_rows": 104, "declared_workload_events": 1328,
               "authored_note_events": 0, "native_run": False, "runtime_eligible": False, "admitted": False}
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
    print(f"LEVEL92 {mode.upper()} PASS tasks=104 declared=1328 note_events=0 admitted=false")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("build", "verify"))
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    run(args.mode, args.root.resolve())


if __name__ == "__main__":
    main()
