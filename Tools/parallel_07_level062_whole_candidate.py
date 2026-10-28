#!/usr/bin/env python3
"""Build the detached whole-source Section VII Level 62 candidate."""

from __future__ import annotations

import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path
import re

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
STEM = "Guitar_Exercises_Section_VII_Level_62_Diagonal_Arpeggio_Connections_String_Skipping_Position_Shifts_and_Full_Neck_Chord_Tone_Motif_Development"
TXT = Path("Notes/music/guitar project/TXT version") / (STEM + ".txt")
PDF = Path("Notes/music/guitar project/PDF version") / (STEM + ".pdf")
MAP = Path("Results/parallel-01/exercises/inventory/20260922T180500Z-2.3-curriculum-v1-source-inventory-evidence/curriculum-source-map.json")
OUT = Path("Build/parallel-07/2.3.1.2.1-level062-whole-r01")
PINS = {"txt": (39791, "39fca1f21a76fa206bad933fae6d5c2464bf21f2ab359e9bc6fcb8d67030eb8b"),
        "pdf": (54869, "b658be4914875592e4765c942afec45abd8f3d6459d78de378a148e400fca836")}
EXPECTED = {"A": 64, "B": 96, "C": 64, "D": 64, "E": 96,
            "F": 72, "G": 72, "H": 68, "I": 128, "J": 64}
CELL_COUNTS = {"A": 8, "B": 6, "C": 8, "D": 8, "E": 8,
               "F": 6, "G": 6, "H": 8, "I": 8, "J": 5}
NOTES = re.compile(r"[A-G](?:#|b)?")
CHORD = re.compile(r"[A-G](?:#|b)?(?:maj7|m7b5|m7|7)")
OPEN = {"E": 40, "A": 45, "D": 50, "G": 55, "B": 59, "e": 64}
PC = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3,
      "E": 4, "E#": 5, "F": 5, "F#": 6, "Gb": 6, "G": 7,
      "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10,
      "B": 11, "B#": 0, "Cb": 11}
ROLE = {"R": 0, "b9": 1, "9": 2, "#9": 3, "b3": 3, "3": 4,
        "11": 5, "b5": 6, "5": 7, "13": 9, "b7": 10, "7": 11}
BRIDGES = {"ii -> V bridge": ("Dm7", "G7"),
           "V -> I bridge": ("G7", "Cmaj7"),
           "I -> vi bridge": ("Cmaj7", "Am7"),
           "iiø -> V bridge": ("Bm7b5", "E7"),
           "V -> i bridge": ("E7", "Am7")}


class CandidateError(ValueError):
    """Pinned identity, tab integrity, count, or output boundary failed."""


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read(root: Path, path: Path, pin: tuple[int, str]) -> bytes:
    target = root / path
    if target.is_symlink() or not target.is_file():
        raise CandidateError(f"SOURCE_PATH_INVALID {path}")
    data = target.read_bytes()
    if (len(data), sha(data)) != pin:
        raise CandidateError(f"PINNED_INPUT_DRIFT {path}")
    return data


def _map(root: Path) -> dict:
    data = json.loads((root / MAP).read_text())
    row = next((r for r in data["rows"] if r["level"] == 62), None)
    if row is None or any(row[k] != value for k, value in {
            "section": "VII", "wbs_owner": "2.3.1.2.1", "txt_path": str(TXT),
            "pdf_path": str(PDF), "txt_bytes": PINS["txt"][0],
            "pdf_bytes": PINS["pdf"][0], "txt_sha256": PINS["txt"][1],
            "pdf_sha256": PINS["pdf"][1], "pair_status": "exact_stem_pair",
            "conversion_status": "not_converted", "imported": False,
            "admitted": False, "stable_ids_assigned": False}.items()):
        raise CandidateError("SOURCE_MAP_IDENTITY_OR_STATUS_DRIFT")
    return row


def _page_lines(data: bytes) -> list[list[str]]:
    reader = PdfReader(BytesIO(data))
    if len(reader.pages) != 20:
        raise CandidateError("PDF_PAGE_COUNT_INVALID")
    return [page.extract_text().splitlines() for page in reader.pages]


def _module_sections(lines: list[str]) -> dict[str, list[tuple[int, int]]]:
    heads = [(i, re.match(r"MODULE ([A-J]) -", line).group(1))
             for i, line in enumerate(lines) if re.match(r"MODULE ([A-J]) -", line)]
    if [letter for _, letter in heads] != list("ABCDEFGHIJ")[:9] + ["I", "J"]:
        raise CandidateError("MODULE_SEQUENCE_INVALID")
    sections: dict[str, list[tuple[int, int]]] = {letter: [] for letter in EXPECTED}
    stop = lines.index("PRACTICE PROGRESSION, ERROR REPAIR, AND MASTERY")
    for pos, (start, letter) in enumerate(heads):
        end = heads[pos + 1][0] if pos + 1 < len(heads) else stop
        sections[letter].append((start, end))
    return sections


def _source_chords(module: str, heading: str, bar_count: int) -> list[str]:
    if module == "A":
        return ["C" if heading.startswith("C major") else "A"] * bar_count
    if module in "BCDE":
        match = CHORD.match(heading)
        if match is None:
            raise CandidateError(f"CHORD_HEADING_INVALID {heading}")
        return [match.group()] * bar_count
    if module in "FG":
        chords = CHORD.findall(heading)
    elif module == "H":
        chords = ["Dm7", "G7", "Cmaj7", "Cmaj7"]
    elif module == "I":
        chords = CHORD.findall(heading)
    else:
        chords = list(BRIDGES.get(heading, ()))
    if len(chords) != bar_count:
        raise CandidateError(f"CHORD_BAR_COUNT_INVALID {module} {heading}")
    return chords


def _parse_grid(lines: list[str], i: int, module: str, pages: list[list[str]]) -> dict:
    heading = lines[i - 1] if module in "FGIJ" else lines[i - 2]
    direction = None if module in "FGIJ" else lines[i - 1]
    nte = lines[i]
    rol = lines[i + 1]
    if not rol.startswith("Rol|"):
        raise CandidateError(f"ROLE_ROW_MISSING {i + 1}")
    note_bars = [s for s in nte[4:].split("|") if s]
    role_bars = [s for s in rol[4:].split("|") if s]
    if len(note_bars) != len(role_bars):
        raise CandidateError("ROLE_BAR_COUNT_INVALID")
    chords = _source_chords(module, heading, len(note_bars))
    tab: dict[str, list[str]] = {}
    for line in lines[i + 2:i + 8]:
        match = re.fullmatch(r"  ([eBGDAE])\|(.*)", line)
        if match is None or match.group(1) in tab:
            raise CandidateError(f"TAB_STRING_ROW_INVALID {i + 1}")
        tab[match.group(1)] = [s for s in match.group(2).split("|") if s]
    if set(tab) != set(OPEN):
        raise CandidateError("TAB_STRING_SET_INVALID")
    events = []
    for bar, (nseg, rseg) in enumerate(zip(note_bars, role_bars, strict=True), 1):
        if len(nseg) != len(rseg) or any(len(parts) != len(note_bars) or len(parts[bar - 1]) != len(nseg)
                                          for parts in tab.values()):
            raise CandidateError(f"TAB_BAR_GEOMETRY_INVALID {i + 1} {bar}")
        matches = list(NOTES.finditer(nseg))
        starts = [m.start() for m in matches]
        frets = {}
        for string, bars in tab.items():
            for match in re.finditer(r"\d+", bars[bar - 1]):
                if match.start() in frets:
                    raise CandidateError("MULTIPLE_TAB_CONTACTS_PER_SLOT")
                frets[match.start()] = (string, int(match.group()))
        if sorted(frets) != starts:
            raise CandidateError(f"TAB_NOTE_ALIGNMENT_INVALID {i + 1} {bar}")
        chord = chords[bar - 1]
        root = NOTES.match(chord).group()
        for slot, (match, end) in enumerate(zip(matches, starts[1:] + [len(nseg)], strict=True), 1):
            note = match.group()
            role = rseg[match.start():end].replace(">", "").replace("-", "")
            string, fret = frets[match.start()]
            if not 0 <= fret <= 20 or (OPEN[string] + fret) % 12 != PC[note]:
                raise CandidateError(f"TAB_PITCH_INVALID {i + 1} {bar}:{slot}")
            if role != "app" and (PC[root] + ROLE.get(role, 999)) % 12 != PC[note]:
                raise CandidateError(f"CHORD_ROLE_INVALID {i + 1} {bar}:{slot}")
            events.append({"bar": bar, "slot": slot, "chord": chord, "note": note,
                           "role": role, "string": string, "fret": fret,
                           "sounded": True, "onset_q": None, "duration_q": None})
    pdf_page = next((n for n, page in enumerate(pages, 1) if nte in page), 19 if module == "J" else None)
    if pdf_page is None:
        raise CandidateError(f"PDF_GRID_MISSING {i + 1}")
    if module != "J" and any(line not in pages[pdf_page - 1] for line in lines[i:i + 8]):
        raise CandidateError(f"PDF_GRID_MISMATCH {i + 1}")
    return {"heading": heading, "direction": direction, "chords_by_bar": chords,
            "events": events, "tone_count": len(events), "raw_lines": lines[i:i + 8],
            "source_ref": f"L62-TXT1-{i + 1}-{i + 8}", "pdf_page": pdf_page,
            "pdf_grid_status": "summary_only" if module == "J" else "exact_row_parity"}


def _recoveries(lines: list[str], pages: list[list[str]], section: tuple[int, int]) -> list[dict]:
    start, end = section
    found = []
    pattern = re.compile(r"^([A-G](?:#|b)?(?:maj7|m7b5|m7|7)): ([A-G](?:#|b)?) B(\d+) -> ([A-G](?:#|b)?) B(\d+)   ([#b]?[0-9]+|R) -> ([#b]?[0-9]+|R)$")
    for i in range(start, end):
        match = pattern.fullmatch(lines[i])
        if match is None:
            continue
        chord, first, f1, second, f2, r1, r2 = match.groups()
        root = NOTES.match(chord).group()
        for note, fret, role in ((first, int(f1), r1), (second, int(f2), r2)):
            if (OPEN["B"] + fret) % 12 != PC[note] or (PC[root] + ROLE[role]) % 12 != PC[note]:
                raise CandidateError(f"RECOVERY_PITCH_OR_ROLE_INVALID {i + 1}")
        if f"{chord}: {first} -> {second}" not in pages[18]:
            raise CandidateError(f"PDF_RECOVERY_SUMMARY_MISSING {i + 1}")
        events = [{"chord": chord, "note": note, "role": role, "string": "B", "fret": int(fret),
                   "sounded": True, "onset_q": None, "duration_q": None}
                  for note, fret, role in ((first, f1, r1), (second, f2, r2))]
        found.append({"heading": chord, "events": events, "tone_count": 2,
                      "raw_line": lines[i], "source_ref": f"L62-TXT1-{i + 1}", "pdf_page": 19})
    if len(found) != 12:
        raise CandidateError("RECOVERY_CARD_COUNT_INVALID")
    return found


def build_candidate(root: Path = ROOT) -> dict:
    row = _map(root)
    txt = _read(root, TXT, PINS["txt"])
    pdf = _read(root, PDF, PINS["pdf"])
    lines = txt.decode("utf-8-sig").splitlines()
    pages = _page_lines(pdf)
    if len(lines) != 874 or "COMPLETE WRITTEN WORKOUT: 788 sounding tones." not in lines:
        raise CandidateError("TXT_STRUCTURE_INVALID")
    sections = _module_sections(lines)
    modules = {}
    for letter, ranges in sections.items():
        cells = [_parse_grid(lines, i, letter, pages)
                 for start, end in ranges for i in range(start, end) if lines[i].startswith("Nte|")]
        if len(cells) != CELL_COUNTS[letter]:
            raise CandidateError(f"MODULE_CELL_COUNT_INVALID {letter}")
        entry = {"sections": [{"source_ref": f"L62-TXT1-{a + 1}-{b}",
                                "raw_lines": lines[a:b]} for a, b in ranges],
                 "cells": cells, "tone_count": sum(c["tone_count"] for c in cells)}
        if letter == "J":
            entry["recovery_cards"] = _recoveries(lines, pages, ranges[0])
            entry["tone_count"] += 24
        if entry["tone_count"] != EXPECTED[letter]:
            raise CandidateError(f"MODULE_TONE_COUNT_INVALID {letter}")
        modules[letter] = entry
    if sum(m["tone_count"] for m in modules.values()) != 788:
        raise CandidateError("WORKLOAD_TOTAL_INVALID")
    pdf_checks = ((1, "Odd-note loops: starting stroke reverses next repetition."),
                  (14, "Grid: rest - notes 1-2 - rest - notes 3-4 - repeat through bars."),
                  (16, "Announce the next key during beat 4 of the final tonic bar."),
                  (17, "Use strict alternate picking first; economy motion may be added only across adjacent strings after every note is clean."))
    if any(phrase not in " ".join(pages[page]) for page, phrase in pdf_checks):
        raise CandidateError("PDF_ONLY_GUIDANCE_MISMATCH")
    return {"schema": "fathom.level62.whole.detached_candidate.v1", "level": 62,
            "wbs": "2.3.1.2.1", "status": "candidate_only", "stable_ids": None,
            "imported": False, "admitted": False,
            "source": {"map_path": str(MAP), "map_row": row,
                       "txt": {"path": str(TXT), "bytes": PINS["txt"][0], "sha256": PINS["txt"][1], "lines": len(lines)},
                       "pdf": {"path": str(PDF), "bytes": PINS["pdf"][0], "sha256": PINS["pdf"][1], "pages": len(pages)}},
            "workload": {"module_tones": EXPECTED, "total_sounding_tones": 788,
                         "recovery_tones": 24, "bridge_tones": 40},
            "core_rules": lines[6:14], "modules": modules,
            "pdf_only_directions": {
                "session_protocol_and_phrase_architecture": pages[0],
                "connection_zones_shift_timing_and_picking_choices": pages[1],
                "connection_zones": [{"zone": "Z1", "fret_area": "0-5", "job": "open/low fragment"},
                                     {"zone": "Z2", "fret_area": "5-9", "job": "lower-position connection"},
                                     {"zone": "Z3", "fret_area": "9-13", "job": "middle register"},
                                     {"zone": "Z4", "fret_area": "13-17", "job": "upper register"},
                                     {"zone": "Z5", "fret_area": "17-20", "job": "high-register destination"}],
                "picking_choices": ["Adjacent strings: alternate or controlled economy.",
                                    "Skipped strings: independent pick attacks.",
                                    "Odd-note loops: starting stroke reverses next repetition.",
                                    "Long shifts: preserve the stroke cycle through the move.",
                                    "Muted preview: air-pick the route before sounding it."],
                "module_page_guidance": [{"page": i + 1, "heading": pages[i][1],
                                          "banner": pages[i][3], "instruction": pages[i][4],
                                          "continuation": pages[i][5] if i in (7, 16) else None}
                                         for i in range(2, 18)],
                "motif_grid": "rest - notes 1-2 - rest - notes 3-4 - repeat through bars",
                "major_capstone_key_announcement": "Announce the next key during beat 4 of the final tonic bar.",
                "minor_capstone_pick_option": "Use strict alternate picking first; economy motion may be added only across adjacent strings after every note is clean.",
                "recovery_framing": pages[18],
                "completion_audit_and_practice_log": pages[19]},
            "mastery": {"txt_lines": lines[842:], "pdf_page": 20},
            "source_transcription": {"txt_lines": lines,
                                     "pdf_pages": [{"page": i + 1, "lines": page} for i, page in enumerate(pages)]},
            "timing_boundary": "No numeric BPM, onset, or duration is assigned; PDF motif rest grid and written quarter-note-speed instruction remain text."}


def write_candidate(candidate: dict, root: Path = ROOT) -> tuple[Path, Path]:
    out = root / OUT
    if out.is_symlink():
        raise CandidateError("OUTPUT_DIRECTORY_SYMLINK_INVALID")
    out.mkdir(parents=True, exist_ok=True)
    target, manifest = out / "level062_whole_candidate.json", out / "manifest.json"
    if target.is_symlink() or manifest.is_symlink():
        raise CandidateError("OUTPUT_FILE_SYMLINK_INVALID")
    blob = (json.dumps(candidate, ensure_ascii=False, indent=2) + "\n").encode()
    target.write_bytes(blob)
    manifest.write_text(json.dumps({"schema": "fathom.detached_candidate_manifest.v1",
                                    "status": "candidate_only", "candidate": target.name,
                                    "bytes": len(blob), "sha256": sha(blob),
                                    "txt_sha256": PINS["txt"][1], "pdf_sha256": PINS["pdf"][1]}, indent=2) + "\n")
    return target, manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    candidate = build_candidate()
    if args.check:
        print("LEVEL62_CHECK_OK", json.dumps(candidate["workload"], sort_keys=True))
    else:
        for path in write_candidate(candidate):
            print(path)


if __name__ == "__main__":
    main()
