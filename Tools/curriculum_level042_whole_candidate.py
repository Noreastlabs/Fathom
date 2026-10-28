#!/usr/bin/env python3
"""Build a detached, source-reconciled whole-Level-42 articulation candidate."""

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
STEM = "Scale_Exercises_Section_V_Level_42_A_Minor_Pentatonic_Horizontal_Movement_and_Articulation_Fixed_Key_A"
TXT_REL = Path(f"Notes/music/guitar project/TXT version/{STEM}.txt")
PDF_REL = Path(f"Notes/music/guitar project/PDF version/{STEM}.pdf")
MAP_REL = Path("Results/parallel-01/exercises/inventory/20260922T180500Z-2.3-curriculum-v1-source-inventory-evidence/curriculum-source-map.tsv")
BUILD_REL = Path("Build/parallel-08/2.3.1.1.1-level042-whole-r01")
PINS = {"txt": (30783, "4d658466a731cf3de48c02cd8694651a3294d27af588a344926aa85e2d64f65b"),
        "pdf": (45764, "fed7a629ecf0c0ff4e7015187ce858a21d333409aedc37bde7b6561b05b5c61d"),
        "map": (68536, "f526ff4d9ce3bceaf9a7cc581a3ac2aee2c74917eba984dd57913adba574c123")}
STRINGS = ("E", "A", "D", "G", "B", "e")
NAMES = ("LOW E", "A", "D", "G", "B", "HIGH E")
DISPLAY = ("Low E", "A", "D", "G", "B", "High e")
FRETS = ((5, 8, 10, 12, 15, 17), (5, 7, 10, 12, 15, 17),
         (5, 7, 10, 12, 14, 17), (5, 7, 9, 12, 14, 17),
         (5, 8, 10, 13, 15, 17), (5, 8, 10, 12, 15, 17))
DEGREES = (("1", "b3", "4", "5", "b7", "1"), ("4", "5", "b7", "1", "b3", "4"),
           ("b7", "1", "b3", "4", "5", "b7"), ("b3", "4", "5", "b7", "1", "b3"),
           ("5", "b7", "1", "b3", "4", "5"), ("1", "b3", "4", "5", "b7", "1"))
FINGERS = ((1, 4, 1, 3, 1, 3), (1, 3, 1, 3, 1, 3),
           (1, 3, 1, 3, 1, 4), (1, 3, 1, 4, 1, 4),
           (1, 4, 1, 4, 1, 3), (1, 4, 1, 3, 1, 3))
NOTE = {"1": "A", "b3": "C", "4": "D", "5": "E", "b7": "G"}
PITCH = {"A": 9, "C": 0, "D": 2, "E": 4, "G": 7, "C#": 1}
OPEN = {"E": 4, "A": 9, "D": 2, "G": 7, "B": 11, "e": 4}
TAB_ORDER = ("e", "B", "G", "D", "A", "E")
COUNTS = {"A": (72, 72), "B": (96, 96), "C": (144, 96), "D": (120, 60),
          "E": (120, 24), "F": (65, 52), "G": (8, 8), "H": (43, 20)}


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


def event(string: str, fret: int, degree: str, name: str, articulation: str = "picked",
          picked: bool = True, finger: int | None = None) -> dict:
    if NOTE.get(degree) != name or (OPEN[string] + fret) % 12 != PITCH[name]:
        raise CandidateError(f"PITCH_OR_DEGREE_MISMATCH {string}{fret} {name}({degree})")
    return {"string": string, "fret": fret, "degree": degree, "note": name,
            "finger": finger, "articulation": articulation, "pick_attack": picked,
            "onset_q": None, "duration_q": None}


def lane_event(index: int, position: int, articulation: str = "picked", picked: bool = True,
               finger: int | None = None) -> dict:
    degree = DEGREES[index][position]
    return event(STRINGS[index], FRETS[index][position], degree, NOTE[degree], articulation, picked, finger)


def row_tokens(row: str, label: str, count: int, pattern: str) -> list[str]:
    if not row.startswith(label + "|"):
        raise CandidateError(f"ROW_LABEL_MISMATCH {label}: {row}")
    values = re.findall(pattern, row.split("|", 1)[1])
    if len(values) != count:
        raise CandidateError(f"ROW_COUNT_MISMATCH {label}: {len(values)} != {count}")
    return values


def validate_rows(name_row: str, degree_row: str, tab_row: str, expected: list[dict],
                  finger_row: str | None = None, pick_row: str | None = None) -> None:
    count = len(expected)
    names = row_tokens(name_row, "Nte", count, r"[ACDEG]")
    degrees = row_tokens(degree_row, "Deg", count, r"b3|b7|[145]")
    tab_label = f"  {expected[0]['string']}"
    frets = [int(v) for v in row_tokens(tab_row, tab_label, count, r"\d+")]
    fingers = None if finger_row is None else [int(v) for v in row_tokens(finger_row, "Fng", count, r"[1-4]")]
    if pick_row is not None and row_tokens(pick_row, "Pck", count, r"[DU]") != ["D", "U"] * (count // 2):
        raise CandidateError("PRINTED_PICK_ROW_MISMATCH")
    for i, item in enumerate(expected):
        actual = (names[i], degrees[i], frets[i], None if fingers is None else fingers[i])
        wanted = (item["note"], item["degree"], item["fret"], None if fingers is None else item["finger"])
        if actual != wanted:
            raise CandidateError(f"PRINTED_EVENT_MISMATCH {item['string']} note={i+1}: {actual} != {wanted}")


def require_pdf_rows(page: list[str], heading: str, rows: list[str]) -> None:
    start = next((i for i, line in enumerate(page) if line.lower().startswith(heading.lower())), None)
    if start is None:
        raise CandidateError(f"PDF_CARD_MISSING {heading}")
    for row in rows:
        if row not in page[start:]:
            raise CandidateError(f"PDF_ROW_MISMATCH {heading}: {row}")


def parse_a(lines: list[str], pages: list[list[str]]) -> list[dict]:
    out = []
    for index, name in enumerate(NAMES):
        heading = next((line for line in lines if line.startswith(f"{name} STRING - 12-NOTE UP/DOWN CELL - STATIONS ")), None)
        if heading is None:
            raise CandidateError(f"MODULE_A_HEADING {name}")
        start = lines.index(heading)
        block = lines[start:start+11]
        positions = list(range(6)) + list(range(5, -1, -1))
        notes = [lane_event(index, p, finger=FINGERS[index][p]) for p in positions]
        active = block[4+TAB_ORDER.index(STRINGS[index])]
        validate_rows(block[1], block[2], active, notes, finger_row=block[3])
        stations = " | ".join(f"{FRETS[index][j]}-{FRETS[index][j+1]}" for j in (0, 2, 4))
        if not heading.endswith("STATIONS " + stations) or block[-1] != "Rule: equal volume, silent relocation, D-start and U-start passes.":
            raise CandidateError(f"MODULE_A_STATIONS_OR_RULE {name}")
        for row_string in TAB_ORDER:
            row = block[4+TAB_ORDER.index(row_string)]
            if not row.startswith(f"  {row_string}|") or (row_string != STRINGS[index] and re.search(r"\d", row)):
                raise CandidateError(f"MODULE_A_TAB_ROW {name} {row_string}")
        page_number = 3 + index // 3
        require_pdf_rows(pages[page_number-1], f"{DISPLAY[index]} string - stations {stations}", block[1:10])
        out.append({"lane": STRINGS[index], "source_txt_lines": [start+1, start+11], "source_pdf_page": page_number,
                    "stations": [list(FRETS[index][j:j+2]) for j in (0, 2, 4)],
                    "silent_shift_after_note_ordinals": [2, 4, 8, 10], "no_slide": True,
                    "printed": block, "events": notes})
    return out


def parse_b(lines: list[str], pages: list[list[str]]) -> list[dict]:
    out = []
    for index, name in enumerate(NAMES):
        heading = f"{name} STRING - FOUR INCREASING-DISTANCE TARGETS"
        start = lines.index(heading)
        block = lines[start:start+8]
        positions = [p for target in range(2, 6) for p in (0, target, target, 0)]
        notes = [lane_event(index, p, finger=1) for p in positions]
        validate_rows(block[2], block[3], block[4], notes, pick_row=block[5])
        launch = notes[0]
        if block[1] != f"Launch: {launch['note']}({launch['degree']}) fret {launch['fret']}; no slide; first pass uses finger 1 on every note.":
            raise CandidateError(f"MODULE_B_LAUNCH {name}")
        targets = []
        for target_position in range(2, 6):
            target = lane_event(index, target_position)
            targets.append({"note": target["note"], "degree": target["degree"], "fret": target["fret"],
                            "distance_frets": target["fret"]-launch["fret"]})
        target_line = "Targets: " + " | ".join(f"{t['note']}({t['degree']})@{t['fret']} +{t['distance_frets']}" for t in targets)
        if block[6] != target_line or block[7] != "After the printed pass, begin at the upper endpoint and mirror the target order downward.":
            raise CandidateError(f"MODULE_B_TARGETS_OR_MIRROR {name}")
        page_number = 5 + index // 3
        require_pdf_rows(pages[page_number-1], f"{DISPLAY[index]} string - launch {launch['note']}({launch['degree']}) fret {launch['fret']}", block[2:7])
        out.append({"lane": STRINGS[index], "source_txt_lines": [start+1, start+8], "source_pdf_page": page_number,
                    "launch": launch, "targets": targets, "upper_endpoint_mirror": "instruction_only",
                    "no_slide": True, "printed": block, "events": notes})
    return out


def split_seam_row(row: str) -> tuple[str, str, str, str, int]:
    match = re.fullmatch(r"(Low E|High e|A|D|G|B)\s+([EADGBe]\|[^|]+\|)\s+(\S+)\s+(\S+)\s+([34])", row.strip())
    if match is None:
        raise CandidateError(f"SEAM_ROW_FORMAT {row}")
    lane, tab, degree_path, note_path, finger = match.groups()
    return lane, tab, degree_path, note_path, int(finger)


def parse_seams(lines: list[str], pages: list[list[str]], module: str) -> list[dict]:
    out = []
    for seam in range(4):
        arrow = "->" if module == "C" else "<->"
        heading = f"SEAM P{seam+1} {arrow} P{seam+2}"
        start = lines.index(heading)
        page_number = (7 if module == "C" else 11) + seam // 2
        page = pages[page_number-1]
        pdf_start = next((i for i, line in enumerate(page) if line == heading), None)
        if pdf_start is None:
            raise CandidateError(f"PDF_SEAM_MISSING {module} {heading}")
        if not lines[start+1].startswith("String | Tablature"):
            raise CandidateError(f"SEAM_HEADER {module} {heading}")
        for index, display in enumerate(DISPLAY):
            row = lines[start+2+index]
            lane, tab, degree_path, note_path, finger = split_seam_row(row)
            pdf_parts = split_seam_row(page[pdf_start+2+index])
            if lane != display or pdf_parts != (lane, tab, degree_path, note_path, finger):
                raise CandidateError(f"PDF_SEAM_ROW {module} {heading} {display}")
            if module == "C":
                positions = [seam, seam+1, seam+2, seam+2, seam+1, seam]
                picked = [True, True, False, True, False, True]
                articulations = ["picked", "picked", "slide_up_arrival", "picked", "slide_down_arrival", "picked"]
                frets = [FRETS[index][p] for p in positions]
                expected_tab = f"{STRINGS[index]}|{frets[0]}--{frets[1]}/{frets[2]}--{frets[3]}\\{frets[4]}--{frets[5]}--|"
                expected_degree_path = f"{DEGREES[index][seam]}-{DEGREES[index][seam+1]}/{DEGREES[index][seam+2]}-{DEGREES[index][seam+2]}\\{DEGREES[index][seam+1]}-{DEGREES[index][seam]}"
                names = [NOTE[DEGREES[index][p]] for p in positions]
                expected_note_path = f"{names[0]}-{names[1]}/{names[2]}-{names[3]}\\{names[4]}-{names[5]}"
                expected_finger = 3 if frets[2]-frets[1] == 2 else 4
            else:
                positions = [seam, seam+1, seam+2, seam+1, seam]
                picked = [True, False, False, False, False]
                articulations = ["picked", "hammer_on", "slide_up_arrival", "slide_down_arrival", "pull_off"]
                frets = [FRETS[index][p] for p in positions]
                expected_tab = f"{STRINGS[index]}|{frets[0]}h{frets[1]}/{frets[2]}\\{frets[3]}p{frets[4]}|"
                expected_degree_path = "-".join(DEGREES[index][p] for p in positions)
                expected_note_path = "-".join(NOTE[DEGREES[index][p]] for p in positions)
                expected_finger = 3 if frets[1]-frets[0] == 2 else 4
            if (tab, degree_path, note_path, finger) != (expected_tab, expected_degree_path, expected_note_path, expected_finger):
                raise CandidateError(f"SEAM_PATH_OR_FINGER {module} {heading} {display}")
            notes = [lane_event(index, p, articulations[j], picked[j]) for j, p in enumerate(positions)]
            out.append({"seam": heading.removeprefix("SEAM "), "lane": STRINGS[index], "source_txt_line": start+3+index,
                        "source_pdf_page": page_number, "work_finger": finger,
                        "printed": {"row": row, "tab": tab, "degree_path": degree_path, "note_path": note_path},
                        "events": notes})
        footer = "Timing rule: do not add an attack at the slide arrival; keep both directions equal in volume." if module == "C" else "One phrase = five sounding tones / one pick attack."
        if lines[start+8] != footer:
            raise CandidateError(f"SEAM_FOOTER {module} {heading}")
        pdf_footer = "Six sounding tones / four attacks; every slide arrival lands on the subdivision." if module == "C" else "Five tones from one attack; no extra pick at either slide arrival."
        if page[pdf_start+8] != pdf_footer:
            raise CandidateError(f"PDF_SEAM_FOOTER {module} {heading}")
    return out


def parse_d(lines: list[str], pages: list[list[str]]) -> list[dict]:
    out = []
    for position in range(5):
        prefix = f"P{position+1} - "
        heading = next((line for line in lines if line.startswith(prefix) and " - frets " in line), None)
        if heading is None:
            raise CandidateError(f"MODULE_D_HEADING {position+1}")
        start = lines.index(heading)
        block = lines[start:start+9]
        page_number = 9 if position < 3 else 10
        page = pages[page_number-1]
        pdf_heading = heading + " - 24 tones / 12 attacks"
        if pdf_heading not in page or block[1] not in page:
            raise CandidateError(f"PDF_MODULE_D_HEADER {position+1}")
        summary = block[1].split(" | ")
        if len(summary) != 6:
            raise CandidateError(f"MODULE_D_SUMMARY_COUNT {position+1}")
        events = []
        for index, chunk in enumerate(summary):
            match = re.fullmatch(r"([EADGBe]):(\d+)h(\d+)/(\d+)p(\d+) ([ACDEG])-([ACDEG]) (b3|b7|1|4|5)-(b3|b7|1|4|5)", chunk)
            if match is None:
                raise CandidateError(f"MODULE_D_SUMMARY_FORMAT {position+1} {chunk}")
            string, lower, upper, upper_again, lower_again, low_name, high_name, low_degree, high_degree = match.groups()
            if (string, int(lower), int(upper), int(upper_again), int(lower_again), low_name, high_name, low_degree, high_degree) != (
                    STRINGS[index], FRETS[index][position], FRETS[index][position+1], FRETS[index][position+1], FRETS[index][position],
                    NOTE[DEGREES[index][position]], NOTE[DEGREES[index][position+1]], DEGREES[index][position], DEGREES[index][position+1]):
                raise CandidateError(f"MODULE_D_SUMMARY_PITCH {position+1} {string}")
            tab_row = block[2+TAB_ORDER.index(string)]
            if not tab_row.startswith(f" {string}|") or re.findall(r"(\d+)h(\d+)", tab_row) != [(lower, upper)] or re.findall(r"(\d+)p(\d+)", tab_row) != [(upper, lower)]:
                raise CandidateError(f"MODULE_D_TAB {position+1} {string}")
            events.extend([lane_event(index, position, "picked", True), lane_event(index, position+1, "hammer_on", False)])
        for index in range(5, -1, -1):
            events.extend([lane_event(index, position+1, "picked", True), lane_event(index, position, "pull_off", False)])
        if len(events) != 24 or sum(e["pick_attack"] for e in events) != 12:
            raise CandidateError(f"MODULE_D_COUNTS {position+1}")
        if block[-1] != "Attack cycle: complete one D-start pass and one U-start pass through the twelve actual attacks.":
            raise CandidateError(f"MODULE_D_ATTACK_RULE {position+1}")
        for row in block[2:8]:
            if row not in page:
                raise CandidateError(f"PDF_MODULE_D_TAB {position+1}")
        out.append({"position": position+1, "source_txt_lines": [start+1, start+9], "source_pdf_page": page_number,
                    "printed": block, "events": events, "attack_cycle": "alternate_actual_attacks_only"})
    return out


def parse_f(lines: list[str], pages: list[list[str]]) -> list[dict]:
    out = []
    sections = (("whole_step", "WHOLE-STEP CORE CELL", 9, 13),
                ("blue_third", "BLUE-THIRD SHADE - C TOWARD C#", 4, 14))
    for kind, heading, count, page_number in sections:
        start = lines.index(heading)
        rows = [line for line in lines[start+1:] if re.match(r"^(?:G|B|High e)\s+(?:G|B|e)\|", line)][:count]
        if len(rows) != count:
            raise CandidateError(f"MODULE_F_SITE_COUNT {kind}")
        page = pages[page_number-1]
        for index, raw in enumerate(rows):
            fields = re.split(r"\s{2,}", raw.strip())
            if len(fields) != 3 or fields[0] not in ("G", "B", "High e"):
                raise CandidateError(f"MODULE_F_ROW_FORMAT {kind} {index+1}")
            label, tab, descriptor = fields
            string = "e" if label == "High e" else label
            match = re.fullmatch(rf"{string}\|--(?P<target>\d+)----(?P<source>\d+)b\((?P=target)\)----(?P=source)b{'<' if kind == 'blue_third' else ''}\((?P=target)\)r(?P=source)----(?P<final>\d+)~~~~--\|", tab)
            if match is None:
                raise CandidateError(f"MODULE_F_TAB_FORMAT {kind} {index+1}")
            target_fret, source_fret, final_fret = (int(match.group(key)) for key in ("target", "source", "final"))
            if kind == "whole_step":
                descriptor_match = re.fullmatch(r"([ACDEG])\((b3|b7|1|4|5)\) -> ([ACDEG])\((b3|b7|1|4|5)\)", descriptor)
                if descriptor_match is None:
                    raise CandidateError(f"MODULE_F_DESCRIPTOR {kind} {index+1}")
                source_name, source_degree, target_name, target_degree = descriptor_match.groups()
                if NOTE[source_degree] != source_name or NOTE[target_degree] != target_name or final_fret != target_fret or target_fret-source_fret != 2:
                    raise CandidateError(f"MODULE_F_TARGET {kind} {index+1}")
                if (OPEN[string]+source_fret)%12 != PITCH[source_name] or (OPEN[string]+target_fret)%12 != PITCH[target_name]:
                    raise CandidateError(f"MODULE_F_PITCH {kind} {index+1}")
                if f"{label}: {descriptor}" not in page or tab not in page:
                    raise CandidateError(f"PDF_MODULE_F_SITE {kind} {index+1}")
                articulations = ["fretted_target", "full_bend_to_target", "repeat_full_bend", "release_to_source", "target_vibrato"]
                pitch_labels = [target_name, target_name, target_name, source_name, target_name]
            else:
                if descriptor != "C(b3) toward C#(3 boundary)" or target_fret-source_fret != 1 or final_fret != source_fret:
                    raise CandidateError(f"MODULE_F_BLUE_BOUNDARY {index+1}")
                if (OPEN[string]+source_fret)%12 != PITCH["C"] or (OPEN[string]+target_fret)%12 != PITCH["C#"]:
                    raise CandidateError(f"MODULE_F_BLUE_PITCH {index+1}")
                if tab not in page or f"{label} - C fret {source_fret} toward C# fret {target_fret}" not in page:
                    raise CandidateError(f"PDF_MODULE_F_BLUE_SITE {index+1}")
                articulations = ["fretted_C_sharp_ceiling", "full_half_step_bend_to_C_sharp", "blue_shade_below_C_sharp", "release_to_C", "C_vibrato"]
                pitch_labels = ["C#", "C#", "between C and C#", "C", "C"]
            events = [{"ordinal": j+1, "articulation": articulation, "pitch_label": pitch_labels[j],
                       "pick_attack": j != 3, "onset_q": None, "duration_q": None}
                      for j, articulation in enumerate(articulations)]
            out.append({"kind": kind, "string": string, "source_fret": source_fret, "target_fret": target_fret,
                        "target_is_pentatonic_degree": kind == "whole_step", "source_txt_line": lines.index(raw)+1,
                        "source_pdf_page": page_number, "printed": {"row": raw, "tab": tab, "descriptor": descriptor},
                        "events": events})
    return out


def parse_g(lines: list[str], pages: list[list[str]]) -> list[dict]:
    start = lines.index("MODULE G - A-ROOT VIBRATO MAP")
    rows = lines[start+2:start+10]
    expected_sites = (("Low E", "E", 5), ("D", "D", 7), ("B", "B", 10), ("A", "A", 12),
                      ("G", "G", 14), ("Low E", "E", 17), ("High e", "e", 5), ("High e", "e", 17))
    page = pages[14]
    out = []
    for index, (row, (label, string, fret)) in enumerate(zip(rows, expected_sites, strict=True)):
        if not re.fullmatch(rf"{re.escape(label)}\s+fret\s+{fret}\s+A degree 1\s+hold four beats with narrow wrist vibrato", row):
            raise CandidateError(f"MODULE_G_ROOT {index+1}")
        if f"{label} fret {fret}" not in page or f"{string}|--{fret}~~~~~~~~--|" not in page:
            raise CandidateError(f"PDF_MODULE_G_ROOT {index+1}")
        out.append({"string": string, "fret": fret, "degree": "1", "note": "A",
                    "source_txt_line": start+3+index, "source_pdf_page": 15, "printed": row,
                    "counted_sounding_events": 1, "pick_attacks": 1,
                    "vibrato_pulses": "instruction_only", "onset_q": None, "duration_q": None})
    if not lines[start+10].startswith("Pass 1: four pulses") or not lines[start+11].startswith("Every pulse returns"):
        raise CandidateError("MODULE_G_PULSE_GUIDANCE")
    return out


def parse_h(lines: list[str], pages: list[list[str]]) -> list[dict]:
    out = []
    for position, counted in enumerate((8, 8, 9, 9, 9), 1):
        prefix = f"{position}. P{position} - "
        heading = next((line for line in lines if line.startswith(prefix) and line.endswith(" - 4 PICK ATTACKS")), None)
        if heading is None:
            raise CandidateError(f"MODULE_H_HEADING {position}")
        start = lines.index(heading)
        block = lines[start:start+10]
        if len(block) != 10 or block[9] != f"Counted sounding tones: {counted}" or not block[7].startswith("Degrees: ") or not block[8].startswith("Notes:   "):
            raise CandidateError(f"MODULE_H_BLOCK {position}")
        if [line[:2] for line in block[1:7]] != ["e|", "B|", "G|", "D|", "A|", "E|"]:
            raise CandidateError(f"MODULE_H_TAB_ORDER {position}")
        root_string, root_fret = (("D", 7), ("B", 10), ("B", 10), ("A", 12), ("e", 17))[position-1]
        root_row = block[1+TAB_ORDER.index(root_string)]
        if not re.search(rf"{root_fret}~{{3,4}}", root_row):
            raise CandidateError(f"MODULE_H_FINAL_ROOT {position}")
        degrees = [part.strip() for part in block[7].removeprefix("Degrees: ").split(" | ")]
        names = [part.strip() for part in block[8].removeprefix("Notes:   ").split(" | ")]
        if len(degrees) != 4 or len(names) != 4:
            raise CandidateError(f"MODULE_H_GROUP_COUNT {position}")
        expected_group_counts = [3, 2, 2, 1] if position <= 2 else [3, 2, 3, 1] if position == 4 else [3, 3, 2, 1]
        if sum(expected_group_counts) != counted or names[-1] != "A" or degrees[-1] != "1":
            raise CandidateError(f"MODULE_H_COUNT_OR_ROOT {position}")
        # The bend/shade-release group has three pitch words but two counted events.
        # Preserve the printed wording rather than assigning invented event onsets.
        if ("shade-to-3-release-b3" if position in (1, 2, 4) else "bend-to-1-release-b7") not in degrees[2 if position in (3, 5) else 1 if position == 4 else 2]:
            raise CandidateError(f"MODULE_H_BEND_GROUP {position}")
        page_number = 16 if position <= 3 else 17
        page = pages[page_number-1]
        pdf_heading = heading.replace(" - 4 PICK ATTACKS", " - 4 attacks")
        if pdf_heading not in page or any(row not in page for row in block[1:7]) or block[7].removeprefix("Degrees: ") not in page or block[8].removeprefix("Notes:   ") not in page:
            raise CandidateError(f"PDF_MODULE_H_PHRASE {position}")
        groups = [{"degree_text": degree_text, "note_text": note_text, "counted_sounding_events": amount,
                   "pick_attacks": 1, "onset_q": None, "duration_q": None}
                  for degree_text, note_text, amount in zip(degrees, names, expected_group_counts, strict=True)]
        out.append({"position": position, "source_txt_lines": [start+1, start+10], "source_pdf_page": page_number,
                    "printed": block, "groups": groups, "counted_sounding_events": counted, "pick_attacks": 4})
    if "43 sounding tones / 20 attacks" not in pages[16][29]:
        raise CandidateError("PDF_MODULE_H_LINKED_TOTAL")
    return out


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
    rows = [row for row in source_map if row["level"] == "42"]
    if len(rows) != 1:
        raise CandidateError("SOURCE_MAP_LEVEL42_CARDINALITY")
    map_row = rows[0]
    if (map_row["txt_path"] != str(TXT_REL) or map_row["pdf_path"] != str(PDF_REL)
            or map_row["txt_sha256"] != PINS["txt"][1] or map_row["pdf_sha256"] != PINS["pdf"][1]
            or map_row["review"] != "Pending" or map_row["conversion_status"] != "not_converted"
            or any(map_row[key] != "False" for key in ("stable_ids_assigned", "runtime_eligible", "imported", "admitted"))):
        raise CandidateError("SOURCE_MAP_LEVEL42_STATE")
    lines = sources["txt"].decode("utf-8").splitlines()
    if len(lines) != 473 or lines[:2] != ["SCALE EXERCISES - SECTION V, LEVEL 42", "A MINOR PENTATONIC HORIZONTAL MOVEMENT AND ARTICULATION - FIXED KEY A"]:
        raise CandidateError("TXT_HEADER_OR_LENGTH")
    reader = PdfReader(BytesIO(sources["pdf"]), strict=True)
    if len(reader.pages) != 18:
        raise CandidateError("PDF_PAGE_COUNT")
    pages = [(page.extract_text() or "").splitlines() for page in reader.pages]
    if any(f"Page {number} of 18" not in page for number, page in enumerate(pages, 1)):
        raise CandidateError("PDF_PAGE_IDENTITY")
    if pages[0][36:38] != ["CORE WORKOUT", "668 counted sounding events / 428 pick attacks"]:
        raise CandidateError("PDF_TOTALS")
    if pages[1][2] != "A C D E G  |  DEGREES 1 b3 4 5 b7" or "C# is not added to the pentatonic map" not in pages[1][-1]:
        raise CandidateError("PDF_FIXED_KEY_OR_BLUE_BOUNDARY")
    lanes = []
    for index, string in enumerate(STRINGS):
        positions = [lane_event(index, p, finger=FINGERS[index][p]) for p in range(6)]
        roots = [e["fret"] for e in positions if e["degree"] == "1"]
        expected_atlas = [DISPLAY[index], " ".join(map(str, FRETS[index])), " ".join(DEGREES[index]),
                          " ".join(NOTE[d] for d in DEGREES[index]), " ".join(map(str, FINGERS[index])),
                          ",".join(map(str, roots)) if len(roots) > 1 else str(roots[0])]
        if pages[1][12+6*index:18+6*index] != expected_atlas:
            raise CandidateError(f"PDF_ATLAS_LANE {string}")
        summary = next((line for line in lines[21:28] if line.startswith(DISPLAY[index] + " ")), None)
        if summary is None:
            raise CandidateError(f"TXT_LANE_SUMMARY {string}")
        normalized = " ".join(summary.split())
        if any(part not in normalized for part in expected_atlas[1:5]) or "roots " + expected_atlas[5] not in normalized:
            raise CandidateError(f"TXT_LANE_SUMMARY_MISMATCH {string}")
        lanes.append({"string": string, "name": DISPLAY[index], "positions": positions, "root_frets": roots,
                      "printed_txt_summary": summary, "printed_pdf_atlas": expected_atlas})
    modules = {"A": parse_a(lines, pages), "B": parse_b(lines, pages), "C": parse_seams(lines, pages, "C"),
               "D": parse_d(lines, pages), "E": parse_seams(lines, pages, "E"),
               "F": parse_f(lines, pages), "G": parse_g(lines, pages), "H": parse_h(lines, pages)}
    expected_items = {"A": 6, "B": 6, "C": 24, "D": 5, "E": 24, "F": 13, "G": 8, "H": 5}
    if {key: len(items) for key, items in modules.items()} != expected_items:
        raise CandidateError("WHOLE_LEVEL_ITEM_COUNTS")
    actual = {}
    for key, items in modules.items():
        if key in "GH":
            actual[key] = (sum(item["counted_sounding_events"] for item in items), sum(item["pick_attacks"] for item in items))
        else:
            actual[key] = (sum(len(item["events"]) for item in items), sum(sum(e["pick_attack"] for e in item["events"]) for item in items))
        if actual[key] != COUNTS[key]:
            raise CandidateError(f"MODULE_COUNT_MISMATCH {key}: {actual[key]}")
        printed = f"Module {key}: {actual[key][0]} " + ("root-vibrato holds" if key == "G" else "counted pitch events" if key == "F" else "sounding tones")
        if key in "ABCDEF" and printed not in "\n".join(lines[28:39]):
            raise CandidateError(f"TXT_PRINTED_MODULE_COUNT {key}")
    total_sounding = sum(value[0] for value in actual.values())
    total_attacks = sum(value[1] for value in actual.values())
    if (total_sounding, total_attacks) != (668, 428) or "Complete written workout: 668 counted sounding events / 428 pick attacks" not in lines:
        raise CandidateError("WHOLE_LEVEL_TOTALS")
    if "C# appears only as the upper boundary" not in "\n".join(lines[:15]) or "b<(target) = blue-third shade" not in "\n".join(lines[:21]):
        raise CandidateError("TXT_BLUE_BOUNDARY")
    guidance = {"txt_intro": "\n".join(lines[:41]),
                "txt_module_A_instruction": "\n".join(lines[40:45]),
                "txt_module_B_instruction": "\n".join(lines[118:124]),
                "txt_module_C_instruction": "\n".join(lines[178:184]),
                "txt_module_D_instruction": "\n".join(lines[224:230]),
                "txt_module_E_instruction": "\n".join(lines[280:286]),
                "txt_module_F_instruction": "\n".join(lines[326:351]),
                "txt_module_G_instruction": "\n".join(lines[350:365]),
                "txt_module_H_linked": "\n".join(lines[422:427]),
                "txt_practice_and_mastery": "\n".join(lines[427:]),
                "pdf_attack_rules": "\n".join(pages[1][54:62]),
                "pdf_bend_and_blue_boundary": "\n".join(pages[12]+pages[13]),
                "pdf_vibrato_guidance": "\n".join(pages[14]),
                "pdf_final_page": "\n".join(pages[17]),
                "cadence_counting_convention": "Each printed bend/shade-release group retains its full pitch wording and contributes two counted sounding events in the cadence totals; no separate timing or audio contour is inferred."}
    return {"schema": "fathom.detached.curriculum.level042.whole.v1", "wbs": "2.3.1.1.1", "level": 42,
            "key": "A minor pentatonic", "transposed": False, "pitch_set": ["A", "C", "D", "E", "G"],
            "source": {label: {"path": str(rel), "bytes": len(sources[kind]), "sha256": digest(sources[kind])}
                       for label, kind, rel in (("txt", "txt", TXT_REL), ("pdf", "pdf", PDF_REL), ("source_map", "map", MAP_REL))},
            "canonical_id": None, "runtime_imported": False, "admitted": False,
            "whole_level_source_covered": True, "whole_level_complete": False,
            "lanes": lanes, "modules": modules,
            "module_counts": {key: {"counted_sounding_events": value[0], "pick_attacks": value[1]} for key, value in actual.items()},
            "totals": {"counted_sounding_events": total_sounding, "pick_attacks": total_attacks},
            "picking": {"separate_starts": ["D", "U"], "alternate_actual_attacks_only": True,
                        "no_reset_within_pass_at": ["string", "station", "position", "seam", "root", "turnaround"],
                        "unpicked_articulation_new_attack": False},
            "timing": {"numeric_onset": None, "numeric_duration": None, "fixed_bpm": None,
                       "performed_pitch_curve": None, "slide_arrival_on_subdivision": True},
            "blue_third": {"C_shade_below_C_sharp": True, "C_sharp_calibration_ceiling_only": True,
                           "C_sharp_is_pentatonic_degree": False},
            "guidance": guidance, "source_discrepancies": []}


def write_candidate(path: Path, root: Path = ROOT) -> str:
    allowed = (root / BUILD_REL).resolve()
    if path.is_symlink() or path.resolve().parent != allowed or path.suffix != ".json":
        raise CandidateError("OUTPUT_PATH_OUTSIDE_DETACHED_BUILD")
    if path.exists():
        raise CandidateError("OUTPUT_EXISTS")
    candidate = build_candidate(root)
    data = (json.dumps(candidate, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
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
