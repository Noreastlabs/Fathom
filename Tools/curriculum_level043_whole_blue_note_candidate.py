#!/usr/bin/env python3
"""Detached, source-bound whole-Level43 A-blues workbook candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from pypdf import PdfReader


ROOT_STEM = "Scale_Exercises_Section_V_Level_43_A_Blues_Scale_Map_and_Blue_Note_Control_Fixed_Key_A_Final"
TXT_REL = f"Notes/music/guitar project/TXT version/{ROOT_STEM}.txt"
PDF_REL = f"Notes/music/guitar project/PDF version/{ROOT_STEM}.pdf"
MAP_REL = "Results/parallel-01/exercises/inventory/20260922T180500Z-2.3-curriculum-v1-source-inventory-evidence/curriculum-source-map.json"
MAP_BYTES = 199753
MAP_SHA = "bad5581a04f43ba8baf14db430449e1ccff5cf88f0f7e42198328073b27053d6"
SRC = (24994, "2757cc44d1b231e6e2203b12ba8da82a7d6784db7a11ca94719efc7f34d3804f", 43204, "6641317bad903771dba4a2e50779dd66ed0d34626ca63f356d3d59b955668f2a")
PREDECESSORS = {
    41: ("Scale_Exercises_Section_V_Level_41_A_Minor_Pentatonic_Five_Position_Map_and_Connection_Fixed_Key_A", 30654, "40188b431cf51581e9fe1df01b50b6bb459482fdbf322822d845c2d45a1cb00a", 42356, "97e30c02960dc260a459bb6a4c38cb4d5c36998952ae876264e839bc40f0c576"),
    42: ("Scale_Exercises_Section_V_Level_42_A_Minor_Pentatonic_Horizontal_Movement_and_Articulation_Fixed_Key_A", 30783, "4d658466a731cf3de48c02cd8694651a3294d27af588a344926aa85e2d64f65b", 45764, "fed7a629ecf0c0ff4e7015187ce858a21d333409aedc37bde7b6561b05b5c61d"),
}
PITCH = {"A": 9, "C": 0, "D": 2, "Eb": 3, "E": 4, "G": 7}
DEGREE = {"A": "1", "C": "b3", "D": "4", "Eb": "b5", "E": "5", "G": "b7"}
DEG_TO_NOTE = {v: k for k, v in DEGREE.items()}
OPEN = {"E": 4, "A": 9, "D": 2, "G": 7, "B": 11, "e": 4}
STRINGS = ("e", "B", "G", "D", "A", "E")
MODULE_COUNTS = {"A": (40, 40), "B": (144, 144), "C": (36, 36), "D": (40, 40), "E": (48, 48), "F": (36, 12), "G": (24, 8), "H": (18, 18), "I": (36, 36)}
MODULE_PAGES = {"A": [3], "B": list(range(4, 9)), "C": [9], "D": [10], "E": [11], "F": [12], "G": [13], "H": [14], "I": [15]}
CHROMATIC_SITES = {"E": (10, 11, 12), "A": (5, 6, 7), "D": (12, 13, 14), "G": (7, 8, 9), "B": (15, 16, 17), "e": (10, 11, 12)}


def _pin(path: Path, size: int, sha: str) -> bytes:
    raw = path.read_bytes()
    if len(raw) != size or hashlib.sha256(raw).hexdigest() != sha:
        raise ValueError(f"source identity drift: {path}")
    return raw


def _note_tokens(row: str, prefix: str) -> list[str]:
    if not row.startswith(prefix + "|"):
        raise ValueError(f"wrong row prefix: {row!r}")
    body = row.split("|", 1)[1].rsplit("|", 1)[0].replace("|", "")
    if len(body) % 4:
        raise ValueError(f"unaligned row: {row!r}")
    return [body[i:i + 4].strip("-") for i in range(0, len(body), 4)]


def _tab_cells(row: str, string: str, count: int, aligned: bool = True) -> list[int | None]:
    if not re.match(rf"^\s*{string}\|", row):
        raise ValueError(f"wrong TAB string {string}: {row!r}")
    body = row.split("|", 1)[1]
    if aligned:
        body = body.replace("|", "")
        if len(body) != count * 4:
            raise ValueError(f"unaligned TAB row: {row!r}")
        cells = [body[i:i + 4] for i in range(0, len(body), 4)]
        if any(not re.fullmatch(r"-*\d{0,2}-*", x) for x in cells):
            raise ValueError(f"malformed TAB cell: {row!r}")
        return [int(x.strip("-")) if x.strip("-") else None for x in cells]
    return [int(x) for x in re.findall(r"\d+", body.split("|", 1)[0])]


def _contact(note: str, string: str, fret: int, finger: int | None, picked: bool, articulation: str, source_line: int) -> dict:
    if note not in PITCH or (OPEN[string] + fret) % 12 != PITCH[note] or finger is not None and finger not in (1, 2, 3, 4):
        raise ValueError(f"pitch/finger mismatch at TXT line {source_line}: {note} {string}{fret}")
    return {"note": note, "degree": DEGREE[note], "string": string, "fret": fret, "printed_finger": finger, "printed_pick_attack": picked, "printed_articulation": articulation, "txt_line": source_line, "performed_onset": None, "performed_duration": None, "performed_pick": None}


def _pdf_exact(pdf: str, row: str, page: int) -> None:
    if row not in pdf:
        raise ValueError(f"TXT/PDF row mismatch p{page}: {row!r}")


def _pdf_frets(pdf: str, string: str, frets: list[int], page: int) -> None:
    if not any([int(x) for x in re.findall(r"\d+", line.split("|", 1)[1].split("|", 1)[0])] == frets for line in pdf.splitlines() if re.match(rf"^\s*{string}\|", line)):
        raise ValueError(f"TXT/PDF TAB mismatch p{page}: {string} {frets}")


def _sections(lines: list[str]) -> dict[str, tuple[int, int]]:
    starts = {}
    for i, line in enumerate(lines):
        match = re.match(r"MODULE ([A-I]) - ", line)
        if match:
            starts[match.group(1)] = i
    if list(starts) != list("ABCDEFGHI"):
        raise ValueError("nine module headings/order drift")
    result = {}
    for n, key in enumerate(starts):
        start = starts[key]
        stop = starts[list(starts)[n + 1]] if n < 8 else next(i for i in range(start, len(lines)) if lines[i] == "PRACTICE PROGRESSION")
        result[key] = (start, stop)
    return result


def _aligned_unit(lines: list[str], index: int, page: int, pdf: str, module: str, label: str) -> dict:
    count = len(_note_tokens(lines[index], "Nte"))
    rows = lines[index:index + 9]
    if len(rows) != 9:
        raise ValueError("short aligned unit")
    notes = _note_tokens(rows[0], "Nte")
    degrees = _note_tokens(rows[1], "Deg")
    fingers = _note_tokens(rows[2], "Fng")
    if len(notes) != len(degrees) or len(notes) != len(fingers):
        raise ValueError("aligned note/degree/finger length")
    for row in rows:
        _pdf_exact(pdf, row, page)
    tabs = {s: _tab_cells(rows[3 + j], s, count) for j, s in enumerate(STRINGS)}
    contacts = []
    for k, (note, degree, finger) in enumerate(zip(notes, degrees, fingers)):
        loc = [(s, cells[k]) for s, cells in tabs.items() if cells[k] is not None]
        if len(loc) != 1 or degree != DEGREE.get(note) or not finger.isdigit():
            raise ValueError(f"aligned contact mismatch {module} {label} slot{k + 1}")
        s, fret = loc[0]
        contacts.append(_contact(note, s, fret, int(finger), True, "picked scale contact", index + 4 + STRINGS.index(s)))
    return {"module": module, "label": label, "pdf_page": page, "txt_line": index + 1, "source_rows": rows, "contacts": contacts, "sounding_tones": len(contacts), "printed_pick_attacks": len(contacts)}


def _module_ab(key: str, lines: list[str], bounds: tuple[int, int], pdf_pages: list[str]) -> list[dict]:
    start, stop = bounds
    indices = [i for i in range(start, stop) if lines[i].startswith("Nte|")]
    expected = 4 if key == "A" else 10
    if len(indices) != expected:
        raise ValueError(f"module {key} aligned unit count drift")
    units = []
    for n, idx in enumerate(indices):
        page = 3 if key == "A" else 4 + n // 2
        label = (("one octave", "two octaves")[n // 2] if key == "A" else f"P{n // 2 + 1}") + (" ascending" if n % 2 == 0 else " descending")
        unit = _aligned_unit(lines, idx, page, pdf_pages[page - 1], key, label)
        units.append(unit)
    if key == "A" and [u["sounding_tones"] for u in units] != [7, 7, 13, 13]:
        raise ValueError("module A reference counts drift")
    if key == "B" and [u["sounding_tones"] for u in units] != [14, 14, 15, 15, 15, 15, 14, 14, 14, 14]:
        raise ValueError("module B position counts drift")
    return units


def _module_c(lines: list[str], bounds: tuple[int, int], pdf: str) -> list[dict]:
    start, stop = bounds
    indices = [i for i in range(start, stop) if lines[i].startswith("Nte|")]
    if len(indices) != 6:
        raise ValueError("module C string count drift")
    units = []
    for idx, string in zip(indices, ("E", "A", "D", "G", "B", "e")):
        rows = lines[idx:idx + 4]
        notes = _note_tokens(rows[0], "Nte")
        degrees = _note_tokens(rows[1], "Deg")
        picks = _note_tokens(rows[3], "Pck")
        frets = _tab_cells(rows[2], string, 6)
        if notes != ["D", "Eb", "E", "E", "Eb", "D"] or degrees != [DEGREE[n] for n in notes] or picks != ["D", "U", "D", "U", "D", "U"] or any(f is None for f in frets):
            raise ValueError(f"module C row drift {string}")
        for row in rows[:3]:
            _pdf_exact(pdf, row, 9)
        contacts = [_contact(note, string, fret, None, True, "picked triplet; printed D/U sequence", idx + 3) for note, fret in zip(notes, frets)]
        units.append({"module": "C", "label": f"{string} string up/down triplets", "pdf_page": 9, "txt_line": idx + 1, "source_rows": rows, "printed_pick_sequence": picks, "contacts": contacts, "sounding_tones": 6, "printed_pick_attacks": 6})
    return units


def _module_d(lines: list[str], bounds: tuple[int, int], pdf: str) -> list[dict]:
    start, stop = bounds
    headings = [i for i in range(start, stop) if re.match(r"P[1-5] - ", lines[i])]
    if len(headings) != 5:
        raise ValueError("module D position count drift")
    units = []
    for n, idx in enumerate(headings):
        span = lines[idx:headings[n + 1] if n < 4 else stop]
        if not any(x.startswith("UP   C-D-Eb-E") for x in span) or not any(x.startswith("DOWN G-E-Eb-D") for x in span):
            raise ValueError("module D degree/note guide drift")
        tab = [(idx + j, x) for j, x in enumerate(span) if re.match(r"^[eBGDAE]\|", x) and re.search(r"\d", x)]
        if len(tab) != 2:
            raise ValueError("module D TAB groups drift")
        groups = (("C", "D", "Eb", "E"), ("G", "E", "Eb", "D"))
        contacts = []
        for (line_idx, row), notes in zip(tab, groups):
            s = row[0]
            frets = _tab_cells(row, s, 4, False)
            if len(frets) != 4:
                raise ValueError("module D four-note group drift")
            _pdf_frets(pdf, s, frets, 10)
            contacts.extend(_contact(note, s, fret, None, True, "picked straight sixteenths", line_idx + 1) for note, fret in zip(notes, frets))
        units.append({"module": "D", "label": lines[idx], "pdf_page": 10, "txt_line": idx + 1, "source_lines": span, "contacts": contacts, "sounding_tones": 8, "printed_pick_attacks": 8})
    return units


def _module_e(lines: list[str], bounds: tuple[int, int], pdf: str) -> list[dict]:
    start, stop = bounds
    indices = [i for i in range(start, stop) if lines[i].startswith("PASS A degrees:")]
    if len(indices) != 6:
        raise ValueError("module E six-string count drift")
    units = []
    for idx, string in zip(indices, ("E", "A", "D", "G", "B", "e")):
        if "4-b5-5-4" not in lines[idx] or "4-b5~~~~-5-4" not in lines[idx + 2]:
            raise ValueError(f"module E degree guide drift {string}")
        contacts = []
        for variant, line_idx in (("passing", idx + 1), ("resting", idx + 3)):
            row = lines[line_idx]
            frets = _tab_cells(row, string, 4, False)
            if len(frets) != 4 or ("~~~~" in row) != (variant == "resting"):
                raise ValueError(f"module E contrast drift {string}")
            _pdf_exact(pdf, row, 11)
            contacts.extend(_contact(note, string, fret, None, True, "picked; Eb " + variant + (" sustain marked" if variant == "resting" and note == "Eb" else ""), line_idx + 1) for note, fret in zip(("D", "Eb", "E", "D"), frets))
        units.append({"module": "E", "label": f"{string} passing/resting contrast", "pdf_page": 11, "txt_line": idx + 1, "source_rows": lines[idx:idx + 5], "contacts": contacts, "sounding_tones": 8, "printed_pick_attacks": 8})
    return units


def _module_f(lines: list[str], bounds: tuple[int, int], pdf: str) -> list[dict]:
    start, stop = bounds
    entries = [(i, line) for i, line in enumerate(lines[start:stop], start) if re.match(r"^(Low E|A\s|D\s|G\s|B\s|High e)\s+\w\|", line)]
    if len(entries) != 6:
        raise ValueError("module F six chain count drift")
    units = []
    for (idx, row), string in zip(entries, ("E", "A", "D", "G", "B", "e")):
        match = re.search(r"([eBGDAE])\|([^|]+)\|", row)
        if not match or match.group(1) != string or match.group(2).count("/") != 2 or match.group(2).count("\\") != 2:
            raise ValueError("module F slide glyph drift")
        frets = [int(x) for x in re.findall(r"\d+", match.group(2))]
        if len(frets) != 6:
            raise ValueError("module F six frets drift")
        _pdf_frets(pdf, string, frets, 12)
        notes = ("D", "Eb", "E", "E", "Eb", "D")
        contacts = [_contact(note, string, fret, None, j in (0, 3), "picked slide start" if j in (0, 3) else "unpicked slide arrival", idx + 1) for j, (note, fret) in enumerate(zip(notes, frets))]
        units.append({"module": "F", "label": row.split("  ", 1)[0], "pdf_page": 12, "txt_line": idx + 1, "source_row": row, "contacts": contacts, "sounding_tones": 6, "printed_pick_attacks": 2})
    return units


def _module_g(lines: list[str], bounds: tuple[int, int], pdf: str) -> list[dict]:
    start, stop = bounds
    headings = [i for i in range(start, stop) if re.match(r"^P[1-4] -> P[2-5] - ", lines[i])]
    if len(headings) != 4:
        raise ValueError("module G seam count drift")
    units = []
    for n, idx in enumerate(headings):
        span = lines[idx:headings[n + 1] if n < 3 else stop]
        if "Degrees: b3-4-b5-5 | b7-1" not in span or "Notes:   C-D-Eb-E | G-A" not in span or not any(x.startswith("Reverse variation: 1-b7-5-b5-4-b3") for x in span):
            raise ValueError("module G phrase/reverse guidance drift")
        tabs = [(idx + j, x) for j, x in enumerate(span) if re.match(r"^[eBGDAE]\|", x) and re.search(r"\d", x)]
        if len(tabs) != 2:
            raise ValueError("module G two string groups drift")
        tabs.sort(key=lambda item: len(re.findall(r"\d+", item[1])), reverse=True)
        contacts = []
        for (line_idx, row), notes in zip(tabs, (("C", "D", "Eb", "E"), ("G", "A"))):
            string = row[0]
            frets = _tab_cells(row, string, len(notes), False)
            if len(frets) != len(notes):
                raise ValueError("module G phrase fret count drift")
            _pdf_exact(pdf, row, 13)
            contacts.extend(_contact(note, string, fret, None, j == 0, "picked group start" if j == 0 else "unpicked hammer/slide arrival", line_idx + 1) for j, (note, fret) in enumerate(zip(notes, frets)))
        units.append({"module": "G", "label": lines[idx], "pdf_page": 13, "txt_line": idx + 1, "source_lines": span, "reverse_variation": {"kind": "printed_instruction_without_full_TAB", "degrees": ["1", "b7", "5", "b5", "4", "b3"], "authored_reverse_contacts": None}, "contacts": contacts, "sounding_tones": 6, "printed_pick_attacks": 2})
    return units


def _module_h(lines: list[str], bounds: tuple[int, int], pdf: str) -> list[dict]:
    start, stop = bounds
    headings = [i for i in range(start, stop) if re.match(r"^[123]\. b5 ON THE ", lines[i])]
    if len(headings) != 3:
        raise ValueError("module H study count drift")
    units = []
    for idx in headings:
        rows = lines[idx + 1:idx + 4]
        if len(rows) != 3 or not rows[0].startswith("Cnt|"):
            raise ValueError("module H grid drift")
        notes = _note_tokens(rows[1], "Nte")
        frets = _tab_cells(rows[2], "G", len(notes))
        for row in rows:
            _pdf_exact(pdf, row, 14)
        if len(notes) not in (8, 12):
            raise ValueError("module H count grid drift")
        contacts = []
        slots = []
        for k, (note, fret) in enumerate(zip(notes, frets)):
            if note == "R":
                if fret is not None:
                    raise ValueError("module H rest has contact")
                slots.append({"slot": k + 1, "kind": "printed_rest", "contact": None, "performed_onset": None, "performed_duration": None})
            else:
                if fret is None or note not in ("D", "Eb", "E"):
                    raise ValueError("module H note/contact mismatch")
                contact = _contact(note, "G", fret, None, True, "picked displacement", idx + 4)
                contacts.append(contact)
                slots.append({"slot": k + 1, "kind": "printed_note", "contact": contact, "performed_onset": None, "performed_duration": None})
        if len(contacts) != 6:
            raise ValueError("module H six tones/study drift")
        units.append({"module": "H", "label": lines[idx], "pdf_page": 14, "txt_line": idx + 1, "source_rows": rows, "slots": slots, "contacts": contacts, "sounding_tones": 6, "printed_pick_attacks": 6})
    return units


def _module_i(lines: list[str], bounds: tuple[int, int], pdf: str) -> list[dict]:
    start, stop = bounds
    headings = [i for i in range(start, stop) if re.match(r"^[1-6]\. (LOW-E|A-STRING|D-STRING|G-STRING|B-STRING|HIGH-E) ", lines[i])]
    if len(headings) != 6:
        raise ValueError("module I audit card count drift")
    units = []
    for n, idx in enumerate(headings):
        span = lines[idx:headings[n + 1] if n < 5 else stop]
        row = span[1]
        string = row[0]
        frets = _tab_cells(row, string, 6, False)
        if len(frets) != 6 or not span[2].startswith("Degrees: ") or not span[3].startswith("Audit: ") or not span[4].startswith("Repair: "):
            raise ValueError("module I card structure drift")
        degrees = re.findall(r"b[357]|[145]", span[2].split(": ", 1)[1])
        if len(degrees) != 6:
            raise ValueError("module I six degrees drift")
        _pdf_exact(pdf, row, 15)
        if span[2].split(": ", 1)[1] not in pdf:
            raise ValueError("TXT/PDF audit degrees mismatch")
        contacts = [_contact(DEG_TO_NOTE[degree], string, fret, None, True, "picked audit; final sustain" if j == 5 and "~~~~" in row else "picked audit", idx + 2) for j, (degree, fret) in enumerate(zip(degrees, frets))]
        units.append({"module": "I", "label": lines[idx], "pdf_page": 15, "txt_line": idx + 1, "source_lines": span, "audit_role": span[3], "repair_instruction": span[4], "contacts": contacts, "sounding_tones": 6, "printed_pick_attacks": 6})
    return units


def build_candidate(root: Path) -> dict:
    txt_raw = _pin(root / TXT_REL, SRC[0], SRC[1])
    _pin(root / PDF_REL, SRC[2], SRC[3])
    source_map_raw = _pin(root / MAP_REL, MAP_BYTES, MAP_SHA)
    source_map = json.loads(source_map_raw)
    row = source_map["rows"][42]
    if any(row[k] != v for k, v in {"level": 43, "section": "V", "wbs_owner": "2.3.1.1.1", "txt_path": TXT_REL, "txt_bytes": SRC[0], "txt_sha256": SRC[1], "pdf_path": PDF_REL, "pdf_bytes": SRC[2], "pdf_sha256": SRC[3], "pair_status": "exact_stem_pair", "review": "Pending", "conversion_status": "not_converted", "stable_ids_assigned": False, "runtime_eligible": False, "imported": False, "admitted": False}.items()):
        raise ValueError("source-map row 43 drift")
    predecessors = []
    for number, (stem, tb, th, pb, ph) in PREDECESSORS.items():
        tp = f"Notes/music/guitar project/TXT version/{stem}.txt"
        pp = f"Notes/music/guitar project/PDF version/{stem}.pdf"
        _pin(root / tp, tb, th)
        _pin(root / pp, pb, ph)
        predecessors.append({"level": number, "txt_path": tp, "txt_bytes": tb, "txt_sha256": th, "pdf_path": pp, "pdf_bytes": pb, "pdf_sha256": ph, "role": "read-only predecessor identity"})
    reader = PdfReader(root / PDF_REL)
    if len(reader.pages) != 17:
        raise ValueError("PDF page count drift")
    pages = [page.extract_text() or "" for page in reader.pages]
    for i, page in enumerate(pages, 1):
        if f"Page {i} of 17" not in page:
            raise ValueError(f"PDF page identity drift: {i}")
    lines = txt_raw.decode("utf-8").splitlines()
    bounds = _sections(lines)
    parsed = {}
    parsed["A"] = _module_ab("A", lines, bounds["A"], pages)
    parsed["B"] = _module_ab("B", lines, bounds["B"], pages)
    parsed["C"] = _module_c(lines, bounds["C"], pages[8])
    parsed["D"] = _module_d(lines, bounds["D"], pages[9])
    parsed["E"] = _module_e(lines, bounds["E"], pages[10])
    parsed["F"] = _module_f(lines, bounds["F"], pages[11])
    parsed["G"] = _module_g(lines, bounds["G"], pages[12])
    parsed["H"] = _module_h(lines, bounds["H"], pages[13])
    parsed["I"] = _module_i(lines, bounds["I"], pages[14])
    modules = []
    for name, units in parsed.items():
        counts = (sum(u["sounding_tones"] for u in units), sum(u["printed_pick_attacks"] for u in units))
        if counts != MODULE_COUNTS[name]:
            raise ValueError(f"module {name} count drift: {counts}")
        start, stop = bounds[name]
        modules.append({"module": name, "unit_count": len(units), "sounding_tones": counts[0], "printed_pick_attacks": counts[1], "pdf_pages": MODULE_PAGES[name], "txt_start_line": start + 1, "txt_end_line": stop, "full_source_lines": lines[start:stop], "units": units})
    if (sum(x["sounding_tones"] for x in modules), sum(x["printed_pick_attacks"] for x in modules)) != (422, 382):
        raise ValueError("whole-workout count drift")
    txt = txt_raw.decode("utf-8")
    required_txt = ("Notes:    A C D Eb E G", "Complete written workout = 422 sounding tones / 382 pick attacks", "PRACTICE PROGRESSION", "ERROR DIAGNOSIS", "ADVANCEMENT RULES", "MASTERY GATE BEFORE LEVEL 44", "PRACTICE LOG", "NEXT LEVEL")
    for phrase in required_txt:
        if phrase not in txt:
            raise ValueError(f"Level43 TXT guidance drift: {phrase}")
    for phrase in ("After the basic workbook is clean", "Hold Eb for one, two, and four beats", "Record one pass and listen for rushed semitone motion"):
        if phrase not in pages[15]:
            raise ValueError(f"PDF-only variation drift: {phrase}")
    for phrase in ("LEVEL 43 MASTERY GATE", "Completion audit", "Practice log", "NEXT"):
        if phrase not in pages[16]:
            raise ValueError(f"PDF closing guidance drift: {phrase}")
    return {
        "schema": "fathom.detached-source-candidate.1", "section": "V", "level": 43, "wbs_id": "2.3.1.1.1",
        "source": {"txt_path": TXT_REL, "txt_bytes": SRC[0], "txt_sha256": SRC[1], "pdf_path": PDF_REL, "pdf_bytes": SRC[2], "pdf_sha256": SRC[3], "pdf_pages": 17, "source_map_path": MAP_REL, "source_map_sha256": MAP_SHA, "source_map_row": row, "predecessors": predecessors},
        "scale": {"tonic": "A", "notes": ["A", "C", "D", "Eb", "E", "G"], "degrees": ["1", "b3", "4", "b5", "5", "b7"], "blue_note": {"note": "Eb", "degree": "b5", "core_sites": [{"string": s, "frets": list(frets)} for s, frets in CHROMATIC_SITES.items()], "extension": {"string": "A", "frets": [17, 18, 19]}}},
        "modules": modules, "module_count": 9, "sounding_tone_count": 422, "printed_pick_attack_count": 382,
        "printed_guidance": {"kind": "printed_instruction", "txt_full_text": txt, "pdf_extracted_pages": [{"page": i + 1, "extracted_text": page} for i, page in enumerate(pages)], "core_alternatives": ["D-start/U-start", "pentatonic skeleton only", "b5 accent then equal volume", "legato after picked triplets", "pass/rest role reversal", "G reverse degrees without authored TAB"], "pdf_only_post_clean_variations": pages[15].split("After the basic workbook is clean", 1)[1].split("Advancement rules", 1)[0]},
        "source_exceptions": [{"code": "PDF_ONLY_POST_CLEAN_VARIATIONS", "status": "Pending Curriculum review", "source": "PDF p16", "decision": "Preserve six PDF-only post-clean variations as instruction, without adding notes to the 422-tone core or inventing performance."}],
        "music_row_exceptions": [], "canonical_ids": None, "review": "Pending", "runtime_eligible": False, "imported": False, "admitted": False, "performed_tempo": None, "performed_mastery": None,
        "pending": ["Curriculum review of source-specific variations", "independent musical review", "canonical IDs and runtime admission", "performed mastery gate"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    candidate = build_candidate(args.root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(candidate, sort_keys=True, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"LEVEL43 CANDIDATE PASS modules=9 tones=422 picked_marks=382 output={args.output}")


if __name__ == "__main__":
    main()
