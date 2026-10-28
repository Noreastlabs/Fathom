#!/usr/bin/env python3
"""Build a detached, source-linked candidate for the whole Level 12 neck ladder.

TAB columns locate printed notes. They do not encode clock time or duration.
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
TXT_REL = Path("Notes/music/guitar project/TXT version/Scale_Exercises_Section_II_Level_12_Major_Scale_One_Fret_Neck_Ladder.txt")
PDF_REL = Path("Notes/music/guitar project/PDF version/Scale_Exercises_Section_II_Level_12_Major_Scale_One_Fret_Neck_Ladder.pdf")
TXT_BYTES = 13087
TXT_SHA256 = "64e65f5293012f9af3c84a885cbdd54c82275f6c6e282c8f8a28cca579631be9"
PDF_BYTES = 18783
PDF_SHA256 = "ae31f029a3df324baa8822b913deb499eccc1438f1986967f96889e6eb45bd3b"
BUILD_REL = Path("Build/parallel-07/2.3.1.1.1-level012-whole-r01")
KEYS = ("A", "Bb", "B", "C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A")
DEGREES = (1, 2, 3, 4, 5, 6, 7, 8, 8, 7, 6, 5, 4, 3, 2, 1)
FINGERS = (2, 4, 1, 2, 4, 1, 3, 4, 4, 3, 1, 4, 2, 1, 4, 2)
STRING_ORDER = ("e", "B", "G", "D", "A", "E")
NOTE_STRINGS = ("E", "E", "A", "A", "A", "D", "D", "D", "D", "D", "D", "A", "A", "A", "E", "E")
NATURAL_PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
OPEN_MIDI = {"E": 40, "A": 45, "D": 50}
RUNG_TXT = re.compile(r"^RUNG (\d{2}) OF 13 - ([A-Z]+) MAJOR( \(OCTAVE\))? - ROOT ON LOW E FRET (\d+) - FRAME (\d+)-(\d+)$")
RUNG_PDF = re.compile(r"^(\d{2})  ([A-Z]+) MAJOR( \(OCTAVE\))?$")
PDF_ROOT = re.compile(r"^ROOT E(\d+)  \|  FRAME (\d+)-(\d+)$")
ROUTE_ITEM = re.compile(r"([A-G](?:b|#)?)\((\d+)\)")
NOTE_NAME = re.compile(r"^[A-G](?:b|#)?$")


class CandidateError(ValueError):
    """A pinned source, authored cell, route, or output boundary failed."""


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


def _body(row: str, prefix: str) -> str:
    if not row.startswith(prefix + "|") or not row.endswith("|"):
        raise CandidateError(f"ROW_LABEL_INVALID {prefix}")
    content = row[len(prefix) + 1:-1]
    if len(content) != 48:
        raise CandidateError(f"ROW_WIDTH_INVALID {prefix} {len(content)}")
    return content


def _note_pc(name: str) -> int:
    if NOTE_NAME.fullmatch(name) is None:
        raise CandidateError(f"SCALE_TONE_INVALID {name}")
    accidental = (1 if name.endswith("#") else -1 if name.endswith("b") else 0)
    return (NATURAL_PC[name[0]] + accidental) % 12


def _tab_notes(rows: list[str], root_fret: int, tones: list[str]) -> list[dict[str, Any]]:
    degree_body = _body(rows[0], "Deg")
    finger_body = _body(rows[1], "Fng")
    degree_tokens = [(m.start(), int(m.group())) for m in re.finditer(r"\d+", degree_body)]
    finger_tokens = [(m.start(), int(m.group())) for m in re.finditer(r"\d+", finger_body)]
    if tuple(value for _, value in degree_tokens) != DEGREES or tuple(value for _, value in finger_tokens) != FINGERS:
        raise CandidateError("DEGREE_OR_FINGER_SEQUENCE_INVALID")
    if tuple(column for column, _ in degree_tokens) != tuple(column for column, _ in finger_tokens):
        raise CandidateError("DEGREE_FINGER_COLUMN_MISMATCH")
    found = []
    for row, string in zip(rows[2:], STRING_ORDER, strict=True):
        for token in re.finditer(r"\d+", _body(row, string + "  ")):
            found.append((token.start(), string, int(token.group())))
    found.sort(key=lambda entry: entry[0])
    if len(found) != 16 or len({column for column, _, _ in found}) != 16:
        raise CandidateError("TAB_NOTE_COUNT_OR_COLLISION")
    if tuple(column for column, _, _ in found) != tuple(column for column, _ in degree_tokens):
        raise CandidateError("TAB_DEGREE_COLUMN_MISMATCH")
    if tuple(string for _, string, _ in found) != NOTE_STRINGS:
        raise CandidateError("TAB_STRING_ROUTE_MISMATCH")
    r = root_fret
    expected_frets = (r, r + 2, r - 1, r, r + 2, r - 1, r + 1, r + 2,
                      r + 2, r + 1, r - 1, r + 2, r, r - 1, r + 2, r)
    if tuple(fret for _, _, fret in found) != expected_frets:
        raise CandidateError("TAB_TRANSPOSED_SHAPE_MISMATCH")
    if len(tones) != 8 or tones[0] != tones[-1]:
        raise CandidateError("SCALE_TONE_OCTAVE_INVALID")
    notes = []
    for index, ((column, string, fret), (_, degree), (_, finger)) in enumerate(
        zip(found, degree_tokens, finger_tokens, strict=True)
    ):
        tone = tones[degree - 1]
        midi = OPEN_MIDI[string] + fret
        if midi % 12 != _note_pc(tone):
            raise CandidateError(f"SCALE_TONE_PITCH_MISMATCH {index + 1} {tone}")
        notes.append({
            "ordinal": index + 1, "degree": degree, "tone": tone, "string": string,
            "fret": fret, "finger_digit": finger, "ascii_column": column,
            "onset_q": None, "duration_q": None,
        })
    if notes[7]["degree"] != 8 or notes[8]["degree"] != 8 or (notes[7]["string"], notes[7]["fret"]) != (notes[8]["string"], notes[8]["fret"]):
        raise CandidateError("OCTAVE_ROOT_REPEAT_MISSING")
    if OPEN_MIDI[notes[7]["string"]] + notes[7]["fret"] != OPEN_MIDI[notes[0]["string"]] + notes[0]["fret"] + 12:
        raise CandidateError("ONE_OCTAVE_SPAN_INVALID")
    return notes


def _txt_cards(txt: str) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    lines = txt.splitlines()
    if len(lines) != 231 or lines[:2] != ["SCALE EXERCISES - SECTION II, LEVEL 12", "MAJOR SCALE ONE-FRET NECK LADDER: A TO A"]:
        raise CandidateError("TXT_HEADER_OR_LENGTH_MISMATCH")
    starts = [(index, match) for index, line in enumerate(lines) if (match := RUNG_TXT.fullmatch(line))]
    if tuple(index + 1 for index, _ in starts) != tuple(42 + 14 * n for n in range(13)):
        raise CandidateError("TXT_RUNG_BOUNDARY_MISMATCH")
    cards = []
    for index, (start, match) in enumerate(starts):
        number = int(match.group(1))
        key = match.group(2).capitalize()
        octave = bool(match.group(3))
        root_fret, frame_low, frame_high = map(int, match.group(4, 5, 6))
        if (number, key, octave, root_fret, frame_low, frame_high) != (
            index + 1, KEYS[index], index == 12, index + 5, index + 4, index + 7
        ):
            raise CandidateError(f"TXT_RUNG_IDENTITY_MISMATCH {number}")
        body = lines[start + 1:start + 12]
        if len(body) != 11 or not body[0].startswith("Scale tones: ") or body[1] != "16-note cell: ascend 1-8, repeat the octave root, descend 8-1.":
            raise CandidateError(f"TXT_RUNG_LAYOUT_MISMATCH {number}")
        if body[10] != "Finish on the low root, release pressure, and move the entire frame one fret in the route direction.":
            raise CandidateError(f"TXT_RUNG_FINISH_MISMATCH {number}")
        if lines[start + 12] != "" or not lines[start + 13].startswith("==="):
            raise CandidateError(f"TXT_RUNG_SEPARATOR_MISMATCH {number}")
        tones = body[0].removeprefix("Scale tones: ").split()
        raw_rows = body[2:10]
        notes = _tab_notes(raw_rows, root_fret, tones)
        cards.append({
            "rung_number": f"{number:02d}", "key": key, "octave_rung": octave,
            "root_string": "E", "root_fret": root_fret,
            "frame_low": frame_low, "frame_high": frame_high,
            "scale_tones": tones, "raw_rows": raw_rows, "notes": notes,
            "heading_line": start + 1, "last_line": start + 12,
        })
    if lines[223] != "FULL ROUND-TRIP CHALLENGE" or lines[228] != "AFTER MASTERY":
        raise CandidateError("TXT_FOOTER_BOUNDARY_MISMATCH")
    route_lines = (lines[30], lines[31])
    route_labels = []
    for label, route in zip(("UP:", "DOWN:"), route_lines, strict=True):
        if not route.startswith(label):
            raise CandidateError("TXT_ROUTE_LABEL_MISMATCH")
        route_labels.append([(key, int(fret)) for key, fret in ROUTE_ITEM.findall(route)])
    expected_up = [(card["key"], card["root_fret"]) for card in cards]
    if route_labels != [expected_up, list(reversed(expected_up))]:
        raise CandidateError("TXT_ROUTE_ORDER_MISMATCH")
    guidance = {
        "overview_text": "\n".join(lines[:40]), "overview_ref": "L12-TXT1-1-40",
        "round_trip_text": "\n".join(lines[223:227]), "round_trip_ref": "L12-TXT1-224-227",
        "after_mastery_text": "\n".join(lines[228:231]), "after_mastery_ref": "L12-TXT1-229-231",
        "pdf_overview_ref": "L12-PDF1-p1", "pdf_route_ref": "L12-PDF1-p2",
    }
    for phrase in ("one fret", "A major is the starting rung, not the key of every rung",
                   "octave root is repeated", "16 notes", "both pick starts"):
        if phrase not in guidance["overview_text"]:
            raise CandidateError(f"TXT_GUIDANCE_MISMATCH {phrase}")
    return cards, guidance, {"up": route_lines[0], "down": route_lines[1]}


def _pdf_cards(pdf_data: bytes) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    try:
        reader = PdfReader(BytesIO(pdf_data), strict=True)
        if len(reader.pages) != 6:
            raise CandidateError(f"PDF_PAGE_COUNT {len(reader.pages)}")
        pages = [(page.extract_text() or "").splitlines() for page in reader.pages]
    except CandidateError:
        raise
    except Exception as exc:
        raise CandidateError(f"PDF_READ_FAILED {type(exc).__name__}") from exc
    if "one fret" not in " ".join(pages[0]) or "The scale section starts on A." not in pages[0]:
        raise CandidateError("PDF_OVERVIEW_MISMATCH")
    table_page = pages[1]
    if table_page[:5] != [
        "Level 12 - Chromatic Major-Key Route",
        "Standard tuning. Compact one-octave 6th-string-root major scale. One completed cell = 16 notes.",
        "Page 2 of 6",
        "Ascending route: complete each scale cell, then move the frame +1 fret",
        "Descending route: use the same cards in reverse order and move -1 fret",
    ]:
        raise CandidateError("PDF_ROUTE_HEADER_MISMATCH")
    table_start = table_page.index("Scale tones (degrees 1-7)") + 1
    table_rows = table_page[table_start:table_start + 13 * 5]
    if len(table_rows) != 65 or "Up pass: rungs 01-13." not in table_page or "Down pass: rungs 12-01. Do not" not in table_page:
        raise CandidateError("PDF_ROUTE_TABLE_MISMATCH")
    table = []
    for index in range(13):
        number, key, root, frame, tones = table_rows[index * 5:index * 5 + 5]
        if number != f"{index + 1:02d}" or root != f"fret {index + 5}" or frame != f"{index + 4}-{index + 7}":
            raise CandidateError(f"PDF_ROUTE_ROW_IDENTITY_MISMATCH {index + 1}")
        table.append({"number": number, "key": key, "root_fret": index + 5,
                      "frame": frame, "tones_1_to_7": tones.split()})
    cards = []
    for page_number, first, count in ((3, 1, 4), (4, 5, 4), (5, 9, 4), (6, 13, 1)):
        lines = pages[page_number - 1]
        if lines[:3] != [
            "Level 12 - Major Scale One-Fret Neck Ladder",
            "Standard tuning. Compact one-octave 6th-string-root major scale. One completed cell = 16 notes.",
            f"Page {page_number} of 6",
        ]:
            raise CandidateError(f"PDF_CARD_PAGE_HEADER_MISMATCH {page_number}")
        starts = [(i, m) for i, line in enumerate(lines) if (m := RUNG_PDF.fullmatch(line))]
        if len(starts) != count or tuple(int(m.group(1)) for _, m in starts) != tuple(range(first, first + count)):
            raise CandidateError(f"PDF_CARD_COUNT_OR_ORDER_MISMATCH {page_number}")
        for position, (start, match) in enumerate(starts):
            stop = starts[position + 1][0] if position + 1 < count else len(lines)
            body = lines[start + 1:stop]
            if len(body) < 13 or body[2] != "16-NOTE UP/DOWN CELL" or not body[1].startswith("Notes: "):
                raise CandidateError(f"PDF_CARD_LAYOUT_MISMATCH {match.group(1)}")
            root_match = PDF_ROOT.fullmatch(body[0])
            if root_match is None or body[11] != "Finish on the low root; release pressure; move the entire frame one fret." or body[12] != "D-start and U-start":
                raise CandidateError(f"PDF_CARD_LAYOUT_MISMATCH {match.group(1)}")
            if page_number != 6 and len(body) != 13:
                raise CandidateError(f"PDF_CARD_TRAILING_TEXT_UNEXPECTED {match.group(1)}")
            if page_number == 6 and ("Full round-trip challenge" not in body[13:] or "3. Reverse at fret 17 and return through rungs 12-01." not in body[13:]):
                raise CandidateError("PDF_ROUND_TRIP_MISMATCH")
            cards.append({
                "number": match.group(1), "key": match.group(2).capitalize(),
                "octave_rung": bool(match.group(3)), "root_fret": int(root_match.group(1)),
                "frame_low": int(root_match.group(2)), "frame_high": int(root_match.group(3)),
                "scale_tones": body[1].removeprefix("Notes: ").split(),
                "raw_rows": body[3:11], "pdf_page": page_number,
            })
    return cards, table


def build_candidate(*, txt_data: bytes | None = None, pdf_data: bytes | None = None) -> dict[str, Any]:
    root = _root()
    txt_data = _source_bytes(root, TXT_REL) if txt_data is None else txt_data
    pdf_data = _source_bytes(root, PDF_REL) if pdf_data is None else pdf_data
    _verify(txt_data, TXT_BYTES, TXT_SHA256, "L12-TXT")
    _verify(pdf_data, PDF_BYTES, PDF_SHA256, "L12-PDF")
    try:
        txt_cards, guidance, raw_routes = _txt_cards(txt_data.decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise CandidateError("TXT_ENCODING_INVALID") from exc
    pdf_cards, table = _pdf_cards(pdf_data)
    records = []
    for txt_card, pdf_card, row in zip(txt_cards, pdf_cards, table, strict=True):
        number = txt_card["rung_number"]
        if (pdf_card["number"], pdf_card["key"], pdf_card["octave_rung"], pdf_card["root_fret"],
            pdf_card["frame_low"], pdf_card["frame_high"], pdf_card["scale_tones"], pdf_card["raw_rows"]) != (
            number, txt_card["key"], txt_card["octave_rung"], txt_card["root_fret"],
            txt_card["frame_low"], txt_card["frame_high"], txt_card["scale_tones"], txt_card["raw_rows"]
        ):
            raise CandidateError(f"PDF_TXT_CARD_MISMATCH {number}")
        expected_key = txt_card["key"] + " major" + (" (octave)" if txt_card["octave_rung"] else "")
        if (row["number"], row["key"], row["root_fret"], row["frame"], row["tones_1_to_7"]) != (
            number, expected_key, txt_card["root_fret"],
            f"{txt_card['frame_low']}-{txt_card['frame_high']}", txt_card["scale_tones"][:7]
        ):
            raise CandidateError(f"PDF_ROUTE_CARD_MISMATCH {number}")
        records.append({
            "source_local_key": f"L12-rung{number}", "rung_number": number,
            "key": txt_card["key"], "octave_rung": txt_card["octave_rung"],
            "root_string": "E", "root_fret": txt_card["root_fret"],
            "frame_low": txt_card["frame_low"], "frame_high": txt_card["frame_high"],
            "scale_tones": txt_card["scale_tones"], "raw_rows": txt_card["raw_rows"],
            "notes": txt_card["notes"],
            "source_refs": {"txt": f"L12-TXT1-{txt_card['heading_line']}-{txt_card['last_line']}",
                            "pdf_card": f"L12-PDF1-p{pdf_card['pdf_page']}", "pdf_route_table": "L12-PDF1-p2"},
            "canonical_item_id": None, "canonical_variant_id": None,
            "onset_q": None, "duration_q": None, "fixed_bpm": None, "note_per_click": None,
            "runtime_eligible": False, "runtime_admitted": False, "imported": False, "admitted": False,
        })
    up = [record["source_local_key"] for record in records]
    down = list(reversed(up))
    return {
        "schema": "fathom-level012-whole-detached-candidate-v1", "wbs_id": "2.3.1.1.1", "level": 12,
        "source": {"txt_path": TXT_REL.as_posix(), "txt_bytes": TXT_BYTES, "txt_sha256": TXT_SHA256,
                   "pdf_path": PDF_REL.as_posix(), "pdf_bytes": PDF_BYTES, "pdf_sha256": PDF_SHA256,
                   "pdf_pages": 6, "selected_pdf_card_pages": [3, 4, 5, 6]},
        "instructions": guidance,
        "routes": {
            "up": {"rungs": up, "root_frets": list(range(5, 18)), "shift_frets_between_cells": 1,
                   "source_text": raw_routes["up"], "source_refs": ["L12-TXT1-31", "L12-PDF1-p2"]},
            "down": {"rungs": down, "root_frets": list(range(17, 4, -1)), "shift_frets_between_cells": -1,
                     "source_text": raw_routes["down"], "source_refs": ["L12-TXT1-32", "L12-PDF1-p2"]},
            "continuous_round_trip": {"rungs": up + down[1:], "turn_after_rung": "L12-rung13",
                                      "return_rungs": down[1:], "source_refs": ["L12-TXT1-224-226", "L12-PDF1-p2", "L12-PDF1-p6"]},
        },
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
