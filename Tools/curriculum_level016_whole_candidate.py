#!/usr/bin/env python3
"""Build a pinned, non-admitted Level 16 rolling-sequence source candidate."""

from __future__ import annotations

import argparse
from io import BytesIO
import hashlib
import json
from pathlib import Path
import re
import subprocess
from typing import Any

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
BUILD_REL = Path("Build/parallel-11/2.3.1.1.1-level016-whole-r01")
TXT = ("Notes/music/guitar project/TXT version/Scale_Exercises_Section_II_Level_16_Major_Scale_Four_Note_Rolling_Sequence_One_Octave_Neck_Ladder.txt",
       "791020f0cdc3d38d690762b9544d9e3e59bf7caad2ccf81a845f771660b5693c", 24787)
PDF = ("Notes/music/guitar project/PDF version/Scale_Exercises_Section_II_Level_16_Major_Scale_Four_Note_Rolling_Sequence_One_Octave_Neck_Ladder.pdf",
       "20e71408a18593b1ac4da655f9dc2174135ab6caf94240c5f978f3fbf11956aa", 21350)
KEYS = ("A", "Bb", "B", "C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A")
TONES = (
    "A B C# D E F# G# A", "Bb C D Eb F G A Bb", "B C# D# E F# G# A# B",
    "C D E F G A B C", "Db Eb F Gb Ab Bb C Db", "D E F# G A B C# D",
    "Eb F G Ab Bb C D Eb", "E F# G# A B C# D# E", "F G A Bb C D E F",
    "Gb Ab Bb Cb Db Eb F Gb", "G A B C D E F# G", "Ab Bb C Db Eb F G Ab",
    "A B C# D E F# G# A",
)
UP_GROUPS = tuple(tuple(range(start, start + 4)) for start in range(1, 6))
DOWN_GROUPS = tuple(tuple(range(start, start - 4, -1)) for start in range(8, 3, -1))
GROUPS = UP_GROUPS + DOWN_GROUPS
STRINGS = ("e", "B", "G", "D", "A", "E")
SCALE_STRING = ("E", "E", "A", "A", "A", "D", "D", "D")
FINGERS = (2, 4, 1, 2, 4, 1, 3, 4)
FINGER_NAMES = {1: "index", 2: "middle", 3: "ring", 4: "pinky"}
OPEN_MIDI = {"E": 40, "A": 45, "D": 50}
NATURAL_PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
HEADER = re.compile(r"RUNG (\d{2}) OF 13 - ([A-G](?:B)?) MAJOR( \(OCTAVE\))? - ROOT ON LOW E FRET (\d+) - FRAME (\d+)-(\d+)")
PDF_HEADER = re.compile(r"(\d{2})  ([A-G](?:B)?) MAJOR( \(OCTAVE\))?")
TAB_PREFIXES = ("e  ", "B  ", "G  ", "D  ", "A  ", "E  ")
TXT_CELL_LABEL = "40-note cell: five ascending four-note groups, repeat the octave root at the turn, then five descending groups."
TXT_FINISH = "Finish on the low root, release pressure, and move the entire frame one fret in the route direction."
PDF_FINISH = "Return to the low root; release pressure; move the entire frame one fret."
PDF_PICK = "Four notes per beat - continuous alternate picking"


class SourceError(ValueError):
    """Pinned source, structural, or musical source assertion failed."""


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def read_pinned(root: Path, spec: tuple[str, str, int]) -> bytes:
    path, digest, size = spec
    target = root / path
    try:
        resolved = target.resolve(strict=True)
    except FileNotFoundError as exc:
        raise SourceError(f"missing pinned input: {path}") from exc
    if target.is_symlink() or not resolved.is_relative_to(root) or not resolved.is_file():
        raise SourceError(f"unsafe pinned input: {path}")
    raw = target.read_bytes()
    if len(raw) != size or sha(raw) != digest:
        raise SourceError(f"pinned input drift: {path}")
    return raw


def split_cells(line: str, prefix: str) -> list[str]:
    if not line.startswith(prefix + "|") or not line.endswith("|"):
        raise SourceError(f"printed row prefix/boundary: {prefix!r}")
    cells = line[len(prefix) + 1:-1].split("|")
    if len(cells) != 10 or any(len(cell) != 12 for cell in cells):
        raise SourceError(f"printed row cell count/width: {prefix!r}")
    return cells


def note_pc(name: str) -> int:
    if not re.fullmatch(r"[A-G][b#]?", name):
        raise SourceError(f"invalid source tone spelling: {name}")
    return (NATURAL_PC[name[0]] + (1 if name.endswith("#") else -1 if name.endswith("b") else 0)) % 12


def parse_sources(txt_raw: bytes, pdf_raw: bytes) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    try:
        lines = txt_raw.decode("utf-8").splitlines()
        reader = PdfReader(BytesIO(pdf_raw), strict=True)
        pages = [(page.extract_text() or "").splitlines() for page in reader.pages]
    except Exception as exc:
        raise SourceError("TXT/PDF decode failure") from exc
    if len(lines) != 265 or len(pages) != 7 or [len(page) for page in pages] != [58, 105, 47, 47, 47, 47, 38]:
        raise SourceError("Level16 source line/page coverage drift")
    if lines[:2] != ["SCALE EXERCISES - SECTION II, LEVEL 16",
                     "MAJOR SCALE FOUR-NOTE ROLLING SEQUENCE - ONE-OCTAVE NECK LADDER: A TO A"]:
        raise SourceError("TXT workbook heading drift")
    if pages[0][:2] != ["Scale Exercises - Section II, Level 16",
                        "Major Scale Four-Note Rolling Sequence: One-Octave Neck Ladder"]:
        raise SourceError("PDF workbook heading drift")
    if [page[-1] for page in pages] != [f"Page {n} of 7" for n in range(1, 8)]:
        raise SourceError("PDF page footer drift")
    if lines[31] != "UP:   1-2-3-4 | 2-3-4-5 | 3-4-5-6 | 4-5-6-7 | 5-6-7-8" or lines[32] != "DOWN: 8-7-6-5 | 7-6-5-4 | 6-5-4-3 | 5-4-3-2 | 4-3-2-1":
        raise SourceError("TXT rolling-group guidance drift")
    if lines[47] != "UP:   A(5) > Bb(6) > B(7) > C(8) > Db(9) > D(10) > Eb(11) > E(12) > F(13) > Gb(14) > G(15) > Ab(16) > A(17)" or lines[48] != "DOWN: A(17) > Ab(16) > G(15) > Gb(14) > F(13) > E(12) > Eb(11) > D(10) > Db(9) > C(8) > B(7) > Bb(6) > A(5)":
        raise SourceError("TXT key-route guidance drift")
    if pages[1][1:3] != ["Ascending route: complete one 40-note rolling cell, then move the frame +1 fret",
                           "Descending route: use the same cards in reverse order and move -1 fret"]:
        raise SourceError("PDF key-route guidance drift")
    if pages[1][3:8] != ["Rung", "Key", "Low-E root", "Frame", "Scale tones (degrees 1-7)"]:
        raise SourceError("PDF route-table heading drift")
    if pages[0][19:27] != lines[64:72]:
        raise SourceError("PDF worked example/TXT Set1 disagreement")
    cards: list[dict[str, Any]] = []
    for rung in range(1, 14):
        start = 61 + 14 * (rung - 1)  # zero-based index of the 12-line TXT body
        if lines[start - 1] != "=" * 144 or lines[start + 12] != "" or lines[start + 13] != "=" * 144:
            raise SourceError(f"TXT rung boundary: {rung}")
        txt_body = lines[start:start + 12]
        pdf_page = 3 + (rung - 1) // 3 if rung <= 12 else 7
        pdf_start = 3 + 14 * ((rung - 1) % 3) if rung <= 12 else 2
        pdf_block = pages[pdf_page - 1][pdf_start:pdf_start + 14]
        if len(pdf_block) != 14:
            raise SourceError(f"PDF rung block loss: {rung}")
        map_row = pages[1][8 + 5 * (rung - 1):8 + 5 * rung]
        if len(map_row) != 5:
            raise SourceError(f"PDF route-map row loss: {rung}")
        cards.append({"rung": rung, "txt_body": txt_body, "pdf_block": pdf_block,
                      "pdf_route_map_row": map_row,
                      "source_refs": {"txt": f"L16-TXT1-{start + 1}-{start + 12}",
                                      "pdf_card": f"L16-PDF1-p{pdf_page}-l{pdf_start + 1}-{pdf_start + 14}",
                                      "pdf_route_map": f"L16-PDF1-p2-l{9 + 5 * (rung - 1)}-{13 + 5 * (rung - 1)}"}})
    if [r["rung"] for r in cards] != list(range(1, 14)):
        raise SourceError("duplicate/out-of-order rung")
    guidance = {"txt_intro_lines_1_60": lines[:60], "txt_after_cards_lines_243_265": lines[242:],
                "pdf_page1_non_card_lines": pages[0][:19] + pages[0][27:],
                "pdf_page2_after_route_map_lines": pages[1][73:],
                "pdf_page7_after_card_lines": pages[6][16:]}
    if lines[243:247] != ["FULL ROUND-TRIP CHALLENGE",
                            "Play rungs 01-13, reverse after the fret-17 A-major cell, and return through rungs 12-01.",
                            "Do not replay rung 13 at the turn. The route contains 25 cells x 40 notes = 1,000 picked notes.",
                            "Say each key name aloud and repeat the complete trip with the opposite starting stroke."]:
        raise SourceError("TXT round-trip guidance drift")
    if "The 25-cell trip contains exactly 1,000 picked notes." not in pages[6][22]:
        raise SourceError("PDF round-trip note count drift")
    return cards, guidance


def normalize_card(card: dict[str, Any]) -> dict[str, Any]:
    rung = card.get("rung")
    if not isinstance(rung, int) or not 1 <= rung <= 13:
        raise SourceError("invalid rung number")
    root = rung + 4
    key = KEYS[rung - 1]
    expected_tones = TONES[rung - 1]
    body = card.get("txt_body")
    pdf = card.get("pdf_block")
    route_row = card.get("pdf_route_map_row")
    if not isinstance(body, list) or len(body) != 12 or not isinstance(pdf, list) or len(pdf) != 14:
        raise SourceError(f"rung card line loss: {rung}")
    h = HEADER.fullmatch(body[0])
    ph = PDF_HEADER.fullmatch(pdf[0])
    octave = " (OCTAVE)" if rung == 13 else ""
    if h is None or (h.group(1), h.group(2), h.group(3) or "", h.group(4), h.group(5), h.group(6)) != (
        f"{rung:02d}", key.upper(), octave, str(root), str(root - 1), str(root + 2)):
        raise SourceError(f"TXT rung/key/root/frame conflict: {rung}")
    if ph is None or ph.groups() != (f"{rung:02d}", key.upper(), octave or None):
        raise SourceError(f"PDF rung/key conflict: {rung}")
    if body[1:3] != [f"Scale tones: {expected_tones}", TXT_CELL_LABEL] or body[11] != TXT_FINISH:
        raise SourceError(f"TXT tone/cell guidance conflict: {rung}")
    if pdf[1:4] != [f"ROOT E{root}  |  FRAME {root - 1}-{root + 2}",
                    body[1], "40-NOTE / 10-GROUP CELL"] or pdf[4:12] != body[3:11] or pdf[12:14] != [PDF_FINISH, PDF_PICK]:
        raise SourceError(f"PDF/TXT rung card conflict: {rung}")
    if route_row != [f"{rung:02d}", f"{key} major{(' (octave)' if rung == 13 else '')}",
                     f"fret {root}", f"{root - 1}-{root + 2}", " ".join(expected_tones.split()[:7])]:
        raise SourceError(f"PDF route-map/rung conflict: {rung}")
    degree_cells = split_cells(body[3], "Deg")
    finger_cells = split_cells(body[4], "Fng")
    tab_cells = {string: split_cells(body[5 + index], TAB_PREFIXES[index])
                 for index, string in enumerate(STRINGS)}
    tones = expected_tones.split()
    groups: list[dict[str, Any]] = []
    for group_index, expected_degrees in enumerate(GROUPS):
        notes: list[dict[str, Any]] = []
        for column, degree in enumerate(expected_degrees):
            pos = 3 * column
            if degree_cells[group_index][pos:pos + 3] != f"{degree}--":
                raise SourceError(f"degree order/alignment: {rung}:{group_index + 1}:{column + 1}")
            finger = FINGERS[degree - 1]
            if finger_cells[group_index][pos:pos + 3] != f"{finger}--":
                raise SourceError(f"finger order/alignment: {rung}:{group_index + 1}:{column + 1}")
            found: list[tuple[str, int]] = []
            for string in STRINGS:
                token = tab_cells[string][group_index][pos:pos + 3]
                if token == "---":
                    continue
                if re.fullmatch(r"(?:[1-9]--|1[0-9]-)", token) is None:
                    raise SourceError(f"TAB fret token/alignment: {rung}:{group_index + 1}:{column + 1}")
                found.append((string, int(token.rstrip("-"))))
            if len(found) != 1:
                raise SourceError(f"TAB column note count: {rung}:{group_index + 1}:{column + 1}")
            string, fret = found[0]
            expected_string = SCALE_STRING[degree - 1]
            expected_fret = root + (-1 if degree in (3, 6) else 1 if degree == 7 else 2 if degree in (2, 5, 8) else 0)
            if (string, fret) != (expected_string, expected_fret):
                raise SourceError(f"TAB string/fret conflict: {rung}:{group_index + 1}:{column + 1}")
            if (OPEN_MIDI[string] + fret) % 12 != note_pc(tones[degree - 1]):
                raise SourceError(f"scale tone/pitch conflict: {rung}:{group_index + 1}:{column + 1}")
            ordinal = group_index * 4 + column + 1
            notes.append({"ordinal_in_cell": ordinal, "degree": degree, "tone": tones[degree - 1],
                          "finger_digit": finger, "finger_name": FINGER_NAMES[finger],
                          "string": string, "fret": fret, "printed_column": pos,
                          "pick_for_down_start": "D" if ordinal % 2 else "U",
                          "pick_for_up_start": "U" if ordinal % 2 else "D",
                          "onset_q": None, "duration_q": None})
        groups.append({"group_number": group_index + 1,
                       "direction": "up" if group_index < 5 else "down",
                       "degrees": list(expected_degrees), "printed_deg_cell": degree_cells[group_index],
                       "printed_fng_cell": finger_cells[group_index],
                       "printed_tab_cells_high_to_low": {s: tab_cells[s][group_index] for s in STRINGS},
                       "notes": notes})
    for start, end in ((0, 5), (5, 10)):
        for index in range(start + 1, end):
            if groups[index - 1]["degrees"][1:] != groups[index]["degrees"][:3]:
                raise SourceError(f"rolling three-note overlap: {rung}:{index + 1}")
    if groups[4]["notes"][-1]["degree"] != 8 or groups[5]["notes"][0]["degree"] != 8:
        raise SourceError(f"repeated octave-root turn: {rung}")
    if groups[0]["notes"][0]["degree"] != 1 or groups[-1]["notes"][-1]["degree"] != 1:
        raise SourceError(f"low-root return: {rung}")
    return {"rung": rung, "source_local_key": f"L16-rung{rung:02d}", "key": key,
            "root_string": "E", "root_fret": root, "frame_frets": [root - 1, root + 2],
            "scale_tones_degrees_1_to_8": tones, "source_refs": card["source_refs"],
            "raw_txt_card": body, "raw_pdf_card": pdf, "raw_pdf_route_map_row": route_row,
            "groups": groups, "note_count": 40, "group_count": 10,
            "shift_after_complete_cell_only": True, "within_cell_shift": False,
            "canonical_item_id": None, "canonical_variant_id": None,
            "onset_q": None, "duration_q": None, "note_per_click": None, "fixed_bpm": None,
            "runtime_eligible": False, "imported": False, "admitted": False}


def assemble(cards: list[dict[str, Any]], guidance: dict[str, Any]) -> dict[str, Any]:
    if len(cards) != 13 or [card.get("rung") for card in cards] != list(range(1, 14)):
        raise SourceError("missing/duplicate/out-of-order rung")
    records = [normalize_card(card) for card in cards]
    if len({record["source_local_key"] for record in records}) != 13:
        raise SourceError("duplicate source-local rung key")
    up = list(range(1, 14))
    down = list(range(12, 0, -1))
    trip = up + down
    if len(trip) != 25 or sum(records[n - 1]["note_count"] for n in trip) != 1000:
        raise SourceError("round-trip coverage/count conflict")
    return {"schema": "fathom-level016-whole-detached-source-candidate.1", "wbs_id": "2.3.1.1.1",
            "level": 16, "classification": "source_bound_non_admitted_candidate",
            "source_authority": {"txt": {"path": TXT[0], "sha256": TXT[1], "bytes": TXT[2]},
                                 "pdf": {"path": PDF[0], "sha256": PDF[1], "bytes": PDF[2], "pages": 7}},
            "counts": {"rungs": 13, "groups_per_rung": 10, "notes_per_rung": 40,
                       "groups_in_source_cards": 130, "notes_in_source_cards": 520,
                       "round_trip_cells": 25, "round_trip_note_occurrences": 1000},
            "source_guidance": guidance, "pick_start_options": ["D", "U"],
            "tempo_and_grouping_are_source_guidance_only": True,
            "ascending_route": up, "descending_route_after_high_a": down,
            "round_trip_rung_order": trip, "reverse_after_rung": 13,
            "frame_shift_after_cell_frets": {"ascending_except_turn": 1, "descending": -1},
            "records": records, "canonical_schema_validated": False,
            "runtime_eligible": False, "imported": False, "admitted": False,
            "whole_workbook_complete": False,
            "required_decisions": ["Stable canonical identities and lineage", "Authorized note timing and meter for runtime representation",
                                   "Curriculum/musical review and canonical admission"]}


def build(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve(strict=True)
    git_root = Path(subprocess.check_output(["git", "-C", str(root), "rev-parse", "--show-toplevel"], text=True).strip()).resolve()
    if root != git_root:
        raise SourceError("root must be the sole Git checkout top level")
    cards, guidance = parse_sources(read_pinned(root, TXT), read_pinned(root, PDF))
    return assemble(cards, guidance)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        root = ROOT.resolve(strict=True)
        output = args.output if args.output.is_absolute() else root / args.output
        allowed = (root / BUILD_REL).resolve(strict=False)
        if output.parent.resolve(strict=False) != allowed or output.exists() or output.is_symlink() or output.suffix != ".json":
            raise SourceError("output must be a new JSON file in the P11 Level16 Build lane")
        raw = (json.dumps(build(root), ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("xb") as stream:
            stream.write(raw)
    except (SourceError, OSError, subprocess.CalledProcessError) as exc:
        parser.exit(2, f"LEVEL16 SOURCE STOP: {exc}\n")
    print(f"LEVEL16 SOURCE PASS {output} rungs=13 groups=130 notes=520 admitted=false sha256={sha(raw)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
