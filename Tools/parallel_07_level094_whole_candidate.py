#!/usr/bin/env python3
"""Build detached whole-source Level 94 expressive-performance candidate."""

from __future__ import annotations

import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path
import re

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
STEM = "Guitar_Exercises_Section_XIII_Level_94_Expressive_Performance_Synthesis_Emotional_Contour_Dynamic_Tonal_Orchestration_Restraint_and_Complete_Solo_Capstone"
TXT = Path("Notes/music/guitar project/TXT version") / (STEM + ".txt")
PDF = Path("Notes/music/guitar project/PDF version") / (STEM + ".pdf")
MAP = Path("Results/parallel-01/exercises/inventory/20260922T180500Z-2.3-curriculum-v1-source-inventory-evidence/curriculum-source-map.json")
OUT = Path("Build/parallel-07/2.3.1.3.1-level094-whole-r01")
PINS = {"txt": (1506, "c145149fba43a2f8836ae64a7569f369aa6dcc88b0e7beefce02e0d4aeddab48"),
        "pdf": (26806, "1743888569b5ea38659d7310af764df0bca4c969ed9a1e633ac106d2fc67965f")}
COUNTS = {"A": 128, "B": 128, "C": 128, "D": 112, "E": 112,
          "F": 128, "G": 192, "H": 160, "I": 320, "J": 64}
TABLES = {
    "workload": (1, ["Module", "Exercise", "Events"], 10),
    "decision_hierarchy": (2, ["Priority", "Question"], 7),
    "emotional_arcs": (3, ["Arc", "Bars 1-2", "Bars 3-4", "Bars 5-6", "Bars 7-8"], 6),
    "target_silence": (4, ["Cell", "Target behavior", "Silence"], 8),
    "articulation_harmony": (5, ["Harmony", "Primary target", "First articulation to test", "Articulation to avoid first"], 6),
    "same_target": (6, ["Pass", "Expression"], 8),
    "dynamic_tone": (7, ["Layer", "Soft version", "Strong version"], 7),
    "tone_without_volume": (8, ["Pass", "Tone variable", "Keep constant"], 6),
    "restraint": (9, ["Constraint", "Exercise"], 8),
    "register_texture": (10, ["Arc", "Register map", "Texture map"], 6),
    "climax_stages": (11, ["Stage", "Bars", "Allowed intensity"], 6),
    "climax_release": (12, ["Climax device", "Required release"], 6),
    "fixed_targets": (17, ["Bar", "Chord", "Required target", "Freedom"], 8),
    "restraint_randomizer": (18, ["Command", "Constraint"], 8),
    "capstone": (19, ["Bars", "Harmony", "Arc role", "Expression", "Dynamic"], 10),
    "completion_rubric": (20, ["Category", "0", "1", "2"], 8),
}
PC = {"C": 0, "C#": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4,
      "F": 5, "F#": 6, "G": 7, "G#": 8, "A": 9, "Bb": 10, "B": 11}
CHORD_TONES = {"Dm7": {2, 5, 9, 0}, "G7": {7, 11, 2, 5},
               "Cmaj7": {0, 4, 7, 11}, "Bm7b5": {11, 2, 5, 9},
               "E7": {4, 8, 11, 2}, "Am7": {9, 0, 4, 7},
               "A7": {9, 1, 4, 7}}


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
    row = next((r for r in json.loads((root / MAP).read_text())["rows"] if r["level"] == 94), None)
    expected = {"section": "XIII", "wbs_owner": "2.3.1.3.1", "txt_path": str(TXT),
                "pdf_path": str(PDF), "txt_bytes": PINS["txt"][0],
                "pdf_bytes": PINS["pdf"][0], "txt_sha256": PINS["txt"][1],
                "pdf_sha256": PINS["pdf"][1], "pair_status": "exact_stem_pair",
                "conversion_status": "not_converted", "stable_ids_assigned": False,
                "runtime_eligible": False, "imported": False, "admitted": False}
    if row is None or any(row.get(k) != v for k, v in expected.items()):
        raise CandidateError("SOURCE_MAP_IDENTITY_OR_STATUS_DRIFT")
    return row


def table(page: str, heads: list[str], count: int, name: str) -> list[dict]:
    lines = page.splitlines()
    positions = [i for i in range(len(lines)) if lines[i:i + len(heads)] == heads]
    if len(positions) != 1:
        raise CandidateError(f"PDF_TABLE_HEADER {name}")
    width = len(heads)
    cells = lines[positions[0] + width:positions[0] + width + width * count]
    if len(cells) != width * count:
        raise CandidateError(f"PDF_TABLE_LENGTH {name}")
    return [dict(zip(heads, cells[i * width:(i + 1) * width], strict=True))
            for i in range(count)]


def task(module: str, kind: str, ordinal: int, page: int, fields: dict,
         txt_line: int | None = None) -> dict:
    return {"local_key": f"l94-{module.lower()}-{kind}-{ordinal:02d}",
            "module": module, "kind": kind,
            "source": {"pdf_page": page, "txt_line": txt_line},
            "fields": fields, "canonical_task_id": None,
            "performed_result": None, "observed_score": None}


def marker(module: str, kind: str, ordinal: int, page: int, bar: int,
           chord: str | None, target: str | None, fields: dict | None = None) -> dict:
    return {"local_key": f"l94-{module.lower()}-{kind}-{ordinal:02d}-bar-{bar:02d}",
            "module": module, "kind": kind, "source": {"pdf_page": page},
            "bar": bar, "chord": chord, "target": target,
            "target_pitch_class": PC[target] if target in PC else None,
            "fields": fields or {}, "octave": None, "string": None, "fret": None,
            "onset_q": None, "duration_q": None, "canonical_event_id": None,
            "performed_result": None}


def build(root: Path = ROOT) -> dict:
    txt = read(root, TXT, PINS["txt"])
    pdf = read(root, PDF, PINS["pdf"])
    inventory = source_map(root)
    lines = txt.decode().splitlines()
    pages = [p.extract_text() or "" for p in PdfReader(BytesIO(pdf)).pages]
    if len(lines) != 44 or len(pages) != 20 or not pages[0].startswith(
            "Guitar Exercises - Section XIII, Level 94"):
        raise CandidateError("SOURCE_LINE_PAGE_BOUNDARY")
    parsed = {name: table(pages[page - 1], heads, n, name)
              for name, (page, heads, n) in TABLES.items()}
    for i, row in enumerate(parsed["workload"]):
        module = chr(ord("A") + i)
        literal = f"{module}. {row['Exercise']} - {row['Events']} events"
        if row["Module"] != module or int(row["Events"]) != COUNTS[module] or literal not in lines:
            raise CandidateError(f"TXT_PDF_WORKLOAD_PARITY {module}")
    if sum(COUNTS.values()) != 1472 or "TOTAL\n1472" not in pages[0] or \
            "COMPLETE WRITTEN WORKLOAD: 1472 events" not in lines:
        raise CandidateError("TOTAL_WORKLOAD_INVALID")
    tasks = []
    markers = []

    for i, row in enumerate(parsed["decision_hierarchy"], 1):
        if not row["Priority"].startswith(f"{i}. "):
            raise CandidateError(f"DECISION_HIERARCHY_ORDER {i}")
        tasks.append(task("A", "decision_priority", i, 2, row))
    arc_windows = [(1, 2), (3, 4), (5, 6), (7, 8)]
    for i, row in enumerate(parsed["emotional_arcs"], 1):
        cells = [row[k] for k in ("Bars 1-2", "Bars 3-4", "Bars 5-6", "Bars 7-8")]
        tasks.append(task("A", "plain_target_emotional_arc", i, 3,
            {"arc": row["Arc"], "bar_windows": [{"first_bar": a, "last_bar": b,
             "expression": cell} for (a, b), cell in zip(arc_windows, cells, strict=True)],
             "progression": None, "no_initial_ornaments": True,
             "numeric_dynamics_or_pitch": None}, 14))
        for j, ((first, last), cell) in enumerate(zip(arc_windows, cells, strict=True), 1):
            markers.append(marker("A", "arc_window", i, 3, first, None, None,
                {"window_index": j, "last_bar": last, "expression": cell,
                 "progression": None}))
    for i, row in enumerate(parsed["target_silence"], 1):
        if int(row["Cell"]) != i:
            raise CandidateError(f"TARGET_SILENCE_CELL {i}")
        tasks.append(task("A", "target_sustain_silence", i, 4,
            {"behavior": row["Target behavior"], "silence": row["Silence"],
             "target_pitch": None, "actual_silence_duration": None}))

    for i, row in enumerate(parsed["articulation_harmony"], 1):
        chord = row["Harmony"]
        options = row["Primary target"].split(" or ")
        if chord not in CHORD_TONES or len(options) != 2 or any(
                PC[n] not in CHORD_TONES[chord] for n in options):
            raise CandidateError(f"ARTICULATION_HARMONY_TARGET {i}")
        tasks.append(task("B", "harmony_articulation_test", i, 5,
            {"chord": chord, "primary_target_options": options,
             "first_to_test": row["First articulation to test"],
             "avoid_first": row["Articulation to avoid first"],
             "preferred_result": None}))
    same_target_contexts = [("Cmaj7", "E"), ("G7", "B"),
                            ("Am7", "C"), ("E7", "G#")]
    for i, row in enumerate(parsed["same_target"], 1):
        if int(row["Pass"]) != i:
            raise CandidateError(f"SAME_TARGET_PASS {i}")
        tasks.append(task("B", "same_target_expression", i, 6,
            {"expression": row["Expression"],
             "contexts": [{"chord": c, "target": n} for c, n in same_target_contexts],
             "ranking": None}))

    for i, row in enumerate(parsed["dynamic_tone"], 1):
        tasks.append(task("C", "dynamic_tone_layer", i, 7,
            {"layer": row["Layer"], "soft": row["Soft version"],
             "strong": row["Strong version"],
             "four_bar_crescendo": True, "numeric_loudness": None}))
    for i, row in enumerate(parsed["tone_without_volume"], 1):
        if int(row["Pass"]) != i:
            raise CandidateError(f"TONE_PASS_NUMBER {i}")
        tasks.append(task("C", "tone_change_constant_volume", i, 8,
            {"tone_variable": row["Tone variable"],
             "keep_constant": row["Keep constant"],
             "measured_loudness": None}))
    for i, row in enumerate(parsed["restraint"], 1):
        tasks.append(task("D", "restraint_constraint", i, 9,
            {"constraint": row["Constraint"], "exercise": row["Exercise"],
             "observed_rest_or_note_count": None}))
    for i, row in enumerate(parsed["register_texture"], 1):
        if int(row["Arc"]) != i:
            raise CandidateError(f"REGISTER_ARC_NUMBER {i}")
        tasks.append(task("E", "register_texture_arc", i, 10,
            {"register_map": row["Register map"], "texture_map": row["Texture map"],
             "specific_octave_or_voicing": None}))

    expected_stages = [("Establish", 1, 2), ("Develop", 3, 4),
                       ("Pre-climax", 5, 5), ("Climax", 6, 6),
                       ("Aftershock", 7, 7), ("Release", 8, 8)]
    for i, (row, (name, first, last)) in enumerate(zip(parsed["climax_stages"], expected_stages, strict=True), 1):
        if row["Stage"] != name or row["Bars"] != (str(first) if first == last else f"{first}-{last}"):
            raise CandidateError(f"CLIMAX_BAR_PLAN {i}")
        tasks.append(task("F", "climax_stage", i, 11,
            {"stage": name, "first_bar": first, "last_bar": last,
             "allowed_intensity": row["Allowed intensity"],
             "chosen_device": None, "numeric_intensity": None}))
    for i, row in enumerate(parsed["climax_release"], 1):
        tasks.append(task("F", "post_climax_release", i, 12,
            {"device": row["Climax device"], "required_release": row["Required release"],
             "performed_intensity": None}))

    studies = []
    for i, page in enumerate(range(13, 17), 1):
        page_lines = pages[page - 1].splitlines()
        heads = [s for s in page_lines if s.startswith(f"Module G - Study {i} - ")]
        charts = [s for s in page_lines if s.startswith("| ") and s.endswith(" |")]
        if len(heads) != 1 or len(charts) != 1:
            raise CandidateError(f"G_STUDY_BOUNDARY {i}")
        chords = [x.strip() for x in charts[0].strip("|").split("|")]
        if len(chords) != 8:
            raise CandidateError(f"G_EIGHT_BARS {i}")
        pass_rows = table(pages[page - 1], ["Pass", "Requirement"], 6, f"G{i}")
        if [int(r["Pass"]) for r in pass_rows] != list(range(1, 7)):
            raise CandidateError(f"G_PASS_SEQUENCE {i}")
        direction = page_lines[page_lines.index(charts[0]) + 1]
        studies.append({"study": i, "page": page, "title": heads[0],
                        "chords": chords, "direction": direction,
                        "passes": pass_rows})
        tasks.append(task("G", "long_form_study", i, page,
            {"title": heads[0], "chords": chords, "direction": direction,
             "passes": pass_rows, "target_notes": None,
             "exact_articulation_plan": None}))
        for bar, chord in enumerate(chords, 1):
            markers.append(marker("G", "study_chord_bar", i, page, bar,
                                  chord, None, {"direction": direction}))
        for pass_no, row in enumerate(pass_rows, 1):
            tasks.append(task("G", "study_pass", (i - 1) * 6 + pass_no, page,
                {"study": i, "pass": pass_no,
                 "requirement": row["Requirement"]}))

    for i, row in enumerate(parsed["fixed_targets"], 1):
        chord, target = row["Chord"], row["Required target"]
        if int(row["Bar"]) != i or chord not in CHORD_TONES or \
                PC[target] not in CHORD_TONES[chord]:
            raise CandidateError(f"H_TARGET_CHORD {i}")
        tasks.append(task("H", "fixed_target_improvised_expression", i, 17,
            {"bar": i, "chord": chord, "required_target": target,
             "freedom": row["Freedom"], "repeat_count": 8,
             "consecutive_pass_same_bar_articulation_repeat": False,
             "chosen_articulation": None}))
        markers.append(marker("H", "fixed_target", i, 17, i, chord, target,
                              {"freedom": row["Freedom"]}))
    for i, row in enumerate(parsed["restraint_randomizer"], 1):
        tasks.append(task("H", "restraint_randomizer", i, 18,
            {"command": row["Command"], "constraint": row["Constraint"],
             "four_chord_loop": None, "draw_order": None}))

    capstone = []
    first_peak = second_peak = None
    for i, row in enumerate(parsed["capstone"], 1):
        first, last = map(int, row["Bars"].split("-"))
        chords = row["Harmony"].split("-")
        if (first, last) != (4 * i - 3, 4 * i) or len(chords) != 4:
            raise CandidateError(f"CAPSTONE_SECTION {i}")
        role = row["Arc role"]
        if role == "first peak":
            first_peak = (first, last)
        if role == "second peak":
            second_peak = (first, last)
        tasks.append(task("I", "capstone_section", i, 19,
            {"first_bar": first, "last_bar": last, "chords": chords,
             "arc_role": role, "expression": row["Expression"],
             "dynamic": row["Dynamic"], "specific_target_notes": None,
             "numeric_loudness": None}))
        for offset, chord in enumerate(chords):
            bar = first + offset
            capstone.append({"bar": bar, "section": i, "chord": chord,
                             "arc_role": role, "expression": row["Expression"],
                             "dynamic": row["Dynamic"]})
            markers.append(marker("I", "capstone_chord_bar", i, 19, bar,
                chord, None, {"arc_role": role, "expression": row["Expression"],
                              "dynamic": row["Dynamic"]}))
    if [x["bar"] for x in capstone] != list(range(1, 41)) or \
            first_peak != (13, 16) or second_peak != (25, 28):
        raise CandidateError("FORTY_BAR_TWO_PEAK_PLAN")
    for i, row in enumerate(parsed["completion_rubric"], 1):
        tasks.append(task("J", "completion_score_category", i, 20,
            {"category": row["Category"], "anchors": {k: row[k] for k in ("0", "1", "2")},
             "observed_score": None}))
    if "14/16 or better on two separate days." not in lines or \
            "No zero in pitch/intonation, articulation choice, restraint, or recovery." not in lines or \
            "Pass Section XIII: 14/16 or better on two separate days" not in pages[19]:
        raise CandidateError("MASTERY_GATE_PARITY")

    methods = [("A", 3, "Begin with no bends, slides, harmonics, or vibrato."),
               ("B", 5, "The choices are starting tests, not rigid rules."),
               ("C", 8, "Record each pair."),
               ("D", 9, "Deliberate silence is not a missing event."),
               ("E", 10, "register change is an expressive option"),
               ("F", 11, "Choose only one climax device:"),
               ("G", 13, "reduce ornaments by 50%"),
               ("H", 17, "Repeat eight times."),
               ("I", 19, "The capstone contains two planned peaks."),
               ("J", 20, "Section XIII is now complete.")]
    for i, (module, page, excerpt) in enumerate(methods, 1):
        if excerpt not in pages[page - 1]:
            raise CandidateError(f"PDF_METHOD_MISSING {module}:{page}")
        tasks.append(task(module, "instructional_method", i, page,
                          {"source_excerpt": excerpt, "full_instruction_page": page}))

    return {"schema": "fathom.detached_curriculum_source_candidate.v1",
            "level": 94, "section": "XIII", "wbs_owner": "2.3.1.3.1",
            "status": "candidate_only", "source_map": inventory,
            "source_pins": {"txt": {"path": str(TXT), "bytes": PINS["txt"][0],
                            "sha256": PINS["txt"][1]},
                            "pdf": {"path": str(PDF), "bytes": PINS["pdf"][0],
                            "sha256": PINS["pdf"][1]}},
            "read_only_narrow_evidence": "Results/parallel-06/exercises/conversion/20260923T115232Z-2.3.1.3.1-level094-module-a-music-r01-results.md",
            "source_archive": {"txt_lines": [{"line": i, "text": x}
                                             for i, x in enumerate(lines, 1)],
                               "pdf_pages": [{"page": i, "text": x}
                                             for i, x in enumerate(pages, 1)]},
            "pdf_tables": {name: {"page": TABLES[name][0], "rows": rows}
                           for name, rows in parsed.items()},
            "module_workload_declared": COUNTS, "declared_workload_total": 1472,
            "tasks": tasks, "bar_or_window_markers": markers,
            "g_studies": studies, "capstone_bar_plan": capstone,
            "source_tensions": [
                {"issue": "TXT supplies an index, while PDF pages 2-20 provide detailed expression tasks",
                 "resolution": "convert PDF detail with page provenance"},
                {"issue": "1472 declared events are not printed as 1472 pitched note or attack specifications",
                 "resolution": "retain declared count separately from source-supported markers"},
                {"issue": "most choices are qualitative; precise target pitch, numeric dynamics, articulation performance, and timing are not authored",
                 "resolution": "leave unprinted values null"}],
            "unresolved_performance_fields": ["specific_target_pitch", "octave",
                "fret", "string", "tempo", "onset_q", "duration_q",
                "numeric_loudness", "performed_articulation", "score",
                "canonical_task_id", "canonical_event_id"],
            "admission_claim": False}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path,
                        default=ROOT / OUT / "level094_whole_candidate.json")
    args = parser.parse_args()
    candidate = build()
    output = args.output.resolve()
    if not output.is_relative_to((ROOT / OUT).resolve()):
        raise CandidateError("OUTPUT_OUTSIDE_P07_LEVEL94_BUILD")
    output.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(candidate, indent=2, ensure_ascii=False).encode() + b"\n"
    output.write_bytes(data)
    print(json.dumps({"output": str(output), "bytes": len(data),
                      "sha256": sha(data), "tasks": len(candidate["tasks"]),
                      "bar_or_window_markers": len(candidate["bar_or_window_markers"]),
                      "declared_workload": candidate["declared_workload_total"]}))


if __name__ == "__main__":
    main()
