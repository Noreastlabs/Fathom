#!/usr/bin/env python3
"""Build a detached, source-reconciled Level 35 horizontal-lane candidate."""

from __future__ import annotations

import argparse
import csv
import hashlib
from io import BytesIO
import json
from pathlib import Path
import re
import subprocess

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
STEM = "Scale_Exercises_Section_IV_Level_35_Major_Pentatonic_Horizontal_String_Lanes_Controlled_Shifts_Slides_and_Destination_Landings_Fixed_Key_A"
TXT_REL = Path(f"Notes/music/guitar project/TXT version/{STEM}.txt")
PDF_REL = Path(f"Notes/music/guitar project/PDF version/{STEM}.pdf")
MAP_REL = Path("Results/parallel-01/exercises/inventory/20260922T180500Z-2.3-curriculum-v1-source-inventory-evidence/curriculum-source-map.tsv")
BUILD_REL = Path("Build/parallel-08/2.3.1.1.1-level035-whole-r01")
PINS = {"txt": (17788, "4a6d7e608e4217a832e72ed6b17526f75567fddc82f8018f40bf96f868d6b684"),
        "pdf": (37209, "90625b12ffac1d51d085f3b95cc12917fa2e6825f8137a83fec28d5ba468ea29"),
        "map": (68536, "f526ff4d9ce3bceaf9a7cc581a3ac2aee2c74917eba984dd57913adba574c123")}
STRINGS = ("E", "A", "D", "G", "B", "e")
LANE_NAMES = ("LOW E", "A", "D", "G", "B", "HIGH E")
FRETS = ((5, 7, 9, 12, 14, 17), (4, 7, 9, 12, 14, 16),
         (4, 7, 9, 11, 14, 16), (4, 6, 9, 11, 14, 16),
         (5, 7, 10, 12, 14, 17), (5, 7, 9, 12, 14, 17))
DEGREES = ((1, 2, 3, 5, 6, 1), (3, 5, 6, 1, 2, 3),
           (6, 1, 2, 3, 5, 6), (2, 3, 5, 6, 1, 2),
           (5, 6, 1, 2, 3, 5), (1, 2, 3, 5, 6, 1))
FINGERS = ((1, 3, 1, 4, 1, 4), (1, 4, 1, 4, 1, 3),
           (1, 4, 1, 3, 1, 3), (1, 3, 1, 3, 1, 3),
           (1, 3, 1, 3, 1, 4), (1, 3, 1, 4, 1, 4))
NOTE_FOR_DEGREE = {1: "A", 2: "B", 3: "C#", 5: "E", 6: "F#"}
PITCH_CLASS = {"A": 9, "B": 11, "C#": 1, "E": 4, "F#": 6}
OPEN_PITCH_CLASS = {"E": 4, "A": 9, "D": 2, "G": 7, "B": 11, "e": 4}
TAB_ORDER = ("e", "B", "G", "D", "A", "E")
COUNTS = {"A": (72, 72), "B": (144, 96), "C": (96, 96), "D": (72, 72)}


class CandidateError(ValueError):
    """Pinned source, structure or output boundary failed."""


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify(data: bytes, kind: str) -> None:
    size, sha = PINS[kind]
    if len(data) != size or digest(data) != sha:
        raise CandidateError(f"PINNED_INPUT_DRIFT {kind}: bytes={len(data)} sha256={digest(data)}")


def source_bytes(root: Path, rel: Path) -> bytes:
    path = root / rel
    if path.is_symlink() or not path.is_file() or path.resolve().parent != path.parent.resolve():
        raise CandidateError(f"SOURCE_PATH_INVALID {rel}")
    return path.read_bytes()


def tokens(row: str, label: str, count: int) -> list[str]:
    if not row.startswith(label + "|"):
        raise CandidateError(f"ROW_LABEL_MISMATCH {label}: {row}")
    values = re.findall(r"C#|F#|[A-G]|\d+", row.split("|", 1)[1])
    if len(values) != count:
        raise CandidateError(f"ROW_COUNT_MISMATCH {label}: {len(values)} != {count}")
    return values


def note(string: str, fret: int, degree: int, name: str, *, finger: int | None = None,
         picked: bool = True, articulation: str = "picked") -> dict:
    if NOTE_FOR_DEGREE.get(degree) != name or (OPEN_PITCH_CLASS[string] + fret) % 12 != PITCH_CLASS[name]:
        raise CandidateError(f"PITCH_OR_DEGREE_MISMATCH {string}{fret} {name}({degree})")
    return {"string": string, "fret": fret, "degree": degree, "note": name,
            "finger": finger, "pick_attack": picked, "articulation": articulation,
            "onset_q": None, "duration_q": None}


def lane_expected(index: int, positions: list[int], *, fingers: list[int] | None = None,
                  picked: list[bool] | None = None, articulations: list[str] | None = None) -> list[dict]:
    out = []
    for ordinal, position in enumerate(positions):
        degree = DEGREES[index][position]
        out.append(note(STRINGS[index], FRETS[index][position], degree, NOTE_FOR_DEGREE[degree],
                        finger=None if fingers is None else fingers[ordinal],
                        picked=True if picked is None else picked[ordinal],
                        articulation="picked" if articulations is None else articulations[ordinal]))
    return out


def assert_rows(rows: list[str], expected: list[dict], string: str, *, with_finger: bool = False,
                with_pick: bool = False) -> None:
    names = tokens(rows[0], "Nte", len(expected))
    degrees = [int(v) for v in tokens(rows[1], "Deg", len(expected))]
    offset = 2
    fingers = None
    if with_finger:
        fingers = [int(v) for v in tokens(rows[2], "Fng", len(expected))]
        offset = 3
    if with_pick:
        if not rows[-1].startswith("Pck|") or re.findall(r"[DU]", rows[-1].split("|", 1)[1]) != ["D", "U"] * (len(expected) // 2):
            raise CandidateError("PRINTED_PICK_ROW_MISMATCH")
    tab = rows[offset]
    if not tab.startswith(f"{string}  |"):
        raise CandidateError(f"TAB_LABEL_MISMATCH {string}: {tab}")
    frets = [int(v) for v in tokens(tab, f"{string}  ", len(expected))]
    for ordinal, event in enumerate(expected):
        actual = (names[ordinal], degrees[ordinal], frets[ordinal], None if fingers is None else fingers[ordinal])
        wanted = (event["note"], event["degree"], event["fret"], event["finger"] if with_finger else None)
        if actual != wanted:
            raise CandidateError(f"PRINTED_EVENT_MISMATCH {string} note={ordinal+1}: {actual} != {wanted}")


def pdf_rows(page: list[str], heading: str, rows: list[str], *, prefix: str = "") -> str:
    try:
        start = next(i for i, line in enumerate(page) if line.lower().startswith(heading.lower()))
    except StopIteration as exc:
        raise CandidateError(f"PDF_CARD_MISSING {heading}") from exc
    for row in rows:
        if row not in page[start:]:
            raise CandidateError(f"PDF_PRINTED_ROW_MISMATCH {heading}: {row}")
    return prefix


def parse_a(lines: list[str], pages: list[list[str]]) -> list[dict]:
    cells = []
    for index, name in enumerate(LANE_NAMES):
        heading = f"{name} STRING - 12-NOTE UP/DOWN CELL"
        start = lines.index(heading)
        block = lines[start:start+12]
        string = STRINGS[index]
        positions = list(range(6)) + list(range(5, -1, -1))
        expected = lane_expected(index, positions, fingers=[FINGERS[index][p] for p in positions])
        rows = [block[2], block[3], block[4], block[5+TAB_ORDER.index(string)]]
        assert_rows(rows, expected, string, with_finger=True)
        for row_string in TAB_ORDER:
            row = block[5+TAB_ORDER.index(row_string)]
            if row_string != string and re.search(r"\d", row):
                raise CandidateError(f"MODULE_A_CROSS_STRING_TAB {name}")
        station = "Stations: " + " | ".join(f"{FRETS[index][j]}-{FRETS[index][j+1]}" for j in (0, 2, 4))
        if block[1] != station or not block[11].startswith("Rule: finish on the lower endpoint"):
            raise CandidateError(f"MODULE_A_STATION_OR_RULE {name}")
        page_number = 3 + index // 2
        page = pages[page_number-1]
        pdf_rows(page, f"{name.lower()} string - 12-note silent-shift cell", block[2:11])
        if not any(line.startswith(station) for line in page):
            raise CandidateError(f"PDF_MODULE_A_STATION {name}")
        cells.append({"lane": string, "source_txt_lines": [start+1, start+12], "source_pdf_page": page_number,
                      "stations": [list(FRETS[index][j:j+2]) for j in (0, 2, 4)],
                      "silent_shift_after_note_ordinals": [2, 4, 8, 10], "no_slide": True,
                      "printed": block, "events": expected})
    return cells


def parse_b(lines: list[str], pages: list[list[str]]) -> list[dict]:
    phrases = []
    for seam in range(4):
        heading = f"SEAM P{seam+1} -> P{seam+2}"
        start = lines.index(heading)
        if not lines[start+1].startswith("String tab") or not lines[start+8].startswith("Timing rule:"):
            raise CandidateError(f"MODULE_B_BOUNDARY {heading}")
        page_number = 6 + seam // 2
        page = pages[page_number-1]
        pdf_heading = f"Seam P{seam+1} -> P{seam+2}:"
        pdf_start = next((i for i, line in enumerate(page) if line.startswith(pdf_heading)), None)
        if pdf_start is None:
            raise CandidateError(f"PDF_MODULE_B_SEAM_MISSING {heading}")
        for index, string in enumerate(STRINGS):
            raw = lines[start+2+index]
            match = re.fullmatch(r"([EADGBe]\|[^|]+\|)\s+([\d/\\-]+)\s+([A-F#\\/\-]+)\s+([34])\s+(A|B|C#|E|F#) \(([12356])\) fret (\d+)", raw)
            if match is None:
                raise CandidateError(f"MODULE_B_ROW_FORMAT {heading} {string}: {raw}")
            tab, deg_path, name_path, finger, target_name, target_degree, target_fret = match.groups()
            if not tab.startswith(string + "|"):
                raise CandidateError(f"MODULE_B_STRING_ORDER {heading} {string}")
            positions = [seam, seam+1, seam+2, seam+2, seam+1, seam]
            expected = lane_expected(index, positions, picked=[True, True, False, True, False, True],
                                     articulations=["picked", "picked", "slide_up_arrival", "picked", "slide_down_arrival", "picked"])
            frets = [int(v) for v in re.findall(r"\d+", tab)]
            degrees = [int(v) for v in re.findall(r"\d+", deg_path)]
            names = re.findall(r"C#|F#|[ABE]", name_path)
            if (frets, degrees, names) != ([e["fret"] for e in expected], [e["degree"] for e in expected], [e["note"] for e in expected]):
                raise CandidateError(f"MODULE_B_PATH_MISMATCH {heading} {string}")
            if (tab != f"{string}|{frets[0]}--{frets[1]}/{frets[2]}--{frets[3]}\\{frets[4]}--{frets[5]}--|"
                    or deg_path != f"{degrees[0]}-{degrees[1]}/{degrees[2]}-{degrees[3]}\\{degrees[4]}-{degrees[5]}"
                    or name_path != f"{names[0]}-{names[1]}/{names[2]}-{names[3]}\\{names[4]}-{names[5]}"):
                raise CandidateError(f"MODULE_B_SLIDE_GLYPHS {heading} {string}")
            gap = expected[2]["fret"] - expected[1]["fret"]
            if gap not in (2, 3) or int(finger) != (3 if gap == 2 else 4):
                raise CandidateError(f"MODULE_B_SLIDE_FINGER {heading} {string}")
            if (target_name, int(target_degree), int(target_fret)) != (expected[2]["note"], expected[2]["degree"], expected[2]["fret"]):
                raise CandidateError(f"MODULE_B_DESTINATION {heading} {string}")
            pdf_block = page[pdf_start+7+5*index:pdf_start+12+5*index]
            if pdf_block != [tab, deg_path, name_path, finger, f"{target_name} ({target_degree}) fret {target_fret}"]:
                raise CandidateError(f"PDF_MODULE_B_ROW_MISMATCH {heading} {string}")
            phrases.append({"seam": heading.removeprefix("SEAM "), "lane": string,
                            "source_txt_line": start+3+index, "source_pdf_page": page_number,
                            "slide_finger": int(finger), "destination": {"note": target_name, "degree": int(target_degree), "fret": int(target_fret)},
                            "printed": {"tab": tab, "degree_path": deg_path, "note_path": name_path, "row": raw},
                            "events": expected, "slide_arrival_ordinals": [3, 5], "pick_attack_ordinals": [1, 2, 4, 6]})
        if not any("slide destination must arrive on the subdivision" in line for line in page):
            raise CandidateError(f"PDF_MODULE_B_TIMING {heading}")
    return phrases


def parse_c(lines: list[str], pages: list[list[str]]) -> list[dict]:
    ladders = []
    for index, name in enumerate(LANE_NAMES):
        string = STRINGS[index]
        heading = f"{name} STRING - LAUNCH {NOTE_FOR_DEGREE[DEGREES[index][0]]}({DEGREES[index][0]}) FRET {FRETS[index][0]}"
        start = lines.index(heading)
        block = lines[start:start+6]
        positions = [p for target in range(2, 6) for p in (0, target, target, 0)]
        expected = lane_expected(index, positions, fingers=[1]*16)
        assert_rows(block[1:5], expected, string, with_pick=True)
        targets = []
        for p in range(2, 6):
            degree = DEGREES[index][p]
            targets.append({"note": NOTE_FOR_DEGREE[degree], "degree": degree, "fret": FRETS[index][p],
                            "distance_frets": FRETS[index][p]-FRETS[index][0]})
        expected_targets = "Targets: " + " | ".join(f"{t['note']} degree {t['degree']} fret {t['fret']} ({t['distance_frets']} frets)" for t in targets)
        if block[5] != expected_targets:
            raise CandidateError(f"MODULE_C_TARGETS {name}")
        page_number = 8 + index // 2
        page = pages[page_number-1]
        pdf_heading = f"{name.lower()} string - four-distance destination ladder"
        pdf_start = next((i for i, line in enumerate(page) if line.lower() == pdf_heading), None)
        if pdf_start is None or page[pdf_start+2:pdf_start+6] != block[1:5]:
            raise CandidateError(f"PDF_MODULE_C_ROWS {name}")
        if page[pdf_start+1] != f"Launch: {expected[0]['note']} degree {expected[0]['degree']} at fret {expected[0]['fret']}. First pass: finger 1 on every note; no slide or scrape.":
            raise CandidateError(f"PDF_MODULE_C_LAUNCH {name}")
        for j, target in enumerate(targets):
            if page[pdf_start+10+4*j:pdf_start+14+4*j] != [target["note"], str(target["fret"]), str(target["degree"]), f"{target['distance_frets']} frets"]:
                raise CandidateError(f"PDF_MODULE_C_TARGET {name} {j+1}")
        ladders.append({"lane": string, "source_txt_lines": [start+1, start+6], "source_pdf_page": page_number,
                        "launch": expected[0], "targets": targets, "first_pass_finger": 1, "no_slide": True,
                        "upper_endpoint_mirror": "instruction_only", "printed": block, "events": expected})
    return ladders


def parse_d(lines: list[str], pages: list[list[str]]) -> list[dict]:
    out = []
    routes = (("forward", [0, 1, 2, 3, 4, 5], [True, False, True, False, True, False], 11),
              ("reverse", [5, 4, 3, 2, 1, 0], [True, False, True, False, True, False], 12))
    for route, lane_order, directions, page_number in routes:
        page = pages[page_number-1]
        for ordinal, (index, ascending) in enumerate(zip(lane_order, directions, strict=True), 1):
            heading = f"{ordinal}. {('Low E' if index == 0 else 'High e' if index == 5 else LANE_NAMES[index])} {'ASC' if ascending else 'DESC'}"
            start = lines.index(heading)
            block = lines[start:start+5]
            positions = list(range(6)) if ascending else list(range(5, -1, -1))
            expected = lane_expected(index, positions, fingers=[FINGERS[index][p] for p in positions])
            assert_rows(block[1:5], expected, STRINGS[index], with_finger=True)
            pdf_start = 6 + 6*(ordinal-1)
            if not page[pdf_start].startswith(heading) or page[pdf_start+1:pdf_start+5] != block[1:5]:
                raise CandidateError(f"PDF_MODULE_D_SEGMENT {route} {ordinal}")
            out.append({"route": route, "segment": ordinal, "lane": STRINGS[index], "direction": "asc" if ascending else "desc",
                        "source_txt_lines": [start+1, start+5], "source_pdf_page": page_number,
                        "printed": block, "events": expected})
    forward, reverse = out[:6], out[6:]
    transitions = "Transitions: " + " | ".join(f"{a['events'][-1]['string']}{a['events'][-1]['fret']}/{b['events'][0]['string']}{b['events'][0]['fret']}" for a, b in zip(forward, forward[1:]))
    if transitions not in lines or not pages[10][5].startswith(transitions):
        raise CandidateError("MODULE_D_FORWARD_TRANSITIONS")
    if (forward[-1]["events"][-1]["string"], forward[-1]["events"][-1]["fret"]) != ("e", 5) or reverse[0]["events"][0]["fret"] != 5:
        raise CandidateError("MODULE_D_TURN_REPEAT")
    return out


def build_candidate(root: Path = ROOT) -> dict:
    if root.resolve() != ROOT.resolve():
        raise CandidateError("REPOSITORY_ROOT_MISMATCH")
    proc = subprocess.run(["git", "-C", str(root), "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if proc.returncode or Path(proc.stdout.strip()).resolve() != root.resolve():
        raise CandidateError("REPOSITORY_ROOT_MISMATCH")
    inputs = {kind: source_bytes(root, rel) for kind, rel in (("txt", TXT_REL), ("pdf", PDF_REL), ("map", MAP_REL))}
    for kind, data in inputs.items():
        verify(data, kind)
    source_map = list(csv.DictReader(inputs["map"].decode("utf-8").splitlines(), delimiter="\t"))
    map_rows = [row for row in source_map if row["level"] == "35"]
    if len(map_rows) != 1:
        raise CandidateError("SOURCE_MAP_LEVEL35_CARDINALITY")
    map_row = map_rows[0]
    if (map_row["txt_path"] != str(TXT_REL) or map_row["pdf_path"] != str(PDF_REL)
            or map_row["txt_sha256"] != PINS["txt"][1] or map_row["pdf_sha256"] != PINS["pdf"][1]
            or map_row["review"] != "Pending" or map_row["conversion_status"] != "not_converted"
            or any(map_row[key] != "False" for key in ("stable_ids_assigned", "runtime_eligible", "imported", "admitted"))):
        raise CandidateError("SOURCE_MAP_LEVEL35_STATE")
    lines = inputs["txt"].decode("utf-8").splitlines()
    if len(lines) != 333 or lines[:2] != ["SCALE EXERCISES - SECTION IV, LEVEL 35", "A MAJOR PENTATONIC HORIZONTAL STRING LANES - CONTROLLED SHIFTS, SLIDES, AND DESTINATION LANDINGS"]:
        raise CandidateError("TXT_HEADER_OR_LENGTH")
    reader = PdfReader(BytesIO(inputs["pdf"]), strict=True)
    if len(reader.pages) != 13:
        raise CandidateError("PDF_PAGE_COUNT")
    pages = [(p.extract_text() or "").splitlines() for p in reader.pages]
    if any(f"Page {i} of 13" not in page for i, page in enumerate(pages, 1)):
        raise CandidateError("PDF_PAGE_IDENTITY")
    if "A major pentatonic" not in "\n".join(line for page in pages[:2] for line in page):
        raise CandidateError("PDF_FIXED_KEY_IDENTITY")
    lanes = []
    for index, string in enumerate(STRINGS):
        props = [lane_expected(index, [p])[0] for p in range(6)]
        for p, item in enumerate(props):
            item["finger"] = FINGERS[index][p]
        atlas = pages[1][106+6*index:112+6*index]
        expected_atlas = ["Low E" if index == 0 else "High e" if index == 5 else string,
                          " ".join(str(fret) for fret in FRETS[index]),
                          " ".join(str(degree) for degree in DEGREES[index]),
                          " ".join(NOTE_FOR_DEGREE[degree] for degree in DEGREES[index]),
                          " ".join(str(finger) for finger in FINGERS[index]),
                          ", ".join(str(e["fret"]) for e in props if e["degree"] == 1)]
        if atlas != expected_atlas:
            raise CandidateError(f"PDF_ATLAS_LANE_MISMATCH {string}")
        summary = next((line for line in lines[19:27] if line.startswith(expected_atlas[0] + " ")), None)
        if summary is None:
            raise CandidateError(f"TXT_LANE_SUMMARY_MISSING {string}")
        normalized = " ".join(summary.split())
        if any(part not in normalized for part in expected_atlas[1:5]) or "roots " + expected_atlas[5].replace(", ", ",") not in normalized:
            raise CandidateError(f"TXT_LANE_SUMMARY_MISMATCH {string}")
        lanes.append({"string": string, "name": LANE_NAMES[index], "positions": props,
                      "root_frets": [e["fret"] for e in props if e["degree"] == 1],
                      "printed_txt_summary": summary, "printed_pdf_atlas": atlas})
    a, b, c, d = parse_a(lines, pages), parse_b(lines, pages), parse_c(lines, pages), parse_d(lines, pages)
    modules = {"A": a, "B": b, "C": c, "D": d}
    actual = {key: (sum(len(item["events"]) for item in items), sum(sum(e["pick_attack"] for e in item["events"]) for item in items))
              for key, items in modules.items()}
    if actual != COUNTS:
        raise CandidateError(f"WHOLE_LEVEL_COUNTS {actual}")
    if sum(x[0] for x in actual.values()) != 384 or sum(x[1] for x in actual.values()) != 336:
        raise CandidateError("WHOLE_LEVEL_TOTALS")
    if len(a) != 6 or len(b) != 24 or len(c) != 6 or len(d) != 12:
        raise CandidateError("WHOLE_LEVEL_ITEM_COUNTS")
    if "384 sounding tones / 336 pick attacks" not in "\n".join(lines):
        raise CandidateError("TXT_PRINTED_TOTALS")
    if "24 seam-slide phrases" not in "\n".join(lines):
        raise CandidateError("TXT_MASTERY_GATE")
    guidance = {"txt": "\n".join(lines[294:]), "pdf": "\n".join(pages[12]),
                "picking": "\n".join(lines[31:38]), "module_a": "\n".join(lines[40:45]),
                "module_b": "\n".join(lines[125:130]), "module_c": "\n".join(lines[172:177]),
                "module_d": "\n".join(lines[221:227])}
    return {"schema": "fathom.detached.curriculum.level035.whole.v1", "wbs": "2.3.1.1.1",
            "level": 35, "key": "A major pentatonic", "transposed": False,
            "source": {label: {"path": str(rel), "bytes": len(inputs[kind]), "sha256": digest(inputs[kind])}
                       for label, kind, rel in (("txt", "txt", TXT_REL), ("pdf", "pdf", PDF_REL), ("source_map", "map", MAP_REL))},
            "canonical_id": None, "runtime_imported": False, "admitted": False,
            "whole_level_source_covered": True, "whole_level_complete": False,
            "lanes": lanes, "modules": modules, "module_counts": {k: {"sounding": v[0], "pick_attacks": v[1]} for k, v in actual.items()},
            "totals": {"sounding": 384, "pick_attacks": 336, "unpicked_slide_arrivals": 48},
            "picking": {"separate_starts": ["D", "U"], "strict_alternate": True, "continuous_across_boundaries": True,
                        "slide_arrival_new_pick_attack": False, "turn_repeated_high_e_fret": 5},
            "timing": {"numeric_onset": None, "numeric_duration": None, "fixed_bpm": None,
                       "slide_destination_on_subdivision": True},
            "guidance": guidance, "source_discrepancies": []}


def write_candidate(path: Path, root: Path = ROOT) -> str:
    allowed = (root / BUILD_REL).resolve()
    if path.is_symlink() or path.resolve().parent != allowed or path.suffix != ".json":
        raise CandidateError("OUTPUT_PATH_OUTSIDE_DETACHED_BUILD")
    if path.exists():
        raise CandidateError("OUTPUT_EXISTS")
    candidate = build_candidate(root)
    data = (json.dumps(candidate, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return digest(data)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(write_candidate(args.output))


if __name__ == "__main__":
    main()
