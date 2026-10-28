#!/usr/bin/env python3
"""Detached whole Level91 semantic source projection; no playable event invention."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

from pypdf import PdfReader, __version__ as PYPDF_VERSION


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "Build/parallel-06/2.3-level091-whole-semantic-r01"
PYPDF_PIN = "6.10.0"
SOURCE = {
    "txt": ("Notes/music/guitar project/TXT version/Guitar_Exercises_Section_XIII_Level_91_Advanced_Bend_Intonation_Unison_Oblique_Bends_Vibrato_Architecture_Expressive_Timing_and_Dynamic_Attack.txt", 1162, "0fac712a8e4ac90d43fc218bb0b68063f139c53523c4c28c442921b8e1f118b7"),
    "pdf": ("Notes/music/guitar project/PDF version/Guitar_Exercises_Section_XIII_Level_91_Advanced_Bend_Intonation_Unison_Oblique_Bends_Vibrato_Architecture_Expressive_Timing_and_Dynamic_Attack.pdf", 41521, "653762bdb591329d04a382df20b6bd57bbe8050e971cf5d081bc549ba5374fc1"),
}
EXPECTED_MODULES = [
    ("A", "Bend calibration", 144), ("B", "Pre-bends and releases", 128),
    ("C", "Unison and oblique bends", 144), ("D", "Bent-note vibrato", 128),
    ("E", "Fretted-note vibrato", 128), ("F", "Dynamic attack and pick position", 128),
    ("G", "Expressive timing", 112), ("H", "Four phrase studies", 192),
    ("I", "32-bar capstone", 256), ("J", "Recovery/mastery", 64),
]
INSTRUCTION = "Use a clean/lightly driven tone first. Record and verify consistency before adding more ornament."
TABLES = [
    (3, "A", "Module A - Bend Intonation", ("Cell", "Example", "Task"), 8),
    (5, "B", "Module B - Pre-Bends and Releases", ("Cell", "Action"), 8),
    (6, "C", "Module C - Unison Bends", ("Fixed", "Bent", "Goal"), 6),
    (7, "C", "Module C - Oblique Bends", ("Held voice", "Moving voice", "Task"), 6),
    (8, "D", "Module D - Bent-Note Vibrato", ("Pass", "Vibrato"), 8),
    (9, "E", "Module E - Fretted Vibrato", ("Type", "Width/rate", "Use"), 6),
    (10, "F", "Module F - Dynamic Attack", ("Pass", "Attack / position"), 8),
    (11, "G", "Module G - Expressive Timing", ("Cell", "Behavior"), 8),
    (16, "I", "Module I - 32-Bar Expression Capstone", ("Bars", "Harmony", "Focus"), 8),
    (17, "J", "Module J - Recovery and Mastery", ("Failure", "Repair"), 8),
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
                f"pinned Level91 {kind} source drift")
        result[kind] = {"identity": {"path": relative, "bytes": size, "sha256": expected},
                        "content": raw.decode("utf-8").splitlines() if kind == "txt"
                        else [page.extract_text() or "" for page in PdfReader(path).pages]}
    require(len(result["txt"]["content"]) == 37 and len(result["pdf"]["content"]) == 17,
            "Level91 line/page count drift")
    return result


def exact_line(lines: list[str], value: str) -> int:
    matches = [i for i, line in enumerate(lines, 1) if line == value]
    require(len(matches) == 1, f"TXT line missing/repeated: {value}")
    return matches[0]


def page_ref(pages: list[str], page: int, heading: str) -> dict:
    value = pages[page - 1]
    require(value.startswith(heading + "\n"), f"PDF page heading drift: {page}")
    return {"page": page, "extracted_text_sha256": sha(value.encode("utf-8"))}


def table_rows(pages: list[str], page: int, heading: str, columns: tuple[str, ...],
               count: int, footer: str | None) -> list[dict]:
    ref = page_ref(pages, page, heading)
    text = pages[page - 1]
    prefix = heading + "\n" + "\n".join(columns) + "\n"
    require(text.startswith(prefix), f"PDF table header drift: page {page}")
    body = text[len(prefix):]
    if footer is not None:
        require(body.endswith(footer + "\n"), f"PDF table footer drift: page {page}")
        body = body[:-(len(footer) + 1)]
    cells = body.strip().splitlines()
    require(len(cells) == count * len(columns), f"PDF table row/cell count drift: page {page}")
    rows = []
    for index in range(count):
        values = cells[index * len(columns):(index + 1) * len(columns)]
        rows.append({"row_ordinal": index + 1, "fields": dict(zip(columns, values)),
                     "source": {**ref, "table_heading": heading, "row_ordinal": index + 1}})
    return rows


def declarations(lines: list[str], pages: list[str]) -> tuple[list[dict], int]:
    txt_total_line = exact_line(lines, "COMPLETE WRITTEN WORKLOAD: 1424 events")
    prefix = "Guitar Exercises - Section XIII, Level 91\n"
    require(pages[0].startswith(prefix), "PDF title page drift")
    # Page 1 has a five-line title block before its module table.
    opening = pages[0].split("Module\nExercise\nEvents\n", 1)
    require(len(opening) == 2 and opening[1].endswith("TOTAL\n1424\n"), "PDF module table/total drift")
    body = opening[1][:-len("TOTAL\n1424\n")].splitlines()
    require(len(body) == 30, "PDF module table shape drift")
    declared = []
    for index, (letter, title, count) in enumerate(EXPECTED_MODULES):
        txt_line = exact_line(lines, f"{letter}. {title} - {count} events")
        require(body[index*3:index*3+3] == [letter, title, str(count)],
                f"TXT/PDF module declaration mismatch: {letter}")
        declared.append({"module": letter, "title": title, "declared_events": count,
                         "txt_line": txt_line, "pdf": {**page_ref(pages, 1, "Guitar Exercises - Section XIII, Level 91"),
                                                       "table_row": index+1}})
    require(sum(x["declared_events"] for x in declared) == 1424, "module event sum differs")
    return declared, txt_total_line


def build_from_source(source: dict) -> dict:
    lines, pages = source["txt"]["content"], source["pdf"]["content"]
    declarations_, total_line = declarations(lines, pages)
    require(exact_line(lines, "MASTERY") == 32 and exact_line(lines, "NEXT") == 36,
            "TXT mastery/next section drift")
    require(lines[32] == "14/16 or better on two separate days."
            and lines[33] == "No zero in bend intonation, vibrato control, pulse, or recovery.",
            "TXT mastery wording drift")
    require(exact_line(lines, "KEY SKILLS") == 21 and all(lines[n-1].startswith("- ") for n in range(22, 31)),
            "TXT key-skill section drift")
    key_skills = [{"txt_line": n, "text": lines[n-1][2:]} for n in range(22, 31)]
    next_line = exact_line(lines, "Level 92: rakes, grace notes, double-stop slides, natural/pinch harmonics, volume swells, muted attacks, and articulation chains.")
    modules = {x["module"]: {**x, "tasks": [], "per_task_event_counts_known": False,
                              "allocated_event_count": None} for x in declarations_}
    support = []
    for page, heading, columns, count in [
        (2, "Bend Calibration", ("Bend", "Semitones", "Method"), 6),
        (4, "Timed Bend Arrivals", ("Arrival", "Task"), 6),
    ]:
        rows = table_rows(pages, page, heading, columns, count, INSTRUCTION)
        support.append({"heading": heading, "page": page, "relation":
                        "calibration_reference_for_A" if page == 2 else "adjacent_unallocated_timed_arrival_reference",
                        "rows": rows})
    for page, letter, heading, columns, count in TABLES:
        footer = INSTRUCTION if page != 16 and page != 17 else (
            "One master tempo. Ornament density may change; form and chord targets may not."
            if page == 16 else None)
        if page == 17:
            # The recovery table is followed by independent mastery and next statements.
            value = pages[16]
            marker = "Pass: 14/16 or better on two separate days; no zero in bend intonation, vibrato control, pulse, or recovery.\n"
            require(value.count(marker) == 1 and value.endswith(
                "Next: Level 92 - rakes, grace notes, double-stop slides, natural/pinch harmonics, volume swells, muted attacks, and articulation chains.\n"),
                "PDF mastery/next wording drift")
            temporary = list(pages)
            temporary[16] = value.split(marker, 1)[0]
            rows = table_rows(temporary, page, heading, columns, count, None)
            for row in rows:
                row["source"]["extracted_text_sha256"] = sha(value.encode("utf-8"))
        else:
            rows = table_rows(pages, page, heading, columns, count, footer)
        if letter in {"A", "B", "D", "F", "G"}:
            require([row["fields"][columns[0]] for row in rows] == [str(x) for x in range(1, count+1)],
                    f"numbered source task drift: {letter}")
        for row in rows:
            modules[letter]["tasks"].append({"local_key": f"L91-{letter}-p{page}-r{row['row_ordinal']}",
                                               **row, "declared_event_count_for_row": None,
                                               "canonical_id": None, "pitch": None, "duration": None,
                                               "performed_timing": None})
    for study, page in enumerate(range(12, 16), 1):
        heading = f"Module H - Study {study}"
        text = pages[page-1]
        match = re.fullmatch(re.escape(heading) + r"\nHarmony: ([^\n]+)\nFocus: ([^\n]+)\n"
                             + re.escape("Pass\nRequirement\n") + r"((?:[^\n]+\n){12})", text)
        require(match is not None, f"Module H study layout drift: {study}")
        pass_lines = match.group(3).splitlines()
        require(pass_lines[0::2] == [str(x) for x in range(1, 7)], f"Module H pass order drift: {study}")
        for index in range(6):
            modules["H"]["tasks"].append({"local_key": f"L91-H-study{study}-pass{index+1}",
                                            "study": study, "harmony": match.group(1),
                                            "focus": match.group(2), "pass": index+1,
                                            "requirement": pass_lines[index*2+1],
                                            "source": {**page_ref(pages, page, heading), "row_ordinal": index+1},
                                            "declared_event_count_for_row": None, "canonical_id": None,
                                            "pitch": None, "duration": None, "performed_timing": None})
    ranges = [x["fields"]["Bars"] for x in modules["I"]["tasks"]]
    require(ranges == [f"{start}-{start+3}" for start in range(1, 33, 4)],
            "Module I 32-bar range coverage drift")
    require(pages[16].find("Pass: 14/16 or better on two separate days; no zero in bend intonation, vibrato control, pulse, or recovery.") >= 0,
            "PDF mastery missing")
    require(len(modules["A"]["tasks"]) == 8 and len(modules["H"]["tasks"]) == 24,
            "module task coverage differs")
    all_tasks = sum(len(module["tasks"]) for module in modules.values())
    require(all_tasks == 98, f"whole Level91 task row coverage differs: {all_tasks}")
    pages_out = [{"page": n, "heading": text.splitlines()[0], "extracted_text_sha256": sha(text.encode()),
                  "extracted_text": text} for n, text in enumerate(pages, 1)]
    return {"wbs": "2.3.1.3.1", "level": 91, "section": "XIII",
            "status": "Pending", "review": "Pending", "detached_source_candidate": True,
            "whole_source_semantic_projection": True, "whole_workbook_accepted": False,
            "canonical_ids_allocated": False, "runtime_eligible": False, "schema1_imported": False,
            "source_identities": {k: source[k]["identity"] for k in ("txt", "pdf")},
            "extractor": f"pypdf {PYPDF_PIN}", "txt_lines": [{"line": n, "text": v} for n, v in enumerate(lines, 1)],
            "pdf_pages": pages_out, "module_order": [x[0] for x in EXPECTED_MODULES],
            "modules": list(modules.values()), "supporting_tables": support,
            "declared_total_events": 1424, "txt_total_anchor_line": total_line,
            "extracted_task_rows": all_tasks, "supporting_rows": 12,
            "key_skills": key_skills, "next_level_source_line": next_line,
            "mastery": {"txt_lines": [33, 34], "minimum": "14/16 or better on two separate days",
                        "protected_zero_domains": ["bend intonation", "vibrato control", "pulse", "recovery"],
                        "pdf_page": page_ref(pages, 17, "Module J - Recovery and Mastery")},
            "unresolved": {"event_distribution_to_tasks": "all 1424 declared events lack printed row allocation",
                           "per_task_event_counts": None, "notes_and_route": None,
                           "pitch_and_bend_curve": None, "performed_timing": None,
                           "rubric_realization": None, "canonical_identity": None,
                           "runtime_admission": False}}


def build(root: Path = ROOT) -> dict:
    return build_from_source(read_source(root))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(BUILD.resolve()):
        parser.error("output must remain under Build/parallel-06/2.3-level091-whole-semantic-r01")
    payload = build()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    print(f"PASS: {len(payload['modules'])} modules, {payload['extracted_task_rows']} task rows, "
          f"{payload['supporting_rows']} support rows, {payload['declared_total_events']} unallocated events")


if __name__ == "__main__":
    main()
