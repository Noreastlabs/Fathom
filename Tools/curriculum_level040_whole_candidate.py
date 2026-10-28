#!/usr/bin/env python3
"""Build a detached, source-linked whole-Level-40 F#-minor harmony candidate."""

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
TXT_REL = Path("Notes/music/guitar project/TXT version/Scale_Exercises_Section_V_Level_40_F_Sharp_Minor_Pentatonic_Harmony_and_Five_Position_Phrasing.txt")
PDF_REL = Path("Notes/music/guitar project/PDF version/Scale_Exercises_Section_V_Level_40_F_Sharp_Minor_Pentatonic_Harmony_and_Five_Position_Phrasing.pdf")
TXT_BYTES = 38564
TXT_SHA256 = "e9e4db6227e4d3ea0ccb15162ccde0c4da337b1dcf65b67a2401e1aab63a6da7"
PDF_BYTES = 45285
PDF_SHA256 = "99484a66ca087544322c922f75c037649ac21b80a355d117b9ad9c524cf76923"
BUILD_REL = Path("Build/parallel-09/2.3.1.1.1-level040-whole-r01")
STRINGS = ("e", "B", "G", "D", "A", "E")
OPEN_MIDI = {"E": 40, "A": 45, "D": 50, "G": 55, "B": 59, "e": 64}
PITCH_PC = {"F#": 6, "A": 9, "B": 11, "C#": 1, "E": 4, "D": 2, "G#": 8}
SCALE_DEGREE = {"F#": "1", "A": "b3", "B": "4", "C#": "5", "E": "b7", "D": "*", "G#": "*"}
ROLE = {
    "F#m": {"F#": "R", "A": "b3", "B": "4", "C#": "5", "E": "b7"},
    "A": {"F#": "13", "A": "R", "B": "9", "C#": "3", "E": "5"},
    "E": {"F#": "9", "A": "11", "B": "5", "C#": "13", "E": "R", "G#": "3"},
    "D": {"F#": "3", "A": "5", "B": "13", "C#": "M7", "E": "9", "D": "R"},
}
POSITION_SPANS = ((4, 7), (6, 10), (9, 12), (11, 14), (14, 17))
A_STARTS = ((44, 58, 72, 86), (102, 116, 130, 144), (160, 174, 188, 202),
            (218, 232, 246, 260), (276, 290, 304, 318))
C_STARTS = (371, 385, 399, 413, 427)
D_STARTS = (446, 459, 472, 485, 498)
E_STARTS = (521, 536, 551, 566, 581)
G_STARTS = (618, 632, 646)
A_CHORDS = ("F#m", "A", "E", "D")
CONTACT_RE = re.compile(r"(F#|C#|G#|A|B|E|D)\(([EADGBe])(\d+)\)")


class CandidateError(ValueError):
    """Pinned input, printed musical structure, or output boundary failed."""


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


def _row(row: str, label: str, groups: int, slots: int) -> list[list[str | None]]:
    prefix = "  " + label if label in STRINGS else label
    parts = row.split("|")
    if len(parts) != groups + 2 or parts[0] != prefix or parts[-1] != "":
        raise CandidateError(f"ROW_SHAPE_INVALID {label}")
    result = []
    for part in parts[1:-1]:
        if len(part) != slots * 4:
            raise CandidateError(f"ROW_WIDTH_INVALID {label}")
        tokens = []
        for i in range(0, len(part), 4):
            cell = part[i:i+4]
            if cell == "----":
                tokens.append(None)
                continue
            token = cell.rstrip("-")
            if not token or token + "-" * (4-len(token)) != cell:
                raise CandidateError(f"ROW_SLOT_INVALID {label}: {cell}")
            tokens.append(token)
        result.append(tokens)
    return result


def _grid(rows: list[str], groups: int, slots: int, *, chord: str | None, has_chd: bool,
          has_out: bool, context: str) -> list[list[dict[str, Any]]]:
    labels = ["Nte", "F#m"] + (["Chd"] if has_chd else []) + ["Job"] + (["Out"] if has_out else []) + ["Fng", *STRINGS]
    if len(rows) != len(labels):
        raise CandidateError(f"GRID_ROW_COUNT {context}")
    parsed = {label: _row(row, label, groups, slots) for label, row in zip(labels, rows, strict=True)}
    result = []
    for g in range(groups):
        events = []
        for i in range(slots):
            name = parsed["Nte"][g][i]
            degree = parsed["F#m"][g][i]
            finger = parsed["Fng"][g][i]
            active = parsed["Chd"][g][i] if has_chd else chord
            job = parsed["Job"][g][i]
            out = parsed["Out"][g][i] if has_out else None
            if name not in PITCH_PC or degree != SCALE_DEGREE[name] or finger not in ("1", "2", "3", "4"):
                raise CandidateError(f"NOTE_DEG_FINGER_MISMATCH {context} {g+1} {i+1}")
            if active not in ROLE or name not in ROLE[active] or job != ROLE[active][name]:
                raise CandidateError(f"CHORD_ROLE_MISMATCH {context} {g+1} {i+1}: {name}/{active}/{job}")
            if has_out and out != ("*" if name in ("D", "G#") else None):
                raise CandidateError(f"OUTSIDE_MARKER_MISMATCH {context} {g+1} {i+1}")
            printed = [(s, parsed[s][g][i]) for s in STRINGS if parsed[s][g][i] is not None]
            if len(printed) != 1 or not printed[0][1].isdigit():
                raise CandidateError(f"TAB_NOTE_CARDINALITY {context} {g+1} {i+1}")
            string, fret = printed[0][0], int(printed[0][1])
            if (OPEN_MIDI[string] + fret) % 12 != PITCH_PC[name]:
                raise CandidateError(f"TAB_PITCH_MISMATCH {context} {g+1} {i+1}")
            events.append({"ordinal": g*slots+i+1, "group": g+1, "slot": i+1, "note_name": name,
                           "minor_pentatonic_degree": degree, "chord": active, "chord_role": job,
                           "outside_pentatonic": name in ("D", "G#"), "printed_out": out,
                           "finger_digit": int(finger), "string": string, "fret": fret,
                           "onset_q": None, "duration_q": None})
        result.append(events)
    return result


def _contacts(text: str, count: int, context: str) -> list[dict[str, Any]]:
    matches = list(CONTACT_RE.finditer(text))
    if len(matches) != count or ", ".join(m.group(0) for m in matches) != text:
        raise CandidateError(f"TARGET_CONTACT_SHAPE {context}")
    result = []
    for m in matches:
        name, string, fret = m.group(1), m.group(2), int(m.group(3))
        if (OPEN_MIDI[string] + fret) % 12 != PITCH_PC[name]:
            raise CandidateError(f"TARGET_CONTACT_PITCH {context}")
        result.append({"note_name": name, "string": string, "fret": fret})
    return result


def _txt(data: bytes) -> dict[str, Any]:
    try:
        lines = data.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise CandidateError("TXT_ENCODING_INVALID") from exc
    if len(lines) != 695 or lines[:3] != ["SCALE EXERCISES - SECTION V, LEVEL 40",
                                          "F# MINOR PENTATONIC HARMONY AND FIVE-POSITION PHRASING",
                                          "FIXED NOTES: F# A B C# E | HARMONY: F#m A E D"]:
        raise CandidateError("TXT_DOCUMENT_BOUNDARY")
    if lines[8:11] != ["F# MINOR PENTATONIC", "Notes: F# A B C# E", "Degrees: 1 b3 4 5 b7"]:
        raise CandidateError("TXT_FIXED_POOL_MISMATCH")
    expected_harmony = ("F# minor = F# A C#", "A major = A C# E", "E major = E G# B", "D major = D F# A")
    if not all(any(line.startswith(x) for line in lines[12:19]) for x in expected_harmony):
        raise CandidateError("TXT_HARMONY_MISMATCH")
    matrix_lines = lines[18:25]
    if matrix_lines != ["CHORD-ROLE MATRIX", "Pitch | Over F#m | Over A | Over E | Over D",
                        "F#    | R        | 13     | 9      | 3",
                        "A     | b3       | R      | 11     | 5",
                        "B     | 4        | 9      | 5      | 13",
                        "C#    | 5        | 3      | 13     | M7",
                        "E     | b7       | 5      | R      | 9"]:
        raise CandidateError("TXT_ROLE_MATRIX_MISMATCH")
    counts = (240, 60, 80, 60, 60, 32, 48)
    if not all(str(n) + " notes" in lines[27+i] if i != 1 else "60 held tones" in lines[27+i]
               for i, n in enumerate(counts)) or lines[34] != "Complete written workout: 580 sounding tones.":
        raise CandidateError("TXT_MODULE_COUNTS_MISMATCH")
    a = []
    for p, starts in enumerate(A_STARTS, 1):
        span = POSITION_SPANS[p-1]
        if not lines[starts[0]-3].startswith(f"P{p} - ") or f"FRETS {span[0]}-{span[1]}" not in lines[starts[0]-3]:
            raise CandidateError(f"TXT_POSITION_HEADER_MISMATCH P{p}")
        for chord, number in zip(A_CHORDS, starts, strict=True):
            i = number-1
            m = re.fullmatch(r"(F#m|A|E|D) - (\d+)-NOTE TARGET CELL", lines[i])
            if not m or m.group(1) != chord:
                raise CandidateError(f"TXT_A_HEADER_MISMATCH P{p} {chord}")
            n = int(m.group(2))
            if n % 2 or n not in (8, 10, 12, 14, 16) or not lines[i+1].startswith("Targets: "):
                raise CandidateError(f"TXT_A_TARGET_COUNT P{p} {chord}")
            contacts = _contacts(lines[i+1][9:], n//2, f"A-P{p}-{chord}")
            rows = lines[i+2:i+12]
            groups = _grid(rows, 2, n//2, chord=chord, has_chd=False, has_out=False, context=f"A-P{p}-{chord}")
            ascent = groups[0]
            descent = groups[1]
            if [{"note_name": e["note_name"], "string": e["string"], "fret": e["fret"]} for e in ascent] != contacts:
                raise CandidateError(f"A_TARGET_CONTACT_MISMATCH P{p} {chord}")
            if [(e["note_name"],e["string"],e["fret"]) for e in descent] != list(reversed([(e["note_name"],e["string"],e["fret"]) for e in ascent])):
                raise CandidateError(f"A_TURN_MISMATCH P{p} {chord}")
            if not lines[i+12].startswith("Rule: "):
                raise CandidateError(f"A_RULE_MISSING P{p} {chord}")
            a.append({"position": p, "position_heading": lines[starts[0]-3], "frame_span": list(span),
                      "chord": chord, "note_count": n, "targets": contacts,
                      "printed_target_text": lines[i+1], "printed_rows": rows, "groups": groups,
                      "rule_text": lines[i+12], "txt_ref": f"L40-TXT1-{number}-{number+12}"})
    if sum(x["note_count"] for x in a) != 240:
        raise CandidateError("A_TOTAL_MISMATCH")
    b = []
    for p in range(1, 6):
        start = 337 + (p-1)*5
        span = POSITION_SPANS[p-1]
        if lines[start-1] != f"P{p} - FRETS {span[0]}-{span[1]}":
            raise CandidateError(f"B_POSITION_HEADER P{p}")
        for j, route in enumerate(("root", "common", "fifth")):
            line = lines[start+j]
            if not line.startswith(("ROOT ROUTE:   ", "COMMON ROUTE: ", "FIFTH ROUTE:  ")[j]):
                raise CandidateError(f"B_ROUTE_HEADER P{p} {route}")
            content = line.partition(":")[2].strip()
            parts = content.split(" -> ")
            if len(parts) != 4:
                raise CandidateError(f"B_ROUTE_COUNT P{p} {route}")
            contacts = [_contacts(x, 1, f"B-P{p}-{route}")[0] for x in parts]
            if [x["note_name"] for x in contacts] != ({"root": ["F#", "A", "E", "F#"],
                                                        "common": ["A", "A", "B", "A"],
                                                        "fifth": ["C#", "C#", "B", "C#"]}[route]):
                raise CandidateError(f"B_ROUTE_NOTES P{p} {route}")
            for target, active in zip(contacts, ("F#m", "A", "E", "F#m"), strict=True):
                target["chord"] = active
                target["chord_role"] = ROLE[active][target["note_name"]]
                target["onset_q"] = None
                target["duration_q"] = None
            b.append({"position": p, "frame_span": list(span), "route": route, "printed": line, "held_targets": contacts,
                      "txt_ref": f"L40-TXT1-{start+j+1}"})
    if len(b)*4 != 60:
        raise CandidateError("B_TOTAL_MISMATCH")
    if not all(x in "\n".join(lines[361:365]) for x in ("F#-E-F#-E", "C#-C#-B-F#")):
        raise CandidateError("B_TRANSFER_ROUTES_MISMATCH")
    def multi(starts: tuple[int, ...], module: str, group_count: int, slots: int,
              *, has_out: bool = False) -> list[dict[str, Any]]:
        records = []
        for idx, number in enumerate(starts, 1):
            i = number-1
            expected_prefix = f"P{idx} - "
            if not lines[i].startswith(expected_prefix):
                raise CandidateError(f"{module}_HEADER P{idx}")
            row_count = 12 if has_out else 11
            rows = lines[i+1:i+1+row_count]
            groups = _grid(rows, group_count, slots, chord=None, has_chd=True, has_out=has_out,
                           context=f"{module}-P{idx}")
            records.append({"position": idx, "frame_span": list(POSITION_SPANS[idx-1]),
                            "printed_heading": lines[i], "printed_rows": rows,
                            "groups": groups, "txt_ref": f"L40-TXT1-{number}-{number+row_count}"})
        return records
    c = multi(C_STARTS, "C", 4, 4)
    d = multi(D_STARTS, "D", 2, 6)
    e = multi(E_STARTS, "E", 3, 4, has_out=True)
    for item, number in zip(c, C_STARTS, strict=True):
        item["articulation_task_text"] = lines[number+11]
        if item["articulation_task_text"] != "First pass: all notes picked. Second pass: add one articulation per bar without moving the beat-1 target.":
            raise CandidateError(f"C_ARTICULATION_TASK P{item['position']}")
    for item, number in zip(e, E_STARTS, strict=True):
        item["cadence_task_text"] = lines[number+12]
        if item["cadence_task_text"] != "Beat 1 states D, G#, and F# in sequence. Return immediately to the established pitch pool after the completion tone.":
            raise CandidateError(f"E_CADENCE_TASK P{item['position']}")
    for cell in c:
        if [g[0]["chord"] for g in cell["groups"]] != ["F#m", "A", "E", "F#m"] or cell["groups"][-1][-1]["note_name"] != "F#":
            raise CandidateError(f"C_PHRASE_ROUTE P{cell['position']}")
    for cell in d:
        if [g[0]["chord"] for g in cell["groups"]] != ["A", "F#m"] or cell["groups"][0][-1]["note_name"] != "A" or cell["groups"][1][-1]["note_name"] != "F#":
            raise CandidateError(f"D_RESPONSE_ROUTE P{cell['position']}")
        if [(x["note_name"],x["degree"] if "degree" in x else x["minor_pentatonic_degree"]) for x in cell["groups"][0][:4]] != [(x["note_name"],x["minor_pentatonic_degree"]) for x in cell["groups"][1][:4]]:
            raise CandidateError(f"D_SHARED_OPENING P{cell['position']}")
    for cell in e:
        if [g[0]["chord"] for g in cell["groups"]] != ["D", "E", "F#m"] or [g[0]["note_name"] for g in cell["groups"]] != ["D", "G#", "F#"]:
            raise CandidateError(f"E_COMPLETION_ROUTE P{cell['position']}")
        if sum(x["outside_pentatonic"] for g in cell["groups"] for x in g) != 2:
            raise CandidateError(f"E_OUTSIDE_COUNT P{cell['position']}")
    if not all(x in "\n".join(lines[513:520]) for x in ("not F#-minor-pentatonic degrees", "P1: D root", "P5: D root")):
        raise CandidateError("E_COMPLETION_CONTACT_MAP")
    f_rows = lines[600:611]
    f_groups = _grid(f_rows, 8, 4, chord=None, has_chd=True, has_out=False, context="F")
    if [g[0]["chord"] for g in f_groups] != ["A", "E", "D", "A", "F#m", "A", "E", "F#m"]:
        raise CandidateError("F_EIGHT_BAR_ROUTE")
    f = {"printed_progression": lines[598], "printed_rows": f_rows, "groups": f_groups,
         "txt_ref": "L40-TXT1-599-611", "center_shift_text": lines[599]}
    g = []
    for model, number in enumerate(G_STARTS, 1):
        i = number-1
        if not lines[i].startswith(f"MODEL {model} - "):
            raise CandidateError(f"G_MODEL_HEADER {model}")
        rows = lines[i+1:i+12]
        groups = _grid(rows, 4, 4, chord=None, has_chd=True, has_out=False, context=f"G{model}")
        g.append({"model": model, "printed_heading": lines[i], "printed_rows": rows, "groups": groups,
                  "ending_guidance": lines[i+12], "txt_ref": f"L40-TXT1-{number}-{number+12}"})
    totals = {"A": sum(x["note_count"] for x in a), "B": len(b)*4,
              "C": sum(len(g) for x in c for g in x["groups"]),
              "D": sum(len(g) for x in d for g in x["groups"]),
              "E": sum(len(g) for x in e for g in x["groups"]),
              "F": sum(len(g) for g in f_groups), "G": sum(len(gr) for x in g for gr in x["groups"])}
    if totals != dict(zip("ABCDEFG", (240, 60, 80, 60, 60, 32, 48), strict=True)):
        raise CandidateError(f"MODULE_TOTAL_MISMATCH {totals}")
    guidance = {"intro_ref": "L40-TXT1-1-37", "intro_text": "\n".join(lines[:37]),
                "module_b_task_ref": "L40-TXT1-333-336", "module_b_task_text": "\n".join(lines[332:336]),
                "module_b_transfer_ref": "L40-TXT1-361-365", "module_b_transfer_text": "\n".join(lines[360:365]),
                "module_c_ref": "L40-TXT1-367-370", "module_c_text": "\n".join(lines[366:370]),
                "module_d_ref": "L40-TXT1-442-445", "module_d_text": "\n".join(lines[441:445]),
                "module_e_ref": "L40-TXT1-512-520", "module_e_text": "\n".join(lines[511:520]),
                "module_f_ref": "L40-TXT1-597-600", "module_f_text": "\n".join(lines[596:600]),
                "module_g_ref": "L40-TXT1-614-617", "module_g_text": "\n".join(lines[613:617]),
                "practice_mastery_ref": "L40-TXT1-661-695", "practice_mastery_text": "\n".join(lines[660:695])}
    return {"A": a, "B": b, "C": c, "D": d, "E": e, "F": f, "G": g,
            "totals": totals, "guidance": guidance, "lines": lines}


def _find_grid(page: list[str], rows: list[str], context: str) -> None:
    if not any(page[i:i+len(rows)] == rows for i in range(len(page)-len(rows)+1)):
        raise CandidateError(f"PDF_TXT_GRID_MISMATCH {context}")


def _pdf(data: bytes, txt: dict[str, Any]) -> dict[str, Any]:
    try:
        reader = PdfReader(BytesIO(data), strict=True)
        if len(reader.pages) != 16:
            raise CandidateError(f"PDF_PAGE_COUNT {len(reader.pages)}")
        pages = [(p.extract_text() or "").splitlines() for p in reader.pages]
    except CandidateError:
        raise
    except Exception as exc:
        raise CandidateError(f"PDF_READ_FAILED {type(exc).__name__}") from exc
    if pages[0][:3] != ["Scale Exercises - Section V, Level 40", "F# minor pentatonic harmony and five-position phrasing",
                       "F#m | A | E | D  -  SAME FIVE NOTES, NEW HARMONIC JOBS"] or "580 sounding tones" not in "\n".join(pages[0]):
        raise CandidateError("PDF_INTRO_MISMATCH")
    atlas = pages[1]
    if atlas[:3] != ["Level 40 - Chord Roles and Target Atlas", "The same pitch changes function whenever the harmony changes.",
                     "F# MINOR PENTATONIC: 1 b3 4 5 b7"]:
        raise CandidateError("PDF_ATLAS_HEADER_MISMATCH")
    role_rows = atlas[8:33]
    pdf_roles = {"F#": ("root", "13 / 6", "9", "third"), "A": ("b3", "root", "11 / sus4", "fifth"),
                 "B": ("4 / 11", "9", "fifth", "13 / 6"), "C#": ("fifth", "third", "13 / 6", "major 7 tension"),
                 "E": ("b7", "fifth", "root", "9")}
    if role_rows != [value for note, vals in pdf_roles.items() for value in (note, *vals)]:
        raise CandidateError("PDF_ROLE_MATRIX_MISMATCH")
    atlas_targets = " ".join(atlas[38:70])
    for item in txt["A"]:
        if item["printed_target_text"][9:] not in atlas_targets:
            raise CandidateError(f"PDF_ATLAS_TARGET_MISMATCH P{item['position']} {item['chord']}")
        page_no = item["position"]+2
        page = pages[page_no-1]
        if page[0] != f"Level 40 - Module A: P{item['position']} Chord-Target Cells":
            raise CandidateError(f"PDF_A_PAGE_MISMATCH P{item['position']}")
        _find_grid(page, item["printed_rows"], f"A-P{item['position']}-{item['chord']}")
    voice = pages[7]
    if voice[:3] != ["Level 40 - Module B: Voice-Leading Routes",
                     "First sustain one whole note per bar; then add pickups without moving the printed beat-1 landing.",
                     "| F#m | A | E | F#m |  -  3 ROUTES x 5 POSITIONS = 60 HELD TONES"]:
        raise CandidateError("PDF_B_HEADER_MISMATCH")
    for item in txt["B"]:
        text = item["printed"].partition(":")[2].strip()
        if text not in voice:
            raise CandidateError(f"PDF_B_ROUTE_MISMATCH P{item['position']} {item['route']}")
    if not all(x in "\n".join(voice) for x in ("F# - E - F# - E", "C# - C# - B - F#", "two eighth-note pickups")):
        raise CandidateError("PDF_B_TRANSFER_MISMATCH")
    for item in txt["C"]:
        _find_grid(pages[8 if item["position"]<=3 else 9], item["printed_rows"], f"C-P{item['position']}")
    for item in txt["D"]:
        _find_grid(pages[10], item["printed_rows"], f"D-P{item['position']}")
    completion = pages[11]
    if completion[:3] != ["Level 40 - Module E: Completion-Tone Map",
                          "D completes D major; G# completes E major. Both are marked outside the five-note pentatonic pool.",
                          "OUTSIDE NOTE = *  |  USE ONLY WHEN THE CHORD REQUIRES IT"]:
        raise CandidateError("PDF_E_COMPLETION_MAP_MISMATCH")
    for p in range(1, 6):
        printed = txt["lines"][514+p-1]
        match = re.fullmatch(r"P\d: D root at ([EADGBe]\d+) finger (\d); G# third at ([EADGBe]\d+) finger (\d)\.", printed)
        if not match or f"D({match.group(1)}) finger {match.group(2)}" not in completion or f"G#({match.group(3)}) finger {match.group(4)}" not in completion:
            raise CandidateError(f"PDF_E_POSITION_CONTACT_MISMATCH P{p}")
    for item in txt["E"]:
        _find_grid(pages[11 if item["position"]<=2 else 12], item["printed_rows"], f"E-P{item['position']}")
    fpage = pages[13]
    if fpage[:3] != ["Level 40 - Module F: Eight-Bar Center Shift",
                     "Bars 1-4 establish A major; bars 5-8 re-center the same pitch pool around F# minor.",
                     "| A | E | D | A |  ->  | F#m | A | E | F#m |"]:
        raise CandidateError("PDF_F_HEADER_MISMATCH")
    for row in txt["F"]["printed_rows"]:
        label, rest = row.split("|",1)
        pdf_rows = [x for x in fpage if x.startswith(label+"|")]
        if len(pdf_rows) != 2 or pdf_rows[0]+pdf_rows[1].split("|",1)[1] != row:
            raise CandidateError(f"PDF_TXT_GRID_MISMATCH F-{label}")
    for item in txt["G"]:
        _find_grid(pages[14], item["printed_rows"], f"G{item['model']}")
    practice = pages[15]
    if practice[:3] != ["Level 40 - Practice, Mastery Gate, and Log",
                        "Harmony accuracy comes before speed, density, or articulation.",
                        "NEXT: LEVEL 41 - A MINOR PENTATONIC FIVE-POSITION MAP"] or "twenty Module A target cells" not in "\n".join(practice):
        raise CandidateError("PDF_PRACTICE_MASTERY_MISMATCH")
    return {"intro_ref": "L40-PDF1-p1", "atlas_ref": "L40-PDF1-p2", "role_matrix_text": "\n".join(atlas[3:33]),
            "target_atlas_text": "\n".join(atlas[33:70]), "module_b_ref": "L40-PDF1-p8",
            "module_b_transfer_text": "\n".join(voice[28:49]), "module_f_ref": "L40-PDF1-p14",
            "module_f_center_text": "\n".join(fpage[30:36]), "practice_ref": "L40-PDF1-p16",
            "practice_text": "\n".join(practice[3:36])}


def build_candidate(*, txt_data: bytes | None = None, pdf_data: bytes | None = None) -> dict[str, Any]:
    root = _root()
    txt_data = _source_bytes(root, TXT_REL) if txt_data is None else txt_data
    pdf_data = _source_bytes(root, PDF_REL) if pdf_data is None else pdf_data
    _verify(txt_data, TXT_BYTES, TXT_SHA256, "L40-TXT")
    _verify(pdf_data, PDF_BYTES, PDF_SHA256, "L40-PDF")
    parsed = _txt(txt_data)
    pdf = _pdf(pdf_data, parsed)
    del parsed["lines"]
    for item in parsed["A"]:
        item["source_refs"] = {"txt": item.pop("txt_ref"), "pdf_card": f"L40-PDF1-p{item['position']+2}", "pdf_atlas": "L40-PDF1-p2"}
    for item in parsed["B"]:
        item["source_refs"] = {"txt": item.pop("txt_ref"), "pdf": "L40-PDF1-p8"}
    for key in "CDE":
        for item in parsed[key]:
            p = item["position"]
            page = {"C": 9 if p<=3 else 10, "D": 11, "E": 12 if p<=2 else 13}[key]
            item["source_refs"] = {"txt": item.pop("txt_ref"), "pdf": f"L40-PDF1-p{page}"}
    parsed["F"]["source_refs"] = {"txt": parsed["F"].pop("txt_ref"), "pdf": "L40-PDF1-p14"}
    for item in parsed["G"]:
        item["source_refs"] = {"txt": item.pop("txt_ref"), "pdf": "L40-PDF1-p15"}
    return {"schema": "fathom-level040-whole-detached-candidate-v1", "wbs_id": "2.3.1.1.1", "level": 40,
            "source": {"txt_path": TXT_REL.as_posix(), "txt_bytes": TXT_BYTES, "txt_sha256": TXT_SHA256,
                       "pdf_path": PDF_REL.as_posix(), "pdf_bytes": PDF_BYTES, "pdf_sha256": PDF_SHA256, "pdf_pages": 16},
            "fixed_pool": ["F#", "A", "B", "C#", "E"], "fixed_degrees": ["1", "b3", "4", "5", "b7"],
            "harmony": {"F#m": ["F#", "A", "C#"], "A": ["A", "C#", "E"],
                        "E": ["E", "G#", "B"], "D": ["D", "F#", "A"]},
            "chord_role_matrix": ROLE, "modules": {key: parsed[key] for key in "ABCDEFG"},
            "module_note_counts": parsed["totals"], "complete_workout_sounding_tones": 580,
            "instructions": parsed["guidance"], "pdf_guidance": pdf, "source_discrepancies": [],
            "whole_source_batch_structurally_reconciled": True,
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
    return {"output": str(target.relative_to(root)), "bytes": len(data), "sha256": digest(data), "modules": 7}


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
