#!/usr/bin/env python3
"""Project P07's whole Level18 source into detached, unallocated schema1 fields."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import parallel_07_level018_whole_candidate as p07

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = p07.BUILD_REL / "candidate.json"
RESULT = Path("Results/parallel-07/conversion/20260923T145509Z-2.3.1.1.1-level018-whole-candidate-r01-results.md")
PACKAGE = Path("Content/controls/curriculum-v1/package.json")
REGISTRY = Path("Content/controls/curriculum-v1/identity-registry.json")
OUT = Path("Build/parallel-12/level018-schema1-unallocated-r01")
PINS = {
    CANDIDATE: (378374, "9950bd9fad4f909d9ffcac3266612a88f093ab25b2897d8c259b28b6eb36ebf2"),
    RESULT: (None, "11021dd468210016d7e114a59a8e9c56967875c184b14793243ce9645ec7368a"),
    p07.TXT_REL: (p07.TXT_BYTES, p07.TXT_SHA256),
    p07.PDF_REL: (p07.PDF_BYTES, p07.PDF_SHA256),
    PACKAGE: (None, "766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255"),
    REGISTRY: (None, "5d265859e1e8a5a530a0e53d88b019a1c920f3bba6cccb4ef0fef2f7640007e5"),
}
FIELDS = {"id", "workbook_id", "module_id", "legacy_level", "title", "kind", "content_revision",
          "status", "runtime_eligible", "source_refs", "authored_text_refs", "normalization", "context",
          "events", "timing", "rubric", "resource_requirements", "ambiguities", "control_scope",
          "variants", "lineage"}
GUIDANCE_REFS = ["L18-TXT1-1-70", "L18-TXT1-423-459", "L18-PDF1-p1", "L18-PDF1-p2", "L18-PDF1-p10"]


class ProposalError(ValueError):
    pass


def need(ok: bool, code: str) -> None:
    if not ok:
        raise ProposalError(code)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def encode(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def pin(root: Path = ROOT) -> None:
    need(root.resolve() == ROOT.resolve(), "ROOT_DRIFT")
    for path, (length, digest) in PINS.items():
        raw = (root / path).read_bytes()
        need((length is None or len(raw) == length) and sha(raw) == digest, f"INPUT_DRIFT {path}")


def txt_span(ref: str, lines: list[str]) -> dict:
    match = re.fullmatch(r"L18-TXT1-(\d+)-(\d+)", ref)
    need(match is not None, "TXT_REF")
    first, last = map(int, match.groups())
    need(1 <= first <= last <= len(lines), "TXT_SPAN")
    return {"ref": ref, "first_line": first, "last_line": last,
            "text_sha256": sha("\n".join(lines[first - 1:last]).encode())}


def source_event(note: dict, key: str) -> dict:
    string = p07.STRINGS_HIGH_TO_LOW.index(note["string"])
    string = 6 - string
    midi = p07.OPEN_MIDI[note["string"]] + note["fret"]
    need(midi % 12 == p07._pitch_class(note["tone"]), "PITCH_SPELLING")
    return {"event_id": None, "kind": "note", "string": string,
            "fret": note["fret"], "midi": midi, "spelling": note["tone"],
            "degree_contexts": {f"{key}-major": {"source_label": str(note["degree"]),
                                                  "ordinal": note["degree"], "alteration": 0}},
            "finger": note["finger_digit"], "onset_q": None, "duration_q": None,
            "attack": "picked", "tie_from": None}


def build(root: Path = ROOT, candidate_override: dict | None = None) -> tuple[dict, dict]:
    pin(root)
    candidate = candidate_override if candidate_override is not None else json.loads((root / CANDIDATE).read_text())
    need(candidate == p07.build_candidate(), "P07_SOURCE_CANDIDATE_DRIFT")
    need(candidate["level"] == 18 and len(candidate["records"]) == 13 and
         len(candidate["exceptions"]) == 1 and candidate["exceptions"][0]["kind"] == "pdf_layout" and
         all(candidate[k] is False for k in ("whole_workbook_complete", "runtime_eligible",
                                              "runtime_admitted", "imported", "admitted")), "SOURCE_SCOPE")
    foundation = json.loads((root / PACKAGE).read_text())
    registry = json.loads((root / REGISTRY).read_text())
    current = [r for r in foundation["records"] if r.get("legacy_level") == 18]
    identities = [e for e in registry["entities"] if e.get("id") == "fg:workbook:000018" or
                  e.get("parent") == "fg:workbook:000018"]
    need(len(foundation["records"]) == 659 and not current and not identities, "CURRENT659_LEVEL18_OVERLAP")
    lines = (root / p07.TXT_REL).read_text().splitlines()
    need(len(lines) == 459, "TXT_LINE_COUNT")
    records, source_map = [], []
    for index, card in enumerate(candidate["records"], 1):
        key = p07.KEYS[index - 1]
        local = f"L18-rung{index:02d}"
        need(card["source_local_key"] == local and card["rung_number"] == f"{index:02d}" and
             card["key"] == key and card["root_string"] == "E" and card["root_fret"] == index + 4 and
             [card["frame_low"], card["frame_high"]] == [index + 3, index + 6] and
             card["octave_rung"] == (index == 13) and len(card["directions"]) == 2 and
             card["pdf_card_has_int_row"] is False and
             all(card[k] is None for k in ("canonical_item_id", "canonical_variant_id", "onset_q",
                                            "duration_q", "fixed_bpm", "note_per_click")) and
             all(card[k] is False for k in ("runtime_eligible", "runtime_admitted", "imported", "admitted")),
             "CARD_SCOPE")
        start = 72 + (index - 1) * 27
        txt_ref = f"L18-TXT1-{start}-{start + 23}"
        pdf_ref = f"L18-PDF1-p{3 + (index - 1) // 2}"
        need(card["source_refs"] == {"txt": txt_ref, "pdf_card": pdf_ref,
                                    "pdf_route_quality": "L18-PDF1-p2"}, "SOURCE_REFS")
        span = txt_span(txt_ref, lines)
        need(lines[start - 1].startswith(f"RUNG {index:02d} OF 13") and
             lines[start + 22].startswith("Finish on the low root"), "TXT_CARD")
        refs = [txt_ref, pdf_ref, *GUIDANCE_REFS]
        events, pairs, printed = [], [], []
        for direction_index, half in enumerate(card["directions"]):
            direction = "ascending" if direction_index == 0 else "descending"
            need(half["direction"] == direction and len(half["pairs"]) == 13 and
                 len(half["notes"]) == 26 and len(half["raw_rows"]) == 9, "DIRECTION_SCOPE")
            printed.append({"direction": direction, "raw_rows": half["raw_rows"]})
            for pair_index, pair in enumerate(half["pairs"], 1):
                source_notes = half["notes"][(pair_index - 1) * 2:pair_index * 2]
                ordinals = [direction_index * 26 + (pair_index - 1) * 2 + n for n in (1, 2)]
                need(pair["ordinal"] == pair_index and pair["note_ordinals"] ==
                     [(pair_index - 1) * 2 + 1, pair_index * 2] and
                     pair["degrees"] == [n["degree"] for n in source_notes] and
                     pair["quality"] in ("M3", "m3") and
                     pair["semitones"] == (4 if pair["quality"] == "M3" else 3), "PAIR_SCOPE")
                pair_events = [source_event(note, key) for note in source_notes]
                need(abs(pair_events[1]["midi"] - pair_events[0]["midi"]) == pair["semitones"],
                     "PAIR_SEMITONES")
                events.extend(pair_events)
                pairs.append({"whole_cell_pair": direction_index * 13 + pair_index,
                              "source_pair": pair_index, "direction": direction,
                              "event_local_ordinals": ordinals, "degrees": pair["degrees"],
                              "quality": pair["quality"], "semitones": pair["semitones"],
                              "source_note_columns": [n["ascii_column_in_pair"] for n in source_notes],
                              "source_note_ordinals": pair["note_ordinals"]})
        need(len(events) == 52 and len(pairs) == 26 and
             (events[25]["string"], events[25]["fret"], events[25]["midi"]) ==
             (events[26]["string"], events[26]["fret"], events[26]["midi"]), "HIGH_ROOT_TURN")
        variants, memberships = [], []
        for pick in ("D", "U"):
            label = f"third-pairs-{pick}-start"
            variants.append({"id": None, "label": label, "event_ids": None,
                             "source_refs": refs, "route": "26_sequential_third_pairs_high_root_repeated",
                             "pick_start": pick, "pick_start_origin": "source_authored",
                             "role": "notation_practice", "accent_policy": "learning_first_of_pair_per_source",
                             "grouping": {"kind": "unresolved", "notes_per_beat": None,
                                          "beat_unit_q": None, "marking_factor": [1, 1],
                                          "source_label": "learning: one pair/beat eighths; performance: two pairs/beat straight sixteenths"},
                             "tail_pause": None,
                             "unresolved": ["Pulse mode, absolute BPM and optional inter-cell pause unbound."]})
            memberships.append({"label": label, "event_local_ordinals": list(range(1, 53)),
                                "pair_indices": list(range(1, 27)),
                                "repeated_high_root_ordinals": [26, 27]})
        fields = {"id": None, "workbook_id": None, "module_id": None, "legacy_level": 18,
                  "title": f"Rung {index:02d}: {key} major two-octave diatonic thirds",
                  "kind": "notation", "content_revision": None, "status": "converted_candidate",
                  "runtime_eligible": False, "source_refs": refs, "authored_text_refs": refs,
                  "normalization": [{"kind": "representation_metadata", "basis": "P07 whole-Level18 candidate and original TXT/PDF",
                                     "text": "The 26 printed third pairs form a 52-contact cell; the high root is repeated at the turn. PDF cards omit Int rows; PDF page 2 gives the shared up-quality pattern checked against TXT and semitone gaps."}],
                  "context": {"local_code": local, "route": "UP rungs01-13; DOWN return12-01; continuous trip has 25 cells",
                              "position": f"low-E root fret {index + 4}; frame {index + 3}-{index + 6}",
                              "pick_start": "D-U or U-D through all pairs, turns, strings and key changes",
                              "pick_start_variants": ["D", "U"], "pick_continues_at_turn": True,
                              "tuning_open_midi": [40, 45, 50, 55, 59, 64], "capo": 0,
                              "source_pair_count": 26, "source_notes_per_pair": 2,
                              "shift_after_complete_cell_only": True},
                  "events": events,
                  "timing": {"status": "unresolved", "unit": "quarter",
                             "basis": "Authored learning and performance pulse options do not select an authorized quarter-note event grid or pause binding",
                             "source_pulses": ["learning: one pair per beat as eighth notes",
                                               "performance: two pairs per beat as straight sixteenth notes"],
                             "selected_pulse": None},
                  "rubric": None, "resource_requirements": [],
                  "ambiguities": ["PDF cards omit Int rows; PDF page 2 supplies common up-quality map.",
                                  "Pulse mode, quarter-note onsets/durations and absolute BPM are unassigned.",
                                  "Optional one-beat inter-cell pause has no selected beat-unit/pass binding."],
                  "control_scope": {"local_case": f"Level18 rung{index:02d} {key} major full 52-contact thirds cell",
                                    "extent": "complete_selected_case", "whole_workbook_complete": False,
                                    "source_event_count": 52, "basis_refs": refs,
                                    "unresolved": ["Identity, lineage and route-level admission pending."]},
                  "variants": variants, "lineage": None}
        need(set(fields) == FIELDS, "FIELD_SHAPE")
        records.append({"source_local_key": local, "rung_number": index, "key": key,
                        "root_fret": index + 4, "frame": [index + 3, index + 6],
                        "schema1_fields": fields, "pair_memberships": pairs,
                        "variant_memberships": memberships, "source_printed_rows": printed,
                        "identity_state": "unallocated", "schema1_importable": False,
                        "open_gaps": ["canonical identities and lineage", "pulse/timing and pause binding",
                                      "runtime/Curriculum admission"]})
        source_map.append({"source_local_key": local, "rung_number": index, "key": key,
                           "root_fret": index + 4, "frame": [index + 3, index + 6],
                           "txt": span, "pdf_card": pdf_ref,
                           "pdf_quality_map": "L18-PDF1-p2", "pdf_card_has_int_row": False})
    up = [f"L18-rung{i:02d}" for i in range(1, 14)]
    down = [f"L18-rung{i:02d}" for i in range(12, 0, -1)]
    route = candidate["routes"]
    need(route["up"]["rungs"] == up and route["down_return"]["rungs"] == down and
         route["continuous_round_trip"]["rungs"] == up + down and
         route["continuous_round_trip"]["cell_count"] == 25 and
         route["continuous_round_trip"]["picked_note_count"] == 1300, "ROUTE_SCOPE")
    counts = {"records": 13, "pairs": 338, "events": 676, "variants": 26,
              "up_landmark_cells": 13, "down_return_cells": 12,
              "continuous_round_trip_cells": 25, "round_trip_contact_traversals": 1300}
    proposal = {"proposal_version": "parallel12-level018-unallocated-schema1-fields.1",
                "classification": "source_mapped_field_proposal_not_schema1_importable",
                "legacy_level": 18,
                "source_pins": {str(path): {"bytes": (root / path).stat().st_size, "sha256": digest}
                                for path, (_, digest) in PINS.items()},
                "counts": counts, "source_guidance": candidate["instructions"],
                "source_exceptions": candidate["exceptions"],
                "current659_level18_records": 0, "current659_level18_workbook_identity": False,
                "representative_collision": None,
                "canonical_ids_allocated": False, "runtime_eligible": False, "admitted": False,
                "fixed_bpm": None, "note_per_click": None, "onset_q": None, "duration_q": None,
                "records": records}
    handoff = {"version": "parallel12-level018-allocation-handoff.1",
               "status": "pending_P02_serial_floor_and_allocation_authority",
               "proposal_sha256": sha(encode(proposal)), "source_map": source_map,
               "guidance_refs": GUIDANCE_REFS,
               "routes": {"up_landmarks": up, "down_return": down,
                          "continuous_round_trip": up + down, "turn_after_rung": "L18-rung13",
                          "shift_frets_up": 1, "shift_frets_down": -1},
               "record_count": 13, "pair_count": 338, "event_count": 676, "variant_count": 26,
               "current659_level18_records": 0, "current659_level18_workbook_identity": False,
               "representative_collision": None,
               "decisions_required": ["P02 serial floor, workbook/module/item/variant identity and source-key bridge",
                                      "Curriculum review of thirds qualities, high-root repeat, 25-cell route and PDF Int-row exception",
                                      "Reviewed pulse/timing/pause binding and lineage/admission policy before import"],
               "selected_choice": None, "allocation_allowed": False, "no_admission": True}
    verify(proposal, handoff)
    return proposal, handoff


def verify(proposal: dict, handoff: dict) -> dict:
    need(proposal["canonical_ids_allocated"] is False and proposal["runtime_eligible"] is False and
         proposal["admitted"] is False and handoff["allocation_allowed"] is False and
         handoff["no_admission"] is True and handoff["selected_choice"] is None and
         all(proposal[k] is None for k in ("fixed_bpm", "note_per_click", "onset_q", "duration_q")),
         "INVALID_AUTHORITY")
    counts = {"records": 13, "pairs": 338, "events": 676, "variants": 26,
              "up_landmark_cells": 13, "down_return_cells": 12,
              "continuous_round_trip_cells": 25, "round_trip_contact_traversals": 1300}
    need(proposal["counts"] == counts and
         (handoff["record_count"], handoff["pair_count"], handoff["event_count"], handoff["variant_count"]) ==
         (13, 338, 676, 26), "COVERAGE")
    keys = [f"L18-rung{i:02d}" for i in range(1, 14)]
    need([r["source_local_key"] for r in proposal["records"]] == keys and
         [r["source_local_key"] for r in handoff["source_map"]] == keys and
         handoff["routes"]["up_landmarks"] == keys and
         handoff["routes"]["down_return"] == list(reversed(keys[:-1])) and
         handoff["routes"]["continuous_round_trip"] == keys + list(reversed(keys[:-1])) and
         handoff["routes"]["turn_after_rung"] == "L18-rung13", "ROUTE_OR_CASE_ORDER")
    for index, record in enumerate(proposal["records"], 1):
        fields = record["schema1_fields"]
        need(record["rung_number"] == index and record["key"] == p07.KEYS[index - 1] and
             record["root_fret"] == index + 4 and record["frame"] == [index + 3, index + 6] and
             record["identity_state"] == "unallocated" and record["schema1_importable"] is False and
             set(fields) == FIELDS and fields["legacy_level"] == 18 and
             fields["context"]["local_code"] == record["source_local_key"] and
             all(fields[k] is None for k in ("id", "workbook_id", "module_id", "content_revision", "lineage")) and
             fields["runtime_eligible"] is False and fields["timing"]["status"] == "unresolved" and
             fields["timing"]["selected_pulse"] is None, "INVALID_AUTHORITY")
        need(len(fields["events"]) == 52 and len(record["pair_memberships"]) == 26 and
             len(fields["variants"]) == len(record["variant_memberships"]) == 2, "CELL_COUNT")
        for ordinal, event in enumerate(fields["events"], 1):
            pair_index = (ordinal - 1) // 2
            pair = record["pair_memberships"][pair_index]
            need(event["event_id"] is event["onset_q"] is event["duration_q"] is None and
                 event["kind"] == "note" and event["midi"] == [40, 45, 50, 55, 59, 64][event["string"] - 1] + event["fret"] and
                 event["midi"] % 12 == p07._pitch_class(event["spelling"]) and
                 event["degree_contexts"] == {f"{record['key']}-major": {
                     "source_label": str(pair["degrees"][(ordinal - 1) % 2]),
                     "ordinal": pair["degrees"][(ordinal - 1) % 2], "alteration": 0}} and
                 1 <= event["finger"] <= 4, "UNSUPPORTED_TIMING_OR_NOTE")
        for pair_index, pair in enumerate(record["pair_memberships"], 1):
            first = 2 * pair_index - 1
            need(pair["whole_cell_pair"] == pair_index and
                 pair["source_pair"] == (pair_index - 1) % 13 + 1 and
                 pair["direction"] == ("ascending" if pair_index <= 13 else "descending") and
                 pair["event_local_ordinals"] == [first, first + 1] and
                 abs(fields["events"][first - 1]["midi"] - fields["events"][first]["midi"]) ==
                 pair["semitones"] == (4 if pair["quality"] == "M3" else 3), "PAIR_MEMBERSHIP")
        need((fields["events"][25]["string"], fields["events"][25]["fret"], fields["events"][25]["midi"]) ==
             (fields["events"][26]["string"], fields["events"][26]["fret"], fields["events"][26]["midi"]),
             "TURN_ROOT")
        need([v["pick_start"] for v in fields["variants"]] == ["D", "U"] and
             all(v["id"] is v["event_ids"] is None and v["grouping"]["kind"] == "unresolved" and
                 v["grouping"]["beat_unit_q"] is None for v in fields["variants"]) and
             all(m["event_local_ordinals"] == list(range(1, 53)) and
                 m["pair_indices"] == list(range(1, 27)) and
                 m["repeated_high_root_ordinals"] == [26, 27]
                 for m in record["variant_memberships"]), "VARIANT_MEMBERSHIP")
    need(handoff["proposal_sha256"] == sha(encode(proposal)) and
         proposal["current659_level18_records"] == handoff["current659_level18_records"] == 0 and
         proposal["current659_level18_workbook_identity"] is handoff["current659_level18_workbook_identity"] is False and
         proposal["representative_collision"] is handoff["representative_collision"] is None,
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
    print(json.dumps({"status": "unallocated_level018_pending_P02_serial_floor",
                      "counts": verify(proposal, handoff)}, sort_keys=True))


if __name__ == "__main__":
    main()
