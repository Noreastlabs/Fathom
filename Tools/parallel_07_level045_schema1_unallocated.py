#!/usr/bin/env python3
"""Project pinned Level45 whole source into detached unallocated schema1 fields."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = Path("Build/parallel-07/2.3.1.1.1-level045-schema1-unallocated-r01")
STEM = "Scale_Exercises_Section_V_Level_45_A_Blues_Shuffle_Rhythm_Triplet_Placement_and_Twelve_Bar_Form_Fixed_Key_A"
TXT = f"Notes/music/guitar project/TXT version/{STEM}.txt"
PDF = f"Notes/music/guitar project/PDF version/{STEM}.pdf"
UPSTREAM_TOOL = "Tools/curriculum_level045_whole_candidate.py"
UPSTREAM = "Build/parallel-08/2.3.1.1.1-level045-whole-r01/level045-candidate-a.json"
TSV = "Results/parallel-01/exercises/inventory/20260922T180500Z-2.3-curriculum-v1-source-inventory-evidence/curriculum-source-map.tsv"
MAP = "Results/parallel-01/exercises/inventory/20260922T180500Z-2.3-curriculum-v1-source-inventory-evidence/curriculum-source-map.json"
PACKAGE = "Content/controls/curriculum-v1/package.json"
REGISTRY = "Content/controls/curriculum-v1/identity-registry.json"
GENERATION = "Content/controls/curriculum-v1/generation.json"
INPUTS = {
    UPSTREAM_TOOL: "513cc1ca86d353dc83560f5c89f7fd2c96c7856e8c305ba6e438439f683bc375",
    UPSTREAM: "29ad18cbbb2734cb909524e52f415d9aea59ad228fc086a5cc5233128af500b5",
    TXT: "9f77c127208540d41d2f331c00c880dcdf935993f9e422993ce3babf232cd069",
    PDF: "f84f04ff134377eca66f904e45fbb8a0669b01c65c8c663f51a092558296357f",
    TSV: "f526ff4d9ce3bceaf9a7cc581a3ac2aee2c74917eba984dd57913adba574c123",
    MAP: "bad5581a04f43ba8baf14db430449e1ccff5cf88f0f7e42198328073b27053d6",
    PACKAGE: "766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255",
    REGISTRY: "5d265859e1e8a5a530a0e53d88b019a1c920f3bba6cccb4ef0fef2f7640007e5",
    GENERATION: "fc6cec9f9d67eb82c97c5f4c3fb95d285178fb7fce7bd147d9ae0296d21b4c1c",
}
COUNTS = {"A": 48, "B": 40, "C": 108, "D": 27, "E": 28,
          "F": 50, "G": 29, "H": 102, "I": 48, "J": 60}
FORM = ["A7", "A7", "A7", "A7", "D7", "D7", "A7", "A7", "E7", "D7", "A7", "E7"]
ROOTS = ["E5", "E5", "E5", "E5", "A5", "A5", "E5", "E5", "A7", "A5", "E5", "A7"]
PC = {"A": 9, "C": 0, "C#": 1, "D": 2, "Eb": 3, "E": 4, "F": 5,
      "F#": 6, "G": 7, "G#": 8, "B": 11}
OPEN = {"E": 4, "A": 9, "D": 2, "G": 7, "B": 11, "e": 4}
PDF_PAGES = {"A": [3], "B": [4], "C": [5], "D": [6], "E": [7], "F": [8,9],
             "G": [10], "H": [11,12,13], "I": [14], "J": [15]}


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise ValueError(reason)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def encoded(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def read_inputs(root: Path) -> dict:
    raw = {}
    for rel, expected in INPUTS.items():
        path = root / rel
        require(not path.is_symlink() and path.is_file() and path.resolve().is_relative_to(root), f"unsafe input: {rel}")
        value = path.read_bytes()
        require(sha(value) == expected, f"input drift: {rel}")
        raw[rel] = value
    return {"raw": raw, "candidate": json.loads(raw[UPSTREAM]),
            "source_map": json.loads(raw[MAP]), "package": json.loads(raw[PACKAGE]),
            "registry": json.loads(raw[REGISTRY]), "generation": json.loads(raw[GENERATION]),
            "lines": raw[TXT].decode().splitlines(), "root": root}


def replay_upstream(root: Path, candidate: dict) -> None:
    spec = importlib.util.spec_from_file_location("sealed_level045_builder", root / UPSTREAM_TOOL)
    require(spec is not None and spec.loader is not None, "upstream builder unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    require(module.build_candidate(root) == candidate, "upstream candidate/source replay drift")


def catalog_boundary(data: dict) -> dict:
    package, registry, generation, source_map = (data[k] for k in ("package", "registry", "generation", "source_map"))
    workbook = "fg:workbook:000045"
    require(len(package["records"]) == generation["records"] == 659, "current659 foundation drift")
    require(not any(r.get("legacy_level") == 45 or r.get("workbook_id") == workbook for r in package["records"]),
            "Level45 canonical records exist")
    require(not any(e.get("id") == workbook for e in registry["entities"]), "Level45 registry entity exists")
    entry = next((x for x in package["workbook_catalog"]["entries"] if x.get("workbook_id") == workbook), None)
    require(entry is not None and entry.get("catalog_role") == "read_only_source_preservation"
            and entry.get("conversion_status") == "not_converted" and entry.get("review") == "Pending"
            and entry.get("playable_projection", {}).get("status") == "explicitly_empty_unresolved"
            and all(entry.get(k) is False for k in ("admitted", "imported", "runtime_eligible", "runtime_admitted", "whole_workbook_complete")),
            "Level45 source-only catalog boundary drift")
    row = next((x for x in source_map["rows"] if x.get("level") == 45), None)
    require(row is not None and row.get("txt_path") == TXT and row.get("pdf_path") == PDF
            and row.get("txt_sha256") == INPUTS[TXT] and row.get("pdf_sha256") == INPUTS[PDF]
            and row.get("review") == "Pending" and row.get("conversion_status") == "not_converted"
            and row.get("representative_item_id") is None
            and all(row.get(k) is False for k in ("stable_ids_assigned", "runtime_eligible", "imported", "admitted")),
            "Level45 frozen source-map boundary drift")
    return entry


def check_placement(note: str, placement: dict) -> None:
    bare = note.removesuffix("*")
    string, fret = placement["string"], placement["fret"]
    require(bare in PC and string in OPEN and 0 <= fret <= 24
            and placement["pitch_class"] == (OPEN[string] + fret) % 12 == PC[bare]
            and isinstance(placement["source_column"], int), "TAB/pitch geometry drift")


def check_mask(mask: dict) -> int:
    beats = mask["beats"]
    require(len(beats) == 4 and all(len(beat) == 3 and set(beat) <= {"X", "."} for beat in beats)
            and mask["literal"] == "|".join(beats), "mask literal/beat geometry drift")
    slots = [[i+1, j+1] for i, beat in enumerate(beats) for j, mark in enumerate(beat) if mark == "X"]
    require(mask["attack_slots"] == slots, "mask X/dot attack-slot geometry drift")
    return len(slots)


def validate_candidate(c: dict, lines: list[str]) -> None:
    require(c.get("schema") == "fathom.detached.curriculum.level045.whole.v1"
            and c.get("level") == 45 and c.get("wbs") == "2.3.1.1.1"
            and c.get("key") == "A blues" and c.get("transposed") is False
            and c.get("permanent_pitch_pool") == ["A", "C", "D", "Eb", "E", "G"]
            and c.get("module_attack_counts") == COUNTS and c.get("written_core_attacks") == 540
            and c.get("whole_level_source_covered") is True and c.get("whole_level_complete") is False
            and c.get("canonical_id") is None and c.get("runtime_imported") is False and c.get("admitted") is False,
            "Level45 scope/count/authority drift")
    require(c["timing"] == {"authored_symbolic_masks": True, "fixed_bpm": None,
                            "numeric_duration": None, "numeric_onset": None, "performed_audio": None},
            "invented timing/performance authority")
    require(c["default_form"] == FORM and c["root_locations"] == ROOTS
            and c["bar_12_tonic_closure_option"] == "A7/E5", "twelve-bar chord/root route drift")
    require(c["source"]["txt"]["sha256"] == INPUTS[TXT]
            and c["source"]["pdf"]["sha256"] == INPUTS[PDF]
            and c["source"]["source_map"]["sha256"] == INPUTS[TSV]
            and len(lines) == 529, "source identity drift")
    m = c["modules"]
    require(list(m) == list(COUNTS) and {k: (sum(x["core_attacks"] for x in v) if isinstance(v, list)
                                       else v["core_attacks"]) for k, v in m.items()} == COUNTS,
            "module coverage/count drift")
    require([len(m[k]) for k in ("A", "B", "D", "E", "F", "G", "I")] == [3,8,3,6,3,4,6]
            and len(m["C"]["passes"]) == 3 and len(m["H"]["model"]["bars"]) == 12
            and len(m["J"]["passes"]) == 5, "module task cardinality drift")
    for pattern in m["A"]:
        require(len(pattern["notes"]) == len(pattern["placements"]) == 8
                and pattern["core_attacks"] == 16 and pattern["straight"]["attack_count"] == 8
                and pattern["shuffle"]["attack_count"] == check_mask(pattern["shuffle"]["triplet_mask"]) == 8,
                "A straight/shuffle geometry drift")
    for card in m["B"]:
        require(sum(check_mask(x) for x in card["bars"]) == card["core_attacks"]
                and card["practice_repetitions"] == 4, "B card mask/repetition drift")
    require([x["core_attacks"] for x in m["C"]["passes"]] == [12,48,48]
            and m["C"]["form"] == [{"bar": i+1, "chord": FORM[i], "root_string": ROOTS[i][0],
                                     "root_fret": int(ROOTS[i][1:])} for i in range(12)], "C form route drift")
    for passage in m["C"]["passes"]:
        require(passage["bars"] == 12 and passage["core_attacks"] == 12*check_mask(passage["mask"]),
                "C pass mask geometry drift")
    for trans in m["D"]:
        require(len(trans["timing_masks"]) == 3 and trans["core_attacks"] == 9
                and trans["destination_on_next_bar_beat_1"] is True
                and all(check_mask(x["source_bar"]) == 2 and check_mask(x["next_bar"]) == 1
                        and x["next_bar"]["attack_slots"] == [[1,1]] for x in trans["timing_masks"]),
                "D pickup/next-bar geometry drift")
    for card in m["E"]:
        require(len(card["bars"]) == 2 and sum(check_mask(x) for x in card["bars"]) == card["core_attacks"],
                "E two-bar rest/mask drift")
    for study in m["F"]:
        require(sum(len(part["notes"]) for part in study["parts"]) == study["core_attacks"]
                and study["bars"] == 8, "F call/response count drift")
    for study in m["G"]:
        require(study["root_hit_staccato_and_muted"] is True
                and (sum(x["attacks"] for x in study["bars"]) if "bars" in study
                     else 1+len(study["lead"])) == study["core_attacks"], "G stop-time structure drift")
    h = m["H"]
    require(h["landmark"]["played_bars"] == [1,5,9,10,11,12]
            and h["landmark"]["core_attacks"] == 6
            and h["root_shuffle"]["form"] == FORM and h["root_shuffle"]["root_locations"] == ROOTS
            and check_mask(h["root_shuffle"]["mask"]) == 4
            and h["root_shuffle"]["core_attacks"] == 48
            and h["model"]["core_attacks"] == 48, "H landmark/root-shuffle route drift")
    for i, bar in enumerate(h["model"]["bars"]):
        require(bar["bar"] == i+1 and bar["chord"] == FORM[i]
                and bar["attacks"] == check_mask(bar["mask"]) == len(bar["notes"]) == 4,
                "H model bar/mask drift")
    for card in m["I"]:
        require(card["core_attacks"] == len(card["notes"]) == len(card["placements"]) == 8,
                "I turnaround count drift")
    require([x["ending_job"] for x in m["I"]] == ["E7_continuation"]*4 + ["tonic_A_close", "pickup_next_chorus"],
            "I turnaround ending drift")
    require(m["J"]["root_route"] == ROOTS and [x["printed_clicks"] for x in m["J"]["passes"]] == [48,24,12,12,6]
            and all(x["root_attacks"] == x["bars"] == 12 for x in m["J"]["passes"]),
            "J click/root-route drift")
    def walk(value):
        if isinstance(value, dict):
            if "notes" in value and "placements" in value:
                require(len(value["notes"]) == len(value["placements"]), "note/TAB count drift")
                for note, placement in zip(value["notes"], value["placements"], strict=True):
                    check_placement(note, placement)
            for v in value.values():
                walk(v)
        elif isinstance(value, list):
            for v in value:
                walk(v)
    walk(m)
    cap = c["capstone"]
    require(cap["bars"] == 36 and cap["reused_attacks"] == 108
            and [x["reused_attacks"] for x in cap["choruses"]] == [12,48,48]
            and cap["included_in_written_core_540"] is False
            and cap["chorus_3_bar_12_txt"] == "A-tonic closing phrase if desired"
            and cap["chorus_3_bar_12_pdf"] == "A7 tonic close", "capstone reuse/difference drift")
    require([x["kind"] for x in c["source_discrepancies"]] ==
            ["pdf_abbreviated_second_bar", "pdf_narrative_extra_rest_dot", "capstone_final_bar_option_vs_requirement"]
            and c["source_discrepancies"][0]["pdf"] == "|| X..|"
            and c["source_discrepancies"][0]["txt"] == "Bar 2 Mask|X..|...|...|...|"
            and c["source_discrepancies"][1]["pdf_prose"] == "X.X|...|X.X|...."
            and c["source_discrepancies"][1]["txt_and_pdf_grid"] == "Mask|X.X|...|X.X|...|"
            and c["source_discrepancies"][2]["pdf"] == "A7 tonic close", "source discrepancy coverage drift")


def slots(mask: dict, bar: int, *, chord: str | None = None) -> list[dict]:
    check_mask(mask)
    return [{"bar": bar, "beat": beat, "triplet_slot": slot, "chord": chord,
             "printed_mask": mask["literal"]} for beat, slot in mask["attack_slots"]]


def note_fields(note: str | None, placement: dict | None) -> dict:
    return {"printed_note": note, "printed_string": placement["string"] if placement else None,
            "printed_fret": placement["fret"] if placement else None,
            "source_column": placement["source_column"] if placement else None,
            "sounding_midi": None}


def make_event(ordinal: int, authored: dict, ref: dict, *, note: str | None = None,
               placement: dict | None = None) -> dict:
    return {"id": None, "kind": "printed_pick_attack", "printed_order": ordinal,
            "performed_order": None, "source_authored": authored, "source_refs": ref,
            "source_tone": note_fields(note, placement), "onset_q": None, "duration_q": None,
            "fixed_bpm": None, "performed_result": None}


def source_ref(module: str, lines: list[str]) -> dict:
    heading = next((i+1 for i, line in enumerate(lines) if line.startswith(f"MODULE {module} - ")), None)
    next_heading = next((i+1 for i, line in enumerate(lines) if line.startswith(f"MODULE {chr(ord(module)+1)} - ")), None)
    if module == "J":
        next_heading = lines.index("LEVEL 45 CAPSTONE - THREE-CHORUS RHYTHM CIRCUIT") + 1
    require(heading is not None and next_heading is not None, "module TXT span drift")
    return {"txt": f"L45-TXT1-L{heading}-{next_heading-1}",
            "pdf_pages": [f"L45-PDF-p{page}" for page in PDF_PAGES[module]]}


def add_record(records: list, module: str, component: str, source: dict, descriptors: list[dict], ref: dict) -> None:
    events = [make_event(i, d["authored"], ref, note=d.get("note"), placement=d.get("placement"))
              for i, d in enumerate(descriptors, 1)]
    records.append({"source_component": component, "source_module": module,
                    "identity_state": "unallocated", "source_unit": source,
                    "schema1_fields": {"id": None, "workbook_id": None, "module_id": None,
                                       "legacy_level": 45, "title": component, "kind": "mixed",
                                       "content_revision": None, "lineage": None,
                                       "runtime_eligible": False, "events": events, "variants": [],
                                       "source_refs": ref, "resource_requirements": [],
                                       "timing": {"status": "unresolved", "fixed_bpm": None}}})


def paired(notes: list[str], placements: list[dict], authored: list[dict] | None = None) -> list[dict]:
    require(len(notes) == len(placements) and (authored is None or len(authored) == len(notes)), "attack/note geometry drift")
    return [{"note": n, "placement": p, "authored": authored[i] if authored else {"printed_ordinal": i+1}}
            for i, (n, p) in enumerate(zip(notes, placements, strict=True))]


def project(data: dict, *, replay: bool = True) -> tuple[dict, dict]:
    c = data["candidate"]
    catalog = catalog_boundary(data)
    validate_candidate(c, data["lines"])
    if replay:
        replay_upstream(data["root"], c)
    m, lines = c["modules"], data["lines"]
    refs = {k: source_ref(k, lines) for k in COUNTS}
    records: list[dict] = []
    for pattern in m["A"]:
        descriptors = paired(pattern["notes"], pattern["placements"],
                             [{"grid": "straight", "eighth_slot": i} for i in range(1,9)])
        shuffle = slots(pattern["shuffle"]["triplet_mask"], 1)
        descriptors += paired(pattern["notes"], pattern["placements"],
                              [{"grid": "shuffle", **x} for x in shuffle])
        add_record(records, "A", f"A_pattern_{pattern['pattern']}", pattern, descriptors, refs["A"])
    for card in m["B"]:
        descriptors = [{"authored": slot} for bar, mask in enumerate(card["bars"], 1)
                       for slot in slots(mask, bar)]
        add_record(records, "B", f"B_card_{card['card']}", card, descriptors, refs["B"])
    for passage in m["C"]["passes"]:
        descriptors = [{"authored": {**slot, "root": ROOTS[bar-1]}}
                       for bar in range(1,13) for slot in slots(passage["mask"], bar, chord=FORM[bar-1])]
        add_record(records, "C", f"C_pass_{passage['pass']}", passage, descriptors, refs["C"])
    for trans in m["D"]:
        descriptors = []
        for mask in trans["timing_masks"]:
            symbolic = slots(mask["source_bar"], 1, chord=trans["source_chord"])
            symbolic += slots(mask["next_bar"], 2, chord=trans["destination_chord"])
            descriptors += paired(trans["notes"], trans["placements"], symbolic)
        add_record(records, "D", f"D_transition_{trans['transition']}", trans, descriptors, refs["D"])
    for card in m["E"]:
        symbolic = [slot for bar, mask in enumerate(card["bars"], 1) for slot in slots(mask, bar)]
        add_record(records, "E", f"E_card_{card['card']}", card,
                   paired(card["notes"], card["placements"], symbolic), refs["E"])
    for study in m["F"]:
        descriptors = []
        for part in study["parts"]:
            descriptors += paired(part["notes"], part["placements"],
                                  [{"source_part": {k:v for k,v in part.items() if k not in ("notes", "placements")},
                                    "part_ordinal": i} for i in range(1,len(part["notes"])+1)])
        add_record(records, "F", f"F_study_{study['study']}", study, descriptors, refs["F"])
    for study in m["G"]:
        if "bars" in study:
            descriptors = [{"placement": p, "authored": {"bar": bar["bar"], "chord": bar["chord"],
                                                          "attack_role": role}}
                           for bar in study["bars"] for role, p in
                           [("staccato_root_hit", bar["hit"]), *(("lead", x) for x in bar["lead"])]]
        else:
            descriptors = [{"placement": study["hit"], "authored": {"attack_role": "staccato_root_hit"}}]
            descriptors += [{"placement": p, "authored": {"attack_role": "lead"}} for p in study["lead"]]
        add_record(records, "G", f"G_study_{study['study']}", study, descriptors, refs["G"])
    h = m["H"]
    landmark = h["landmark"]
    add_record(records, "H", "H_landmark", landmark,
               [{"authored": {"bar": bar, "chord": FORM[bar-1], "root": ROOTS[bar-1]}}
                for bar in landmark["played_bars"]], refs["H"])
    shuffle = h["root_shuffle"]
    add_record(records, "H", "H_root_shuffle", shuffle,
               [{"authored": {**slot, "root": ROOTS[bar-1]}}
                for bar in range(1,13) for slot in slots(shuffle["mask"], bar, chord=FORM[bar-1])], refs["H"])
    for bar in h["model"]["bars"]:
        add_record(records, "H", f"H_model_bar_{bar['bar']}", bar,
                   paired(bar["notes"], bar["placements"], slots(bar["mask"], bar["bar"], chord=bar["chord"])), refs["H"])
    for card in m["I"]:
        add_record(records, "I", f"I_turnaround_{card['card']}", card,
                   paired(card["notes"], card["placements"]), refs["I"])
    for passage in m["J"]["passes"]:
        add_record(records, "J", f"J_click_pass_{passage['pass']}", passage,
                   [{"authored": {"bar": bar, "chord": FORM[bar-1], "root": ROOTS[bar-1],
                                  "printed_clicks": passage["printed_clicks"]}} for bar in range(1,13)], refs["J"])
    actual = {k: sum(len(r["schema1_fields"]["events"]) for r in records if r["source_module"] == k) for k in COUNTS}
    require(actual == COUNTS and len(records) == 55, "projected attack/module coverage drift")
    proposal = {"proposal_version": "level045-unallocated-schema1-fields.1", "wbs_id": "2.3.1.1.1",
                "classification": "Build-only, nonimportable schema1 field proposal", "legacy_level": 45,
                "canonical_ids_allocated": False, "schema1_importable": False,
                "whole_workbook_complete": False, "runtime_eligible": False, "admitted": False,
                "source": c["source"], "source_key": c["key"],
                "permanent_pitch_pool": c["permanent_pitch_pool"],
                "temporary_support_notes": c["temporary_support_notes"],
                "default_form": c["default_form"], "root_locations": c["root_locations"],
                "bar_12_tonic_closure_option": c["bar_12_tonic_closure_option"],
                "source_guidance": c["guidance"], "source_discrepancies": c["source_discrepancies"],
                "module_attack_counts": actual, "written_core_attacks": 540,
                "capstone_reuse_reference": {"source": c["capstone"], "new_core_attacks": 0,
                                              "existing_material_reused_attacks": 108,
                                              "admitted": False, "event_ids": None},
                "unresolved": ["Stable workbook/module/item/event identities and lineage require allocation.",
                               "Symbolic masks retain beat/triplet positions; numeric onset/duration and fixed BPM remain unresolved.",
                               "No performed audio, score, mastery or import/admission is authorized.",
                               "Three TXT/PDF differences, including chorus-three final-bar policy, require Curriculum review."],
                "records": records}
    handoff = {"handoff_version": "level045-allocation-handoff.1", "wbs_id": "2.3.1.1.1",
               "catalog_workbook_id": catalog["workbook_id"], "catalog_role": catalog["catalog_role"],
               "existing_level045_records": 0, "existing_level045_workbook_entities": 0,
               "proposed_source_units": 55, "printed_core_attacks": 540,
               "capstone_bars": 36, "capstone_reused_attacks": 108,
               "source_discrepancies": 3, "canonical_ids_allocated": False, "admitted": False,
               "required_decisions": ["Review ten module routes, support-note marks, masks, rests and TAB geometry.",
                                      "Disposition the three retained TXT/PDF differences, especially chorus-three bar 12.",
                                      "Allocate identities and explicit performed timing, click/BPM, audio and mastery authority before import."]}
    return proposal, handoff


def products(root: Path) -> dict[str, object]:
    data = read_inputs(root)
    proposal, handoff = project(data)
    manifest = {"manifest_version": "level045-input-pins.1", "inputs": [
        {"path": rel, "bytes": len(data["raw"][rel]), "sha256": expected}
        for rel, expected in INPUTS.items()]}
    summary = {"summary_version": "level045-schema1-unallocated-summary.1",
               "proposal_sha256": sha(encoded(proposal)), "handoff_sha256": sha(encoded(handoff)),
               "source_units": 55, "printed_core_attacks": 540,
               "capstone_reused_attacks": 108, "source_discrepancies": 3,
               "native_run": False, "runtime_eligible": False, "admitted": False}
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
    print(f"LEVEL45 {mode.upper()} PASS units=55 core_attacks=540 capstone_reuse=108 differences=3 admitted=false")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("build", "verify"))
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    run(args.mode, args.root.resolve())
