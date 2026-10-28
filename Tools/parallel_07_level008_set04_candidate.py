#!/usr/bin/env python3
"""Build an unadmitted, source-linked Level 8 Set 4 position-ladder candidate.

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
TXT_REL = Path("Notes/music/guitar project/TXT version/108_Finger_Permutations_Level_8_Two_Position_Ladder.txt")
PDF_REL = Path("Notes/music/guitar project/PDF version/108_Finger_Permutations_Level_8_Two_Position_Ladder.pdf")
TXT_BYTES = 53407
TXT_SHA256 = "0cba6885ed917013d5ceda5e0c231c568b4aa99be4c8c0e23941295a3fa5926a"
PDF_BYTES = 43123
PDF_SHA256 = "750f9b14962e71bc9ed0dc48a6f9343f2a1d5d14363858f7b9462187fc338829"
BUILD_REL = Path("Build/parallel-07/2.3.1.1.1-level008-set04-r01")
CODES = ("2312", "2313", "2314", "2321", "2323", "2324", "2341", "2342", "2343", "2412", "2413", "2414")
STRINGS_HIGH_TO_LOW = ("e", "B", "G", "D", "A", "E")
ROUTE_ORDERS = {"shift_up": tuple(reversed(STRINGS_HIGH_TO_LOW)), "shift_down": STRINGS_HIGH_TO_LOW}
POSITIONS = {"P5": 4, "P7": 6}  # Add to the finger digit to obtain the fret.
FINGER_NAMES = {"1": "index", "2": "middle", "3": "ring", "4": "pinky"}
TXT_HEADING = re.compile(r"^Exercise (\d{3}): ([1-4]{4})$")
PDF_HEADING = re.compile(r"^(\d{3})\s+([1-4]{4})$")
TAB_ROW = re.compile(r"^([eBGDAES])\|([^|]+)\|([^|]+)\|$")
CELL = re.compile(r"^([0-9]+)-([0-9]+)-([0-9]+)-([0-9]+)(-+)$")


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
        raise CandidateError(f"SET4_CARD_COUNT {len(starts)}")
    cards = []
    for position, (start, match) in enumerate(starts):
        stop = starts[position + 1][0] if position + 1 < len(starts) else len(lines)
        body = [line.strip() for line in lines[start + 1:stop] if line.strip()]
        cards.append((match.group(1), match.group(2), start + 1, body))
    if tuple(code for _, code, _, _ in cards) != CODES or tuple(number for number, _, _, _ in cards) != tuple(f"{n:03d}" for n in range(37, 49)):
        raise CandidateError("SET4_CODE_OR_ORDER_MISMATCH")
    return cards


def _txt_cards(txt: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    lines = txt.splitlines()
    if lines[0] != "108 FINGER PERMUTATIONS - LEVEL 8: TWO-POSITION LADDER":
        raise CandidateError("TXT_HEADER_MISMATCH")
    if lines[615] != "SET 4 OF 9 - EXERCISES 037-048" or lines[811] != "SET 5 OF 9 - EXERCISES 049-060":
        raise CandidateError("TXT_SET_BOUNDARY_MISMATCH")
    cards = []
    for number, code, heading_line, body in _blocks(lines[618:810], TXT_HEADING):
        if len(body) != 14 or body[0] != "SHIFT UP - P5 to P7; play bottom line first: E-A-D-G-B-e" or body[7] != "SHIFT DOWN - P7 to P5; play top line first: e-B-G-D-A-E":
            raise CandidateError(f"TXT_CARD_LAYOUT_MISMATCH {number}")
        directions = {"shift_up": body[1:7], "shift_down": body[8:14]}
        for name, rows in directions.items():
            if tuple((m.group(1) if (m := TAB_ROW.fullmatch(row)) else "") for row in rows) != STRINGS_HIGH_TO_LOW:
                raise CandidateError(f"TXT_TAB_ROW_INVALID {number} {name}")
        cards.append({"number": number, "code": code, "heading_line": heading_line + 618,
                      "last_line": heading_line + 632, "directions": directions})
    instructions = {
        "position_maps": {position: {digit: {"name": name, "fret": int(digit) + offset}
                                     for digit, name in FINGER_NAMES.items()}
                          for position, offset in POSITIONS.items()},
        "position_map_ref": "L8-TXT1-3-4",
        "movement_rule_text": "\n".join(lines[5:11]),
        "movement_rule_ref": "L8-TXT1-6-11",
        "practice_rule_text": "\n".join(lines[17:25]),
        "practice_rule_ref": "L8-TXT1-18-25",
        "pdf_ref": "L8-PDF1-p1",
    }
    combined = instructions["movement_rule_text"] + instructions["practice_rule_text"]
    for phrase in ("shift the entire hand frame two frets", "only between complete four-note cells",
                   "one string at a time", "not simultaneous chord tones", "pause one subdivision",
                   "straight 16ths", "two separate days"):
        if phrase not in combined:
            raise CandidateError(f"TXT_INSTRUCTION_MISMATCH {phrase}")
    return cards, instructions


def _pdf_cards(pdf_data: bytes) -> list[dict[str, Any]]:
    try:
        reader = PdfReader(BytesIO(pdf_data), strict=True)
        if len(reader.pages) != 10:
            raise CandidateError(f"PDF_PAGE_COUNT {len(reader.pages)}")
        intro = reader.pages[0].extract_text() or ""
        page = reader.pages[4].extract_text() or ""
    except CandidateError:
        raise
    except Exception as exc:
        raise CandidateError(f"PDF_READ_FAILED {type(exc).__name__}") from exc
    if any(phrase not in intro for phrase in ("P5: 1=5, 2=6, 3=7, 4=8", "P7: 1=7, 2=8, 3=9, 4=10", "notes are not played as a", "chord")):
        raise CandidateError("PDF_INSTRUCTION_MISMATCH")
    lines = page.splitlines()
    if lines[:3] != ["Level 8 - Two-Position Ladder", "Set 4 of 9 - Exercises 037-048",
                     "4+4: complete the code in P5, shift two frets, then repeat the entire code in P7."]:
        raise CandidateError("PDF_SET_HEADER_MISMATCH")
    cards = []
    for number, code, _, body in _blocks(lines[3:], PDF_HEADING):
        footer = ("Standard tuning. P5 = frets 5-8; P7 = frets 7-10. Repeat the one-string template on each string in route order.",
                  "Page 5 of 10") if number == "048" else ()
        if len(body) != 8 + len(footer) or tuple(body[8:]) != footer:
            raise CandidateError(f"PDF_CARD_TRAILING_TEXT_UNEXPECTED {number}")
        if (body[0], body[1], body[2], body[4], body[5], body[7]) != (
            "4+4 POSITION LADDER", "UP", "E>A>D>G>B>e   P5->P7", "DN",
            "e>B>G>D>A>E   P7->P5", "shift at the center barline",
        ):
            raise CandidateError(f"PDF_CARD_LAYOUT_MISMATCH {number}")
        templates = {"shift_up": body[3], "shift_down": body[6]}
        if any((m := TAB_ROW.fullmatch(row)) is None or m.group(1) != "S" for row in templates.values()):
            raise CandidateError(f"PDF_TEMPLATE_INVALID {number}")
        cards.append({"number": number, "code": code, "templates": templates})
    return cards


def _cell(cell: str, code: str, position: str) -> list[dict[str, Any]]:
    match = CELL.fullmatch(cell)
    if match is None or len(cell) != 11:
        raise CandidateError(f"TAB_CELL_INVALID {code} {position} {cell}")
    frets = tuple(int(value) for value in match.groups()[:4])
    if frets != tuple(int(digit) + POSITIONS[position] for digit in code):
        raise CandidateError(f"TAB_CODE_POSITION_MISMATCH {code} {position} {cell}")
    return [
        {"ordinal": index + 1, "fret": fret, "finger_digit": code[index],
         "finger_name": FINGER_NAMES[code[index]], "ascii_column": token.start(),
         "onset_q": None, "duration_q": None}
        for index, (fret, token) in enumerate(zip(frets, re.finditer(r"\d+", cell), strict=True))
    ]


def _route(row: str, string: str, code: str, direction: str) -> dict[str, Any]:
    match = TAB_ROW.fullmatch(row)
    if match is None or match.group(1) != string:
        raise CandidateError(f"TXT_ROUTE_ROW_INVALID {code} {direction} {string}")
    positions = ("P5", "P7") if direction == "shift_up" else ("P7", "P5")
    cells = [
        {"position": position, "notes": _cell(cell, code, position)}
        for position, cell in zip(positions, match.groups()[1:], strict=True)
    ]
    return {"string": string, "source_tab_row": row, "cells": cells,
            "shift_at_center_barline": True, "shift_after_cell": 1,
            "hand_frame_shift_frets": 2 if direction == "shift_up" else -2}


def build_candidate(*, txt_data: bytes | None = None, pdf_data: bytes | None = None) -> dict[str, Any]:
    root = _root()
    txt_data = _source_bytes(root, TXT_REL) if txt_data is None else txt_data
    pdf_data = _source_bytes(root, PDF_REL) if pdf_data is None else pdf_data
    _verify(txt_data, TXT_BYTES, TXT_SHA256, "L8-TXT")
    _verify(pdf_data, PDF_BYTES, PDF_SHA256, "L8-PDF")
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
            "source_local_key": f"L8-set04-ex{number}", "exercise_number": number, "code": code,
            "source_refs": {"txt": f"L8-TXT1-{txt_card['heading_line']}-{txt_card['last_line']}", "pdf": "L8-PDF1-p5"},
            "directions": directions, "canonical_item_id": None, "canonical_variant_id": None,
            "onset_q": None, "duration_q": None, "note_per_click": None, "fixed_bpm": None,
            "runtime_eligible": False, "runtime_admitted": False, "imported": False, "admitted": False,
        })
    return {
        "schema": "fathom-level008-set04-detached-candidate-v1", "wbs_id": "2.3.1.1.1", "level": 8, "set": 4,
        "source": {"txt_path": TXT_REL.as_posix(), "txt_bytes": TXT_BYTES, "txt_sha256": TXT_SHA256,
                   "pdf_path": PDF_REL.as_posix(), "pdf_bytes": PDF_BYTES, "pdf_sha256": PDF_SHA256,
                   "pdf_pages": 10, "selected_pdf_page": 5},
        "instructions": instructions, "records": records, "exceptions": [],
        "pending": ["Level 8 candidate family review", "canonical identity allocation and admission",
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
