#!/usr/bin/env python3
"""Verify pinned Level 6 Sets 1–9 and index their detached records by hash."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BUILD_REL = Path("Build/parallel-06/2.3-level006-batch-integrity-r01")
SPECS = (
    ("Build/parallel-04/2.3.1.1.1-level006-set01-r01/candidate.json", "b763ce846562c6dc8dcd66c0b651a28d28c0963d6b1addf76161140d08c69729", 887662),
    ("Build/parallel-04/2.3.1.1.1-level006-set02-r02/candidate.json", "486216ca6f3e8774e11c8d80e277efc3a128a1fe44ec57a2b16bf80bef392bf2", 887709),
    ("Build/parallel-04/2.3.1.1.1-level006-set03-r01/candidate.json", "aa8d2b0868e08a25b98bda82966e3c4ac37205c73396db3c3f8d252eb7372483", 888185),
    ("Build/parallel-04/2.3.1.1.1-level006-set04-r01/candidate.json", "a689cade24ee25ada4cba16b0a2f700e3518306bcbde49f96f0fb81d040797e5", 888437),
    ("Build/parallel-04/2.3.1.1.1-level006-set05-r01/candidate.json", "7f10d72079b24de7a3366c754b667101de6ad4184b744aa4c555191dc1ba07c6", 888639),
    ("Build/parallel-04/2.3.1.1.1-level006-set06-r01/candidate.json", "32e75668bedbef137cb1b2a25ce362668e1e1b1a6223155fa1b683e687a9bf60", 888563),
    ("Build/parallel-04/2.3.1.1.1-level006-set07-r01/candidate.json", "fc9f0bd8eaad676695600a649aa2bc26d9e78869573ebddcdbeabb11d3c1fa64", 888531),
    ("Build/parallel-04/2.3.1.1.1-level006-set08-r01/candidate.json", "b5676520593dc06ed7cbf119a1aca06c9582efa65cc76e64fd8b797cbb4f2ad6", 888663),
    ("Build/parallel-04/2.3.1.1.1-level006-set09-r02/candidate.json", "aa5b229e07b8ce722389bd4b3cc2892f04c419ab262b9db4ddaa8a220a5407b2", 888618),
)
SOURCE_SPECS = {
    "txt": ("Notes/music/guitar project/TXT version/108_Finger_Permutations_Level_6_Odd_Count_String_Skip_Transfer.txt",
            "bbd337b205eac66e474b7b90dea7c5e18c35fe6f09eec7aee3a058f1c0eb4d19", 126760),
    "pdf": ("Notes/music/guitar project/PDF version/108_Finger_Permutations_Level_6_Odd_Count_String_Skip_Transfer.pdf",
            "a2b97e01ad98bc4e01dfeccfb799b19a5c3c712c233cc9def5e8d95ca16aaac8", 85764),
    "source_map": ("Results/parallel-01/exercises/inventory/20260922T180500Z-2.3-curriculum-v1-source-inventory-evidence/curriculum-source-map.tsv",
                   "f526ff4d9ce3bceaf9a7cc581a3ac2aee2c74917eba984dd57913adba574c123", 68536),
}
MODES = (("A", "3+1 late skip"), ("B", "1+3 early skip"))
TXT_REF = re.compile(r"L6-TXT1-(\d+)-(\d+)$")
PDF_REF = re.compile(r"L6-PDF1-p(\d+)$")


class IntegrityError(ValueError):
    """Pinned source/candidate integrity or admission boundary failed."""


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def read_pinned(root: Path, spec: tuple[str, str, int]) -> bytes:
    relative, digest, size = spec
    path = root / relative
    try:
        resolved = path.resolve(strict=True)
    except FileNotFoundError as exc:
        raise IntegrityError(f"missing pinned input: {relative}") from exc
    if path.is_symlink() or not resolved.is_relative_to(root) or not resolved.is_file():
        raise IntegrityError(f"unsafe pinned input: {relative}")
    raw = path.read_bytes()
    if len(raw) != size or sha(raw) != digest:
        raise IntegrityError(f"pinned input drift: {relative}")
    return raw


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise IntegrityError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def load_candidate(root: Path, set_number: int) -> dict[str, Any]:
    if not 1 <= set_number <= 9:
        raise IntegrityError("Level 6 set number out of range")
    raw = read_pinned(root, SPECS[set_number - 1])
    try:
        value = json.loads(raw, object_pairs_hook=unique_object)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise IntegrityError(f"invalid candidate JSON: set {set_number}") from exc
    if not isinstance(value, dict):
        raise IntegrityError(f"candidate is not an object: set {set_number}")
    return value


def require_unassigned(candidate: dict[str, Any], set_number: int) -> None:
    if candidate.get("wbs_id") != "2.3.1.1.1" or candidate.get("projection_schema") != "schema-v1-curriculum-candidate-projection.1" or candidate.get("target_schema_version") != "1.0.0-curriculum-candidate" or candidate.get("candidate_classification") != "detached_unassigned_non_admitted_source_projection":
        raise IntegrityError(f"candidate authority drift: set {set_number}")
    if candidate.get("canonical_schema_validation") is not False:
        raise IntegrityError(f"false canonical validation: set {set_number}")
    identity = candidate.get("identity_assignment")
    if not isinstance(identity, dict) or identity.get("state") != "unassigned" or identity.get("source_local_keys_are_canonical") is not False or identity.get("stable_identity_fields_emitted") is not False:
        raise IntegrityError(f"false identity allocation: set {set_number}")
    release = candidate.get("release_state")
    if not isinstance(release, dict) or release.get("curriculum_review") != "Pending" or any(release.get(key) is not False for key in ("admitted", "canonical_schema_validated", "curriculum_accepted", "imported", "runtime_eligible", "whole_level_complete", "whole_workbook_complete")):
        raise IntegrityError(f"false admission/release state: set {set_number}")


def require_authority(candidate: dict[str, Any], set_number: int) -> None:
    authority = candidate.get("source_authority")
    if not isinstance(authority, dict):
        raise IntegrityError(f"source authority missing: set {set_number}")
    for kind in SOURCE_SPECS:
        entry = authority.get(kind)
        relative, digest, size = SOURCE_SPECS[kind]
        if not isinstance(entry, dict) or (entry.get("path"), entry.get("sha256"), entry.get("bytes")) != (relative, digest, size):
            raise IntegrityError(f"source authority drift: set {set_number}:{kind}")
    row = authority["source_map"].get("row")
    if not isinstance(row, dict) or row.get("level") != "6" or row.get("wbs_owner") != "2.3.1.1.1" or row.get("review") != "Pending" or any(row.get(key) != "False" for key in ("admitted", "imported", "runtime_eligible", "stable_ids_assigned", "historical_candidate_stable_ids")) or row.get("conversion_status") != "not_converted":
        raise IntegrityError(f"source-map row admission drift: set {set_number}")
    if authority["txt"].get("source_ref") != "L6-TXT1" or authority["pdf"].get("source_ref") != "L6-PDF1" or authority["pdf"].get("instruction_page") != 1 or authority["pdf"].get(f"mode_a_set_{set_number}_figure_page") != 2 * set_number or authority["pdf"].get(f"mode_b_set_{set_number}_figure_page") != 2 * set_number + 1:
        raise IntegrityError(f"source page/ref drift: set {set_number}")


def require_record(record: dict[str, Any], set_number: int, exercise: int, mode: str,
                   lines: list[str]) -> dict[str, Any]:
    mode_name = MODES[0 if mode == "A" else 1][1]
    code = record.get("context", {}).get("pattern_code") if isinstance(record.get("context"), dict) else None
    case_key = f"L006-S{set_number:02d}-MODE-{mode}-EX-{exercise:03d}"
    context = record.get("context")
    if not isinstance(context, dict) or context.get("set_number") != set_number or context.get("exercise_number") != exercise or context.get("movement_mode") != mode_name or context.get("active_grouping_for_this_candidate") is not None or context.get("source_code_order_preserved") is not True or not isinstance(code, str) or not re.fullmatch(r"[1-4]{4}", code):
        raise IntegrityError(f"record code/mode/context drift: {case_key}")
    if record.get("source_local_case_key") != case_key or record.get("legacy_level") != 6 or record.get("kind") != "exercise" or record.get("projection_status") != "detached_source_candidate" or record.get("runtime_eligible") is not False or any(key in record for key in ("id", "workbook_id", "module_id", "content_revision", "lineage")):
        raise IntegrityError(f"record identity/admission drift: {case_key}")
    refs = record.get("source_refs")
    if not isinstance(refs, list) or len(refs) != 4 or refs[2:] != ["L6-TXT1-1-23", "L6-PDF1-p1"]:
        raise IntegrityError(f"record source refs drift: {case_key}")
    txt_match, pdf_match = TXT_REF.fullmatch(refs[0]), PDF_REF.fullmatch(refs[1])
    span = record.get("source_line_range")
    if not txt_match or not pdf_match or not isinstance(span, dict) or (int(txt_match[1]), int(txt_match[2])) != (span.get("start"), span.get("end")) or int(pdf_match[1]) != record.get("source_figure_page") or int(pdf_match[1]) != 2 * set_number + (0 if mode == "A" else 1):
        raise IntegrityError(f"record TXT/PDF locator drift: {case_key}")
    start, end = int(txt_match[1]), int(txt_match[2])
    if not 1 <= start <= end <= len(lines) or f"Exercise {exercise:03d}: {code}" not in lines[start - 1:end]:
        raise IntegrityError(f"record printed code/span drift: {case_key}")
    timing = record.get("timing")
    if not isinstance(timing, dict) or any(timing.get(key) is not None for key in ("cell_beat_count", "duration_q", "meter", "note_per_click", "onset_q", "tempo_bpm")) or not isinstance(timing.get("reason_unassigned"), list) or not timing["reason_unassigned"] or not isinstance(record.get("ambiguities"), list) or not record["ambiguities"]:
        raise IntegrityError(f"invented timing or missing ambiguity: {case_key}")
    groups, events = record.get("directional_groups"), record.get("events")
    if not isinstance(groups, list) or len(groups) != 2 or not isinstance(events, list) or len(events) != 32:
        raise IntegrityError(f"record groups/events count drift: {case_key}")
    all_cell_keys: list[str] = []
    for direction, group in zip(("ascending", "descending"), groups):
        if not isinstance(group, dict) or group.get("direction") != direction or group.get("source_line_ref") != refs[0] or group.get("pdf_figure_page") != int(pdf_match[1]) or group.get("cell_order_is_authored_route_order") is not True:
            raise IntegrityError(f"record direction/source drift: {case_key}:{direction}")
        cells = group.get("cells")
        if not isinstance(cells, list) or len(cells) != 4:
            raise IntegrityError(f"record cell count drift: {case_key}:{direction}")
        for ordinal, cell in enumerate(cells, 1):
            if not isinstance(cell, dict) or cell.get("cell_order_in_direction") != ordinal or cell.get("source_line_ref") != refs[0] or cell.get("pdf_page") != int(pdf_match[1]) or cell.get("silent_intervening_string_is_required_muted") is not True:
                raise IntegrityError(f"record cell source drift: {case_key}:{direction}:{ordinal}")
            keys = cell.get("source_local_event_keys_in_code_order")
            if not isinstance(keys, list) or len(keys) != 4 or len(set(keys)) != 4:
                raise IntegrityError(f"record cell event keys drift: {case_key}:{direction}:{ordinal}")
            all_cell_keys.extend(keys)
    if [event.get("source_local_event_key") if isinstance(event, dict) else None for event in events] != all_cell_keys:
        raise IntegrityError(f"record event order/source keys drift: {case_key}")
    for event in events:
        if any(event.get(key) is not None for key in ("beat_index", "duration_q", "note_per_click", "onset_q")) or any(key in event for key in ("id", "event_id")):
            raise IntegrityError(f"invented event timing/identity: {case_key}")
    return {"set": set_number, "mode": mode, "exercise_number": exercise, "pattern_code": code,
            "source_local_case_key": case_key, "source_refs": refs, "event_count": len(events),
            "record_sha256": sha(canonical(record))}


def build_aggregate(root: Path) -> dict[str, Any]:
    root = root.resolve(strict=True)
    git_root = Path(subprocess.check_output(["git", "-C", str(root), "rev-parse", "--show-toplevel"], text=True).strip()).resolve()
    if root != git_root:
        raise IntegrityError("--root must be the Git checkout top level")
    source_bytes = {kind: read_pinned(root, spec) for kind, spec in SOURCE_SPECS.items()}
    try:
        lines = source_bytes["txt"].decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise IntegrityError("pinned TXT is not UTF-8") from exc
    instruction_context: dict[str, Any] | None = None
    candidates: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    codes: dict[str, list[str]] = {mode: [] for mode, _ in MODES}
    for set_number, (relative, digest, size) in enumerate(SPECS, 1):
        candidate = load_candidate(root, set_number)
        require_unassigned(candidate, set_number)
        require_authority(candidate, set_number)
        scope = candidate.get("candidate_scope")
        expected_exercises = list(range(12 * (set_number - 1) + 1, 12 * set_number + 1))
        if not isinstance(scope, dict) or scope.get("set") != set_number or scope.get("level") != 6 or scope.get("exercise_numbers") != expected_exercises or scope.get("movement_modes") != [f"{letter}: {name}" for letter, name in MODES] or (scope.get("record_projection_count"), scope.get("source_event_count"), scope.get("source_cell_count"), scope.get("directional_group_count")) != (24, 768, 192, 48) or scope.get("whole_level_complete") is not False:
            raise IntegrityError(f"set scope drift: {set_number}")
        context = candidate.get("instruction_context")
        if not isinstance(context, dict) or context.get("source_refs") != ["L6-TXT1-1-23", "L6-PDF1-p1"] or not isinstance(context.get("facts"), list) or not context["facts"] or not isinstance(context.get("unresolved_timing_and_interpretation"), list) or not context["unresolved_timing_and_interpretation"]:
            raise IntegrityError(f"instruction context missing: set {set_number}")
        if instruction_context is None:
            instruction_context = context
        elif context != instruction_context:
            raise IntegrityError(f"instruction context differs across sets: {set_number}")
        source_records = candidate.get("records")
        if not isinstance(source_records, list) or len(source_records) != 24:
            raise IntegrityError(f"record count drift: set {set_number}")
        for mode_index, (mode, _) in enumerate(MODES):
            for offset, exercise in enumerate(expected_exercises):
                index = 12 * mode_index + offset
                record = require_record(source_records[index], set_number, exercise, mode, lines)
                record["candidate_json_pointer"] = f"/records/{index}"
                record["candidate_path"] = relative
                records.append(record)
                codes[mode].append(record["pattern_code"])
        candidates.append({"set": set_number, "path": relative, "bytes": size, "sha256": digest,
                           "record_count": 24, "event_count": 768})
    if len(codes["A"]) != 108 or len(set(codes["A"])) != 108 or codes["A"] != codes["B"]:
        raise IntegrityError("108 source codes do not occur exactly once in both modes")
    for spec in SPECS:
        read_pinned(root, spec)
    for spec in SOURCE_SPECS.values():
        read_pinned(root, spec)
    return {
        "schema": "fathom-level006-detached-batch-integrity.1",
        "classification": "source_bound_preadmission_index",
        "wbs_id": "2.3.1.1.1",
        "source_authority": {kind: {"path": spec[0], "sha256": spec[1], "bytes": spec[2]} for kind, spec in SOURCE_SPECS.items()},
        "instruction_context": instruction_context,
        "candidates": candidates,
        "records": records,
        "codes_in_printed_order": codes["A"],
        "counts": {"sets": 9, "distinct_codes": 108, "modes_per_code": 2, "records": len(records),
                   "events": sum(record["event_count"] for record in records), "source_cells": 1728,
                   "directional_groups": 432},
        "identity_assignment": "unassigned",
        "timing": "unassigned; printed ASCII columns are not beats or note-per-click",
        "runtime_eligible": False,
        "admitted": False,
        "validator_ready": False,
        "required_decisions": ["Reviewed stable identities, source-to-schema admission, timing and Curriculum acceptance remain Pending."],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        root = args.root.resolve(strict=True)
        output = args.output if args.output.is_absolute() else root / args.output
        if (root / BUILD_REL).resolve() not in output.resolve(strict=False).parents:
            raise IntegrityError("output must stay in the P06 Level6 Build lane")
        aggregate = build_aggregate(root)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes((json.dumps(aggregate, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8"))
    except (IntegrityError, FileNotFoundError, subprocess.CalledProcessError) as exc:
        print(f"LEVEL6 INDEX STOP: {exc}", file=sys.stderr)
        return 2
    print(f"INDEX PASS {output} records={aggregate['counts']['records']} events={aggregate['counts']['events']} admitted=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
