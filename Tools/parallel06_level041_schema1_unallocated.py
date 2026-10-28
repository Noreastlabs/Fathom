#!/usr/bin/env python3
"""Project sealed Level 41 source contacts to nonimportable schema1-shaped fields."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from parallel_07_level041_whole_candidate import build_candidate


ROOT = Path(__file__).resolve().parents[1]
OUT_REL = Path("Build/parallel-06/level041-schema1-unallocated-r01")
INPUTS = {
    "Build/parallel-07/2.3.1.1.1-level041-whole-r01/candidate.json": "e639f86c4ff07232ae32563bdc382159f9219fafc7567bab26b6d308029c655a",
    "Tools/parallel_07_level041_whole_candidate.py": "c00ae0ea3a88c9fb95ad1ccd2a887ce057e3429eea26644b40f5b8ab0621161e",
    "Content/controls/curriculum-v1/package.json": "766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255",
    "Content/controls/curriculum-v1/identity-registry.json": "5d265859e1e8a5a530a0e53d88b019a1c920f3bba6cccb4ef0fef2f7640007e5",
    "Results/primary/20260912T100538Z-2.1.1.2.1-r02-evidence/schema-freeze.json": "0659fa962a5c933a2bcf3045772b6fe5b05b4deefb3511f5dcb68af51088de95",
}
COUNTS = {"vertical_positions": (5, 120), "shared_anchor_seams": (4, 120),
          "linked_zigzag": (2, 120), "parallel_color_comparisons": (10, 60)}
OPEN = {"E": (1, 40), "A": (2, 45), "D": (3, 50), "G": (4, 55),
        "B": (5, 59), "e": (6, 64)}
PITCH_CLASS = {"A": 9, "B": 11, "C": 0, "C#": 1, "D": 2,
               "E": 4, "F#": 6, "G": 7}
MINOR = {"A": "1", "C": "b3", "D": "4", "E": "5", "G": "b7"}
MAJOR = {"A": "1", "B": "2", "C#": "3", "E": "5", "F#": "6"}


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
    freeze = json.loads(raw[list(INPUTS)[4]])
    if (freeze.get("decision") != "Technical schema1 FROZEN"
            or freeze.get("schema_version") != "1.0.0-curriculum-candidate"):
        raise ValueError("schema freeze drift")
    return candidate, json.loads(raw[list(INPUTS)[2]]), json.loads(raw[list(INPUTS)[3]])


def identity_boundary(package: dict, registry: dict) -> dict:
    wid = "fg:workbook:000041"
    if any(r.get("legacy_level") == 41 or r.get("workbook_id") == wid
           for r in package["records"]):
        raise ValueError("unexpected canonical Level 41 record")
    if any(e.get("id") == wid for e in registry["entities"]):
        raise ValueError("unexpected Level 41 registry entity")
    entries = [e for e in package["workbook_catalog"]["entries"]
               if e.get("workbook_id") == wid]
    if len(entries) != 1:
        raise ValueError("Level 41 catalog identity drift")
    entry = entries[0]
    if (entry.get("conversion_status") != "not_converted"
            or entry.get("whole_workbook_complete") is not False
            or entry.get("admitted") is not False
            or entry.get("runtime_eligible") is not False
            or entry.get("representative_item_id") is not None):
        raise ValueError("Level 41 source-only catalog drift")
    return entry


def event(source: dict, module: str, item_ordinal: int, event_ordinal: int,
          refs: object, degrees: dict) -> dict:
    if source["onset_q"] is not None or source["duration_q"] is not None:
        raise ValueError("source event timing drift")
    string, fret, tone, degree = (source[k] for k in ("string", "fret", "tone", "degree"))
    if (string not in OPEN or type(fret) is not int or fret < 0
            or tone not in PITCH_CLASS or degrees.get(tone) != degree
            or source["finger"] not in (1, 2, 3, 4)):
        raise ValueError("source note/degree/TAB drift")
    string_number, base = OPEN[string]
    midi = base + fret
    if midi % 12 != PITCH_CLASS[tone]:
        raise ValueError("source note/TAB pitch mismatch")
    return {
        "source_event": source, "source_module": module,
        "source_item_ordinal": item_ordinal, "source_event_ordinal": event_ordinal,
        "source_refs": refs, "performed_result": None,
        "schema1_fields": {
            "event_id": None, "kind": "note", "attack": None,
            "spelling": tone, "midi": midi, "string": string_number,
            "fret": fret, "finger": source["finger"],
            "degree_contexts": {}, "onset_q": None, "duration_q": None,
            "tie_from": None,
        },
    }


def source_units(candidate: dict, module: str) -> list[dict]:
    data = candidate["modules"][module]
    if module == "vertical_positions":
        return [{"events": x["events"], "source_item": {k: v for k, v in x.items() if k != "events"},
                 "source_refs": x["source_refs"], "degrees": MINOR}
                for x in data["positions"]]
    if module == "shared_anchor_seams":
        return [{"events": x["events"], "source_item": {k: v for k, v in x.items() if k != "events"},
                 "source_refs": x["source_refs"], "degrees": MINOR}
                for x in data["seams"]]
    if module == "linked_zigzag":
        return [{"events": [e for segment in data[direction]["route"] for e in segment["events"]],
                 "source_item": {"direction": direction, "route": [
                     {k: v for k, v in segment.items() if k != "events"}
                     for segment in data[direction]["route"]],
                     "transitions": data[direction]["transitions"],
                     "pdf_layout_exception": data[direction]["pdf_layout_exception"],
                     "turn_rearticulated": data["turn_rearticulated"]},
                 "source_refs": [segment["source_refs"] for segment in data[direction]["route"]],
                 "event_refs": [segment["source_refs"] for segment in data[direction]["route"]
                                for _ in segment["events"]],
                 "degrees": MINOR}
                for direction in ("forward", "reverse")]
    if module == "parallel_color_comparisons":
        return [{"events": phrase["events"],
                 "source_item": {"pair_position": pair["position"], "color": phrase["color"],
                                 "raw_rows": phrase["raw_rows"],
                                 "pdf_raw_rows": pair["pdf_raw_rows"],
                                 "pdf_source_ref": pair["pdf_source_ref"],
                                 "silence_between_phrases_beats": pair["silence_between_phrases_beats"],
                                 "silence_is_instruction_not_note_event": pair["silence_is_instruction_not_note_event"]},
                 "source_refs": [phrase["source_ref"], pair["pdf_source_ref"]],
                 "degrees": MAJOR if phrase["color"] == "major" else MINOR}
                for pair in data["pairs"] for phrase in pair["phrases"]]
    raise ValueError("unknown module")


def project(candidate: dict, package: dict, registry: dict) -> tuple[dict, dict]:
    catalog = identity_boundary(package, registry)
    if (candidate.get("schema") != "fathom-level041-whole-detached-candidate-v1"
            or candidate.get("wbs_id") != "2.3.1.1.1" or candidate.get("level") != 41
            or candidate.get("key") != "A" or candidate.get("written_workout_note_count") != 420
            or candidate.get("minor_pentatonic") != MINOR
            or candidate.get("major_comparison") != MAJOR
            or any(candidate.get(k) is not None for k in
                   ("canonical_item_id", "canonical_variant_id", "onset_q", "duration_q", "fixed_bpm", "note_per_click"))
            or any(candidate.get(k) is not False for k in
                   ("whole_workbook_complete", "imported", "runtime_eligible", "runtime_admitted", "admitted"))
            or set(candidate.get("modules", {})) != set(COUNTS)):
        raise ValueError("whole Level 41 source/boundary drift")
    cards = candidate["random_entry_cards"]
    if (len(cards) != 10 or [c["card"] for c in cards] != list(range(1, 11))
            or any(c["authored_phrase_events"] is not None
                   or c["counted_in_written_workout"] is not False
                   or c["requested_phrase_note_count"] != 6
                   or not c["source_refs"] for c in cards)):
        raise ValueError("random-entry card authorship drift")
    for card in cards:
        for endpoint in (card["start"], card["required_resolution"]):
            event({**endpoint, "finger": 1, "onset_q": None, "duration_q": None},
                  "random_entry_endpoint", card["card"], 0, card["source_refs"], MINOR)
        if card["required_resolution"]["degree"] != "1":
            raise ValueError("random-entry resolution drift")
    records = []
    for module, (item_count, note_count) in COUNTS.items():
        units = source_units(candidate, module)
        if len(units) != item_count or candidate["modules"][module]["note_count"] != note_count:
            raise ValueError("module item/count drift")
        events, variants = [], []
        expected_per_item = {"vertical_positions": 24, "shared_anchor_seams": 30,
                             "linked_zigzag": 60, "parallel_color_comparisons": 6}[module]
        for item_ordinal, unit in enumerate(units, 1):
            if len(unit["events"]) != expected_per_item or not unit["source_refs"]:
                raise ValueError("source unit/contact count drift")
            start = len(events) + 1
            for event_ordinal, source in enumerate(unit["events"], 1):
                refs = unit.get("event_refs", [unit["source_refs"]] * len(unit["events"]))[event_ordinal - 1]
                events.append(event(source, module, item_ordinal, event_ordinal,
                                    refs, unit["degrees"]))
            variants.append({"id": None, "source_item_ordinal": item_ordinal,
                             "source_item": unit["source_item"],
                             "source_event_ordinals": list(range(start, len(events) + 1)),
                             "event_ids": None, "runtime_eligible": False})
        if len(events) != note_count:
            raise ValueError("module note count drift")
        records.append({"source_component": module, "identity_state": "unallocated",
                        "source_item_count": item_count,
                        "schema1_fields": {
                            "id": None, "workbook_id": None, "module_id": None,
                            "legacy_level": 41, "title": f"Level 41 {module.replace('_', ' ')}",
                            "kind": "mixed", "content_revision": None, "lineage": None,
                            "runtime_eligible": False, "source_refs": None,
                            "events": events, "variants": variants,
                            "resource_requirements": [],
                            "timing": {"status": "unresolved", "unit": "quarter", "fixed_bpm": None},
                            "ambiguities": ["canonical identities and lineage unallocated",
                                            "numeric onset/duration and click mapping unresolved",
                                            "D/U passes and random-entry phrases remain instructions, not additional authored contacts"],
                        }})
    if sum(len(r["schema1_fields"]["events"]) for r in records) != 420:
        raise ValueError("whole written contact count drift")
    zig = candidate["modules"]["linked_zigzag"]
    if (zig["turn_rearticulated"] != "e17"
            or len(zig["forward"]["route"]) != 5
            or len(zig["reverse"]["route"]) != 5):
        raise ValueError("zigzag route/turn drift")
    if len(candidate["pdf_layout_exceptions"]) != 3:
        raise ValueError("PDF exception drift")
    proposal = {
        "proposal_version": "level041-unallocated-schema1-fields.1", "wbs_id": "2.3.1.1.1",
        "classification": "Build-only, nonimportable schema1 field proposal",
        "legacy_level": 41, "canonical_ids_allocated": False,
        "schema1_importable": False, "whole_workbook_complete": False,
        "runtime_eligible": False, "admitted": False,
        "counts": {"provisional_components": 4, "source_items": 21,
                   "written_note_contacts": 420, "random_entry_cards": 10,
                   "by_module": {k: {"items": i, "notes": n} for k, (i, n) in COUNTS.items()}},
        "source": candidate["source"], "source_catalog_level": catalog,
        "source_instructions": candidate["source_instructions"],
        "source_position_numbering": candidate["position_numbering"],
        "source_minor_pentatonic": MINOR, "source_major_comparison": MAJOR,
        "source_pdf_layout_exceptions": candidate["pdf_layout_exceptions"],
        "source_random_entry_cards": cards, "source_pending": candidate["pending"],
        "records": records,
    }
    handoff = {
        "handoff_version": "level041-allocation-handoff.1", "wbs_id": "2.3.1.1.1",
        "catalog_workbook_id": catalog["workbook_id"],
        "existing_level041_records": 0, "existing_level041_workbook_entities": 0,
        "source_items": 21, "written_note_contacts": 420,
        "random_entry_cards_without_authored_phrases": 10,
        "canonical_ids_allocated": False, "admitted": False,
        "required_decisions": [
            "Allocate stable workbook/module/item/event/variant identities and revision lineage.",
            "Resolve numeric onset/duration, fixed BPM, pick attacks and click mapping.",
            "Review all 420 printed contacts, route transitions, turn rearticulation and PDF layout exceptions.",
            "Keep ten random-entry cards as endpoint instructions until actual phrases are authored and reviewed.",
            "Complete musical correctness and Curriculum review before native import.",
        ],
    }
    return proposal, handoff


def products(root: Path) -> dict[str, object]:
    candidate, package, registry = read_inputs(root)
    proposal, handoff = project(candidate, package, registry)
    manifest = {"manifest_version": "level041-input-pins.1", "inputs": [
        {"path": rel, "bytes": (root / rel).stat().st_size, "sha256": sha}
        for rel, sha in INPUTS.items()]}
    summary = {"summary_version": "level041-schema1-unallocated-summary.1",
               "proposal_sha256": digest(encoded(proposal)),
               "handoff_sha256": digest(encoded(handoff)),
               "source_items": 21, "written_note_contacts": 420,
               "random_entry_cards_without_authored_phrases": 10,
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
    print("LEVEL41 " + mode.upper() + " PASS items=21 contacts=420 cards=10 admitted=false")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("mode", choices=("build", "verify"))
    ap.add_argument("--root", type=Path, default=ROOT)
    args = ap.parse_args()
    run(args.mode, args.root.resolve(strict=True))


if __name__ == "__main__":
    main()
