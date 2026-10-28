#!/usr/bin/env python3
"""Build an unadmitted, source-linked Level 9 Set 5 mid-pattern transfer candidate.

Aligned TXT rows are six sequential one-string routes, not a simultaneous chord.
ASCII columns are source positions, not a clock or duration claim.
"""

from __future__ import annotations

import argparse
from io import BytesIO
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
TXT_REL = Path("Notes/music/guitar project/TXT version/108_Finger_Permutations_Level_9_Mid_Pattern_Position_Transfer.txt")
PDF_REL = Path("Notes/music/guitar project/PDF version/108_Finger_Permutations_Level_9_Mid_Pattern_Position_Transfer.pdf")
TXT_BYTES = 55960
TXT_SHA256 = "3cb0983c95081771caea7a12e8263d780f58850154681a9cd85c1a1916956105"
PDF_BYTES = 42285
PDF_SHA256 = "3564ed3c24d55df462dba49b81ef2aeaf9a716a5a5af993bfdbf3e774702b00f"
BUILD_REL = Path("Build/parallel-07/2.3.1.1.1-level009-set05-r01")
CODES = ("2421", "2423", "2424", "2431", "2432", "2434", "3121", "3123", "3124", "3131", "3132", "3134")
STRINGS_HIGH_TO_LOW = ("e", "B", "G", "D", "A", "E")
ROUTE_ORDERS = {"shift_up": tuple(reversed(STRINGS_HIGH_TO_LOW)), "shift_down": STRINGS_HIGH_TO_LOW}
POSITIONS = {"P5": 4, "P7": 6}  # Add to the finger digit to obtain the fret.
FINGER_NAMES = {"1": "index", "2": "middle", "3": "ring", "4": "pinky"}
TXT_HEADING = re.compile(r"^Exercise (\d{3}): ([1-4]{4})$")
PDF_HEADING = re.compile(r"^(\d{3})\s+([1-4]{4})$")
TAB_ROW = re.compile(r"^([eBGDAES])\|([^|]+)\|([^|]+)\|$")
CELL = re.compile(r"^([0-9]+)-([0-9]+)(-+)$")


class CandidateError(ValueError):
    """A pinned source, selected cell, or output boundary failed."""


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _verify(data: bytes, size: int, sha: str, label: str) -> None:
    if len(data) != size or digest(data) != sha:
        raise CandidateError(f"PINNED_INPUT_DRIFT {label}: bytes={len(data)} sha256={digest(data)}")


def _root() -> Path:
    result = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if result.returncode != 0 or Path(result.stdout.strip()).resolve() != ROOT.resolve():
        raise CandidateError("REPOSITORY_ROOT_MISMATCH")
    return ROOT


def _source_bytes(root: Path, rel: Path) -> bytes:
    path = root / rel
    if path.is_symlink() or not path.is_file() or path.resolve().parent != path.parent.resolve():
        raise CandidateError(f"SOURCE_PATH_INVALID {rel}")
    return path.read_bytes()


def _blocks(lines: list[str], heading: re.Pattern[str]) -> list[tuple[str, str, int, list[str]]]:
    starts = [(i, m) for i, line in enumerate(lines) if (m := heading.fullmatch(line.strip()))]
    if len(starts) != 12:
        raise CandidateError(f"SET5_CARD_COUNT {len(starts)}")
    cards = []
    for position, (start, match) in enumerate(starts):
        stop = starts[position + 1][0] if position + 1 < len(starts) else len(lines)
        body = [line.strip() for line in lines[start + 1:stop] if line.strip()]
        cards.append((match.group(1), match.group(2), start + 1, body))
    if tuple(code for _, code, _, _ in cards) != CODES or tuple(number for number, _, _, _ in cards) != tuple(f"{n:03d}" for n in range(49, 61)):
        raise CandidateError("SET5_CODE_OR_ORDER_MISMATCH")
    return cards


def _txt_cards(txt: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    lines = txt.splitlines()
    if lines[0] != "108 FINGER PERMUTATIONS - LEVEL 9: MID-PATTERN POSITION TRANSFER":
        raise CandidateError("TXT_HEADER_MISMATCH")
    if lines[811] != "SET 5 OF 9 - EXERCISES 049-060" or lines[1007] != "SET 6 OF 9 - EXERCISES 061-072":
        raise CandidateError("TXT_SET_BOUNDARY_MISMATCH")
    cards = []
    for number, code, heading_line, body in _blocks(lines[814:1006], TXT_HEADING):
        if len(body) != 14 or body[0] != "SHIFT UP - P5 to P7; digits 1-2 in P5, digits 3-4 in P7; play bottom line first: E-A-D-G-B-e" or body[7] != "SHIFT DOWN - P7 to P5; digits 1-2 in P7, digits 3-4 in P5; play top line first: e-B-G-D-A-E":
            raise CandidateError(f"TXT_CARD_LAYOUT_MISMATCH {number}")
        directions = {"shift_up": body[1:7], "shift_down": body[8:14]}
        for name, rows in directions.items():
            if tuple((m.group(1) if (m := TAB_ROW.fullmatch(row)) else "") for row in rows) != STRINGS_HIGH_TO_LOW:
                raise CandidateError(f"TXT_TAB_ROW_INVALID {number} {name}")
        cards.append({"number": number, "code": code, "heading_line": heading_line + 814,
                      "last_line": heading_line + 828, "directions": directions})
    instructions = {
        "position_maps": {position: {digit: {"name": name, "fret": int(digit) + offset}
                                     for digit, name in FINGER_NAMES.items()}
                          for position, offset in POSITIONS.items()},
        "position_map_ref": "L9-TXT1-3-4",
        "movement_rule_text": "\n".join(lines[5:12]),
        "movement_rule_ref": "L9-TXT1-6-12",
        "practice_rule_text": "\n".join(lines[18:25]),
        "practice_rule_ref": "L9-TXT1-19-25",
        "pdf_ref": "L9-PDF1-p1",
    }
    combined = instructions["movement_rule_text"] + instructions["practice_rule_text"]
    for phrase in ("shift the whole hand frame two frets", "shift after note 2",
                   "one string at a time", "not the melodic interval", "Pass 1: play notes 1-2",
                   "straight eighths", "two separate days"):
        if phrase not in combined:
            raise CandidateError(f"TXT_INSTRUCTION_MISMATCH {phrase}")
    return cards, instructions


def _pdf_cards(pdf_data: bytes) -> list[dict[str, Any]]:
    try:
        reader = PdfReader(BytesIO(pdf_data), strict=True)
        if len(reader.pages) != 10:
            raise CandidateError(f"PDF_PAGE_COUNT {len(reader.pages)}")
        intro = reader.pages[0].extract_text() or ""
        page = reader.pages[5].extract_text() or ""
    except CandidateError:
        raise
    except Exception as exc:
        raise CandidateError(f"PDF_READ_FAILED {type(exc).__name__}") from exc
    if any(phrase not in intro for phrase in ("P5: 1=5, 2=6, 3=7, 4=8", "P7: 1=7, 2=8, 3=9, 4=10", "Release after note 2", "one-string template")):
        raise CandidateError("PDF_INSTRUCTION_MISMATCH")
    lines = page.splitlines()
    if lines[:3] != ["Level 9 - Mid-Pattern Position Transfer", "Set 5 of 9 - Exercises 049-060",
                     "2+2: notes 1-2 in the starting frame, shift, then notes 3-4 in the destination frame."]:
        raise CandidateError("PDF_SET_HEADER_MISMATCH")
    cards = []
    for number, code, _, body in _blocks(lines[3:], PDF_HEADING):
        footer = ("Standard tuning. P5 = frets 5-8; P7 = frets 7-10. Shift the whole hand frame after note 2.",
                  "Page 6 of 10") if number == "060" else ()
        if len(body) != 9 + len(footer) or tuple(body[9:]) != footer:
            raise CandidateError(f"PDF_CARD_TRAILING_TEXT_UNEXPECTED {number}")
        if (body[0], body[1], body[2], body[3], body[5], body[6], body[7]) != (
            "2+2 POSITION SPLIT", "UP", "E>A>D>G>B>e", "P5->P7", "DN",
            "e>B>G>D>A>E", "P7->P5",
        ):
            raise CandidateError(f"PDF_CARD_LAYOUT_MISMATCH {number}")
        templates = {"shift_up": body[4], "shift_down": body[8]}
        if any((m := TAB_ROW.fullmatch(row)) is None or m.group(1) != "S" for row in templates.values()):
            raise CandidateError(f"PDF_TEMPLATE_INVALID {number}")
        cards.append({"number": number, "code": code, "templates": templates})
    return cards


def _cell(cell: str, code_pair: str, position: str, ordinal_start: int) -> list[dict[str, Any]]:
    match = CELL.fullmatch(cell)
    if match is None or len(cell) != 9:
        raise CandidateError(f"TAB_CELL_INVALID {code_pair} {position} {cell}")
    frets = tuple(int(value) for value in match.groups()[:2])
    if frets != tuple(int(digit) + POSITIONS[position] for digit in code_pair):
        raise CandidateError(f"TAB_CODE_POSITION_MISMATCH {code_pair} {position} {cell}")
    return [
        {"ordinal": ordinal_start + index, "fret": fret, "finger_digit": code_pair[index],
         "finger_name": FINGER_NAMES[code_pair[index]], "ascii_column": token.start(),
         "onset_q": None, "duration_q": None}
        for index, (fret, token) in enumerate(zip(frets, re.finditer(r"\d+", cell), strict=True))
    ]


def _route(row: str, string: str, code: str, direction: str) -> dict[str, Any]:
    match = TAB_ROW.fullmatch(row)
    if match is None or match.group(1) != string:
        raise CandidateError(f"TXT_ROUTE_ROW_INVALID {code} {direction} {string}")
    positions = ("P5", "P7") if direction == "shift_up" else ("P7", "P5")
    cells = [
        {"position": position, "notes": _cell(cell, code_pair, position, ordinal_start)}
        for position, cell, code_pair, ordinal_start in zip(
            positions, match.groups()[1:], (code[:2], code[2:]), (1, 3), strict=True
        )
    ]
    return {"string": string, "source_tab_row": row, "cells": cells,
            "shift_at_center_barline": True, "shift_after_cell": 1, "shift_after_note": 2,
            "hand_frame_shift_frets": 2 if direction == "shift_up" else -2}


def build_candidate(*, txt_data: bytes | None = None, pdf_data: bytes | None = None) -> dict[str, Any]:
    root = _root()
    txt_data = _source_bytes(root, TXT_REL) if txt_data is None else txt_data
    pdf_data = _source_bytes(root, PDF_REL) if pdf_data is None else pdf_data
    _verify(txt_data, TXT_BYTES, TXT_SHA256, "L9-TXT")
    _verify(pdf_data, PDF_BYTES, PDF_SHA256, "L9-PDF")
    try:
        txt_cards, instructions = _txt_cards(txt_data.decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise CandidateError("TXT_ENCODING_INVALID") from exc
    pdf_cards = _pdf_cards(pdf_data)
    records = []
    for txt_card, pdf_card in zip(txt_cards, pdf_cards, strict=True):
        number, code = txt_card["number"], txt_card["code"]
        if (pdf_card["number"], pdf_card["code"]) != (number, code):
            raise CandidateError(f"PDF_TXT_CARD_MISMATCH {number}")
        directions = []
        for direction, order in ROUTE_ORDERS.items():
            rows = txt_card["directions"][direction]
            template = pdf_card["templates"][direction]
            if any("S" + row[1:] != template for row in rows):
                raise CandidateError(f"PDF_TXT_TEMPLATE_MISMATCH {number} {direction}")
            row_by_string = {row[0]: row for row in rows}
            routes = [_route(row_by_string[string], string, code, direction) for string in order]
            directions.append({"direction": direction, "route_order": list(order),
                               "txt_tab_rows_high_to_low": rows, "pdf_template": template, "routes": routes})
        records.append({
            "source_local_key": f"L9-set05-ex{number}", "exercise_number": number, "code": code,
            "source_refs": {"txt": f"L9-TXT1-{txt_card['heading_line']}-{txt_card['last_line']}", "pdf": "L9-PDF1-p6"},
            "directions": directions, "canonical_item_id": None, "canonical_variant_id": None,
            "onset_q": None, "duration_q": None, "note_per_click": None, "fixed_bpm": None,
            "runtime_eligible": False, "runtime_admitted": False, "imported": False, "admitted": False,
        })
    return {
        "schema": "fathom-level009-set05-detached-candidate-v1", "wbs_id": "2.3.1.1.1", "level": 9, "set": 5,
        "source": {"txt_path": TXT_REL.as_posix(), "txt_bytes": TXT_BYTES, "txt_sha256": TXT_SHA256,
                   "pdf_path": PDF_REL.as_posix(), "pdf_bytes": PDF_BYTES, "pdf_sha256": PDF_SHA256,
                   "pdf_pages": 10, "selected_pdf_page": 6},
        "instructions": instructions, "records": records, "exceptions": [],
        "pending": ["Level 9 candidate family review", "canonical identity allocation and admission",
                    "Curriculum/musical review", "runtime note timing and performed audio"],
        "whole_workbook_complete": False, "runtime_eligible": False, "runtime_admitted": False,
        "imported": False, "admitted": False,
    }


def write_candidate(output: Path) -> dict[str, Any]:
    root = _root()
    target = output if output.is_absolute() else root / output
    allowed = root / BUILD_REL
    if not target.parent.exists() or target.parent.is_symlink() or target.parent.resolve() != allowed.resolve():
        raise CandidateError(f"OUTPUT_OUTSIDE_LANE_BUILD {output}")
    if target.suffix != ".json" or target.is_symlink():
        raise CandidateError(f"OUTPUT_INVALID {output}")
    candidate = build_candidate()
    data = (json.dumps(candidate, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
    try:
        with target.open("xb") as handle:
            handle.write(data)
    except FileExistsError as exc:
        raise CandidateError(f"OUTPUT_EXISTS {output}") from exc
    return {"output": str(target.relative_to(root)), "bytes": len(data), "sha256": digest(data), "records": len(candidate["records"])}


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
