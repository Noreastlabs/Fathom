#!/usr/bin/env python3
"""Build a detached whole-Level64 source-bound schema1 field proposal."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = Path("Build/parallel-07/2.3.1.2.1-level064-schema1-unallocated-r01")
STEM = "Guitar_Exercises_Section_VII_Level_64_Long_Form_Arpeggio_Solo_Construction_Secondary_Dominants_Key_Changes_and_System_Aware_Phrase_Orchestration"
TXT = f"Notes/music/guitar project/TXT version/{STEM}.txt"
PDF = f"Notes/music/guitar project/PDF version/{STEM}.pdf"
WHOLE = "Build/parallel-09/2.3.1.2.1-level064-whole-r01/level064-whole-candidate-03.json"
INDEX = "Build/parallel-01/2.3-level064-whole-coverage-index-r01/candidate-r01.json"
MAP = "Results/parallel-01/exercises/inventory/20260922T180500Z-2.3-curriculum-v1-source-inventory-evidence/curriculum-source-map.json"
PACKAGE = "Content/controls/curriculum-v1/package.json"
REGISTRY = "Content/controls/curriculum-v1/identity-registry.json"
GENERATION = "Content/controls/curriculum-v1/generation.json"
INPUTS = {
    WHOLE: "684e272826c8b9403ea3d9b2a159c7be1c48c19b3ad951119ffb5620fe2dc65d",
    INDEX: "9e9256c41c65656298c97d0e45f88e7430a4256e955f562e5739cef3bbd12c23",
    TXT: "f00e6ef35a1971a91aab67103c69338c4b4a041ca37a100ec857b8537f3f6f24",
    PDF: "70c3179403ca12179f99f072911a76c56c88279e40534030184415e8f6d8a145",
    MAP: "bad5581a04f43ba8baf14db430449e1ccff5cf88f0f7e42198328073b27053d6",
    PACKAGE: "766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255",
    REGISTRY: "5d265859e1e8a5a530a0e53d88b019a1c920f3bba6cccb4ef0fef2f7640007e5",
    GENERATION: "fc6cec9f9d67eb82c97c5f4c3fb95d285178fb7fce7bd147d9ae0296d21b4c1c",
}
COUNTS = {"A": 40, "B": 40, "C": 40, "D": 64, "E": 64,
          "F": 64, "G": 128, "H": 64, "I": 64, "J": 72}
EXPECTED_DISCREPANCIES = {"PDF_ONLY_PRACTICE_LOG_FIELDS", "P01_D_PAGE8_PART_LABEL"}
EXPECTED_EXCEPTIONS = {
    "LEVEL64-PAGES-01-02-REFERENCE-ONLY", "LEVEL64-PAGE20-PRACTICE-LOG-PDF-ONLY",
    "LEVEL64-MODULE-D-PAGE-8-PART-METADATA", "LEVEL64-MODULE-B-PAGE-5-RASTER-LIMIT",
    "LEVEL64-MODULE-J-CARD-TAB-ABSENCE", "LEVEL64-TUNING-UNSPECIFIED",
}
UNRESOLVED = [
    "Canonical workbook/module/item/event/variant IDs, content revision and lineage are unallocated.",
    "No authorized quarter-note onset/duration, fixed BPM, note-per-click or performed mastery.",
    "Tuning is not declared; note tokens and printed TAB do not authorize sounding MIDI pitch.",
    "PDF-only practice-log columns, D page-8 part label and page-5 raster qualification require review.",
    "The 24 recovery-card positions do not print string/fret TAB; their playable contact remains unspecified.",
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
    parsed = {rel: json.loads(raw[rel]) for rel in (WHOLE, INDEX, MAP, PACKAGE, REGISTRY, GENERATION)}
    parsed[TXT] = raw[TXT].decode("utf-8").splitlines()
    return parsed


def identity_boundary(data: dict) -> dict:
    foundation, registry, generation = data[PACKAGE], data[REGISTRY], data[GENERATION]
    workbook = "fg:workbook:000064"
    if len(foundation["records"]) != 659 or generation["records"] != 659:
        raise ValueError("current659 foundation drift")
    if any(r.get("legacy_level") == 64 or r.get("workbook_id") == workbook for r in foundation["records"]):
        raise ValueError("Level64 canonical record already exists")
    if any(e.get("id") == workbook for e in registry["entities"]):
        raise ValueError("Level64 registry entity already exists")
    entry = next((e for e in foundation["workbook_catalog"]["entries"] if e.get("workbook_id") == workbook), None)
    if (not entry or entry.get("conversion_status") != "not_converted" or entry.get("admitted") is not False
        or entry.get("representative_item_id") is not None or entry.get("whole_workbook_complete") is not False):
        raise ValueError("Level64 source-only catalog boundary drift")
    return entry


def check_source_boundary(whole: dict, index: dict, source_map: object, lines: list[str]) -> None:
    if (whole.get("schema") != "fathom-level064-whole-detached-candidate-v1" or whole.get("level") != 64
        or whole.get("wbs_id") != "2.3.1.2.1" or whole.get("complete_written_workout_printed_positions") != 640
        or whole.get("module_printed_position_counts") != COUNTS or len(whole.get("positions", [])) != 640
        or list(whole.get("modules", {})) != list(COUNTS)):
        raise ValueError("whole candidate coverage drift")
    for key in ("canonical_item_id", "canonical_variant_id", "fixed_bpm", "note_per_click", "onset_q",
                "duration_q", "performed_result"):
        if whole.get(key) is not None:
            raise ValueError("whole candidate invented identity/performance")
    for key in ("runtime_eligible", "runtime_admitted", "imported", "admitted", "curriculum_signoff"):
        if whole.get(key) is not False:
            raise ValueError("whole candidate admission drift")
    source = whole["source"]
    if (source["txt_path"] != TXT or source["txt_sha256"] != INPUTS[TXT] or source["txt_lines"] != len(lines) != 669
        or source["pdf_path"] != PDF or source["pdf_sha256"] != INPUTS[PDF] or source["pdf_pages"] != 20
        or whole["txt_document_text"].splitlines() != lines or len(whole["pdf_page_texts"]) != 20):
        raise ValueError("original source identity/text drift")
    if (whole["p01_index_ref"]["path"] != INDEX or whole["p01_index_ref"]["sha256"] != INPUTS[INDEX]
        or index["coverage_scope"]["printed_position_count"] != 640
        or index["coverage_scope"]["source_only_pdf_pages"] != [1, 2, 20]
        or index["coverage_scope"]["module_candidate_pdf_pages"] != list(range(3, 20))
        or index["coverage_scope"]["module_union"] != list(COUNTS)
        or len(index["module_candidate_union"]) != 12):
        raise ValueError("P01 coverage index drift")
    if (index["candidate_status"]["admitted"] is not False
        or index["candidate_status"]["canonical_ids_allocated"] is not False
        or index["candidate_status"]["runtime_eligible"] is not False):
        raise ValueError("P01 coverage index authority drift")
    if {x["code"] for x in whole["source_discrepancies"]} != EXPECTED_DISCREPANCIES:
        raise ValueError("source discrepancy ledger drift")
    if {x["id"] for x in index["coverage_exceptions"]} != EXPECTED_EXCEPTIONS:
        raise ValueError("P01 coverage exceptions drift")
    if whole["source_only_reference_pages"] != [1, 2, 20]:
        raise ValueError("source-only page boundary drift")
    fields = ["Date", "Study / key change", "System", "BPM", "Clean?", "Weak harmony / phrase / system", "Next target"]
    if whole["pdf_only_practice_log_fields"] != fields:
        raise ValueError("PDF-only practice log drift")
    rows = source_map.get("rows", source_map.get("sources", [])) if isinstance(source_map, dict) else source_map
    match = [r for r in rows if str(r.get("level")) == "64"]
    if (len(match) != 1 or match[0].get("txt_sha256") != INPUTS[TXT]
        or match[0].get("pdf_sha256") != INPUTS[PDF]
        or match[0].get("conversion_status") != "not_converted"):
        raise ValueError("frozen source map drift")


def check_slices(whole: dict, index: dict) -> dict[str, dict]:
    entries = {e["candidate_key"]: e for e in index["module_candidate_union"]}
    if len(entries) != 12 or [s["slice_key"] for s in whole["p01_slices"]] != list(entries):
        raise ValueError("P01 slice union/order drift")
    for source in whole["p01_slices"]:
        entry = entries[source["slice_key"]]
        if source["candidate_ref"] != entry["candidate_ref"] or source["result_ref"] != entry["result_ref"]:
            raise ValueError("P01 slice pin drift")
    return entries


def validate_refs(pos: dict, entry: dict, lines: list[str], module: str) -> None:
    refs = pos["source_refs"]
    if not isinstance(refs, dict) or not refs:
        raise ValueError("position source refs absent")
    seen_pdf = False
    seen_txt = False
    for ref in refs.values():
        if isinstance(ref, dict) and ref.get("source") == "pdf":
            if ref.get("path") != PDF or ref.get("page") not in entry["pdf_pages"]:
                raise ValueError("position PDF ref outside slice")
            seen_pdf = True
        elif isinstance(ref, dict) and ref.get("source") == "txt":
            line = ref.get("line")
            if ref.get("path") != TXT or not isinstance(line, int) or not entry["txt_lines"][0] <= line <= entry["txt_lines"][1]:
                raise ValueError("position TXT ref outside slice")
            if not lines[line - 1]:
                raise ValueError("position TXT ref blank")
            seen_txt = True
    if module == "J":
        if refs.get("pdf_page") != 19:
            raise ValueError("J PDF page ref drift")
        for name, value in refs.items():
            if name.startswith("txt_"):
                if not isinstance(value, int) or not entry["txt_lines"][0] <= value <= entry["txt_lines"][1] or not lines[value - 1]:
                    raise ValueError("J TXT line ref drift")
                seen_txt = True
        seen_pdf = True
    if not seen_pdf or not seen_txt:
        raise ValueError("position source refs incomplete")


def position_event(pos: dict, entry: dict, lines: list[str], module: str, ordinal: int) -> dict:
    expected = {"canonical_event_id", "duration_q", "module", "note_token", "onset_q", "path_in_slice",
                "pick_token", "role_token", "slice_key", "sounding_pitch", "source_local_key", "source_order",
                "source_refs", "source_tab"}
    if (set(pos) != expected or pos["module"] != module or pos["source_order"] != ordinal
        or pos["slice_key"] != entry["candidate_key"] or not isinstance(pos["note_token"], str)
        or not isinstance(pos["role_token"], str)
        or (pos["pick_token"] is not None and not isinstance(pos["pick_token"], str))):
        raise ValueError("position token/order drift")
    if any(pos[key] is not None for key in ("canonical_event_id", "onset_q", "duration_q", "sounding_pitch")):
        raise ValueError("position invented identity/timing/pitch")
    check = pos["source_tab"]
    if check is not None and (set(check) != {"string_label", "fret_token"}
                              or check["string_label"] not in ("E", "A", "D", "G", "B", "e")
                              or not str(check["fret_token"]).isdigit()):
        raise ValueError("position printed TAB token drift")
    validate_refs(pos, entry, lines, module)
    return {"source_position": pos,
            "source_tone": {"printed_note": pos["note_token"], "printed_role": pos["role_token"],
                            "printed_pick": pos["pick_token"], "printed_tab": check, "sounding_midi": None},
            "schema1_fields": {"event_id": None, "kind": "contact", "contact": "pitched",
                               "pick": None, "pitch_binding": None, "onset_q": None, "duration_q": None}}


def project(data: dict) -> tuple[dict, dict]:
    whole, index, lines = data[WHOLE], data[INDEX], data[TXT]
    entry = identity_boundary(data)
    check_source_boundary(whole, index, data[MAP], lines)
    slice_entries = check_slices(whole, index)
    records = []
    all_positions = []
    card_without_tab = 0
    bridge_with_tab = 0
    for module, expected_count in COUNTS.items():
        source = whole["modules"][module]
        if source["module"] != module or len(source["positions"]) != expected_count:
            raise ValueError("module position count drift")
        events = []
        for ordinal, pos in enumerate(source["positions"], 1):
            slice_entry = slice_entries[pos["slice_key"]]
            if module not in slice_entry["modules"]:
                raise ValueError("module/slice membership drift")
            events.append(position_event(pos, slice_entry, lines, module, ordinal))
            all_positions.append(pos)
            if module == "J":
                path = pos["path_in_slice"]
                if path[0] == "recovery_cards":
                    if pos["source_tab"] is not None:
                        raise ValueError("J recovery card invented TAB")
                    card_without_tab += 1
                elif path[0] == "modulation_bridges":
                    if pos["source_tab"] is None:
                        raise ValueError("J bridge lost printed TAB")
                    bridge_with_tab += 1
                else:
                    raise ValueError("J source order/path drift")
        source_slices = []
        variants = []
        for slice_source in source["slices"]:
            key = slice_source["slice_key"]
            candidate_ref = slice_entries[key]["candidate_ref"]
            if (slice_source["candidate_ref"] != candidate_ref or slice_source["pdf_pages"] != slice_entries[key]["pdf_pages"]
                or slice_source["txt_lines"] != slice_entries[key]["txt_lines"]):
                raise ValueError("module slice metadata drift")
            ordinals = [n for n, p in enumerate(source["positions"], 1) if p["slice_key"] == key]
            if len(ordinals) != slice_source["printed_position_count"]:
                raise ValueError("module slice count drift")
            source_slices.append({"slice_key": key, "pdf_pages": slice_source["pdf_pages"],
                                  "txt_lines": slice_source["txt_lines"], "candidate_ref": candidate_ref,
                                  "structured_source_candidate": slice_source["structured_source_candidate"]})
            variants.append({"id": None, "source_slice_key": key, "source_event_ordinals": ordinals,
                             "event_ids": None, "runtime_eligible": False})
        records.append({"source_component": module, "identity_state": "unallocated",
                        "source_slices": source_slices,
                        "schema1_fields": {"id": None, "workbook_id": None, "module_id": None,
                                           "legacy_level": 64, "title": f"Level 64 component {module}",
                                           "kind": "mixed", "content_revision": None, "lineage": None,
                                           "runtime_eligible": False, "source_refs": None,
                                           "events": events, "variants": variants,
                                           "resource_requirements": [],
                                           "timing": {"status": "unresolved", "unit": "quarter", "fixed_bpm": None},
                                           "ambiguities": UNRESOLVED}})
    if all_positions != whole["positions"]:
        raise ValueError("whole normalized union/order drift")
    if (card_without_tab, bridge_with_tab) != (24, 48):
        raise ValueError("J card/bridge TAB boundary drift")
    if ([p["path_in_slice"][0] for p in whole["modules"]["J"]["positions"]]
        != ["recovery_cards"] * 24 + ["modulation_bridges"] * 48):
        raise ValueError("J printed ordering drift")
    proposal = {"proposal_version": "level064-unallocated-schema1-fields.1", "wbs_id": "2.3.1.2.1",
                "classification": "Build-only, nonimportable schema1 field proposal", "legacy_level": 64,
                "canonical_ids_allocated": False, "schema1_importable": False,
                "whole_workbook_complete": False, "runtime_eligible": False, "admitted": False,
                "counts": {"components": 10, "p01_slices": 12, "source_described_printed_positions": 640,
                           "by_module": COUNTS, "j_recovery_note_role_positions_without_tab": 24,
                           "j_bridge_positions_with_tab": 48},
                "source": whole["source"], "source_map_boundary": whole["source_map_boundary"],
                "source_only_references": index["source_only_references"],
                "pdf_only_practice_log_fields": whole["pdf_only_practice_log_fields"],
                "source_discrepancies": whole["source_discrepancies"],
                "coverage_exceptions": index["coverage_exceptions"],
                "other_source_limits": whole["other_source_limits"],
                "records": records}
    handoff = {"handoff_version": "level064-allocation-handoff.1", "wbs_id": "2.3.1.2.1",
               "catalog_workbook_id": entry["workbook_id"], "catalog_role": entry["catalog_role"],
               "existing_level064_records": 0, "existing_level064_workbook_entities": 0,
               "proposed_component_partition": list(COUNTS), "source_described_printed_positions": 640,
               "canonical_ids_allocated": False, "admitted": False,
               "required_decisions": ["Review PDF-only page-20 practice-log columns, D page-8 part label and page-5 raster qualification.",
                                      "Review 24 Module J recovery-card note/role positions without TAB before playable mapping.",
                                      "Allocate stable workbook/module/item/event/variant identities and lineage after registry review.",
                                      "Authorize tuning, pitch binding, timing, audio and mastery semantics before native import or runtime admission."]}
    return proposal, handoff


def products(root: Path) -> dict[str, object]:
    proposal, handoff = project(read_inputs(root))
    manifest = {"manifest_version": "level064-input-pins.1", "inputs": [
        {"path": rel, "bytes": (root / rel).stat().st_size, "sha256": digest}
        for rel, digest in INPUTS.items()]}
    summary = {"summary_version": "level064-schema1-unallocated-summary.1",
               "proposal_sha256": sha(encoded(proposal)), "handoff_sha256": sha(encoded(handoff)),
               "source_described_printed_positions": 640, "j_without_tab": 24,
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
    print(f"LEVEL64 {mode.upper()} PASS positions=640 J_without_TAB=24 admitted=false")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("build", "verify"))
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    run(args.mode, args.root.resolve())
