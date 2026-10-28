#!/usr/bin/env python3
"""Project sealed Level24 rolling rungs into detached unallocated schema1 fields."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from curriculum_level024_whole_candidate import build_candidate


ROOT = Path(__file__).resolve().parents[1]
OUT_REL = Path("Build/parallel-06/level024-schema1-unallocated-r01")
INPUTS = {
    "Build/parallel-09/2.3.1.1.1-level024-whole-r01/candidate-01.json": "16159d81cb657d3d05744121225f22fd3e9f542ee93df60c1d107ad94e1cc804",
    "Tools/curriculum_level024_whole_candidate.py": "cc9d57c9a2a1725558c86bd1b18ff564f0c8c800b8ae9ac3f55bec1bd994c2b8",
    "Content/controls/curriculum-v1/package.json": "766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255",
    "Content/controls/curriculum-v1/identity-registry.json": "5d265859e1e8a5a530a0e53d88b019a1c920f3bba6cccb4ef0fef2f7640007e5",
    "Results/primary/20260912T100538Z-2.1.1.2.1-r02-evidence/schema-freeze.json": "0659fa962a5c933a2bcf3045772b6fe5b05b4deefb3511f5dcb68af51088de95",
}
KEYS = ("A", "Bb", "B", "C", "C#", "D", "Eb", "E", "F", "F#", "G", "G#", "A")
DEGREES = ("1", "2", "b3", "4", "5", "b6", "b7", "8", "9", "b10", "11", "12", "b13", "b14", "15")
OPEN = {"E": (1, 40), "A": (2, 45), "D": (3, 50), "G": (4, 55),
        "B": (5, 59), "e": (6, 64)}
PC = {"C": 0, "B#": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3,
      "Eb": 3, "E": 4, "Fb": 4, "F": 5, "F#": 6, "Gb": 6,
      "G": 7, "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10,
      "B": 11, "Cb": 11}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def encoded(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False,
                       separators=(",", ":")) + "\n").encode()


def read_inputs(root: Path) -> tuple[dict, dict, dict]:
    raw = {}
    for rel, expected in INPUTS.items():
        path = root / rel
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"missing or symlink input: {rel}")
        data = path.read_bytes()
        if digest(data) != expected:
            raise ValueError(f"input drift: {rel}")
        raw[rel] = data
    candidate = json.loads(raw[next(iter(INPUTS))])
    if candidate != build_candidate():
        raise ValueError("sealed candidate differs from original TXT/PDF replay")
    package = json.loads(raw[list(INPUTS)[2]])
    registry = json.loads(raw[list(INPUTS)[3]])
    freeze = json.loads(raw[list(INPUTS)[4]])
    if freeze.get("decision") != "Technical schema1 FROZEN" or freeze.get("schema_version") != "1.0.0-curriculum-candidate":
        raise ValueError("schema freeze drift")
    return candidate, package, registry


def identity_boundary(package: dict, registry: dict) -> dict:
    wid = "fg:workbook:000024"
    if any(r.get("legacy_level") == 24 or r.get("workbook_id") == wid
           for r in package["records"]):
        raise ValueError("unexpected canonical Level24 record")
    if any(e.get("id") == wid for e in registry["entities"]):
        raise ValueError("unexpected Level24 registry entity")
    entries = [e for e in package["workbook_catalog"]["entries"]
               if e.get("workbook_id") == wid]
    if len(entries) != 1:
        raise ValueError("Level24 catalog identity drift")
    entry = entries[0]
    if (entry.get("conversion_status") != "not_converted"
            or entry.get("whole_workbook_complete") is not False
            or entry.get("admitted") is not False
            or entry.get("runtime_eligible") is not False
            or entry.get("representative_item_id") is not None):
        raise ValueError("Level24 source-only catalog drift")
    return entry


def event(note: dict, record: dict) -> dict:
    if note["onset_q"] is not None or note["duration_q"] is not None:
        raise ValueError("source note timing drift")
    position, string, fret = note["position"], note["string"], note["fret"]
    if not 1 <= position <= 15 or string not in OPEN or type(fret) is not int or fret < 0:
        raise ValueError("source note position/TAB drift")
    spelling = record["scale_tones"][position - 1]
    string_number, base = OPEN[string]
    midi = base + fret
    if spelling not in PC or midi % 12 != PC[spelling]:
        raise ValueError("source note/TAB pitch mismatch")
    if note["altered_degree"] != DEGREES[position - 1] or note["finger_digit"] not in "1234":
        raise ValueError("source degree/finger drift")
    return {
        "source_note": note, "source_spelling": spelling,
        "source_key": record["source_local_key"],
        "source_refs": record["source_refs"], "performed_result": None,
        "schema1_fields": {
            "event_id": None, "kind": "note", "attack": None,
            "spelling": spelling, "midi": midi, "string": string_number,
            "fret": fret, "finger": int(note["finger_digit"]),
            "degree_contexts": {}, "onset_q": None, "duration_q": None,
            "tie_from": None,
        },
    }


def project(candidate: dict, package: dict, registry: dict) -> tuple[dict, dict]:
    catalog = identity_boundary(package, registry)
    if (candidate.get("schema") != "fathom-level024-whole-detached-candidate-v1"
            or candidate.get("wbs_id") != "2.3.1.1.1"
            or candidate.get("level") != 24
            or candidate.get("whole_source_batch_structurally_reconciled") is not True
            or candidate.get("exceptions") != []
            or len(candidate.get("records", [])) != 13):
        raise ValueError("whole Level24 source scope drift")
    for key in ("admitted", "imported", "runtime_eligible", "runtime_admitted"):
        if candidate.get(key) is not False:
            raise ValueError(f"source admission drift: {key}")
    route = candidate["neck_route"]
    expected_sequence = list(range(1, 14)) + list(range(12, 0, -1))
    if (route["single_turn_cell_sequence"] != expected_sequence
            or route["single_turn_cell_count"] != 25
            or route["notes_per_cell"] != 78
            or route["single_turn_note_count"] != 1950
            or route["turn_rung_played_once"] != 13):
        raise ValueError("25-cell route/count drift")
    records = []
    group_total = event_total = 0
    for ordinal, source in enumerate(candidate["records"], 1):
        if (source["rung"] != ordinal or source["key"] != KEYS[ordinal - 1]
                or source["root_fret"] != ordinal + 4
                or source["frame"] != [ordinal + 3, ordinal + 7]
                or source["position_degree_map"] != list(DEGREES)
                or len(source["scale_tones"]) != 15
                or len(source["groups"]) != 26):
            raise ValueError("rung source scope drift")
        for key in ("admitted", "imported", "runtime_eligible", "runtime_admitted"):
            if source.get(key) is not False:
                raise ValueError("rung source admission drift")
        for key in ("canonical_item_id", "canonical_variant_id", "fixed_bpm", "note_per_click", "onset_q", "duration_q"):
            if source.get(key) is not None:
                raise ValueError("rung source identity/timing drift")
        events = []
        group_refs = []
        for group_no, group in enumerate(source["groups"], 1):
            if group["ordinal"] != group_no or len(group["notes"]) != 3:
                raise ValueError("rolling group order/count drift")
            start = len(events) + 1
            for note in group["notes"]:
                if (note["ordinal"] != len(events) + 1
                        or note["group"] != (group_no - 1) % 13 + 1
                        or note["half"] != group["half"]
                        or note["string"] != group["string_pattern"][note["slot"] - 1]):
                    raise ValueError("rolling note/group provenance drift")
                events.append(event(note, source))
            group_refs.append({"source_group": group,
                               "source_event_ordinals": list(range(start, len(events) + 1))})
        if (len(events) != 78 or [e["source_note"]["is_high_root_turn"] for e in events].count(True) != 2
                or not all(events[i]["source_note"]["is_high_root_turn"] for i in (38, 39))):
            raise ValueError("rung event/high-root-turn drift")
        group_total += len(group_refs)
        event_total += len(events)
        records.append({
            "source_component": f"rung-{ordinal:02d}", "identity_state": "unallocated",
            "source_rung": {k: v for k, v in source.items() if k != "groups"},
            "source_groups": group_refs,
            "schema1_fields": {
                "id": None, "workbook_id": None, "module_id": None,
                "legacy_level": 24, "title": source["printed_txt"]["heading"],
                "kind": "note_sequence", "content_revision": None, "lineage": None,
                "runtime_eligible": False, "source_refs": None,
                "events": events,
                "variants": [{"id": None, "source_rung": ordinal,
                              "source_event_ordinals": list(range(1, 79)),
                              "event_ids": None, "runtime_eligible": False}],
                "resource_requirements": [],
                "timing": {"status": "unresolved", "unit": "quarter", "fixed_bpm": None},
                "ambiguities": ["canonical identities and lineage unallocated",
                                "quarter-note onset/duration and fixed BPM unresolved",
                                "printed picking and route guidance are not performed results"],
            },
        })
    if group_total != 338 or event_total != 1014:
        raise ValueError("whole rolling group/event parity drift")
    proposal = {
        "proposal_version": "level024-unallocated-schema1-fields.1", "wbs_id": "2.3.1.1.1",
        "classification": "Build-only, nonimportable schema1 field proposal",
        "legacy_level": 24, "canonical_ids_allocated": False,
        "schema1_importable": False, "whole_workbook_complete": False,
        "runtime_eligible": False, "admitted": False,
        "counts": {"provisional_rung_records": 13, "rolling_triplet_groups": 338,
                   "rung_note_contacts": 1014, "route_cells": 25,
                   "route_source_described_contacts": 1950,
                   "route_new_unique_note_events": 0},
        "source": candidate["source"], "source_catalog_level": catalog,
        "instructions": candidate["instructions"],
        "pdf_route_map": candidate["pdf_route_map"],
        "neck_route": route,
        "route_application": [{"route_cell": i, "source_rung": rung,
                               "source_event_ordinals": list(range(1, 79))}
                              for i, rung in enumerate(expected_sequence, 1)],
        "records": records,
    }
    handoff = {
        "handoff_version": "level024-allocation-handoff.1", "wbs_id": "2.3.1.1.1",
        "catalog_workbook_id": catalog["workbook_id"],
        "existing_level024_records": 0, "existing_level024_workbook_entities": 0,
        "rung_records": 13, "rolling_triplet_groups": 338,
        "rung_note_contacts": 1014, "route_cells": 25,
        "route_source_described_contacts": 1950,
        "canonical_ids_allocated": False, "admitted": False,
        "required_decisions": [
            "Allocate stable workbook/module/item/event/variant identities and revision lineage.",
            "Decide route reuse and occurrence identity for 25 cells without creating extra authored rung notes.",
            "Resolve onset/duration, fixed BPM, picking variants and Practice semantics before native import.",
            "Complete musical correctness and Curriculum review of all 13 rungs and the route.",
        ],
    }
    return proposal, handoff


def products(root: Path) -> dict[str, object]:
    candidate, package, registry = read_inputs(root)
    proposal, handoff = project(candidate, package, registry)
    manifest = {"manifest_version": "level024-input-pins.1", "inputs": [
        {"path": rel, "bytes": (root / rel).stat().st_size, "sha256": sha}
        for rel, sha in INPUTS.items()]}
    summary = {"summary_version": "level024-schema1-unallocated-summary.1",
               "proposal_sha256": digest(encoded(proposal)),
               "handoff_sha256": digest(encoded(handoff)),
               "rung_records": 13, "rolling_triplet_groups": 338,
               "rung_note_contacts": 1014, "route_cells": 25,
               "route_source_described_contacts": 1950,
               "native_run": False, "runtime_eligible": False, "admitted": False}
    return {"field-proposal.json": proposal, "allocation-handoff.json": handoff,
            "input-manifest.json": manifest, "summary.json": summary}


def run(mode: str, root: Path) -> None:
    git_root = Path(subprocess.run(["git", "rev-parse", "--show-toplevel"],
                                   cwd=root, capture_output=True, text=True,
                                   check=True).stdout.strip()).resolve(strict=True)
    if root != git_root:
        raise ValueError("root must equal Git top level")
    built = products(root)
    out = root
    for part in OUT_REL.parts:
        out /= part
        if out.is_symlink():
            raise ValueError("output symlink path")
    if mode == "build":
        if out.exists():
            raise ValueError("output already exists")
        out.mkdir(parents=True)
        for name, value in built.items():
            with (out / name).open("xb") as f:
                f.write(encoded(value))
    else:
        contents = {p.name for p in out.iterdir()}
        if contents not in (set(built), set(built) | {"focused-tests.log"}):
            raise ValueError("output file set drift")
        if "focused-tests.log" in contents and (out / "focused-tests.log").is_symlink():
            raise ValueError("output test log symlink")
        for name, value in built.items():
            path = out / name
            if path.is_symlink() or path.read_bytes() != encoded(value):
                raise ValueError(f"output drift: {name}")
    print("LEVEL24 " + mode.upper() + " PASS rungs=13 groups=338 contacts=1014 route=1950 admitted=false")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("mode", choices=("build", "verify"))
    ap.add_argument("--root", type=Path, default=ROOT)
    args = ap.parse_args()
    run(args.mode, args.root.resolve(strict=True))


if __name__ == "__main__":
    main()
