#!/usr/bin/env python3
"""Convert pinned Level 86 TXT/PDF into detached groove tasks and contact slots."""

from __future__ import annotations

import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path
import re

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
STEM = "Guitar_Exercises_Section_XII_Level_86_Funk_and_RnB_Groove_Vocabulary_Sixteenth_Muting_Chord_Stabs_Ghost_Hierarchy_Syncopated_Triads_and_Bass_Space"
TXT = Path("Notes/music/guitar project/TXT version") / (STEM + ".txt")
PDF = Path("Notes/music/guitar project/PDF version") / (STEM + ".pdf")
MAP = Path("Results/parallel-01/exercises/inventory/20260922T180500Z-2.3-curriculum-v1-source-inventory-evidence/curriculum-source-map.json")
OUT = Path("Build/parallel-07/2.3.1.3.1-level086-whole-r01")
PINS = {"txt": (1483, "8730bcc844ca1a1f0dfeae22701be5ada9214926e412c9646643ba536cd7953e"),
        "pdf": (41765, "74d4db847ed27ce9e11641bbc0120cecfb7818f390df8c0680ce2cca708d3565")}
COUNTS = {"A": 144, "B": 128, "C": 144, "D": 128, "E": 160,
          "F": 160, "G": 128, "H": 192, "I": 256, "J": 64}
TABLES = {
    "workload": (1, ["Module", "Exercise", "Events"], 10),
    "hierarchy": (2, ["Level", "Symbol", "Job"], 5),
    "ghost_cells": (3, ["Cell", "1 e & a | 2 e & a | 3 e & a | 4 e & a", "Goal"], 6),
    "stab_duration": (4, ["Duration", "Exercise", "Release cue"], 6),
    "syncopated_chords": (5, ["Cell", "Harmony", "Contact points"], 8),
    "bass_space": (6, ["Bass event", "Guitar rule"], 6),
    "funk_pockets": (7, ["Name", "Chord", "Pattern", "Purpose"], 8),
    "rnb_pockets": (8, ["Study", "Harmony", "Primary behavior"], 8),
    "register_rotation": (9, ["Pass", "Voicing / register", "Instruction"], 6),
    "capstone_sections": (14, ["Bars", "Harmony", "Feel", "Voicing", "Dynamic"], 8),
    "recovery": (15, ["Failure", "Immediate repair"], 8),
}
SLOT_MEANING = {"P": "pitched_chord", "x": "accented_mute", "g": "soft_ghost",
                "-": "air_stroke", "~": "sustain_no_new_attack"}


class CandidateError(ValueError):
    pass


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read(root: Path, rel: Path, pin: tuple[int, str]) -> bytes:
    path = root / rel
    if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root.resolve()):
        raise CandidateError(f"SOURCE_PATH_INVALID {rel}")
    data = path.read_bytes()
    if (len(data), sha(data)) != pin:
        raise CandidateError(f"PINNED_INPUT_DRIFT {rel}")
    return data


def source_map(root: Path) -> dict:
    row = next((r for r in json.loads((root / MAP).read_text())["rows"] if r["level"] == 86), None)
    expected = {"section": "XII", "wbs_owner": "2.3.1.3.1", "txt_path": str(TXT),
                "pdf_path": str(PDF), "txt_bytes": PINS["txt"][0],
                "pdf_bytes": PINS["pdf"][0], "txt_sha256": PINS["txt"][1],
                "pdf_sha256": PINS["pdf"][1], "pair_status": "exact_stem_pair",
                "conversion_status": "not_converted", "stable_ids_assigned": False,
                "runtime_eligible": False, "imported": False, "admitted": False}
    if row is None or any(row.get(k) != v for k, v in expected.items()):
        raise CandidateError("SOURCE_MAP_IDENTITY_OR_STATUS_DRIFT")
    return row


def table(page: str, heads: list[str], n: int, label: str) -> list[dict]:
    lines = page.splitlines()
    found = [i for i in range(len(lines)) if lines[i:i + len(heads)] == heads]
    if len(found) != 1:
        raise CandidateError(f"PDF_TABLE_HEADER {label}")
    width = len(heads)
    cells = lines[found[0] + width:found[0] + width + width * n]
    if len(cells) != width * n:
        raise CandidateError(f"PDF_TABLE_LENGTH {label}")
    return [dict(zip(heads, cells[i * width:(i + 1) * width], strict=True))
            for i in range(n)]


def task(module: str, ordinal: int, kind: str, page: int, fields: dict,
         txt_line: int | None = None) -> dict:
    return {"local_key": f"l86-{module.lower()}-{kind}-{ordinal:02d}",
            "module": module, "kind": kind, "source": {"pdf_page": page,
            "txt_line": txt_line}, "fields": fields, "canonical_task_id": None,
            "performed_result": None, "observed_score": None}


def slots(module: str, kind: str, row: int, page: int, mask: str,
          allowed_lengths: tuple[int, ...]) -> list[dict]:
    compact = re.sub(r"[\s|]", "", mask)
    if len(compact) not in allowed_lengths or any(c not in SLOT_MEANING for c in compact):
        raise CandidateError(f"MASK_INVALID {module}:{kind}:{row}:{mask}")
    return [{"local_key": f"l86-{module.lower()}-{kind}-{row:02d}-slot-{i:02d}",
             "module": module, "source": {"pdf_page": page, "row": row},
             "slot": i, "beat": (i - 1) // 4 + 1,
             "subdivision": ("1", "e", "&", "a")[(i - 1) % 4],
             "symbol": char, "action": SLOT_MEANING[char],
             "sounded": char in "Pxg", "pitch": None, "chord_voicing": None,
             "onset_q": None, "duration_q": None, "canonical_event_id": None}
            for i, char in enumerate(compact, 1)]


def build(root: Path = ROOT) -> dict:
    txt = read(root, TXT, PINS["txt"])
    pdf = read(root, PDF, PINS["pdf"])
    inventory = source_map(root)
    lines = txt.decode().splitlines()
    pages = [p.extract_text() or "" for p in PdfReader(BytesIO(pdf)).pages]
    if len(lines) != 43 or len(pages) != 15 or not pages[0].startswith(
            "Guitar Exercises - Section XII, Level 86"):
        raise CandidateError("SOURCE_LINE_PAGE_BOUNDARY")
    parsed = {name: table(pages[page - 1], heads, n, name)
              for name, (page, heads, n) in TABLES.items()}
    for i, r in enumerate(parsed["workload"]):
        module = chr(ord("A") + i)
        literal = f"{module}. {r['Exercise']} - {r['Events']} events"
        if r["Module"] != module or int(r["Events"]) != COUNTS[module] or literal not in lines:
            raise CandidateError(f"TXT_PDF_WORKLOAD_PARITY {module}")
    if sum(COUNTS.values()) != 1504 or "TOTAL\n1504" not in pages[0] or \
            "COMPLETE WRITTEN WORKLOAD: 1504 events" not in lines:
        raise CandidateError("TOTAL_WORKLOAD_INVALID")
    if [r["Symbol"] for r in parsed["hierarchy"]] != list("Pxg-~"):
        raise CandidateError("CONTACT_HIERARCHY_INVALID")
    tasks = []
    grid_slots = []
    contact_events = []

    for i, r in enumerate(parsed["hierarchy"], 1):
        tasks.append(task("A", i, "contact_hierarchy_reference", 2, r))
    for i, r in enumerate(parsed["ghost_cells"], 1):
        if int(r["Cell"]) != i:
            raise CandidateError(f"A_CELL_NUMBER {i}")
        mask = r["1 e & a | 2 e & a | 3 e & a | 4 e & a"]
        cell_slots = slots("A", "ghost_cell", i, 3, mask, (16,))
        grid_slots.extend(cell_slots)
        tasks.append(task("A", i, "ghost_hierarchy_cell", 3,
                          {"mask": mask, "goal": r["Goal"], "slot_count": 16,
                           "substitute_chords": ["Am7", "D9"],
                           "passes": ["all_muted", "replace_P_with_triads", "lower_g_level"]}))
    for i, r in enumerate(parsed["stab_duration"], 1):
        mask = r["Exercise"]
        cell_slots = slots("B", "duration", i, 4, mask, (4, 8))
        grid_slots.extend(cell_slots)
        tasks.append(task("B", i, "chord_stab_release", 4,
                          {"duration_label": r["Duration"], "mask": mask,
                           "release_cue": r["Release cue"], "contexts": ["Am7", "D9",
                           "G13", "Cmaj9", "F#m7", "E9"],
                           "release_time_seconds": None}))
    for i, r in enumerate(parsed["syncopated_chords"], 1):
        if int(r["Cell"]) != i:
            raise CandidateError(f"C_CELL_NUMBER {i}")
        contact_text = r["Contact points"]
        if i <= 7:
            marks = re.findall(r"(?<!\w)(?:[&a]?[1-4])(?!\w)", contact_text)
            if len(marks) < 3:
                raise CandidateError(f"C_CONTACT_MARKS {i}")
        else:
            marks = []
        tasks.append(task("C", i, "syncopated_triad_or_shell", 5,
            {"harmony": r["Harmony"], "contact_instruction": contact_text,
             "explicit_contact_marks": marks, "triad_pitch_classes": None,
             "full_chord_grip_optional": True}))
        for j, mark in enumerate(marks, 1):
            contact_events.append({"local_key": f"l86-c-{i:02d}-contact-{j:02d}",
                "source": {"pdf_page": 5, "row": i}, "module": "C",
                "contact_mark": mark, "chord": r["Harmony"], "pitch": None,
                "voicing": None, "canonical_event_id": None})
    for i, r in enumerate(parsed["bass_space"], 1):
        tasks.append(task("D", i, "bass_space_rule", 6,
            {"bass_event": r["Bass event"], "guitar_rule": r["Guitar rule"],
             "bass_recording": None, "guitar_voicing": None}))
    for i, r in enumerate(parsed["funk_pockets"], 1):
        if r["Name"] != f"Pocket {i}":
            raise CandidateError(f"E_POCKET_NUMBER {i}")
        mask = r["Pattern"]
        grid_slots.extend(slots("E", "funk_pocket", i, 7, mask, (16,)))
        tasks.append(task("E", i, "one_chord_funk_pocket", 7,
            {"chord": r["Chord"], "pattern": mask, "purpose": r["Purpose"],
             "same_master_tempo": True, "voicing": None}))
    for i, r in enumerate(parsed["rnb_pockets"], 1):
        chords = r["Harmony"].split("-")
        if not 2 <= len(chords) <= 4:
            raise CandidateError(f"F_HARMONY_WIDTH {i}")
        tasks.append(task("F", i, "rnb_pocket_variation", 8,
            {"study": r["Study"], "harmony": chords,
             "primary_behavior": r["Primary behavior"], "exact_onsets": None,
             "voicings": None}))
    for i, r in enumerate(parsed["register_rotation"], 1):
        if int(r["Pass"]) != i:
            raise CandidateError(f"G_PASS_NUMBER {i}")
        tasks.append(task("G", i, "register_texture_rotation", 9,
            {"register_voicing": r["Voicing / register"],
             "instruction": r["Instruction"],
             "four_bar_harmony": ["Am7", "D9", "G13", "Cmaj9"],
             "contact_grid_source": None}))

    h_studies = []
    for i, page in enumerate(range(10, 14), 1):
        page_lines = pages[page - 1].splitlines()
        headings = [line for line in page_lines if line.startswith(f"Module H - Study {i} - ")]
        chord_lines = [line for line in page_lines if line.startswith("| ") and line.endswith(" |")]
        if len(headings) != 1 or len(chord_lines) != 1:
            raise CandidateError(f"H_STUDY_BOUNDARY {i}")
        chords = [c.strip() for c in chord_lines[0].strip("|").split("|")]
        if len(chords) != 8:
            raise CandidateError(f"H_EIGHT_BARS {i}")
        pass_rows = table(pages[page - 1], ["Pass", "Requirement"], 6, f"H{i}")
        if [int(r["Pass"]) for r in pass_rows] != list(range(1, 7)):
            raise CandidateError(f"H_PASS_SEQUENCE {i}")
        h_studies.append({"study": i, "title": headings[0], "page": page,
                          "chords": chords, "passes": pass_rows})
        tasks.append(task("H", i, "eight_bar_groove_study", page,
            {"title": headings[0], "chords": chords,
             "study_direction": page_lines[page_lines.index(chord_lines[0]) + 1],
             "passes": pass_rows, "exact_contact_grid": None}))
        for bar, chord in enumerate(chords, 1):
            contact_events.append({"local_key": f"l86-h-{i:02d}-bar-{bar:02d}",
                "module": "H", "source": {"pdf_page": page, "bar": bar},
                "chord": chord, "pitch": None, "voicing": None,
                "onset_q": None, "duration_q": None, "canonical_event_id": None})
        for pass_no, row in enumerate(pass_rows, 1):
            tasks.append(task("H", (i - 1) * 6 + pass_no,
                "groove_study_pass", page,
                {"study": i, "pass": pass_no, "requirement": row["Requirement"]}))

    capstone = []
    for i, r in enumerate(parsed["capstone_sections"], 1):
        start, end = map(int, r["Bars"].split("-"))
        chords = r["Harmony"].split("-")
        if (start, end) != (4 * i - 3, 4 * i) or len(chords) != 4:
            raise CandidateError(f"I_SECTION_BOUNDARY {i}")
        tasks.append(task("I", i, "capstone_section", 14,
            {"first_bar": start, "last_bar": end, "chords": chords,
             "feel": r["Feel"], "voicing": r["Voicing"],
             "dynamic": r["Dynamic"], "same_master_tempo": True}))
        for offset, chord in enumerate(chords):
            bar = start + offset
            capstone.append({"bar": bar, "chord": chord, "section": i})
            contact_events.append({"local_key": f"l86-i-bar-{bar:02d}",
                "module": "I", "source": {"pdf_page": 14, "section": i,
                "bar": bar}, "chord": chord, "pitch": None, "voicing": r["Voicing"],
                "onset_q": None, "duration_q": None, "canonical_event_id": None})
    if [b["bar"] for b in capstone] != list(range(1, 33)):
        raise CandidateError("I_BAR_UNION")
    for i, r in enumerate(parsed["recovery"], 1):
        tasks.append(task("J", i, "pocket_recovery", 15,
            {"failure": r["Failure"], "repair": r["Immediate repair"],
             "recovery_trial": None}))

    methods = [("A", 2, "Practice order: clap accents -> muted strings -> one triad -> full groove."),
               ("D", 6, "Record or loop each bass figure."),
               ("E", 7, "Run all eight cells at one tempo."),
               ("F", 8, "The chord stab remains the structural event."),
               ("G", 9, "The groove must survive the register change."),
               ("I", 14, "The tempo never changes between"),
               ("J", 15, "Mastery: 14/16 or better on two separate days")]
    for i, (module, page, excerpt) in enumerate(methods, 1):
        if excerpt not in pages[page - 1]:
            raise CandidateError(f"PDF_METHOD_MISSING {module}:{page}")
        tasks.append(task(module, 90 + i, "instructional_method", page,
                          {"source_excerpt": excerpt, "full_instruction_page": page}))
    if "14/16 or better on two separate days." not in lines or \
            "No zero in pulse, ghost hierarchy, bass-space discipline, or recovery." not in lines:
        raise CandidateError("TXT_MASTERY_GATE")
    return {"schema": "fathom.detached_curriculum_source_candidate.v1",
            "level": 86, "section": "XII", "wbs_owner": "2.3.1.3.1",
            "status": "candidate_only", "source_map": inventory,
            "source_pins": {"txt": {"path": str(TXT), "bytes": PINS["txt"][0],
                            "sha256": PINS["txt"][1]},
                            "pdf": {"path": str(PDF), "bytes": PINS["pdf"][0],
                            "sha256": PINS["pdf"][1]}},
            "source_archive": {"txt_lines": [{"line": i, "text": x}
                                             for i, x in enumerate(lines, 1)],
                               "pdf_pages": [{"page": i, "text": x}
                                             for i, x in enumerate(pages, 1)]},
            "pdf_tables": {name: {"page": TABLES[name][0], "rows": rows}
                           for name, rows in parsed.items()},
            "module_workload_declared": COUNTS, "declared_workload_total": 1504,
            "tasks": tasks, "grid_slots": grid_slots,
            "contact_or_bar_events": contact_events,
            "capstone_bar_plan": capstone, "h_studies": h_studies,
            "source_tensions": [
                {"issue": "TXT supplies module summary only; PDF pages 2-15 supply expanded cells, studies, and capstone",
                 "resolution": "PDF detail converted with page provenance"},
                {"issue": "1504 declared events are not individually specified as 1504 contact slots or notes",
                 "resolution": "retain declared counts separately from parsed grids and bar targets"},
                {"issue": "PDF Module H study charts and Module I capstone give harmony/feel, not per-bar contact masks or pitched voicings",
                 "exact_grid_or_pitch": None}],
            "unresolved_performance_fields": ["pitch", "voicing", "string", "fret",
                "tempo", "onset_q", "duration_q", "performed_result", "score",
                "canonical_task_id", "canonical_event_id"],
            "admission_claim": False}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path,
                        default=ROOT / OUT / "level086_whole_candidate.json")
    args = parser.parse_args()
    candidate = build()
    output = args.output.resolve()
    if not output.is_relative_to((ROOT / OUT).resolve()):
        raise CandidateError("OUTPUT_OUTSIDE_P07_LEVEL86_BUILD")
    output.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(candidate, indent=2, ensure_ascii=False).encode() + b"\n"
    output.write_bytes(data)
    print(json.dumps({"output": str(output), "bytes": len(data),
                      "sha256": sha(data), "tasks": len(candidate["tasks"]),
                      "grid_slots": len(candidate["grid_slots"]),
                      "contact_or_bar_events": len(candidate["contact_or_bar_events"]),
                      "declared_workload": candidate["declared_workload_total"]}))


if __name__ == "__main__":
    main()
