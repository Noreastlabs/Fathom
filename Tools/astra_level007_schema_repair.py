#!/usr/bin/env python3
"""Pinned, Build-only Level7 r02 representation repair; no source/schema inference."""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = Path("Build/parallel-10/level007-schema1-overlay-r01")
PRE = Path("Build/parallel-12/level009-schema1-overlay-r02b")
SOURCE = Path("Build/parallel-10/level007-source-proposal-adapter-r01/proposal-01.json")
TXT = Path("Notes/music/guitar project/TXT version/108_Finger_Permutations_Level_7_Three_String_Skip_Relay.txt")
PDF = Path("Notes/music/guitar project/PDF version/108_Finger_Permutations_Level_7_Three_String_Skip_Relay.pdf")
OUT = Path("Build/astra-level007-schema/r02")
SIDECAR = OUT / "source-identity-map.json"
PINS = {
    BASE / "package.json": "8a9f10f34de7f08ad1098a8959d30858e7156c92acf101980067725d5f0a013b",
    BASE / "identity-registry.json": "7c1567712b37ae838cfebe8a67837fb7e60d020418aff858dbf622c2e46932df",
    BASE / "expected-profile.json": "b70060ece8f62646fbff46fd4b8338176e43f66f2575cffca55236e33b87d12b",
    BASE / "candidate-allocation.json": "70c574a03db26d4d47bee738dba62c0fbff7da8400a58568549f752ccb473e27",
    BASE / "transaction.json": "ee191d97ec85b2e3a8d5da695560bda3b613f34ea6020949dedd2ebc81c23f45",
    BASE / "generation.json": "bba4f1623c9a36dd37f12834f95873b459c2ba9f24cabbc2859a0df193786154",
    BASE / "proposal.json": "647b8c16ebc031c3930756deb2bfe4f913a6447f829a4fe85d338c09d2e39252",
    PRE / "package.json": "766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255",
    PRE / "identity-registry.json": "5d265859e1e8a5a530a0e53d88b019a1c920f3bba6cccb4ef0fef2f7640007e5",
    SOURCE: "8838eaed97e30fc384d2ab8e51bc2def3f7f9f9df912d2543d64674d5dc0a5c9",
    TXT: "467d1401237e34633efc4c517fa98d8190f0b47346a7b34be9d2548924883b61",
    PDF: "5c8607cff40801acb13f5e08dd2988b2ff943593eb084de2801f05f507a6c4ea",
}


class RepairError(ValueError):
    pass


def require(ok, code):
    if not ok:
        raise RepairError(code)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, allow_nan=False,
                       sort_keys=True, separators=(",", ":")) + "\n").encode()


def strict_load(data):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "DUPLICATE_KEY " + key)
            result[key] = value
        return result

    def nonfinite(value):
        raise RepairError("NONFINITE " + value)

    return json.loads(data, object_pairs_hook=pairs, parse_constant=nonfinite)


def load_inputs(root=ROOT):
    values = {}
    for rel, expected in PINS.items():
        data = (root / rel).read_bytes()
        require(sha(data) == expected, "PIN_DRIFT " + str(rel))
        if rel.suffix == ".json":
            values[rel] = strict_load(data)
    return values


def unique(values, code):
    require(len(values) == len(set(values)), code)
    return set(values)


def check_source_map(records, rows, allocation, source_cases):
    require(len(records) == len(rows) == len(source_cases) == 108, "NEW_SCOPE")
    unique([r["source_local_key"] for r in rows], "DUPLICATE_SOURCE_LOCAL_KEY")
    unique([r["item_id"] for r in rows], "DUPLICATE_SOURCE_ITEM")
    for index, (record, row, case) in enumerate(zip(records, rows, source_cases)):
        key = f"L7-set{index // 12 + 1:02d}-ex{index + 1:03d}"
        require(row["item_id"] == record["id"] == f"fg:item:{696 + index:06d}", "SOURCE_ITEM")
        require(row["source_local_key"] == record["context"]["source_local_key"] ==
                case["source_local_key"] == key, "SOURCE_KEY")
        require(row["exercise_number"] == int(case["exercise_number"]) == index + 1 and
                row["code"] == case["source_code"] == record["context"]["local_code"] and
                row["source_record_sha256"] == case["source_record_sha256"], "SOURCE_RECORD")
        require(row["txt"] == case["source_refs"]["txt"] == record["source_refs"][0] and
                row["pdf"] == case["source_refs"]["pdf"] == record["source_refs"][1], "SOURCE_REFS")
        entry = allocation[record["id"]]
        require(len(entry["occurrences"]) == 16 and len(entry["variants"]) == 2, "SOURCE_ALLOCATION")
        require(all(k.startswith(key + ":") for k in entry["occurrences"]), "SOURCE_OCCURRENCE_KEY")
        require(set(entry["occurrences"].values()) == {e["event_id"] for e in record["events"]} and
                set(entry["variants"].values()) == {v["id"] for v in record["variants"]}, "SOURCE_ALLOCATION")


def check_baseline(inputs):
    package, registry = inputs[BASE / "package.json"], inputs[BASE / "identity-registry.json"]
    records, entities = package["records"], registry["entities"]
    require(len(records) == 767 and len(entities) == 6769, "BASE_SCOPE")
    unique([r["id"] for r in records], "DUPLICATE_RECORD")
    unique([e["id"] for e in entities], "DUPLICATE_ENTITY")
    unique([e["event_id"] for r in records for e in r["events"]], "DUPLICATE_EVENT")
    unique([v["id"] for r in records for v in r["variants"]], "DUPLICATE_VARIANT")
    require(records[:659] == inputs[PRE / "package.json"]["records"] and
            entities[:6336] == inputs[PRE / "identity-registry.json"]["entities"], "PREDECESSOR_DRIFT")
    transaction, allocation = inputs[BASE / "transaction.json"], inputs[BASE / "candidate-allocation.json"]
    require(entities[6336:] == transaction["new_entities"], "NEW_ENTITY_DRIFT")
    require(records[659:] == inputs[BASE / "proposal.json"]["records"], "R01_PROPOSAL_DRIFT")
    require(set(allocation["records"]) == {r["id"] for r in records}, "ALLOCATION_COVERAGE")
    require({r["id"]: allocation["records"][r["id"]] for r in records[659:]} ==
            transaction["records"], "TRANSACTION_ALLOCATION")
    check_source_map(records[659:], transaction["source_map"], transaction["records"], inputs[SOURCE]["records"])
    require(sum(len(r["events"]) for r in records[659:]) == 1728 and
            sum(len(r["variants"]) for r in records[659:]) == 216, "NEW_EVENT_VARIANT_SCOPE")
    profile = inputs[BASE / "expected-profile.json"]
    require(profile["reference_package"] == {k: v for k, v in package.items() if k != "workbook_catalog"} and
            profile["reference_registry"] == {k: v for k, v in registry.items() if k != "workbook_catalog"}, "R01_PROFILE")
    for record in records[659:]:
        require(record["runtime_eligible"] is False and record["timing"]["status"] == "unresolved", "ADMISSION_TIMING")
        require(all(e["onset_q"] is None and e["duration_q"] is None for e in record["events"]), "EVENT_TIMING")
        require(all(profile["event_sources"][e["event_id"]] == record["source_refs"][0]
                    for e in record["events"]), "EVENT_SOURCE")
        require(record["context"]["tuning_open_midi"] == [40, 45, 50, 55, 59, 64] and
                "capo" not in record["context"], "INSTRUMENT_FACT_DRIFT")


def metadata(key):
    return {"kind": "representation_metadata", "basis": str(SIDECAR),
            "text": "Source-local identity: " + key}


def repaired_record(original):
    record = deepcopy(original)
    key = record["context"].pop("source_local_key")
    record["normalization"].append(metadata(key))
    return record


def derive(inputs):
    check_baseline(inputs)
    package = deepcopy(inputs[BASE / "package.json"])
    package["content_version"] = "curriculum-v1-level007-767-build-only-candidate.2"
    package["records"][659:] = [repaired_record(r) for r in package["records"][659:]]
    registry = inputs[BASE / "identity-registry.json"]
    allocation = inputs[BASE / "candidate-allocation.json"]
    transaction = inputs[BASE / "transaction.json"]
    rows = []
    for record, row in zip(package["records"][659:], transaction["source_map"]):
        rows.append({**row, "record_canonical_sha256": sha(encoded(record)[:-1]),
                     "occurrences": transaction["records"][record["id"]]["occurrences"],
                     "variants": transaction["records"][record["id"]]["variants"]})
    sidecar = {"version": "astra-level007-source-identity-map.1", "runtime_eligible": False,
               "classification": "build_only_nonadmitted_representation_repair",
               "inputs": [{"path": str(p), "sha256": digest} for p, digest in PINS.items()],
               "records": rows}
    profile = deepcopy(inputs[BASE / "expected-profile.json"])
    profile["reference_package"] = {k: v for k, v in package.items() if k != "workbook_catalog"}
    refs = [a for a in profile["authority_artifacts"] if a["role"] == "candidate_identity_allocation"]
    require(len(refs) == 1, "ALLOCATION_AUTHORITY")
    refs[0].update(path=str(OUT / "candidate-allocation.json"), sha256=sha(encoded(allocation)))
    profile["authority_artifacts"].append({"path": str(SIDECAR), "sha256": sha(encoded(sidecar)),
                                           "role": "source_identity_allocation"})
    artifacts = {"package.json": package, "identity-registry.json": registry,
                 "expected-profile.json": profile, "candidate-allocation.json": allocation,
                 "source-identity-map.json": sidecar}
    generation = deepcopy(inputs[BASE / "generation.json"])
    generation["classification"] = "Build-only Level7 r02 representation repair; native/source decisions Pending; no admission"
    generation["identities"] = {name: sha(encoded(value)) for name, value in artifacts.items()}
    artifacts["generation.json"] = generation
    return artifacts


def verify(artifacts, inputs):
    expected = derive(inputs)
    require(set(artifacts) == set(expected), "OUTPUT_FILES")
    for name, value in expected.items():
        require(encoded(artifacts[name]) == encoded(value), "OUTPUT_DRIFT " + name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "verify"))
    args = parser.parse_args()
    destination = ROOT / OUT
    if args.command == "build":
        require(not destination.exists() and not destination.is_symlink(), "OUTPUT_EXISTS")
    inputs = load_inputs()
    expected = derive(inputs)
    if args.command == "build":
        destination.mkdir(parents=True, exist_ok=False)
        for name, value in expected.items():
            with (destination / name).open("xb") as stream:
                stream.write(encoded(value))
    else:
        require({p.name for p in destination.iterdir()} == set(expected), "OUTPUT_FILES")
        for name, value in expected.items():
            require(not (destination / name).is_symlink() and
                    (destination / name).read_bytes() == encoded(value), "OUTPUT_DRIFT " + name)
    print(json.dumps({"status": args.command + "_verified", "records": 767,
                      "new_records": 108, "new_variants": 216, "new_events": 1728,
                      "source_local_keys": 108, "native_reference": "Pending",
                      "admission": False, "identities": {name: sha(encoded(value))
                                                          for name, value in expected.items()}}, sort_keys=True))


if __name__ == "__main__":
    main()
