#!/usr/bin/env python3
"""Build the detached Level 41 A minor pentatonic source candidate."""

from __future__ import annotations

import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path
import re
import subprocess
from typing import Any

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
STEM = "Scale_Exercises_Section_V_Level_41_A_Minor_Pentatonic_Five_Position_Map_and_Connection_Fixed_Key_A"
TXT_REL = Path("Notes/music/guitar project/TXT version") / (STEM + ".txt")
PDF_REL = Path("Notes/music/guitar project/PDF version") / (STEM + ".pdf")
BUILD_REL = Path("Build/parallel-07/2.3.1.1.1-level041-whole-r01")
TXT_BYTES = 30654
TXT_SHA256 = "40188b431cf51581e9fe1df01b50b6bb459482fdbf322822d845c2d45a1cb00a"
PDF_BYTES = 42356
PDF_SHA256 = "97e30c02960dc260a459bb6a4c38cb4d5c36998952ae876264e839bc40f0c576"
STRINGS = ("E", "A", "D", "G", "B", "e")
TAB_STRINGS = tuple(reversed(STRINGS))
OPEN_MIDI = {"E": 40, "A": 45, "D": 50, "G": 55, "B": 59, "e": 64}
PITCH_CLASS = {"C": 0, "C#": 1, "D": 2, "E": 4, "F#": 6, "G": 7, "A": 9, "B": 11}
MINOR = {"A": "1", "C": "b3", "D": "4", "E": "5", "G": "b7"}
MAJOR = {"A": "1", "B": "2", "C#": "3", "E": "5", "F#": "6"}
POSITION_HEAD = re.compile(r"^P([1-5]) - (.+) FRAME - FRETS (\d+)-(\d+)$")
PAIR = re.compile(r"^  ([EADGBe]): (\d+)-(\d+) / fingers ([1-4])-([1-4]) / degrees (1|b3|4|5|b7)-(1|b3|4|5|b7) / notes ([A-G])-([A-G])$")
CARD = re.compile(r"^(\d+)\. P([1-5]): start ([EADGBe])(\d+) \(([A-G]) / (1|b3|4|5|b7)\); resolve to ([EADGBe])(\d+) \(A / 1\)\.$")


class CandidateError(ValueError):
    """Pinned source, printed musical semantics, or output boundary failed."""


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _verify(data: bytes, size: int, sha: str, label: str) -> None:
    if len(data) != size or digest(data) != sha:
        raise CandidateError(f"PINNED_INPUT_DRIFT {label}: bytes={len(data)} sha256={digest(data)}")


def _root() -> Path:
    result = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--show-toplevel"],
                            capture_output=True, text=True)
    if result.returncode or Path(result.stdout.strip()).resolve() != ROOT.resolve():
        raise CandidateError("REPOSITORY_ROOT_MISMATCH")
    return ROOT


def _source_bytes(root: Path, rel: Path) -> bytes:
    path = root / rel
    if path.is_symlink() or not path.is_file() or path.resolve().parent != path.parent.resolve():
        raise CandidateError(f"SOURCE_PATH_INVALID {rel}")
    return path.read_bytes()


def _pdf_pages(data: bytes) -> list[list[str]]:
    try:
        reader = PdfReader(BytesIO(data))
        if len(reader.pages) != 14:
            raise CandidateError("PDF_PAGE_COUNT_INVALID")
        return [page.extract_text().splitlines() for page in reader.pages]
    except CandidateError:
        raise
    except Exception as exc:
        raise CandidateError(f"PDF_READ_FAILED {type(exc).__name__}") from exc


def _line_after(lines: list[str], label: str) -> int:
    try:
        return lines.index(label) + 1
    except ValueError as exc:
        raise CandidateError(f"SOURCE_HEADING_MISSING {label}") from exc


def _row_parts(row: str, label: str, segments: int, slots: int) -> list[str]:
    parts = row.split("|")
    prefix = parts[0] if parts else ""
    normalized = prefix.strip() if label in STRINGS else prefix
    if (normalized != label or len(parts) != segments + 2 or parts[-1] != ""
        or any(len(part) != slots * 4 or re.fullmatch(r"[A-Za-z0-9#-]+", part) is None
               for part in parts[1:-1])):
        raise CandidateError(f"STAFF_ROW_INVALID {label}")
    return parts[1:-1]


def _staff(rows: list[str], segments: int, slots: int, pool: dict[str, str], label: str) -> dict[str, Any]:
    if len(rows) != 9:
        raise CandidateError(f"STAFF_LAYOUT_INVALID {label}")
    names = _row_parts(rows[0], "Nte", segments, slots)
    degrees = _row_parts(rows[1], "Deg", segments, slots)
    fingers = _row_parts(rows[2], "Fng", segments, slots)
    tabs = {string: _row_parts(row, string, segments, slots)
            for string, row in zip(TAB_STRINGS, rows[3:], strict=True)}
    events = []
    for segment in range(segments):
        for slot in range(slots):
            start = slot * 4
            tone = names[segment][start:start + 4].rstrip("-")
            degree = degrees[segment][start:start + 4].rstrip("-")
            finger = fingers[segment][start:start + 4].rstrip("-")
            contact = [(string, tabs[string][segment][start:start + 4].rstrip("-"))
                       for string in STRINGS if tabs[string][segment][start:start + 4] != "----"]
            if (tone not in pool or degree != pool[tone] or finger not in ("1", "2", "3", "4")
                or len(contact) != 1 or re.fullmatch(r"\d{1,2}", contact[0][1]) is None):
                raise CandidateError(f"STAFF_SLOT_INVALID {label} {segment + 1}:{slot + 1}")
            string, fret_text = contact[0]
            fret = int(fret_text)
            if (OPEN_MIDI[string] + fret) % 12 != PITCH_CLASS[tone]:
                raise CandidateError(f"TAB_NOTE_PITCH_MISMATCH {label} {segment + 1}:{slot + 1}")
            events.append({"ordinal": len(events) + 1, "segment": segment + 1,
                           "slot": slot + 1, "ascii_column": start,
                           "tone": tone, "degree": degree, "finger": int(finger),
                           "string": string, "fret": fret,
                           "onset_q": None, "duration_q": None})
    return {"raw_rows": rows, "events": events}


def _normalized_rows(rows: list[str]) -> list[str]:
    return [re.sub(r"^\s+([eBGDAE])\|", r"  \1|", row) for row in rows]


def _source_rows(lines: list[str], start: int) -> list[str]:
    rows = lines[start:start + 9]
    if len(rows) != 9 or not rows[0].startswith("Nte|"):
        raise CandidateError(f"TXT_STAFF_MISSING line {start + 1}")
    return rows


def _pdf_rows(page: list[str], heading: str, *, notes: bool = True) -> list[str]:
    start = _line_after(page, heading)
    count = 9 if notes else 8
    for index in range(start, min(start + 5, len(page))):
        if page[index].startswith("Nte|" if notes else "Deg|"):
            return page[index:index + count]
    raise CandidateError(f"PDF_STAFF_MISSING {heading}")


def _contact(event: dict[str, Any]) -> tuple[Any, ...]:
    return tuple(event[key] for key in ("tone", "degree", "finger", "string", "fret", "ascii_column"))


def _positions(lines: list[str], pages: list[list[str]]) -> list[dict[str, Any]]:
    first = _line_after(lines, "FIVE VERTICAL POSITION CELLS")
    last = lines.index("SHARED-ANCHOR SEAM CELLS")
    heads = [(index, match) for index in range(first, last)
             if (match := POSITION_HEAD.fullmatch(lines[index]))]
    if len(heads) != 5 or [int(match.group(1)) for _, match in heads] != list(range(1, 6)):
        raise CandidateError("POSITION_HEADINGS_INVALID")
    positions = []
    for ordinal, (index, match) in enumerate(heads, 1):
        low, high = int(match.group(3)), int(match.group(4))
        start_line = lines[index + 1]
        root_match = re.fullmatch(r"Starts on degree (1|b3|4|5|b7)\. Roots: (.+)\.", start_line)
        if root_match is None:
            raise CandidateError(f"POSITION_ROOTS_INVALID P{ordinal}")
        roots = root_match.group(2).split(", ")
        pairs = []
        for offset, string in enumerate(STRINGS, 1):
            pair_match = PAIR.fullmatch(lines[index + 3 + offset])
            if pair_match is None or pair_match.group(1) != string:
                raise CandidateError(f"POSITION_PAIR_INVALID P{ordinal} {string}")
            fret_a, fret_b, finger_a, finger_b = map(int, pair_match.group(2, 3, 4, 5))
            degree_a, degree_b, tone_a, tone_b = pair_match.group(6, 7, 8, 9)
            if (not low <= fret_a < fret_b <= high or (OPEN_MIDI[string] + fret_a) % 12 != PITCH_CLASS[tone_a]
                or (OPEN_MIDI[string] + fret_b) % 12 != PITCH_CLASS[tone_b]
                or MINOR.get(tone_a) != degree_a or MINOR.get(tone_b) != degree_b):
                raise CandidateError(f"POSITION_PAIR_SEMANTICS_INVALID P{ordinal} {string}")
            pairs.append({"string": string, "frets": [fret_a, fret_b], "fingers": [finger_a, finger_b],
                          "degrees": [degree_a, degree_b], "tones": [tone_a, tone_b],
                          "raw_line": lines[index + 3 + offset]})
        staff_start = index + 12
        rows = _source_rows(lines, staff_start)
        parsed = _staff(rows, 2, 12, MINOR, f"P{ordinal} vertical")
        events = parsed["events"]
        for string_index, pair in enumerate(pairs):
            for side in range(2):
                event = events[string_index * 2 + side]
                if (event["string"], event["fret"], event["finger"], event["degree"], event["tone"]) != (
                    pair["string"], pair["frets"][side], pair["fingers"][side],
                    pair["degrees"][side], pair["tones"][side]):
                    raise CandidateError(f"POSITION_PAIR_STAFF_MISMATCH P{ordinal} {pair['string']}")
        if ([_contact(event)[:5] for event in events[12:]] !=
            [_contact(event)[:5] for event in reversed(events[:12])]
            or events[0]["degree"] != root_match.group(1)):
            raise CandidateError(f"POSITION_ASC_DESC_INVALID P{ordinal}")
        root_set = [f"{event['string']}{event['fret']}" for event in events[:12]
                    if event["tone"] == "A"]
        if roots != root_set:
            raise CandidateError(f"POSITION_ROOT_LIST_MISMATCH P{ordinal}")
        pdf_page = pages[ordinal + 1]
        pdf_rows = _pdf_rows(pdf_page, "Position 1 vertical cell - 12 notes up + 12 notes down"
                             if ordinal == 1 else f"Position {ordinal} vertical cell - 12 notes up + 12 notes down")
        if _normalized_rows(pdf_rows) != _normalized_rows(rows):
            raise CandidateError(f"PDF_TXT_POSITION_STAFF_MISMATCH P{ordinal}")
        positions.append({"position": ordinal, "frame_name": match.group(2), "fret_span": [low, high],
                          "starting_degree": root_match.group(1), "roots": roots,
                          "string_pairs": pairs, **parsed, "pdf_raw_rows": pdf_rows,
                          "source_refs": [f"L41-TXT1-{index + 1}-{staff_start + 9}", f"L41-PDF1-p{ordinal + 2}"]})
    return positions


def _seams(lines: list[str], pages: list[list[str]], positions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seams = []
    for lower in range(1, 5):
        heading = f"SEAM P{lower} <-> P{lower + 1} - 30 NOTES"
        index = _line_after(lines, heading)
        anchor_line = lines[index]
        if not anchor_line.startswith("Shared anchors: "):
            raise CandidateError(f"SEAM_ANCHOR_LINE_INVALID {lower}")
        anchors = anchor_line.removeprefix("Shared anchors: ").split(", ")
        expected = []
        for left, right in zip(positions[lower - 1]["string_pairs"], positions[lower]["string_pairs"], strict=True):
            overlap = set(left["frets"]) & set(right["frets"])
            if len(overlap) != 1:
                raise CandidateError(f"SEAM_POSITION_OVERLAP_INVALID {lower}")
            expected.append(f"{left['string']}{next(iter(overlap))}")
        if anchors != expected:
            raise CandidateError(f"SEAM_ANCHORS_MISMATCH {lower}")
        rows = _source_rows(lines, index + 1)
        parsed = _staff(rows, 6, 5, MINOR, f"P{lower}-P{lower + 1} seam")
        events = parsed["events"]
        for group, (left, right, anchor) in enumerate(zip(
                positions[lower - 1]["string_pairs"], positions[lower]["string_pairs"], anchors, strict=True)):
            subset = events[group * 5:(group + 1) * 5]
            target_frets = [left["frets"][0], int(anchor[len(left["string"]):]),
                            right["frets"][1], int(anchor[len(left["string"]):]), left["frets"][0]]
            if [event["string"] for event in subset] != [left["string"]] * 5 or [
                    event["fret"] for event in subset] != target_frets:
                raise CandidateError(f"SEAM_FIVE_NOTE_LOOP_INVALID {lower} {left['string']}")
        pdf_page = pages[6 + (lower + 1) // 2]
        pdf_rows = _pdf_rows(pdf_page, f"Seam P{lower} <-> P{lower + 1}: shared-anchor five-note loops")
        if _normalized_rows(pdf_rows) != _normalized_rows(rows):
            raise CandidateError(f"PDF_TXT_SEAM_STAFF_MISMATCH {lower}")
        seams.append({"lower_position": lower, "upper_position": lower + 1,
                      "shared_anchors": anchors, "anchor_contact_slots": [2, 4],
                      "frame_phase_by_slot": ["lower", "lower", "upper", "upper", "lower"],
                      "shift_after_slot": [2, 4], "groups": [
                          {"string": string, "event_ordinals": list(range(i * 5 + 1, i * 5 + 6))}
                          for i, string in enumerate(STRINGS)],
                      **parsed, "pdf_raw_rows": pdf_rows,
                      "source_refs": [f"L41-TXT1-{index}-{index + 10}", f"L41-PDF1-p{8 if lower <= 2 else 9}"]})
    return seams


def _zigzag(lines: list[str], page: list[str], positions: list[dict[str, Any]], direction: str) -> dict[str, Any]:
    order = [(1, "ASC"), (2, "DESC"), (3, "ASC"), (4, "DESC"), (5, "ASC")] if direction == "forward" else [
        (5, "DESC"), (4, "ASC"), (3, "DESC"), (2, "ASC"), (1, "DESC")]
    route = []
    all_events = []
    for ordinal, (pos, orientation) in enumerate(order, 1):
        low, high = positions[pos - 1]["fret_span"]
        heading = f"P{pos} {orientation} - frets {low}-{high} - 12 NOTES"
        start = _line_after(lines, heading)
        rows = _source_rows(lines, start)
        parsed = _staff(rows, 1, 12, MINOR, f"{direction} P{pos}")
        cell_events = positions[pos - 1]["events"][:12] if orientation == "ASC" else positions[pos - 1]["events"][12:]
        if [_contact(event) for event in parsed["events"]] != [_contact(event) for event in cell_events]:
            raise CandidateError(f"ZIGZAG_POSITION_MISMATCH {direction} P{pos}")
        pdf_rows = _pdf_rows(page, f"P{pos} {orientation} - frets {low}-{high}", notes=False)
        if _normalized_rows(pdf_rows) != _normalized_rows(rows[1:]):
            raise CandidateError(f"PDF_TXT_ZIGZAG_STAFF_MISMATCH {direction} P{pos}")
        route.append({"position": pos, "direction": orientation.lower(), **parsed,
                      "pdf_raw_rows": pdf_rows,
                      "source_refs": [f"L41-TXT1-{start + 1}-{start + 9}",
                                      f"L41-PDF1-p{10 if direction == 'forward' else 11}"]})
        all_events.extend(parsed["events"])
    expected_transitions = [(("e", 8), ("e", 10)), (("E", 8), ("E", 10)),
                            (("e", 12), ("e", 15)), (("E", 12), ("E", 15))] if direction == "forward" else [
        (("E", 15), ("E", 12)), (("e", 15), ("e", 12)),
        (("E", 10), ("E", 8)), (("e", 10), ("e", 8))]
    transitions = []
    for index, (source, target) in enumerate(expected_transitions):
        left, right = all_events[index * 12 + 11], all_events[index * 12 + 12]
        if (left["string"], left["fret"]) != source or (right["string"], right["fret"]) != target:
            raise CandidateError(f"ZIGZAG_TRANSITION_MISMATCH {direction} {index + 1}")
        transitions.append({"from": f"{source[0]}{source[1]}", "to": f"{target[0]}{target[1]}"})
    return {"route": route, "transitions": transitions, "note_count": len(all_events),
            "pdf_layout_exception": "PDF omits Nte rows; TXT note names are verified against TAB pitch and position cells."}


def _comparison(lines: list[str], page: list[str]) -> list[dict[str, Any]]:
    pairs = []
    for pos in range(1, 6):
        phrases = []
        for color, pool in (("MAJOR", MAJOR), ("MINOR", MINOR)):
            heading = f"P{pos} - A {color} COLOR"
            start = _line_after(lines, heading)
            rows = _source_rows(lines, start)
            parsed = _staff(rows, 1, 6, pool, f"P{pos} {color} color")
            if [event["tone"] for event in parsed["events"]] != (
                ["A", "B", "C#", "E", "F#", "A"] if color == "MAJOR" else ["A", "C", "D", "E", "G", "A"]):
                raise CandidateError(f"COLOR_PHRASE_POOL_INVALID P{pos} {color}")
            phrases.append({"color": color.lower(), **parsed,
                            "source_ref": f"L41-TXT1-{start + 1}-{start + 9}"})
        if any(phrase["events"][0]["tone"] != "A" or phrase["events"][-1]["tone"] != "A"
               for phrase in phrases):
            raise CandidateError(f"COLOR_A_ROOT_ENDPOINT_INVALID P{pos}")
        for endpoint in (0, -1):
            if [(phrase["events"][endpoint]["string"], phrase["events"][endpoint]["fret"])
                    for phrase in phrases] != [
                        (phrases[0]["events"][endpoint]["string"], phrases[0]["events"][endpoint]["fret"])] * 2:
                raise CandidateError(f"COLOR_COMPARABLE_ROOT_MISMATCH P{pos}")
        pdf_rows = _pdf_rows(page, f"P{pos} - major color | minor color")
        if not pdf_rows[1].startswith("Job|"):
            raise CandidateError(f"PDF_COLOR_JOB_LABEL_MISSING P{pos}")
        for segment, phrase in enumerate(phrases):
            normalized = []
            for row in pdf_rows:
                prefix, *parts = row.split("|")
                normalized.append(("Deg" if prefix == "Job" else prefix) + "|" + parts[segment] + "|")
            if _normalized_rows(normalized) != _normalized_rows(phrase["raw_rows"]):
                raise CandidateError(f"PDF_TXT_COLOR_STAFF_MISMATCH P{pos} {phrase['color']}")
        pairs.append({"position": pos, "phrases": phrases, "silence_between_phrases_beats": 1,
                      "silence_is_instruction_not_note_event": True, "pdf_raw_rows": pdf_rows,
                      "pdf_source_ref": "L41-PDF1-p12"})
    return pairs


def _cards(lines: list[str], page: list[str], positions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cards = []
    start = _line_after(lines, "RANDOM-POSITION ENTRY CARDS")
    candidates = [(i, CARD.fullmatch(line)) for i, line in enumerate(lines[start:], start) if CARD.fullmatch(line)]
    if len(candidates) != 10:
        raise CandidateError("RANDOM_CARD_COUNT_INVALID")
    for index, (line_index, match) in enumerate(candidates, 1):
        assert match is not None
        number, pos = int(match.group(1)), int(match.group(2))
        string, fret, tone, degree = match.group(3), int(match.group(4)), match.group(5), match.group(6)
        root_string, root_fret = match.group(7), int(match.group(8))
        if number != index or pos != (index + 1) // 2 or MINOR.get(tone) != degree:
            raise CandidateError(f"RANDOM_CARD_IDENTITY_INVALID {index}")
        if (OPEN_MIDI[string] + fret) % 12 != PITCH_CLASS[tone] or (
                OPEN_MIDI[root_string] + root_fret) % 12 != PITCH_CLASS["A"]:
            raise CandidateError(f"RANDOM_CARD_PITCH_INVALID {index}")
        contacts = {(event["string"], event["fret"]) for event in positions[pos - 1]["events"]}
        if (string, fret) not in contacts or (root_string, root_fret) not in contacts:
            raise CandidateError(f"RANDOM_CARD_POSITION_INVALID {index}")
        pdf_header = f"{index}. P{pos}"
        pdf_index = _line_after(page, pdf_header)
        if page[pdf_index:pdf_index + 2] != [f"{string}{fret} ({tone} / {degree})",
                                                 f"{root_string}{root_fret} (A / 1)"]:
            raise CandidateError(f"PDF_TXT_RANDOM_CARD_MISMATCH {index}")
        cards.append({"card": number, "position": pos,
                      "start": {"string": string, "fret": fret, "tone": tone, "degree": degree},
                      "required_resolution": {"string": root_string, "fret": root_fret, "tone": "A", "degree": "1"},
                      "requested_phrase_note_count": 6, "authored_phrase_events": None,
                      "counted_in_written_workout": False, "raw_line": lines[line_index],
                      "source_refs": [f"L41-TXT1-{line_index + 1}", "L41-PDF1-p13"]})
    return cards


def _verify_atlas(positions: list[dict[str, Any]], seams: list[dict[str, Any]], page: list[str]) -> None:
    if page[0] != "Level 41 - Fixed-Key A Minor-Pentatonic Atlas" or "A C D E G  |  1 b3 4 5 b7" not in page:
        raise CandidateError("PDF_ATLAS_TITLE_OR_POOL_MISMATCH")
    head = _line_after(page, "Ascending degree order")
    for pos in positions:
        number = pos["position"]
        chunk = page[head + (number - 1) * 5:head + number * 5]
        expected = [f"P{number}", f"{pos['fret_span'][0]}-{pos['fret_span'][1]}",
                    pos["starting_degree"], ", ".join(pos["roots"]),
                    " ".join(event["degree"] for event in pos["events"][:12])]
        if chunk != expected:
            raise CandidateError(f"PDF_ATLAS_POSITION_MISMATCH P{number}")
    seam_start = _line_after(page, "Shared anchors: E A D G B e")
    for index, seam in enumerate(seams):
        if page[seam_start + 2 * index:seam_start + 2 * index + 2] != [
                f"P{index + 1}-P{index + 2}",
                " ".join(re.search(r"\d+", anchor).group() for anchor in seam["shared_anchors"])]:
            raise CandidateError(f"PDF_ATLAS_SEAM_MISMATCH {index + 1}")


def build_candidate(*, txt_data: bytes | None = None, pdf_data: bytes | None = None) -> dict[str, Any]:
    root = _root()
    txt_data = _source_bytes(root, TXT_REL) if txt_data is None else txt_data
    pdf_data = _source_bytes(root, PDF_REL) if pdf_data is None else pdf_data
    _verify(txt_data, TXT_BYTES, TXT_SHA256, "L41-TXT")
    _verify(pdf_data, PDF_BYTES, PDF_SHA256, "L41-PDF")
    try:
        lines = txt_data.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise CandidateError("TXT_ENCODING_INVALID") from exc
    if len(lines) != 554 or lines[:2] != ["SCALE EXERCISES - SECTION V, LEVEL 41",
                                      "A MINOR PENTATONIC FIVE-POSITION MAP AND CONNECTION - FIXED KEY A"]:
        raise CandidateError("TXT_TITLE_OR_LINE_COUNT_INVALID")
    pages = _pdf_pages(pdf_data)
    expected_titles = {0: "Scale Exercises - Section V, Level 41",
                       1: "Level 41 - Fixed-Key A Minor-Pentatonic Atlas",
                       7: "Level 41 - Shared-Anchor Seams I", 8: "Level 41 - Shared-Anchor Seams II",
                       9: "Level 41 - Forward Five-Position Zigzag",
                       10: "Level 41 - Reverse Five-Position Zigzag",
                       11: "Level 41 - Parallel Major and Minor Color Comparison",
                       12: "Level 41 - Practice Progression and Random Entry",
                       13: "Level 41 - Mastery Gate and Practice Log"}
    if any(pages[index][0] != title for index, title in expected_titles.items()):
        raise CandidateError("PDF_PAGE_TITLE_MISMATCH")
    positions = _positions(lines, pages)
    seams = _seams(lines, pages, positions)
    if (lines[198:201] != [
            "For each string, play lower outer note -> shared anchor -> upper outer note -> shared anchor -> lower outer note.",
            "Stay in the lower-position fingering through note 2. Shift after the anchor sounds, play note 3 in the upper",
            "frame, return to the anchor as note 4, then shift back before note 5."]
        or any("SHIFT AFTER THE ANCHOR - NOT BEFORE" not in pages[index] for index in (7, 8))):
        raise CandidateError("SEAM_SHIFT_RULE_MISMATCH")
    forward = _zigzag(lines, pages[9], positions, "forward")
    reverse = _zigzag(lines, pages[10], positions, "reverse")
    for zigzag, page in ((forward, pages[9]), (reverse, pages[10])):
        joined = " ".join(page)
        if any(f"{step['from']} to {step['to']}" not in joined for step in zigzag["transitions"]):
            raise CandidateError("PDF_ZIGZAG_ROUTE_TRANSITIONS_MISMATCH")
    if (forward["route"][-1]["events"][-1]["string"], forward["route"][-1]["events"][-1]["fret"],
        reverse["route"][0]["events"][0]["string"], reverse["route"][0]["events"][0]["fret"]) != (
            "e", 17, "e", 17):
        raise CandidateError("ZIGZAG_TURN_REARTICULATION_INVALID")
    if (reverse["route"][-1]["events"][-1]["string"], reverse["route"][-1]["events"][-1]["fret"]) != ("E", 5):
        raise CandidateError("ZIGZAG_FINAL_ROOT_INVALID")
    comparisons = _comparison(lines, pages[11])
    cards = _cards(lines, pages[12], positions)
    _verify_atlas(positions, seams, pages[1])
    count_parts = [sum(len(p["events"]) for p in positions), sum(len(s["events"]) for s in seams),
                   forward["note_count"] + reverse["note_count"],
                   sum(len(phrase["events"]) for pair in comparisons for phrase in pair["phrases"])]
    if count_parts != [120, 120, 120, 60] or sum(count_parts) != 420:
        raise CandidateError(f"WRITTEN_WORKOUT_COUNT_INVALID {count_parts}")
    page13 = pages[12]
    for label, value in zip(("5 position cells", "4 seam cells", "Forward + reverse", "Color comparisons", "Written total"),
                            (*count_parts, 420), strict=True):
        if page13[_line_after(page13, label)] != str(value):
            raise CandidateError(f"PDF_WRITTEN_COUNT_MISMATCH {label}")
    if "Complete written workout = 420 tones." not in lines[40] or "one beat" not in lines[382]:
        raise CandidateError("TXT_WRITTEN_COUNT_OR_COMPARISON_RULE_MISSING")
    return {
        "schema": "fathom-level041-whole-detached-candidate-v1", "wbs_id": "2.3.1.1.1", "level": 41,
        "source": {"txt_path": TXT_REL.as_posix(), "txt_bytes": TXT_BYTES, "txt_sha256": TXT_SHA256,
                   "pdf_path": PDF_REL.as_posix(), "pdf_bytes": PDF_BYTES, "pdf_sha256": PDF_SHA256,
                   "pdf_pages": 14},
        "key": "A", "minor_pentatonic": MINOR, "major_comparison": MAJOR,
        "position_numbering": "ascending-neck order from the standard A-minor root frame at fret 5",
        "modules": {"vertical_positions": {"positions": positions, "note_count": count_parts[0]},
                    "shared_anchor_seams": {"seams": seams, "note_count": count_parts[1]},
                    "linked_zigzag": {"forward": forward, "reverse": reverse,
                                      "note_count": count_parts[2], "turn_rearticulated": "e17"},
                    "parallel_color_comparisons": {"pairs": comparisons, "note_count": count_parts[3]}},
        "written_workout_note_count": 420, "random_entry_cards": cards,
        "source_instructions": {"overview_text": "\n".join(lines[:50]),
                                "seam_rule_text": "\n".join(lines[198:201]),
                                "practice_mastery_text": "\n".join(lines[506:]),
                                "source_refs": ["L41-TXT1-1-50", "L41-TXT1-199-202",
                                                "L41-TXT1-507-554", "L41-PDF1-p1-2", "L41-PDF1-p13-14"]},
        "pdf_layout_exceptions": [
            "PDF zigzag pages omit TXT Nte rows; printed degrees, fingers, and TAB match.",
            "PDF comparison page merges each major/minor pair and labels the degree row Job; split segments match TXT Deg rows.",
            "PDF TAB row leading spaces are normalized for parity; each source's raw rows remain stored."],
        "canonical_item_id": None, "canonical_variant_id": None,
        "onset_q": None, "duration_q": None, "fixed_bpm": None, "note_per_click": None,
        "pending": ["Curriculum/musical review", "canonical identity allocation and admission",
                    "runtime note timing and performed audio"],
        "whole_workbook_complete": False, "runtime_eligible": False, "runtime_admitted": False,
        "imported": False, "admitted": False,
    }


def write_candidate(output: Path) -> dict[str, Any]:
    root = _root()
    target = output if output.is_absolute() else root / output
    allowed = root / BUILD_REL
    if not target.parent.exists() or target.parent.is_symlink() or target.parent.resolve() != allowed.resolve():
        raise CandidateError(f"OUTPUT_OUTSIDE_LANE_BUILD {output}")
    if target.suffix != ".json" or target.is_symlink():
        raise CandidateError(f"OUTPUT_INVALID {output}")
    data = (json.dumps(build_candidate(), indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode()
    try:
        with target.open("xb") as handle:
            handle.write(data)
    except FileExistsError as exc:
        raise CandidateError(f"OUTPUT_EXISTS {output}") from exc
    return {"output": str(target.relative_to(root)), "bytes": len(data), "sha256": digest(data)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(write_candidate(args.output), sort_keys=True))
    except CandidateError as exc:
        parser.exit(2, f"{exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
