#!/usr/bin/env python3
"""Project P07's pinned whole Level57 source candidate into unallocated schema1 fields."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from parallel_07_level057_whole_candidate import build_candidate


ROOT = Path(__file__).resolve().parents[1]
OUT_REL = Path("Build/parallel-10/level057-schema1-unallocated-r01")
INPUTS = {
    "Tools/parallel_07_level057_whole_candidate.py": "19b450a35d3733e70b6c7352ad65ecb71a3ed4d74c3d78f41201a86a78a456c2",
    "Results/parallel-07/conversion/20260923T160843Z-2.3.1.2.1-level057-whole-candidate-r01-results.md": "bda0347dcdc12ab585ef501a271c7e109455bf5ab3aedf0aedd3c313a7525f19",
    "Build/parallel-07/2.3.1.2.1-level057-whole-r01/level057_whole_candidate.json": "0697ac49f849da89cf142f606b0a09693f33ba103d46225fbb7824e78a7e886e",
    "Content/controls/curriculum-v1/package.json": "766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255",
    "Content/controls/curriculum-v1/identity-registry.json": "5d265859e1e8a5a530a0e53d88b019a1c920f3bba6cccb4ef0fef2f7640007e5",
    "Content/controls/curriculum-v1/generation.json": "fc6cec9f9d67eb82c97c5f4c3fb95d285178fb7fce7bd147d9ae0296d21b4c1c",
    "Results/parallel-01/exercises/inventory/20260922T180500Z-2.3-curriculum-v1-source-inventory-evidence/curriculum-source-map.json": "bad5581a04f43ba8baf14db430449e1ccff5cf88f0f7e42198328073b27053d6",
    "Notes/music/guitar project/TXT version/Guitar_Exercises_Section_VI_Level_57_Seventh_Chords_Shell_Voicings_Major_and_Minor_ii_V_I_and_Functional_Voice_Leading.txt": "f8c4090f825373861e07c506a44d1f8ef486161700d96896181f9785a9086545",
    "Notes/music/guitar project/PDF version/Guitar_Exercises_Section_VI_Level_57_Seventh_Chords_Shell_Voicings_Major_and_Minor_ii_V_I_and_Functional_Voice_Leading.pdf": "ddf35a3cd2a0506446c209b81aa31e9206439f0ff6a06675fef5b4f7f8c991fd",
}
COUNTS = {"B_E_root_families": 112, "C_A_root_families": 112, "D_quality_ladders": 56,
          "E_major_cadences": 108, "F_minor_cadences": 108, "G_A_blues": 108,
          "H_arpeggio_scans": 64, "I_capstones": 128}
UNRESOLVED = ["canonical workbook/module/item/event/variant identities and lineage",
              "quarter-note onset/duration, fixed BPM, accent and pick direction",
              "minor preparatory full iiø sounded-strike count beyond printed totals",
              "A-blues pass-four three-note arpeggio contact selection and string order",
              "human mastery and runtime admission"]


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def encoded(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def pinned(root: Path, rel: str, sha: str) -> bytes:
    path = root / rel
    if path.is_symlink():
        raise ValueError(f"input symlink: {rel}")
    raw = path.read_bytes()
    if digest(raw) != sha:
        raise ValueError(f"input drift: {rel}")
    return raw


def read_inputs(root: Path) -> tuple[dict, dict, dict]:
    raw = {rel: pinned(root, rel, sha) for rel, sha in INPUTS.items()}
    candidate = json.loads(raw["Build/parallel-07/2.3.1.2.1-level057-whole-r01/level057_whole_candidate.json"])
    if candidate != json.loads(json.dumps(build_candidate(root))):
        raise ValueError("P07 candidate differs from original TXT/PDF replay")
    foundation = json.loads(raw["Content/controls/curriculum-v1/package.json"])
    registry = json.loads(raw["Content/controls/curriculum-v1/identity-registry.json"])
    generation = json.loads(raw["Content/controls/curriculum-v1/generation.json"])
    if len(foundation["records"]) != 659 or generation["records"] != 659:
        raise ValueError("current659 foundation drift")
    return candidate, foundation, registry


def identity_boundary(foundation: dict, registry: dict) -> dict:
    workbook = "fg:workbook:000057"
    if any(r.get("legacy_level") == 57 or r.get("workbook_id") == workbook for r in foundation["records"]):
        raise ValueError("unexpected canonical Level57 record")
    if any(e.get("id") == workbook for e in registry["entities"]):
        raise ValueError("unexpected Level57 registry entity")
    entry = next((e for e in foundation["workbook_catalog"]["entries"] if e.get("workbook_id") == workbook), None)
    if (not entry or entry.get("representative_item_id") is not None or
        entry.get("whole_workbook_complete") is not False or entry.get("admitted") is not False or
        entry.get("conversion_status") != "not_converted"):
        raise ValueError("Level57 source-only catalog drift")
    return entry


def _units(name: str, module: dict) -> list[dict]:
    if name in ("B_E_root_families", "C_A_root_families"):
        return [shape for family in module["families"] for shape in family["shapes"]]
    if name == "D_quality_ladders":
        return module["ladders"]
    if name in ("E_major_cadences", "F_minor_cadences"):
        return module["cells"]
    if name == "G_A_blues":
        return module["passes"]
    if name == "H_arpeggio_scans":
        return module["scans"]
    if name == "I_capstones":
        return module["major"]["blocks"] + module["minor"]["blocks"]
    raise ValueError(f"unrecognized source module: {name}")


def project(candidate: dict, foundation: dict, registry: dict) -> tuple[dict, dict]:
    entry = identity_boundary(foundation, registry)
    if (candidate.get("schema") != "fathom.level57.whole.detached_candidate.v1" or
        candidate.get("level") != 57 or candidate.get("status") != "candidate_only" or
        candidate.get("wbs") != "2.3.1.2.1"):
        raise ValueError("Level57 source scope drift")
    workload = candidate["workload"]
    if (workload != {"silent_formations": 56, "sounded_attacks": 796,
                     "module_attacks": COUNTS, "preparatory_full_iiø_checks_counted": False}):
        raise ValueError("796/56 source workload drift")
    limits = candidate["musical_limits"]
    if (limits["m7_m7b5_shells_identical"] is not True or
        limits["flat_fifth_restoration_required"] is not True or
        limits["blues_pass4_arpeggio_contacts"] != "unspecified in source" or
        "outside the printed 18" not in limits["minor_full_check_count_boundary"] or
        "outside printed 64" not in limits["minor_capstone_check_count_boundary"]):
        raise ValueError("musical/count boundary drift")
    modules = candidate["modules"]
    if list(modules) != ["A_silent_formations", *COUNTS]:
        raise ValueError("module sequence drift")
    silent = modules["A_silent_formations"]
    shapes = [shape for name in ("B_E_root_families", "C_A_root_families")
              for family in modules[name]["families"] for shape in family["shapes"]]
    if silent["count"] != 56 or silent["sounded"] is not False or len(shapes) != 56 or not all(
        shape["silent_formation_before_first_attack"] is True for shape in shapes):
        raise ValueError("56 silent formations drift")
    silent_tasks = [{"source_chord": shape["chord"], "source_root_string": shape["root_string"],
                     "source_shape": shape, "source_ref": shape["source_ref"],
                     "pdf_page": shape["pdf_page"], "performed": None} for shape in shapes]
    records = [{"source_component": "A", "source_module_name": "A_silent_formations",
                "source_module": silent, "silent_tasks": silent_tasks, "identity_state": "unallocated",
                "schema1_fields": {"id": None, "workbook_id": None, "module_id": None,
                                   "legacy_level": 57, "title": "Level 57 component A", "kind": "mixed",
                                   "content_revision": None, "lineage": None, "source_refs": None,
                                   "events": [], "variants": [], "runtime_eligible": False,
                                   "resource_requirements": [],
                                   "timing": {"status": "unresolved", "unit": "quarter", "fixed_bpm": None},
                                   "ambiguities": UNRESOLVED}}]
    unit_total = 0
    event_total = 0
    for name, expected in COUNTS.items():
        module = modules[name]
        source_units = _units(name, module)
        events = []
        variants = []
        for unit_number, source_unit in enumerate(source_units, 1):
            attacks = source_unit["attacks"]
            if len(attacks) != source_unit["attack_count"]:
                raise ValueError(f"{name} source-unit attack count drift")
            start = len(events) + 1
            ref = source_unit.get("source_ref", module.get("source_ref"))
            page = source_unit.get("pdf_page", module.get("pdf_page"))
            if name == "G_A_blues":
                ref, page = module["source_ref"], module["pdf_pages"]
            for source_attack in attacks:
                if (source_attack["sounded"] is not True or source_attack["onset_q"] is not None or
                    source_attack["duration_q"] is not None or not isinstance(source_attack["contacts"], list)):
                    raise ValueError("source attack performance boundary drift")
                if (name == "G_A_blues" and unit_number == 4 and
                    source_attack["kind"] == "three_note_arpeggio_unspecified_contact" and
                    (source_attack["contacts"] or source_attack["contact_selection"] is not None)):
                    raise ValueError("invented blues pass-four contact")
                events.append({"source_module": name, "source_unit_number": unit_number,
                               "source_local_ordinal": len(events) + 1, "source_ref": ref,
                               "source_pdf_page": page, "source_attack": source_attack,
                               "schema1_fields": {"event_id": None, "kind": "contact", "contact": "pitched",
                                                  "pick": None, "pitch_binding": None,
                                                  "onset_q": None, "duration_q": None}})
            variants.append({"id": None, "source_unit_number": unit_number,
                             "source_unit": source_unit,
                             "source_event_ordinals": list(range(start, len(events) + 1)),
                             "event_ids": None, "runtime_eligible": False})
            unit_total += 1
        if len(events) != expected or module["attack_count"] != expected:
            raise ValueError(f"{name} printed attack count drift")
        event_total += len(events)
        letter = name[0]
        records.append({"source_component": letter, "source_module_name": name,
                        "source_module": module, "silent_tasks": None, "identity_state": "unallocated",
                        "schema1_fields": {"id": None, "workbook_id": None, "module_id": None,
                                           "legacy_level": 57, "title": f"Level 57 component {letter}",
                                           "kind": "mixed", "content_revision": None, "lineage": None,
                                           "source_refs": None, "events": events, "variants": variants,
                                           "runtime_eligible": False, "resource_requirements": [],
                                           "timing": {"status": "unresolved", "unit": "quarter", "fixed_bpm": None},
                                           "ambiguities": UNRESOLVED}})
    if event_total != 796 or unit_total != 90:
        raise ValueError("whole Level57 attack/unit count drift")
    proposal = {"proposal_version": "level057-unallocated-schema1-fields.1", "wbs_id": "2.3.1.2.1",
                "classification": "Build-only, nonimportable schema1 field proposal", "legacy_level": 57,
                "canonical_ids_allocated": False, "schema1_importable": False,
                "whole_workbook_complete": False, "runtime_eligible": False, "admitted": False,
                "counts": {"provisional_components": 9, "attack_units": unit_total,
                           "silent_formations": 56, "printed_attacks": event_total},
                "source": candidate["source"], "musical_limits": limits,
                "source_transcription": candidate["source_transcription"], "records": records}
    handoff = {"handoff_version": "level057-allocation-handoff.1", "wbs_id": "2.3.1.2.1",
               "catalog_workbook_id": entry["workbook_id"], "catalog_role": entry["catalog_role"],
               "existing_level057_records": 0, "existing_level057_workbook_entities": 0,
               "printed_attacks": 796, "silent_formations_not_events": 56,
               "proposed_component_partition": list("ABCDEFGHI"), "canonical_ids_allocated": False,
               "admitted": False,
               "required_decisions": ["Set count policy for sounded minor full iiø preparatory strikes before runtime work.",
                   "Allocate stable identities after current registry reservations are sealed.",
                   "Set pick/timing/accent and A-blues pass-four contacts before native import or admission."]}
    return proposal, handoff


def products(root: Path) -> dict[str, object]:
    candidate, foundation, registry = read_inputs(root)
    proposal, handoff = project(candidate, foundation, registry)
    manifest = {"manifest_version": "level057-input-pins.1", "inputs": [
        {"path": rel, "bytes": (root / rel).stat().st_size, "sha256": sha} for rel, sha in INPUTS.items()]}
    summary = {"summary_version": "level057-schema1-unallocated-summary.1",
               "proposal_sha256": digest(encoded(proposal)), "handoff_sha256": digest(encoded(handoff)),
               "printed_attacks": 796, "silent_formations": 56, "native_run": False,
               "runtime_eligible": False, "admitted": False}
    return {"field-proposal.json": proposal, "allocation-handoff.json": handoff,
            "input-manifest.json": manifest, "summary.json": summary}


def run(mode: str, root: Path) -> None:
    built = products(root)
    out = root / OUT_REL
    part = root
    for component in OUT_REL.parts:
        part /= component
        if part.is_symlink():
            raise ValueError("output symlink path")
    if mode == "build":
        out.mkdir(parents=True, exist_ok=True)
        for name, value in built.items():
            (out / name).write_bytes(encoded(value))
    else:
        for name, value in built.items():
            path = out / name
            if path.is_symlink() or path.read_bytes() != encoded(value):
                raise ValueError(f"output drift: {name}")
    print(f"LEVEL57 {mode.upper()} PASS attacks=796 silent=56 admitted=false")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("build", "verify"))
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    run(args.mode, args.root.resolve())


if __name__ == "__main__":
    main()
