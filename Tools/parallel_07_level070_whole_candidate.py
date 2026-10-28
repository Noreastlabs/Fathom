#!/usr/bin/env python3
"""Build a pinned, detached whole-source Section IX Level 70 candidate."""

from __future__ import annotations

import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path
import re

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
STEM = "Guitar_Exercises_Section_IX_Level_70_A_Melodic_Minor_Five_Position_Map_Horizontal_Routes_Directional_Descents_Seam_Transitions_and_Full_Register_Movement"
TXT = Path("Notes/music/guitar project/TXT version") / (STEM + ".txt")
PDF = Path("Notes/music/guitar project/PDF version") / (STEM + ".pdf")
MAP = Path("Results/parallel-01/exercises/inventory/20260922T180500Z-2.3-curriculum-v1-source-inventory-evidence/curriculum-source-map.json")
OUT = Path("Build/parallel-07/2.3.1.2.1-level070-whole-r01")
PINS = {"txt": (36082, "13ed1a46b87e74c3b3fb78161281268f79ed710b5bd7f12195378f3b247c4b9b"),
        "pdf": (56679, "4b95c98c91c35f132954f2452104280f40d8e96b46ca431344e6b4de007c764f")}
COUNTS = {"A": 180, "B": 168, "C": 94, "D": 88, "E": 180, "F": 60, "G": 64, "H": 64}
CELLS = {"A": 5, "B": 4, "C": 6, "D": 5, "E": 10, "F": 5, "G": 4, "H": 4}
PC = {"A": 9, "B": 11, "C": 0, "D": 2, "E": 4, "F": 5, "F#": 6, "G": 7, "G#": 8}
DEGREE = {"A": "1", "B": "2", "C": "b3", "D": "4", "E": "5", "F": "b6", "F#": "6", "G": "b7", "G#": "7"}
OPEN = {"E": 40, "A": 45, "D": 50, "G": 55, "B": 59, "e": 64}
ROLE = {"R": 0, "b3": 3, "3": 4, "5": 7, "b7": 10, "7": 11, "6": 9,
        "b5": 6, "#5": 8}
CHORD_ROOTS = {"AmMaj7": 9, "D7": 2, "E7": 4, "Bm7": 11,
               "Am6": 9, "Cmaj7#5": 0, "F#m7b5": 6, "G#m7b5": 8}
NOTE_RE = re.compile(r"F#|G#|[A-G]")
SEAM_LINE = re.compile(r"^([EADGBe]): frets ([0-9-]+) \| notes ([A-G#-]+) \| degrees ([0-9b-]+)$")


class CandidateError(ValueError):
    """Pinned identity, authored grid, count, or output boundary failed."""


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read(root: Path, rel: Path, pin: tuple[int, str]) -> bytes:
    path = root / rel
    if not path.is_file() or path.is_symlink():
        raise CandidateError(f"SOURCE_PATH_INVALID {rel}")
    data = path.read_bytes()
    if (len(data), sha(data)) != pin:
        raise CandidateError(f"PINNED_INPUT_DRIFT {rel}")
    return data


def _map(root: Path) -> dict:
    rows = json.loads((root / MAP).read_text())["rows"]
    row = next((r for r in rows if r["level"] == 70), None)
    expected = {"section": "IX", "wbs_owner": "2.3.1.2.1", "txt_path": str(TXT),
                "pdf_path": str(PDF), "txt_bytes": PINS["txt"][0],
                "pdf_bytes": PINS["pdf"][0], "txt_sha256": PINS["txt"][1],
                "pdf_sha256": PINS["pdf"][1], "pair_status": "exact_stem_pair",
                "conversion_status": "not_converted", "stable_ids_assigned": False,
                "imported": False, "admitted": False}
    if row is None or any(row.get(k) != value for k, value in expected.items()):
        raise CandidateError("SOURCE_MAP_IDENTITY_OR_STATUS_DRIFT")
    return row


def _pages(data: bytes) -> list[list[str]]:
    reader = PdfReader(BytesIO(data))
    if len(reader.pages) != 20:
        raise CandidateError("PDF_PAGE_COUNT_INVALID")
    return [page.extract_text().splitlines() for page in reader.pages]


def _sections(lines: list[str]) -> dict[str, tuple[int, int]]:
    heads = [(i, re.fullmatch(r"MODULE ([A-H]) - .+", line).group(1))
             for i, line in enumerate(lines) if re.fullmatch(r"MODULE ([A-H]) - .+", line)]
    if [letter for _, letter in heads] != list("ABCDEFGH"):
        raise CandidateError("MODULE_SEQUENCE_INVALID")
    end = lines.index("PRACTICE PROGRESSION AND MASTERY")
    return {letter: (start, heads[pos + 1][0] if pos + 1 < len(heads) else end)
            for pos, (start, letter) in enumerate(heads)}


def _segments(line: str, prefix: str) -> list[str]:
    if not line.startswith(prefix + "|"):
        raise CandidateError(f"ROW_PREFIX_INVALID {prefix}")
    return [part for part in line[len(prefix) + 1:].split("|") if part]


def _parse_grid(lines: list[str], i: int, module: str, pages: list[list[str]]) -> dict:
    note_bars = _segments(lines[i], "Nte")
    degree_bars = _segments(lines[i + 1], "Deg")
    if len(note_bars) != len(degree_bars):
        raise CandidateError(f"DEGREE_BAR_COUNT_INVALID {i + 1}")
    j = i + 2
    fingers = _segments(lines[j], "Fng") if lines[j].startswith("Fng|") else None
    if fingers is not None:
        j += 1
    roles = _segments(lines[j], "Rol") if lines[j].startswith("Rol|") else None
    if roles is not None:
        j += 1
    tab: dict[str, list[str]] = {}
    while j < len(lines) and (match := re.fullmatch(r"  ([eBGDAE])\|(.*)", lines[j])):
        if match.group(1) in tab:
            raise CandidateError("DUPLICATE_TAB_STRING")
        tab[match.group(1)] = [part for part in match.group(2).split("|") if part]
        j += 1
    if not tab or any(len(parts) != len(note_bars) for parts in tab.values()):
        raise CandidateError(f"TAB_BAR_COUNT_INVALID {i + 1}")
    if module in "GH" and roles is None:
        raise CandidateError("HARMONIC_ROLE_ROW_MISSING")
    if roles is not None and len(roles) != len(note_bars):
        raise CandidateError("ROLE_BAR_COUNT_INVALID")
    if fingers is not None and len(fingers) != len(note_bars):
        raise CandidateError("FINGER_BAR_COUNT_INVALID")
    chords = None
    if module == "G":
        chords = ["AmMaj7", "D7", "E7", "AmMaj7"]
    elif module == "H":
        chords = [part.strip().split("(")[0] for part in lines[i - 1].split(": ", 1)[1].split(" | ")]
    if chords is not None and (len(chords) != len(note_bars) or any(c not in CHORD_ROOTS for c in chords)):
        raise CandidateError(f"GRID_CHORD_LIST_INVALID {i + 1}")
    events = []
    for bar, (nseg, dseg) in enumerate(zip(note_bars, degree_bars, strict=True), 1):
        if len(nseg) != len(dseg) or any(len(parts[bar - 1]) != len(nseg) for parts in tab.values()):
            raise CandidateError(f"TAB_GEOMETRY_INVALID {i + 1}:{bar}")
        matches = list(NOTE_RE.finditer(nseg))
        starts = [m.start() for m in matches]
        found = {}
        for string, parts in tab.items():
            for match in re.finditer(r"\d+", parts[bar - 1]):
                if match.start() in found:
                    raise CandidateError("MULTIPLE_TAB_CONTACTS")
                found[match.start()] = (string, int(match.group()))
        if sorted(found) != starts:
            raise CandidateError(f"TAB_NOTE_ALIGNMENT_INVALID {i + 1}:{bar}")
        for slot, (match, end) in enumerate(zip(matches, starts[1:] + [len(nseg)], strict=True), 1):
            note = match.group()
            start = match.start()
            degree = dseg[start:end].replace("-", "")
            finger = None if fingers is None else fingers[bar - 1][start:end].replace("-", "")
            role = None if roles is None else roles[bar - 1][start:end].replace("-", "").replace(">", "")
            string, fret = found[start]
            if degree != DEGREE[note] or not 0 <= fret <= 19 or (OPEN[string] + fret) % 12 != PC[note]:
                raise CandidateError(f"NOTE_DEGREE_OR_PITCH_INVALID {i + 1}:{bar}:{slot}")
            if finger is not None and finger not in ("1", "2", "3", "4"):
                raise CandidateError(f"FINGER_INVALID {i + 1}:{bar}:{slot}")
            if role is not None:
                chord = chords[bar - 1]
                if role not in ROLE or (CHORD_ROOTS[chord] + ROLE[role]) % 12 != PC[note]:
                    raise CandidateError(f"CHORD_ROLE_INVALID {i + 1}:{bar}:{slot}")
            else:
                chord = None
            events.append({"bar": bar, "slot": slot, "note": note, "degree": degree,
                           "finger": finger, "role": role, "chord": chord,
                           "form": ("ASC" if slot <= 4 else "SYM" if slot <= 8 else "CLS") if module == "F" else None,
                           "string": string, "fret": fret, "sounded": True,
                           "onset_q": None, "duration_q": None})
    rows_to_match = lines[i + 1:j] if module == "E" else lines[i:j]
    page_number = next((num for num, page in enumerate(pages, 1)
                        if all(row in page for row in rows_to_match)), None)
    if page_number is None:
        raise CandidateError(f"PDF_GRID_MISMATCH {i + 1}")
    if module == "F" and "Frm|ASC-ASC-ASC-ASC-SYM-SYM-SYM-SYM-CLS-CLS-CLS-CLS-|" not in pages[page_number - 1]:
        raise CandidateError(f"PDF_DIRECTIONAL_FORM_ROW_MISSING {i + 1}")
    return {"heading": lines[i - 1], "events": events, "tone_count": len(events),
            "raw_lines": lines[i:j], "source_ref": f"L70-TXT1-{i + 1}-{j}",
            "pdf_page": page_number,
            "pdf_grid_status": "degree_finger_tab_without_note_row" if module == "E" else "exact_row_parity"}


def _seams(lines: list[str], section: tuple[int, int], pages: list[list[str]]) -> list[dict]:
    start, end = section
    seams = []
    for i in range(start, end):
        if not re.fullmatch(r"SEAM P[1-4]-P[2-5]", lines[i]):
            continue
        label = lines[i]
        page_number = 8 if len(seams) < 2 else 9
        lanes = []
        for offset in range(1, 7):
            line = lines[i + offset]
            match = SEAM_LINE.fullmatch(line)
            if match is None:
                raise CandidateError(f"SEAM_LINE_INVALID {i + offset + 1}")
            string, frets_s, notes_s, degrees_s = match.groups()
            frets = [int(x) for x in frets_s.split("-")]
            notes = notes_s.split("-")
            degrees = degrees_s.split("-")
            if not (len(frets) == len(notes) == len(degrees)):
                raise CandidateError("SEAM_TONE_COUNT_INVALID")
            if len(frets) != 7 or frets != list(reversed(frets)):
                raise CandidateError("SEAM_MIRROR_INVALID")
            events = []
            for slot, (fret, note, degree) in enumerate(zip(frets, notes, degrees, strict=True), 1):
                if note not in PC or degree != DEGREE[note] or (OPEN[string] + fret) % 12 != PC[note]:
                    raise CandidateError(f"SEAM_PITCH_OR_DEGREE_INVALID {i + offset + 1}:{slot}")
                events.append({"slot": slot, "string": string, "fret": fret,
                               "note": note, "degree": degree, "sounded": True,
                               "onset_q": None, "duration_q": None})
            pdf_page = pages[page_number - 1]
            heading = f"Seam {label.removeprefix('SEAM ')} - 6 strings x 7 tones = 42 tones"
            if heading not in pdf_page:
                raise CandidateError(f"PDF_SEAM_HEADING_MISSING {label}")
            pdf_start = pdf_page.index(heading)
            pdf_block = pdf_page[pdf_start + 1:]
            degree_line = next((row for row in pdf_block if row.startswith("Deg|")), None)
            tab_line = next((row for row in pdf_block if row.startswith("  " + string + "|")), None)
            order = "EADGBe".index(string)
            if degree_line is None or tab_line is None:
                raise CandidateError(f"PDF_SEAM_GRID_MISSING {label} {string}")
            pdf_degrees = degree_line[4:].split("|")[order]
            pdf_frets = tab_line[4:].split("|")[order]
            if [int(x) for x in re.findall(r"\d+", pdf_frets)] != frets or re.findall(r"b3|b7|[1-7]", pdf_degrees) != degrees:
                raise CandidateError(f"PDF_SEAM_GRID_MISMATCH {label} {string}")
            lanes.append({"string": string, "events": events, "tone_count": 7,
                          "raw_line": line, "source_ref": f"L70-TXT1-{i + offset + 1}"})
        count_line = lines[i + 7]
        if count_line != "Count: 6 strings x 7 tones = 42 tones. Repeat twice to restore the original starting stroke.":
            raise CandidateError(f"SEAM_COUNT_RULE_INVALID {label}")
        seams.append({"heading": label, "lanes": lanes, "tone_count": 42,
                      "repeat_twice_instruction": True, "repeat_counted_in_printed_898": False,
                      "count_boundary": "A literal second sounding pass adds 42 tones beyond the printed seam count.",
                      "source_ref": f"L70-TXT1-{i + 1}-{i + 8}", "pdf_page": page_number,
                      "pdf_grid_status": "degree_finger_tab_without_note_row"})
    if len(seams) != 4 or [s["heading"] for s in seams] != ["SEAM P1-P2", "SEAM P2-P3", "SEAM P3-P4", "SEAM P4-P5"]:
        raise CandidateError("SEAM_SET_INVALID")
    return seams


def build_candidate(root: Path = ROOT) -> dict:
    row = _map(root)
    txt = _read(root, TXT, PINS["txt"])
    pdf = _read(root, PDF, PINS["pdf"])
    lines = txt.decode("utf-8-sig").splitlines()
    pages = _pages(pdf)
    if len(lines) != 533 or "COMPLETE WRITTEN WORKOUT: 898 sounding tones." not in lines:
        raise CandidateError("TXT_STRUCTURE_INVALID")
    sections = _sections(lines)
    modules = {}
    for letter, (start, end) in sections.items():
        cells = (_seams(lines, (start, end), pages) if letter == "B" else
                 [_parse_grid(lines, i, letter, pages) for i in range(start, end) if lines[i].startswith("Nte|")])
        if len(cells) != CELLS[letter] or sum(cell["tone_count"] for cell in cells) != COUNTS[letter]:
            raise CandidateError(f"MODULE_COUNT_INVALID {letter}")
        modules[letter] = {"title": lines[start], "cells": cells,
                           "tone_count": COUNTS[letter], "source_ref": f"L70-TXT1-{start + 1}-{end}",
                           "raw_lines": lines[start:end]}
    if sum(COUNTS.values()) != 898:
        raise CandidateError("TOTAL_COUNT_INVALID")
    if [c["tone_count"] for c in modules["C"]["cells"]] != [16, 16, 14, 16, 16, 16] or [
            c["tone_count"] for c in modules["D"]["cells"]] != [18, 20, 12, 18, 20]:
        raise CandidateError("LANE_OR_SEQUENCE_DISTRIBUTION_INVALID")
    if [c["tone_count"] for c in modules["E"]["cells"]] != [18] * 10:
        raise CandidateError("ZIGZAG_SEGMENT_COUNT_INVALID")
    if [c["tone_count"] for c in modules["F"]["cells"]] != [12] * 5:
        raise CandidateError("DIRECTIONAL_CELL_COUNT_INVALID")
    pdf_only = {"page_1_protocol_and_picking": pages[0], "page_2_atlas_and_connection_rule": pages[1],
                "module_page_guidance": [{"page": p + 1, "heading": pages[p][1],
                                          "banner": pages[p][3], "instruction": pages[p][4],
                                          "all_printed_lines": pages[p]}
                                         for p in range(2, 19)],
                "zigzag_pdf_parity": "PDF pages 14-15 omit Nte rows but print the matching degree, fingering, and TAB rows.",
                "position_three_passes": "1. Notes and degrees. 2. D-start and U-start alternate picking. 3. Accent F# and G#, then remove the accents while preserving the melodic-minor sound.",
                "directional_forms": {"modern": "A G# F# E D C B A", "classical": "A G F E D C B A"},
                "directional_cell_structure": "Each written 12-tone cell contains E-F#-G#-A ascent, A-G#-F#-E modern descent, and A-G-F-E classical descent.",
                "directional_stop_rule": "If F/F# or G/G# changes without intention, return to one register and play only the two descent forms.",
                "connection_audit": "Repair the last four tones of the old zigzag segment plus the first four of the new segment.",
                "mastery_and_log": pages[19]}
    required_pdf = ((2, "Three passes"),
                    (13, "Repair the last four tones"),
                    (15, "ASCEND E-F#-G#-A; THEN CHOOSE ONE OF TWO DESCENDING FORMS"),
                    (15, pdf_only["directional_stop_rule"]),
                    (18, "FOUR HARMONIC REGIONS"))
    if any(phrase not in " ".join(pages[p]) for p, phrase in required_pdf):
        raise CandidateError("PDF_ONLY_GUIDANCE_MISMATCH")
    return {"schema": "fathom.level70.whole.detached_candidate.v1", "level": 70,
            "wbs": "2.3.1.2.1", "status": "candidate_only", "stable_ids": None,
            "imported": False, "admitted": False,
            "source": {"map_path": str(MAP), "map_row": row,
                       "txt": {"path": str(TXT), "bytes": PINS["txt"][0], "sha256": PINS["txt"][1], "lines": len(lines)},
                       "pdf": {"path": str(PDF), "bytes": PINS["pdf"][0], "sha256": PINS["pdf"][1], "pages": len(pages)}},
            "scale": {"notes": ["A", "B", "C", "D", "E", "F#", "G#"],
                      "degrees": ["1", "2", "b3", "4", "5", "6", "7"],
                      "steps": ["W", "H", "W", "W", "W", "W", "H"]},
            "workload": {"module_tones": COUNTS, "total_sounding_tones": 898,
                         "supplemental_seam_second_pass_counted": False,
                         "supplemental_sequence_translations_counted": False,
                         "module_f_both_descent_forms_written_and_counted": True,
                         "supplemental_capstone_repeat_counted": False},
            "modules": modules, "pdf_only_directions": pdf_only,
            "mastery": {"txt_lines": lines[500:], "pdf_page": 20},
            "count_boundaries": ["Each seam is printed as 42 tones but also says repeat twice to restore starting pick orientation; a literal repeat would add 168 tones overall.",
                                 "Translate all five sequence patterns to every frame start after learning the printed 88-tone Module D; extra translations are not enumerated in 898.",
                                 "Module F's five 12-tone cells include both modern and classical descents as written; capstone twice is a practice extension beyond printed 898."],
            "source_ambiguities": ["PDF page 16 says to choose one of two descending forms, but its 12-tone grid and TXT print both four-tone descents after the ascent, and Module F totals 60. Both descents remain in the counted printed cells; the PDF choice wording remains a separate performance direction."],
            "source_transcription": {"txt_lines": lines,
                                     "pdf_pages": [{"page": i + 1, "lines": page} for i, page in enumerate(pages)]},
            "timing_boundary": "Onset/duration and BPM remain null; source-specific rhythmic alternatives remain prose."}


def write_candidate(candidate: dict, root: Path = ROOT) -> tuple[Path, Path]:
    out = root / OUT
    if out.is_symlink():
        raise CandidateError("OUTPUT_DIRECTORY_SYMLINK_INVALID")
    out.mkdir(parents=True, exist_ok=True)
    target, manifest = out / "level070_whole_candidate.json", out / "manifest.json"
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
        print("LEVEL70_CHECK_OK", json.dumps(candidate["workload"], sort_keys=True))
    else:
        for path in write_candidate(candidate):
            print(path)


if __name__ == "__main__":
    main()
