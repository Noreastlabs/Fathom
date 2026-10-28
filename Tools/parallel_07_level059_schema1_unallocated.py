#!/usr/bin/env python3
"""Project sealed Level59 sources to Build-only, unallocated schema1 fields."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = Path("Build/parallel-07/2.3.1.2.1-level059-schema1-unallocated-r01")
STEM = "Guitar_Exercises_Section_VII_Level_59_Major_and_Minor_Triad_Arpeggios_Inversion_Starts_Alternate_and_Economy_Picking_and_Chord_Tone_Connections"
TXT = f"Notes/music/guitar project/TXT version/{STEM}.txt"
PDF = f"Notes/music/guitar project/PDF version/{STEM}.pdf"
WHOLE = "Build/parallel-08/2.3.1.2.1-level059-whole-r01/level059-candidate-a.json"
NARROW = "Build/parallel-01/2.3-level059-modulek-call-response-r01/candidate-r02.json"
MAP = "Results/parallel-01/exercises/inventory/20260922T180500Z-2.3-curriculum-v1-source-inventory-evidence/curriculum-source-map.json"
PACKAGE = "Content/controls/curriculum-v1/package.json"
REGISTRY = "Content/controls/curriculum-v1/identity-registry.json"
GENERATION = "Content/controls/curriculum-v1/generation.json"
INPUTS = {
    WHOLE: "f50f9418544eff7d8ff06b3cf111f06d77d26b153be385615fd04c0b6696f82e",
    NARROW: "a939a5ebbb4c4673ac01a58a8e5b8ef53bd7c0f629c13d157e5658d249d4c6cb",
    TXT: "7eea221134b4308f384c27d5ebd40c21430c44fe2aaca9332dadb0a6d6b77adb",
    PDF: "43b1b70a42f05b80aa575bf377735aa0ccec27889485864750b169ccef4305ba",
    MAP: "bad5581a04f43ba8baf14db430449e1ccff5cf88f0f7e42198328073b27053d6",
    PACKAGE: "766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255",
    REGISTRY: "5d265859e1e8a5a530a0e53d88b019a1c920f3bba6cccb4ef0fef2f7640007e5",
    GENERATION: "fc6cec9f9d67eb82c97c5f4c3fb95d285178fb7fce7bd147d9ae0296d21b4c1c",
}
HEAD = {
    "A": "MODULE A - FORMULA ATLAS AND SILENT COMMANDS",
    "B": "MODULE B - C MAJOR AND C MINOR BLOCKED-PLUS-ARPEGGIO FAMILIES",
    "C": "MODULE C - A MAJOR AND A MINOR BLOCKED-PLUS-ARPEGGIO FAMILIES",
    "D": "MODULE D - STRICT ALTERNATE VERSUS ECONOMY PICKING",
    "E": "MODULE E - FIVE-NOTE NO-REPEAT LOOPS",
    "F": "MODULE F - INVERSION-START CYCLES",
    "G": "MODULE G - SAME-ROOT MAJOR/MINOR QUALITY SWITCHES",
    "H": "MODULE H - TRIAD ARPEGGIO PERMUTATIONS",
    "I": "MODULE I - ARPEGGIO-TO-SCALE CONNECTIONS",
    "J": "MODULE J - PROGRESSION TRACKING",
    "K": "MODULE K - CHORD-TONE CALL AND RESPONSE",
}
PAGES = {"A": [2], "B": [3, 4, 5], "C": [6, 7, 8], "D": [9], "E": [10], "F": [11, 12],
         "G": [13], "H": [14], "I": [15, 16], "J": [17, 18], "K": [19]}
COUNTS = {"A": 0, "B": 168, "C": 168, "D": 96, "E": 80, "F": 144,
          "G": 96, "H": 64, "I": 112, "J": 128, "K": 64}
UNRESOLVED = [
    "Canonical workbook/module/item/event/variant IDs, revision and lineage require allocation.",
    "Quarter-note onset/duration, BPM, audio and performed mastery are not printed.",
    "The printed string/fret and note spelling do not authorize an inferred MIDI register.",
    "Curriculum must reconcile the D/E PDF workouts with the different TXT variants and choose phase-ten ordering.",
]


def encoded(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def inputs(root: Path) -> dict:
    raw = {}
    for path, digest in INPUTS.items():
        data = (root / path).read_bytes()
        if sha(data) != digest:
            raise ValueError(f"input drift: {path}")
        raw[path] = data
    return {p: json.loads(raw[p]) for p in (WHOLE, NARROW, MAP, PACKAGE, REGISTRY, GENERATION)} | {TXT: raw[TXT].decode().splitlines()}


def source_spans(lines: list[str]) -> dict[str, tuple[int, int]]:
    starts = {}
    for module, heading in HEAD.items():
        matches = [i + 1 for i, line in enumerate(lines) if line == heading]
        if len(matches) != 1:
            raise ValueError(f"module {module} heading drift")
        starts[module] = matches[0]
    return {m: (start, (starts[list(HEAD)[i + 1]] - 1 if i + 1 < len(HEAD) else len(lines)))
            for i, (m, start) in enumerate(starts.items())}


def row_ref(lines: list[str], span: tuple[int, int], rows: list[str], occurrence: int = 0) -> dict:
    if not rows:
        raise ValueError("source rows missing")
    start, end = span
    matches = [i for i in range(start - 1, end - len(rows) + 1) if lines[i:i + len(rows)] == rows]
    if occurrence >= len(matches):
        raise ValueError("source rows occurrence not pinned to TXT")
    return {"txt_start_line": matches[occurrence] + 1, "txt_end_line": matches[occurrence] + len(rows)}


def structured_unit_ref(lines: list[str], span: tuple[int, int], module: str, unit: dict,
                        seen: Counter) -> dict:
    if module == "G":
        row = (f'{unit["string_set"]} {unit["inversion"]}: major '
               f'{"-".join(map(str, unit["major"]["frets"]))} -> minor '
               f'{"-".join(map(str, unit["minor"]["frets"]))} | {unit["literal_pattern"]}')
        return row_ref(lines, span, [row])
    if module == "F":
        rows = [unit["string_set"]]
        for shape in unit["shapes"]:
            triad = shape["triad"]
            rows.append(f'{shape["inversion"]}: {"-".join(map(str, triad["frets"]))} | '
                        f'{"-".join(triad["notes"])} | {"-".join(triad["roles"])}')
        rows.append("Picking: D-U-D-U-D-U for each shape; 18 attacks total.")
    elif module == "J":
        rows = [unit["string_set"]]
        for chord in unit["chords"]:
            triad = chord["triad"]
            rows.append(f'{chord["chord"]} {chord["inversion"]}: '
                        f'{"-".join(map(str, triad["frets"]))} | {"-".join(triad["notes"])}')
        rows.append("Pattern per measure: blocked chord, low voice, middle voice, high voice.")
    else:
        raise ValueError("unmapped structured TXT unit")
    key = tuple(rows)
    ref = row_ref(lines, span, rows, seen[key])
    seen[key] += 1
    return ref


def event(module: str, unit: int, ordinal: int, kind: str, note: str | None, role: str | None,
          pick: str | None, string: str | None, fret: int | None, ref: dict,
          *, voicing: dict | None = None, bar: int | None = None, column: int | None = None,
          segment: str | None = None, phase: str | None = None) -> dict:
    if kind == "single" and (not note or string not in ("E", "A", "D", "G", "B", "e") or not isinstance(fret, int)):
        raise ValueError("single-note source contact drift")
    if kind == "blocked" and (not voicing or any(x is not None for x in (note, role, string, fret))):
        raise ValueError("blocked source voicing drift")
    if pick is not None and pick not in ("D", "U"):
        raise ValueError("printed pick drift")
    attack = {"module": module, "unit_number": unit, "ordinal": ordinal, "kind": kind,
              "printed_note": note, "printed_role": role, "printed_pick": pick,
              "printed_string": string, "printed_fret": fret, "printed_voicing": voicing,
              "printed_bar": bar, "source_column": column, "segment": segment, "phase": phase,
              "source_refs": ref}
    return {"source_attack": attack,
            "source_tone": None if kind == "blocked" else {"string": string, "fret": fret,
                                                              "printed_note": note, "printed_role": role,
                                                              "sounding_midi": None},
            "schema1_fields": {"event_id": None, "kind": "contact", "contact": "pitched",
                               "pick": None, "pitch_binding": None, "onset_q": None, "duration_q": None}}


def triad_note(triad: dict, index: int) -> tuple[str, str | None, str, int]:
    roles = triad.get("roles")
    return triad["notes"][index], roles[index] if roles else None, triad["strings"][index], triad["frets"][index]


def single(module: str, unit: int, ordinal: int, note: str, role: str | None, pick: str | None,
           tab: dict, ref: dict, *, segment: str | None = None, phase: str | None = None) -> dict:
    if tab["note"] != note:
        raise ValueError("TAB/note divergence")
    return event(module, unit, ordinal, "single", note, role, pick, tab["string"], tab["fret"], ref,
                 bar=tab.get("bar"), column=tab.get("source_column"), segment=segment, phase=phase)


def shape_tab(triad: dict, index: int) -> dict:
    note, _, string, fret = triad_note(triad, index)
    return {"note": note, "string": string, "fret": fret}


def mirror_events(module: str, unit_no: int, unit: dict, ref: dict, *, txt: bool = False) -> list[dict]:
    triad = unit["blocked"]
    out = []
    for phase, picks in (("alternate", unit["alternate_picks"]), ("economy", unit["economy_picks"])):
        if len(picks) != 6 or len(unit["notes"]) != 6:
            raise ValueError("D pass length drift")
        for i, shape_index in enumerate((0, 1, 2, 2, 1, 0)):
            note, role, string, fret = triad_note(triad, shape_index)
            if note != unit["notes"][i]:
                raise ValueError("D shape/note divergence")
            out.append(event(module, unit_no, len(out) + 1, "single", note, role, picks[i], string, fret,
                             ref | {"variant_source": "TXT" if txt else "PDF", "pass": phase}, phase=phase))
    return out


def unit_events(module: str, no: int, unit: dict, ref: dict, *, alternative: bool = False) -> list[dict]:
    out = []
    add = out.append
    if module in ("B", "C"):
        add(event(module, no, 1, "blocked", None, None, None, None, None, ref, voicing=unit["blocked"]))
        for i, tab in enumerate(unit["tab"]):
            add(single(module, no, i + 2, unit["single_notes"][i], unit["roles"][i], unit["picks"][i], tab, ref))
    elif module == "D":
        out = mirror_events(module, no, unit, ref, txt=alternative)
    elif module == "E":
        triad = unit["blocked_reference"] if not alternative else None
        for i, note in enumerate(unit["notes"]):
            if alternative:
                tab = unit["tab"][i]
            else:
                tab = shape_tab(triad, (0, 1, 2, 1, 0)[i % 5])
            add(single(module, no, i + 1, note, unit["roles"][i], unit["picks"][i], tab, ref,
                       phase=f"loop_{i // 5 + 1}"))
    elif module == "F":
        for shape in unit["shapes"]:
            triad = shape["triad"]
            for i, shape_index in enumerate((0, 1, 2, 2, 1, 0)):
                tab = shape_tab(triad, shape_index)
                if tab["note"] != shape["six_note_mirror"][i]:
                    raise ValueError("F shape/mirror divergence")
                add(single(module, no, len(out) + 1, tab["note"], triad["roles"][shape_index],
                           shape["picks"][i], tab, ref, phase=shape["inversion"]))
    elif module == "G":
        for i, quality in enumerate(unit["attack_sequence"]):
            if quality != ("major" if i % 2 == 0 else "minor"):
                raise ValueError("G quality alternation drift")
            add(event(module, no, i + 1, "blocked", None, None, None, None, None, ref,
                      voicing=unit[quality], phase=quality))
    elif module in ("H", "I"):
        for i, tab in enumerate(unit["tab"]):
            segment = unit["segments"][i] if module == "I" else unit["cell"]
            add(single(module, no, i + 1, unit["notes"][i], unit["roles"][i], unit["picks"][i],
                       tab, ref, segment=segment))
    elif module == "J":
        for chord in unit["chords"]:
            triad = chord["triad"]
            add(event(module, no, len(out) + 1, "blocked", None, None, None, None, None, ref,
                      voicing=triad, phase=chord["chord"]))
            for i in range(3):
                note, role, string, fret = triad_note(triad, i)
                add(event(module, no, len(out) + 1, "single", note, role, None, string, fret, ref,
                          phase=chord["chord"]))
    else:
        raise ValueError(f"unmapped module {module}")
    expected = unit.get("attack_count")
    if alternative:
        expected = unit.get("if_performed_both_printed_passes_attacks", unit.get("if_performed_printed_two_loops_attacks"))
    if len(out) != expected:
        raise ValueError(f"{module} unit attack count drift")
    return out


def k_events(unit: dict, narrow_pair: dict, no: int) -> list[dict]:
    if (narrow_pair["source_pair_order"] != no or narrow_pair["printed_attack_count"] != 8
        or narrow_pair["question_chord_token"] != unit["question_chord"]
        or narrow_pair["answer_chord_token"] != unit["answer_chord"]
        or len(narrow_pair["positions"]) != len(unit["tab"]) != 8):
        raise ValueError("K pair identity/count drift")
    out = []
    for i, (tab, pos) in enumerate(zip(unit["tab"], narrow_pair["positions"])):
        if (pos["attack_order"] != i + 1 or pos["note_token"] != unit["notes"][i]
            or pos["role_token"] != unit["roles"][i] or pos["pick_token"] != unit["picks"][i]
            or pos["printed_bar_order"] != tab["bar"] or pos["source_column"] != tab["source_column"]
            or pos["source_tab"] != {"string_label": tab["string"], "fret_token": str(tab["fret"])}
            or pos["canonical_event_id"] is not None or pos["sounding_pitch"] is not None or pos["timing"] is not None):
            raise ValueError("K whole/narrow position divergence or inferred authority")
        ref = pos["source_refs"]
        if ref["pdf_page"] != 19 or any(not isinstance(ref[k], int) for k in ("txt_heading_line", "txt_note_line", "txt_role_line", "txt_pick_line", "txt_tab_line")):
            raise ValueError("K position source-ref drift")
        out.append(single("K", no, i + 1, pos["note_token"], pos["role_token"], pos["pick_token"],
                          tab, ref, phase="question" if i < 4 else "answer"))
    return out


def boundary(data: dict) -> dict:
    foundation, registry, generation = data[PACKAGE], data[REGISTRY], data[GENERATION]
    workbook = "fg:workbook:000059"
    if len(foundation["records"]) != 659 or generation["records"] != 659:
        raise ValueError("current659 foundation drift")
    if any(r.get("legacy_level") == 59 or r.get("workbook_id") == workbook for r in foundation["records"]):
        raise ValueError("Level59 canonical record already exists")
    if any(e.get("id") == workbook for e in registry["entities"]):
        raise ValueError("Level59 registry entity already exists")
    entry = next((x for x in foundation["workbook_catalog"]["entries"] if x.get("workbook_id") == workbook), None)
    if (not entry or entry.get("conversion_status") != "not_converted" or entry.get("representative_item_id") is not None
        or entry.get("whole_workbook_complete") is not False or entry.get("admitted") is not False):
        raise ValueError("Level59 catalog source-only boundary drift")
    return entry


def project(data: dict) -> tuple[dict, dict]:
    whole, narrow, lines = data[WHOLE], data[NARROW], data[TXT]
    entry = boundary(data)
    if (whole.get("level") != 59 or whole.get("wbs") != "2.3.1.2.1" or whole.get("counted_sounded_attacks") != 1120
        or whole.get("silent_formations") != 48 or whole.get("counted_sounded_attacks_by_module") != COUNTS
        or whole.get("canonical_ids") is not None or whole.get("content_admitted") is not False
        or whole.get("runtime_import") is not False or whole.get("timing_or_audio_inferred") is not False
        or whole.get("source_reconciliation_status") != "D/E_variant_choice_pending"):
        raise ValueError("whole-Level59 candidate scope/authority drift")
    if (narrow.get("source_scope", {}).get("module") != "K" or narrow["source_scope"]["printed_attack_count"] != 64
        or narrow["candidate_status"].get("admitted") is not False
        or narrow["candidate_status"].get("canonical_id_allocated") is not False):
        raise ValueError("K narrow candidate authority drift")
    source = whole["source"]
    if (source["txt"]["path"] != TXT or source["txt"]["sha256"] != INPUTS[TXT]
        or source["pdf"]["path"] != PDF or source["pdf"]["sha256"] != INPUTS[PDF]
        or source["txt"]["lines"] != len(lines)):
        raise ValueError("source identity drift")
    map_rows = data[MAP]
    if isinstance(map_rows, dict):
        values = map_rows.get("rows", map_rows.get("sources", []))
    else:
        values = map_rows
    if not isinstance(values, list) or not any(str(row.get("level")) == "59" and row.get("txt_sha256") == INPUTS[TXT] for row in values):
        raise ValueError("frozen inventory Level59 row drift")
    spans = source_spans(lines)
    records = []
    counted = Counter()
    alt_counts = Counter()
    for module in HEAD:
        source_module = whole["modules"][module]
        events, variants, alternatives = [], [], []
        seen_rows: Counter = Counter()
        seen_headings: Counter = Counter()
        if module == "A":
            if (len(source_module["relative_fret_formulas"]) != 24 or len(source_module["silent_commands"]) != 48
                or source_module["silent_count"] != 48 or any(x["sounded"] is not False for x in source_module["silent_commands"])):
                raise ValueError("A silent command drift")
            formula_refs: Counter = Counter()
            formulas = []
            for formula in source_module["relative_fret_formulas"]:
                row = formula["source_row"]
                ref = row_ref(lines, spans[module], [row], formula_refs[row])
                formula_refs[row] += 1
                formulas.append(formula | {"source_refs": ref | {"pdf_page": 2}})
            command_row = "Silent commands: C major/minor and A major/minor; all three inversions; all four string sets. Name notes and bass role before release."
            command_ref = row_ref(lines, spans[module], [command_row]) | {"pdf_page": 2}
            silent_tasks = {"relative_fret_formulas": formulas,
                            "silent_commands": [command | {"source_refs": command_ref} for command in source_module["silent_commands"]],
                            "source_refs": {"pdf_pages": PAGES[module], "txt_span": spans[module]},
                            "event_count": 0}
            units = []
        else:
            silent_tasks = None
            units = source_module["pdf_counted_workout"] if module in ("D", "E") else source_module
        for no, unit in enumerate(units, 1):
            page = unit.get("pdf_page", PAGES[module][(no - 1) * len(PAGES[module]) // len(units)])
            if page not in PAGES[module]:
                raise ValueError("unit PDF page drift")
            ref = {"pdf_page": page, "txt_module_span": spans[module]}
            if unit.get("source_rows"):
                key = tuple(unit["source_rows"])
                ref |= row_ref(lines, spans[module], unit["source_rows"], seen_rows[key])
                seen_rows[key] += 1
            elif module in ("F", "G", "J"):
                ref |= structured_unit_ref(lines, spans[module], module, unit, seen_rows)
            ev = k_events(unit, narrow["call_response_pairs"][no - 1], no) if module == "K" else unit_events(module, no, unit, ref)
            start = len(events) + 1
            events.extend(ev)
            variants.append({"id": None, "source_unit_number": no,
                             "source_unit": {k: v for k, v in unit.items() if k != "source_rows"},
                             "source_event_ordinals": list(range(start, len(events) + 1)), "event_ids": None,
                             "runtime_eligible": False})
        if module in ("D", "E"):
            if source_module["curriculum_choice"] != "unresolved" or len(source_module["txt_alternate_variant"]) != 4:
                raise ValueError("D/E variant choice drift")
            for no, unit in enumerate(source_module["txt_alternate_variant"], 1):
                heading = unit["heading"]
                matches = [i + 1 for i in range(spans[module][0] - 1, spans[module][1]) if lines[i] == heading]
                if seen_headings[heading] >= len(matches):
                    raise ValueError("D/E TXT alternate heading drift")
                ref = {"txt_heading_line": matches[seen_headings[heading]], "txt_module_span": spans[module], "pdf_comparison_page": PAGES[module][0]}
                seen_headings[heading] += 1
                if unit.get("source_rows"):
                    key = tuple(unit["source_rows"])
                    ref |= row_ref(lines, spans[module], unit["source_rows"], seen_rows[key])
                    seen_rows[key] += 1
                ev = unit_events(module, no, unit, ref, alternative=True)
                alternatives.append({"id": None, "source": "TXT", "pdf_counted": False,
                                     "source_unit_number": no, "source_unit": {k: v for k, v in unit.items() if k != "source_rows"},
                                     "events": ev, "event_ids": None, "runtime_eligible": False})
                alt_counts[module] += len(ev)
        if len(events) != COUNTS[module]:
            raise ValueError(f"{module} attack total drift")
        counted[module] = len(events)
        records.append({"source_component": module, "source_heading": HEAD[module],
                        "source_txt_start_line": spans[module][0], "source_txt_end_line": spans[module][1],
                        "source_pdf_pages": PAGES[module], "identity_state": "unallocated",
                        "silent_tasks": silent_tasks, "alternative_authored_variants": alternatives,
                        "task_instructions": ({"call_response_pairs": [{"source_pair_order": p["source_pair_order"],
                            "question_chord": p["question_chord_token"], "answer_chord": p["answer_chord_token"],
                            "question_event_ordinals": [i for i in range((p["source_pair_order"] - 1) * 8 + 1, (p["source_pair_order"] - 1) * 8 + 5)],
                            "answer_event_ordinals": [i for i in range((p["source_pair_order"] - 1) * 8 + 5, p["source_pair_order"] * 8 + 1)],
                            "last_root_sustain_instruction": whole["modules"]["K"][p["source_pair_order"] - 1]["last_root_sustain_instruction"],
                            "sustain_duration_q": None, "source_refs": p["source_refs"]}
                            for p in narrow["call_response_pairs"]]} if module == "K" else None),
                        "schema1_fields": {"id": None, "workbook_id": None, "module_id": None,
                            "legacy_level": 59, "title": f"Level 59 component {module}", "kind": "mixed",
                            "content_revision": None, "lineage": None, "runtime_eligible": False,
                            "source_refs": None, "events": events, "variants": variants,
                            "resource_requirements": [],
                            "timing": {"status": "unresolved", "unit": "quarter", "fixed_bpm": None},
                            "ambiguities": UNRESOLVED}})
    if sum(counted.values()) != 1120 or dict(alt_counts) != {"D": 48, "E": 40}:
        raise ValueError("whole/alternative totals drift")
    proposal = {"proposal_version": "level059-unallocated-schema1-fields.1", "wbs_id": "2.3.1.2.1",
                "classification": "Build-only, nonimportable schema1 field proposal", "legacy_level": 59,
                "canonical_ids_allocated": False, "schema1_importable": False,
                "whole_workbook_complete": False, "runtime_eligible": False, "admitted": False,
                "counts": {"components": 11, "pdf_counted_sounded_attacks": 1120,
                           "pdf_counted_by_module": dict(counted), "silent_formations_not_events": 48,
                           "txt_authored_alternative_attacks_not_counted": dict(alt_counts),
                           "call_response_pairs": 8, "call_response_positions": 64},
                "source": source, "source_difference_ledger": whole["source_difference_ledger"],
                "pdf_guidance": whole["pdf_guidance"],
                "practice_progression_pdf": whole["practice_progression_pdf"],
                "practice_progression_txt": whole["practice_progression_txt"],
                "mastery_gate_pdf": whole["mastery_gate_pdf"], "mastery_gate_txt": whole["mastery_gate_txt"],
                "records": records}
    handoff = {"handoff_version": "level059-allocation-handoff.1", "wbs_id": "2.3.1.2.1",
               "catalog_workbook_id": entry["workbook_id"], "catalog_role": entry["catalog_role"],
               "existing_level059_records": 0, "existing_level059_workbook_entities": 0,
               "proposed_component_partition": list(HEAD), "pdf_counted_sounded_attacks": 1120,
               "silent_formations_not_events": 48, "txt_alternative_attacks_not_counted": 88,
               "canonical_ids_allocated": False, "admitted": False,
               "required_decisions": ["Reconcile Module D/E PDF and TXT authored workouts before choosing a runtime variant.",
                                      "Choose the PDF/TXT phase-ten progression ordering and review source-specific guidance.",
                                      "Allocate stable identities and lineage after registry reservation review.",
                                      "Authorize performed timing, picking where not printed, sustain duration, and MIDI register before runtime import."]}
    return proposal, handoff


def products(root: Path) -> dict[str, object]:
    proposal, handoff = project(inputs(root))
    manifest = {"manifest_version": "level059-input-pins.1", "inputs": [
        {"path": rel, "bytes": (root / rel).stat().st_size, "sha256": digest}
        for rel, digest in INPUTS.items()]}
    summary = {"summary_version": "level059-schema1-unallocated-summary.1",
               "proposal_sha256": sha(encoded(proposal)), "handoff_sha256": sha(encoded(handoff)),
               "pdf_counted_sounded_attacks": 1120, "silent_formations": 48,
               "txt_alternative_attacks_not_counted": 88,
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
    print(f"LEVEL59 {mode.upper()} PASS counted=1120 silent=48 txt_alternative=88 admitted=false")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("build", "verify"))
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    run(args.mode, args.root.resolve())
