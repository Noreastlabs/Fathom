#!/usr/bin/env python3
"""Build a detached, source-linked candidate for the whole Level 32 ladder.

Each printed TAB contact becomes a distinct ordered event, including overlap and
module-boundary repetitions. Source pulse/beat counts are instruction, not a clock.
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
TXT_REL = Path("Notes/music/guitar project/TXT version/Scale_Exercises_Section_IV_Level_32_Major_Pentatonic_Three_Note_Roll_and_Five_Note_Cycle_Two_Octave_Six_String_Neck_Ladder.txt")
PDF_REL = Path("Notes/music/guitar project/PDF version/Scale_Exercises_Section_IV_Level_32_Major_Pentatonic_Three_Note_Roll_and_Five_Note_Cycle_Two_Octave_Six_String_Neck_Ladder.pdf")
TXT_BYTES = 60667
TXT_SHA256 = "574eddbeedabd9afbb2e1e08cbc270bcb9966ea752c55eb87bb348957492217e"
PDF_BYTES = 45850
PDF_SHA256 = "9e587c3eb6df807dc872ea7ff1cfdb30fcb7e461902e41314de7bc22a7589371"
BUILD_REL = Path("Build/parallel-07/2.3.1.1.1-level032-whole-r01")
KEYS = ("A", "Bb", "B", "C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A")
DEGREES = (1, 2, 3, 5, 6, 8, 9, 10, 12, 13, 15)
OFFSETS = (0, 2, 4, 7, 9, 12, 14, 16, 19, 21, 24)
POSITION_MAP = (("E", 0, 2), ("E", 2, 4), ("A", -1, 1), ("A", 2, 4),
                ("D", -1, 1), ("D", 2, 4), ("G", -1, 1), ("G", 1, 3),
                ("B", 0, 2), ("B", 2, 4), ("e", 0, 2))
STRINGS_HIGH_TO_LOW = ("e", "B", "G", "D", "A", "E")
OPEN_MIDI = {"E": 40, "A": 45, "D": 50, "G": 55, "B": 59, "e": 64}
NATURAL_PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
PATHS = {
    "A": {"ascending": ("EEA", "EAA", "AAD", "ADD", "DDG", "DGG", "GGB", "GBB", "BBe"),
          "descending": ("eBB", "BBG", "BGG", "GGD", "GDD", "DDA", "DAA", "AAE", "AEE")},
    "B": {"ascending": ("EEAAD", "EAADD", "AADDG", "ADDGG", "DDGGB", "DGGBB", "GGBBe"),
          "descending": ("eBBGG", "BBGGD", "BGGDD", "GGDDA", "GDDAA", "DDAAE", "DAAEE")},
}
MODULES = {"A": {"size": 3, "groups_each_direction": 9, "group_name": "TRIPLETS", "note_count": 54,
                 "header": "MODULE A - THREE-NOTE ROLL"},
           "B": {"size": 5, "groups_each_direction": 7, "group_name": "QUINTUPLETS", "note_count": 70,
                 "header": "MODULE B - FIVE-NOTE CYCLE"}}
RUNG_TXT = re.compile(r"^RUNG (\d{2}) OF 13 - ([A-G](?:b|#)?) MAJOR PENTATONIC( - OCTAVE)? - ROOT ON LOW E FRET (\d+) - FRAME (\d+)-(\d+)$", re.I)
RUNG_PDF = re.compile(r"^(\d{2})  ([A-G](?:b|#)?) MAJOR PENTATONIC( - OCTAVE)?   \|   LOW-E ROOT FRET (\d+)   \|   FRAME (\d+)-(\d+)$", re.I)
NOTE_NAME = re.compile(r"^[A-G](?:b|#)?$")
ROUTE_TOKEN = re.compile(r"([A-G](?:b|#)?)\((\d+)\)")


class CandidateError(ValueError):
    """Pinned source, authored contact, route or output boundary failed."""


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


def _key(value: str) -> str:
    return value[0].upper() + value[1:].lower()


def _pitch_class(name: str) -> int:
    if NOTE_NAME.fullmatch(name) is None:
        raise CandidateError(f"SCALE_TONE_INVALID {name}")
    accidental = 1 if name.endswith("#") else -1 if name.endswith("b") else 0
    return (NATURAL_PC[name[0]] + accidental) % 12


def _cells(row: str, prefix: str, group_count: int, width: int) -> list[str]:
    parts = row.split("|")
    if (len(parts) != group_count + 2 or parts[0] != prefix or parts[-1] != ""
        or any(re.fullmatch(rf"[0-9-]{{{width}}}", part) is None for part in parts[1:-1])):
        raise CandidateError(f"GROUP_ROW_INVALID {prefix}")
    return parts[1:-1]


def _expected_degrees(module: str, direction: str) -> tuple[tuple[int, ...], ...]:
    size = MODULES[module]["size"]
    count = MODULES[module]["groups_each_direction"]
    if direction == "ascending":
        return tuple(tuple(DEGREES[index:index + size]) for index in range(count))
    return tuple(tuple(reversed(DEGREES[11 - size - index:11 - index])) for index in range(count))


def _parse_direction(rows: list[str], path_line: str, tones: list[str], root_fret: int,
                     module: str, direction: str) -> dict[str, Any]:
    if len(rows) != 8 or module not in MODULES or direction not in ("ascending", "descending"):
        raise CandidateError(f"GROUP_LAYOUT_INVALID {module} {direction}")
    size = MODULES[module]["size"]
    count = MODULES[module]["groups_each_direction"]
    width = size * 3
    paths = PATHS[module][direction]
    if path_line != "PATH " + " | ".join(paths):
        raise CandidateError(f"GROUP_PRINTED_PATH_MISMATCH {module} {direction}")
    degree_cells = _cells(rows[0], "Deg", count, width)
    finger_cells = _cells(rows[1], "Fng", count, width)
    tab_cells = [_cells(row, string + "  ", count, width)
                 for row, string in zip(rows[2:], STRINGS_HIGH_TO_LOW, strict=True)]
    expected = _expected_degrees(module, direction)
    groups = []
    notes = []
    for group_index, degrees in enumerate(expected):
        degree_tokens = [(match.start(), int(match.group())) for match in re.finditer(r"\d+", degree_cells[group_index])]
        finger_tokens = [(match.start(), int(match.group())) for match in re.finditer(r"\d+", finger_cells[group_index])]
        if tuple(degree for _, degree in degree_tokens) != degrees or len(finger_tokens) != size:
            raise CandidateError(f"GROUP_DEGREE_OR_FINGER_INVALID {module} {direction} {group_index + 1}")
        if [column for column, _ in degree_tokens] != [column for column, _ in finger_tokens]:
            raise CandidateError(f"GROUP_DEGREE_FINGER_COLUMN_MISMATCH {module} {direction} {group_index + 1}")
        found = []
        for string, cells in zip(STRINGS_HIGH_TO_LOW, tab_cells, strict=True):
            for token in re.finditer(r"\d+", cells[group_index]):
                found.append((token.start(), string, int(token.group())))
        found.sort(key=lambda item: item[0])
        if len(found) != size or [column for column, _, _ in found] != [column for column, _ in degree_tokens]:
            raise CandidateError(f"GROUP_TAB_COLUMN_MISMATCH {module} {direction} {group_index + 1}")
        if "".join(string for _, string, _ in found) != paths[group_index]:
            raise CandidateError(f"GROUP_CROSSING_PATH_MISMATCH {module} {direction} {group_index + 1}")
        group_notes = []
        for note_index, ((column, string, fret), (_, degree), (_, finger)) in enumerate(
            zip(found, degree_tokens, finger_tokens, strict=True)
        ):
            position = DEGREES.index(degree)
            expected_string, offset, expected_finger = POSITION_MAP[position]
            if (string, fret, finger) != (expected_string, root_fret + offset, expected_finger):
                raise CandidateError(f"GROUP_CONTACT_OR_FINGER_MISMATCH {module} {direction} {group_index + 1} {degree}")
            tone = tones[position]
            midi = OPEN_MIDI[string] + fret
            if midi != OPEN_MIDI["E"] + root_fret + OFFSETS[position] or midi % 12 != _pitch_class(tone):
                raise CandidateError(f"GROUP_TONE_PITCH_MISMATCH {module} {direction} {group_index + 1} {degree}")
            group_notes.append({"ordinal": group_index * size + note_index + 1,
                                "group_ordinal": group_index + 1,
                                "scale_position": position + 1, "degree": degree, "tone": tone,
                                "string": string, "fret": fret, "finger_digit": finger,
                                "ascii_column_in_group": column,
                                "onset_q": None, "duration_q": None})
        notes.extend(group_notes)
        module_group_index = group_index + (count if direction == "descending" else 0)
        groups.append({"ordinal": group_index + 1, "degrees": list(degrees),
                       "string_path": paths[group_index],
                       "note_ordinals": [group_index * size + i + 1 for i in range(size)],
                       "D_start_group_start_stroke": "D" if module_group_index % 2 == 0 else "U"})
    if len(notes) != count * size:
        raise CandidateError(f"DIRECTION_NOTE_COUNT {module} {direction}")
    return {"direction": direction, "path_line": path_line, "raw_rows": rows,
            "groups": groups, "notes": notes}


def _route_tokens(line: str, prefix: str) -> list[tuple[str, int]]:
    if not line.startswith(prefix):
        raise CandidateError(f"TXT_ROUTE_PREFIX_INVALID {prefix}")
    parts = line.removeprefix(prefix).strip().split(" > ")
    if any(ROUTE_TOKEN.fullmatch(part) is None for part in parts):
        raise CandidateError(f"TXT_ROUTE_TOKEN_INVALID {prefix}")
    return [(match.group(1), int(match.group(2))) for part in parts if (match := ROUTE_TOKEN.fullmatch(part))]


def _txt_cards(txt: str) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    lines = txt.splitlines()
    if len(lines) != 741 or lines[:2] != [
        "SCALE EXERCISES - SECTION IV, LEVEL 32",
        "MAJOR PENTATONIC THREE-NOTE ROLL AND FIVE-NOTE CYCLE - TWO-OCTAVE SIX-STRING NECK LADDER: A TO A",
    ]:
        raise CandidateError("TXT_HEADER_OR_LENGTH_MISMATCH")
    if lines[12] != "The complete two-octave position line is: 1 2 3 5 6 8 9 10 12 13 15.":
        raise CandidateError("TXT_PENTATONIC_DEGREE_MAP_MISMATCH")
    for line_index, module, direction in ((28, "A", "ascending"), (29, "A", "descending"),
                                          (36, "B", "ascending"), (37, "B", "descending")):
        label = "String paths " + ("up:   " if direction == "ascending" else "down: ")
        if lines[line_index] != label + " | ".join(PATHS[module][direction]):
            raise CandidateError(f"TXT_OVERVIEW_PATH_MISMATCH {module} {direction}")
    expected_up = list(zip(KEYS, range(5, 18), strict=True))
    if _route_tokens(lines[53], "UP:") != expected_up or _route_tokens(lines[54], "DOWN:") != list(reversed(expected_up)):
        raise CandidateError("TXT_CHROMATIC_ROUTE_MISMATCH")
    if lines[57:60] != [
        "Module A: 54 notes / 18 beats per key; 25-cell round trip = 1,350 notes.",
        "Module B: 70 notes / 14 beats per key; 25-cell round trip = 1,750 notes.",
        "Linked A+B: 124 notes / 32 beats per key; 25-cell round trip = 3,100 notes / 800 beats.",
    ]:
        raise CandidateError("TXT_ROUTE_COUNTS_MISMATCH")
    starts = [(index, match) for index, line in enumerate(lines) if (match := RUNG_TXT.fullmatch(line))]
    if tuple(index + 1 for index, _ in starts) != tuple(63 + 50 * n for n in range(13)):
        raise CandidateError("TXT_RUNG_BOUNDARY_MISMATCH")
    cards = []
    for index, (start, match) in enumerate(starts):
        number, key, octave = int(match.group(1)), _key(match.group(2)), bool(match.group(3))
        root_fret, frame_low, frame_high = map(int, match.group(4, 5, 6))
        if (number, key, octave, root_fret, frame_low, frame_high) != (
            index + 1, KEYS[index], index == 12, index + 5, index + 4, index + 7
        ):
            raise CandidateError(f"TXT_RUNG_IDENTITY_MISMATCH {number}")
        body = lines[start + 1:start + 48]
        if (len(body) != 47 or not body[0].startswith("Two-octave tones: ")
            or [body[position] for position in (1, 12, 23, 34, 45)] != [""] * 5
            or body[46] != "Complete the assigned module or linked A+B rung, return to the low root, release pressure, and move one fret."):
            raise CandidateError(f"TXT_RUNG_LAYOUT_MISMATCH {number}")
        if lines[start + 48] != "" or not lines[start + 49].startswith("==="):
            raise CandidateError(f"TXT_RUNG_SEPARATOR_MISMATCH {number}")
        tones = body[0].removeprefix("Two-octave tones: ").split()
        if len(tones) != 11 or tones[0] != key or tones[0] != tones[5] or tones[5] != tones[10]:
            raise CandidateError(f"TXT_SCALE_TONES_INVALID {number}")
        tonic_pc = _pitch_class(key)
        if any(_pitch_class(tone) != (tonic_pc + offset) % 12 for tone, offset in zip(tones, OFFSETS, strict=True)):
            raise CandidateError(f"TXT_PENTATONIC_TONES_INVALID {number}")
        modules = {}
        for module, direction, header_index, path_index, row_start in (
            ("A", "ascending", 2, 3, 4), ("A", "descending", 13, 14, 15),
            ("B", "ascending", 24, 25, 26), ("B", "descending", 35, 36, 37)
        ):
            spec = MODULES[module]
            expected_header = (f"{spec['header']} - {direction.upper()} - {spec['groups_each_direction']} "
                               f"{spec['group_name']} / {spec['groups_each_direction'] * spec['size']} NOTES")
            if body[header_index] != expected_header:
                raise CandidateError(f"TXT_MODULE_HEADER_MISMATCH {number} {module} {direction}")
            parsed = _parse_direction(body[row_start:row_start + 8], body[path_index], tones,
                                      root_fret, module, direction)
            modules.setdefault(module, {"module": module, "group_size": spec["size"],
                                        "group_name": spec["group_name"].lower(),
                                        "note_count": spec["note_count"], "directions": []})["directions"].append(parsed)
        for module in ("A", "B"):
            up, down = modules[module]["directions"]
            if (up["notes"][0]["degree"], up["notes"][0]["string"], up["notes"][0]["fret"],
                up["notes"][-1]["degree"], up["notes"][-1]["string"], up["notes"][-1]["fret"],
                down["notes"][0]["degree"], down["notes"][0]["string"], down["notes"][0]["fret"],
                down["notes"][-1]["degree"], down["notes"][-1]["string"], down["notes"][-1]["fret"]) != (
                1, "E", root_fret, 15, "e", root_fret,
                15, "e", root_fret, 1, "E", root_fret
            ):
                raise CandidateError(f"MODULE_ROOT_TURN_OR_RETURN_INVALID {number} {module}")
        low_a = modules["A"]["directions"][1]["notes"][-1]
        low_b = modules["B"]["directions"][0]["notes"][0]
        if (low_a["degree"], low_a["string"], low_a["fret"]) != (
            low_b["degree"], low_b["string"], low_b["fret"]
        ):
            raise CandidateError(f"LINKED_LOW_ROOT_BOUNDARY_INVALID {number}")
        cards.append({"rung_number": f"{number:02d}", "key": key, "octave_rung": octave,
                      "root_fret": root_fret, "frame_low": frame_low, "frame_high": frame_high,
                      "scale_tones": tones, "modules": [modules["A"], modules["B"]],
                      "heading_line": start + 1, "last_line": start + 48})
    if (lines[728] != "FULL ROUND-TRIP CHALLENGE"
        or lines[730] != "2. Play linked Module A + Module B through rungs 01-13 without restarting the pick cycle."
        or lines[731] != "3. Reverse after the fret-17 card and return through rungs 12-01."):
        raise CandidateError("TXT_ROUND_TRIP_MISMATCH")
    guidance = {"overview_text": "\n".join(lines[:61]), "overview_ref": "L32-TXT1-1-61",
                "practice_and_challenge_text": "\n".join(lines[712:]),
                "practice_and_challenge_ref": "L32-TXT1-713-741",
                "pdf_overview_ref": "L32-PDF1-p1", "pdf_route_ref": "L32-PDF1-p2",
                "pdf_practice_ref": "L32-PDF1-p16"}
    return cards, guidance, {"up_text": lines[53], "down_text": lines[54]}


def _pdf_cards(pdf_data: bytes) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    try:
        reader = PdfReader(BytesIO(pdf_data), strict=True)
        if len(reader.pages) != 16:
            raise CandidateError(f"PDF_PAGE_COUNT {len(reader.pages)}")
        pages = [(page.extract_text() or "").splitlines() for page in reader.pages]
    except CandidateError:
        raise
    except Exception as exc:
        raise CandidateError(f"PDF_READ_FAILED {type(exc).__name__}") from exc
    if (pages[0][:3] != ["Scale Exercises - Section IV, Level 32", "Five notes. Two sequence engines.",
                         "Major Pentatonic Sequence Studies: Three-Note Roll and Five-Note Cycle"]
        or "COUNT  25 x 124 = 3,100 notes; 800 beats." not in pages[15]):
        raise CandidateError("PDF_OVERVIEW_OR_PRACTICE_MISMATCH")
    route_page = pages[1]
    if route_page[:3] != ["Level 32 - Chromatic Major-Pentatonic Route and Sequence Map",
                          "Ascending: complete the selected module or linked 124-note rung, then move the frame +1 fret",
                          "Descending: use the same cards in reverse order and move -1 fret"]:
        raise CandidateError("PDF_ROUTE_HEADER_MISMATCH")
    if route_page[3:8] != ["Rung", "Key", "Low-E root", "Frame", "Scale tones (1, 2, 3, 5, 6)"]:
        raise CandidateError("PDF_ROUTE_TABLE_HEADER_MISMATCH")
    table = []
    for index in range(13):
        number, key_label, root, frame, tones = route_page[8 + index * 5:13 + index * 5]
        expected_label = KEYS[index] + " major pentatonic" + (" - octave" if index == 12 else "")
        if (number, key_label, root, frame) != (
            f"{index + 1:02d}", expected_label, f"fret {index + 5}", f"{index + 4}-{index + 7}"
        ):
            raise CandidateError(f"PDF_ROUTE_TABLE_IDENTITY_MISMATCH {index + 1}")
        table.append({"number": number, "key_label": key_label, "root_fret": index + 5,
                      "frame": frame, "tones_1_to_5": tones.split()})
    if route_page[92:95] != ["ROUND-TRIP COUNTS",
                              "Module A: 1,350 notes. Module B: 1,750 notes. Linked route: 3,100 notes / 800 beats.",
                              "Standard tuning. Level 31 two-octave major-pentatonic frame. Two independent sequence modules."]:
        raise CandidateError("PDF_ROUTE_COUNTS_MISMATCH")
    cards = []
    for index in range(13):
        page_number = index + 3
        lines = pages[page_number - 1]
        match = RUNG_PDF.fullmatch(lines[1]) if len(lines) == 46 else None
        expected_footer = ("Finish the fret-17 linked rung, then reverse direction and continue through rungs 12-01."
                           if index == 12 else
                           "A=54 notes; B=70 notes; linked rung=124 notes. Continuous alternate picking - D-start and U-start.")
        if (lines[0] != "Level 32 - Major Pentatonic Sequence Studies" or match is None
            or lines[3] != "Complete a module, return to the low root, then link or shift as assigned."
            or lines[44] != expected_footer or lines[45] != f"Page {page_number} of 16"):
            raise CandidateError(f"PDF_CARD_PAGE_LAYOUT_MISMATCH {page_number}")
        blocks = []
        for module, direction, start in (("A", "ascending", 4), ("A", "descending", 14),
                                         ("B", "ascending", 24), ("B", "descending", 34)):
            spec = MODULES[module]
            expected_header = (f"{spec['header']} - {direction.upper()} | {spec['groups_each_direction']} "
                               f"{spec['group_name']} / {spec['groups_each_direction'] * spec['size']} NOTES")
            if lines[start] != expected_header:
                raise CandidateError(f"PDF_MODULE_HEADER_MISMATCH {page_number} {module} {direction}")
            blocks.append({"module": module, "direction": direction,
                           "path_line": lines[start + 1], "raw_rows": lines[start + 2:start + 10]})
        cards.append({"number": match.group(1), "key": _key(match.group(2)),
                      "octave_rung": bool(match.group(3)), "root_fret": int(match.group(4)),
                      "frame_low": int(match.group(5)), "frame_high": int(match.group(6)),
                      "scale_tones": lines[2].removeprefix("Two-octave tones: ").split(),
                      "blocks": blocks, "pdf_page": page_number})
    return cards, table


def build_candidate(*, txt_data: bytes | None = None, pdf_data: bytes | None = None) -> dict[str, Any]:
    root = _root()
    txt_data = _source_bytes(root, TXT_REL) if txt_data is None else txt_data
    pdf_data = _source_bytes(root, PDF_REL) if pdf_data is None else pdf_data
    _verify(txt_data, TXT_BYTES, TXT_SHA256, "L32-TXT")
    _verify(pdf_data, PDF_BYTES, PDF_SHA256, "L32-PDF")
    try:
        txt_cards, guidance, raw_route = _txt_cards(txt_data.decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise CandidateError("TXT_ENCODING_INVALID") from exc
    pdf_cards, pdf_table = _pdf_cards(pdf_data)
    records = []
    for index, (txt_card, pdf_card, pdf_row) in enumerate(zip(txt_cards, pdf_cards, pdf_table, strict=True)):
        number = txt_card["rung_number"]
        if (pdf_card["number"], pdf_card["key"], pdf_card["octave_rung"], pdf_card["root_fret"],
            pdf_card["frame_low"], pdf_card["frame_high"], pdf_card["scale_tones"]) != (
            number, txt_card["key"], txt_card["octave_rung"], txt_card["root_fret"],
            txt_card["frame_low"], txt_card["frame_high"], txt_card["scale_tones"]
        ) or pdf_row["tones_1_to_5"] != txt_card["scale_tones"][:5]:
            raise CandidateError(f"PDF_TXT_CARD_IDENTITY_MISMATCH {number}")
        txt_blocks = [(module["module"], direction["direction"], direction["path_line"], direction["raw_rows"])
                      for module in txt_card["modules"] for direction in module["directions"]]
        pdf_blocks = [(block["module"], block["direction"], block["path_line"], block["raw_rows"])
                      for block in pdf_card["blocks"]]
        if txt_blocks != pdf_blocks:
            raise CandidateError(f"PDF_TXT_CARD_BLOCK_MISMATCH {number}")
        if index:
            baseline = txt_cards[0]
            for module, first_module in zip(txt_card["modules"], baseline["modules"], strict=True):
                for direction, first_direction in zip(module["directions"], first_module["directions"], strict=True):
                    for note, first_note in zip(direction["notes"], first_direction["notes"], strict=True):
                        if (note["string"], note["fret"], note["degree"], note["finger_digit"],
                            note["group_ordinal"]) != (
                            first_note["string"], first_note["fret"] + index, first_note["degree"],
                            first_note["finger_digit"], first_note["group_ordinal"]
                        ):
                            raise CandidateError(f"RUNG_TRANSPOSED_CONTACT_MISMATCH {number}")
        records.append({
            "source_local_key": f"L32-rung{number}", "rung_number": number,
            "key": txt_card["key"], "octave_rung": txt_card["octave_rung"],
            "root_string": "E", "root_fret": txt_card["root_fret"],
            "frame_low": txt_card["frame_low"], "frame_high": txt_card["frame_high"],
            "scale_tones": txt_card["scale_tones"], "degree_map": list(DEGREES),
            "modules": txt_card["modules"],
            "linked_order": ["A ascending", "A descending", "B ascending", "B descending"],
            "linked_note_count": 124,
            "linked_boundary": {"after": "A descending note 54", "before": "B ascending note 1",
                                "degree": 1, "string": "E", "fret": txt_card["root_fret"],
                                "separate_rearticulated_contacts": True,
                                "pick_cycle_continues": True},
            "source_refs": {"txt": f"L32-TXT1-{txt_card['heading_line']}-{txt_card['last_line']}",
                            "pdf_card": f"L32-PDF1-p{pdf_card['pdf_page']}",
                            "pdf_route": "L32-PDF1-p2"},
            "canonical_item_id": None, "canonical_variant_id": None,
            "onset_q": None, "duration_q": None, "fixed_bpm": None, "note_per_click": None,
            "runtime_eligible": False, "runtime_admitted": False, "imported": False, "admitted": False,
        })
    up = [record["source_local_key"] for record in records]
    down_standalone = list(reversed(up))
    return_down = down_standalone[1:]
    traversal = up + return_down
    return {
        "schema": "fathom-level032-whole-detached-candidate-v1", "wbs_id": "2.3.1.1.1", "level": 32,
        "source": {"txt_path": TXT_REL.as_posix(), "txt_bytes": TXT_BYTES, "txt_sha256": TXT_SHA256,
                   "pdf_path": PDF_REL.as_posix(), "pdf_bytes": PDF_BYTES, "pdf_sha256": PDF_SHA256,
                   "pdf_pages": 16, "selected_pdf_card_pages": list(range(3, 16))},
        "instructions": guidance,
        "shape": {"position_map": [{"scale_position": i + 1, "degree": DEGREES[i], "string": string,
                                     "fret_offset_from_root": offset, "finger_digit": finger}
                                    for i, (string, offset, finger) in enumerate(POSITION_MAP)],
                  "source_refs": ["L32-TXT1-10-22", "L32-PDF1-p1"]},
        "routes": {"up": {"rungs": up, "root_frets": list(range(5, 18)),
                          "shift_frets_between_cells": 1, "source_text": raw_route["up_text"],
                          "source_refs": ["L32-TXT1-54", "L32-PDF1-p2"]},
                   "down_standalone": {"rungs": down_standalone, "root_frets": list(range(17, 4, -1)),
                                       "shift_frets_between_cells": -1,
                                       "source_text": raw_route["down_text"],
                                       "source_refs": ["L32-TXT1-55", "L32-PDF1-p2"]},
                   "down_return": {"rungs": return_down, "root_frets": list(range(16, 4, -1)),
                                   "shift_frets_between_cells": -1,
                                   "source_refs": ["L32-TXT1-729-734", "L32-PDF1-p15-16"]},
                   "continuous_round_trip": {"rungs": traversal, "turn_after_rung": "L32-rung13",
                                             "cell_count": 25, "source_refs": ["L32-TXT1-729-734", "L32-PDF1-p16"],
                                             "module_A_notes": 1350, "module_B_notes": 1750,
                                             "linked_notes": 3100,
                                             "authored_grouped_beats_instruction_only": 800}},
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
