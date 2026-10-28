#!/usr/bin/env python3
"""Project Level91's pinned whole-source candidate to detached unallocated schema1 fields."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path

import curriculum_level091_whole_semantic_candidate as source

ROOT = Path(__file__).resolve().parents[1]
OUT = Path("Build/parallel-13/level091-schema1-unallocated-r01")
CANDIDATE = Path("Build/parallel-06/2.3-level091-whole-semantic-r01/final-a.json")
PINS = {
    CANDIDATE: "1b7c56239673e27ff59f352aea3aa3b178045c297f1945c6c4370d4b1d474881",
    Path("Tools/curriculum_level091_whole_semantic_candidate.py"): "bd8b9f2f71bc1d952e53f440084fa5693633b699e2fbe8ecaa598a5b74f95204",
    Path("Results/parallel-06/exercises/conversion/20260923T181500Z-2.3.1.3.1-level091-whole-semantic-r01-results.md"): "f1ce5cb291a7c049b5417055178f1bd7dd4c03fb6e32d8c442829d19f0bc8034",
    Path("Results/primary/20260912T100538Z-2.1.1.2.1-r02-evidence/schema-freeze.json"): "0659fa962a5c933a2bcf3045772b6fe5b05b4deefb3511f5dcb68af51088de95",
}
TASKS = dict(zip("ABCDEFGHIJ", (8, 8, 12, 8, 6, 8, 8, 24, 8, 8)))
MODULE_EVENTS = dict(zip("ABCDEFGHIJ", (144, 128, 144, 128, 128, 128, 112, 192, 256, 64)))
UNRESOLVED = [
    "no printed event allocation per task or supporting row",
    "no complete pitch/route/bend-curve and playable attack notation",
    "no performed onset/duration/fixed BPM or rubric realization",
    "canonical identity, lineage, revision, Curriculum review and runtime admission pending",
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
               if e["workbook_id"] == "fg:workbook:000091"]
    need(len(package["records"]) == 659 and len(entries) == 1 and
         not any(r.get("legacy_level") == 91 for r in package["records"]),
         "FOUNDATION_RECORDS")
    entry = entries[0]
    need(entry["conversion_status"] == "not_converted" and
         entry["representative_item_id"] is None and
         entry["whole_workbook_complete"] is False and
         entry["playable_projection"]["status"] == "explicitly_empty_unresolved" and
         all(entry[k] is False for k in
             ("admitted", "imported", "runtime_admitted", "runtime_eligible")),
         "FOUNDATION_ADMISSION")
    for kind in ("txt", "pdf"):
        identity = source.SOURCE[kind]
        block = entry[kind]
        need((block["path"], block["bytes"], block["sha256"]) == identity,
             f"FOUNDATION_SOURCE_{kind.upper()}")


def check_candidate(candidate: dict, original: dict) -> None:
    need(candidate == original, "SOURCE_REPLAY_DRIFT")
    need(candidate["wbs"] == "2.3.1.3.1" and candidate["level"] == 91 and
         candidate["section"] == "XIII" and candidate["module_order"] == list(TASKS) and
         candidate["declared_total_events"] == 1424 and
         candidate["extracted_task_rows"] == 98 and candidate["supporting_rows"] == 12 and
         candidate["whole_source_semantic_projection"] is True and
         candidate["whole_workbook_accepted"] is False and
         candidate["canonical_ids_allocated"] is False and
         candidate["runtime_eligible"] is False and
         candidate["schema1_imported"] is False, "SOURCE_SCOPE")
    need({m["module"]: m["declared_events"] for m in candidate["modules"]} == MODULE_EVENTS and
         {m["module"]: len(m["tasks"]) for m in candidate["modules"]} == TASKS and
         len(candidate["txt_lines"]) == 37 and len(candidate["pdf_pages"]) == 17 and
         [t["page"] for t in candidate["supporting_tables"]] == [2, 4],
         "SOURCE_COVERAGE")
    need(candidate["unresolved"]["per_task_event_counts"] is None and
         candidate["unresolved"]["runtime_admission"] is False and
         all(t["declared_event_count_for_row"] is None and t["canonical_id"] is None and
             t["pitch"] is None and t["duration"] is None and t["performed_timing"] is None
             for m in candidate["modules"] for t in m["tasks"]), "SOURCE_ALLOCATION")
    need(candidate["mastery"]["minimum"] == "14/16 or better on two separate days" and
         candidate["mastery"]["protected_zero_domains"] ==
         ["bend intonation", "vibrato control", "pulse", "recovery"] and
         [t["fields"]["Bars"] for t in candidate["modules"][8]["tasks"]] ==
         [f"{start}-{start+3}" for start in range(1, 33, 4)], "SOURCE_MASTERY_FORM")


def row_fields(kind: str, key: str, row: dict, module: str | None,
               relation: str | None = None) -> dict:
    page = row["source"]["page"]
    need(1 <= page <= 17 and row["source"]["extracted_text_sha256"], "ROW_PROVENANCE")
    if kind == "task":
        need(row["local_key"] == key, "ROW_KEY")
    fields = row.get("fields", {})
    title = " | ".join(fields.values()) if fields else row["requirement"]
    return {
        "source_local_key": key,
        "source_kind": "module_task" if kind == "task" else "supporting_reference",
        "source_module": module,
        "support_relation": relation,
        "source_row_sha256": sha(encoded(row)),
        "source_row": copy.deepcopy(row),
        "source_provenance": {
            "pdf_path": source.SOURCE["pdf"][0],
            "pdf_page": page,
            "pdf_extracted_text_sha256": row["source"]["extracted_text_sha256"],
            "whole_candidate_sha256": PINS[CANDIDATE],
        },
        "printed_event_allocation": None,
        "playable_event_status": "unresolved_not_fully_notated",
        "schema1_fields": {
            "id": None, "workbook_id": None, "module_id": None,
            "lineage": None, "content_revision": None,
            "legacy_level": 91, "title": title,
            "kind": "unallocated_source_task" if kind == "task" else
                    "unallocated_support_reference",
            "runtime_eligible": False,
            "source_refs": [f"L91-PDF-p{page}-r{row['source']['row_ordinal']}"],
            "events": [], "variants": [],
            "pitch": None, "route": None, "bend_curve": None,
            "timing": {"status": "unresolved", "onset_q": None,
                       "duration_q": None, "fixed_bpm": None},
            "resource_requirements": [], "ambiguities": UNRESOLVED,
        },
    }


def project(candidate: dict, original: dict) -> dict:
    check_candidate(candidate, original)
    modules, rows, support = [], [], []
    for module in candidate["modules"]:
        letter = module["module"]
        modules.append({
            "source_module": letter, "title": module["title"],
            "declared_events": module["declared_events"],
            "per_task_event_counts_known": False, "allocated_event_count": None,
            "source_txt_line": module["txt_line"], "source_pdf": module["pdf"],
            "task_keys": [task["local_key"] for task in module["tasks"]],
            "schema1_module_id": None,
        })
        rows.extend(row_fields("task", task["local_key"], task, letter)
                    for task in module["tasks"])
    for table in candidate["supporting_tables"]:
        for row in table["rows"]:
            key = f"L91-support-p{table['page']}-r{row['row_ordinal']}"
            support.append(row_fields("support", key, row, None, table["relation"]))
    need(len(rows) == 98 and len(support) == 12 and
         sum(m["declared_events"] for m in modules) == 1424 and
         all(r["printed_event_allocation"] is None and
             r["schema1_fields"]["events"] == [] for r in rows + support),
         "PROJECTION_COUNTS")
    return {
        "schema": "fathom.detached.curriculum.level091.schema1-unallocated.r01",
        "wbs": "2.3.1.3.1", "level": 91, "section": "XIII",
        "status": "detached_proposal_pending_curriculum_and_admission",
        "source_candidate": {"path": str(CANDIDATE), "sha256": PINS[CANDIDATE]},
        "source_identities": candidate["source_identities"],
        "schema_freeze_sha256": PINS[Path("Results/primary/20260912T100538Z-2.1.1.2.1-r02-evidence/schema-freeze.json")],
        "source_context": {"txt_lines": candidate["txt_lines"],
                           "pdf_pages": candidate["pdf_pages"],
                           "key_skills": candidate["key_skills"],
                           "supporting_tables": candidate["supporting_tables"],
                           "mastery": candidate["mastery"],
                           "next_level_source_line": candidate["next_level_source_line"]},
        "declared_total_events": 1424,
        "printed_event_allocation_status": "module_totals_only_no_per_row_allocation",
        "playable_event_count": 0,
        "module_count": 10, "module_task_row_count": 98, "supporting_row_count": 12,
        "modules": modules, "rows": rows, "supporting_rows": support,
        "canonical_ids_allocated": False, "schema1_imported": False,
        "whole_workbook_accepted": False, "runtime_eligible": False,
        "unresolved": candidate["unresolved"],
    }


def build() -> dict:
    check_pins()
    foundation_status()
    original = source.build(ROOT)
    candidate = json.loads((ROOT / CANDIDATE).read_text())
    return project(candidate, original)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("build", "verify"))
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    need(output.is_relative_to((ROOT / OUT).resolve()), "OUTPUT_SCOPE")
    payload = encoded(build())
    if args.mode == "build":
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(payload)
    else:
        need(output.is_file() and output.read_bytes() == payload, "PROJECTION_DRIFT")
    print(f"PASS: {args.mode}; 10 modules, 98 task rows, 12 supporting rows, "
          "1424 unallocated module-declared events, zero playable events")


if __name__ == "__main__":
    main()
