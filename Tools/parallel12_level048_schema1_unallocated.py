#!/usr/bin/env python3
"""Replay Level48 source and propose only supported unallocated schema1 fields."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader

import curriculum_level048_whole_candidate as p04

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_A = p04.BUILD_REL / "candidate-01.json"
CANDIDATE_B = p04.BUILD_REL / "candidate-02.json"
RESULT = Path("Results/parallel-04/exercises/conversion/20260923T160059Z-2.3.1.1.1-level048-whole-source-candidate-r04-results.md")
PACKAGE = Path("Content/controls/curriculum-v1/package.json")
REGISTRY = Path("Content/controls/curriculum-v1/identity-registry.json")
OUT = Path("Build/parallel-12/level048-schema1-unallocated-r01")
PINS = {
    CANDIDATE_A: (498914, "f0dcaa2f593f141a5d60278329b95cca64141bc587fde2ff597db3f4c220b8c9"),
    CANDIDATE_B: (498914, "f0dcaa2f593f141a5d60278329b95cca64141bc587fde2ff597db3f4c220b8c9"),
    RESULT: (None, "4bd3e308ede2ea77e4ced02048335fd6bb92c56f4bb21e464f473c328c574798"),
    p04.TXT_REL: (p04.TXT_BYTES, p04.TXT_SHA256),
    p04.PDF_REL: (p04.PDF_BYTES, p04.PDF_SHA256),
    p04.MAP_REL: (p04.MAP_BYTES, p04.MAP_SHA256),
    p04.P03_RESULT_REL: (None, p04.P03_RESULT_SHA256),
    PACKAGE: (None, "766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255"),
    REGISTRY: (None, "5d265859e1e8a5a530a0e53d88b019a1c920f3bba6cccb4ef0fef2f7640007e5"),
}
FIELDS = {"id", "workbook_id", "module_id", "legacy_level", "title", "kind", "content_revision",
          "status", "runtime_eligible", "source_refs", "authored_text_refs", "normalization", "context",
          "events", "timing", "rubric", "resource_requirements", "ambiguities", "control_scope",
          "variants", "lineage"}
MODULE_COUNTS = {"A": (57, 38), "B": (92, 77), "C": (47, 30), "D": (60, 59),
                 "E": (60, 57), "F": (66, 62), "G": (71, 46), "H": (75, 68),
                 "I": (60, 57), "J": (26, 23)}
EXPECTED_CELL_COUNTS = {"A": 10, "B": 4, "C": 8, "D": 3, "E": 3,
                        "F": 12, "G": 12, "H": 12, "I": 6, "J": 6}


class ProposalError(ValueError):
    pass


def need(ok: bool, code: str) -> None:
    if not ok:
        raise ProposalError(code)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def encode(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def pin(root: Path = ROOT) -> None:
    need(root.resolve() == ROOT.resolve(), "ROOT_DRIFT")
    for path, (length, digest) in PINS.items():
        raw = (root / path).read_bytes()
        need((length is None or len(raw) == length) and sha(raw) == digest, f"INPUT_DRIFT {path}")


def verify_degree_contexts_shape(events: list[dict]) -> None:
    for event in events:
        value = event.get("degree_contexts")
        if event.get("kind") == "rest" and value is None:
            continue
        need(isinstance(value, dict) and all(isinstance(key, str) and isinstance(item, dict)
                                              for key, item in value.items()), "DEGREE_CONTEXTS_SHAPE")


def authored_counts(candidate: dict) -> dict:
    lines = candidate["txt_source"]["raw_text"].splitlines()
    counts = {}
    for line in lines[32:42]:
        match = re.fullmatch(r"([A-J]) - .+: (\d+) sounding tones / (\d+) pick attacks\.", line)
        need(match is not None, "AUTHORED_MODULE_COUNT_ROW")
        module, sounding, attacks = match.groups()
        counts[module] = {"sounding_tones": int(sounding), "pick_attacks": int(attacks),
                          "txt_ref": f"L48-TXT{lines.index(line) + 1}"}
    need({key: (value["sounding_tones"], value["pick_attacks"]) for key, value in counts.items()} ==
         MODULE_COUNTS and sum(value["sounding_tones"] for value in counts.values()) == 614 and
         sum(value["pick_attacks"] for value in counts.values()) == 517 and
         lines[42] == "Complete written workout: 614 sounding tones / 517 pick attacks, before the free capstone.",
         "AUTHORED_CORE_COUNT_DRIFT")
    return {"modules": counts, "total": {"sounding_tones": 614, "pick_attacks": 517,
                                          "txt_ref": "L48-TXT43"},
            "classification": "authored_source_claim_not_projected_events_or_performed_outcome"}


def representative_context(package: dict, registry: dict) -> dict:
    matching = [record for record in package["records"] if record.get("legacy_level") == 48]
    need(len(package["records"]) == 659 and len(matching) == 1, "CURRENT659_LEVEL48_SCOPE")
    record = matching[0]
    need(record["id"] == "fg:item:000007" and record["workbook_id"] == "fg:workbook:000048" and
         record["module_id"] == "fg:module:000007" and record["content_revision"] == 3 and
         record["control_scope"]["extent"] == "selected_illustration" and
         record["control_scope"]["whole_workbook_complete"] is False and
         record["runtime_eligible"] is False and len(record["events"]) == 16,
         "CURRENT659_REPRESENTATIVE_DRIFT")
    verify_degree_contexts_shape(record["events"])
    identities = [entity for entity in registry["entities"] if entity.get("id") == "fg:workbook:000048" or
                  entity.get("parent") == "fg:workbook:000048"]
    need({entity["id"] for entity in identities} == {"fg:workbook:000048", "fg:module:000007"},
         "CURRENT659_IDENTITY_DRIFT")
    return {"id": record["id"], "workbook_id": record["workbook_id"],
            "module_id": record["module_id"], "content_revision": record["content_revision"],
            "record_sha256": sha(encode(record)), "status": record["status"],
            "runtime_eligible": record["runtime_eligible"], "source_refs": record["source_refs"],
            "authored_text_refs": record["authored_text_refs"],
            "control_scope": record["control_scope"], "lineage": record["lineage"],
            "event_count": len(record["events"]), "variant_count": len(record["variants"]),
            "overlapping_new_source_cells": ["L48-cell-001", "L48-cell-002"],
            "identity_role": "read_only_selected_representative_not_new_allocation"}


def preserve_sources(candidate: dict, txt_raw: bytes, pdf_raw: bytes) -> dict:
    need(candidate["txt_source"]["raw_text"].encode() == txt_raw and
         len(candidate["txt_source"]["lines"]) == 1246 and
         [line["line"] for line in candidate["txt_source"]["lines"]] == list(range(1, 1247)),
         "TXT_PRESERVATION_DRIFT")
    reader = PdfReader(BytesIO(pdf_raw), strict=True)
    pages = candidate["pdf_source"]["pages"]
    need(len(reader.pages) == len(pages) == 22, "PDF_PRESERVATION_BOUNDARY")
    for index, page in enumerate(pages, 1):
        text = reader.pages[index - 1].extract_text() or ""
        need(page["page"] == index and page["extracted_text"] == text and
             page["text_sha256"] == sha(text.encode()), "PDF_PAGE_TEXT_DRIFT")
    need(candidate["source_coverage"]["txt_line_count"] == 1246 and
         candidate["source_coverage"]["pdf_page_count"] == 22 and
         len(candidate["txt_notation_cells"]) == 76 and
         len(candidate["source_difference_ledger"]) == 5, "SOURCE_COVERAGE")
    preserved = {"version": "parallel12-level048-whole-original-preservation.1",
                 "classification": "pinned_original_forms_without_txt_pdf_precedence_or_admission",
                 "source_candidate": candidate,
                 "source_candidate_sha256": PINS[CANDIDATE_A][1],
                 "original_txt_sha256": sha(txt_raw), "original_pdf_sha256": sha(pdf_raw),
                 "authored_counts": authored_counts(candidate),
                 "source_precedence_selected": None,
                 "schema1_projection_allowed_after_parity": True,
                 "canonical_allocation_allowed": False}
    verify_preservation(preserved, txt_raw, pdf_raw)
    return preserved


def verify_preservation(preserved: dict, txt_raw: bytes, pdf_raw: bytes) -> None:
    candidate = preserved["source_candidate"]
    need(preserved["source_candidate_sha256"] == PINS[CANDIDATE_A][1] and
         preserved["original_txt_sha256"] == sha(txt_raw) and
         preserved["original_pdf_sha256"] == sha(pdf_raw) and
         preserved["source_precedence_selected"] is None and
         preserved["schema1_projection_allowed_after_parity"] is True and
         preserved["canonical_allocation_allowed"] is False and
         candidate["txt_source"]["raw_text"].encode() == txt_raw and
         len(candidate["txt_source"]["lines"]) == 1246 and
         len(candidate["pdf_source"]["pages"]) == 22 and
         len(candidate["txt_notation_cells"]) == 76 and
         preserved["authored_counts"] == authored_counts(candidate), "SOURCE_PRESERVATION_DRIFT")
    reader = PdfReader(BytesIO(pdf_raw), strict=True)
    for index, page in enumerate(candidate["pdf_source"]["pages"], 1):
        text = reader.pages[index - 1].extract_text() or ""
        need(page["page"] == index and page["extracted_text"] == text and
             page["text_sha256"] == sha(text.encode()), "PDF_PAGE_TEXT_DRIFT")


def section_record(section: dict, candidate: dict, counts: dict) -> dict:
    label = section.get("module", section.get("id"))
    local = f"L48-section-{label}"
    first, last = section["txt_line_range"]
    lines = candidate["txt_source"]["raw_text"].splitlines()
    text = "\n".join(lines[first - 1:last])
    pages = [candidate["pdf_source"]["pages"][number - 1] for number in section["pdf_pages"]]
    refs = [section["txt_ref"], *section["pdf_refs"]]
    source_count = counts["modules"].get(label)
    context = {"local_code": local, "source_section": section, "source_txt_text": text,
               "source_pdf_pages": [{"page": page["page"], "text": page["extracted_text"]}
                                    for page in pages],
               "source_authored_module_count": source_count,
               "source_task_scope": "section_text_and_independent_pdf_page_text",
               "source_precedence_selected": None, "unresolved_degree_contexts": {}}
    fields = base_fields(local, section.get("title", label), "instruction", refs, context,
                         ["Independent TXT and PDF wordings require Curriculum reconciliation before semantics or scoring."])
    return {"source_local_key": local, "case_type": "section", "module": section.get("module"),
            "source_section": section, "schema1_fields": fields,
            "identity_state": "unallocated", "schema1_importable": False,
            "source_event_geometry_status": "not_projected_from_structural_source",
            "open_gaps": ["TXT/PDF precedence and semantics", "identities and lineage",
                          "runtime timing and admission"]}


def cell_record(cell: dict, candidate: dict) -> dict:
    ordinal, module = cell["ordinal"], cell["module"]
    local = f"L48-cell-{ordinal:03d}"
    module_info = next(section for section in candidate["source_coverage"]["sections_in_source_order"]
                       if section.get("module") == module)
    rows = cell["rows"]
    labels = [row["kind"] for row in rows if row["kind"] != "TAB"]
    need(labels in (list(p04.TABLE_LABELS), ["Cnt", "Nte", "Deg", "Rol", "Atk"]) and
         len([row for row in rows if row["kind"] == "TAB"]) == 6 and
         cell["txt_line_range"][0] <= cell["txt_line_range"][1], "CELL_SOURCE_ROWS")
    ref = cell["txt_ref"]
    refs = [ref, *module_info["pdf_refs"]]
    indexed = {row["kind"]: row["raw"] for row in rows if row["kind"] != "TAB"}
    context = {"local_code": local, "source_module": module, "source_cell_ordinal": ordinal,
               "source_txt_line_range": cell["txt_line_range"], "source_rows": rows,
               "source_count_row": indexed["Cnt"], "source_note_row": indexed["Nte"],
               "source_degree_row": indexed["Deg"], "source_color_row": indexed.get("Col"),
               "source_role_row": indexed["Rol"], "source_attack_row": indexed["Atk"],
               "source_tab_rows": [row for row in rows if row["kind"] == "TAB"],
               "source_pdf_module_pages": module_info["pdf_pages"],
               "pdf_cell_match_status": "unresolved_independent_form_coverage",
               "source_precedence_selected": None, "unresolved_degree_contexts": {}}
    fields = base_fields(local, f"Level48 Module {module} printed cell {ordinal:03d}",
                         "notation", refs, context,
                         ["ASCII columns and printed count row are source notation, not allocated event timing.",
                          "No source-backed one-to-one TXT/PDF cell event geometry or performed attack mapping is assigned."])
    return {"source_local_key": local, "case_type": "txt_notation_cell", "module": module,
            "cell_ordinal": ordinal, "source_cell": cell, "schema1_fields": fields,
            "identity_state": "unallocated", "schema1_importable": False,
            "source_event_geometry_status": "not_projected_from_structural_source",
            "read_only_representative_overlap": ordinal in (1, 2),
            "open_gaps": ["TXT/PDF cell reconciliation", "note/attack geometry and timing",
                          "identities, lineage and admission"]}


def base_fields(local: str, title: str, kind: str, refs: list[str], context: dict,
                ambiguities: list[str]) -> dict:
    fields = {"id": None, "workbook_id": None, "module_id": None, "legacy_level": 48,
              "title": title, "kind": kind, "content_revision": None,
              "status": "converted_candidate", "runtime_eligible": False,
              "source_refs": refs, "authored_text_refs": refs,
              "normalization": [{"kind": "representation_metadata",
                                 "basis": "P04 whole-Level48 structural source candidate and complete original TXT/PDF",
                                 "text": "Literal source rows, prose and independent PDF coverage are retained; event semantics remain unresolved."}],
              "context": context, "events": [],
              "timing": {"status": "unresolved", "unit": "quarter",
                         "basis": "ASCII grid and rest wording do not assign a verified performance clock",
                         "selected_pulse": None},
              "rubric": None, "resource_requirements": [], "ambiguities": ambiguities,
              "control_scope": {"local_case": local, "extent": "source_preservation_candidate",
                                "whole_workbook_complete": False, "source_event_count": None,
                                "basis_refs": refs,
                                "unresolved": ["Musical event geometry, identity, timing, lineage and admission pending."]},
              "variants": [], "lineage": None}
    need(set(fields) == FIELDS and isinstance(context["unresolved_degree_contexts"], dict), "FIELD_SHAPE")
    return fields


def build(root: Path = ROOT, candidate_override: dict | None = None) -> tuple[dict, dict, dict]:
    pin(root)
    candidate = candidate_override if candidate_override is not None else json.loads((root / CANDIDATE_A).read_text())
    need((root / CANDIDATE_A).read_bytes() == (root / CANDIDATE_B).read_bytes(), "P04_TWIN_DRIFT")
    rebuilt = p04.build_candidate(txt_data=(root / p04.TXT_REL).read_bytes(),
                                   pdf_data=(root / p04.PDF_REL).read_bytes(),
                                   map_data=(root / p04.MAP_REL).read_bytes(),
                                   prior_result_data=(root / p04.P03_RESULT_REL).read_bytes())
    need(candidate == rebuilt, "P04_SOURCE_CANDIDATE_DRIFT")
    need(candidate["candidate_status"] == "pending-source-reconciliation" and
         candidate["identity_state"]["preexisting_source_map_representative_reference_only"] == "fg:item:000007" and
         candidate["identity_state"]["new_stable_identity_created_by_lane"] is False and
         all(candidate["release_state"][key] is False for key in
             ("runtime_eligible", "imported", "admitted", "curriculum_accepted")) and
         candidate["timing_state"]["derived_onsets_or_durations_created"] is False,
         "SOURCE_SCOPE")
    preserved = preserve_sources(candidate, (root / p04.TXT_REL).read_bytes(),
                                 (root / p04.PDF_REL).read_bytes())
    representative = representative_context(json.loads((root / PACKAGE).read_text()),
                                            json.loads((root / REGISTRY).read_text()))
    counts = preserved["authored_counts"]
    sections = candidate["source_coverage"]["sections_in_source_order"]
    section_records = [section_record(section, candidate, counts) for section in sections]
    cell_records = [cell_record(cell, candidate) for cell in candidate["txt_notation_cells"]]
    need(len(section_records) == 14 and len(cell_records) == 76 and
         [cell["cell_ordinal"] for cell in cell_records] == list(range(1, 77)) and
         {module: sum(cell["module"] == module for cell in cell_records) for module in EXPECTED_CELL_COUNTS} ==
         EXPECTED_CELL_COUNTS and
         candidate["source_coverage"]["txt_table_row_counts"] == p04.EXPECTED_TXT_COUNTS and
         candidate["source_coverage"]["pdf_extracted_table_row_counts"] == p04.EXPECTED_PDF_COUNTS and
         candidate["source_coverage"]["txt_tab_row_count"] == 456 and
         candidate["source_coverage"]["pdf_extracted_tab_row_count"] == 438,
         "WHOLE_LEVEL_COVERAGE")
    summary = {"section_cases": 14, "notation_cell_cases": 76, "total_source_cases": 90,
               "projected_events": 0, "projected_variants": 0,
               "authored_core_sounding_tones_claim": 614,
               "authored_core_pick_attacks_claim": 517,
               "txt_lines": 1246, "pdf_pages": 22,
               "txt_table_row_counts": p04.EXPECTED_TXT_COUNTS,
               "pdf_extracted_table_row_counts": p04.EXPECTED_PDF_COUNTS,
               "txt_tab_rows": 456, "pdf_extracted_tab_rows": 438,
               "source_difference_ledger_entries": 5}
    proposal = {"proposal_version": "parallel12-level048-unallocated-schema1-fields.1",
                "classification": "source_mapped_structural_field_proposal_not_schema1_importable",
                "legacy_level": 48,
                "source_pins": {str(path): {"bytes": (root / path).stat().st_size, "sha256": digest}
                                for path, (_, digest) in PINS.items()},
                "source_preservation_sha256": sha(encode(preserved)), "counts": summary,
                "authored_counts": counts,
                "source_difference_ledger": candidate["source_difference_ledger"],
                "source_map_level48_row": candidate["source_map"]["level48_row"],
                "selected_representative_read_only": representative,
                "source_precedence_selected": None,
                "current659_level48_records": 1, "representative_collision": representative["id"],
                "canonical_ids_allocated": False, "runtime_eligible": False, "admitted": False,
                "fixed_bpm": None, "note_per_click": None, "onset_q": None, "duration_q": None,
                "records": section_records + cell_records}
    handoff = {"version": "parallel12-level048-allocation-handoff.1",
               "status": "pending_P02_representative_lineage_and_source_reconciliation",
               "source_preservation_sha256": sha(encode(preserved)),
               "proposal_sha256": sha(encode(proposal)),
               "section_source_map": [{"source_local_key": record["source_local_key"],
                                       "source_section": record["source_section"]}
                                      for record in section_records],
               "cell_source_map": [{"source_local_key": record["source_local_key"],
                                    "source_ref": record["source_cell"]["txt_ref"],
                                    "module": record["module"]} for record in cell_records],
               "selected_representative_read_only": representative,
               "source_difference_ledger": candidate["source_difference_ledger"],
               "source_precedence_selected": None, "section_case_count": 14,
               "cell_case_count": 76, "projected_event_count": 0,
               "current659_level48_records": 1, "representative_collision": representative["id"],
               "decisions_required": ["P02 lineage and identity plan for selected fg:item:000007 versus whole-Level48 cases",
                                      "Curriculum TXT/PDF row precedence, module-J recovery-grid omission, rubric wording and historical next-section ambiguity",
                                      "Musical note/attack semantics, timing/click, performance and admission before import"],
               "selected_choice": None, "allocation_allowed": False, "no_admission": True}
    verify_projection(preserved, proposal, handoff, candidate)
    return preserved, proposal, handoff


def verify_projection(preserved: dict, proposal: dict, handoff: dict, candidate: dict) -> dict:
    need(preserved["schema1_projection_allowed_after_parity"] is True and
         proposal["source_preservation_sha256"] == handoff["source_preservation_sha256"] == sha(encode(preserved)),
         "PARITY_GATE")
    need(proposal["canonical_ids_allocated"] is False and proposal["runtime_eligible"] is False and
         proposal["admitted"] is False and proposal["source_precedence_selected"] is None and
         handoff["source_precedence_selected"] is None and handoff["allocation_allowed"] is False and
         handoff["no_admission"] is True and handoff["selected_choice"] is None and
         all(proposal[key] is None for key in ("fixed_bpm", "note_per_click", "onset_q", "duration_q")),
         "INVALID_AUTHORITY")
    need(proposal["counts"]["section_cases"] == handoff["section_case_count"] == 14 and
         proposal["counts"]["notation_cell_cases"] == handoff["cell_case_count"] == 76 and
         proposal["counts"]["total_source_cases"] == len(proposal["records"]) == 90 and
         proposal["counts"]["projected_events"] == handoff["projected_event_count"] == 0 and
         proposal["counts"]["authored_core_sounding_tones_claim"] == 614 and
         proposal["counts"]["authored_core_pick_attacks_claim"] == 517 and
         proposal["authored_counts"] == preserved["authored_counts"] == authored_counts(candidate),
         "COVERAGE")
    sections = candidate["source_coverage"]["sections_in_source_order"]
    cells = candidate["txt_notation_cells"]
    expected = ([section_record(section, candidate, preserved["authored_counts"])
                 for section in sections] +
                [cell_record(cell, candidate) for cell in cells])
    need([record["source_local_key"] for record in proposal["records"]] ==
         [record["source_local_key"] for record in expected] and
         [entry["source_local_key"] for entry in handoff["section_source_map"]] ==
         [record["source_local_key"] for record in expected[:14]] and
         [entry["source_local_key"] for entry in handoff["cell_source_map"]] ==
         [record["source_local_key"] for record in expected[14:]], "SOURCE_CASE_ORDER")
    for record, baseline in zip(proposal["records"], expected, strict=True):
        fields = record["schema1_fields"]
        need(record["identity_state"] == "unallocated" and record["schema1_importable"] is False and
             set(fields) == FIELDS and fields["legacy_level"] == 48 and
             fields["context"]["local_code"] == record["source_local_key"] and
             all(fields[key] is None for key in ("id", "workbook_id", "module_id", "content_revision", "lineage")) and
             fields["runtime_eligible"] is False and fields["timing"]["status"] == "unresolved" and
             fields["timing"]["selected_pulse"] is None and
             fields["events"] == fields["variants"] == [] and
             isinstance(fields["context"]["unresolved_degree_contexts"], dict), "INVALID_AUTHORITY")
        verify_degree_contexts_shape(fields["events"])
        need(record == baseline, "SOURCE_FIELD_DRIFT")
    need(proposal["source_difference_ledger"] == handoff["source_difference_ledger"] ==
         candidate["source_difference_ledger"] and
         proposal["selected_representative_read_only"] == handoff["selected_representative_read_only"] and
         proposal["selected_representative_read_only"]["id"] == "fg:item:000007" and
         proposal["current659_level48_records"] == handoff["current659_level48_records"] == 1 and
         proposal["representative_collision"] == handoff["representative_collision"] == "fg:item:000007" and
         handoff["proposal_sha256"] == sha(encode(proposal)),
         "REPRESENTATIVE_OR_PROPOSAL_DRIFT")
    return proposal["counts"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("build", "verify"))
    args = parser.parse_args()
    preserved, proposal, handoff = build()
    outputs = {"source-preservation.json": preserved,
               "field-proposal.json": proposal,
               "allocation-handoff.json": handoff}
    if args.command == "build":
        (ROOT / OUT).mkdir(parents=True, exist_ok=True)
        for name, value in outputs.items():
            (ROOT / OUT / name).write_bytes(encode(value))
    else:
        for name, value in outputs.items():
            need((ROOT / OUT / name).read_bytes() == encode(value), f"OUTPUT_DRIFT {name}")
    print(json.dumps({"status": "level048_unallocated_pending_P02_reconciliation",
                      "counts": verify_projection(preserved, proposal, handoff,
                                                  json.loads((ROOT / CANDIDATE_A).read_text()))}, sort_keys=True))


if __name__ == "__main__":
    main()
