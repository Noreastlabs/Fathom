#!/usr/bin/env python3
"""Whole-Level12 source fields and explicit existing-rung reconciliation, unallocated."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import parallel_07_level012_whole_candidate as p07

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = Path("Build/parallel-07/2.3.1.1.1-level012-whole-r01/candidate.json")
RESULT = Path("Results/parallel-07/conversion/20260923T144316Z-2.3.1.1.1-level012-whole-candidate-r01-results.md")
TXT = p07.TXT_REL
PDF = p07.PDF_REL
FOUNDATION_PACKAGE = Path("Content/controls/curriculum-v1/package.json")
FOUNDATION_REGISTRY = Path("Content/controls/curriculum-v1/identity-registry.json")
OUT = Path("Build/parallel-12/level012-schema1-unallocated-r01")
PINS = {
    CANDIDATE: (76983, "12822706dee2a9ce2dcea906f205270351ba2df901952335410d4f699d0bd7e7"),
    RESULT: (None, "ad469a886c071cd6a9467bdef9f8d8d5fe73b90cfd6fc01bdcccfdeaff297e90"),
    TXT: (13087, "64e65f5293012f9af3c84a885cbdd54c82275f6c6e282c8f8a28cca579631be9"),
    PDF: (18783, "ae31f029a3df324baa8822b913deb499eccc1438f1986967f96889e6eb45bd3b"),
    FOUNDATION_PACKAGE: (None, "766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255"),
    FOUNDATION_REGISTRY: (None, "5d265859e1e8a5a530a0e53d88b019a1c920f3bba6cccb4ef0fef2f7640007e5"),
}
OPEN = {"E": (1, 40), "A": (2, 45), "D": (3, 50)}
PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
DEGREES = [1, 2, 3, 4, 5, 6, 7, 8, 8, 7, 6, 5, 4, 3, 2, 1]
FINGERS = [2, 4, 1, 2, 4, 1, 3, 4, 4, 3, 1, 4, 2, 1, 4, 2]
GUIDANCE = ["L12-TXT1-1-40", "L12-TXT1-224-227", "L12-TXT1-229-231",
            "L12-PDF1-p1", "L12-PDF1-p2"]
FIELDS = {"id", "workbook_id", "module_id", "legacy_level", "title", "kind",
          "content_revision", "status", "runtime_eligible", "source_refs", "authored_text_refs",
          "normalization", "context", "events", "timing", "rubric", "resource_requirements",
          "ambiguities", "control_scope", "variants", "lineage"}


class ProposalError(ValueError):
    pass


def need(ok: bool, code: str) -> None:
    if not ok:
        raise ProposalError(code)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def encode(obj: object) -> bytes:
    return (json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def pin(root: Path = ROOT) -> None:
    need(root.resolve() == ROOT.resolve(), "ROOT_DRIFT")
    for path, (length, expected) in PINS.items():
        raw = (root / path).read_bytes()
        need(length is None or len(raw) == length, f"INPUT_LENGTH_DRIFT {path}")
        need(sha(raw) == expected, f"INPUT_HASH_DRIFT {path}")


def pitch_class(name: str) -> int:
    need(re.fullmatch(r"[A-G](?:#|b)?", name) is not None, "SPELLING_SHAPE")
    return (PC[name[0]] + (1 if name.endswith("#") else -1 if name.endswith("b") else 0)) % 12


def source_span(row: dict, lines: list[str], pages: list[str]) -> dict:
    ref = row["source_refs"]["txt"]
    match = re.fullmatch(r"L12-TXT1-(\d+)-(\d+)", ref)
    need(match is not None, "TXT_REF")
    first, last = map(int, match.groups())
    need(1 <= first <= last <= len(lines), "TXT_SPAN")
    section = lines[first - 1:last]
    need(section[0].startswith(f"RUNG {row['rung_number']} OF 13") and
         all(raw in section for raw in row["raw_rows"]), "TXT_RUNG_ROWS")
    pdf_ref = row["source_refs"]["pdf_card"]
    match = re.fullmatch(r"L12-PDF1-p(\d+)", pdf_ref)
    need(match is not None, "PDF_REF")
    page = int(match.group(1))
    need(3 <= page <= len(pages) and
         re.search(rf"\b{row['rung_number']}\b\s+{row['key'].upper()}\s+MAJOR", pages[page - 1]) is not None,
         "PDF_RUNG_HEADING")
    return {"txt": ref, "pdf_card": pdf_ref, "pdf_route_table": row["source_refs"]["pdf_route_table"],
            "pdf_page": page, "txt_passage_sha256": sha("\n".join(section).encode())}


def reconciliation(root: Path, candidate: dict) -> dict:
    foundation = json.loads((root / FOUNDATION_PACKAGE).read_text())
    registry = json.loads((root / FOUNDATION_REGISTRY).read_text())
    existing = [r for r in foundation["records"] if r["legacy_level"] == 12]
    need(len(existing) == 1 and existing[0]["id"] == "fg:item:000003" and
         existing[0]["workbook_id"] == "fg:workbook:000012" and
         existing[0]["content_revision"] == 3 and
         existing[0]["lineage"]["kind"] == "revision" and
         any(e["id"] == "fg:workbook:000012" for e in registry["entities"]),
         "EXISTING_LEVEL12_SCOPE")
    old = existing[0]
    first = candidate["records"][0]
    source_notes = [(OPEN[n["string"]][0], n["fret"], OPEN[n["string"]][1] + n["fret"], n["finger_digit"])
                    for n in first["notes"]]
    old_notes = [(e["string"], e["fret"], e["midi"], e["finger"]) for e in old["events"]]
    need(source_notes == old_notes and len(old_notes) == 16, "EXISTING_RUNG01_PITCH_OVERLAP")
    need({"L12-TXT34-52", "L12-TXT34-53"}.issubset(old["source_refs"]) and
         first["source_refs"]["txt"] == "L12-TXT1-42-53", "EXISTING_RUNG01_SOURCE")
    old_assets = {foundation["sources"][ref]["sha256"] for ref in old["source_refs"]}
    need(old_assets == {PINS[TXT][1]}, "EXISTING_SOURCE_ASSET")
    return {
        "status": "allocation_authority_pending_P02",
        "existing_workbook_id": "fg:workbook:000012",
        "existing_item_id": old["id"], "existing_module_id": old["module_id"],
        "existing_content_revision": 3,
        "existing_lineage_kind": old["lineage"]["kind"],
        "existing_variant_ids": [v["id"] for v in old["variants"]],
        "existing_timing_status": old["timing"]["status"],
        "source_local_key_correspondence": {"L12-rung01": old["id"]},
        "source_local_key_is_stored_in_current_record": False,
        "exact_source_ref_key_overlap": [],
        "shared_original_txt_sha256": PINS[TXT][1],
        "overlapping_txt_line_spans": [
            {"proposal": "L12-TXT1-42-53", "existing": "L12-TXT34-52", "shared_lines": [42, 52]},
            {"proposal": "L12-TXT1-42-53", "existing": "L12-TXT34-53", "shared_lines": [42, 53]},
        ],
        "physical_note_tuple_match": True,
        "remaining_source_keys": [r["source_local_key"] for r in candidate["records"][1:]],
        "decision_matrix": [
            {"choice": "retain_revision3_rung01_and_add_remaining12", "requires":
             "P02 decision on existing workbook baseline, source-key bridge, whole-route coverage and timing split; no rung01 reallocation"},
            {"choice": "reviewed_rung01_revision_then_add_remaining12", "requires":
             "separate lineage authority, predecessor digest, source/timing/variant reconciliation and P02 integration decision"},
            {"choice": "defer_level12_allocation", "requires":
             "continue only detached source-field evidence until workbook/revision semantics are approved"},
        ],
        "selected_choice": None,
        "canonical_ids_allocated": False, "admitted": False,
    }


def build(root: Path = ROOT, candidate_override: dict | None = None) -> tuple[dict, dict]:
    pin(root)
    candidate = candidate_override if candidate_override is not None else json.loads((root / CANDIDATE).read_text())
    need(candidate == p07.build_candidate(), "P07_SOURCE_CANDIDATE_DRIFT")
    need(candidate["level"] == 12 and len(candidate["records"]) == 13 and
         all(candidate[k] is False for k in ("admitted", "imported", "runtime_admitted", "runtime_eligible",
                                              "whole_workbook_complete")), "SOURCE_SCOPE")
    from pypdf import PdfReader
    lines = (root / TXT).read_text().splitlines()
    pages = [page.extract_text() for page in PdfReader(str(root / PDF)).pages]
    need(len(pages) == 6 and len(lines) == 231, "SOURCE_LENGTH")
    existing = reconciliation(root, candidate)
    records, source_map, seen = [], [], set()
    for index, row in enumerate(candidate["records"]):
        rung = index + 1
        key = f"L12-rung{rung:02d}"
        need(row["source_local_key"] == key and row["rung_number"] == f"{rung:02d}" and
             key not in seen and row["root_fret"] == rung + 4 and
             row["frame_low"] == row["root_fret"] - 1 and
             row["frame_high"] == row["root_fret"] + 2, "RUNG_ORDER_OR_FRAME")
        seen.add(key)
        need(all(row[k] is None for k in ("canonical_item_id", "canonical_variant_id", "fixed_bpm",
                                            "note_per_click", "onset_q", "duration_q")) and
             all(row[k] is False for k in ("admitted", "imported", "runtime_admitted", "runtime_eligible")),
             "SOURCE_TIMING_OR_AUTHORITY")
        src = source_span(row, lines, pages)
        refs = [src["txt"], src["pdf_card"], src["pdf_route_table"], *GUIDANCE]
        need(len(row["notes"]) == 16 and row["scale_tones"][0] == row["scale_tones"][-1] == row["key"],
             "SCALE_SOURCE")
        events = []
        for ordinal, note in enumerate(row["notes"], 1):
            string, open_midi = OPEN[note["string"]]
            midi = open_midi + note["fret"]
            degree = DEGREES[ordinal - 1]
            need(note["ordinal"] == ordinal and note["degree"] == degree and
                 note["finger_digit"] == FINGERS[ordinal - 1] and
                 note["tone"] == row["scale_tones"][degree - 1] and
                 pitch_class(note["tone"]) == midi % 12 and
                 note["onset_q"] is note["duration_q"] is None,
                 "NOTE_PITCH_DEGREE_SOURCE")
            events.append({"event_id": None, "kind": "note", "string": string,
                           "fret": note["fret"], "midi": midi, "spelling": note["tone"],
                           "degree_contexts": {f"{row['key']}-major": {
                               "source_label": str(degree), "ordinal": degree, "alteration": 0}},
                           "finger": note["finger_digit"], "onset_q": None,
                           "duration_q": None, "attack": "picked", "tie_from": None})
        variants, membership = [], []
        for pick in ("D", "U"):
            label = f"cell-{pick}-start"
            variants.append({"id": None, "label": label, "event_ids": None,
                             "source_refs": refs, "route": "one_octave_up_down_repeated_octave_root",
                             "pick_start": pick, "pick_start_origin": "learner_configuration",
                             "accent_policy": "source_unspecified", "role": "notation_practice",
                             "grouping": {"kind": "unresolved", "notes_per_beat": None,
                                          "beat_unit_q": None, "marking_factor": [1, 1],
                                          "source_label": "Even eighths and optional one-beat cell pause are not bound to a quarter-note grid"},
                             "tail_pause": None,
                             "unresolved": ["One authored beat of practice pause lacks a selected beat unit and pass binding."]})
            membership.append({"label": label, "event_local_ordinals": list(range(1, 17)),
                               "repeated_octave_root_ordinals": [8, 9]})
        practice = candidate["instructions"]["overview_text"]
        fields = {"id": None, "workbook_id": None, "module_id": None, "legacy_level": 12,
                  "title": f"Rung {rung:02d}: {row['key']} major one-fret neck ladder cell",
                  "kind": "notation", "content_revision": None, "status": "converted_candidate",
                  "runtime_eligible": False, "source_refs": refs, "authored_text_refs": refs,
                  "normalization": [{"kind": "representation_metadata", "basis": "P07 whole-Level12 candidate and original TXT/PDF",
                                     "text": "One 16-note major-scale cell repeats its octave root at the turn. The full ladder moves the complete hand frame one fret between cells; the two A rungs are distinct source positions."}],
                  "context": {"local_code": key, "route": "UP rungs01-13; DOWN rungs13-01; continuous round trip rungs01-13 then12-01",
                              "position": f"low-E root fret {row['root_fret']}; frame {row['frame_low']}-{row['frame_high']}",
                              "pick_start": "D or U selected by learner; cycle continues at cell turn and between rungs",
                              "pick_start_variants": ["D", "U"], "pick_continues_at_turn": True,
                              "source_tempo_rules_ref": "L12-TXT1-1-40",
                              "tuning_open_midi": [40, 45, 50, 55, 59, 64], "capo": 0},
                  "events": events,
                  "timing": {"status": "unresolved", "unit": "quarter",
                             "basis": "Printed TAB columns and relative practice BPM do not allocate quarter-note onsets or durations; one-beat pause lacks beat-unit binding",
                             "other_source_requirements": [practice, candidate["instructions"]["round_trip_text"],
                                                           candidate["instructions"]["after_mastery_text"]]},
                  "rubric": None, "resource_requirements": [],
                  "ambiguities": ["Absolute BPM, quarter-note onset/duration and beat mapping are unprovided.",
                                  "One-beat inter-cell pause is optional practice guidance with unbound beat unit.",
                                  "Existing accepted revision-3 rung01 requires P02 lineage and timing reconciliation before allocation."],
                  "control_scope": {"local_case": f"Level12 rung{rung:02d} {row['key']} major full 16-note cell",
                                    "extent": "complete_selected_case", "whole_workbook_complete": False,
                                    "source_event_count": 16, "basis_refs": refs,
                                    "unresolved": ["Identity/lineage and route-level admission pending."]},
                  "variants": variants, "lineage": None}
        need(set(fields) == FIELDS, "FIELD_SHAPE")
        records.append({"source_local_key": key, "rung_number": rung, "key": row["key"],
                        "root_fret": row["root_fret"], "frame": [row["frame_low"], row["frame_high"]],
                        "schema1_fields": fields, "variant_memberships": membership,
                        "identity_state": "unallocated", "schema1_importable": False,
                        "open_gaps": ["canonical identities", "existing-rung01 lineage decision",
                                      "quarter-note timing and beat unit", "runtime/curriculum admission"]})
        source_map.append({"source_local_key": key, "rung_number": rung, "key": row["key"],
                           "root_fret": row["root_fret"], **src})
    routes = candidate["routes"]
    up = [f"L12-rung{i:02d}" for i in range(1, 14)]
    down = list(reversed(up))
    round_trip = up + down[1:]
    need(routes["up"]["rungs"] == up and routes["down"]["rungs"] == down and
         routes["continuous_round_trip"]["rungs"] == round_trip and
         routes["continuous_round_trip"]["turn_after_rung"] == "L12-rung13", "ROUTE_ORDER")
    proposal = {"proposal_version": "parallel12-level012-unallocated-schema1-fields.1",
                "classification": "source_mapped_field_proposal_not_schema1_importable",
                "legacy_level": 12,
                "source_pins": {str(p): {"bytes": (root / p).stat().st_size, "sha256": h}
                                for p, (_, h) in PINS.items()},
                "counts": {"records": 13, "events": 208, "variants": 26,
                           "up_route_cells": 13, "down_route_cells": 13,
                           "continuous_round_trip_cells": 25},
                "canonical_ids_allocated": False, "runtime_eligible": False,
                "admitted": False, "fixed_bpm": None, "note_per_click": None,
                "onset_q": None, "duration_q": None,
                "existing_rung01_reconciliation": existing,
                "records": records}
    handoff = {"version": "parallel12-level012-allocation-decision-handoff.1",
               "status": "pending_P02_existing_rung01_lineage_decision",
               "proposal_sha256": sha(encode(proposal)), "source_map": source_map,
               "routes": {"up": up, "down": down, "continuous_round_trip": round_trip,
                          "turn_after_rung": "L12-rung13", "shift_frets_up": 1, "shift_frets_down": -1},
               "existing_rung01_reconciliation": existing,
               "record_count": 13, "event_count": 208, "variant_count": 26,
               "no_admission": True, "allocation_allowed": False}
    verify(proposal, handoff)
    return proposal, handoff


def verify(proposal: dict, handoff: dict) -> dict:
    need(proposal["canonical_ids_allocated"] is False and proposal["runtime_eligible"] is False and
         proposal["admitted"] is False and handoff["no_admission"] is True and
         handoff["allocation_allowed"] is False and
         all(proposal[k] is None for k in ("fixed_bpm", "note_per_click", "onset_q", "duration_q")),
         "INVALID_AUTHORITY")
    need(proposal["counts"] == {"records": 13, "events": 208, "variants": 26,
                                "up_route_cells": 13, "down_route_cells": 13,
                                "continuous_round_trip_cells": 25} and
         handoff["record_count"] == 13 and handoff["event_count"] == 208 and
         handoff["variant_count"] == 26, "COVERAGE")
    keys = [r["source_local_key"] for r in proposal["records"]]
    need(keys == [f"L12-rung{i:02d}" for i in range(1, 14)] and
         [r["source_local_key"] for r in handoff["source_map"]] == keys and
         handoff["routes"]["up"] == keys and
         handoff["routes"]["down"] == list(reversed(keys)) and
         handoff["routes"]["continuous_round_trip"] == keys + list(reversed(keys))[1:],
         "ROUTE_OR_CASE_ORDER")
    for row in proposal["records"]:
        fields = row["schema1_fields"]
        need(set(fields) == FIELDS and row["schema1_importable"] is False and
             row["identity_state"] == "unallocated", "FIELD_SHAPE")
        need(all(fields[k] is None for k in ("id", "workbook_id", "module_id", "lineage", "content_revision")) and
             fields["runtime_eligible"] is False and fields["timing"]["status"] == "unresolved", "INVALID_AUTHORITY")
        need(len(fields["events"]) == 16 and len(fields["variants"]) == 2 and
             len(row["variant_memberships"]) == 2 and
             [e["midi"] for e in fields["events"]][7] == [e["midi"] for e in fields["events"]][8],
             "CELL_COUNT_OR_OCTAVE_TURN")
        need(all(e["event_id"] is e["onset_q"] is e["duration_q"] is None for e in fields["events"]),
             "UNSUPPORTED_TIMING_OR_ID")
        need(all(v["id"] is v["event_ids"] is None and v["grouping"]["kind"] == "unresolved"
                 for v in fields["variants"]), "UNSUPPORTED_TIMING_OR_ID")
        need([m["label"] for m in row["variant_memberships"]] ==
             [v["label"] for v in fields["variants"]] and
             all(m["event_local_ordinals"] == list(range(1, 17)) and
                 m["repeated_octave_root_ordinals"] == [8, 9] for m in row["variant_memberships"]),
             "VARIANT_MEMBERSHIP")
    reconciliation = proposal["existing_rung01_reconciliation"]
    need(reconciliation == handoff["existing_rung01_reconciliation"] and
         reconciliation["selected_choice"] is None and
         reconciliation["existing_item_id"] == "fg:item:000003" and
         reconciliation["existing_content_revision"] == 3 and
         len(reconciliation["remaining_source_keys"]) == 12 and
         reconciliation["physical_note_tuple_match"] is True, "EXISTING_RUNG01_RECONCILIATION")
    need(handoff["proposal_sha256"] == sha(encode(proposal)), "PROPOSAL_HASH")
    return proposal["counts"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("build", "verify"))
    args = parser.parse_args()
    proposal, handoff = build()
    if args.command == "build":
        (ROOT / OUT).mkdir(parents=True, exist_ok=True)
        (ROOT / OUT / "field-proposal.json").write_bytes(encode(proposal))
        (ROOT / OUT / "allocation-handoff.json").write_bytes(encode(handoff))
    else:
        need((ROOT / OUT / "field-proposal.json").read_bytes() == encode(proposal), "OUTPUT_DRIFT proposal")
        need((ROOT / OUT / "allocation-handoff.json").read_bytes() == encode(handoff), "OUTPUT_DRIFT handoff")
    print(json.dumps({"status": "unallocated_level012_pending_rung01_reconciliation",
                      "counts": verify(proposal, handoff)}, sort_keys=True))


if __name__ == "__main__":
    main()
