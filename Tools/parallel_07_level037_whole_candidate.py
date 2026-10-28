#!/usr/bin/env python3
"""Build a detached, source-linked candidate for the whole fixed-key Level 37.

Printed note slots and source rhythm words are retained without assigning a
runtime clock. The PDF-only overview example remains outside the 496-note core.
"""

from __future__ import annotations

from collections import Counter
from io import BytesIO
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
TXT_REL = Path("Notes/music/guitar project/TXT version/Scale_Exercises_Section_IV_Level_37_Major_Pentatonic_I_IV_V_Chord_Tone_Targeting_and_Voice_Leading_Fixed_Key_A.txt")
PDF_REL = Path("Notes/music/guitar project/PDF version/Scale_Exercises_Section_IV_Level_37_Major_Pentatonic_I_IV_V_Chord_Tone_Targeting_and_Voice_Leading_Fixed_Key_A.pdf")
TXT_BYTES = 28711
TXT_SHA256 = "dc7e313b24cb46abd30b9dc8f3e26344d096cbf18c733f5619318c2c4dbfc301"
PDF_BYTES = 38536
PDF_SHA256 = "249b77610bec5ffbef1525bcead75b3ee51eeec8584b49c99730234a9387225b"
BUILD_REL = Path("Build/parallel-07/2.3.1.1.1-level037-whole-r01")
STRINGS_HIGH_TO_LOW = ("e", "B", "G", "D", "A", "E")
OPEN_MIDI = {"E": 40, "A": 45, "D": 50, "G": 55, "B": 59, "e": 64}
NATURAL_PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
POOL = ("A", "B", "C#", "E", "F#")
CHORDS = ("A", "D", "E")
ROLE = {
    "A": {"A": "R", "B": "9", "C#": "3", "E": "5", "F#": "13"},
    "D": {"A": "5", "B": "13", "C#": "M7", "E": "9", "F#": "3", "D*": "R"},
    "E": {"A": "11", "B": "5", "C#": "13", "E": "R", "F#": "9", "G#*": "3"},
}
STRONG = {"A": ("A", "C#", "E"), "D": ("F#", "A", "D*"), "E": ("E", "B", "G#*")}
POSITION_HEAD = re.compile(r"^P([1-5]) - ([A-Z-]+) FRAME - FRETS (\d+)-(\d+)(?: - 32 EIGHTH NOTES)?$")
TARGET_HEAD = re.compile(r"^(I|IV|V) - ([ADE]) MAJOR - (\d+)-NOTE TARGET CELL$")
TARGET_TOKEN = re.compile(r"([A-G](?:#|b)?)\(([eBGDAE])(\d+)\)")
ROUTE_TOKEN = re.compile(r"([A-G](?:#|b)?)\(([eBGDAE])(\d+)\) (R|3|5)")
BEAT_TARGET = re.compile(r"([ADE]) ([A-G](?:#|b)?)(?:\((R|3|5)\))")
STAFF_ROW = re.compile(r"^(?:Nte|Rol|Fng|[eBGDAE]  )\|")
NOTE_TOKEN = re.compile(r"[A-G](?:#|b)?\*?")
ROLE_TOKEN = re.compile(r">?(?:R|M7|13|11|9|5|3)")
PROGRESSION_C = ("A", "D", "E", "A")
PROGRESSION_D = ("D", "E", "A")
PROGRESSION_E = ("A", "A", "A", "A", "D", "D", "A", "A", "E", "D", "A", "E")
PDF_EXAMPLE_ROWS = (
    "Nte|A---B---C#--E---|F#--E---C#--A---|E---F#--B---E---|C#--B---A---A---|",
    "Rol|>R--9---3---5---|>3--9---M7--5---|>R--9---5---R---|>3--9---R---R---|",
    "e  |----------------|----------------|--------7-------|----------------|",
    "B  |------------5---|7---5-----------|5---7-------5---|----------------|",
    "G  |----4---6-------|--------6-------|----------------|6---4-----------|",
    "D  |7---------------|------------7---|----------------|--------7---7---|",
    "A  |----------------|----------------|----------------|----------------|",
    "E  |----------------|----------------|----------------|----------------|",
)


class CandidateError(ValueError):
    """Pinned source, contact, harmony or output boundary failed."""


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _verify(data: bytes, size: int, sha: str, label: str) -> None:
    if len(data) != size or digest(data) != sha:
        raise CandidateError(f"PINNED_INPUT_DRIFT {label}: bytes={len(data)} sha256={digest(data)}")


def _root() -> Path:
    result = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if result.returncode != 0 or Path(result.stdout.strip()).resolve() != ROOT.resolve():
        raise CandidateError("REPOSITORY_ROOT_MISMATCH")
    return ROOT


def _source_bytes(root: Path, rel: Path) -> bytes:
    path = root / rel
    if path.is_symlink() or not path.is_file() or path.resolve().parent != path.parent.resolve():
        raise CandidateError(f"SOURCE_PATH_INVALID {rel}")
    return path.read_bytes()


def _pitch_class(name: str) -> int:
    bare = name.removesuffix("*")
    if re.fullmatch(r"[A-G](?:#|b)?", bare) is None:
        raise CandidateError(f"NOTE_NAME_INVALID {name}")
    accidental = 1 if bare.endswith("#") else -1 if bare.endswith("b") else 0
    return (NATURAL_PC[bare[0]] + accidental) % 12


def _row_parts(row: str, prefix: str, bars: int, width: int) -> list[str]:
    parts = row.split("|")
    if (len(parts) != bars + 2 or parts[0] != prefix or parts[-1] != ""
        or any(len(part) != width or re.fullmatch(r"[A-Za-z0-9#*>-]+", part) is None for part in parts[1:-1])):
        raise CandidateError(f"STAFF_ROW_INVALID {prefix}")
    return parts[1:-1]


def _parse_staff(rows: list[str], chords: tuple[str, ...], slots_per_bar: int,
                 *, finger: bool, strong_first: bool, label: str) -> dict[str, Any]:
    expected_rows = 9 if finger else 8
    if len(rows) != expected_rows or len(chords) == 0:
        raise CandidateError(f"STAFF_LAYOUT_INVALID {label}")
    bars = len(chords)
    width = slots_per_bar * 4
    note_cells = _row_parts(rows[0], "Nte", bars, width)
    role_cells = _row_parts(rows[1], "Rol", bars, width)
    finger_cells = _row_parts(rows[2], "Fng", bars, width) if finger else None
    tab_start = 3 if finger else 2
    tab_cells = [_row_parts(row, string + "  ", bars, width)
                 for row, string in zip(rows[tab_start:], STRINGS_HIGH_TO_LOW, strict=True)]
    events = []
    bar_records = []
    for bar_index, chord in enumerate(chords):
        note_tokens = [(m.start(), m.group()) for m in NOTE_TOKEN.finditer(note_cells[bar_index])]
        role_tokens = [(m.start(), m.group()) for m in ROLE_TOKEN.finditer(role_cells[bar_index])]
        expected_columns = list(range(0, width, 4))
        if ([col for col, _ in note_tokens] != expected_columns
            or [col for col, _ in role_tokens] != expected_columns):
            raise CandidateError(f"STAFF_NOTE_ROLE_COLUMNS_INVALID {label} {bar_index + 1}")
        finger_tokens = [(m.start(), int(m.group())) for m in re.finditer(r"\d+", finger_cells[bar_index])] if finger_cells else []
        if finger_cells and ([col for col, _ in finger_tokens] != expected_columns
                             or any(not 1 <= digit <= 4 for _, digit in finger_tokens)):
            raise CandidateError(f"STAFF_FINGER_COLUMNS_INVALID {label} {bar_index + 1}")
        contacts = []
        for string, cells in zip(STRINGS_HIGH_TO_LOW, tab_cells, strict=True):
            for m in re.finditer(r"\d+", cells[bar_index]):
                contacts.append((m.start(), string, int(m.group())))
        contacts.sort(key=lambda item: item[0])
        if [column for column, _, _ in contacts] != expected_columns:
            raise CandidateError(f"STAFF_TAB_COLUMNS_INVALID {label} {bar_index + 1}")
        bar_events = []
        for slot_index, ((_, tone), (_, role_token), (_, string, fret)) in enumerate(
            zip(note_tokens, role_tokens, contacts, strict=True)
        ):
            role = role_token.removeprefix(">")
            expected_role = ROLE[chord].get(tone)
            if expected_role is None or role != expected_role:
                raise CandidateError(f"CHORD_ROLE_OR_COMPLETION_INVALID {label} {bar_index + 1} {slot_index + 1}")
            if bool(role_token.startswith(">")) != bool(strong_first and slot_index == 0):
                raise CandidateError(f"BEAT_ONE_MARKER_INVALID {label} {bar_index + 1} {slot_index + 1}")
            if strong_first and slot_index == 0 and tone not in STRONG[chord]:
                raise CandidateError(f"BEAT_ONE_TARGET_INVALID {label} {bar_index + 1}")
            if (OPEN_MIDI[string] + fret) % 12 != _pitch_class(tone):
                raise CandidateError(f"TAB_NOTE_PITCH_MISMATCH {label} {bar_index + 1} {slot_index + 1}")
            event = {"ordinal": len(events) + 1, "bar_ordinal": bar_index + 1,
                     "slot_in_bar": slot_index + 1, "chord": chord, "tone": tone,
                     "role": role, "marked_beat_one": role_token.startswith(">"),
                     "string": string, "fret": fret,
                     "finger_digit": finger_tokens[slot_index][1] if finger_cells else None,
                     "ascii_column_in_bar": expected_columns[slot_index],
                     "completion_tone": tone.endswith("*"),
                     "onset_q": None, "duration_q": None}
            events.append(event)
            bar_events.append(event["ordinal"])
        bar_records.append({"ordinal": bar_index + 1, "chord": chord, "event_ordinals": bar_events})
    return {"raw_rows": rows, "bars": bar_records, "events": events}


def _parse_target_list(line: str) -> list[dict[str, Any]]:
    if not line.startswith("Targets: "):
        raise CandidateError("TARGET_LIST_PREFIX_INVALID")
    parts = line.removeprefix("Targets: ").split(", ")
    if any(TARGET_TOKEN.fullmatch(part) is None for part in parts):
        raise CandidateError("TARGET_LIST_TOKEN_INVALID")
    return [{"tone": m.group(1), "string": m.group(2), "fret": int(m.group(3))}
            for part in parts if (m := TARGET_TOKEN.fullmatch(part))]


def _position(line: str, expected: int, *, phrase: bool = False) -> dict[str, Any]:
    match = POSITION_HEAD.fullmatch(line)
    if match is None or int(match.group(1)) != expected or bool(phrase) != bool(line.endswith(" - 32 EIGHTH NOTES")):
        raise CandidateError(f"POSITION_HEADER_INVALID P{expected}")
    return {"position": expected, "name": match.group(2).lower(),
            "frame_low": int(match.group(3)), "frame_high": int(match.group(4))}


def _parse_module_a(lines: list[str]) -> list[dict[str, Any]]:
    starts = [44, 82, 120, 158, 196]
    positions = []
    note_total = 0
    for pos_index, start in enumerate(starts):
        position = _position(lines[start], pos_index + 1)
        end = starts[pos_index + 1] if pos_index < 4 else 234
        section = lines[start + 1:end]
        headers = [(i, m) for i, line in enumerate(section) if (m := TARGET_HEAD.fullmatch(line))]
        if len(headers) != 3 or [m.group(1) for _, m in headers] != ["I", "IV", "V"]:
            raise CandidateError(f"TARGET_CELL_HEADERS_INVALID P{pos_index + 1}")
        cells = []
        for local_start, match in headers:
            roman, chord, note_count = match.group(1), match.group(2), int(match.group(3))
            if (roman, chord) not in (("I", "A"), ("IV", "D"), ("V", "E")) or note_count % 2:
                raise CandidateError(f"TARGET_CELL_IDENTITY_INVALID P{pos_index + 1}")
            targets = _parse_target_list(section[local_start + 1])
            parsed = _parse_staff(section[local_start + 2:local_start + 11], (chord,), note_count,
                                  finger=True, strong_first=False,
                                  label=f"A P{pos_index + 1} {roman}")
            if (len(parsed["events"]) != note_count or len(targets) * 2 != note_count
                or section[local_start + 11] !=
                "Rule: equal note length and volume; hear the chord under the line; do not fill in omitted scale notes."):
                raise CandidateError(f"TARGET_CELL_COUNT_OR_RULE_INVALID P{pos_index + 1} {roman}")
            observed = [{"tone": event["tone"], "string": event["string"], "fret": event["fret"]}
                        for event in parsed["events"]]
            if observed != targets + list(reversed(targets)):
                raise CandidateError(f"TARGET_CELL_ASC_REPEAT_DESC_INVALID P{pos_index + 1} {roman}")
            if [event["finger_digit"] for event in parsed["events"]] != list(reversed(
                [event["finger_digit"] for event in parsed["events"]]
            )):
                raise CandidateError(f"TARGET_CELL_FINGER_MIRROR_INVALID P{pos_index + 1} {roman}")
            note_total += note_count
            cells.append({"roman": roman, "chord": chord, "target_count": len(targets),
                          "target_list": targets, "target_list_text": section[local_start + 1],
                          "note_count": note_count, **parsed,
                          "source_ref": f"L37-TXT1-{start + local_start + 2}-{start + local_start + 13}"})
        positions.append({**position, "cells": cells})
    if note_total != 168:
        raise CandidateError(f"MODULE_A_NOTE_COUNT {note_total}")
    return positions


def _parse_route_line(line: str, name: str, position: int) -> dict[str, Any]:
    if not line.startswith(name + ": "):
        raise CandidateError(f"VOICE_ROUTE_NAME_INVALID P{position} {name}")
    parts = line.removeprefix(name + ": ").split(" | ")
    if len(parts) != 4 or any(ROUTE_TOKEN.fullmatch(part) is None for part in parts):
        raise CandidateError(f"VOICE_ROUTE_TOKENS_INVALID P{position} {name}")
    events = []
    for index, (part, chord) in enumerate(zip(parts, PROGRESSION_C, strict=True)):
        match = ROUTE_TOKEN.fullmatch(part)
        assert match is not None
        tone, string, fret, role = match.group(1), match.group(2), int(match.group(3)), match.group(4)
        if tone not in STRONG[chord] or ROLE[chord].get(tone) != role:
            raise CandidateError(f"VOICE_ROUTE_ROLE_INVALID P{position} {name} {index + 1}")
        if (OPEN_MIDI[string] + fret) % 12 != _pitch_class(tone):
            raise CandidateError(f"VOICE_ROUTE_PITCH_INVALID P{position} {name} {index + 1}")
        events.append({"ordinal": index + 1, "chord": chord, "tone": tone, "role": role,
                       "string": string, "fret": fret, "source_token": part,
                       "onset_q": None, "duration_q": None})
    return {"name": name, "raw_line": line, "events": events}


def _parse_module_b(lines: list[str]) -> list[dict[str, Any]]:
    starts = [240, 248, 256, 264, 272]
    positions = []
    for pos_index, start in enumerate(starts):
        position = _position(lines[start], pos_index + 1)
        routes = []
        for offset, name in ((1, "COMMON-TONE"), (3, "GUIDE-TONE"), (5, "FIFTH-LED")):
            route = _parse_route_line(lines[start + offset], name, pos_index + 1)
            route["instruction_text"] = lines[start + offset + 1].strip()
            route["source_ref"] = f"L37-TXT1-{start + offset + 1}-{start + offset + 2}"
            routes.append(route)
        positions.append({**position, "routes": routes})
    if sum(len(route["events"]) for pos in positions for route in pos["routes"]) != 60:
        raise CandidateError("MODULE_B_NOTE_COUNT")
    return positions


def _beat_targets(line: str, position: int) -> list[dict[str, Any]]:
    if not line.startswith("Beat-1 targets: "):
        raise CandidateError(f"PHRASE_TARGET_PREFIX_INVALID P{position}")
    parts = line.removeprefix("Beat-1 targets: ").split(" | ")
    if len(parts) != 4 or any(BEAT_TARGET.fullmatch(part) is None for part in parts):
        raise CandidateError(f"PHRASE_TARGET_TOKEN_INVALID P{position}")
    return [{"chord": m.group(1), "tone": m.group(2), "role": m.group(3)}
            for part in parts if (m := BEAT_TARGET.fullmatch(part))]


def _parse_module_c(lines: list[str]) -> list[dict[str, Any]]:
    starts = [286, 307, 328, 349, 370]
    phrases = []
    for pos_index, start in enumerate(starts):
        position = _position(lines[start], pos_index + 1, phrase=True)
        targets = _beat_targets(lines[start + 1], pos_index + 1)
        if [target["chord"] for target in targets] != list(PROGRESSION_C):
            raise CandidateError(f"PHRASE_PROGRESSION_INVALID P{pos_index + 1}")
        if lines[start + 2] != "BARS 1-2: A | D" or lines[start + 11] != "BARS 3-4: E | A":
            raise CandidateError(f"PHRASE_BARS_HEADER_INVALID P{pos_index + 1}")
        first = _parse_staff(lines[start + 3:start + 11], ("A", "D"), 8, finger=False,
                             strong_first=True, label=f"C P{pos_index + 1} bars1-2")
        second = _parse_staff(lines[start + 12:start + 20], ("E", "A"), 8, finger=False,
                              strong_first=True, label=f"C P{pos_index + 1} bars3-4")
        bars = first["bars"] + [{**bar, "ordinal": bar["ordinal"] + 2,
                                 "event_ordinals": [i + 16 for i in bar["event_ordinals"]]}
                                for bar in second["bars"]]
        events = first["events"] + [{**event, "ordinal": event["ordinal"] + 16,
                                     "bar_ordinal": event["bar_ordinal"] + 2}
                                    for event in second["events"]]
        observed_targets = [{"chord": event["chord"], "tone": event["tone"], "role": event["role"]}
                            for event in events if event["slot_in_bar"] == 1]
        if observed_targets != targets or len(events) != 32:
            raise CandidateError(f"PHRASE_BEAT_ONE_TARGET_MISMATCH P{pos_index + 1}")
        phrases.append({**position, "beat_one_targets": targets, "beat_one_target_text": lines[start + 1],
                        "raw_blocks": [first["raw_rows"], second["raw_rows"]],
                        "bars": bars, "events": events,
                        "source_ref": f"L37-TXT1-{start + 1}-{start + 20}"})
    if sum(len(phrase["events"]) for phrase in phrases) != 160:
        raise CandidateError("MODULE_C_NOTE_COUNT")
    return phrases


def _choice_map(lines: list[str]) -> list[dict[str, Any]]:
    if lines[396] != "Position | D choices | G# choices":
        raise CandidateError("COMPLETION_CHOICES_HEADER_MISMATCH")
    choices = []
    for index, line in enumerate(lines[397:402]):
        parts = [part.strip() for part in line.split("|")]
        if len(parts) != 3 or parts[0] != f"P{index + 1}":
            raise CandidateError(f"COMPLETION_CHOICES_ROW_INVALID P{index + 1}")
        choices.append({"position": index + 1, "D": parts[1].split(", "),
                        "G#": parts[2].split(", "), "raw_line": line})
    return choices


def _parse_module_d(lines: list[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    choices = _choice_map(lines)
    starts = [405, 415, 425, 435, 445]
    cadences = []
    for pos_index, start in enumerate(starts):
        if lines[start] != f"P{pos_index + 1} COMPLETION CADENCE":
            raise CandidateError(f"CADENCE_HEADER_INVALID P{pos_index + 1}")
        parsed = _parse_staff(lines[start + 1:start + 9], PROGRESSION_D, 4, finger=False,
                              strong_first=False, label=f"D P{pos_index + 1}")
        events = parsed["events"]
        if (len(events) != 12 or [event["tone"] for event in events if event["completion_tone"]] != ["D*", "G#*"]
            or events[0]["tone"] != "D*" or events[4]["tone"] != "G#*"):
            raise CandidateError(f"CADENCE_COMPLETION_BOUNDARY_INVALID P{pos_index + 1}")
        d_contact = events[0]["string"] + str(events[0]["fret"])
        gs_contact = events[4]["string"] + str(events[4]["fret"])
        if d_contact not in choices[pos_index]["D"] or gs_contact not in choices[pos_index]["G#"]:
            raise CandidateError(f"CADENCE_COMPLETION_CHOICE_MISMATCH P{pos_index + 1}")
        cadences.append({"position": pos_index + 1, **parsed,
                         "source_ref": f"L37-TXT1-{start + 1}-{start + 9}"})
    if sum(len(cadence["events"]) for cadence in cadences) != 60:
        raise CandidateError("MODULE_D_NOTE_COUNT")
    return choices, cadences


def _parse_module_e(lines: list[str]) -> dict[str, Any]:
    if lines[458] != "Progression: | A | A | A | A | D | D | A | A | E | D | A | E |.":
        raise CandidateError("CHORUS_PROGRESSION_INVALID")
    blocks = []
    bars = []
    events = []
    for block_index, start in enumerate((462, 472, 482)):
        if lines[start] != f"BARS {block_index * 4 + 1}-{block_index * 4 + 4}":
            raise CandidateError(f"CHORUS_BLOCK_HEADER_INVALID {block_index + 1}")
        parsed = _parse_staff(lines[start + 1:start + 9], PROGRESSION_E[block_index * 4:block_index * 4 + 4],
                              4, finger=False, strong_first=True, label=f"E block{block_index + 1}")
        offset = block_index * 16
        bars.extend({**bar, "ordinal": bar["ordinal"] + block_index * 4,
                     "event_ordinals": [i + offset for i in bar["event_ordinals"]]}
                    for bar in parsed["bars"])
        events.extend({**event, "ordinal": event["ordinal"] + offset,
                       "bar_ordinal": event["bar_ordinal"] + block_index * 4}
                      for event in parsed["events"])
        blocks.append(parsed["raw_rows"])
    if len(events) != 48 or [event["tone"] for event in events if event["completion_tone"]] != ["D*", "G#*", "G#*"]:
        raise CandidateError("CHORUS_COUNT_OR_COMPLETIONS_INVALID")
    return {"progression": list(PROGRESSION_E), "raw_blocks": blocks, "bars": bars, "events": events,
            "source_ref": "L37-TXT1-457-492"}


def _txt_model(txt: str) -> dict[str, Any]:
    lines = txt.splitlines()
    if len(lines) != 520 or lines[:3] != [
        "SCALE EXERCISES - SECTION IV, LEVEL 37",
        "A MAJOR PENTATONIC I-IV-V CHORD-TONE TARGETING AND VOICE LEADING",
        "FIXED KEY A - FIVE POSITIONS - A, D, AND E MAJOR HARMONY",
    ]:
        raise CandidateError("TXT_HEADER_OR_LENGTH_MISMATCH")
    if (lines[10] != "Notes: A B C# E F#" or lines[11] != "Degrees: 1 2 3 5 6"
        or lines[36] != "Complete written workout: 496 sounding tones before optional articulation overlays."):
        raise CandidateError("TXT_POOL_OR_COUNT_MISMATCH")
    if [lines[i] for i in (39, 235, 281, 392, 456)] != [
        "MODULE A - FIVE-POSITION CHORD-TARGET CELLS",
        "MODULE B - NEAREST-TARGET VOICE LEADING THROUGH | A | D | E | A |",
        "MODULE C - FIVE FOUR-BAR TARGET PHRASES",
        "MODULE D - CHORD-COMPLETION TONES: D OVER IV AND G# OVER V",
        "MODULE E - 12-BAR I-IV-V TARGET CIRCUIT AND MODEL CHORUS",
    ]:
        raise CandidateError("TXT_MODULE_BOUNDARY_MISMATCH")
    module_a = _parse_module_a(lines)
    module_b = _parse_module_b(lines)
    module_c = _parse_module_c(lines)
    choices, module_d = _parse_module_d(lines)
    module_e = _parse_module_e(lines)
    return {"lines": lines, "module_a": module_a, "module_b": module_b,
            "module_c": module_c, "module_d_choices": choices,
            "module_d": module_d, "module_e": module_e}


def _pdf_pages(data: bytes) -> list[list[str]]:
    try:
        reader = PdfReader(BytesIO(data), strict=True)
        if len(reader.pages) != 15:
            raise CandidateError(f"PDF_PAGE_COUNT {len(reader.pages)}")
        return [(page.extract_text() or "").splitlines() for page in reader.pages]
    except CandidateError:
        raise
    except Exception as exc:
        raise CandidateError(f"PDF_READ_FAILED {type(exc).__name__}") from exc


def _staff_counter(lines: list[str]) -> Counter[str]:
    return Counter(line for line in lines if STAFF_ROW.match(line))


def _verify_pdf(model: dict[str, Any], pages: list[list[str]]) -> dict[str, Any]:
    txt_lines = model["lines"]
    if (pages[0][:3] != ["Scale Exercises - Section IV, Level 37",
                          "A Major Pentatonic I-IV-V chord-tone targeting and voice leading",
                          "FIXED KEY: A  |  FIVE POSITIONS  |  CHORDS: A - D - E"]
        or "496 sounding tones: 168 target-cell notes, 60 voice-leading tones, 160 phrase notes, 60 chord-completion notes, and a 48-note model chorus. The core target pool remains A-B-C#-E-F#." not in pages[0]):
        raise CandidateError("PDF_OVERVIEW_OR_COUNTS_MISMATCH")
    expected_page_titles = {
        2: "Level 37 - Chord-Role Matrix and Target Atlas",
        8: "Level 37 - Nearest-Target Voice Leading",
        12: "Level 37 - Chord-Completion Tones",
        13: "Level 37 - 12-Bar I-IV-V Target Circuit",
        14: "Level 37 - Model 12-Bar Chorus",
        15: "Level 37 - Practice Progression, Mastery Gate, and Log",
    }
    if any(pages[n - 1][0] != title for n, title in expected_page_titles.items()):
        raise CandidateError("PDF_MODULE_PAGE_TITLE_MISMATCH")
    for position in range(1, 6):
        if pages[position + 1][0] != f"Level 37 - P{position} Chord-Target Cells":
            raise CandidateError(f"PDF_TARGET_PAGE_TITLE_MISMATCH P{position}")
    owned_ranges = ((39, 234, tuple(range(2, 7)), "A"),
                    (281, 391, tuple(range(8, 11)), "C"),
                    (392, 455, (11,), "D"),
                    (456, 492, (13,), "E"))
    for first, last, page_indexes, name in owned_ranges:
        txt_rows = _staff_counter(txt_lines[first:last])
        pdf_rows = sum((_staff_counter(pages[index]) for index in page_indexes), Counter())
        if txt_rows != pdf_rows:
            raise CandidateError(f"PDF_TXT_STAFF_ROWS_MISMATCH {name}")
    if tuple(pages[0][18:26]) != PDF_EXAMPLE_ROWS:
        raise CandidateError("PDF_ONLY_OVERVIEW_EXAMPLE_MISMATCH")
    all_txt = _staff_counter(txt_lines)
    all_pdf = sum((_staff_counter(page) for page in pages), Counter())
    if all_pdf - all_txt != Counter(PDF_EXAMPLE_ROWS) or all_txt - all_pdf:
        raise CandidateError("PDF_TXT_ALL_STAFF_ROWS_MISMATCH")
    atlas = pages[1]
    if atlas[34:40] != ["I - A MAJOR", "A root | C# third | E fifth",
                        "IV - D MAJOR", "F# third | A fifth | D root is absent",
                        "V - E MAJOR", "E root | B fifth | G# third is absent"]:
        raise CandidateError("PDF_CHORD_ATLAS_MISMATCH")
    for pos_index, pos in enumerate(model["module_a"]):
        for cell_index, cell in enumerate(pos["cells"]):
            atlas_text = ", ".join(f"{item['tone']}({item['string']}{item['fret']})"
                                   for item in cell["target_list"])
            if atlas[45 + pos_index * 4 + cell_index] != atlas_text:
                raise CandidateError(f"PDF_TARGET_ATLAS_MISMATCH P{pos_index + 1} {cell['roman']}")
            page = pages[pos_index + 2]
            header = f"{cell['roman']} - {cell['chord']} MAJOR - {cell['note_count']}-NOTE TARGET CELL"
            if header not in page:
                raise CandidateError(f"PDF_TARGET_CELL_HEADER_MISMATCH P{pos_index + 1} {cell['roman']}")
    voice_page = pages[7]
    for pos in model["module_b"]:
        for route in pos["routes"]:
            payload = route["raw_line"].split(": ", 1)[1]
            if payload not in voice_page or route["name"] not in voice_page:
                raise CandidateError(f"PDF_VOICE_ROUTE_MISMATCH P{pos['position']} {route['name']}")
    for phrase in model["module_c"]:
        source_line = phrase["beat_one_target_text"]
        pdf_line = source_line.replace(" A ", " A:").replace(" D ", " D:").replace(" E ", " E:")
        if pdf_line not in pages[8] + pages[9] + pages[10]:
            raise CandidateError(f"PDF_PHRASE_BEAT_TARGET_MISMATCH P{phrase['position']}")
    completion_page = pages[11]
    for choice in model["module_d_choices"]:
        if (", ".join(choice["D"]) not in completion_page
            or ", ".join(choice["G#"]) not in completion_page):
            raise CandidateError(f"PDF_COMPLETION_CHOICES_MISMATCH P{choice['position']}")
    chart = []
    chart_page = pages[12]
    for chunk_start in (9, 34, 59):
        for offset in range(0, 20, 5):
            number, chord, choices, position, target = chart_page[chunk_start + offset:chunk_start + offset + 5]
            bar_number = int(number)
            event = model["module_e"]["events"][(bar_number - 1) * 4]
            allowed_choices = choices.replace("; D* optional", " / D*").replace("; G#* optional", " / G#*").split(" / ")
            if (bar_number != len(chart) + 1 or chord != PROGRESSION_E[bar_number - 1]
                or target != event["tone"] or position not in ("P1", "P2", "P3", "P4", "P5")
                or event["tone"] not in allowed_choices):
                raise CandidateError(f"PDF_CHORUS_CHART_MISMATCH {bar_number}")
            chart.append({"bar": bar_number, "chord": chord, "strong_choices": choices,
                          "suggested_position": position, "model_beat_one": target})
    supplemental = _parse_staff(list(PDF_EXAMPLE_ROWS), PROGRESSION_C, 4, finger=False,
                                strong_first=True, label="PDF-only overview example")
    if len(supplemental["events"]) != 16:
        raise CandidateError("PDF_ONLY_EXAMPLE_COUNT")
    return {"chart": chart, "supplemental_example": supplemental}


def build_candidate(*, txt_data: bytes | None = None, pdf_data: bytes | None = None) -> dict[str, Any]:
    root = _root()
    txt_data = _source_bytes(root, TXT_REL) if txt_data is None else txt_data
    pdf_data = _source_bytes(root, PDF_REL) if pdf_data is None else pdf_data
    _verify(txt_data, TXT_BYTES, TXT_SHA256, "L37-TXT")
    _verify(pdf_data, PDF_BYTES, PDF_SHA256, "L37-PDF")
    try:
        model = _txt_model(txt_data.decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise CandidateError("TXT_ENCODING_INVALID") from exc
    pdf = _verify_pdf(model, _pdf_pages(pdf_data))
    a = sum(len(cell["events"]) for position in model["module_a"] for cell in position["cells"])
    b = sum(len(route["events"]) for position in model["module_b"] for route in position["routes"])
    c = sum(len(phrase["events"]) for phrase in model["module_c"])
    d = sum(len(cadence["events"]) for cadence in model["module_d"])
    e = len(model["module_e"]["events"])
    if (a, b, c, d, e) != (168, 60, 160, 60, 48) or a + b + c + d + e != 496:
        raise CandidateError("WHOLE_WORKOUT_COUNT_MISMATCH")
    lines = model["lines"]
    return {
        "schema": "fathom-level037-whole-detached-candidate-v1", "wbs_id": "2.3.1.1.1", "level": 37,
        "source": {"txt_path": TXT_REL.as_posix(), "txt_bytes": TXT_BYTES, "txt_sha256": TXT_SHA256,
                   "pdf_path": PDF_REL.as_posix(), "pdf_bytes": PDF_BYTES, "pdf_sha256": PDF_SHA256,
                   "pdf_pages": 15},
        "key": "A", "pentatonic_pool": list(POOL),
        "harmony": {"progression_four_bar": list(PROGRESSION_C),
                    "progression_twelve_bar": list(PROGRESSION_E),
                    "strong_targets": {chord: list(targets) for chord, targets in STRONG.items()},
                    "role_matrix": ROLE,
                    "completion_rule": "D* only over D major (IV); G#* only over E major (V); stars are outside the A major pentatonic pool.",
                    "source_refs": ["L37-TXT1-10-29", "L37-PDF1-p2"]},
        "instructions": {"overview_text": "\n".join(lines[:38]), "overview_ref": "L37-TXT1-1-38",
                         "module_B_passes_text": "\n".join(lines[237:240]),
                         "module_C_passes_text": "\n".join(lines[283:286]),
                         "module_D_completion_text": "\n".join(lines[394:405]),
                         "module_E_passes_text": "\n".join(lines[458:462]),
                         "practice_and_mastery_text": "\n".join(lines[492:]),
                         "practice_ref": "L37-TXT1-493-520", "pdf_practice_ref": "L37-PDF1-p15"},
        "modules": {
            "A_target_cells": {"positions": model["module_a"], "note_count": a,
                               "source_refs": ["L37-TXT1-40-235", "L37-PDF1-p2-7"]},
            "B_voice_leading": {"positions": model["module_b"], "note_count": b,
                                "source_refs": ["L37-TXT1-236-281", "L37-PDF1-p8"]},
            "C_target_phrases": {"phrases": model["module_c"], "note_count": c,
                                 "source_refs": ["L37-TXT1-282-392", "L37-PDF1-p9-11"]},
            "D_completion_cadences": {"choices": model["module_d_choices"],
                                      "cadences": model["module_d"], "note_count": d,
                                      "source_refs": ["L37-TXT1-393-456", "L37-PDF1-p12"]},
            "E_model_chorus": {**model["module_e"], "chart": pdf["chart"], "note_count": e,
                               "source_refs": ["L37-TXT1-457-492", "L37-PDF1-p13-14"]},
        },
        "written_workout_note_count": 496,
        "supplemental_pdf_only": {"kind": "worked_overview_example", "source_ref": "L37-PDF1-p1",
                                  "counted_in_written_workout": False,
                                  "note_count": 16, **pdf["supplemental_example"]},
        "exceptions": [{"kind": "pdf_supplemental_example",
                        "detail": "PDF page 1 prints an additional 16-note worked overview absent from TXT; it is kept separate from the 496-note written workout."}],
        "canonical_item_id": None, "canonical_variant_id": None,
        "onset_q": None, "duration_q": None, "fixed_bpm": None, "note_per_click": None,
        "pending": ["Curriculum/musical review", "canonical identity allocation and admission",
                    "runtime note timing and performed audio"],
        "whole_workbook_complete": False, "runtime_eligible": False, "runtime_admitted": False,
        "imported": False, "admitted": False,
    }


def write_candidate(output: Path) -> dict[str, Any]:
    root = _root()
    target = output if output.is_absolute() else root / output
    allowed = root / BUILD_REL
    if not target.parent.exists() or target.parent.is_symlink() or target.parent.resolve() != allowed.resolve():
        raise CandidateError(f"OUTPUT_OUTSIDE_LANE_BUILD {output}")
    if target.suffix != ".json" or target.is_symlink():
        raise CandidateError(f"OUTPUT_INVALID {output}")
    candidate = build_candidate()
    data = (json.dumps(candidate, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
    try:
        with target.open("xb") as handle:
            handle.write(data)
    except FileExistsError as exc:
        raise CandidateError(f"OUTPUT_EXISTS {output}") from exc
    return {"output": str(target.relative_to(root)), "bytes": len(data), "sha256": digest(data)}


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
