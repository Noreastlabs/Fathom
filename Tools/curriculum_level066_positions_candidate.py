#!/usr/bin/env python3
"""Build detached source-linked Level 66 Module A vertical-position cards."""

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
TXT_REL = Path("Notes/music/guitar project/TXT version/Guitar_Exercises_Section_VIII_Level_66_A_Harmonic_Minor_Five_Position_Map_Horizontal_Routes_Sequences_Seam_Transitions_and_Full_Register_Movement.txt")
PDF_REL = Path("Notes/music/guitar project/PDF version/Guitar_Exercises_Section_VIII_Level_66_A_Harmonic_Minor_Five_Position_Map_Horizontal_Routes_Sequences_Seam_Transitions_and_Full_Register_Movement.pdf")
TXT_BYTES = 28401
TXT_SHA256 = "c8f3675ac60f9b220715c7aa3da7260c7a87bd461f6682865cc40fa3046e1dbe"
PDF_BYTES = 57857
PDF_SHA256 = "9bf4baf225ad063e75349b0a290d193c3bd797e7c6584fc4425adeb18de1b13c"
BUILD_REL = Path("Build/parallel-09/2.3-level066-positions-r01")
POSITION_IDS = ("P1", "P2", "P3", "P4", "P5")
TXT_STARTS = (24, 37, 50, 63, 76)  # zero-based heading line indexes
STRING_LOW_TO_HIGH = ("E", "A", "D", "G", "B", "e")
STRING_HIGH_TO_LOW = tuple(reversed(STRING_LOW_TO_HIGH))
OPEN_MIDI = {"E": 40, "A": 45, "D": 50, "G": 55, "B": 59, "e": 64}
PITCH_CLASSES = {"A": 9, "B": 11, "C": 0, "D": 2, "E": 4, "F": 5, "G#": 8}
DEGREES_FOR_NOTE = {"A": "1", "B": "2", "C": "b3", "D": "4", "E": "5", "F": "b6", "G#": "7"}
HEADING = re.compile(r"^(P[1-5]) - (.+) - FRETS (\d+)-(\d+) - START ([A-G]#?) / degree (b3|b6|[1-7]) - ROOTS (.+)$")
TAB_ROW = re.compile(r"^([eBGDAE])\|([0-9-]+)\|([0-9-]+)$")


class CandidateError(ValueError):
    """Pinned input, source cell or output boundary failed."""


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _verify(data: bytes, expected_size: int, expected_sha: str, label: str) -> None:
    if len(data) != expected_size or digest(data) != expected_sha:
        raise CandidateError(f"PINNED_INPUT_DRIFT {label}: bytes={len(data)} sha256={digest(data)}")


def _root() -> Path:
    result = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if result.returncode != 0 or Path(result.stdout.strip()).resolve() != ROOT.resolve():
        raise CandidateError("REPOSITORY_ROOT_MISMATCH")
    return ROOT


def _source_bytes(root: Path, relative: Path) -> bytes:
    path = root / relative
    if not path.is_file() or path.is_symlink() or path.resolve().parent != path.parent.resolve():
        raise CandidateError(f"SOURCE_PATH_INVALID {relative}")
    return path.read_bytes()


def _tokens(row: str, label: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    if not row.startswith(label + "|") or row.count("|") != 2:
        raise CandidateError(f"{label}_ROW_FORMAT_INVALID")
    left, right = row[len(label) + 1:].split("|", 1)
    expression = {"Nte": r"G#|[A-G]", "Deg": r"b3|b6|[1-7]", "Fng": r"[1-4]"}[label]
    parts = tuple(tuple(re.findall(expression, segment)) for segment in (left, right))
    if any(len(part) != 18 for part in parts):
        raise CandidateError(f"{label}_TOKEN_COUNT_INVALID")
    if any(re.sub(expression + r"|-", "", segment) for segment in (left, right)):
        raise CandidateError(f"{label}_TOKEN_INVALID")
    return parts[0], parts[1]


def _parse_rows(rows: list[str], source: str, position: str) -> dict[str, Any]:
    if len(rows) != 9:
        raise CandidateError(f"CARD_ROW_COUNT {source} {position}: {len(rows)}")
    ascending_notes, descending_notes = _tokens(rows[0], "Nte")
    ascending_degrees, descending_degrees = _tokens(rows[1], "Deg")
    ascending_fingers, descending_fingers = _tokens(rows[2], "Fng")
    tab_rows = [row.strip() for row in rows[3:]]
    if tuple(TAB_ROW.fullmatch(row).group(1) if TAB_ROW.fullmatch(row) else None for row in tab_rows) != STRING_HIGH_TO_LOW:
        raise CandidateError(f"TAB_STRING_ORDER_INVALID {source} {position}")
    frets_by_string = {}
    for row in tab_rows:
        match = TAB_ROW.fullmatch(row)
        assert match is not None
        string, asc, desc = match.groups()
        if re.sub(r"[0-9-]", "", asc + desc):
            raise CandidateError(f"TAB_CHARACTER_INVALID {source} {position} {string}")
        up = tuple(int(x) for x in re.findall(r"\d+", asc))
        down = tuple(int(x) for x in re.findall(r"\d+", desc))
        if len(up) != 3 or len(down) != 3:
            raise CandidateError(f"TAB_STRING_THREE_NOTE_COUNT {source} {position} {string}")
        frets_by_string[string] = {"ascending": up, "descending": down}
    routes = {}
    for direction, string_order, notes, degrees, fingers in (
        ("ascending", STRING_LOW_TO_HIGH, ascending_notes, ascending_degrees, ascending_fingers),
        ("descending", STRING_HIGH_TO_LOW, descending_notes, descending_degrees, descending_fingers),
    ):
        frets = [(string, fret) for string in string_order for fret in frets_by_string[string][direction]]
        if len(frets) != 18:
            raise CandidateError(f"ROUTE_NOTE_COUNT {source} {position} {direction}")
        attacks = []
        for i, ((string, fret), note, degree, finger) in enumerate(zip(frets, notes, degrees, fingers, strict=True)):
            if not 0 <= fret <= 24 or note not in PITCH_CLASSES or degree != DEGREES_FOR_NOTE[note]:
                raise CandidateError(f"PRINTED_NOTE_DEGREE_INVALID {source} {position} {direction} {i + 1}")
            if (OPEN_MIDI[string] + fret) % 12 != PITCH_CLASSES[note]:
                raise CandidateError(f"PITCH_FRET_CONFLICT {source} {position} {direction} {i + 1}")
            attacks.append({
                "ordinal": i + 1, "string": string, "fret": fret,
                "printed_note": note, "printed_degree": degree, "printed_finger": int(finger),
                "onset_q": None, "duration_q": None,
            })
        routes[direction] = attacks
    forward = [(a["string"], a["fret"], a["printed_note"], a["printed_degree"]) for a in routes["ascending"]]
    reverse = [(a["string"], a["fret"], a["printed_note"], a["printed_degree"]) for a in routes["descending"]]
    if reverse != list(reversed(forward)):
        raise CandidateError(f"NOT_EXACT_REVERSE {source} {position}")
    return {"tab_rows": tab_rows, "routes": routes}


def _txt_cards(text: str) -> list[dict[str, Any]]:
    lines = text.splitlines()
    if lines[:2] != [
        "GUITAR EXERCISES - SECTION VIII, LEVEL 66",
        "A HARMONIC MINOR FIVE-POSITION MAP, HORIZONTAL ROUTES, SEQUENCES, SEAM TRANSITIONS, AND FULL-REGISTER MOVEMENT",
    ]:
        raise CandidateError("TXT_HEADER_MISMATCH")
    if lines[22] != "MODULE A - FIVE 36-TONE VERTICAL POSITION CELLS" or lines[91] != "MODULE B - FOUR SHARED-ANCHOR SEAMS":
        raise CandidateError("TXT_MODULE_BOUNDARY_MISMATCH")
    cards = []
    for position, start in zip(POSITION_IDS, TXT_STARTS, strict=True):
        heading = HEADING.fullmatch(lines[start])
        if heading is None or heading.group(1) != position:
            raise CandidateError(f"TXT_CARD_HEADING_INVALID {position}")
        frame_name, low, high, start_note, start_degree, roots_text = heading.groups()[1:]
        roots = tuple(root.strip() for root in roots_text.split(","))
        if not roots or any(re.fullmatch(r"[eEADGB]\d+", root) is None for root in roots):
            raise CandidateError(f"ROOT_DECLARATION_INVALID {position}")
        for root in roots:
            match = re.fullmatch(r"([eEADGB])(\d+)", root)
            assert match is not None
            if (OPEN_MIDI[match.group(1)] + int(match.group(2))) % 12 != PITCH_CLASSES["A"]:
                raise CandidateError(f"ROOT_PITCH_INVALID {position} {root}")
        if start_note not in PITCH_CLASSES or start_degree != DEGREES_FOR_NOTE[start_note]:
            raise CandidateError(f"START_NOTE_DEGREE_INVALID {position}")
        parsed = _parse_rows(lines[start + 1:start + 10], "TXT", position)
        if any(
            not int(low) <= attack["fret"] <= int(high)
            for route in parsed["routes"].values() for attack in route
        ):
            raise CandidateError(f"FRET_OUTSIDE_PRINTED_FRAME {position}")
        hand_note = lines[start + 11]
        if not hand_note.startswith("Hand note: "):
            raise CandidateError(f"HAND_NOTE_MISSING {position}")
        if parsed["routes"]["ascending"][0]["printed_note"] != start_note:
            raise CandidateError(f"START_NOTE_ROUTE_MISMATCH {position}")
        parsed.update({
            "position": position, "frame_name": frame_name, "fret_bounds": [int(low), int(high)],
            "start_note": start_note, "start_degree": start_degree, "roots": list(roots),
            "heading": lines[start], "hand_note": hand_note[11:],
            "txt_ref": f"L66-TXT1-{start + 1}-{start + 12}",
        })
        cards.append(parsed)
    return cards


def _pdf_cards(data: bytes) -> list[dict[str, Any]]:
    try:
        reader = PdfReader(BytesIO(data), strict=True)
        if len(reader.pages) != 20:
            raise CandidateError(f"PDF_PAGE_COUNT {len(reader.pages)}")
        page_texts = [(page.extract_text() or "") for page in reader.pages[2:7]]
    except CandidateError:
        raise
    except Exception as exc:
        raise CandidateError(f"PDF_READ_FAILED {type(exc).__name__}") from exc
    cards = []
    for index, (position, text) in enumerate(zip(POSITION_IDS, page_texts, strict=True), start=3):
        lines = text.splitlines()
        if lines[0] != "Guitar Exercises - Section VIII, Level 66" or not lines[1].startswith(f"Module A - {position} "):
            raise CandidateError(f"PDF_CARD_HEADER_INVALID {position}")
        if "36 TONES" not in lines[2] or "18 TONES ASCENDING + EXACT 18-TONE REVERSE; THE HIGHEST NOTE IS RE-ATTACKED" not in lines:
            raise CandidateError(f"PDF_CARD_COUNT_OR_TURNAROUND_INVALID {position}")
        marker = f"{position} - complete 36-tone position cell"
        if lines.count(marker) != 1:
            raise CandidateError(f"PDF_CARD_MARKER_INVALID {position}")
        start = lines.index(marker)
        parsed = _parse_rows(lines[start + 1:start + 10], "PDF", position)
        hand = text.split("Hand and ear note\n", 1)
        if len(hand) != 2 or "\nRoot audit:" not in hand[1]:
            raise CandidateError(f"PDF_HAND_NOTE_MISSING {position}")
        hand_text = hand[1].split("\nRoot audit:", 1)[0]
        parsed.update({
            "position": position, "pdf_ref": f"L66-PDF1-p{index}",
            "pdf_frame_title": lines[1], "pdf_bounds": lines[2],
            "pdf_hand_note": " ".join(hand_text.split()),
            "pdf_instruction": lines[4],
        })
        cards.append(parsed)
    return cards


def build_candidate(*, txt_data: bytes | None = None, pdf_data: bytes | None = None) -> dict[str, Any]:
    root = _root()
    txt_data = _source_bytes(root, TXT_REL) if txt_data is None else txt_data
    pdf_data = _source_bytes(root, PDF_REL) if pdf_data is None else pdf_data
    _verify(txt_data, TXT_BYTES, TXT_SHA256, "L66-TXT")
    _verify(pdf_data, PDF_BYTES, PDF_SHA256, "L66-PDF")
    try:
        txt_cards = _txt_cards(txt_data.decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise CandidateError("TXT_ENCODING_INVALID") from exc
    pdf_cards = _pdf_cards(pdf_data)
    records = []
    for txt, pdf in zip(txt_cards, pdf_cards, strict=True):
        position = txt["position"]
        if pdf["position"] != position or pdf["tab_rows"] != txt["tab_rows"] or pdf["routes"] != txt["routes"]:
            raise CandidateError(f"PDF_TXT_CARD_MISMATCH {position}")
        if pdf["pdf_hand_note"] != " ".join(txt["hand_note"].split()):
            raise CandidateError(f"PDF_TXT_HAND_NOTE_MISMATCH {position}")
        if f"{txt['fret_bounds'][0]}-{txt['fret_bounds'][1]}" not in pdf["pdf_bounds"]:
            raise CandidateError(f"PDF_TXT_FRAME_BOUNDS_MISMATCH {position}")
        if txt["frame_name"].lower() not in pdf["pdf_frame_title"].lower():
            raise CandidateError(f"PDF_TXT_FRAME_NAME_MISMATCH {position}")
        lead = f"{txt['start_note']} / degree {txt['start_degree']}. A roots: {', '.join(txt['roots'])}."
        if not pdf["pdf_instruction"].startswith(lead):
            raise CandidateError(f"PDF_TXT_START_OR_ROOT_MISMATCH {position}")
        records.append({
            "source_local_key": f"L66-moduleA-{position}", "position": position,
            "frame_name": txt["frame_name"], "fret_bounds": txt["fret_bounds"],
            "start_note": txt["start_note"], "start_degree": txt["start_degree"],
            "roots": txt["roots"], "hand_note": txt["hand_note"],
            "source_refs": {"txt": txt["txt_ref"], "pdf": pdf["pdf_ref"]},
            "tab_rows": txt["tab_rows"], "routes": txt["routes"],
            "pdf_instruction": pdf["pdf_instruction"],
            "canonical_item_id": None, "canonical_variant_id": None,
            "fixed_bpm": None, "note_per_click": None,
            "runtime_eligible": False, "runtime_admitted": False,
            "imported": False, "admitted": False,
        })
    if len(records) != 5 or sum(len(row["routes"][direction]) for row in records for direction in ("ascending", "descending")) != 180:
        raise CandidateError("SELECTED_TOTAL_COUNT_INVALID")
    return {
        "schema": "fathom-level066-moduleA-positions-detached-v1", "wbs_id": "2.3.1.2.1",
        "level": 66, "section": "VIII", "module": "A",
        "source": {
            "txt_path": TXT_REL.as_posix(), "txt_bytes": TXT_BYTES, "txt_sha256": TXT_SHA256,
            "pdf_path": PDF_REL.as_posix(), "pdf_bytes": PDF_BYTES, "pdf_sha256": PDF_SHA256,
            "pdf_pages": 20, "selected_pdf_pages": [3, 4, 5, 6, 7],
        },
        "records": records, "exceptions": [],
        "pending": ["Module B seams", "horizontal lanes and later Level 66 modules", "canonical identity allocation and admission", "Curriculum/musical review", "performed audio and note-level timing"],
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
    return {"output": str(target.relative_to(root)), "bytes": len(data), "sha256": digest(data), "cards": len(candidate["records"])}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(write_candidate(args.output), sort_keys=True))
    except CandidateError as exc:
        parser.exit(2, f"{exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
