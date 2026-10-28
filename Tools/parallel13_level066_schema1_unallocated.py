#!/usr/bin/env python3
"""Project sealed whole-Level66 source into unallocated schema1 fields."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path

import curriculum_level066_positions_candidate as narrow
import parallel_07_level066_whole_candidate as whole


ROOT = Path(__file__).resolve().parents[1]
OUT = Path("Build/parallel-13/level066-schema1-unallocated-r01")
CANDIDATE = Path("Build/parallel-07/2.3.1.2.1-level066-whole-r01/level066_whole_candidate.json")
NARROW = Path("Build/parallel-09/2.3-level066-positions-r01/candidate-final-02.json")
FOUNDATION = Path("Content/controls/curriculum-v1/package.json")
PINS = {
    CANDIDATE: "816290478a779c72715b1947fad609d0b71514aa7b25e524b8710889cd488881",
    NARROW: "05d8fe02ac7ec2a849f812b155bdc44b74929dd296cd9539aa7b3a92e33a7ce3",
    FOUNDATION: "766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255",
    Path("Results/primary/20260912T100538Z-2.1.1.2.1-r02-evidence/schema-freeze.json"): "0659fa962a5c933a2bcf3045772b6fe5b05b4deefb3511f5dcb68af51088de95",
    Path("Tools/parallel_07_level066_whole_candidate.py"): "874869df0bf8ac3681835171b20feab2880ce76dce3add29fbfc9444d18077b6",
    Path("Tools/curriculum_level066_positions_candidate.py"): "9390da36ba0bbe12cafa4d62e0d1c2c9a9e95434bcb262de35f935bc0a66618b",
    Path("Results/parallel-07/conversion/20260923T163240Z-2.3.1.2.1-level066-whole-candidate-r01-results.md"): "93f7178eafbe173e7af6d0c3e9a835cbce214b1af46ddc51188433fa0e5c8e77",
    Path("Results/parallel-09/exercises/conversion/20260923T111911Z-2.3.1.2.1-level066-positions-r01-results.md"): "448f757a65b67999ab246d008fb0dc752ab50f6186024667a164483ec197ed06",
    whole.TXT: whole.PINS["txt"][1],
    whole.PDF: whole.PINS["pdf"][1],
    whole.MAP: "bad5581a04f43ba8baf14db430449e1ccff5cf88f0f7e42198328073b27053d6",
}
UNRESOLVED = [
    "canonical workbook/module/item/event/variant IDs, lineage and revision",
    "fixed BPM, absolute onset/duration and note-per-click",
    "four seam repeat-twice instructions add 168 if performed literally; excluded from printed 898",
    "supplemental sequence translation, rhythm passes and capstone repeats are uncounted",
    "Curriculum review, performed mastery and runtime admission",
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
             if e["workbook_id"] == "fg:workbook:000066"]
    need(len(package["records"]) == 659 and
         not any(r.get("legacy_level") == 66 for r in package["records"]) and
         len(entry) == 1 and entry[0]["representative_item_id"] is None and
         entry[0]["conversion_status"] == "not_converted" and
         entry[0]["whole_workbook_complete"] is False and
         all(entry[0][k] is False for k in
             ("admitted", "imported", "runtime_admitted", "runtime_eligible")),
         "FOUNDATION_ADMISSION")


def narrow_parity(candidate: dict, narrow_candidate: dict) -> None:
    need(narrow_candidate["schema"] == "fathom-level066-moduleA-positions-detached-v1" and
         narrow_candidate["level"] == 66 and
         narrow_candidate["module"] == "A" and
         len(narrow_candidate["records"]) == 5 and
         all(narrow_candidate[k] is False for k in
             ("runtime_eligible", "runtime_admitted", "imported", "admitted",
              "whole_workbook_complete")), "NARROW_SCOPE")
    cells = candidate["modules"]["A"]["cells"]
    for index, (cell, record) in enumerate(zip(cells, narrow_candidate["records"],
                                              strict=True), 1):
        seq = record["routes"]["ascending"] + record["routes"]["descending"]
        left = [(e["note"], e["degree"], e["finger"], e["string"], e["fret"])
                for e in cell["events"]]
        right = [(e["printed_note"], e["printed_degree"],
                  str(e["printed_finger"]), e["string"], e["fret"])
                 for e in seq]
        need(record["position"] == f"P{index}" and
             record["source_local_key"] == f"L66-moduleA-P{index}" and
             len(left) == len(right) == 36 and left == right and
             cell["events"][17]["note"] == cell["events"][18]["note"] and
             cell["events"][17]["string"] == cell["events"][18]["string"] and
             cell["events"][17]["fret"] == cell["events"][18]["fret"],
             f"A_PARITY {index}")


def project(candidate: dict, narrow_candidate: dict) -> tuple[dict, dict]:
    need(candidate["schema"] == "fathom.level66.whole.detached_candidate.v1" and
         candidate["level"] == 66 and candidate["wbs"] == "2.3.1.2.1" and
         candidate["status"] == "candidate_only" and
         candidate["stable_ids"] is None and
         candidate["imported"] is False and candidate["admitted"] is False and
         candidate["workload"]["module_tones"] == whole.COUNTS and
         candidate["workload"]["total_sounding_tones"] == 898 and
         all(candidate["workload"][k] is False for k in
             ("supplemental_seam_second_pass_counted",
              "supplemental_sequence_translations_counted",
              "supplemental_characteristic_rhythm_pass_counted",
              "supplemental_capstone_repeat_counted")), "SOURCE_SCOPE")
    source_info = candidate["source"]
    row = source_info["map_row"]
    need(row["level"] == 66 and row["representative_item_id"] is None and
         row["conversion_status"] == "not_converted" and
         row["stable_ids_assigned"] is False and
         all(row[k] is False for k in
             ("runtime_eligible", "imported", "admitted")) and
         source_info["txt"]["sha256"] == PINS[whole.TXT] and
         source_info["pdf"]["sha256"] == PINS[whole.PDF] and
         source_info["txt"]["lines"] == 503 and
         source_info["pdf"]["pages"] == 20,
         "SOURCE_LINEAGE")
    need(candidate["scale"]["notes"] == list(whole.PC) and
         candidate["scale"]["degrees"] == list(whole.DEGREE.values()) and
         len(candidate["source_transcription"]["txt_lines"]) == 503 and
         len(candidate["source_transcription"]["pdf_pages"]) == 20 and
         len(candidate["count_boundaries"]) == 3 and
         candidate["mastery"]["pdf_page"] == 20 and
         len(candidate["pdf_only_directions"]["module_page_guidance"]) == 17,
         "SOURCE_GUIDANCE")
    narrow_parity(candidate, narrow_candidate)
    records: list[dict] = []
    mapping: list[dict] = []
    module_counts: dict[str, dict] = {}
    for module, expected_cells in whole.CELLS.items():
        source_module = candidate["modules"][module]
        cells = source_module["cells"]
        need(len(cells) == expected_cells and
             source_module["tone_count"] == whole.COUNTS[module],
             f"MODULE_SCOPE {module}")
        counted = 0
        for index, cell in enumerate(cells, 1):
            flattened: list[tuple[dict, str, int | None]] = []
            if module == "B":
                need(cell["tone_count"] == 42 and
                     cell["repeat_twice_instruction"] is True and
                     cell["repeat_counted_in_printed_898"] is False and
                     len(cell["lanes"]) == 6 and
                     cell["pdf_page"] in (8, 9),
                     f"SEAM_COUNT {index}")
                for lane_index, lane in enumerate(cell["lanes"], 1):
                    need(lane["tone_count"] == 7 and len(lane["events"]) == 7 and
                         lane["string"] in whole.OPEN,
                         f"SEAM_LANE {index}:{lane_index}")
                    flattened += [(event, lane["source_ref"], lane_index)
                                  for event in lane["events"]]
            else:
                need(cell["pdf_page"] in range(1, 21) and
                     cell["tone_count"] == len(cell["events"]),
                     f"GRID_COUNT {module}{index}")
                flattened = [(event, cell["source_ref"], None)
                             for event in cell["events"]]
            need(len(flattened) == cell["tone_count"],
                 f"CELL_COUNT {module}{index}")
            events = []
            for ordinal, (item, ref, lane_index) in enumerate(flattened, 1):
                string, fret, note, degree = (item[k] for k in
                                              ("string", "fret", "note", "degree"))
                need(string in whole.OPEN and isinstance(fret, int) and
                     0 <= fret <= 19 and note in whole.PC and
                     degree == whole.DEGREE[note] and
                     (whole.OPEN[string] + fret) % 12 == whole.PC[note] and
                     item["sounded"] is True and
                     item["onset_q"] is None and item["duration_q"] is None and
                     item["slot"] >= 1 and
                     (item.get("finger") is None or item["finger"] in ("1", "2", "3", "4")) and
                     (item.get("role") is None or item["role"] in whole.ROLE) and
                     (module in "GH" or item.get("role") is None) and
                     (module == "B" or item["bar"] in (1, 2, 3, 4)),
                     f"EVENT_SOURCE {module}{index}:{ordinal}")
                chord = item.get("chord")
                if module in "GH":
                    need(chord == ("Am", "Dm", "E7", "Am")[item["bar"] - 1] and
                         (whole.CHORD_ROOTS[chord] + whole.ROLE[item["role"]]) % 12 ==
                         whole.PC[note], f"HARMONIC_ROLE {module}{index}:{ordinal}")
                else:
                    need(chord is None, f"CHORD_SCOPE {module}{index}:{ordinal}")
                events.append({
                    "source_local_ordinal": ordinal,
                    "schema1_fields": {"event_id": None, "kind": "sounded_note",
                                       "midi": whole.OPEN[string] + fret,
                                       "string": string, "fret": fret,
                                       "onset_q": None, "duration_q": None},
                    "source_attack": copy.deepcopy(item),
                    "printed_note": note, "printed_degree": degree,
                    "printed_finger": item.get("finger"),
                    "printed_chord_role": item.get("role"),
                    "printed_chord": chord,
                    "source_lane_index": lane_index,
                    "source_ref": ref, "pdf_page": cell["pdf_page"],
                })
            counted += len(events)
            key = f"L66-{module}-{index:02d}"
            payload = {"source_local_key": key, "identity_state": "unallocated",
                       "source_cell_sha256": sha(encoded(cell)),
                       "source_cell": copy.deepcopy(cell),
                       "source_provenance": {"txt_path": str(whole.TXT),
                                             "txt_ref": cell["source_ref"],
                                             "pdf_path": str(whole.PDF),
                                             "pdf_page": cell["pdf_page"],
                                             "source_candidate_sha256": PINS[CANDIDATE]},
                       "schema1_fields": {"id": None, "workbook_id": None,
                                          "module_id": None, "lineage": None,
                                          "content_revision": None,
                                          "legacy_level": 66,
                                          "title": cell["heading"],
                                          "kind": "harmonic_minor_position_cell",
                                          "runtime_eligible": False,
                                          "source_refs": [cell["source_ref"],
                                                          f"L66-PDF1-p{cell['pdf_page']}"],
                                          "events": events, "variants": [],
                                          "timing": {"status": "unresolved",
                                                     "onset_q": None,
                                                     "duration_q": None,
                                                     "fixed_bpm": None,
                                                     "note_per_click": None},
                                          "resource_requirements": [],
                                          "ambiguities": UNRESOLVED}}
            records.append(payload)
            mapping.append({"source_local_key": key,
                            "source_cell_sha256": payload["source_cell_sha256"],
                            "module": module, "cell": index,
                            "printed_tones": len(events),
                            "supplemental_seam_repeat_tones":
                            len(events) if module == "B" else 0,
                            "txt_ref": cell["source_ref"],
                            "pdf_page": cell["pdf_page"]})
        need(counted == whole.COUNTS[module], f"MODULE_TONES {module}")
        module_counts[module] = {"cells": len(cells), "printed_tones": counted}
    need(len(records) == 48 and
         sum(v["printed_tones"] for v in module_counts.values()) == 898 and
         sum(x["supplemental_seam_repeat_tones"] for x in mapping) == 168,
         "WHOLE_COUNTS")
    proposal = {"schema": "fathom-level066-schema1-field-proposal.1",
                "classification": "build_only_unallocated_nonimportable",
                "wbs_id": "2.3.1.2.1", "legacy_level": 66,
                "source_candidate_sha256": PINS[CANDIDATE],
                "narrow_module_a_candidate_sha256": PINS[NARROW],
                "source": copy.deepcopy(source_info),
                "scale": copy.deepcopy(candidate["scale"]),
                "workload": copy.deepcopy(candidate["workload"]),
                "source_transcription": copy.deepcopy(candidate["source_transcription"]),
                "pdf_only_directions": copy.deepcopy(candidate["pdf_only_directions"]),
                "mastery": copy.deepcopy(candidate["mastery"]),
                "count_boundaries": copy.deepcopy(candidate["count_boundaries"]),
                "timing_boundary": candidate["timing_boundary"],
                "module_counts": module_counts, "records": records,
                "canonical_ids_allocated": False, "runtime_eligible": False,
                "admitted": False, "whole_workbook_complete": False,
                "timing_resolved": False, "curriculum_signoff": False}
    handoff = {"schema": "fathom-level066-schema1-allocation-handoff.1",
               "field_proposal_sha256": sha(encoded(proposal)),
               "source_candidate_sha256": PINS[CANDIDATE],
               "narrow_module_a_candidate_sha256": PINS[NARROW],
               "records": mapping, "module_counts": module_counts,
               "printed_tones": 898,
               "supplemental_seam_repeat_tones_not_counted": 168,
               "unresolved": UNRESOLVED,
               "next_step": "independent source/music review before ID allocation or import",
               "admitted": False, "runtime_eligible": False,
               "whole_workbook_complete": False}
    return proposal, handoff


def derive() -> tuple[dict, dict]:
    pins()
    foundation_status()
    sealed = json.loads((ROOT / CANDIDATE).read_text())
    narrow_sealed = json.loads((ROOT / NARROW).read_text())
    need(sealed == whole.build_candidate(ROOT), "P07_REPLAY_DRIFT")
    need(narrow_sealed == narrow.build_candidate(), "P09_REPLAY_DRIFT")
    return project(sealed, narrow_sealed)


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
                      "cells": len(proposal["records"]), "printed_tones": 898,
                      "supplemental_seam_repeat_not_counted": 168,
                      "field_proposal_sha256": sha(files["field-proposal.json"]),
                      "handoff_sha256": sha(files["allocation-handoff.json"])},
                     sort_keys=True))


if __name__ == "__main__":
    main()
