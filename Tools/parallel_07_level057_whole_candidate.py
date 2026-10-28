#!/usr/bin/env python3
"""Build the detached, source-linked whole Level 57 seventh-chord candidate."""

from __future__ import annotations

import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path
import re
import subprocess
from typing import Any

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
STEM = "Guitar_Exercises_Section_VI_Level_57_Seventh_Chords_Shell_Voicings_Major_and_Minor_ii_V_I_and_Functional_Voice_Leading"
TXT_REL = Path("Notes/music/guitar project/TXT version") / (STEM + ".txt")
PDF_REL = Path("Notes/music/guitar project/PDF version") / (STEM + ".pdf")
BUILD_REL = Path("Build/parallel-07/2.3.1.2.1-level057-whole-r01")
TXT_BYTES = 29126
TXT_SHA256 = "f8c4090f825373861e07c506a44d1f8ef486161700d96896181f9785a9086545"
PDF_BYTES = 56585
PDF_SHA256 = "ddf35a3cd2a0506446c209b81aa31e9206439f0ff6a06675fef5b4f7f8c991fd"
STRINGS = ("E", "A", "D", "G", "B", "e")
OPEN_MIDI = {"E": 40, "A": 45, "D": 50, "G": 55, "B": 59, "e": 64}
PC = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3,
      "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8,
      "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11, "Cb": 11}
QUALITY_SUFFIXES = ("maj7", "m7b5", "m7", "7")
FORMULAS = {"maj7": {"R": 0, "3": 4, "5": 7, "7": 11},
            "7": {"R": 0, "3": 4, "5": 7, "b7": 10},
            "m7": {"R": 0, "b3": 3, "5": 7, "b7": 10},
            "m7b5": {"R": 0, "b3": 3, "b5": 6, "b7": 10}}
SHAPE_HEAD = re.compile(r"^([A-G](?:#|b)?(?:maj7|m7b5|m7|7)): ([0-9x ]+) \| spelling ([A-G#b-]+) \| fingering ([0-9x ]+)$")
CADENCE_HEAD = re.compile(r"^([A-G](?:#|b)?) (major|minor): ([A-G](?:#|b)?(?:maj7|m7b5|m7|7)) -> ([A-G](?:#|b)?(?:maj7|m7b5|m7|7)) -> ([A-G](?:#|b)?(?:maj7|m7b5|m7|7))$")
ARP_HEAD = re.compile(r"^([A-G](?:#|b)?(?:maj7|m7b5|m7|7)) - (E-root|A-root)$")
CHORD_TOKEN = re.compile(r"[A-G](?:#|b)?(?:maj7|m7b5|m7|7)")
EXPECTED_COUNTS = {"B_E_root_families": 112, "C_A_root_families": 112,
                   "D_quality_ladders": 56, "E_major_cadences": 108,
                   "F_minor_cadences": 108, "G_A_blues": 108,
                   "H_arpeggio_scans": 64, "I_capstones": 128}
BLUES_FORM = ("A7", "A7", "A7", "A7", "D7", "D7", "A7", "A7", "E7", "D7", "A7", "E7")


class CandidateError(ValueError):
    """Pinned source, printed contact, count, or output boundary failed."""


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


def _chord(chord: str) -> tuple[str, str]:
    for suffix in QUALITY_SUFFIXES:
        if chord.endswith(suffix):
            root = chord.removesuffix(suffix)
            if root in PC:
                return root, suffix
    raise CandidateError(f"CHORD_NAME_INVALID {chord}")


def _voicing_tokens(text: str) -> list[int | None]:
    tokens = text.split()
    if len(tokens) != 6 or any(re.fullmatch(r"x|\d+", token) is None for token in tokens):
        raise CandidateError(f"VOICING_TOKENS_INVALID {text}")
    return [None if token == "x" else int(token) for token in tokens]


def _staff_tokens(line: str, prefix: str) -> list[str]:
    if not line.startswith(prefix + "|") or not line.endswith("|"):
        raise CandidateError(f"STAFF_LINE_INVALID {prefix}")
    tokens = line[len(prefix) + 1:-1].split()
    if len(tokens) != 6:
        raise CandidateError(f"STAFF_TOKEN_COUNT_INVALID {prefix}")
    return tokens


def _attack(chord: str, *, kind: str, contacts: list[dict[str, Any]],
            sounded: bool = True, string: str | None = None, role: str | None = None,
            note: str | None = None) -> dict[str, Any]:
    return {"chord": chord, "kind": kind, "contacts": contacts,
            "string": string, "role": role, "note": note, "sounded": sounded,
            "onset_q": None, "duration_q": None}


def _shape_families(lines: list[str], pages: list[list[str]]) -> tuple[list[dict[str, Any]], dict[tuple[str, str], dict[str, Any]]]:
    first = lines.index("MODULES B-C - E-ROOT AND A-ROOT FAMILIES")
    last = lines.index("MODULE D - SHELL VOICINGS AND QUALITY LADDERS")
    families = []
    lookup: dict[tuple[str, str], dict[str, Any]] = {}
    root_maps = {"E": [("F", 1), ("G", 3), ("A", 5), ("B", 7), ("C", 8), ("D", 10), ("E", 12)],
                 "A": [("B", 2), ("C", 3), ("D", 5), ("E", 7), ("F", 8), ("G", 10), ("A", 12)]}
    for index in range(first, last):
        line = lines[index]
        family_match = re.fullmatch(r"([EA])-ROOT (MAJOR 7|DOMINANT 7|MINOR 7|MINOR 7 FLAT 5 / HALF-DIMINISHED) FAMILY - (.+)", line)
        if family_match is None:
            continue
        root_string = family_match.group(1)
        quality = {"MAJOR 7": "maj7", "DOMINANT 7": "7", "MINOR 7": "m7",
                   "MINOR 7 FLAT 5 / HALF-DIMINISHED": "m7b5"}[family_match.group(2)]
        if family_match.group(3).split("-") != {
                "maj7": ["1", "3", "5", "7"], "7": ["1", "3", "5", "b7"],
                "m7": ["1", "b3", "5", "b7"], "m7b5": ["1", "b3", "b5", "b7"]}[quality]:
            raise CandidateError(f"FAMILY_FORMULA_INVALID {root_string} {quality}")
        page_number = {("E", "maj7"): 3, ("E", "7"): 3, ("E", "m7"): 4,
                       ("E", "m7b5"): 4, ("A", "maj7"): 5, ("A", "7"): 5,
                       ("A", "m7"): 6, ("A", "m7b5"): 6}[(root_string, quality)]
        page = pages[page_number - 1]
        family = {"root_string": root_string, "quality": quality, "shapes": [],
                  "source_ref": f"L57-TXT1-{index + 1}", "pdf_page": page_number}
        for root_name, root_fret in root_maps[root_string]:
            chord = root_name + quality
            matching = [(j, m) for j in range(index + 1, min(index + 44, last))
                        if (m := SHAPE_HEAD.fullmatch(lines[j])) and m.group(1) == chord]
            if len(matching) != 1:
                raise CandidateError(f"FAMILY_SHAPE_MISSING {root_string} {chord}")
            j, match = matching[0]
            assert match is not None
            frets = _voicing_tokens(match.group(2))
            spellings = match.group(3).split("-")
            fingers = match.group(4).split()
            if (len(spellings) != 4 or len(fingers) != 6 or
                any((fret is None) != (finger == "x") for fret, finger in zip(frets, fingers, strict=True))):
                raise CandidateError(f"SHAPE_HEADER_INVALID {chord}")
            rows = lines[j + 1:j + 5]
            if rows[0] != "Str|E---A---D---G---B---e---|" or len(rows) != 4:
                raise CandidateError(f"SHAPE_STAFF_LAYOUT_INVALID {chord}")
            staff_frets = _staff_tokens(rows[1], "Fre")
            notes = _staff_tokens(rows[2], "Nte")
            roles = _staff_tokens(rows[3], "Rol")
            if staff_frets != ["x" if fret is None else str(fret) for fret in frets]:
                raise CandidateError(f"SHAPE_FRET_ROW_MISMATCH {chord}")
            if (sum(note != "x" for note in notes) != 4 or
                sorted(PC[n] for n in spellings) != sorted(PC[n] for n in notes if n != "x")):
                raise CandidateError(f"SHAPE_SPELLING_MISMATCH {chord}")
            contacts = []
            for string, fret, note, role in zip(STRINGS, frets, notes, roles, strict=True):
                if fret is None:
                    if note != "x" or role != "x":
                        raise CandidateError(f"MUTED_STRING_ROLE_INVALID {chord}")
                    continue
                if (OPEN_MIDI[string] + fret) % 12 != PC[note] or (
                        PC[root_name] + FORMULAS[quality].get(role, 99)) % 12 != PC[note]:
                    raise CandidateError(f"SHAPE_PITCH_OR_ROLE_INVALID {chord} {string}")
                contacts.append({"string": string, "fret": fret, "note": note, "role": role})
            root_contact = contacts[0]
            if root_contact["string"] != root_string or root_contact["fret"] != root_fret or root_contact["role"] != "R":
                raise CandidateError(f"SHAPE_ROOT_MAP_INVALID {chord}")
            if lines[j + 5] != "Exercise: four quarter-note attacks; release before moving to the next root.":
                raise CandidateError(f"SHAPE_ATTACK_RULE_MISSING {chord}")
            pdf_shape = " ".join("x" if f is None else str(f) for f in frets)
            pdf_spelling = "-".join(spellings)
            pdf_fingers = " ".join(fingers)
            sequence = [chord, pdf_shape, pdf_spelling, pdf_fingers]
            if not any(page[k:k + 4] == sequence for k in range(len(page) - 3)):
                raise CandidateError(f"PDF_SHAPE_TABLE_MISMATCH {chord} {root_string}")
            shape = {"chord": chord, "root": root_name, "quality": quality,
                     "root_string": root_string, "frets_e_a_d_g_b_e": frets,
                     "fingers_e_a_d_g_b_e": fingers, "spelling": spellings,
                     "contacts": contacts, "excluded_strings": [s for s, f in zip(STRINGS, frets, strict=True) if f is None],
                     "attack_count": 4, "attacks": [_attack(chord, kind="blocked", contacts=contacts) for _ in range(4)],
                     "silent_formation_before_first_attack": True,
                     "raw_lines": lines[j:j + 6], "source_ref": f"L57-TXT1-{j + 1}-{j + 6}",
                     "pdf_page": page_number}
            family["shapes"].append(shape)
            lookup[(root_string, chord)] = shape
        families.append(family)
    if (len(families) != 8 or len(lookup) != 56 or
        any(len(family["shapes"]) != 7 for family in families)):
        raise CandidateError("FAMILY_SHAPE_COUNT_INVALID")
    return families, lookup


def _contact(string: str, fret: int, chord: str, role: str | None = None) -> dict[str, Any]:
    root, quality = _chord(chord)
    pc = (OPEN_MIDI[string] + fret) % 12
    if role is not None and (PC[root] + FORMULAS[quality][role]) % 12 != pc:
        raise CandidateError(f"CONTACT_ROLE_INVALID {chord} {string}{fret} {role}")
    return {"string": string, "fret": fret, "pitch_class": pc, "role": role}


def _full_half_dim_check(chord: str, frets: list[int | None]) -> None:
    root, quality = _chord(chord)
    if quality != "m7b5" or frets[1] is None:
        raise CandidateError(f"FULL_HALF_DIM_INVALID {chord}")
    r = frets[1]
    if frets != [None, r, r + 1, r, r + 1, None]:
        raise CandidateError(f"FULL_HALF_DIM_FRETS_INVALID {chord}")
    for string, fret, role in (("A", r, "R"), ("D", r + 1, "b5"),
                               ("G", r, "b7"), ("B", r + 1, "b3")):
        _contact(string, fret, chord, role)


def _shell_and_ladders(lines: list[str], pages: list[list[str]], lookup: dict[tuple[str, str], dict[str, Any]]) -> dict[str, Any]:
    start = lines.index("MODULE D - SHELL VOICINGS AND QUALITY LADDERS")
    stop = lines.index("MODULE E - MAJOR ii-V-I SHELLS AND GUIDE-TONE LINES")
    raw = lines[start:stop]
    expected = ["E-root shells on E-D-G:", "A-root shells on A-G-B:",
                "m7b5 uses the same shell; add B-string r-1 for b5.",
                "m7b5 uses the same shell; add D-string r+1 for b5."]
    if any(item not in raw for item in expected):
        raise CandidateError("SHELL_RULE_MISSING")
    for root_string, root_name in (("E", "A"), ("A", "D")):
        minor = lookup[(root_string, root_name + "m7")]["contacts"]
        half = lookup[(root_string, root_name + "m7b5")]["contacts"]
        retained = ("E", "D", "G") if root_string == "E" else ("A", "G", "B")
        if [(c["string"], c["fret"]) for c in minor if c["string"] in retained] != [
                (c["string"], c["fret"]) for c in half if c["string"] in retained]:
            raise CandidateError("HALF_DIM_SHELL_NOT_IDENTICAL")
    ladders = []
    for root_name, root_string in (("A", "E"), ("D", "A")):
        prefix = f"{root_name} {root_string}-root ladder: "
        matches = [(i, line) for i, line in enumerate(lines) if line.startswith(prefix)]
        if len(matches) != 1:
            raise CandidateError("LADDER_MISSING")
        i, line = matches[0]
        if not line.endswith(". Repeat four times."):
            raise CandidateError("LADDER_REPEAT_MISSING")
        chords = line[len(prefix):-len(". Repeat four times.")].split(" -> ")
        if chords != [root_name + quality for quality in ("maj7", "7", "m7", "m7b5", "m7", "7", "maj7")]:
            raise CandidateError("LADDER_ORDER_INVALID")
        attacks = []
        for repeat in range(1, 5):
            for step, chord in enumerate(chords, 1):
                shape = lookup[(root_string, chord)]
                retained = ("E", "D", "G") if root_string == "E" else ("A", "G", "B")
                contacts = [c for c in shape["contacts"] if c["string"] in retained]
                attack = _attack(chord, kind="shell_ladder", contacts=contacts)
                attack.update({"repeat": repeat, "step": step})
                attacks.append(attack)
        ladders.append({"root": root_name, "root_string": root_string, "chords": chords,
                        "repetitions": 4, "attacks": attacks, "attack_count": len(attacks),
                        "source_ref": f"L57-TXT1-{i + 1}", "raw_line": line, "pdf_page": 8})
    if not all(ladder["attack_count"] == 28 for ladder in ladders):
        raise CandidateError("LADDER_COUNT_INVALID")
    return {"shell_rules": raw, "source_ref": f"L57-TXT1-{start + 1}-{stop}",
            "pdf_pages": [7, 8], "ladders": ladders, "attack_count": 56,
            "pdf_text": [pages[6], pages[7]]}


def _cadences(lines: list[str], pages: list[list[str]], *, minor: bool,
              lookup: dict[tuple[str, str], dict[str, Any]]) -> dict[str, Any]:
    title = "MODULE F - MINOR iiø-V-i SHELLS AND GUIDE-TONE LINES" if minor else "MODULE E - MAJOR ii-V-I SHELLS AND GUIDE-TONE LINES"
    next_title = "MODULE G - A-BLUES SHELL COMPING" if minor else "MODULE F - MINOR iiø-V-i SHELLS AND GUIDE-TONE LINES"
    start, stop = lines.index(title), lines.index(next_title)
    expected_keys = ("A", "E", "B", "F#", "C#", "D") if minor else ("C", "G", "D", "A", "E", "F")
    cells = []
    for i in range(start, stop):
        match = CADENCE_HEAD.fullmatch(lines[i])
        if not match:
            continue
        key, mode = match.group(1), match.group(2)
        if (mode == "minor") != minor:
            raise CandidateError("CADENCE_MODE_INVALID")
        chords = [match.group(3), match.group(4), match.group(5)]
        row_start = i + (2 if minor else 1)
        block = lines[row_start:row_start + 10]
        if len(block) != 10 or not block[0].startswith("Chd|") or not block[1].startswith("Rol|"):
            raise CandidateError(f"CADENCE_GRID_INVALID {key}")
        if CHORD_TOKEN.findall(block[0]) != chords or block[4] != "LOWER VOICE" or block[7] != "UPPER VOICE":
            raise CandidateError(f"CADENCE_CHORD_ROW_INVALID {key}")
        g = [int(x) for x in re.findall(r"\d+", block[2])]
        d = [int(x) for x in re.findall(r"\d+", block[3])]
        low = [int(x) for x in re.findall(r"\d+", block[5])]
        high = [int(x) for x in re.findall(r"\d+", block[8])]
        lower_roles = re.findall(r"b3|b7|3|7", block[6])
        upper_roles = re.findall(r"b3|b7|3|7", block[9])
        expected_low = ["b3", "b7", "b3" if minor else "3"]
        expected_high = ["b7", "3", "b7" if minor else "7"]
        if not (len(g) == len(d) == len(low) == len(high) == 3 and d == low and g == high and
                lower_roles == expected_low and upper_roles == expected_high):
            raise CandidateError(f"CADENCE_VOICE_ROWS_INVALID {key}")
        expected_rule = ("Exercise: play full iiø once; four shell attacks per chord; both voice lines = 18 attacks."
                         if minor else "Exercise: four shell attacks per chord plus both three-note voice lines = 18 attacks.")
        if lines[row_start + 10] != expected_rule:
            raise CandidateError(f"CADENCE_ATTACK_RULE_INVALID {key}")
        attacks = []
        for slot, chord in enumerate(chords):
            pair = [_contact("D", d[slot], chord, expected_low[slot]),
                    _contact("G", g[slot], chord, expected_high[slot])]
            for beat in range(1, 5):
                event = _attack(chord, kind="blocked_shell", contacts=pair)
                event.update({"chord_slot": slot + 1, "beat": beat})
                attacks.append(event)
        for direction, string, frets, roles in (("lower", "D", low, lower_roles),
                                                ("upper", "G", high, upper_roles)):
            for slot, (chord, fret, role) in enumerate(zip(chords, frets, roles, strict=True), 1):
                contact = _contact(string, fret, chord, role)
                event = _attack(chord, kind="guide_tone_line", contacts=[contact], string=string, role=role)
                event.update({"voice": direction, "chord_slot": slot})
                attacks.append(event)
        check = None
        if minor:
            check_line = lines[i + 1]
            if not check_line.startswith("Full iiø quality check: "):
                raise CandidateError("MINOR_FULL_CHECK_MISSING")
            frets = _voicing_tokens(check_line.removeprefix("Full iiø quality check: "))
            _full_half_dim_check(chords[0], frets)
            check = {"chord": chords[0], "frets_e_a_d_g_b_e": frets,
                     "preparatory_instruction": check_line, "counted_in_printed_18": False,
                     "source_ref": f"L57-TXT1-{i + 2}"}
        pdf_page = (12 if minor and len(cells) < 3 else 13 if minor else 9 if len(cells) < 3 else 10)
        if lines[i] not in pages[pdf_page - 1]:
            raise CandidateError(f"PDF_CADENCE_HEADING_MISSING {key}")
        cells.append({"key": key, "mode": mode, "chords": chords,
                      "shell_d_frets": d, "shell_g_frets": g,
                      "lower_roles": lower_roles, "upper_roles": upper_roles,
                      "preparatory_full_iiø": check, "attacks": attacks,
                      "attack_count": len(attacks), "raw_lines": lines[i:row_start + 11],
                      "source_ref": f"L57-TXT1-{i + 1}-{row_start + 11}", "pdf_page": pdf_page})
    if [cell["key"] for cell in cells] != list(expected_keys) or any(cell["attack_count"] != 18 for cell in cells):
        raise CandidateError("CADENCE_CELL_COUNT_INVALID")
    return {"cells": cells, "attack_count": 108, "source_ref": f"L57-TXT1-{start + 1}-{stop}",
            "pdf_pages": [12, 13, 14] if minor else [9, 10, 11],
            "count_boundary": "Full iiø formation is preparatory and outside the printed 18 counted attacks; source wording says play once, so an actual sounded preparatory strike would exceed the printed total." if minor else None,
            "supplemental_pdf_alternative": (
                {"page": 14, "two_stage_iiø_drill": "Play the full four-note m7b5 voicing and sing the b5, then remove the b5 and continue with the rootless guide-tone dyad.",
                 "dominant_resolution_drill": "Hold the V third, sing the tonic, then resolve both guide voices into minor i.",
                 "counted_in_printed_108": False} if minor else
                {"page": 11, "circle_order": ["C", "G", "D", "A", "E", "F"],
                 "comping_pass": "Attack shell on beat 1; arpeggiate lower then upper guide tone on beats 2-3; release on beat 4.",
                 "printed_supplemental_attacks_per_key": 12, "counted_in_printed_108": False}),
            "supplemental_pdf_text": pages[13] if minor else pages[10]}


def _blues(lines: list[str], pages: list[list[str]]) -> dict[str, Any]:
    start = lines.index("MODULE G - A-BLUES SHELL COMPING")
    stop = lines.index("MODULE H - SEVENTH-CHORD ARPEGGIO SCANS")
    raw = lines[start:stop]
    form = "FORM: | A7 | A7 | A7 | A7 | D7 | D7 | A7 | A7 | E7 | D7 | A7 | E7 |"
    if form not in raw:
        raise CandidateError("BLUES_FORM_INVALID")
    maps: dict[str, dict[str, list[dict[str, Any]]]] = {"low": {}, "middle": {}, "high": {}}
    for chord in ("A7", "D7", "E7"):
        low = [line for line in raw if line.startswith(chord + ": ") and " + " not in line]
        middle = [line for line in raw if re.fullmatch(chord + r": D\d+ \+ G\d+", line)]
        high = [line for line in raw if re.fullmatch(chord + r": B\d+ \+ e\d+", line)]
        if len(low) != 1 or len(middle) != 1 or len(high) != 1:
            raise CandidateError("BLUES_MAP_COUNT_INVALID")
        frets = _voicing_tokens(low[0].split(": ", 1)[1])
        maps["low"][chord] = [_contact(s, fret, chord) for s, fret in zip(STRINGS, frets, strict=True) if fret is not None]
        for register, line in (("middle", middle[0]), ("high", high[0])):
            pairs = re.findall(r"([EDGBeA])(\d+)", line.split(": ", 1)[1])
            maps[register][chord] = [_contact(s, int(fret), chord) for s, fret in pairs]
        if len(maps["low"][chord]) != 3 or len(maps["middle"][chord]) != 2 or len(maps["high"][chord]) != 2:
            raise CandidateError("BLUES_CONTACT_COUNT_INVALID")
    pass_rules = ["Pass 1: low sustained, 12 attacks.",
                  "Pass 2: middle beats 2 and 4, 24 attacks.",
                  "Pass 3: high shuffle chops on beats 2 and 4, 24 attacks.",
                  "Pass 4: register-cycle blocked shell plus arpeggio, 48 attacks."]
    if any(rule not in raw for rule in pass_rules):
        raise CandidateError("BLUES_PASS_RULE_MISSING")
    if "low bars 1-4; middle 5-8; high 9-12" not in pages[15]:
        raise CandidateError("PDF_BLUES_REGISTER_RULE_MISSING")
    passes = []
    for number, (register, beats, kind) in enumerate((("low", (1,), "sustained_shell"),
                                                       ("middle", (2, 4), "backbeat_dyad"),
                                                       ("high", (2, 4), "shuffle_chop")), 1):
        attacks = []
        for bar, chord in enumerate(BLUES_FORM, 1):
            for beat in beats:
                event = _attack(chord, kind=kind, contacts=maps[register][chord])
                event.update({"bar": bar, "beat": beat, "register": register})
                attacks.append(event)
        passes.append({"pass": number, "rule": pass_rules[number - 1], "attacks": attacks,
                       "attack_count": len(attacks)})
    cycle = ("low", "middle", "high")
    attacks = []
    for bar, chord in enumerate(BLUES_FORM, 1):
        register = cycle[(bar - 1) // 4]
        event = _attack(chord, kind="blocked_shell", contacts=maps[register][chord])
        event.update({"bar": bar, "register": register, "attack_in_bar": 1})
        attacks.append(event)
        for slot in (2, 3, 4):
            event = _attack(chord, kind="three_note_arpeggio_unspecified_contact", contacts=[])
            event.update({"bar": bar, "register": register, "attack_in_bar": slot,
                          "contact_selection": None})
            attacks.append(event)
    passes.append({"pass": 4, "rule": pass_rules[3],
                   "register_blocks": [{"bars": [1, 4], "register": "low"},
                                       {"bars": [5, 8], "register": "middle"},
                                       {"bars": [9, 12], "register": "high"}],
                   "pdf_register_rule": "low bars 1-4; middle 5-8; high 9-12",
                   "contact_limit": "Source does not specify the three arpeggio contacts or string order, particularly for rootless dyads.",
                   "attacks": attacks, "attack_count": len(attacks)})
    if [p["attack_count"] for p in passes] != [12, 24, 24, 48]:
        raise CandidateError("BLUES_PASS_COUNT_INVALID")
    return {"form": list(BLUES_FORM), "maps": maps, "passes": passes,
            "attack_count": 108, "raw_lines": raw, "source_ref": f"L57-TXT1-{start + 1}-{stop}",
            "pdf_pages": [15, 16], "pdf_text": [pages[14], pages[15]]}


def _arpeggios(lines: list[str], pages: list[list[str]]) -> dict[str, Any]:
    start = lines.index("MODULE H - SEVENTH-CHORD ARPEGGIO SCANS")
    stop = lines.index("MODULE I - SIXTEEN-BAR CAPSTONES")
    scans = []
    for i in range(start, stop):
        match = ARP_HEAD.fullmatch(lines[i])
        if not match:
            continue
        chord, position = match.groups()
        block = lines[i + 1:i + 10]
        if len(block) != 9 or block[-1] != "Eight attacks: low to high, then high to low.":
            raise CandidateError(f"ARPEGGIO_GRID_INVALID {chord}")
        if any(row not in pages[16] for row in [lines[i], *block[:8]]):
            raise CandidateError(f"PDF_ARPEGGIO_GRID_MISMATCH {chord}")
        notes = block[0][4:-1].split("-")
        roles = block[1][4:-1].split("-")
        notes = [token for token in notes if token]
        roles = [token for token in roles if token]
        if len(notes) != 8 or len(roles) != 8:
            raise CandidateError(f"ARPEGGIO_NOTE_COUNT_INVALID {chord}")
        grid = {}
        for row in block[2:8]:
            m = re.fullmatch(r"  ([eBGDAE])\|([0-9-]{32})\|", row)
            if not m:
                raise CandidateError(f"ARPEGGIO_TAB_ROW_INVALID {chord}")
            grid[m.group(1)] = [m.group(2)[j:j + 4] for j in range(0, 32, 4)]
        if set(grid) != set(STRINGS):
            raise CandidateError("ARPEGGIO_STRING_SET_INVALID")
        attacks = []
        for slot in range(8):
            sounding = [(s, int(token.rstrip("-"))) for s, slots in grid.items()
                        if (token := slots[slot]) != "----"]
            if len(sounding) != 1:
                raise CandidateError(f"ARPEGGIO_SLOT_INVALID {chord} {slot + 1}")
            string, fret = sounding[0]
            contact = _contact(string, fret, chord, roles[slot])
            if PC[notes[slot]] != contact["pitch_class"]:
                raise CandidateError(f"ARPEGGIO_PITCH_INVALID {chord} {slot + 1}")
            attack = _attack(chord, kind="single_note_arpeggio", contacts=[contact],
                             string=string, role=roles[slot], note=notes[slot])
            attack["slot"] = slot + 1
            attacks.append(attack)
        if notes[3] != notes[4] or roles[3] != roles[4] or attacks[3]["contacts"] != attacks[4]["contacts"]:
            raise CandidateError(f"ARPEGGIO_TOP_REPEAT_INVALID {chord}")
        scans.append({"chord": chord, "position": position, "notes": notes, "roles": roles,
                      "tab_rows": block[2:8], "attacks": attacks, "attack_count": len(attacks),
                      "source_ref": f"L57-TXT1-{i + 1}-{i + 10}", "pdf_page": 17})
    if [(s["chord"], s["position"]) for s in scans] != [(c, "E-root") for c in ("Amaj7", "A7", "Am7", "Am7b5")] + [(c, "A-root") for c in ("Dmaj7", "D7", "Dm7", "Dm7b5")]:
        raise CandidateError("ARPEGGIO_SCAN_SET_INVALID")
    return {"scans": scans, "attack_count": 64, "pdf_page": 17, "pdf_text": pages[16],
            "supplemental_pdf_passes": ["Second pass: accent only the third and seventh.",
                                        "Third pass: omit the root attack and hear the remaining guide-tone function."],
            "source_ref": f"L57-TXT1-{start + 1}-{stop}"}


def _capstones(lines: list[str], pages: list[list[str]], lookup: dict[tuple[str, str], dict[str, Any]]) -> dict[str, Any]:
    start = lines.index("MODULE I - SIXTEEN-BAR CAPSTONES")
    stop = lines.index("PRACTICE PROGRESSION AND MASTERY")
    raw = lines[start:stop]
    heading_major = "MAJOR CAPSTONE: C, G, D, A major. Each block = ii-V-I-I. Four quarter-note shell attacks per bar. 64 attacks."
    heading_minor = "MINOR CAPSTONE: A, E, B, D minor. Each block = iiø-V-i-i. Play full iiø once before the shell block. 64 attacks."
    if heading_major not in raw or heading_minor not in raw:
        raise CandidateError("CAPSTONE_RULE_MISSING")
    result = {}
    for mode, keys in (("major", ("C", "G", "D", "A")), ("minor", ("A", "E", "B", "D"))):
        blocks = []
        for key in keys:
            matches = [(i, line) for i, line in enumerate(lines[start:stop], start) if line.startswith(key + ": ")]
            matches = [(i, line) for i, line in matches if (" ; iiø " in line) == (mode == "minor")]
            if len(matches) != 1:
                raise CandidateError(f"CAPSTONE_BLOCK_MISSING {mode} {key}")
            i, line = matches[0]
            pieces = line.split(" ; ")
            chords = [c.strip() for c in pieces[0].split(": ", 1)[1].split(" | ")]
            pairs = [(int(a), int(b)) for a, b in re.findall(r"\((\d+), (\d+)\)", pieces[1])]
            if len(chords) != 4 or len(pairs) != 4 or chords[2] != chords[3]:
                raise CandidateError("CAPSTONE_BAR_GRID_INVALID")
            preparatory = None
            if mode == "minor":
                if len(pieces) != 3 or not pieces[2].startswith("iiø "):
                    raise CandidateError("CAPSTONE_MINOR_CHECK_MISSING")
                frets = _voicing_tokens(pieces[2].removeprefix("iiø "))
                _full_half_dim_check(chords[0], frets)
                preparatory = {"chord": chords[0], "frets_e_a_d_g_b_e": frets,
                               "counted_in_printed_64": False}
            attacks = []
            for bar, (chord, (d, g)) in enumerate(zip(chords, pairs, strict=True), 1):
                quality = _chord(chord)[1]
                roles = ("b3", "b7") if quality in ("m7", "m7b5") else ("b7", "3") if quality == "7" else ("3", "7")
                pair = [_contact("D", d, chord, roles[0]), _contact("G", g, chord, roles[1])]
                for beat in range(1, 5):
                    event = _attack(chord, kind="capstone_shell", contacts=pair)
                    event.update({"bar_in_block": bar, "beat": beat})
                    attacks.append(event)
            blocks.append({"key": key, "mode": mode, "chords": chords, "dg_pairs": pairs,
                           "preparatory_full_iiø": preparatory, "attacks": attacks,
                           "attack_count": len(attacks), "raw_line": line,
                           "source_ref": f"L57-TXT1-{i + 1}", "pdf_page": 18})
        if any(block["attack_count"] != 16 for block in blocks):
            raise CandidateError("CAPSTONE_BLOCK_COUNT_INVALID")
        result[mode] = {"blocks": blocks, "bars": 16, "attack_count": 64,
                        "count_boundary": "Full iiø once before each minor block is preparatory and outside printed 64; a sounded strike would exceed 64." if mode == "minor" else None}
    return {"major": result["major"], "minor": result["minor"], "attack_count": 128,
            "supplemental_pdf_performance": ["Announce the next key on beat 4 of the final tonic measure.",
                                             "Use the printed D/G guide-tone dyads; add the root only on the first pass."],
            "raw_lines": raw, "source_ref": f"L57-TXT1-{start + 1}-{stop}",
            "pdf_page": 18, "pdf_text": pages[17]}


def build_candidate(root: Path | None = None) -> dict[str, Any]:
    root = _root() if root is None else root
    txt_bytes = _source_bytes(root, TXT_REL)
    pdf_bytes = _source_bytes(root, PDF_REL)
    _verify(txt_bytes, TXT_BYTES, TXT_SHA256, "TXT")
    _verify(pdf_bytes, PDF_BYTES, PDF_SHA256, "PDF")
    lines = txt_bytes.decode("utf-8-sig").splitlines()
    pages = _pdf_pages(pdf_bytes)
    if len(lines) != 741 or "COMPLETE SOUNDED WORKOUT: 796 attacks." not in lines:
        raise CandidateError("TXT_STRUCTURE_INVALID")
    families, lookup = _shape_families(lines, pages)
    shells = _shell_and_ladders(lines, pages, lookup)
    major = _cadences(lines, pages, minor=False, lookup=lookup)
    minor = _cadences(lines, pages, minor=True, lookup=lookup)
    blues = _blues(lines, pages)
    arpeggios = _arpeggios(lines, pages)
    capstones = _capstones(lines, pages, lookup)
    modules = {"A_silent_formations": {"count": 56, "sounded": False,
                                       "root_maps": lines[42:44], "rule": lines[44],
                                       "source_ref": "L57-TXT1-41-45"},
               "B_E_root_families": {"families": [f for f in families if f["root_string"] == "E"], "attack_count": 112},
               "C_A_root_families": {"families": [f for f in families if f["root_string"] == "A"], "attack_count": 112},
               "D_quality_ladders": shells, "E_major_cadences": major,
               "F_minor_cadences": minor, "G_A_blues": blues,
               "H_arpeggio_scans": arpeggios, "I_capstones": capstones}
    actual = {name: modules[name]["attack_count"] for name in EXPECTED_COUNTS}
    if actual != EXPECTED_COUNTS or sum(actual.values()) != 796:
        raise CandidateError("WORKLOAD_RECONCILIATION_INVALID")
    return {"schema": "fathom.level57.whole.detached_candidate.v1", "level": 57,
            "status": "candidate_only", "wbs": "2.3.1.2.1",
            "source": {"txt": {"path": str(TXT_REL), "bytes": TXT_BYTES, "sha256": TXT_SHA256,
                               "lines": len(lines), "line_ids": [f"L57-TXT1-{i + 1}" for i in range(len(lines))]},
                       "pdf": {"path": str(PDF_REL), "bytes": PDF_BYTES, "sha256": PDF_SHA256,
                               "pages": len(pages), "page_ids": [f"L57-PDF1-p{i + 1}" for i in range(len(pages))]}},
            "workload": {"silent_formations": 56, "sounded_attacks": 796,
                         "module_attacks": actual, "preparatory_full_iiø_checks_counted": False},
            "musical_limits": {"m7_m7b5_shells_identical": True,
                               "flat_fifth_restoration_required": True,
                               "minor_full_check_count_boundary": minor["count_boundary"],
                               "minor_capstone_check_count_boundary": capstones["minor"]["count_boundary"],
                               "blues_pass4_arpeggio_contacts": "unspecified in source"},
            "modules": modules,
            "source_transcription": {"txt_lines": lines,
                                     "pdf_pages": [{"page": i + 1, "lines": page} for i, page in enumerate(pages)]}}


def write_candidate(candidate: dict[str, Any], root: Path | None = None) -> tuple[Path, Path]:
    root = _root() if root is None else root
    build = root / BUILD_REL
    if build.exists() and build.is_symlink():
        raise CandidateError("BUILD_SYMLINK_INVALID")
    build.mkdir(parents=True, exist_ok=True)
    main = build / "level057_whole_candidate.json"
    manifest = build / "manifest.json"
    for path in (main, manifest):
        if path.exists() and path.is_symlink():
            raise CandidateError(f"OUTPUT_SYMLINK_INVALID {path.name}")
    blob = (json.dumps(candidate, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    main.write_bytes(blob)
    manifest.write_text(json.dumps({"schema": "fathom.detached_candidate_manifest.v1",
                                    "candidate": main.name, "sha256": digest(blob),
                                    "bytes": len(blob), "status": "candidate_only",
                                    "source_txt_sha256": TXT_SHA256,
                                    "source_pdf_sha256": PDF_SHA256}, indent=2) + "\n")
    return main, manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Validate pinned sources and construct candidate in memory")
    args = parser.parse_args()
    candidate = build_candidate()
    if args.check:
        print("LEVEL57_CHECK_OK", json.dumps(candidate["workload"], sort_keys=True))
    else:
        main_path, manifest_path = write_candidate(candidate)
        print(main_path)
        print(manifest_path)


if __name__ == "__main__":
    main()
