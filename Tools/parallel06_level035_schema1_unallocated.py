#!/usr/bin/env python3
"""Project sealed Level35 lane source into detached unallocated schema1 fields."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from curriculum_level035_whole_candidate import build_candidate


ROOT = Path(__file__).resolve().parents[1]
OUT_REL = Path("Build/parallel-06/level035-schema1-unallocated-r01")
INPUTS = {
    "Build/parallel-08/2.3.1.1.1-level035-whole-r01/level035-candidate-a.json": "f7a392055617edcd736270afe2d9c3b30a2a9e3a18a9ca687bf62e402eda7f71",
    "Tools/curriculum_level035_whole_candidate.py": "e649da956e608c008cc79e6ddf103fdf38b40c71dcfaa93d57c305b7b4736d8f",
    "Content/controls/curriculum-v1/package.json": "766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255",
    "Content/controls/curriculum-v1/identity-registry.json": "5d265859e1e8a5a530a0e53d88b019a1c920f3bba6cccb4ef0fef2f7640007e5",
    "Results/primary/20260912T100538Z-2.1.1.2.1-r02-evidence/schema-freeze.json": "0659fa962a5c933a2bcf3045772b6fe5b05b4deefb3511f5dcb68af51088de95",
}
COUNTS = {"A": {"sounding": 72, "pick_attacks": 72},
          "B": {"sounding": 144, "pick_attacks": 96},
          "C": {"sounding": 96, "pick_attacks": 96},
          "D": {"sounding": 72, "pick_attacks": 72}}
ITEM_COUNTS = {"A": 6, "B": 24, "C": 6, "D": 12}
OPEN = {"E": (1, 40), "A": (2, 45), "D": (3, 50), "G": (4, 55),
        "B": (5, 59), "e": (6, 64)}
PITCH_CLASS = {"A": 9, "B": 11, "C#": 1, "E": 4, "F#": 6}
DEGREES = {1: "A", 2: "B", 3: "C#", 5: "E", 6: "F#"}


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
    if candidate != build_candidate(root):
        raise ValueError("sealed candidate differs from original TXT/PDF replay")
    package = json.loads(raw[list(INPUTS)[2]])
    registry = json.loads(raw[list(INPUTS)[3]])
    freeze = json.loads(raw[list(INPUTS)[4]])
    if freeze.get("decision") != "Technical schema1 FROZEN" or freeze.get("schema_version") != "1.0.0-curriculum-candidate":
        raise ValueError("schema freeze drift")
    return candidate, package, registry


def identity_boundary(package: dict, registry: dict) -> dict:
    wid = "fg:workbook:000035"
    if any(r.get("legacy_level") == 35 or r.get("workbook_id") == wid
           for r in package["records"]):
        raise ValueError("unexpected canonical Level35 record")
    if any(e.get("id") == wid for e in registry["entities"]):
        raise ValueError("unexpected Level35 registry entity")
    entries = [e for e in package["workbook_catalog"]["entries"]
               if e.get("workbook_id") == wid]
    if len(entries) != 1:
        raise ValueError("Level35 catalog identity drift")
    entry = entries[0]
    if (entry.get("conversion_status") != "not_converted"
            or entry.get("whole_workbook_complete") is not False
            or entry.get("admitted") is not False
            or entry.get("runtime_eligible") is not False
            or entry.get("representative_item_id") is not None):
        raise ValueError("Level35 source-only catalog drift")
    return entry


def event(source: dict, module: str, item_ordinal: int, event_ordinal: int,
          source_ref: dict) -> dict:
    if source["onset_q"] is not None or source["duration_q"] is not None:
        raise ValueError("source event timing drift")
    string, fret, note, degree = (source[k] for k in ("string", "fret", "note", "degree"))
    if (string not in OPEN or type(fret) is not int or fret < 0
            or note not in PITCH_CLASS or DEGREES.get(degree) != note):
        raise ValueError("source note/degree/TAB drift")
    string_number, base = OPEN[string]
    midi = base + fret
    if midi % 12 != PITCH_CLASS[note]:
        raise ValueError("source note/TAB pitch mismatch")
    articulation = source["articulation"]
    pick = source["pick_attack"]
    if (articulation == "picked" and pick is not True) or (articulation in
            ("slide_up_arrival", "slide_down_arrival") and pick is not False):
        raise ValueError("source pick/slide articulation drift")
    if articulation not in ("picked", "slide_up_arrival", "slide_down_arrival"):
        raise ValueError("unsupported source articulation")
    return {
        "source_event": source, "source_module": module,
        "source_item_ordinal": item_ordinal, "source_event_ordinal": event_ordinal,
        "source_ref": source_ref, "performed_result": None,
        "schema1_fields": {
            "event_id": None, "kind": "note", "attack": "picked" if pick else None,
            "spelling": note, "midi": midi, "string": string_number,
            "fret": fret, "finger": source["finger"],
            "degree_contexts": {}, "onset_q": None, "duration_q": None,
            "tie_from": None,
        },
    }


def project(candidate: dict, package: dict, registry: dict) -> tuple[dict, dict]:
    catalog = identity_boundary(package, registry)
    if (candidate.get("schema") != "fathom.detached.curriculum.level035.whole.v1"
            or candidate.get("wbs") != "2.3.1.1.1"
            or candidate.get("level") != 35 or candidate.get("key") != "A major pentatonic"
            or candidate.get("transposed") is not False
            or candidate.get("whole_level_source_covered") is not True
            or candidate.get("whole_level_complete") is not False
            or candidate.get("module_counts") != COUNTS
            or candidate.get("totals") != {"sounding": 384, "pick_attacks": 336,
                                          "unpicked_slide_arrivals": 48}
            or list(candidate.get("modules", {})) != list(COUNTS)):
        raise ValueError("whole Level35 source scope/count drift")
    if candidate.get("admitted") is not False or candidate.get("runtime_imported") is not False or candidate.get("canonical_id") is not None:
        raise ValueError("source admission/identity drift")
    if candidate["source_discrepancies"] != []:
        raise ValueError("unexpected source discrepancies")
    if (candidate["timing"] != {"fixed_bpm": None, "numeric_duration": None,
                                "numeric_onset": None,
                                "slide_destination_on_subdivision": True}):
        raise ValueError("source timing boundary drift")
    if (candidate["picking"]["separate_starts"] != ["D", "U"]
            or candidate["picking"]["strict_alternate"] is not True
            or candidate["picking"]["slide_arrival_new_pick_attack"] is not False
            or candidate["picking"]["turn_repeated_high_e_fret"] != 5):
        raise ValueError("source picking/turn boundary drift")
    modules = candidate["modules"]
    if any(len(modules[m]) != ITEM_COUNTS[m] for m in COUNTS):
        raise ValueError("module item count drift")
    # The printed six-lane atlas is a source claim, not a generated route.
    if [lane["string"] for lane in candidate["lanes"]] != list(OPEN):
        raise ValueError("six-lane atlas order drift")
    for lane in candidate["lanes"]:
        for position in lane["positions"]:
            event(position, "atlas", 0, 0, {"source": "printed_lane_atlas"})
    records = []
    sound_total = pick_total = slide_total = 0
    for module in COUNTS:
        events = []
        variants = []
        for item_ordinal, item in enumerate(modules[module], 1):
            source_ref = {k: v for k, v in item.items() if k.startswith("source_")}
            if not source_ref or not item.get("events"):
                raise ValueError("source item/provenance drift")
            start = len(events) + 1
            for event_ordinal, source in enumerate(item["events"], 1):
                events.append(event(source, module, item_ordinal, event_ordinal, source_ref))
            variants.append({"id": None, "source_item_ordinal": item_ordinal,
                             "source_item": {k: v for k, v in item.items() if k != "events"},
                             "source_event_ordinals": list(range(start, len(events) + 1)),
                             "event_ids": None, "runtime_eligible": False})
            if module == "A" and (len(item["events"]) != 12 or item["no_slide"] is not True
                                  or len(item["stations"]) != 3):
                raise ValueError("A station/shift scope drift")
            if module == "B" and (len(item["events"]) != 6
                                  or item["pick_attack_ordinals"] != [1, 2, 4, 6]
                                  or item["slide_arrival_ordinals"] != [3, 5]
                                  or item["slide_finger"] not in (3, 4)):
                raise ValueError("B seam/slide scope drift")
            if module == "C" and (len(item["events"]) != 16
                                  or item["first_pass_finger"] != 1
                                  or item["no_slide"] is not True
                                  or len(item["targets"]) != 4):
                raise ValueError("C target/mirror scope drift")
            if module == "D" and (len(item["events"]) != 6
                                  or item["route"] != ("forward" if item_ordinal <= 6 else "reverse")):
                raise ValueError("D snake route scope drift")
        module_picks = sum(e["source_event"]["pick_attack"] for e in events)
        if (len(events) != COUNTS[module]["sounding"]
                or module_picks != COUNTS[module]["pick_attacks"]):
            raise ValueError("module sounding/pick count drift")
        sound_total += len(events)
        pick_total += module_picks
        slide_total += sum(not e["source_event"]["pick_attack"] for e in events)
        records.append({
            "source_component": module, "identity_state": "unallocated",
            "source_item_count": len(modules[module]),
            "schema1_fields": {
                "id": None, "workbook_id": None, "module_id": None,
                "legacy_level": 35, "title": f"Level 35 Module {module}", "kind": "mixed",
                "content_revision": None, "lineage": None, "runtime_eligible": False,
                "source_refs": None, "events": events, "variants": variants,
                "resource_requirements": [],
                "timing": {"status": "unresolved", "unit": "quarter", "fixed_bpm": None},
                "ambiguities": ["canonical identities and lineage unallocated",
                                "numeric onset/duration, fixed BPM and click mapping unresolved",
                                "D/U passes and C upper-endpoint mirror remain guidance, not extra events"],
            },
        })
    if (sound_total, pick_total, slide_total) != (384, 336, 48):
        raise ValueError("whole sounding/pick/slide parity drift")
    d_events = records[-1]["schema1_fields"]["events"]
    if [(e["source_event"]["string"], e["source_event"]["fret"]) for e in d_events[35:37]] != [("e", 5), ("e", 5)]:
        raise ValueError("D high-e turn drift")
    proposal = {
        "proposal_version": "level035-unallocated-schema1-fields.1", "wbs_id": "2.3.1.1.1",
        "classification": "Build-only, nonimportable schema1 field proposal",
        "legacy_level": 35, "canonical_ids_allocated": False,
        "schema1_importable": False, "whole_workbook_complete": False,
        "runtime_eligible": False, "admitted": False,
        "counts": {"provisional_components": 4, "source_items": 48,
                   "sounding_events": 384, "picked_attacks": 336,
                   "unpicked_slide_arrivals": 48, "by_module": COUNTS},
        "source": candidate["source"], "source_catalog_level": catalog,
        "source_lanes": candidate["lanes"], "source_guidance": candidate["guidance"],
        "source_picking": candidate["picking"], "source_timing": candidate["timing"],
        "source_discrepancies": candidate["source_discrepancies"],
        "records": records,
    }
    handoff = {
        "handoff_version": "level035-allocation-handoff.1", "wbs_id": "2.3.1.1.1",
        "catalog_workbook_id": catalog["workbook_id"],
        "existing_level035_records": 0, "existing_level035_workbook_entities": 0,
        "source_items": 48, "sounding_events": 384,
        "picked_attacks": 336, "unpicked_slide_arrivals": 48,
        "canonical_ids_allocated": False, "admitted": False,
        "required_decisions": [
            "Allocate stable workbook/module/item/event/variant identities and revision lineage.",
            "Resolve numeric onset/duration, fixed BPM and click mapping without changing slide-arrival attack semantics.",
            "Review D/U passes, C mirror guidance and D turn before native import.",
            "Complete musical correctness and Curriculum review of all A–D source items.",
        ],
    }
    return proposal, handoff


def products(root: Path) -> dict[str, object]:
    candidate, package, registry = read_inputs(root)
    proposal, handoff = project(candidate, package, registry)
    manifest = {"manifest_version": "level035-input-pins.1", "inputs": [
        {"path": rel, "bytes": (root / rel).stat().st_size, "sha256": sha}
        for rel, sha in INPUTS.items()]}
    summary = {"summary_version": "level035-schema1-unallocated-summary.1",
               "proposal_sha256": digest(encoded(proposal)),
               "handoff_sha256": digest(encoded(handoff)),
               "source_items": 48, "sounding_events": 384,
               "picked_attacks": 336, "unpicked_slide_arrivals": 48,
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
    print("LEVEL35 " + mode.upper() + " PASS items=48 sounding=384 picked=336 slides=48 admitted=false")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("mode", choices=("build", "verify"))
    ap.add_argument("--root", type=Path, default=ROOT)
    args = ap.parse_args()
    run(args.mode, args.root.resolve(strict=True))


if __name__ == "__main__":
    main()
