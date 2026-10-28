#!/usr/bin/env python3
"""Focused source and integrity checks for the A42 private packet."""
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "Tools/exercise-impl-shard-a42-r01/build_packet.py"
spec = importlib.util.spec_from_file_location("a42_builder", SCRIPT)
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


def validate(raw, manifest, keys, prior):
    rows = [json.loads(line) for line in raw.splitlines()]
    assert len(rows) == 78
    assert [r["package_key"] for r in rows] == keys
    assert len(set(keys)) == 78
    assert hashlib.sha256(raw.encode()).hexdigest() == manifest["packet_sha256"]
    txt = (ROOT / next(k for k in builder.PINS if str(k).endswith(".txt"))).read_text().splitlines()
    counts = {"B": (16, 16), "C": (6, 4), "D": (24, 12), "E": (5, 1), "F": (7, 4)}
    family_count = {}
    for r in rows:
        key = r["package_key"]
        family = r["family"]
        family_count[family] = family_count.get(family, 0) + 1
        old = prior[key]
        assert r["source_identity"] == old["source_identity"]
        assert r["source_lines"] == old["source_payload"]["exact_unit_lines"]
        assert len(r["source_refs"]) == 2
        for ref in r["source_refs"]:
            assert hashlib.sha256((ROOT / ref["path"]).read_bytes()).hexdigest() == ref["sha256"]
        for ref in r["source_refs"]:
            if ref["path"].endswith(".txt"):
                loc = ref["locator"]
                lines = txt[loc["line_start"] - 1:loc["line_end"]]
                assert all(line in lines for line in r["source_lines"])
        assert r["timing_authority"]["numeric_projection"] is None
        assert r["timing_authority"]["bpm"] is None
        assert r["source_conflicts"] == []
        assert r["unresolved_fields"]
        assert r["actual_pick_attacks"] == sum(bool(c.get("pick_attack")) for c in r["ordered_contacts"])
        if family in counts:
            expect_contacts, expect_attacks = counts[family]
            assert (len(r["ordered_contacts"]), r["actual_pick_attacks"]) == (expect_contacts, expect_attacks)
        if family == "B":
            assert len(r["realizations"]) == 2
            assert len(r["realizations"][1]["contacts"]) == 16
            assert r["realizations"][1]["contacts"][0]["fret"] == 17
            assert all(x["pick_attack"] for x in r["realizations"][1]["contacts"])
        if family == "H" and r["ordered_contacts"]:
            assert r["actual_pick_attacks"] == 4
            assert len(r["counted_events"]) in (8, 9)
        if family == "H" and not r["ordered_contacts"]:
            assert len(r["linked_phrases"]) == 5
            assert sum(len(p["counted_events"]) for p in r["linked_phrases"]) == 43
            assert sum(p["pick_attacks"] for p in r["linked_phrases"]) == 20
            assert [p["unit"] for p in r["rest_contract"]["passes"]] == ["source bar", "source beat", "source beat", "extra pause"]
    assert family_count == {"B": 6, "C": 24, "D": 5, "E": 24, "F": 13, "H": 6}
    return family_count


def main():
    keys, prior = builder.load()
    official = {r["package_key"]: r for r in map(json.loads, (ROOT / "Results/level-oracle/exercise-completeness-r01/reviewed-handoff-r01/wbs-annex-candidate.jsonl").read_text().splitlines())}
    index = {r["package_key"]: r for r in map(json.loads, (ROOT / "Build/fullscope-private-a-r01/semantic-overlay-index-r13/effective-range-index.jsonl").read_text().splitlines())}
    assert all(official[k]["status"] == "Pending" for k in keys)
    assert all(index[k]["level"] == 42 and index[k]["category"] == "implementation_or_interpretation_pending" and not index[k]["Accepted"] for k in keys)
    packet = (ROOT / builder.OUTPUT).read_text()
    manifest = json.loads((ROOT / builder.MANIFEST).read_text())
    family_count = validate(packet, manifest, keys, prior)
    # Refuse a changed digest and a malformed record, even if its filename is right.
    try:
        validate(packet.replace('"level":42', '"level":41', 1), manifest, keys, prior)
    except AssertionError:
        pass
    else:
        raise AssertionError("corrupt changed packet was accepted")
    try:
        validate(packet[:-2], manifest, keys, prior)
    except (AssertionError, json.JSONDecodeError):
        pass
    else:
        raise AssertionError("truncated packet was accepted")
    saved = builder.PINS[builder.RESERVATION]
    builder.PINS[builder.RESERVATION] = "0" * 64
    try:
        builder.load()
    except ValueError as error:
        assert "INPUT_DRIFT" in str(error)
    else:
        raise AssertionError("changed input pin was accepted")
    finally:
        builder.PINS[builder.RESERVATION] = saved
    print(json.dumps({"status": "PASS", "exact_keys": len(keys), "families": family_count,
                      "corruption_refusals": 3}, sort_keys=True))


if __name__ == "__main__":
    main()
