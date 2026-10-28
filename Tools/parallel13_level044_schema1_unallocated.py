#!/usr/bin/env python3
"""Project sealed Level44 note/TAB source tasks into detached schema1-shaped fields."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path

import curriculum_level044_whole_candidate as source_tool

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "Build/parallel-13/level044-schema1-unallocated-r01"
CANDIDATE = Path("Build/parallel-11/2.3.1.1.1-level044-whole-r01/candidate-c.json")
PINS = {
    CANDIDATE: "1205e9f8ece41bf6525c8824ee9c6cbea2694bbfc23ec1c897899d25e65f0172",
    Path("Tools/curriculum_level044_whole_candidate.py"): "49ab9bbaf4aa4efda499e4145c19e82cd32ed5b41f8ad14f8acdc765215daaa8",
    Path("Results/parallel-11/curriculum/20260923T154500Z-2.3-level044-whole-r01-results.md"): "fb04c7752ed29a85884d472a9d4cb0502e01505a6d1c5528c522e211e1d1065a",
    Path("Results/primary/20260912T100538Z-2.1.1.2.1-r02-evidence/schema-freeze.json"): "0659fa962a5c933a2bcf3045772b6fe5b05b4deefb3511f5dcb68af51088de95",
}
COUNTS = dict(zip("ABCDEFGHIJ", (6, 6, 6, 5, 5, 10, 4, 5, 4, 28)))
TONES = dict(zip("ABCDEFGHIJ", (54, 36, 48, 160, 57, 65, 51, 70, 41, 64)))
AMBIGUITIES = [
    "Module J prints 64 workload tones but its 16 full opening-ending choices imply 128 degree occurrences; counting convention unresolved",
    "source TAB is authored notation, not an executable event timeline or pick-attack schedule",
    "canonical identity, lineage, revision, click/timing, performed result, Curriculum review, and admission pending",
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


def check_candidate(c: dict, replayed: dict) -> None:
    need(c == replayed, "SOURCE_REPLAY_DRIFT")
    need(c["schema"] == "fathom.level044.detached-source-candidate.1" and
         c["wbs"] == "2.3.1.1.1" and c["status"] == "non_admitted" and
         c["admitted"] is False and
         all(c[k] is None for k in ("canonical_id", "exercise_id", "onset_q",
                                   "duration_q", "fixed_bpm", "pick_attack_count",
                                   "executable_events")), "SOURCE_SCOPE")
    need(set(c["modules"]) == set(COUNTS) and
         c["pdf_printed_workload_by_module"] == TONES and
         c["pdf_printed_total_tones"] == 646 and
         len(c["module_sections"]) == 10 and
         len(c["source_guidance"]["txt_full_lines"]) == 660 and
         len(c["source_guidance"]["pdf_full_extracted_pages"]) == 19 and
         c["core_notes"] == ["A", "C", "D", "Eb", "E", "G"] and
         c["core_degrees"] == ["1", "b3", "4", "b5", "5", "b7"] and
         c["marked_support_notes"] == {"C#": "3*", "F#": "6*", "F": "b6*",
                                         "B": "2*/E7-5", "G#": "7*/E7-3"},
         "SOURCE_COVERAGE")
    j = c["modules"]["J"]
    need(len(j["openings"]) == 4 and len(j["endings"]) == 4 and
         len(j["all_combinations"]) == 16 and len(j["model_combinations_raw"]) == 4 and
         j["printed_workload_tones"] == 64 and
         j["implied_full_combination_degree_occurrences"] == 128 and
         j["count_status"] == "unresolved_source_counting_convention" and
         all(x["component_degree_occurrences"] == 8 for x in j["all_combinations"]),
         "J_COUNT_CONFLICT")
    need(c["modules"]["I"][2]["kind"] == "simultaneous_voice_leading_shapes" and
         c["modules"]["I"][2]["printed_workload_tones"] == 16 and
         {d["kind"] for d in c["source_differences"]} ==
         {"PDF_only_post_workbook_variations", "PDF_only_completion_audit_checklist",
          "PDF_visual_completion_audit_border_overlap", "J_workload_count_ambiguous"},
         "SOURCE_SEMANTICS")
    for item in c["source"].values():
        path = ROOT / item["path"]
        need(path.is_file() and not path.is_symlink() and
             path.resolve().is_relative_to(ROOT.resolve()) and
             path.stat().st_size == item["bytes"] and
             sha(path.read_bytes()) == item["sha256"], f"SOURCE_IDENTITY {item['role']}")


def check_current_catalog(c: dict) -> dict:
    package = json.loads((ROOT / "Content/controls/curriculum-v1/package.json").read_text())
    entries = package["workbook_catalog"]["entries"]
    need(len(package["records"]) == 659 and len(entries) == 105,
         "CATALOG_POPULATION")
    entry = entries[43]
    need(entry["workbook_id"] == "fg:workbook:000044" and
         entry["conversion_status"] == "not_converted" and
         entry["catalog_role"] == "read_only_source_preservation" and
         entry["admitted"] is False and entry["imported"] is False and
         entry["whole_workbook_complete"] is False and
         entry["txt"]["sha256"] == c["source"]["txt"]["sha256"] and
         entry["pdf"]["sha256"] == c["source"]["pdf"]["sha256"] and
         not any(r.get("legacy_level") == 44 for r in package["records"]),
         "CATALOG_LEVEL44_STATE")
    return {"path": "Content/controls/curriculum-v1/package.json",
            "sha256": sha((ROOT / "Content/controls/curriculum-v1/package.json").read_bytes()),
            "record_count": 659, "level44_status": entry["conversion_status"]}


def tasks(c: dict) -> list[tuple[str, str, dict, int | None]]:
    m = c["modules"]
    out: list[tuple[str, str, dict, int | None]] = []
    for letter in "ABC":
        for row in m[letter]:
            count = {"A": 9, "B": 6, "C": 8}[letter]
            out.append((letter, f"{letter}-site-{row['site']:02d}", row, count))
    for row in m["D"]["families"]:
        out.append(("D", f"D-family-{row['family']:02d}", row, row["printed_workload_tones"]))
    for row in m["E"]:
        out.append(("E", f"E-pair-{row['position']:02d}", row, row["written_tones"]))
    for lick in m["F"]:
        for row in lick["positions"]:
            out.append(("F", f"F-lick-{lick['core_lick']}-position-{row['position']:02d}",
                        {"core_lick": lick["core_lick"], "degree_formula": lick["degree_formula"],
                         "position": row}, row["written_tones"]))
    for row in m["G"]:
        out.append(("G", f"G-conversation-{row['conversation']:02d}", row, row["written_tones"]))
    for row in m["H"]:
        out.append(("H", f"H-ending-pair-{row['position']:02d}", row, row["written_tones"]))
    for row in m["I"]:
        out.append(("I", f"I-model-{row['model']:02d}", row, row["printed_workload_tones"]))
    j = m["J"]
    for row in j["openings"]:
        out.append(("J", f"J-opening-{row['label']}", row, None))
    for row in j["endings"]:
        out.append(("J", f"J-ending-{row['label']}", row, None))
    for row in j["all_combinations"]:
        out.append(("J", f"J-combination-{row['opening']}-{row['ending']}", row, None))
    for ordinal, row in enumerate(j["model_combinations_raw"], 1):
        out.append(("J", f"J-printed-model-{ordinal:02d}",
                    {"printed_model_raw": row, "pdf_page": j["pdf_page"],
                     "txt_ref": j["txt_ref"]}, None))
    return out


def task_refs(task: object, module: str, c: dict) -> list[str]:
    refs: set[str] = set()

    def visit(value: object) -> None:
        if isinstance(value, dict):
            if isinstance(value.get("txt_ref"), str):
                refs.add(value["txt_ref"])
            if isinstance(value.get("pdf_page"), int):
                refs.add(f"L44-PDF-p{value['pdf_page']}")
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(task)
    refs.add(c["module_sections"][module]["txt_ref"])
    refs.update(f"L44-PDF-p{page}" for page in c["module_sections"][module]["pdf_pages"])
    return sorted(refs)


def project(c: dict, replayed: dict, catalog: dict) -> dict:
    check_candidate(c, replayed)
    rows = []
    for module, key, task, tones in tasks(c):
        rows.append({
            "source_local_key": key, "source_module": module,
            "source_task": copy.deepcopy(task), "source_task_sha256": sha(encoded(task)),
            "source_count_backed_tones": tones,
            "source_count_meaning": "printed_workload_or_written_tones_not_pick_attacks" if tones is not None else None,
            "playable_pick_attacks": None,
            "schema1_fields": {
                "id": None, "workbook_id": None, "module_id": None,
                "lineage": None, "content_revision": None, "legacy_level": 44,
                "title": key, "kind": "unallocated_source_task",
                "runtime_eligible": False, "events": [], "variants": [],
                "pitch": None, "route": None, "performed_result": None,
                "source_refs": task_refs(task, module, c),
                "timing": {"status": "unresolved", "onset_q": None,
                           "duration_q": None, "fixed_bpm": None,
                           "click_pattern": None, "exact_microtiming_ms": None},
                "resource_requirements": [], "ambiguities": AMBIGUITIES,
            },
        })
    counts = {x: sum(r["source_module"] == x for r in rows) for x in COUNTS}
    need(len(rows) == 79 and counts == COUNTS and
         sum(r["source_count_backed_tones"] or 0 for r in rows) == 582 and
         len({r["source_local_key"] for r in rows}) == 79 and
         all(r["schema1_fields"]["events"] == [] and
             r["schema1_fields"]["id"] is None for r in rows),
         "PROJECTION_COUNTS")
    return {
        "schema": "fathom.detached.curriculum.level044.schema1-unallocated.r01",
        "wbs": "2.3.1.1.1", "level": 44, "section": "V",
        "status": "detached_proposal_pending_curriculum_and_admission",
        "whole_source_candidate": {"path": str(CANDIDATE), "sha256": PINS[CANDIDATE]},
        "schema_freeze_sha256": PINS[Path("Results/primary/20260912T100538Z-2.1.1.2.1-r02-evidence/schema-freeze.json")],
        "current_catalog": catalog, "source_identities": c["source"],
        "source_context": {"key": c["key"], "core_notes": c["core_notes"],
                           "core_degrees": c["core_degrees"],
                           "marked_support_notes": c["marked_support_notes"],
                           "module_sections": c["module_sections"],
                           "source_map_rows": c["source_map_rows"],
                           "source_guidance": c["source_guidance"],
                           "source_differences": c["source_differences"],
                           "module_D_rhythm_templates_raw": c["modules"]["D"]["rhythm_templates_raw"],
                           "module_J_full_source": c["modules"]["J"]},
        "module_count": 10, "source_task_count": 79,
        "source_task_count_by_module": counts,
        "pdf_printed_workload_by_module": TONES,
        "pdf_printed_total_tones": 646,
        "module_J_printed_workload_tones": 64,
        "module_J_implied_full_combination_degree_occurrences": 128,
        "module_J_count_status": "unresolved_source_counting_convention",
        "playable_event_count": 0, "playable_pick_attack_count": None,
        "canonical_ids_allocated": False, "schema1_imported": False,
        "whole_workbook_accepted": False, "runtime_eligible": False,
        "rows": rows, "unresolved": AMBIGUITIES,
    }


def build() -> dict:
    check_pins()
    replayed = source_tool.build_candidate(ROOT)
    candidate = json.loads((ROOT / CANDIDATE).read_text())
    check_candidate(candidate, replayed)
    return project(candidate, replayed, check_current_catalog(candidate))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("build", "verify"))
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    need(output.is_relative_to(OUT.resolve()), "OUTPUT_SCOPE")
    payload = encoded(build())
    if args.mode == "build":
        need(not output.exists(), "OUTPUT_EXISTS")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(payload)
    else:
        need(output.is_file() and output.read_bytes() == payload, "PROJECTION_DRIFT")
    print("PASS: Level44 schema1; 79 source tasks, 646 printed module tones, "
          "J 64-versus-128 unresolved, zero playable events")


if __name__ == "__main__":
    main()
