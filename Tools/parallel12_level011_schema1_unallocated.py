#!/usr/bin/env python3
"""Whole-Level11 source-to-schema1 field proposal without canonical allocation."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import curriculum_level011_whole_candidate as p08

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = Path("Build/parallel-08/2.3.1.1.1-level011-whole-r01/candidate-02.json")
RESULT = Path("Results/parallel-08/exercises/conversion/20260923T144113Z-2.3.1.1.1-level011-whole-candidate-r01-results.md")
TXT = Path("Notes/music/guitar project/TXT version/108_Finger_Permutations_Level_11_Three_Position_Relay.txt")
PDF = Path("Notes/music/guitar project/PDF version/108_Finger_Permutations_Level_11_Three_Position_Relay.pdf")
OUT = Path("Build/parallel-12/level011-schema1-unallocated-r01")
PINS = {
    CANDIDATE: (3254172, "81d0afbcdeaacc61a48bace0766a7c725d26b629fddc7ec1bc931c9e76b698d9"),
    RESULT: (None, "6c37f6a25555243b5b5ee372665ec85390c2d098ecd0f1cf067ad0e55b44772e"),
    TXT: (29960, "e579bb423d644a628723c802d84967f5c7aad49bf4e8e89bba5e4b622bf6ff48"),
    PDF: (43510, "5f9b5e29e2f5ad3aa3372125f0ec0b91e6245eef1edabd5e81c06d1f00f5e917"),
}
STRINGS = {"E": (1, 40), "A": (2, 45), "D": (3, 50), "G": (4, 55), "B": (5, 59), "e": (6, 64)}
FIELDS = {"id", "workbook_id", "module_id", "legacy_level", "title", "kind", "content_revision", "status", "runtime_eligible", "source_refs", "authored_text_refs", "normalization", "context", "events", "timing", "rubric", "resource_requirements", "ambiguities", "control_scope", "variants", "lineage"}
GAPS = ["canonical item/module/workbook IDs", "canonical event IDs", "canonical variant IDs and memberships",
        "bound allocation and new-record lineage", "absolute starting BPM", "quarter-note onset/duration and beat unit",
        "both first-pass shift pauses in quarter notes", "pass-specific landing accents",
        "triplet/quintuplet pulse-to-quarter mapping"]


class ProposalError(ValueError):
    pass


def need(ok: bool, code: str) -> None:
    if not ok:
        raise ProposalError(code)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def encode(obj: object) -> bytes:
    return (json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n").encode()


def pin(root: Path = ROOT) -> None:
    need(root.resolve() == ROOT.resolve(), "ROOT_DRIFT")
    for path, (length, expected) in PINS.items():
        raw = (root / path).read_bytes()
        need(length is None or len(raw) == length, f"INPUT_LENGTH_DRIFT {path}")
        need(sha(raw) == expected, f"INPUT_HASH_DRIFT {path}")


def source_span(row: dict, lines: list[str], pages: list[str]) -> dict:
    ref = row["source_refs"]["txt"]
    match = re.fullmatch(r"L11-TXT1-(\d+)-(\d+)", ref)
    need(match is not None, "TXT_REF")
    first, last = map(int, match.groups())
    need(1 <= first <= last <= len(lines), "TXT_SPAN")
    section = lines[first - 1:last]
    need(section[0] == f"Exercise {row['exercise_number']}: {row['code']}", "TXT_HEADING")
    for direction in row["directions"]:
        need(direction["f_row"] in section and direction["s_row"] in section,
             "TXT_FINGER_TAB")
    pdf_ref = row["source_refs"]["pdf"]
    match = re.fullmatch(r"L11-PDF1-p(\d+)", pdf_ref)
    need(match is not None, "PDF_REF")
    page = int(match.group(1))
    need(2 <= page <= len(pages) and
         re.search(rf"\b{row['exercise_number']}\b\s+{row['code']}\b", pages[page - 1]) is not None,
         "PDF_HEADING")
    for direction in row["directions"]:
        need(direction["f_row"] in pages[page - 1] and direction["s_row"] in pages[page - 1],
             "PDF_FINGER_TAB")
    return {"txt": ref, "pdf": pdf_ref, "pdf_page": page,
            "txt_passage_sha256": sha("\n".join(section).encode())}


def build(root: Path = ROOT, candidate_override: dict | None = None) -> tuple[dict, dict]:
    pin(root)
    candidate = candidate_override if candidate_override is not None else json.loads((root / CANDIDATE).read_text())
    need(candidate == p08.build_candidate(), "P08_SOURCE_CANDIDATE_DRIFT")
    need(candidate["schema"] == "fathom-level011-whole-detached-candidate-v1" and
         candidate["level"] == 11 and candidate["set_count"] == 9 and
         candidate["whole_workbook_source_covered"] is True and
         candidate["whole_workbook_complete"] is False and
         all(candidate[k] is False for k in ("admitted", "imported", "runtime_admitted", "runtime_eligible")) and
         len(candidate["records"]) == 108, "SOURCE_SCOPE")
    from pypdf import PdfReader
    pages = [page.extract_text() for page in PdfReader(str(root / PDF)).pages]
    lines = (root / TXT).read_text().splitlines()
    need(len(pages) == 10 and len(lines) == 945 and
         "The first landing note is note 2. The second landing note is note 4." in "\n".join(lines[:45]),
         "SOURCE_INSTRUCTION")
    records, source_map, seen = [], [], set()
    for index, row in enumerate(candidate["records"]):
        number = index + 1
        key = f"L11-set{index // 12 + 1:02d}-ex{number:03d}"
        need(row["source_local_key"] == key and row["exercise_number"] == f"{number:03d}" and
             key not in seen and re.fullmatch(r"[1-4]{4}", row["code"]) is not None,
             "CASE_MISSING_OR_DUPLICATE")
        seen.add(key)
        need(all(row[k] is None for k in ("canonical_item_id", "canonical_variant_id", "fixed_bpm",
                                            "note_per_click", "onset_q", "duration_q")) and
             all(row[k] is False for k in ("admitted", "imported", "runtime_admitted", "runtime_eligible")),
             "SOURCE_AUTHORITY_OR_TIMING")
        src = source_span(row, lines, pages)
        refs = [src["txt"], src["pdf"], "L11-TXT1-4-6", "L11-TXT1-9-15",
                "L11-TXT1-24-26", "L11-TXT1-29-31", "L11-TXT1-34-41", "L11-TXT1-44-45"]
        need(len(row["directions"]) == 2, "DIRECTION_COUNT")
        events, variants, memberships = [], [], []
        for direction_index, direction in enumerate(row["directions"]):
            name = ("shift_up", "shift_down")[direction_index]
            strings = ["E", "A", "D", "G", "B", "e"] if name == "shift_up" else ["e", "B", "G", "D", "A", "E"]
            positions = ["P5", "P7", "P9"] if name == "shift_up" else ["P9", "P7", "P5"]
            need(direction["direction"] == name and direction["string_order"] == strings and
                 direction["position_order"] == positions and direction["shift_after_notes"] == [1, 3] and
                 direction["landing_note_ordinals"] == [2, 4] and len(direction["string_routes"]) == 6,
                 "DIRECTION_SOURCE")
            start = len(events)
            landings = []
            for route_index, route in enumerate(direction["string_routes"]):
                string = strings[route_index]
                need(route["string"] == string and route["shift_after_notes"] == [1, 3] and
                     route["landing_note_ordinals"] == [2, 4] and
                     route["shift_frets"] == ([2, 2] if name == "shift_up" else [-2, -2]) and
                     [c["position"] for c in route["cells"]] == positions and
                     [len(c["notes"]) for c in route["cells"]] == [1, 2, 1], "ROUTE_SOURCE")
                notes = [note for cell in route["cells"] for note in cell["notes"]]
                for local, note in enumerate(notes, 1):
                    pos = positions[0 if local == 1 else 1 if local <= 3 else 2]
                    finger = int(row["code"][local - 1])
                    fret = int(pos[1:]) + finger - 1
                    string_number, open_midi = STRINGS[string]
                    need(note["ordinal"] == local and note["string"] == string and note["position"] == pos and
                         note["finger_digit"] == str(finger) and note["fret"] == fret and
                         note["is_landing_note"] is (local in (2, 4)) and
                         note["onset_q"] is note["duration_q"] is None,
                         "FINGER_FRET_LANDING_SOURCE")
                    events.append({"event_id": None, "kind": "note", "string": string_number,
                                   "fret": fret, "midi": open_midi + fret, "spelling": None,
                                   "degree_contexts": {}, "finger": finger, "onset_q": None,
                                   "duration_q": None, "attack": "picked", "tie_from": None})
                    if local in (2, 4):
                        landings.append(len(events))
            need(len(events) - start == 24 and len(landings) == 12, "DIRECTION_EVENT_COUNT")
            ordinals = list(range(start + 1, len(events) + 1))
            for pick in ("D", "U"):
                label = f"{name}-{pick}"
                variants.append({"id": None, "label": label, "event_ids": None, "source_refs": refs,
                                 "route": name, "pick_start": pick,
                                 "pick_start_origin": "learner_configuration",
                                 "accent_policy": "source_unspecified", "role": "notation_practice",
                                 "grouping": {"kind": "unresolved", "notes_per_beat": None,
                                              "beat_unit_q": None, "marking_factor": [1, 1],
                                              "source_label": "1+2+1 double-shift practice specifies eighths, pauses and later pulses but no fixed quarter-note grid"},
                                 "tail_pause": None,
                                 "unresolved": ["Pass-specific two pauses and landing accents require later timing/accent binding."]})
                memberships.append({"label": label, "event_local_ordinals": ordinals,
                                    "landing_event_local_ordinals": landings})
        need(len(events) == 48 and len(variants) == 4, "CASE_EVENT_COUNT")
        timing_requirements = [candidate["instructions"][k] for k in
                               ("movement_rule_text", "overlapping_fret_rule_text", "picking_rule_text",
                                "practice_rule_text", "after_mastery_text")]
        fields = {"id": None, "workbook_id": None, "module_id": None, "legacy_level": 11,
                  "title": f"Exercise {number:03d}: {row['code']} — three-position relay", "kind": "notation",
                  "content_revision": 1, "status": "converted_candidate", "runtime_eligible": False,
                  "source_refs": refs, "authored_text_refs": refs,
                  "normalization": [{"kind": "representation_metadata", "basis": "P08 closed whole-Level11 candidate and original TXT/PDF",
                                     "text": "Two printed directions each traverse six sequential one-string 1+2+1 routes through three whole-hand frames; shifts occur after notes 1 and 3 and land on notes 2 and 4. Direction names describe frame travel, not melodic contour."}],
                  "context": {"local_code": row["code"], "route": "shift_up E-A-D-G-B-e; shift_down e-B-G-D-A-E",
                              "position": "P5-P7-P9 or P9-P7-P5; 1+2+1 grouping with two whole-hand shifts",
                              "pick_start": "D or U selected by learner; alternation continues through both shifts",
                              "pick_start_variants": ["D", "U"],
                              "source_tempo_rules_ref": "L11-TXT1-34-41",
                              "tuning_open_midi": [40, 45, 50, 55, 59, 64], "capo": 0},
                  "events": events, "timing": {"status": "unresolved", "unit": "quarter",
                                               "basis": "Relative tempo, ASCII shift barlines and practice subdivisions do not bind quarter-note event spans",
                                               "other_source_requirements": timing_requirements},
                  "rubric": None, "resource_requirements": [],
                  "ambiguities": ["Absolute BPM, onset/duration and quarter-note beat mapping are unprovided.",
                                  "Two first-pass subdivision pauses and landing accents have no pass-specific schema1 binding."],
                  "control_scope": {"local_case": f"Level11 Exercise {number:03d} {row['code']} whole printed case",
                                    "extent": "complete_selected_case", "whole_workbook_complete": False,
                                    "source_event_count": 48, "basis_refs": refs,
                                    "unresolved": ["Timing, accent and identity allocation pending."]},
                  "variants": variants, "lineage": None}
        need(set(fields) == FIELDS, "FIELD_SHAPE")
        records.append({"source_local_key": key, "exercise_number": number, "code": row["code"],
                        "schema1_fields": fields, "variant_memberships": memberships,
                        "identity_state": "unallocated", "schema1_importable": False,
                        "open_gaps": GAPS})
        source_map.append({"source_local_key": key, "exercise_number": number, "code": row["code"], **src})
    proposal = {"proposal_version": "parallel12-level011-unallocated-schema1-fields.1",
                "classification": "source_mapped_field_proposal_not_schema1_importable",
                "legacy_level": 11,
                "source_pins": {str(path): {"bytes": (root / path).stat().st_size, "sha256": expected}
                                for path, (_, expected) in PINS.items()},
                "counts": {"records": 108, "directions": 216, "routes": 1296,
                           "position_cells": 3888, "events": 5184, "landing_flags": 2592,
                           "variant_field_proposals": 432},
                "canonical_ids_allocated": False, "runtime_eligible": False, "admitted": False,
                "fixed_bpm": None, "note_per_click": None, "onset_q": None, "duration_q": None,
                "records": records}
    handoff = {"version": "parallel12-level011-serial-allocation-handoff.1",
               "status": "pending_serial_sharded_identity_allocation",
               "proposal_sha256": sha(encode(proposal)), "source_map": source_map,
               "source_checks": {"txt_headings": 108, "txt_direction_finger_rows": 216,
                                 "txt_direction_tab_rows": 216, "pdf_extracted_headings": 108,
                                 "pdf_direction_finger_tab_pairs": 216, "pdf_pages": 10,
                                 "ordered_physical_notes": 5184, "shift_landing_flags": 2592},
               "record_count": 108, "event_count": 5184, "variant_count": 432,
               "required_identity_slots": ["record.id", "record.workbook_id", "record.module_id",
                                           "events[].event_id", "variants[].id", "variants[].event_ids",
                                           "record.lineage", "candidate_identity_allocation"],
               "allocation_rule": "Allocate only after reviewed predecessor shards and all pending reservations; preserve source fields and 1+2+1 landing ordinals.",
               "no_admission": True}
    verify(proposal, handoff)
    return proposal, handoff


def verify(proposal: dict, handoff: dict) -> dict:
    need(proposal["canonical_ids_allocated"] is False and proposal["runtime_eligible"] is False and
         proposal["admitted"] is False and handoff["no_admission"] is True and
         all(proposal[k] is None for k in ("fixed_bpm", "note_per_click", "onset_q", "duration_q")),
         "INVALID_AUTHORITY")
    need(proposal["counts"] == {"records": 108, "directions": 216, "routes": 1296,
                                "position_cells": 3888, "events": 5184, "landing_flags": 2592,
                                "variant_field_proposals": 432} and
         handoff["record_count"] == 108 and handoff["event_count"] == 5184 and
         handoff["variant_count"] == 432, "COVERAGE")
    keys = [r["source_local_key"] for r in proposal["records"]]
    need(keys == [f"L11-set{i // 12 + 1:02d}-ex{i + 1:03d}" for i in range(108)] and
         [r["source_local_key"] for r in handoff["source_map"]] == keys, "CASE_ORDER")
    for record in proposal["records"]:
        fields = record["schema1_fields"]
        need(set(fields) == FIELDS and record["schema1_importable"] is False and
             record["identity_state"] == "unallocated", "FIELD_SHAPE")
        need(all(fields[k] is None for k in ("id", "workbook_id", "module_id", "lineage")) and
             fields["runtime_eligible"] is False and fields["timing"]["status"] == "unresolved", "INVALID_AUTHORITY")
        need(len(fields["events"]) == 48 and len(fields["variants"]) == 4 and
             len(record["variant_memberships"]) == 4, "CASE_COUNT")
        need(all(e["event_id"] is e["onset_q"] is e["duration_q"] is None for e in fields["events"]),
             "UNSUPPORTED_TIMING_OR_ID")
        need(all(v["id"] is v["event_ids"] is None and v["grouping"]["kind"] == "unresolved" and
                 v["grouping"]["notes_per_beat"] is v["grouping"]["beat_unit_q"] is None
                 for v in fields["variants"]), "UNSUPPORTED_TIMING_OR_ID")
        need([m["label"] for m in record["variant_memberships"]] ==
             [v["label"] for v in fields["variants"]] and
             [m["event_local_ordinals"][0] for m in record["variant_memberships"]] == [1, 1, 25, 25] and
             [m["landing_event_local_ordinals"][:2] for m in record["variant_memberships"]] ==
             [[2, 4], [2, 4], [26, 28], [26, 28]], "VARIANT_MEMBERSHIP")
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
    print(json.dumps({"status": "unallocated_nonadmitted_field_proposal", "counts": verify(proposal, handoff)},
                     sort_keys=True))


if __name__ == "__main__":
    main()
