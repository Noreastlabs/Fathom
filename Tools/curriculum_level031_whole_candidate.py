#!/usr/bin/env python3
"""Build a pinned, non-admitted Level 31 major-pentatonic source candidate."""

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
BUILD_REL = Path("Build/parallel-11/2.3.1.1.1-level031-whole-r01")
TXT = ("Notes/music/guitar project/TXT version/Scale_Exercises_Section_IV_Level_31_Major_Pentatonic_Two_Octave_Six_String_Neck_Ladder.txt",
       "491359a3d7227f4887eb2486cdaf5827ef85a7487ea57c7b21d089ad6be3bfa7", 17681)
PDF = ("Notes/music/guitar project/PDF version/Scale_Exercises_Section_IV_Level_31_Major_Pentatonic_Two_Octave_Six_String_Neck_Ladder.pdf",
       "1f1cbc0f1d8a996f5239769abce00f94c4267e5504e6edbb72112210a12f137e", 21059)
KEYS = ("A", "Bb", "B", "C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A")
TONES = (
    "A B C# E F# A | B C# E F# A", "Bb C D F G Bb | C D F G Bb",
    "B C# D# F# G# B | C# D# F# G# B", "C D E G A C | D E G A C",
    "Db Eb F Ab Bb Db | Eb F Ab Bb Db", "D E F# A B D | E F# A B D",
    "Eb F G Bb C Eb | F G Bb C Eb", "E F# G# B C# E | F# G# B C# E",
    "F G A C D F | G A C D F", "Gb Ab Bb Db Eb Gb | Ab Bb Db Eb Gb",
    "G A B D E G | A B D E G", "Ab Bb C Eb F Ab | Bb C Eb F Ab",
    "A B C# E F# A | B C# E F# A",
)
DEGREES_UP = (1, 2, 3, 5, 6, 1, 2, 3, 5, 6, 1)
DEGREES = DEGREES_UP + tuple(reversed(DEGREES_UP))
FINGERS_UP = (2, 4, 1, 4, 1, 4, 1, 3, 2, 4, 2)
FINGERS = FINGERS_UP + tuple(reversed(FINGERS_UP))
STRINGS_UP = ("E", "E", "A", "A", "D", "D", "G", "G", "B", "B", "e")
STRINGS = STRINGS_UP + tuple(reversed(STRINGS_UP))
FRET_OFFSETS_UP = (0, 2, -1, 2, -1, 2, -1, 1, 0, 2, 0)
FRET_OFFSETS = FRET_OFFSETS_UP + tuple(reversed(FRET_OFFSETS_UP))
PRINTED_STRINGS = ("e", "B", "G", "D", "A", "E")
TAB_PREFIXES = ("e  ", "B  ", "G  ", "D  ", "A  ", "E  ")
OPEN_MIDI = {"E": 40, "A": 45, "D": 50, "G": 55, "B": 59, "e": 64}
NATURAL_PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
FINGER_NAMES = {1: "index", 2: "middle", 3: "ring", 4: "pinky"}
HEADER = re.compile(r"RUNG (\d{2}) OF 13 - ([A-G]B?) MAJOR PENTATONIC( - OCTAVE)? - ROOT ON LOW E FRET (\d+) - FRAME (\d+)-(\d+)")
PDF_HEADER = re.compile(r"(\d{2})  ([A-G]B?) MAJOR PENTATONIC( - OCTAVE)?")
TXT_CELL = "22-note cell: low root to high root, repeat the high root, then return to the low root."
TXT_FINISH = "Return to the low root, release pressure, and move the entire frame one fret in the route direction."
PDF_FINISH = "Return to the low root; release pressure; move the entire frame one fret."


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


def tone_pc(name: str) -> int:
    if not re.fullmatch(r"[A-G][b#]?", name):
        raise SourceError(f"invalid source tone spelling: {name}")
    return (NATURAL_PC[name[0]] + (1 if name.endswith("#") else -1 if name.endswith("b") else 0)) % 12


def columns(line: str, prefix: str) -> list[str]:
    if not line.startswith(prefix + "|") or not line.endswith("|"):
        raise SourceError(f"printed row prefix/boundary: {prefix!r}")
    interior = line[len(prefix) + 1:-1]
    if len(interior) != 66 or "|" in interior:
        raise SourceError(f"printed 22-column width: {prefix!r}")
    return [interior[i:i + 3] for i in range(0, 66, 3)]


def parse_sources(txt_raw: bytes, pdf_raw: bytes) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    try:
        lines = txt_raw.decode("utf-8").splitlines()
        reader = PdfReader(BytesIO(pdf_raw), strict=True)
        pages = [(page.extract_text() or "").splitlines() for page in reader.pages]
    except Exception as exc:
        raise SourceError("TXT/PDF decode failure") from exc
    if len(lines) != 259 or len(pages) != 7 or [len(page) for page in pages] != [56, 103, 47, 47, 47, 47, 45]:
        raise SourceError("Level31 source line/page coverage drift")
    if lines[:2] != ["SCALE EXERCISES - SECTION IV, LEVEL 31",
                     "MAJOR PENTATONIC TWO-OCTAVE SIX-STRING NECK LADDER: A TO A"]:
        raise SourceError("TXT workbook heading drift")
    if pages[0][:3] != ["Scale Exercises - Section IV, Level 31",
                        "The pentatonic section still starts on A.",
                        "Major Pentatonic Two-Octave Six-String Neck Ladder: A to A"]:
        raise SourceError("PDF workbook heading drift")
    if [page[-1] for page in pages] != [f"Page {n} of 7" for n in range(1, 8)]:
        raise SourceError("PDF page footer drift")
    if lines[14:17] != ["Degrees per octave: 1 2 3 5 6",
                         "Intervals: whole - whole - minor third - whole - minor third",
                         "The omitted degrees 4 and 7 remain absent in both octaves."]:
        raise SourceError("TXT pentatonic formula drift")
    if lines[28:30] != ["Ascending note counts by string: 2 - 2 - 2 - 2 - 2 - 1.",
                         "Descending note counts by string: 1 - 2 - 2 - 2 - 2 - 2."]:
        raise SourceError("TXT string distribution drift")
    if lines[42:44] != ["UP:   A(5) > Bb(6) > B(7) > C(8) > Db(9) > D(10) > Eb(11) > E(12) > F(13) > Gb(14) > G(15) > Ab(16) > A(17)",
                         "DOWN: A(17) > Ab(16) > G(15) > Gb(14) > F(13) > E(12) > Eb(11) > D(10) > Db(9) > C(8) > B(7) > Bb(6) > A(5)"]:
        raise SourceError("TXT key-route guidance drift")
    if pages[1][1:3] != ["Ascending: complete one 22-note cell, then move the frame +1 fret",
                           "Descending: reverse the cards and move -1 fret"]:
        raise SourceError("PDF key-route guidance drift")
    if pages[1][3:8] != ["Rung", "Key", "Low-E root", "Frame", "Scale tones (degrees 1, 2, 3, 5, 6)"]:
        raise SourceError("PDF route-table heading drift")
    if pages[0][19:27] != lines[56:64]:
        raise SourceError("PDF worked TAB/TXT rung1 disagreement")
    if lines[234:241] != ["FULL ROUND-TRIP CHALLENGE",
                            "1. Start with A major pentatonic at low-E fret 5.",
                            "2. Play all 13 cells without restarting the alternate-picking cycle.",
                            "3. Reverse after the fret-17 cell and return through rungs 12-01.",
                            "4. Name each key and sing or say 1-2-3-5-6 through both octaves.",
                            "5. Repeat the route with the opposite starting stroke.",
                            "One complete route contains 25 cells x 22 notes = 550 picked notes."]:
        raise SourceError("TXT round-trip guidance drift")
    if pages[1][100] != "25 cells x 22 notes = 550 picked notes." or pages[6][28] != "550 picked notes per complete round trip.":
        raise SourceError("PDF round-trip count drift")
    cards: list[dict[str, Any]] = []
    for rung in range(1, 14):
        start = 53 + 14 * (rung - 1)  # zero-based index of the 12-line TXT card
        if lines[start - 1] != "=" * 122 or lines[start + 12] != "":
            raise SourceError(f"TXT rung boundary: {rung}")
        if rung < 13 and lines[start + 13] != "=" * 122:
            raise SourceError(f"TXT next-rung boundary: {rung}")
        txt_body = lines[start:start + 12]
        pdf_page = 3 + (rung - 1) // 3 if rung <= 12 else 7
        pdf_start = 3 + 14 * ((rung - 1) % 3) if rung <= 12 else 3
        pdf_block = pages[pdf_page - 1][pdf_start:pdf_start + 14]
        if len(pdf_block) != 14:
            raise SourceError(f"PDF rung block loss: {rung}")
        map_row = pages[1][8 + 5 * (rung - 1):8 + 5 * rung]
        if len(map_row) != 5:
            raise SourceError(f"PDF route-map row loss: {rung}")
        cards.append({"rung": rung, "txt_body": txt_body, "pdf_block": pdf_block,
                      "pdf_route_map_row": map_row,
                      "source_refs": {"txt": f"L31-TXT1-{start + 1}-{start + 12}",
                                      "pdf_card": f"L31-PDF1-p{pdf_page}-l{pdf_start + 1}-{pdf_start + 14}",
                                      "pdf_route_map": f"L31-PDF1-p2-l{9 + 5 * (rung - 1)}-{13 + 5 * (rung - 1)}"}})
    card_tones = lines[54]
    pdf_worked = pages[0][17]
    if card_tones != "Scale tones across two octaves: A B C# E F# A | B C# E F# A" or pdf_worked != (
        "Scale notes: A B C# E F# | A B C# E F# A. The high root is repeated at the turn."):
        raise SourceError("source separator variant drift")
    pdf_card_tones = pages[2][5]
    if pdf_card_tones != "Notes: A  B  C#  E  F#  A | B  C#  E  F#  A":
        raise SourceError("PDF card separator variant drift")
    expected_tone_order = TONES[0].replace("|", "").split()
    txt_tone_order = card_tones.split(": ", 1)[1].replace("|", "").split()
    pdf_card_tone_order = pdf_card_tones.split(": ", 1)[1].replace("|", "").split()
    pdf_worked_tone_order = pdf_worked.split(": ", 1)[1].split(". The high root", 1)[0].replace("|", "").split()
    if txt_tone_order != expected_tone_order or pdf_card_tone_order != expected_tone_order or pdf_worked_tone_order != expected_tone_order:
        raise SourceError("worked/card tone order disagreement")
    guidance = {"txt_intro_lines_1_52": lines[:52], "txt_after_cards_lines_235_259": lines[234:],
                "pdf_page1_non_tab_lines": pages[0][:19] + pages[0][27:],
                "pdf_page2_after_route_map_lines": pages[1][73:],
                "pdf_page7_after_card_lines": pages[6][17:]}
    discrepancy = [{"kind": "octave_separator_position", "status": "pending_curriculum_review",
                    "txt_card": {"ref": "L31-TXT1-55", "text": card_tones, "tokens_before_separator": 6},
                    "pdf_card": {"ref": "L31-PDF1-p3-l6", "text": pdf_card_tones, "tokens_before_separator": 6},
                    "pdf_worked_example": {"ref": "L31-PDF1-p1-l18", "text": pdf_worked, "tokens_before_separator": 5},
                    "sounding_tone_order_same": True,
                    "resolution": None}]
    return cards, guidance, discrepancy


def normalize_card(card: dict[str, Any]) -> dict[str, Any]:
    rung = card.get("rung")
    if not isinstance(rung, int) or not 1 <= rung <= 13:
        raise SourceError("invalid rung number")
    root = rung + 4
    key = KEYS[rung - 1]
    expected_tones = TONES[rung - 1]
    body = card.get("txt_body")
    pdf = card.get("pdf_block")
    map_row = card.get("pdf_route_map_row")
    if not isinstance(body, list) or len(body) != 12 or not isinstance(pdf, list) or len(pdf) != 14:
        raise SourceError(f"rung card line loss: {rung}")
    h = HEADER.fullmatch(body[0])
    ph = PDF_HEADER.fullmatch(pdf[0])
    octave = " - OCTAVE" if rung == 13 else ""
    if h is None or (h.group(1), h.group(2), h.group(3) or "", h.group(4), h.group(5), h.group(6)) != (
        f"{rung:02d}", key.upper(), octave, str(root), str(root - 1), str(root + 2)):
        raise SourceError(f"TXT rung/key/root/frame conflict: {rung}")
    if ph is None or ph.groups() != (f"{rung:02d}", key.upper(), octave or None):
        raise SourceError(f"PDF rung/key conflict: {rung}")
    if body[1:3] != [f"Scale tones across two octaves: {expected_tones}", TXT_CELL] or body[11] != TXT_FINISH:
        raise SourceError(f"TXT tone/cell/shift guidance conflict: {rung}")
    tokens = expected_tones.replace(" | ", " ").split()
    printed_pdf_tones = "Notes: " + "  ".join(tokens[:6]) + " | " + "  ".join(tokens[6:])
    if pdf[1:4] != [f"ROOT E{root}  |  FRAME {root - 1}-{root + 2}",
                    printed_pdf_tones, "22-NOTE TWO-OCTAVE CELL"] or pdf[4:12] != body[3:11] or pdf[12:14] != [PDF_FINISH, "D-start and U-start"]:
        raise SourceError(f"PDF/TXT rung card conflict: {rung}")
    if map_row != [f"{rung:02d}", f"{key} major pentatonic{(' - octave' if rung == 13 else '')}",
                   f"fret {root}", f"{root - 1}-{root + 2}", " ".join(tokens[:5])]:
        raise SourceError(f"PDF route-map/rung conflict: {rung}")
    deg_cols = columns(body[3], "Deg")
    finger_cols = columns(body[4], "Fng")
    tab_cols = {string: columns(body[5 + index], TAB_PREFIXES[index])
                for index, string in enumerate(PRINTED_STRINGS)}
    notes: list[dict[str, Any]] = []
    for index in range(22):
        degree, finger, string, offset = DEGREES[index], FINGERS[index], STRINGS[index], FRET_OFFSETS[index]
        if deg_cols[index] != f"{degree}--" or finger_cols[index] != f"{finger}--":
            raise SourceError(f"degree/finger order conflict: {rung}:{index + 1}")
        found: list[tuple[str, int]] = []
        for row_string in PRINTED_STRINGS:
            token = tab_cols[row_string][index]
            if token == "---":
                continue
            if re.fullmatch(r"(?:[1-9]--|1[0-9]-)", token) is None:
                raise SourceError(f"TAB token/alignment: {rung}:{index + 1}")
            found.append((row_string, int(token.rstrip("-"))))
        if len(found) != 1:
            raise SourceError(f"TAB column note count: {rung}:{index + 1}")
        if found[0] != (string, root + offset):
            raise SourceError(f"TAB string/fret conflict: {rung}:{index + 1}")
        tone = tokens[index if index < 11 else 21 - index]
        if (OPEN_MIDI[string] + root + offset) % 12 != tone_pc(tone):
            raise SourceError(f"pentatonic tone/pitch conflict: {rung}:{index + 1}")
        notes.append({"ordinal_in_cell": index + 1, "direction": "up" if index < 11 else "down",
                      "degree": degree, "tone": tone, "finger_digit": finger,
                      "finger_name": FINGER_NAMES[finger], "string": string,
                      "fret": root + offset, "printed_column": 3 * index,
                      "pick_for_down_start": "D" if index % 2 == 0 else "U",
                      "pick_for_up_start": "U" if index % 2 == 0 else "D",
                      "onset_q": None, "duration_q": None})
    if [n["string"] for n in notes[:11]] != list(STRINGS_UP) or [n["string"] for n in notes[11:]] != list(reversed(STRINGS_UP)):
        raise SourceError(f"six-string distribution conflict: {rung}")
    if (notes[0]["degree"], notes[5]["degree"], notes[10]["degree"],
            notes[11]["degree"], notes[16]["degree"], notes[21]["degree"]) != (1, 1, 1, 1, 1, 1):
        raise SourceError(f"low/middle/high-root order conflict: {rung}")
    if (notes[10]["tone"], notes[10]["string"], notes[10]["fret"]) != (
            notes[11]["tone"], notes[11]["string"], notes[11]["fret"]):
        raise SourceError(f"repeated high-root turn conflict: {rung}")
    return {"rung": rung, "source_local_key": f"L31-rung{rung:02d}", "key": key,
            "root_string": "E", "root_fret": root, "frame_frets": [root - 1, root + 2],
            "degrees_per_octave": [1, 2, 3, 5, 6], "scale_tones_two_octaves": tokens,
            "source_refs": card["source_refs"], "raw_txt_card": body,
            "raw_pdf_card": pdf, "raw_pdf_route_map_row": map_row,
            "printed_deg_row": body[3], "printed_fng_row": body[4],
            "printed_tab_rows_high_to_low": body[5:11],
            "notes": notes, "note_count": 22, "up_note_count": 11, "down_note_count": 11,
            "shift_after_complete_cell_only": True, "within_cell_shift": False,
            "canonical_item_id": None, "canonical_variant_id": None,
            "onset_q": None, "duration_q": None, "note_per_click": None, "fixed_bpm": None,
            "runtime_eligible": False, "imported": False, "admitted": False}


def assemble(cards: list[dict[str, Any]], guidance: dict[str, Any], discrepancies: list[dict[str, Any]]) -> dict[str, Any]:
    if len(cards) != 13 or [card.get("rung") for card in cards] != list(range(1, 14)):
        raise SourceError("missing/duplicate/out-of-order rung")
    records = [normalize_card(card) for card in cards]
    if len({record["source_local_key"] for record in records}) != 13:
        raise SourceError("duplicate source-local rung key")
    if len(discrepancies) != 1 or discrepancies[0].get("kind") != "octave_separator_position" or discrepancies[0].get("resolution") is not None:
        raise SourceError("source discrepancy lost or falsely resolved")
    up = list(range(1, 14))
    down = list(range(12, 0, -1))
    trip = up + down
    if len(trip) != 25 or sum(records[n - 1]["note_count"] for n in trip) != 550:
        raise SourceError("round-trip coverage/count conflict")
    return {"schema": "fathom-level031-whole-detached-source-candidate.1", "wbs_id": "2.3.1.1.1",
            "level": 31, "classification": "source_bound_non_admitted_candidate",
            "source_authority": {"txt": {"path": TXT[0], "sha256": TXT[1], "bytes": TXT[2]},
                                 "pdf": {"path": PDF[0], "sha256": PDF[1], "bytes": PDF[2], "pages": 7}},
            "counts": {"rungs": 13, "notes_per_rung": 22, "notes_in_source_cards": 286,
                       "round_trip_cells": 25, "round_trip_note_occurrences": 550},
            "source_guidance": guidance, "source_discrepancies": discrepancies,
            "pick_start_options": ["D", "U"], "tempo_and_picking_are_source_guidance_only": True,
            "ascending_route": up, "descending_route_after_high_a": down,
            "round_trip_rung_order": trip, "reverse_after_rung": 13,
            "frame_shift_after_cell_frets": {"ascending_except_turn": 1, "descending": -1},
            "records": records, "canonical_schema_validated": False,
            "runtime_eligible": False, "imported": False, "admitted": False,
            "whole_workbook_complete": False,
            "required_decisions": ["Stable canonical identities and lineage", "Authorized note timing/meter for runtime representation",
                                   "Curriculum resolution of the worked-example octave separator",
                                   "Curriculum/musical review and canonical admission"]}


def build(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve(strict=True)
    git_root = Path(subprocess.check_output(["git", "-C", str(root), "rev-parse", "--show-toplevel"], text=True).strip()).resolve()
    if root != git_root:
        raise SourceError("root must be the sole Git checkout top level")
    return assemble(*parse_sources(read_pinned(root, TXT), read_pinned(root, PDF)))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        root = ROOT.resolve(strict=True)
        output = args.output if args.output.is_absolute() else root / args.output
        allowed = (root / BUILD_REL).resolve(strict=False)
        if output.parent.resolve(strict=False) != allowed or output.exists() or output.is_symlink() or output.suffix != ".json":
            raise SourceError("output must be a new JSON file in the P11 Level31 Build lane")
        raw = (json.dumps(build(root), ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("xb") as stream:
            stream.write(raw)
    except (SourceError, OSError, subprocess.CalledProcessError) as exc:
        parser.exit(2, f"LEVEL31 SOURCE STOP: {exc}\n")
    print(f"LEVEL31 SOURCE PASS {output} rungs=13 notes=286 admitted=false sha256={sha(raw)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
