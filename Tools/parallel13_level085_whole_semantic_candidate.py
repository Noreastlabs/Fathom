#!/usr/bin/env python3
"""Expand pinned Level85 TXT/PDF and P03 structure index into detached semantic tasks."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader, __version__ as PYPDF_VERSION
import curriculum_level085_whole_source_candidate as index

ROOT = Path(__file__).resolve().parents[1]
OUT = Path("Build/parallel-13/level085-whole-semantic-r01")
STRUCTURE = Path("Build/parallel-03/2.3.1.3.1-level-085-whole-source-index-r01/candidate-a.json")
PINS = {
    STRUCTURE: "a43462c3da92c7e4156e507a1d7992e492872a4b7b10f1cd8a8d1f5fec56c64e",
    Path("Tools/curriculum_level085_whole_source_candidate.py"): "0849a12cf72f2dc16f37061b3841c33f2f4154d836b9775f8a64c129267b6669",
    Path("Results/parallel-03/exercises/conversion/20260923T155826Z-2.3.1.3.1-level085-whole-source-index-r01-results.md"): "935dc4ea6489c24e8f53150fa2f355ac72b5097333d2e4a795a7a333f61f802d",
    Path("Results/primary/20260912T100538Z-2.1.1.2.1-r02-evidence/schema-freeze.json"): "0659fa962a5c933a2bcf3045772b6fe5b05b4deefb3511f5dcb68af51088de95",
}
TABLES = {
    2: (None, "Reference - One Grid, Several Grooves", ("Name", "1 e & a 2 e & a 3 e & a 4 e & a", "Primary variable"), 6),
    3: ("A", "Module A - Subdivision-to-Groove Conversion", ("Pass", "Instruction"), 6),
    4: ("B", "Module B - Note-Length Ladder", ("Level", "Duration target", "Left-hand behavior"), 6),
    5: ("C", "Module C - Muting and Ghost Contacts", ("Pattern", "Grid", "Goal"), 6),
    6: ("D", "Module D - Locking to Kick and Snare", ("Study", "Guitar job", "Count"), 6),
    7: ("E", "Module E - Bass/Guitar Interlock", ("Bass figure", "Guitar response", "Rule"), 6),
    8: ("F", "Module F - Ahead, On, and Behind the Beat", ("Placement", "Practice cue", "Failure sign"), 4),
    9: ("G", "Module G - Eight Groove Cells, Same Harmonic Skills", ("Groove", "Progression", "Primary feel variable"), 8),
    10: ("H", "Module H - Study 1 - Rock pocket", ("Pass", "Requirement"), 6),
    11: ("H", "Module H - Study 2 - Funk pocket", ("Pass", "Requirement"), 6),
    12: ("H", "Module H - Study 3 - Offbeat pocket", ("Pass", "Requirement"), 6),
    13: ("H", "Module H - Study 4 - Soul pocket", ("Pass", "Requirement"), 6),
    14: ("I", "Module I - Thirty-Two-Bar Groove Capstone", index.I_HEADERS, 8),
    15: ("J", "Module J - Pocket Audit and Recovery", ("Failure", "Repair"), 8),
}
COUNTS = dict(zip("ABCDEFGHIJ", (6, 6, 6, 6, 6, 4, 8, 24, 8, 8)))
UNRESOLVED = [
    "1440 module workload events are not allocated to PDF task rows",
    "Module I's 256 events are not mapped to the eight printed four-bar ranges",
    "pitch-bound playable attacks, voicings and exact performed microtiming are unspecified",
    "canonical IDs, lineage, revision, Curriculum review and runtime admission pending",
]


class SourceError(ValueError):
    pass


def need(ok: bool, code: str) -> None:
    if not ok:
        raise SourceError(code)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def encoded(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def check_pins() -> None:
    for rel, expected in PINS.items():
        path = ROOT / rel
        need(path.is_file() and not path.is_symlink() and
             path.resolve().is_relative_to(ROOT.resolve()), f"INPUT_PATH {rel}")
        need(sha(path.read_bytes()) == expected, f"INPUT_PIN {rel}")


def foundation_status() -> None:
    package = json.loads((ROOT / index.CATALOG).read_text())
    entries = [e for e in package["workbook_catalog"]["entries"]
               if e["workbook_id"] == "fg:workbook:000085"]
    need(len(package["records"]) == 659 and len(entries) == 1 and
         not any(r.get("legacy_level") == 85 for r in package["records"]),
         "FOUNDATION_RECORDS")
    entry = entries[0]
    need(entry["conversion_status"] == "not_converted" and
         entry["representative_item_id"] is None and
         entry["whole_workbook_complete"] is False and
         entry["playable_projection"]["status"] == "explicitly_empty_unresolved" and
         all(entry[k] is False for k in
             ("admitted", "imported", "runtime_admitted", "runtime_eligible")),
         "FOUNDATION_ADMISSION")
    for kind, rel in (("txt", index.TXT), ("pdf", index.PDF)):
        value = entry[kind]
        size, digest = index.PINNED[rel]
        need((value["path"], value["bytes"], value["sha256"]) ==
             (rel, size, digest), f"FOUNDATION_SOURCE_{kind.upper()}")


def table_rows(text: str, page: int) -> tuple[list[dict], list[str], list[str]]:
    letter, heading, columns, count = TABLES[page]
    lines = text.splitlines()
    need(lines and lines[0] == heading, f"HEADING_p{page}")
    positions = [i for i in range(1, len(lines) - len(columns) + 1)
                 if tuple(lines[i:i + len(columns)]) == columns]
    need(len(positions) == 1, f"TABLE_HEADER_p{page}")
    start = positions[0] + len(columns)
    end = start + count * len(columns)
    need(end <= len(lines), f"TABLE_EXTENT_p{page}")
    raw_cells = lines[start:end]
    need(all(cell for cell in raw_cells), f"EMPTY_PRINTED_CELL_p{page}")
    rows = []
    for n in range(count):
        values = raw_cells[n * len(columns):(n + 1) * len(columns)]
        fields = dict(zip(columns, values))
        if page in (3, 10, 11, 12, 13):
            need(fields["Pass"] == str(n + 1), f"PASS_ORDER_p{page}")
        if page in (4, 5):
            need(values[0] == str(n + 1), f"ROW_ORDER_p{page}")
        row = {"row_ordinal": n + 1, "fields": fields,
               "source": {"pdf_page": page, "pdf_line_start": start + 1 + n * len(columns),
                          "pdf_line_end": start + (n + 1) * len(columns),
                          "pdf_extracted_text_sha256": sha(text.encode()),
                          "table_heading": heading},
               "declared_event_count_for_row": None,
               "canonical_id": None, "onset_q": None, "duration_q": None,
               "performed_result": None}
        rows.append(row)
    intro, closing = lines[1:positions[0]], lines[end:]
    need(len(intro) + len(closing) > 0, f"PAGE_CONTEXT_p{page}")
    return rows, intro, closing


def check_page_context(page: int, intro: list[str], closing: list[str], rows: list[dict]) -> None:
    if page == 2:
        need(len(intro) == 1 and intro[0].startswith("Maintain continuous sixteenth-note hand motion: D U D U.") and
             all(token in intro[0] for token in ("P = pitched contact", "x = muted contact",
                                                   "- = air stroke", "~ = sustain")) and
             not closing, "REFERENCE_LEGEND")
    elif page == 3:
        need(intro == ["Use one chord - Am7 - for every cell. Do not change harmony while learning the feel."] and
             len(closing) == 1 and "same metronome tempo" in closing[0], "A_FIXED_HARMONY_TEMPO")
    elif page == 4:
        need(len(intro) == 1 and "four quarter-note attacks per measure. Only duration changes." in intro[0] and
             len(closing) == 1 and "must not speed up" in closing[0], "B_DURATION_ONLY")
    elif page == 5:
        need(not intro and len(closing) == 1 and
             "A ghost contact may click but may not reveal a recognizable chord pitch." in closing[0],
             "C_GHOST_PITCH")
    elif page == 6:
        need(len(intro) == 1 and "kick on 1 and 3, snare on 2 and 4" in intro[0] and
             len(closing) == 1 and "metronome only on 2 and 4" in closing[0], "D_DRUM_GRID")
    elif page == 7:
        need(not intro and len(closing) == 1 and
             "Play the bass line yourself first" in closing[0], "E_BASS_SOURCE")
    elif page == 8:
        need(len(intro) == 1 and "microtiming, not a new subdivision" in intro[0] and
             len(closing) == 1 and "not by an exact millisecond target" in closing[0],
             "F_NO_MS_TARGET")
    elif page == 9:
        need(not intro and len(closing) == 1 and
             "not claims that each genre can be reduced to one pattern" in closing[0],
             "G_GENRE_LIMIT")
    elif page in (10, 11, 12, 13):
        need(len(intro) == 2 and intro[0].startswith("| ") and
             intro[0].endswith(" |") and len([x for x in intro[0].split("|") if x.strip()]) == 8 and
             bool(intro[1]) and not closing, f"H_STUDY_p{page}")
    elif page == 14:
        need(len(intro) == 1 and "without changing the underlying tempo" in intro[0] and
             "during beat 4 of the previous section" in intro[0] and
             len(closing) == 1 and all(f"Pass {n}:" in closing[0] for n in range(1, 6)) and
             "one uninterrupted 32-bar performance" in closing[0], "I_FORM_PASSES")
        actual = [tuple(row["fields"][key] for key in index.I_HEADERS) for row in rows]
        need(actual == list(index.EXPECTED_I_ROWS), "I_INDEX_PARITY")
    elif page == 15:
        full = " ".join(closing)
        need(not intro and len(rows) == 8 and
             "14/16 or better on two separate days" in full and
             "No zero in pulse, note length, muting, or recovery." in full and
             "HARD STOP after 105." in full, "J_MASTERY_HARD_STOP")


def semantics(page: int, row: dict, intro: list[str]) -> dict:
    f = row["fields"]
    if page == 2:
        return {"name": f["Name"], "grid_literal": f["1 e & a 2 e & a 3 e & a 4 e & a"],
                "primary_variable": f["Primary variable"], "pitched_attack_events": None}
    if page == 3:
        return {"pass": int(f["Pass"]), "instruction": f["Instruction"],
                "fixed_harmony": "Am7", "performed_pulse_consistency": None}
    if page == 4:
        return {"level": int(f["Level"]), "duration_target_literal": f["Duration target"],
                "left_hand_behavior": f["Left-hand behavior"], "quarter_attacks_per_measure": 4,
                "tempo_change": False, "performed_note_length": None}
    if page == 5:
        return {"pattern": int(f["Pattern"]), "grid_literal": f["Grid"],
                "goal": f["Goal"], "ghost_pitch_allowed": False,
                "pitched_attack_events": None}
    if page == 6:
        return {"study": f["Study"], "guitar_job": f["Guitar job"],
                "count_literal": f["Count"], "drum_grid": "kick 1/3; snare 2/4",
                "imagined_drum_part": True}
    if page == 7:
        return {"bass_figure": f["Bass figure"], "guitar_response": f["Guitar response"],
                "rule": f["Rule"], "recorded_bass_supplied": False}
    if page == 8:
        return {"placement": f["Placement"], "practice_cue": f["Practice cue"],
                "failure_sign": f["Failure sign"], "exact_millisecond_target": None,
                "performed_offset": None}
    if page == 9:
        return {"groove": f["Groove"], "progression_literal": f["Progression"],
                "primary_feel_variable": f["Primary feel variable"],
                "complete_genre_definition": False}
    if page in (10, 11, 12, 13):
        chords = [x.strip() for x in intro[0].split("|") if x.strip()]
        return {"study": page - 9, "harmony_bars_literal": chords,
                "focus": intro[1], "pass": int(f["Pass"]),
                "requirement": f["Requirement"], "performed_study": None}
    if page == 14:
        first, last = map(int, f["Bars"].split("-"))
        return {"bar_start": first, "bar_end": last,
                "harmony_literal": f["Harmony"], "groove": f["Groove"],
                "dynamic_literal": f["Dynamic"], "register_literal": f["Register"],
                "declared_events_for_range": None, "performed_range": None}
    return {"failure": f["Failure"], "repair": f["Repair"],
            "observed_failure": None, "performed_recovery": None}


def parse_pages(pages: list[str], structure: dict) -> tuple[list[dict], list[dict], list[dict]]:
    need(len(pages) == 15, "PDF_PAGE_COUNT")
    expected_hashes = [x["literal_extracted_text_sha256"] for x in structure["pdf"]["pages"]]
    need([sha(text.encode()) for text in pages] == expected_hashes, "PDF_INDEX_PAGE_HASH_DRIFT")
    modules = {letter: {"module": letter, "title": title, "declared_events": count,
                        "txt_line": structure["txt"]["modules"][n]["txt_line_number"],
                        "tasks": [], "per_task_event_counts_known": False,
                        "allocated_event_count": None}
               for n, (letter, title, count) in enumerate(index.EXPECTED_MODULES)}
    reference, contexts = [], []
    for page in range(2, 16):
        letter, heading, _, count = TABLES[page]
        rows, intro, closing = table_rows(pages[page - 1], page)
        need(len(rows) == count, f"ROW_COUNT_p{page}")
        check_page_context(page, intro, closing, rows)
        contexts.append({"page": page, "heading": heading, "intro": intro,
                         "closing": closing, "extracted_text_sha256": sha(pages[page - 1].encode())})
        for row in rows:
            row["semantic"] = semantics(page, row, intro)
            if letter is None:
                row["local_key"] = f"L85-reference-p2-r{row['row_ordinal']}"
                row["relation"] = "adjacent_unassigned_groove_reference"
                reference.append(row)
            else:
                n = len(modules[letter]["tasks"]) + 1
                row["local_key"] = f"L85-{letter}-{n:02d}"
                row["source"]["txt_module_line"] = modules[letter]["txt_line"]
                modules[letter]["tasks"].append(row)
    result = list(modules.values())
    need({m["module"]: len(m["tasks"]) for m in result} == COUNTS and
         sum(m["declared_events"] for m in result) == 1440 and
         len(reference) == 6, "WHOLE_COVERAGE")
    return result, reference, contexts


def build() -> dict:
    check_pins()
    foundation_status()
    replayed = index.build_candidate(ROOT)
    structure = json.loads((ROOT / STRUCTURE).read_text())
    need(structure == replayed, "STRUCTURE_REPLAY_DRIFT")
    need(structure["level"] == 85 and structure["section"] == "XII" and
         structure["wbs_id"] == "2.3.1.3.1" and
         structure["candidate_status"] == "pending_source_reconciliation" and
         structure["runtime_eligible"] is False and structure["admitted"] is False and
         structure["canonical_ids_allocated"] is False and
         structure["pdf"]["i_capstone_table"]["event_mapping"] is None,
         "STRUCTURE_SCOPE")
    need(PYPDF_VERSION == "6.10.0", "PDF_EXTRACTOR_VERSION")
    raw_txt = index.read_pinned(ROOT, index.TXT)
    raw_pdf = index.read_pinned(ROOT, index.PDF)
    pages = [page.extract_text() or "" for page in PdfReader(BytesIO(raw_pdf)).pages]
    modules, reference, contexts = parse_pages(pages, structure)
    need([x["literal"] for x in structure["txt"]["literal_lines"]] ==
         raw_txt.decode("utf-8").splitlines(), "TXT_INDEX_REPLAY_DRIFT")
    return {
        "schema": "fathom.detached.curriculum.level085.whole-semantic.r01",
        "wbs": "2.3.1.3.1", "level": 85, "section": "XII",
        "status": "detached_semantic_source_candidate_pending_curriculum_and_admission",
        "source_index": {"path": str(STRUCTURE), "sha256": PINS[STRUCTURE]},
        "source_identities": {"txt": {"path": index.TXT, "bytes": len(raw_txt),
                                      "sha256": sha(raw_txt)},
                              "pdf": {"path": index.PDF, "bytes": len(raw_pdf),
                                      "sha256": sha(raw_pdf)}},
        "txt_lines": structure["txt"]["literal_lines"],
        "pdf_pages": [{"page": n, "extracted_text_sha256": sha(text.encode()),
                       "extracted_text": text} for n, text in enumerate(pages, 1)],
        "module_order": list("ABCDEFGHIJ"), "modules": modules,
        "reference_rows": reference, "page_context": contexts,
        "declared_total_events": 1440, "module_task_row_count": 82,
        "reference_row_count": 6,
        "symbol_legend": {"P": "pitched contact", "x": "muted contact",
                          "-": "air stroke", "~": "sustain"},
        "continuous_hand_motion": "D U D U sixteenths",
        "capstone": {"bar_count": 32, "groove_environment_count": 8,
                     "one_underlying_tempo": True,
                     "beat_four_announcement_required": True,
                     "printed_module_events": 256,
                     "per_four_bar_row_event_counts": None,
                     "performed_timing": None},
        "mastery": {"minimum": "14/16 or better on two separate days",
                    "protected_zero_domains": ["pulse", "note length", "muting", "recovery"],
                    "observed_score": None,
                    "source_pdf_page": 15, "source_txt_lines": [36, 37]},
        "unresolved": UNRESOLVED,
        "canonical_ids_allocated": False, "schema1_imported": False,
        "whole_workbook_accepted": False, "runtime_eligible": False,
        "playable_event_count": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("build", "verify"))
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    need(output.is_relative_to((ROOT / OUT).resolve()), "OUTPUT_SCOPE")
    payload = encoded(build())
    if args.mode == "build":
        need(not output.exists(), "OUTPUT_EXISTS")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(payload)
    else:
        need(output.is_file() and output.read_bytes() == payload, "CANDIDATE_DRIFT")
    print("PASS: Level85 whole semantic; 82 module rows, 6 references, "
          "1440 unallocated module events, zero playable events")


if __name__ == "__main__":
    main()
