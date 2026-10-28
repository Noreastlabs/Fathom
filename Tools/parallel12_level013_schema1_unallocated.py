#!/usr/bin/env python3
"""Build and verify a detached whole-Level13 schema1 field proposal."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import parallel10_level013_ladder_candidate as p10

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = Path("Build/parallel-10/2.3.1.1.1-level013-whole-ladder-r01/candidate-02.json")
RESULT = Path("Results/parallel-10/exercises/conversion/20260923T144500Z-2.3.1.1.1-level013-whole-ladder-r01-results.md")
PACKAGE = Path("Content/controls/curriculum-v1/package.json")
REGISTRY = Path("Content/controls/curriculum-v1/identity-registry.json")
OUT = Path("Build/parallel-12/level013-schema1-unallocated-r01")
PINS = {
    CANDIDATE: (72031, "eb3f51993f59803ce3d1df5305e5c7140fc6dadcdc8e1994a77c162420bb531e"),
    RESULT: (None, "15f964189ad450043bf960c4bdc6cc82078074904c2d06feb645b94c4f93255e"),
    p10.TXT_REL: (20305, p10.TXT_SHA),
    p10.PDF_REL: (20852, p10.PDF_SHA),
    PACKAGE: (None, "766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255"),
    REGISTRY: (None, "5d265859e1e8a5a530a0e53d88b019a1c920f3bba6cccb4ef0fef2f7640007e5"),
}
FIELDS = {"id", "workbook_id", "module_id", "legacy_level", "title", "kind", "content_revision",
          "status", "runtime_eligible", "source_refs", "authored_text_refs", "normalization", "context",
          "events", "timing", "rubric", "resource_requirements", "ambiguities", "control_scope",
          "variants", "lineage"}
PITCH_CLASS = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


class ProposalError(ValueError):
    pass


def need(ok: bool, code: str) -> None:
    if not ok:
        raise ProposalError(code)


def encode(obj: object) -> bytes:
    return (json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n").encode()


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def pin(root: Path = ROOT) -> None:
    need(root.resolve() == ROOT.resolve(), "ROOT_DRIFT")
    for path, (length, expected) in PINS.items():
        raw = (root / path).read_bytes()
        need(length is None or len(raw) == length, f"INPUT_LENGTH_DRIFT {path}")
        need(sha(raw) == expected, f"INPUT_HASH_DRIFT {path}")


def pitch_class(spelling: str) -> int:
    need(re.fullmatch(r"[A-G](?:#|b)?", spelling) is not None, "SPELLING_SHAPE")
    return (PITCH_CLASS[spelling[0]] + (1 if spelling.endswith("#") else -1 if spelling.endswith("b") else 0)) % 12


def build(root: Path = ROOT, candidate_override: dict | None = None) -> tuple[dict, dict]:
    pin(root)
    candidate = candidate_override if candidate_override is not None else json.loads((root / CANDIDATE).read_text())
    need(candidate == p10.build_candidate(root), "P10_SOURCE_CANDIDATE_DRIFT")
    need(candidate["level"] == 13 and len(candidate["rungs"]) == 13 and not candidate["exceptions"] and
         all(candidate[k] is False for k in ("canonical_identity_assigned", "runtime_import_authorized",
                                              "curriculum_reviewed", "timing_interpreted")), "SOURCE_SCOPE")
    foundation = json.loads((root / PACKAGE).read_text())
    registry = json.loads((root / REGISTRY).read_text())
    need(len(foundation["records"]) == 659 and
         not any(r["legacy_level"] == 13 for r in foundation["records"]) and
         not any(e["id"] == "fg:workbook:000013" or e.get("parent") == "fg:workbook:000013"
                 for e in registry["entities"]), "CURRENT659_LEVEL13_OVERLAP")
    lines = (root / p10.TXT_REL).read_text().splitlines()
    records, source_map = [], []
    for index, rung in enumerate(candidate["rungs"], 1):
        key = f"L13-rung{index:02d}"
        root_fret = index + 4
        need(rung["rung"] == index and rung["key"] == p10.KEYS[index - 1] and
             rung["low_e_root_fret"] == root_fret and
             rung["frame_frets"] == [root_fret - 1, root_fret + 2] and
             rung["txt_header_line"] == 52 + (index - 1) * 14 and
             rung["cell_note_count"] == len(rung["notes"]) == 30 and
             all(rung[k] is None for k in ("canonical_item_id", "fixed_bpm", "note_per_click", "onset", "duration")) and
             rung["runtime_eligible"] is rung["admitted"] is False, "RUNG_SCOPE")
        start = rung["txt_header_line"]
        block = lines[start - 1:start + 11]
        need(len(block) == 12 and block[0].startswith(f"RUNG {index:02d} OF 13") and
             all(row in block for row in rung["txt_rows"].values()), "TXT_CARD_SPAN")
        txt_ref = f"L13-TXT1-{start}-{start + 11}"
        pdf_ref = f"L13-PDF1-p{rung['pdf_page']}"
        refs = [txt_ref, pdf_ref, "L13-TXT1-30-49", "L13-PDF1-p2", "L13-TXT1-234-239"]
        events = []
        for ordinal, note in enumerate(rung["notes"], 1):
            need(note["index"] == ordinal and note["phase"] == ("ascend" if ordinal <= 15 else "descend") and
                 note["repeated_high_root_at_turn"] is (ordinal in (15, 16)) and
                 note["degree"] == (p10.ASC_DEGREES[ordinal - 1] if ordinal <= 15 else p10.ASC_DEGREES[30 - ordinal]) and
                 note["finger"] == p10.FINGERS[ordinal - 1] and
                 note["midi"] == p10.TUNING_MIDI[note["string"]] + note["fret"] and
                 pitch_class(note["source_tone"]) == note["midi"] % 12, "NOTE_SOURCE")
            events.append({"event_id": None, "kind": "note", "string": p10.STRINGS.index(note["string"]) + 1,
                           "fret": note["fret"], "midi": note["midi"], "spelling": note["source_tone"],
                           "degree_contexts": {f"{rung['key']}-major": {
                               "source_label": str(note["degree"]), "ordinal": note["degree"], "alteration": 0}},
                           "finger": note["finger"], "onset_q": None, "duration_q": None,
                           "attack": "picked", "tie_from": None})
        need(events[14]["midi"] == events[15]["midi"] and
             events[14]["string"] == events[15]["string"] and
             events[14]["fret"] == events[15]["fret"], "TURN_ROOT")
        variants, membership = [], []
        for pick in ("D", "U"):
            label = f"cell-{pick}-start"
            variants.append({"id": None, "label": label, "event_ids": None, "source_refs": refs,
                             "route": "two_octave_up_down_repeated_high_root", "pick_start": pick,
                             "pick_start_origin": "learner_configuration", "role": "notation_practice",
                             "accent_policy": "source_unspecified",
                             "grouping": {"kind": "unresolved", "notes_per_beat": None,
                                          "beat_unit_q": None, "marking_factor": [1, 1],
                                          "source_label": "Even eighths and optional one-beat pause lack a selected quarter-note grid"},
                             "tail_pause": None,
                             "unresolved": ["One practice beat after each cell has no selected beat unit or pass binding."]})
            membership.append({"label": label, "event_local_ordinals": list(range(1, 31)),
                               "repeated_high_root_ordinals": [15, 16]})
        fields = {"id": None, "workbook_id": None, "module_id": None, "legacy_level": 13,
                  "title": f"Rung {index:02d}: {rung['key']} major two-octave six-string ladder cell",
                  "kind": "notation", "content_revision": None, "status": "converted_candidate",
                  "runtime_eligible": False, "source_refs": refs, "authored_text_refs": refs,
                  "normalization": [{"kind": "representation_metadata", "basis": "P10 whole-Level13 candidate and original TXT/PDF",
                                     "text": "One 30-contact major-scale cell repeats the high root at the turn. A at frets 5 and 17 are distinct source positions."}],
                  "context": {"local_code": key,
                              "route": "UP rungs01-13; DOWN rungs13-01; continuous round trip rungs01-13 then12-01",
                              "position": f"low-E root fret {root_fret}; frame {root_fret - 1}-{root_fret + 2}",
                              "pick_start": "D or U selected by learner; strict alternate picking continues across cells",
                              "pick_start_variants": ["D", "U"], "pick_continues_at_turn": True,
                              "tuning_open_midi": [40, 45, 50, 55, 59, 64], "capo": 0},
                  "events": events,
                  "timing": {"status": "unresolved", "unit": "quarter",
                             "basis": "Printed TAB and relative practice BPM do not allocate quarter-note onsets or durations; the optional one-beat pause has no beat-unit binding",
                             "other_source_requirements": candidate["guidance_only"]["practice_rule"]},
                  "rubric": None, "resource_requirements": [],
                  "ambiguities": ["Absolute BPM, quarter-note onset/duration and beat mapping are unprovided.",
                                  "Optional inter-cell pause has an unbound beat unit."],
                  "control_scope": {"local_case": f"Level13 rung{index:02d} {rung['key']} major full 30-contact cell",
                                    "extent": "complete_selected_case", "whole_workbook_complete": False,
                                    "source_event_count": 30, "basis_refs": refs,
                                    "unresolved": ["Identity, lineage and route-level admission pending."]},
                  "variants": variants, "lineage": None}
        need(set(fields) == FIELDS, "FIELD_SHAPE")
        records.append({"source_local_key": key, "rung_number": index, "key": rung["key"],
                        "root_fret": root_fret, "frame": rung["frame_frets"],
                        "schema1_fields": fields, "variant_memberships": membership,
                        "identity_state": "unallocated", "schema1_importable": False,
                        "open_gaps": ["canonical identities and lineage", "quarter-note timing and beat unit",
                                      "runtime/Curriculum admission"]})
        source_map.append({"source_local_key": key, "rung_number": index, "key": rung["key"],
                           "root_fret": root_fret, "frame": rung["frame_frets"],
                           "txt": txt_ref, "pdf_card": pdf_ref, "pdf_route_table": "L13-PDF1-p2",
                           "txt_passage_sha256": sha("\n".join(block).encode())})
    up = [f"L13-rung{i:02d}" for i in candidate["ladder"]["up_rungs"]]
    continuous_down = [f"L13-rung{i:02d}" for i in candidate["ladder"]["down_rungs"]]
    need(up == [f"L13-rung{i:02d}" for i in range(1, 14)] and
         continuous_down == [f"L13-rung{i:02d}" for i in range(12, 0, -1)] and
         candidate["ladder"]["round_trip_cells"] == 25 and
         candidate["ladder"]["round_trip_note_contacts"] == 750, "ROUTE_SOURCE")
    proposal = {"proposal_version": "parallel12-level013-unallocated-schema1-fields.1",
                "classification": "source_mapped_field_proposal_not_schema1_importable",
                "legacy_level": 13,
                "source_pins": {str(path): {"bytes": (root / path).stat().st_size, "sha256": digest}
                                for path, (_, digest) in PINS.items()},
                "counts": {"records": 13, "events": 390, "variants": 26,
                           "up_route_cells": 13, "continuous_down_cells": 12,
                           "continuous_round_trip_cells": 25, "round_trip_contact_traversals": 750},
                "current659_level13_records": 0, "current659_level13_workbook_identity": False,
                "canonical_ids_allocated": False, "runtime_eligible": False, "admitted": False,
                "fixed_bpm": None, "note_per_click": None, "onset_q": None, "duration_q": None,
                "records": records}
    handoff = {"version": "parallel12-level013-allocation-decision-handoff.1",
               "status": "pending_P02_allocation_authority",
               "proposal_sha256": sha(encode(proposal)), "source_map": source_map,
               "routes": {"up": up, "down": list(reversed(up)),
                          "continuous_round_trip": up + continuous_down,
                          "turn_after_rung": "L13-rung13", "shift_frets_up": 1, "shift_frets_down": -1},
               "record_count": 13, "event_count": 390, "variant_count": 26,
               "current659_level13_records": 0, "current659_level13_workbook_identity": False,
               "decisions_required": ["P02 authorization for canonical workbook/module/item/variant identities and source-key bridge",
                                      "Curriculum review of 30-contact cell, route semantics and picking rules",
                                      "Reviewed timing model and lineage/admission policy before schema1 import"],
               "selected_choice": None, "allocation_allowed": False, "no_admission": True}
    verify(proposal, handoff)
    return proposal, handoff


def verify(proposal: dict, handoff: dict) -> dict:
    need(proposal["canonical_ids_allocated"] is False and proposal["runtime_eligible"] is False and
         proposal["admitted"] is False and handoff["allocation_allowed"] is False and
         handoff["no_admission"] is True and handoff["selected_choice"] is None and
         all(proposal[k] is None for k in ("fixed_bpm", "note_per_click", "onset_q", "duration_q")),
         "INVALID_AUTHORITY")
    counts = {"records": 13, "events": 390, "variants": 26, "up_route_cells": 13,
              "continuous_down_cells": 12, "continuous_round_trip_cells": 25,
              "round_trip_contact_traversals": 750}
    need(proposal["counts"] == counts and (handoff["record_count"], handoff["event_count"],
          handoff["variant_count"]) == (13, 390, 26), "COVERAGE")
    keys = [f"L13-rung{i:02d}" for i in range(1, 14)]
    need([r["source_local_key"] for r in proposal["records"]] == keys and
         [r["source_local_key"] for r in handoff["source_map"]] == keys and
         handoff["routes"]["up"] == keys and
         handoff["routes"]["down"] == list(reversed(keys)) and
         handoff["routes"]["continuous_round_trip"] == keys + list(reversed(keys))[1:] and
         handoff["routes"]["turn_after_rung"] == "L13-rung13", "ROUTE_OR_CASE_ORDER")
    for index, record in enumerate(proposal["records"], 1):
        fields = record["schema1_fields"]
        need(set(fields) == FIELDS and record["schema1_importable"] is False and
             record["identity_state"] == "unallocated" and fields["legacy_level"] == 13 and
             fields["context"]["local_code"] == record["source_local_key"] and
             all(fields[k] is None for k in ("id", "workbook_id", "module_id", "lineage", "content_revision")) and
             fields["runtime_eligible"] is False and fields["timing"]["status"] == "unresolved", "INVALID_AUTHORITY")
        need(record["rung_number"] == index and record["key"] == p10.KEYS[index - 1] and
             record["root_fret"] == index + 4 and record["frame"] == [index + 3, index + 6] and
             len(fields["events"]) == 30 and len(fields["variants"]) == 2, "CELL_COUNT_OR_FRAME")
        for ordinal, event in enumerate(fields["events"], 1):
            need(event["event_id"] is event["onset_q"] is event["duration_q"] is None and
                 event["kind"] == "note" and event["midi"] == [40, 45, 50, 55, 59, 64][event["string"] - 1] + event["fret"] and
                 pitch_class(event["spelling"]) == event["midi"] % 12 and
                 event["finger"] == p10.FINGERS[ordinal - 1], "UNSUPPORTED_TIMING_OR_NOTE")
        need(fields["events"][14]["midi"] == fields["events"][15]["midi"] and
             fields["events"][14]["fret"] == fields["events"][15]["fret"] and
             fields["events"][14]["string"] == fields["events"][15]["string"], "TURN_ROOT")
        need([v["pick_start"] for v in fields["variants"]] == ["D", "U"] and
             all(v["id"] is v["event_ids"] is None and v["grouping"]["kind"] == "unresolved"
                 for v in fields["variants"]) and
             all(m["event_local_ordinals"] == list(range(1, 31)) and
                 m["repeated_high_root_ordinals"] == [15, 16] for m in record["variant_memberships"]),
             "VARIANT_MEMBERSHIP")
    need(handoff["proposal_sha256"] == sha(encode(proposal)) and
         proposal["current659_level13_records"] == handoff["current659_level13_records"] == 0 and
         proposal["current659_level13_workbook_identity"] is handoff["current659_level13_workbook_identity"] is False,
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
    print(json.dumps({"status": "unallocated_level013_pending_P02_allocation", "counts": verify(proposal, handoff)}, sort_keys=True))


if __name__ == "__main__":
    main()
