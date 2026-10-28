#!/usr/bin/env python3
"""Finite B52 contract validation and refusal probes."""
from __future__ import annotations

import copy
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KEYS = json.loads((ROOT / "Prompts/manager-resume-r01/mass-implementation-shards-r02/shard-b52-reservation.json").read_text())["keys"]
PACKETS = [ROOT / f"Build/exercise-impl-shard-b52-r01/contracts-batch-{i:02d}.jsonl" for i in (1, 2, 3)]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(rows: list[dict]) -> None:
    if [x.get("package_key") for x in rows] != KEYS or len({x.get("package_key") for x in rows}) != 84:
        raise ValueError("identity/order/uniqueness refusal")
    counts = Counter()
    for row in rows:
        if row.get("schema_version") != "fathom-private-l052-exercise-contract.1" or row.get("level") != 52:
            raise ValueError("schema/level refusal")
        if row.get("runtime_admitted") is not False or row.get("canonical_id") is not None or not row.get("status", "").startswith("private_source_backed_"):
            raise ValueError("admission/no-credit refusal")
        for medium in ("txt", "pdf"):
            source = row["source"][medium]
            path = ROOT / source["path"]
            if digest(path) != source["sha256"]:
                raise ValueError("source identity refusal")
        txt = row["source"]["txt"]
        if txt["line_start"] is not None:
            lines = (ROOT / txt["path"]).read_text().splitlines()
            if "\n".join(lines[txt["line_start"] - 1:txt["line_end"]]) != txt["excerpt"]:
                raise ValueError("TXT locator refusal")
        elif row["family"] != "voice_emphasis_test":
            raise ValueError("missing TXT locator refusal")
        if row["source"]["pdf"]["physical_page"] not in range(1, 21):
            raise ValueError("PDF page refusal")
        timing = row["timing"]
        if timing["fixed_bpm"] is not None or timing["onsets_q"] is not None or timing["durations_q"] is not None:
            raise ValueError("fabricated timing refusal")
        for i, event in enumerate(row["events"], 1):
            if event["order"] != i or event["onset_q"] is not None or event["duration_q"] is not None:
                raise ValueError("event order/timing refusal")
            if event["kind"] == "pressure_release_mute" and event["sounded_members"]:
                raise ValueError("mute sounding refusal")
        counts[row["family"]] += 1
    if counts != Counter({"shape_workout": 42, "inversion_cycle": 14, "quality_switch": 21,
                          "pattern_cell": 5, "voice_emphasis_test": 2}):
        raise ValueError("family count refusal")
    f6 = next(x for x in rows if x.get("cell") == "F6")
    if Counter(e["kind"] for e in f6["events"]) != Counter({"blocked_triad": 4, "pressure_release_mute": 4}):
        raise ValueError("F6 release/refusal")
    for row in rows:
        if row["family"] == "voice_emphasis_test" and row["events"]:
            raise ValueError("fabricated test realization refusal")


def main() -> None:
    rows = [json.loads(line) for path in PACKETS for line in path.read_text().splitlines()]
    check(rows)
    probes = []
    def refuse(name, mutate):
        changed = copy.deepcopy(rows)
        mutate(changed)
        try:
            check(changed)
        except ValueError as e:
            probes.append({"probe": name, "result": "REFUSED", "reason": str(e)})
        else:
            raise AssertionError(f"negative accepted: {name}")
    refuse("duplicate_key", lambda x: x.__setitem__(1, copy.deepcopy(x[0])))
    refuse("wrong_source_hash", lambda x: x[0]["source"]["txt"].__setitem__("sha256", "0" * 64))
    refuse("fabricated_bpm", lambda x: x[0]["timing"].__setitem__("fixed_bpm", 120))
    refuse("fake_canonical_id", lambda x: x[0].__setitem__("canonical_id", "bad"))
    refuse("shifted_contact_order", lambda x: x[0]["events"][0].__setitem__("order", 2))
    refuse("sounding_mute", lambda x: next(v for v in x if v.get("cell") == "F6")["events"][1].__setitem__("sounded_members", [{"string": 3}]))
    report = {"result": "PASS", "exact_key_count": 84, "families": dict(Counter(x["family"] for x in rows)),
              "negative_refusals": probes, "packet_sha256": {str(p.relative_to(ROOT)): digest(p) for p in PACKETS}}
    out = ROOT / "Results/exercise-impl-shard-b52-r01/validation.json"
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"result": "PASS", "exact_keys": 84, "negative_refusals": len(probes)}))


if __name__ == "__main__":
    main()
