#!/usr/bin/env python3
"""Whole Level19 triad source fields, detached from canonical allocation."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import curriculum_level019_whole_candidate as p09

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = p09.BUILD_REL / "candidate-02.json"
RESULT = Path("Results/parallel-09/exercises/conversion/20260923T150100Z-2.3.1.1.1-level019-whole-r01-results.md")
PACKAGE = Path("Content/controls/curriculum-v1/package.json")
REGISTRY = Path("Content/controls/curriculum-v1/identity-registry.json")
OUT = Path("Build/parallel-12/level019-schema1-unallocated-r01")
PINS = {
    CANDIDATE: (514263, "c7006360d4de080bafc488cd11098d5b1c464beb88c8a6a89c1f1d02422ea91a"),
    RESULT: (None, "82fff0aa3ecbcf54e8a7e89a813c328c075aef6bfe3ee115632be9391739b923"),
    p09.TXT_REL: (p09.TXT_BYTES, p09.TXT_SHA256),
    p09.PDF_REL: (p09.PDF_BYTES, p09.PDF_SHA256),
    PACKAGE: (None, "766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255"),
    REGISTRY: (None, "5d265859e1e8a5a530a0e53d88b019a1c920f3bba6cccb4ef0fef2f7640007e5"),
}
FIELDS = {"id", "workbook_id", "module_id", "legacy_level", "title", "kind", "content_revision",
          "status", "runtime_eligible", "source_refs", "authored_text_refs", "normalization", "context",
          "events", "timing", "rubric", "resource_requirements", "ambiguities", "control_scope",
          "variants", "lineage"}
OPEN = {"E": (1, 40), "A": (2, 45), "D": (3, 50), "G": (4, 55), "B": (5, 59), "e": (6, 64)}
NATURAL = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
GUIDANCE_REFS = ["L19-TXT1-6-8", "L19-TXT1-11-16", "L19-TXT1-19-23", "L19-TXT1-26-30",
                 "L19-TXT1-33-35", "L19-TXT1-38-43", "L19-TXT1-46-48", "L19-TXT1-51-65",
                 "L19-TXT1-437-443", "L19-TXT1-445-450", "L19-PDF1-p1", "L19-PDF1-p2",
                 "L19-PDF1-p9", "L19-PDF1-p10"]


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


def pitch_class(spelling: str) -> int:
    need(re.fullmatch(r"[A-G](?:#|b)?", spelling) is not None, "SPELLING_SHAPE")
    return (NATURAL[spelling[0]] + (1 if spelling.endswith("#") else -1 if spelling.endswith("b") else 0)) % 12


def txt_span(ref: str, lines: list[str]) -> dict:
    match = re.fullmatch(r"L19-TXT1-(\d+)-(\d+)", ref)
    need(match is not None, "TXT_REF")
    first, last = map(int, match.groups())
    need(1 <= first <= last <= len(lines), "TXT_SPAN")
    return {"ref": ref, "first_line": first, "last_line": last,
            "text_sha256": sha("\n".join(lines[first - 1:last]).encode())}


def source_event(note: dict, key: str, tones: list[str]) -> dict:
    need(note["onset_q"] is note["duration_q"] is None and
         note["string"] in OPEN and 1 <= note["degree"] <= 15 and
         note["finger_digit"] in ("1", "2", "3", "4"), "SOURCE_NOTE_SCOPE")
    string, open_midi = OPEN[note["string"]]
    midi = open_midi + note["fret"]
    spelling = tones[note["degree"] - 1]
    need(midi % 12 == pitch_class(spelling), "NOTE_PITCH_SPELLING")
    return {"event_id": None, "kind": "note", "string": string, "fret": note["fret"],
            "midi": midi, "spelling": spelling,
            "degree_contexts": {f"{key}-major": {"source_label": str(note["degree"]),
                                                  "ordinal": note["degree"], "alteration": 0}},
            "finger": int(note["finger_digit"]), "onset_q": None, "duration_q": None,
            "attack": "picked", "tie_from": None}


def build(root: Path = ROOT, candidate_override: dict | None = None) -> tuple[dict, dict]:
    pin(root)
    candidate = candidate_override if candidate_override is not None else json.loads((root / CANDIDATE).read_text())
    need(candidate == p09.build_candidate(), "P09_SOURCE_CANDIDATE_DRIFT")
    need(candidate["level"] == 19 and len(candidate["records"]) == 13 and
         candidate["whole_source_batch_structurally_reconciled"] is True and not candidate["exceptions"] and
         all(candidate[k] is False for k in ("runtime_eligible", "runtime_admitted", "imported", "admitted")),
         "SOURCE_SCOPE")
    foundation = json.loads((root / PACKAGE).read_text())
    registry = json.loads((root / REGISTRY).read_text())
    current = [r for r in foundation["records"] if r.get("legacy_level") == 19]
    identities = [e for e in registry["entities"] if e.get("id") == "fg:workbook:000019" or
                  e.get("parent") == "fg:workbook:000019"]
    need(len(foundation["records"]) == 659 and not current and not identities, "CURRENT659_LEVEL19_OVERLAP")
    lines = (root / p09.TXT_REL).read_text().splitlines()
    records, source_map = [], []
    for index, card in enumerate(candidate["records"], 1):
        key, local = p09.KEYS[index - 1], f"L19-rung{index:02d}"
        start = 71 + (index - 1) * 28
        txt_ref, pdf_ref = f"L19-TXT1-{start}-{start + 24}", f"L19-PDF1-p{3 + (index - 1) // 2}"
        need(card["source_local_key"] == local and card["rung"] == index and card["key"] == key and
             card["root_string"] == "E" and card["root_fret"] == index + 4 and
             card["frame"] == [index + 3, index + 6] and
             card["scale_tones"] == [*p09.SCALE7[index - 1], *p09.SCALE7[index - 1], key] and
             card["chord_names"] == list(p09.CHORDS7[index - 1]) and
             card["source_refs"] == {"txt": txt_ref, "pdf_card": pdf_ref, "pdf_map": "L19-PDF1-p2"} and
             len(card["triads"]) == 22 and
             all(card[k] is None for k in ("canonical_item_id", "canonical_variant_id", "onset_q",
                                            "duration_q", "fixed_bpm", "note_per_click")) and
             all(card[k] is False for k in ("runtime_eligible", "runtime_admitted", "imported", "admitted")),
             "CARD_SCOPE")
        span = txt_span(txt_ref, lines)
        need(lines[start - 1] == card["printed_txt"]["heading"] and
             lines[start + 23] == card["printed_txt"]["footer"], "TXT_CARD")
        for row in ("ascending_hrm", "ascending_deg", "ascending_fng", "ascending_tab",
                    "descending_hrm", "descending_deg", "descending_fng", "descending_tab"):
            need(card["printed_txt"][row] == card["printed_pdf"][row], "PRINTED_ROW_RECONCILIATION")
        refs = [txt_ref, pdf_ref, *GUIDANCE_REFS]
        events, triad_memberships = [], []
        for ordinal, triad in enumerate(card["triads"], 1):
            half = "up" if ordinal <= 11 else "down"
            local_group = (ordinal - 1) % 11 + 1
            root_degree = (local_group if half == "up" else 12 - local_group)
            # Descending group 1: 15-13-11, with harmonic root degree 11.
            need(triad["ordinal"] == ordinal and triad["half"] == half and
                 len(triad["notes"]) == 3 and
                 triad["harmonic_root_degree"] == root_degree and
                 triad["function_degree"] == (root_degree - 1) % 7 + 1 and
                 triad["roman"] == p09.ROMANS[(root_degree - 1) % 7] and
                 triad["quality"] == p09.QUALITIES[(root_degree - 1) % 7] and
                 triad["chord_name"] == card["chord_names"][(root_degree - 1) % 7], "TRIAD_SCOPE")
            ordinals = list(range((ordinal - 1) * 3 + 1, ordinal * 3 + 1))
            roles = ["root", "third", "fifth"] if half == "up" else ["fifth", "third", "root"]
            for slot, note in enumerate(triad["notes"], 1):
                need(note["ordinal"] == ordinals[slot - 1] and note["half"] == half and
                     note["triad"] == local_group and note["slot"] == slot and
                     note["role"] == roles[slot - 1] and
                     note["is_high_root_turn"] == (note["ordinal"] in (33, 34)), "TRIAD_NOTE_SCOPE")
                events.append(source_event(note, key, card["scale_tones"]))
            triad_memberships.append({"whole_cell_triad": ordinal, "source_triad": local_group,
                                      "direction": "ascending" if half == "up" else "descending",
                                      "event_local_ordinals": ordinals,
                                      "source_degrees": [n["degree"] for n in triad["notes"]],
                                      "source_note_roles": roles,
                                      "harmonic_root_degree": root_degree,
                                      "function_degree": triad["function_degree"],
                                      "roman": triad["roman"], "quality": triad["quality"],
                                      "chord_name": triad["chord_name"],
                                      "source_beat_options": ["one_triad_per_beat_triplets",
                                                              "two_triads_per_beat_sextuplets"],
                                      "selected_beat_unit_q": None})
        need(len(events) == 66 and len(triad_memberships) == 22 and
             (events[32]["string"], events[32]["fret"], events[32]["midi"]) ==
             (events[33]["string"], events[33]["fret"], events[33]["midi"]), "TURN_ROOT")
        variants, memberships = [], []
        for pick in ("D", "U"):
            label = f"broken-triads-{pick}-start"
            variants.append({"id": None, "label": label, "event_ids": None, "source_refs": refs,
                             "route": "22_sequential_broken_triads_high_root_repeated",
                             "pick_start": pick, "pick_start_origin": "source_authored",
                             "role": "notation_practice", "accent_policy": "learning_triad_root_per_source",
                             "grouping": {"kind": "unresolved", "notes_per_beat": None,
                                          "beat_unit_q": None, "marking_factor": [1, 1],
                                          "source_label": "learning: one triad/beat triplets; performance: two triads/beat sextuplets"},
                             "tail_pause": None,
                             "unresolved": ["Pulse mode, absolute BPM and optional inter-cell pause unbound."]})
            memberships.append({"label": label, "event_local_ordinals": list(range(1, 67)),
                                "triad_indices": list(range(1, 23)),
                                "repeated_high_root_ordinals": [33, 34]})
        fields = {"id": None, "workbook_id": None, "module_id": None, "legacy_level": 19,
                  "title": f"Rung {index:02d}: {key} major two-octave diatonic triads",
                  "kind": "notation", "content_revision": None, "status": "converted_candidate",
                  "runtime_eligible": False, "source_refs": refs, "authored_text_refs": refs,
                  "normalization": [{"kind": "representation_metadata", "basis": "P09 whole-Level19 candidate and original TXT/PDF",
                                     "text": "Each printed triad is a sequential three-note broken triad, not a simultaneous chord. Descending notes retain fifth-third-root order; harmonic function follows the final root."}],
                  "context": {"local_code": local, "route": "UP rungs01-13; DOWN return12-01; continuous trip has 25 cells",
                              "position": f"low-E root fret {index + 4}; frame {index + 3}-{index + 6}",
                              "pick_start": "D or U; alternate continuously across triads, strings, turn and key changes",
                              "pick_start_variants": ["D", "U"], "pick_continues_at_turn": True,
                              "tuning_open_midi": [40, 45, 50, 55, 59, 64], "capo": 0,
                              "source_triad_count": 22, "source_notes_per_triad": 3,
                              "shift_after_complete_cell_only": True},
                  "events": events,
                  "timing": {"status": "unresolved", "unit": "quarter",
                             "basis": "Authored triplet and sextuplet pulse options do not select an authorized quarter-note event grid or pause binding",
                             "source_pulses": ["learning: one triad per beat as eighth-note triplets",
                                               "performance: two triads per beat as sixteenth-note triplets (sextuplets)"],
                             "selected_pulse": None},
                  "rubric": None, "resource_requirements": [],
                  "ambiguities": ["Pulse mode, quarter-note onsets/durations and absolute BPM are unassigned.",
                                  "Optional one-beat inter-cell pause has no selected beat-unit/pass binding.",
                                  "No simultaneous-chord or performed-audio claim is authorized."],
                  "control_scope": {"local_case": f"Level19 rung{index:02d} {key} major full 66-contact broken-triad cell",
                                    "extent": "complete_selected_case", "whole_workbook_complete": False,
                                    "source_event_count": 66, "basis_refs": refs,
                                    "unresolved": ["Identity, lineage and route-level admission pending."]},
                  "variants": variants, "lineage": None}
        need(set(fields) == FIELDS, "FIELD_SHAPE")
        records.append({"source_local_key": local, "rung_number": index, "key": key,
                        "root_fret": index + 4, "frame": [index + 3, index + 6],
                        "schema1_fields": fields, "triad_memberships": triad_memberships,
                        "variant_memberships": memberships,
                        "source_printed_txt": card["printed_txt"], "source_printed_pdf": card["printed_pdf"],
                        "identity_state": "unallocated", "schema1_importable": False,
                        "open_gaps": ["canonical identities and lineage", "pulse/timing and pause binding",
                                      "runtime/Curriculum admission"]})
        source_map.append({"source_local_key": local, "rung_number": index, "key": key,
                           "root_fret": index + 4, "frame": [index + 3, index + 6],
                           "txt": span, "pdf_card": pdf_ref, "pdf_harmony_map": "L19-PDF1-p2"})
    up = [f"L19-rung{i:02d}" for i in range(1, 14)]
    down = [f"L19-rung{i:02d}" for i in range(12, 0, -1)]
    route = candidate["neck_route"]
    need(route["ascending_rungs"] == list(range(1, 14)) and
         route["descending_rungs_after_turn"] == list(range(12, 0, -1)) and
         route["single_turn_cell_sequence"] == list(range(1, 14)) + list(range(12, 0, -1)) and
         route["single_turn_cell_count"] == 25 and route["notes_per_cell"] == 66 and
         route["single_turn_note_count"] == 1650, "ROUTE_SCOPE")
    counts = {"records": 13, "triads": 286, "events": 858, "variants": 26,
              "up_landmark_cells": 13, "down_return_cells": 12,
              "continuous_round_trip_cells": 25, "round_trip_contact_traversals": 1650}
    proposal = {"proposal_version": "parallel12-level019-unallocated-schema1-fields.1",
                "classification": "source_mapped_field_proposal_not_schema1_importable",
                "legacy_level": 19,
                "source_pins": {str(path): {"bytes": (root / path).stat().st_size, "sha256": digest}
                                for path, (_, digest) in PINS.items()},
                "counts": counts, "source_guidance": candidate["instructions"],
                "source_pdf_route_map": candidate["pdf_route_map"],
                "source_exceptions": candidate["exceptions"],
                "current659_level19_records": 0, "current659_level19_workbook_identity": False,
                "representative_collision": None,
                "canonical_ids_allocated": False, "runtime_eligible": False, "admitted": False,
                "fixed_bpm": None, "note_per_click": None, "onset_q": None, "duration_q": None,
                "records": records}
    handoff = {"version": "parallel12-level019-allocation-handoff.1",
               "status": "pending_P02_serial_floor_and_allocation_authority",
               "proposal_sha256": sha(encode(proposal)), "source_map": source_map,
               "guidance_refs": GUIDANCE_REFS,
               "routes": {"up_landmarks": up, "down_return": down,
                          "continuous_round_trip": up + down, "turn_after_rung": "L19-rung13",
                          "shift_frets_up": 1, "shift_frets_down": -1},
               "record_count": 13, "triad_count": 286, "event_count": 858, "variant_count": 26,
               "current659_level19_records": 0, "current659_level19_workbook_identity": False,
               "representative_collision": None,
               "decisions_required": ["P02 serial floor, workbook/module/item/variant identity and source-key bridge",
                                      "Curriculum review of broken-triad roles/functions, high-root turn and 25-cell route",
                                      "Reviewed pulse/timing/pause binding and lineage/admission policy before import"],
               "selected_choice": None, "allocation_allowed": False, "no_admission": True}
    verify(proposal, handoff)
    return proposal, handoff


def verify(proposal: dict, handoff: dict) -> dict:
    need(proposal["canonical_ids_allocated"] is False and proposal["runtime_eligible"] is False and
         proposal["admitted"] is False and handoff["allocation_allowed"] is False and
         handoff["no_admission"] is True and handoff["selected_choice"] is None and
         all(proposal[k] is None for k in ("fixed_bpm", "note_per_click", "onset_q", "duration_q")),
         "INVALID_AUTHORITY")
    counts = {"records": 13, "triads": 286, "events": 858, "variants": 26,
              "up_landmark_cells": 13, "down_return_cells": 12,
              "continuous_round_trip_cells": 25, "round_trip_contact_traversals": 1650}
    need(proposal["counts"] == counts and
         (handoff["record_count"], handoff["triad_count"], handoff["event_count"], handoff["variant_count"]) ==
         (13, 286, 858, 26), "COVERAGE")
    keys = [f"L19-rung{i:02d}" for i in range(1, 14)]
    need([r["source_local_key"] for r in proposal["records"]] == keys and
         [r["source_local_key"] for r in handoff["source_map"]] == keys and
         handoff["routes"]["up_landmarks"] == keys and
         handoff["routes"]["down_return"] == list(reversed(keys[:-1])) and
         handoff["routes"]["continuous_round_trip"] == keys + list(reversed(keys[:-1])) and
         handoff["routes"]["turn_after_rung"] == "L19-rung13", "ROUTE_OR_CASE_ORDER")
    for index, record in enumerate(proposal["records"], 1):
        fields = record["schema1_fields"]
        need(record["rung_number"] == index and record["key"] == p09.KEYS[index - 1] and
             record["root_fret"] == index + 4 and record["frame"] == [index + 3, index + 6] and
             record["identity_state"] == "unallocated" and record["schema1_importable"] is False and
             set(fields) == FIELDS and fields["legacy_level"] == 19 and
             fields["context"]["local_code"] == record["source_local_key"] and
             all(fields[k] is None for k in ("id", "workbook_id", "module_id", "content_revision", "lineage")) and
             fields["runtime_eligible"] is False and fields["timing"]["status"] == "unresolved" and
             fields["timing"]["selected_pulse"] is None, "INVALID_AUTHORITY")
        need(len(fields["events"]) == 66 and len(record["triad_memberships"]) == 22 and
             len(fields["variants"]) == len(record["variant_memberships"]) == 2, "CELL_COUNT")
        for ordinal, event in enumerate(fields["events"], 1):
            group = record["triad_memberships"][(ordinal - 1) // 3]
            degree = group["source_degrees"][(ordinal - 1) % 3]
            need(event["event_id"] is event["onset_q"] is event["duration_q"] is None and
                 event["kind"] == "note" and event["midi"] == [40, 45, 50, 55, 59, 64][event["string"] - 1] + event["fret"] and
                 event["midi"] % 12 == pitch_class(event["spelling"]) and
                 event["degree_contexts"] == {f"{record['key']}-major": {
                     "source_label": str(degree), "ordinal": degree, "alteration": 0}} and
                 1 <= event["finger"] <= 4, "UNSUPPORTED_TIMING_OR_NOTE")
        for ordinal, group in enumerate(record["triad_memberships"], 1):
            half = "ascending" if ordinal <= 11 else "descending"
            root_degree = (ordinal if ordinal <= 11 else 23 - ordinal)
            need(group["whole_cell_triad"] == ordinal and group["source_triad"] == (ordinal - 1) % 11 + 1 and
                 group["direction"] == half and group["event_local_ordinals"] ==
                 list(range((ordinal - 1) * 3 + 1, ordinal * 3 + 1)) and
                 group["harmonic_root_degree"] == root_degree and
                 group["function_degree"] == (root_degree - 1) % 7 + 1 and
                 group["roman"] == p09.ROMANS[(root_degree - 1) % 7] and
                 group["quality"] == p09.QUALITIES[(root_degree - 1) % 7] and
                 group["source_note_roles"] == (["root", "third", "fifth"] if ordinal <= 11 else
                                                ["fifth", "third", "root"]), "TRIAD_MEMBERSHIP")
        need((fields["events"][32]["string"], fields["events"][32]["fret"], fields["events"][32]["midi"]) ==
             (fields["events"][33]["string"], fields["events"][33]["fret"], fields["events"][33]["midi"]),
             "TURN_ROOT")
        need([v["pick_start"] for v in fields["variants"]] == ["D", "U"] and
             all(v["id"] is v["event_ids"] is None and v["grouping"]["kind"] == "unresolved" and
                 v["grouping"]["beat_unit_q"] is None for v in fields["variants"]) and
             all(m["event_local_ordinals"] == list(range(1, 67)) and
                 m["triad_indices"] == list(range(1, 23)) and
                 m["repeated_high_root_ordinals"] == [33, 34]
                 for m in record["variant_memberships"]), "VARIANT_MEMBERSHIP")
    need(handoff["proposal_sha256"] == sha(encode(proposal)) and
         proposal["current659_level19_records"] == handoff["current659_level19_records"] == 0 and
         proposal["current659_level19_workbook_identity"] is handoff["current659_level19_workbook_identity"] is False and
         proposal["representative_collision"] is handoff["representative_collision"] is None,
         "PROPOSAL_HASH_OR_CURRENT659")
    return counts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("build", "verify"))
    args = parser.parse_args()
    proposal, handoff = build()
    if args.command == "build":
        (ROOT / OUT).mkdir(parents=True, exist_ok=True)
        (ROOT / OUT / "field-proposal.json").write_bytes(encode(proposal))
        (ROOT / OUT / "allocation-handoff.json").write_bytes(encode(handoff))
    else:
        need((ROOT / OUT / "field-proposal.json").read_bytes() == encode(proposal), "OUTPUT_DRIFT proposal")
        need((ROOT / OUT / "allocation-handoff.json").read_bytes() == encode(handoff), "OUTPUT_DRIFT handoff")
    print(json.dumps({"status": "unallocated_level019_pending_P02_serial_floor",
                      "counts": verify(proposal, handoff)}, sort_keys=True))


if __name__ == "__main__":
    main()
