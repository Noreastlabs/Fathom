#!/usr/bin/env python3
"""Detached, source-bound whole-Level53 triad workbook candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from pypdf import PdfReader


STEM = "Guitar_Exercises_Section_VI_Level_53_Major_and_Minor_Triads_Across_Four_Adjacent_Three_String_Sets"
TXT_REL = f"Notes/music/guitar project/TXT version/{STEM}.txt"
PDF_REL = f"Notes/music/guitar project/PDF version/{STEM}.pdf"
TXT_SIZE, TXT_SHA = 19373, "eeedc261db89d3421fafc116e7352bbf8a3e3f6b7eddfd822ed6e4c731e0538e"
PDF_SIZE, PDF_SHA = 58492, "5e016f98623dc4362b2e3fc9b2d1cf1fb6c8692d6312d5b30a65234d47fa20ae"
MAP_REL = "Results/parallel-01/exercises/inventory/20260922T180500Z-2.3-curriculum-v1-source-inventory-evidence/curriculum-source-map.json"
MAP_SIZE, MAP_SHA = 199753, "bad5581a04f43ba8baf14db430449e1ccff5cf88f0f7e42198328073b27053d6"
SETS = {"123": ("G", "B", "e"), "234": ("D", "G", "B"), "345": ("A", "D", "G"), "456": ("E", "A", "D")}
SET_NAMES = {"G-B-e": "123", "D-G-B": "234", "A-D-G": "345", "E-A-D": "456"}
OPEN = {"E": 4, "A": 9, "D": 2, "G": 7, "B": 11, "e": 4}
PC = {"C": 0, "C#": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9, "Bb": 10, "B": 11}
ROOTS = ("C", "D", "E", "F", "G", "A", "B")
INV = ("RP", "1st", "2nd")
DEGREES = {("major", "RP"): ("1", "3", "5"), ("major", "1st"): ("3", "5", "1"), ("major", "2nd"): ("5", "1", "3"), ("minor", "RP"): ("1", "b3", "5"), ("minor", "1st"): ("b3", "5", "1"), ("minor", "2nd"): ("5", "1", "b3")}
INTERVAL = {"1": 0, "b3": 3, "3": 4, "5": 7}
COUNTS = {"A": 0, "B": 672, "C": 96, "D": 96, "E": 128, "F": 64, "G": 64, "H": 128}


def _pin(path: Path, size: int, sha: str) -> bytes:
    raw = path.read_bytes()
    if len(raw) != size or hashlib.sha256(raw).hexdigest() != sha:
        raise ValueError(f"source identity drift: {path}")
    return raw


def _source_map(root: Path) -> dict:
    row = json.loads(_pin(root / MAP_REL, MAP_SIZE, MAP_SHA))["rows"][52]
    expected = {"level": 53, "section": "VI", "wbs_owner": "2.3.1.2.1", "txt_path": TXT_REL, "txt_bytes": TXT_SIZE, "txt_sha256": TXT_SHA, "pdf_path": PDF_REL, "pdf_bytes": PDF_SIZE, "pdf_sha256": PDF_SHA, "pair_status": "exact_stem_pair", "representative_status": "outside_representative_package", "representative_item_id": None, "conversion_status": "not_converted", "stable_ids_assigned": False, "review": "Pending", "runtime_eligible": False, "imported": False, "admitted": False}
    if any(row.get(k) != v for k, v in expected.items()):
        raise ValueError("Level53 source-map identity/status drift")
    return row


def _bounds(lines: list[str]) -> dict[str, tuple[int, int]]:
    headings = [(m.group(1), i) for i, s in enumerate(lines) if (m := re.match(r"MODULE ([A-H]) - ", s))]
    if [x[0] for x in headings] != list("ABCDEFGHH"):
        raise ValueError("module heading/order drift")
    end = next(i for i, s in enumerate(lines) if s == "EAR TRAINING, RANDOM FORMATION, AND MASTERY")
    return {name + ("_minor" if name == "H" and n == 8 else ""): (i, headings[n + 1][1] if n + 1 < len(headings) else end) for n, (name, i) in enumerate(headings)}


def _cells(row: str, label: str, count: int) -> list[str]:
    if not re.match(r"^" + re.escape(label) + r"\s*\|", row):
        raise ValueError(f"{label} row drift: {row!r}")
    values = [v.strip() for v in row.split("|")[1:]]
    if values and values[-1] == "":
        values.pop()
    if len(values) != count:
        raise ValueError(f"{label} cell count drift: {row!r}")
    return values


def _fret_tuple(text: str) -> tuple[int, int, int]:
    parts = text.split("-")
    if len(parts) != 3 or any(not x.isdigit() for x in parts):
        raise ValueError(f"triad fret syntax drift: {text}")
    return tuple(map(int, parts))


def _degree_tuple(text: str) -> tuple[str, str, str]:
    parts = tuple(text.split("-"))
    if len(parts) != 3 or any(x not in INTERVAL for x in parts):
        raise ValueError(f"degree syntax drift: {text}")
    return parts


def _pitch(root: str, quality: str, inversion: str, set_id: str, frets: tuple[int, int, int], degrees: tuple[str, str, str]) -> list[dict]:
    if quality not in ("major", "minor") or degrees != DEGREES[quality, inversion]:
        raise ValueError(f"quality/inversion degree drift: {root} {quality} {inversion} {degrees}")
    notes = []
    for string, fret, degree in zip(SETS[set_id], frets, degrees):
        pc = (OPEN[string] + fret) % 12
        if pc != (PC[root] + INTERVAL[degree]) % 12:
            raise ValueError(f"triad pitch drift: {root} {quality} {inversion} {set_id} {string}{fret} {degree}")
        notes.append({"string": string, "fret": fret, "degree": degree, "pitch_class": pc})
    return notes


def _pdf_has(page: str, value: str, label: str) -> None:
    if re.sub(r"\s+", "", value) not in re.sub(r"\s+", "", page):
        raise ValueError(f"TXT/PDF {label} mismatch: {value!r}")


def _attack(module: str, unit: str, n: int, kind: str, line: int, page: int, *, string: str | None = None, fret: int | None = None, chord: str | None = None, degree: str | None = None, symbol: str | None = None) -> dict:
    return {"module": module, "unit": unit, "ordinal": n, "kind": kind, "printed_symbol": symbol, "string": string, "fret": fret, "chord": chord, "degree": degree, "txt_line": line, "pdf_page": page, "performed_onset": None, "performed_duration": None, "performed_pick": None, "performed_quality": None}


def _a_formulas(lines: list[str], span: tuple[int, int], pages: list[str]) -> dict:
    start, stop = span
    result = {}
    current = None
    for i in range(start, stop):
        if m := re.match(r"STRINGS ([1-4]-[2-5]-[3-6]) - ([A-Ga-g]-[A-Ga-g]-[A-Ga-g])", lines[i]):
            current = SET_NAMES[m.group(2)]
        elif m := re.match(r"(MAJOR|MINOR) (RP|1st|2nd)\s+frets (r(?:[+-]\d+)?\s+r(?:[+-]\d+)?\s+r(?:[+-]\d+)?)\s+degrees ([b\d-]+)\s+fingers ([1-4]-[1-4]-[1-4])", lines[i]):
            if current is None:
                raise ValueError("formula before set")
            quality, inv, frets, deg, fingers = m.groups()
            offsets = tuple(0 if x == "r" else int(x[1:]) for x in frets.split())
            if _degree_tuple(deg) != DEGREES[quality.lower(), inv]:
                raise ValueError("formula degree drift")
            key = (current, quality.lower(), inv)
            if key in result:
                raise ValueError("duplicate formula")
            result[key] = {"set": current, "quality": quality.lower(), "inversion": inv, "relative_frets": frets.split(), "offsets": offsets, "degrees": deg, "fingers": fingers.split("-"), "txt_line": i + 1, "pdf_page": 2, "source_row": lines[i]}
    if len(result) != 24 or "168 formations" not in "\n".join(lines[start:stop]):
        raise ValueError("24 formulas/168 silent audit drift")
    for formula in result.values():
        _pdf_has(pages[1], formula["degrees"], "formula degree")
    return result


def _b(lines: list[str], span: tuple[int, int], pages: list[str], formulas: dict) -> tuple[list[dict], dict]:
    start, stop = span
    units, lookup = [], {}
    set_id = None
    for i in range(start, stop):
        if m := re.match(r"STRINGS [1-4]-[2-5]-[3-6] - (G-B-e|D-G-B|A-D-G|E-A-D)$", lines[i]):
            set_id = SET_NAMES[m.group(1)]
            page = list(SETS).index(set_id) + 3
            if "168 ATTACKS" not in pages[page - 1]:
                raise ValueError("PDF family count drift")
        elif m := re.match(r"^([CDEFGAB])\s*\|", lines[i]):
            if set_id is None:
                raise ValueError("family row before set")
            fields = _cells(lines[i], m.group(1), 7)
            root = m.group(1)
            spelling = fields[0]
            if "/" not in spelling:
                raise ValueError("major/minor spelling drift")
            major_spell, minor_spell = (x.strip().split("-") for x in spelling.split("/"))
            if len(major_spell) != 3 or len(minor_spell) != 3:
                raise ValueError("triad spelling length drift")
            for quality, spell in (("major", major_spell), ("minor", minor_spell)):
                if [PC[x] for x in spell] != [(PC[root] + n) % 12 for n in (0, 4 if quality == "major" else 3, 7)]:
                    raise ValueError(f"spelling pitch drift: {root} {quality}")
            for j, fret_text in enumerate(fields[1:]):
                quality, inv = ("major" if j < 3 else "minor"), INV[j % 3]
                fret = _fret_tuple(fret_text)
                formula = formulas[(set_id, quality, inv)]
                if tuple(x - fret[0] for x in fret) != formula["offsets"]:
                    raise ValueError(f"relative formula drift: {root} {set_id} {quality} {inv}")
                notes = _pitch(root, quality, inv, set_id, fret, DEGREES[quality, inv])
                _pdf_has(pages[page - 1], fret_text, "family fret")
                name = root + ("m" if quality == "minor" else "")
                key = (set_id, name, inv)
                if key in lookup:
                    raise ValueError("duplicate B shape")
                attacks = [_attack("B", f"{set_id}:{name}:{inv}", k + 1, "blocked triad" if k == 0 else "individual arpeggio pick", i + 1, page, string=notes[k - 1]["string"] if k else None, fret=notes[k - 1]["fret"] if k else None, chord=name, degree=notes[k - 1]["degree"] if k else None, symbol="BLOCK" if k == 0 else notes[k - 1]["string"]) for k in range(4)]
                unit = {"set": set_id, "root": root, "chord": name, "quality": quality, "inversion": inv, "frets": fret, "degrees": DEGREES[quality, inv], "spelling": spell, "notes": notes, "active_strings": SETS[set_id], "muted_strings": [s for s in ("E", "A", "D", "G", "B", "e") if s not in SETS[set_id]], "source_row": lines[i], "txt_line": i + 1, "pdf_page": page, "attacks": attacks}
                lookup[key] = unit
                units.append(unit)
    if len(units) != 168 or sum(len(x["attacks"]) for x in units) != 672:
        raise ValueError("B 168 shapes/672 attacks drift")
    if [u["set"] for u in units[::42]] != list(SETS):
        raise ValueError("B set order drift")
    return units, lookup


def _shape(name: str, inv: str, set_id: str, frets: str, degrees: str, lookup: dict, *, allow_octave: bool = False) -> list[dict]:
    quality = "minor" if name.endswith("m") else "major"
    root = name[:-1] if quality == "minor" else name
    fret = _fret_tuple(frets)
    deg = _degree_tuple(degrees)
    notes = _pitch(root, quality, inv, set_id, fret, deg)
    if root in ROOTS:
        reference = lookup[(set_id, name, inv)]["frets"]
        if fret != reference and not (allow_octave and all((a - b) % 12 == 0 for a, b in zip(fret, reference))):
            raise ValueError(f"B shape mismatch: {name} {inv} {set_id} {fret} vs {reference}")
    return notes


def _c(lines: list[str], span: tuple[int, int], pages: list[str], lookup: dict) -> list[dict]:
    start, stop = span
    units = []
    name = inv = None
    for i in range(start, stop):
        if lines[i] in ("C MAJOR", "C MINOR", "G MAJOR", "G MINOR"):
            root, quality = lines[i].split()
            name = root + ("m" if quality == "MINOR" else "")
        elif lines[i] in ("Root position", "First inversion", "Second inversion"):
            inv = {"Root position": "RP", "First inversion": "1st", "Second inversion": "2nd"}[lines[i]]
        elif lines[i].startswith("Set |"):
            if name is None or inv is None:
                raise ValueError("C grid context drift")
            sets = _cells(lines[i], "Set", 8)
            frets = _cells(lines[i + 1], "Fret", 8)
            degrees = _cells(lines[i + 2], "Deg", 8)
            if sets != ["123", "234", "345", "456", "456", "345", "234", "123"]:
                raise ValueError("C set transfer route drift")
            page = 7 if name.startswith("C") else 8
            for row in lines[i:i + 3]:
                _pdf_has(pages[page - 1], row, "C grid")
            attacks = []
            for k, (set_id, fret, deg) in enumerate(zip(sets, frets, degrees)):
                _shape(name, inv, set_id, fret, deg, lookup)
                attacks.append(_attack("C", f"{name}:{inv}", k + 1, "blocked triad", i + 1, page, chord=name, symbol=set_id))
            units.append({"chord": name, "inversion": inv, "set_route": sets, "frets": frets, "degrees": degrees, "source_rows": lines[i:i + 3], "txt_line": i + 1, "pdf_page": page, "attacks": attacks})
    if len(units) != 12 or sum(len(x["attacks"]) for x in units) != 96:
        raise ValueError("C transfer count drift")
    return units


def _d(lines: list[str], span: tuple[int, int], pages: list[str], lookup: dict) -> list[dict]:
    start, stop = span
    units, set_id, inv = [], None, None
    for i in range(start, stop):
        if m := re.match(r"STRINGS [1-4]-[2-5]-[3-6] - (G-B-e|D-G-B|A-D-G|E-A-D)$", lines[i]):
            set_id = SET_NAMES[m.group(1)]
        elif lines[i] in ("Root position", "First inversion", "Second inversion"):
            inv = {"Root position": "RP", "First inversion": "1st", "Second inversion": "2nd"}[lines[i]]
        elif lines[i].startswith("MAJ |"):
            if set_id is None or inv is None or not lines[i + 1].startswith("MIN |"):
                raise ValueError("D quality context drift")
            maj = re.fullmatch(r"MAJ \|([0-9-]+)\|\s+([b\d-]+)", lines[i])
            minor = re.fullmatch(r"MIN \|([0-9-]+)\|\s+([b\d-]+)", lines[i + 1])
            if not maj or not minor or not lines[i + 2].startswith("MOVE|") or lines[i + 3] != "Cnt |M--m--M--m--|M--m--M--m--|":
                raise ValueError("D rows/count drift")
            for name, m in (("C", maj), ("Cm", minor)):
                _shape(name, inv, set_id, m.group(1), m.group(2), lookup, allow_octave=True)
            a, b = _fret_tuple(maj.group(1)), _fret_tuple(minor.group(1))
            changed = [k for k in range(3) if a[k] != b[k]]
            if len(changed) != 1 or a[changed[0]] - b[changed[0]] != 1 or SETS[set_id][changed[0]] + " string" not in lines[i + 2]:
                raise ValueError("D quality-defining third move drift")
            page = 9 if set_id in ("123", "234") else 10
            for row in lines[i:i + 4]:
                _pdf_has(pages[page - 1], row, "D quality cell")
            attacks = [_attack("D", f"{set_id}:{inv}", k + 1, "blocked triad", i + 3, page, chord="C" if k % 2 == 0 else "Cm", symbol="M" if k % 2 == 0 else "m") for k in range(8)]
            units.append({"set": set_id, "inversion": inv, "major_frets": a, "minor_frets": b, "major_degrees": maj.group(2), "minor_degrees": minor.group(2), "moving_string": SETS[set_id][changed[0]], "source_rows": lines[i:i + 4], "txt_line": i + 1, "pdf_page": page, "attacks": attacks})
    if len(units) != 12 or sum(len(x["attacks"]) for x in units) != 96:
        raise ValueError("D quality count drift")
    return units


def _e(lines: list[str], span: tuple[int, int], pages: list[str], lookup: dict) -> list[dict]:
    start, stop = span
    units = []
    for i in range(start, stop):
        if not (m := re.match(r"^(G-B-e|D-G-B|A-D-G|E-A-D): ([A-G]m?(?:-[A-G]m?){3})$", lines[i])):
            continue
        set_id, label = SET_NAMES[m.group(1)], m.group(2)
        chords = _cells(lines[i + 1], "Chd", 4)
        invs = _cells(lines[i + 2], "Inv", 4)
        frets = _cells(lines[i + 3], "Fret", 4)
        degrees = _cells(lines[i + 4], "Deg", 4)
        if chords != label.split("-") or lines[i + 5] != "Cnt |1--2--3--4--| repeated four times":
            raise ValueError("E progression/count drift")
        page = 11 if len(units) < 4 else 12
        for row in lines[i + 1:i + 6]:
            _pdf_has(pages[page - 1], row, "E progression")
        for chord, inv, fret, deg in zip(chords, invs, frets, degrees):
            _shape(chord, inv, set_id, fret, deg, lookup)
        attacks = [_attack("E", label, k + 1, "blocked triad", i + 6, page, chord=chords[k % 4], symbol=str(k % 4 + 1)) for k in range(16)]
        units.append({"label": label, "set": set_id, "chords": chords, "inversions": invs, "frets": frets, "degrees": degrees, "source_rows": lines[i:i + 6], "txt_line": i + 1, "pdf_page": page, "attacks": attacks})
    if len(units) != 8 or sum(len(x["attacks"]) for x in units) != 128:
        raise ValueError("E progression count drift")
    return units


def _f(lines: list[str], span: tuple[int, int], pages: list[str], lookup: dict, e_units: list[dict]) -> list[dict]:
    start, stop = span
    headings = [(i, re.match(r"F([1-8])\. ", lines[i]).group(1)) for i in range(start, stop) if re.match(r"F[1-8]\. ", lines[i])]
    if [int(n) for _, n in headings] != list(range(1, 9)):
        raise ValueError("F pattern heading drift")
    expected = ["BLOCK x8", "D-G-B-B-G-D | D-G", "G-D-A-A-D-G | G-D", "E-D-A-D | E-D-A-D", "BLOCK | G-B-e | BLOCK | e-B-G", "CHORD mute CHORD mute | CHORD mute CHORD mute"]
    units = []
    for k, (i, num) in enumerate(headings):
        n = int(num)
        span_lines = lines[i:headings[k + 1][0] if k + 1 < 8 else stop]
        page = 13 if n <= 4 else 14
        if (lines[i] if n <= 6 else lines[i].split(":", 1)[0].replace(":", "")) not in pages[page - 1]:
            raise ValueError("F PDF heading drift")
        if n <= 6:
            chord_line = next((x for x in span_lines if x.startswith("Chord ")), None)
            m = re.fullmatch(r"Chord ([A-G]m?) (RP|1st|2nd) on (G-B-e|D-G-B|A-D-G|E-A-D)", chord_line or "")
            fret_line = next((x for x in span_lines if x.startswith("Frets ")), None)
            if not m or not fret_line:
                raise ValueError("F chord/fret drift")
            name, inv, set_name = m.groups()
            frets, deg = re.fullmatch(r"Frets ([0-9-]+); degrees ([b\d-]+)", fret_line).groups()
            set_id = SET_NAMES[set_name]
            _shape(name, inv, set_id, frets, deg, lookup)
            pattern = expected[n - 1]
            if pattern not in span_lines or "8 attacks." not in span_lines:
                raise ValueError("F core pattern/count drift")
            _pdf_has(pages[page - 1], pattern, "F pattern")
            if n == 1:
                marks = ["BLOCK"] * 8
            elif n == 6:
                marks = ["CHORD", "mute", "CHORD", "mute"] * 2
            else:
                marks = [x for x in re.split(r"[\s|+-]+", pattern) if x]
            if len(marks) != 8:
                raise ValueError("F eight-attack pattern drift")
        else:
            m = re.fullmatch(r"F[78]\. .+: ([A-G]m?(?:-[A-G]m?){3}) on (A-D-G|E-A-D)\. .+", lines[i])
            if not m:
                raise ValueError("F7/F8 source heading drift")
            label, set_name = m.groups()
            set_id = SET_NAMES[set_name]
            match = next((u for u in e_units if u["label"] == label and u["set"] == set_id), None)
            if match is None:
                raise ValueError("F7/F8 progression reference drift")
            for row in match["source_rows"][1:5]:
                _pdf_has(pages[13], row, "F7/F8 PDF-only explicit grid")
            name, inv, frets, deg = label, None, None, None
            pattern = "block + high-string repeat per chord" if n == 7 else "low string + block per chord"
            _pdf_has(pages[13], pattern, "F7/F8 voice pattern")
            marks = (["BLOCK", SETS[set_id][-1]] if n == 7 else [SETS[set_id][0], "BLOCK"]) * 4
        attacks = []
        for j, mark in enumerate(marks):
            chord = match["chords"][j // 2] if n >= 7 else name
            kind = "muted stroke" if mark == "mute" else "blocked triad" if mark in ("BLOCK", "CHORD") else "individual voice pick"
            attacks.append(_attack("F", lines[i], j + 1, kind, i + 1, page, string=mark if mark in SETS[set_id] else None, chord=chord, symbol=mark))
        units.append({"label": lines[i], "set": set_id, "pattern": pattern, "source_lines": span_lines, "txt_line": i + 1, "pdf_page": page, "attacks": attacks, "pdf_only_detail": n >= 7})
    if len(units) != 8 or sum(len(x["attacks"]) for x in units) != 64:
        raise ValueError("F pattern count drift")
    return units


def _g(lines: list[str], span: tuple[int, int], pages: list[str], lookup: dict) -> list[dict]:
    start, stop = span
    units = []
    for i in range(start, stop):
        m = re.fullmatch(r"([A-G]m?) (RP|1st|2nd) on (G-B-e|D-G-B|A-D-G|E-A-D)", lines[i])
        if not m:
            continue
        name, inv, set_name = m.groups()
        set_id = SET_NAMES[set_name]
        fret, deg = re.fullmatch(r"Frets ([0-9-]+); degrees ([b\d-]+)", lines[i + 1]).groups()
        notes = _shape(name, inv, set_id, fret, deg, lookup)
        if not lines[i + 2].startswith("Pattern ") or lines[i + 3] != "8 attacks.":
            raise ValueError("G fragment row/count drift")
        marks = [x for x in re.split(r"[\s|+-]+", lines[i + 2].removeprefix("Pattern ")) if x]
        if len(marks) != 8 or any(x not in SETS[set_id] for x in marks):
            raise ValueError("G eight-string route drift")
        for row in (lines[i], lines[i + 1], lines[i + 2]):
            _pdf_has(pages[14], row.replace(" on ", " - ").replace("Frets ", "Fret ").replace("; degrees ", "   Deg ").replace("Pattern ", "Play "), "G fragment")
        attacks = []
        for j, string in enumerate(marks):
            note = next(x for x in notes if x["string"] == string)
            attacks.append(_attack("G", lines[i], j + 1, "individual melodic pick", i + 3, 15, string=string, fret=note["fret"], chord=name, degree=note["degree"], symbol=string))
        units.append({"label": lines[i], "set": set_id, "frets": fret, "degrees": deg, "pattern": marks, "source_rows": lines[i:i + 4], "txt_line": i + 1, "pdf_page": 15, "attacks": attacks})
    if len(units) != 8 or sum(len(x["attacks"]) for x in units) != 64:
        raise ValueError("G fragment count drift")
    return units


def _h(lines: list[str], spans: tuple[tuple[int, int], tuple[int, int]], pages: list[str], lookup: dict) -> list[dict]:
    capstones = []
    for quality, (start, stop), page_start in (("major", spans[0], 16), ("minor", spans[1], 18)):
        bars = []
        for i in range(start, stop):
            m = re.fullmatch(r"Bar\s+(\d+): ([A-G]m?)\s+set (G-B-e|D-G-B|A-D-G|E-A-D) (RP|1st|2nd)\s+frets ([0-9-]+)\s+degrees ([b\d-]+) \| BLOCK \+ low-middle-high", lines[i])
            if not m:
                continue
            number, chord, set_name, inv, fret, deg = m.groups()
            if int(number) != len(bars) + 1:
                raise ValueError("H bar order drift")
            set_id = SET_NAMES[set_name]
            notes = _shape(chord, inv, set_id, fret, deg, lookup)
            page = page_start + (int(number) - 1) // 8
            pdf_lines = pages[page - 1].splitlines()
            marker = f"Bar {number}: {chord}"
            if marker not in pdf_lines:
                raise ValueError(f"H PDF bar heading mismatch: {marker}")
            p = pdf_lines.index(marker)
            detail = pdf_lines[p + 1:p + 7]
            if len(detail) != 6 or detail[0].split() != [set_name, inv] or detail[1] != f"Fret|{fret}|" or detail[2] != f"Deg |{deg}|" or detail[4] != "PAT |BLOCK + low-mid-high|" or detail[5] != "4 attacks":
                raise ValueError(f"H PDF bar detail mismatch: {marker}")
            note_match = re.fullmatch(r"Note\|([^|]+)\|", detail[3])
            spell = note_match.group(1).split("-") if note_match else []
            if len(spell) != 3 or any(n not in PC for n in spell) or [PC[n] for n in spell] != [n["pitch_class"] for n in notes]:
                raise ValueError(f"H PDF note-spelling mismatch: {marker}")
            attacks = [_attack("H", f"{quality}:bar{number}", j + 1, "blocked triad" if j == 0 else "individual arpeggio pick", i + 1, page, string=notes[j - 1]["string"] if j else None, fret=notes[j - 1]["fret"] if j else None, chord=chord, degree=notes[j - 1]["degree"] if j else None, symbol="BLOCK" if j == 0 else notes[j - 1]["string"]) for j in range(4)]
            bars.append({"bar": int(number), "chord": chord, "set": set_id, "inversion": inv, "frets": fret, "degrees": deg, "notes": notes, "pdf_spelling": spell, "source_row": lines[i], "txt_line": i + 1, "pdf_page": page, "attacks": attacks})
        if len(bars) != 16 or "64 attacks total." not in lines[start:stop]:
            raise ValueError("H sixteen-bar/64-attack drift")
        capstones.append({"quality": quality, "bars": bars, "printed_attack_count": 64})
    return capstones


def build_candidate(root: Path) -> dict:
    root = root.resolve()
    if root != Path(__file__).resolve().parents[1]:
        raise ValueError("supplied root is not this Git checkout")
    txt_raw = _pin(root / TXT_REL, TXT_SIZE, TXT_SHA)
    _pin(root / PDF_REL, PDF_SIZE, PDF_SHA)
    source_row = _source_map(root)
    pdf = PdfReader(root / PDF_REL)
    if len(pdf.pages) != 20:
        raise ValueError("PDF 20-page identity drift")
    pages = [x.extract_text() or "" for x in pdf.pages]
    for i, p in enumerate(pages, 1):
        if f"Page {i} of 20" not in p:
            raise ValueError(f"PDF page identity drift: {i}")
    txt = txt_raw.decode("utf-8")
    lines = txt.splitlines()
    bounds = _bounds(lines)
    formulas = _a_formulas(lines, bounds["A"], pages)
    b_units, lookup = _b(lines, bounds["B"], pages, formulas)
    modules = {"A": {"formula_count": 24, "silent_formation_count": 168, "formulas": list(formulas.values()), "formations": [{"set": u["set"], "chord": u["chord"], "quality": u["quality"], "inversion": u["inversion"], "frets": u["frets"], "txt_line": u["txt_line"], "pdf_page": u["pdf_page"], "kind": "silent formation", "performed": None} for u in b_units], "units": [], "printed_attack_count": 0}, "B": {"units": b_units}}
    modules["C"] = {"units": _c(lines, bounds["C"], pages, lookup)}
    modules["D"] = {"units": _d(lines, bounds["D"], pages, lookup)}
    modules["E"] = {"units": _e(lines, bounds["E"], pages, lookup)}
    modules["F"] = {"units": _f(lines, bounds["F"], pages, lookup, modules["E"]["units"])}
    modules["G"] = {"units": _g(lines, bounds["G"], pages, lookup)}
    capstones = _h(lines, (bounds["H"], bounds["H_minor"]), pages, lookup)
    modules["H"] = {"capstones": capstones, "units": [b for c in capstones for b in c["bars"]]}
    for name, module in modules.items():
        count = sum(len(u["attacks"]) for u in module["units"])
        if count != COUNTS[name]:
            raise ValueError(f"module {name} attack count drift: {count}")
        module["printed_attack_count"] = count
        start, stop = bounds[name]
        if name == "H":
            stop = bounds["H_minor"][1]
        module["txt_start_line"], module["txt_end_line"] = start + 1, stop
        module["full_source_lines"] = lines[start:stop]
    if sum(m["printed_attack_count"] for m in modules.values()) != 1248 or "COMPLETE SOUNDED WORKOUT: 1248 attacks plus 168 silent formations." not in txt:
        raise ValueError("Level53 whole count drift")
    for phrase in ("MASTERY GATE BEFORE LEVEL 54", "Pass at least 30 of 42 random prompts", "Random commands:", "Ear passes:"):
        if phrase not in txt:
            raise ValueError(f"TXT guidance drift: {phrase}")
    for page, phrase in ((1, "Session protocol"), (3, "randomize quality and inversion"), (13, "apply the same pattern to one major and one minor chord"), (15, "Repeat with the opposite pick start"), (20, "Practice log and completion audit")):
        if phrase.lower() not in pages[page - 1].lower():
            raise ValueError(f"PDF-specific guidance drift p{page}: {phrase}")
    return {"schema": "fathom.detached-source-candidate.1", "section": "VI", "level": 53, "wbs_id": "2.3.1.2.1", "source": {"txt_path": TXT_REL, "txt_bytes": TXT_SIZE, "txt_sha256": TXT_SHA, "pdf_path": PDF_REL, "pdf_bytes": PDF_SIZE, "pdf_sha256": PDF_SHA, "pdf_pages": 20, "source_map_path": MAP_REL, "source_map_bytes": MAP_SIZE, "source_map_sha256": MAP_SHA, "source_map_row": source_row}, "modules": modules, "module_count": 8, "silent_formation_count": 168, "printed_attack_count": 1248, "printed_guidance": {"kind": "printed_instruction", "txt_full_text": txt, "pdf_extracted_pages": [{"page": i + 1, "extracted_text": p} for i, p in enumerate(pages)]}, "source_exceptions": [{"code": "F7_F8_PDF_EXPLICIT_GRID", "status": "Pending Curriculum review", "source": "TXT Module F7/F8 versus PDF p14", "decision": "Preserve the PDF four-chord fret/inversion/degree grids as source-specific detail for the eight-attack voice-emphasis cells."}, {"code": "PDF_ADDITIONAL_PRACTICE_PASSES", "status": "Pending Curriculum review", "source": "PDF pp3-6,13-15", "decision": "Preserve PDF randomization, pattern-transfer and opposite-pick-start directions as printed alternatives without adding them to the 1248-attack core."}, {"code": "PDF_SESSION_AND_COMPLETION_AUDIT", "status": "Pending Curriculum review", "source": "PDF pp1,20", "decision": "Preserve session protocol and explicit 168 shape-forms/completion-log checklist as PDF-specific instructions; do not treat blank boxes or log fields as performed evidence or additional attacks."}, {"code": "D_C_MAJOR_SECOND_INVERSION_OCTAVE", "status": "Pending Curriculum review", "source": "TXT/PDF Module D G-B-e second inversion versus Module B family map", "decision": "D prints 12-13-12 for one-fret C/Cm switch while B prints 0-1-0 for the same C-major inversion pitch classes; retain the D register and both source voicings."}], "music_row_exceptions": [], "canonical_ids": None, "review": "Pending", "runtime_eligible": False, "imported": False, "admitted": False, "performed_bpm": None, "performed_quality": None, "performed_mastery": None, "pending": ["Curriculum review of source-specific guidance and D octave/register variant", "independent musical review", "canonical IDs and runtime admission", "performed mastery gate"]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    candidate = build_candidate(args.root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(candidate, sort_keys=True, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"LEVEL53 CANDIDATE PASS modules=8 silent=168 attacks=1248 output={args.output}")


if __name__ == "__main__":
    main()
