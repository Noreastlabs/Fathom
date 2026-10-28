#!/usr/bin/env python3
"""Build a detached, source-linked whole-Level-14 rolling-scale candidate."""

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
TXT_REL = Path("Notes/music/guitar project/TXT version/Scale_Exercises_Section_II_Level_14_Major_Scale_Three_Note_Rolling_Sequence_One_Octave_Neck_Ladder.txt")
PDF_REL = Path("Notes/music/guitar project/PDF version/Scale_Exercises_Section_II_Level_14_Major_Scale_Three_Note_Rolling_Sequence_One_Octave_Neck_Ladder.pdf")
TXT_BYTES = 23537
TXT_SHA256 = "301edb98b64daa90a015a3560b8c2219cfab13984d6a8c320765af48f444912b"
PDF_BYTES = 21352
PDF_SHA256 = "c5ec5b0d1ed50c0c8af758a021f4488c886a1c6030c8a5a52cb755471ae7ed19"
BUILD_REL = Path("Build/parallel-09/2.3.1.1.1-level014-whole-r01")
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
DEGREE_FINGERS = ("2", "4", "1", "2", "4", "1", "3", "4")
DEGREE_GROUPS = tuple(tuple(range(start, start + 3)) for start in range(1, 7)) + tuple(tuple(range(start, start - 3, -1)) for start in range(8, 2, -1))
RUNG_FOOTER = "Finish on the low root, release pressure, and move the entire frame one fret in the route direction."
CELL_LABEL = "36-note cell: six ascending rolling triplets, repeat the octave root at the turn, then six descending triplets."
PDF_CELL_LABEL = "36-NOTE / 12-TRIPLET CELL"
PDF_CARD_FOOTER = "Return to the low root; release pressure; move the entire frame one fret."
PDF_PICKING = "Continuous alternate picking - D-start and U-start"
PDF_PAGE_FOOTER = "Eighth-note triplets: one three-note group per beat. Do not restart alternate picking at a group boundary."
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
            if token and (not token.isdigit() or token + "-" * (3 - len(token)) != slot):
                raise CandidateError(f"SLOT_INVALID {label}: {slot}")
            if not token and slot != "---":
                raise CandidateError(f"SLOT_INVALID {label}: {slot}")
            values.append(token or None)
        groups.append(values)
    return groups


def _expected_place(degree: int, root: int) -> tuple[str, int]:
    return {
        1: ("E", root), 2: ("E", root + 2), 3: ("A", root - 1), 4: ("A", root),
        5: ("A", root + 2), 6: ("D", root - 1), 7: ("D", root + 1), 8: ("D", root + 2),
    }[degree]


def _parse_rows(deg_row: str, fng_row: str, tab_rows: list[str], root: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    degrees = _groups(deg_row, "Deg")
    fingers = _groups(fng_row, "Fng")
    if len(tab_rows) != 6:
        raise CandidateError("TAB_ROW_COUNT")
    tab = {string: _groups(row, f"{string}  ") for string, row in zip(ROWS, tab_rows, strict=True)}
    if any(len(groups) != 12 for groups in (degrees, fingers, *tab.values())):
        raise CandidateError("GROUP_COUNT")
    groups_out = []
    notes_out = []
    for group_index, expected_degrees in enumerate(DEGREE_GROUPS):
        group_notes = []
        for slot_index, expected_degree in enumerate(expected_degrees):
            degree_token = degrees[group_index][slot_index]
            finger_token = fingers[group_index][slot_index]
            if degree_token != str(expected_degree) or finger_token != DEGREE_FINGERS[expected_degree - 1]:
                raise CandidateError(f"DEG_FNG_SEQUENCE_MISMATCH group={group_index+1} slot={slot_index+1}")
            printed = [(string, token) for string in ROWS if (token := tab[string][group_index][slot_index]) is not None]
            if len(printed) != 1:
                raise CandidateError(f"TAB_NOTE_CARDINALITY group={group_index+1} slot={slot_index+1}: {len(printed)}")
            string, fret_token = printed[0]
            expected_string, expected_fret = _expected_place(expected_degree, root)
            if (string, int(fret_token)) != (expected_string, expected_fret):
                raise CandidateError(f"TAB_DEGREE_FRET_MISMATCH group={group_index+1} slot={slot_index+1}")
            ordinal = group_index * 3 + slot_index + 1
            note = {"ordinal": ordinal, "group": group_index + 1, "slot": slot_index + 1, "half": "up" if group_index < 6 else "down",
                    "degree": expected_degree, "finger_digit": finger_token, "string": string, "fret": int(fret_token),
                    "is_octave_turn_root": ordinal in (18, 19), "onset_q": None, "duration_q": None}
            group_notes.append(note)
            notes_out.append(note)
        groups_out.append({"index": group_index + 1, "half": "up" if group_index < 6 else "down", "notes": group_notes})
    if notes_out[17]["degree"] != 8 or notes_out[18]["degree"] != 8 or (notes_out[17]["string"], notes_out[17]["fret"]) != (notes_out[18]["string"], notes_out[18]["fret"]):
        raise CandidateError("OCTAVE_TURN_ROOT_MISMATCH")
    return groups_out, notes_out


def _txt_rungs(data: bytes) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    try:
        lines = data.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise CandidateError("TXT_ENCODING_INVALID") from exc
    if lines[:2] != ["SCALE EXERCISES - SECTION II, LEVEL 14", "MAJOR SCALE THREE-NOTE ROLLING SEQUENCE - ONE-OCTAVE NECK LADDER: A TO A"]:
        raise CandidateError("TXT_HEADER_MISMATCH")
    if lines[236] != "====================================================================================================================================" or lines[237] != "FULL ROUND-TRIP CHALLENGE":
        raise CandidateError("TXT_RUNG_END_BOUNDARY_MISMATCH")
    up_route = lines[43]
    down_route = lines[44]
    if up_route != "UP:   A(5) > Bb(6) > B(7) > C(8) > Db(9) > D(10) > Eb(11) > E(12) > F(13) > Gb(14) > G(15) > Ab(16) > A(17)" or down_route != "DOWN: A(17) > Ab(16) > G(15) > Gb(14) > F(13) > E(12) > Eb(11) > D(10) > Db(9) > C(8) > B(7) > Bb(6) > A(5)":
        raise CandidateError("TXT_NECK_ROUTE_MISMATCH")
    if lines[29] != "UP:   1-2-3 | 2-3-4 | 3-4-5 | 4-5-6 | 5-6-7 | 6-7-8" or lines[30] != "DOWN: 8-7-6 | 7-6-5 | 6-5-4 | 5-4-3 | 4-3-2 | 3-2-1":
        raise CandidateError("TXT_SEQUENCE_RULE_MISMATCH")
    rungs = []
    for index, key in enumerate(KEYS):
        start = 55 + 14 * index
        block = lines[start:start + 12]
        if len(block) != 12 or lines[start - 1] != "=" * 132 or lines[start + 12] != "":
            raise CandidateError(f"TXT_RUNG_BOUNDARY {index+1}")
        match = RUNG_HEADER.fullmatch(block[0])
        root = 5 + index
        if match is None or (match.group(1), match.group(2), bool(match.group(3)), int(match.group(4)), int(match.group(5)), int(match.group(6))) != (f"{index+1:02d}", key.upper(), index == 12, root, root - 1, root + 2):
            raise CandidateError(f"TXT_RUNG_HEADER_MISMATCH {index+1}")
        tones = block[1].removeprefix("Scale tones: ").split()
        if block[1] != "Scale tones: " + " ".join((*SCALE_TONES[index], key)) or tones != [*SCALE_TONES[index], key]:
            raise CandidateError(f"TXT_SCALE_TONES_MISMATCH {index+1}")
        if block[2] != CELL_LABEL or block[11] != RUNG_FOOTER:
            raise CandidateError(f"TXT_RUNG_GUIDANCE_MISMATCH {index+1}")
        groups, notes = _parse_rows(block[3], block[4], block[5:11], root)
        rungs.append({"rung": index + 1, "key": key, "key_label": f"{key} major" + (" (octave)" if index == 12 else ""),
                      "root_fret": root, "frame": [root - 1, root + 2], "scale_tones": tones,
                      "source_ref": f"L14-TXT1-{start+1}-{start+12}", "printed": {"heading": block[0], "scale_tones": block[1],
                      "cell_label": block[2], "deg_row": block[3], "fng_row": block[4], "tab_rows": block[5:11], "footer": block[11]},
                      "groups": groups, "notes": notes})
    round_trip = "\n".join(lines[238:241])
    if not all(phrase in round_trip for phrase in ("rungs 01-13", "rungs 12-01", "fret-17 A-major cell")):
        raise CandidateError("TXT_ROUND_TRIP_RULE_MISMATCH")
    guidance = {"purpose_text": "\n".join(lines[4:8]), "purpose_ref": "L14-TXT1-5-8",
                "interpretation_text": "\n".join(lines[15:17]), "interpretation_ref": "L14-TXT1-16-17",
                "shape_text": "\n".join(lines[23:27]), "shape_ref": "L14-TXT1-24-27",
                "sequence_text": "\n".join(lines[29:33]), "sequence_ref": "L14-TXT1-30-33",
                "cell_picking_text": "\n".join(lines[35:41]), "cell_picking_ref": "L14-TXT1-36-41",
                "neck_route_text": up_route + "\n" + down_route, "neck_route_ref": "L14-TXT1-44-45",
                "practice_text": "\n".join(lines[47:53]), "practice_ref": "L14-TXT1-48-53",
                "round_trip_text": round_trip, "round_trip_ref": "L14-TXT1-239-241",
                "clean_standard_text": "\n".join(lines[243:246]), "clean_standard_ref": "L14-TXT1-244-246",
                "pdf_ref": "L14-PDF1-p1-p2-p7"}
    if not all(phrase in guidance["practice_text"] for phrase in ("eighth-note triplets", "12-18 BPM below", "pause one beat", "Add 2 BPM", "two separate days")):
        raise CandidateError("TXT_PRACTICE_RULE_MISMATCH")
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
    first = pages[0]
    if not all(any(phrase in line for line in first) for phrase in ("Three notes forward, one degree back", "12 equal triplets", "downstroke", "Page 1 of 7")):
        raise CandidateError("PDF_GUIDANCE_MISMATCH")
    route_page = pages[1]
    if route_page[:8] != ["Level 14 - Chromatic Major-Key Route and Sequence Map", "Ascending route: complete one 36-note rolling cell, then move the frame +1 fret", "Descending route: use the same cards in reverse order and move -1 fret", "Rung", "Key", "Low-E root", "Frame", "Scale tones (degrees 1-7)"]:
        raise CandidateError("PDF_ROUTE_MAP_HEADER_MISMATCH")
    for index, key in enumerate(KEYS):
        chunk = route_page[8 + 5 * index:13 + 5 * index]
        root = 5 + index
        if chunk != [f"{index+1:02d}", f"{key} major" + (" (octave)" if index == 12 else ""), f"fret {root}", f"{root-1}-{root+2}", " ".join(SCALE_TONES[index])]:
            raise CandidateError(f"PDF_ROUTE_MAP_RUNG_MISMATCH {index+1}")
    route_tail = "\n".join(route_page[73:])
    if not all(phrase in route_tail for phrase in ("rungs 01-13", "rungs 12-01. Do not replay the", "one three-note group per beat", "Page 2 of 7")):
        raise CandidateError("PDF_ROUTE_MAP_TAIL_MISMATCH")
    rungs = []
    for page_number in range(3, 8):
        lines = pages[page_number - 1]
        if page_number < 7:
            first_rung = 1 + 3 * (page_number - 3)
            if lines[:3] != ["Level 14 - Major Scale Three-Note Rolling Sequence", f"Rungs {first_rung:02d}-{first_rung+2:02d}: play each card as one 12-triplet cell, then move +1 fret", "For the descending pass, read the cards in reverse order and move -1 fret"] or lines[-2:] != [PDF_PAGE_FOOTER, f"Page {page_number} of 7"] or len(lines) != 47:
                raise CandidateError(f"PDF_RUNG_PAGE_SHAPE {page_number}")
            blocks = [lines[3 + 14 * j:3 + 14 * (j + 1)] for j in range(3)]
        else:
            if lines[:2] != ["Level 14 - Final Rung and Mastery Work", "Rung 13: complete the octave A-major cell, then reverse the neck route"] or lines[-1] != "Page 7 of 7":
                raise CandidateError("PDF_FINAL_PAGE_SHAPE")
            blocks = [lines[2:16]]
            if not all(phrase in "\n".join(lines[16:]) for phrase in ("rungs 01-13", "rungs 12-01", "opposite starting stroke")):
                raise CandidateError("PDF_FINAL_ROUND_TRIP_MISMATCH")
        for block in blocks:
            index = len(rungs)
            key, root = KEYS[index], 5 + index
            if len(block) != 14 or block[:4] != [f"{index+1:02d}  {key.upper()} MAJOR" + (" (OCTAVE)" if index == 12 else ""),
                                                    f"ROOT E{root}  |  FRAME {root-1}-{root+2}",
                                                    f"Scale tones: {' '.join(SCALE_TONES[index])} | octave {key}", PDF_CELL_LABEL] or block[12:] != [PDF_CARD_FOOTER, PDF_PICKING]:
                raise CandidateError(f"PDF_RUNG_CARD_MISMATCH {index+1}")
            groups, notes = _parse_rows(block[4], block[5], block[6:12], root)
            rungs.append({"rung": index+1, "key": key, "root_fret": root, "frame": [root-1, root+2],
                          "source_ref": f"L14-PDF1-p{page_number}", "printed": {"heading": block[0], "root_frame": block[1],
                          "scale_tones": block[2], "cell_label": block[3], "deg_row": block[4], "fng_row": block[5],
                          "tab_rows": block[6:12], "footer": block[12], "picking": block[13]},
                          "groups": groups, "notes": notes})
    if len(rungs) != 13:
        raise CandidateError(f"PDF_RUNG_COUNT {len(rungs)}")
    route = {"map_ref": "L14-PDF1-p2", "map_header": route_page[:8], "map_rows": route_page[8:73],
             "map_guidance": route_page[73:98], "final_round_trip_ref": "L14-PDF1-p7", "final_round_trip_text": "\n".join(pages[6][16:20])}
    return rungs, route


def build_candidate(*, txt_data: bytes | None = None, pdf_data: bytes | None = None) -> dict[str, Any]:
    root = _root()
    txt_data = _source_bytes(root, TXT_REL) if txt_data is None else txt_data
    pdf_data = _source_bytes(root, PDF_REL) if pdf_data is None else pdf_data
    _verify(txt_data, TXT_BYTES, TXT_SHA256, "L14-TXT")
    _verify(pdf_data, PDF_BYTES, PDF_SHA256, "L14-PDF")
    txt_rungs, instructions = _txt_rungs(txt_data)
    pdf_rungs, pdf_route = _pdf_rungs(pdf_data)
    records = []
    for txt, pdf in zip(txt_rungs, pdf_rungs, strict=True):
        if (txt["rung"], txt["key"], txt["root_fret"], txt["frame"]) != (pdf["rung"], pdf["key"], pdf["root_fret"], pdf["frame"]):
            raise CandidateError(f"PDF_TXT_RUNG_MISMATCH {txt['rung']}")
        for field in ("deg_row", "fng_row", "tab_rows"):
            if txt["printed"][field] != pdf["printed"][field]:
                raise CandidateError(f"PDF_TXT_ROW_MISMATCH {txt['rung']} {field}")
        if txt["groups"] != pdf["groups"] or txt["notes"] != pdf["notes"]:
            raise CandidateError(f"PDF_TXT_EVENT_MISMATCH {txt['rung']}")
        records.append({"source_local_key": f"L14-rung{txt['rung']:02d}", "rung": txt["rung"], "key": txt["key"],
                        "key_label": txt["key_label"], "root_string": "E", "root_fret": txt["root_fret"], "frame": txt["frame"],
                        "scale_tones": txt["scale_tones"], "source_refs": {"txt": txt["source_ref"], "pdf_card": pdf["source_ref"], "pdf_map": "L14-PDF1-p2"},
                        "printed_txt": txt["printed"], "printed_pdf": pdf["printed"], "groups": txt["groups"],
                        "canonical_item_id": None, "canonical_variant_id": None, "onset_q": None, "duration_q": None,
                        "note_per_click": None, "fixed_bpm": None, "runtime_eligible": False, "runtime_admitted": False,
                        "imported": False, "admitted": False})
    up = list(range(1, 14))
    down = list(range(13, 0, -1))
    route = {"ascending_landmarks": [{"rung": n, "key": KEYS[n-1], "root_fret": n+4} for n in up],
             "descending_landmarks": [{"rung": n, "key": KEYS[n-1], "root_fret": n+4} for n in down],
             "single_turn_cell_sequence": up + down[1:], "single_turn_cell_count": 25,
             "turn_rung_played_once": 13, "up_fret_step": 1, "down_fret_step": -1,
             "txt_ref": "L14-TXT1-44-45,L14-TXT1-239-241", "pdf_ref": "L14-PDF1-p2,L14-PDF1-p7",
             "interpretation": "The 13-rung DOWN route lists the turn position A(17); a continuous round trip plays its cell once before returning through rungs 12-01."}
    return {"schema": "fathom-level014-whole-detached-candidate-v1", "wbs_id": "2.3.1.1.1", "level": 14,
            "source": {"txt_path": TXT_REL.as_posix(), "txt_bytes": TXT_BYTES, "txt_sha256": TXT_SHA256,
                       "pdf_path": PDF_REL.as_posix(), "pdf_bytes": PDF_BYTES, "pdf_sha256": PDF_SHA256, "pdf_pages": 7},
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
