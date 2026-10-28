#!/usr/bin/env python3
"""Fail-closed, non-admitted Level 8 Sets 1–5 detached candidate adapter."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from io import BytesIO
from pathlib import Path
from typing import Any

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
TXT = Path("Notes/music/guitar project/TXT version/108_Finger_Permutations_Level_8_Two_Position_Ladder.txt")
PDF = Path("Notes/music/guitar project/PDF version/108_Finger_Permutations_Level_8_Two_Position_Ladder.pdf")
SOURCE_PINS = {TXT: (53407, "0cba6885ed917013d5ceda5e0c231c568b4aa99be4c8c0e23941295a3fa5926a"),
               PDF: (43123, "750f9b14962e71bc9ed0dc48a6f9343f2a1d5d14363858f7b9462187fc338829")}
CANDIDATES = {
    1: (Path("Build/parallel-07/2.3.1.1.1-level008-set01-r01/candidate.json"), 473281, "2ce7da17ec0b633950af15718c6319317ccfbd2085fbc2046a9b1d58873c1f51"),
    2: (Path("Build/parallel-08/2.3.1.1.1-level008-set02-r01/candidate-01.json"), 501852, "99ca81322e18ca74ad41f3ad7ab0ab0b1da591022b57a11379646b55633eaa11"),
    3: (Path("Build/parallel-09/2.3.1.1.1-level008-set03-r01/candidate-03.json"), 502021, "0914729e59c4dcec0637e30aecff6bdff29b23b92c957eb58adf9f198d120037"),
    4: (Path("Build/parallel-07/2.3.1.1.1-level008-set04-r01/candidate.json"), 473350, "fa261e06bbb3c83474210cd680546e9ca110f02182b59ffbfe761241d092973b"),
    5: (Path("Build/parallel-08/2.3.1.1.1-level008-set05-r01/candidate-01.json"), 501877, "0664f64a4d19fd3138e55bfff8b1891245a3d8bec052800e74aa9c08926f8755"),
}
OUTPUT_ROOT = Path("Build/parallel-12/2.3.1.1.1-level008-sets01-05-normalization-r01")
UP = ("E", "A", "D", "G", "B", "e")
DOWN = tuple(reversed(UP))
PRINTED = DOWN
FINGERS = {"1": "index", "2": "middle", "3": "ring", "4": "pinky"}
ROOT_KEYS = {"admitted", "exceptions", "imported", "instructions", "level", "pending", "records",
             "runtime_admitted", "runtime_eligible", "schema", "set", "source", "wbs_id", "whole_workbook_complete"}
RECORD_KEYS = {"admitted", "canonical_item_id", "canonical_variant_id", "code", "directions", "duration_q",
               "exercise_number", "fixed_bpm", "imported", "note_per_click", "onset_q", "runtime_admitted",
               "runtime_eligible", "source_local_key", "source_refs"}
A_DIRECTION = {"direction", "pdf_template", "route_order", "routes", "txt_tab_rows_high_to_low"}
B_DIRECTION = {"direction", "pdf_template", "position_order", "string_order", "string_routes", "tab_rows_printed"}
A_ROUTE = {"cells", "hand_frame_shift_frets", "shift_after_cell", "shift_at_center_barline", "source_tab_row", "string"}
B_ROUTE = {"cells", "shift_frets", "string", "tab_row"}
A_NOTE = {"ascii_column", "duration_q", "finger_digit", "finger_name", "fret", "onset_q", "ordinal"}
B_NOTE = {"duration_q", "finger_digit", "finger_name", "fret", "onset_q", "ordinal", "position", "string"}
ROW = re.compile(r"^([eBGDAES])\|([0-9-]+)\|([0-9-]+)\|$")
REF = re.compile(r"^L8-TXT1-(\d+)-(\d+)$")


class NormalizeError(ValueError):
    """An exact source, candidate, or semantic invariant failed."""


def require(ok: bool, code: str) -> None:
    if not ok:
        raise NormalizeError(code)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify(data: bytes, pin: tuple[int, str], label: str) -> None:
    require(len(data) == pin[0] and digest(data) == pin[1], f"PINNED_INPUT_DRIFT {label}")


def local_bytes(root: Path, relative: Path) -> bytes:
    require(root.is_absolute() and root.resolve() == ROOT.resolve(), "REPOSITORY_ROOT_MISMATCH")
    path = root / relative
    require(not path.is_symlink() and path.is_file() and path.resolve().is_relative_to(root.resolve()),
            f"INPUT_PATH_INVALID {relative}")
    return path.read_bytes()


def load_pinned(root: Path = ROOT) -> tuple[dict[int, dict[str, Any]], bytes, bytes]:
    txt = local_bytes(root, TXT)
    pdf = local_bytes(root, PDF)
    verify(txt, SOURCE_PINS[TXT], "TXT")
    verify(pdf, SOURCE_PINS[PDF], "PDF")
    documents = {}
    for set_number, (path, size, sha) in CANDIDATES.items():
        data = local_bytes(root, path)
        verify(data, (size, sha), f"SET{set_number}")
        try:
            documents[set_number] = json.loads(data)
        except (ValueError, UnicodeDecodeError) as exc:
            raise NormalizeError(f"CANDIDATE_JSON_INVALID SET{set_number}") from exc
    return documents, txt, pdf


def _keys(value: Any, expected: set[str], where: str) -> None:
    require(type(value) is dict and set(value) == expected, f"FIELD_SHAPE {where}")


def _nonadmitted(value: dict[str, Any], where: str, *, root: bool = False) -> None:
    for key in ("admitted", "imported", "runtime_admitted", "runtime_eligible"):
        require(value.get(key) is False, f"FALSE_ADMISSION {where}.{key}")
    if root:
        require(value.get("whole_workbook_complete") is False, f"FALSE_COMPLETION {where}")
    else:
        for key in ("canonical_item_id", "canonical_variant_id", "onset_q", "duration_q", "note_per_click", "fixed_bpm"):
            require(value.get(key) is None, f"INVENTED_ID_OR_TIME {where}.{key}")


def _printed_row(row: str, string: str, code: str, positions: tuple[str, str], where: str) -> tuple[tuple[int, ...], tuple[int, ...]]:
    match = ROW.fullmatch(row)
    require(match is not None and match.group(1) == string, f"PRINTED_TAB_ROW {where}")
    cells = []
    for index, position in enumerate(positions, 2):
        tokens = re.findall(r"\d+", match.group(index))
        expected = tuple(int(digit) + (4 if position == "P5" else 6) for digit in code)
        require(len(tokens) == 4 and tuple(map(int, tokens)) == expected, f"PRINTED_TAB_CELL {where}.{position}")
        cells.append(expected)
    return cells[0], cells[1]


def _normalize_route(route: dict[str, Any], family: str, string: str, code: str,
                     direction: str, positions: tuple[str, str], where: str) -> dict[str, Any]:
    _keys(route, A_ROUTE if family == "A" else B_ROUTE, where)
    require(route["string"] == string, f"ROUTE_LOSS_OR_ORDER {where}")
    row = route["source_tab_row"] if family == "A" else route["tab_row"]
    printed_cells = _printed_row(row, string, code, positions, where)
    require(len(route["cells"]) == 2, f"CELL_COUNT {where}")
    shift = 2 if direction == "shift_up" else -2
    if family == "A":
        require(route["hand_frame_shift_frets"] == shift and route["shift_after_cell"] == 1 and
                route["shift_at_center_barline"] is True, f"SHIFT_BOUNDARY {where}")
    else:
        require(route["shift_frets"] == shift, f"SHIFT_BOUNDARY {where}")
    cells = []
    match = ROW.fullmatch(row)
    assert match is not None
    for cell_index, (cell, position, frets) in enumerate(zip(route["cells"], positions, printed_cells, strict=True)):
        _keys(cell, {"notes", "position"}, f"{where}.cell{cell_index}")
        require(cell["position"] == position and len(cell["notes"]) == 4, f"CELL_SHAPE {where}.{cell_index}")
        ascii_columns = tuple(m.start() for m in re.finditer(r"\d+", match.group(cell_index + 2)))
        notes = []
        for ordinal, (note, fret, digit, column) in enumerate(zip(cell["notes"], frets, code, ascii_columns, strict=True), 1):
            _keys(note, A_NOTE if family == "A" else B_NOTE, f"{where}.note{ordinal}")
            require(type(note["ordinal"]) is int and note["ordinal"] == ordinal and
                    type(note["fret"]) is int and note["fret"] == fret and
                    note["finger_digit"] == digit and note["finger_name"] == FINGERS[digit] and
                    note["onset_q"] is None and note["duration_q"] is None,
                    f"NOTE_SEMANTICS {where}.{cell_index}.{ordinal}")
            if family == "A":
                require(note["ascii_column"] == column, f"ASCII_COLUMN {where}.{cell_index}.{ordinal}")
            else:
                require(note["string"] == string and note["position"] == position,
                        f"NOTE_ROUTE_BINDING {where}.{cell_index}.{ordinal}")
            notes.append({"ordinal": ordinal, "string": string, "position": position,
                          "fret": fret, "finger_digit": digit, "finger_name": FINGERS[digit],
                          "ascii_column": column if family == "A" else None,
                          "onset_q": None, "duration_q": None})
        cells.append({"position": position, "notes": notes})
    return {"string": string, "printed_tab_row": row, "cells": cells,
            "shift_after_cell": 1, "shift_at_center_barline": True, "hand_frame_shift_frets": shift}


def normalize_documents(documents: dict[int, dict[str, Any]], txt_data: bytes,
                        pdf_data: bytes) -> dict[str, Any]:
    require(set(documents) == set(CANDIDATES), "SET_COVERAGE")
    verify(txt_data, SOURCE_PINS[TXT], "TXT")
    verify(pdf_data, SOURCE_PINS[PDF], "PDF")
    try:
        txt_lines = txt_data.decode("utf-8").splitlines()
        reader = PdfReader(BytesIO(pdf_data), strict=True)
        require(len(reader.pages) == 10, "PDF_PAGE_COUNT")
        pdf_pages = {set_number: reader.pages[set_number].extract_text() or "" for set_number in CANDIDATES}
    except (UnicodeDecodeError, ValueError) as exc:
        raise NormalizeError("SOURCE_READ_INVALID") from exc
    seen_keys: set[str] = set()
    seen_numbers: set[int] = set()
    normalized = []
    set_metadata = []
    for set_number in sorted(CANDIDATES):
        document = documents[set_number]
        _keys(document, ROOT_KEYS, f"set{set_number}")
        _nonadmitted(document, f"set{set_number}", root=True)
        require(document["level"] == 8 and document["set"] == set_number and document["wbs_id"] == "2.3.1.1.1" and
                document["schema"] == f"fathom-level008-set{set_number:02d}-detached-candidate-v1" and
                document["exceptions"] == [] and isinstance(document["pending"], list), f"ROOT_IDENTITY SET{set_number}")
        source = document["source"]
        _keys(source, {"txt_path", "txt_bytes", "txt_sha256", "pdf_path", "pdf_bytes", "pdf_sha256",
                       "pdf_pages", "selected_pdf_page"}, f"set{set_number}.source")
        require(source == {"txt_path": TXT.as_posix(), "txt_bytes": SOURCE_PINS[TXT][0],
                           "txt_sha256": SOURCE_PINS[TXT][1], "pdf_path": PDF.as_posix(),
                           "pdf_bytes": SOURCE_PINS[PDF][0], "pdf_sha256": SOURCE_PINS[PDF][1],
                           "pdf_pages": 10, "selected_pdf_page": set_number + 1},
                f"SOURCE_BINDING SET{set_number}")
        require(type(document["records"]) is list and len(document["records"]) == 12,
                f"RECORD_COUNT SET{set_number}")
        set_metadata.append({"set": set_number, "source": source, "instructions": document["instructions"],
                             "pending": document["pending"], "candidate_path": CANDIDATES[set_number][0].as_posix(),
                             "candidate_bytes": CANDIDATES[set_number][1], "candidate_sha256": CANDIDATES[set_number][2]})
        family = "A" if set_number in (1, 4) else "B"
        for record_index, record in enumerate(document["records"]):
            where = f"set{set_number}.record{record_index + 1}"
            _keys(record, RECORD_KEYS, where)
            _nonadmitted(record, where)
            number = (set_number - 1) * 12 + record_index + 1
            number_text = f"{number:03d}"
            code = record["code"]
            require(type(record["source_local_key"]) is str and type(record["exercise_number"]) is str,
                    f"EXERCISE_IDENTITY {where}")
            require(record["source_local_key"] not in seen_keys and record["exercise_number"] not in
                    {f"{seen:03d}" for seen in seen_numbers}, f"DUPLICATE_EXERCISE_KEY {where}")
            require(record["exercise_number"] == number_text and type(code) is str and
                    re.fullmatch(r"[1-4]{4}", code) is not None and
                    record["source_local_key"] == f"L8-set{set_number:02d}-ex{number_text}",
                    f"EXERCISE_IDENTITY {where}")
            seen_keys.add(record["source_local_key"]);seen_numbers.add(number)
            refs = record["source_refs"]
            _keys(refs, {"txt", "pdf"}, f"{where}.source_refs")
            match = REF.fullmatch(refs["txt"])
            require(match is not None and refs["pdf"] == f"L8-PDF1-p{set_number + 1}",
                    f"SOURCE_REF {where}")
            start, end = map(int, match.groups())
            require(1 <= start < end <= len(txt_lines) and end - start == 14 and
                    txt_lines[start - 1].strip() == f"Exercise {number_text}: {code}",
                    f"TXT_LINE_REF {where}")
            block = [line.strip() for line in txt_lines[start - 1:end]]
            pdf_page = pdf_pages[set_number]
            require(re.search(rf"(?m)^{number_text}\s+{code}$", pdf_page) is not None,
                    f"PDF_CARD_REF {where}")
            require(type(record["directions"]) is list and len(record["directions"]) == 2,
                    f"DIRECTION_COUNT {where}")
            directions = []
            for direction_index, direction in enumerate(record["directions"]):
                name = "shift_up" if direction_index == 0 else "shift_down"
                route_order = UP if direction_index == 0 else DOWN
                positions = ("P5", "P7") if direction_index == 0 else ("P7", "P5")
                location = f"{where}.{name}"
                _keys(direction, A_DIRECTION if family == "A" else B_DIRECTION, location)
                require(direction["direction"] == name, f"DIRECTION_ORDER {location}")
                if family == "A":
                    require(direction["route_order"] == list(route_order), f"ROUTE_ORDER {location}")
                    routes = direction["routes"]
                    rows = direction["txt_tab_rows_high_to_low"]
                else:
                    require(direction["string_order"] == list(route_order) and
                            direction["position_order"] == list(positions), f"ROUTE_ORDER {location}")
                    routes = direction["string_routes"]
                    rows = direction["tab_rows_printed"]
                require(type(routes) is list and len(routes) == 6 and type(rows) is list and len(rows) == 6,
                        f"ROUTE_LOSS {location}")
                require(tuple(row[0] for row in rows) == PRINTED and
                        all(block.count(row) == 1 for row in rows), f"TXT_TAB_REF {location}")
                template = direction["pdf_template"]
                require(type(template) is str and template in pdf_page and
                        all("S" + row[1:] == template for row in rows), f"PDF_TXT_TEMPLATE {location}")
                normalized_routes = []
                for route, string in zip(routes, route_order, strict=True):
                    row = route.get("source_tab_row") if family == "A" else route.get("tab_row")
                    require(row == rows[PRINTED.index(string)], f"ROUTE_PRINTED_BINDING {location}.{string}")
                    normalized_routes.append(_normalize_route(route, family, string, code, name, positions,
                                                               f"{location}.{string}"))
                directions.append({"direction": name, "route_order": list(route_order),
                                   "position_order": list(positions), "printed_tab_rows_high_to_low": rows,
                                   "pdf_template": template, "routes": normalized_routes})
            normalized.append({"source_local_key": record["source_local_key"],
                               "exercise_number": number_text, "code": code, "set": set_number,
                               "source_refs": refs, "directions": directions,
                               "canonical_item_id": None, "canonical_variant_id": None,
                               "onset_q": None, "duration_q": None, "note_per_click": None,
                               "fixed_bpm": None, "runtime_eligible": False, "runtime_admitted": False,
                               "imported": False, "admitted": False})
    require(len(normalized) == 60 and len(seen_keys) == 60 and len(seen_numbers) == 60,
            "AGGREGATE_COVERAGE")
    return {"schema": "fathom-level008-sets01-05-detached-normalized-v1", "wbs_id": "2.3.1.1.1",
            "classification": "detached_non_admitted_candidate", "level": 8, "sets": [1, 2, 3, 4, 5],
            "source_pins": {"txt": {"path": TXT.as_posix(), "bytes": SOURCE_PINS[TXT][0], "sha256": SOURCE_PINS[TXT][1]},
                            "pdf": {"path": PDF.as_posix(), "bytes": SOURCE_PINS[PDF][0], "sha256": SOURCE_PINS[PDF][1]}},
            "set_metadata": set_metadata, "records": normalized,
            "counts": {"records": 60, "directions": 120, "string_routes": 720, "four_note_cells": 1440,
                       "untimed_note_projections": 5760},
            "canonical_item_id": None, "canonical_variant_id": None, "onset_q": None,
            "duration_q": None, "fixed_bpm": None, "note_per_click": None,
            "runtime_eligible": False, "runtime_admitted": False, "imported": False, "admitted": False,
            "whole_workbook_complete": False}


def build(root: Path = ROOT) -> dict[str, Any]:
    documents, txt, pdf = load_pinned(root)
    return normalize_documents(documents, txt, pdf)


def serialize(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def write_output(output: Path, data: bytes, root: Path = ROOT) -> None:
    allowed = root / OUTPUT_ROOT
    require(output.is_absolute() and output.parent.resolve() == allowed.resolve() and
            not output.is_symlink() and not output.exists() and output.name.endswith(".json"),
            "OUTPUT_BOUNDARY")
    allowed.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as stream:
        stream.write(data)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="new absolute JSON file in P12 Build root")
    args = parser.parse_args()
    try:
        data = serialize(build())
        write_output(args.output, data)
        print(f"PASS detached Level 8 Sets 1–5: 60 records, 720 routes, 5760 untimed notes; bytes={len(data)} sha256={digest(data)}")
        return 0
    except (NormalizeError, OSError) as exc:
        print(f"FAIL {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
