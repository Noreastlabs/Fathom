#!/usr/bin/env python3
"""Bridge P12 Level8 provenance and verify two genuine native workbook shards."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import parallel10_global_shard_verifier as globalv


ROOT = Path(__file__).resolve().parents[1]
OUT = Path("Build/parallel-10/two-real-shard-manifest-r04")
R03 = Path("Build/parallel-10/global-shard-verifier-r03")
P12 = Path("Build/parallel-12/level008-local-shard-r01")
P12_SOURCE = Path("Build/parallel-12/level008-schema1-unallocated-r01")
TXT8 = Path("Notes/music/guitar project/TXT version/108_Finger_Permutations_Level_8_Two_Position_Ladder.txt")
PDF8 = Path("Notes/music/guitar project/PDF version/108_Finger_Permutations_Level_8_Two_Position_Ladder.pdf")
PINS = {
    Path("Tools/parallel10_global_shard_verifier.py"): "896785c05fc95514a0e812e445498d8eb49907dada16a864f44fb91dc615a14c",
    R03 / "manifest.json": "3c4bdc8e5ac49e839b401ef5257931c1f141f71e20a35e7b0731affdb0e4cf02",
    R03 / "level007-source-map.json": "ac108b0265d2427ecc605baafd651b74cb87b32a24b8daef6c2a6192b74d7b7a",
    P12 / "package.json": "588947d8420086f3259626caf704473e08242a2e543714e34bcc01cb0211c032",
    P12 / "identity-registry.json": "74affebdad7c3b46f3477c2ac8eabaa03bf2d899338b313a53551e4d5d0affc7",
    P12 / "expected-profile.json": "e2697b96d6eadc1942dcfe2870da22a364e4e6d19e967adb37566922fae95284",
    P12 / "native-report.json": "a5733c5065e1de86d8834c04bf306efc210acce0a921136291824656106fc9d6",
    P12 / "candidate-allocation.json": "e4757064fd1b6e0f7d8b1d620edb41f3d8385df0df4f4124560cab42a5ce81ec",
    P12 / "identity-baseline.json": "cd2a5c2ae7f472618d1a4d3129be7e72401a841db2fc95db552215107bf4bf35",
    P12 / "allocation-baseline.json": "055e3bb340a6d1768cf1da4c89ffe5a17f251563ddebdd78fbf9b01813628090",
    P12 / "lineage-baseline.json": "d0bb0eeba0b7484b513a0e44784b34b1fc3f42c5cd0f2596ac678a94ffded932",
    P12_SOURCE / "field-proposal.json": "9434ca6e21dd35a6b84e4ea2b4f699dd505d4f93901458b3651d9e097992da18",
    P12_SOURCE / "allocation-handoff.json": "7461d176a7c1af46cf5c705c6cb69bd4f8395e154fba08edeb7390b57ea942b8",
    TXT8: "0cba6885ed917013d5ceda5e0c231c568b4aa99be4c8c0e23941295a3fa5926a",
    PDF8: "750f9b14962e71bc9ed0dc48a6f9343f2a1d5d14363858f7b9462187fc338829",
}
OUTPUTS = ("level008-normalized-source-proposal.json", "level008-source-map.json",
           "manifest.json", "summary.json")


class BridgeError(ValueError):
    pass


def require(ok: bool, code: str) -> None:
    if not ok:
        raise BridgeError(code)


def load(path: Path) -> dict:
    return json.loads((ROOT / path).read_text())


def derive() -> dict[str, dict]:
    for path, expected in PINS.items():
        require(globalv.digest(ROOT, str(path)) == expected, f"INPUT_PIN_DRIFT {path}")
    r03 = load(R03 / "manifest.json")
    require(r03["validated_workbooks"] == [7] and len(r03["shards"]) == 1 and
            r03["admitted"] is False and r03["aggregate_complete"] is False,
            "R03_SCOPE")
    proposal, handoff = (load(P12_SOURCE / n) for n in
                         ("field-proposal.json", "allocation-handoff.json"))
    package = load(P12 / "package.json")
    require(handoff["proposal_sha256"] == PINS[P12_SOURCE / "field-proposal.json"] and
            proposal["source_pins"][str(TXT8)]["sha256"] == PINS[TXT8] and
            proposal["source_pins"][str(PDF8)]["sha256"] == PINS[PDF8] and
            handoff["no_admission"] is True and handoff["event_count"] == 10368 and
            handoff["variant_count"] == 432 and
            len(proposal["records"]) == len(handoff["source_map"]) ==
            len(package["records"]) == 108, "P12_SOURCE_SCOPE")
    normalized, mapping = [], []
    for row, source, record in zip(proposal["records"], handoff["source_map"], package["records"], strict=True):
        require(row["source_local_key"] == source["source_local_key"] and
                record["workbook_id"] == "fg:workbook:000008" and
                record["legacy_level"] == 8 and
                row["schema1_fields"]["source_refs"] == record["source_refs"] and
                record["source_refs"][:2] == [source["txt"], source["pdf"]] and
                package["sources"][source["txt"]]["text_sha256"] == source["txt_passage_sha256"] and
                package["sources"][source["txt"]]["sha256"] == PINS[TXT8] and
                package["sources"][source["pdf"]]["sha256"] == PINS[PDF8],
                "P12_SOURCE_PROJECTION")
        digest = globalv.sha(globalv.encoded(row))
        normalized.append({"source_local_key": row["source_local_key"],
                           "source_record_sha256": digest,
                           "source_refs": {"txt": source["txt"], "pdf": source["pdf"]}})
        mapping.append({"record_id": record["id"],
                        "source_local_key": row["source_local_key"],
                        "source_record_sha256": digest,
                        "source_refs": [source["txt"], source["pdf"]]})
    require(len({x["source_local_key"] for x in normalized}) == 108 and
            len({x["record_id"] for x in mapping}) == 108, "P12_SOURCE_KEYS")
    normalized_proposal = {"schema": "global-shard-source-proposal-bridge.1",
                           "upstream_field_proposal_path": str(P12_SOURCE / "field-proposal.json"),
                           "upstream_field_proposal_sha256": PINS[P12_SOURCE / "field-proposal.json"],
                           "upstream_handoff_path": str(P12_SOURCE / "allocation-handoff.json"),
                           "upstream_handoff_sha256": PINS[P12_SOURCE / "allocation-handoff.json"],
                           "records": normalized}
    normalized_ref = {"path": str(OUT / OUTPUTS[0]),
                      "sha256": globalv.sha(globalv.encoded(normalized_proposal))}
    source_map = {"schema": "global-shard-source-map.1", "workbook_id": "fg:workbook:000008",
                  "source_proposal_sha256": normalized_ref["sha256"], "entries": mapping}
    map_ref = {"path": str(OUT / OUTPUTS[1]), "sha256": globalv.sha(globalv.encoded(source_map))}
    artifacts = {role: {"path": str(P12 / name), "sha256": PINS[P12 / name]}
                 for role, name in globalv.LOCAL_NAMES.items()}
    artifacts["source_proposal"] = normalized_ref
    artifacts["source_map"] = map_ref
    manifest = {**r03, "shards": [r03["shards"][0],
                                   {"workbook_id": "fg:workbook:000008", "legacy_level": 8,
                                    "artifacts": artifacts}],
                "validated_workbooks": [7, 8], "aggregate_complete": False,
                "admitted": False}
    return {OUTPUTS[0]: normalized_proposal, OUTPUTS[1]: source_map,
            OUTPUTS[2]: manifest}


def verify() -> dict:
    expected = derive()
    for name, obj in expected.items():
        require((ROOT / OUT / name).read_bytes() == globalv.encoded(obj), f"OUTPUT_DRIFT {name}")
    summary = globalv.verify(ROOT, expected["manifest.json"])
    require(summary["validated_workbooks"] == [7, 8] and summary["shard_count"] == 2 and
            summary["aggregate_complete"] is False and summary["admitted"] is False and
            summary["new_counts"] == {"records": 216, "entities": 1082,
                                      "events": 12096, "sources": 238, "variants": 648} and
            summary["next_allocation_floor"] == {"module": 912, "item": 912, "variant": 6082},
            "TWO_REAL_SHARD_COUNTS")
    return {**summary, "full_105_workbook_source_coverage_verified": False,
            "curriculum_acceptance": "Pending", "runtime_admission": False,
            "source_bridge_upstream_sha256": {
                "field_proposal": PINS[P12_SOURCE / "field-proposal.json"],
                "allocation_handoff": PINS[P12_SOURCE / "allocation-handoff.json"]}}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "verify"))
    args = parser.parse_args()
    if args.command == "build":
        expected = derive()
        target = ROOT / OUT
        target.mkdir(parents=True, exist_ok=True)
        require(all(not (target / n).exists() and not (target / n).is_symlink()
                    for n in OUTPUTS), "OUTPUT_EXISTS")
        for name, obj in expected.items():
            (target / name).write_bytes(globalv.encoded(obj))
        summary = verify()
        (target / OUTPUTS[3]).write_bytes(globalv.encoded(summary))
        print(json.dumps(summary, sort_keys=True))
    else:
        summary = verify()
        require((ROOT / OUT / OUTPUTS[3]).read_bytes() == globalv.encoded(summary),
                "SUMMARY_DRIFT")
        print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
