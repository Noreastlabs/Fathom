#!/usr/bin/env python3
"""Finite identity, source, order, contact, and no-credit checks for C81."""
import hashlib
import json
import sys
import copy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "Tools/exercise-impl-shard-c81-r01"))
from build_contracts import line_range, sha, grip  # noqa: E402

RES = ROOT / "Prompts/manager-resume-r01/mass-implementation-shards-r02/shard-c81-reservation.json"
PACKET = ROOT / "Build/exercise-impl-shard-c81-r01/implementation-contracts.jsonl"
TXT = ROOT / "Notes/music/guitar project/TXT version/Guitar_Exercises_Section_XI_Level_81_Moving_Inner_Voices_Pedal_Tones_Walking_Bass_Passing_Diminished_and_Drop_2_Drop_3_Voicings.txt"
PDF = ROOT / "Notes/music/guitar project/PDF version/Guitar_Exercises_Section_XI_Level_81_Moving_Inner_Voices_Pedal_Tones_Walking_Bass_Passing_Diminished_and_Drop_2_Drop_3_Voicings.pdf"

def validate(rows, keys, lines):
    if len(rows)!=63 or [r["package_key"] for r in rows]!=keys or len({r["package_key"] for r in rows})!=63:
        raise ValueError("exact identity/order failure")
    for r in rows:
        k=r["package_key"]
        if r["source_identity"]!=k.split("/",1)[1] or r["level"]!=81:
            raise ValueError("foreign identity")
        if r["schema_version"]!="fathom-private-exercise-contract.c81.1":
            raise ValueError("schema failure")
        if r["canonical_ids_allocated"] or r["playback_admitted"] or r["automatic_score"] or r["learner_credit"]:
            raise ValueError("false credit/admission")
        if r["timing_authority"] not in {"unavailable","relative_quarter_notes_inner_voice","relative_one_or_half_beat_connector",
            "relative_beats_1_to_4_for_separation_drill","relative_beats_1_and_3_for_inner_guides",
            "bar_relative; guide_tones_beats_1_and_3","bar_relative","relative_one_beat_connector","relative_beat_1_destination"}:
            raise ValueError("invalid timing authority")
        refs=r["source_refs"]
        if refs[0]["sha256"]!=sha(PDF) or refs[1]["sha256"]!=sha(TXT):
            raise ValueError("source identity drift")
        if refs[1]["line_numbers"]!=line_range(k):
            raise ValueError("TXT locator mismatch")
        if refs[1]["line_text_sha256"]!=[hashlib.sha256(lines[n-1].encode()).hexdigest() for n in line_range(k)]:
            raise ValueError("TXT line corruption")
        data=r["source_contract"]
        if r["contract_kind"]=="voicing_contact":
            positions=data["frets_string_6_to_1"]
            if len(positions)!=6 or len([x for x in positions if x is not None])!=4:
                raise ValueError("four contact violation")
            if len(data["sounding_pitch_classes_low_to_high"])!=4:
                raise ValueError("pitch order loss")
        if r["contract_kind"]=="three_chord_contact_route":
            if len(data["contacts_by_role"])!=3 or [v["role"] for v in data["contacts_by_role"]]!=["source","passing_diminished","destination"]:
                raise ValueError("diminished contact order")
            if any(len(v["frets_string_6_to_1"])!=6 for v in data["contacts_by_role"]):
                raise ValueError("diminished grip length")
        if r["contract_kind"]=="eight_bar_arrangement":
            if [b["bar"] for b in data["bars"]]!=list(range(1,9)):
                raise ValueError("bar order")
            if any(not b["melody_note_order"] for b in data["bars"]):
                raise ValueError("melody target loss")
        if r["contract_kind"]=="twenty_four_bar_capstone" and [b["bar"] for b in data["bars"]]!=list(range(1,25)):
            raise ValueError("capstone form loss")
        if r["contract_kind"]=="manual_mastery_gate":
            if data["pass_total_at_least"]!=14 or data["out_of"]!=16 or data["separate_days"]!=2:
                raise ValueError("mastery criteria corruption")

def expect_refuse(rows,keys,lines,kind,mutator):
    altered=copy.deepcopy(rows)
    mutator(altered)
    try: validate(altered,keys,lines)
    except ValueError: return
    raise AssertionError(f"failed to refuse {kind}")

def main():
    keys=json.loads(RES.read_text())["keys"]
    rows=[json.loads(x) for x in PACKET.read_text().splitlines()]
    lines=TXT.read_text().splitlines()
    validate(rows,keys,lines)
    expect_refuse(rows,keys,lines,"duplicate identity",lambda rr:rr.__setitem__(1,dict(rr[0])))
    expect_refuse(rows,keys,lines,"foreign identity",lambda rr:rr[0].__setitem__("source_identity","level999/foreign"))
    expect_refuse(rows,keys,lines,"source corruption",lambda rr:rr[0]["source_refs"][0].__setitem__("sha256","0"*64))
    expect_refuse(rows,keys,lines,"false learner credit",lambda rr:rr[0].__setitem__("learner_credit",True))
    expect_refuse(rows,keys,lines,"false playback admission",lambda rr:rr[0].__setitem__("playback_admitted",True))
    print("PASS exact 63 keys, source locators/hashes, structured contact and form order, and five finite refusals")

if __name__=="__main__": main()
