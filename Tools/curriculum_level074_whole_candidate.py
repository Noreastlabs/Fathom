#!/usr/bin/env python3
"""Build a detached, source-pinned whole-Level-74 event/task candidate."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
from fractions import Fraction
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
STEM = "Guitar_Exercises_Section_X_Level_74_Odd_Rhythmic_Groupings_Cross_Bar_Accent_Cycles_Metric_Displacement_and_Polyrhythmic_Phrase_Control"
TXT = Path("Notes/music/guitar project/TXT version") / f"{STEM}.txt"
PDF = Path("Notes/music/guitar project/PDF version") / f"{STEM}.pdf"
MAP = Path("Results/parallel-01/exercises/inventory/20260922T180500Z-2.3-curriculum-v1-source-inventory-evidence/curriculum-source-map.tsv")
BUILD = Path("Build/parallel-08/2.3.1.3.1-level074-whole-r01")
PINS = {"txt": (18931, "63df8ae138ca4587315a04f239818057db44c990c3a6fac3ce9f82244a46aa28"),
        "pdf": (50020, "83ce1b9e548e28052de1487f21d70052aeeb3916829d25cc61589df69b650a72"),
        "map": (68536, "f526ff4d9ce3bceaf9a7cc581a3ac2aee2c74917eba984dd57913adba574c123")}
COUNTS = {"A": 240, "B": 64, "C": 192, "D": 108, "E": 108, "F": 192, "G": 64, "H": 200}
NOTE_RE = re.compile(r"[A-G](?:#|b)?")
TUNING = {"E": 4, "A": 9, "D": 2, "G": 7, "B": 11}
PITCH = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, "F#": 6,
         "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}
GRID = ("1", "e", "&", "a") * 4


class CandidateError(ValueError):
    pass


def need(ok: bool, code: str, detail: object = "") -> None:
    if not ok:
        raise CandidateError(f"{code}: {detail}")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def pinned(root: Path, path: Path, kind: str) -> bytes:
    raw = (root / path).read_bytes()
    need((len(raw), sha(raw)) == PINS[kind], "PINNED_SOURCE_DRIFT", path)
    return raw


def read_sources(root: Path) -> tuple[list[str], list[str], dict, dict]:
    raw_txt, raw_pdf, raw_map = (pinned(root, path, kind) for kind, path in
                                 (("txt", TXT), ("pdf", PDF), ("map", MAP)))
    lines = raw_txt.decode("utf-8").splitlines()
    need(len(lines) == 429 and lines[0] == "GUITAR EXERCISES - SECTION X, LEVEL 74", "TXT_HEADER")
    pages = [(page.extract_text() or "").strip() for page in PdfReader(io.BytesIO(raw_pdf)).pages]
    need(len(pages) == 20 and all("Level 74" in page for page in pages), "PDF_PAGES")
    rows = list(csv.DictReader(io.StringIO(raw_map.decode("utf-8")), delimiter="\t"))
    matches = [row for row in rows if row.get("level") == "74"]
    need(len(matches) == 1, "SOURCE_MAP_ROW")
    row = matches[0]
    need(row["section"] == "X" and row["wbs_owner"] == "2.3.1.3.1" and
         row["txt_path"] == str(TXT) and row["pdf_path"] == str(PDF) and
         row["pair_status"] == "exact_stem_pair" and row["review"] == "Pending" and
         row["representative_status"] == "frozen_representative_record" and
         row["representative_item_id"] == "fg:item:000010" and row["stable_ids_assigned"] == "True" and
         row["runtime_eligible"] == row["imported"] == row["admitted"] == "False",
         "SOURCE_MAP_STATUS", row)
    source = {label: {"path": str(path), "bytes": PINS[pin][0], "sha256": PINS[pin][1]}
              for label, pin, path in (("txt", "txt", TXT), ("pdf", "pdf", PDF),
                                       ("source_map", "map", MAP))}
    source["txt"]["lines"] = len(lines)
    source["pdf"]["pages"] = len(pages)
    return lines, pages, row, source


def sections(lines: list[str]) -> dict[str, tuple[int, int]]:
    heads = {key: next(i for i, line in enumerate(lines) if line.startswith(f"MODULE {key} -"))
             for key in COUNTS}
    need(list(heads.values()) == sorted(heads.values()), "MODULE_ORDER")
    return {key: (at, list(heads.values())[n + 1] if n < 7 else 405)
            for n, (key, at) in enumerate(heads.items())}


def notes(row: str, label: str) -> list[str]:
    need(row.lstrip().startswith(label), "GRID_LABEL", row)
    return NOTE_RE.findall(row.split("|", 1)[1])


def grid_rows(block: list[str], note_label: str) -> list[tuple[int, str]]:
    return [(i, line) for i, line in enumerate(block) if line.lstrip().startswith(note_label) and "|" in line]


def page_has(page: str, line: str, context: str) -> None:
    need(line.strip() in page, "PDF_GRID_DRIFT", (context, line))


def route(header: str) -> list[dict]:
    contacts = re.findall(r"([EADGB])([0-9]+)\(([A-G]#?)\)", header)
    need(contacts, "ROUTE_MISSING", header)
    out = []
    for string, fret, note in contacts:
        need((TUNING[string] + int(fret)) % 12 == PITCH[note], "ROUTE_PITCH", header)
        out.append({"string": string, "fret": int(fret), "pitch": note})
    return out


def event(note: str | None, position: int, *, voice: str | None = None,
          accent: bool | None = None, contact: dict | None = None) -> dict:
    return {"pitch": note, "position_index": position, "voice": voice,
            "accent": accent, "fret_contact": contact, "canonical_event_id": None}


def parse_a(lines: list[str], pages: list[str], bounds: tuple[int, int]) -> list[dict]:
    block = lines[bounds[0]:bounds[1]]
    tasks = []
    for group, bars, page_no, expected in ((3, 3, 3, 48), (5, 5, 4, 80), (7, 7, 5, 112)):
        header = f"GROUP OF {group}: {bars} bars, {expected} contacts, 16 accents"
        start = next(i for i, line in enumerate(block) if line == header)
        end = next((i for i in range(start + 1, len(block)) if block[i].startswith("GROUP OF ")), len(block))
        part = block[start:end]
        locations = route(next(line for line in part if line.startswith("Route:")))
        need(len(locations) == group, "A_ROUTE_SIZE", group)
        bar_lines = [(i, line) for i, line in enumerate(part) if re.match(r"Bar \d+\|", line)]
        need(len(bar_lines) == bars, "A_BAR_COUNT", group)
        all_events = []
        for bar_no, (at, bar_line) in enumerate(bar_lines, 1):
            acc, grp, nte = part[at + 1:at + 4]
            need(acc.startswith("Acc") and grp.startswith("Grp") and nte.startswith("Nte"), "A_GRID", (group, bar_no))
            for row in (bar_line, acc, grp, nte):
                page_has(pages[page_no - 1], row, f"A{group} bar {bar_no}")
            pitches = notes(nte, "Nte")
            need(len(pitches) == 16, "A_CONTACTS", (group, bar_no))
            marks = [m.start() for m in re.finditer(">", acc.split("|", 1)[1])]
            pitch_starts = [m.start() for m in NOTE_RE.finditer(nte.split("|", 1)[1])]
            expected_slots = [slot for slot in range(16) if (bar_no - 1) * 16 + slot in range(0, expected, group)]
            need(marks == [pitch_starts[slot] for slot in expected_slots], "A_ACCENT_GRID", (group, bar_no))
            group_numbers = [int(v) for v in re.findall(r"\d+", grp.split("|", 1)[1])]
            need(group_numbers == [((bar_no - 1) * 16 + slot) // group + 1 for slot in expected_slots],
                 "A_GROUP_NUMBERS", (group, bar_no))
            for slot, pitch in enumerate(pitches):
                contact = locations[((bar_no - 1) * 16 + slot) % group]
                need(pitch == contact["pitch"], "A_PITCH_ROUTE", (group, bar_no, slot))
                all_events.append({**event(pitch, (bar_no - 1) * 16 + slot,
                                           accent=slot in expected_slots, contact=contact),
                                   "bar": bar_no, "sixteenth_slot": slot, "count_label": GRID[slot]})
        need(len(all_events) == expected and sum(x["accent"] for x in all_events) == 16,
             "A_CYCLE_TOTAL", group)
        tasks.append({"task": f"A{len(tasks)+1}", "group_size": group, "meter": "4/4",
                      "source_txt_lines": [bounds[0] + start + 1, bounds[0] + end],
                      "source_pdf_pages": [page_no], "fret_route": locations,
                      "notated_contacts": expected, "events": all_events})
    return tasks


def parse_b(lines: list[str], pages: list[str], bounds: tuple[int, int]) -> list[dict]:
    block = lines[bounds[0]:bounds[1]]
    locations = route(next(line for line in block if line.startswith("Route:")))
    need([x["pitch"] for x in locations] == ["C", "E", "G", "B", "A", "G", "E", "D"], "B_ROUTE")
    tasks = []
    for num in range(1, 9):
        at = next(i for i, line in enumerate(block) if line.startswith(f"B{num}:"))
        count, nte = block[at + 1:at + 3]
        page_no = 6 if num <= 4 else 7
        page_has(pages[page_no - 1], count, f"B{num}")
        page_has(pages[page_no - 1], nte, f"B{num}")
        pitches = notes(nte, "Nte")
        starts = [48 * bar + m.start() for bar, segment in enumerate(nte.split("|")[1:-1])
                  for m in NOTE_RE.finditer(segment)]
        onset = num - 1 if num <= 4 else num + 7
        need(pitches == [x["pitch"] for x in locations] and starts == [3 * (onset + i) for i in range(8)],
             "B_DISPLACEMENT", num)
        events = [{**event(pitch, onset + i, contact=locations[i]),
                   "bar": (onset + i) // 16 + 1, "sixteenth_slot": (onset + i) % 16}
                  for i, pitch in enumerate(pitches)]
        tasks.append({"task": f"B{num}", "source_txt_lines": [bounds[0] + at + 1, bounds[0] + at + 3],
                      "source_pdf_pages": [page_no], "meter": "4/4", "two_bar_onset_slot": onset,
                      "notated_contacts": 8, "events": events})
    return tasks


def parse_c(lines: list[str], pages: list[str], bounds: tuple[int, int]) -> list[dict]:
    block = lines[bounds[0]:bounds[1]]
    specs = [("C1", 20, 5, 4, ["A"] * 20, 8),
             ("C2", 20, 5, 4, ["C", "E", "G", "B", "D"] * 4, 8),
             ("C3", 25, 5, 5, [None] * 25, 8),
             ("C4", 28, 7, 4, ["A"] * 28, 9),
             ("C5", 28, 7, 4, ["C", "D", "E", "F", "G", "A", "B"] * 4, 9),
             ("C6", 49, 7, 7, [None] * 49, 9),
             ("C7", 22, None, 4, ["C", "E", "G", "B", "C", "E", "G", "B", "D",
                                       "C", "D", "E", "G", "A", "B", "C", "D", "E", "F", "G", "A", "B"], 9)]
    tasks = []
    pdf_rows = {8: [notes(line, "Nte") for line in pages[7].splitlines() if line.startswith("Nte")],
                9: [notes(line, "Nte") for line in pages[8].splitlines() if line.startswith("Nte")]}
    need([len(row) for row in pdf_rows[8]] == [20, 20] and
         [len(row) for row in pdf_rows[9]] == [28, 28], "C_PDF_NOTE_ROWS")
    for name, count, rate, beats, pitches, page_no in specs:
        at = next(i for i, line in enumerate(block) if line.startswith(name + " "))
        need(name in pages[page_no - 1] and str(count) in pages[page_no - 1], "C_PDF_COUNT", name)
        if name == "C7":
            txt_notes = [NOTE_RE.findall(line.split(":", 1)[1]) for line in block[at + 1:at + 5]]
            need([len(x) for x in txt_notes] == [4, 5, 6, 7] and sum(txt_notes, []) == pitches,
                 "C_RATE_LADDER")
        else:
            need(re.search(rf"\b{count}\b", block[at]) or
                 (name in ("C2", "C5") and "once per beat, four beats" in block[at]) or
                 (name in ("C3", "C6") and f"{beats} beats x {rate} notes = {count} tones" in pages[page_no - 1]),
                 "C_TXT_COUNT", name)
        if name in ("C1", "C2", "C4", "C5"):
            row_index = 0 if name in ("C1", "C4") else 1
            need(pdf_rows[page_no][row_index] == pitches, "C_PDF_PITCHES", name)
        events = []
        for i, pitch in enumerate(pitches):
            current_rate = rate if rate else [4, 5, 6, 7][next(b for b, edge in enumerate((4, 9, 15, 22)) if i < edge)]
            beat = i // rate if rate else next(b for b, edge in enumerate((4, 9, 15, 22)) if i < edge)
            index_in_beat = i % rate if rate else i - (0, 4, 9, 15)[beat]
            events.append({**event(pitch, i, accent=(index_in_beat == beat % rate) if name in ("C3", "C6") else None),
                           "beat_index": beat, "subdivision_index": index_in_beat,
                           "subdivision_rate": current_rate})
        tasks.append({"task": name, "source_txt_lines": [bounds[0] + at + 1, bounds[0] + at + 1],
                      "source_pdf_pages": [page_no], "notated_contacts": count, "events": events,
                      "unresolved": ["rotation_cell_pitches_not_specified"] if name in ("C3", "C6") else []})
    need(sum(t["notated_contacts"] for t in tasks) == 192, "C_TOTAL")
    return tasks


def parse_d(lines: list[str], pages: list[str], bounds: tuple[int, int]) -> list[dict]:
    block = lines[bounds[0]:bounds[1]]
    tasks = []
    roles = {"Cmaj7": ("C", "E"), "Am7": ("A", "C"),
             "Dm7": ("D", "F"), "G7": ("G", "B")}
    for name, prefix, page_no, lower_label, upper_label, count in (
            ("D1", "3:2", 10, "2-pul", "3-pul", 10),
            ("D2", "4:3", 11, "3-pul", "4-pul", 8)):
        for chord in ("Cmaj7", "Am7", "Dm7", "G7"):
            at = next(i for i, line in enumerate(block) if line.startswith(prefix + " " + chord + " -"))
            line_count = 3 if name == "D1" else 4
            rows = block[at + 1:at + 1 + line_count]
            need(rows[0].startswith("Count") and rows[1].startswith(lower_label) and
                 rows[2].startswith(upper_label), "D_GRID", (name, chord))
            for row in rows:
                page_has(pages[page_no - 1], row, f"{name} {chord}")
            lower, upper = notes(rows[1], lower_label), notes(rows[2], upper_label)
            need(len(lower) == (4 if name == "D1" else 3) and
                 len(upper) == (6 if name == "D1" else 4), "D_VOICE_COUNT", (name, chord))
            root_pitch, upper_pitch = roles[chord]
            need(set(lower) == {root_pitch} and set(upper) == {upper_pitch},
                 "D_CHORD_ROLES", (name, chord))
            if name == "D1":
                match = re.search(r"locations ([EADGB])(\d+) / ([EADGB])(\d+)", block[at], re.I)
                need(match is not None and (TUNING[match[1].upper()] + int(match[2])) % 12 == PITCH[root_pitch]
                     and (TUNING[match[3].upper()] + int(match[4])) % 12 == PITCH[upper_pitch],
                     "D_VOICING_CONTACT", chord)
            if name == "D1":
                lower_pos = [Fraction(i) for i in range(4)]
                upper_pos = [Fraction(i * 2, 3) for i in range(6)]
            else:
                lower_pos = [Fraction(i) for i in range(3)]
                upper_pos = [Fraction(i * 3, 4) for i in range(4)]
            events = ([{**event(pitch, i, voice="lower"), "quarter_position": str(pos)}
                       for i, (pitch, pos) in enumerate(zip(lower, lower_pos))] +
                      [{**event(pitch, i, voice="upper"), "quarter_position": str(pos)}
                       for i, (pitch, pos) in enumerate(zip(upper, upper_pos))])
            if name == "D2":
                resolution = notes(rows[3], "Beat4")
                need(len(resolution) == 1 and resolution[0] == lower[0], "D_RESOLUTION", chord)
                events.append({**event(resolution[0], 0, voice="beat_four_resolution"), "quarter_position": "3"})
            need(len(events) == count, "D_CONTACTS", (name, chord))
            tasks.append({"task": name, "chord": chord, "source_txt_lines": [bounds[0] + at + 1,
                          bounds[0] + at + 1 + line_count], "source_pdf_pages": [page_no],
                          "notated_contacts": count, "events": events,
                          "simultaneous_contacts_counted_separately": True})
    for n, text in enumerate(("Transition cell 1: Cmaj7 3:2 -> G7 4:3. 18 tones.",
                              "Transition cell 2: Am7 3:2 -> E7 4:3. 18 tones."), 1):
        at = next(i for i, line in enumerate(block) if line == text)
        need(("Cell " + str(n) + ":") in pages[10] and "18 tones" in pages[10], "D_TRANSITION_PDF")
        tasks.append({"task": f"D3.{n}", "source_txt_lines": [bounds[0] + at + 1],
                      "source_pdf_pages": [11], "notated_contacts": 18,
                      "bar_1": "Cmaj7 3:2" if n == 1 else "Am7 3:2",
                      "bar_2": "G7 4:3" if n == 1 else "E7 4:3",
                      "events": None,
                      "unresolved": ["transition_pitches_and_exact_event_positions_not_printed",
                                     "E7_upper_voice_and_voicing_not_printed"] if n == 2 else
                                    ["transition_pitches_and_exact_event_positions_not_printed"]})
    need(sum(t["notated_contacts"] for t in tasks) == 108, "D_TOTAL")
    return tasks


def parse_e(lines: list[str], pages: list[str], bounds: tuple[int, int]) -> list[dict]:
    block = lines[bounds[0]:bounds[1]]
    expected_cells = {1: ["C", "D", "E", "F", "G", "A", "B", "C", "D", "E"],
                      2: ["C", "D", "E", "F", "G", "A", "B", "C", "D", "E"],
                      3: ["C", "E", "G", "C", "E", "G", "B", "D", "F", "G"],
                      4: ["A", "C", "E", "G", "A", "D", "F", "A", "C", "D"],
                      5: ["C", "D", "E", "F", "G", "A", "B"],
                      6: ["C", "D", "E", "F", "G", "A", "B"],
                      7: ["C", "D", "E", "F", "G", "A", "B"],
                      8: ["C", "E", "D", "F", "G", "B", "D"]}
    tasks = []
    for num in range(1, 9):
        at = next(i for i, line in enumerate(block) if line.startswith(f"E{num} -"))
        grouping = next(line for line in block[at + 1:at + 4] if line.startswith("Group"))
        nte = next(line for line in block[at + 1:at + 4] if line.startswith("Notes"))
        page_no = 12 if num <= 4 else 13
        page_has(pages[page_no - 1], grouping, f"E{num}")
        page_has(pages[page_no - 1], nte, f"E{num}")
        pitches = notes(nte, "Notes")
        expected = 10 if num <= 4 else 7
        need(len(pitches) == expected and pitches == expected_cells[num], "E_PITCH_CELL", num)
        meter = "5/4" if num <= 4 else "7/8"
        groups = [int(x) for x in re.search(r"Group (\d(?:\+\d)+)", grouping).group(1).split("+")]
        need(sum(groups) == (5 if num <= 4 else 7), "E_GROUPING", num)
        boundaries = [0] + [sum(groups[:i]) * (2 if num <= 4 else 1) for i in range(1, len(groups))]
        mark_starts = [m.start() for m in re.finditer(">", grouping.split("|", 1)[1])]
        note_starts = [m.start() for m in NOTE_RE.finditer(nte.split("|", 1)[1])]
        need(mark_starts == [note_starts[index] for index in boundaries], "E_ACCENT_GRID", num)
        repeats = 2 if num <= 4 else 1
        events = [{**event(pitch, bar * expected + slot, accent=slot in boundaries),
                   "bar": bar + 1, "eighth_slot": slot}
                  for bar in range(repeats) for slot, pitch in enumerate(pitches)]
        tasks.append({"task": f"E{num}", "meter": meter, "grouping": groups,
                      "source_txt_lines": [bounds[0] + at + 1, bounds[0] + at + 3],
                      "source_pdf_pages": [page_no], "notated_contacts": len(events), "events": events})
    need(sum(t["notated_contacts"] for t in tasks) == 108, "E_TOTAL")
    return tasks


def parse_f(lines: list[str], pages: list[str], bounds: tuple[int, int]) -> list[dict]:
    block = lines[bounds[0]:bounds[1]]
    expected_cells = {
        1: [["C", "E", "G"], ["A", "C", "E"], ["D", "F", "A"], ["G", "B", "D"]],
        2: [["C", "E", "G", "B", "D"], ["A", "C", "E", "G", "B"],
            ["D", "F", "A", "C", "E"], ["G", "B", "D", "F", "A"]],
        3: [["C", "D", "E", "F", "G", "A", "B"],
            ["D", "E", "F", "G", "A", "B", "C"],
            ["G", "A", "B", "C", "D", "E", "F"],
            ["C", "D", "E", "F", "G", "A", "B"]]}
    tasks = []
    for num, group, page_no in ((1, 3, 14), (2, 5, 14), (3, 7, 15)):
        at = next(i for i, line in enumerate(block) if line.startswith(f"F{num} group of "))
        bars = []
        for bar_num in range(1, 5):
            row_at = next(i for i in range(at + 1, len(block)) if block[i].startswith(f"Bar {bar_num} "))
            head, acc, nte = block[row_at:row_at + 3]
            need(acc.startswith("Accent") and nte.startswith("Notes"), "F_GRID", (num, bar_num))
            for row in (head, acc, nte):
                page_has(pages[page_no - 1], row, f"F{num} bar {bar_num}")
            pitches = notes(nte, "Notes")
            need(len(pitches) == 16, "F_CONTACTS", (num, bar_num))
            starts = [m.start() for m in NOTE_RE.finditer(nte.split("|", 1)[1])]
            marks = [m.start() for m in re.finditer(">", acc.split("|", 1)[1])]
            accented = [slot for slot in range(16) if ((bar_num - 1) * 16 + slot) % group == 0]
            need(marks == [starts[slot] for slot in accented], "F_ACCENT_GRID", (num, bar_num))
            chord = re.match(r"Bar \d+ ([^| ]+)", head).group(1)
            cell = pitches[:group]
            need(cell == expected_cells[num][bar_num - 1] and
                 all(pitch == cell[slot % group] for slot, pitch in enumerate(pitches)),
                 "F_CHORD_CELL", (num, bar_num))
            bars.append({"bar": bar_num, "harmony": chord, "events":
                         [{**event(pitch, (bar_num - 1) * 16 + slot, accent=slot in accented),
                           "bar": bar_num, "sixteenth_slot": slot}
                          for slot, pitch in enumerate(pitches)]})
        need([bar["harmony"] for bar in bars] == (["Cmaj7", "Am7", "Dm7", "G7"] if num < 3 else
                                                   ["Cmaj7", "Dm7", "G7", "Cmaj7"]), "F_HARMONY", num)
        tasks.append({"task": f"F{num}", "group_size": group, "meter": "4/4",
                      "source_txt_lines": [bounds[0] + at + 1, bounds[0] + at + 13],
                      "source_pdf_pages": [page_no], "notated_contacts": 64, "bars": bars})
    return tasks


def parse_g(lines: list[str], pages: list[str], bounds: tuple[int, int]) -> list[dict]:
    block = lines[bounds[0]:bounds[1]]
    tasks = []
    for num in range(1, 9):
        at = next(i for i, line in enumerate(block) if line.startswith(f"G{num}:"))
        q, a = block[at + 1:at + 3]
        page_has(pages[15], q, f"G{num}")
        page_has(pages[15], a, f"G{num}")
        question, answer = notes(q, "Q"), notes(a, "A")
        onset = [m.start() for m in NOTE_RE.finditer(a.split("|", 1)[1])][0] // 3
        need(question == ["C", "E", "G", "B"] and answer == ["A", "G", "E", "D"] and
             onset == num - 1, "G_PAIR", num)
        events = [{**event(pitch, i, voice="question"), "bar": 1, "quarter_beat": i + 1}
                  for i, pitch in enumerate(question)] + [
                    {**event(pitch, onset + i, voice="answer"), "bar": 2, "sixteenth_slot": onset + i}
                    for i, pitch in enumerate(answer)]
        tasks.append({"task": f"G{num}", "source_txt_lines": [bounds[0] + at + 1, bounds[0] + at + 3],
                      "source_pdf_pages": [16], "answer_onset_slot": onset,
                      "notated_contacts": 8, "events": events})
    return tasks


def parse_h(lines: list[str], pages: list[str], bounds: tuple[int, int]) -> list[dict]:
    block = lines[bounds[0]:bounds[1]]
    cue = pages[17]
    for fragment in ("Cmaj7-----------|Am7-------------|Dm7-------------|",
                     "C-E-G repeating", "A-C-E repeating", "D-F-A repeating",
                     "G7------|Cmaj7---|Am7-----|Dm7-----|G7------|",
                     "G-B-D-F-A|C-E-G-B-D|A-C-E-G-B|D-F-A-C-E|G-B-D-F-A|",
                     "Bar 9 start 1", "Bar 10 start e of 1", "Bar 11 start & of 1",
                     "Bar 12 start a of 1", "Motif each bar: C-E-G-B-A-G-E-D",
                     "Bass roots: C, A, D, G", "Upper thirds: E, C, F, B"):
        need(fragment in cue, "H_PDF_CUE", fragment)
    harmonies = ["Cmaj7", "Am7", "Dm7", "G7", "Cmaj7", "Am7", "Dm7", "G7",
                 "Cmaj7", "Am7", "Dm7", "G7", "Cmaj7", "Am7", "Dm7", "G7"]
    cells = [["C", "E", "G"], ["A", "C", "E"], ["D", "F", "A"],
             ["G", "B", "D", "F", "A"], ["C", "E", "G", "B", "D"],
             ["A", "C", "E", "G", "B"], ["D", "F", "A", "C", "E"],
             ["G", "B", "D", "F", "A"]]
    printed = [("Bars 1-3:", 48, 1, 3, "group_of_3"),
               ("Bars 4-8:", 80, 4, 8, "group_of_5"),
               ("Bars 9-12:", 32, 9, 12, "displaced_motif"),
               ("Bars 13-16:", 40, 13, 16, "three_over_two")]
    tasks = []
    for prefix, count, first, last, rhythm in printed:
        at = next(i for i, line in enumerate(block) if line.startswith(prefix))
        need(f"{count} tones" in block[at] and str(count) in pages[16], "H_ARCHITECTURE", prefix)
        bars = []
        for bar in range(first, last + 1):
            plan = {"bar": bar, "harmony": harmonies[bar - 1],
                    "notated_contacts": 16 if bar <= 8 else 8 if bar <= 12 else 10}
            if bar <= 8:
                plan["pitch_cell"] = cells[bar - 1]
                plan["accent_group_size"] = 3 if bar <= 3 else 5
                plan["pitch_cell_restarts_at_barline"] = True
                plan["accent_cycle_continues_across_barline"] = True
            elif bar <= 12:
                plan["motif"] = ["C", "E", "G", "B", "A", "G", "E", "D"]
                plan["onset_sixteenth_slot"] = bar - 9
            else:
                plan["lower_root"] = ["C", "A", "D", "G"][bar - 13]
                plan["upper_third"] = ["E", "C", "F", "B"][bar - 13]
                plan["lower_contacts"] = 4
                plan["upper_contacts"] = 6
            bars.append(plan)
        need(sum(bar["notated_contacts"] for bar in bars) == count, "H_SECTION_TOTAL", prefix)
        tasks.append({"task": rhythm, "bar_range": [first, last], "source_txt_lines": [bounds[0] + at + 1],
                      "source_pdf_pages": [17, 18], "notated_contacts": count,
                      "bar_plan": bars,
                      "pitch_and_rhythm_cue": [line for line in cue.splitlines()
                                               if line.startswith("Bars ") or line.startswith("Harmony") or
                                               line.startswith("Grouping") or line.startswith("Pitch") or
                                               line.startswith("Cell") or line.startswith("Rule") or
                                               line.startswith("Motif") or line.startswith("Bass roots")],
                      "unresolved": ["full_individual_contact_notation_not_printed"]})
    need(sum(task["notated_contacts"] for task in tasks) == 200, "H_TOTAL")
    close = next(line for line in block if line.startswith("Final close:"))
    need("not included in the 200-tone capstone count" in close and
         "one whole-note Cmaj7" in pages[16], "H_CLOSE")
    return tasks


def build(root: Path = ROOT) -> dict:
    lines, pages, source_row, source = read_sources(root)
    bounds = sections(lines)
    modules = {"A": parse_a(lines, pages, bounds["A"]),
               "B": parse_b(lines, pages, bounds["B"]),
               "C": parse_c(lines, pages, bounds["C"]),
               "D": parse_d(lines, pages, bounds["D"]),
               "E": parse_e(lines, pages, bounds["E"]),
               "F": parse_f(lines, pages, bounds["F"]),
               "G": parse_g(lines, pages, bounds["G"]),
               "H": parse_h(lines, pages, bounds["H"])}
    totals = {key: sum(task["notated_contacts"] for task in tasks) for key, tasks in modules.items()}
    need(totals == COUNTS and sum(totals.values()) == 1168, "PRINTED_WORKLOAD", totals)
    explicit_events = [event for tasks in modules.values() for task in tasks
                       for event in ((task.get("events") or []) +
                                     [item for bar in task.get("bars", []) for item in bar["events"]])]
    pitched = sum(event["pitch"] is not None for event in explicit_events)
    need(len(explicit_events) == 932 and pitched == 858, "EVENT_COVERAGE",
         (len(explicit_events), pitched))
    for key, count in COUNTS.items():
        need(f"Module {key}: {count} notated contacts." in lines, "TXT_LEDGER", key)
    need("TOTAL: 1168 notated contacts before diagnostic repeats and silent passes." in lines and
         "1168 NOTATED CONTACTS" in pages[0], "GLOBAL_LEDGER")
    return {"schema": "fathom.detached.curriculum.level074.whole.r01", "wbs": "2.3.1.3.1",
            "level": 74, "section": "X", "title": lines[1], "source": source,
            "source_map_row": source_row, "modules": modules,
            "txt_source_lines": [{"line": i, "text": line} for i, line in enumerate(lines, 1)],
            "pdf_source_pages": [{"page": i, "extracted_text": page,
                                  "text_sha256": sha(page.encode("utf-8"))}
                                 for i, page in enumerate(pages, 1)],
            "notated_contacts_by_module": totals, "notated_contacts": 1168,
            "event_coverage": {"individual_contacts_materialized": len(explicit_events),
                               "with_printed_pitch": pitched,
                               "printed_contact_with_unspecified_pitch": len(explicit_events) - pitched,
                               "task_count_only_without_individual_grid": 1168 - len(explicit_events)},
            "count_convention": "Each printed pitched/voice contact counts once; simultaneous lower and upper voices count separately. Diagnostic repeats, silent passes and the final whole-note Cmaj7 close are outside the 1168-contact ledger.",
            "workload_exceptions": [
                {"task": "E5-E8", "source_pdf_page": 13, "instruction": "Repeat eight bars without changing the grouping", "ledger_effect": "one seven-contact written bar per study; practice repetitions not multiplied"},
                {"task": "C7", "source_pdf_page": 9, "instruction": "Practice rate ladder in both directions", "ledger_effect": "one 22-contact written ladder; reverse practice pass not multiplied"},
                {"task": "F3", "source_pdf_page": 15, "instruction": "Replay with beat-1 target accent", "ledger_effect": "one 64-contact printed form; replay not multiplied"},
                {"task": "H close", "source_pdf_page": 17, "instruction": "one whole-note Cmaj7 after bar 16", "ledger_effect": "outside printed 200-contact capstone and 1168-contact total"}],
            "uncertainty_ledger": [
                {"module": "C", "field": "C3/C6 rotation pitches", "status": "not specified in TXT/PDF"},
                {"module": "D", "field": "D3 transition contact-by-contact pitches and slots", "status": "not specified in TXT/PDF; only two 18-tone transition tasks printed"},
                {"module": "H", "field": "individual capstone event grids", "status": "architecture and condensed cues printed; full individual contact grids absent"},
                {"module": "H", "field": "whole-note Cmaj7 final voicing", "status": "chord and duration class printed; voicing and individual-string attacks unspecified; excluded from 1168-contact ledger"},
                {"module": "global", "field": "BPM/performance/audio mapping", "status": "not assigned; PDF's +2 BPM practice rule retained as source text only"}],
            "whole_level_source_coverage": True, "candidate_status": "detached_pending_P02_integration_and_curriculum_review",
            "new_canonical_ids_assigned": False, "runtime_import": False, "content_admitted": False,
            "timing_in_seconds_or_audio_inferred": False}


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
    parser.add_argument("--output", type=Path, default=BUILD / "level074-candidate-a.json")
    args = parser.parse_args()
    try:
        candidate = build()
        digest = write_candidate(candidate, args.output)
    except (CandidateError, OSError, UnicodeError) as exc:
        parser.exit(2, f"LEVEL074_CANDIDATE_ERROR {exc}\n")
    print(f"LEVEL074_CANDIDATE_OK contacts={candidate['notated_contacts']} sha256={digest} output={args.output}")


if __name__ == "__main__":
    main()
