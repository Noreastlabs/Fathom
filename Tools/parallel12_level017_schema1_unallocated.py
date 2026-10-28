#!/usr/bin/env python3
"""Whole-Level17 rolling-ladder source fields, without canonical allocation."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from pypdf import PdfReader

import parallel10_level017_rolling_candidate as p10

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = Path("Build/parallel-10/2.3.1.1.1-level017-whole-rolling-r01/candidate-02.json")
RESULT = Path("Results/parallel-10/exercises/conversion/20260923T145200Z-2.3.1.1.1-level017-whole-rolling-r01-results.md")
PACKAGE = Path("Content/controls/curriculum-v1/package.json")
REGISTRY = Path("Content/controls/curriculum-v1/identity-registry.json")
OUT = Path("Build/parallel-12/level017-schema1-unallocated-r01")
PINS = {
    CANDIDATE: (189426, "b16f5fca1d2e1b043a07d8859fd73fb8421824cc320e4e0ea09caddd0596151d"),
    RESULT: (None, "255c5e70fbbb5a06ef20f91ecde50f4baf10602364916eedf264a76cb9337c86"),
    p10.TXT_REL: (46483, p10.TXT_SHA), p10.PDF_REL: (31200, p10.PDF_SHA),
    PACKAGE: (None, "766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255"),
    REGISTRY: (None, "5d265859e1e8a5a530a0e53d88b019a1c920f3bba6cccb4ef0fef2f7640007e5"),
}
FIELDS = {"id", "workbook_id", "module_id", "legacy_level", "title", "kind", "content_revision",
          "status", "runtime_eligible", "source_refs", "authored_text_refs", "normalization", "context",
          "events", "timing", "rubric", "resource_requirements", "ambiguities", "control_scope",
          "variants", "lineage"}
PITCH_CLASS = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
GUIDANCE_REFS = ["L17-TXT1-34-48", "L17-TXT1-58-66", "L17-TXT1-381-384"]


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


def pitch_class(spelling: str) -> int:
    need(re.fullmatch(r"[A-G](?:#|b)?", spelling) is not None, "SPELLING_SHAPE")
    return (PITCH_CLASS[spelling[0]] + (1 if spelling.endswith("#") else -1 if spelling.endswith("b") else 0)) % 12


def txt_span(ref: str, lines: list[str]) -> dict:
    match = re.fullmatch(r"L17-TXT1-(\d+)-(\d+)", ref)
    need(match is not None, "TXT_REF")
    first, last = map(int, match.groups())
    need(1 <= first <= last <= len(lines), "TXT_SPAN")
    return {"ref": ref, "first_line": first, "last_line": last,
            "text_sha256": sha("\n".join(lines[first - 1:last]).encode())}


def expected_positions(group_index: int) -> list[int]:
    if group_index <= 12:
        return list(range(group_index, group_index + 4))
    j = group_index - 13
    return list(range(15 - j, 11 - j, -1))


def build(root: Path = ROOT, candidate_override: dict | None = None) -> tuple[dict, dict]:
    pin(root)
    candidate = candidate_override if candidate_override is not None else json.loads((root / CANDIDATE).read_text())
    need(candidate == p10.build_candidate(root), "P10_SOURCE_CANDIDATE_DRIFT")
    need(candidate["level"] == 17 and len(candidate["rungs"]) == 13 and not candidate["exceptions"] and
         all(candidate[k] is False for k in ("canonical_identity_assigned", "runtime_import_authorized",
                                              "curriculum_reviewed", "timing_interpreted")), "SOURCE_SCOPE")
    foundation = json.loads((root / PACKAGE).read_text())
    registry = json.loads((root / REGISTRY).read_text())
    need(len(foundation["records"]) == 659 and
         not any(r["legacy_level"] == 17 for r in foundation["records"]) and
         not any(e["id"] == "fg:workbook:000017" or e.get("parent") == "fg:workbook:000017"
                 for e in registry["entities"]), "CURRENT659_LEVEL17_OVERLAP")
    lines = (root / p10.TXT_REL).read_text().splitlines()
    pages = [page.extract_text() for page in PdfReader(str(root / p10.PDF_REL)).pages]
    need(len(pages) == 10, "PDF_COUNT")
    records, source_map = [], []
    for index, rung in enumerate(candidate["rungs"], 1):
        key, root_fret = f"L17-rung{index:02d}", index + 4
        need(rung["rung"] == index and rung["key"] == p10.KEYS[index - 1] and
             rung["low_e_root_fret"] == root_fret and
             rung["frame_frets"] == [root_fret - 1, root_fret + 2] and
             rung["txt_header_line"] == 69 + (index - 1) * 24 and
             rung["cell_note_count"] == 96 and len(rung["groups"]) == 24 and
             all(rung[k] is None for k in ("canonical_item_id", "fixed_bpm", "note_per_click", "onset", "duration")) and
             rung["runtime_eligible"] is rung["admitted"] is False, "RUNG_SCOPE")
        start = rung["txt_header_line"]
        block = lines[start - 1:start + 21]
        need(len(block) == 22 and block[0].startswith(f"RUNG {index:02d} OF 13") and
             all(value in block for half in rung["source_halves"].values() for value in half.values()),
             "TXT_CARD_SPAN")
        txt_ref = f"L17-TXT1-{start}-{start + 21}"
        pdf_ref = f"L17-PDF1-p{rung['pdf_page']}"
        need(3 <= rung["pdf_page"] <= 9 and
             re.search(rf"\b{index:02d}\b\s+{rung['key'].upper()}\s+MAJOR",
                       pages[rung["pdf_page"] - 1]) is not None, "PDF_CARD")
        refs = [txt_ref, pdf_ref, "L17-PDF1-p2", *GUIDANCE_REFS]
        base = p10.scale_contacts(root_fret, index - 1)
        need(rung["scale_tones_two_octaves"] == list(p10.TONES[index - 1]) * 2 + [rung["key"]],
             "SCALE_TONES")
        events, groups = [], []
        for group_index, group in enumerate(rung["groups"], 1):
            phase = "ascending" if group_index <= 12 else "descending"
            source_group = (group_index - 1) % 12 + 1
            positions = expected_positions(group_index)
            need(group["group"] == source_group and group["scale_positions"] == positions and
                 len(group["notes"]) == 4, "GROUP_SOURCE")
            ordinals = []
            for slot, note in enumerate(group["notes"], 1):
                ordinal = (group_index - 1) * 4 + slot
                position = positions[slot - 1]
                expected = {**base[position - 1], "cell_note_index": (source_group - 1) * 4 + slot}
                need(note == expected, "NOTE_SOURCE")
                string = p10.STRINGS.index(note["string"]) + 1
                midi = p10.TUNING[note["string"]] + note["fret"]
                need(note["midi"] == midi and
                     pitch_class(note["source_tone"]) == midi % 12, "NOTE_PITCH_SPELLING")
                events.append({"event_id": None, "kind": "note", "string": string,
                               "fret": note["fret"], "midi": midi, "spelling": note["source_tone"],
                               "degree_contexts": {f"{rung['key']}-major": {
                                   "source_label": str(position), "ordinal": position, "alteration": 0}},
                               "finger": note["finger"], "onset_q": None, "duration_q": None,
                               "attack": "picked", "tie_from": None})
                ordinals.append(ordinal)
            groups.append({"source_group": source_group, "whole_cell_group": group_index,
                           "phase": phase, "event_local_ordinals": ordinals,
                           "source_scale_positions": positions,
                           "source_beat_relation": "one_four_note_group_per_beat",
                           "beat_unit_q": None})
        need(len(events) == 96 and
             (events[47]["string"], events[47]["fret"], events[47]["midi"]) ==
             (events[48]["string"], events[48]["fret"], events[48]["midi"]), "CELL_TURN")
        variants, membership = [], []
        for pick in ("D", "U"):
            label = f"rolling-four-{pick}-start"
            variants.append({"id": None, "label": label, "event_ids": None, "source_refs": refs,
                             "route": "two_octave_24_four_note_groups_repeated_high_root",
                             "pick_start": pick, "pick_start_origin": "source_authored",
                             "role": "notation_practice", "accent_policy": "source_unspecified",
                             "grouping": {"kind": "unresolved", "notes_per_beat": 4,
                                          "beat_unit_q": None, "marking_factor": [1, 1],
                                          "source_label": "Sixteenth notes; one four-note group per authored beat"},
                             "tail_pause": None,
                             "unresolved": ["Absolute BPM, quarter-note beat mapping and optional one-beat pause are unbound."]})
            membership.append({"label": label, "event_local_ordinals": list(range(1, 97)),
                               "group_indices": list(range(1, 25)),
                               "repeated_high_root_ordinals": [48, 49]})
        fields = {"id": None, "workbook_id": None, "module_id": None, "legacy_level": 17,
                  "title": f"Rung {index:02d}: {rung['key']} major two-octave four-note rolling sequence",
                  "kind": "notation", "content_revision": None, "status": "converted_candidate",
                  "runtime_eligible": False, "source_refs": refs, "authored_text_refs": refs,
                  "normalization": [{"kind": "representation_metadata", "basis": "P10 whole-Level17 candidate and original TXT/PDF",
                                     "text": "One 96-contact cell has 24 overlapping four-note groups and repeats the high root at the turn; the whole frame shifts only after a completed cell."}],
                  "context": {"local_code": key,
                              "route": "UP rungs01-13; DOWN landmarks13-01; continuous trip rungs01-13 then12-01",
                              "position": f"low-E root fret {root_fret}; frame {root_fret - 1}-{root_fret + 2}",
                              "pick_start": "D or U; alternate picking continues across groups, turn and relocation",
                              "pick_start_variants": ["D", "U"], "pick_continues_at_turn": True,
                              "tuning_open_midi": [40, 45, 50, 55, 59, 64], "capo": 0,
                              "source_group_count": 24, "source_notes_per_group": 4,
                              "shift_after_complete_cell_only": True},
                  "events": events,
                  "timing": {"status": "unresolved", "unit": "quarter",
                             "basis": "Source sixteenth/group and relative BPM instructions do not allocate an authorized absolute quarter-note event grid or pause binding",
                             "other_source_requirements": candidate["guidance_only"]["practice_rule"]},
                  "rubric": None, "resource_requirements": [],
                  "ambiguities": ["Quarter-note onset/duration and absolute BPM are unassigned.",
                                  "Optional one-beat inter-cell pause has no selected beat-unit/pass binding."],
                  "control_scope": {"local_case": f"Level17 rung{index:02d} {rung['key']} major full 96-contact rolling cell",
                                    "extent": "complete_selected_case", "whole_workbook_complete": False,
                                    "source_event_count": 96, "basis_refs": refs,
                                    "unresolved": ["Identity, lineage and route-level admission pending."]},
                  "variants": variants, "lineage": None}
        need(set(fields) == FIELDS, "FIELD_SHAPE")
        records.append({"source_local_key": key, "rung_number": index, "key": rung["key"],
                        "root_fret": root_fret, "frame": rung["frame_frets"],
                        "schema1_fields": fields, "group_memberships": groups,
                        "variant_memberships": membership,
                        "source_printed_rows": rung["source_halves"],
                        "identity_state": "unallocated", "schema1_importable": False,
                        "open_gaps": ["canonical identities and lineage", "quarter-note timing and pause binding",
                                      "runtime/Curriculum admission"]})
        source_map.append({"source_local_key": key, "rung_number": index, "key": rung["key"],
                           "root_fret": root_fret, "frame": rung["frame_frets"],
                           "txt": txt_ref, "txt_passage_sha256": sha("\n".join(block).encode()),
                           "pdf_card": pdf_ref, "pdf_route_map": "L17-PDF1-p2"})
    up = [f"L17-rung{i:02d}" for i in range(1, 14)]
    down = list(reversed(up))
    trip = up + down[1:]
    need(candidate["ladder"]["up_rungs"] == list(range(1, 14)) and
         candidate["ladder"]["down_rungs"] == list(range(12, 0, -1)) and
         candidate["ladder"]["round_trip_cells"] == 25 and
         candidate["ladder"]["round_trip_note_contacts"] == 2400, "ROUTE_SOURCE")
    counts = {"records": 13, "groups": 312, "events": 1248, "variants": 26,
              "up_landmark_cells": 13, "down_landmark_cells": 13,
              "continuous_round_trip_cells": 25, "round_trip_contact_traversals": 2400}
    proposal = {"proposal_version": "parallel12-level017-unallocated-schema1-fields.1",
                "classification": "source_mapped_field_proposal_not_schema1_importable",
                "legacy_level": 17,
                "source_pins": {str(path): {"bytes": (root / path).stat().st_size, "sha256": digest}
                                for path, (_, digest) in PINS.items()},
                "counts": counts, "source_guidance": candidate["guidance_only"],
                "current659_level17_records": 0, "current659_level17_workbook_identity": False,
                "canonical_ids_allocated": False, "runtime_eligible": False, "admitted": False,
                "fixed_bpm": None, "note_per_click": None, "onset_q": None, "duration_q": None,
                "records": records}
    handoff = {"version": "parallel12-level017-allocation-handoff.1",
               "status": "pending_P02_serial_floor_and_allocation_authority",
               "proposal_sha256": sha(encode(proposal)), "source_map": source_map,
               "guidance_refs": GUIDANCE_REFS,
               "routes": {"up_landmarks": up, "down_landmarks": down,
                          "continuous_round_trip": trip, "turn_after_rung": "L17-rung13",
                          "shift_frets_up": 1, "shift_frets_down": -1},
               "record_count": 13, "group_count": 312, "event_count": 1248, "variant_count": 26,
               "current659_level17_records": 0, "current659_level17_workbook_identity": False,
               "decisions_required": ["P02 serial floor, workbook/module/item/variant identity and source-key bridge",
                                      "Curriculum review of four-note overlap, high-root turn and 25-cell route",
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
    counts = {"records": 13, "groups": 312, "events": 1248, "variants": 26,
              "up_landmark_cells": 13, "down_landmark_cells": 13,
              "continuous_round_trip_cells": 25, "round_trip_contact_traversals": 2400}
    need(proposal["counts"] == counts and
         (handoff["record_count"], handoff["group_count"], handoff["event_count"],
          handoff["variant_count"]) == (13, 312, 1248, 26), "COVERAGE")
    keys = [f"L17-rung{i:02d}" for i in range(1, 14)]
    need([r["source_local_key"] for r in proposal["records"]] == keys and
         [r["source_local_key"] for r in handoff["source_map"]] == keys and
         handoff["routes"]["up_landmarks"] == keys and
         handoff["routes"]["down_landmarks"] == list(reversed(keys)) and
         handoff["routes"]["continuous_round_trip"] == keys + list(reversed(keys))[1:] and
         handoff["routes"]["turn_after_rung"] == "L17-rung13", "ROUTE_OR_CASE_ORDER")
    for index, record in enumerate(proposal["records"], 1):
        fields = record["schema1_fields"]
        need(record["rung_number"] == index and record["key"] == p10.KEYS[index - 1] and
             record["root_fret"] == index + 4 and record["frame"] == [index + 3, index + 6] and
             record["identity_state"] == "unallocated" and record["schema1_importable"] is False and
             set(fields) == FIELDS and fields["legacy_level"] == 17 and
             fields["context"]["local_code"] == record["source_local_key"] and
             all(fields[k] is None for k in ("id", "workbook_id", "module_id", "content_revision", "lineage")) and
             fields["runtime_eligible"] is False and fields["timing"]["status"] == "unresolved", "INVALID_AUTHORITY")
        need(len(fields["events"]) == 96 and len(record["group_memberships"]) == 24 and
             len(fields["variants"]) == len(record["variant_memberships"]) == 2, "CELL_COUNT")
        base = p10.scale_contacts(index + 4, index - 1)
        for ordinal, event in enumerate(fields["events"], 1):
            group_index, slot_index = divmod(ordinal - 1, 4)
            position = expected_positions(group_index + 1)[slot_index]
            note = base[position - 1]
            need(event["event_id"] is event["onset_q"] is event["duration_q"] is None and
                 event["kind"] == "note" and
                 (event["string"], event["fret"], event["midi"], event["finger"], event["spelling"]) ==
                 (p10.STRINGS.index(note["string"]) + 1, note["fret"], note["midi"],
                  note["finger"], note["source_tone"]) and
                 event["degree_contexts"] == {f"{record['key']}-major": {
                     "source_label": str(position), "ordinal": position, "alteration": 0}},
                 "UNSUPPORTED_TIMING_OR_NOTE")
        for group_index, group in enumerate(record["group_memberships"], 1):
            need(group == {"source_group": (group_index - 1) % 12 + 1,
                           "whole_cell_group": group_index,
                           "phase": "ascending" if group_index <= 12 else "descending",
                           "event_local_ordinals": list(range((group_index - 1) * 4 + 1, group_index * 4 + 1)),
                           "source_scale_positions": expected_positions(group_index),
                           "source_beat_relation": "one_four_note_group_per_beat", "beat_unit_q": None},
                 "GROUP_MEMBERSHIP")
        need((fields["events"][47]["string"], fields["events"][47]["fret"], fields["events"][47]["midi"]) ==
             (fields["events"][48]["string"], fields["events"][48]["fret"], fields["events"][48]["midi"]),
             "TURN_ROOT")
        need([v["pick_start"] for v in fields["variants"]] == ["D", "U"] and
             all(v["id"] is v["event_ids"] is None and v["grouping"]["kind"] == "unresolved" and
                 v["grouping"]["beat_unit_q"] is None for v in fields["variants"]) and
             all(m["event_local_ordinals"] == list(range(1, 97)) and
                 m["group_indices"] == list(range(1, 25)) and
                 m["repeated_high_root_ordinals"] == [48, 49]
                 for m in record["variant_memberships"]), "VARIANT_MEMBERSHIP")
    need(handoff["proposal_sha256"] == sha(encode(proposal)) and
         proposal["current659_level17_records"] == handoff["current659_level17_records"] == 0 and
         proposal["current659_level17_workbook_identity"] is handoff["current659_level17_workbook_identity"] is False,
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
    print(json.dumps({"status": "unallocated_level017_pending_P02_serial_floor",
                      "counts": verify(proposal, handoff)}, sort_keys=True))


if __name__ == "__main__":
    main()
