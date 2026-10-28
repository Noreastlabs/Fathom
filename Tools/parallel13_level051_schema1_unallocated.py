#!/usr/bin/env python3
"""Project the sealed whole Level51 source into unallocated schema1-shaped fields."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path

import curriculum_level051_whole_candidate as source


ROOT = Path(__file__).resolve().parents[1]
OUT = Path("Build/parallel-13/level051-schema1-unallocated-r01")
CANDIDATE = Path("Build/parallel-09/2.3.1.2.1-level051-whole-r01/level051-whole-candidate-01.json")
RESULT = Path("Results/parallel-09/exercises/conversion/20260923T160422Z-2.3.1.2.1-level051-whole-r01-results.md")
SCHEMA = Path("Results/primary/20260912T100538Z-2.1.1.2.1-r02-evidence/schema-freeze.json")
FOUNDATION = Path("Content/controls/curriculum-v1/package.json")
PINS = {
    CANDIDATE: "dfa18b59a6c3337cd2c75b672837e636d92fe5b3d9f91a0b2803916ea3372a6c",
    RESULT: "cef0593e68ce4eb26e2bd62ca26dd192242ba9d9174ae93d4fae87e021defe44",
    SCHEMA: "0659fa962a5c933a2bcf3045772b6fe5b05b4deefb3511f5dcb68af51088de95",
    FOUNDATION: "766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255",
    source.TXT_REL: source.TXT_SHA,
    source.PDF_REL: source.PDF_SHA,
    Path("Tools/curriculum_level051_whole_candidate.py"): "9b6d403ea5396f2297d6566a94390cf3b36ab702a4adae65b4be02822e71a8dd",
}
STRINGS = source.STRINGS
OPEN = dict(zip(STRINGS, source.OPEN, strict=True))
EXPECTED_ITEMS = {"A": 28, "B": 5, "C": 14, "D": 14, "E": 14,
                  "F": 12, "G": 4, "H": 4, "I": 8, "J": 4, "K": 2}
UNRESOLVED = ["canonical workbook/module/item/event/variant IDs and lineage",
              "absolute BPM, note-per-click, beat mapping and quarter-note onset/duration",
              "J4 arpeggio string order within each four-attack bar",
              "Curriculum disposition and runtime admission"]


class ProposalError(ValueError):
    pass


def need(ok: bool, code: str) -> None:
    if not ok:
        raise ProposalError(code)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def encoded(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False,
                       separators=(",", ":")) + "\n").encode()


def pin() -> None:
    for path, expected in PINS.items():
        actual = ROOT / path
        need(actual.is_file() and not actual.is_symlink() and
             actual.resolve().is_relative_to(ROOT.resolve()), f"INPUT_PATH {path}")
        need(sha(actual.read_bytes()) == expected, f"INPUT_PIN {path}")


def foundation_status() -> None:
    pkg = json.loads((ROOT / FOUNDATION).read_text())
    need(len(pkg["records"]) == 659 and
         not any(r.get("legacy_level") == 51 for r in pkg["records"]), "FOUNDATION_RECORD")
    entries = [e for e in pkg["workbook_catalog"]["entries"]
               if e["workbook_id"] == "fg:workbook:000051"]
    need(len(entries) == 1 and entries[0]["conversion_status"] == "not_converted" and
         entries[0]["representative_item_id"] is None and
         entries[0]["whole_workbook_complete"] is False and
         all(entries[0][k] is False for k in
             ("admitted", "imported", "runtime_admitted", "runtime_eligible")),
         "CATALOG_ADMISSION")


def chord_parts(chord: str) -> tuple[str, str]:
    quality = "minor" if chord.endswith("m") else "major"
    root = chord[:-1] if quality == "minor" else chord
    need(root in source.PC, "CHORD_ROOT")
    return root, quality


def voicing_tables(candidate: dict) -> dict[tuple[str, str], dict]:
    table = {(v["shape"], v["chord"]): v for module in ("C", "D")
             for v in candidate["modules"][module]}
    need(len(table) == 28, "VOICING_TABLE")
    for key, row in table.items():
        need(row["shape"] == key[0] and row["chord"] == key[1] and
             len(row["frets"]) == len(row["fingers"]) ==
             len(row["notes_by_string"]) == 6, "VOICING_ROW")
        for string, fret, finger, note in zip(STRINGS, row["frets"],
                                              row["fingers"], row["notes_by_string"], strict=True):
            if fret is None:
                need(finger is None and note is None, "MUTED_CONTACT")
            else:
                need(finger in (1, 2, 3, 4) and note in source.PC and
                     (OPEN[string] + fret) % 12 == source.PC[note], "PITCH_CONTACT")
    return table


def contacts(shape: str, chord: str, root_fret: int, table: dict,
             partial: bool = False) -> dict:
    root, quality = chord_parts(chord)
    need(shape in ("E", "A") and isinstance(root_fret, int) and 1 <= root_fret <= 12 and
         (OPEN[shape] + root_fret) % 12 == source.PC[root], "ROOT_FRET")
    row = table.get((shape, chord))
    if row is not None:
        need(row["root_fret"] == root_fret and row["quality"] == quality,
             "PRINTED_VOICING_DRIFT")
        frets, fingers = row["frets"], row["fingers"]
        names = row["notes_by_string"]
        authority = "printed_C_D_voicing_table"
    else:
        frets = source._expected_frets(shape, quality, root_fret)
        fingers = ({"E": {"major": [1, 3, 4, 2, 1, 1],
                           "minor": [1, 3, 4, 1, 1, 1]},
                    "A": {"major": [None, 1, 3, 3, 3, 1],
                           "minor": [None, 1, 3, 4, 2, 1]}}[shape][quality])
        names = [None] * 6
        authority = "derived_from_printed_shape_formula_and_finger_family"
    active = ("D", "G", "B", "e") if shape == "E" else ("A", "D", "G", "B")
    members = []
    for string, fret, finger, name in zip(STRINGS, frets, fingers, names, strict=True):
        if fret is None or (partial and string not in active):
            continue
        midi = OPEN[string] + fret
        if name is not None:
            need(source.PC[name] == midi % 12, "PRINTED_PITCH")
        members.append({"string": string, "fret": fret, "finger": finger,
                        "midi": midi, "pitch_class": midi % 12,
                        "printed_note": name})
    need(len(members) == (4 if partial else (6 if shape == "E" else 5)),
         "CONTACT_COUNT")
    return {"chord": chord, "shape": shape, "quality": quality,
            "root_fret": root_fret, "partial": partial,
            "members": members, "authority": authority}


def event(ordinal: int, module: str, item: int, line: int, page: int,
          kind: str, chord: dict | None, selected: dict | None = None,
          bar: int | None = None) -> dict:
    need(1 <= line <= 466 and 1 <= page <= 20, "PROVENANCE_RANGE")
    return {"source_local_ordinal": ordinal,
            "schema1_fields": {"event_id": None, "onset_q": None,
                               "duration_q": None, "kind": kind,
                               "midi": selected["midi"] if selected else None,
                               "string": selected["string"] if selected else None,
                               "fret": selected["fret"] if selected else None,
                               "finger": selected["finger"] if selected else None},
            "source_attack": {"module": module, "item": item,
                              "txt_line": line, "pdf_page": page, "bar": bar,
                              "kind": kind, "sounded": True},
            "sounding_members": ([selected] if selected else
                                 ([] if kind == "arpeggio_pick_string_unresolved" else
                                  (chord["members"] if chord else []))),
            "possible_voicing_members": chord["members"] if chord else
                                        ([selected] if selected else []),
            "chord": chord["chord"] if chord else None,
            "voicing_authority": chord["authority"] if chord else "printed_partial_barre_stage"}


def item_events(module: str, item: int, row: dict, table: dict) -> tuple[list[dict], list[dict]]:
    line, page = row["txt_line"], row["pdf_page"]
    events: list[dict] = []
    silent: list[dict] = []

    def append(kind: str, chord: dict | None, selected: dict | None = None,
               bar: int | None = None) -> None:
        events.append(event(len(events) + 1, module, item, line, page,
                            kind, chord, selected, bar))

    if module == "A":
        need(row["sounded_attack_count"] == 0 and
             row["silent_full_landing"] == row["silent_partial_landing"] == 1,
             "SILENT_SOURCE")
        shape = row["root_string"]
        chord = row["root"] + ("m" if row["quality"] == "minor" else "")
        for partial in (False, True):
            grip = contacts(shape, chord, row["root_fret"], table, partial)
            silent.append({"kind": "silent_chord_landing", "sounded": False,
                           "phase": "partial" if partial else "full", "voicing": grip,
                           "txt_line": line, "pdf_page": page})
    elif module == "B":
        need(row["repeat_frets"] == [5, 7] and
             len(row["active_strings"]) == row["picked_attacks_per_fret"] and
             row["frets"] == [5] * len(row["active_strings"]), "BARRE_STAGE")
        for fret in row["repeat_frets"]:
            for string in row["active_strings"]:
                need(string in STRINGS, "BARRE_STRING")
                selected = {"string": string, "fret": fret, "finger": 1,
                            "midi": OPEN[string] + fret,
                            "pitch_class": (OPEN[string] + fret) % 12,
                            "printed_note": None}
                append("picked_note", None, selected)
    elif module in ("C", "D"):
        grip = contacts(row["shape"], row["chord"], row["root_fret"], table)
        need([m["fret"] for m in grip["members"]] ==
             [f for f in row["frets"] if f is not None], "SCAN_VOICING")
        members = grip["members"]
        for selected in [*members, *reversed(members)]:
            append("picked_note", grip, selected)
        need(len(events) == row["scan_attack_count"], "SCAN_COUNT")
    elif module in ("E", "F", "G"):
        chords = row["chords"]
        expected = row["attack_count"]
        need(len(chords) == expected, "GRID_COUNT")
        for index, chord in enumerate(chords):
            if module == "E":
                shape, fret, partial = row["shape"], row["root_fret"], row["shape"] == "A"
            elif module == "F":
                shape = "E" if chord == row["E_chord"] else "A"
                need(chord in (row["E_chord"], row["A_chord"]), "FAMILY_CHORD")
                fret, partial = row["shared_fret"], False
            else:
                shape, fret, partial = row["shape"], row["frets"][index], False
            grip = contacts(shape, chord, fret, table, partial)
            append("strum_attack", grip)
    else:
        need(module in ("H", "I", "J", "K"), "MODULE")
        bars = row["bars"]
        need(len(bars) == (16 if module == "K" else 4), "BAR_COUNT")
        for bar_index, bar in enumerate(bars, 1):
            need(bar["onset_q"] is None and bar["duration_q"] is None and
                 bar["sounded_attacks"] == 4, "BAR_TIMING_OR_COUNT")
            need(chord_parts(bar["chord"])[1] == bar["quality"], "BAR_CHORD_QUALITY")
            if module == "I" and item >= 5 and bar_index == 3:
                need(bar["quality"] == "major", "MINOR_ROUTE_MAJOR_V")
            grip = contacts(bar["shape"], bar["chord"], bar["root_fret"], table,
                            module == "J")
            for _ in range(4):
                kind = "arpeggio_pick_string_unresolved" if module == "J" and item == 4 else "strum_attack"
                append(kind, grip, bar=bar_index)
        need(len(events) == row["sounded_attack_count"], "PROGRESSION_COUNT")
    return events, silent


def project(candidate: dict) -> tuple[dict, dict]:
    need(candidate["schema"] == "fathom-level051-whole-detached-candidate-v1" and
         candidate["level"] == 51 and candidate["wbs_id"] == "2.3.1.2.1" and
         candidate["complete_sounded_workload_attacks"] == 996 and
         candidate["silent_chord_landings"] == 56 and
         candidate["module_sounded_attacks"] == source.ATTACKS and
         set(candidate["modules"]) == set(EXPECTED_ITEMS) and
         all(candidate[k] is None for k in
             ("canonical_item_id", "canonical_variant_id", "fixed_bpm", "note_per_click",
              "onset_q", "duration_q", "performed_result")) and
         all(candidate[k] is False for k in
             ("runtime_eligible", "runtime_admitted", "imported", "admitted",
              "curriculum_signoff")), "SOURCE_SCOPE")
    need(candidate["pdf_reconciliation"]["discrepancies"] == [] and
         candidate["pdf_reconciliation"]["pages"] == 20 and
         len(candidate["pdf_reconciliation"]["partial_diagram_examples"]) == 4,
         "PDF_SCOPE")
    table = voicing_tables(candidate)
    for diagram in candidate["pdf_reconciliation"]["partial_diagram_examples"]:
        shape = diagram["shape"]
        root_fret = diagram["frets"].get("e" if shape == "E" else "A")
        grip = contacts(shape, diagram["chord"], root_fret, table, partial=True)
        need(diagram["pdf_page"] == 4 and diagram["visual_reviewed"] is True and
             diagram["active_strings"] == [m["string"] for m in grip["members"]] and
             diagram["frets"] == {m["string"]: m["fret"] for m in grip["members"]} and
             diagram["fingers"] == {m["string"]: m["finger"] for m in grip["members"]},
             "PDF_DIAGRAM")
    records = []
    map_rows = []
    module_counts = {}
    for module in EXPECTED_ITEMS:
        rows = candidate["modules"][module]["natural_calls"] if module == "A" else candidate["modules"][module]
        need(len(rows) == EXPECTED_ITEMS[module], f"ITEM_COUNT {module}")
        attacks = landings = 0
        for index, row in enumerate(rows, 1):
            need(row["onset_q"] is None and row["duration_q"] is None
                 if "onset_q" in row else True, "ITEM_TIMING")
            item = ({**row, "txt_line": candidate["modules"]["A"]["txt_line"],
                     "pdf_page": candidate["modules"]["A"]["pdf_page"]}
                    if module == "A" else row)
            events, silent = item_events(module, index, item, table)
            attacks += len(events)
            landings += len(silent)
            key = f"L51-{module}-{index:02d}"
            ref = {"txt": f"L51-TXT1-{item['txt_line']}",
                   "pdf": f"L51-PDF1-p{item['pdf_page']}",
                   "txt_line": item["txt_line"], "pdf_page": item["pdf_page"]}
            record = {"source_local_key": key, "identity_state": "unallocated",
                      "source_item_sha256": sha(encoded(row)), "source_item": copy.deepcopy(row),
                      "source_provenance": ref, "source_silent_landings": silent,
                      "schema1_fields": {"id": None, "workbook_id": None,
                                         "module_id": None, "lineage": None,
                                         "content_revision": None,
                                         "legacy_level": 51,
                                         "title": f"Level 51 module {module} item {index}",
                                         "kind": "chord_formation" if module == "A" else "chord_attack",
                                         "runtime_eligible": False,
                                         "source_refs": [ref["txt"], ref["pdf"]],
                                         "events": events, "variants": [],
                                         "timing": {"status": "unresolved", "unit": "quarter",
                                                    "onset_q": None, "duration_q": None,
                                                    "fixed_bpm": None, "note_per_click": None},
                                         "resource_requirements": [],
                                         "ambiguities": UNRESOLVED}}
            records.append(record)
            map_rows.append({"source_local_key": key, "module": module,
                             "source_item_sha256": record["source_item_sha256"],
                             **ref, "sounded_attacks": len(events),
                             "silent_landings": len(silent)})
        need(attacks == source.ATTACKS[module], f"MODULE_ATTACKS {module}")
        module_counts[module] = {"items": len(rows), "sounded_attacks": attacks,
                                 "silent_landings": landings}
    need(len(records) == 109 and sum(x["sounded_attacks"] for x in module_counts.values()) == 996 and
         sum(x["silent_landings"] for x in module_counts.values()) == 56,
         "WHOLE_COUNTS")
    pdf = candidate["pdf_reconciliation"]
    proposal = {"schema": "fathom-level051-schema1-field-proposal.1",
                "classification": "build_only_unallocated_nonimportable",
                "wbs_id": "2.3.1.2.1", "legacy_level": 51,
                "source_candidate_sha256": PINS[CANDIDATE],
                "source": candidate["source"], "records": records,
                "module_counts": module_counts,
                "pdf_only": {"partial_diagrams": pdf["partial_diagram_examples"],
                             "guidance_pages": pdf["pdf_only_guidance_pages"],
                             "extracted_page_text": pdf["extracted_page_text"],
                             "limitations": "PDF text is search metadata; P09 visually reviewed original diagram pages."},
                "source_instructions": candidate["instructions"],
                "canonical_ids_allocated": False, "runtime_eligible": False,
                "admitted": False, "whole_workbook_complete": False,
                "timing_resolved": False, "curriculum_signoff": False}
    handoff = {"schema": "fathom-level051-schema1-allocation-handoff.1",
               "field_proposal_sha256": sha(encoded(proposal)),
               "source_candidate_sha256": PINS[CANDIDATE],
               "records": map_rows, "module_counts": module_counts,
               "next_step": "independent source/musical review before any ID allocation or native import",
               "unresolved": UNRESOLVED,
               "admitted": False, "runtime_eligible": False,
               "whole_workbook_complete": False}
    return proposal, handoff


def derive() -> tuple[dict, dict]:
    pin()
    foundation_status()
    sealed = json.loads((ROOT / CANDIDATE).read_text())
    replay = source.build_candidate()
    need(sealed == replay, "P09_REPLAY_DRIFT")
    return project(sealed)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "verify"))
    args = parser.parse_args()
    proposal, handoff = derive()
    files = {"field-proposal.json": encoded(proposal),
             "allocation-handoff.json": encoded(handoff)}
    if args.command == "build":
        dest = ROOT / OUT
        need(not dest.exists() and not dest.is_symlink(), "OUTPUT_EXISTS")
        dest.mkdir(parents=True)
        for name, raw in files.items():
            (dest / name).write_bytes(raw)
    for name, raw in files.items():
        need((ROOT / OUT / name).read_bytes() == raw, f"OUTPUT_DRIFT {name}")
    print(json.dumps({"status": "verified_unallocated_nonadmitted",
                      "items": len(proposal["records"]), "sounded_attacks": 996,
                      "silent_landings": 56,
                      "field_proposal_sha256": sha(files["field-proposal.json"]),
                      "handoff_sha256": sha(files["allocation-handoff.json"])}, sort_keys=True))


if __name__ == "__main__":
    main()
