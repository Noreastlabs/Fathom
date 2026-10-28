#!/usr/bin/env python3
"""Replay Level32 originals and project detached, unallocated schema1-shaped fields."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader

import parallel_07_level032_whole_candidate as p07

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = p07.BUILD_REL / "candidate.json"
RESULT = Path("Results/parallel-07/conversion/20260923T151438Z-2.3.1.1.1-level032-whole-candidate-r01-results.md")
PACKAGE = Path("Content/controls/curriculum-v1/package.json")
REGISTRY = Path("Content/controls/curriculum-v1/identity-registry.json")
OUT = Path("Build/parallel-12/level032-schema1-unallocated-r01")
PINS = {
    CANDIDATE: (978505, "f66189ab30d4961d971b58818e9d83fe4846fe986d34fdecb65caff976f653e5"),
    RESULT: (None, "1ca3646fc0859ecd84d4ad1da69be2fd776c876886b23d72c1718f7199934b5d"),
    p07.TXT_REL: (p07.TXT_BYTES, p07.TXT_SHA256),
    p07.PDF_REL: (p07.PDF_BYTES, p07.PDF_SHA256),
    PACKAGE: (None, "766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255"),
    REGISTRY: (None, "5d265859e1e8a5a530a0e53d88b019a1c920f3bba6cccb4ef0fef2f7640007e5"),
}
FIELDS = {"id", "workbook_id", "module_id", "legacy_level", "title", "kind", "content_revision",
          "status", "runtime_eligible", "source_refs", "authored_text_refs", "normalization", "context",
          "events", "timing", "rubric", "resource_requirements", "ambiguities", "control_scope",
          "variants", "lineage"}
STRING_NUMBER = {"E": 1, "A": 2, "D": 3, "G": 4, "B": 5, "e": 6}
MODULE_LAYOUT = (("A", "ascending", 0), ("A", "descending", 27),
                 ("B", "ascending", 54), ("B", "descending", 89))


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


def txt_span(ref: str, lines: list[str]) -> dict:
    match = re.fullmatch(r"L32-TXT1-(\d+)-(\d+)", ref)
    need(match is not None, "TXT_REF")
    first, last = map(int, match.groups())
    need(1 <= first <= last <= len(lines), "TXT_SPAN")
    return {"ref": ref, "first_line": first, "last_line": last,
            "text_sha256": sha("\n".join(lines[first - 1:last]).encode())}


def preserve_sources(candidate: dict, txt_raw: bytes, pdf_raw: bytes) -> dict:
    txt_text = txt_raw.decode("utf-8")
    lines = txt_text.splitlines()
    need(len(lines) == 741 and txt_raw.endswith(b"\n"), "TXT_COMPLETE_BOUNDARY")
    reader = PdfReader(BytesIO(pdf_raw), strict=True)
    need(len(reader.pages) == 16, "PDF_COMPLETE_BOUNDARY")
    pages = []
    for number, page in enumerate(reader.pages, 1):
        extracted = page.extract_text() or ""
        page_lines = extracted.splitlines()
        need(page_lines and any(f"Page {number} of 16" in line for line in page_lines),
             f"PDF_PAGE_IDENTITY {number}")
        pages.append({"page": number, "text": extracted, "text_sha256": sha(extracted.encode()),
                      "line_count": len(page_lines), "media_box": [float(value) for value in page.mediabox]})
    source_map = []
    for index, card in enumerate(candidate["records"], 1):
        span = txt_span(card["source_refs"]["txt"], lines)
        need(span["first_line"] == 63 + (index - 1) * 50 and span["last_line"] == span["first_line"] + 47,
             "TXT_CARD_BOUNDARY")
        source_map.append({"source_local_key": card["source_local_key"], "rung_number": index,
                           "txt": span, "pdf_card": card["source_refs"]["pdf_card"],
                           "pdf_route": card["source_refs"]["pdf_route"]})
    txt_final_footer = lines[source_map[-1]["txt"]["last_line"] - 1]
    pdf_final_footer = pages[14]["text"].splitlines()[44]
    need(txt_final_footer == "Complete the assigned module or linked A+B rung, return to the low root, release pressure, and move one fret." and
         pdf_final_footer == "Finish the fret-17 linked rung, then reverse direction and continue through rungs 12-01.",
         "FINAL_FOOTER_DISTINCTION")
    preserved = {"version": "parallel12-level032-whole-original-preservation.1",
                 "classification": "pinned_original_text_and_page_preservation_not_admission",
                 "source": {"txt_path": str(p07.TXT_REL), "txt_bytes": len(txt_raw), "txt_sha256": sha(txt_raw),
                            "txt_text": txt_text, "txt_line_count": len(lines), "txt_trailing_newline": True,
                            "pdf_path": str(p07.PDF_REL), "pdf_bytes": len(pdf_raw), "pdf_sha256": sha(pdf_raw),
                            "pdf_page_count": len(pages), "pdf_pages": pages},
                 "source_map": source_map, "source_guidance": candidate["instructions"],
                 "source_shape": candidate["shape"], "source_routes": candidate["routes"],
                 "source_exceptions": candidate["exceptions"],
                 "source_distinctions": [{"kind": "final_card_footer_wording", "source_local_key": "L32-rung13",
                                          "txt": txt_final_footer, "pdf": pdf_final_footer,
                                          "interpretation": "the explicit round-trip route turns after rung13 and returns through rung12"}],
                 "card_parity": {"txt_pdf_rungs": 13, "printed_blocks_each": 4,
                                 "all_printed_rows_and_paths_equal": True,
                                 "whole_candidate_rebuilt_exactly": True,
                                 "source_candidate_sha256": PINS[CANDIDATE][1]},
                 "schema1_projection_allowed_after_parity": True,
                 "canonical_allocation_allowed": False}
    verify_preservation(preserved, txt_raw, pdf_raw)
    return preserved


def verify_preservation(preserved: dict, txt_raw: bytes, pdf_raw: bytes) -> None:
    data = preserved["source"]
    need(data["txt_text"].encode() == txt_raw and data["txt_sha256"] == sha(txt_raw) and
         data["txt_line_count"] == 741 and data["txt_trailing_newline"] is True and
         data["pdf_sha256"] == sha(pdf_raw) and data["pdf_bytes"] == len(pdf_raw) and
         data["pdf_page_count"] == len(data["pdf_pages"]) == 16,
         "SOURCE_PRESERVATION_DRIFT")
    reader = PdfReader(BytesIO(pdf_raw), strict=True)
    for index, page in enumerate(data["pdf_pages"], 1):
        text = reader.pages[index - 1].extract_text() or ""
        need(page["page"] == index and page["text"] == text and
             page["text_sha256"] == sha(text.encode()) and
             page["line_count"] == len(text.splitlines()), "PDF_PAGE_TEXT_DRIFT")
    need(preserved["card_parity"] == {"txt_pdf_rungs": 13, "printed_blocks_each": 4,
                                      "all_printed_rows_and_paths_equal": True,
                                      "whole_candidate_rebuilt_exactly": True,
                                      "source_candidate_sha256": PINS[CANDIDATE][1]} and
         preserved["schema1_projection_allowed_after_parity"] is True and
         preserved["canonical_allocation_allowed"] is False, "PARITY_GATE")
    need(preserved["source_distinctions"] == [{"kind": "final_card_footer_wording",
                                               "source_local_key": "L32-rung13",
                                               "txt": data["txt_text"].splitlines()[709],
                                               "pdf": data["pdf_pages"][14]["text"].splitlines()[44],
                                               "interpretation": "the explicit round-trip route turns after rung13 and returns through rung12"}],
         "SOURCE_DISTINCTION_DRIFT")


def event_from_source(note: dict, key: str) -> dict:
    need(note["onset_q"] is note["duration_q"] is None and
         note["string"] in STRING_NUMBER and note["finger_digit"] in (1, 2, 3, 4) and
         note["degree"] == p07.DEGREES[note["scale_position"] - 1] and
         note["ascii_column_in_group"] % 3 == 0, "SOURCE_NOTE_SCOPE")
    midi = p07.OPEN_MIDI[note["string"]] + note["fret"]
    need(midi % 12 == p07._pitch_class(note["tone"]), "NOTE_PITCH_SPELLING")
    return {"event_id": None, "kind": "note", "string": STRING_NUMBER[note["string"]],
            "fret": note["fret"], "midi": midi, "spelling": note["tone"],
            "degree_contexts": {f"{key}-major-pentatonic": {"source_label": str(note["degree"]),
                                                           "ordinal": note["scale_position"],
                                                           "alteration": 0}},
            "finger": note["finger_digit"], "onset_q": None, "duration_q": None,
            "attack": "picked", "tie_from": None}


def source_refs(card: dict, candidate: dict) -> list[str]:
    guidance = candidate["instructions"]
    return [card["source_refs"]["txt"], card["source_refs"]["pdf_card"],
            card["source_refs"]["pdf_route"], guidance["overview_ref"],
            guidance["practice_and_challenge_ref"], guidance["pdf_overview_ref"],
            guidance["pdf_practice_ref"]]


def project_record(card: dict, candidate: dict, index: int) -> dict:
    key, local, root_fret = p07.KEYS[index - 1], f"L32-rung{index:02d}", index + 4
    need(card["source_local_key"] == local and card["rung_number"] == f"{index:02d}" and
         card["key"] == key and card["root_string"] == "E" and card["root_fret"] == root_fret and
         [card["frame_low"], card["frame_high"]] == [root_fret - 1, root_fret + 2] and
         card["degree_map"] == list(p07.DEGREES) and len(card["scale_tones"]) == 11 and
         card["linked_order"] == ["A ascending", "A descending", "B ascending", "B descending"] and
         card["linked_note_count"] == 124 and card["octave_rung"] == (index == 13) and
         all(card[k] is None for k in ("canonical_item_id", "canonical_variant_id", "onset_q",
                                        "duration_q", "fixed_bpm", "note_per_click")) and
         all(card[k] is False for k in ("runtime_eligible", "runtime_admitted", "imported", "admitted")),
         "CARD_SCOPE")
    refs = source_refs(card, candidate)
    events, groups, blocks = [], [], []
    for module_name, direction_name, start in MODULE_LAYOUT:
        module = card["modules"][0 if module_name == "A" else 1]
        direction = module["directions"][0 if direction_name == "ascending" else 1]
        spec = p07.MODULES[module_name]
        size, group_count = spec["size"], spec["groups_each_direction"]
        need(module["module"] == module_name and module["group_size"] == size and
             module["note_count"] == spec["note_count"] and
             direction["direction"] == direction_name and
             len(direction["notes"]) == group_count * size and
             len(direction["groups"]) == group_count and len(direction["raw_rows"]) == 8 and
             direction["path_line"] == "PATH " + " | ".join(p07.PATHS[module_name][direction_name]),
             "MODULE_SCOPE")
        blocks.append({"module": module_name, "direction": direction_name,
                       "source_path_line": direction["path_line"], "source_raw_rows": direction["raw_rows"],
                       "event_local_ordinals": list(range(start + 1, start + len(direction["notes"]) + 1))})
        for note_index, note in enumerate(direction["notes"], 1):
            need(note["ordinal"] == note_index and note["group_ordinal"] ==
                 (note_index - 1) // size + 1 and note["tone"] ==
                 card["scale_tones"][note["scale_position"] - 1], "NOTE_ORDER")
            events.append(event_from_source(note, key))
        for group_index, group in enumerate(direction["groups"], 1):
            whole_index = len(groups) + 1
            ordinals = [start + ordinal for ordinal in group["note_ordinals"]]
            notes = [direction["notes"][ordinal - 1] for ordinal in group["note_ordinals"]]
            need(group["ordinal"] == group_index and len(ordinals) == size and
                 group["note_ordinals"] == list(range((group_index - 1) * size + 1,
                                                       group_index * size + 1)) and
                 group["degrees"] == [note["degree"] for note in notes] and
                 group["string_path"] == p07.PATHS[module_name][direction_name][group_index - 1] and
                 group["D_start_group_start_stroke"] == ("D" if whole_index % 2 else "U"),
                 "GROUP_SCOPE")
            groups.append({"whole_cell_group": whole_index, "module": module_name,
                           "direction": direction_name, "module_direction_group": group_index,
                           "event_local_ordinals": ordinals,
                           "source_scale_positions": [note["scale_position"] for note in notes],
                           "source_degree_labels": group["degrees"],
                           "source_string_path": group["string_path"],
                           "source_D_start_first_stroke": group["D_start_group_start_stroke"],
                           "group_size": size,
                           "source_grouped_pulse": "one eighth-note triplet per beat" if module_name == "A"
                                                   else "one quintuplet per beat",
                           "beat_unit_q": None})
    need(len(events) == 124 and len(groups) == 32 and
         all((events[a]["string"], events[a]["fret"], events[a]["midi"]) ==
             (events[b]["string"], events[b]["fret"], events[b]["midi"])
             for a, b in ((26, 27), (53, 54), (88, 89))), "REARTICULATED_ROOTS")
    boundary = card["linked_boundary"]
    need(boundary == {"after": "A descending note 54", "before": "B ascending note 1",
                      "degree": 1, "string": "E", "fret": root_fret,
                      "separate_rearticulated_contacts": True, "pick_cycle_continues": True},
         "LINKED_BOUNDARY")
    variants, memberships = [], []
    for mode, start, end, first_group, last_group in (("A", 1, 54, 1, 18),
                                                       ("B", 55, 124, 19, 32),
                                                       ("linked_A_B", 1, 124, 1, 32)):
        for pick in ("D", "U"):
            label = f"major-pentatonic-{mode}-{pick}-start"
            variants.append({"id": None, "label": label, "event_ids": None,
                             "source_refs": refs, "route": "two_octave_six_string_rung",
                             "pick_start": pick, "pick_start_origin": "source_authored",
                             "role": "notation_practice", "accent_policy": "source_unspecified",
                             "grouping": {"kind": "unresolved", "notes_per_beat": None,
                                          "beat_unit_q": None, "marking_factor": [1, 1],
                                          "source_label": "grouped triplet/quintuplet or later displacement mode"},
                             "tail_pause": None,
                             "unresolved": ["No selected clock, grouped/displacement mode, absolute BPM or pause binding."]})
            memberships.append({"label": label, "mode": mode, "pick_start": pick,
                                "event_local_ordinals": list(range(start, end + 1)),
                                "group_indices": list(range(first_group, last_group + 1)),
                                "rearticulated_high_root_ordinals": ([27, 28] if mode == "A" else
                                                                      [89, 90] if mode == "B" else
                                                                      [27, 28, 89, 90]),
                                "linked_low_root_ordinals": [54, 55] if mode == "linked_A_B" else []})
    fields = {"id": None, "workbook_id": None, "module_id": None, "legacy_level": 32,
              "title": f"Rung {index:02d}: {key} major pentatonic rolling and cycle sequences",
              "kind": "notation", "content_revision": None, "status": "converted_candidate",
              "runtime_eligible": False, "source_refs": refs, "authored_text_refs": refs,
              "normalization": [{"kind": "representation_metadata",
                                 "basis": "P07 whole-Level32 candidate and complete original TXT/PDF",
                                 "text": "Two source modules form a 124-contact linked cell; repeated roots are separate picked contacts."}],
              "context": {"local_code": local, "root_string": "E", "root_fret": root_fret,
                          "frame": [root_fret - 1, root_fret + 2],
                          "source_scale_tones": card["scale_tones"], "source_degree_map": card["degree_map"],
                          "linked_order": card["linked_order"],
                          "route": "UP rungs01-13; printed DOWN landmarks13-01; continuous return12-01",
                          "pick_continues_at_groups_turn_module_boundary_and_shift": True,
                          "rhythm_modes_source_only": ["grouped triplet/quintuplet", "sixteenth-note displacement"],
                          "tuning_open_midi": [40, 45, 50, 55, 59, 64], "capo": 0},
              "events": events,
              "timing": {"status": "unresolved", "unit": "quarter",
                         "basis": "Source grouped beat counts and practice modes do not allocate a quarter-note grid",
                         "selected_pulse": None},
              "rubric": None, "resource_requirements": [],
              "ambiguities": ["Quarter-note onsets/durations, note-per-click and absolute BPM are unassigned.",
                              "Grouped triplet/quintuplet versus displacement mode is unselected.",
                              "Module boundary, pause and route-level timing remain unbound."],
              "control_scope": {"local_case": f"Level32 rung{index:02d} {key} major-pentatonic linked 124-contact cell",
                                "extent": "complete_selected_case", "whole_workbook_complete": False,
                                "source_event_count": 124, "basis_refs": refs,
                                "unresolved": ["Identity, lineage and route-level admission pending."]},
              "variants": variants, "lineage": None}
    need(set(fields) == FIELDS, "FIELD_SHAPE")
    return {"source_local_key": local, "rung_number": index, "key": key, "root_fret": root_fret,
            "frame": [root_fret - 1, root_fret + 2], "schema1_fields": fields,
            "group_memberships": groups, "variant_memberships": memberships,
            "source_printed_blocks": blocks, "source_modules": card["modules"],
            "source_linked_boundary": boundary, "identity_state": "unallocated",
            "schema1_importable": False,
            "open_gaps": ["canonical identities and lineage", "quarter-note timing/mode/pause binding",
                          "runtime/Curriculum admission"]}


def build(root: Path = ROOT, candidate_override: dict | None = None) -> tuple[dict, dict, dict]:
    pin(root)
    txt_raw, pdf_raw = (root / p07.TXT_REL).read_bytes(), (root / p07.PDF_REL).read_bytes()
    candidate = candidate_override if candidate_override is not None else json.loads((root / CANDIDATE).read_text())
    rebuilt = p07.build_candidate(txt_data=txt_raw, pdf_data=pdf_raw)
    need(candidate == rebuilt, "P07_SOURCE_CANDIDATE_DRIFT")
    need(candidate["level"] == 32 and len(candidate["records"]) == 13 and
         candidate["whole_workbook_complete"] is False and
         all(candidate[k] is False for k in ("runtime_eligible", "runtime_admitted", "imported", "admitted")),
         "SOURCE_SCOPE")
    preserved = preserve_sources(candidate, txt_raw, pdf_raw)
    package = json.loads((root / PACKAGE).read_text())
    registry = json.loads((root / REGISTRY).read_text())
    current = [record for record in package["records"] if record.get("legacy_level") == 32]
    identities = [entity for entity in registry["entities"] if entity.get("id") == "fg:workbook:000032" or
                  entity.get("parent") == "fg:workbook:000032"]
    need(len(package["records"]) == 659 and not current and not identities, "CURRENT659_LEVEL32_OVERLAP")
    records = [project_record(card, candidate, index) for index, card in enumerate(candidate["records"], 1)]
    route = candidate["routes"]
    up = [f"L32-rung{i:02d}" for i in range(1, 14)]
    down = list(reversed(up))
    need(route["up"]["rungs"] == up and route["down_standalone"]["rungs"] == down and
         route["down_return"]["rungs"] == down[1:] and
         route["continuous_round_trip"]["rungs"] == up + down[1:] and
         route["continuous_round_trip"]["cell_count"] == 25 and
         route["continuous_round_trip"]["linked_notes"] == 3100 and
         route["continuous_round_trip"]["authored_grouped_beats_instruction_only"] == 800,
         "ROUTE_SOURCE")
    counts = {"records": 13, "groups": 416, "events": 1612, "variants": 78,
              "module_A_events": 702, "module_B_events": 910,
              "continuous_round_trip_cells": 25, "round_trip_linked_contact_traversals": 3100,
              "source_grouped_beats_instruction_only": 800,
              "preserved_txt_lines": 741, "preserved_pdf_pages": 16}
    proposal = {"proposal_version": "parallel12-level032-unallocated-schema1-fields.1",
                "classification": "source_mapped_field_proposal_not_schema1_importable",
                "legacy_level": 32,
                "source_pins": {str(path): {"bytes": (root / path).stat().st_size, "sha256": digest}
                                for path, (_, digest) in PINS.items()},
                "source_preservation_sha256": sha(encode(preserved)),
                "counts": counts, "source_exceptions": candidate["exceptions"],
                "source_distinctions": preserved["source_distinctions"],
                "source_guidance": candidate["instructions"], "source_shape": candidate["shape"],
                "source_routes": candidate["routes"],
                "current659_level32_records": 0, "current659_level32_workbook_identity": False,
                "representative_collision": None,
                "canonical_ids_allocated": False, "runtime_eligible": False, "admitted": False,
                "fixed_bpm": None, "note_per_click": None, "onset_q": None, "duration_q": None,
                "records": records}
    handoff = {"version": "parallel12-level032-allocation-handoff.1",
               "status": "pending_P02_serial_floor_and_allocation_authority",
               "source_preservation_sha256": sha(encode(preserved)),
               "proposal_sha256": sha(encode(proposal)),
               "source_map": preserved["source_map"],
               "routes": {"up": up, "down_standalone": down, "down_return": down[1:],
                          "continuous_round_trip": up + down[1:],
                          "turn_after_rung": "L32-rung13", "shift_frets_up": 1,
                          "shift_frets_down": -1},
               "record_count": 13, "group_count": 416, "event_count": 1612, "variant_count": 78,
               "current659_level32_records": 0, "current659_level32_workbook_identity": False,
               "representative_collision": None,
               "decisions_required": ["P02 serial floor, workbook/module/item/variant identity and source-key bridge",
                                      "Curriculum review of overlapping windows, repeated roots, final footer distinction and linked module/route order",
                                      "Reviewed grouped/displacement timing, pause, lineage and admission policy before import"],
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
         all(proposal[k] is None for k in ("fixed_bpm", "note_per_click", "onset_q", "duration_q")),
         "INVALID_AUTHORITY")
    counts = {"records": 13, "groups": 416, "events": 1612, "variants": 78,
              "module_A_events": 702, "module_B_events": 910,
              "continuous_round_trip_cells": 25, "round_trip_linked_contact_traversals": 3100,
              "source_grouped_beats_instruction_only": 800,
              "preserved_txt_lines": 741, "preserved_pdf_pages": 16}
    need(proposal["counts"] == counts and
         (handoff["record_count"], handoff["group_count"], handoff["event_count"],
          handoff["variant_count"]) == (13, 416, 1612, 78), "COVERAGE")
    keys = [f"L32-rung{i:02d}" for i in range(1, 14)]
    route = handoff["routes"]
    need([r["source_local_key"] for r in proposal["records"]] == keys and
         [r["source_local_key"] for r in handoff["source_map"]] == keys and
         route["up"] == keys and route["down_standalone"] == list(reversed(keys)) and
         route["down_return"] == list(reversed(keys))[1:] and
         route["continuous_round_trip"] == keys + list(reversed(keys))[1:] and
         route["turn_after_rung"] == "L32-rung13", "ROUTE_OR_CASE_ORDER")
    for index, (record, card) in enumerate(zip(proposal["records"], candidate["records"], strict=True), 1):
        fields = record["schema1_fields"]
        need(record["rung_number"] == index and record["key"] == p07.KEYS[index - 1] and
             record["root_fret"] == index + 4 and record["frame"] == [index + 3, index + 6] and
             record["identity_state"] == "unallocated" and record["schema1_importable"] is False and
             set(fields) == FIELDS and fields["legacy_level"] == 32 and
             fields["context"]["local_code"] == record["source_local_key"] and
             all(fields[k] is None for k in ("id", "workbook_id", "module_id", "content_revision", "lineage")) and
             fields["runtime_eligible"] is False and fields["timing"]["status"] == "unresolved" and
             fields["timing"]["selected_pulse"] is None, "INVALID_AUTHORITY")
        need(record["source_modules"] == card["modules"] and
             record["source_linked_boundary"] == card["linked_boundary"] and
             len(record["source_printed_blocks"]) == 4 and
             len(fields["events"]) == 124 and len(record["group_memberships"]) == 32 and
             len(fields["variants"]) == len(record["variant_memberships"]) == 6, "CELL_COUNT_OR_SOURCE")
        expected = project_record(card, candidate, index)
        need(record["source_printed_blocks"] == expected["source_printed_blocks"] and
             record["group_memberships"] == expected["group_memberships"], "GROUP_MEMBERSHIP")
        need(fields["events"] == expected["schema1_fields"]["events"], "UNSUPPORTED_TIMING_OR_NOTE")
        need(fields["variants"] == expected["schema1_fields"]["variants"] and
             record["variant_memberships"] == expected["variant_memberships"], "VARIANT_MEMBERSHIP")
    need(handoff["proposal_sha256"] == sha(encode(proposal)) and
         proposal["current659_level32_records"] == handoff["current659_level32_records"] == 0 and
         proposal["current659_level32_workbook_identity"] is handoff["current659_level32_workbook_identity"] is False and
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
    print(json.dumps({"status": "level032_unallocated_pending_P02",
                      "counts": verify_projection(preserved, proposal, handoff,
                                                  json.loads((ROOT / CANDIDATE).read_text()))}, sort_keys=True))


if __name__ == "__main__":
    main()
