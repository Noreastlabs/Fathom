#!/usr/bin/env python3
"""Focused coverage, source-order, and refusal checks for the C79 private packet."""
import copy
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "Prompts/manager-resume-r01/mass-implementation-shards-r01/shard-c79-reservation.json"
PACKET = ROOT / "Build/exercise-impl-shard-c79-r01/source-contracts.jsonl"
REPORT = ROOT / "Results/exercise-impl-shard-c79-r01/validation.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(rows, keys):
    assert len(rows) == len(keys) == 109, "coverage count"
    assert [r["package_key"] for r in rows] == keys, "coverage order, omission, duplicate or foreign key"
    for r in rows:
        i = r["implementation"]
        assert r["schema_version"] == "fathom-level79-private-source-contract.1"
        assert r["source"]["pdf"]["sha256"] == "00a75f782c15ef8e8aaa8239b64f96cd272e90fca74ccc3ad09da362ad12aebb"
        assert r["source"]["txt"]["sha256"] == "56e42cd4324af9178b85d2525c38241e85b7c91c9cb75d9bfc7c7013664793fe"
        assert 3 <= r["source"]["pdf"]["physical_page"] <= 17
        assert len(r["source"]["pdf"]["original_page_extract_sha256"]) == 64
        assert r["source"]["txt"]["lines"]
        assert i["kind"] and i["prescription"] and i["learner_choice_parameters"]
        assert i["unresolved_fields"] and i["timing"]["authority"]
        assert i["timing"]["absolute"] is None and i["timing"]["fixed_bpm"] is None
        assert i["string_fret_finger"]["fret"] is None and i["string_fret_finger"]["finger"] is None
        assert i["automatic_score"] is False and i["credit_awarded"] is False and i["canonical_ids_allocated"] is False
        if i["kind"] == "dynamic_arc":
            assert len(i["prescription"]["bar_sections"]) == 8
            assert [s["Density"] for s in i["prescription"]["bar_sections"]] == [
                "1-2 contacts/bar", "4 contacts/bar", "4-6 contacts/bar", "6-8 contacts/bar", "2-4 contacts/bar", "4-7 contacts/bar", "6 contacts/bar", "4 -> 1"]
        if i["kind"] == "structural_target":
            assert len(i["note_or_contact_order"]) == 1
            assert i["note_or_contact_order"][0] == i["prescription"]["target"]
        if i["kind"] == "two_voice_harmonic_chain":
            assert len(i["note_or_contact_order"]) == 3
        if i["kind"] == "motif_first_onset_displacement":
            assert len(i["note_or_contact_order"]) == 8
            assert i["timing"]["authority"] == "relative_first_onset_only"
        if i["kind"] == "four_bar_role_circuit":
            assert len(i["prescription"]["bar_map"]) == 4
        if i["kind"] == "section_harmony_study":
            m = i["prescription"]["bar_map"]
            assert len(m) in (4, 8, 12)
            assert [x["bar"] for x in m] == list(range(m[0]["bar"], m[0]["bar"] + len(m)))
    by_key = {r["package_key"]: r for r in rows}
    intro = next(r for k, r in by_key.items() if "/modulea/p004-card01/" in k)
    assert any(x["kind"] == "rest" for x in intro["implementation"]["pause_hold_rest"])
    bridge = next(r for k, r in by_key.items() if "/moduleg/p015-card02/" in k)
    assert bridge["implementation"]["prescription"]["printed_voice_lines"] == [["C", "C", "B", "F#"], ["E", "F#", "F#", "C"]]
    memory = next(r for k, r in by_key.items() if "/modulef/p013-t1-r13/" in k)
    assert memory["implementation"]["prescription"]["next_action"] == "enter at next structural bar"
    assert "prior_packet_repair" in memory["source"]


def rejected(rows, keys, edit):
    bad = copy.deepcopy(rows)
    edit(bad)
    try:
        validate(bad, keys)
    except (AssertionError, KeyError, TypeError):
        return True
    return False


def main():
    keys = json.loads(MANIFEST.read_text())["keys"]
    rows = [json.loads(s) for s in PACKET.read_text().splitlines()]
    validate(rows, keys)
    tests = {
        "duplicate_key": rejected(rows, keys, lambda r: r.__setitem__(1, copy.deepcopy(r[0]))),
        "missing_key": rejected(rows, keys, lambda r: r.pop()),
        "source_hash_drift": rejected(rows, keys, lambda r: r[0]["source"]["pdf"].__setitem__("sha256", "0" * 64)),
        "fabricated_credit": rejected(rows, keys, lambda r: r[0]["implementation"].__setitem__("credit_awarded", True)),
        "lost_note_order": rejected(rows, keys, lambda r: next(x for x in r if x["implementation"]["kind"] == "motif_first_onset_displacement")["implementation"]["note_or_contact_order"].pop()),
        "corrupt_prior_memory_row": rejected(rows, keys, lambda r: next(x for x in r if "/modulef/p013-t1-r13/" in x["package_key"])["implementation"]["prescription"].__setitem__("next_action", "pair is successful if listener")),
    }
    assert all(tests.values()), tests
    result = {"status": "PASS", "contracts": len(rows), "kind_counts": dict(Counter(r["implementation"]["kind"] for r in rows)),
              "packet_sha256": sha(PACKET), "refusal_checks": tests}
    REPORT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
