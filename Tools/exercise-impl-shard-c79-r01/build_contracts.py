#!/usr/bin/env python3
"""Produce typed, non-admitted Level 79 contracts from pinned original sources."""
import hashlib
import json
import re
import resource
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[2]
RES = ROOT / "Prompts/manager-resume-r01/mass-implementation-shards-r01/shard-c79-reservation.json"
PRIOR = ROOT / "Build/fullscope-private-c-r01/level079-r06/implementation-packet.jsonl"
OUT = ROOT / "Build/exercise-impl-shard-c79-r01/source-contracts.jsonl"
PINS = {
    "Prompts/manager-resume-r01/mass-implementation-shards-r01/shard-c79-full-template-prompt.md": "ff7ec4791a689a6a9ebb71af79e17c04325b8ab6392609300952b571542aca9f",
    "Prompts/manager-resume-r01/mass-implementation-shards-r01/shard-c79-reservation.json": "6710c208b0b350a4e4172eeba1ca3315f0205328f71c2569e1c163d03f6548b6",
    "Results/level-oracle/exercise-completeness-r01/reviewed-handoff-r01/wbs-annex-candidate.jsonl": "dc285a946a929ba08a7e0e1075d56f9c2eb53ce2dfa9c70ea67d34270d2bda6c",
    "Planning/Fathom-Exercise-WBS-Annex-v1.json": "a76f5ca0b6bae1bf793cd9867b67f27dfa35e95f8a0596bc0eb1fe756ea67ce1",
    "Results/fullscope-private-c-r01/range-category-index-r06.json": "f282df4d03d28ca8590ea3ca20ac0466c876390fbdd1309f186b9899bd3261d7",
}


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def need(condition, message):
    if not condition:
        raise ValueError(message)


def table(row):
    t = row["implementation"]["task"]["table_fields"]
    need(len(t) == 1 and len(t[0]["columns"]) == len(t[0]["values"]), row["package_key"] + " table")
    return dict(zip(t[0]["columns"], t[0]["values"]))


def pdf_lines(row):
    return [s.strip() for s in row["source_payload"]["pdf_region_text"].splitlines() if s.strip()]


def txt_lines(module, leaf, row_num):
    if module == "modulea":
        return list(range(32, 41)) if leaf.startswith("p003") else list(range(32, 40))
    if module == "moduleb":
        return [44 + row_num] if leaf.startswith("p005") else [70 + row_num]
    if module == "modulec":
        return [81, 81 + row_num] if leaf.startswith("p007") else [91]
    if module == "moduled":
        if leaf.startswith("p009"):
            return [95 + row_num]
        return [[110, 114, 111, 115, 112, 116, 113, 117][row_num - 1]]
    if module == "modulee":
        return [121 + row_num] if leaf.startswith("p011") else [131 + row_num]
    if module == "modulef":
        if leaf.startswith("p013"):
            return [143 + row_num] if row_num <= 10 else [155]
        return [[158, 162, 159, 160, 164, 161, 165][[1, 2, 3, 5, 6, 7, 8].index(row_num)]]
    if module == "moduleg":
        return {"p015-card01": [170, 171, 172, 173], "p015-card02": [174, 175],
                "p016-card02": [179, 180, 181], "p017-card01": [182, 183, 184],
                "p017-card02": [185, 186, 187]}[leaf]
    raise ValueError(module)


def contract(key, row, txt, page_text):
    module, leaf = key.split("/")[2:4]
    n = int(re.search(r"(?:-r|-card)(\d+)", leaf).group(1)) if leaf != "p003-u001" else 0
    page = row["source_refs"][0]["locator"]["physical_pages"][0]
    label = row["source_payload"]["printed_label"]
    lines = pdf_lines(row)
    need(label.casefold() in page_text.casefold(), key + " PDF label drift")
    tl = txt_lines(module, leaf, n)
    need(all(1 <= i <= len(txt) for i in tl), key + " TXT locator")
    c = {
        "schema_version": "fathom-level79-private-source-contract.1",
        "package_key": key,
        "source_identity": row["source_identity"],
        "source": {"pdf": {"path": row["source_refs"][0]["path"], "sha256": row["source_refs"][0]["sha256"], "physical_page": page,
                           "printed_label": label, "region_text": row["source_payload"]["pdf_region_text"],
                           "original_page_extract_sha256": hashlib.sha256(page_text.encode()).hexdigest()},
                   "txt": {"path": row["source_refs"][1]["path"], "sha256": row["source_refs"][1]["sha256"],
                           "lines": [{"line": i, "text": txt[i - 1]} for i in tl]},
                   "discrepancies": row["source_payload"].get("source_discrepancies", [])},
        "implementation": {"delivery": "manual_parameterized_source_contract", "kind": None, "prescription": {},
                           "note_or_contact_order": [], "string_fret_finger": {"string_set": None, "string_set_order": [], "fret": None, "finger": None},
                           "technique": [], "pause_hold_rest": [],
                           "timing": {"authority": "unavailable", "relative": [], "absolute": None, "fixed_bpm": None},
                           "unresolved_fields": ["performed_onsets", "performed_durations", "fixed_bpm", "exact_octaves", "frets", "fingers", "chord_voicings", "observed_performance"],
                           "source_conflicts": [], "source_differences": [], "learner_choice_parameters": [],
                           "automatic_score": False, "credit_awarded": False, "canonical_ids_allocated": False},
    }
    I = c["implementation"]
    if module == "modulea" and leaf.startswith("p003"):
        T = row["implementation"]["task"]["table_fields"][0]
        need(len(T["rows"]) == 8, key + " arc count")
        I["kind"] = "dynamic_arc"
        I["prescription"] = {"bar_sections": [dict(zip(T["columns"], r)) for r in T["rows"]],
                             "passes": ["roots only", "shells", "full arrangement"]}
        I["timing"]["authority"] = "relative_bars_only"
        I["timing"]["relative"] = ["bar ranges and contacts per bar only; contact placements unspecified"]
        I["learner_choice_parameters"] = ["specific roots/shells/voicings", "contact placements within each bar"]
        I["unresolved_fields"].append("specific_contacts_in_density_ranges")
        I["unresolved_fields"].append("header_says_eight_passes_but_only_three_pass_instructions_are_printed")
    elif module == "modulea":
        I["kind"] = "register_texture_card"
        reg = next(s.split(":", 1)[1].strip() for s in lines if s.startswith("Register:"))
        texture = next(s.split(":", 1)[1].strip() for s in lines if s.startswith("Texture:"))
        I["prescription"] = {"section": label, "register": reg, "texture": texture,
                             "global_rest_rule": "at least one full silent beat in every four-bar block (PDF p4)"}
        string_sets = re.findall(r"\b(?:E/A|D/G/B|G/B/e)\b", reg)
        if string_sets:
            I["string_fret_finger"]["string_set"] = string_sets[0].split("/")
            I["string_fret_finger"]["string_set_order"] = [s.split("/") for s in string_sets]
        if "rest" in texture or "empty" in texture or "silence" in texture:
            I["pause_hold_rest"].append({"kind": "rest", "rule": texture})
        I["pause_hold_rest"].append({"kind": "rest", "rule": "one full beat silent per four-bar block"})
        I["learner_choice_parameters"] = ["note/voicing selection", "contact placement respecting rests"]
        I["timing"]["authority"] = "relative_bars_only"
        I["timing"]["relative"] = ["section/bar placement from master 48-bar form", "full-beat rest requirement"]
    elif module == "moduleb" and leaf.startswith("p005"):
        t = table(row)
        I["kind"] = "structural_target"
        I["prescription"] = {"context": t["Context"], "chord": t["Chord"], "target": t["Target"],
                             "harmonic_role": t["Role"], "action_order": ["sing target", "one target attack", "play in two registers"]}
        I["note_or_contact_order"] = [t["Target"]]
        I["learner_choice_parameters"] = ["two octave/register locations", "string/fret", "attack placement"]
        I["timing"]["authority"] = "relative_action_order_only"
        I["timing"]["relative"] = ["sing before first target attack; two registers thereafter"]
        I["source_differences"].append({"field": "action_detail", "pdf": "one attack -> 2 registers", "txt": "silently locate, then play in two registers", "resolution": "PDF supplies one-attack step; exact total attacks across registers unavailable"})
        I["unresolved_fields"].append("exact_total_attacks_across_two_registers")
    elif module == "moduleb":
        m = re.match(r"(.+?)\s+((?:[A-G][#b]?(?:m7b5|maj7|m7|7)(?: -> )?){3})\s+V1\s+(.+)", lines[0])
        need(m is not None, key + " chain parse")
        chords = m.group(2).split(" -> ")
        v1 = m.group(3).split(" -> ")
        v2 = lines[1].removeprefix("V2 ").split(" -> ")
        need(len(chords) == len(v1) == len(v2) == 3, key + " chain length")
        I["kind"] = "two_voice_harmonic_chain"
        I["prescription"] = {"route": label, "chords": chords, "voice_1": v1, "voice_2": v2,
                             "pass_order": ["two guide-tone lines", "add roots", "complete arpeggios", "free phrases after key change is clear"]}
        I["note_or_contact_order"] = [{"chord": a, "voice_1": b, "voice_2": d} for a, b, d in zip(chords, v1, v2)]
        I["learner_choice_parameters"] = ["voice register and fretboard position", "rhythmic realization"]
        I["timing"]["authority"] = "relative_harmonic_order_only"
        I["timing"]["relative"] = ["three ordered harmonic stages; no fixed durations"]
    elif module == "modulec" and leaf.startswith("p007"):
        start = re.search(r"Start on (.+)", label).group(1)
        offset = {"beat 1": 0, "e of 1": 1, "& of 1": 2, "a of 1": 3,
                  "beat 2": 4, "& of 2": 6, "beat 4": 12, "& of 4": 14}[start]
        I["kind"] = "motif_first_onset_displacement"
        I["prescription"] = {"motif": ["C", "E", "G", "B", "A", "G", "E", "D"],
                             "first_onset_sixteenth_offset_from_barline": offset,
                             "chord": "Cmaj7", "barline_and_chord_change": "fixed"}
        I["note_or_contact_order"] = I["prescription"]["motif"]
        I["timing"]["authority"] = "relative_first_onset_only"
        I["timing"]["relative"] = ["first onset at printed sixteenth subdivision", "remaining note spacing unavailable", "Cmaj7 barline fixed"]
        I["unresolved_fields"].append("inter_note_spacing_and_motif_completion_across_barline")
        I["learner_choice_parameters"] = ["octave/string/fret", "note durations after first onset"]
    elif module == "modulec":
        t = table(row)
        I["kind"] = "rhythm_texture_study"
        I["prescription"] = {"location": t["Location"], "device": t["Device"], "grid": t["Grid"],
                             "instruction": t["Instruction"], "follow_with": "plain version of same bars immediately"}
        I["timing"]["authority"] = "relative_grid_only"
        I["timing"]["relative"] = [t["Grid"], t["Instruction"], "plain version immediately follows"]
        I["learner_choice_parameters"] = ["notes/chord voicings", "actual contacts and repetitions"]
        I["unresolved_fields"].append("exact_contact_count_and_onsets")
        if t["Device"] == "quintuplet beat":
            I["learner_choice_parameters"].append("which one of the two location bars carries the quintuplet")
            I["unresolved_fields"].append("quintuplet_bar_choice")
    elif module == "moduled" and leaf.startswith("p009"):
        t = table(row)
        I["kind"] = "ensemble_cue_response"
        I["prescription"] = {"cue": t["Cue"], "lead_time": t["Lead time"], "required_response": t["Required response"],
                             "if_missed": t["Recovery if missed"], "pulse_rule": "keep current beat and active chord"}
        I["timing"]["authority"] = "relative_cue_window"
        I["timing"]["relative"] = [t["Lead time"]]
        I["learner_choice_parameters"] = ["cue occurrence in a performed take", "note/voicing response"]
        if "sustain" in t["Required response"] or "mute" in t["Required response"]:
            I["pause_hold_rest"].append({"kind": "hold_or_mute", "rule": t["Required response"]})
    elif module == "moduled":
        need(label in lines and lines.index(label) + 1 < len(lines), key + " action position")
        action = lines[lines.index(label) + 1]
        role = label.split(":", 1)[1].strip()
        I["kind"] = "cue_role_transition"
        I["prescription"] = {"cue": label.split(":", 1)[0], "role_transition": role, "ordered_action": action.split("; "),
                             "bar_count": "preserved", "harmony": "unchanged"}
        I["timing"]["relative"] = [x for x in ["beat 3" if "beat 3" in action else None,
                                            "next bar" if "next bar" in action else None,
                                            "beat-one during count" if "beat-one" in action else None] if x]
        I["timing"]["authority"] = "relative_cue_window" if I["timing"]["relative"] else "unavailable"
        I["learner_choice_parameters"] = ["actual cue occurrence", "selected notes and voicing"]
        if "SILENCE" in role or "mute" in action or "stop adding" in action:
            I["pause_hold_rest"].append({"kind": "mute_or_silence", "rule": action})
    elif module == "modulee" and leaf.startswith("p011"):
        t = table(row)
        chords = t["Progression"].split("-")
        roles = t["Role map"].split()
        need(len(chords) == len(roles) == 4, key + " circuit count")
        I["kind"] = "four_bar_role_circuit"
        I["prescription"] = {"key": t["Key"], "bar_map": [{"ordinal": i + 1, "chord": ch, "role": "comp" if role == "C" else "lead"} for i, (ch, role) in enumerate(zip(chords, roles))],
                             "prehear": "sing first lead target before entry", "partner_option": "invert role map after count-in; progression unchanged"}
        I["note_or_contact_order"] = chords
        I["timing"]["authority"] = "relative_bars_only"
        I["timing"]["relative"] = ["one printed chord and role per bar, four bars"]
        I["learner_choice_parameters"] = ["actual comp voicing", "lead target", "partner role inversion", "contacts per bar"]
    elif module == "modulee":
        t = table(row)
        I["kind"] = "density_register_transition"
        I["prescription"] = {"study": t["Study"], "outgoing": t["Outgoing role"], "incoming": t["Incoming role"], "register": t["Register"]}
        I["timing"]["relative"] = [x for x in [t["Outgoing role"], t["Incoming role"]] if any(w in x for w in ["/bar", "quarters", "8th", "16th", "3+3+2"])]
        I["timing"]["authority"] = "relative_grid_or_density_only" if I["timing"]["relative"] else "relative_role_order_only"
        I["learner_choice_parameters"] = ["specific notes", "voicings", "transition location"]
    elif module == "modulef" and leaf.startswith("p013"):
        t = table(row)
        if label == "Memory blank":
            # Prior range packet accidentally spliced the page footer into this row.
            # The original PDF page 13 and TXT line 155 agree on the three fields.
            need("Memory blank" in page_text and "silence + count" in page_text and "enter at next structural bar" in page_text,
                 key + " original memory-blank row")
            t = {"Failure": "Memory blank", "Immediate repair": "silence + count", "Next action": "enter at next structural bar"}
            c["source"]["prior_packet_repair"] = "Discard corrupted PDF table-row splice; restored exact page-13/TXT-155 row"
            c["source"]["pdf"]["region_text"] = "Memory blank | silence + count | enter at next structural bar"
        I["kind"] = "ear_led_recovery"
        I["prescription"] = {"failure": t["Failure"], "immediate_repair": t["Immediate repair"], "next_action": t["Next action"],
                             "priority": "recover function, then restore complexity"}
        I["timing"]["relative"] = ["repair precedes next action"] + (["next beat"] if "next beat" in t["Next action"] else [])
        I["timing"]["authority"] = "relative_repair_order_only"
        I["learner_choice_parameters"] = ["trigger time and harmony", "specific realization"]
        if "silence" in t["Immediate repair"] or "stop" in t["Immediate repair"]:
            I["pause_hold_rest"].append({"kind": "silence_or_stop", "rule": t["Immediate repair"]})
    elif module == "modulef":
        need(label in lines and lines.index(label) + 1 < len(lines), key + " scenario action position")
        action = lines[lines.index(label) + 1]
        I["kind"] = "randomized_recovery_scenario"
        I["prescription"] = {"scenario": label, "repair": action, "continuation": "continue through section exit; no restart",
                             "scoring_window": "first error until next section boundary"}
        I["timing"]["authority"] = "relative_scenario_window"
        I["timing"]["relative"] = [x for x in ["beat 3" if "beat 3" in action else None,
                                            "next bar" if "next bar" in action else None,
                                            "quarter notes" if "quarter" in action else None,
                                            "straight eighths" if "eighth" in action else None,
                                            "immediate" if "immediate" in action else None] if x]
        I["learner_choice_parameters"] = ["scenario onset in take", "specific voicing"]
        if "mute" in action or "skip fill" in action:
            I["pause_hold_rest"].append({"kind": "mute_or_omit", "rule": action})
    else:
        need(module == "moduleg", key + " unhandled")
        bar_data = {
            "p015-card01": (1, "Cmaj7 Am7 Dm7 G7 Cmaj7 Am7 Dm7 G7 Cmaj7 A7 Dm7 G7"),
            "p015-card02": (13, "Am7 D7 Gmaj7 D7"),
            "p016-card02": (25, "Gmaj7 Em7 Am7 D7 Cmaj7 B7 Em7 E7"),
            "p017-card01": (33, "Am7 Dm7 E7 Am7 Fmaj7 Bm7b5 E7 Am7"),
            "p017-card02": (41, "Dm7 G7 Cmaj7 A7 Dm7 G7 Cmaj7 Gmaj7"),
        }
        first, sequence = bar_data[leaf]
        chords = sequence.split()
        need(all(ch in page_text for ch in chords), key + " PDF chord drift")
        I["kind"] = "section_harmony_study"
        I["prescription"] = {"section": label, "bar_map": [{"bar": first + j, "chord": ch} for j, ch in enumerate(chords)],
                             "tasks": [s for s in lines[1:] if "Tasks:" in s or "contacts" in s or "motif" in s or "the Chorus" in s or "from mf" in s]}
        I["note_or_contact_order"] = chords
        I["timing"]["authority"] = "relative_bars_only"
        I["timing"]["relative"] = ["one printed chord per numbered bar"]
        if leaf == "p015-card01":
            I["prescription"]["target_constraints"] = [{"bar": 10, "pitch": "C#", "chord": "A7"}]
            I["pause_hold_rest"].append({"kind": "rest", "bar": 12, "beat": 4, "rule": "empty for Pre cue"})
        if leaf == "p015-card02":
            I["prescription"]["target_constraints"] = [{"bar": 14, "pitch": "F#", "action": "sing before D7"}, {"bar": 15, "pitch": "B", "chord": "Gmaj7"}]
            I["prescription"]["printed_voice_lines"] = [["C", "C", "B", "F#"], ["E", "F#", "F#", "C"]]
            I["note_or_contact_order"] = [{"bar": 13 + j, "chord": chords[j], "voice_1": I["prescription"]["printed_voice_lines"][0][j],
                                            "voice_2": I["prescription"]["printed_voice_lines"][1][j]} for j in range(4)]
        if leaf == "p016-card02":
            I["prescription"]["target_constraints"] = [{"bar": 30, "pitch": "D#", "chord": "B7"}, {"bar": 32, "pitch": "G#", "chord": "E7"}]
            I["prescription"]["contact_density"] = "2-4 per bar"
        if leaf == "p017-card01":
            I["prescription"]["target_constraints"] = [{"bar": 38, "pitch": "F", "chord": "Bm7b5"}, {"bar": 39, "pitch": "G#", "chord": "E7"}, {"bar": 40, "pitch_choices": ["C", "A"], "chord": "Am7"}]
        if leaf == "p017-card02":
            I["prescription"]["final_chord_hold"] = "sustain Gmaj7; do not restart form"
            I["pause_hold_rest"].append({"kind": "hold", "bar": 48, "rule": "sustain final Gmaj7"})
        I["learner_choice_parameters"] = ["note realization", "chord voicing", "contact placements", "motif realization"]
    # Source-provided musical pitches are pitch classes; never infer octave, fret or fingering.
    return c


def main():
    for p, expected in PINS.items():
        need(sha(ROOT / p) == expected, "pin drift: " + p)
    manifest = json.loads(RES.read_text())
    keys = manifest["keys"]
    need(len(keys) == len(set(keys)) == 109, "reservation count/uniqueness")
    need(hashlib.sha256(("\n".join(sorted(keys)) + "\n").encode()).hexdigest() == manifest["key_set_sha256"], "key set hash")
    prior = {x["package_key"]: x for x in map(json.loads, PRIOR.open())}
    need(set(keys) <= set(prior), "prior packet coverage")
    pdf_path = ROOT / prior[keys[0]]["source_refs"][0]["path"]
    txt_path = ROOT / prior[keys[0]]["source_refs"][1]["path"]
    need(sha(pdf_path) == "00a75f782c15ef8e8aaa8239b64f96cd272e90fca74ccc3ad09da362ad12aebb", "original PDF drift")
    need(sha(txt_path) == "56e42cd4324af9178b85d2525c38241e85b7c91c9cb75d9bfc7c7013664793fe", "original TXT drift")
    txt = txt_path.read_text().splitlines()
    reader = PdfReader(str(pdf_path))
    pages = {i: reader.pages[i - 1].extract_text(extraction_mode="layout") for i in range(3, 18)}
    out = []
    for key in keys:
        row = prior[key]
        need(row["level"] == 79 and row["implementation"]["events"] == [], key + " prior guard")
        page = row["source_refs"][0]["locator"]["physical_pages"][0]
        tf = row["implementation"]["task"]["table_fields"]
        if len(tf) == 1 and "values" in tf[0] and row["source_payload"]["printed_label"] != "Memory blank":
            normalized_page = " ".join(pages[page].split())
            need(all(" ".join(v.split()) in normalized_page for v in tf[0]["values"]), key + " original PDF field mismatch")
        out.append(contract(key, row, txt, pages[page]))
    need(len(out) == 109 and len({r["package_key"] for r in out}) == 109, "output coverage")
    OUT.write_text("".join(json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for x in out))
    print(json.dumps({"status": "PASS", "contracts": len(out), "output": str(OUT.relative_to(ROOT)), "sha256": sha(OUT),
                      "pdf_sha256": sha(pdf_path), "txt_sha256": sha(txt_path),
                      "peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}, sort_keys=True))


if __name__ == "__main__":
    main()
