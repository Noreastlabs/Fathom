#!/usr/bin/env python3
"""Build a detached, source-backed Level 27 candidate without runtime admission."""

from __future__ import annotations

import argparse
import csv
from io import BytesIO
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
TXT_REL = Path("Notes/music/guitar project/TXT version/Scale_Exercises_Section_III_Level_27_Natural_Minor_Diatonic_Thirds_Two_Octave_Six_String_Neck_Ladder.txt")
PDF_REL = Path("Notes/music/guitar project/PDF version/Scale_Exercises_Section_III_Level_27_Natural_Minor_Diatonic_Thirds_Two_Octave_Six_String_Neck_Ladder.pdf")
SOURCE_MAP_REL = Path("Results/parallel-01/exercises/inventory/20260922T180500Z-2.3-curriculum-v1-source-inventory-evidence/curriculum-source-map.tsv")
TXT_BYTES = 44185
TXT_SHA256 = "f50784bd14bb098f80ffff9eb64c08f913f8828152bc1fecc211b5e5f83a72cc"
PDF_BYTES = 31632
PDF_SHA256 = "844aff8996501dc76f10cbb9bf887137d7968da5f911ed04addcb9d14a727109"
SOURCE_MAP_BYTES = 68536
SOURCE_MAP_SHA256 = "f526ff4d9ce3bceaf9a7cc581a3ac2aee2c74917eba984dd57913adba574c123"
BUILD_REL = Path("Build/parallel-04/2.3.1.1.1-level027-whole-r03")
TITLE = "SCALE EXERCISES - SECTION III, LEVEL 27"
SUBTITLE = "NATURAL MINOR DIATONIC THIRDS - TWO-OCTAVE SIX-STRING NECK LADDER"
STRING_ORDER = ("e", "B", "G", "D", "A", "E")
OPEN_MIDI = {"E": 40, "A": 45, "D": 50, "G": 55, "B": 59, "e": 64}
DEGREE_SEMITONES = {
    "1": 0, "2": 2, "b3": 3, "4": 5, "5": 7, "b6": 8, "b7": 10,
    "8": 12, "9": 14, "b10": 15, "11": 17, "12": 19, "b13": 20,
    "b14": 22, "15": 24,
}
PITCH_CLASSES = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
RUNG_HEADER = re.compile(r"^RUNG (\d{2}) OF 13 - (.+) - ROOT ON LOW E FRET (\d+) - FRAME (\d+)-(\d+)$")
ROUTE_ROW = re.compile(r"^(\d{2})\s+(.+?)\s+fret (\d+)\s+(\d+-\d+)\s+(.+)$")
TAB_ROW = re.compile(r"^([eBGDAE])\s*\|(.*)$")
SLOT_VALUE = re.compile(r"^(b?\d{1,2})-*$")
PDF_RUNG = re.compile(r"^(\d{2})\s+(.+? NATURAL MINOR(?: - OCTAVE)?)$")
PDF_TABLE_LABELS = ("Int", "Deg", "Fng")


class CandidateError(ValueError):
    """A pinned input, source mapping, musical projection, or output boundary failed."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _fail(message: str) -> None:
    raise CandidateError(message)


def _root() -> Path:
    result = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0 or Path(result.stdout.strip()).resolve() != ROOT.resolve():
        _fail("REPOSITORY_ROOT_MISMATCH")
    return ROOT


def _safe_file(root: Path, relative: Path, label: str) -> Path:
    path = root / relative
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            _fail(f"INPUT_SYMLINK {label}: {relative.as_posix()}")
    if not path.is_file():
        _fail(f"INPUT_MISSING {label}: {relative.as_posix()}")
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        _fail(f"INPUT_UNRESOLVABLE {label}: {type(exc).__name__}")
    if not resolved.is_relative_to(root.resolve()):
        _fail(f"INPUT_OUTSIDE_ROOT {label}: {relative.as_posix()}")
    return path


def _pinned(data: bytes, expected_bytes: int, expected_sha256: str, label: str) -> bytes:
    actual = sha256(data)
    if len(data) != expected_bytes or actual != expected_sha256:
        _fail(f"PINNED_INPUT_DRIFT {label}: bytes={len(data)} sha256={actual}")
    return data


def _read_pinned(root: Path, rel: Path, size: int, digest: str, label: str, override: bytes | None) -> bytes:
    data = override if override is not None else _safe_file(root, rel, label).read_bytes()
    return _pinned(data, size, digest, label)


def _source_map_row(data: bytes) -> dict[str, str]:
    try:
        rows = list(csv.DictReader(data.decode("utf-8").splitlines(), delimiter="\t"))
    except (UnicodeDecodeError, csv.Error) as exc:
        _fail(f"SOURCE_MAP_PARSE_FAILED {type(exc).__name__}")
    matches = [row for row in rows if row.get("level") == "27"]
    if len(matches) != 1:
        _fail(f"SOURCE_MAP_LEVEL27_ROW_COUNT {len(matches)}")
    row = matches[0]
    expected = {
        "section": "III",
        "wbs_owner": "2.3.1.1.1",
        "txt_path": TXT_REL.as_posix(),
        "txt_bytes": str(TXT_BYTES),
        "txt_sha256": TXT_SHA256,
        "pdf_path": PDF_REL.as_posix(),
        "pdf_bytes": str(PDF_BYTES),
        "pdf_sha256": PDF_SHA256,
        "review": "Pending",
        "conversion_status": "not_converted",
        "representative_item_id": "",
    }
    for field, value in expected.items():
        if row.get(field) != value:
            _fail(f"SOURCE_MAP_STATE_MISMATCH {field}: {row.get(field)!r}")
    for field in ("stable_ids_assigned", "runtime_eligible", "imported", "admitted"):
        if row.get(field, "").casefold() != "false":
            _fail(f"SOURCE_MAP_STATE_MISMATCH {field}: {row.get(field)!r}")
    return row


def _line_excerpt(lines: list[str], start: int, end: int) -> dict[str, Any]:
    if start < 1 or end < start or end > len(lines):
        _fail(f"TXT_EXCERPT_RANGE_INVALID {start}-{end}")
    return {"start_line": start, "end_line": end, "text": "\n".join(lines[start - 1:end])}


def _split_pipe_cells(raw: str, expected_label: str) -> list[str]:
    pieces = raw.split("|")
    if len(pieces) != 15 or pieces[0].strip() != expected_label or pieces[-1] != "":
        _fail(f"GRID_CELL_SHAPE_INVALID label={expected_label} row={raw!r}")
    cells = pieces[1:-1]
    if len(cells) != 13 or any(len(cell) != 8 for cell in cells):
        _fail(f"GRID_COLUMN_SHAPE_INVALID label={expected_label}")
    return cells


def _tab_row(raw: str) -> tuple[str, list[str]]:
    match = TAB_ROW.fullmatch(raw)
    if match is None:
        _fail(f"TAB_ROW_INVALID {raw!r}")
    string, rest = match.groups()
    cells = rest.split("|")
    if cells[-1] == "":
        cells.pop()
    if len(cells) != 13 or any(len(cell) != 8 for cell in cells):
        _fail(f"TAB_ROW_COLUMN_COUNT_INVALID {string}")
    return string, cells


def _slot_value(slot: str, context: str) -> str | None:
    if slot == "----":
        return None
    match = SLOT_VALUE.fullmatch(slot)
    if match is None:
        _fail(f"GRID_SLOT_INVALID {context}: {slot!r}")
    return match.group(1)


def _pair_values(cell: str, context: str) -> tuple[str, str]:
    first = _slot_value(cell[:4], context)
    second = _slot_value(cell[4:], context)
    if first is None or second is None:
        _fail(f"PAIR_SLOT_MISSING {context}")
    return first, second


def _degree_pitch(degree: str) -> int:
    if degree not in DEGREE_SEMITONES:
        _fail(f"UNKNOWN_DEGREE {degree}")
    return DEGREE_SEMITONES[degree]


def _note_name_pitch_class(name: str) -> int:
    match = re.fullmatch(r"([A-G])([#b]?)", name)
    if match is None:
        _fail(f"KEY_ROOT_INVALID {name}")
    letter, accidental = match.groups()
    return (PITCH_CLASSES[letter] + (1 if accidental == "#" else -1 if accidental == "b" else 0)) % 12


def _pair_labels(lines: list[str], section_heading: str, label: str) -> list[str]:
    heading_index = lines.index(section_heading)
    prefix = label + ":"
    for line in lines[heading_index + 1:]:
        if line.startswith(prefix):
            values = [part.strip() for part in line.split(":", 1)[1].split("|")]
            if values and values[-1] == "":
                values.pop()
            return values
    _fail(f"SEQUENCE_ROW_MISSING {label}")


def _route_pairs(lines: list[str], label: str) -> list[str]:
    index = lines.index("STRING-PATH MAP")
    wanted = label + ":"
    for line in lines[index + 1:]:
        if line.startswith(wanted):
            result = [part.strip() for part in line.split(":", 1)[1].split("|")]
            if result and result[-1] == "":
                result.pop()
            return result
    _fail(f"STRING_PATH_ROW_MISSING {label}")


def _parse_route_table(lines: list[str]) -> list[dict[str, Any]]:
    records = []
    for index, line in enumerate(lines, start=1):
        match = ROUTE_ROW.fullmatch(line.strip())
        if match is None:
            continue
        number, key_name, root_fret, frame, tones = match.groups()
        if int(number) != len(records) + 1:
            _fail(f"ROUTE_TABLE_ORDER_MISMATCH row={number}")
        lo, hi = (int(value) for value in frame.split("-"))
        records.append({
            "rung": int(number),
            "key_name": key_name,
            "root_pitch": key_name.split()[0],
            "root_fret": int(root_fret),
            "frame": {"low_fret": lo, "high_fret": hi},
            "scale_tones_degrees_1_through_b7": tones.split(),
            "source_line": index,
        })
    if len(records) != 13:
        _fail(f"ROUTE_TABLE_COUNT {len(records)}")
    return records


def _parse_direction(rows: list[str], direction_name: str, rung_number: int, root_fret: int, key_name: str) -> dict[str, Any]:
    if len(rows) != 9 or not rows[0].startswith("Int|") or not rows[1].startswith("Deg|") or not rows[2].startswith("Fng|"):
        _fail(f"DIRECTION_ROW_LAYOUT_INVALID rung={rung_number} {direction_name}")
    interval_cells = _split_pipe_cells(rows[0], "Int")
    degree_cells = _split_pipe_cells(rows[1], "Deg")
    finger_cells = _split_pipe_cells(rows[2], "Fng")
    tab_rows: list[dict[str, Any]] = []
    for raw in rows[3:]:
        string, cells = _tab_row(raw)
        tab_rows.append({"string": string, "raw": raw, "cells": cells})
    if tuple(row["string"] for row in tab_rows) != STRING_ORDER:
        _fail(f"TAB_STRING_ORDER_INVALID rung={rung_number} {direction_name}")

    root_midi = OPEN_MIDI["E"] + root_fret
    root_pitch_class = _note_name_pitch_class(key_name.split()[0])
    if root_midi % 12 != root_pitch_class:
        _fail(f"ROOT_FRET_KEY_PITCH_MISMATCH rung={rung_number} key={key_name}")

    pairs = []
    for column in range(13):
        degree_pair = _pair_values(degree_cells[column], f"rung={rung_number} {direction_name} degree column={column + 1}")
        finger_pair = _pair_values(finger_cells[column], f"rung={rung_number} {direction_name} finger column={column + 1}")
        interval = interval_cells[column].rstrip("-")
        if interval not in ("m3", "M3"):
            _fail(f"INTERVAL_LABEL_INVALID rung={rung_number} {direction_name} column={column + 1}")
        contacts = []
        for slot_index in range(2):
            found = []
            for row in tab_rows:
                value = _slot_value(row["cells"][column][slot_index * 4:slot_index * 4 + 4],
                                    f"rung={rung_number} {direction_name} col={column + 1} string={row['string']} slot={slot_index + 1}")
                if value is not None:
                    found.append((row["string"], int(value)))
            if len(found) != 1:
                _fail(f"TAB_CONTACT_CARDINALITY rung={rung_number} {direction_name} col={column + 1} slot={slot_index + 1} count={len(found)}")
            string, fret = found[0]
            degree = degree_pair[slot_index]
            finger = finger_pair[slot_index]
            if finger not in ("1", "2", "3", "4"):
                _fail(f"FINGER_DIGIT_INVALID rung={rung_number} {direction_name} col={column + 1}")
            midi = OPEN_MIDI[string] + fret
            expected_midi = root_midi + _degree_pitch(degree)
            if midi != expected_midi:
                _fail(f"DEGREE_TAB_PITCH_MISMATCH rung={rung_number} {direction_name} col={column + 1} slot={slot_index + 1} degree={degree} tab={string}{fret} midi={midi} expected={expected_midi}")
            if not root_fret - 1 <= fret <= root_fret + 3:
                _fail(f"FRET_OUTSIDE_FRAME rung={rung_number} {direction_name} col={column + 1}")
            contacts.append({
                "slot_order": slot_index + 1,
                "degree_label": degree,
                "finger_digit": int(finger),
                "string": string,
                "fret": fret,
                "midi_pitch": midi,
                "onset_q": None,
                "duration_q": None,
                "source_cell_column": column + 1,
            })
        measured_interval = abs(contacts[1]["midi_pitch"] - contacts[0]["midi_pitch"])
        expected_interval = 3 if interval == "m3" else 4
        if measured_interval != expected_interval:
            _fail(f"INTERVAL_TAB_PITCH_MISMATCH rung={rung_number} {direction_name} col={column + 1} label={interval} measured={measured_interval}")
        pairs.append({
            "pair_number": column + 1,
            "interval_quality": interval,
            "degree_pair": list(degree_pair),
            "finger_pair": [int(value) for value in finger_pair],
            "string_path": "".join(note["string"] for note in contacts),
            "contacts": contacts,
        })
    return {
        "direction": direction_name,
        "interval_row": rows[0],
        "degree_row": rows[1],
        "finger_row": rows[2],
        "tab_rows": [row["raw"] for row in tab_rows],
        "pairs": pairs,
    }


def _parse_text_rungs(lines: list[str], route_table: list[dict[str, Any]], asc_degrees: list[str], desc_degrees: list[str], asc_quality: list[str], desc_quality: list[str], up_paths: list[str], down_paths: list[str]) -> list[dict[str, Any]]:
    headings = []
    for index, line in enumerate(lines):
        match = RUNG_HEADER.fullmatch(line.strip())
        if match:
            headings.append((index, match))
    if len(headings) != 13:
        _fail(f"RUNG_HEADING_COUNT {len(headings)}")
    expected_asc = [value.split("-") for value in asc_degrees]
    expected_desc = [value.split("-") for value in desc_degrees]
    if len(asc_quality) != 13 or len(desc_quality) != 13 or len(up_paths) != 13 or len(down_paths) != 13:
        _fail("SOURCE_SEQUENCE_CARDINALITY")
    result = []
    for rung_index, (start, match) in enumerate(headings, start=1):
        number, heading_key, root_fret, frame_low, frame_high = match.groups()
        route = route_table[rung_index - 1]
        if int(number) != rung_index or int(number) != route["rung"]:
            _fail(f"RUNG_SEQUENCE_MISMATCH rung={number}")
        normalized_heading_key = heading_key.lower().replace("bb", "bb").replace("eb", "eb")
        if normalized_heading_key != route["key_name"].casefold().replace("♭", "b"):
            _fail(f"RUNG_ROUTE_KEY_MISMATCH rung={number} heading={heading_key!r} table={route['key_name']!r}")
        if int(root_fret) != route["root_fret"] or (int(frame_low), int(frame_high)) != (route["frame"]["low_fret"], route["frame"]["high_fret"]):
            _fail(f"RUNG_ROUTE_FRET_MISMATCH rung={number}")
        block = lines[start:start + 24]
        if len(block) != 24 or block[3] != "ASCENDING - 13 PAIRS / 26 NOTES" or block[13] != "DESCENDING - 13 PAIRS / 26 NOTES":
            _fail(f"RUNG_BLOCK_SHAPE_INVALID rung={number}")
        scale_prefix = "Scale tones across two octaves: "
        if not block[1].startswith(scale_prefix):
            _fail(f"RUNG_SCALE_TONE_LINE_MISSING rung={number}")
        scale_tones = block[1][len(scale_prefix):].rstrip(".").split()
        if scale_tones[:7] != route["scale_tones_degrees_1_through_b7"]:
            _fail(f"RUNG_SCALE_TONES_ROUTE_MISMATCH rung={number}")
        ascending = _parse_direction(block[4:13], "ascending", rung_index, int(root_fret), route["key_name"])
        descending = _parse_direction(block[14:23], "descending", rung_index, int(root_fret), route["key_name"])
        for direction, expected_degrees, expected_qualities, expected_paths in (
            (ascending, expected_asc, asc_quality, up_paths),
            (descending, expected_desc, desc_quality, down_paths),
        ):
            name = direction["direction"]
            if [pair["degree_pair"] for pair in direction["pairs"]] != expected_degrees:
                _fail(f"DEGREE_SEQUENCE_MISMATCH rung={number} {name}")
            if [pair["interval_quality"] for pair in direction["pairs"]] != expected_qualities:
                _fail(f"QUALITY_SEQUENCE_MISMATCH rung={number} {name}")
            if [pair["string_path"] for pair in direction["pairs"]] != expected_paths:
                _fail(f"STRING_PATH_SEQUENCE_MISMATCH rung={number} {name}")
        result.append({
            "rung": rung_index,
            "key_name": route["key_name"],
            "root_pitch": route["root_pitch"],
            "root_fret": int(root_fret),
            "frame": route["frame"],
            "scale_tones_two_octaves": scale_tones,
            "source_refs": {
                "txt_path": TXT_REL.as_posix(),
                "txt_start_line": start + 1,
                "txt_end_line": start + 24,
                "route_table_line": route["source_line"],
                "pdf_card_page": 3 + (rung_index - 1) // 2 if rung_index < 13 else 9,
                "pdf_route_summary_page": 2,
                "pdf_worked_example_page": 1 if rung_index == 1 else None,
            },
            "source_cell_note_count": 52,
            "canonical_item_id": None,
            "canonical_variant_id": None,
            "onset_q": None,
            "duration_q": None,
            "note_per_click": None,
            "fixed_bpm": None,
            "runtime_eligible": False,
            "runtime_admitted": False,
            "imported": False,
            "admitted": False,
            "directions": [ascending, descending],
        })
    return result


def _normalize_pdf_tab(raw: str) -> tuple[str, list[str]]:
    match = TAB_ROW.fullmatch(raw)
    if match is None:
        _fail(f"PDF_TAB_ROW_INVALID {raw!r}")
    label, body = match.groups()
    cells = body.split("|")
    if cells and cells[-1] == "":
        cells.pop()
    if len(cells) != 13 or any(len(cell) != 8 for cell in cells):
        _fail(f"PDF_TAB_SHAPE_INVALID {label}")
    return label, cells


def _pdf_table(block: list[str], rung: int, direction_index: int) -> list[str]:
    table_starts = [i for i, line in enumerate(block) if line.startswith("Int|")]
    if len(table_starts) != 2:
        _fail(f"PDF_DIRECTION_TABLE_COUNT rung={rung} count={len(table_starts)}")
    start = table_starts[direction_index]
    rows = block[start:start + 9]
    if len(rows) != 9 or not rows[1].startswith("Deg|") or not rows[2].startswith("Fng|"):
        _fail(f"PDF_DIRECTION_TABLE_SHAPE rung={rung}")
    for i, row in enumerate(rows[3:]):
        label, _ = _normalize_pdf_tab(row)
        if label != STRING_ORDER[i]:
            _fail(f"PDF_TAB_STRING_ORDER rung={rung}")
    return rows


def _parse_pdf_card_pages(pdf_bytes: bytes) -> tuple[dict[int, dict[str, Any]], dict[str, Any]]:
    try:
        reader = PdfReader(BytesIO(pdf_bytes), strict=True)
        if len(reader.pages) != 10:
            _fail(f"PDF_PAGE_COUNT {len(reader.pages)}")
        page_lines = [
            [line.strip() for line in (page.extract_text() or "").splitlines() if line.strip()]
            for page in reader.pages
        ]
    except CandidateError:
        raise
    except Exception as exc:
        _fail(f"PDF_READ_FAILED {type(exc).__name__}")
    cards: dict[int, dict[str, Any]] = {}
    for page_number in range(3, 10):
        lines = page_lines[page_number - 1]
        headings = []
        for index, line in enumerate(lines):
            match = PDF_RUNG.fullmatch(line)
            if match:
                headings.append((index, match))
        for card_index, (start, match) in enumerate(headings):
            rung_number = int(match.group(1))
            stop = headings[card_index + 1][0] if card_index + 1 < len(headings) else len(lines)
            block = lines[start + 1:stop]
            tables = [_pdf_table(block, rung_number, direction_index) for direction_index in range(2)]
            cards[rung_number] = {
                "rung": rung_number,
                "pdf_page": page_number,
                "heading": match.group(2),
                "ascending_rows": tables[0],
                "descending_rows": tables[1],
            }
    if tuple(sorted(cards)) != tuple(range(1, 14)):
        _fail(f"PDF_CARD_COVERAGE {sorted(cards)}")
    page_one = page_lines[0]
    table_starts = [i for i, line in enumerate(page_one) if line.startswith("Int|")]
    if len(table_starts) != 2:
        _fail(f"PDF_WORKED_EXAMPLE_TABLE_COUNT {len(table_starts)}")
    example = {
        "ascending_rows": page_one[table_starts[0]:table_starts[0] + 9],
        "descending_rows": page_one[table_starts[1]:table_starts[1] + 9],
    }
    page_two = page_lines[1]
    route_table = _parse_pdf_route_table(page_two)
    page_nine = page_lines[8]
    page_ten = page_lines[9]
    pdf_facts = {
        "page_count": len(reader.pages),
        "route_table": route_table,
        "worked_example": example,
        "page_one_session_protocol_step_count": 6,
        "page_one_pause_statement": "Use 2-3 neighboring rungs; pause only after each cell.",
        "page_nine_tempo_statement": next((line for line in page_nine if line.startswith("Add 2 BPM")), ""),
        "page_ten_practice_heading": next((line for line in page_ten if "practice sequence" in line.lower()), ""),
        "page_two_has_up_paths": any(line.startswith("UP PATHS:") for line in page_two),
        "page_two_has_down_paths": any(line.startswith("DOWN PATHS:") for line in page_two),
        "page_nine_down_pass_statement": next((line for line in page_nine if line.startswith("Down pass:")), ""),
    }
    if pdf_facts["page_one_pause_statement"] not in " ".join(page_one):
        _fail("PDF_PAGE_ONE_PAUSE_STATEMENT_MISSING")
    if pdf_facts["page_nine_tempo_statement"] != "Add 2 BPM after 3 clean trips; reduce 4-6 BPM after 2 errors.":
        _fail("PDF_PAGE_NINE_TEMPO_STATEMENT_MISMATCH")
    if pdf_facts["page_ten_practice_heading"] != "Five-phase practice sequence":
        _fail("PDF_PAGE_TEN_PHASE_HEADING_MISMATCH")
    return cards, pdf_facts


def _parse_pdf_route_table(lines: list[str]) -> list[dict[str, Any]]:
    try:
        header = lines.index("Rung")
        how_to_use = lines.index("How to use")
    except ValueError:
        _fail("PDF_ROUTE_TABLE_BOUNDS_MISSING")
    body = lines[header + 5:how_to_use]
    if len(body) != 65:
        _fail(f"PDF_ROUTE_TABLE_SHAPE {len(body)}")
    rows = []
    for offset in range(0, len(body), 5):
        number, key_name, root, frame, tones = body[offset:offset + 5]
        rows.append({
            "rung": int(number),
            "key_name": key_name,
            "root_fret": int(root.removeprefix("fret ")),
            "frame": frame,
            "scale_tones_degrees_1_through_b7": tones.split(),
        })
    if len(rows) != 13:
        _fail(f"PDF_ROUTE_TABLE_COUNT {len(rows)}")
    return rows


def _compare_pdf_grids(rungs: list[dict[str, Any]], pdf_cards: dict[int, dict[str, Any]], pdf_facts: dict[str, Any]) -> int:
    compared = 0
    for rung in rungs:
        number = rung["rung"]
        card = pdf_cards[number]
        if card["pdf_page"] != rung["source_refs"]["pdf_card_page"]:
            _fail(f"PDF_CARD_PAGE_MISMATCH rung={number}")
        if card["heading"].casefold() != rung["key_name"].upper().casefold():
            _fail(f"PDF_CARD_KEY_MISMATCH rung={number}")
        for direction, rows_key in (("ascending", "ascending_rows"), ("descending", "descending_rows")):
            candidate_rows = rung["directions"][0 if direction == "ascending" else 1]
            pdf_rows = card[rows_key]
            if candidate_rows["interval_row"] != pdf_rows[0] or candidate_rows["degree_row"] != pdf_rows[1] or candidate_rows["finger_row"] != pdf_rows[2]:
                _fail(f"PDF_TEXT_GRID_MISMATCH rung={number} {direction} musical_rows")
            for txt_row, pdf_row in zip(candidate_rows["tab_rows"], pdf_rows[3:], strict=True):
                txt_label, txt_cells = _tab_row(txt_row)
                pdf_label, pdf_cells = _normalize_pdf_tab(pdf_row)
                if txt_label != pdf_label or txt_cells != pdf_cells:
                    _fail(f"PDF_TEXT_GRID_MISMATCH rung={number} {direction} {txt_label}")
            compared += 1
    worked = pdf_facts["worked_example"]
    rung_one = rungs[0]
    for direction, key in (("ascending", "ascending_rows"), ("descending", "descending_rows")):
        candidate_direction = rung_one["directions"][0 if direction == "ascending" else 1]
        pdf_rows = worked[key]
        if (candidate_direction["interval_row"], candidate_direction["degree_row"], candidate_direction["finger_row"]) != tuple(pdf_rows[:3]):
            _fail(f"PDF_WORKED_EXAMPLE_GRID_MISMATCH {direction}")
        for txt_row, pdf_row in zip(candidate_direction["tab_rows"], pdf_rows[3:], strict=True):
            txt_label, txt_cells = _tab_row(txt_row)
            pdf_label, pdf_cells = _normalize_pdf_tab(pdf_row)
            if txt_label != pdf_label or txt_cells != pdf_cells:
                _fail(f"PDF_WORKED_EXAMPLE_GRID_MISMATCH {direction} {txt_label}")
        compared += 1
    return compared


def _instruction_sections(lines: list[str]) -> dict[str, Any]:
    return {
        "purpose_and_scope": _line_excerpt(lines, 5, 16),
        "natural_minor_formula": _line_excerpt(lines, 18, 21),
        "ascending_and_descending_pair_sequences": _line_excerpt(lines, 23, 27),
        "interval_quality_pattern": _line_excerpt(lines, 29, 34),
        "six_string_shape_and_frame": _line_excerpt(lines, 36, 44),
        "string_path_maps": _line_excerpt(lines, 46, 50),
        "cell_and_picking_instructions": _line_excerpt(lines, 52, 64),
        "rhythm_and_practice_progression": _line_excerpt(lines, 66, 77),
        "chromatic_route": _line_excerpt(lines, 79, 82),
        "full_round_trip_and_mastery": _line_excerpt(lines, 444, 475),
    }


def _discrepancies(lines: list[str], pdf_facts: dict[str, Any]) -> list[dict[str, Any]]:
    txt_tempo = lines[450]
    txt_pause = lines[75]
    return [
        {
            "id": "rung_13_route_label_presentation",
            "status": "source_difference_pending_review",
            "txt_ref": {
                "path": TXT_REL.as_posix(),
                "line": 99,
                "text": "A natural minor - octave",
            },
            "pdf_ref": {
                "path": PDF_REL.as_posix(),
                "page": 2,
                "text": "A natural minor (octave)",
            },
            "shared_facts_match": {
                "rung": 13,
                "root_fret": 17,
                "frame": "16-20",
                "scale_tones_degrees_1_through_b7": ["A", "B", "C", "D", "E", "F", "G"],
            },
            "note": "Both labels identify the octave extension in their respective route tables; preserve the printed labels separately without canonicalizing the text.",
        },
        {
            "id": "tempo_downshift_trigger_specificity",
            "status": "source_difference_pending_review",
            "txt_ref": {"path": TXT_REL.as_posix(), "line": 451, "text": txt_tempo},
            "pdf_ref": {"path": PDF_REL.as_posix(), "page": 9, "text": pdf_facts["page_nine_tempo_statement"]},
            "note": "The TXT includes signs of tension as an additional downshift trigger; the PDF tempo summary names two errors only.",
        },
        {
            "id": "pause_duration_specificity",
            "status": "source_difference_pending_review",
            "txt_ref": {"path": TXT_REL.as_posix(), "line": 76, "text": txt_pause},
            "pdf_ref": {"path": PDF_REL.as_posix(), "page": 1, "text": pdf_facts["page_one_pause_statement"]},
            "note": "The TXT specifies a one-beat pause; the PDF states only that a pause occurs after each cell.",
        },
        {
            "id": "descending_string_path_summary",
            "status": "pdf_summary_omission_pending_review",
            "txt_ref": {"path": TXT_REL.as_posix(), "line": 48, "text": lines[47]},
            "pdf_ref": {"path": PDF_REL.as_posix(), "page": 2, "text": "UP PATHS appears; no DOWN PATHS summary row appears. Descending TAB remains on the card pages."},
            "note": "The PDF route summary omits the descending string-path summary present in the TXT; the downward pair and TAB grids remain source-available.",
        },
        {
            "id": "practice_phase_grouping",
            "status": "presentation_difference_pending_review",
            "txt_ref": {"path": TXT_REL.as_posix(), "lines": [71, 77], "text": _line_excerpt(lines, 71, 77)["text"]},
            "pdf_ref": {"path": PDF_REL.as_posix(), "pages": [1, 10], "text": "Page 1 labels a six-step Session protocol; page 10 titles its summary a Five-phase practice sequence."},
            "note": "The PDF presents practice guidance with different phase grouping. Preserve both statements; do not infer a preferred grouping.",
        },
    ]


def build_candidate(*, txt_data: bytes | None = None, pdf_data: bytes | None = None, source_map_data: bytes | None = None) -> dict[str, Any]:
    root = _root()
    txt_bytes = _read_pinned(root, TXT_REL, TXT_BYTES, TXT_SHA256, "L27-TXT", txt_data)
    pdf_bytes = _read_pinned(root, PDF_REL, PDF_BYTES, PDF_SHA256, "L27-PDF", pdf_data)
    map_bytes = _read_pinned(root, SOURCE_MAP_REL, SOURCE_MAP_BYTES, SOURCE_MAP_SHA256, "L27-SOURCE-MAP", source_map_data)
    map_row = _source_map_row(map_bytes)
    try:
        lines = txt_bytes.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        _fail(f"TXT_ENCODING_INVALID {type(exc).__name__}")
    if len(lines) != 481 or lines[0] != TITLE or lines[1] != SUBTITLE:
        _fail(f"TXT_DOCUMENT_SHAPE_MISMATCH lines={len(lines)}")
    route_table = _parse_route_table(lines)
    asc_degrees = _pair_labels(lines, "MAIN SEQUENCE", "Ascending")
    desc_degrees = _pair_labels(lines, "MAIN SEQUENCE", "Descending")
    asc_quality = _pair_labels(lines, "INTERVAL-QUALITY PATTERN", "Ascending")
    desc_quality = _pair_labels(lines, "INTERVAL-QUALITY PATTERN", "Descending")
    up_paths = _route_pairs(lines, "Ascending")
    down_paths = _route_pairs(lines, "Descending")
    rungs = _parse_text_rungs(lines, route_table, asc_degrees, desc_degrees, asc_quality, desc_quality, up_paths, down_paths)
    pdf_cards, pdf_facts = _parse_pdf_card_pages(pdf_bytes)
    pdf_grid_comparisons = _compare_pdf_grids(rungs, pdf_cards, pdf_facts)
    for route, pdf_route in zip(route_table, pdf_facts["route_table"], strict=True):
        shared_route_facts = (
            route["rung"], route["root_fret"], f'{route["frame"]["low_fret"]}-{route["frame"]["high_fret"]}',
            route["scale_tones_degrees_1_through_b7"],
        )
        pdf_shared_route_facts = (
            pdf_route["rung"], pdf_route["root_fret"], pdf_route["frame"],
            pdf_route["scale_tones_degrees_1_through_b7"],
        )
        if shared_route_facts != pdf_shared_route_facts:
            _fail(f"PDF_ROUTE_TABLE_MISMATCH rung={route['rung']}")
        if route["key_name"] != pdf_route["key_name"] and not (
            route["rung"] == 13
            and route["key_name"] == "A natural minor - octave"
            and pdf_route["key_name"] == "A natural minor (octave)"
        ):
            _fail(f"PDF_ROUTE_KEY_LABEL_MISMATCH rung={route['rung']}")
    if not pdf_facts["page_two_has_up_paths"] or pdf_facts["page_two_has_down_paths"]:
        _fail("PDF_ROUTE_PATH_SUMMARY_EXPECTATION_MISMATCH")

    pair_count = sum(len(direction["pairs"]) for rung in rungs for direction in rung["directions"])
    contact_count = sum(len(pair["contacts"]) for rung in rungs for direction in rung["directions"] for pair in direction["pairs"])
    quality_counts = {
        quality: sum(pair["interval_quality"] == quality for rung in rungs for direction in rung["directions"] for pair in direction["pairs"])
        for quality in ("m3", "M3")
    }
    return {
        "schema": "fathom-level027-detached-candidate-v1",
        "schema_version": 1,
        "candidate_status": "detached_pending_review",
        "wbs_id": "2.3.1.1.1",
        "level": 27,
        "section": "III",
        "source_title": "Natural Minor Diatonic Thirds: Two-Octave Six-String Neck Ladder",
        "source": {
            "txt_path": TXT_REL.as_posix(),
            "txt_bytes": TXT_BYTES,
            "txt_sha256": TXT_SHA256,
            "txt_line_count": len(lines),
            "pdf_path": PDF_REL.as_posix(),
            "pdf_bytes": PDF_BYTES,
            "pdf_sha256": PDF_SHA256,
            "pdf_page_count": pdf_facts["page_count"],
            "pdf_rendered_pages_visually_reviewed": list(range(1, 11)),
            "source_map_path": SOURCE_MAP_REL.as_posix(),
            "source_map_bytes": SOURCE_MAP_BYTES,
            "source_map_sha256": SOURCE_MAP_SHA256,
        },
        "source_map_state": {
            "review": map_row["review"],
            "conversion_status": map_row["conversion_status"],
            "representative_item_id": None,
            "stable_ids_assigned": False,
            "runtime_eligible": False,
            "imported": False,
            "admitted": False,
        },
        "scope": {
            "level_source_coverage_verified": True,
            "whole_workbook_complete": False,
            "source_coverage_verification_basis": "TXT line mapping, all rung grids and PDF route/card text plus all ten rendered PDF pages.",
            "performed_or_recorded_practice": False,
            "canonical_ids_assigned": False,
            "runtime_eligible": False,
            "runtime_admitted": False,
            "imported": False,
            "admitted": False,
            "parent_acceptance": False,
        },
        "instruction_sections": _instruction_sections(lines),
        "route_reference": route_table,
        "sequence_facts": {
            "ascending_degree_pairs": [value.split("-") for value in asc_degrees],
            "descending_degree_pairs": [value.split("-") for value in desc_degrees],
            "ascending_quality": asc_quality,
            "descending_quality": desc_quality,
            "ascending_string_paths": up_paths,
            "descending_string_paths": down_paths,
            "cell_design": {
                "ascending_pairs": 13,
                "ascending_notes": 26,
                "descending_pairs": 13,
                "descending_notes": 26,
                "high_root_occurrences_at_turn": 2,
                "notes_per_rung_cell": 52,
                "frame_shift_frets_after_final_pair": 1,
                "timing_inference": None,
                "fixed_bpm": None,
            },
            "full_round_trip_instruction": {
                "route": "rungs 01-13, then rungs 12-01; do not replay rung 13",
                "cells_per_round": 25,
                "notes_per_cell": 52,
                "instructed_note_count": 1300,
                "performed": False,
                "source_ref": {"txt_path": TXT_REL.as_posix(), "lines": [446, 451], "pdf_path": PDF_REL.as_posix(), "page": 9},
            },
            "tempo_rule": {
                "txt": lines[450],
                "txt_source_line": 451,
                "pdf": pdf_facts["page_nine_tempo_statement"],
                "pdf_page": 9,
                "fixed_bpm": None,
            },
        },
        "pdf_projection_checks": {
            "route_rows_compared": 13,
            "direction_grids_compared": pdf_grid_comparisons,
            "worked_example_matches_rung_01": True,
            "rung_13_route_labels_preserved_separately": {
                "txt": route_table[-1]["key_name"],
                "pdf": pdf_facts["route_table"][-1]["key_name"],
                "shared_route_facts_match": True,
            },
            "down_paths_summary_present": pdf_facts["page_two_has_down_paths"],
            "page_one_session_protocol_step_count": pdf_facts["page_one_session_protocol_step_count"],
            "page_ten_practice_heading": pdf_facts["page_ten_practice_heading"],
        },
        "source_discrepancies": _discrepancies(lines, pdf_facts),
        "coverage": {
            "rung_count": len(rungs),
            "pair_count": pair_count,
            "note_contact_count": contact_count,
            "minor_third_pair_count": quality_counts["m3"],
            "major_third_pair_count": quality_counts["M3"],
            "rung_numbers": [rung["rung"] for rung in rungs],
            "source_page_card_count": len(pdf_cards),
        },
        "records": rungs,
        "pending": [
            "Curriculum review and reconciliation of each recorded source difference.",
            "Canonical identity allocation, schema admission, runtime eligibility, import and admission.",
            "Any timing, starting tempo, performed repetitions or practice-history semantics.",
            "WBS parent dependencies and whole-workbook completion remain outside this detached Level27 candidate.",
        ],
    }


def serialize_candidate(candidate: dict[str, Any]) -> bytes:
    return (json.dumps(candidate, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def _lane_build(root: Path) -> Path:
    build = root / BUILD_REL
    if build.resolve() != (root / BUILD_REL).resolve():
        _fail("OUTPUT_BUILD_ROOT_MISMATCH")
    build.mkdir(parents=True, exist_ok=True)
    return build


def write_candidates() -> dict[str, Any]:
    root = _root()
    build = _lane_build(root)
    outputs = (build / "candidate-01.json", build / "candidate-02.json")
    if any(path.exists() or path.is_symlink() for path in outputs):
        _fail("OUTPUT_EXISTS")
    payload = serialize_candidate(build_candidate())
    hashes = []
    for path in outputs:
        try:
            with path.open("xb") as stream:
                stream.write(payload)
        except FileExistsError:
            _fail("OUTPUT_EXISTS")
        hashes.append(sha256(path.read_bytes()))
    if hashes[0] != hashes[1] or outputs[0].read_bytes() != outputs[1].read_bytes():
        _fail("DETERMINISM_FAILURE")
    return {
        "paths": [path.relative_to(root).as_posix() for path in outputs],
        "bytes": len(payload),
        "sha256": hashes[0],
        "identical": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-candidates", action="store_true")
    args = parser.parse_args()
    candidate = build_candidate()
    if args.write_candidates:
        materialized = write_candidates()
        print(json.dumps({"coverage": candidate["coverage"], "materialized": materialized}, sort_keys=True))
    else:
        print(json.dumps({"coverage": candidate["coverage"], "candidate_sha256": sha256(serialize_candidate(candidate))}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
