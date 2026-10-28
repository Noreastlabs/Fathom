#!/usr/bin/env python3
"""Build detached, source-literal Level 96 Module A missing-information pairs."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from pypdf import PdfReader, __version__ as PYPDF_VERSION


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "Build/parallel-06/2.3-level096-music-r01"
EXPECTED_PYPDF = "6.10.0"
SOURCE = {
    "txt": ("Notes/music/guitar project/TXT version/Guitar_Exercises_Section_XIV_Level_96_Chart_to_Performance_Repertoire_Reconstruction_Selective_Transcription_Independent_Voicing_Style_Decisions_and_Rehearsal_Planning.txt", 1646, "2d2b8e84da6fd16994d078cd779bc8c963a7b1b5e4cbee03e360de97cb80c54b"),
    "pdf": ("Notes/music/guitar project/PDF version/Guitar_Exercises_Section_XIV_Level_96_Chart_to_Performance_Repertoire_Reconstruction_Selective_Transcription_Independent_Voicing_Style_Decisions_and_Rehearsal_Planning.pdf", 45292, "51435c2e4537fccb536a6ba109d73db1a317247cbd4206ad3d67a5d4f986283f"),
    "page_count": 18,
}
GUIDANCE = "Mark each answer: supplied, must transcribe, safe to choose, or safe to omit."
CLASSIFICATION_OPTIONS = ("supplied", "must transcribe", "safe to choose", "safe to omit")
EXPECTED_PAIRS = (
    ("Chord chart gives C-Am-F-G", "What voicings fit the register/style?"),
    ("Chart says 'shuffle'", "What subdivision and note lengths define it?"),
    ("Slash chord appears", "Is bass note structural or optional?"),
    ("No intro written", "Does recording establish a pickup/figure?"),
    ("No fills written", "Which fills are identity-defining?"),
    ("Repeat signs only", "What changes on later repetitions?"),
    ("Final chord shown", "How is the ending actually articulated?"),
    ("Tempo shown", "Does performance feel ahead/on/behind?"),
)


class CandidateError(ValueError):
    """The pinned source or a printed audit pair changed."""


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
        verify_bytes(raw, size, digest, f"Level 96 {kind}")
        content = (raw.decode("utf-8").splitlines() if kind == "txt"
                   else [page.extract_text() or "" for page in PdfReader(path).pages])
        if kind == "pdf" and len(content) != SOURCE["page_count"]:
            raise CandidateError("Level 96 PDF page count drift")
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
    start = "Module A - Lead-Sheet Missing-Information Audit\nPrompt\nDecision\n"
    end = "\n" + GUIDANCE
    if not page.startswith(start) or page.count(start) != 1 or page.count(end) != 1:
        raise CandidateError("Module A page/table boundary drift")
    fields = page.split(start, 1)[1].split(end, 1)[0].splitlines()
    if len(fields) != 8 * 2:
        raise CandidateError(f"Module A table shape drift: {len(fields)} fields")
    return [fields[i:i + 2] for i in range(0, len(fields), 2)], {
        "page": 3, "extracted_text_sha256": sha(page.encode("utf-8"))}


def checked_pair(number: int, pair: list[str]) -> dict[str, str]:
    if len(pair) != 2 or tuple(pair) != EXPECTED_PAIRS[number - 1]:
        raise CandidateError(f"Module A audit pair {number} drift")
    return {"printed_prompt": pair[0], "printed_decision_question": pair[1]}


def module_a(source: dict[str, Any]) -> dict[str, Any]:
    lines, pages = source["txt"]["content"], source["pdf"]["content"]
    module_line = exact_line(lines, "A. Lead-sheet reduction and missing-information audit - 96 events")
    skill_line = exact_line(lines, "- missing-information audit")
    rows, page_ref = selected_page(pages)
    cells = []
    txt_content = "\n".join(lines)
    if GUIDANCE in txt_content:
        raise CandidateError("Module A guidance unexpectedly present in TXT")
    for number, pair in enumerate(rows, 1):
        if pair[0] in txt_content or pair[1] in txt_content:
            raise CandidateError(f"Module A PDF-only pair drift: {number}")
        cells.append({"local_key": f"missing-info-pair-{number}",
                      **checked_pair(number, pair),
                      "classification_assigned": None, "learner_answer": None,
                      "song_or_recording_finding": None,
                      "txt_module_anchor_line": module_line, "txt_skill_anchor_line": skill_line,
                      "txt_cell_detail": "omitted", "pdf": page_ref})
    return {"module": "A", "selected_pdf_page": page_ref, "selected_pdf_rows": "1-8",
            "selected_cell_count": len(cells), "cells": cells,
            "printed_classification_guidance": GUIDANCE,
            "printed_classification_options": list(CLASSIFICATION_OPTIONS),
            "txt_relation": "module and missing-information skill named in TXT; detailed pairs omitted"}


def build(root: Path = ROOT) -> dict[str, Any]:
    source = read_source(root)
    module = module_a(source)
    return {"wbs": "2.3.1.3.1", "level": 96, "section": "XIV",
            "status": "Pending", "review": "Pending", "detached_source_candidate": True,
            "canonical_ids_allocated": False, "runtime_eligible": False,
            "whole_workbook_complete": False, "selected_cell_count": 8,
            "extractor": f"pypdf {EXPECTED_PYPDF}",
            "source_identities": {kind: source[kind]["identity"] for kind in ("txt", "pdf")},
            "module_a": module,
            "limitations": ["Only printed Module A audit pairs represented; remaining Level 96 and Curriculum review Pending",
                            "Classification options are source guidance; no answer is assigned",
                            "No canonical IDs, runtime admission, learner/song/recording judgment or performance result"]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(BUILD.resolve()):
        parser.error("output must remain under Build/parallel-06/2.3-level096-music-r01")
    payload = build()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
