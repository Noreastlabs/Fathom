#!/usr/bin/env python3
"""Build a detached, source-linked candidate for the whole Level 18 thirds ladder.

The two notes of each printed pair are sequential. TAB columns are source
positions, not a clock or note-duration claim.
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
TXT_REL = Path("Notes/music/guitar project/TXT version/Scale_Exercises_Section_II_Level_18_Major_Scale_Diatonic_Thirds_Two_Octave_Six_String_Neck_Ladder.txt")
PDF_REL = Path("Notes/music/guitar project/PDF version/Scale_Exercises_Section_II_Level_18_Major_Scale_Diatonic_Thirds_Two_Octave_Six_String_Neck_Ladder.pdf")
TXT_BYTES = 35270
TXT_SHA256 = "a4faf2579a2d3546e2dc021640eeb3764ec7de9d858975a66f29f9611e2ad3a8"
PDF_BYTES = 30110
PDF_SHA256 = "a79374066ff017c148c11ec75791b02ba930560123dde1a6fcc933fe17821536"
BUILD_REL = Path("Build/parallel-07/2.3.1.1.1-level018-whole-r01")
KEYS = ("A", "Bb", "B", "C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A")
STRINGS_HIGH_TO_LOW = ("e", "B", "G", "D", "A", "E")
OPEN_MIDI = {"E": 40, "A": 45, "D": 50, "G": 55, "B": 59, "e": 64}
NATURAL_PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
ASC_DEGREES = tuple((n, n + 2) for n in range(1, 14))
DESC_DEGREES = tuple((15 - n, 13 - n) for n in range(13))
ASC_QUALITY = ("M3", "m3", "m3", "M3", "M3", "m3", "m3", "M3", "m3", "m3", "M3", "M3", "m3")
DESC_QUALITY = tuple(reversed(ASC_QUALITY))
RUNG_TXT = re.compile(r"^RUNG (\d{2}) OF 13 - ([A-G](?:b|#)?) MAJOR( - OCTAVE)? - ROOT ON LOW E FRET (\d+) - FRAME (\d+)-(\d+)$")
RUNG_PDF = re.compile(r"^(\d{2})  ([A-G](?:b|#)?) MAJOR( - OCTAVE)?$")
PDF_ROOT = re.compile(r"^ROOT E(\d+)  \|  FRAME (\d+)-(\d+)$")
TXT_TABLE = re.compile(r"^(\d{2})\s+([A-G](?:b|#)?) major( - octave)?\s+fret (\d+)\s+(\d+)-(\d+)\s+(.+)$")
NOTE_NAME = re.compile(r"^[A-G](?:b|#)?$")


class CandidateError(ValueError):
    """A pinned source, authored pair, route, or output boundary failed."""


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


def _segments(row: str, prefix: str) -> list[str]:
    parts = row.split("|")
    if len(parts) != 15 or parts[0] != prefix or parts[-1] != "" or any(len(segment) != 6 for segment in parts[1:-1]):
        raise CandidateError(f"PAIR_ROW_INVALID {prefix}")
    return parts[1:-1]


def _pitch_class(name: str) -> int:
    if NOTE_NAME.fullmatch(name) is None:
        raise CandidateError(f"SCALE_TONE_INVALID {name}")
    accidental = 1 if name.endswith("#") else -1 if name.endswith("b") else 0
    return (NATURAL_PC[name[0]] + accidental) % 12


def _parse_direction(rows: list[str], tones: list[str], direction: str) -> dict[str, Any]:
    if len(rows) != 9 or direction not in ("ascending", "descending"):
        raise CandidateError(f"PAIR_LAYOUT_INVALID {direction}")
    quality_cells = _segments(rows[0], "Int")
    degree_cells = _segments(rows[1], "Deg")
    finger_cells = _segments(rows[2], "Fng")
    tab_cells = [_segments(row, string + "  ") for row, string in zip(rows[3:], STRINGS_HIGH_TO_LOW, strict=True)]
    expected_degrees = ASC_DEGREES if direction == "ascending" else DESC_DEGREES
    expected_quality = ASC_QUALITY if direction == "ascending" else DESC_QUALITY
    notes = []
    pairs = []
    for pair_index in range(13):
        quality_match = re.fullmatch(r"(M3|m3)-{4}", quality_cells[pair_index])
        if quality_match is None or quality_match.group(1) != expected_quality[pair_index]:
            raise CandidateError(f"PAIR_QUALITY_PATTERN_MISMATCH {direction} {pair_index + 1}")
        degree_tokens = [(m.start(), int(m.group())) for m in re.finditer(r"\d+", degree_cells[pair_index])]
        finger_tokens = [(m.start(), int(m.group())) for m in re.finditer(r"\d+", finger_cells[pair_index])]
        if (tuple(value for _, value in degree_tokens) != expected_degrees[pair_index]
            or len(finger_tokens) != 2 or any(not 1 <= finger <= 4 for _, finger in finger_tokens)):
            raise CandidateError(f"PAIR_DEGREE_OR_FINGER_INVALID {direction} {pair_index + 1}")
        if tuple(column for column, _ in degree_tokens) != tuple(column for column, _ in finger_tokens):
            raise CandidateError(f"PAIR_DEGREE_FINGER_COLUMN_MISMATCH {direction} {pair_index + 1}")
        found = []
        for string, cells in zip(STRINGS_HIGH_TO_LOW, tab_cells, strict=True):
            for token in re.finditer(r"\d+", cells[pair_index]):
                found.append((token.start(), string, int(token.group())))
        found.sort(key=lambda item: item[0])
        if len(found) != 2 or tuple(column for column, _, _ in found) != tuple(column for column, _ in degree_tokens):
            raise CandidateError(f"PAIR_TAB_COLUMN_MISMATCH {direction} {pair_index + 1}")
        pair_notes = []
        for note_index, ((column, string, fret), (_, degree), (_, finger)) in enumerate(
            zip(found, degree_tokens, finger_tokens, strict=True)
        ):
            tone = tones[degree - 1]
            midi = OPEN_MIDI[string] + fret
            if midi % 12 != _pitch_class(tone):
                raise CandidateError(f"PAIR_TONE_PITCH_MISMATCH {direction} {pair_index + 1} {tone}")
            pair_notes.append({
                "ordinal": pair_index * 2 + note_index + 1, "pair_ordinal": pair_index + 1,
                "degree": degree, "tone": tone, "string": string, "fret": fret,
                "finger_digit": finger, "ascii_column_in_pair": column,
                "onset_q": None, "duration_q": None,
            })
        semitones = abs((OPEN_MIDI[pair_notes[1]["string"]] + pair_notes[1]["fret"])
                        - (OPEN_MIDI[pair_notes[0]["string"]] + pair_notes[0]["fret"]))
        quality = quality_match.group(1)
        if semitones != (4 if quality == "M3" else 3):
            raise CandidateError(f"PAIR_QUALITY_SEMITONE_MISMATCH {direction} {pair_index + 1}")
        notes.extend(pair_notes)
        pairs.append({"ordinal": pair_index + 1, "degrees": list(expected_degrees[pair_index]),
                      "quality": quality, "semitones": semitones,
                      "note_ordinals": [pair_index * 2 + 1, pair_index * 2 + 2]})
    if len(notes) != 26:
        raise CandidateError(f"DIRECTION_NOTE_COUNT {direction}")
    return {"direction": direction, "raw_rows": rows, "pairs": pairs, "notes": notes}


def _txt_cards(txt: str) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    lines = txt.splitlines()
    if len(lines) != 459 or lines[:2] != [
        "SCALE EXERCISES - SECTION II, LEVEL 18",
        "MAJOR SCALE DIATONIC THIRDS - TWO-OCTAVE SIX-STRING NECK LADDER",
    ]:
        raise CandidateError("TXT_HEADER_OR_LENGTH_MISMATCH")
    starts = [(index, match) for index, line in enumerate(lines) if (match := RUNG_TXT.fullmatch(line))]
    if tuple(index + 1 for index, _ in starts) != tuple(72 + 27 * n for n in range(13)):
        raise CandidateError("TXT_RUNG_BOUNDARY_MISMATCH")
    cards = []
    for index, (start, match) in enumerate(starts):
        number = int(match.group(1))
        key = match.group(2)
        octave = bool(match.group(3))
        root_fret, frame_low, frame_high = map(int, match.group(4, 5, 6))
        if (number, key, octave, root_fret, frame_low, frame_high) != (
            index + 1, KEYS[index], index == 12, index + 5, index + 4, index + 7
        ):
            raise CandidateError(f"TXT_RUNG_IDENTITY_MISMATCH {number}")
        body = lines[start + 1:start + 24]
        if (len(body) != 23 or not body[0].startswith("Scale tones across two octaves: ")
            or body[1] != "52-note cell: 13 ascending third pairs, repeat the high root at the turn, then 13 descending pairs."
            or body[2] != "ASCENDING - 13 PAIRS / 26 NOTES"
            or body[12] != "DESCENDING - 13 PAIRS / 26 NOTES"
            or body[22] != "Finish on the low root, release pressure, and move the entire frame one fret in the route direction."):
            raise CandidateError(f"TXT_RUNG_LAYOUT_MISMATCH {number}")
        if lines[start + 24] != "" or not lines[start + 25].startswith("===") or lines[start + 26] != "":
            raise CandidateError(f"TXT_RUNG_SEPARATOR_MISMATCH {number}")
        tones = body[0].removeprefix("Scale tones across two octaves: ").split()
        if len(tones) != 15 or not (tones[0] == tones[7] == tones[14]) or tones[0] != key:
            raise CandidateError(f"TXT_SCALE_TONES_INVALID {number}")
        ascending = _parse_direction(body[3:12], tones, "ascending")
        descending = _parse_direction(body[13:22], tones, "descending")
        high_up, high_down = ascending["notes"][-1], descending["notes"][0]
        if (high_up["degree"], high_up["string"], high_up["fret"]) != (
            15, high_down["string"], high_down["fret"]
        ) or high_down["degree"] != 15:
            raise CandidateError(f"HIGH_ROOT_REPEAT_INVALID {number}")
        low_up, low_down = ascending["notes"][0], descending["notes"][-1]
        if (low_up["string"], low_up["fret"], low_down["string"], low_down["fret"]) != ("E", root_fret, "E", root_fret):
            raise CandidateError(f"LOW_ROOT_RETURN_INVALID {number}")
        if OPEN_MIDI[high_up["string"]] + high_up["fret"] != OPEN_MIDI["E"] + root_fret + 24:
            raise CandidateError(f"TWO_OCTAVE_SPAN_INVALID {number}")
        cards.append({"rung_number": f"{number:02d}", "key": key, "octave_rung": octave,
                      "root_fret": root_fret, "frame_low": frame_low, "frame_high": frame_high,
                      "scale_tones": tones, "directions": [ascending, descending],
                      "heading_line": start + 1, "last_line": start + 24})
    if lines[422] != "FULL ROUND-TRIP CHALLENGE" or not any("25 cells x 52 notes = 1,300 picked notes." in line for line in lines[422:]):
        raise CandidateError("TXT_CHALLENGE_BOUNDARY_MISMATCH")
    up_keys = [key.strip() for key in lines[46].removeprefix("Up:").split("->")]
    down_keys = [key.strip() for key in lines[47].removeprefix("Down:").split("->")]
    if up_keys != list(KEYS) or down_keys != list(reversed(KEYS[:-1])):
        raise CandidateError("TXT_CHROMATIC_ROUTE_MISMATCH")
    table = []
    for index, line in enumerate(lines[53:66]):
        match = TXT_TABLE.fullmatch(line)
        if match is None:
            raise CandidateError(f"TXT_ROUTE_TABLE_ROW_INVALID {index + 1}")
        number, key, octave, root_fret, low, high, tones = match.groups()
        if (int(number), key, bool(octave), int(root_fret), int(low), int(high)) != (
            index + 1, KEYS[index], index == 12, index + 5, index + 4, index + 7
        ):
            raise CandidateError(f"TXT_ROUTE_TABLE_IDENTITY_MISMATCH {index + 1}")
        table.append({"number": number, "key": key + " major" + (" - octave" if octave else ""), "root_fret": int(root_fret),
                      "frame": f"{low}-{high}", "tones_1_to_7": tones.split()})
    overview = "\n".join(lines[:70])
    for phrase in ("13 ascending pairs / 26 notes", "52 notes total per key", "The quality is determined by the major key",
                   "Do not replay the high A-major rung"):
        if phrase not in overview:
            raise CandidateError(f"TXT_OVERVIEW_MISMATCH {phrase}")
    guidance = {"overview_text": overview, "overview_ref": "L18-TXT1-1-70",
                "challenge_text": "\n".join(lines[422:459]), "challenge_ref": "L18-TXT1-423-459",
                "pdf_overview_ref": "L18-PDF1-p1", "pdf_route_ref": "L18-PDF1-p2",
                "pdf_practice_ref": "L18-PDF1-p10"}
    routes = {"up_text": lines[46], "down_text": lines[47]}
    return cards, guidance, routes, table


def _pdf_cards(pdf_data: bytes) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    try:
        reader = PdfReader(BytesIO(pdf_data), strict=True)
        if len(reader.pages) != 10:
            raise CandidateError(f"PDF_PAGE_COUNT {len(reader.pages)}")
        pages = [(page.extract_text() or "").splitlines() for page in reader.pages]
    except CandidateError:
        raise
    except Exception as exc:
        raise CandidateError(f"PDF_READ_FAILED {type(exc).__name__}") from exc
    if "26 pairs. 52 notes. One interval line." not in pages[0] or not any("Level 19 stacks" in line for line in pages[9]):
        raise CandidateError("PDF_OVERVIEW_OR_PRACTICE_MISMATCH")
    route_page = pages[1]
    if route_page[:3] != ["Level 18 - Chromatic Major-Key Route and Diatonic-Third Map",
                          "Ascending route: complete one 52-note thirds cell, then move the frame +1 fret",
                          "Descending route: use the same cards in reverse order and move -1 fret"]:
        raise CandidateError("PDF_ROUTE_HEADER_MISMATCH")
    table_start = route_page.index("Scale tones (degrees 1-7)") + 1
    table_lines = route_page[table_start:table_start + 65]
    if len(table_lines) != 65 or "rungs 01-13." not in route_page or "rungs 12-01. Do not replay" not in route_page:
        raise CandidateError("PDF_ROUTE_TABLE_MISMATCH")
    table = []
    for index in range(13):
        number, key, root, frame, tones = table_lines[index * 5:index * 5 + 5]
        if number != f"{index + 1:02d}" or root != f"fret {index + 5}" or frame != f"{index + 4}-{index + 7}":
            raise CandidateError(f"PDF_ROUTE_ROW_IDENTITY_MISMATCH {index + 1}")
        table.append({"number": number, "key": key, "root_fret": index + 5,
                      "frame": frame, "tones_1_to_7": tones.split()})
    quality_index = route_page.index("UP QUALITY:")
    quality = [part.strip() for part in route_page[quality_index + 1].split("|")]
    if tuple(quality) != ASC_QUALITY:
        raise CandidateError("PDF_UP_QUALITY_PATTERN_MISMATCH")
    cards = []
    for page_number in range(3, 10):
        lines = pages[page_number - 1]
        count = 1 if page_number == 9 else 2
        first = 13 if page_number == 9 else 1 + (page_number - 3) * 2
        expected_title = ("Level 18 - Final Rung and Full Round-Trip Challenge" if page_number == 9
                          else "Level 18 - Major Scale Diatonic Thirds: Two Octaves")
        if lines[0] != expected_title:
            raise CandidateError(f"PDF_CARD_PAGE_HEADER_MISMATCH {page_number}")
        starts = [(index, match) for index, line in enumerate(lines) if (match := RUNG_PDF.fullmatch(line))]
        if len(starts) != count or tuple(int(match.group(1)) for _, match in starts) != tuple(range(first, first + count)):
            raise CandidateError(f"PDF_CARD_COUNT_OR_ORDER_MISMATCH {page_number}")
        for position, (start, match) in enumerate(starts):
            stop = starts[position + 1][0] if position + 1 < count else len(lines)
            body = lines[start + 1:stop]
            if len(body) < 23 or body[1] != "52 NOTES / 26 PAIRS" or not body[2].startswith("Scale tones: ") or body[3] != "ASCENDING - 13 PAIRS / 26 NOTES" or body[12] != "DESCENDING - 13 PAIRS / 26 NOTES":
                raise CandidateError(f"PDF_CARD_LAYOUT_MISMATCH {match.group(1)}")
            root_match = PDF_ROOT.fullmatch(body[0])
            if root_match is None or body[21] != "Return to the low root; release pressure; move the entire frame one fret." or body[22] != "Pair pulse: D-U or U-D; do not reset":
                raise CandidateError(f"PDF_CARD_LAYOUT_MISMATCH {match.group(1)}")
            if page_number == 9 and ("25 cells x 52 notes = 1,300 picked notes." not in body[23:]
                                     or "Do not replay rung 13 during the down pass unless beginning a new round" not in lines):
                raise CandidateError("PDF_ROUND_TRIP_MISMATCH")
            cards.append({"number": match.group(1), "key": match.group(2),
                          "octave_rung": bool(match.group(3)), "root_fret": int(root_match.group(1)),
                          "frame_low": int(root_match.group(2)), "frame_high": int(root_match.group(3)),
                          "scale_tones": body[2].removeprefix("Scale tones: ").split(),
                          "ascending_rows": body[4:12], "descending_rows": body[13:21],
                          "pdf_page": page_number})
    return cards, table, quality


def build_candidate(*, txt_data: bytes | None = None, pdf_data: bytes | None = None) -> dict[str, Any]:
    root = _root()
    txt_data = _source_bytes(root, TXT_REL) if txt_data is None else txt_data
    pdf_data = _source_bytes(root, PDF_REL) if pdf_data is None else pdf_data
    _verify(txt_data, TXT_BYTES, TXT_SHA256, "L18-TXT")
    _verify(pdf_data, PDF_BYTES, PDF_SHA256, "L18-PDF")
    try:
        txt_cards, guidance, raw_routes, txt_table = _txt_cards(txt_data.decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise CandidateError("TXT_ENCODING_INVALID") from exc
    pdf_cards, pdf_table, quality = _pdf_cards(pdf_data)
    if tuple(quality) != ASC_QUALITY:
        raise CandidateError("PDF_QUALITY_MISMATCH")
    records = []
    for index, (txt_card, pdf_card, txt_row, pdf_row) in enumerate(
        zip(txt_cards, pdf_cards, txt_table, pdf_table, strict=True)
    ):
        number = txt_card["rung_number"]
        if (pdf_card["number"], pdf_card["key"], pdf_card["octave_rung"], pdf_card["root_fret"],
            pdf_card["frame_low"], pdf_card["frame_high"], pdf_card["scale_tones"],
            pdf_card["ascending_rows"], pdf_card["descending_rows"]) != (
            number, txt_card["key"], txt_card["octave_rung"], txt_card["root_fret"],
            txt_card["frame_low"], txt_card["frame_high"], txt_card["scale_tones"],
            txt_card["directions"][0]["raw_rows"][1:], txt_card["directions"][1]["raw_rows"][1:]
        ):
            raise CandidateError(f"PDF_TXT_CARD_MISMATCH {number}")
        key_label = txt_card["key"] + " major" + (" - octave" if txt_card["octave_rung"] else "")
        for row in (txt_row, pdf_row):
            if (row["number"], row["key"], row["root_fret"], row["frame"], row["tones_1_to_7"]) != (
                number, key_label, txt_card["root_fret"],
                f"{txt_card['frame_low']}-{txt_card['frame_high']}", txt_card["scale_tones"][:7]
            ):
                raise CandidateError(f"ROUTE_TABLE_CARD_MISMATCH {number}")
        if index > 0:
            baseline = txt_cards[0]
            for direction, first_direction in zip(txt_card["directions"], baseline["directions"], strict=True):
                for note, first_note in zip(direction["notes"], first_direction["notes"], strict=True):
                    if (note["string"], note["fret"], note["degree"], note["finger_digit"], note["pair_ordinal"]) != (
                        first_note["string"], first_note["fret"] + index, first_note["degree"],
                        first_note["finger_digit"], first_note["pair_ordinal"]
                    ):
                        raise CandidateError(f"RUNG_TRANSPOSED_ROUTE_MISMATCH {number}")
        records.append({
            "source_local_key": f"L18-rung{number}", "rung_number": number,
            "key": txt_card["key"], "octave_rung": txt_card["octave_rung"],
            "root_string": "E", "root_fret": txt_card["root_fret"],
            "frame_low": txt_card["frame_low"], "frame_high": txt_card["frame_high"],
            "scale_tones": txt_card["scale_tones"], "directions": txt_card["directions"],
            "pdf_card_has_int_row": False,
            "source_refs": {"txt": f"L18-TXT1-{txt_card['heading_line']}-{txt_card['last_line']}",
                            "pdf_card": f"L18-PDF1-p{pdf_card['pdf_page']}",
                            "pdf_route_quality": "L18-PDF1-p2"},
            "canonical_item_id": None, "canonical_variant_id": None,
            "onset_q": None, "duration_q": None, "fixed_bpm": None, "note_per_click": None,
            "runtime_eligible": False, "runtime_admitted": False, "imported": False, "admitted": False,
        })
    up = [record["source_local_key"] for record in records]
    return_down = list(reversed(up[:-1]))
    return {
        "schema": "fathom-level018-whole-detached-candidate-v1", "wbs_id": "2.3.1.1.1", "level": 18,
        "source": {"txt_path": TXT_REL.as_posix(), "txt_bytes": TXT_BYTES, "txt_sha256": TXT_SHA256,
                   "pdf_path": PDF_REL.as_posix(), "pdf_bytes": PDF_BYTES, "pdf_sha256": PDF_SHA256,
                   "pdf_pages": 10, "selected_pdf_card_pages": list(range(3, 10))},
        "instructions": guidance,
        "routes": {"up": {"rungs": up, "root_frets": list(range(5, 18)),
                          "shift_frets_between_cells": 1, "source_text": raw_routes["up_text"],
                          "source_refs": ["L18-TXT1-47", "L18-PDF1-p2"]},
                   "down_return": {"rungs": return_down, "root_frets": list(range(16, 4, -1)),
                                   "shift_frets_between_cells": -1, "source_text": raw_routes["down_text"],
                                   "source_refs": ["L18-TXT1-48-49", "L18-PDF1-p2", "L18-PDF1-p9"]},
                   "continuous_round_trip": {"rungs": up + return_down,
                                             "turn_after_rung": "L18-rung13", "cell_count": 25,
                                             "picked_note_count": 1300,
                                             "source_refs": ["L18-TXT1-423-429", "L18-PDF1-p9"]}},
        "records": records, "exceptions": [{"kind": "pdf_layout", "detail": "PDF card pages omit per-card Int rows; the common ascending quality pattern is on PDF page 2 and agrees with all pinned TXT cards and semitone checks."}],
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
