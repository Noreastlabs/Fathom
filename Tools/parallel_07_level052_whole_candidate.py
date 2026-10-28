#!/usr/bin/env python3
"""Build a detached, source-linked whole Level 52 G-B-e triad candidate."""

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
STEM = "Guitar_Exercises_Section_VI_Level_52_Major_and_Minor_Triads_Root_Position_First_Inversion_Second_Inversion_Top_Three_Strings"
TXT_REL = Path("Notes/music/guitar project/TXT version") / (STEM + ".txt")
PDF_REL = Path("Notes/music/guitar project/PDF version") / (STEM + ".pdf")
BUILD_REL = Path("Build/parallel-07/2.3.1.2.1-level052-whole-r01")
TXT_BYTES = 19114
TXT_SHA256 = "6e8a5b93bf8b5b66c045ed943e6b873fe52c849da2d741f59857c6a736ea0bd3"
PDF_BYTES = 74422
PDF_SHA256 = "0cdfff4afe53df5c881e05c61908f4576c0a5d828e7440bb9ec88ebaa6fba503"
ROOTS = "CDEFGAB"
STRINGS = ("G", "B", "e")
OPEN_MIDI = {"G": 55, "B": 59, "e": 64}
PC = {"C": 0, "C#": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4,
      "F": 5, "F#": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9,
      "Bb": 10, "B": 11}
INV_NAMES = {"R": "root_position", "1": "first_inversion", "2": "second_inversion"}
INV_DEGREES = {"major": {"R": ("1", "3", "5"), "1": ("3", "5", "1"), "2": ("5", "1", "3")},
               "minor": {"R": ("1", "b3", "5"), "1": ("b3", "5", "1"), "2": ("5", "1", "b3")}}
SHAPE_HEAD = re.compile(r"^([CDEFGAB]m?) - (Root position|First inversion|Second inversion)$")
CYCLE = re.compile(r"^([CDEFGAB]m?): ((?:[R12]\(\d+-\d+-\d+\)(?: -> )?){6})$")
SWITCH = re.compile(r"^([CDEFGAB]) \((\d+), (\d+), (\d+)\) <-> ([CDEFGAB]m) \((\d+), (\d+), (\d+)\): major-minor-major-minor repeated to 8 attacks\.$")
FRET = re.compile(r"^\d+-\d+-\d+$")
PROGRESSION_KEYS = ("C-F-G-C", "G-C-D-G", "D-G-A-D", "A-D-E-A",
                    "Am-Dm-E-Am", "Em-Am-B-Em", "Dm-Gm-A-Dm", "Gm-Cm-D-Gm")
EXPECTED_COUNTS = {"shape_workouts": 420, "inversion_cycles": 84,
                   "quality_switches": 168, "patterns": 48,
                   "major_progressions": 64, "minor_progressions": 64,
                   "major_capstone": 64, "minor_capstone": 64}


class CandidateError(ValueError):
    """Pinned source, printed voicing, or output boundary failed."""


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


def _frets(text: str) -> tuple[int, int, int]:
    if FRET.fullmatch(text) is None:
        raise CandidateError(f"FRET_TRIPLE_INVALID {text}")
    result = tuple(int(part) for part in text.split("-"))
    assert len(result) == 3
    return result


def _quality(chord: str) -> str:
    return "minor" if chord.endswith("m") else "major"


def _root_name(chord: str) -> str:
    return chord.removesuffix("m")


def _shape_pitch(frets: tuple[int, int, int]) -> tuple[int, int, int]:
    return tuple((OPEN_MIDI[string] + fret) % 12 for string, fret in zip(STRINGS, frets, strict=True))


def _attack(chord: str, inv: str, frets: tuple[int, int, int], *, kind: str,
            string: str | None = None, note: str | None = None, sounded: bool = True) -> dict[str, Any]:
    return {"chord": chord, "quality": _quality(chord), "inversion": INV_NAMES[inv],
            "frets_g_b_e": list(frets), "kind": kind, "string": string,
            "tone": note, "sounded": sounded,
            "onset_q": None, "duration_q": None}


def _shape_rows(lines: list[str], pages: list[list[str]]) -> tuple[list[dict[str, Any]], dict[tuple[str, str], dict[str, Any]]]:
    shapes = []
    lookup: dict[tuple[str, str], dict[str, Any]] = {}
    for root_index, root in enumerate(ROOTS):
        heading = f"{root} MAJOR AND MINOR TRIADS"
        try:
            start = lines.index(heading)
        except ValueError as exc:
            raise CandidateError(f"TRIAD_FAMILY_MISSING {root}") from exc
        major_line = f"{root} major spelling: "
        minor_line = f"{root} minor spelling: "
        if not lines[start + 2].startswith(major_line) or not lines[start + 3].startswith(minor_line):
            raise CandidateError(f"TRIAD_SPELLING_MISSING {root}")
        spellings = {"major": lines[start + 2].removeprefix(major_line).split(),
                     "minor": lines[start + 3].removeprefix(minor_line).split()}
        if any(len(notes) != 3 or notes[0] != root for notes in spellings.values()):
            raise CandidateError(f"TRIAD_SPELLING_INVALID {root}")
        expected_third_major = (PC[root] + 4) % 12
        expected_third_minor = (PC[root] + 3) % 12
        expected_fifth = (PC[root] + 7) % 12
        for quality, third in (("major", expected_third_major), ("minor", expected_third_minor)):
            notes = spellings[quality]
            if [PC[note] for note in notes] != [PC[root], third, expected_fifth]:
                raise CandidateError(f"TRIAD_FORMULA_INVALID {root} {quality}")
        family = {"root": root, "spelling": spellings, "shapes": [],
                  "pdf_page": root_index + 3, "source_ref": f"L52-TXT1-{start + 1}"}
        for quality_index, quality in enumerate(("major", "minor")):
            label = root + ("m" if quality == "minor" else "")
            for inv_index, (inv, name) in enumerate((("R", "Root position"),
                                                     ("1", "First inversion"),
                                                     ("2", "Second inversion"))):
                head = f"{label} - {name}"
                try:
                    index = lines.index(head, start)
                except ValueError as exc:
                    raise CandidateError(f"TRIAD_SHAPE_MISSING {head}") from exc
                if (lines[index + 1].startswith("G-B-e frets: ") is False or
                    lines[index + 2].startswith("Notes:   ") is False or
                    lines[index + 3].startswith("Degrees: ") is False or
                    lines[index + 4].startswith("Fingers: ") is False or
                    lines[index + 5] != "Workout: 4 blocked attacks; arpeggio G-B-e-e-B-G. 10 attacks."):
                    raise CandidateError(f"TRIAD_SHAPE_FIELDS_INVALID {head}")
                frets = _frets(lines[index + 1].removeprefix("G-B-e frets: "))
                tones = lines[index + 2].removeprefix("Notes:   ").split()
                degrees = lines[index + 3].removeprefix("Degrees: ").split()
                fingers = lines[index + 4].removeprefix("Fingers: ").split()
                expected_order = INV_DEGREES[quality][inv]
                tone_by_degree = {"1": spellings[quality][0],
                                  "3" if quality == "major" else "b3": spellings[quality][1],
                                  "5": spellings[quality][2]}
                if (tuple(degrees) != expected_order or tones != [tone_by_degree[d] for d in degrees]
                    or len(fingers) != 3 or any(f not in ("O", "1", "2", "3", "4") for f in fingers)
                    or any((fret == 0) != (finger == "O") for fret, finger in zip(frets, fingers, strict=True))
                    or _shape_pitch(frets) != tuple(PC[tone] for tone in tones)):
                    raise CandidateError(f"TRIAD_SHAPE_MUSIC_INVALID {head}")
                attacks = [_attack(label, inv, frets, kind="blocked") for _ in range(4)]
                for string in ("G", "B", "e", "e", "B", "G"):
                    slot = STRINGS.index(string)
                    attacks.append(_attack(label, inv, frets, kind="arpeggio", string=string,
                                           note=tones[slot]))
                shape = {"root": root, "chord": label, "quality": quality,
                         "inversion": INV_NAMES[inv], "inversion_code": inv,
                         "frets_g_b_e": list(frets), "tones_g_b_e": tones,
                         "degrees_g_b_e": degrees, "fingers_g_b_e": fingers,
                         "family_spelling": spellings,
                         "attack_count": 10, "attacks": attacks,
                         "silent_formation_before_first_attack": True,
                         "raw_lines": lines[index:index + 6],
                         "source_ref": f"L52-TXT1-{index + 1}-{index + 6}",
                         "pdf_page": root_index + 3}
                shapes.append(shape)
                family["shapes"].append(shape)
                lookup[(label, inv)] = shape
        if lines[start + 42] != "Page workload: 6 shapes x 10 attacks = 60 attacks.":
            raise CandidateError(f"TRIAD_PAGE_WORKLOAD_INVALID {root}")
        page = pages[root_index + 2]
        if (page[1] != f"{root} major and {root} minor triads on G-B-e"
            or page[2] != f"{root} MAJOR / {root} MINOR  |  60 ATTACKS"):
            raise CandidateError(f"PDF_TRIAD_PAGE_HEADING_MISMATCH {root}")
        pdf_cards = []
        for i, line in enumerate(page):
            if line == "G-B-e" and i + 7 < len(page) and FRET.fullmatch(page[i + 1]):
                if page[i + 2] != "NOTES" or page[i + 4] != "DEG" or page[i + 6] != "FING":
                    raise CandidateError(f"PDF_TRIAD_CARD_LAYOUT_INVALID {root}")
                pdf_cards.append((page[i + 1], page[i + 3].split("-"), page[i + 5].split("-"),
                                  page[i + 7].split("-")))
        order = [family["shapes"][offset] for offset in (0, 3, 1, 4, 2, 5)]
        expected_pdf = [("-".join(str(n) for n in shape["frets_g_b_e"]),
                         shape["tones_g_b_e"], shape["degrees_g_b_e"], shape["fingers_g_b_e"])
                        for shape in order]
        if pdf_cards != expected_pdf:
            raise CandidateError(f"PDF_TRIAD_SHAPES_MISMATCH {root}")
    if len(shapes) != 42 or len(lookup) != 42:
        raise CandidateError("TRIAD_SHAPE_COUNT_INVALID")
    return shapes, lookup


def _cycles(lines: list[str], page: list[str], lookup: dict[tuple[str, str], dict[str, Any]]) -> list[dict[str, Any]]:
    first = lines.index("MODULE D - NECK-ORDER INVERSION CYCLES")
    last = lines.index("MODULE E - SAME-INVERSION MAJOR/MINOR QUALITY SWITCHES")
    cycles = []
    for index in range(first, last):
        match = CYCLE.fullmatch(lines[index])
        if match is None:
            continue
        chord = match.group(1)
        tokens = re.findall(r"([R12])\((\d+-\d+-\d+)\)", match.group(2))
        if len(tokens) != 6 or tokens != list(reversed(tokens)):
            raise CandidateError(f"INVERSION_CYCLE_ORDER_INVALID {chord}")
        attacks = []
        for inv, fret_text in tokens:
            frets = _frets(fret_text)
            shape = lookup.get((chord, inv))
            if shape is None or frets != tuple(shape["frets_g_b_e"]):
                raise CandidateError(f"INVERSION_CYCLE_SHAPE_MISMATCH {chord} {inv}")
            attacks.append(_attack(chord, inv, frets, kind="blocked"))
        pdf_frets = " | ".join(fret for _, fret in tokens)
        pdf_inv = "Inv " + "-".join(inv for inv, _ in tokens)
        if pdf_frets not in page or pdf_inv not in page:
            raise CandidateError(f"PDF_INVERSION_CYCLE_MISMATCH {chord}")
        if lines[index + 1] != "Six blocked attacks. Name every inversion before playing.":
            raise CandidateError(f"INVERSION_CYCLE_INSTRUCTION_MISSING {chord}")
        cycles.append({"chord": chord, "quality": _quality(chord),
                       "attack_count": 6, "attacks": attacks, "raw_line": lines[index],
                       "source_refs": [f"L52-TXT1-{index + 1}-{index + 2}", "L52-PDF1-p10"]})
    if len(cycles) != 14:
        raise CandidateError("INVERSION_CYCLE_COUNT_INVALID")
    return cycles


def _switches(lines: list[str], pages: list[list[str]], lookup: dict[tuple[str, str], dict[str, Any]]) -> list[dict[str, Any]]:
    first = lines.index("MODULE E - SAME-INVERSION MAJOR/MINOR QUALITY SWITCHES")
    last = lines.index("MODULE F - BLOCKED AND ARPEGGIATED PATTERNS")
    switches = []
    inv = None
    for index in range(first, last):
        if lines[index] in ("ROOT POSITION", "FIRST INVERSION", "SECOND INVERSION"):
            inv = {"ROOT POSITION": "R", "FIRST INVERSION": "1", "SECOND INVERSION": "2"}[lines[index]]
        match = SWITCH.fullmatch(lines[index])
        if match is None:
            continue
        if inv is None or match.group(5) != match.group(1) + "m":
            raise CandidateError("QUALITY_SWITCH_HEADING_INVALID")
        major, minor = match.group(1), match.group(5)
        major_frets = tuple(map(int, match.group(2, 3, 4)))
        minor_frets = tuple(map(int, match.group(6, 7, 8)))
        expected_major = tuple(lookup[(major, inv)]["frets_g_b_e"])
        expected_minor = tuple(lookup[(minor, inv)]["frets_g_b_e"])
        alternate = major == "C" and inv == "2" and major_frets == (12, 13, 12)
        if (minor_frets != expected_minor or (major_frets != expected_major and not alternate)
            or sum(a != b for a, b in zip(major_frets, minor_frets, strict=True)) != 1
            or max(abs(a - b) for a, b in zip(major_frets, minor_frets, strict=True)) != 1):
            raise CandidateError(f"QUALITY_SWITCH_VOICING_INVALID {major} {inv}")
        major_pcs = sorted(_shape_pitch(major_frets))
        minor_pcs = sorted(_shape_pitch(minor_frets))
        if (major_pcs != sorted(PC[t] for t in lookup[(major, inv)]["tones_g_b_e"])
            or minor_pcs != sorted(PC[t] for t in lookup[(minor, inv)]["tones_g_b_e"])):
            raise CandidateError(f"QUALITY_SWITCH_PITCH_INVALID {major} {inv}")
        moving = [string for string, a, b in zip(STRINGS, major_frets, minor_frets, strict=True) if a != b]
        if moving != [{"R": "B", "1": "G", "2": "e"}[inv]]:
            raise CandidateError(f"QUALITY_SWITCH_THIRD_STRING_INVALID {major} {inv}")
        page_number = {"R": 11, "1": 12, "2": 13}[inv]
        page = pages[page_number - 1]
        pdf_header = f"{major} <-> {minor}"
        if (pdf_header not in page or f"MAJ|{'-'.join(map(str, major_frets))}|" not in page
            or f"MIN|{'-'.join(map(str, minor_frets))}|" not in page):
            raise CandidateError(f"PDF_QUALITY_SWITCH_MISMATCH {major} {inv}")
        attacks = [_attack(major if n % 2 == 0 else minor, inv,
                           major_frets if n % 2 == 0 else minor_frets, kind="blocked")
                   for n in range(8)]
        switches.append({"root": major, "inversion": INV_NAMES[inv], "moving_string": moving[0],
                         "major_frets_g_b_e": list(major_frets), "minor_frets_g_b_e": list(minor_frets),
                         "alternate_octave": alternate, "attack_count": 8, "attacks": attacks,
                         "raw_line": lines[index], "source_refs": [f"L52-TXT1-{index + 1}",
                                                                f"L52-PDF1-p{page_number}"]})
    if len(switches) != 21 or sum(s["alternate_octave"] for s in switches) != 1:
        raise CandidateError("QUALITY_SWITCH_COUNT_OR_ALTERNATE_INVALID")
    return switches


def _patterns(lines: list[str], page: list[str], lookup: dict[tuple[str, str], dict[str, Any]]) -> list[dict[str, Any]]:
    first = lines.index("MODULE F - BLOCKED AND ARPEGGIATED PATTERNS")
    last = lines.index("MODULE G - NEAREST-INVERSION MAJOR I-IV-V-I PROGRESSIONS")
    heads = [(i, re.fullmatch(r"F([1-6])\. (.+) - ([CDEFGAB]) (major|minor) (root position|first inversion|second inversion)", lines[i]))
             for i in range(first, last)]
    heads = [(i, match) for i, match in heads if match]
    if len(heads) != 6:
        raise CandidateError("PATTERN_HEADINGS_INVALID")
    patterns = []
    for ordinal, (index, match) in enumerate(heads, 1):
        assert match is not None
        if int(match.group(1)) != ordinal or lines[index + 2] != "8 attacks":
            raise CandidateError(f"PATTERN_COUNT_INVALID F{ordinal}")
        root, quality = match.group(3), match.group(4)
        chord = root + ("m" if quality == "minor" else "")
        inv = {"root position": "R", "first inversion": "1", "second inversion": "2"}[match.group(5)]
        shape = lookup[(chord, inv)]
        raw_pattern = lines[index + 1]
        if ordinal == 1:
            tokens = ["BLOCK"] * 8
        elif ordinal == 6:
            tokens = raw_pattern.replace("|", " ").split()
        else:
            body = raw_pattern
            if ordinal == 5:
                tokens = [item for part in body.split("|") for item in (
                    [part.strip()] if part.strip() == "BLOCK" else part.strip().split("-"))]
            else:
                tokens = [item for part in body.split("|") for item in part.strip().split("-")]
        if len(tokens) != 8 or any(token not in ("BLOCK", "CHORD", "mute", "G", "B", "e") for token in tokens):
            raise CandidateError(f"PATTERN_ATTACK_SEQUENCE_INVALID F{ordinal}")
        if ordinal == 6 and tokens != ["CHORD", "mute"] * 4:
            raise CandidateError("RELEASE_BACKBEATS_INVALID")
        if ordinal == 1 and raw_pattern != "Chord attacks: 1 2 3 4 | 1 2 3 4":
            raise CandidateError("BLOCKED_QUARTERS_INVALID")
        attacks = []
        for token in tokens:
            if token == "mute":
                attacks.append(_attack(chord, inv, tuple(shape["frets_g_b_e"]),
                                       kind="muted_backbeat", sounded=False))
            elif token in ("BLOCK", "CHORD"):
                attacks.append(_attack(chord, inv, tuple(shape["frets_g_b_e"]), kind="blocked"))
            else:
                slot = STRINGS.index(token)
                attacks.append(_attack(chord, inv, tuple(shape["frets_g_b_e"]),
                                       kind="arpeggio", string=token, note=shape["tones_g_b_e"][slot]))
        if (f"F{ordinal}. {match.group(2)}" not in page or raw_pattern not in page
            or f"{root} {quality} {match.group(5)}" not in page):
            raise CandidateError(f"PDF_PATTERN_MISMATCH F{ordinal}")
        patterns.append({"ordinal": ordinal, "name": match.group(2), "chord": chord,
                         "inversion": INV_NAMES[inv], "frets_g_b_e": shape["frets_g_b_e"],
                         "attack_count": 8, "attacks": attacks, "raw_lines": lines[index:index + 3],
                         "source_refs": [f"L52-TXT1-{index + 1}-{index + 3}", "L52-PDF1-p14"]})
    return patterns


def _split_pipe(line: str, prefix: str, count: int) -> list[str]:
    if not line.startswith(prefix):
        raise CandidateError(f"PIPE_PREFIX_INVALID {prefix}")
    pieces = [part.strip() for part in line.removeprefix(prefix).split("|")]
    if len(pieces) != count:
        raise CandidateError(f"PIPE_COUNT_INVALID {prefix}")
    return pieces


def _pdf_grid(page: list[str], expected: list[tuple[str, str, str]], label: str) -> dict[str, str]:
    grid: dict[str, str] = {}
    for prefix in ("Cnt", "Chd", "Inv", "GBe", "Str"):
        rows = [line for line in page if line.startswith(prefix + "|")]
        if len(rows) != 1:
            raise CandidateError(f"PDF_GRID_ROW_COUNT_INVALID {label} {prefix}")
        grid[prefix] = rows[0]
    chords = re.findall(r"[A-G]m?", grid["Chd"].split("|", 1)[1])
    inversions = re.findall(r"[R12]", grid["Inv"].split("|", 1)[1])
    frets = re.findall(r"\d+-\d+-\d+", grid["GBe"].split("|", 1)[1])
    counts = re.findall(r"[1-4]", grid["Cnt"].split("|", 1)[1])
    strokes = re.findall(r"[DU]", grid["Str"].split("|", 1)[1])
    if (list(zip(chords, inversions, frets, strict=False)) != expected or
        counts != [str(i % 4 + 1) for i in range(16)] or strokes != ["D"] * 16):
        raise CandidateError(f"PDF_GRID_MISMATCH {label}")
    return grid


def _progressions(lines: list[str], pages: list[list[str]], lookup: dict[tuple[str, str], dict[str, Any]],
                  *, minor: bool) -> list[dict[str, Any]]:
    heading = ("MODULE H - NEAREST-INVERSION MINOR i-iv-V-i PROGRESSIONS" if minor else
               "MODULE G - NEAREST-INVERSION MAJOR I-IV-V-I PROGRESSIONS")
    next_heading = "MODULE I - SIXTEEN-BAR CAPSTONES" if minor else "MODULE H - NEAREST-INVERSION MINOR i-iv-V-i PROGRESSIONS"
    first, last = lines.index(heading), lines.index(next_heading)
    page_number = 16 if minor else 15
    page = pages[page_number - 1]
    progressions = []
    keys = PROGRESSION_KEYS[4:] if minor else PROGRESSION_KEYS[:4]
    for key in keys:
        try:
            index = lines.index(key, first, last)
        except ValueError as exc:
            raise CandidateError(f"PROGRESSION_MISSING {key}") from exc
        chords = _split_pipe(lines[index + 1], "Chords: ", 4)
        inversions = _split_pipe(lines[index + 2], "Inversions: ", 4)
        fret_texts = _split_pipe(lines[index + 3], "G-B-e: ", 4)
        if (chords != key.split("-") or any(inv not in INV_NAMES for inv in inversions)
            or lines[index + 4] != "Repeat four times, one chord per beat. 16 attacks."):
            raise CandidateError(f"PROGRESSION_STRUCTURE_INVALID {key}")
        quartet = []
        for chord, inv, fret_text in zip(chords, inversions, fret_texts, strict=True):
            shape = lookup.get((chord, inv))
            if shape is None or list(_frets(fret_text)) != shape["frets_g_b_e"]:
                raise CandidateError(f"PROGRESSION_VOICING_INVALID {key} {chord}")
            quartet.append((chord, inv, fret_text))
        if (key not in page or f"GBe|{' | '.join(fret_texts)} |" not in page):
            raise CandidateError(f"PDF_PROGRESSION_SUMMARY_MISMATCH {key}")
        attacks = [_attack(chord, inv, _frets(fret_text), kind="blocked")
                   for _ in range(4) for chord, inv, fret_text in quartet]
        progressions.append({"key_route": key, "chords": chords, "inversions": inversions,
                             "frets_g_b_e": [list(_frets(text)) for text in fret_texts],
                             "attack_count": 16, "attacks": attacks,
                             "grid_frets": fret_texts * 4,
                             "raw_lines": lines[index:index + 5],
                             "source_refs": [f"L52-TXT1-{index + 1}-{index + 5}",
                                             f"L52-PDF1-p{page_number}"]})
    if len(progressions) != 4:
        raise CandidateError("PROGRESSION_COUNT_INVALID")
    # Each PDF card prints one four-chord summary and one sixteen-attack grid.
    by_prefix = {prefix: [row for row in page if row.startswith(prefix + "|")]
                 for prefix in ("Cnt", "Chd", "Inv", "GBe", "Str")}
    if any(len(by_prefix[prefix]) != (8 if prefix in ("Chd", "Inv", "GBe") else 4)
           for prefix in by_prefix):
        raise CandidateError("PDF_PROGRESSION_GRID_COUNT_INVALID")
    for i, progression in enumerate(progressions):
        chords = progression["chords"]
        invs = progression["inversions"]
        frets = ["-".join(map(str, part)) for part in progression["frets_g_b_e"]]
        if (re.findall(r"[A-G]m?", by_prefix["Chd"][2 * i].split("|", 1)[1]) != chords
            or re.findall(r"[R12]", by_prefix["Inv"][2 * i].split("|", 1)[1]) != invs
            or re.findall(r"\d+-\d+-\d+", by_prefix["GBe"][2 * i]) != frets
            or re.findall(r"[A-G]m?", by_prefix["Chd"][2 * i + 1].split("|", 1)[1]) != chords * 4
            or re.findall(r"[R12]", by_prefix["Inv"][2 * i + 1].split("|", 1)[1]) != invs * 4
            or re.findall(r"\d+-\d+-\d+", by_prefix["GBe"][2 * i + 1]) != frets * 4
            or re.findall(r"[1-4]", by_prefix["Cnt"][i]) != [str(j % 4 + 1) for j in range(16)]
            or re.findall(r"[DU]", by_prefix["Str"][i]) != ["D"] * 16):
            raise CandidateError(f"PDF_PROGRESSION_GRID_MISMATCH {progression['key_route']}")
    return progressions


def _capstone(lines: list[str], page: list[str], lookup: dict[tuple[str, str], dict[str, Any]],
              *, minor: bool) -> dict[str, Any]:
    first = lines.index("MINOR CAPSTONE" if minor else "MAJOR CAPSTONE")
    last = lines.index("EAR TRAINING, ERROR REPAIR, AND MASTERY") if minor else lines.index("MINOR CAPSTONE")
    bars = []
    for group in range(4):
        label = f"Bars {group * 4 + 1}-{group * 4 + 4}: "
        found = [(i, line) for i, line in enumerate(lines[first:last], first) if line.startswith(label)]
        if len(found) != 1:
            raise CandidateError(f"CAPSTONE_BLOCK_MISSING {group + 1}")
        index, line = found[0]
        chords = _split_pipe(line, label, 4)
        inversions = _split_pipe(lines[index + 1], "Inversions: ", 4)
        shapes = _split_pipe(lines[index + 2], "Shapes: ", 4)
        expected_route = PROGRESSION_KEYS[group + (4 if minor else 0)].split("-")
        if chords != expected_route:
            raise CandidateError(f"CAPSTONE_CHORD_ROUTE_INVALID {group + 1}")
        for chord, inv, fret_text in zip(chords, inversions, shapes, strict=True):
            shape = lookup.get((chord, inv))
            if shape is None or shape["frets_g_b_e"] != list(_frets(fret_text)):
                raise CandidateError(f"CAPSTONE_VOICING_INVALID {chord} {group + 1}")
        if (" | ".join(chords) not in page or " | ".join(inversions) not in page
            or " | ".join(shapes) not in page):
            raise CandidateError(f"PDF_CAPSTONE_TABLE_MISMATCH {group + 1}")
        bars.extend({"bar": group * 4 + offset + 1, "chord": chord, "inversion": inv,
                     "frets_g_b_e": list(_frets(fret_text)),
                     "attacks": [_attack(chord, inv, _frets(fret_text), kind="blocked") for _ in range(4)],
                     "source_ref": f"L52-TXT1-{index + 1}-{index + 3}"}
                    for offset, (chord, inv, fret_text) in enumerate(zip(chords, inversions, shapes, strict=True)))
    if lines[last - 1] != "Four quarter-note attacks per bar. 64 attacks." and (
            "Four quarter-note attacks per bar. 64 attacks." not in lines[first:last]):
        raise CandidateError("CAPSTONE_ATTACK_COUNT_MISSING")
    expected = [(bar["chord"], bar["inversion"], "-".join(map(str, bar["frets_g_b_e"]))) for bar in bars]
    grid = _pdf_grid(page, expected, "minor capstone" if minor else "major capstone")
    return {"quality": "minor" if minor else "major", "bars": bars,
            "attack_count": 64, "pdf_grid_raw_rows": grid,
            "pdf_performance_passes_text": "\n".join(page[page.index("Four performance passes"):page.index("Capstone grid")]),
            "source_ref": f"L52-TXT1-{first + 1}-{last}", "pdf_page": 18 if minor else 17}


def _silent_tasks(shapes: list[dict[str, Any]], lines: list[str], page19: list[str], page20: list[str]) -> dict[str, Any]:
    formations = [{"root": shape["root"], "quality": shape["quality"],
                   "inversion": shape["inversion"], "degrees_g_b_e": shape["degrees_g_b_e"],
                   "frets_g_b_e": shape["frets_g_b_e"], "sound_attack": False,
                   "source_ref": shape["source_ref"]}
                  for shape in shapes]
    if (len(formations) != 42 or "42 silent landings" not in page20
        or "Complete all 42" not in " ".join(page19)
        or "At least 18 of 21 shapes per quality are formed correctly on the first attempt." not in page19):
        raise CandidateError("SILENT_FORMATION_OR_CRITERION_INVALID")
    source_tail = lines[lines.index("EAR TRAINING, ERROR REPAIR, AND MASTERY"):]
    if ("MASTERY GATE: spell and play all natural-root major and minor triads; identify all inversions; complete all shape workouts, quality switches, progressions, capstones, and random-root silent formations on two separate days without pain or persistent tension." not in source_tail):
        raise CandidateError("TXT_MASTERY_GATE_MISSING")
    return {"formations": formations, "silent_formation_count": 42,
            "pdf_first_attempt_threshold": {"minimum_correct_per_quality": 18, "total_per_quality": 21},
            "txt_mastery_separate_days": 2, "counted_in_attacks": False,
            "txt_raw_lines": source_tail, "pdf_page19_raw_lines": page19,
            "pdf_page20_raw_lines": page20,
            "source_refs": ["L52-TXT1-501-511", "L52-PDF1-p19-20"]}


def build_candidate(*, txt_data: bytes | None = None, pdf_data: bytes | None = None) -> dict[str, Any]:
    root = _root()
    txt_data = _source_bytes(root, TXT_REL) if txt_data is None else txt_data
    pdf_data = _source_bytes(root, PDF_REL) if pdf_data is None else pdf_data
    _verify(txt_data, TXT_BYTES, TXT_SHA256, "L52-TXT")
    _verify(pdf_data, PDF_BYTES, PDF_SHA256, "L52-PDF")
    try:
        lines = txt_data.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise CandidateError("TXT_ENCODING_INVALID") from exc
    if (len(lines) != 511 or lines[:2] != ["GUITAR EXERCISES - SECTION VI, LEVEL 52",
            "MAJOR AND MINOR TRIADS - ROOT POSITION, FIRST INVERSION, SECOND INVERSION - TOP THREE STRINGS"]):
        raise CandidateError("TXT_TITLE_OR_LINE_COUNT_INVALID")
    pages = _pdf_pages(pdf_data)
    if (any(page[0] != "Guitar Exercises - Section VI, Level 52" for page in pages)
        or pages[0][2] != "G-B-e STRING SET  |  976 ATTACKS + 42 SILENT LANDINGS"):
        raise CandidateError("PDF_TITLE_OR_TOTAL_INVALID")
    shapes, lookup = _shape_rows(lines, pages)
    cycles = _cycles(lines, pages[9], lookup)
    switches = _switches(lines, pages, lookup)
    patterns = _patterns(lines, pages[13], lookup)
    major_progressions = _progressions(lines, pages, lookup, minor=False)
    minor_progressions = _progressions(lines, pages, lookup, minor=True)
    major_capstone = _capstone(lines, pages[16], lookup, minor=False)
    minor_capstone = _capstone(lines, pages[17], lookup, minor=True)
    silent = _silent_tasks(shapes, lines, pages[18], pages[19])
    modules = {
        "shape_workouts": {"shapes": shapes, "attack_count": sum(s["attack_count"] for s in shapes),
                           "source_refs": ["L52-TXT1-18-338", "L52-PDF1-p3-9"]},
        "inversion_cycles": {"cycles": cycles, "attack_count": sum(c["attack_count"] for c in cycles),
                             "source_refs": ["L52-TXT1-339-370", "L52-PDF1-p10"]},
        "quality_switches": {"switches": switches, "attack_count": sum(s["attack_count"] for s in switches),
                             "source_refs": ["L52-TXT1-371-398", "L52-PDF1-p11-13"]},
        "patterns": {"patterns": patterns, "attack_count": sum(p["attack_count"] for p in patterns),
                     "source_refs": ["L52-TXT1-399-420", "L52-PDF1-p14"]},
        "major_progressions": {"progressions": major_progressions,
                               "attack_count": sum(p["attack_count"] for p in major_progressions),
                               "source_refs": ["L52-TXT1-421-444", "L52-PDF1-p15"]},
        "minor_progressions": {"progressions": minor_progressions,
                               "attack_count": sum(p["attack_count"] for p in minor_progressions),
                               "source_refs": ["L52-TXT1-445-468", "L52-PDF1-p16"]},
        "major_capstone": major_capstone, "minor_capstone": minor_capstone,
        "silent_and_ear_tasks": silent,
    }
    counts = {key: modules[key]["attack_count"] for key in EXPECTED_COUNTS}
    if counts != EXPECTED_COUNTS or sum(counts.values()) != 976:
        raise CandidateError(f"SOUNDED_WORKLOAD_COUNT_INVALID {counts}")
    if ("COMPLETE SOUNDED WORKLOAD: 976 attacks plus 42 silent triad formations." not in lines
        or len(silent["formations"]) != 42):
        raise CandidateError("SOURCE_TOTAL_OR_SILENT_COUNT_INVALID")
    return {
        "schema": "fathom-level052-whole-detached-candidate-v1", "wbs_id": "2.3.1.2.1",
        "level": 52,
        "source": {"txt_path": TXT_REL.as_posix(), "txt_bytes": TXT_BYTES, "txt_sha256": TXT_SHA256,
                   "pdf_path": PDF_REL.as_posix(), "pdf_bytes": PDF_BYTES, "pdf_sha256": PDF_SHA256,
                   "pdf_pages": 20},
        "strings_low_to_high": list(STRINGS), "natural_roots": list(ROOTS),
        "inversion_degree_orders": INV_DEGREES,
        "quality_string_by_inversion": {"R": "B", "1": "G", "2": "e"},
        "modules": modules, "module_attack_counts": counts,
        "sounded_workload_attack_count": 976, "silent_formation_count": 42,
        "authored_alternatives": [{"chord": "C", "inversion": "second_inversion",
                                   "module_a_and_d_frets_g_b_e": [0, 1, 0],
                                   "module_e_quality_switch_frets_g_b_e": [12, 13, 12],
                                   "relationship": "same C-major inversion one octave higher"}],
        "instructions": {"txt_full_text": "\n".join(lines) + "\n",
                         "pdf_pages_text": ["\n".join(page) for page in pages],
                         "pdf_only_performance_passes_counted": False,
                         "source_refs": ["L52-TXT1-1-511", "L52-PDF1-p1-20"]},
        "canonical_item_id": None, "canonical_variant_id": None,
        "onset_q": None, "duration_q": None, "fixed_bpm": None, "note_per_click": None,
        "pending": ["Curriculum/musical review", "canonical identity allocation and admission",
                    "runtime note timing and performed audio", "human mastery and silent-formation observation"],
        "whole_workbook_complete": False, "runtime_eligible": False,
        "runtime_admitted": False, "imported": False, "admitted": False,
    }


def write_candidate(output: Path) -> dict[str, Any]:
    root = _root()
    target = output if output.is_absolute() else root / output
    allowed = root / BUILD_REL
    if not target.parent.exists() or target.parent.is_symlink() or target.parent.resolve() != allowed.resolve():
        raise CandidateError(f"OUTPUT_OUTSIDE_LANE_BUILD {output}")
    if target.suffix != ".json" or target.is_symlink():
        raise CandidateError(f"OUTPUT_INVALID {output}")
    data = (json.dumps(build_candidate(), indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode()
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
