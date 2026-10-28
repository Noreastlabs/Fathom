#!/usr/bin/env python3
"""Detached, source-bound whole-Level49 open-chord workbook candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from pypdf import PdfReader


STEM = "Guitar_Exercises_Section_VI_Level_49_Chord_Mechanics_Muting_and_Open_Chord_Foundation"
TXT_REL = f"Notes/music/guitar project/TXT version/{STEM}.txt"
PDF_REL = f"Notes/music/guitar project/PDF version/{STEM}.pdf"
TXT_BYTES = 21942
TXT_SHA = "8487f1d1bc949e79509de98b10e1888200d48ddf8651d98979634e44b9fc20c3"
PDF_BYTES = 62737
PDF_SHA = "abadffbe75122328585fd64758e3ef9ffb7c6f8c9d2f14702e173a97808cfd8f"
MAP_REL = "Results/parallel-01/exercises/inventory/20260922T180500Z-2.3-curriculum-v1-source-inventory-evidence/curriculum-source-map.json"
MAP_BYTES = 199753
MAP_SHA = "bad5581a04f43ba8baf14db430449e1ccff5cf88f0f7e42198328073b27053d6"
STRINGS = ("E", "A", "D", "G", "B", "e")
OPEN = {"E": 4, "A": 9, "D": 2, "G": 7, "B": 11, "e": 4}
PC = {"C": 0, "C#": 1, "D": 2, "E": 4, "F": 5, "F#": 6, "G": 7, "G#": 8, "A": 9, "B": 11}
OPEN_CHORDS = ("E", "Em", "A", "Am", "D", "Dm", "C", "G")
POWER_CHORDS = ("E5", "A5", "D5")
ALL_CHORDS = OPEN_CHORDS + POWER_CHORDS
MODULE_COUNTS = {"A1": 24, "A2": 48, "B": 96, "C": 36, "D": 64, "E": 64, "F": 128, "G": 64, "H": 96, "I": 96, "J": 64}
MODULE_UNITS = {"A1": 6, "A2": 8, "B": 8, "C": 3, "D": 8, "E": 8, "F": 8, "G": 8, "H": 8, "I": 6, "J": 4}
PAIR_LABELS = ("E <-> Em", "A <-> Am", "D <-> Dm", "C <-> Am", "Em <-> G", "G <-> C", "D <-> A", "E <-> A")
G_LABELS = ("E <-> Em", "D <-> Dm", "C <-> Am", "G <-> Em", "Em <-> C", "G <-> C", "A <-> D", "A <-> Am")
PROGRESSIONS = ("A-D-E-A", "D-G-A-D", "G-C-D-G", "Em-G-D-C", "Am-C-G-Em", "Am-Dm-Em-Am")


def _pin(path: Path, size: int, sha: str) -> bytes:
    raw = path.read_bytes()
    if len(raw) != size or hashlib.sha256(raw).hexdigest() != sha:
        raise ValueError(f"source identity drift: {path}")
    return raw


def _tokens(row: str, prefix: str, width: int = 5) -> list[str]:
    if not row.startswith(prefix + "|") or not row.endswith("|"):
        raise ValueError(f"row prefix/terminator drift: {row!r}")
    body = row.split("|", 1)[1][:-1]
    if len(body) % width:
        raise ValueError(f"unaligned row: {row!r}")
    return [body[i:i + width].strip("-") for i in range(0, len(body), width)]


def _pdf_row(pdf: str, row: str, page: int) -> None:
    if row not in pdf:
        raise ValueError(f"TXT/PDF row mismatch p{page}: {row!r}")


def _source_map(root: Path) -> dict:
    source_map = json.loads(_pin(root / MAP_REL, MAP_BYTES, MAP_SHA))
    row = source_map["rows"][48]
    expected = {"level": 49, "section": "VI", "wbs_owner": "2.3.1.2.1", "txt_path": TXT_REL, "txt_bytes": TXT_BYTES, "txt_sha256": TXT_SHA, "pdf_path": PDF_REL, "pdf_bytes": PDF_BYTES, "pdf_sha256": PDF_SHA, "pair_status": "exact_stem_pair", "representative_status": "frozen_representative_record", "representative_item_id": "fg:item:000008", "review": "Pending", "runtime_eligible": False, "imported": False, "admitted": False}
    if any(row.get(k) != v for k, v in expected.items()):
        raise ValueError("source-map row49 drift")
    return row


def _sections(lines: list[str]) -> dict[str, tuple[int, int]]:
    starts = {}
    for i, line in enumerate(lines):
        match = re.match(r"MODULE (A1|A2|[B-J]) - ", line)
        if match and match.group(1) not in starts:
            starts[match.group(1)] = i
    names = list(MODULE_COUNTS)
    if list(starts) != names:
        raise ValueError("module heading/order drift")
    return {key: (start, starts[names[n + 1]] if n < len(names) - 1 else next(i for i in range(start, len(lines)) if lines[i] == "PRACTICE PROGRESSION AND ERROR REPAIR")) for n, (key, start) in enumerate(starts.items())}


def _parse_shapes(lines: list[str], pages: list[str], bounds: dict) -> dict[str, dict]:
    shapes = {}
    for module in ("B", "C"):
        start, stop = bounds[module]
        for i in range(start, stop):
            match = re.fullmatch(r"(E|Em|A|Am|D|Dm|C|G|E5|A5|D5): frets ([0-9x ]+)", lines[i])
            if not match:
                continue
            name = match.group(1)
            if name in shapes or i + 4 >= stop:
                raise ValueError("duplicate/incomplete chord shape")
            frets = match.group(2).split()
            if len(frets) != 6 or lines[i + 1] != "Strings: E A D G B e":
                raise ValueError(f"shape fret/string drift: {name}")
            finger = lines[i + 2].removeprefix("Fingers: ").split()
            notes = lines[i + 3].removeprefix("Notes:   ").split()
            if len(finger) != 6 or len(notes) != 6 or not lines[i + 4].startswith("Spelling: "):
                raise ValueError(f"shape finger/note rows drift: {name}")
            spelling = lines[i + 4].split(". Attack zone:", 1)[0].removeprefix("Spelling: ").split()
            sounding = []
            for string, fret, fng, note in zip(STRINGS, frets, finger, notes):
                if fret.lower() == "x":
                    if fng.lower() != "x" or note.upper() != "X":
                        raise ValueError(f"X-string shape mismatch: {name}/{string}")
                else:
                    num = int(fret)
                    if note not in PC or (OPEN[string] + num) % 12 != PC[note] or (num == 0 and fng != "O") or (num > 0 and fng not in ("1", "2", "3", "4")):
                        raise ValueError(f"shape pitch/finger mismatch: {name}/{string}")
                    sounding.append(note)
            if set(spelling) != set(sounding):
                raise ValueError(f"chord spelling mismatch: {name}")
            page = (5 + (list(OPEN_CHORDS).index(name) // 2)) if module == "B" else 9
            if " ".join(frets).upper() not in pages[page - 1].upper() or " ".join(spelling) not in pages[page - 1]:
                raise ValueError(f"TXT/PDF shape mismatch p{page}: {name}")
            shapes[name] = {"chord": name, "kind": "open" if module == "B" else "power", "frets": frets, "fingers": finger, "notes": notes, "spelling": spelling, "attack_zone": lines[i + 4].split("Attack zone: ", 1)[1].rstrip("."), "source_lines": lines[i:i + 5], "txt_line": i + 1, "pdf_page": page}
    if set(shapes) != set(ALL_CHORDS):
        raise ValueError("11 chord shape coverage drift")
    if shapes["A"]["fingers"] != ["x", "O", "2", "1", "3", "O"] or shapes["G"]["frets"] != ["3", "2", "0", "0", "0", "3"]:
        raise ValueError("A pivot/G open-fret shape drift")
    return shapes


def _attack(module: str, unit: str, number: int, symbol: str, kind: str, line: int, page: int, chord: str | None = None, string: str | None = None, fret: str | None = None) -> dict:
    return {"module": module, "unit": unit, "ordinal": number, "printed_symbol": symbol, "kind": kind, "chord": chord, "string": string, "printed_fret_or_mute": fret, "txt_line": line, "pdf_page": page, "performed_onset": None, "performed_duration": None, "performed_pick": None, "performed_quality": None}


def _a1(lines: list[str], bounds: tuple[int, int], pdf: str) -> list[dict]:
    start, stop = bounds
    entries = [(i, line) for i, line in enumerate(lines[start:stop], start) if re.match(r"^(index|middle|ring) finger: ", line)]
    if len(entries) != 6:
        raise ValueError("A1 pressure site count drift")
    units = []
    for idx, line in entries:
        match = re.match(r"^(index|middle|ring) finger: ([EADGBe])(\d+) \(([^)]+)\) - four attacks:", line)
        if not match:
            raise ValueError("A1 pressure site syntax drift")
        finger, string, fret, note = match.groups()
        if note not in PC or (OPEN[string] + int(fret)) % 12 != PC[note] or f"{finger.capitalize()} finger - {string}{fret} ({note})" not in pdf:
            raise ValueError("A1 pressure site pitch/PDF mismatch")
        jobs = ("clean", "fade to buzz threshold", "minimum clean pressure", "release without lifting")
        attacks = [_attack("A1", f"{string}{fret}", j + 1, str(j + 1), jobs[j], idx + 1, 3, string=string, fret=fret) for j in range(4)]
        units.append({"label": line, "txt_line": idx + 1, "pdf_page": 3, "printed_note": note, "fretting_finger": finger, "attacks": attacks})
    return units


def _a2(lines: list[str], bounds: tuple[int, int], pdf: str, shapes: dict) -> list[dict]:
    start, stop = bounds
    entries = [(i, line) for i, line in enumerate(lines[start:stop], start) if re.match(r"^(Em|E|Am|A|Dm|D|C|G): [0-3X ]+ \| start ", line)]
    if len(entries) != 8:
        raise ValueError("A2 chord audit count drift")
    units = []
    for idx, row in entries:
        name, rest = row.split(": ", 1)
        frets = rest.split(" |", 1)[0].split()
        if [x.upper() for x in frets] != [x.upper() for x in shapes[name]["frets"]] or f"\n{name}\n" not in pdf:
            raise ValueError(f"A2 chord row/PDF mismatch: {name}")
        attacks = [_attack("A2", name, j + 1, string, "muted-string test" if fret == "X" else "pitched-string test", idx + 1, 4, chord=name, string=string, fret=fret) for j, (string, fret) in enumerate(zip(STRINGS, frets))]
        units.append({"label": name, "source_row": row, "txt_line": idx + 1, "pdf_page": 4, "attacks": attacks})
    return units


def _cells(lines: list[str], bounds: tuple[int, int], pages: list[str], shapes: dict, module: str) -> list[dict]:
    start, stop = bounds
    indices = [i for i in range(start, stop) if lines[i].startswith("Str|")]
    expected = 8 if module == "B" else 3
    if len(indices) != expected:
        raise ValueError(f"{module} 12-attack cell count drift")
    units = []
    order = OPEN_CHORDS if module == "B" else POWER_CHORDS
    for idx, name in zip(indices, order):
        rows = lines[idx:idx + 5]
        if len(rows) != 5 or _tokens(rows[0], "Str") != list(STRINGS):
            raise ValueError(f"{module} string row drift: {name}")
        val, fng, nte = (_tokens(rows[j], label) for j, label in ((1, "Val"), (2, "Fng"), (3, "Nte")))
        shape = shapes[name]
        if [x.upper() for x in val] != [x.upper() for x in shape["frets"]] or [x.upper() for x in fng] != [x.upper() for x in shape["fingers"]] or [x.upper() for x in nte] != [x.upper() for x in shape["notes"]]:
            raise ValueError(f"{module} cell/shape mismatch: {name}")
        marks = rows[4].split("|", 1)[1].split("|", 1)[0].split("-")
        if len(marks) != 12 or marks != (["D", "x", "D", "x", "6", "5", "4", "3", "2", "1", "D", "D" if module == "B" else "x"]):
            raise ValueError(f"{module} attack-row drift: {name}")
        page = shape["pdf_page"]
        for row in rows[:4]:
            _pdf_row(pages[page - 1], row, page)
        pdf_atk = next((x for x in pages[page - 1].splitlines() if x.startswith("Atk|") and [z for z in x.split("|")[1].split("-") if z] == marks), None)
        if pdf_atk is None:
            raise ValueError(f"{module} TXT/PDF attack row mismatch: {name}")
        attacks = []
        for j, mark in enumerate(marks):
            if mark == "D":
                kind, string, fret = "downstrum", None, None
            elif mark == "x":
                kind, string, fret = "muted strum", None, None
            else:
                string = STRINGS[6 - int(mark)]
                fret = shape["frets"][STRINGS.index(string)]
                kind = "muted-string test" if fret.lower() == "x" else "pitched-string test"
            attacks.append(_attack(module, name, j + 1, mark, kind, idx + 5, page, chord=name, string=string, fret=fret))
        units.append({"label": name, "source_rows": rows, "txt_line": idx + 1, "pdf_page": page, "attacks": attacks})
    return units


def _grid_tokens(row: str, prefix: str, count: int) -> list[str]:
    if not row.startswith(prefix + "|"):
        raise ValueError(f"grid row drift: {row!r}")
    body = row.split("|", 1)[1].split("|", 1)[0]
    if prefix == "Chd":
        result = re.findall(r"Em|Am|Dm|[EADCG]", body)
    elif prefix == "Str":
        result = re.findall(r"[DUx]", body)
    else:
        result = re.findall(r"\d+", body)
    if len(result) != count:
        raise ValueError(f"grid slot count drift: {prefix} {len(result)} != {count}")
    return result


def _grid_module(module: str, lines: list[str], bounds: tuple[int, int], pages: list[str], shapes: dict) -> list[dict]:
    start, stop = bounds
    indices = [i for i in range(start, stop) if lines[i].startswith("Cnt|")]
    expected = 6 if module == "I" else 8
    count = 16 if module in ("F", "I") else 8
    if len(indices) != expected:
        raise ValueError(f"module {module} grid count drift")
    units = []
    for n, idx in enumerate(indices):
        rows = lines[idx:idx + 3]
        count_tokens = _grid_tokens(rows[0], "Cnt", count)
        chords = _grid_tokens(rows[1], "Chd", count)
        strokes = _grid_tokens(rows[2], "Str", count)
        if any(chord not in shapes for chord in chords) or strokes != ["D"] * count:
            raise ValueError(f"module {module} grid chord/stroke drift")
        if module in ("D", "E", "F"):
            label = PAIR_LABELS[n]
            if not lines[idx - 1].startswith(label + ":") or set(chords) != set(label.split(" <-> ")):
                raise ValueError(f"module {module} pair sequence drift")
            expected_pattern = ([label.split(" <-> ")[i % 2] for i in range(count)] if module != "E" else [label.split(" <-> ")[(i // 2) % 2] for i in range(count)])
            if chords != expected_pattern:
                raise ValueError(f"module {module} chord order drift")
            page = {"D": 10, "E": 11, "F": 12}[module]
        elif module == "G":
            label = G_LABELS[n]
            if lines[idx - 2] != label or chords != [label.split(" <-> ")[i % 2] for i in range(8)]:
                raise ValueError("module G transition sequence drift")
            page = 13 if n < 4 else 14
        else:
            label = PROGRESSIONS[n]
            if not lines[idx - 1].startswith(label + ":") or chords != [part for part in label.split("-") for _ in range(4)]:
                raise ValueError("module I progression sequence drift")
            page = 16 if n < 3 else 17
        for row in rows:
            _pdf_row(pages[page - 1], row, page)
        attacks = [_attack(module, label, j + 1, "D", "downstrum", idx + 3, page, chord=chord) for j, chord in enumerate(chords)]
        units.append({"label": label, "printed_count_labels": count_tokens, "source_rows": rows, "txt_line": idx + 1, "pdf_page": page, "attacks": attacks})
    return units


def _h(lines: list[str], bounds: tuple[int, int], pdf: str, shapes: dict) -> list[dict]:
    start, stop = bounds
    entries = [(i, line) for i, line in enumerate(lines[start:stop], start) if re.match(r"^(Em|E|Am|A|Dm|D|C|G): (?:[0-3X] ?){12}$", line)]
    if len(entries) != 8:
        raise ValueError("module H eight audits drift")
    units = []
    for idx, row in entries:
        name, values = row.split(": ", 1)
        frets = values.split()
        expected = shapes[name]["frets"] + list(reversed(shapes[name]["frets"]))
        if [x.upper() for x in frets] != [x.upper() for x in expected] or f"\n{name}\n" not in pdf:
            raise ValueError(f"module H 12-string shape/PDF drift: {name}")
        attacks = [_attack("H", name, j + 1, str(6 - j if j < 6 else j - 5), "muted-string test" if fret.upper() == "X" else "pitched-string test", idx + 1, 15, chord=name, string=STRINGS[j if j < 6 else 11 - j], fret=fret) for j, fret in enumerate(frets)]
        units.append({"label": name, "source_row": row, "txt_line": idx + 1, "pdf_page": 15, "attacks": attacks})
    return units


def _j(lines: list[str], bounds: tuple[int, int], pdf: str, shapes: dict) -> list[dict]:
    start, stop = bounds
    headings = [i for i in range(start, stop) if re.match(r"Pass [1-4] - ", lines[i])]
    if len(headings) != 4 or "Progression: Am | C | G | Em" not in lines[start:stop]:
        raise ValueError("module J four-pass shape drift")
    units = []
    for n, idx in enumerate(headings):
        span = lines[idx:headings[n + 1] if n < 3 else stop]
        grid = next((x.split("Grid: ", 1)[1] for x in span if x.startswith("Grid: ")), None)
        if grid != ("D D D D", "D . D . D . D .", "D x D x", "1 2 3 4")[n] or "16 attacks" not in span:
            raise ValueError("module J grid/count drift")
        if lines[idx] not in pdf or f"Grid|{grid}|" not in pdf:
            raise ValueError("TXT/PDF capstone pass mismatch")
        marks = [x for x in grid.split() if x != "."]
        if len(marks) != 4:
            raise ValueError("module J four attacks/bar drift")
        attacks = []
        for bar, chord in enumerate(("Am", "C", "G", "Em")):
            for k, mark in enumerate(marks):
                kind = "muted backbeat" if mark == "x" else "four-string arpeggio pick" if mark.isdigit() else "downstrum"
                attacks.append(_attack("J", lines[idx], bar * 4 + k + 1, mark, kind, idx + 1, 18, chord=chord))
        units.append({"label": lines[idx], "source_lines": span, "txt_line": idx + 1, "pdf_page": 18, "attacks": attacks})
    return units


def build_candidate(root: Path) -> dict:
    txt_raw = _pin(root / TXT_REL, TXT_BYTES, TXT_SHA)
    _pin(root / PDF_REL, PDF_BYTES, PDF_SHA)
    source_row = _source_map(root)
    pdf = PdfReader(root / PDF_REL)
    if len(pdf.pages) != 20:
        raise ValueError("PDF page count drift")
    pages = [page.extract_text() or "" for page in pdf.pages]
    for i, page in enumerate(pages, 1):
        if f"Page {i} of 20" not in page:
            raise ValueError(f"PDF page identity drift: {i}")
    lines = txt_raw.decode("utf-8").splitlines()
    bounds = _sections(lines)
    shapes = _parse_shapes(lines, pages, bounds)
    parsed = {"A1": _a1(lines, bounds["A1"], pages[2]), "A2": _a2(lines, bounds["A2"], pages[3], shapes), "B": _cells(lines, bounds["B"], pages, shapes, "B"), "C": _cells(lines, bounds["C"], pages, shapes, "C")}
    for module in ("D", "E", "F", "G"):
        parsed[module] = _grid_module(module, lines, bounds[module], pages, shapes)
    parsed["H"] = _h(lines, bounds["H"], pages[14], shapes)
    parsed["I"] = _grid_module("I", lines, bounds["I"], pages, shapes)
    parsed["J"] = _j(lines, bounds["J"], pages[17], shapes)
    modules = []
    for module, units in parsed.items():
        attacks = sum(len(x["attacks"]) for x in units)
        if attacks != MODULE_COUNTS[module] or len(units) != MODULE_UNITS[module]:
            raise ValueError(f"module {module} count/unit drift: {len(units)} {attacks}")
        start, stop = bounds[module]
        modules.append({"module": module, "unit_count": len(units), "printed_attack_count": attacks, "txt_start_line": start + 1, "txt_end_line": stop, "full_source_lines": lines[start:stop], "units": units})
    if sum(x["printed_attack_count"] for x in modules) != 780:
        raise ValueError("whole-workbook 780 attack count drift")
    txt = txt_raw.decode("utf-8")
    for phrase in ("COMPLETE NOTATED WORKLOAD: 780 pick or strum attacks", "CHORD-DIAGRAM LEGEND", "PRACTICE PROGRESSION AND ERROR REPAIR", "MASTERY GATE BEFORE LEVEL 50", "NEXT LEVEL"):
        if phrase not in txt:
            raise ValueError(f"TXT guidance drift: {phrase}")
    for phrase in ("One-minute change tests", "clean 20-change whole-note minute", "Add 2 BPM after three clean loops", "DAILY LIMIT"):
        if phrase not in pages[18]:
            raise ValueError(f"PDF-only test/advancement drift: {phrase}")
    if "Completion audit and practice log" not in pages[19]:
        raise ValueError("PDF mastery/log drift")
    return {
        "schema": "fathom.detached-source-candidate.1", "section": "VI", "level": 49, "wbs_id": "2.3.1.2.1",
        "source": {"txt_path": TXT_REL, "txt_bytes": TXT_BYTES, "txt_sha256": TXT_SHA, "pdf_path": PDF_REL, "pdf_bytes": PDF_BYTES, "pdf_sha256": PDF_SHA, "pdf_pages": 20, "source_map_path": MAP_REL, "source_map_bytes": MAP_BYTES, "source_map_sha256": MAP_SHA, "source_map_row": source_row},
        "chord_shapes": [shapes[name] for name in ALL_CHORDS], "modules": modules, "module_count": 11, "module_components": list(MODULE_COUNTS), "printed_attack_count": 780,
        "printed_guidance": {"kind": "printed_instruction", "txt_full_text": txt, "pdf_extracted_pages": [{"page": i + 1, "extracted_text": page} for i, page in enumerate(pages)], "reverse_a2_audit": "printed optional high-e-to-low-E pass; not added to the 48-attack core", "pdf_one_minute_tests": pages[18].split("One-minute change tests", 1)[1].split("ADVANCE", 1)[0], "pdf_advancement_and_fatigue": pages[18].split("ADVANCE", 1)[1]},
        "source_exceptions": [
            {"code": "PDF_ONLY_ONE_MINUTE_CHANGE_TESTS_AND_ADVANCEMENT", "status": "Pending Curriculum review", "source": "PDF p19", "decision": "Preserve tests, threshold, tempo rule and daily limit as printed instructions; do not infer completed transitions or increase the 780-attack core."},
            {"code": "A2_REVERSE_PASS_OUTSIDE_CORE_COUNT", "status": "Pending Curriculum review", "source": "TXT Module A2 and PDF p4", "printed_direction": "Repeat high e back to low E / repeat the audit with light upstrokes", "printed_core_count": "8 chords x 6 strings = 48 attacks", "decision": "Keep 48 primary A2 attacks in the 780-attack core; preserve the reverse pass as instruction without assuming it is an additional counted 48."},
        ],
        "music_row_exceptions": [], "canonical_ids": None, "review": "Pending", "runtime_eligible": False, "imported": False, "admitted": False,
        "performed_bpm": None, "performed_quality": None, "performed_mastery": None,
        "pending": ["Curriculum review of PDF-only one-minute test/advancement and A2 reverse-count ambiguity", "independent musical review", "canonical IDs and runtime admission", "performed mastery gate"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    candidate = build_candidate(args.root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(candidate, sort_keys=True, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"LEVEL49 CANDIDATE PASS components=11 attacks=780 output={args.output}")


if __name__ == "__main__":
    main()
