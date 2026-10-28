#!/usr/bin/env python3
"""Build an unadmitted, source-linked candidate for Level 58 Module A masks A1-A15."""

from __future__ import annotations

import argparse
from hashlib import sha256
from io import BytesIO
import json
import os
from pathlib import Path
import re
from typing import Any

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
BUILD_ROOT = ROOT / "Build/parallel-01/2.3-level058-masks-r01"
TXT_SOURCE = {
    "path": "Notes/music/guitar project/TXT version/Guitar_Exercises_Section_VI_Level_58_Sixteenth_Note_Rhythm_Guitar_Syncopation_Dead_Strokes_Chord_Releases_Anticipations_Funk_Comping_and_Full_Song_Capstone.txt",
    "bytes": 18083,
    "sha256": "e0c153f77a6c917056b7f17c876b2431336b40cb93bf484708230296b472acd4",
}
PDF_SOURCE = {
    "path": "Notes/music/guitar project/PDF version/Guitar_Exercises_Section_VI_Level_58_Sixteenth_Note_Rhythm_Guitar_Syncopation_Dead_Strokes_Chord_Releases_Anticipations_Funk_Comping_and_Full_Song_Capstone.pdf",
    "bytes": 53179,
    "sha256": "fcc609ccb4b13f52fde57ca95d7727db8acb351e07f0fe39ea08b0774ad501b5",
    "pages": 20,
}
EXPECTED_LABELS = [f"A{i}" for i in range(1, 16)]
EXPECTED_PAGE_LABELS = {
    3: [f"A{i}" for i in range(1, 9)],
    4: [f"A{i}" for i in range(9, 16)],
}
EXPECTED_PAGE_SUMMARIES = {
    3: {"mask_count": 8, "attack_total": 48, "source_text": "8 MASKS | 48 ATTACKS"},
    4: {"mask_count": 7, "attack_total": 80, "source_text": "7 MASKS | 80 ATTACKS"},
}
MODULE_A_HEADER = "MODULE A - FIFTEEN ONE-BEAT ATTACK MASKS"
MODULE_B_PREFIX = "MODULE B -"
REPEAT_TEXT = "Repeat the one-beat mask on all four beats."
EXPECTED_GRID = ["1e&a", "2e&a", "3e&a", "4e&a"]
EXPECTED_HAND_BEAT = "DUDU"


class CandidateError(ValueError):
    """Raised when pinned Level 58 source or candidate requirements fail."""


def _sha(data: bytes) -> str:
    return sha256(data).hexdigest()


def deterministic_json_bytes(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def load_sources(root: Path = ROOT) -> tuple[bytes, bytes]:
    try:
        txt_data = (root / TXT_SOURCE["path"]).read_bytes()
        pdf_data = (root / PDF_SOURCE["path"]).read_bytes()
    except OSError as exc:
        raise CandidateError(f"cannot read pinned Level 58 source pair: {exc}") from exc
    return txt_data, pdf_data


def verify_source_pins(txt_data: bytes, pdf_data: bytes) -> int:
    for name, data, expected in (
        ("TXT", txt_data, TXT_SOURCE),
        ("PDF", pdf_data, PDF_SOURCE),
    ):
        if len(data) != expected["bytes"] or _sha(data) != expected["sha256"]:
            raise CandidateError(f"Level 58 {name} byte length or SHA-256 mismatch")
    try:
        page_count = len(PdfReader(BytesIO(pdf_data)).pages)
    except Exception as exc:
        raise CandidateError(f"Level 58 PDF cannot be read: {exc}") from exc
    if page_count != PDF_SOURCE["pages"]:
        raise CandidateError(f"Level 58 PDF page count {page_count} != {PDF_SOURCE['pages']}")
    return page_count


def _parse_row(line: str, tag: str, count: int, *, context: str) -> list[str]:
    if not line.startswith(tag + "|"):
        raise CandidateError(f"missing or malformed {tag} row in {context}: {line!r}")
    parts = line.split("|")
    if parts and parts[-1] == "":
        parts.pop()
    if len(parts) != count + 1 or parts[0] != tag:
        raise CandidateError(f"{tag} row in {context} must have {count} printed cells")
    return parts[1:]


def _txt_ref(line: int) -> dict[str, Any]:
    return {"source": "txt", "path": TXT_SOURCE["path"], "line": line}


def _pdf_ref(page: int) -> dict[str, Any]:
    return {"source": "pdf", "path": PDF_SOURCE["path"], "page": page}


def parse_module_a_txt(lines: list[str]) -> list[dict[str, Any]]:
    try:
        start = lines.index(MODULE_A_HEADER)
    except ValueError as exc:
        raise CandidateError("Level 58 Module A header missing") from exc
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith(MODULE_B_PREFIX)), None)
    if end is None or start + 1 != 41 or end + 1 != 150:
        raise CandidateError("Level 58 Module A TXT scope no longer matches lines 41-149")
    title_rows = [
        (i, re.fullmatch(r"(A\d+)\.\s+(.+)", lines[i]))
        for i in range(start + 1, end)
        if re.match(r"A\d+\.\s+", lines[i])
    ]
    labels = [match.group(1) for _, match in title_rows if match]
    if labels != EXPECTED_LABELS:
        raise CandidateError(f"Module A mask labels/order differ: {labels}")
    records: list[dict[str, Any]] = []
    for ordinal, (title_i, match) in enumerate(title_rows):
        if match is None:
            raise CandidateError(f"malformed mask title at TXT line {title_i + 1}")
        next_title_i = title_rows[ordinal + 1][0] if ordinal + 1 < len(title_rows) else end
        block = [(i, lines[i]) for i in range(title_i + 1, next_title_i)]
        label = match.group(1)
        context = f"TXT {label}"
        rows: dict[str, tuple[int, list[str]]] = {}
        repeat: tuple[int, str] | None = None
        contacts: tuple[int, str, int] | None = None
        for i, line in block:
            for tag in ("Cnt", "Hnd", "Snd"):
                if line.startswith(tag + "|"):
                    if tag in rows:
                        raise CandidateError(f"duplicate {tag} row in {context}")
                    rows[tag] = (i + 1, _parse_row(line, tag, 4, context=context))
            if line.startswith("Repeat the one-beat mask"):
                if repeat is not None:
                    raise CandidateError(f"duplicate repeat instruction in {context}")
                repeat = (i + 1, line)
            count_match = re.fullmatch(r"Contacts:\s*(\d+)", line)
            if count_match:
                if contacts is not None:
                    raise CandidateError(f"duplicate Contacts label in {context}")
                contacts = (i + 1, line, int(count_match.group(1)))
        if set(rows) != {"Cnt", "Hnd", "Snd"} or repeat is None or contacts is None:
            raise CandidateError(f"incomplete printed fields in {context}")
        cnt_line, cnt_cells = rows["Cnt"]
        hand_line, hand_cells = rows["Hnd"]
        sound_line, sound_cells = rows["Snd"]
        if cnt_cells != EXPECTED_GRID:
            raise CandidateError(f"printed Cnt grid differs in {context}: {cnt_cells}")
        if hand_cells != [EXPECTED_HAND_BEAT] * 4:
            raise CandidateError(f"printed Hnd repetitions differ in {context}: {hand_cells}")
        if len(set(sound_cells)) != 1:
            raise CandidateError(f"printed one-beat Snd mask is not repeated four times in {context}")
        one_beat = sound_cells[0]
        if len(one_beat) != 4 or any(symbol not in {"P", "-"} for symbol in one_beat):
            raise CandidateError(f"invalid one-beat mask tokens in {context}: {one_beat!r}")
        if repeat[1] != REPEAT_TEXT:
            raise CandidateError(f"repeat instruction differs in {context}: {repeat[1]!r}")
        expected_count = one_beat.count("P") * 4
        if contacts[2] != expected_count:
            raise CandidateError(
                f"TXT Contacts count {contacts[2]} != four-beat mask count {expected_count} in {context}"
            )
        records.append({
            "label": label,
            "title": match.group(2),
            "txt_contact_label": contacts[1],
            "txt_contacts_per_bar": contacts[2],
            "one_beat_mask": one_beat,
            "txt_count_grid_cells": cnt_cells,
            "txt_hand_stroke_cells": hand_cells,
            "txt_sound_mask_cells": sound_cells,
            "txt_repeat_instruction": repeat[1],
            "txt_source_lines": {
                "title": title_i + 1,
                "count_grid": cnt_line,
                "hand_strokes": hand_line,
                "sound_mask": sound_line,
                "repeat_instruction": repeat[0],
                "contacts": contacts[0],
            },
        })
    if len(records) != 15:
        raise CandidateError(f"expected 15 Module A records, got {len(records)}")
    return records


def _parse_pdf_row_block(page_text: str, page_number: int) -> tuple[dict[str, dict[str, Any]], dict[str, int]]:
    summary_match = re.search(r"(\d+)\s+MASKS\s*\|\s*(\d+)\s+ATTACKS", page_text, re.IGNORECASE)
    if not summary_match:
        raise CandidateError(f"PDF page {page_number} Module A summary missing")
    summary = {"mask_count": int(summary_match.group(1)), "attack_total": int(summary_match.group(2))}
    expected_summary = EXPECTED_PAGE_SUMMARIES[page_number]
    if summary != {key: expected_summary[key] for key in ("mask_count", "attack_total")}:
        raise CandidateError(f"PDF page {page_number} Module A summary differs: {summary}")
    title_rows = list(re.finditer(r"(?m)^(A\d+)\.\s+(.+)$", page_text))
    labels = [match.group(1) for match in title_rows]
    if labels != EXPECTED_PAGE_LABELS[page_number]:
        raise CandidateError(f"PDF page {page_number} mask labels/order differ: {labels}")
    parsed: dict[str, dict[str, Any]] = {}
    for i, title_match in enumerate(title_rows):
        begin = title_match.end()
        end = title_rows[i + 1].start() if i + 1 < len(title_rows) else page_text.find("PASS ORDER", begin)
        if end < 0:
            end = len(page_text)
        block = page_text[begin:end]
        label = title_match.group(1)
        context = f"PDF page {page_number} {label}"
        cnt_line = next((line for line in block.splitlines() if line.startswith("Cnt|")), None)
        hand_line = next((line for line in block.splitlines() if line.startswith("Hnd|")), None)
        sound_line = next((line for line in block.splitlines() if line.startswith("Snd|")), None)
        if not cnt_line or not hand_line or not sound_line:
            raise CandidateError(f"PDF rows missing in {context}")
        cnt_cells = _parse_row(cnt_line, "Cnt", 4, context=context)
        hand_cells = _parse_row(hand_line, "Hnd", 4, context=context)
        sound_cells = _parse_row(sound_line, "Snd", 4, context=context)
        if cnt_cells != EXPECTED_GRID or hand_cells != [EXPECTED_HAND_BEAT] * 4:
            raise CandidateError(f"PDF Cnt/Hnd rows differ in {context}")
        if len(set(sound_cells)) != 1:
            raise CandidateError(f"PDF Snd mask is not repeated four times in {context}")
        one_beat = sound_cells[0]
        if len(one_beat) != 4 or any(symbol not in {"P", "-"} for symbol in one_beat):
            raise CandidateError(f"invalid PDF Snd symbols in {context}")
        caption_match = re.search(r"(\d+)\s+pitched contacts per bar\.", block, re.IGNORECASE)
        footer_match = re.search(r"(?m)^\s*(\d+)\s+contacts\s*$", block, re.IGNORECASE)
        if not caption_match or not footer_match:
            raise CandidateError(f"PDF contact totals missing in {context}")
        caption_count, footer_count = int(caption_match.group(1)), int(footer_match.group(1))
        expected_count = one_beat.count("P") * 4
        if caption_count != footer_count or caption_count != expected_count:
            raise CandidateError(f"PDF contact totals conflict with repeated mask in {context}")
        parsed[label] = {
            "title": title_match.group(2),
            "cnt_cells": cnt_cells,
            "hand_cells": hand_cells,
            "sound_cells": sound_cells,
            "one_beat_mask": one_beat,
            "caption_text": caption_match.group(0),
            "pitched_contacts_per_bar": caption_count,
            "footer_text": footer_match.group(0).strip(),
            "contacts_label_count": footer_count,
            "page": page_number,
        }
    return parsed, summary


def _extract_pdf(pdf_data: bytes) -> list[str]:
    try:
        return [page.extract_text() or "" for page in PdfReader(BytesIO(pdf_data)).pages]
    except Exception as exc:
        raise CandidateError(f"Level 58 PDF text extraction failed: {exc}") from exc


def _verify_semantics_pages(pages: list[str]) -> None:
    if len(pages) != PDF_SOURCE["pages"]:
        raise CandidateError(f"Level 58 PDF page count {len(pages)} != {PDF_SOURCE['pages']}")
    page2 = re.sub(r"\s+", " ", pages[1])
    if not re.search(r"Numbers\s*\+\s*&:\s*downstroke path", page2, re.IGNORECASE):
        raise CandidateError("PDF page 2 downstroke rule missing")
    if not re.search(r"e\s*\+\s*a:\s*upstroke path", page2, re.IGNORECASE):
        raise CandidateError("PDF page 2 upstroke rule missing")
    if not re.search(r"-\s*/\s*~:\s*do not touch strings", page2, re.IGNORECASE):
        raise CandidateError("PDF page 2 no-contact rule missing")


def reconcile_pdf(records: list[dict[str, Any]], pages: list[str]) -> tuple[list[dict[str, Any]], dict[int, dict[str, int]]]:
    _verify_semantics_pages(pages)
    pdf_rows: dict[str, dict[str, Any]] = {}
    summaries: dict[int, dict[str, int]] = {}
    for page_number in (3, 4):
        page_rows, summary = _parse_pdf_row_block(pages[page_number - 1], page_number)
        pdf_rows.update(page_rows)
        summaries[page_number] = summary
    if list(pdf_rows) != EXPECTED_LABELS:
        raise CandidateError(f"paired PDF Module A mask coverage differs: {list(pdf_rows)}")
    reconciled: list[dict[str, Any]] = []
    for record in records:
        label = record["label"]
        pdf = pdf_rows.get(label)
        expected_page = 3 if int(label[1:]) <= 8 else 4
        if not pdf or pdf["page"] != expected_page:
            raise CandidateError(f"paired PDF page mapping differs for {label}")
        for field in ("title", "cnt_cells", "hand_cells", "sound_cells", "one_beat_mask"):
            source_value = record["title"] if field == "title" else (
                record["txt_count_grid_cells"] if field == "cnt_cells" else
                record["txt_hand_stroke_cells"] if field == "hand_cells" else
                record["txt_sound_mask_cells"] if field == "sound_cells" else
                record["one_beat_mask"]
            )
            if source_value != pdf[field]:
                raise CandidateError(f"Level 58 TXT/PDF {field} mismatch for {label}")
        if record["txt_contacts_per_bar"] != pdf["pitched_contacts_per_bar"]:
            raise CandidateError(f"Level 58 TXT/PDF caption count mismatch for {label}")
        if record["txt_contacts_per_bar"] != pdf["contacts_label_count"]:
            raise CandidateError(f"Level 58 TXT/PDF footer count mismatch for {label}")
        one_beat = record["one_beat_mask"]
        bar_mask = one_beat * 4
        hand_bar = EXPECTED_HAND_BEAT * 4
        txt_lines = record.pop("txt_source_lines")
        refs = {
            "txt": {
                "title": _txt_ref(txt_lines["title"]),
                "cnt": _txt_ref(txt_lines["count_grid"]),
                "hnd": _txt_ref(txt_lines["hand_strokes"]),
                "snd": _txt_ref(txt_lines["sound_mask"]),
                "repeat": _txt_ref(txt_lines["repeat_instruction"]),
                "contacts": _txt_ref(txt_lines["contacts"]),
            },
            "pdf": _pdf_ref(expected_page),
        }
        reconciled.append({
            "source_local_key": f"L58-MA-{label}",
            "label_source": label,
            "title_source": record["title"],
            "one_beat_grid_source": record["txt_count_grid_cells"][0],
            "count_grid_groups_source": record["txt_count_grid_cells"],
            "hand_stroke_one_beat_source": record["txt_hand_stroke_cells"][0],
            "hand_stroke_groups_source": record["txt_hand_stroke_cells"],
            "hand_stroke_bar_source": hand_bar,
            "sound_mask_one_beat_source": one_beat,
            "sound_mask_groups_source": record["txt_sound_mask_cells"],
            "sound_mask_bar_source": bar_mask,
            "txt_contacts_label_source": record["txt_contact_label"],
            "txt_contacts_per_bar_source": record["txt_contacts_per_bar"],
            "pdf_pitched_contacts_per_bar_source": pdf["caption_text"],
            "pdf_pitched_contacts_per_bar": pdf["pitched_contacts_per_bar"],
            "pdf_bottom_contacts_label_source": pdf["footer_text"],
            "pdf_bottom_contacts_count": pdf["contacts_label_count"],
            "bar_repetition_instruction_source": record["txt_repeat_instruction"],
            "canonical_identity": None,
            "source_refs": refs,
        })
    return reconciled, summaries


def _page_summary_records(summaries: dict[int, dict[str, int]]) -> list[dict[str, Any]]:
    result = []
    for page_number in (3, 4):
        summary = summaries[page_number]
        source = EXPECTED_PAGE_SUMMARIES[page_number]
        result.append({
            "mask_count_source": summary["mask_count"],
            "attack_total_source": summary["attack_total"],
            "source_text": source["source_text"],
            "source_ref": _pdf_ref(page_number),
        })
    if sum(item["mask_count_source"] for item in result) != 15:
        raise CandidateError("PDF page 3/4 mask summaries do not sum to 15")
    if sum(item["attack_total_source"] for item in result) != 128:
        raise CandidateError("PDF page 3/4 attack summaries do not sum to 128")
    return result


def build_candidate(
    txt_data: bytes | None = None,
    pdf_data: bytes | None = None,
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    if txt_data is None or pdf_data is None:
        loaded_txt, loaded_pdf = load_sources(root)
        txt_data = loaded_txt if txt_data is None else txt_data
        pdf_data = loaded_pdf if pdf_data is None else pdf_data
    verify_source_pins(txt_data, pdf_data)
    try:
        lines = txt_data.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise CandidateError("Level 58 TXT is not valid UTF-8") from exc
    txt_records = parse_module_a_txt(lines)
    pages = _extract_pdf(pdf_data)
    records, summaries = reconcile_pdf(txt_records, pages)
    note_definitions = [
        {
            "symbol_source": "P",
            "meaning_source": "P = pitched chord attack",
            "source_refs": [_txt_ref(8), _pdf_ref(3)],
        },
        {
            "symbol_source": "-",
            "meaning_source": "- = air stroke; no string contact",
            "source_refs": [_txt_ref(10), _pdf_ref(2), _pdf_ref(3)],
        },
        {
            "symbol_source": "D/U",
            "meaning_source": "D is the downstroke path; U is the upstroke path.",
            "source_refs": [_txt_ref(17), _pdf_ref(2)],
        },
    ]
    source_authority = {
        "txt": {"path": TXT_SOURCE["path"], "bytes": TXT_SOURCE["bytes"], "sha256": TXT_SOURCE["sha256"]},
        "pdf": {
            "path": PDF_SOURCE["path"],
            "bytes": PDF_SOURCE["bytes"],
            "sha256": PDF_SOURCE["sha256"],
            "page_count": PDF_SOURCE["pages"],
        },
    }
    return {
        "candidate_schema": "lane-local-level058-mask-source-candidate.1",
        "classification": "unadmitted_source_candidate_projection",
        "wbs": "2.3.1.2.1",
        "source_scope": {
            "level": 58,
            "module": "A",
            "labels": EXPECTED_LABELS,
            "mask_count": len(records),
            "modules_b_i_status": "unconverted",
            "whole_workbook_equivalence_claimed": False,
        },
        "source_authority": source_authority,
        "notation_source": note_definitions,
        "pdf_module_summaries_source": _page_summary_records(summaries),
        "identity_assignment": {
            "status": "pending_trusted_identity_handoff",
            "canonical_ids_assigned": False,
            "r15_reservations_used": False,
        },
        "release_state": {
            "runtime_eligible": False,
            "runtime_admitted": False,
            "imported": False,
            "admitted": False,
            "note_event_records_generated": False,
            "parent_acceptance": "Pending",
        },
        "records": records,
    }


def write_candidate(path: Path, candidate: dict[str, Any]) -> Path:
    if path.is_absolute():
        target = path
    else:
        target = ROOT / path
    target = Path(os.path.abspath(target))
    build_root = Path(os.path.abspath(BUILD_ROOT))
    try:
        relative = target.relative_to(build_root)
    except ValueError as exc:
        raise CandidateError(f"candidate output must remain under {BUILD_ROOT}") from exc
    probe = build_root
    for part in relative.parts:
        probe = probe / part
        if probe.is_symlink():
            raise CandidateError(f"candidate output may not traverse a symlink: {probe}")
    resolved = target.resolve()
    try:
        resolved.relative_to(build_root.resolve())
    except ValueError as exc:
        raise CandidateError(f"candidate output must remain under {BUILD_ROOT}") from exc
    if resolved.exists():
        raise CandidateError(f"refusing to replace existing candidate: {resolved}")
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_bytes(deterministic_json_bytes(candidate))
    return resolved


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        candidate = build_candidate()
        output = write_candidate(args.output, candidate)
    except (CandidateError, OSError) as exc:
        parser.error(str(exc))
    print(json.dumps({
        "output": output.relative_to(ROOT).as_posix(),
        "mask_count": candidate["source_scope"]["mask_count"],
        "pdf_page_summaries": candidate["pdf_module_summaries_source"],
        "sha256": _sha(output.read_bytes()),
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
