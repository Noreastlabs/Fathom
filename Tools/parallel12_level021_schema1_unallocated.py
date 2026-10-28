#!/usr/bin/env python3
"""Whole Level21 natural-minor source fields, without canonical allocation."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import parallel10_level021_minor_candidate as p10

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = p10.BUILD_REL / "candidate-02.json"
RESULT = Path("Results/parallel-10/exercises/conversion/20260923T150000Z-2.3.1.1.1-level021-whole-minor-r01-results.md")
PACKAGE = Path("Content/controls/curriculum-v1/package.json")
REGISTRY = Path("Content/controls/curriculum-v1/identity-registry.json")
OUT = Path("Build/parallel-12/level021-schema1-unallocated-r01")
PINS = {
    CANDIDATE: (42349, "980300d90260fe7c3df030426eaed27ca42a51baf18eeb4f31d14a83fd46bf5d"),
    RESULT: (None, "59f0cfc860f0da928cf420fedda4de2d326fe89523e68cc35a3fc18622bc41fc"),
    p10.TXT_REL: (14003, p10.TXT_SHA),
    p10.PDF_REL: (18814, p10.PDF_SHA),
    PACKAGE: (None, "766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255"),
    REGISTRY: (None, "5d265859e1e8a5a530a0e53d88b019a1c920f3bba6cccb4ef0fef2f7640007e5"),
}
FIELDS = {"id", "workbook_id", "module_id", "legacy_level", "title", "kind", "content_revision",
          "status", "runtime_eligible", "source_refs", "authored_text_refs", "normalization", "context",
          "events", "timing", "rubric", "resource_requirements", "ambiguities", "control_scope",
          "variants", "lineage"}
NATURAL = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
GUIDANCE_REFS = ["L21-TXT1-1-43", "L21-TXT1-226-232", "L21-PDF1-p1", "L21-PDF1-p2"]


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
        need((length is None or len(raw) == length) and sha(raw) == digest, f"INPUT_DRIFT {path}")


def pitch_class(spelling: str) -> int:
    need(re.fullmatch(r"[A-G](?:#|b)?", spelling) is not None, "SPELLING_SHAPE")
    return (NATURAL[spelling[0]] + (1 if spelling.endswith("#") else -1 if spelling.endswith("b") else 0)) % 12


def txt_span(ref: str, lines: list[str]) -> dict:
    match = re.fullmatch(r"L21-TXT1-(\d+)-(\d+)", ref)
    need(match is not None, "TXT_REF")
    first, last = map(int, match.groups())
    need(1 <= first <= last <= len(lines), "TXT_SPAN")
    return {"ref": ref, "first_line": first, "last_line": last,
            "text_sha256": sha("\n".join(lines[first - 1:last]).encode())}


def source_event(note: dict, key: str) -> dict:
    string = p10.STRINGS.index(note["string"]) + 1
    midi = p10.TUNING[note["string"]] + note["fret"]
    degree = note["degree"]
    need(midi == note["midi"] and midi % 12 == pitch_class(note["source_tone"]) and
         degree in p10.DEGREES and 1 <= note["finger"] <= 4, "NOTE_PITCH_OR_DEGREE")
    return {"event_id": None, "kind": "note", "string": string, "fret": note["fret"],
            "midi": midi, "spelling": note["source_tone"],
            "degree_contexts": {f"{key}-natural-minor": {"source_label": degree,
                                                          "ordinal": int(degree.removeprefix("b")),
                                                          "alteration": -1 if degree.startswith("b") else 0}},
            "finger": note["finger"], "onset_q": None, "duration_q": None,
            "attack": "picked", "tie_from": None}


def build(root: Path = ROOT, candidate_override: dict | None = None) -> tuple[dict, dict]:
    pin(root)
    candidate = candidate_override if candidate_override is not None else json.loads((root / CANDIDATE).read_text())
    need(candidate == p10.build_candidate(root), "P10_SOURCE_CANDIDATE_DRIFT")
    need(candidate["level"] == 21 and len(candidate["rungs"]) == 13 and
         all(candidate[k] is False for k in ("canonical_identity_assigned", "runtime_import_authorized",
                                              "curriculum_reviewed", "timing_interpreted")), "SOURCE_SCOPE")
    foundation = json.loads((root / PACKAGE).read_text())
    registry = json.loads((root / REGISTRY).read_text())
    current = [r for r in foundation["records"] if r.get("legacy_level") == 21]
    identities = [e for e in registry["entities"] if e.get("id") == "fg:workbook:000021" or
                  e.get("parent") == "fg:workbook:000021"]
    need(len(foundation["records"]) == 659 and not current and not identities, "CURRENT659_LEVEL21_OVERLAP")
    lines = (root / p10.TXT_REL).read_text().splitlines()
    need(lines[32].startswith("UP:") and lines[33].startswith("DOWN:"), "PRINTED_ROUTE")
    records, source_map = [], []
    for index, rung in enumerate(candidate["rungs"], 1):
        key, local = p10.KEYS[index - 1], f"L21-rung{index:02d}"
        root_fret, start = index + 4, 45 + (index - 1) * 14
        txt_ref = f"L21-TXT1-{start}-{start + 11}"
        pdf_ref = f"L21-PDF1-p{3 + (index - 1) // 4}"
        need(rung["rung"] == index and rung["key"] == key and
             rung["low_e_root_fret"] == root_fret and rung["frame_frets"] == [root_fret, root_fret + 3] and
             rung["txt_header_line"] == start and rung["pdf_page"] == 3 + (index - 1) // 4 and
             rung["scale_tones"] == list(p10.TONES[index - 1]) + [key] and
             rung["cell_note_count"] == len(rung["notes"]) == 16 and
             all(rung[k] is None for k in ("canonical_item_id", "fixed_bpm", "note_per_click", "onset", "duration")) and
             rung["runtime_eligible"] is rung["admitted"] is False, "RUNG_SCOPE")
        span = txt_span(txt_ref, lines)
        need(lines[start - 1].startswith(f"RUNG {index:02d} OF 13") and
             lines[start + 10].startswith("Finish on the low root") and
             rung["txt_rows"]["Deg"] == lines[start + 2] and
             rung["txt_rows"]["Fng"] == lines[start + 3], "TXT_CARD")
        for offset, string in enumerate(("e", "B", "G", "D", "A", "E"), 5):
            need(rung["txt_rows"][string] == lines[start + offset - 1], "PRINTED_TAB")
        refs = [txt_ref, pdf_ref, *GUIDANCE_REFS]
        events = []
        for ordinal, note in enumerate(rung["notes"], 1):
            expected_position = ordinal if ordinal <= 8 else 17 - ordinal
            need(note["index"] == ordinal and note["degree"] == p10.DEGREES[expected_position - 1] and
                 note["phase"] == ("ascend" if ordinal <= 8 else "descend") and
                 note["repeated_octave_root_at_turn"] == (ordinal in (8, 9)), "NOTE_ORDER")
            events.append(source_event(note, key))
        need((events[7]["string"], events[7]["fret"], events[7]["midi"]) ==
             (events[8]["string"], events[8]["fret"], events[8]["midi"]), "HIGH_ROOT_TURN")
        variants, memberships = [], []
        for pick in ("D", "U"):
            label = f"minor-one-octave-{pick}-start"
            variants.append({"id": None, "label": label, "event_ids": None,
                             "source_refs": refs, "route": "one_octave_16_contact_high_root_repeated",
                             "pick_start": pick, "pick_start_origin": "source_authored",
                             "role": "notation_practice", "accent_policy": "source_unspecified",
                             "grouping": {"kind": "unresolved", "notes_per_beat": None,
                                          "beat_unit_q": None, "marking_factor": [1, 1],
                                          "source_label": "even eighth notes; optional one-beat pause after cell"},
                             "tail_pause": None,
                             "unresolved": ["Absolute BPM, quarter-note grid and optional pause binding unassigned."]})
            memberships.append({"label": label, "event_local_ordinals": list(range(1, 17)),
                                "repeated_high_root_ordinals": [8, 9]})
        fields = {"id": None, "workbook_id": None, "module_id": None, "legacy_level": 21,
                  "title": f"Rung {index:02d}: {key} natural minor one-octave neck cell",
                  "kind": "notation", "content_revision": None, "status": "converted_candidate",
                  "runtime_eligible": False, "source_refs": refs, "authored_text_refs": refs,
                  "normalization": [{"kind": "representation_metadata", "basis": "P10 whole-Level21 candidate and original TXT/PDF",
                                     "text": "One 16-contact natural-minor up/down cell repeats the octave root at the turn; the full hand frame moves one fret only after the cell."}],
                  "context": {"local_code": local,
                              "route": "UP rungs01-13; printed DOWN landmarks13-01; continuous return12-01",
                              "position": f"low-E root fret {root_fret}; frame {root_fret}-{root_fret + 3}",
                              "pick_start": "D or U; alternate through turn and one-fret relocations",
                              "pick_start_variants": ["D", "U"], "pick_continues_at_turn": True,
                              "tuning_open_midi": [40, 45, 50, 55, 59, 64], "capo": 0,
                              "source_contact_count": 16,
                              "scale_formula": ["1", "2", "b3", "4", "5", "b6", "b7", "8"],
                              "shift_after_complete_cell_only": True},
                  "events": events,
                  "timing": {"status": "unresolved", "unit": "quarter",
                             "basis": "Source even-eighth and relative BPM instructions do not allocate an absolute quarter-note event grid or pause binding",
                             "source_pulse": "even eighth notes", "selected_pulse": None},
                  "rubric": None, "resource_requirements": [],
                  "ambiguities": ["Quarter-note onsets/durations, note-per-click and absolute BPM are unassigned.",
                                  "Optional one-beat inter-cell pause has no selected beat-unit/pass binding."],
                  "control_scope": {"local_case": f"Level21 rung{index:02d} {key} natural-minor full 16-contact cell",
                                    "extent": "complete_selected_case", "whole_workbook_complete": False,
                                    "source_event_count": 16, "basis_refs": refs,
                                    "unresolved": ["Identity, lineage and route-level admission pending."]},
                  "variants": variants, "lineage": None}
        need(set(fields) == FIELDS, "FIELD_SHAPE")
        records.append({"source_local_key": local, "rung_number": index, "key": key,
                        "root_fret": root_fret, "frame": [root_fret, root_fret + 3],
                        "schema1_fields": fields, "variant_memberships": memberships,
                        "source_printed_rows": rung["txt_rows"],
                        "source_note_details": rung["notes"],
                        "identity_state": "unallocated", "schema1_importable": False,
                        "open_gaps": ["canonical identities and lineage", "quarter-note timing and pause binding",
                                      "runtime/Curriculum admission"]})
        source_map.append({"source_local_key": local, "rung_number": index, "key": key,
                           "root_fret": root_fret, "frame": [root_fret, root_fret + 3],
                           "txt": span, "pdf_card": pdf_ref, "pdf_route_map": "L21-PDF1-p2"})
    up = [f"L21-rung{i:02d}" for i in range(1, 14)]
    down_landmarks = list(reversed(up))
    down_return = down_landmarks[1:]
    route = candidate["ladder"]
    need(route["up_rungs"] == list(range(1, 14)) and route["down_rungs"] == list(range(12, 0, -1)) and
         route["round_trip_cells"] == 25 and route["round_trip_note_contacts"] == 400, "ROUTE_SOURCE")
    counts = {"records": 13, "events": 208, "variants": 26,
              "up_landmark_cells": 13, "down_landmark_cells": 13,
              "down_return_cells": 12, "continuous_round_trip_cells": 25,
              "round_trip_contact_traversals": 400}
    proposal = {"proposal_version": "parallel12-level021-unallocated-schema1-fields.1",
                "classification": "source_mapped_field_proposal_not_schema1_importable",
                "legacy_level": 21,
                "source_pins": {str(path): {"bytes": (root / path).stat().st_size, "sha256": digest}
                                for path, (_, digest) in PINS.items()},
                "counts": counts, "source_guidance": candidate["guidance_only"],
                "source_exceptions": candidate["exceptions"],
                "source_printed_route": {"up": lines[32], "down": lines[33]},
                "current659_level21_records": 0, "current659_level21_workbook_identity": False,
                "representative_collision": None,
                "canonical_ids_allocated": False, "runtime_eligible": False, "admitted": False,
                "fixed_bpm": None, "note_per_click": None, "onset_q": None, "duration_q": None,
                "records": records}
    handoff = {"version": "parallel12-level021-allocation-handoff.1",
               "status": "pending_P02_serial_floor_and_allocation_authority",
               "proposal_sha256": sha(encode(proposal)), "source_map": source_map,
               "guidance_refs": GUIDANCE_REFS,
               "routes": {"up_landmarks": up, "down_landmarks": down_landmarks,
                          "down_return": down_return, "continuous_round_trip": up + down_return,
                          "turn_after_rung": "L21-rung13", "shift_frets_up": 1, "shift_frets_down": -1},
               "record_count": 13, "event_count": 208, "variant_count": 26,
               "current659_level21_records": 0, "current659_level21_workbook_identity": False,
               "representative_collision": None,
               "decisions_required": ["P02 serial floor, workbook/module/item/variant identity and source-key bridge",
                                      "Curriculum review of minor spelling, repeated octave root and 25-cell route",
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
    counts = {"records": 13, "events": 208, "variants": 26,
              "up_landmark_cells": 13, "down_landmark_cells": 13,
              "down_return_cells": 12, "continuous_round_trip_cells": 25,
              "round_trip_contact_traversals": 400}
    need(proposal["counts"] == counts and
         (handoff["record_count"], handoff["event_count"], handoff["variant_count"]) == (13, 208, 26), "COVERAGE")
    keys = [f"L21-rung{i:02d}" for i in range(1, 14)]
    need([r["source_local_key"] for r in proposal["records"]] == keys and
         [r["source_local_key"] for r in handoff["source_map"]] == keys and
         handoff["routes"]["up_landmarks"] == keys and
         handoff["routes"]["down_landmarks"] == list(reversed(keys)) and
         handoff["routes"]["down_return"] == list(reversed(keys))[1:] and
         handoff["routes"]["continuous_round_trip"] == keys + list(reversed(keys))[1:] and
         handoff["routes"]["turn_after_rung"] == "L21-rung13", "ROUTE_OR_CASE_ORDER")
    for index, record in enumerate(proposal["records"], 1):
        fields = record["schema1_fields"]
        need(record["rung_number"] == index and record["key"] == p10.KEYS[index - 1] and
             record["root_fret"] == index + 4 and record["frame"] == [index + 4, index + 7] and
             record["identity_state"] == "unallocated" and record["schema1_importable"] is False and
             set(fields) == FIELDS and fields["legacy_level"] == 21 and
             fields["context"]["local_code"] == record["source_local_key"] and
             all(fields[k] is None for k in ("id", "workbook_id", "module_id", "content_revision", "lineage")) and
             fields["runtime_eligible"] is False and fields["timing"]["status"] == "unresolved" and
             fields["timing"]["selected_pulse"] is None, "INVALID_AUTHORITY")
        need(len(fields["events"]) == 16 and len(fields["variants"]) == len(record["variant_memberships"]) == 2,
             "CELL_COUNT")
        for ordinal, event in enumerate(fields["events"], 1):
            source = record["source_note_details"][ordinal - 1]
            degree = source["degree"]
            need(event["event_id"] is event["onset_q"] is event["duration_q"] is None and
                 event["kind"] == "note" and
                 (event["string"], event["fret"], event["midi"], event["spelling"], event["finger"]) ==
                 (p10.STRINGS.index(source["string"]) + 1, source["fret"], source["midi"],
                  source["source_tone"], source["finger"]) and
                 event["degree_contexts"] == {f"{record['key']}-natural-minor": {
                     "source_label": degree, "ordinal": int(degree.removeprefix("b")),
                     "alteration": -1 if degree.startswith("b") else 0}},
                 "UNSUPPORTED_TIMING_OR_NOTE")
        need((fields["events"][7]["string"], fields["events"][7]["fret"], fields["events"][7]["midi"]) ==
             (fields["events"][8]["string"], fields["events"][8]["fret"], fields["events"][8]["midi"]),
             "TURN_ROOT")
        need([v["pick_start"] for v in fields["variants"]] == ["D", "U"] and
             all(v["id"] is v["event_ids"] is None and v["grouping"]["kind"] == "unresolved" and
                 v["grouping"]["beat_unit_q"] is None for v in fields["variants"]) and
             all(m["event_local_ordinals"] == list(range(1, 17)) and
                 m["repeated_high_root_ordinals"] == [8, 9] for m in record["variant_memberships"]),
             "VARIANT_MEMBERSHIP")
    need(handoff["proposal_sha256"] == sha(encode(proposal)) and
         proposal["current659_level21_records"] == handoff["current659_level21_records"] == 0 and
         proposal["current659_level21_workbook_identity"] is handoff["current659_level21_workbook_identity"] is False and
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
    print(json.dumps({"status": "unallocated_level021_pending_P02_serial_floor",
                      "counts": verify(proposal, handoff)}, sort_keys=True))


if __name__ == "__main__":
    main()
