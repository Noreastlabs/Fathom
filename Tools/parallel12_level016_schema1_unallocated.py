#!/usr/bin/env python3
"""Build source-linked, unallocated schema1 fields for the whole Level16 ladder."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from pypdf import PdfReader

import curriculum_level016_whole_candidate as p11

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = Path("Build/parallel-11/2.3.1.1.1-level016-whole-r01/candidate-final-b.json")
RESULT = Path("Results/parallel-11/curriculum/20260923T145300Z-2.3-level016-whole-r01-results.md")
PACKAGE = Path("Content/controls/curriculum-v1/package.json")
REGISTRY = Path("Content/controls/curriculum-v1/identity-registry.json")
OUT = Path("Build/parallel-12/level016-schema1-unallocated-r01")
PINS = {
    CANDIDATE: (359420, "2fe5f23a73a13b742192588b0d2d6a6336c42ed4e1722403393de79f2bd5289a"),
    RESULT: (None, "076ad845724abd36e152c23bf1bbb066532f1fc179153fd9e13f6e43438a841b"),
    Path(p11.TXT[0]): (p11.TXT[2], p11.TXT[1]),
    Path(p11.PDF[0]): (p11.PDF[2], p11.PDF[1]),
    PACKAGE: (None, "766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255"),
    REGISTRY: (None, "5d265859e1e8a5a530a0e53d88b019a1c920f3bba6cccb4ef0fef2f7640007e5"),
}
FIELDS = {"id", "workbook_id", "module_id", "legacy_level", "title", "kind", "content_revision",
          "status", "runtime_eligible", "source_refs", "authored_text_refs", "normalization", "context",
          "events", "timing", "rubric", "resource_requirements", "ambiguities", "control_scope",
          "variants", "lineage"}
OPEN_MIDI = {"E": (1, 40), "A": (2, 45), "D": (3, 50),
             "G": (4, 55), "B": (5, 59), "e": (6, 64)}
GUIDANCE_REFS = ["L16-TXT1-1-60", "L16-TXT1-243-265", "L16-PDF1-p1",
                 "L16-PDF1-p2-l74-105", "L16-PDF1-p7-l17-38"]


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
    for path, (length, digest) in PINS.items():
        raw = (root / path).read_bytes()
        need(length is None or len(raw) == length, f"INPUT_LENGTH_DRIFT {path}")
        need(sha(raw) == digest, f"INPUT_HASH_DRIFT {path}")


def txt_span(ref: str, lines: list[str]) -> dict:
    match = re.fullmatch(r"L16-TXT1-(\d+)-(\d+)", ref)
    need(match is not None, "TXT_REF")
    first, last = map(int, match.groups())
    need(1 <= first <= last <= len(lines), "TXT_SPAN")
    return {"ref": ref, "first_line": first, "last_line": last,
            "text_sha256": sha("\n".join(lines[first - 1:last]).encode())}


def pdf_span(ref: str, pages: list[list[str]]) -> dict:
    match = re.fullmatch(r"L16-PDF1-p(\d+)-l(\d+)-(\d+)", ref)
    need(match is not None, "PDF_REF")
    page, first, last = map(int, match.groups())
    need(1 <= page <= len(pages) and 1 <= first <= last <= len(pages[page - 1]), "PDF_SPAN")
    return {"ref": ref, "page": page, "first_line": first, "last_line": last,
            "text_sha256": sha("\n".join(pages[page - 1][first - 1:last]).encode())}


def build(root: Path = ROOT, candidate_override: dict | None = None) -> tuple[dict, dict]:
    pin(root)
    candidate = candidate_override if candidate_override is not None else json.loads((root / CANDIDATE).read_text())
    need(candidate == p11.build(root), "P11_SOURCE_CANDIDATE_DRIFT")
    need(candidate["level"] == 16 and len(candidate["records"]) == 13 and
         candidate["counts"] == {"rungs": 13, "groups_per_rung": 10, "notes_per_rung": 40,
                                 "groups_in_source_cards": 130, "notes_in_source_cards": 520,
                                 "round_trip_cells": 25, "round_trip_note_occurrences": 1000} and
         all(candidate[k] is False for k in ("canonical_schema_validated", "runtime_eligible",
                                              "imported", "admitted", "whole_workbook_complete")), "SOURCE_SCOPE")
    foundation = json.loads((root / PACKAGE).read_text())
    registry = json.loads((root / REGISTRY).read_text())
    need(len(foundation["records"]) == 659 and
         not any(r["legacy_level"] == 16 for r in foundation["records"]) and
         not any(e["id"] == "fg:workbook:000016" or e.get("parent") == "fg:workbook:000016"
                 for e in registry["entities"]), "CURRENT659_LEVEL16_OVERLAP")
    lines = (root / p11.TXT[0]).read_text().splitlines()
    pages = [page.extract_text().splitlines() for page in PdfReader(str(root / p11.PDF[0])).pages]
    need(len(lines) == 265 and len(pages) == 7, "SOURCE_LENGTH")
    records, source_map = [], []
    for index, row in enumerate(candidate["records"], 1):
        key, root_fret = f"L16-rung{index:02d}", index + 4
        need(row["source_local_key"] == key and row["rung"] == index and
             row["key"] == p11.KEYS[index - 1] and row["root_string"] == "E" and
             row["root_fret"] == root_fret and row["frame_frets"] == [root_fret - 1, root_fret + 2] and
             row["group_count"] == len(row["groups"]) == 10 and row["note_count"] == 40 and
             row["shift_after_complete_cell_only"] is True and row["within_cell_shift"] is False and
             all(row[k] is None for k in ("canonical_item_id", "canonical_variant_id", "onset_q",
                                           "duration_q", "note_per_click", "fixed_bpm")) and
             all(row[k] is False for k in ("admitted", "imported", "runtime_eligible")),
             "RUNG_SCOPE")
        txt = txt_span(row["source_refs"]["txt"], lines)
        pdf_card = pdf_span(row["source_refs"]["pdf_card"], pages)
        pdf_map = pdf_span(row["source_refs"]["pdf_route_map"], pages)
        need(txt["first_line"] == 62 + 14 * (index - 1) and
             txt["last_line"] == txt["first_line"] + 11 and
             lines[txt["first_line"] - 1:txt["last_line"]] == row["raw_txt_card"] and
             pages[pdf_card["page"] - 1][pdf_card["first_line"] - 1:pdf_card["last_line"]] == row["raw_pdf_card"] and
             pages[pdf_map["page"] - 1][pdf_map["first_line"] - 1:pdf_map["last_line"]] ==
             row["raw_pdf_route_map_row"], "CARD_SOURCE_SPAN")
        refs = [txt["ref"], pdf_card["ref"], pdf_map["ref"], *GUIDANCE_REFS]
        events, groups = [], []
        need(row["scale_tones_degrees_1_to_8"] == p11.TONES[index - 1].split(), "SCALE_TONES")
        for group_index, group in enumerate(row["groups"], 1):
            degrees = p11.GROUPS[group_index - 1]
            direction = "up" if group_index <= 5 else "down"
            need(group["group_number"] == group_index and group["direction"] == direction and
                 group["degrees"] == list(degrees) and len(group["notes"]) == 4,
                 "GROUP_SOURCE")
            ordinals = []
            for slot, note in enumerate(group["notes"], 1):
                ordinal = (group_index - 1) * 4 + slot
                degree = degrees[slot - 1]
                string = p11.SCALE_STRING[degree - 1]
                fret = root_fret + (-1 if degree in (3, 6) else 1 if degree == 7 else
                                    2 if degree in (2, 5, 8) else 0)
                tone = row["scale_tones_degrees_1_to_8"][degree - 1]
                need(note["ordinal_in_cell"] == ordinal and note["degree"] == degree and
                     note["tone"] == tone and note["finger_digit"] == p11.FINGERS[degree - 1] and
                     note["string"] == string and note["fret"] == fret and
                     note["printed_column"] == (slot - 1) * 3 and
                     note["pick_for_down_start"] == ("D" if ordinal % 2 else "U") and
                     note["pick_for_up_start"] == ("U" if ordinal % 2 else "D") and
                     note["onset_q"] is note["duration_q"] is None, "NOTE_SOURCE")
                string_num, open_midi = OPEN_MIDI[string]
                midi = open_midi + fret
                need(p11.note_pc(tone) == midi % 12, "NOTE_PITCH_SPELLING")
                events.append({"event_id": None, "kind": "note", "string": string_num,
                               "fret": fret, "midi": midi, "spelling": tone,
                               "degree_contexts": {f"{row['key']}-major": {
                                   "source_label": str(degree), "ordinal": degree, "alteration": 0}},
                               "finger": note["finger_digit"], "onset_q": None,
                               "duration_q": None, "attack": "picked", "tie_from": None})
                ordinals.append(ordinal)
            groups.append({"source_group": group_index, "direction": direction,
                           "event_local_ordinals": ordinals, "source_degrees": list(degrees),
                           "printed_deg_cell": group["printed_deg_cell"],
                           "printed_fng_cell": group["printed_fng_cell"],
                           "printed_tab_cells_high_to_low": group["printed_tab_cells_high_to_low"],
                           "source_beat_relation": "one_four_note_group_per_beat", "beat_unit_q": None})
        need(len(events) == 40 and
             (events[19]["string"], events[19]["fret"], events[19]["midi"]) ==
             (events[20]["string"], events[20]["fret"], events[20]["midi"]), "CELL_TURN")
        variants, membership = [], []
        for pick in ("D", "U"):
            label = f"rolling-four-{pick}-start"
            variants.append({"id": None, "label": label, "event_ids": None, "source_refs": refs,
                             "route": "one_octave_10_four_note_groups_repeated_octave_root",
                             "pick_start": pick, "pick_start_origin": "source_authored",
                             "role": "notation_practice", "accent_policy": "source_unspecified",
                             "grouping": {"kind": "unresolved", "notes_per_beat": 4,
                                          "beat_unit_q": None, "marking_factor": [1, 1],
                                          "source_label": "Sixteenth notes; one four-note group per authored beat"},
                             "tail_pause": None,
                             "unresolved": ["Absolute BPM, quarter-note beat mapping and optional inter-cell pause are unbound."]})
            membership.append({"label": label, "event_local_ordinals": list(range(1, 41)),
                               "group_indices": list(range(1, 11)),
                               "repeated_octave_root_ordinals": [20, 21]})
        fields = {"id": None, "workbook_id": None, "module_id": None, "legacy_level": 16,
                  "title": f"Rung {index:02d}: {row['key']} major one-octave four-note rolling sequence",
                  "kind": "notation", "content_revision": None, "status": "converted_candidate",
                  "runtime_eligible": False, "source_refs": refs, "authored_text_refs": refs,
                  "normalization": [{"kind": "representation_metadata", "basis": "P11 whole-Level16 candidate and original TXT/PDF",
                                     "text": "One 40-contact cell has ten four-note groups, overlaps three notes between adjacent groups and repeats the octave root at the turn; the whole frame shifts only after the cell."}],
                  "context": {"local_code": key,
                              "route": "UP rungs01-13; DOWN landmarks13-01; continuous trip rungs01-13 then12-01",
                              "position": f"low-E root fret {root_fret}; frame {root_fret - 1}-{root_fret + 2}",
                              "pick_start": "D or U; alternate picking continues across groups, turn and relocation",
                              "pick_start_variants": ["D", "U"], "pick_continues_at_turn": True,
                              "tuning_open_midi": [40, 45, 50, 55, 59, 64], "capo": 0,
                              "source_group_count": 10, "source_notes_per_group": 4,
                              "shift_after_complete_cell_only": True},
                  "events": events,
                  "timing": {"status": "unresolved", "unit": "quarter",
                             "basis": "Source sixteenth/group and relative BPM instructions do not allocate an authorized absolute quarter-note event grid or pause binding",
                             "other_source_requirements": ["Sixteenth notes: one four-note group per beat.",
                                                           "Shift the complete frame one fret only after the 40-note cell."]},
                  "rubric": None, "resource_requirements": [],
                  "ambiguities": ["Quarter-note onset/duration and absolute BPM are unassigned.",
                                  "Optional inter-cell practice pause has no selected beat-unit/pass binding."],
                  "control_scope": {"local_case": f"Level16 rung{index:02d} {row['key']} major full 40-contact rolling cell",
                                    "extent": "complete_selected_case", "whole_workbook_complete": False,
                                    "source_event_count": 40, "basis_refs": refs,
                                    "unresolved": ["Identity, lineage and route-level admission pending."]},
                  "variants": variants, "lineage": None}
        need(set(fields) == FIELDS, "FIELD_SHAPE")
        records.append({"source_local_key": key, "rung_number": index, "key": row["key"],
                        "root_fret": root_fret, "frame": row["frame_frets"],
                        "schema1_fields": fields, "group_memberships": groups,
                        "variant_memberships": membership,
                        "source_printed_rows": {"txt_card": row["raw_txt_card"],
                                                "pdf_card": row["raw_pdf_card"],
                                                "pdf_route_map_row": row["raw_pdf_route_map_row"]},
                        "identity_state": "unallocated", "schema1_importable": False,
                        "open_gaps": ["canonical identities and lineage", "quarter-note timing and pause binding",
                                      "runtime/Curriculum admission"]})
        source_map.append({"source_local_key": key, "rung_number": index, "key": row["key"],
                           "root_fret": root_fret, "frame": row["frame_frets"],
                           "txt": txt, "pdf_card": pdf_card, "pdf_route_map": pdf_map})
    up = [f"L16-rung{i:02d}" for i in range(1, 14)]
    down = list(reversed(up))
    trip = up + down[1:]
    need(candidate["ascending_route"] == list(range(1, 14)) and
         candidate["descending_route_after_high_a"] == list(range(12, 0, -1)) and
         candidate["round_trip_rung_order"] == list(range(1, 14)) + list(range(12, 0, -1)) and
         candidate["reverse_after_rung"] == 13 and
         candidate["frame_shift_after_cell_frets"] == {"ascending_except_turn": 1, "descending": -1},
         "ROUTE_SOURCE")
    counts = {"records": 13, "groups": 130, "events": 520, "variants": 26,
              "up_landmark_cells": 13, "down_landmark_cells": 13,
              "continuous_round_trip_cells": 25, "round_trip_contact_traversals": 1000}
    proposal = {"proposal_version": "parallel12-level016-unallocated-schema1-fields.1",
                "classification": "source_mapped_field_proposal_not_schema1_importable",
                "legacy_level": 16,
                "source_pins": {str(path): {"bytes": (root / path).stat().st_size, "sha256": digest}
                                for path, (_, digest) in PINS.items()},
                "counts": counts, "source_guidance": candidate["source_guidance"],
                "current659_level16_records": 0, "current659_level16_workbook_identity": False,
                "canonical_ids_allocated": False, "runtime_eligible": False, "admitted": False,
                "fixed_bpm": None, "note_per_click": None, "onset_q": None, "duration_q": None,
                "records": records}
    handoff = {"version": "parallel12-level016-allocation-handoff.1",
               "status": "pending_P02_serial_floor_and_allocation_authority",
               "proposal_sha256": sha(encode(proposal)), "source_map": source_map,
               "guidance_refs": GUIDANCE_REFS,
               "routes": {"up_landmarks": up, "down_landmarks": down,
                          "continuous_round_trip": trip, "turn_after_rung": "L16-rung13",
                          "shift_frets_up": 1, "shift_frets_down": -1},
               "record_count": 13, "group_count": 130, "event_count": 520, "variant_count": 26,
               "current659_level16_records": 0, "current659_level16_workbook_identity": False,
               "decisions_required": ["P02 serial floor, workbook/module/item/variant identity and source-key bridge",
                                      "Curriculum review of four-note overlap, repeated root and 25-cell route",
                                      "Reviewed timing/pause binding and lineage/admission policy before import"],
               "selected_choice": None, "allocation_allowed": False, "no_admission": True}
    verify(proposal, handoff)
    return proposal, handoff


def verify(proposal: dict, handoff: dict) -> dict:
    need(proposal["canonical_ids_allocated"] is False and proposal["runtime_eligible"] is False and
         proposal["admitted"] is False and handoff["allocation_allowed"] is False and
         handoff["no_admission"] is True and handoff["selected_choice"] is None and
         all(proposal[k] is None for k in ("fixed_bpm", "note_per_click", "onset_q", "duration_q")),
         "INVALID_AUTHORITY")
    counts = {"records": 13, "groups": 130, "events": 520, "variants": 26,
              "up_landmark_cells": 13, "down_landmark_cells": 13,
              "continuous_round_trip_cells": 25, "round_trip_contact_traversals": 1000}
    need(proposal["counts"] == counts and
         (handoff["record_count"], handoff["group_count"], handoff["event_count"],
          handoff["variant_count"]) == (13, 130, 520, 26), "COVERAGE")
    keys = [f"L16-rung{i:02d}" for i in range(1, 14)]
    need([r["source_local_key"] for r in proposal["records"]] == keys and
         [r["source_local_key"] for r in handoff["source_map"]] == keys and
         handoff["routes"]["up_landmarks"] == keys and
         handoff["routes"]["down_landmarks"] == list(reversed(keys)) and
         handoff["routes"]["continuous_round_trip"] == keys + list(reversed(keys))[1:] and
         handoff["routes"]["turn_after_rung"] == "L16-rung13", "ROUTE_OR_CASE_ORDER")
    for index, record in enumerate(proposal["records"], 1):
        fields = record["schema1_fields"]
        need(record["rung_number"] == index and record["key"] == p11.KEYS[index - 1] and
             record["root_fret"] == index + 4 and record["frame"] == [index + 3, index + 6] and
             record["identity_state"] == "unallocated" and record["schema1_importable"] is False and
             set(fields) == FIELDS and fields["legacy_level"] == 16 and
             fields["context"]["local_code"] == record["source_local_key"] and
             all(fields[k] is None for k in ("id", "workbook_id", "module_id", "content_revision", "lineage")) and
             fields["runtime_eligible"] is False and fields["timing"]["status"] == "unresolved", "INVALID_AUTHORITY")
        need(len(fields["events"]) == 40 and len(record["group_memberships"]) == 10 and
             len(fields["variants"]) == len(record["variant_memberships"]) == 2, "CELL_COUNT")
        for ordinal, event in enumerate(fields["events"], 1):
            group_index, slot_index = divmod(ordinal - 1, 4)
            degree = p11.GROUPS[group_index][slot_index]
            string = p11.SCALE_STRING[degree - 1]
            fret = index + 4 + (-1 if degree in (3, 6) else 1 if degree == 7 else
                                2 if degree in (2, 5, 8) else 0)
            string_num, open_midi = OPEN_MIDI[string]
            need(event["event_id"] is event["onset_q"] is event["duration_q"] is None and
                 event["kind"] == "note" and
                 (event["string"], event["fret"], event["midi"], event["finger"]) ==
                 (string_num, fret, open_midi + fret, p11.FINGERS[degree - 1]) and
                 event["spelling"] == p11.TONES[index - 1].split()[degree - 1] and
                 event["degree_contexts"] == {f"{record['key']}-major": {
                     "source_label": str(degree), "ordinal": degree, "alteration": 0}},
                 "UNSUPPORTED_TIMING_OR_NOTE")
        for group_index, group in enumerate(record["group_memberships"], 1):
            need(group["source_group"] == group_index and
                 group["direction"] == ("up" if group_index <= 5 else "down") and
                 group["event_local_ordinals"] == list(range((group_index - 1) * 4 + 1, group_index * 4 + 1)) and
                 group["source_degrees"] == list(p11.GROUPS[group_index - 1]) and
                 group["source_beat_relation"] == "one_four_note_group_per_beat" and
                 group["beat_unit_q"] is None, "GROUP_MEMBERSHIP")
        need((fields["events"][19]["string"], fields["events"][19]["fret"], fields["events"][19]["midi"]) ==
             (fields["events"][20]["string"], fields["events"][20]["fret"], fields["events"][20]["midi"]),
             "TURN_ROOT")
        need([v["pick_start"] for v in fields["variants"]] == ["D", "U"] and
             all(v["id"] is v["event_ids"] is None and v["grouping"]["kind"] == "unresolved" and
                 v["grouping"]["beat_unit_q"] is None for v in fields["variants"]) and
             all(m["event_local_ordinals"] == list(range(1, 41)) and
                 m["group_indices"] == list(range(1, 11)) and
                 m["repeated_octave_root_ordinals"] == [20, 21]
                 for m in record["variant_memberships"]), "VARIANT_MEMBERSHIP")
    need(handoff["proposal_sha256"] == sha(encode(proposal)) and
         proposal["current659_level16_records"] == handoff["current659_level16_records"] == 0 and
         proposal["current659_level16_workbook_identity"] is handoff["current659_level16_workbook_identity"] is False,
         "PROPOSAL_HASH_OR_CURRENT659")
    return counts


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
    print(json.dumps({"status": "unallocated_level016_pending_P02_serial_floor",
                      "counts": verify(proposal, handoff)}, sort_keys=True))


if __name__ == "__main__":
    main()
