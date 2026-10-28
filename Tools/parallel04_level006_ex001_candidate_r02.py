#!/usr/bin/env python3
"""Build the source-closed r02 Level 6 Exercise 001 string-skip cell."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = Path("Build/parallel-04/controlled-open-level006-r02")
TXT = Path("Notes/music/guitar project/TXT version/108_Finger_Permutations_Level_6_Odd_Count_String_Skip_Transfer.txt")
PDF = Path("Notes/music/guitar project/PDF version/108_Finger_Permutations_Level_6_Odd_Count_String_Skip_Transfer.pdf")
PROPOSAL = Path("Build/parallel-03/level006-schema1-unallocated-r01/field-proposal-a.json")
AUDIT = Path("Build/parallel-02/controlled-open-r01/identity-audit.json")
BASE = Path("Content/controls/curriculum-v1")
TXT_SHA = "bbd337b205eac66e474b7b90dea7c5e18c35fe6f09eec7aee3a058f1c0eb4d19"
PDF_SHA = "a2b97e01ad98bc4e01dfeccfb799b19a5c3c712c233cc9def5e8d95ca16aaac8"
PROPOSAL_SHA = "f6ae33d7ac3220d267adc2ae87a0000f60149564035edf7fec90d4618c10da99"
AUDIT_SHA = "08ddc1dda01463f6161017d5f792c3cde3d99d84b305e4e0ebb1ecd572fb3586"
ITEM = "fg:item:001144"
MODULE = "fg:module:001144"
VARIANTS = ("fg:variant:007410", "fg:variant:007411")
NAMES = ("package.json", "identity-registry.json", "expected-profile.json", "candidate-allocation.json",
         "identity-baseline.json", "allocation-baseline.json", "lineage-baseline.json", "source-provenance.json", "summary.json")


class CandidateError(ValueError):
    pass


def need(condition: bool, code: str) -> None:
    if not condition:
        raise CandidateError(code)


def encode(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n").encode()


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def read(root: Path, path: Path) -> dict:
    return json.loads((root / path).read_bytes())


def checked_source(root: Path) -> tuple[list[str], list[str]]:
    from pypdf import PdfReader

    need(sha((root / TXT).read_bytes()) == TXT_SHA, "TXT_PIN_DRIFT")
    need(sha((root / PDF).read_bytes()) == PDF_SHA, "PDF_PIN_DRIFT")
    lines = (root / TXT).read_text().splitlines()
    pages = [page.extract_text() or "" for page in PdfReader(str(root / PDF)).pages]
    need(len(pages) == 19, "PDF_PAGE_COUNT")
    need(lines[33].strip() == "Exercise 001: 1212" and
         lines[38].strip() == "D|------6-|--------|5-6-5---|--------|" and
         lines[39].strip() == "A|--------|5-6-5---|--------|--------|" and
         lines[40].strip() == "E|5-6-5---|--------|--------|--------|", "TXT_CELL_DRIFT")
    need("Start with separated four-note cells" in "\n".join(lines[14:23]) and
         "straight-16th, triplet, and quintuplet" in lines[20] and
         "once beginning with a downstroke and once beginning with an upstroke" in lines[16] and
         "alternate-picking timing" in "\n".join(lines[10:14]), "TXT_TIMING_PICKING_SUPPORT")
    need("001   1212" in pages[1] and "E|5-6-5---" in pages[1] and
         "D|------6-|" in pages[1] and "A|--------|" in pages[1] and
         "Begin with separated four-note cells" in pages[0] and
         "downstroke start and then with an upstroke start" in pages[0], "PDF_CELL_PICKING_PARITY")
    return lines, pages


def passage(path: Path, digest: str, fmt: str, text: str, **where: int) -> dict:
    return {"path": str(path), "sha256": digest, "format": fmt, **where,
            "text": text, "text_sha256": sha(text.encode())}


def check_event_source_closure(record: dict, sources: dict, event_sources: dict, provenance_by_event: dict) -> None:
    need(set(provenance_by_event) == set(event_sources) == {e["event_id"] for e in record["events"]},
         "EVENT_SOURCE_COVERAGE")
    for eid, provenance in provenance_by_event.items():
        ref = provenance["source_txt_ref"]
        need(ref == event_sources[eid] and ref in sources and ref in record["source_refs"] and
             sources[ref]["first_line"] == 34 and sources[ref]["last_line"] == 41 and
             provenance["source_pdf_page"] == sources["L6-PDF1-p2"]["page"],
             "EVENT_SOURCE_CLOSURE")


def derive(root: Path = ROOT, override: dict | None = None, force_eligible: bool = False) -> dict[str, dict]:
    need(root.resolve() == ROOT.resolve(), "ROOT_DRIFT")
    need(not force_eligible, "FORCED_ELIGIBILITY")
    lines, pages = checked_source(root)
    need(sha((root / PROPOSAL).read_bytes()) == PROPOSAL_SHA, "PROPOSAL_PIN_DRIFT")
    need(sha((root / AUDIT).read_bytes()) == AUDIT_SHA, "AUDIT_PIN_DRIFT")
    proposal = read(root, PROPOSAL)
    row = proposal["records"][0]
    need(row["exercise_number"] == 1 and row["mode"] == "A" and row["pattern_code"] == "1212", "PROPOSAL_SCOPE")
    first = row["schema1_fields"]["events"][:4]
    facts = [(1, 5, 1, 45), (1, 6, 2, 46), (1, 5, 1, 45), (3, 6, 2, 56)]
    need([(e["string"], e["fret"], e["finger"], e["midi"]) for e in first] == facts and
         all(e["source_local_provenance"]["silent_intervening_string"] == "A" for e in first),
         "PROPOSAL_CELL_PARITY")
    need(override is None or override == row["schema1_fields"], "CANDIDATE_SOURCE_DRIFT")
    record = copy.deepcopy(row["schema1_fields"])
    record["events"] = record["events"][:4]
    record.update(id=ITEM, module_id=MODULE, workbook_id="fg:workbook:000006",
                  content_revision=1, lineage={"kind": "new"}, runtime_eligible=False,
                  title="Level 6 Exercise 001 Mode A first E-D separated cell",
                  status="converted_candidate")
    refs = ["L6-TXT1-34-41", "L6-PDF1-p2", "L6-TXT1-1-23", "L6-PDF1-p1"]
    record["source_refs"] = refs
    record["authored_text_refs"] = refs
    record["control_scope"].update(extent="complete_selected_case",
                                     source_event_count=4, basis_refs=refs,
                                     unresolved=["Whole route and Curriculum/runtime admission remain Pending."])
    record["context"] = {"local_code": "L006-S01-MODE-A-EX-001:ascending:cell-01",
                         "route": "one separated ascending E-D cell; A string silent",
                         "mode": "3+1 late skip", "position": "fifth",
                         "pick_start": "D or U selected by learner; alternate strokes through four notes",
                         "pick_start_variants": ["D", "U"],
                         "tuning_open_midi": [40, 45, 50, 55, 59, 64], "capo": 0,
                         "source_tempo_rules_ref": "L6-TXT1-1-23"}
    record["timing"] = {"status": "source_defined", "unit": "quarter",
                        "basis": "Original TXT lines 20-21: separated four-note cells and straight-16th session option; four equal sixteenth-note spans are the selected interpretation. ASCII columns are not timing.",
                        "meter": None}
    record["ambiguities"] = ["The source offers straight-sixteenth, triplet and quintuplet options; this candidate selects only straight sixteenths. Independent Curriculum review must assess that explicit interpretation.",
                             "Source gives relative tempo guidance but no fixed BPM; whole route, accents, mastery and admission are outside this cell."]
    record["normalization"] = [{"kind": "representation_metadata", "basis": "L6-TXT1-1-23",
                                "text": "Straight sixteenths are selected from source session options for one separated four-note cell; alternate picking starts D or U, with no fixed BPM or accent imposed. Standard tuning is represented by EADGBE open MIDI and capo zero; this is an explicit source interpretation for independent review."}]
    event_sources = {}
    event_provenance = {}
    for i, event in enumerate(record["events"], 1):
        need(event["event_id"] is event["onset_q"] is event["duration_q"] is None, "PROPOSAL_EVENT_TIME_DRIFT")
        need((event["string"], event["fret"], event["finger"], event["midi"]) == facts[i - 1], "EVENT_FACT_DRIFT")
        eid = f"{ITEM}:event:{i:04d}"
        provenance = event.pop("source_local_provenance")
        # The broad unallocated proposal cites the whole Exercise001 span,
        # including descent. This selected ascending cell has a narrower
        # declared passage; bind every event to that exact original TXT slice.
        need(provenance["source_txt_ref"] == "L6-TXT1-34-48" and
             provenance["source_pdf_page"] == 2 and
             provenance["direction"] == "ascending" and
             provenance["source_pair"] == "E-D", "PROPOSAL_PROVENANCE_DRIFT")
        provenance["source_txt_ref"] = "L6-TXT1-34-41"
        event_provenance[eid] = provenance
        onset = Fraction(i - 1, 4)
        event.update(event_id=eid, onset_q=[onset.numerator, onset.denominator], duration_q=[1, 4])
        event_sources[eid] = "L6-TXT1-34-41"
    record["variants"] = [{"id": vid, "label": f"first-E-D-cell-{start}-start",
                           "role": "notation_practice", "route": "ascending_E_D_one_separated_cell",
                           "source_refs": refs, "event_ids": list(event_sources),
                           "pick_start": start, "pick_start_origin": "source_authored",
                           "grouping": {"kind": "source_event_time", "notes_per_beat": None,
                                        "beat_unit_q": None, "marking_factor": [1, 1],
                                        "source_label": "Original TXT lines 20-21: selected straight-sixteenth four-note cell"},
                           "accent_policy": "source_unspecified", "tail_pause": None,
                           "unresolved": []} for vid, start in zip(VARIANTS, ("D", "U"))]
    sources = {
        "L6-TXT1-34-41": passage(TXT, TXT_SHA, "txt", "\n".join(lines[33:41]), first_line=34, last_line=41),
        "L6-PDF1-p2": passage(PDF, PDF_SHA, "pdf", pages[1], page=2),
        "L6-TXT1-1-23": passage(TXT, TXT_SHA, "txt", "\n".join(lines[:23]), first_line=1, last_line=23),
        "L6-PDF1-p1": passage(PDF, PDF_SHA, "pdf", pages[0], page=1),
    }
    foundation = read(root, BASE / "package.json")
    base_registry = read(root, BASE / "identity-registry.json")
    base_profile = read(root, BASE / "expected-profile.json")
    package = {k: copy.deepcopy(v) for k, v in foundation.items() if k not in ("records", "sources", "workbook_catalog")}
    package.update(content_version="curriculum-v1-level006-ex001-first-cell-build-only.2", records=[record], sources=sources)
    entities = [{"id": "fg:workbook:000006", "kind": "workbook", "label": "Legacy Level6", "parent": "fg:course:000001"},
                {"id": MODULE, "kind": "module", "label": "Level6 Exercise001 Mode A first cell", "parent": "fg:workbook:000006"},
                {"id": ITEM, "kind": "item", "label": record["title"], "parent": MODULE},
                *({"id": vid, "kind": "variant", "label": record["variants"][i]["label"], "parent": ITEM}
                  for i, vid in enumerate(VARIANTS))]
    registry = {"identity_version": base_registry["identity_version"], "rules": base_registry["rules"],
                "entities": [base_registry["entities"][0], *entities]}
    identity_baseline = {"identity_version": registry["identity_version"], "rules": registry["rules"],
                         "entities": [registry["entities"][0]]}
    allocation_baseline = {"version": "control-allocation.1", "authority": "P02 reserved IDs; no prior local Level6 allocation", "records": {}}
    lineage_baseline = {"version": "lineage-baseline.1", "records": {}}
    allocation = {"version": "control-allocation.1", "authority": "P02 provisional reservation; nonadmitted candidate only",
                  "records": {ITEM: {"legacy_level": 6,
                                     "occurrences": {p["source_local_event_key"]: eid for eid, p in event_provenance.items()},
                                     "variants": {v["label"]: v["id"] for v in record["variants"]}}}}
    profile = {k: copy.deepcopy(v) for k, v in base_profile.items()
               if k not in ("reference_package", "reference_registry", "event_sources", "authority_artifacts", "workbook_catalog")}
    # This non-tonal finger exercise has no authored scale-degree root.
    profile["degree_roots"] = {}
    profile.update(reference_package=package, reference_registry=registry, event_sources=event_sources)
    check_event_source_closure(record, sources, event_sources, event_provenance)
    profile["authority_artifacts"] = [copy.deepcopy(a) for a in base_profile["authority_artifacts"]
                                      if a["role"] in ("source_manifest", "source_acceptance", "current_schema_freeze")]
    for role, name, value in (("identity_baseline", "identity-baseline.json", identity_baseline),
                              ("allocation_baseline", "allocation-baseline.json", allocation_baseline),
                              ("lineage_baseline", "lineage-baseline.json", lineage_baseline),
                              ("candidate_identity_allocation", "candidate-allocation.json", allocation)):
        profile["authority_artifacts"].append({"path": str(OUT / name), "role": role, "sha256": sha(encode(value))})
    summary = {"status": "source_interpreted_nonadmitted_reference", "item_id": ITEM,
               "variant_ids": list(VARIANTS), "event_count": 4, "admitted": False,
               "runtime_eligible": False, "whole_workbook_complete": False,
               "corrected_from_package_sha256": "07103d6aa9c26923f44d27b992de00bd57879780e3f5b73dfc0ffbc0add29a78",
               "source_txt_sha256": TXT_SHA, "source_pdf_sha256": PDF_SHA,
               "proposal_sha256": PROPOSAL_SHA, "identity_audit_sha256": AUDIT_SHA,
               "interpretation": "one four-note straight-sixteenth cell; alternate-pick D/U starts; independent review required"}
    return {"package.json": package, "identity-registry.json": registry,
            "expected-profile.json": profile, "candidate-allocation.json": allocation,
            "identity-baseline.json": identity_baseline, "allocation-baseline.json": allocation_baseline,
            "lineage-baseline.json": lineage_baseline,
            "source-provenance.json": {"source_txt_ref": "L6-TXT1-34-41", "source_pdf_ref": "L6-PDF1-p2",
                                       "events": event_provenance,
                                       "source_ref_correction": "Unallocated proposal refs 34-48 include descent; r02 selects original TXT lines 34-41 for the ascending E-D cell, matching package and profile closure.",
                                       "variant_strokes": {VARIANTS[0]: ["D", "U", "D", "U"],
                                                           VARIANTS[1]: ["U", "D", "U", "D"]},
                                       "stroke_basis": "TXT lines 13 and 17: alternate picking and both starts; inferred sequence for this separated four-note cell, pending independent source review"},
            "summary.json": summary}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("build", "verify"))
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    result = derive()
    dest = (ROOT / args.out).resolve()
    need(dest == (ROOT / OUT).resolve() or (ROOT / OUT).resolve() in dest.parents, "OUTPUT_SCOPE")
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
