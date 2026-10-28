#!/usr/bin/env python3
"""Normalize nine pinned detached Level 9 sets without identity or timing invention."""

from __future__ import annotations

import argparse
from io import BytesIO
import hashlib
import json
from pathlib import Path
import re
import subprocess
from typing import Any

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
BUILD_REL = Path("Build/parallel-11/2.3.1.1.1-level009-whole-r01")
TXT = ("Notes/music/guitar project/TXT version/108_Finger_Permutations_Level_9_Mid_Pattern_Position_Transfer.txt",
       "3cb0983c95081771caea7a12e8263d780f58850154681a9cd85c1a1916956105", 55960)
PDF = ("Notes/music/guitar project/PDF version/108_Finger_Permutations_Level_9_Mid_Pattern_Position_Transfer.pdf",
       "3564ed3c24d55df462dba49b81ef2aeaf9a716a5a5af993bfdbf3e774702b00f", 42285)
# Each final source candidate is a separate, released, read-only Build artifact.
SPECS = (
    (1, "Build/parallel-07/2.3.1.1.1-level009-set01-r01/candidate.json", "098bb861ddcabcaf48f75753988304c6a96ac6994140666d0c8c5070def8f94e", 290628, "p07"),
    (2, "Build/parallel-08/2.3.1.1.1-level009-set02-r01/candidate-01.json", "aa4f72064bccc13263e92c008e7e791d339e23e6a664d1eb86dce312d890b86c", 298499, "p08"),
    (3, "Build/parallel-09/2.3.1.1.1-level009-set03-r01/candidate-01.json", "4f9b00e6bb68183862d42c6d9570ae5778674b634c721cb2ff334a119ff7dee3", 298578, "p08"),
    (4, "Build/parallel-11/2.3.1.1.1-level009-set04-r01/candidate-final-a.json", "99cca1e1eb4498b103f3e68fc080e3c21eed0d421b0cd6c588ffa47761f0bccc", 324972, "p11"),
    (5, "Build/parallel-07/2.3.1.1.1-level009-set05-r01/candidate.json", "cc36ea65334c5153a6083cafe9e49a615270ea5d6993ae970dbc69a5792bfd04", 290614, "p07"),
    (6, "Build/parallel-08/2.3.1.1.1-level009-set06-r01/candidate-01.json", "cc0943d790714d4510a47969b694d176337f6879459242fd7997194d2ba2dc29", 298463, "p08"),
    (7, "Build/parallel-09/2.3.1.1.1-level009-set07-r01/candidate-01.json", "333dbba84a9099168ec48d3d3468919fc6f99a075b4244666509a783f74b02c4", 298476, "p08"),
    (8, "Build/parallel-11/2.3.1.1.1-level009-set08-r01/candidate-final-a.json", "f6e66604794cc2c7510d6e6191efd9d43c15b781ea97f1142705a42ab2a456d1", 325012, "p11"),
    (9, "Build/parallel-08/2.3.1.1.1-level009-set09-r01/candidate-01.json", "50e7ba4c8b74421ba3ade4a7c52d20554eeff3ab44e81f56c035be16acd8ef43", 298560, "p08"),
)
FINGERS = {"1": "index", "2": "middle", "3": "ring", "4": "pinky"}
HIGH_TO_LOW = ("e", "B", "G", "D", "A", "E")
DIRECTIONS = (("shift_up", tuple(reversed(HIGH_TO_LOW)), ("P5", "P7"), 2),
              ("shift_down", HIGH_TO_LOW, ("P7", "P5"), -2))
SET_HEAD = re.compile(r"^SET ([1-9]) OF 9 - EXERCISES (\d{3})-(\d{3})$")
TXT_HEAD = re.compile(r"^Exercise (\d{3}): ([1-4]{4})$")
PDF_HEAD = re.compile(r"^(\d{3})\s+([1-4]{4})$")
TXT_ROW = re.compile(r"^([eBGDAE])\|([0-9-]+)\|([0-9-]+)\|$")
PDF_ROW = re.compile(r"^S\|([0-9-]+)\|([0-9-]+)\|$")
CELL = re.compile(r"^((?:10|[5-9]))-((?:10|[5-9]))(-+)$")
UP_LABEL = "SHIFT UP - P5 to P7; digits 1-2 in P5, digits 3-4 in P7; play bottom line first: E-A-D-G-B-e"
DOWN_LABEL = "SHIFT DOWN - P7 to P5; digits 1-2 in P7, digits 3-4 in P5; play top line first: e-B-G-D-A-E"
COUNTS = {"sets": 9, "exercises": 108, "directions": 216, "one_string_routes": 1296,
          "two_note_cells": 2592, "notes": 5184}
TOP_KEYS = {"admitted", "exceptions", "imported", "instructions", "level", "pending", "records",
            "runtime_admitted", "runtime_eligible", "schema", "set", "source", "wbs_id",
            "whole_workbook_complete"}
RECORD_KEYS = {"admitted", "canonical_item_id", "canonical_variant_id", "code", "directions",
               "duration_q", "exercise_number", "fixed_bpm", "imported", "note_per_click",
               "onset_q", "runtime_admitted", "runtime_eligible", "source_local_key", "source_refs"}
FAMILY_KEYS = {
    "p07": ({"direction", "pdf_template", "route_order", "routes", "txt_tab_rows_high_to_low"},
            {"cells", "hand_frame_shift_frets", "shift_after_cell", "shift_after_note",
             "shift_at_center_barline", "source_tab_row", "string"},
            {"notes", "position"},
            {"ascii_column", "duration_q", "finger_digit", "finger_name", "fret", "onset_q", "ordinal"}),
    "p08": ({"direction", "pdf_template", "position_order", "string_order", "string_routes", "tab_rows_printed"},
            {"cells", "shift_after_note", "shift_frets", "string", "tab_row"},
            {"notes", "position"},
            {"duration_q", "finger_digit", "finger_name", "fret", "onset_q", "ordinal", "position", "string"}),
    "p11": ({"direction", "pdf_one_string_template", "position_order", "route_order",
             "sequential_one_string_routes", "txt_rows_high_to_low"},
            {"cells", "melodic_interval_inferred", "shift_after_note", "source_tab_row",
             "string", "whole_hand_frame_shift_frets"},
            {"notes", "position", "source_ascii_cell"},
            {"duration_q", "finger_digit", "finger_name", "fret", "onset_q", "ordinal", "position", "string"}),
}


class CoverageError(ValueError):
    """A pinned source or normalized Level 9 fact is missing or contradictory."""


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise CoverageError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def read_pinned(root: Path, path: str, digest: str, size: int) -> bytes:
    target = root / path
    try:
        resolved = target.resolve(strict=True)
    except FileNotFoundError as exc:
        raise CoverageError(f"missing pinned input: {path}") from exc
    if target.is_symlink() or not resolved.is_relative_to(root) or not resolved.is_file():
        raise CoverageError(f"unsafe pinned input: {path}")
    raw = target.read_bytes()
    if len(raw) != size or sha(raw) != digest:
        raise CoverageError(f"pinned input drift: {path}")
    return raw


def source_cards(txt: bytes, pdf: bytes) -> dict[int, dict[str, Any]]:
    try:
        lines = txt.decode("utf-8").splitlines()
        reader = PdfReader(BytesIO(pdf), strict=True)
    except Exception as exc:
        raise CoverageError("source decode/PDF read failure") from exc
    if len(reader.pages) != 10 or lines[0] != "108 FINGER PERMUTATIONS - LEVEL 9: MID-PATTERN POSITION TRANSFER":
        raise CoverageError("Level 9 source header/page count drift")
    sets = [(n + 1, m) for n, line in enumerate(lines) if (m := SET_HEAD.fullmatch(line))]
    if len(sets) != 9 or any((int(m.group(1)), int(m.group(2)), int(m.group(3))) != (s, 12 * s - 11, 12 * s)
                             for s, (_, m) in enumerate(sets, 1)):
        raise CoverageError("TXT set boundary/count drift")
    heads = [(n + 1, m) for n, line in enumerate(lines) if (m := TXT_HEAD.fullmatch(line))]
    if len(heads) != 108 or [int(m.group(1)) for _, m in heads] != list(range(1, 109)):
        raise CoverageError("TXT exercise order/count drift")
    cards: dict[int, dict[str, Any]] = {}
    for exercise, (first, match) in enumerate(heads, 1):
        body = lines[first:first + 14]
        if len(body) != 14 or body[0] != UP_LABEL or body[7] != DOWN_LABEL:
            raise CoverageError(f"TXT card/shift label drift: {exercise}")
        rows = {"shift_up": body[1:7], "shift_down": body[8:14]}
        for direction, printed in rows.items():
            if tuple((m.group(1) if (m := TXT_ROW.fullmatch(row)) else None) for row in printed) != HIGH_TO_LOW:
                raise CoverageError(f"TXT one-string row order: {exercise}:{direction}")
            if len({row[1:] for row in printed}) != 1:
                raise CoverageError(f"TXT repeated template conflict: {exercise}:{direction}")
        cards[exercise] = {"code": match.group(2), "txt_ref": f"L9-TXT1-{first}-{first + 14}",
                           "rows": rows}
    for set_number in range(1, 10):
        page = set_number + 1
        text = (reader.pages[set_number].extract_text() or "").splitlines()
        expected_head = ["Level 9 - Mid-Pattern Position Transfer",
                         f"Set {set_number} of 9 - Exercises {12 * set_number - 11:03d}-{12 * set_number:03d}",
                         "2+2: notes 1-2 in the starting frame, shift, then notes 3-4 in the destination frame."]
        expected_tail = ["Standard tuning. P5 = frets 5-8; P7 = frets 7-10. Shift the whole hand frame after note 2.",
                         f"Page {page} of 10"]
        if len(text) != 125 or text[:3] != expected_head or text[-2:] != expected_tail:
            raise CoverageError(f"PDF page/card boundary drift: {page}")
        for offset in range(12):
            exercise = 12 * (set_number - 1) + offset + 1
            block = text[3 + offset * 10:3 + (offset + 1) * 10]
            heading = PDF_HEAD.fullmatch(block[0])
            if heading is None or heading.groups() != (f"{exercise:03d}", cards[exercise]["code"]):
                raise CoverageError(f"PDF exercise/code mismatch: {exercise}")
            if block[1:5] != ["2+2 POSITION SPLIT", "UP", "E>A>D>G>B>e", "P5->P7"] or block[6:9] != ["DN", "e>B>G>D>A>E", "P7->P5"]:
                raise CoverageError(f"PDF route/frame labels: {exercise}")
            templates = {"shift_up": block[5], "shift_down": block[9]}
            for direction, template in templates.items():
                if PDF_ROW.fullmatch(template) is None or any("S" + row[1:] != template for row in cards[exercise]["rows"][direction]):
                    raise CoverageError(f"PDF/TXT template mismatch: {exercise}:{direction}")
            cards[exercise]["pdf_ref"] = f"L9-PDF1-p{page}"
            cards[exercise]["templates"] = templates
    if len(cards) != 108:
        raise CoverageError("source exercise coverage loss")
    return cards


def load_inputs(root: Path) -> tuple[dict[int, dict[str, Any]], dict[int, dict[str, Any]]]:
    root = root.resolve(strict=True)
    git_root = Path(subprocess.check_output(["git", "-C", str(root), "rev-parse", "--show-toplevel"], text=True).strip()).resolve()
    if root != git_root:
        raise CoverageError("--root must be the sole Git checkout top level")
    cards = source_cards(read_pinned(root, *TXT), read_pinned(root, *PDF))
    candidates: dict[int, dict[str, Any]] = {}
    for number, path, digest, size, _ in SPECS:
        raw = read_pinned(root, path, digest, size)
        try:
            candidate = json.loads(raw, object_pairs_hook=unique_object)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise CoverageError(f"invalid candidate JSON: set {number}") from exc
        if not isinstance(candidate, dict):
            raise CoverageError(f"candidate not an object: set {number}")
        candidates[number] = candidate
    return cards, candidates


def normalize(cards: dict[int, dict[str, Any]], candidates: dict[int, dict[str, Any]]) -> dict[str, Any]:
    if set(cards) != set(range(1, 109)) or set(candidates) != set(range(1, 10)):
        raise CoverageError("whole-Level9 source/candidate coverage gap")
    normalized: list[dict[str, Any]] = []
    inputs: list[dict[str, Any]] = []
    seen_keys: set[str] = set()
    for number, path, digest, size, family in SPECS:
        candidate = candidates[number]
        if set(candidate) != TOP_KEYS:
            raise CoverageError(f"candidate field/schema drift: set {number}")
        if (candidate.get("schema"), candidate.get("wbs_id"), candidate.get("level"), candidate.get("set")) != (f"fathom-level009-set{number:02d}-detached-candidate-v1", "2.3.1.1.1", 9, number):
            raise CoverageError(f"candidate schema/scope drift: set {number}")
        source = candidate.get("source")
        if not isinstance(source, dict) or any(source.get(key) != value for key, value in
            {"txt_path": TXT[0], "txt_sha256": TXT[1], "txt_bytes": TXT[2],
             "pdf_path": PDF[0], "pdf_sha256": PDF[1], "pdf_bytes": PDF[2],
             "pdf_pages": 10, "selected_pdf_page": number + 1}.items()):
            raise CoverageError(f"candidate source identity drift: set {number}")
        if any(candidate.get(key) is not False for key in
               ("admitted", "runtime_admitted", "runtime_eligible", "imported", "whole_workbook_complete")):
            raise CoverageError(f"false candidate admission: set {number}")
        records = candidate.get("records")
        if not isinstance(records, list) or len(records) != 12 or candidate.get("exceptions") != []:
            raise CoverageError(f"candidate record count/exception drift: set {number}")
        inputs.append({"set": number, "path": path, "sha256": digest, "bytes": size,
                       "schema_family": family, "instructions": candidate.get("instructions")})
        for offset, record in enumerate(records):
            exercise = 12 * (number - 1) + offset + 1
            source_card = cards[exercise]
            if not isinstance(record, dict) or set(record) != RECORD_KEYS:
                raise CoverageError(f"record field/schema drift: {exercise}")
            if not isinstance(record, dict) or record.get("exercise_number") != f"{exercise:03d}" or record.get("code") != source_card["code"]:
                raise CoverageError(f"candidate exercise/code order conflict: {exercise}")
            key = f"L9-set{number:02d}-ex{exercise:03d}"
            if record.get("source_local_key") != key or key in seen_keys:
                raise CoverageError(f"duplicate/missing source-local key: {exercise}")
            seen_keys.add(key)
            if record.get("source_refs") != {"txt": source_card["txt_ref"], "pdf": source_card["pdf_ref"]}:
                raise CoverageError(f"source ref conflict: {exercise}")
            if any(record.get(field) is not None for field in
                   ("canonical_item_id", "canonical_variant_id", "onset_q", "duration_q", "note_per_click", "fixed_bpm")):
                raise CoverageError(f"invented identity/timing: {exercise}")
            if any(record.get(field) is not False for field in
                   ("runtime_eligible", "runtime_admitted", "imported", "admitted")):
                raise CoverageError(f"false record admission: {exercise}")
            directions = record.get("directions")
            if not isinstance(directions, list) or len(directions) != 2:
                raise CoverageError(f"direction loss: {exercise}")
            result_directions = []
            for direction_index, (direction_name, order, positions, shift) in enumerate(DIRECTIONS):
                direction = directions[direction_index]
                if not isinstance(direction, dict) or set(direction) != FAMILY_KEYS[family][0] or direction.get("direction") != direction_name:
                    raise CoverageError(f"direction order conflict: {exercise}")
                if family == "p07":
                    route_order = direction.get("route_order")
                    printed_rows = direction.get("txt_tab_rows_high_to_low")
                    template = direction.get("pdf_template")
                    routes = direction.get("routes")
                elif family == "p08":
                    route_order = direction.get("string_order")
                    printed_rows = direction.get("tab_rows_printed")
                    template = direction.get("pdf_template")
                    routes = direction.get("string_routes")
                elif family == "p11":
                    route_order = direction.get("route_order")
                    printed_rows = direction.get("txt_rows_high_to_low")
                    template = direction.get("pdf_one_string_template")
                    routes = direction.get("sequential_one_string_routes")
                else:
                    raise CoverageError(f"unknown candidate route schema: set {number}")
                if (route_order, printed_rows, template) != (list(order), source_card["rows"][direction_name], source_card["templates"][direction_name]):
                    raise CoverageError(f"candidate route/template/source conflict: {exercise}:{direction_name}")
                if family != "p07" and direction.get("position_order") != list(positions):
                    raise CoverageError(f"position order conflict: {exercise}:{direction_name}")
                if not isinstance(routes, list) or len(routes) != 6:
                    raise CoverageError(f"one-string route loss: {exercise}:{direction_name}")
                by_string = dict(zip(HIGH_TO_LOW, printed_rows, strict=True))
                normalized_routes = []
                for route_index, string in enumerate(order):
                    route = routes[route_index]
                    if not isinstance(route, dict) or set(route) != FAMILY_KEYS[family][1]:
                        raise CoverageError(f"route field/schema drift: {exercise}:{string}")
                    row = route.get("source_tab_row") if family != "p08" else route.get("tab_row")
                    shift_value = route.get("hand_frame_shift_frets") if family == "p07" else route.get("shift_frets") if family == "p08" else route.get("whole_hand_frame_shift_frets")
                    if route.get("string") != string or row != by_string[string] or route.get("shift_after_note") != 2 or shift_value != shift:
                        raise CoverageError(f"one-string route/shift conflict: {exercise}:{direction_name}:{string}")
                    if family == "p07" and (route.get("shift_after_cell") != 1 or route.get("shift_at_center_barline") is not True):
                        raise CoverageError(f"P07 shift boundary conflict: {exercise}:{string}")
                    if family == "p11" and route.get("melodic_interval_inferred") is not False:
                        raise CoverageError(f"false melodic direction claim: {exercise}:{string}")
                    match = TXT_ROW.fullmatch(row)
                    cells = route.get("cells")
                    if match is None or not isinstance(cells, list) or len(cells) != 2:
                        raise CoverageError(f"cell loss/shape: {exercise}:{string}")
                    normalized_notes = []
                    for cell_index, position in enumerate(positions):
                        cell = cells[cell_index]
                        printed = match.group(cell_index + 2)
                        cm = CELL.fullmatch(printed)
                        notes = cell.get("notes") if isinstance(cell, dict) else None
                        if cm is None or not isinstance(cell, dict) or set(cell) != FAMILY_KEYS[family][2] or cell.get("position") != position or not isinstance(notes, list) or len(notes) != 2:
                            raise CoverageError(f"2+2 cell conflict: {exercise}:{string}:{cell_index}")
                        if family == "p11" and cell.get("source_ascii_cell") != printed:
                            raise CoverageError(f"P11 source cell conflict: {exercise}:{string}")
                        frets = (int(cm.group(1)), int(cm.group(2)))
                        for local_index, note in enumerate(notes):
                            ordinal = 2 * cell_index + local_index + 1
                            finger = source_card["code"][ordinal - 1]
                            expected_fret = int(finger) + (4 if position == "P5" else 6)
                            if not isinstance(note, dict) or set(note) != FAMILY_KEYS[family][3] or (note.get("ordinal"), note.get("finger_digit"), note.get("finger_name"), note.get("fret")) != (ordinal, finger, FINGERS[finger], expected_fret) or frets[local_index] != expected_fret:
                                raise CoverageError(f"finger/fret/order conflict: {exercise}:{string}:{ordinal}")
                            if note.get("onset_q", "missing") is not None or note.get("duration_q", "missing") is not None:
                                raise CoverageError(f"invented note timing: {exercise}:{string}:{ordinal}")
                            if "string" in note and note["string"] != string or "position" in note and note["position"] != position:
                                raise CoverageError(f"note string/frame conflict: {exercise}:{string}:{ordinal}")
                            normalized_notes.append({"ordinal": ordinal, "string": string, "position": position,
                                                     "finger_digit": finger, "finger_name": FINGERS[finger],
                                                     "fret": expected_fret, "onset_q": None, "duration_q": None})
                    normalized_routes.append({"string": string, "source_tab_row": row,
                                              "shift_after_note": 2, "whole_hand_frame_shift_frets": shift,
                                              "melodic_interval_inferred": False, "notes": normalized_notes})
                result_directions.append({"direction": direction_name, "route_order": list(order),
                                          "position_order": list(positions), "pdf_template": template,
                                          "printed_rows_high_to_low": printed_rows,
                                          "sequential_one_string_routes": normalized_routes})
            normalized.append({"exercise_number": exercise, "code": source_card["code"],
                               "source_local_key": key,
                               "source_refs": {"txt": source_card["txt_ref"], "pdf": source_card["pdf_ref"]},
                               "candidate_path": path, "original_record_sha256": sha(canonical(record)),
                               "original_record": record, "directions": result_directions,
                               "canonical_item_id": None, "canonical_variant_id": None,
                               "onset_q": None, "duration_q": None, "note_per_click": None,
                               "fixed_bpm": None, "runtime_eligible": False, "admitted": False})
    if len(normalized) != 108 or len(seen_keys) != 108:
        raise CoverageError("normalized record coverage loss")
    return {"schema": "fathom-level009-whole-detached-normalization.1", "wbs_id": "2.3.1.1.1",
            "classification": "source_bound_non_admitted_aggregate",
            "source_authority": {"txt": {"path": TXT[0], "sha256": TXT[1], "bytes": TXT[2]},
                                 "pdf": {"path": PDF[0], "sha256": PDF[1], "bytes": PDF[2]}},
            "candidate_inputs": inputs, "counts": COUNTS, "records": normalized,
            "canonical_schema_validated": False, "runtime_eligible": False, "imported": False,
            "admitted": False, "whole_workbook_complete": False,
            "required_decisions": ["Reviewed stable identities and lineage", "Source-authorized note timing, meter and note-per-click",
                                   "Curriculum/musical review and canonical admission"]}


def build(root: Path = ROOT) -> dict[str, Any]:
    return normalize(*load_inputs(root))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        root = ROOT.resolve(strict=True)
        output = args.output if args.output.is_absolute() else root / args.output
        allowed = (root / BUILD_REL).resolve(strict=False)
        if output.parent.resolve(strict=False) != allowed or output.exists() or output.is_symlink() or output.suffix != ".json":
            raise CoverageError("output must be a new JSON file in the P11 whole-Level9 Build lane")
        raw = (json.dumps(build(root), ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("xb") as stream:
            stream.write(raw)
    except (CoverageError, OSError, subprocess.CalledProcessError) as exc:
        parser.exit(2, f"LEVEL9 NORMALIZATION STOP: {exc}\n")
    print(f"NORMALIZATION PASS {output} records=108 notes=5184 admitted=false sha256={sha(raw)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
