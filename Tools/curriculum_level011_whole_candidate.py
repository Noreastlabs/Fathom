#!/usr/bin/env python3
"""Build one unadmitted, source-reconciled Level 11 whole-workbook candidate.

Printed F/S cells are 1+2+1 contacts on sequential one-string routes. Their
ASCII spacing and practice instructions do not establish performed time.
"""

from __future__ import annotations

import argparse
from io import BytesIO
import hashlib
import itertools
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
TXT_REL = Path("Notes/music/guitar project/TXT version/108_Finger_Permutations_Level_11_Three_Position_Relay.txt")
PDF_REL = Path("Notes/music/guitar project/PDF version/108_Finger_Permutations_Level_11_Three_Position_Relay.pdf")
TXT_BYTES = 29960
TXT_SHA256 = "e579bb423d644a628723c802d84967f5c7aad49bf4e8e89bba5e4b622bf6ff48"
PDF_BYTES = 43510
PDF_SHA256 = "5f9b5e29e2f5ad3aa3372125f0ec0b91e6245eef1edabd5e81c06d1f00f5e917"
BUILD_REL = Path("Build/parallel-08/2.3.1.1.1-level011-whole-r01")
CODES = tuple("".join(digits) for digits in itertools.product("1234", repeat=4) if all(a != b for a, b in zip(digits, digits[1:])))
CODE_ORDER_SHA256 = "0f908baa37a88504753eaf1d4e6943a23c57d55c8ab5416c13239432500f9096"
ROUTES = {
    "shift_up": {"strings": ("E", "A", "D", "G", "B", "e"), "positions": ("P5", "P7", "P9"), "shift_frets": (2, 2)},
    "shift_down": {"strings": ("e", "B", "G", "D", "A", "E"), "positions": ("P9", "P7", "P5"), "shift_frets": (-2, -2)},
}
TXT_LABELS = {
    "shift_up": "SHIFT UP - P5 to P7 to P9; repeat on E>A>D>G>B>e",
    "shift_down": "SHIFT DOWN - P9 to P7 to P5; repeat on e>B>G>D>A>E",
}
PDF_ROUTES = {
    "shift_up": "E>A>D>G>B>e   P5>P7>P9",
    "shift_down": "e>B>G>D>A>E   P9>P7>P5",
}
FINGER_NAMES = {"1": "index", "2": "middle", "3": "ring", "4": "pinky"}
POSITION_OFFSETS = {"P5": 4, "P7": 6, "P9": 8}
GROUPS = (1, 2, 1)
TXT_HEADING = re.compile(r"^Exercise (\d{3}): ([1-4]{4})$")
PDF_HEADING = re.compile(r"^(\d{3})\s+([1-4]{4})$")
ROW = re.compile(r"^([FS])\|([0-9-]+)\|([0-9-]+)\|([0-9-]+)\|$")
PDF_RULE = "1+2+1: note 1 in the first frame, notes 2-3 in the middle frame, note 4 in the third frame."
PDF_FOOTER = "Standard tuning. P5 = frets 5-8; P7 = frets 7-10; P9 = frets 9-12. Shift after notes 1 and 3."


class CandidateError(ValueError):
    """Pinned source, selected cell, or output boundary failed."""


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


def _cells(f_row: str, s_row: str, code: str, positions: tuple[str, str, str]) -> tuple[tuple[tuple[str, int], ...], ...]:
    finger_match, fret_match = ROW.fullmatch(f_row), ROW.fullmatch(s_row)
    if finger_match is None or finger_match.group(1) != "F" or fret_match is None or fret_match.group(1) != "S":
        raise CandidateError(f"FS_ROW_INVALID {code}")
    groups = []
    offset = 0
    for index, (size, position) in enumerate(zip(GROUPS, positions, strict=True)):
        fingers = tuple(re.findall(r"\d+", finger_match.group(index + 2)))
        frets = tuple(int(value) for value in re.findall(r"\d+", fret_match.group(index + 2)))
        expected_fingers = tuple(code[offset:offset + size])
        expected_frets = tuple(int(digit) + POSITION_OFFSETS[position] for digit in expected_fingers)
        if len(fingers) != size or fingers != expected_fingers or frets != expected_frets:
            raise CandidateError(f"FS_CODE_FRAME_MISMATCH {code} {position} group={index + 1}")
        groups.append(tuple(zip(fingers, frets, strict=True)))
        offset += size
    return tuple(groups)


def _instructions(lines: list[str]) -> dict[str, Any]:
    blocks = {
        "movement_rule_text": ("\n".join(lines[8:15]), "L11-TXT1-9-15"),
        "overlapping_fret_rule_text": ("\n".join(lines[23:26]), "L11-TXT1-24-26"),
        "picking_rule_text": ("\n".join(lines[28:31]), "L11-TXT1-29-31"),
        "practice_rule_text": ("\n".join(lines[33:41]), "L11-TXT1-34-41"),
        "after_mastery_text": ("\n".join(lines[43:45]), "L11-TXT1-44-45"),
    }
    required = {
        "movement_rule_text": ("1+2+1", "E>A>D>G>B>e", "e>B>G>D>A>E", "note 2", "note 4", "both frame relocations are mandatory"),
        "overlapping_fret_rule_text": ("not necessarily the melodic contour", "Overlapping fret numbers do not cancel a move"),
        "picking_rule_text": ("D | U-D | U", "U | D-U | D", "Do not restart"),
        "practice_rule_text": ("10-15 BPM below", "both shift barlines", "notes 2 and 4", "two separate days"),
        "after_mastery_text": ("position distance", "not another full 108-exercise level"),
    }
    if any(any(phrase not in blocks[key][0] for phrase in phrases) for key, phrases in required.items()):
        raise CandidateError("TXT_INSTRUCTION_MISMATCH")
    result = {key: value for key, (value, _) in blocks.items()}
    result.update({key.replace("_text", "_ref"): ref for key, (_, ref) in blocks.items()})
    result["finger_map"] = {
        position: {digit: {"name": name, "fret": int(digit) + offset} for digit, name in FINGER_NAMES.items()}
        for position, offset in POSITION_OFFSETS.items()
    }
    result["finger_map_ref"] = "L11-TXT1-4-6"
    result["pdf_ref"] = "L11-PDF1-p1"
    return result


def _txt_cards(data: bytes) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    try:
        lines = data.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise CandidateError("TXT_ENCODING_INVALID") from exc
    if len(lines) != 945 or lines[0] != "108 FINGER PERMUTATIONS - LEVEL 11: THREE-POSITION RELAY":
        raise CandidateError("TXT_HEADER_OR_EOF_MISMATCH")
    if digest(",".join(CODES).encode("ascii")) != CODE_ORDER_SHA256 or len(CODES) != 108:
        raise CandidateError("EXPECTED_CODE_ORDER_INVALID")
    cards = []
    for set_number in range(1, 10):
        header_line = 48 + 100 * (set_number - 1)
        first, last = 12 * (set_number - 1) + 1, 12 * set_number
        if (lines[header_line - 2] != "=" * 112 or
                lines[header_line - 1] != f"SET {set_number} OF 9 - EXERCISES {first:03d}-{last:03d}" or
                lines[header_line] != "=" * 112 or lines[header_line + 1] != ""):
            raise CandidateError(f"TXT_SET_BOUNDARY_MISMATCH {set_number}")
        for within_set in range(12):
            number = first + within_set
            heading_line = header_line + 3 + 8 * within_set
            match = TXT_HEADING.fullmatch(lines[heading_line - 1])
            if match is None or match.group(1) != f"{number:03d}" or match.group(2) != CODES[number - 1]:
                raise CandidateError(f"TXT_CARD_ORDER_MISMATCH {number}")
            if number < 108 and lines[heading_line + 6] != "":
                raise CandidateError(f"TXT_CARD_SEPARATOR_MISMATCH {number}")
            body = lines[heading_line:heading_line + 6]
            code = match.group(2)
            directions = {}
            for name, offset in (("shift_up", 0), ("shift_down", 3)):
                if body[offset] != TXT_LABELS[name]:
                    raise CandidateError(f"TXT_ROUTE_LABEL_MISMATCH {number} {name}")
                f_row, s_row = body[offset + 1:offset + 3]
                cells = _cells(f_row, s_row, code, ROUTES[name]["positions"])
                directions[name] = {"f_row": f_row, "s_row": s_row, "cells": cells}
            cards.append({"set": set_number, "number": f"{number:03d}", "code": code,
                          "heading_line": heading_line, "last_line": heading_line + 6, "directions": directions})
    return cards, _instructions(lines)


def _pdf_cards(data: bytes) -> list[dict[str, Any]]:
    try:
        reader = PdfReader(BytesIO(data), strict=True)
        if len(reader.pages) != 10:
            raise CandidateError(f"PDF_PAGE_COUNT {len(reader.pages)}")
        first = reader.pages[0].extract_text() or ""
        pages = [(reader.pages[index].extract_text() or "").splitlines() for index in range(1, 10)]
    except CandidateError:
        raise
    except Exception as exc:
        raise CandidateError(f"PDF_READ_FAILED {type(exc).__name__}") from exc
    if any(phrase not in first for phrase in ("P5: 1=5", "P7: 1=7", "P9: 1=9", "Landing notes are 2 and 4", "Shift after notes 1 and 3")):
        raise CandidateError("PDF_INSTRUCTION_MISMATCH")
    cards = []
    for set_number, lines in enumerate(pages, 1):
        first_number, last_number = 12 * (set_number - 1) + 1, 12 * set_number
        if len(lines) != 137 or lines[:3] != ["Level 11 - Three-Position Relay", f"Set {set_number} of 9 - Exercises {first_number:03d}-{last_number:03d}", PDF_RULE]:
            raise CandidateError(f"PDF_SET_HEADER_OR_LENGTH_MISMATCH {set_number}")
        if lines[-2:] != [PDF_FOOTER, f"Page {set_number + 1} of 10"]:
            raise CandidateError(f"PDF_SET_FOOTER_MISMATCH {set_number}")
        for within_set in range(12):
            number = first_number + within_set
            block = lines[3 + 11 * within_set:3 + 11 * (within_set + 1)]
            match = PDF_HEADING.fullmatch(block[0])
            if match is None or match.group(1) != f"{number:03d}" or match.group(2) != CODES[number - 1]:
                raise CandidateError(f"PDF_CARD_ORDER_MISMATCH {number}")
            if block[1] != "1+2+1 DOUBLE SHIFT" or block[2] != "UP" or block[3] != PDF_ROUTES["shift_up"] or block[6] != "DN" or block[7] != PDF_ROUTES["shift_down"] or block[10] != "landings 2 and 4; no pick reset":
                raise CandidateError(f"PDF_CARD_LAYOUT_MISMATCH {number}")
            directions = {}
            for name, f_row, s_row in (("shift_up", block[4], block[5]), ("shift_down", block[8], block[9])):
                cells = _cells(f_row, s_row, match.group(2), ROUTES[name]["positions"])
                directions[name] = {"f_row": f_row, "s_row": s_row, "cells": cells}
            cards.append({"set": set_number, "number": match.group(1), "code": match.group(2), "directions": directions})
    return cards


def _string_route(string: str, code: str, direction: str, cells: tuple[tuple[tuple[str, int], ...], ...]) -> dict[str, Any]:
    route = ROUTES[direction]
    projected = []
    ordinal = 0
    for position, grouped in zip(route["positions"], cells, strict=True):
        notes = []
        for finger_digit, fret in grouped:
            ordinal += 1
            notes.append({"ordinal": ordinal, "string": string, "position": position, "fret": fret,
                          "finger_digit": finger_digit, "finger_name": FINGER_NAMES[finger_digit],
                          "is_landing_note": ordinal in (2, 4), "onset_q": None, "duration_q": None})
        projected.append({"position": position, "notes": notes})
    if ordinal != 4 or tuple(note["finger_digit"] for cell in projected for note in cell["notes"]) != tuple(code):
        raise CandidateError(f"PROJECTED_CODE_MISMATCH {code} {direction} {string}")
    return {"string": string, "cells": projected, "shift_after_notes": [1, 3],
            "landing_note_ordinals": [2, 4], "shift_frets": list(route["shift_frets"])}


def build_candidate(*, txt_data: bytes | None = None, pdf_data: bytes | None = None) -> dict[str, Any]:
    root = _root()
    txt_data = _source_bytes(root, TXT_REL) if txt_data is None else txt_data
    pdf_data = _source_bytes(root, PDF_REL) if pdf_data is None else pdf_data
    _verify(txt_data, TXT_BYTES, TXT_SHA256, "L11-TXT")
    _verify(pdf_data, PDF_BYTES, PDF_SHA256, "L11-PDF")
    txt_cards, instructions = _txt_cards(txt_data)
    pdf_cards = _pdf_cards(pdf_data)
    records = []
    for txt, pdf in zip(txt_cards, pdf_cards, strict=True):
        set_number, number, code = txt["set"], txt["number"], txt["code"]
        if (pdf["set"], pdf["number"], pdf["code"]) != (set_number, number, code):
            raise CandidateError(f"PDF_TXT_CARD_MISMATCH {number}")
        directions = []
        for name in ("shift_up", "shift_down"):
            printed, extracted = txt["directions"][name], pdf["directions"][name]
            if printed != extracted:
                raise CandidateError(f"PDF_TXT_FS_MISMATCH {number} {name}")
            route = ROUTES[name]
            directions.append({"direction": name, "string_order": list(route["strings"]),
                               "position_order": list(route["positions"]),
                               "f_row": printed["f_row"], "s_row": printed["s_row"],
                               "shift_after_notes": [1, 3], "landing_note_ordinals": [2, 4],
                               "string_routes": [_string_route(string, code, name, printed["cells"]) for string in route["strings"]]})
        records.append({"source_local_key": f"L11-set{set_number:02d}-ex{number}", "set": set_number,
                        "exercise_number": number, "code": code,
                        "source_refs": {"txt": f"L11-TXT1-{txt['heading_line']}-{txt['last_line']}",
                                        "pdf": f"L11-PDF1-p{set_number + 1}"},
                        "directions": directions, "canonical_item_id": None, "canonical_variant_id": None,
                        "onset_q": None, "duration_q": None, "note_per_click": None, "fixed_bpm": None,
                        "runtime_eligible": False, "runtime_admitted": False, "imported": False, "admitted": False})
    if len(records) != 108:
        raise CandidateError(f"WHOLE_LEVEL_CARD_COUNT {len(records)}")
    return {"schema": "fathom-level011-whole-detached-candidate-v1", "wbs_id": "2.3.1.1.1",
            "level": 11, "set_count": 9,
            "source": {"txt_path": TXT_REL.as_posix(), "txt_bytes": TXT_BYTES, "txt_sha256": TXT_SHA256,
                       "txt_lines": 945, "pdf_path": PDF_REL.as_posix(), "pdf_bytes": PDF_BYTES,
                       "pdf_sha256": PDF_SHA256, "pdf_pages": 10, "selected_pdf_pages": list(range(2, 11)),
                       "code_order_sha256": CODE_ORDER_SHA256},
            "instructions": instructions, "records": records, "exceptions": [],
            "whole_workbook_source_covered": True, "whole_workbook_complete": False,
            "runtime_eligible": False, "runtime_admitted": False, "imported": False, "admitted": False,
            "pending": ["integrated Curriculum/musical review", "canonical identity allocation and admission", "runtime note timing and performed audio"]}


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
