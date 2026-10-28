#!/usr/bin/env python3
"""Materialize a pinned, noncanonical Level 8 preadmission structural draft."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import parallel_12_level008_sets01_09_normalize as normalized

ROOT = Path(__file__).resolve().parents[1]
AGGREGATE = Path("Build/parallel-12/2.3.1.1.1-level008-sets01-09-normalization-r02/aggregate-01.json")
AGGREGATE_PIN = (1914399, "5bd1843dd0a6bbce5515125967cc703b3521a79fac7aa5453094d997e83f4b9e")
OUTPUT_ROOT = Path("Build/parallel-12/2.3.1.1.1-level008-preadmission-draft-r03")
UP = ("E", "A", "D", "G", "B", "e")
DOWN = tuple(reversed(UP))
PRINTED = DOWN
FINGERS = {"1": "index", "2": "middle", "3": "ring", "4": "pinky"}
COUNTS = {"records": 108, "directions": 216, "string_routes": 1296,
          "four_note_cells": 2592, "untimed_note_projections": 10368}
ROOT_KEYS = {"admitted", "canonical_item_id", "canonical_variant_id", "classification", "counts",
             "duration_q", "fixed_bpm", "imported", "level", "note_per_click", "onset_q", "records",
             "runtime_admitted", "runtime_eligible", "schema", "set_metadata", "sets", "source_pins",
             "wbs_id", "whole_workbook_complete"}
RECORD_KEYS = {"admitted", "canonical_item_id", "canonical_variant_id", "code", "directions",
               "duration_q", "exercise_number", "fixed_bpm", "imported", "note_per_click", "onset_q",
               "runtime_admitted", "runtime_eligible", "set", "source_local_key", "source_refs"}
DIRECTION_KEYS = {"direction", "pdf_template", "position_order", "printed_tab_rows_high_to_low",
                  "route_order", "routes"}
ROUTE_KEYS = {"cells", "hand_frame_shift_frets", "printed_tab_row", "shift_after_cell",
              "shift_at_center_barline", "string"}
CELL_KEYS = {"notes", "position"}
NOTE_KEYS = {"ascii_column", "duration_q", "finger_digit", "finger_name", "fret",
             "onset_q", "ordinal", "position", "string"}
ROW = re.compile(r"^([eBGDAE])\|([0-9-]+)\|([0-9-]+)\|$")


class DraftError(ValueError):
    """The source aggregate or draft invariant failed closed."""


def require(ok: bool, code: str) -> None:
    if not ok:
        raise DraftError(code)


def exact_keys(value: Any, expected: set[str], where: str) -> None:
    require(type(value) is dict and set(value) == expected, f"SCHEMA_CHANGE {where}")


def null_identity_and_time(value: dict[str, Any], where: str) -> None:
    for field in ("canonical_item_id", "canonical_variant_id", "onset_q", "duration_q", "fixed_bpm", "note_per_click"):
        require(value[field] is None, f"FALSE_ID_OR_TIME {where}.{field}")
    for field in ("runtime_eligible", "runtime_admitted", "imported", "admitted"):
        require(value[field] is False, f"FALSE_ADMISSION {where}.{field}")


def load_pinned(root: Path = ROOT) -> dict[str, Any]:
    require(root.is_absolute() and root.resolve() == ROOT.resolve(), "REPOSITORY_ROOT_MISMATCH")
    path = root / AGGREGATE
    require(not path.is_symlink() and path.is_file() and path.resolve().is_relative_to(root.resolve()),
            "AGGREGATE_PATH_INVALID")
    data = path.read_bytes()
    normalized.verify(data, AGGREGATE_PIN, "R02_AGGREGATE")
    # Verify every final candidate and both originals, then require exact r02 bytes.
    final = normalized.serialize(normalized.build(root))
    require(final == data, "AGGREGATE_SOURCE_MISMATCH")
    try:
        return json.loads(data)
    except (ValueError, UnicodeDecodeError) as exc:
        raise DraftError("AGGREGATE_JSON_INVALID") from exc


def materialize(document: dict[str, Any]) -> dict[str, Any]:
    exact_keys(document, ROOT_KEYS, "root")
    null_identity_and_time(document, "root")
    require(document["whole_workbook_complete"] is False and
            document["schema"] == "fathom-level008-sets01-09-detached-normalized-v2" and
            document["classification"] == "detached_non_admitted_candidate" and
            document["wbs_id"] == "2.3.1.1.1" and document["level"] == 8 and
            document["sets"] == list(range(1, 10)) and document["counts"] == COUNTS,
            "AGGREGATE_IDENTITY")
    require(type(document["set_metadata"]) is list and len(document["set_metadata"]) == 9 and
            type(document["records"]) is list and len(document["records"]) == 108,
            "AGGREGATE_COVERAGE")
    expected_source = {"txt": {"path": normalized.TXT.as_posix(),
                                "bytes": normalized.SOURCE_PINS[normalized.TXT][0],
                                "sha256": normalized.SOURCE_PINS[normalized.TXT][1]},
                       "pdf": {"path": normalized.PDF.as_posix(),
                                "bytes": normalized.SOURCE_PINS[normalized.PDF][0],
                                "sha256": normalized.SOURCE_PINS[normalized.PDF][1]}}
    require(document["source_pins"] == expected_source, "SOURCE_PIN_CHANGE")
    for index, metadata in enumerate(document["set_metadata"], 1):
        path, size, sha = normalized.CANDIDATES[index]
        require(type(metadata) is dict and metadata.get("set") == index and
                metadata.get("candidate_path") == path.as_posix() and
                metadata.get("candidate_bytes") == size and metadata.get("candidate_sha256") == sha and
                metadata.get("source", {}).get("selected_pdf_page") == index + 1 and
                "instructions" in metadata and "pending" in metadata,
                f"SET_SOURCE_IDENTITY {index}")
    seen: set[str] = set()
    records = []
    for record_index, record in enumerate(document["records"]):
        where = f"record{record_index + 1}"
        exact_keys(record, RECORD_KEYS, where)
        null_identity_and_time(record, where)
        set_number = record_index // 12 + 1
        number = record_index + 1
        number_text = f"{number:03d}"
        key = f"L8-set{set_number:02d}-ex{number_text}"
        code = record["code"]
        require(record["set"] == set_number and record["exercise_number"] == number_text and
                record["source_local_key"] == key and key not in seen and type(code) is str and
                re.fullmatch(r"[1-4]{4}", code) is not None,
                f"SOURCE_LOCAL_ORDER {where}")
        seen.add(key)
        refs = record["source_refs"]
        require(type(refs) is dict and set(refs) == {"txt", "pdf"} and
                re.fullmatch(r"L8-TXT1-\d+-\d+", refs["txt"]) is not None and
                refs["pdf"] == f"L8-PDF1-p{set_number + 1}", f"SOURCE_REFS {where}")
        require(type(record["directions"]) is list and len(record["directions"]) == 2,
                f"DIRECTION_LOSS {where}")
        directions = []
        for direction_index, direction in enumerate(record["directions"]):
            name = "shift_up" if direction_index == 0 else "shift_down"
            route_order = UP if direction_index == 0 else DOWN
            position_order = ("P5", "P7") if direction_index == 0 else ("P7", "P5")
            shift = 2 if direction_index == 0 else -2
            location = f"{where}.{name}"
            exact_keys(direction, DIRECTION_KEYS, location)
            require(direction["direction"] == name and direction["route_order"] == list(route_order) and
                    direction["position_order"] == list(position_order) and
                    type(direction["printed_tab_rows_high_to_low"]) is list and
                    len(direction["printed_tab_rows_high_to_low"]) == 6 and
                    type(direction["pdf_template"]) is str and
                    type(direction["routes"]) is list and len(direction["routes"]) == 6,
                    f"ROUTE_LOSS_OR_ORDER {location}")
            rows = direction["printed_tab_rows_high_to_low"]
            require(tuple(row[0] for row in rows) == PRINTED and
                    all("S" + row[1:] == direction["pdf_template"] for row in rows),
                    f"PRINTED_TAB {location}")
            routes = []
            for route_index, (route, string) in enumerate(zip(direction["routes"], route_order, strict=True)):
                route_where = f"{location}.{string}"
                exact_keys(route, ROUTE_KEYS, route_where)
                row = route["printed_tab_row"]
                require(route["string"] == string and row == rows[PRINTED.index(string)] and
                        route["shift_after_cell"] == 1 and route["shift_at_center_barline"] is True and
                        route["hand_frame_shift_frets"] == shift and
                        type(route["cells"]) is list and len(route["cells"]) == 2,
                        f"ROUTE_OR_SHIFT {route_where}")
                match = ROW.fullmatch(row)
                require(match is not None and match.group(1) == string, f"PRINTED_TAB_ROW {route_where}")
                ordered_notes = []
                for cell_index, (cell, position) in enumerate(zip(route["cells"], position_order, strict=True)):
                    exact_keys(cell, CELL_KEYS, f"{route_where}.cell{cell_index + 1}")
                    require(cell["position"] == position and type(cell["notes"]) is list and
                            len(cell["notes"]) == 4, f"CELL_LOSS {route_where}.{cell_index + 1}")
                    tokens = re.findall(r"\d+", match.group(cell_index + 2))
                    require(len(tokens) == 4, f"PRINTED_TAB_CELL {route_where}.{cell_index + 1}")
                    for note_index, note in enumerate(cell["notes"]):
                        note_where = f"{route_where}.cell{cell_index + 1}.note{note_index + 1}"
                        exact_keys(note, NOTE_KEYS, note_where)
                        digit = code[note_index]
                        fret = int(digit) + (4 if position == "P5" else 6)
                        require(note["ordinal"] == note_index + 1 and note["string"] == string and
                                note["position"] == position and note["finger_digit"] == digit and
                                note["finger_name"] == FINGERS[digit] and note["fret"] == fret and
                                tokens[note_index] == str(fret) and note["onset_q"] is None and
                                note["duration_q"] is None and
                                (note["ascii_column"] is None or type(note["ascii_column"]) is int),
                                f"NOTE_LOSS_OR_CHANGE {note_where}")
                        route_note_ordinal = cell_index * 4 + note_index + 1
                        ordered_notes.append({"source_sequence_ordinal": route_index * 8 + route_note_ordinal,
                                              "route_note_ordinal": route_note_ordinal,
                                              "cell_ordinal": cell_index + 1, "note_ordinal": note_index + 1,
                                              "string": string, "position": position, "fret": fret,
                                              "finger_digit": digit, "finger_name": FINGERS[digit],
                                              "ascii_column": note["ascii_column"],
                                              "onset_q": None, "duration_q": None})
                routes.append({"route_ordinal": route_index + 1, "string": string,
                               "printed_tab_row": row, "position_order": list(position_order),
                               "shift_after_cell": 1, "shift_at_center_barline": True,
                               "hand_frame_shift_frets": shift, "ordered_notes": ordered_notes})
            directions.append({"direction": name, "route_order": list(route_order),
                               "position_order": list(position_order),
                               "printed_tab_rows_high_to_low": rows,
                               "pdf_template": direction["pdf_template"], "routes": routes})
        records.append({"source_local_key": key, "exercise_number": number_text,
                        "set": set_number, "code": code, "source_refs": refs,
                        "directions": directions, "canonical_item_id": None,
                        "canonical_variant_id": None, "onset_q": None, "duration_q": None,
                        "fixed_bpm": None, "note_per_click": None, "runtime_eligible": False,
                        "runtime_admitted": False, "imported": False, "admitted": False})
    require(len(seen) == 108, "DUPLICATE_SOURCE_LOCAL_KEY")
    return {"schema": "fathom-level008-preadmission-structural-draft-v1",
            "classification": "noncanonical_nonadmitted_structural_draft", "wbs_id": "2.3.1.1.1",
            "level": 8, "sets": list(range(1, 10)), "counts": COUNTS,
            "source_pins": document["source_pins"], "set_metadata": document["set_metadata"],
            "normalized_aggregate": {"path": AGGREGATE.as_posix(), "bytes": AGGREGATE_PIN[0],
                                     "sha256": AGGREGATE_PIN[1]},
            "records": records, "canonical_item_id": None, "canonical_variant_id": None,
            "onset_q": None, "duration_q": None, "fixed_bpm": None, "note_per_click": None,
            "runtime_eligible": False, "runtime_admitted": False, "imported": False,
            "admitted": False, "whole_workbook_complete": False}


def build(root: Path = ROOT) -> dict[str, Any]:
    return materialize(load_pinned(root))


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
    parser.add_argument("--output", type=Path, required=True, help="new absolute JSON file in P12 r03 Build root")
    args = parser.parse_args()
    try:
        data = serialize(build())
        write_output(args.output, data)
        print(f"PASS noncanonical Level 8 draft: 108 records, 1296 sequential routes, 10368 untimed positions; bytes={len(data)} sha256={normalized.digest(data)}")
        return 0
    except (DraftError, normalized.NormalizeError, OSError) as exc:
        print(f"FAIL {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
