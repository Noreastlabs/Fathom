#!/usr/bin/env python3
"""Build detached, source-literal Level 92 Module A rake cells."""

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
BUILD = ROOT / "Build/parallel-06/2.3-level092-music-r01"
EXPECTED_PYPDF = "6.10.0"
SOURCE = {
    "txt": ("Notes/music/guitar project/TXT version/Guitar_Exercises_Section_XIII_Level_92_Rakes_Grace_Notes_Double_Stop_Slides_Harmonics_Volume_Swells_Muted_Attacks_and_Articulation_Chains.txt", 1675, "67ddb7a03c84f727f78ced578853b21b2ecf22eb81a72deedfe1d16bd9ab8e1a"),
    "pdf": ("Notes/music/guitar project/PDF version/Guitar_Exercises_Section_XIII_Level_92_Rakes_Grace_Notes_Double_Stop_Slides_Harmonics_Volume_Swells_Muted_Attacks_and_Articulation_Chains.pdf", 43299, "c2068c5c2a52366fcd53526a0ae32a82a4aaabde9252be17599726bf8f01beff"),
    "page_count": 16,
}
INTRO = ("A rake is a controlled sweep across muted strings into one pitched target. "
         "The muted strings must not reveal chord tones.")
PRACTICE = "Practice on one target note in three registers before changing pitches."
EXPECTED_ROWS = (
    ("low-to-high", "B-string target", "3 muted strings + target"),
    ("low-to-high", "high-e target", "4 muted strings + target"),
    ("high-to-low", "G-string target", "2 muted strings + target"),
    ("low-to-high", "bent target", "rake ends before bend begins"),
    ("low-to-high", "vibrato target", "vibrato begins after pitch centers"),
    ("single muted contact", "target on next 16th", "micro-rake"),
    ("two muted contacts", "target on beat", "pickup rake"),
    ("silent rest -> rake", "target on beat 4", "dramatic entry"),
)


class CandidateError(ValueError):
    """The pinned source or a printed rake relationship changed."""


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify_bytes(data: bytes, size: int, digest: str, label: str) -> None:
    if len(data) != size or sha(data) != digest:
        raise CandidateError(f"pinned source drift: {label}")


def read_source(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve(strict=True)
    git_root = Path(subprocess.check_output(
        ["git", "rev-parse", "--show-toplevel"], cwd=root, text=True).strip())
    if git_root != root:
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
        verify_bytes(raw, size, digest, f"Level 92 {kind}")
        content = (raw.decode("utf-8").splitlines() if kind == "txt"
                   else [page.extract_text() or "" for page in PdfReader(path).pages])
        if kind == "pdf" and len(content) != SOURCE["page_count"]:
            raise CandidateError("Level 92 PDF page count drift")
        result[kind] = {"identity": {"path": relative, "bytes": size, "sha256": digest},
                        "content": content}
    return result


def exact_line(lines: list[str], literal: str) -> int:
    matches = [i for i, line in enumerate(lines, 1) if line == literal]
    if len(matches) != 1:
        raise CandidateError(f"TXT line missing or repeated: {literal}")
    return matches[0]


def selected_page(pages: list[str]) -> tuple[list[list[str]], dict[str, Any]]:
    page = pages[2]
    heading = "Module A - Rakes and Muted Lead-In Attacks\n"
    if not page.startswith(heading) or page.count(INTRO) != 1 or page.count(PRACTICE) != 1:
        raise CandidateError("Module A page heading/instruction drift")
    table_start = INTRO + "\nCell\nDirection\nTarget\nRule\n"
    table_end = "\n" + PRACTICE
    if page.count(table_start) != 1 or page.count(table_end) != 1:
        raise CandidateError("Module A table boundary drift")
    fields = page.split(table_start, 1)[1].split(table_end, 1)[0].splitlines()
    if len(fields) != 8 * 4:
        raise CandidateError(f"Module A table shape drift: {len(fields)} fields")
    return [fields[i:i + 4] for i in range(0, len(fields), 4)], {
        "page": 3, "extracted_text_sha256": sha(page.encode("utf-8"))}


def relationship(number: int, direction: str, target: str, rule: str) -> dict[str, Any]:
    if (direction, target, rule) != EXPECTED_ROWS[number - 1]:
        raise CandidateError(f"Module A row {number} printed relationship drift")
    if number <= 3:
        count_match = re.fullmatch(r"([2-4]) muted strings \+ target", rule)
        if count_match is None:
            raise CandidateError(f"Module A row {number} muted-contact rule drift")
        count = int(count_match.group(1))
        if (count, direction, target) != (
            (3, "low-to-high", "B-string target"),
            (4, "low-to-high", "high-e target"),
            (2, "high-to-low", "G-string target"),
        )[number - 1]:
            raise CandidateError(f"Module A row {number} contact/target mismatch")
        return {"printed_muted_string_count": count, "pitched_target_token": target,
                "printed_direction": direction, "target_placement": None,
                "printed_event_order": ["muted strings", "pitched target"]}
    if number == 4:
        return {"printed_muted_string_count": None, "pitched_target_token": target,
                "printed_direction": direction, "target_placement": None,
                "printed_event_order": ["rake ends", "bend begins"]}
    if number == 5:
        return {"printed_muted_string_count": None, "pitched_target_token": target,
                "printed_direction": direction, "target_placement": None,
                "printed_event_order": ["pitch centers", "vibrato begins"]}
    return {
        "printed_muted_string_count": 1 if number == 6 else 2 if number == 7 else None,
        "pitched_target_token": None,
        "printed_direction": direction,
        "target_placement": {6: "next 16th", 7: "beat", 8: "beat 4"}[number],
        "printed_event_order": {6: ["single muted contact", "target"],
                                7: ["two muted contacts", "target"],
                                8: ["silent rest", "rake", "target"]}[number],
    }


def module_a(source: dict[str, Any]) -> dict[str, Any]:
    lines, pages = source["txt"]["content"], source["pdf"]["content"]
    module_line = exact_line(lines, "A. Rakes and muted lead-in attacks - 128 events")
    skill_line = exact_line(lines, "- controlled rakes")
    rows, page_ref = selected_page(pages)
    cells = []
    txt_content = "\n".join(lines)
    for number, (label, direction, target, rule) in enumerate(rows, 1):
        if label != str(number) or any(value in txt_content for value in (direction, target, rule)):
            raise CandidateError(f"Module A PDF-only row drift: {number}")
        cells.append({"local_key": f"rake-{number}", "printed_cell": label,
                      "printed_direction": direction, "printed_target": target,
                      "printed_rule": rule, "relationship": relationship(number, direction, target, rule),
                      "txt_module_anchor_line": module_line, "txt_skill_anchor_line": skill_line,
                      "txt_cell_detail": "omitted", "pdf": page_ref,
                      "performed_pitch_or_target_attainment": None,
                      "performed_muting_or_dynamics": None, "performed_timing": None,
                      "audio_or_physical_result": None})
    return {"module": "A", "selected_pdf_page": page_ref,
            "selected_pdf_rows": "1-8", "selected_cell_count": len(cells), "cells": cells,
            "printed_intro": INTRO, "printed_practice_instruction": PRACTICE,
            "txt_relation": "module and controlled-rakes skill named in TXT; detailed cells omitted"}


def build(root: Path = ROOT) -> dict[str, Any]:
    source = read_source(root)
    module = module_a(source)
    return {"wbs": "2.3.1.3.1", "level": 92, "section": "XIII",
            "status": "Pending", "review": "Pending", "detached_source_candidate": True,
            "canonical_ids_allocated": False, "runtime_eligible": False,
            "whole_workbook_complete": False, "selected_cell_count": 8,
            "extractor": f"pypdf {EXPECTED_PYPDF}",
            "source_identities": {kind: source[kind]["identity"] for kind in ("txt", "pdf")},
            "module_a": module,
            "limitations": ["Only printed Module A rows represented; remaining Level 92 and Curriculum review Pending",
                            "Rake instructions and target placements are source text, not performed proof",
                            "No canonical IDs, runtime admission, pitch, actual muting, timing or audio/physical result"]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(BUILD.resolve()):
        parser.error("output must remain under Build/parallel-06/2.3-level092-music-r01")
    payload = build()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
