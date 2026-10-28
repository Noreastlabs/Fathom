#!/usr/bin/env python3
"""Source-bound, nonadmitted Level 38 fixed-key-A phrase candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from pypdf import PdfReader


STEM = "Scale_Exercises_Section_IV_Level_38_Major_Pentatonic_Call_and_Response_Phrasing_and_Improvisation_Synthesis_Fixed_Key_A"
TXT_REL = f"Notes/music/guitar project/TXT version/{STEM}.txt"
PDF_REL = f"Notes/music/guitar project/PDF version/{STEM}.pdf"
TXT_BYTES = 38000
PDF_BYTES = 47375
TXT_SHA = "d34fe379da8b7dd4fbe7d70beb7cef6f7e6e81a6c9fb52cc7ecdca19d4c7e640"
PDF_SHA = "10adb1e628f5dbcada38494a60ca648450abc183f2ec8ed977fad1fbd0f8844d"
PDF_PAGES = 18
MODULE_BOUNDS = {"A": (0, 10, 55, 37), "B": (10, 26, 97, 62), "C": (26, 33, 30, 23), "D": (33, 45, 60, 60), "E": (45, 57, 70, 55)}
PITCH_CLASS = {"A": 9, "B": 11, "C#": 1, "D*": 2, "E": 4, "F#": 6, "G#*": 8}
DEGREE = {"A": "1", "B": "2", "C#": "3", "D*": "*R", "E": "5", "F#": "6", "G#*": "*3"}
OPEN_PITCH = {"E": 4, "A": 9, "D": 2, "G": 7, "B": 11, "e": 4}
TAB_STRINGS = ("e", "B", "G", "D", "A", "E")
COUNTS = ("1", "&", "2", "&", "3", "&", "4", "&")
SEAM_TARGETS = (
    "Targets: A root | F# over D | E over E | C# over A",
    "Targets: C# over A | A over D | E over E | C# over A",
    "Targets: E over A | F# over D | E over E | C# over A",
    "Targets: A over A | F# over D | E/G# over E | C# over A",
)
CHORUS_CHORDS = ("A", "A", "A", "A", "D", "D", "A", "A", "E", "D", "A", "E")
CHORUS_POSITIONS = ("P1", "P2", "P2", "P3", "P3", "P4", "P4", "P5", "P5", "P4", "P3", "P1")
STRONG_TARGETS = {"A": {"A", "C#", "E"}, "D": {"F#", "A", "D*"}, "E": {"E", "B", "G#*"}}


def _pin(path: Path, size: int, sha: str) -> bytes:
    data = path.read_bytes()
    if len(data) != size or hashlib.sha256(data).hexdigest() != sha:
        raise ValueError(f"source identity drift: {path}")
    return data


def _cells(row: str, name: str) -> list[str]:
    if not row.startswith(f"{name:<4}|") or len(row) != 46 or row[-1] != "|":
        raise ValueError(f"malformed {name} row: {row!r}")
    return [row[5 + 5 * i : 10 + 5 * i].strip() for i in range(8)]


def _expected_page(index: int) -> int:
    if index < 10:
        return (3, 3, 3, 3, 4, 4, 4, 4, 5, 5)[index]
    if index < 26:
        return 6 + (index - 10) // 4
    if index < 33:
        return 10
    if index < 45:
        return 11 + (index - 33) // 4
    return 14 + (index - 45) // 4


def _identity(index: int, lines: list[str], row_index: int) -> dict:
    if index < 10:
        pair = index // 2 + 1
        heading = f"P{pair} - "
        if not any(line.startswith(heading) for line in lines[max(0, row_index - 20) : row_index]):
            raise ValueError(f"local pair heading missing: {pair}")
        label = "CALL" if index % 2 == 0 else "RESPONSE"
        if lines[row_index - 1] != label:
            raise ValueError(f"local phrase label drift: {index}")
        return {"module": "A", "group": f"P{pair}", "phrase": label, "position": f"P{pair}", "harmony": "A"}
    if index < 26:
        seam = (index - 10) // 4 + 1
        within = (index - 10) % 4
        if f"SEAM {seam} - P{seam} TO P{seam+1}" not in lines:
            raise ValueError(f"seam heading missing: {seam}")
        label = (f"A call - P{seam}" if within == 0 else f"D response - P{seam+1}" if within == 1 else f"E call - P{seam+1}" if within == 2 else f"A answer - P{seam}")
        if seam == 4 and within == 0:
            label = "A call - P4/P5"
        if seam == 4 and within == 3:
            label = "A answer - P5"
        if lines[row_index - 1] != label:
            raise ValueError(f"seam phrase label drift: {index}")
        return {"module": "B", "group": f"SEAM {seam}", "phrase": label, "position": label.split(" - ")[-1], "harmony": ("A", "D", "E", "A")[within], "target_guidance": SEAM_TARGETS[seam - 1]}
    if index < 33:
        option = index - 26
        labels = ("Seed question - P2 over A", "1. Exact echo", "2. Harmonic answer over D", "3. Contour contrast over E", "4. Position sequence - P3", "5. Rhythmic displacement", "6. Expansion and closure")
        if lines[row_index - 1] != labels[option]:
            raise ValueError(f"motif option label drift: {index}")
        return {"module": "C", "group": "motif transformations", "phrase": labels[option], "option": option, "harmony": ("A", "A", "D", "E", "A", "A", "A")[option]}
    if index < 45:
        density = ("SPARSE", "MEDIUM", "DENSE")[(index - 33) // 4]
        within = (index - 33) % 4
        label = ("A BAR", "D BAR", "E BAR", "A BAR")[within]
        if lines[row_index - 1] != label or not any(line.startswith(density + " - ") for line in lines[max(0, row_index - 55) : row_index]):
            raise ValueError(f"density heading drift: {index}")
        return {"module": "D", "group": density, "phrase": label, "bar_in_group": within + 1, "harmony": ("A", "D", "E", "A")[within]}
    number = index - 45
    match = re.fullmatch(r"(\d+)\. (.+) - (P\d)", lines[row_index - 1])
    if not match or int(match.group(1)) != number + 1 or match.group(3) != CHORUS_POSITIONS[number]:
        raise ValueError(f"chorus label/position drift: {index}")
    return {"module": "E", "group": "model 12-bar chorus", "phrase": lines[row_index - 1], "bar_in_group": number + 1, "position": match.group(3), "harmony": CHORUS_CHORDS[number]}


def _parse_bar(index: int, line_index: int, lines: list[str], pdf_text: str) -> dict:
    rows = lines[line_index : line_index + 10]
    if len(rows) != 10:
        raise ValueError(f"incomplete bar {index + 1}")
    names = ("Cnt", "Nte", "Deg", "Atk", *TAB_STRINGS)
    data = {name: _cells(row, name) for name, row in zip(names, rows)}
    if data["Cnt"] != list(COUNTS):
        raise ValueError(f"count grid drift: bar {index + 1}")
    for name, row in zip(names, rows):
        if name in ("Cnt", "Nte", "Deg", "Atk") or row[5:-1].strip():
            if row not in pdf_text:
                raise ValueError(f"TXT/PDF {name} row mismatch: bar {index + 1}")
    ident = _identity(index, lines, line_index)
    slots = []
    for slot in range(8):
        note, deg, attack = (data[name][slot] for name in ("Nte", "Deg", "Atk"))
        fretted = [(string, data[string][slot]) for string in TAB_STRINGS if data[string][slot]]
        if note in ("r", "="):
            if note != deg or note != attack or fretted:
                raise ValueError(f"rest/hold semantics: bar {index + 1}, slot {slot + 1}")
            if note == "=" and (slot == 0 or slots[-1]["kind"] == "rest"):
                raise ValueError(f"orphan hold: bar {index + 1}")
            slots.append({"slot": slot + 1, "printed_count": COUNTS[slot], "kind": "rest" if note == "r" else "hold", "note": note, "degree": deg, "attack_mark": attack, "contact": None, "onset": None, "duration": None, "performed_pick": None})
            continue
        if note not in PITCH_CLASS or deg != DEGREE[note] or attack not in ("P", "h", "p", "s", "b") or len(fretted) != 1:
            raise ValueError(f"note/degree/attack/contact: bar {index + 1}, slot {slot + 1}")
        if note == "D*" and ident["harmony"] != "D" or note == "G#*" and ident["harmony"] != "E":
            raise ValueError(f"completion tone on wrong chord: bar {index + 1}")
        string, glyph = fretted[0]
        match = re.fullmatch(r"(h|p|/|b)?(\d{1,2})(~)?", glyph)
        if not match:
            raise ValueError(f"TAB glyph: bar {index + 1}, slot {slot + 1}: {glyph}")
        prefix, fret_text, sustain = match.groups()
        expected_prefix = {"P": None, "h": "h", "p": "p", "s": "/", "b": "b"}[attack]
        if prefix != expected_prefix:
            raise ValueError(f"attack/TAB mismatch: bar {index + 1}, slot {slot + 1}")
        fret = int(fret_text)
        if (OPEN_PITCH[string] + fret) % 12 != PITCH_CLASS[note]:
            raise ValueError(f"TAB pitch mismatch: bar {index + 1}, slot {slot + 1}")
        slots.append({"slot": slot + 1, "printed_count": COUNTS[slot], "kind": "sounded", "note": note, "degree": deg, "attack_mark": attack, "contact": {"string": string, "fret": fret, "printed_glyph": glyph, "sustain_mark": bool(sustain)}, "onset": None, "duration": None, "performed_pick": None})
    first_sounded = next(slot for slot in slots if slot["kind"] == "sounded")
    if first_sounded["note"] not in STRONG_TARGETS[ident["harmony"]]:
        raise ValueError(f"first-sounding harmony target mismatch: bar {index + 1}")
    if ident["module"] in ("B", "D", "E") and slots[0]["kind"] != "sounded":
        raise ValueError(f"beat-1 target absent: bar {index + 1}")
    return {**ident, "bar": index + 1, "pdf_page": _expected_page(index), "txt_line": line_index + 1, "source_rows": dict(zip(names, rows)), "slots": slots, "sounding_tones": sum(slot["kind"] == "sounded" for slot in slots), "picked_attack_marks": sum(slot["attack_mark"] == "P" for slot in slots)}


def _require_guidance(lines: list[str], pdf_pages: list[str]) -> None:
    txt = "\n".join(lines)
    required = (
        "CORE WRITTEN COUNTS", "Complete written workout: 312 sounding tones / 237 pick attacks",
        "Progression for every phrase: | A | D | E | A |.", "Position route: P1 -> P2 -> P2 -> P3 -> P3 -> P4 -> P4 -> P5 -> P5 -> P4 -> P3 -> P1.",
        "CHORUS 1 - SKELETON AND SPACE", "CHORUS 2 - MOTIF DEVELOPMENT AND POSITION MOVEMENT", "CHORUS 3 - FREE SYNTHESIS",
        "Add 2 BPM after three clean choruses", 
        "RESPONSE CARDS", "PRACTICE PROGRESSION", "ERROR DIAGNOSIS", "ADVANCEMENT RULES", "MASTERY GATE - SECTION IV COMPLETE", "NEXT SECTION",
    )
    for phrase in required:
        if phrase not in txt:
            raise ValueError(f"TXT guidance drift: {phrase}")
    for phrase in SEAM_TARGETS:
        if phrase not in txt:
            raise ValueError(f"seam target drift: {phrase}")
    pdf_required = {1: ("312 written sounding tones and 237 pick attacks",), 2: ("Chord", "Completion tone", "Picked attack"), 17: ("Max 7 tones per bar", "Score 0-2", "Harmony", "Motif", "Space", "Neck movement", "Articulation", "Recovery", "Keep the first complete take.", "10/12 or better on two separate days"), 18: ("Eight-phase practice progression", "Mastery gate - Section IV complete", "Score /12", "NEXT - SECTION V")}
    for page, phrases in pdf_required.items():
        for phrase in phrases:
            if phrase not in pdf_pages[page - 1]:
                raise ValueError(f"PDF guidance drift p{page}: {phrase}")


def build_candidate(root: Path) -> dict:
    txt_data = _pin(root / TXT_REL, TXT_BYTES, TXT_SHA)
    pdf_data = _pin(root / PDF_REL, PDF_BYTES, PDF_SHA)
    lines = txt_data.decode("utf-8").splitlines()
    reader = PdfReader(root / PDF_REL)
    if len(reader.pages) != PDF_PAGES:
        raise ValueError("PDF page count drift")
    pdf_pages = [page.extract_text() or "" for page in reader.pages]
    for number, page in enumerate(pdf_pages, 1):
        if f"Page {number} of 18" not in page:
            raise ValueError(f"PDF page identity drift: {number}")
    _require_guidance(lines, pdf_pages)
    bar_lines = [i for i, line in enumerate(lines) if line.startswith("Cnt |")]
    if len(bar_lines) != 57:
        raise ValueError(f"bar count drift: {len(bar_lines)}")
    bars = [_parse_bar(i, line, lines, pdf_pages[_expected_page(i) - 1]) for i, line in enumerate(bar_lines)]
    modules = []
    for name, (start, stop, expected_notes, expected_picks) in MODULE_BOUNDS.items():
        group = bars[start:stop]
        notes = sum(bar["sounding_tones"] for bar in group)
        picks = sum(bar["picked_attack_marks"] for bar in group)
        if (notes, picks) != (expected_notes, expected_picks):
            raise ValueError(f"module {name} printed count drift: {(notes, picks)}")
        modules.append({"module": name, "written_bar_count": stop - start, "sounding_tones": notes, "picked_attack_marks": picks, "bars": group})
    if sum(module["sounding_tones"] for module in modules) != 312 or sum(module["picked_attack_marks"] for module in modules) != 237:
        raise ValueError("whole-workout count drift")
    txt = "\n".join(lines)
    return {
        "schema": "fathom.detached-source-candidate.1", "section": "IV", "level": 38, "wbs_id": "2.3.1.1.1",
        "source": {"txt_path": TXT_REL, "txt_bytes": TXT_BYTES, "txt_sha256": TXT_SHA, "pdf_path": PDF_REL, "pdf_bytes": PDF_BYTES, "pdf_sha256": PDF_SHA, "pdf_pages": PDF_PAGES, "written_pdf_pages": list(range(3, 17))},
        "fixed_key": "A major pentatonic", "scale_tones": ["A", "B", "C#", "E", "F#"], "harmony": ["A", "D", "E"],
        "written_bar_count": 57, "sounding_tone_count": 312, "picked_attack_mark_count": 237, "modules": modules,
        "printed_guidance": {"kind": "printed_instruction", "txt_full_text": txt, "pdf_extracted_pages": [{"page": i + 1, "extracted_text": page} for i, page in enumerate(pdf_pages)], "seam_targets": list(SEAM_TARGETS), "model_chord_route": list(CHORUS_CHORDS), "model_position_route": list(CHORUS_POSITIONS), "pdf_page1_overview": "duplicate seed/response illustration; not an additional written bar"},
        "source_exceptions": [
            {"code": "CHORUS3_DENSITY_LIMIT_PDF_ONLY", "status": "Pending Curriculum review", "txt_guidance": "Use all five positions and horizontal lanes. Preserve strong beat-1 targets, include at least two bars of deliberate space, use D* and G#* only on their supporting chords, and finish on an A root without a last-second fret search.", "pdf_guidance": "Max 7 tones per bar; at least two deliberately sparse bars", "decision": "Retain both instructions; do not infer a performed density or silently impose the PDF-only maximum on TXT wording."},
            {"code": "ADVANCEMENT_CRITERIA_DIFFERENT", "status": "Pending Curriculum review", "txt_guidance": "Add 2 BPM after three clean choruses at the current constraint.", "pdf_guidance": "Keep the first complete take. Score it before recording again. Advance after 10/12 or better on two separate days.", "decision": "Retain both source-specific criteria; do not equate a clean chorus with a 10/12 score or infer any completed recording."},
        ],
        "canonical_ids": None, "review": "Pending", "runtime_eligible": False, "imported": False, "admitted": False,
        "performed_score": None, "performed_mastery": None,
        "pending": ["Curriculum review of PDF-only Chorus 3 density limit and different advancement criteria", "independent whole-source review", "canonical IDs and runtime admission", "performed mastery gate"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    candidate = build_candidate(args.root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(candidate, sort_keys=True, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"LEVEL38 CANDIDATE PASS bars=57 tones=312 picked_marks=237 output={args.output}")


if __name__ == "__main__":
    main()
