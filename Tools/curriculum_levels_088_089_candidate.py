#!/usr/bin/env python3
"""Detached literal gallop and alternating-bass cells from Levels 88–89."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from pypdf import PdfReader, __version__ as PYPDF_VERSION


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "Build/parallel-06/2.3-levels-088-089-r01"
EXPECTED_PYPDF = "6.10.0"
SOURCES = {
    88: {
        "txt": ("Notes/music/guitar project/TXT version/Guitar_Exercises_Section_XII_Level_88_Rock_Hard_Rock_and_Metal_Groove_Control_Eighth_Note_Drive_Gallops_Pedal_Tones_Power_Chord_Displacement_and_Riff_Architecture.txt", 1489, "0cbaa5ea7950658dc89eec8b484792d05a640d9532ef7add0442b571a07a2aac"),
        "pdf": ("Notes/music/guitar project/PDF version/Guitar_Exercises_Section_XII_Level_88_Rock_Hard_Rock_and_Metal_Groove_Control_Eighth_Note_Drive_Gallops_Pedal_Tones_Power_Chord_Displacement_and_Riff_Architecture.pdf", 40992, "c2e71c0f2391c29d713f6992c9149e43ec599f9eb1cd1f08bf09d915f1a8971f"),
        "page_count": 15,
    },
    89: {
        "txt": ("Notes/music/guitar project/TXT version/Guitar_Exercises_Section_XII_Level_89_Country_Americana_and_Hybrid_Picking_Groove_Alternating_Bass_Boom_Chuck_Train_Rhythm_Double_Stops_and_Controlled_Fills.txt", 1459, "700365c24590c0579cff36906ad71434184f90146333dc9cee062b35ebd8e4df"),
        "pdf": ("Notes/music/guitar project/PDF version/Guitar_Exercises_Section_XII_Level_89_Country_Americana_and_Hybrid_Picking_Groove_Alternating_Bass_Boom_Chuck_Train_Rhythm_Double_Stops_and_Controlled_Fills.pdf", 26341, "ffd3a2dbf7fe9c8f13c4006474ed965a24370af471d2a50601b924a5a356ea2c"),
        "page_count": 20,
    },
}
PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


class CandidateError(ValueError):
    """A pinned source or literal musical relationship drifted."""


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify_bytes(data: bytes, size: int, digest: str, label: str) -> None:
    if len(data) != size or sha(data) != digest:
        raise CandidateError(f"pinned source drift: {label}")


def read_sources(root: Path = ROOT) -> dict[int, dict[str, Any]]:
    root = root.resolve(strict=True)
    if Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], cwd=root, text=True).strip()) != root:
        raise CandidateError("root is not the sole Git checkout")
    if PYPDF_VERSION != EXPECTED_PYPDF:
        raise CandidateError(f"PDF extractor drift: {PYPDF_VERSION}")
    out: dict[int, dict[str, Any]] = {}
    for level, formats in SOURCES.items():
        out[level] = {}
        for kind in ("txt", "pdf"):
            relative, size, digest = formats[kind]
            path = root
            for part in Path(relative).parts:
                path /= part
                if path.is_symlink():
                    raise CandidateError(f"source symlink: {relative}")
            if not path.resolve(strict=True).is_relative_to(root):
                raise CandidateError(f"source escapes root: {relative}")
            raw = path.read_bytes()
            verify_bytes(raw, size, digest, f"Level {level} {kind}")
            content = raw.decode("utf-8").splitlines() if kind == "txt" else [page.extract_text() or "" for page in PdfReader(path).pages]
            if kind == "pdf" and len(content) != formats["page_count"]:
                raise CandidateError(f"PDF page count drift: Level {level}")
            out[level][kind] = {"identity": {"path": relative, "bytes": size, "sha256": digest},
                                "content": content}
    return out


def exact_line(lines: list[str], literal: str) -> int:
    matches = [i for i, line in enumerate(lines, 1) if line == literal]
    if len(matches) != 1:
        raise CandidateError(f"TXT line missing or repeated: {literal}")
    return matches[0]


def pdf_ref(pages: list[str], page: int, heading: str) -> dict[str, Any]:
    value = pages[page - 1]
    if not value.startswith(heading + "\n"):
        raise CandidateError(f"PDF heading drift: page {page}")
    return {"page": page, "extracted_text_sha256": sha(value.encode("utf-8"))}


def table(page: str, start: str, end: str, width: int, count: int) -> list[list[str]]:
    if page.count(start) != 1 or page.count(end) != 1:
        raise CandidateError("PDF table boundary drift")
    cells = page.split(start, 1)[1].split(end, 1)[0].strip().splitlines()
    if len(cells) != width * count:
        raise CandidateError(f"PDF table shape drift: {len(cells)} cells")
    return [cells[i:i + width] for i in range(0, len(cells), width)]


def gallop_tokens(grid: str, picking: str) -> tuple[list[str], list[str]]:
    contact, pick = grid.split(), picking.split()
    if len(contact) != 4 or len(pick) != 4:
        raise CandidateError("single-beat gallop grid is not four slots")
    for symbol, direction in zip(contact, pick):
        if symbol == "M" and direction in ("D", "U"):
            continue
        if symbol == "-" and direction == "-":
            continue
        raise CandidateError(f"gallop attack/pick mismatch: {symbol}/{direction}")
    if contact.count("M") != 3 or contact.count("-") != 1:
        raise CandidateError("gallop does not have three attacks and one rest")
    return contact, pick


def level88(source: dict[str, Any]) -> dict[str, Any]:
    lines, pages = source["txt"]["content"], source["pdf"]["content"]
    ref = pdf_ref(pages, 4, "Module B - Gallops and Reverse Gallops")
    module_line = exact_line(lines, "B. Gallop and reverse-gallop control - 144 events")
    skill_line = exact_line(lines, "- gallops and reverse gallops")
    count = "Count each beat as 1 e & a. Gallop = long-short-short; reverse gallop = short-short-long."
    if count not in pages[3]:
        raise CandidateError("Level 88 count statement drift")
    rows = table(pages[3], "Cell\nSixteenth grid\nPicking goal\n", "Begin on one string.", 3, 8)
    if [r[0] for r in rows] != [str(i) for i in range(1, 9)]:
        raise CandidateError("Level 88 row order drift")
    if "|" not in rows[4][1] or "accent displacement" != rows[7][2]:
        raise CandidateError("Level 88 excluded multi-beat rows drift")
    chosen = []
    for number, (_, grid, picking) in enumerate(rows[:4], 1):
        if grid in "\n".join(lines):
            raise CandidateError(f"Level 88 PDF-only row drift: {number}")
        contact, pick = gallop_tokens(grid, picking)
        chosen.append({"local_key": f"single-beat-gallop-{number}", "printed_sixteenth_grid": grid,
                       "printed_picking_goal": picking, "ordered_contact_symbols": contact,
                       "ordered_picking_symbols": pick, "txt_module_anchor_line": module_line,
                       "txt_skill_anchor_line": skill_line, "txt_cell_detail": "omitted", "pdf": ref,
                       "performed_onsets_and_durations": None, "pedal_string_and_fret": None,
                       "power_chord_realization": None, "audio": None})
    return {"module": "B", "selected_pdf_page": ref, "cells": chosen,
            "printed_count_and_shape": count,
            "printed_instruction": "Begin on one string. Then move the final attack of each beat to a power chord while the pedal note remains muted.",
            "scope_note": "PDF rows 1–4 only; multi-beat/continuity/accent rows 5–8 not converted",
            "txt_relation": "module and broad gallop skill named in TXT; four selected rows omitted"}


def check_bass(chord: str, pattern: str, count: str) -> list[str]:
    match = re.fullmatch(r"([A-G])m?", chord)
    notes = pattern.split("-")
    if match is None or len(notes) != 4 or any(note not in PC for note in notes) or count != "1-2-3-4":
        raise CandidateError(f"unsupported alternating bass row: {chord}/{pattern}/{count}")
    root = match.group(1)
    if notes[0] != root or notes[2] != root or notes[1] != notes[3]:
        raise CandidateError(f"alternating root/fifth order drift: {chord}/{pattern}")
    if (PC[notes[1]] - PC[root]) % 12 != 7:
        raise CandidateError(f"alternating bass fifth mismatch: {chord}/{pattern}")
    return notes


def level89(source: dict[str, Any]) -> dict[str, Any]:
    lines, pages = source["txt"]["content"], source["pdf"]["content"]
    ref = pdf_ref(pages, 3, "Module A - Alternating Bass Independence")
    module_line = exact_line(lines, "A. Alternating-bass independence - 144 events")
    skill_line = exact_line(lines, "- alternating root/fifth bass")
    rows = table(pages[2], "Chord\nBass pattern\nCount\n", "Passes: bass only", 3, 8)
    chosen = []
    for number, (chord, pattern, count) in enumerate(rows, 1):
        if pattern in "\n".join(lines):
            raise CandidateError(f"Level 89 PDF-only row drift: {number}")
        chosen.append({"local_key": f"alternating-bass-{number}", "printed_chord": chord,
                       "printed_bass_pattern": pattern, "ordered_bass_notes": check_bass(chord, pattern, count),
                       "printed_count": count, "txt_module_anchor_line": module_line,
                       "txt_skill_anchor_line": skill_line, "txt_cell_detail": "omitted", "pdf": ref,
                       "sounding_octaves": None, "strings_and_frets": None,
                       "performed_onsets_and_durations": None, "fingering": None, "audio": None})
    return {"module": "A", "selected_pdf_page": ref, "cells": chosen,
            "printed_instruction": "Play each bass pattern alone before adding any chord.",
            "printed_passes": "bass only -> bass while silently fretting chord -> bass + upper chord on beats 2/4 -> bass + upper melodic note",
            "txt_relation": "module and broad root/fifth skill named in TXT; eight detailed cells omitted"}


def build(root: Path = ROOT) -> dict[str, Any]:
    sources = read_sources(root)
    return {"wbs": "2.3.1.3.1", "status": "Pending", "review": "Pending",
            "detached_source_candidate": True, "canonical_ids_allocated": False,
            "runtime_eligible": False, "whole_workbook_complete": False,
            "selected_cell_count": 12, "extractor": f"pypdf {EXPECTED_PYPDF}",
            "source_identities": {str(level): {kind: sources[level][kind]["identity"] for kind in ("txt", "pdf")}
                                  for level in SOURCES},
            "levels": {"88": level88(sources[88]), "89": level89(sources[89])},
            "limitations": ["Selected PDF rows only; Curriculum review Pending",
                            "No canonical identity, runtime admission or complete workbook conversion",
                            "Performed timing, octave, strings/frets, fingering and audio unknown"]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(BUILD.resolve()):
        parser.error("output must remain under Build/parallel-06/2.3-levels-088-089-r01")
    payload = build()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
