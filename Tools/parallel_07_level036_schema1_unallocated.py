#!/usr/bin/env python3
"""Project pinned Level36 source evidence into detached unallocated schema1 fields."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = Path("Build/parallel-07/2.3.1.1.1-level036-schema1-unallocated-r01")
STEM = "Scale_Exercises_Section_IV_Level_36_Major_Pentatonic_Expressive_Articulation_Legato_Slides_Bends_Releases_and_Vibrato_Fixed_Key_A"
TXT = f"Notes/music/guitar project/TXT version/{STEM}.txt"
PDF = f"Notes/music/guitar project/PDF version/{STEM}.pdf"
UPSTREAM_TOOL = "Tools/curriculum_level036_whole_candidate.py"
UPSTREAM = "Build/parallel-11/2.3.1.1.1-level036-whole-r01/candidate-a.json"
MAP = "Results/parallel-01/exercises/inventory/20260922T180500Z-2.3-curriculum-v1-source-inventory-evidence/curriculum-source-map.json"
PACKAGE = "Content/controls/curriculum-v1/package.json"
REGISTRY = "Content/controls/curriculum-v1/identity-registry.json"
GENERATION = "Content/controls/curriculum-v1/generation.json"
INPUTS = {
    UPSTREAM_TOOL: "94c68f6aae8430398e7baa829a21096ded67e335a7fff5e3290799ba8169d15d",
    UPSTREAM: "c29a6e408d13e2d20bf047b8466904d52759af36bd4427f9ffde3ebdd5c8197a",
    TXT: "4aee029db1f594b01963374e1269dba273fd82ae8e24d0e24df551cb442ef828",
    PDF: "ecdb6d4b249ac09116647f9b278413727bab6cf4b2557e094d9ee34741c11a43",
    MAP: "bad5581a04f43ba8baf14db430449e1ccff5cf88f0f7e42198328073b27053d6",
    PACKAGE: "766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255",
    REGISTRY: "5d265859e1e8a5a530a0e53d88b019a1c920f3bba6cccb4ef0fef2f7640007e5",
    GENERATION: "fc6cec9f9d67eb82c97c5f4c3fb95d285178fb7fce7bd147d9ae0296d21b4c1c",
}
COUNTS = {"A_pick_attacks": 60, "A_root_vibrato_holds": 8, "A_sounding_tones": 120,
          "B_pick_attacks": 24, "B_sounding_tones": 120, "C_pick_attacks": 36,
          "D_prebend_pick_attacks": 18, "D_vibrato_pick_attacks": 8,
          "E_pick_attacks": 19, "bend_prebend_cells": 15, "cadences": 5,
          "explicit_legato_slide_tones": 240, "total_pick_attacks": 165}
OPEN_PC = {"E": 4, "A": 9, "D": 2, "G": 7, "B": 11, "e": 4}
PC = {"A": 9, "B": 11, "C#": 1, "E": 4, "F#": 6}
DEG = {"A": 1, "B": 2, "C#": 3, "E": 5, "F#": 6}
STRING_ORDER = ("E", "A", "D", "G", "B", "e")


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def encoded(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError(reason)


def read_inputs(root: Path) -> dict:
    raw = {}
    for rel, expected in INPUTS.items():
        path = root / rel
        require(not path.is_symlink() and path.is_file() and path.resolve().is_relative_to(root), f"unsafe input: {rel}")
        value = path.read_bytes()
        require(digest(value) == expected, f"input drift: {rel}")
        raw[rel] = value
    return {"raw": raw, "candidate": json.loads(raw[UPSTREAM]), "map": json.loads(raw[MAP]),
            "package": json.loads(raw[PACKAGE]), "registry": json.loads(raw[REGISTRY]),
            "generation": json.loads(raw[GENERATION]), "lines": raw[TXT].decode().splitlines()}


def replay_upstream(root: Path, candidate: dict) -> None:
    spec = importlib.util.spec_from_file_location("sealed_level036_builder", root / UPSTREAM_TOOL)
    require(spec is not None and spec.loader is not None, "upstream builder unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    rebuilt = module.build_candidate(root)
    require(rebuilt == candidate, "upstream candidate/source replay drift")


def catalog_boundary(data: dict) -> dict:
    package, registry, generation, source_map = (data[x] for x in ("package", "registry", "generation", "map"))
    workbook = "fg:workbook:000036"
    require(len(package["records"]) == generation["records"] == 659, "current659 foundation drift")
    require(not any(r.get("legacy_level") == 36 or r.get("workbook_id") == workbook for r in package["records"]),
            "Level36 canonical records exist")
    require(not any(e.get("id") == workbook for e in registry["entities"]), "Level36 workbook registry entity exists")
    entry = next((x for x in package["workbook_catalog"]["entries"] if x.get("workbook_id") == workbook), None)
    require(entry is not None and entry.get("catalog_role") == "read_only_source_preservation"
            and entry.get("conversion_status") == "not_converted" and entry.get("review") == "Pending"
            and entry.get("playable_projection", {}).get("status") == "explicitly_empty_unresolved"
            and all(entry.get(k) is False for k in ("runtime_eligible", "runtime_admitted", "imported", "admitted", "whole_workbook_complete")),
            "Level36 source-only catalog boundary drift")
    row = next((x for x in source_map["rows"] if x.get("level") == 36), None)
    require(row is not None and row.get("txt_path") == TXT and row.get("pdf_path") == PDF
            and row.get("txt_sha256") == INPUTS[TXT] and row.get("pdf_sha256") == INPUTS[PDF]
            and row.get("conversion_status") == "not_converted" and row.get("review") == "Pending"
            and row.get("representative_item_id") is None
            and all(row.get(k) is False for k in ("stable_ids_assigned", "runtime_eligible", "imported", "admitted")),
            "Level36 frozen source-map boundary drift")
    return entry


def check_tone(string: str, fret: int, note: str, degree: int) -> None:
    require(string in OPEN_PC and note in PC and DEG[note] == degree and 0 <= fret <= 24
            and (OPEN_PC[string] + fret) % 12 == PC[note], "note/degree/TAB geometry drift")


def validate_candidate(candidate: dict, lines: list[str]) -> None:
    require(candidate.get("schema") == "fathom.level036.detached-source-candidate.1"
            and candidate.get("wbs") == "2.3.1.1.1" and candidate.get("status") == "non_admitted"
            and candidate.get("admitted") is False and candidate.get("counts") == COUNTS
            and candidate.get("key") == "A major pentatonic"
            and candidate.get("notes") == list(PC) and candidate.get("degrees") == [1, 2, 3, 5, 6],
            "Level36 scope/count drift")
    require(all(candidate.get(k) is None for k in ("canonical_id", "exercise_id", "onset_q", "duration_q", "fixed_bpm")),
            "upstream identity/timing authority drift")
    require(candidate["source"]["txt"]["path"] == TXT and candidate["source"]["pdf"]["path"] == PDF
            and candidate["source"]["txt"]["sha256"] == INPUTS[TXT]
            and candidate["source"]["pdf"]["sha256"] == INPUTS[PDF] and len(lines) == 324,
            "source identity drift")
    modules = candidate["modules"]
    require({k: len(v) for k, v in modules.items()} == {
        "A_legato_positions": 5, "B_seam_chains": 4, "C_whole_step_bends": 9,
        "D_prebend_cells": 6, "D_A_root_vibrato_holds": 8, "E_cadences": 5}, "module coverage drift")
    for posno, position in enumerate(modules["A_legato_positions"], 1):
        require(position["position"] == posno and len(position["groups"]) == 12
                and position["pick_attacks"] == 12 and position["sounding_tones"] == 24
                and position["raw_txt"] == lines[40 + 20*(posno-1):59 + 20*(posno-1)]
                and position["raw_pdf_cell"] == position["raw_txt"][8:18], "Module A row/source drift")
        for ordinal, group in enumerate(position["groups"], 1):
            string = STRING_ORDER[ordinal-1] if ordinal <= 6 else STRING_ORDER[12-ordinal]
            require(group["string"] == string and group["articulation"] == ("h" if ordinal <= 6 else "p")
                    and group["pick_attacks"] == 1 and group["sounding_tones"] == 2
                    and all(1 <= f <= 4 for f in group["fingers"]), "Module A group geometry drift")
            for fret, note, degree in zip(group["frets"], group["notes"], group["degrees"], strict=True):
                check_tone(string, fret, note, degree)
    for seamno, seam in enumerate(modules["B_seam_chains"], 1):
        require(seam["seam"] == seamno and len(seam["phrases"]) == 6
                and seam["pick_attacks"] == 6 and seam["sounding_tones"] == 30, "Module B seam drift")
        for index, phrase in enumerate(seam["phrases"]):
            require(phrase["string"] == STRING_ORDER[index] and phrase["pick_attacks"] == 1
                    and phrase["sounding_tones"] == 5 and phrase["articulations"] ==
                    ["pick", "hammer_on", "slide_up", "slide_down", "pull_off"]
                    and re.fullmatch(rf"{phrase['string']}\|\d+h\d+/\d+\\\d+p\d+\|", phrase["tab"]) is not None
                    and phrase["frets"][0] == phrase["frets"][4]
                    and phrase["frets"][1] == phrase["frets"][3]
                    and phrase["frets"][0] < phrase["frets"][1] < phrase["frets"][2],
                    "Module B TAB/route geometry drift")
            for fret, note, degree in zip(phrase["frets"], phrase["notes"], phrase["degrees"], strict=True):
                check_tone(phrase["string"], fret, note, degree)
    for family, attacks in (("C_whole_step_bends", 4), ("D_prebend_cells", 3)):
        for ordinal, site in enumerate(modules[family], 1):
            require(site["site"] == ordinal and site["pick_attacks"] == attacks
                    and len(site["articulation_sequence"]) == attacks
                    and site["target_fret"] == site["source_fret"] + 2
                    and site["tab"].startswith(site["string"] + "|")
                    and f"b({site['target_fret']})" in site["tab"], "bend/prebend site geometry drift")
            check_tone(site["string"], site["source_fret"], site["source_note"], site["source_degree"])
            check_tone(site["string"], site["target_fret"], site["target_note"], site["target_degree"])
    for root in modules["D_A_root_vibrato_holds"]:
        require(root["pick_attacks"] == 1 and root["raw_guidance"] == lines[int(root["txt_ref"].split("L")[-1])-1],
                "root guidance/source drift")
        check_tone(root["string"], root["fret"], root["note"], root["degree"])
    for ordinal, cadence in enumerate(modules["E_cadences"], 1):
        start = 228 + 10*(ordinal-1)
        require(cadence["position"] == ordinal and cadence["pick_attacks"] == [4,4,4,3,4][ordinal-1]
                and len(cadence["attack_tokens"]) == cadence["pick_attacks"]
                and cadence["tab_rows"] == lines[start+1:start+7]
                and cadence["degrees_raw"] == lines[start+7]
                and cadence["txt_notes_raw"] == lines[start+8]
                and cadence["pdf_notes_raw"] == (None if ordinal < 5 else lines[start+8].replace("Notes:   ", "Notes: ")),
                "cadence TAB/summary source drift")
    differences = candidate["source_discrepancies"]
    require(len(differences) == 4 and [d["position"] for d in differences] == [1,2,3,4],
            "cadence PDF omission coverage drift")
    for diff in differences:
        pos = diff["position"]
        require(diff["kind"] == "pdf_cadence_notes_summary_omitted"
                and diff["status"] == "pending_curriculum_review" and diff["pdf_notes"] is None
                and diff["txt_notes"] == modules["E_cadences"][pos-1]["txt_notes_raw"]
                and diff["txt_ref"] == f"L36-TXT-L{227+10*(pos-1)+10}",
                "cadence omission detail drift")


def event(authored: dict, kind: str, source_ref: dict, printed_order: int, *, performed_order: None = None) -> dict:
    return {"id": None, "kind": kind, "printed_order": printed_order,
            "performed_order": performed_order, "source_authored": authored, "source_refs": source_ref,
            "pick_attack_source_count": 1, "onset_q": None, "duration_q": None,
            "fixed_bpm": None, "sounding_midi": None, "performed_result": None}


def record(component: str, title: str, source: dict, events: list[dict]) -> dict:
    return {"source_component": component, "identity_state": "unallocated", "source_unit": source,
            "schema1_fields": {"id": None, "workbook_id": None, "module_id": None,
                               "legacy_level": 36, "title": title, "kind": "mixed",
                               "content_revision": None, "lineage": None, "runtime_eligible": False,
                               "events": events, "variants": [], "resource_requirements": [],
                               "timing": {"status": "unresolved", "unit": "quarter", "fixed_bpm": None},
                               "source_refs": {"txt": source.get("txt_ref"), "pdf": source.get("pdf_ref")}}}


def project(data: dict, *, replay: bool = True) -> tuple[dict, dict]:
    candidate = data["candidate"]
    catalog = catalog_boundary(data)
    validate_candidate(candidate, data["lines"])
    if replay:
        replay_upstream(data["root"], candidate)
    modules = candidate["modules"]
    records: list[dict] = []
    for position in modules["A_legato_positions"]:
        events = [event(g, "legato_pair", {"txt": position["txt_ref"], "pdf": position["pdf_ref"]}, i)
                  for i, g in enumerate(position["groups"], 1)]
        records.append(record(f"A_position_{position['position']}", f"Level 36 position {position['position']} legato cell", position, events))
    for seam in modules["B_seam_chains"]:
        events = [event(p, "one_pick_five_tone_seam", {"txt": p["txt_ref"], "pdf": p["pdf_ref"]}, i)
                  for i, p in enumerate(seam["phrases"], 1)]
        records.append(record(f"B_seam_{seam['seam']}", f"Level 36 seam P{seam['seam']} to P{seam['seam']+1}", seam, events))
    for family, kind in (("C_whole_step_bends", "bend_site"), ("D_prebend_cells", "prebend_site")):
        for site in modules[family]:
            refs = {"txt": site["txt_ref"], "pdf": site["pdf_ref"]}
            events = [event({"source_site": site, "articulation": articulation}, kind, refs, i)
                      for i, articulation in enumerate(site["articulation_sequence"], 1)]
            records.append(record(f"{family}_{site['site']}", f"Level 36 {kind} {site['site']}", site, events))
    for ordinal, hold in enumerate(modules["D_A_root_vibrato_holds"], 1):
        refs = {"txt": hold["txt_ref"], "pdf": None}
        records.append(record(f"D_A_root_vibrato_{ordinal}", f"Level 36 A-root vibrato hold {ordinal}", hold,
                              [event(hold, "source_vibrato_hold", refs, 1)]))
    for cadence in modules["E_cadences"]:
        refs = {"txt": cadence["txt_ref"], "pdf": cadence["pdf_ref"]}
        events = [event({"source_attack_token": token, "source_scanning_order": i},
                        "cadence_printed_attack_token", refs, i)
                  for i, token in enumerate(cadence["attack_tokens"], 1)]
        records.append(record(f"E_cadence_{cadence['position']}", f"Level 36 position {cadence['position']} expressive cadence", cadence, events))
    require(len(records) == 37 and sum(len(r["schema1_fields"]["events"]) for r in records) == 165,
            "projection record/attack loss")
    proposal = {"proposal_version": "level036-unallocated-schema1-fields.1", "wbs_id": "2.3.1.1.1",
                "classification": "Build-only, nonimportable schema1 field proposal", "legacy_level": 36,
                "canonical_ids_allocated": False, "schema1_importable": False,
                "whole_workbook_complete": False, "runtime_eligible": False, "admitted": False,
                "counts": candidate["counts"], "source": candidate["source"],
                "source_key": candidate["key"], "source_notes": candidate["notes"],
                "source_degrees": candidate["degrees"], "source_guidance": candidate["source_guidance"],
                "source_discrepancies": candidate["source_discrepancies"],
                "source_route_claims": {"seams": [1,2,3,4], "cadence_positions": [1,2,3,4,5],
                                        "cadence_performance_order": None,
                                        "cadence_attack_tokens_are_printed_row_scan_order": True},
                "unresolved": ["Stable workbook/module/item/event identities and lineage require allocation.",
                               "No event onset, duration, fixed click/BPM, sounding MIDI register or bend/vibrato waveform is authorized.",
                               "Four TXT cadence Notes summaries are absent from PDF page 13; curriculum review is pending.",
                               "Performed order, audio, scoring, mastery and runtime admission require later authority."],
                "records": records}
    handoff = {"handoff_version": "level036-allocation-handoff.1", "wbs_id": "2.3.1.1.1",
               "catalog_workbook_id": catalog["workbook_id"], "catalog_role": catalog["catalog_role"],
               "existing_level036_records": 0, "existing_level036_workbook_entities": 0,
               "proposed_source_units": 37, "proposed_pick_attack_entries": 165,
               "explicit_legato_slide_tones": 240, "cadence_pdf_omissions": 4,
               "canonical_ids_allocated": False, "admitted": False,
               "required_decisions": ["Review all five modules and source-defined articulation/geometry.",
                                      "Resolve four PDF page-13 cadence Notes-summary omissions before admission.",
                                      "Allocate stable identities and explicit performed timing, click, pitch register, audio and mastery authority before import."]}
    return proposal, handoff


def products(root: Path, *, replay: bool = True) -> dict[str, object]:
    data = read_inputs(root)
    data["root"] = root
    proposal, handoff = project(data, replay=replay)
    manifest = {"manifest_version": "level036-input-pins.1", "inputs": [
        {"path": rel, "bytes": len(data["raw"][rel]), "sha256": expected}
        for rel, expected in INPUTS.items()]}
    summary = {"summary_version": "level036-schema1-unallocated-summary.1",
               "proposal_sha256": digest(encoded(proposal)), "handoff_sha256": digest(encoded(handoff)),
               "source_units": 37, "pick_attack_entries": 165, "legato_slide_tones": 240,
               "cadence_pdf_omissions": 4, "native_run": False,
               "runtime_eligible": False, "admitted": False}
    return {"field-proposal.json": proposal, "allocation-handoff.json": handoff,
            "input-manifest.json": manifest, "summary.json": summary}


def output_dir(root: Path) -> Path:
    path = root
    for part in OUT.parts:
        path /= part
        require(not path.is_symlink(), "output symlink path")
    return path


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
            require(not path.is_symlink() and path.read_bytes() == encoded(value), f"output drift: {name}")
    print(f"LEVEL36 {mode.upper()} PASS units=37 attacks=165 legato_slide=240 pdf_omissions=4 admitted=false")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("build", "verify"))
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    run(args.mode, args.root.resolve())
