#!/usr/bin/env python3
"""Materialize pinned Level 6 source projections as a non-admitted schema draft."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any

from Tools import curriculum_level006_batch_adapter_candidate as integrity


ROOT = Path(__file__).resolve().parents[1]
BUILD_REL = Path("Build/parallel-11/2.3-level006-draft-materializer-r01")
INDEX = ("Build/parallel-06/2.3-level006-batch-integrity-r01/index-a.json",
         "ce16f26098ce583288b1a98ff2fcca3b09b50286f4e4feeea5feace6bd07479d", 126514)
ADAPTER = ("Tools/curriculum_level006_batch_adapter_candidate.py",
           "102becd2ccf0c864d067ed8923b4abf0702d487226f09727a71ec878d1526f08", 17727)
COUNTS = {"sets": 9, "distinct_codes": 108, "modes_per_code": 2, "records": 216,
          "events": 6912, "source_cells": 1728, "directional_groups": 432}
UNRESOLVED = ("workbook_id", "module_id", "item_id", "variant_ids", "event_ids",
              "cell_beat_count", "duration_q", "meter", "note_per_click", "onset_q", "tempo_bpm",
              "source_to_schema_admission", "curriculum_interpretation")


class DraftError(ValueError):
    """Pinned source, index or non-admission contract is inconsistent."""


def canonical(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def pinned(root: Path, spec: tuple[str, str, int]) -> bytes:
    path, expected_hash, expected_size = spec
    target = root / path
    try:
        resolved = target.resolve(strict=True)
    except FileNotFoundError as exc:
        raise DraftError(f"missing pinned input: {path}") from exc
    if target.is_symlink() or not resolved.is_relative_to(root) or not resolved.is_file():
        raise DraftError(f"unsafe pinned input: {path}")
    raw = target.read_bytes()
    if len(raw) != expected_size or digest(raw) != expected_hash:
        raise DraftError(f"pinned input drift: {path}")
    return raw


def load_inputs(root: Path) -> tuple[dict[str, Any], dict[int, dict[str, Any]], list[str]]:
    pinned(root, ADAPTER)
    raw = pinned(root, INDEX)
    try:
        index = json.loads(raw, object_pairs_hook=integrity.unique_object)
    except (UnicodeDecodeError, json.JSONDecodeError, integrity.IntegrityError) as exc:
        raise DraftError("invalid pinned P06 index JSON") from exc
    if not isinstance(index, dict) or index != integrity.build_aggregate(root):
        raise DraftError("P06 index differs from the nine validated source candidates")
    if index.get("counts") != COUNTS or any(index.get(key) is not False for key in ("admitted", "runtime_eligible", "validator_ready")):
        raise DraftError("P06 index counts or non-admission state drift")
    candidates = {number: integrity.load_candidate(root, number) for number in range(1, 10)}
    lines = pinned(root, integrity.SOURCE_SPECS["txt"]).decode("utf-8").splitlines()
    return index, candidates, lines


def materialize(index: dict[str, Any], candidates: dict[int, dict[str, Any]],
                lines: list[str]) -> dict[str, Any]:
    if index.get("counts") != COUNTS or len(index.get("records", [])) != 216 or set(candidates) != set(range(1, 10)):
        raise DraftError("whole-Level6 index/candidate count conflict")
    if any(index.get(key) is not False for key in ("admitted", "runtime_eligible", "validator_ready")) or index.get("identity_assignment") != "unassigned":
        raise DraftError("false index admission or identity state")
    indexed_candidates = index.get("candidates")
    if not isinstance(indexed_candidates, list) or len(indexed_candidates) != 9:
        raise DraftError("candidate index conflict")
    for number, row in enumerate(indexed_candidates, 1):
        if not isinstance(row, dict) or row != {"set": number, "path": integrity.SPECS[number - 1][0],
                                               "bytes": integrity.SPECS[number - 1][2],
                                               "sha256": integrity.SPECS[number - 1][1],
                                               "record_count": 24, "event_count": 768}:
            raise DraftError(f"candidate path/hash/count conflict: set {number}")
        integrity.require_unassigned(candidates[number], number)
        integrity.require_authority(candidates[number], number)
    if any(candidates[number]["instruction_context"] != index["instruction_context"] for number in candidates):
        raise DraftError("instruction context conflict")

    drafts: list[dict[str, Any]] = []
    seen_keys: set[str] = set()
    event_count = cell_count = group_count = 0
    for ref in index["records"]:
        if not isinstance(ref, dict):
            raise DraftError("invalid record index row")
        number, mode, exercise = ref.get("set"), ref.get("mode"), ref.get("exercise_number")
        if not isinstance(number, int) or number not in candidates or mode not in ("A", "B") or not isinstance(exercise, int):
            raise DraftError("record index key conflict")
        pointer = ref.get("candidate_json_pointer")
        offset = 12 * (mode == "B") + exercise - (number - 1) * 12 - 1
        if pointer != f"/records/{offset}" or not 0 <= offset < 24:
            raise DraftError("record JSON pointer/order conflict")
        source = candidates[number]["records"][offset]
        validated = integrity.require_record(source, number, exercise, mode, lines)
        validated["candidate_json_pointer"] = pointer
        validated["candidate_path"] = integrity.SPECS[number - 1][0]
        if validated != ref:
            raise DraftError(f"record hash/ref/code conflict: {ref.get('source_local_case_key')}")
        key = source["source_local_case_key"]
        if key in seen_keys:
            raise DraftError(f"duplicate source-local record key: {key}")
        seen_keys.add(key)
        if any(source["timing"].get(field) is not None for field in
               ("cell_beat_count", "duration_q", "meter", "note_per_click", "onset_q", "tempo_bpm")):
            raise DraftError(f"invented record timing: {key}")
        event_count += len(source["events"])
        group_count += len(source["directional_groups"])
        cell_count += sum(len(group["cells"]) for group in source["directional_groups"])
        drafts.append({
            "source_local_case_key": key,
            "source_record_sha256": ref["record_sha256"],
            "source_locator": {"candidate_path": ref["candidate_path"], "json_pointer": pointer,
                               "source_refs": copy.deepcopy(ref["source_refs"])},
            "schema_slots": {field: None for field in UNRESOLVED},
            "source_projection": copy.deepcopy(source),
            "canonical_schema_validated": False,
            "runtime_eligible": False,
            "admitted": False,
        })
    if (len(drafts), event_count, cell_count, group_count) != (216, 6912, 1728, 432):
        raise DraftError("materialized record/event/cell/group count conflict")
    return {
        "schema": "fathom-level006-schema-oriented-draft.1",
        "classification": "detached_source_bound_non_admitted_draft",
        "wbs_id": "2.3.1.1.1",
        "target_schema_version": "1.0.0-curriculum-candidate",
        "canonical_schema_validated": False,
        "runtime_eligible": False,
        "admitted": False,
        "identity_assignment": "unassigned",
        "p06_index": {"path": INDEX[0], "sha256": INDEX[1], "bytes": INDEX[2]},
        "source_authority": copy.deepcopy(index["source_authority"]),
        "instruction_context": copy.deepcopy(index["instruction_context"]),
        "candidate_inputs": copy.deepcopy(indexed_candidates),
        "counts": copy.deepcopy(COUNTS),
        "unresolved_schema_fields": list(UNRESOLVED),
        "required_decisions": ["Review and allocate stable workbook/module/item/variant/event identities and lineage.",
                               "Interpret printed rhythm, beat/note-per-click and tempo without inference.",
                               "Validate canonical schema and obtain Curriculum approval before admission."],
        "records": drafts,
    }


def render(root: Path) -> bytes:
    root = root.resolve(strict=True)
    git_root = Path(subprocess.check_output(["git", "-C", str(root), "rev-parse", "--show-toplevel"], text=True).strip()).resolve()
    if root != git_root:
        raise DraftError("--root must be the sole Git checkout top level")
    return canonical(materialize(*load_inputs(root)))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        root = args.root.resolve(strict=True)
        output = args.output if args.output.is_absolute() else root / args.output
        build = (root / BUILD_REL).resolve(strict=False)
        if output.resolve(strict=False) == build or build not in output.resolve(strict=False).parents or output.exists() or output.is_symlink():
            raise DraftError("output must be a new file inside the P11 Level6 Build lane")
        raw = render(root)
        output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=output.parent, prefix="draft-", suffix=".tmp", delete=False) as stream:
            temp = Path(stream.name)
            try:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            except BaseException:
                temp.unlink(missing_ok=True)
                raise
        try:
            os.link(temp, output)  # Exclusive publication: never replace an earlier draft.
        finally:
            temp.unlink(missing_ok=True)
    except (DraftError, integrity.IntegrityError, OSError, subprocess.CalledProcessError) as exc:
        print(f"LEVEL6 DRAFT STOP: {exc}", file=sys.stderr)
        return 2
    print(f"DRAFT PASS {output} records=216 events=6912 admitted=false sha256={digest(raw)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
