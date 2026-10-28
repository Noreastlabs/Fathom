#!/usr/bin/env python3
"""Project P05's whole Level20 synthesis source into unallocated schema1 fields."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import curriculum_level020_whole_synthesis_candidate as p05

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = p05.BUILD_REL / "candidate-c.json"
RESULT = Path("Results/parallel-05/exercises/conversion/20260923T151000Z-2.3.1.1.1-level020-whole-synthesis-r01-results.md")
PACKAGE = Path("Content/controls/curriculum-v1/package.json")
REGISTRY = Path("Content/controls/curriculum-v1/identity-registry.json")
OUT = Path("Build/parallel-12/level020-schema1-unallocated-r01")
PINS = {
    CANDIDATE: (3758457, "3a0bbd3093afb093a96432b2d6e46c676d5a217e23d4c2b0d430577f433b5bff"),
    RESULT: (None, "5335c55557088dca3c0352c8edd735032d2685b47b6a1a6da664e65ed7bbec66"),
    p05.TXT_REL: (p05.TXT_BYTES, p05.TXT_SHA256),
    p05.PDF_REL: (p05.PDF_BYTES, p05.PDF_SHA256),
    PACKAGE: (None, "766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255"),
    REGISTRY: (None, "5d265859e1e8a5a530a0e53d88b019a1c920f3bba6cccb4ef0fef2f7640007e5"),
}
FIELDS = {"id", "workbook_id", "module_id", "legacy_level", "title", "kind", "content_revision",
          "status", "runtime_eligible", "source_refs", "authored_text_refs", "normalization", "context",
          "events", "timing", "rubric", "resource_requirements", "ambiguities", "control_scope",
          "variants", "lineage"}
OPEN = {"E": (1, 40), "A": (2, 45), "D": (3, 50), "G": (4, 55), "B": (5, 59), "e": (6, 64)}
MODULE_COUNTS = [30, 78, 96, 52, 66]
MODULE_GROUPS = [1, 26, 24, 26, 22]
MODULE_BEATS = [15, 26, 24, 26, 22]
GUIDANCE_REFS = ["L20-TXT1-1-74", "L20-TXT1-1453-1466",
                 "L20-PDF1-p1", "L20-PDF1-p2", "L20-PDF1-p29", "L20-PDF1-p30", "L20-PDF1-p31"]


class ProposalError(ValueError):
    pass


def need(ok: bool, code: str) -> None:
    if not ok:
        raise ProposalError(code)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def encode(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def pin(root: Path = ROOT) -> None:
    need(root.resolve() == ROOT.resolve(), "ROOT_DRIFT")
    for path, (length, digest) in PINS.items():
        raw = (root / path).read_bytes()
        need((length is None or len(raw) == length) and sha(raw) == digest, f"INPUT_DRIFT {path}")


def txt_span(ref: str, lines: list[str]) -> dict:
    match = re.fullmatch(r"L20-TXT1-(\d+)-(\d+)", ref)
    need(match is not None, "TXT_REF")
    first, last = map(int, match.groups())
    need(1 <= first <= last <= len(lines), "TXT_SPAN")
    return {"ref": ref, "first_line": first, "last_line": last,
            "text_sha256": sha("\n".join(lines[first - 1:last]).encode())}


def source_event(contact: dict, key: str) -> dict:
    need(contact["onset_q"] is contact["duration_q"] is contact["performed_pick"] is None and
         contact["string"] in OPEN and 1 <= contact["scale_step"] <= 15 and
         contact["printed_finger"] in (1, 2, 3, 4), "SOURCE_CONTACT_SCOPE")
    string, open_midi = OPEN[contact["string"]]
    midi = open_midi + contact["fret"]
    need(midi % 12 == p05._name_pc(contact["printed_note_spelling"]), "CONTACT_PITCH_SPELLING")
    return {"event_id": None, "kind": "note", "string": string, "fret": contact["fret"],
            "midi": midi, "spelling": contact["printed_note_spelling"],
            "degree_contexts": {f"{key}-major": {"source_label": str(contact["printed_degree"]),
                                                  "ordinal": contact["scale_step"], "alteration": 0}},
            "finger": contact["printed_finger"], "onset_q": None, "duration_q": None,
            "attack": "picked", "tie_from": None}


def build(root: Path = ROOT, candidate_override: dict | None = None) -> tuple[dict, dict]:
    pin(root)
    candidate = candidate_override if candidate_override is not None else json.loads((root / CANDIDATE).read_text())
    rebuilt = json.loads(json.dumps(p05.build_candidate()))
    need(candidate == rebuilt, "P05_SOURCE_CANDIDATE_DRIFT")
    need(candidate["level"] == 20 and candidate["rung_count"] == len(candidate["rungs"]) == 13 and
         candidate["module_count"] == 65 and candidate["authored_contact_count"] == 4186 and
         not candidate["source_exceptions"] and candidate["canonical_ids"] is None and
         candidate["review"] == "Pending" and
         all(candidate[k] is False for k in ("runtime_eligible", "imported", "admitted")), "SOURCE_SCOPE")
    foundation = json.loads((root / PACKAGE).read_text())
    registry = json.loads((root / REGISTRY).read_text())
    current = [r for r in foundation["records"] if r.get("legacy_level") == 20]
    identities = [e for e in registry["entities"] if e.get("id") == "fg:workbook:000020" or
                  e.get("parent") == "fg:workbook:000020"]
    need(len(foundation["records"]) == 659 and not current and not identities, "CURRENT659_LEVEL20_OVERLAP")
    lines = (root / p05.TXT_REL).read_text().splitlines()
    need(len(lines) == 1466, "TXT_LINE_COUNT")
    records, source_map, circuits = [], [], []
    for rung_index, rung in enumerate(candidate["rungs"], 1):
        key, root_fret = p05.KEYS[rung_index - 1], rung_index + 4
        need(rung["rung"] == rung_index and rung["key"] == key and
             rung["root_string"] == "E" and rung["root_fret"] == root_fret and
             rung["frame_frets"] == [root_fret - 1, root_fret + 2] and
             rung["txt_heading_line"] == 75 + (rung_index - 1) * 106 and
             rung["pdf_pages"] == [1 + 2 * rung_index, 2 + 2 * rung_index] and
             rung["scale_seven"] == list(p05._scale7(key)) and
             rung["contact_count"] == 322 and len(rung["modules"]) == 5,
             "RUNG_SCOPE")
        keys, boundaries, running = [], [], 0
        for module_index, module in enumerate(rung["modules"], 1):
            local = f"L20-rung{rung_index:02d}-module{module_index}"
            title = p05.MODULES[module_index - 1][1]
            count, group_count = MODULE_COUNTS[module_index - 1], MODULE_GROUPS[module_index - 1]
            start, last = module["txt_line_span"]
            txt_ref, pdf_ref = f"L20-TXT1-{start}-{last}", f"L20-PDF1-p{module['pdf_page']}"
            need(module["module_number"] == module_index and module["contact_count"] == count and
                 len(module["contacts"]) == count and len(module["groups"]) == group_count and
                 module["printed_heading"] == f"MODULE {module_index} - {title} - {count} NOTES" and
                 module["printed_pulse_description"] == p05.MODULES[module_index - 1][-1] and
                 module["pdf_page"] == (rung["pdf_pages"][0] if module_index <= 3 else rung["pdf_pages"][1]) and
                 lines[start - 1] == module["printed_heading"] and
                 lines[last - 1] == module["printed_boundary_instruction"], "MODULE_SCOPE")
            span = txt_span(txt_ref, lines)
            for row in module["source_rows"]:
                need(start < row["txt_line"] < last and
                     lines[row["txt_line"] - 1] == row["printed_row"] and
                     row["pdf_page"] == module["pdf_page"], "PRINTED_ROW_SCOPE")
            refs = [txt_ref, pdf_ref, *GUIDANCE_REFS]
            events, groups = [], []
            for ordinal, contact in enumerate(module["contacts"], 1):
                need(contact["ordinal_in_module"] == ordinal and
                     contact["ordinal_in_circuit"] == running + ordinal and
                     contact["source_refs"]["pdf_page"] == module["pdf_page"] and
                     all(start < contact["source_refs"][k] < last for k in
                         ("txt_degree_line", "txt_finger_line", "txt_tab_line")), "CONTACT_ORDER_REFS")
                events.append(source_event(contact, key))
            for group_index, group in enumerate(module["groups"], 1):
                need(group["group"] == (1 if module_index == 1 else (group_index - 1) % (group_count // 2) + 1) and
                     group["direction"] == ("linear" if module_index == 1 else
                                            "up" if group_index <= group_count // 2 else "down") and
                     group["contact_ordinals"] and
                     all(1 <= n <= count for n in group["contact_ordinals"]), "GROUP_SCOPE")
                groups.append({"whole_module_group": group_index,
                               "source_group": group["group"], "direction": group["direction"],
                               "event_local_ordinals": group["contact_ordinals"],
                               "source_scale_steps": [module["contacts"][n - 1]["scale_step"] for n in group["contact_ordinals"]],
                               "source_printed_degrees": [module["contacts"][n - 1]["printed_degree"] for n in group["contact_ordinals"]],
                               "printed_interval_or_harmony": group["printed_interval_or_harmony"],
                               "selected_beat_unit_q": None})
            need([n for group in groups for n in group["event_local_ordinals"]] == list(range(1, count + 1)) and
                 events[0]["string"] == events[-1]["string"] == 1 and
                 events[0]["fret"] == events[-1]["fret"] == root_fret, "MODULE_CONTACT_COVERAGE")
            variants, memberships = [], []
            for pick in ("D", "U"):
                label = f"synthesis-module{module_index}-{pick}-start"
                variants.append({"id": None, "label": label, "event_ids": None, "source_refs": refs,
                                 "route": "whole_322_contact_circuit_module_order_1_to_5",
                                 "pick_start": pick, "pick_start_origin": "source_authored",
                                 "role": "notation_practice", "accent_policy": "source_module_root_only_when_learning",
                                 "grouping": {"kind": "unresolved", "notes_per_beat": None,
                                              "beat_unit_q": None, "marking_factor": [1, 1],
                                              "source_label": f"learning one note/click; native {module['printed_pulse_description']}"},
                                 "tail_pause": None,
                                 "unresolved": ["Pulse mode, absolute BPM and optional boundary pause unbound."]})
                memberships.append({"label": label, "event_local_ordinals": list(range(1, count + 1)),
                                    "group_indices": list(range(1, group_count + 1))})
            fields = {"id": None, "workbook_id": None, "module_id": None, "legacy_level": 20,
                      "title": f"Rung {rung_index:02d}: {key} major synthesis {title.lower()}",
                      "kind": "notation", "content_revision": None, "status": "converted_candidate",
                      "runtime_eligible": False, "source_refs": refs, "authored_text_refs": refs,
                      "normalization": [{"kind": "representation_metadata", "basis": "P05 whole-Level20 candidate and original TXT/PDF",
                                         "text": "This source module is one ordered portion of a five-module 322-contact circuit; the low root is re-articulated at each module boundary and the frame shifts only after module 5."}],
                      "context": {"local_code": local, "rung": rung_index, "module_number": module_index,
                                  "module_title": title, "circuit_contact_ordinals": [running + 1, running + count],
                                  "route": "UP rungs01-13; DOWN return12-01; 25 full circuits",
                                  "position": f"low-E root fret {root_fret}; frame {root_fret - 1}-{root_fret + 2}",
                                  "pick_start": "D or U; alternate continuously across groups, modules, turns and key changes",
                                  "pick_start_variants": ["D", "U"],
                                  "tuning_open_midi": [40, 45, 50, 55, 59, 64], "capo": 0,
                                  "source_group_count": group_count, "source_contact_count": count,
                                  "source_native_pulse": module["printed_pulse_description"],
                                  "source_native_beats": MODULE_BEATS[module_index - 1],
                                  "shift_after_complete_circuit_only": True},
                      "events": events,
                      "timing": {"status": "unresolved", "unit": "quarter",
                                 "basis": "Source supplies learning one-note/click and native subdivisions/beat counts but does not authorize a selected runtime grid or absolute BPM",
                                 "source_pulses": ["learning: one note per metronome click",
                                                   f"native: {module['printed_pulse_description']}"],
                                 "selected_pulse": None},
                      "rubric": None, "resource_requirements": [],
                      "ambiguities": ["Pulse mode, quarter-note onsets/durations and absolute BPM are unassigned.",
                                      "Optional module-boundary pause/accent has no selected runtime binding.",
                                      "Printed practice log is blank; no performed result exists."],
                      "control_scope": {"local_case": f"Level20 rung{rung_index:02d} module{module_index} {title}",
                                        "extent": "complete_selected_case", "whole_workbook_complete": False,
                                        "source_event_count": count, "basis_refs": refs,
                                        "unresolved": ["Identity, lineage and circuit-level admission pending."]},
                      "variants": variants, "lineage": None}
            need(set(fields) == FIELDS, "FIELD_SHAPE")
            records.append({"source_local_key": local, "rung_number": rung_index, "module_number": module_index,
                            "key": key, "root_fret": root_fret, "frame": [root_fret - 1, root_fret + 2],
                            "schema1_fields": fields, "group_memberships": groups,
                            "variant_memberships": memberships,
                            "source_printed_rows": module["source_rows"],
                            "source_heading": module["printed_heading"],
                            "source_boundary_instruction": module["printed_boundary_instruction"],
                            "identity_state": "unallocated", "schema1_importable": False,
                            "open_gaps": ["canonical identities and lineage", "pulse/timing and pause binding",
                                          "runtime/Curriculum admission"]})
            source_map.append({"source_local_key": local, "rung_number": rung_index,
                               "module_number": module_index, "key": key,
                               "txt": span, "pdf_page": pdf_ref, "contact_count": count,
                               "circuit_ordinals": [running + 1, running + count]})
            keys.append(local)
            boundaries.append({"module_number": module_index, "first_circuit_contact": running + 1,
                               "last_circuit_contact": running + count})
            running += count
        need(running == 322 and [b["last_circuit_contact"] for b in boundaries] ==
             [30, 108, 204, 256, 322], "CIRCUIT_BOUNDARIES")
        circuits.append({"rung_number": rung_index, "key": key, "root_fret": root_fret,
                         "module_keys": keys, "module_boundaries": boundaries,
                         "source_rung_heading_line": rung["txt_heading_line"],
                         "source_pdf_pages": rung["pdf_pages"],
                         "source_native_beats": 113, "selected_timing": None})
    route = candidate["printed_guidance"]
    need(route["route_rung_indices"] == list(range(1, 14)) + list(range(12, 0, -1)) and
         route["route_printed_note_count"] == 8050 and route["route_printed_beat_count"] == 2825 and
         route["native_beats_per_circuit"] == 113 and route["practice_log_values"] is None,
         "ROUTE_SCOPE")
    up = [f"L20-rung{i:02d}" for i in range(1, 14)]
    down = [f"L20-rung{i:02d}" for i in range(12, 0, -1)]
    counts = {"rungs": 13, "records": 65, "modules": 65, "groups": 1287,
              "events": 4186, "variants": 130,
              "continuous_round_trip_circuits": 25, "round_trip_contact_traversals": 8050,
              "source_native_beats_per_circuit": 113, "source_native_beats_per_route": 2825}
    proposal = {"proposal_version": "parallel12-level020-unallocated-schema1-fields.1",
                "classification": "source_mapped_field_proposal_not_schema1_importable",
                "legacy_level": 20,
                "source_pins": {str(path): {"bytes": (root / path).stat().st_size, "sha256": digest}
                                for path, (_, digest) in PINS.items()},
                "counts": counts, "source_guidance": route,
                "source_exceptions": candidate["source_exceptions"],
                "current659_level20_records": 0, "current659_level20_workbook_identity": False,
                "representative_collision": None,
                "canonical_ids_allocated": False, "runtime_eligible": False, "admitted": False,
                "fixed_bpm": None, "note_per_click": None, "onset_q": None, "duration_q": None,
                "circuits": circuits, "records": records}
    handoff = {"version": "parallel12-level020-allocation-handoff.1",
               "status": "pending_P02_serial_floor_and_allocation_authority",
               "proposal_sha256": sha(encode(proposal)), "source_map": source_map,
               "guidance_refs": GUIDANCE_REFS,
               "routes": {"up_rungs": up, "down_return_rungs": down,
                          "continuous_round_trip": up + down, "turn_after_rung": "L20-rung13",
                          "module_order_per_circuit": [1, 2, 3, 4, 5],
                          "shift_frets_up": 1, "shift_frets_down": -1},
               "rung_count": 13, "record_count": 65, "group_count": 1287,
               "event_count": 4186, "variant_count": 130,
               "current659_level20_records": 0, "current659_level20_workbook_identity": False,
               "representative_collision": None,
               "decisions_required": ["P02 serial floor, workbook/module/item/variant identity and source-key bridge",
                                      "Curriculum review of five-module sequence, repeated roots and 25-circuit route",
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
    counts = {"rungs": 13, "records": 65, "modules": 65, "groups": 1287,
              "events": 4186, "variants": 130,
              "continuous_round_trip_circuits": 25, "round_trip_contact_traversals": 8050,
              "source_native_beats_per_circuit": 113, "source_native_beats_per_route": 2825}
    need(proposal["counts"] == counts and
         (handoff["rung_count"], handoff["record_count"], handoff["group_count"],
          handoff["event_count"], handoff["variant_count"]) == (13, 65, 1287, 4186, 130), "COVERAGE")
    up = [f"L20-rung{i:02d}" for i in range(1, 14)]
    down = [f"L20-rung{i:02d}" for i in range(12, 0, -1)]
    need(handoff["routes"]["up_rungs"] == up and handoff["routes"]["down_return_rungs"] == down and
         handoff["routes"]["continuous_round_trip"] == up + down and
         handoff["routes"]["turn_after_rung"] == "L20-rung13" and
         handoff["routes"]["module_order_per_circuit"] == [1, 2, 3, 4, 5], "ROUTE_OR_CASE_ORDER")
    expected_keys = [f"L20-rung{r:02d}-module{m}" for r in range(1, 14) for m in range(1, 6)]
    need([r["source_local_key"] for r in proposal["records"]] == expected_keys and
         [r["source_local_key"] for r in handoff["source_map"]] == expected_keys and
         [c["module_keys"] for c in proposal["circuits"]] ==
         [expected_keys[i:i + 5] for i in range(0, 65, 5)], "MODULE_ORDER")
    for record in proposal["records"]:
        fields = record["schema1_fields"]
        module_index, rung_index = record["module_number"], record["rung_number"]
        count, group_count = MODULE_COUNTS[module_index - 1], MODULE_GROUPS[module_index - 1]
        need(record["key"] == p05.KEYS[rung_index - 1] and record["root_fret"] == rung_index + 4 and
             record["identity_state"] == "unallocated" and record["schema1_importable"] is False and
             set(fields) == FIELDS and fields["legacy_level"] == 20 and
             fields["context"]["local_code"] == record["source_local_key"] and
             all(fields[k] is None for k in ("id", "workbook_id", "module_id", "content_revision", "lineage")) and
             fields["runtime_eligible"] is False and fields["timing"]["status"] == "unresolved" and
             fields["timing"]["selected_pulse"] is None, "INVALID_AUTHORITY")
        need(len(fields["events"]) == count and len(record["group_memberships"]) == group_count and
             len(fields["variants"]) == len(record["variant_memberships"]) == 2, "MODULE_COUNT")
        need([n for group in record["group_memberships"] for n in group["event_local_ordinals"]] ==
             list(range(1, count + 1)), "GROUP_MEMBERSHIP")
        for event in fields["events"]:
            need(event["event_id"] is event["onset_q"] is event["duration_q"] is None and
                 event["kind"] == "note" and 1 <= event["string"] <= 6 and
                 event["midi"] == [40, 45, 50, 55, 59, 64][event["string"] - 1] + event["fret"] and
                 event["midi"] % 12 == p05._name_pc(event["spelling"]) and
                 1 <= event["finger"] <= 4, "UNSUPPORTED_TIMING_OR_NOTE")
        need([v["pick_start"] for v in fields["variants"]] == ["D", "U"] and
             all(v["id"] is v["event_ids"] is None and v["grouping"]["kind"] == "unresolved" and
                 v["grouping"]["beat_unit_q"] is None for v in fields["variants"]) and
             all(m["event_local_ordinals"] == list(range(1, count + 1)) and
                 m["group_indices"] == list(range(1, group_count + 1))
                 for m in record["variant_memberships"]), "VARIANT_MEMBERSHIP")
    need(handoff["proposal_sha256"] == sha(encode(proposal)) and
         proposal["current659_level20_records"] == handoff["current659_level20_records"] == 0 and
         proposal["current659_level20_workbook_identity"] is handoff["current659_level20_workbook_identity"] is False and
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
    print(json.dumps({"status": "unallocated_level020_pending_P02_serial_floor",
                      "counts": verify(proposal, handoff)}, sort_keys=True))


if __name__ == "__main__":
    main()
