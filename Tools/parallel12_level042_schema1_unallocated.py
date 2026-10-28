#!/usr/bin/env python3
"""Replay Level42 originals and project source-backed unallocated schema1 fields."""

from __future__ import annotations

import argparse
import hashlib
import json
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader

import curriculum_level042_whole_candidate as p08

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_A = p08.BUILD_REL / "level042-candidate-a.json"
CANDIDATE_B = p08.BUILD_REL / "level042-candidate-b.json"
RESULT = Path("Results/parallel-08/exercises/conversion/20260923T153550Z-2.3.1.1.1-level042-whole-candidate-r01-results.md")
PACKAGE = Path("Content/controls/curriculum-v1/package.json")
REGISTRY = Path("Content/controls/curriculum-v1/identity-registry.json")
OUT = Path("Build/parallel-12/level042-schema1-unallocated-r01")
PINS = {
    CANDIDATE_A: (272845, "058be419fa5458cf9e1f802d73a3865202903c420b2bcef4d5c2b72c75307af5"),
    CANDIDATE_B: (272845, "058be419fa5458cf9e1f802d73a3865202903c420b2bcef4d5c2b72c75307af5"),
    RESULT: (None, "3ce937b89847175a4aa3ba27c7bd5e42ba97e6a4cbe15b9ff87d267fbc9dfa92"),
    p08.TXT_REL: p08.PINS["txt"],
    p08.PDF_REL: p08.PINS["pdf"],
    p08.MAP_REL: p08.PINS["map"],
    PACKAGE: (None, "766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255"),
    REGISTRY: (None, "5d265859e1e8a5a530a0e53d88b019a1c920f3bba6cccb4ef0fef2f7640007e5"),
}
FIELDS = {"id", "workbook_id", "module_id", "legacy_level", "title", "kind", "content_revision",
          "status", "runtime_eligible", "source_refs", "authored_text_refs", "normalization", "context",
          "events", "timing", "rubric", "resource_requirements", "ambiguities", "control_scope",
          "variants", "lineage"}
STRING_NUMBER = {"E": 1, "A": 2, "D": 3, "G": 4, "B": 5, "e": 6}
OPEN_MIDI = {"E": 40, "A": 45, "D": 50, "G": 55, "B": 59, "e": 64}
ITEM_COUNTS = {"A": 6, "B": 6, "C": 24, "D": 5, "E": 24, "F": 13, "G": 8, "H": 5}
MODULE_COUNTS = {key: {"counted_sounding_events": pair[0], "pick_attacks": pair[1]}
                 for key, pair in p08.COUNTS.items()}


class ProposalError(ValueError):
    pass


def need(ok: bool, code: str) -> None:
    if not ok:
        raise ProposalError(code)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def encode(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def pin(root: Path = ROOT) -> None:
    need(root.resolve() == ROOT.resolve(), "ROOT_DRIFT")
    for path, (length, digest) in PINS.items():
        raw = (root / path).read_bytes()
        need((length is None or len(raw) == length) and sha(raw) == digest, f"INPUT_DRIFT {path}")


def source_span(item: dict, lines: list[str]) -> dict:
    first, last = item.get("source_txt_lines", [item.get("source_txt_line"), item.get("source_txt_line")])
    need(isinstance(first, int) and isinstance(last, int) and 1 <= first <= last <= len(lines), "TXT_SOURCE_SPAN")
    return {"ref": f"L42-TXT1-{first}-{last}", "first_line": first, "last_line": last,
            "text_sha256": sha("\n".join(lines[first - 1:last]).encode())}


def preserve_sources(candidate: dict, txt_raw: bytes, pdf_raw: bytes) -> dict:
    txt_text = txt_raw.decode("utf-8")
    lines = txt_text.splitlines()
    need(len(lines) == 473 and txt_raw.endswith(b"\n"), "TXT_COMPLETE_BOUNDARY")
    reader = PdfReader(BytesIO(pdf_raw), strict=True)
    need(len(reader.pages) == 18, "PDF_COMPLETE_BOUNDARY")
    pages = []
    for number, page in enumerate(reader.pages, 1):
        extracted = page.extract_text() or ""
        page_lines = extracted.splitlines()
        need(page_lines and any(f"Page {number} of 18" in line for line in page_lines),
             f"PDF_PAGE_IDENTITY {number}")
        pages.append({"page": number, "text": extracted, "text_sha256": sha(extracted.encode()),
                      "line_count": len(page_lines), "media_box": [float(value) for value in page.mediabox]})
    source_map = []
    for module in "ABCDEFGH":
        for index, item in enumerate(candidate["modules"][module], 1):
            source_map.append({"source_local_key": f"L42-{module}-{index:02d}",
                               "module": module, "module_item": index,
                               "txt": source_span(item, lines),
                               "pdf_page": item["source_pdf_page"],
                               "pdf_ref": f"L42-PDF1-p{item['source_pdf_page']}"})
    preserved = {"version": "parallel12-level042-whole-original-preservation.1",
                 "classification": "pinned_original_text_and_page_preservation_not_admission",
                 "source": {"txt_path": str(p08.TXT_REL), "txt_bytes": len(txt_raw), "txt_sha256": sha(txt_raw),
                            "txt_text": txt_text, "txt_line_count": len(lines), "txt_trailing_newline": True,
                            "pdf_path": str(p08.PDF_REL), "pdf_bytes": len(pdf_raw), "pdf_sha256": sha(pdf_raw),
                            "pdf_page_count": len(pages), "pdf_pages": pages},
                 "source_map": source_map, "source_lanes": candidate["lanes"],
                 "source_guidance": candidate["guidance"], "source_picking": candidate["picking"],
                 "source_timing": candidate["timing"], "source_blue_third": candidate["blue_third"],
                 "source_module_counts": candidate["module_counts"],
                 "source_discrepancies": candidate["source_discrepancies"],
                 "source_ambiguities": [
                     "C# is a calibration ceiling; the blue-third shade is below it and has no exact discrete pitch.",
                     "H cadence bend/shade-release groups preserve pitch wording and counted tones without individual onset or pitch-curve allocation.",
                     "Slide arrivals are sounding events without new pick attacks; subdivision placement is source guidance without numeric timing.",
                     "Module B upper-endpoint mirror and G vibrato pulses are instructions, not extra projected notes."],
                 "candidate_parity": {"all_A_through_H_items": 91, "whole_candidate_rebuilt_exactly": True,
                                      "source_candidate_sha256": PINS[CANDIDATE_A][1]},
                 "schema1_projection_allowed_after_parity": True,
                 "canonical_allocation_allowed": False}
    verify_preservation(preserved, txt_raw, pdf_raw)
    return preserved


def verify_preservation(preserved: dict, txt_raw: bytes, pdf_raw: bytes) -> None:
    data = preserved["source"]
    need(data["txt_text"].encode() == txt_raw and data["txt_sha256"] == sha(txt_raw) and
         data["txt_line_count"] == 473 and data["txt_trailing_newline"] is True and
         data["pdf_sha256"] == sha(pdf_raw) and data["pdf_bytes"] == len(pdf_raw) and
         data["pdf_page_count"] == len(data["pdf_pages"]) == 18,
         "SOURCE_PRESERVATION_DRIFT")
    reader = PdfReader(BytesIO(pdf_raw), strict=True)
    for index, page in enumerate(data["pdf_pages"], 1):
        extracted = reader.pages[index - 1].extract_text() or ""
        need(page["page"] == index and page["text"] == extracted and
             page["text_sha256"] == sha(extracted.encode()) and
             page["line_count"] == len(extracted.splitlines()), "PDF_PAGE_TEXT_DRIFT")
    need(preserved["candidate_parity"] == {"all_A_through_H_items": 91,
                                            "whole_candidate_rebuilt_exactly": True,
                                            "source_candidate_sha256": PINS[CANDIDATE_A][1]} and
         preserved["schema1_projection_allowed_after_parity"] is True and
         preserved["canonical_allocation_allowed"] is False and
         len(preserved["source_map"]) == 91, "PARITY_GATE")


def note_event(note: dict) -> dict:
    string, fret, degree, name = note["string"], note["fret"], note["degree"], note["note"]
    need(string in STRING_NUMBER and p08.NOTE[degree] == name and
         (p08.OPEN[string] + fret) % 12 == p08.PITCH[name] and
         note["onset_q"] is note["duration_q"] is None and isinstance(note["pick_attack"], bool),
         "SOURCE_NOTE_GEOMETRY")
    picked = note["pick_attack"]
    need((note["articulation"] == "picked") == picked or
         (note["articulation"] == "vibrato_hold" and picked), "SOURCE_ATTACK_ARTICULATION")
    return {"event_id": None, "kind": "note", "string": STRING_NUMBER[string], "fret": fret,
            "midi": OPEN_MIDI[string] + fret, "spelling": name,
            "degree_contexts": {"A-minor-pentatonic": {"source_label": degree,
                                                        "alteration": -1 if degree.startswith("b") else 0}},
            "finger": note.get("finger"), "articulation": note["articulation"],
            "pick_attack": picked, "onset_q": None, "duration_q": None,
            "tie_from": None}


def f_event(note: dict, site: dict) -> dict:
    need(note["ordinal"] in range(1, 6) and note["onset_q"] is note["duration_q"] is None and
         isinstance(note["pick_attack"], bool) and site["string"] in STRING_NUMBER,
         "SOURCE_BEND_SCOPE")
    if site["kind"] == "blue_third":
        need(site["target_is_pentatonic_degree"] is False and
             note["pitch_label"] in ("C#", "between C and C#", "C"), "BLUE_BOUNDARY")
    else:
        need(site["target_is_pentatonic_degree"] is True and note["pitch_label"] in p08.PITCH,
             "BEND_TARGET_SCOPE")
    return {"event_id": None, "kind": "unresolved_bend_pitch", "string": STRING_NUMBER[site["string"]],
            "fret": None, "midi": None, "spelling": None, "degree_contexts": {}, "finger": None,
            "source_pitch_label": note["pitch_label"], "articulation": note["articulation"],
            "pick_attack": note["pick_attack"], "source_counted_sounding_events": 1,
            "onset_q": None, "duration_q": None, "tie_from": None}


def h_group_event(group: dict) -> dict:
    need(group["onset_q"] is group["duration_q"] is None and group["pick_attacks"] == 1 and
         group["counted_sounding_events"] in (1, 2, 3), "SOURCE_CADENCE_GROUP")
    return {"event_id": None, "kind": "unresolved_articulation_group", "string": None,
            "fret": None, "midi": None, "spelling": None, "degree_contexts": {}, "finger": None,
            "source_degree_text": group["degree_text"], "source_note_text": group["note_text"],
            "source_counted_sounding_events": group["counted_sounding_events"],
            "articulation": "source_group_wording", "pick_attack": True,
            "onset_q": None, "duration_q": None, "tie_from": None}


def project_item(module: str, index: int, item: dict, source_ref: dict) -> dict:
    local = f"L42-{module}-{index:02d}"
    need(source_ref["source_local_key"] == local and source_ref["module"] == module and
         source_ref["module_item"] == index and source_ref["pdf_page"] == item["source_pdf_page"],
         "SOURCE_CASE_ORDER")
    if module in "ABCDE":
        events = [note_event(note) for note in item["events"]]
        sounding, attacks = len(events), sum(e["pick_attack"] for e in events)
    elif module == "F":
        events = [f_event(note, item) for note in item["events"]]
        sounding, attacks = len(events), sum(e["pick_attack"] for e in events)
    elif module == "G":
        need(item["degree"] == "1" and item["note"] == "A" and
             item["counted_sounding_events"] == item["pick_attacks"] == 1 and
             item["vibrato_pulses"] == "instruction_only", "SOURCE_VIBRATO_SCOPE")
        events = [note_event({"string": item["string"], "fret": item["fret"], "degree": "1",
                              "note": "A", "finger": None, "articulation": "vibrato_hold",
                              "pick_attack": True, "onset_q": item["onset_q"],
                              "duration_q": item["duration_q"]})]
        sounding, attacks = 1, 1
    else:
        need(module == "H" and len(item["groups"]) == item["pick_attacks"] == 4,
             "SOURCE_CADENCE_SCOPE")
        events = [h_group_event(group) for group in item["groups"]]
        sounding, attacks = sum(e["source_counted_sounding_events"] for e in events), 4
        need(sounding == item["counted_sounding_events"], "SOURCE_CADENCE_COUNT")
    need((sounding, attacks) ==
         ((sum(group["counted_sounding_events"] for group in item["groups"]), item["pick_attacks"])
          if module == "H" else
          (item["counted_sounding_events"], item["pick_attacks"]) if module == "G" else
          (len(item["events"]), sum(note["pick_attack"] for note in item["events"]))),
         "SOURCE_EVENT_ATTACK_COUNT")
    picked_ordinals = [ordinal for ordinal, event in enumerate(events, 1) if event["pick_attack"]]
    refs = [source_ref["txt"]["ref"], source_ref["pdf_ref"]]
    variants, memberships = [], []
    for pick in ("D", "U"):
        label = f"level42-{module}-{index:02d}-{pick}-start"
        variants.append({"id": None, "label": label, "event_ids": None,
                         "source_refs": refs, "route": "fixed_A_minor_pentatonic_level42_workout",
                         "pick_start": pick, "pick_start_origin": "source_authored",
                         "role": "notation_practice", "accent_policy": "source_unspecified",
                         "grouping": {"kind": "unresolved", "notes_per_beat": None,
                                      "beat_unit_q": None, "marking_factor": [1, 1],
                                      "source_label": "printed module instruction only"},
                         "tail_pause": None,
                         "unresolved": ["No selected clock, absolute BPM, click or performed bend/slide contour."]})
        memberships.append({"label": label, "event_local_ordinals": list(range(1, len(events) + 1)),
                            "picked_attack_local_ordinals": picked_ordinals,
                            "source_counted_sounding_events": sounding,
                            "source_pick_attacks": attacks,
                            "alternate_actual_attacks_only": True})
    ambiguities = ["Canonical identity, lineage, fixed BPM, note-per-click, onsets/durations and admission are unallocated."]
    if module == "F":
        ambiguities.append("Bend/shade pitch curve and exact intermediate pitch are unresolved; C# is a calibration ceiling, not a pentatonic degree.")
    if module == "H":
        ambiguities.append("Four source groups represent counted tones; individual bend/shade-release pitch onsets and note geometry remain unresolved.")
    if module in "CE":
        ambiguities.append("Slide arrival is a sounding event without a new pick; numeric subdivision onset remains unresolved.")
    fields = {"id": None, "workbook_id": None, "module_id": None, "legacy_level": 42,
              "title": f"Level 42 Module {module} source case {index:02d}",
              "kind": "notation", "content_revision": None, "status": "converted_candidate",
              "runtime_eligible": False, "source_refs": refs, "authored_text_refs": refs,
              "normalization": [{"kind": "representation_metadata",
                                 "basis": "P08 whole-Level42 candidate and complete original TXT/PDF",
                                 "text": "Source sounding/attack counts and articulation order are retained without timing or performed pitch inference."}],
              "context": {"local_code": local, "source_module": module, "source_case_number": index,
                          "fixed_key": "A minor pentatonic", "pitch_set": ["A", "C", "D", "E", "G"],
                          "source_item": item, "source_counted_sounding_events": sounding,
                          "source_pick_attacks": attacks,
                          "tuning_open_midi": [40, 45, 50, 55, 59, 64], "capo": 0},
              "events": events,
              "timing": {"status": "unresolved", "unit": "quarter",
                         "basis": "Source practice subdivision and articulation guidance has no allocated event grid",
                         "selected_pulse": None},
              "rubric": None, "resource_requirements": [], "ambiguities": ambiguities,
              "control_scope": {"local_case": local, "extent": "complete_selected_case",
                                "whole_workbook_complete": False, "source_event_count": sounding,
                                "source_pick_attacks": attacks, "basis_refs": refs,
                                "unresolved": ["Identity, lineage, timing and admission pending."]},
              "variants": variants, "lineage": None}
    need(set(fields) == FIELDS, "FIELD_SHAPE")
    return {"source_local_key": local, "module": module, "module_item": index,
            "source_refs": refs, "schema1_fields": fields, "variant_memberships": memberships,
            "source_item": item, "source_counted_sounding_events": sounding,
            "source_pick_attacks": attacks, "projected_event_units": len(events),
            "identity_state": "unallocated", "schema1_importable": False,
            "open_gaps": ["canonical identities and lineage", "quarter-note timing/click and performed articulation",
                          "runtime/Curriculum admission"]}


def build(root: Path = ROOT, candidate_override: dict | None = None) -> tuple[dict, dict, dict]:
    pin(root)
    txt_raw, pdf_raw = (root / p08.TXT_REL).read_bytes(), (root / p08.PDF_REL).read_bytes()
    candidate = candidate_override if candidate_override is not None else json.loads((root / CANDIDATE_A).read_text())
    need((root / CANDIDATE_A).read_bytes() == (root / CANDIDATE_B).read_bytes(), "P08_TWIN_DRIFT")
    rebuilt = p08.build_candidate(root)
    need(candidate == rebuilt, "P08_SOURCE_CANDIDATE_DRIFT")
    need(candidate["level"] == 42 and candidate["canonical_id"] is None and
         candidate["runtime_imported"] is candidate["admitted"] is False and
         candidate["whole_level_source_covered"] is True and
         candidate["whole_level_complete"] is False and
         candidate["pitch_set"] == ["A", "C", "D", "E", "G"] and
         candidate["blue_third"]["C_sharp_is_pentatonic_degree"] is False and
         candidate["timing"]["fixed_bpm"] is candidate["timing"]["numeric_onset"] is
         candidate["timing"]["numeric_duration"] is candidate["timing"]["performed_pitch_curve"] is None,
         "SOURCE_SCOPE")
    preserved = preserve_sources(candidate, txt_raw, pdf_raw)
    package = json.loads((root / PACKAGE).read_text())
    registry = json.loads((root / REGISTRY).read_text())
    current = [record for record in package["records"] if record.get("legacy_level") == 42]
    identities = [entity for entity in registry["entities"] if entity.get("id") == "fg:workbook:000042" or
                  entity.get("parent") == "fg:workbook:000042"]
    need(len(package["records"]) == 659 and not current and not identities, "CURRENT659_LEVEL42_OVERLAP")
    records = []
    for source_ref in preserved["source_map"]:
        module, index = source_ref["module"], source_ref["module_item"]
        records.append(project_item(module, index, candidate["modules"][module][index - 1], source_ref))
    need({key: len(candidate["modules"][key]) for key in "ABCDEFGH"} == ITEM_COUNTS and
         candidate["module_counts"] == MODULE_COUNTS and
         candidate["totals"] == {"counted_sounding_events": 668, "pick_attacks": 428} and
         sum(r["source_counted_sounding_events"] for r in records) == 668 and
         sum(r["source_pick_attacks"] for r in records) == 428 and
         sum(r["projected_event_units"] for r in records) == 645,
         "WHOLE_LEVEL_COVERAGE")
    counts = {"cases": 91, "module_cases": ITEM_COUNTS, "counted_sounding_events": 668,
              "pick_attacks": 428, "explicit_sounding_event_rows_A_through_G": 625,
              "H_aggregate_group_rows": 20, "H_counted_sounding_events_represented": 43,
              "projected_event_units": 645, "variants": 182,
              "preserved_txt_lines": 473, "preserved_pdf_pages": 18}
    proposal = {"proposal_version": "parallel12-level042-unallocated-schema1-fields.1",
                "classification": "source_mapped_field_proposal_not_schema1_importable",
                "legacy_level": 42,
                "source_pins": {str(path): {"bytes": (root / path).stat().st_size, "sha256": digest}
                                for path, (_, digest) in PINS.items()},
                "source_preservation_sha256": sha(encode(preserved)), "counts": counts,
                "source_lanes": candidate["lanes"], "source_guidance": candidate["guidance"],
                "source_picking": candidate["picking"], "source_timing": candidate["timing"],
                "source_blue_third": candidate["blue_third"],
                "source_discrepancies": candidate["source_discrepancies"],
                "source_ambiguities": preserved["source_ambiguities"],
                "current659_level42_records": 0, "current659_level42_workbook_identity": False,
                "representative_collision": None,
                "canonical_ids_allocated": False, "runtime_eligible": False, "admitted": False,
                "fixed_bpm": None, "note_per_click": None, "onset_q": None, "duration_q": None,
                "records": records}
    handoff = {"version": "parallel12-level042-allocation-handoff.1",
               "status": "pending_P02_serial_floor_and_allocation_authority",
               "source_preservation_sha256": sha(encode(preserved)),
               "proposal_sha256": sha(encode(proposal)), "source_map": preserved["source_map"],
               "module_order": list("ABCDEFGH"), "module_counts": candidate["module_counts"],
               "case_count": 91, "counted_sounding_events": 668, "pick_attacks": 428,
               "projected_event_units": 645, "variant_count": 182,
               "current659_level42_records": 0, "current659_level42_workbook_identity": False,
               "representative_collision": None,
               "decisions_required": ["P02 serial floor, workbook/module/item/variant identity and source-key bridge",
                                      "Curriculum review of fixed-key lane/position geometry, bend and cadence ambiguity, and printed route",
                                      "Reviewed click, articulation timing, lineage and admission policy before import"],
               "selected_choice": None, "allocation_allowed": False, "no_admission": True}
    verify_projection(preserved, proposal, handoff, candidate)
    return preserved, proposal, handoff


def verify_projection(preserved: dict, proposal: dict, handoff: dict, candidate: dict) -> dict:
    need(preserved["schema1_projection_allowed_after_parity"] is True and
         proposal["source_preservation_sha256"] == handoff["source_preservation_sha256"] == sha(encode(preserved)),
         "PARITY_GATE")
    need(proposal["canonical_ids_allocated"] is False and proposal["runtime_eligible"] is False and
         proposal["admitted"] is False and handoff["allocation_allowed"] is False and
         handoff["no_admission"] is True and handoff["selected_choice"] is None and
         all(proposal[key] is None for key in ("fixed_bpm", "note_per_click", "onset_q", "duration_q")),
         "INVALID_AUTHORITY")
    counts = {"cases": 91, "module_cases": ITEM_COUNTS, "counted_sounding_events": 668,
              "pick_attacks": 428, "explicit_sounding_event_rows_A_through_G": 625,
              "H_aggregate_group_rows": 20, "H_counted_sounding_events_represented": 43,
              "projected_event_units": 645, "variants": 182,
              "preserved_txt_lines": 473, "preserved_pdf_pages": 18}
    need(proposal["counts"] == counts and handoff["case_count"] == 91 and
         handoff["counted_sounding_events"] == 668 and handoff["pick_attacks"] == 428 and
         handoff["projected_event_units"] == 645 and handoff["variant_count"] == 182,
         "COVERAGE")
    expected_keys = [f"L42-{module}-{index:02d}" for module in "ABCDEFGH"
                     for index in range(1, ITEM_COUNTS[module] + 1)]
    need(handoff["module_order"] == list("ABCDEFGH") and
         handoff["module_counts"] == candidate["module_counts"] and
         handoff["source_map"] == preserved["source_map"] and
         [record["source_local_key"] for record in proposal["records"]] == expected_keys and
         len(proposal["records"]) == len(handoff["source_map"]) == 91,
         "SOURCE_CASE_ORDER")
    for record, source_ref in zip(proposal["records"], handoff["source_map"], strict=True):
        module, index = source_ref["module"], source_ref["module_item"]
        fields = record["schema1_fields"]
        need(record["source_local_key"] == source_ref["source_local_key"] and
             record["module"] == module and record["module_item"] == index and
             record["identity_state"] == "unallocated" and record["schema1_importable"] is False and
             set(fields) == FIELDS and fields["legacy_level"] == 42 and
             fields["context"]["local_code"] == record["source_local_key"] and
             all(fields[key] is None for key in ("id", "workbook_id", "module_id", "content_revision", "lineage")) and
             fields["runtime_eligible"] is False and fields["timing"]["status"] == "unresolved" and
             fields["timing"]["selected_pulse"] is None,
             "INVALID_AUTHORITY")
        expected = project_item(module, index, candidate["modules"][module][index - 1], source_ref)
        need(record["source_item"] == expected["source_item"] and
             fields["context"]["source_item"] == expected["schema1_fields"]["context"]["source_item"] and
             record["source_refs"] == expected["source_refs"], "SOURCE_CASE_DRIFT")
        need(fields["events"] == expected["schema1_fields"]["events"] and
             record["source_counted_sounding_events"] == expected["source_counted_sounding_events"] and
             record["source_pick_attacks"] == expected["source_pick_attacks"] and
             record["projected_event_units"] == expected["projected_event_units"],
             "SOURCE_GEOMETRY_OR_ATTACK_DRIFT")
        need(fields["variants"] == expected["schema1_fields"]["variants"] and
             record["variant_memberships"] == expected["variant_memberships"], "VARIANT_MEMBERSHIP")
    need(handoff["proposal_sha256"] == sha(encode(proposal)) and
         proposal["current659_level42_records"] == handoff["current659_level42_records"] == 0 and
         proposal["current659_level42_workbook_identity"] is handoff["current659_level42_workbook_identity"] is False and
         proposal["representative_collision"] is handoff["representative_collision"] is None,
         "PROPOSAL_HASH_OR_CURRENT659")
    return counts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("build", "verify"))
    args = parser.parse_args()
    preserved, proposal, handoff = build()
    outputs = {"source-preservation.json": preserved,
               "field-proposal.json": proposal,
               "allocation-handoff.json": handoff}
    if args.command == "build":
        (ROOT / OUT).mkdir(parents=True, exist_ok=True)
        for name, value in outputs.items():
            (ROOT / OUT / name).write_bytes(encode(value))
    else:
        for name, value in outputs.items():
            need((ROOT / OUT / name).read_bytes() == encode(value), f"OUTPUT_DRIFT {name}")
    print(json.dumps({"status": "level042_unallocated_pending_P02",
                      "counts": verify_projection(preserved, proposal, handoff,
                                                  json.loads((ROOT / CANDIDATE_A).read_text()))}, sort_keys=True))


if __name__ == "__main__":
    main()
