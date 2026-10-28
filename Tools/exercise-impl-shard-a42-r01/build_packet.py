#!/usr/bin/env python3
"""Produce the bounded Level 42 private exercise contracts from pinned source evidence."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESERVATION = Path("Prompts/manager-resume-r01/mass-implementation-shards-r01/shard-a42-reservation.json")
PRIOR = Path("Build/fullscope-private-a-r01/level042-r06/packet.jsonl")
OUTPUT = Path("Build/exercise-impl-shard-a42-r01/level042-contracts.jsonl")
MANIFEST = Path("Build/exercise-impl-shard-a42-r01/packet-manifest.json")
PINS = {
    RESERVATION: "1c60e6f3361846f0cc60f30458a490fdc91852ecb1d8c8a82f5ef294f70b46c7",
    PRIOR: "9d7cb83eebbfb2b0ad0ca9a2d71e54d809f894bacf4350cf3e9c44990e07c973",
    Path("Results/level-oracle/exercise-completeness-r01/reviewed-handoff-r01/wbs-annex-candidate.jsonl"): "dc285a946a929ba08a7e0e1075d56f9c2eb53ce2dfa9c70ea67d34270d2bda6c",
    Path("Planning/Fathom-Exercise-WBS-Annex-v1.json"): "a76f5ca0b6bae1bf793cd9867b67f27dfa35e95f8a0596bc0eb1fe756ea67ce1",
    Path("Build/fullscope-private-a-r01/semantic-overlay-index-r13/effective-range-index.jsonl"): "6786cbcbf1982207ad0d0a815ff96b44426c88c442548f1a8d0a8661bb255945",
    Path("Notes/music/guitar project/TXT version/Scale_Exercises_Section_V_Level_42_A_Minor_Pentatonic_Horizontal_Movement_and_Articulation_Fixed_Key_A.txt"): "4d658466a731cf3de48c02cd8694651a3294d27af588a344926aa85e2d64f65b",
    Path("Notes/music/guitar project/PDF version/Scale_Exercises_Section_V_Level_42_A_Minor_Pentatonic_Horizontal_Movement_and_Articulation_Fixed_Key_A.pdf"): "fed7a629ecf0c0ff4e7015187ce858a21d333409aedc37bde7b6561b05b5c61d",
}


def digest(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def load():
    for path, expected in PINS.items():
        actual = digest(path)
        if actual != expected:
            raise ValueError(f"INPUT_DRIFT {path}: {actual} != {expected}")
    reservation = json.loads((ROOT / RESERVATION).read_text())
    keys = reservation["keys"]
    assert len(keys) == len(set(keys)) == 78
    assert hashlib.sha256(("\n".join(sorted(keys)) + "\n").encode()).hexdigest() == reservation["key_set_sha256"]
    prior = {r["package_key"]: r for r in map(json.loads, (ROOT / PRIOR).read_text().splitlines())}
    assert set(keys) <= set(prior)
    return keys, prior


def contact(c):
    # Preserve physical fret and sounding pitch separately: a bend target is not
    # another fretted finger contact, and an expressive shade has no fixed MIDI.
    wanted = ("ordinal", "string_label", "string_low_to_high", "fret", "physical_fret",
              "finger", "finger_authority", "midi", "note_spelling", "degree",
              "attack", "pick_attack", "technique_symbols", "printed_fret_role",
              "sounding_pitch_constraint", "vibrato_constraint", "source_line")
    return {k: c[k] for k in wanted if k in c}


def rest_contract(impl):
    c = impl["circuit_contract"]
    return {
        "position": "between consecutive phrases P1 through P5",
        "passes": [{"pass": i, "duration": p["value"], "unit": p["unit"]}
                   for i, p in enumerate(c["successive_rest_passes"], 1)],
        "bar_to_beat_ratio": None,
        "clock_status": "source_relative_only",
    }


def build_one(row, all_rows):
    key = row["package_key"]
    impl = row["implementation"]
    family = key.split("-module-")[1][0].upper()
    contacts = [contact(c) for c in impl["ordered_contacts"]]
    source_refs = [{"path": r["path"], "sha256": r["sha256"], "locator": r["locator"]}
                   for r in row["source_refs"]]
    result = {
        "schema_version": "fathom-private-exercise-contract.a42.1",
        "package_key": key,
        "source_identity": row["source_identity"],
        "level": 42,
        "family": family,
        "source_refs": source_refs,
        "printed_label": row["source_payload"]["printed_label"],
        "source_lines": row["source_payload"]["exact_unit_lines"],
        "ordered_contacts": contacts,
        "actual_pick_attacks": sum(bool(c.get("pick_attack")) for c in contacts),
        "attack_variants": impl.get("variants", []),
        "source_order_rule": impl.get("ordering_basis"),
        "technique": impl.get("technique_contract", impl.get("route_contract")),
        "counted_events": impl.get("source_counted_events"),
        "count_contract": impl.get("count_contract"),
        "phrase_groups": impl.get("phrase_groups"),
        "timing_authority": {
            "absolute_onsets": None,
            "absolute_durations": None,
            "bpm": None,
            "relative_rule": None,
            "source_unit": None,
            "acoustic_gate": impl.get("source_gate_rule"),
            "numeric_projection": None,
        },
        "rest_contract": None,
        "unresolved_fields": [],
        "source_conflicts": [],
        "realization_status": "source_ordered_manual_or_parameterized",
        "native_valid": False,
        "integrated": False,
        "accepted": False,
        "credit_or_mastery_authorized": False,
    }
    t = result["timing_authority"]
    if family == "B":
        # The printed 16 attacks are the counted module; the upper-endpoint
        # route is a separate required practice pass derived in prior work.
        upper = impl["route_contract"]["subsequent_upper_endpoint_pass"]
        result["realizations"] = [
            {"name": "printed_lower_endpoint", "contacts": contacts, "counted_in_written_module": True},
            {"name": "upper_endpoint_mirror", "contacts": [contact(c) for c in upper["ordered_contacts"]],
             "counted_in_written_module": False, "authority_line": upper["authority_line"],
             "derivation": upper["derivation"], "finger_choice_unselected": True},
        ]
        result["count_scope"] = "16 printed tones and attacks; upper mirror is instructed continuation outside the stated 96-tone written module count"
        t["relative_rule"] = "four picked contacts per destination cell in printed order; no slide or shift sound"
        t["source_unit"] = "ordered picked contacts; no fixed subdivision"
    elif family == "C":
        t["relative_rule"] = "six sounded tones, four picked attacks; each slide arrival is an unpicked counted subdivision tone"
        t["source_unit"] = "ordered subdivision arrival, no numeric fraction"
    elif family == "D":
        t["relative_rule"] = "twelve two-tone pairs: picked tone then unpicked partner on the subdivision"
        t["source_unit"] = "pair subdivision, no numeric fraction"
    elif family == "E":
        t["relative_rule"] = "five sounded tones from one pick: hammer, outward slide, return slide, pull; arrivals unpicked"
        t["source_unit"] = "ordered technique arrivals, no numeric fraction"
    elif family == "F":
        t["relative_rule"] = "four actual attacks; bend arrival and release are unpicked; hold bent target before release"
        t["source_unit"] = "ordered bend and release events, no numeric fraction"
        result["unresolved_fields"].append({"field": "expressive_pitch_curve", "reason": "No printed trajectory or dwell duration; blue shade is bounded below C# rather than assigned a fixed pitch."})
    elif family == "H" and contacts:
        t["relative_rule"] = "four actual attacks; unpicked hammer, pull, slide, bend arrival, release and vibrato events retain printed order"
        t["source_unit"] = "ordered counted sounding events, no numeric fraction"
        result["unresolved_fields"].append({"field": "expressive_pitch_curve", "reason": "Continuous bend, slide and vibrato curves and dwell times are not printed."})
    elif family == "H":
        # The earlier private record contained only phrase references and no
        # playable circuit sequence. Compose exact source-counted phrase events
        # for every rest pass, preserving phrase identities and attack counts.
        c = impl["circuit_contract"]
        phrases = []
        for phrase_key in c["ordered_package_keys"]:
            phrase = all_rows[phrase_key]
            pi = phrase["implementation"]
            phrases.append({"package_key": phrase_key,
                            "counted_events": pi["source_counted_events"],
                            "ordered_contacts": [contact(x) for x in pi["ordered_contacts"]],
                            "pick_attacks": sum(bool(x.get("pick_attack")) for x in pi["ordered_contacts"])})
        assert sum(len(p["counted_events"]) for p in phrases) == 43
        assert sum(p["pick_attacks"] for p in phrases) == 20
        result["linked_phrases"] = phrases
        result["rest_contract"] = rest_contract(impl)
        result["count_scope"] = "43 counted tones and 20 picked attacks per P1–P5 circuit pass; four rest variants are practice repetitions"
        t["relative_rule"] = "P1–P5 in order with four successive between-phrase rest passes: one source bar, two source beats, one source beat, no extra pause"
        t["source_unit"] = "source bar or beat rest only; phrase clocks unspecified"
        result["unresolved_fields"].append({"field": "bar_to_beat_ratio_and_phrase_clock", "reason": "Source supplies relative rests but no meter, bar-to-beat ratio, cadence onset grid or phrase durations."})
        result["unresolved_fields"].append({"field": "expressive_pitch_curve", "reason": "Referenced cadence bends, slides and vibrato remain performer parameterized."})
    if family != "H" or contacts:
        result["unresolved_fields"].insert(0, {"field": "numeric_onsets_durations_and_gate", "reason": "Printed order and relative technique timing are available; a complete numeric clock, BPM and acoustic note-off gate are not."})
    # Preserve source-specific uncertainty without conflating it with a conflict.
    for prior_issue in row.get("unresolved_reasons", []):
        field = prior_issue["field"]
        if field not in {x["field"] for x in result["unresolved_fields"]}:
            result["unresolved_fields"].append({"field": field, "reason": prior_issue["reason"]})
    return result


def main():
    keys, prior = load()
    rows = [build_one(prior[key], prior) for key in keys]
    assert len(rows) == len({r["package_key"] for r in rows}) == 78
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    body = "".join(json.dumps(r, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n" for r in rows)
    (ROOT / OUTPUT).write_text(body)
    manifest = {"schema_version": "fathom-private-exercise-shard-manifest.a42.1",
                "reservation": str(RESERVATION), "reservation_sha256": PINS[RESERVATION],
                "key_set_sha256": hashlib.sha256(("\n".join(sorted(keys)) + "\n").encode()).hexdigest(),
                "key_count": len(rows), "packet": str(OUTPUT), "packet_sha256": digest(OUTPUT),
                "source_txt_sha256": list(PINS.values())[-2], "source_pdf_sha256": list(PINS.values())[-1],
                "prior_packet": str(PRIOR), "prior_packet_sha256": PINS[PRIOR],
                "native_valid": 0, "integrated": 0, "accepted": 0}
    (ROOT / MANIFEST).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"keys": len(rows), "packet_sha256": manifest["packet_sha256"]}))


if __name__ == "__main__":
    main()
