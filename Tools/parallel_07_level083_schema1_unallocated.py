#!/usr/bin/env python3
"""Project sealed whole-Level83 semantics into detached unallocated schema1 fields."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = Path("Build/parallel-07/2.3.1.3.1-level083-schema1-unallocated-r01")
STEM = "Guitar_Exercises_Section_XI_Level_83_Melody_Harmonization_Chord_Substitution_Reharmonization_and_Fixed_Top_Line_Control"
TXT = f"Notes/music/guitar project/TXT version/{STEM}.txt"
PDF = f"Notes/music/guitar project/PDF version/{STEM}.pdf"
WHOLE = "Build/parallel-09/2.3.1.3.1-level083-whole-semantic-r01/level083-whole-semantic-candidate.json"
APPENDIX = "Results/parallel-01/exercises/conversion/20260923T024322Z-2.3.1.3.1-level-083-pdf-source-appendix-r01-evidence/level083-pdf-source-candidate.json"
COVERAGE = "Content/controls/curriculum-v1/workbook-coverage.json"
MAP = "Results/parallel-01/exercises/inventory/20260922T180500Z-2.3-curriculum-v1-source-inventory-evidence/curriculum-source-map.json"
PACKAGE = "Content/controls/curriculum-v1/package.json"
REGISTRY = "Content/controls/curriculum-v1/identity-registry.json"
GENERATION = "Content/controls/curriculum-v1/generation.json"
INPUTS = {
    WHOLE: "85852bb53a7e7d7e2e47aeb99d4c01fc49b285c86c1ddfeb9efe7ad1f554b000",
    APPENDIX: "a66c90b853d32bf9c2cfc5ceac67db8eb404ac269bf4aeb9f5a0f12f96993e4c",
    TXT: "12561dfc8c1d81b710cb2d429b52e2d9574ea5fd7bfa65d0bf1f1b575682bb85",
    PDF: "3571f063bdafa8a3acb9a52f542d6f490516d75e325f55ea29915111659e5c5c",
    COVERAGE: "d8e492101c97c60add858799c77da4db3f0c528d348c9cf66105c2dc37df4eeb",
    MAP: "bad5581a04f43ba8baf14db430449e1ccff5cf88f0f7e42198328073b27053d6",
    PACKAGE: "766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255",
    REGISTRY: "5d265859e1e8a5a530a0e53d88b019a1c920f3bba6cccb4ef0fef2f7640007e5",
    GENERATION: "fc6cec9f9d67eb82c97c5f4c3fb95d285178fb7fce7bd147d9ae0296d21b4c1c",
}
COUNTS = {"A": 96, "B": 128, "C": 112, "D": 112, "E": 128,
          "F": 112, "G": 96, "H": 160, "I": 192, "J": 64}
PAGES = {"A": [2, 3, 4, 5, 6, 7, 8, 9], "B": [2, 3, 4, 5, 6, 7, 8, 9],
         "C": [10], "D": [11], "E": [12], "F": [13], "G": [14],
         "H": [15, 16, 17, 18], "I": [19], "J": [20]}
UNRESOLVED = [
    "New workbook/module/item/task/event/variant identities, content revision and lineage are unallocated.",
    "1,200 written module-level slots have no source-authorized row/bar assignment or note-level playable mapping.",
    "PDF pages 3–9 jointly label Module A/B; individual candidate rows are not exclusive to A or B.",
    "Pitch, route, string/fret, rhythm, duration, accent, grading, playback and performed mastery remain unresolved.",
    "Page-19 capstone title overlaps the first phase line in the rendered source; extracted text remains recoverable.",
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
    data = {rel: json.loads(raw[rel]) for rel in (WHOLE, APPENDIX, COVERAGE, MAP, PACKAGE, REGISTRY, GENERATION)}
    data[TXT] = raw[TXT].decode("utf-8").splitlines()
    return data


def identity_boundary(data: dict) -> dict:
    foundation, registry, generation = data[PACKAGE], data[REGISTRY], data[GENERATION]
    workbook, representative = "fg:workbook:000083", "fg:item:000011"
    if len(foundation["records"]) != 659 or generation["records"] != 659:
        raise ValueError("current659 foundation drift")
    records = [r for r in foundation["records"] if r.get("legacy_level") == 83 or r.get("workbook_id") == workbook]
    if (len(records) != 1 or records[0].get("id") != representative or records[0].get("workbook_id") != workbook
        or records[0].get("control_scope", {}).get("extent") != "task_reference"
        or records[0].get("control_scope", {}).get("source_event_count") != 0
        or records[0].get("runtime_eligible") is not False):
        raise ValueError("frozen Level83 representative record drift")
    entities = [e for e in registry["entities"] if e.get("id") in (workbook, representative)]
    if len(entities) != 2 or {e["id"]: e["kind"] for e in entities} != {workbook: "workbook", representative: "item"}:
        raise ValueError("frozen Level83 representative registry drift")
    entry = next((e for e in foundation["workbook_catalog"]["entries"] if e.get("workbook_id") == workbook), None)
    if (not entry or entry.get("catalog_role") != "read_only_source_preservation"
        or entry.get("review") != "Pending" or entry.get("conversion_status") != "not_converted"
        or entry.get("representative_item_id") != representative
        or any(entry.get(k) is not False for k in ("runtime_eligible", "runtime_admitted", "imported", "admitted", "whole_workbook_complete"))
        or entry.get("playable_projection", {}).get("status") != "explicitly_empty_unresolved"):
        raise ValueError("Level83 source-only catalog boundary drift")
    coverage = next((e for e in data[COVERAGE]["workbook_catalog"]["entries"] if e.get("workbook_id") == workbook), None)
    if coverage != entry:
        raise ValueError("frozen coverage/package catalog parity drift")
    return entry


def validate_source(candidate: dict, appendix: dict, source_map: dict, lines: list[str]) -> None:
    if (candidate.get("schema_status") != "detached_whole_source_semantic_candidate_not_curriculum_record"
        or candidate.get("legacy_level") != 83 or candidate.get("wbs_owner") != "2.3.1.3.1"
        or candidate.get("candidate_status") != "pending_source_reconciliation"
        or candidate.get("workbook_id") != "fg:workbook:000083"
        or candidate.get("written_event_total") != 1200 or len(candidate.get("modules", [])) != 10):
        raise ValueError("whole Level83 candidate scope drift")
    if any(candidate.get(k) is not False for k in ("runtime_eligible", "imported", "admitted",
                                                  "whole_workbook_complete", "stable_ids_assigned_by_this_candidate")):
        raise ValueError("whole Level83 candidate authority drift")
    source = candidate["source_pair"]
    if (source["txt"]["path"] != TXT or source["txt"]["sha256"] != INPUTS[TXT]
        or source["pdf"]["path"] != PDF or source["pdf"]["sha256"] != INPUTS[PDF]
        or source["pdf"]["page_count"] != 20 or len(candidate["pdf_pages"]) != 20):
        raise ValueError("original source identity drift")
    if (len(lines) != 59 or candidate["txt"]["line_count"] != 59
        or candidate["txt"]["lines"] != [{"line": i, "text": line} for i, line in enumerate(lines, 1)]):
        raise ValueError("original TXT semantic archive drift")
    for i, page in enumerate(candidate["pdf_pages"], 1):
        if page["page"] != i or sha(page["extracted_text"].encode()) != page["extracted_text_sha256"]:
            raise ValueError("PDF extracted page identity drift")
    if (candidate["predecessor"]["path"] != APPENDIX or candidate["predecessor"]["sha256"] != INPUTS[APPENDIX]
        or appendix["candidate_scope"]["table_row_count"] != 24
        or appendix["candidate_scope"]["rubric_row_count"] != 8
        or appendix["candidate_scope"]["selected_physical_pdf_pages"] != [19, 20]):
        raise ValueError("P01 literal appendix scope/pin drift")
    for page_no, expected_count, semantic_key in ((19, 24, "printed_bar_table"), (20, 8, "rubric")):
        prior = next(p for p in appendix["pages"] if p["page_number"] == page_no)
        current = candidate["pdf_pages"][page_no - 1]
        if (prior["extracted_text_sha256"] != current["extracted_text_sha256"]
            or prior["pdf_source_sha256"] != INPUTS[PDF]
            or len(prior["candidate_content"]["rows"]) != expected_count
            or len(current["semantic"][semantic_key]) != expected_count):
            raise ValueError("P01 literal appendix/P09 PDF parity drift")
        for literal, semantic in zip(prior["candidate_content"]["rows"], current["semantic"][semantic_key]):
            values = [cell["value"] for cell in literal["cells"]]
            comparable = ([str(semantic["bar"]), semantic["chord"], semantic["top_note"]] if page_no == 19
                          else [semantic["category"], semantic["score_0"], semantic["score_1"], semantic["score_2"]])
            if values != comparable:
                raise ValueError("P01 literal cell/P09 semantic row divergence")
    reconciliation = candidate["source_reconciliation"]
    required = ("reference_matches_A_B_grids", "common_tone_txt_pdf_progressions_match",
                "secondary_txt_pdf_progressions_match", "secondary_txt_does_not_print_top_notes_or_functions",
                "module_A_B_shared_pdf_pages_without_separate_row_allocation",
                "module_counts_not_distributed_to_rows_or_bars",
                "pdf_capstone_table_is_printed_source_not_performed_reharmonization",
                "note_level_playable_fields_unresolved")
    if any(reconciliation.get(k) is not True for k in required):
        raise ValueError("Level83 source reconciliation/ambiguity drift")
    if not any(x.get("pages") == [19] and "overlaps" in x.get("observation", "") for x in candidate["visual_review"]):
        raise ValueError("page-19 visual qualification lost")
    row = next((r for r in source_map["rows"] if r.get("level") == 83), None)
    if (row is None or row.get("txt_sha256") != INPUTS[TXT] or row.get("pdf_sha256") != INPUTS[PDF]
        or row.get("representative_item_id") != "fg:item:000011"
        or row.get("conversion_status") != "converted_candidate_reference"
        or row.get("admitted") is not False or row.get("runtime_eligible") is not False):
        raise ValueError("frozen Level83 source-map representative boundary drift")


def slot_field(slot: dict, ordinal: int) -> dict:
    expected = {"slot", "pitch", "string", "fret", "onset", "duration", "performed_result"}
    if set(slot) != expected or slot["slot"] != ordinal or any(slot[k] is not None for k in expected - {"slot"}):
        raise ValueError("written slot identity/playable drift")
    return {"source_written_slot": slot,
            "schema1_fields": {"event_id": None, "kind": None, "contact": None,
                               "pick": None, "pitch_binding": None, "onset_q": None, "duration_q": None}}


def project(data: dict) -> tuple[dict, dict]:
    candidate, appendix, lines = data[WHOLE], data[APPENDIX], data[TXT]
    entry = identity_boundary(data)
    validate_source(candidate, appendix, data[MAP], lines)
    records = []
    for module, source in zip(COUNTS, candidate["modules"]):
        count = COUNTS[module]
        if (source["module"] != module or source["written_event_count"] != count
            or source["pdf_pages"] != PAGES[module] or source["txt_line"] != 15 + ord(module) - ord("A")
            or source["slot_allocation"] != "module_count_only_unresolved_per_task_and_time"
            or len(source["written_event_slots"]) != count):
            raise ValueError("module written-slot/source-allocation drift")
        fields = [slot_field(slot, i) for i, slot in enumerate(source["written_event_slots"], 1)]
        page_semantics = [{"pdf_page": n, "semantic": candidate["pdf_pages"][n - 1]["semantic"],
                           "allocation": "shared_A_B_unresolved" if module in ("A", "B") and 3 <= n <= 9 else "module_source"}
                          for n in PAGES[module]]
        if module in ("A", "B"):
            if any(page["semantic"].get("allocation_status") != "shared_A_B_heading_no_row_allocation"
                   for page in page_semantics if 3 <= page["pdf_page"] <= 9):
                raise ValueError("shared A/B row-allocation ambiguity lost")
        records.append({"source_component": module, "identity_state": "unallocated",
                        "source_module": {k: source[k] for k in ("module", "title", "txt_line", "pdf_pages", "written_event_count", "slot_allocation")},
                        "source_task_groups": page_semantics,
                        "schema1_fields": {"id": None, "workbook_id": None, "module_id": None,
                                           "legacy_level": 83, "title": f"Level 83 component {module}",
                                           "kind": "mixed", "content_revision": None, "lineage": None,
                                           "runtime_eligible": False, "source_refs": None,
                                           "events": fields,
                                           "variants": [{"id": None, "source_component": module,
                                                         "source_slot_ordinals": list(range(1, count + 1)),
                                                         "event_ids": None, "runtime_eligible": False}],
                                           "resource_requirements": [],
                                           "timing": {"status": "unresolved", "unit": "quarter", "fixed_bpm": None},
                                           "ambiguities": UNRESOLVED}})
    if sum(len(r["schema1_fields"]["events"]) for r in records) != 1200:
        raise ValueError("whole Level83 written-slot total drift")
    capstone = candidate["pdf_pages"][18]["semantic"]
    mastery = candidate["pdf_pages"][19]["semantic"]
    if (capstone["performed_reharmonization"] is not None or mastery["performed_score"] is not None
        or len(capstone["printed_bar_table"]) != 24 or len(mastery["rubric"]) != 8
        or "14/16" not in mastery["pass_condition"] or "two separate days" not in mastery["pass_condition"]):
        raise ValueError("capstone/mastery source criterion drift")
    proposal = {"proposal_version": "level083-unallocated-schema1-fields.1", "wbs_id": "2.3.1.3.1",
                "classification": "Build-only, nonimportable schema1 field proposal", "legacy_level": 83,
                "canonical_ids_allocated_by_this_proposal": False, "schema1_importable": False,
                "whole_workbook_complete": False, "runtime_eligible": False, "admitted": False,
                "frozen_representative_reference": "fg:item:000011",
                "counts": {"components": 10, "source_described_written_slots": 1200, "by_module": COUNTS,
                           "printed_capstone_bars": 24, "rubric_categories": 8},
                "source_pair": candidate["source_pair"], "predecessor": candidate["predecessor"],
                "frozen_catalog_reference": candidate["frozen_catalog"],
                "txt": candidate["txt"], "pdf_pages": candidate["pdf_pages"],
                "source_reconciliation": candidate["source_reconciliation"],
                "visual_review": candidate["visual_review"], "records": records}
    handoff = {"handoff_version": "level083-allocation-handoff.1", "wbs_id": "2.3.1.3.1",
               "catalog_workbook_id": entry["workbook_id"], "catalog_role": entry["catalog_role"],
               "existing_frozen_representative_item_id": "fg:item:000011",
               "existing_level083_representative_records": 1, "existing_workbook_registry_entities": 1,
               "proposed_component_partition": list(COUNTS), "source_described_written_slots": 1200,
               "new_canonical_ids_allocated": False, "admitted": False,
               "required_decisions": ["Resolve shared A/B pages 3–9 row ownership before allocating task/event identities.",
                                      "Review page-19 overlap against original PDF; retain the printed 24-bar table as source, not performance.",
                                      "Allocate slots to authored rows/bars only with Curriculum authority and playable pitch/route/rhythm detail.",
                                      "Preserve the existing representative reference without treating it as whole-workbook admission."]}
    return proposal, handoff


def products(root: Path) -> dict[str, object]:
    proposal, handoff = project(read_inputs(root))
    manifest = {"manifest_version": "level083-input-pins.1", "inputs": [
        {"path": rel, "bytes": (root / rel).stat().st_size, "sha256": digest}
        for rel, digest in INPUTS.items()]}
    summary = {"summary_version": "level083-schema1-unallocated-summary.1",
               "proposal_sha256": sha(encoded(proposal)), "handoff_sha256": sha(encoded(handoff)),
               "source_described_written_slots": 1200, "frozen_representative_item_id": "fg:item:000011",
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
    print(f"LEVEL83 {mode.upper()} PASS written_slots=1200 frozen_representative=fg:item:000011 admitted=false")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("build", "verify"))
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    run(args.mode, args.root.resolve())
