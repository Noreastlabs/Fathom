#!/usr/bin/env python3
"""Project sealed whole-Level82 source tasks and pitch classes to unallocated fields."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from parallel_07_level082_whole_candidate import build, COUNTS, PC


ROOT = Path(__file__).resolve().parents[1]
OUT_REL = Path("Build/parallel-11/2.3.1.3.1-level082-schema1-unallocated-r01")
INPUTS = {
    "Tools/parallel_07_level082_whole_candidate.py": "6f1976f18666b84e78f5dd47bc9b984ecd4bf8fdb087901e8285cfbc6936f821",
    "Results/parallel-07/conversion/20260923T170449Z-2.3.1.3.1-level082-whole-candidate-r01-results.md": "fc74de3f80bb9c086a78123a3f2ec305c44745409edf558aa88cdd23a54bfe77",
    "Build/parallel-07/2.3.1.3.1-level082-whole-r01/level082_whole_candidate.json": "a72620baf62612f1e10fef7d65bf3fe7bfdc51500432e223c0e9b13b60e68d7b",
    "Build/parallel-07/2.3.1.3.1-level082-whole-r01/manifest.json": "d7ab132acdfcae674864251c55f241d1cd7a8cb3c2c494b22323cf31cc6ecc64",
    "Content/controls/curriculum-v1/package.json": "766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255",
    "Content/controls/curriculum-v1/identity-registry.json": "5d265859e1e8a5a530a0e53d88b019a1c920f3bba6cccb4ef0fef2f7640007e5",
    "Content/controls/curriculum-v1/generation.json": "fc6cec9f9d67eb82c97c5f4c3fb95d285178fb7fce7bd147d9ae0296d21b4c1c",
    "Notes/music/guitar project/TXT version/Guitar_Exercises_Section_XI_Level_82_Walking_Bass_Chord_Melody_Chromatic_Approach_Bass_Lines_Bass_Substitutions_and_Solo_Guitar_Arrangements.txt": "075685fca4a69a33860abfddddac2ec47ff744c245e4c474f8c8a9715f355318",
    "Notes/music/guitar project/PDF version/Guitar_Exercises_Section_XI_Level_82_Walking_Bass_Chord_Melody_Chromatic_Approach_Bass_Lines_Bass_Substitutions_and_Solo_Guitar_Arrangements.pdf": "e12a87917b2a3537922e56e0139574627a59dbd7b4959073cfbf87a4a8846005",
    "Results/parallel-01/exercises/inventory/20260922T180500Z-2.3-curriculum-v1-source-inventory-evidence/curriculum-source-map.json": "bad5581a04f43ba8baf14db430449e1ccff5cf88f0f7e42198328073b27053d6",
}
TASK_COUNTS = {"A": 9, "B": 9, "C": 11, "D": 9, "E": 7, "F": 7, "G": 7, "H": 33, "I": 33, "J": 9}
PITCH_COUNTS = {"A": 104, "B": 56, "C": 21, "D": 0, "E": 102, "F": 102,
                "G": 102, "H": 64, "I": 64, "J": 0}
UNRESOLVED = [
    "Canonical workbook/module/item/event/variant IDs and lineage are not allocated.",
    "Printed pitch class has no authored octave, guitar string/fret or sounding MIDI binding.",
    "No numeric note onset/duration, fixed BPM, inner chord voicing or performed pass allocation is established.",
    "Declared 1,392 workload events exceed 615 printed pitch entries; unprinted contacts are not synthesized.",
    "No observed recovery, scores, mastery, native import or Curriculum admission is established.",
]


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
    c = json.loads(raw["Build/parallel-07/2.3.1.3.1-level082-whole-r01/level082_whole_candidate.json"])
    if c != build(root):
        raise ValueError("P07 sealed Level82 candidate differs from original TXT/PDF/source-map replay")
    foundation = json.loads(raw["Content/controls/curriculum-v1/package.json"])
    registry = json.loads(raw["Content/controls/curriculum-v1/identity-registry.json"])
    generation = json.loads(raw["Content/controls/curriculum-v1/generation.json"])
    if len(foundation["records"]) != 659 or generation["records"] != 659:
        raise ValueError("current659 foundation drift")
    return c, foundation, registry


def identity_boundary(foundation: dict, registry: dict) -> dict:
    workbook = "fg:workbook:000082"
    if any(r.get("legacy_level") == 82 or r.get("workbook_id") == workbook for r in foundation["records"]):
        raise ValueError("unexpected canonical Level82 record")
    if any(e.get("id") == workbook for e in registry["entities"]):
        raise ValueError("unexpected Level82 registry entity")
    entry = next((e for e in foundation["workbook_catalog"]["entries"] if e.get("workbook_id") == workbook), None)
    if (not entry or entry.get("representative_item_id") is not None or entry.get("whole_workbook_complete") is not False
            or entry.get("admitted") is not False or entry.get("conversion_status") != "not_converted"):
        raise ValueError("Level82 source-only catalog drift")
    return entry


def validate_candidate(c: dict) -> None:
    if (c.get("schema") != "fathom.detached_curriculum_source_candidate.v1" or c.get("level") != 82
            or c.get("section") != "XI" or c.get("wbs_owner") != "2.3.1.3.1"
            or c.get("status") != "candidate_only" or c.get("admission_claim") is not False):
        raise ValueError("Level82 source scope/admission drift")
    if c["module_workload_declared"] != COUNTS or c["declared_workload_total"] != 1392:
        raise ValueError("1392 declared workload drift")
    if len(c["tasks"]) != 134 or dict(Counter(t["module"] for t in c["tasks"])) != TASK_COUNTS:
        raise ValueError("134 printed task count drift")
    if len(c["explicit_pitch_events"]) != 615 or dict(Counter(e["module"] for e in c["explicit_pitch_events"])) != {k: v for k, v in PITCH_COUNTS.items() if v}:
        raise ValueError("615 printed pitch count drift")
    if list(c["module_count_comparison"]) != list(COUNTS):
        raise ValueError("module comparison order drift")
    for letter, row in c["module_count_comparison"].items():
        if (row["declared_events"] != COUNTS[letter] or row["printed_pitch_entries"] != PITCH_COUNTS[letter]
                or row["difference_not_assignable_to_specific_contacts"] != COUNTS[letter] - PITCH_COUNTS[letter]):
            raise ValueError(f"{letter} declared/printed count distinction drift")
    if len(c["source_archive"]["txt_lines"]) != 355 or len(c["source_archive"]["pdf_pages"]) != 20 or len(c["pdf_tables"]) != 7:
        raise ValueError("whole-source archive/table drift")
    if [len(c["pdf_tables"][k]["rows"]) for k in ("C", "D", "H1", "H2", "I1", "I2", "J")] != [10, 8, 16, 16, 16, 16, 8]:
        raise ValueError("seven PDF table row drift")
    a = [t for t in c["tasks"] if t["module"] == "A" and t["kind"] == "walking_bass_chord_melody_study"]
    if len(a) != 8 or [t["fields"]["pdf_status"] for t in a] != ["exact_printed_study"] * 4 + ["txt_only_study"] * 4:
        raise ValueError("A PDF/TXT study coverage drift")
    if len(c["source_tensions"]) != 5 or len(c["unresolved_performance_fields"]) != 10:
        raise ValueError("source tension/performance uncertainty drift")
    task_keys = {t["local_key"] for t in c["tasks"]}
    if len(task_keys) != 134 or any(t["canonical_task_id"] is not None or t["observed_score"] is not None or t["observed_performance"] is not None for t in c["tasks"]):
        raise ValueError("invented task identity/performance")
    event_keys = set()
    for event in c["explicit_pitch_events"]:
        if event["local_key"] in event_keys:
            raise ValueError("duplicate source pitch local key")
        event_keys.add(event["local_key"])
        if (event["pitch_name"] not in PC or event["pitch_class"] != PC[event["pitch_name"]]
                or any(event[k] is not None for k in ("octave", "string", "fret", "onset_q", "duration_q", "canonical_event_id", "performed_result"))):
            raise ValueError("invented source pitch binding/timing/performance")
        if sum(event["local_key"].startswith(key + "-") for key in task_keys) != 1:
            raise ValueError("source pitch/task linkage drift")
    if [(e["pitch_name"], e["pitch_class"]) for e in c["explicit_pitch_events"] if e["pitch_name"] == "F##"] != [("F##", 7)]:
        raise ValueError("F## spelling drift")
    h = [t for t in c["tasks"] if t["module"] == "H" and t["kind"] == "arrangement_bar"]
    i = [t for t in c["tasks"] if t["module"] == "I" and t["kind"] == "capstone_bar"]
    if len(h) != len(i) or len(h) != 32:
        raise ValueError("H/I structural bar count drift")
    for h_task, i_task in zip(h, i, strict=True):
        if h_task["local_key"] == i_task["local_key"] or any(h_task["fields"][k] != i_task["fields"][k] for k in ("chord", "bass", "melody")):
            raise ValueError("H/I structural parity/occurrence drift")


def _event_field(event: dict) -> dict:
    return {
        "source_pitch": event,
        "schema1_fields": {
            "event_id": None, "kind": "note", "spelling": event["pitch_name"],
            "pitch_class": event["pitch_class"], "midi": None, "octave": None,
            "string": None, "fret": None, "finger": None, "attack": None,
            "onset_q": None, "duration_q": None, "pick": None, "performed": None,
        },
    }


def project(c: dict, foundation: dict, registry: dict) -> tuple[dict, dict]:
    validate_candidate(c)
    entry = identity_boundary(foundation, registry)
    records = []
    all_task_proposals = []
    for letter in COUNTS:
        tasks = [t for t in c["tasks"] if t["module"] == letter]
        events = [e for e in c["explicit_pitch_events"] if e["module"] == letter]
        event_fields = [_event_field(e) for e in events]
        task_proposals = []
        for task in tasks:
            ordinals = [j for j, event in enumerate(events, 1) if event["local_key"].startswith(task["local_key"] + "-")]
            projected = {"source_task": task, "schema1_fields": {
                "id": None, "workbook_id": None, "module_id": None, "legacy_level": 82,
                "kind": "task", "source_local_key": task["local_key"],
                "content_revision": None, "lineage": None, "runtime_eligible": False,
                "source_event_ordinals": ordinals, "event_ids": None,
                "observed_performance": None, "observed_score": None,
            }}
            task_proposals.append(projected)
            all_task_proposals.append(projected)
        records.append({
            "source_component": letter, "identity_state": "unallocated",
            "declared_workload_events": COUNTS[letter],
            "printed_pitch_entries": PITCH_COUNTS[letter],
            "unassigned_workload_difference": COUNTS[letter] - PITCH_COUNTS[letter],
            "task_proposals": task_proposals,
            "schema1_fields": {
                "id": None, "workbook_id": None, "module_id": None, "legacy_level": 82,
                "title": f"Level 82 component {letter}", "kind": "mixed",
                "content_revision": None, "lineage": None, "status": "unallocated_source_projection",
                "runtime_eligible": False, "admitted": False,
                "source_refs": sorted({f"L82-TXT-L{t['source']['txt_line']}" for t in tasks}
                                      | {f"L82-PDF-p{t['source']['pdf_page']}" for t in tasks if t["source"].get("pdf_page") is not None}),
                "events": event_fields, "variants": [], "resource_requirements": [],
                "timing": {"status": "unresolved", "unit": "quarter", "fixed_bpm": None},
                "ambiguities": UNRESOLVED,
            },
        })
    proposal = {
        "proposal_version": "level082-unallocated-schema1-fields.1", "wbs_id": "2.3.1.3.1",
        "classification": "Build-only, nonimportable schema1 field proposal", "legacy_level": 82,
        "canonical_ids_allocated": False, "schema1_importable": False,
        "whole_workbook_complete": False, "runtime_eligible": False, "admitted": False,
        "mastery_observed": None,
        "counts": {"provisional_components": 10, "source_tasks": 134, "explicit_pitch_entries": 615,
                   "declared_workload_events": 1392,
                   "unassigned_workload_difference": 1392 - 615},
        "source_map": c["source_map"], "source_pins": c["source_pins"],
        "source_archive": c["source_archive"], "pdf_tables": c["pdf_tables"],
        "module_workload_declared": c["module_workload_declared"],
        "module_count_comparison": c["module_count_comparison"],
        "source_tensions": c["source_tensions"],
        "unresolved_performance_fields": c["unresolved_performance_fields"],
        "task_field_proposals": all_task_proposals, "records": records,
    }
    handoff = {
        "handoff_version": "level082-allocation-handoff.1", "wbs_id": "2.3.1.3.1",
        "catalog_workbook_id_read_only": entry["workbook_id"], "existing_level082_records": 0,
        "existing_level082_workbook_entities": 0, "source_tasks": 134,
        "explicit_pitch_entries": 615, "declared_workload_events": 1392,
        "proposed_component_partition": list(COUNTS), "canonical_ids_allocated": False, "admitted": False,
        "required_decisions": [
            "Review eight TXT Module A studies versus four PDF study pages and preserve TXT-only coverage.",
            "Allocate stable identities and lineage only through the canonical owner.",
            "Keep H arrangement and I capstone occurrences distinct despite matching structural bars.",
            "Resolve octave, string/fret, timing, inner voicings and 777 unassigned workload events before native admission.",
            "Require observed performance, recovery, score and mastery evidence before completion claims.",
        ],
    }
    return proposal, handoff


def products(root: Path) -> dict[str, object]:
    c, foundation, registry = read_inputs(root)
    proposal, handoff = project(c, foundation, registry)
    manifest = {"manifest_version": "level082-schema1-input-pins.1", "inputs": [
        {"path": rel, "bytes": (root / rel).stat().st_size, "sha256": sha} for rel, sha in INPUTS.items()]}
    summary = {"summary_version": "level082-schema1-unallocated-summary.1",
               "proposal_sha256": digest(encoded(proposal)), "handoff_sha256": digest(encoded(handoff)),
               "source_tasks": 134, "explicit_pitch_entries": 615, "declared_workload_events": 1392,
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
    print(f"LEVEL82 {mode.upper()} PASS tasks=134 printed_pitch=615 declared=1392 admitted=false")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("build", "verify"))
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    run(args.mode, args.root.resolve())


if __name__ == "__main__":
    main()
