#!/usr/bin/env python3
"""Project sealed Level28 triad ladder into detached unallocated schema1 fields."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = Path("Build/parallel-07/2.3.1.1.1-level028-schema1-unallocated-r01")
STEM = "Scale_Exercises_Section_III_Level_28_Natural_Minor_Diatonic_Triads_Two_Octave_Six_String_Neck_Ladder"
TXT = f"Notes/music/guitar project/TXT version/{STEM}.txt"
PDF = f"Notes/music/guitar project/PDF version/{STEM}.pdf"
WHOLE = "Build/parallel-12/2.3.1.1.1-level028-whole-triad-ladder-r01/candidate-02.json"
MAP = "Results/parallel-01/exercises/inventory/20260922T180500Z-2.3-curriculum-v1-source-inventory-evidence/curriculum-source-map.json"
PACKAGE = "Content/controls/curriculum-v1/package.json"
REGISTRY = "Content/controls/curriculum-v1/identity-registry.json"
GENERATION = "Content/controls/curriculum-v1/generation.json"
INPUTS = {
    WHOLE: "928709755e903407a723540499e2a7a04da79da339907c94d98d37aba7b98aca",
    TXT: "2f745bc5000d27f032fd1187fee245e387bfd1bf7b0f132782ebb7a72aafac1b",
    PDF: "779c1b2da3cad5046af51013dc4a72053b7cd5dd0a211caa27352bfa93076219",
    MAP: "bad5581a04f43ba8baf14db430449e1ccff5cf88f0f7e42198328073b27053d6",
    PACKAGE: "766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255",
    REGISTRY: "5d265859e1e8a5a530a0e53d88b019a1c920f3bba6cccb4ef0fef2f7640007e5",
    GENERATION: "fc6cec9f9d67eb82c97c5f4c3fb95d285178fb7fce7bd147d9ae0296d21b4c1c",
}
KEYS = ("A", "Bb", "B", "C", "C#", "D", "Eb", "E", "F", "F#", "G", "G#", "A")
STRINGS_HIGH_TO_LOW = ("e", "B", "G", "D", "A", "E")
OPEN_PC = {"E": 4, "A": 9, "D": 2, "G": 7, "B": 11, "e": 4}
NATURAL_PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
UNRESOLVED = [
    "Canonical workbook/module/item/event/variant IDs, content revision and lineage are unallocated.",
    "Exact quarter-note onset/duration, fixed BPM, note-per-click, audio and performed result remain unresolved.",
    "The 25-cell round trip reuses 13 authored rungs; its 1,650 contacts are route occurrences, not 1,650 new unique contacts.",
    "Chord spelling, TAB fret/string and printed finger/degree are source facts; sounding MIDI register remains unassigned.",
]


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def encoded(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def pitch_class(spelling: str) -> int:
    if not re.fullmatch(r"[A-G](?:b|#)?", spelling):
        raise ValueError("source pitch spelling drift")
    return (NATURAL_PC[spelling[0]] + (1 if spelling.endswith("#") else -1 if spelling.endswith("b") else 0)) % 12


def read_inputs(root: Path) -> dict:
    raw = {}
    for rel, expected in INPUTS.items():
        data = (root / rel).read_bytes()
        if sha(data) != expected:
            raise ValueError(f"input drift: {rel}")
        raw[rel] = data
    parsed = {rel: json.loads(raw[rel]) for rel in (WHOLE, MAP, PACKAGE, REGISTRY, GENERATION)}
    parsed[TXT] = raw[TXT].decode("utf-8").splitlines()
    return parsed


def identity_boundary(data: dict) -> dict:
    foundation, registry, generation = data[PACKAGE], data[REGISTRY], data[GENERATION]
    workbook = "fg:workbook:000028"
    if len(foundation["records"]) != 659 or generation["records"] != 659:
        raise ValueError("current659 foundation drift")
    if any(r.get("legacy_level") == 28 or r.get("workbook_id") == workbook for r in foundation["records"]):
        raise ValueError("Level28 canonical record already exists")
    if any(e.get("id") == workbook for e in registry["entities"]):
        raise ValueError("Level28 workbook registry entity already exists")
    entry = next((x for x in foundation["workbook_catalog"]["entries"] if x.get("workbook_id") == workbook), None)
    if (not entry or entry.get("catalog_role") != "read_only_source_preservation"
        or entry.get("conversion_status") != "not_converted" or entry.get("review") != "Pending"
        or entry.get("representative_item_id") is not None
        or any(entry.get(k) is not False for k in ("runtime_eligible", "runtime_admitted", "imported", "admitted", "whole_workbook_complete"))):
        raise ValueError("Level28 source-only catalog boundary drift")
    return entry


def validate_source(candidate: dict, source_map: dict, lines: list[str]) -> None:
    if (candidate.get("schema") != "fathom-level028-whole-detached-triad-candidate-v1"
        or candidate.get("level") != 28 or candidate.get("wbs_id") != "2.3.1.1.1"
        or candidate.get("classification") != "noncanonical_nonadmitted_source_candidate"
        or candidate.get("source_discrepancies") != [] or candidate.get("exceptions") != []):
        raise ValueError("whole Level28 candidate scope/conflict drift")
    for field in ("canonical_item_id", "canonical_variant_id", "fixed_bpm", "note_per_click", "onset_q", "duration_q"):
        if candidate.get(field) is not None:
            raise ValueError("whole Level28 candidate invented identity/timing")
    for field in ("runtime_eligible", "runtime_admitted", "imported", "admitted", "whole_workbook_complete"):
        if candidate.get(field) is not False:
            raise ValueError("whole Level28 candidate authority drift")
    source = candidate["source"]
    if (source["txt_path"] != TXT or source["txt_sha256"] != INPUTS[TXT]
        or source["pdf_path"] != PDF or source["pdf_sha256"] != INPUTS[PDF]
        or source["pdf_pages"] != 10 or source["card_pdf_pages"] != list(range(3, 10))
        or len(lines) != 487):
        raise ValueError("Level28 original source identity drift")
    counts = {"contacts_per_cell": 66, "round_trip_cells": 25, "round_trip_contacts": 1650,
              "rungs": 13, "triads_per_cell": 22, "unique_contacts": 858, "unique_triads": 286}
    if candidate["counts"] != counts or len(candidate["rungs"]) != 13 or len(candidate["full_round_trip_route"]) != 25:
        raise ValueError("Level28 source workload/route count drift")
    guidance = candidate["source_guidance"]
    if (guidance.get("practice_is_timing_authority") is not False
        or guidance.get("static_five_fret_stretch_inferred") is not False
        or not guidance.get("picking_source") or not guidance.get("rhythm_source")):
        raise ValueError("Level28 source guidance/semantic boundary drift")
    row = next((r for r in source_map["rows"] if r.get("level") == 28), None)
    if (row is None or row.get("txt_sha256") != INPUTS[TXT] or row.get("pdf_sha256") != INPUTS[PDF]
        or row.get("conversion_status") != "not_converted" or row.get("representative_item_id") is not None
        or any(row.get(k) is not False for k in ("stable_ids_assigned", "runtime_eligible", "imported", "admitted"))):
        raise ValueError("Level28 frozen source-map boundary drift")


def validate_rows(rung: dict, lines: list[str], index: int) -> None:
    start = 104 + 27 * index
    end = start + 24
    refs = rung["source_refs"]
    if (refs["txt"] != f"L28-TXT1-{start}-{end}"
        or f"-p{3 + index // 2}-" not in refs["pdf"]
        or refs["pdf_overview"] != "L28-PDF1-p2"):
        raise ValueError("rung exact TXT/PDF source ref drift")
    block = lines[start - 1:end]
    if len(block) != 25:
        raise ValueError("rung TXT span drift")
    for direction in ("ascending", "descending"):
        rows = rung["source_rows"][direction]
        if len(rows) != 9 or sum(block[i:i + 9] == rows for i in range(len(block) - 8)) != 1:
            raise ValueError("rung source rows not pinned to TXT")


def validate_triad(triad: dict, rung: dict, triad_ordinal: int) -> None:
    direction = "ascending" if triad_ordinal <= 11 else "descending"
    expected_direction_ordinal = triad_ordinal if triad_ordinal <= 11 else triad_ordinal - 11
    if (triad["triad_ordinal"] != triad_ordinal or triad["direction"] != direction
        or triad["direction_triad_ordinal"] != expected_direction_ordinal
        or len(triad["contacts"]) != 3 or len(triad["source_cells"]["tab_high_to_low"]) != 6):
        raise ValueError("triad source order/shape drift")
    source_cells = triad["source_cells"]
    if any(len(row) != 12 for row in source_cells["tab_high_to_low"]):
        raise ValueError("triad TAB cell width drift")
    if "".join(x["string"] for x in triad["contacts"]) != triad["string_path"]:
        raise ValueError("triad printed string path drift")
    parsed_contacts = []
    for string, row in zip(STRINGS_HIGH_TO_LOW, source_cells["tab_high_to_low"]):
        for match in re.finditer(r"\d+", row):
            parsed_contacts.append((match.start(), string, int(match.group())))
    parsed_contacts.sort(key=lambda value: value[0])
    if len(parsed_contacts) != 3 or [x[0] for x in parsed_contacts] != [0, 4, 8]:
        raise ValueError("triad TAB column geometry drift")
    for i, contact in enumerate(triad["contacts"], 1):
        if (contact["contact_ordinal"] != i or contact["ordinal"] != (triad_ordinal - 1) * 3 + i
            or (contact["string"], contact["fret"]) != parsed_contacts[i - 1][1:]
            or not 0 <= contact["fret"] <= 24 or not 1 <= contact["finger_digit"] <= 4):
            raise ValueError("triad contact order/TAB/finger drift")
        offset = (i - 1) * 4
        degree_cell = source_cells["degrees"][offset:offset + 4].strip("-")
        finger_cell = source_cells["fingers"][offset:offset + 4].strip("-")
        if degree_cell != contact["degree"] or finger_cell != str(contact["finger_digit"]):
            raise ValueError("triad degree/finger source-cell drift")
        if pitch_class(contact["pitch_spelling"]) != (OPEN_PC[contact["string"]] + contact["fret"]) % 12:
            raise ValueError("triad pitch spelling/TAB geometry drift")
        if contact["onset_q"] is not None or contact["duration_q"] is not None:
            raise ValueError("triad invented contact timing")


def contact_field(contact: dict, triad: dict, rung: dict) -> dict:
    return {"source_rung": rung["rung"], "source_triad_ordinal": triad["triad_ordinal"],
            "source_contact": contact, "source_chord": {"name": triad["chord_name"],
                "quality": triad["chord_quality"], "harmonic_function": triad["harmonic_function"],
                "direction": triad["direction"], "string_path": triad["string_path"],
                "source_cells": triad["source_cells"]},
            "source_refs": rung["source_refs"],
            "source_tone": {"printed_pitch_spelling": contact["pitch_spelling"],
                            "printed_degree": contact["degree"], "printed_string": contact["string"],
                            "printed_fret": contact["fret"], "printed_finger": contact["finger_digit"],
                            "sounding_midi": None},
            "schema1_fields": {"event_id": None, "kind": "contact", "contact": "pitched",
                               "pick": None, "pitch_binding": None, "onset_q": None, "duration_q": None}}


def project(data: dict) -> tuple[dict, dict]:
    candidate, lines = data[WHOLE], data[TXT]
    entry = identity_boundary(data)
    validate_source(candidate, data[MAP], lines)
    records = []
    unique_triads = 0
    unique_contacts = 0
    for index, rung in enumerate(candidate["rungs"]):
        expected_root = 5 + index
        if (rung["rung"] != index + 1 or rung["key"] != KEYS[index]
            or rung["root_fret"] != expected_root or rung["root_string"] != "E"
            or (rung["frame_min_fret"], rung["frame_max_fret"]) != (expected_root - 1, expected_root + 3)
            or len(rung["triads"]) != 22 or len(rung["diatonic_triad_names"]) != 7
            or len(rung["scale_tones_two_octaves"]) != 15):
            raise ValueError("rung key/root/frame/triad count drift")
        if (any(rung[k] is not None for k in ("canonical_item_id", "canonical_variant_id", "fixed_bpm",
                                                 "note_per_click", "onset_q", "duration_q"))
            or any(rung[k] is not False for k in ("runtime_eligible", "runtime_admitted", "imported", "admitted"))):
            raise ValueError("rung invented authority/timing")
        validate_rows(rung, lines, index)
        events = []
        variants = []
        for ordinal, triad in enumerate(rung["triads"], 1):
            validate_triad(triad, rung, ordinal)
            start = len(events) + 1
            events.extend(contact_field(c, triad, rung) for c in triad["contacts"])
            variants.append({"id": None, "source_triad_ordinal": ordinal,
                             "source_chord_name": triad["chord_name"],
                             "source_chord_quality": triad["chord_quality"],
                             "source_harmonic_function": triad["harmonic_function"],
                             "source_direction": triad["direction"],
                             "source_event_ordinals": list(range(start, len(events) + 1)),
                             "event_ids": None, "runtime_eligible": False})
        if len(events) != 66:
            raise ValueError("rung contact count drift")
        unique_triads += len(variants)
        unique_contacts += len(events)
        records.append({"source_component": f"rung_{index + 1:02d}", "identity_state": "unallocated",
                        "source_rung": {k: v for k, v in rung.items() if k != "triads"},
                        "schema1_fields": {"id": None, "workbook_id": None, "module_id": None,
                                           "legacy_level": 28, "title": f"Level 28 {rung['key']} natural-minor triad rung",
                                           "kind": "mixed", "content_revision": None, "lineage": None,
                                           "runtime_eligible": False, "source_refs": None,
                                           "events": events, "variants": variants,
                                           "resource_requirements": [],
                                           "timing": {"status": "unresolved", "unit": "quarter", "fixed_bpm": None},
                                           "ambiguities": UNRESOLVED}})
    if (unique_triads, unique_contacts) != (286, 858):
        raise ValueError("whole Level28 unique triad/contact count drift")
    route = candidate["full_round_trip_route"]
    expected_rungs = list(range(1, 14)) + list(range(12, 0, -1))
    for ordinal, (cell, rung_number) in enumerate(zip(route, expected_rungs), 1):
        source_rung = candidate["rungs"][rung_number - 1]
        if (cell["cell_ordinal"] != ordinal or cell["rung"] != rung_number
            or cell["key"] != source_rung["key"] or cell["root_fret"] != source_rung["root_fret"]
            or cell["travel_direction"] != ("up" if ordinal <= 13 else "down")
            or cell["triad_count"] != 22 or cell["contact_count"] != 66):
            raise ValueError("round-trip route geometry/count drift")
    proposal = {"proposal_version": "level028-unallocated-schema1-fields.1", "wbs_id": "2.3.1.1.1",
                "classification": "Build-only, nonimportable schema1 field proposal", "legacy_level": 28,
                "canonical_ids_allocated": False, "schema1_importable": False,
                "whole_workbook_complete": False, "runtime_eligible": False, "admitted": False,
                "counts": candidate["counts"], "source": candidate["source"],
                "source_title": candidate["source_title"], "source_guidance": candidate["source_guidance"],
                "source_discrepancies": candidate["source_discrepancies"], "exceptions": candidate["exceptions"],
                "round_trip_route_reference": {"classification": "reuses_authored_rungs_not_new_unique_events",
                                               "cells": route, "source_rung_order": expected_rungs,
                                               "route_contact_occurrences": 1650, "new_unique_contacts": 0,
                                               "event_ids": None, "runtime_eligible": False},
                "records": records}
    handoff = {"handoff_version": "level028-allocation-handoff.1", "wbs_id": "2.3.1.1.1",
               "catalog_workbook_id": entry["workbook_id"], "catalog_role": entry["catalog_role"],
               "existing_representative_item_id": None, "existing_level028_records": 0,
               "existing_level028_workbook_entities": 0, "proposed_rung_partition": 13,
               "unique_triads": 286, "unique_contacts": 858, "round_trip_cells": 25,
               "round_trip_contact_occurrences": 1650, "canonical_ids_allocated": False, "admitted": False,
               "required_decisions": ["Review all 13 pinned rung cards and the G/B-string geometry with Curriculum.",
                                      "Allocate stable rung/triad/contact identities without duplicating 25-cell route occurrences.",
                                      "Authorize performed picking start, quarter-note timing, BPM, audio and mastery before runtime import."]}
    return proposal, handoff


def products(root: Path) -> dict[str, object]:
    proposal, handoff = project(read_inputs(root))
    manifest = {"manifest_version": "level028-input-pins.1", "inputs": [
        {"path": rel, "bytes": (root / rel).stat().st_size, "sha256": digest}
        for rel, digest in INPUTS.items()]}
    summary = {"summary_version": "level028-schema1-unallocated-summary.1",
               "proposal_sha256": sha(encoded(proposal)), "handoff_sha256": sha(encoded(handoff)),
               "rungs": 13, "unique_triads": 286, "unique_contacts": 858,
               "round_trip_cells": 25, "round_trip_contact_occurrences": 1650,
               "native_run": False, "runtime_eligible": False, "admitted": False}
    return {"field-proposal.json": proposal, "allocation-handoff.json": handoff,
            "input-manifest.json": manifest, "summary.json": summary}


def output_dir(root: Path) -> Path:
    part = root
    for component in OUT.parts:
        part /= component
        if part.is_symlink():
            raise ValueError("output symlink path")
    return part


def run(mode: str, root: Path) -> None:
    built = products(root)
    out = output_dir(root)
    if mode == "build":
        out.mkdir(parents=True, exist_ok=True)
        for name, value in built.items():
            (out / name).write_bytes(encoded(value))
    else:
        for name, value in built.items():
            path = out / name
            if path.is_symlink() or path.read_bytes() != encoded(value):
                raise ValueError(f"output drift: {name}")
    print(f"LEVEL28 {mode.upper()} PASS rungs=13 triads=286 contacts=858 route=25/1650 admitted=false")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("build", "verify"))
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    run(args.mode, args.root.resolve())
