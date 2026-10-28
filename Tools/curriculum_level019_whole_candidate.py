#!/usr/bin/env python3
"""Build a detached, source-linked whole-Level-19 diatonic-triad candidate."""

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
TXT_REL = Path("Notes/music/guitar project/TXT version/Scale_Exercises_Section_II_Level_19_Major_Scale_Diatonic_Triads_Two_Octave_Six_String_Neck_Ladder.txt")
PDF_REL = Path("Notes/music/guitar project/PDF version/Scale_Exercises_Section_II_Level_19_Major_Scale_Diatonic_Triads_Two_Octave_Six_String_Neck_Ladder.pdf")
TXT_BYTES = 40736
TXT_SHA256 = "d4d0bebee8d9d2b6899bde448a0f5017070eef7936c2ccd6ffa03e7b95a4ce26"
PDF_BYTES = 32552
PDF_SHA256 = "107bfaecd5daa15adc1117440d01feead623f831e720837de5d18662375166e6"
BUILD_REL = Path("Build/parallel-09/2.3.1.1.1-level019-whole-r01")
KEYS = ("A", "Bb", "B", "C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A")
SCALE7 = (
    ("A", "B", "C#", "D", "E", "F#", "G#"), ("Bb", "C", "D", "Eb", "F", "G", "A"),
    ("B", "C#", "D#", "E", "F#", "G#", "A#"), ("C", "D", "E", "F", "G", "A", "B"),
    ("Db", "Eb", "F", "Gb", "Ab", "Bb", "C"), ("D", "E", "F#", "G", "A", "B", "C#"),
    ("Eb", "F", "G", "Ab", "Bb", "C", "D"), ("E", "F#", "G#", "A", "B", "C#", "D#"),
    ("F", "G", "A", "Bb", "C", "D", "E"), ("Gb", "Ab", "Bb", "Cb", "Db", "Eb", "F"),
    ("G", "A", "B", "C", "D", "E", "F#"), ("Ab", "Bb", "C", "Db", "Eb", "F", "G"),
    ("A", "B", "C#", "D", "E", "F#", "G#"),
)
CHORDS7 = (
    ("A", "Bm", "C#m", "D", "E", "F#m", "G#dim"), ("Bb", "Cm", "Dm", "Eb", "F", "Gm", "Adim"),
    ("B", "C#m", "D#m", "E", "F#", "G#m", "A#dim"), ("C", "Dm", "Em", "F", "G", "Am", "Bdim"),
    ("Db", "Ebm", "Fm", "Gb", "Ab", "Bbm", "Cdim"), ("D", "Em", "F#m", "G", "A", "Bm", "C#dim"),
    ("Eb", "Fm", "Gm", "Ab", "Bb", "Cm", "Ddim"), ("E", "F#m", "G#m", "A", "B", "C#m", "D#dim"),
    ("F", "Gm", "Am", "Bb", "C", "Dm", "Edim"), ("Gb", "Abm", "Bbm", "Cb", "Db", "Ebm", "Fdim"),
    ("G", "Am", "Bm", "C", "D", "Em", "F#dim"), ("Ab", "Bbm", "Cm", "Db", "Eb", "Fm", "Gdim"),
    ("A", "Bm", "C#m", "D", "E", "F#m", "G#dim"),
)
ROMANS = ("I", "ii", "iii", "IV", "V", "vi", "vii-dim")
QUALITIES = ("major", "minor", "minor", "major", "major", "minor", "diminished")
DEGREE_FINGERS = ("2", "4", "1", "2", "4", "1", "3", "4", "1", "3", "4", "2", "4", "1", "2")
ROWS = ("e", "B", "G", "D", "A", "E")
ASC_ROOTS = tuple(range(1, 12))
DESC_TOPS = tuple(range(15, 4, -1))
TXT_RUNG_HEADER = re.compile(r"^RUNG (\d{2}) OF 13 - (.+) MAJOR( - OCTAVE)? - ROOT ON LOW E FRET (\d+) - FRAME (\d+)-(\d+)$")
TXT_MAP_ROW = re.compile(r"^(\d{2})\s+(.+?)\s+fret (\d+)\s+(\d+)-(\d+)\s+(.+)$")
CELL_LABEL = "66-note cell: 11 ascending triads, repeat the high root at the turn, then 11 descending triads."
ASC_LABEL = "ASCENDING - 11 TRIADS / 33 NOTES"
DESC_LABEL = "DESCENDING - 11 TRIADS / 33 NOTES"
TXT_CARD_FOOTER = "Finish on the low root, release pressure, and move the entire frame one fret in the route direction."
PDF_CARD_FOOTER = "Return to the low root; release pressure; move the entire frame one fret."
PDF_PICKING = "Triad pulse: D-U-D / U-D-U; do not reset"


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
    if len(parts) != 13 or parts[0] != label or parts[-1] != "":
        raise CandidateError(f"ROW_SHAPE_INVALID {label}")
    cells = parts[1:-1]
    if any(len(cell) != 9 for cell in cells):
        raise CandidateError(f"GROUP_WIDTH_INVALID {label}")
    return cells


def _numeric_slots(cell: str, label: str) -> list[int | None]:
    slots = []
    for offset in (0, 3, 6):
        text = cell[offset:offset + 3]
        token = text.rstrip("-")
        if token:
            if not token.isdigit() or token + "-" * (3 - len(token)) != text:
                raise CandidateError(f"SLOT_INVALID {label}: {text}")
            slots.append(int(token))
        elif text == "---":
            slots.append(None)
        else:
            raise CandidateError(f"SLOT_INVALID {label}: {text}")
    return slots


def _expected_place(degree: int, root: int) -> tuple[str, int]:
    shifts = (("E", 0), ("E", 2), ("A", -1), ("A", 0), ("A", 2), ("D", -1), ("D", 1), ("D", 2),
              ("G", -1), ("G", 1), ("G", 2), ("B", 0), ("B", 2), ("e", -1), ("e", 0))
    string, delta = shifts[degree - 1]
    return string, root + delta


def _parse_half(hrm_row: str, deg_row: str, fng_row: str, tab_rows: list[str], root: int, half: str,
                chords: tuple[str, ...]) -> list[dict[str, Any]]:
    if len(tab_rows) != 6:
        raise CandidateError("TAB_ROW_COUNT")
    harmony = _cells(hrm_row, "Hrm")
    degrees = [_numeric_slots(cell, "Deg") for cell in _cells(deg_row, "Deg")]
    fingers = [_numeric_slots(cell, "Fng") for cell in _cells(fng_row, "Fng")]
    tab = {string: [_numeric_slots(cell, string) for cell in _cells(row, f"{string}  ")]
           for string, row in zip(ROWS, tab_rows, strict=True)}
    if any(len(groups) != 11 for groups in (harmony, degrees, fingers, *tab.values())):
        raise CandidateError("TRIAD_GROUP_COUNT")
    triads = []
    for group_index in range(11):
        top_or_root = ASC_ROOTS[group_index] if half == "up" else DESC_TOPS[group_index]
        expected_degrees = (top_or_root, top_or_root + 2, top_or_root + 4) if half == "up" else (top_or_root, top_or_root - 2, top_or_root - 4)
        # Python's zero-based index: degree 1 and 8 both map to index 0.
        function_index = ((expected_degrees[0] if half == "up" else expected_degrees[-1]) - 1) % 7
        expected_roman = ROMANS[function_index]
        printed_roman = harmony[group_index].rstrip("-")
        if printed_roman != expected_roman or harmony[group_index] != printed_roman + "-" * (9 - len(printed_roman)):
            raise CandidateError(f"HARMONIC_FUNCTION_MISMATCH {half} {group_index+1}")
        roles = ("root", "third", "fifth") if half == "up" else ("fifth", "third", "root")
        notes = []
        for slot_index, (degree, role) in enumerate(zip(expected_degrees, roles, strict=True)):
            finger = DEGREE_FINGERS[degree - 1]
            if degrees[group_index][slot_index] != degree or fingers[group_index][slot_index] != int(finger):
                raise CandidateError(f"DEG_FNG_SEQUENCE_MISMATCH {half} {group_index+1} {slot_index+1}")
            printed = [(string, value) for string in ROWS if (value := tab[string][group_index][slot_index]) is not None]
            if len(printed) != 1:
                raise CandidateError(f"TAB_NOTE_CARDINALITY {half} {group_index+1} {slot_index+1}")
            string, fret = printed[0]
            if (string, fret) != _expected_place(degree, root):
                raise CandidateError(f"TAB_DEGREE_FRET_MISMATCH {half} {group_index+1} {slot_index+1}")
            ordinal = (0 if half == "up" else 33) + group_index * 3 + slot_index + 1
            notes.append({"ordinal": ordinal, "half": half, "triad": group_index + 1, "slot": slot_index + 1,
                          "role": role, "degree": degree, "finger_digit": finger, "string": string, "fret": fret,
                          "is_high_root_turn": ordinal in (33, 34), "onset_q": None, "duration_q": None})
        triads.append({"ordinal": (0 if half == "up" else 11) + group_index + 1, "half": half,
                       "harmonic_root_degree": expected_degrees[0] if half == "up" else expected_degrees[-1],
                       "function_degree": function_index + 1, "roman": expected_roman, "quality": QUALITIES[function_index],
                       "chord_name": chords[function_index], "notes": notes})
    return triads


def _validate_turn(triads: list[dict[str, Any]], root: int) -> None:
    if len(triads) != 22:
        raise CandidateError("TRIAD_CELL_COUNT")
    notes = [note for triad in triads for note in triad["notes"]]
    if len(notes) != 66 or [note["ordinal"] for note in notes] != list(range(1, 67)):
        raise CandidateError("TRIAD_NOTE_COUNT")
    if (notes[32]["degree"], notes[33]["degree"], notes[32]["string"], notes[33]["string"], notes[32]["fret"], notes[33]["fret"]) != (15, 15, "e", "e", root, root):
        raise CandidateError("HIGH_ROOT_TURN_MISMATCH")


def _txt_rungs(data: bytes) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    try:
        lines = data.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise CandidateError("TXT_ENCODING_INVALID") from exc
    if lines[:2] != ["SCALE EXERCISES - SECTION II, LEVEL 19", "MAJOR SCALE DIATONIC TRIADS - TWO-OCTAVE SIX-STRING NECK LADDER"]:
        raise CandidateError("TXT_HEADER_MISMATCH")
    if lines[67] != "COMPLETE TABLATURE" or lines[434] != "FULL ROUND-TRIP CHALLENGE":
        raise CandidateError("TXT_SECTION_BOUNDARY_MISMATCH")
    if lines[45] != "Up:   A -> Bb -> B -> C -> Db -> D -> Eb -> E -> F -> Gb -> G -> Ab -> A" or lines[46] != "Down: Ab -> G -> Gb -> F -> E -> Eb -> D -> Db -> C -> B -> Bb -> A" or "Do not replay the high A-major rung" not in lines[47]:
        raise CandidateError("TXT_CHROMATIC_ROUTE_MISMATCH")
    map_rows = []
    for index, key in enumerate(KEYS):
        match = TXT_MAP_ROW.fullmatch(lines[52 + index])
        root = 5 + index
        label = f"{key} major" + (" - octave" if index == 12 else "")
        if match is None or (match.group(1), match.group(2), int(match.group(3)), int(match.group(4)), int(match.group(5)), match.group(6).split()) != (f"{index+1:02d}", label, root, root-1, root+2, list(CHORDS7[index])):
            raise CandidateError(f"TXT_ROUTE_MAP_RUNG_MISMATCH {index+1}")
        map_rows.append(lines[52 + index])
    if not all(phrase in "\n".join(lines[10:23]) for phrase in ("11 ascending triads / 33 notes", "11 descending triads / 33 notes", "22 triads / 66 notes", "repeat the high root")):
        raise CandidateError("TXT_SEQUENCE_GUIDANCE_MISMATCH")
    rungs = []
    for index, key in enumerate(KEYS):
        start = 70 + 28 * index
        block = lines[start:start + 25]
        root = 5 + index
        match = TXT_RUNG_HEADER.fullmatch(block[0]) if len(block) == 25 else None
        if match is None or (match.group(1), match.group(2), bool(match.group(3)), int(match.group(4)), int(match.group(5)), int(match.group(6))) != (f"{index+1:02d}", key, index == 12, root, root-1, root+2):
            raise CandidateError(f"TXT_RUNG_HEADER_MISMATCH {index+1}")
        tones = [*SCALE7[index], *SCALE7[index], key]
        if block[1] != "Scale tones across two octaves: " + " ".join(tones) or block[2] != "Diatonic triads: " + " | ".join(CHORDS7[index]):
            raise CandidateError(f"TXT_TONES_OR_TRIADS_MISMATCH {index+1}")
        if block[3:5] != [CELL_LABEL, ASC_LABEL] or block[14] != DESC_LABEL or block[24] != TXT_CARD_FOOTER:
            raise CandidateError(f"TXT_CARD_SHAPE_MISMATCH {index+1}")
        asc = _parse_half(block[5], block[6], block[7], block[8:14], root, "up", CHORDS7[index])
        desc = _parse_half(block[15], block[16], block[17], block[18:24], root, "down", CHORDS7[index])
        triads = asc + desc
        _validate_turn(triads, root)
        rungs.append({"rung": index+1, "key": key, "root_fret": root, "frame": [root-1, root+2], "scale_tones": tones,
                      "chord_names": list(CHORDS7[index]), "source_ref": f"L19-TXT1-{start+1}-{start+25}",
                      "printed": {"heading": block[0], "scale_tones": block[1], "chord_names": block[2], "cell_label": block[3],
                                  "ascending_label": block[4], "ascending_hrm": block[5], "ascending_deg": block[6],
                                  "ascending_fng": block[7], "ascending_tab": block[8:14], "descending_label": block[14],
                                  "descending_hrm": block[15], "descending_deg": block[16], "descending_fng": block[17],
                                  "descending_tab": block[18:24], "footer": block[24]}, "triads": triads})
    round_trip = "\n".join(lines[436:443])
    if not all(phrase in round_trip for phrase in ("rungs 01-13", "rungs 12-01", "25 cells x 66 notes = 1,650", "add 2 BPM")):
        raise CandidateError("TXT_ROUND_TRIP_MISMATCH")
    guidance = {"purpose_text": "\n".join(lines[5:8]), "purpose_ref": "L19-TXT1-6-8",
                "sequence_text": "\n".join(lines[10:16]), "sequence_ref": "L19-TXT1-11-16",
                "cell_design_text": "\n".join(lines[18:23]), "cell_design_ref": "L19-TXT1-19-23",
                "picking_text": "\n".join(lines[25:30]), "picking_ref": "L19-TXT1-26-30",
                "rhythm_text": "\n".join(lines[32:35]), "rhythm_ref": "L19-TXT1-33-35",
                "practice_text": "\n".join(lines[37:43]), "practice_ref": "L19-TXT1-38-43",
                "chromatic_route_text": "\n".join(lines[45:48]), "chromatic_route_ref": "L19-TXT1-46-48",
                "route_map_rows": map_rows, "route_map_ref": "L19-TXT1-51-65",
                "round_trip_text": round_trip, "round_trip_ref": "L19-TXT1-437-443",
                "clean_standard_text": "\n".join(lines[444:450]), "clean_standard_ref": "L19-TXT1-445-450",
                "pdf_ref": "L19-PDF1-p1-p2-p9-p10"}
    if not all(phrase in guidance["rhythm_text"] for phrase in ("eighth-note triplets", "sixteenth-note triplets", "sextuplets")):
        raise CandidateError("TXT_RHYTHM_GUIDANCE_MISMATCH")
    return rungs, guidance


def _pdf_rungs(data: bytes) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    try:
        reader = PdfReader(BytesIO(data), strict=True)
        if len(reader.pages) != 10:
            raise CandidateError(f"PDF_PAGE_COUNT {len(reader.pages)}")
        pages = [(page.extract_text() or "").splitlines() for page in reader.pages]
    except CandidateError:
        raise
    except Exception as exc:
        raise CandidateError(f"PDF_READ_FAILED {type(exc).__name__}") from exc
    if not all(any(phrase in line for line in pages[0]) for phrase in ("22 triads. 66 notes", "major", "minor", "Page 1 of 10")):
        raise CandidateError("PDF_INTRO_GUIDANCE_MISMATCH")
    route_page = pages[1]
    if route_page[:10] != ["Level 19 - Chromatic Major-Key Route and Diatonic-Triad Map",
                           "Ascending route: complete one 66-note triad cell, then move the frame +1 fret",
                           "Descending route: use the same cards in reverse order and move -1 fret",
                           "Standard tuning. Two-octave sixth-string-root major scale. One completed cell = 66 notes.",
                           "Page 2 of 10", "Rung", "Key", "Low-E root", "Frame", "Diatonic triads (degrees 1-7)"]:
        raise CandidateError("PDF_ROUTE_MAP_HEADER_MISMATCH")
    for index, key in enumerate(KEYS):
        root = 5 + index
        chunk = route_page[10 + 5 * index:15 + 5 * index]
        expected = [f"{index+1:02d}", f"{key} major" + (" - octave" if index == 12 else ""), f"fret {root}",
                    f"{root-1}-{root+2}", " ".join(CHORDS7[index])]
        if chunk != expected:
            raise CandidateError(f"PDF_ROUTE_MAP_RUNG_MISMATCH {index+1}")
    tail = "\n".join(route_page[75:])
    if not all(phrase in tail for phrase in ("rungs 01-13", "rungs 12-01. Do not replay", "one triad per beat as triplets", "two triads per beat as", "HARMONY")):
        raise CandidateError("PDF_ROUTE_MAP_TAIL_MISMATCH")
    rungs = []
    for page_number in range(3, 10):
        lines = pages[page_number - 1]
        if page_number < 9:
            first_rung = 1 + 2 * (page_number - 3)
            if lines[:5] != ["Level 19 - Major Scale Diatonic Triads: Two Octaves",
                             f"Rungs {first_rung:02d}-{first_rung+1:02d}: play each card as one 22-triad cell, then move +1 fret",
                             "For the descending pass, read the cards in reverse order and move -1 fret",
                             "One triad per beat while learning; two triads per beat as sextuplets after the sequence is secure.",
                             f"Page {page_number} of 10"] or len(lines) != 59:
                raise CandidateError(f"PDF_RUNG_PAGE_SHAPE {page_number}")
            blocks = [lines[5:32], lines[32:59]]
        else:
            if lines[:5] != ["Level 19 - Final Rung and Full Round-Trip Challenge",
                             "Rung 13: complete the high-A triad cell at fret 17, then reverse the neck route",
                             "Do not replay rung 13 during the down pass unless beginning a new round",
                             "The complete A-to-A-to-A route contains 25 cells and 1,650 continuously picked notes.", "Page 9 of 10"]:
                raise CandidateError("PDF_FINAL_PAGE_SHAPE")
            blocks = [lines[5:32]]
            if not all(phrase in "\n".join(lines[32:]) for phrase in ("rungs 01-13", "rungs 12-01", "25 cells x 66 notes = 1,650")):
                raise CandidateError("PDF_FINAL_ROUND_TRIP_MISMATCH")
        for block in blocks:
            index = len(rungs)
            key, root = KEYS[index], 5 + index
            expected_head = [f"{index+1:02d}  {key} MAJOR" + (" - OCTAVE" if index == 12 else ""),
                             f"ROOT E{root}  |  FRAME {root-1}-{root+2}", "66 NOTES / 22 TRIADS",
                             "Scale: " + " ".join((*SCALE7[index], *SCALE7[index], key)),
                             "Triads: " + " | ".join(CHORDS7[index]), ASC_LABEL]
            if len(block) != 27 or block[:6] != expected_head or block[15] != DESC_LABEL or block[25:] != [PDF_CARD_FOOTER, PDF_PICKING]:
                raise CandidateError(f"PDF_RUNG_CARD_MISMATCH {index+1}")
            asc = _parse_half(block[6], block[7], block[8], block[9:15], root, "up", CHORDS7[index])
            desc = _parse_half(block[16], block[17], block[18], block[19:25], root, "down", CHORDS7[index])
            triads = asc + desc
            _validate_turn(triads, root)
            rungs.append({"rung": index+1, "key": key, "root_fret": root, "frame": [root-1, root+2],
                          "source_ref": f"L19-PDF1-p{page_number}", "printed": {"heading": block[0], "root_frame": block[1],
                          "cell_label": block[2], "scale_tones": block[3], "chord_names": block[4], "ascending_label": block[5],
                          "ascending_hrm": block[6], "ascending_deg": block[7], "ascending_fng": block[8],
                          "ascending_tab": block[9:15], "descending_label": block[15], "descending_hrm": block[16],
                          "descending_deg": block[17], "descending_fng": block[18], "descending_tab": block[19:25],
                          "footer": block[25], "picking": block[26]}, "triads": triads})
    if len(rungs) != 13:
        raise CandidateError(f"PDF_RUNG_COUNT {len(rungs)}")
    if not all(any(phrase in line for line in pages[9]) for phrase in ("Level 19 - Practice Architecture", "sextuplets", "Page 10 of 10")):
        raise CandidateError("PDF_PRACTICE_PAGE_MISMATCH")
    route = {"map_ref": "L19-PDF1-p2", "map_header": route_page[:10], "map_rows": route_page[10:75],
             "map_guidance": route_page[75:], "final_round_trip_ref": "L19-PDF1-p9",
             "final_round_trip_text": "\n".join(pages[8][32:44]), "practice_ref": "L19-PDF1-p10"}
    return rungs, route


def build_candidate(*, txt_data: bytes | None = None, pdf_data: bytes | None = None) -> dict[str, Any]:
    root = _root()
    txt_data = _source_bytes(root, TXT_REL) if txt_data is None else txt_data
    pdf_data = _source_bytes(root, PDF_REL) if pdf_data is None else pdf_data
    _verify(txt_data, TXT_BYTES, TXT_SHA256, "L19-TXT")
    _verify(pdf_data, PDF_BYTES, PDF_SHA256, "L19-PDF")
    txt_rungs, instructions = _txt_rungs(txt_data)
    pdf_rungs, pdf_route = _pdf_rungs(pdf_data)
    records = []
    for txt, pdf in zip(txt_rungs, pdf_rungs, strict=True):
        if (txt["rung"], txt["key"], txt["root_fret"], txt["frame"]) != (pdf["rung"], pdf["key"], pdf["root_fret"], pdf["frame"]):
            raise CandidateError(f"PDF_TXT_RUNG_MISMATCH {txt['rung']}")
        for field in ("ascending_hrm", "ascending_deg", "ascending_fng", "ascending_tab", "descending_hrm", "descending_deg", "descending_fng", "descending_tab"):
            if txt["printed"][field] != pdf["printed"][field]:
                raise CandidateError(f"PDF_TXT_ROW_MISMATCH {txt['rung']} {field}")
        if txt["triads"] != pdf["triads"]:
            raise CandidateError(f"PDF_TXT_TRIAD_MISMATCH {txt['rung']}")
        records.append({"source_local_key": f"L19-rung{txt['rung']:02d}", "rung": txt["rung"], "key": txt["key"],
                        "key_label": f"{txt['key']} major" + (" - octave" if txt["rung"] == 13 else ""),
                        "root_string": "E", "root_fret": txt["root_fret"], "frame": txt["frame"], "scale_tones": txt["scale_tones"],
                        "chord_names": txt["chord_names"], "source_refs": {"txt": txt["source_ref"],
                        "pdf_card": pdf["source_ref"], "pdf_map": "L19-PDF1-p2"},
                        "printed_txt": txt["printed"], "printed_pdf": pdf["printed"], "triads": txt["triads"],
                        "canonical_item_id": None, "canonical_variant_id": None, "onset_q": None, "duration_q": None,
                        "note_per_click": None, "fixed_bpm": None, "runtime_eligible": False, "runtime_admitted": False,
                        "imported": False, "admitted": False})
    up = list(range(1, 14))
    down = list(range(12, 0, -1))
    route = {"ascending_rungs": up, "descending_rungs_after_turn": down, "single_turn_cell_sequence": up + down,
             "single_turn_cell_count": 25, "notes_per_cell": 66, "single_turn_note_count": 1650,
             "turn_rung_played_once": 13, "up_fret_step": 1, "down_fret_step": -1,
             "txt_ref": "L19-TXT1-46-48,L19-TXT1-437-443", "pdf_ref": "L19-PDF1-p2,L19-PDF1-p9"}
    return {"schema": "fathom-level019-whole-detached-candidate-v1", "wbs_id": "2.3.1.1.1", "level": 19,
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
