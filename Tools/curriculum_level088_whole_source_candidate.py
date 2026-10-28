#!/usr/bin/env python3
"""Build a detached Level88 TXT/PDF source-structure index."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
from io import BytesIO, StringIO
from pathlib import Path
from typing import Any

import pypdf
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
BUILD_REL = Path("Build/parallel-03/2.3.1.3.1-level-088-whole-source-index-r01")
SOURCE_MAP = "Results/parallel-01/exercises/inventory/20260922T180500Z-2.3-curriculum-v1-source-inventory-evidence/curriculum-source-map.json"
SOURCE_MAP_TSV = "Results/parallel-01/exercises/inventory/20260922T180500Z-2.3-curriculum-v1-source-inventory-evidence/curriculum-source-map.tsv"
SOURCE_INVENTORY = "Results/parallel-01/exercises/inventory/20260922T180500Z-2.3-curriculum-v1-source-inventory-evidence/source-inventory.json"
CATALOG = "Content/controls/curriculum-v1/package.json"
COVERAGE = "Results/parallel-01/exercises/conversion/20260923T021155Z-2.3.1.3.1-pdf-txt-passage-coverage-r01-evidence/pdf-txt-coverage-report.json"
TXT = "Notes/music/guitar project/TXT version/Guitar_Exercises_Section_XII_Level_88_Rock_Hard_Rock_and_Metal_Groove_Control_Eighth_Note_Drive_Gallops_Pedal_Tones_Power_Chord_Displacement_and_Riff_Architecture.txt"
PDF = "Notes/music/guitar project/PDF version/Guitar_Exercises_Section_XII_Level_88_Rock_Hard_Rock_and_Metal_Groove_Control_Eighth_Note_Drive_Gallops_Pedal_Tones_Power_Chord_Displacement_and_Riff_Architecture.pdf"
APPENDIX = "Results/parallel-01/exercises/conversion/20260923T032643Z-2.3.1.3.1-pdf-source-appendices-levels-088-089-r01-evidence/levels-088-089-pdf-source-candidate.json"
APPENDIX_RESULT = "Results/parallel-01/exercises/conversion/20260923T032643Z-2.3.1.3.1-pdf-source-appendices-levels-088-089-r01-results.md"
ROOT_GUARD_REVIEW = "Results/parallel-02/review/20260923T040740Z-independent-review-parallel-01-levels-088-089-root-guard-r13-results.md"
SCHEMA_FREEZE = "Results/primary/20260912T100538Z-2.1.1.2.1-r02-evidence/schema-freeze.json"
M1_ACCEPTANCE = "Results/primary/20260912T092802Z-11.4.1.1.1-r03-evidence/acceptance.json"

PINNED: dict[str, tuple[int, str]] = {
    SOURCE_MAP: (199753, "bad5581a04f43ba8baf14db430449e1ccff5cf88f0f7e42198328073b27053d6"),
    SOURCE_MAP_TSV: (68536, "f526ff4d9ce3bceaf9a7cc581a3ac2aee2c74917eba984dd57913adba574c123"),
    SOURCE_INVENTORY: (36518, "9c216852ddab1151745a9617f9ff3725a8fcd4608fd7d6915e8a04864bb54f73"),
    CATALOG: (24698658, "766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255"),
    COVERAGE: (3123277, "968318ab8d5559b742b2871e217d254fe424d6ee5efa72c084d91d44962b7631"),
    TXT: (1489, "0cbaa5ea7950658dc89eec8b484792d05a640d9532ef7add0442b571a07a2aac"),
    PDF: (40992, "c2e71c0f2391c29d713f6992c9149e43ec599f9eb1cd1f08bf09d915f1a8971f"),
    APPENDIX: (59361, "810f844e8a901cf5a325280861ea78f048ae24e39ef78fa2943a342585ae6607"),
    APPENDIX_RESULT: (5143, "2971202d929f94042fe332764ca4c8b5b57180ff70633671bfa47781806a99fe"),
    ROOT_GUARD_REVIEW: (2617, "fabbd522cc9caaac3700cb56f2c64081fe3cadd1483112285b20c8b1bb5045a8"),
    SCHEMA_FREEZE: (2737, "0659fa962a5c933a2bcf3045772b6fe5b05b4deefb3511f5dcb68af51088de95"),
    M1_ACCEPTANCE: (2745, "730fa18677abf1a4feb802bb135d70b8b8b261b637e6703e8f3290dceace63ce"),
}
PYPDF_VERSION = "6.10.0"
WORKBOOK_ID = "fg:workbook:000088"
EXPECTED_PAGE_HASHES = {
    1: "f78c379c94751365c9c57803b384d3275e21fd52e81ccdb69c425c4fd069b276",
    2: "359de03506d0f68d2743286587712f2230283d2f8250d6a96580c4101aeb3500",
    3: "9eebb6d7221fe6619f748fa82d087f3c486e72e54107c613b2d13d7442b9edec",
    4: "0adb8992f1bd0b58151f820a9f53129b8ac5f51deb827e3215450ed98895a5b8",
    5: "361e6d774ec8b2e815167f8720ae0ad3abd313ae1c04e28f9e9969d28bcafaab",
    6: "eeafc558d01ebfaf61eff1f5f4469a0236a71fc8225ac6188210b32beea7f44a",
    7: "3e7727f897c2b9d1a390fef625c88b7122e7cc1916bb973fa200b0b1b018fe6a",
    8: "5c3fe24752ab660fc0c816a70ca62a34f89980600622180ddb74dee7c8af015a",
    9: "204c84520a3f2692ae4bf5bdb1a6a4d125587cd3761b51abc7b88caa62c991d7",
    10: "c2db1906fd486d1c6142a10661009df0fe3182475db86386a713d3d94f3be91b",
    11: "6fb535c7a4592a276da3bebd69ecbab1f467ff1eb533ae51c6ff30cd612e5ce3",
    12: "715618cf8bc69352e843e1cb81cb99a30132d5f3dd0ddfe8f01a758878fc411d",
    13: "78977343125b3e23b0220c36809d4cbffed79cd510d899371acc00f11b46592a",
    14: "531586caf8f3a3ffee074a6c8fc27ceb0f4f9bffdd91a504d71c21e8d689cb2a",
    15: "dcc33314615f5f604a6215ebef816c40d72b8c3ca8d30cd0790e3f3cb21fa2d1",
}
EXPECTED_MODULES = (
    ("A", "Eighth-note drive and palm-mute depth", 160),
    ("B", "Gallop and reverse-gallop control", 144),
    ("C", "Pedal-tone riffs and chord punctuation", 160),
    ("D", "Power-chord displacement and syncopation", 144),
    ("E", "Accent architecture and riff identity", 128),
    ("F", "Open/muted contrast and section lift", 128),
    ("G", "Riff construction and variation", 160),
    ("H", "Four eight-bar rock/metal studies", 192),
    ("I", "Thirty-two-bar riff-performance capstone", 256),
    ("J", "Recovery and groove audit", 64),
)
DETAIL_HEADINGS = {
    3: ("A", "Module A - Eighth-Note Drive and Mute Depth"),
    4: ("B", "Module B - Gallops and Reverse Gallops"),
    5: ("C", "Module C - Pedal-Tone Riffs"),
    6: ("D", "Module D - Power-Chord Displacement"),
    7: ("E", "Module E - Accent Architecture"),
    8: ("F", "Module F - Open/Muted Contrast and Section Lift"),
    9: ("G", "Module G - Riff Construction and Variation"),
    10: ("H", "Module H - Study 1 - Rock eighth-note drive"),
    11: ("H", "Module H - Study 2 - Hard-rock pedal riff"),
    12: ("H", "Module H - Study 3 - Gallop study"),
    13: ("H", "Module H - Study 4 - Breakdown/chorus contrast"),
    14: ("I", "Module I - Thirty-Two-Bar Riff-Performance Capstone"),
    15: ("J", "Module J - Recovery and Groove Audit"),
}
CAPSTONE_HEADERS = ("Bars", "Harmony", "Riff role", "Texture", "Dynamic")
EXPECTED_CAPSTONE_ROWS = (
    ("1-4", "E5-G5-A5-E5", "rock drive", "medium mute", "mf"),
    ("5-8", "E pedal + G5/A5", "hard rock", "pedal punctuation", "mf"),
    ("9-12", "E5-G5-A5-D5", "gallop", "heavy mute", "f"),
    ("13-16", "E5-D5-C5-B5", "breakdown", "rests + low hits", "f"),
    ("17-20", "E5-G5-A5-E5", "open chorus", "light/open", "f"),
    ("21-24", "E pedal + D5/C5", "reverse gallop", "heavy/medium", "mf"),
    ("25-28", "E5-G5-A5-D5", "syncopated riff", "displaced chords", "f"),
    ("29-32", "E5-D5-A5-E5", "outro", "open -> mute -> sustain", "f -> p"),
)
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


def exactly_one(rows: list[dict[str, Any]], predicate, label: str) -> dict[str, Any]:
    found = [row for row in rows if predicate(row)]
    if len(found) != 1:
        raise CandidateError(f"EXPECTED_ONE {label} got={len(found)}")
    return found[0]


def text_lines(text: str, *, require_lf: bool = True) -> list[dict[str, Any]]:
    if "\r" in text:
        raise CandidateError("TXT_NEWLINE_NOT_LF")
    if require_lf and not text.endswith("\n"):
        raise CandidateError("TXT_TERMINAL_NEWLINE_MISSING")
    records = []
    offset = 0
    for number, raw_line in enumerate(text.splitlines(keepends=True), 1):
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


def page_lines(text: str) -> list[dict[str, Any]]:
    records = []
    offset = 0
    for number, raw_line in enumerate(text.splitlines(keepends=True), 1):
        literal = raw_line[:-1] if raw_line.endswith("\n") else raw_line
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
    if len(records) != 43:
        raise CandidateError(f"TXT_LINE_COUNT expected=43 actual={len(records)}")
    fixed = {
        4: "LEVEL 88 OF 105 - HARD STOP AFTER LEVEL 105",
        10: "COMPLETE WRITTEN WORKLOAD: 1536 events",
        12: "MODULES",
        24: "KEY SKILLS",
        35: "CAPSTONE",
        38: "MASTERY",
        42: "NEXT",
    }
    for number, expected in fixed.items():
        if records[number - 1]["literal"] != expected:
            raise CandidateError(f"TXT_FIXED_LITERAL_CHANGED line={number}")
    rows = []
    for line_no, expected in enumerate(EXPECTED_MODULES, 13):
        record = records[line_no - 1]
        match = MODULE_LINE_RE.fullmatch(record["literal"])
        if not match:
            raise CandidateError(f"TXT_MODULE_LINE_SHAPE line={line_no}")
        label, title, count = match.group("label", "title", "count")
        if (label, title, int(count)) != expected:
            raise CandidateError(f"TXT_MODULE_LITERAL_DRIFT line={line_no}")
        start = record["source_position"]["start_char"]
        rows.append({
            "module_label": label,
            "title_literal": title,
            "declared_workload_literal": f"{count} events",
            "declared_workload_value": int(count),
            "txt_line_number": line_no,
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
    if records[35]["literal"] != "32 bars moving through rock drive, hard-rock pedal riff, gallops, breakdown, open chorus, reverse gallop, syncopated riff, and outro at one tempo.":
        raise CandidateError("TXT_CAPSTONE_LITERAL_CHANGED")
    if records[38]["literal"] != "14/16 or better on two separate days." or records[39]["literal"] != "No zero in pulse, gallop control, pedal/chord balance, or recovery.":
        raise CandidateError("TXT_MASTERY_LITERAL_CHANGED")
    if records[42]["literal"] != "Level 89: country, Americana, and hybrid-picking groove principles.":
        raise CandidateError("TXT_NEXT_LEVEL_BOUNDARY_CHANGED")
    if sum(row["declared_workload_value"] for row in rows) != 1536:
        raise CandidateError("TXT_MODULE_WORKLOAD_SUM_CHANGED")
    return rows


def parse_pdf_index(page_text: str, txt_modules: list[dict[str, Any]]) -> dict[str, Any]:
    lines = page_lines(page_text)
    header_indexes = [
        i for i in range(len(lines) - 2)
        if tuple(lines[i + n]["literal"] for n in range(3)) == ("Module", "Exercise", "Events")
    ]
    if len(header_indexes) != 1:
        raise CandidateError("PDF_INDEX_HEADER_NOT_UNIQUE")
    header = header_indexes[0]
    cursor = header + 3
    rows = []
    for ordinal, txt_row in enumerate(txt_modules, 1):
        cells = lines[cursor:cursor + 3]
        if len(cells) != 3:
            raise CandidateError("PDF_INDEX_ROWS_TRUNCATED")
        expected = (txt_row["module_label"], txt_row["title_literal"], str(txt_row["declared_workload_value"]))
        actual = tuple(cell["literal"] for cell in cells)
        if actual != expected:
            raise CandidateError(f"PDF_INDEX_ROW_DRIFT position={ordinal}")
        rows.append({
            "printed_row_position": ordinal,
            "module_label": actual[0],
            "exercise_title_literal": actual[1],
            "declared_workload_literal": actual[2],
            "declared_workload_value": int(actual[2]),
            "pdf_source_positions": {
                "module_label": cells[0]["source_position"],
                "exercise_title": cells[1]["source_position"],
                "declared_workload": cells[2]["source_position"],
            },
        })
        cursor += 3
    if tuple(line["literal"] for line in lines[cursor:cursor + 2]) != ("TOTAL", "1536"):
        raise CandidateError("PDF_INDEX_TOTAL_CHANGED")
    if sum(row["declared_workload_value"] for row in rows) != 1536:
        raise CandidateError("PDF_INDEX_SUM_CHANGED")
    return {
        "page_number": 1,
        "header_literal": "Module\nExercise\nEvents",
        "header_source_position": {
            "start_char": lines[header]["source_position"]["start_char"],
            "end_char_exclusive": lines[header + 2]["source_position"]["end_char_exclusive"],
            "literal_sha256": sha(b"Module\nExercise\nEvents"),
        },
        "rows": rows,
        "declared_total_literal": "1536",
        "declared_total_source_position": lines[cursor + 1]["source_position"],
        "module_workload_sum": sum(row["declared_workload_value"] for row in rows),
        "meaning": "Printed source labels/counts only; no event realization or event model is emitted.",
    }


def parse_attack_vocabulary(page_text: str) -> list[dict[str, str]]:
    lines = [line["literal"] for line in page_lines(page_text)]
    expected = [
        ("O", "open/full power-chord attack", "allow controlled sustain"),
        ("M", "palm-muted pitched attack", "bridge-hand mute; pitch remains clear"),
        ("x", "dead/muted contact", "no stable pitch"),
        ("-", "rest/air stroke", "no contact"),
        (">", "accent", "more attack, not necessarily more duration"),
        ("~", "sustain", "no new attack"),
    ]
    header = ("Symbol", "Meaning", "Execution")
    indexes = [i for i in range(len(lines) - 2) if tuple(lines[i:i + 3]) == header]
    if len(indexes) != 1:
        raise CandidateError("PDF_ATTACK_REFERENCE_HEADER_NOT_UNIQUE")
    cursor = indexes[0] + 3
    parsed = []
    for row in expected:
        actual = tuple(lines[cursor:cursor + 3])
        if actual != row:
            raise CandidateError(f"PDF_ATTACK_REFERENCE_ROW_DRIFT symbol={row[0]}")
        parsed.append({"symbol_literal": row[0], "meaning_literal": row[1], "execution_literal": row[2]})
        cursor += 3
    return parsed


def parse_capstone_table(page_text: str) -> dict[str, Any]:
    lines = page_lines(page_text)
    headers = [
        i for i in range(len(lines) - len(CAPSTONE_HEADERS) + 1)
        if tuple(lines[i + n]["literal"] for n in range(len(CAPSTONE_HEADERS))) == CAPSTONE_HEADERS
    ]
    if len(headers) != 1:
        raise CandidateError("PDF_CAPSTONE_HEADER_NOT_UNIQUE")
    cursor = headers[0] + len(CAPSTONE_HEADERS)
    rows = []
    for ordinal, expected in enumerate(EXPECTED_CAPSTONE_ROWS, 1):
        cells = lines[cursor:cursor + len(CAPSTONE_HEADERS)]
        actual = tuple(cell["literal"] for cell in cells)
        if actual != expected:
            raise CandidateError(f"PDF_CAPSTONE_ROW_DRIFT position={ordinal}")
        rows.append({
            "printed_row_position": ordinal,
            "literal_fields": dict(zip(CAPSTONE_HEADERS, actual)),
            "pdf_source_positions": dict(zip(CAPSTONE_HEADERS, [cell["source_position"] for cell in cells])),
        })
        cursor += len(CAPSTONE_HEADERS)
    return {
        "page_number": 14,
        "table_headers": list(CAPSTONE_HEADERS),
        "rows": rows,
        "printed_bar_ranges": [row["literal_fields"]["Bars"] for row in rows],
        "printed_row_count": len(rows),
        "declared_event_workload_reference": {"txt_line_number": 21, "literal": "256 events"},
        "event_mapping": None,
        "interpretation_limit": "The eight four-bar table rows are preserved as printed source structure. TXT's 256-event declaration is not mapped to those rows; no event timing or schedule is inferred.",
    }


def _read_json(raw: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CandidateError(f"PINNED_JSON_INVALID {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise CandidateError(f"PINNED_JSON_ROOT_NOT_OBJECT {label}")
    return value


def read_inputs(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve(strict=True)
    assert_git_root(root)
    if pypdf.__version__ != PYPDF_VERSION:
        raise CandidateError(f"PYPDF_VERSION expected={PYPDF_VERSION} actual={pypdf.__version__}")
    raw = {relative: read_pinned(root, relative) for relative in PINNED}
    source_map = _read_json(raw[SOURCE_MAP], SOURCE_MAP)
    inventory = _read_json(raw[SOURCE_INVENTORY], SOURCE_INVENTORY)
    catalog = _read_json(raw[CATALOG], CATALOG)
    coverage = _read_json(raw[COVERAGE], COVERAGE)
    appendix = _read_json(raw[APPENDIX], APPENDIX)
    schema_freeze = _read_json(raw[SCHEMA_FREEZE], SCHEMA_FREEZE)
    m1_acceptance = _read_json(raw[M1_ACCEPTANCE], M1_ACCEPTANCE)

    map_row = exactly_one(source_map.get("rows", []), lambda row: row.get("level") == 88, "Level88 source-map row")
    if any(map_row.get(key) != value for key, value in {
        "level": 88,
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
        "source_specific_ambiguities": ["pdf_expansion_requires_page_level_conversion_review"],
    }.items()):
        raise CandidateError("LEVEL88_SOURCE_MAP_BINDING_OR_STATUS_CHANGED")

    inventory_row = exactly_one(inventory.get("entries", []), lambda row: row.get("level") == 88, "Level88 source-inventory row")
    if any(inventory_row.get(key) != value for key, value in {
        "path": Path(TXT).name,
        "bytes": PINNED[TXT][0],
        "sha256": PINNED[TXT][1],
        "packaged": False,
        "package_item_id": None,
    }.items()):
        raise CandidateError("LEVEL88_INVENTORY_BINDING_OR_STATUS_CHANGED")
    tsv_rows = list(csv.DictReader(StringIO(raw[SOURCE_MAP_TSV].decode("utf-8")), delimiter="\t"))
    tsv_row = exactly_one(tsv_rows, lambda row: row.get("level") == "88", "Level88 source-map TSV row")
    if any(tsv_row.get(key) != value for key, value in {
        "section": "XII",
        "wbs_owner": "2.3.1.3.1",
        "txt_path": TXT,
        "txt_bytes": str(PINNED[TXT][0]),
        "txt_sha256": PINNED[TXT][1],
        "pdf_path": PDF,
        "pdf_bytes": str(PINNED[PDF][0]),
        "pdf_sha256": PINNED[PDF][1],
        "pair_status": "exact_stem_pair",
        "review": "Pending",
        "conversion_status": "not_converted",
        "runtime_eligible": "False",
        "imported": "False",
        "admitted": "False",
    }.items()):
        raise CandidateError("LEVEL88_SOURCE_MAP_TSV_BINDING_OR_STATUS_CHANGED")

    if catalog.get("content_version") != "curriculum-v1-level009-659-build-only-candidate.1" or len(catalog.get("records", [])) != 659:
        raise CandidateError("CURRENT_CANONICAL_REFERENCE_SNAPSHOT_CHANGED")
    workbook_catalog = catalog.get("workbook_catalog", {})
    if workbook_catalog.get("catalog_version") != "curriculum-v1-workbook-source-catalog.5":
        raise CandidateError("WORKBOOK_CATALOG_VERSION_CHANGED")
    entry = exactly_one(workbook_catalog.get("entries", []), lambda item: item.get("workbook_id") == WORKBOOK_ID, "Level88 catalog entry")
    if any(entry.get(key) != value for key, value in {
        "review": "Pending",
        "conversion_status": "not_converted",
        "runtime_eligible": False,
        "runtime_admitted": False,
        "imported": False,
        "admitted": False,
        "whole_workbook_complete": False,
    }.items()):
        raise CandidateError("LEVEL88_CATALOG_STATUS_CHANGED")
    if entry.get("playable_projection") != {"events": [], "items": [], "modules": [], "passages": [], "records": [], "status": "explicitly_empty_unresolved", "variants": []}:
        raise CandidateError("LEVEL88_PLAYABLE_PROJECTION_NOT_EMPTY")
    txt_entry, pdf_entry = entry.get("txt", {}), entry.get("pdf", {})
    if (
        (txt_entry.get("path"), txt_entry.get("bytes"), txt_entry.get("sha256"), txt_entry.get("encoding"), txt_entry.get("line_count"))
        != (TXT, PINNED[TXT][0], PINNED[TXT][1], "utf-8", 43)
        or (pdf_entry.get("path"), pdf_entry.get("bytes"), pdf_entry.get("sha256"), pdf_entry.get("page_count"))
        != (PDF, PINNED[PDF][0], PINNED[PDF][1], 15)
        or pdf_entry.get("extraction", {}).get("engine") != "pypdf"
        or pdf_entry.get("extraction", {}).get("version") != PYPDF_VERSION
    ):
        raise CandidateError("LEVEL88_CATALOG_SOURCE_BINDING_CHANGED")

    txt_text = raw[TXT].decode("utf-8", errors="strict")
    txt_records = text_lines(txt_text)
    txt_modules = parse_module_rows(txt_records)
    catalog_txt_lines = txt_entry.get("lines", [])
    if len(catalog_txt_lines) != 43 or any(
        (cached.get("line_number"), cached.get("text")) != (record["line_number"], record["literal"])
        for cached, record in zip(catalog_txt_lines, txt_records)
    ):
        raise CandidateError("LEVEL88_CATALOG_SOURCE_TEXT_BINDING_CHANGED")

    reader = PdfReader(BytesIO(raw[PDF]))
    if len(reader.pages) != 15:
        raise CandidateError(f"PDF_PAGE_COUNT expected=15 actual={len(reader.pages)}")
    pdf_pages = [(page.extract_text() or "") for page in reader.pages]
    page_hashes = {number: sha(text.encode("utf-8")) for number, text in enumerate(pdf_pages, 1)}
    if page_hashes != EXPECTED_PAGE_HASHES:
        raise CandidateError("LEVEL88_SELECTED_PDF_PAGE_HASHES_CHANGED")
    cached_pages = pdf_entry.get("pages", [])
    if len(cached_pages) != 15 or [page.get("page_number") for page in cached_pages] != list(range(1, 16)):
        raise CandidateError("LEVEL88_CATALOG_PDF_PAGE_ORDER_CHANGED")
    for number, (page_text, cached) in enumerate(zip(pdf_pages, cached_pages), 1):
        if (
            cached.get("full_pdf_sha256") != PINNED[PDF][1]
            or cached.get("extracted_text_sha256") != page_hashes[number]
            or cached.get("extracted_text") != page_text
        ):
            raise CandidateError(f"LEVEL88_CATALOG_PAGE_CACHE_CHANGED page={number}")

    old_wb = exactly_one(appendix.get("workbooks", []), lambda row: row.get("workbook_id") == WORKBOOK_ID, "Level88 historical appendix workbook")
    if (
        appendix.get("candidate_classification") != "lexical_source_only_pending_curriculum_interpretation"
        or appendix.get("runtime_eligible") is not False
        or appendix.get("runtime_admitted") is not False
        or appendix.get("imported") is not False
        or appendix.get("admitted") is not False
        or appendix.get("whole_workbook_complete") is not False
        or old_wb.get("page_count") != 15
        or [page.get("page_number") for page in old_wb.get("pages", [])] != list(range(1, 16))
    ):
        raise CandidateError("HISTORICAL_LEVEL88_APPENDIX_STATUS_OR_PAGE_SET_CHANGED")
    old_pages = old_wb["pages"]
    for number, (page_text, old_page) in enumerate(zip(pdf_pages, old_pages), 1):
        if (
            old_page.get("literal_extracted_text") != page_text
            or old_page.get("literal_extracted_text_sha256") != page_hashes[number]
            or old_page.get("page_number") != number
        ):
            raise CandidateError(f"HISTORICAL_LEVEL88_APPENDIX_PAGE_CHANGED page={number}")

    coverage_wb = exactly_one(coverage.get("workbooks", []), lambda row: row.get("workbook_id") == WORKBOOK_ID, "Level88 coverage row")
    if coverage_wb.get("level") != 88:
        raise CandidateError("LEVEL88_COVERAGE_LEVEL_CHANGED")
    coverage_pages = coverage_wb.get("pages", [])
    if len(coverage_pages) != 15 or [page.get("page_number") for page in coverage_pages] != list(range(1, 16)):
        raise CandidateError("LEVEL88_COVERAGE_PAGE_SET_CHANGED")
    for number, coverage_page in enumerate(coverage_pages, 1):
        if (
            coverage_page.get("pdf_extracted_text_sha256") != page_hashes[number]
            or coverage_page.get("pdf_source_path") != PDF
            or coverage_page.get("pdf_source_sha256") != PINNED[PDF][1]
            or coverage_page.get("txt_source_path") != TXT
            or coverage_page.get("txt_source_sha256") != PINNED[TXT][1]
        ):
            raise CandidateError(f"LEVEL88_COVERAGE_PAGE_BINDING_CHANGED page={number}")
    coverage_counts = {"partial_literal_overlap": 9, "no_exact_five_token_window_found": 6}
    observed = {key: sum(page.get("classification") == key for page in coverage_pages) for key in coverage_counts}
    if observed != coverage_counts:
        raise CandidateError("LEVEL88_COVERAGE_CLASSIFICATION_COUNTS_CHANGED")

    schema = _read_json(raw[SCHEMA_FREEZE], SCHEMA_FREEZE)
    if schema.get("decision") != "Technical schema1 FROZEN" or schema.get("schema_version") != "1.0.0-curriculum-candidate":
        raise CandidateError("SCHEMA_PREDECESSOR_STATUS_CHANGED")
    acceptance = _read_json(raw[M1_ACCEPTANCE], M1_ACCEPTANCE)
    criteria = acceptance.get("criteria", {})
    if (
        acceptance.get("wbs_id") != "11.4.1.1.1"
        or acceptance.get("lane_status") != "Done"
        or acceptance.get("work_package_status") != "ACCEPTED"
        or acceptance.get("human_acceptance") is not False
        or not criteria
        or any(value != "PASS" for value in criteria.values())
    ):
        raise CandidateError("M1_PREDECESSOR_STATUS_CHANGED")

    review = raw[ROOT_GUARD_REVIEW].decode("utf-8")
    if "**RESULT: PASS.**" not in review or "levels-088-089" not in review:
        raise CandidateError("P01_ROOT_GUARD_REVIEW_STATUS_CHANGED")
    return {
        "root": root,
        "raw": raw,
        "source_map_row": map_row,
        "inventory_row": inventory_row,
        "catalog": catalog,
        "catalog_entry": entry,
        "coverage_pages": coverage_pages,
        "txt_text": txt_text,
        "txt_records": txt_records,
        "txt_modules": txt_modules,
        "pdf_pages": pdf_pages,
        "page_hashes": page_hashes,
        "catalog_pages": cached_pages,
        "appendix_pages": old_pages,
    }


def parse_index(page_text: str, txt_modules: list[dict[str, Any]]) -> dict[str, Any]:
    parsed = parse_pdf_index(page_text, txt_modules)
    rows = []
    for txt_row, pdf_row in zip(txt_modules, parsed["rows"]):
        rows.append({
            "module_label": txt_row["module_label"],
            "txt_title_literal": txt_row["title_literal"],
            "pdf_index_title_literal": pdf_row["exercise_title_literal"],
            "titles_exactly_equal": txt_row["title_literal"] == pdf_row["exercise_title_literal"],
            "txt_workload_literal": txt_row["declared_workload_literal"],
            "pdf_index_workload_literal": pdf_row["declared_workload_literal"],
            "workloads_exactly_equal": txt_row["declared_workload_literal"] == f"{pdf_row['declared_workload_value']} events",
            "txt_line_number": txt_row["txt_line_number"],
            "txt_source_positions": {"title": txt_row["title_source_position"], "workload": txt_row["workload_source_position"]},
            "pdf_source_positions": pdf_row["pdf_source_positions"],
        })
    if not all(row["titles_exactly_equal"] and row["workloads_exactly_equal"] for row in rows):
        raise CandidateError("TXT_PDF_INDEX_PARITY_CHANGED")
    parsed["rows"] = rows
    return parsed


def build_candidate(root: Path = ROOT) -> dict[str, Any]:
    source = read_inputs(root)
    index = parse_index(source["pdf_pages"][0], source["txt_modules"])
    vocabulary = parse_attack_vocabulary(source["pdf_pages"][1])
    capstone = parse_capstone_table(source["pdf_pages"][13])
    details: dict[str, list[dict[str, Any]]] = {letter: [] for letter, _, _ in EXPECTED_MODULES}
    page_records = []
    for number, text in enumerate(source["pdf_pages"], 1):
        heading = (text.splitlines() or [""])[0]
        if number == 1:
            role, label = "document-title-and-module-index", None
        elif number == 2:
            role, label = "unassigned-reference-page", None
            if heading != "Reference - Attack and Mute Vocabulary":
                raise CandidateError("PDF_P2_REFERENCE_HEADING_CHANGED")
        else:
            label, expected = DETAIL_HEADINGS[number]
            if heading != expected:
                raise CandidateError(f"PDF_DETAIL_HEADING_CHANGED page={number}")
            role = "explicit-module-detail-heading"
        coverage = source["coverage_pages"][number - 1]
        page_record = {
            "page_number": number,
            "source_path": PDF,
            "source_pdf_bytes": PINNED[PDF][0],
            "source_pdf_sha256": PINNED[PDF][1],
            "literal_heading": heading,
            "page_role": role,
            "module_label_from_printed_heading": label,
            "literal_extracted_text_character_count": len(text),
            "literal_extracted_text_sha256": source["page_hashes"][number],
            "current_catalog_text_sha256": source["catalog_pages"][number - 1]["extracted_text_sha256"],
            "historical_appendix_text_sha256": source["appendix_pages"][number - 1]["literal_extracted_text_sha256"],
            "historical_appendix_reference": {
                "path": APPENDIX,
                "bytes": PINNED[APPENDIX][0],
                "sha256": PINNED[APPENDIX][1],
                "page_number": number,
                "page_text_sha256": source["page_hashes"][number],
            },
            "lexical_coverage": {
                "classification": coverage["classification"],
                "matched_passage_count": len(coverage.get("matched_passages", [])),
                "unmatched_passage_count": len(coverage.get("unmatched_passages", [])),
                "meaning": "Lexical matching metadata only; it does not establish source equivalence or module semantics.",
            },
            "pypdf_extracted_control_codepoints": {"U+007F": text.count("\x7f")} if number == 1 and "\x7f" in text else {},
            "full_pdf_text_embedded": False,
        }
        page_records.append(page_record)
        if label is not None:
            details[label].append({
                "page_number": number,
                "detail_heading_literal": heading,
                "literal_text_reference_sha256": source["page_hashes"][number],
            })
    if [row["page_number"] for row in page_records] != list(range(1, 16)):
        raise CandidateError("PDF_PAGE_ACCOUNTING_INCOMPLETE")

    expected_pages = {"A": [3], "B": [4], "C": [5], "D": [6], "E": [7], "F": [8], "G": [9], "H": [10, 11, 12, 13], "I": [14], "J": [15]}
    crosswalk = []
    for txt_row, pdf_row in zip(source["txt_modules"], index["rows"]):
        label = txt_row["module_label"]
        if [row["page_number"] for row in details[label]] != expected_pages[label]:
            raise CandidateError(f"PDF_DETAIL_PAGE_MAP_CHANGED module={label}")
        headings_equal = [row["detail_heading_literal"] for row in details[label]] == [pdf_row["pdf_index_title_literal"]]
        note = (
            "The TXT has one H summary and the PDF supplies four separately headed eight-bar studies."
            if label == "H" else
            "The TXT declares 256 events; the PDF displays eight four-bar ranges without an event mapping."
            if label == "I" else
            "The printed PDF detail heading is retained literally and may differ in wording/case from the TXT/index title."
            if not headings_equal else
            "The printed detail heading and shared TXT/PDF index label are retained by source reference."
        )
        crosswalk.append({
            "module_label": label,
            "txt_summary_title_literal": txt_row["title_literal"],
            "pdf_p1_index_title_literal": pdf_row["pdf_index_title_literal"],
            "pdf_detail_headings": details[label],
            "detail_heading_sequence_equals_index_title": headings_equal,
            "link_basis": "The printed A-J letter and p.1 index only; no event or semantic mapping is inferred.",
            "source_difference_note": note,
        })

    txt = {
        "source_path": TXT,
        "source_bytes": PINNED[TXT][0],
        "source_sha256": PINNED[TXT][1],
        "encoding": "utf-8",
        "newline": "LF",
        "terminal_newline": True,
        "line_count": len(source["txt_records"]),
        "position_convention": "Zero-based half-open Unicode codepoint offsets in exact decoded original TXT; line literal excludes LF.",
        "literal_lines": source["txt_records"],
        "declared_total": {"line_number": 10, "literal": source["txt_records"][9]["literal"], "source_position": source["txt_records"][9]["source_position"]},
        "modules": source["txt_modules"],
        "capstone_statement": {"line_number": 36, "literal": source["txt_records"][35]["literal"], "source_position": source["txt_records"][35]["source_position"]},
        "mastery_lines": [
            {"line_number": n, "literal": source["txt_records"][n - 1]["literal"], "source_position": source["txt_records"][n - 1]["source_position"]}
            for n in (39, 40)
        ],
        "level105_hard_stop": {"line_number": 4, "literal": source["txt_records"][3]["literal"], "source_position": source["txt_records"][3]["source_position"]},
        "next_level_boundary": {"line_number": 43, "literal": source["txt_records"][42]["literal"], "source_position": source["txt_records"][42]["source_position"], "level89_in_candidate": False},
    }
    pdf = {
        "source_path": PDF,
        "source_bytes": PINNED[PDF][0],
        "source_sha256": PINNED[PDF][1],
        "extractor": {"name": "pypdf", "version": PYPDF_VERSION},
        "page_count": len(page_records),
        "page_position_convention": "Zero-based half-open Unicode codepoint offsets in exact pypdf page extraction; page text bodies referenced by existing PDF/appendix path and hash.",
        "pages": page_records,
        "module_index": index,
        "unassigned_reference_page": {
            "page_number": 2,
            "heading_literal": page_records[1]["literal_heading"],
            "heading_source_text_sha256": page_records[1]["literal_extracted_text_sha256"],
            "module_label": None,
            "lexical_coverage_classification": page_records[1]["lexical_coverage"]["classification"],
            "attack_vocabulary": vocabulary,
            "disposition": "The printed page has no A-J module letter; keep its symbol reference separate from the module crosswalk.",
        },
        "i_capstone_table": capstone,
        "historical_full_literal_page_reference": {
            "path": APPENDIX,
            "bytes": PINNED[APPENDIX][0],
            "sha256": PINNED[APPENDIX][1],
            "page_count": 15,
            "relation": "All live Level88 PDF page texts and hashes were matched to this immutable P01 appendix and current catalog page cache; page bodies are not duplicated here.",
        },
    }
    return {
        "artifact_type": "detached_workbook_source_structure_candidate",
        "candidate_format_version": 1,
        "wbs_id": "2.3.1.3.1",
        "level": 88,
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
        "source_identities": {path: {"bytes": PINNED[path][0], "sha256": PINNED[path][1]} for path in PINNED},
        "current_source_status": {
            "source_map_review": source["source_map_row"]["review"],
            "source_map_conversion_status": source["source_map_row"]["conversion_status"],
            "prior_staging_found_in_map": source["source_map_row"]["prior_staging_found"],
            "prior_staging_used": False,
            "catalog_content_version": source["catalog"]["content_version"],
            "catalog_record_count": len(source["catalog"].get("records", [])),
            "catalog_workbook_catalog_version": source["catalog"]["workbook_catalog"]["catalog_version"],
            "representative_status": source["source_map_row"]["representative_status"],
            "review": source["catalog_entry"]["review"],
            "conversion_status": source["catalog_entry"]["conversion_status"],
            "runtime_eligible": source["catalog_entry"]["runtime_eligible"],
            "runtime_admitted": source["catalog_entry"]["runtime_admitted"],
            "imported": source["catalog_entry"]["imported"],
            "admitted": source["catalog_entry"]["admitted"],
            "whole_workbook_complete": source["catalog_entry"]["whole_workbook_complete"],
            "playable_projection_status": source["catalog_entry"]["playable_projection"]["status"],
        },
        "extractor": {"name": "pypdf", "version": PYPDF_VERSION},
        "txt": txt,
        "pdf": pdf,
        "module_crosswalk": crosswalk,
        "pdf_only_structure_references": [
            {"page_number": 2, "role": "unassigned attack/mute symbol vocabulary", "text_sha256": page_records[1]["literal_extracted_text_sha256"]},
            {"page_number": 3, "module_label": "A", "structure": "eight mute-depth passes", "text_sha256": page_records[2]["literal_extracted_text_sha256"]},
            {"page_number": 4, "module_label": "B", "structure": "eight gallop/reverse-gallop cells with picking goals", "text_sha256": page_records[3]["literal_extracted_text_sha256"]},
            {"page_number": 5, "module_label": "C", "structure": "six pedal-tone riff rows", "text_sha256": page_records[4]["literal_extracted_text_sha256"]},
            {"page_number": 6, "module_label": "D", "structure": "eight power-chord displacement cells", "text_sha256": page_records[5]["literal_extracted_text_sha256"]},
            {"page_number": 7, "module_label": "E", "structure": "printed accent cycles", "text_sha256": page_records[6]["literal_extracted_text_sha256"]},
            {"page_number": 8, "module_label": "F", "structure": "six section-texture rows", "text_sha256": page_records[7]["literal_extracted_text_sha256"]},
            {"page_number": 9, "module_label": "G", "structure": "eight riff cells and three stated variation dimensions", "text_sha256": page_records[8]["literal_extracted_text_sha256"]},
            {"page_numbers": [10, 11, 12, 13], "module_label": "H", "structure": "four separately headed eight-bar studies with six pass requirements apiece", "text_sha256_by_page": [page_records[n - 1]["literal_extracted_text_sha256"] for n in (10, 11, 12, 13)]},
            {"page_number": 14, "module_label": "I", "structure": "eight four-bar capstone ranges and transition instructions", "text_sha256": page_records[13]["literal_extracted_text_sha256"]},
            {"page_number": 15, "module_label": "J", "structure": "eight recovery rows, mastery statement and Level89 roadmap", "text_sha256": page_records[14]["literal_extracted_text_sha256"]},
        ],
        "source_specific_observations": [
            "TXT lines 13-22 and PDF p.1 repeat the ten module labels, titles, counts and 1536 declared total; numeric equality does not identify event contents.",
            "TXT contains high-level core/key-skill/capstone/mastery summaries; the 15-page PDF preserves detailed module tables and four H studies by reference. Their semantics are not reconciled here.",
            "PDF p.2's attack/mute vocabulary has no printed A-J label and remains unassigned to the module crosswalk.",
            "The TXT H row is one summary; PDF pp.10-13 are four separately headed studies.",
            "TXT I declares 256 events and a 32-bar capstone; PDF p.14 displays eight four-bar ranges with no event mapping.",
            "TXT line43 identifies Level89 as next; PDF p.15 elaborates that roadmap. Level89 is a boundary only.",
            "The source map reports historical staging manifests, but they were not opened, copied, used, or changed.",
        ],
        "limits": [
            "TXT lines and page identities preserve source literal structure; no semantic authority is selected.",
            "The existing P01 appendix supplies the full PDF page literals by reference; this candidate does not duplicate those page bodies.",
            "No canonical ID, event identity, event schedule, onset/duration, tempo assignment, pitch realization, audio behavior or performance judgment is emitted.",
            "Lexical overlap metadata does not establish semantic equivalence or instructional correctness.",
            "The 1536 workload count and PDF detail tables do not define event granularity; the 256-event capstone remains unmapped to eight bar ranges.",
            "No runtime import, admission, Curriculum acceptance, or whole-workbook completion is claimed.",
        ],
    }


def validate_output_path(root: Path, output: Path) -> Path:
    root = root.resolve(strict=True)
    if ".." in output.parts:
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
