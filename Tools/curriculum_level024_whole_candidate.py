#!/usr/bin/env python3
"""Build a detached, source-linked whole-Level-24 natural-minor rolling candidate."""

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
TXT_REL = Path("Notes/music/guitar project/TXT version/Scale_Exercises_Section_III_Level_24_Natural_Minor_Three_Note_Rolling_Sequence_Two_Octave_Six_String_Neck_Ladder.txt")
PDF_REL = Path("Notes/music/guitar project/PDF version/Scale_Exercises_Section_III_Level_24_Natural_Minor_Three_Note_Rolling_Sequence_Two_Octave_Six_String_Neck_Ladder.pdf")
TXT_BYTES = 42406
TXT_SHA256 = "2a91403130355b916d2d935a2df197cbe54a03d1d17cb32575ad6df73bee9988"
PDF_BYTES = 31268
PDF_SHA256 = "6f447ad03a5a0b21cee9ea20ab2cb561e9fb25f5cd7c6a5e8a5121b7657697ad"
BUILD_REL = Path("Build/parallel-09/2.3.1.1.1-level024-whole-r01")
KEYS = ("A", "Bb", "B", "C", "C#", "D", "Eb", "E", "F", "F#", "G", "G#", "A")
SCALE7 = (
    ("A", "B", "C", "D", "E", "F", "G"), ("Bb", "C", "Db", "Eb", "F", "Gb", "Ab"),
    ("B", "C#", "D", "E", "F#", "G", "A"), ("C", "D", "Eb", "F", "G", "Ab", "Bb"),
    ("C#", "D#", "E", "F#", "G#", "A", "B"), ("D", "E", "F", "G", "A", "Bb", "C"),
    ("Eb", "F", "Gb", "Ab", "Bb", "Cb", "Db"), ("E", "F#", "G", "A", "B", "C", "D"),
    ("F", "G", "Ab", "Bb", "C", "Db", "Eb"), ("F#", "G#", "A", "B", "C#", "D", "E"),
    ("G", "A", "Bb", "C", "D", "Eb", "F"), ("G#", "A#", "B", "C#", "D#", "E", "F#"),
    ("A", "B", "C", "D", "E", "F", "G"),
)
POSITION_LABELS = ("1", "2", "b3", "4", "5", "b6", "b7", "8", "9", "b10", "11", "12", "b13", "b14", "15")
POSITION_FINGERS = ("1", "3", "4", "1", "3", "4", "1", "3", "1", "2", "4", "1", "2", "4", "1")
ROWS = ("e", "B", "G", "D", "A", "E")
ASC_GROUPS = tuple(tuple(range(start, start + 3)) for start in range(1, 14))
DESC_GROUPS = tuple(tuple(range(start, start - 3, -1)) for start in range(15, 2, -1))
TXT_HEADER = re.compile(r"^RUNG (\d{2}) OF 13 - (.+) NATURAL MINOR( \(OCTAVE\))? - ROOT ON LOW E FRET (\d+) - FRAME (\d+)-(\d+)$")
CELL_LABEL = "78-note cell: 13 ascending rolling triplets, repeat the high root at the turn, then 13 descending triplets."
ASC_LABEL = "ASCENDING - 13 TRIPLETS / 39 NOTES"
DESC_LABEL = "DESCENDING - 13 TRIPLETS / 39 NOTES"
TXT_FOOTER = "Finish on the low root, release pressure, and move the entire frame one fret in the route direction."
PDF_FOOTER = "Return to the low root; release pressure; move the entire frame one fret."
PDF_PICKING = "Continuous alternate picking - D-start and U-start"


class CandidateError(ValueError):
    """Pinned source, printed structure, or output boundary failed."""


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _verify(data: bytes, size: int, sha: str, label: str) -> None:
    if len(data) != size or digest(data) != sha:
        raise CandidateError(f"PINNED_INPUT_DRIFT {label}: bytes={len(data)} sha256={digest(data)}")


def _root() -> Path:
    result = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if result.returncode or Path(result.stdout.strip()).resolve() != ROOT.resolve():
        raise CandidateError("REPOSITORY_ROOT_MISMATCH")
    return ROOT


def _source_bytes(root: Path, rel: Path) -> bytes:
    path = root / rel
    if path.is_symlink() or not path.is_file() or path.resolve().parent != path.parent.resolve():
        raise CandidateError(f"SOURCE_PATH_INVALID {rel}")
    return path.read_bytes()


def _cells(row: str, label: str) -> list[str]:
    parts = row.split("|")
    if len(parts) != 15 or parts[0] != label or parts[-1] != "":
        raise CandidateError(f"ROW_SHAPE_INVALID {label}")
    cells = parts[1:-1]
    if any(len(cell) != 9 for cell in cells):
        raise CandidateError(f"GROUP_WIDTH_INVALID {label}")
    return cells


def _slots(cell: str, label: str) -> list[int | None]:
    values = []
    for offset in (0, 3, 6):
        text = cell[offset:offset + 3]
        token = text.rstrip("-")
        if token:
            if not token.isdigit() or token + "-" * (3 - len(token)) != text:
                raise CandidateError(f"SLOT_INVALID {label}: {text}")
            values.append(int(token))
        elif text == "---":
            values.append(None)
        else:
            raise CandidateError(f"SLOT_INVALID {label}: {text}")
    return values


def _expected_place(position: int, root: int) -> tuple[str, int]:
    shifts = (("E", 0), ("E", 2), ("E", 3), ("A", 0), ("A", 2), ("A", 3), ("D", 0), ("D", 2),
              ("G", -1), ("G", 0), ("G", 2), ("B", 0), ("B", 1), ("B", 3), ("e", 0))
    string, delta = shifts[position - 1]
    return string, root + delta


def _parse_half(pos_row: str, fng_row: str, tab_rows: list[str], root: int, half: str,
                crossing: tuple[str, ...]) -> list[dict[str, Any]]:
    if len(tab_rows) != 6 or len(crossing) != 13:
        raise CandidateError("TAB_OR_CROSSING_COUNT")
    positions = [_slots(cell, "Pos") for cell in _cells(pos_row, "Pos")]
    fingers = [_slots(cell, "Fng") for cell in _cells(fng_row, "Fng")]
    tab = {string: [_slots(cell, string) for cell in _cells(row, f"{string}  ")]
           for string, row in zip(ROWS, tab_rows, strict=True)}
    groups = []
    expected_groups = ASC_GROUPS if half == "up" else DESC_GROUPS
    for group_index, expected_positions in enumerate(expected_groups):
        notes = []
        for slot_index, position in enumerate(expected_positions):
            finger = POSITION_FINGERS[position - 1]
            if positions[group_index][slot_index] != position or fingers[group_index][slot_index] != int(finger):
                raise CandidateError(f"POS_FNG_SEQUENCE_MISMATCH {half} {group_index+1} {slot_index+1}")
            printed = [(string, value) for string in ROWS if (value := tab[string][group_index][slot_index]) is not None]
            if len(printed) != 1:
                raise CandidateError(f"TAB_NOTE_CARDINALITY {half} {group_index+1} {slot_index+1}")
            string, fret = printed[0]
            if (string, fret) != _expected_place(position, root):
                raise CandidateError(f"TAB_POSITION_FRET_MISMATCH {half} {group_index+1} {slot_index+1}")
            ordinal = (0 if half == "up" else 39) + group_index * 3 + slot_index + 1
            notes.append({"ordinal": ordinal, "half": half, "group": group_index + 1, "slot": slot_index + 1,
                          "position": position, "altered_degree": POSITION_LABELS[position - 1], "finger_digit": finger,
                          "string": string, "fret": fret, "is_high_root_turn": ordinal in (39, 40),
                          "onset_q": None, "duration_q": None})
        pattern = "".join(note["string"] for note in notes)
        if pattern != crossing[group_index]:
            raise CandidateError(f"STRING_CROSSING_MISMATCH {half} {group_index+1}: {pattern}")
        groups.append({"ordinal": (0 if half == "up" else 13) + group_index + 1, "half": half,
                       "string_pattern": pattern, "notes": notes})
    return groups


def _validate_turn(groups: list[dict[str, Any]], root: int) -> None:
    if len(groups) != 26:
        raise CandidateError("ROLLING_GROUP_COUNT")
    notes = [note for group in groups for note in group["notes"]]
    if len(notes) != 78 or [note["ordinal"] for note in notes] != list(range(1, 79)):
        raise CandidateError("ROLLING_NOTE_COUNT")
    if (notes[38]["position"], notes[39]["position"], notes[38]["string"], notes[39]["string"], notes[38]["fret"], notes[39]["fret"]) != (15, 15, "e", "e", root, root):
        raise CandidateError("HIGH_ROOT_TURN_MISMATCH")


def _txt_rungs(data: bytes) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    try:
        lines = data.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise CandidateError("TXT_ENCODING_INVALID") from exc
    if lines[:2] != ["SCALE EXERCISES - SECTION III, LEVEL 24", "NATURAL MINOR THREE-NOTE ROLLING SEQUENCE - TWO-OCTAVE SIX-STRING NECK LADDER: A TO A"]:
        raise CandidateError("TXT_HEADER_MISMATCH")
    if lines[384] != "FULL ROUND-TRIP CHALLENGE":
        raise CandidateError("TXT_RUNG_END_BOUNDARY_MISMATCH")
    if lines[21] != "One octave: 1 2 b3 4 5 b6 b7 8" or lines[22] != "Two octaves: 1 2 b3 4 5 b6 b7 8 9 b10 11 12 b13 b14 15":
        raise CandidateError("TXT_ALTERED_DEGREE_MAP_MISMATCH")
    cross_up = tuple(lines[43].partition(":")[2].strip().split(" | "))
    cross_down = tuple(lines[44].partition(":")[2].strip().split(" | "))
    if cross_up != ("EEE", "EEA", "EAA", "AAA", "AAD", "ADD", "DDG", "DGG", "GGG", "GGB", "GBB", "BBB", "BBe") or cross_down != ("eBB", "BBB", "BBG", "BGG", "GGG", "GGD", "GDD", "DDA", "DAA", "AAA", "AAE", "AEE", "EEE"):
        raise CandidateError("TXT_CROSSING_MAP_MISMATCH")
    if lines[58] != "UP:   A(5) > Bb(6) > B(7) > C(8) > C#(9) > D(10) > Eb(11) > E(12) > F(13) > F#(14) > G(15) > G#(16) > A(17)" or lines[59] != "DOWN: A(17) > G#(16) > G(15) > F#(14) > F(13) > E(12) > Eb(11) > D(10) > C#(9) > C(8) > B(7) > Bb(6) > A(5)":
        raise CandidateError("TXT_CHROMATIC_ROUTE_MISMATCH")
    rungs = []
    for index, key in enumerate(KEYS):
        start = 72 + 24 * index
        block = lines[start:start + 22]
        root = 5 + index
        match = TXT_HEADER.fullmatch(block[0]) if len(block) == 22 else None
        if match is None or (match.group(1), match.group(2), bool(match.group(3)), int(match.group(4)), int(match.group(5)), int(match.group(6))) != (f"{index+1:02d}", key.upper(), index == 12, root, root-1, root+3):
            raise CandidateError(f"TXT_RUNG_HEADER_MISMATCH {index+1}")
        tones = [*SCALE7[index], *SCALE7[index], key]
        if block[1] != "Scale tones across two octaves: " + " ".join(tones) or block[2] != CELL_LABEL:
            raise CandidateError(f"TXT_TONES_OR_CELL_MISMATCH {index+1}")
        if block[3] != ASC_LABEL or block[12] != DESC_LABEL or block[21] != TXT_FOOTER:
            raise CandidateError(f"TXT_CARD_SHAPE_MISMATCH {index+1}")
        asc = _parse_half(block[4], block[5], block[6:12], root, "up", cross_up)
        desc = _parse_half(block[13], block[14], block[15:21], root, "down", cross_down)
        groups = asc + desc
        _validate_turn(groups, root)
        rungs.append({"rung": index+1, "key": key, "root_fret": root, "frame": [root-1, root+3],
                      "scale_tones": tones, "source_ref": f"L24-TXT1-{start+1}-{start+22}",
                      "printed": {"heading": block[0], "scale_tones": block[1], "cell_label": block[2],
                                  "ascending_label": block[3], "ascending_pos": block[4], "ascending_fng": block[5],
                                  "ascending_tab": block[6:12], "descending_label": block[12], "descending_pos": block[13],
                                  "descending_fng": block[14], "descending_tab": block[15:21], "footer": block[21]},
                      "groups": groups})
    round_trip = "\n".join(lines[385:391])
    if not all(phrase in round_trip for phrase in ("rungs 01-13", "rungs 12-01", "25 cells x 78 notes = 1,950")):
        raise CandidateError("TXT_ROUND_TRIP_MISMATCH")
    guidance = {"purpose_text": "\n".join(lines[4:8]), "purpose_ref": "L24-TXT1-5-8",
                "formula_text": "\n".join(lines[21:25]), "formula_ref": "L24-TXT1-22-25",
                "shape_text": "\n".join(lines[27:35]), "shape_ref": "L24-TXT1-28-35",
                "sequence_text": "\n".join(lines[37:41]), "sequence_ref": "L24-TXT1-38-41",
                "crossing_map_text": "\n".join(lines[43:47]), "crossing_map_ref": "L24-TXT1-44-47",
                "cell_picking_text": "\n".join(lines[49:56]), "cell_picking_ref": "L24-TXT1-50-56",
                "neck_route_text": "\n".join(lines[58:60]), "neck_route_ref": "L24-TXT1-59-60",
                "practice_text": "\n".join(lines[62:70]), "practice_ref": "L24-TXT1-63-70",
                "round_trip_text": round_trip, "round_trip_ref": "L24-TXT1-386-391",
                "clean_standard_text": "\n".join(lines[393:396]), "clean_standard_ref": "L24-TXT1-394-396",
                "pdf_ref": "L24-PDF1-p1-p2-p9-p10",
                "crossing_up": list(cross_up), "crossing_down": list(cross_down)}
    if not all(phrase in guidance["practice_text"] for phrase in ("eighth-note triplets", "15-20 BPM below", "pause one beat", "two separate days")):
        raise CandidateError("TXT_PRACTICE_GUIDANCE_MISMATCH")
    return rungs, guidance


def _pdf_rungs(data: bytes, cross_up: tuple[str, ...], cross_down: tuple[str, ...]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    try:
        reader = PdfReader(BytesIO(data), strict=True)
        if len(reader.pages) != 10:
            raise CandidateError(f"PDF_PAGE_COUNT {len(reader.pages)}")
        pages = [(page.extract_text() or "").splitlines() for page in reader.pages]
    except CandidateError:
        raise
    except Exception as exc:
        raise CandidateError(f"PDF_READ_FAILED {type(exc).__name__}") from exc
    if not all(any(phrase in line for line in pages[0]) for phrase in ("26 triplets", "natural-minor", "Page 1 of 10")):
        raise CandidateError("PDF_INTRO_GUIDANCE_MISMATCH")
    route_page = pages[1]
    if route_page[:10] != ["Level 24 - Chromatic Natural-Minor Route and Two-Octave Sequence Map",
                           "Standard tuning. Two-octave 6th-string-root natural minor. One completed cell = 78 notes.",
                           "Page 2 of 10", "Ascending route: complete one 78-note rolling cell, then move the frame +1 fret",
                           "Descending route: use the same cards in reverse order and move -1 fret",
                           "Rung", "Key", "Low-E root", "Frame", "Scale tones (degrees 1-b7)"]:
        raise CandidateError("PDF_ROUTE_MAP_HEADER_MISMATCH")
    for index, key in enumerate(KEYS):
        root = 5 + index
        chunk = route_page[10 + 5 * index:15 + 5 * index]
        expected = [f"{index+1:02d}", f"{key} natural minor" + (" - octave" if index == 12 else ""),
                    f"fret {root}", f"{root-1}-{root+3}", " ".join(SCALE7[index])]
        if chunk != expected:
            raise CandidateError(f"PDF_ROUTE_MAP_RUNG_MISMATCH {index+1}")
    tail = "\n".join(route_page[75:])
    if not all(phrase in tail for phrase in ("rungs 01-13", "rungs 12-01. Skip the high-A", "b3", "b10", "1,950 picked notes")):
        raise CandidateError("PDF_ROUTE_MAP_TAIL_MISMATCH")
    rungs = []
    for page_number in range(3, 10):
        lines = pages[page_number - 1]
        if page_number < 9:
            first_rung = 1 + 2 * (page_number - 3)
            if lines[:5] != ["Level 24 - Natural Minor Three-Note Rolling Sequence: Two Octaves",
                             "Eighth-note triplets: one three-note group per beat. Never restart alternate picking at a group boundary.",
                             f"Page {page_number} of 10",
                             f"Rungs {first_rung:02d}-{first_rung+1:02d}: play each card as one 26-triplet cell, then move +1 fret",
                             "For the descending pass, read the cards in reverse order and move -1 fret"] or len(lines) != 53:
                raise CandidateError(f"PDF_RUNG_PAGE_SHAPE {page_number}")
            blocks = [lines[5:29], lines[29:53]]
        else:
            if lines[:5] != ["Level 24 - Final Rung and Full Round-Trip Challenge",
                             "The complete A-to-A-to-A route contains 25 cells and 1,950 continuously picked notes.",
                             "Page 9 of 10", "Rung 13: complete the high-A cell at fret 17, then reverse the neck route",
                             "Do not replay rung 13 during the down pass unless beginning a new round"]:
                raise CandidateError("PDF_FINAL_PAGE_SHAPE")
            blocks = [lines[5:29]]
            if not all(phrase in "\n".join(lines[29:]) for phrase in ("rungs 01-13", "rungs 12-01", "1,950 notes")):
                raise CandidateError("PDF_FINAL_ROUND_TRIP_MISMATCH")
        for block in blocks:
            index = len(rungs)
            key, root = KEYS[index], 5 + index
            expected_head = [f"{index+1:02d}  {key.upper()} NATURAL MINOR" + (" - OCTAVE" if index == 12 else ""),
                             f"ROOT E{root}  |  FRAME {root-1}-{root+3}", "78 NOTES / 26 TRIPLETS",
                             "Scale tones: " + " ".join((*SCALE7[index], *SCALE7[index], key)), ASC_LABEL]
            if len(block) != 24 or block[:5] != expected_head or block[13] != DESC_LABEL or block[22:] != [PDF_FOOTER, PDF_PICKING]:
                raise CandidateError(f"PDF_RUNG_CARD_MISMATCH {index+1}")
            asc = _parse_half(block[5], block[6], block[7:13], root, "up", cross_up)
            desc = _parse_half(block[14], block[15], block[16:22], root, "down", cross_down)
            groups = asc + desc
            _validate_turn(groups, root)
            rungs.append({"rung": index+1, "key": key, "root_fret": root, "frame": [root-1, root+3],
                          "source_ref": f"L24-PDF1-p{page_number}", "printed": {"heading": block[0], "root_frame": block[1],
                          "cell_label": block[2], "scale_tones": block[3], "ascending_label": block[4],
                          "ascending_pos": block[5], "ascending_fng": block[6], "ascending_tab": block[7:13],
                          "descending_label": block[13], "descending_pos": block[14], "descending_fng": block[15],
                          "descending_tab": block[16:22], "footer": block[22], "picking": block[23]}, "groups": groups})
    if len(rungs) != 13:
        raise CandidateError(f"PDF_RUNG_COUNT {len(rungs)}")
    if not all(any(phrase in line for line in pages[9]) for phrase in ("Level 24 - Practice Architecture", "triplets", "Page 10 of 10")):
        raise CandidateError("PDF_PRACTICE_PAGE_MISMATCH")
    route = {"map_ref": "L24-PDF1-p2", "map_header": route_page[:10], "map_rows": route_page[10:75],
             "map_guidance": route_page[75:], "final_round_trip_ref": "L24-PDF1-p9",
             "final_round_trip_text": "\n".join(pages[8][29:39]), "practice_ref": "L24-PDF1-p10"}
    return rungs, route


def build_candidate(*, txt_data: bytes | None = None, pdf_data: bytes | None = None) -> dict[str, Any]:
    root = _root()
    txt_data = _source_bytes(root, TXT_REL) if txt_data is None else txt_data
    pdf_data = _source_bytes(root, PDF_REL) if pdf_data is None else pdf_data
    _verify(txt_data, TXT_BYTES, TXT_SHA256, "L24-TXT")
    _verify(pdf_data, PDF_BYTES, PDF_SHA256, "L24-PDF")
    txt_rungs, instructions = _txt_rungs(txt_data)
    pdf_rungs, pdf_route = _pdf_rungs(pdf_data, tuple(instructions["crossing_up"]), tuple(instructions["crossing_down"]))
    records = []
    for txt, pdf in zip(txt_rungs, pdf_rungs, strict=True):
        if (txt["rung"], txt["key"], txt["root_fret"], txt["frame"]) != (pdf["rung"], pdf["key"], pdf["root_fret"], pdf["frame"]):
            raise CandidateError(f"PDF_TXT_RUNG_MISMATCH {txt['rung']}")
        for field in ("ascending_pos", "ascending_fng", "ascending_tab", "descending_pos", "descending_fng", "descending_tab"):
            if txt["printed"][field] != pdf["printed"][field]:
                raise CandidateError(f"PDF_TXT_ROW_MISMATCH {txt['rung']} {field}")
        if txt["groups"] != pdf["groups"]:
            raise CandidateError(f"PDF_TXT_GROUP_MISMATCH {txt['rung']}")
        records.append({"source_local_key": f"L24-rung{txt['rung']:02d}", "rung": txt["rung"], "key": txt["key"],
                        "key_label": f"{txt['key']} natural minor" + (" - octave" if txt["rung"] == 13 else ""),
                        "root_string": "E", "root_fret": txt["root_fret"], "frame": txt["frame"], "scale_tones": txt["scale_tones"],
                        "position_degree_map": list(POSITION_LABELS), "source_refs": {"txt": txt["source_ref"],
                        "pdf_card": pdf["source_ref"], "pdf_map": "L24-PDF1-p2"},
                        "printed_txt": txt["printed"], "printed_pdf": pdf["printed"], "groups": txt["groups"],
                        "canonical_item_id": None, "canonical_variant_id": None, "onset_q": None, "duration_q": None,
                        "note_per_click": None, "fixed_bpm": None, "runtime_eligible": False, "runtime_admitted": False,
                        "imported": False, "admitted": False})
    up = list(range(1, 14))
    down = list(range(12, 0, -1))
    route = {"ascending_landmarks": [{"rung": n, "key": KEYS[n-1], "root_fret": n+4} for n in up],
             "descending_landmarks": [{"rung": n, "key": KEYS[n-1], "root_fret": n+4} for n in range(13, 0, -1)],
             "descending_rungs_after_turn": down, "single_turn_cell_sequence": up + down,
             "single_turn_cell_count": 25, "notes_per_cell": 78, "single_turn_note_count": 1950,
             "turn_rung_played_once": 13, "up_fret_step": 1, "down_fret_step": -1,
             "txt_ref": "L24-TXT1-59-60,L24-TXT1-386-391", "pdf_ref": "L24-PDF1-p2,L24-PDF1-p9"}
    return {"schema": "fathom-level024-whole-detached-candidate-v1", "wbs_id": "2.3.1.1.1", "level": 24,
            "source": {"txt_path": TXT_REL.as_posix(), "txt_bytes": TXT_BYTES, "txt_sha256": TXT_SHA256,
                       "pdf_path": PDF_REL.as_posix(), "pdf_bytes": PDF_BYTES, "pdf_sha256": PDF_SHA256, "pdf_pages": 10},
            "instructions": instructions, "pdf_route_map": pdf_route, "neck_route": route, "records": records, "exceptions": [],
            "pending": ["canonical identity allocation and admission", "Curriculum/musical review", "runtime note timing and performed audio"],
            "whole_source_batch_structurally_reconciled": True, "runtime_eligible": False, "runtime_admitted": False,
            "imported": False, "admitted": False}


def write_candidate(output: Path) -> dict[str, Any]:
    root = _root()
    target = output if output.is_absolute() else root / output
    allowed = root / BUILD_REL
    if not target.parent.exists() or target.parent.is_symlink() or target.parent.resolve() != allowed.resolve():
        raise CandidateError(f"OUTPUT_OUTSIDE_LANE_BUILD {output}")
    if target.suffix != ".json" or target.is_symlink():
        raise CandidateError(f"OUTPUT_INVALID {output}")
    data = (json.dumps(build_candidate(), indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
    try:
        with target.open("xb") as handle:
            handle.write(data)
    except FileExistsError as exc:
        raise CandidateError(f"OUTPUT_EXISTS {output}") from exc
    return {"output": str(target.relative_to(root)), "bytes": len(data), "sha256": digest(data), "records": 13}


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
