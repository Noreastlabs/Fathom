#!/usr/bin/env python3
"""Build a detached, pinned Level 54 CAGED source candidate."""

from __future__ import annotations

import argparse
import csv
import hashlib
from io import BytesIO
import json
from pathlib import Path
import re

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
STEM = "Guitar_Exercises_Section_VI_Level_54_CAGED_Practical_Chord_Triad_Root_Arpeggio_and_Nearby_Scale_Tone_Map"
TXT = Path(f"Notes/music/guitar project/TXT version/{STEM}.txt")
PDF = Path(f"Notes/music/guitar project/PDF version/{STEM}.pdf")
MAP = Path("Results/parallel-01/exercises/inventory/20260922T180500Z-2.3-curriculum-v1-source-inventory-evidence/curriculum-source-map.tsv")
BUILD = Path("Build/parallel-08/2.3.1.2.1-level054-whole-r01")
PINS = {"txt": (20494, "b980a8b75b207e2b6ebf46b6245752084f85797cf6cdc7cf4d42d0a53cbf29aa"),
        "pdf": (55120, "4fc5fe471f533ebd89707c998aa4d9151a84094f8af72ba420cc68f82d0db3a9"),
        "map": (68536, "f526ff4d9ce3bceaf9a7cc581a3ac2aee2c74917eba984dd57913adba574c123")}
FORMS = ("C", "A", "G", "E", "D")
OPEN = {"E": 4, "A": 9, "D": 2, "G": 7, "B": 11, "e": 4}
PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11, "Eb": 3}
C_DEG = {"1": "C", "2": "D", "3": "E", "4": "F", "5": "G", "6": "A", "7": "B", "b3": "Eb"}
COUNTS = {"A": 0, "B": 66, "C": 60, "D": 40, "E": 52, "F": 80, "G": 40, "H": 80, "I": 60, "J": 80}
PAGES = {"A": [2, 18], "B": [3, 4, 5, 6, 7], "C": [8], "D": [9], "E": [10, 11],
         "F": [12, 13], "G": [14], "H": [15, 16], "I": [17], "J": [19]}
HEAD = {"A": "MODULE A - ROOT MAP AND SILENT FORMATION", "B": "MODULE B - FIVE C-MAJOR FORM FAMILIES",
        "C": "MODULE C - TRIAD FRAGMENTS", "D": "MODULE D - MAJOR/MINOR QUALITY CONVERSION",
        "E": "MODULE E - CHORD-TONE ARPEGGIOS", "F": "MODULE F - NEARBY C-MAJOR SCALE TONES",
        "G": "MODULE G - SAME CHORD THROUGH THE CAGED CYCLE", "H": "MODULE H - C-F-G-C IN FIVE CAGED REGIONS",
        "I": "MODULE I - ZONE SYNTHESIS", "J": "MODULE J - TWENTY-BAR REGISTER CAPSTONE"}
FORMULA = {"C": "C form: A-string root r; x r r-1 r-3 r-2 r-3. Additional root on B string r-2.",
           "A": "A form: A-string root r; x r r+2 r+2 r+2 r. Additional root on G string r+2.",
           "G": "G form: low-E root r; r r-1 r-3 r-3 r-3 r. Additional roots on G string r-3 and high e r.",
           "E": "E form: low-E root r; r r+2 r+2 r+1 r r. Additional roots on D string r+2 and high e r.",
           "D": "D form: D-string root r; x x r r+2 r+3 r+2. Additional root on B string r+3."}
ROOT_TABLE = {"C": {"A": [3, 15], "E": [8], "D": [10]},
              "D": {"A": [5], "E": [10], "D": [0, 12]},
              "E": {"A": [7], "E": [0, 12], "D": [2, 14]},
              "F": {"A": [8], "E": [1, 13], "D": [3, 15]},
              "G": {"A": [10], "E": [3, 15], "D": [5, 17]},
              "A": {"A": [0, 12], "E": [5, 17], "D": [7]},
              "B": {"A": [2, 14], "E": [7], "D": [9]}}


class CandidateError(ValueError):
    """Pinned input or authored structure failed validation."""


def fail(code: str, detail: object = "") -> None:
    raise CandidateError(f"{code}: {detail}")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def pinned(root: Path, rel: Path, kind: str) -> bytes:
    path = root / rel
    if path.is_symlink() or not path.is_file() or path.resolve().parent != path.parent.resolve():
        fail("SOURCE_PATH_INVALID", rel)
    data = path.read_bytes()
    if (len(data), sha(data)) != PINS[kind]:
        fail("PINNED_INPUT_DRIFT", f"{kind} bytes={len(data)} sha256={sha(data)}")
    return data


def require(condition: bool, code: str, detail: object = "") -> None:
    if not condition:
        fail(code, detail)


def block(lines: list[str], key: str) -> list[str]:
    start = lines.index(HEAD[key])
    if key == "J":
        end = lines.index("PRACTICE PROGRESSION AND MASTERY")
    else:
        end = lines.index(HEAD[chr(ord(key) + 1)])
    return lines[start:end]


def pdf_has(page: str, value: str, label: str) -> None:
    require(value in page, "PDF_PARITY", f"{label}: {value}")


def placement(string: str, fret: int) -> dict:
    require(string in OPEN and 0 <= fret <= 24, "FRET_INVALID", (string, fret))
    pc = (OPEN[string] + fret) % 12
    names = [name for name, value in PC.items() if value == pc]
    require(len(names) == 1, "PITCH_CLASS_UNNAMED", (string, fret))
    return {"string": string, "fret": fret, "note": names[0]}


def triad(strings: str, frets: str, degrees: str, inversion: str, chord: str = "C") -> dict:
    ss, ff, dd = strings.split("-"), [int(x) for x in frets.split("-")], degrees.split("-")
    require(len(ss) == len(ff) == len(dd) == 3, "TRIAD_LENGTH", (strings, frets, degrees))
    notes = [placement(s, f) for s, f in zip(ss, ff, strict=True)]
    tones = {"C": {"1": "C", "3": "E", "5": "G"},
             "F": {"1": "F", "3": "A", "5": "C"},
             "G": {"1": "G", "3": "B", "5": "D"}}[chord]
    require(all(n["note"] == tones[d] for n, d in zip(notes, dd, strict=True)), "TRIAD_PITCH", (chord, strings, frets, degrees, notes))
    expected = {"1": "RP", "3": "1st", "5": "2nd"}[dd[0]]
    require(inversion == expected, "TRIAD_INVERSION", (chord, strings, degrees, inversion))
    return {"strings": ss, "frets": ff, "degrees": dd, "notes": [n["note"] for n in notes], "inversion": inversion}


def parse_grid(rows: list[str], label: str) -> dict:
    require(len(rows) in (4, 5), "GRID_ROWS", label)
    tokens = {row[:3]: re.findall(r"x|\d+|[A-Ga-e]|O", row.split("|", 1)[1]) for row in rows}
    ss = ["E", "A", "D", "G", "B", "e"]
    require(tokens["Str"] == ss, "GRID_STRINGS", label)
    ff = re.findall(r"x|\d+", rows[1].split("|", 1)[1])
    nn = re.findall(r"x|[A-G]", rows[2].split("|", 1)[1])
    dd = re.findall(r"x|\d+", rows[3].split("|", 1)[1])
    require(len(ff) == len(nn) == len(dd) == 6, "GRID_WIDTH", label)
    for s, f, n, d in zip(ss, ff, nn, dd, strict=True):
        if f == "x":
            require(n == d == "x", "GRID_MUTE", label)
        else:
            p = placement(s, int(f))
            require(n == p["note"] and n == C_DEG[d], "GRID_PITCH", (label, s, f, n, d))
    if len(rows) == 5:
        fingers = re.findall(r"x|\d+|O", rows[4].split("|", 1)[1])
        require(len(fingers) == 6, "FINGER_WIDTH", label)
        for f, finger in zip(ff, fingers, strict=True):
            require((f == "x" and finger == "x") or (f == "0" and finger == "O") or
                    (f not in ("x", "0") and finger in ("1", "2", "3", "4")), "FINGER_STATE", label)
    return {"strings": ss, "frets": [None if f == "x" else int(f) for f in ff],
            "notes": [None if n == "x" else n for n in nn],
            "degrees": [None if d == "x" else d for d in dd],
            "source_rows": rows}


def parse_a(lines: list[str], page: str) -> dict:
    source = block(lines, "A")
    pdf_has(page, "35 SILENT FORMATIONS", "A count")
    for root, table in ROOT_TABLE.items():
        require(any(re.search(rf"^\s*{root}\s+", line) and all(
            (" / ".join(map(str, value)) if len(value) > 1 else str(value[0])) in line
            for value in table.values()) for line in page.splitlines()), "ROOT_TABLE_PARITY", root)
    prompts = []
    for root in "CDEFGAB":
        for form in FORMS:
            root_string = "A" if form in ("C", "A") else "E" if form in ("G", "E") else "D"
            options = ROOT_TABLE[root][root_string]
            valid = [r for r in options if min({"C": [r, r - 1, r - 3, r - 2, r - 3],
                                                "A": [r, r + 2, r + 2, r + 2, r],
                                                "G": [r, r - 1, r - 3, r - 3, r - 3, r],
                                                "E": [r, r + 2, r + 2, r + 1, r, r],
                                                "D": [r, r + 2, r + 3, r + 2]}[form]) >= 0]
            require(valid, "ROOT_OCTAVE_UNAVAILABLE", (root, form))
            prompts.append({"root": root, "form": form, "root_string": root_string,
                            "source_root_fret_options": options, "formula_valid_root_fret_options": valid,
                            "sound": False})
    require("5 master forms + 5 practical partials + 35 root/form prompts = 45" in "\n".join(source), "A_COUNT")
    return {"silent_master_forms": list(FORMS), "silent_practical_partials": list(FORMS),
            "natural_root_form_prompts": prompts, "silent_prompt_count": 45,
            "verification_instruction": source[2], "pdf_pages": PAGES["A"]}


def parse_b(lines: list[str], pages: list[str]) -> list[dict]:
    source = block(lines, "B")
    output = []
    for index, form in enumerate(FORMS):
        heading = next((line for line in source if line.startswith(f"{form} FORM - {form} FORM - ")), None)
        require(heading is not None, "B_FORM_MISSING", form)
        p = source.index(heading)
        roots_line = source[p + 1]
        full_at = source.index("FULL FORM", p)
        fragment_at = source.index("PRACTICAL FRAGMENT", full_at)
        embedded_at = source.index("EMBEDDED TRIADS", fragment_at)
        full_rows, fragment_rows = source[full_at + 1:full_at + 6], source[fragment_at + 1:fragment_at + 5]
        full, fragment = parse_grid(full_rows, f"B {form} full"), parse_grid(fragment_rows, f"B {form} fragment")
        for row in full_rows + fragment_rows:
            pdf_has(pages[index], row, f"B {form} grid")
        contacts = [{"string": s, "fret": int(f)} for s, f in re.findall(r"([EADGBe])(\d+)", roots_line)]
        actual_roots = [{"string": s, "fret": f} for s, f, n in zip(full["strings"], full["frets"], full["notes"], strict=True) if n == "C"]
        require(contacts == actual_roots, "B_ROOT_CONTACTS", form)
        fragment_roots = [r for r in contacts if fragment["frets"][OPEN_ORDER.index(r["string"])] == r["fret"]]
        triads = []
        for row in source[embedded_at + 1:embedded_at + 4]:
            match = re.fullmatch(r"(.+?): strings ([EADGBe]-[EADGBe]-[EADGBe]) frets (\d+-\d+-\d+) degrees ([135]-[135]-[135]) inversion (RP|1st|2nd)\.", row)
            require(match is not None, "B_TRIAD_ROW", (form, row))
            _, strings, frets, degrees, inversion = match.groups()
            triads.append(triad(strings, frets, degrees, inversion))
            pdf_has(pages[index], strings, f"B {form} triad strings")
            pdf_has(pages[index], frets, f"B {form} triad frets")
        sounded_strings = sum(f is not None for f in full["frets"])
        pdf_has(pages[index], f"4 blocked attacks + {sounded_strings}-string low-to-high audit", f"B {form} workout")
        count = 8 + sounded_strings
        pdf_has(pages[index], f"{count} ATTACKS", f"B {form} count")
        output.append({"form": form, "zone": index + 1, "heading": heading, "source_roots": roots_line,
                       "full_form": full, "practical_fragment": fragment,
                       "full_form_root_contacts": contacts, "fragment_root_contacts": fragment_roots,
                       "embedded_triads": triads,
                       "workout": {"full_blocked_attacks": 4, "full_string_audit_attacks": sounded_strings,
                                   "fragment_blocked_attacks": 4, "attack_count": count},
                       "pdf_page": index + 3})
    require(sum(x["workout"]["attack_count"] for x in output) == COUNTS["B"], "B_TOTAL")
    return output


OPEN_ORDER = ["E", "A", "D", "G", "B", "e"]


def parse_c(lines: list[str], b: list[dict], pdf: str) -> list[dict]:
    source = block(lines, "C")
    result = []
    for index, form in enumerate(FORMS):
        at = source.index(f"{form} FORM REGION")
        rows = source[at + 1:at + 4]
        for j, row in enumerate(rows):
            match = re.fullmatch(r"(.+?): ([EADGBe]-[EADGBe]-[EADGBe]) (\d+-\d+-\d+) ([135]-[135]-[135]) (RP|1st|2nd); 4 attacks\.", row)
            require(match is not None, "C_ROW", row)
            _, strings, frets, degrees, inversion = match.groups()
            parsed = triad(strings, frets, degrees, inversion)
            require(parsed == b[index]["embedded_triads"][j], "C_B_TRIAD_PARITY", (form, j))
            pdf_has(pdf, f"{strings} {frets} {degrees}", f"C {form} triad")
            result.append({"form": form, "fragment": j + 1, "triad": parsed,
                           "attack_pattern": ["blocked", "low", "middle", "high"], "attack_count": 4})
    require(len(result) == 15, "C_TOTAL")
    return result


def parse_d(lines: list[str], pdf: str) -> list[dict]:
    source = block(lines, "D")
    output = []
    for form, row in zip(FORMS, [s for s in source if s.startswith(tuple(f"{f} form " for f in FORMS))], strict=True):
        match = re.fullmatch(r"([CAGED]) form (RP|1st|2nd): MAJOR ([\d-]+) ([135]-[135]-[135]); MINOR ([\d-]+) ([1b35-]+)\. Alternate M-m eight times\.", row)
        require(match is not None, "D_ROW", row)
        _, inversion, major_frets, major_degrees, minor_frets, minor_degrees = match.groups()
        strings = {"C": "A-D-G", "A": "G-B-e", "G": "A-D-G", "E": "D-G-B", "D": "G-B-e"}[form]
        maj = triad(strings, major_frets, major_degrees, inversion)
        ss, mm, dd = strings.split("-"), [int(x) for x in minor_frets.split("-")], minor_degrees.split("-")
        minor_notes = [placement(s, f)["note"] for s, f in zip(ss, mm, strict=True)]
        require(len(dd) == 3 and all(n == C_DEG[d] for n, d in zip(minor_notes, dd, strict=True)), "D_MINOR_PITCH", form)
        shifts = [i for i, (a, z) in enumerate(zip(maj["frets"], mm, strict=True)) if a != z]
        require(len(shifts) == 1 and maj["degrees"][shifts[0]] == "3" and dd[shifts[0]] == "b3" and mm[shifts[0]] == maj["frets"][shifts[0]] - 1, "D_ONE_VOICE", form)
        pdf_has(pdf, f"MAJ|{major_frets}", f"D {form} major")
        pdf_has(pdf, f"MIN|{minor_frets}", f"D {form} minor")
        output.append({"form": form, "strings": ss, "inversion": inversion, "major": maj,
                       "minor": {"frets": mm, "degrees": dd, "notes": minor_notes},
                       "moving_string": ss[shifts[0]], "attack_sequence": ["major", "minor"] * 4, "attack_count": 8})
    require(len(output) == 5, "D_TOTAL")
    return output


def tab_events(rows: list[str], count: int, label: str) -> list[dict]:
    events = []
    for row in rows:
        match = re.fullmatch(r"\s*([EADGBe])\|([^|]*)\|([^|]*)", row)
        require(match is not None, "TAB_ROW", (label, row))
        string, left, right = match.groups()
        for bar, body in enumerate((left, right), 1):
            for token in re.finditer(r"\d+", body):
                events.append({"bar": bar, "source_column": token.start(), **placement(string, int(token.group()))})
    events.sort(key=lambda x: (x["bar"], x["source_column"]))
    require(len(events) == count, "TAB_COUNT", (label, len(events), count))
    return events


def parse_melody(lines: list[str], pages: list[str], key: str, counts: list[int]) -> list[dict]:
    source = block(lines, key)
    output = []
    for index, (form, expected) in enumerate(zip(FORMS, counts, strict=True)):
        heading = f"{form} FORM - {expected} ATTACKS" if key == "E" else f"{form} FORM LOCAL SCALE ROUTE"
        at = source.index(heading)
        nte, deg = source[at + 1:at + 3]
        roles = source[at + 3] if key == "F" else None
        tab_start = at + (4 if key == "F" else 3)
        rows = source[tab_start:tab_start + 6]
        notes = re.findall(r"[A-G]", nte.split("|", 1)[1])
        degrees = re.findall(r"\d+", deg.split("|", 1)[1])
        require(len(notes) == len(degrees) == expected and all(n == C_DEG[d] for n, d in zip(notes, degrees, strict=True)), "MELODY_LABELS", (key, form))
        if roles:
            role_values = re.findall(r"[TS]", roles.split("|", 1)[1])
            require(len(role_values) == expected and all(r == ("T" if d in ("1", "3", "5") else "S") for r, d in zip(role_values, degrees, strict=True)), "SCALE_ROLES", form)
        else:
            role_values = None
        events = tab_events(rows, expected, f"{key} {form}")
        require(all(n == p["note"] for n, p in zip(notes, events, strict=True)), "MELODY_TAB_PITCH", (key, form))
        pdf_page = pages[0] if index < (3 if key == "E" else 3) else pages[1]
        for row in [nte, deg] + ([roles] if roles else []) + rows:
            pdf_has(pdf_page, row.strip(), f"{key} {form} row")
        output.append({"form": form, "notes": notes, "degrees": degrees, "roles": role_values,
                       "placements": events, "source_rows": [nte, deg] + ([roles] if roles else []) + rows,
                       "attack_count": expected, "pdf_page": 10 if key == "E" and index < 3 else
                       11 if key == "E" else 12 if index < 3 else 13})
    return output


def parse_g(lines: list[str], b: list[dict], pdf: str) -> list[dict]:
    source = block(lines, "G")
    expected = list(FORMS) + list(reversed(FORMS))
    result = []
    for index, form in enumerate(expected, 1):
        row = next((s for s in source if s.startswith(f"{index}. ")), None)
        require(row is not None, "G_ENTRY", index)
        match = re.fullmatch(r"\d+\. ([CAGED]) form: strings ([EADGBe-]+) frets ([\d-]+) notes ([A-G-]+); roots (.+)\.", row)
        require(match is not None and match.group(1) == form, "G_ROW", row)
        _, strings, frets, notes, roots = match.groups()
        ss, ff, nn = strings.split("-"), [int(x) for x in frets.split("-")], notes.split("-")
        require(len(ss) == len(ff) == len(nn) == 4 and all(placement(s, f)["note"] == n for s, f, n in zip(ss, ff, nn, strict=True)), "G_PITCH", index)
        ref = b[FORMS.index(form)]
        fragment = ref["practical_fragment"]
        actual = [(s, f) for s, f in zip(fragment["strings"], fragment["frets"], strict=True) if f is not None]
        require(actual == list(zip(ss, ff, strict=True)), "G_B_FRAGMENT", index)
        require(roots == ref["source_roots"].removeprefix("Roots: "), "G_ROOTS", index)
        pdf_has(pdf, f"Frt|{frets}|", f"G {index} frets")
        result.append({"position": index, "form": form, "strings": ss, "frets": ff, "notes": nn,
                       "full_form_root_contacts": ref["full_form_root_contacts"],
                       "fragment_root_contacts": ref["fragment_root_contacts"],
                       "quarter_note_blocked_attacks": 4, "attack_count": 4})
    return result


def parse_h(lines: list[str], pages: list[str]) -> list[dict]:
    source = block(lines, "H")
    result = []
    for index, form in enumerate(FORMS):
        heading = next((s for s in source if s.startswith(f"{form} FORM REGION - SET ")), None)
        require(heading is not None, "H_REGION", form)
        strings = heading.split("SET ", 1)[1]
        at = source.index(heading)
        rows = source[at + 1:at + 5]
        chords = []
        for expected_chord, row in zip(("C", "F", "G", "C"), rows, strict=True):
            match = re.fullmatch(r"([CFG]): frets ([\d-]+) inversion (RP|1st|2nd); BLOCK \+ low-middle-high\.", row)
            require(match is not None and match.group(1) == expected_chord, "H_ROW", (form, row))
            _, frets, inversion = match.groups()
            degrees = {"RP": "1-3-5", "1st": "3-5-1", "2nd": "5-1-3"}[inversion]
            chord_tri = triad(strings, frets, degrees, inversion, expected_chord)
            chords.append({"chord": expected_chord, "triad": chord_tri,
                           "attack_pattern": ["blocked", "low", "middle", "high"], "attack_count": 4})
        page = pages[0] if index < 3 else pages[1]
        pdf_has(page, f"{form} form region - {strings}", f"H {form} region")
        pdf_has(page, "Inversions: C:RP | F:2nd | G:1st | C:RP", f"H {form} inversions")
        for chord in chords:
            pdf_has(page, "-".join(map(str, chord["triad"]["frets"])), f"H {form} fret")
        result.append({"form": form, "strings": strings.split("-"), "chords": chords, "attack_count": 16})
    return result


def parse_i(lines: list[str], b: list[dict], c: list[dict], f: list[dict], pdf: str) -> list[dict]:
    source = block(lines, "I")
    result = []
    for index, form in enumerate(FORMS):
        row = next((s for s in source if s.startswith(f"{form}: BLOCK ")), None)
        require(row is not None, "I_ROW", form)
        match = re.fullmatch(r"[CAGED]: BLOCK ([\d-]+); TRIAD ([\d-]+); SCALE ([\d-]+)\.", row)
        require(match is not None, "I_SHAPE", row)
        blk, tri, scale = match.groups()
        expected_blk = "-".join(str(x) for x in b[index]["practical_fragment"]["frets"] if x is not None)
        require(blk == expected_blk, "I_BLOCK_B", form)
        matching_triads = [item["triad"] for item in c if item["form"] == form and "-".join(map(str, item["triad"]["frets"])) == tri]
        require(len(matching_triads) == 1, "I_TRIAD_C", form)
        require(scale == "-".join(f[index]["degrees"][:8]), "I_SCALE_F", form)
        pdf_has(pdf, f"BLK|{blk}|", f"I {form} block")
        pdf_has(pdf, f"TRI|{tri}|", f"I {form} triad")
        result.append({"form": form, "blocked_fragment_frets": [int(x) for x in blk.split("-")],
                       "primary_triad": matching_triads[0], "scale_degrees": [int(x) for x in scale.split("-")],
                       "attack_pattern": ["blocked"] + ["triad_low", "triad_middle", "triad_high"] + ["scale"] * 8,
                       "attack_count": 12})
    return result


def parse_j(lines: list[str], h: list[dict], pdf: str) -> list[dict]:
    source = block(lines, "J")
    output = []
    for index, form in enumerate(FORMS):
        start_bar = index * 4 + 1
        heading = f"Bars {start_bar}-{start_bar + 3}: {form} form region, set {'-'.join(h[index]['strings'])}."
        at = source.index(heading)
        rows = source[at + 1:at + 5]
        pdf_has(pdf, f"Bars {start_bar}-{start_bar + 3} - {form} form region", f"J {form} bars")
        pdf_has(pdf, "Chd|C---------F---------G---------C", f"J {form} progression")
        pdf_has(pdf, "Inv|RP--------2nd-------1st-------RP", f"J {form} inversions")
        for j, (row, ref) in enumerate(zip(rows, h[index]["chords"], strict=True)):
            match = re.fullmatch(r"  ([CFG]): ([\d-]+) (RP|1st|2nd); BLOCK \+ low-middle-high\.", row)
            require(match is not None, "J_ROW", row)
            chord, frets, inversion = match.groups()
            require(chord == ref["chord"] and frets == "-".join(map(str, ref["triad"]["frets"])) and inversion == ref["triad"]["inversion"], "J_H_PARITY", (form, j))
            pdf_has(pdf, frets, f"J {form} fret")
            output.append({"bar": start_bar + j, "form": form, "strings": h[index]["strings"],
                           "chord": chord, "triad": ref["triad"],
                           "attack_pattern": ["blocked", "low", "middle", "high"], "attack_count": 4})
    require(len(output) == 20, "J_TOTAL")
    return output


def build(root: Path = ROOT) -> dict:
    txt, pdf, source_map = (pinned(root, rel, kind) for rel, kind in ((TXT, "txt"), (PDF, "pdf"), (MAP, "map")))
    lines = txt.decode("utf-8").splitlines()
    require(len(lines) == 419, "TXT_LINES", len(lines))
    pdf_pages = [page.extract_text(extraction_mode="layout") or "" for page in PdfReader(BytesIO(pdf)).pages]
    require(len(pdf_pages) == 20, "PDF_PAGES", len(pdf_pages))
    for key, page_numbers in PAGES.items():
        require(all(pdf_pages[n - 1] for n in page_numbers), "PDF_MODULE_PAGE", key)
    map_rows = list(csv.DictReader(source_map.decode("utf-8").splitlines(), delimiter="\t"))
    matches = [row for row in map_rows if STEM in " ".join(row.values())]
    require(len(matches) == 1, "SOURCE_MAP_LEVEL54", len(matches))
    map_row = matches[0]
    require(map_row["level"] == "54" and map_row["wbs_owner"] == "2.3.1.2.1" and
            map_row["txt_path"] == str(TXT) and map_row["pdf_path"] == str(PDF) and
            map_row["pair_status"] == "exact_stem_pair" and map_row["review"] == "Pending" and
            map_row["conversion_status"] == "not_converted" and
            all(map_row[key] == "False" for key in ("stable_ids_assigned", "runtime_eligible", "imported", "admitted")),
            "SOURCE_MAP_STATUS", map_row)
    require("COMPLETE SOUNDED WORKOUT: 558 attacks plus 45 silent formation prompts." in lines, "WORKLOAD_HEADER")
    for form in FORMS:
        require(FORMULA[form] in lines, "ROOT_FORMULA", form)
    pdf_has(pdf_pages[0], "558 ATTACKS  |  45 SILENT PROMPTS", "overview count")
    a = parse_a(lines, pdf_pages[17])
    b = parse_b(lines, [pdf_pages[i] for i in range(2, 7)])
    c = parse_c(lines, b, pdf_pages[7])
    d = parse_d(lines, pdf_pages[8])
    e = parse_melody(lines, [pdf_pages[9], pdf_pages[10]], "E", [10, 10, 12, 12, 8])
    f = parse_melody(lines, [pdf_pages[11], pdf_pages[12]], "F", [16] * 5)
    g = parse_g(lines, b, pdf_pages[13])
    h = parse_h(lines, [pdf_pages[14], pdf_pages[15]])
    i = parse_i(lines, b, c, f, pdf_pages[16])
    j = parse_j(lines, h, pdf_pages[18])
    modules = {"A": a, "B": b, "C": c, "D": d, "E": e, "F": f, "G": g, "H": h, "I": i, "J": j}
    count = {"A": 0, "B": sum(x["workout"]["attack_count"] for x in b)}
    for key in "CDEFGHIJ":
        count[key] = sum(item["attack_count"] for item in modules[key])
    require(count == COUNTS and sum(count.values()) == 558 and a["silent_prompt_count"] == 45, "WORKLOAD_TOTAL", count)
    for key, page_numbers in PAGES.items():
        if key != "A":
            require(all(f"Module {key}" in pdf_pages[n - 1] for n in page_numbers), "PDF_MODULE_LABEL", key)
    return {"schema": "fathom.detached.curriculum.level054.whole.r01", "wbs": "2.3.1.2.1", "level": 54,
            "title": lines[1], "source": {"txt": {"path": str(TXT), "bytes": len(txt), "sha256": sha(txt), "lines": len(lines)},
                                         "pdf": {"path": str(PDF), "bytes": len(pdf), "sha256": sha(pdf), "pages": len(pdf_pages)},
                                         "source_map": {"path": str(MAP), "bytes": len(source_map), "sha256": sha(source_map)}},
            "source_map_row": map_row, "reference_cycle": "C open -> A fret 3 -> G fret 5 -> E fret 8 -> D fret 10 -> next C area fret 12",
            "root_formulas": FORMULA, "modules": modules, "sounded_attacks_by_module": count,
            "sounded_attacks": sum(count.values()), "silent_formation_prompts": 45,
            "source_notes": ["Module B's 66-attack breakdown is explicit in PDF pages 3-7; TXT supplies forms and fragments.",
                             "Module G names full-form roots even when practical fragment omits that string.",
                             "Module E linking and reverse passes reuse printed cards; PDF gives no added attack total.",
                             "Module F accent-removal pass is practice guidance outside the printed 80-attack workload.",
                             "Module H voice audits are guidance outside its 80 attacks; Module J reuses H triads in a separately counted 80-attack capstone."],
            "candidate_status": "detached_pending_P02_integration", "canonical_ids": None,
            "runtime_import": False, "content_admitted": False, "timing_or_audio_inferred": False}


def write_candidate(candidate: dict, output: Path, root: Path = ROOT) -> str:
    target = output if output.is_absolute() else root / output
    allowed = (root / BUILD).resolve()
    require(not target.is_symlink() and target.resolve().parent == allowed and target.suffix == ".json",
            "OUTPUT_BOUNDARY", target)
    require(not target.exists(), "OUTPUT_EXISTS", target)
    target.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(candidate, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    target.write_bytes(data)
    return sha(data)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=BUILD / "level054-candidate-a.json")
    args = parser.parse_args()
    try:
        candidate = build()
        digest = write_candidate(candidate, args.output)
    except (CandidateError, OSError, UnicodeError) as exc:
        parser.exit(2, f"LEVEL054_CANDIDATE_ERROR {exc}\n")
    print(f"LEVEL054_CANDIDATE_OK attacks={candidate['sounded_attacks']} silent={candidate['silent_formation_prompts']} sha256={digest} output={args.output}")


if __name__ == "__main__":
    main()
