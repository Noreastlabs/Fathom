#!/usr/bin/env python3
"""Build a detached, lossless source-preservation candidate for Level 48.

This tool retains source text and page extraction independently. It does not
normalize source grids into performance events or create runtime content.
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from io import BytesIO
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

import pypdf
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
TXT_REL = Path("Notes/music/guitar project/TXT version/Scale_Exercises_Section_V_Level_48_A_Blues_Call_and_Response_and_Improvisation_Synthesis_Fixed_Key_A.txt")
PDF_REL = Path("Notes/music/guitar project/PDF version/Scale_Exercises_Section_V_Level_48_A_Blues_Call_and_Response_and_Improvisation_Synthesis_Fixed_Key_A.pdf")
MAP_REL = Path("Results/parallel-01/exercises/inventory/20260922T180500Z-2.3-curriculum-v1-source-inventory-evidence/curriculum-source-map.tsv")
P03_RESULT_REL = Path("Results/parallel-03/implementation/20260923T124343Z-11.2.1.1.1-level48-reference-rest-source-and-refusal-r01-results.md")
BUILD_REL = Path("Build/parallel-04/2.3.1.1.1-level048-whole-r04")
TXT_BYTES = 70913
TXT_SHA256 = "76b77483351d84ee3af830b96fb08d9c95fcf944cb353e356e85974da18ed511"
PDF_BYTES = 60666
PDF_SHA256 = "8f6cdf6c49436ad9cb16b0c0655213bcce0570572e32a3dec294abd2a78fea30"
MAP_BYTES = 68536
MAP_SHA256 = "f526ff4d9ce3bceaf9a7cc581a3ac2aee2c74917eba984dd57913adba574c123"
P03_RESULT_SHA256 = "be5b32efb2baedc5e745b55f0ff53c45b7d88e597515e80bf5f288b20b7ea7fc"
MAP_ROW_EXPECTED = {
    "level": "48",
    "section": "V",
    "instructional_family": "Minor pentatonic and blues",
    "wbs_owner": "2.3.1.1.1",
    "txt_path": TXT_REL.as_posix(),
    "txt_bytes": str(TXT_BYTES),
    "txt_sha256": TXT_SHA256,
    "pdf_path": PDF_REL.as_posix(),
    "pdf_bytes": str(PDF_BYTES),
    "pdf_sha256": PDF_SHA256,
    "pair_status": "exact_stem_pair",
    "representative_status": "frozen_representative_record",
    "representative_item_id": "fg:item:000007",
    "prior_staging_found": "False",
    "review": "Pending",
    "conversion_status": "converted_candidate_reference",
    "stable_ids_assigned": "True",
    "runtime_eligible": "False",
    "imported": "False",
    "admitted": "False",
    "source_specific_ambiguities": "obsolete_next_level_label_corrected_by_compilation_toc;pick_attacks_differ_from_sounding_tones_and_authored_rubric",
    "historical_conversion_evidence": "none",
    "historical_candidate_stable_ids": "False",
}
TABLE_PREFIXES = ("Cnt|", "Nte|", "Deg|", "Col|", "Rol|", "Atk|")
TABLE_LABELS = ("Cnt", "Nte", "Deg", "Col", "Rol", "Atk")
TAB_RE = re.compile(r"^\s+([eBGDAE])\|")
MODULE_RE = re.compile(r"^MODULE ([A-K]) - (.+)$")
PDF_MODULE_RE = re.compile(r"Module ([A-K]) - ([^\n]+)", re.IGNORECASE)
EXPECTED_TXT_COUNTS = {"Cnt": 76, "Nte": 76, "Deg": 76, "Col": 73, "Rol": 76, "Atk": 76}
EXPECTED_PDF_COUNTS = {"Cnt": 73, "Nte": 73, "Deg": 64, "Col": 36, "Rol": 65, "Atk": 73}
EXPECTED_MODULE_PAGES = {
    "A": [3, 4, 5], "B": [6, 7], "C": [8, 9], "D": [10], "E": [11],
    "F": [12, 13], "G": [14, 15], "H": [16, 17], "I": [18], "J": [19], "K": [20],
}
EXPECTED_MODULE_LINES = {
    "A": [46, 194], "B": [195, 262], "C": [263, 378], "D": [379, 427],
    "E": [428, 476], "F": [477, 649], "G": [650, 822], "H": [823, 995],
    "I": [996, 1089], "J": [1090, 1190], "K": [1191, 1213],
}


class CandidateError(ValueError):
    """A pinned source, map row, table, or output boundary failed."""


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _root() -> Path:
    result = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if result.returncode != 0 or Path(result.stdout.strip()).resolve() != ROOT.resolve():
        raise CandidateError("REPOSITORY_ROOT_MISMATCH")
    return ROOT


def _safe_repo_file(root: Path, relative: Path, label: str) -> bytes:
    path = root / relative
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise CandidateError(f"INPUT_SYMLINK {label}: {relative.as_posix()}")
    if not path.is_file():
        raise CandidateError(f"INPUT_MISSING {label}: {relative.as_posix()}")
    if not path.resolve(strict=True).is_relative_to(root.resolve()):
        raise CandidateError(f"INPUT_OUTSIDE_ROOT {label}: {relative.as_posix()}")
    return path.read_bytes()


def _read_pinned(root: Path, relative: Path, size: int, sha: str, label: str, override: bytes | None) -> bytes:
    data = override if override is not None else _safe_repo_file(root, relative, label)
    actual = digest(data)
    if len(data) != size or actual != sha:
        raise CandidateError(f"PINNED_INPUT_DRIFT {label}: bytes={len(data)} sha256={actual}")
    return data


def _source_map_row(data: bytes) -> dict[str, str]:
    try:
        rows = list(csv.DictReader(data.decode("utf-8").splitlines(), delimiter="\t"))
    except (UnicodeDecodeError, csv.Error) as exc:
        raise CandidateError(f"SOURCE_MAP_PARSE_FAILED {type(exc).__name__}") from exc
    matches = [row for row in rows if row.get("level") == "48"]
    if len(matches) != 1:
        raise CandidateError(f"LEVEL48_MAP_ROW_COUNT {len(matches)}")
    row = matches[0]
    for key, expected in MAP_ROW_EXPECTED.items():
        if row.get(key) != expected:
            raise CandidateError(f"LEVEL48_MAP_ROW_MISMATCH {key}: {row.get(key)!r}")
    return row


def _count_rows(lines: list[str]) -> tuple[dict[str, int], int]:
    counts = Counter(line.split("|", 1)[0] for line in lines if line.startswith(TABLE_PREFIXES))
    tabs = sum(TAB_RE.match(line) is not None for line in lines)
    return {label: counts.get(label, 0) for label in TABLE_LABELS}, tabs


def _module_ranges(lines: list[str]) -> list[dict[str, Any]]:
    found: list[tuple[int, str, str]] = []
    for index, line in enumerate(lines, 1):
        match = MODULE_RE.fullmatch(line)
        if match:
            found.append((index, match.group(1), match.group(2)))
    if tuple(item[1] for item in found) != tuple("ABCDEFGHIJK"):
        raise CandidateError(f"TXT_MODULE_ORDER_MISMATCH {[item[1] for item in found]}")
    result = []
    for i, (start, letter, title) in enumerate(found):
        end = found[i + 1][0] - 1 if i + 1 < len(found) else 1213
        if [start, end] != EXPECTED_MODULE_LINES[letter]:
            raise CandidateError(f"TXT_MODULE_BOUNDARY_MISMATCH {letter} {start}-{end}")
        result.append({
            "module": letter,
            "title": title,
            "txt_line_range": [start, end],
            "txt_ref": f"L48-TXT{start}-{end}",
            "pdf_pages": EXPECTED_MODULE_PAGES[letter],
            "pdf_refs": [f"L48-PDF-p{page}" for page in EXPECTED_MODULE_PAGES[letter]],
        })
    return result


def _module_for_line(line_number: int, modules: list[dict[str, Any]]) -> str:
    for module in modules:
        start, end = module["txt_line_range"]
        if start <= line_number <= end:
            return module["module"]
    raise CandidateError(f"TABLE_OUTSIDE_MODULE line={line_number}")


def _txt_cells(lines: list[str], modules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    starts = [i for i, line in enumerate(lines) if line.startswith("Cnt|")]
    if len(starts) != EXPECTED_TXT_COUNTS["Cnt"]:
        raise CandidateError(f"TXT_CELL_COUNT {len(starts)}")
    cells = []
    for ordinal, start in enumerate(starts, 1):
        stop = starts[ordinal] if ordinal < len(starts) else len(lines)
        selected: list[dict[str, Any]] = []
        for index in range(start, stop):
            line = lines[index]
            if line.startswith(TABLE_PREFIXES):
                selected.append({"kind": line.split("|", 1)[0], "line": index + 1, "raw": line})
            else:
                tab_match = TAB_RE.match(line)
                if tab_match:
                    selected.append({"kind": "TAB", "string": tab_match.group(1), "line": index + 1, "raw": line})
        labels = [row["kind"] for row in selected if row["kind"] != "TAB"]
        if labels not in (list(TABLE_LABELS), ["Cnt", "Nte", "Deg", "Rol", "Atk"]):
            raise CandidateError(f"TXT_CELL_ROW_ORDER_INVALID ordinal={ordinal} labels={labels}")
        tabs = [row for row in selected if row["kind"] == "TAB"]
        if len(tabs) != 6 or tuple(row["string"] for row in tabs) != ("e", "B", "G", "D", "A", "E"):
            raise CandidateError(f"TXT_CELL_TAB_INVALID ordinal={ordinal} count={len(tabs)}")
        cells.append({
            "ordinal": ordinal,
            "module": _module_for_line(start + 1, modules),
            "txt_line_range": [start + 1, tabs[-1]["line"]],
            "txt_ref": f"L48-TXT{start + 1}-{tabs[-1]['line']}",
            "rows": selected,
            "timing_interpretation": "verbatim grid only; no onset or duration derived",
        })
    return cells


def _pdf_pages(pdf_data: bytes) -> tuple[list[dict[str, Any]], dict[str, int], int, list[dict[str, Any]]]:
    try:
        reader = PdfReader(BytesIO(pdf_data), strict=True)
        if len(reader.pages) != 22:
            raise CandidateError(f"PDF_PAGE_COUNT {len(reader.pages)}")
        pages = []
        total_counts = Counter()
        total_tab_rows = 0
        module_page_rows: dict[str, list[int]] = {}
        for page_number, page in enumerate(reader.pages, 1):
            text = page.extract_text() or ""
            if not text.strip() or f"Page {page_number} of 22" not in text:
                raise CandidateError(f"PDF_PAGE_TEXT_OR_FOOTER_MISSING page={page_number}")
            lines = text.splitlines()
            counts, tab_rows = _count_rows(lines)
            total_counts.update(counts)
            total_tab_rows += tab_rows
            for letter, title in PDF_MODULE_RE.findall(text):
                module_page_rows.setdefault(letter.upper(), []).append(page_number)
            pages.append({
                "page": page_number,
                "ref": f"L48-PDF-p{page_number}",
                "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                "extracted_text": text,
                "printed_row_counts": counts,
                "tab_row_count": tab_rows,
                "module_headers": [
                    {"module": letter.upper(), "text": title.strip()}
                    for letter, title in PDF_MODULE_RE.findall(text)
                ],
            })
        actual_counts = {label: total_counts.get(label, 0) for label in TABLE_LABELS}
        if actual_counts != EXPECTED_PDF_COUNTS:
            raise CandidateError(f"PDF_EXTRACTED_ROW_COUNTS {actual_counts}")
        if total_tab_rows != 438:
            raise CandidateError(f"PDF_TAB_ROW_COUNT {total_tab_rows}")
        for letter, expected_pages in EXPECTED_MODULE_PAGES.items():
            if module_page_rows.get(letter) != expected_pages:
                raise CandidateError(f"PDF_MODULE_PAGE_MAP_MISMATCH {letter}: {module_page_rows.get(letter)}")
        return pages, actual_counts, total_tab_rows, [
            {"module": letter, "pdf_pages": expected_pages, "pdf_refs": [f"L48-PDF-p{n}" for n in expected_pages]}
            for letter, expected_pages in EXPECTED_MODULE_PAGES.items()
        ]
    except CandidateError:
        raise
    except Exception as exc:
        raise CandidateError(f"PDF_READ_FAILED {type(exc).__name__}") from exc


def _difference_ledger() -> list[dict[str, Any]]:
    return [
        {
            "id": "notation-row-coverage",
            "status": "pending-source-reconciliation",
            "summary": "The current TXT and PDF preserve different per-cell row coverage; both representations remain literal and separate.",
            "txt_counts": EXPECTED_TXT_COUNTS,
            "pdf_extracted_counts": EXPECTED_PDF_COUNTS,
            "txt_tab_rows": 456,
            "pdf_extracted_tab_rows": 438,
            "row_omissions": [
                {"module": "A", "rows_absent_in_pdf": ["Col"], "txt_ref": "L48-TXT46-194", "pdf_refs": ["L48-PDF-p3", "L48-PDF-p4", "L48-PDF-p5"]},
                {"module": "B", "rows_absent_in_pdf": ["Col"], "txt_ref": "L48-TXT195-262", "pdf_refs": ["L48-PDF-p6", "L48-PDF-p7"]},
                {"module": "C", "rows_absent_in_pdf": ["Col", "Rol"], "txt_ref": "L48-TXT263-378", "pdf_refs": ["L48-PDF-p8", "L48-PDF-p9"]},
                {"module": "D", "rows_absent_in_pdf": ["Col", "Deg"], "txt_ref": "L48-TXT379-427", "pdf_refs": ["L48-PDF-p10"]},
                {"module": "E", "rows_absent_in_pdf": ["Deg"], "txt_ref": "L48-TXT428-476", "pdf_refs": ["L48-PDF-p11"]},
                {"module": "I", "rows_absent_in_pdf": ["Col"], "txt_ref": "L48-TXT996-1089", "pdf_refs": ["L48-PDF-p18"]},
                {"module": "J", "rows_absent_in_pdf": ["Col", "Deg"], "txt_ref": "L48-TXT1090-1190", "pdf_refs": ["L48-PDF-p19"]},
            ],
        },
        {
            "id": "module-j-three-recovery-grids",
            "status": "pending-source-reconciliation",
            "summary": "TXT lines 1148-1188 provide full grids for late response, missed bend, and lost position. PDF page 19 labels a section SIX WRITTEN RECOVERY CELLS, shows three full grids, then summarizes those other repairs in prose; it does not print the three corresponding grids.",
            "txt_ref": "L48-TXT1148-1188",
            "pdf_ref": "L48-PDF-p19",
            "txt_additional_grid_count": 3,
            "pdf_additional_grid_count": 0,
        },
        {
            "id": "txt-only-core-written-counts",
            "status": "source-specific-count-retained-no-precedence",
            "summary": "The TXT supplies module totals and a 614 sounding-tone / 517 pick-attack total before the free capstone; the PDF contains no equivalent core written-count table. These are authored source counts, not performance observations.",
            "txt_ref": "L48-TXT32-43",
            "pdf_refs": [f"L48-PDF-p{n}" for n in range(1, 23)],
        },
        {
            "id": "rubric-wording-and-authored-counts",
            "status": "pending-curriculum-reconciliation",
            "summary": "Both forms provide eight 0-2 scoring categories and a 13/16 two-day gate, but phrase category-level scoring differently; the TXT also separates sounding-tone and picked-attack counts. Preserve both authored wordings without deriving a scoring result.",
            "txt_ref": "L48-TXT29-43;L48-TXT1214-1225",
            "pdf_refs": ["L48-PDF-p21", "L48-PDF-p22"],
        },
        {
            "id": "next-section-map-history",
            "status": "historical-map-ambiguity-not-located-in-current-pair",
            "summary": "The source map flags an obsolete next-level label corrected by the compilation TOC. In the pinned current pair, the TXT points to Section VI at lines 1244-1246 and PDF page 22 labels Section VI - Harmonic Minor. The older label/TOC context is not part of this source pair and remains unresolved.",
            "txt_ref": "L48-TXT1244-1246",
            "pdf_ref": "L48-PDF-p22",
        },
    ]


def build_candidate(
    *, txt_data: bytes | None = None, pdf_data: bytes | None = None,
    map_data: bytes | None = None, prior_result_data: bytes | None = None,
) -> dict[str, Any]:
    root = _root()
    txt_data = _read_pinned(root, TXT_REL, TXT_BYTES, TXT_SHA256, "L48-TXT", txt_data)
    pdf_data = _read_pinned(root, PDF_REL, PDF_BYTES, PDF_SHA256, "L48-PDF", pdf_data)
    map_data = _read_pinned(root, MAP_REL, MAP_BYTES, MAP_SHA256, "source-map", map_data)
    prior_result_data = prior_result_data if prior_result_data is not None else _safe_repo_file(root, P03_RESULT_REL, "P03-Level48-proof")
    if digest(prior_result_data) != P03_RESULT_SHA256:
        raise CandidateError(f"P03_RESULT_IDENTITY_DRIFT sha256={digest(prior_result_data)}")
    prior_result_text = prior_result_data.decode("utf-8")
    if "L48-TXT49-76" not in prior_result_text or all(f":{n:04d}" not in prior_result_text for n in (3, 8, 11, 16)):
        raise CandidateError("P03_REST_PROOF_REFERENCE_MISSING")
    map_row = _source_map_row(map_data)
    try:
        txt_text = txt_data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CandidateError("TXT_UTF8_INVALID") from exc
    txt_lines = txt_text.splitlines()
    if len(txt_lines) != 1246:
        raise CandidateError(f"TXT_LINE_COUNT {len(txt_lines)}")
    if not txt_text.endswith("\n"):
        raise CandidateError("TXT_FINAL_NEWLINE_MISSING")
    txt_counts, txt_tab_rows = _count_rows(txt_lines)
    if txt_counts != EXPECTED_TXT_COUNTS or txt_tab_rows != 456:
        raise CandidateError(f"TXT_STRUCTURE_COUNTS rows={txt_counts} tabs={txt_tab_rows}")
    modules = _module_ranges(txt_lines)
    cells = _txt_cells(txt_lines, modules)
    pages, pdf_counts, pdf_tab_rows, pdf_module_pages = _pdf_pages(pdf_data)
    extracted_all = "\n".join(page["extracted_text"] for page in pages)
    if "614 sounding tones" in extracted_all or "517 pick attacks" in extracted_all:
        raise CandidateError("PDF_CONTAINS_UNEXPECTED_CORE_TOTAL")
    if not all(phrase in pages[21]["extracted_text"] for phrase in ("SECTION VI", "HARMONIC MINOR")):
        raise CandidateError("PDF_NEXT_SECTION_REFERENCE_MISSING")
    if not all(phrase in txt_lines[1243] + " " + txt_lines[1244] + " " + txt_lines[1245] for phrase in ("NEXT SECTION", "harmonic minor")):
        raise CandidateError("TXT_NEXT_SECTION_REFERENCE_MISSING")
    sections = [
        {"id": "front-matter", "txt_line_range": [1, 45], "txt_ref": "L48-TXT1-45", "pdf_pages": [1, 2], "pdf_refs": ["L48-PDF-p1", "L48-PDF-p2"]},
        *modules,
        {"id": "record-review-rubric", "txt_line_range": [1214, 1225], "txt_ref": "L48-TXT1214-1225", "pdf_pages": [21], "pdf_refs": ["L48-PDF-p21"]},
        {"id": "completion-practice-next-section", "txt_line_range": [1226, 1246], "txt_ref": "L48-TXT1226-1246", "pdf_pages": [22], "pdf_refs": ["L48-PDF-p22"]},
    ]
    return {
        "candidate_format": "p04.detached-level48-source-preservation.v1",
        "candidate_status": "pending-source-reconciliation",
        "release_state": {"runtime_eligible": False, "imported": False, "admitted": False, "curriculum_accepted": False},
        "identity_state": {
            "new_stable_identity_created_by_lane": False,
            "preexisting_source_map_representative_reference_only": map_row["representative_item_id"],
            "identity_assignment_or_reassignment_performed_by_lane": False,
        },
        "timing_state": {"derived_onsets_or_durations_created": False, "ascii_columns_are_timing_claims": False},
        "source_map": {"path": MAP_REL.as_posix(), "bytes": MAP_BYTES, "sha256": MAP_SHA256, "level48_row": map_row},
        "prior_bounded_proof": {
            "path": P03_RESULT_REL.as_posix(),
            "sha256": P03_RESULT_SHA256,
            "preserved_source_refs": ["L48-TXT49-76"],
            "preserved_event_suffixes": ["0003", "0008", "0011", "0016"],
            "scope_note": "ReferenceAudio refusal/source-rest proof only; not Level48 whole-source conversion or runtime admission.",
        },
        "source_identity": {
            "level": 48,
            "section": "V",
            "title": "A Blues Call-and-Response and Improvisation Synthesis - Fixed Key A",
            "txt": {"path": TXT_REL.as_posix(), "bytes": len(txt_data), "sha256": TXT_SHA256},
            "pdf": {"path": PDF_REL.as_posix(), "bytes": len(pdf_data), "sha256": PDF_SHA256, "page_count": len(pages)},
        },
        "source_coverage": {
            "txt_line_count": len(txt_lines),
            "pdf_page_count": len(pages),
            "txt_table_row_counts": txt_counts,
            "txt_tab_row_count": txt_tab_rows,
            "pdf_extracted_table_row_counts": pdf_counts,
            "pdf_extracted_tab_row_count": pdf_tab_rows,
            "sections_in_source_order": sections,
            "pdf_module_page_index": pdf_module_pages,
        },
        "txt_source": {
            "source_ref": "L48-TXT1-1246",
            "raw_text": txt_text,
            "lines": [{"line": i, "ref": f"L48-TXT{i}", "text": line} for i, line in enumerate(txt_lines, 1)],
        },
        "pdf_source": {
            "extraction_library": f"pypdf {pypdf.__version__}",
            "pages": pages,
        },
        "txt_notation_cells": cells,
        "source_difference_ledger": _difference_ledger(),
    }


def serialize_candidate(candidate: dict[str, Any]) -> bytes:
    return (json.dumps(candidate, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def _validated_output_dir(root: Path, output_dir: Path) -> Path:
    allowed_base = (root / "Build/parallel-04").resolve()
    resolved = output_dir.resolve(strict=False)
    if not resolved.is_relative_to(allowed_base):
        raise CandidateError(f"OUTPUT_OUTSIDE_LANE {output_dir}")
    current = root
    for part in output_dir.relative_to(root).parts:
        current = current / part
        if current.exists() and current.is_symlink():
            raise CandidateError(f"OUTPUT_SYMLINK {current}")
    return resolved


def write_candidates(candidate: dict[str, Any], output_dir: Path | None = None) -> list[Path]:
    root = _root()
    target_dir = _validated_output_dir(root, output_dir or (root / BUILD_REL))
    names = ("candidate-01.json", "candidate-02.json")
    target_dir.mkdir(parents=True, exist_ok=True)
    targets = [target_dir / name for name in names]
    if any(path.exists() or path.is_symlink() for path in targets):
        raise CandidateError("OUTPUT_EXISTS " + ",".join(path.name for path in targets if path.exists() or path.is_symlink()))
    data = serialize_candidate(candidate)
    for path in targets:
        try:
            with path.open("xb") as f:
                f.write(data)
        except FileExistsError as exc:
            raise CandidateError(f"OUTPUT_EXISTS {path.name}") from exc
    return targets


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-candidates", action="store_true", help="write the deterministic twin candidates in the pinned P04 Build directory")
    args = parser.parse_args()
    try:
        candidate = build_candidate()
        payload = serialize_candidate(candidate)
        print(f"LEVEL48_CANDIDATE_READY bytes={len(payload)} txt_lines={candidate['source_coverage']['txt_line_count']} pdf_pages={candidate['source_coverage']['pdf_page_count']} txt_cells={len(candidate['txt_notation_cells'])} pdf_cells={candidate['source_coverage']['pdf_extracted_table_row_counts']['Cnt']}")
        if args.write_candidates:
            paths = write_candidates(candidate)
            print(f"CANDIDATES_WRITTEN {paths[0]} {paths[1]} sha256={digest(payload)}")
    except CandidateError as exc:
        print(f"CANDIDATE_REFUSED {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
