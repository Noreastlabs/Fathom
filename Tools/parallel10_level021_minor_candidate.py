"""Detached whole-Level21 natural-minor ladder source projection."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
STEM = "Scale_Exercises_Section_III_Level_21_Natural_Minor_One_Fret_Neck_Ladder"
TXT_REL = Path(f"Notes/music/guitar project/TXT version/{STEM}.txt")
PDF_REL = Path(f"Notes/music/guitar project/PDF version/{STEM}.pdf")
TXT_SHA = "018db1d53df6b1b175c64d59f95809b3215d055f2c3361c90199ee8f3d75bf67"
PDF_SHA = "b8679699687ef8078f958563ce8f887e8e1083c486ef52d816a09c434d57d235"
BUILD_REL = Path("Build/parallel-10/2.3.1.1.1-level021-whole-minor-r01")
KEYS = ("A", "Bb", "B", "C", "C#", "D", "Eb", "E", "F", "F#", "G", "G#", "A")
TONES = (
    ("A", "B", "C", "D", "E", "F", "G"), ("Bb", "C", "Db", "Eb", "F", "Gb", "Ab"),
    ("B", "C#", "D", "E", "F#", "G", "A"), ("C", "D", "Eb", "F", "G", "Ab", "Bb"),
    ("C#", "D#", "E", "F#", "G#", "A", "B"), ("D", "E", "F", "G", "A", "Bb", "C"),
    ("Eb", "F", "Gb", "Ab", "Bb", "Cb", "Db"), ("E", "F#", "G", "A", "B", "C", "D"),
    ("F", "G", "Ab", "Bb", "C", "Db", "Eb"), ("F#", "G#", "A", "B", "C#", "D", "E"),
    ("G", "A", "Bb", "C", "D", "Eb", "F"), ("G#", "A#", "B", "C#", "D#", "E", "F#"),
    ("A", "B", "C", "D", "E", "F", "G"),
)
TUNING = {"E": 40, "A": 45, "D": 50, "G": 55, "B": 59, "e": 64}
STRINGS = ("E", "A", "D", "G", "B", "e")
DEGREES = ("1", "2", "b3", "4", "5", "b6", "b7", "8")
FINGERS = (1, 3, 4, 1, 3, 4, 1, 3)
MINOR_OFFSETS = (0, 2, 3, 5, 7, 8, 10, 12)


def require(ok: bool, detail: str) -> None:
    if not ok:
        raise ValueError(detail)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sources(root: Path = ROOT) -> tuple[list[str], PdfReader]:
    txt = (root / TXT_REL).read_bytes()
    pdf = (root / PDF_REL).read_bytes()
    require(sha256(txt) == TXT_SHA, "TXT source drift")
    require(sha256(pdf) == PDF_SHA, "PDF source drift")
    reader = PdfReader(str(root / PDF_REL))
    require(len(reader.pages) == 6, "PDF page count")
    return txt.decode("utf-8").splitlines(), reader


def pdf_route(reader: PdfReader) -> None:
    lines = [s.strip() for s in reader.pages[1].extract_text().splitlines()]
    require("Ascending route: complete each scale cell, then move the frame +1 fret" in lines, "PDF UP guidance")
    require("Descending route: use the same cards in reverse order and move -1 fret" in lines, "PDF DOWN guidance")
    start = lines.index("Scale tones (degrees 1-7)") + 1
    for i in range(13):
        root = 5 + i
        expected = [f"{i + 1:02d}", KEYS[i] + (" natural minor - octave" if i == 12 else " natural minor"),
                    f"fret {root}", f"{root}-{root + 3}", " ".join(TONES[i])]
        require(lines[start + i * 5 : start + (i + 1) * 5] == expected, f"PDF route rung {i + 1}")
    require("25 cells x 16 notes = 400 picked notes." in lines, "PDF route count")


def pdf_cards(reader: PdfReader) -> dict[int, tuple[int, list[str]]]:
    cards: dict[int, tuple[int, list[str]]] = {}
    for page in range(3, 7):
        text = reader.pages[page - 1].extract_text()
        chunks = re.split(r"(?m)^(\d{2})\s+([A-Z#]+ MINOR(?: \(OCTAVE\))?)\s*$", text)
        count = 4 if page < 6 else 1
        require(len(chunks) == 1 + count * 3, f"PDF page {page} card count")
        for j in range(count):
            n = int(chunks[1 + j * 3])
            label = chunks[2 + j * 3]
            require(n == (page - 3) * 4 + j + 1, "PDF rung order")
            require(label == KEYS[n - 1].upper() + " MINOR" + (" (OCTAVE)" if n == 13 else ""), "PDF rung key")
            cards[n] = (page, [line.strip() for line in chunks[3 + j * 3].splitlines() if line.strip()])
    require(list(cards) == list(range(1, 14)), "PDF whole-rung coverage")
    return cards


def degree_tokens(row: str) -> list[str]:
    require(row.startswith("Deg|") and row.endswith("|"), "Deg row format")
    values = re.findall(r"b?[1-8]", row[4:-1])
    require(len(values) == 16, "Deg count")
    return values


def checked_degree_tokens(row: str) -> list[str]:
    values = degree_tokens(row)
    require(values == list(DEGREES) + list(reversed(DEGREES)), "lowered b3/b6/b7 degree sequence")
    return values


def number_tokens(row: str, label: str, count: int) -> list[int]:
    require(row.startswith(label + "|") and row.endswith("|"), f"{label} row format")
    values = [int(x) for x in re.findall(r"\d+", row[len(label) + 1 : -1])]
    require(len(values) == count, f"{label} token count")
    return values


def tab_tokens(row: str, string: str, count: int) -> list[int]:
    require(row.startswith(string + "  |") and row.endswith("|"), f"{string} TAB row format")
    values = [int(x) for x in re.findall(r"\d+", row.split("|", 1)[1])]
    require(len(values) == count, f"{string} TAB token count")
    return values


def parse_rung(lines: list[str], n: int, page: int, pdf: list[str]) -> dict[str, object]:
    root = 4 + n
    key = KEYS[n - 1]
    start = 45 + (n - 1) * 14
    block = lines[start - 1 : start + 12]
    require(len(block) == 13, "TXT rung truncation")
    label = key.upper() + " NATURAL MINOR" + (" - OCTAVE" if n == 13 else "")
    require(block[0] == f"RUNG {n:02d} OF 13 - {label} - ROOT ON LOW E FRET {root} - FRAME {root}-{root + 3}", "TXT rung header")
    tones8 = list(TONES[n - 1]) + [key]
    require(block[1] == "Scale tones: " + " ".join(tones8), "TXT minor tones/spelling")
    require(block[2] == "16-note cell: ascend 1-8, repeat the octave root, descend 8-1.", "TXT cell instruction")
    require(pdf[0] == f"ROOT E{root}  |  FRAME {root}-{root + 3}", "PDF root/frame")
    require(pdf[1] == "Notes: " + "  ".join(tones8), "PDF minor tones/spelling")
    require(pdf[2] == "16-NOTE UP/DOWN CELL", "PDF cell label")
    require(pdf[3:11] == block[3:11], "PDF/TXT Deg/Fng/TAB mismatch")
    require(pdf[11] == "Finish on the low root; release pressure; move the entire frame one fret.", "PDF relocation")
    require(pdf[12] == "D-start and U-start", "PDF picking")
    require(block[11] == "Finish on the low root, release pressure, and move the entire frame one fret in the route direction.", "TXT relocation")
    require(block[12] == "", "TXT rung boundary")
    degrees = checked_degree_tokens(block[3])
    fingers = number_tokens(block[4], "Fng", 16)
    require(fingers == list(FINGERS) + list(reversed(FINGERS)), "minor finger sequence")
    rows = {s: block[5 + 5 - STRINGS.index(s)] for s in STRINGS}
    expected_frets = {"E": [root, root + 2, root + 3], "A": [root, root + 2, root + 3],
                      "D": [root, root + 2], "G": [], "B": [], "e": []}
    printed = {s: tab_tokens(rows[s], s, len(expected_frets[s]) * 2) for s in STRINGS}
    require(printed == {s: f + list(reversed(f)) for s, f in expected_frets.items()}, "3-3-2 TAB geometry")
    ascending = [(s, fret) for s in STRINGS for fret in expected_frets[s]]
    descending = list(reversed(ascending))
    contacts = ascending + descending
    require(len(contacts) == 16 and contacts[7] == contacts[8], "16-note/repeated octave root")
    midi = [TUNING[s] + fret for s, fret in contacts]
    require(midi == [40 + root + v for v in MINOR_OFFSETS] + [40 + root + v for v in reversed(MINOR_OFFSETS)], "natural-minor pitch")
    spelled = tones8 + list(reversed(tones8))
    notes = [{"index": i, "phase": "ascend" if i <= 8 else "descend", "string": s,
              "fret": fret, "degree": deg, "finger": finger, "midi": pitch,
              "source_tone": tone, "repeated_octave_root_at_turn": i in (8, 9)}
             for i, ((s, fret), deg, finger, pitch, tone)
             in enumerate(zip(contacts, degrees, fingers, midi, spelled, strict=True), 1)]
    return {"rung": n, "key": key, "low_e_root_fret": root, "frame_frets": [root, root + 3],
            "txt_header_line": start, "txt_rows": {"Deg": block[3], "Fng": block[4], **rows},
            "pdf_page": page, "scale_tones": tones8, "cell_note_count": 16, "notes": notes,
            "canonical_item_id": None, "fixed_bpm": None, "note_per_click": None,
            "onset": None, "duration": None, "runtime_eligible": False, "admitted": False}


def build_candidate(root: Path = ROOT) -> dict[str, object]:
    lines, reader = sources(root)
    up = "UP:   " + " > ".join(f"{key}({5 + i})" for i, key in enumerate(KEYS))
    down = "DOWN: " + " > ".join(f"{KEYS[i]}({5 + i})" for i in range(12, -1, -1))
    require(lines[32] == up, "TXT UP minor ladder route")
    require(lines[33] == down, "TXT DOWN minor ladder route")
    require(lines[225] == "FULL ROUND-TRIP CHALLENGE", "TXT rung-end boundary")
    require(lines[231] == "One complete route contains 25 cells x 16 notes = 400 picked notes.", "TXT route count")
    pdf_route(reader)
    cards = pdf_cards(reader)
    rungs = [parse_rung(lines, n, *cards[n]) for n in range(1, 14)]
    return {"schema": "fathom-detached-source-candidate.1", "workstream": "2.3.1.1.1",
            "level": 21, "source": {"txt": str(TXT_REL), "txt_sha256": TXT_SHA,
             "pdf": str(PDF_REL), "pdf_sha256": PDF_SHA, "pdf_pages": [2, 3, 4, 5, 6]},
            "canonical_identity_assigned": False, "runtime_import_authorized": False,
            "curriculum_reviewed": False, "timing_interpreted": False,
            "guidance_only": {"minor_formula": lines[13:19], "practice_rule": lines[35:43],
                              "round_trip": lines[225:232]},
            "ladder": {"up_rungs": list(range(1, 14)), "down_rungs": list(range(12, 0, -1)),
                       "round_trip_cells": 25, "round_trip_note_contacts": 400,
                       "turn": "finish rung 13 then return through 12-01; do not replay rung 13"},
            "rungs": rungs, "exceptions": []}


def render(data: dict[str, object]) -> bytes:
    return (json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")


def write_candidate(output: Path, root: Path = ROOT) -> tuple[int, str]:
    allowed = (root / BUILD_REL).resolve()
    require(output.parent.resolve().is_relative_to(allowed), "output outside P10 Level21 Build")
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
    print(f"LEVEL21 WHOLE MINOR DETACHED PASS bytes={size} sha256={digest} output={args.output}")


if __name__ == "__main__":
    main()
