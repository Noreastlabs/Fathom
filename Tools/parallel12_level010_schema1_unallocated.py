#!/usr/bin/env python3
"""Full-Level10 source-to-schema1 field proposal without canonical allocation."""

import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path("Build/parallel-12/2.3.1.1.1-level010-whole-normalization-r01/candidate-01.json")
SOURCE_RESULT = Path("Results/parallel-12/conversion/20260923T145207Z-level010-whole-normalization-r01-results.md")
TXT = Path("Notes/music/guitar project/TXT version/108_Finger_Permutations_Level_10_Odd_Count_Position_Transfer.txt")
PDF = Path("Notes/music/guitar project/PDF version/108_Finger_Permutations_Level_10_Odd_Count_Position_Transfer.pdf")
OUT = Path("Build/parallel-12/level010-schema1-unallocated-r01")
PINS = {
    SOURCE: (4823531, "a68c8ba4712b534a1934660e7964def70fd69f6b10de125a95aa6b21d4230732"),
    SOURCE_RESULT: (None, "9e21e47353200d6755714b5585929ea81ec2f21cb0be7e687646929596f256e0"),
    TXT: (136538, "e5ed078c62295adbb5f6bf00e6821e6eee0b2da73ef42c1714421158b5273226"),
    PDF: (81545, "1dafdcd177343f0ea147a5479ad654397d85f4b374cf960e264a230db965496b"),
}
STRINGS = {"E": (1, 40), "A": (2, 45), "D": (3, 50), "G": (4, 55), "B": (5, 59), "e": (6, 64)}
FIELDS = {"id", "workbook_id", "module_id", "legacy_level", "title", "kind", "content_revision", "status", "runtime_eligible", "source_refs", "authored_text_refs", "normalization", "context", "events", "timing", "rubric", "resource_requirements", "ambiguities", "control_scope", "variants", "lineage"}
GAPS = ["canonical item/module/workbook IDs", "canonical event IDs", "canonical variant IDs and memberships", "bound identity allocation and new-record lineage", "absolute starting BPM", "quarter-note onset/duration and beat unit", "first-pass one-subdivision pause in quarter notes", "pass-specific landing accent binding", "triplet/quintuplet pulse-to-quarter mapping"]


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


def check_aggregate(aggregate):
    require(aggregate["level"] == 10 and len(aggregate["records"]) == 108, "CASE_COVERAGE")
    require(aggregate["counts"] == {"records": 108, "modes": 216, "directions": 432, "string_routes": 2592, "untimed_note_positions": 10368}, "AGGREGATE_COUNT")
    require(not aggregate["admitted"] and not aggregate["runtime_eligible"] and not aggregate["imported"] and not aggregate["runtime_admitted"], "INVALID_AUTHORITY")
    require(all(aggregate[k] is None for k in ("canonical_item_id", "canonical_variant_id", "onset_q", "duration_q", "fixed_bpm", "note_per_click")), "UNSUPPORTED_TIMING_OR_ID")


def mode_source(mode, number, code, lines, pages):
    ref = mode["source_refs"]["txt"]
    match = re.fullmatch(r"L10-TXT1-(\d+)-(\d+)", ref)
    require(match is not None, "TXT_REF_SHAPE")
    first, last = map(int, match.groups())
    require(first > 0 and first <= last <= len(lines), "TXT_SPAN")
    passage = lines[first - 1:last]
    require(passage[0] == f"Exercise {number:03d}: {code}", "TXT_HEADING")
    for direction in mode["directions"]:
        for route in direction["routes"]:
            require(route["source_tab_row"] in passage and route["source_finger_row"] in passage, "TXT_PRINTED_ROW")
    pdf_ref = mode["source_refs"]["pdf"]
    pdf_match = re.fullmatch(r"L10-PDF1-p(\d+)", pdf_ref)
    require(pdf_match is not None, "PDF_REF_SHAPE")
    page = int(pdf_match.group(1))
    require(1 <= page <= len(pages) and re.search(rf"\b{number:03d}\b\s+{code}\b", pages[page - 1]) is not None, "PDF_HEADING")
    for direction in mode["directions"]:
        first_route = direction["routes"][0]
        require(first_route["pdf_tab_template"] in pages[page - 1] and first_route["pdf_finger_template"] in pages[page - 1], "PDF_TEMPLATE")
    return {"txt": ref, "pdf": pdf_ref, "txt_passage_sha256": digest("\n".join(passage).encode()), "pdf_page": page}


def build(root=ROOT, aggregate_override=None):
    check_pins(root)
    aggregate = aggregate_override if aggregate_override is not None else json.loads((root / SOURCE).read_text())
    check_aggregate(aggregate)
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise ProposalError("PDF_EXTRACTOR_MISSING: run with bundled workspace Python") from exc
    pages = [p.extract_text() for p in PdfReader(str(root / PDF)).pages]
    require(len(pages) == 19, "PDF_PAGE_COUNT")
    lines = (root / TXT).read_text().splitlines()
    require(lines[5] == "MOVEMENT RULE" and lines[20] == "PICKING RULE" and lines[25] == "PRACTICE RULE", "SOURCE_INSTRUCTIONS")
    introduction = "\n".join(lines[:33])
    require("triplet and quintuplet" in introduction and "does not restart" in introduction and "pause one subdivision" in introduction, "SOURCE_INSTRUCTIONS")
    records, source_map, seen = [], [], set()
    for index, row in enumerate(aggregate["records"]):
        number = index + 1
        key = f"L10-set{(index // 12) + 1:02d}-ex{number:03d}"
        require(row["source_local_key"] == key and row["exercise_number"] == f"{number:03d}" and key not in seen, "CASE_MISSING_OR_DUPLICATE")
        seen.add(key)
        code = row["code"]
        require(re.fullmatch(r"[1-4]{4}", code) is not None and not row["admitted"] and not row["runtime_eligible"] and not row["imported"], "CASE_AUTHORITY")
        require(all(row[k] is None for k in ("canonical_item_id", "canonical_variant_id", "fixed_bpm", "note_per_click", "onset_q", "duration_q")), "UNSUPPORTED_TIMING_OR_ID")
        require(len(row["modes"]) == 2, "MODE_COUNT")
        events, variants, memberships, mode_refs = [], [], [], []
        for mode_index, mode in enumerate(row["modes"]):
            mode_name = ("mode_a", "mode_b")[mode_index]
            shift_after = 3 if mode_index == 0 else 1
            landing = shift_after + 1
            require(mode["mode"] == mode_name and mode["shift_after_note"] == shift_after and mode["landing_note_ordinal"] == landing and len(mode["directions"]) == 2, "MODE_SEMANTICS")
            source = mode_source(mode, number, code, lines, pages)
            mode_refs.append({"mode": mode_name, **source})
            for direction_index, direction in enumerate(mode["directions"]):
                direction_name = ("shift_up", "shift_down")[direction_index]
                route_order = ["E", "A", "D", "G", "B", "e"] if direction_index == 0 else ["e", "B", "G", "D", "A", "E"]
                positions = ["P5", "P7"] if direction_index == 0 else ["P7", "P5"]
                require(direction["direction"] == direction_name and direction["route_order"] == route_order and direction["position_order"] == positions and len(direction["routes"]) == 6, "DIRECTION_ROUTE")
                start = len(events)
                for route_index, route in enumerate(direction["routes"]):
                    string_name = route_order[route_index]
                    require(route["string"] == string_name and route["route_ordinal"] == route_index + 1 and route["shift_after_note"] == shift_after and route["landing_note_ordinal"] == landing and len(route["notes"]) == 4, "ROUTE_SEMANTICS")
                    for note_index, note in enumerate(route["notes"]):
                        ordinal = note_index + 1
                        position = positions[0 if ordinal <= shift_after else 1]
                        digit = code[note_index]
                        fret = (5 if position == "P5" else 7) + int(digit) - 1
                        require(note["ordinal"] == ordinal and note["string"] == string_name and note["position"] == position and note["finger_digit"] == digit and note["fret"] == fret, "PHYSICAL_NOTE")
                        require(note["landing"] is (ordinal == landing), "LANDING_NOTE")
                        require(note["onset_q"] is None and note["duration_q"] is None, "UNSUPPORTED_TIMING")
                        string_number, open_midi = STRINGS[string_name]
                        events.append({"event_id": None, "kind": "note", "string": string_number, "fret": fret, "midi": open_midi + fret, "spelling": None, "degree_contexts": {}, "finger": int(digit), "onset_q": None, "duration_q": None, "attack": "picked", "tie_from": None})
                require(len(events) - start == 24, "DIRECTION_EVENT_COUNT")
                local_ordinals = list(range(start + 1, len(events) + 1))
                refs = [source["txt"], source["pdf"], "L10-TXT1-1-33"]
                for pick in ("D", "U"):
                    label = f"{mode_name}-{direction_name}-{pick}"
                    variants.append({"id": None, "label": label, "event_ids": None, "source_refs": refs, "route": f"{mode_name} {direction_name}", "pick_start": pick, "pick_start_origin": "learner_configuration", "accent_policy": "source_unspecified", "role": "notation_practice", "grouping": {"kind": "unresolved", "notes_per_beat": None, "beat_unit_q": None, "marking_factor": [1, 1], "source_label": "Practice passes specify eighths, pause, sixteenths and later pulses without a fixed quarter-note event grid"}, "tail_pause": None, "unresolved": ["Pass-specific landing accent/pause and uninterrupted alternate-picking cycle require later binding."]})
                    memberships.append({"label": label, "event_local_ordinals": local_ordinals, "landing_event_local_ordinals": [start + route_index * 4 + landing for route_index in range(6)]})
        require(len(events) == 96 and len(variants) == 8, "CASE_EVENT_COUNT")
        refs = [mode_refs[0]["txt"], mode_refs[0]["pdf"], mode_refs[1]["txt"], mode_refs[1]["pdf"], "L10-TXT1-1-33"]
        rules = ["Mode A shifts after note3 and lands on note4; Mode B shifts after note1 and lands on note2; neither landing implies melodic interval direction.", "Strict alternate picking continues through the shift barline without restart, reversal or reset: Mode A D-U-D|U or U-D-U|D; Mode B D|U-D-U or U|D-U-D.", "Begin 8–12 BPM below the learner's clean Level9 continuous tempo; no absolute BPM supplied.", "Pass1 even eighths, one-subdivision shift pause and light landing-note accent; no authored quarter-note duration for that pause.", "Pass2 removes pause/accent, connects straight eighths then straight sixteenths; no authored quarter-note event spans.", "After three clean loops add 2 BPM next session; after two late landings, slides, squeaks, errors or rising tension reduce 4–6 BPM; advance after both modes/both directions clean on two separate days.", "Later restore existing triplet and quintuplet pulses without moving the code-bound shift point to match the beat; pulse-to-quarter binding remains unresolved."]
        fields = {"id": None, "workbook_id": None, "module_id": None, "legacy_level": 10, "title": f"Exercise {number:03d}: {code} — odd-count position transfer", "kind": "notation", "content_revision": 1, "status": "converted_candidate", "runtime_eligible": False,
                  "source_refs": refs, "authored_text_refs": refs, "normalization": [{"kind": "representation_metadata", "basis": "Closed whole-Level10 source aggregate and original TXT/PDF", "text": "Mode A 3+1 and Mode B 1+3 are distinct printed cases. Each UP/DOWN direction traverses six sequential one-string routes; the center barline marks a whole-hand frame shift at a code-bound note, never simultaneous chord tones or a pick-cycle reset."}],
                  "context": {"local_code": code, "route": "Mode A/B; shift_up E-A-D-G-B-e; shift_down e-B-G-D-A-E", "position": "P5→P7 or P7→P5; shift after note3 in A or note1 in B", "pick_start": "D or U selected by learner; strict alternation continues across shift", "pick_start_variants": ["D", "U"], "source_tempo_rules_ref": "L10-TXT1-1-33", "tuning_open_midi": [40, 45, 50, 55, 59, 64], "capo": 0},
                  "events": events, "timing": {"status": "unresolved", "unit": "quarter", "basis": "Relative tempo, ASCII shift barline and pass-specific subdivisions do not define quarter-note event spans", "other_source_requirements": rules},
                  "rubric": None, "resource_requirements": [], "ambiguities": ["Absolute BPM, quarter-note onset/duration and metrical beat mapping are unprovided.", "First-pass pause is one subdivision without an authored quarter-note conversion; landing accent and later triplet/quintuplet pulses lack pass-specific schema1 bindings."],
                  "control_scope": {"local_case": f"Level10 Exercise {number:03d} {code} both printed modes/directions", "extent": "complete_selected_case", "whole_workbook_complete": False, "source_event_count": 96, "basis_refs": refs, "unresolved": ["Pass-specific timing/accent, pulse and identity allocation pending."]},
                  "variants": variants, "lineage": None}
        require(set(fields) == FIELDS, "FIELD_SHAPE")
        records.append({"source_local_key": key, "exercise_number": number, "code": code, "mode_source_refs": mode_refs, "schema1_fields": fields, "variant_memberships": memberships, "identity_state": "unallocated", "schema1_importable": False, "fixed_bpm": None, "note_per_click": None, "onset_q": None, "duration_q": None, "open_gaps": GAPS})
        source_map.append({"source_local_key": key, "exercise_number": number, "code": code, "modes": mode_refs})
    proposal = {"proposal_version": "parallel12-level010-unallocated-schema1-fields.1", "classification": "source_mapped_field_proposal_not_schema1_importable", "legacy_level": 10, "source_pins": {str(path): {"bytes": (root / path).stat().st_size, "sha256": expected} for path, (_, expected) in PINS.items()}, "counts": {"records": 108, "mode_cases": 216, "directions": 432, "routes": 2592, "events": 10368, "variant_field_proposals": 864}, "canonical_ids_allocated": False, "runtime_eligible": False, "admitted": False, "fixed_bpm": None, "note_per_click": None, "onset_q": None, "duration_q": None, "records": records}
    handoff = {"version": "parallel12-level010-serial-allocation-handoff.1", "status": "pending_sharded_identity_architecture_then_P02_serial_allocation", "proposal_sha256": digest(serialized(proposal)), "source_map": source_map, "source_checks": {"txt_mode_headings": 216, "txt_printed_route_rows": 2592, "txt_finger_rows": 2592, "pdf_extracted_mode_headings": 216, "pdf_template_checks": 432, "pdf_pages": 19, "ordered_physical_notes": 10368}, "record_count": 108, "event_count": 10368, "variant_count": 864, "required_identity_slots": ["record.id", "record.workbook_id", "record.module_id", "events[].event_id", "variants[].id", "variants[].event_ids", "record.lineage", "candidate_identity_allocation"], "allocation_rule": "Use the later reviewed sharded current head and all pending reservations; map source-local event/landing ordinals and variant memberships without changing musical source fields. Do not assemble a monolithic overlay or retry the known JSON value cap.", "no_admission": True}
    verify(proposal, handoff)
    return proposal, handoff


def verify(proposal, handoff):
    require(proposal["canonical_ids_allocated"] is False and proposal["runtime_eligible"] is False and proposal["admitted"] is False and handoff["no_admission"] is True, "INVALID_AUTHORITY")
    require(all(proposal[k] is None for k in ("fixed_bpm", "note_per_click", "onset_q", "duration_q")), "UNSUPPORTED_TIMING")
    require(len(proposal["records"]) == 108 and handoff["record_count"] == 108 and handoff["event_count"] == 10368 and handoff["variant_count"] == 864, "COVERAGE")
    keys = [r["source_local_key"] for r in proposal["records"]]
    require(len(set(keys)) == 108 and keys == [f"L10-set{(i // 12) + 1:02d}-ex{i + 1:03d}" for i in range(108)], "CASE_MISSING_OR_DUPLICATE")
    require([s["source_local_key"] for s in handoff["source_map"]] == keys, "SOURCE_MAP_COVERAGE")
    for record in proposal["records"]:
        require(all(record[k] is None for k in ("fixed_bpm", "note_per_click", "onset_q", "duration_q")), "UNSUPPORTED_TIMING")
        fields = record["schema1_fields"]
        require(set(fields) == FIELDS and record["identity_state"] == "unallocated" and record["schema1_importable"] is False, "FIELD_SHAPE")
        require(all(fields[k] is None for k in ("id", "workbook_id", "module_id", "lineage")), "INVALID_AUTHORITY")
        require(fields["status"] == "converted_candidate" and fields["runtime_eligible"] is False and fields["timing"]["status"] == "unresolved", "INVALID_AUTHORITY")
        require(len(fields["events"]) == 96 and len(fields["variants"]) == 8 and len(record["variant_memberships"]) == 8 and len(record["mode_source_refs"]) == 2, "CASE_EVENT_COUNT")
        require(all(e["event_id"] is None and e["onset_q"] is None and e["duration_q"] is None for e in fields["events"]), "UNSUPPORTED_TIMING_OR_ID")
        require(all(v["id"] is None and v["event_ids"] is None and v["grouping"]["kind"] == "unresolved" and v["grouping"]["notes_per_beat"] is None and v["grouping"]["beat_unit_q"] is None for v in fields["variants"]), "UNSUPPORTED_TIMING_OR_ID")
        require([m["label"] for m in record["variant_memberships"]] == [v["label"] for v in fields["variants"]], "VARIANT_MEMBERSHIP")
        require([m["event_local_ordinals"][0] for m in record["variant_memberships"]] == [1, 1, 25, 25, 49, 49, 73, 73], "VARIANT_MEMBERSHIP")
        require([m["landing_event_local_ordinals"][0] for m in record["variant_memberships"]] == [4, 4, 28, 28, 50, 50, 74, 74], "LANDING_MEMBERSHIP")
    require(handoff["proposal_sha256"] == digest(serialized(proposal)), "PROPOSAL_HASH")
    require(handoff["source_checks"] == {"txt_mode_headings": 216, "txt_printed_route_rows": 2592, "txt_finger_rows": 2592, "pdf_extracted_mode_headings": 216, "pdf_template_checks": 432, "pdf_pages": 19, "ordered_physical_notes": 10368}, "SOURCE_CHECK_COVERAGE")
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
