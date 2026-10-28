#!/usr/bin/env python3
"""Pinned, detached whole-Level-46 A7/D7/E7 curriculum candidate."""

from __future__ import annotations

import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path
import re

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
STEM = "Scale_Exercises_Section_V_Level_46_A7_D7_E7_Chord_Tone_Targeting_and_Guide_Tone_Voice_Leading_Fixed_Key_A"
TXT_REL = Path("Notes/music/guitar project/TXT version") / (STEM + ".txt")
PDF_REL = Path("Notes/music/guitar project/PDF version") / (STEM + ".pdf")
TXT_BYTES, TXT_SHA256 = 31776, "5da713ae996e5458d04af6418670e05096a30f2be94fe344bd7acd59b137c291"
PDF_BYTES, PDF_SHA256 = 56884, "2daf0c87123a89cccf5fb6a6e2f1643ef9bb69d92b6767b6ba644f6e8348e9bd"
BUILD_REL = Path("Build/parallel-09/2.3.1.1.1-level046-whole-r01")
STRINGS = ("e", "B", "G", "D", "A", "E")
OPEN = {"E": 40, "A": 45, "D": 50, "G": 55, "B": 59, "e": 64}
PC = {"A": 9, "C": 0, "C#": 1, "D": 2, "Eb": 3, "E": 4, "F#": 6, "G": 7, "G#": 8, "B": 11}
CHORDS = {"A7": {"A": "R", "C#": "3", "E": "5", "G": "b7"},
          "D7": {"D": "R", "F#": "3", "A": "5", "C": "b7"},
          "E7": {"E": "R", "G#": "3", "B": "5", "D": "b7"}}
ROLES = {"A7": {**CHORDS["A7"], "C": "b3", "D": "11", "Eb": "b5", "B": "9"},
         "D7": {**CHORDS["D7"], "E": "9", "G": "11", "Eb": "b9", "B": "13"},
         "E7": {**CHORDS["E7"], "A": "11", "C": "b13", "Eb": "M7", "G": "#9"}}
FORM = ["A7"] * 4 + ["D7"] * 2 + ["A7"] * 2 + ["E7", "D7", "A7", "E7"]
COUNTS = {"A": 294, "B": 30, "C": 48, "D": 120, "E": 80, "F": 60, "G": 48, "H": 24}
MODULE_LINE = {"A": 50, "B": 244, "C": 308, "D": 322, "E": 381, "F": 441, "G": 468, "H": 555}
PDF_PAGES = {"A": [3, 4, 5, 6, 7], "B": [8], "C": [9], "D": [10, 11],
             "E": [12, 13, 14], "F": [15, 16], "G": [17, 18], "H": [19]}
CONTACT = re.compile(r"(A|C#|C|D|Eb|E|F#|G#|G|B)\(([eBGDAE])(\d+)\)")


class CandidateError(ValueError):
    pass


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _pin(data: bytes, size: int, sha: str, label: str) -> None:
    if len(data) != size or _sha(data) != sha:
        raise CandidateError(f"PINNED_INPUT_DRIFT {label}: {len(data)} {_sha(data)}")


def _check_contact(note: str, string: str, fret: int, context: str) -> None:
    if note not in PC or string not in OPEN or fret < 0 or (OPEN[string] + fret) % 12 != PC[note]:
        raise CandidateError(f"PITCH_CONTACT_MISMATCH {context}: {note}({string}{fret})")


def _contact(value: str, context: str) -> dict:
    m = CONTACT.fullmatch(value)
    if not m:
        raise CandidateError(f"CONTACT_SHAPE {context}: {value}")
    note, string, fret = m.group(1), m.group(2), int(m.group(3))
    _check_contact(note, string, fret, context)
    return {"note": note, "string": string, "fret": fret}


def _slots(line: str, label: str, groups: int, width: int) -> list[list[str | None]]:
    head = " " + label if label in STRINGS else label
    parts = line.split("|")
    if len(parts) != groups + 2 or parts[0] != head or parts[-1] != "":
        raise CandidateError(f"GRID_SHAPE {label}: {line}")
    result = []
    for part in parts[1:-1]:
        if len(part) != width * 4:
            raise CandidateError(f"GRID_WIDTH {label}: {line}")
        values = []
        for j in range(0, len(part), 4):
            cell = part[j:j + 4]
            if cell == "----":
                values.append(None)
            else:
                token = cell.rstrip("-")
                if not token or token + "-" * (4 - len(token)) != cell:
                    raise CandidateError(f"GRID_SLOT {label}: {cell}")
                values.append(token)
        result.append(values)
    return result


def _grid(rows: list[str], chord_by_group: list[str], width: int, context: str, marked: bool = False) -> list[list[dict]]:
    labels = ["Nte", "Rol", *STRINGS]
    if len(rows) != 8:
        raise CandidateError(f"GRID_ROWS {context}")
    parsed = {label: _slots(row, label, len(chord_by_group), width)
              for label, row in zip(labels, rows, strict=True)}
    groups = []
    for g, chord in enumerate(chord_by_group):
        events = []
        for j in range(width):
            note = parsed["Nte"][g][j]
            raw_role = parsed["Rol"][g][j]
            mark = bool(raw_role and raw_role.startswith(">"))
            role = raw_role[1:] if mark else raw_role
            if note not in ROLES[chord] or role != ROLES[chord][note] or mark != (marked and j == 0):
                raise CandidateError(f"ROLE_MISMATCH {context} group={g+1} slot={j+1}: {note}/{role}/{chord}")
            found = [(s, parsed[s][g][j]) for s in STRINGS if parsed[s][g][j] is not None]
            if len(found) != 1 or not found[0][1].isdigit():
                raise CandidateError(f"TAB_CARDINALITY {context} group={g+1} slot={j+1}")
            string, fret = found[0][0], int(found[0][1])
            _check_contact(note, string, fret, context)
            events.append({"note": note, "role": role, "chord": chord, "string": string, "fret": fret,
                           "beat_one_marker": mark, "onset_q": None, "duration_q": None})
        groups.append(events)
    return groups


def _bar_values(line: str, prefix: str) -> list[str]:
    if not line.startswith(prefix):
        raise CandidateError(f"BAR_ROW_PREFIX {prefix}")
    values = [v.strip() for v in line[len(prefix):].split(" | ")]
    if len(values) != 12:
        raise CandidateError(f"BAR_ROW_COUNT {prefix}: {len(values)}")
    return values


def _parse_txt(data: bytes) -> dict:
    lines = data.decode("utf-8").splitlines()
    if len(lines) != 604 or lines[0:2] != ["SCALE EXERCISES - SECTION V, LEVEL 46",
        "A7-D7-E7 CHORD-TONE TARGETING AND GUIDE-TONE VOICE LEADING - FIXED KEY A"]:
        raise CandidateError("TXT_BOUNDARY")
    for chord, tones in CHORDS.items():
        if not any(x.startswith(chord + " = " + " ".join(tones)) for x in lines[9:12]):
            raise CandidateError(f"HARMONY_MISMATCH {chord}")
    if lines[14] != "A7: C# + G    D7: F# + C    E7: G# + D":
        raise CandidateError("GUIDE_SHELL_MISMATCH")
    if not all(f"{COUNTS[k]} tones" in lines[21+i] for i, k in enumerate("ABCDEFGH")) or \
            lines[29] != "Complete written workload: 704 sounding tones before repeats.":
        raise CandidateError("PRINTED_COUNT_MISMATCH")
    for k, n in MODULE_LINE.items():
        if not lines[n-1].startswith("MODULE " + k + " - "):
            raise CandidateError(f"MODULE_BOUNDARY {k}")
    a = []
    for p in range(1, 6):
        headings = [i for i, x in enumerate(lines[:243]) if x.startswith(f"P{p} - ")]
        if len(headings) != 1:
            raise CandidateError(f"A_POSITION {p}")
        start = headings[0]
        cells = [i for i in range(start + 1, min(start + 40, 243)) if re.fullmatch(r"(?:A7|D7|E7) - \d+-NOTE TARGET CELL", lines[i])]
        if len(cells) != 3:
            raise CandidateError(f"A_CELL_COUNT P{p}")
        for chord, i in zip(("A7", "D7", "E7"), cells, strict=True):
            match = re.fullmatch(rf"{chord} - (\d+)-NOTE TARGET CELL", lines[i])
            if not match:
                raise CandidateError(f"A_CELL_HEADER P{p} {chord}")
            n = int(match.group(1))
            loc = lines[i+1]
            if not loc.startswith("Locations: "):
                raise CandidateError(f"A_LOCATIONS P{p} {chord}")
            targets = []
            for raw in loc[11:].split(", "):
                m = re.fullmatch(r"(.+\(.[0-9]+),([R35]|b7)\)", raw)
                if not m:
                    raise CandidateError(f"A_LOCATION_SHAPE {raw}")
                contact = _contact(m.group(1) + ")", f"A-P{p}-{chord}")
                if CHORDS[chord].get(contact["note"]) != m.group(2):
                    raise CandidateError(f"A_LOCATION_ROLE P{p} {chord}")
                targets.append({**contact, "role": m.group(2)})
            if n != len(targets) * 2:
                raise CandidateError(f"A_LOCATION_COUNT P{p} {chord}")
            rows = lines[i+2:i+10]
            events = _grid(rows, [chord], n, f"A-P{p}-{chord}")[0]
            asc = [(e["note"], e["string"], e["fret"], e["role"]) for e in events[:n//2]]
            desc = [(e["note"], e["string"], e["fret"], e["role"]) for e in events[n//2:]]
            target_values = [(t["note"], t["string"], t["fret"], t["role"]) for t in targets]
            if asc != target_values or desc != list(reversed(asc)):
                raise CandidateError(f"A_TURN_MISMATCH P{p} {chord}")
            if not lines[i+10].startswith("Rule: "):
                raise CandidateError(f"A_RULE_MISSING P{p} {chord}")
            a.append({"position": p, "position_heading": lines[start], "chord": chord, "targets": targets,
                      "events": events, "printed_rows": rows, "rule": lines[i+10], "txt_line": i+1,
                      "pdf_page": 2+p})
    b = []
    for p in range(1, 6):
        i = 246 + (p-1)*12
        if lines[i] != f"P{p} GUIDE-TONE DYADS":
            raise CandidateError(f"B_POSITION P{p}")
        for j, chord in enumerate(("A7", "D7", "E7")):
            line = lines[i+1+j*3]
            m = re.fullmatch(rf"{chord}: ([A-G]#?\((?:3|b7)\)) at ([eBGDAE])(\d+) \+ ([A-G]#?\((?:3|b7)\)) at ([eBGDAE])(\d+)", line)
            if not m:
                raise CandidateError(f"B_DYAD_SHAPE P{p} {chord}")
            contacts = []
            for note_role, string, fret in ((m.group(1), m.group(2), m.group(3)),
                                           (m.group(4), m.group(5), m.group(6))):
                note, role = note_role[:-1].split("(")
                _check_contact(note, string, int(fret), f"B-P{p}-{chord}")
                if CHORDS[chord].get(note) != role:
                    raise CandidateError(f"B_ROLE P{p} {chord}")
                contacts.append({"note": note, "role": role, "string": string, "fret": int(fret),
                                 "onset_q": None, "duration_q": None})
            if {v["role"] for v in contacts} != {"3", "b7"}:
                raise CandidateError(f"B_SHELL P{p} {chord}")
            tab = lines[i+2+j*3:i+4+j*3]
            tab_contacts = []
            for row in tab:
                tm = re.fullmatch(r"([eBGDAE])\|(-{0,4})(\d+)(-{0,8})\|", row)
                if not tm:
                    raise CandidateError(f"B_TAB_SHAPE P{p} {chord}")
                tab_contacts.append((tm.group(1), int(tm.group(3))))
            if sorted(tab_contacts) != sorted((c["string"], c["fret"]) for c in contacts):
                raise CandidateError(f"B_TAB_CONTACT P{p} {chord}")
            b.append({"position": p, "chord": chord, "contacts": contacts, "printed_text": line,
                      "printed_tab": tab, "txt_line": i+2, "pdf_page": 8})
        if lines[i+10] != "Practice sequence: A7 -> D7 -> A7 -> E7 -> D7 -> A7 -> E7.":
            raise CandidateError(f"B_SEQUENCE P{p}")
    if _bar_values(lines[310], "Chord | ") != FORM:
        raise CandidateError("C_FORM")
    c = []
    for i, label in enumerate(("Root", "Third", "b7", "Mixed"), 311):
        contacts = [_contact(raw, f"C-{label}") for raw in _bar_values(lines[i], label + " pass | ")]
        for chord, contact in zip(FORM, contacts, strict=True):
            if contact["note"] not in CHORDS[chord]:
                raise CandidateError(f"C_TARGET_ROLE {label} {chord}")
            contact["chord"] = chord
            contact["role"] = CHORDS[chord][contact["note"]]
            contact["onset_q"] = contact["duration_q"] = None
        if label != "Mixed" and any(x["role"] != {"Root": "R", "Third": "3", "b7": "b7"}[label] for x in contacts):
            raise CandidateError(f"C_PASS_ROLE {label}")
        c.append({"pass": label, "targets": contacts, "printed_row": lines[i], "txt_line": i+1, "pdf_page": 9})
    d = []
    for p in range(1, 6):
        i = 324 + (p-1)*11
        if lines[i] != f"P{p} - TWO GUIDE-TONE VOICES" or _bar_values(lines[i+2], "Chord | ") != FORM:
            raise CandidateError(f"D_POSITION_FORM P{p}")
        voices = []
        for v in (1, 2):
            off = 3 if v == 1 else 6
            notes = _bar_values(lines[i+off], f"Voice {v} notes: ")
            roles = _bar_values(lines[i+off+1], f"Voice {v} roles: ")
            sm = re.fullmatch(r"([eBGDAE]) string frets: (.+)", lines[i+off+2])
            if not sm:
                raise CandidateError(f"D_STRING P{p} V{v}")
            string = sm.group(1)
            frets = sm.group(2).split(" | ")
            if len(frets) != 12:
                raise CandidateError(f"D_FRETS P{p} V{v}")
            events = []
            for bar, (chord, note, role, fret) in enumerate(zip(FORM, notes, roles, frets, strict=True), 1):
                if not fret.isdigit() or CHORDS[chord].get(note) != role or role not in ("3", "b7"):
                    raise CandidateError(f"D_ROLE P{p} V{v} BAR{bar}")
                _check_contact(note, string, int(fret), f"D-P{p}-V{v}-BAR{bar}")
                events.append({"bar": bar, "chord": chord, "note": note, "role": role,
                               "string": string, "fret": int(fret), "onset_q": None, "duration_q": None})
            voices.append(events)
        if not all({voices[0][j]["role"], voices[1][j]["role"]} == {"3", "b7"} for j in range(12)):
            raise CandidateError(f"D_SHELL_COMPLEMENT P{p}")
        d.append({"position": p, "voices": voices, "printed_rows": lines[i+1:i+9],
                  "shell_instruction": lines[i+9], "txt_line": i+1, "pdf_page": 10 if p < 4 else 11})
    e = []
    for p in range(1, 6):
        i = 384 + (p-1)*11
        if lines[i] != f"P{p} - 16-NOTE TARGET PHRASE":
            raise CandidateError(f"E_HEADER P{p}")
        rows = lines[i+1:i+9]
        groups = _grid(rows, ["A7", "D7", "E7", "A7"], 4, f"E-P{p}", marked=True)
        if any(g[0]["note"] not in CHORDS[g[0]["chord"]] for g in groups):
            raise CandidateError(f"E_BEAT_ONE P{p}")
        e.append({"position": p, "bars": groups, "printed_rows": rows, "transformation": lines[i+9],
                  "txt_line": i+1, "pdf_page": 12 + (p-1)//2})
    f = []
    for chord, start in (("A7", 444), ("D7", 451), ("E7", 458)):
        if lines[start-1] != f"{chord} THIRD-ARRIVAL SITES":
            raise CandidateError(f"F_HEADING {chord}")
        for i in range(start, start+5):
            raw = lines[i]
            m = re.fullmatch(r"([eBGDAE]) string: target ([A-G]#?) fret (\d+); slide (\d+)/(\d+); bend (\d+)b\((\d+)\); release (\d+)b\((\d+)\)r(\d+); (.+)\.", raw)
            if not m:
                raise CandidateError(f"F_SITE_SHAPE L{i+1}")
            string, note, target, slide_from, slide_to, bend_from, bend_to, release_from, release_to, release_end, function = m.groups()
            values = list(map(int, (target, slide_from, slide_to, bend_from, bend_to, release_from, release_to, release_end)))
            target, slide_from, slide_to, bend_from, bend_to, release_from, release_to, release_end = values
            _check_contact(note, string, target, f"F-L{i+1}")
            if CHORDS[chord].get(note) != "3" or target != slide_to or target != bend_to or bend_from != slide_from or (release_from, release_to, release_end) != (bend_from, target, bend_from):
                raise CandidateError(f"F_THIRD_ARRIVAL L{i+1}")
            f.append({"chord": chord, "string": string, "target_note": note, "target_fret": target,
                      "slide": f"{slide_from}/{slide_to}", "bend": f"{bend_from}b({bend_to})",
                      "bend_release": f"{release_from}b({release_to})r{release_end}", "function": function,
                      "source_described_event_count": 4, "printed_text": raw, "txt_line": i+1,
                      "pdf_page": 15 if chord != "E7" else 16, "performed_bend_pitch": None})
    g = []
    for bar in range(1, 13):
        positions = [i for i, line in enumerate(lines[470:552], 470) if line.startswith(f"BAR {bar} - ")]
        if len(positions) != 1:
            raise CandidateError(f"G_BAR_HEADER {bar}")
        i = positions[0]
        chord = lines[i].split(" - ")[1]
        if chord != FORM[bar-1]:
            raise CandidateError(f"G_FORM BAR{bar}")
        notes = lines[i+1].removeprefix("Notes: ").split()
        roles = lines[i+2].removeprefix("Roles: ").split()
        if len(notes) != 4 or len(roles) != 4 or not roles[0].startswith(">"):
            raise CandidateError(f"G_NOTE_ROLE_SHAPE BAR{bar}")
        tab = []
        j = i+3
        while j < len(lines) and re.fullmatch(r"[eBGDAE]\|[-\d]+\|", lines[j]):
            tab.append(lines[j]); j += 1
        if len(tab) not in (2, 3):
            raise CandidateError(f"G_TAB_ROWS BAR{bar}")
        events = []
        for slot, (note, raw_role) in enumerate(zip(notes, roles, strict=True)):
            role = raw_role.lstrip(">")
            if ROLES[chord].get(note) != role:
                raise CandidateError(f"G_ROLE BAR{bar} SLOT{slot+1}")
            found = []
            for row in tab:
                body = row.split("|")[1]
                if len(body) != 16:
                    raise CandidateError(f"G_TAB_WIDTH BAR{bar}")
                token = body[slot*4:slot*4+4].rstrip("-")
                if token:
                    found.append((row[0], token))
            if len(found) != 1 or not found[0][1].isdigit():
                raise CandidateError(f"G_TAB_CARDINALITY BAR{bar} SLOT{slot+1}")
            string, fret = found[0][0], int(found[0][1])
            _check_contact(note, string, fret, f"G-BAR{bar}")
            events.append({"note": note, "role": role, "chord": chord, "bar": bar, "string": string,
                           "fret": fret, "beat_one_marker": slot == 0, "onset_q": None, "duration_q": None})
        if events[0]["note"] not in CHORDS[chord]:
            raise CandidateError(f"G_BEAT_ONE BAR{bar}")
        g.append({"bar": bar, "chord": chord, "events": events, "printed_tab": tab,
                  "txt_line": i+1, "pdf_page": 17 if bar <= 6 else 18})
    if (g[-1]["events"][-1]["note"], g[-1]["events"][-1]["role"]) != ("G#", "3"):
        raise CandidateError("G_TURN")
    h = []
    for i in range(556, 568):
        m = re.fullmatch(r"(A7|D7|E7): ([A-G]#?b?) -> ([A-G]#?b?)   (.+) -> (.+)", lines[i])
        if not m:
            raise CandidateError(f"H_CARD_SHAPE L{i+1}")
        chord, before, after, before_role, after_role = m.groups()
        if ROLES[chord].get(before) != before_role or CHORDS[chord].get(after) != after_role:
            raise CandidateError(f"H_CARD_ROLE L{i+1}")
        h.append({"chord": chord, "from_note": before, "from_role": before_role,
                  "to_note": after, "to_role": after_role, "printed_text": lines[i],
                  "txt_line": i+1, "pdf_page": 19, "onset_q": None, "duration_q": None})
    modules = dict(zip("ABCDEFGH", (a, b, c, d, e, f, g, h), strict=True))
    observed = {"A": sum(len(x["events"]) for x in a), "B": sum(len(x["contacts"]) for x in b),
                "C": sum(len(x["targets"]) for x in c), "D": sum(len(v) for x in d for v in x["voices"]),
                "E": sum(len(v) for x in e for v in x["bars"]), "F": sum(x["source_described_event_count"] for x in f),
                "G": sum(len(x["events"]) for x in g), "H": len(h)*2}
    if observed != COUNTS:
        raise CandidateError(f"MODULE_COUNT_MISMATCH {observed}")
    return {"modules": modules, "lines": lines,
            "instruction_text": {"purpose": "\n".join(lines[3:7]), "guide_tones": lines[14:19],
                "chord_role_matrix": lines[32:47], "C": lines[316:319], "E": lines[382],
                "F": lines[464], "G": lines[551], "H": lines[569:575],
                "practice": lines[577:589], "error_diagnosis": lines[590:598],
                "mastery_gate": lines[599:601], "next_level": lines[602:604]}}


def _pdf(data: bytes, parsed: dict) -> dict:
    reader = PdfReader(BytesIO(data))
    if len(reader.pages) != 20:
        raise CandidateError("PDF_PAGE_COUNT")
    pages = [p.extract_text() or "" for p in reader.pages]
    if any(f"Page {i} of 20" not in page for i, page in enumerate(pages, 1)):
        raise CandidateError("PDF_PAGE_BOUNDARY")
    modules = parsed["modules"]
    checked = {k: 0 for k in "ABCDEFGH"}
    for x in modules["A"]:
        page = pages[x["pdf_page"]-1]
        for value in [f'{x["chord"]} - {len(x["events"])}-NOTE TARGET CELL',
                      "Locations: " + ", ".join(f'{t["note"]}({t["string"]}{t["fret"]},{t["role"]})' for t in x["targets"]),
                      *x["printed_rows"]]:
            if value not in page:
                raise CandidateError(f"PDF_A_MISMATCH P{x['position']} {x['chord']}: {value[:40]}")
        checked["A"] += 1
    for x in modules["B"]:
        page = pages[7]
        pair = " + ".join(f'{c["note"]}({c["role"]})' for c in x["contacts"])
        if pair not in page or any(row not in page for row in x["printed_tab"]):
            raise CandidateError(f"PDF_B_MISMATCH P{x['position']} {x['chord']}")
        checked["B"] += 1
    page = pages[8]
    for x in modules["C"]:
        sequence = "\n".join(f'{t["note"]}({t["string"]}{t["fret"]})' for t in x["targets"])
        if x["pass"] + " pass\n" + sequence not in page:
            raise CandidateError(f"PDF_C_MISMATCH {x['pass']}")
        checked["C"] += 1
    for x in modules["D"]:
        page = pages[x["pdf_page"]-1]
        for v, voice in enumerate(x["voices"], 1):
            for prefix, values in ((f"V{v}N", [e["note"] for e in voice]),
                                   (f"V{v}R", [e["role"] for e in voice])):
                row = prefix + "|" + "|".join(value + "-"*(4-len(value)) for value in values) + "|"
                if row not in page:
                    raise CandidateError(f"PDF_D_MISMATCH P{x['position']} {prefix}")
            string = voice[0]["string"]
            fret_row = "  " + string + " |" + "|".join(str(e["fret"]) + "-"*(4-len(str(e["fret"]))) for e in voice) + "|"
            if fret_row not in page:
                raise CandidateError(f"PDF_D_MISMATCH P{x['position']} {string} FRETS")
        checked["D"] += 1
    for x in modules["E"]:
        page = pages[x["pdf_page"]-1]
        if any(row not in page for row in x["printed_rows"]):
            raise CandidateError(f"PDF_E_MISMATCH P{x['position']}")
        checked["E"] += 1
    for x in modules["F"]:
        page = pages[x["pdf_page"]-1]
        values = [x["string"], f'{x["target_note"]} {x["target_fret"]}', x["slide"], x["bend"], x["bend_release"], x["function"]]
        pattern = r"\n".join(re.escape(v) for v in values)
        if not re.search(pattern, page):
            raise CandidateError(f"PDF_F_MISMATCH L{x['txt_line']}")
        checked["F"] += 1
    for x in modules["G"]:
        page = pages[x["pdf_page"]-1]
        names = "Nte|" + "".join(e["note"] + "-"*(4-len(e["note"])) for e in x["events"]) + "|"
        roles = "Rol|" + "".join((">" if j==0 else "") + e["role"] + "-"*(4-len(e["role"])-(j==0)) for j,e in enumerate(x["events"])) + "|"
        if names not in page or roles not in page or any(row not in page for row in x["printed_tab"]):
            raise CandidateError(f"PDF_G_MISMATCH BAR{x['bar']}")
        checked["G"] += 1
    for x in modules["H"]:
        page = pages[18]
        if f'{x["chord"]}: {x["from_note"]} -> {x["to_note"]}\n{x["from_role"]} -> {x["to_role"]}\n2 tones' not in page:
            raise CandidateError(f"PDF_H_MISMATCH L{x['txt_line']}")
        checked["H"] += 1
    if checked != {"A": 15, "B": 15, "C": 4, "D": 5, "E": 5, "F": 15, "G": 12, "H": 12}:
        raise CandidateError(f"PDF_RECONCILIATION_COUNT {checked}")
    return {"pages": len(pages), "checked_items": checked, "module_pages": PDF_PAGES,
            "discrepancies": [], "extracted_page_text": pages}


def build_candidate(txt_data: bytes | None = None, pdf_data: bytes | None = None) -> dict:
    for rel in (TXT_REL, PDF_REL):
        path = ROOT / rel
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(ROOT.resolve()):
            raise CandidateError(f"SOURCE_PATH_INVALID {rel}")
    txt = txt_data if txt_data is not None else (ROOT / TXT_REL).read_bytes()
    pdf = pdf_data if pdf_data is not None else (ROOT / PDF_REL).read_bytes()
    _pin(txt, TXT_BYTES, TXT_SHA256, "L46-TXT")
    _pin(pdf, PDF_BYTES, PDF_SHA256, "L46-PDF")
    parsed = _parse_txt(txt)
    pdf_check = _pdf(pdf, parsed)
    return {"schema": "fathom-level046-whole-detached-candidate-v1", "wbs_id": "2.3.1.1.1", "level": 46,
            "source": {"txt_path": TXT_REL.as_posix(), "txt_bytes": TXT_BYTES, "txt_sha256": TXT_SHA256,
                       "pdf_path": PDF_REL.as_posix(), "pdf_bytes": PDF_BYTES, "pdf_sha256": PDF_SHA256,
                       "pdf_pages": 20}, "harmony": {k: list(v) for k,v in CHORDS.items()},
            "chord_roles": ROLES, "twelve_bar_form": FORM, "modules": parsed["modules"],
            "module_note_counts": COUNTS, "complete_workload_source_described_tones": 704,
            "instructions": parsed["instruction_text"], "txt_document_text": txt.decode("utf-8"),
            "pdf_reconciliation": pdf_check,
            "canonical_item_id": None, "canonical_variant_id": None, "fixed_bpm": None,
            "note_per_click": None, "onset_q": None, "duration_q": None,
            "runtime_eligible": False, "runtime_admitted": False, "imported": False, "admitted": False,
            "curriculum_signoff": False, "performed_result": None}


def write_candidate(path: Path) -> dict:
    build = ROOT / BUILD_REL
    if (not build.resolve().is_relative_to(ROOT.resolve()) or build.is_symlink() or path.is_symlink()
            or path.parent.is_symlink() or path.parent.resolve() != build.resolve() or path.suffix != ".json"):
        raise CandidateError("OUTPUT_OUTSIDE_LANE_BUILD")
    if path.exists():
        raise CandidateError("OUTPUT_EXISTS")
    candidate = build_candidate()
    build.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(candidate, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode()
    with path.open("xb") as handle:
        handle.write(encoded)
    return {"path": str(path), "bytes": len(encoded), "sha256": _sha(encoded),
            "modules": len(candidate["modules"]), "tones": sum(COUNTS.values())}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(json.dumps(write_candidate(args.output), sort_keys=True))


if __name__ == "__main__":
    main()
