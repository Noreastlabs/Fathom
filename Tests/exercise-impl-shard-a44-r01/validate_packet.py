#!/usr/bin/env python3
"""Finite source, identity, and no-credit guard for the A44 private packet."""

import copy
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "Tools/exercise-impl-shard-a44-r01"))
from build_contracts import PINS, INDEX  # noqa: E402


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify(records, keys):
    if [r.get("package_key") for r in records] != keys or len(set(keys)) != 46:
        raise ValueError("identity/order refusal")
    prior_index = {x["package_key"]: x for x in map(json.loads, INDEX.read_text().splitlines()) if x["package_key"] in keys}
    for r in records:
        if r.get("schema_version") != "fathom-private-exercise-contract-a44.1":
            raise ValueError("schema refusal")
        identity = prior_index[r["package_key"]]
        if r["level"] != 44 or r["source_identity"] != identity["source_identity"] or r["prior_record"]["record_canonical_sha256"] != identity["record_canonical_sha256"]:
            raise ValueError("source identity refusal")
        if any(r["status"].get(k) for k in ("native_valid", "integrated", "accepted", "mastery_credit")):
            raise ValueError("unsupported credit refusal")
        if r["timing_authority"]["fixed_bpm"] is not None or r["timing_authority"]["ascii_spacing_is_duration"]:
            raise ValueError("invented timing refusal")
        if not r["unresolved_fields"] or not r["printed_contacts_in_order"]:
            raise ValueError("incomplete contract refusal")
        ords = [c["ordinal"] for c in r["printed_contacts_in_order"]]
        if ords != list(range(1, len(ords)+1)):
            raise ValueError("contact order refusal")
        for ref in r["source_refs"]:
            path = ROOT / ref["path"]
            if sha(path.read_bytes()) != ref["sha256"] or PINS[ref["path"]] != ref["sha256"]:
                raise ValueError("source hash refusal")
        txt = (ROOT / r["source_refs"][0]["path"]).read_text().splitlines()
        loc = r["source_refs"][0]["locator"]
        for c in r["printed_contacts_in_order"]:
            line = c["source_line"]
            if line is None or not loc["line_start"] <= line <= loc["line_end"] or str(c["fret"]) not in txt[line-1]:
                raise ValueError("source contact refusal")
            if c["physical_fret"] is not None and c["physical_fret"] != c["fret"]:
                if c["fret_role"] != "sounding_equivalent_target" or c["pick_attack"]:
                    raise ValueError("bend physical/sounding refusal")
        module = r["source_module"]
        pc = r["performer_contract"]
        if module == "D":
            if len(r["printed_contacts_in_order"]) != 8 or len(pc["relative_rhythm_realizations"]) != 3:
                raise ValueError("rhythm family refusal")
            if pc["syncopated_sixteenth_silent_slots_zero_based"] != [0, 2, 5, 7, 8, 10, 13, 15]:
                raise ValueError("rest refusal")
        if module == "E" and pc["phrase_contract"]["initial_silence_source_beats"] != [1, 1]:
            raise ValueError("PDF one-beat silence refusal")
        if module == "J" and len(pc["all_required_combinations"]) != 16:
            raise ValueError("16-choice refusal")


def main():
    reservation = json.loads((ROOT / "Prompts/manager-resume-r01/mass-implementation-shards-r02/shard-a44-reservation.json").read_text())
    manifest = json.loads((ROOT / "Results/exercise-impl-shard-a44-r01/manifest.json").read_text())
    records = []
    for batch in manifest["batches"]:
        data = (ROOT / batch["path"]).read_bytes()
        if sha(data) != batch["sha256"]:
            raise ValueError("packet batch hash refusal")
        records.extend(map(json.loads, data.splitlines()))
    verify(records, reservation["keys"])
    # Mutation checks are in memory; no new files or false acceptance are created.
    mutations = []
    for name, mutate in [
        ("identity", lambda a: a[0].update(package_key="wrong")),
        ("source_hash", lambda a: a[0]["source_refs"][0].update(sha256="0"*64)),
        ("contact", lambda a: a[0]["printed_contacts_in_order"][0].update(fret=99)),
        ("credit", lambda a: a[0]["status"].update(accepted=True)),
        ("timing", lambda a: a[0]["timing_authority"].update(fixed_bpm=120)),
    ]:
        changed = copy.deepcopy(records)
        mutate(changed)
        try:
            verify(changed, reservation["keys"])
        except ValueError:
            mutations.append({"case": name, "refused": True})
        else:
            raise AssertionError(f"mutation not refused: {name}")
    result = {"schema_version": "fathom-private-a44-validation.1", "records": 46,
              "key_order_exact": True, "source_identity_and_locators": True,
              "finite_refusals": mutations, "source_backed_contracts": 46,
              "remaining_keys": 0}
    output = ROOT / "Results/exercise-impl-shard-a44-r01/validation.json"
    output.write_text(json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
