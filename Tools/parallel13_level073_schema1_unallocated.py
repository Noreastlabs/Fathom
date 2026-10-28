#!/usr/bin/env python3
"""Project sealed whole-Level73 modulation source into unallocated schema1 fields."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path

import curriculum_level073_whole_candidate as source


ROOT = Path(__file__).resolve().parents[1]
OUT = Path("Build/parallel-13/level073-schema1-unallocated-r01")
CANDIDATE = Path("Build/parallel-11/2.3.1.3.1-level073-whole-r01/candidate-c.json")
FOUNDATION = Path("Content/controls/curriculum-v1/package.json")
PINS = {
    CANDIDATE: "789edc836deba29120cf5f49903be435e1064eabefb8e723fd6d880a82b25991",
    FOUNDATION: "766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255",
    Path("Results/primary/20260912T100538Z-2.1.1.2.1-r02-evidence/schema-freeze.json"): "0659fa962a5c933a2bcf3045772b6fe5b05b4deefb3511f5dcb68af51088de95",
    Path("Tools/curriculum_level073_whole_candidate.py"): "291f0c7e10ee7da889c2f9576bc9b0fb2d4cbda35094bfc72e644804c8905e54",
    Path("Results/parallel-11/curriculum/20260923T164500Z-2.3-level073-whole-r01-results.md"): "be06b737faf4060929e5219e5ff62ebf8605e91e50fe664a5cd41286d16abbca",
    Path(source.TXT[0]): source.TXT[1],
    Path(source.PDF[0]): source.PDF[1],
    Path(source.MAP[0]): source.MAP[1],
}
UNRESOLVED = [
    "canonical workbook/module/item/event/variant IDs, lineage and revision",
    "fixed BPM, absolute onset/duration, note-per-click and performed mastery",
    "three A PDF barline sustain instructions conflict with printed note changes",
    "C two-voice worksheet simultaneity has no selected execution order",
    "B emphasis, F final tonic, H performance passes and I improvisation ladder remain instructions",
    "Curriculum review and runtime admission",
]


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


def pins() -> None:
    for rel, expected in PINS.items():
        path = ROOT / rel
        need(path.is_file() and not path.is_symlink() and
             path.resolve().is_relative_to(ROOT.resolve()), f"INPUT_PATH {rel}")
        need(sha(path.read_bytes()) == expected, f"INPUT_PIN {rel}")


def foundation_status() -> None:
    package = json.loads((ROOT / FOUNDATION).read_text())
    entry = [e for e in package["workbook_catalog"]["entries"]
             if e["workbook_id"] == "fg:workbook:000073"]
    need(len(package["records"]) == 659 and
         not any(r.get("legacy_level") == 73 for r in package["records"]) and
         len(entry) == 1 and entry[0]["representative_item_id"] is None and
         entry[0]["conversion_status"] == "not_converted" and
         entry[0]["whole_workbook_complete"] is False and
         all(entry[0][k] is False for k in
             ("admitted", "imported", "runtime_admitted", "runtime_eligible")),
         "FOUNDATION_ADMISSION")


def event_fields(item: dict, *, c_voice: int | None = None,
                 c_bar: int | None = None) -> dict:
    string, fret, note = item["string"], item["fret"], item["note"]
    need(string in source.OPEN and isinstance(fret, int) and 0 <= fret <= 24 and
         note in source.PC and
         (source.OPEN[string] + fret) % 12 == source.PC[note] and
         item["pitch_class"] == source.PC[note], "EVENT_PITCH")
    if c_voice is None:
        need(isinstance(item["source_column"], int) and
             item["source_column"] >= 0 and
             isinstance(item["source_bar_ordinal"], int) and
             item["source_bar_ordinal"] >= 1 and
             isinstance(item["role_slot_raw"], str), "EVENT_SOURCE_POSITION")
    else:
        need(c_voice in (1, 2) and c_bar in range(1, 5) and
             item["bar"] == c_bar and item["role"] in source.ROLE_OFFSET and
             item["chord"] and
             (source.PC[source.chord_root(item["chord"])] +
              source.ROLE_OFFSET[item["role"]]) % 12 == source.PC[note] and
             source.PC[note] in source.chord_pcs(item["chord"]),
             "C_VOICE_ROLE")
    return {"event_id": None, "kind": "sounded_note",
            "midi": source.OPEN[string] + fret,
            "string": string, "fret": fret,
            "onset_q": None, "duration_q": None}


def project(candidate: dict) -> tuple[dict, dict]:
    need(candidate["schema"] == "fathom.level073.detached-source-candidate.1" and
         candidate["wbs"] == "2.3.1.3.1" and
         candidate["status"] == "non_admitted" and
         candidate["admitted"] is False and
         candidate["printed_tones_by_module"] == source.EXPECTED and
         candidate["printed_sounding_tones"] == 652 and
         all(candidate[k] is None for k in
             ("canonical_id", "exercise_id", "onset_q", "duration_q",
              "fixed_bpm", "executable_events", "sounding_midi_events")),
         "SOURCE_SCOPE")
    row = candidate["source_map_row"]
    need(row["level"] == 73 and row["section"] == "X" and
         row["representative_item_id"] is None and
         row["conversion_status"] == "not_converted" and
         row["review"] == "Pending" and
         row["stable_ids_assigned"] is False and
         all(row[k] is False for k in
             ("runtime_eligible", "imported", "admitted")) and
         candidate["source"] ==
         {key: {"path": spec[0], "sha256": spec[1], "bytes": spec[2]}
          for key, spec in (("txt", source.TXT), ("pdf", source.PDF),
                            ("source_map", source.MAP))},
         "SOURCE_LINEAGE")
    guidance = candidate["guidance"]
    need(len(guidance["txt_full_lines"]) == 668 and
         len(guidance["pdf_full_extracted_pages"]) == 20 and
         len(candidate["source_sections"]) == 9 and
         len(candidate["source_ambiguities"]) == 3 and
         [a["printed_barline_notes"] for a in candidate["source_ambiguities"]] ==
         [["G", "E"], ["G", "C"], ["D", "B"]] and
         all(a["status"] == "pending_curriculum_review" for a in
             candidate["source_ambiguities"]) and
         any(d["kind"] == "PDF_A_barline_sustain_conflicts_with_three_printed_cells"
             for d in candidate["source_differences"]),
         "SOURCE_GUIDANCE_AMBIGUITY")
    need(set(candidate["modules"]) == set(source.CELL_COUNTS) and
         len(candidate["guide_tone_worksheets"]) == 6,
         "MODULE_SCOPE")

    records: list[dict] = []
    mapping: list[dict] = []
    module_counts: dict[str, dict] = {}
    for letter in source.KEYS:
        units = (candidate["guide_tone_worksheets"] if letter == "C" else
                 candidate["modules"][letter])
        expected_units = 6 if letter == "C" else source.CELL_COUNTS[letter]
        need(len(units) == expected_units, f"MODULE_UNIT_COUNT {letter}")
        tones = 0
        for index, unit in enumerate(units, 1):
            projected = []
            if letter == "C":
                need(unit["printed_tones"] == 8 and len(unit["chords"]) == 4 and
                     len(unit["voices"]) == 2 and unit["pdf_ref"] == "L73-PDF-p7",
                     f"C_WORKSHEET {index}")
                for voice in unit["voices"]:
                    number = voice["voice"]
                    need(number in (1, 2) and len(voice["events"]) == 4 and
                         voice["string"] in source.OPEN,
                         f"C_VOICE {index}:{number}")
                    for item in voice["events"]:
                        fields = event_fields(item, c_voice=number, c_bar=item["bar"])
                        need(item["chord"] == unit["chords"][item["bar"] - 1],
                             f"C_CHORD {index}:{number}:{item['bar']}")
                        projected.append({"source_entry_index": len(projected) + 1,
                                          "schema1_fields": fields,
                                          "source_attack": copy.deepcopy(item),
                                          "printed_note": item["note"],
                                          "printed_role": item["role"],
                                          "source_voice": number,
                                          "source_bar": item["bar"],
                                          "simultaneity_group": f"bar-{item['bar']}",
                                          "execution_order": None,
                                          "txt_ref": voice["txt_ref"],
                                          "pdf_ref": unit["pdf_ref"]})
            else:
                need(unit["printed_tones"] == source.CELL_TONES[letter] and
                     len(unit["events"]) == unit["printed_tones"] and
                     unit["pdf_ref"].startswith("L73-PDF-p") and
                     unit["txt_ref"].startswith("L73-TXT-L"),
                     f"CELL_SOURCE {letter}{index}")
                for ordinal, item in enumerate(unit["events"], 1):
                    fields = event_fields(item)
                    raw_role = item["role_slot_raw"].strip("-|")
                    if letter in "BFGH":
                        chord = unit["chords"][item["source_bar_ordinal"] - 1]
                        need(raw_role in source.ROLE_OFFSET and
                             (source.PC[source.chord_root(chord)] +
                              source.ROLE_OFFSET[raw_role]) % 12 ==
                             source.PC[item["note"]] and
                             source.PC[item["note"]] in source.chord_pcs(chord),
                             f"CHORD_ROLE {letter}{index}:{ordinal}")
                    projected.append({"source_order_ordinal": ordinal,
                                      "schema1_fields": fields,
                                      "source_attack": copy.deepcopy(item),
                                      "printed_note": item["note"],
                                      "printed_role_slot": item["role_slot_raw"],
                                      "source_bar": item["source_bar_ordinal"],
                                      "source_column": item["source_column"],
                                      "txt_ref": unit["txt_ref"],
                                      "pdf_ref": unit["pdf_ref"]})
                if letter == "A":
                    need(unit["barline_repeats_note"] ==
                         (unit["events"][3]["note"] == unit["events"][4]["note"]),
                         f"A_BARLINE {index}")
            need(len(projected) == unit["printed_tones"],
                 f"UNIT_TONES {letter}{index}")
            tones += len(projected)
            key = f"L73-{letter}-{index:02d}"
            provenance = {"txt_path": source.TXT[0],
                          "txt_ref": unit["txt_ref"],
                          "pdf_path": source.PDF[0],
                          "pdf_ref": unit["pdf_ref"],
                          "source_candidate_sha256": PINS[CANDIDATE]}
            payload = {"source_local_key": key, "identity_state": "unallocated",
                       "source_unit_sha256": sha(encoded(unit)),
                       "source_unit": copy.deepcopy(unit),
                       "source_provenance": provenance,
                       "schema1_fields": {"id": None, "workbook_id": None,
                                          "module_id": None, "lineage": None,
                                          "content_revision": None,
                                          "legacy_level": 73,
                                          "title": (unit.get("route") or
                                                    f"Level 73 module {letter} unit {index}"),
                                          "kind": ("two_voice_guide_tone_worksheet"
                                                   if letter == "C" else
                                                   "modulation_notation_cell"),
                                          "runtime_eligible": False,
                                          "source_refs": [unit["txt_ref"], unit["pdf_ref"]],
                                          "events": projected, "variants": [],
                                          "timing": {"status": "unresolved",
                                                     "onset_q": None,
                                                     "duration_q": None,
                                                     "fixed_bpm": None,
                                                     "note_per_click": None},
                                          "resource_requirements": [],
                                          "ambiguities": UNRESOLVED}}
            records.append(payload)
            mapping.append({"source_local_key": key,
                            "source_unit_sha256": payload["source_unit_sha256"],
                            "module": letter, "unit": index,
                            "printed_tones": len(projected),
                            "two_voice_simultaneous": letter == "C",
                            "txt_ref": unit["txt_ref"],
                            "pdf_ref": unit["pdf_ref"]})
        need(tones == source.EXPECTED[letter], f"MODULE_TONES {letter}")
        module_counts[letter] = {"units": len(units), "printed_tones": tones}
    need(len(records) == 61 and
         sum(x["printed_tones"] for x in module_counts.values()) == 652 and
         sum(x["printed_tones"] for k, x in module_counts.items() if k != "C") == 604,
         "WHOLE_COUNTS")
    conflicts = [r for r in records if r["source_local_key"].startswith("L73-A-")
                 and r["source_unit"]["barline_repeats_note"] is False]
    need(len(conflicts) == 3 and
         [r["source_unit"]["route"] for r in conflicts] ==
         [a["route"] for a in candidate["source_ambiguities"]],
         "A_CONFLICT_MAPPING")
    proposal = {"schema": "fathom-level073-schema1-field-proposal.1",
                "classification": "build_only_unallocated_nonimportable",
                "wbs_id": "2.3.1.3.1", "legacy_level": 73,
                "source_candidate_sha256": PINS[CANDIDATE],
                "source": copy.deepcopy(candidate["source"]),
                "source_map_row": copy.deepcopy(row),
                "source_sections": copy.deepcopy(candidate["source_sections"]),
                "source_ambiguities": copy.deepcopy(candidate["source_ambiguities"]),
                "source_differences": copy.deepcopy(candidate["source_differences"]),
                "guidance": copy.deepcopy(guidance),
                "module_counts": module_counts, "records": records,
                "printed_sounding_tones": 652,
                "canonical_ids_allocated": False, "runtime_eligible": False,
                "admitted": False, "whole_workbook_complete": False,
                "timing_resolved": False, "curriculum_signoff": False}
    handoff = {"schema": "fathom-level073-schema1-allocation-handoff.1",
               "field_proposal_sha256": sha(encoded(proposal)),
               "source_candidate_sha256": PINS[CANDIDATE],
               "records": mapping, "module_counts": module_counts,
               "printed_sounding_tones": 652,
               "A_pdf_barline_conflicts": copy.deepcopy(candidate["source_ambiguities"]),
               "unresolved": UNRESOLVED,
               "next_step": "independent source/music review before ID allocation or import",
               "admitted": False, "runtime_eligible": False,
               "whole_workbook_complete": False}
    return proposal, handoff


def derive() -> tuple[dict, dict]:
    pins()
    foundation_status()
    sealed = json.loads((ROOT / CANDIDATE).read_text())
    need(sealed == source.build_candidate(ROOT), "P11_REPLAY_DRIFT")
    return project(sealed)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "verify"))
    args = parser.parse_args()
    proposal, handoff = derive()
    files = {"field-proposal.json": encoded(proposal),
             "allocation-handoff.json": encoded(handoff)}
    if args.command == "build":
        target = ROOT / OUT
        need(not target.exists() and not target.is_symlink(), "OUTPUT_EXISTS")
        target.mkdir(parents=True)
        for name, raw in files.items():
            (target / name).write_bytes(raw)
    for name, raw in files.items():
        need((ROOT / OUT / name).read_bytes() == raw, f"OUTPUT_DRIFT {name}")
    print(json.dumps({"status": "verified_unallocated_nonadmitted",
                      "units": len(proposal["records"]),
                      "printed_sounding_tones": 652,
                      "A_pdf_barline_conflicts": 3,
                      "field_proposal_sha256": sha(files["field-proposal.json"]),
                      "handoff_sha256": sha(files["allocation-handoff.json"])},
                     sort_keys=True))


if __name__ == "__main__":
    main()
