#!/usr/bin/env python3
"""Build detached whole-source Section XI Level 82 bass/chord-melody candidate."""

from __future__ import annotations

import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path
import re

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
STEM = "Guitar_Exercises_Section_XI_Level_82_Walking_Bass_Chord_Melody_Chromatic_Approach_Bass_Lines_Bass_Substitutions_and_Solo_Guitar_Arrangements"
TXT = Path("Notes/music/guitar project/TXT version") / (STEM + ".txt")
PDF = Path("Notes/music/guitar project/PDF version") / (STEM + ".pdf")
MAP = Path("Results/parallel-01/exercises/inventory/20260922T180500Z-2.3-curriculum-v1-source-inventory-evidence/curriculum-source-map.json")
OUT = Path("Build/parallel-07/2.3.1.3.1-level082-whole-r01")
PINS = {"txt": (7929, "075685fca4a69a33860abfddddac2ec47ff744c245e4c474f8c8a9715f355318"),
        "pdf": (70289, "e12a87917b2a3537922e56e0139574627a59dbd7b4959073cfbf87a4a8846005")}
COUNTS = {"A": 128, "B": 128, "C": 112, "D": 128, "E": 144,
          "F": 144, "G": 128, "H": 160, "I": 256, "J": 64}
PC = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3,
      "E": 4, "E#": 5, "F": 5, "F#": 6, "F##": 7, "Gb": 6,
      "G": 7, "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10,
      "B": 11, "B#": 0}
CHORD_PCS = {"Cmaj7": {0, 4, 7, 11}, "Am7": {9, 0, 4, 7},
             "G7": {7, 11, 2, 5}, "Fmaj7": {5, 9, 0, 4},
             "F#dim7": {6, 9, 0, 3}, "E7": {4, 8, 11, 2},
             "Dm7": {2, 5, 9, 0}, "Bm7b5": {11, 2, 5, 9},
             "G#dim7": {8, 11, 2, 5}, "AmMaj7": {9, 0, 4, 8},
             "Am6": {9, 0, 4, 6}}
HEADERS = {"C": (7, ["Type", "Harmony", "Bass", "Purpose"], 10),
           "D": (8, ["Pattern", "Instruction", "Grid / cue"], 8),
           "H1": (15, ["Bar", "Chord", "Bass", "Melody", "Function"], 16),
           "H2": (16, ["Bar", "Chord", "Bass", "Melody", "Function"], 16),
           "I1": (17, ["Bar", "Chord", "Bass", "Melody", "Job"], 16),
           "I2": (18, ["Bar", "Chord", "Bass", "Melody", "Job"], 16),
           "J": (19, ["Failure", "Immediate repair", "Restore"], 8)}


class CandidateError(ValueError):
    pass


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read(root: Path, rel: Path, pin: tuple[int, str]) -> bytes:
    path = root / rel
    if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root.resolve()):
        raise CandidateError(f"SOURCE_PATH_INVALID {rel}")
    data = path.read_bytes()
    if (len(data), sha(data)) != pin:
        raise CandidateError(f"PINNED_INPUT_DRIFT {rel}")
    return data


def source_map(root: Path) -> dict:
    row = next((r for r in json.loads((root / MAP).read_text())["rows"] if r["level"] == 82), None)
    expected = {"section": "XI", "wbs_owner": "2.3.1.3.1", "txt_path": str(TXT),
                "pdf_path": str(PDF), "txt_bytes": PINS["txt"][0],
                "pdf_bytes": PINS["pdf"][0], "txt_sha256": PINS["txt"][1],
                "pdf_sha256": PINS["pdf"][1], "pair_status": "exact_stem_pair",
                "conversion_status": "not_converted", "stable_ids_assigned": False,
                "runtime_eligible": False, "imported": False, "admitted": False}
    if row is None or any(row.get(k) != v for k, v in expected.items()):
        raise CandidateError("SOURCE_MAP_IDENTITY_OR_STATUS_DRIFT")
    return row


def notes(s: str) -> list[str]:
    result = s.split("-")
    if not result or any(n not in PC for n in result):
        raise CandidateError(f"NOTE_SEQUENCE_INVALID {s}")
    return result


def chord_bass(chord: str) -> str:
    return chord.split("/", 1)[1] if "/" in chord else re.match(r"[A-G](?:#|b)?", chord).group()


def blocks(lines: list[str], first: int, last: int) -> list[tuple[int, list[str]]]:
    result = []
    start = None
    for index in range(first, last + 1):
        if index < last and lines[index]:
            if start is None:
                start = index
        elif start is not None:
            result.append((start + 1, lines[start:index]))
            start = None
    return result


def sections(lines: list[str]) -> dict[str, list[tuple[int, list[str]]]]:
    marks = [(i, re.fullmatch(r"MODULE ([A-J]) - .+", line).group(1))
             for i, line in enumerate(lines) if re.fullmatch(r"MODULE ([A-J]) - .+", line)]
    if [letter for _, letter in marks] != list("ABCDEFGHIJ"):
        raise CandidateError("TXT_MODULE_SEQUENCE")
    end = lines.index("MASTERY")
    return {letter: blocks(lines, pos + 1,
            marks[j + 1][0] if j + 1 < len(marks) else end)
            for j, (pos, letter) in enumerate(marks)}


def pdf_table(page: str, headers: list[str], count: int, label: str) -> list[dict]:
    lines = page.splitlines()
    positions = [i for i in range(len(lines)) if lines[i:i + len(headers)] == headers]
    if len(positions) != 1:
        raise CandidateError(f"PDF_TABLE_HEADER {label}")
    width = len(headers)
    start = positions[0] + width
    cells = lines[start:start + count * width]
    if len(cells) != count * width:
        raise CandidateError(f"PDF_TABLE_LENGTH {label}")
    return [dict(zip(headers, cells[i * width:(i + 1) * width], strict=True))
            for i in range(count)]


def event(module: str, task_no: int, voice: str, ordinal: int, note: str,
          line: int, page: int | None) -> dict:
    return {"local_key": f"l82-{module.lower()}-{task_no:02d}-{voice}-{ordinal:02d}",
            "module": module, "source": {"txt_line": line, "pdf_page": page},
            "voice": voice, "slot": ordinal, "pitch_name": note, "pitch_class": PC[note],
            "octave": None, "string": None, "fret": None, "onset_q": None,
            "duration_q": None, "canonical_event_id": None, "performed_result": None}


def task(module: str, ordinal: int, kind: str, line: int, page: int | None,
         fields: dict) -> dict:
    return {"local_key": f"l82-{module.lower()}-{ordinal:02d}", "module": module,
            "kind": kind, "source": {"txt_line": line, "pdf_page": page},
            "fields": fields, "canonical_task_id": None, "observed_score": None,
            "observed_performance": None}


def line_ref(lines: list[str], literal: str, start: int = 0) -> int:
    positions = [i for i in range(start, len(lines)) if lines[i] == literal]
    if not positions:
        raise CandidateError(f"TXT_LINE_MISSING {literal}")
    return positions[0] + 1


def build(root: Path = ROOT) -> dict:
    txt_data = read(root, TXT, PINS["txt"])
    pdf_data = read(root, PDF, PINS["pdf"])
    inventory = source_map(root)
    lines = txt_data.decode().splitlines()
    pages = [page.extract_text() or "" for page in PdfReader(BytesIO(pdf_data)).pages]
    if len(lines) != 355 or len(pages) != 20 or any(
        "Section XI, Level 82" not in p.splitlines()[0] for p in pages):
        raise CandidateError("SOURCE_LINE_PAGE_BOUNDARY")
    grouped = sections(lines)
    tabled = {name: pdf_table(pages[p - 1], headers, count, name)
              for name, (p, headers, count) in HEADERS.items()}
    tasks = []
    events = []

    # A: the TXT has eight studies; PDF pages 3-4 print only studies 1-4.
    if len(grouped["A"]) != 8:
        raise CandidateError("MODULE_A_STUDY_COUNT")
    for i, (start, b) in enumerate(grouped["A"], 1):
        if len(b) != 4:
            raise CandidateError(f"MODULE_A_STUDY_WIDTH {i}")
        title, bass_s, harmony_s, melody_s = b
        bass, melody, harmony = notes(bass_s), notes(melody_s), harmony_s.split(" | ")
        if len(bass) != len(melody) or len(bass) != len(harmony):
            raise CandidateError(f"MODULE_A_VOICE_WIDTH {i}")
        for j, (n, chord) in enumerate(zip(bass, harmony, strict=True), 1):
            if PC[chord_bass(chord)] != PC[n]:
                raise CandidateError(f"MODULE_A_HARMONY_BASS {i}:{j}")
        page = 3 if i <= 2 else 4 if i <= 4 else None
        if page is not None:
            for pdf_literal in (title, "Bass:    " + bass_s, "Harmony: " + harmony_s,
                                "Melody:  " + melody_s):
                if pdf_literal not in pages[page - 1]:
                    raise CandidateError(f"PDF_A_PARITY {i}:{pdf_literal}")
        tasks.append(task("A", i, "walking_bass_chord_melody_study", start, page,
            {"title": title, "bass": bass, "harmony": harmony, "melody": melody,
             "pdf_status": "exact_printed_study" if page else "txt_only_study",
             "passes": ["bass_quarters", "melody_only", "outer_voices",
                        "guide_tones_beats_1_3", "full_texture"] if page else None,
             "fretboard_locations": None, "timing_grid": None}))
        events.extend(event("A", i, "bass", j, n, start + 1, page)
                      for j, n in enumerate(bass, 1))
        events.extend(event("A", i, "melody", j, n, start + 3, page)
                      for j, n in enumerate(melody, 1))

    # B: six eight-note approaches and two four-note enclosures.
    if len(grouped["B"]) != 8:
        raise CandidateError("MODULE_B_STUDY_COUNT")
    for i, (start, b) in enumerate(grouped["B"], 1):
        if len(b) != 4:
            raise CandidateError(f"MODULE_B_STUDY_WIDTH {i}")
        name, bass_s, target_s, direction = b
        bass = notes(bass_s)
        page = 5 if i <= 4 else 6
        if len(bass) != (8 if i <= 6 else 4) or not target_s.startswith("Target "):
            raise CandidateError(f"MODULE_B_BASS_WIDTH {i}")
        if PC[bass[-1]] != PC[chord_bass(target_s[7:].split(" / ")[0])]:
            raise CandidateError(f"MODULE_B_DESTINATION {i}")
        if name not in pages[page - 1] or "Bass:   " + bass_s not in pages[page - 1] or target_s not in pages[page - 1]:
            raise CandidateError(f"PDF_B_PARITY {i}")
        tasks.append(task("B", i, "chromatic_approach_or_enclosure", start, page,
            {"name": name, "bass": bass, "target": target_s[7:],
             "upper_voice_direction": direction,
             "destination_on_beat_1": True, "exact_onsets": None}))
        events.extend(event("B", i, "bass", j, n, start + 1, page)
                      for j, n in enumerate(bass, 1))

    # C and D: exact PDF tables, including the printable cue masks.
    for module, kind in (("C", "bass_substitution"), ("D", "independence_pattern")):
        if len(grouped[module]) != len(tabled[module]):
            raise CandidateError(f"MODULE_{module}_ROW_COUNT")
        for i, ((start, b), pdf_row) in enumerate(zip(grouped[module], tabled[module], strict=True), 1):
            if b != list(pdf_row.values()):
                raise CandidateError(f"PDF_{module}_ROW_PARITY {i}")
            fields = pdf_row.copy()
            if module == "C":
                bass = [part.strip() for part in pdf_row["Bass"].split(" -> ")]
                if any(n not in PC for n in bass):
                    raise CandidateError(f"MODULE_C_BASS {i}")
                fields["bass_notes"] = bass
                events.extend(event("C", i, "bass", j, n, start + 2, 7)
                              for j, n in enumerate(bass, 1))
            else:
                fields["exact_onsets"] = None
                fields["exact_durations"] = None
                fields["contexts"] = ["Cmaj7", "Am7", "Dm7", "G7"]
            tasks.append(task(module, i, kind, start, HEADERS[module][0], fields))

    # E/F: six four-bar cadences each, with each bar's first bass note matching its chord root.
    for module, page_start, kind in (("E", 9, "major_ii_v_i_walk"),
                                     ("F", 11, "minor_ii_halfdim_v_i_walk")):
        if len(grouped[module]) != 6:
            raise CandidateError(f"MODULE_{module}_STUDY_COUNT")
        for i, (start, b) in enumerate(grouped[module], 1):
            if len(b) != 4:
                raise CandidateError(f"MODULE_{module}_WIDTH {i}")
            context, chords_s, bass_s, top_s = b
            chords = chords_s.split(" | ")
            bars = [part.strip() for part in bass_s.split(" | ")]
            bass = [notes(part) if not part.endswith("---") else [part[:-3]] for part in bars]
            top = notes(top_s)
            page = page_start + (i - 1) // 3
            if len(chords) != 4 or len(bass) != 4 or len(top) != 4 or [len(x) for x in bass] != [4, 4, 4, 1]:
                raise CandidateError(f"MODULE_{module}_BAR_WIDTH {i}")
            if any(PC[bar[0]] != PC[chord_bass(chord)] for bar, chord in zip(bass, chords, strict=True)):
                raise CandidateError(f"MODULE_{module}_BASS_ROOT {i}")
            for snippet in (context, "Harmony: " + chords_s, "Bass:    " + bass_s,
                            "Top line: " + top_s):
                if snippet not in pages[page - 1]:
                    raise CandidateError(f"PDF_{module}_PARITY {i}")
            tasks.append(task(module, i, kind, start, page,
                {"context": context, "harmony": chords, "bass_bars": bass,
                 "top_line": top, "bass_note_count": sum(map(len, bass)),
                 "top_note_count": len(top), "exact_onsets": None,
                 "fretboard_locations": None}))
            bass_line = start + 2
            k = 0
            for bar in bass:
                for n in bar:
                    k += 1
                    events.append(event(module, i, "bass", k, n, bass_line, page))
            events.extend(event(module, i, "melody", j, n, start + 3, page)
                          for j, n in enumerate(top, 1))

    # G: all six transfer contexts; the bass line and top contour are independently retained.
    if len(grouped["G"]) != 6:
        raise CandidateError("MODULE_G_STUDY_COUNT")
    for i, (start, b) in enumerate(grouped["G"], 1):
        if len(b) != 4 or not b[2].startswith("bass: "):
            raise CandidateError(f"MODULE_G_WIDTH {i}")
        context, melody_s, bass_line, chord_line = b
        melody, bass = notes(melody_s), notes(bass_line[6:])
        chords = chord_line.split("-")
        page = 13 if i <= 3 else 14
        if len(melody) != 8 or len(bass) != 9 or len(chords) != 5:
            raise CandidateError(f"MODULE_G_VOICE_WIDTH {i}")
        if any(snippet not in pages[page - 1] for snippet in
               (context, "Melody: " + melody_s, bass_line, "Harmony: " + chord_line)):
            raise CandidateError(f"PDF_G_PARITY {i}")
        tasks.append(task("G", i, "key_transfer_outer_voices", start, page,
            {"context": context, "melody": melody, "bass": bass,
             "harmony": chords, "shells_added_after_outer_voice_independence": True,
             "bass_melody_alignment": None}))
        events.extend(event("G", i, "melody", j, n, start + 1, page)
                      for j, n in enumerate(melody, 1))
        events.extend(event("G", i, "bass", j, n, start + 2, page)
                      for j, n in enumerate(bass, 1))

    # H/I: the capstone reproduces both arrangements. Preserve each occurrence and prove parity.
    h_blocks = grouped["H"]
    if len(h_blocks) != 2 or [b[0] for _, b in h_blocks] != ["Arrangement 1:", "Arrangement 2:"]:
        raise CandidateError("MODULE_H_ARRANGEMENT_STRUCTURE")
    arrangements = []
    for arrangement, (start, b) in enumerate(h_blocks, 1):
        if len(b) != 17:
            raise CandidateError(f"MODULE_H_BAR_COUNT {arrangement}")
        rows = []
        for local_bar, literal in enumerate(b[1:], 1):
            fields = [part.strip() for part in literal.split("|")]
            if len(fields) != 5 or int(fields[0]) != local_bar:
                raise CandidateError(f"MODULE_H_BAR_FORMAT {arrangement}:{local_bar}")
            pdf_row = tabled[f"H{arrangement}"][local_bar - 1]
            if fields != list(pdf_row.values()):
                raise CandidateError(f"PDF_H_PARITY {arrangement}:{local_bar}")
            chord, bass, melody = fields[1:4]
            if PC[chord_bass(chord)] != PC[bass] or (chord.split("/")[0] in CHORD_PCS and
                  PC[melody] not in CHORD_PCS[chord.split("/")[0]]):
                raise CandidateError(f"MODULE_H_MUSIC {arrangement}:{local_bar}")
            line = start + local_bar
            ordinal = (arrangement - 1) * 16 + local_bar
            data = {"bar": ordinal, "local_bar": local_bar, "arrangement": arrangement,
                    "chord": chord, "bass": bass, "melody": melody,
                    "function": fields[4], "other_chord_tones": None,
                    "fretboard_locations": None, "timing": None}
            rows.append(data)
            tasks.append(task("H", ordinal, "arrangement_bar", line,
                              14 + arrangement, data))
            events.extend((event("H", ordinal, "bass", 1, bass, line, 14 + arrangement),
                           event("H", ordinal, "melody", 1, melody, line, 14 + arrangement)))
        arrangements.extend(rows)
    if len(grouped["I"]) != 1 or len(grouped["I"][0][1]) != 32:
        raise CandidateError("MODULE_I_CAPSTONE_WIDTH")
    i_start, i_rows = grouped["I"][0]
    for bar, (literal, source_row) in enumerate(zip(i_rows, arrangements, strict=True), 1):
        m = re.fullmatch(r"(\d\d): (.+) \| ([A-G#b]+) \| ([A-G#b]+) \| (.+)", literal)
        if not m or int(m[1]) != bar or [m[2], m[3], m[4], m[5]] != [
                source_row["chord"], source_row["bass"], source_row["melody"],
                source_row["function"]]:
            raise CandidateError(f"TXT_I_H_PARITY {bar}")
        half, local_bar = (1, bar) if bar <= 16 else (2, bar - 16)
        pdf_row = tabled[f"I{half}"][local_bar - 1]
        if [pdf_row[k] for k in ("Bar", "Chord", "Bass", "Melody", "Job")] != [
                str(local_bar), m[2], m[3], m[4], m[5]]:
            raise CandidateError(f"PDF_I_PARITY {bar}")
        line = i_start + bar - 1
        tasks.append(task("I", bar, "capstone_bar", line, 16 + half,
            {"bar": bar, "source_arrangement_bar": source_row["bar"],
             "chord": m[2], "bass": m[3], "melody": m[4], "job": m[5],
             "other_chord_tones": None, "timing": None}))
        events.extend((event("I", bar, "bass", 1, m[3], line, 16 + half),
                       event("I", bar, "melody", 1, m[4], line, 16 + half)))

    # J: source and PDF agree on eight distinct no-restart repair actions.
    if len(grouped["J"]) != 1 or len(grouped["J"][0][1]) != 8:
        raise CandidateError("MODULE_J_RECOVERY_COUNT")
    j_start, repairs = grouped["J"][0]
    for i, (literal, pdf_row) in enumerate(zip(repairs, tabled["J"], strict=True), 1):
        fields = [part.strip() for part in literal.split(" | ")]
        if fields != list(pdf_row.values()):
            raise CandidateError(f"PDF_J_PARITY {i}")
        tasks.append(task("J", i, "no_restart_repair", j_start + i - 1, 19,
                          pdf_row | {"trigger_bar": None, "performed_recovery": None}))

    # Page-level instructions become method tasks even when they do not name notes.
    methods = [
        ("A", 3, "Pass 1: bass quarter notes. Pass 2: melody only."),
        ("B", 5, "Chromatic limit: use one approach device per destination"),
        ("C", 7, "Verification: play the upper chord without bass"),
        ("D", 8, "Practice each pattern on Cmaj7, Am7, Dm7, and G7."),
        ("E", 9, "Play one guide tone per bar first."),
        ("F", 11, "The bass may chromatically approach V"),
        ("G", 13, "Sing both outer voices separately."),
        ("H", 15, "Performance ladder: bass only -> melody only -> outer voices"),
        ("I", 18, "End the capstone on Am6, not with another turnaround."),
        ("J", 19, "Intentionally miss one bass approach in every eight-bar run."),
    ]
    for i, (module, page, excerpt) in enumerate(methods, 1):
        if excerpt not in pages[page - 1]:
            raise CandidateError(f"PDF_METHOD_MISSING {module}:{page}")
        tasks.append(task(module, 90 + i, "instructional_method", None, page,
                          {"source_excerpt": excerpt, "full_instruction_page": page}))

    if sum(COUNTS.values()) != 1392 or "1,392 EVENTS" not in pages[0] or \
            "14/16 or better on two separate days" not in pages[19]:
        raise CandidateError("PDF_WORKLOAD_OR_MASTERY")
    printed_pitch_counts = {module: sum(e["module"] == module for e in events)
                            for module in COUNTS}
    return {"schema": "fathom.detached_curriculum_source_candidate.v1", "level": 82,
            "section": "XI", "wbs_owner": "2.3.1.3.1", "status": "candidate_only",
            "source_map": inventory,
            "source_pins": {"txt": {"path": str(TXT), "bytes": PINS["txt"][0],
                            "sha256": PINS["txt"][1]},
                            "pdf": {"path": str(PDF), "bytes": PINS["pdf"][0],
                            "sha256": PINS["pdf"][1]}},
            "source_archive": {"txt_lines": [{"line": i, "text": line}
                                             for i, line in enumerate(lines, 1)],
                               "pdf_pages": [{"page": i, "text": p}
                                             for i, p in enumerate(pages, 1)]},
            "pdf_tables": {name: {"page": HEADERS[name][0], "rows": rows}
                           for name, rows in tabled.items()},
            "module_workload_declared": COUNTS, "declared_workload_total": 1392,
            "module_count_comparison": {module: {"declared_events": count,
                "printed_pitch_entries": printed_pitch_counts[module],
                "difference_not_assignable_to_specific_contacts": count - printed_pitch_counts[module]}
                for module, count in COUNTS.items()},
            "tasks": tasks, "explicit_pitch_events": events,
            "source_tensions": [
                {"module": "A", "issue": "TXT lists eight studies; PDF pages 3-4 print only studies 1-4",
                 "txt_studies": 8, "pdf_studies": 4, "resolution": "retain all; latter four TXT-only"},
                {"module": "A", "issue": "PDF declares 128 events for four printed studies; exact voice contacts and pass multiplication are unspecified",
                 "declared_events": 128},
                {"module": "D", "issue": "pattern cues describe syncopation but give no complete note pitches or onset/duration grid",
                 "exact_timing": None},
                {"module": "H", "issue": "80 events per arrangement claimed; one bass and one melody note per bar are structurally printed",
                 "additional_contacts": None},
                {"module": "I", "issue": "256 capstone events claimed; 32 bars repeat H structural bass/melody targets without full voicings or timing",
                 "additional_contacts": None}],
            "unresolved_performance_fields": ["octave", "string", "fret", "onset_q",
                "duration_q", "inner_chord_voicing", "performed_result", "score",
                "canonical_task_id", "canonical_event_id"],
            "admission_claim": False}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path,
                        default=ROOT / OUT / "level082_whole_candidate.json")
    args = parser.parse_args()
    candidate = build()
    output = args.output.resolve()
    if not output.is_relative_to((ROOT / OUT).resolve()):
        raise CandidateError("OUTPUT_OUTSIDE_P07_LEVEL82_BUILD")
    output.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(candidate, indent=2, ensure_ascii=False).encode() + b"\n"
    output.write_bytes(data)
    print(json.dumps({"output": str(output), "bytes": len(data), "sha256": sha(data),
                      "tasks": len(candidate["tasks"]),
                      "explicit_pitch_events": len(candidate["explicit_pitch_events"]),
                      "declared_workload": candidate["declared_workload_total"]}))


if __name__ == "__main__":
    main()
