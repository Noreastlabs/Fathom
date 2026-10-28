#!/usr/bin/env python3
"""Build source-bound, unallocated whole-Level52 schema1 field proposals."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from parallel_07_level052_whole_candidate import EXPECTED_COUNTS, build_candidate


ROOT = Path(__file__).resolve().parents[1]
OUT_REL = Path("Build/parallel-10/level052-schema1-unallocated-r01")
INPUTS = {
    "Tools/parallel_07_level052_whole_candidate.py": "daf5f4dda10467b6cd5c80978db51dd58576d7b227605f4358b7899f5960e90a",
    "Results/parallel-07/conversion/20260923T155742Z-2.3.1.2.1-level052-whole-candidate-r01-results.md": "86af414fd7fe1a36dc44a24ebe9fea5b81ffcb9a9e3cd51d4143839d2b02142f",
    "Build/parallel-07/2.3.1.2.1-level052-whole-r01/candidate.json": "269f7257ee570baa849a039023056521f11f033d2e15ab6934cda88f7ba2837d",
    "Content/controls/curriculum-v1/package.json": "766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255",
    "Content/controls/curriculum-v1/identity-registry.json": "5d265859e1e8a5a530a0e53d88b019a1c920f3bba6cccb4ef0fef2f7640007e5",
    "Content/controls/curriculum-v1/generation.json": "fc6cec9f9d67eb82c97c5f4c3fb95d285178fb7fce7bd147d9ae0296d21b4c1c",
    "Results/parallel-01/exercises/inventory/20260922T180500Z-2.3-curriculum-v1-source-inventory-evidence/curriculum-source-map.json": "bad5581a04f43ba8baf14db430449e1ccff5cf88f0f7e42198328073b27053d6",
    "Notes/music/guitar project/TXT version/Guitar_Exercises_Section_VI_Level_52_Major_and_Minor_Triads_Root_Position_First_Inversion_Second_Inversion_Top_Three_Strings.txt": "6e8a5b93bf8b5b66c045ed943e6b873fe52c849da2d741f59857c6a736ea0bd3",
    "Notes/music/guitar project/PDF version/Guitar_Exercises_Section_VI_Level_52_Major_and_Minor_Triads_Root_Position_First_Inversion_Second_Inversion_Top_Three_Strings.pdf": "0cdfff4afe53df5c881e05c61908f4576c0a5d828e7440bb9ec88ebaa6fba503",
}
UNIT_KEYS = {"shape_workouts": "shapes", "inversion_cycles": "cycles", "quality_switches": "switches",
             "patterns": "patterns", "major_progressions": "progressions", "minor_progressions": "progressions",
             "major_capstone": "bars", "minor_capstone": "bars"}
UNRESOLVED = ["canonical workbook/module/item/event/variant IDs and lineage",
              "performed chord/strum voicing, note MIDI and pick direction",
              "quarter-note onset/duration, fixed BPM and note-per-click",
              "Curriculum/musical review and human silent-formation mastery"]


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def encoded(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")


def pinned(root: Path, rel: str, sha: str) -> bytes:
    raw = (root / rel).read_bytes()
    if digest(raw) != sha:
        raise ValueError(f"input drift: {rel}")
    return raw


def read_inputs(root: Path) -> tuple[dict, dict, dict, dict]:
    raw = {rel: pinned(root, rel, sha) for rel, sha in INPUTS.items()}
    sealed = json.loads(raw["Build/parallel-07/2.3.1.2.1-level052-whole-r01/candidate.json"])
    txt = raw[sealed["source"]["txt_path"]]
    pdf = raw[sealed["source"]["pdf_path"]]
    # The P07 in-memory degree tables contain tuples; JSON serializes them as arrays.
    if sealed != json.loads(json.dumps(build_candidate(txt_data=txt, pdf_data=pdf))):
        raise ValueError("P07 Level52 candidate differs from original TXT/PDF replay")
    foundation = json.loads(raw["Content/controls/curriculum-v1/package.json"])
    registry = json.loads(raw["Content/controls/curriculum-v1/identity-registry.json"])
    generation = json.loads(raw["Content/controls/curriculum-v1/generation.json"])
    source_map = json.loads(raw["Results/parallel-01/exercises/inventory/20260922T180500Z-2.3-curriculum-v1-source-inventory-evidence/curriculum-source-map.json"])
    if len(foundation["records"]) != 659 or generation["records"] != 659:
        raise ValueError("current659 foundation drift")
    return sealed, foundation, registry, source_map


def identity_boundary(foundation: dict, registry: dict, source_map: dict) -> dict:
    workbook = "fg:workbook:000052"
    if any(r.get("legacy_level") == 52 or r.get("workbook_id") == workbook for r in foundation["records"]):
        raise ValueError("unexpected canonical Level52 record")
    if any(e.get("id") == workbook for e in registry["entities"]):
        raise ValueError("unexpected Level52 registry entity")
    entry = next((x for x in foundation["workbook_catalog"]["entries"] if x.get("workbook_id") == workbook), None)
    if not entry or entry.get("representative_item_id") is not None or entry.get("whole_workbook_complete") is not False or entry.get("admitted") is not False or entry.get("conversion_status") != "not_converted":
        raise ValueError("Level52 source-only catalog drift")
    row = next((r for r in source_map["rows"] if r.get("level") == 52), None)
    if not row or row.get("representative_item_id") is not None or row.get("stable_ids_assigned") is not False or row.get("admitted") is not False or row.get("wbs_owner") != "2.3.1.2.1":
        raise ValueError("Level52 source-map authority drift")
    return entry


def _attack_field(source: dict, module: str, unit_number: int, ordinal: int, refs: list[str]) -> dict:
    if set(source) != {"chord", "duration_q", "frets_g_b_e", "inversion", "kind", "onset_q", "quality", "sounded", "string", "tone"}:
        raise ValueError("source attack field drift")
    if source["kind"] not in ("blocked", "arpeggio", "muted_backbeat") or source["onset_q"] is not None or source["duration_q"] is not None:
        raise ValueError("invented or unsupported source attack")
    if source["kind"] == "muted_backbeat":
        if source["sounded"] is not False or source["string"] is not None or source["tone"] is not None:
            raise ValueError("muted backbeat acquired sounding tone")
        contact = "muted"
    else:
        if source["sounded"] is not True:
            raise ValueError("printed sounded attack became silent")
        contact = "pitched"
    if source["kind"] == "blocked" and (source["string"] is not None or source["tone"] is not None):
        raise ValueError("blocked chord acquired invented member")
    if source["kind"] == "arpeggio" and (source["string"] not in ("G", "B", "e") or not source["tone"]):
        raise ValueError("arpeggio lost printed string/tone")
    if len(source["frets_g_b_e"]) != 3 or any(not isinstance(f, int) or f < 0 for f in source["frets_g_b_e"]):
        raise ValueError("source triad fret drift")
    return {"source_module": module, "source_unit_number": unit_number, "source_local_ordinal": ordinal,
            "source_refs": refs, "source_attack": source,
            "source_tone": {"string": source["string"], "printed_tone": source["tone"], "sounding_midi": None}
                if source["kind"] == "arpeggio" else None,
            "performed_member_pitches": None,
            "schema1_fields": {"event_id": None, "kind": "contact", "contact": contact,
                               "pick": None, "pitch_binding": None, "onset_q": None, "duration_q": None}}


def project(candidate: dict, foundation: dict, registry: dict, source_map: dict) -> tuple[dict, dict]:
    entry = identity_boundary(foundation, registry, source_map)
    if candidate.get("schema") != "fathom-level052-whole-detached-candidate-v1" or candidate.get("level") != 52 or candidate.get("wbs_id") != "2.3.1.2.1":
        raise ValueError("Level52 candidate scope drift")
    if any(candidate.get(k) is not None for k in ("canonical_item_id", "canonical_variant_id", "onset_q", "duration_q", "fixed_bpm", "note_per_click")) or any(candidate.get(k) is not False for k in ("whole_workbook_complete", "runtime_eligible", "runtime_admitted", "imported", "admitted")):
        raise ValueError("source candidate invented authority/timing")
    if candidate.get("module_attack_counts") != EXPECTED_COUNTS or candidate.get("sounded_workload_attack_count") != 976 or candidate.get("silent_formation_count") != 42:
        raise ValueError("976/42 workload drift")
    if candidate.get("authored_alternatives") != [{"chord": "C", "inversion": "second_inversion",
            "module_a_and_d_frets_g_b_e": [0, 1, 0], "module_e_quality_switch_frets_g_b_e": [12, 13, 12],
            "relationship": "same C-major inversion one octave higher"}]:
        raise ValueError("C second-inversion octave alternative drift")
    modules = candidate["modules"]
    if set(modules) != set(UNIT_KEYS) | {"silent_and_ear_tasks"}:
        raise ValueError("module set drift")
    silent = modules["silent_and_ear_tasks"]
    if (silent.get("silent_formation_count") != 42 or len(silent.get("formations", [])) != 42 or
        silent.get("counted_in_attacks") is not False or
        silent.get("pdf_first_attempt_threshold") != {"minimum_correct_per_quality": 18, "total_per_quality": 21} or
        silent.get("txt_mastery_separate_days") != 2 or any(f.get("sound_attack") is not False for f in silent["formations"])):
        raise ValueError("silent formation/source mastery drift")
    records = []
    attack_total = 0
    unit_total = 0
    kind_counts = {"blocked": 0, "arpeggio": 0, "muted_backbeat": 0}
    for module, unit_key in UNIT_KEYS.items():
        group = modules[module]
        units = group[unit_key]
        events = []
        variants = []
        for unit_number, unit in enumerate(units, 1):
            attacks = unit["attacks"]
            if len(attacks) != unit.get("attack_count", 4) or (module.endswith("capstone") and len(attacks) != 4):
                raise ValueError("source unit attack count drift")
            refs = unit.get("source_refs") or ([unit["source_ref"]] if "source_ref" in unit else group.get("source_refs", []))
            if not refs:
                raise ValueError("source unit refs missing")
            start = len(events) + 1
            for ordinal, attack in enumerate(attacks, 1):
                kind_counts[attack["kind"]] += 1
                events.append(_attack_field(attack, module, unit_number, ordinal, refs))
            meta = {key: value for key, value in unit.items() if key != "attacks"}
            variants.append({"id": None, "source_unit_number": unit_number,
                             "source_unit": meta, "source_event_ordinals": list(range(start, len(events) + 1)),
                             "event_ids": None, "runtime_eligible": False})
            unit_total += 1
        if len(events) != EXPECTED_COUNTS[module] or group["attack_count"] != len(events):
            raise ValueError(f"{module} module attack count drift")
        attack_total += len(events)
        records.append({"source_component": module, "identity_state": "unallocated", "silent_tasks": [],
                        "schema1_fields": {"id": None, "workbook_id": None, "module_id": None, "legacy_level": 52,
                            "title": f"Level 52 {module.replace('_', ' ')}", "kind": "mixed", "content_revision": None,
                            "lineage": None, "runtime_eligible": False, "source_refs": None,
                            "events": events, "variants": variants, "resource_requirements": [],
                            "timing": {"status": "unresolved", "unit": "quarter", "fixed_bpm": None},
                            "ambiguities": UNRESOLVED}})
    records.append({"source_component": "silent_and_ear_tasks", "identity_state": "unallocated",
                    "silent_tasks": silent, "schema1_fields": {"id": None, "workbook_id": None, "module_id": None,
                        "legacy_level": 52, "title": "Level 52 silent formations and ear tasks", "kind": "task",
                        "content_revision": None, "lineage": None, "runtime_eligible": False, "source_refs": None,
                        "events": [], "variants": [], "resource_requirements": [],
                        "timing": {"status": "unresolved", "unit": "quarter", "fixed_bpm": None},
                        "ambiguities": UNRESOLVED}})
    if attack_total != 976 or unit_total != 123 or kind_counts != {"blocked": 690, "arpeggio": 282, "muted_backbeat": 4}:
        raise ValueError("whole-Level52 event projection drift")
    f6 = records[3]["schema1_fields"]["variants"][5]
    f6_events = records[3]["schema1_fields"]["events"]
    f6_kinds = [f6_events[i - 1]["source_attack"]["kind"] for i in f6["source_event_ordinals"]]
    if f6_kinds != ["blocked", "muted_backbeat"] * 4:
        raise ValueError("F6 sounded/muted backbeat drift")
    proposal = {"proposal_version": "level052-unallocated-schema1-fields.1", "wbs_id": "2.3.1.2.1",
                "classification": "Build-only, nonimportable schema1 field proposal", "legacy_level": 52,
                "canonical_ids_allocated": False, "schema1_importable": False, "whole_workbook_complete": False,
                "runtime_eligible": False, "admitted": False,
                "counts": {"provisional_components": 9, "attack_units": unit_total, "silent_formations": 42,
                           "printed_attacks": attack_total, "attack_kinds": kind_counts},
                "source": candidate["source"], "authored_alternatives": candidate["authored_alternatives"],
                "instructions": candidate["instructions"], "inversion_degree_orders": candidate["inversion_degree_orders"],
                "records": records}
    handoff = {"handoff_version": "level052-allocation-handoff.1", "wbs_id": "2.3.1.2.1",
               "catalog_workbook_id": entry["workbook_id"], "catalog_role": entry["catalog_role"],
               "existing_level052_records": 0, "existing_level052_workbook_entities": 0,
               "printed_attacks": 976, "silent_formations_not_events": 42,
               "proposed_component_partition": list(UNIT_KEYS) + ["silent_and_ear_tasks"],
               "canonical_ids_allocated": False, "admitted": False,
               "required_decisions": ["Review source spelling, forms and printed pass alternatives with Curriculum.",
                  "Allocate stable IDs/lineage after current source and registry reservations are sealed.",
                  "Authorize exact pitch, pick and timing semantics before native import or runtime admission."]}
    return proposal, handoff


def products(root: Path) -> dict[str, object]:
    candidate, foundation, registry, source_map = read_inputs(root)
    proposal, handoff = project(candidate, foundation, registry, source_map)
    manifest = {"manifest_version": "level052-input-pins.1", "inputs": [
        {"path": rel, "bytes": (root / rel).stat().st_size, "sha256": sha} for rel, sha in INPUTS.items()]}
    summary = {"summary_version": "level052-schema1-unallocated-summary.1",
               "proposal_sha256": digest(encoded(proposal)), "handoff_sha256": digest(encoded(handoff)),
               "printed_attacks": 976, "silent_formations": 42,
               "native_run": False, "runtime_eligible": False, "admitted": False}
    return {"field-proposal.json": proposal, "allocation-handoff.json": handoff,
            "input-manifest.json": manifest, "summary.json": summary}


def output_dir(root: Path) -> Path:
    part = root
    for component in OUT_REL.parts:
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
    print(f"LEVEL52 {mode.upper()} PASS attacks=976 silent=42 admitted=false")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("build", "verify"))
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    run(args.mode, args.root.resolve())


if __name__ == "__main__":
    main()
