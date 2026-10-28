#!/usr/bin/env python3
"""Build detached source-literal Level 90 Module B shuffle cells."""

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
BUILD = ROOT / "Build/parallel-06/2.3-level090-music-r01"
EXPECTED_PYPDF = "6.10.0"
SOURCE = {
    "txt": ("Notes/music/guitar project/TXT version/Guitar_Exercises_Section_XII_Level_90_Jazz_Swing_Shuffle_Afrobeat_Latin_Interlock_Jam_Band_Pocket_and_Multi_Style_Groove_Synthesis.txt", 1506, "a62ff7bed53111d9b12c4674755b898696890af4964dda1d9505537642219f60"),
    "pdf": ("Notes/music/guitar project/PDF version/Guitar_Exercises_Section_XII_Level_90_Jazz_Swing_Shuffle_Afrobeat_Latin_Interlock_Jam_Band_Pocket_and_Multi_Style_Groove_Synthesis.pdf", 28245, "abec6d82d4fc638fff8978ee1c4d33f569aba56e690ecf5918e37d3242429b1b"),
    "page_count": 21,
}
PATTERN_SYMBOLS = {"P", "M", "O", "x", "-", ">P"}
CHORD = re.compile(r"[A-G](?:#|b)?(?:maj7|m7|7)")


class CandidateError(ValueError):
    """Source identity or printed Module B structure drifted."""


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify_bytes(data: bytes, size: int, digest: str, label: str) -> None:
    if len(data) != size or sha(data) != digest:
        raise CandidateError(f"pinned source drift: {label}")


def read_source(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve(strict=True)
    if Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], cwd=root, text=True).strip()) != root:
        raise CandidateError("root is not the sole Git checkout")
    if PYPDF_VERSION != EXPECTED_PYPDF:
        raise CandidateError(f"PDF extractor drift: {PYPDF_VERSION}")
    result: dict[str, Any] = {}
    for kind in ("txt", "pdf"):
        relative, size, digest = SOURCE[kind]
        path = root
        for part in Path(relative).parts:
            path /= part
            if path.is_symlink():
                raise CandidateError(f"source symlink: {relative}")
        if not path.resolve(strict=True).is_relative_to(root):
            raise CandidateError(f"source escapes root: {relative}")
        raw = path.read_bytes()
        verify_bytes(raw, size, digest, f"Level 90 {kind}")
        content = raw.decode("utf-8").splitlines() if kind == "txt" else [page.extract_text() or "" for page in PdfReader(path).pages]
        if kind == "pdf" and len(content) != SOURCE["page_count"]:
            raise CandidateError("Level 90 PDF page count drift")
        result[kind] = {"identity": {"path": relative, "bytes": size, "sha256": digest},
                        "content": content}
    return result


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


def pattern_groups(pattern: str) -> list[list[str]]:
    groups = pattern.split(" | ")
    if len(groups) != 2:
        raise CandidateError(f"shuffle pattern is not two triplet groups: {pattern}")
    parsed = [group.split() for group in groups]
    if any(len(group) != 3 or any(symbol not in PATTERN_SYMBOLS for symbol in group) for group in parsed):
        raise CandidateError(f"invalid printed shuffle symbols: {pattern}")
    if all(symbol == "-" for group in parsed for symbol in group):
        raise CandidateError("shuffle pattern has no printed contact")
    return parsed


def progression_chords(value: str) -> list[str]:
    chords = value.split("-")
    if len(chords) != 4 or any(CHORD.fullmatch(chord) is None for chord in chords):
        raise CandidateError(f"invalid printed contrast progression: {value}")
    if value != "A7-D7-E7-A7":
        raise CandidateError(f"Level 90 same-progression drift: {value}")
    return chords


def module_b(source: dict[str, Any]) -> dict[str, Any]:
    lines, pages = source["txt"]["content"], source["pdf"]["content"]
    module_line = exact_line(lines, "B. Shuffle hierarchy and triplet-feel control - 144 events")
    skill_line = exact_line(lines, "- shuffle hierarchy")
    hierarchy_ref = pdf_ref(pages, 5, "Module B - Shuffle Hierarchy")
    contrast_ref = pdf_ref(pages, 6, "Module B - Swing/Shuffle Contrast")
    hierarchy_intro = "The shuffle uses the same long-short triplet spacing as swing, but often with more repetitive riff or chord motion."
    hierarchy_close = "Apply to A7-D7-E7 blues, E5-A5 rock shuffle, and G-C-D country shuffle. The harmonic language changes; the shuffle spacing does not."
    contrast_close = "The triplet grid stays fixed. Register, density, note length, and orchestration create the contrast."
    if hierarchy_intro not in pages[4] or hierarchy_close not in pages[4] or contrast_close not in pages[5]:
        raise CandidateError("Module B printed instruction drift")
    hierarchy = table(pages[4], "Cell\nPattern\nGoal\n", "Apply to A7-D7-E7", 3, 6)
    contrast = table(pages[5], "Pass\nSame progression\nInstruction\n", "The triplet grid stays fixed.", 3, 5)
    txt_content = "\n".join(lines)
    patterns = []
    for number, (label, pattern, goal) in enumerate(hierarchy, 1):
        if label != str(number) or pattern in txt_content:
            raise CandidateError(f"Module B hierarchy PDF-only row drift: {number}")
        patterns.append({"local_key": f"shuffle-pattern-{number}", "printed_pattern": pattern,
                         "ordered_triplet_groups": pattern_groups(pattern), "printed_goal": goal,
                         "txt_module_anchor_line": module_line, "txt_skill_anchor_line": skill_line,
                         "txt_cell_detail": "omitted", "pdf": hierarchy_ref,
                         "performed_onsets_and_durations": None, "swing_ratio": None,
                         "voicing_strings_and_frets": None, "audio": None})
    passes = []
    for number, (label, progression, instruction) in enumerate(contrast, 1):
        if label != str(number) or instruction in txt_content:
            raise CandidateError(f"Module B contrast PDF-only row drift: {number}")
        passes.append({"local_key": f"swing-shuffle-pass-{number}",
                       "printed_same_progression": progression, "ordered_chords": progression_chords(progression),
                       "printed_instruction": instruction, "txt_module_anchor_line": module_line,
                       "txt_skill_anchor_line": skill_line, "txt_cell_detail": "omitted", "pdf": contrast_ref,
                       "performed_onsets_and_durations": None, "swing_ratio": None,
                       "voicing_strings_and_frets": None, "audio": None})
    return {"module": "B", "selected_pdf_pages": [hierarchy_ref, contrast_ref],
            "shuffle_pattern_cells": patterns, "swing_shuffle_contrast_passes": passes,
            "selected_cell_count": len(patterns) + len(passes),
            "printed_hierarchy_intro": hierarchy_intro, "printed_hierarchy_closing": hierarchy_close,
            "printed_contrast_closing": contrast_close,
            "symbol_execution_semantics": "Pending: source symbols retained literally; Module B supplies no full execution legend",
            "txt_relation": "module and broad shuffle skill named in TXT; eleven detailed cells omitted"}


def build(root: Path = ROOT) -> dict[str, Any]:
    source = read_source(root)
    module = module_b(source)
    return {"wbs": "2.3.1.3.1", "level": 90, "section": "XII", "status": "Pending",
            "review": "Pending", "detached_source_candidate": True,
            "canonical_ids_allocated": False, "runtime_eligible": False,
            "whole_workbook_complete": False, "selected_cell_count": 11,
            "extractor": f"pypdf {EXPECTED_PYPDF}",
            "source_identities": {kind: source[kind]["identity"] for kind in ("txt", "pdf")},
            "module_b": module,
            "limitations": ["Only printed Module B rows represented; rest of Level 90 and Curriculum review Pending",
                            "No canonical IDs, runtime admission or complete workbook conversion",
                            "Performed timing, swing ratio, voicing/fret, fingering and audio unknown"]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(BUILD.resolve()):
        parser.error("output must remain under Build/parallel-06/2.3-level090-music-r01")
    payload = build()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
