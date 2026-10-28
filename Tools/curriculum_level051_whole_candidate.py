#!/usr/bin/env python3
"""Build a pinned, detached whole-Level-51 movable-barre curriculum candidate."""

from __future__ import annotations

import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path
import re

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
STEM = "Guitar_Exercises_Section_VI_Level_51_Movable_Barre_Chord_Families_E_Shape_A_Shape_Root_Finding_Partial_Barres_and_Pressure_Management"
TXT_REL = Path("Notes/music/guitar project/TXT version") / (STEM + ".txt")
PDF_REL = Path("Notes/music/guitar project/PDF version") / (STEM + ".pdf")
TXT_BYTES, TXT_SHA = 21436, "227c3a52acbae2c2a8a58a5dffa603f632db2c3e62d9be5285cab333c81903da"
PDF_BYTES, PDF_SHA = 56914, "7a91c79021415138929f38349db58ae61b670c215f186ab28c36241ae61e5749"
BUILD_REL = Path("Build/parallel-09/2.3.1.2.1-level051-whole-r01")
STRINGS = ("E", "A", "D", "G", "B", "e")
OPEN = (40, 45, 50, 55, 59, 64)
PC = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4,
      "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9,
      "Bb": 10, "B": 11}
NATURAL_E = ["F", "G", "A", "B", "C", "D", "E"]
NATURAL_A = ["B", "C", "D", "E", "F", "G", "A"]
ROOT_FRETS_E = [1, 3, 5, 7, 8, 10, 12]
ROOT_FRETS_A = [2, 3, 5, 7, 8, 10, 12]
ATTACKS = {"A": 0, "B": 40, "C": 168, "D": 140, "E": 112, "F": 96,
           "G": 56, "H": 64, "I": 128, "J": 64, "K": 128}
MODULE_LINE = {"A": 17, "B": 28, "C": 41, "D": 90, "E": 153, "F": 216,
               "G": 271, "H": 300, "I": 333, "J": 396, "K": 433}
PDF_PAGES = {"A": [2], "B": [3, 4], "C": [5, 6], "D": [7, 8],
             "E": [9, 10], "F": [11, 12], "G": [13, 14], "H": [15],
             "I": [16, 17], "J": [18], "K": [19]}


class CandidateError(ValueError):
    pass


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _pin(data: bytes, size: int, digest: str, label: str) -> None:
    if len(data) != size or sha(data) != digest:
        raise CandidateError(f"PINNED_INPUT_DRIFT {label}: {len(data)} {sha(data)}")


def _midi_note(note: str, string: str, fret: int, context: str) -> None:
    if note not in PC or string not in STRINGS or fret < 0 or (OPEN[STRINGS.index(string)] + fret) % 12 != PC[note]:
        raise CandidateError(f"PITCH_MISMATCH {context}: {note} {string}{fret}")


def _tokens(line: str, label: str, n: int, width: int = 7, groups: int = 1) -> list[str]:
    parts = line.split("|")
    if len(parts) != groups + 2 or parts[0] != label or parts[-1] != "":
        raise CandidateError(f"GRID_SHAPE {label}: {line}")
    values = []
    for part in parts[1:-1]:
        if len(part) != n * width // groups:
            raise CandidateError(f"GRID_WIDTH {label}: {line}")
        for j in range(0, len(part), width):
            cell = part[j:j+width]
            value = cell.rstrip("-")
            if not value or value + "-"*(width-len(value)) != cell:
                raise CandidateError(f"GRID_SLOT {label}: {cell}")
            values.append(value)
    if len(values) != n:
        raise CandidateError(f"GRID_COUNT {label}")
    return values


def _fret_list(raw: str, context: str) -> list[int | None]:
    parts = raw.split()
    if len(parts) != 6 or any(x != "x" and not x.isdigit() for x in parts):
        raise CandidateError(f"FRET_SHAPE {context}")
    return [None if x == "x" else int(x) for x in parts]


def _fingers(raw: str, context: str) -> list[int | None]:
    parts = raw.split()
    if len(parts) != 6 or any(x != "x" and x not in "1234" for x in parts):
        raise CandidateError(f"FINGER_SHAPE {context}")
    return [None if x == "x" else int(x) for x in parts]


def _quality(chord: str) -> tuple[str, str]:
    if chord.endswith("m"):
        return chord[:-1], "minor"
    return chord, "major"


def _expected_frets(shape: str, quality: str, root_fret: int) -> list[int | None]:
    r = root_fret
    if shape == "E":
        return [r, r+2, r+2, r+1 if quality == "major" else r, r, r]
    return [None, r, r+2, r+2, r+2 if quality == "major" else r+1, r]


def _voicing(chord: str, shape: str, frets: list[int | None], fingers: list[int | None],
             notes: list[str | None], spelling: list[str], context: str, partial: list[int | None] | None = None) -> dict:
    root, quality = _quality(chord)
    root_fret = frets[0] if shape == "E" else frets[1]
    if root_fret is None or root not in PC or quality not in ("major", "minor") or frets != _expected_frets(shape, quality, root_fret):
        raise CandidateError(f"SHAPE_FRETS {context}")
    _midi_note(root, shape, root_fret, context)
    third = (PC[root] + (4 if quality == "major" else 3)) % 12
    fifth = (PC[root] + 7) % 12
    if len(spelling) != 3 or [PC.get(x) for x in spelling] != [PC[root], third, fifth]:
        raise CandidateError(f"SPELLING_MISMATCH {context}")
    if len(notes) != 6:
        raise CandidateError(f"NOTES_SHAPE {context}")
    roles = ["R", "5", "R", "3" if quality == "major" else "b3", "5", "R"] if shape == "E" else \
            [None, "R", "5", "R", "3" if quality == "major" else "b3", "5"]
    pcs = {"R": PC[root], "3": third, "b3": third, "5": fifth}
    for string, fret, note, role, finger in zip(STRINGS, frets, notes, roles, fingers, strict=True):
        if fret is None:
            if note is not None or role is not None or finger is not None:
                raise CandidateError(f"MUTED_STRING {context}")
        else:
            if note not in PC or PC[note] != pcs[role] or finger is None:
                raise CandidateError(f"NOTE_ROLE {context} {string}")
            _midi_note(note, string, fret, context)
    if partial is not None:
        if shape != "A" or partial != frets[:5] + [None]:
            raise CandidateError(f"PARTIAL_SHAPE {context}")
    return {"chord": chord, "shape": shape, "quality": quality, "root": root,
            "root_string": shape, "root_fret": root_fret, "frets": frets, "fingers": fingers,
            "notes_by_string": notes, "roles_by_string": roles, "spelling": spelling,
            "partial_frets": partial, "scan_attack_count": 12 if shape == "E" else 10,
            "onset_q": None, "duration_q": None}


def _parse_txt(data: bytes) -> dict:
    lines = data.decode("utf-8").splitlines()
    def L(n: int) -> str:
        return lines[n-1]
    if len(lines) != 466 or L(1) != "GUITAR EXERCISES - SECTION VI, LEVEL 51" or \
            L(13) != "COMPLETE SOUNDED WORKLOAD: 996 attacks plus 56 silent chord landings.":
        raise CandidateError("TXT_BOUNDARY")
    for k, n in MODULE_LINE.items():
        if not L(n).startswith(f"MODULE {k} - "):
            raise CandidateError(f"MODULE_BOUNDARY {k}")
    formulas = {"E major": L(8), "E minor": L(9), "A major": L(10), "A minor": L(11)}
    if formulas != {"E major": "E-shape major: R 5 R 3 5 R", "E minor": "E-shape minor: R 5 R b3 5 R",
                    "A major": "A-shape major: x R 5 R 3 5", "A minor": "A-shape minor: x R 5 R b3 5"}:
        raise CandidateError("CORE_FORMULA")
    # Module A: two full chromatic maps and the silent full/partial calls.
    e_map = L(21).removeprefix("Note | ").split()
    a_map = L(24).removeprefix("Note | ").split()
    if L(20) != L(23) or len(e_map) != 12 or len(a_map) != 12:
        raise CandidateError("ROOT_MAP_SHAPE")
    for string, names in (("E", e_map), ("A", a_map)):
        for fret, name in enumerate(names, 1):
            if any(part not in PC or PC[part] != (OPEN[STRINGS.index(string)] + fret) % 12 for part in name.split("/")):
                raise CandidateError(f"ROOT_MAP_PITCH {string}{fret}")
    for names, frets, observed in ((NATURAL_E, ROOT_FRETS_E, e_map), (NATURAL_A, ROOT_FRETS_A, a_map)):
        if [observed[f-1] for f in frets] != names:
            raise CandidateError("ROOT_MAP_NATURAL_CALLS")
    a = {"chromatic_roots": {"E": e_map, "A": a_map}, "natural_calls": [],
         "silent_landings": 56, "instruction": L(25), "txt_line": 17, "pdf_page": 2}
    for shape, names, frets in (("E", NATURAL_E, ROOT_FRETS_E), ("A", NATURAL_A, ROOT_FRETS_A)):
        for name, fret in zip(names, frets, strict=True):
            for quality in ("major", "minor"):
                a["natural_calls"].append({"root": name, "root_string": shape, "root_fret": fret,
                    "quality": quality, "silent_full_landing": 1, "silent_partial_landing": 1,
                    "sounded_attack_count": 0, "onset_q": None, "duration_q": None})
    # Module B: two passes of the same five-stage ladder.
    b = []
    for stage, n in enumerate(range(2, 7), 1):
        raw = L(31+stage)
        m = re.fullmatch(rf"{n}-string barre: (.+); frets (.+); {n} attacks\.", raw)
        if not m or len(m.group(2).split()) != n or any(x != "5" for x in m.group(2).split()):
            raise CandidateError(f"B_STAGE {n}")
        active = list(STRINGS[-n:])
        if m.group(1) != (" + ".join(["high e"] if n == 1 else ["B", "high e"]) if n == 2 else
                          {3:"G + B + high e",4:"D + G + B + high e",5:"A through high e",6:"low E through high e"}[n]):
            raise CandidateError(f"B_ACTIVE_STRINGS {n}")
        b.append({"stage": n, "active_strings": active, "frets": [5]*n,
                  "repeat_frets": [5,7], "picked_attacks_per_fret": n, "printed_text": raw,
                  "txt_line": 31+stage, "pdf_page": 4})
    if L(37) != "Repeat all five stages at frets 5 and 7. 40 picked-string attacks.":
        raise CandidateError("B_COUNT")
    # Modules C/D: every printed fret, finger, pitch and A partial.
    c, d = [], []
    for shape, starts, target in (("E", ((44,65),(66,87)), c), ("A", ((93,121),(122,150)), d)):
        for quality, (start, end) in zip(("major", "minor"), starts, strict=True):
            stride = 3 if shape == "E" else 4
            for n in range(start, end, stride):
                raw = L(n)
                m = re.fullmatch(r"([A-G]#?m?): frets (.+) \| fingers (.+) \| spelling (.+)", raw)
                if not m or L(n+1) != "Strings: E A D G B e" or not L(n+2).startswith("Notes:   "):
                    raise CandidateError(f"CHORD_RECORD_SHAPE L{n}")
                chord, fret_raw, finger_raw, spelling_raw = m.groups()
                if _quality(chord)[1] != quality:
                    raise CandidateError(f"CHORD_QUALITY L{n}")
                frets = _fret_list(fret_raw, f"L{n}")
                fingers = _fingers(finger_raw, f"L{n}")
                notes = [None if x == "x" else x for x in L(n+2)[9:].split()]
                partial = _fret_list(L(n+3).removeprefix("Partial: "), f"L{n}") if shape == "A" else None
                item = _voicing(chord, shape, frets, fingers, notes, spelling_raw.split(), f"L{n}", partial)
                item.update({"printed_rows": lines[n-1:n-1+stride], "txt_line": n,
                             "pdf_page": 5 if shape == "E" and quality == "major" else
                                         6 if shape == "E" else 7 if quality == "major" else 8})
                target.append(item)
    if len(c) != 14 or len(d) != 14 or L(87) != "Scan every chord low-to-high and high-to-low. 168 attacks total." or \
            L(150) != "Scan every chord A-to-e and e-to-A. 140 attacks total.":
        raise CandidateError("FAMILY_COUNT")
    # Modules E/F: strict eight-slot count/chord/strum grids.
    def eight_route(n: int, label: str) -> dict:
        count, chords, strum = (_tokens(L(n+i), k, 8) for i,k in enumerate(("Cnt","Chd","Str"), 1))
        if count != list(map(str, range(1,9))) or strum != ["D"]*8:
            raise CandidateError(f"EIGHT_GRID {label} L{n}")
        return {"chords": chords, "count_row": L(n+1), "chord_row": L(n+2), "strum_row": L(n+3),
                "attack_count": 8, "onset_q": None, "duration_q": None, "txt_line": n}
    e = []
    for shape, indices in (("E", range(156,181,4)), ("A", range(185,210,4))):
        for n in indices:
            m = re.fullmatch(r"([A-G]) <-> ([A-G]m) at (?:A-string )?fret (\d+)", L(n))
            if not m or m.group(2) != m.group(1)+"m":
                raise CandidateError(f"E_PAIR_HEADER L{n}")
            major, minor, fret = m.group(1), m.group(2), int(m.group(3))
            if fret != (ROOT_FRETS_E[NATURAL_E.index(major)] if shape == "E" else ROOT_FRETS_A[NATURAL_A.index(major)]):
                raise CandidateError(f"E_ROOT_FRET L{n}")
            route = eight_route(n, "E")
            if route["chords"] != [major,minor]*4:
                raise CandidateError(f"E_ALTERNATION L{n}")
            route.update({"shape": shape, "root_fret": fret, "pair": [major,minor],
                          "printed_heading": L(n), "pdf_page": 9 if shape == "E" else 10})
            e.append(route)
    if len(e) != 14 or L(213) != "112 attacks total.":
        raise CandidateError("E_COUNT")
    f = []
    for quality, indices in (("major", range(219,240,4)), ("minor", range(244,265,4))):
        for n in indices:
            m = re.fullmatch(r"([A-G]m?) E-shape <-> ([A-G]m?) A-shape at fret (\d+)", L(n))
            if not m or _quality(m.group(1))[1] != quality or _quality(m.group(2))[1] != quality:
                raise CandidateError(f"F_PAIR_HEADER L{n}")
            left, right, fret = m.group(1), m.group(2), int(m.group(3))
            if fret not in ROOT_FRETS_E or _expected_frets("E", quality, fret)[0] != fret or \
                    PC[_quality(right)[0]] != (PC[_quality(left)[0]] + 5) % 12:
                raise CandidateError(f"F_PAIR_RELATION L{n}")
            route = eight_route(n, "F")
            if route["chords"] != [left,right]*4:
                raise CandidateError(f"F_ALTERNATION L{n}")
            route.update({"quality": quality, "shared_fret": fret, "E_chord": left, "A_chord": right,
                          "printed_heading": L(n), "pdf_page": 11 if quality == "major" else 12})
            f.append(route)
    if len(f) != 12 or L(268) != "96 attacks total.":
        raise CandidateError("F_COUNT")
    # Module G: four full natural-root ascent/descent ladders.
    g = []
    for start, shape, quality in ((273,"E","major"),(279,"E","minor"),(285,"A","major"),(291,"A","minor")):
        names = NATURAL_E if shape == "E" else NATURAL_A
        frets = ROOT_FRETS_E if shape == "E" else ROOT_FRETS_A
        rows = lines[start:start+5]
        direction = _tokens(rows[0], "Dir", 14, groups=2)
        chords = _tokens(rows[1], "Chd", 14)
        roots = [int(x) for x in _tokens(rows[2], "Fret", 14)]
        shapes = _tokens(rows[3], "Shp", 14)
        attacks = _tokens(rows[4], "Atk", 14)
        expected_names = [x+("m" if quality=="minor" else "") for x in names]
        if direction != ["UP"]*7+["DOWN"]*7 or chords != expected_names+list(reversed(expected_names)) or \
                roots != frets+list(reversed(frets)) or shapes != [shape+("-M" if quality=="major" else "-m")]*14 or attacks != ["D"]*14:
            raise CandidateError(f"G_LADDER L{start}")
        g.append({"shape": shape, "quality": quality, "chords": chords, "frets": roots,
                  "directions": direction, "printed_rows": rows, "attack_count": 14,
                  "txt_line": start, "pdf_page": 13 if shape=="E" else 14,
                  "onset_q": None, "duration_q": None})
    if L(297) != "56 attacks total. One attack, release, look, shift, land.":
        raise CandidateError("G_COUNT")
    # Progression modules H/I/J: four bars, chord and shape agreement, four source-counted attacks per bar.
    def shape_chord(chord: str, token: str, context: str) -> dict:
        m = re.fullmatch(r"([EA])@?(\d+)", token)
        if not m:
            raise CandidateError(f"PROGRESSION_SHAPE {context}: {token}")
        shape, fret = m.group(1), int(m.group(2))
        root, quality = _quality(chord)
        if root not in PC or fret < 0:
            raise CandidateError(f"PROGRESSION_CHORD {context}")
        _midi_note(root, shape, fret, context)
        return {"chord": chord, "shape": shape, "root_fret": fret, "quality": quality,
                "sounded_attacks": 4, "onset_q": None, "duration_q": None}
    def progression(n: int, module: str, pdf_page: int, offset: int = 0) -> dict:
        chords = [x.strip() for x in L(n+1+offset).removeprefix("Chords: ").split(" | ")]
        shapes = [x.strip() for x in L(n+2+offset).removeprefix("Shapes: ").split(" | ")]
        if len(chords) != 4 or len(shapes) != 4 or L(n+1+offset).startswith("Chords: ") is False or L(n+2+offset).startswith("Shapes: ") is False:
            raise CandidateError(f"PROGRESSION_ROWS {module} L{n}")
        count, grid_chords, grid_shapes, grid_strum = \
            (_tokens(L(n+3+offset+i), k, 4) for i,k in enumerate(("Cnt","Chd","Shp","Str")))
        if count != ["1","2","3","4"] or grid_chords != chords or grid_strum != ["D"]*4 or \
                grid_shapes != [x.replace("@", "") for x in shapes]:
            raise CandidateError(f"PROGRESSION_GRID {module} L{n}")
        bars = [shape_chord(chord, shape, f"{module}-L{n}") for chord,shape in zip(chords,shapes,strict=True)]
        return {"title": L(n), "bars": bars, "printed_rows": lines[n-1:n+6+offset],
                "sounded_attack_count": 16, "txt_line": n, "pdf_page": pdf_page}
    h = [progression(n,"H",15) for n in (302,309,316,323)]
    if len(h) != 4 or L(330) != "64 attacks total.":
        raise CandidateError("H_COUNT")
    i = [progression(n,"I",16 if n < 364 else 17) for n in (336,343,350,357,365,372,379,386)]
    if len(i) != 8 or L(393) != "128 attacks total.":
        raise CandidateError("I_COUNT")
    for route in i[4:]:
        if [bar["quality"] for bar in route["bars"]] != ["minor","minor","major","minor"]:
            raise CandidateError("I_MAJOR_V")
    j = []
    for n in (398,406,414,422):
        route = progression(n,"J",18,offset=1)
        if not L(n+1) in ("four quarter-note attacks per bar", "release pressure after every attack", "pick four active strings once per bar"):
            raise CandidateError(f"J_PATTERN L{n}")
        route["pattern_instruction"] = L(n+1)
        # J adds a pattern line before the shared progression rows.
        chords = [x.strip() for x in L(n+2).removeprefix("Chords: ").split(" | ")]
        if chords != [b["chord"] for b in route["bars"]]:
            raise CandidateError(f"J_CHORDS L{n}")
        j.append(route)
    if len(j) != 4 or L(430) != "64 attacks total.":
        raise CandidateError("J_COUNT")
    # Module K: two exact 16-bar progression maps.
    k = []
    for quality, start in (("major",436),("minor",445)):
        bars = []
        for n in range(start,start+8,2):
            m = re.fullmatch(r"Bars (\d+)-(\d+): (.+)", L(n))
            if not m or int(m.group(2))-int(m.group(1)) != 3 or int(m.group(1)) != len(bars)+1:
                raise CandidateError(f"K_BAR_RANGE L{n}")
            chords = [x.strip() for x in m.group(3).split(" | ")]
            shapes = [x.strip() for x in L(n+1).removeprefix("Shapes: ").split(" | ")]
            if len(chords) != 4 or len(shapes) != 4:
                raise CandidateError(f"K_ROWS L{n}")
            bars += [shape_chord(chord, shape, f"K-L{n}") for chord,shape in zip(chords,shapes,strict=True)]
        if len(bars) != 16 or (quality=="major" and any(b["quality"]!="major" for b in bars)) or \
                (quality=="minor" and any([b["quality"] for b in bars[x:x+4]] != ["minor","minor","major","minor"] for x in (0,4,8,12))):
            raise CandidateError(f"K_QUALITY {quality}")
        k.append({"quality_route": quality, "bars": bars, "sounded_attack_count": 64,
                  "txt_line": start, "pdf_page": 19})
    if L(453) != "Four quarter-note attacks per bar. 128 attacks total. Rest at least one minute between passes.":
        raise CandidateError("K_COUNT_REST")
    modules = dict(zip("ABCDEFGHIJK", (a,b,c,d,e,f,g,h,i,j,k), strict=True))
    actual = {"A":0,"B":sum(x["picked_attacks_per_fret"]*2 for x in b),
              "C":sum(x["scan_attack_count"] for x in c),"D":sum(x["scan_attack_count"] for x in d),
              "E":sum(x["attack_count"] for x in e),"F":sum(x["attack_count"] for x in f),
              "G":sum(x["attack_count"] for x in g),"H":sum(x["sounded_attack_count"] for x in h),
              "I":sum(x["sounded_attack_count"] for x in i),"J":sum(x["sounded_attack_count"] for x in j),
              "K":sum(x["sounded_attack_count"] for x in k)}
    if actual != ATTACKS or sum(actual.values()) != 996 or sum(x["silent_full_landing"]+x["silent_partial_landing"] for x in a["natural_calls"]) != 56:
        raise CandidateError(f"WORKLOAD_MISMATCH {actual}")
    return {"modules": modules, "instructions": {"purpose": L(5), "core_shapes": formulas,
        "A": L(25), "B": L(30)+" " + L(31)+" " + L(37)+" " + L(38),
        "C": L(87), "D": L(150), "E": [L(155),L(184)], "G": L(297),
        "K": L(453), "error_repair": lines[457:464], "mastery": L(465), "next_level": L(466)},
        "lines": lines}


def _pdf(data: bytes, parsed: dict) -> dict:
    pages = [p.extract_text() or "" for p in PdfReader(BytesIO(data)).pages]
    if len(pages) != 20 or any(f"Page {n} of 20" not in text for n,text in enumerate(pages,1)):
        raise CandidateError("PDF_BOUNDARY")
    modules = parsed["modules"]
    checked = {k:0 for k in "ABCDEFGHIJK"}
    a = modules["A"]
    for string in ("E","A"):
        sequence = "\n".join(a["chromatic_roots"][string])
        if sequence not in pages[1]:
            raise CandidateError(f"PDF_A_ROOT_MAP {string}")
    for shape,names,frets in (("E",NATURAL_E,ROOT_FRETS_E),("A",NATURAL_A,ROOT_FRETS_A)):
        call = "  ".join(x+"/"+x+"m" for x in names)
        rows = re.findall(r"Root \| ([^\n]+)\nFret \| ([^\n]+)\nCall \| ([^\n]+)", pages[1])
        if not any(root.split()==names and list(map(int,fret.split()))==frets and printed_call==call
                   for root,fret,printed_call in rows):
            raise CandidateError(f"PDF_A_NATURAL_CALLS {shape}")
    checked["A"] = 28
    for x in modules["B"]:
        page = pages[3]
        expected = f'{x["stage"]}-string barre\n' + ("B + high e" if x["stage"]==2 else
            {3:"G + B + high e",4:"D + G + B + high e",5:"A through high e",6:"low E through high e"}[x["stage"]]) + \
            "\n" + " ".join(["5"]*x["stage"]) + f'\n{x["stage"]} attacks'
        if expected not in page:
            raise CandidateError(f"PDF_B_STAGE {x['stage']}")
        checked["B"] += 1
    diagram_examples = []
    for chord, shape, active, label in (("A","E",("D","G","B","e"),"A major - E upper four"),
                                        ("Am","E",("D","G","B","e"),"A minor - E upper four"),
                                        ("D","A",("A","D","G","B"),"D major - A inner four"),
                                        ("Dm","A",("A","D","G","B"),"D minor - A inner four")):
        item = next(v for v in modules["C" if shape=="E" else "D"] if v["chord"]==chord)
        if label not in pages[3]:
            raise CandidateError(f"PDF_B_DIAGRAM {label}")
        diagram_examples.append({"pdf_page":4,"label":label,"chord":chord,"shape":shape,
            "active_strings":list(active),
            "frets":{s:item["frets"][STRINGS.index(s)] for s in active},
            "fingers":{s:item["fingers"][STRINGS.index(s)] for s in active},
            "visual_reviewed":True})
    for key in ("C","D"):
        for x in modules[key]:
            page = pages[x["pdf_page"]-1]
            frets = " ".join("x" if v is None else str(v) for v in x["frets"])
            partial = "\n" + " ".join("x" if v is None else str(v) for v in x["partial_frets"]) if x["partial_frets"] else ""
            row = f'{x["chord"]}\n{x["root_fret"]}\n{frets}{partial}\n{" ".join(x["spelling"])}'
            if row not in page:
                raise CandidateError(f"PDF_{key}_CHORD {x['chord']}")
            checked[key] += 1
    for key in ("E","F","G"):
        for x in modules[key]:
            page = pages[x["pdf_page"]-1]
            rows = [x["count_row"],x["chord_row"],x["strum_row"]] if key in ("E","F") else x["printed_rows"]
            if any(row not in page for row in rows):
                raise CandidateError(f"PDF_{key}_GRID L{x['txt_line']}")
            checked[key] += 1
    for key in ("H","I","J"):
        for x in modules[key]:
            page = pages[x["pdf_page"]-1]
            grids = [row for row in x["printed_rows"] if row.startswith(("Cnt|","Chd|","Shp|","Str|"))]
            if len(grids)!=4 or any(row not in page for row in grids):
                raise CandidateError(f"PDF_{key}_GRID L{x['txt_line']}")
            if x["title"] not in page:
                raise CandidateError(f"PDF_{key}_TITLE L{x['txt_line']}")
            checked[key] += 1
    for x in modules["K"]:
        page = pages[18]
        for block in range(4):
            bars = x["bars"][block*4:block*4+4]
            first = block*4+1
            row = f'Bars {first:02d}-{first+3:02d}  | ' + " | ".join(b["chord"] for b in bars) + " |"
            shapes = "Shapes     | " + " | ".join(f'{b["shape"]}@{b["root_fret"]}' for b in bars) + " |"
            if row not in page or shapes not in page:
                raise CandidateError(f"PDF_K_BAR {x['quality_route']} {first}")
        checked["K"] += 1
    if checked != {"A":28,"B":5,"C":14,"D":14,"E":14,"F":12,"G":4,"H":4,"I":8,"J":4,"K":2}:
        raise CandidateError(f"PDF_ITEM_COUNT {checked}")
    return {"pages":20,"module_pages":PDF_PAGES,"checked_items":checked,"discrepancies":[],
            "partial_diagram_examples":diagram_examples,
            "pdf_only_guidance_pages": [2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20],
            "extracted_page_text":pages}


def build_candidate(txt_data: bytes | None = None, pdf_data: bytes | None = None) -> dict:
    for rel in (TXT_REL,PDF_REL):
        path = ROOT / rel
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(ROOT.resolve()):
            raise CandidateError(f"SOURCE_PATH_INVALID {rel}")
    txt = txt_data if txt_data is not None else (ROOT/TXT_REL).read_bytes()
    pdf = pdf_data if pdf_data is not None else (ROOT/PDF_REL).read_bytes()
    _pin(txt,TXT_BYTES,TXT_SHA,"L51-TXT")
    _pin(pdf,PDF_BYTES,PDF_SHA,"L51-PDF")
    parsed = _parse_txt(txt)
    pdf_check = _pdf(pdf,parsed)
    return {"schema":"fathom-level051-whole-detached-candidate-v1","wbs_id":"2.3.1.2.1","level":51,
        "source":{"txt_path":TXT_REL.as_posix(),"txt_bytes":TXT_BYTES,"txt_sha256":TXT_SHA,
                  "pdf_path":PDF_REL.as_posix(),"pdf_bytes":PDF_BYTES,"pdf_sha256":PDF_SHA,"pdf_pages":20},
        "modules":parsed["modules"],"module_sounded_attacks":ATTACKS,
        "complete_sounded_workload_attacks":996,"silent_chord_landings":56,
        "instructions":parsed["instructions"],"txt_document_text":txt.decode("utf-8"),
        "pdf_reconciliation":pdf_check,
        "canonical_item_id":None,"canonical_variant_id":None,"fixed_bpm":None,"note_per_click":None,
        "onset_q":None,"duration_q":None,"runtime_eligible":False,"runtime_admitted":False,
        "imported":False,"admitted":False,"curriculum_signoff":False,"performed_result":None}


def write_candidate(path: Path) -> dict:
    build = ROOT / BUILD_REL
    if (not build.resolve().is_relative_to(ROOT.resolve()) or build.is_symlink() or path.is_symlink()
            or path.parent.is_symlink() or path.parent.resolve()!=build.resolve() or path.suffix!=".json"):
        raise CandidateError("OUTPUT_OUTSIDE_LANE_BUILD")
    if path.exists():
        raise CandidateError("OUTPUT_EXISTS")
    candidate = build_candidate()
    build.mkdir(parents=True,exist_ok=True)
    encoded = (json.dumps(candidate,sort_keys=True,indent=2,ensure_ascii=False)+"\n").encode()
    with path.open("xb") as handle:
        handle.write(encoded)
    return {"path":str(path),"bytes":len(encoded),"sha256":sha(encoded),"modules":11,
            "sounded_attacks":996,"silent_landings":56}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output",type=Path)
    args = parser.parse_args()
    print(json.dumps(write_candidate(args.output),sort_keys=True))


if __name__ == "__main__":
    main()
