#!/usr/bin/env python3
"""Build a detached, pinned whole-source Level 77 ear-to-hand candidate."""

from __future__ import annotations

import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path
import re

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
STEM = "Guitar_Exercises_Section_X_Level_77_Interval_Recognition_Chord_Function_Hearing_Sung_Guide_Tones_Melodic_Dictation_Call_and_Response_and_Immediate_Fretboard_Realization"
TXT = Path("Notes/music/guitar project/TXT version") / (STEM + ".txt")
PDF = Path("Notes/music/guitar project/PDF version") / (STEM + ".pdf")
MAP = Path("Results/parallel-01/exercises/inventory/20260922T180500Z-2.3-curriculum-v1-source-inventory-evidence/curriculum-source-map.json")
OUT = Path("Build/parallel-07/2.3.1.3.1-level077-whole-r01")
PINS = {"txt": (3011, "54ab2490448e1fa6391ead275fe22e2fbec9be23d6e83c88001293b4be7e7236"),
        "pdf": (54683, "bfeaab5b0ddd52ac55063e0552b8c451d8a8029ddb073b744d8f0e76186aedce")}
COUNTS = {"A": 144, "B": 96, "C": 120, "D": 128, "E": 128, "F": 112, "G": 96, "H": 128}
TABLES = {
    "interval_atlas": (2, ["Interval", "Semitones", "Reference", "Sing upward", "Sing downward"], 12, 3),
    "interval_cards": (3, ["Card", "Start", "Destination", "Direction", "Answer"], 24, 5),
    "interval_transfer": (4, ["Card", "Given root", "Requested interval", "Sing destination", "Low / mid / high"], 12, 3),
    "function_atlas": (5, ["Roman", "Family", "Functional sensation", "Sing after chord", "Resolve"], 7, 5),
    "function_progressions": (6, ["Key", "Source progression", "Roman answer", "Function answer"], 12, 4),
    "major_guides": (7, ["Chord", "Guide 1", "Role", "Guide 2", "Role", "Task"], 5, 6),
    "minor_guides": (8, ["Chord", "Guide 1", "Role", "Guide 2", "Role", "Task"], 5, 6),
    "dictation_phrases": (9, ["Context", "Degree answer", "Pitch answer", "Contour / confidence"], 8, 3),
    "rhythm_dictation": (10, ["Card", "Context", "Pitch contour", "Rhythm layer", "Rebuild"], 8, 4),
    "call_response": (11, ["Chord", "Question", "Exact echo", "Answer model"], 8, 4),
    "memory_delays": (12, ["Card", "Source question", "Required delay", "Reproduction / answer"], 8, 3),
    "degree_realization": (13, ["Context", "Requested degree", "Answer pitch", "Low", "Mid", "High"], 14, 3),
    "chord_realization": (14, ["Chord", "Role", "Pitch", "Sing", "String set 1", "String set 2"], 14, 3),
    "reaction_ladder": (15, ["Stage", "Command type", "Response limit", "Required response"], 12, 4),
    "model_bars": (17, ["Bar", "Chord", "Four-note source", "Structural target"], 16, 4),
    "capstone_rubric": (19, ["Category", "0", "1", "2"], 6, 4),
}
PC = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4,
      "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9,
      "A#": 10, "Bb": 10, "B": 11, "B#": 0}
INTERVAL = {"m2": 1, "M2": 2, "m3": 3, "M3": 4, "P4": 5, "TT": 6,
            "P5": 7, "m6": 8, "M6": 9, "m7": 10, "M7": 11, "P8": 12}
SCALES = {"C major": ("C", [0, 2, 4, 5, 7, 9, 11]),
          "G major": ("G", [0, 2, 4, 5, 7, 9, 11]),
          "D major": ("D", [0, 2, 4, 5, 7, 9, 11]),
          "A major": ("A", [0, 2, 4, 5, 7, 9, 11]),
          "E major": ("E", [0, 2, 4, 5, 7, 9, 11]),
          "F major": ("F", [0, 2, 4, 5, 7, 9, 11]),
          "A minor": ("A", [0, 2, 3, 5, 7, 8, 10]),
          "E minor": ("E", [0, 2, 3, 5, 7, 8, 10]),
          "D minor": ("D", [0, 2, 3, 5, 7, 8, 10]),
          "A harmonic minor": ("A", [0, 2, 3, 5, 7, 8, 11]),
          "A melodic minor": ("A", [0, 2, 3, 5, 7, 9, 11])}
MAJOR_ROMAN = {"I": (0, "T"), "ii": (2, "P"), "iii": (4, "T"),
               "IV": (5, "P"), "V": (7, "D"), "vi": (9, "T"), "vii dim": (11, "D")}
CHORD_ROOT = {"Cmaj7": "C", "Dm7": "D", "G7": "G", "Am7": "A", "Fmaj7": "F",
              "AmMaj7": "A", "Bm7b5": "B", "E7": "E", "A7": "A", "D7": "D",
              "Gmaj7": "G", "D7#11": "D", "G#7alt": "G#"}
ROLE_SEMITONES = {"3": 4, "7": 11, "b3": 3, "b7": 10, "b5": 6, "#11": 6}
MODEL_CHORD_TONES = {"Cmaj7": {0, 4, 7, 11}, "Am7": {9, 0, 4, 7},
                     "Dm7": {2, 5, 9, 0}, "G7": {7, 11, 2, 5},
                     "E7": {4, 8, 11, 2}, "A7": {9, 1, 4, 7},
                     "D7": {2, 6, 9, 0}, "Gmaj7": {7, 11, 2, 6}}


class CandidateError(ValueError):
    pass


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def source(root: Path, rel: Path, pin: tuple[int, str]) -> bytes:
    path = root / rel
    if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root.resolve()):
        raise CandidateError(f"SOURCE_PATH_INVALID {rel}")
    data = path.read_bytes()
    if (len(data), sha(data)) != pin:
        raise CandidateError(f"PINNED_INPUT_DRIFT {rel}")
    return data


def source_map(root: Path) -> dict:
    row = next((r for r in json.loads((root / MAP).read_text())["rows"] if r["level"] == 77), None)
    expected = {"section": "X", "wbs_owner": "2.3.1.3.1", "txt_path": str(TXT),
                "pdf_path": str(PDF), "txt_bytes": PINS["txt"][0], "pdf_bytes": PINS["pdf"][0],
                "txt_sha256": PINS["txt"][1], "pdf_sha256": PINS["pdf"][1],
                "pair_status": "exact_stem_pair", "conversion_status": "not_converted",
                "stable_ids_assigned": False, "runtime_eligible": False,
                "imported": False, "admitted": False}
    if row is None or any(row.get(k) != v for k, v in expected.items()):
        raise CandidateError("SOURCE_MAP_IDENTITY_OR_STATUS_DRIFT")
    return row


def table(page: str, headers: list[str], count: int, active: int, label: str) -> list[dict]:
    lines = page.splitlines()
    positions = [i for i in range(len(lines)) if lines[i:i + len(headers)] == headers]
    if len(positions) != 1:
        raise CandidateError(f"PDF_TABLE_HEADER {label}")
    start = positions[0] + len(headers)
    cells = lines[start:start + count * active]
    if len(cells) != count * active:
        raise CandidateError(f"PDF_TABLE_LENGTH {label}")
    keys = [f"{h} {headers[:j + 1].count(h)}" if headers.count(h) > 1 else h
            for j, h in enumerate(headers[:active])]
    return [dict(zip(keys, cells[i * active:(i + 1) * active], strict=True))
            for i in range(count)]


def notes(text: str) -> list[str]:
    found = text.split("-")
    if not found or any(n not in PC for n in found):
        raise CandidateError(f"NOTE_TOKENS_INVALID {text}")
    return found


def degree_pc(context: str, degree: str) -> int:
    if context not in SCALES or not re.fullmatch(r"[b#]?[1-7]", degree):
        raise CandidateError(f"DEGREE_INVALID {context}:{degree}")
    root, steps = SCALES[context]
    accidental = -1 if degree.startswith("b") else 1 if degree.startswith("#") else 0
    number = int(degree[-1])
    # Minor contexts print b3/b6/b7 against the major-scale degree map.
    if context.endswith("minor"):
        base = [0, 2, 4, 5, 7, 9, 11][number - 1]
    else:
        base = steps[number - 1]
    return (PC[root] + base + accidental) % 12


def event(note: str | None, *, page: int, table_name: str, row: int, slot: int,
          role: str, degree: str | None = None) -> dict:
    return {"local_key": f"l77-p{page:02d}-{table_name}-{row:02d}-{role}-{slot:02d}",
            "source": {"pdf_page": page, "table": table_name, "row": row, "slot": slot},
            "pitch_name": note, "pitch_class": PC[note] if note in PC else None,
            "degree": degree, "role": role, "octave": None, "string": None,
            "fret": None, "onset_q": None, "duration_q": None,
            "canonical_event_id": None, "performed_result": None}


def task(module: str, kind: str, page: int, row: int | None, fields: dict,
         txt_line: int | None = None) -> dict:
    return {"local_key": f"l77-{module.lower()}-p{page:02d}-{kind}-{row or 0:02d}",
            "module": module, "kind": kind, "source": {"txt_line": txt_line,
            "pdf_page": page, "table_row": row}, "fields": fields,
            "canonical_task_id": None, "answer_visibility": "source_player_only_until_response"
            if kind in {"interval_dictation", "function_dictation", "melodic_dictation",
                        "call_response", "memory_delay", "model_bar"} else "learner_visible",
            "observed_answer": None, "observed_score": None}


def build(root: Path = ROOT) -> dict:
    raw_txt = source(root, TXT, PINS["txt"])
    raw_pdf = source(root, PDF, PINS["pdf"])
    row = source_map(root)
    lines = raw_txt.decode("utf-8").splitlines()
    pages = [p.extract_text() or "" for p in PdfReader(BytesIO(raw_pdf)).pages]
    if len(lines) != 80 or len(pages) != 20 or any(
        "Section X, Level 77" not in page.splitlines()[0] for page in pages):
        raise CandidateError("SOURCE_LINE_OR_PAGE_BOUNDARY")
    parsed = {name: table(pages[page - 1], heads, n, active, name)
              for name, (page, heads, n, active) in TABLES.items()}
    tasks: list[dict] = []
    events: list[dict] = []
    anomalies: list[dict] = []

    def add(module: str, kind: str, page: int, row_no: int | None, fields: dict,
            txt_line: int | None = None) -> None:
        tasks.append(task(module, kind, page, row_no, fields, txt_line))

    # A: the atlas, played interval cards, and transfer prompts are distinct tasks.
    for i, r in enumerate(parsed["interval_atlas"], 1):
        label, size, ref = r["Interval"], int(r["Semitones"]), r["Reference"]
        a, b = notes(ref)
        if INTERVAL.get(label) != size or (PC[b] - PC[a]) % 12 != size % 12:
            raise CandidateError(f"INTERVAL_ATLAS_MUSIC {i}")
        literal = f"{label}: {size} semitones; reference {ref}"
        if literal not in lines:
            raise CandidateError(f"TXT_INTERVAL_PARITY {i}")
        add("A", "interval_reference", 2, i, {"interval": label, "semitones": size,
            "reference": [a, b], "directions": ["up", "down"]}, lines.index(literal) + 1)
    for i, r in enumerate(parsed["interval_cards"], 1):
        a, b, direction, label = r["Start"], r["Destination"], r["Direction"], r["Answer"]
        if int(r["Card"]) != i or label not in INTERVAL or direction not in ("up", "down"):
            raise CandidateError(f"INTERVAL_CARD_FORMAT {i}")
        distance = (PC[b] - PC[a]) % 12 if direction == "up" else (PC[a] - PC[b]) % 12
        if distance != INTERVAL[label] % 12:
            if i != 20:
                raise CandidateError(f"INTERVAL_CARD_MUSIC {i}")
            anomalies.append({"pdf_page": 3, "issue": "card 20 prints B down to D as m6; pitch-class descent is M6",
                              "printed_answer": label, "computed_semitones": distance,
                              "resolution": "unresolved_source_error"})
        add("A", "interval_dictation", 3, i, {"start": a, "destination": b,
            "direction": direction, "answer": label, "octave_unresolved": True})
        events.extend([event(n, page=3, table_name="interval_cards", row=i, slot=s,
                             role=role) for s, (n, role) in enumerate(((a, "source"), (b, "answer")), 1)])
    for i, r in enumerate(parsed["interval_transfer"], 1):
        a, label = r["Given root"], r["Requested interval"]
        if int(r["Card"]) != i or a not in PC or label not in INTERVAL:
            raise CandidateError(f"INTERVAL_TRANSFER_FORMAT {i}")
        add("A", "random_root_transfer", 4, i, {"root": a, "interval": label,
            "destination_pitch_class": (PC[a] + INTERVAL[label]) % 12,
            "answer_spelling": None, "registers": ["low", "mid", "high"],
            "locations": None})

    # B: verify the seven-family map and every printed progression's root/function.
    for i, r in enumerate(parsed["function_atlas"], 1):
        roman = r["Roman"]
        if roman not in MAJOR_ROMAN:
            raise CandidateError(f"ROMAN_ATLAS {i}")
        literal = f"{roman}: {r['Family']}; {r['Functional sensation']}"
        if literal not in lines:
            raise CandidateError(f"TXT_FUNCTION_PARITY {i}")
        add("B", "function_reference", 5, i, r, lines.index(literal) + 1)
    for i, r in enumerate(parsed["function_progressions"], 1):
        context = r["Key"] + " major"
        chords = r["Source progression"].split("-")
        romans = r["Roman answer"].split("-")
        families = r["Function answer"].split("-")
        if len(chords) != 4 or len(romans) != 4 or len(families) != 4:
            raise CandidateError(f"PROGRESSION_WIDTH {i}")
        tonic = PC[SCALES[context][0]]
        for j, (chord, roman, family) in enumerate(zip(chords, romans, families, strict=True), 1):
            if roman not in MAJOR_ROMAN or family != MAJOR_ROMAN[roman][1]:
                raise CandidateError(f"PROGRESSION_FUNCTION {i}:{j}")
            root_match = re.match(r"[A-G](?:#|b)?", chord)
            if not root_match or (tonic + MAJOR_ROMAN[roman][0]) % 12 != PC[root_match.group()]:
                raise CandidateError(f"PROGRESSION_ROOT {i}:{j}")
        add("B", "function_dictation", 6, i, {"key": context,
            "source_chords": chords, "roman_answer": romans, "function_answer": families,
            "missing_final_tonic_second_pass": True})

    # C: all ten printed guide-tone pairs, roles, and cadence instructions.
    for label, page in (("major_guides", 7), ("minor_guides", 8)):
        for i, r in enumerate(parsed[label], 1):
            chord = r["Chord"]
            if chord not in CHORD_ROOT:
                raise CandidateError(f"GUIDE_CHORD {label}:{i}")
            guide = [(r["Guide 1"], r["Role 1"]), (r["Guide 2"], r["Role 2"])]
            for j, (note, role) in enumerate(guide, 1):
                if role not in ROLE_SEMITONES or (PC[CHORD_ROOT[chord]] + ROLE_SEMITONES[role]) % 12 != PC[note]:
                    raise CandidateError(f"GUIDE_ROLE {label}:{i}:{j}")
                events.append(event(note, page=page, table_name=label, row=i, slot=j,
                                    role="guide_tone", degree=role))
            literal = f"{chord}: {guide[0][0]}({guide[0][1]}) + {guide[1][0]}({guide[1][1]})"
            if literal not in lines:
                raise CandidateError(f"TXT_GUIDE_PARITY {label}:{i}")
            add("C", "sung_guide_pair", page, i, {"chord": chord, "guides": guide,
                "command": r["Task"], "fretboard_shell": None}, lines.index(literal) + 1)

    # D: printed pitch and degree answers plus a separate rhythm layer with no grid.
    for i, (r, rhythm) in enumerate(zip(parsed["dictation_phrases"], parsed["rhythm_dictation"], strict=True), 1):
        context, degrees, pitches = r["Context"], r["Degree answer"].split("-"), notes(r["Pitch answer"])
        if not (len(degrees) == len(pitches)) or int(rhythm["Card"]) != i or rhythm["Context"] != context or rhythm["Pitch contour"] != r["Degree answer"]:
            raise CandidateError(f"DICTATION_PAIR {i}")
        for j, (degree, pitch) in enumerate(zip(degrees, pitches, strict=True), 1):
            if degree_pc(context, degree) != PC[pitch]:
                raise CandidateError(f"DICTATION_DEGREE {i}:{j}")
            events.append(event(pitch, page=9, table_name="dictation_phrases", row=i,
                                slot=j, role="melodic_answer", degree=degree))
        literal = f"{context}: degrees {r['Degree answer']}; pitches {r['Pitch answer']}"
        if literal not in lines:
            raise CandidateError(f"TXT_DICTATION_PARITY {i}")
        add("D", "melodic_dictation", 9, i, {"context": context, "degrees": degrees,
            "answer_pitches": pitches, "passes": ["contour", "degree", "exact_note"]},
            lines.index(literal) + 1)
        add("D", "rhythm_pitch_dictation", 10, i, {"context": context,
            "degrees": degrees, "answer_pitches": pitches,
            "rhythm_label": rhythm["Rhythm layer"], "meter": None,
            "onsets": None, "durations": None, "two_bar_claim": True})

    # E: exact questions/answers and the eight distinct printed delay commands.
    for i, (r, delayed) in enumerate(zip(parsed["call_response"], parsed["memory_delays"], strict=True), 1):
        question, answer = notes(r["Question"]), notes(r["Answer model"])
        if len(question) != 4 or len(answer) != 4 or int(delayed["Card"]) != i or delayed["Source question"] != r["Question"]:
            raise CandidateError(f"CALL_RESPONSE_PAIR {i}")
        for role, seq in (("source_question", question), ("model_answer", answer)):
            events.extend(event(n, page=11, table_name="call_response", row=i, slot=j,
                                role=role) for j, n in enumerate(seq, 1))
        literal = f"{r['Chord']}: question {r['Question']}; answer {r['Answer model']}"
        if literal not in lines:
            raise CandidateError(f"TXT_CALL_PARITY {i}")
        add("E", "call_response", 11, i, {"chord": r["Chord"], "question": question,
            "exact_echo": r["Exact echo"], "answer_model": answer,
            "passes": ["exact_echo", "new_pitches_same_rhythm", "new_register_same_contour",
                       "next_chord_same_length"]}, lines.index(literal) + 1)
        add("E", "memory_delay", 12, i, {"source_question": question,
            "delay": delayed["Required delay"], "reproduction_pitches": None,
            "answer_pitches": None})

    # F: answer pitches are given; fret locations and the claimed fourth contact are not.
    for i, r in enumerate(parsed["degree_realization"], 1):
        context, degree, pitch = r["Context"], r["Requested degree"], r["Answer pitch"]
        if degree_pc(context, degree) != PC[pitch]:
            raise CandidateError(f"REALIZATION_DEGREE {i}")
        add("F", "degree_realization", 13, i, {"context": context, "degree": degree,
            "answer_pitch": pitch, "requested_registers": ["low", "mid", "high"],
            "string_fret_locations": None, "fourth_declared_contact": None})
        events.append(event(pitch, page=13, table_name="degree_realization", row=i,
                            slot=1, role="answer_pitch", degree=degree))
    for i, r in enumerate(parsed["chord_realization"], 1):
        chord, role, spelling = r["Chord"], r["Role"], r["Pitch"]
        pitch = spelling.split(" / ")[0]
        if chord not in CHORD_ROOT or role not in ROLE_SEMITONES or (PC[CHORD_ROOT[chord]] + ROLE_SEMITONES[role]) % 12 != PC[pitch]:
            raise CandidateError(f"REALIZATION_CHORD {i}")
        add("F", "chord_tone_realization", 14, i, {"chord": chord, "role": role,
            "answer_spelling": spelling, "answer_pitch_class": PC[pitch],
            "string_sets": ["set 1", "set 2"], "string_fret_locations": None,
            "fourth_declared_contact": None})
        events.append(event(pitch, page=14, table_name="chord_realization", row=i,
                            slot=1, role="answer_pitch", degree=role))

    # G: the PDF's 24-prompt headline contains only 18 numbered prompts.
    for i, r in enumerate(parsed["reaction_ladder"], 1):
        if int(r["Stage"]) != i or r["Response limit"] not in ("4 sec", "3 sec", "2 sec"):
            raise CandidateError(f"REACTION_STAGE {i}")
        add("G", "timed_reaction_stage", 15, i, {"command_type": r["Command type"],
            "response_limit": r["Response limit"], "required_response": r["Required response"],
            "advance_accuracy": 0.90, "trial_prompts": None})
    prompts = [(int(n), s) for n, s in re.findall(r"(?m)^(\d+)\. (.+)$", pages[15])]
    if [n for n, _ in prompts] != list(range(1, 19)):
        raise CandidateError("PROMPT_DECK_PRINTED_SEQUENCE")
    derived = [
        ("C + M3", ["E"]), ("F# + m3", ["A"]), ("Bb + P5", ["F"]),
        ("E + M6", ["C#"]), ("C major degree 7", ["B"]),
        ("G major degree 3", ["B"]), ("A minor degree b6", ["F"]),
        ("A harmonic minor degree 7", ["G#"]), ("Cmaj7 third", ["E"]),
        ("G7 b7", ["F"]), ("Dm7 b3", ["F"]), ("Bm7b5 b5", ["F"]),
        ("Function of V in D", ["dominant"]),
        ("Function of ii in G", ["predominant"]),
        ("Function of vi in C", ["tonic family"]),
        ("Sing V->I roots in A", ["E", "A"]),
        ("Sing 3->7 of Cmaj7", ["E", "B"]),
        ("Sing b7->3 of G7", ["F", "B"]),
    ]
    for (number, literal), (expected_prompt, answer) in zip(prompts, derived, strict=True):
        if literal != expected_prompt:
            raise CandidateError(f"RANDOM_PROMPT_DRIFT {number}")
        add("G", "random_function_prompt", 16, number,
            {"prompt": literal, "printed_answer": None, "derived_answer": answer,
             "answer_provenance": "music_theory_inference_not_printed",
             "specific_audio_or_octave": None})

    # H: source card supplies 64 pitch names; worksheet repeats the same four-bar blocks.
    for i, r in enumerate(parsed["model_bars"], 1):
        phrase = notes(r["Four-note source"])
        if (int(r["Bar"]) != i or len(phrase) != 4 or r["Structural target"] not in phrase
                or r["Chord"] not in MODEL_CHORD_TONES
                or {PC[n] for n in phrase} != MODEL_CHORD_TONES[r["Chord"]]):
            raise CandidateError(f"MODEL_BAR {i}")
        add("H", "model_bar", 17, i, {"bar": i, "chord": r["Chord"],
            "source_pitches": phrase, "structural_target": r["Structural target"],
            "rhythm": "even_lengths_comfortable_pulse", "octaves": None,
            "source_visibility": "source_player_only"})
        events.extend(event(n, page=17, table_name="model_bars", row=i, slot=j,
                            role="source_note") for j, n in enumerate(phrase, 1))
    for block, first in enumerate((1, 5, 9, 13), 1):
        add("H", "reconstruction_block", 18, block,
            {"bars": list(range(first, first + 4)), "passes": ["contour", "degrees",
             "exact_notes", "chord_function", "play"], "expected_answers": None,
             "second_register": True, "score_range": [0, 4]})
    add("H", "unfamiliar_capstone", 19, None,
        {"bars": 16, "source_recording": None, "source_requirements": ["four_chord_qualities",
         "dominant_resolution", "repeated_motif", "syncopated_rhythm", "tonal_landmark"],
         "reconstruction_passes": 7, "score_max": 12, "mastery_min": 10,
         "required_days": 2, "score_categories": parsed["capstone_rubric"]})

    # Preserve source methods as executable task directions, rather than only in the archive.
    directions = [
        ("A", 2, "Practice: hear root -> sing interval -> play it."),
        ("A", 3, "Fretboard pass: source names only the starting note and interval."),
        ("A", 4, "After the first correct note, repeat the same pitch class in two other registers"),
        ("B", 5, "Partner plays one diatonic chord in C, G, D, A, E, or F major."),
        ("B", 6, "Second pass: source performer omits the tonic chord at the end."),
        ("C", 7, "Sing each line alone; then sing one while playing the other."),
        ("C", 7, "Transposition command: move the ii-V-I guide-tone pair through G, D, A, E, and F major."),
        ("C", 8, "Dominant test: partner plays E7 without its third."),
        ("D", 9, "Three passes: 1) U/D/S contour only."),
        ("D", 10, "Verification: clap the rhythm without pitch; sing the melody without rhythm; then recombine."),
        ("E", 11, "Pass 1: exact echo. Pass 2: same rhythm, new pitches."),
        ("E", 12, "Do not silently finger the phrase during the delay."),
        ("F", 13, "Partner names only context + degree."),
        ("F", 14, "Guide-tone priority: if response time is slow,"),
        ("G", 15, "A wrong fast response scores below a correct slower response."),
        ("G", 16, "Shuffle prompt order between sessions."),
        ("H", 18, "After the exact notes are written, sing each four-note bar once"),
        ("H", 19, "Use an unfamiliar 16-bar excerpt containing at least four chord qualities,"),
    ]
    for method_no, (module, page, phrase) in enumerate(directions, 1):
        if phrase not in pages[page - 1]:
            raise CandidateError(f"PDF_DIRECTION_MISSING {module}:{page}:{phrase}")
        add(module, "instructional_method", page, None, {"source_excerpt": phrase,
            "full_instruction_page": page})
        tasks[-1]["local_key"] += f"-m{method_no:02d}"

    total = sum(COUNTS.values())
    if total != 952 or "952" not in pages[0] or "10/12 or better on two separate days" not in pages[19]:
        raise CandidateError("PDF_WORKLOAD_OR_MASTERY")
    txt_headings = [line for line in lines if line.startswith("MODULE ")]
    if len(txt_headings) != 9 or [line.split(" - ")[0][-1] for line in txt_headings] != list("ABCCDEFGH"):
        raise CandidateError("TXT_MODULE_STRUCTURE")
    return {"schema": "fathom.detached_curriculum_source_candidate.v1", "level": 77,
            "section": "X", "wbs_owner": "2.3.1.3.1", "status": "candidate_only",
            "source_map": row, "source_pins": {"txt": {"path": str(TXT), "bytes": PINS["txt"][0],
            "sha256": PINS["txt"][1]}, "pdf": {"path": str(PDF), "bytes": PINS["pdf"][0],
            "sha256": PINS["pdf"][1]}},
            "source_archive": {"txt_lines": [{"line": i, "text": line} for i, line in enumerate(lines, 1)],
                               "pdf_pages": [{"page": i, "text": p} for i, p in enumerate(pages, 1)]},
            "pdf_tables": {name: {"page": TABLES[name][0], "rows": rows}
                           for name, rows in parsed.items()},
            "module_workload_declared": COUNTS, "declared_workload_total": total,
            "tasks": tasks, "explicit_pitch_events": events,
            "source_tensions": anomalies + [
                {"pdf_pages": [3, 4], "issue": "24 cards are labeled 96 tones and 12 transfers 48 realizations; the printed columns name two pitches per card and one root per transfer, leaving contact multiplicity unspecified",
                 "contact_multiplicity": None},
                {"pdf_page": 16, "issue": "24 prompts claimed; only numbered prompts 1-18 printed",
                 "missing_prompt_numbers": list(range(19, 25)), "resolution": "unresolved"},
                {"pdf_page": 13, "issue": "14 commands / 56 realizations, but three low/mid/high locations printed per command",
                 "fourth_contact": None},
                {"pdf_page": 14, "issue": "14 commands / 56 tones, but only a sung pitch and two string sets are labeled",
                 "contact_assignment": None},
                {"pdf_page": 10, "issue": "two-bar rhythm labels omit exact meter/onset/duration grids",
                 "timing": None},
                {"pdf_page": 11, "issue": "64 source + 64 response tones claimed; eight printed four-note questions and four-note answer models yield 64 explicit pitch names",
                 "additional_pass_realizations": None},
                {"pdf_page": 19, "issue": "unfamiliar capstone source required but no source pitches, chord chart, or recording supplied",
                 "unfamiliar_source": None}],
            "unresolved_performance_fields": ["source_audio", "octave", "string", "fret",
                "onset_q", "duration_q", "performed_response", "score", "canonical_task_id",
                "canonical_event_id"],
            "admission_claim": False}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / OUT / "level077_whole_candidate.json")
    args = parser.parse_args()
    candidate = build()
    output = args.output.resolve()
    if not output.is_relative_to((ROOT / OUT).resolve()):
        raise CandidateError("OUTPUT_OUTSIDE_P07_LEVEL77_BUILD")
    output.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(candidate, indent=2, ensure_ascii=False).encode() + b"\n"
    output.write_bytes(data)
    print(json.dumps({"output": str(output), "bytes": len(data), "sha256": sha(data),
                      "tasks": len(candidate["tasks"]), "explicit_pitch_events": len(candidate["explicit_pitch_events"]),
                      "declared_workload": candidate["declared_workload_total"]}))


if __name__ == "__main__":
    main()
