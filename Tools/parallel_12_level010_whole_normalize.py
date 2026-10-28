#!/usr/bin/env python3
"""Pinned whole-Level10 detached normalization of four released candidates."""

from __future__ import annotations

import argparse
import json
from io import BytesIO
from pathlib import Path
from typing import Any

from pypdf import PdfReader

from parallel_12_level010_set03_candidate import (
    CandidateError, DOWN_LABEL, FINGER_NAMES, HEADING, HIGH_TO_LOW, MODES,
    PDF, PDF_HEADING, PDF_PIN, POSITIONS, ROOT, ROUTE_ORDER, TXT, TXT_PIN,
    UP_LABEL, digest, local_bytes, parse_cell, require, verify,
)

OUTPUT_ROOT = Path("Build/parallel-12/2.3.1.1.1-level010-whole-normalization-r01")
INPUTS = (
    (1, 1, Path("Build/parallel-09/2.3.1.1.1-level010-set01-r01/candidate-01.json"),
     (746234, "6b9c1ad832a633d0da5872e9dd3b5a086e7a89fa66440046cb4c058b1e6521c3"),
     "fathom-level010-set01-detached-candidate-v1"),
    (2, 2, Path("Build/parallel-10/2.3.1.1.1-level010-set02-r01/candidate-01.json"),
     (191248, "271d47f36b2235a36609542d7cbf4c386a9b3e80a9b7e89dadcd9371eea1f759"),
     "fathom-detached-source-candidate.1"),
    (3, 3, Path("Build/parallel-12/2.3.1.1.1-level010-set03-r01/candidate-01.json"),
     (291878, "f306c4dfeaf6ffd4ad3d377d1962f37fce3952d628a7f579ef33c30a41531bce"),
     "fathom-level010-set03-detached-candidate-v1"),
    (4, 9, Path("Build/parallel-12/2.3.1.1.1-level010-sets04-09-r01/candidate-01.json"),
     (1744935, "91b30e6fb13cad0711d463f09fd4e21fe676a49cafce09cd88deef978deaa353"),
     "fathom-level010-sets04-09-detached-candidate-v1"),
)
MODE_ORDER = ("mode_a", "mode_b")
DIRECTION_ORDER = ("shift_up", "shift_down")


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def verify_document_shape(value: dict[str, Any], first: int, last: int, schema: str) -> None:
    require(value.get("level") == 10 and value.get("schema") == schema and
            len(value.get("records", [])) == 12 * (last - first + 1) and
            (value.get("set") == first if first == last else value.get("sets") == list(range(first, last + 1))),
            f"INPUT_ROOT_SHAPE {first}_{last}")
    if first == 2:
        require(all(value.get(key) is False for key in
                    ("canonical_identity_assigned", "curriculum_reviewed",
                     "runtime_import_authorized", "timing_interpreted")), "INPUT_ROOT_ADMISSION 2")
    else:
        require(all(value.get(key) is False for key in
                    ("runtime_eligible", "runtime_admitted", "imported", "admitted",
                     "whole_workbook_complete")), f"INPUT_ROOT_ADMISSION {first}_{last}")


def load_inputs(root: Path = ROOT) -> tuple[bytes, bytes, list[dict[str, Any]]]:
    txt_data, pdf_data = local_bytes(root, TXT), local_bytes(root, PDF)
    verify(txt_data, TXT_PIN, "LEVEL10_TXT")
    verify(pdf_data, PDF_PIN, "LEVEL10_PDF")
    docs = []
    for first, last, path, pin, schema in INPUTS:
        data = local_bytes(root, path)
        verify(data, pin, f"RELEASED_SETS_{first}_{last}")
        try:
            value = json.loads(data)
        except (ValueError, UnicodeDecodeError) as exc:
            raise CandidateError(f"INPUT_JSON_INVALID {first}_{last}") from exc
        verify_document_shape(value, first, last, schema)
        docs.append(value)
    return txt_data, pdf_data, docs


def source_cards(txt_data: bytes, pdf_data: bytes) -> dict[tuple[int, str], dict[str, Any]]:
    try:
        lines = txt_data.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise CandidateError("TXT_ENCODING_INVALID") from exc
    require(len(lines) == 4065 and lines[0] ==
            "108 FINGER PERMUTATIONS - LEVEL 10: ODD-COUNT POSITION TRANSFER", "TXT_TITLE_OR_EOF")
    introduction = "\n".join(lines[:40])
    for phrase in ("Mode A - 3+1 late shift", "Mode B - 1+3 early shift",
                   "The landing note is note 4", "The landing note is note 2",
                   "The barline marks the position shift only", "not the melodic interval",
                   "one string at a time"):
        require(phrase in introduction, f"TXT_INSTRUCTION {phrase}")
    try:
        reader = PdfReader(BytesIO(pdf_data), strict=True)
        require(len(reader.pages) == 19, "PDF_PAGE_COUNT")
        pdf_lines = {page: (reader.pages[page - 1].extract_text() or "").splitlines()
                     for page in range(2, 20)}
    except CandidateError:
        raise
    except Exception as exc:
        raise CandidateError("PDF_READ_FAILED") from exc
    cards = {}
    all_codes = []
    for set_number in range(1, 10):
        header = 36 + 448 * (set_number - 1)
        first = 12 * (set_number - 1) + 1
        last = first + 11
        require(lines[header - 1] == f"SET {set_number} OF 9 - EXERCISES {first:03d}-{last:03d}",
                f"TXT_SET_HEADER {set_number}")
        for mode in MODE_ORDER:
            spec = MODES[mode]
            offset = 0 if mode == "mode_a" else 222
            mode_heading = header + 4 + offset
            require(lines[mode_heading - 1] == spec["txt_label"] and
                    lines[mode_heading + 1] == spec["picking"], f"TXT_MODE_HEADER {set_number} {mode}")
            page = 2 * set_number + (0 if mode == "mode_a" else 1)
            pdf = pdf_lines[page]
            label = "Mode A - 3+1 Late Shift" if mode == "mode_a" else "Mode B - 1+3 Early Shift"
            intro = ("Digits 1-3 stay in the source frame; digit 4 lands in the destination frame."
                     if mode == "mode_a" else
                     "Digit 1 starts in the source frame; digits 2-4 continue in the destination frame.")
            require(len(pdf) == 137 and pdf[0] == "Level 10 - Odd-Count Position Transfer" and
                    pdf[1] == f"Set {set_number} of 9 - {label} - Exercises {first:03d}-{last:03d}" and
                    pdf[2] == intro and
                    pdf[-2] == "Standard tuning. P5 = frets 5-8; P7 = frets 7-10. Shift after note 3 in Mode A or after note 1 in Mode B." and
                    pdf[-1] == f"Page {page} of 19", f"PDF_MODE_PAGE {set_number} {mode}")
            for index in range(12):
                number = first + index
                txt_start = header + 9 + offset + 18 * index
                block = lines[txt_start - 1:txt_start + 16]
                pdf_block = pdf[3 + index * 11:3 + (index + 1) * 11]
                text_heading = HEADING.fullmatch(block[0]) if block else None
                page_heading = PDF_HEADING.fullmatch(pdf_block[0]) if pdf_block else None
                require(len(block) == 17 and len(pdf_block) == 11 and
                        text_heading is not None and page_heading is not None and
                        text_heading.groups() == page_heading.groups() and
                        text_heading.group(1) == f"{number:03d}" and
                        block[1] == UP_LABEL[mode] and block[9] == DOWN_LABEL[mode] and
                        pdf_block[1] == spec["pdf_label"] and
                        pdf_block[2:4] == ["UP", "E>A>D>G>B>e   P5>P7"] and
                        pdf_block[6:8] == ["DN", "e>B>G>D>A>E   P7>P5"] and
                        pdf_block[10] == f"landing note {spec['landing']}; no pick reset",
                        f"SOURCE_CARD_SHAPE {number:03d} {mode}")
                code = text_heading.group(2)
                if mode == "mode_a":
                    all_codes.append(code)
                else:
                    require(cards[(number, "mode_a")]["code"] == code,
                            f"SOURCE_MODE_CODE_MISMATCH {number:03d}")
                directions = {}
                for direction, finger, rows, pdf_finger, pdf_tab in (
                    ("shift_up", block[2], block[3:9], pdf_block[4], pdf_block[5]),
                    ("shift_down", block[10], block[11:17], pdf_block[8], pdf_block[9]),
                ):
                    require(len(rows) == 6 and tuple(row[0] for row in rows) == HIGH_TO_LOW and
                            finger == pdf_finger and all("S" + row[1:] == pdf_tab for row in rows),
                            f"SOURCE_TAB_PARITY {number:03d} {mode} {direction}")
                    require(parse_cell(finger, "F", code, mode, direction) == list(map(int, code)),
                            f"SOURCE_FINGER {number:03d} {mode} {direction}")
                    for string, row in zip(HIGH_TO_LOW, rows, strict=True):
                        parse_cell(row, string, code, mode, direction)
                    directions[direction] = {"finger_row": finger, "rows_high_to_low": rows,
                                             "pdf_finger_template": pdf_finger,
                                             "pdf_tab_template": pdf_tab}
                cards[(number, mode)] = {"code": code, "set": set_number,
                                         "txt_start_line": txt_start, "txt_end_line": txt_start + 16,
                                         "pdf_page": page, "directions": directions}
    require(len(cards) == 216 and len(all_codes) == len(set(all_codes)) == 108, "SOURCE_COVERAGE")
    return cards


def input_modes(record: dict[str, Any], set_number: int, number: int,
                code: str) -> dict[str, dict[str, Any]]:
    modes = record.get("modes")
    require(isinstance(modes, list) and len(modes) == 2, f"CANDIDATE_MODE_COUNT {number:03d}")
    result = {}
    for item in modes:
        raw = item.get("mode")
        mode = {"A": "mode_a", "B": "mode_b", "mode_a": "mode_a", "mode_b": "mode_b"}.get(raw)
        require(mode in MODE_ORDER and mode not in result, f"CANDIDATE_MODE_DUPLICATE {number:03d}")
        spec = MODES[mode]
        require(item.get("shift_after_note") == spec["shift_after"] and
                item.get("landing_note", item.get("landing_note_index", item.get("landing_note_ordinal"))) == spec["landing"],
                f"CANDIDATE_LANDING {number:03d} {mode}")
        if set_number == 2:
            require(item.get("code") == code, f"CANDIDATE_MODE_CODE {number:03d}")
        result[mode] = item
    require(set(result) == set(MODE_ORDER), f"CANDIDATE_MODE_COVERAGE {number:03d}")
    return result


def candidate_direction(mode_item: dict[str, Any], set_number: int,
                        direction: str, number: int) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    if set_number == 2:
        routes = mode_item.get("routes")
        require(isinstance(routes, list) and len(routes) == 12 and
                [route.get("direction") for route in routes] == ["UP"] * 6 + ["DOWN"] * 6,
                f"CANDIDATE_ROUTE_COUNT {number:03d}")
        label = "UP" if direction == "shift_up" else "DOWN"
        selected = [route for route in routes if route.get("direction") == label]
        require(len(selected) == 6, f"CANDIDATE_DIRECTION_COVERAGE {number:03d} {direction}")
        return None, selected
    directions = mode_item.get("directions")
    require(isinstance(directions, list) and len(directions) == 2 and
            [entry.get("direction") for entry in directions] == list(DIRECTION_ORDER),
            f"CANDIDATE_DIRECTION_COVERAGE {number:03d}")
    item = directions[DIRECTION_ORDER.index(direction)]
    routes = item.get("string_routes") if set_number == 1 else item.get("routes")
    require(isinstance(routes, list) and len(routes) == 6, f"CANDIDATE_ROUTE_COUNT {number:03d} {direction}")
    return item, routes


def normalize_route(route: dict[str, Any], direction_item: dict[str, Any] | None,
                    set_number: int, mode: str, direction: str, number: int,
                    ordinal: int, code: str, card: dict[str, Any]) -> dict[str, Any]:
    string = ROUTE_ORDER[direction][ordinal - 1]
    source = card["directions"][direction]
    row = source["rows_high_to_low"][HIGH_TO_LOW.index(string)]
    finger_row = source["finger_row"]
    pdf_tab = source["pdf_tab_template"]
    pdf_finger = source["pdf_finger_template"]
    shift = MODES[mode]["shift_after"]
    landing = MODES[mode]["landing"]
    positions = list(POSITIONS[direction])
    expected_positions = [positions[0]] * shift + [positions[1]] * (4 - shift)
    expected_frets = parse_cell(row, string, code, mode, direction)
    require(route.get("string") == string, f"CANDIDATE_ROUTE_ORDER {number:03d} {mode} {direction}")
    if set_number == 1:
        require(direction_item is not None and
                direction_item.get("string_order") == list(ROUTE_ORDER[direction]) and
                direction_item.get("position_order") == positions and
                direction_item.get("tab_rows_printed") == source["rows_high_to_low"] and
                direction_item.get("finger_row_printed") == finger_row and
                direction_item.get("pdf_finger_template") == pdf_finger and
                direction_item.get("pdf_tab_template") == pdf_tab and
                route.get("tab_row") == row and route.get("shift_after_note") == shift and
                route.get("landing_note") == landing and
                route.get("shift_frets") == (2 if direction == "shift_up" else -2),
                f"CANDIDATE_ROUTE_SOURCE {number:03d} {mode} {direction} {string}")
        cells = route.get("cells")
        require(isinstance(cells, list) and len(cells) == 2 and
                [cell.get("position") for cell in cells] == positions and
                [len(cell.get("notes", [])) for cell in cells] == [shift, 4 - shift],
                f"CANDIDATE_CELLS {number:03d} {mode} {direction} {string}")
        raw_notes = [note for cell in cells for note in cell["notes"]]
        note_map = lambda note: (note.get("ordinal"), note.get("finger_digit"), note.get("finger_name"),
                                 note.get("position"), note.get("fret"), note.get("string"),
                                 note.get("is_landing_note"), note.get("onset_q"), note.get("duration_q"))
    elif set_number == 2:
        require(route.get("direction") == ("UP" if direction == "shift_up" else "DOWN") and
                route.get("play_order") == ordinal and route.get("txt_tab_row") == row and
                route.get("txt_finger_row") == finger_row and
                route.get("pdf_tab_template") == pdf_tab and
                route.get("pdf_finger_template") == pdf_finger and
                route.get("pdf_page") == card["pdf_page"] and
                route.get("txt_finger_line") == card["txt_start_line"] + (2 if direction == "shift_up" else 10) and
                route.get("txt_tab_line") == card["txt_start_line"] +
                ((3 + HIGH_TO_LOW.index(string)) if direction == "shift_up" else
                 (11 + HIGH_TO_LOW.index(string))),
                f"CANDIDATE_ROUTE_SOURCE {number:03d} {mode} {direction} {string}")
        raw_notes = route.get("notes")
        note_map = lambda note: (note.get("note_index"), str(note.get("finger")),
                                 FINGER_NAMES.get(str(note.get("finger"))), note.get("frame"),
                                 note.get("fret"), note.get("string"), note.get("landing_note"), None, None)
    else:
        require(direction_item is not None and
                direction_item.get("route_order") == list(ROUTE_ORDER[direction]) and
                direction_item.get("position_order") == positions and
                direction_item.get("source_rows_high_to_low") == source["rows_high_to_low"] and
                direction_item.get("source_finger_row") == finger_row and
                direction_item.get("pdf_finger_template") == pdf_finger and
                direction_item.get("pdf_tab_template") == pdf_tab and
                route.get("route_ordinal") == ordinal and route.get("source_tab_row") == row and
                route.get("source_finger_row") == finger_row and
                route.get("pdf_tab_template") == pdf_tab and
                route.get("pdf_finger_template") == pdf_finger and
                route.get("shift_after_note") == shift and
                route.get("landing_note") == {"ordinal": landing,
                                              "position": expected_positions[landing - 1],
                                              "finger_digit": code[landing - 1],
                                              "fret": expected_frets[landing - 1]},
                f"CANDIDATE_ROUTE_SOURCE {number:03d} {mode} {direction} {string}")
        raw_notes = route.get("notes")
        note_map = lambda note: (note.get("ordinal"), note.get("finger_digit"), note.get("finger_name"),
                                 note.get("position"), note.get("fret"), note.get("string"),
                                 note.get("landing"), note.get("onset_q"), note.get("duration_q"))
    require(isinstance(raw_notes, list) and len(raw_notes) == 4,
            f"CANDIDATE_NOTE_COUNT {number:03d} {mode} {direction} {string}")
    notes = []
    for index, raw_note in enumerate(raw_notes):
        expected = (index + 1, code[index], FINGER_NAMES[code[index]], expected_positions[index],
                    expected_frets[index], string, index + 1 == landing, None, None)
        require(note_map(raw_note) == expected,
                f"CANDIDATE_NOTE_MISMATCH {number:03d} {mode} {direction} {string} {index + 1}")
        notes.append({"ordinal": index + 1, "finger_digit": code[index],
                      "finger_name": FINGER_NAMES[code[index]], "position": expected_positions[index],
                      "fret": expected_frets[index], "string": string, "landing": index + 1 == landing,
                      "onset_q": None, "duration_q": None})
    return {"route_ordinal": ordinal, "string": string, "source_tab_row": row,
            "source_finger_row": finger_row, "pdf_tab_template": pdf_tab,
            "pdf_finger_template": pdf_finger, "shift_after_note": shift,
            "landing_note_ordinal": landing, "notes": notes}


def normalize_record(record: dict[str, Any], set_number: int, number: int,
                     card_index: dict[tuple[int, str], dict[str, Any]],
                     source_path: Path, source_pin: tuple[int, str]) -> dict[str, Any]:
    number_str = f"{number:03d}"
    code = card_index[(number, "mode_a")]["code"]
    raw_number = record.get("exercise_number")
    require(raw_number in (number, number_str) and
            record.get("code", record.get("finger_code")) == code and
            (record.get("set", set_number) == set_number),
            f"CANDIDATE_RECORD_IDENTITY {number_str}")
    if set_number == 2:
        require(record.get("admitted") is False and record.get("runtime_eligible") is False and
                all(record.get(key) is None for key in
                    ("canonical_item_id", "onset", "duration", "fixed_bpm", "note_per_click")),
                f"CANDIDATE_RECORD_ADMISSION {number_str}")
    else:
        require(all(record.get(key) is False for key in
                    ("runtime_eligible", "runtime_admitted", "imported", "admitted")) and
                all(record.get(key) is None for key in
                    ("canonical_item_id", "canonical_variant_id", "onset_q", "duration_q",
                     "fixed_bpm", "note_per_click")), f"CANDIDATE_RECORD_ADMISSION {number_str}")
    modes = input_modes(record, set_number, number, code)
    normalized_modes = []
    for mode in MODE_ORDER:
        item = modes[mode]
        card = card_index[(number, mode)]
        ref = {"txt": f"L10-TXT1-{card['txt_start_line']}-{card['txt_end_line']}",
               "pdf": f"L10-PDF1-p{card['pdf_page']}"}
        if set_number == 1 or set_number >= 3:
            require(item.get("source_refs") == ref, f"CANDIDATE_SOURCE_REF {number_str} {mode}")
        else:
            require(item.get("txt_card_line") == card["txt_start_line"] and
                    item.get("pdf_page") == card["pdf_page"],
                    f"CANDIDATE_SOURCE_REF {number_str} {mode}")
        directions = []
        for direction in DIRECTION_ORDER:
            direction_item, raw_routes = candidate_direction(item, set_number, direction, number)
            if set_number == 2:
                require([route.get("direction") for route in raw_routes] ==
                        ["UP" if direction == "shift_up" else "DOWN"] * 6,
                        f"CANDIDATE_DIRECTION_ORDER {number_str} {mode}")
            routes = [normalize_route(route, direction_item, set_number, mode, direction,
                                      number, ordinal, code, card)
                      for ordinal, route in enumerate(raw_routes, 1)]
            directions.append({"direction": direction, "route_order": list(ROUTE_ORDER[direction]),
                               "position_order": list(POSITIONS[direction]), "routes": routes})
        normalized_modes.append({"mode": mode, "shift_after_note": MODES[mode]["shift_after"],
                                 "landing_note_ordinal": MODES[mode]["landing"],
                                 "source_refs": ref, "directions": directions})
    return {"source_local_key": f"L10-set{set_number:02d}-ex{number_str}", "set": set_number,
            "exercise_number": number_str, "code": code, "modes": normalized_modes,
            "source_candidate_path": source_path.as_posix(),
            "source_candidate_sha256": source_pin[1],
            "source_record_sha256": digest(canonical_bytes(record)), "source_record": record,
            "canonical_item_id": None, "canonical_variant_id": None,
            "onset_q": None, "duration_q": None, "fixed_bpm": None, "note_per_click": None,
            "runtime_eligible": False, "runtime_admitted": False, "imported": False,
            "admitted": False}


def normalize_sources(txt_data: bytes, pdf_data: bytes,
                      documents: list[dict[str, Any]]) -> dict[str, Any]:
    require(len(documents) == len(INPUTS), "INPUT_DOCUMENT_COUNT")
    cards = source_cards(txt_data, pdf_data)
    records = []
    source_inputs = []
    for doc, (first, last, path, pin, schema) in zip(documents, INPUTS, strict=True):
        verify_document_shape(doc, first, last, schema)
        source_inputs.append({"sets": list(range(first, last + 1)), "path": path.as_posix(),
                              "bytes": pin[0], "sha256": pin[1], "schema": schema})
        for index, record in enumerate(doc["records"]):
            set_number = first + index // 12
            number = 12 * (set_number - 1) + index % 12 + 1
            records.append(normalize_record(record, set_number, number, cards, path, pin))
    require(len(records) == 108 and
            [record["exercise_number"] for record in records] == [f"{n:03d}" for n in range(1, 109)] and
            len(set(record["source_local_key"] for record in records)) == 108,
            "NORMALIZED_RECORD_COVERAGE")
    route_count = sum(len(direction["routes"]) for record in records for mode in record["modes"]
                      for direction in mode["directions"])
    note_count = sum(len(route["notes"]) for record in records for mode in record["modes"]
                     for direction in mode["directions"] for route in direction["routes"])
    require(route_count == 2592 and note_count == 10368, "NORMALIZED_ROUTE_COVERAGE")
    return {"schema": "fathom-level010-whole-detached-normalized-v1", "wbs_id": "2.3.1.1.1",
            "classification": "noncanonical_nonadmitted_source_aggregate", "level": 10,
            "sets": list(range(1, 10)),
            "source": {"txt_path": TXT.as_posix(), "txt_bytes": TXT_PIN[0], "txt_sha256": TXT_PIN[1],
                       "pdf_path": PDF.as_posix(), "pdf_bytes": PDF_PIN[0], "pdf_sha256": PDF_PIN[1],
                       "pdf_pages": 19, "selected_pdf_pages": list(range(2, 20))},
            "source_candidate_inputs": source_inputs,
            "counts": {"records": 108, "modes": 216, "directions": 432,
                       "string_routes": 2592, "untimed_note_positions": 10368},
            "instructions": {"mode_a_shift_after_note": 3, "mode_a_landing_note": 4,
                             "mode_b_shift_after_note": 1, "mode_b_landing_note": 2,
                             "routes_are_sequential": True, "ascii_barline_is_clock": False},
            "records": records, "exceptions": [],
            "pending": ["Curriculum/musical review", "canonical identity allocation",
                        "runtime admission and timing decisions"],
            "canonical_item_id": None, "canonical_variant_id": None,
            "onset_q": None, "duration_q": None, "fixed_bpm": None, "note_per_click": None,
            "runtime_eligible": False, "runtime_admitted": False, "imported": False,
            "admitted": False, "whole_workbook_complete": False}


def build_candidate(root: Path = ROOT) -> dict[str, Any]:
    txt_data, pdf_data, documents = load_inputs(root)
    return normalize_sources(txt_data, pdf_data, documents)


def serialize(value: dict[str, Any]) -> bytes:
    return canonical_bytes(value) + b"\n"


def write_output(output: Path, data: bytes, root: Path = ROOT) -> None:
    allowed = root / OUTPUT_ROOT
    require(output.is_absolute() and output.parent.resolve() == allowed.resolve() and
            not output.is_symlink() and not output.exists() and output.name.endswith(".json"),
            "OUTPUT_BOUNDARY")
    allowed.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as stream:
        stream.write(data)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="new absolute P12 Build JSON path")
    args = parser.parse_args()
    try:
        data = serialize(build_candidate())
        write_output(args.output, data)
        print(f"PASS detached whole Level 10: 108 codes, 216 modes, 2592 routes, 10368 untimed notes; bytes={len(data)} sha256={digest(data)}")
        return 0
    except (CandidateError, OSError) as exc:
        print(f"FAIL {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
