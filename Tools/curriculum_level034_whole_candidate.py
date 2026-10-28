#!/usr/bin/env python3
"""Build a detached, source-linked whole-Level-34 fixed-key A pentatonic candidate."""

from __future__ import annotations

import argparse
from io import BytesIO
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
TXT_REL = Path("Notes/music/guitar project/TXT version/Scale_Exercises_Section_IV_Level_34_Major_Pentatonic_Five_Position_Connection_Fixed_Key_A_Neck_Map.txt")
PDF_REL = Path("Notes/music/guitar project/PDF version/Scale_Exercises_Section_IV_Level_34_Major_Pentatonic_Five_Position_Connection_Fixed_Key_A_Neck_Map.pdf")
TXT_BYTES = 21711
TXT_SHA256 = "e4d015b5f553691f1fd108702b36a538182c2d35b9b457b70c34306b16312724"
PDF_BYTES = 34668
PDF_SHA256 = "d4c1833abf92748214cc61054f51683c994edd14048d16046a6cc619b9031a8e"
BUILD_REL = Path("Build/parallel-09/2.3.1.1.1-level034-whole-r01")
STRINGS = ("E", "A", "D", "G", "B", "e")
TAB_ROWS = tuple(reversed(STRINGS))
OPEN_MIDI = {"E": 40, "A": 45, "D": 50, "G": 55, "B": 59, "e": 64}
DEGREE_NOTE = {1: "A", 2: "B", 3: "C#", 5: "E", 6: "F#"}
NOTE_PC = {"A": 9, "B": 11, "C#": 1, "E": 4, "F#": 6}
POSITIONS = (
    ("ROOT FRAME", "Root Frame", (4, 7), 1, "E5, D7, e5"),
    ("SECOND-DEGREE FRAME", "Second-Degree Frame", (6, 10), 2, "D7, B10"),
    ("THIRD-DEGREE FRAME", "Third-Degree Frame", (9, 12), 3, "A12, B10"),
    ("FIFTH-DEGREE FRAME", "Fifth-Degree Frame", (11, 14), 5, "A12, G14"),
    ("SIXTH-DEGREE FRAME", "Sixth-Degree Frame", (14, 17), 6, "E17, G14, e17"),
)
POSITION_LINES = (49, 78, 107, 136, 165)
SEAM_LINES = (202, 214, 226, 238)
FORWARD_LINES = (257, 267, 277, 287, 297)
REVERSE_LINES = (315, 325, 335, 345, 355)
FORWARD_ORDER = ((1, "ASC"), (2, "DESC"), (3, "ASC"), (4, "DESC"), (5, "ASC"))
REVERSE_ORDER = ((5, "DESC"), (4, "ASC"), (3, "DESC"), (2, "ASC"), (1, "DESC"))
PDF_FOOT = "Standard tuning. Fixed-key A major pentatonic. Position labels follow ascending-neck order from the root frame."
SEAM_PICK = "Picking: five-note groups alternate their starting stroke; the complete six-string seam cell is even."
PAIR_RE = re.compile(r"  ([EADGBe]): (\d+)-(\d+) / fingers (\d+)-(\d+) / degrees ([12356])-([12356]) / notes (A|B|C#|E|F#)-(A|B|C#|E|F#)")


class CandidateError(ValueError):
    """Pinned input, printed musical structure or output boundary failed."""


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _root() -> Path:
    result = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if result.returncode or Path(result.stdout.strip()).resolve() != ROOT.resolve():
        raise CandidateError("REPOSITORY_ROOT_MISMATCH")
    return ROOT


def _source_bytes(root: Path, rel: Path) -> bytes:
    path = root / rel
    if path.is_symlink() or not path.is_file() or path.resolve().parent != path.parent.resolve():
        raise CandidateError(f"SOURCE_PATH_INVALID {rel}")
    return path.read_bytes()


def _verify(data: bytes, length: int, sha: str, label: str) -> None:
    if len(data) != length or digest(data) != sha:
        raise CandidateError(f"PINNED_INPUT_DRIFT {label}: bytes={len(data)} sha256={digest(data)}")


def _groups(row: str, label: str, count: int, slots: int) -> list[list[str | int | None]]:
    prefix = label if label in ("Nte", "Deg", "Fng") else label + "  "
    parts = row.split("|")
    if len(parts) != count + 2 or parts[0] != prefix or parts[-1] != "":
        raise CandidateError(f"ROW_SHAPE_INVALID {label}")
    result = []
    for cell in parts[1:-1]:
        if len(cell) != slots * 3:
            raise CandidateError(f"ROW_WIDTH_INVALID {label}")
        values: list[str | int | None] = []
        for i in range(0, len(cell), 3):
            token = cell[i:i+3]
            if token == "---":
                values.append(None)
                continue
            value = token.rstrip("-")
            if not value or value + "-" * (3-len(value)) != token:
                raise CandidateError(f"ROW_SLOT_INVALID {label}")
            if label == "Nte":
                if value not in NOTE_PC:
                    raise CandidateError(f"NOTE_NAME_INVALID {value}")
                values.append(value)
            elif not value.isdigit():
                raise CandidateError(f"ROW_SLOT_INVALID {label}")
            else:
                values.append(int(value))
        result.append(values)
    return result


def _parse_grid(rows: list[str], count: int, slots: int, *, note_names: bool, context: str) -> list[list[dict[str, Any]]]:
    labels = (["Nte"] if note_names else []) + ["Deg", "Fng", *TAB_ROWS]
    if len(rows) != len(labels):
        raise CandidateError(f"GRID_ROW_COUNT {context}")
    parsed = {label: _groups(row, label, count, slots) for label, row in zip(labels, rows, strict=True)}
    result = []
    for g in range(count):
        events = []
        for i in range(slots):
            degree, finger = parsed["Deg"][g][i], parsed["Fng"][g][i]
            if degree not in DEGREE_NOTE or finger not in (1, 2, 3, 4):
                raise CandidateError(f"DEG_FNG_INVALID {context} {g+1} {i+1}")
            printed = [(string, parsed[string][g][i]) for string in TAB_ROWS if parsed[string][g][i] is not None]
            if len(printed) != 1:
                raise CandidateError(f"TAB_NOTE_CARDINALITY {context} {g+1} {i+1}")
            string, fret = printed[0]
            if (OPEN_MIDI[string] + fret) % 12 != NOTE_PC[DEGREE_NOTE[degree]]:
                raise CandidateError(f"PITCH_DEGREE_MISMATCH {context} {g+1} {i+1}")
            if note_names and parsed["Nte"][g][i] != DEGREE_NOTE[degree]:
                raise CandidateError(f"PRINTED_NOTE_DEGREE_MISMATCH {context} {g+1} {i+1}")
            events.append({"ordinal": g * slots + i + 1, "group": g + 1, "slot": i + 1,
                           "degree": degree, "note_name": DEGREE_NOTE[degree], "finger_digit": finger,
                           "string": string, "fret": fret, "onset_q": None, "duration_q": None})
        result.append(events)
    return result


def _pair(line: str, string: str) -> dict[str, Any]:
    m = PAIR_RE.fullmatch(line)
    if not m or m.group(1) != string:
        raise CandidateError(f"STRING_PAIR_INVALID {string}")
    frets = [int(m.group(2)), int(m.group(3))]
    fingers = [int(m.group(4)), int(m.group(5))]
    degrees = [int(m.group(6)), int(m.group(7))]
    names = [m.group(8), m.group(9)]
    if frets != sorted(set(frets)) or any(f not in (1, 2, 3, 4) for f in fingers):
        raise CandidateError(f"STRING_PAIR_FRET_FINGER_INVALID {string}")
    for fret, degree, name in zip(frets, degrees, names, strict=True):
        if DEGREE_NOTE[degree] != name or (OPEN_MIDI[string] + fret) % 12 != NOTE_PC[name]:
            raise CandidateError(f"STRING_PAIR_PITCH_INVALID {string}")
    return {"string": string, "frets": frets, "finger_digits": fingers, "degrees": degrees, "notes": names,
            "printed": line}


def _event_contact(e: dict[str, Any]) -> tuple[str, int, int, int]:
    return (e["string"], e["fret"], e["finger_digit"], e["degree"])


def _pair_contact(pair: dict[str, Any], index: int) -> tuple[str, int, int, int]:
    return (pair["string"], pair["frets"][index], pair["finger_digits"][index], pair["degrees"][index])


def _parse_txt(data: bytes) -> dict[str, Any]:
    try:
        lines = data.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise CandidateError("TXT_ENCODING_INVALID") from exc
    if len(lines) != 403 or lines[:2] != ["SCALE EXERCISES - SECTION IV, LEVEL 34", "A MAJOR PENTATONIC FIVE-POSITION CONNECTION - FIXED-KEY NECK MAP"]:
        raise CandidateError("TXT_DOCUMENT_BOUNDARY")
    if lines[14:18] != ["A MAJOR-PENTATONIC FORMULA", "Notes: A B C# E F#", "Degrees: 1 2 3 5 6", "Intervals: whole - whole - minor third - whole - minor third"]:
        raise CandidateError("TXT_FIXED_KEY_FORMULA_MISMATCH")
    count_text = "\n".join(lines[31:43])
    if not all(x in count_text for x in ("24 notes", "30 notes", "60 notes", "120-note circuit", "Complete Level 34 workout = 360 notes")):
        raise CandidateError("TXT_COUNT_MISMATCH")
    if "Do not restart" not in "\n".join(lines[40:43]):
        raise CandidateError("TXT_PICKING_MISMATCH")
    positions = []
    for index, number in enumerate(POSITION_LINES):
        start = number - 1
        upper, title, span, first_degree, roots = POSITIONS[index]
        summary_head = lines[20 + index * 2]
        summary_match = re.fullmatch(r"P(\d) (.+?)\s+frets (\d+)-(\d+)\s+starts degree ([12356])\s+roots (.+)", summary_head)
        if not summary_match or (int(summary_match.group(1)), summary_match.group(2), int(summary_match.group(3)),
                                 int(summary_match.group(4)), int(summary_match.group(5)), summary_match.group(6)) != (index+1, upper, span[0], span[1], first_degree, roots):
            raise CandidateError(f"TXT_POSITION_SUMMARY_MISMATCH {index+1}")
        expected = f"POSITION {index+1} - {upper} - FRETS {span[0]}-{span[1]}"
        if lines[start] != expected or lines[start+1] != f"Starts on degree {first_degree}. Roots: {roots}." or lines[start+3] != "String pairs (fret / finger / degree):" or lines[start+11] != "24-NOTE UP/DOWN CELL":
            raise CandidateError(f"TXT_POSITION_HEADER_MISMATCH {index+1}")
        pairs = [_pair(lines[start+4+j], string) for j, string in enumerate(STRINGS)]
        if any(not (span[0] <= fret <= span[1]) for p in pairs for fret in p["frets"]):
            raise CandidateError(f"POSITION_SPAN_MISMATCH {index+1}")
        actual_roots = ", ".join(f"{p['string']}{fret}" for p in pairs for fret, degree in zip(p["frets"], p["degrees"], strict=True) if degree == 1)
        if actual_roots != roots:
            raise CandidateError(f"POSITION_ROOTS_MISMATCH {index+1}: {actual_roots}")
        rows = lines[start+12:start+21]
        groups = _parse_grid(rows, 2, 12, note_names=True, context=f"position{index+1}")
        asc_expected = [_pair_contact(p, j) for p in pairs for j in (0, 1)]
        actual_up = [_event_contact(e) for e in groups[0]]
        actual_down = [_event_contact(e) for e in groups[1]]
        if actual_up != asc_expected or actual_down != list(reversed(asc_expected)):
            raise CandidateError(f"POSITION_CONTACT_MISMATCH {index+1}")
        if lines[21 + index * 2].strip() != "Ascending degrees: " + " ".join(str(e["degree"]) for e in groups[0]):
            raise CandidateError(f"TXT_POSITION_SUMMARY_DEGREES_MISMATCH {index+1}")
        if lines[start+22] != "Practice passes:" or "D-start and U-start" not in "\n".join(lines[start+23:start+28]):
            raise CandidateError(f"POSITION_PRACTICE_MISMATCH {index+1}")
        positions.append({"position": index+1, "name": title, "span": list(span), "starting_degree": first_degree,
                          "roots": roots.split(", "), "hand_note": lines[start+2], "string_pairs": pairs,
                          "printed_rows": rows, "ascending_events": groups[0], "descending_events": groups[1],
                          "practice_text": "\n".join(lines[start+22:start+28]),
                          "source_ref": f"L34-TXT1-{number}-{number+27}"})
    if not all(x in "\n".join(lines[196:200]) for x in ("shared anchor", "Shift after", "note 4", "shift back")):
        raise CandidateError("TXT_SEAM_INSTRUCTION_MISMATCH")
    seams = []
    for index, number in enumerate(SEAM_LINES):
        start = number - 1
        if lines[start] != f"SEAM P{index+1} <-> P{index+2} - 30 NOTES" or lines[start+10] != SEAM_PICK:
            raise CandidateError(f"TXT_SEAM_HEADER_MISMATCH {index+1}")
        anchors = [f"{string}{positions[index]['string_pairs'][j]['frets'][1]}" for j, string in enumerate(STRINGS)]
        if any(positions[index]["string_pairs"][j]["frets"][1] != positions[index+1]["string_pairs"][j]["frets"][0] for j in range(6)):
            raise CandidateError(f"SEAM_SHARED_CONTACT_MISMATCH {index+1}")
        if lines[start+1] != "Shared anchors: " + ", ".join(anchors):
            raise CandidateError(f"SEAM_ANCHOR_LABEL_MISMATCH {index+1}")
        rows = lines[start+2:start+10]
        groups = _parse_grid(rows, 6, 5, note_names=False, context=f"seam{index+1}")
        for j, group in enumerate(groups):
            low = positions[index]["string_pairs"][j]
            high = positions[index+1]["string_pairs"][j]
            expected = [_pair_contact(low, 0), _pair_contact(low, 1), _pair_contact(high, 1),
                        _pair_contact(high, 0), _pair_contact(low, 0)]
            if [_event_contact(e) for e in group] != expected:
                raise CandidateError(f"SEAM_CONTACT_MISMATCH {index+1} {j+1}")
        seams.append({"seam": index+1, "from_position": index+1, "to_position": index+2,
                      "shared_anchors": anchors, "printed_rows": rows, "groups": groups,
                      "picking_text": lines[start+10], "source_ref": f"L34-TXT1-{number}-{number+10}"})
    route_texts = {"forward": "\n".join(lines[252:255]), "reverse": "\n".join(lines[309:313])}
    if not all(x in route_texts["forward"] for x in ("high-e 7 to 9", "low-E 7 to 9", "high-e 12 to 14", "low-E 12 to 14")):
        raise CandidateError("TXT_FORWARD_ROUTE_MISMATCH")
    if not all(x in route_texts["reverse"] for x in ("low-E 14 to 12", "high-e 14 to 12", "low-E 9 to 7", "high-e 9 to 7", "high-e fret 17")):
        raise CandidateError("TXT_REVERSE_ROUTE_MISMATCH")
    zigzags = {}
    for label, starts, order in (("forward", FORWARD_LINES, FORWARD_ORDER), ("reverse", REVERSE_LINES, REVERSE_ORDER)):
        segments = []
        for number, (position, direction) in zip(starts, order, strict=True):
            start = number - 1
            span = POSITIONS[position-1][2]
            if lines[start] != f"P{position} {direction} - frets {span[0]}-{span[1]} - 12 NOTES":
                raise CandidateError(f"TXT_ZIGZAG_HEADER_MISMATCH {label} P{position}")
            rows = lines[start+1:start+9]
            parsed = _parse_grid(rows, 1, 12, note_names=False, context=f"{label}-P{position}")[0]
            source_events = positions[position-1]["ascending_events" if direction == "ASC" else "descending_events"]
            if [_event_contact(e) for e in parsed] != [_event_contact(e) for e in source_events]:
                raise CandidateError(f"ZIGZAG_POSITION_MISMATCH {label} P{position}")
            segments.append({"position": position, "direction": direction, "printed_rows": rows, "events": parsed,
                             "source_ref": f"L34-TXT1-{number}-{number+8}"})
        zigzags[label] = segments
    transitions = {}
    for label, segments in zigzags.items():
        contacts = []
        for left, right in zip(segments, segments[1:]):
            a, b = left["events"][-1], right["events"][0]
            if a["string"] != b["string"] or a["string"] not in ("E", "e"):
                raise CandidateError(f"ZIGZAG_TRANSITION_STRING {label}")
            contacts.append({"from_position": left["position"], "to_position": right["position"],
                             "from": {"string": a["string"], "fret": a["fret"], "degree": a["degree"]},
                             "to": {"string": b["string"], "fret": b["fret"], "degree": b["degree"]}})
        transitions[label] = contacts
    last = zigzags["forward"][-1]["events"][-1]
    first = zigzags["reverse"][0]["events"][0]
    if (last["string"], last["fret"], first["string"], first["fret"]) != ("e", 17, "e", 17):
        raise CandidateError("ZIGZAG_TURN_MISMATCH")
    if "Complete Level 34 workout = 360 notes" not in count_text or "120-note circuit" not in "\n".join(lines[364:377]):
        raise CandidateError("TXT_WORKOUT_COUNT_MISMATCH")
    guidance = {"position_summary_text": "\n".join(lines[19:30]), "position_summary_ref": "L34-TXT1-20-30",
                "counts_picking_text": "\n".join(lines[31:47]), "counts_picking_ref": "L34-TXT1-32-47",
                "seam_instruction_text": "\n".join(lines[196:200]), "seam_instruction_ref": "L34-TXT1-197-200",
                "forward_route_text": route_texts["forward"], "forward_route_ref": "L34-TXT1-253-255",
                "reverse_route_text": route_texts["reverse"], "reverse_route_ref": "L34-TXT1-310-313",
                "practice_mastery_text": "\n".join(lines[365:393]), "practice_mastery_ref": "L34-TXT1-366-393",
                "next_level_text": "\n".join(lines[400:403]), "next_level_ref": "L34-TXT1-401-403"}
    return {"positions": positions, "seams": seams, "zigzags": zigzags, "transitions": transitions,
            "guidance": guidance}


def _parse_pdf(data: bytes, txt: dict[str, Any]) -> dict[str, Any]:
    try:
        reader = PdfReader(BytesIO(data), strict=True)
        if len(reader.pages) != 12:
            raise CandidateError(f"PDF_PAGE_COUNT {len(reader.pages)}")
        pages = [(page.extract_text() or "").splitlines() for page in reader.pages]
    except CandidateError:
        raise
    except Exception as exc:
        raise CandidateError(f"PDF_READ_FAILED {type(exc).__name__}") from exc
    if pages[0][:4] != ["Scale Exercises - Section IV, Level 34", "One key. Five frames. Four seams.",
                        "A Major Pentatonic Five-Position Connection",
                        "Hold A major pentatonic constant while the fretting hand moves through five common positions."]:
        raise CandidateError("PDF_INTRO_MISMATCH")
    atlas = pages[1]
    if atlas[:4] != ["Level 34 - Fixed-Key A Major-Pentatonic Atlas",
                     "Roots are highlighted. Colored position spans overlap because adjacent frames share one note on every string.",
                     PDF_FOOT, "Page 2 of 12"]:
        raise CandidateError("PDF_ATLAS_HEADER_MISMATCH")
    for i, p in enumerate(txt["positions"]):
        row = atlas[71+5*i:76+5*i]
        expected = [f"P{i+1}", f"{p['span'][0]}-{p['span'][1]}", str(p["starting_degree"]),
                    ", ".join(p["roots"]), " ".join(str(e["degree"]) for e in p["ascending_events"])]
        if row != expected:
            raise CandidateError(f"PDF_ATLAS_POSITION_MISMATCH {i+1}")
    if atlas[96:98] != ["Seam", "Shared anchors: E A D G B e"]:
        raise CandidateError("PDF_ATLAS_SEAM_HEADER_MISMATCH")
    for i, seam in enumerate(txt["seams"]):
        expected = [f"P{i+1}-P{i+2}", "  ".join(str(int(re.search(r"\d+", x).group())) for x in seam["shared_anchors"])]
        if atlas[98+2*i:100+2*i] != expected:
            raise CandidateError(f"PDF_ATLAS_SEAM_MISMATCH {i+1}")
    pdf_positions = []
    for i, p in enumerate(txt["positions"]):
        page_no = i + 3
        lines = pages[page_no-1]
        if lines[:2] != [f"Level 34 - Position {i+1}: {POSITIONS[i][1]}",
                         f"frets {p['span'][0]}-{p['span'][1]}. Starts on scale degree {p['starting_degree']}. Roots: {', '.join(p['roots'])}."]:
            raise CandidateError(f"PDF_POSITION_HEADER_MISMATCH {i+1}")
        if lines[2:6] != [PDF_FOOT, f"Page {page_no} of 12", f"Position {i+1} vertical cell - 12 notes up + 12 notes down",
                         "The highest note is articulated once at the end of the ascent and again to begin the descent."]:
            raise CandidateError(f"PDF_POSITION_CARD_MISMATCH {i+1}")
        rows = lines[6:15]
        if rows != p["printed_rows"]:
            raise CandidateError(f"PDF_TXT_POSITION_ROWS_MISMATCH {i+1}")
        dna = [line for line in lines[15:] if re.fullmatch(r"[EADGBe]:\s+\d+-\d+\s+f\d-\d\s+d[12356]-[12356]", line)]
        expected_dna = [f"{pair['string']}: {pair['frets'][0]:>2}-{pair['frets'][1]:<2}  f{pair['finger_digits'][0]}-{pair['finger_digits'][1]}  d{pair['degrees'][0]}-{pair['degrees'][1]}" for pair in p["string_pairs"]]
        if dna != expected_dna or "Roots" not in lines or ", ".join(p["roots"]) not in lines:
            raise CandidateError(f"PDF_POSITION_DNA_MISMATCH {i+1}")
        pdf_positions.append({"page_ref": f"L34-PDF1-p{page_no}", "printed_rows": rows, "dna": dna})
    pdf_seams = []
    for i, seam in enumerate(txt["seams"]):
        page_no = 8 if i < 2 else 9
        lines = pages[page_no-1]
        offset = 4 if i % 2 == 0 else 16
        if lines[offset] != f"Seam P{i+1} <-> P{i+2}: shared-anchor five-note loops" or not lines[offset+1].startswith("Anchors: " + ", ".join(seam["shared_anchors"])):
            raise CandidateError(f"PDF_SEAM_HEADER_MISMATCH {i+1}")
        rows = lines[offset+2:offset+10]
        if rows != seam["printed_rows"] or lines[offset+10:offset+12] != ["COUNT", "6 strings x 5 notes = 30 notes. Odd groups flip the starting stroke; the complete seam cell is even."]:
            raise CandidateError(f"PDF_TXT_SEAM_ROWS_MISMATCH {i+1}")
        pdf_seams.append({"page_ref": f"L34-PDF1-p{page_no}", "printed_rows": rows,
                          "anchor_instruction": lines[offset+1]})
    pdf_zigzags = {}
    for label, page_no, order in (("forward", 10, FORWARD_ORDER), ("reverse", 11, REVERSE_ORDER)):
        lines = pages[page_no-1]
        if len(lines) != 59 or lines[0] != f"Level 34 - {label.title()} Five-Position Zigzag" or lines[2:4] != [PDF_FOOT, f"Page {page_no} of 12"]:
            raise CandidateError(f"PDF_ZIGZAG_PAGE_MISMATCH {label}")
        page_segments = []
        for j, ((position, direction), segment) in enumerate(zip(order, txt["zigzags"][label], strict=True)):
            offset = 5 + j * 10
            span = POSITIONS[position-1][2]
            if lines[offset] != f"P{position} {direction} - frets {span[0]}-{span[1]}":
                raise CandidateError(f"PDF_ZIGZAG_HEADER_MISMATCH {label} {j+1}")
            events = segment["events"]
            if lines[offset+1] != f"Start degree {events[0]['degree']}; end degree {events[-1]['degree']}; 12 notes.":
                raise CandidateError(f"PDF_ZIGZAG_DEGREE_MISMATCH {label} {j+1}")
            rows = lines[offset+2:offset+10]
            if rows != segment["printed_rows"]:
                raise CandidateError(f"PDF_TXT_ZIGZAG_ROWS_MISMATCH {label} {j+1}")
            page_segments.append({"page_ref": f"L34-PDF1-p{page_no}", "printed_rows": rows})
        if label == "forward" and "e7->e9" not in lines[4]:
            raise CandidateError("PDF_FORWARD_ROUTE_MISMATCH")
        if label == "reverse" and not all(x in lines[56] for x in ("high-e fret 17", "120 notes", "low-E fret 5")):
            raise CandidateError("PDF_REVERSE_TURN_MISMATCH")
        pdf_zigzags[label] = {"route_label": lines[4], "segments": page_segments, "rule": lines[56]}
    practice = pages[11]
    if practice[:4] != ["Level 34 - Practice Progression, Mastery Gate, and Log",
                        "Advance by adding position connections before adding speed. The fixed key must remain audible throughout the route.",
                        PDF_FOOT, "Page 12 of 12"] or practice[21:29] != ["5 position cells", "120 notes", "4 seam cells", "120 notes",
                                                                      "Forward + reverse zigzag", "120 notes", "Complete Level 34 workout", "360 notes / 90 sixteenth-note beats"]:
        raise CandidateError("PDF_PRACTICE_COUNT_MISMATCH")
    return {"intro_ref": "L34-PDF1-p1", "atlas_ref": "L34-PDF1-p2", "atlas_grid_text": "\n".join(atlas[4:66]),
            "atlas_position_rows": atlas[66:96], "atlas_seam_rows": atlas[96:109],
            "positions": pdf_positions, "seams": pdf_seams, "zigzags": pdf_zigzags,
            "practice_ref": "L34-PDF1-p12", "practice_text": "\n".join(practice[4:55])}


def build_candidate(*, txt_data: bytes | None = None, pdf_data: bytes | None = None) -> dict[str, Any]:
    root = _root()
    txt_data = _source_bytes(root, TXT_REL) if txt_data is None else txt_data
    pdf_data = _source_bytes(root, PDF_REL) if pdf_data is None else pdf_data
    _verify(txt_data, TXT_BYTES, TXT_SHA256, "L34-TXT")
    _verify(pdf_data, PDF_BYTES, PDF_SHA256, "L34-PDF")
    parsed = _parse_txt(txt_data)
    pdf = _parse_pdf(pdf_data, parsed)
    for p, page in zip(parsed["positions"], pdf["positions"], strict=True):
        p["source_refs"] = {"txt": p.pop("source_ref"), "pdf_card": page["page_ref"], "pdf_atlas": "L34-PDF1-p2"}
        p["printed_pdf_rows"] = page["printed_rows"]
        p["pdf_dna"] = page["dna"]
    for s, page in zip(parsed["seams"], pdf["seams"], strict=True):
        s["source_refs"] = {"txt": s.pop("source_ref"), "pdf_card": page["page_ref"], "pdf_atlas": "L34-PDF1-p2"}
        s["printed_pdf_rows"] = page["printed_rows"]
        s["pdf_anchor_instruction"] = page["anchor_instruction"]
    for label in ("forward", "reverse"):
        for s, page in zip(parsed["zigzags"][label], pdf["zigzags"][label]["segments"], strict=True):
            s["source_refs"] = {"txt": s.pop("source_ref"), "pdf_card": page["page_ref"]}
            s["printed_pdf_rows"] = page["printed_rows"]
    route = {"forward_positions": [p for p, _ in FORWARD_ORDER], "reverse_positions": [p for p, _ in REVERSE_ORDER],
             "forward_transitions": parsed["transitions"]["forward"], "reverse_transitions": parsed["transitions"]["reverse"],
             "repeated_turn": {"string": "e", "fret": 17, "forward_event": 60, "reverse_event": 1},
             "vertical_note_count": 120, "seam_note_count": 120, "linked_zigzag_note_count": 120,
             "complete_workout_note_count": 360,
             "forward_route_text": parsed["guidance"]["forward_route_text"],
             "reverse_route_text": parsed["guidance"]["reverse_route_text"],
             "pdf_forward_route_label": pdf["zigzags"]["forward"]["route_label"],
             "pdf_reverse_route_label": pdf["zigzags"]["reverse"]["route_label"]}
    return {"schema": "fathom-level034-whole-detached-candidate-v1", "wbs_id": "2.3.1.1.1", "level": 34,
            "source": {"txt_path": TXT_REL.as_posix(), "txt_bytes": TXT_BYTES, "txt_sha256": TXT_SHA256,
                       "pdf_path": PDF_REL.as_posix(), "pdf_bytes": PDF_BYTES, "pdf_sha256": PDF_SHA256, "pdf_pages": 12},
            "fixed_key": "A major pentatonic", "fixed_notes": ["A", "B", "C#", "E", "F#"],
            "fixed_degrees": [1, 2, 3, 5, 6], "positions": parsed["positions"], "seams": parsed["seams"],
            "zigzags": parsed["zigzags"], "route": route, "instructions": parsed["guidance"],
            "pdf_guidance": {key: value for key, value in pdf.items() if key not in ("positions", "seams", "zigzags")},
            "source_discrepancies": [], "whole_source_batch_structurally_reconciled": True,
            "pending": ["canonical identity allocation and admission", "Curriculum/musical review", "runtime note timing and performed audio"],
            "canonical_item_id": None, "canonical_variant_id": None, "fixed_bpm": None, "note_per_click": None,
            "onset_q": None, "duration_q": None, "runtime_eligible": False, "runtime_admitted": False,
            "imported": False, "admitted": False}


def write_candidate(output: Path) -> dict[str, Any]:
    root = _root()
    target = output if output.is_absolute() else root / output
    allowed = root / BUILD_REL
    if not target.parent.exists() or target.parent.is_symlink() or target.parent.resolve() != allowed.resolve():
        raise CandidateError(f"OUTPUT_OUTSIDE_LANE_BUILD {output}")
    if target.suffix != ".json" or target.is_symlink():
        raise CandidateError(f"OUTPUT_INVALID {output}")
    data = (json.dumps(build_candidate(), indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
    try:
        with target.open("xb") as handle:
            handle.write(data)
    except FileExistsError as exc:
        raise CandidateError(f"OUTPUT_EXISTS {output}") from exc
    return {"output": str(target.relative_to(root)), "bytes": len(data), "sha256": digest(data), "positions": 5, "seams": 4}


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
