#!/usr/bin/env python3
"""Build the detached, source-linked whole Level 47 color-control candidate."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
from io import BytesIO
import json
from pathlib import Path
import re
import subprocess
from typing import Any

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
STEM = "Scale_Exercises_Section_V_Level_47_A_Major_and_Minor_Pentatonic_Mixing_Chord_Aware_Color_Control_Fixed_Key_A"
TXT_REL = Path("Notes/music/guitar project/TXT version") / (STEM + ".txt")
PDF_REL = Path("Notes/music/guitar project/PDF version") / (STEM + ".pdf")
BUILD_REL = Path("Build/parallel-07/2.3.1.1.1-level047-whole-r01")
TXT_BYTES = 40258
TXT_SHA256 = "3f51b3e8ef654008b901b0b652a0331e174763da28ab9766a8fbb8bea768e554"
PDF_BYTES = 58859
PDF_SHA256 = "e5aceb9339fc0d2ffc781b7001ecf2c330bb4b0c712742c5d8c9a4d5b730e468"
STRINGS = ("E", "A", "D", "G", "B", "e")
TAB_STRINGS = tuple(reversed(STRINGS))
OPEN_MIDI = {"E": 40, "A": 45, "D": 50, "G": 55, "B": 59, "e": 64}
PC = {"A": 9, "B": 11, "C": 0, "C#": 1, "D": 2, "E": 4, "F#": 6, "G": 7, "G#": 8}
DEGREE = {"A": "1", "B": "2", "C": "b3", "C#": "3", "D": "4", "E": "5", "F#": "6", "G": "b7"}
COLOR = {"A": "C", "E": "C", "B": "M", "C#": "M", "F#": "M",
         "C": "m", "D": "m", "G": "m", "G#": "*"}
ROLE = {
    "A7": {"A": "R", "B": "9", "C": "b3", "C#": "3", "D": "11", "E": "5",
           "F#": "13", "G": "b7", "G#": "M7"},
    "D7": {"A": "5", "B": "13", "C": "b7", "C#": "M7", "D": "R", "E": "9",
           "F#": "3", "G": "11"},
    "E7": {"A": "11", "B": "5", "C": "b13", "C#": "13", "D": "b7", "E": "R",
           "F#": "9", "G": "#9", "G#": "3*"},
}
ROW_PREFIX = ("Nte|", "Deg|", "Rol|", "Col|", "Chd|", "Pos|", "Set|") + tuple(
    f"  {string}|" for string in TAB_STRINGS)
POSITION_HEAD = re.compile(r"^P([1-5]) COLOR FOUNDATION - FRETS (\d+)-(\d+) - ROOTS (.+)$")
RECOVERY = re.compile(r"^(\d{2})\. ([ADE]7): ([A-G](?:#)?) -> ([A-G](?:#)?) \(([^ ]+) -> ([^ )]+)\)$")
CHORUS_HEADS = ("MINOR-ONLY TWELVE-BAR PASS", "MAJOR-ONLY TWELVE-BAR PASS",
                "CHORD-AWARE MIXED TWELVE-BAR PASS", "MODEL MIXED-COLOR CHORUS")
EXPECTED_COUNTS = {"A": 80, "B": 72, "C": 80, "D": 80, "E": 96,
                   "F": 48, "G": 120, "H": 80, "I": 144, "J": 72}
CHORD_FORM = ("A7", "A7", "A7", "A7", "D7", "D7", "A7", "A7", "E7", "D7", "A7", "E7")
POSITION_FORM = ("P1", "P1", "P2", "P2", "P3", "P3", "P4", "P4", "P5", "P4", "P3", "P1")


class CandidateError(ValueError):
    """Pinned source, printed semantics, or output boundary failed."""


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _verify(data: bytes, size: int, sha: str, label: str) -> None:
    if len(data) != size or digest(data) != sha:
        raise CandidateError(f"PINNED_INPUT_DRIFT {label}: bytes={len(data)} sha256={digest(data)}")


def _root() -> Path:
    result = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--show-toplevel"],
                            capture_output=True, text=True)
    if result.returncode or Path(result.stdout.strip()).resolve() != ROOT.resolve():
        raise CandidateError("REPOSITORY_ROOT_MISMATCH")
    return ROOT


def _source_bytes(root: Path, rel: Path) -> bytes:
    path = root / rel
    if path.is_symlink() or not path.is_file() or path.resolve().parent != path.parent.resolve():
        raise CandidateError(f"SOURCE_PATH_INVALID {rel}")
    return path.read_bytes()


def _pdf_pages(data: bytes) -> list[list[str]]:
    try:
        reader = PdfReader(BytesIO(data))
        if len(reader.pages) != 20:
            raise CandidateError("PDF_PAGE_COUNT_INVALID")
        return [page.extract_text().splitlines() for page in reader.pages]
    except CandidateError:
        raise
    except Exception as exc:
        raise CandidateError(f"PDF_READ_FAILED {type(exc).__name__}") from exc


def _row_parts(row: str, prefix: str, segments: int, slots: int, width: int) -> list[str]:
    if not row.startswith(prefix + "|"):
        raise CandidateError(f"STAFF_PREFIX_INVALID {prefix}")
    body = row[len(prefix) + 1:].removesuffix("|")
    parts = body.split("|")
    if len(parts) != segments or any(len(part) != slots * width or
                                     re.fullmatch(r"[A-Za-z0-9#*\-]+", part) is None for part in parts):
        raise CandidateError(f"STAFF_ROW_INVALID {prefix}")
    return parts


def _cells(row: str, prefix: str, segments: int, slots: int, width: int) -> list[list[str]]:
    return [[part[start:start + width].rstrip("-") for start in range(0, len(part), width)]
            for part in _row_parts(row, prefix, segments, slots, width)]


def _staff(rows: list[str], *, segments: int, slots: int, width: int,
           second: str | None, label: str, chords: list[str] | None = None,
           positions: list[str] | None = None, sets: list[str] | None = None) -> dict[str, Any]:
    expected = 8 if second is None else 9
    if len(rows) != expected or not rows[0].startswith("Nte|"):
        raise CandidateError(f"STAFF_LAYOUT_INVALID {label}")
    notes = _cells(rows[0], "Nte", segments, slots, width)
    second_cells = _cells(rows[1], second, segments, slots, width) if second else None
    col_index = 1 if second is None else 2
    colors = _cells(rows[col_index], "Col", segments, slots, width)
    tabs = {string: _cells(row, f"  {string}", segments, slots, width)
            for string, row in zip(TAB_STRINGS, rows[col_index + 1:], strict=True)}
    if (chords is not None and len(chords) != segments or
        positions is not None and len(positions) != segments or
        sets is not None and len(sets) != segments):
        raise CandidateError(f"STAFF_BAR_LABEL_COUNT_INVALID {label}")
    events = []
    for segment in range(segments):
        for slot in range(slots):
            tone = notes[segment][slot]
            degree_or_role = second_cells[segment][slot] if second_cells else None
            color = colors[segment][slot]
            contacts = [(string, tabs[string][segment][slot]) for string in STRINGS
                        if tabs[string][segment][slot]]
            if tone not in PC or color != COLOR.get(tone) or len(contacts) != 1 or re.fullmatch(
                    r"\d{1,2}", contacts[0][1]) is None:
                raise CandidateError(f"STAFF_SLOT_INVALID {label} {segment + 1}:{slot + 1}")
            string, fret_string = contacts[0]
            fret = int(fret_string)
            if (OPEN_MIDI[string] + fret) % 12 != PC[tone]:
                raise CandidateError(f"TAB_NOTE_PITCH_MISMATCH {label} {segment + 1}:{slot + 1}")
            chord = chords[segment] if chords else None
            if tone == "G#" and chord != "E7":
                raise CandidateError(f"GSHARP_OUTSIDE_E7 {label}")
            if second == "Deg" and DEGREE.get(tone) != degree_or_role:
                raise CandidateError(f"A_DEGREE_MISMATCH {label} {segment + 1}:{slot + 1}")
            if second == "Rol" and (chord is None or ROLE[chord].get(tone) != degree_or_role):
                raise CandidateError(f"CHORD_ROLE_MISMATCH {label} {segment + 1}:{slot + 1}")
            if sets and tone not in ({"MIN": {"A", "C", "D", "E", "G"},
                                     "MAJ": {"A", "B", "C#", "E", "F#"}}[sets[segment]]):
                raise CandidateError(f"BAR_POOL_MISMATCH {label} {segment + 1}:{slot + 1}")
            events.append({"ordinal": len(events) + 1, "segment": segment + 1,
                           "slot": slot + 1, "ascii_column": slot * width,
                           "tone": tone, "degree": degree_or_role if second == "Deg" else None,
                           "chord_role": degree_or_role if second == "Rol" else None,
                           "color": color, "string": string, "fret": fret,
                           "chord": chord, "position": positions[segment] if positions else None,
                           "set": sets[segment] if sets else None,
                           "onset_q": None, "duration_q": None})
    return {"raw_rows": rows, "events": events}


def _position_modules(lines: list[str]) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    heads = [(index, match) for index, line in enumerate(lines)
             if (match := POSITION_HEAD.fullmatch(line))]
    if len(heads) != 5 or [int(m.group(1)) for _, m in heads] != list(range(1, 6)):
        raise CandidateError("POSITION_HEADINGS_INVALID")
    modules: dict[str, list[dict[str, Any]]] = {key: [] for key in ("A", "C", "D", "G", "H")}
    positions = []
    for ordinal, (start, match) in enumerate(heads, 1):
        end = heads[ordinal][0] if ordinal < 5 else lines.index("MODULE B - EXACT C/C# THIRD CONTROL")
        staff_starts = [index for index in range(start, end) if lines[index].startswith("Nte|")]
        if len(staff_starts) != 11:
            raise CandidateError(f"POSITION_STAFF_COUNT_INVALID P{ordinal}")
        position = {"position": ordinal, "fret_span": [int(match.group(2)), int(match.group(3))],
                    "roots": match.group(4).split(", "), "source_ref": f"L47-TXT1-{start + 1}",
                    "pdf_pages": [ordinal * 2 + 1, ordinal * 2 + 2]}
        if position["fret_span"] != [[4, 8], [7, 10], [9, 13], [12, 15], [14, 17]][ordinal - 1]:
            raise CandidateError(f"POSITION_SPAN_INVALID P{ordinal}")
        positions.append(position)
        for cell_index, row_index in enumerate(staff_starts):
            heading = lines[row_index - 1]
            if cell_index < 2:
                module = "A"
            elif cell_index < 4:
                module = "C"
            elif cell_index < 6:
                module = "D"
            elif cell_index < 9:
                module = "G"
            else:
                module = "H"
            segments, slots = (2, 4) if module == "H" else (1, 8)
            second = "Rol" if module == "G" else "Deg"
            chord = heading[:2] if module == "G" else None
            parsed = _staff(lines[row_index:row_index + 9], segments=segments, slots=slots,
                            width=4, second=second, label=f"P{ordinal} {heading}",
                            chords=[chord] if chord else None)
            if module == "G" and chord not in ("A7", "D7", "E7"):
                raise CandidateError(f"HYBRID_CHORD_INVALID P{ordinal}")
            if module == "H":
                if heading not in ("MAJOR QUESTION -> MINOR ANSWER", "MINOR QUESTION -> MAJOR ANSWER"):
                    raise CandidateError(f"QUESTION_ANSWER_HEADING_INVALID P{ordinal}")
                colors = [[event["color"] for event in parsed["events"][i:i + 4]] for i in (0, 4)]
                if not (set(colors[0]) <= ({"C", "M"} if heading.startswith("MAJOR") else {"C", "m"}) and
                        set(colors[1]) <= ({"C", "m"} if heading.startswith("MAJOR") else {"C", "M"})):
                    raise CandidateError(f"QUESTION_ANSWER_COLOR_INVALID P{ordinal}")
            modules[module].append({"position": ordinal, "heading": heading, "chord": chord,
                                    "note_count": len(parsed["events"]), **parsed,
                                    "source_ref": f"L47-TXT1-{row_index}-{row_index + 9}",
                                    "pdf_page": ordinal * 2 + (1 if cell_index < 6 else 2)})
    return modules, positions


def _third_sites(lines: list[str], pdf_page: list[str]) -> list[dict[str, Any]]:
    first = lines.index("MODULE B - EXACT C/C# THIRD CONTROL")
    last = lines.index("MODULE E - TWO-BAR COLOR SWITCHING")
    headers = [(index, re.fullmatch(r"(Low E|A|D|G|B|High e): C fret (\d+), C# fret (\d+)", line))
               for index, line in enumerate(lines[first:last], first)]
    headers = [(i, m) for i, m in headers if m]
    if len(headers) != 6:
        raise CandidateError("THIRD_SITE_COUNT_INVALID")
    sites = []
    for ordinal, (index, match) in enumerate(headers, 1):
        assert match is not None
        string = {"Low E": "E", "High e": "e"}.get(match.group(1), match.group(1))
        c_fret, sharp_fret = int(match.group(2)), int(match.group(3))
        root_fret = {"E": 5, "A": 12, "D": 7, "G": 7, "B": 10, "e": 5}[string]
        resolution_tone = "D" if string == "G" else "A"
        if sharp_fret != c_fret + 1 or any((OPEN_MIDI[string] + fret) % 12 != PC[tone]
                                           for tone, fret in (("C", c_fret), ("C#", sharp_fret),
                                                              (resolution_tone, root_fret))):
            raise CandidateError(f"THIRD_SITE_PITCH_INVALID {string}")
        fretted = f"Fretted  {string}|--{c_fret}--{sharp_fret}--{c_fret}--{sharp_fret}--|"
        slides = f"Slides   {string}|--{c_fret}/{sharp_fret}--{sharp_fret}\\{c_fret}--|"
        bend = f"Bend     {string}|--{c_fret}b({sharp_fret})r{c_fret}--{root_fret}--|"
        if lines[index + 1:index + 5] != [fretted, slides, bend,
                                           "Count 12 sounding tones and 8 attacks."]:
            raise CandidateError(f"THIRD_SITE_NOTATION_INVALID {string}")
        pdf_header = f"{match.group(1)}: C fret {c_fret} / C# fret {sharp_fret}"
        if (pdf_header not in pdf_page or any(row not in pdf_page for row in (fretted, slides, bend))
            or "Notes       C  C#  C  C# | C-C# C#-C | C-C#-C  A" not in pdf_page):
            raise CandidateError(f"PDF_THIRD_SITE_MISMATCH {string}")
        def event(tone: str, technique: str, attack: bool, physical_fret: int | None = None) -> dict[str, Any]:
            return {"tone": tone, "color": COLOR[tone], "string": string,
                    "sounding_fret_equivalent": {"C": c_fret, "C#": sharp_fret,
                                                  resolution_tone: root_fret}[tone],
                    "physical_fret": physical_fret if physical_fret is not None else
                    {"C": c_fret, "C#": sharp_fret, resolution_tone: root_fret}[tone],
                    "technique": technique, "new_pick_attack": attack,
                    "onset_q": None, "duration_q": None}
        groups = [
            {"technique": "fretted", "events": [event(t, "fretted", True) for t in ("C", "C#", "C", "C#")]},
            {"technique": "slides", "events": [event("C", "slide_up_start", True),
                                                event("C#", "slide_up_arrival", False),
                                                event("C#", "slide_down_start", True),
                                                event("C", "slide_down_arrival", False)]},
            {"technique": "bend_release", "events": [event("C", "bend_start", True),
                                                       event("C#", "bend_arrival", False, c_fret),
                                                       event("C", "bend_release", False, c_fret),
                                                       event(resolution_tone, "printed_resolution", True)]},
        ]
        sites.append({"ordinal": ordinal, "string": string, "c_fret": c_fret,
                      "c_sharp_fret": sharp_fret, "printed_resolution_fret": root_fret,
                      "tab_sounding_resolution_tone": resolution_tone,
                      "pdf_note_guide_resolution_tone": "A",
                      "source_conflict": "G7 sounds D, although PDF p13 labels the resolution A."
                      if string == "G" else None,
                      "passes": groups, "sounding_tone_count": 12, "pick_attack_count": 8,
                      "raw_lines": lines[index:index + 5],
                      "source_refs": [f"L47-TXT1-{index + 1}-{index + 5}", "L47-PDF1-p13"]})
    return sites


def _switches(lines: list[str]) -> list[dict[str, Any]]:
    first = lines.index("MODULE E - TWO-BAR COLOR SWITCHING")
    last = lines.index("MODULE F - POSITION-OVERLAP CELLS")
    heads = [(index, match) for index in range(first, last)
             if (match := re.fullmatch(r"([1-6])\. P([1-5]) - (.+)", lines[index]))]
    if len(heads) != 6:
        raise CandidateError("SWITCH_COUNT_INVALID")
    studies = []
    for ordinal, (index, match) in enumerate(heads, 1):
        if int(match.group(1)) != ordinal:
            raise CandidateError("SWITCH_ORDINAL_INVALID")
        set_row = lines[index + 1]
        sets = [cell.rstrip("-") for cell in _row_parts(set_row, "Set", 2, 8, 3)]
        if sets not in (["MIN", "MAJ"], ["MAJ", "MIN"]):
            raise CandidateError(f"SWITCH_SET_INVALID {ordinal}")
        parsed = _staff(lines[index + 2:index + 10], segments=2, slots=8, width=3,
                        second=None, label=f"switch {ordinal}", sets=sets)
        studies.append({"ordinal": ordinal, "position": int(match.group(2)),
                        "heading": lines[index], "sets": sets, "raw_set_row": set_row,
                        "note_count": 16, **parsed,
                        "source_ref": f"L47-TXT1-{index + 1}-{index + 10}", "pdf_page": 14})
    return studies


def _overlaps(lines: list[str]) -> list[dict[str, Any]]:
    first = lines.index("MODULE F - POSITION-OVERLAP CELLS")
    last = lines.index(CHORUS_HEADS[0])
    cells = []
    for lower in range(1, 5):
        heading = f"P{lower} <-> P{lower + 1} OVERLAP"
        try:
            index = lines.index(heading, first, last)
        except ValueError as exc:
            raise CandidateError(f"OVERLAP_HEADING_MISSING {lower}") from exc
        parsed = _staff(lines[index + 1:index + 10], segments=1, slots=12, width=3,
                        second="Deg", label=heading)
        if [event["color"] for event in parsed["events"]] != ["C", "M", "m"] * 4:
            raise CandidateError(f"OVERLAP_COLOR_SEQUENCE_INVALID {lower}")
        cells.append({"lower_position": lower, "upper_position": lower + 1,
                      "note_count": 12, **parsed,
                      "source_ref": f"L47-TXT1-{index + 1}-{index + 10}", "pdf_page": 15})
    return cells


def _chorus(lines: list[str], heading: str, pdf_page: int) -> dict[str, Any]:
    try:
        start = lines.index(heading)
    except ValueError as exc:
        raise CandidateError(f"CHORUS_HEADING_MISSING {heading}") from exc
    blocks = []
    for group in range(3):
        marker = f"Bars {1 + group * 4}-{4 + group * 4}"
        try:
            index = lines.index(marker, start)
        except ValueError as exc:
            raise CandidateError(f"CHORUS_BAR_HEADING_MISSING {heading} {group + 1}") from exc
        chords = [part.rstrip("-") for part in _row_parts(lines[index + 1], "Chd", 4, 4, 3)]
        positions = [part.rstrip("-") for part in _row_parts(lines[index + 2], "Pos", 4, 4, 3)]
        if chords != list(CHORD_FORM[group * 4:group * 4 + 4]) or positions != list(
                POSITION_FORM[group * 4:group * 4 + 4]):
            raise CandidateError(f"CHORUS_FORM_INVALID {heading} {group + 1}")
        parsed = _staff(lines[index + 3:index + 12], segments=4, slots=4, width=3,
                        second="Rol", label=f"{heading} {marker}", chords=chords,
                        positions=positions)
        if heading == CHORUS_HEADS[0] and any(event["tone"] not in {"A", "C", "D", "E", "G"}
                                                 for event in parsed["events"]):
            raise CandidateError("MINOR_CHORUS_POOL_INVALID")
        if heading == CHORUS_HEADS[1] and any(event["tone"] not in {"A", "B", "C#", "E", "F#"}
                                                 for event in parsed["events"]):
            raise CandidateError("MAJOR_CHORUS_POOL_INVALID")
        blocks.append({"bars": list(range(group * 4 + 1, group * 4 + 5)),
                       "chords": chords, "positions": positions,
                       "raw_chord_row": lines[index + 1], "raw_position_row": lines[index + 2],
                       **parsed, "source_ref": f"L47-TXT1-{index + 1}-{index + 12}"})
    return {"heading": heading, "blocks": blocks, "note_count": 48,
            "pdf_page": pdf_page, "source_ref": f"L47-TXT1-{start + 1}"}


def _recovery(lines: list[str], pdf_page: list[str]) -> list[dict[str, Any]]:
    first = lines.index("RECOVERY CARDS")
    last = lines.index("PRACTICE PROGRESSION")
    cards = []
    pdf_text = " ".join(pdf_page)
    for index in range(first, last):
        match = RECOVERY.fullmatch(lines[index])
        if match is None:
            continue
        ordinal = int(match.group(1))
        chord, source, target, source_role, target_role = match.group(2, 3, 4, 5, 6)
        if (ordinal != len(cards) + 1 or ROLE[chord].get(source) != source_role
            or ROLE[chord].get(target) not in (target_role, target_role + "*")):
            raise CandidateError(f"RECOVERY_CARD_ROLE_INVALID {ordinal}")
        pdf_token = f"{ordinal:02d} {chord}: {source}->{target} ({source_role} -> {target_role})"
        if pdf_token not in pdf_text:
            raise CandidateError(f"PDF_RECOVERY_CARD_MISMATCH {ordinal}")
        cards.append({"ordinal": ordinal, "chord": chord,
                      "sounds": [{"tone": source, "role": source_role, "color": COLOR[source],
                                  "string": None, "fret": None, "onset_q": None, "duration_q": None},
                                 {"tone": target, "role": target_role, "color": COLOR[target],
                                  "string": None, "fret": None, "onset_q": None, "duration_q": None}],
                      "raw_line": lines[index], "source_refs": [f"L47-TXT1-{index + 1}", "L47-PDF1-p19"]})
    if len(cards) != 12:
        raise CandidateError("RECOVERY_CARD_COUNT_INVALID")
    return cards


def _verify_pdf_rows(lines: list[str], pages: list[list[str]]) -> dict[str, Any]:
    txt = Counter(line for line in lines if line.startswith(ROW_PREFIX))
    pdf = Counter(line for page in pages for line in page if line.startswith(ROW_PREFIX))
    if txt != pdf or sum(txt.values()) != 717:
        raise CandidateError(f"PDF_TXT_STRUCTURED_ROWS_MISMATCH txt={sum(txt.values())} pdf={sum(pdf.values())}")
    per_page = [sum(line.startswith(ROW_PREFIX) for line in page) for page in pages]
    if per_page != [0, 0, 54, 45, 54, 45, 54, 45, 54, 45, 54, 45,
                    0, 54, 36, 33, 33, 33, 33, 0]:
        raise CandidateError("PDF_STRUCTURED_PAGE_MAP_MISMATCH")
    if any(page[0] != "Scale Exercises - Section V, Level 47" for page in pages):
        raise CandidateError("PDF_PAGE_TITLE_MISMATCH")
    page_subtitles = {12: "Module B - exact C/C# third control on all six strings",
                      13: "Module E - two-bar color switching without losing the motif",
                      14: "Module F - four position-overlap cells for fixed-key color changes",
                      15: "Module I - twelve-bar pass 1: A minor pentatonic only",
                      16: "Module I - twelve-bar pass 2: A major pentatonic only",
                      17: "Module I - twelve-bar pass 3: chord-aware major/minor mixture",
                      18: "Module J - model mixed-color chorus and rapid recovery cards"}
    if any(pages[index][1] != subtitle for index, subtitle in page_subtitles.items()):
        raise CandidateError("PDF_SECTION_PAGE_MAP_MISMATCH")
    return {"structured_row_count": 717, "per_page_counts": per_page,
            "comparison": "exact raw-row multiset; PDF page placement differs"}


def build_candidate(*, txt_data: bytes | None = None, pdf_data: bytes | None = None) -> dict[str, Any]:
    root = _root()
    txt_data = _source_bytes(root, TXT_REL) if txt_data is None else txt_data
    pdf_data = _source_bytes(root, PDF_REL) if pdf_data is None else pdf_data
    _verify(txt_data, TXT_BYTES, TXT_SHA256, "L47-TXT")
    _verify(pdf_data, PDF_BYTES, PDF_SHA256, "L47-PDF")
    try:
        lines = txt_data.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise CandidateError("TXT_ENCODING_INVALID") from exc
    if len(lines) != 1044 or lines[:2] != ["SCALE EXERCISES - SECTION V, LEVEL 47",
                                       "A MAJOR AND A MINOR PENTATONIC MIXING - CHORD-AWARE COLOR CONTROL - FIXED KEY A"]:
        raise CandidateError("TXT_TITLE_OR_LENGTH_INVALID")
    pages = _pdf_pages(pdf_data)
    pdf_parity = _verify_pdf_rows(lines, pages)
    position_modules, positions = _position_modules(lines)
    sites = _third_sites(lines, pages[12])
    switches = _switches(lines)
    overlaps = _overlaps(lines)
    choruses = [_chorus(lines, heading, page) for heading, page in zip(CHORUS_HEADS, (16, 17, 18, 19), strict=True)]
    cards = _recovery(lines, pages[18])
    modules: dict[str, dict[str, Any]] = {}
    for key in ("A", "C", "D", "G", "H"):
        cells = position_modules[key]
        modules[key] = {"name": {"A": "anchor branches", "C": "6/b7 and 2/4 color pairs",
                                 "D": "paired cadence endings", "G": "hybrid dominant target cells",
                                 "H": "major/minor question-answer"}[key],
                        "cells": cells, "sounding_tone_count": sum(cell["note_count"] for cell in cells)}
    modules["B"] = {"name": "exact C/C# third control", "sites": sites,
                    "sounding_tone_count": sum(site["sounding_tone_count"] for site in sites),
                    "pick_attack_count": sum(site["pick_attack_count"] for site in sites)}
    modules["E"] = {"name": "two-bar color switching", "studies": switches,
                    "sounding_tone_count": sum(study["note_count"] for study in switches)}
    modules["F"] = {"name": "position-overlap cells", "cells": overlaps,
                    "sounding_tone_count": sum(cell["note_count"] for cell in overlaps)}
    modules["I"] = {"name": "three twelve-bar passes", "choruses": choruses[:3],
                    "sounding_tone_count": sum(chorus["note_count"] for chorus in choruses[:3])}
    modules["J"] = {"name": "model chorus plus recovery pairs", "model_chorus": choruses[3],
                    "recovery_cards": cards, "sounding_tone_count": 48 + 2 * len(cards)}
    counts = {key: modules[key]["sounding_tone_count"] for key in EXPECTED_COUNTS}
    if counts != EXPECTED_COUNTS or sum(counts.values()) != 872:
        raise CandidateError(f"WRITTEN_WORKLOAD_COUNT_INVALID {counts}")
    count_lines = [f"Module {key}: {value} sounding tones" for key, value in EXPECTED_COUNTS.items()]
    if any(line not in lines for line in count_lines) or "Total written workload: 872 sounding tones" not in lines:
        raise CandidateError("TXT_MODULE_COUNT_TABLE_MISMATCH")
    pdf1 = pages[0]
    if "FIXED KEY: A  |  10 MODULES  |  872 TONES" not in pdf1 or pdf1[pdf1.index("TOTAL") + 1] != "872":
        raise CandidateError("PDF_MODULE_TOTAL_MISMATCH")
    return {"schema": "fathom-level047-whole-detached-candidate-v1", "wbs_id": "2.3.1.1.1",
            "level": 47,
            "source": {"txt_path": TXT_REL.as_posix(), "txt_bytes": TXT_BYTES, "txt_sha256": TXT_SHA256,
                       "pdf_path": PDF_REL.as_posix(), "pdf_bytes": PDF_BYTES, "pdf_sha256": PDF_SHA256,
                       "pdf_pages": 20},
            "key": "A", "major_pool": ["A", "B", "C#", "E", "F#"],
            "minor_pool": ["A", "C", "D", "E", "G"], "common_anchors": ["A", "E"],
            "color_pairs": [["C#", "C"], ["F#", "G"], ["B", "D"]],
            "chord_completion_tone": "G#* over E7 only", "color_key": COLOR,
            "chord_role_matrix": ROLE, "positions": positions, "modules": modules,
            "module_sounding_tone_counts": counts, "written_workload_sounding_tones": 872,
            "pdf_parity": pdf_parity,
            "source_conflicts": [{"kind": "third_control_g_string_resolution",
                                  "txt_ref": "L47-TXT1-690-694", "pdf_ref": "L47-PDF1-p13",
                                  "printed_tab_contact": "G7", "sounding_tone_standard_tuning": "D",
                                  "pdf_note_guide_label": "A", "curriculum_resolution": "Pending"}],
            "source_instructions": {"overview_text": "\n".join(lines[:37]),
                                    "practice_mastery_text": "\n".join(lines[1013:]),
                                    "source_refs": ["L47-TXT1-1-37", "L47-TXT1-1014-1044",
                                                    "L47-PDF1-p1-2", "L47-PDF1-p20"]},
            "canonical_item_id": None, "canonical_variant_id": None,
            "onset_q": None, "duration_q": None, "fixed_bpm": None, "note_per_click": None,
            "pending": ["Curriculum/musical review", "canonical identity allocation and admission",
                        "runtime note timing and performed audio"],
            "whole_workbook_complete": False, "runtime_eligible": False,
            "runtime_admitted": False, "imported": False, "admitted": False}


def write_candidate(output: Path) -> dict[str, Any]:
    root = _root()
    target = output if output.is_absolute() else root / output
    allowed = root / BUILD_REL
    if not target.parent.exists() or target.parent.is_symlink() or target.parent.resolve() != allowed.resolve():
        raise CandidateError(f"OUTPUT_OUTSIDE_LANE_BUILD {output}")
    if target.suffix != ".json" or target.is_symlink():
        raise CandidateError(f"OUTPUT_INVALID {output}")
    data = (json.dumps(build_candidate(), indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode()
    try:
        with target.open("xb") as handle:
            handle.write(data)
    except FileExistsError as exc:
        raise CandidateError(f"OUTPUT_EXISTS {output}") from exc
    return {"output": str(target.relative_to(root)), "bytes": len(data), "sha256": digest(data)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(write_candidate(args.output), sort_keys=True))
    except CandidateError as exc:
        parser.exit(2, f"{exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
