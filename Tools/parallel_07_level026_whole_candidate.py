#!/usr/bin/env python3
"""Build a detached, source-linked candidate for the whole Level 26 ladder.

Printed TAB columns preserve note order and source position. The source pulse is
instruction text, not a machine timing assertion.
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
TXT_REL = Path("Notes/music/guitar project/TXT version/Scale_Exercises_Section_III_Level_26_Natural_Minor_Four_Note_Rolling_Sequence_Two_Octave_Six_String_Neck_Ladder.txt")
PDF_REL = Path("Notes/music/guitar project/PDF version/Scale_Exercises_Section_III_Level_26_Natural_Minor_Four_Note_Rolling_Sequence_Two_Octave_Six_String_Neck_Ladder.pdf")
TXT_BYTES = 47528
TXT_SHA256 = "816ef6a286175efe575ee93d14224aaaf44111af3ea58a73f6787898b478c0f5"
PDF_BYTES = 32096
PDF_SHA256 = "c00d5751bb301d4a6b5bb66e009376218226fc90cb7f2d2fb0abbc2e0c9697d8"
BUILD_REL = Path("Build/parallel-07/2.3.1.1.1-level026-whole-r01")
KEYS = ("A", "Bb", "B", "C", "C#", "D", "Eb", "E", "F", "F#", "G", "G#", "A")
DEGREES = ("1", "2", "b3", "4", "5", "b6", "b7", "8", "9", "b10", "11", "12", "b13", "b14", "15")
OFFSETS = (0, 2, 3, 5, 7, 8, 10, 12, 14, 15, 17, 19, 20, 22, 24)
STRINGS_HIGH_TO_LOW = ("e", "B", "G", "D", "A", "E")
OPEN_MIDI = {"E": 40, "A": 45, "D": 50, "G": 55, "B": 59, "e": 64}
NATURAL_PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
POSITION_MAP = (
    ("E", 0, 1), ("E", 2, 3), ("E", 3, 4),
    ("A", 0, 1), ("A", 2, 3), ("A", 3, 4),
    ("D", 0, 1), ("D", 2, 3),
    ("G", -1, 1), ("G", 0, 2), ("G", 2, 4),
    ("B", 0, 1), ("B", 1, 2), ("B", 3, 4),
    ("e", 0, 1),
)
ASC_POSITIONS = tuple(tuple(range(i, i + 4)) for i in range(1, 13))
DESC_POSITIONS = tuple(tuple(range(16 - i, 12 - i, -1)) for i in range(1, 13))
UP_PATHS = ("EEEA", "EEAA", "EAAA", "AAAD", "AADD", "ADDG", "DDGG", "DGGG", "GGGB", "GGBB", "GBBB", "BBBe")
DOWN_PATHS = ("eBBB", "BBBG", "BBGG", "BGGG", "GGGD", "GGDD", "GDDA", "DDAA", "DAAA", "AAAE", "AAEE", "AEEE")
RUNG_TXT = re.compile(r"^RUNG (\d{2}) OF 13 - ([A-G](?:b|#)?) NATURAL MINOR( - OCTAVE)? - ROOT ON LOW E FRET (\d+) - FRAME (\d+)-(\d+)$", re.I)
RUNG_PDF = re.compile(r"^(\d{2})  ([A-G](?:b|#)?) NATURAL MINOR( - OCTAVE)?$", re.I)
PDF_ROOT = re.compile(r"^ROOT E(\d+)  \|  FRAME (\d+)-(\d+)$")
NOTE_NAME = re.compile(r"^[A-G](?:b|#)?$")
ROUTE_TOKEN = re.compile(r"([A-G](?:b|#)?)\((\d+)\)")


class CandidateError(ValueError):
    """Pinned source, authored event, route or output boundary failed."""


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


def _cells(row: str, prefix: str) -> list[str]:
    parts = row.split("|")
    if (len(parts) != 14 or parts[0] != prefix or parts[-1] != ""
        or any(re.fullmatch(r"[0-9-]{12}", part) is None for part in parts[1:-1])):
        raise CandidateError(f"GROUP_ROW_INVALID {prefix}")
    return parts[1:-1]


def _pitch_class(name: str) -> int:
    if NOTE_NAME.fullmatch(name) is None:
        raise CandidateError(f"SCALE_TONE_INVALID {name}")
    accidental = 1 if name.endswith("#") else -1 if name.endswith("b") else 0
    return (NATURAL_PC[name[0]] + accidental) % 12


def _parse_direction(rows: list[str], tones: list[str], root_fret: int, direction: str) -> dict[str, Any]:
    if len(rows) != 8 or direction not in ("ascending", "descending"):
        raise CandidateError(f"GROUP_LAYOUT_INVALID {direction}")
    position_cells = _cells(rows[0], "Pos")
    finger_cells = _cells(rows[1], "Fng")
    tab_cells = [_cells(row, string + "  ") for row, string in zip(rows[2:], STRINGS_HIGH_TO_LOW, strict=True)]
    expected_positions = ASC_POSITIONS if direction == "ascending" else DESC_POSITIONS
    expected_paths = UP_PATHS if direction == "ascending" else DOWN_PATHS
    notes: list[dict[str, Any]] = []
    groups: list[dict[str, Any]] = []
    for group_index, positions in enumerate(expected_positions):
        position_tokens = [(match.start(), int(match.group())) for match in re.finditer(r"\d+", position_cells[group_index])]
        finger_tokens = [(match.start(), int(match.group())) for match in re.finditer(r"\d+", finger_cells[group_index])]
        if tuple(position for _, position in position_tokens) != positions or len(finger_tokens) != 4:
            raise CandidateError(f"GROUP_POSITION_OR_FINGER_INVALID {direction} {group_index + 1}")
        if [column for column, _ in position_tokens] != [column for column, _ in finger_tokens]:
            raise CandidateError(f"GROUP_POSITION_FINGER_COLUMN_MISMATCH {direction} {group_index + 1}")
        found = []
        for string, cells in zip(STRINGS_HIGH_TO_LOW, tab_cells, strict=True):
            for token in re.finditer(r"\d+", cells[group_index]):
                found.append((token.start(), string, int(token.group())))
        found.sort(key=lambda item: item[0])
        if len(found) != 4 or [column for column, _, _ in found] != [column for column, _ in position_tokens]:
            raise CandidateError(f"GROUP_TAB_COLUMN_MISMATCH {direction} {group_index + 1}")
        if "".join(string for _, string, _ in found) != expected_paths[group_index]:
            raise CandidateError(f"GROUP_CROSSING_PATH_MISMATCH {direction} {group_index + 1}")
        group_notes = []
        for note_index, ((column, string, fret), (_, position), (_, finger)) in enumerate(
            zip(found, position_tokens, finger_tokens, strict=True)
        ):
            expected_string, offset, expected_finger = POSITION_MAP[position - 1]
            if (string, fret, finger) != (expected_string, root_fret + offset, expected_finger):
                raise CandidateError(f"GROUP_GEOMETRY_OR_FINGER_MISMATCH {direction} {group_index + 1} {position}")
            tone = tones[position - 1]
            midi = OPEN_MIDI[string] + fret
            if midi != OPEN_MIDI["E"] + root_fret + OFFSETS[position - 1] or midi % 12 != _pitch_class(tone):
                raise CandidateError(f"GROUP_TONE_PITCH_MISMATCH {direction} {group_index + 1} {position}")
            group_notes.append({
                "ordinal": group_index * 4 + note_index + 1,
                "group_ordinal": group_index + 1,
                "position": position, "degree": DEGREES[position - 1], "tone": tone,
                "string": string, "fret": fret, "finger_digit": finger,
                "ascii_column_in_group": column, "onset_q": None, "duration_q": None,
            })
        notes.extend(group_notes)
        groups.append({"ordinal": group_index + 1, "positions": list(positions),
                       "degrees": [DEGREES[position - 1] for position in positions],
                       "string_path": expected_paths[group_index],
                       "note_ordinals": [group_index * 4 + i + 1 for i in range(4)]})
    if len(notes) != 48:
        raise CandidateError(f"DIRECTION_NOTE_COUNT {direction}")
    return {"direction": direction, "raw_rows": rows, "groups": groups, "notes": notes}


def _route_tokens(line: str, prefix: str) -> list[tuple[str, int]]:
    if not line.startswith(prefix):
        raise CandidateError(f"TXT_ROUTE_PREFIX_INVALID {prefix}")
    payload = line.removeprefix(prefix).strip()
    parts = payload.split(" > ")
    if any(ROUTE_TOKEN.fullmatch(part) is None for part in parts):
        raise CandidateError(f"TXT_ROUTE_TOKEN_INVALID {prefix}")
    return [(match.group(1), int(match.group(2))) for part in parts if (match := ROUTE_TOKEN.fullmatch(part))]


def _txt_cards(txt: str) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    lines = txt.splitlines()
    if len(lines) != 421 or lines[:2] != [
        "SCALE EXERCISES - SECTION III, LEVEL 26",
        "NATURAL MINOR FOUR-NOTE ROLLING SEQUENCE - TWO-OCTAVE SIX-STRING NECK LADDER: A TO A",
    ]:
        raise CandidateError("TXT_HEADER_OR_LENGTH_MISMATCH")
    if lines[23] != "Two octaves: 1 2 b3 4 5 b6 b7 8 9 b10 11 12 b13 b14 15":
        raise CandidateError("TXT_NATURAL_MINOR_DEGREE_MAP_MISMATCH")
    if lines[49].removeprefix("UP:   ").split(" | ") != list(UP_PATHS) or lines[50].removeprefix("DOWN: ").split(" | ") != list(DOWN_PATHS):
        raise CandidateError("TXT_CROSSING_MAP_MISMATCH")
    if lines[55] != "The complete cell contains 12 ascending groups and 12 descending groups: 24 groups and 96 notes.":
        raise CandidateError("TXT_CELL_COUNT_MISMATCH")
    up_route = _route_tokens(lines[64], "UP:")
    down_route = _route_tokens(lines[65], "DOWN:")
    expected_up = list(zip(KEYS, range(5, 18), strict=True))
    if up_route != expected_up or down_route != list(reversed(expected_up)):
        raise CandidateError("TXT_CHROMATIC_ROUTE_MISMATCH")
    starts = [(index, match) for index, line in enumerate(lines) if (match := RUNG_TXT.fullmatch(line))]
    if tuple(index + 1 for index, _ in starts) != tuple(79 + 24 * n for n in range(13)):
        raise CandidateError("TXT_RUNG_BOUNDARY_MISMATCH")
    cards = []
    for index, (start, match) in enumerate(starts):
        number = int(match.group(1))
        key = match.group(2)[0].upper() + match.group(2)[1:].lower()
        octave = bool(match.group(3))
        root_fret, frame_low, frame_high = map(int, match.group(4, 5, 6))
        if (number, key, octave, root_fret, frame_low, frame_high) != (
            index + 1, KEYS[index], index == 12, index + 5, index + 4, index + 8
        ):
            raise CandidateError(f"TXT_RUNG_IDENTITY_MISMATCH {number}")
        body = lines[start + 1:start + 22]
        if (len(body) != 21 or not body[0].startswith("Scale tones across two octaves: ")
            or body[1] != "96-note cell: 12 ascending four-note groups, repeat the high root at the turn, then 12 descending groups."
            or body[2] != "ASCENDING - 12 GROUPS / 48 NOTES"
            or body[11] != "DESCENDING - 12 GROUPS / 48 NOTES"
            or body[20] != "Finish on the low root, release pressure, and move the entire frame one fret in the route direction."):
            raise CandidateError(f"TXT_RUNG_LAYOUT_MISMATCH {number}")
        if lines[start + 22] != "" or not lines[start + 23].startswith("==="):
            raise CandidateError(f"TXT_RUNG_SEPARATOR_MISMATCH {number}")
        tones = body[0].removeprefix("Scale tones across two octaves: ").split()
        if len(tones) != 15 or tones[0] != tones[7] or tones[7] != tones[14] or tones[0] != key:
            raise CandidateError(f"TXT_SCALE_TONES_INVALID {number}")
        tonic_pc = _pitch_class(key)
        if any(_pitch_class(tone) != (tonic_pc + offset) % 12 for tone, offset in zip(tones, OFFSETS, strict=True)):
            raise CandidateError(f"TXT_NATURAL_MINOR_TONES_INVALID {number}")
        ascending = _parse_direction(body[3:11], tones, root_fret, "ascending")
        descending = _parse_direction(body[12:20], tones, root_fret, "descending")
        high_up, high_down = ascending["notes"][-1], descending["notes"][0]
        if (high_up["position"], high_up["string"], high_up["fret"], high_down["position"],
            high_down["string"], high_down["fret"]) != (15, "e", root_fret, 15, "e", root_fret):
            raise CandidateError(f"HIGH_ROOT_REPEAT_INVALID {number}")
        if (ascending["notes"][0]["string"], ascending["notes"][0]["fret"],
            descending["notes"][-1]["string"], descending["notes"][-1]["fret"]) != (
            "E", root_fret, "E", root_fret
        ):
            raise CandidateError(f"LOW_ROOT_RETURN_INVALID {number}")
        cards.append({"rung_number": f"{number:02d}", "key": key, "octave_rung": octave,
                      "root_fret": root_fret, "frame_low": frame_low, "frame_high": frame_high,
                      "scale_tones": tones, "directions": [ascending, descending],
                      "heading_line": start + 1, "last_line": start + 22})
    if (lines[390] != "FULL ROUND-TRIP CHALLENGE"
        or lines[391] != "Play rungs 01-13, reverse after the fret-17 A-natural-minor cell, and return through rungs 12-01."
        or lines[392] != "Do not replay rung 13 at the turn. The route contains 25 cells x 96 notes = 2,400 picked notes."):
        raise CandidateError("TXT_ROUND_TRIP_MISMATCH")
    guidance = {"overview_text": "\n".join(lines[:77]), "overview_ref": "L26-TXT1-1-77",
                "challenge_text": "\n".join(lines[390:]), "challenge_ref": "L26-TXT1-391-421",
                "pdf_overview_ref": "L26-PDF1-p1", "pdf_route_ref": "L26-PDF1-p2",
                "pdf_practice_ref": "L26-PDF1-p10"}
    route = {"up_text": lines[64], "down_text": lines[65]}
    return cards, guidance, route


def _pdf_cards(pdf_data: bytes) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    try:
        reader = PdfReader(BytesIO(pdf_data), strict=True)
        if len(reader.pages) != 10:
            raise CandidateError(f"PDF_PAGE_COUNT {len(reader.pages)}")
        pages = [(page.extract_text() or "").splitlines() for page in reader.pages]
    except CandidateError:
        raise
    except Exception as exc:
        raise CandidateError(f"PDF_READ_FAILED {type(exc).__name__}") from exc
    if (pages[0][:2] != ["Scale Exercises - Section III, Level 26",
                          "Natural Minor Four-Note Rolling Sequence: Two-Octave Six-String Neck Ladder"]
        or "UP: 1-2-b3-4 | 2-b3-4-5 | ... | 11-12-b13-b14 | 12-b13-b14-15" not in pages[0]
        or "NEXT: Level 27 - Natural Minor Diatonic Thirds, Two Octaves." not in pages[9]):
        raise CandidateError("PDF_OVERVIEW_OR_PRACTICE_MISMATCH")
    route_page = pages[1]
    if route_page[:3] != ["Level 26 - Chromatic Natural-Minor Route and Sequence Map",
                          "Up: complete one 96-note cell, then move +1 fret",
                          "Down: reverse the cards, then move -1 fret"]:
        raise CandidateError("PDF_ROUTE_HEADER_MISMATCH")
    if (route_page[94].removeprefix("UP PATHS:   ").split(" | ") != list(UP_PATHS)
        or route_page[95].removeprefix("DOWN PATHS: ").split(" | ") != list(DOWN_PATHS)
        or route_page[80:82] != ["rungs 12-01; do not replay", "rung 13."]):
        raise CandidateError("PDF_ROUTE_OR_CROSSING_MISMATCH")
    table = []
    if route_page[3:8] != ["Rung", "Key", "Low-E root", "Frame", "Scale tones (degrees 1-b7)"]:
        raise CandidateError("PDF_ROUTE_TABLE_HEADER_MISMATCH")
    for index in range(13):
        number, key_label, root, frame, tones = route_page[8 + index * 5:13 + index * 5]
        expected_label = KEYS[index] + " natural minor" + (" (octave)" if index == 12 else "")
        if (number, key_label, root, frame) != (
            f"{index + 1:02d}", expected_label, f"fret {index + 5}", f"{index + 4}-{index + 8}"
        ):
            raise CandidateError(f"PDF_ROUTE_TABLE_IDENTITY_MISMATCH {index + 1}")
        table.append({"number": number, "key_label": key_label, "root_fret": index + 5,
                      "frame": frame, "tones_1_to_7": tones.split()})
    cards = []
    for page_number in range(3, 10):
        lines = pages[page_number - 1]
        count = 1 if page_number == 9 else 2
        first = 13 if page_number == 9 else 1 + (page_number - 3) * 2
        expected_title = ("Level 26 - Final Rung and Full Round-Trip Challenge" if page_number == 9
                          else "Level 26 - Natural Minor Four-Note Rolling Sequence: Two Octaves")
        if lines[0] != expected_title:
            raise CandidateError(f"PDF_CARD_PAGE_HEADER_MISMATCH {page_number}")
        starts = [(index, match) for index, line in enumerate(lines) if (match := RUNG_PDF.fullmatch(line))]
        if len(starts) != count or tuple(int(match.group(1)) for _, match in starts) != tuple(range(first, first + count)):
            raise CandidateError(f"PDF_CARD_COUNT_OR_ORDER_MISMATCH {page_number}")
        for position, (start, match) in enumerate(starts):
            stop = starts[position + 1][0] if position + 1 < count else len(lines)
            body = lines[start + 1:stop]
            root_match = PDF_ROOT.fullmatch(body[0]) if body else None
            if (root_match is None or len(body) < 23
                or not body[1].startswith("Scale tones: ")
                or body[2] != "96 NOTES / 24 GROUPS"
                or body[3] != "ASCENDING - 12 GROUPS / 48 NOTES"
                or body[12] != "DESCENDING - 12 GROUPS / 48 NOTES"
                or body[21] != "Return to the low root; release pressure; move the complete frame one fret."
                or body[22] != "Continuous alternate picking - D-start and U-start"):
                raise CandidateError(f"PDF_CARD_LAYOUT_MISMATCH {match.group(1)}")
            key = match.group(2)[0].upper() + match.group(2)[1:].lower()
            cards.append({"number": match.group(1), "key": key,
                          "octave_rung": bool(match.group(3)), "root_fret": int(root_match.group(1)),
                          "frame_low": int(root_match.group(2)), "frame_high": int(root_match.group(3)),
                          "scale_tones": body[1].removeprefix("Scale tones: ").split(),
                          "ascending_rows": body[4:12], "descending_rows": body[13:21],
                          "pdf_page": page_number})
    if ("25 cells x 96 notes = 2,400 picked notes." not in pages[8]
        or "Down pass: use rungs 12-01; do not replay rung 13" not in pages[8]):
        raise CandidateError("PDF_ROUND_TRIP_MISMATCH")
    return cards, table


def build_candidate(*, txt_data: bytes | None = None, pdf_data: bytes | None = None) -> dict[str, Any]:
    root = _root()
    txt_data = _source_bytes(root, TXT_REL) if txt_data is None else txt_data
    pdf_data = _source_bytes(root, PDF_REL) if pdf_data is None else pdf_data
    _verify(txt_data, TXT_BYTES, TXT_SHA256, "L26-TXT")
    _verify(pdf_data, PDF_BYTES, PDF_SHA256, "L26-PDF")
    try:
        txt_cards, guidance, raw_route = _txt_cards(txt_data.decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise CandidateError("TXT_ENCODING_INVALID") from exc
    pdf_cards, pdf_table = _pdf_cards(pdf_data)
    # Page 1 repeats the complete first card as the worked example.
    first_page = (PdfReader(BytesIO(pdf_data)).pages[0].extract_text() or "").splitlines()
    first_up = first_page.index("ASCENDING - 12 GROUPS / 48 NOTES")
    first_down = first_page.index("DESCENDING - 12 GROUPS / 48 NOTES")
    if (first_page[first_up + 1:first_up + 9] != txt_cards[0]["directions"][0]["raw_rows"]
        or first_page[first_down + 1:first_down + 9] != txt_cards[0]["directions"][1]["raw_rows"]):
        raise CandidateError("PDF_WORKED_EXAMPLE_MISMATCH")
    records = []
    for index, (txt_card, pdf_card, pdf_row) in enumerate(zip(txt_cards, pdf_cards, pdf_table, strict=True)):
        number = txt_card["rung_number"]
        if (pdf_card["number"], pdf_card["key"], pdf_card["octave_rung"], pdf_card["root_fret"],
            pdf_card["frame_low"], pdf_card["frame_high"], pdf_card["scale_tones"],
            pdf_card["ascending_rows"], pdf_card["descending_rows"]) != (
            number, txt_card["key"], txt_card["octave_rung"], txt_card["root_fret"],
            txt_card["frame_low"], txt_card["frame_high"], txt_card["scale_tones"],
            txt_card["directions"][0]["raw_rows"], txt_card["directions"][1]["raw_rows"]
        ):
            raise CandidateError(f"PDF_TXT_CARD_MISMATCH {number}")
        if pdf_row["tones_1_to_7"] != txt_card["scale_tones"][:7]:
            raise CandidateError(f"PDF_ROUTE_TONES_MISMATCH {number}")
        if index:
            baseline = txt_cards[0]
            for direction, first_direction in zip(txt_card["directions"], baseline["directions"], strict=True):
                for note, first_note in zip(direction["notes"], first_direction["notes"], strict=True):
                    if (note["string"], note["fret"], note["position"], note["finger_digit"], note["group_ordinal"]) != (
                        first_note["string"], first_note["fret"] + index, first_note["position"],
                        first_note["finger_digit"], first_note["group_ordinal"]
                    ):
                        raise CandidateError(f"RUNG_TRANSPOSED_ROUTE_MISMATCH {number}")
        records.append({
            "source_local_key": f"L26-rung{number}", "rung_number": number,
            "key": txt_card["key"], "octave_rung": txt_card["octave_rung"],
            "root_string": "E", "root_fret": txt_card["root_fret"],
            "frame_low": txt_card["frame_low"], "frame_high": txt_card["frame_high"],
            "scale_tones": txt_card["scale_tones"], "degree_map": list(DEGREES),
            "directions": txt_card["directions"],
            "source_refs": {"txt": f"L26-TXT1-{txt_card['heading_line']}-{txt_card['last_line']}",
                            "pdf_card": f"L26-PDF1-p{pdf_card['pdf_page']}",
                            "pdf_route": "L26-PDF1-p2"},
            "canonical_item_id": None, "canonical_variant_id": None,
            "onset_q": None, "duration_q": None, "fixed_bpm": None, "note_per_click": None,
            "runtime_eligible": False, "runtime_admitted": False, "imported": False, "admitted": False,
        })
    up = [record["source_local_key"] for record in records]
    down_standalone = list(reversed(up))
    return_down = down_standalone[1:]
    return {
        "schema": "fathom-level026-whole-detached-candidate-v1", "wbs_id": "2.3.1.1.1", "level": 26,
        "source": {"txt_path": TXT_REL.as_posix(), "txt_bytes": TXT_BYTES, "txt_sha256": TXT_SHA256,
                   "pdf_path": PDF_REL.as_posix(), "pdf_bytes": PDF_BYTES, "pdf_sha256": PDF_SHA256,
                   "pdf_pages": 10, "selected_pdf_card_pages": list(range(3, 10))},
        "instructions": guidance,
        "shape": {"position_map": [{"position": i + 1, "string": string, "fret_offset_from_root": offset,
                                     "finger_digit": finger, "degree": DEGREES[i]}
                                    for i, (string, offset, finger) in enumerate(POSITION_MAP)],
                  "up_crossing_paths": list(UP_PATHS), "down_crossing_paths": list(DOWN_PATHS),
                  "source_refs": ["L26-TXT1-22-36", "L26-TXT1-49-53", "L26-PDF1-p2"]},
        "routes": {"up": {"rungs": up, "root_frets": list(range(5, 18)),
                          "shift_frets_between_cells": 1, "source_text": raw_route["up_text"],
                          "source_refs": ["L26-TXT1-65", "L26-PDF1-p2"]},
                   "down_standalone": {"rungs": down_standalone, "root_frets": list(range(17, 4, -1)),
                                       "shift_frets_between_cells": -1,
                                       "source_text": raw_route["down_text"],
                                       "source_refs": ["L26-TXT1-66", "L26-PDF1-p2"]},
                   "down_return": {"rungs": return_down, "root_frets": list(range(16, 4, -1)),
                                   "shift_frets_between_cells": -1,
                                   "source_refs": ["L26-TXT1-391-393", "L26-PDF1-p9"]},
                   "continuous_round_trip": {"rungs": up + return_down,
                                             "turn_after_rung": "L26-rung13", "cell_count": 25,
                                             "picked_note_count": 2400,
                                             "source_refs": ["L26-TXT1-391-393", "L26-PDF1-p9"]}},
        "records": records, "exceptions": [],
        "pending": ["Curriculum/musical review", "canonical identity allocation and admission",
                    "runtime note timing and performed audio"],
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
    return {"output": str(target.relative_to(root)), "bytes": len(data), "sha256": digest(data),
            "records": len(candidate["records"])}


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
