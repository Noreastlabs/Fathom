#!/usr/bin/env python3
"""Normalize closed Level10 source evidence before a three-shard manifest seal."""

from __future__ import annotations

import argparse
import copy
import json
import re
from pathlib import Path

import parallel10_global_shard_verifier as globalv


ROOT = Path(__file__).resolve().parents[1]
OUT = Path("Build/parallel-10/three-real-shard-manifest-r05")
SOURCE = Path("Build/parallel-12/level010-schema1-unallocated-r01")
TXT = Path("Notes/music/guitar project/TXT version/108_Finger_Permutations_Level_10_Odd_Count_Position_Transfer.txt")
PDF = Path("Notes/music/guitar project/PDF version/108_Finger_Permutations_Level_10_Odd_Count_Position_Transfer.pdf")
FOUNDATION = Path("Content/controls/curriculum-v1")
R04 = Path("Build/parallel-10/two-real-shard-manifest-r04")
LOCAL10 = Path("Build/parallel-12/level010-local-shard-r01")
PINS = {
    SOURCE / "field-proposal.json": "0a855d720b2cf57ac831accf150a2e1474141657c5b3c99482e6483acf3afe66",
    SOURCE / "allocation-handoff.json": "1064daaffbb1493d6402e7af36f2bf4fecfd15a0f6680f1e2e1c3a9ed3b5adf8",
    TXT: "e5ed078c62295adbb5f6bf00e6821e6eee0b2da73ef42c1714421158b5273226",
    PDF: "1dafdcd177343f0ea147a5479ad654397d85f4b374cf960e264a230db965496b",
    FOUNDATION / "package.json": globalv.FOUNDATION_PINS["package"],
    FOUNDATION / "identity-registry.json": globalv.FOUNDATION_PINS["registry"],
    FOUNDATION / "expected-profile.json": globalv.FOUNDATION_PINS["profile"],
    FOUNDATION / "generation.json": globalv.FOUNDATION_PINS["generation"],
    FOUNDATION / "workbook-coverage.json": globalv.FOUNDATION_PINS["catalog_coverage"],
}
SOURCE_OUTPUTS = ("level010-normalized-source-proposal.json",
                  "level010-source-preallocation-map.json", "completion-contract.json")
SEALED_PINS = {
    Path("Tools/parallel10_global_shard_verifier.py"): "896785c05fc95514a0e812e445498d8eb49907dada16a864f44fb91dc615a14c",
    R04 / "manifest.json": "52be85242a49dbebddec89abc4ee06a5a9d7d805ac27da7528253f9150c3101f",
    R04 / "summary.json": "2e74d8041ab3b6354c1df85e4bce8f9d46f5b0c2422e9d27209a5e940f96ab2a",
    LOCAL10 / "package.json": "b4e59b36a9dd20a8dbdc8b16a9c20c8eafb6d054665f83ec86742424c57896d0",
    LOCAL10 / "identity-registry.json": "7415e720ffab238ccd43a82e30a9f486e402d8c33f19865ae466aa308ba52594",
    LOCAL10 / "expected-profile.json": "fca1af76befb72b9fdf4b828821435817c13fd5c884bac11c6f95a9cd563c90e",
    LOCAL10 / "native-report.json": "5bb9c054a7a5e77315d2f273deb26583ab2ebb46264429c52573781f94e89d1e",
    LOCAL10 / "candidate-allocation.json": "9474561fe9a097313307be06ca0c38b707bcb7f3a17760a4a226ecf5633a5e65",
    LOCAL10 / "identity-baseline.json": "cd2a5c2ae7f472618d1a4d3129be7e72401a841db2fc95db552215107bf4bf35",
    LOCAL10 / "allocation-baseline.json": "adb5406f2113c1feacb795479ea2112ae12b53310a2ff11b44936fdfc3aacb7d",
    LOCAL10 / "lineage-baseline.json": "d0bb0eeba0b7484b513a0e44784b34b1fc3f42c5cd0f2596ac678a94ffded932",
}
MANIFEST_OUTPUTS = ("level010-source-map.json", "manifest.json", "summary.json")


class PreworkError(ValueError):
    pass


def require(ok: bool, code: str) -> None:
    if not ok:
        raise PreworkError(code)


def read(relative: Path) -> dict:
    return json.loads((ROOT / relative).read_text())


def source_prework() -> dict[str, dict]:
    for path, expected in PINS.items():
        require(globalv.digest(ROOT, str(path)) == expected, f"INPUT_PIN_DRIFT {path}")
    proposal, handoff = read(SOURCE / "field-proposal.json"), read(SOURCE / "allocation-handoff.json")
    require(handoff["proposal_sha256"] == PINS[SOURCE / "field-proposal.json"] and
            handoff["no_admission"] is True and handoff["record_count"] == 108 and
            handoff["event_count"] == 10368 and handoff["variant_count"] == 864 and
            len(proposal["records"]) == len(handoff["source_map"]) == 108 and
            proposal["source_pins"][str(TXT)]["sha256"] == PINS[TXT] and
            proposal["source_pins"][str(PDF)]["sha256"] == PINS[PDF], "SOURCE_SCOPE")
    txt_lines = (ROOT / TXT).read_text().splitlines()
    normalized, preallocation = [], []
    for index, (row, mapping) in enumerate(zip(proposal["records"], handoff["source_map"], strict=True), 1):
        key = f"L10-set{(index-1)//12+1:02d}-ex{index:03d}"
        require(row["source_local_key"] == mapping["source_local_key"] == key and
                row["mode_source_refs"] == mapping["modes"] and
                len(mapping["modes"]) == 2 and
                [x["mode"] for x in mapping["modes"]] == ["mode_a", "mode_b"] and
                len(row["variant_memberships"]) == 8, "MODE_MAP")
        refs = row["schema1_fields"]["source_refs"]
        require(refs == [mapping["modes"][0]["txt"], mapping["modes"][0]["pdf"],
                         mapping["modes"][1]["txt"], mapping["modes"][1]["pdf"],
                         "L10-TXT1-1-33"], "MODE_REFS")
        for mode in mapping["modes"]:
            match = re.fullmatch(r"L10-TXT1-(\d+)-(\d+)", mode["txt"])
            require(match is not None, "TXT_SPAN_REF")
            first, last = map(int, match.groups())
            require(1 <= first <= last <= len(txt_lines) and
                    globalv.sha("\n".join(txt_lines[first-1:last]).encode()) ==
                    mode["txt_passage_sha256"], "TXT_SPAN_HASH")
            require(re.fullmatch(r"L10-PDF1-p\d+", mode["pdf"]) is not None, "PDF_REF")
        digest = globalv.sha(globalv.encoded(row))
        normalized.append({"source_local_key": key, "source_record_sha256": digest,
                           "source_refs": {"txt": refs[0], "pdf": refs[1]},
                           "mode_refs": mapping["modes"]})
        preallocation.append({"source_local_key": key, "source_record_sha256": digest,
                              "all_source_refs": refs, "mode_refs": mapping["modes"]})
    require(len({x["source_local_key"] for x in normalized}) == 108 and
            len({x for row in preallocation for x in row["all_source_refs"] if x.startswith("L10-TXT1-")}) == 217,
            "SOURCE_KEY_COVERAGE")
    normalized_proposal = {"schema": "global-shard-source-proposal-bridge.1",
                           "upstream_field_proposal_path": str(SOURCE / "field-proposal.json"),
                           "upstream_field_proposal_sha256": PINS[SOURCE / "field-proposal.json"],
                           "upstream_handoff_path": str(SOURCE / "allocation-handoff.json"),
                           "upstream_handoff_sha256": PINS[SOURCE / "allocation-handoff.json"],
                           "records": normalized}
    source_map = {"schema": "global-shard-source-preallocation-map.1",
                  "workbook_id": "fg:workbook:000010",
                  "source_proposal_sha256": globalv.sha(globalv.encoded(normalized_proposal)),
                  "records": preallocation}
    registry = read(FOUNDATION / "identity-registry.json")
    catalog = registry["workbook_catalog"]
    complete = [e["workbook_id"] for e in catalog["entries"] if e["whole_workbook_complete"] is True]
    admitted = [e["workbook_id"] for e in catalog["entries"] if e["admitted"] is True]
    foundation_workbooks = [e["id"] for e in registry["entities"] if e["kind"] == "workbook"]
    require(len(catalog["entries"]) == 105 and len(foundation_workbooks) == 16 and
            not complete and not admitted, "COMPLETION_BASELINE_DRIFT")
    completion = {"schema": "preparatory-completion-contract.1",
                  "catalog_coverage_sha256": PINS[FOUNDATION / "workbook-coverage.json"],
                  "catalog_entry_count": 105, "foundation_workbook_identity_count": 16,
                  "whole_source_complete_workbooks": complete,
                  "admitted_workbooks": admitted,
                  "release_authority_present": False,
                  "aggregate_complete": False, "runtime_admitted": False,
                  "rule": "Workbook identity count alone never proves full source coverage, curriculum acceptance or release authority"}
    return {SOURCE_OUTPUTS[0]: normalized_proposal,
            SOURCE_OUTPUTS[1]: source_map, SOURCE_OUTPUTS[2]: completion}


def manifest_inputs() -> dict[str, dict]:
    source_outputs = source_prework()
    for name, obj in source_outputs.items():
        require((ROOT / OUT / name).read_bytes() == globalv.encoded(obj), f"SOURCE_OUTPUT_DRIFT {name}")
    for path, expected in SEALED_PINS.items():
        require(globalv.digest(ROOT, str(path)) == expected, f"SEALED_PIN_DRIFT {path}")
    r04 = read(R04 / "manifest.json")
    require(r04["validated_workbooks"] == [7, 8] and len(r04["shards"]) == 2 and
            r04["aggregate_complete"] is False and r04["admitted"] is False,
            "R04_SCOPE")
    package = read(LOCAL10 / "package.json")
    proposal = read(SOURCE / "field-proposal.json")
    handoff = read(SOURCE / "allocation-handoff.json")
    preallocation = source_outputs[SOURCE_OUTPUTS[1]]["records"]
    normalized_proposal = source_outputs[SOURCE_OUTPUTS[0]]
    require(len(package["records"]) == len(proposal["records"]) ==
            len(handoff["source_map"]) == len(preallocation) == 108, "LEVEL10_SCOPE")
    entries = []
    for local, source, hand, pre in zip(package["records"], proposal["records"],
                                        handoff["source_map"], preallocation, strict=True):
        require(source["source_local_key"] == hand["source_local_key"] ==
                pre["source_local_key"] and local["workbook_id"] == "fg:workbook:000010" and
                local["legacy_level"] == 10 and local["source_refs"] == pre["all_source_refs"],
                "LEVEL10_RECORD_SOURCE")
        expected = copy.deepcopy(source["schema1_fields"])
        for key in ("id", "module_id", "workbook_id", "lineage"):
            expected[key] = local[key]
        require(len(expected["events"]) == len(local["events"]) == 96 and
                len(expected["variants"]) == len(local["variants"]) ==
                len(source["variant_memberships"]) == 8, "LEVEL10_RECORD_COVERAGE")
        for e, actual in zip(expected["events"], local["events"], strict=True):
            require(e["event_id"] is None and actual["onset_q"] is None and
                    actual["duration_q"] is None, "LEVEL10_EVENT_AUTHORITY")
            e["event_id"] = actual["event_id"]
        for v, actual, member in zip(expected["variants"], local["variants"],
                                      source["variant_memberships"], strict=True):
            require(v["id"] is None and v["event_ids"] is None and
                    v["label"] == actual["label"] == member["label"] and
                    actual["event_ids"] == [local["events"][i-1]["event_id"]
                                            for i in member["event_local_ordinals"]] and
                    len(member["landing_event_local_ordinals"]) == 6,
                    "LEVEL10_VARIANT_SOURCE")
            v["id"], v["event_ids"] = actual["id"], actual["event_ids"]
        require(expected == local, "LEVEL10_FIELD_PROJECTION")
        for mode in hand["modes"]:
            require(package["sources"][mode["txt"]]["text_sha256"] ==
                    mode["txt_passage_sha256"] and
                    package["sources"][mode["txt"]]["sha256"] == PINS[TXT] and
                    package["sources"][mode["pdf"]]["sha256"] == PINS[PDF],
                    "LEVEL10_MODE_PASSAGE")
        entries.append({"record_id": local["id"], "source_local_key": pre["source_local_key"],
                        "source_record_sha256": pre["source_record_sha256"],
                        "source_refs": pre["all_source_refs"][:2],
                        "all_source_refs": pre["all_source_refs"],
                        "mode_refs": pre["mode_refs"]})
    source_map = {"schema": "global-shard-source-map.1",
                  "workbook_id": "fg:workbook:000010",
                  "source_proposal_sha256": globalv.sha(globalv.encoded(normalized_proposal)),
                  "entries": entries}
    artifacts = {role: {"path": str(LOCAL10 / name), "sha256": SEALED_PINS[LOCAL10 / name]}
                 for role, name in globalv.LOCAL_NAMES.items()}
    artifacts["source_proposal"] = {"path": str(OUT / SOURCE_OUTPUTS[0]),
                                    "sha256": source_map["source_proposal_sha256"]}
    artifacts["source_map"] = {"path": str(OUT / MANIFEST_OUTPUTS[0]),
                               "sha256": globalv.sha(globalv.encoded(source_map))}
    manifest = {**r04, "shards": [*r04["shards"],
                                  {"workbook_id": "fg:workbook:000010", "legacy_level": 10,
                                   "artifacts": artifacts}],
                "validated_workbooks": [7, 8, 10], "aggregate_complete": False,
                "admitted": False,
                "completion_contract": {"path": str(OUT / SOURCE_OUTPUTS[2]),
                                        "sha256": globalv.sha(globalv.encoded(source_outputs[SOURCE_OUTPUTS[2]]))}}
    return {MANIFEST_OUTPUTS[0]: source_map, MANIFEST_OUTPUTS[1]: manifest}


def verify_manifest() -> dict:
    expected = manifest_inputs()
    for name, obj in expected.items():
        require((ROOT / OUT / name).read_bytes() == globalv.encoded(obj), f"MANIFEST_OUTPUT_DRIFT {name}")
    manifest = expected[MANIFEST_OUTPUTS[1]]
    completion = source_prework()[SOURCE_OUTPUTS[2]]
    require(manifest["completion_contract"]["sha256"] == globalv.sha(globalv.encoded(completion)) and
            completion["aggregate_complete"] is False and
            completion["release_authority_present"] is False and
            not completion["whole_source_complete_workbooks"] and
            not completion["admitted_workbooks"], "COMPLETION_AUTHORITY")
    summary = globalv.verify(ROOT, manifest)
    require(summary["validated_workbooks"] == [7, 8, 10] and summary["shard_count"] == 3 and
            summary["aggregate_complete"] is False and summary["admitted"] is False and
            summary["new_counts"] == {"records": 324, "entities": 2163,
                                      "events": 22464, "sources": 473, "variants": 1512} and
            summary["next_allocation_floor"] == {"module": 1020, "item": 1020, "variant": 6946},
            "THREE_REAL_SHARD_COUNTS")
    return {**summary, "full_105_workbook_source_coverage_verified": False,
            "curriculum_acceptance": "Pending", "runtime_admission": False,
            "completion_contract_sha256": manifest["completion_contract"]["sha256"],
            "source_bridge_upstream_sha256": {
                "field_proposal": PINS[SOURCE / "field-proposal.json"],
                "allocation_handoff": PINS[SOURCE / "allocation-handoff.json"]}}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build-source", "verify-source", "build-manifest", "verify-manifest"))
    args = parser.parse_args()
    target = ROOT / OUT
    if args.command in ("build-source", "verify-source"):
        outputs = source_prework()
        if args.command == "build-source":
            target.mkdir(parents=True, exist_ok=True)
            require(all(not (target / name).exists() and not (target / name).is_symlink()
                        for name in SOURCE_OUTPUTS), "OUTPUT_EXISTS")
            for name, obj in outputs.items():
                (target / name).write_bytes(globalv.encoded(obj))
        else:
            for name, obj in outputs.items():
                require((target / name).read_bytes() == globalv.encoded(obj), f"OUTPUT_DRIFT {name}")
        print(json.dumps({"status": "level010_source_bridge_ready", "records": 108,
                          "modes": 216, "aggregate_complete": False, "runtime_admitted": False},
                         sort_keys=True))
    elif args.command == "build-manifest":
        outputs = manifest_inputs()
        require(all(not (target / name).exists() and not (target / name).is_symlink()
                    for name in MANIFEST_OUTPUTS), "OUTPUT_EXISTS")
        for name, obj in outputs.items():
            (target / name).write_bytes(globalv.encoded(obj))
        summary = verify_manifest()
        (target / MANIFEST_OUTPUTS[2]).write_bytes(globalv.encoded(summary))
        print(json.dumps(summary, sort_keys=True))
    else:
        summary = verify_manifest()
        require((target / MANIFEST_OUTPUTS[2]).read_bytes() == globalv.encoded(summary),
                "SUMMARY_DRIFT")
        print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
