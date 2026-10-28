#!/usr/bin/env python3
"""Build a lane-local, unassigned projection of Level 50's E-to-Em cell.

This is deliberately not a canonical package writer. A trusted current
identity handoff is required before any fg:* identity can be allocated.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TXT_REL = Path(
    "Notes/music/guitar project/TXT version/"
    "Guitar_Exercises_Section_VI_Level_50_Chord_Transitions_Common_Finger_and_"
    "Guide_Finger_Movement_Anticipated_Changes_and_Uninterrupted_Progressions.txt"
)
PDF_REL = Path(
    "Notes/music/guitar project/PDF version/"
    "Guitar_Exercises_Section_VI_Level_50_Chord_Transitions_Common_Finger_and_"
    "Guide_Finger_Movement_Anticipated_Changes_and_Uninterrupted_Progressions.pdf"
)
TXT_BYTES = 23_789
TXT_SHA256 = "c2a1e88fdc69545f17f7439b109fdad6a4b652285704ea730d0b8dae89a4306e"
PDF_BYTES = 50_728
PDF_SHA256 = "eec11800419be73416833d09a0bd46b42785cc050afc716b44d3b0129d0e2afc"
BUILD_ROOT = ROOT / "Build/parallel-01/2.3-level050-r02"
OPEN_MIDI_LOW_TO_HIGH = (40, 45, 50, 55, 59, 64)
EXPECTED_CHORD_DATA = {
    "E": {
        "frets": (0, 2, 2, 1, 0, 0),
        "fingers": ("O", 2, 3, 1, "O", "O"),
        "spelling": ("E", "G#", "B"),
        "pitch_class_to_spelling": {4: "E", 8: "G#", 11: "B"},
    },
    "Em": {
        "frets": (0, 2, 2, 0, 0, 0),
        "fingers": ("O", 2, 3, "O", "O", "O"),
        "spelling": ("E", "G", "B"),
        "pitch_class_to_spelling": {4: "E", 7: "G", 11: "B"},
    },
}
EXPECTED_COUNTS = ("1", "2", "3", "4", "1", "2", "3", "4")
EXPECTED_CHORDS = ("E", "Em", "E", "Em", "E", "Em", "E", "Em")
EXPECTED_STRUMS = ("D",) * 8
EXPECTED_PASSAGE_LINES = (45, 46, 47, 48, 49)


class CandidateError(ValueError):
    """Raised when source bytes or the selected cell do not match authority."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _labelled_row(lines: list[str], prefix: str) -> str:
    matches = [line for line in lines if line.startswith(prefix + "|")]
    if len(matches) != 1:
        raise CandidateError(f"expected one {prefix} row, found {len(matches)}")
    return matches[0].split("|", 1)[1]


def _parse_chord_reference(lines: list[str], chord: str) -> dict[str, Any]:
    matches = [line for line in lines if line.startswith(chord + ": frets ")]
    if len(matches) != 1:
        raise CandidateError(f"expected one printed {chord} voicing")
    fields = matches[0].split(" | ")
    if len(fields) != 4:
        raise CandidateError(f"unexpected printed {chord} reference shape")
    try:
        fret_text = fields[0].split(": frets ", 1)[1]
        frets = tuple(int(value) for value in fret_text.split())
        fingers = tuple(
            value if value == "O" else int(value)
            for value in fields[1].removeprefix("fingers ").split()
        )
        spelling = tuple(fields[2].removeprefix("spelling ").split())
    except (ValueError, TypeError) as exc:
        raise CandidateError(f"invalid printed {chord} voicing tokens") from exc
    if fields[3] != "attack all 6 strings":
        raise CandidateError(f"{chord} attack scope is not the authored six-string span")

    expected = EXPECTED_CHORD_DATA[chord]
    if frets != expected["frets"] or fingers != expected["fingers"]:
        raise CandidateError(f"printed {chord} fret/finger shape differs from pinned authority")
    if spelling != expected["spelling"]:
        raise CandidateError(f"printed {chord} spelling differs from pinned authority")

    members: list[dict[str, Any]] = []
    for index, (fret, finger, open_midi) in enumerate(
        zip(frets, fingers, OPEN_MIDI_LOW_TO_HIGH), start=1
    ):
        midi = open_midi + fret
        pitch_class = midi % 12
        note_name = expected["pitch_class_to_spelling"].get(pitch_class)
        if note_name is None:
            raise CandidateError(f"computed {chord} member pitch is outside its source spelling")
        members.append(
            {
                "kind": "note",
                "string": index,
                "fret": fret,
                "midi": midi,
                "spelling": note_name,
                "degree_contexts": {},
                "finger": finger,
                "onset_q": None,
                "duration_q": None,
                "attack": "picked",
                "tie_from": None,
            }
        )
    return {
        "symbol": chord,
        "frets_low_to_high": list(frets),
        "fingers_low_to_high": list(fingers),
        "source_spelling": list(spelling),
        "members_low_to_high": members,
        "attack_scope": "all_6_strings",
    }


def _parse_selected_cell(txt_bytes: bytes) -> dict[str, Any]:
    try:
        text = txt_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CandidateError("Level 50 TXT is not valid UTF-8") from exc
    lines = text.splitlines()

    if len(lines) < EXPECTED_PASSAGE_LINES[-1]:
        raise CandidateError("Level 50 TXT is truncated before the selected Module B cell")
    if lines[44:49] != [
        "E <-> Em",
        "Keep fingers 2-3 on A2 and D2; add or lift finger 1 at G1.",
        "Cnt|1----2----3----4----1----2----3----4----|",
        "Chd|E----Em---E----Em---E----Em---E----Em---|",
        "Str|D----D----D----D----D----D----D----D----|",
    ]:
        raise CandidateError("selected Level 50 TXT lines 45–49 differ from pinned cell authority")

    header_lines = lines[:24]
    chord_shapes = {
        chord: _parse_chord_reference(header_lines, chord) for chord in ("E", "Em")
    }
    selected = lines[44:49]
    count_row = _labelled_row(selected, "Cnt")
    chord_row = _labelled_row(selected, "Chd")
    strum_row = _labelled_row(selected, "Str")
    counts = tuple(re.findall(r"[1-4]", count_row))
    chords = tuple(re.findall(r"Em|E", chord_row))
    strums = tuple(re.findall(r"[A-Z]", strum_row))
    if counts != EXPECTED_COUNTS:
        raise CandidateError(f"expected eight explicit count positions, got {counts!r}")
    if chords != EXPECTED_CHORDS:
        raise CandidateError(f"expected the eight authored E/Em chord attacks, got {chords!r}")
    if strums != EXPECTED_STRUMS:
        raise CandidateError(f"expected eight authored D strums, got {strums!r}")

    return {
        "chord_shapes": chord_shapes,
        "counts": list(counts),
        "chords": list(chords),
        "strums": list(strums),
        "transition_instruction": selected[1],
    }


def build_projection(txt_bytes: bytes, pdf_bytes: bytes) -> dict[str, Any]:
    if len(txt_bytes) != TXT_BYTES or sha256(txt_bytes) != TXT_SHA256:
        raise CandidateError("Level 50 TXT byte length or SHA-256 differs from pinned source")
    if len(pdf_bytes) != PDF_BYTES or sha256(pdf_bytes) != PDF_SHA256:
        raise CandidateError("Level 50 PDF byte length or SHA-256 differs from pinned source")

    selected = _parse_selected_cell(txt_bytes)
    events: list[dict[str, Any]] = []
    for index, (count, chord, strum) in enumerate(
        zip(selected["counts"], selected["chords"], selected["strums"])
    ):
        shape = selected["chord_shapes"][chord]
        members = [dict(member) for member in shape["members_low_to_high"]]
        events.append(
            {
                "source_local_occurrence_key": f"L50-TXT1-47-49:attack-{index + 1:04d}",
                "count_label": count,
                "source_hand_direction": strum,
                "source_hand_action": "down_strum",
                "canonical_event_shape_projection": {
                    "kind": "chord",
                    "symbol": chord,
                    "onset_q": [index, 1],
                    "duration_q": None,
                    "members": members,
                    "attack": "simultaneous_example",
                },
            }
        )

    return {
        "projection_schema": "lane-local-source-cell-projection.1",
        "wbs_id": "2.3.1.2.1",
        "classification": "unadmitted_source_candidate_projection",
        "identity_assignment": {
            "status": "pending_trusted_identity_handoff",
            "workbook_level": 50,
            "module_id": None,
            "item_id": None,
            "variant_ids": [],
            "event_ids": [],
            "reason": (
                "No authorized current identity handoff is available for this batch; "
                "r15 reservations remain untouched."
            ),
        },
        "release_state": {
            "canonical_schema1_validated": False,
            "runtime_eligible": False,
            "imported": False,
            "admitted": False,
            "curriculum_accepted": False,
            "whole_workbook_complete": False,
        },
        "source_authority": {
            "txt": {
                "path": TXT_REL.as_posix(),
                "bytes": len(txt_bytes),
                "sha256": sha256(txt_bytes),
                "source_ref": "L50-TXT1-45-49",
                "line_start": 45,
                "line_end": 49,
            },
            "pdf": {
                "path": PDF_REL.as_posix(),
                "bytes": len(pdf_bytes),
                "sha256": sha256(pdf_bytes),
                "source_ref": "L50-PDF1-p4",
                "page": 4,
            },
        },
        "record_projection": {
            "title": "Level 50 Module B E-to-Em common-finger transition cell",
            "legacy_level": 50,
            "kind": "harmony",
            "source_refs": ["L50-TXT1-45-49", "L50-PDF1-p4"],
            "scope": {
                "extent": "complete_selected_case",
                "case": "Module B E <-> Em; eight authored attacks",
                "source_event_count": 8,
                "whole_workbook_complete": False,
            },
            "timing": {
                "unit": "quarter",
                "basis": (
                    "PDF page 4 explicitly says slow quarter notes and the source count "
                    "row labels eight successive positions."
                ),
                "attack_count": 8,
                "tempo_bpm": None,
                "attack_duration_q": None,
                "member_duration_q": None,
            },
            "voicings": selected["chord_shapes"],
            "transition_instruction": selected["transition_instruction"],
            "technique_legend": {
                "D": "down-strum, preserved from the authored Str row",
                "attack": (
                    "Each source chord attack is represented as a grouped chord example; "
                    "the schema projection does not fabricate within-strum member timing."
                ),
            },
            "events": events,
        },
    }


def deterministic_json_bytes(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode(
        "utf-8"
    )


def write_projection(output_path: Path, value: dict[str, Any]) -> Path:
    requested = output_path if output_path.is_absolute() else ROOT / output_path
    resolved = requested.resolve()
    build_root = BUILD_ROOT.resolve()
    if not resolved.is_relative_to(build_root):
        raise CandidateError(f"output must remain under {build_root}")
    if resolved.exists():
        raise CandidateError(f"refusing to replace existing candidate output: {resolved}")
    resolved.parent.mkdir(parents=True, exist_ok=True)
    with resolved.open("xb") as stream:
        stream.write(deterministic_json_bytes(value))
    return resolved


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        txt_bytes = (ROOT / TXT_REL).read_bytes()
        pdf_bytes = (ROOT / PDF_REL).read_bytes()
        projection = build_projection(txt_bytes, pdf_bytes)
        path = write_projection(args.output, projection)
    except (OSError, CandidateError) as exc:
        print(f"candidate refused: {exc}", file=sys.stderr)
        return 2
    print(f"lane-local candidate written: {path.relative_to(ROOT)}")
    print(f"candidate sha256: {sha256(path.read_bytes())}")
    print("identity assignment: pending; runtime/import/admission: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
