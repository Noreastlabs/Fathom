#!/usr/bin/env python3
"""Project Level97's pinned whole-source rows to detached unallocated schema1 fields."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path

import curriculum_level097_whole_candidate as source

ROOT = Path(__file__).resolve().parents[1]
OUT = Path("Build/parallel-13/level097-schema1-unallocated-r01")
CANDIDATE = Path("Build/parallel-11/2.3.1.3.1-level097-whole-r01/candidate-b.json")
PINS = {
    CANDIDATE: "6d677aae9a7cbc710565b972ef1450f04cb0bd04f9879b877572ed2738d8de5f",
    Path("Tools/curriculum_level097_whole_candidate.py"): "27263b66ed7cb80fabade67a48b95bd60bbdd1197b9f293a004a7d409746ca0d",
    Path("Results/parallel-11/curriculum/20260923T171600Z-2.3-level097-whole-r01-results.md"): "e61084d59c9e40765c36da51dec37f97deb41296d611d3e05cd878eb1375dc5f",
    Path("Results/primary/20260912T100538Z-2.1.1.2.1-r02-evidence/schema-freeze.json"): "0659fa962a5c933a2bcf3045772b6fe5b05b4deefb3511f5dcb68af51088de95",
}
EVENTS = dict(zip(source.KEYS, source.EVENTS))
UNRESOLVED = [
    "1424 source events are module workload declarations without per-row allocation",
    "no source audio supplied; no observed root, harmony, groove, riff or performance",
    "no complete playable pitch/route/onset/duration/fixed-BPM notation",
    "whole-workbook identity, lineage, revision, Curriculum review and admission pending",
]


class ProposalError(ValueError):
    pass


def need(ok: bool, code: str) -> None:
    if not ok:
        raise ProposalError(code)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def encoded(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def check_pins() -> None:
    for rel, expected in PINS.items():
        path = ROOT / rel
        need(path.is_file() and not path.is_symlink() and
             path.resolve().is_relative_to(ROOT.resolve()), f"INPUT_PATH {rel}")
        need(sha(path.read_bytes()) == expected, f"INPUT_PIN {rel}")


def foundation_status() -> dict:
    package = json.loads((ROOT / "Content/controls/curriculum-v1/package.json").read_text())
    entries = [e for e in package["workbook_catalog"]["entries"]
               if e["workbook_id"] == "fg:workbook:000097"]
    reps = [r for r in package["records"] if r.get("legacy_level") == 97]
    need(len(package["records"]) == 659 and len(entries) == 1 and len(reps) == 1,
         "FOUNDATION_SCOPE")
    entry, rep = entries[0], reps[0]
    need(entry["conversion_status"] == "not_converted" and
         entry["representative_item_id"] == "fg:item:000012" and
         entry["representative_status"] == "frozen_representative_record" and
         entry["whole_workbook_complete"] is False and
         entry["playable_projection"]["status"] == "explicitly_empty_unresolved" and
         all(entry[k] is False for k in
             ("admitted", "imported", "runtime_admitted", "runtime_eligible")),
         "FOUNDATION_ADMISSION")
    for kind, spec in (("txt", source.TXT), ("pdf", source.PDF)):
        block = entry[kind]
        need((block["path"], block["bytes"], block["sha256"]) == spec,
             f"FOUNDATION_SOURCE_{kind.upper()}")
    need(rep["id"] == "fg:item:000012" and
         rep["workbook_id"] == "fg:workbook:000097" and
         rep["module_id"] == "fg:module:000012" and
         rep["control_scope"]["extent"] == "task_reference" and
         rep["control_scope"]["whole_workbook_complete"] is False and
         rep["events"] == [] and rep["runtime_eligible"] is False and
         rep["resource_requirements"][0]["supplied"] is False,
         "REPRESENTATIVE_BOUNDARY")
    return {"id": rep["id"], "workbook_id": rep["workbook_id"],
            "module_id": rep["module_id"], "content_revision": rep["content_revision"],
            "record_sha256": sha(encoded(rep)), "scope": "selected_task_reference_only",
            "source_catalog_status": entry["conversion_status"],
            "runtime_eligible": False, "whole_workbook_complete": False}


def check_candidate(candidate: dict, replayed: dict) -> None:
    need(candidate == replayed, "SOURCE_REPLAY_DRIFT")
    need(candidate["schema"] == "fathom.level097.detached-source-task-candidate.1" and
         candidate["wbs"] == "2.3.1.3.1" and candidate["level"] == 97 and
         candidate["section"] == "XIV" and candidate["status"] == "non_admitted" and
         candidate["admitted"] is False and
         candidate["existing_representative_item_id_read_only"] == "fg:item:000012" and
         all(candidate[k] is None for k in
             ("canonical_id", "exercise_id", "onset_q", "duration_q", "fixed_bpm",
              "executable_events", "sounding_midi_events", "performed_event_count",
              "rubric_outcome")), "SOURCE_SCOPE")
    need(candidate["declared_workload_total"] == 1424 and
         candidate["declared_workload_by_module"] == EVENTS and
         list(candidate["modules"]) == list(source.KEYS) and
         len(candidate["txt_full_lines"]) == 43 and
         len(candidate["pdf_full_extracted_pages"]) == 19 and
         len(candidate["reference_listening_passes"]) == 7 and
         len(candidate["source_ambiguities"]) == 4 and
         candidate["capstone"]["source_audio_supplied"] is False and
         candidate["capstone"]["chord_chart_allowed"] is False,
         "SOURCE_COVERAGE")
    rows = [r for m in candidate["modules"].values()
            for table in m["tables"] for r in table["rows"]]
    need(len(rows) == 117 and
         all(r["declared_events_for_row"] is None and
             r["observed_answer"] is None and r["performed_events"] is None
             for r in rows + candidate["reference_listening_passes"]),
         "SOURCE_ROW_ALLOCATION")
    need(len(candidate["studies"]) == 2 and
         [len(study["passes"]) for study in candidate["studies"]] == [6, 6] and
         [r["semantic"]["start_bar"] for r in candidate["capstone"]["section_blocks"]] ==
         [1, 5, 13, 17, 25, 33, 41, 45] and
         [r["semantic"]["end_bar"] for r in candidate["capstone"]["section_blocks"]] ==
         [4, 12, 16, 24, 32, 40, 44, 48] and
         len(candidate["capstone"]["required_deliverables"]) == 7 and
         candidate["mastery"]["required_score"] == 14 and
         candidate["mastery"]["maximum_score"] == 16 and
         candidate["mastery"]["unfamiliar_excerpt_count"] == 2 and
         candidate["mastery"]["no_zero_categories"] ==
         ["Form", "Bass/function", "Groove", "Recovery"] and
         candidate["mastery"]["observed_scores"] is None,
         "SOURCE_FORM_MASTERY")


def row_fields(row: dict, page: int, module: str | None, kind: str,
               page_lines: list[str]) -> dict:
    key = f"L97-{module if module else 'reference'}-p{page}-r{row['ordinal']}"
    need(row["pdf_ref"].startswith(f"L97-PDF-p{page}-") and
         row["declared_events_for_row"] is None and
         row["observed_answer"] is None and row["performed_events"] is None,
         "ROW_SOURCE")
    return {
        "source_local_key": key, "source_kind": kind,
        "source_module": module, "source_row": copy.deepcopy(row),
        "source_row_sha256": sha(encoded(row)),
        "source_provenance": {"pdf_path": source.PDF[0], "pdf_page": page,
                              "pdf_ref": row["pdf_ref"],
                              "extracted_page_sha256": sha(encoded(page_lines)),
                              "whole_candidate_sha256": PINS[CANDIDATE]},
        "printed_event_allocation": None,
        "playable_event_status": "unresolved_source_task_without_audio_or_note_events",
        "schema1_fields": {
            "id": None, "workbook_id": None, "module_id": None,
            "lineage": None, "content_revision": None,
            "legacy_level": 97,
            "title": " | ".join(row["raw_fields"]),
            "kind": "unallocated_source_task" if module else
                    "unallocated_listening_reference",
            "runtime_eligible": False, "source_refs": [row["pdf_ref"]],
            "events": [], "variants": [], "pitch": None, "route": None,
            "audio_source": None, "observed_result": None,
            "timing": {"status": "unresolved", "onset_q": None,
                       "duration_q": None, "fixed_bpm": None},
            "resource_requirements": [{"kind": "learner_teacher_offline_recording",
                                       "supplied": False}],
            "ambiguities": UNRESOLVED,
        },
    }


def project(candidate: dict, replayed: dict, representative: dict) -> dict:
    check_candidate(candidate, replayed)
    need(representative["id"] == candidate["existing_representative_item_id_read_only"] and
         representative["scope"] == "selected_task_reference_only" and
         representative["whole_workbook_complete"] is False and
         representative["runtime_eligible"] is False,
         "REPRESENTATIVE_COLLISION")
    modules, rows = [], []
    for letter, module in candidate["modules"].items():
        keys = []
        for table in module["tables"]:
            page = table["page"]
            for row in table["rows"]:
                record = row_fields(row, page, letter, "module_task",
                                    candidate["pdf_full_extracted_pages"][page - 1])
                keys.append(record["source_local_key"])
                rows.append(record)
        modules.append({"source_module": letter, "title": module["name"],
                        "declared_events": module["declared_events"],
                        "per_task_event_allocation": None,
                        "source_txt_ref": module["txt_ref"],
                        "pdf_overview_ref": module["pdf_overview_ref"],
                        "pdf_pages": module["pdf_pages"],
                        "task_keys": keys, "schema1_module_id": None})
    references = [row_fields(row, 2, None, "listening_order_reference",
                             candidate["pdf_full_extracted_pages"][1])
                  for row in candidate["reference_listening_passes"]]
    need(len(rows) == 117 and len(references) == 7 and
         sum(m["declared_events"] for m in modules) == 1424 and
         len({r["source_local_key"] for r in rows + references}) == 124 and
         all(r["printed_event_allocation"] is None and
             r["schema1_fields"]["events"] == [] and
             r["schema1_fields"]["id"] is None
             for r in rows + references), "PROJECTION_COUNTS")
    return {
        "schema": "fathom.detached.curriculum.level097.schema1-unallocated.r01",
        "wbs": "2.3.1.3.1", "level": 97, "section": "XIV",
        "status": "detached_proposal_pending_audio_curriculum_and_admission",
        "source_candidate": {"path": str(CANDIDATE), "sha256": PINS[CANDIDATE]},
        "source_identities": candidate["source"],
        "schema_freeze_sha256": PINS[Path("Results/primary/20260912T100538Z-2.1.1.2.1-r02-evidence/schema-freeze.json")],
        "selected_representative_read_only": representative,
        "source_map_representative_status": {
            "id": candidate["source_map_row"]["representative_item_id"],
            "conversion_status": candidate["source_map_row"]["conversion_status"],
            "admitted": candidate["source_map_row"]["admitted"]},
        "source_context": {
            "txt_full_lines": candidate["txt_full_lines"],
            "pdf_full_extracted_pages": candidate["pdf_full_extracted_pages"],
            "reference_page_intro": candidate["reference_page_intro"],
            "reference_page_closing": candidate["reference_page_closing"],
            "studies": candidate["studies"], "capstone": candidate["capstone"],
            "mastery": candidate["mastery"],
            "source_ambiguities": candidate["source_ambiguities"],
        },
        "declared_total_events": 1424,
        "printed_event_allocation_status": "module_totals_only_no_per_row_allocation",
        "playable_event_count": 0, "module_count": 10,
        "module_task_row_count": 117, "listening_reference_row_count": 7,
        "modules": modules, "rows": rows, "listening_reference_rows": references,
        "canonical_ids_allocated": False, "schema1_imported": False,
        "whole_workbook_accepted": False, "runtime_eligible": False,
        "unresolved": UNRESOLVED,
    }


def build() -> dict:
    check_pins()
    representative = foundation_status()
    replayed = source.build_candidate(ROOT)
    candidate = json.loads((ROOT / CANDIDATE).read_text())
    return project(candidate, replayed, representative)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("build", "verify"))
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    need(output.is_relative_to((ROOT / OUT).resolve()), "OUTPUT_SCOPE")
    payload = encoded(build())
    if args.mode == "build":
        need(not output.exists(), "OUTPUT_EXISTS")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(payload)
    else:
        need(output.is_file() and output.read_bytes() == payload, "PROJECTION_DRIFT")
    print(f"PASS: {args.mode}; 10 modules, 117 rows, 7 references, "
          "1424 unallocated module declarations, zero playable events")


if __name__ == "__main__":
    main()
