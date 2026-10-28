#!/usr/bin/env python3
"""Project the sealed whole-Level54 CAGED source to unallocated schema1 fields."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import re

import curriculum_level054_whole_candidate as source


ROOT = Path(__file__).resolve().parents[1]
OUT = Path("Build/parallel-13/level054-schema1-unallocated-r01")
CANDIDATE = Path("Build/parallel-08/2.3.1.2.1-level054-whole-r01/level054-candidate-a.json")
RESULT = Path("Results/parallel-08/exercises/conversion/20260923T160418Z-2.3.1.2.1-level054-whole-candidate-r01-results.md")
SCHEMA = Path("Results/primary/20260912T100538Z-2.1.1.2.1-r02-evidence/schema-freeze.json")
FOUNDATION = Path("Content/controls/curriculum-v1/package.json")
PINS = {
    CANDIDATE: "24175aeed5bb71eb8a5186ef35fd7299b4f5ae00d23e2c0c34cc17e71f5a5b61",
    RESULT: "c9844e5b86a4d5d716746aaadca765ee0be93f0b17c7b5f78cbb9698e718adbd",
    SCHEMA: "0659fa962a5c933a2bcf3045772b6fe5b05b4deefb3511f5dcb68af51088de95",
    FOUNDATION: "766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255",
    source.TXT: source.PINS["txt"][1],
    source.PDF: source.PINS["pdf"][1],
    source.MAP: source.PINS["map"][1],
    Path("Tools/curriculum_level054_whole_candidate.py"): "6b8c0a22d362ee383fc692d7229ad82e36f39390fa3e2f6ae09468463ab993f8",
}
STRINGS = ("E", "A", "D", "G", "B", "e")
OPEN = {"E": 40, "A": 45, "D": 50, "G": 55, "B": 59, "e": 64}
COUNTS = {"A": 0, "B": 66, "C": 60, "D": 40, "E": 52,
          "F": 80, "G": 40, "H": 80, "I": 60, "J": 80}
ITEMS = {"A": 45, "B": 5, "C": 15, "D": 5, "E": 5,
         "F": 5, "G": 10, "H": 5, "I": 5, "J": 20}
UNRESOLVED = ["canonical workbook/module/item/event/variant IDs, lineage and revision",
              "absolute BPM, beat mapping and quarter-note onset/duration",
              "source-only practice passes and voice-audit counts outside the 558 attacks",
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
         not any(r.get("legacy_level") == 54 for r in pkg["records"]),
         "FOUNDATION_RECORD")
    rows = [x for x in pkg["workbook_catalog"]["entries"]
            if x["workbook_id"] == "fg:workbook:000054"]
    need(len(rows) == 1 and rows[0]["conversion_status"] == "not_converted" and
         rows[0]["representative_item_id"] is None and
         rows[0]["whole_workbook_complete"] is False and
         all(rows[0][k] is False for k in
             ("admitted", "imported", "runtime_admitted", "runtime_eligible")),
         "CATALOG_ADMISSION")


def contact(string: str, fret: int, note: str, degree: str | None = None,
            finger: int | None = None) -> dict:
    need(string in OPEN and isinstance(fret, int) and 0 <= fret <= 24 and
         note in source.PC and (OPEN[string] + fret) % 12 == source.PC[note],
         "PITCH_CONTACT")
    return {"string": string, "fret": fret, "finger": finger,
            "note": note, "degree": degree, "midi": OPEN[string] + fret}


def members(strings: list[str], frets: list, notes: list,
            degrees: list | None = None, fingers: list | None = None) -> list[dict]:
    need(len(strings) == len(frets) == len(notes) and
         (degrees is None or len(degrees) == len(strings)) and
         (fingers is None or len(fingers) == len(strings)), "CONTACT_SHAPE")
    output = []
    for i, (string, fret, note) in enumerate(zip(strings, frets, notes, strict=True)):
        if fret is None:
            need(note is None, "MUTED_CONTACT")
            continue
        output.append(contact(string, fret, note,
                              degrees[i] if degrees else None,
                              fingers[i] if fingers else None))
    return output


def form_members(form: dict) -> list[dict]:
    fingers = None
    if len(form["source_rows"]) == 5:
        raw = form["source_rows"][4]
        need(raw.startswith("Fng|"), "FINGER_ROW")
        values = re.findall(r"x|O|[1-4]", raw.split("|", 1)[1])
        need(len(values) == 6, "FINGER_COUNT")
        fingers = [None if x in ("x", "O") else int(x) for x in values]
    return members(form["strings"], form["frets"], form["notes"],
                   form.get("degrees"), fingers)


def triad_members(triad: dict) -> list[dict]:
    return members(triad["strings"], triad["frets"], triad["notes"],
                   triad.get("degrees"))


def attack(kind: str, contacts: list[dict], module: str, item: int,
           ordinal: int, span: dict, **extra: object) -> dict:
    need(bool(contacts), "SOUNDING_CONTACTS")
    single = contacts[0] if len(contacts) == 1 else None
    return {"source_local_ordinal": ordinal,
            "schema1_fields": {"event_id": None, "kind": kind,
                               "onset_q": None, "duration_q": None,
                               "midi": single["midi"] if single else None,
                               "string": single["string"] if single else None,
                               "fret": single["fret"] if single else None,
                               "finger": single["finger"] if single else None},
            "sounding_members": contacts,
            "source_attack": {"module": module, "item": item,
                              "kind": kind, "sounded": True,
                              "txt_module_span": span["txt_module_span"],
                              "pdf_pages": span["pdf_pages"], **extra}}


def module_span(lines: list[str], module: str) -> dict:
    starts = {k: lines.index(source.HEAD[k]) + 1 for k in COUNTS}
    first = starts[module]
    following = [n for n in starts.values() if n > first]
    last = min(following) - 1 if following else len(lines)
    need(1 <= first <= last <= len(lines), "SOURCE_SPAN")
    return {"txt_module_span": [first, last], "pdf_pages": source.PAGES[module]}


def events_for(module: str, index: int, unit: dict, candidate: dict,
               span: dict) -> list[dict]:
    out: list[dict] = []

    def add(kind: str, contacts: list[dict], **extra: object) -> None:
        out.append(attack(kind, contacts, module, index, len(out) + 1, span, **extra))

    if module == "B":
        full = form_members(unit["full_form"])
        fragment = form_members(unit["practical_fragment"])
        workout = unit["workout"]
        need(workout["full_blocked_attacks"] == 4 and
             workout["fragment_blocked_attacks"] == 4 and
             workout["full_string_audit_attacks"] == len(full) and
             workout["attack_count"] == 8 + len(full), "B_WORKOUT")
        for _ in range(4):
            add("blocked_full_form", full)
        for member in full:
            add("picked_string_audit", [member])
        for _ in range(4):
            add("blocked_practical_fragment", fragment)
    elif module == "C":
        triad = triad_members(unit["triad"])
        need(unit["attack_pattern"] == ["blocked", "low", "middle", "high"] and
             unit["attack_count"] == 4, "C_PATTERN")
        add("blocked_triad", triad)
        for member in triad:
            add("picked_triad_note", [member])
    elif module == "D":
        major = triad_members(unit["major"])
        minor = members(unit["strings"], unit["minor"]["frets"],
                        unit["minor"]["notes"], unit["minor"]["degrees"])
        changed = [(a, b) for a, b in zip(major, minor, strict=True)
                   if a["fret"] != b["fret"]]
        need(len(changed) == 1 and changed[0][0]["string"] == unit["moving_string"] and
             changed[0][0]["fret"] - changed[0][1]["fret"] == 1 and
             unit["attack_sequence"] == ["major", "minor"] * 4 and
             unit["attack_count"] == 8, "D_THIRD")
        for quality in unit["attack_sequence"]:
            add("blocked_quality_" + quality, major if quality == "major" else minor)
    elif module in ("E", "F"):
        placements = unit["placements"]
        need(len(placements) == unit["attack_count"] == len(unit["notes"]) ==
             len(unit["degrees"]), "MELODY_COUNT")
        for i, place in enumerate(placements):
            need(place["note"] == unit["notes"][i], "MELODY_NOTE")
            add("picked_chord_tone" if module == "E" else "picked_nearby_scale_tone",
                [contact(place["string"], place["fret"], place["note"],
                         unit["degrees"][i])], bar=place["bar"],
                source_column=place["source_column"])
    elif module == "G":
        grip = members(unit["strings"], unit["frets"], unit["notes"])
        need(len(grip) == 4 and unit["attack_count"] ==
             unit["quarter_note_blocked_attacks"] == 4, "G_FRAGMENT")
        for _ in range(4):
            add("blocked_practical_fragment", grip)
    elif module in ("H", "J"):
        chords = unit["chords"] if module == "H" else [unit]
        for chord in chords:
            grip = triad_members(chord["triad"])
            need(chord["attack_pattern"] == ["blocked", "low", "middle", "high"] and
                 chord["attack_count"] == 4, "TRIAD_PATTERN")
            add("blocked_triad", grip, chord=chord["chord"])
            for member in grip:
                add("picked_triad_note", [member], chord=chord["chord"])
    elif module == "I":
        by_form = {x["form"]: x for x in candidate["modules"]["B"]}
        scales = {x["form"]: x for x in candidate["modules"]["F"]}
        form = unit["form"]
        fragment = form_members(by_form[form]["practical_fragment"])
        need([m["fret"] for m in fragment] == unit["blocked_fragment_frets"],
             "I_FRAGMENT")
        triad = triad_members(unit["primary_triad"])
        scale = scales[form]
        need(unit["attack_pattern"] == ["blocked", "triad_low", "triad_middle",
                                        "triad_high"] + ["scale"] * 8 and
             unit["scale_degrees"] == [int(x) for x in scale["degrees"][:8]] and
             unit["attack_count"] == 12, "I_PATTERN")
        add("blocked_practical_fragment", fragment)
        for member in triad:
            add("picked_triad_note", [member])
        for i, place in enumerate(scale["placements"][:8]):
            add("picked_nearby_scale_tone", [contact(place["string"], place["fret"],
                                                    place["note"], scale["degrees"][i])],
                source_link=f"F-{form}-{i+1:02d}")
    else:
        need(False, "MODULE")
    need(len(out) == (unit["workout"]["attack_count"] if module == "B" else
                      unit["attack_count"]), f"ITEM_ATTACK_COUNT {module}")
    return out


def project(candidate: dict) -> tuple[dict, dict]:
    need(candidate["schema"] == "fathom.detached.curriculum.level054.whole.r01" and
         candidate["wbs"] == "2.3.1.2.1" and candidate["level"] == 54 and
         candidate["sounded_attacks"] == 558 and
         candidate["silent_formation_prompts"] == 45 and
         candidate["sounded_attacks_by_module"] == COUNTS and
         set(candidate["modules"]) == set(COUNTS) and
         candidate["canonical_ids"] is None and
         all(candidate[k] is False for k in
             ("runtime_import", "content_admitted", "timing_or_audio_inferred")),
         "SOURCE_SCOPE")
    need(candidate["source"]["txt"]["sha256"] == PINS[source.TXT] and
         candidate["source"]["pdf"]["sha256"] == PINS[source.PDF] and
         candidate["source"]["source_map"]["sha256"] == PINS[source.MAP],
         "SOURCE_IDENTITY")
    lines = (ROOT / source.TXT).read_text().splitlines()
    records = []
    mapping = []
    module_counts = {}
    for module in COUNTS:
        span = module_span(lines, module)
        if module == "A":
            a = candidate["modules"]["A"]
            need(a["silent_prompt_count"] == 45 and
                 a["silent_master_forms"] == a["silent_practical_partials"] ==
                 list(source.FORMS) and len(a["natural_root_form_prompts"]) == 35,
                 "A_SILENCE")
            units = ([{"form": form, "kind": "silent_master_form", "sound": False}
                      for form in a["silent_master_forms"]] +
                     [{"form": form, "kind": "silent_practical_partial", "sound": False}
                      for form in a["silent_practical_partials"]] +
                     [{**x, "kind": "silent_natural_root_form"}
                      for x in a["natural_root_form_prompts"]])
        else:
            units = candidate["modules"][module]
        need(len(units) == ITEMS[module], f"ITEM_COUNT {module}")
        attack_count = 0
        for index, unit in enumerate(units, 1):
            if module == "A":
                need(unit["sound"] is False, "A_SILENT_ONLY")
            events = [] if module == "A" else events_for(module, index, unit, candidate, span)
            attack_count += len(events)
            key = f"L54-{module}-{index:02d}"
            provenance = {"txt_path": str(source.TXT),
                          "txt_module_span": span["txt_module_span"],
                          "pdf_path": str(source.PDF),
                          "pdf_pages": span["pdf_pages"],
                          "source_candidate_sha256": PINS[CANDIDATE]}
            record = {"source_local_key": key, "identity_state": "unallocated",
                      "source_unit_sha256": sha(encoded(unit)),
                      "source_unit": copy.deepcopy(unit),
                      "source_provenance": provenance,
                      "silent_formation": (copy.deepcopy(unit) if module == "A" else None),
                      "schema1_fields": {"id": None, "workbook_id": None,
                                         "module_id": None, "lineage": None,
                                         "content_revision": None,
                                         "legacy_level": 54,
                                         "title": f"Level 54 module {module} item {index}",
                                         "kind": "silent_formation" if module == "A" else "chord_or_note_attack",
                                         "runtime_eligible": False,
                                         "source_refs": [f"L54-TXT1-{span['txt_module_span'][0]}-{span['txt_module_span'][1]}"] +
                                                        [f"L54-PDF1-p{p}" for p in span["pdf_pages"]],
                                         "events": events, "variants": [],
                                         "timing": {"status": "unresolved", "unit": "quarter",
                                                    "onset_q": None, "duration_q": None,
                                                    "fixed_bpm": None, "note_per_click": None},
                                         "resource_requirements": [],
                                         "ambiguities": UNRESOLVED}}
            records.append(record)
            mapping.append({"source_local_key": key,
                            "source_unit_sha256": record["source_unit_sha256"],
                            "module": module, "item": index,
                            "sounded_attacks": len(events),
                            "silent_formations": 1 if module == "A" else 0,
                            **span})
        need(attack_count == COUNTS[module], f"MODULE_ATTACKS {module}")
        module_counts[module] = {"items": len(units), "sounded_attacks": attack_count,
                                 "silent_formations": len(units) if module == "A" else 0}
    need(len(records) == 120 and sum(x["sounded_attacks"] for x in module_counts.values()) == 558 and
         sum(x["silent_formations"] for x in module_counts.values()) == 45,
         "WHOLE_COUNTS")
    proposal = {"schema": "fathom-level054-schema1-field-proposal.1",
                "classification": "build_only_unallocated_nonimportable",
                "wbs_id": "2.3.1.2.1", "legacy_level": 54,
                "source_candidate_sha256": PINS[CANDIDATE],
                "source": candidate["source"],
                "source_notes": candidate["source_notes"],
                "reference_cycle": candidate["reference_cycle"],
                "root_formulas": candidate["root_formulas"],
                "module_counts": module_counts, "records": records,
                "canonical_ids_allocated": False, "runtime_eligible": False,
                "admitted": False, "whole_workbook_complete": False,
                "timing_resolved": False, "curriculum_signoff": False}
    handoff = {"schema": "fathom-level054-schema1-allocation-handoff.1",
               "field_proposal_sha256": sha(encoded(proposal)),
               "source_candidate_sha256": PINS[CANDIDATE],
               "records": mapping, "module_counts": module_counts,
               "unresolved": UNRESOLVED,
               "next_step": "independent source/music review before identity allocation or import",
               "admitted": False, "runtime_eligible": False,
               "whole_workbook_complete": False}
    return proposal, handoff


def derive() -> tuple[dict, dict]:
    pin()
    foundation_status()
    sealed = json.loads((ROOT / CANDIDATE).read_text())
    replay = source.build(ROOT)
    need(sealed == replay, "P08_REPLAY_DRIFT")
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
                      "items": len(proposal["records"]), "sounded_attacks": 558,
                      "silent_formations": 45,
                      "field_proposal_sha256": sha(files["field-proposal.json"]),
                      "handoff_sha256": sha(files["allocation-handoff.json"])}, sort_keys=True))


if __name__ == "__main__":
    main()
