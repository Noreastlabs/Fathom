#!/usr/bin/env python3
"""Project sealed Level85 semantic source rows into detached unallocated schema1 fields."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path

import parallel13_level085_whole_semantic_candidate as source

ROOT = Path(__file__).resolve().parents[1]
OUT = Path("Build/parallel-13/level085-schema1-unallocated-r01")
CANDIDATE = Path("Build/parallel-13/level085-whole-semantic-r01/candidate-a.json")
PINS = {
    CANDIDATE: "d90595273f866e5fdbaf785e2de606a6107a05434c20052067bcb14b075bf59a",
    Path("Tools/parallel13_level085_whole_semantic_candidate.py"): "3dd1f400290058bc401d1005d67b9fd85245a41f379c353d0b3133369d2a7d9e",
    Path("Results/parallel-13/20260923T181619Z-2.3-level085-whole-semantic-r01-results.md"): "cb1e131b70859638d84f04d462c99962de7baea90b106f5582cc5f015d04dfab",
    Path("Results/primary/20260912T100538Z-2.1.1.2.1-r02-evidence/schema-freeze.json"): "0659fa962a5c933a2bcf3045772b6fe5b05b4deefb3511f5dcb68af51088de95",
}
COUNTS = dict(zip("ABCDEFGHIJ", (6, 6, 6, 6, 6, 4, 8, 24, 8, 8)))
MODULE_EVENTS = dict(zip("ABCDEFGHIJ", (128, 128, 144, 144, 128, 96, 160, 192, 256, 64)))
UNRESOLVED = [
    "1440 source workload events are declared by module without task-row allocations",
    "Module I's 256 events are not assigned to its eight printed four-bar ranges",
    "pitched playable attacks, chord voicings, onset/duration and exact microtiming unresolved",
    "canonical identity, lineage, revision, performed mastery, Curriculum review and admission pending",
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


def check_candidate(candidate: dict, replayed: dict) -> None:
    need(candidate == replayed, "SOURCE_REPLAY_DRIFT")
    need(candidate["schema"] == "fathom.detached.curriculum.level085.whole-semantic.r01" and
         candidate["wbs"] == "2.3.1.3.1" and candidate["level"] == 85 and
         candidate["section"] == "XII" and
         candidate["status"] == "detached_semantic_source_candidate_pending_curriculum_and_admission" and
         candidate["declared_total_events"] == 1440 and
         candidate["module_task_row_count"] == 82 and candidate["reference_row_count"] == 6 and
         candidate["playable_event_count"] == 0 and
         candidate["canonical_ids_allocated"] is False and
         candidate["schema1_imported"] is False and
         candidate["whole_workbook_accepted"] is False and
         candidate["runtime_eligible"] is False,
         "SOURCE_SCOPE")
    need(candidate["module_order"] == list(COUNTS) and
         {m["module"]: len(m["tasks"]) for m in candidate["modules"]} == COUNTS and
         {m["module"]: m["declared_events"] for m in candidate["modules"]} == MODULE_EVENTS and
         len(candidate["txt_lines"]) == 40 and len(candidate["pdf_pages"]) == 15 and
         len(candidate["page_context"]) == 14 and
         candidate["symbol_legend"] == {"P": "pitched contact", "x": "muted contact",
                                        "-": "air stroke", "~": "sustain"} and
         candidate["continuous_hand_motion"] == "D U D U sixteenths" and
         len(candidate["reference_rows"]) == 6 and
         all(r["relation"] == "adjacent_unassigned_groove_reference" and
             r["source"]["pdf_page"] == 2 for r in candidate["reference_rows"]),
         "SOURCE_COVERAGE")
    rows = [r for m in candidate["modules"] for r in m["tasks"]] + candidate["reference_rows"]
    need(len(rows) == 88 and
         len({r["local_key"] for r in rows}) == 88 and
         all(r["declared_event_count_for_row"] is None and r["canonical_id"] is None and
             r["onset_q"] is None and r["duration_q"] is None and
             r["performed_result"] is None for r in rows), "SOURCE_ROW_STATE")
    i = candidate["modules"][8]
    need(i["module"] == "I" and i["declared_events"] == 256 and
         [r["semantic"]["bar_start"] for r in i["tasks"]] == list(range(1, 33, 4)) and
         [r["semantic"]["bar_end"] for r in i["tasks"]] == list(range(4, 33, 4)) and
         all(r["semantic"]["declared_events_for_range"] is None for r in i["tasks"]) and
         candidate["capstone"]["bar_count"] == 32 and
         candidate["capstone"]["one_underlying_tempo"] is True and
         candidate["capstone"]["beat_four_announcement_required"] is True and
         candidate["capstone"]["per_four_bar_row_event_counts"] is None,
         "SOURCE_CAPSTONE")
    need(candidate["mastery"]["minimum"] == "14/16 or better on two separate days" and
         candidate["mastery"]["protected_zero_domains"] ==
         ["pulse", "note length", "muting", "recovery"] and
         candidate["mastery"]["observed_score"] is None and
         all(p["extracted_text_sha256"] == sha(p["extracted_text"].encode())
             for p in candidate["pdf_pages"]), "SOURCE_MASTERY_PAGES")


def row_fields(row: dict, module: str | None) -> dict:
    ref = row["source"]
    page = ref["pdf_page"]
    need(2 <= page <= 15 and ref["pdf_extracted_text_sha256"] and
         row["declared_event_count_for_row"] is None and
         row["canonical_id"] is None and row["onset_q"] is None and
         row["duration_q"] is None and row["performed_result"] is None,
         "ROW_SOURCE")
    return {
        "source_local_key": row["local_key"],
        "source_kind": "module_task" if module else "groove_reference",
        "source_module": module,
        "support_relation": row.get("relation") if module is None else None,
        "source_row": copy.deepcopy(row),
        "source_row_sha256": sha(encoded(row)),
        "source_provenance": {
            "txt_path": source.index.TXT,
            "txt_module_line": ref.get("txt_module_line"),
            "pdf_path": source.index.PDF,
            "pdf_page": page,
            "pdf_line_start": ref["pdf_line_start"],
            "pdf_line_end": ref["pdf_line_end"],
            "pdf_extracted_text_sha256": ref["pdf_extracted_text_sha256"],
            "semantic_candidate_sha256": PINS[CANDIDATE],
        },
        "printed_event_allocation": None,
        "playable_event_status": "unresolved_source_task_not_playable_attack_sequence",
        "schema1_fields": {
            "id": None, "workbook_id": None, "module_id": None,
            "lineage": None, "content_revision": None,
            "legacy_level": 85,
            "title": " | ".join(row["fields"].values()),
            "kind": "unallocated_source_task" if module else
                    "unallocated_support_reference",
            "runtime_eligible": False,
            "source_refs": [f"L85-PDF-p{page}-r{row['row_ordinal']}"] +
                           ([f"L85-TXT-L{ref['txt_module_line']}"] if module else []),
            "events": [], "variants": [], "pitch": None, "route": None,
            "performed_result": None,
            "timing": {"status": "unresolved", "onset_q": None,
                       "duration_q": None, "fixed_bpm": None,
                       "exact_microtiming_ms": None},
            "resource_requirements": [], "ambiguities": UNRESOLVED,
        },
    }


def project(candidate: dict, replayed: dict) -> dict:
    check_candidate(candidate, replayed)
    modules, rows, reference = [], [], []
    for module in candidate["modules"]:
        letter = module["module"]
        modules.append({"source_module": letter, "title": module["title"],
                        "declared_events": module["declared_events"],
                        "per_task_event_counts_known": False,
                        "allocated_event_count": None,
                        "source_txt_line": module["txt_line"],
                        "task_keys": [r["local_key"] for r in module["tasks"]],
                        "schema1_module_id": None})
        rows.extend(row_fields(r, letter) for r in module["tasks"])
    reference.extend(row_fields(r, None) for r in candidate["reference_rows"])
    need(len(rows) == 82 and len(reference) == 6 and
         sum(m["declared_events"] for m in modules) == 1440 and
         all(r["printed_event_allocation"] is None and
             r["schema1_fields"]["events"] == [] and
             r["schema1_fields"]["id"] is None
             for r in rows + reference), "PROJECTION_COUNTS")
    return {
        "schema": "fathom.detached.curriculum.level085.schema1-unallocated.r01",
        "wbs": "2.3.1.3.1", "level": 85, "section": "XII",
        "status": "detached_proposal_pending_curriculum_and_admission",
        "semantic_source_candidate": {"path": str(CANDIDATE), "sha256": PINS[CANDIDATE]},
        "structural_source_index": candidate["source_index"],
        "source_identities": candidate["source_identities"],
        "schema_freeze_sha256": PINS[Path("Results/primary/20260912T100538Z-2.1.1.2.1-r02-evidence/schema-freeze.json")],
        "source_context": {
            "txt_lines": candidate["txt_lines"],
            "pdf_pages": candidate["pdf_pages"],
            "page_context": candidate["page_context"],
            "symbol_legend": candidate["symbol_legend"],
            "continuous_hand_motion": candidate["continuous_hand_motion"],
            "capstone": candidate["capstone"],
            "mastery": candidate["mastery"],
        },
        "declared_total_events": 1440,
        "printed_event_allocation_status": "module_totals_only_no_per_row_allocation",
        "playable_event_count": 0,
        "module_count": 10, "module_task_row_count": 82,
        "reference_row_count": 6,
        "modules": modules, "rows": rows, "reference_rows": reference,
        "canonical_ids_allocated": False, "schema1_imported": False,
        "whole_workbook_accepted": False, "runtime_eligible": False,
        "unresolved": candidate["unresolved"],
    }


def build() -> dict:
    check_pins()
    replayed = source.build()
    candidate = json.loads((ROOT / CANDIDATE).read_text())
    return project(candidate, replayed)


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
    print("PASS: Level85 schema1; 82 task rows, 6 references, "
          "1440 unallocated module events, zero playable events")


if __name__ == "__main__":
    main()
