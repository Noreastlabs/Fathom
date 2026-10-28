#!/usr/bin/env python3
"""Build detached source-literal Level 91 Module A bend-intonation cells."""

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
BUILD = ROOT / "Build/parallel-06/2.3-level091-music-r01"
EXPECTED_PYPDF = "6.10.0"
SOURCE = {
    "txt": ("Notes/music/guitar project/TXT version/Guitar_Exercises_Section_XIII_Level_91_Advanced_Bend_Intonation_Unison_Oblique_Bends_Vibrato_Architecture_Expressive_Timing_and_Dynamic_Attack.txt", 1162, "0fac712a8e4ac90d43fc218bb0b68063f139c53523c4c28c442921b8e1f118b7"),
    "pdf": ("Notes/music/guitar project/PDF version/Guitar_Exercises_Section_XIII_Level_91_Advanced_Bend_Intonation_Unison_Oblique_Bends_Vibrato_Architecture_Expressive_Timing_and_Dynamic_Attack.pdf", 41521, "653762bdb591329d04a382df20b6bd57bbe8050e971cf5d081bc549ba5374fc1"),
    "page_count": 17,
}
EXAMPLE = re.compile(r"(B|G|e)(\d+) -> (B|G|e)(\d+)")
STEP_LABELS = {"half-step": "Half", "whole-step": "Whole", "1.5-step": "1.5 step"}


class CandidateError(ValueError):
    """The original source or a printed bend-interval relation changed."""


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
        verify_bytes(raw, size, digest, f"Level 91 {kind}")
        content = raw.decode("utf-8").splitlines() if kind == "txt" else [page.extract_text() or "" for page in PdfReader(path).pages]
        if kind == "pdf" and len(content) != SOURCE["page_count"]:
            raise CandidateError("Level 91 PDF page count drift")
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


def calibration(pages: list[str]) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    ref = pdf_ref(pages, 2, "Bend Calibration")
    rows = table(pages[1], "Bend\nSemitones\nMethod\n", "Use a clean/lightly driven tone first.", 3, 6)
    expected_labels = ["Quarter shade", "Half", "Whole", "1.5 step", "Pre-bend", "Release"]
    if [row[0] for row in rows] != expected_labels:
        raise CandidateError("calibration label order drift")
    expected = {"Half": 1, "Whole": 2, "1.5 step": 3}
    selected = {}
    for label, semitones, method in rows:
        if label not in expected:
            continue
        if semitones != str(expected[label]) or method != f"play target +{semitones} fret{'s' if semitones != '1' else ''}, return, match":
            raise CandidateError(f"calibration interval/method drift: {label}")
        selected[label] = {"printed_label": label, "printed_semitones": semitones,
                           "printed_method": method, "pdf": ref}
    if len(selected) != 3:
        raise CandidateError("calibration interval coverage drift")
    return selected, ref


def parse_example(example: str, task: str, references: dict[str, dict[str, Any]]) -> dict[str, Any]:
    match = EXAMPLE.fullmatch(example)
    if match is None or match.group(1) != match.group(3):
        raise CandidateError(f"different/invalid string in bend example: {example}")
    source_fret, target_fret = int(match.group(2)), int(match.group(4))
    if source_fret < 0 or target_fret > 24 or target_fret <= source_fret:
        raise CandidateError(f"invalid printed fret span: {example}")
    interval = next((label for label in STEP_LABELS if task == label or task.startswith(label + " + ")), None)
    if interval is None:
        raise CandidateError(f"unsupported printed task: {task}")
    if task != interval and task != "half-step + 2-beat hold":
        raise CandidateError(f"unsupported extra bend instruction: {task}")
    calibration_label = STEP_LABELS[interval]
    expected_delta = int(references[calibration_label]["printed_semitones"])
    if target_fret - source_fret != expected_delta:
        raise CandidateError(f"printed fret/interval mismatch: {example}/{task}")
    return {"printed_string_token": match.group(1), "source_fret": source_fret,
            "target_reference_fret": target_fret, "printed_interval_label": interval,
            "reference_semitones": expected_delta, "printed_additional_instruction":
                "2-beat hold" if task != interval else None}


def module_a(source: dict[str, Any]) -> dict[str, Any]:
    lines, pages = source["txt"]["content"], source["pdf"]["content"]
    module_line = exact_line(lines, "A. Bend calibration - 144 events")
    skill_line = exact_line(lines, "- half-, whole-, and 1.5-step bend calibration")
    references, calibration_ref = calibration(pages)
    example_ref = pdf_ref(pages, 3, "Module A - Bend Intonation")
    rows = table(pages[2], "Cell\nExample\nTask\n", "Use a clean/lightly driven tone first.", 3, 8)
    chosen = []
    txt_content = "\n".join(lines)
    for number, (label, example, task) in enumerate(rows, 1):
        if label != str(number) or example in txt_content:
            raise CandidateError(f"Module A PDF-only row drift: {number}")
        chosen.append({"local_key": f"bend-intonation-{number}", "printed_example": example,
                       "printed_task": task, **parse_example(example, task, references),
                       "txt_module_anchor_line": module_line, "txt_skill_anchor_line": skill_line,
                       "txt_cell_detail": "omitted", "pdf": example_ref,
                       "actual_target_pitch": None, "bend_curve": None,
                       "performed_arrival_and_hold_timing": None, "fingering": None,
                       "audio_or_physical_result": None})
    return {"module": "A", "selected_pdf_page": example_ref,
            "supporting_calibration_page": calibration_ref, "calibration_reference": references,
            "cells": chosen, "selected_cell_count": 8,
            "printed_instruction": "Use a clean/lightly driven tone first. Record and verify consistency before adding more ornament.",
            "txt_relation": "module and interval skills named in TXT; eight detailed examples omitted"}


def build(root: Path = ROOT) -> dict[str, Any]:
    source = read_source(root)
    module = module_a(source)
    return {"wbs": "2.3.1.3.1", "level": 91, "section": "XIII",
            "status": "Pending", "review": "Pending", "detached_source_candidate": True,
            "canonical_ids_allocated": False, "runtime_eligible": False,
            "whole_workbook_complete": False, "selected_cell_count": 8,
            "extractor": f"pypdf {EXPECTED_PYPDF}",
            "source_identities": {kind: source[kind]["identity"] for kind in ("txt", "pdf")},
            "module_a": module,
            "limitations": ["Only printed Module A example rows represented; remaining Level 91 and Curriculum review Pending",
                            "Reference frets and interval labels are source data, not performed intonation proof",
                            "No canonical IDs, runtime admission, pitch/bend curve, timing or audio/physical result"]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(BUILD.resolve()):
        parser.error("output must remain under Build/parallel-06/2.3-level091-music-r01")
    payload = build()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
