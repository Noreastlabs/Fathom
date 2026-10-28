#!/usr/bin/env python3
"""Build-only source candidate for the Level12 Rung05 Db-major cell."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
from fractions import Fraction
from pathlib import Path

import parallel12_level012_schema1_unallocated as source

ROOT = Path(__file__).resolve().parents[1]
OUT = Path("Build/parallel-03/controlled-open-rung05-r01")
BASE = Path("Content/controls/curriculum-v1")
PROPOSAL = source.OUT / "field-proposal.json"
HANDOFF = source.OUT / "allocation-handoff.json"
FOUR = Path("Build/parallel-02/four-real-shard-manifest-r01/summary.json")
LEVEL13 = Path("Build/parallel-12/level013-local-shard-r01")
LEVEL13_REGISTRY_SHA = "07406f7658b973a2a20ed65f75613bf516d44852bf1804beed7543da8fb2c0ef"
RUNG02 = Path("Content/runtime/rung02-extension-v1/Build/parallel-02/level012-rung02-vertical-r01")
RUNG02_REGISTRY_SHA = "1541b508787cf87d61a917da89e8933fdc85aedf5f0b38abbc8d85d6be70cf87"
RUNG02_PACKAGE_SHA = "3cacd1c5c3dd2059a018c475192657ec0bb4e4c600074a5fbfb657ea611cefbc"
RUNG03 = Path("Build/parallel-02/level012-rung03-shard-r01")
RUNG03_REGISTRY_SHA = "fbebd891f157eaa47688364087860313450f88daef62aa9dc15bb05af50d1000"
IDENTITY_AUDIT = Path("Build/parallel-02/controlled-open-rung05-assignment-r01/identity-audit.json")
IDENTITY_AUDIT_SHA = "d5a067857bfe13d446662c193d9c6d5742c3254d3da0f61485101f7c20e6d570"
NAMES = ("package.json", "identity-registry.json", "expected-profile.json",
         "candidate-allocation.json", "identity-baseline.json",
         "allocation-baseline.json", "lineage-baseline.json",
         "source-provenance.json", "summary.json")
IDS = {"fg:item:001145", "fg:module:001145", "fg:variant:007412", "fg:variant:007413"}


class PilotError(ValueError):
    pass


def need(ok: bool, code: str) -> None:
    if not ok:
        raise PilotError(code)


def encode(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def read(root: Path, rel: Path) -> dict:
    return json.loads((root / rel).read_bytes())


def suffix(identity: str) -> int:
    return int(identity.rsplit(":", 1)[1])


def source_passages(root: Path, refs: list[str]) -> dict:
    from pypdf import PdfReader

    lines = (root / source.TXT).read_text().splitlines()
    pages = [p.extract_text() for p in PdfReader(str(root / source.PDF)).pages]
    need(len(lines) == 231 and len(pages) == 6, "SOURCE_LENGTH")
    output = {}
    for ref in refs:
        if match := re.fullmatch(r"L12-TXT1-(\d+)-(\d+)", ref):
            first, last = map(int, match.groups())
            need(1 <= first <= last <= len(lines), "TXT_SPAN")
            fragment = "\n".join(lines[first - 1:last])
            output[ref] = {"path": str(source.TXT), "sha256": source.PINS[source.TXT][1],
                           "format": "txt", "first_line": first, "last_line": last,
                           "text": fragment, "text_sha256": sha(fragment.encode())}
        elif match := re.fullmatch(r"L12-PDF1-p(\d+)", ref):
            page = int(match.group(1))
            need(1 <= page <= len(pages), "PDF_SPAN")
            fragment = pages[page - 1]
            output[ref] = {"path": str(source.PDF), "sha256": source.PINS[source.PDF][1],
                           "format": "pdf", "page": page,
                           "text": fragment, "text_sha256": sha(fragment.encode())}
        else:
            raise PilotError("SOURCE_REF_SHAPE")
    return output


def fresh_identity_scan(root: Path) -> dict:
    """Refuse a foreign allocation of P02's provisional IDs before writing."""
    matches = {identity: [] for identity in sorted(IDS)}
    count = 0
    for base in (root / "Content", root / "Build"):
        for path in base.rglob("identity-registry.json"):
            if path.is_symlink() or OUT in path.relative_to(root).parents:
                continue
            registry = json.loads(path.read_bytes())
            count += 1
            for entity in registry.get("entities", []):
                if entity.get("id") in matches:
                    matches[entity["id"]].append(str(path.relative_to(root)))
    need(not any(matches.values()), "LIVE_ID_COLLISION " + json.dumps(matches, sort_keys=True))
    return {"registries_scanned": count, "matches": matches, "collision_free": True}


def check_connected_eighths(record: dict) -> None:
    """The frozen validator checks structure; this binds exact source rhythm."""
    need(len(record["events"]) == 16 and record["timing"]["status"] == "source_defined", "TIMING_SCOPE")
    for ordinal, event in enumerate(record["events"]):
        onset = Fraction(ordinal, 2)
        need(event["onset_q"] == [onset.numerator, onset.denominator] and
             event["duration_q"] == [1, 2], "TIMING_SCOPE")
    need(all(v["tail_pause"] is None and len(v["event_ids"]) == 16
             for v in record["variants"]), "TIMING_SCOPE")


def check_source_cell(refs: dict, record: dict, txt_ref: str, pdf_ref: str) -> None:
    """Bind the projection to both printed cards and each exact note position."""
    rows = (
        "Deg|1--2--3--4--5--6--7--8--8--7--6--5--4--3--2--1--|",
        "Fng|2--4--1--2--4--1--3--4--4--3--1--4--2--1--4--2--|",
        "D  |---------------8--10-11-11-10-8-----------------|",
        "A  |------8--9--11-------------------11-9--8--------|",
        "E  |9--11-------------------------------------11-9--|",
    )
    txt, pdf = refs[txt_ref]["text"], refs[pdf_ref]["text"]
    need(all(row in txt and row in pdf for row in rows) and
         "RUNG 05 OF 13 - DB MAJOR - ROOT ON LOW E FRET 9 - FRAME 8-11" in txt and
         "05  DB MAJOR\nROOT E9  |  FRAME 8-11" in pdf and
         "Scale tones: Db Eb F Gb Ab Bb C Db" in txt and
         "Notes: Db  Eb  F  Gb  Ab  Bb  C  Db" in pdf and
         "D-start and U-start" in pdf,
         "SOURCE_CARD_DRIFT")
    expected = [
        (1, 9, 2, 49, "Db", 1), (1, 11, 4, 51, "Eb", 2),
        (2, 8, 1, 53, "F", 3), (2, 9, 2, 54, "Gb", 4),
        (2, 11, 4, 56, "Ab", 5), (3, 8, 1, 58, "Bb", 6),
        (3, 10, 3, 60, "C", 7), (3, 11, 4, 61, "Db", 8),
        (3, 11, 4, 61, "Db", 8), (3, 10, 3, 60, "C", 7),
        (3, 8, 1, 58, "Bb", 6), (2, 11, 4, 56, "Ab", 5),
        (2, 9, 2, 54, "Gb", 4), (2, 8, 1, 53, "F", 3),
        (1, 11, 4, 51, "Eb", 2), (1, 9, 2, 49, "Db", 1),
    ]
    actual = [(e["string"], e["fret"], e["finger"], e["midi"],
               e["spelling"], e["degree_contexts"]["Db-major"]["ordinal"])
              for e in record["events"]]
    need(actual == expected, "SOURCE_EVENT_DRIFT")


def check_candidate_labels(record: dict, registry: dict, profile: dict) -> None:
    """Keep identity and source-provenance labels aligned with the selected card."""
    entities = {entry["id"]: entry for entry in registry["entities"]}
    need(entities["fg:module:001145"]["label"] == "Level12 Rung05 Db-major connected cell" and
         entities["fg:item:001145"]["label"] == record["title"] ==
         "Rung 05: Db major one-fret neck ladder cell" and
         profile["degree_roots"]["Db-major"] == {
             "root_pitch_class": 1,
             "basis": "Original Level12 Rung05 Db-major scale tones and TAB; no octave inferred"},
         "DB_MAJOR_SOURCE_LABEL_DRIFT")


def check_source_closure(record: dict, refs: dict, event_sources: dict) -> None:
    declared = set(record["source_refs"])
    need(declared == set(refs) and len(record["source_refs"]) == len(declared), "SOURCE_REF_CLOSURE")
    need(set(record["authored_text_refs"]) <= declared and
         set(record["control_scope"]["basis_refs"]) <= declared and
         all(set(variant["source_refs"]) <= declared for variant in record["variants"]),
         "SOURCE_REF_CLOSURE")
    need(set(event_sources) == {event["event_id"] for event in record["events"]} and
         set(event_sources.values()) == {"L12-TXT1-98-109"}, "EVENT_SOURCE_CLOSURE")
    need(record["context"]["tuning_open_midi"] == [40, 45, 50, 55, 59, 64] and
         record["context"]["capo"] == 0 and not record["runtime_eligible"],
         "SETUP_OR_ADMISSION_DRIFT")


def derive(root: Path = ROOT, override: dict | None = None) -> dict[str, dict]:
    need(root.resolve() == ROOT.resolve(), "ROOT_DRIFT")
    fresh_scan = fresh_identity_scan(root)
    source.pin(root)
    expected, expected_handoff = source.build(root)
    proposal = read(root, PROPOSAL)
    handoff = read(root, HANDOFF)
    need(proposal == expected and handoff == expected_handoff, "SOURCE_PROJECTION_DRIFT")
    need(sha((root / PROPOSAL).read_bytes()) == "d2ad9856313c003777d6fd926e27272eecd833a74a38e76fe0104d0a89fbcce9",
         "PROPOSAL_PIN_DRIFT")
    foundation = read(root, BASE / "package.json")
    foundation_registry = read(root, BASE / "identity-registry.json")
    foundation_profile = read(root, BASE / "expected-profile.json")
    global_summary = read(root, FOUR)
    need(len(foundation["records"]) == 659 and
         next(r for r in foundation["records"] if r["id"] == "fg:item:000003")["legacy_level"] == 12 and
         global_summary["validated_workbooks"] == [7, 8, 10, 11] and
         global_summary["admitted"] is False, "FOUNDATION_SCOPE")
    need(sha((root / LEVEL13 / "identity-registry.json").read_bytes()) == LEVEL13_REGISTRY_SHA,
         "LEVEL13_RESERVATION_DRIFT")
    need(sha((root / RUNG02 / "identity-registry.json").read_bytes()) == RUNG02_REGISTRY_SHA and
         sha((root / RUNG02 / "package.json").read_bytes()) == RUNG02_PACKAGE_SHA,
         "RUNG02_PREDECESSOR_DRIFT")
    need(sha((root / RUNG03 / "identity-registry.json").read_bytes()) == RUNG03_REGISTRY_SHA,
         "RUNG03_PREDECESSOR_DRIFT")
    need(sha((root / IDENTITY_AUDIT).read_bytes()) == IDENTITY_AUDIT_SHA,
         "LIVE_ID_AUDIT_DRIFT")
    audit = read(root, IDENTITY_AUDIT)
    need(audit["proposed"] == {"item": "fg:item:001145", "module": "fg:module:001145",
                               "variants": ["fg:variant:007412", "fg:variant:007413"]} and
         audit["collision_free"] is True and audit["registries_scanned"] == 181,
         "LIVE_ID_RESERVATION_DRIFT")
    item, module = "fg:item:001145", "fg:module:001145"
    variants = ["fg:variant:007412", "fg:variant:007413"]
    row = proposal["records"][4]
    map_row = handoff["source_map"][4]
    need(row["source_local_key"] == "L12-rung05" and map_row["txt"] == "L12-TXT1-98-109" and
         row["key"] == "Db" and row["root_fret"] == 9 and row["frame"] == [8, 11] and map_row["pdf_card"] == "L12-PDF1-p4",
         "CASE_SCOPE")
    need(override is None or override == row["schema1_fields"], "CANDIDATE_SOURCE_DRIFT")
    record = copy.deepcopy(override if override is not None else row["schema1_fields"])
    need(record["id"] is record["module_id"] is record["workbook_id"] is record["lineage"] is None and
         record["runtime_eligible"] is False and len(record["events"]) == 16 and
         record["source_refs"][0] == map_row["txt"], "CANDIDATE_AUTHORITY")
    # P12's handoff preserves PDF page 2 in two source roles; schema1 requires
    # a passage identity only once per record, without dropping its content.
    record["source_refs"] = list(dict.fromkeys(record["source_refs"]))
    record["authored_text_refs"] = list(dict.fromkeys(record["authored_text_refs"]))
    record["control_scope"]["basis_refs"] = list(dict.fromkeys(record["control_scope"]["basis_refs"]))
    for variant in record["variants"]:
        variant["source_refs"] = list(dict.fromkeys(variant["source_refs"]))
    refs = source_passages(root, record["source_refs"])
    need(refs[map_row["txt"]]["text_sha256"] == map_row["txt_passage_sha256"] and
         "RUNG 05 OF 13 - DB MAJOR" in refs[map_row["txt"]]["text"] and
         "Play even eighth notes" in refs["L12-TXT1-1-40"]["text"] and
         re.search(r"\b05\s+DB MAJOR\b", refs["L12-PDF1-p4"]["text"].upper()) is not None,
         "SOURCE_PARITY_OR_TIMING")
    check_source_cell(refs, record, map_row["txt"], map_row["pdf_card"])
    record.update(id=item, module_id=module, workbook_id="fg:workbook:000012",
                  content_revision=1, lineage={"kind": "new"})
    record["timing"] = {"status": "source_defined", "unit": "quarter",
                        "basis": "Original Level12 TXT line 35: even eighth notes for each 16-note cell; connected single-cell span only",
                        "other_source_requirements": record["timing"]["other_source_requirements"]}
    record["normalization"].append({"kind": "representation_metadata", "basis": "L12-TXT1-1-40",
                                    "text": "The connected 16-note cell uses even eighths. Optional inter-cell pause, fixed BPM and full-ladder advancement are not this selected Practice span."})
    record["ambiguities"] = ["Optional one-beat inter-cell pause has no bound beat unit; not in selected span.",
                             "Whole 13-rung ladder and two-day advancement remain outside this cell."]
    record["control_scope"]["unresolved"] = ["Whole route and Curriculum admission remain Pending."]
    event_sources = {}
    for ordinal, event in enumerate(record["events"], 1):
        need(event["event_id"] is event["onset_q"] is event["duration_q"] is None and
             event["attack"] == "picked", "UNAUTHORED_EVENT")
        eid = f"{item}:event:{ordinal:04d}"
        onset = Fraction(ordinal - 1, 2)
        event.update(event_id=eid, onset_q=[onset.numerator, onset.denominator], duration_q=[1, 2])
        event_sources[eid] = map_row["txt"]
    for vi, variant in enumerate(record["variants"]):
        need(variant["id"] is variant["event_ids"] is None and variant["tail_pause"] is None and
             variant["pick_start"] == ("D", "U")[vi], "VARIANT_SCOPE")
        variant.update(id=variants[vi], event_ids=list(event_sources))
        variant["pick_start_origin"] = "source_authored"
        variant["grouping"] = {"kind": "source_event_time", "notes_per_beat": None,
                               "beat_unit_q": None, "marking_factor": [1, 1],
                               "source_label": "Original TXT line 35 even eighths; exact event spans"}
        variant["unresolved"] = []
    check_connected_eighths(record)
    check_source_closure(record, refs, event_sources)
    entities = [{"id": "fg:workbook:000012", "kind": "workbook", "label": "Legacy Level12", "parent": "fg:course:000001"},
                {"id": module, "kind": "module", "label": "Level12 Rung05 Db-major connected cell",
                 "parent": "fg:workbook:000012"},
                {"id": item, "kind": "item", "label": record["title"], "parent": module},
                *({"id": vid, "kind": "variant", "label": record["variants"][i]["label"], "parent": item}
                  for i, vid in enumerate(variants))]
    need(len({e["id"] for e in entities}) == len(entities) and
         item != "fg:item:000003", "GLOBAL_ENTITY_COLLISION")
    package = {k: copy.deepcopy(v) for k, v in foundation.items() if k not in ("records", "sources", "workbook_catalog")}
    package.update(content_version="curriculum-v1-level012-rung05-local-build-only.1",
                   records=[record], sources=refs)
    registry = {"identity_version": foundation_registry["identity_version"],
                "rules": foundation_registry["rules"],
                "entities": [foundation_registry["entities"][0], *entities]}
    identity_baseline = {"identity_version": registry["identity_version"],
                         "rules": registry["rules"], "entities": [registry["entities"][0]]}
    allocation_baseline = {"version": "control-allocation.1", "authority":
                           "Local source-backed Rung05 candidate; P02 181-registry audit and fresh collision scan checked separately",
                           "records": {}}
    lineage_baseline = {"version": "lineage-baseline.1", "records": {}}
    allocation = {"version": "control-allocation.1", "authority":
                  "P03 Level12 Rung05 Build-only candidate; P02 agent Curriculum/runtime admission Pending",
                  "records": {item: {"legacy_level": 12,
                                     "occurrences": {f"L12-rung05:note:{i:03d}": eid
                                                     for i, eid in enumerate(event_sources, 1)},
                                     "variants": {record["variants"][i]["label"]: vid
                                                  for i, vid in enumerate(variants)}}}}
    profile = {k: copy.deepcopy(v) for k, v in foundation_profile.items()
               if k not in ("reference_package", "reference_registry", "event_sources",
                            "authority_artifacts", "workbook_catalog")}
    profile["degree_roots"]["Db-major"] = {"root_pitch_class": 1,
                                          "basis": "Original Level12 Rung05 Db-major scale tones and TAB; no octave inferred"}
    profile.update(reference_package=package, reference_registry=registry, event_sources=event_sources)
    profile["authority_artifacts"] = [copy.deepcopy(a) for a in foundation_profile["authority_artifacts"]
                                      if a["role"] in ("source_manifest", "source_acceptance", "current_schema_freeze")]
    for role, name, value in (("identity_baseline", "identity-baseline.json", identity_baseline),
                              ("allocation_baseline", "allocation-baseline.json", allocation_baseline),
                              ("lineage_baseline", "lineage-baseline.json", lineage_baseline),
                              ("candidate_identity_allocation", "candidate-allocation.json", allocation)):
        profile["authority_artifacts"].append({"path": str(OUT / name), "role": role,
                                               "sha256": sha(encode(value))})
    check_candidate_labels(record, registry, profile)
    provenance = {"source_local_key": "L12-rung05", "status": "nonadmitted_build_only",
                  "originals": [{"path": str(path), "bytes": source.PINS[path][0],
                                 "sha256": source.PINS[path][1]}
                                for path in (source.TXT, source.PDF)],
                  "passages": {key: {"path": value["path"], "sha256": value["sha256"],
                                     "text_sha256": value["text_sha256"], "format": value["format"],
                                     **({"page": value["page"]} if "page" in value else
                                        {"first_line": value["first_line"], "last_line": value["last_line"]})}
                               for key, value in refs.items()},
                  "event_sources": event_sources,
                  "timing_basis": "L12-TXT1-1-40 lines 34-36: even eighth notes per 16-note cell",
                  "cell_basis": "L12-TXT1-98-109 and L12-PDF1-p4 Rung05 card",
                  "setup_basis": "Original Level12 standard tuning; no capo instruction, represented as capo 0",
                  "source_decision_questions": ["Confirm the quarter-grid representation of printed even eighths for one cell.",
                                                "Confirm Db spelling, repeated octave root and D/U starts against both originals.",
                                                "Keep optional between-cell pause and whole ladder outside this packet."]}
    result = {"package.json": package, "identity-registry.json": registry,
              "expected-profile.json": profile, "candidate-allocation.json": allocation,
              "identity-baseline.json": identity_baseline,
              "allocation-baseline.json": allocation_baseline,
              "lineage-baseline.json": lineage_baseline,
              "source-provenance.json": provenance,
              "summary.json": {"status": "single_case_source_timed_nonadmitted_reference",
                               "source_local_key": "L12-rung05", "item_id": item,
                               "variant_ids": variants, "event_count": 16,
                               "fresh_identity_scan": fresh_scan,
                               "foundation_sha256": sha((root / BASE / "package.json").read_bytes()),
                               "source_proposal_sha256": sha((root / PROPOSAL).read_bytes()),
                               "global_four_shard_sha256": sha((root / FOUR).read_bytes()),
                               "level013_registry_sha256": LEVEL13_REGISTRY_SHA,
                               "rung03_registry_sha256": RUNG03_REGISTRY_SHA,
                               "rung02_registry_sha256": RUNG02_REGISTRY_SHA,
                               "rung02_package_sha256": RUNG02_PACKAGE_SHA,
                               "live_identity_audit_sha256": IDENTITY_AUDIT_SHA,
                               "source_provenance_sha256": sha(encode(provenance)),
                               "admitted": False, "runtime_eligible": False,
                               "whole_workbook_complete": False}}
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("build", "verify"))
    parser.add_argument("--output", default=str(OUT),
                        help="primary package or a repeat directory inside the lane Build boundary")
    args = parser.parse_args()
    result = derive()
    destination = (ROOT / args.output).resolve()
    need(destination == (ROOT / OUT).resolve() or
         destination.parent == (ROOT / OUT).resolve(), "OUTPUT_SCOPE")
    if args.command == "build":
        destination.mkdir(parents=True, exist_ok=True)
        need(all(not (destination / name).exists() for name in NAMES), "OUTPUT_EXISTS")
        for name in NAMES:
            (destination / name).write_bytes(encode(result[name]))
    else:
        for name in NAMES:
            need((destination / name).read_bytes() == encode(result[name]), f"OUTPUT_DRIFT {name}")
    print(json.dumps(result["summary.json"], sort_keys=True))


if __name__ == "__main__":
    main()
