#!/usr/bin/env python3
"""Detached, source-verified whole Level 20 major-scale synthesis candidate."""

from __future__ import annotations

import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path
import re
import subprocess

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
STEM = "Scale_Exercises_Section_II_Level_20_Major_Scale_Synthesis_Circuit_Two_Octave_Six_String_Neck_Ladder"
TXT_REL = Path(f"Notes/music/guitar project/TXT version/{STEM}.txt")
PDF_REL = Path(f"Notes/music/guitar project/PDF version/{STEM}.pdf")
TXT_BYTES = 144515
TXT_SHA256 = "d64e78142630e4b6e22ce49055df87938062d9051eb44d792a1a46448e54d410"
PDF_BYTES = 108602
PDF_SHA256 = "b3160de6f22ffbb1b2fe8ca42bd02474a813fe2088a747cea628968fc7914dd5"
BUILD_REL = Path("Build/parallel-05/2.3.1.1.1-level020-whole-r01")
KEYS = ("A", "Bb", "B", "C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A")
ROWS = ("e", "B", "G", "D", "A", "E")
TUNING = {"E": 40, "A": 45, "D": 50, "G": 55, "B": 59, "e": 64}
NATURAL_PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
MAJOR_OFFSETS = (0, 2, 4, 5, 7, 9, 11, 12, 14, 16, 17, 19, 21, 23, 24)
FINGERS = (2, 4, 1, 2, 4, 1, 3, 4, 1, 3, 4, 2, 4, 1, 2)
PLACEMENTS = (("E", 0), ("E", 2), ("A", -1), ("A", 0), ("A", 2),
              ("D", -1), ("D", 1), ("D", 2), ("G", -1), ("G", 1),
              ("G", 2), ("B", 0), ("B", 2), ("e", -1), ("e", 0))
ROMANS = ("I", "ii", "iii", "IV", "V", "vi", "vii-dim")
CHORD_SUFFIX = ("", "m", "m", "", "", "m", "dim")
MODULES = (
    (1, "LINEAR SCALE", 30, 5, 1, 30, 3, "eighth notes"),
    (2, "THREE-NOTE ROLL", 78, 16, 13, 3, 3, "eighth-note triplets"),
    (3, "FOUR-NOTE ROLL", 96, 37, 12, 4, 3, "sixteenth notes"),
    (4, "DIATONIC THIRDS", 52, 58, 13, 2, 3, "eighth notes"),
    (5, "DIATONIC TRIADS", 66, 81, 11, 3, 3, "eighth-note triplets"),
)
TXT_REARTICULATE = "Re-articulate the low root immediately and continue into the next module without resetting the pick cycle."
TXT_FINISH = "Finish on the low root, release pressure, move the complete frame one fret, and begin module 1 in the next key."
TXT_RUNG = re.compile(r"^RUNG (\d{2}) OF 13 - ([A-G](?:b|#)?) MAJOR( - OCTAVE)? - ROOT ON LOW E FRET (\d+) - FRAME (\d+)-(\d+)$")
PDF_GUIDANCE = {
    1: ("The 322-note synthesis cell", "113 quarter-note beats", "One uninterrupted cell"),
    2: ("Circuit Map, Pulse Plan, and Chromatic Route", "LEARNING MODE", "113 beats", "8,050 notes"),
    29: ("Full Round-Trip Challenge", "8,050 picked notes", "2,825 quarter-note beats", "Major-scale mastery gate"),
    30: ("Practice Variations, Error Diagnosis, and Recovery Rules", "One note per click", "Native pulse", "Recovery and advancement rules"),
    31: ("Synthesis Circuit Practice Log and Section Completion", "Pulse mode", "Start stroke", "Section II completion check"),
}
TXT_GUIDANCE = (
    "Learning mode: one note per metronome click through the complete circuit.",
    "Native-pulse mode:",
    "- Linear scale: 30 eighth notes = 15 beats",
    "- Three-note roll: 78 triplet eighths = 26 beats",
    "- Four-note roll: 96 sixteenth notes = 24 beats",
    "- Diatonic thirds: 52 eighth notes = 26 beats",
    "- Diatonic triads: 66 triplet eighths = 22 beats",
    "TOTAL: 113 quarter-note beats per 322-note circuit",
    "25 circuits x 322 notes = 8,050 picked notes.",
    "25 circuits x 113 native-pulse beats = 2,825 quarter-note beats.",
)


class CandidateError(ValueError):
    """Pinned source, authored music or output boundary failed closed."""


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _root() -> Path:
    proc = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if proc.returncode or Path(proc.stdout.strip()).resolve() != ROOT.resolve():
        raise CandidateError("REPOSITORY_ROOT_MISMATCH")
    return ROOT


def _pinned(relative: Path, size: int, sha: str) -> bytes:
    path = _root() / relative
    if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(ROOT):
        raise CandidateError(f"SOURCE_PATH_INVALID {relative}")
    data = path.read_bytes()
    if len(data) != size or digest(data) != sha:
        raise CandidateError(f"PINNED_INPUT_DRIFT {relative}: bytes={len(data)} sha256={digest(data)}")
    return data


def _name_pc(name: str) -> int:
    if re.fullmatch(r"[A-G](?:b|#)?", name) is None:
        raise CandidateError(f"NOTE_NAME_INVALID {name}")
    delta = -1 if name.endswith("b") else 1 if name.endswith("#") else 0
    return (NATURAL_PC[name[0]] + delta) % 12


def _scale7(key: str) -> tuple[str, ...]:
    letters = "CDEFGAB"
    start = letters.index(key[0])
    root_pc = _name_pc(key)
    names = []
    for degree, offset in enumerate(MAJOR_OFFSETS[:7]):
        letter = letters[(start + degree) % 7]
        target = (root_pc + offset) % 12
        options = (letter, letter + "b", letter + "#")
        matches = [name for name in options if _name_pc(name) == target]
        if len(matches) != 1:
            raise CandidateError(f"SCALE_SPELLING_INVALID {key} {degree + 1}")
        names.append(matches[0])
    return tuple(names)


def _slots(row: str, label: str, groups: int, size: int, width: int = 3) -> tuple[tuple[str, ...], ...]:
    if not row.startswith(label + "|") or not row.endswith("|"):
        raise CandidateError(f"ROW_LABEL_INVALID {label}")
    parts = row[len(label) + 1:-1].split("|")
    if len(parts) != groups or any(len(part) != size * width for part in parts):
        raise CandidateError(f"ROW_GROUP_SHAPE_INVALID {label}")
    out = []
    for part in parts:
        cells = []
        for i in range(0, len(part), width):
            raw = part[i:i + width]
            token = raw.rstrip("-")
            if not (raw == "-" * width or token.isdigit() and raw == token + "-" * (width - len(token))):
                raise CandidateError(f"ROW_SLOT_INVALID {label} {raw}")
            cells.append(token)
        out.append(tuple(cells))
    return tuple(out)


def _labels(row: str, label: str, groups: int, width: int) -> tuple[str, ...]:
    if not row.startswith(label + "|") or not row.endswith("|"):
        raise CandidateError(f"ROW_LABEL_INVALID {label}")
    parts = row[len(label) + 1:-1].split("|")
    if len(parts) != groups or any(len(part) != width for part in parts):
        raise CandidateError(f"ROW_GROUP_SHAPE_INVALID {label}")
    return tuple(part.rstrip("-") for part in parts)


def _expected_degrees(module: int, direction: str) -> tuple[tuple[int, ...], ...]:
    if module == 1:
        return (tuple(range(1, 16)) + tuple(range(15, 0, -1)),)
    if module == 2:
        return tuple(tuple(range(start, start + 3)) for start in range(1, 14)) if direction == "up" else tuple(
            tuple(range(start, start - 3, -1)) for start in range(15, 2, -1))
    if module == 3:
        return tuple(tuple(range(start, start + 4)) for start in range(1, 13)) if direction == "up" else tuple(
            tuple(range(start, start - 4, -1)) for start in range(15, 3, -1))
    if module == 4:
        return tuple((start, start + 2) for start in range(1, 14)) if direction == "up" else tuple(
            (start, start - 2) for start in range(15, 2, -1))
    return tuple((start, start + 2, start + 4) for start in range(1, 12)) if direction == "up" else tuple(
        (start, start - 2, start - 4) for start in range(15, 4, -1))


def _parse_half(rows: list[str], module: int, direction: str, root: int, key: str,
                source_lines: list[int], pdf_page: int) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    groups, size = (1, 30) if module == 1 else (13, 3) if module == 2 else (12, 4) if module == 3 else (13, 2) if module == 4 else (11, 3)
    extra = 0 if module in (1, 2, 3) else 1
    if len(rows) != extra + 2 + 6 or len(source_lines) != len(rows):
        raise CandidateError(f"HALF_ROW_COUNT_INVALID m{module} {direction}")
    labels = None
    if module == 4:
        labels = _labels(rows[0], "Int", groups, 6)
    elif module == 5:
        labels = _labels(rows[0], "Hrm", groups, 9)
    degrees = _slots(rows[extra], "Deg", groups, size)
    fingers = _slots(rows[extra + 1], "Fng", groups, size)
    tab = {string: _slots(row, string + "  ", groups, size) for string, row in zip(ROWS, rows[extra + 2:], strict=True)}
    expected = _expected_degrees(module, direction)
    contacts = []
    groups_out = []
    for gi, steps in enumerate(expected):
        group_label = labels[gi] if labels else None
        function_root = (steps[0] if direction == "up" else steps[-1])
        if module == 4:
            expected_quality = "M3" if (function_root - 1) % 7 in (0, 3, 4) else "m3"
            if group_label != expected_quality:
                raise CandidateError(f"INTERVAL_QUALITY_INVALID {key} m{module} {direction} g{gi + 1}")
        elif module == 5:
            expected_roman = ROMANS[(function_root - 1) % 7]
            if group_label != expected_roman:
                raise CandidateError(f"TRIAD_FUNCTION_INVALID {key} {direction} g{gi + 1}")
        group_contacts = []
        for si, step in enumerate(steps):
            printed_degree = ((step - 1) % 7 + 1) if module == 1 else step
            if degrees[gi][si] != str(printed_degree) or fingers[gi][si] != str(FINGERS[step - 1]):
                raise CandidateError(f"DEG_FNG_INVALID {key} m{module} {direction} g{gi + 1} s{si + 1}")
            positions = [(string, int(cells[gi][si])) for string, cells in tab.items() if cells[gi][si]]
            if len(positions) != 1:
                raise CandidateError(f"CONTACT_CARDINALITY_INVALID {key} m{module} {direction} g{gi + 1} s{si + 1}")
            string, fret = positions[0]
            expected_string, offset = PLACEMENTS[step - 1]
            if (string, fret) != (expected_string, root + offset) or not root - 1 <= fret <= root + 2:
                raise CandidateError(f"DEG_FRET_INVALID {key} m{module} {direction} g{gi + 1} s{si + 1}")
            if TUNING[string] + fret != TUNING["E"] + root + MAJOR_OFFSETS[step - 1]:
                raise CandidateError(f"PITCH_INVALID {key} m{module} {direction} g{gi + 1} s{si + 1}")
            note = _scale7(key)[(step - 1) % 7]
            contact = {"ordinal_in_module": len(contacts) + 1, "direction": direction,
                       "group": gi + 1, "slot": si + 1, "scale_step": step,
                       "printed_degree": printed_degree, "printed_finger": FINGERS[step - 1],
                       "printed_note_spelling": note, "string": string, "fret": fret,
                       "printed_interval_or_harmony": group_label,
                       "onset_q": None, "duration_q": None, "performed_pick": None,
                       "source_refs": {"txt_degree_line": source_lines[extra],
                                       "txt_finger_line": source_lines[extra + 1],
                                       "txt_tab_line": source_lines[extra + 2 + ROWS.index(string)],
                                       "pdf_page": pdf_page}}
            contacts.append(contact)
            group_contacts.append(contact["ordinal_in_module"])
        groups_out.append({"group": gi + 1, "direction": direction,
                           "printed_interval_or_harmony": group_label,
                           "contact_ordinals": group_contacts})
    return contacts, groups_out


def _module_rows(lines: list[str], header: int, module: int) -> tuple[list[dict[str, object]], str]:
    # header is one-based; each row set carries its own original line numbers.
    if module == 1:
        offsets = ((1, 8, "linear"),)
        footer = TXT_REARTICULATE
        footer_offset = 9
    elif module in (2, 3):
        offsets = ((2, 9, "up"), (11, 18, "down"))
        footer = TXT_REARTICULATE
        footer_offset = 19
    else:
        offsets = ((2, 10, "up"), (12, 20, "down"))
        footer = TXT_REARTICULATE if module == 4 else TXT_FINISH
        footer_offset = 21
    if lines[header + footer_offset - 1] != footer:
        raise CandidateError(f"TXT_MODULE_FOOTER_INVALID m{module} line{header + footer_offset}")
    if module > 1:
        n, noun, count = (13, "TRIPLETS", 39) if module == 2 else (12, "GROUPS", 48) if module == 3 else (13, "PAIRS", 26) if module == 4 else (11, "TRIADS", 33)
        for label_offset, direction in ((1, "ASCENDING"), (10, "DESCENDING")) if module in (2, 3) else ((1, "ASCENDING"), (11, "DESCENDING")):
            if lines[header + label_offset - 1] != f"{direction} - {n} {noun} / {count} NOTES":
                raise CandidateError(f"TXT_HALF_LABEL_INVALID m{module} line{header + label_offset}")
    halves = []
    for start, end, direction in offsets:
        row_lines = list(range(header + start, header + end + 1))
        halves.append({"direction": direction, "rows": [lines[n - 1] for n in row_lines], "line_numbers": row_lines})
    return halves, footer


def _pdf_sections(text: str, module_numbers: tuple[int, ...]) -> dict[int, str]:
    headings = {m: re.search(rf"(?m)^\s+{m}\. {MODULES[m - 1][1]}\b", text) for m in module_numbers}
    if any(match is None for match in headings.values()):
        raise CandidateError(f"PDF_MODULE_HEADING_INVALID {module_numbers}")
    starts = [(m, headings[m].start()) for m in module_numbers]
    if [pos for _, pos in starts] != sorted(pos for _, pos in starts):
        raise CandidateError("PDF_MODULE_ORDER_INVALID")
    return {m: text[pos:starts[i + 1][1] if i + 1 < len(starts) else len(text)]
            for i, (m, pos) in enumerate(starts)}


def _parse_rung(lines: list[str], pages: dict[int, str], rung: int) -> dict[str, object]:
    base = 75 + 106 * (rung - 1)
    match = TXT_RUNG.fullmatch(lines[base - 1])
    if not match or int(match[1]) != rung or match[2] != KEYS[rung - 1] or bool(match[3]) != (rung == 13):
        raise CandidateError(f"TXT_RUNG_HEADING_INVALID {rung}")
    root = int(match[4])
    if (root, int(match[5]), int(match[6])) != (4 + rung, 3 + rung, 6 + rung):
        raise CandidateError(f"TXT_RUNG_FRAME_INVALID {rung}")
    key = KEYS[rung - 1]
    scale = _scale7(key)
    chords = tuple(name + suffix for name, suffix in zip(scale, CHORD_SUFFIX, strict=True))
    expected_scale_line = "Scale tones across two octaves: " + " ".join(scale + scale + (key,))
    expected_chord_line = "Diatonic triads: " + " | ".join(chords)
    if lines[base] != expected_scale_line or lines[base + 1] != expected_chord_line or lines[base + 2] != "322-note synthesis circuit: play modules 1-5 without stopping, then shift one fret.":
        raise CandidateError(f"TXT_RUNG_SCALE_CHORD_INVALID {rung}")
    first_page, second_page = 1 + 2 * rung, 2 + 2 * rung
    for page, subset in ((first_page, (1, 2, 3)), (second_page, (4, 5))):
        text = pages[page]
        if f"Level 20 - Rung {rung:02d}: {key} MAJOR" not in text or f"ROOT E{root}  |  FRAME {root-1}-{root+2}" not in text:
            raise CandidateError(f"PDF_RUNG_IDENTITY_INVALID {rung} p{page}")
        if "Scale: " + " ".join(scale + scale + (key,)) not in text or "Triads: " + " | ".join(chords) not in text:
            raise CandidateError(f"PDF_RUNG_SCALE_CHORD_INVALID {rung} p{page}")
        if subset == (1, 2, 3) and ("PAGE-TO-PAGE TRANSITION" not in text or "DO NOT SHIFT YET" not in text):
            raise CandidateError(f"PDF_RUNG_TRANSITION_INVALID {rung} p{page}")
        if subset == (4, 5) and ("Boundary audit" not in text or "SHIFT AFTER NOTE 322" not in text):
            raise CandidateError(f"PDF_RUNG_BOUNDARY_INVALID {rung} p{page}")
    sections = {**_pdf_sections(pages[first_page], (1, 2, 3)), **_pdf_sections(pages[second_page], (4, 5))}
    records = []
    running = 0
    for number, title, count, relative, *_rest in MODULES:
        header = base + relative
        if lines[header - 1] != f"MODULE {number} - {title} - {count} NOTES":
            raise CandidateError(f"TXT_MODULE_HEADING_INVALID {rung} m{number}")
        page = first_page if number <= 3 else second_page
        if f"{count} notes | {_rest[-1]}" not in sections[number]:
            raise CandidateError(f"PDF_MODULE_PULSE_INVALID {rung} m{number}")
        halves, footer = _module_rows(lines, header, number)
        contacts = []
        groups = []
        source_rows = []
        for half in halves:
            for row, row_line in zip(half["rows"], half["line_numbers"], strict=True):
                if sections[number].count(row) != 1:
                    raise CandidateError(f"PDF_TXT_ROW_MISMATCH rung{rung} m{number} line{row_line}")
                source_rows.append({"txt_line": row_line, "pdf_page": page, "printed_row": row})
            parsed, grouped = _parse_half(half["rows"], number, half["direction"], root, key,
                                          half["line_numbers"], page)
            for item in parsed:
                item["ordinal_in_module"] += len(contacts)
                item["ordinal_in_circuit"] = running + item["ordinal_in_module"]
            for group in grouped:
                group["contact_ordinals"] = [ordinal + len(contacts) for ordinal in group["contact_ordinals"]]
            contacts.extend(parsed)
            groups.extend(grouped)
        if len(contacts) != count or contacts[0]["string"] != "E" or contacts[0]["fret"] != root or contacts[-1]["string"] != "E" or contacts[-1]["fret"] != root:
            raise CandidateError(f"MODULE_COUNT_ROOT_INVALID {rung} m{number}")
        if number == 1 and (contacts[14]["scale_step"], contacts[15]["scale_step"]) != (15, 15):
            raise CandidateError(f"LINEAR_HIGH_ROOT_REATTACK_INVALID {rung}")
        if number > 1 and records[-1]["contacts"][-1]["ordinal_in_circuit"] + 1 != contacts[0]["ordinal_in_circuit"]:
            raise CandidateError(f"MODULE_BOUNDARY_ORDINAL_INVALID {rung} m{number}")
        records.append({"module_number": number, "printed_heading": lines[header - 1],
                        "txt_line_span": [header, header + (9 if number == 1 else 19 if number in (2, 3) else 21)],
                        "pdf_page": page, "printed_pulse_description": _rest[-1],
                        "printed_boundary_instruction": footer, "source_rows": source_rows,
                        "groups": groups, "contacts": contacts, "contact_count": count})
        running += count
    if running != 322 or [r["contact_count"] for r in records] != [30, 78, 96, 52, 66]:
        raise CandidateError(f"RUNG_COUNT_INVALID {rung}")
    return {"rung": rung, "key": key, "root_string": "E", "root_fret": root,
            "frame_frets": [root - 1, root + 2], "scale_seven": scale,
            "diatonic_triads": chords, "txt_heading_line": base,
            "pdf_pages": [first_page, second_page], "modules": records, "contact_count": running}


def build_candidate(txt_data: bytes | None = None, pdf_data: bytes | None = None) -> dict[str, object]:
    txt = _pinned(TXT_REL, TXT_BYTES, TXT_SHA256) if txt_data is None else txt_data
    pdf = _pinned(PDF_REL, PDF_BYTES, PDF_SHA256) if pdf_data is None else pdf_data
    if len(txt) != TXT_BYTES or digest(txt) != TXT_SHA256 or len(pdf) != PDF_BYTES or digest(pdf) != PDF_SHA256:
        raise CandidateError("PINNED_INPUT_DRIFT")
    lines = txt.decode("utf-8").splitlines()
    if len(lines) != 1466 or lines[0] != "SCALE EXERCISES - SECTION II, LEVEL 20" or lines[1452] != "FULL ROUND-TRIP CHALLENGE":
        raise CandidateError("TXT_LEVEL_BOUNDARY_INVALID")
    for phrase in TXT_GUIDANCE:
        if phrase not in lines[:74]:
            raise CandidateError(f"TXT_GUIDANCE_INVALID {phrase}")
    up = "Up:   A -> Bb -> B -> C -> Db -> D -> Eb -> E -> F -> Gb -> G -> Ab -> A"
    down = "Down: Ab -> G -> Gb -> F -> E -> Eb -> D -> Db -> C -> B -> Bb -> A"
    if lines[44:46] != [up, down]:
        raise CandidateError("TXT_ROUTE_INVALID")
    map_row = re.compile(r"^(\d{2})\s+([A-G](?:b|#)?) major( - octave)?\s+fret (\d+)\s+(\d+)-(\d+)\s+322 notes / shift after module 5$")
    for rung, row in enumerate(lines[56:69], 1):
        match = map_row.fullmatch(row)
        if not match or (int(match[1]), match[2], bool(match[3]), int(match[4]), int(match[5]), int(match[6])) != (
                rung, KEYS[rung - 1], rung == 13, 4 + rung, 3 + rung, 6 + rung):
            raise CandidateError(f"TXT_ROUTE_MAP_INVALID {rung}")
    reader = PdfReader(BytesIO(pdf))
    if len(reader.pages) != 31:
        raise CandidateError("PDF_PAGE_COUNT_INVALID")
    pages = {n: reader.pages[n - 1].extract_text(extraction_mode="layout") or "" for n in range(1, 32)}
    for page, text in pages.items():
        if f"Page {page} of 31" not in text:
            raise CandidateError(f"PDF_PAGE_NUMBER_INVALID p{page}")
    for page, phrases in PDF_GUIDANCE.items():
        for phrase in phrases:
            if phrase not in pages[page]:
                raise CandidateError(f"PDF_GUIDANCE_INVALID p{page} {phrase}")
    rungs = [_parse_rung(lines, pages, rung) for rung in range(1, 14)]
    if sum(r["contact_count"] for r in rungs) != 4186:
        raise CandidateError("WHOLE_LEVEL_CONTACT_COUNT_INVALID")
    route = list(range(1, 14)) + list(range(12, 0, -1))
    if len(route) != 25 or 25 * 322 != 8050 or 25 * 113 != 2825:
        raise CandidateError("ROUTE_COUNT_INVALID")
    return {"schema": "fathom.detached-source-candidate.1", "wbs_id": "2.3.1.1.1",
            "section": "II", "level": 20, "rungs": rungs, "rung_count": 13,
            "module_count": 65, "authored_contact_count": 4186,
            "source": {"txt_path": str(TXT_REL), "txt_bytes": TXT_BYTES, "txt_sha256": TXT_SHA256,
                       "pdf_path": str(PDF_REL), "pdf_bytes": PDF_BYTES, "pdf_sha256": PDF_SHA256,
                       "pdf_pages": 31, "selected_pdf_pages": list(range(1, 32))},
            "printed_guidance": {"txt_intro_lines": lines[:74], "txt_closing_lines": lines[1452:],
                                 "pdf_pages": [{"page": p, "extracted_text_sha256": digest(pages[p].encode("utf-8")),
                                                "extracted_text": pages[p]} for p in (1, 2, 29, 30, 31)],
                                 "learning_pulse": "one note per metronome click",
                                 "native_pulse": [{"module": m, "printed_subdivision": pulse, "printed_beats": beats}
                                                  for m, pulse, beats in ((1, "eighth notes", 15), (2, "triplet eighths", 26),
                                                                         (3, "sixteenth notes", 24), (4, "eighth notes", 26),
                                                                         (5, "triplet eighths", 22))],
                                 "native_beats_per_circuit": 113,
                                 "route_rung_indices": route, "route_printed_note_count": 8050,
                                 "route_printed_beat_count": 2825,
                                 "practice_log_values": None, "kind": "printed_instruction"},
            "source_exceptions": [], "canonical_ids": None, "review": "Pending",
            "runtime_eligible": False, "imported": False, "admitted": False,
            "pending": ["Independent Curriculum review", "canonical IDs and runtime admission", "performed mastery gates"]}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    root = _root()
    output = args.output
    if not output.is_absolute() or output.is_symlink() or not output.resolve().is_relative_to(root / BUILD_REL):
        raise CandidateError("OUTPUT_OUTSIDE_ASSIGNED_BUILD")
    data = (json.dumps(build_candidate(), ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as handle:
        handle.write(data)
    print(f"candidate {output} bytes={len(data)} sha256={digest(data)}")


if __name__ == "__main__":
    main()
