#!/usr/bin/env python3
"""Detached whole Level96 source projection, with no inferred song or event facts."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

from pypdf import PdfReader, __version__ as PYPDF_VERSION


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "Build/parallel-06/2.3-level096-whole-semantic-r01"
PYPDF_PIN = "6.10.0"
SOURCE = {
    "txt": ("Notes/music/guitar project/TXT version/Guitar_Exercises_Section_XIV_Level_96_Chart_to_Performance_Repertoire_Reconstruction_Selective_Transcription_Independent_Voicing_Style_Decisions_and_Rehearsal_Planning.txt", 1646, "2d2b8e84da6fd16994d078cd779bc8c963a7b1b5e4cbee03e360de97cb80c54b"),
    "pdf": ("Notes/music/guitar project/PDF version/Guitar_Exercises_Section_XIV_Level_96_Chart_to_Performance_Repertoire_Reconstruction_Selective_Transcription_Independent_Voicing_Style_Decisions_and_Rehearsal_Planning.pdf", 45292, "51435c2e4537fccb536a6ba109d73db1a317247cbd4206ad3d67a5d4f986283f"),
}
MODULES = [
    ("A", "Lead-sheet reduction and missing-information audit", 96),
    ("B", "Independent form and harmonic-function mapping", 112),
    ("C", "Selective transcription: riffs, fills, and landmarks", 144),
    ("D", "Independent voicing and register decisions", 128),
    ("E", "Style matching from rhythmic evidence", 128),
    ("F", "Self-authored rehearsal plan and risk ranking", 96),
    ("G", "Two partially scaffolded 16-bar repertoire studies", 192),
    ("H", "One minimally scaffolded 24-bar reconstruction", 192),
    ("I", "Forty-eight-bar independent performance capstone", 320),
    ("J", "Post-take diagnosis and next-session planning", 64),
]
GUIDANCE = "Mark each answer: supplied, must transcribe, safe to choose, or safe to omit."
TABLES = [
    (3, "A", "Module A - Lead-Sheet Missing-Information Audit", ("Prompt", "Decision"), 8,
     GUIDANCE),
    (4, "B", "Module B - Independent Form Map", ("Pass", "Deliverable"), 8,
     "The completed form map must fit on half a page. If it does not, it is still too detailed."),
    (5, "B", "Module B - Harmonic Function Map", ("Task", "Example output"), 7,
     "A chord name is not yet an interpretation. Function predicts where the music is going."),
    (6, "C", "Module C - Selective Transcription Priority", ("Priority", "Transcribe", "Usually do not need note-for-note"), 6,
     "For each excerpt, justify why a detail is structural before spending rehearsal time on exact transcription."),
    (7, "C", "Module C - Eight Selective-Transcription Cards", ("Card", "Given", "Student reconstructs"), 8,
     "Verification: sing/tap first, then locate on guitar, then compare against source."),
    (8, "D", "Module D - Independent Voicing Decisions", ("Constraint", "Choose"), 8,
     "Write two viable voicing plans for every section, then choose one after playing with the groove."),
    (9, "D", "Module D - Register Comparison", ("Pass", "Voicing family", "Question"), 6,
     "The easiest grip is not automatically the best arrangement choice."),
    (10, "E", "Module E - Style Matching from Evidence", ("Evidence", "Inference to test"), 8,
     "Describe the evidence before naming the style. Then choose the closest learned groove engine and modify it to match the source."),
    (11, "E", "Module E - Style Approximation Ladder", ("Pass", "Goal"), 8,
     "Effects may support style, but the groove must remain identifiable without them."),
    (12, "F", "Module F - Self-Authored Rehearsal Plan", ("Risk score", "Meaning", "Rehearsal allocation"), 5,
     "Rank no more than five risks. Do not spend equal time on every measure."),
    (13, "F", "Module F - 30-Minute Rehearsal Budget", ("Minutes", "Default allocation"), 7,
     "The student may alter the allocation, but must write the reason before practice begins."),
    (16, "H", "Module H - Minimally Scaffolded 24-Bar Reconstruction", ("Fact", "Supplied information"), 7,
     "Construct the form, chord sequence, groove, voicings, motif placement, transitions, dynamics, and recovery version. Then perform from memory."),
    (17, "I", "Module I - Forty-Eight-Bar Independent Performance Capstone", ("Bars", "Section", "Harmony", "Student responsibility"), 8,
     "Only the chord/form skeleton is supplied. The student must independently create groove, voicings, register map, fills, expression arc, cue map, fallback\narrangement, and rehearsal plan."),
]


class SourceError(ValueError):
    pass


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise SourceError(reason)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def read_source(root: Path = ROOT) -> dict:
    root = root.resolve(strict=True)
    require(Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], cwd=root, text=True).strip()) == root,
            "root is not the sole Git checkout")
    require(PYPDF_VERSION == PYPDF_PIN, f"PDF extractor drift: {PYPDF_VERSION}")
    result = {}
    for kind in ("txt", "pdf"):
        relative, size, expected = SOURCE[kind]
        path = root
        for part in Path(relative).parts:
            path /= part
            require(not path.is_symlink(), f"source symlink: {relative}")
        raw = path.read_bytes()
        require(path.resolve().is_relative_to(root) and len(raw) == size and sha(raw) == expected,
                f"pinned Level96 {kind} source drift")
        result[kind] = {"identity": {"path": relative, "bytes": size, "sha256": expected},
                        "content": raw.decode("utf-8").splitlines() if kind == "txt"
                        else [page.extract_text() or "" for page in PdfReader(path).pages]}
    require(len(result["pdf"]["content"]) == 18, "Level96 PDF page count drift")
    return result


def exact_line(lines: list[str], value: str) -> int:
    matches = [i for i, line in enumerate(lines, 1) if line == value]
    require(len(matches) == 1, f"TXT line missing/repeated: {value}")
    return matches[0]


def page_ref(pages: list[str], page: int, heading: str) -> dict:
    value = pages[page-1]
    require(value.startswith(heading + "\n"), f"PDF heading drift: page {page}")
    return {"page": page, "extracted_text_sha256": sha(value.encode("utf-8"))}


def parse_table(pages: list[str], page: int, heading: str, columns: tuple[str, ...],
                count: int, footer: str, preface: str = "") -> list[dict]:
    ref = page_ref(pages, page, heading)
    prefix = heading + "\n" + preface + "\n".join(columns) + "\n"
    value = pages[page-1]
    require(value.startswith(prefix) and value.endswith(footer + "\n"),
            f"PDF table boundary drift: page {page}")
    body = value[len(prefix):-(len(footer)+1)]
    cells = body.strip().splitlines()
    require(len(cells) == count*len(columns), f"PDF table row/cell count drift: page {page}")
    return [{"row_ordinal": n+1,
             "fields": dict(zip(columns, cells[n*len(columns):(n+1)*len(columns)])),
             "source": {**ref, "table_heading": heading, "row_ordinal": n+1}}
            for n in range(count)]


def declarations(lines: list[str], pages: list[str]) -> tuple[list[dict], int]:
    total_line = exact_line(lines, "COMPLETE WRITTEN WORKLOAD: 1472 events")
    require(pages[0].startswith("Guitar Exercises - Section XIV, Level 96\n"), "PDF title drift")
    parts = pages[0].split("Module\nExercise\nEvents\n", 1)
    require(len(parts) == 2 and parts[1].endswith(
        "TOTAL\n1472\nCore rule: do not transcribe everything. Transcribe what the performance actually depends on.\n"),
        "PDF module total/core rule drift")
    body = parts[1].split("TOTAL\n1472\n", 1)[0].splitlines()
    require(len(body) == 30, "PDF module table shape drift")
    result = []
    for n, (letter, title, count) in enumerate(MODULES):
        line = exact_line(lines, f"{letter}. {title} - {count} events")
        require(body[n*3:n*3+3] == [letter, title, str(count)],
                f"TXT/PDF module declaration mismatch: {letter}")
        result.append({"module": letter, "title": title, "declared_events": count,
                       "txt_line": line, "pdf": {**page_ref(pages, 1, "Guitar Exercises - Section XIV, Level 96"),
                                                 "table_row": n+1}})
    require(sum(x["declared_events"] for x in result) == 1472, "module event sum differs")
    return result, total_line


def task(row: dict, key: str) -> dict:
    return {"local_key": key, **row, "declared_event_count_for_row": None,
            "canonical_id": None, "song_or_recording_finding": None,
            "learner_answer": None, "pitch": None, "duration": None,
            "performed_timing": None}


def build_from_source(source: dict) -> dict:
    lines, pages = source["txt"]["content"], source["pdf"]["content"]
    declarations_, total_line = declarations(lines, pages)
    modules = {x["module"]: {**x, "tasks": [], "per_task_event_counts_known": False,
                              "allocated_event_count": None} for x in declarations_}
    reference = parse_table(pages, 2, "Reference - Information Sufficiency for Repertoire",
                            ("Information", "If supplied", "If missing"), 8,
                            "The player distinguishes essential information from optional detail before touching the difficult passages.")
    for page, letter, heading, columns, count, footer in TABLES:
        preface = "You are given only the following structural facts. All other arrangement decisions are yours.\n" if page == 16 else ""
        rows = parse_table(pages, page, heading, columns, count, footer, preface)
        if page in {4, 7, 9, 11}:
            require([r["fields"][columns[0]] for r in rows] == [str(x) for x in range(1, count+1)],
                    f"numbered task order drift: page {page}")
        if page == 12:
            require([r["fields"]["Risk score"] for r in rows] == [str(x) for x in range(5)],
                    "risk score order drift")
        for row in rows:
            modules[letter]["tasks"].append(task(row, f"L96-{letter}-p{page}-r{row['row_ordinal']}"))
    studies = []
    for study, page in [(1, 14), (2, 15)]:
        heading = f"Module G - Study {study} - " + ("Partial chart" if study == 1 else "Partial recording brief")
        value = pages[page-1]
        require(value.startswith(heading + "\n") and value.count("Pass\nDeliverable\n") == 1,
                f"Module G study boundary drift: {study}")
        before, after = value.split("Pass\nDeliverable\n", 1)
        preface = before[len(heading)+1:].splitlines()
        require(len(preface) == 2 and preface[0].startswith("Given: ")
                and preface[1].startswith("Student decisions: "),
                f"Module G given/decision drift: {study}")
        fields = after.strip().splitlines()
        require(len(fields) == 12 and fields[0::2] == [str(x) for x in range(1, 7)],
                f"Module G pass table drift: {study}")
        studies.append({"study": study, "page": page, "given": preface[0][7:],
                        "student_decisions": preface[1][19:], "source": page_ref(pages, page, heading)})
        for n in range(6):
            row = {"row_ordinal": n+1, "fields": {"Pass": fields[n*2], "Deliverable": fields[n*2+1]},
                   "study": study, "given": preface[0][7:], "student_decisions": preface[1][19:],
                   "source": {**page_ref(pages, page, heading), "row_ordinal": n+1}}
            modules["G"]["tasks"].append(task(row, f"L96-G-study{study}-pass{n+1}"))
    expected_ranges = ["1-4", "5-12", "13-16", "17-24", "25-32", "33-40", "41-44", "45-48"]
    require([x["fields"]["Bars"] for x in modules["I"]["tasks"]] == expected_ranges,
            "Module I 48-bar range coverage drift")
    heading = "Module J - Post-Take Diagnosis"
    value = pages[17]
    prefix = heading + "\nQuestion\nWrite one answer only\n"
    marker = "Pass Level 96: 14/16 or better on two separate days across form, harmony, groove/style match, selective transcription, voicing decisions, rehearsal planning,\n"
    require(value.startswith(prefix) and value.count(marker) == 1
            and value.endswith("arrangement against the source.\n"), "Module J diagnosis/mastery boundary drift")
    questions = value[len(prefix):].split(marker, 1)[0].splitlines()
    require(len(questions) == 7 and all(q.endswith("?") for q in questions),
            "Module J question count/shape drift")
    for n, question in enumerate(questions, 1):
        row = {"row_ordinal": n, "fields": {"Question": question, "answer_rule": "Write one answer only"},
               "source": {**page_ref(pages, 18, heading), "row_ordinal": n}}
        modules["J"]["tasks"].append(task(row, f"L96-J-question{n}"))
    require(exact_line(lines, "KEY SKILLS") == 24 and exact_line(lines, "CAPSTONE") == 36,
            "TXT skills/capstone section drift")
    skills = [{"txt_line": n, "text": lines[n-1][2:]} for n in range(25, 35)]
    require(all(lines[n-1].startswith("- ") for n in range(25, 35)), "TXT key-skill list drift")
    capstone_line = exact_line(lines, "48 bars with only form/chord skeleton supplied. Student creates the performance arrangement and rehearsal plan.")
    mastery_line = exact_line(lines, "14/16 or better on two separate days.")
    zero_line = exact_line(lines, "No zero in form, groove/style match, rehearsal planning, or recovery.")
    next_line = exact_line(lines, "Level 97: recording-led repertoire reconstruction with no supplied chord chart.")
    require("memory, and recovery. No zero in form, groove/style match, rehearsal planning, or recovery.\n" in value,
            "PDF protected mastery domains drift")
    task_count = sum(len(m["tasks"]) for m in modules.values())
    require(task_count == 113, f"whole Level96 task row coverage differs: {task_count}")
    return {"wbs": "2.3.1.3.1", "level": 96, "section": "XIV",
            "status": "Pending", "review": "Pending", "detached_source_candidate": True,
            "whole_source_semantic_projection": True, "whole_workbook_accepted": False,
            "canonical_ids_allocated": False, "schema1_imported": False, "runtime_eligible": False,
            "extractor": f"pypdf {PYPDF_PIN}",
            "source_identities": {k: source[k]["identity"] for k in ("txt", "pdf")},
            "txt_lines": [{"line": n, "text": text} for n, text in enumerate(lines, 1)],
            "pdf_pages": [{"page": n, "heading": text.splitlines()[0],
                           "extracted_text_sha256": sha(text.encode()), "extracted_text": text}
                          for n, text in enumerate(pages, 1)],
            "module_order": [x[0] for x in MODULES], "modules": list(modules.values()),
            "supporting_reference": {"page": 2, "rows": reference,
                                     "relation": "information-sufficiency guidance, no answer assigned"},
            "g_studies": studies, "declared_total_events": 1472,
            "txt_total_anchor_line": total_line, "extracted_task_rows": task_count,
            "key_skills": skills, "capstone_txt_line": capstone_line,
            "mastery": {"txt_lines": [mastery_line, zero_line], "pdf": page_ref(pages, 18, heading),
                        "minimum": "14/16 or better on two separate days",
                        "protected_zero_domains": ["form", "groove/style match", "rehearsal planning", "recovery"]},
            "next_level_source_line": next_line,
            "unresolved": {"event_distribution_to_tasks": "all 1472 declared events lack printed row allocation",
                           "per_task_event_counts": None, "actual_song_or_recording": None,
                           "classification_answers": None, "notes_and_voicings": None,
                           "performed_timing": None, "rubric_realization": None,
                           "canonical_identity": None, "runtime_admission": False}}


def build(root: Path = ROOT) -> dict:
    return build_from_source(read_source(root))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(BUILD.resolve()):
        parser.error("output must remain under Build/parallel-06/2.3-level096-whole-semantic-r01")
    result = build()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    print(f"PASS: {len(result['modules'])} modules, {result['extracted_task_rows']} task rows, "
          f"{len(result['supporting_reference']['rows'])} reference rows, {result['declared_total_events']} unallocated events")


if __name__ == "__main__":
    main()
