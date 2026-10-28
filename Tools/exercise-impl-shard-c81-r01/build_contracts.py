#!/usr/bin/env python3
"""Build the exact Level 81 private implementation lease from pinned sources."""
from __future__ import annotations

import hashlib
import json
import re
import resource
from datetime import datetime, timezone
from pathlib import Path

import pdfplumber

ROOT = Path(__file__).resolve().parents[2]
RESERVATION = ROOT / "Prompts/manager-resume-r01/mass-implementation-shards-r02/shard-c81-reservation.json"
PRIOR = ROOT / "Build/fullscope-private-c-r01/level081-r06/implementation-packet.jsonl"
OUT = ROOT / "Build/exercise-impl-shard-c81-r01"
RESULT = ROOT / "Results/exercise-impl-shard-c81-r01"
TXT = ROOT / "Notes/music/guitar project/TXT version/Guitar_Exercises_Section_XI_Level_81_Moving_Inner_Voices_Pedal_Tones_Walking_Bass_Passing_Diminished_and_Drop_2_Drop_3_Voicings.txt"
PDF = ROOT / "Notes/music/guitar project/PDF version/Guitar_Exercises_Section_XI_Level_81_Moving_Inner_Voices_Pedal_Tones_Walking_Bass_Passing_Diminished_and_Drop_2_Drop_3_Voicings.pdf"
PINS = {
    RESERVATION: "0b7ef2dd90a5628e043fb82a1584881a9cce36255269d4e227b2599cb34646a5",
    PRIOR: "8335f248700694d791057e1d93d68d8ad5ea7405972f4d327211c7c79ded06d3",
    TXT: "62178bd2edae899efc36cc5bff76c589660b66a45d99476e4efc73a66a29b9b6",
    PDF: "025e2c01ee637555544a64adf0b7a196b8bc1ca04f08bb61dd4cf7c6d479686d",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def memory_gib() -> float | None:
    # macOS vm_stat pages are 16 KiB on this host. The compressor occupancy is
    # counted with active and wired, as required by the lane guard.
    import subprocess
    p = subprocess.run(["vm_stat"], capture_output=True, text=True, check=True)
    names = ("Pages active", "Pages wired down", "Pages occupied by compressor")
    counts = []
    for name in names:
        m = re.search(r"^" + re.escape(name) + r":\s*(\d+)", p.stdout, re.M)
        if not m:
            raise ValueError(f"missing vm_stat field {name}")
        counts.append(int(m.group(1)))
    return round(sum(counts) * 16384 / 2**30, 3)


def tokens(s: str) -> list[str]:
    return re.findall(r"[A-G](?:#|b)?", s)


def grip(s: str) -> list[int | None]:
    xs = s.split()
    if len(xs) != 6 or any(not re.fullmatch(r"x|\d+", x) for x in xs):
        raise ValueError(f"bad source grip: {s!r}")
    return [None if x == "x" else int(x) for x in xs]


def grip_text(xs: list[int | None]) -> str:
    return " ".join("x" if x is None else str(x) for x in xs)


def line_range(k: str) -> list[int]:
    part = k.split("/level081/")[1]
    group = part.split("/")[0]
    starts = {"modulea": 30, "moduleb": 38, "modulec": 46, "moduled": 56, "modulee": 66,
              "modulef": 76, "moduleg": 84}
    if group in starts:
        if group in ("moduled", "modulee", "modulef"):
            n = int(re.search(r"-r(\d+)", part).group(1))
            return [starts[group] + n - 1 - (1 if n == 9 else 0)]
        card = int(re.search(r"card(\d+)", part).group(1))
        offset = (int(re.search(r"p(\d+)", part).group(1)) - {"modulea":3,"moduleb":5,"modulec":7,"moduleg":12}[group])
        return [starts[group] + (offset * {"modulea":3,"moduleb":3,"modulec":4,"moduleg":4}[group]) + card - 1]
    if group == "moduleh":
        p = int(re.search(r"p(\d+)", part).group(1))
        return list(range({14:94,15:99,16:104,17:109}[p], {14:99,15:104,16:109,17:114}[p]))
    if group == "modulei":
        return list(range(115, 140))
    if group == "modulej":
        if "masterygate" in part:
            return [151, 152]
        n = int(re.search(r"supplement(\d+)", part).group(1))
        return [141 + n]
    if group == "workbookfoundations":
        return [10,11,12,13,14]
    raise ValueError(k)


def build_content(k: str, lines: list[str], old: dict) -> tuple[str, dict, list[str], list[str], str]:
    part = k.split("/level081/")[1]
    group = part.split("/")[0]
    loc = line_range(k)
    s = lines[loc[0]-1]
    choices: list[str] = []
    missing = ["fixed_bpm", "absolute_onset_seconds", "attack_curve", "performer_fingering", "mastery_observation", "rights_clearance"]
    timing = "unavailable"
    if group == "modulea":
        x = [y.strip() for y in s.split(";")]
        chord, seq = x[0].split(": line ")
        data = {"harmony_route": [y.strip() for y in chord.split("->")],
                "inner_voice_order": tokens(seq), "printed_degrees": x[1].replace("degrees ", "").split("-"),
                "bass_route": tokens(x[2]), "source_instruction": x[3:] if len(x)>3 else [],
                "voice_roles": {"moving_inner": "printed four-note line", "bass": "printed outer anchor",
                                "melody": "E held" if "melody E stays fixed" in s else "performer-selected"},
                "pulse": "four quarter-note inner movements", "work_passes": ["sing inner line", "melody plus inner", "bass plus inner", "full texture", "remove inner voice and confirm harmony"]}
        timing = "relative_quarter_notes_inner_voice"
        choices += ["choose register and guitar route for each inner note", "choose any lower inner voice or top melody not fixed by source"]
        missing += ["inner_voice_octaves", "bass_change_onset", "full_voicing"]
        if "hold E or G" in s: choices.append("hold E or G as lower inner voice")
        return "ordered_voice_study", data, choices, missing, timing
    if group == "moduleb":
        title, tail = s.split(": harmony ")
        harmony, pedal_tail = tail.split("; pedal ")
        pedal, func = pedal_tail.split("; functions ")
        data = {"pedal_role": title.strip(), "harmony_order": [v.strip() for v in harmony.split("|")],
                "pedal_note_order": tokens(pedal), "printed_function": func,
                "pedal_action": "hold or re-articulate at the same dynamic while other voices establish harmony"}
        choices += ["hold or re-articulate pedal", "choose the unprinted other voices and voicings"]
        missing += ["harmony_duration", "pedal_attack_times", "other_voice_contacts", "pedal_octave"]
        return "pedal_voice_study", data, choices, missing, timing
    if group == "modulec":
        title, tail = s.split(": bass ")
        bass, harm = tail.split("; harmony ")
        data = {"route": title, "bass_note_order": tokens(bass), "harmony_instruction": harm,
                "harmony_route_where_explicit": [v.strip() for v in harm.split("->")] if "->" in harm else None,
                "work_passes": ["bass alone", "bass plus top melody", "guide tones on structural beats"],
                "destination_rule": "destination chord beat 1 must sound intentional and rhythmically secure"}
        choices += ["choose unprinted top melody and guide-tone contacts", "choose diatonic or chromatic approach where allowed"]
        missing += ["bass_note_octaves", "bass_note_onsets", "harmony_alignment_except_named_destination", "voicings"]
        return "ordered_walking_bass", data, choices, missing, timing
    if group == "moduled":
        parts = [v.strip() for v in s.split("|")]
        route = [v.strip() for v in parts[0].split("->")]
        positions = [grip(re.search(r"(?:x|\d+)(?:\s+(?:x|\d+)){5}", v).group()) for v in parts[1:4]]
        data = {"harmony_route": route, "contacts_by_role": [
            {"role": role, "chord": chord, "frets_string_6_to_1": pos}
            for role,chord,pos in zip(["source", "passing_diminished", "destination"], route, positions)],
            "top_line_idea": parts[4].replace("top idea ", "") if len(parts)>4 else None,
            "connector_function": "connect source to destination, not a new tonal center",
            "functional_test": ["play source and destination alone", "reinsert diminished as a one-beat or half-beat connector", "shorten or simplify if it sounds like a new tonic"]}
        choices += ["choose top-line alternative where slash appears", "choose one-beat or half-beat connector", "choose grip fingering"]
        missing += ["connector_absolute_onset", "finger_numbers"]
        timing = "relative_one_or_half_beat_connector"
        return "three_chord_contact_route", data, choices, missing, timing
    if group in ("modulee", "modulef"):
        pieces = [v.strip() for v in s.split("|")]
        chord, rest = pieces[0].split(": ")
        pos = grip(rest)
        pitch = pieces[1].split("-")
        degree = pieces[2].split("-") if len(pieces)>2 else None
        if group=="modulee" and chord=="Fmaj7":
            # The short TXT omits this degree column; PDF p10 prints it.
            degree = ["R","5","7","3"]
        data = {"voicing_family": "drop_2" if group=="modulee" else "spread_drop_3",
                "chord": chord, "frets_string_6_to_1": pos,
                "sounding_pitch_classes_low_to_high": pitch,
                "printed_voice_order": degree,
                "simultaneous_contacts": True}
        choices += ["choose left-hand fingering and attack"]
        missing += ["finger_numbers", "attack_time", "contact_duration"]
        if degree is None: missing.append("printed_degree_labels")
        if group=="modulee":
            data["cycle_drill"]=["blocked chord four times","low-to-high arpeggio","top-to-low arpeggio","melody-emphasis pass"]
            data["connection_route"]=["Cmaj7","Am7","Dm7","G7"]
            choices.append("connect using nearest available top note")
        else:
            data["bass_separation_drill"]=[{"beat":1,"role":"bass"},{"beat":2,"role":"upper three voices"},
                                           {"beat":3,"role":"bass"},{"beat":4,"role":"upper three voices"}]
            data["comfort_rule"]="if stretch destabilizes melody, intonation, or pulse, omit fifth or move upper structure nearer"
            timing="relative_beats_1_to_4_for_separation_drill"
            choices.append("compress to compact texture or change inversion for comfort")
        return "voicing_contact", data, choices, missing, timing
    if group == "moduleg":
        title, tail = s.split(": ",1)
        fields = [v.strip() for v in tail.split(";")]
        data = {"integration_pattern": title, "printed_voice_instructions": fields,
                "build_passes": ["outer voices", "add one inner voice", "full texture", "reduction test"],
                "reduction_trigger": "reduce immediately if more than one voice becomes rhythmically uncertain"}
        if title=="Pedal melody + walking bass":
            data["voice_routes"]={"melody":{"note":"G","hold":True},"bass":{"note_order":["C","B","A","G"]}}
            data["harmony_route"]=["Cmaj7","Cmaj7/B","Am7","G7"]
        elif title=="Pedal bass + moving top":
            data["voice_routes"]={"bass":{"note":"C","hold":True},"melody":{"note_order":["E","F","G","E"]}}
            data["harmony_route"]=["Cmaj7","Dm7/C","G7/C","Cmaj7"]
        elif title=="Walking bass + guide dyad":
            data["voice_routes"]={"bass":{"note_order":["D","E","F","F#","G"]},"guide_1":{"note_order":["C","B"]},"guide_2":{"note_order":["F","F"]}}
            data["harmony_route"]=["Dm7","G7"]
        elif title=="Passing diminished + melody":
            data["harmony_route"]=["Cmaj7","C#dim7","Dm7"]
            data["voice_routes"]={"melody":{"hold_note":"G","resolution_choices":["F","A"]}}
        elif title=="Spread voicing + bass fill":
            data["harmony_route"]=["Cmaj7","Am7"]
            data["voice_routes"]={"upper_three":{"hold":True},"bass":{"note_order":["C","B","A"]}}
        elif title=="Contrary outer voices":
            data["voice_routes"]={"bass":{"note_order":["C","D","E","F"]},"melody":{"note_order":["G","F","E","D"]},"inner_guides":{"roles":["third","seventh"],"beats":[1,3]}}
        elif title=="Reduction ladder":
            data["layer_order"]=["full voicing","drop inner","bass plus melody","melody only","restore voices in reverse order"]
        if "beats 1 and 3" in s: timing = "relative_beats_1_and_3_for_inner_guides"
        choices += ["choose unprinted inner pitches or voicing where needed", "choose guitar route and exact attack placement"]
        missing += ["all_unprinted_voice_contacts", "onsets_except_named_beats", "durations"]
        return "integration_voice_pattern", data, choices, missing, timing
    if group == "moduleh":
        block = [lines[i-1] for i in loc]
        name = block[0]
        chords = [v.strip() for row in block[1:3] for v in row.split("|") if v.strip()]
        melody = tokens(block[3].split(":",1)[1]) if "Melody:" in block[3] else tokens(block[4].split(":",1)[1])
        bass = tokens(block[4].split(":",1)[1]) if "Bass:" in block[4] else []
        if len(chords)!=8: raise ValueError((k,"chord count",chords))
        data = {"arrangement": name, "bars": [{"bar": i+1, "chord": chords[i],
                "melody_note_order": melody[2*i:2*i+2] if len(melody)==16 else melody[i:i+1],
                "bass_note": bass[i] if len(bass)==8 else None} for i in range(8)],
                "rehearsal_passes": ["melody only", "bass only", "melody plus bass", "guide tones on beats 1 and 3", "full arrangement with selected drop-2 or spread voicings"],
                "reduction_test": "remove all inner voices; form must remain recognizable from bass and melody"}
        if "Texture:" in block[3]:
            data["texture_instruction"]=block[3].split(":",1)[1].strip()
        timing = "bar_relative; guide_tones_beats_1_and_3"
        choices += ["select drop-2 or spread voicing by register", "choose inner voices and exact melody attacks within each bar"]
        missing += ["time_signature", "melody_within_bar_onsets", "exact_voicings", "bar_duration"]
        if len(bass)!=8: missing.append("bass_notes_in_arrangement_4")
        return "eight_bar_arrangement", data, choices, missing, timing
    if group == "modulei":
        bars=[]
        for n in range(116,140):
            m=re.fullmatch(r"Bar (\d+): ([^;]+); bass ([^;]+); melody ([^;]+); (.+)\.",lines[n-1])
            if not m: raise ValueError((n,lines[n-1]))
            bars.append({"bar":int(m[1]),"chord":m[2],"bass_note":m[3],"melody_note":m[4],"function":m[5]})
        data={"bars":bars,"passes":["bass plus melody", "add guide tones", "add passing diminished or walking bass where printed", "choose compact or spread voicing by register", "record one uninterrupted take"]}
        timing="bar_relative"
        choices += ["choose compact or spread voicings by register", "choose exact attacks and all unprinted inner voices"]
        missing += ["time_signature", "bar_duration", "within_bar_onsets", "exact_voicings"]
        return "twenty_four_bar_capstone",data,choices,missing,timing
    if group == "modulej":
        if "masterygate" in part:
            data={"score_dimensions":["melody clarity","bass timing","inner-voice accuracy","pedal-tone stability","diminished-chord function","voicing cleanliness","pulse / form","recovery"],
                  "score_range_each":[0,2],"pass_total_at_least":14,"out_of":16,"separate_days":2,
                  "required_nonzero":["melody clarity","bass timing","pulse / form","recovery"],
                  "practice_requirements":["sing moving inner voices independently","hold six pedal-tone studies without drift","perform eight walking-bass routes","use all eight diminished connectors functionally","play eight drop-2 voicings cleanly","play six spread voicings without strain","perform eight integration studies","complete four eight-bar arrangements","perform 24-bar capstone twice"],
                  "manual_report_fields":{"attempt_day":"calendar date supplied by performer","scores":"eight integer scores in printed dimension order, each 0..2","observer":"performer or separately named observer","evidence_note":"free text"},
                  "evidence_mode":"manual performer report; no automatic musical score or credit"}
            missing += ["observed_attempts", "verified_day_separation", "per_dimension_scores"]
            return "manual_mastery_gate",data,[],missing,timing
        title, action = s.split(": ",1)
        data={"recovery_trigger":title,"ordered_action":action.split("; "),
              "manual_report_fields":{"trigger_observed":"boolean self-report","action_attempted":"boolean self-report","evidence_note":"free text"},
              "evidence_mode":"manual performer report; no automatic completion or credit"}
        choices += ["perform and report recovery in context"]
        missing += ["observed_trigger", "observed_recovery", "performance_score"]
        if "one-beat" in s: timing="relative_one_beat_connector"
        if "beat 1" in s: timing="relative_beat_1_destination"
        return "manual_recovery_action",data,choices,missing,timing
    if group == "workbookfoundations":
        table=old["implementation"]["task"]["table_fields"][0]
        data={"voice_priority":["melody","bass","guide tones / pedals","extensions and optional color"],
              "voicing_examples":[{"type":r[0],"frets_string_6_to_1":grip(r[1]),"pitches_low_to_high":r[2].split("-"),"use":r[3]} for r in table["rows"]],
              "reduction_order":["full: melody + upper guide + lower guide + bass","melody + one guide + bass","melody + bass","melody only"],
              "restore_order":["bass","guide tone","optional color"]}
        choices += ["name four voices and choose grip"]
        missing += ["reference_example_attack_timing", "fingering"]
        return "reference_and_reduction_contract",data,choices,missing,timing
    raise ValueError(k)


def main() -> None:
    for p,h in PINS.items():
        if sha(p)!=h: raise SystemExit(f"pin drift: {p}")
    res=json.loads(RESERVATION.read_text())
    keys=res["keys"]
    assert len(keys)==63 and len(set(keys))==63
    assert hashlib.sha256(("\n".join(sorted(keys))+"\n").encode()).hexdigest()==res["key_set_sha256"]
    prior={x["package_key"]:x for x in map(json.loads,PRIOR.read_text().splitlines())}
    assert set(keys)<=set(prior)
    lines=TXT.read_text().splitlines()
    with pdfplumber.open(PDF) as pdf:
        assert len(pdf.pages)==20
        pdf_text={i+1:pdf.pages[i].extract_text() or "" for i in range(20)}
    OUT.mkdir(parents=True,exist_ok=True)
    RESULT.mkdir(parents=True,exist_ok=True)
    records=[]
    for key in keys:
        old=prior[key]
        pages=old["source_refs"][0]["locator"]["physical_pages"]
        for page in pages:
            assert "Guitar Exercises - Section XI, Level 81" in pdf_text[page]
        loc=line_range(key)
        kind,data,choices,missing,timing=build_content(key,lines,old)
        # The prior region itself is checked against the original page at its
        # printed label; the long prose extraction is deliberately not copied.
        label=old["source_payload"]["printed_label"]
        if label and label.lower() not in " ".join(pdf_text[p].lower() for p in pages):
            raise ValueError((key,"PDF label absent",label,pages))
        page_text="\n".join(pdf_text[p] for p in pages)
        if kind=="voicing_contact":
            needle=f'{data["chord"]} {grip_text(data["frets_string_6_to_1"])} {"-".join(data["sounding_pitch_classes_low_to_high"])}'
            if needle not in page_text: raise ValueError((key,"PDF voicing mismatch",needle))
        if kind=="three_chord_contact_route":
            needle=" -> ".join(data["harmony_route"])+" "+" ".join(grip_text(x["frets_string_6_to_1"]) for x in data["contacts_by_role"])
            if needle not in page_text: raise ValueError((key,"PDF contact route mismatch",needle))
        if kind=="twenty_four_bar_capstone":
            for bar in data["bars"]:
                needle=f'{bar["bar"]} {bar["chord"]} {bar["bass_note"]} {bar["melody_note"]} {bar["function"]}'
                if needle not in page_text: raise ValueError((key,"PDF capstone bar mismatch",needle))
        rec={"schema_version":"fathom-private-exercise-contract.c81.1", "package_key":key,
             "source_identity":old["source_identity"],"level":81,
             "source_refs":[{"path":str(PDF.relative_to(ROOT)),"sha256":PINS[PDF],
                 "physical_pages":pages,"page_text_sha256":[hashlib.sha256(pdf_text[p].encode()).hexdigest() for p in pages],
                 "within_page_label":label},
                 {"path":str(TXT.relative_to(ROOT)),"sha256":PINS[TXT],"line_numbers":loc,
                  "line_text_sha256":[hashlib.sha256(lines[n-1].encode()).hexdigest() for n in loc]}],
             "disposition":"SOURCE_BACKED_MANUAL_OR_CHOICE_IMPLEMENTATION",
             "contract_kind":kind,"source_contract":data,"timing_authority":timing,
             "performer_choices":choices,"unresolved_fields":sorted(set(missing)),
             "source_conflicts":[],"canonical_ids_allocated":False,"playback_admitted":False,
             "automatic_score":False,"learner_credit":False}
        if kind=="reference_and_reduction_contract":
            rec["source_boundary_note"]="PDF page 2 defines the reference; paired abbreviated TXT has no exact standalone reference boundary. TXT lines 10-14 only corroborate priority."
        records.append(rec)
    # Bounded immutable batches preserve the exact remaining-key census.
    checkpoints=[]
    for b in range(3):
        chunk=records[b*21:(b+1)*21]
        path=OUT/f"contracts-batch-{b+1:02d}.jsonl"
        path.write_text("".join(json.dumps(x,sort_keys=True,separators=(",",":"))+"\n" for x in chunk))
        remain=keys[(b+1)*21:]
        checkpoint={"batch":b+1,"attempted":(b+1)*21,"implemented":(b+1)*21,
                    "manual_or_choice":(b+1)*21,"unresolved_conflict_cases":0,
                    "remaining_keys":remain,"remaining_count":len(remain),"packet_path":str(path.relative_to(ROOT)),
                    "packet_sha256":sha(path),"memory_proxy_gib":memory_gib(),
                    "process_peak_rss_mib":round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/2**20,2),
                    "failure_trace":[]}
        if checkpoint["memory_proxy_gib"]>=13.0: raise SystemExit("memory guard reached after checkpoint")
        cp=RESULT/f"checkpoint-batch-{b+1:02d}.json"
        cp.write_text(json.dumps(checkpoint,indent=2)+"\n")
        checkpoints.append(checkpoint)
    packet=OUT/"implementation-contracts.jsonl"
    packet.write_text("".join(json.dumps(x,sort_keys=True,separators=(",",":"))+"\n" for x in records))
    summary={"schema_version":"fathom-private-c81-handoff.1","utc":datetime.now(timezone.utc).isoformat(),
             "lease":"shard-c81","reservation_sha256":PINS[RESERVATION],"key_set_sha256":res["key_set_sha256"],
             "attempted":63,"source_backed_implemented":63,"manual_or_choice":63,
             "unresolved_conflict_cases":0,"remaining_keys":[],"native_valid":0,"queue_selected":0,
             "installed_accepted":0,"whole_workbook_increment":0,"wbs_parent_increment":0,
             "packet_path":str(packet.relative_to(ROOT)),"packet_sha256":sha(packet),
             "batch_hashes":[c["packet_sha256"] for c in checkpoints],
             "one_case_admission_proposal":"exercise-completeness-r01/level081/modulee/p010-t1-r1/cmaj7, only after independent source review and P02 queue selection; printed four-contact drop-2 shape has no fixed attack/onset or fingering",
             "causal_limit":"The PDF and TXT prescribe note order, grips, harmonic roles and some relative beats/bars, but omit fixed BPM, many attacks, fingerings and a single full arrangement realization. Manual/choice contracts cannot claim playback validation or mastery."}
    (RESULT/"handoff.json").write_text(json.dumps(summary,indent=2)+"\n")
    print(json.dumps({"packet_sha256":sha(packet),"batches":summary["batch_hashes"],"memory_gib":[c["memory_proxy_gib"] for c in checkpoints]}))

if __name__=="__main__": main()
