#!/usr/bin/env python3
"""Whole-Level15 source-linked schema1 fields and existing-illustration reconciliation."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from pypdf import PdfReader

import curriculum_level015_whole_candidate as p08

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = Path("Build/parallel-08/2.3.1.1.1-level015-whole-r01/candidate-02.json")
RESULT = Path("Results/parallel-08/exercises/conversion/20260923T145058Z-2.3.1.1.1-level015-whole-candidate-r01-results.md")
PACKAGE = Path("Content/controls/curriculum-v1/package.json")
REGISTRY = Path("Content/controls/curriculum-v1/identity-registry.json")
OUT = Path("Build/parallel-12/level015-schema1-unallocated-r01")
PINS = {
    CANDIDATE: (559471, "bff1da256722d18dff4c564032a74947fa56cbd3af460b3733537380dc9d804b"),
    RESULT: (None, "49a2b75a3aaf88c96e1a1efb16837643b540240cee43d3ab0e6b1ec639bc8a94"),
    p08.TXT_REL: (p08.TXT_BYTES, p08.TXT_SHA256),
    p08.PDF_REL: (p08.PDF_BYTES, p08.PDF_SHA256),
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
GUIDANCE_KEYS = ("purpose", "change_from_level14", "interpretation", "formula", "shape", "sequence",
                 "cell_picking", "crossing", "neck_route", "practice", "round_trip", "clean_standard",
                 "variations", "mastery")


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
    match = re.fullmatch(r"L15-TXT1-(\d+)-(\d+)", ref)
    need(match is not None, "TXT_REF")
    first, last = map(int, match.groups())
    need(1 <= first <= last <= len(lines), "TXT_SPAN")
    section = "\n".join(lines[first - 1:last])
    return {"ref": ref, "first_line": first, "last_line": last,
            "text_sha256": sha(section.encode())}


def reconcile(root: Path, candidate: dict) -> dict:
    foundation = json.loads((root / PACKAGE).read_text())
    registry = json.loads((root / REGISTRY).read_text())
    existing = [r for r in foundation["records"] if r["legacy_level"] == 15]
    need(len(foundation["records"]) == 659 and len(existing) == 1 and
         existing[0]["id"] == "fg:item:000004" and
         existing[0]["workbook_id"] == "fg:workbook:000015" and
         existing[0]["module_id"] == "fg:module:000004" and
         existing[0]["content_revision"] == 3 and existing[0]["lineage"]["kind"] == "revision" and
         any(e["id"] == "fg:workbook:000015" for e in registry["entities"]),
         "EXISTING_LEVEL15_SCOPE")
    old = existing[0]
    notes = candidate["records"][0]["groups"][0]["notes"]
    source_tuples = [(OPEN_MIDI[n["string"]][0], n["fret"],
                      OPEN_MIDI[n["string"]][1] + n["fret"], int(n["finger_digit"])) for n in notes]
    old_tuples = [(e["string"], e["fret"], e["midi"], e["finger"]) for e in old["events"]]
    need(len(source_tuples) == 3 and source_tuples == old_tuples and
         old["control_scope"]["extent"] == "selected_illustration" and
         old["timing"]["status"] == "source_defined" and
         len(old["variants"]) == 4, "EXISTING_FIRST_TRIPLET_OVERLAP")
    refs = set(old["source_refs"])
    need({"L15-TXT59-81", "L15-TXT21-32", "L15-TXT392-398"}.issubset(refs) and
         candidate["records"][0]["source_refs"]["txt"] == "L15-TXT1-70-91" and
         {foundation["sources"][ref]["sha256"] for ref in refs} == {p08.TXT_SHA256},
         "EXISTING_SOURCE_ASSET")
    return {"status": "allocation_authority_pending_P02",
            "existing_workbook_id": old["workbook_id"], "existing_item_id": old["id"],
            "existing_module_id": old["module_id"], "existing_content_revision": 3,
            "existing_lineage_kind": old["lineage"]["kind"],
            "existing_predecessor_revision": old["lineage"]["predecessor_revision"],
            "existing_predecessor_sha256": old["lineage"]["predecessor_sha256"],
            "existing_variant_ids": [v["id"] for v in old["variants"]],
            "existing_variant_labels": [v["label"] for v in old["variants"]],
            "existing_timing_status": old["timing"]["status"],
            "existing_extent": old["control_scope"]["extent"],
            "source_local_key_correspondence": {"L15-rung01-first-triplet": old["id"]},
            "source_local_key_is_stored_in_current_record": False,
            "exact_source_ref_key_overlap": [],
            "shared_original_txt_sha256": p08.TXT_SHA256,
            "overlapping_txt_line_spans": [{"proposal": "L15-TXT1-70-91", "existing": "L15-TXT59-81",
                                            "shared_lines": [70, 81]}],
            "physical_first_triplet_tuple_match": True,
            "old_spelling_values": [e["spelling"] for e in old["events"]],
            "old_event_timing": [{"onset_q": e["onset_q"], "duration_q": e["duration_q"]}
                                 for e in old["events"]],
            "remaining_full_rung_source_keys": [r["source_local_key"] for r in candidate["records"][1:]],
            "decision_matrix": [
                {"choice": "retain_selected_illustration_and_add_13_full_rungs",
                 "requires": "P02 review of duplicate opening-triplet source, workbook baseline, source-key bridge, timing split and no selected-item reallocation"},
                {"choice": "reviewed_revision_of_existing_item_to_complete_rung01_then_add_12",
                 "requires": "Separate lineage authority, predecessor digest, 3-to-78 event/variant/timing reconciliation and P02 integration decision"},
                {"choice": "defer_level15_allocation",
                 "requires": "Continue detached source-field evidence until workbook/revision semantics are approved"}],
            "selected_choice": None, "canonical_ids_allocated": False, "admitted": False}


def build(root: Path = ROOT, candidate_override: dict | None = None) -> tuple[dict, dict]:
    pin(root)
    candidate = candidate_override if candidate_override is not None else json.loads((root / CANDIDATE).read_text())
    need(candidate == p08.build_candidate(), "P08_SOURCE_CANDIDATE_DRIFT")
    need(candidate["level"] == 15 and len(candidate["records"]) == 13 and
         candidate["whole_workbook_source_covered"] is True and
         candidate["whole_workbook_complete"] is False and not candidate["exceptions"] and
         all(candidate[k] is False for k in ("admitted", "imported", "runtime_admitted", "runtime_eligible")),
         "SOURCE_SCOPE")
    lines = (root / p08.TXT_REL).read_text().splitlines()
    pdf_pages = [page.extract_text() for page in PdfReader(str(root / p08.PDF_REL)).pages]
    need(len(lines) == 410 and len(pdf_pages) == 10, "SOURCE_LENGTH")
    existing = reconcile(root, candidate)
    guidance_refs = [candidate["instructions"][key]["ref"] for key in GUIDANCE_KEYS]
    need(len(guidance_refs) == len(set(guidance_refs)) == 14 and
         all(txt_span(ref, lines)["ref"] == ref for ref in guidance_refs), "GUIDANCE_REFS")
    records, source_map = [], []
    for index, row in enumerate(candidate["records"], 1):
        key = f"L15-rung{index:02d}"
        root_fret = index + 4
        need(row["source_local_key"] == key and row["rung"] == index and
             row["key"] == p08.KEYS[index - 1] and row["root_string"] == "E" and
             row["root_fret"] == root_fret and row["frame"] == [root_fret - 1, root_fret + 2] and
             row["group_count"] == len(row["groups"]) == 26 and row["note_count"] == 78 and
             all(row[k] is None for k in ("canonical_item_id", "canonical_variant_id", "onset_q",
                                           "duration_q", "note_per_click", "fixed_bpm")) and
             all(row[k] is False for k in ("admitted", "imported", "runtime_admitted", "runtime_eligible")),
             "RUNG_SCOPE")
        txt = txt_span(row["source_refs"]["txt"], lines)
        need(txt["first_line"] == 70 + (index - 1) * 24 and txt["last_line"] == txt["first_line"] + 21 and
             lines[txt["first_line"] - 1] == row["printed_txt"]["heading"], "TXT_CARD")
        pdf_ref = row["source_refs"]["pdf_card"]
        match = re.fullmatch(r"L15-PDF1-p([3-9])", pdf_ref)
        need(match is not None and row["printed_pdf"]["heading"] in pdf_pages[int(match.group(1)) - 1] and
             row["source_refs"]["pdf_map"] == "L15-PDF1-p2", "PDF_CARD")
        refs = list(dict.fromkeys([txt["ref"], pdf_ref, "L15-PDF1-p2", "L15-PDF1-p1",
                                  "L15-PDF1-p9", "L15-PDF1-p10", *guidance_refs]))
        need(row["scale_tones"] == [*p08.SCALE_TONES[index - 1], *p08.SCALE_TONES[index - 1], row["key"]],
             "SCALE_TONES")
        events, groups, middle_roots = [], [], []
        for group_index, group in enumerate(row["groups"], 1):
            half = "up" if group_index <= 13 else "down"
            degrees = p08.DEGREE_GROUPS[group_index - 1]
            need(group["index"] == group_index and group["half"] == half and len(group["notes"]) == 3,
                 "GROUP_SOURCE")
            ordinals = []
            for slot, note in enumerate(group["notes"], 1):
                ordinal = (group_index - 1) * 3 + slot
                degree = degrees[slot - 1]
                string, fret = p08._expected_place(degree, root_fret)
                spelling = row["scale_tones"][degree - 1]
                need(note == {"ordinal": ordinal, "group": group_index, "slot": slot, "half": half,
                              "degree": degree, "finger_digit": p08.DEGREE_FINGERS[degree - 1],
                              "string": string, "fret": fret,
                              "is_middle_octave_root": degree == 8,
                              "is_high_root_turn": ordinal in (39, 40),
                              "onset_q": None, "duration_q": None}, "NOTE_SOURCE")
                string_num, open_midi = OPEN_MIDI[string]
                midi = open_midi + fret
                need(midi == 40 + root_fret + p08.MAJOR_OFFSETS[degree - 1] and
                     pitch_class(spelling) == midi % 12, "NOTE_PITCH_SPELLING")
                events.append({"event_id": None, "kind": "note", "string": string_num,
                               "fret": fret, "midi": midi, "spelling": spelling,
                               "degree_contexts": {f"{row['key']}-major": {
                                   "source_label": str(degree), "ordinal": degree, "alteration": 0}},
                               "finger": int(note["finger_digit"]), "onset_q": None,
                               "duration_q": None, "attack": "picked", "tie_from": None})
                ordinals.append(ordinal)
                if degree == 8:
                    middle_roots.append(ordinal)
            groups.append({"source_group": group_index, "half": half,
                           "event_local_ordinals": ordinals, "source_degrees": list(degrees),
                           "source_beat_relation": "one_three_note_group_per_beat",
                           "beat_unit_q": None})
        need(len(events) == 78 and len(middle_roots) == 6 and
             (events[38]["string"], events[38]["fret"], events[38]["midi"]) ==
             (events[39]["string"], events[39]["fret"], events[39]["midi"]), "CELL_TURN_OR_MIDDLE_ROOT")
        variants, membership = [], []
        for grouping, pick, notes_per_beat, factor in (
                ("triplets", "D", 3, [1, 1]), ("triplets", "U", 3, [1, 1]),
                ("sextuplets-half-marking", "D", 6, [1, 2]),
                ("sextuplets-half-marking", "U", 6, [1, 2])):
            label = f"{grouping}-{pick}"
            variants.append({"id": None, "label": label, "event_ids": None, "source_refs": refs,
                             "route": "two_octave_26_rolling_triplets_repeated_high_root",
                             "pick_start": pick, "pick_start_origin": "source_authored",
                             "role": "notation_practice", "accent_policy": "source_unspecified",
                             "grouping": {"kind": "unresolved", "notes_per_beat": notes_per_beat,
                                          "beat_unit_q": None, "marking_factor": factor,
                                          "source_label": "Eighth-note triplets; optional two groups per beat at half marking"},
                             "tail_pause": None,
                             "unresolved": ["Absolute BPM, quarter-note beat mapping and optional inter-cell pause are unbound."]})
            membership.append({"label": label, "event_local_ordinals": list(range(1, 79)),
                               "group_indices": list(range(1, 27)),
                               "middle_octave_root_ordinals": middle_roots,
                               "repeated_high_root_ordinals": [39, 40]})
        fields = {"id": None, "workbook_id": None, "module_id": None, "legacy_level": 15,
                  "title": f"Rung {index:02d}: {row['key']} major two-octave three-note rolling sequence",
                  "kind": "notation", "content_revision": None, "status": "converted_candidate",
                  "runtime_eligible": False, "source_refs": refs, "authored_text_refs": refs,
                  "normalization": [{"kind": "representation_metadata", "basis": "P08 whole-Level15 candidate and original TXT/PDF",
                                     "text": "One 78-contact cell has 26 overlapping triplets, six middle-octave-root contacts and two consecutive high-root contacts; A at frets 5 and 17 are distinct positions."}],
                  "context": {"local_code": key,
                              "route": "UP rungs01-13; DOWN landmarks13-01; continuous trip rungs01-13 then12-01",
                              "position": f"low-E root fret {root_fret}; frame {root_fret - 1}-{root_fret + 2}",
                              "pick_start": "D or U source-authored; alternate picking continues across groups, octaves, turn and shifts",
                              "pick_start_variants": ["D", "U"], "pick_continues_at_turn": True,
                              "tuning_open_midi": [40, 45, 50, 55, 59, 64], "capo": 0,
                              "source_group_count": 26, "source_notes_per_group": 3},
                  "events": events,
                  "timing": {"status": "unresolved", "unit": "quarter",
                             "basis": "Printed triplet/sextuplet relationships and relative practice BPM do not allocate absolute quarter-note onset/duration or pause binding",
                             "other_source_requirements": [candidate["instructions"][name]["text"]
                                                           for name in ("practice", "cell_picking", "sequence", "variations")]},
                  "rubric": None, "resource_requirements": [],
                  "ambiguities": ["Quarter-note onset/duration and absolute BPM are unassigned.",
                                  "Optional one-beat inter-cell pause and sextuplet marking are not bound to a performed grid.",
                                  "Existing revision-3 selected opening triplet requires P02 lineage/timing reconciliation before allocation."],
                  "control_scope": {"local_case": f"Level15 rung{index:02d} {row['key']} major full 78-contact rolling cell",
                                    "extent": "complete_selected_case", "whole_workbook_complete": False,
                                    "source_event_count": 78, "basis_refs": refs,
                                    "unresolved": ["Identity, lineage and route-level admission pending."]},
                  "variants": variants, "lineage": None}
        need(set(fields) == FIELDS, "FIELD_SHAPE")
        records.append({"source_local_key": key, "rung_number": index, "key": row["key"],
                        "root_fret": root_fret, "frame": row["frame"], "schema1_fields": fields,
                        "group_memberships": groups, "variant_memberships": membership,
                        "source_printed_rows": {"ascending": row["printed_txt"]["ascending"],
                                                "descending": row["printed_txt"]["descending"]},
                        "identity_state": "unallocated", "schema1_importable": False,
                        "open_gaps": ["existing selected-illustration lineage decision", "canonical identities",
                                      "quarter-note timing and pause binding", "runtime/Curriculum admission"]})
        source_map.append({"source_local_key": key, "rung_number": index, "key": row["key"],
                           "root_fret": root_fret, "frame": row["frame"],
                           "txt": txt["ref"], "txt_passage_sha256": txt["text_sha256"],
                           "pdf_card": pdf_ref, "pdf_map": "L15-PDF1-p2"})
    up = [f"L15-rung{i:02d}" for i in range(1, 14)]
    down = list(reversed(up))
    trip = up + down[1:]
    route = candidate["neck_route"]
    need([x["rung"] for x in route["ascending_landmarks"]] == list(range(1, 14)) and
         [x["rung"] for x in route["descending_landmarks"]] == list(range(13, 0, -1)) and
         route["single_turn_cell_sequence"] == list(range(1, 14)) + list(range(12, 0, -1)) and
         route["single_turn_cell_count"] == 25 and route["single_turn_note_count"] == 1950 and
         route["turn_rung_played_once"] == 13 and route["up_fret_step"] == 1 and
         route["down_fret_step"] == -1, "ROUTE_SOURCE")
    counts = {"records": 13, "groups": 338, "events": 1014, "variants": 52,
              "up_landmark_cells": 13, "down_landmark_cells": 13,
              "continuous_round_trip_cells": 25, "round_trip_contact_traversals": 1950}
    proposal = {"proposal_version": "parallel12-level015-unallocated-schema1-fields.1",
                "classification": "source_mapped_field_proposal_not_schema1_importable",
                "legacy_level": 15,
                "source_pins": {str(path): {"bytes": (root / path).stat().st_size, "sha256": digest}
                                for path, (_, digest) in PINS.items()},
                "counts": counts, "canonical_ids_allocated": False, "runtime_eligible": False,
                "admitted": False, "fixed_bpm": None, "note_per_click": None,
                "onset_q": None, "duration_q": None,
                "existing_selected_illustration_reconciliation": existing,
                "records": records}
    handoff = {"version": "parallel12-level015-allocation-decision-handoff.1",
               "status": "pending_P02_existing_selected_illustration_lineage_decision",
               "proposal_sha256": sha(encode(proposal)), "source_map": source_map,
               "guidance_refs": guidance_refs,
               "routes": {"up_landmarks": up, "down_landmarks": down,
                          "continuous_round_trip": trip, "turn_after_rung": "L15-rung13",
                          "shift_frets_up": 1, "shift_frets_down": -1},
               "existing_selected_illustration_reconciliation": existing,
               "record_count": 13, "group_count": 338, "event_count": 1014, "variant_count": 52,
               "allocation_allowed": False, "no_admission": True}
    verify(proposal, handoff)
    return proposal, handoff


def verify(proposal: dict, handoff: dict) -> dict:
    need(proposal["canonical_ids_allocated"] is False and proposal["runtime_eligible"] is False and
         proposal["admitted"] is False and handoff["allocation_allowed"] is False and
         handoff["no_admission"] is True and
         all(proposal[k] is None for k in ("fixed_bpm", "note_per_click", "onset_q", "duration_q")),
         "INVALID_AUTHORITY")
    counts = {"records": 13, "groups": 338, "events": 1014, "variants": 52,
              "up_landmark_cells": 13, "down_landmark_cells": 13,
              "continuous_round_trip_cells": 25, "round_trip_contact_traversals": 1950}
    need(proposal["counts"] == counts and
         (handoff["record_count"], handoff["group_count"], handoff["event_count"],
          handoff["variant_count"]) == (13, 338, 1014, 52), "COVERAGE")
    keys = [f"L15-rung{i:02d}" for i in range(1, 14)]
    need([r["source_local_key"] for r in proposal["records"]] == keys and
         [r["source_local_key"] for r in handoff["source_map"]] == keys and
         handoff["routes"]["up_landmarks"] == keys and
         handoff["routes"]["down_landmarks"] == list(reversed(keys)) and
         handoff["routes"]["continuous_round_trip"] == keys + list(reversed(keys))[1:] and
         handoff["routes"]["turn_after_rung"] == "L15-rung13", "ROUTE_OR_CASE_ORDER")
    for index, record in enumerate(proposal["records"], 1):
        fields = record["schema1_fields"]
        need(record["rung_number"] == index and record["key"] == p08.KEYS[index - 1] and
             record["root_fret"] == index + 4 and record["frame"] == [index + 3, index + 6] and
             record["identity_state"] == "unallocated" and record["schema1_importable"] is False and
             set(fields) == FIELDS and fields["legacy_level"] == 15 and
             fields["context"]["local_code"] == record["source_local_key"] and
             all(fields[k] is None for k in ("id", "workbook_id", "module_id", "content_revision", "lineage")) and
             fields["runtime_eligible"] is False and fields["timing"]["status"] == "unresolved", "INVALID_AUTHORITY")
        need(len(fields["events"]) == 78 and len(record["group_memberships"]) == 26 and
             len(fields["variants"]) == len(record["variant_memberships"]) == 4, "CELL_COUNT")
        middle_roots = []
        for ordinal, event in enumerate(fields["events"], 1):
            group_index = (ordinal - 1) // 3
            slot_index = (ordinal - 1) % 3
            degree = p08.DEGREE_GROUPS[group_index][slot_index]
            string, fret = p08._expected_place(degree, index + 4)
            string_num, open_midi = OPEN_MIDI[string]
            need(event["event_id"] is event["onset_q"] is event["duration_q"] is None and
                 event["kind"] == "note" and
                 (event["string"], event["fret"], event["midi"], event["finger"]) ==
                 (string_num, fret, open_midi + fret, int(p08.DEGREE_FINGERS[degree - 1])) and
                 event["spelling"] == [*p08.SCALE_TONES[index - 1], *p08.SCALE_TONES[index - 1],
                                       p08.KEYS[index - 1]][degree - 1] and
                 event["degree_contexts"] == {f"{record['key']}-major": {
                     "source_label": str(degree), "ordinal": degree, "alteration": 0}},
                 "UNSUPPORTED_TIMING_OR_NOTE")
            if degree == 8:
                middle_roots.append(ordinal)
        for group_index, group in enumerate(record["group_memberships"], 1):
            need(group == {"source_group": group_index, "half": "up" if group_index <= 13 else "down",
                           "event_local_ordinals": list(range((group_index - 1) * 3 + 1, group_index * 3 + 1)),
                           "source_degrees": list(p08.DEGREE_GROUPS[group_index - 1]),
                           "source_beat_relation": "one_three_note_group_per_beat", "beat_unit_q": None},
                 "GROUP_MEMBERSHIP")
        need(len(middle_roots) == 6 and
             (fields["events"][38]["string"], fields["events"][38]["fret"], fields["events"][38]["midi"]) ==
             (fields["events"][39]["string"], fields["events"][39]["fret"], fields["events"][39]["midi"]),
             "TURN_ROOT_OR_MIDDLE_ROOT")
        expected_labels = ["triplets-D", "triplets-U", "sextuplets-half-marking-D", "sextuplets-half-marking-U"]
        need([v["label"] for v in fields["variants"]] == expected_labels and
             all(v["id"] is v["event_ids"] is None and v["grouping"]["kind"] == "unresolved" and
                 v["grouping"]["beat_unit_q"] is None for v in fields["variants"]) and
             all(m["event_local_ordinals"] == list(range(1, 79)) and
                 m["group_indices"] == list(range(1, 27)) and
                 m["middle_octave_root_ordinals"] == middle_roots and
                 m["repeated_high_root_ordinals"] == [39, 40]
                 for m in record["variant_memberships"]), "VARIANT_MEMBERSHIP")
    overlap = proposal["existing_selected_illustration_reconciliation"]
    need(overlap == handoff["existing_selected_illustration_reconciliation"] and
         overlap["selected_choice"] is None and overlap["existing_item_id"] == "fg:item:000004" and
         overlap["existing_content_revision"] == 3 and overlap["physical_first_triplet_tuple_match"] is True and
         len(overlap["remaining_full_rung_source_keys"]) == 12 and
         overlap["exact_source_ref_key_overlap"] == [], "EXISTING_SELECTED_RECONCILIATION")
    need(handoff["proposal_sha256"] == sha(encode(proposal)), "PROPOSAL_HASH")
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
    print(json.dumps({"status": "unallocated_level015_pending_existing_illustration_reconciliation",
                      "counts": verify(proposal, handoff)}, sort_keys=True))


if __name__ == "__main__":
    main()
