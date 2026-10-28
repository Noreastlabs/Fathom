#!/usr/bin/env python3
"""Build a detached, source-pinned whole-Level-81 task/event candidate."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
STEM = "Guitar_Exercises_Section_XI_Level_81_Moving_Inner_Voices_Pedal_Tones_Walking_Bass_Passing_Diminished_and_Drop_2_Drop_3_Voicings"
TXT = Path("Notes/music/guitar project/TXT version") / f"{STEM}.txt"
PDF = Path("Notes/music/guitar project/PDF version") / f"{STEM}.pdf"
MAP = Path("Results/parallel-01/exercises/inventory/20260922T180500Z-2.3-curriculum-v1-source-inventory-evidence/curriculum-source-map.tsv")
CATALOG = Path("Content/controls/curriculum-v1/package.json")
BUILD = Path("Build/parallel-08/2.3.1.3.1-level081-whole-r01")
PINS = {"txt": (8206, "62178bd2edae899efc36cc5bff76c589660b66a45d99476e4efc73a66a29b9b6"),
        "pdf": (48135, "025e2c01ee637555544a64adf0b7a196b8bc1ca04f08bb61dd4cf7c6d479686d"),
        "map": (68536, "f526ff4d9ce3bceaf9a7cc581a3ac2aee2c74917eba984dd57913adba574c123"),
        "catalog": (24698658, "766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255")}
COUNTS = {"A": 96, "B": 96, "C": 128, "D": 96, "E": 128,
          "F": 96, "G": 128, "H": 160, "I": 192, "J": 64}
NOTE_RE = re.compile(r"[A-G](?:#|b)?")
PITCH = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3,
         "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8,
         "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11}
OPEN = [4, 9, 2, 7, 11, 4]  # low E, A, D, G, B, high e
CHORD = {"Cmaj7": {0, 4, 7, 11}, "Cmaj7/B": {0, 4, 7, 11},
         "Cm7": {0, 3, 7, 10}, "C7": {0, 4, 7, 10}, "Cm7b5": {0, 3, 6, 10},
         "C#dim7": {1, 4, 7, 10}, "Dm7": {2, 5, 9, 0}, "Dm7/F": {2, 5, 9, 0},
         "D#dim7": {3, 6, 9, 0}, "Edim7": {4, 7, 10, 1}, "Em7": {4, 7, 11, 2},
         "E7": {4, 8, 11, 2}, "Fmaj7": {5, 9, 0, 4}, "F#dim7": {6, 9, 0, 3},
         "G7": {7, 11, 2, 5}, "G#dim7": {8, 11, 2, 5}, "Am7": {9, 0, 4, 7},
         "Am": {9, 0, 4}, "AmMaj7": {9, 0, 4, 8}, "A7": {9, 1, 4, 7},
         "A#dim7": {10, 1, 4, 7}, "Bm7b5": {11, 2, 5, 9}, "Dm": {2, 5, 9}}


class CandidateError(ValueError):
    pass


def need(ok: bool, code: str, detail: object = "") -> None:
    if not ok:
        raise CandidateError(f"{code}: {detail}")


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def pinned(root: Path, path: Path, key: str) -> bytes:
    raw = (root / path).read_bytes()
    need((len(raw), sha(raw)) == PINS[key], "PINNED_SOURCE_DRIFT", path)
    return raw


def compact(text: str) -> str:
    return " ".join(text.split())


def page_contains(page: str, snippet: str, context: str) -> None:
    need(compact(snippet) in compact(page), "PDF_SOURCE_DRIFT", (context, snippet))


def read_sources(root: Path) -> tuple[list[str], list[str], dict, dict, dict]:
    raw = {key: pinned(root, path, key) for key, path in
           (("txt", TXT), ("pdf", PDF), ("map", MAP), ("catalog", CATALOG))}
    lines = raw["txt"].decode("utf-8").splitlines()
    need(len(lines) == 158 and lines[0] == "Guitar Exercises - Section XI, Level 81", "TXT_HEADER")
    pages = [(page.extract_text() or "").strip() for page in PdfReader(io.BytesIO(raw["pdf"])).pages]
    need(len(pages) == 20 and all("Level 81" in page for page in pages), "PDF_PAGES")
    rows = list(csv.DictReader(io.StringIO(raw["map"].decode("utf-8")), delimiter="\t"))
    match = [row for row in rows if row.get("level") == "81"]
    need(len(match) == 1, "SOURCE_MAP_ROW")
    row = match[0]
    need(row["section"] == "XI" and row["wbs_owner"] == "2.3.1.3.1" and
         row["txt_path"] == str(TXT) and row["pdf_path"] == str(PDF) and
         row["txt_sha256"] == PINS["txt"][1] and row["pdf_sha256"] == PINS["pdf"][1] and
         row["pair_status"] == "exact_stem_pair" and row["review"] == "Pending" and
         row["conversion_status"] == "not_converted" and
         all(row[field] == "False" for field in ("stable_ids_assigned", "runtime_eligible", "imported", "admitted")),
         "SOURCE_MAP_STATUS", row)
    package = json.loads(raw["catalog"])
    wc = package["workbook_catalog"]
    need(len(wc["entries"]) == len(wc["inventory_bindings"]) == 105, "FROZEN_CATALOG_SCOPE")
    entry, binding = wc["entries"][80], wc["inventory_bindings"][80]
    need(binding["level"] == 81 and binding["workbook_id"] == entry["workbook_id"] == "fg:workbook:000081"
         and binding["section"] == "XI" and binding["wbs_owner"] == "2.3.1.3.1"
         and binding["txt_sha256"] == PINS["txt"][1] and binding["pdf_sha256"] == PINS["pdf"][1]
         and entry["catalog_role"] == "read_only_source_preservation"
         and entry["conversion_status"] == "not_converted" and entry["review"] == "Pending"
         and not any(entry[field] for field in ("runtime_eligible", "runtime_admitted", "imported", "admitted", "whole_workbook_complete"))
         and entry["playable_projection"]["status"] == "explicitly_empty_unresolved", "FROZEN_CATALOG_STATUS")
    need(entry["txt"]["sha256"] == PINS["txt"][1] and entry["pdf"]["sha256"] == PINS["pdf"][1],
         "FROZEN_CATALOG_SOURCE")
    source = {label: {"path": str(path), "bytes": PINS[key][0], "sha256": PINS[key][1]}
              for label, key, path in (("txt", "txt", TXT), ("pdf", "pdf", PDF),
                                       ("source_map", "map", MAP), ("frozen_catalog", "catalog", CATALOG))}
    source["txt"]["lines"] = len(lines)
    source["pdf"]["pages"] = len(pages)
    catalog_context = {"workbook_id": entry["workbook_id"], "catalog_role": entry["catalog_role"],
                       "conversion_status": entry["conversion_status"], "review": entry["review"],
                       "whole_workbook_complete": entry["whole_workbook_complete"],
                       "playable_projection_status": entry["playable_projection"]["status"],
                       "unresolved_playable_fields": entry["unresolved_playable_fields"],
                       "inventory_binding": binding}
    return lines, pages, row, source, catalog_context


def sections(lines: list[str]) -> dict[str, tuple[int, int]]:
    heads = {key: next(i for i, line in enumerate(lines) if line.startswith(f"MODULE {key} -"))
             for key in COUNTS}
    positions = list(heads.values())
    need(positions == sorted(positions), "MODULE_ORDER")
    return {key: (at, positions[n + 1] if n < 9 else
                  next(i for i, line in enumerate(lines) if line == "MASTERY"))
            for n, (key, at) in enumerate(heads.items())}


def module_lines(lines: list[str], bound: tuple[int, int]) -> list[tuple[int, str]]:
    return [(i + 1, lines[i]) for i in range(bound[0] + 1, bound[1]) if lines[i].strip()]


def pitch_tokens(text: str) -> list[str]:
    return NOTE_RE.findall(text)


def split_note_route(text: str) -> list[str]:
    return [part for part in re.split(r"-|->|\s+", text) if part in PITCH]


def voicing(shape: str) -> dict:
    frets = shape.split()
    need(len(frets) == 6 and all(f == "x" or re.fullmatch(r"\d+", f) for f in frets),
         "VOICING_SHAPE", shape)
    pitch_classes = [(open_pitch + int(fret)) % 12 for open_pitch, fret in zip(OPEN, frets) if fret != "x"]
    return {"frets_low_to_high": [None if fret == "x" else int(fret) for fret in frets],
            "pitch_classes_low_to_high": pitch_classes, "sounding_strings": len(pitch_classes)}


def parse_a(lines: list[str], pages: list[str], bound: tuple[int, int]) -> list[dict]:
    tasks = []
    expected = [("Cmaj7", ["B", "C", "B", "A"], ["7", "R", "7", "6"], "C"),
                ("Am7", ["G", "G#", "A", "G"], ["b7", "7", "R", "b7"], "A"),
                ("Dm7", ["C", "C#", "D", "C"], ["b7", "7", "R", "b7"], "D"),
                ("G7", ["F", "F#", "G", "F"], ["b7", "7", "R", "b7"], "G"),
                ("Cmaj7 -> A7", ["B", "Bb", "A", "G#"], ["7", "b7", "6", "#5"], "C -> A"),
                ("Dm7 -> G7", ["C", "B", "Bb", "B"], ["b7", "3", "b3", "3"], "D -> G")]
    rows = module_lines(lines, bound)
    need(len(rows) == 6, "A_STUDY_COUNT")
    for n, ((line_no, line), (harmony, notes, degrees, bass)) in enumerate(zip(rows, expected), 1):
        match = re.fullmatch(r"(.+?): line ([A-G#b-]+); degrees ([#b0-9R-]+); (.+?) bass; (.+)\.", line)
        need(match is not None, "A_STUDY_FORMAT", line_no)
        need(match[1] == harmony and match[2].split("-") == notes and
             match[3].split("-") == degrees and match[4] == bass, "A_MUSICAL_RELATION", line_no)
        page_no = 3 if n <= 3 else 4
        for snippet in (f"{harmony} - inner line {match[2]}", f"Degrees: {match[3]}", f"Bass:    {bass} bass", match[5]):
            page_contains(pages[page_no - 1], snippet, f"A{n}")
        tasks.append({"task": f"A{n}", "source_txt_lines": [line_no], "source_pdf_pages": [page_no],
                      "harmony": harmony, "inner_line": notes, "degrees_as_printed": degrees,
                      "bass_role": bass, "musical_direction": match[5],
                      "printed_event_allocation": 16, "source_anchors": 4,
                      "unresolved": ["remaining_twelve_event_pitches_and_voice_allocation_not_printed"]})
    return tasks


def parse_b(lines: list[str], pages: list[str], bound: tuple[int, int]) -> list[dict]:
    rows = module_lines(lines, bound)
    need(len(rows) == 6, "B_STUDY_COUNT")
    tasks = []
    expected_functions = ["E = 3,5,7,root", "G = 5,b3,b7,root", "C = b3,5,b7,11",
                          "upper harmony changes above fixed tonic", "hear 1,5,3,11 over changing upper structure",
                          "retain one middle voice while outer voices move"]
    for n, ((line_no, line), function) in enumerate(zip(rows, expected_functions), 1):
        match = re.fullmatch(r"(High|Bass|Inner) ([A-G]) pedal: harmony (.+); pedal ([A-G-]+); functions (.+)\.", line)
        need(match is not None, "B_STUDY_FORMAT", line_no)
        placement, pitch, harmony, pedals, printed_function = match.groups()
        chords = [item.strip() for item in harmony.split(" | ")]
        pedal_notes = pedals.split("-")
        need(len(chords) == len(pedal_notes) == 4 and pedal_notes == [pitch] * 4 and
             printed_function == function, "B_PEDAL_RELATION", line_no)
        page_no = 5 if n <= 3 else 6
        for snippet in (f"{placement} {pitch} pedal", f"Harmony: {harmony}", f"Pedal:   {pedals}",
                        f"Function:{function}"):
            page_contains(pages[page_no - 1], snippet, f"B{n}")
        tasks.append({"task": f"B{n}", "source_txt_lines": [line_no], "source_pdf_pages": [page_no],
                      "pedal_placement": placement.lower(), "pedal_pitch": pitch,
                      "harmonic_route": chords, "pedal_functions_as_printed": function,
                      "printed_event_allocation": 16, "source_anchors": 4,
                      "unresolved": ["hold_vs_rearticulate_option_and_other_voice_events_not_fully_notated"]})
    return tasks


def parse_c(lines: list[str], pages: list[str], bound: tuple[int, int]) -> list[dict]:
    rows = module_lines(lines, bound)
    need(len(rows) == 8, "C_STUDY_COUNT")
    tasks = []
    for n, (line_no, line) in enumerate(rows, 1):
        match = re.fullmatch(r"(.+?): bass ([^;]+); harmony (.+)\.", line)
        need(match is not None, "C_STUDY_FORMAT", line_no)
        label, bass, harmony = match.groups()
        bass_route = split_note_route(bass)
        need(4 <= len(bass_route) <= 6, "C_BASS_ROUTE", (line_no, bass_route))
        page_no = 7 if n <= 4 else 8
        for snippet in (label, f"Bass: {bass}", f"Harmony: {harmony}"):
            page_contains(pages[page_no - 1], snippet, f"C{n}")
        tasks.append({"task": f"C{n}", "source_txt_lines": [line_no], "source_pdf_pages": [page_no],
                      "label": label, "bass_route": bass_route, "harmonic_route_as_printed": harmony,
                      "printed_event_allocation": 16, "source_anchors": len(bass_route),
                      "unresolved": ["melody_guide_tone_and_contact_timing_not_printed"]})
    return tasks


def parse_d(lines: list[str], pages: list[str], bound: tuple[int, int]) -> list[dict]:
    rows = module_lines(lines, bound)
    need(len(rows) == 8, "D_CELL_COUNT")
    tasks = []
    for n, (line_no, line) in enumerate(rows, 1):
        parts = line.split(" | ")
        need(len(parts) == 5, "D_ROUTE_FORMAT", line_no)
        names = parts[0].split(" -> ")
        need(len(names) == 3 and all(name in CHORD for name in names), "D_CHORD_NAMES", names)
        shapes = []
        for label, text, chord in zip(("source", "diminished", "destination"), parts[1:4], names):
            need(text.startswith(label + " "), "D_VOICING_LABEL", line_no)
            grip = voicing(text[len(label) + 1:])
            need(set(grip["pitch_classes_low_to_high"]).issubset(CHORD[chord]) and
                 len(grip["pitch_classes_low_to_high"]) >= 4,
                 "D_CHORD_PITCH_SET", (line_no, label, chord, grip))
            shapes.append({"role": label, "chord": chord, **grip})
        need(parts[4].startswith("top idea "), "D_TOP_IDEA", line_no)
        top_idea = parts[4][len("top idea "):]
        need(all(token in PITCH for token in top_idea.split("/")), "D_TOP_PITCH", line_no)
        page = pages[8]
        for snippet in (parts[0], *(part.split(" ", 1)[1] for part in parts[1:4]), top_idea):
            page_contains(page, snippet, f"D{n}")
        tasks.append({"task": f"D{n}", "source_txt_lines": [line_no], "source_pdf_pages": [9],
                      "harmonic_route": names, "voicings": shapes, "top_line_idea": top_idea.split("/"),
                      "printed_event_allocation": 12, "source_anchors": sum(x["sounding_strings"] for x in shapes),
                      "unresolved": ["top_line_idea_is_separate_from_printed_grip",
                                     "twelve_event_play_order_and_timing_not_printed"]})
    return tasks


def parse_e_f(lines: list[str], pages: list[str], bound: tuple[int, int], key: str) -> list[dict]:
    rows = module_lines(lines, bound)
    expected = 8 if key == "E" else 6
    need(len(rows) == expected, f"{key}_VOICING_COUNT")
    tasks = []
    page_no = 10 if key == "E" else 11
    for n, (line_no, line) in enumerate(rows, 1):
        name, payload = line.split(": ", 1)
        need(name in CHORD, f"{key}_CHORD_NAME", line_no)
        parts = payload.split(" | ")
        need(len(parts) == 3, f"{key}_VOICING_FORMAT", line_no)
        shape, note_text, degree_text = parts
        grip = voicing(shape)
        spellings = note_text.split("-")
        degrees = degree_text.split("-")
        need(len(spellings) == len(degrees) == grip["sounding_strings"] == 4 and
             set(PITCH[pitch] for pitch in spellings) == set(grip["pitch_classes_low_to_high"]) == CHORD[name],
             f"{key}_FRET_PITCH_DEGREE", (line_no, name))
        by_class = {PITCH[pitch]: (pitch, degree) for pitch, degree in zip(spellings, degrees)}
        actual = [by_class[pc] for pc in grip["pitch_classes_low_to_high"]]
        source_order_differs = [pitch for pitch, _ in actual] != spellings
        need(not source_order_differs or (key == "F" and name in ("Cmaj7", "Cm7", "Dm7")),
             f"{key}_UNEXPECTED_PITCH_ORDER", (line_no, name))
        for snippet in (name, shape, note_text, degree_text):
            page_contains(pages[page_no - 1], snippet, f"{key}{n}")
        tasks.append({"task": f"{key}{n}", "source_txt_lines": [line_no], "source_pdf_pages": [page_no],
                      "chord": name, "voicing": grip, "notes_low_to_high": spellings,
                      "degrees_low_to_high": degrees,
                      "actual_fretboard_notes_low_to_high": [pitch for pitch, _ in actual],
                      "actual_fretboard_degrees_low_to_high": [degree for _, degree in actual],
                      "source_pitch_order_differs_from_fretboard": source_order_differs,
                      "printed_event_allocation": 16,
                      "source_anchors": 4,
                      "unresolved": ["drill_passes_and_exact_sixteen_event_order_not_fully_notated"]})
    return tasks


def parse_g(lines: list[str], pages: list[str], bound: tuple[int, int]) -> list[dict]:
    rows = module_lines(lines, bound)
    need(len(rows) == 8, "G_STUDY_COUNT")
    tasks = []
    for n, (line_no, line) in enumerate(rows, 1):
        label, payload = line.split(": ", 1)
        parts = payload.split("; ")
        need(2 <= len(parts) <= 3, "G_RELATION_FORMAT", line_no)
        page_no = 12 if n <= 4 else 13
        page_contains(pages[page_no - 1], label, f"G{n}")
        for part in parts:
            page_contains(pages[page_no - 1], part.rstrip("."), f"G{n}")
        tasks.append({"task": f"G{n}", "source_txt_lines": [line_no], "source_pdf_pages": [page_no],
                      "integration_pattern": label, "voice_and_harmony_relationships": parts,
                      "printed_event_allocation": 16,
                      "unresolved": ["exact_voice_event_sequence_and_timing_not_printed"]})
    return tasks


def parse_h(lines: list[str], pages: list[str], bound: tuple[int, int]) -> list[dict]:
    block = module_lines(lines, bound)
    headings = [(i, no, text) for i, (no, text) in enumerate(block) if text.startswith("Arrangement ")]
    need(len(headings) == 4, "H_ARRANGEMENT_COUNT")
    tasks = []
    for n, (at, line_no, title) in enumerate(headings, 1):
        end = headings[n][0] if n < 4 else len(block)
        detail = block[at + 1:end]
        chord_rows = [text for _, text in detail if text.startswith("|")]
        need(len(chord_rows) == 2, "H_HARMONY_ROWS", n)
        harmony = [name.strip() for row in chord_rows for name in row.strip("|").split("|")]
        need(len(harmony) == 8 and all(harmony), "H_EIGHT_BARS", n)
        melody_row = next((text for _, text in detail if text.startswith("Melody:")), None)
        target_row = next((text for _, text in detail if text.startswith("Melody targets:")), None)
        bass_row = next((text for _, text in detail if text.startswith("Bass:")), None)
        texture_row = next((text for _, text in detail if text.startswith("Texture:")), None)
        need((melody_row is not None) == (n <= 3), "H_MELODY_FORM", n)
        if melody_row:
            melody = [pitch_tokens(pair) for pair in melody_row.split(":", 1)[1].split("|")]
            need(len(melody) == 8 and all(len(pair) == 2 for pair in melody), "H_MELODY_PAIRS", n)
        else:
            melody = [[pitch] for pitch in pitch_tokens(target_row.split(":", 1)[1])]
            need(len(melody) == 8, "H_MELODY_TARGETS")
        bass = pitch_tokens(bass_row.split(":", 1)[1]) if bass_row else [None] * 8
        need(len(bass) == 8, "H_BASS_ROUTE", n)
        page_no = n + 13
        for snippet in (title, *chord_rows, melody_row or target_row, bass_row or texture_row):
            page_contains(pages[page_no - 1], snippet, f"H{n}")
        bars = [{"bar": bar, "harmony": harmony[bar - 1], "melody_anchors": melody[bar - 1],
                 "bass_anchor": bass[bar - 1], "printed_event_allocation": 5}
                for bar in range(1, 9)]
        tasks.append({"task": f"H{n}", "source_txt_lines": [line_no, detail[-1][0]],
                      "source_pdf_pages": [page_no], "title": title, "bars": bars,
                      "texture_direction": texture_row, "printed_event_allocation": 40,
                      "unresolved": ["five_event_per_bar_allocation_does_not_specify_all_inner_attacks"] +
                                    (["arrangement_four_bass_route_not_printed"] if n == 4 else [])})
    return tasks


def parse_i(lines: list[str], pages: list[str], bound: tuple[int, int]) -> list[dict]:
    rows = module_lines(lines, bound)
    need(len(rows) == 24, "I_BAR_COUNT")
    tasks = []
    for n, (line_no, line) in enumerate(rows, 1):
        match = re.fullmatch(r"Bar (\d+): ([^;]+); bass ([A-G]#?); melody ([A-G]#?); (.+)\.", line)
        need(match is not None and int(match[1]) == n, "I_BAR_FORMAT", line_no)
        chord, bass, melody, job = match[2], match[3], match[4], match[5]
        page_no = 18 if n <= 12 else 19
        page_lines = pages[page_no - 1].splitlines()
        start = page_lines.index("Job") + 1
        offset = (n - 1) % 12 * 5
        need(page_lines[start + offset:start + offset + 5] ==
             [str(n), chord, bass, melody, job], "I_PDF_TABLE", n)
        need(chord in CHORD or chord in ("G7/C", "Dm7/C"), "I_HARMONY_NAME", n)
        tasks.append({"task": f"I{n}", "source_txt_lines": [line_no], "source_pdf_pages": [page_no],
                      "bar": n, "harmony": chord, "bass_anchor": bass, "melody_anchor": melody,
                      "functional_job": job, "printed_event_allocation": 8, "source_anchors": 2,
                      "unresolved": ["remaining_six_event_pitches_and_inner_voice_allocation_not_printed"]})
    return tasks


def parse_j(lines: list[str], pages: list[str], bound: tuple[int, int]) -> list[dict]:
    rows = module_lines(lines, bound)
    need(len(rows) == 8, "J_RECOVERY_COUNT")
    tasks = []
    for n, (line_no, line) in enumerate(rows, 1):
        label, repair = line.split(": ", 1)
        page_contains(pages[19], line, f"J{n}")
        tasks.append({"task": f"J{n}", "source_txt_lines": [line_no], "source_pdf_pages": [20],
                      "failure_trigger": label, "recovery_instruction": repair,
                      "printed_event_allocation": 8,
                      "unresolved": ["recovery_instruction_is_not_eight_notated_note_attacks"]})
    return tasks


def extract_pdf_rubric(page: str) -> dict:
    text = page.splitlines()
    start = text.index("Mastery gate")
    end = text.index("Capstone score - 0 to 2 each")
    mastery = text[start + 1:end]
    stop = next(i for i in range(end + 1, len(text)) if text[i].startswith("Pass at 14/16"))
    categories = text[end + 1:stop]
    need(len(mastery) == 9 and len(categories) == 8 and
         "14/16 or better on two separate days" in text[stop], "PDF_RUBRIC")
    return {"mastery_gate": mastery, "score_categories": categories,
            "score_scale_per_category": [0, 2], "pass_threshold": 14, "maximum_score": 16,
            "two_separate_days_required": True,
            "zero_forbidden_categories": ["Melody clarity", "Bass timing", "Pulse / form", "Recovery"],
            "exact_pass_rule": text[stop]}


def build(root: Path = ROOT) -> dict:
    lines, pages, source_row, source, frozen = read_sources(root)
    bound = sections(lines)
    modules = {"A": parse_a(lines, pages, bound["A"]),
               "B": parse_b(lines, pages, bound["B"]),
               "C": parse_c(lines, pages, bound["C"]),
               "D": parse_d(lines, pages, bound["D"]),
               "E": parse_e_f(lines, pages, bound["E"], "E"),
               "F": parse_e_f(lines, pages, bound["F"], "F"),
               "G": parse_g(lines, pages, bound["G"]),
               "H": parse_h(lines, pages, bound["H"]),
               "I": parse_i(lines, pages, bound["I"]),
               "J": parse_j(lines, pages, bound["J"])}
    totals = {key: sum(task["printed_event_allocation"] for task in tasks)
              for key, tasks in modules.items()}
    need(totals == COUNTS and sum(totals.values()) == 1184, "PRINTED_WORKLOAD", totals)
    for key, label in zip(COUNTS, ("Moving inner-voice lines", "Pedal-tone independence",
                                   "Walking-bass construction", "Passing diminished chords",
                                   "Drop-2 voicing control", "Drop-3 spread voicings",
                                   "Independent-voice integration patterns", "Four eight-bar arrangements",
                                   "Twenty-four-bar capstone", "Recovery and reduction audit")):
        need(f"{key}. {label}: {COUNTS[key]} events" in lines, "TXT_LEDGER", key)
    need("TOTAL: 1184 events" in lines and "1,184 EVENTS" in pages[0] and
         any("There is no Level 106" in line for line in lines) and
         "NO LEVEL 106" in pages[19], "GLOBAL_LEDGER_AND_HARD_STOP")
    rubric = extract_pdf_rubric(pages[19])
    return {"schema": "fathom.detached.curriculum.level081.whole.r01", "wbs": "2.3.1.3.1",
            "level": 81, "section": "XI", "title": lines[1], "source": source,
            "source_map_row": source_row, "frozen_catalog_context": frozen,
            "modules": modules, "printed_events_by_module": totals, "printed_event_allocation": 1184,
            "count_convention": "A-J allocations are printed source workload, not 1184 fully specified playable note attacks. Where individual events are absent, retain count-backed tasks and unresolved fields.",
            "pdf_source_pages": [{"page": i, "extracted_text": page,
                                  "text_sha256": sha(page.encode("utf-8"))}
                                 for i, page in enumerate(pages, 1)],
            "txt_source_lines": [{"line": i, "text": line} for i, line in enumerate(lines, 1)],
            "pdf_only_assessment": rubric,
            "source_difference_ledger": [
                {"module": "D", "field": "Dm7/F printed grip", "txt": "x x 3 2 3 1",
                 "musical_check": "sounds F-A-D-F, omitting the printed Dm7 chord's C seventh",
                 "disposition": "retain printed grip and Dm7/F functional label separately; do not add C"},
                {"module": "F", "field": "printed low-to-high pitch order", "voicings": ["Cmaj7", "Cm7", "Dm7"],
                 "musical_check": "the D- and G-string pitches are reversed in the TXT/PDF pitch and degree lists for these three shapes",
                 "disposition": "retain the printed lists and fretboard-derived low-to-high order as separate fields"},
                {"module": "J", "field": "64-event recovery allocation", "txt_pdf": "eight verbal recovery cards with eight-event allocation each, no note grids",
                 "disposition": "retain as count-backed recovery tasks, not fabricated note attacks"}],
            "whole_level_source_coverage": True,
            "candidate_status": "detached_pending_P02_integration_and_curriculum_review",
            "new_canonical_ids_assigned": False, "runtime_import": False, "content_admitted": False,
            "timing_audio_or_scoring_inferred": False}


def write_candidate(candidate: dict, output: Path, root: Path = ROOT) -> str:
    target = output if output.is_absolute() else root / output
    allowed = (root / BUILD).resolve()
    need(not target.is_symlink() and target.resolve().parent == allowed and target.suffix == ".json",
         "OUTPUT_BOUNDARY", target)
    need(not target.exists(), "OUTPUT_EXISTS", target)
    target.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(candidate, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    target.write_bytes(raw)
    return sha(raw)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=BUILD / "level081-candidate-a.json")
    args = parser.parse_args()
    try:
        candidate = build()
        digest = write_candidate(candidate, args.output)
    except (CandidateError, OSError, UnicodeError) as exc:
        parser.exit(2, f"LEVEL081_CANDIDATE_ERROR {exc}\n")
    print(f"LEVEL081_CANDIDATE_OK events={candidate['printed_event_allocation']} sha256={digest} output={args.output}")


if __name__ == "__main__":
    main()
