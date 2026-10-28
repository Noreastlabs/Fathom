#!/usr/bin/env python3
"""Build a detached, source-reconciled Level 45 blues-rhythm candidate."""

from __future__ import annotations

import argparse
import csv
import hashlib
from io import BytesIO
import json
from pathlib import Path
import re
import subprocess

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
STEM = "Scale_Exercises_Section_V_Level_45_A_Blues_Shuffle_Rhythm_Triplet_Placement_and_Twelve_Bar_Form_Fixed_Key_A"
TXT_REL = Path(f"Notes/music/guitar project/TXT version/{STEM}.txt")
PDF_REL = Path(f"Notes/music/guitar project/PDF version/{STEM}.pdf")
MAP_REL = Path("Results/parallel-01/exercises/inventory/20260922T180500Z-2.3-curriculum-v1-source-inventory-evidence/curriculum-source-map.tsv")
BUILD_REL = Path("Build/parallel-08/2.3.1.1.1-level045-whole-r01")
PINS = {"txt": (18102, "9f77c127208540d41d2f331c00c880dcdf935993f9e422993ce3babf232cd069"),
        "pdf": (51540, "f84f04ff134377eca66f904e45fbb8a0669b01c65c8c663f51a092558296357f"),
        "map": (68536, "f526ff4d9ce3bceaf9a7cc581a3ac2aee2c74917eba984dd57913adba574c123")}
CHORDS = ("A7", "A7", "A7", "A7", "D7", "D7", "A7", "A7", "E7", "D7", "A7", "E7")
ROOTS = (("E", 5), ("E", 5), ("E", 5), ("E", 5), ("A", 5), ("A", 5),
         ("E", 5), ("E", 5), ("A", 7), ("A", 5), ("E", 5), ("A", 7))
PITCH = {"A": 9, "C": 0, "C#": 1, "D": 2, "Eb": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "G#": 8, "B": 11}
OPEN = {"E": 4, "A": 9, "D": 2, "G": 7, "B": 11, "e": 4}
POOL = ("A", "C", "D", "Eb", "E", "G")
SUPPORT = {"C#*": "3* major-third/turnaround destination", "F#*": "6* turnaround support", "F*": "b6* chromatic lower approach to E",
           "B": "2*/E7-5 where marked", "G#": "7*/E7-3 where marked"}
COUNTS = {"A": 48, "B": 40, "C": 108, "D": 27, "E": 28, "F": 50, "G": 29, "H": 102, "I": 48, "J": 60}
MODULE_HEADINGS = {
    "A": "MODULE A - STRAIGHT EIGHTHS VERSUS SHUFFLE EIGHTHS",
    "B": "MODULE B - SINGLE-NOTE TRIPLET PLACEMENT",
    "C": "MODULE C - ROOT-CHANGE STUDY THROUGH THE TWELVE-BAR FORM",
    "D": "MODULE D - PICKUP-NOTE PLACEMENT INTO CHORD CHANGES",
    "E": "MODULE E - DELIBERATE RESTS AND CONTROLLED ENTRIES",
    "F": "MODULE F - FOUR-BAR CALLS AND FOUR-BAR RESPONSES",
    "G": "MODULE G - STOP-TIME PHRASING",
    "H": "MODULE H - TWELVE-BAR NAVIGATION",
    "I": "MODULE I - TURNAROUND ENTRY AND ENDING TIMING",
    "J": "MODULE J - METRONOME DISPLACEMENT AND FORM RECOVERY",
}


class CandidateError(ValueError):
    """Pinned source, printed structure or output boundary failed."""


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify(data: bytes, kind: str) -> None:
    size, sha = PINS[kind]
    if len(data) != size or digest(data) != sha:
        raise CandidateError(f"PINNED_INPUT_DRIFT {kind}: bytes={len(data)} sha256={digest(data)}")


def source_bytes(root: Path, relative: Path) -> bytes:
    path = root / relative
    if path.is_symlink() or not path.is_file() or path.resolve().parent != path.parent.resolve():
        raise CandidateError(f"SOURCE_PATH_INVALID {relative}")
    return path.read_bytes()


def module_block(lines: list[str], key: str) -> tuple[int, list[str]]:
    start = lines.index(MODULE_HEADINGS[key])
    candidates = [lines.index(heading) for heading in MODULE_HEADINGS.values() if heading != MODULE_HEADINGS[key] and heading in lines and lines.index(heading) > start]
    if key == "J":
        candidates.append(lines.index("LEVEL 45 CAPSTONE - THREE-CHORUS RHYTHM CIRCUIT"))
    end = min(candidates) if candidates else len(lines)
    return start, lines[start:end]


def parse_bar_mask(value: str) -> dict:
    beats = [part for part in value.strip().split("|") if part]
    if len(beats) != 4 or any(re.fullmatch(r"[X.]{3}", beat) is None for beat in beats):
        raise CandidateError(f"MASK_SHAPE_INVALID {value}")
    return {"beats": beats, "attack_slots": [[beat+1, slot+1] for beat, group in enumerate(beats)
                                                   for slot, mark in enumerate(group) if mark == "X"],
            "literal": "|".join(beats)}


def parse_masks(line: str) -> list[dict]:
    if "Mask|" not in line:
        raise CandidateError(f"MASK_MISSING {line}")
    if "||" in line:
        left, right = line.split("||", 1)
        first = left.split("Mask|", 1)[1]
        second = right.split("Mask|", 1)[1] if "Mask|" in right else right
        return [parse_bar_mask(first), parse_bar_mask(second)]
    return [parse_bar_mask(part) for part in re.findall(r"Mask\|([X.|]+)", line)]


def attacks(masks: list[dict]) -> int:
    return sum(len(mask["attack_slots"]) for mask in masks)


def note_tokens(value: str) -> list[str]:
    return re.findall(r"C#\*|F#\*|F\*|G#\*|Eb|C#|F#|G#|[ACDEFGB]", value.replace("|", " "))


def tab_events(tab_lines: list[str]) -> list[dict]:
    """Read authored TAB tokens in printed left-to-right order, preserving string/fret."""
    events = []
    for line in tab_lines:
        for match in re.finditer(r"([EADGBe])\|([^|]*)\|", line):
            string, body = match.groups()
            for fret_match in re.finditer(r"\d+", body):
                fret = int(fret_match.group())
                events.append({"string": string, "fret": fret,
                               "pitch_class": (OPEN[string]+fret)%12,
                               "source_column": match.start()+2+fret_match.start()})
    return events


def validate_pitch_sequence(notes: list[str], events: list[dict], label: str) -> None:
    if len(notes) != len(events):
        raise CandidateError(f"TAB_NOTE_COUNT {label}: {len(events)} != {len(notes)}")
    for ordinal, (name, placement) in enumerate(zip(notes, events, strict=True), 1):
        bare = name.removesuffix("*")
        if bare not in PITCH or placement["pitch_class"] != PITCH[bare]:
            raise CandidateError(f"TAB_NOTE_PITCH {label} {ordinal}: {name} {placement}")
        if name not in POOL and name not in SUPPORT:
            raise CandidateError(f"UNMARKED_SUPPORT_NOTE {label} {ordinal}: {name}")


def pdf_has(page: list[str], value: str, label: str) -> None:
    if value not in page:
        raise CandidateError(f"PDF_PARITY {label}: {value}")


def pdf_has_tab(page: list[str], tab: str, label: str) -> None:
    signature = [(event["string"], event["fret"]) for event in tab_events([tab])]
    pdf_tabs = re.findall(r"[EADGBe]\|[^|]*\|", "\n".join(page))
    if not any([(event["string"], event["fret"]) for event in tab_events([pdf_tab])] == signature for pdf_tab in pdf_tabs):
        raise CandidateError(f"PDF_TAB_PARITY {label}: {tab}")


def parse_a(block: list[str], pdf: list[str]) -> list[dict]:
    straight_count = block[block.index("STRAIGHT GRID")+2]
    shuffle_count = block[block.index("SHUFFLE GRID")+2]
    if straight_count != "Hit|X  X  X  X  X  X  X  X |" or shuffle_count != "Hit|X .  X |X .  X |X .  X |X .  X |":
        raise CandidateError("MODULE_A_GRID")
    shuffle_symbols = re.findall(r"[X.]", shuffle_count)
    if len(shuffle_symbols) != 12:
        raise CandidateError("MODULE_A_SHUFFLE_SLOT_COUNT")
    shuffle_mask = parse_bar_mask("|".join("".join(shuffle_symbols[3*i:3*i+3]) for i in range(4)))
    if len(shuffle_mask["attack_slots"]) != 8:
        raise CandidateError("MODULE_A_SHUFFLE_ATTACKS")
    out = []
    for index in range(1, 4):
        heading = next((line for line in block if line.startswith(f"PATTERN {index} - ")), None)
        if heading is None:
            raise CandidateError(f"MODULE_A_PATTERN {index}")
        start = block.index(heading)
        note_line, tab = block[start+1:start+3]
        names = note_tokens(note_line.removeprefix("Notes: "))
        events = tab_events([tab])
        validate_pitch_sequence(names, events, f"A{index}")
        if len(names) != 8 or not any(line == note_line for line in pdf) or f"Tab  {tab}" not in pdf:
            raise CandidateError(f"PDF_MODULE_A_PATTERN {index}")
        out.append({"pattern": index, "heading": heading, "notes": names, "tab": tab, "placements": events,
                    "straight": {"printed_grid": straight_count, "eighth_slot_attacks": list(range(1, 9)), "attack_count": 8},
                    "shuffle": {"printed_grid": shuffle_count, "triplet_mask": shuffle_mask, "attack_count": 8},
                    "core_attacks": 16})
    return out


def parse_b(block: list[str], pdf: list[str]) -> list[dict]:
    out = []
    expected = (4, 8, 4, 4, 6, 6, 5, 3)
    for index, expected_count in enumerate(expected, 1):
        heading = next((line for line in block if line.startswith(f"{index}. ")), None)
        if heading is None:
            raise CandidateError(f"MODULE_B_CARD {index}")
        line = block[block.index(heading)+1]
        masks = parse_masks(line)
        if attacks(masks) != expected_count or f"{expected_count} attacks" not in line:
            raise CandidateError(f"MODULE_B_MASK_COUNT {index}")
        if not any(f"{expected_count} attacks" == item for item in pdf):
            raise CandidateError(f"PDF_MODULE_B_COUNT {index}")
        for bar_index, mask in enumerate(masks):
            if index == 8 and bar_index == 1:
                if "|| X..|" not in "\n".join(pdf):
                    raise CandidateError("PDF_MODULE_B_PICKUP_MASK")
                continue
            if mask["literal"] not in "\n".join(pdf):
                raise CandidateError(f"PDF_MODULE_B_MASK {index}")
        out.append({"card": index, "heading": heading, "printed_mask": line, "bars": masks,
                    "root": {"string": "E", "fret": 5, "note": "A"}, "core_attacks": expected_count,
                    "practice_repetitions": 4})
    return out


def parse_c(block: list[str], pdf: list[str]) -> dict:
    passes = []
    for index, expected_total in enumerate((12, 48, 48), 1):
        heading = next((line for line in block if line.startswith(f"PASS {index} - ")), None)
        if heading is None:
            raise CandidateError(f"MODULE_C_PASS {index}")
        start = block.index(heading)
        mask = parse_masks(block[start+1])
        if len(mask) != 1 or attacks(mask)*12 != expected_total:
            raise CandidateError(f"MODULE_C_PASS_MASK {index}")
        pdf_has(pdf, block[start+1], f"C pass {index}")
        passes.append({"pass": index, "heading": heading, "mask": mask[0], "per_bar_attacks": attacks(mask),
                       "bars": 12, "core_attacks": expected_total})
    chord_line = next(line for line in block if line.startswith("Chord:"))
    root_line = next(line for line in block if line.startswith("Root:"))
    chords = re.findall(r"A7|D7|E7", chord_line)
    roots = re.findall(r"E5|A5|A7", root_line)
    if tuple(chords) != CHORDS or tuple(roots) != tuple(f"{s}{f}" for s, f in ROOTS):
        raise CandidateError("MODULE_C_FORM_ROUTE")
    if pdf[41:53] != list(CHORDS) or pdf[54:66] != roots:
        raise CandidateError("PDF_MODULE_C_FORM_ROUTE")
    return {"passes": passes, "form": [{"bar": i+1, "chord": chord, "root_string": ROOTS[i][0], "root_fret": ROOTS[i][1]}
                                       for i, chord in enumerate(CHORDS)],
            "bar_12_turnaround": "E7", "bar_12_closure_option": "A7", "core_attacks": 108}


def parse_d(block: list[str], pdf: list[str]) -> list[dict]:
    mask_headings = ("TIMING MASK A - BEAT-4 SHUFFLE PAIR", "TIMING MASK B - LATE TRIPLET", "TIMING MASK C - TWO-BEAT PICKUP")
    masks = []
    for heading in mask_headings:
        source = block[block.index(heading)+1]
        source_bar, next_bar = source.split("Next bar", 1)
        source_mask = parse_bar_mask(source_bar.split("Source bar", 1)[1])
        next_mask = parse_bar_mask(next_bar)
        if len(source_mask["attack_slots"]) != 2 or next_mask["attack_slots"] != [[1, 1]]:
            raise CandidateError(f"MODULE_D_PICKUP_MASK {heading}")
        masks.append({"heading": heading, "source_bar": source_mask, "next_bar": next_mask})
    out = []
    for index, (source, destination) in enumerate((("A7", "D7"), ("A7", "E7"), ("E7", "A7")), 1):
        heading = f"TRANSITION {index} - {source} TO {destination}"
        start = block.index(heading)
        note_line, degree_line, tab = block[start+1:start+4]
        names = note_tokens(note_line.removeprefix("Notes: "))
        placements = tab_events([tab])
        validate_pitch_sequence(names, placements, f"D{index}")
        root = (("D", 12, "D"), ("A", 7, "E"), ("G", 14, "A"))[index-1]
        if len(names) != 3 or (placements[-1]["string"], placements[-1]["fret"], names[-1]) != root:
            raise CandidateError(f"MODULE_D_DESTINATION {index}")
        if block[start+4] != "Apply timing masks A, B, and C. 9 attacks total.":
            raise CandidateError(f"MODULE_D_COUNT {index}")
        if f"Notes: {'-'.join(names)}" not in pdf or f"Tab {tab}" not in pdf:
            raise CandidateError(f"PDF_MODULE_D_TRANSITION {index}")
        out.append({"transition": index, "source_chord": source, "destination_chord": destination,
                    "printed": block[start:start+5], "notes": names, "degrees": degree_line,
                    "placements": placements, "timing_masks": masks, "core_attacks": 9,
                    "destination_on_next_bar_beat_1": True})
    return out


def parse_e(block: list[str], pdf: list[str]) -> list[dict]:
    out = []
    for index, expected_count in enumerate((6, 4, 2, 4, 6, 6), 1):
        heading = next((line for line in block if line.startswith(f"{index}. ")), None)
        if heading is None:
            raise CandidateError(f"MODULE_E_CARD {index}")
        start = block.index(heading)
        masks = parse_masks(block[start+1])
        following = block[start+2:]
        note_offset = next((j for j, line in enumerate(following) if line.startswith("Notes: ")), None)
        if note_offset is None:
            raise CandidateError(f"MODULE_E_NOTES {index}")
        tabs = following[:note_offset]
        names = note_tokens(following[note_offset].removeprefix("Notes: "))
        placements = tab_events(tabs)
        validate_pitch_sequence(names, placements, f"E{index}")
        if len(masks) != 2 or attacks(masks) != expected_count or len(names) != expected_count:
            raise CandidateError(f"MODULE_E_COUNT {index}")
        if not any(line == block[start+1] for line in pdf):
            raise CandidateError(f"PDF_MODULE_E_MASK {index}")
        for tab in tabs:
            pdf_has(pdf, tab, f"E card {index} tab")
        out.append({"card": index, "heading": heading, "printed": block[start:start+3+note_offset],
                    "bars": masks, "notes": names, "placements": placements, "core_attacks": expected_count})
    return out


def parse_f(block: list[str], pages: list[list[str]]) -> list[dict]:
    out = []
    headings = [next((line for line in block if line.startswith(f"STUDY {index} - ")), None) for index in range(1, 4)]
    if any(heading is None for heading in headings):
        raise CandidateError("MODULE_F_STUDY_HEADINGS")
    boundaries = [block.index(heading) for heading in headings] + [block.index("TRANSFORMATION PASSES")]
    for index, expected_count in enumerate((16, 18, 16), 1):
        section = block[boundaries[index-1]:boundaries[index]]
        if f"/ {expected_count} ATTACKS" not in section[0]:
            raise CandidateError(f"MODULE_F_PRINTED_COUNT {index}")
        if index == 1:
            bar_lines = [line for line in section if re.match(r"^Bar [1-8] ", line)]
            if len(bar_lines) != 8:
                raise CandidateError("MODULE_F_STUDY1_BAR_COUNT")
            bars = []
            for bar_number, line in enumerate(bar_lines, 1):
                placements = tab_events([line])
                tail = line.rsplit("|", 1)[1]
                names = note_tokens(tail)
                validate_pitch_sequence(names, placements, f"F1 bar {bar_number}")
                if len(names) != 2:
                    raise CandidateError(f"MODULE_F_STUDY1_BAR_NOTES {bar_number}")
                bars.append({"bar": bar_number, "printed": line, "notes": names, "placements": placements})
        else:
            tab_lines = [line for line in section if re.match(r"^B[15] ", line)]
            if len(tab_lines) != 2:
                raise CandidateError(f"MODULE_F_STUDY{index}_TAB_LINES")
            bars = []
            for half, tab_line in enumerate(tab_lines):
                source_index = section.index(tab_line)
                note_line = section[source_index+1]
                names = note_tokens(note_line)
                placements = tab_events([tab_line])
                validate_pitch_sequence(names, placements, f"F{index} {'call' if half == 0 else 'answer'}")
                count = 9 if index == 2 else 8
                if len(names) != count:
                    raise CandidateError(f"MODULE_F_STUDY{index}_HALF_COUNT")
                bars.append({"half": "call" if half == 0 else "response", "printed_tab": tab_line,
                             "printed_notes": note_line, "notes": names, "placements": placements,
                             "bar_numbers": [1, 2, 3, 4] if half == 0 else [5, 6, 7, 8]})
        total = sum(len(part["notes"]) for part in bars)
        if total != expected_count:
            raise CandidateError(f"MODULE_F_TOTAL {index}")
        page_numbers = [8] if index in (1, 2) else [9]
        pdf_text = "\n".join(line for page_number in page_numbers for line in pages[page_number-1])
        pdf_tabs = re.findall(r"[EADGBe]\|[^|]*\|", pdf_text)
        for part in bars:
            printed = part.get("printed", part.get("printed_tab", ""))
            for tab in re.findall(r"[EADGBe]\|[^|]*\|", printed):
                signature = [(event["string"], event["fret"]) for event in tab_events([tab])]
                if not any([(event["string"], event["fret"]) for event in tab_events([pdf_tab])] == signature for pdf_tab in pdf_tabs):
                    raise CandidateError(f"PDF_MODULE_F_TAB {index}: {tab}")
        out.append({"study": index, "heading": section[0], "printed": section, "parts": bars,
                    "bars": 8, "core_attacks": expected_count})
    if not all(line in pages[8] for line in block[block.index("TRANSFORMATION PASSES")+1:block.index("TRANSFORMATION PASSES")+6]):
        raise CandidateError("PDF_MODULE_F_TRANSFORMATIONS")
    return out


def parse_g(block: list[str], pdf: list[str]) -> list[dict]:
    out = []
    for index, expected_count in enumerate((5, 4, 4), 1):
        heading = next((line for line in block if line.startswith(f"{index}. ")), None)
        if heading is None or not heading.endswith(f"/ {expected_count} ATTACKS"):
            raise CandidateError(f"MODULE_G_HEADING {index}")
        start = block.index(heading)
        hit, lead = block[start+1:start+3]
        placements = tab_events([hit, lead])
        if len(placements) != expected_count or "x" not in hit or not lead.startswith("LEAD "):
            raise CandidateError(f"MODULE_G_COUNT {index}")
        for tab in re.findall(r"[EADGBe]\|[^|]*\|", hit+" "+lead):
            pdf_has_tab(pdf, tab, f"G study {index}")
        out.append({"study": index, "heading": heading, "printed": [heading, hit, lead],
                    "hit": placements[0], "lead": placements[1:], "core_attacks": expected_count,
                    "root_hit_staccato_and_muted": True})
    heading = next((line for line in block if line.startswith("4. FOUR-BAR STOP-TIME CHAIN")), None)
    if heading != "4. FOUR-BAR STOP-TIME CHAIN / 16 ATTACKS":
        raise CandidateError("MODULE_G_CHAIN_HEADING")
    start = block.index(heading)
    bars = []
    for bar_number, chord in enumerate(("A7", "D7", "E7", "A7"), 1):
        marker = f"BAR {bar_number} - {chord}"
        position = block.index(marker, start)
        tab_lines = [block[position+1], block[position+2]]
        if bar_number == 4:
            tab_lines.append(block[position+3])
        placements = tab_events(tab_lines)
        if len(placements) != 4 or "x" not in tab_lines[0]:
            raise CandidateError(f"MODULE_G_CHAIN_BAR {bar_number}")
        for tab in re.findall(r"[EADGBe]\|[^|]*\|", " ".join(tab_lines)):
            pdf_has_tab(pdf, tab, f"G chain bar {bar_number}")
        bars.append({"bar": bar_number, "chord": chord, "printed": [marker, *tab_lines],
                     "hit": placements[0], "lead": placements[1:], "attacks": 4})
    out.append({"study": 4, "heading": heading, "bars": bars, "core_attacks": 16,
                "root_hit_staccato_and_muted": True})
    return out


def parse_h(block: list[str], pages: list[list[str]]) -> dict:
    landmark = "LANDMARK PASS - 6 ATTACKS"
    shuffle = "ROOT-SHUFFLE CHORUS - 48 ATTACKS"
    model = "MODEL TWELVE-BAR RHYTHM CHORUS - 48 ATTACKS"
    if not all(heading in block for heading in (landmark, shuffle, model)):
        raise CandidateError("MODULE_H_HEADINGS")
    landmark_play = next(line for line in block if line.startswith("Play: "))
    landmark_roots = re.findall(r"E5|A5|A7|--", landmark_play)
    expected_play = ["E5", "--", "--", "--", "A5", "--", "--", "--", "A7", "A5", "E5", "A7"]
    if landmark_roots != expected_play:
        raise CandidateError("MODULE_H_LANDMARK_ROUTE")
    pdf_landmark = pages[10]
    for bar_number, (chord, (string, fret)) in enumerate(zip(CHORDS, ROOTS, strict=True), 1):
        pdf_row = pdf_landmark[10+5*(bar_number-1):15+5*(bar_number-1)]
        if pdf_row[:4] != [str(bar_number), chord, f"{string}{fret}", "PLAY" if bar_number in (1, 5, 9, 10, 11, 12) else "count"]:
            raise CandidateError(f"PDF_MODULE_H_LANDMARK_BAR {bar_number}")
    if "Let each played root last one beat" not in "\n".join(pdf_landmark):
        raise CandidateError("PDF_MODULE_H_LANDMARK")
    shuffle_start = block.index(shuffle)
    shuffle_mask = parse_masks(block[shuffle_start+2])
    if len(shuffle_mask) != 1 or attacks(shuffle_mask) != 4 or shuffle_mask[0]["literal"] != "X.X|...|X.X|...":
        raise CandidateError("MODULE_H_SHUFFLE_MASK")
    if "Mask|X.X|...|X.X|...|  repeated for each bar" not in pages[11]:
        raise CandidateError("PDF_MODULE_H_SHUFFLE_MASK")
    if not any("mask X.X|...|X.X|...." in line for line in pages[11]):
        raise CandidateError("PDF_MODULE_H_NARRATIVE_MASK_VARIANT")
    pdf_shuffle = pages[11]
    for group, first in enumerate((7, 13, 19)):
        chords_in_table = re.findall(r"A7|D7|E7", pdf_shuffle[first+1])
        if chords_in_table != list(CHORDS[4*group:4*group+4]):
            raise CandidateError(f"PDF_MODULE_H_SHUFFLE_CHORDS {group+1}")
        e_cells = pdf_shuffle[first+2].split("|")[1:5]
        a_cells = pdf_shuffle[first+3].split("|")[1:5]
        if len(e_cells) != 4 or len(a_cells) != 4:
            raise CandidateError(f"PDF_MODULE_H_SHUFFLE_TAB_CELLS {group+1}")
        for offset, (string, fret) in enumerate(ROOTS[4*group:4*group+4]):
            if ([int(value) for value in re.findall(r"\d+", e_cells[offset])],
                [int(value) for value in re.findall(r"\d+", a_cells[offset])]) != (
                    ([fret]*4 if string == "E" else []), ([fret]*4 if string == "A" else [])):
                raise CandidateError(f"PDF_MODULE_H_SHUFFLE_ROOT {4*group+offset+1}")
    model_start = block.index(model)
    model_rows = block[model_start+2:]
    cards = []
    for bar_number, chord in enumerate(CHORDS, 1):
        marker = f"BAR {bar_number} - {chord}" + (" TURNAROUND" if bar_number == 12 else "")
        if marker not in model_rows:
            raise CandidateError(f"MODULE_H_MODEL_BAR {bar_number}")
        start = model_rows.index(marker)
        mask = parse_masks(model_rows[start+1])
        following = model_rows[start+2:]
        note_offset = next((j for j, line in enumerate(following) if line.startswith("Notes: ")), None)
        if note_offset is None:
            raise CandidateError(f"MODULE_H_MODEL_NOTES {bar_number}")
        tabs = following[:note_offset]
        names = note_tokens(following[note_offset].removeprefix("Notes: "))
        placements = tab_events(tabs)
        validate_pitch_sequence(names, placements, f"H model bar {bar_number}")
        if len(mask) != 1 or attacks(mask) != 4 or len(names) != 4:
            raise CandidateError(f"MODULE_H_MODEL_COUNT {bar_number}")
        pdf_page = pages[12]
        pdf_start = pdf_page.index(f"{bar_number} {chord}")
        if pdf_page[pdf_start+1] != model_rows[start+1]:
            raise CandidateError(f"PDF_MODULE_H_MODEL_MASK {bar_number}")
        pdf_note_index = next((i for i in range(pdf_start+2, min(pdf_start+7, len(pdf_page))) if pdf_page[i].startswith("Nte|")), None)
        if pdf_note_index is None or note_tokens(pdf_page[pdf_note_index].removeprefix("Nte|")) != names:
            raise CandidateError(f"PDF_MODULE_H_MODEL_NOTES {bar_number}")
        validate_pitch_sequence(names, tab_events(pdf_page[pdf_start+2:pdf_note_index]), f"PDF H model bar {bar_number}")
        cards.append({"bar": bar_number, "chord": chord, "mask": mask[0], "notes": names,
                      "placements": placements, "printed": model_rows[start:start+3+note_offset], "attacks": 4})
    if cards[-1]["notes"] != ["G", "F#*", "F*", "E"]:
        raise CandidateError("MODULE_H_TURNAROUND_SUPPORT")
    return {"landmark": {"played_bars": [1, 5, 9, 10, 11, 12], "play_route": landmark_roots, "core_attacks": 6},
            "root_shuffle": {"mask": shuffle_mask[0], "form": list(CHORDS), "root_locations": [f"{s}{f}" for s, f in ROOTS],
                             "bar_12_closure_option": "A7/E5", "core_attacks": 48},
            "model": {"bars": cards, "core_attacks": 48}, "core_attacks": 102}


def parse_i(block: list[str], pdf: list[str]) -> list[dict]:
    out = []
    headings = [next((line for line in block if line.startswith(f"{index}. ")), None) for index in range(1, 7)]
    if any(heading is None for heading in headings):
        raise CandidateError("MODULE_I_HEADINGS")
    boundaries = [block.index(heading) for heading in headings] + [block.index("AUDIT")]
    prior_notes: list[str] = []
    for index in range(1, 7):
        section = block[boundaries[index-1]:boundaries[index]]
        tabs = [line for line in section if re.search(r"[EADGBe]\|[^|]*\|", line)]
        placements = tab_events(tabs)
        note_line = next((line for line in section if line.startswith("Notes: ")), None)
        if index == 2:
            if "Same eight-note line; begin two beats later." not in section or not prior_notes:
                raise CandidateError("MODULE_I_SAME_LINE_RULE")
            names = prior_notes
        else:
            if note_line is None:
                raise CandidateError(f"MODULE_I_NOTES {index}")
            names = note_tokens(note_line.removeprefix("Notes: "))
        validate_pitch_sequence(names, placements, f"I{index}")
        if len(names) != 8:
            raise CandidateError(f"MODULE_I_COUNT {index}")
        if index == 1:
            prior_notes = names
        pdf_start = next((i for i, line in enumerate(pdf) if line.lower().startswith(f"{index}. ")), None)
        if pdf_start is None:
            raise CandidateError(f"PDF_MODULE_I_CARD {index}")
        next_heading = next((i for i in range(pdf_start+1, len(pdf)) if re.match(r"^[1-6]\. ", pdf[i])), len(pdf))
        pdf_section = pdf[pdf_start:next_heading]
        pdf_tabs = [line for line in pdf_section if re.search(r"[EADGBe]\|[^|]*\|", line)]
        validate_pitch_sequence(names, tab_events(pdf_tabs), f"PDF I{index}")
        if "8 attacks" not in pdf_section:
            raise CandidateError(f"PDF_MODULE_I_COUNT {index}")
        out.append({"card": index, "heading": section[0], "printed": section, "notes": names,
                    "placements": placements, "core_attacks": 8,
                    "ending_job": "tonic_A_close" if index == 5 else "pickup_next_chorus" if index == 6 else "E7_continuation"})
    if [card["notes"][-1] for card in out] != ["E", "E", "E", "E", "A", "E"] or out[5]["notes"][4] != "A":
        raise CandidateError("MODULE_I_ENDINGS")
    return out


def parse_j(block: list[str], pdf: list[str]) -> dict:
    root_line = next((line for line in block if line.startswith("A A A A | D D")), None)
    if root_line != "A A A A | D D A A | E D A E":
        raise CandidateError("MODULE_J_ROOT_ROUTE")
    root_tabs = block[block.index("Root tablature:")+1:block.index("Root tablature:")+6]
    for line in root_tabs:
        pdf_has(pdf, line, "J root tab")
    expected_clicks = (48, 24, 12, 12, 6)
    passes = []
    for index, clicks in enumerate(expected_clicks, 1):
        heading = next((line for line in block if line.startswith(f"PASS {index} - ")), None)
        if heading is None:
            raise CandidateError(f"MODULE_J_PASS {index}")
        start = block.index(heading)
        count_line = block[start+1]
        if not count_line.startswith(f"{clicks} clicks across 12 bars."):
            raise CandidateError(f"MODULE_J_CLICK_COUNT {index}")
        pdf_row = pdf[10+4*(index-1):14+4*(index-1)]
        if pdf_row[0] != str(index) or pdf_row[2] != str(clicks):
            raise CandidateError(f"PDF_MODULE_J_CLICK_COUNT {index}")
        passes.append({"pass": index, "heading": heading, "printed_clicks": clicks,
                       "bars": 12, "root_attacks": 12, "printed_instruction": count_line})
    if "Each pass contains 12 root attacks. Five passes contain 60 attacks." not in block:
        raise CandidateError("MODULE_J_TOTAL")
    if "The first note after the gap must be E at A-string fret 7." not in "\n".join(block):
        raise CandidateError("MODULE_J_RECOVERY_TARGET")
    return {"root_route": [f"{s}{f}" for s, f in ROOTS], "root_tablature": root_tabs,
            "passes": passes, "form_recovery": "\n".join(block[block.index("FORM-RECOVERY DRILL"):]),
            "core_attacks": 60}


def parse_capstone(lines: list[str], pdf: list[str]) -> dict:
    start = lines.index("LEVEL 45 CAPSTONE - THREE-CHORUS RHYTHM CIRCUIT")
    end = lines.index("PRACTICE PROGRESSION", start)
    block = lines[start:end]
    choruses = []
    for index, count in enumerate((12, 48, 48), 1):
        heading = f"CHORUS {index}"
        pos = block.index(heading)
        if f"{count} attacks." not in block[pos+1]:
            raise CandidateError(f"CAPSTONE_CHORUS_COUNT {index}")
        choruses.append({"chorus": index, "printed": block[pos:pos+2], "reused_attacks": count,
                         "bar_12": "E7_turnaround" if index < 3 else "A7_tonic_close_option"})
    if "The capstone reuses previous material and is not added to the 540-attack written workload." not in block:
        raise CandidateError("CAPSTONE_REUSE_BOUNDARY")
    if [pdf[i] for i in (14, 19, 24)] != ["12", "48", "48"]:
        raise CandidateError("PDF_CAPSTONE_COUNTS")
    if "if desired" not in choruses[2]["printed"][1] or pdf[25] != "A7 tonic close":
        raise CandidateError("CAPSTONE_BAR12_SOURCE_VARIANT")
    if "The capstone combines existing modules, so its notes are not added to the 540-attack workload." not in "\n".join(pdf):
        raise CandidateError("PDF_CAPSTONE_REUSE_BOUNDARY")
    return {"choruses": choruses, "bars": 36, "reused_attacks": 108, "included_in_written_core_540": False,
            "chorus_3_bar_12_txt": "A-tonic closing phrase if desired",
            "chorus_3_bar_12_pdf": "A7 tonic close",
            "source_text": "\n".join(block), "source_pdf_page": 16}


def build_candidate(root: Path = ROOT) -> dict:
    if root.resolve() != ROOT.resolve():
        raise CandidateError("REPOSITORY_ROOT_MISMATCH")
    proc = subprocess.run(["git", "-C", str(root), "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if proc.returncode or Path(proc.stdout.strip()).resolve() != root.resolve():
        raise CandidateError("REPOSITORY_ROOT_MISMATCH")
    sources = {kind: source_bytes(root, rel) for kind, rel in (("txt", TXT_REL), ("pdf", PDF_REL), ("map", MAP_REL))}
    for kind, data in sources.items():
        verify(data, kind)
    source_map = list(csv.DictReader(sources["map"].decode("utf-8").splitlines(), delimiter="\t"))
    rows = [row for row in source_map if row["level"] == "45"]
    if len(rows) != 1:
        raise CandidateError("SOURCE_MAP_LEVEL45_CARDINALITY")
    map_row = rows[0]
    if (map_row["txt_path"] != str(TXT_REL) or map_row["pdf_path"] != str(PDF_REL)
            or map_row["txt_sha256"] != PINS["txt"][1] or map_row["pdf_sha256"] != PINS["pdf"][1]
            or map_row["review"] != "Pending" or map_row["conversion_status"] != "not_converted"
            or any(map_row[key] != "False" for key in ("stable_ids_assigned", "runtime_eligible", "imported", "admitted"))):
        raise CandidateError("SOURCE_MAP_LEVEL45_STATE")
    lines = sources["txt"].decode("utf-8").splitlines()
    if len(lines) != 529 or lines[:2] != ["SCALE EXERCISES - SECTION V, LEVEL 45", "A BLUES SHUFFLE RHYTHM, TRIPLET PLACEMENT, AND TWELVE-BAR FORM - FIXED KEY A"]:
        raise CandidateError("TXT_HEADER_OR_LENGTH")
    reader = PdfReader(BytesIO(sources["pdf"]), strict=True)
    if len(reader.pages) != 18:
        raise CandidateError("PDF_PAGE_COUNT")
    pages = [(page.extract_text() or "").splitlines() for page in reader.pages]
    if any(f"Page {number} of 18" not in page for number, page in enumerate(pages, 1)):
        raise CandidateError("PDF_PAGE_IDENTITY")
    if "540 ATTACKS" not in pages[0][2] or "Triplet-grid legend" not in pages[1]:
        raise CandidateError("PDF_OVERVIEW")
    expected_support = ("C# = 3*", "F# = 6*", "F  = b6*", "B  = 2*/E7-5", "G# = 7*/E7-3")
    if any(not any(line.startswith(prefix) for line in lines[13:21]) for prefix in expected_support):
        raise CandidateError("TXT_SUPPORT_ROLES")
    blocks = {key: module_block(lines, key)[1] for key in MODULE_HEADINGS}
    modules = {"A": parse_a(blocks["A"], pages[2]), "B": parse_b(blocks["B"], pages[3]),
               "C": parse_c(blocks["C"], pages[4]), "D": parse_d(blocks["D"], pages[5]),
               "E": parse_e(blocks["E"], pages[6]), "F": parse_f(blocks["F"], pages),
               "G": parse_g(blocks["G"], pages[9]), "H": parse_h(blocks["H"], pages),
               "I": parse_i(blocks["I"], pages[13]), "J": parse_j(blocks["J"], pages[14])}
    actual = {key: (sum(item["core_attacks"] for item in value) if isinstance(value, list) else value["core_attacks"])
              for key, value in modules.items()}
    if actual != COUNTS or sum(actual.values()) != 540:
        raise CandidateError(f"WHOLE_LEVEL_COUNTS {actual}")
    for key, count in COUNTS.items():
        if not any(line.startswith(f"Module {key} - ") and line.endswith(f"{count} attacks") for line in lines[36:50]):
            raise CandidateError(f"TXT_WORKLOAD_COUNT {key}")
    if "TOTAL:                                   540 attacks" not in lines:
        raise CandidateError("TXT_WORKLOAD_TOTAL")
    capstone = parse_capstone(lines, pages[15])
    guidance = {"txt_intro_and_legend": "\n".join(lines[:50]),
                "txt_modules": {key: "\n".join(block) for key, block in blocks.items()},
                "txt_practice_and_mastery": "\n".join(lines[485:]),
                "pdf_triplet_legend": "\n".join(pages[1]),
                "pdf_practice_and_mastery": "\n".join(pages[16]+pages[17]),
                "core_workload_counting": "Printed core counts one pass through each authored card/pass. Module B four repetitions are practice instruction. Capstone reuses previous material and is excluded from 540."}
    return {"schema": "fathom.detached.curriculum.level045.whole.v1", "wbs": "2.3.1.1.1", "level": 45,
            "key": "A blues", "transposed": False, "permanent_pitch_pool": list(POOL),
            "temporary_support_notes": SUPPORT,
            "source": {label: {"path": str(rel), "bytes": len(sources[kind]), "sha256": digest(sources[kind])}
                       for label, kind, rel in (("txt", "txt", TXT_REL), ("pdf", "pdf", PDF_REL), ("source_map", "map", MAP_REL))},
            "canonical_id": None, "runtime_imported": False, "admitted": False,
            "whole_level_source_covered": True, "whole_level_complete": False,
            "default_form": list(CHORDS), "root_locations": [f"{string}{fret}" for string, fret in ROOTS],
            "bar_12_tonic_closure_option": "A7/E5", "modules": modules, "module_attack_counts": actual,
            "written_core_attacks": 540, "capstone": capstone,
            "timing": {"authored_symbolic_masks": True, "numeric_onset": None, "numeric_duration": None,
                       "performed_audio": None, "fixed_bpm": None},
            "guidance": guidance,
            "source_discrepancies": [
                {"kind": "pdf_abbreviated_second_bar", "source_ref": "L45-PDF-p4-card8",
                 "txt": "Bar 2 Mask|X..|...|...|...|", "pdf": "|| X..|",
                 "handling": "Preserve the complete TXT second-bar mask and the PDF abbreviation; both print three attacks across the two bars."},
                {"kind": "pdf_narrative_extra_rest_dot", "source_ref": "L45-PDF-p12-root-shuffle",
                 "pdf_prose": "X.X|...|X.X|....", "txt_and_pdf_grid": "Mask|X.X|...|X.X|...|",
                 "handling": "Use the four three-slot beats of the printed grid/table; retain the narrative typo as provenance."},
                {"kind": "capstone_final_bar_option_vs_requirement", "source_ref": "L45-TXT1-capstone / L45-PDF-p16",
                 "txt": "Replace bar 12 with an A-tonic closing phrase if desired.", "pdf": "A7 tonic close",
                 "handling": "Preserve both instructions; detached candidate does not adjudicate whether chorus 3 must close on A."},
            ]}


def write_candidate(path: Path, root: Path = ROOT) -> str:
    allowed = (root / BUILD_REL).resolve()
    if path.is_symlink() or path.resolve().parent != allowed or path.suffix != ".json":
        raise CandidateError("OUTPUT_PATH_OUTSIDE_DETACHED_BUILD")
    if path.exists():
        raise CandidateError("OUTPUT_EXISTS")
    data = (json.dumps(build_candidate(root), indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return digest(data)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(write_candidate(args.output))


if __name__ == "__main__":
    main()
