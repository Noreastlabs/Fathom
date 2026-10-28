#!/usr/bin/env python3
"""Detached literal musical cells from the original Level 83–85 workbook pairs.

This source aid allocates no canonical identity and admits nothing to the app.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "Build/parallel-06/2.3-levels-083-085-r01"
SOURCES = {
    83: {
        "txt": ("Notes/music/guitar project/TXT version/Guitar_Exercises_Section_XI_Level_83_Melody_Harmonization_Chord_Substitution_Reharmonization_and_Fixed_Top_Line_Control.txt", 1908, "12561dfc8c1d81b710cb2d429b52e2d9574ea5fd7bfa65d0bf1f1b575682bb85"),
        "pdf": ("Notes/music/guitar project/PDF version/Guitar_Exercises_Section_XI_Level_83_Melody_Harmonization_Chord_Substitution_Reharmonization_and_Fixed_Top_Line_Control.pdf", 48628, "3571f063bdafa8a3acb9a52f542d6f490516d75e325f55ea29915111659e5c5c"),
        "page_count": 20,
    },
    84: {
        "txt": ("Notes/music/guitar project/TXT version/Guitar_Exercises_Section_XI_Level_84_Complete_Solo_Guitar_Arrangement_Independent_Voices_Walking_Bass_Reharmonization_Dynamics_and_Performance_Capstone.txt", 1456, "2f4b612882dddd7a8766995747096166049fd0843492ec91ed673be4007e15ba"),
        "pdf": ("Notes/music/guitar project/PDF version/Guitar_Exercises_Section_XI_Level_84_Complete_Solo_Guitar_Arrangement_Independent_Voices_Walking_Bass_Reharmonization_Dynamics_and_Performance_Capstone.pdf", 42244, "c1b2eea466ed612ecc7ffe05ec2f67b286d5ae151f028b8d394c63621335821c"),
        "page_count": 15,
    },
    85: {
        "txt": ("Notes/music/guitar project/TXT version/Guitar_Exercises_Section_XII_Level_85_Pocket_Note_Length_Muting_Attack_Placement_and_Drum_Bass_Lock.txt", 1534, "8ca7ce364dac61adae9cbcf2dfd4cb800a10107523dc74e23014585e0cee33f7"),
        "pdf": ("Notes/music/guitar project/PDF version/Guitar_Exercises_Section_XII_Level_85_Pocket_Note_Length_Muting_Attack_Placement_and_Drum_Bass_Lock.pdf", 41449, "9ea3d4547e28ac2feb30659ee9d45af4ea84102d9f9a23837234ea37b6951323"),
        "page_count": 15,
    },
}
NOTE_PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
ROLE_PC = {"root": 0, "b3": 3, "3": 4, "5": 7, "b7": 10, "7": 11}
NOTE = re.compile(r"[A-G](?:#|b)?")
CHORD = re.compile(r"([A-G])(?:maj7|m7|7)")


class CandidateError(ValueError):
    """A pinned source or selected printed relationship changed."""


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_sources(root: Path = ROOT) -> dict[int, dict[str, Any]]:
    root = root.resolve(strict=True)
    if Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], cwd=root, text=True).strip()) != root:
        raise CandidateError("root is not the sole Git checkout")
    result: dict[int, dict[str, Any]] = {}
    for level, formats in SOURCES.items():
        result[level] = {}
        for kind in ("txt", "pdf"):
            relative, size, expected_sha = formats[kind]
            path = root
            for part in Path(relative).parts:
                path /= part
                if path.is_symlink():
                    raise CandidateError(f"source symlink: {relative}")
            if not path.resolve(strict=True).is_relative_to(root):
                raise CandidateError(f"source escapes root: {relative}")
            raw = path.read_bytes()
            if len(raw) != size or sha(raw) != expected_sha:
                raise CandidateError(f"pinned source drift: Level {level} {kind}")
            content = raw.decode("utf-8").splitlines() if kind == "txt" else [page.extract_text() or "" for page in PdfReader(path).pages]
            if kind == "pdf" and len(content) != formats["page_count"]:
                raise CandidateError(f"PDF page count: Level {level}")
            result[level][kind] = {"identity": {"path": relative, "bytes": size, "sha256": expected_sha}, "content": content}
    return result


def exact_line(lines: list[str], literal: str) -> int:
    matches = [i for i, line in enumerate(lines, 1) if line == literal]
    if len(matches) != 1:
        raise CandidateError(f"exact TXT line missing or repeated: {literal}")
    return matches[0]


def pdf_ref(pages: list[str], page: int, heading: str) -> dict[str, Any]:
    value = pages[page - 1]
    if not value.startswith(heading + "\n"):
        raise CandidateError(f"PDF page heading drift: page {page}")
    return {"page": page, "extracted_text_sha256": sha(value.encode("utf-8"))}


def note_pc(note: str) -> int:
    if NOTE.fullmatch(note) is None:
        raise CandidateError(f"invalid pitch spelling: {note}")
    return (NOTE_PC[note[0]] + (1 if note.endswith("#") else -1 if note.endswith("b") else 0)) % 12


def check_role(note: str, chord: str, role: str) -> None:
    match = CHORD.fullmatch(chord)
    if match is None or role not in ROLE_PC:
        raise CandidateError(f"unsupported chord/role: {chord}/{role}")
    if (note_pc(note) - note_pc(match.group(1))) % 12 != ROLE_PC[role]:
        raise CandidateError(f"printed pitch/role disagreement: {note}/{chord}/{role}")


def bounded_table(page: str, start: str, end: str, row_width: int, count: int) -> list[list[str]]:
    if page.count(start) != 1 or page.count(end) != 1:
        raise CandidateError("PDF table boundary drift")
    cells = page.split(start, 1)[1].split(end, 1)[0].strip().splitlines()
    if len(cells) != row_width * count:
        raise CandidateError(f"PDF table shape drift: {len(cells)} cells")
    return [cells[i:i + row_width] for i in range(0, len(cells), row_width)]


def level83(source: dict[str, Any]) -> dict[str, Any]:
    lines, pages = source["txt"]["content"], source["pdf"]["content"]
    ref = pdf_ref(pages, 10, "Module C — Common-Tone Chord Substitution")
    rows = bounded_table(pages[9], "Fixed melody\nHarmony\nChanging role\n", "Keep the top note fixed.", 3, 6)
    out = []
    for number, (melody, progression, roles) in enumerate(rows, 1):
        chords, role_list = progression.split(" → "), roles.split(" → ")
        if NOTE.fullmatch(melody) is None or len(chords) != 3 or len(role_list) != 3:
            raise CandidateError(f"Level 83 row {number} shape")
        for chord, role in zip(chords, role_list):
            check_role(melody, chord, role)
        txt_literal = f"{melody}: {progression.replace(' → ', ' -> ')}"
        line = exact_line(lines, txt_literal)
        out.append({"local_key": f"common-tone-{number}", "fixed_melody": melody, "harmony": chords,
                    "printed_roles": role_list, "txt_line": line, "pdf": ref,
                    "sounding_octave": None, "bass_and_inner_voice_realization": None,
                    "onsets_and_durations": None})
    return {"module": "C", "selected_pdf_page": ref, "cells": out,
            "txt_relation": "progressions match exact TXT lines; changing roles are PDF-only",
            "instruction": "Keep the top note fixed. Move bass and inner voices by the smallest available intervals. Then create one additional substitute for each row."}


def split_notes(value: str) -> list[str]:
    notes = value.split("-")
    if len(notes) != 4 or any(NOTE.fullmatch(note) is None for note in notes):
        raise CandidateError(f"four-note voice changed: {value}")
    return notes


def level84(source: dict[str, Any]) -> dict[str, Any]:
    lines, pages = source["txt"]["content"], source["pdf"]["content"]
    ref = pdf_ref(pages, 2, "Module A — Melody/Bass Skeleton")
    anchor = exact_line(lines, "A. Melody/bass skeleton extraction — 128 events")
    rows = bounded_table(pages[1], "Cell\nBass\nTop melody\nTask\n", "Passes: melody alone", 4, 6)
    out = []
    for number, (label, bass, melody, task) in enumerate(rows, 1):
        if label != str(number) or bass in "\n".join(lines) or melody in "\n".join(lines):
            raise CandidateError(f"Level 84 PDF-only row drift: {number}")
        out.append({"local_key": f"outer-voice-{number}", "bass_notes": split_notes(bass),
                    "top_melody_notes": split_notes(melody), "printed_task": task,
                    "txt_module_anchor_line": anchor, "txt_cell_detail": "omitted", "pdf": ref,
                    "sounding_octaves": None, "strings_and_frets": None, "onsets_and_durations": None})
    return {"module": "A", "selected_pdf_page": ref, "cells": out,
            "txt_relation": "module named in TXT; all six detailed cells omitted",
            "passes": "melody alone → bass alone → sing melody while playing bass → play both → transpose one cell"}


def level85(source: dict[str, Any]) -> dict[str, Any]:
    lines, pages = source["txt"]["content"], source["pdf"]["content"]
    ref = pdf_ref(pages, 4, "Module B - Note-Length Ladder")
    module_anchor = exact_line(lines, "B. Note-length ladder: legato to clipped - 128 events")
    practice_anchor = exact_line(lines, "- long vs clipped note duration")
    instruction = "Play G-C-D-G with four quarter-note attacks per measure. Only duration changes."
    if instruction not in pages[3] or "G-C-D-G" in "\n".join(lines):
        raise CandidateError("Level 85 PDF-only instruction drift")
    rows = bounded_table(pages[3], "Level\nDuration target\nLeft-hand behavior\n", "Repeat with triads", 3, 6)
    out = []
    for number, (label, target, behavior) in enumerate(rows, 1):
        if label != str(number) or behavior in "\n".join(lines):
            raise CandidateError(f"Level 85 PDF-only row drift: {number}")
        if number <= 4 and target != f"{(5-number)*25}%":
            raise CandidateError(f"Level 85 duration target drift: {number}")
        if number == 5 and target != "percussive" or number == 6 and target != "mixed":
            raise CandidateError(f"Level 85 target label drift: {number}")
        out.append({"local_key": f"note-length-{number}", "printed_duration_target": target,
                    "printed_left_hand_behavior": behavior, "txt_module_anchor_line": module_anchor,
                    "txt_practice_anchor_line": practice_anchor, "txt_cell_detail": "omitted", "pdf": ref,
                    "measured_sounding_duration": None, "audio_timing": None})
    return {"module": "B", "selected_pdf_page": ref, "cells": out,
            "txt_relation": "module and general practice named in TXT; six detailed rows omitted",
            "printed_attack_instruction": instruction,
            "printed_repeat_instruction": "Repeat with triads, shells, and full chords. The shorter versions must not speed up."}


def build(root: Path = ROOT) -> dict[str, Any]:
    sources = read_sources(root)
    return {"wbs": "2.3.1.3.1", "status": "Pending", "detached_source_candidate": True,
            "canonical_ids_allocated": False, "runtime_eligible": False, "whole_workbook_complete": False,
            "review": "Pending", "selected_cell_count": 18,
            "source_identities": {str(level): {kind: sources[level][kind]["identity"] for kind in ("txt", "pdf")}
                                  for level in SOURCES},
            "levels": {"83": level83(sources[83]), "84": level84(sources[84]), "85": level85(sources[85])},
            "limitations": ["PDF selected cells only; whole workbooks and semantic authority remain Pending",
                            "No canonical exercise identity or runtime admission",
                            "Unprinted octave, realization, timing, fingering and audio behavior remain unknown"]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    destination = args.output.resolve()
    if not destination.is_relative_to(BUILD.resolve()):
        parser.error("output must remain under Build/parallel-06/2.3-levels-083-085-r01")
    payload = build()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
