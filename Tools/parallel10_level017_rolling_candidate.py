"""Detached whole-Level17 four-note rolling ladder source projection."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
STEM = "Scale_Exercises_Section_II_Level_17_Major_Scale_Four_Note_Rolling_Sequence_Two_Octave_Six_String_Neck_Ladder"
TXT_REL = Path(f"Notes/music/guitar project/TXT version/{STEM}.txt")
PDF_REL = Path(f"Notes/music/guitar project/PDF version/{STEM}.pdf")
TXT_SHA = "e742548015d297941c9972ddb7cfcaeb0a66375b164864698e72d3e0b6bed511"
PDF_SHA = "fc60d519a880c3d6a8a4984d99dd07030fcb56d09f1e2ea9ad951da271349d6d"
BUILD_REL = Path("Build/parallel-10/2.3.1.1.1-level017-whole-rolling-r01")
KEYS = ("A", "Bb", "B", "C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A")
TONES = (
    ("A", "B", "C#", "D", "E", "F#", "G#"), ("Bb", "C", "D", "Eb", "F", "G", "A"),
    ("B", "C#", "D#", "E", "F#", "G#", "A#"), ("C", "D", "E", "F", "G", "A", "B"),
    ("Db", "Eb", "F", "Gb", "Ab", "Bb", "C"), ("D", "E", "F#", "G", "A", "B", "C#"),
    ("Eb", "F", "G", "Ab", "Bb", "C", "D"), ("E", "F#", "G#", "A", "B", "C#", "D#"),
    ("F", "G", "A", "Bb", "C", "D", "E"), ("Gb", "Ab", "Bb", "Cb", "Db", "Eb", "F"),
    ("G", "A", "B", "C", "D", "E", "F#"), ("Ab", "Bb", "C", "Db", "Eb", "F", "G"),
    ("A", "B", "C#", "D", "E", "F#", "G#"),
)
STRINGS = ("E", "A", "D", "G", "B", "e")
TUNING = {"E": 40, "A": 45, "D": 50, "G": 55, "B": 59, "e": 64}
BASE_FINGERS = (2, 4, 1, 2, 4, 1, 3, 4, 1, 3, 4, 2, 4, 1, 2)
MAJOR_OFFSETS = (0, 2, 4, 5, 7, 9, 11, 12, 14, 16, 17, 19, 21, 23, 24)


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sources(root: Path = ROOT) -> tuple[list[str], PdfReader]:
    txt = (root / TXT_REL).read_bytes()
    pdf = (root / PDF_REL).read_bytes()
    require(sha256(txt) == TXT_SHA, "TXT source drift")
    require(sha256(pdf) == PDF_SHA, "PDF source drift")
    reader = PdfReader(str(root / PDF_REL))
    require(len(reader.pages) == 10, "PDF page count")
    return txt.decode("utf-8").splitlines(), reader


def scale_contacts(root_fret: int, key_index: int) -> list[dict[str, object]]:
    r = root_fret
    frets = {"E": [r, r + 2], "A": [r - 1, r, r + 2],
             "D": [r - 1, r + 1, r + 2], "G": [r - 1, r + 1, r + 2],
             "B": [r, r + 2], "e": [r - 1, r]}
    contacts = []
    tone_names = list(TONES[key_index]) * 2 + [KEYS[key_index]]
    for string in STRINGS:
        for fret in frets[string]:
            pos = len(contacts)
            contacts.append({"scale_position": pos + 1, "string": string, "fret": fret,
                             "finger": BASE_FINGERS[pos], "midi": TUNING[string] + fret,
                             "source_tone": tone_names[pos]})
    require(len(contacts) == 15, "scale contact count")
    require([c["midi"] for c in contacts] == [40 + r + off for off in MAJOR_OFFSETS], "major pitch/B offset")
    return contacts


def cells(row: str, label: str) -> list[str]:
    require(row.startswith(label + "|") and row.endswith("|"), f"{label} row format")
    result = row[len(label) + 1 : -1].split("|")
    require(len(result) == 12, f"{label} rolling cell count")
    return result


def tab_cells(row: str, string: str) -> list[str]:
    require(row.startswith(string + "  |") and row.endswith("|"), f"{string} TAB row format")
    result = row.split("|", 1)[1][:-1].split("|")
    require(len(result) == 12, f"{string} TAB cell count")
    return result


def numbers(cell: str) -> list[int]:
    return [int(x) for x in re.findall(r"\d+", cell)]


def pdf_route(reader: PdfReader) -> None:
    lines = [x.strip() for x in reader.pages[1].extract_text().splitlines()]
    require("Ascending route: complete one 96-note rolling cell, then move the frame +1 fret" in lines, "PDF UP route")
    require("Descending route: use the same cards in reverse order and move -1 fret" in lines, "PDF DOWN route")
    start = lines.index("Scale tones (degrees 1-7)") + 1
    for i in range(13):
        root = 5 + i
        expected = [f"{i + 1:02d}", KEYS[i] + (" major - octave" if i == 12 else " major"),
                    f"fret {root}", f"{root - 1}-{root + 2}", " ".join(TONES[i])]
        require(lines[start + i * 5 : start + (i + 1) * 5] == expected, f"PDF route rung {i + 1}")
    require("rungs 12-01. Do not replay" in lines, "PDF high-A turn")


def pdf_cards(reader: PdfReader) -> dict[int, tuple[int, list[str]]]:
    cards: dict[int, tuple[int, list[str]]] = {}
    for page in range(3, 10):
        text = reader.pages[page - 1].extract_text()
        chunks = re.split(r"(?m)^(\d{2})\s+([A-Z]+ MAJOR(?: - OCTAVE)?)\s*$", text)
        count = 2 if page < 9 else 1
        require(len(chunks) == 1 + count * 3, f"PDF page {page} card count")
        for j in range(count):
            n = int(chunks[1 + j * 3])
            key = chunks[2 + j * 3]
            require(n == (page - 3) * 2 + j + 1, "PDF rung order")
            require(key == KEYS[n - 1].upper() + " MAJOR" + (" - OCTAVE" if n == 13 else ""), "PDF rung key")
            cards[n] = (page, [line.strip() for line in chunks[3 + j * 3].splitlines() if line.strip()])
    require(list(cards) == list(range(1, 14)), "PDF whole-rung coverage")
    return cards


def parse_half(block: list[str], offset: int, phase: str, base: list[dict[str, object]], start_line: int) -> dict[str, object]:
    require(block[offset] == f"{phase.upper()} - 12 GROUPS / 48 NOTES", f"{phase} heading")
    deg_row, fng_row = block[offset + 1 : offset + 3]
    deg = cells(deg_row, "Deg")
    fng = cells(fng_row, "Fng")
    rows = {s: block[offset + 3 + 5 - STRINGS.index(s)] for s in STRINGS}
    tabs = {s: tab_cells(rows[s], s) for s in STRINGS}
    groups = []
    for j in range(12):
        positions = (list(range(j + 1, j + 5)) if phase == "ascending"
                     else list(range(15 - j, 11 - j, -1)))
        require(numbers(deg[j]) == positions, f"{phase} group {j + 1} degree sequence")
        notes = [dict(base[p - 1]) for p in positions]
        require(numbers(fng[j]) == [n["finger"] for n in notes], f"{phase} group {j + 1} finger sequence")
        for string in STRINGS:
            expected = [n["fret"] for n in notes if n["string"] == string]
            require(numbers(tabs[string][j]) == expected, f"{phase} group {j + 1} {string} TAB/B offset")
        groups.append({"group": j + 1, "scale_positions": positions,
                       "notes": [{**n, "cell_note_index": j * 4 + k + 1} for k, n in enumerate(notes)]})
    require(len(groups) == 12 and sum(len(g["notes"]) for g in groups) == 48, f"{phase} count")
    return {"phase": phase, "txt_heading_line": start_line + offset,
            "txt_rows": {"Deg": deg_row, "Fng": fng_row, **rows}, "groups": groups}


def parse_rung(lines: list[str], n: int, pdf_page: int, pdf_lines: list[str]) -> dict[str, object]:
    start = 69 + (n - 1) * 24
    root = n + 4
    key = KEYS[n - 1]
    label = key.upper() + " MAJOR" + (" - OCTAVE" if n == 13 else "")
    block = lines[start - 1 : start + 22]
    require(len(block) == 23, "TXT rung truncation")
    require(block[0] == f"RUNG {n:02d} OF 13 - {label} - ROOT ON LOW E FRET {root} - FRAME {root - 1}-{root + 2}", "TXT rung header")
    tones15 = list(TONES[n - 1]) * 2 + [key]
    require(block[1] == "Scale tones across two octaves: " + " ".join(tones15), "TXT scale tones")
    require(block[2] == "96-note cell: 12 ascending four-note groups, repeat the high root at the turn, then 12 descending groups.", "TXT cell guidance")
    require(pdf_lines[0] == f"ROOT E{root}  |  FRAME {root - 1}-{root + 2}", "PDF root/frame")
    require(pdf_lines[1] == "Scale tones: " + " ".join(tones15), "PDF scale tones")
    require(pdf_lines[2] == "96 NOTES / 24 GROUPS", "PDF cell label")
    require(pdf_lines[3:21] == block[3:21], "PDF/TXT rolling Deg/Fng/TAB mismatch")
    require(pdf_lines[21] == "Return to the low root; release pressure; move the entire frame one fret.", "PDF relocation")
    require(pdf_lines[22] == "Continuous alternate picking - D-start and U-start", "PDF picking")
    require(block[21] == "Finish on the low root, release pressure, and move the entire frame one fret in the route direction.", "TXT relocation")
    require(block[22] == "", "TXT rung boundary")
    base = scale_contacts(root, n - 1)
    ascending = parse_half(block, 3, "ascending", base, start)
    descending = parse_half(block, 12, "descending", base, start)
    require(ascending["groups"][-1]["notes"][-1]["scale_position"] == 15, "ascending high-root end")
    require(descending["groups"][0]["notes"][0]["scale_position"] == 15, "descending high-root repeat")
    return {"rung": n, "key": key, "low_e_root_fret": root, "frame_frets": [root - 1, root + 2],
            "txt_header_line": start, "pdf_page": pdf_page, "scale_tones_two_octaves": tones15,
            "cell_note_count": 96, "groups": ascending["groups"] + descending["groups"],
            "source_halves": {"ascending": ascending["txt_rows"], "descending": descending["txt_rows"]},
            "canonical_item_id": None, "fixed_bpm": None, "note_per_click": None,
            "onset": None, "duration": None, "runtime_eligible": False, "admitted": False}


def build_candidate(root: Path = ROOT) -> dict[str, object]:
    lines, reader = sources(root)
    up = "UP:   " + " > ".join(f"{key}({5 + i})" for i, key in enumerate(KEYS))
    down = "DOWN: " + " > ".join(f"{KEYS[i]}({5 + i})" for i in range(12, -1, -1))
    require(lines[54] == up, "TXT UP ladder route")
    require(lines[55] == down, "TXT DOWN ladder route")
    require(lines[380] == "FULL ROUND-TRIP CHALLENGE", "TXT rung-end boundary")
    require(lines[382] == "Do not replay rung 13 at the turn. The route contains 25 cells x 96 notes = 2,400 picked notes.", "TXT round-trip count/turn")
    pdf_route(reader)
    cards = pdf_cards(reader)
    rungs = [parse_rung(lines, n, *cards[n]) for n in range(1, 14)]
    require(sum(len(r["groups"]) for r in rungs) == 13 * 24, "whole-workbook group count")
    return {"schema": "fathom-detached-source-candidate.1", "workstream": "2.3.1.1.1",
            "level": 17, "source": {"txt": str(TXT_REL), "txt_sha256": TXT_SHA,
             "pdf": str(PDF_REL), "pdf_sha256": PDF_SHA, "pdf_pages": list(range(2, 10))},
            "canonical_identity_assigned": False, "runtime_import_authorized": False,
            "curriculum_reviewed": False, "timing_interpreted": False,
            "guidance_only": {"rolling_rule": lines[33:48], "practice_rule": lines[57:66],
                              "round_trip": lines[380:384]},
            "ladder": {"up_rungs": list(range(1, 14)), "down_rungs": list(range(12, 0, -1)),
                       "round_trip_cells": 25, "round_trip_note_contacts": 2400,
                       "turn": "finish rung 13 then return through 12-01; do not replay rung 13"},
            "rungs": rungs, "exceptions": []}


def render(data: dict[str, object]) -> bytes:
    return (json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")


def write_candidate(output: Path, root: Path = ROOT) -> tuple[int, str]:
    allowed = (root / BUILD_REL).resolve()
    require(output.parent.resolve().is_relative_to(allowed), "output outside P10 Level17 Build")
    require(not output.exists() and not output.is_symlink(), "output exists or is symlink")
    data = render(build_candidate(root))
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as stream:
        stream.write(data)
    return len(data), sha256(data)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    size, digest = write_candidate(args.output)
    print(f"LEVEL17 WHOLE ROLLING DETACHED PASS bytes={size} sha256={digest} output={args.output}")


if __name__ == "__main__":
    main()
