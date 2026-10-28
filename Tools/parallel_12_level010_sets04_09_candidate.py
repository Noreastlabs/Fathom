#!/usr/bin/env python3
"""Pinned, detached Level 10 Sets 4–9 odd-count transfer batch."""

from __future__ import annotations

import argparse
import json
from io import BytesIO
from pathlib import Path
from typing import Any

from pypdf import PdfReader

from parallel_12_level010_set03_candidate import (
    CandidateError, DOWN_LABEL, FINGER_NAMES, HEADING, HIGH_TO_LOW, MODES,
    PDF, PDF_HEADING, POSITIONS, ROOT, ROUTE_ORDER, TXT, TXT_PIN, PDF_PIN,
    UP_LABEL, digest, local_bytes, parse_cell, require, verify,
)

OUTPUT_ROOT = Path("Build/parallel-12/2.3.1.1.1-level010-sets04-09-r01")
PRIOR = (
    (1, Path("Build/parallel-09/2.3.1.1.1-level010-set01-r01/candidate-01.json"),
     (746234, "6b9c1ad832a633d0da5872e9dd3b5a086e7a89fa66440046cb4c058b1e6521c3")),
    (2, Path("Build/parallel-10/2.3.1.1.1-level010-set02-r01/candidate-01.json"),
     (191248, "271d47f36b2235a36609542d7cbf4c386a9b3e80a9b7e89dadcd9371eea1f759")),
    (3, Path("Build/parallel-12/2.3.1.1.1-level010-set03-r01/candidate-01.json"),
     (291878, "f306c4dfeaf6ffd4ad3d377d1962f37fce3952d628a7f579ef33c30a41531bce")),
)
SETS = {
    4: (1380, ("2312", "2313", "2314", "2321", "2323", "2324", "2341", "2342", "2343", "2412", "2413", "2414")),
    5: (1828, ("2421", "2423", "2424", "2431", "2432", "2434", "3121", "3123", "3124", "3131", "3132", "3134")),
    6: (2276, ("3141", "3142", "3143", "3212", "3213", "3214", "3231", "3232", "3234", "3241", "3242", "3243")),
    7: (2724, ("3412", "3413", "3414", "3421", "3423", "3424", "3431", "3432", "3434", "4121", "4123", "4124")),
    8: (3172, ("4131", "4132", "4134", "4141", "4142", "4143", "4212", "4213", "4214", "4231", "4232", "4234")),
    9: (3620, ("4241", "4242", "4243", "4312", "4313", "4314", "4321", "4323", "4324", "4341", "4342", "4343")),
}


def prior_inputs(root: Path = ROOT) -> list[dict[str, Any]]:
    result = []
    for set_number, path, pin in PRIOR:
        data = local_bytes(root, path)
        verify(data, pin, f"RELEASED_SET_{set_number}")
        try:
            candidate = json.loads(data)
        except (ValueError, UnicodeDecodeError) as exc:
            raise CandidateError(f"RELEASED_SET_JSON {set_number}") from exc
        require(candidate.get("level") == 10 and candidate.get("set") == set_number and
                len(candidate.get("records", [])) == 12, f"RELEASED_SET_SHAPE {set_number}")
        result.append({"set": set_number, "path": path.as_posix(), "bytes": pin[0], "sha256": pin[1]})
    return result


def parse_txt_set(lines: list[str], set_number: int) -> dict[str, list[dict[str, Any]]]:
    require(set_number in SETS, "SET_OUT_OF_SCOPE")
    header, codes = SETS[set_number]
    first = 12 * (set_number - 1) + 1
    last = first + 11
    require(lines[header - 1] == f"SET {set_number} OF 9 - EXERCISES {first:03d}-{last:03d}",
            f"TXT_SET_BOUNDARY {set_number}")
    if set_number < 9:
        require(lines[header + 447] == f"SET {set_number + 1} OF 9 - EXERCISES {last + 1:03d}-{last + 12:03d}",
                f"TXT_NEXT_SET_BOUNDARY {set_number}")
    else:
        require(len(lines) == 4065, "TXT_FINAL_SET_EOF")
    parsed = {}
    for mode, spec in MODES.items():
        offset = 0 if mode == "mode_a" else 222
        heading_line = header + 4 + offset
        require(lines[heading_line - 1] == spec["txt_label"] and
                lines[heading_line + 1] == spec["picking"], f"TXT_MODE_HEADER {set_number} {mode}")
        cards = []
        for index, code in enumerate(codes):
            start = header + 9 + offset + 18 * index
            number = f"{first + index:03d}"
            block = lines[start - 1:start + 16]
            heading = HEADING.fullmatch(block[0]) if block else None
            require(len(block) == 17 and heading is not None and heading.groups() == (number, code) and
                    block[1] == UP_LABEL[mode] and block[9] == DOWN_LABEL[mode],
                    f"TXT_CARD_SHAPE {set_number} {mode} {number}")
            up_finger, down_finger = block[2], block[10]
            require(parse_cell(up_finger, "F", code, mode, "shift_up") == list(map(int, code)) and
                    parse_cell(down_finger, "F", code, mode, "shift_down") == list(map(int, code)),
                    f"TXT_FINGER_ROW {set_number} {mode} {number}")
            directions = {}
            for direction, rows, finger in (("shift_up", block[3:9], up_finger),
                                            ("shift_down", block[11:17], down_finger)):
                require(len(rows) == 6 and tuple(row[0] for row in rows) == HIGH_TO_LOW,
                        f"TXT_STRING_ORDER {set_number} {mode} {number} {direction}")
                for row, string in zip(rows, HIGH_TO_LOW, strict=True):
                    parse_cell(row, string, code, mode, direction)
                directions[direction] = {"finger_row": finger, "rows_high_to_low": rows}
            cards.append({"number": number, "code": code, "txt_start_line": start,
                          "txt_end_line": start + 16, **directions})
        parsed[mode] = cards
    return parsed


def parse_pdf_set(reader: PdfReader, set_number: int) -> dict[str, list[dict[str, Any]]]:
    require(set_number in SETS and len(reader.pages) == 19, "PDF_PAGE_COUNT")
    _, codes = SETS[set_number]
    first = 12 * (set_number - 1) + 1
    last = first + 11
    parsed = {}
    for mode, spec in MODES.items():
        page = 2 * set_number + (0 if mode == "mode_a" else 1)
        label = "Mode A - 3+1 Late Shift" if mode == "mode_a" else "Mode B - 1+3 Early Shift"
        lines = (reader.pages[page - 1].extract_text() or "").splitlines()
        require(len(lines) == 137 and lines[0] == "Level 10 - Odd-Count Position Transfer" and
                lines[1] == f"Set {set_number} of 9 - {label} - Exercises {first:03d}-{last:03d}" and
                lines[2] == ("Digits 1-3 stay in the source frame; digit 4 lands in the destination frame."
                             if mode == "mode_a" else
                             "Digit 1 starts in the source frame; digits 2-4 continue in the destination frame.") and
                lines[-2] == "Standard tuning. P5 = frets 5-8; P7 = frets 7-10. Shift after note 3 in Mode A or after note 1 in Mode B." and
                lines[-1] == f"Page {page} of 19", f"PDF_MODE_PAGE {set_number} {mode}")
        cards = []
        for index, code in enumerate(codes):
            number = f"{first + index:03d}"
            block = lines[3 + index * 11:3 + (index + 1) * 11]
            heading = PDF_HEADING.fullmatch(block[0]) if block else None
            require(len(block) == 11 and heading is not None and heading.groups() == (number, code) and
                    block[1] == spec["pdf_label"] and block[2:4] == ["UP", "E>A>D>G>B>e   P5>P7"] and
                    block[6:8] == ["DN", "e>B>G>D>A>E   P7>P5"] and
                    block[10] == f"landing note {spec['landing']}; no pick reset",
                    f"PDF_CARD_SHAPE {set_number} {mode} {number}")
            directions = {}
            for direction, finger, tab in (("shift_up", block[4], block[5]),
                                           ("shift_down", block[8], block[9])):
                parse_cell(finger, "F", code, mode, direction)
                parse_cell(tab, "S", code, mode, direction)
                directions[direction] = {"finger_template": finger, "tab_template": tab}
            cards.append({"number": number, "code": code, **directions})
        parsed[mode] = cards
    return parsed


def project_record(set_number: int, code: str, index: int,
                   txt: dict[str, list[dict[str, Any]]],
                   pdf: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    number = f"{12 * (set_number - 1) + index + 1:03d}"
    modes = []
    for mode, spec in MODES.items():
        txt_card, pdf_card = txt[mode][index], pdf[mode][index]
        require(txt_card["number"] == pdf_card["number"] == number and
                txt_card["code"] == pdf_card["code"] == code, f"TXT_PDF_CARD_IDENTITY {set_number} {mode} {number}")
        directions = []
        for direction in ("shift_up", "shift_down"):
            source, reference = txt_card[direction], pdf_card[direction]
            finger, rows = source["finger_row"], source["rows_high_to_low"]
            require(finger == reference["finger_template"] and
                    all("S" + row[1:] == reference["tab_template"] for row in rows),
                    f"TXT_PDF_TAB_MISMATCH {set_number} {mode} {number} {direction}")
            routes = []
            for string in ROUTE_ORDER[direction]:
                row = rows[HIGH_TO_LOW.index(string)]
                frets = parse_cell(row, string, code, mode, direction)
                shift_after = spec["shift_after"]
                positions = POSITIONS[direction]
                notes = []
                for ordinal, (digit, fret) in enumerate(zip(code, frets, strict=True), 1):
                    position = positions[0] if ordinal <= shift_after else positions[1]
                    notes.append({"ordinal": ordinal, "string": string, "position": position,
                                  "finger_digit": digit, "finger_name": FINGER_NAMES[digit],
                                  "fret": fret, "landing": ordinal == spec["landing"],
                                  "onset_q": None, "duration_q": None})
                landing = notes[spec["landing"] - 1]
                routes.append({"route_ordinal": len(routes) + 1, "string": string,
                               "source_tab_row": row, "source_finger_row": finger,
                               "pdf_tab_template": reference["tab_template"],
                               "pdf_finger_template": reference["finger_template"],
                               "shift_after_note": shift_after,
                               "landing_note": {"ordinal": spec["landing"], "position": landing["position"],
                                                "finger_digit": landing["finger_digit"], "fret": landing["fret"]},
                               "notes": notes})
            directions.append({"direction": direction, "route_order": list(ROUTE_ORDER[direction]),
                               "position_order": list(POSITIONS[direction]),
                               "source_rows_high_to_low": rows, "source_finger_row": finger,
                               "pdf_tab_template": reference["tab_template"],
                               "pdf_finger_template": reference["finger_template"], "routes": routes})
        page = 2 * set_number + (0 if mode == "mode_a" else 1)
        modes.append({"mode": mode, "label": spec["name"], "shift_after_note": spec["shift_after"],
                      "landing_note_ordinal": spec["landing"], "picking_rule_source": spec["picking"],
                      "source_refs": {"txt": f"L10-TXT1-{txt_card['txt_start_line']}-{txt_card['txt_end_line']}",
                                      "pdf": f"L10-PDF1-p{page}"}, "directions": directions})
    return {"source_local_key": f"L10-set{set_number:02d}-ex{number}", "set": set_number,
            "exercise_number": number, "code": code, "modes": modes,
            "canonical_item_id": None, "canonical_variant_id": None,
            "onset_q": None, "duration_q": None, "fixed_bpm": None, "note_per_click": None,
            "runtime_eligible": False, "runtime_admitted": False, "imported": False, "admitted": False}


def build_candidate(*, txt_data: bytes | None = None, pdf_data: bytes | None = None,
                    root: Path = ROOT) -> dict[str, Any]:
    txt_data = local_bytes(root, TXT) if txt_data is None else txt_data
    pdf_data = local_bytes(root, PDF) if pdf_data is None else pdf_data
    verify(txt_data, TXT_PIN, "LEVEL10_TXT")
    verify(pdf_data, PDF_PIN, "LEVEL10_PDF")
    prior = prior_inputs(root)
    try:
        lines = txt_data.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise CandidateError("TXT_ENCODING_INVALID") from exc
    require(lines[0] == "108 FINGER PERMUTATIONS - LEVEL 10: ODD-COUNT POSITION TRANSFER", "TXT_TITLE")
    introduction = "\n".join(lines[:40])
    for phrase in ("Mode A - 3+1 late shift", "Mode B - 1+3 early shift", "The landing note is note 4",
                   "The landing note is note 2", "The barline marks the position shift only",
                   "not the melodic interval", "one string at a time"):
        require(phrase in introduction, f"TXT_INSTRUCTION_MISMATCH {phrase}")
    try:
        reader = PdfReader(BytesIO(pdf_data), strict=True)
        require(len(reader.pages) == 19, "PDF_PAGE_COUNT")
    except CandidateError:
        raise
    except Exception as exc:
        raise CandidateError("PDF_READ_FAILED") from exc
    records = []
    for set_number, (_, codes) in SETS.items():
        txt = parse_txt_set(lines, set_number)
        pdf = parse_pdf_set(reader, set_number)
        records.extend(project_record(set_number, code, index, txt, pdf)
                       for index, code in enumerate(codes))
    route_count = sum(len(direction["routes"]) for record in records for mode in record["modes"]
                      for direction in mode["directions"])
    note_count = sum(len(route["notes"]) for record in records for mode in record["modes"]
                     for direction in mode["directions"] for route in direction["routes"])
    require(len(records) == 72 and route_count == 1728 and note_count == 6912, "CANDIDATE_COVERAGE")
    return {"schema": "fathom-level010-sets04-09-detached-candidate-v1", "wbs_id": "2.3.1.1.1",
            "classification": "noncanonical_nonadmitted_source_candidate", "level": 10, "sets": list(SETS),
            "source": {"txt_path": TXT.as_posix(), "txt_bytes": TXT_PIN[0], "txt_sha256": TXT_PIN[1],
                       "pdf_path": PDF.as_posix(), "pdf_bytes": PDF_PIN[0], "pdf_sha256": PDF_PIN[1],
                       "pdf_pages": 19, "selected_pdf_pages": list(range(8, 20)),
                       "txt_set_refs": [f"L10-TXT1-{header}-{header + (447 if number < 9 else 445)}"
                                        for number, (header, _) in SETS.items()]},
            "released_prior_set_inputs": prior,
            "instructions": {"mode_a_shift_after_note": 3, "mode_a_landing_note": 4,
                             "mode_b_shift_after_note": 1, "mode_b_landing_note": 2,
                             "routes_are_sequential": True, "ascii_barline_is_clock": False,
                             "no_pick_reset": True},
            "counts": {"records": 72, "modes": 144, "directions": 288,
                       "string_routes": 1728, "untimed_note_positions": 6912},
            "records": records, "exceptions": [],
            "pending": ["Level 10 family Curriculum/musical review", "canonical identity allocation",
                        "runtime admission and timing decisions"],
            "canonical_item_id": None, "canonical_variant_id": None, "onset_q": None,
            "duration_q": None, "fixed_bpm": None, "note_per_click": None,
            "runtime_eligible": False, "runtime_admitted": False, "imported": False,
            "admitted": False, "whole_workbook_complete": False}


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
    parser.add_argument("--output", type=Path, required=True, help="new absolute P12 Build JSON path")
    args = parser.parse_args()
    try:
        data = serialize(build_candidate())
        write_output(args.output, data)
        print(f"PASS detached Level 10 Sets 4-9: 72 codes, 144 modes, 1728 routes, 6912 untimed notes; bytes={len(data)} sha256={digest(data)}")
        return 0
    except (CandidateError, OSError) as exc:
        print(f"FAIL {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
