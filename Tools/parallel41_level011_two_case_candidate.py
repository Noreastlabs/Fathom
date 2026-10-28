#!/usr/bin/env python3
"""Build two source-closed, nonadmitted Level 11 first-route references."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = Path("Build/parallel-41/controlled-open-level011-two-case-r01")
TXT = Path("Notes/music/guitar project/TXT version/108_Finger_Permutations_Level_11_Three_Position_Relay.txt")
PDF = Path("Notes/music/guitar project/PDF version/108_Finger_Permutations_Level_11_Three_Position_Relay.pdf")
P12 = Path("Build/parallel-12/level011-local-shard-r01/package.json")
AUDIT = OUT / "identity-audit.json"
BASE = Path("Content/controls/curriculum-v1")
TXT_SHA = "e579bb423d644a628723c802d84967f5c7aad49bf4e8e89bba5e4b622bf6ff48"
PDF_SHA = "5f9b5e29e2f5ad3aa3372125f0ec0b91e6245eef1edabd5e81c06d1f00f5e917"
P12_SHA = "154c534d6a5e31373b763d6c296bbba3ad1399ac7eb6c3b0931f1ef8434eab37"
AUDIT_SHA = "185d175e89b78fe6af12edd0894f3a2205f07f1544e3c79088b7544bf4997e4d"
ITEMS = ("fg:item:001151", "fg:item:001152")
MODULES = ("fg:module:001151", "fg:module:001152")
VARIANTS = (("fg:variant:007424", "fg:variant:007425"),
            ("fg:variant:007426", "fg:variant:007427"))
WORKBOOK = "fg:workbook:000011"
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
    need(sha((ROOT / P12).read_bytes()) == P12_SHA, "P12_PIN_DRIFT")
    need(sha((ROOT / AUDIT).read_bytes()) == AUDIT_SHA, "AUDIT_PIN_DRIFT")
    audit = read(AUDIT)
    wanted = {*ITEMS, *MODULES, *VARIANTS[0], *VARIANTS[1]}
    need(audit["status"] == "PASS" and not audit["matches"] and not audit["errors"] and
         audit["json_files_scanned"] >= 10000 and set(audit["wanted"]) == wanted,
         "IDENTITY_AUDIT_DRIFT")

    lines = (ROOT / TXT).read_text().splitlines()
    pages = [p.extract_text() or "" for p in PdfReader(str(ROOT / PDF)).pages]
    need(len(pages) == 10, "PDF_PAGE_COUNT")
    need(lines[2].startswith("1+2+1 double-shift control") and
         lines[3].startswith("P5 mapping: 1=index/fret 5") and
         lines[4].startswith("P7 mapping: 1=index/fret 7") and
         lines[5].startswith("P9 mapping: 1=index/fret 9") and
         lines[8].startswith("Divide every four-digit code 1+2+1") and
         lines[9].startswith("SHIFT UP: play note 1 in P5") and
         lines[11].startswith("SHIFT DOWN: play note 1 in P9") and
         lines[13] == "The first landing note is note 2. The second landing note is note 4." and
         lines[14].endswith("both frame relocations are mandatory."),
         "TXT_FRAME_RULE_DRIFT")
    need(lines[28] == "Downstroke start: D | U-D | U." and
         lines[29] == "Upstroke start:   U | D-U | D." and
         lines[30].endswith("alternate-picking cycle.") and
         lines[34].startswith("Pass 1: use even eighth notes, pause") and
         lines[35].startswith("Pass 2: remove both pauses") and
         lines[36].startswith("Convert the connected cell to straight sixteenth notes."),
         "TXT_PASS2_DRIFT")
    need(lines[50:57] == ["Exercise 001: 1212",
         "SHIFT UP - P5 to P7 to P9; repeat on E>A>D>G>B>e",
         "F|1------|2-1----|2------|", "S|5------|8-7----|10-----|",
         "SHIFT DOWN - P9 to P7 to P5; repeat on e>B>G>D>A>E",
         "F|1------|2-1----|2------|", "S|9------|8-7----|6------|"],
         "TXT_SELECTED_TAB_DRIFT")
    need("Pass 2: remove both pauses" in pages[0] and
         "D-start  D | U-D | U" in pages[0] and
         "U-start  U | D-U | D" in pages[0] and
         "Shift after notes 1 and 3." in pages[0], "PDF_RULE_DRIFT")
    first = pages[1].split("001   1212", 1)[-1].split("002   1213", 1)[0]
    need("001   1212" in pages[1] and "UP" in first and "DN" in first and
         "P5>P7>P9" in first and "P9>P7>P5" in first and
         "S|5------|8-7----|10-----|" in first and
         "S|9------|8-7----|6------|" in first and
         "landings 2 and 4; no pick reset" in first, "PDF_SELECTED_TAB_DRIFT")

    p12 = read(P12)["records"][0]
    need(p12["title"].startswith("Exercise 001: 1212") and
         len(p12["events"]) == 48, "P12_CODE_DRIFT")
    specs = (("shift_up", "E", 1, (5, 8, 7, 10), ("P5", "P7", "P7", "P9"), 54, 0),
             ("shift_down", "e", 6, (9, 8, 7, 6), ("P9", "P7", "P7", "P5"), 57, 24))
    selected = []
    for direction, string_name, string_num, frets, frames, txt_line, offset in specs:
        prior = p12["events"][offset:offset+4]
        expected = [(string_num, fret, (1,2,1,2)[i], (40 if string_num == 1 else 64)+fret)
                    for i, fret in enumerate(frets)]
        need([(e["string"],e["fret"],e["finger"],e["midi"]) for e in prior] == expected and
             all(e["onset_q"] is e["duration_q"] is None for e in prior),
             "P12_UNTIMED_PARITY_DRIFT")
        facts = [(s,f,d,m,frames[i]) for i,(s,f,d,m) in enumerate(expected)]
        selected.append({"direction":direction,"string_name":string_name,
                         "txt_line":txt_line,"facts":facts})
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
    refs = ["L11-TXT1-51-57", "L11-PDF1-p2", "L11-TXT1-1-41", "L11-PDF1-p1"]
    sources = {
        refs[0]: passage(TXT, TXT_SHA, "txt", "\n".join(lines[50:57]), first_line=51, last_line=57),
        refs[1]: passage(PDF, PDF_SHA, "pdf", pages[1], page=2),
        refs[2]: passage(TXT, TXT_SHA, "txt", "\n".join(lines[:41]), first_line=1, last_line=41),
        refs[3]: passage(PDF, PDF_SHA, "pdf", pages[0], page=1),
    }
    records, entities, event_sources, provenance, allocations = [], [], {}, {}, {}
    entities.append({"id": WORKBOOK, "kind": "workbook", "label": "Legacy Level11",
                     "parent": "fg:course:000001"})
    for ix, spec in enumerate(selected):
        item, module, vids = ITEMS[ix], MODULES[ix], VARIANTS[ix]
        direction, string_name, txt_line = spec["direction"], spec["string_name"], spec["txt_line"]
        local = f"L011-S01-EX001:{direction.upper()}:{string_name}:PASS2"
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
                            "source_finger_line": {"P5":4,"P7":5,"P9":6}[frame],
                            "string": string, "fret": fret, "finger_digit": finger,
                            "frame": frame, "shift_boundary_after_notes": [1,3],
                            "landing_note": index in (2,4),
                            "timing_ref": refs[2], "timing_pdf_ref": refs[3],
                            "timing_option": "PASS2_connected_unaccented_straight_sixteenths"}
        provenance.update(sidecar)
        variants = []
        for vid, start in zip(vids, ("D", "U")):
            variants.append({"id": vid, "label": f"ex001-{direction}-first-{string_name}-pass2-{start}-start",
                             "role": "notation_practice", "route": f"{direction}_{string_name}_only_1_plus_2_plus_1",
                             "source_refs": refs, "event_ids": list(sidecar),
                             "pick_start": start, "pick_start_origin": "source_authored",
                             "grouping": {"kind": "source_event_time", "notes_per_beat": None,
                                          "beat_unit_q": None, "marking_factor": [1, 1],
                                          "source_label": "TXT lines35-38 connected Pass2 straight sixteenths; PDF page1 confirms pause/accent removal"},
                             "accent_policy": "even", "tail_pause": None,
                             "unresolved": []})
        title = f"Level 11 Exercise 001 first {string_name} {direction.replace('_', ' ')} 1+2+1 Pass2"
        record = {"id": item, "module_id": module, "workbook_id": WORKBOOK,
                  "content_revision": 1, "lineage": {"kind": "new"}, "kind": "notation",
                  "legacy_level": 11, "status": "converted_candidate", "runtime_eligible": False,
                  "title": title, "source_refs": refs, "authored_text_refs": refs,
                  "events": events, "variants": variants, "resource_requirements": [], "rubric": None,
                  "control_scope": {"extent": "complete_selected_case", "local_case": local,
                                    "source_event_count": 4, "basis_refs": refs,
                                    "whole_workbook_complete": False,
                                    "unresolved": ["Other strings, passes and Exercises002-108 are outside this case.",
                                                   "Whole Exercise001/Level11 and runtime admission remain Pending."]},
                  "context": {"local_code": local, "route": f"{direction} first {string_name} string only",
                              "position": "P5_to_P7_to_P9" if ix == 0 else "P9_to_P7_to_P5",
                              "pick_start_variants": ["D", "U"],
                              "pick_start": "source-authored D or U; D|U-D|U or U|D-U|D, no reset",
                              "tuning_open_midi": [40, 45, 50, 55, 59, 64], "capo": 0,
                              "source_tempo_rules_ref": refs[2]},
                  "timing": {"status": "source_defined", "unit": "quarter", "meter": None,
                             "basis": "TXT lines35-38 select connected unaccented Pass2 straight 16ths; PDF page1 confirms two pauses/accent removal but does not restate 16ths. Nominal quarter subdivisions, not measured sustain or ASCII spacing."},
                  "ambiguities": ["The selected straight-sixteenth Pass2 option excludes Pass1 and intermediate eighths/accent; PDF does not independently restate straight 16ths.",
                                  "Relative tempo and progression rules do not author fixed BPM or credit.",
                                  "Capo zero is untransposed standard-tuning representation, not a capo instruction."],
                  "normalization": [{"kind": "representation_metadata", "basis": refs[2],
                                     "text": f"First {string_name} {direction} 1+2+1 Pass2 cell; mandatory whole frame shifts after notes1/3, events2/4 land in destination frames. Straight-sixteenth nominal slots; source-authored D/U patterns continue without stop or accent."}]}
        records.append(record)
        entities.extend([{"id": module, "kind": "module", "label": title, "parent": WORKBOOK},
                         {"id": item, "kind": "item", "label": title, "parent": module},
                         *({"id": v["id"], "kind": "variant", "label": v["label"],
                            "parent": item} for v in variants)])
        allocations[item] = {"legacy_level": 11,
                             "occurrences": {p["source_local_event_key"]: eid for eid, p in sidecar.items()},
                             "variants": {v["label"]: v["id"] for v in variants}}

    foundation, base_registry, base_profile = (read(BASE / name) for name in
                                                ("package.json", "identity-registry.json", "expected-profile.json"))
    package = {k: copy.deepcopy(v) for k, v in foundation.items()
               if k not in ("records", "sources", "workbook_catalog")}
    package.update(content_version="curriculum-v1-level011-ex001-first-up-down-pass2-build-only.1",
                   records=records, sources=sources)
    registry = {"identity_version": base_registry["identity_version"],
                "rules": base_registry["rules"],
                "entities": [base_registry["entities"][0], *entities]}
    identity_baseline = {"identity_version": registry["identity_version"],
                         "rules": registry["rules"], "entities": [registry["entities"][0]]}
    allocation_baseline = {"version": "control-allocation.1",
                           "authority": "P41 provisional only; no prior local Level11 selected-case allocation",
                           "records": {}}
    lineage_baseline = {"version": "lineage-baseline.1", "records": {}}
    allocation = {"version": "control-allocation.1",
                  "authority": "P41 provisional nonadmitted allocation; P02 canonical re-audit required",
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
               "p12_parity_sha256": P12_SHA, "identity_audit_sha256": AUDIT_SHA,
               "selected_option": "PASS2_connected_unaccented_straight_sixteenths",
               "interpretation": "First low-E SHIFT UP and high-e SHIFT DOWN 1+2+1 with two shifts; D/U starts; independent review required"}
    return {"package.json": package, "identity-registry.json": registry,
            "expected-profile.json": profile, "candidate-allocation.json": allocation,
            "identity-baseline.json": identity_baseline,
            "allocation-baseline.json": allocation_baseline,
            "lineage-baseline.json": lineage_baseline,
            "source-provenance.json": {"source_txt_ref": refs[0], "source_pdf_ref": refs[1],
                                       "timing_txt_ref": refs[2], "timing_pdf_ref": refs[3],
                                       "events": provenance, "variant_strokes": strokes,
                                       "stroke_basis": "TXT lines29-31 and PDF page1 author D|U-D|U and U|D-U|D with no reset for both directions."},
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
