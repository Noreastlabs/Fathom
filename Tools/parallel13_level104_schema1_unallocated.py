#!/usr/bin/env python3
"""Project Level104's pinned whole-source candidate into detached unallocated schema1 fields."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path

import curriculum_level104_whole_original_work_candidate as source

ROOT = Path(__file__).resolve().parents[1]
OUT = Path("Build/parallel-13/level104-schema1-unallocated-r01")
CANDIDATE = Path("Build/parallel-05/2.3.1.3.1-level104-whole-r01/candidate-b.json")
PINS = {
    CANDIDATE: "a7c34ec400b459699b32cd7a6ab1c2982b47a8187ff47a0aa38d1eb0b727aebe",
    Path("Tools/curriculum_level104_whole_original_work_candidate.py"): "2ac429b2852c9e0b897372368ffc95caaf4e0b268a8eea0ee3d822a9f41de392",
    Path("Results/parallel-05/exercises/conversion/20260923T172445Z-2.3.1.3.1-level104-whole-original-work-r01-results.md"): "0e31609bd00b0b84835c9ef6ae98ef3038706cb9ed4355203297b314b437158e",
    Path("Results/primary/20260912T100538Z-2.1.1.2.1-r02-evidence/schema-freeze.json"): "0659fa962a5c933a2bcf3045772b6fe5b05b4deefb3511f5dcb68af51088de95",
}
UNRESOLVED = [
    "1440 source workload events lack complete timed attack notation or row allocation",
    "creative brief, three identity choices, arrangements, rehearsal and recordings are blank",
    "no learner audio, critique observations, finalized portfolio or awarded scores",
    "canonical identity, lineage, revision, Curriculum review and runtime admission pending",
    "TXT companion 16-32 bar requirement is not repeated on PDF page 20",
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


def foundation_status() -> None:
    package = json.loads((ROOT / "Content/controls/curriculum-v1/package.json").read_text())
    entries = [e for e in package["workbook_catalog"]["entries"]
               if e["workbook_id"] == "fg:workbook:000104"]
    need(len(package["records"]) == 659 and len(entries) == 1 and
         not any(r.get("legacy_level") == 104 for r in package["records"]),
         "FOUNDATION_RECORDS")
    entry = entries[0]
    need(entry["conversion_status"] == "not_converted" and
         entry["representative_item_id"] is None and
         entry["whole_workbook_complete"] is False and
         entry["playable_projection"]["status"] == "explicitly_empty_unresolved" and
         all(entry[k] is False for k in
             ("admitted", "imported", "runtime_admitted", "runtime_eligible")),
         "FOUNDATION_ADMISSION")
    for kind, rel in (("txt", source.TXT), ("pdf", source.PDF)):
        block = entry[kind]
        size, digest = source.PINS[rel]
        need((block["path"], block["bytes"], block["sha256"]) ==
             (rel, size, digest), f"FOUNDATION_SOURCE_{kind.upper()}")


def check_candidate(candidate: dict, replayed: dict, txt_lines: list[str]) -> None:
    need(candidate == replayed, "SOURCE_REPLAY_DRIFT")
    need(candidate["schema"] == "fathom.detached.level104.whole-source-candidate.v1" and
         candidate["level"] == 104 and candidate["section"] == "XV" and
         candidate["wbs_owner"] == "2.3.1.3.1" and
         candidate["review"] == "Pending" and
         candidate["canonical_ids"] is None and
         candidate["runtime_eligible"] is False and
         candidate["imported"] is False and candidate["admitted"] is False and
         candidate["atomic_event_interpretation"] is None,
         "SOURCE_SCOPE")
    need(candidate["source_pins"] ==
         {p: {"bytes": n, "sha256": h} for p, (n, h) in source.PINS.items()} and
         candidate["source_map_row"]["conversion_status"] == "not_converted" and
         candidate["source_map_row"]["representative_item_id"] in (None, "") and
         len(txt_lines) == 47 and len(candidate["pdf_page_sources"]) == 22 and
         [p["page"] for p in candidate["pdf_page_sources"]] == list(range(1, 23)) and
         all(p["extracted_text_sha256"] == sha(p["text"].encode())
             for p in candidate["pdf_page_sources"]), "SOURCE_PROVENANCE")
    need(candidate["printed_workload_claim"] == 1440 and
         list(candidate["modules"]) == list(source.CLAIMS) and
         {a: m["printed_event_claim"] for a, m in candidate["modules"].items()} == source.CLAIMS and
         {a: len(m["tasks"]) for a, m in candidate["modules"].items()} == source.COUNTS and
         len(candidate["production_gate_sequence_pdf_p2"]) == 9,
         "SOURCE_COVERAGE")
    tasks = [t for m in candidate["modules"].values() for t in m["tasks"]]
    need(len(tasks) == 140 and
         all(t["canonical_task_id"] is None and t["onset_q"] is None and
             t["duration_q"] is None and t["observed_result"] is None
             for t in tasks), "SOURCE_TASK_STATE")
    need(candidate["identity_lock"]["required_chosen_elements"] == 3 and
         candidate["identity_lock"]["chosen_elements"] is None and
         candidate["modules"]["G"]["tasks"][-1]["fields"]["visible_blank_row_slots"] == 5 and
         candidate["modules"]["G"]["tasks"][-1]["fields"]["entries"] == [] and
         candidate["primary_work"]["bar_min"] == 32 and
         candidate["primary_work"]["bar_max"] == 64 and
         candidate["primary_work"]["actual_bars"] is None and
         candidate["companion_work"]["bar_min"] == 16 and
         candidate["companion_work"]["bar_max"] == 32 and
         candidate["companion_work"]["minimum_major_contrasting_dimensions"] == 4 and
         candidate["companion_work"]["actual_bars"] is None and
         "One contrasting 16-32 bar original" in "\n".join(txt_lines) and
         "16-32" not in candidate["pdf_page_sources"][19]["text"],
         "SOURCE_BLANKS_LENGTH")
    need(candidate["portfolio"]["printed_item_count"] == 8 and
         candidate["portfolio"]["delivered_items"] is None and
         len(candidate["mastery_gate"]["rubric_0_to_2"]) == 8 and
         candidate["mastery_gate"]["threshold"] == "14/16 or better" and
         candidate["mastery_gate"]["required_nonzero"] ==
         ["Identity", "Form", "Performance", "Finalization"] and
         candidate["mastery_gate"]["observed_scores"] is None and
         len(candidate["unresolved"]) == 7, "SOURCE_PORTFOLIO_MASTERY")


def row_fields(task: dict, module: str) -> dict:
    source_ref = task["source"]
    page = source_ref["pdf"]["page"]
    need(task["local_key"].startswith(f"level104-{module.lower()}-") and
         3 <= page <= 22 and
         task["canonical_task_id"] is None and task["onset_q"] is None and
         task["duration_q"] is None and task["observed_result"] is None,
         "ROW_SOURCE")
    title = " | ".join(str(value) for value in task["fields"].values()
                       if isinstance(value, str)) or task["kind"]
    return {
        "source_local_key": task["local_key"], "source_module": module,
        "source_kind": task["kind"], "source_task": copy.deepcopy(task),
        "source_task_sha256": sha(encoded(task)),
        "source_provenance": {"txt_path": source.TXT,
                              "txt_module_line": source_ref["txt_module_line"],
                              "txt_row_detail": source_ref["txt_row_detail"],
                              "pdf_path": source.PDF,
                              "pdf_page": page,
                              "pdf_row": source_ref["pdf_row"],
                              "pdf_extracted_text_sha256": source_ref["pdf"]["extracted_text_sha256"],
                              "whole_candidate_sha256": PINS[CANDIDATE]},
        "printed_event_allocation": None,
        "playable_event_status": "unresolved_source_task_not_timed_attacks",
        "schema1_fields": {
            "id": None, "workbook_id": None, "module_id": None,
            "lineage": None, "content_revision": None,
            "legacy_level": 104, "title": title,
            "kind": "unallocated_source_task", "runtime_eligible": False,
            "source_refs": [f"L104-TXT-L{source_ref['txt_module_line']}",
                            f"L104-PDF-p{page}-r{source_ref['pdf_row']}"],
            "events": [], "variants": [], "pitch": None, "route": None,
            "observed_result": None,
            "timing": {"status": "unresolved", "onset_q": None,
                       "duration_q": None, "fixed_bpm": None},
            "resource_requirements": [], "ambiguities": UNRESOLVED,
        },
    }


def project(candidate: dict, replayed: dict, txt_lines: list[str]) -> dict:
    check_candidate(candidate, replayed, txt_lines)
    modules, rows = [], []
    for letter, module in candidate["modules"].items():
        keys = [task["local_key"] for task in module["tasks"]]
        modules.append({"source_module": letter,
                        "declared_events": module["printed_event_claim"],
                        "per_task_event_allocation": None,
                        "source_txt_line": module["tasks"][0]["source"]["txt_module_line"],
                        "task_keys": keys, "schema1_module_id": None})
        rows.extend(row_fields(task, letter) for task in module["tasks"])
    need(len(rows) == 140 and len({r["source_local_key"] for r in rows}) == 140 and
         sum(m["declared_events"] for m in modules) == 1440 and
         all(r["printed_event_allocation"] is None and
             r["schema1_fields"]["events"] == [] and
             r["schema1_fields"]["id"] is None for r in rows),
         "PROJECTION_COUNTS")
    return {
        "schema": "fathom.detached.curriculum.level104.schema1-unallocated.r01",
        "wbs": "2.3.1.3.1", "level": 104, "section": "XV",
        "status": "detached_proposal_pending_creative_work_curriculum_and_admission",
        "source_candidate": {"path": str(CANDIDATE), "sha256": PINS[CANDIDATE]},
        "source_identities": candidate["source_pins"],
        "schema_freeze_sha256": PINS[Path("Results/primary/20260912T100538Z-2.1.1.2.1-r02-evidence/schema-freeze.json")],
        "source_context": {
            "txt_full_lines": txt_lines,
            "pdf_page_sources": candidate["pdf_page_sources"],
            "production_gate_sequence_pdf_p2": candidate["production_gate_sequence_pdf_p2"],
            "identity_lock": candidate["identity_lock"],
            "primary_work": candidate["primary_work"],
            "companion_work": candidate["companion_work"],
            "companion_length_source_difference": {
                "txt_requirement": "16-32 bars",
                "pdf_page_20_repeats_length": False,
                "pdf_page_20_minimum_contrast_dimensions": 4},
            "portfolio": candidate["portfolio"],
            "mastery_gate": candidate["mastery_gate"],
            "unresolved": candidate["unresolved"],
        },
        "declared_total_events": 1440,
        "printed_event_allocation_status": "module_totals_only_no_per_row_allocation",
        "playable_event_count": 0, "module_count": 10,
        "module_task_row_count": 140, "production_gate_count": 9,
        "modules": modules, "rows": rows,
        "canonical_ids_allocated": False, "schema1_imported": False,
        "whole_workbook_accepted": False, "runtime_eligible": False,
    }


def build() -> dict:
    check_pins()
    foundation_status()
    replayed = source.make(ROOT)
    txt_lines = (ROOT / source.TXT).read_text(encoding="utf-8").splitlines()
    candidate = json.loads((ROOT / CANDIDATE).read_text())
    return project(candidate, replayed, txt_lines)


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
    print(f"PASS: {args.mode}; 10 modules, 140 tasks, 9 gates, "
          "1440 unallocated source events, zero playable events")


if __name__ == "__main__":
    main()
