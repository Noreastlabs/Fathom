#!/usr/bin/env python3
"""Pinned, detached Level 22 natural-minor two-octave neck ladder."""

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
TXT = Path("Notes/music/guitar project/TXT version/Scale_Exercises_Section_III_Level_22_Natural_Minor_Two_Octave_Six_String_Neck_Ladder.txt")
PDF = Path("Notes/music/guitar project/PDF version/Scale_Exercises_Section_III_Level_22_Natural_Minor_Two_Octave_Six_String_Neck_Ladder.pdf")
TXT_PIN = (20967, "0031bdd05834d1f1f381240a48a5fa193da561f7bdf51df580771f593c82b1dc")
PDF_PIN = (21185, "f07518814be26b8290c6b9a688251eb77fd2b2aedb8efc03a0469167d8be7bde")
OUTPUT_ROOT = Path("Build/parallel-12/2.3.1.1.1-level022-whole-ladder-r01")
KEYS = ("A", "Bb", "B", "C", "C#", "D", "Eb", "E", "F", "F#", "G", "G#", "A")
STRINGS_HIGH_TO_LOW = ("e", "B", "G", "D", "A", "E")
ASCENDING_DISTRIBUTION = (("E", (0, 2, 3), (1, 3, 4)),
                          ("A", (0, 2, 3), (1, 3, 4)),
                          ("D", (0, 2), (1, 3)),
                          ("G", (-1, 0, 2), (1, 2, 4)),
                          ("B", (0, 1, 3), (1, 2, 4)),
                          ("e", (0,), (1,)))
DEGREES_ASC = ("1", "2", "b3", "4", "5", "b6", "b7", "1", "2", "b3", "4", "5", "b6", "b7", "1")
NATURAL_MINOR_STEPS = (0, 2, 3, 5, 7, 8, 10)
TUNING_PC = {"E": 4, "A": 9, "D": 2, "G": 7, "B": 11, "e": 4}
NATURAL_PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
LETTER_ORDER = "CDEFGAB"
TAB = re.compile(r"^([eBGDAE])  \|([0-9-]+)\|$")
TONE = re.compile(r"^[A-G](?:b|#)?$")


class CandidateError(ValueError):
    """A pinned source, musical mapping or output boundary failed."""


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
    require(not absolute.is_symlink() and absolute.is_file() and
            absolute.resolve().is_relative_to(root.resolve()), f"SOURCE_PATH_INVALID {path}")
    return absolute.read_bytes()


def pitch_class(spelling: str) -> int:
    require(TONE.fullmatch(spelling) is not None, f"PITCH_SPELLING {spelling}")
    return (NATURAL_PC[spelling[0]] + (1 if spelling.endswith("#") else
                                       -1 if spelling.endswith("b") else 0)) % 12


def parse_tones(line: str, key: str, rung: int) -> list[str]:
    prefix = "Scale tones across two octaves: "
    require(line.startswith(prefix), f"TXT_TONES_LABEL {rung}")
    parts = line[len(prefix):].split(" | ")
    require(len(parts) == 2, f"TXT_TONES_SHAPE {rung}")
    first, second = parts[0].split(), parts[1].split()
    require(len(first) == 7 and second == first + [key] and first[0] == key,
            f"TXT_TONES_SEQUENCE {rung}")
    root_pc = pitch_class(key)
    root_letter = LETTER_ORDER.index(key[0])
    for degree, name in enumerate(first):
        require(pitch_class(name) == (root_pc + NATURAL_MINOR_STEPS[degree]) % 12 and
                name[0] == LETTER_ORDER[(root_letter + degree) % 7],
                f"NATURAL_MINOR_TONE {rung} {degree + 1}")
    return first + second


def parse_tab_rows(rows: list[str], root: int, rung: int) -> dict[str, list[int]]:
    require(len(rows) == 6, f"TXT_TAB_ROW_COUNT {rung}")
    parsed = {}
    expected = {string: [root + offset for offset in offsets]
                for string, offsets, _ in ASCENDING_DISTRIBUTION}
    for string, row in zip(STRINGS_HIGH_TO_LOW, rows, strict=True):
        match = TAB.fullmatch(row)
        require(match is not None and match.group(1) == string,
                f"TXT_TAB_ROW_SHAPE {rung} {string}")
        frets = [int(value) for value in re.findall(r"\d+", match.group(2))]
        expect = expected[string] + list(reversed(expected[string]))
        require(frets == expect, f"TXT_TAB_FRETS {rung} {string}")
        parsed[string] = frets
    return parsed


def parse_pdf_pages(pdf_data: bytes) -> dict[int, list[str]]:
    try:
        reader = PdfReader(BytesIO(pdf_data), strict=True)
        require(len(reader.pages) == 7, "PDF_PAGE_COUNT")
        pages = {page: (reader.pages[page - 1].extract_text() or "").splitlines()
                 for page in range(1, 8)}
    except CandidateError:
        raise
    except Exception as exc:
        raise CandidateError("PDF_READ_FAILED") from exc
    require(pages[1][0:2] == ["Scale Exercises - Section III, Level 22",
                               "Natural Minor Two-Octave Six-String Neck Ladder: A to A"] and
            pages[1][-1] == "Page 1 of 7" and
            pages[2][0:5] == ["Level 22 - Chromatic Natural-Minor Route",
                               "Ascending route: complete each 30-note scale cell, then move the frame +1 fret",
                               "Descending route: use the same cards in reverse order and move -1 fret",
                               "Standard tuning. Two-octave 6th-string-root natural minor. One completed cell = 30 notes.",
                               "Page 2 of 7"] and
            pages[2][-1] == "25 cells x 30 notes = 750 picked notes.", "PDF_OVERVIEW")
    for page in range(3, 8):
        lines = pages[page]
        require(lines[0] == "Level 22 - Natural Minor Two-Octave Six-String Neck Ladder" and
                lines[3] == "Standard tuning. Two-octave 6th-string-root natural minor. One completed cell = 30 notes." and
                lines[4] == f"Page {page} of 7" and
                (len(lines) == 47 if page <= 6 else len(lines) == 49),
                f"PDF_CARD_PAGE {page}")
    return pages


def source_rungs(txt_data: bytes, pdf_data: bytes) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    try:
        lines = txt_data.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise CandidateError("TXT_ENCODING_INVALID") from exc
    require(len(lines) == 264 and lines[0:2] ==
            ["SCALE EXERCISES - SECTION III, LEVEL 22",
             "NATURAL MINOR TWO-OCTAVE SIX-STRING NECK LADDER: A TO A"], "TXT_TITLE_OR_LENGTH")
    for line_number, phrase in ((11, "Moving one fixed scale shape by one fret transposes it."),
                                (26, "Do not hold a static five-fret stretch."),
                                (32, "The G string begins one fret below the root reference"),
                                (36, "repeat the high root at the turn"),
                                (38, "D-start: strict D-U alternate picking"),
                                (39, "U-start: strict U-D alternate picking"),
                                (47, "Begin 10-15 BPM below your clean Level 21 tempo"),
                                (43, "UP:   A(5)"), (44, "DOWN: A(17)"),
                                (243, "25 cells x 30 notes = 750 picked notes.")):
        require(phrase in lines[line_number - 1], f"TXT_INSTRUCTION {line_number}")
    pages = parse_pdf_pages(pdf_data)
    rungs = []
    for index, key in enumerate(KEYS):
        rung = index + 1
        root = 5 + index
        start = 55 + 14 * index
        block = lines[start - 1:start + 11]
        heading = (f"RUNG {rung:02d} OF 13 - {key.upper()} NATURAL MINOR - " +
                   ("OCTAVE - " if rung == 13 else "") +
                   f"ROOT ON LOW E FRET {root} - FRAME {root - 1}-{root + 3}")
        require(len(block) == 12 and block[0] == heading and
                block[2] == "30-note cell: low root to high root, repeat the high root, then return to the low root." and
                block[11] == "Finish on the low root, release pressure, and move the entire frame one fret in the route direction.",
                f"TXT_RUNG_SHAPE {rung}")
        tones = parse_tones(block[1], key, rung)
        summary = pages[2][10 + 5 * index:15 + 5 * index]
        expected_summary = [f"{rung:02d}", f"{key} natural minor" + (" - octave" if rung == 13 else ""),
                            f"fret {root}", f"{root - 1}-{root + 3}", "  ".join(tones[:7])]
        require(summary == expected_summary, f"PDF_RUNG_SUMMARY {rung}")
        page = 3 + index // 3
        page_line = 6 + 14 * (index % 3)
        pdf_block = pages[page][page_line - 1:page_line + 13]
        pdf_heading = f"{rung:02d}  {key.upper()} MINOR" + (" (OCTAVE)" if rung == 13 else "")
        require(len(pdf_block) == 14 and pdf_block[0] == pdf_heading and
                pdf_block[1] == f"ROOT E{root}  |  FRAME {root - 1}-{root + 3}" and
                pdf_block[2] == f"Notes: {' '.join(tones[:7])} | {' '.join(tones[7:])}" and
                pdf_block[3] == "30-NOTE TWO-OCTAVE CELL" and
                pdf_block[4:12] == block[3:11] and
                pdf_block[12] == "Return to the low root; release pressure; move the entire frame one fret." and
                pdf_block[13] == "D-start and U-start",
                f"TXT_PDF_RUNG_MISMATCH {rung}")
        degrees = re.findall(r"b[367]|[1-7]", block[3][4:])
        fingers = [int(digit) for digit in re.findall(r"[1-4]", block[4][4:])]
        expected_degrees = list(DEGREES_ASC) + list(reversed(DEGREES_ASC))
        expected_fingers = ([finger for _, _, group in ASCENDING_DISTRIBUTION for finger in group] +
                            [finger for _, _, group in reversed(ASCENDING_DISTRIBUTION)
                             for finger in reversed(group)])
        require(block[3].startswith("Deg|") and block[4].startswith("Fng|") and
                len(degrees) == len(fingers) == 30 and degrees == expected_degrees and
                fingers == expected_fingers, f"DEG_FNG_SEQUENCE {rung}")
        tabs = block[5:11]
        tab_frets = parse_tab_rows(tabs, root, rung)
        ascending = [(string, root + offset, finger)
                     for string, offsets, finger_group in ASCENDING_DISTRIBUTION
                     for offset, finger in zip(offsets, finger_group, strict=True)]
        sequence = ascending + list(reversed(ascending))
        require(len(sequence) == 30 and sequence[14] == sequence[15] == ("e", root, 1),
                f"TURN_ROOT {rung}")
        tone_sequence = tones + list(reversed(tones))
        require(len(tone_sequence) == 30, f"TONE_COUNT {rung}")
        notes = []
        for note_index, ((string, fret, finger), degree, printed_finger, spelling) in enumerate(
            zip(sequence, degrees, fingers, tone_sequence, strict=True), 1
        ):
            require(finger == printed_finger and
                    pitch_class(spelling) == (TUNING_PC[string] + fret) % 12,
                    f"NOTE_MUSICAL_MISMATCH {rung} {note_index}")
            notes.append({"ordinal": note_index, "direction": "ascending" if note_index <= 15 else "descending",
                          "string": string, "fret": fret, "finger_digit": finger,
                          "degree": degree, "pitch_spelling": spelling,
                          "turn_repeat": note_index == 16,
                          "onset_q": None, "duration_q": None})
        for string, row_frets in tab_frets.items():
            require(row_frets == [note["fret"] for note in notes if note["string"] == string],
                    f"TAB_NOTE_PARITY {rung} {string}")
        require(notes[0]["string"] == notes[-1]["string"] == "E" and
                notes[0]["fret"] == notes[-1]["fret"] == root, f"LOW_ROOT_RETURN {rung}")
        rungs.append({"source_local_key": f"L22-rung{rung:02d}", "rung": rung,
                      "key": key, "root_string": "E", "root_fret": root,
                      "frame_min_fret": root - 1, "frame_max_fret": root + 3,
                      "scale_tones_two_octaves": tones, "source_degree_line": block[3],
                      "source_finger_line": block[4], "source_tab_rows_high_to_low": tabs,
                      "source_refs": {"txt": f"L22-TXT1-{start}-{start + 11}",
                                      "pdf": f"L22-PDF1-p{page}-L{page_line}-{page_line + 13}",
                                      "pdf_overview": "L22-PDF1-p2"},
                      "cell_notes": notes, "canonical_item_id": None,
                      "canonical_variant_id": None, "onset_q": None, "duration_q": None,
                      "fixed_bpm": None, "note_per_click": None,
                      "runtime_eligible": False, "runtime_admitted": False,
                      "imported": False, "admitted": False})
    require(len(rungs) == 13 and [rung["root_fret"] for rung in rungs] == list(range(5, 18)),
            "RUNG_COVERAGE")
    guidance = {"interpretation_source": lines[10:13], "shape_source": lines[18:27],
                "distribution_source": lines[28:33], "picking_source": lines[34:40],
                "route_source": lines[41:44], "practice_tempo_source": lines[45:52],
                "practice_is_timing_authority": False,
                "static_five_fret_stretch_inferred": False}
    return rungs, guidance


def build_candidate(*, txt_data: bytes | None = None, pdf_data: bytes | None = None,
                    root: Path = ROOT) -> dict[str, Any]:
    txt_data = local_bytes(root, TXT) if txt_data is None else txt_data
    pdf_data = local_bytes(root, PDF) if pdf_data is None else pdf_data
    verify(txt_data, TXT_PIN, "LEVEL22_TXT")
    verify(pdf_data, PDF_PIN, "LEVEL22_PDF")
    rungs, guidance = source_rungs(txt_data, pdf_data)
    route = []
    for ordinal, rung_index in enumerate(list(range(1, 14)) + list(range(12, 0, -1)), 1):
        rung = rungs[rung_index - 1]
        route.append({"cell_ordinal": ordinal, "rung": rung_index, "key": rung["key"],
                      "root_fret": rung["root_fret"], "cell_note_count": 30,
                      "travel_direction": "up" if ordinal <= 13 else "down"})
    require(len(route) == 25 and route[0]["key"] == route[-1]["key"] == "A" and
            route[0]["root_fret"] == route[-1]["root_fret"] == 5 and
            route[12]["root_fret"] == 17 and
            all(abs(b["root_fret"] - a["root_fret"]) == 1 for a, b in zip(route, route[1:])),
            "ROUTE_COVERAGE")
    return {"schema": "fathom-level022-whole-detached-candidate-v1", "wbs_id": "2.3.1.1.1",
            "classification": "noncanonical_nonadmitted_source_candidate", "level": 22,
            "source": {"txt_path": TXT.as_posix(), "txt_bytes": TXT_PIN[0], "txt_sha256": TXT_PIN[1],
                       "pdf_path": PDF.as_posix(), "pdf_bytes": PDF_PIN[0], "pdf_sha256": PDF_PIN[1],
                       "pdf_pages": 7, "card_pdf_pages": [3, 4, 5, 6, 7]},
            "counts": {"rungs": 13, "notes_per_cell": 30, "unique_cell_notes": 390,
                       "round_trip_cells": 25, "round_trip_picked_notes": 750},
            "rungs": rungs, "full_round_trip_route": route, "source_guidance": guidance,
            "exceptions": [], "pending": ["Curriculum/musical review", "canonical identity allocation",
                                          "runtime admission and timing decisions"],
            "canonical_item_id": None, "canonical_variant_id": None,
            "onset_q": None, "duration_q": None, "fixed_bpm": None, "note_per_click": None,
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
        print(f"PASS detached Level 22: 13 rungs, 390 unique cell notes, 25-cell/750-note round trip; bytes={len(data)} sha256={digest(data)}")
        return 0
    except (CandidateError, OSError) as exc:
        print(f"FAIL {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
