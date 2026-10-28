#!/usr/bin/env python3
"""Build two source-closed, nonadmitted Level 9 first-route references."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = Path("Build/parallel-37/controlled-open-level009-two-case-r01")
TXT = Path("Notes/music/guitar project/TXT version/108_Finger_Permutations_Level_9_Mid_Pattern_Position_Transfer.txt")
PDF = Path("Notes/music/guitar project/PDF version/108_Finger_Permutations_Level_9_Mid_Pattern_Position_Transfer.pdf")
P07 = Path("Build/parallel-07/2.3.1.1.1-level009-set01-r01/candidate.json")
AUDIT = OUT / "identity-audit.json"
BASE = Path("Content/controls/curriculum-v1")
TXT_SHA = "3cb0983c95081771caea7a12e8263d780f58850154681a9cd85c1a1916956105"
PDF_SHA = "3564ed3c24d55df462dba49b81ef2aeaf9a716a5a5af993bfdbf3e774702b00f"
P07_SHA = "098bb861ddcabcaf48f75753988304c6a96ac6994140666d0c8c5070def8f94e"
AUDIT_SHA = "ff03d39798622296e0dba0166181af8f9c78b7019ae1a8854d2bcfc84f5e93c6"
ITEMS = ("fg:item:001149", "fg:item:001150")
MODULES = ("fg:module:001149", "fg:module:001150")
VARIANTS = (("fg:variant:007420", "fg:variant:007421"),
            ("fg:variant:007422", "fg:variant:007423"))
WORKBOOK = "fg:workbook:000009"
NAMES = ("package.json", "identity-registry.json", "expected-profile.json",
         "candidate-allocation.json", "identity-baseline.json", "allocation-baseline.json",
         "lineage-baseline.json", "source-provenance.json", "summary.json")


class CandidateError(ValueError):
    pass


def need(ok: bool, code: str) -> None:
    if not ok:
        raise CandidateError(code)


def encode(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n").encode()


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read(path: Path) -> dict:
    return json.loads((ROOT / path).read_bytes())


def passage(path: Path, digest: str, fmt: str, text: str, **where: int) -> dict:
    return {"path": str(path), "sha256": digest, "format": fmt, **where,
            "text": text, "text_sha256": sha(text.encode())}


def source_facts() -> tuple[list[str], list[str], list[dict]]:
    from pypdf import PdfReader

    need(sha((ROOT / TXT).read_bytes()) == TXT_SHA, "TXT_PIN_DRIFT")
    need(sha((ROOT / PDF).read_bytes()) == PDF_SHA, "PDF_PIN_DRIFT")
    need(sha((ROOT / P07).read_bytes()) == P07_SHA, "P07_PIN_DRIFT")
    need(sha((ROOT / AUDIT).read_bytes()) == AUDIT_SHA, "AUDIT_PIN_DRIFT")
    audit = read(AUDIT)
    wanted = {*ITEMS, *MODULES, *VARIANTS[0], *VARIANTS[1]}
    need(audit["status"] == "PASS" and not audit["matches"] and
         audit["json_files_scanned"] >= 12000 and set(audit["wanted"]) == wanted,
         "IDENTITY_AUDIT_DRIFT")

    lines = (ROOT / TXT).read_text().splitlines()
    pages = [p.extract_text() or "" for p in PdfReader(str(ROOT / PDF)).pages]
    need(len(pages) == 10, "PDF_PAGE_COUNT")
    need(lines[2].startswith("P5 mapping: 1=index/fret 5") and
         lines[3].startswith("P7 mapping: 1=index/fret 7") and
         "SHIFT UP: play digits 1-2" in lines[6] and
         "SHIFT DOWN: play digits 1-2" in lines[8] and
         "center divider marks the shift after note 2" in lines[9],
         "TXT_FRAME_RULE_DRIFT")
    need(lines[20].startswith("Pass 1: play notes 1-2, stop") and
         lines[21] == "Pass 2: remove the stop, play straight eighths, lightly accent note 3, remove the accent, then convert to 16ths." and
         lines[22].endswith("D-U | D-U and U-D | U-D."), "TXT_PASS2_DRIFT")
    need(lines[30] == "Exercise 001: 1212" and
         lines[31].startswith("SHIFT UP - P5 to P7") and
         lines[37] == "E|5-6------|7-8------|" and
         lines[38].startswith("SHIFT DOWN - P7 to P5") and
         lines[39] == "e|7-8------|5-6------|", "TXT_SELECTED_TAB_DRIFT")
    need("PASS 2" in pages[0] and "convert to 16ths" in pages[0] and
         "Use D-U | D-U and U-D | U-D" in pages[0] and
         "release after note 2" in pages[0].lower(), "PDF_RULE_DRIFT")
    first = pages[1].split("001    1212", 1)[-1].split("002    1213", 1)[0]
    need("001    1212" in pages[1] and "UP" in first and "DN" in first and
         "P5->P7" in first and "P7->P5" in first and
         "S|5-6------|7-8------|" in first and
         "S|7-8------|5-6------|" in first, "PDF_SELECTED_TAB_DRIFT")

    p07 = read(P07)["records"][0]
    need(p07["code"] == "1212", "P07_CODE_DRIFT")
    selected = []
    specs = (("shift_up", "E", 1, (5, 6, 7, 8), ("P5", "P7"), 38),
             ("shift_down", "e", 6, (7, 8, 5, 6), ("P7", "P5"), 40))
    for direction, string_name, string_num, frets, frames, txt_line in specs:
        route = next(d for d in p07["directions"] if d["direction"] == direction)["routes"][0]
        need(route["string"] == string_name and route["shift_after_note"] == 2 and
             route["source_tab_row"] == lines[txt_line-1], "P07_ROUTE_DRIFT")
        need(tuple(c["position"] for c in route["cells"]) == frames,
             "P07_FRAME_DRIFT")
        notes = [n for c in route["cells"] for n in c["notes"]]
        need(tuple(n["fret"] for n in notes) == frets and
             tuple(n["finger_digit"] for n in notes) == ("1", "2", "1", "2") and
             all(n["onset_q"] is n["duration_q"] is None for n in notes),
             "P07_UNTIMED_PARITY_DRIFT")
        open_midi = 40 if string_num == 1 else 64
        facts = [(string_num, fret, int(n["finger_digit"]), open_midi+fret,
                  frames[i//2]) for i, (fret, n) in enumerate(zip(frets, notes))]
        selected.append({"direction": direction, "string_name": string_name,
                         "txt_line": txt_line, "facts": facts})
    return lines, pages, selected


def derive(*, changed_facts: list | None = None, changed_onsets: list | None = None,
           changed_durations: list | None = None, changed_strokes: dict | None = None,
           force_eligible: bool = False, reserved_item: str = ITEMS[0]) -> dict[str, dict]:
    need(not force_eligible, "FORCED_ELIGIBILITY")
    need(reserved_item == ITEMS[0], "FOREIGN_ID")
    lines, pages, selected = source_facts()
    facts = [s["facts"] for s in selected]
    need(changed_facts is None or changed_facts == facts, "CANDIDATE_SOURCE_DRIFT")
    onsets = [[Fraction(i, 4).numerator, Fraction(i, 4).denominator] for i in range(4)]
    need(changed_onsets is None or changed_onsets == onsets, "CANDIDATE_TIMING_DRIFT")
    durations = [[1, 4]] * 4
    need(changed_durations is None or changed_durations == durations, "CANDIDATE_DURATION_DRIFT")
    strokes = {v: (["D", "U", "D", "U"] if ix == 0 else ["U", "D", "U", "D"])
               for pair in VARIANTS for ix, v in enumerate(pair)}
    need(changed_strokes is None or changed_strokes == strokes, "CANDIDATE_STROKE_DRIFT")
    refs = ["L9-TXT1-31-45", "L9-PDF1-p2", "L9-TXT1-1-25", "L9-PDF1-p1"]
    sources = {
        refs[0]: passage(TXT, TXT_SHA, "txt", "\n".join(lines[30:45]), first_line=31, last_line=45),
        refs[1]: passage(PDF, PDF_SHA, "pdf", pages[1], page=2),
        refs[2]: passage(TXT, TXT_SHA, "txt", "\n".join(lines[:25]), first_line=1, last_line=25),
        refs[3]: passage(PDF, PDF_SHA, "pdf", pages[0], page=1),
    }
    records, entities, event_sources, provenance, allocations = [], [], {}, {}, {}
    entities.append({"id": WORKBOOK, "kind": "workbook", "label": "Legacy Level9",
                     "parent": "fg:course:000001"})
    for ix, spec in enumerate(selected):
        item, module, vids = ITEMS[ix], MODULES[ix], VARIANTS[ix]
        direction, string_name, txt_line = spec["direction"], spec["string_name"], spec["txt_line"]
        local = f"L009-S01-EX001:{direction.upper()}:{string_name}:PASS2"
        events, sidecar = [], {}
        for index, (string, fret, finger, midi, frame) in enumerate(spec["facts"], 1):
            eid = f"{item}:event:{index:04d}"
            events.append({"event_id": eid, "kind": "note", "string": string,
                           "fret": fret, "finger": finger, "midi": midi,
                           "spelling": None, "attack": "picked", "onset_q": onsets[index-1],
                           "duration_q": durations[index-1], "tie_from": None,
                           "degree_contexts": {}})
            event_sources[eid] = refs[0]
            sidecar[eid] = {"source_local_event_key": f"{local}:{index:02d}",
                            "source_txt_ref": refs[0], "source_pdf_ref": refs[1],
                            "source_txt_line": txt_line, "source_pdf_page": 2,
                            "source_finger_line": 3 if frame == "P5" else 4,
                            "string": string, "fret": fret, "finger_digit": finger,
                            "frame": frame, "shift_boundary_after_note": 2,
                            "landing_note": index == 3,
                            "timing_ref": refs[2], "timing_pdf_ref": refs[3],
                            "timing_option": "PASS2_unaccented_straight_sixteenths"}
        provenance.update(sidecar)
        variants = []
        for vid, start in zip(vids, ("D", "U")):
            variants.append({"id": vid, "label": f"ex001-{direction}-first-{string_name}-pass2-{start}-start",
                             "role": "notation_practice", "route": f"{direction}_{string_name}_only_2_plus_2",
                             "source_refs": refs, "event_ids": list(sidecar),
                             "pick_start": start, "pick_start_origin": "source_authored",
                             "grouping": {"kind": "source_event_time", "notes_per_beat": None,
                                          "beat_unit_q": None, "marking_factor": [1, 1],
                                          "source_label": "TXT line22/PDF page1 Pass2 straight sixteenths"},
                             "accent_policy": "even", "tail_pause": None,
                             "unresolved": []})
        title = f"Level 9 Exercise 001 first {string_name} {direction.replace('_', ' ')} 2+2 Pass2"
        record = {"id": item, "module_id": module, "workbook_id": WORKBOOK,
                  "content_revision": 1, "lineage": {"kind": "new"}, "kind": "notation",
                  "legacy_level": 9, "status": "converted_candidate", "runtime_eligible": False,
                  "title": title, "source_refs": refs, "authored_text_refs": refs,
                  "events": events, "variants": variants, "resource_requirements": [], "rubric": None,
                  "control_scope": {"extent": "complete_selected_case", "local_case": local,
                                    "source_event_count": 4, "basis_refs": refs,
                                    "whole_workbook_complete": False,
                                    "unresolved": ["Other strings, passes and Exercises002-108 are outside this case.",
                                                   "Whole Exercise001/Level9 and runtime admission remain Pending."]},
                  "context": {"local_code": local, "route": f"{direction} first {string_name} string only",
                              "position": "P5_to_P7" if ix == 0 else "P7_to_P5",
                              "pick_start_variants": ["D", "U"],
                              "pick_start": "source-authored D or U; D-U|D-U or U-D|U-D",
                              "tuning_open_midi": [40, 45, 50, 55, 59, 64], "capo": 0,
                              "source_tempo_rules_ref": refs[2]},
                  "timing": {"status": "source_defined", "unit": "quarter", "meter": None,
                             "basis": "TXT line22/PDF page1 Pass2: remove stop and accent, select straight 16ths. Nominal quarter subdivisions, not measured sustain or ASCII spacing."},
                  "ambiguities": ["The selected straight-sixteenth Pass2 option excludes Pass1 and intermediate eighths/accent.",
                                  "Relative tempo and progression rules do not author fixed BPM or credit.",
                                  "Capo zero is untransposed standard-tuning representation, not a capo instruction."],
                  "normalization": [{"kind": "representation_metadata", "basis": refs[2],
                                     "text": f"First {string_name} {direction} 2+2 Pass2 cell; whole frame shifts after note2, event3 lands in destination frame. Straight-sixteenth nominal slots; source-authored D/U patterns continue without stop or accent."}]}
        records.append(record)
        entities.extend([{"id": module, "kind": "module", "label": title, "parent": WORKBOOK},
                         {"id": item, "kind": "item", "label": title, "parent": module},
                         *({"id": v["id"], "kind": "variant", "label": v["label"],
                            "parent": item} for v in variants)])
        allocations[item] = {"legacy_level": 9,
                             "occurrences": {p["source_local_event_key"]: eid for eid, p in sidecar.items()},
                             "variants": {v["label"]: v["id"] for v in variants}}

    foundation, base_registry, base_profile = (read(BASE / name) for name in
                                                ("package.json", "identity-registry.json", "expected-profile.json"))
    package = {k: copy.deepcopy(v) for k, v in foundation.items()
               if k not in ("records", "sources", "workbook_catalog")}
    package.update(content_version="curriculum-v1-level009-ex001-first-up-down-pass2-build-only.1",
                   records=records, sources=sources)
    registry = {"identity_version": base_registry["identity_version"],
                "rules": base_registry["rules"],
                "entities": [base_registry["entities"][0], *entities]}
    identity_baseline = {"identity_version": registry["identity_version"],
                         "rules": registry["rules"], "entities": [registry["entities"][0]]}
    allocation_baseline = {"version": "control-allocation.1",
                           "authority": "P37 provisional only; no prior local Level9 selected-case allocation",
                           "records": {}}
    lineage_baseline = {"version": "lineage-baseline.1", "records": {}}
    allocation = {"version": "control-allocation.1",
                  "authority": "P37 provisional nonadmitted allocation; P02 canonical re-audit required",
                  "records": allocations}
    profile = {k: copy.deepcopy(v) for k, v in base_profile.items()
               if k not in ("reference_package", "reference_registry", "event_sources",
                            "authority_artifacts", "workbook_catalog")}
    profile["degree_roots"] = {}
    profile.update(reference_package=package, reference_registry=registry,
                   event_sources=event_sources)
    profile["authority_artifacts"] = [copy.deepcopy(a) for a in base_profile["authority_artifacts"]
                                      if a["role"] in ("source_manifest", "source_acceptance",
                                                      "current_schema_freeze")]
    for role, name, value in (("identity_baseline", "identity-baseline.json", identity_baseline),
                              ("allocation_baseline", "allocation-baseline.json", allocation_baseline),
                              ("lineage_baseline", "lineage-baseline.json", lineage_baseline),
                              ("candidate_identity_allocation", "candidate-allocation.json", allocation)):
        profile["authority_artifacts"].append({"path": str(OUT / name), "role": role,
                                               "sha256": sha(encode(value))})
    need(set(event_sources) == set(provenance) ==
         {e["event_id"] for r in records for e in r["events"]}, "EVENT_PROVENANCE_COVERAGE")
    need(set(sources) == set(refs), "SOURCE_REF_COVERAGE")
    summary = {"status": "source_interpreted_nonadmitted_reference",
               "item_ids": list(ITEMS), "variant_ids": [v for pair in VARIANTS for v in pair],
               "record_count": 2, "event_count": 8, "admitted": False,
               "runtime_eligible": False, "whole_workbook_complete": False,
               "source_txt_sha256": TXT_SHA, "source_pdf_sha256": PDF_SHA,
               "p07_parity_sha256": P07_SHA, "identity_audit_sha256": AUDIT_SHA,
               "selected_option": "PASS2_unaccented_straight_sixteenths",
               "interpretation": "First low-E SHIFT UP and high-e SHIFT DOWN 2+2; D/U starts; independent review required"}
    return {"package.json": package, "identity-registry.json": registry,
            "expected-profile.json": profile, "candidate-allocation.json": allocation,
            "identity-baseline.json": identity_baseline,
            "allocation-baseline.json": allocation_baseline,
            "lineage-baseline.json": lineage_baseline,
            "source-provenance.json": {"source_txt_ref": refs[0], "source_pdf_ref": refs[1],
                                       "timing_txt_ref": refs[2], "timing_pdf_ref": refs[3],
                                       "events": provenance, "variant_strokes": strokes,
                                       "stroke_basis": "TXT line23 and PDF page1 author D-U|D-U and U-D|U-D for both directions."},
            "summary.json": summary}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("build", "verify"))
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    result = derive()
    dest = (ROOT / args.out).resolve()
    allowed = (ROOT / OUT).resolve()
    need(dest == allowed or allowed in dest.parents, "OUTPUT_SCOPE")
    if args.command == "build":
        dest.mkdir(parents=True, exist_ok=True)
        need(all(not (dest / name).exists() for name in NAMES), "OUTPUT_EXISTS")
        for name in NAMES:
            (dest / name).write_bytes(encode(result[name]))
    else:
        for name in NAMES:
            need((dest / name).read_bytes() == encode(result[name]), f"OUTPUT_DRIFT:{name}")
    print(json.dumps(result["summary.json"], sort_keys=True))


if __name__ == "__main__":
    main()
