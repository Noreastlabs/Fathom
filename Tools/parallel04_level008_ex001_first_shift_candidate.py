#!/usr/bin/env python3
"""Build one source-closed, nonadmitted Level 8 first-shift reference."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = Path("Build/parallel-04/controlled-open-level008-r01")
TXT = Path("Notes/music/guitar project/TXT version/108_Finger_Permutations_Level_8_Two_Position_Ladder.txt")
PDF = Path("Notes/music/guitar project/PDF version/108_Finger_Permutations_Level_8_Two_Position_Ladder.pdf")
P07 = Path("Build/parallel-07/2.3.1.1.1-level008-set01-r01/candidate.json")
AUDIT = Path("Build/parallel-02/controlled-open-level008-assignment-r01/identity-audit.json")
BASE = Path("Content/controls/curriculum-v1")
TXT_SHA = "0cba6885ed917013d5ceda5e0c231c568b4aa99be4c8c0e23941295a3fa5926a"
PDF_SHA = "750f9b14962e71bc9ed0dc48a6f9343f2a1d5d14363858f7b9462187fc338829"
P07_SHA = "2ce7da17ec0b633950af15718c6319317ccfbd2085fbc2046a9b1d58873c1f51"
AUDIT_SHA = "e7cf78dbb8c172a800cd4bb369caf5e7ea9d22e9c8b0d3d7183a78a5c6b28708"
ITEM = "fg:item:001146"
MODULE = "fg:module:001146"
VARIANTS = ("fg:variant:007414", "fg:variant:007415")
WORKBOOK = "fg:workbook:000008"
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


def source_facts() -> tuple[list[str], list[str], list[tuple[int, int, int, int, str]]]:
    from pypdf import PdfReader

    need(sha((ROOT / TXT).read_bytes()) == TXT_SHA, "TXT_PIN_DRIFT")
    need(sha((ROOT / PDF).read_bytes()) == PDF_SHA, "PDF_PIN_DRIFT")
    need(sha((ROOT / P07).read_bytes()) == P07_SHA, "P07_PIN_DRIFT")
    need(sha((ROOT / AUDIT).read_bytes()) == AUDIT_SHA, "AUDIT_PIN_DRIFT")
    audit = read(AUDIT)
    need(audit["status"] == "PASS" and not audit["matches"] and
         set(audit["wanted"]) == {ITEM, MODULE, *VARIANTS}, "ID_RESERVATION_DRIFT")
    lines = (ROOT / TXT).read_text().splitlines()
    pages = [p.extract_text() or "" for p in PdfReader(str(ROOT / PDF)).pages]
    need(len(pages) == 10, "PDF_PAGE_COUNT")
    need(lines[30] == "Exercise 001: 1212" and
         lines[31].startswith("SHIFT UP - P5 to P7; play bottom line first") and
         lines[37] == "E|5-6-5-6----|7-8-7-8----|", "TXT_FIRST_ROUTE_DRIFT")
    need("shift occurs only between complete four-note cells" in " ".join(lines[5:11]) and
         "one string at a time" in " ".join(lines[5:12]) and
         "repeat the same code in seventh position" in " ".join(lines[5:11]),
         "TXT_MOVEMENT_DRIFT")
    need("Second pass: remove the pause and accent, then convert the 4+4 phrase to straight 16ths." in lines[20] and
         "Play both routes with a downstroke start, then repeat with an upstroke start." in lines[21] and
         "second cell begins with the same pick direction" in " ".join(lines[21:24]),
         "TXT_PASS2_TIMING_DRIFT")
    need("PASS 2" in pages[0] and "Remove the pause and accent" in pages[0] and
         "straight sixteenths" in pages[0] and "notes are not played as a" in pages[0] and
         "No scrape, slide, pause, or extra accent" in pages[0], "PDF_PASS2_DRIFT")
    need("001   1212" in pages[1] and "S|5-6-5-6----|7-8-7-8----|" in pages[1] and
         "shift at the center barline" in pages[1] and "E>A>D>G>B>e" in pages[1],
         "PDF_EX001_DRIFT")
    row = read(P07)["records"][0]
    route = row["directions"][0]["routes"][0]
    need(row["exercise_number"] == "001" and row["code"] == "1212" and
         row["source_local_key"] == "L8-set01-ex001" and
         route["string"] == "E" and route["source_tab_row"] == lines[37] and
         route["shift_after_cell"] == 1 and route["hand_frame_shift_frets"] == 2,
         "P07_ROUTE_DRIFT")
    need([c["position"] for c in route["cells"]] == ["P5", "P7"], "P07_FRAME_DRIFT")
    facts = []
    for cell_index, cell in enumerate(route["cells"]):
        for note in cell["notes"]:
            finger = int(note["finger_digit"])
            fret = note["fret"]
            facts.append((1, fret, finger, 40 + fret, cell["position"]))
            need(note["onset_q"] is note["duration_q"] is None, "P07_UNTIMED_PARITY_DRIFT")
            need(fret == (5 if cell_index == 0 else 7) + finger - 1, "P07_FINGER_MAP_DRIFT")
    need(facts == [(1, 5, 1, 45, "P5"), (1, 6, 2, 46, "P5"),
                   (1, 5, 1, 45, "P5"), (1, 6, 2, 46, "P5"),
                   (1, 7, 1, 47, "P7"), (1, 8, 2, 48, "P7"),
                   (1, 7, 1, 47, "P7"), (1, 8, 2, 48, "P7")], "EVENT_FACT_DRIFT")
    return lines, pages, facts


def derive(*, changed_facts: list | None = None, force_eligible: bool = False,
           reserved_item: str = ITEM) -> dict[str, dict]:
    need(not force_eligible, "FORCED_ELIGIBILITY")
    need(reserved_item == ITEM, "ID_RESERVATION_DRIFT")
    lines, pages, facts = source_facts()
    need(changed_facts is None or changed_facts == facts, "CANDIDATE_SOURCE_DRIFT")
    refs = ["L8-TXT1-31-38", "L8-PDF1-p2", "L8-TXT1-1-25", "L8-PDF1-p1"]
    sources = {
        refs[0]: passage(TXT, TXT_SHA, "txt", "\n".join(lines[30:38]), first_line=31, last_line=38),
        refs[1]: passage(PDF, PDF_SHA, "pdf", pages[1], page=2),
        refs[2]: passage(TXT, TXT_SHA, "txt", "\n".join(lines[:25]), first_line=1, last_line=25),
        refs[3]: passage(PDF, PDF_SHA, "pdf", pages[0], page=1),
    }
    events = []
    event_sources = {}
    provenance = {}
    for index, (string, fret, finger, midi, frame) in enumerate(facts, 1):
        eid = f"{ITEM}:event:{index:04d}"
        onset = Fraction(index - 1, 4)
        events.append({"event_id": eid, "kind": "note", "string": string, "fret": fret,
                       "finger": finger, "midi": midi, "spelling": None, "attack": "picked",
                       "onset_q": [onset.numerator, onset.denominator], "duration_q": [1, 4],
                       "tie_from": None, "degree_contexts": {}})
        event_sources[eid] = refs[0]
        provenance[eid] = {"source_local_event_key": f"L008-S01-EX001:UP:E:{frame}:{(index - 1) % 4 + 1}",
                           "source_txt_ref": refs[0], "source_pdf_ref": refs[1],
                           "source_txt_line": 38, "source_pdf_page": 2,
                           "frame": frame, "cell": 1 if index <= 4 else 2,
                           "finger_digit": finger, "fret": fret,
                           "timing_ref": refs[2], "timing_pdf_ref": refs[3],
                           "timing_option": "PASS2_connected_straight_sixteenths"}
    variants = []
    for vid, start in zip(VARIANTS, ("D", "U")):
        variants.append({"id": vid, "label": f"first-E-string-P5-P7-pass2-{start}-start",
                         "role": "notation_practice", "route": "shift_up_low_E_only_P5_to_P7",
                         "source_refs": refs, "event_ids": list(event_sources),
                         "pick_start": start, "pick_start_origin": "source_authored",
                         "grouping": {"kind": "source_event_time", "notes_per_beat": None,
                                      "beat_unit_q": None, "marking_factor": [1, 1],
                                      "source_label": "Original TXT line21/PDF page1 PASS2 straight sixteenths"},
                         "accent_policy": "even", "tail_pause": None, "unresolved": []})
    record = {"id": ITEM, "module_id": MODULE, "workbook_id": WORKBOOK,
              "content_revision": 1, "lineage": {"kind": "new"}, "kind": "notation",
              "legacy_level": 8, "status": "converted_candidate", "runtime_eligible": False,
              "title": "Level 8 Exercise 001 first low-E P5-to-P7 PASS2 shift",
              "source_refs": refs, "authored_text_refs": refs, "events": events,
              "variants": variants, "resource_requirements": [], "rubric": None,
              "control_scope": {"extent": "complete_selected_case",
                                "local_case": "L008-S01-EX001:UP:E:PASS2",
                                "source_event_count": 8, "basis_refs": refs,
                                "whole_workbook_complete": False,
                                "unresolved": ["Remaining five-string SHIFT UP and all SHIFT DOWN routes remain outside this selected case.",
                                               "Whole Exercise001, Level8 and Curriculum/runtime admission remain Pending."]},
              "context": {"local_code": "L008-S01-EX001:UP:E:PASS2",
                          "route": "SHIFT UP first low-E string only; complete P5 cell then P7 cell",
                          "mode": "two-position 4+4 whole-pattern shift", "position": "P5_to_P7",
                          "pick_start_variants": ["D", "U"],
                          "pick_start": "learner-selected D or U; alternate strokes across eight notes",
                          "tuning_open_midi": [40, 45, 50, 55, 59, 64], "capo": 0,
                          "source_tempo_rules_ref": refs[2]},
              "timing": {"status": "source_defined", "unit": "quarter", "meter": None,
                         "basis": "Original TXT line21 and PDF page1 PASS2: remove center pause/accent, connect 4+4 and convert to straight sixteenths. Each event occupies 1/4 quarter; ASCII spacing is not timing."},
              "ambiguities": ["PASS1 even eighths plus a center subdivision is a different source option and is excluded.",
                              "Relative tempo guidance does not author a fixed BPM; no mastery or credit is inferred."],
              "normalization": [{"kind": "representation_metadata", "basis": refs[2],
                                 "text": "Selected PASS2 connected straight-sixteenth option. Low-E open MIDI40 in standard tuning yields MIDI45/46/45/46 then47/48/47/48; capo zero. Whole hand frame shifts after event4; no center pause or accent. D/U starts are source-authored."}]}
    foundation = read(BASE / "package.json")
    base_registry = read(BASE / "identity-registry.json")
    base_profile = read(BASE / "expected-profile.json")
    package = {k: copy.deepcopy(v) for k, v in foundation.items()
               if k not in ("records", "sources", "workbook_catalog")}
    package.update(content_version="curriculum-v1-level008-ex001-first-shift-build-only.1",
                   records=[record], sources=sources)
    entities = [{"id": WORKBOOK, "kind": "workbook", "label": "Legacy Level8", "parent": "fg:course:000001"},
                {"id": MODULE, "kind": "module", "label": "Level8 Exercise001 first low-E P5-P7 PASS2", "parent": WORKBOOK},
                {"id": ITEM, "kind": "item", "label": record["title"], "parent": MODULE},
                *({"id": v["id"], "kind": "variant", "label": v["label"], "parent": ITEM} for v in variants)]
    registry = {"identity_version": base_registry["identity_version"], "rules": base_registry["rules"],
                "entities": [base_registry["entities"][0], *entities]}
    identity_baseline = {"identity_version": registry["identity_version"], "rules": registry["rules"],
                         "entities": [registry["entities"][0]]}
    allocation_baseline = {"version": "control-allocation.1", "authority": "P02 reserved IDs; no prior local Level8 allocation", "records": {}}
    lineage_baseline = {"version": "lineage-baseline.1", "records": {}}
    allocation = {"version": "control-allocation.1", "authority": "P02 provisional reservation; nonadmitted candidate only",
                  "records": {ITEM: {"legacy_level": 8,
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
    summary = {"status": "source_interpreted_nonadmitted_reference", "item_id": ITEM,
               "variant_ids": list(VARIANTS), "event_count": 8, "admitted": False,
               "runtime_eligible": False, "whole_workbook_complete": False,
               "source_txt_sha256": TXT_SHA, "source_pdf_sha256": PDF_SHA,
               "p07_parity_sha256": P07_SHA, "identity_audit_sha256": AUDIT_SHA,
               "selected_option": "PASS2_connected_straight_sixteenths",
               "interpretation": "one low-E P5-to-P7 connected 4+4 shift; D/U starts; independent review required"}
    return {"package.json": package, "identity-registry.json": registry,
            "expected-profile.json": profile, "candidate-allocation.json": allocation,
            "identity-baseline.json": identity_baseline, "allocation-baseline.json": allocation_baseline,
            "lineage-baseline.json": lineage_baseline,
            "source-provenance.json": {"source_txt_ref": refs[0], "source_pdf_ref": refs[1],
                                       "timing_txt_ref": refs[2], "timing_pdf_ref": refs[3],
                                       "events": provenance,
                                       "variant_strokes": {VARIANTS[0]: ["D", "U"] * 4,
                                                           VARIANTS[1]: ["U", "D"] * 4},
                                       "stroke_basis": "Original TXT lines22-23: both starts and same direction at second cell; alternate picking is the selected performance interpretation."},
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
