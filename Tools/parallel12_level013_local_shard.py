#!/usr/bin/env python3
"""Allocate and verify a nonadmitted, native-valid Level13 local shard."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from pypdf import PdfReader

import parallel12_level013_schema1_unallocated as source

ROOT = Path(__file__).resolve().parents[1]
OUT = Path("Build/parallel-12/level013-local-shard-r01")
PROPOSAL = Path("Build/parallel-12/level013-schema1-unallocated-r01")
FOUR = Path("Build/parallel-02/four-real-shard-manifest-r01")
PINS = {
    FOUR / "manifest.json": "01967090d337c7154211ddd8e6926a9d67aa1ed2a7eda0e37b662d0b52aa33e8",
    FOUR / "summary.json": "a3072fc6074d812c3b59fd5cc002da34813be9fb98abe3efe79967b06ca140fa",
    PROPOSAL / "field-proposal.json": "e04b5283b1fcc1a67d5eb44727d71f62a08a7db3a3dffddef467274df0454549",
    PROPOSAL / "allocation-handoff.json": "12fed051575ca7530aafacdb2b7d4ab3043b48f26ba603a9b3b090cfe5b091fe",
    source.p10.TXT_REL: source.p10.TXT_SHA,
    source.p10.PDF_REL: source.p10.PDF_SHA,
}
FILES = ("package.json", "identity-registry.json", "expected-profile.json",
         "candidate-allocation.json", "identity-baseline.json",
         "allocation-baseline.json", "lineage-baseline.json", "local-summary.json")
GUIDANCE = ("L13-TXT1-30-49", "L13-TXT1-234-239")


class ShardError(ValueError):
    pass


def need(ok: bool, code: str) -> None:
    if not ok:
        raise ShardError(code)


def encode(obj: object) -> bytes:
    return (json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def read(root: Path, path: Path) -> dict:
    return json.loads((root / path).read_text())


def number(identity: str) -> int:
    return int(identity.rsplit(":", 1)[1])


def pin(root: Path) -> None:
    need(root.resolve() == ROOT.resolve(), "ROOT_DRIFT")
    for path, digest in PINS.items():
        need(sha((root / path).read_bytes()) == digest, f"INPUT_PIN_DRIFT {path}")


def predecessors(root: Path) -> tuple[dict, tuple[dict, ...], tuple[dict, ...], dict]:
    manifest = read(root, FOUR / "manifest.json")
    summary = read(root, FOUR / "summary.json")
    need(manifest["validated_workbooks"] == summary["validated_workbooks"] == [7, 8, 10, 11] and
         manifest["aggregate_complete"] is summary["aggregate_complete"] is False and
         manifest["admitted"] is summary["admitted"] is summary["runtime_admission"] is False and
         summary["status"] == "verified_preparatory_global_manifest" and
         len(manifest["shards"]) == 4, "FOUR_SHARD_AUTHORITY")
    paths = [manifest["foundation"]] + [s["artifacts"] for s in manifest["shards"]]
    packages, registries = [], []
    for index, artifacts in enumerate(paths):
        for role, target in (("package", packages), ("registry", registries)):
            identity = artifacts[role]
            path = Path(identity["path"])
            need(not path.is_absolute() and (root / path).is_file() and
                 sha((root / path).read_bytes()) == identity["sha256"], f"PREDECESSOR_HASH {index} {role}")
            target.append(read(root, path))
    need([len(p["records"]) for p in packages] == [659, 108, 108, 108, 108] and
         [s["legacy_level"] for s in manifest["shards"]] == [7, 8, 10, 11], "PREDECESSOR_SCOPE")
    foundation = manifest["foundation"]
    for role in ("profile", "generation", "catalog_coverage"):
        identity = foundation[role]
        need(sha((root / identity["path"]).read_bytes()) == identity["sha256"],
             f"FOUNDATION_AUTHORITY_HASH {role}")
    for shard in manifest["shards"]:
        for role, identity in shard["artifacts"].items():
            need(sha((root / identity["path"]).read_bytes()) == identity["sha256"],
                 f"FOUR_SHARD_ARTIFACT_HASH {shard['legacy_level']} {role}")
    return manifest, tuple(packages), tuple(registries), summary


def floors(registries: tuple[dict, ...]) -> dict[str, int]:
    base = registries[0]
    floor = {}
    for kind, plural in (("module", "modules"), ("item", "items"), ("variant", "variants")):
        used = [number(e["id"]) for reg in registries for e in reg["entities"] if e["kind"] == kind]
        reserved = []
        for entry in base["workbook_catalog"]["entries"]:
            bounds = entry.get("reserved_playable_identity_ranges", {}).get(plural)
            if bounds:
                need(len(bounds) == 2 and all(x.startswith(f"fg:{kind}:") for x in bounds) and
                     number(bounds[0]) <= number(bounds[1]), "RESERVATION_SHAPE")
                reserved.append(number(bounds[1]))
        floor[kind] = max(used + reserved) + 1
    need(floor == {"module": 1128, "item": 1128, "variant": 7378}, "ALLOCATION_FLOOR_DRIFT")
    return floor


def txt_passage(lines: list[str], ref: str) -> dict:
    match = re.fullmatch(r"L13-TXT1-(\d+)-(\d+)", ref)
    need(match is not None, "TXT_REF")
    first, last = map(int, match.groups())
    need(1 <= first <= last <= len(lines), "TXT_SPAN")
    text = "\n".join(lines[first - 1:last])
    return {"path": str(source.p10.TXT_REL), "sha256": source.p10.TXT_SHA,
            "format": "txt", "first_line": first, "last_line": last,
            "text": text, "text_sha256": sha(text.encode())}


def passages(root: Path, handoff: dict) -> dict:
    lines = (root / source.p10.TXT_REL).read_text().splitlines()
    pdf = PdfReader(str(root / source.p10.PDF_REL))
    need(len(pdf.pages) == 7, "PDF_COUNT")
    result = {ref: txt_passage(lines, ref) for ref in GUIDANCE}
    for page in range(2, 8):
        text = pdf.pages[page - 1].extract_text()
        result[f"L13-PDF1-p{page}"] = {"path": str(source.p10.PDF_REL), "sha256": source.p10.PDF_SHA,
                                       "format": "pdf", "page": page, "text": text,
                                       "text_sha256": sha(text.encode())}
    for entry in handoff["source_map"]:
        ref = entry["txt"]
        need(ref not in result, "DUPLICATE_SOURCE_REF")
        passage = txt_passage(lines, ref)
        need(passage["text_sha256"] == entry["txt_passage_sha256"] and
             passage["text"].startswith(f"RUNG {entry['rung_number']:02d} OF 13") and
             re.search(rf"\b{entry['rung_number']:02d}\b\s+{entry['key'].upper()}\s+MAJOR",
                       result[entry["pdf_card"]]["text"]) is not None, "SOURCE_CARD")
        result[ref] = passage
    need(len(result) == 21, "SOURCE_COUNT")
    return result


def derive(root: Path = ROOT, proposal_override: dict | None = None) -> dict[str, dict]:
    pin(root)
    manifest, packages, registries, four_summary = predecessors(root)
    floor = floors(registries)
    need(four_summary["next_allocation_floor"] == floor and
         not any(r["legacy_level"] == 13 for pkg in packages for r in pkg["records"]) and
         not any(e["id"] == "fg:workbook:000013" or e.get("parent") == "fg:workbook:000013"
                 for reg in registries for e in reg["entities"]), "PREDECESSOR_LEVEL13_COLLISION")
    expected_proposal, expected_handoff = source.build(root)
    proposal = proposal_override if proposal_override is not None else read(root, PROPOSAL / "field-proposal.json")
    handoff = read(root, PROPOSAL / "allocation-handoff.json")
    need(proposal == expected_proposal and handoff == expected_handoff, "SOURCE_PROPOSAL_DRIFT")
    source.verify(proposal, handoff)
    refs = passages(root, handoff)
    records, entities, allocations, event_sources, source_map = [], [], {}, {}, []
    entities.append({"id": "fg:workbook:000013", "kind": "workbook",
                     "label": "Legacy Level13 two-octave six-string neck ladder", "parent": "fg:course:000001"})
    for index, row in enumerate(proposal["records"]):
        item = f"fg:item:{floor['item'] + index:06d}"
        module = f"fg:module:{floor['module'] + index:06d}"
        fields = copy.deepcopy(row["schema1_fields"])
        src = handoff["source_map"][index]
        need(row["source_local_key"] == src["source_local_key"] and
             fields["source_refs"] == [src["txt"], src["pdf_card"], "L13-TXT1-30-49",
                                       "L13-PDF1-p2", "L13-TXT1-234-239"] and
             all(fields[k] is None for k in ("id", "workbook_id", "module_id", "content_revision", "lineage")),
             "SOURCE_IDENTITY_OR_REFS")
        fields.update(id=item, workbook_id="fg:workbook:000013", module_id=module,
                      content_revision=1, lineage={"kind": "new"})
        entities.extend(({"id": module, "kind": "module", "label": f"Level13 rung {index + 1:02d} {row['key']}",
                          "parent": "fg:workbook:000013"},
                         {"id": item, "kind": "item", "label": fields["title"], "parent": module}))
        occurrences = {}
        for ordinal, event in enumerate(fields["events"], 1):
            need(event["event_id"] is event["onset_q"] is event["duration_q"] is None,
                 "SOURCE_TIMING_OR_ID")
            eid = f"{item}:event:{ordinal:04d}"
            event["event_id"] = eid
            occurrences[f"{row['source_local_key']}:note:{ordinal:03d}"] = eid
            event_sources[eid] = src["txt"]
        variants, turns = {}, {}
        for vi, (variant, membership) in enumerate(zip(fields["variants"], row["variant_memberships"], strict=True)):
            need(variant["id"] is variant["event_ids"] is None and
                 variant["label"] == membership["label"] and
                 membership["event_local_ordinals"] == list(range(1, 31)) and
                 membership["repeated_high_root_ordinals"] == [15, 16], "VARIANT_SOURCE")
            vid = f"fg:variant:{floor['variant'] + index * 2 + vi:06d}"
            variant["id"] = vid
            variant["event_ids"] = [fields["events"][ordinal - 1]["event_id"]
                                    for ordinal in membership["event_local_ordinals"]]
            variants[variant["label"]] = vid
            turns[variant["label"]] = [fields["events"][ordinal - 1]["event_id"]
                                       for ordinal in membership["repeated_high_root_ordinals"]]
            entities.append({"id": vid, "kind": "variant", "label": variant["label"], "parent": item})
        need(len(fields["events"]) == len(occurrences) == 30 and len(variants) == 2, "CASE_COUNT")
        records.append(fields)
        allocations[item] = {"legacy_level": 13, "occurrences": occurrences, "variants": variants}
        source_map.append({"item_id": item, **src, "variant_turn_event_ids": turns})
    pkg = {k: v for k, v in packages[-1].items() if k not in ("records", "sources")}
    pkg.update(content_version="curriculum-v1-level013-local-shard-build-only.1", records=records, sources=refs)
    reg = {"identity_version": registries[0]["identity_version"], "rules": registries[0]["rules"],
           "entities": [registries[0]["entities"][0], *entities]}
    identity_baseline = {"identity_version": reg["identity_version"], "rules": reg["rules"],
                         "entities": [reg["entities"][0]]}
    allocation_baseline = {"version": "control-allocation.1", "authority":
                           "Local Level13 course-only preallocation; current659 and four shards pinned separately", "records": {}}
    lineage_baseline = {"version": "lineage-baseline.1", "records": {}}
    allocation = {"version": "control-allocation.1", "authority":
                  "P12 Level13 local shard only; global aggregate validation required; no admission", "records": allocations}
    predecessor_profile = read(root, Path(manifest["shards"][-1]["artifacts"]["profile"]["path"]))
    profile = {k: v for k, v in predecessor_profile.items() if k not in
               ("reference_package", "reference_registry", "event_sources", "authority_artifacts")}
    profile.update(reference_package=pkg, reference_registry=reg, event_sources=event_sources)
    for key in source.p10.KEYS:
        label = f"{key}-major"
        profile["degree_roots"][label] = {"basis": "Level13 original major-scale source card; pitch class only; no octave inferred",
                                           "root_pitch_class": source.pitch_class(key)}
    profile["authority_artifacts"] = [a for a in predecessor_profile["authority_artifacts"] if a["role"] in
                                      ("source_manifest", "source_acceptance", "current_schema_freeze")]
    for role, name, obj in (("identity_baseline", "identity-baseline.json", identity_baseline),
                            ("allocation_baseline", "allocation-baseline.json", allocation_baseline),
                            ("lineage_baseline", "lineage-baseline.json", lineage_baseline),
                            ("candidate_identity_allocation", "candidate-allocation.json", allocation)):
        profile["authority_artifacts"].append({"path": str(OUT / name), "role": role,
                                               "sha256": sha(encode(obj))})
    summary = {"schema": "parallel12-level013-local-shard-summary.1", "status": "local_reference_only",
               "four_shard_manifest_sha256": PINS[FOUR / "manifest.json"],
               "predecessor_package_sha256": {"current659": manifest["foundation"]["package"]["sha256"],
                                               **{str(s["legacy_level"]): s["artifacts"]["package"]["sha256"]
                                                  for s in manifest["shards"]}},
               "source_proposal_sha256": PINS[PROPOSAL / "field-proposal.json"],
               "source_handoff_sha256": PINS[PROPOSAL / "allocation-handoff.json"],
               "allocation_floors": floor,
               "counts": {"records": 13, "entities": 54, "sources": 21, "events": 390, "variants": 26,
                          "variant_event_memberships": 780, "round_trip_cells": 25,
                          "round_trip_contact_traversals": 750},
               "source_map": source_map, "routes": handoff["routes"],
               "aggregate_complete": False, "admitted": False, "runtime_eligible": False}
    output = {"package.json": pkg, "identity-registry.json": reg,
              "expected-profile.json": profile, "candidate-allocation.json": allocation,
              "identity-baseline.json": identity_baseline, "allocation-baseline.json": allocation_baseline,
              "lineage-baseline.json": lineage_baseline, "local-summary.json": summary}
    check_global(output, packages, registries)
    return output


def check_global(output: dict, packages: tuple[dict, ...], registries: tuple[dict, ...]) -> None:
    pkg, reg, prof, allocation = (output[n] for n in
                                  ("package.json", "identity-registry.json", "expected-profile.json", "candidate-allocation.json"))
    new = reg["entities"][1:]
    ids = [e["id"] for e in new]
    old_ids = {e["id"] for ancestor in registries for e in ancestor["entities"]}
    need(len(ids) == 53 and len(reg["entities"]) == 54 and len(ids) == len(set(ids)) and
         not old_ids.intersection(ids), "GLOBAL_ENTITY_COLLISION")
    base = registries[0]
    for kind, plural in (("module", "modules"), ("item", "items"), ("variant", "variants")):
        used = [number(e["id"]) for ancestor in registries for e in ancestor["entities"] if e["kind"] == kind]
        mine = [number(e["id"]) for e in new if e["kind"] == kind]
        need(min(mine) > max(used), f"GLOBAL_ID_ORDER {kind}")
        for entry in base["workbook_catalog"]["entries"]:
            bounds = entry.get("reserved_playable_identity_ranges", {}).get(plural)
            if bounds:
                lo, hi = map(number, bounds)
                need(all(not lo <= x <= hi for x in mine), f"RESERVED_ID_COLLISION {kind}")
    events = [e["event_id"] for record in pkg["records"] for e in record["events"]]
    old_events = {e["event_id"] for ancestor in packages for record in ancestor["records"]
                  for e in record["events"]}
    need(len(events) == 390 and len(events) == len(set(events)) and
         not old_events.intersection(events), "GLOBAL_EVENT_COLLISION")
    refs = set(pkg["sources"])
    need(len(refs) == 21 and all(not refs.intersection(p["sources"]) for p in packages) and
         set(prof["event_sources"]) == set(events) and
         all(ref in refs for ref in prof["event_sources"].values()), "GLOBAL_SOURCE_COLLISION")
    old_source_keys = {r["context"].get("local_code") for ancestor in packages for r in ancestor["records"]}
    new_source_keys = [r["context"]["local_code"] for r in pkg["records"]]
    need(len(new_source_keys) == len(set(new_source_keys)) == 13 and
         not old_source_keys.intersection(new_source_keys), "GLOBAL_SOURCE_KEY_COLLISION")
    need(set(allocation["records"]) == {r["id"] for r in pkg["records"]} and
         all(r["lineage"] == {"kind": "new"} and r["content_revision"] == 1 and
             r["runtime_eligible"] is False and r["timing"]["status"] == "unresolved" and
             all(e["onset_q"] is e["duration_q"] is None for e in r["events"])
             for r in pkg["records"]), "LINEAGE_OR_TIMING")
    need(prof["reference_package"] == pkg and prof["reference_registry"] == reg and
         all("workbook_catalog" not in obj for obj in (pkg, reg, prof)) and
         output["local-summary.json"]["aggregate_complete"] is False and
         output["local-summary.json"]["admitted"] is False, "LOCAL_AUTHORITY")


def verify_native(root: Path, output: dict) -> dict:
    report = read(root, OUT / "native-report.json")
    need(report["exit_code"] == 2 and report["valid_reference"] is True and
         report["curriculum_playback_authorized"] is False, "NATIVE_AUTHORITY")
    for name, key in (("package.json", "package_sha256"),
                      ("identity-registry.json", "registry_sha256"),
                      ("expected-profile.json", "profile_sha256")):
        need(report[key] == sha(encode(output[name])) == sha((root / OUT / name).read_bytes()),
             f"NATIVE_INPUT_BINDING {name}")
    need(report["coverage"] == {"events": 390, "expected_entities": 54,
                                "expected_passages": 21, "expected_records": 13,
                                "observed_entities": 54, "observed_passages": 21,
                                "observed_records": 13, "variant_event_memberships": 780,
                                "variants": 26}, "NATIVE_COVERAGE")
    issues = Counter((x["severity"], x["code"]) for x in report["issues"])
    need(issues == {("unresolved", "MODEL_unresolved_time"): 390,
                    ("unresolved", "VARIANT_BINDING_UNRESOLVED"): 26,
                    ("not_admitted", "MODEL_not_admitted"): 13}, "NATIVE_ISSUES")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("build", "verify", "verify-native"))
    args = parser.parse_args()
    output = derive()
    if args.command == "build":
        (ROOT / OUT).mkdir(parents=True, exist_ok=True)
        for name in FILES:
            (ROOT / OUT / name).write_bytes(encode(output[name]))
    else:
        for name in FILES:
            need((ROOT / OUT / name).read_bytes() == encode(output[name]), f"OUTPUT_DRIFT {name}")
        if args.command == "verify-native":
            verify_native(ROOT, output)
    print(json.dumps({"status": "level013_local_nonadmitted_reference",
                      "counts": output["local-summary.json"]["counts"],
                      "allocation_floors": output["local-summary.json"]["allocation_floors"]}, sort_keys=True))


if __name__ == "__main__":
    main()
