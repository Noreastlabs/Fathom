#!/usr/bin/env python3
"""Build a detached Level85 TXT/PDF source-structure index, without runtime events."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
from io import BytesIO
from pathlib import Path
from typing import Any

import pypdf
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
BUILD_REL = Path("Build/parallel-03/2.3.1.3.1-level-085-whole-source-index-r01")
SOURCE_MAP = "Results/parallel-01/exercises/inventory/20260922T180500Z-2.3-curriculum-v1-source-inventory-evidence/curriculum-source-map.json"
CATALOG = "Content/controls/curriculum-v1/package.json"
COVERAGE = "Results/parallel-01/exercises/conversion/20260923T021155Z-2.3.1.3.1-pdf-txt-passage-coverage-r01-evidence/pdf-txt-coverage-report.json"
TXT = "Notes/music/guitar project/TXT version/Guitar_Exercises_Section_XII_Level_85_Pocket_Note_Length_Muting_Attack_Placement_and_Drum_Bass_Lock.txt"
PDF = "Notes/music/guitar project/PDF version/Guitar_Exercises_Section_XII_Level_85_Pocket_Note_Length_Muting_Attack_Placement_and_Drum_Bass_Lock.pdf"
APPENDIX = "Results/parallel-03/exercises/conversion/20260923T031000Z-2.3.1.3.1-pdf-source-appendices-levels-084-085-evidence/levels-084-085-pdf-source-candidate.json"
APPENDIX_RESULT = "Results/parallel-03/exercises/conversion/20260923T031000Z-2.3.1.3.1-pdf-source-appendices-levels-084-085-results.md"
SCHEMA_FREEZE = "Results/primary/20260912T100538Z-2.1.1.2.1-r02-evidence/schema-freeze.json"
M1_ACCEPTANCE = "Results/primary/20260912T092802Z-11.4.1.1.1-r03-evidence/acceptance.json"

PINNED: dict[str, tuple[int, str]] = {
    SOURCE_MAP: (199753, "bad5581a04f43ba8baf14db430449e1ccff5cf88f0f7e42198328073b27053d6"),
    CATALOG: (24698658, "766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255"),
    COVERAGE: (3123277, "968318ab8d5559b742b2871e217d254fe424d6ee5efa72c084d91d44962b7631"),
    TXT: (1534, "8ca7ce364dac61adae9cbcf2dfd4cb800a10107523dc74e23014585e0cee33f7"),
    PDF: (41449, "9ea3d4547e28ac2feb30659ee9d45af4ea84102d9f9a23837234ea37b6951323"),
    APPENDIX: (53063, "cc8136d97f9b3070c1688b2b49e4495222349ef0d7baff1e065d921775e9be57"),
    APPENDIX_RESULT: (7675, "c7eaf04d99a111da3d02a783ae7b800fa1a6b52bd5f028477101d749585eab18"),
    SCHEMA_FREEZE: (2737, "0659fa962a5c933a2bcf3045772b6fe5b05b4deefb3511f5dcb68af51088de95"),
    M1_ACCEPTANCE: (2745, "730fa18677abf1a4feb802bb135d70b8b8b261b637e6703e8f3290dceace63ce"),
}
PYPDF_VERSION = "6.10.0"
WORKBOOK_ID = "fg:workbook:000085"
EXPECTED_PAGE_HASHES = {
    1: "f61f97f72e28b344188c143fd14e024cd8ca11a6fd695f71c53689ac2309014d",
    2: "65575fcf69dbe5db651e7fdbb80cf626d3559ae306bf76c06f0f8bfae406d2b7",
    3: "b78ada3a692d361cd9e5a46bc40dced94e5efb22b0052041d4b391293cd85f4b",
    4: "08de636779583e582013c0c564aab57ef6e0e7dd2db1fc63892ef26ba5ac31be",
    5: "3a86702eee9b98a69738b4c49045b16c81dff48a535047bfbaf55e34cbcb3308",
    6: "a9c665ca61bb018796d024aefc595754d6f27b208599827f4f3f11e195740e41",
    7: "e1abc34dae0a64ae65fe7a51cb2074a28fa0e36c7b551f63b48f3f49951d2a5c",
    8: "946b34c5c8cf93a92f64c049e9fde5b45ee70a1cdbebf061bb431d136485daec",
    9: "5f1189d2b4687823ddf2c3f4ab53de48f30fed0816ed80959c9af0fc145e95f3",
    10: "1d7d22d809d5036ea97f201d7ec5b65f1e4e9d2862266c0fbc798e4fb34f7501",
    11: "c9339df9cba342fa5404b8a27436b1fd51ca8f7c57158dc757ab03bcdd5fbd6e",
    12: "0039b2fdf18a9fd527acbf2603ba92ade58b44952164e03ed4c30fad1706ea9d",
    13: "3ce569d3c304fa080d647d6f1f11b411d0f19fb7ac828fc17d478071c0e2605a",
    14: "ddac7f086c8592fbf00963087d3be8873dfdf598138445db3ca8afc99be4ed69",
    15: "0911217ba31c46a4efe89a11e46af3424c4a8f3856aab49f1ddaef79fef7d13e",
}
EXPECTED_MODULES = (
    ("A", "Subdivision-to-groove conversion", 128),
    ("B", "Note-length ladder: legato to clipped", 128),
    ("C", "Muting and ghost-contact control", 144),
    ("D", "Kick/snare lock and backbeat placement", 144),
    ("E", "Bass-guitar interlock and register separation", 128),
    ("F", "Ahead/on/behind placement laboratory", 96),
    ("G", "Eight groove cells with identical harmony", 160),
    ("H", "Four eight-bar pocket studies", 192),
    ("I", "Thirty-two-bar groove capstone", 256),
    ("J", "Recovery and pocket audit", 64),
)
DETAIL_HEADINGS = {
    3: ("A", "Module A - Subdivision-to-Groove Conversion"),
    4: ("B", "Module B - Note-Length Ladder"),
    5: ("C", "Module C - Muting and Ghost Contacts"),
    6: ("D", "Module D - Locking to Kick and Snare"),
    7: ("E", "Module E - Bass/Guitar Interlock"),
    8: ("F", "Module F - Ahead, On, and Behind the Beat"),
    9: ("G", "Module G - Eight Groove Cells, Same Harmonic Skills"),
    10: ("H", "Module H - Study 1 - Rock pocket"),
    11: ("H", "Module H - Study 2 - Funk pocket"),
    12: ("H", "Module H - Study 3 - Offbeat pocket"),
    13: ("H", "Module H - Study 4 - Soul pocket"),
    14: ("I", "Module I - Thirty-Two-Bar Groove Capstone"),
    15: ("J", "Module J - Pocket Audit and Recovery"),
}
EXPECTED_I_ROWS = (
    ("1-4", "G-D-Em-C", "straight rock", "mf", "middle"),
    ("5-8", "Am7-D9-Am7-E7#9", "funk", "mp", "upper"),
    ("9-12", "C-F-G-C", "offbeat", "mp", "upper"),
    ("13-16", "Cmaj7-Am7-Dm7-G7", "soul/R&B", "mf", "middle"),
    ("17-20", "A7-D7-E7-A7", "shuffle", "f", "middle"),
    ("21-24", "Am7-D7-Gmaj7-Cmaj7", "disco", "f", "upper"),
    ("25-28", "G-C-D-G", "country two-step", "mf", "low+upper"),
    ("29-32", "A-D-A-E", "jam-band pocket", "mp -> f -> p", "wide"),
)
I_HEADERS = ("Bars", "Harmony", "Groove", "Dynamic", "Register")
MODULE_LINE_RE = re.compile(r"(?P<label>[A-J])\. (?P<title>.+) - (?P<count>[0-9]+) events")


class CandidateError(ValueError):
    """Raised when a pinned source or literal structure violates the contract."""


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def assert_git_root(root: Path) -> None:
    root = root.resolve(strict=True)
    proc = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise CandidateError(f"GIT_ROOT_UNAVAILABLE {proc.stderr.strip()}")
    actual = Path(proc.stdout.strip()).resolve(strict=True)
    if actual != root:
        raise CandidateError(f"GIT_ROOT_MISMATCH expected-top-level={actual} supplied={root}")


def safe_input(root: Path, relative: str) -> Path:
    rel = Path(relative)
    if rel.is_absolute() or not rel.parts or any(part in ("", ".", "..") for part in rel.parts):
        raise CandidateError(f"UNSAFE_INPUT_PATH {relative}")
    current = root
    for part in rel.parts:
        current = current / part
        if current.is_symlink():
            raise CandidateError(f"INPUT_SYMLINK {relative}")
    try:
        resolved = (root / rel).resolve(strict=True)
    except OSError as exc:
        raise CandidateError(f"INPUT_MISSING {relative}: {exc}") from exc
    if not resolved.is_relative_to(root) or not resolved.is_file():
        raise CandidateError(f"INPUT_NOT_REGULAR_OR_ESCAPES_ROOT {relative}")
    if not stat.S_ISREG(resolved.stat().st_mode):
        raise CandidateError(f"INPUT_NOT_REGULAR {relative}")
    return resolved


def read_pinned(root: Path, relative: str) -> bytes:
    raw = safe_input(root, relative).read_bytes()
    expected_bytes, expected_sha = PINNED[relative]
    if len(raw) != expected_bytes or sha(raw) != expected_sha:
        raise CandidateError(f"PINNED_INPUT_DRIFT {relative}")
    return raw


def one(values: list[dict[str, Any]], predicate, label: str) -> dict[str, Any]:
    found = [value for value in values if predicate(value)]
    if len(found) != 1:
        raise CandidateError(f"EXPECTED_ONE {label} got={len(found)}")
    return found[0]


def line_records(text: str, *, require_lf: bool = True) -> list[dict[str, Any]]:
    if "\r" in text:
        raise CandidateError("TXT_NEWLINE_NOT_LF")
    if require_lf and not text.endswith("\n"):
        raise CandidateError("TXT_TERMINAL_NEWLINE_MISSING")
    raw_lines = text.splitlines(keepends=True)
    if raw_lines and raw_lines[-1] == "":
        raw_lines.pop()
    records: list[dict[str, Any]] = []
    offset = 0
    for number, raw_line in enumerate(raw_lines, 1):
        if not raw_line.endswith("\n"):
            raise CandidateError(f"TXT_LINE_TERMINATOR_MISSING line={number}")
        literal = raw_line[:-1]
        records.append({
            "line_number": number,
            "literal": literal,
            "source_position": {
                "start_char": offset,
                "end_char_exclusive": offset + len(literal),
                "literal_sha256": sha(literal.encode("utf-8")),
            },
        })
        offset += len(raw_line)
    return records


def parse_module_rows(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if len(records) != 40:
        raise CandidateError(f"TXT_LINE_COUNT expected=40 actual={len(records)}")
    if records[3]["literal"] != "LEVEL 85 OF 105 - HARD STOP AFTER LEVEL 105":
        raise CandidateError("TXT_LEVEL_OR_HARD_STOP_LINE_CHANGED")
    if records[8]["literal"] != "COMPLETE WRITTEN WORKLOAD: 1440 events":
        raise CandidateError("TXT_TOTAL_WORKLOAD_CHANGED")
    rows: list[dict[str, Any]] = []
    for index, expected in enumerate(EXPECTED_MODULES, 12):
        record = records[index - 1]
        match = MODULE_LINE_RE.fullmatch(record["literal"])
        if not match:
            raise CandidateError(f"TXT_MODULE_LINE_SHAPE line={index}")
        label, title, count = match.group("label", "title", "count")
        if (label, title, int(count)) != expected:
            raise CandidateError(f"TXT_MODULE_LITERAL_DRIFT line={index}")
        start = record["source_position"]["start_char"]
        rows.append({
            "module_label": label,
            "title_literal": title,
            "declared_workload_literal": f"{count} events",
            "declared_workload_value": int(count),
            "txt_line_number": index,
            "txt_line_position": record["source_position"],
            "title_source_position": {
                "start_char": start + match.start("title"),
                "end_char_exclusive": start + match.end("title"),
                "literal_sha256": sha(title.encode("utf-8")),
            },
            "workload_source_position": {
                "start_char": start + match.start("count"),
                "end_char_exclusive": start + match.end("count"),
                "literal_sha256": sha(count.encode("utf-8")),
            },
        })
    if records[32]["literal"] != "32 bars, eight groove environments, one continuous tempo.":
        raise CandidateError("TXT_CAPSTONE_LINE_CHANGED")
    if records[35]["literal"] != "14/16 or better on two separate days." or records[36]["literal"] != "No zero in pulse, note length, muting, or recovery.":
        raise CandidateError("TXT_MASTERY_LINES_CHANGED")
    if not records[39]["literal"].startswith("Level 86: ") or "HARD STOP AFTER LEVEL 105" not in records[3]["literal"]:
        raise CandidateError("TXT_NEXT_LEVEL_BOUNDARY_CHANGED")
    total = sum(row["declared_workload_value"] for row in rows)
    if total != 1440:
        raise CandidateError(f"TXT_MODULE_WORKLOAD_SUM expected=1440 actual={total}")
    return rows


def page_line_records(text: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    offset = 0
    for number, line in enumerate(text.splitlines(keepends=True), 1):
        literal = line[:-1] if line.endswith("\n") else line
        records.append({
            "line_number": number,
            "literal": literal,
            "source_position": {
                "start_char": offset,
                "end_char_exclusive": offset + len(literal),
                "literal_sha256": sha(literal.encode("utf-8")),
            },
        })
        offset += len(line)
    return records


def parse_pdf_index(page_text: str, txt_rows: list[dict[str, Any]]) -> dict[str, Any]:
    lines = page_line_records(page_text)
    header_indexes = [
        i for i in range(len(lines) - 2)
        if tuple(lines[i + n]["literal"] for n in range(3)) == ("Module", "Exercise", "Events")
    ]
    if len(header_indexes) != 1:
        raise CandidateError("PDF_INDEX_HEADER_NOT_UNIQUE")
    header_index = header_indexes[0]
    expected_titles = [(letter, title, count) for letter, title, count in EXPECTED_MODULES]
    rows = []
    cursor = header_index + 3
    for ordinal, (letter, title, count) in enumerate(expected_titles, 1):
        cell_lines = lines[cursor:cursor + 3]
        if len(cell_lines) != 3:
            raise CandidateError("PDF_INDEX_ROWS_TRUNCATED")
        actual = (cell_lines[0]["literal"], cell_lines[1]["literal"], cell_lines[2]["literal"])
        if actual != (letter, title, str(count)):
            raise CandidateError(f"PDF_INDEX_ROW_DRIFT position={ordinal}")
        rows.append({
            "printed_row_position": ordinal,
            "module_label": letter,
            "exercise_title_literal": title,
            "declared_workload_literal": str(count),
            "declared_workload_value": count,
            "pdf_source_positions": {
                "module_label": cell_lines[0]["source_position"],
                "exercise_title": cell_lines[1]["source_position"],
                "declared_workload": cell_lines[2]["source_position"],
            },
        })
        cursor += 3
    if cursor + 1 >= len(lines) or (lines[cursor]["literal"], lines[cursor + 1]["literal"]) != ("TOTAL", "1440"):
        raise CandidateError("PDF_INDEX_TOTAL_CHANGED")
    return {
        "page_number": 1,
        "header_literal": "Module\nExercise\nEvents",
        "header_source_position": {
            "start_char": lines[header_index]["source_position"]["start_char"],
            "end_char_exclusive": lines[header_index + 2]["source_position"]["end_char_exclusive"],
            "literal_sha256": sha("Module\nExercise\nEvents".encode("utf-8")),
        },
        "rows": rows,
        "declared_total_literal": "1440",
        "declared_total_source_position": lines[cursor + 1]["source_position"],
        "module_workload_sum": sum(row["declared_workload_value"] for row in rows),
        "meaning": "Printed source index labels and workload declarations only; no event model is emitted.",
    }


def parse_i_table(page_text: str) -> dict[str, Any]:
    lines = page_line_records(page_text)
    header_indexes = [
        i for i in range(len(lines) - len(I_HEADERS) + 1)
        if tuple(lines[i + n]["literal"] for n in range(len(I_HEADERS))) == I_HEADERS
    ]
    if len(header_indexes) != 1:
        raise CandidateError("PDF_I_TABLE_HEADER_NOT_UNIQUE")
    header_index = header_indexes[0]
    cursor = header_index + len(I_HEADERS)
    rows = []
    for ordinal, expected in enumerate(EXPECTED_I_ROWS, 1):
        cell_lines = lines[cursor:cursor + len(I_HEADERS)]
        actual = tuple(item["literal"] for item in cell_lines)
        if actual != expected:
            raise CandidateError(f"PDF_I_TABLE_ROW_DRIFT position={ordinal}")
        rows.append({
            "printed_row_position": ordinal,
            "literal_fields": dict(zip(I_HEADERS, actual)),
            "pdf_source_positions": dict(zip(I_HEADERS, [item["source_position"] for item in cell_lines])),
        })
        cursor += len(I_HEADERS)
    return {
        "page_number": 14,
        "table_headers": list(I_HEADERS),
        "rows": rows,
        "printed_bar_range_count": len(rows),
        "printed_bar_ranges": [row["literal_fields"]["Bars"] for row in rows],
        "declared_event_workload_reference": {"txt_line_number": 20, "literal": "256 events"},
        "event_mapping": None,
        "interpretation_limit": "Eight printed four-bar ranges are source table rows. The TXT declares 256 events but supplies no mapping from those events to these ranges; no per-event timing or schedule is inferred.",
    }


def read_inputs(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve(strict=True)
    assert_git_root(root)
    if pypdf.__version__ != PYPDF_VERSION:
        raise CandidateError(f"PYPDF_VERSION expected={PYPDF_VERSION} actual={pypdf.__version__}")
    raw = {relative: read_pinned(root, relative) for relative in PINNED}
    try:
        source_map = json.loads(raw[SOURCE_MAP].decode("utf-8"))
        catalog = json.loads(raw[CATALOG].decode("utf-8"))
        coverage = json.loads(raw[COVERAGE].decode("utf-8"))
        appendix = json.loads(raw[APPENDIX].decode("utf-8"))
        schema_freeze = json.loads(raw[SCHEMA_FREEZE].decode("utf-8"))
        m1_acceptance = json.loads(raw[M1_ACCEPTANCE].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CandidateError(f"PINNED_JSON_INVALID {exc}") from exc

    map_row = one(source_map.get("rows", []), lambda row: row.get("level") == 85, "Level85 source-map row")
    if any(map_row.get(key) != value for key, value in {
        "level": 85,
        "section": "XII",
        "wbs_owner": "2.3.1.3.1",
        "pair_status": "exact_stem_pair",
        "txt_path": TXT,
        "txt_bytes": PINNED[TXT][0],
        "txt_sha256": PINNED[TXT][1],
        "pdf_path": PDF,
        "pdf_bytes": PINNED[PDF][0],
        "pdf_sha256": PINNED[PDF][1],
        "review": "Pending",
        "conversion_status": "not_converted",
        "stable_ids_assigned": False,
        "runtime_eligible": False,
        "imported": False,
        "admitted": False,
    }.items()):
        raise CandidateError("LEVEL85_SOURCE_MAP_BINDING_OR_STATUS_CHANGED")

    if catalog.get("content_version") != "curriculum-v1-level009-659-build-only-candidate.1" or len(catalog.get("records", [])) != 659:
        raise CandidateError("CURRENT_CANONICAL_REFERENCE_SNAPSHOT_CHANGED")
    workbook_catalog = catalog.get("workbook_catalog", {})
    if workbook_catalog.get("catalog_version") != "curriculum-v1-workbook-source-catalog.5":
        raise CandidateError("WORKBOOK_CATALOG_VERSION_CHANGED")
    entry = one(workbook_catalog.get("entries", []), lambda item: item.get("workbook_id") == WORKBOOK_ID, "Level85 catalog entry")
    if any(entry.get(key) != value for key, value in {
        "review": "Pending",
        "conversion_status": "not_converted",
        "runtime_eligible": False,
        "runtime_admitted": False,
        "imported": False,
        "admitted": False,
        "whole_workbook_complete": False,
    }.items()):
        raise CandidateError("LEVEL85_CATALOG_STATUS_CHANGED")
    txt_entry, pdf_entry = entry.get("txt", {}), entry.get("pdf", {})
    if (
        (txt_entry.get("path"), txt_entry.get("bytes"), txt_entry.get("sha256"), txt_entry.get("encoding"), txt_entry.get("line_count"))
        != (TXT, PINNED[TXT][0], PINNED[TXT][1], "utf-8", 40)
        or (pdf_entry.get("path"), pdf_entry.get("bytes"), pdf_entry.get("sha256"), pdf_entry.get("page_count"))
        != (PDF, PINNED[PDF][0], PINNED[PDF][1], 15)
        or pdf_entry.get("extraction", {}).get("engine") != "pypdf"
        or pdf_entry.get("extraction", {}).get("version") != PYPDF_VERSION
    ):
        raise CandidateError("LEVEL85_CATALOG_SOURCE_BINDING_CHANGED")

    txt_text = raw[TXT].decode("utf-8", errors="strict")
    txt_records = line_records(txt_text)
    txt_modules = parse_module_rows(txt_records)
    catalog_txt_lines = txt_entry.get("lines", [])
    if len(catalog_txt_lines) != len(txt_records) or any(
        (cached.get("line_number"), cached.get("text")) != (record["line_number"], record["literal"])
        for cached, record in zip(catalog_txt_lines, txt_records)
    ):
        raise CandidateError("LEVEL85_CATALOG_TXT_LINES_CHANGED")

    reader = PdfReader(BytesIO(raw[PDF]))
    if len(reader.pages) != 15:
        raise CandidateError(f"PDF_PAGE_COUNT expected=15 actual={len(reader.pages)}")
    pdf_pages = [(page.extract_text() or "") for page in reader.pages]
    page_hashes = {page_no: sha(text.encode("utf-8")) for page_no, text in enumerate(pdf_pages, 1)}
    if page_hashes != EXPECTED_PAGE_HASHES:
        raise CandidateError("LEVEL85_SELECTED_PDF_PAGE_HASHES_CHANGED")
    cached_pdf_pages = pdf_entry.get("pages", [])
    if len(cached_pdf_pages) != 15 or [page.get("page_number") for page in cached_pdf_pages] != list(range(1, 16)):
        raise CandidateError("LEVEL85_CATALOG_PDF_PAGE_ORDER_CHANGED")
    for number, (page_text, cached) in enumerate(zip(pdf_pages, cached_pdf_pages), 1):
        if (
            cached.get("full_pdf_sha256") != PINNED[PDF][1]
            or cached.get("extracted_text_sha256") != page_hashes[number]
            or cached.get("extracted_text") != page_text
        ):
            raise CandidateError(f"LEVEL85_CATALOG_PAGE_CACHE_CHANGED page={number}")

    appendix_wb = one(appendix.get("workbooks", []), lambda item: item.get("level") == 85, "prior appendix Level85 workbook")
    if (
        appendix.get("artifact_type") != "curriculum_pdf_gap_source_appendix"
        or appendix.get("candidate_status") != "pending_source_reconciliation"
        or appendix.get("runtime_eligible") is not False
        or appendix.get("imported") is not False
        or appendix.get("admitted") is not False
        or appendix_wb.get("workbook_id") != WORKBOOK_ID
        or appendix_wb.get("source_pair", {}).get("pdf", {}).get("sha256") != PINNED[PDF][1]
        or appendix_wb.get("source_pair", {}).get("txt", {}).get("sha256") != PINNED[TXT][1]
    ):
        raise CandidateError("PRIOR_APPENDIX_LEVEL85_BINDING_OR_STATUS_CHANGED")
    appendix_pages = appendix_wb.get("source_pages", [])
    if len(appendix_pages) != 15 or [item.get("page_number") for item in appendix_pages] != list(range(1, 16)):
        raise CandidateError("PRIOR_APPENDIX_LEVEL85_PAGE_SET_CHANGED")
    for number, (page_text, appendix_page) in enumerate(zip(pdf_pages, appendix_pages), 1):
        if (
            appendix_page.get("literal_extracted_text") != page_text
            or appendix_page.get("literal_extracted_text_sha256") != page_hashes[number]
        ):
            raise CandidateError(f"PRIOR_APPENDIX_PAGE_TEXT_CHANGED page={number}")

    coverage_row = one(coverage.get("workbooks", []), lambda item: item.get("workbook_id") == WORKBOOK_ID, "Level85 coverage row")
    if coverage_row.get("level") != 85:
        raise CandidateError("LEVEL85_COVERAGE_LEVEL_CHANGED")
    coverage_pages = coverage_row.get("pages", [])
    if len(coverage_pages) != 15 or [item.get("page_number") for item in coverage_pages] != list(range(1, 16)):
        raise CandidateError("LEVEL85_COVERAGE_PAGE_ORDER_CHANGED")
    expected_class = {1: "partial_literal_overlap", 3: "partial_literal_overlap", 14: "partial_literal_overlap", 15: "partial_literal_overlap"}
    for number, coverage_page in enumerate(coverage_pages, 1):
        if (
            coverage_page.get("pdf_extracted_text_sha256") != page_hashes[number]
            or coverage_page.get("pdf_source_path") != PDF
            or coverage_page.get("pdf_source_sha256") != PINNED[PDF][1]
            or coverage_page.get("txt_source_path") != TXT
            or coverage_page.get("txt_source_sha256") != PINNED[TXT][1]
        ):
            raise CandidateError(f"LEVEL85_COVERAGE_PAGE_BINDING_CHANGED page={number}")
        expected = expected_class.get(number, "no_exact_five_token_window_found")
        if coverage_page.get("classification") != expected:
            raise CandidateError(f"LEVEL85_COVERAGE_CLASSIFICATION_CHANGED page={number}")

    if schema_freeze.get("decision") != "Technical schema1 FROZEN" or schema_freeze.get("schema_version") != "1.0.0-curriculum-candidate":
        raise CandidateError("SCHEMA_PREDECESSOR_STATUS_CHANGED")
    criteria = m1_acceptance.get("criteria", {})
    if (
        m1_acceptance.get("wbs_id") != "11.4.1.1.1"
        or m1_acceptance.get("lane_status") != "Done"
        or m1_acceptance.get("work_package_status") != "ACCEPTED"
        or m1_acceptance.get("human_acceptance") is not False
        or not criteria
        or any(value != "PASS" for value in criteria.values())
    ):
        raise CandidateError("M1_PREDECESSOR_STATUS_CHANGED")

    return {
        "root": root,
        "raw": raw,
        "map_row": map_row,
        "catalog": catalog,
        "catalog_entry": entry,
        "coverage_pages": coverage_pages,
        "txt_text": txt_text,
        "txt_records": txt_records,
        "txt_modules": txt_modules,
        "pdf_pages": pdf_pages,
        "page_hashes": page_hashes,
        "catalog_pdf_pages": cached_pdf_pages,
        "appendix_pages": appendix_pages,
        "appendix_wb": appendix_wb,
    }


def _page_span(text: str, literal: str, start: int = 0) -> dict[str, Any]:
    index = text.find(literal, start)
    if index < 0:
        raise CandidateError(f"SOURCE_LITERAL_NOT_FOUND {literal!r}")
    return {
        "start_char": index,
        "end_char_exclusive": index + len(literal),
        "literal_sha256": sha(literal.encode("utf-8")),
    }


def parse_module_index(page_text: str, txt_modules: list[dict[str, Any]]) -> dict[str, Any]:
    parsed = parse_pdf_index(page_text, txt_modules)
    rows: list[dict[str, Any]] = []
    for txt_row, pdf_row in zip(txt_modules, parsed["rows"]):
        if (
            txt_row["module_label"] != pdf_row["module_label"]
            or txt_row["title_literal"] != pdf_row["exercise_title_literal"]
            or txt_row["declared_workload_value"] != pdf_row["declared_workload_value"]
        ):
            raise CandidateError(f"TXT_PDF_INDEX_MISMATCH module={txt_row['module_label']}")
        rows.append({
            "module_label": txt_row["module_label"],
            "txt_title_literal": txt_row["title_literal"],
            "pdf_index_title_literal": pdf_row["exercise_title_literal"],
            "titles_exactly_equal": True,
            "txt_declared_workload_literal": txt_row["declared_workload_literal"],
            "pdf_index_workload_literal": pdf_row["declared_workload_literal"],
            "workloads_exactly_equal": True,
            "txt_line_number": txt_row["txt_line_number"],
            "txt_source_positions": {
                "title": txt_row["title_source_position"],
                "workload": txt_row["workload_source_position"],
            },
            "pdf_source_positions": pdf_row["pdf_source_positions"],
        })
    parsed["rows"] = rows
    parsed["meaning"] = "The TXT summary and PDF p.1 index repeat the same source labels and declared counts; equality does not define the counted event contents."
    return parsed


def build_candidate(root: Path = ROOT) -> dict[str, Any]:
    source = read_inputs(root)
    module_index = parse_module_index(source["pdf_pages"][0], source["txt_modules"])
    i_table = parse_i_table(source["pdf_pages"][13])
    detail_by_module: dict[str, list[dict[str, Any]]] = {letter: [] for letter, _, _ in EXPECTED_MODULES}
    page_records = []
    for number, (text, digest, coverage, cached, appendix) in enumerate(zip(
        source["pdf_pages"],
        [source["page_hashes"][i] for i in range(1, 16)],
        source["coverage_pages"],
        source["catalog_pdf_pages"],
        source["appendix_pages"],
    ), 1):
        first_line = (text.splitlines() or [""])[0]
        if number == 1:
            role, label = "document-title-and-module-index", None
        elif number == 2:
            role, label = "unassigned-reference-page", None
            if first_line != "Reference - One Grid, Several Grooves":
                raise CandidateError("PDF_P2_REFERENCE_HEADING_CHANGED")
        else:
            label, expected_heading = DETAIL_HEADINGS[number]
            if first_line != expected_heading:
                raise CandidateError(f"PDF_DETAIL_HEADING_CHANGED page={number}")
            role = "explicit-module-detail-heading"
        page_record = {
            "page_number": number,
            "source_path": PDF,
            "literal_heading": first_line,
            "page_role": role,
            "module_label_from_printed_heading": label,
            "literal_extracted_text_character_count": len(text),
            "literal_extracted_text_sha256": digest,
            "current_catalog_text_sha256": cached["extracted_text_sha256"],
            "historical_appendix_text_sha256": appendix["literal_extracted_text_sha256"],
            "lexical_coverage": {
                "classification": coverage["classification"],
                "matched_passage_count": len(coverage.get("matched_passages", [])),
                "unmatched_passage_count": len(coverage.get("unmatched_passages", [])),
                "meaning": "Lexical matching metadata only; it does not establish source equivalence or module semantics.",
            },
            "heading_source_position": _page_span(text, first_line) if first_line else None,
        }
        page_records.append(page_record)
        if label is not None:
            detail_by_module[label].append({
                "page_number": number,
                "detail_heading_literal": first_line,
                "heading_source_position": page_record["heading_source_position"],
            })

    if [item["page_number"] for item in page_records] != list(range(1, 16)):
        raise CandidateError("PDF_PAGE_ACCOUNTING_INCOMPLETE")
    module_crosswalk = []
    for txt_row, index_row in zip(source["txt_modules"], module_index["rows"]):
        label = txt_row["module_label"]
        details = detail_by_module[label]
        expected_pages = {"A": [3], "B": [4], "C": [5], "D": [6], "E": [7], "F": [8], "G": [9], "H": [10, 11, 12, 13], "I": [14], "J": [15]}[label]
        if [item["page_number"] for item in details] != expected_pages:
            raise CandidateError(f"PDF_DETAIL_PAGE_MAP_CHANGED module={label}")
        module_crosswalk.append({
            "module_label": label,
            "txt_summary_title_literal": txt_row["title_literal"],
            "pdf_p1_index_title_literal": index_row["pdf_index_title_literal"],
            "pdf_detail_headings": details,
            "link_basis": "Only the explicit printed module letter and source index are recorded; this is not semantic equivalence or event mapping.",
            "source_difference_note": (
                "One TXT module summary line is accompanied by four separately headed PDF studies."
                if label == "H" else
                "The PDF p.14 table prints eight four-bar ranges; the TXT declares 256 events and does not map those events to the ranges."
                if label == "I" else
                "Detail heading spelling is retained literally and may differ from the shared TXT/PDF index title."
                if details and details[0]["detail_heading_literal"] != txt_row["title_literal"] else
                "No additional source-specific difference is asserted from the label crosswalk."
            ),
        })

    txt = {
        "source_path": TXT,
        "encoding": "utf-8",
        "newline": "LF",
        "terminal_newline": True,
        "line_count": len(source["txt_records"]),
        "position_convention": "Zero-based half-open Unicode codepoint offsets in exact decoded TXT text; line literal excludes LF.",
        "literal_lines": source["txt_records"],
        "declared_total": {
            "line_number": 9,
            "literal": source["txt_records"][8]["literal"],
            "source_position": source["txt_records"][8]["source_position"],
        },
        "modules": source["txt_modules"],
        "capstone_statement": {
            "line_number": 33,
            "literal": source["txt_records"][32]["literal"],
            "source_position": source["txt_records"][32]["source_position"],
        },
        "level105_hard_stop": {
            "line_number": 4,
            "literal": source["txt_records"][3]["literal"],
            "source_position": source["txt_records"][3]["source_position"],
        },
        "next_level_boundary": {
            "line_number": 40,
            "literal": source["txt_records"][39]["literal"],
            "source_position": source["txt_records"][39]["source_position"],
            "level86_in_candidate": False,
        },
    }

    index_lines = page_line_records(source["pdf_pages"][0])
    p2_heading = page_line_records(source["pdf_pages"][1])[0]
    pdf = {
        "source_path": PDF,
        "extractor": {"name": "pypdf", "version": PYPDF_VERSION},
        "page_count": len(source["pdf_pages"]),
        "page_position_convention": "Zero-based half-open Unicode codepoint offsets in exact pypdf page extraction.",
        "pages": page_records,
        "module_index": module_index,
        "unassigned_reference_page": {
            "page_number": 2,
            "heading_literal": p2_heading["literal"],
            "heading_source_position": p2_heading["source_position"],
            "module_label": None,
            "lexical_coverage_classification": page_records[1]["lexical_coverage"]["classification"],
            "disposition": "No explicit A-J module label; retained as an unassigned PDF reference page.",
        },
        "i_capstone_table": i_table,
        "complete_literal_page_text_reference": {
            "path": APPENDIX,
            "bytes": PINNED[APPENDIX][0],
            "sha256": PINNED[APPENDIX][1],
            "page_count": len(source["pdf_pages"]),
            "relation": "All 15 full page text strings were re-extracted from live PDF and matched to this historical appendix and current catalog page cache. New candidate does not duplicate the PDF page bodies.",
        },
    }

    return {
        "artifact_type": "detached_workbook_source_structure_candidate",
        "candidate_format_version": 1,
        "wbs_id": "2.3.1.3.1",
        "level": 85,
        "section": "XII",
        "workbook_id": WORKBOOK_ID,
        "candidate_status": "pending_source_reconciliation",
        "curriculum_review": "Pending",
        "canonical_ids_allocated": False,
        "canonical_record_emitted": False,
        "runtime_eligible": False,
        "imported": False,
        "admitted": False,
        "whole_workbook_complete": False,
        "source_identities": {
            path: {"bytes": PINNED[path][0], "sha256": PINNED[path][1]}
            for path in PINNED
        },
        "current_source_status": {
            "source_map_review": source["map_row"]["review"],
            "catalog_content_version": source["catalog"]["content_version"],
            "catalog_record_count": len(source["catalog"].get("records", [])),
            "catalog_workbook_catalog_version": source["catalog"]["workbook_catalog"]["catalog_version"],
            "review": source["catalog_entry"]["review"],
            "conversion_status": source["catalog_entry"]["conversion_status"],
            "runtime_eligible": source["catalog_entry"]["runtime_eligible"],
            "imported": source["catalog_entry"]["imported"],
            "admitted": source["catalog_entry"]["admitted"],
            "whole_workbook_complete": source["catalog_entry"]["whole_workbook_complete"],
        },
        "extractor": {"name": "pypdf", "version": PYPDF_VERSION},
        "txt": txt,
        "pdf": pdf,
        "module_crosswalk": module_crosswalk,
        "source_specific_observations": [
            "TXT lines 12-21 and PDF p.1 index repeat the same ten module titles and numeric workload declarations; the equality does not define event contents.",
            "PDF p.2 is an unassigned reference page. Similarities to TXT core-practice prose are not treated as a source mapping.",
            "PDF detail headings are retained exactly and can differ in capitalization or wording from TXT/PDF p.1 labels.",
            "The TXT H row summarizes four eight-bar studies while the PDF labels four separate H studies on pp.10-13.",
            "TXT I declares 256 events; PDF p.14 presents eight four-bar table rows. No row-to-event relationship or timing is inferred.",
            "PDF p.15 contains recovery/mastery/roadmap text including the Level105 hard stop; TXT line40 names Level86 as next. Level86 is a boundary only.",
        ],
        "limits": [
            "Every TXT line is literal source text; no curriculum semantics or authority is selected.",
            "PDF page bodies remain by-reference in the historical appendix and original source PDF; this candidate stores page identities/headings only.",
            "No canonical ID, event identity, event schedule, onset/duration, tempo assignment, note realization, audio behavior or performance judgment is emitted.",
            "Lexical overlap is match metadata only; it does not establish semantic reconciliation.",
            "The 256-event TXT declaration and PDF p.14's eight four-bar rows remain unmapped.",
            "No runtime import, admission, curriculum acceptance, or whole-workbook completion is claimed.",
        ],
    }


def validate_output_path(root: Path, output: Path) -> Path:
    root = root.resolve(strict=True)
    raw_parts = output.parts
    if ".." in raw_parts:
        raise CandidateError("OUTPUT_PARENT_TRAVERSAL")
    destination = output if output.is_absolute() else root / output
    destination = Path(os.path.abspath(destination))
    try:
        relative = destination.relative_to(root)
    except ValueError as exc:
        raise CandidateError("OUTPUT_OUTSIDE_REPOSITORY") from exc
    expected = BUILD_REL.parts
    if relative.parts[:len(expected)] != expected or len(relative.parts) <= len(expected):
        raise CandidateError("OUTPUT_OUTSIDE_LANE_BUILD_ROOT")
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise CandidateError("OUTPUT_PATH_SYMLINK")
    if destination.exists():
        raise CandidateError("OUTPUT_OVERWRITE_REFUSED")
    return destination


def write_candidate(root: Path, output: Path) -> dict[str, Any]:
    root = root.resolve(strict=True)
    assert_git_root(root)
    destination = validate_output_path(root, output)
    candidate = build_candidate(root)
    destination.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(candidate, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    with destination.open("xb") as stream:
        stream.write(encoded)
    return {"path": destination.relative_to(root).as_posix(), "bytes": len(encoded), "sha256": sha(encoded)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = write_candidate(ROOT, args.output)
    except (CandidateError, OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
