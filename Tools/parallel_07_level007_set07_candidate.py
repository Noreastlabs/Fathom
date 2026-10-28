#!/usr/bin/env python3
"""Build an unadmitted, source-linked Level 7 Set 7 candidate.

Only the twelve printed Set 7 cards are interpreted. ASCII columns locate
notes within a four-note cell; they are not a clock, beat, or duration claim.
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
TXT_REL = Path("Notes/music/guitar project/TXT version/108_Finger_Permutations_Level_7_Three_String_Skip_Relay.txt")
PDF_REL = Path("Notes/music/guitar project/PDF version/108_Finger_Permutations_Level_7_Three_String_Skip_Relay.pdf")
TXT_BYTES = 38155
TXT_SHA256 = "467d1401237e34633efc4c517fa98d8190f0b47346a7b34be9d2548924883b61"
PDF_BYTES = 44165
PDF_SHA256 = "5c8607cff40801acb13f5e08dd2988b2ff943593eb084de2801f05f507a6c4ea"
BUILD_REL = Path("Build/parallel-07/2.3.1.1.1-level007-set07-r01")
CODES = ("3412", "3413", "3414", "3421", "3423", "3424", "3431", "3432", "3434", "4121", "4123", "4124")
STRING_HIGH_TO_LOW = ("e", "B", "G", "D", "A", "E")
STRING_LOW_TO_HIGH = tuple(reversed(STRING_HIGH_TO_LOW))
ROUTES = {
    "ascending": (("E", "D", "B"), ("A", "G", "e")),
    "descending": (("e", "G", "A"), ("B", "D", "E")),
}
TAB_ROW = re.compile(r"^([eBGDAE])\|([5-8-]{8})\|([5-8-]{8})\|$")
TXT_HEADING = re.compile(r"^Exercise (\d{3}): ([1-4]{4})$")
PDF_HEADING = re.compile(r"^(\d{3})\s+([1-4]{4})$")
FINGER_NAMES = {"1": "index", "2": "middle", "3": "ring", "4": "pinky"}


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
        raise CandidateError(f"SET7_CARD_COUNT {len(starts)}")
    cards: list[tuple[str, str, int, list[str]]] = []
    for position, (start, match) in enumerate(starts):
        stop = starts[position + 1][0] if position + 1 < len(starts) else len(lines)
        card = [line.strip() for line in lines[start + 1:stop] if line.strip()]
        cards.append((match.group(1), match.group(2), start + 1, card))
    if tuple(code for _, code, _, _ in cards) != CODES or tuple(number for number, _, _, _ in cards) != tuple(f"{n:03d}" for n in range(73, 85)):
        raise CandidateError("SET7_CODE_OR_ORDER_MISMATCH")
    return cards


def _tab_cards(cards: list[tuple[str, str, int, list[str]]], *, pdf: bool) -> list[dict[str, Any]]:
    parsed = []
    for number, code, heading_line, lines in cards:
        if pdf:
            if not lines or lines[0] != "1+2+1 SKIP RELAY":
                raise CandidateError(f"PDF_CARD_LABEL_MISMATCH {number}")
            lines = lines[1:]
            headings = ("UP", "DN")
        else:
            headings = ("ASCEND - E-D-B, A-G-e", "DESCEND - e-G-A, B-D-E")
        if len(lines) < 14 or lines[0] != headings[0] or lines[7] != headings[1]:
            raise CandidateError(f"CARD_DIRECTION_LAYOUT_MISMATCH {number}")
        directions = {}
        for label, rows in (("ascending", lines[1:7]), ("descending", lines[8:14])):
            if len(rows) != 6 or any(TAB_ROW.fullmatch(row) is None for row in rows):
                raise CandidateError(f"TAB_ROW_INVALID {number} {label}")
            if tuple(TAB_ROW.fullmatch(row).group(1) for row in rows) != STRING_HIGH_TO_LOW:
                raise CandidateError(f"TAB_STRING_ORDER_INVALID {number} {label}")
            directions[label] = rows
        allowed_footer = (
            "Standard tuning. Fifth position. 1+2+1 across three played strings; clear one silent string at each crossing.",
            "Page 8 of 10",
        ) if pdf and number == "084" else ()
        if tuple(lines[14:]) != allowed_footer:
            raise CandidateError(f"CARD_TRAILING_TEXT_UNEXPECTED {number}")
        parsed.append({"number": number, "code": code, "heading_line": heading_line, "directions": directions})
    return parsed


def _txt_cards(txt: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    lines = txt.splitlines()
    if lines[0] != "108 FINGER PERMUTATIONS - LEVEL 7: THREE-STRING SKIP RELAY":
        raise CandidateError("TXT_HEADER_MISMATCH")
    if lines[1202] != "SET 7 OF 9 - EXERCISES 073-084" or lines[1398] != "SET 8 OF 9 - EXERCISES 085-096":
        raise CandidateError("TXT_SET_BOUNDARY_MISMATCH")
    selected = lines[1205:1397]
    cards = _tab_cards(_blocks(selected, TXT_HEADING), pdf=False)
    for card in cards:
        card["heading_line"] += 1205
        card["last_line"] = card["heading_line"] + 14
    instructions = {
        "finger_map": {digit: {"name": name, "fret": int(digit) + 4} for digit, name in FINGER_NAMES.items()},
        "finger_map_ref": "L7-TXT1-3",
        "movement_rule_text": "\n".join(lines[4:9]),
        "movement_rule_ref": "L7-TXT1-5-9",
        "practice_rule_text": "\n".join(lines[15:24]),
        "practice_rule_ref": "L7-TXT1-16-24",
        "pdf_ref": "L7-PDF1-p1",
    }
    required = (
        "one physical string silent", "Ascend through E-D-B and A-G-e", "Descend through e-G-A and B-D-E",
        "Use straight 16ths first", "opposite starting pick stroke", "After three clean loops, add 2 BPM",
        "reduce 4-6 BPM", "two separate days",
    )
    combined = instructions["movement_rule_text"] + instructions["practice_rule_text"]
    if any(phrase not in combined for phrase in required):
        raise CandidateError("TXT_INSTRUCTION_MISMATCH")
    return cards, instructions


def _pdf_cards(pdf_bytes: bytes) -> list[dict[str, Any]]:
    try:
        reader = PdfReader(BytesIO(pdf_bytes), strict=True)
        if len(reader.pages) != 10:
            raise CandidateError(f"PDF_PAGE_COUNT {len(reader.pages)}")
        first = reader.pages[0].extract_text() or ""
        selected_page = reader.pages[7].extract_text() or ""
    except CandidateError:
        raise
    except Exception as exc:
        raise CandidateError(f"PDF_READ_FAILED {type(exc).__name__}") from exc
    if "Ascend: E-D-B, then A-G-e" not in first or "Descend: e-G-A, then B-D-E" not in first or "both gaps inaudible" not in first:
        raise CandidateError("PDF_INSTRUCTION_MISMATCH")
    lines = selected_page.splitlines()
    if lines[:3] != [
        "Level 7 - Three-String Skip Relay",
        "Set 7 of 9 - Exercises 073-084",
        "1+2+1: notes 2 and 4 land across separate silent strings; preserve the four-digit code order.",
    ]:
        raise CandidateError("PDF_SET_HEADER_MISMATCH")
    return _tab_cards(_blocks(lines[3:], PDF_HEADING), pdf=True)


def _route(rows: list[str], strings: tuple[str, str, str], segment: int, code: str) -> dict[str, Any]:
    found = []
    for row in rows:
        match = TAB_ROW.fullmatch(row)
        assert match is not None
        string = match.group(1)
        for column, fret in enumerate(match.group(segment + 2)):
            if fret != "-":
                found.append((column, string, int(fret)))
    found.sort(key=lambda value: value[0])
    expected_strings = (strings[0], strings[1], strings[1], strings[2])
    expected_frets = tuple(int(digit) + 4 for digit in code)
    if len(found) != 4 or tuple(item[1] for item in found) != expected_strings or tuple(item[2] for item in found) != expected_frets:
        raise CandidateError(f"TAB_CODE_ROUTE_MISMATCH {code} {strings} {segment}")
    if len({item[0] for item in found}) != 4:
        raise CandidateError(f"TAB_COLUMN_COLLISION {code} {strings}")
    string_indices = tuple(STRING_LOW_TO_HIGH.index(string) for string in strings)
    if abs(string_indices[1] - string_indices[0]) != 2 or abs(string_indices[2] - string_indices[1]) != 2:
        raise CandidateError(f"SILENT_GAP_ROUTE_INVALID {strings}")
    notes = [
        {
            "ordinal": i + 1, "string": string, "fret": fret, "finger_digit": code[i],
            "finger_name": FINGER_NAMES[code[i]], "ascii_column": column,
            "onset_q": None, "duration_q": None,
        }
        for i, (column, string, fret) in enumerate(found)
    ]
    return {"strings": list(strings), "silent_intervening_strings": 2, "notes": notes}


def build_candidate(*, txt_data: bytes | None = None, pdf_data: bytes | None = None) -> dict[str, Any]:
    root = _root()
    txt_data = _source_bytes(root, TXT_REL) if txt_data is None else txt_data
    pdf_data = _source_bytes(root, PDF_REL) if pdf_data is None else pdf_data
    _verify(txt_data, TXT_BYTES, TXT_SHA256, "L7-TXT")
    _verify(pdf_data, PDF_BYTES, PDF_SHA256, "L7-PDF")
    try:
        txt_cards, instructions = _txt_cards(txt_data.decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise CandidateError("TXT_ENCODING_INVALID") from exc
    pdf_cards = _pdf_cards(pdf_data)
    records = []
    for txt_card, pdf_card in zip(txt_cards, pdf_cards, strict=True):
        number = txt_card["number"]
        if pdf_card["number"] != number or pdf_card["code"] != txt_card["code"] or pdf_card["directions"] != txt_card["directions"]:
            raise CandidateError(f"PDF_TXT_CARD_MISMATCH {number}")
        code = txt_card["code"]
        directions = []
        for direction in ("ascending", "descending"):
            rows = txt_card["directions"][direction]
            routes = [
                _route(rows, route_strings, segment, code)
                for segment, route_strings in enumerate(ROUTES[direction])
            ]
            directions.append({"direction": direction, "tab_rows": rows, "routes": routes})
        records.append({
            "source_local_key": f"L7-set07-ex{number}", "exercise_number": number, "code": code,
            "source_refs": {"txt": f"L7-TXT1-{txt_card['heading_line']}-{txt_card['last_line']}", "pdf": "L7-PDF1-p8"},
            "directions": directions, "canonical_item_id": None, "canonical_variant_id": None,
            "onset_q": None, "duration_q": None, "note_per_click": None, "fixed_bpm": None,
            "runtime_eligible": False, "runtime_admitted": False, "imported": False, "admitted": False,
        })
    return {
        "schema": "fathom-level007-set07-detached-candidate-v1", "wbs_id": "2.3.1.1.1", "level": 7, "set": 7,
        "source": {
            "txt_path": TXT_REL.as_posix(), "txt_bytes": TXT_BYTES, "txt_sha256": TXT_SHA256,
            "pdf_path": PDF_REL.as_posix(), "pdf_bytes": PDF_BYTES, "pdf_sha256": PDF_SHA256,
            "pdf_pages": 10, "selected_pdf_page": 8,
        },
        "instructions": instructions, "records": records, "exceptions": [],
        "pending": ["Level 7 candidate family review", "canonical identity allocation and admission", "Curriculum/musical review", "runtime note timing and performed audio"],
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
