#!/usr/bin/env python3
"""Build one source-closed, nonadmitted Level 10 odd-count shift reference."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = Path("Build/parallel-23/controlled-open-level010-r01")
TXT = Path("Notes/music/guitar project/TXT version/108_Finger_Permutations_Level_10_Odd_Count_Position_Transfer.txt")
PDF = Path("Notes/music/guitar project/PDF version/108_Finger_Permutations_Level_10_Odd_Count_Position_Transfer.pdf")
P09 = Path("Build/parallel-09/2.3.1.1.1-level010-set01-r01/candidate-01.json")
AUDIT = OUT / "identity-audit.json"
BASE = Path("Content/controls/curriculum-v1")
TXT_SHA = "e5ed078c62295adbb5f6bf00e6821e6eee0b2da73ef42c1714421158b5273226"
PDF_SHA = "1dafdcd177343f0ea147a5479ad654397d85f4b374cf960e264a230db965496b"
P09_SHA = "6b9c1ad832a633d0da5872e9dd3b5a086e7a89fa66440046cb4c058b1e6521c3"
AUDIT_SHA = "9dafab20936e60c153c67ae6c37b516d7ab576358bde9a2e8e3d7d409fdf40d3"
ITEM = "fg:item:001147"
MODULE = "fg:module:001147"
VARIANTS = ("fg:variant:007416", "fg:variant:007417")
WORKBOOK = "fg:workbook:000010"
NAMES = ("package.json", "identity-registry.json", "expected-profile.json",
         "candidate-allocation.json", "identity-baseline.json", "allocation-baseline.json",
         "lineage-baseline.json", "source-provenance.json", "summary.json")


class CandidateError(ValueError):
    pass


def need(condition: bool, code: str) -> None:
    if not condition:
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


def source_facts() -> tuple[list[str], list[str], list[tuple[int, int, int, int, str]]]:
    from pypdf import PdfReader

    need(sha((ROOT / TXT).read_bytes()) == TXT_SHA, "TXT_PIN_DRIFT")
    need(sha((ROOT / PDF).read_bytes()) == PDF_SHA, "PDF_PIN_DRIFT")
    need(sha((ROOT / P09).read_bytes()) == P09_SHA, "P09_PIN_DRIFT")
    need(sha((ROOT / AUDIT).read_bytes()) == AUDIT_SHA, "AUDIT_PIN_DRIFT")
    audit = read(AUDIT)
    need(audit["status"] == "PASS" and not audit["matches"] and audit["files_scanned"] >= 10000 and
         set(audit["wanted"]) == {ITEM, MODULE, *VARIANTS}, "IDENTITY_AUDIT_DRIFT")

    lines = (ROOT / TXT).read_text().splitlines()
    pages = [p.extract_text() or "" for p in PdfReader(str(ROOT / PDF)).pages]
    need(len(pages) == 19, "PDF_PAGE_COUNT")
    need(lines[44] == "Exercise 001: 1212" and
         lines[45].startswith("SHIFT UP - P5 to P7; digits 1-3 in P5, digit 4 in P7") and
         lines[46] == "F|1-2-1------|2----------|" and
         lines[52] == "E|5-6-5------|8----------|", "TXT_FIRST_ROUTE_DRIFT")
    need("Mode A - 3+1 late shift: play digits 1-3" in lines[6] and
         "move the whole hand and thumb" in lines[6] and
         "The landing note is note 4." in lines[7] and
         "SHIFT UP moves P5 to P7" in lines[10], "TXT_MOVEMENT_DRIFT")
    need(lines[21] == "Mode A: downstroke start = D-U-D | U; upstroke start = U-D-U | D." and
         "does not restart" in lines[23] and
         lines[28] == "Pass 2: remove the pause and accent, then connect the cell as straight eighths and finally straight 16ths." and
         "upstroke start" in lines[29], "TXT_PASS2_PICKING_DRIFT")
    need("Mode A, 3+1: shift after note 3." in pages[0] and
         "D-start D-U-D | U    U-start U-D-U | D" in pages[0] and
         "Pass 2: remove the pause and accent; move from eighths to 16ths." in pages[0],
         "PDF_RULE_DRIFT")
    need("001   1212" in pages[1] and "F|1-2-1------|2----------|" in pages[1] and
         "S|5-6-5------|8----------|" in pages[1] and
         "landing note 4; no pick reset" in pages[1], "PDF_EX001_DRIFT")

    candidate = read(P09)
    row = candidate["records"][0]
    route = row["modes"][0]["directions"][0]["string_routes"][0]
    need(row["exercise_number"] == "001" and row["code"] == "1212" and
         row["modes"][0]["mode"] == "A" and
         row["modes"][0]["directions"][0]["direction"] == "shift_up" and
         route["string"] == "E" and route["tab_row"] == lines[52] and
         route["shift_after_note"] == 3 and route["landing_note"] == 4 and
         route["shift_frets"] == 2, "P09_ROUTE_DRIFT")
    need([cell["position"] for cell in route["cells"]] == ["P5", "P7"], "P09_FRAME_DRIFT")
    facts = []
    for cell in route["cells"]:
        for note in cell["notes"]:
            need(note["onset_q"] is note["duration_q"] is None, "P09_UNTIMED_PARITY_DRIFT")
            finger = int(note["finger_digit"])
            facts.append((1, note["fret"], finger, 40 + note["fret"], cell["position"]))
    need(facts == [(1, 5, 1, 45, "P5"), (1, 6, 2, 46, "P5"),
                   (1, 5, 1, 45, "P5"), (1, 8, 2, 48, "P7")], "EVENT_FACT_DRIFT")
    return lines, pages, facts


def derive(*, changed_facts: list | None = None, changed_onsets: list | None = None,
           force_eligible: bool = False, reserved_item: str = ITEM) -> dict[str, dict]:
    need(not force_eligible, "FORCED_ELIGIBILITY")
    need(reserved_item == ITEM, "FOREIGN_ID")
    lines, pages, facts = source_facts()
    need(changed_facts is None or changed_facts == facts, "CANDIDATE_SOURCE_DRIFT")
    onsets = [[0, 1], [1, 4], [1, 2], [3, 4]]
    need(changed_onsets is None or changed_onsets == onsets, "CANDIDATE_TIMING_DRIFT")
    refs = ["L10-TXT1-39-53", "L10-PDF1-p2", "L10-TXT1-1-33", "L10-PDF1-p1"]
    sources = {
        refs[0]: passage(TXT, TXT_SHA, "txt", "\n".join(lines[38:53]), first_line=39, last_line=53),
        refs[1]: passage(PDF, PDF_SHA, "pdf", pages[1], page=2),
        refs[2]: passage(TXT, TXT_SHA, "txt", "\n".join(lines[:33]), first_line=1, last_line=33),
        refs[3]: passage(PDF, PDF_SHA, "pdf", pages[0], page=1),
    }
    events, event_sources, provenance = [], {}, {}
    for index, (string, fret, finger, midi, frame) in enumerate(facts, 1):
        eid = f"{ITEM}:event:{index:04d}"
        onset = Fraction(index - 1, 4)
        events.append({"event_id": eid, "kind": "note", "string": string, "fret": fret,
                       "finger": finger, "midi": midi, "spelling": None, "attack": "picked",
                       "onset_q": [onset.numerator, onset.denominator], "duration_q": [1, 4],
                       "tie_from": None, "degree_contexts": {}})
        event_sources[eid] = refs[0]
        provenance[eid] = {"source_local_event_key": f"L010-S01-MA-EX001:UP:E:{frame}:{index}",
                           "source_txt_ref": refs[0], "source_pdf_ref": refs[1],
                           "source_txt_line": 53, "source_pdf_page": 2,
                           "source_finger_line": 47, "finger_digit": finger,
                           "frame": frame, "fret": fret, "landing_note": index == 4,
                           "timing_ref": refs[2], "timing_pdf_ref": refs[3],
                           "timing_option": "PASS2_connected_straight_sixteenths"}
    variants = []
    for vid, start in zip(VARIANTS, ("D", "U")):
        variants.append({"id": vid, "label": f"mode-A-shift-up-first-E-pass2-{start}-start",
                         "role": "notation_practice", "route": "shift_up_low_E_only_P5_to_P7_3_plus_1",
                         "source_refs": refs, "event_ids": list(event_sources),
                         "pick_start": start, "pick_start_origin": "source_authored",
                         "grouping": {"kind": "source_event_time", "notes_per_beat": None,
                                      "beat_unit_q": None, "marking_factor": [1, 1],
                                      "source_label": "Original TXT line29/PDF page1 Pass2 straight sixteenths"},
                         "accent_policy": "even", "tail_pause": None, "unresolved": []})
    record = {"id": ITEM, "module_id": MODULE, "workbook_id": WORKBOOK,
              "content_revision": 1, "lineage": {"kind": "new"}, "kind": "notation",
              "legacy_level": 10, "status": "converted_candidate", "runtime_eligible": False,
              "title": "Level 10 Exercise 001 Mode A first low-E P5-to-P7 3+1 Pass2 shift",
              "source_refs": refs, "authored_text_refs": refs, "events": events,
              "variants": variants, "resource_requirements": [], "rubric": None,
              "control_scope": {"extent": "complete_selected_case",
                                "local_case": "L010-S01-MA-EX001:UP:E:PASS2",
                                "source_event_count": 4, "basis_refs": refs,
                                "whole_workbook_complete": False,
                                "unresolved": ["Remaining SHIFT UP strings, SHIFT DOWN and Mode B are outside this case.",
                                               "Whole Exercise001, Level10 and runtime admission remain Pending."]},
              "context": {"local_code": "L010-S01-MA-EX001:UP:E:PASS2",
                          "route": "Mode A SHIFT UP first low-E string only; 1-2-1 P5 then 2 P7",
                          "mode": "3+1 late whole-frame shift", "position": "P5_to_P7",
                          "pick_start_variants": ["D", "U"],
                          "pick_start": "learner-selected D or U; uninterrupted alternate picking",
                          "tuning_open_midi": [40, 45, 50, 55, 59, 64], "capo": 0,
                          "source_tempo_rules_ref": refs[2]},
              "timing": {"status": "source_defined", "unit": "quarter", "meter": None,
                         "basis": "Original TXT line29 and PDF page1 Pass2: remove shift pause/accent, connect four notes and select straight sixteenths. Nominal 1/4-quarter grid; ASCII spacing is not timing or sustain."},
              "ambiguities": ["Pass1 eighths with shift pause/accent and Pass2 eighths are excluded; selected Pass2 straight sixteenths are a source option.",
                              "Relative tempo and mastery guidance do not author fixed BPM, credit or measured sustain."],
              "normalization": [{"kind": "representation_metadata", "basis": refs[2],
                                 "text": "Selected Mode A Pass2 connected straight-sixteenth low-E four-note cell. Standard low-E MIDI40 yields45/46/45/48, capo zero. Whole hand/thumb shifts P5 to P7 after event3; event4 is landing note. D/U starts continue through the shift without pause or added accent."}]}
    foundation, base_registry, base_profile = (read(BASE / name) for name in
                                                ("package.json", "identity-registry.json", "expected-profile.json"))
    package = {k: copy.deepcopy(v) for k, v in foundation.items()
               if k not in ("records", "sources", "workbook_catalog")}
    package.update(content_version="curriculum-v1-level010-ex001-first-odd-shift-build-only.1",
                   records=[record], sources=sources)
    entities = [{"id": WORKBOOK, "kind": "workbook", "label": "Legacy Level10", "parent": "fg:course:000001"},
                {"id": MODULE, "kind": "module", "label": "Level10 Exercise001 Mode A first low-E 3+1 Pass2", "parent": WORKBOOK},
                {"id": ITEM, "kind": "item", "label": record["title"], "parent": MODULE},
                *({"id": v["id"], "kind": "variant", "label": v["label"], "parent": ITEM} for v in variants)]
    registry = {"identity_version": base_registry["identity_version"], "rules": base_registry["rules"],
                "entities": [base_registry["entities"][0], *entities]}
    identity_baseline = {"identity_version": registry["identity_version"], "rules": registry["rules"],
                         "entities": [registry["entities"][0]]}
    allocation_baseline = {"version": "control-allocation.1", "authority": "Provisional P23 IDs only; no prior local Level10 allocation", "records": {}}
    lineage_baseline = {"version": "lineage-baseline.1", "records": {}}
    allocation = {"version": "control-allocation.1", "authority": "P23 provisional nonadmitted allocation; P02 canonical re-audit required",
                  "records": {ITEM: {"legacy_level": 10,
                                     "occurrences": {p["source_local_event_key"]: eid for eid, p in provenance.items()},
                                     "variants": {v["label"]: v["id"] for v in variants}}}}
    profile = {k: copy.deepcopy(v) for k, v in base_profile.items()
               if k not in ("reference_package", "reference_registry", "event_sources", "authority_artifacts", "workbook_catalog")}
    profile["degree_roots"] = {}
    profile.update(reference_package=package, reference_registry=registry, event_sources=event_sources)
    profile["authority_artifacts"] = [copy.deepcopy(a) for a in base_profile["authority_artifacts"]
                                      if a["role"] in ("source_manifest", "source_acceptance", "current_schema_freeze")]
    for role, name, value in (("identity_baseline", "identity-baseline.json", identity_baseline),
                              ("allocation_baseline", "allocation-baseline.json", allocation_baseline),
                              ("lineage_baseline", "lineage-baseline.json", lineage_baseline),
                              ("candidate_identity_allocation", "candidate-allocation.json", allocation)):
        profile["authority_artifacts"].append({"path": str(OUT / name), "role": role,
                                               "sha256": sha(encode(value))})
    need(set(event_sources) == set(provenance) == {e["event_id"] for e in events}, "EVENT_PROVENANCE_COVERAGE")
    need(set(sources) == set(refs), "SOURCE_REF_COVERAGE")
    summary = {"status": "source_interpreted_nonadmitted_reference", "item_id": ITEM,
               "variant_ids": list(VARIANTS), "event_count": 4, "admitted": False,
               "runtime_eligible": False, "whole_workbook_complete": False,
               "source_txt_sha256": TXT_SHA, "source_pdf_sha256": PDF_SHA,
               "p09_parity_sha256": P09_SHA, "identity_audit_sha256": AUDIT_SHA,
               "selected_option": "PASS2_connected_straight_sixteenths",
               "interpretation": "Mode A first low-E P5-to-P7 3+1 shift; D/U starts; independent source review required"}
    return {"package.json": package, "identity-registry.json": registry,
            "expected-profile.json": profile, "candidate-allocation.json": allocation,
            "identity-baseline.json": identity_baseline, "allocation-baseline.json": allocation_baseline,
            "lineage-baseline.json": lineage_baseline,
            "source-provenance.json": {"source_txt_ref": refs[0], "source_pdf_ref": refs[1],
                                       "timing_txt_ref": refs[2], "timing_pdf_ref": refs[3],
                                       "events": provenance,
                                       "variant_strokes": {VARIANTS[0]: ["D", "U", "D", "U"],
                                                           VARIANTS[1]: ["U", "D", "U", "D"]},
                                       "stroke_basis": "Original TXT lines22,24,42 and PDF pages1-2: alternate picking continues without reset through the late shift."},
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
