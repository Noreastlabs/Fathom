#!/usr/bin/env python3
"""Normalize the exact leased Level 78 exercises into private source contracts."""
import hashlib
import json
import re
import resource
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESERVATION = ROOT / "Prompts/manager-resume-r01/mass-implementation-shards-r01/shard-c78-reservation.json"
PRIOR = ROOT / "Build/fullscope-private-c-r01/level078-r06/implementation-packet.jsonl"
OUT = ROOT / "Build/exercise-impl-shard-c78-r01/contracts.jsonl"
TXT = ROOT / "Notes/music/guitar project/TXT version/Guitar_Exercises_Section_X_Level_78_Ear_Led_Improvisation_Anticipatory_Guide_Tones_Motif_Prediction_and_Spontaneous_Role_Switching.txt"
PDF = ROOT / "Notes/music/guitar project/PDF version/Guitar_Exercises_Section_X_Level_78_Ear_Led_Improvisation_Anticipatory_Guide_Tones_Motif_Prediction_and_Spontaneous_Role_Switching.pdf"
EXPECTED = {
    TXT: "39fb82445b8d5f0d4e01f7108f360e7db0aaf45270145d4816213365d81a024e",
    PDF: "c7ecb9afda1dc902e38f1861a1d05422e4a48b8d5efcf2a9701f73684b922268",
    PRIOR: "4c7e25ebee48e6e319f62dbb30708d34631d234a85d233120d20dc5116552555",
}
TXT_LINES = TXT.read_text().splitlines()
LINE_RANGES = {"modulea": (21, 48), "moduleb": (50, 65), "modulec": (67, 93), "moduled": (95, 113),
               "modulee": (115, 129), "modulef": (131, 149), "moduleg": (151, 177), "moduleh": (179, 212)}
NOTE_RE = re.compile(r"^[A-G](?:#|b)?$")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def notes(text):
    values = [v.strip() for v in re.split(r"\s*(?:->|-)\s*", text)]
    if not values or not all(NOTE_RE.fullmatch(v) for v in values):
        raise ValueError(f"invalid printed note order: {text!r}")
    return values


def unavailable(*fields):
    return {f: "not printed; performer selection or later source authority required" for f in fields}


def slot(pitch, role, context=None, relative=None, source_field=None):
    return {"pitch_name": pitch, "role": role, "harmonic_context": context, "relative_position": relative,
            "source_field": source_field, "string": None, "fret": None, "finger": None,
            "octave": None, "onset_seconds": None, "duration_seconds": None,
            "performed_observation": False}


def parse(d):
    key = d["package_key"]
    mod = key.split("/")[2]
    page = d["source_refs"][0]["locator"]["physical_pages"][0]
    raw = d["source_payload"]["pdf_region_text"]
    lines = [s.strip() for s in raw.splitlines() if s.strip()]
    context = {"kind": "manual_source_task", "steps": [], "contacts": [], "alternatives": [],
               "timing": {"authority": "unavailable", "fixed_bpm": None, "absolute_onsets": None},
               "pause_hold_rest": [], "unresolved": unavailable("string", "fret", "finger", "octave", "fixed_bpm"),
               "source_conflicts": [], "source_extraction_limits": [], "source_order": "printed sequence only; not a measured performance"}
    steps, contacts, alternatives, timing, pauses, unresolved = (context[x] for x in
        ("steps", "contacts", "alternatives", "timing", "pause_hold_rest", "unresolved"))

    if mod == "modulea":
        rows = d["implementation"]["task"]["table_fields"][0]["rows"]
        for row in rows:
            bar, chord, degree, pitch, sing = row[:5]
            contacts.append(slot(pitch, "target", chord, {"bar": int(bar), "beat": 1 if page == 2 else None}, "Target pitch"))
            steps.append({"bar": int(bar), "chord": chord, "target_degree": degree,
                          "sing_preview": sing, "target_contact_index": len(contacts)-1,
                          "resolution_wording": row[5] if len(row) > 5 else None})
        timing.update(authority="relative", unit="bar/beat", count_in="bar 1 target sung on count-in beat 4")
        if page == 2:
            timing["first_pass_target"] = {"beat": 1, "duration_beats": 1}
            pauses.append({"pass": 1, "beats": [2, 3, 4], "meaning": "no further played notes; beat 4 sung preview"})
            alternatives.append({"pass": "later", "extra_notes_max": 2, "beat_4": "clear for sung preview"})
        else:
            pauses.append({"scope": "resolution words hold/settle/close", "duration": None})
            alternatives.append({"pass": 2, "preview": "silent singing; return to audible if accuracy drops"})
            unresolved["target_beat_and_duration"] = "minor matrix does not print a numeric target attack/duration"
        assert len(contacts) == 12

    elif mod == "moduleb":
        m = re.match(r"(.+?): (.+?)\nV1 (.+?) Sing -> play -> (?:combine|resolve)\nV2 (.+)", raw)
        if not m: raise ValueError(f"guide-tone parse {key}")
        key_name, chord_text, v1, v2 = m.groups()
        chords = [x.strip() for x in chord_text.split("->")]
        for voice, line in (("V1", v1), ("V2", v2)):
            ns = notes(line)
            if len(ns) != 3: raise ValueError(key)
            for j, n in enumerate(ns): contacts.append(slot(n, voice, chords[j], {"chord_order": j+1}, voice))
        steps.extend([{"action": "sing guide tone before chord change"}, {"action": "play printed voice order"}])
        alternatives.extend([{"pass": v} for v in (["V1", "V2", "dyad", "dyad with light root comp", "free phrase landing on sung guide tone"] if page == 4 else ["V1", "V2", "resolve into minor tonic"])])
        context["harmonic_route"] = {"key": key_name, "chords": chords, "parallel_voices": True}
        timing.update(authority="relative", unit="chord order", chord_changes="unquantified")
        unresolved.update(unavailable("chord_change_beat", "note_duration", "comp_voicing"))

    elif mod == "modulec":
        fields = d["implementation"]["task"]["table_fields"][0]
        vals = fields["values"]
        if page == 6:
            card, key_name, opening, answer, degree = vals
            for role, seq in (("heard_opening", opening), ("hidden_answer", answer)):
                for j, n in enumerate(notes(seq)):
                    contacts.append(slot(n, role, key_name, {"sequence": role, "ordinal": j+1}, role))
            steps.extend([{"action": "hear opening"}, {"action": "sing two continuation notes before answer reveal"},
                          {"action": "compare with source answer", "degree_answer": degree}])
            context["answer_visibility"] = "withhold printed answer until learner prediction"
            timing.update(authority="relative", unit="sequence order", beat_grid=None)
            unresolved.update(unavailable("phrase_rhythm", "answer_note_duration"))
        else:
            card, key_name, move, request, correct = vals
            contacts.append(slot(correct, "hidden_reference_answer", key_name, None, "Correct pitch"))
            steps.extend([{"action": "show key and function move", "key": key_name, "function_move": move,
                           "requested_target": request}, {"action": "sing requested chord tone"},
                          {"action": "play in two registers"}, {"action": "reveal chord name for verification"}])
            context["answer_visibility"] = "hide chord symbol and correct pitch until response"
            unresolved.update(unavailable("two_register_octaves", "chord_symbol_realization", "rhythm"))

    elif mod == "moduled":
        if page == 8:
            m = re.search(r"Q: ([A-G#b-]+) (.*?)\nA: ([A-G#b-]+)", raw)
            if not m: raise ValueError(f"motif parse {key}")
            q, rule, a = m.groups()
            for role, seq in (("question", q), ("reference_answer", a)):
                for j, n in enumerate(notes(seq)): contacts.append(slot(n, role, None, {"motif_position": j+1}, role))
            steps.extend([{"action": "sing reference answer"}, {"action": "play question and answer continuously"},
                          {"action": "invent later answer", "constraint": rule}])
            context["motif_rule"] = rule
            timing.update(authority="relative", unit="motif order", rhythm_relation="same as question only where printed")
            unresolved.update(unavailable("motif_rhythm", "new_answer_notes"))
        else:
            m = re.match(r"(.+?) -> (.+?) ([A-G#b-]+) ([A-G#b-]+) beat 1 = chord 3rd", lines[0])
            if not m: raise ValueError(f"chord motif parse {key}")
            c1, c2, q, a = m.groups()
            for role, chord, seq in (("question", c1, q), ("answer", c2, a)):
                for j, n in enumerate(notes(seq)): contacts.append(slot(n, role, chord, {"motif_position": j+1, "beat": 1 if j == 0 else None}, role))
            steps.extend([{"action": "play question under first chord"}, {"action": "answer under changed chord; first answer pitch is chord third"},
                          {"action": "third pass choose a different chord tone on beat 1; preserve question rhythm"}])
            timing.update(authority="relative", unit="beat plus ordered motif", first_contact_beat=1, other_beats=None)
            unresolved.update(unavailable("remaining_note_beats", "motif_rhythm", "third_pass_first_pitch"))

    elif mod == "modulee":
        if page == 10:
            chord_line = next(x for x in lines if " | " in x and x.count("|") >= 3)
            chords = [x.strip() for x in chord_line.split("|")]
            if len(chords) != 4: raise ValueError(key)
            lead_line = next(x for x in lines if x.startswith("Sing lead entry:"))
            m = re.match(r"Sing lead entry: ([A-G](?:#|b)?) \| (.+?) -> (.+)", lead_line)
            if not m: raise ValueError(key)
            target, comp_style, lead_style = m.groups()
            contacts.append(slot(target, "preheard_lead_entry", chords[2], {"sung_bar": 2, "sung_beat": 4, "played_bar": 3}, "Sing lead entry"))
            steps.extend([{"bars": [1,2], "role": "comp", "chords": chords[:2], "style": comp_style},
                          {"bar": 2, "beat": 4, "action": "sing lead target"},
                          {"bars": [3,4], "role": "lead", "chords": chords[2:], "style": lead_style}])
            timing.update(authority="relative", unit="bar/beat", lead_entry_preview={"bar": 2, "beat": 4})
            unresolved.update(unavailable("exact_comp_attacks", "lead_target_play_beat", "lead_phrase_notes"))
        else:
            heading = lines[0]
            chordline = lines[1].split(" Comp: ")[0]
            chords = chordline.split("-")
            comp = lines[1].split(" Comp: ")[1].split(" Lead: ")[0]
            lead = lines[1].split(" Lead: ")[1]
            steps.extend([{"role": "comp", "register_change": heading.split(" -> ")[0], "texture": comp},
                          {"role": "lead", "register_change": heading.split(" -> ")[1], "texture": lead}])
            context["harmonic_route"] = chords
            timing.update(authority="relative", unit="chord order", handoff_position="not quantified on this page")
            unresolved.update(unavailable("handoff_beat", "comp_voicing", "lead_melody"))

    elif mod == "modulef":
        if page == 12:
            m = re.match(r"(.+?) lead (?:ends on )?([A-G](?:#|b)?) -> comp (\S+) bar 4 (beat 3|& of 2) ([A-G](?:#|b)?) -> ([A-G](?:#|b)?)(?: / (.+))?", lines[0])
            if not m: raise ValueError(f"return parse {key}: {lines[0]}")
            key_name, lead_pitch, chord, subdivision, resolved_from, target, color = m.groups()
            if resolved_from != lead_pitch: raise ValueError(f"lead resolution mismatch {key}")
            contacts.extend([slot(lead_pitch,"last_lead_attack",key_name,{"bar":4,"subdivision":subdivision},"Last lead attack"),
                             slot(target,"resolution_target",chord,None,"Resolution")])
            steps.extend([{"action":"end lead", "bar":4,"subdivision":subdivision},
                          {"action":"re-form accompaniment voicing during remaining silence"},
                          {"action":"re-enter accompaniment without setup strum","chord":chord,"color":color}])
            pauses.append({"after":"last lead attack","meaning":"setup silence before comp re-entry","duration":None})
            timing.update(authority="relative",unit="bar/beat",last_lead_attack={"bar":4,"subdivision":subdivision})
            unresolved.update(unavailable("comp_reentry_beat", "comp_voicing", "resolution_duration"))
        else:
            cue = next((x for x in lines if x in {"Cue at beat 1","Cue at beat 3","Cue at beat 4","Visual nod","Drum fill","Held ensemble chord"}), None)
            if not cue: raise ValueError(key)
            action = next(x for x in lines if x != cue and not x.startswith("Practice with partner") and not x.isupper())
            steps.extend([{"cue":cue,"response":action},{"action":"practice with partner calling cues randomly"}])
            if cue in {"Held ensemble chord","Cue at beat 4"}: pauses.append({"cue":cue,"condition":action,"duration":None})
            timing.update(authority="relative" if "beat" in cue else "unavailable", cue=cue,
                          cue_beat=int(cue[-1]) if re.fullmatch(r"Cue at beat [1-4]",cue) else None)
            unresolved.update(unavailable("cue_wall_time", "partner_signal_time", "exact_followup_notes"))

    elif mod == "moduleg":
        if page == 14:
            fields = d["implementation"]["task"]["table_fields"][0]["values"]
            progression, ra, da, rb, db = fields
            chords = progression.split("-")
            steps.extend([{"pass":1,"role":ra,"density":da,"chords":chords},
                          {"pass":2,"role":rb,"density":db,"chords":chords},
                          {"pass":3,"switch_after_bars":2,"preserve":"harmonic targets and bar count"}])
            if "rest" in da or "rest" in db: pauses.append({"instruction":"target plus rest","rest_duration":None})
            timing.update(authority="relative",unit="bar",role_switch_after_bars=2)
            unresolved.update(unavailable("specific_target_notes", "attack_subdivisions", "voicings"))
        else:
            cmd = lines[0].split(". ",1)[1]
            m = re.match(r"(?:Comp|Lead over) (\S+) -> (?:lead on (\S+)|comp (\S+))",cmd)
            if m:
                from_chord, target, to_chord = m.groups()
                if target: contacts.append(slot(target,"new_role_lead_target",from_chord,{"next_bar":True},"command"))
                steps.append({"command":cmd,"from_chord":from_chord,"target_pitch":target,"to_comp_chord":to_chord})
            else: steps.append({"command":cmd,"new_role_target":"performer selected within current harmony"})
            steps.extend([{"action":"partner reads command during current bar"},
                          {"action":"sing new-role target on final beat"},
                          {"action":"switch at next barline without count restart"}])
            timing.update(authority="relative",unit="bar/beat",sung_preview="current bar final beat",role_switch="next barline")
            if "extra bar" in cmd: pauses.append({"instruction":"preserve current role through inserted bar","bar_count":1})
            unresolved.update(unavailable("new_role_target_pitch_if_unprinted", "role_realization_notes", "voicing"))

    elif mod == "moduleh":
        if page == 16:
            rows = d["implementation"]["task"]["table_fields"][0]["rows"]
            # Original PDF table extraction interleaves the last row and paragraph.
            # The independently pinned TXT line 195 preserves that exact row.
            rows = rows[:15] + [["16","Gmaj7","comp","G","sing target on prior beat 4"]]
            for row in rows:
                bar,chord,role,pitch,cue=row
                contacts.append(slot(pitch,"beat_one_target",chord,{"bar":int(bar),"beat":1},"Pre-heard target"))
                steps.append({"bar":int(bar),"chord":chord,"role":role,"target_contact_index":len(contacts)-1,
                              "sing_preview":"count-in" if int(bar)==1 else {"prior_bar":int(bar)-1,"beat":4}})
            alternatives.extend([{"pass":1,"rule":"one beat-one target; rest of bar silent"},
                                 {"pass":2,"rule":"accompaniment only, sing upcoming lead targets"},
                                 {"pass":3,"rule":"printed role map; beat 4 available before handoff"},
                                 {"pass":4,"rule":"partner changes four handoffs; preserve form"},
                                 {"pass":5,"rule":"free role/register/density/articulation, preserve chord and target schedule"}])
            pauses.append({"pass":1,"after":"one beat-one note","until":"next bar"})
            timing.update(authority="relative",unit="bar/beat",target_beat=1,preview_beat=4)
            context["source_extraction_limits"].append({"pdf_page":16,"issue":"last table row text interleaved with paragraph in prior extraction", "repaired_from_txt_line":195})
            unresolved.update(unavailable("pass_one_note_duration", "later_pass_notes", "comp_voicings", "random_cue_times"))
        else:
            fields=d["implementation"]["task"]["table_fields"][0]["values"]
            exercise, schedule, harmony=fields
            steps.extend([{"exercise":exercise,"role_schedule":schedule,"harmony_or_cue":harmony},
                          {"solo_substitute":"record one role, answer live, then reverse"}])
            if "Hidden cue" in exercise:
                timing.update(authority="relative",unit="partner cue",cue_time=None)
                unresolved["partner_cue_time"]="partner selected; no fixed cue time"
            else:
                timing.update(authority="relative",unit="bar/role order",role_schedule=schedule)
            unresolved.update(unavailable("actual_notes", "voicings", "rhythm"))
    else: raise ValueError(mod)

    # Locate exact original TXT lines where a corresponding printed entry exists.
    lo,hi=LINE_RANGES[mod]
    tail=key.split("/")[3]
    ordinal=int(re.search(r"(?:card|r)(\d+)$",tail).group(1)) if re.search(r"(?:card|r)(\d+)$",tail) else None
    if mod=="modulea": candidates=list(range(23 if page==2 else 37,35 if page==2 else 49))
    elif mod=="moduleb": candidates=[(51 if page==4 else 59)+int(re.search(r"card(\d+)",tail).group(1))]
    elif mod=="modulec": candidates=[(67 if page==6 else 81)+ordinal]
    elif mod=="moduled" and page==8: candidates=[{"E7":101,"G7":98,"Am7":99}[lines[0].split(". ",1)[1]]]
    elif mod=="moduled": candidates=[105+ordinal]
    elif mod=="modulee" and page==10: candidates=[115+int(re.search(r"(\d+)\. ",raw).group(1))]
    elif mod=="modulee": candidates=[125+int(re.search(r"card(\d+)",tail).group(1))]
    elif mod=="modulef" and page==12: candidates=[131+ordinal]
    elif mod=="modulef": candidates=[{"Cue at beat 1":142,"Visual nod":146,"Drum fill":147,
                                         "Cue at beat 3":144,"Held ensemble chord":148,"Cue at beat 4":145}[cue]]
    elif mod=="moduleg" and page==14: candidates=[151+ordinal]
    elif mod=="moduleg": candidates=[161+int(re.search(r"card(\d+)",tail).group(1))]
    elif mod=="moduleh" and page==16: candidates=list(range(180,196))+list(range(197,203))
    elif mod=="moduleh": candidates=[204+ordinal]
    else: raise ValueError(f"missing TXT locator {key}")
    if not all(lo<=n<=hi for n in candidates): raise ValueError(f"out-of-range TXT locator {key}")
    txt_locator={"path":str(TXT.relative_to(ROOT)),"sha256":EXPECTED[TXT],"relevant_lines":candidates or [lo,hi],
                 "printed_text":[TXT_LINES[n-1] for n in candidates]}
    pdf_locator={"path":str(PDF.relative_to(ROOT)),"sha256":EXPECTED[PDF],"physical_page":page,
                 "region":d["source_refs"][0]["locator"].get("regions"),"printed_text":raw}
    return {"schema_version":"fathom-private-level078-exercise-contract.1", "package_key":key,
            "source_identity":d["source_identity"],"source":{"pdf":pdf_locator,"txt":txt_locator,
            "prior_packet":{"path":str(PRIOR.relative_to(ROOT)),"sha256":EXPECTED[PRIOR]}},
            "implementation":context,"canonical_ids_allocated":False,"playback_admitted":False,
            "learner_observation":None,"score":None,"credit_awarded":False}


def main():
    manifest=json.loads(RESERVATION.read_text())
    keys=manifest["keys"]
    assert len(keys)==103 and len(set(keys))==103
    assert hashlib.sha256(("\n".join(sorted(keys))+"\n").encode()).hexdigest()==manifest["key_set_sha256"]
    for path,expected in EXPECTED.items():
        actual=digest(path)
        if actual!=expected: raise SystemExit(f"PIN_DRIFT {path}: {actual} != {expected}")
    prior={d["package_key"]:d for d in map(json.loads,PRIOR.read_text().splitlines())}
    if not set(keys)<=prior.keys(): raise SystemExit("missing prior child")
    contracts=[parse(prior[k]) for k in keys]
    if [c["package_key"] for c in contracts]!=keys: raise AssertionError("order or coverage changed")
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text("".join(json.dumps(c,ensure_ascii=False,sort_keys=True)+"\n" for c in contracts))
    print(json.dumps({"count":len(contracts),"contract_sha256":digest(OUT),
                      "pages":dict(Counter(c["source"]["pdf"]["physical_page"] for c in contracts)),
                      "peak_rss_bytes":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss},sort_keys=True))


if __name__=="__main__": main()
