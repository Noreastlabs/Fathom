"""Detached, fail-closed Level 10 Set 2 source projection (no admission)."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
TXT_REL = Path("Notes/music/guitar project/TXT version/108_Finger_Permutations_Level_10_Odd_Count_Position_Transfer.txt")
PDF_REL = Path("Notes/music/guitar project/PDF version/108_Finger_Permutations_Level_10_Odd_Count_Position_Transfer.pdf")
TXT_SHA = "e5ed078c62295adbb5f6bf00e6821e6eee0b2da73ef42c1714421158b5273226"
PDF_SHA = "1dafdcd177343f0ea147a5479ad654397d85f4b374cf960e264a230db965496b"
BUILD_ROOT = ROOT / "Build/parallel-10/2.3.1.1.1-level010-set02-r01"
CODES = ("1321", "1323", "1324", "1341", "1342", "1343", "1412", "1413", "1414", "1421", "1423", "1424")
STRINGS = {"UP": ("E", "A", "D", "G", "B", "e"), "DOWN": ("e", "B", "G", "D", "A", "E")}
MODE = {
    "A": {"heading_line": 488, "first_card_line": 493, "pdf_page": 4, "split": 3, "landing": 4, "name": "3+1 late shift"},
    "B": {"heading_line": 710, "first_card_line": 715, "pdf_page": 5, "split": 1, "landing": 2, "name": "1+3 early shift"},
}
PICKING = {
    "A": "D-start D-U-D | U; U-start U-D-U | D; no pick reset",
    "B": "D-start D | U-D-U; U-start U | D-U-D; no pick reset",
}


def require(test: bool, message: str) -> None:
    if not test:
        raise ValueError(message)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def pinned_sources(root: Path = ROOT) -> list[str]:
    txt = (root / TXT_REL).read_bytes()
    pdf = (root / PDF_REL).read_bytes()
    require(sha256(txt) == TXT_SHA, "TXT source drift")
    require(sha256(pdf) == PDF_SHA, "PDF source drift")
    return txt.decode("utf-8").splitlines()


def parse_row(row: str, prefix: str) -> tuple[str, tuple[int, ...]]:
    require(row.startswith(prefix + "|") and row.endswith("|"), f"invalid {prefix} row: {row}")
    cells = row[2:-1].split("|")
    require(len(cells) == 2, f"invalid {prefix} cell count")
    groups = tuple(tuple(int(n) for n in re.findall(r"\d+", cell)) for cell in cells)
    require(all(groups), f"empty {prefix} cell")
    return row, tuple(groups[0] + groups[1])


def pdf_cards(pdf_path: Path, mode: str) -> dict[int, dict[str, object]]:
    info = MODE[mode]
    text = PdfReader(str(pdf_path)).pages[int(info["pdf_page"]) - 1].extract_text()
    require(f"Set 2 of 9 - Mode {mode}" in text and "Exercises 013-024" in text, "PDF page/set/mode mismatch")
    chunks = re.split(r"(?m)^(\d{3})\s+(\d{4})\s*$", text)
    require(len(chunks) == 1 + 12 * 3, "PDF card count")
    out: dict[int, dict[str, object]] = {}
    for i in range(12):
        number = int(chunks[1 + 3 * i])
        code = chunks[2 + 3 * i]
        lines = [line.strip() for line in chunks[3 + 3 * i].splitlines() if line.strip()]
        require(number == 13 + i and code == CODES[i], "PDF card identity/order mismatch")
        expected_mode = "3+1 LATE SHIFT" if mode == "A" else "1+3 EARLY SHIFT"
        require(lines[0] == expected_mode, "PDF mode mismatch")
        require(lines[1] == "UP" and lines[5] == "DN", "PDF direction/order mismatch")
        require(lines[2] == "E>A>D>G>B>e   P5>P7", "PDF UP route mismatch")
        require(lines[6] == "e>B>G>D>A>E   P7>P5", "PDF DOWN route mismatch")
        require(lines[3].startswith("F|") and lines[4].startswith("S|"), "PDF UP rows missing")
        require(lines[7].startswith("F|") and lines[8].startswith("S|"), "PDF DOWN rows missing")
        require(lines[9] == f"landing note {info['landing']}; no pick reset", "PDF landing mismatch")
        out[number] = {"code": code, "UP": (lines[3], lines[4]), "DOWN": (lines[7], lines[8])}
    return out


def parse_txt_card(lines: list[str], mode: str, number: int, pdf: dict[str, object]) -> dict[str, object]:
    info = MODE[mode]
    start = int(info["first_card_line"]) + (number - 13) * 18
    card = lines[start - 1 : start + 17]
    require(len(card) == 18, "truncated TXT card")
    code = CODES[number - 13]
    require(card[0] == f"Exercise {number:03d}: {code}", "TXT card identity/order mismatch")
    require(card[17] == "", "TXT card boundary mismatch")
    require(pdf["code"] == code, "PDF/TXT code mismatch")
    out_routes: list[dict[str, object]] = []
    for direction, offset in (("UP", 1), ("DOWN", 9)):
        source, destination = (("P5", "P7") if direction == "UP" else ("P7", "P5"))
        expected = (f"SHIFT {direction} - {source} to {destination}; "
                    + ("digits 1-3 in " + source + ", digit 4 in " + destination if mode == "A"
                       else "digit 1 in " + source + ", digits 2-4 in " + destination)
                    + ("; play bottom line first: E-A-D-G-B-e" if direction == "UP"
                       else "; play top line first: e-B-G-D-A-E"))
        require(card[offset] == expected, f"TXT {mode}/{direction} direction mismatch")
        frow, fingers = parse_row(card[offset + 1], "F")
        require(fingers == tuple(int(d) for d in code), "finger code mismatch")
        pdf_frow, pdf_srow = pdf[direction]
        require(frow == pdf_frow, "PDF/TXT finger template mismatch")
        first_count = int(info["split"])
        require(len(re.findall(r"\d+", frow.split("|")[1])) == first_count, "finger shift cell mismatch")
        for string in STRINGS[direction]:
            row_idx = (5 - STRINGS[direction].index(string)) if direction == "UP" else STRINGS[direction].index(string)
            # TXT rows are printed e,B,G,D,A,E; UP is performed bottom-first.
            tab_line = start + offset + 2 + row_idx
            raw = card[offset + 2 + row_idx]
            require(raw.startswith(string + "|"), "TXT string order mismatch")
            _, frets = parse_row("S" + raw[1:], "S")
            require(len(frets) == 4, "TAB note count mismatch")
            require("S" + raw[1:] == pdf_srow, "PDF/TXT TAB template mismatch")
            require(len(re.findall(r"\d+", raw.split("|")[1])) == first_count, "TAB shift cell mismatch")
            notes = []
            for position, (finger, fret) in enumerate(zip(fingers, frets, strict=True), 1):
                frame = source if position <= first_count else destination
                expected_fret = (5 if frame == "P5" else 7) + finger - 1
                require(fret == expected_fret, "finger/frame/fret mismatch")
                notes.append({"note_index": position, "string": string, "finger": finger,
                              "fret": fret, "frame": frame,
                              "landing_note": position == info["landing"]})
            out_routes.append({"direction": direction, "string": string,
                               "play_order": STRINGS[direction].index(string) + 1,
                               "txt_tab_line": tab_line, "txt_tab_row": raw,
                               "txt_finger_line": start + offset + 1, "txt_finger_row": frow,
                               "pdf_page": info["pdf_page"], "pdf_finger_template": pdf_frow,
                               "pdf_tab_template": pdf_srow, "notes": notes})
    require(len(out_routes) == 12, "route count mismatch")
    return {"mode": mode, "mode_name": info["name"], "code": code,
            "txt_card_line": start, "pdf_page": info["pdf_page"],
            "shift_after_note": info["split"], "landing_note_index": info["landing"],
            "picking_instruction": PICKING[mode], "routes": out_routes}


def build_candidate(root: Path = ROOT) -> dict[str, object]:
    lines = pinned_sources(root)
    require(lines[483] == "SET 2 OF 9 - EXERCISES 013-024", "TXT Set 2 heading mismatch")
    require(lines[931] == "SET 3 OF 9 - EXERCISES 025-036", "TXT next-set boundary mismatch")
    require(lines[487] == "MODE A - 3+1 LATE SHIFT", "TXT Mode A heading mismatch")
    require(lines[709] == "MODE B - 1+3 EARLY SHIFT", "TXT Mode B heading mismatch")
    cards = {mode: pdf_cards(root / PDF_REL, mode) for mode in MODE}
    records = []
    for number in range(13, 25):
        modes = [parse_txt_card(lines, mode, number, cards[mode][number]) for mode in ("A", "B")]
        records.append({"exercise_number": number, "finger_code": CODES[number - 13], "modes": modes,
                        "canonical_item_id": None, "runtime_eligible": False, "admitted": False,
                        "fixed_bpm": None, "note_per_click": None, "onset": None, "duration": None})
    require(sum(len(m["routes"]) for r in records for m in r["modes"]) == 288, "total route count mismatch")
    return {"schema": "fathom-detached-source-candidate.1", "workstream": "2.3.1.1.1",
            "level": 10, "set": 2, "source": {"txt": str(TXT_REL), "txt_sha256": TXT_SHA,
             "txt_lines": [484, 931], "pdf": str(PDF_REL), "pdf_sha256": PDF_SHA, "pdf_pages": [4, 5]},
            "canonical_identity_assigned": False,
            "runtime_import_authorized": False, "curriculum_reviewed": False,
            "timing_interpreted": False, "records": records}


def render(candidate: dict[str, object]) -> bytes:
    return (json.dumps(candidate, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def write_candidate(output: Path, root: Path = ROOT) -> tuple[int, str]:
    allowed = (root / "Build/parallel-10/2.3.1.1.1-level010-set02-r01").resolve()
    require(output.parent.resolve().is_relative_to(allowed), "output outside P10 Build allowance")
    require(not output.exists() and not output.is_symlink(), "output already exists or is symlink")
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
    print(f"LEVEL10 SET2 DETACHED PASS bytes={size} sha256={digest} output={args.output}")


if __name__ == "__main__":
    main()
