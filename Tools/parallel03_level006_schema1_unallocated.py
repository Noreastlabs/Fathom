#!/usr/bin/env python3
"""Build an independent, unallocated schema1-shaped Level 6 proposal."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT_REL = Path("Build/parallel-03/level006-schema1-unallocated-r01")
TXT_REL = Path(
    "Notes/music/guitar project/TXT version/"
    "108_Finger_Permutations_Level_6_Odd_Count_String_Skip_Transfer.txt"
)
PDF_REL = Path(
    "Notes/music/guitar project/PDF version/"
    "108_Finger_Permutations_Level_6_Odd_Count_String_Skip_Transfer.pdf"
)
SOURCE_MAP_REL = Path(
    "Results/parallel-01/exercises/inventory/"
    "20260922T180500Z-2.3-curriculum-v1-source-inventory-evidence/"
    "curriculum-source-map.tsv"
)
PACKAGE_REL = Path("Content/controls/curriculum-v1/package.json")
REGISTRY_REL = Path("Content/controls/curriculum-v1/identity-registry.json")
GENERATION_REL = Path("Content/controls/curriculum-v1/generation.json")
SCHEMA_FREEZE_REL = Path(
    "Results/primary/20260912T100538Z-2.1.1.2.1-r02-evidence/schema-freeze.json"
)
SCHEMA_CONTRACT_REL = Path(
    "Results/primary/20260912T100538Z-2.1.1.2.1-r02-evidence/contract.md"
)


class ProposalError(ValueError):
    """Pinned input or non-importable proposal invariant was violated."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ProposalError(message)


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def encoded(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        require(key not in result, f"duplicate JSON key: {key}")
        result[key] = value
    return result


def sha_spec(path: str, size: int, sha: str, role: str) -> dict[str, Any]:
    return {"path": path, "bytes": size, "sha256": sha, "role": role}


PINS: list[dict[str, Any]] = [
    sha_spec(TXT_REL.as_posix(), 126760,
             "bbd337b205eac66e474b7b90dea7c5e18c35fe6f09eec7aee3a058f1c0eb4d19", "original Level6 TXT; generation source"),
    sha_spec(PDF_REL.as_posix(), 85764,
             "a2b97e01ad98bc4e01dfeccfb799b19a5c3c712c233cc9def5e8d95ca16aaac8", "original paired Level6 PDF; source page identity"),
    sha_spec(SOURCE_MAP_REL.as_posix(), 68536,
             "f526ff4d9ce3bceaf9a7cc581a3ac2aee2c74917eba984dd57913adba574c123", "current source map"),
    sha_spec(PACKAGE_REL.as_posix(), 24698658,
             "766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255", "current659 package/catalog"),
    sha_spec(REGISTRY_REL.as_posix(), 10008718,
             "5d265859e1e8a5a530a0e53d88b019a1c920f3bba6cccb4ef0fef2f7640007e5", "current659 identity registry"),
    sha_spec(GENERATION_REL.as_posix(), 9313623,
             "fc6cec9f9d67eb82c97c5f4c3fb95d285178fb7fce7bd147d9ae0296d21b4c1c", "current659 generation record"),
    sha_spec(SCHEMA_FREEZE_REL.as_posix(), 2737,
             "0659fa962a5c933a2bcf3045772b6fe5b05b4deefb3511f5dcb68af51088de95", "frozen schema1 contract decision"),
    sha_spec(SCHEMA_CONTRACT_REL.as_posix(), 10912,
             "3f6e3d91ff46d8dce46d3b5e4a00e36d41b1bbc6767bbc7f1be2e914f4eadb94", "frozen schema1 field contract"),
    sha_spec("Results/parallel-04/exercises/conversion/20260923T131029Z-2.3.1.1.1-level006-set09-candidate-r04-results.md", 6753,
             "a4aa2ea3700e0e172d4cf161fff6217c9e017678e6cb839044f7697e947f5cc3", "P04 sealed whole-Level6 set-candidate result"),
    sha_spec("Results/parallel-06/governance/20260923T135400Z-2.3-level006-batch-integrity-r01-results.md", 3583,
             "2db533921218b0faf60d716c02f19ad35ce43c8d2b9094bde9b75f298afd2334", "P06 sealed Level6 aggregate-index result"),
    sha_spec("Results/parallel-11/curriculum/20260923T144000Z-2.3-level006-draft-materializer-r01-results.md", 3218,
             "ba503f9288de5c0a71449ed97aaa4a494542e27a1f729e4a210c6675de631daf", "P11 sealed whole-Level6 draft result"),
]

P04_CANDIDATES = [
    sha_spec("Build/parallel-04/2.3.1.1.1-level006-set01-r01/candidate.json", 887662,
             "b763ce846562c6dc8dcd66c0b651a28d28c0963d6b1addf76161140d08c69729", "P04 Set1 read-only parity control"),
    sha_spec("Build/parallel-04/2.3.1.1.1-level006-set02-r02/candidate.json", 887709,
             "486216ca6f3e8774e11c8d80e277efc3a128a1fe44ec57a2b16bf80bef392bf2", "P04 Set2 read-only parity control"),
    sha_spec("Build/parallel-04/2.3.1.1.1-level006-set03-r01/candidate.json", 888185,
             "aa8d2b0868e08a25b98bda82966e3c4ac37205c73396db3c3f8d252eb7372483", "P04 Set3 read-only parity control"),
    sha_spec("Build/parallel-04/2.3.1.1.1-level006-set04-r01/candidate.json", 888437,
             "a689cade24ee25ada4cba16b0a2f700e3518306bcbde49f96f0fb81d040797e5", "P04 Set4 read-only parity control"),
    sha_spec("Build/parallel-04/2.3.1.1.1-level006-set05-r01/candidate.json", 888639,
             "7f10d72079b24de7a3366c754b667101de6ad4184b744aa4c555191dc1ba07c6", "P04 Set5 read-only parity control"),
    sha_spec("Build/parallel-04/2.3.1.1.1-level006-set06-r01/candidate.json", 888563,
             "32e75668bedbef137cb1b2a25ce362668e1e1b1a6223155fa1b683e687a9bf60", "P04 Set6 read-only parity control"),
    sha_spec("Build/parallel-04/2.3.1.1.1-level006-set07-r01/candidate.json", 888531,
             "fc9f0bd8eaad676695600a649aa2bc26d9e78869573ebddcdbeabb11d3c1fa64", "P04 Set7 read-only parity control"),
    sha_spec("Build/parallel-04/2.3.1.1.1-level006-set08-r01/candidate.json", 888663,
             "b5676520593dc06ed7cbf119a1aca06c9582efa65cc76e64fd8b797cbb4f2ad6", "P04 Set8 read-only parity control"),
    sha_spec("Build/parallel-04/2.3.1.1.1-level006-set09-r02/candidate.json", 888618,
             "aa5b229e07b8ce722389bd4b3cc2892f04c419ab262b9db4ddaa8a220a5407b2", "P04 Set9 read-only parity control"),
]
P06_INDEX = sha_spec(
    "Build/parallel-06/2.3-level006-batch-integrity-r01/index-a.json", 126514,
    "ce16f26098ce583288b1a98ff2fcca3b09b50286f4e4feeea5feace6bd07479d", "P06 read-only all-record index")
P11_DRAFT = sha_spec(
    "Build/parallel-11/2.3-level006-draft-materializer-r01/draft-final-a.json", 5451350,
    "f87637b01dec4c32ef92e425ed329de6e359f722e1fe35a8c7c8136304f1ac8e", "P11 read-only whole-level draft")
ALL_PINS = PINS + P04_CANDIDATES + [P06_INDEX, P11_DRAFT]

STRING_ORDER_HIGH_TO_LOW = ("e", "B", "G", "D", "A", "E")
STRING_NUMBER_LOW_TO_HIGH = {"E": 1, "A": 2, "D": 3, "G": 4, "B": 5, "e": 6}
OPEN_MIDI = {"E": 40, "A": 45, "D": 50, "G": 55, "B": 59, "e": 64}
FINGER = {"1": "index", "2": "middle", "3": "ring", "4": "pinky"}
FRET = {"1": 5, "2": 6, "3": 7, "4": 8}
MODE = {
    "A": {"heading": "MODE A - 3+1 LATE SKIP", "name": "3+1 late skip", "crossing": 3,
          "ascend": "ASCEND - E-D, A-G, D-B, G-e", "descend": "DESCEND - e-G, B-D, G-A, D-E",
          "routes": [("E", "D", "A"), ("A", "G", "D"), ("D", "B", "G"), ("G", "e", "B")]},
    "B": {"heading": "MODE B - 1+3 EARLY SKIP", "name": "1+3 early skip", "crossing": 1,
          "ascend": "ASCEND - E-D, A-G, D-B, G-e", "descend": "DESCEND - e-G, B-D, G-A, D-E",
          "routes": [("E", "D", "A"), ("A", "G", "D"), ("D", "B", "G"), ("G", "e", "B")]},
}
DESCENDING_ROUTES = [("e", "G", "B"), ("B", "D", "G"), ("G", "A", "D"), ("D", "E", "A")]
EXPECTED_SET_HEADING = "SET {set_number} OF 9 - EXERCISES {first:03d}-{last:03d}"
TAB_CHARACTERS = set("-0123456789")
UNRESOLVED_TIMING = [
    "No note-level onset, duration, meter, or beat count is specified for the printed four-note cells.",
    "The source gives relative tempo adjustment guidance, not a fixed BPM for the proposed record.",
    "Straight-16th, triplet, and quintuplet grouping choices are session options; none is selected here.",
    "Both downstroke and upstroke starts are instructed; no per-event D/U stroke sequence or canonical variant partition is assigned.",
    "The four ASCII cell columns locate printed source notes and are not interpreted as beats or note-per-click values.",
]
OUT_NAMES = (
    "field-proposal-a.json",
    "field-proposal-b.json",
    "allocation-handoff.json",
    "input-manifest.json",
)


def pinned_bytes(root: Path, spec: dict[str, Any]) -> bytes:
    path = root / spec["path"]
    try:
        resolved = path.resolve(strict=True)
    except FileNotFoundError as exc:
        raise ProposalError(f"missing pinned input: {spec['path']}") from exc
    if path.is_symlink() or not resolved.is_relative_to(root) or not resolved.is_file():
        raise ProposalError(f"unsafe pinned input: {spec['path']}")
    raw = resolved.read_bytes()
    if len(raw) != spec["bytes"] or digest(raw) != spec["sha256"]:
        raise ProposalError(f"pinned input drift: {spec['path']}")
    return raw


def verify_all_pins(root: Path) -> list[dict[str, Any]]:
    manifest: list[dict[str, Any]] = []
    for spec in ALL_PINS:
        pinned_bytes(root, spec)
        manifest.append(dict(spec))
    return manifest


def load_json(raw: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(raw, object_pairs_hook=unique_object)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProposalError(f"invalid JSON: {label}") from exc
    if not isinstance(value, dict):
        raise ProposalError(f"expected JSON object: {label}")
    return value


def verify_authority(root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    package = load_json(pinned_bytes(root, {"path": PACKAGE_REL.as_posix(), "bytes": 24698658,
                                           "sha256": "766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255"}),
                       PACKAGE_REL.as_posix())
    registry = load_json(pinned_bytes(root, {"path": REGISTRY_REL.as_posix(), "bytes": 10008718,
                                            "sha256": "5d265859e1e8a5a530a0e53d88b019a1c920f3bba6cccb4ef0fef2f7640007e5"}),
                         REGISTRY_REL.as_posix())
    generation = load_json(pinned_bytes(root, {"path": GENERATION_REL.as_posix(), "bytes": 9313623,
                                               "sha256": "fc6cec9f9d67eb82c97c5f4c3fb95d285178fb7fce7bd147d9ae0296d21b4c1c"}),
                            GENERATION_REL.as_posix())
    freeze = load_json(pinned_bytes(root, {"path": SCHEMA_FREEZE_REL.as_posix(), "bytes": 2737,
                                          "sha256": "0659fa962a5c933a2bcf3045772b6fe5b05b4deefb3511f5dcb68af51088de95"}),
                       SCHEMA_FREEZE_REL.as_posix())
    contract = pinned_bytes(root, {"path": SCHEMA_CONTRACT_REL.as_posix(), "bytes": 10912,
                                   "sha256": "3f6e3d91ff46d8dce46d3b5e4a00e36d41b1bbc6767bbc7f1be2e914f4eadb94"})
    require(len(package.get("records", [])) == 659, "CURRENT_PACKAGE_RECORD_COUNT")
    require(generation.get("records") == 659, "GENERATION_RECORD_COUNT")
    entries = package.get("workbook_catalog", {}).get("entries", [])
    require(len(entries) == 105, "WORKBOOK_CATALOG_COUNT")
    catalog = [entry for entry in entries if entry.get("workbook_id") == "fg:workbook:000006"]
    require(len(catalog) == 1, "LEVEL6_CATALOG_ROW")
    entry = catalog[0]
    require(entry.get("catalog_role") == "read_only_source_preservation" and
            entry.get("conversion_status") == "not_converted" and
            entry.get("stable_identity_status") == "evidenced_source_only", "LEVEL6_CATALOG_CLASSIFICATION")
    require(entry.get("representative_item_id") is None and entry.get("whole_workbook_complete") is False,
            "LEVEL6_CATALOG_COVERAGE_STATE")
    require(all(entry.get(key) is False for key in
                ("admitted", "imported", "runtime_eligible", "runtime_admitted")), "LEVEL6_CATALOG_ADMISSION")
    require(not any(row.get("legacy_level") == 6 or row.get("workbook_id") == "fg:workbook:000006"
                    for row in package["records"]), "LEVEL6_CANONICAL_RECORD_EXISTS")
    require(not any(entity.get("id") == "fg:workbook:000006" for entity in registry.get("entities", [])),
            "LEVEL6_CANONICAL_WORKBOOK_ENTITY_EXISTS")
    require(freeze.get("decision") == "Technical schema1 FROZEN" and
            freeze.get("schema_version") == "1.0.0-curriculum-candidate", "SCHEMA1_FREEZE")
    require(b"1.0.0-curriculum-candidate" in contract, "SCHEMA1_CONTRACT_VERSION")
    return package, registry, generation, freeze, entry, {"contract_sha256": digest(contract)}


def verify_source_map(root: Path) -> dict[str, str]:
    raw = pinned_bytes(root, next(spec for spec in PINS if spec["path"] == SOURCE_MAP_REL.as_posix()))
    try:
        rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8")), delimiter="\t"))
    except (UnicodeDecodeError, csv.Error) as exc:
        raise ProposalError("invalid source-map TSV") from exc
    matching = [row for row in rows if row.get("level") == "6"]
    require(len(matching) == 1, "LEVEL6_SOURCE_MAP_ROW")
    row = matching[0]
    expected = {
        "level": "6", "section": "I", "instructional_family": "Finger coordination and position control",
        "wbs_owner": "2.3.1.1.1", "txt_path": TXT_REL.as_posix(), "txt_bytes": "126760",
        "txt_sha256": "bbd337b205eac66e474b7b90dea7c5e18c35fe6f09eec7aee3a058f1c0eb4d19",
        "pdf_path": PDF_REL.as_posix(), "pdf_bytes": "85764",
        "pdf_sha256": "a2b97e01ad98bc4e01dfeccfb799b19a5c3c712c233cc9def5e8d95ca16aaac8",
        "pair_status": "exact_stem_pair", "representative_status": "outside_representative_package",
        "representative_item_id": "", "review": "Pending", "conversion_status": "not_converted",
        "stable_ids_assigned": "False", "runtime_eligible": "False", "imported": "False", "admitted": "False",
    }
    for key, value in expected.items():
        require(row.get(key) == value, f"SOURCE_MAP_{key.upper()}")
    return row


def parse_tab_row(line: str) -> tuple[str, tuple[str, str, str, str]]:
    if "|" not in line:
        raise ProposalError("TAB_ROW_MISSING_SEPARATOR")
    fields = line.split("|")
    require(len(fields) == 6 and fields[0] in STRING_ORDER_HIGH_TO_LOW and fields[-1] == "", "TAB_ROW_SHAPE")
    groups = fields[1:5]
    require(all(len(group) == 8 and set(group) <= TAB_CHARACTERS for group in groups), "TAB_CELL_WIDTH_OR_SYMBOL")
    return fields[0], (groups[0], groups[1], groups[2], groups[3])


def parse_rows(lines: list[str], start: int, label: str) -> dict[str, tuple[str, str, str, str]]:
    rows = [parse_tab_row(lines[start + offset]) for offset in range(6)]
    require([name for name, _ in rows] == list(STRING_ORDER_HIGH_TO_LOW), f"{label}_STRING_ROW_ORDER")
    require(len({name for name, _ in rows}) == 6, f"{label}_STRING_ROW_DUPLICATE")
    return {name: groups for name, groups in rows}


def make_events(case_key: str, code: str, mode: str, direction: str,
                routes: list[tuple[str, str, str]], table: dict[str, tuple[str, str, str, str]],
                txt_ref: str, pdf_page: int) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    source_ordinals = (1, 2, 3) if mode == "A" else (1,)
    target_ordinals = (4,) if mode == "A" else (2, 3, 4)
    for cell_index, (source, target, silent) in enumerate(routes, 1):
        by_string = {name: list(enumerate(table[name][cell_index - 1])) for name in STRING_ORDER_HIGH_TO_LOW}
        for name, chars in by_string.items():
            digits = [(column, char) for column, char in chars if char.isdigit()]
            expected_count = len(source_ordinals) if name == source else len(target_ordinals) if name == target else 0
            require(len(digits) == expected_count, "TAB_CELL_NOTE_PLACEMENT")
            expected_digits = [str(FRET[code[index - 1]]) for index in (source_ordinals if name == source else target_ordinals if name == target else ())]
            require([digit for _, digit in digits] == expected_digits, "TAB_CELL_CODE_ORDER")
            require(all(column in (0, 2, 4, 6) for column, _ in digits), "TAB_CELL_ASCII_COLUMN")
        for ordinal, digit in enumerate(code, 1):
            name = source if ordinal in source_ordinals else target
            string_rows = table[name][cell_index - 1]
            note_positions = [(column, char) for column, char in enumerate(string_rows) if char.isdigit()]
            position_in_row = source_ordinals.index(ordinal) if ordinal in source_ordinals else target_ordinals.index(ordinal)
            column, printed_fret = note_positions[position_in_row]
            fret = FRET[digit]
            require(int(printed_fret) == fret, "PRINTED_FRET_DIGIT_MAP")
            key = f"{case_key}:{direction}:cell-{cell_index:02d}:note-{ordinal:02d}"
            events.append({
                "event_id": None,
                "kind": "note",
                "attack": "picked",
                "string": STRING_NUMBER_LOW_TO_HIGH[name],
                "fret": fret,
                "midi": OPEN_MIDI[name] + fret,
                "finger": int(digit),
                "onset_q": None,
                "duration_q": None,
                "spelling": None,
                "tie_from": None,
                "degree_contexts": {},
                "source_local_provenance": {
                    "source_local_event_key": key,
                    "source_local_cell_key": f"{case_key}:{direction}:cell-{cell_index:02d}",
                    "source_txt_ref": txt_ref,
                    "source_pdf_page": pdf_page,
                    "direction": direction,
                    "source_pair": f"{source}-{target}",
                    "source_string": name,
                    "target_string": target,
                    "silent_intervening_string": silent,
                    "source_cell_order": cell_index,
                    "source_note_order_in_cell": ordinal,
                    "source_digit": digit,
                    "source_finger_assignment": FINGER[digit],
                    "source_fret": fret,
                    "ascii_column": column,
                    "midi_derivation": "standard_tuning_open_midi_plus_printed_fret",
                },
            })
    return events


def parse_exercise(lines: list[str], index: int, set_number: int, mode: str) -> dict[str, Any]:
    header = lines[index]
    parts = header.split(": ")
    require(len(parts) == 2 and parts[0].startswith("Exercise "), "EXERCISE_HEADER")
    try:
        exercise_number = int(parts[0].removeprefix("Exercise "))
    except ValueError as exc:
        raise ProposalError("EXERCISE_NUMBER") from exc
    code = parts[1]
    require(len(code) == 4 and all(char in FINGER for char in code), "EXERCISE_CODE")
    spec = MODE[mode]
    require(lines[index + 1] == spec["ascend"], "ASCENDING_ROUTE_LABEL")
    require(lines[index + 8] == spec["descend"], "DESCENDING_ROUTE_LABEL")
    ascending = parse_rows(lines, index + 2, "ASCENDING")
    descending = parse_rows(lines, index + 9, "DESCENDING")
    start_line = index + 1
    end_line = index + 15
    txt_ref = f"L6-TXT1-{start_line}-{end_line}"
    pdf_page = 2 + (set_number - 1) * 2 + (1 if mode == "B" else 0)
    case_key = f"L006-S{set_number:02d}-MODE-{mode}-EX-{exercise_number:03d}"
    routes = spec["routes"]
    events = make_events(case_key, code, mode, "ascending", routes, ascending, txt_ref, pdf_page)
    events.extend(make_events(case_key, code, mode, "descending", DESCENDING_ROUTES, descending, txt_ref, pdf_page))
    require(len(events) == 32, "RECORD_EVENT_COUNT")
    source_refs = [txt_ref, f"L6-PDF1-p{pdf_page}", "L6-TXT1-1-23", "L6-PDF1-p1"]
    context = {
        "set_number": set_number,
        "exercise_number": exercise_number,
        "pattern_code": code,
        "movement_mode": spec["name"],
        "crossing_after_note": spec["crossing"],
        "position": "fifth",
        "tuning": "standard",
        "tuning_open_midi_low_to_high": [40, 45, 50, 55, 59, 64],
        "source_code_order_preserved": True,
        "source_digits_to_finger_and_fret": {
            digit: {"finger": FINGER[digit], "fret": FRET[digit]} for digit in "1234"
        },
        "direction_options_from_source": ["ascending", "descending"],
        "pick_start_options_from_source": ["downstroke", "upstroke"],
        "rhythmic_grouping_options_from_source": ["straight-16th", "triplet", "quintuplet"],
        "active_grouping_for_this_proposal": None,
    }
    title = f"Level 6 Set {set_number} Mode {mode} Exercise {exercise_number:03d} {code}"
    schema_fields = {
        "id": None,
        "workbook_id": None,
        "module_id": None,
        "legacy_level": 6,
        "title": title,
        "kind": "notation",
        "content_revision": None,
        "lineage": None,
        "runtime_eligible": False,
        "source_refs": source_refs,
        "authored_text_refs": [txt_ref, "L6-TXT1-1-23"],
        "context": context,
        "control_scope": {
            "basis_refs": source_refs,
            "extent": "complete_selected_mode_exercise_source_projection",
            "local_case": case_key,
            "source_event_count": len(events),
            "unresolved": list(UNRESOLVED_TIMING),
            "whole_workbook_complete": False,
        },
        "events": events,
        "variants": [],
        "timing": {
            "status": "unresolved",
            "unit": None,
            "meter": None,
            "fixed_bpm": None,
            "note_per_click": None,
            "onset_q": None,
            "duration_q": None,
            "active_grouping": None,
            "basis": "No note-level time is inferred from ASCII positions or relative practice guidance.",
        },
        "rubric": None,
        "resource_requirements": [],
        "ambiguities": list(UNRESOLVED_TIMING),
    }
    return {
        "source_local_case_key": case_key,
        "status": "source_mapped_unallocated",
        "set_number": set_number,
        "mode": mode,
        "exercise_number": exercise_number,
        "pattern_code": code,
        "source_refs": source_refs,
        "source_event_count": len(events),
        "schema1_fields": schema_fields,
        "canonical_schema_validated": False,
        "runtime_eligible": False,
        "admitted": False,
    }


def parse_source(raw: bytes) -> list[dict[str, Any]]:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ProposalError("TXT_NOT_UTF8") from exc
    lines = text.splitlines()
    require(len(lines) == 3605, "TXT_LINE_COUNT")
    require(lines[0] == "108 FINGER PERMUTATIONS - LEVEL 6: ODD-COUNT STRING-SKIP TRANSFER", "TXT_LEVEL_HEADER")
    require(lines[1] == "3+1 / 1+3 gap control in standard tuning.", "TXT_MODE_HEADER")
    require(lines[2] == "Fifth position: 1=index/fret 5, 2=middle/fret 6, 3=ring/fret 7, 4=pinky/fret 8.", "TXT_FINGER_POSITION")
    require(lines[4] == "MOVEMENT RULE" and lines[14] == "PRACTICE RULE", "TXT_INSTRUCTION_BLOCKS")
    parsed: list[dict[str, Any]] = []
    current_set: int | None = None
    current_mode: str | None = None
    set_modes: dict[int, list[str]] = {}
    mode_exercises: dict[tuple[int, str], list[dict[str, Any]]] = {}
    set_re = __import__("re").compile(r"^SET (\d+) OF 9 - EXERCISES (\d{3})-(\d{3})$")
    mode_re = __import__("re").compile(r"^MODE ([AB]) - (?:3\+1 LATE SKIP|1\+3 EARLY SKIP)$")
    exercise_re = __import__("re").compile(r"^Exercise (\d{3}): ([1-4]{4})$")
    for index, line in enumerate(lines):
        set_match = set_re.fullmatch(line)
        if set_match:
            current_set = int(set_match.group(1))
            first, last = int(set_match.group(2)), int(set_match.group(3))
            require(current_set == len(set_modes) + 1 and (first, last) == ((current_set - 1) * 12 + 1, current_set * 12),
                    "SET_ORDER_OR_RANGE")
            set_modes[current_set] = []
            current_mode = None
            continue
        mode_match = mode_re.fullmatch(line)
        if mode_match:
            require(current_set is not None, "MODE_WITHOUT_SET")
            current_mode = mode_match.group(1)
            require(current_mode not in set_modes[current_set], "DUPLICATE_MODE")
            set_modes[current_set].append(current_mode)
            mode_exercises[(current_set, current_mode)] = []
            require(line == MODE[current_mode]["heading"], "MODE_HEADING")
            continue
        exercise_match = exercise_re.fullmatch(line)
        if exercise_match:
            require(current_set is not None and current_mode is not None, "EXERCISE_OUTSIDE_MODE")
            source_number, source_code = int(exercise_match.group(1)), exercise_match.group(2)
            expected_number = (current_set - 1) * 12 + len(mode_exercises[(current_set, current_mode)]) + 1
            require(source_number == expected_number, "EXERCISE_ORDER")
            require(line == lines[index], "EXERCISE_LINE_IDENTITY")
            record = parse_exercise(lines, index, current_set, current_mode)
            require(record["exercise_number"] == source_number and record["pattern_code"] == source_code,
                    "EXERCISE_PARSE_IDENTITY")
            mode_exercises[(current_set, current_mode)].append(record)
            parsed.append(record)
    require(set(set_modes) == set(range(1, 10)), "SET_COVERAGE")
    for set_number in range(1, 10):
        require(set_modes[set_number] == ["A", "B"], "MODE_ORDER_OR_COVERAGE")
        a = mode_exercises[(set_number, "A")]
        b = mode_exercises[(set_number, "B")]
        require(len(a) == len(b) == 12, "SET_MODE_EXERCISE_COUNT")
        require([r["pattern_code"] for r in a] == [r["pattern_code"] for r in b], "MODE_CODE_PARITY")
        require(len({r["pattern_code"] for r in a}) == 12, "DUPLICATE_CODE_WITHIN_SET")
    require(len(parsed) == 216 and sum(record["source_event_count"] for record in parsed) == 6912,
            "WHOLE_LEVEL_RECORD_OR_EVENT_COUNT")
    require([r["mode"] for r in parsed[:24]] == ["A"] * 12 + ["B"] * 12, "FIRST_SET_RECORD_ORDER")
    return parsed


def source_authority(root: Path, package: dict[str, Any], entry: dict[str, Any], source_map: dict[str, str],
                     pins: list[dict[str, Any]], contract_identity: dict[str, Any]) -> dict[str, Any]:
    return {
        "txt": next({k: pin[k] for k in ("path", "bytes", "sha256")} for pin in pins if pin["path"] == TXT_REL.as_posix()),
        "pdf": next({k: pin[k] for k in ("path", "bytes", "sha256")} for pin in pins if pin["path"] == PDF_REL.as_posix()),
        "source_map": {
            "path": SOURCE_MAP_REL.as_posix(),
            "sha256": next(pin["sha256"] for pin in pins if pin["path"] == SOURCE_MAP_REL.as_posix()),
            "level6_row": source_map,
        },
        "source_catalog": {
            "catalog_workbook_key": entry["workbook_id"],
            "catalog_role": entry["catalog_role"],
            "conversion_status": entry["conversion_status"],
            "stable_identity_status": entry["stable_identity_status"],
            "current_catalog_entries": len(package["workbook_catalog"]["entries"]),
            "current_records": len(package["records"]),
            "level6_canonical_record_count": 0,
            "level6_registry_workbook_entity_count": 0,
        },
        "schema1_contract": {
            "version": "1.0.0-curriculum-candidate",
            "freeze_path": SCHEMA_FREEZE_REL.as_posix(),
            "contract_path": SCHEMA_CONTRACT_REL.as_posix(),
            **contract_identity,
        },
        "pdf_visual_reconciliation": {
            "status": "referenced from P04 r04; not repeated by this schema-field lane",
            "pages": 19,
        },
    }


def validate_non_admission(proposal: dict[str, Any]) -> None:
    require(proposal.get("schema1_importable") is False and proposal.get("admitted") is False and
            proposal.get("runtime_eligible") is False and proposal.get("canonical_schema_validated") is False and
            proposal.get("whole_workbook_complete") is False, "PROPOSAL_AUTHORITY")
    require(proposal.get("canonical_ids_allocated") is False and proposal.get("identity_assignment") == "unassigned",
            "PROPOSAL_IDENTITY")
    records = proposal.get("records", [])
    require(len(records) == 216, "PROPOSAL_RECORD_COUNT")
    event_total = 0
    seen_keys: set[str] = set()
    for record in records:
        require(record.get("status") == "source_mapped_unallocated" and
                record.get("canonical_schema_validated") is False and record.get("runtime_eligible") is False and
                record.get("admitted") is False, "RECORD_AUTHORITY")
        key = record.get("source_local_case_key")
        require(isinstance(key, str) and key.startswith("L006-") and key not in seen_keys, "RECORD_LOCAL_KEY")
        seen_keys.add(key)
        fields = record.get("schema1_fields", {})
        for name in ("id", "workbook_id", "module_id", "content_revision", "lineage"):
            require(name in fields and fields[name] is None, f"RECORD_IDENTITY_{name.upper()}")
        require(fields.get("legacy_level") == 6 and fields.get("kind") == "notation" and
                fields.get("runtime_eligible") is False and fields.get("variants") == [] and
                fields.get("rubric") is None and fields.get("resource_requirements") == [], "RECORD_SCHEMA_FIELDS")
        refs = fields.get("source_refs")
        require(isinstance(refs, list) and len(refs) == 4 and refs == record.get("source_refs"), "RECORD_SOURCE_REFS")
        timing = fields.get("timing", {})
        for name in ("unit", "meter", "fixed_bpm", "note_per_click", "onset_q", "duration_q", "active_grouping"):
            require(name in timing and timing[name] is None, f"RECORD_TIMING_{name.upper()}")
        events = fields.get("events", [])
        require(len(events) == 32 and record.get("source_event_count") == 32, "RECORD_EVENT_COUNT")
        event_total += len(events)
        for event in events:
            require(event.get("event_id") is None and event.get("onset_q") is None and
                    event.get("duration_q") is None, "EVENT_ID_OR_TIMING")
            provenance = event.get("source_local_provenance", {})
            require(provenance.get("source_local_event_key") and
                    provenance["source_local_event_key"].startswith(key + ":"), "EVENT_LOCAL_KEY")
    require(event_total == 6912, "PROPOSAL_EVENT_COUNT")


def build_proposal(root: Path, input_manifest: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    txt = pinned_bytes(root, next(pin for pin in PINS if pin["path"] == TXT_REL.as_posix()))
    source_map = verify_source_map(root)
    package, registry, _generation, freeze, entry, contract_identity = verify_authority(root)
    records = parse_source(txt)
    counts = {"sets": 9, "distinct_codes": 108, "mode_records": 216,
              "source_events": 6912, "events_per_record": 32, "source_refs_per_record": 4}
    proposal = {
        "proposal_version": "level006-unallocated-schema1-fields.1",
        "wbs_id": "2.3.1.1.1",
        "legacy_level": 6,
        "classification": "Build-only, nonimportable schema1 field proposal",
        "target_schema_version": freeze["schema_version"],
        "canonical_ids_allocated": False,
        "identity_assignment": "unassigned",
        "schema1_importable": False,
        "canonical_schema_validated": False,
        "whole_workbook_complete": False,
        "runtime_eligible": False,
        "admitted": False,
        "source_authority": source_authority(root, package, entry, source_map, input_manifest, contract_identity),
        "coverage": counts,
        "source_code_order": [record["pattern_code"] for record in records if record["mode"] == "A"],
        "source_mode_order": ["A", "B"],
        "unresolved_fields": ["canonical workbook/module/item/event/variant IDs", "content revision and lineage",
                              "variant partition", "onset/duration/meter/fixed BPM/note-per-click/active grouping",
                              "canonical schema validation", "Curriculum interpretation and admission"],
        "records": records,
    }
    handoff = {
        "handoff_version": "level006-schema1-allocation-handoff.1",
        "wbs_id": "2.3.1.1.1",
        "legacy_level": 6,
        "catalog_workbook_key": entry["workbook_id"],
        "catalog_key_is_allocated_canonical_identity": False,
        "catalog_role": entry["catalog_role"],
        "source_mapped_records": 216,
        "source_events": 6912,
        "source_mode_records": {"A": 108, "B": 108},
        "canonical_records_created": 0,
        "canonical_ids_allocated": False,
        "content_revision_assigned": False,
        "lineage_assigned": False,
        "variant_ids_allocated": False,
        "event_ids_allocated": False,
        "timing_assigned": False,
        "schema1_importable": False,
        "canonical_schema_validated": False,
        "runtime_eligible": False,
        "imported": False,
        "admitted": False,
        "required_decisions": [
            "Review canonical workbook/module/item/event identities and revision lineage; keep source-local keys separate from canonical IDs.",
            "Decide whether mode, direction, and D/U pick-start options are canonical variants; no partition is proposed here.",
            "Interpret any authored tempo/rhythm timing only from approved source and Curriculum review; no timing is inferred from tab-cell columns.",
            "Obtain source/Curriculum review and canonical schema validation before considering import or runtime admission.",
        ],
        "wbs_parent_status": "Pending",
    }
    validate_non_admission(proposal)
    return proposal, handoff


def check_root(root: Path) -> Path:
    try:
        resolved = root.resolve(strict=True)
        git_root = Path(subprocess.check_output(
            ["git", "-C", str(resolved), "rev-parse", "--show-toplevel"], text=True
        ).strip()).resolve(strict=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ProposalError("--root is not a usable Git checkout") from exc
    require(resolved == git_root, "--root must be the sole Git checkout top level")
    return resolved


def output_directory(root: Path, *, must_be_new: bool) -> Path:
    target = root / OUT_REL
    cursor = root
    for part in OUT_REL.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise ProposalError("symlink in output path")
    resolved = target.resolve(strict=False)
    require(resolved.is_relative_to(root) and resolved != root, "unsafe Build output path")
    if must_be_new and target.exists():
        raise ProposalError("Build output directory already exists; refusing overwrite")
    return target


def rendered_outputs(root: Path) -> dict[str, bytes]:
    input_manifest = verify_all_pins(root)
    proposal_a, handoff = build_proposal(root, input_manifest)
    proposal_b, handoff_b = build_proposal(root, input_manifest)
    proposal_bytes_a = encoded(proposal_a)
    proposal_bytes_b = encoded(proposal_b)
    require(proposal_bytes_a == proposal_bytes_b and encoded(handoff) == encoded(handoff_b), "NONDETERMINISTIC_RENDER")
    manifest = {
        "manifest_version": "level006-schema1-field-proposal-inputs.1",
        "source_generation": "parsed directly from original Level6 TXT; no P04/P06/P11 record arrays used",
        "inputs": input_manifest,
        "reference_roles": "P04/P06/P11 identities are read-only parity controls, never proposal-generation authority.",
        "canonical_admission": False,
    }
    return {
        "field-proposal-a.json": proposal_bytes_a,
        "field-proposal-b.json": proposal_bytes_b,
        "allocation-handoff.json": encoded(handoff),
        "input-manifest.json": encoded(manifest),
    }


def write_new(path: Path, raw: bytes) -> None:
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError as exc:
        raise ProposalError(f"refusing overwrite: {path}") from exc
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        raise


def execute(mode: str, supplied_root: Path) -> None:
    root = check_root(supplied_root)
    out = output_directory(root, must_be_new=(mode == "build"))
    expected = rendered_outputs(root)
    if mode == "build":
        out.mkdir(parents=True, exist_ok=False)
        for name in OUT_NAMES:
            write_new(out / name, expected[name])
    else:
        require(out.is_dir(), "Build output directory missing")
        actual_names = {path.name for path in out.iterdir()}
        require(actual_names == set(OUT_NAMES), "unexpected Build output files")
        for name, expected_bytes in expected.items():
            path = out / name
            require(not path.is_symlink() and path.is_file(), f"unsafe Build output file: {name}")
            require(path.read_bytes() == expected_bytes, f"Build output drift: {name}")
    proposal = json.loads(expected["field-proposal-a.json"])
    print(f"LEVEL6 SCHEMA1 {mode.upper()} PASS records={proposal['coverage']['mode_records']} "
          f"events={proposal['coverage']['source_events']} admitted=false")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("build", "verify"))
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    try:
        execute(args.mode, args.root)
    except (ProposalError, OSError, subprocess.CalledProcessError, KeyError, TypeError) as exc:
        print(f"LEVEL6 SCHEMA1 STOP: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
