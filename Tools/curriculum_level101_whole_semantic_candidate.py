#!/usr/bin/env python3
"""Detached whole Level101 composition-source projection without invented events."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from pypdf import PdfReader, __version__ as PYPDF_VERSION


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "Build/parallel-06/2.3-level101-whole-semantic-r01"
PYPDF_PIN = "6.10.0"
SOURCE = {
    "txt": ("Notes/music/guitar project/TXT version/Guitar_Exercises_Section_XV_Level_101_Larger_Form_Composition_AB_Sections_Verse_Chorus_Bridges_Transitions_Thematic_Return_and_32_Bar_Originals.txt", 1424, "8ad7e8e8ad58090b44da4bed3b141d45b4b76fd1d7a0182c0a22d3dd0f20c282"),
    "pdf": ("Notes/music/guitar project/PDF version/Guitar_Exercises_Section_XV_Level_101_Larger_Form_Composition_AB_Sections_Verse_Chorus_Bridges_Transitions_Thematic_Return_and_32_Bar_Originals.pdf", 26684, "e184d9e8f8681d6d5b1ad3f9d1ab30d12b2fb7215756f2cae26b6c535f79698f"),
}
MODULES = [
    ("A", "A/B contrast from shared source material", 144),
    ("B", "Verse/chorus contrast and return", 144),
    ("C", "Bridge construction and harmonic departure", 128),
    ("D", "Transitions, pickups, and connective bars", 128),
    ("E", "Thematic return and variation", 128),
    ("F", "16-bar form construction", 144),
    ("G", "32-bar form construction", 160),
    ("H", "Four complete larger-form composition studies", 224),
    ("I", "Thirty-two-bar original composition capstone", 320),
    ("J", "Revision, reduction, and authorship audit", 64),
]
TABLES = [
    (3, "A", "Module A - A/B Contrast from Shared Material", ("Variable", "A section", "B section"), 7,
     "Create four A/B pairs. Change only two variables at first; preserve the rest."),
    (4, "A", "Module A - Identity Preservation Test", ("Test", "Question"), 6,
     "If B sounds like a different song, restore one identity-bearing feature from A."),
    (5, "B", "Module B - Verse/Chorus Contrast", ("Dimension", "Verse", "Chorus"), 6,
     "Write two 8-bar verse/chorus pairs. The chorus must feel larger even when performed at the same volume."),
    (6, "B", "Module B - Chorus Hook Construction", ("Hook type", "Constraint"), 6,
     "A chorus hook should survive a plain-tone performance with no effects or advanced articulation."),
    (7, "C", "Module C - Bridge Construction", ("Bridge strategy", "Exercise"), 8,
     "The bridge should create perspective, not erase the piece's identity."),
    (8, "C", "Module C - Bridge Exit Design", ("Exit type", "Task"), 6,
     "Loop only the final bridge bar plus the first return bar until the return feels inevitable."),
    (9, "D", "Module D - Transition Bars and Pickups", ("Transition", "Constraint"), 8,
     "Write eight one-bar transitions between the same two sections, then rank them by clarity and musical necessity."),
    (10, "D", "Module D - Transition Economy", ("Version", "Allowed content"), 5,
     "A transition is optional unless it improves direction, timing, or identity."),
    (11, "E", "Module E - Thematic Return", ("Return type", "Keep", "Change"), 8,
     "Write one A section and seven different returns. The listener should recognize all seven as descendants of the same material."),
    (12, "E", "Module E - Return Memory Test", ("Pass", "Task"), 6,
     "The return should be retrievable as an idea, not merely as a memorized fretboard sequence."),
    (13, "F", "Module F - Sixteen-Bar Form Construction", ("Form", "Bars", "Assignment"), 6,
     "Complete all six forms using the same original 3-4 note motif."),
    (14, "G", "Module G - Thirty-Two-Bar Form Construction", ("Form", "Architecture"), 6,
     "Write a one-sentence job description for each 8-bar block before composing it."),
    (20, "I", "Module I - Thirty-Two-Bar Original Composition Capstone", ("Bars", "Section", "Job", "Requirement", "Dynamic"), 4,
     "Create one complete 32-bar original. Required deliverables: working title, form map, motif statement, chord/function chart, bass map, melody or lead sheet,\ntransition notes, dynamic arc, performance arrangement, and recorded take."),
    (21, "J", "Module J - Revision, Reduction, and Authorship Audit", ("Question", "Revision task"), 8,
     "Pass Level 101: 14/16 or better across identity, section contrast, bridge function, transition clarity, thematic return, form, revision, and performance. No zero in\nidentity, form, thematic return, or performance.\nNext: Level 102 develops arrangement and orchestration for original music: multiple guitar roles, bass/inner-voice design, groove changes, dynamic\narchitecture, solo sections, and demo-ready 32-48 bar arrangements.\nFixed roadmap: Levels 100-104 Composition; Level 105 Final Musicianship Capstone. HARD STOP after Level 105."),
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
        relative, size, digest = SOURCE[kind]
        path = root
        for part in Path(relative).parts:
            path /= part
            require(not path.is_symlink(), f"source symlink: {relative}")
        raw = path.read_bytes()
        require(path.resolve().is_relative_to(root) and len(raw) == size and sha(raw) == digest,
                f"pinned Level101 {kind} source drift")
        result[kind] = {"identity": {"path": relative, "bytes": len(raw), "sha256": digest},
                        "content": raw.decode("utf-8").splitlines() if kind == "txt"
                        else [page.extract_text() or "" for page in PdfReader(path).pages]}
    require(len(result["txt"]["content"]) == 51 and len(result["pdf"]["content"]) == 21,
            "Level101 TXT line/PDF page count drift")
    return result


def exact_line(lines: list[str], value: str) -> int:
    matches = [i for i, line in enumerate(lines, 1) if line == value]
    require(len(matches) == 1, f"TXT line missing/repeated: {value}")
    return matches[0]


def page_ref(pages: list[str], page: int, heading: str) -> dict:
    value = pages[page-1]
    require(value.startswith(heading + "\n"), f"PDF heading drift: page {page}")
    return {"page": page, "extracted_text_sha256": sha(value.encode())}


def parse_table(pages: list[str], page: int, heading: str, columns: tuple[str, ...],
                count: int, footer: str) -> list[dict]:
    ref = page_ref(pages, page, heading)
    prefix = heading + "\n" + "\n".join(columns) + "\n"
    value = pages[page-1]
    require(value.startswith(prefix) and value.endswith(footer + "\n"),
            f"PDF table boundary drift: page {page}")
    cells = value[len(prefix):-(len(footer)+1)].strip().splitlines()
    require(len(cells) == count*len(columns), f"PDF table row/cell count drift: page {page}")
    return [{"row_ordinal": n+1, "fields": dict(zip(columns, cells[n*len(columns):(n+1)*len(columns)])),
             "source": {**ref, "table_heading": heading, "row_ordinal": n+1}}
            for n in range(count)]


def declarations(lines: list[str], pages: list[str]) -> tuple[list[dict], int]:
    total_line = exact_line(lines, "COMPLETE WRITTEN WORKLOAD: 1584 events")
    require(pages[0].startswith("Guitar Exercises - Section XV, Level 101\n"), "PDF title drift")
    parts = pages[0].split("Module\nExercise\nEvents\n", 1)
    require(len(parts) == 2 and parts[1].endswith(
        "TOTAL\n1584\nCore rule: contrast should sound new; return should sound remembered.\n"),
        "PDF module total/core rule drift")
    body = parts[1].split("TOTAL\n1584\n", 1)[0].splitlines()
    require(len(body) == 30, "PDF module table shape drift")
    result = []
    for n, (letter, title, count) in enumerate(MODULES):
        line = exact_line(lines, f"{letter}. {title} - {count} events")
        require(body[n*3:n*3+3] == [letter, title, str(count)],
                f"TXT/PDF module declaration mismatch: {letter}")
        result.append({"module": letter, "title": title, "declared_events": count,
                       "txt_line": line, "pdf": {**page_ref(pages, 1, "Guitar Exercises - Section XV, Level 101"),
                                                 "table_row": n+1}})
    require(sum(x["declared_events"] for x in result) == 1584, "module event sum differs")
    return result, total_line


def task(row: dict, key: str) -> dict:
    return {"local_key": key, **row, "declared_event_count_for_row": None,
            "canonical_id": None, "composed_notes": None, "motif_realization": None,
            "recorded_take": None, "duration": None, "performed_timing": None}


def build_from_source(source: dict) -> dict:
    lines, pages = source["txt"]["content"], source["pdf"]["content"]
    declarations_, total_line = declarations(lines, pages)
    modules = {x["module"]: {**x, "tasks": [], "per_task_event_counts_known": False,
                              "allocated_event_count": None} for x in declarations_}
    reference = parse_table(pages, 2, "Reference - Larger-Form Hierarchy", ("Layer", "Question"), 8,
                            "Write the section jobs before writing all the notes.")
    for page, letter, heading, columns, count, footer in TABLES:
        rows = parse_table(pages, page, heading, columns, count, footer)
        if page == 12:
            require([r["fields"]["Pass"] for r in rows] == [str(x) for x in range(1, 7)],
                    "Module E return-pass order drift")
        if page == 20:
            require([r["fields"]["Bars"] for r in rows] == ["1-8", "9-16", "17-24", "25-32"]
                    and [r["fields"]["Section"] for r in rows] == ["A", "B", "Bridge", "A'"],
                    "Module I 32-bar form coverage drift")
        for row in rows:
            modules[letter]["tasks"].append(task(row, f"L101-{letter}-p{page}-r{row['row_ordinal']}"))
    # p15 is visibly sparse: pypdf omits the blank Density/Register/Cadence cells.
    heading = "Module G - Section Energy Map"
    value = pages[14]
    prefix = heading + "\nSection\nEnergy 1-5\nDensity\nRegister\nCadence\n"
    footer = "The energy map must be legible even if all articulations are removed.\n"
    require(value.startswith(prefix) and value.endswith(footer), "Module G energy-map boundary drift")
    cells = value[len(prefix):-len(footer)].splitlines()
    require(cells == ["A", "2", "A'/B", "3", "Bridge/Peak", "4-5", "Return/Release", "2-4"],
            "Module G sparse energy-map cells drift")
    for n in range(4):
        row = {"row_ordinal": n+1,
               "fields": {"Section": cells[n*2], "Energy 1-5": cells[n*2+1],
                          "Density": None, "Register": None, "Cadence": None},
               "source": {**page_ref(pages, 15, heading), "row_ordinal": n+1},
               "blank_cells_verified_from_render": True}
        modules["G"]["tasks"].append(task(row, f"L101-G-p15-r{n+1}"))
    studies = []
    for study, page, suffix in [(1, 16, "A/B instrumental"), (2, 17, "Verse/chorus"),
                                (3, 18, "A-B-Bridge-A"), (4, 19, "4-section arc")]:
        heading = f"Module H - Study {study} - {suffix}"
        value = pages[page-1]
        require(value.startswith(heading + "\n") and value.count("Pass\nRequirement\n") == 1,
                f"Module H study boundary drift: {study}")
        before, after = value.split("Pass\nRequirement\n", 1)
        instruction = before[len(heading)+1:].strip()
        fields = after.strip().splitlines()
        require(instruction and len(fields) == 12 and fields[0::2] == [str(x) for x in range(1, 7)],
                f"Module H study pass drift: {study}")
        studies.append({"study": study, "title": suffix, "printed_instruction": instruction,
                        "source": page_ref(pages, page, heading)})
        for n in range(6):
            row = {"row_ordinal": n+1, "study": study, "printed_instruction": instruction,
                   "fields": {"Pass": fields[n*2], "Requirement": fields[n*2+1]},
                   "source": {**page_ref(pages, page, heading), "row_ordinal": n+1}}
            modules["H"]["tasks"].append(task(row, f"L101-H-study{study}-pass{n+1}"))
    require(exact_line(lines, "KEY SKILLS") == 24 and exact_line(lines, "CAPSTONE") == 36,
            "TXT key-skill/capstone section drift")
    skills = [{"txt_line": n, "text": lines[n-1][2:]} for n in range(25, 35)]
    require(all(lines[n-1].startswith("- ") for n in range(25, 35)), "TXT key-skill list drift")
    capstone_lines = [(n, lines[n-1]) for n in range(37, 45) if lines[n-1]]
    require([text for _, text in capstone_lines[:5]] ==
            ["One complete 32-bar original:", "A 8 bars", "B 8 bars", "Bridge 8 bars", "A' 8 bars"],
            "TXT capstone form drift")
    txt_deliverables = lines[43]
    pdf_deliverables = pages[19].split("Required deliverables: ", 1)[1].strip()
    require(txt_deliverables.startswith("working title, form map, motif, harmony/function chart")
            and "motif statement, chord/function chart" in pdf_deliverables
            and txt_deliverables != pdf_deliverables,
            "TXT/PDF capstone wording relationship drift")
    mastery_line = exact_line(lines, "14/16 or better.")
    zero_line = exact_line(lines, "No zero in identity, form, thematic return, or performance.")
    next_line = exact_line(lines, "Level 102: arrangement and orchestration for original music.")
    task_count = sum(len(m["tasks"]) for m in modules.values())
    require(task_count == 118, f"whole Level101 task-row coverage differs: {task_count}")
    return {"wbs": "2.3.1.3.1", "level": 101, "section": "XV",
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
            "supporting_reference": {"page": 2, "rows": reference, "relation": "section-job guidance"},
            "h_studies": studies, "declared_total_events": 1584,
            "txt_total_anchor_line": total_line, "extracted_task_rows": task_count,
            "key_skills": skills, "capstone_txt_lines": capstone_lines,
            "capstone_deliverables": {"txt": txt_deliverables, "pdf": pdf_deliverables,
                                        "wording_equivalence_review": "Pending"},
            "mastery": {"txt_lines": [mastery_line, zero_line], "pdf": page_ref(pages, 21, "Module J - Revision, Reduction, and Authorship Audit"),
                        "minimum": "14/16 or better", "protected_zero_domains":
                        ["identity", "form", "thematic return", "performance"]},
            "next_level_source_line": next_line,
            "unresolved": {"event_distribution_to_tasks": "all 1584 declared events lack printed row allocation",
                           "per_task_event_counts": None, "composed_notes_and_motifs": None,
                           "density_register_cadence_energy_map_cells": None,
                           "recorded_take": None, "performed_timing": None,
                           "txt_pdf_capstone_wording_equivalence": "Pending",
                           "canonical_identity": None, "runtime_admission": False}}


def build(root: Path = ROOT) -> dict:
    return build_from_source(read_source(root))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(BUILD.resolve()):
        parser.error("output must remain under Build/parallel-06/2.3-level101-whole-semantic-r01")
    payload = build()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    print(f"PASS: {len(payload['modules'])} modules, {payload['extracted_task_rows']} task rows, "
          f"{len(payload['supporting_reference']['rows'])} reference rows, {payload['declared_total_events']} unallocated events")


if __name__ == "__main__":
    main()
