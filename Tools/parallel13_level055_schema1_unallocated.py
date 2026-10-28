#!/usr/bin/env python3
"""Project sealed whole-Level55 harmony source into unallocated schema1 fields."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path

import curriculum_level055_whole_candidate as source


ROOT = Path(__file__).resolve().parents[1]
OUT = Path("Build/parallel-13/level055-schema1-unallocated-r01")
CANDIDATE = Path("Build/parallel-09/2.3.1.2.1-level055-whole-r01/level055-whole-candidate-01.json")
RESULT = Path("Results/parallel-09/exercises/conversion/20260923T161327Z-2.3.1.2.1-level055-whole-r01-results.md")
SCHEMA = Path("Results/primary/20260912T100538Z-2.1.1.2.1-r02-evidence/schema-freeze.json")
FOUNDATION = Path("Content/controls/curriculum-v1/package.json")
PINS = {
    CANDIDATE: "9dd264bee8f64a1d7047905b4be5655575beabff778562758406a3d2c79970ec",
    RESULT: "173f87d75d52d43cc2d66667893b9e2b027ac98a73b7dfb01761c641668c1a1a",
    SCHEMA: "0659fa962a5c933a2bcf3045772b6fe5b05b4deefb3511f5dcb68af51088de95",
    FOUNDATION: "766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255",
    source.TXT_REL: source.TXT_SHA,
    source.PDF_REL: source.PDF_SHA,
    Path("Tools/curriculum_level055_whole_candidate.py"): "848b64ce08b4efc60f8bfd41c1cd5b81bab2c18e9d38e80615f404eae7c52682",
}
ITEMS = {"A": 42, "B": 42, "C": 6, "D": 6, "E": 6, "F": 6,
         "G": 6, "H": 6, "I": 6, "J": 24, "K": 6}
ATTACKS = source.ATTACKS
UNRESOLVED = ["canonical workbook/module/item/event/variant IDs, lineage and revision",
              "fixed BPM, beat mapping, note-per-click and onset/duration",
              "chosen chord voicing and pitch for C-H/K progression attacks",
              "I low/middle/top alternate voice-path selection",
              "Curriculum review, performed mastery and runtime admission"]


class ProposalError(ValueError):
    pass


def need(ok: bool, code: str) -> None:
    if not ok:
        raise ProposalError(code)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def encoded(obj: object) -> bytes:
    return (json.dumps(obj, sort_keys=True, ensure_ascii=False,
                       separators=(",", ":")) + "\n").encode()


def pin() -> None:
    for rel, expected in PINS.items():
        p = ROOT / rel
        need(p.is_file() and not p.is_symlink() and
             p.resolve().is_relative_to(ROOT.resolve()), f"INPUT_PATH {rel}")
        need(sha(p.read_bytes()) == expected, f"INPUT_PIN {rel}")


def foundation_status() -> None:
    pkg = json.loads((ROOT / FOUNDATION).read_text())
    need(len(pkg["records"]) == 659 and
         not any(r.get("legacy_level") == 55 for r in pkg["records"]),
         "FOUNDATION_RECORD")
    entries = [e for e in pkg["workbook_catalog"]["entries"]
               if e["workbook_id"] == "fg:workbook:000055"]
    need(len(entries) == 1 and entries[0]["conversion_status"] == "not_converted" and
         entries[0]["representative_item_id"] is None and
         entries[0]["whole_workbook_complete"] is False and
         all(entries[0][k] is False for k in
             ("admitted", "imported", "runtime_admitted", "runtime_eligible")),
         "CATALOG_ADMISSION")


def triad_contacts(strings: list[str], frets: list[int],
                   spelling: list[str] | None = None) -> list[dict]:
    need(len(strings) == len(frets) == 3 and len(set(strings)) == 3,
         "TRIAD_CONTACT_COUNT")
    out = []
    for string, fret in zip(strings, frets, strict=True):
        need(string in source.OPEN and isinstance(fret, int) and 0 <= fret <= 24,
             "TRIAD_CONTACT")
        midi = source.OPEN[string] + fret
        out.append({"string": string, "fret": fret, "midi": midi,
                    "pitch_class": midi % 12,
                    "printed_note": None})
    if spelling is not None:
        need(len(spelling) == 3 and all(n in source.PC for n in spelling) and
             sorted(m["pitch_class"] for m in out) ==
             sorted(source.PC[n] for n in spelling), "TRIAD_PITCH")
    return out


def event(kind: str, contacts: list[dict], module: str, item: int,
          ordinal: int, provenance: dict, **meaning: object) -> dict:
    one = contacts[0] if len(contacts) == 1 else None
    return {"source_local_ordinal": ordinal,
            "schema1_fields": {"event_id": None, "kind": kind,
                               "onset_q": None, "duration_q": None,
                               "midi": one["midi"] if one else None,
                               "string": one["string"] if one else None,
                               "fret": one["fret"] if one else None},
            "sounding_members": contacts,
            "pitch_binding": "source_contact" if contacts else "unresolved_voicing_choice",
            "source_attack": {"module": module, "item": item,
                              "sounded": True, "txt_line": provenance["txt_line"],
                              "pdf_page": provenance["pdf_page"],
                              "kind": kind, **meaning}}


def provenance(module: str, row: dict, parent: dict | None = None) -> dict:
    outer = parent or row
    line = row.get("txt_line", outer.get("txt_line", source.MODULE_LINE[module]))
    page = row.get("pdf_page", outer.get("pdf_page", source.PDF_PAGES[module][0]))
    need(isinstance(line, int) and 1 <= line <= 530 and
         isinstance(page, int) and page in source.PDF_PAGES[module], "SOURCE_PROVENANCE")
    return {"txt_path": str(source.TXT_REL), "txt_line": line,
            "pdf_path": str(source.PDF_REL), "pdf_page": page,
            "source_candidate_sha256": PINS[CANDIDATE]}


def triad_attacks(contacts: list[dict], module: str, index: int,
                  ref: dict, meaning: dict) -> list[dict]:
    return [event("blocked_triad", contacts, module, index, 1, ref, **meaning)] + [
        event("picked_triad_note", [member], module, index, i + 2, ref,
              **meaning) for i, member in enumerate(contacts)]


def project(candidate: dict) -> tuple[dict, dict]:
    need(candidate["schema"] == "fathom-level055-whole-detached-candidate-v1" and
         candidate["level"] == 55 and candidate["wbs_id"] == "2.3.1.2.1" and
         candidate["complete_sounded_workout_attacks"] == 936 and
         candidate["silent_spelling_formation_prompts"] == 42 and
         candidate["written_analysis_transposition_prompts"] == 24 and
         candidate["module_sounded_attacks"] == ATTACKS and
         set(candidate["modules"]) == set(ITEMS) and
         all(candidate[k] is None for k in
             ("canonical_item_id", "canonical_variant_id", "fixed_bpm",
              "note_per_click", "onset_q", "duration_q", "performed_result")) and
         all(candidate[k] is False for k in
             ("runtime_eligible", "runtime_admitted", "imported", "admitted",
              "curriculum_signoff")), "SOURCE_SCOPE")
    need(candidate["source"]["txt_sha256"] == PINS[source.TXT_REL] and
         candidate["source"]["pdf_sha256"] == PINS[source.PDF_REL] and
         candidate["pdf_reconciliation"]["discrepancies"] == [] and
         candidate["pdf_reconciliation"]["pages"] == 20 and
         candidate["pdf_reconciliation"]["checked_items"] == ITEMS,
         "SOURCE_RECONCILIATION")
    a_foundation = candidate["modules"]["A"]
    need(a_foundation["circle_order"] == list(source.KEYS) and
         set(a_foundation["key_scales"]) == set(source.SCALE) and
         all(a_foundation["key_scales"][key] == source.SCALE[key]
             for key in source.SCALE), "KEY_SCALE_FOUNDATION")
    records, mapping, counts = [], [], {}
    for module in ITEMS:
        if module == "A":
            rows = candidate["modules"]["A"]["silent_prompts"]
        elif module == "B":
            rows = [(key, degree) for key in candidate["modules"]["B"]
                    for degree in key["degrees"]]
        elif module == "J":
            rows = ([{"written_kind": "analysis", **x} for x in candidate["modules"]["J"]["analysis"]] +
                    [{"written_kind": "transposition", **x}
                     for x in candidate["modules"]["J"]["transposition"]])
        else:
            rows = candidate["modules"][module]
        need(len(rows) == ITEMS[module], f"ITEM_COUNT {module}")
        sounded = silent = written = 0
        for index, entry in enumerate(rows, 1):
            parent, row = entry if module == "B" else (None, entry)
            ref = provenance(module, row, parent)
            attacks: list[dict] = []
            context: dict = {}
            if module == "A":
                need(row["sounded_attacks"] == 0 and
                     row["onset_q"] is None and row["duration_q"] is None,
                     "A_SILENT_ONLY")
                silent += 1
            elif module == "B":
                need(row["blocked_plus_arpeggio_attacks"] == 4 and
                     row["onset_q"] is None and row["duration_q"] is None and
                     row["roman"] == source.ROMAN[row["degree"] - 1] and
                     row["quality"] == source.QUALITY[row["degree"] - 1],
                     "B_TRIAD_SOURCE")
                contacts = triad_contacts(row["string_set"], row["frets"], row["spelling"])
                meaning = {"key": parent["key"], "roman": row["roman"],
                           "chord": row["chord"], "quality": row["quality"],
                           "function": row["function"]}
                attacks = triad_attacks(contacts, module, index, ref, meaning)
                context = {"key": parent["key"], "rhythm_voicing_alternatives":
                           row["rhythm_voicing_alternatives"]}
            elif module == "I":
                need(len(row["bars"]) == 4 and row["attack_count"] == 16 and
                     set(row["voice_frets"]) == {"low", "middle", "top"} and
                     all(len(path) == 4 for path in row["voice_frets"].values()),
                     "I_VOICE_PATHS")
                for bar in row["bars"]:
                    need(bar["blocked_plus_arpeggio_attacks"] == 4 and
                         bar["onset_q"] is None and bar["duration_q"] is None,
                         "I_BAR_COUNT")
                    contacts = triad_contacts(bar["string_set"], bar["frets"])
                    batch = triad_attacks(contacts, module, index, ref,
                                          {"key": row["key"], "bar": bar["bar"],
                                           "chord": bar["chord"], "roman": bar["roman"],
                                           "inversion": bar["inversion"]})
                    for x in batch:
                        x["source_local_ordinal"] = len(attacks) + 1
                        attacks.append(x)
                context = {"unselected_voice_fret_paths": row["voice_frets"]}
            elif module == "J":
                need(row["written_kind"] in ("analysis", "transposition"),
                     "J_WRITTEN")
                written += 1
            else:
                need(module in "CDEFGHK" and len(row["bars"]) == 4 and
                     row["attack_count"] == 16, "PROGRESSION_SHAPE")
                for bar in row["bars"]:
                    need(bar["sounded_attacks"] == 4 and bar["onset_q"] is None and
                         bar["duration_q"] is None and
                         isinstance(bar["rhythm_voicing_alternatives"], list),
                         "PROGRESSION_BAR")
                    if module in "CDEFGH":
                        need(bar["roman"] == source.PROGRESSION_ROMAN[module][bar["bar"] - 1],
                             "PROGRESSION_ROMAN")
                    for _ in range(4):
                        attacks.append(event("chord_attack_voicing_unresolved", [], module,
                                             index, len(attacks) + 1, ref,
                                             key=row["key"], bar=bar["bar"],
                                             roman=bar["roman"], chord=bar["chord"],
                                             function=bar["function"],
                                             rhythm_voicing_alternatives=
                                             bar["rhythm_voicing_alternatives"]))
            sounded += len(attacks)
            key = f"L55-{module}-{index:02d}"
            payload = {"source_local_key": key, "identity_state": "unallocated",
                       "source_item_sha256": sha(encoded(row)),
                       "source_item": copy.deepcopy(row),
                       "source_context": context, "source_provenance": ref,
                       "silent_prompt": copy.deepcopy(row) if module == "A" else None,
                       "written_prompt": copy.deepcopy(row) if module == "J" else None,
                       "schema1_fields": {"id": None, "workbook_id": None,
                                          "module_id": None, "lineage": None,
                                          "content_revision": None, "legacy_level": 55,
                                          "title": f"Level 55 module {module} item {index}",
                                          "kind": ("silent_formation" if module == "A" else
                                                   "written_harmony" if module == "J" else
                                                   "harmony_attack"),
                                          "runtime_eligible": False,
                                          "source_refs": [f"L55-TXT1-{ref['txt_line']}",
                                                          f"L55-PDF1-p{ref['pdf_page']}"],
                                          "events": attacks, "variants": [],
                                          "timing": {"status": "unresolved", "unit": "quarter",
                                                     "onset_q": None, "duration_q": None,
                                                     "fixed_bpm": None, "note_per_click": None},
                                          "resource_requirements": [],
                                          "ambiguities": UNRESOLVED}}
            records.append(payload)
            mapping.append({"source_local_key": key,
                            "source_item_sha256": payload["source_item_sha256"],
                            "module": module, "item": index,
                            "sounded_attacks": len(attacks),
                            "silent_prompts": 1 if module == "A" else 0,
                            "written_prompts": 1 if module == "J" else 0,
                            "txt_line": ref["txt_line"], "pdf_page": ref["pdf_page"]})
        need(sounded == ATTACKS[module], f"MODULE_ATTACKS {module}")
        counts[module] = {"items": len(rows), "sounded_attacks": sounded,
                          "silent_prompts": silent, "written_prompts": written}
    need(len(records) == 156 and
         sum(x["sounded_attacks"] for x in counts.values()) == 936 and
         sum(x["silent_prompts"] for x in counts.values()) == 42 and
         sum(x["written_prompts"] for x in counts.values()) == 24,
         "WHOLE_COUNTS")
    proposal = {"schema": "fathom-level055-schema1-field-proposal.1",
                "classification": "build_only_unallocated_nonimportable",
                "wbs_id": "2.3.1.2.1", "legacy_level": 55,
                "source_candidate_sha256": PINS[CANDIDATE],
                "source": candidate["source"], "source_instructions": candidate["instructions"],
                "key_foundation": {"circle_order": a_foundation["circle_order"],
                                   "key_scales": a_foundation["key_scales"],
                                   "instructions": a_foundation["instructions"]},
                "pdf_only": {"module_pages": candidate["pdf_reconciliation"]["module_pages"],
                             "extracted_page_text": candidate["pdf_reconciliation"]["extracted_page_text"],
                             "limitation": "PDF text is search metadata; P09 visually reviewed original pages."},
                "module_counts": counts, "records": records,
                "canonical_ids_allocated": False, "runtime_eligible": False,
                "admitted": False, "whole_workbook_complete": False,
                "timing_resolved": False, "curriculum_signoff": False}
    handoff = {"schema": "fathom-level055-schema1-allocation-handoff.1",
               "field_proposal_sha256": sha(encoded(proposal)),
               "source_candidate_sha256": PINS[CANDIDATE],
               "records": mapping, "module_counts": counts,
               "unresolved": UNRESOLVED,
               "next_step": "independent source/music review before ID allocation or import",
               "admitted": False, "runtime_eligible": False,
               "whole_workbook_complete": False}
    return proposal, handoff


def derive() -> tuple[dict, dict]:
    pin()
    foundation_status()
    sealed = json.loads((ROOT / CANDIDATE).read_text())
    need(sealed == source.build_candidate(), "P09_REPLAY_DRIFT")
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
                      "items": len(proposal["records"]), "sounded_attacks": 936,
                      "silent_prompts": 42, "written_prompts": 24,
                      "field_proposal_sha256": sha(files["field-proposal.json"]),
                      "handoff_sha256": sha(files["allocation-handoff.json"])}, sort_keys=True))


if __name__ == "__main__":
    main()
