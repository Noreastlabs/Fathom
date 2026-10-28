#!/usr/bin/env python3
"""Full-Level8 source-to-schema1 field proposal without canonical identity allocation."""

import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DRAFT = Path("Build/parallel-12/2.3.1.1.1-level008-preadmission-draft-r03/draft-01.json")
DRAFT_RESULT = Path("Results/parallel-12/conversion/20260923T143235Z-level008-preadmission-draft-r03-results.md")
TXT = Path("Notes/music/guitar project/TXT version/108_Finger_Permutations_Level_8_Two_Position_Ladder.txt")
PDF = Path("Notes/music/guitar project/PDF version/108_Finger_Permutations_Level_8_Two_Position_Ladder.pdf")
OUT = Path("Build/parallel-12/level008-schema1-unallocated-r01")
PINS = {
    DRAFT: (2678610, "4ef944ab6196ad813d10ed5318f72b57785e4d2d9b4f3f931addd507668b52b2"),
    DRAFT_RESULT: (None, "d504a0f03f80da281b5395d2e0bf638d2b1f69277bba8e190a976fae62deeeba"),
    TXT: (53407, "0cba6885ed917013d5ceda5e0c231c568b4aa99be4c8c0e23941295a3fa5926a"),
    PDF: (43123, "750f9b14962e71bc9ed0dc48a6f9343f2a1d5d14363858f7b9462187fc338829"),
}
STRINGS = {"E": (1, 40), "A": (2, 45), "D": (3, 50), "G": (4, 55), "B": (5, 59), "e": (6, 64)}
REQUIRED_RECORD_KEYS = {"id", "workbook_id", "module_id", "legacy_level", "title", "kind", "content_revision", "status", "runtime_eligible", "source_refs", "authored_text_refs", "normalization", "context", "events", "timing", "rubric", "resource_requirements", "ambiguities", "control_scope", "variants", "lineage"}
OPEN_GAPS = ["canonical item/module/workbook IDs", "canonical event IDs", "canonical variant IDs", "bound identity allocation", "new-record lineage authority", "absolute starting BPM", "quarter-note onset/duration and beat unit", "first-pass pause subdivision duration in quarter notes", "pass-specific accent and stop bindings"]


class ProposalError(ValueError):
    pass


def require(condition, code):
    if not condition:
        raise ProposalError(code)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def serialized(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n").encode()


def check_pins(root=ROOT):
    for path, (length, expected) in PINS.items():
        raw = (root / path).read_bytes()
        require(length is None or len(raw) == length, f"INPUT_LENGTH_DRIFT {path}")
        require(digest(raw) == expected, f"INPUT_HASH_DRIFT {path}")


def source_span(row, lines, pdf_text):
    number = int(row["exercise_number"])
    code = row["code"]
    ref = row["source_refs"]["txt"]
    match = re.fullmatch(r"L8-TXT1-(\d+)-(\d+)", ref)
    require(match is not None, "TXT_REF_SHAPE")
    first, last = map(int, match.groups())
    require(first > 0 and first <= last <= len(lines), "TXT_SPAN")
    passage = lines[first - 1:last]
    require(passage[0] == f"Exercise {number:03d}: {code}", "TXT_HEADING")
    for direction in row["directions"]:
        for route in direction["routes"]:
            require(route["printed_tab_row"] in passage, "TXT_ROUTE_ROW")
    pdf_ref = row["source_refs"]["pdf"]
    pdf_match = re.fullmatch(r"L8-PDF1-p(\d+)", pdf_ref)
    require(pdf_match is not None, "PDF_REF_SHAPE")
    page = int(pdf_match.group(1))
    require(1 <= page <= len(pdf_text) and re.search(rf"\b{number:03d}\b\s+{code}\b", pdf_text[page - 1]) is not None, "PDF_HEADING")
    return {"txt": ref, "pdf": pdf_ref, "txt_passage_sha256": digest("\n".join(passage).encode()), "pdf_page": page}


def check_draft_authority(draft):
    require(draft["level"] == 8 and len(draft["records"]) == 108, "DRAFT_COVERAGE")
    require(draft["counts"] == {"records": 108, "directions": 216, "string_routes": 1296, "four_note_cells": 2592, "untimed_note_projections": 10368}, "DRAFT_COUNT")
    require(not draft["admitted"] and not draft["runtime_eligible"] and not draft["imported"] and not draft["runtime_admitted"], "INVALID_AUTHORITY")
    require(all(draft[x] is None for x in ("canonical_item_id", "canonical_variant_id", "fixed_bpm", "note_per_click", "onset_q", "duration_q")), "UNSUPPORTED_TIMING_OR_ID")
    require(draft["source_pins"]["txt"]["sha256"] == PINS[TXT][1] and draft["source_pins"]["pdf"]["sha256"] == PINS[PDF][1], "SOURCE_PIN_DRIFT")


def build(root=ROOT, draft_override=None):
    check_pins(root)
    draft = draft_override if draft_override is not None else json.loads((root / DRAFT).read_text())
    check_draft_authority(draft)
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise ProposalError("PDF_EXTRACTOR_MISSING: run with bundled workspace Python") from exc
    pdf_reader = PdfReader(str(root / PDF))
    pdf_text = [page.extract_text() for page in pdf_reader.pages]
    require(len(pdf_text) == 10, "PDF_PAGE_COUNT")
    lines = (root / TXT).read_text().splitlines()
    require(lines[5] == "MOVEMENT RULE" and lines[17] == "PRACTICE RULE", "PRACTICE_SOURCE")
    require("pause one subdivision" in "\n".join(lines[:26]) and "10-15 BPM below" in "\n".join(lines[:26]), "PRACTICE_SOURCE")
    records, source_map, seen = [], [], set()
    for index, row in enumerate(draft["records"]):
        number = index + 1
        key = f"L8-set{(index // 12) + 1:02d}-ex{number:03d}"
        require(row["source_local_key"] == key and row["exercise_number"] == f"{number:03d}" and key not in seen, "CASE_MISSING_OR_DUPLICATE")
        seen.add(key)
        require(re.fullmatch(r"[1-4]{4}", row["code"]) is not None, "CODE_SHAPE")
        require(not row["admitted"] and not row["runtime_eligible"] and not row["imported"], "INVALID_AUTHORITY")
        require(row["canonical_item_id"] is None and row["canonical_variant_id"] is None and row["fixed_bpm"] is None and row["note_per_click"] is None and row["onset_q"] is None and row["duration_q"] is None, "UNSUPPORTED_TIMING_OR_ID")
        source = source_span(row, lines, pdf_text)
        refs = [source["txt"], source["pdf"], "L8-TXT1-1-26"]
        events, variant_fields, memberships = [], [], []
        require(len(row["directions"]) == 2, "DIRECTION_COUNT")
        for direction_index, direction in enumerate(row["directions"]):
            name = ("shift_up", "shift_down")[direction_index]
            route_order = ["E", "A", "D", "G", "B", "e"] if name == "shift_up" else ["e", "B", "G", "D", "A", "E"]
            positions = ["P5", "P7"] if name == "shift_up" else ["P7", "P5"]
            require(direction["direction"] == name and direction["route_order"] == route_order and direction["position_order"] == positions and len(direction["routes"]) == 6, "DIRECTION_ROUTE")
            start = len(events)
            for route_index, route in enumerate(direction["routes"]):
                string_name = route_order[route_index]
                require(route["string"] == string_name and route["route_ordinal"] == route_index + 1 and route["position_order"] == positions, "ROUTE_ORDER")
                require(route["shift_after_cell"] == 1 and route["shift_at_center_barline"] is True and route["hand_frame_shift_frets"] == (2 if name == "shift_up" else -2), "SHIFT_BOUNDARY")
                require(len(route["ordered_notes"]) == 8, "ROUTE_NOTE_COUNT")
                for note_index, note in enumerate(route["ordered_notes"]):
                    cell = 1 if note_index < 4 else 2
                    ordinal = (note_index % 4) + 1
                    expected_digit = row["code"][ordinal - 1]
                    expected_position = positions[cell - 1]
                    expected_fret = (5 if expected_position == "P5" else 7) + int(expected_digit) - 1
                    require(note["string"] == string_name and note["cell_ordinal"] == cell and note["note_ordinal"] == ordinal and note["route_note_ordinal"] == note_index + 1 and note["source_sequence_ordinal"] == route_index * 8 + note_index + 1, "NOTE_ORDER")
                    require(note["finger_digit"] == expected_digit and note["position"] == expected_position and note["fret"] == expected_fret, "FINGER_FRET_SOURCE")
                    require(note["onset_q"] is None and note["duration_q"] is None, "UNSUPPORTED_TIMING")
                    string_number, open_midi = STRINGS[string_name]
                    events.append({"event_id": None, "kind": "note", "string": string_number, "fret": expected_fret, "midi": open_midi + expected_fret, "spelling": None, "degree_contexts": {}, "finger": int(expected_digit), "onset_q": None, "duration_q": None, "attack": "picked", "tie_from": None})
            require(len(events) - start == 48, "DIRECTION_EVENT_COUNT")
            local_event_ordinals = list(range(start + 1, len(events) + 1))
            for pick in ("D", "U"):
                label = f"{name}-{pick}"
                variant_fields.append({"id": None, "label": label, "event_ids": None, "source_refs": refs, "route": name, "pick_start": pick, "pick_start_origin": "learner_configuration", "accent_policy": "source_unspecified", "role": "notation_practice", "grouping": {"kind": "unresolved", "notes_per_beat": None, "beat_unit_q": None, "marking_factor": [1, 1], "source_label": "Two practice passes have eighth/subdivision-pause and sixteenth directions, but no fixed quarter-note event grid"}, "tail_pause": None, "unresolved": ["Pass-specific center pause and note-5 accent are source instructions without an allocated timing/accent variant binding."]})
                memberships.append({"label": label, "event_local_ordinals": local_event_ordinals})
        require(len(events) == 96 and len(variant_fields) == 4, "RECORD_EVENT_COUNT")
        tempo_rule = "Begin 10–15 BPM below the learner's clean Level1 same-string tempo; no absolute BPM supplied."
        practice_rules = ["First pass: even eighths; pause one subdivision at center after note4, shift entire hand frame, lightly accent note5. Subdivision duration has no authored quarter-note conversion.", "Second pass: remove pause/accent, then play the 4+4 phrase as straight sixteenths; no authored quarter-note onsets/durations.", "Both directions use D-start and U-start, preserving the same pick direction at the second cell start.", "After three clean loops add 2 BPM next session; after two late landings, fret squeaks, errors or rising tension reduce 4–6 BPM.", "Advance only after full-set clean performance in both directions on two separate days; no automatic mastery inference."]
        fields = {"id": None, "workbook_id": None, "module_id": None, "legacy_level": 8, "title": f"Exercise {number:03d}: {row['code']} — two-position ladder", "kind": "notation", "content_revision": 1, "status": "converted_candidate", "runtime_eligible": False,
                  "source_refs": refs, "authored_text_refs": refs, "normalization": [{"kind": "representation_metadata", "basis": "Closed Level8 whole-source draft and original TXT/PDF", "text": "Two directions each traverse six sequential one-string routes. Each route repeats the full four-note code in P5 and P7; the center barline marks a whole-hand ±2-fret shift after note4, not simultaneous chord tones."}],
                  "context": {"local_code": row["code"], "route": "shift_up E-A-D-G-B-e; shift_down e-B-G-D-A-E", "position": "P5 then P7 or P7 then P5; shift between complete four-note cells", "pick_start": "D or U selected by learner", "pick_start_variants": ["D", "U"], "source_tempo_rules_ref": "L8-TXT1-1-26", "tuning_open_midi": [40, 45, 50, 55, 59, 64], "capo": 0},
                  "events": events, "timing": {"status": "unresolved", "unit": "quarter", "basis": "ASCII spacing, relative BPM and subdivision practice rules do not bind quarter-note event spans", "other_source_requirements": [tempo_rule, *practice_rules]},
                  "rubric": None, "resource_requirements": [], "ambiguities": ["Absolute BPM, event onset/duration and quarter-note beat mapping are unprovided.", "First-pass pause is one subdivision, but no fixed quarter-note duration can be allocated without a selected practice pass/tempo binding."],
                  "control_scope": {"local_case": f"Level8 Exercise {number:03d} {row['code']} whole printed case", "extent": "complete_selected_case", "whole_workbook_complete": False, "source_event_count": 96, "basis_refs": refs, "unresolved": ["Pass-specific timing/accent bindings and identity allocation pending."]},
                  "variants": variant_fields, "lineage": None}
        require(set(fields) == REQUIRED_RECORD_KEYS, "FIELD_SHAPE")
        records.append({"source_local_key": key, "exercise_number": number, "code": row["code"], "schema1_fields": fields, "variant_memberships": memberships, "identity_state": "unallocated", "schema1_importable": False, "open_gaps": OPEN_GAPS})
        source_map.append({"source_local_key": key, "exercise_number": number, "code": row["code"], **source})
    proposal = {"proposal_version": "parallel12-level008-unallocated-schema1-fields.1", "classification": "source_mapped_field_proposal_not_schema1_importable", "legacy_level": 8, "authority": "original_txt_pdf_and_closed_whole_source_draft", "source_pins": {str(path): {"bytes": (root / path).stat().st_size, "sha256": expected} for path, (_, expected) in PINS.items()}, "counts": {"records": 108, "directions": 216, "routes": 1296, "four_note_cells": 2592, "events": 10368, "variant_field_proposals": 432}, "canonical_ids_allocated": False, "runtime_eligible": False, "admitted": False, "records": records}
    handoff = {"version": "parallel12-level008-serial-allocation-handoff.1", "status": "pending_P10_Level7_final_head_then_P02_serial_allocation", "proposal_sha256": digest(serialized(proposal)), "source_map": source_map, "source_checks": {"txt_headings": 108, "txt_printed_route_rows": 1296, "pdf_extracted_headings": 108, "pdf_pages": 10, "ordered_physical_notes": 10368}, "record_count": 108, "event_count": 10368, "variant_count": 432, "required_identity_slots": ["record.id", "record.workbook_id", "record.module_id", "events[].event_id", "variants[].id", "variants[].event_ids", "record.lineage", "candidate_identity_allocation"], "allocation_rule": "Use the then-current reviewed head and every pending reservation; map source-local event ordinals and variant memberships without changing source-derived fields. Never reuse Level5/Level7/Level9 reserved or allocated IDs.", "no_admission": True}
    verify(proposal, handoff)
    return proposal, handoff


def verify(proposal, handoff):
    require(proposal["canonical_ids_allocated"] is False and proposal["runtime_eligible"] is False and proposal["admitted"] is False and handoff["no_admission"] is True, "INVALID_AUTHORITY")
    require(len(proposal["records"]) == 108 and handoff["record_count"] == 108 and handoff["event_count"] == 10368 and handoff["variant_count"] == 432, "COVERAGE")
    keys = [r["source_local_key"] for r in proposal["records"]]
    require(len(set(keys)) == 108 and keys == [f"L8-set{(i // 12) + 1:02d}-ex{i + 1:03d}" for i in range(108)], "CASE_MISSING_OR_DUPLICATE")
    require([s["source_local_key"] for s in handoff["source_map"]] == keys, "SOURCE_MAP_COVERAGE")
    for record in proposal["records"]:
        fields = record["schema1_fields"]
        require(set(fields) == REQUIRED_RECORD_KEYS and record["identity_state"] == "unallocated" and record["schema1_importable"] is False, "FIELD_SHAPE")
        require(all(fields[k] is None for k in ("id", "workbook_id", "module_id", "lineage")), "INVALID_AUTHORITY")
        require(fields["status"] == "converted_candidate" and fields["runtime_eligible"] is False and fields["timing"]["status"] == "unresolved", "INVALID_AUTHORITY")
        require(len(fields["events"]) == 96 and len(fields["variants"]) == 4 and len(record["variant_memberships"]) == 4, "RECORD_COVERAGE")
        require(all(e["event_id"] is None and e["onset_q"] is None and e["duration_q"] is None for e in fields["events"]), "UNSUPPORTED_TIMING_OR_ID")
        require(all(v["id"] is None and v["event_ids"] is None and v["grouping"]["kind"] == "unresolved" and v["grouping"]["notes_per_beat"] is None and v["grouping"]["beat_unit_q"] is None for v in fields["variants"]), "UNSUPPORTED_TIMING_OR_ID")
        require([m["label"] for m in record["variant_memberships"]] == [v["label"] for v in fields["variants"]], "VARIANT_MEMBERSHIP")
        require(record["variant_memberships"][0]["event_local_ordinals"] == list(range(1, 49)) and record["variant_memberships"][2]["event_local_ordinals"] == list(range(49, 97)), "VARIANT_MEMBERSHIP")
    require(handoff["proposal_sha256"] == digest(serialized(proposal)), "PROPOSAL_HASH")
    require(handoff["source_checks"] == {"txt_headings": 108, "txt_printed_route_rows": 1296, "pdf_extracted_headings": 108, "pdf_pages": 10, "ordered_physical_notes": 10368}, "SOURCE_CHECK_COVERAGE")
    return proposal["counts"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("build", "verify"))
    command = parser.parse_args().command
    proposal, handoff = build()
    if command == "build":
        (ROOT / OUT).mkdir(parents=True, exist_ok=True)
        (ROOT / OUT / "field-proposal.json").write_bytes(serialized(proposal))
        (ROOT / OUT / "allocation-handoff.json").write_bytes(serialized(handoff))
    else:
        require((ROOT / OUT / "field-proposal.json").read_bytes() == serialized(proposal), "OUTPUT_DRIFT proposal")
        require((ROOT / OUT / "allocation-handoff.json").read_bytes() == serialized(handoff), "OUTPUT_DRIFT handoff")
    print(json.dumps({"status": "unallocated_nonadmitted_field_proposal", "counts": verify(proposal, handoff)}, sort_keys=True))


if __name__ == "__main__":
    main()
