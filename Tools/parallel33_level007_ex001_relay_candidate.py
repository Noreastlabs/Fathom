#!/usr/bin/env python3
"""Build one source-closed, nonadmitted Level 7 connected skip-relay reference."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = Path("Build/parallel-33/controlled-open-level007-ex001-r01")
TXT = Path("Notes/music/guitar project/TXT version/108_Finger_Permutations_Level_7_Three_String_Skip_Relay.txt")
PDF = Path("Notes/music/guitar project/PDF version/108_Finger_Permutations_Level_7_Three_String_Skip_Relay.pdf")
P10 = Path("Build/parallel-10/level007-shard-reference-r02/package.json")
AUDIT = OUT / "identity-audit.json"
BASE = Path("Content/controls/curriculum-v1")
TXT_SHA = "467d1401237e34633efc4c517fa98d8190f0b47346a7b34be9d2548924883b61"
PDF_SHA = "5c8607cff40801acb13f5e08dd2988b2ff943593eb084de2801f05f507a6c4ea"
P10_SHA = "a9cfaa7b0c86fd8d4e089b0ba86913f6e18ca3a33f1f8cddca1897ea017f4732"
AUDIT_SHA = "9036c957322c34cc348af4892306e97caf8292d984171e9941a5d78aad84c4f9"
ITEM = "fg:item:001148"
MODULE = "fg:module:001148"
VARIANTS = ("fg:variant:007418", "fg:variant:007419")
WORKBOOK = "fg:workbook:000007"
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


def source_facts() -> tuple[list[str], list[str], list[tuple[int, int, int, int, str, int]]]:
    from pypdf import PdfReader

    need(sha((ROOT / TXT).read_bytes()) == TXT_SHA, "TXT_PIN_DRIFT")
    need(sha((ROOT / PDF).read_bytes()) == PDF_SHA, "PDF_PIN_DRIFT")
    need(sha((ROOT / P10).read_bytes()) == P10_SHA, "P10_PIN_DRIFT")
    need(sha((ROOT / AUDIT).read_bytes()) == AUDIT_SHA, "AUDIT_PIN_DRIFT")
    audit = read(AUDIT)
    need(audit["status"] == "PASS" and not audit["matches"] and
         audit["json_files_scanned"] >= 10000 and
         set(audit["wanted"]) == {ITEM, MODULE, *VARIANTS}, "IDENTITY_AUDIT_DRIFT")

    lines = (ROOT / TXT).read_text().splitlines()
    pages = [p.extract_text() or "" for p in PdfReader(str(ROOT / PDF)).pages]
    need(len(pages) == 10, "PDF_PAGE_COUNT")
    need(lines[1].startswith("1+2+1 double-gap crossing") and
         lines[2].startswith("Fifth position: 1=index/fret 5") and
         lines[5].startswith("Play code note 1 on the first played string") and
         "Leave one physical string silent" in lines[6] and
         lines[7].endswith("Descend through e-G-A and B-D-E.") and
         lines[8].endswith("The four-digit code order never changes."),
         "TXT_MOVEMENT_DRIFT")
    need(lines[17] == "Play ASCEND directly into DESCEND, then repeat the entire exercise with the opposite starting pick stroke." and
         lines[20] == "Second pass: connect the route, remove the accents, and equalize all four notes in volume, timing, and duration." and
         lines[21].startswith("Use straight 16ths first."), "TXT_PASS2_DRIFT")
    tab = ["Exercise 001: 1212", "ASCEND - E-D-B, A-G-e",
           "e|--------|------6-|", "B|------6-|--------|", "G|--------|--6-5---|",
           "D|--6-5---|--------|", "A|--------|5-------|", "E|5-------|--------|",
           "DESCEND - e-G-A, B-D-E", "e|5-------|--------|", "B|--------|5-------|",
           "G|--6-5---|--------|", "D|--------|--6-5---|", "A|------6-|--------|",
           "E|--------|------6-|"]
    need(lines[29:44] == tab, "TXT_EX001_TAB_DRIFT")
    pdf_case = pages[1].split("001   1212", 1)[-1].split("002   1213", 1)[0]
    need("001   1212" in pages[1] and "UP" in pdf_case and "DN" in pdf_case and
         all(row in pdf_case for row in tab[2:8] + tab[9:15]), "PDF_EX001_TAB_DRIFT")
    need("Second pass: equalize all four notes." in pages[0] and
         "PASS 2" in pages[0] and "Connect the route" in pages[0] and
         "downstroke start" in pages[0] and "upstroke start" in pages[0] and
         "one silent string" in pages[0], "PDF_RULE_DRIFT")

    # Ordered notes come from the checked TXT/PDF TAB and the checked 1212 finger map.
    # Group labels are representation metadata; all four groups remain connected.
    string_fret_group_line = [
        (1,5,"ASC-E-D-B",37),(3,6,"ASC-E-D-B",35),(3,5,"ASC-E-D-B",35),(5,6,"ASC-E-D-B",33),
        (2,5,"ASC-A-G-e",36),(4,6,"ASC-A-G-e",34),(4,5,"ASC-A-G-e",34),(6,6,"ASC-A-G-e",32),
        (6,5,"DESC-e-G-A",39),(4,6,"DESC-e-G-A",41),(4,5,"DESC-e-G-A",41),(2,6,"DESC-e-G-A",43),
        (5,5,"DESC-B-D-E",40),(3,6,"DESC-B-D-E",42),(3,5,"DESC-B-D-E",42),(1,6,"DESC-B-D-E",44),
    ]
    opens = [40,45,50,55,59,64]
    facts = [(string,fret,(1,2,1,2)[i%4],opens[string-1]+fret,group,line)
             for i,(string,fret,group,line) in enumerate(string_fret_group_line)]
    prior = read(P10)["records"][0]
    need(prior["title"] == "Exercise 001: 1212" and
         [(e["string"],e["fret"],e["finger"],e["midi"]) for e in prior["events"]] ==
         [f[:4] for f in facts] and
         all(e["onset_q"] is e["duration_q"] is None for e in prior["events"]),
         "P10_UNTIMED_PARITY_DRIFT")
    return lines, pages, facts


def derive(*, changed_facts: list | None = None, changed_onsets: list | None = None,
           changed_durations: list | None = None, changed_strokes: dict | None = None,
           force_eligible: bool = False, reserved_item: str = ITEM) -> dict[str, dict]:
    need(not force_eligible, "FORCED_ELIGIBILITY")
    need(reserved_item == ITEM, "FOREIGN_ID")
    lines, pages, facts = source_facts()
    need(changed_facts is None or changed_facts == facts, "CANDIDATE_SOURCE_DRIFT")
    # Canonical rational encoding: 0, 1/4, 1/2, ... 15/4.
    onsets = [[Fraction(i,4).numerator, Fraction(i,4).denominator] for i in range(16)]
    need(changed_onsets is None or changed_onsets == onsets, "CANDIDATE_TIMING_DRIFT")
    durations = [[1,4]] * 16
    need(changed_durations is None or changed_durations == durations, "CANDIDATE_DURATION_DRIFT")
    strokes = {VARIANTS[0]: ["D","U"]*8, VARIANTS[1]: ["U","D"]*8}
    need(changed_strokes is None or changed_strokes == strokes, "CANDIDATE_STROKE_DRIFT")
    refs = ["L7-TXT1-30-44", "L7-PDF1-p2", "L7-TXT1-1-24", "L7-PDF1-p1"]
    sources = {
        refs[0]: passage(TXT, TXT_SHA, "txt", "\n".join(lines[29:44]), first_line=30, last_line=44),
        refs[1]: passage(PDF, PDF_SHA, "pdf", pages[1], page=2),
        refs[2]: passage(TXT, TXT_SHA, "txt", "\n".join(lines[:24]), first_line=1, last_line=24),
        refs[3]: passage(PDF, PDF_SHA, "pdf", pages[0], page=1),
    }
    events, event_sources, provenance = [], {}, {}
    for index,(string,fret,finger,midi,group,line) in enumerate(facts,1):
        eid=f"{ITEM}:event:{index:04d}"
        events.append({"event_id":eid,"kind":"note","string":string,"fret":fret,
                       "finger":finger,"midi":midi,"spelling":None,"attack":"picked",
                       "onset_q":onsets[index-1],"duration_q":durations[index-1],
                       "tie_from":None,"degree_contexts":{}})
        event_sources[eid]=refs[0]
        provenance[eid]={"source_local_event_key":f"L007-S01-EX001:PASS2:{group}:{index:02d}",
                         "source_txt_ref":refs[0],"source_pdf_ref":refs[1],
                         "source_txt_line":line,"source_pdf_page":2,
                         "source_finger_ref":refs[2],"source_finger_line":3,
                         "finger_digit":finger,"fret":fret,"string":string,
                         "route_group":group,"group_event_number":((index-1)%4)+1,
                         "gap_landing":((index-1)%4) in (1,3),
                         "timing_ref":refs[2],"timing_pdf_ref":refs[3],
                         "timing_option":"PASS2_connected_straight_sixteenths"}
    variants=[]
    for vid,start in zip(VARIANTS,("D","U")):
        variants.append({"id":vid,"label":f"ex001-connected-pass2-{start}-start",
                         "role":"notation_practice","route":"ascend_E-D-B_A-G-e_then_descend_e-G-A_B-D-E",
                         "source_refs":refs,"event_ids":list(event_sources),
                         "pick_start":start,"pick_start_origin":"learner_configuration",
                         "grouping":{"kind":"source_event_time","notes_per_beat":None,
                                     "beat_unit_q":None,"marking_factor":[1,1],
                                     "source_label":"TXT line22 straight 16ths; PDF page1 Pass2 connected route"},
                         "accent_policy":"even","tail_pause":None,"unresolved":[]})
    record={"id":ITEM,"module_id":MODULE,"workbook_id":WORKBOOK,
            "content_revision":1,"lineage":{"kind":"new"},"kind":"notation",
            "legacy_level":7,"status":"converted_candidate","runtime_eligible":False,
            "title":"Level 7 Exercise 001 1212 connected skip relay Pass2",
            "source_refs":refs,"authored_text_refs":refs,"events":events,"variants":variants,
            "resource_requirements":[],"rubric":None,
            "control_scope":{"extent":"complete_selected_case",
                             "local_case":"L007-S01-EX001:ASC-DESC:PASS2",
                             "source_event_count":16,"basis_refs":refs,
                             "whole_workbook_complete":False,
                             "unresolved":["Pass1, triplet/quintuplet options and Exercises002-108 are outside this selected case.",
                                           "Whole Level7, runtime admission and learner performance remain Pending."]},
            "context":{"local_code":"L007-S01-EX001:ASC-DESC:PASS2",
                       "route":"ASC E-D-B then A-G-e directly into DESC e-G-A then B-D-E",
                       "position":"fifth","pick_start_variants":["D","U"],
                       "pick_start":"learner-selected D or U; continuous alternate-picking interpretation",
                       "tuning_open_midi":[40,45,50,55,59,64],"capo":0,
                       "source_tempo_rules_ref":refs[2]},
            "timing":{"status":"source_defined","unit":"quarter","meter":None,
                      "basis":"TXT lines18,21-22: direct ASCEND into DESCEND; selected Pass2 connected/even straight 16ths. PDF page1 confirms connected Pass2 but does not restate 16ths. Nominal 1/4-quarter grid, not measured sustain."},
            "ambiguities":["D/U starts are source-authored; per-note alternate strokes are a conservative selected interpretation for review, not separately printed per event.",
                           "No authored fixed BPM or confirmed silent strings; Pass1 and triplet/quintuplet options are excluded.",
                           "Capo zero is a validator representation of untransposed standard tuning, not an instruction to use a capo."],
            "normalization":[{"kind":"representation_metadata","basis":refs[2],
                              "text":"Selected full 16-note Pass2 route, four 1+2+1 groups, source fingers 1-2-1-2 repeated; open-string MIDI yields note pitches. 1/4-quarter nominal slots use TXT straight-16ths option; D/U alternate from chosen start without an added group reset/accent."}]}
    foundation,base_registry,base_profile=(read(BASE/name) for name in
        ("package.json","identity-registry.json","expected-profile.json"))
    package={k:copy.deepcopy(v) for k,v in foundation.items()
             if k not in ("records","sources","workbook_catalog")}
    package.update(content_version="curriculum-v1-level007-ex001-relay-pass2-build-only.1",
                   records=[record],sources=sources)
    entities=[{"id":WORKBOOK,"kind":"workbook","label":"Legacy Level7","parent":"fg:course:000001"},
              {"id":MODULE,"kind":"module","label":"Level7 Exercise001 connected Pass2 relay","parent":WORKBOOK},
              {"id":ITEM,"kind":"item","label":record["title"],"parent":MODULE},
              *({"id":v["id"],"kind":"variant","label":v["label"],"parent":ITEM} for v in variants)]
    registry={"identity_version":base_registry["identity_version"],"rules":base_registry["rules"],
              "entities":[base_registry["entities"][0],*entities]}
    identity_baseline={"identity_version":registry["identity_version"],"rules":registry["rules"],
                       "entities":[registry["entities"][0]]}
    allocation_baseline={"version":"control-allocation.1","authority":"P33 provisional only; no prior local Level7 allocation","records":{}}
    lineage_baseline={"version":"lineage-baseline.1","records":{}}
    allocation={"version":"control-allocation.1","authority":"P33 provisional nonadmitted allocation; P02 canonical re-audit required",
                "records":{ITEM:{"legacy_level":7,
                                 "occurrences":{p["source_local_event_key"]:eid for eid,p in provenance.items()},
                                 "variants":{v["label"]:v["id"] for v in variants}}}}
    profile={k:copy.deepcopy(v) for k,v in base_profile.items()
             if k not in ("reference_package","reference_registry","event_sources","authority_artifacts","workbook_catalog")}
    profile["degree_roots"]={}
    profile.update(reference_package=package,reference_registry=registry,event_sources=event_sources)
    profile["authority_artifacts"]=[copy.deepcopy(a) for a in base_profile["authority_artifacts"]
                                    if a["role"] in ("source_manifest","source_acceptance","current_schema_freeze")]
    for role,name,value in (("identity_baseline","identity-baseline.json",identity_baseline),
                            ("allocation_baseline","allocation-baseline.json",allocation_baseline),
                            ("lineage_baseline","lineage-baseline.json",lineage_baseline),
                            ("candidate_identity_allocation","candidate-allocation.json",allocation)):
        profile["authority_artifacts"].append({"path":str(OUT/name),"role":role,
                                               "sha256":sha(encode(value))})
    need(set(event_sources)==set(provenance)=={e["event_id"] for e in events},"EVENT_PROVENANCE_COVERAGE")
    need(set(sources)==set(refs),"SOURCE_REF_COVERAGE")
    summary={"status":"source_interpreted_nonadmitted_reference","item_id":ITEM,
             "variant_ids":list(VARIANTS),"event_count":16,"admitted":False,
             "runtime_eligible":False,"whole_workbook_complete":False,
             "source_txt_sha256":TXT_SHA,"source_pdf_sha256":PDF_SHA,
             "p10_parity_sha256":P10_SHA,"identity_audit_sha256":AUDIT_SHA,
             "selected_option":"PASS2_connected_straight_sixteenths",
             "interpretation":"Four 1+2+1 groups, ASC directly into DESC; D/U starts; independent source review required"}
    return {"package.json":package,"identity-registry.json":registry,
            "expected-profile.json":profile,"candidate-allocation.json":allocation,
            "identity-baseline.json":identity_baseline,"allocation-baseline.json":allocation_baseline,
            "lineage-baseline.json":lineage_baseline,
            "source-provenance.json":{"source_txt_ref":refs[0],"source_pdf_ref":refs[1],
                                      "timing_txt_ref":refs[2],"timing_pdf_ref":refs[3],
                                      "events":provenance,"variant_strokes":strokes,
                                      "stroke_basis":"TXT line18 and PDF page1 require both D/U starts; continuous alternation is the selected bounded performance interpretation and needs independent review."},
            "summary.json":summary}


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
