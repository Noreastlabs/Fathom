#!/usr/bin/env python3
"""Whole Level22 natural-minor two-octave source fields without allocation."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import parallel_12_level022_whole_ladder as source

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = source.OUTPUT_ROOT / "candidate-02.json"
RESULT = Path("Results/parallel-12/conversion/20260923T150132Z-level022-whole-ladder-r01-results.md")
PACKAGE = Path("Content/controls/curriculum-v1/package.json")
REGISTRY = Path("Content/controls/curriculum-v1/identity-registry.json")
OUT = Path("Build/parallel-12/level022-schema1-unallocated-r01")
PINS = {
    CANDIDATE: (89655, "a1f1579d82fc469486960991fe708e8ba34e6cc4267f0281748ccb9a09f5a41d"),
    RESULT: (None, "9712ac7cfcafc27b60b95db8360dc46c45fd38e7891a892e8033b3ac43c84023"),
    source.TXT: source.TXT_PIN,
    source.PDF: source.PDF_PIN,
    PACKAGE: (None, "766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255"),
    REGISTRY: (None, "5d265859e1e8a5a530a0e53d88b019a1c920f3bba6cccb4ef0fef2f7640007e5"),
}
FIELDS = {"id", "workbook_id", "module_id", "legacy_level", "title", "kind", "content_revision",
          "status", "runtime_eligible", "source_refs", "authored_text_refs", "normalization", "context",
          "events", "timing", "rubric", "resource_requirements", "ambiguities", "control_scope",
          "variants", "lineage"}
OPEN = {"E": (1, 40), "A": (2, 45), "D": (3, 50), "G": (4, 55), "B": (5, 59), "e": (6, 64)}
GUIDANCE_REFS = ["L22-TXT1-1-52", "L22-TXT1-242-244", "L22-PDF1-p1", "L22-PDF1-p2"]


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


def txt_span(ref: str, lines: list[str]) -> dict:
    match = re.fullmatch(r"L22-TXT1-(\d+)-(\d+)", ref)
    need(match is not None, "TXT_REF")
    first, last = map(int, match.groups())
    need(1 <= first <= last <= len(lines), "TXT_SPAN")
    return {"ref": ref, "first_line": first, "last_line": last,
            "text_sha256": sha("\n".join(lines[first - 1:last]).encode())}


def source_event(note: dict, key: str, scale_position: int) -> dict:
    need(note["onset_q"] is note["duration_q"] is None and
         note["string"] in OPEN and note["degree"] in ("1", "2", "b3", "4", "5", "b6", "b7") and
         1 <= note["finger_digit"] <= 4, "SOURCE_NOTE_SCOPE")
    string, open_midi = OPEN[note["string"]]
    midi = open_midi + note["fret"]
    need(midi % 12 == source.pitch_class(note["pitch_spelling"]), "NOTE_PITCH_SPELLING")
    degree = note["degree"]
    return {"event_id": None, "kind": "note", "string": string, "fret": note["fret"],
            "midi": midi, "spelling": note["pitch_spelling"],
            "degree_contexts": {f"{key}-natural-minor": {"source_label": degree,
                                                          "ordinal": scale_position,
                                                          "alteration": -1 if degree.startswith("b") else 0}},
            "finger": note["finger_digit"], "onset_q": None, "duration_q": None,
            "attack": "picked", "tie_from": None}


def build(root: Path = ROOT, candidate_override: dict | None = None) -> tuple[dict, dict]:
    pin(root)
    candidate = candidate_override if candidate_override is not None else json.loads((root / CANDIDATE).read_text())
    need(candidate == source.build_candidate(root=root), "SOURCE_CANDIDATE_DRIFT")
    need(candidate["level"] == 22 and len(candidate["rungs"]) == 13 and
         candidate["counts"] == {"rungs": 13, "notes_per_cell": 30, "unique_cell_notes": 390,
                                "round_trip_cells": 25, "round_trip_picked_notes": 750} and
         all(candidate[k] is None for k in ("canonical_item_id", "canonical_variant_id", "onset_q",
                                            "duration_q", "fixed_bpm", "note_per_click")) and
         all(candidate[k] is False for k in ("runtime_eligible", "runtime_admitted", "imported",
                                               "admitted", "whole_workbook_complete")), "SOURCE_SCOPE")
    foundation = json.loads((root / PACKAGE).read_text())
    registry = json.loads((root / REGISTRY).read_text())
    current = [r for r in foundation["records"] if r.get("legacy_level") == 22]
    identities = [e for e in registry["entities"] if e.get("id") == "fg:workbook:000022" or
                  e.get("parent") == "fg:workbook:000022"]
    need(len(foundation["records"]) == 659 and not current and not identities, "CURRENT659_LEVEL22_OVERLAP")
    lines = (root / source.TXT).read_text().splitlines()
    need(len(lines) == 264 and lines[42].startswith("UP:") and lines[43].startswith("DOWN:"), "TXT_ROUTE")
    records, source_map = [], []
    for index, rung in enumerate(candidate["rungs"], 1):
        key, root_fret = source.KEYS[index - 1], index + 4
        local, start = f"L22-rung{index:02d}", 55 + (index - 1) * 14
        txt_ref = f"L22-TXT1-{start}-{start + 11}"
        pdf_page = 3 + (index - 1) // 3
        pdf_line = 6 + 14 * ((index - 1) % 3)
        pdf_ref = f"L22-PDF1-p{pdf_page}-L{pdf_line}-{pdf_line + 13}"
        need(rung["source_local_key"] == local and rung["rung"] == index and rung["key"] == key and
             rung["root_string"] == "E" and rung["root_fret"] == root_fret and
             (rung["frame_min_fret"], rung["frame_max_fret"]) == (root_fret - 1, root_fret + 3) and
             rung["source_refs"] == {"txt": txt_ref, "pdf": pdf_ref, "pdf_overview": "L22-PDF1-p2"} and
             len(rung["cell_notes"]) == 30 and
             all(rung[k] is None for k in ("canonical_item_id", "canonical_variant_id", "onset_q",
                                            "duration_q", "fixed_bpm", "note_per_click")) and
             all(rung[k] is False for k in ("runtime_eligible", "runtime_admitted", "imported", "admitted")),
             "RUNG_SCOPE")
        span = txt_span(txt_ref, lines)
        need(lines[start - 1].startswith(f"RUNG {index:02d} OF 13") and
             rung["source_degree_line"] == lines[start + 2] and
             rung["source_finger_line"] == lines[start + 3] and
             rung["source_tab_rows_high_to_low"] == lines[start + 4:start + 10] and
             lines[start + 10].startswith("Finish on the low root"), "TXT_CARD")
        refs = [txt_ref, pdf_ref, "L22-PDF1-p2", *GUIDANCE_REFS]
        events = []
        for ordinal, note in enumerate(rung["cell_notes"], 1):
            position = ordinal if ordinal <= 15 else 31 - ordinal
            need(note["ordinal"] == ordinal and note["direction"] ==
                 ("ascending" if ordinal <= 15 else "descending") and
                 note["degree"] == source.DEGREES_ASC[position - 1] and
                 note["turn_repeat"] == (ordinal == 16) and
                 note["pitch_spelling"] == rung["scale_tones_two_octaves"][position - 1], "NOTE_ORDER")
            events.append(source_event(note, key, position))
        need((events[14]["string"], events[14]["fret"], events[14]["midi"]) ==
             (events[15]["string"], events[15]["fret"], events[15]["midi"]), "HIGH_ROOT_TURN")
        variants, memberships = [], []
        for pick in ("D", "U"):
            label = f"minor-two-octave-{pick}-start"
            variants.append({"id": None, "label": label, "event_ids": None,
                             "source_refs": refs, "route": "two_octave_30_contact_high_root_repeated",
                             "pick_start": pick, "pick_start_origin": "source_authored",
                             "role": "notation_practice", "accent_policy": "source_unspecified",
                             "grouping": {"kind": "unresolved", "notes_per_beat": None,
                                          "beat_unit_q": None, "marking_factor": [1, 1],
                                          "source_label": "even eighth notes; optional one-beat pause after cell"},
                             "tail_pause": None,
                             "unresolved": ["Absolute BPM, quarter-note grid and optional pause binding unassigned."]})
            memberships.append({"label": label, "event_local_ordinals": list(range(1, 31)),
                                "repeated_high_root_ordinals": [15, 16]})
        fields = {"id": None, "workbook_id": None, "module_id": None, "legacy_level": 22,
                  "title": f"Rung {index:02d}: {key} natural minor two-octave neck cell",
                  "kind": "notation", "content_revision": None, "status": "converted_candidate",
                  "runtime_eligible": False, "source_refs": refs, "authored_text_refs": refs,
                  "normalization": [{"kind": "representation_metadata", "basis": "Sealed P12 whole-Level22 source candidate and original TXT/PDF",
                                     "text": "One 30-contact two-octave cell repeats the high root at the turn; the complete moving frame shifts one fret only after the cell. G backreach and B tuning offset retain the printed fingering."}],
                  "context": {"local_code": local,
                              "route": "UP rungs01-13; printed DOWN landmarks13-01; continuous return12-01",
                              "position": f"low-E root fret {root_fret}; moving frame {root_fret - 1}-{root_fret + 3}",
                              "pick_start": "D or U; alternate through turns, string crossings and one-fret relocations",
                              "pick_start_variants": ["D", "U"], "pick_continues_at_turn": True,
                              "tuning_open_midi": [40, 45, 50, 55, 59, 64], "capo": 0,
                              "source_contact_count": 30,
                              "ascending_string_distribution_low_to_high": [3, 3, 2, 3, 3, 1],
                              "shift_after_complete_cell_only": True},
                  "events": events,
                  "timing": {"status": "unresolved", "unit": "quarter",
                             "basis": "Source eighth-note and relative BPM guidance does not allocate an absolute quarter-note event grid or pause binding",
                             "source_pulse": "even eighth notes", "selected_pulse": None},
                  "rubric": None, "resource_requirements": [],
                  "ambiguities": ["Quarter-note onsets/durations, note-per-click and absolute BPM are unassigned.",
                                  "Optional one-beat inter-cell pause has no selected beat-unit/pass binding.",
                                  "Moving frame guidance does not impose a static five-fret stretch."],
                  "control_scope": {"local_case": f"Level22 rung{index:02d} {key} natural-minor full 30-contact cell",
                                    "extent": "complete_selected_case", "whole_workbook_complete": False,
                                    "source_event_count": 30, "basis_refs": refs,
                                    "unresolved": ["Identity, lineage and route-level admission pending."]},
                  "variants": variants, "lineage": None}
        need(set(fields) == FIELDS, "FIELD_SHAPE")
        records.append({"source_local_key": local, "rung_number": index, "key": key,
                        "root_fret": root_fret, "frame": [root_fret - 1, root_fret + 3],
                        "schema1_fields": fields, "variant_memberships": memberships,
                        "source_printed_rows": {"Deg": rung["source_degree_line"],
                                                "Fng": rung["source_finger_line"],
                                                "TAB_high_to_low": rung["source_tab_rows_high_to_low"]},
                        "source_note_details": rung["cell_notes"],
                        "identity_state": "unallocated", "schema1_importable": False,
                        "open_gaps": ["canonical identities and lineage", "quarter-note timing and pause binding",
                                      "runtime/Curriculum admission"]})
        source_map.append({"source_local_key": local, "rung_number": index, "key": key,
                           "root_fret": root_fret, "frame": [root_fret - 1, root_fret + 3],
                           "txt": span, "pdf_card": pdf_ref, "pdf_route_map": "L22-PDF1-p2"})
    up = [f"L22-rung{i:02d}" for i in range(1, 14)]
    down_landmarks = list(reversed(up))
    down_return = down_landmarks[1:]
    route = candidate["full_round_trip_route"]
    need(len(route) == 25 and [c["rung"] for c in route] == list(range(1, 14)) + list(range(12, 0, -1)) and
         all(c["cell_note_count"] == 30 for c in route), "ROUTE_SOURCE")
    counts = {"records": 13, "events": 390, "variants": 26,
              "up_landmark_cells": 13, "down_landmark_cells": 13,
              "down_return_cells": 12, "continuous_round_trip_cells": 25,
              "round_trip_contact_traversals": 750}
    proposal = {"proposal_version": "parallel12-level022-unallocated-schema1-fields.1",
                "classification": "source_mapped_field_proposal_not_schema1_importable",
                "legacy_level": 22,
                "source_pins": {str(path): {"bytes": (root / path).stat().st_size, "sha256": digest}
                                for path, (_, digest) in PINS.items()},
                "counts": counts, "source_guidance": candidate["source_guidance"],
                "source_exceptions": candidate["exceptions"],
                "source_printed_route": {"up": lines[42], "down": lines[43]},
                "current659_level22_records": 0, "current659_level22_workbook_identity": False,
                "representative_collision": None,
                "canonical_ids_allocated": False, "runtime_eligible": False, "admitted": False,
                "fixed_bpm": None, "note_per_click": None, "onset_q": None, "duration_q": None,
                "records": records}
    handoff = {"version": "parallel12-level022-allocation-handoff.1",
               "status": "pending_P02_serial_floor_and_allocation_authority",
               "proposal_sha256": sha(encode(proposal)), "source_map": source_map,
               "guidance_refs": GUIDANCE_REFS,
               "routes": {"up_landmarks": up, "down_landmarks": down_landmarks,
                          "down_return": down_return, "continuous_round_trip": up + down_return,
                          "turn_after_rung": "L22-rung13", "shift_frets_up": 1, "shift_frets_down": -1},
               "record_count": 13, "event_count": 390, "variant_count": 26,
               "current659_level22_records": 0, "current659_level22_workbook_identity": False,
               "representative_collision": None,
               "decisions_required": ["P02 serial floor, workbook/module/item/variant identity and source-key bridge",
                                      "Curriculum review of minor spelling, G/B geometry, repeated root and 25-cell route",
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
    counts = {"records": 13, "events": 390, "variants": 26,
              "up_landmark_cells": 13, "down_landmark_cells": 13,
              "down_return_cells": 12, "continuous_round_trip_cells": 25,
              "round_trip_contact_traversals": 750}
    need(proposal["counts"] == counts and
         (handoff["record_count"], handoff["event_count"], handoff["variant_count"]) == (13, 390, 26), "COVERAGE")
    keys = [f"L22-rung{i:02d}" for i in range(1, 14)]
    need([r["source_local_key"] for r in proposal["records"]] == keys and
         [r["source_local_key"] for r in handoff["source_map"]] == keys and
         handoff["routes"]["up_landmarks"] == keys and
         handoff["routes"]["down_landmarks"] == list(reversed(keys)) and
         handoff["routes"]["down_return"] == list(reversed(keys))[1:] and
         handoff["routes"]["continuous_round_trip"] == keys + list(reversed(keys))[1:] and
         handoff["routes"]["turn_after_rung"] == "L22-rung13", "ROUTE_OR_CASE_ORDER")
    for index, record in enumerate(proposal["records"], 1):
        fields = record["schema1_fields"]
        need(record["rung_number"] == index and record["key"] == source.KEYS[index - 1] and
             record["root_fret"] == index + 4 and record["frame"] == [index + 3, index + 7] and
             record["identity_state"] == "unallocated" and record["schema1_importable"] is False and
             set(fields) == FIELDS and fields["legacy_level"] == 22 and
             fields["context"]["local_code"] == record["source_local_key"] and
             all(fields[k] is None for k in ("id", "workbook_id", "module_id", "content_revision", "lineage")) and
             fields["runtime_eligible"] is False and fields["timing"]["status"] == "unresolved" and
             fields["timing"]["selected_pulse"] is None, "INVALID_AUTHORITY")
        need(len(fields["events"]) == 30 and len(fields["variants"]) == len(record["variant_memberships"]) == 2,
             "CELL_COUNT")
        for ordinal, event in enumerate(fields["events"], 1):
            note = record["source_note_details"][ordinal - 1]
            position = ordinal if ordinal <= 15 else 31 - ordinal
            degree = note["degree"]
            need(event["event_id"] is event["onset_q"] is event["duration_q"] is None and
                 event["kind"] == "note" and
                 (event["string"], event["fret"], event["midi"], event["spelling"], event["finger"]) ==
                 (OPEN[note["string"]][0], note["fret"], OPEN[note["string"]][1] + note["fret"],
                  note["pitch_spelling"], note["finger_digit"]) and
                 event["degree_contexts"] == {f"{record['key']}-natural-minor": {
                     "source_label": degree, "ordinal": position,
                     "alteration": -1 if degree.startswith("b") else 0}},
                 "UNSUPPORTED_TIMING_OR_NOTE")
        need((fields["events"][14]["string"], fields["events"][14]["fret"], fields["events"][14]["midi"]) ==
             (fields["events"][15]["string"], fields["events"][15]["fret"], fields["events"][15]["midi"]),
             "TURN_ROOT")
        need([v["pick_start"] for v in fields["variants"]] == ["D", "U"] and
             all(v["id"] is v["event_ids"] is None and v["grouping"]["kind"] == "unresolved" and
                 v["grouping"]["beat_unit_q"] is None for v in fields["variants"]) and
             all(m["event_local_ordinals"] == list(range(1, 31)) and
                 m["repeated_high_root_ordinals"] == [15, 16] for m in record["variant_memberships"]),
             "VARIANT_MEMBERSHIP")
    need(handoff["proposal_sha256"] == sha(encode(proposal)) and
         proposal["current659_level22_records"] == handoff["current659_level22_records"] == 0 and
         proposal["current659_level22_workbook_identity"] is handoff["current659_level22_workbook_identity"] is False and
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
    print(json.dumps({"status": "unallocated_level022_pending_P02_serial_floor",
                      "counts": verify(proposal, handoff)}, sort_keys=True))


if __name__ == "__main__":
    main()
