#!/usr/bin/env python3
"""Project pinned Level 9 Set 4 as detached 2+2 shift routes, never admitted."""

from __future__ import annotations

import argparse
from io import BytesIO
import hashlib
import json
from pathlib import Path
import re
import subprocess
from typing import Any

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
BUILD_REL = Path("Build/parallel-11/2.3.1.1.1-level009-set04-r01")
TXT_REL = Path("Notes/music/guitar project/TXT version/108_Finger_Permutations_Level_9_Mid_Pattern_Position_Transfer.txt")
PDF_REL = Path("Notes/music/guitar project/PDF version/108_Finger_Permutations_Level_9_Mid_Pattern_Position_Transfer.pdf")
TXT_PIN = (55960, "3cb0983c95081771caea7a12e8263d780f58850154681a9cd85c1a1916956105")
PDF_PIN = (42285, "3564ed3c24d55df462dba49b81ef2aeaf9a716a5a5af993bfdbf3e774702b00f")
CODES = ("2312", "2313", "2314", "2321", "2323", "2324", "2341", "2342", "2343", "2412", "2413", "2414")
HIGH_TO_LOW = ("e", "B", "G", "D", "A", "E")
ROUTE_ORDER = {"shift_up": tuple(reversed(HIGH_TO_LOW)), "shift_down": HIGH_TO_LOW}
POSITION_ORDER = {"shift_up": ("P5", "P7"), "shift_down": ("P7", "P5")}
FINGERS = {"1": "index", "2": "middle", "3": "ring", "4": "pinky"}
TXT_HEADING = re.compile(r"^Exercise (\d{3}): ([1-4]{4})$")
PDF_HEADING = re.compile(r"^(\d{3})\s+([1-4]{4})$")
TXT_ROW = re.compile(r"^([eBGDAE])\|([0-9-]+)\|([0-9-]+)\|$")
PDF_ROW = re.compile(r"^S\|([0-9-]+)\|([0-9-]+)\|$")
CELL = re.compile(r"^((?:10|[5-9]))-((?:10|[5-9]))(-+)$")
UP_LABEL = "SHIFT UP - P5 to P7; digits 1-2 in P5, digits 3-4 in P7; play bottom line first: E-A-D-G-B-e"
DOWN_LABEL = "SHIFT DOWN - P7 to P5; digits 1-2 in P7, digits 3-4 in P5; play top line first: e-B-G-D-A-E"


class CandidateError(ValueError):
    """Source, route, shift or write boundary disagrees with the pinned Set 4."""


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def pinned(raw: bytes, expected: tuple[int, str], name: str) -> None:
    if (len(raw), sha(raw)) != expected:
        raise CandidateError(f"PINNED_INPUT_DRIFT {name}")


def checkout() -> Path:
    result = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--show-toplevel"],
                            capture_output=True, text=True)
    if result.returncode or Path(result.stdout.strip()).resolve() != ROOT.resolve():
        raise CandidateError("REPOSITORY_ROOT_MISMATCH")
    return ROOT


def read_source(root: Path, relative: Path) -> bytes:
    path = root / relative
    if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root):
        raise CandidateError(f"SOURCE_PATH_INVALID {relative}")
    return path.read_bytes()


def cell_notes(cell: str, digits: str, position: str, first_ordinal: int, string: str) -> list[dict[str, Any]]:
    match = CELL.fullmatch(cell)
    if match is None or len(re.findall(r"10|[5-9]", cell)) != 2:
        raise CandidateError(f"TAB_CELL_SHAPE {cell}")
    frets = (int(match.group(1)), int(match.group(2)))
    offset = 4 if position == "P5" else 6
    if frets != tuple(int(digit) + offset for digit in digits):
        raise CandidateError(f"FINGER_FRET_MISMATCH {digits} {position} {cell}")
    return [{"ordinal": first_ordinal + index, "string": string, "position": position,
             "finger_digit": digit, "finger_name": FINGERS[digit], "fret": fret,
             "onset_q": None, "duration_q": None}
            for index, (digit, fret) in enumerate(zip(digits, frets, strict=True))]


def route(row: str, string: str, code: str, direction: str) -> dict[str, Any]:
    match = TXT_ROW.fullmatch(row)
    if match is None or match.group(1) != string:
        raise CandidateError(f"STRING_ROUTE_MISMATCH {code} {direction} {string}")
    cells = []
    for i, (position, text) in enumerate(zip(POSITION_ORDER[direction], match.groups()[1:], strict=True)):
        cells.append({"position": position, "source_ascii_cell": text,
                      "notes": cell_notes(text, code[2 * i:2 * i + 2], position, 2 * i + 1, string)})
    return {"string": string, "source_tab_row": row, "cells": cells, "shift_after_note": 2,
            "whole_hand_frame_shift_frets": 2 if direction == "shift_up" else -2,
            "melodic_interval_inferred": False}


def txt_cards(raw: bytes) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    try:
        lines = raw.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise CandidateError("TXT_ENCODING_INVALID") from exc
    if lines[0] != "108 FINGER PERMUTATIONS - LEVEL 9: MID-PATTERN POSITION TRANSFER":
        raise CandidateError("TXT_HEADER_MISMATCH")
    if lines[615] != "SET 4 OF 9 - EXERCISES 037-048" or lines[811] != "SET 5 OF 9 - EXERCISES 049-060":
        raise CandidateError("TXT_SET_BOUNDARY_MISMATCH")
    selection = lines[618:810]  # Printed lines 619–810; line 810 is the final blank.
    starts = [(i, m) for i, line in enumerate(selection) if (m := TXT_HEADING.fullmatch(line.strip()))]
    if len(starts) != 12:
        raise CandidateError(f"TXT_CARD_COUNT {len(starts)}")
    cards = []
    for i, (start, match) in enumerate(starts):
        stop = starts[i + 1][0] if i + 1 < len(starts) else len(selection)
        body = [line.strip() for line in selection[start + 1:stop] if line.strip()]
        number, code = match.groups()
        if number != f"{37 + i:03d}" or code != CODES[i] or len(body) != 14:
            raise CandidateError(f"TXT_CODE_ORDER_OR_CARD_SHAPE {number}")
        if body[0] != UP_LABEL or body[7] != DOWN_LABEL:
            raise CandidateError(f"TXT_SHIFT_LABEL_MISMATCH {number}")
        directions = {}
        for direction, rows in (("shift_up", body[1:7]), ("shift_down", body[8:14])):
            if tuple((m.group(1) if (m := TXT_ROW.fullmatch(row)) else None) for row in rows) != HIGH_TO_LOW:
                raise CandidateError(f"TXT_STRING_ORDER_MISMATCH {number} {direction}")
            if len(set(rows[i][1:] for i in range(6))) != 1:
                raise CandidateError(f"TXT_TEMPLATE_CONFLICT {number} {direction}")
            for row in rows:
                route(row, row[0], code, direction)
            directions[direction] = rows
        first_line = 619 + start
        cards.append({"number": number, "code": code, "first_line": first_line,
                      "last_line": first_line + 14, "directions": directions})
    movement = "\n".join(lines[5:12])
    practice = "\n".join(lines[18:25])
    for phrase in ("shift the whole hand frame two frets", "shift after note 2",
                   "not the melodic interval", "next note may rise, repeat, or fall"):
        if phrase not in movement:
            raise CandidateError(f"MOVEMENT_RULE_DRIFT {phrase}")
    for phrase in ("8-12 BPM below", "straight eighths", "accent note 3", "16ths",
                   "D-U | D-U", "U-D | U-D", "two separate days"):
        if phrase not in practice:
            raise CandidateError(f"PRACTICE_RULE_DRIFT {phrase}")
    instructions = {"finger_position_maps": {position: {digit: {"finger_name": name,
                          "fret": int(digit) + (4 if position == "P5" else 6)}
                          for digit, name in FINGERS.items()} for position in ("P5", "P7")},
                    "finger_map_ref": "L9-TXT1-3-4", "movement_text": movement,
                    "movement_ref": "L9-TXT1-6-12", "practice_text": practice,
                    "practice_ref": "L9-TXT1-19-25", "pdf_instruction_ref": "L9-PDF1-p1"}
    return cards, instructions


def pdf_cards(raw: bytes) -> list[dict[str, Any]]:
    try:
        reader = PdfReader(BytesIO(raw), strict=True)
        if len(reader.pages) != 10:
            raise CandidateError(f"PDF_PAGE_COUNT {len(reader.pages)}")
        instruction = reader.pages[0].extract_text() or ""
        lines = (reader.pages[4].extract_text() or "").splitlines()
    except CandidateError:
        raise
    except Exception as exc:
        raise CandidateError(f"PDF_READ_FAILED {type(exc).__name__}") from exc
    for phrase in ("P5: 1=5, 2=6, 3=7, 4=8", "P7: 1=7, 2=8, 3=9, 4=10",
                   "Release after note 2", "The next note may rise, repeat, or fall"):
        if phrase not in instruction:
            raise CandidateError(f"PDF_INSTRUCTION_DRIFT {phrase}")
    if lines[:3] != ["Level 9 - Mid-Pattern Position Transfer", "Set 4 of 9 - Exercises 037-048",
                     "2+2: notes 1-2 in the starting frame, shift, then notes 3-4 in the destination frame."]:
        raise CandidateError("PDF_SET_BOUNDARY_MISMATCH")
    if lines[-2:] != ["Standard tuning. P5 = frets 5-8; P7 = frets 7-10. Shift the whole hand frame after note 2.",
                       "Page 5 of 10"] or len(lines[3:-2]) != 120:
        raise CandidateError("PDF_PAGE_FOOTER_OR_CARD_COUNT")
    cards = []
    for i in range(12):
        block = lines[3 + i * 10:3 + (i + 1) * 10]
        match = PDF_HEADING.fullmatch(block[0])
        if match is None or match.groups() != (f"{37 + i:03d}", CODES[i]):
            raise CandidateError(f"PDF_CODE_ORDER {i}")
        if block[1:5] != ["2+2 POSITION SPLIT", "UP", "E>A>D>G>B>e", "P5->P7"] or block[6:9] != ["DN", "e>B>G>D>A>E", "P7->P5"]:
            raise CandidateError(f"PDF_ROUTE_OR_SHIFT_LAYOUT {i}")
        if PDF_ROW.fullmatch(block[5]) is None or PDF_ROW.fullmatch(block[9]) is None:
            raise CandidateError(f"PDF_TEMPLATE_SHAPE {i}")
        cards.append({"number": match.group(1), "code": match.group(2),
                      "shift_up": block[5], "shift_down": block[9]})
    return cards


def build_candidate(*, txt_data: bytes | None = None, pdf_data: bytes | None = None) -> dict[str, Any]:
    root = checkout()
    txt_data = read_source(root, TXT_REL) if txt_data is None else txt_data
    pdf_data = read_source(root, PDF_REL) if pdf_data is None else pdf_data
    pinned(txt_data, TXT_PIN, "L9-TXT")
    pinned(pdf_data, PDF_PIN, "L9-PDF")
    text_cards, instructions = txt_cards(txt_data)
    page_cards = pdf_cards(pdf_data)
    records = []
    for text, page in zip(text_cards, page_cards, strict=True):
        number, code = text["number"], text["code"]
        if (number, code) != (page["number"], page["code"]):
            raise CandidateError(f"PDF_TXT_CARD_MISMATCH {number}")
        directions = []
        for direction in ("shift_up", "shift_down"):
            printed = text["directions"][direction]
            template = page[direction]
            if any("S" + row[1:] != template for row in printed):
                raise CandidateError(f"PDF_TXT_TEMPLATE_MISMATCH {number} {direction}")
            by_string = dict(zip(HIGH_TO_LOW, printed, strict=True))
            routes = [route(by_string[string], string, code, direction) for string in ROUTE_ORDER[direction]]
            directions.append({"direction": direction, "route_order": list(ROUTE_ORDER[direction]),
                               "position_order": list(POSITION_ORDER[direction]),
                               "txt_rows_high_to_low": printed, "pdf_one_string_template": template,
                               "sequential_one_string_routes": routes})
        records.append({"source_local_key": f"L9-set04-ex{number}", "exercise_number": number,
                        "code": code, "source_refs": {"txt": f"L9-TXT1-{text['first_line']}-{text['last_line']}",
                                                     "pdf": "L9-PDF1-p5"},
                        "directions": directions, "canonical_item_id": None, "canonical_variant_id": None,
                        "onset_q": None, "duration_q": None, "note_per_click": None, "fixed_bpm": None,
                        "runtime_eligible": False, "runtime_admitted": False, "imported": False,
                        "admitted": False})
    return {"schema": "fathom-level009-set04-detached-candidate-v1", "wbs_id": "2.3.1.1.1",
            "level": 9, "set": 4,
            "source": {"txt_path": TXT_REL.as_posix(), "txt_bytes": TXT_PIN[0], "txt_sha256": TXT_PIN[1],
                       "pdf_path": PDF_REL.as_posix(), "pdf_bytes": PDF_PIN[0], "pdf_sha256": PDF_PIN[1],
                       "pdf_pages": 10, "selected_pdf_page": 5},
            "instructions": instructions, "records": records, "exceptions": [],
            "pending": ["Sets 1-3 and 5-9 family integration", "canonical identity allocation and admission",
                        "Curriculum/musical review", "runtime note timing and performed audio"],
            "whole_workbook_complete": False, "runtime_eligible": False, "runtime_admitted": False,
            "imported": False, "admitted": False}


def write_candidate(output: Path) -> dict[str, Any]:
    root = checkout()
    target = output if output.is_absolute() else root / output
    allowed = root / BUILD_REL
    if not target.parent.exists() or target.parent.is_symlink() or target.parent.resolve() != allowed.resolve():
        raise CandidateError(f"OUTPUT_OUTSIDE_LANE_BUILD {output}")
    if target.suffix != ".json" or target.is_symlink():
        raise CandidateError(f"OUTPUT_INVALID {output}")
    data = (json.dumps(build_candidate(), indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
    try:
        with target.open("xb") as stream:
            stream.write(data)
    except FileExistsError as exc:
        raise CandidateError(f"OUTPUT_EXISTS {output}") from exc
    return {"output": str(target.relative_to(root)), "bytes": len(data), "sha256": sha(data),
            "records": 12, "routes": 144, "notes": 576, "admitted": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(write_candidate(args.output), sort_keys=True))
    except CandidateError as exc:
        parser.exit(2, f"{exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
