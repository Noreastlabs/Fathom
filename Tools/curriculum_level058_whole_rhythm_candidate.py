#!/usr/bin/env python3
"""Detached whole-Level58 rhythm source candidate with explicit contact-count conflict."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from pypdf import PdfReader


STEM = "Guitar_Exercises_Section_VI_Level_58_Sixteenth_Note_Rhythm_Guitar_Syncopation_Dead_Strokes_Chord_Releases_Anticipations_Funk_Comping_and_Full_Song_Capstone"
TXT_REL = f"Notes/music/guitar project/TXT version/{STEM}.txt"
PDF_REL = f"Notes/music/guitar project/PDF version/{STEM}.pdf"
TXT_SIZE, TXT_SHA = 18083, "e0c153f77a6c917056b7f17c876b2431336b40cb93bf484708230296b472acd4"
PDF_SIZE, PDF_SHA = 53179, "fcc609ccb4b13f52fde57ca95d7727db8acb351e07f0fe39ea08b0774ad501b5"
MAP_REL = "Results/parallel-01/exercises/inventory/20260922T180500Z-2.3-curriculum-v1-source-inventory-evidence/curriculum-source-map.json"
MAP_SIZE, MAP_SHA = 199753, "bad5581a04f43ba8baf14db430449e1ccff5cf88f0f7e42198328073b27053d6"
P01_REL = "Tools/curriculum_level058_masks_candidate.py"
P01_RESULT = "Results/parallel-01/exercises/conversion/20260923T112002Z-2.3.1.2.1-level058-modulea-masks-r02-results.md"
MODULE_COUNTS = {"A": 128, "B": 84, "C": 40, "D": 43, "E": 142, "F": 68, "G": 188, "H": 116, "I": 209}
MODULE_UNITS = {"A": 15, "B": 8, "C": 8, "D": 8, "E": 12, "F": 6, "G": 6, "H": 4, "I": 7}
MODULE_PAGES = {"A": (3, 4), "B": (5,), "C": (6, 7), "D": (8,), "E": (9, 10), "F": (11, 12), "G": (13, 14), "H": (15,), "I": (16, 17, 18, 19)}
STRINGS = ("E", "A", "D", "G", "B", "e")


def _pin(path: Path, size: int, sha: str) -> bytes:
    raw = path.read_bytes()
    if len(raw) != size or hashlib.sha256(raw).hexdigest() != sha:
        raise ValueError(f"source identity drift: {path}")
    return raw


def _source_map(root: Path) -> dict:
    row = json.loads(_pin(root / MAP_REL, MAP_SIZE, MAP_SHA))["rows"][57]
    expected = {"level": 58, "section": "VI", "wbs_owner": "2.3.1.2.1", "txt_path": TXT_REL, "txt_bytes": TXT_SIZE, "txt_sha256": TXT_SHA, "pdf_path": PDF_REL, "pdf_bytes": PDF_SIZE, "pdf_sha256": PDF_SHA, "pair_status": "exact_stem_pair", "representative_status": "frozen_representative_record", "representative_item_id": "fg:item:000009", "conversion_status": "converted_candidate_reference", "stable_ids_assigned": True, "review": "Pending", "runtime_eligible": False, "imported": False, "admitted": False}
    if any(row.get(k) != v for k, v in expected.items()):
        raise ValueError("Level58 source-map identity/status drift")
    return row


def _bounds(lines: list[str]) -> dict[str, tuple[int, int]]:
    heads = [(m.group(1), i) for i, s in enumerate(lines) if (m := re.match(r"MODULE ([A-I]) - ", s))]
    if [x[0] for x in heads] != list("ABCDEFGHI"):
        raise ValueError("module heading/order drift")
    end = next(i for i, s in enumerate(lines) if s == "PRACTICE PROGRESSION AND MASTERY")
    return {name: (start, heads[n + 1][1] if n < 8 else end) for n, (name, start) in enumerate(heads)}


def _pdf_has(pages: list[str], page: int, row: str, label: str) -> None:
    if row not in pages[page - 1]:
        raise ValueError(f"TXT/PDF {label} mismatch p{page}: {row!r}")


def _groups(row: str, label: str, bars: int) -> list[str]:
    if not row.startswith(label + "|") or not row.endswith("|"):
        raise ValueError(f"{label} row syntax drift: {row!r}")
    parts = [p for p in row.split("|")[1:-1] if p]
    if len(parts) != bars * 4 or any(len(p) != 4 for p in parts):
        raise ValueError(f"{label} four-slot grid drift: {row!r}")
    return parts


def _grid(rows: list[str], module: str, unit: str, line: int, page: int, bars: int = 1, *, chord_route: list[str] | None = None, repeat: int = 1) -> dict:
    count = _groups(rows[0], "Cnt", bars)
    hand = _groups(rows[1], "Hnd", bars)
    sound = _groups(rows[2], "Snd", bars)
    left = _groups(rows[3], "Lft", bars) if len(rows) > 3 and rows[3].startswith("Lft|") else ["----"] * (bars * 4)
    if count != [f"{beat}e&a" for _ in range(bars) for beat in range(1, 5)] or hand != ["DUDU"] * (bars * 4):
        raise ValueError(f"{module}/{unit} right-hand/count grid drift")
    if any(set(x) - set("Px-~") for x in sound) or any(set(x) - set("R-") for x in left):
        raise ValueError(f"{module}/{unit} unknown sound/release symbol")
    slots = []
    sustain_open = False
    for bar in range(bars):
        for beat in range(4):
            g = bar * 4 + beat
            for sub in range(4):
                symbol = sound[g][sub]
                if symbol == "~" and not sustain_open:
                    raise ValueError(f"{module}/{unit} tie without preceding pitched attack")
                if symbol in "Px":
                    sustain_open = symbol == "P"
                elif symbol == "-":
                    sustain_open = False
                if left[g][sub] == "R" and symbol in "P~":
                    raise ValueError(f"{module}/{unit} pressure release overlaps contact/tie")
                chord = chord_route[bar] if chord_route is not None else None
                slots.append({"bar_in_unit": bar + 1, "beat": beat + 1, "subdivision": ("number", "e", "&", "a")[sub], "printed_count": count[g][sub], "right_hand_path": hand[g][sub], "sound_symbol": symbol, "kind": {"P": "pitched contact", "x": "dead contact", "-": "silent air stroke", "~": "tie/sustain no new contact"}[symbol], "left_pressure_release": left[g][sub] == "R", "chord": chord, "txt_line": line, "pdf_page": page, "performed_onset": None, "performed_duration": None, "performed_bpm": None, "performed_quality": None})
    slots = [{**slot} for _ in range(repeat) for slot in slots]
    return {"source_rows": rows, "slots": slots, "contact_count": sum(s["sound_symbol"] in "Px" for s in slots), "pitched_count": sum(s["sound_symbol"] == "P" for s in slots), "dead_count": sum(s["sound_symbol"] == "x" for s in slots), "air_count": sum(s["sound_symbol"] == "-" for s in slots), "tie_count": sum(s["sound_symbol"] == "~" for s in slots), "release_count": sum(s["left_pressure_release"] for s in slots)}


def _reference_voicings(lines: list[str], pages: list[str]) -> list[dict]:
    start = lines.index("REFERENCE VOICINGS") + 1
    stop = lines.index("COMPLETE NOTATED WORKLOAD: 1018 string contacts plus continuous silent air strokes.")
    result = []
    for i in range(start, stop):
        m = re.fullmatch(r"\s*([A-G]m?(?:7|maj7|m7b5)?(?:-shell)?)\s+([x0-9 ]+)", lines[i])
        if not m:
            continue
        name, values = m.groups()
        frets = values.split()
        if len(frets) != 6 or any(x != "x" and (not x.isdigit() or int(x) > 24) for x in frets):
            raise ValueError(f"reference voicing six-string drift: {name}")
        in_pdf_palette = "".join(frets).lower() in pages[1].lower()
        result.append({"name": name, "frets_low_to_high": frets, "active_strings": [s for s, f in zip(STRINGS, frets) if f != "x"], "muted_strings": [s for s, f in zip(STRINGS, frets) if f == "x"], "source_row": lines[i], "txt_line": i + 1, "pdf_page": 2 if in_pdf_palette else None, "pdf_palette_present": in_pdf_palette})
    if len(result) != 17:
        raise ValueError(f"17 reference voicings drift: {len(result)}")
    if [x["name"] for x in result if not x["pdf_palette_present"]] != ["A", "E"]:
        raise ValueError("TXT/PDF reference palette subset drift")
    return result


def _simple_module(lines: list[str], bounds: tuple[int, int], pages: list[str], module: str) -> list[dict]:
    start, stop = bounds
    heads = [(i, m) for i in range(start, stop) if (m := re.match(rf"^{module}(\d+)\. (.+)", lines[i]))]
    if len(heads) != MODULE_UNITS[module] or [int(m.group(1)) for _, m in heads] != list(range(1, len(heads) + 1)):
        raise ValueError(f"module {module} heading coverage drift")
    units = []
    for n, (i, m) in enumerate(heads):
        segment = lines[i:heads[n + 1][0] if n + 1 < len(heads) else stop]
        row_i = next((k for k, row in enumerate(segment) if row.startswith("Cnt|")), None)
        if row_i is None or row_i + 2 >= len(segment):
            raise ValueError(f"module {module} missing grid")
        rows = segment[row_i:row_i + (4 if module == "C" else 3)]
        page = (3 if n < 8 else 4) if module == "A" else (6 if n < 4 else 7) if module == "C" else (11 if n < 3 else 12) if module == "F" else MODULE_PAGES[module][0]
        for row in rows:
            _pdf_has(pages, page, row, f"{module} grid")
        parsed = _grid(rows, module, m.group(0), i + row_i + 1, page, 2 if "||" in rows[0] else 1)
        label = next((int(x.split(":", 1)[1].strip()) for x in segment if x.startswith("Contacts:")), None)
        if label is None or label != parsed["contact_count"]:
            raise ValueError(f"module {module} printed contact count mismatch: {m.group(0)}")
        if module == "D":
            acc = next((x for x in pages[page - 1].splitlines() if x.startswith("Acc|") and x == "Acc|>---|----|----|----|"), None)
            if acc is None:
                raise ValueError("PDF D accent-row drift")
            parsed["pdf_accent_row"] = acc
        units.append({"label": m.group(0), "printed_contact_count": label, "txt_line": i + 1, "pdf_page": page, "full_source_lines": segment, **parsed})
    if sum(u["contact_count"] for u in units) != MODULE_COUNTS[module]:
        raise ValueError(f"module {module} total drift")
    return units


def _e(lines: list[str], bounds: tuple[int, int], pages: list[str]) -> list[dict]:
    start, stop = bounds
    pair_i = [i for i in range(start, stop) if re.fullmatch(r"[A-G]m?7? -> [A-G]m?7?", lines[i])]
    push_i = [i for i in range(start, stop) if re.match(r"E(?:9|10|11|12)\. ", lines[i])]
    if len(pair_i) != 8 or len(push_i) != 4:
        raise ValueError("E pair/push coverage drift")
    units = []
    for n, i in enumerate(pair_i + push_i):
        end = (pair_i + push_i)[n + 1] if n < 11 else stop
        segment = lines[i:end]
        grid_at = next(j for j, s in enumerate(segment) if s.startswith("Cnt|"))
        rows = segment[grid_at:grid_at + 3]
        bars = 2 if n < 8 else 1
        page = 9 if n < 4 else 10
        if n < 8:
            for row in rows:
                _pdf_has(pages, page, row, "E anticipation grid")
        else:
            for row in rows[:2]:
                _pdf_has(pages, page, row, "E push motion grid")
        parsed = _grid(rows, "E", lines[i], i + grid_at + 1, page, bars)
        label = next((int(s.split(":", 1)[1].strip()) for s in segment if s.startswith("Contacts:")), None)
        if label != parsed["contact_count"]:
            raise ValueError("E printed contact count drift")
        if n < 8:
            pair = lines[i].split(" -> ")
            chd = next((s for s in segment if s.startswith("Chd|")), None)
            if chd is None or [x.strip() for x in chd.split("||") if x.strip()] != [f"Chd|{pair[0]}", f"{pair[1]}                   |".strip()]:
                # The fixed-width Chd row is preserved verbatim; verify its two labels and barline.
                if chd is None or "||" not in chd or not chd.startswith("Chd|" + pair[0]) or not chd.endswith(pair[1].ljust(20) + "|"):
                    raise ValueError("E chord-label/barline drift")
            if rows[2] != "Snd|P-x-|P-x-|P-x-|P-P~||~~~~|P-x-|P-x-|P-x-|":
                raise ValueError("E anticipated tie route drift")
            for slot_index, slot in enumerate(parsed["slots"]):
                slot["chord"] = pair[0] if slot_index < 14 else pair[1]
        else:
            pair = None
            expected = {9: ("4 &", "Snd|P-x-|P-x-|P-x-|P-P~|"), 10: ("4 a", "Snd|P-x-|P-x-|P-x-|P--P|"), 11: ("2 &", "Snd|P-x-|P-P~|~~~~|P-x-|"), 12: ("3 a", "Snd|P-x-|P-x-|P--P|P-x-|")}[n + 1]
            if expected[0] not in lines[i] or rows[2] != expected[1]:
                raise ValueError("E push-point route drift")
        units.append({"label": lines[i], "pair": pair, "printed_contact_count": label, "txt_line": i + 1, "pdf_page": page, "full_source_lines": segment, **parsed})
    if sum(u["contact_count"] for u in units) != 142:
        raise ValueError("E 142-contact total drift")
    return units


def _progressions(lines: list[str], bounds: tuple[int, int], pages: list[str], module: str) -> list[dict]:
    start, stop = bounds
    heads = [(i, m) for i in range(start, stop) if (m := re.match(rf"^{module}(\d+)\. (.+)", lines[i]))]
    if len(heads) != MODULE_UNITS[module]:
        raise ValueError(f"module {module} study coverage drift")
    units = []
    for n, (i, m) in enumerate(heads):
        segment = lines[i:heads[n + 1][0] if n + 1 < len(heads) else stop]
        progression = next((x for x in segment if x.startswith("Progression: ")), None)
        if progression is None:
            raise ValueError(f"module {module} progression missing")
        chords = [x.strip() for x in progression.removeprefix("Progression: ").split("|") if x.strip()]
        if len(chords) != 4:
            raise ValueError(f"module {module} four-bar chord route drift")
        grid_at = next(j for j, s in enumerate(segment) if s.startswith("Cnt|"))
        rows = segment[grid_at:grid_at + 3]
        page = (13 if n < 3 else 14) if module == "G" else 15
        for row in rows:
            _pdf_has(pages, page, row, f"{module} study grid")
        parsed = _grid(rows, module, lines[i], i + grid_at + 1, page, chord_route=[chords[0]], repeat=4)
        # One printed bar is applied to each of the four named chords.
        for bar, chord in enumerate(chords):
            for slot in parsed["slots"][bar * 16:(bar + 1) * 16]:
                slot["bar_in_unit"] = bar + 1
                slot["chord"] = chord
        printed = next((int(x.split("x", 1)[1].split("=", 1)[1].split()[0]) for x in segment if x.startswith("Workload: 4 bars x ")), None) if module == "G" else next((int(x.split()[0]) for x in segment if re.fullmatch(r"\d+ contacts", x)), None)
        if printed is None:
            raise ValueError(f"module {module} count label missing")
        if module == "G":
            per_bar = int(next(x for x in segment if x.startswith("Workload: 4 bars x ")).split("x", 1)[1].split("=", 1)[0].strip())
            if parsed["contact_count"] != 4 * per_bar or printed != parsed["contact_count"]:
                raise ValueError("G four-bar workload drift")
        elif printed != 32:
            raise ValueError("H four printed 32-contact captions drift")
        units.append({"label": lines[i], "progression": chords, "voicing_or_texture": segment[2], "printed_contact_count": printed, "mask_derived_contact_count": parsed["contact_count"], "txt_line": i + 1, "pdf_page": page, "full_source_lines": segment, **parsed})
    if sum(u["contact_count"] for u in units) != MODULE_COUNTS[module]:
        raise ValueError(f"module {module} mask-derived total drift")
    if module == "H" and ([u["contact_count"] for u in units] != [32, 24, 32, 28] or sum(u["printed_contact_count"] for u in units) != 128):
        raise ValueError("H 116/128 conflict shape drift")
    return units


def _capstone(lines: list[str], bounds: tuple[int, int], pages: list[str]) -> list[dict]:
    start, stop = bounds
    heads = [(i, m) for i in range(start, stop) if (m := re.match(r"^(INTRO|VERSE A|PRE-CHORUS|CHORUS|BRIDGE|OUTRO|FINAL G) - bars (\d+)-(\d+)$", lines[i]))]
    if len(heads) != 7:
        raise ValueError("I seven-section form drift")
    units = []
    for n, (i, m) in enumerate(heads):
        segment = lines[i:heads[n + 1][0] if n < 6 else next(j for j in range(i, stop) if lines[j] == "PERFORMANCE PASSES")]
        name, first, last = m.groups()
        first, last = int(first), int(last)
        chords = [x.strip() for x in next(s for s in segment if s.startswith("Progression: ")).removeprefix("Progression: ").split("|") if x.strip()]
        if len(chords) != last - first + 1:
            raise ValueError("I section bar/chord route drift")
        grid_at = next(j for j, s in enumerate(segment) if s.startswith("Cnt|"))
        rows = segment[grid_at:grid_at + 3]
        page = 17 if n < 2 else 18 if n < 4 else 19
        for row in rows:
            _pdf_has(pages, page, row.replace("Snd|", "FINAL|", 1) if name == "FINAL G" and row.startswith("Snd|") else row, "I section grid")
        parsed = _grid(rows, "I", name, i + grid_at + 1, page, chord_route=[chords[0]], repeat=len(chords))
        for bar, chord in enumerate(chords):
            for slot in parsed["slots"][bar * 16:(bar + 1) * 16]:
                slot["bar_in_unit"] = first + bar
                slot["chord"] = chord
        printed = next((int(s.split(":", 1)[1].strip()) for s in segment if s.startswith("Contacts:")), None)
        if printed != parsed["contact_count"]:
            raise ValueError("I section contact count drift")
        units.append({"section": name, "first_bar": first, "last_bar": last, "chords": chords, "texture": next(s for s in segment if s.startswith("Texture: ")).removeprefix("Texture: "), "printed_contact_count": printed, "txt_line": i + 1, "pdf_page": page, "full_source_lines": segment, **parsed})
    if [(u["first_bar"], u["last_bar"]) for u in units] != [(1, 4), (5, 12), (13, 16), (17, 24), (25, 28), (29, 31), (32, 32)]:
        raise ValueError("I 32-bar form drift")
    if [u["contact_count"] for u in units] != [16, 64, 24, 64, 16, 24, 1] or sum(u["contact_count"] for u in units) != 209:
        raise ValueError("I 209-contact capstone drift")
    return units


def build_candidate(root: Path) -> dict:
    root = root.resolve()
    if root != Path(__file__).resolve().parents[1]:
        raise ValueError("supplied root is not this Git checkout")
    txt_raw = _pin(root / TXT_REL, TXT_SIZE, TXT_SHA)
    _pin(root / PDF_REL, PDF_SIZE, PDF_SHA)
    source_row = _source_map(root)
    pdf = PdfReader(root / PDF_REL)
    if len(pdf.pages) != 20:
        raise ValueError("PDF page count drift")
    pages = [x.extract_text() or "" for x in pdf.pages]
    for i, page in enumerate(pages, 1):
        if f"Page {i} of 20" not in page:
            raise ValueError(f"PDF page identity drift: {i}")
    txt = txt_raw.decode("utf-8")
    lines = txt.splitlines()
    bounds = _bounds(lines)
    voicings = _reference_voicings(lines, pages)
    modules = {m: {"units": _simple_module(lines, bounds[m], pages, m)} for m in "ABCDF"}
    modules["E"] = {"units": _e(lines, bounds["E"], pages)}
    modules["G"] = {"units": _progressions(lines, bounds["G"], pages, "G")}
    modules["H"] = {"units": _progressions(lines, bounds["H"], pages, "H")}
    modules["I"] = {"units": _capstone(lines, bounds["I"], pages)}
    modules = {m: modules[m] for m in "ABCDEFGHI"}
    for name, module in modules.items():
        if len(module["units"]) != MODULE_UNITS[name] or sum(u["contact_count"] for u in module["units"]) != MODULE_COUNTS[name]:
            raise ValueError(f"module {name} unit/contact total drift")
        module["mask_derived_contact_count"] = MODULE_COUNTS[name]
        module["txt_start_line"] = bounds[name][0] + 1
        module["txt_end_line"] = bounds[name][1]
        module["full_source_lines"] = lines[bounds[name][0]:bounds[name][1]]
    if sum(MODULE_COUNTS.values()) != 1018 or "COMPLETE NOTATED WORKLOAD: 1018 string contacts plus continuous silent air strokes." not in txt or "1018" not in pages[0]:
        raise ValueError("whole-workbook 1018-contact identity drift")
    if "128 CONTACTS" not in pages[14] or "H - texture / dynamics\n116" not in pages[0]:
        raise ValueError("H 116/128 printed contradiction drift")
    if "209 notated string contacts" not in pages[15] or "PERFORMANCE PASSES" not in txt or "two clean recorded days" not in txt:
        raise ValueError("capstone/mastery guidance drift")
    if "NO-STOP RULE" not in pages[18] or "Practice log" not in pages[19]:
        raise ValueError("PDF-only guidance drift")
    candidate = {"schema": "fathom.detached-source-candidate.1", "section": "VI", "level": 58, "wbs_id": "2.3.1.2.1", "source": {"txt_path": TXT_REL, "txt_bytes": TXT_SIZE, "txt_sha256": TXT_SHA, "pdf_path": PDF_REL, "pdf_bytes": PDF_SIZE, "pdf_sha256": PDF_SHA, "pdf_pages": 20, "source_map_path": MAP_REL, "source_map_bytes": MAP_SIZE, "source_map_sha256": MAP_SHA, "source_map_row": source_row, "prior_module_a_candidate": P01_REL, "prior_module_a_result": P01_RESULT}, "symbols": {"P": "pitched string contact", "x": "dead muted string contact", "-": "silent air motion", "~": "tie/sustain; no new contact", "R": "left-hand pressure release; no new contact", ">": "accent instruction, not a contact"}, "reference_voicings": voicings, "modules": modules, "module_count": 9, "printed_total_contact_count": 1018, "mask_derived_total_contact_count": 1018, "raw_caption_total_contact_count": 1030, "H_printed_headline_count": 128, "H_mask_derived_count": 116, "printed_guidance": {"kind": "printed_instruction", "txt_full_text": txt, "pdf_extracted_pages": [{"page": i + 1, "extracted_text": page} for i, page in enumerate(pages)]}, "source_exceptions": [{"code": "H_COUNT_CONFLICT", "status": "Pending Curriculum review", "source": "TXT H captions and PDF p15 versus TXT/PDF p1 workload", "decision": "Retain each H caption at 32, the p15 128 headline, all four exact masks and their derived 32/24/32/28=116 contacts. The printed 1018 total matches mask-derived H=116, while raw captions sum to 1030. Do not invent twelve contacts."}, {"code": "D_PDF_ACCENT_ROW", "status": "Pending Curriculum review", "source": "PDF p8 versus TXT Module D", "decision": "Retain PDF Acc|>---|----|----|----| row and text's first/final-contact accent alternatives; do not infer performed accent or shift a P slot."}, {"code": "PDF_ONLY_PROTOCOL_AND_CAPSTONE_REPAIR", "status": "Pending Curriculum review", "source": "PDF pp1-2,16-20", "decision": "Preserve PDF session/motion/muting, count and no-stop repair guidance, completion audit and blank log as instructions only."}, {"code": "E_PUSH_PAIR_UNSPECIFIED", "status": "Pending Curriculum review", "source": "TXT E9-E12 and PDF p10", "decision": "The push-point ladder says use the same progression without naming one chord pair for each cell; preserve the grid and chord mapping as unspecified."}], "music_row_exceptions": [], "canonical_ids": None, "review": "Pending", "runtime_eligible": False, "imported": False, "admitted": False, "performed_onset": None, "performed_duration": None, "performed_bpm": None, "performed_mastery": None, "pending": ["Curriculum count and accent/push interpretation", "independent musical review", "canonical IDs and runtime admission", "performed mastery gate"]}
    candidate["source_exceptions"].append({"code": "TXT_PDF_LAYOUT_AND_PALETTE", "status": "Pending Curriculum review", "source": "TXT reference palette/E9-E12/FINAL G versus PDF pp2,10,19", "decision": "TXT lists A and E open voicings absent from PDF p2 subset; TXT prints E9-E12 grids where PDF p10 summarizes push locations/counts; PDF p19 labels the final-G sustain row FINAL and combines it with the outro. Preserve both presentations without fabricating contacts."})
    return candidate


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    candidate = build_candidate(args.root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(candidate, sort_keys=True, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"LEVEL58 CANDIDATE PASS modules=9 contacts=1018 H_masks=116 H_captions=128 output={args.output}")


if __name__ == "__main__":
    main()
