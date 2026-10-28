"""Build a detached whole-Level13 source candidate; no runtime admission."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
STEM = "Scale_Exercises_Section_II_Level_13_Major_Scale_Two_Octave_Six_String_Neck_Ladder"
TXT_REL = Path(f"Notes/music/guitar project/TXT version/{STEM}.txt")
PDF_REL = Path(f"Notes/music/guitar project/PDF version/{STEM}.pdf")
TXT_SHA = "973b9c614546e432282dcc0ba415a21c0bc28858e61e7910ef2d0559329a0956"
PDF_SHA = "0730f903d6d7a992b1f366f0e4977c05ba59d6467666fde5a7ea15ff20ca040c"
BUILD_REL = Path("Build/parallel-10/2.3.1.1.1-level013-whole-ladder-r01")
KEYS = ("A", "Bb", "B", "C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A")
SCALE_TONES = (
    ("A", "B", "C#", "D", "E", "F#", "G#"),
    ("Bb", "C", "D", "Eb", "F", "G", "A"),
    ("B", "C#", "D#", "E", "F#", "G#", "A#"),
    ("C", "D", "E", "F", "G", "A", "B"),
    ("Db", "Eb", "F", "Gb", "Ab", "Bb", "C"),
    ("D", "E", "F#", "G", "A", "B", "C#"),
    ("Eb", "F", "G", "Ab", "Bb", "C", "D"),
    ("E", "F#", "G#", "A", "B", "C#", "D#"),
    ("F", "G", "A", "Bb", "C", "D", "E"),
    ("Gb", "Ab", "Bb", "Cb", "Db", "Eb", "F"),
    ("G", "A", "B", "C", "D", "E", "F#"),
    ("Ab", "Bb", "C", "Db", "Eb", "F", "G"),
    ("A", "B", "C#", "D", "E", "F#", "G#"),
)
STRINGS = ("E", "A", "D", "G", "B", "e")
TUNING_MIDI = {"E": 40, "A": 45, "D": 50, "G": 55, "B": 59, "e": 64}
ASC_COUNTS = {"E": 2, "A": 3, "D": 3, "G": 3, "B": 2, "e": 2}
MAJOR_OFFSETS = (0, 2, 4, 5, 7, 9, 11, 12, 14, 16, 17, 19, 21, 23, 24)
ASC_DEGREES = (1, 2, 3, 4, 5, 6, 7, 1, 2, 3, 4, 5, 6, 7, 1)
FINGERS = (2, 4, 1, 2, 4, 1, 3, 4, 1, 3, 4, 2, 4, 1, 2,
           2, 1, 4, 2, 4, 3, 1, 4, 3, 1, 4, 2, 1, 4, 2)


def require(ok: bool, detail: str) -> None:
    if not ok:
        raise ValueError(detail)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def source(root: Path = ROOT) -> tuple[list[str], PdfReader]:
    txt_data = (root / TXT_REL).read_bytes()
    pdf_data = (root / PDF_REL).read_bytes()
    require(sha256(txt_data) == TXT_SHA, "TXT source drift")
    require(sha256(pdf_data) == PDF_SHA, "PDF source drift")
    reader = PdfReader(str(root / PDF_REL))
    require(len(reader.pages) == 7, "PDF page count")
    return txt_data.decode("utf-8").splitlines(), reader


def tokens(row: str, label: str, expected_count: int) -> list[int]:
    require(row.startswith(label + "|") and row.endswith("|"), f"{label} row format")
    values = [int(x) for x in re.findall(r"\d+", row[len(label) + 1 : -1])]
    require(len(values) == expected_count, f"{label} token count")
    return values


def tab_tokens(row: str, string: str, count: int) -> list[int]:
    require(row.startswith(string + "  |") and row.endswith("|"), f"{string} TAB row format")
    values = [int(x) for x in re.findall(r"\d+", row.split("|", 1)[1])]
    require(len(values) == count, f"{string} TAB token count")
    return values


def expected_row_frets(root_fret: int) -> dict[str, list[int]]:
    r = root_fret
    ascending = {"E": [r, r + 2], "A": [r - 1, r, r + 2],
                 "D": [r - 1, r + 1, r + 2], "G": [r - 1, r + 1, r + 2],
                 "B": [r, r + 2], "e": [r - 1, r]}
    return {string: frets + list(reversed(frets)) for string, frets in ascending.items()}


def pdf_card_map(reader: PdfReader) -> dict[int, tuple[int, list[str]]]:
    cards: dict[int, tuple[int, list[str]]] = {}
    for page_number in range(3, 8):
        text = reader.pages[page_number - 1].extract_text()
        chunks = re.split(r"(?m)^(\d{2})\s+([A-Z]+ MAJOR(?: \(OCTAVE\))?)\s*$", text)
        expected_count = 3 if page_number in (3, 4, 5, 6) else 1
        require(len(chunks) == 1 + expected_count * 3, f"PDF card count page {page_number}")
        for j in range(expected_count):
            number = int(chunks[1 + 3 * j])
            key_label = chunks[2 + 3 * j]
            expected_number = (page_number - 3) * 3 + j + 1
            require(number == expected_number, "PDF rung order")
            expected_key = KEYS[number - 1].upper() + " MAJOR" + (" (OCTAVE)" if number == 13 else "")
            require(key_label == expected_key, "PDF rung key")
            lines = [line.strip() for line in chunks[3 + 3 * j].splitlines() if line.strip()]
            cards[number] = (page_number, lines)
    require(list(cards) == list(range(1, 14)), "PDF whole-rung coverage")
    return cards


def verify_pdf_route(reader: PdfReader) -> None:
    lines = [x.strip() for x in reader.pages[1].extract_text().splitlines()]
    require("Ascending route: complete each 30-note scale cell, then move the frame +1 fret" in lines, "PDF UP guidance")
    require("Descending route: use the same cards in reverse order and move -1 fret" in lines, "PDF DOWN guidance")
    start = lines.index("Scale tones (degrees 1-7)") + 1
    for index in range(13):
        group = lines[start + index * 5 : start + (index + 1) * 5]
        root = 5 + index
        expected = [f"{index + 1:02d}", KEYS[index] + (" major (octave)" if index == 12 else " major"),
                    f"fret {root}", f"{root - 1}-{root + 2}", "  ".join(SCALE_TONES[index])]
        require(group == expected, f"PDF route table rung {index + 1}")


def parse_rung(lines: list[str], number: int, page: int, pdf_lines: list[str]) -> dict[str, object]:
    root = number + 4
    key = KEYS[number - 1]
    start = 52 + (number - 1) * 14
    block = lines[start - 1 : start + 12]
    require(len(block) == 13, "TXT rung truncation")
    key_label = key.upper() + " MAJOR" + (" (OCTAVE)" if number == 13 else "")
    require(block[0] == f"RUNG {number:02d} OF 13 - {key_label} - ROOT ON LOW E FRET {root} - FRAME {root - 1}-{root + 2}", "TXT rung header")
    tones15 = list(SCALE_TONES[number - 1]) * 2 + [key]
    require(block[1] == "Scale tones across two octaves: " + " ".join(tones15), "TXT scale tones")
    require(block[2] == "30-note cell: low root to high root, repeat the high root, then return to the low root.", "TXT cell guidance")
    degrees = tokens(block[3], "Deg", 30)
    fingers = tokens(block[4], "Fng", 30)
    expected_degrees = list(ASC_DEGREES) + list(reversed(ASC_DEGREES))
    require(degrees == expected_degrees, "degree sequence")
    require(fingers == list(FINGERS), "finger sequence")
    require(pdf_lines[0] == f"ROOT E{root}  |  FRAME {root - 1}-{root + 2}", "PDF root/frame")
    require(pdf_lines[1] == "Notes: " + " ".join(SCALE_TONES[number - 1]) + " | " + " ".join(SCALE_TONES[number - 1]) + f" {key}", "PDF scale tones")
    require(pdf_lines[2] == "30-NOTE TWO-OCTAVE CELL", "PDF cell label")
    require(pdf_lines[3:11] == block[3:11], "PDF/TXT Deg/Fng/TAB mismatch")
    require(block[11] == "Finish on the low root, release pressure, and move the entire frame one fret in the route direction.", "TXT relocation guidance")
    require(pdf_lines[11] == "Return to the low root; release pressure; move the entire frame one fret.", "PDF relocation guidance")
    require(pdf_lines[12] == "D-start and U-start", "PDF pick-start guidance")
    require(block[12] == "", "TXT rung boundary")
    raw_rows = {string: block[5 + (5 - STRINGS.index(string))] for string in STRINGS}
    fret_rows = {s: tab_tokens(raw_rows[s], s, ASC_COUNTS[s] * 2) for s in STRINGS}
    require(fret_rows == expected_row_frets(root), "TAB shape/B-string offset")
    ascending = [(s, fret) for s in STRINGS for fret in fret_rows[s][: ASC_COUNTS[s]]]
    descending = [(s, fret) for s in reversed(STRINGS) for fret in fret_rows[s][ASC_COUNTS[s] :]]
    contacts = ascending + descending
    require(len(contacts) == 30 and contacts[14] == contacts[15], "30-note turn/repeated high root")
    midi = [TUNING_MIDI[s] + fret for s, fret in contacts]
    expected_midi = [40 + root + o for o in MAJOR_OFFSETS] + [40 + root + o for o in reversed(MAJOR_OFFSETS)]
    require(midi == expected_midi, "major-scale pitch/B-string tuning")
    spelled = tones15 + list(reversed(tones15))
    require(len(spelled) == 30, "tone spelling count")
    notes = []
    for i, ((string, fret), degree, finger, pitch, tone) in enumerate(zip(contacts, degrees, fingers, midi, spelled, strict=True), 1):
        notes.append({"index": i, "phase": "ascend" if i <= 15 else "descend", "string": string,
                      "fret": fret, "degree": degree, "finger": finger, "midi": pitch,
                      "source_tone": tone, "repeated_high_root_at_turn": i in (15, 16)})
    return {"rung": number, "key": key, "low_e_root_fret": root, "frame_frets": [root - 1, root + 2],
            "txt_header_line": start, "txt_rows": {"Deg": block[3], "Fng": block[4], **raw_rows},
            "pdf_page": page, "scale_tones_two_octaves": tones15,
            "cell_note_count": 30, "notes": notes,
            "canonical_item_id": None, "fixed_bpm": None, "note_per_click": None,
            "onset": None, "duration": None, "runtime_eligible": False, "admitted": False}


def build_candidate(root: Path = ROOT) -> dict[str, object]:
    lines, reader = source(root)
    up_route = "UP:   " + " > ".join(f"{key}({5 + i})" for i, key in enumerate(KEYS))
    down_route = "DOWN: " + " > ".join(f"{KEYS[i]}({5 + i})" for i in range(12, -1, -1))
    require(lines[40] == up_route, "TXT UP ladder route")
    require(lines[41] == down_route, "TXT DOWN ladder route")
    require(lines[233] == "FULL ROUND-TRIP CHALLENGE", "TXT end-of-rungs boundary")
    verify_pdf_route(reader)
    pdf = pdf_card_map(reader)
    rungs = [parse_rung(lines, n, *pdf[n]) for n in range(1, 14)]
    up = list(range(1, 14))
    down = list(range(12, 0, -1))
    require(len(up + down) == 25, "round-trip coverage")
    return {"schema": "fathom-detached-source-candidate.1", "workstream": "2.3.1.1.1",
            "level": 13, "source": {"txt": str(TXT_REL), "txt_sha256": TXT_SHA,
             "pdf": str(PDF_REL), "pdf_sha256": PDF_SHA, "pdf_pages": [2, 3, 4, 5, 6, 7]},
            "canonical_identity_assigned": False, "runtime_import_authorized": False,
            "curriculum_reviewed": False, "timing_interpreted": False,
            "guidance_only": {"cell_and_picking": lines[29:38], "practice_rule": lines[43:49],
                              "full_round_trip": lines[233:239]},
            "ladder": {"up_rungs": up, "down_rungs": down,
                       "turn": "finish rung 13 then return through 12-01; do not replay rung 13",
                       "round_trip_cells": 25, "round_trip_note_contacts": 750},
            "rungs": rungs, "exceptions": []}


def render(payload: dict[str, object]) -> bytes:
    return (json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")


def write_candidate(output: Path, root: Path = ROOT) -> tuple[int, str]:
    allowed = (root / BUILD_REL).resolve()
    require(output.parent.resolve().is_relative_to(allowed), "output outside P10 Level13 Build")
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
    print(f"LEVEL13 WHOLE LADDER DETACHED PASS bytes={size} sha256={digest} output={args.output}")


if __name__ == "__main__":
    main()
