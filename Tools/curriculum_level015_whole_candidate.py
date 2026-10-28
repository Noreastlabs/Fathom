#!/usr/bin/env python3
"""Build an unadmitted, source-reconciled whole-Level-15 rolling-scale candidate."""

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
STEM = "Scale_Exercises_Section_II_Level_15_Major_Scale_Three_Note_Rolling_Sequence_Two_Octave_Six_String_Neck_Ladder"
TXT_REL = Path(f"Notes/music/guitar project/TXT version/{STEM}.txt")
PDF_REL = Path(f"Notes/music/guitar project/PDF version/{STEM}.pdf")
TXT_BYTES = 42020
TXT_SHA256 = "896937c0d5040c8e7590364433e141bbe7f6da419e063a8ed2590666d5a2c514"
PDF_BYTES = 30825
PDF_SHA256 = "9c3e2b980079fb3a4eca7affe9bc948a2e58cab15f256766976451ac08d53a5e"
BUILD_REL = Path("Build/parallel-08/2.3.1.1.1-level015-whole-r01")
KEYS = ("A", "Bb", "B", "C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A")
SCALE_TONES = (
    ("A", "B", "C#", "D", "E", "F#", "G#"), ("Bb", "C", "D", "Eb", "F", "G", "A"),
    ("B", "C#", "D#", "E", "F#", "G#", "A#"), ("C", "D", "E", "F", "G", "A", "B"),
    ("Db", "Eb", "F", "Gb", "Ab", "Bb", "C"), ("D", "E", "F#", "G", "A", "B", "C#"),
    ("Eb", "F", "G", "Ab", "Bb", "C", "D"), ("E", "F#", "G#", "A", "B", "C#", "D#"),
    ("F", "G", "A", "Bb", "C", "D", "E"), ("Gb", "Ab", "Bb", "Cb", "Db", "Eb", "F"),
    ("G", "A", "B", "C", "D", "E", "F#"), ("Ab", "Bb", "C", "Db", "Eb", "F", "G"),
    ("A", "B", "C#", "D", "E", "F#", "G#"),
)
ROWS = ("e", "B", "G", "D", "A", "E")
OPEN_MIDI = {"E": 40, "A": 45, "D": 50, "G": 55, "B": 59, "e": 64}
MAJOR_OFFSETS = (0, 2, 4, 5, 7, 9, 11, 12, 14, 16, 17, 19, 21, 23, 24)
DEGREE_FINGERS = ("2", "4", "1", "2", "4", "1", "3", "4", "1", "3", "4", "2", "4", "1", "2")
DEGREE_GROUPS = tuple(tuple(range(start, start + 3)) for start in range(1, 14)) + tuple(tuple(range(start, start - 3, -1)) for start in range(15, 2, -1))
RUNG_FOOTER = "Finish on the low root, release pressure, and move the entire frame one fret in the route direction."
TXT_CELL_LABEL = "78-note cell: 13 ascending rolling triplets, repeat the high root at the turn, then 13 descending triplets."
PDF_CELL_LABEL = "78 NOTES / 26 TRIPLETS"
PDF_CARD_FOOTER = "Return to the low root; release pressure; move the entire frame one fret."
PDF_PICKING = "Continuous alternate picking - D-start and U-start"
PDF_PAGE_FOOTER = "Eighth-note triplets: one three-note group per beat. Never restart alternate picking at a group boundary."
ASC_LABEL = "ASCENDING - 13 TRIPLETS / 39 NOTES"
DESC_LABEL = "DESCENDING - 13 TRIPLETS / 39 NOTES"
RUNG_HEADER = re.compile(r"^RUNG (\d{2}) OF 13 - (.+) MAJOR( \(OCTAVE\))? - ROOT ON LOW E FRET (\d+) - FRAME (\d+)-(\d+)$")


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


def _groups(row: str, label: str) -> list[list[str | None]]:
    parts = row.split("|")
    if len(parts) != 15 or parts[0] != label or parts[-1] != "":
        raise CandidateError(f"ROW_SHAPE_INVALID {label}")
    groups = []
    for cell in parts[1:-1]:
        if len(cell) != 9:
            raise CandidateError(f"GROUP_WIDTH_INVALID {label}: {cell}")
        values = []
        for offset in (0, 3, 6):
            slot = cell[offset:offset + 3]
            token = slot.rstrip("-")
            if token and (not token.isdigit() or token + "-" * (3 - len(token)) != slot):
                raise CandidateError(f"SLOT_INVALID {label}: {slot}")
            if not token and slot != "---":
                raise CandidateError(f"SLOT_INVALID {label}: {slot}")
            values.append(token or None)
        groups.append(values)
    return groups


def _expected_place(degree: int, root: int) -> tuple[str, int]:
    shape = (
        ("E", 0), ("E", 2), ("A", -1), ("A", 0), ("A", 2),
        ("D", -1), ("D", 1), ("D", 2), ("G", -1), ("G", 1),
        ("G", 2), ("B", 0), ("B", 2), ("e", -1), ("e", 0),
    )
    string, offset = shape[degree - 1]
    return string, root + offset


def _parse_half(deg_row: str, fng_row: str, tab_rows: list[str], root: int, half: str) -> list[dict[str, Any]]:
    degrees = _groups(deg_row, "Deg")
    fingers = _groups(fng_row, "Fng")
    if len(tab_rows) != 6:
        raise CandidateError("TAB_ROW_COUNT")
    tab = {string: _groups(row, f"{string}  ") for string, row in zip(ROWS, tab_rows, strict=True)}
    groups_out = []
    start_group = 0 if half == "up" else 13
    for local_index, expected_degrees in enumerate(DEGREE_GROUPS[start_group:start_group + 13]):
        group_index = start_group + local_index
        notes = []
        for slot_index, expected_degree in enumerate(expected_degrees):
            degree_token = degrees[local_index][slot_index]
            finger_token = fingers[local_index][slot_index]
            if degree_token != str(expected_degree) or finger_token != DEGREE_FINGERS[expected_degree - 1]:
                raise CandidateError(f"DEG_FNG_SEQUENCE_MISMATCH group={group_index+1} slot={slot_index+1}")
            printed = [(string, token) for string in ROWS if (token := tab[string][local_index][slot_index]) is not None]
            if len(printed) != 1:
                raise CandidateError(f"TAB_NOTE_CARDINALITY group={group_index+1} slot={slot_index+1}: {len(printed)}")
            string, fret_token = printed[0]
            expected_string, expected_fret = _expected_place(expected_degree, root)
            if (string, int(fret_token)) != (expected_string, expected_fret):
                raise CandidateError(f"TAB_DEGREE_FRET_MISMATCH group={group_index+1} slot={slot_index+1}")
            if OPEN_MIDI[string] + int(fret_token) != 40 + root + MAJOR_OFFSETS[expected_degree - 1]:
                raise CandidateError(f"TAB_PITCH_MISMATCH group={group_index+1} slot={slot_index+1}")
            ordinal = group_index * 3 + slot_index + 1
            notes.append({"ordinal": ordinal, "group": group_index + 1, "slot": slot_index + 1, "half": half,
                          "degree": expected_degree, "finger_digit": finger_token, "string": string, "fret": int(fret_token),
                          "is_middle_octave_root": expected_degree == 8,
                          "is_high_root_turn": ordinal in (39, 40), "onset_q": None, "duration_q": None})
        groups_out.append({"index": group_index + 1, "half": half, "notes": notes})
    return groups_out


def _parse_card_rows(asc_deg: str, asc_fng: str, asc_tab: list[str], desc_deg: str, desc_fng: str,
                     desc_tab: list[str], root: int) -> list[dict[str, Any]]:
    groups = _parse_half(asc_deg, asc_fng, asc_tab, root, "up") + _parse_half(desc_deg, desc_fng, desc_tab, root, "down")
    notes = [note for group in groups for note in group["notes"]]
    if len(groups) != 26 or len(notes) != 78 or [note["ordinal"] for note in notes] != list(range(1, 79)):
        raise CandidateError("CELL_COUNT_OR_ORDER_MISMATCH")
    if notes[38]["degree"] != 15 or notes[39]["degree"] != 15 or (notes[38]["string"], notes[38]["fret"]) != (notes[39]["string"], notes[39]["fret"]):
        raise CandidateError("HIGH_ROOT_TURN_MISMATCH")
    return groups


def _txt_rungs(data: bytes) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    try:
        lines = data.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise CandidateError("TXT_ENCODING_INVALID") from exc
    if len(lines) != 410 or lines[:2] != ["SCALE EXERCISES - SECTION II, LEVEL 15", "MAJOR SCALE THREE-NOTE ROLLING SEQUENCE - TWO-OCTAVE SIX-STRING NECK LADDER: A TO A"]:
        raise CandidateError("TXT_HEADER_OR_EOF_MISMATCH")
    route_up = "UP:   " + " > ".join(f"{key}({5+i})" for i, key in enumerate(KEYS))
    route_down = "DOWN: " + " > ".join(f"{KEYS[i]}({5+i})" for i in range(12, -1, -1))
    if lines[55:57] != [route_up, route_down]:
        raise CandidateError("TXT_NECK_ROUTE_MISMATCH")
    seq_up = "UP:   " + " | ".join("-".join(map(str, group)) for group in DEGREE_GROUPS[:13])
    seq_down = "DOWN: " + " | ".join("-".join(map(str, group)) for group in DEGREE_GROUPS[13:])
    if lines[34:36] != [seq_up, seq_down]:
        raise CandidateError("TXT_SEQUENCE_RULE_MISMATCH")
    rungs = []
    for index, key in enumerate(KEYS):
        start = 69 + 24 * index
        block = lines[start:start + 22]
        root = 5 + index
        if len(block) != 22 or lines[start - 1] != "=" * 150 or lines[start + 22] != "":
            raise CandidateError(f"TXT_RUNG_BOUNDARY {index+1}")
        match = RUNG_HEADER.fullmatch(block[0])
        if match is None or (match.group(1), match.group(2), bool(match.group(3)), int(match.group(4)), int(match.group(5)), int(match.group(6))) != (f"{index+1:02d}", key, index == 12, root, root - 1, root + 2):
            raise CandidateError(f"TXT_RUNG_HEADER_MISMATCH {index+1}")
        expected_tones = [*SCALE_TONES[index], *SCALE_TONES[index], key]
        if block[1] != "Scale tones across two octaves: " + " ".join(expected_tones) or block[2] != TXT_CELL_LABEL:
            raise CandidateError(f"TXT_RUNG_TONES_OR_CELL_MISMATCH {index+1}")
        if block[3] != ASC_LABEL or block[12] != DESC_LABEL or block[21] != RUNG_FOOTER:
            raise CandidateError(f"TXT_RUNG_GUIDANCE_MISMATCH {index+1}")
        printed = {"heading": block[0], "scale_tones": block[1], "cell_label": block[2],
                   "ascending": {"label": block[3], "deg_row": block[4], "fng_row": block[5], "tab_rows": block[6:12]},
                   "descending": {"label": block[12], "deg_row": block[13], "fng_row": block[14], "tab_rows": block[15:21]},
                   "footer": block[21]}
        groups = _parse_card_rows(block[4], block[5], block[6:12], block[13], block[14], block[15:21], root)
        rungs.append({"rung": index + 1, "key": key, "root_fret": root, "frame": [root - 1, root + 2],
                      "scale_tones": expected_tones, "source_ref": f"L15-TXT1-{start+1}-{start+22}",
                      "printed": printed, "groups": groups})
    if lines[380:382] != ["=" * 150, "FULL ROUND-TRIP CHALLENGE"]:
        raise CandidateError("TXT_RUNG_END_BOUNDARY_MISMATCH")
    round_trip = "\n".join(lines[381:385])
    if any(phrase not in round_trip for phrase in ("rungs 01-13", "rungs 12-01", "fret-17 A-major cell")):
        raise CandidateError("TXT_ROUND_TRIP_RULE_MISMATCH")
    ranges = {"purpose": (5, 8), "change_from_level14": (11, 14), "interpretation": (17, 18),
              "formula": (21, 23), "shape": (26, 32), "sequence": (35, 39), "cell_picking": (42, 47),
              "crossing": (50, 53), "neck_route": (56, 57), "practice": (60, 67), "round_trip": (382, 385),
              "clean_standard": (388, 390), "variations": (393, 399), "mastery": (402, 404)}
    guidance = {name: {"text": "\n".join(lines[first-1:last]), "ref": f"L15-TXT1-{first}-{last}"}
                for name, (first, last) in ranges.items()}
    if any(phrase not in guidance["practice"]["text"] for phrase in ("eighth-note triplets", "15-20 BPM below", "two high-root notes", "Add 2 BPM", "both pick starts on two separate days")):
        raise CandidateError("TXT_PRACTICE_RULE_MISMATCH")
    guidance["pdf_instruction_refs"] = ["L15-PDF1-p1", "L15-PDF1-p2", "L15-PDF1-p9", "L15-PDF1-p10"]
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
    first, route_page, final = pages[0], pages[1], pages[9]
    if len(first) != 64 or first[-1] != "Page 1 of 10" or any(phrase not in "\n".join(first) for phrase in ("26 triplets", "High root repeats at the turn", "15-20 BPM below", "Page 1 of 10")):
        raise CandidateError("PDF_FIRST_PAGE_MISMATCH")
    if route_page[:8] != ["Level 15 - Chromatic Major-Key Route and Two-Octave Sequence Map",
                          "Ascending route: complete one 78-note rolling cell, then move the frame +1 fret",
                          "Descending route: use the same cards in reverse order and move -1 fret", "Rung", "Key", "Low-E root", "Frame", "Scale tones (degrees 1-7)"] or len(route_page) != 104:
        raise CandidateError("PDF_ROUTE_MAP_HEADER_MISMATCH")
    for index, key in enumerate(KEYS):
        root = 5 + index
        chunk = route_page[8 + 5 * index:13 + 5 * index]
        expected = [f"{index+1:02d}", f"{key} major" + (" (octave)" if index == 12 else ""), f"fret {root}", f"{root-1}-{root+2}", " ".join(SCALE_TONES[index])]
        if chunk != expected:
            raise CandidateError(f"PDF_ROUTE_MAP_RUNG_MISMATCH {index+1}")
    if any(phrase not in "\n".join(route_page[73:]) for phrase in ("rungs 01-13", "rungs 12-01. Do not replay rung", "one group per beat", "Page 2 of 10")):
        raise CandidateError("PDF_ROUTE_MAP_TAIL_MISMATCH")
    if len(final) != 58 or final[-1] != "Page 10 of 10" or any(phrase not in "\n".join(final) for phrase in ("B-string offset", "two position-15 notes", "Move only after note 78", "both pick starts")):
        raise CandidateError("PDF_FINAL_GUIDANCE_MISMATCH")
    rungs = []
    for page_number in range(3, 10):
        lines = pages[page_number - 1]
        if page_number < 9:
            first_rung = 1 + 2 * (page_number - 3)
            expected_head = ["Level 15 - Major Scale Three-Note Rolling Sequence: Two Octaves",
                             f"Rungs {first_rung:02d}-{first_rung+1:02d}: play each card as one 26-triplet cell, then move +1 fret",
                             "For the descending pass, read the cards in reverse order and move -1 fret"]
            if len(lines) != 53 or lines[:3] != expected_head or lines[-2:] != [PDF_PAGE_FOOTER, f"Page {page_number} of 10"]:
                raise CandidateError(f"PDF_RUNG_PAGE_SHAPE {page_number}")
            blocks = [lines[3:27], lines[27:51]]
        else:
            if len(lines) != 46 or lines[:3] != ["Level 15 - Final Rung and Full Round-Trip Challenge",
                                                   "Rung 13: complete the high-A cell at fret 17, then reverse the neck route",
                                                   "Do not replay rung 13 during the down pass unless beginning a new round"] or lines[-1] != "Page 9 of 10":
                raise CandidateError("PDF_FINAL_RUNG_PAGE_SHAPE")
            if any(phrase not in "\n".join(lines[27:]) for phrase in ("rungs 01-13", "rungs 12-01", "25 cells", "1,950", "both high-root notes")):
                raise CandidateError("PDF_ROUND_TRIP_GUIDANCE_MISMATCH")
            blocks = [lines[3:27]]
        for block in blocks:
            index = len(rungs)
            key, root = KEYS[index], 5 + index
            expected_head = f"{index+1:02d}  {key} MAJOR" + (" - OCTAVE" if index == 12 else "")
            expected_tones = [*SCALE_TONES[index], *SCALE_TONES[index], key]
            if len(block) != 24 or block[:5] != [expected_head, f"ROOT E{root}  |  FRAME {root-1}-{root+2}",
                                                   "Scale tones: " + " ".join(expected_tones), PDF_CELL_LABEL, ASC_LABEL] or block[13] != DESC_LABEL or block[22:] != [PDF_CARD_FOOTER, PDF_PICKING]:
                raise CandidateError(f"PDF_RUNG_CARD_MISMATCH {index+1}")
            printed = {"heading": block[0], "root_frame": block[1], "scale_tones": block[2], "cell_label": block[3],
                       "ascending": {"label": block[4], "deg_row": block[5], "fng_row": block[6], "tab_rows": block[7:13]},
                       "descending": {"label": block[13], "deg_row": block[14], "fng_row": block[15], "tab_rows": block[16:22]},
                       "footer": block[22], "picking": block[23]}
            groups = _parse_card_rows(block[5], block[6], block[7:13], block[14], block[15], block[16:22], root)
            rungs.append({"rung": index + 1, "key": key, "root_fret": root, "frame": [root - 1, root + 2],
                          "scale_tones": expected_tones, "source_ref": f"L15-PDF1-p{page_number}",
                          "printed": printed, "groups": groups})
    if len(rungs) != 13:
        raise CandidateError(f"PDF_RUNG_COUNT {len(rungs)}")
    first_card = rungs[0]["printed"]
    for offset, half in ((16, "ascending"), (25, "descending")):
        printed_half = first_card[half]
        if first[offset:offset + 9] != [printed_half["label"], printed_half["deg_row"], printed_half["fng_row"], *printed_half["tab_rows"]]:
            raise CandidateError(f"PDF_FIRST_PAGE_WORKED_EXAMPLE_MISMATCH {half}")
    return rungs, {"map_ref": "L15-PDF1-p2", "map_rows": route_page[8:73], "map_guidance": route_page[73:103],
                   "first_page_ref": "L15-PDF1-p1", "first_page_guidance": first[:16] + first[34:63],
                   "round_trip_ref": "L15-PDF1-p9", "round_trip_guidance": pages[8][27:45],
                   "final_page_ref": "L15-PDF1-p10", "final_page_guidance": final[:52]}


def build_candidate(*, txt_data: bytes | None = None, pdf_data: bytes | None = None) -> dict[str, Any]:
    root = _root()
    txt_data = _source_bytes(root, TXT_REL) if txt_data is None else txt_data
    pdf_data = _source_bytes(root, PDF_REL) if pdf_data is None else pdf_data
    _verify(txt_data, TXT_BYTES, TXT_SHA256, "L15-TXT")
    _verify(pdf_data, PDF_BYTES, PDF_SHA256, "L15-PDF")
    txt_rungs, instructions = _txt_rungs(txt_data)
    pdf_rungs, pdf_context = _pdf_rungs(pdf_data)
    records = []
    for txt, pdf in zip(txt_rungs, pdf_rungs, strict=True):
        if (txt["rung"], txt["key"], txt["root_fret"], txt["frame"], txt["scale_tones"]) != (pdf["rung"], pdf["key"], pdf["root_fret"], pdf["frame"], pdf["scale_tones"]):
            raise CandidateError(f"PDF_TXT_RUNG_MISMATCH {txt['rung']}")
        for half in ("ascending", "descending"):
            for field in ("label", "deg_row", "fng_row", "tab_rows"):
                if txt["printed"][half][field] != pdf["printed"][half][field]:
                    raise CandidateError(f"PDF_TXT_ROW_MISMATCH {txt['rung']} {half} {field}")
        if txt["groups"] != pdf["groups"]:
            raise CandidateError(f"PDF_TXT_EVENT_MISMATCH {txt['rung']}")
        records.append({"source_local_key": f"L15-rung{txt['rung']:02d}", "rung": txt["rung"],
                        "key": txt["key"], "key_label": f"{txt['key']} major" + (" (octave)" if txt["rung"] == 13 else ""),
                        "root_string": "E", "root_fret": txt["root_fret"], "frame": txt["frame"],
                        "scale_tones": txt["scale_tones"], "group_count": 26, "note_count": 78,
                        "source_refs": {"txt": txt["source_ref"], "pdf_card": pdf["source_ref"], "pdf_map": "L15-PDF1-p2"},
                        "printed_txt": txt["printed"], "printed_pdf": pdf["printed"], "groups": txt["groups"],
                        "canonical_item_id": None, "canonical_variant_id": None, "onset_q": None, "duration_q": None,
                        "note_per_click": None, "fixed_bpm": None, "runtime_eligible": False, "runtime_admitted": False,
                        "imported": False, "admitted": False})
    up = list(range(1, 14))
    down = list(range(12, 0, -1))
    route = {"ascending_landmarks": [{"rung": n, "key": KEYS[n-1], "root_fret": n+4} for n in up],
             "descending_landmarks": [{"rung": n, "key": KEYS[n-1], "root_fret": n+4} for n in range(13, 0, -1)],
             "single_turn_cell_sequence": up + down, "single_turn_cell_count": 25, "single_turn_note_count": 1950,
             "turn_rung_played_once": 13, "up_fret_step": 1, "down_fret_step": -1,
             "txt_ref": "L15-TXT1-56-57,L15-TXT1-382-385", "pdf_ref": "L15-PDF1-p2,L15-PDF1-p9",
             "interpretation": "The 13-rung DOWN listing includes turn position A(17); a continuous round trip plays its cell once before returning through rungs 12-01."}
    return {"schema": "fathom-level015-whole-detached-candidate-v1", "wbs_id": "2.3.1.1.1", "level": 15,
            "source": {"txt_path": TXT_REL.as_posix(), "txt_bytes": TXT_BYTES, "txt_sha256": TXT_SHA256, "txt_lines": 410,
                       "pdf_path": PDF_REL.as_posix(), "pdf_bytes": PDF_BYTES, "pdf_sha256": PDF_SHA256, "pdf_pages": 10,
                       "selected_pdf_card_pages": list(range(3, 10))},
            "instructions": instructions, "pdf_context": pdf_context, "neck_route": route, "records": records, "exceptions": [],
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
