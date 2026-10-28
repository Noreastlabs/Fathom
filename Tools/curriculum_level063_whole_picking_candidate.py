#!/usr/bin/env python3
"""Pinned, detached whole-Level63 picking workbook source conversion."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
TXT = "Notes/music/guitar project/TXT version/Guitar_Exercises_Section_VII_Level_63_Crosspicking_Hybrid_Picking_Controlled_Sweep_Bursts_and_Arpeggio_Phrase_Endurance.txt"
PDF = "Notes/music/guitar project/PDF version/Guitar_Exercises_Section_VII_Level_63_Crosspicking_Hybrid_Picking_Controlled_Sweep_Bursts_and_Arpeggio_Phrase_Endurance.pdf"
MAP = "Results/parallel-01/exercises/inventory/20260922T180500Z-2.3-curriculum-v1-source-inventory-evidence/curriculum-source-map.json"
PIN = {TXT: (51663, "7241985f8ce08055d3171db3d935ee1d99ec6716f87f9b8d452d46004f91420b"),
       PDF: (60010, "9a0f8cc0ab906a5bcd2e495294be067e76eee6593a80f242b3c368475df5639f"),
       MAP: (199753, "bad5581a04f43ba8baf14db430449e1ccff5cf88f0f7e42198328073b27053d6")}
EXPECTED = {"A": 64, "B": 64, "C": 64, "D": 64, "E": 72, "F": 64, "G": 224, "H": 144, "I": 128, "J": 128}
PAGE_SPANS = {"A": [(3, 4), (4, 4)], "B": [(5, 8)], "C": [(6, 8)], "D": [(7, 8)],
              "E": [(8, 6), (9, 6)], "F": [(10, 8)], "G": [(11, 16), (12, 16)],
              "H": [(13, 6), (14, 6)], "I": [(15, 4)], "J": [(17, 16), (18, 16)]}
OPEN = {"E": 40, "A": 45, "D": 50, "G": 55, "B": 59, "e": 64}
PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
NOTE = re.compile(r"[A-G](?:#|b)?")
ROLE = re.compile(r">?(?:b?\d+|R)")
PICK = re.compile(r"[DUPma]")
FRET = re.compile(r"\d+")


class ConversionError(ValueError):
    pass


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sources(root: Path) -> tuple[list[str], list[str], dict]:
    raw = {}
    for rel, (size, digest) in PIN.items():
        path = root / rel
        if path.is_symlink() or not path.resolve(strict=True).is_relative_to(root):
            raise ConversionError(f"unsafe source: {rel}")
        data = path.read_bytes()
        if len(data) != size or sha(data) != digest:
            raise ConversionError(f"pinned source drift: {rel}")
        raw[rel] = data
    rows = json.loads(raw[MAP])["rows"]
    row = next((r for r in rows if r["level"] == 63), None)
    if row is None or row["txt_path"] != TXT or row["pdf_path"] != PDF or row["section"] != "VII" or row["wbs_owner"] != "2.3.1.2.1" or row["conversion_status"] != "not_converted" or row["admitted"]:
        raise ConversionError("source-map identity/status drift")
    pages = [p.extract_text() or "" for p in PdfReader(root / PDF).pages]
    if len(pages) != 20 or any(f"Level 63" not in p.splitlines()[0] for p in pages):
        raise ConversionError("PDF identity/pages drift")
    return raw[TXT].decode("utf-8").splitlines(), pages, row


def segments(row: str, label: str, count: int) -> list[str]:
    if not row.startswith(label + "|"):
        raise ConversionError(f"expected {label} grid")
    parts = row.split("|")[1:]
    if parts and parts[-1] == "":
        parts.pop()
    if len(parts) != count:
        raise ConversionError(f"{label} bar count {len(parts)} != {count}")
    return parts


def pitch_class(note: str) -> int:
    return (PC[note[0]] + (1 if note.endswith("#") else -1 if note.endswith("b") else 0)) % 12


def parse_grid(lines: list[str], note_index: int, page: int) -> tuple[list[dict], dict]:
    note_line = lines[note_index]
    bars = note_line.count("|") - (1 if note_line.endswith("|") else 0)
    if bars not in (1, 3, 4):
        raise ConversionError(f"unexpected bar shape TXT {note_index + 1}: {bars}")
    rows = {label: segments(lines[note_index + offset], label, bars)
            for offset, label in enumerate(("Nte", "Rol", "Pck"))}
    tab = {}
    for offset, string in enumerate(("e", "B", "G", "D", "A", "E"), 3):
        row = lines[note_index + offset]
        if row.split("|", 1)[0].strip() != string:
            raise ConversionError(f"TAB string order TXT {note_index + offset + 1}")
        tab[string] = segments(row.strip(), string, bars)
    attacks = []
    for bar in range(bars):
        notes = list(NOTE.finditer(rows["Nte"][bar]))
        roles = list(ROLE.finditer(rows["Rol"][bar]))
        picks = list(PICK.finditer(rows["Pck"][bar]))
        frets = [(m.start(), string, int(m.group())) for string in OPEN
                 for m in FRET.finditer(tab[string][bar])]
        positions = [m.start() for m in notes]
        if not positions or positions != [m.start() for m in roles] or positions != [m.start() for m in picks] or positions != sorted(pos for pos, _, _ in frets):
            raise ConversionError(f"source grid alignment TXT {note_index + 1} bar {bar + 1}: {positions}, {[m.start() for m in roles]}, {[m.start() for m in picks]}, {sorted(p for p,_,_ in frets)}")
        for ordinal, (n, role, pick) in enumerate(zip(notes, roles, picks), 1):
            _, string, fret = next(f for f in frets if f[0] == n.start())
            midi = OPEN[string] + fret
            spelling = n.group()
            if midi % 12 != pitch_class(spelling):
                raise ConversionError(f"source pitch/fret mismatch TXT {note_index + 1} bar {bar + 1} slot {ordinal}: {spelling} {string}{fret}")
            attacks.append({"ordinal": len(attacks) + 1, "bar": bar + 1, "slot": ordinal,
                            "spelling": spelling, "printed_role": role.group(), "printed_pick": pick.group(),
                            "string": string, "fret": fret, "midi": midi,
                            "onset_q": None, "duration_q": None, "canonical_event_id": None,
                            "source": {"txt_lines": [note_index + 1, note_index + 2, note_index + 3,
                                                     note_index + 4 + list(("e", "B", "G", "D", "A", "E")).index(string)],
                                       "pdf_page": page}})
    grid = {"txt_start_line": note_index + 1, "txt_end_line": note_index + 9,
            "rows": {label: lines[note_index + offset] for offset, label in enumerate(("Nte", "Rol", "Pck"))},
            "tab": [lines[note_index + 3 + i] for i in range(6)], "pdf_page": page,
            "pdf_grid_relationship": "PDF omits TAB" if page in (11, 12) else
                                     "PDF combines four TXT bars" if page in (17, 18) else "printed grid"}
    return attacks, grid


def page_for(module: str, cell_index: int) -> int:
    remaining = cell_index
    for page, count in PAGE_SPANS[module]:
        if remaining <= count:
            return page
        remaining -= count
    raise ConversionError(f"too many {module} cells")


def check_picking(modules: dict) -> None:
    for key, mod in modules.items():
        for i, cell in enumerate(mod["cells"]):
            actual = "".join(a["printed_pick"] for a in cell["attacks"])
            if key in "AB":
                expected = "DUDUDUDU"
            elif key == "C":
                expected = "PmamPmam"
            elif key == "D":
                expected = "PPmamPPa" if i % 2 == 0 else "PmPaPmam"
            elif key == "E":
                expected = "DDDUUU"
            elif key == "F":
                expected = "DDDDUUUU"
            elif key == "G":
                expected = ("DUDUDUDU", "PmamPmam", "DDDUUU", "UUUDDD")[i % 4]
            elif key == "H":
                expected = ("DUDU" if i % 6 < 2 else "PPma" if i % 6 < 4 else "DDDD") * 3
            elif key == "I":
                expected = ("DUDUDUDU" * 4, "PPmamPPa" * 4, "DDDDUUUU" * 4,
                            "DUDUDUDUPPmamPPaDDDDUUUUUUUUDDDD")[i]
            else:
                expected = ("DUDU", "PPma", "DDDD", "UUUU")[i % 4]
            if actual != expected:
                raise ConversionError(f"picking-system mismatch {key} cell {i + 1}: {actual}")


def check_pdf_relayout(modules: dict, pages: list[str]) -> None:
    for i in range(0, 32, 4):
        cells = modules["J"]["cells"][i:i + 4]
        page = 17 if i < 16 else 18
        for row in ("Nte", "Pck"):
            joined = row + "|" + "|".join(c["grid"]["rows"][row][4:] for c in cells) + "|"
            if joined not in pages[page - 1]:
                raise ConversionError(f"PDF grouped capstone mismatch p{page} bars {i + 1}-{i + 4} {row}")
        pdf_roles = [line for line in pages[page - 1].splitlines() if line.startswith("Rol|")]
        if len(pdf_roles) != 4:
            raise ConversionError(f"PDF capstone role group count p{page}")
        pdf_role = pdf_roles[(i % 16) // 4]
        pdf_bars = pdf_role.split("|")[1:-1]
        if len(pdf_bars) != 4:
            raise ConversionError(f"PDF capstone bar roles p{page}")
        for cell, pdf_bar in zip(cells, pdf_bars):
            txt_roles = [m.group() for m in ROLE.finditer(cell["grid"]["rows"]["Rol"].split("|", 1)[1])]
            visible_roles = [m.group() for m in ROLE.finditer(pdf_bar)]
            if [r.removeprefix(">") for r in visible_roles] != txt_roles or not visible_roles[0].startswith(">"):
                raise ConversionError(f"PDF/TXT capstone role difference outside beat-one accent p{page}")
            cell["pdf_beat_one_role_accent"] = True


def convert(root: Path = ROOT) -> dict:
    root = root.resolve(strict=True)
    lines, pages, row = sources(root)
    modules = {key: {"letter": key, "headings": [], "cells": [], "attack_count": 0}
               for key in EXPECTED}
    current = None
    for i, line in enumerate(lines):
        heading = re.fullmatch(r"MODULE ([A-J]) - (.+)", line)
        if heading:
            current = heading.group(1)
            modules[current]["headings"].append({"txt_line": i + 1, "text": line})
            continue
        if not line.startswith("Nte|"):
            continue
        if current is None:
            raise ConversionError(f"grid before module TXT {i + 1}")
        mod = modules[current]
        idx = len(mod["cells"]) + 1
        page = page_for(current, idx)
        attacks, grid = parse_grid(lines, i, page)
        if current != "J":
            comparable = lines[i:i + 3] if current == "G" else lines[i:i + 9]
            for source_line in comparable:
                if source_line not in pages[page - 1]:
                    raise ConversionError(f"PDF/TXT grid mismatch p{page} TXT {i + 1}")
        preceding = []
        j = i - 1
        while j >= 0 and lines[j].strip() and not lines[j].startswith(("MODULE ", "Nte|", "Rol|", "Pck|")) and not re.match(r"\s*[eBGDAE]\|", lines[j]):
            preceding.insert(0, {"txt_line": j + 1, "text": lines[j]})
            j -= 1
        mod["cells"].append({"local_key": f"level63-{current.lower()}-{idx:02d}", "heading_context": preceding,
                             "grid": grid, "attacks": attacks, "attack_count": len(attacks)})
        mod["attack_count"] += len(attacks)
    actual = {key: mod["attack_count"] for key, mod in modules.items()}
    if actual != EXPECTED or sum(actual.values()) != 1016:
        raise ConversionError(f"workload mismatch: {actual}")
    for key, mod in modules.items():
        if len(mod["cells"]) != sum(n for _, n in PAGE_SPANS[key]):
            raise ConversionError(f"cell count mismatch {key}")
    check_picking(modules)
    check_pdf_relayout(modules, pages)
    return {"candidate_kind": "detached_whole_workbook_source_conversion", "level": 63,
            "section": "VII", "workstream": "2.3.1.2.1", "review": "Pending",
            "runtime_eligible": False, "imported": False, "admitted": False, "canonical_ids": None,
            "source_map_row": row,
            "source_pins": {rel: {"bytes": size, "sha256": digest} for rel, (size, digest) in PIN.items()},
            "workload_printed": EXPECTED, "attack_count": 1016,
            "modules": [modules[key] for key in EXPECTED],
            "txt_source_lines": [{"line": i + 1, "text": s} for i, s in enumerate(lines)],
            "pdf_source_pages": [{"page": i + 1, "text": p,
                                  "extracted_text_sha256": sha(p.encode("utf-8"))} for i, p in enumerate(pages)],
            "source_exceptions": [
                {"kind": "pdf_relayout", "detail": "PDF Module G displays Nte/Rol/Pck blocks without matching six-string TAB rows; TXT supplies fret contacts.", "pdf_pages": [11, 12]},
                {"kind": "pdf_relayout", "detail": "PDF Module J groups four TXT single-bar grids into each four-bar key phrase.", "pdf_pages": [17, 18]},
                {"kind": "pdf_only_role_accent", "detail": "PDF Module J prints a > beat-one role accent in every bar; the TXT role rows omit these accents. Candidate retains both authored rows and marks PDF beat-one accents without changing TXT attacks.", "pdf_pages": [17, 18]},
                {"kind": "unquantified_performance", "detail": "Opposite pick starts, note release, work/rest duration, tempo, stamina and mastery are instructions; no per-attack absolute timing or observed performance is supplied.", "pdf_pages": [3, 4, 15, 16, 19, 20]}],
            "pending": "No canonical IDs, Curriculum acceptance, runtime import or learner performance observation."}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    root = args.root.resolve(strict=True)
    if root != ROOT:
        raise ConversionError("wrong checkout")
    output = args.output.resolve()
    allowed = root / "Build/parallel-05/2.3.1.2.1-level063-whole-r01"
    if not output.is_relative_to(allowed) or output.exists():
        raise ConversionError("output must be new under lane Build")
    data = (json.dumps(convert(root), indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(data)
    print(f"{output.relative_to(root)} {len(data)} bytes sha256={sha(data)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
