#!/usr/bin/env python3
"""Build an unadmitted, source-reconciled whole-Level-23 minor rolling candidate."""

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
STEM = "Scale_Exercises_Section_III_Level_23_Natural_Minor_Three_Note_Rolling_Sequence_One_Octave_Neck_Ladder"
TXT_REL = Path(f"Notes/music/guitar project/TXT version/{STEM}.txt")
PDF_REL = Path(f"Notes/music/guitar project/PDF version/{STEM}.pdf")
TXT_BYTES = 24585
TXT_SHA256 = "c8c01c4a4ad95e1aed5323d485b359a1bd4d057f46fd2b3ffe8277324b0032f7"
PDF_BYTES = 21472
PDF_SHA256 = "5601a14c406f3b33e455e96d4539ade22160ed0ac95aa782b36a2ef9d960dd43"
BUILD_REL = Path("Build/parallel-08/2.3.1.1.1-level023-whole-r01")
KEYS = ("A", "Bb", "B", "C", "C#", "D", "Eb", "E", "F", "F#", "G", "G#", "A")
SCALE_TONES = (
    ("A", "B", "C", "D", "E", "F", "G"), ("Bb", "C", "Db", "Eb", "F", "Gb", "Ab"),
    ("B", "C#", "D", "E", "F#", "G", "A"), ("C", "D", "Eb", "F", "G", "Ab", "Bb"),
    ("C#", "D#", "E", "F#", "G#", "A", "B"), ("D", "E", "F", "G", "A", "Bb", "C"),
    ("Eb", "F", "Gb", "Ab", "Bb", "Cb", "Db"), ("E", "F#", "G", "A", "B", "C", "D"),
    ("F", "G", "Ab", "Bb", "C", "Db", "Eb"), ("F#", "G#", "A", "B", "C#", "D", "E"),
    ("G", "A", "Bb", "C", "D", "Eb", "F"), ("G#", "A#", "B", "C#", "D#", "E", "F#"),
    ("A", "B", "C", "D", "E", "F", "G"),
)
DEGREES = ("1", "2", "b3", "4", "5", "b6", "b7", "8")
DEGREE_FINGERS = ("1", "3", "4", "1", "3", "4", "1", "3")
MINOR_OFFSETS = (0, 2, 3, 5, 7, 8, 10, 12)
DEGREE_GROUPS = tuple(tuple(range(start, start + 3)) for start in range(1, 7)) + tuple(tuple(range(start, start - 3, -1)) for start in range(8, 2, -1))
CROSSINGS = ("EEE", "EEA", "EAA", "AAA", "AAD", "ADD", "DDA", "DAA", "AAA", "AAE", "AEE", "EEE")
ROWS = ("e", "B", "G", "D", "A", "E")
OPEN_MIDI = {"E": 40, "A": 45, "D": 50, "G": 55, "B": 59, "e": 64}
TXT_CELL_LABEL = "36-note cell: six ascending rolling triplets, repeat the octave root at the turn, then six descending triplets."
TXT_RUNG_FOOTER = "Finish on the low root, release pressure, and move the entire frame one fret in the route direction."
PDF_CELL_LABEL = "36-NOTE / 12-TRIPLET CELL"
PDF_CARD_FOOTER = "Finish on the low root; release pressure; move the entire frame one fret."
PDF_FINAL_CARD_FOOTER = "Finish on the low root; reverse direction and continue with rung 12."
PDF_PICKING = "Continuous alternate picking - D-start and U-start"
PDF_PAGE_FOOTER = "Eighth-note triplets: one three-note group per beat. Keep early and late crossings inside the same pulse."
RUNG_HEADER = re.compile(r"^RUNG (\d{2}) OF 13 - (.+) NATURAL MINOR( - OCTAVE)? - ROOT ON LOW E FRET (\d+) - FRAME (\d+)-(\d+)$")


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
    if len(parts) != 14 or parts[0] != label or parts[-1] != "":
        raise CandidateError(f"ROW_SHAPE_INVALID {label}")
    groups = []
    for cell in parts[1:-1]:
        if len(cell) != 9:
            raise CandidateError(f"GROUP_WIDTH_INVALID {label}: {cell}")
        values = []
        for offset in (0, 3, 6):
            slot = cell[offset:offset + 3]
            token = slot.rstrip("-")
            if token and (re.fullmatch(r"(?:\d+|b[367])", token) is None or token + "-" * (3 - len(token)) != slot):
                raise CandidateError(f"SLOT_INVALID {label}: {slot}")
            if not token and slot != "---":
                raise CandidateError(f"SLOT_INVALID {label}: {slot}")
            values.append(token or None)
        groups.append(values)
    return groups


def _expected_place(degree: int, root: int) -> tuple[str, int]:
    shape = (("E", 0), ("E", 2), ("E", 3), ("A", 0), ("A", 2), ("A", 3), ("D", 0), ("D", 2))
    string, offset = shape[degree - 1]
    return string, root + offset


def _parse_rows(deg_row: str, fng_row: str, tab_rows: list[str], root: int) -> list[dict[str, Any]]:
    degrees = _groups(deg_row, "Deg")
    fingers = _groups(fng_row, "Fng")
    if len(tab_rows) != 6:
        raise CandidateError("TAB_ROW_COUNT")
    tab = {string: _groups(row, f"{string}  ") for string, row in zip(ROWS, tab_rows, strict=True)}
    groups_out = []
    notes_out = []
    for group_index, expected_degrees in enumerate(DEGREE_GROUPS):
        notes = []
        for slot_index, expected_degree in enumerate(expected_degrees):
            degree_token = degrees[group_index][slot_index]
            finger_token = fingers[group_index][slot_index]
            if degree_token != DEGREES[expected_degree - 1] or finger_token != DEGREE_FINGERS[expected_degree - 1]:
                raise CandidateError(f"DEG_FNG_SEQUENCE_MISMATCH group={group_index+1} slot={slot_index+1}")
            printed = [(string, token) for string in ROWS if (token := tab[string][group_index][slot_index]) is not None]
            if len(printed) != 1:
                raise CandidateError(f"TAB_NOTE_CARDINALITY group={group_index+1} slot={slot_index+1}: {len(printed)}")
            string, fret_token = printed[0]
            expected_string, expected_fret = _expected_place(expected_degree, root)
            if (string, int(fret_token)) != (expected_string, expected_fret):
                raise CandidateError(f"TAB_DEGREE_FRET_MISMATCH group={group_index+1} slot={slot_index+1}")
            if OPEN_MIDI[string] + int(fret_token) != 40 + root + MINOR_OFFSETS[expected_degree - 1]:
                raise CandidateError(f"TAB_PITCH_MISMATCH group={group_index+1} slot={slot_index+1}")
            ordinal = group_index * 3 + slot_index + 1
            note = {"ordinal": ordinal, "group": group_index + 1, "slot": slot_index + 1,
                    "half": "up" if group_index < 6 else "down", "degree_position": expected_degree,
                    "degree_label": degree_token, "finger_digit": finger_token, "string": string, "fret": int(fret_token),
                    "is_octave_turn_root": ordinal in (18, 19), "onset_q": None, "duration_q": None}
            notes.append(note)
            notes_out.append(note)
        crossing = "".join(note["string"] for note in notes)
        if crossing != CROSSINGS[group_index]:
            raise CandidateError(f"CROSSING_MAP_MISMATCH group={group_index+1}")
        groups_out.append({"index": group_index + 1, "half": "up" if group_index < 6 else "down",
                           "string_pattern": crossing, "notes": notes})
    if len(groups_out) != 12 or len(notes_out) != 36 or [note["ordinal"] for note in notes_out] != list(range(1, 37)):
        raise CandidateError("CELL_COUNT_OR_ORDER_MISMATCH")
    if notes_out[17]["degree_label"] != "8" or notes_out[18]["degree_label"] != "8" or (notes_out[17]["string"], notes_out[17]["fret"]) != (notes_out[18]["string"], notes_out[18]["fret"]):
        raise CandidateError("OCTAVE_TURN_ROOT_MISMATCH")
    return groups_out


def _txt_rungs(data: bytes) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    try:
        lines = data.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise CandidateError("TXT_ENCODING_INVALID") from exc
    if len(lines) != 275 or lines[:2] != ["SCALE EXERCISES - SECTION III, LEVEL 23", "NATURAL MINOR THREE-NOTE ROLLING SEQUENCE - ONE-OCTAVE NECK LADDER: A TO A"]:
        raise CandidateError("TXT_HEADER_OR_EOF_MISMATCH")
    route_up = "UP:   " + " > ".join(f"{key}({5+i})" for i, key in enumerate(KEYS))
    route_down = "DOWN: " + " > ".join(f"{KEYS[i]}({5+i})" for i in range(12, -1, -1))
    if lines[49:51] != [route_up, route_down]:
        raise CandidateError("TXT_NECK_ROUTE_MISMATCH")
    seq_up = "UP:   " + " | ".join("-".join(DEGREES[d-1] for d in group) for group in DEGREE_GROUPS[:6])
    seq_down = "DOWN: " + " | ".join("-".join(DEGREES[d-1] for d in group) for group in DEGREE_GROUPS[6:])
    if lines[30:32] != [seq_up, seq_down]:
        raise CandidateError("TXT_SEQUENCE_RULE_MISMATCH")
    if lines[36:38] != ["UP:   " + " | ".join(CROSSINGS[:6]), "DOWN: " + " | ".join(CROSSINGS[6:])]:
        raise CandidateError("TXT_CROSSING_MAP_MISMATCH")
    rungs = []
    for index, key in enumerate(KEYS):
        start = 61 + 14 * index
        block = lines[start:start + 12]
        root = 5 + index
        if len(block) != 12 or lines[start - 1] != "=" * 132 or lines[start + 12] != "":
            raise CandidateError(f"TXT_RUNG_BOUNDARY {index+1}")
        match = RUNG_HEADER.fullmatch(block[0])
        if match is None or (match.group(1), match.group(2), bool(match.group(3)), int(match.group(4)), int(match.group(5)), int(match.group(6))) != (f"{index+1:02d}", key.upper(), index == 12, root, root, root + 3):
            raise CandidateError(f"TXT_RUNG_HEADER_MISMATCH {index+1}")
        tones = [*SCALE_TONES[index], key]
        if block[1] != "Scale tones: " + " ".join(tones) or block[2] != TXT_CELL_LABEL or block[11] != TXT_RUNG_FOOTER:
            raise CandidateError(f"TXT_RUNG_TONES_OR_GUIDANCE_MISMATCH {index+1}")
        groups = _parse_rows(block[3], block[4], block[5:11], root)
        rungs.append({"rung": index + 1, "key": key, "root_fret": root, "frame": [root, root + 3],
                      "scale_tones": tones, "source_ref": f"L23-TXT1-{start+1}-{start+12}",
                      "printed": {"heading": block[0], "scale_tones": block[1], "cell_label": block[2],
                                  "deg_row": block[3], "fng_row": block[4], "tab_rows": block[5:11], "footer": block[11]},
                      "groups": groups})
    if lines[242:244] != ["=" * 132, "FULL ROUND-TRIP CHALLENGE"]:
        raise CandidateError("TXT_RUNG_END_BOUNDARY_MISMATCH")
    round_trip = "\n".join(lines[243:250])
    if any(phrase not in round_trip for phrase in ("all 13 cells", "rungs 12-01", "25 cells x 36 notes = 900")):
        raise CandidateError("TXT_ROUND_TRIP_RULE_MISMATCH")
    ranges = {"purpose": (5, 8), "why_one_octave": (11, 13), "interpretation": (16, 17),
              "formula": (20, 21), "shape": (24, 28), "sequence": (31, 34), "crossing": (37, 39),
              "cell_picking": (42, 47), "neck_route": (50, 51), "practice": (54, 59),
              "round_trip": (244, 250), "clean_standard": (253, 255), "variations": (258, 264), "mastery": (267, 269)}
    guidance = {name: {"text": "\n".join(lines[first-1:last]), "ref": f"L23-TXT1-{first}-{last}"}
                for name, (first, last) in ranges.items()}
    if any(phrase not in guidance["practice"]["text"] for phrase in ("eighth-note triplets", "12-18 BPM below", "one beat after each 36-note cell", "both pick starts", "two separate days")):
        raise CandidateError("TXT_PRACTICE_RULE_MISMATCH")
    guidance["pdf_instruction_refs"] = ["L23-PDF1-p1", "L23-PDF1-p2", "L23-PDF1-p7"]
    return rungs, guidance


def _pdf_rungs(data: bytes) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    try:
        reader = PdfReader(BytesIO(data), strict=True)
        if len(reader.pages) != 7:
            raise CandidateError(f"PDF_PAGE_COUNT {len(reader.pages)}")
        pages = [(page.extract_text() or "").splitlines() for page in reader.pages]
    except CandidateError:
        raise
    except Exception as exc:
        raise CandidateError(f"PDF_READ_FAILED {type(exc).__name__}") from exc
    first, route_page = pages[0], pages[1]
    if len(first) != 57 or first[-1] != "Page 1 of 7" or any(phrase not in "\n".join(first) for phrase in ("Three notes forward", "octave root is repeated", "12-18 BPM below")):
        raise CandidateError("PDF_FIRST_PAGE_MISMATCH")
    if len(route_page) != 109 or route_page[:8] != ["Level 23 - Chromatic Natural-Minor Route and Sequence Map",
                                                     "Ascending route: complete one 36-note rolling cell, then move the frame +1 fret",
                                                     "Descending route: use the same cards in reverse order and move -1 fret",
                                                     "Rung", "Key", "Low-E root", "Frame", "Scale tones (degrees 1-b7)"]:
        raise CandidateError("PDF_ROUTE_MAP_HEADER_MISMATCH")
    for index, key in enumerate(KEYS):
        root = 5 + index
        chunk = route_page[8 + 5 * index:13 + 5 * index]
        expected = [f"{index+1:02d}", f"{key} natural minor" + (" - octave" if index == 12 else ""),
                    f"fret {root}", f"{root}-{root+3}", " ".join(SCALE_TONES[index])]
        if chunk != expected:
            raise CandidateError(f"PDF_ROUTE_MAP_RUNG_MISMATCH {index+1}")
    if any(phrase not in "\n".join(route_page[73:]) for phrase in ("rungs 01-13", "rungs 12-01", "25 cells x 36 notes = 900", "Page 2 of 7")):
        raise CandidateError("PDF_ROUTE_MAP_TAIL_MISMATCH")
    rungs = []
    for page_number in range(3, 8):
        lines = pages[page_number - 1]
        if page_number < 7:
            first_rung = 1 + 3 * (page_number - 3)
            expected_head = ["Level 23 - Natural Minor Three-Note Rolling Sequence",
                             f"Rungs {first_rung:02d}-{first_rung+2:02d}: play each card as one 12-triplet cell, then move +1 fret",
                             "For the descending pass, read the cards in reverse order and move -1 fret"]
            if len(lines) != 47 or lines[:3] != expected_head or lines[-2:] != [PDF_PAGE_FOOTER, f"Page {page_number} of 7"]:
                raise CandidateError(f"PDF_RUNG_PAGE_SHAPE {page_number}")
            blocks = [lines[3 + 14 * j:3 + 14 * (j + 1)] for j in range(3)]
        else:
            if len(lines) != 41 or lines[:2] != ["Level 23 - Final Rung and Mastery Work",
                                                   "Rung 13: complete the octave A-minor cell, then reverse the neck route"] or lines[-1] != "Page 7 of 7":
                raise CandidateError("PDF_FINAL_RUNG_PAGE_SHAPE")
            if any(phrase not in "\n".join(lines[16:]) for phrase in ("rungs 01-13", "return through 12-01", "25 cells x 36 notes = 900", "two clean days")):
                raise CandidateError("PDF_ROUND_TRIP_GUIDANCE_MISMATCH")
            blocks = [lines[2:16]]
        for block in blocks:
            index = len(rungs)
            key, root = KEYS[index], 5 + index
            expected_heading = f"{index+1:02d}  {key.upper()} NATURAL MINOR" + (" - OCTAVE" if index == 12 else "")
            footer = PDF_FINAL_CARD_FOOTER if index == 12 else PDF_CARD_FOOTER
            if len(block) != 14 or block[:4] != [expected_heading, f"ROOT E{root}  |  FRAME {root}-{root+3}",
                                                   PDF_CELL_LABEL, "Scale tones: " + " ".join((*SCALE_TONES[index], key))] or block[12:] != [footer, PDF_PICKING]:
                raise CandidateError(f"PDF_RUNG_CARD_MISMATCH {index+1}")
            groups = _parse_rows(block[4], block[5], block[6:12], root)
            rungs.append({"rung": index + 1, "key": key, "root_fret": root, "frame": [root, root + 3],
                          "scale_tones": [*SCALE_TONES[index], key], "source_ref": f"L23-PDF1-p{page_number}",
                          "printed": {"heading": block[0], "root_frame": block[1], "cell_label": block[2],
                                      "scale_tones": block[3], "deg_row": block[4], "fng_row": block[5],
                                      "tab_rows": block[6:12], "footer": block[12], "picking": block[13]},
                          "groups": groups})
    if len(rungs) != 13:
        raise CandidateError(f"PDF_RUNG_COUNT {len(rungs)}")
    first_card = rungs[0]["printed"]
    if first[22:30] != [first_card["deg_row"], first_card["fng_row"], *first_card["tab_rows"]]:
        raise CandidateError("PDF_FIRST_PAGE_WORKED_EXAMPLE_MISMATCH")
    return rungs, {"first_page_ref": "L23-PDF1-p1", "first_page_guidance": first[:22] + first[30:56],
                   "map_ref": "L23-PDF1-p2", "map_rows": route_page[8:73], "map_guidance": route_page[73:108],
                   "final_page_ref": "L23-PDF1-p7", "final_page_guidance": pages[6][16:40]}


def build_candidate(*, txt_data: bytes | None = None, pdf_data: bytes | None = None) -> dict[str, Any]:
    root = _root()
    txt_data = _source_bytes(root, TXT_REL) if txt_data is None else txt_data
    pdf_data = _source_bytes(root, PDF_REL) if pdf_data is None else pdf_data
    _verify(txt_data, TXT_BYTES, TXT_SHA256, "L23-TXT")
    _verify(pdf_data, PDF_BYTES, PDF_SHA256, "L23-PDF")
    txt_rungs, instructions = _txt_rungs(txt_data)
    pdf_rungs, pdf_context = _pdf_rungs(pdf_data)
    records = []
    for txt, pdf in zip(txt_rungs, pdf_rungs, strict=True):
        if (txt["rung"], txt["key"], txt["root_fret"], txt["frame"], txt["scale_tones"]) != (pdf["rung"], pdf["key"], pdf["root_fret"], pdf["frame"], pdf["scale_tones"]):
            raise CandidateError(f"PDF_TXT_RUNG_MISMATCH {txt['rung']}")
        for field in ("deg_row", "fng_row", "tab_rows"):
            if txt["printed"][field] != pdf["printed"][field]:
                raise CandidateError(f"PDF_TXT_ROW_MISMATCH {txt['rung']} {field}")
        if txt["groups"] != pdf["groups"]:
            raise CandidateError(f"PDF_TXT_EVENT_MISMATCH {txt['rung']}")
        records.append({"source_local_key": f"L23-rung{txt['rung']:02d}", "rung": txt["rung"], "key": txt["key"],
                        "key_label": f"{txt['key']} natural minor" + (" (octave)" if txt["rung"] == 13 else ""),
                        "root_string": "E", "root_fret": txt["root_fret"], "frame": txt["frame"],
                        "scale_tones": txt["scale_tones"], "group_count": 12, "note_count": 36,
                        "source_refs": {"txt": txt["source_ref"], "pdf_card": pdf["source_ref"], "pdf_map": "L23-PDF1-p2"},
                        "printed_txt": txt["printed"], "printed_pdf": pdf["printed"], "groups": txt["groups"],
                        "canonical_item_id": None, "canonical_variant_id": None, "onset_q": None, "duration_q": None,
                        "note_per_click": None, "fixed_bpm": None, "runtime_eligible": False, "runtime_admitted": False,
                        "imported": False, "admitted": False})
    up = list(range(1, 14))
    down = list(range(12, 0, -1))
    route = {"ascending_landmarks": [{"rung": n, "key": KEYS[n-1], "root_fret": n+4} for n in up],
             "descending_landmarks": [{"rung": n, "key": KEYS[n-1], "root_fret": n+4} for n in range(13, 0, -1)],
             "single_turn_cell_sequence": up + down, "single_turn_cell_count": 25, "single_turn_note_count": 900,
             "turn_rung_played_once": 13, "up_fret_step": 1, "down_fret_step": -1,
             "txt_ref": "L23-TXT1-50-51,L23-TXT1-244-250", "pdf_ref": "L23-PDF1-p2,L23-PDF1-p7",
             "interpretation": "The DOWN listing includes A(17); a continuous round trip plays its cell once, then returns through rungs 12-01."}
    return {"schema": "fathom-level023-whole-detached-candidate-v1", "wbs_id": "2.3.1.1.1", "level": 23,
            "source": {"txt_path": TXT_REL.as_posix(), "txt_bytes": TXT_BYTES, "txt_sha256": TXT_SHA256, "txt_lines": 275,
                       "pdf_path": PDF_REL.as_posix(), "pdf_bytes": PDF_BYTES, "pdf_sha256": PDF_SHA256, "pdf_pages": 7,
                       "selected_pdf_card_pages": list(range(3, 8))},
            "instructions": instructions, "pdf_context": pdf_context, "neck_route": route, "records": records,
            "exceptions": [], "whole_workbook_source_covered": True, "whole_workbook_complete": False,
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
