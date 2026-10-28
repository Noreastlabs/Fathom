#!/usr/bin/env python3
"""Pinned, detached Level 28 natural-minor diatonic-triad neck ladder."""

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
TXT = Path("Notes/music/guitar project/TXT version/Scale_Exercises_Section_III_Level_28_Natural_Minor_Diatonic_Triads_Two_Octave_Six_String_Neck_Ladder.txt")
PDF = Path("Notes/music/guitar project/PDF version/Scale_Exercises_Section_III_Level_28_Natural_Minor_Diatonic_Triads_Two_Octave_Six_String_Neck_Ladder.pdf")
TXT_PIN = (50876, "2f745bc5000d27f032fd1187fee245e387bfd1bf7b0f132782ebb7a72aafac1b")
PDF_PIN = (33021, "779c1b2da3cad5046af51013dc4a72053b7cd5dd0a211caa27352bfa93076219")
OUTPUT_ROOT = Path("Build/parallel-12/2.3.1.1.1-level028-whole-triad-ladder-r01")
KEYS = ("A", "Bb", "B", "C", "C#", "D", "Eb", "E", "F", "F#", "G", "G#", "A")
STRINGS_HIGH_TO_LOW = ("e", "B", "G", "D", "A", "E")
SCALE_SHAPE = (("E", (0, 2, 3), (1, 3, 4)), ("A", (0, 2, 3), (1, 3, 4)),
               ("D", (0, 2), (1, 3)), ("G", (-1, 0, 2), (1, 2, 4)),
               ("B", (0, 1, 3), (1, 2, 4)), ("e", (0,), (1,)))
DEGREES = ("1", "2", "b3", "4", "5", "b6", "b7", "8", "9", "b10", "11", "12", "b13", "b14", "15")
QUALITY = ("minor", "diminished", "major", "minor", "minor", "major", "major")
FUNCTION = ("i", "ii-dim", "III", "iv", "v", "VI", "VII")
UP_PATH = ("EEA", "EAA", "EAD", "AAD", "ADG", "ADG", "DGG", "DGB", "GGB", "GBB", "GBe")
DOWN_PATH = ("eBG", "BBG", "BGG", "BGD", "GGD", "GDA", "GDA", "DAA", "DAE", "AAE", "AEE")
NATURAL_MINOR_STEPS = (0, 2, 3, 5, 7, 8, 10)
TUNING_PC = {"E": 4, "A": 9, "D": 2, "G": 7, "B": 11, "e": 4}
NATURAL_PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
LETTER_ORDER = "CDEFGAB"
TONE = re.compile(r"^[A-G](?:b|#)?$")
TAB_CELL = re.compile(r"^[0-9-]{12}$")


class CandidateError(ValueError):
    """A source pin, card, contact or output boundary failed."""


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
    require(line.startswith(prefix), f"TXT_TONE_LABEL {rung}")
    tones = line[len(prefix):].split()
    require(len(tones) == 15 and tones[0] == tones[7] == tones[14] == key and
            tones[7:14] == tones[:7], f"TXT_TONE_SEQUENCE {rung}")
    root_pc = pitch_class(key)
    root_letter = LETTER_ORDER.index(key[0])
    for degree, spelling in enumerate(tones[:7]):
        require(pitch_class(spelling) == (root_pc + NATURAL_MINOR_STEPS[degree]) % 12 and
                spelling[0] == LETTER_ORDER[(root_letter + degree) % 7],
                f"NATURAL_MINOR_TONE {rung} {degree + 1}")
    return tones


def chord_names(tones: list[str]) -> list[str]:
    result = []
    for degree, quality in enumerate(QUALITY):
        first = pitch_class(tones[degree])
        third = (pitch_class(tones[degree + 2]) - first) % 12
        fifth = (pitch_class(tones[degree + 4]) - first) % 12
        require((third, fifth) == {"minor": (3, 7), "diminished": (3, 6), "major": (4, 7)}[quality],
                f"CHORD_QUALITY {degree + 1}")
        result.append(tones[degree] + ("m" if quality == "minor" else
                                       "dim" if quality == "diminished" else ""))
    return result


def split_cells(line: str, prefix: str, rung: int, direction: str) -> list[str]:
    parts = line.split("|")
    require(len(parts) == 13 and parts[0] == prefix and parts[-1] == "" and
            all(len(cell) == 12 for cell in parts[1:-1]),
            f"SOURCE_ROW_SHAPE {rung} {direction} {prefix}")
    return parts[1:-1]


def parse_contact_cells(rows: list[str], rung: int, direction: str) -> list[list[tuple[str, int]]]:
    require(len(rows) == 6, f"TAB_ROW_COUNT {rung} {direction}")
    parsed = {}
    for string, row in zip(STRINGS_HIGH_TO_LOW, rows, strict=True):
        cells = split_cells(row, string + "  ", rung, direction)
        require(all(TAB_CELL.fullmatch(cell) is not None for cell in cells),
                f"TAB_CELL_CHARACTERS {rung} {direction} {string}")
        parsed[string] = cells
    groups = []
    for cell_index in range(11):
        contacts = []
        for string in STRINGS_HIGH_TO_LOW:
            for match in re.finditer(r"\d+", parsed[string][cell_index]):
                contacts.append((match.start(), string, int(match.group())))
        contacts.sort(key=lambda value: value[0])
        require(len(contacts) == 3 and [value[0] for value in contacts] == [0, 4, 8],
                f"TAB_CONTACT_COLUMNS {rung} {direction} {cell_index + 1}")
        groups.append([(string, fret) for _, string, fret in contacts])
    return groups


def parse_pdf_pages(pdf_data: bytes) -> dict[int, list[str]]:
    try:
        reader = PdfReader(BytesIO(pdf_data), strict=True)
        require(len(reader.pages) == 10, "PDF_PAGE_COUNT")
        pages = {page: (reader.pages[page - 1].extract_text() or "").splitlines()
                 for page in range(1, 11)}
    except CandidateError:
        raise
    except Exception as exc:
        raise CandidateError("PDF_READ_FAILED") from exc
    require(pages[1][0:2] == ["Scale Exercises - Section III, Level 28",
                               "Natural Minor Diatonic Triads: Two-Octave Six-String Neck Ladder"] and
            pages[1][-1] == "Page 1 of 10" and
            pages[2][0:3] == ["Level 28 - Chromatic Natural-Minor Route and Diatonic-Triad Map",
                               "Ascending route: complete one 66-note triad cell, then move the frame +1 fret",
                               "Descending route: use the same cards in reverse order and move -1 fret"] and
            pages[2][-2:] == ["Standard tuning. Two-octave 6th-string-root natural minor. One completed cell = 66 notes.",
                                "Page 2 of 10"], "PDF_OVERVIEW")
    for page in range(3, 10):
        lines = pages[page]
        require(lines[0] == ("Level 28 - Natural Minor Diatonic Triads: Two Octaves"
                             if page <= 8 else "Level 28 - Final Rung and Full Round-Trip Challenge") and
                lines[-1] == f"Page {page} of 10" and
                len(lines) == (57 if page <= 8 else 51), f"PDF_CARD_PAGE {page}")
    require(pages[9][35] == "25 cells x 66 notes = 1,650 picked notes." and
            pages[10][-3] == "NEXT: Level 29 - Natural Minor Synthesis Circuit." and
            pages[10][-1] == "Page 10 of 10", "PDF_ROUTE_OR_NEXT_LEVEL")
    return pages


def source_rungs(txt_data: bytes, pdf_data: bytes) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    try:
        lines = txt_data.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise CandidateError("TXT_ENCODING_INVALID") from exc
    require(len(lines) == 487 and lines[:2] ==
            ["SCALE EXERCISES - SECTION III, LEVEL 28",
             "NATURAL MINOR DIATONIC TRIADS - TWO-OCTAVE SIX-STRING NECK LADDER"],
            "TXT_TITLE_OR_LENGTH")
    for line_number, phrase in ((19, "Two octaves: 1 2 b3"),
                                (31, "minor v and a major VII"),
                                (38, "G string:     R-1, R, R+2"),
                                (39, "B string:     R, R+1, R+3"),
                                (42, "do not hold a static five-fret stretch"),
                                (52, "repeat the high root at the turnaround"),
                                (54, "22 triads / 66 notes total per key"),
                                (78, "Up:   A -> Bb"),
                                (79, "Down: G# -> G")):
        require(phrase in lines[line_number - 1], f"TXT_INSTRUCTION {line_number}")
    require(lines[45 - 1] == "Ascending:  " + " | ".join(UP_PATH) and
            lines[46 - 1] == "Descending: " + " | ".join(DOWN_PATH), "TXT_STRING_PATH_MAP")
    expected_up = [[DEGREES[j], DEGREES[j + 2], DEGREES[j + 4]] for j in range(11)]
    expected_down = [list(reversed(group)) for group in reversed(expected_up)]
    require(lines[23 - 1] == "Ascending:  " + " | ".join("-".join(group) for group in expected_up) and
            lines[24 - 1] == "Descending: " + " | ".join("-".join(group) for group in expected_down),
            "TXT_DEGREE_SEQUENCE")
    pages = parse_pdf_pages(pdf_data)
    require(pages[2][92] == "UP:   " + " | ".join("-".join(group) for group in expected_up) and
            pages[2][93] == "DOWN: " + " | ".join("-".join(group) for group in expected_down) and
            pages[2][97] == " | ".join(UP_PATH), "PDF_SEQUENCE_MAP")
    rungs = []
    for index, key in enumerate(KEYS):
        rung = index + 1
        root = 5 + index
        start = 104 + 27 * index
        block = lines[start - 1:start + 24]
        heading = (f"RUNG {rung:02d} OF 13 - {key.upper()} NATURAL MINOR - " +
                   ("OCTAVE - " if rung == 13 else "") +
                   f"ROOT ON LOW E FRET {root} - FRAME {root - 1}-{root + 3}")
        require(len(block) == 25 and block[0] == heading and
                block[3] == "66-note cell: 11 ascending triads, repeat the high root at the turn, then 11 descending triads." and
                block[4] == "ASCENDING - 11 TRIADS / 33 NOTES" and
                block[14] == "DESCENDING - 11 TRIADS / 33 NOTES" and
                block[24] == "Finish on the low root, release pressure, and move the entire frame one fret in the route direction.",
                f"TXT_RUNG_SHAPE {rung}")
        tones = parse_tones(block[1], key, rung)
        triad_names = block[2].removeprefix("Diatonic triads: ").split(" | ")
        require(block[2].startswith("Diatonic triads: ") and
                triad_names == chord_names(tones), f"TXT_TRIAD_NAMES {rung}")
        summary = pages[2][8 + 5 * index:13 + 5 * index]
        expected_summary = [f"{rung:02d}", f"{key} natural minor" + (" - octave" if rung == 13 else ""),
                            f"fret {root}", f"{root - 1}-{root + 3}", " ".join(triad_names)]
        require(summary == expected_summary, f"PDF_RUNG_SUMMARY {rung}")
        table = lines[84 + index]
        expected_table = (f"{rung:02d}    {key} natural minor" + (" - octave" if rung == 13 else ""))
        require(table.startswith(expected_table) and
                re.search(rf"fret {root}\s+{root - 1}-{root + 3}\s+{' '.join(triad_names)}$", table) is not None,
                f"TXT_RUNG_SUMMARY {rung}")
        page = 3 + index // 2
        page_line = 4 + 26 * (index % 2)
        pdf_block = pages[page][page_line - 1:page_line + 25]
        pdf_heading = f"{rung:02d}  {key.upper()} NATURAL MINOR" + (" - OCTAVE" if rung == 13 else "")
        require(len(pdf_block) == 26 and pdf_block[0] == pdf_heading and
                pdf_block[1] == f"ROOT E{root}  |  FRAME {root - 1}-{root + 3}" and
                pdf_block[2] == "66 NOTES / 22 TRIADS" and
                pdf_block[3] == "Scale tones: " + " ".join(tones) and
                pdf_block[4:24] == block[4:24] and
                pdf_block[24] == "Return to the low root; release pressure; move the complete frame one fret." and
                pdf_block[25] == "Triplet pulse: continuous alternate picking; do not reset",
                f"TXT_PDF_RUNG_MISMATCH {rung}")
        base_points = [(string, root + offset, finger)
                       for string, offsets, fingers in SCALE_SHAPE
                       for offset, finger in zip(offsets, fingers, strict=True)]
        require(len(base_points) == 15, "BASE_SCALE_SHAPE")
        triads = []
        for direction, row_start, expected_groups, expected_paths in (
            ("ascending", 5, expected_up, UP_PATH),
            ("descending", 15, expected_down, DOWN_PATH),
        ):
            source_rows = block[row_start:row_start + 9]
            hrm = split_cells(source_rows[0], "Hrm", rung, direction)
            deg = split_cells(source_rows[1], "Deg", rung, direction)
            fng = split_cells(source_rows[2], "Fng", rung, direction)
            tab_groups = parse_contact_cells(source_rows[3:], rung, direction)
            for cell_index, (contacts, degree_cell, finger_cell, function_cell) in enumerate(
                zip(tab_groups, deg, fng, hrm, strict=True), 1
            ):
                expected_degrees = expected_groups[cell_index - 1]
                degrees = re.findall(r"b\d+|\d+", degree_cell)
                fingers = [int(value) for value in re.findall(r"[1-4]", finger_cell)]
                function = function_cell.rstrip("-")
                root_index = DEGREES.index(expected_degrees[0] if direction == "ascending"
                                           else expected_degrees[-1]) % 7
                expected_function = FUNCTION[root_index]
                expected_chord = triad_names[root_index]
                expected_points = [base_points[DEGREES.index(degree)] for degree in expected_degrees]
                require(degrees == expected_degrees and len(fingers) == 3 and
                        function == expected_function and
                        "".join(string for string, _ in contacts) == expected_paths[cell_index - 1] and
                        contacts == [(string, fret) for string, fret, _ in expected_points] and
                        fingers == [finger for _, _, finger in expected_points],
                        f"TRIAD_CONTACT_MISMATCH {rung} {direction} {cell_index}")
                projected_contacts = []
                for contact_index, (degree, finger, (string, fret)) in enumerate(
                    zip(degrees, fingers, contacts, strict=True), 1
                ):
                    spelling = tones[DEGREES.index(degree)]
                    require(pitch_class(spelling) == (TUNING_PC[string] + fret) % 12,
                            f"TRIAD_PITCH_MISMATCH {rung} {direction} {cell_index} {contact_index}")
                    ordinal = len(triads) * 3 + contact_index
                    projected_contacts.append({"ordinal": ordinal, "contact_ordinal": contact_index,
                                               "string": string, "fret": fret, "finger_digit": finger,
                                               "degree": degree, "pitch_spelling": spelling,
                                               "onset_q": None, "duration_q": None})
                triads.append({"triad_ordinal": len(triads) + 1,
                               "direction": direction, "direction_triad_ordinal": cell_index,
                               "harmonic_function": function, "chord_name": expected_chord,
                               "chord_quality": QUALITY[root_index],
                               "string_path": expected_paths[cell_index - 1],
                               "source_cells": {"harmonic": function_cell, "degrees": degree_cell,
                                                "fingers": finger_cell,
                                                "tab_high_to_low": [row.split("|")[cell_index]
                                                                    for row in source_rows[3:]]},
                               "contacts": projected_contacts})
        require(len(triads) == 22 and sum(len(item["contacts"]) for item in triads) == 66 and
                triads[10]["contacts"][-1]["degree"] == "15" and
                triads[11]["contacts"][0]["degree"] == "15" and
                triads[10]["contacts"][-1]["string"] == triads[11]["contacts"][0]["string"] == "e" and
                triads[10]["contacts"][-1]["fret"] == triads[11]["contacts"][0]["fret"] == root and
                triads[0]["contacts"][0]["string"] == triads[-1]["contacts"][-1]["string"] == "E" and
                triads[0]["contacts"][0]["fret"] == triads[-1]["contacts"][-1]["fret"] == root,
                f"CELL_TURN_OR_ROOT {rung}")
        rungs.append({"source_local_key": f"L28-rung{rung:02d}", "rung": rung,
                      "key": key, "root_string": "E", "root_fret": root,
                      "frame_min_fret": root - 1, "frame_max_fret": root + 3,
                      "scale_tones_two_octaves": tones,
                      "diatonic_triad_names": triad_names,
                      "source_rows": {"ascending": block[5:14], "descending": block[15:24]},
                      "source_refs": {"txt": f"L28-TXT1-{start}-{start + 24}",
                                      "pdf": f"L28-PDF1-p{page}-L{page_line}-{page_line + 25}",
                                      "pdf_overview": "L28-PDF1-p2"},
                      "triads": triads, "canonical_item_id": None,
                      "canonical_variant_id": None, "onset_q": None,
                      "duration_q": None, "fixed_bpm": None, "note_per_click": None,
                      "runtime_eligible": False, "runtime_admitted": False,
                      "imported": False, "admitted": False})
    require(len(rungs) == 13 and [rung["root_fret"] for rung in rungs] == list(range(5, 18)),
            "RUNG_COVERAGE")
    guidance = {"degree_sequence_source": lines[22:24],
                "harmonic_function_source": lines[28:32],
                "shape_source": lines[33:42],
                "string_path_source": lines[43:48],
                "picking_source": lines[56:62], "rhythm_source": lines[63:67],
                "route_source": lines[76:80],
                "practice_is_timing_authority": False,
                "static_five_fret_stretch_inferred": False}
    return rungs, guidance


def build_candidate(*, txt_data: bytes | None = None, pdf_data: bytes | None = None,
                    root: Path = ROOT) -> dict[str, Any]:
    txt_data = local_bytes(root, TXT) if txt_data is None else txt_data
    pdf_data = local_bytes(root, PDF) if pdf_data is None else pdf_data
    verify(txt_data, TXT_PIN, "LEVEL28_TXT")
    verify(pdf_data, PDF_PIN, "LEVEL28_PDF")
    rungs, guidance = source_rungs(txt_data, pdf_data)
    route = []
    for ordinal, rung_index in enumerate(list(range(1, 14)) + list(range(12, 0, -1)), 1):
        rung = rungs[rung_index - 1]
        route.append({"cell_ordinal": ordinal, "rung": rung_index, "key": rung["key"],
                      "root_fret": rung["root_fret"], "triad_count": 22,
                      "contact_count": 66, "travel_direction": "up" if ordinal <= 13 else "down"})
    require(len(route) == 25 and route[0]["key"] == route[-1]["key"] == "A" and
            route[0]["root_fret"] == route[-1]["root_fret"] == 5 and
            route[12]["root_fret"] == 17 and
            all(abs(b["root_fret"] - a["root_fret"]) == 1 for a, b in zip(route, route[1:])),
            "ROUTE_COVERAGE")
    return {"schema": "fathom-level028-whole-detached-triad-candidate-v1",
            "wbs_id": "2.3.1.1.1", "classification": "noncanonical_nonadmitted_source_candidate",
            "level": 28, "source_title": "Natural Minor Diatonic Triads - Two-Octave Six-String Neck Ladder",
            "source": {"txt_path": TXT.as_posix(), "txt_bytes": TXT_PIN[0], "txt_sha256": TXT_PIN[1],
                       "pdf_path": PDF.as_posix(), "pdf_bytes": PDF_PIN[0], "pdf_sha256": PDF_PIN[1],
                       "pdf_pages": 10, "card_pdf_pages": [3, 4, 5, 6, 7, 8, 9]},
            "counts": {"rungs": 13, "triads_per_cell": 22, "contacts_per_cell": 66,
                       "unique_triads": 286, "unique_contacts": 858,
                       "round_trip_cells": 25, "round_trip_contacts": 1650},
            "rungs": rungs, "full_round_trip_route": route,
            "source_guidance": guidance, "source_discrepancies": [],
            "exceptions": [], "pending": ["Curriculum/musical review", "canonical identity allocation",
                                          "runtime admission and timing decisions"],
            "canonical_item_id": None, "canonical_variant_id": None,
            "onset_q": None, "duration_q": None, "fixed_bpm": None, "note_per_click": None,
            "runtime_eligible": False, "runtime_admitted": False,
            "imported": False, "admitted": False, "whole_workbook_complete": False}


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
        print(f"PASS detached Level 28 triads: 13 rungs, 286 unique triads, 858 contacts, 25-cell/1650-contact route; bytes={len(data)} sha256={digest(data)}")
        return 0
    except (CandidateError, OSError) as exc:
        print(f"FAIL {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
