#!/usr/bin/env python3
"""One source-backed, identity-allocated, nonadmitted Level12 Rung02 native pilot."""
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
OUT = Path("Build/parallel-02/level012-rung02-vertical-r01")
BASE = Path("Content/controls/curriculum-v1")
PROPOSAL = source.OUT / "field-proposal.json"
HANDOFF = source.OUT / "allocation-handoff.json"
FOUR = Path("Build/parallel-02/four-real-shard-manifest-r01/summary.json")
LEVEL13 = Path("Build/parallel-12/level013-local-shard-r01")
LEVEL13_REGISTRY_SHA = "07406f7658b973a2a20ed65f75613bf516d44852bf1804beed7543da8fb2c0ef"
NAMES = ("package.json", "identity-registry.json", "expected-profile.json",
         "candidate-allocation.json", "identity-baseline.json",
         "allocation-baseline.json", "lineage-baseline.json", "summary.json")


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


def allocation_floor(registries: list[dict], kind: str, reserved_registry: dict) -> int:
    plural = {"module": "modules", "item": "items", "variant": "variants"}[kind]
    used = [suffix(e["id"]) for r in registries for e in r["entities"] if e["kind"] == kind]
    reserved = []
    for workbook in reserved_registry["workbook_catalog"]["entries"]:
        bounds = workbook.get("reserved_playable_identity_ranges", {}).get(plural)
        if bounds:
            need(len(bounds) == 2, "RESERVATION_SHAPE")
            reserved.append(suffix(bounds[1]))
    return max(used + reserved) + 1


def check_connected_eighths(record: dict) -> None:
    """The frozen validator checks structure; this binds exact source rhythm."""
    need(len(record["events"]) == 16 and record["timing"]["status"] == "source_defined", "TIMING_SCOPE")
    for ordinal, event in enumerate(record["events"]):
        onset = Fraction(ordinal, 2)
        need(event["onset_q"] == [onset.numerator, onset.denominator] and
             event["duration_q"] == [1, 2], "TIMING_SCOPE")
    need(all(v["tail_pause"] is None and len(v["event_ids"]) == 16
             for v in record["variants"]), "TIMING_SCOPE")


def derive(root: Path = ROOT, override: dict | None = None) -> dict[str, dict]:
    need(root.resolve() == ROOT.resolve(), "ROOT_DRIFT")
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
    # Every sealed allocated local shard is a reservation even while nonadmitted.
    shard_paths = [Path("Build/parallel-10/level007-shard-reference-r02"),
                   Path("Build/parallel-12/level008-local-shard-r01"),
                   Path("Build/parallel-12/level010-local-shard-r01"),
                   Path("Build/parallel-12/level011-local-shard-r01"), LEVEL13]
    registries = [foundation_registry, *(read(root, p / "identity-registry.json") for p in shard_paths)]
    item_number = allocation_floor(registries, "item", foundation_registry)
    module_number = allocation_floor(registries, "module", foundation_registry)
    variant_number = allocation_floor(registries, "variant", foundation_registry)
    need((item_number, module_number, variant_number) == (1141, 1141, 7404), "ALLOCATION_FLOOR_DRIFT")
    item = f"fg:item:{item_number:06d}"
    module = f"fg:module:{module_number:06d}"
    variants = [f"fg:variant:{variant_number + i:06d}" for i in range(2)]
    row = proposal["records"][1]
    map_row = handoff["source_map"][1]
    need(row["source_local_key"] == "L12-rung02" and map_row["txt"] == "L12-TXT1-56-67" and
         row["key"] == "Bb" and row["root_fret"] == 6, "CASE_SCOPE")
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
         "RUNG 02 OF 13 - BB MAJOR" in refs[map_row["txt"]]["text"] and
         "Play even eighth notes" in refs["L12-TXT1-1-40"]["text"] and
         re.search(r"\b02\s+BB MAJOR\b", refs["L12-PDF1-p3"]["text"].upper()) is not None,
         "SOURCE_PARITY_OR_TIMING")
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
    entities = [{"id": "fg:workbook:000012", "kind": "workbook", "label": "Legacy Level12", "parent": "fg:course:000001"},
                {"id": module, "kind": "module", "label": "Level12 Rung02 Bb-major connected cell",
                 "parent": "fg:workbook:000012"},
                {"id": item, "kind": "item", "label": record["title"], "parent": module},
                *({"id": vid, "kind": "variant", "label": record["variants"][i]["label"], "parent": item}
                  for i, vid in enumerate(variants))]
    old_ids = {e["id"] for registry in registries for e in registry["entities"]}
    need(not old_ids.intersection(e["id"] for e in entities if e["kind"] != "workbook") and
         len({e["id"] for e in entities}) == len(entities) and
         item != "fg:item:000003", "GLOBAL_ENTITY_COLLISION")
    package = {k: copy.deepcopy(v) for k, v in foundation.items() if k not in ("records", "sources", "workbook_catalog")}
    package.update(content_version="curriculum-v1-level012-rung02-local-build-only.1",
                   records=[record], sources=refs)
    registry = {"identity_version": foundation_registry["identity_version"],
                "rules": foundation_registry["rules"],
                "entities": [foundation_registry["entities"][0], *entities]}
    identity_baseline = {"identity_version": registry["identity_version"],
                         "rules": registry["rules"], "entities": [registry["entities"][0]]}
    allocation_baseline = {"version": "control-allocation.1", "authority":
                           "Local source-backed Rung02 pilot; global 659/four-shard identities checked separately",
                           "records": {}}
    lineage_baseline = {"version": "lineage-baseline.1", "records": {}}
    allocation = {"version": "control-allocation.1", "authority":
                  "P02 Level12 Rung02 local technical candidate only; Curriculum/runtime admission Pending",
                  "records": {item: {"legacy_level": 12,
                                     "occurrences": {f"L12-rung02:note:{i:03d}": eid
                                                     for i, eid in enumerate(event_sources, 1)},
                                     "variants": {record["variants"][i]["label"]: vid
                                                  for i, vid in enumerate(variants)}}}}
    profile = {k: copy.deepcopy(v) for k, v in foundation_profile.items()
               if k not in ("reference_package", "reference_registry", "event_sources",
                            "authority_artifacts", "workbook_catalog")}
    profile["degree_roots"]["Bb-major"] = {"root_pitch_class": 10,
                                           "basis": "Original Level12 Rung02 Bb-major scale tones and TAB; no octave inferred"}
    profile.update(reference_package=package, reference_registry=registry, event_sources=event_sources)
    profile["authority_artifacts"] = [copy.deepcopy(a) for a in foundation_profile["authority_artifacts"]
                                      if a["role"] in ("source_manifest", "source_acceptance", "current_schema_freeze")]
    for role, name, value in (("identity_baseline", "identity-baseline.json", identity_baseline),
                              ("allocation_baseline", "allocation-baseline.json", allocation_baseline),
                              ("lineage_baseline", "lineage-baseline.json", lineage_baseline),
                              ("candidate_identity_allocation", "candidate-allocation.json", allocation)):
        profile["authority_artifacts"].append({"path": str(OUT / name), "role": role,
                                               "sha256": sha(encode(value))})
    result = {"package.json": package, "identity-registry.json": registry,
              "expected-profile.json": profile, "candidate-allocation.json": allocation,
              "identity-baseline.json": identity_baseline,
              "allocation-baseline.json": allocation_baseline,
              "lineage-baseline.json": lineage_baseline,
              "summary.json": {"status": "single_case_source_timed_nonadmitted_reference",
                               "source_local_key": "L12-rung02", "item_id": item,
                               "variant_ids": variants, "event_count": 16,
                               "allocation_floors": {"item": item_number, "module": module_number,
                                                     "variant": variant_number},
                               "foundation_sha256": sha((root / BASE / "package.json").read_bytes()),
                               "source_proposal_sha256": sha((root / PROPOSAL).read_bytes()),
                               "global_four_shard_sha256": sha((root / FOUR).read_bytes()),
                               "level013_registry_sha256": LEVEL13_REGISTRY_SHA,
                               "admitted": False, "runtime_eligible": False,
                               "whole_workbook_complete": False}}
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("build", "verify"))
    args = parser.parse_args()
    result = derive()
    destination = ROOT / OUT
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
