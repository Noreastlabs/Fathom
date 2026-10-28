#!/usr/bin/env python3
"""Preserve whole Level23 originals and project only source-proven unallocated fields."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader

import curriculum_level023_whole_candidate as p08

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = p08.BUILD_REL / "candidate-02.json"
RESULT = Path("Results/parallel-08/exercises/conversion/20260923T150205Z-2.3.1.1.1-level023-whole-candidate-r01-results.md")
PACKAGE = Path("Content/controls/curriculum-v1/package.json")
REGISTRY = Path("Content/controls/curriculum-v1/identity-registry.json")
OUT = Path("Build/parallel-12/level023-source-preservation-schema1-r01")
PINS = {
    CANDIDATE: (279793, "4ac1bacef35c57994038c5957c891c9bc491c38566d62c506dc955ef96c273dc"),
    RESULT: (None, "d49801965fb3d9233920723cb86f59ca1c025f15474c8400157a2f83e3559880"),
    p08.TXT_REL: (p08.TXT_BYTES, p08.TXT_SHA256),
    p08.PDF_REL: (p08.PDF_BYTES, p08.PDF_SHA256),
    PACKAGE: (None, "766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255"),
    REGISTRY: (None, "5d265859e1e8a5a530a0e53d88b019a1c920f3bba6cccb4ef0fef2f7640007e5"),
}
FIELDS = {"id", "workbook_id", "module_id", "legacy_level", "title", "kind", "content_revision",
          "status", "runtime_eligible", "source_refs", "authored_text_refs", "normalization", "context",
          "events", "timing", "rubric", "resource_requirements", "ambiguities", "control_scope",
          "variants", "lineage"}
OPEN = {"E": (1, 40), "A": (2, 45), "D": (3, 50), "G": (4, 55), "B": (5, 59), "e": (6, 64)}
NATURAL = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


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


def pitch_class(spelling: str) -> int:
    need(re.fullmatch(r"[A-G](?:#|b)?", spelling) is not None, "SPELLING_SHAPE")
    return (NATURAL[spelling[0]] + (1 if spelling.endswith("#") else -1 if spelling.endswith("b") else 0)) % 12


def txt_span(ref: str, lines: list[str]) -> dict:
    match = re.fullmatch(r"L23-TXT1-(\d+)-(\d+)", ref)
    need(match is not None, "TXT_REF")
    first, last = map(int, match.groups())
    need(1 <= first <= last <= len(lines), "TXT_SPAN")
    return {"ref": ref, "first_line": first, "last_line": last,
            "text_sha256": sha("\n".join(lines[first - 1:last]).encode())}


def source_event(note: dict, key: str, tones: list[str]) -> dict:
    need(note["onset_q"] is note["duration_q"] is None and note["string"] in OPEN and
         1 <= note["degree_position"] <= 8 and note["degree_label"] == p08.DEGREES[note["degree_position"] - 1] and
         note["finger_digit"] in ("1", "3", "4"), "SOURCE_NOTE_SCOPE")
    string, open_midi = OPEN[note["string"]]
    midi = open_midi + note["fret"]
    spelling = tones[note["degree_position"] - 1]
    need(midi % 12 == pitch_class(spelling), "NOTE_PITCH_SPELLING")
    degree = note["degree_label"]
    return {"event_id": None, "kind": "note", "string": string, "fret": note["fret"],
            "midi": midi, "spelling": spelling,
            "degree_contexts": {f"{key}-natural-minor": {"source_label": degree,
                                                          "ordinal": note["degree_position"],
                                                          "alteration": -1 if degree.startswith("b") else 0}},
            "finger": int(note["finger_digit"]), "onset_q": None, "duration_q": None,
            "attack": "picked", "tie_from": None}


def preserve_sources(root: Path, candidate: dict, txt_raw: bytes, pdf_raw: bytes) -> dict:
    txt_text = txt_raw.decode("utf-8")
    lines = txt_text.splitlines()
    need(len(lines) == 275 and not txt_raw.endswith(b"\n"), "TXT_COMPLETE_BOUNDARY")
    reader = PdfReader(BytesIO(pdf_raw), strict=True)
    need(len(reader.pages) == 7, "PDF_COMPLETE_BOUNDARY")
    pages = []
    for number, page in enumerate(reader.pages, 1):
        extracted = page.extract_text() or ""
        page_lines = extracted.splitlines()
        need(page_lines and any(f"Page {number} of 7" in line for line in page_lines),
             f"PDF_PAGE_IDENTITY {number}")
        pages.append({"page": number, "text": extracted, "text_sha256": sha(extracted.encode()),
                      "line_count": len(page_lines), "media_box": [float(value) for value in page.mediabox]})
    source_map = []
    for index, record in enumerate(candidate["records"], 1):
        txt_ref = record["source_refs"]["txt"]
        span = txt_span(txt_ref, lines)
        need(span["first_line"] == 62 + (index - 1) * 14 and span["last_line"] == span["first_line"] + 11,
             "TXT_CARD_BOUNDARY")
        source_map.append({"source_local_key": record["source_local_key"],
                           "rung_number": index, "txt": span,
                           "pdf_card": record["source_refs"]["pdf_card"],
                           "pdf_route_map": record["source_refs"]["pdf_map"]})
    final = candidate["records"][-1]
    need(final["printed_txt"]["footer"] == p08.TXT_RUNG_FOOTER and
         final["printed_pdf"]["footer"] == p08.PDF_FINAL_CARD_FOOTER and
         final["printed_txt"]["footer"] != final["printed_pdf"]["footer"],
         "FINAL_FOOTER_DISTINCTION")
    preservation = {
        "version": "parallel12-level023-whole-original-preservation.1",
        "classification": "pinned_original_text_and_page_preservation_not_admission",
        "source": {"txt_path": str(p08.TXT_REL), "txt_bytes": len(txt_raw), "txt_sha256": sha(txt_raw),
                   "txt_text": txt_text, "txt_line_count": len(lines), "txt_trailing_newline": False,
                   "pdf_path": str(p08.PDF_REL), "pdf_bytes": len(pdf_raw), "pdf_sha256": sha(pdf_raw),
                   "pdf_page_count": len(pages), "pdf_pages": pages},
        "source_map": source_map,
        "source_guidance": candidate["instructions"],
        "pdf_context": candidate["pdf_context"],
        "source_route": candidate["neck_route"],
        "source_exceptions": candidate["exceptions"],
        "source_distinctions": [{"kind": "final_card_footer_wording",
                                 "source_local_key": final["source_local_key"],
                                 "txt": final["printed_txt"]["footer"],
                                 "pdf": final["printed_pdf"]["footer"],
                                 "interpretation": "single turn after rung13 follows explicit round-trip route"}],
        "card_parity": {"txt_pdf_rungs": 13, "printed_rows_equal": True,
                        "note_groups_equal": True, "page_1_worked_example_equal_first_card": True,
                        "continuous_route_cells": 25, "source_candidate_sha256": PINS[CANDIDATE][1]},
        "visual_review_pages": [1, 2, 3, 7],
        "schema1_projection_allowed_after_parity": True,
        "canonical_allocation_allowed": False,
    }
    verify_preservation(preservation, txt_raw, pdf_raw)
    return preservation


def verify_preservation(preservation: dict, txt_raw: bytes, pdf_raw: bytes) -> None:
    source_data = preservation["source"]
    need(source_data["txt_text"].encode() == txt_raw and
         source_data["txt_sha256"] == sha(txt_raw) and
         source_data["txt_line_count"] == 275 and
         source_data["txt_trailing_newline"] is False and
         source_data["pdf_sha256"] == sha(pdf_raw) and
         source_data["pdf_bytes"] == len(pdf_raw) and
         source_data["pdf_page_count"] == len(source_data["pdf_pages"]) == 7,
         "SOURCE_PRESERVATION_DRIFT")
    reader = PdfReader(BytesIO(pdf_raw), strict=True)
    for index, preserved_page in enumerate(source_data["pdf_pages"], 1):
        extracted = reader.pages[index - 1].extract_text() or ""
        need(preserved_page["page"] == index and preserved_page["text"] == extracted and
             preserved_page["text_sha256"] == sha(extracted.encode()) and
             preserved_page["line_count"] == len(extracted.splitlines()), "PDF_PAGE_TEXT_DRIFT")
    need(preservation["card_parity"] == {"txt_pdf_rungs": 13, "printed_rows_equal": True,
                                        "note_groups_equal": True, "page_1_worked_example_equal_first_card": True,
                                        "continuous_route_cells": 25,
                                        "source_candidate_sha256": PINS[CANDIDATE][1]} and
         preservation["schema1_projection_allowed_after_parity"] is True and
         preservation["canonical_allocation_allowed"] is False,
         "PARITY_GATE")


def build(root: Path = ROOT, candidate_override: dict | None = None) -> tuple[dict, dict, dict]:
    pin(root)
    txt_raw, pdf_raw = (root / p08.TXT_REL).read_bytes(), (root / p08.PDF_REL).read_bytes()
    candidate = candidate_override if candidate_override is not None else json.loads((root / CANDIDATE).read_text())
    rebuilt = json.loads(json.dumps(p08.build_candidate()))
    need(candidate == rebuilt, "P08_SOURCE_CANDIDATE_DRIFT")
    need(candidate["level"] == 23 and len(candidate["records"]) == 13 and
         candidate["whole_workbook_source_covered"] is True and candidate["whole_workbook_complete"] is False and
         all(candidate[k] is False for k in ("runtime_eligible", "runtime_admitted", "imported", "admitted")),
         "SOURCE_SCOPE")
    preservation = preserve_sources(root, candidate, txt_raw, pdf_raw)
    foundation = json.loads((root / PACKAGE).read_text())
    registry = json.loads((root / REGISTRY).read_text())
    current = [r for r in foundation["records"] if r.get("legacy_level") == 23]
    identities = [e for e in registry["entities"] if e.get("id") == "fg:workbook:000023" or
                  e.get("parent") == "fg:workbook:000023"]
    need(len(foundation["records"]) == 659 and not current and not identities, "CURRENT659_LEVEL23_OVERLAP")
    records = []
    for index, card in enumerate(candidate["records"], 1):
        local, key, root_fret = f"L23-rung{index:02d}", p08.KEYS[index - 1], index + 4
        need(card["source_local_key"] == local and card["rung"] == index and card["key"] == key and
             card["root_string"] == "E" and card["root_fret"] == root_fret and
             card["frame"] == [root_fret, root_fret + 3] and
             card["scale_tones"] == [*p08.SCALE_TONES[index - 1], key] and
             card["group_count"] == len(card["groups"]) == 12 and card["note_count"] == 36 and
             all(card[k] is None for k in ("canonical_item_id", "canonical_variant_id", "onset_q",
                                            "duration_q", "note_per_click", "fixed_bpm")) and
             all(card[k] is False for k in ("runtime_eligible", "runtime_admitted", "imported", "admitted")),
             "CARD_SCOPE")
        for printed_key in ("deg_row", "fng_row", "tab_rows"):
            need(card["printed_txt"][printed_key] == card["printed_pdf"][printed_key], "PRINTED_ROW_PARITY")
        refs = [card["source_refs"]["txt"], card["source_refs"]["pdf_card"],
                card["source_refs"]["pdf_map"],
                *[g["ref"] for g in candidate["instructions"].values() if isinstance(g, dict) and "ref" in g]]
        events, groups = [], []
        for group_index, group in enumerate(card["groups"], 1):
            need(group["index"] == group_index and group["half"] == ("up" if group_index <= 6 else "down") and
                 group["string_pattern"] == p08.CROSSINGS[group_index - 1] and len(group["notes"]) == 3,
                 "GROUP_SCOPE")
            ordinals = []
            for slot, note in enumerate(group["notes"], 1):
                ordinal = (group_index - 1) * 3 + slot
                need(note["ordinal"] == ordinal and note["group"] == group_index and note["slot"] == slot and
                     note["half"] == group["half"] and note["degree_position"] ==
                     p08.DEGREE_GROUPS[group_index - 1][slot - 1] and
                     note["is_octave_turn_root"] == (ordinal in (18, 19)), "NOTE_ORDER")
                events.append(source_event(note, key, card["scale_tones"]))
                ordinals.append(ordinal)
            groups.append({"whole_cell_group": group_index, "source_group": (group_index - 1) % 6 + 1,
                           "direction": "ascending" if group_index <= 6 else "descending",
                           "event_local_ordinals": ordinals,
                           "source_scale_positions": [n["degree_position"] for n in group["notes"]],
                           "source_degree_labels": [n["degree_label"] for n in group["notes"]],
                           "source_string_pattern": group["string_pattern"],
                           "source_beat_relation": "one_three_note_group_per_beat", "beat_unit_q": None})
        need(len(events) == 36 and
             (events[17]["string"], events[17]["fret"], events[17]["midi"]) ==
             (events[18]["string"], events[18]["fret"], events[18]["midi"]), "OCTAVE_TURN")
        variants, memberships = [], []
        for pick in ("D", "U"):
            label = f"minor-rolling-three-{pick}-start"
            variants.append({"id": None, "label": label, "event_ids": None,
                             "source_refs": refs, "route": "one_octave_12_rolling_triplets_high_root_repeated",
                             "pick_start": pick, "pick_start_origin": "source_authored",
                             "role": "notation_practice", "accent_policy": "source_unspecified",
                             "grouping": {"kind": "unresolved", "notes_per_beat": 3,
                                          "beat_unit_q": None, "marking_factor": [1, 1],
                                          "source_label": "eighth-note triplets; one three-note group per beat"},
                             "tail_pause": None,
                             "unresolved": ["Absolute BPM, quarter-note grid and optional inter-cell pause unassigned."]})
            memberships.append({"label": label, "event_local_ordinals": list(range(1, 37)),
                                "group_indices": list(range(1, 13)),
                                "repeated_octave_root_ordinals": [18, 19]})
        footer_distinction = index == 13
        fields = {"id": None, "workbook_id": None, "module_id": None, "legacy_level": 23,
                  "title": f"Rung {index:02d}: {key} natural minor one-octave rolling triplets",
                  "kind": "notation", "content_revision": None, "status": "converted_candidate",
                  "runtime_eligible": False, "source_refs": refs, "authored_text_refs": refs,
                  "normalization": [{"kind": "representation_metadata", "basis": "P08 whole-Level23 candidate and complete original TXT/PDF",
                                     "text": "Twelve printed three-note groups form a 36-contact sequential cell and repeat the octave root at contacts 18/19; shift only after the full cell."}],
                  "context": {"local_code": local,
                              "route": "UP rungs01-13; printed DOWN landmarks13-01; continuous return12-01",
                              "position": f"low-E root fret {root_fret}; frame {root_fret}-{root_fret + 3}",
                              "pick_start": "D or U; alternate continuously through groups, string crossings, turn and relocation",
                              "pick_start_variants": ["D", "U"], "pick_continues_at_turn": True,
                              "tuning_open_midi": [40, 45, 50, 55, 59, 64], "capo": 0,
                              "source_group_count": 12, "source_notes_per_group": 3,
                              "shift_after_complete_cell_only": True},
                  "events": events,
                  "timing": {"status": "unresolved", "unit": "quarter",
                             "basis": "Source triplet grouping and relative BPM guidance do not allocate an absolute quarter-note event grid or pause binding",
                             "source_pulse": "one three-note triplet group per beat", "selected_pulse": None},
                  "rubric": None, "resource_requirements": [],
                  "ambiguities": ["Quarter-note onsets/durations, note-per-click and absolute BPM are unassigned.",
                                  "Optional one-beat inter-cell pause has no selected beat-unit/pass binding."] +
                                 (["Final TXT footer says move one fret; final PDF footer says reverse to rung12. Both source wordings are preserved."]
                                  if footer_distinction else []),
                  "control_scope": {"local_case": f"Level23 rung{index:02d} {key} natural-minor full 36-contact rolling cell",
                                    "extent": "complete_selected_case", "whole_workbook_complete": False,
                                    "source_event_count": 36, "basis_refs": refs,
                                    "unresolved": ["Identity, lineage and route-level admission pending."]},
                  "variants": variants, "lineage": None}
        need(set(fields) == FIELDS, "FIELD_SHAPE")
        records.append({"source_local_key": local, "rung_number": index, "key": key,
                        "root_fret": root_fret, "frame": [root_fret, root_fret + 3],
                        "schema1_fields": fields, "group_memberships": groups,
                        "variant_memberships": memberships,
                        "source_printed_txt": card["printed_txt"],
                        "source_printed_pdf": card["printed_pdf"],
                        "source_group_details": card["groups"],
                        "identity_state": "unallocated", "schema1_importable": False,
                        "open_gaps": ["canonical identities and lineage", "quarter-note timing and pause binding",
                                      "runtime/Curriculum admission"]})
    route = candidate["neck_route"]
    up = [f"L23-rung{i:02d}" for i in range(1, 14)]
    down_landmarks = list(reversed(up))
    down_return = down_landmarks[1:]
    need(route["single_turn_cell_sequence"] == list(range(1, 14)) + list(range(12, 0, -1)) and
         route["single_turn_cell_count"] == 25 and route["single_turn_note_count"] == 900,
         "ROUTE_SOURCE")
    counts = {"records": 13, "groups": 156, "events": 468, "variants": 26,
              "up_landmark_cells": 13, "down_landmark_cells": 13,
              "continuous_round_trip_cells": 25, "round_trip_contact_traversals": 900,
              "preserved_txt_lines": 275, "preserved_pdf_pages": 7}
    proposal = {"proposal_version": "parallel12-level023-unallocated-schema1-fields.1",
                "classification": "source_mapped_field_proposal_not_schema1_importable",
                "legacy_level": 23,
                "source_pins": {str(path): {"bytes": (root / path).stat().st_size, "sha256": digest}
                                for path, (_, digest) in PINS.items()},
                "source_preservation_sha256": sha(encode(preservation)),
                "counts": counts, "source_exceptions": candidate["exceptions"],
                "source_distinctions": preservation["source_distinctions"],
                "current659_level23_records": 0, "current659_level23_workbook_identity": False,
                "representative_collision": None,
                "canonical_ids_allocated": False, "runtime_eligible": False, "admitted": False,
                "fixed_bpm": None, "note_per_click": None, "onset_q": None, "duration_q": None,
                "records": records}
    handoff = {"version": "parallel12-level023-allocation-handoff.1",
               "status": "pending_P02_serial_floor_and_allocation_authority",
               "source_preservation_sha256": sha(encode(preservation)),
               "proposal_sha256": sha(encode(proposal)),
               "source_map": preservation["source_map"],
               "routes": {"up_landmarks": up, "down_landmarks": down_landmarks,
                          "down_return": down_return, "continuous_round_trip": up + down_return,
                          "turn_after_rung": "L23-rung13", "shift_frets_up": 1, "shift_frets_down": -1},
               "record_count": 13, "group_count": 156, "event_count": 468, "variant_count": 26,
               "current659_level23_records": 0, "current659_level23_workbook_identity": False,
               "representative_collision": None,
               "decisions_required": ["P02 serial floor, workbook/module/item/variant identity and source-key bridge",
                                      "Curriculum review of rolling groups, octave repeat and final-card footer distinction",
                                      "Reviewed timing/pause binding and lineage/admission policy before import"],
               "selected_choice": None, "allocation_allowed": False, "no_admission": True}
    verify_projection(preservation, proposal, handoff)
    return preservation, proposal, handoff


def verify_projection(preservation: dict, proposal: dict, handoff: dict) -> dict:
    need(preservation["schema1_projection_allowed_after_parity"] is True and
         proposal["source_preservation_sha256"] == handoff["source_preservation_sha256"] == sha(encode(preservation)),
         "PARITY_GATE")
    need(proposal["canonical_ids_allocated"] is False and proposal["runtime_eligible"] is False and
         proposal["admitted"] is False and handoff["allocation_allowed"] is False and
         handoff["no_admission"] is True and handoff["selected_choice"] is None and
         all(proposal[k] is None for k in ("fixed_bpm", "note_per_click", "onset_q", "duration_q")),
         "INVALID_AUTHORITY")
    counts = {"records": 13, "groups": 156, "events": 468, "variants": 26,
              "up_landmark_cells": 13, "down_landmark_cells": 13,
              "continuous_round_trip_cells": 25, "round_trip_contact_traversals": 900,
              "preserved_txt_lines": 275, "preserved_pdf_pages": 7}
    need(proposal["counts"] == counts and
         (handoff["record_count"], handoff["group_count"], handoff["event_count"],
          handoff["variant_count"]) == (13, 156, 468, 26), "COVERAGE")
    keys = [f"L23-rung{i:02d}" for i in range(1, 14)]
    need([r["source_local_key"] for r in proposal["records"]] == keys and
         [r["source_local_key"] for r in handoff["source_map"]] == keys and
         handoff["routes"]["up_landmarks"] == keys and
         handoff["routes"]["down_landmarks"] == list(reversed(keys)) and
         handoff["routes"]["down_return"] == list(reversed(keys))[1:] and
         handoff["routes"]["continuous_round_trip"] == keys + list(reversed(keys))[1:] and
         handoff["routes"]["turn_after_rung"] == "L23-rung13", "ROUTE_OR_CASE_ORDER")
    for index, record in enumerate(proposal["records"], 1):
        fields = record["schema1_fields"]
        need(record["rung_number"] == index and record["key"] == p08.KEYS[index - 1] and
             record["root_fret"] == index + 4 and record["frame"] == [index + 4, index + 7] and
             record["identity_state"] == "unallocated" and record["schema1_importable"] is False and
             set(fields) == FIELDS and fields["legacy_level"] == 23 and
             fields["context"]["local_code"] == record["source_local_key"] and
             all(fields[k] is None for k in ("id", "workbook_id", "module_id", "content_revision", "lineage")) and
             fields["runtime_eligible"] is False and fields["timing"]["status"] == "unresolved" and
             fields["timing"]["selected_pulse"] is None, "INVALID_AUTHORITY")
        need(len(fields["events"]) == 36 and len(record["group_memberships"]) == 12 and
             len(fields["variants"]) == len(record["variant_memberships"]) == 2, "CELL_COUNT")
        for ordinal, event in enumerate(fields["events"], 1):
            note = record["source_group_details"][(ordinal - 1) // 3]["notes"][(ordinal - 1) % 3]
            degree = note["degree_label"]
            need(event["event_id"] is event["onset_q"] is event["duration_q"] is None and
                 event["kind"] == "note" and
                 (event["string"], event["fret"], event["midi"], event["finger"]) ==
                 (OPEN[note["string"]][0], note["fret"], OPEN[note["string"]][1] + note["fret"],
                  int(note["finger_digit"])) and
                 event["degree_contexts"] == {f"{record['key']}-natural-minor": {
                     "source_label": degree, "ordinal": note["degree_position"],
                     "alteration": -1 if degree.startswith("b") else 0}},
                 "UNSUPPORTED_TIMING_OR_NOTE")
        need((fields["events"][17]["string"], fields["events"][17]["fret"], fields["events"][17]["midi"]) ==
             (fields["events"][18]["string"], fields["events"][18]["fret"], fields["events"][18]["midi"]),
             "TURN_ROOT")
        for group_index, group in enumerate(record["group_memberships"], 1):
            need(group["whole_cell_group"] == group_index and group["event_local_ordinals"] ==
                 list(range((group_index - 1) * 3 + 1, group_index * 3 + 1)) and
                 group["source_string_pattern"] == p08.CROSSINGS[group_index - 1] and
                 group["beat_unit_q"] is None, "GROUP_MEMBERSHIP")
        need([v["pick_start"] for v in fields["variants"]] == ["D", "U"] and
             all(v["id"] is v["event_ids"] is None and v["grouping"]["kind"] == "unresolved" and
                 v["grouping"]["beat_unit_q"] is None for v in fields["variants"]) and
             all(m["event_local_ordinals"] == list(range(1, 37)) and
                 m["group_indices"] == list(range(1, 13)) and
                 m["repeated_octave_root_ordinals"] == [18, 19]
                 for m in record["variant_memberships"]), "VARIANT_MEMBERSHIP")
    need(handoff["proposal_sha256"] == sha(encode(proposal)) and
         proposal["current659_level23_records"] == handoff["current659_level23_records"] == 0 and
         proposal["current659_level23_workbook_identity"] is handoff["current659_level23_workbook_identity"] is False and
         proposal["representative_collision"] is handoff["representative_collision"] is None,
         "PROPOSAL_HASH_OR_CURRENT659")
    return counts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("build", "verify"))
    args = parser.parse_args()
    preservation, proposal, handoff = build()
    outputs = {"source-preservation.json": preservation,
               "field-proposal.json": proposal,
               "allocation-handoff.json": handoff}
    if args.command == "build":
        (ROOT / OUT).mkdir(parents=True, exist_ok=True)
        for name, value in outputs.items():
            (ROOT / OUT / name).write_bytes(encode(value))
    else:
        for name, value in outputs.items():
            need((ROOT / OUT / name).read_bytes() == encode(value), f"OUTPUT_DRIFT {name}")
    print(json.dumps({"status": "level023_source_preserved_unallocated_pending_P02",
                      "counts": verify_projection(preservation, proposal, handoff)}, sort_keys=True))


if __name__ == "__main__":
    main()
