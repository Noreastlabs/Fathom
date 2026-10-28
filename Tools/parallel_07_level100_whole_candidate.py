#!/usr/bin/env python3
"""Build a pinned detached whole-source Level 100 composition candidate."""

from __future__ import annotations

import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path
import re

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
STEM = "Guitar_Exercises_Section_XV_Level_100_Motif_Generation_Harmonic_Constraints_Bass_First_Melody_First_Writing_and_Eight_Bar_Composition"
TXT = Path("Notes/music/guitar project/TXT version") / (STEM + ".txt")
PDF = Path("Notes/music/guitar project/PDF version") / (STEM + ".pdf")
MAP = Path("Results/parallel-01/exercises/inventory/20260922T180500Z-2.3-curriculum-v1-source-inventory-evidence/curriculum-source-map.json")
OUT = Path("Build/parallel-07/2.3.1.3.1-level100-whole-r01")
PINS = {"txt": (1474, "d9d156ed64317d7567dcb57bbdaa630afb3861da43a70a77f25fbf8613b867d5"),
        "pdf": (47322, "4d4efa497b1fe782a89cbb22e935ea5cdf9d3ec6b7c94c609b5a36b631fb6a31")}
COUNTS = {"A": 144, "B": 144, "C": 128, "D": 128, "E": 128,
          "F": 112, "G": 160, "H": 192, "I": 320, "J": 64}
TABLES = {
    "workload": (1, ["Module", "Exercise", "Events"], 10),
    "composition_hierarchy": (2, ["Layer", "Question"], 8),
    "motif_seeds": (3, ["Seed", "Degrees", "Rhythm"], 8),
    "rhythm_motifs": (4, ["Cell", "Contacts"], 8),
    "transformations": (5, ["Transformation", "Keep", "Change"], 8),
    "development_ladder": (6, ["Bars", "Instruction"], 5),
    "harmony_constraints": (7, ["Constraint", "Eight-bar assignment"], 8),
    "direction_audit": (8, ["Question", "Pass condition"], 6),
    "melody_first_passes": (9, ["Pass", "Task"], 7),
    "harmonizations": (10, ["Version", "Constraint"], 6),
    "bass_designs": (11, ["Bass design", "Assignment"], 8),
    "bass_harmony_passes": (12, ["Pass", "Bass", "Harmony"], 6),
    "groove_engines": (13, ["Groove engine", "Constraint"], 8),
    "rhythmic_identities": (14, ["Version", "Rhythmic identity"], 6),
    "constraint_cards": (15, ["Card", "Required constraints"], 8),
    "portfolio_pieces": (20, ["Bars", "Piece", "Starting method", "Requirement"], 4),
    "revision_audit": (21, ["Question", "Action"], 8),
}
PC = {"C": 0, "C#": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4,
      "F": 5, "F#": 6, "G": 7, "G#": 8, "A": 9, "Bb": 10, "B": 11}


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
    row = next((r for r in json.loads((root / MAP).read_text())["rows"] if r["level"] == 100), None)
    expected = {"section": "XV", "wbs_owner": "2.3.1.3.1", "txt_path": str(TXT),
                "pdf_path": str(PDF), "txt_bytes": PINS["txt"][0],
                "pdf_bytes": PINS["pdf"][0], "txt_sha256": PINS["txt"][1],
                "pdf_sha256": PINS["pdf"][1], "pair_status": "exact_stem_pair",
                "conversion_status": "not_converted", "stable_ids_assigned": False,
                "runtime_eligible": False, "imported": False, "admitted": False}
    if row is None or any(row.get(k) != v for k, v in expected.items()):
        raise CandidateError("SOURCE_MAP_IDENTITY_OR_STATUS_DRIFT")
    return row


def table(page: str, headers: list[str], count: int, name: str) -> list[dict]:
    lines = page.splitlines()
    matches = [i for i in range(len(lines)) if lines[i:i + len(headers)] == headers]
    if len(matches) != 1:
        raise CandidateError(f"PDF_TABLE_HEADER {name}")
    width = len(headers)
    cells = lines[matches[0] + width:matches[0] + width + count * width]
    if len(cells) != count * width:
        raise CandidateError(f"PDF_TABLE_LENGTH {name}")
    return [dict(zip(headers, cells[i * width:(i + 1) * width], strict=True))
            for i in range(count)]


def task(module: str, kind: str, ordinal: int, page: int, fields: dict,
         txt_line: int | None = None) -> dict:
    return {"local_key": f"l100-{module.lower()}-{kind}-{ordinal:02d}",
            "module": module, "kind": kind,
            "source": {"pdf_page": page, "txt_line": txt_line},
            "fields": fields, "canonical_task_id": None,
            "authored_response": None, "observed_score": None}


def event(module: str, kind: str, row: int, slot: int, page: int,
          *, degree: str | None = None, pitch: str | None = None,
          contact: str | None = None, bar: int | None = None,
          fields: dict | None = None) -> dict:
    return {"local_key": f"l100-{module.lower()}-{kind}-{row:02d}-{slot:02d}",
            "module": module, "kind": kind,
            "source": {"pdf_page": page, "row": row},
            "slot": slot, "bar": bar, "degree": degree, "pitch": pitch,
            "pitch_class": PC[pitch] if pitch in PC else None,
            "contact_mark": contact, "fields": fields or {},
            "octave": None, "string": None, "fret": None,
            "onset_q": None, "duration_q": None,
            "canonical_event_id": None, "performed_result": None}


def build(root: Path = ROOT) -> dict:
    txt = read(root, TXT, PINS["txt"])
    pdf = read(root, PDF, PINS["pdf"])
    inventory = source_map(root)
    lines = txt.decode().splitlines()
    pages = [p.extract_text() or "" for p in PdfReader(BytesIO(pdf)).pages]
    if len(lines) != 48 or len(pages) != 21 or not pages[0].startswith(
            "Guitar Exercises - Section XV, Level 100"):
        raise CandidateError("SOURCE_LINE_PAGE_BOUNDARY")
    parsed = {name: table(pages[page - 1], heads, n, name)
              for name, (page, heads, n) in TABLES.items()}
    for i, row in enumerate(parsed["workload"]):
        module = chr(ord("A") + i)
        literal = f"{module}. {row['Exercise']} - {row['Events']} events"
        if row["Module"] != module or int(row["Events"]) != COUNTS[module] or literal not in lines:
            raise CandidateError(f"TXT_PDF_WORKLOAD_PARITY {module}")
    if sum(COUNTS.values()) != 1520 or "TOTAL\n1520" not in pages[0] or \
            "COMPLETE WRITTEN WORKLOAD: 1520 events" not in lines:
        raise CandidateError("WORKLOAD_TOTAL_INVALID")
    tasks = []
    events = []

    for i, row in enumerate(parsed["composition_hierarchy"], 1):
        tasks.append(task("A", "composition_decision_layer", i, 2, row))
    for i, row in enumerate(parsed["motif_seeds"], 1):
        degrees = row["Degrees"].split("-")
        if int(row["Seed"]) != i or not 3 <= len(degrees) <= 4 or any(
                not re.fullmatch(r"[b#]?[1-7]", d) for d in degrees):
            raise CandidateError(f"MOTIF_SEED_DEGREES {i}")
        tasks.append(task("A", "interval_rhythm_motif_seed", i, 3,
            {"degrees": degrees, "rhythm_label": row["Rhythm"],
             "key_chosen_after_singing": True, "register_count": 2,
             "key": None, "note_pitches": None, "exact_onsets": None}))
        events.extend(event("A", "seed_degree", i, j, 3, degree=d)
                      for j, d in enumerate(degrees, 1))
    for i, row in enumerate(parsed["rhythm_motifs"], 1):
        label, cue = row["Cell"], row["Contacts"]
        if label != chr(ord("A") + i - 1):
            raise CandidateError(f"RHYTHM_CELL_LABEL {i}")
        marks = re.findall(r"(?<!\w)(?:[&a]?[1-4])(?!\w)", cue) if i <= 4 else []
        if i <= 4 and len(marks) < 3:
            raise CandidateError(f"RHYTHM_CELL_CONTACTS {i}")
        tasks.append(task("A", "rhythm_only_motif", i, 4,
            {"cell": label, "printed_contact_cue": cue,
             "explicit_contact_marks": marks, "apply_to_contours": 3,
             "pitch_contours": None, "meter": None}))
        events.extend(event("A", "rhythm_contact", i, j, 4, contact=mark)
                      for j, mark in enumerate(marks, 1))

    for i, row in enumerate(parsed["transformations"], 1):
        tasks.append(task("B", "motif_transformation", i, 5,
            {"transformation": row["Transformation"], "keep": row["Keep"],
             "change": row["Change"], "source_motif": None,
             "authored_variant": None, "audible_identity_result": None}))
    expected_ladder = [(1, 2), (3, 4), (5, 6), (7, 7), (8, 8)]
    for i, (row, (first, last)) in enumerate(zip(parsed["development_ladder"], expected_ladder, strict=True), 1):
        span = str(first) if first == last else f"{first}-{last}"
        if row["Bars"] != span:
            raise CandidateError(f"DEVELOPMENT_LADDER_SPAN {i}")
        tasks.append(task("B", "eight_bar_development_step", i, 6,
            {"first_bar": first, "last_bar": last,
             "instruction": row["Instruction"],
             "four_variants_requested": True, "authored_notes": None}))

    for i, row in enumerate(parsed["harmony_constraints"], 1):
        tasks.append(task("C", "harmony_first_constraint", i, 7,
            {"constraint": row["Constraint"],
             "eight_bar_assignment": row["Eight-bar assignment"],
             "authored_progression": None, "authored_voicings": None,
             "authored_melody": None}))
    for i, row in enumerate(parsed["direction_audit"], 1):
        tasks.append(task("C", "harmonic_direction_audit", i, 8,
            {"question": row["Question"], "pass_condition": row["Pass condition"],
             "observed_answer": None}))

    for i, row in enumerate(parsed["melody_first_passes"], 1):
        if int(row["Pass"]) != i:
            raise CandidateError(f"MELODY_FIRST_PASS {i}")
        tasks.append(task("D", "melody_first_writing_pass", i, 9,
            {"pass": i, "instruction": row["Task"],
             "authored_melody": None, "harmonization": None}))
    for i, row in enumerate(parsed["harmonizations"], 1):
        if int(row["Version"]) != i:
            raise CandidateError(f"HARMONIZATION_VERSION {i}")
        tasks.append(task("D", "same_melody_harmonization", i, 10,
            {"version": i, "constraint": row["Constraint"],
             "shared_melody": None, "authored_chords": None,
             "ranking": None}))

    for i, row in enumerate(parsed["bass_designs"], 1):
        assignment = row["Assignment"]
        route = re.search(r"(?:above )?([A-G](?:#|b)?(?:-[A-G](?:#|b)?){7})", assignment)
        pitches = route.group(1).split("-") if route else []
        if i <= 2 and len(pitches) != 8:
            raise CandidateError(f"BASS_ROUTE_MISSING {i}")
        if any(n not in PC for n in pitches):
            raise CandidateError(f"BASS_ROUTE_PITCH {i}")
        tasks.append(task("E", "bass_first_design", i, 11,
            {"design": row["Bass design"], "assignment": assignment,
             "printed_bass_route": pitches or None,
             "authored_harmony": None, "authored_top_line": None}))
        events.extend(event("E", "printed_bass_route", i, j, 11, pitch=n)
                      for j, n in enumerate(pitches, 1))
    for i, row in enumerate(parsed["bass_harmony_passes"], 1):
        if int(row["Pass"]) != i:
            raise CandidateError(f"BASS_HARMONY_PASS {i}")
        tasks.append(task("E", "bass_harmony_independence", i, 12,
            {"bass_rule": row["Bass"], "harmony_rule": row["Harmony"],
             "authored_bass": None, "authored_harmony": None}))

    for i, row in enumerate(parsed["groove_engines"], 1):
        tasks.append(task("F", "rhythm_first_groove_engine", i, 13,
            {"engine": row["Groove engine"], "constraint": row["Constraint"],
             "authored_rhythm_mask": None, "authored_harmony": None}))
    if "Use | Am7 | Fmaj7 | Cmaj7 | G7 | x2." not in pages[13]:
        raise CandidateError("RHYTHMIC_IDENTITY_HARMONY")
    for i, row in enumerate(parsed["rhythmic_identities"], 1):
        if int(row["Version"]) != i:
            raise CandidateError(f"RHYTHMIC_IDENTITY_VERSION {i}")
        tasks.append(task("F", "fixed_harmony_rhythmic_identity", i, 14,
            {"version": i, "rhythmic_identity": row["Rhythmic identity"],
             "four_chord_loop_twice": ["Am7", "Fmaj7", "Cmaj7", "G7"] * 2,
             "authored_contact_grid": None}))
    for i, row in enumerate(parsed["constraint_cards"], 1):
        if int(row["Card"]) != i:
            raise CandidateError(f"CONSTRAINT_CARD_NUMBER {i}")
        tasks.append(task("G", "eight_bar_constraint_card", i, 15,
            {"card": i, "required_constraints": row["Required constraints"],
             "generate_full_draft_before_revision": True,
             "authored_eight_bars": None}))

    studies = []
    for i, page in enumerate(range(16, 20), 1):
        page_lines = pages[page - 1].splitlines()
        headings = [line for line in page_lines if line.startswith(f"Module H - Study {i} - ")]
        if len(headings) != 1:
            raise CandidateError(f"H_STUDY_HEADING {i}")
        direction = page_lines[page_lines.index(headings[0]) + 1]
        pass_rows = table(pages[page - 1], ["Pass", "Requirement"], 6, f"H{i}")
        if [int(row["Pass"]) for row in pass_rows] != list(range(1, 7)):
            raise CandidateError(f"H_PASS_SEQUENCE {i}")
        studies.append({"study": i, "page": page, "title": headings[0],
                        "direction": direction, "passes": pass_rows})
        tasks.append(task("H", "complete_original_study", i, page,
            {"title": headings[0], "direction": direction,
             "bars": 8, "passes": pass_rows,
             "authored_composition": None, "recorded_take": None}))
        for j, row in enumerate(pass_rows, 1):
            tasks.append(task("H", "study_pass", (i - 1) * 6 + j, page,
                {"study": i, "pass": j, "requirement": row["Requirement"],
                 "authored_result": None}))

    portfolio = []
    methods = ["motif-first", "melody-first", "bass-first", "rhythm-first"]
    for i, row in enumerate(parsed["portfolio_pieces"], 1):
        first, last = map(int, row["Bars"].split("-"))
        if (first, last) != (8 * i - 7, 8 * i) or row["Piece"] != f"Piece {chr(64 + i)}" or \
                row["Starting method"] != methods[i - 1]:
            raise CandidateError(f"PORTFOLIO_PIECE_SPAN {i}")
        tasks.append(task("I", "composition_portfolio_piece", i, 20,
            {"piece": row["Piece"], "first_bar": first, "last_bar": last,
             "starting_method": row["Starting method"],
             "requirement": row["Requirement"], "linked_study": i,
             "title": None, "identity_statement": None, "lead_sheet": None,
             "performance_arrangement": None, "recorded_take": None}))
        for bar in range(first, last + 1):
            portfolio.append({"bar": bar, "piece": row["Piece"],
                              "starting_method": row["Starting method"],
                              "authored_chord": None, "authored_melody": None,
                              "authored_bass": None, "authored_rhythm": None,
                              "source": {"pdf_page": 20, "section_row": i}})
    if [x["bar"] for x in portfolio] != list(range(1, 33)):
        raise CandidateError("PORTFOLIO_THIRTY_TWO_BAR_UNION")
    for i, row in enumerate(parsed["revision_audit"], 1):
        tasks.append(task("J", "revision_authorship_question", i, 21,
            {"question": row["Question"], "action": row["Action"],
             "authored_revision": None, "observed_result": None}))
    if "14/16 or better." not in lines or \
            "No zero in identity, development, form, or performance." not in lines or \
            "Pass Level 100: 14/16 or better" not in pages[20]:
        raise CandidateError("MASTERY_GATE_PARITY")

    directions = [
        ("A", 3, "Choose a key only after the contour and rhythm can be sung."),
        ("A", 4, "Apply the same rhythm to three different pitch contours."),
        ("B", 5, "After each transformation, play original then variant."),
        ("C", 7, "Write the functional progression first, then voicings, then melody."),
        ("D", 9, "Do not change the melody merely because the first chord grip is inconvenient."),
        ("E", 11, "Sing a possible top line while playing bass before adding chords."),
        ("F", 13, "Write rhythm first on muted strings."),
        ("G", 15, "Do not revise while generating the first draft;"),
        ("I", 20, "Create four independent eight-bar originals."),
    ]
    for i, (module, page, excerpt) in enumerate(directions, 1):
        if excerpt not in pages[page - 1]:
            raise CandidateError(f"PDF_DIRECTION_MISSING {module}:{page}")
        tasks.append(task(module, "instructional_method", i, page,
                          {"source_excerpt": excerpt, "full_instruction_page": page}))
    return {"schema": "fathom.detached_curriculum_source_candidate.v1",
            "level": 100, "section": "XV", "wbs_owner": "2.3.1.3.1",
            "status": "candidate_only", "source_map": inventory,
            "source_pins": {"txt": {"path": str(TXT), "bytes": PINS["txt"][0],
                            "sha256": PINS["txt"][1]},
                            "pdf": {"path": str(PDF), "bytes": PINS["pdf"][0],
                            "sha256": PINS["pdf"][1]}},
            "source_archive": {"txt_lines": [{"line": i, "text": line}
                                             for i, line in enumerate(lines, 1)],
                               "pdf_pages": [{"page": i, "text": page}
                                             for i, page in enumerate(pages, 1)]},
            "pdf_tables": {name: {"page": TABLES[name][0], "rows": rows}
                           for name, rows in parsed.items()},
            "module_workload_declared": COUNTS, "declared_workload_total": 1520,
            "tasks": tasks, "source_supported_seed_or_contact_events": events,
            "h_studies": studies, "portfolio_bar_allocations": portfolio,
            "source_tensions": [
                {"pdf_page": 10, "issue": "heading says four harmonizations; table prints six versions",
                 "resolution": "convert all six printed versions"},
                {"pdf_page": 14, "issue": "heading says four rhythmic identities; table prints six versions",
                 "resolution": "convert all six printed versions"},
                {"issue": "TXT is a module summary; PDF pages 2-21 contain detailed composition assignments",
                 "resolution": "PDF detail converted with page provenance"},
                {"issue": "1520 workload events are not 1520 pre-authored pitches or contacts; learner composes the material",
                 "resolution": "retain declared workload apart from source-supported seeds and blank portfolio allocations"}],
            "unresolved_performance_fields": ["key", "authored_pitch", "authored_chord",
                "authored_bass", "authored_rhythm", "meter", "onset_q", "duration_q",
                "string", "fret", "lead_sheet", "recorded_take", "score",
                "canonical_task_id", "canonical_event_id"],
            "admission_claim": False}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path,
                        default=ROOT / OUT / "level100_whole_candidate.json")
    args = parser.parse_args()
    candidate = build()
    output = args.output.resolve()
    if not output.is_relative_to((ROOT / OUT).resolve()):
        raise CandidateError("OUTPUT_OUTSIDE_P07_LEVEL100_BUILD")
    output.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(candidate, indent=2, ensure_ascii=False).encode() + b"\n"
    output.write_bytes(data)
    print(json.dumps({"output": str(output), "bytes": len(data), "sha256": sha(data),
                      "tasks": len(candidate["tasks"]),
                      "seed_or_contact_events": len(candidate["source_supported_seed_or_contact_events"]),
                      "portfolio_bars": len(candidate["portfolio_bar_allocations"]),
                      "declared_workload": candidate["declared_workload_total"]}))


if __name__ == "__main__":
    main()
