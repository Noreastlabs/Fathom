#!/usr/bin/env python3
"""Project sealed Level81 source tasks into unallocated schema1-shaped fields."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path

import curriculum_level081_whole_candidate as source


ROOT = Path(__file__).resolve().parents[1]
OUT = Path("Build/parallel-13/level081-schema1-unallocated-r01")
CANDIDATE = Path("Build/parallel-08/2.3.1.3.1-level081-whole-r01/level081-candidate-a.json")
PINS = {
    CANDIDATE: "4fc9e7c575a8ea8b67a52f49a14dba24d280af7e49a72d30c81857a953e27da7",
    Path("Results/primary/20260912T100538Z-2.1.1.2.1-r02-evidence/schema-freeze.json"): "0659fa962a5c933a2bcf3045772b6fe5b05b4deefb3511f5dcb68af51088de95",
    Path("Tools/curriculum_level081_whole_candidate.py"): "d01aebbf4b2bf8c9d824521b5dd826ad75be210fa7c34ba7ccf4f64192e55fa2",
    Path("Results/parallel-08/exercises/conversion/20260923T170113Z-2.3.1.3.1-level081-whole-candidate-r01-results.md"): "db01e2dc2a56fe6951edd4a0ff6920f3a3dbfec39680e6341470c5e52e301145",
    source.TXT: source.PINS["txt"][1],
    source.PDF: source.PINS["pdf"][1],
    source.MAP: source.PINS["map"][1],
    source.CATALOG: source.PINS["catalog"][1],
}
TASKS = {"A": 6, "B": 6, "C": 8, "D": 8, "E": 8,
         "F": 6, "G": 8, "H": 4, "I": 24, "J": 8}
UNRESOLVED = [
    "canonical workbook/module/item/event/variant IDs, lineage and revision",
    "printed allocations are not fully notated playable note attacks",
    "pitch-bound contact placement, inner voices, onset/duration and fixed BPM",
    "D Dm7/F omitted seventh and F printed/fretboard voice-order differences",
    "performed rubric/mastery, Curriculum review and runtime admission",
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
    package = json.loads((ROOT / source.CATALOG).read_text())
    entry = [e for e in package["workbook_catalog"]["entries"]
             if e["workbook_id"] == "fg:workbook:000081"]
    need(len(package["records"]) == 659 and
         not any(r.get("legacy_level") == 81 for r in package["records"]) and
         len(entry) == 1 and entry[0]["representative_item_id"] is None and
         entry[0]["conversion_status"] == "not_converted" and
         entry[0]["whole_workbook_complete"] is False and
         entry[0]["playable_projection"]["status"] ==
         "explicitly_empty_unresolved" and
         all(entry[0][k] is False for k in
             ("admitted", "imported", "runtime_admitted", "runtime_eligible")),
         "FOUNDATION_ADMISSION")


def check_voicing(chord: str, shape: dict) -> None:
    frets = shape["frets_low_to_high"]
    need(len(frets) == 6 and
         all(f is None or isinstance(f, int) and 0 <= f <= 24 for f in frets),
         "VOICING_FRETS")
    pcs = [(open_pc + fret) % 12 for open_pc, fret in zip(source.OPEN, frets)
           if fret is not None]
    need(pcs == shape["pitch_classes_low_to_high"] and
         len(pcs) == shape["sounding_strings"] and
         set(pcs).issubset(source.CHORD[chord]), "VOICING_PITCH")


def check_task(letter: str, index: int, task: dict) -> None:
    count = task["printed_event_allocation"]
    need(task["task"] == f"{letter}{index}" and
         isinstance(count, int) and count > 0 and
         task["source_txt_lines"] and task["source_pdf_pages"] and
         all(isinstance(n, int) and 1 <= n <= 158 for n in task["source_txt_lines"]) and
         all(isinstance(n, int) and 1 <= n <= 20 for n in task["source_pdf_pages"]) and
         task["unresolved"], f"TASK_SCOPE {letter}{index}")
    if letter == "A":
        need(count == 16 and len(task["inner_line"]) ==
             len(task["degrees_as_printed"]) == 4 and
             task["source_anchors"] == 4, f"A_ANCHORS {index}")
    elif letter == "B":
        need(count == 16 and len(task["harmonic_route"]) == 4 and
             task["source_anchors"] == 4, f"B_PEDAL {index}")
    elif letter == "C":
        need(count == 16 and len(task["bass_route"]) ==
             task["source_anchors"] and
             4 <= task["source_anchors"] <= 6,
             f"C_BASS {index}")
    elif letter == "D":
        need(count == 12 and len(task["voicings"]) == 3 and
             len(task["harmonic_route"]) == 3 and
             task["source_anchors"] ==
             sum(shape["sounding_strings"] for shape in task["voicings"]) and
             task["top_line_idea"], f"D_ROUTE {index}")
        for shape in task["voicings"]:
            check_voicing(shape["chord"], shape)
        if any(shape["chord"] == "Dm7/F" for shape in task["voicings"]):
            dm = next(s for s in task["voicings"] if s["chord"] == "Dm7/F")
            need(dm["frets_low_to_high"] == [None, None, 3, 2, 3, 1] and
                 dm["pitch_classes_low_to_high"] == [5, 9, 2, 5] and
                 0 not in dm["pitch_classes_low_to_high"], "DM7_F_OMITTED_SEVENTH")
    elif letter in "EF":
        need(count == 16 and task["source_anchors"] == 4 and
             len(task["notes_low_to_high"]) ==
             len(task["degrees_low_to_high"]) ==
             len(task["actual_fretboard_notes_low_to_high"]) ==
             len(task["actual_fretboard_degrees_low_to_high"]) == 4,
             f"{letter}_VOICING {index}")
        check_voicing(task["chord"], task["voicing"])
        actual = [source.PITCH[n] for n in task["actual_fretboard_notes_low_to_high"]]
        need(actual == task["voicing"]["pitch_classes_low_to_high"] and
             set(source.PITCH[n] for n in task["notes_low_to_high"]) ==
             set(actual) and
             task["source_pitch_order_differs_from_fretboard"] ==
             (task["notes_low_to_high"] != task["actual_fretboard_notes_low_to_high"]),
             f"{letter}_PRINTED_ACTUAL_ORDER {index}")
    elif letter == "G":
        need(count == 16 and task["voice_and_harmony_relationships"],
             f"G_RELATION {index}")
    elif letter == "H":
        need(count == 40 and len(task["bars"]) == 8 and
             all(bar["bar"] == n and bar["printed_event_allocation"] == 5 and
                 bar["harmony"] and
                 len(bar["melody_anchors"]) == (1 if index == 4 else 2) and
                 (bar["bass_anchor"] is None if index == 4 else
                  bar["bass_anchor"] is not None)
                 for n, bar in enumerate(task["bars"], 1)),
             f"H_ARRANGEMENT {index}")
    elif letter == "I":
        need(count == 8 and task["source_anchors"] == 2 and
             task["bar"] == index and task["harmony"] and
             task["bass_anchor"] and task["melody_anchor"] and
             "remaining_six_event_pitches_and_inner_voice_allocation_not_printed"
             in task["unresolved"], f"I_OUTER_VOICES {index}")
    else:
        need(letter == "J" and count == 8 and task["failure_trigger"] and
             task["recovery_instruction"] and
             "recovery_instruction_is_not_eight_notated_note_attacks"
             in task["unresolved"], f"J_RECOVERY {index}")


def project(candidate: dict) -> tuple[dict, dict]:
    need(candidate["schema"] == "fathom.detached.curriculum.level081.whole.r01" and
         candidate["wbs"] == "2.3.1.3.1" and
         candidate["level"] == 81 and candidate["section"] == "XI" and
         candidate["whole_level_source_coverage"] is True and
         candidate["candidate_status"] ==
         "detached_pending_P02_integration_and_curriculum_review" and
         candidate["new_canonical_ids_assigned"] is False and
         candidate["runtime_import"] is False and
         candidate["content_admitted"] is False and
         candidate["timing_audio_or_scoring_inferred"] is False and
         candidate["printed_events_by_module"] == source.COUNTS and
         candidate["printed_event_allocation"] == 1184 and
         candidate["count_convention"].startswith(
             "A-J allocations are printed source workload, not 1184 fully specified"),
         "SOURCE_SCOPE")
    expected_sources = {label: {"path": str(rel), "bytes": source.PINS[pin][0],
                                "sha256": source.PINS[pin][1]}
                        for label, pin, rel in
                        (("txt", "txt", source.TXT), ("pdf", "pdf", source.PDF),
                         ("source_map", "map", source.MAP),
                         ("frozen_catalog", "catalog", source.CATALOG))}
    expected_sources["txt"]["lines"] = 158
    expected_sources["pdf"]["pages"] = 20
    need(candidate["source"] == expected_sources and
         candidate["source_map_row"]["representative_item_id"] == "" and
         candidate["source_map_row"]["conversion_status"] == "not_converted" and
         candidate["source_map_row"]["admitted"] == "False" and
         candidate["frozen_catalog_context"]["workbook_id"] ==
         "fg:workbook:000081" and
         candidate["frozen_catalog_context"]["playable_projection_status"] ==
         "explicitly_empty_unresolved", "SOURCE_LINEAGE")
    need(len(candidate["txt_source_lines"]) == 158 and
         len(candidate["pdf_source_pages"]) == 20 and
         all(p["page"] == i and p["text_sha256"] ==
             sha(p["extracted_text"].encode())
             for i, p in enumerate(candidate["pdf_source_pages"], 1)) and
         len(candidate["source_difference_ledger"]) == 3 and
         [x["module"] for x in candidate["source_difference_ledger"]] ==
         ["D", "F", "J"], "SOURCE_GUIDANCE")
    rubric = candidate["pdf_only_assessment"]
    need(rubric["maximum_score"] == 16 and rubric["pass_threshold"] == 14 and
         rubric["two_separate_days_required"] is True and
         len(rubric["score_categories"]) == 8 and
         rubric["zero_forbidden_categories"] ==
         ["Melody clarity", "Bass timing", "Pulse / form", "Recovery"] and
         rubric["score_scale_per_category"] == [0, 2] and
         len(rubric["mastery_gate"]) == 9 and
         any("There is no Level 106" in row["text"]
             for row in candidate["txt_source_lines"]),
         "RUBRIC_HARD_STOP")
    need(set(candidate["modules"]) == set(TASKS), "MODULE_SCOPE")

    records: list[dict] = []
    mapping: list[dict] = []
    module_counts: dict[str, dict] = {}
    for letter, expected_units in TASKS.items():
        tasks = candidate["modules"][letter]
        need(len(tasks) == expected_units, f"TASK_COUNT {letter}")
        allocated = 0
        for index, task in enumerate(tasks, 1):
            check_task(letter, index, task)
            allocation = task["printed_event_allocation"]
            allocated += allocation
            key = f"L81-{letter}-{index:02d}"
            provenance = {"txt_path": str(source.TXT),
                          "txt_lines": task["source_txt_lines"],
                          "pdf_path": str(source.PDF),
                          "pdf_pages": task["source_pdf_pages"],
                          "source_candidate_sha256": PINS[CANDIDATE]}
            payload = {"source_local_key": key,
                       "identity_state": "unallocated",
                       "source_task_sha256": sha(encoded(task)),
                       "source_task": copy.deepcopy(task),
                       "source_provenance": provenance,
                       "printed_event_allocation": allocation,
                       "source_anchor_count": task.get("source_anchors"),
                       "playable_event_status": "unresolved_not_fully_notated",
                       "schema1_fields": {
                           "id": None, "workbook_id": None, "module_id": None,
                           "lineage": None, "content_revision": None,
                           "legacy_level": 81,
                           "title": task.get("title", task["task"]),
                           "kind": "count_backed_source_task",
                           "runtime_eligible": False,
                           "source_refs": [f"L81-TXT-{n}" for n in
                                           task["source_txt_lines"]] +
                                          [f"L81-PDF-p{n}" for n in
                                           task["source_pdf_pages"]],
                           "events": [], "variants": [],
                           "timing": {"status": "unresolved",
                                      "onset_q": None, "duration_q": None,
                                      "fixed_bpm": None, "note_per_click": None},
                           "resource_requirements": [],
                           "ambiguities": UNRESOLVED + task["unresolved"]}}
            records.append(payload)
            mapping.append({"source_local_key": key,
                            "source_task_sha256": payload["source_task_sha256"],
                            "module": letter, "task": index,
                            "printed_event_allocation": allocation,
                            "fully_notated_playable_events": 0,
                            "source_anchor_count": task.get("source_anchors"),
                            "txt_lines": task["source_txt_lines"],
                            "pdf_pages": task["source_pdf_pages"]})
        need(allocated == source.COUNTS[letter], f"MODULE_ALLOCATION {letter}")
        module_counts[letter] = {"tasks": len(tasks),
                                 "printed_event_allocation": allocated,
                                 "fully_notated_playable_events": 0}
    need(len(records) == 86 and
         sum(v["printed_event_allocation"] for v in module_counts.values()) == 1184 and
         all(r["schema1_fields"]["events"] == [] for r in records) and
         [task["chord"] for task in candidate["modules"]["F"]
          if task["source_pitch_order_differs_from_fretboard"]] ==
         ["Cmaj7", "Cm7", "Dm7"],
         "WHOLE_COUNTS_AND_DIFFERENCES")
    proposal = {"schema": "fathom-level081-schema1-field-proposal.1",
                "classification": "build_only_unallocated_nonimportable",
                "wbs_id": "2.3.1.3.1", "legacy_level": 81,
                "source_candidate_sha256": PINS[CANDIDATE],
                "source": copy.deepcopy(candidate["source"]),
                "source_map_row": copy.deepcopy(candidate["source_map_row"]),
                "frozen_catalog_context": copy.deepcopy(
                    candidate["frozen_catalog_context"]),
                "count_convention": candidate["count_convention"],
                "source_difference_ledger": copy.deepcopy(
                    candidate["source_difference_ledger"]),
                "txt_source_lines": copy.deepcopy(candidate["txt_source_lines"]),
                "pdf_source_pages": copy.deepcopy(candidate["pdf_source_pages"]),
                "pdf_only_assessment": copy.deepcopy(rubric),
                "module_counts": module_counts, "records": records,
                "printed_event_allocation": 1184,
                "fully_notated_playable_events": 0,
                "canonical_ids_allocated": False, "runtime_eligible": False,
                "admitted": False, "whole_workbook_complete": False,
                "timing_resolved": False, "performed_assessment": None,
                "curriculum_signoff": False}
    handoff = {"schema": "fathom-level081-schema1-allocation-handoff.1",
               "field_proposal_sha256": sha(encoded(proposal)),
               "source_candidate_sha256": PINS[CANDIDATE],
               "records": mapping, "module_counts": module_counts,
               "printed_event_allocation": 1184,
               "fully_notated_playable_events": 0,
               "unresolved": UNRESOLVED,
               "next_step": "independent source/music review before playable event authoring, ID allocation or import",
               "admitted": False, "runtime_eligible": False,
               "whole_workbook_complete": False}
    return proposal, handoff


def derive() -> tuple[dict, dict]:
    pins()
    foundation_status()
    sealed = json.loads((ROOT / CANDIDATE).read_text())
    need(sealed == source.build(ROOT), "P08_REPLAY_DRIFT")
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
                      "tasks": len(proposal["records"]),
                      "printed_event_allocation": 1184,
                      "fully_notated_playable_events": 0,
                      "field_proposal_sha256": sha(files["field-proposal.json"]),
                      "handoff_sha256": sha(files["allocation-handoff.json"])},
                     sort_keys=True))


if __name__ == "__main__":
    main()
