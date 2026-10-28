#!/usr/bin/env python3
"""Pinned, detached Level 10 Set 3 odd-count position-transfer candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from io import BytesIO
from pathlib import Path
from typing import Any

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
TXT = Path("Notes/music/guitar project/TXT version/108_Finger_Permutations_Level_10_Odd_Count_Position_Transfer.txt")
PDF = Path("Notes/music/guitar project/PDF version/108_Finger_Permutations_Level_10_Odd_Count_Position_Transfer.pdf")
TXT_PIN = (136538, "e5ed078c62295adbb5f6bf00e6821e6eee0b2da73ef42c1714421158b5273226")
PDF_PIN = (81545, "1dafdcd177343f0ea147a5479ad654397d85f4b374cf960e264a230db965496b")
OUTPUT_ROOT = Path("Build/parallel-12/2.3.1.1.1-level010-set03-r01")
CODES = ("1431", "1432", "1434", "2121", "2123", "2124", "2131", "2132", "2134", "2141", "2142", "2143")
HIGH_TO_LOW = ("e", "B", "G", "D", "A", "E")
ROUTE_ORDER = {"shift_up": tuple(reversed(HIGH_TO_LOW)), "shift_down": HIGH_TO_LOW}
POSITIONS = {"shift_up": ("P5", "P7"), "shift_down": ("P7", "P5")}
FINGER_NAMES = {"1": "index", "2": "middle", "3": "ring", "4": "pinky"}
MODES = {"mode_a": {"name": "3+1 late shift", "shift_after": 3, "landing": 4,
                    "txt_heading": 936, "first_card": 941, "pdf_page": 6,
                    "txt_label": "MODE A - 3+1 LATE SHIFT", "pdf_label": "3+1 LATE SHIFT",
                    "picking": "Picking: D-start D-U-D | U; U-start U-D-U | D. Landing note: 4."},
         "mode_b": {"name": "1+3 early shift", "shift_after": 1, "landing": 2,
                    "txt_heading": 1158, "first_card": 1163, "pdf_page": 7,
                    "txt_label": "MODE B - 1+3 EARLY SHIFT", "pdf_label": "1+3 EARLY SHIFT",
                    "picking": "Picking: D-start D | U-D-U; U-start U | D-U-D. Landing note: 2."}}
UP_LABEL = {"mode_a": "SHIFT UP - P5 to P7; digits 1-3 in P5, digit 4 in P7; play bottom line first: E-A-D-G-B-e",
            "mode_b": "SHIFT UP - P5 to P7; digit 1 in P5, digits 2-4 in P7; play bottom line first: E-A-D-G-B-e"}
DOWN_LABEL = {"mode_a": "SHIFT DOWN - P7 to P5; digits 1-3 in P7, digit 4 in P5; play top line first: e-B-G-D-A-E",
              "mode_b": "SHIFT DOWN - P7 to P5; digit 1 in P7, digits 2-4 in P5; play top line first: e-B-G-D-A-E"}
PDF_HEADER = {"mode_a": "Set 3 of 9 - Mode A - 3+1 Late Shift - Exercises 025-036",
              "mode_b": "Set 3 of 9 - Mode B - 1+3 Early Shift - Exercises 025-036"}
ROW = re.compile(r"^([FeBGDAES])\|([0-9-]+)\|([0-9-]+)\|$")
HEADING = re.compile(r"^Exercise (\d{3}): ([1-4]{4})$")
PDF_HEADING = re.compile(r"^(\d{3})\s+([1-4]{4})$")


class CandidateError(ValueError):
    """A source pin, source row, semantic projection or output boundary failed."""


def require(condition: bool, code: str) -> None:
    if not condition:
        raise CandidateError(code)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify(data: bytes, pin: tuple[int, str], label: str) -> None:
    require(len(data) == pin[0] and digest(data) == pin[1], f"PINNED_INPUT_DRIFT {label}")


def local_bytes(root: Path, path: Path) -> bytes:
    require(root.is_absolute() and root.resolve() == ROOT.resolve(), "REPOSITORY_ROOT_MISMATCH")
    absolute = root / path
    require(not absolute.is_symlink() and absolute.is_file() and absolute.resolve().is_relative_to(root.resolve()),
            f"SOURCE_PATH_INVALID {path}")
    return absolute.read_bytes()


def parse_cell(row: str, expected_label: str, code: str, mode: str, direction: str) -> list[int]:
    match = ROW.fullmatch(row)
    require(match is not None and match.group(1) == expected_label, f"TAB_ROW_INVALID {mode} {direction} {expected_label}")
    shift_after = MODES[mode]["shift_after"]
    require(row.count("|") == 3 and row.endswith("|"), f"TAB_BARLINE_INVALID {mode} {direction} {expected_label}")
    digits_by_cell = (code[:shift_after], code[shift_after:])
    positions = POSITIONS[direction]
    frets: list[int] = []
    for cell_index, (digits, position) in enumerate(zip(digits_by_cell, positions, strict=True), 2):
        tokens = re.findall(r"\d+", match.group(cell_index))
        expected = [int(digit) + (4 if position == "P5" else 6) for digit in digits]
        if expected_label == "F":
            expected = [int(digit) for digit in digits]
        require(len(tokens) == len(digits) and list(map(int, tokens)) == expected,
                f"TAB_CELL_MISMATCH {mode} {direction} {expected_label} {cell_index - 1}")
        frets.extend(expected)
    require(len(frets) == 4, f"TAB_NOTE_COUNT {mode} {direction} {expected_label}")
    return frets


def parse_txt(lines: list[str]) -> dict[str, list[dict[str, Any]]]:
    require(len(lines) >= 1380 and lines[0] == "108 FINGER PERMUTATIONS - LEVEL 10: ODD-COUNT POSITION TRANSFER" and
            lines[931] == "SET 3 OF 9 - EXERCISES 025-036" and
            lines[1379] == "SET 4 OF 9 - EXERCISES 037-048", "TXT_SET_BOUNDARY")
    introduction = "\n".join(lines[:40])
    for phrase in ("Mode A - 3+1 late shift", "Mode B - 1+3 early shift", "The landing note is note 4",
                   "The landing note is note 2", "The barline marks the position shift only",
                   "not the melodic interval", "one string at a time"):
        require(phrase in introduction, f"TXT_INSTRUCTION_MISMATCH {phrase}")
    parsed: dict[str, list[dict[str, Any]]] = {}
    for mode, spec in MODES.items():
        heading_line = spec["txt_heading"]
        require(lines[heading_line - 1] == spec["txt_label"] and
                lines[heading_line + 1] == spec["picking"], f"TXT_MODE_HEADER {mode}")
        cards = []
        for index, code in enumerate(CODES):
            start = spec["first_card"] + index * 18
            number = f"{25 + index:03d}"
            block = lines[start - 1:start + 16]
            require(len(block) == 17 and HEADING.fullmatch(block[0]) is not None and
                    HEADING.fullmatch(block[0]).groups() == (number, code) and
                    block[1] == UP_LABEL[mode] and block[9] == DOWN_LABEL[mode] and
                    block[17 - 1].startswith("E|"), f"TXT_CARD_SHAPE {mode} {number}")
            up_finger, down_finger = block[2], block[10]
            require(parse_cell(up_finger, "F", code, mode, "shift_up") == list(map(int, code)) and
                    parse_cell(down_finger, "F", code, mode, "shift_down") == list(map(int, code)),
                    f"TXT_FINGER_ROW {mode} {number}")
            up_rows, down_rows = block[3:9], block[11:17]
            for direction, rows in (("shift_up", up_rows), ("shift_down", down_rows)):
                require(len(rows) == 6 and tuple(row[0] for row in rows) == HIGH_TO_LOW,
                        f"TXT_STRING_ORDER {mode} {number} {direction}")
                for row, string in zip(rows, HIGH_TO_LOW, strict=True):
                    parse_cell(row, string, code, mode, direction)
            cards.append({"number": number, "code": code, "txt_start_line": start,
                          "txt_end_line": start + 16,
                          "shift_up": {"finger_row": up_finger, "rows_high_to_low": up_rows},
                          "shift_down": {"finger_row": down_finger, "rows_high_to_low": down_rows}})
        parsed[mode] = cards
    return parsed


def parse_pdf(pdf_data: bytes) -> dict[str, list[dict[str, Any]]]:
    try:
        reader = PdfReader(BytesIO(pdf_data), strict=True)
        require(len(reader.pages) == 19, "PDF_PAGE_COUNT")
        pages = {mode: (reader.pages[spec["pdf_page"] - 1].extract_text() or "").splitlines()
                 for mode, spec in MODES.items()}
    except CandidateError:
        raise
    except Exception as exc:
        raise CandidateError("PDF_READ_FAILED") from exc
    parsed: dict[str, list[dict[str, Any]]] = {}
    for mode, spec in MODES.items():
        lines = pages[mode]
        require(len(lines) == 137 and lines[0] == "Level 10 - Odd-Count Position Transfer" and
                lines[1] == PDF_HEADER[mode] and
                lines[-1] == f"Page {spec['pdf_page']} of 19" and
                lines[-2] == "Standard tuning. P5 = frets 5-8; P7 = frets 7-10. Shift after note 3 in Mode A or after note 1 in Mode B.",
                f"PDF_MODE_PAGE {mode}")
        cards = []
        for index, code in enumerate(CODES):
            number = f"{25 + index:03d}"
            block = lines[3 + index * 11:3 + (index + 1) * 11]
            heading = PDF_HEADING.fullmatch(block[0]) if block else None
            require(len(block) == 11 and heading is not None and heading.groups() == (number, code) and
                    block[1] == spec["pdf_label"] and block[2] == "UP" and
                    block[3] == "E>A>D>G>B>e   P5>P7" and block[6] == "DN" and
                    block[7] == "e>B>G>D>A>E   P7>P5" and
                    block[10] == f"landing note {spec['landing']}; no pick reset",
                    f"PDF_CARD_SHAPE {mode} {number}")
            for direction, finger, tab in (("shift_up", block[4], block[5]),
                                           ("shift_down", block[8], block[9])):
                parse_cell(finger, "F", code, mode, direction)
                parse_cell(tab, "S", code, mode, direction)
            cards.append({"number": number, "code": code,
                          "shift_up": {"finger_template": block[4], "tab_template": block[5]},
                          "shift_down": {"finger_template": block[8], "tab_template": block[9]}})
        parsed[mode] = cards
    return parsed


def build_candidate(*, txt_data: bytes | None = None, pdf_data: bytes | None = None,
                    root: Path = ROOT) -> dict[str, Any]:
    txt_data = local_bytes(root, TXT) if txt_data is None else txt_data
    pdf_data = local_bytes(root, PDF) if pdf_data is None else pdf_data
    verify(txt_data, TXT_PIN, "LEVEL10_TXT")
    verify(pdf_data, PDF_PIN, "LEVEL10_PDF")
    try:
        lines = txt_data.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise CandidateError("TXT_ENCODING_INVALID") from exc
    txt = parse_txt(lines)
    pdf = parse_pdf(pdf_data)
    records = []
    for index, code in enumerate(CODES):
        number = f"{25 + index:03d}"
        modes = []
        for mode, spec in MODES.items():
            txt_card, pdf_card = txt[mode][index], pdf[mode][index]
            require(txt_card["number"] == pdf_card["number"] == number and
                    txt_card["code"] == pdf_card["code"] == code,
                    f"TXT_PDF_CARD_IDENTITY {mode} {number}")
            directions = []
            for direction in ("shift_up", "shift_down"):
                txt_direction, pdf_direction = txt_card[direction], pdf_card[direction]
                finger = txt_direction["finger_row"]
                rows = txt_direction["rows_high_to_low"]
                require(finger == pdf_direction["finger_template"] and
                        all("S" + row[1:] == pdf_direction["tab_template"] for row in rows),
                        f"TXT_PDF_TAB_MISMATCH {mode} {number} {direction}")
                routes = []
                for string in ROUTE_ORDER[direction]:
                    row = rows[HIGH_TO_LOW.index(string)]
                    frets = parse_cell(row, string, code, mode, direction)
                    shift_after = spec["shift_after"]
                    positions = POSITIONS[direction]
                    notes = []
                    for note_index, (digit, fret) in enumerate(zip(code, frets, strict=True), 1):
                        position = positions[0] if note_index <= shift_after else positions[1]
                        notes.append({"ordinal": note_index, "string": string, "position": position,
                                      "finger_digit": digit, "finger_name": FINGER_NAMES[digit],
                                      "fret": fret, "landing": note_index == spec["landing"],
                                      "onset_q": None, "duration_q": None})
                    landing_note = notes[spec["landing"] - 1]
                    routes.append({"route_ordinal": len(routes) + 1, "string": string,
                                   "source_tab_row": row, "source_finger_row": finger,
                                   "pdf_tab_template": pdf_direction["tab_template"],
                                   "pdf_finger_template": pdf_direction["finger_template"],
                                   "shift_after_note": shift_after,
                                   "landing_note": {"ordinal": spec["landing"], "position": landing_note["position"],
                                                    "finger_digit": landing_note["finger_digit"],
                                                    "fret": landing_note["fret"]},
                                   "notes": notes})
                directions.append({"direction": direction, "route_order": list(ROUTE_ORDER[direction]),
                                   "position_order": list(POSITIONS[direction]),
                                   "source_rows_high_to_low": rows, "source_finger_row": finger,
                                   "pdf_tab_template": pdf_direction["tab_template"],
                                   "pdf_finger_template": pdf_direction["finger_template"],
                                   "routes": routes})
            modes.append({"mode": mode, "label": spec["name"], "shift_after_note": spec["shift_after"],
                          "landing_note_ordinal": spec["landing"], "picking_rule_source": spec["picking"],
                          "source_refs": {"txt": f"L10-TXT1-{txt_card['txt_start_line']}-{txt_card['txt_end_line']}",
                                          "pdf": f"L10-PDF1-p{spec['pdf_page']}"},
                          "directions": directions})
        records.append({"source_local_key": f"L10-set03-ex{number}", "exercise_number": number,
                        "code": code, "modes": modes, "canonical_item_id": None,
                        "canonical_variant_id": None, "onset_q": None, "duration_q": None,
                        "fixed_bpm": None, "note_per_click": None, "runtime_eligible": False,
                        "runtime_admitted": False, "imported": False, "admitted": False})
    require(len(records) == 12 and sum(len(direction["routes"]) for record in records for mode in record["modes"]
                                       for direction in mode["directions"]) == 288,
            "CANDIDATE_COVERAGE")
    return {"schema": "fathom-level010-set03-detached-candidate-v1", "wbs_id": "2.3.1.1.1",
            "classification": "noncanonical_nonadmitted_source_candidate", "level": 10, "set": 3,
            "source": {"txt_path": TXT.as_posix(), "txt_bytes": TXT_PIN[0], "txt_sha256": TXT_PIN[1],
                       "pdf_path": PDF.as_posix(), "pdf_bytes": PDF_PIN[0], "pdf_sha256": PDF_PIN[1],
                       "pdf_pages": 19, "selected_pdf_pages": [6, 7], "txt_set_ref": "L10-TXT1-932-1379"},
            "instructions": {"mode_a_shift_after_note": 3, "mode_a_landing_note": 4,
                             "mode_b_shift_after_note": 1, "mode_b_landing_note": 2,
                             "routes_are_sequential": True, "ascii_barline_is_clock": False,
                             "no_pick_reset": True},
            "counts": {"records": 12, "modes": 24, "directions": 48,
                       "string_routes": 288, "untimed_note_positions": 1152},
            "records": records, "exceptions": [],
            "pending": ["Level 10 family Curriculum/musical review", "canonical identity allocation",
                        "runtime admission and timing decisions"],
            "canonical_item_id": None, "canonical_variant_id": None, "onset_q": None,
            "duration_q": None, "fixed_bpm": None, "note_per_click": None,
            "runtime_eligible": False, "runtime_admitted": False, "imported": False,
            "admitted": False, "whole_workbook_complete": False}


def serialize(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


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
        print(f"PASS detached Level 10 Set 3: 12 codes, 24 modes, 288 sequential routes, 1152 untimed notes; bytes={len(data)} sha256={digest(data)}")
        return 0
    except (CandidateError, OSError) as exc:
        print(f"FAIL {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
