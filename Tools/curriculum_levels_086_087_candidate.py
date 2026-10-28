#!/usr/bin/env python3
"""Build a detached, source-literal Level 86–87 groove-cell candidate."""

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
BUILD = ROOT / "Build/parallel-06/2.3-levels-086-087-r01"
EXPECTED_PYPDF = "6.10.0"
SOURCES = {
    86: {
        "txt": ("Notes/music/guitar project/TXT version/Guitar_Exercises_Section_XII_Level_86_Funk_and_RnB_Groove_Vocabulary_Sixteenth_Muting_Chord_Stabs_Ghost_Hierarchy_Syncopated_Triads_and_Bass_Space.txt", 1483, "8730bcc844ca1a1f0dfeae22701be5ada9214926e412c9646643ba536cd7953e"),
        "pdf": ("Notes/music/guitar project/PDF version/Guitar_Exercises_Section_XII_Level_86_Funk_and_RnB_Groove_Vocabulary_Sixteenth_Muting_Chord_Stabs_Ghost_Hierarchy_Syncopated_Triads_and_Bass_Space.pdf", 41765, "74d4db847ed27ce9e11641bbc0120cecfb7818f390df8c0680ce2cca708d3565"),
        "page_count": 15,
    },
    87: {
        "txt": ("Notes/music/guitar project/TXT version/Guitar_Exercises_Section_XII_Level_87_Reggae_Ska_Soul_Disco_and_Motown_Groove_Principles_Offbeats_Clipped_Chords_Repeated_Figures_and_Octave_Bass_Interaction.txt", 1625, "833c2f7db7011ffd2e7cb6ec4753ea141da47dd3981d895a64cc76e53425b311"),
        "pdf": ("Notes/music/guitar project/PDF version/Guitar_Exercises_Section_XII_Level_87_Reggae_Ska_Soul_Disco_and_Motown_Groove_Principles_Offbeats_Clipped_Chords_Repeated_Figures_and_Octave_Bass_Interaction.pdf", 48311, "a86904384a13a21744d2c052d37ae09bb6df7d3355136e9441a5fe387f20a3e0"),
        "page_count": 20,
    },
}
CHORD = re.compile(r"[A-G](?:#|b)?(?:maj9|m7|9|13)")
POINT = re.compile(r"(?:[1-4]|[ea&][1-4])")


class CandidateError(ValueError):
    """Pinned source or selected musical row is unsupported."""


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify_bytes(raw: bytes, size: int, digest: str, label: str) -> None:
    if len(raw) != size or sha(raw) != digest:
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
        raise CandidateError(f"TXT anchor missing or repeated: {literal}")
    return matches[0]


def pdf_ref(pages: list[str], page: int, heading: str) -> dict[str, Any]:
    value = pages[page - 1]
    if not value.startswith(heading + "\n"):
        raise CandidateError(f"PDF heading drift: page {page}")
    return {"page": page, "extracted_text_sha256": sha(value.encode("utf-8"))}


def table(page: str, start: str, end: str, width: int, count: int) -> list[list[str]]:
    if page.count(start) != 1 or page.count(end) != 1:
        raise CandidateError("PDF table boundary drift")
    content = page.split(start, 1)[1].split(end, 1)[0].strip().splitlines()
    if len(content) != width * count:
        raise CandidateError(f"PDF table shape drift: {len(content)} cells")
    return [content[i:i + width] for i in range(0, len(content), width)]


def parse_points(value: str) -> list[str]:
    points = value.split(", ")
    if len(points) not in (3, 4) or any(POINT.fullmatch(point) is None for point in points) or len(set(points)) != len(points):
        raise CandidateError(f"invalid contact points: {value}")
    return points


def level86(source: dict[str, Any]) -> dict[str, Any]:
    lines, pages = source["txt"]["content"], source["pdf"]["content"]
    ref = pdf_ref(pages, 5, "Module C - Syncopated Triads and Shells")
    module_line = exact_line(lines, "C. Syncopated triad and shell placement - 144 events")
    skill_line = exact_line(lines, "- syncopated triads and shells")
    rows = table(pages[4], "Cell\nHarmony\nContact points\n", "Use three-note triads first.", 3, 8)
    if [row[0] for row in rows] != [str(i) for i in range(1, 9)]:
        raise CandidateError("Level 86 row order drift")
    if rows[6][1] != "Am7 -> D9" or rows[7][1] != "Cmaj7 -> Dm7 -> G7":
        raise CandidateError("Level 86 excluded progression rows drift")
    chosen = []
    for number, (_, harmony, points) in enumerate(rows[:6], 1):
        if CHORD.fullmatch(harmony) is None or points in "\n".join(lines):
            raise CandidateError(f"Level 86 PDF-only row drift: {number}")
        chosen.append({"local_key": f"single-chord-contact-{number}", "printed_harmony": harmony,
                       "printed_contact_points": points, "ordered_contact_labels": parse_points(points),
                       "txt_module_anchor_line": module_line, "txt_skill_anchor_line": skill_line,
                       "txt_cell_detail": "omitted", "pdf": ref,
                       "performed_onsets_and_durations": None, "voicing_strings_and_frets": None,
                       "fingering": None, "audio": None})
    return {"module": "C", "selected_pdf_page": ref, "cells": chosen,
            "scope_note": "PDF rows 1–6 only; progression/change rows 7–8 not converted",
            "txt_relation": "module and broad skill named in TXT; six selected contact rows omitted",
            "printed_instruction": "Use three-note triads first. Full chord grips are optional and should not increase noise or reduce release control."}


def parse_pattern(count: str, value: str) -> list[str]:
    tokens = value.split()
    if count == "1 & 2 & 3 & 4 &":
        if len(tokens) != 8 or any(token not in {"P", "x", "-"} for token in tokens):
            raise CandidateError(f"invalid eighth contact pattern: {value}")
        if tokens[0] != "-" or tokens[2] != "-" or tokens[4] != "-" or tokens[6] != "-":
            raise CandidateError("reggae eighth downbeat contact drift")
        return tokens
    if count == "1 e & a ...":
        if len(tokens) != 4 or any(len(token) != 4 or set(token) - {"P", "x", "-"} for token in tokens):
            raise CandidateError(f"invalid sixteenth contact pattern: {value}")
        return list("".join(tokens))
    raise CandidateError(f"unsupported printed count grid: {count}")


def level87(source: dict[str, Any]) -> dict[str, Any]:
    lines, pages = source["txt"]["content"], source["pdf"]["content"]
    ref = pdf_ref(pages, 3, "Module A - Reggae Offbeat Placement")
    module_line = exact_line(lines, "A. Offbeat placement and clipped skank control - 128 events")
    skill_line = exact_line(lines, "- reggae offbeat skank")
    instruction = "Use C-F-G-C. Keep the downbeat physically present in the counting hand but mostly silent in the fretting/attack hand."
    if instruction not in pages[2]:
        raise CandidateError("Level 87 instruction drift")
    rows = table(pages[2], "Cell\nCount\nContact pattern\nGoal\n", "Every pitched chord must release", 4, 6)
    chosen = []
    for number, (label, count, pattern, goal) in enumerate(rows, 1):
        if label != str(number) or pattern in "\n".join(lines):
            raise CandidateError(f"Level 87 PDF-only row drift: {number}")
        symbols = parse_pattern(count, pattern)
        chosen.append({"local_key": f"reggae-offbeat-{number}", "printed_count": count,
                       "printed_contact_pattern": pattern, "ordered_contact_symbols": symbols,
                       "printed_goal": goal, "txt_module_anchor_line": module_line,
                       "txt_skill_anchor_line": skill_line, "txt_cell_detail": "omitted", "pdf": ref,
                       "chord_to_grid_assignment": None, "performed_onsets_and_durations": None,
                       "voicing_strings_and_frets": None, "fingering": None, "audio": None})
    return {"module": "A", "selected_pdf_page": ref, "cells": chosen,
            "printed_progression": "C-F-G-C", "txt_relation": "module and broad skill named in TXT; six placement cells omitted",
            "printed_release_instruction": "Every pitched chord must release before the following downbeat. Use three-string triads or partial barres rather than large grips."}


def build(root: Path = ROOT) -> dict[str, Any]:
    sources = read_sources(root)
    return {"wbs": "2.3.1.3.1", "status": "Pending", "review": "Pending",
            "detached_source_candidate": True, "canonical_ids_allocated": False,
            "runtime_eligible": False, "whole_workbook_complete": False,
            "selected_cell_count": 12, "extractor": f"pypdf {EXPECTED_PYPDF}",
            "source_identities": {str(level): {kind: sources[level][kind]["identity"] for kind in ("txt", "pdf")}
                                  for level in SOURCES},
            "levels": {"86": level86(sources[86]), "87": level87(sources[87])},
            "limitations": ["Selected PDF rows only; parent curriculum review remains Pending",
                            "No canonical identity, runtime admission or complete workbook conversion",
                            "Performed timing, voicing, fingering and audio remain unknown"]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(BUILD.resolve()):
        parser.error("output must remain under Build/parallel-06/2.3-levels-086-087-r01")
    payload = build()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
