#!/usr/bin/env python3
"""Whole-Level14 source-linked schema1 fields, deliberately unallocated."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from pypdf import PdfReader

import curriculum_level014_whole_candidate as p09

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = Path("Build/parallel-09/2.3.1.1.1-level014-whole-r01/candidate-02.json")
RESULT = Path("Results/parallel-09/exercises/conversion/20260923T145145Z-2.3.1.1.1-level014-whole-r01-results.md")
PACKAGE = Path("Content/controls/curriculum-v1/package.json")
REGISTRY = Path("Content/controls/curriculum-v1/identity-registry.json")
OUT = Path("Build/parallel-12/level014-schema1-unallocated-r01")
PINS = {
    CANDIDATE: (246913, "76f17ced310675c370d19afb8f07bcedac2ab8527410e27e507820a8c543b3b1"),
    RESULT: (None, "d8703d2e296ccc2b114bbe6bbb8a665012268efb157698e148366596a5c5b150"),
    p09.TXT_REL: (p09.TXT_BYTES, p09.TXT_SHA256),
    p09.PDF_REL: (p09.PDF_BYTES, p09.PDF_SHA256),
    PACKAGE: (None, "766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255"),
    REGISTRY: (None, "5d265859e1e8a5a530a0e53d88b019a1c920f3bba6cccb4ef0fef2f7640007e5"),
}
FIELDS = {"id", "workbook_id", "module_id", "legacy_level", "title", "kind", "content_revision",
          "status", "runtime_eligible", "source_refs", "authored_text_refs", "normalization", "context",
          "events", "timing", "rubric", "resource_requirements", "ambiguities", "control_scope",
          "variants", "lineage"}
OPEN_MIDI = {"E": (1, 40), "A": (2, 45), "D": (3, 50),
             "G": (4, 55), "B": (5, 59), "e": (6, 64)}
PITCH_CLASS = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
GUIDANCE_KEYS = ("purpose_ref", "interpretation_ref", "shape_ref", "sequence_ref",
                 "cell_picking_ref", "neck_route_ref", "practice_ref", "round_trip_ref",
                 "clean_standard_ref")


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
    match = re.fullmatch(r"L14-TXT1-(\d+)-(\d+)", ref)
    need(match is not None, "TXT_REF")
    first, last = map(int, match.groups())
    need(1 <= first <= last <= len(lines), "TXT_SPAN")
    section = "\n".join(lines[first - 1:last])
    return {"ref": ref, "first_line": first, "last_line": last,
            "text_sha256": sha(section.encode())}


def build(root: Path = ROOT, candidate_override: dict | None = None) -> tuple[dict, dict]:
    pin(root)
    candidate = candidate_override if candidate_override is not None else json.loads((root / CANDIDATE).read_text())
    need(candidate == p09.build_candidate(), "P09_SOURCE_CANDIDATE_DRIFT")
    need(candidate["level"] == 14 and len(candidate["records"]) == 13 and
         candidate["whole_source_batch_structurally_reconciled"] is True and not candidate["exceptions"] and
         all(candidate[k] is False for k in ("admitted", "imported", "runtime_admitted", "runtime_eligible")),
         "SOURCE_SCOPE")
    foundation = json.loads((root / PACKAGE).read_text())
    registry = json.loads((root / REGISTRY).read_text())
    need(len(foundation["records"]) == 659 and
         not any(r["legacy_level"] == 14 for r in foundation["records"]) and
         not any(e["id"] == "fg:workbook:000014" or e.get("parent") == "fg:workbook:000014"
                 for e in registry["entities"]), "CURRENT659_LEVEL14_OVERLAP")
    lines = (root / p09.TXT_REL).read_text().splitlines()
    pdf_pages = [page.extract_text() for page in PdfReader(str(root / p09.PDF_REL)).pages]
    need(len(pdf_pages) == 7, "PDF_COUNT")
    guidance_refs = [candidate["instructions"][key] for key in GUIDANCE_KEYS]
    need(len(guidance_refs) == len(set(guidance_refs)) == 9 and
         all(txt_span(ref, lines)["ref"] == ref for ref in guidance_refs), "GUIDANCE_REFS")
    records, source_map = [], []
    for index, row in enumerate(candidate["records"], 1):
        local_key = f"L14-rung{index:02d}"
        root_fret = index + 4
        need(row["source_local_key"] == local_key and row["rung"] == index and
             row["key"] == p09.KEYS[index - 1] and row["root_string"] == "E" and
             row["root_fret"] == root_fret and row["frame"] == [root_fret - 1, root_fret + 2] and
             len(row["groups"]) == 12 and
             all(row[k] is None for k in ("canonical_item_id", "canonical_variant_id", "onset_q",
                                           "duration_q", "note_per_click", "fixed_bpm")) and
             all(row[k] is False for k in ("admitted", "imported", "runtime_admitted", "runtime_eligible")),
             "RUNG_SCOPE")
        txt = txt_span(row["source_refs"]["txt"], lines)
        need(txt["first_line"] == 56 + (index - 1) * 14 and txt["last_line"] == txt["first_line"] + 11 and
             lines[txt["first_line"] - 1] == row["printed_txt"]["heading"] and
             all(value in lines[txt["first_line"] - 1:txt["last_line"]]
                 for key, value in row["printed_txt"].items() if isinstance(value, str)), "TXT_CARD")
        pdf_ref = row["source_refs"]["pdf_card"]
        match = re.fullmatch(r"L14-PDF1-p([3-7])", pdf_ref)
        need(match is not None and
             row["printed_pdf"]["heading"] in pdf_pages[int(match.group(1)) - 1] and
             row["source_refs"]["pdf_map"] == "L14-PDF1-p2", "PDF_CARD")
        refs = [txt["ref"], pdf_ref, "L14-PDF1-p2", "L14-PDF1-p1", *guidance_refs]
        refs = list(dict.fromkeys(refs))
        events, groups = [], []
        need(row["scale_tones"] == [*p09.SCALE_TONES[index - 1], row["key"]], "SCALE_TONES")
        for group_index, group in enumerate(row["groups"], 1):
            half = "up" if group_index <= 6 else "down"
            expected_degrees = p09.DEGREE_GROUPS[group_index - 1]
            need(group["index"] == group_index and group["half"] == half and
                 len(group["notes"]) == 3, "GROUP_SOURCE")
            ordinals = []
            for slot, note in enumerate(group["notes"], 1):
                ordinal = (group_index - 1) * 3 + slot
                degree = expected_degrees[slot - 1]
                string, fret = p09._expected_place(degree, root_fret)
                spelling = row["scale_tones"][degree - 1]
                need(note == {"ordinal": ordinal, "group": group_index, "slot": slot, "half": half,
                              "degree": degree, "finger_digit": p09.DEGREE_FINGERS[degree - 1],
                              "string": string, "fret": fret,
                              "is_octave_turn_root": ordinal in (18, 19),
                              "onset_q": None, "duration_q": None}, "NOTE_SOURCE")
                string_num, open_midi = OPEN_MIDI[string]
                midi = open_midi + fret
                need(pitch_class(spelling) == midi % 12, "NOTE_PITCH_SPELLING")
                events.append({"event_id": None, "kind": "note", "string": string_num,
                               "fret": fret, "midi": midi, "spelling": spelling,
                               "degree_contexts": {f"{row['key']}-major": {
                                   "source_label": str(degree), "ordinal": degree, "alteration": 0}},
                               "finger": int(note["finger_digit"]), "onset_q": None,
                               "duration_q": None, "attack": "picked", "tie_from": None})
                ordinals.append(ordinal)
            groups.append({"source_group": group_index, "half": half, "event_local_ordinals": ordinals,
                           "source_degrees": list(expected_degrees),
                           "source_beat_relation": "one_three_note_group_per_beat",
                           "beat_unit_q": None})
        need(len(events) == 36 and events[17]["midi"] == events[18]["midi"] and
             events[17]["string"] == events[18]["string"] and
             events[17]["fret"] == events[18]["fret"], "CELL_TURN")
        variants, membership = [], []
        for pick in ("D", "U"):
            label = f"rolling-{pick}-start"
            variants.append({"id": None, "label": label, "event_ids": None, "source_refs": refs,
                             "route": "one_octave_12_rolling_triplets_repeated_octave_root",
                             "pick_start": pick, "pick_start_origin": "learner_configuration",
                             "role": "notation_practice", "accent_policy": "source_unspecified",
                             "grouping": {"kind": "unresolved", "notes_per_beat": 3,
                                          "beat_unit_q": None, "marking_factor": [1, 1],
                                          "source_label": "Eighth-note triplets; one three-note group per authored beat"},
                             "tail_pause": None,
                             "unresolved": ["Absolute BPM, quarter-note beat mapping and optional one-beat inter-cell pause are unbound."]})
            membership.append({"label": label, "event_local_ordinals": list(range(1, 37)),
                               "group_indices": list(range(1, 13)),
                               "repeated_octave_root_ordinals": [18, 19]})
        fields = {"id": None, "workbook_id": None, "module_id": None, "legacy_level": 14,
                  "title": f"Rung {index:02d}: {row['key']} major three-note rolling sequence",
                  "kind": "notation", "content_revision": None, "status": "converted_candidate",
                  "runtime_eligible": False, "source_refs": refs, "authored_text_refs": refs,
                  "normalization": [{"kind": "representation_metadata", "basis": "P09 whole-Level14 candidate and original TXT/PDF",
                                     "text": "One 36-contact cell has twelve overlapping three-note groups and repeats degree 8 at the turn; A at frets 5 and 17 are distinct positions."}],
                  "context": {"local_code": local_key,
                              "route": "UP rungs01-13; DOWN landmarks rungs13-01; continuous trip rungs01-13 then12-01",
                              "position": f"low-E root fret {root_fret}; frame {root_fret - 1}-{root_fret + 2}",
                              "pick_start": "D or U learner choice; strict alternate picking continues across groups, turn and relocation",
                              "pick_start_variants": ["D", "U"], "pick_continues_at_turn": True,
                              "tuning_open_midi": [40, 45, 50, 55, 59, 64], "capo": 0,
                              "source_group_count": 12, "source_notes_per_group": 3},
                  "events": events,
                  "timing": {"status": "unresolved", "unit": "quarter",
                             "basis": "Source specifies eighth-note triplets and one group per beat but not a selected absolute tempo/quarter-note event grid or pause binding",
                             "other_source_requirements": [candidate["instructions"]["practice_text"],
                                                           candidate["instructions"]["cell_picking_text"],
                                                           candidate["instructions"]["sequence_text"]]},
                  "rubric": None, "resource_requirements": [],
                  "ambiguities": ["Quarter-note onset/duration and absolute BPM are unassigned.",
                                  "Optional one-beat inter-cell pause has no selected beat-unit/pass binding."],
                  "control_scope": {"local_case": f"Level14 rung{index:02d} {row['key']} major full 36-contact rolling cell",
                                    "extent": "complete_selected_case", "whole_workbook_complete": False,
                                    "source_event_count": 36, "basis_refs": refs,
                                    "unresolved": ["Identity, lineage and route-level admission pending."]},
                  "variants": variants, "lineage": None}
        need(set(fields) == FIELDS, "FIELD_SHAPE")
        records.append({"source_local_key": local_key, "rung_number": index, "key": row["key"],
                        "root_fret": root_fret, "frame": row["frame"], "schema1_fields": fields,
                        "group_memberships": groups, "variant_memberships": membership,
                        "source_printed_rows": {"deg": row["printed_txt"]["deg_row"],
                                                "fng": row["printed_txt"]["fng_row"],
                                                "tab": row["printed_txt"]["tab_rows"]},
                        "identity_state": "unallocated", "schema1_importable": False,
                        "open_gaps": ["canonical identities and lineage", "quarter-note timing and pause binding",
                                      "runtime/Curriculum admission"]})
        source_map.append({"source_local_key": local_key, "rung_number": index, "key": row["key"],
                           "root_fret": root_fret, "frame": row["frame"],
                           "txt": txt["ref"], "txt_passage_sha256": txt["text_sha256"],
                           "pdf_card": pdf_ref, "pdf_map": "L14-PDF1-p2"})
    up = [f"L14-rung{i:02d}" for i in range(1, 14)]
    down = list(reversed(up))
    trip = up + down[1:]
    route = candidate["neck_route"]
    need([x["rung"] for x in route["ascending_landmarks"]] == list(range(1, 14)) and
         [x["rung"] for x in route["descending_landmarks"]] == list(range(13, 0, -1)) and
         route["single_turn_cell_sequence"] == list(range(1, 14)) + list(range(12, 0, -1)) and
         route["single_turn_cell_count"] == 25 and route["turn_rung_played_once"] == 13 and
         route["up_fret_step"] == 1 and route["down_fret_step"] == -1, "ROUTE_SOURCE")
    proposal = {"proposal_version": "parallel12-level014-unallocated-schema1-fields.1",
                "classification": "source_mapped_field_proposal_not_schema1_importable",
                "legacy_level": 14,
                "source_pins": {str(path): {"bytes": (root / path).stat().st_size, "sha256": digest}
                                for path, (_, digest) in PINS.items()},
                "counts": {"records": 13, "groups": 156, "events": 468, "variants": 26,
                           "up_landmark_cells": 13, "down_landmark_cells": 13,
                           "continuous_round_trip_cells": 25, "round_trip_contact_traversals": 900},
                "current659_level14_records": 0, "current659_level14_workbook_identity": False,
                "canonical_ids_allocated": False, "runtime_eligible": False, "admitted": False,
                "fixed_bpm": None, "note_per_click": None, "onset_q": None, "duration_q": None,
                "records": records}
    handoff = {"version": "parallel12-level014-allocation-handoff.1",
               "status": "pending_P02_allocation_authority_and_post_Level13_floor",
               "proposal_sha256": sha(encode(proposal)), "source_map": source_map,
               "guidance_refs": guidance_refs,
               "routes": {"up_landmarks": up, "down_landmarks": down,
                          "continuous_round_trip": trip, "turn_after_rung": "L14-rung13",
                          "shift_frets_up": 1, "shift_frets_down": -1},
               "record_count": 13, "group_count": 156, "event_count": 468, "variant_count": 26,
               "current659_level14_records": 0, "current659_level14_workbook_identity": False,
               "decisions_required": ["P02 allocation after Level13 global floor and source-key review",
                                      "Curriculum review of 12 rolling triplets, repeated octave root and 25-cell route",
                                      "Reviewed timing/pause binding and lineage/admission policy before schema1 import"],
               "selected_choice": None, "allocation_allowed": False, "no_admission": True}
    verify(proposal, handoff)
    return proposal, handoff


def verify(proposal: dict, handoff: dict) -> dict:
    need(proposal["canonical_ids_allocated"] is False and proposal["runtime_eligible"] is False and
         proposal["admitted"] is False and handoff["allocation_allowed"] is False and
         handoff["no_admission"] is True and handoff["selected_choice"] is None and
         all(proposal[k] is None for k in ("fixed_bpm", "note_per_click", "onset_q", "duration_q")),
         "INVALID_AUTHORITY")
    counts = {"records": 13, "groups": 156, "events": 468, "variants": 26,
              "up_landmark_cells": 13, "down_landmark_cells": 13,
              "continuous_round_trip_cells": 25, "round_trip_contact_traversals": 900}
    need(proposal["counts"] == counts and
         (handoff["record_count"], handoff["group_count"], handoff["event_count"],
          handoff["variant_count"]) == (13, 156, 468, 26), "COVERAGE")
    keys = [f"L14-rung{i:02d}" for i in range(1, 14)]
    need([r["source_local_key"] for r in proposal["records"]] == keys and
         [r["source_local_key"] for r in handoff["source_map"]] == keys and
         handoff["routes"]["up_landmarks"] == keys and
         handoff["routes"]["down_landmarks"] == list(reversed(keys)) and
         handoff["routes"]["continuous_round_trip"] == keys + list(reversed(keys))[1:] and
         handoff["routes"]["turn_after_rung"] == "L14-rung13", "ROUTE_OR_CASE_ORDER")
    for index, record in enumerate(proposal["records"], 1):
        fields = record["schema1_fields"]
        need(record["rung_number"] == index and record["key"] == p09.KEYS[index - 1] and
             record["root_fret"] == index + 4 and record["frame"] == [index + 3, index + 6] and
             record["identity_state"] == "unallocated" and record["schema1_importable"] is False and
             set(fields) == FIELDS and fields["legacy_level"] == 14 and
             fields["context"]["local_code"] == record["source_local_key"] and
             all(fields[k] is None for k in ("id", "workbook_id", "module_id", "content_revision", "lineage")) and
             fields["runtime_eligible"] is False and fields["timing"]["status"] == "unresolved", "INVALID_AUTHORITY")
        need(len(fields["events"]) == 36 and len(record["group_memberships"]) == 12 and
             len(fields["variants"]) == len(record["variant_memberships"]) == 2, "CELL_COUNT")
        for ordinal, event in enumerate(fields["events"], 1):
            group_index = (ordinal - 1) // 3
            slot_index = (ordinal - 1) % 3
            degree = p09.DEGREE_GROUPS[group_index][slot_index]
            string, fret = p09._expected_place(degree, index + 4)
            string_num, open_midi = OPEN_MIDI[string]
            need(event["event_id"] is event["onset_q"] is event["duration_q"] is None and
                 event["kind"] == "note" and (event["string"], event["fret"], event["midi"], event["finger"])
                 == (string_num, fret, open_midi + fret, int(p09.DEGREE_FINGERS[degree - 1])) and
                 event["spelling"] == p09.SCALE_TONES[index - 1][(degree - 1) % 7] and
                 event["degree_contexts"] == {f"{record['key']}-major": {
                     "source_label": str(degree), "ordinal": degree, "alteration": 0}},
                 "UNSUPPORTED_TIMING_OR_NOTE")
        for group_index, group in enumerate(record["group_memberships"], 1):
            need(group == {"source_group": group_index, "half": "up" if group_index <= 6 else "down",
                           "event_local_ordinals": list(range((group_index - 1) * 3 + 1, group_index * 3 + 1)),
                           "source_degrees": list(p09.DEGREE_GROUPS[group_index - 1]),
                           "source_beat_relation": "one_three_note_group_per_beat",
                           "beat_unit_q": None}, "GROUP_MEMBERSHIP")
        need(fields["events"][17]["midi"] == fields["events"][18]["midi"] and
             fields["events"][17]["string"] == fields["events"][18]["string"] and
             fields["events"][17]["fret"] == fields["events"][18]["fret"], "TURN_ROOT")
        need([v["pick_start"] for v in fields["variants"]] == ["D", "U"] and
             all(v["id"] is v["event_ids"] is None and v["grouping"]["kind"] == "unresolved" and
                 v["grouping"]["beat_unit_q"] is None for v in fields["variants"]) and
             all(m["event_local_ordinals"] == list(range(1, 37)) and
                 m["group_indices"] == list(range(1, 13)) and
                 m["repeated_octave_root_ordinals"] == [18, 19]
                 for m in record["variant_memberships"]), "VARIANT_MEMBERSHIP")
    need(handoff["proposal_sha256"] == sha(encode(proposal)) and
         proposal["current659_level14_records"] == handoff["current659_level14_records"] == 0 and
         proposal["current659_level14_workbook_identity"] is handoff["current659_level14_workbook_identity"] is False,
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
    print(json.dumps({"status": "unallocated_level014_pending_P02_allocation", "counts": verify(proposal, handoff)}, sort_keys=True))


if __name__ == "__main__":
    main()
