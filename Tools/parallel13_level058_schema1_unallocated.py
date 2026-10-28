#!/usr/bin/env python3
"""Project sealed Level58 rhythm masks into unallocated schema1-shaped fields."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path

import curriculum_level058_masks_candidate as narrow
import curriculum_level058_whole_rhythm_candidate as whole


ROOT = Path(__file__).resolve().parents[1]
OUT = Path("Build/parallel-13/level058-schema1-unallocated-r01")
WHOLE = Path("Build/parallel-05/2.3.1.2.1-level058-whole-r01/candidate-c.json")
NARROW = Path("Build/parallel-01/2.3-level058-masks-r01/candidate.json")
FOUNDATION = Path("Content/controls/curriculum-v1/package.json")
PINS = {
    WHOLE: "3f5d605c7f21da45584f988f0ffe17f444677542f66c6a4ab3fa81edb237dc91",
    NARROW: "361efe5129ac29b4420ca9166b9e436c9874412c1f98fef76a9459e4c69a93f5",
    FOUNDATION: "766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255",
    Path("Results/primary/20260912T100538Z-2.1.1.2.1-r02-evidence/schema-freeze.json"): "0659fa962a5c933a2bcf3045772b6fe5b05b4deefb3511f5dcb68af51088de95",
    Path("Tools/curriculum_level058_whole_rhythm_candidate.py"): "2c35f86db5712967cbf247fbf39d700dec91fbb9b0cd8164ecc194bbc07d2a81",
    Path("Tools/curriculum_level058_masks_candidate.py"): "f452bc98d70dc24901f0f8e7e1833d7df2d4c3facd4c945dc29d278cded886d8",
    Path("Results/parallel-05/exercises/conversion/20260923T161400Z-2.3.1.2.1-level058-whole-rhythm-r01-results.md"): "9674cf0bdcb245aac4a191aa3ea93e35beb5891f5e8d18ad6428f08bbf83b1bb",
    Path("Results/parallel-01/exercises/conversion/20260923T112002Z-2.3.1.2.1-level058-modulea-masks-r02-results.md"): "988391e95a7a6bbe1e415074c6ff629bc4f921673e897a8615b961766e1cf5e9",
    Path(whole.TXT_REL): whole.TXT_SHA,
    Path(whole.PDF_REL): whole.PDF_SHA,
    Path(whole.MAP_REL): whole.MAP_SHA,
}
UNRESOLVED = [
    "canonical workbook/module/item/event/variant IDs, lineage and revision",
    "chosen pitch and voicing for P contacts; x contacts are unpitched",
    "fixed BPM, absolute onset/duration, beat mapping and note-per-click",
    "H source conflict: 116 exact-mask versus 128 headline contacts",
    "E9-E12 chord-pair selection and D accent alternatives",
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
    rep = [r for r in package["records"] if r.get("legacy_level") == 58]
    entry = [e for e in package["workbook_catalog"]["entries"]
             if e["workbook_id"] == "fg:workbook:000058"]
    need(len(package["records"]) == 659 and len(rep) == len(entry) == 1 and
         rep[0]["id"] == entry[0]["representative_item_id"] == "fg:item:000009" and
         rep[0]["runtime_eligible"] is False and
         entry[0]["conversion_status"] == "not_converted" and
         entry[0]["whole_workbook_complete"] is False and
         all(entry[0][k] is False for k in
             ("admitted", "imported", "runtime_admitted", "runtime_eligible")),
         "FOUNDATION_ADMISSION")


def narrow_parity(candidate: dict, narrow_candidate: dict) -> None:
    records = narrow_candidate["records"]
    units = candidate["modules"]["A"]["units"]
    need(len(records) == len(units) == 15, "A_UNIT_COUNT")
    for index, (record, unit) in enumerate(zip(records, units, strict=True), 1):
        slots = unit["slots"]
        mask = "".join(s["sound_symbol"] for s in slots)
        hand = "".join(s["right_hand_path"] for s in slots)
        need(record["label_source"] == f"A{index}" and
             mask == record["sound_mask_bar_source"] and
             hand == record["hand_stroke_bar_source"] and
             unit["contact_count"] == record["txt_contacts_per_bar_source"] ==
             record["pdf_bottom_contacts_count"], f"A_PARITY {index}")


def project(candidate: dict, narrow_candidate: dict) -> tuple[dict, dict]:
    need(candidate["schema"] == "fathom.detached-source-candidate.1" and
         candidate["level"] == 58 and candidate["wbs_id"] == "2.3.1.2.1" and
         candidate["module_count"] == 9 and
         set(candidate["modules"]) == set(whole.MODULE_UNITS) and
         candidate["printed_total_contact_count"] == 1018 and
         candidate["mask_derived_total_contact_count"] == 1018 and
         candidate["raw_caption_total_contact_count"] == 1030 and
         candidate["H_mask_derived_count"] == 116 and
         candidate["H_printed_headline_count"] == 128 and
         candidate["canonical_ids"] is None and candidate["review"] == "Pending" and
         all(candidate[k] is False for k in
             ("runtime_eligible", "imported", "admitted")) and
         all(candidate[k] is None for k in
             ("performed_onset", "performed_duration", "performed_bpm", "performed_mastery")),
         "SOURCE_SCOPE")
    src = candidate["source"]
    need(src["txt_sha256"] == PINS[Path(whole.TXT_REL)] and
         src["pdf_sha256"] == PINS[Path(whole.PDF_REL)] and
         src["source_map_sha256"] == PINS[Path(whole.MAP_REL)] and
         src["source_map_row"]["representative_item_id"] == "fg:item:000009" and
         src["source_map_row"]["admitted"] is False,
         "SOURCE_LINEAGE")
    narrow_parity(candidate, narrow_candidate)
    need({e["code"] for e in candidate["source_exceptions"]} ==
         {"H_COUNT_CONFLICT", "D_PDF_ACCENT_ROW",
          "PDF_ONLY_PROTOCOL_AND_CAPSTONE_REPAIR", "E_PUSH_PAIR_UNSPECIFIED",
          "TXT_PDF_LAYOUT_AND_PALETTE"} and
         all(e["status"] == "Pending Curriculum review"
             for e in candidate["source_exceptions"]), "SOURCE_EXCEPTIONS")
    need(candidate["symbols"]["P"] == "pitched string contact" and
         candidate["symbols"]["x"] == "dead muted string contact" and
         len(candidate["reference_voicings"]) == 17 and
         candidate["printed_guidance"]["kind"] == "printed_instruction" and
         len(candidate["printed_guidance"]["pdf_extracted_pages"]) == 20,
         "SOURCE_GUIDANCE")

    records: list[dict] = []
    mapping: list[dict] = []
    module_counts: dict[str, dict] = {}
    for module, expected_units in whole.MODULE_UNITS.items():
        source_module = candidate["modules"][module]
        units = source_module["units"]
        need(len(units) == expected_units and
             source_module["mask_derived_contact_count"] == whole.MODULE_COUNTS[module],
             f"MODULE_SCOPE {module}")
        contacts = 0
        for index, unit in enumerate(units, 1):
            slots = unit["slots"]
            need(len(slots) > 0 and len(slots) % 16 == 0 and
                 isinstance(unit["txt_line"], int) and unit["txt_line"] > 0 and
                 unit["pdf_page"] in whole.MODULE_PAGES[module],
                 f"UNIT_SOURCE {module}{index}")
            events: list[dict] = []
            for slot_index, slot in enumerate(slots, 1):
                symbol = slot["sound_symbol"]
                need(symbol in "Px-~" and slot["right_hand_path"] in "DU" and
                     slot["bar_in_unit"] >= 1 and slot["beat"] in range(1, 5) and
                     slot["subdivision"] in ("number", "e", "&", "a") and
                     unit["txt_line"] <= slot["txt_line"] <= source_module["txt_end_line"] and
                     slot["pdf_page"] == unit["pdf_page"] and
                     all(slot[k] is None for k in
                         ("performed_onset", "performed_duration", "performed_bpm",
                          "performed_quality")), f"SLOT_SOURCE {module}{index}:{slot_index}")
                expected_kind = {"P": "pitched contact", "x": "dead contact",
                                 "-": "silent air stroke",
                                 "~": "tie/sustain no new contact"}[symbol]
                need(slot["kind"] == expected_kind and
                     not (slot["left_pressure_release"] and symbol in "P~"),
                     f"SLOT_SEMANTIC {module}{index}:{slot_index}")
                if symbol not in "Px":
                    continue
                events.append({
                    "source_local_ordinal": len(events) + 1,
                    "source_slot_ordinal": slot_index,
                    "schema1_fields": {"event_id": None,
                                       "kind": ("pitched_chord_contact_voicing_unresolved"
                                                if symbol == "P" else "dead_muted_contact"),
                                       "onset_q": None, "duration_q": None,
                                       "midi": None, "string": None, "fret": None},
                    "source_attack": {"sound_symbol": symbol,
                                      "bar_in_unit": slot["bar_in_unit"],
                                      "beat": slot["beat"],
                                      "subdivision": slot["subdivision"],
                                      "printed_count": slot["printed_count"],
                                      "right_hand_path": slot["right_hand_path"],
                                      "chord_symbol": slot["chord"],
                                      "left_pressure_release": slot["left_pressure_release"],
                                      "txt_line": slot["txt_line"],
                                      "pdf_page": slot["pdf_page"]},
                    "pitch_binding": ("unresolved_voicing_choice" if symbol == "P"
                                      else "unpitched_dead_contact"),
                })
            expected_counts = {"P": unit["pitched_count"],
                               "x": unit["dead_count"],
                               "-": unit["air_count"],
                               "~": unit["tie_count"]}
            need(all(sum(s["sound_symbol"] == sym for s in slots) == count
                     for sym, count in expected_counts.items()) and
                 sum(s["left_pressure_release"] for s in slots) == unit["release_count"] and
                 len(events) == unit["contact_count"] and
                 (module != "H" or unit["printed_contact_count"] == 32),
                 f"UNIT_CONTACTS {module}{index}")
            contacts += len(events)
            key = f"L58-{module}-{index:02d}"
            refs = {"txt_path": src["txt_path"], "txt_line": unit["txt_line"],
                    "pdf_path": src["pdf_path"], "pdf_page": unit["pdf_page"],
                    "source_candidate_sha256": PINS[WHOLE]}
            payload = {"source_local_key": key, "identity_state": "unallocated",
                       "source_unit_sha256": sha(encoded(unit)),
                       "source_unit": copy.deepcopy(unit), "source_provenance": refs,
                       "schema1_fields": {"id": None, "workbook_id": None,
                                          "module_id": None, "lineage": None,
                                          "content_revision": None, "legacy_level": 58,
                                          "title": unit.get("label", unit.get("section")),
                                          "kind": "rhythm_mask_contacts",
                                          "runtime_eligible": False,
                                          "source_refs": [f"L58-TXT-{unit['txt_line']}",
                                                          f"L58-PDF-p{unit['pdf_page']}"],
                                          "events": events, "variants": [],
                                          "timing": {"status": "absolute_unresolved",
                                                     "printed_subdivision": "1-e-&-a",
                                                     "onset_q": None,
                                                     "duration_q": None,
                                                     "fixed_bpm": None,
                                                     "note_per_click": None},
                                          "resource_requirements": [],
                                          "ambiguities": UNRESOLVED}}
            records.append(payload)
            mapping.append({"source_local_key": key,
                            "source_unit_sha256": payload["source_unit_sha256"],
                            "module": module, "unit": index,
                            "contact_events": len(events),
                            "pitched_contacts": unit["pitched_count"],
                            "dead_contacts": unit["dead_count"],
                            "silent_or_tied_slots": unit["air_count"] + unit["tie_count"],
                            "txt_line": unit["txt_line"], "pdf_page": unit["pdf_page"]})
        need(contacts == whole.MODULE_COUNTS[module], f"MODULE_CONTACTS {module}")
        module_counts[module] = {"units": len(units), "contact_events": contacts}
    need(len(records) == 74 and sum(x["contact_events"] for x in module_counts.values()) == 1018,
         "WHOLE_COUNTS")
    h = candidate["modules"]["H"]["units"]
    need([u["contact_count"] for u in h] == [32, 24, 32, 28] and
         [u["printed_contact_count"] for u in h] == [32] * 4,
         "H_CONFLICT")
    capstone = candidate["modules"]["I"]["units"]
    need([(u["first_bar"], u["last_bar"]) for u in capstone] ==
         [(1, 4), (5, 12), (13, 16), (17, 24), (25, 28), (29, 31), (32, 32)] and
         sum(u["contact_count"] for u in capstone) == 209 and
         all(u["pair"] is None for u in candidate["modules"]["E"]["units"][8:]),
         "CAPSTONE_AND_PUSH")
    proposal = {"schema": "fathom-level058-schema1-field-proposal.1",
                "classification": "build_only_unallocated_nonimportable",
                "wbs_id": "2.3.1.2.1", "legacy_level": 58,
                "source_candidate_sha256": PINS[WHOLE],
                "narrow_module_a_candidate_sha256": PINS[NARROW],
                "source": copy.deepcopy(src),
                "symbols": copy.deepcopy(candidate["symbols"]),
                "reference_voicings": copy.deepcopy(candidate["reference_voicings"]),
                "printed_guidance": copy.deepcopy(candidate["printed_guidance"]),
                "source_exceptions": copy.deepcopy(candidate["source_exceptions"]),
                "pending": copy.deepcopy(candidate["pending"]),
                "module_counts": module_counts, "records": records,
                "H_printed_headline_count": 128, "H_mask_derived_count": 116,
                "printed_total_contact_count": 1018,
                "raw_caption_total_contact_count": 1030,
                "canonical_ids_allocated": False, "runtime_eligible": False,
                "admitted": False, "whole_workbook_complete": False,
                "timing_resolved": False, "curriculum_signoff": False}
    handoff = {"schema": "fathom-level058-schema1-allocation-handoff.1",
               "field_proposal_sha256": sha(encoded(proposal)),
               "source_candidate_sha256": PINS[WHOLE],
               "narrow_module_a_candidate_sha256": PINS[NARROW],
               "records": mapping, "module_counts": module_counts,
               "H_conflict": {"mask_contacts": 116, "printed_headline_contacts": 128,
                              "raw_caption_workbook_sum": 1030,
                              "status": "Pending Curriculum review"},
               "unresolved": UNRESOLVED,
               "next_step": "independent source/music review before ID allocation or import",
               "admitted": False, "runtime_eligible": False,
               "whole_workbook_complete": False}
    return proposal, handoff


def derive() -> tuple[dict, dict]:
    pins()
    foundation_status()
    sealed = json.loads((ROOT / WHOLE).read_text())
    narrow_sealed = json.loads((ROOT / NARROW).read_text())
    need(sealed == whole.build_candidate(ROOT), "P05_REPLAY_DRIFT")
    need(narrow_sealed == narrow.build_candidate(root=ROOT), "P01_REPLAY_DRIFT")
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
                      "units": len(proposal["records"]),
                      "contact_events": 1018,
                      "H_mask_contacts": 116,
                      "H_printed_headline": 128,
                      "field_proposal_sha256": sha(files["field-proposal.json"]),
                      "handoff_sha256": sha(files["allocation-handoff.json"])},
                     sort_keys=True))


if __name__ == "__main__":
    main()
