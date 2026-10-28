#!/usr/bin/env python3
"""Build a source-bound, unallocated Level49 schema1 field proposal."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from curriculum_level049_whole_chord_foundation_candidate import (
    MODULE_COUNTS,
    MODULE_UNITS,
    build_candidate,
)


ROOT = Path(__file__).resolve().parents[1]
OUT_REL = Path("Build/parallel-10/level049-schema1-unallocated-r01")
INPUTS = {
    "Tools/curriculum_level049_whole_chord_foundation_candidate.py": "3aca79451ecaac8693662c4bb6476d0f7a5d061eb600528605169b282b6160bd",
    "Results/parallel-05/exercises/conversion/20260923T155200Z-2.3.1.2.1-level049-whole-chord-foundation-r01-results.md": "22bec7e8393e7987827ee03864093054aeb437622a8d001a29f0ba3a27975281",
    "Build/parallel-05/2.3.1.2.1-level049-whole-r01/candidate-b.json": "20d21821c317773990671ceef1a6b730ac3c1bef620aceefe5caec5414e30d33",
    "Content/controls/curriculum-v1/package.json": "766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255",
    "Content/controls/curriculum-v1/identity-registry.json": "5d265859e1e8a5a530a0e53d88b019a1c920f3bba6cccb4ef0fef2f7640007e5",
    "Content/controls/curriculum-v1/generation.json": "fc6cec9f9d67eb82c97c5f4c3fb95d285178fb7fce7bd147d9ae0296d21b4c1c",
    "Content/controls/curriculum-v1/workbook-coverage.json": "d8e492101c97c60add858799c77da4db3f0c528d348c9cf66105c2dc37df4eeb",
    "Notes/music/guitar project/TXT version/Guitar_Exercises_Section_VI_Level_49_Chord_Mechanics_Muting_and_Open_Chord_Foundation.txt": "8487f1d1bc949e79509de98b10e1888200d48ddf8651d98979634e44b9fc20c3",
    "Notes/music/guitar project/PDF version/Guitar_Exercises_Section_VI_Level_49_Chord_Mechanics_Muting_and_Open_Chord_Foundation.pdf": "abadffbe75122328585fd64758e3ef9ffb7c6f8c9d2f14702e173a97808cfd8f",
    "Results/parallel-01/exercises/inventory/20260922T180500Z-2.3-curriculum-v1-source-inventory-evidence/curriculum-source-map.json": "bad5581a04f43ba8baf14db430449e1ccff5cf88f0f7e42198328073b27053d6",
}
SOURCE_KEYS = ("module", "unit", "ordinal", "printed_symbol", "kind", "chord", "string", "printed_fret_or_mute", "txt_line", "pdf_page")
UNRESOLVED = [
    "canonical workbook/module/item/event/variant IDs and lineage",
    "quarter-note onset/duration, fixed BPM and note-per-click",
    "strum sounding members, attack-zone performance and contact pitch binding",
    "Curriculum disposition of PDF-only tests and A2 reverse pass",
]


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def encoded(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def pinned(root: Path, rel: str, sha: str) -> bytes:
    path = root / rel
    raw = path.read_bytes()
    if digest(raw) != sha:
        raise ValueError(f"input drift: {rel}")
    return raw


def read_inputs(root: Path) -> tuple[dict, dict, dict]:
    raw = {rel: pinned(root, rel, sha) for rel, sha in INPUTS.items()}
    sealed = json.loads(raw["Build/parallel-05/2.3.1.2.1-level049-whole-r01/candidate-b.json"])
    replay = build_candidate(root)
    if sealed != replay:
        raise ValueError("P05 candidate differs from original TXT/PDF replay")
    foundation = json.loads(raw["Content/controls/curriculum-v1/package.json"])
    generation = json.loads(raw["Content/controls/curriculum-v1/generation.json"])
    if len(foundation["records"]) != 659 or generation["records"] != 659:
        raise ValueError("current659 foundation drift")
    return sealed, foundation, generation


def representative(foundation: dict) -> dict:
    matches = [r for r in foundation["records"] if r.get("legacy_level") == 49]
    if len(matches) != 1:
        raise ValueError("expected exactly one selected Level49 representative")
    record = matches[0]
    if (record.get("id"), record.get("workbook_id"), record.get("content_revision"), len(record.get("events", []))) != (
        "fg:item:000008", "fg:workbook:000049", 3, 2
    ):
        raise ValueError("Level49 representative identity/revision drift")
    scope = record.get("control_scope", {})
    if scope.get("extent") != "complete_selected_case" or scope.get("whole_workbook_complete") is not False:
        raise ValueError("representative falsely became whole-workbook coverage")
    return record


def _source_tone(attack: dict, unit: dict, shapes: dict) -> dict | None:
    string = attack["string"]
    if string is None:
        return None
    if string not in ("E", "A", "D", "G", "B", "e"):
        raise ValueError("unrecognized source string")
    if attack["module"] == "A1":
        return {"string": string, "fret_or_mute": attack["printed_fret_or_mute"], "printed_note": unit["printed_note"], "printed_finger": unit["fretting_finger"], "sounding_midi": None}
    shape = shapes[attack["chord"]]
    idx = ("E", "A", "D", "G", "B", "e").index(string)
    fret = shape["frets"][idx]
    if attack["printed_fret_or_mute"].upper() != fret.upper():
        raise ValueError("individual string test differs from chord source shape")
    note = shape["notes"][idx]
    if fret.upper() == "X" and note.upper() != "X":
        raise ValueError("muted source string has printed note")
    return {"string": string, "fret_or_mute": fret, "printed_note": note, "printed_finger": shape["fingers"][idx], "sounding_midi": None}


def _contact(kind: str) -> str | None:
    if kind in {"muted-string test", "muted strum", "muted backbeat"}:
        return "muted"
    if kind in {"pitched-string test", "clean", "minimum clean pressure", "downstrum", "four-string arpeggio pick"}:
        return "pitched"
    if kind == "release without lifting":
        return "release"
    if kind == "fade to buzz threshold":
        return None
    raise ValueError(f"unmapped source attack kind: {kind}")


def project(candidate: dict, foundation: dict) -> tuple[dict, dict]:
    if candidate.get("level") != 49 or candidate.get("wbs_id") != "2.3.1.2.1" or candidate.get("module_components") != list(MODULE_COUNTS):
        raise ValueError("Level49 source candidate scope drift")
    if candidate.get("printed_attack_count") != 780 or candidate.get("module_count") != 11:
        raise ValueError("Level49 source count drift")
    if any(candidate.get(k) is not False for k in ("admitted", "imported", "runtime_eligible")) or candidate.get("canonical_ids") is not None:
        raise ValueError("source candidate has false authority")
    exceptions = candidate.get("source_exceptions")
    if not isinstance(exceptions, list) or {e.get("code") for e in exceptions} != {
        "PDF_ONLY_ONE_MINUTE_CHANGE_TESTS_AND_ADVANCEMENT", "A2_REVERSE_PASS_OUTSIDE_CORE_COUNT"
    } or any(e.get("status") != "Pending Curriculum review" for e in exceptions):
        raise ValueError("source exceptions lost or changed")
    rep = representative(foundation)
    catalog = foundation["workbook_catalog"]["entries"]
    entry = next((x for x in catalog if x.get("workbook_id") == "fg:workbook:000049"), None)
    if entry is None or entry.get("whole_workbook_complete") is not False or entry.get("admitted") is not False:
        raise ValueError("catalog Level49 authority drift")
    if candidate["source"]["source_map_row"].get("representative_item_id") != rep["id"]:
        raise ValueError("source-map representative mismatch")
    shapes = {s["chord"]: s for s in candidate["chord_shapes"]}
    if len(shapes) != 11 or len(candidate["chord_shapes"]) != 11:
        raise ValueError("chord-shape coverage drift")
    records = []
    attack_total = 0
    unit_total = 0
    for module in candidate["modules"]:
        name = module["module"]
        if name not in MODULE_COUNTS or name != list(MODULE_COUNTS)[len(records)]:
            raise ValueError("component order drift")
        if len(module["units"]) != MODULE_UNITS[name] or module["printed_attack_count"] != MODULE_COUNTS[name]:
            raise ValueError("component count drift")
        events = []
        variants = []
        for unit_number, unit in enumerate(module["units"], 1):
            unit_ordinals = []
            for ordinal, attack in enumerate(unit["attacks"], 1):
                if set(attack) != set(SOURCE_KEYS) | {"performed_onset", "performed_duration", "performed_pick", "performed_quality"}:
                    raise ValueError("source attack field set drift")
                if attack["module"] != name or attack["unit"] != unit["label"] and name != "A1" or attack["ordinal"] != ordinal:
                    raise ValueError("source attack order drift")
                if (attack["txt_line"] < module["txt_start_line"] or attack["txt_line"] > module["txt_end_line"] or
                    attack["pdf_page"] < 1 or attack["pdf_page"] > 20):
                    raise ValueError("source span drift")
                if any(attack[k] is not None for k in ("performed_onset", "performed_duration", "performed_pick", "performed_quality")):
                    raise ValueError("source candidate invented performance data")
                source = {key: attack[key] for key in SOURCE_KEYS}
                event = {
                    "source_local_ordinal": len(events) + 1,
                    "source_attack": source,
                    "source_tone": _source_tone(attack, unit, shapes),
                    "schema1_fields": {"event_id": None, "kind": "contact", "contact": _contact(attack["kind"]),
                                       "pick": "D" if attack["kind"] == "downstrum" else None,
                                       "pitch_binding": None, "onset_q": None, "duration_q": None},
                }
                events.append(event)
                unit_ordinals.append(len(events))
            variants.append({"id": None, "source_unit_number": unit_number, "label": unit["label"],
                             "source_txt_line": unit["txt_line"], "source_pdf_page": unit["pdf_page"],
                             "event_ids": None, "source_event_ordinals": unit_ordinals,
                             "timing": None, "runtime_eligible": False})
            unit_total += 1
        if len(events) != MODULE_COUNTS[name]:
            raise ValueError("projected attack count drift")
        records.append({"source_component": name, "identity_state": "unallocated", "schema1_fields": {
            "id": None, "workbook_id": None, "module_id": None, "legacy_level": 49,
            "title": f"Level 49 component {name}", "kind": "mixed", "content_revision": None,
            "lineage": None, "runtime_eligible": False, "source_refs": None,
            "events": events, "variants": variants, "timing": {"status": "unresolved", "unit": "quarter",
            "basis": "Printed beat/BPM directions do not establish performed onset or duration."},
            "resource_requirements": [], "ambiguities": list(UNRESOLVED)},
            "source_txt_start_line": module["txt_start_line"], "source_txt_end_line": module["txt_end_line"]})
        attack_total += len(events)
    if attack_total != 780 or unit_total != 75:
        raise ValueError("whole-Level49 projection total drift")
    proposal = {"proposal_version": "level049-unallocated-schema1-fields.1", "wbs_id": "2.3.1.2.1", "legacy_level": 49,
                "classification": "Build-only, nonimportable schema1 field proposal", "canonical_ids_allocated": False,
                "schema1_importable": False, "whole_workbook_complete": False, "admitted": False, "runtime_eligible": False,
                "counts": {"components": 11, "units": unit_total, "printed_attacks": attack_total, "chord_shapes": 11},
                "source": {key: candidate["source"][key] for key in ("txt_path", "txt_sha256", "pdf_path", "pdf_sha256", "pdf_pages", "source_map_path", "source_map_sha256")},
                "chord_shapes": candidate["chord_shapes"], "source_exceptions": exceptions,
                "printed_guidance": candidate["printed_guidance"], "records": records}
    handoff = {"handoff_version": "level049-allocation-handoff.1", "wbs_id": "2.3.1.2.1", "admitted": False,
               "existing_selected_representative": {"id": rep["id"], "workbook_id": rep["workbook_id"],
                    "content_revision": rep["content_revision"], "event_count": len(rep["events"]),
                    "record_sha256": digest(encoded(rep)), "source_refs": rep["source_refs"],
                    "extent": rep["control_scope"]["extent"], "whole_workbook_complete": False},
               "proposed_component_partition": [r["source_component"] for r in records],
               "required_decisions": ["Compare the existing E/Em two-event reference with B's full E/Em cells and source spans.",
                    "Choose revision/new-record lineage and allocate disjoint IDs after current global floors are sealed.",
                    "Resolve strum member/pitch, timing and the two source exceptions with Curriculum before import."],
               "canonical_ids_allocated": False, "runtime_eligible": False}
    return proposal, handoff


def products(root: Path) -> dict[str, object]:
    candidate, foundation, _ = read_inputs(root)
    proposal, handoff = project(candidate, foundation)
    input_manifest = {"manifest_version": "level049-input-pins.1", "inputs": [
        {"path": rel, "bytes": (root / rel).stat().st_size, "sha256": sha} for rel, sha in INPUTS.items()]}
    summary = {"summary_version": "level049-schema1-unallocated-summary.1", "proposal_sha256": digest(encoded(proposal)),
               "handoff_sha256": digest(encoded(handoff)), "components": 11, "units": 75, "printed_attacks": 780,
               "native_run": False, "admitted": False, "runtime_eligible": False}
    return {"field-proposal.json": proposal, "allocation-handoff.json": handoff,
            "input-manifest.json": input_manifest, "summary.json": summary}


def output_dir(root: Path) -> Path:
    out = root / OUT_REL
    part = root
    for component in OUT_REL.parts:
        part = part / component
        if part.is_symlink():
            raise ValueError("output path uses symlink")
    return out


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
    print(f"LEVEL49 {mode.upper()} PASS components=11 units=75 attacks=780 admitted=false")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("build", "verify"))
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    run(args.mode, args.root.resolve())


if __name__ == "__main__":
    main()
