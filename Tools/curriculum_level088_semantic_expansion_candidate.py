from __future__ import annotations

import argparse
import hashlib
import json
import re
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BUILD_REL = Path("Build/parallel-04/2.3.1.3.1-level088-semantic-pdf-expansion-r01")
PROMPT_REL = Path("Prompts/parallel-04/exercises/conversion/20260923T171130Z-2.3.1.3.1-level088-semantic-pdf-expansion-r01.md")
TXT = "Notes/music/guitar project/TXT version/Guitar_Exercises_Section_XII_Level_88_Rock_Hard_Rock_and_Metal_Groove_Control_Eighth_Note_Drive_Gallops_Pedal_Tones_Power_Chord_Displacement_and_Riff_Architecture.txt"
PDF = "Notes/music/guitar project/PDF version/Guitar_Exercises_Section_XII_Level_88_Rock_Hard_Rock_and_Metal_Groove_Control_Eighth_Note_Drive_Gallops_Pedal_Tones_Power_Chord_Displacement_and_Riff_Architecture.pdf"
SOURCE_MAP = "Results/parallel-01/exercises/inventory/20260922T180500Z-2.3-curriculum-v1-source-inventory-evidence/curriculum-source-map.json"
SOURCE_MAP_TSV = "Results/parallel-01/exercises/inventory/20260922T180500Z-2.3-curriculum-v1-source-inventory-evidence/curriculum-source-map.tsv"
INVENTORY = "Results/parallel-01/exercises/inventory/20260922T180500Z-2.3-curriculum-v1-source-inventory-evidence/source-inventory.json"
COVERAGE = "Results/parallel-01/exercises/conversion/20260923T021155Z-2.3.1.3.1-pdf-txt-passage-coverage-r01-evidence/pdf-txt-coverage-report.json"
PACKAGE = "Content/controls/curriculum-v1/package.json"
P01_CANDIDATE = "Results/parallel-01/exercises/conversion/20260923T032643Z-2.3.1.3.1-pdf-source-appendices-levels-088-089-r01-evidence/levels-088-089-pdf-source-candidate.json"
P01_RESULT = "Results/parallel-01/exercises/conversion/20260923T032643Z-2.3.1.3.1-pdf-source-appendices-levels-088-089-r01-results.md"
P03_CANDIDATE_A = "Build/parallel-03/2.3.1.3.1-level-088-whole-source-index-r01/candidate-a.json"
P03_CANDIDATE_B = "Build/parallel-03/2.3.1.3.1-level-088-whole-source-index-r01/candidate-b.json"
P03_RESULT = "Results/parallel-03/exercises/conversion/20260923T162344Z-2.3.1.3.1-level088-whole-source-index-r01-results.md"
P03_PROMPT = "Prompts/parallel-03/exercises/conversion/20260923T162344Z-2.3.1.3.1-level088-whole-source-index-r01-prompt.md"
SCHEMA = "Results/primary/20260912T100538Z-2.1.1.2.1-r02-evidence/schema-freeze.json"
M1_ACCEPTANCE = "Results/primary/20260912T092802Z-11.4.1.1.1-r03-evidence/acceptance.json"
P02_REVIEW = "Results/parallel-02/review/20260923T040740Z-independent-review-parallel-01-levels-088-089-root-guard-r13-results.md"
WBS = "Fathom-Master-WBS-v1.0.md"
CHECKPOINT = "Results/primary/Fathom-Loop-State.md"

PINNED: dict[str, tuple[int | None, str]] = {
    TXT: (1489, "0cbaa5ea7950658dc89eec8b484792d05a640d9532ef7add0442b571a07a2aac"),
    PDF: (40992, "c2e71c0f2391c29d713f6992c9149e43ec599f9eb1cd1f08bf09d915f1a8971f"),
    SOURCE_MAP: (199753, "bad5581a04f43ba8baf14db430449e1ccff5cf88f0f7e42198328073b27053d6"),
    SOURCE_MAP_TSV: (68536, "f526ff4d9ce3bceaf9a7cc581a3ac2aee2c74917eba984dd57913adba574c123"),
    INVENTORY: (36518, "9c216852ddab1151745a9617f9ff3725a8fcd4608fd7d6915e8a04864bb54f73"),
    COVERAGE: (3123277, "968318ab8d5559b742b2871e217d254fe424d6ee5efa72c084d91d44962b7631"),
    PACKAGE: (24698658, "766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255"),
    P01_CANDIDATE: (59361, "810f844e8a901cf5a325280861ea78f048ae24e39ef78fa2943a342585ae6607"),
    P01_RESULT: (5143, "2971202d929f94042fe332764ca4c8b5b57180ff70633671bfa47781806a99fe"),
    P03_CANDIDATE_A: (99843, "96d9ccbe08fc38c020c9a982e1ddf3c6419128ed39ceaffc7774d8c20dcbeecc"),
    P03_CANDIDATE_B: (99843, "96d9ccbe08fc38c020c9a982e1ddf3c6419128ed39ceaffc7774d8c20dcbeecc"),
    P03_RESULT: (None, "b07f9d1f6ae7f5a477a25a7cf0ebaf5f98a105bc930450857cef523fa9efcec7"),
    P03_PROMPT: (None, "ea4534bf3ea9ab2b42e474d02e263080beda9ecf847356805e31f8f9709fafd3"),
    SCHEMA: (2737, "0659fa962a5c933a2bcf3045772b6fe5b05b4deefb3511f5dcb68af51088de95"),
    M1_ACCEPTANCE: (2745, "730fa18677abf1a4feb802bb135d70b8b8b261b637e6703e8f3290dceace63ce"),
    P02_REVIEW: (2617, "fabbd522cc9caaac3700cb56f2c64081fe3cadd1483112285b20c8b1bb5045a8"),
    PROMPT_REL: (None, "593269b4294119ea5d1d6e0daa2d3f5fa833ff98afff356a7d989c188789ee21"),
}

EXPECTED_PAGE_HASHES = {
    1: "f78c379c94751365c9c57803b384d3275e21fd52e81ccdb69c425c4fd069b276",
    2: "359de03506d0f68d2743286587712f2230283d2f8250d6a96580c4101aeb3500",
    3: "9eebb6d7221fe6619f748fa82d087f3c486e72e54107c613b2d13d7442b9edec",
    4: "0adb8992f1bd0b58151f820a9f53129b8ac5f51deb827e3215450ed98895a5b8",
    5: "361e6d774ec8b2e815167f8720ae0ad3abd313ae1c04e28f9e9969d28bcafaab",
    6: "eeafc558d01ebfaf61eff1f5f4469a0236a71fc8225ac6188210b32beea7f44a",
    7: "3e7727f897c2b9d1a390fef625c88b7122e7cc1916bb973fa200b0b1b018fe6a",
    8: "5c3fe24752ab660fc0c816a70ca62a34f89980600622180ddb74dee7c8af015a",
    9: "204c84520a3f2692ae4bf5bdb1a6a4d125587cd3761b51abc7b88caa62c991d7",
    10: "c2db1906fd486d1c6142a10661009df0fe3182475db86386a713d3d94f3be91b",
    11: "6fb535c7a4592a276da3bebd69ecbab1f467ff1eb533ae51c6ff30cd612e5ce3",
    12: "715618cf8bc69352e843e1cb81cb99a30132d5f3dd0ddfe8f01a758878fc411d",
    13: "78977343125b3e23b0220c36809d4cbffed79cd510d899371acc00f11b46592a",
    14: "531586caf8f3a3ffee074a6c8fc27ceb0f4f9bffdd91a504d71c21e8d689cb2a",
    15: "dcc33314615f5f604a6215ebef816c40d72b8c3ca8d30cd0790e3f3cb21fa2d1",
}

EXPECTED_MODULES = (
    ("A", "Eighth-note drive and palm-mute depth", 160, 3, "Module A - Eighth-Note Drive and Mute Depth"),
    ("B", "Gallop and reverse-gallop control", 144, 4, "Module B - Gallops and Reverse Gallops"),
    ("C", "Pedal-tone riffs and chord punctuation", 160, 5, "Module C - Pedal-Tone Riffs"),
    ("D", "Power-chord displacement and syncopation", 144, 6, "Module D - Power-Chord Displacement"),
    ("E", "Accent architecture and riff identity", 128, 7, "Module E - Accent Architecture"),
    ("F", "Open/muted contrast and section lift", 128, 8, "Module F - Open/Muted Contrast and Section Lift"),
    ("G", "Riff construction and variation", 160, 9, "Module G - Riff Construction and Variation"),
    ("H", "Four eight-bar rock/metal studies", 192, 10, "Module H - Study 1 - Rock eighth-note drive"),
    ("I", "Thirty-two-bar riff-performance capstone", 256, 14, "Module I - Thirty-Two-Bar Riff-Performance Capstone"),
    ("J", "Recovery and groove audit", 64, 15, "Module J - Recovery and Groove Audit"),
)

H_PASS_REQUIREMENTS = (
    "one muted root only",
    "add accents",
    "add power chords",
    "add mute-depth changes",
    "add section dynamics",
    "record clean tone, then gain tone",
)

TASK_SPECS: dict[str, dict[str, Any]] = {
    "A": {
        "unit_kind": "pass",
        "rows": [
            ("1", "M M M M M M M M", "heavy mute; short low-E pitch"),
            ("2", "M M M M M M M M", "medium mute; more fundamental"),
            ("3", "M M M M M M M M", "light mute; near-open"),
            ("4", "O O O O O O O O", "fully open reference"),
            ("5", "M M M M O O O O", "verse-to-chorus lift"),
            ("6", "M O M O M O M O", "alternating mute/open"),
            ("7", ">M M >M M >M M >M M", "accents every two eighths"),
            ("8", ">M M M >M M M >M M", "3+3+2 accent feel"),
        ],
        "field_names": ("pass", "grid_literal", "mute_target_literal"),
        "guidance": ("Use E5, A5, D5, and G5. The mute changes timbre and duration, not tempo.",),
    },
    "B": {
        "unit_kind": "cell",
        "rows": [
            ("1", "M - M M", "D - D U"),
            ("2", "M M - M", "D U - U"),
            ("3", "M M M -", "D U D -"),
            ("4", "- M M M", "- U D U"),
            ("5", "M - M M | M - M M", "repeat without reset"),
            ("6", "M M - M | M M - M", "reverse-gallop continuity"),
            ("7", "M - M M | M M - M", "alternate gallop/reverse"),
            ("8", ">M - M M | M - >M M", "accent displacement"),
        ],
        "field_names": ("cell", "sixteenth_grid_literal", "picking_goal_literal"),
        "guidance": (
            "Count each beat as 1 e & a. Gallop = long-short-short; reverse gallop = short-short-long.",
            "Begin on one string. Then move the final attack of each beat to a power chord while the pedal note remains muted.",
        ),
    },
    "C": {
        "unit_kind": "riff",
        "rows": [
            ("1", "E pedal", "G5-A5", "E E G5 E | E E A5 E"),
            ("2", "E pedal", "D5-C5", "E E E D5 | E C5 E E"),
            ("3", "A pedal", "C5-D5", "A A C5 A | A A D5 A"),
            ("4", "D pedal", "F5-G5", "D D F5 D | D G5 D D"),
            ("5", "E pedal", "F5-G5-A5", "E F5 E G5 | E A5 G5 E"),
            ("6", "E pedal", "D5-A5", "gallop pedal + chord on beat 4"),
        ],
        "field_names": ("riff", "pedal_literal", "chord_punctuation_literal", "pattern_literal"),
        "guidance": ("Mute the pedal more heavily than the chord punctuation. The chord should sound like a structural event, not merely a louder version of the pedal.",),
    },
    "D": {
        "unit_kind": "cell",
        "rows": [
            ("1", "1, 2, 3, 4", "downbeat reference"),
            ("2", "&, &, &, &", "offbeat power chords"),
            ("3", "1, &2, 3, &4", "alternating placement"),
            ("4", "&1, 2, &3, 4", "reverse displacement"),
            ("5", "1, a2, &3, 4", "late-sixteenth tension"),
            ("6", "a1, 2, a3, 4", "pickup-driven riff"),
            ("7", "1, &2, a3, &4", "syncopated hard-rock cell"),
            ("8", "&1, a2, &3, a4", "high-displacement test"),
        ],
        "field_names": ("cell", "chord_attacks_literal", "purpose_literal"),
        "guidance": ("Use E5-G5-A5-D5. Keep a muted low-E sixteenth grid underneath the chord attacks.",),
    },
    "E": {
        "unit_kind": "accent_cycle",
        "rows": [
            ("2", "1 0 1 0 1 0 1 0 ...", "square drive"),
            ("3", "1 0 0 1 0 0 1 0 ...", "cross-bar 3 grouping"),
            ("4", "1 0 0 0 ...", "quarter-note landmarks"),
            ("5", "1 0 0 0 0 1 ...", "longer cross-bar cycle"),
            ("3+3+2", "1 0 0 1 0 0 1 0", "asymmetrical bar identity"),
            ("2+2+4", "1 0 1 0 1 0 0 0", "front-loaded bar"),
        ],
        "field_names": ("accent_cycle_literal", "attack_pattern_literal", "effect_literal"),
        "guidance": ("16 eighth-note attacks", "Accent cycles are first played on one pitch, then mapped to chord changes. Do not move the barline to follow the accent."),
        "partial_patterns": ("2", "3", "4", "5"),
    },
    "F": {
        "unit_kind": "section_texture",
        "rows": [
            ("Verse", "heavy palm mute", "short punctuation", "mp"),
            ("Pre-chorus", "medium mute", "more frequent power chords", "mf"),
            ("Chorus", "light/open", "longer chord sustain", "f"),
            ("Breakdown", "heavy mute + rests", "low-register hits", "f but sparse"),
            ("Bridge", "mixed mute", "syncopated chords", "mf"),
            ("Outro", "open then progressively muted", "final sustained tonic", "f -> p"),
        ],
        "field_names": ("section_literal", "pedal_behavior_literal", "chord_behavior_literal", "dynamic_literal"),
        "guidance": ("Use the same E5-G5-A5-D5 harmony through all six textures. Section identity must come from orchestration, not new chords.",),
    },
    "G": {
        "unit_kind": "riff_example",
        "rows": [
            ("Riff A", "E E G5 E | E A5 G5 E", "pedal + punctuation"),
            ("Riff B", "E - E E | G5 E A5 E", "gallop"),
            ("Riff C", "E E E D5 | E C5 D5 E", "descending chord answer"),
            ("Riff D", "E G5 E A5 | E - D5 E", "displaced power chords"),
            ("Riff E", "E E G5 A5 | E E D5 E", "two-chord climax"),
            ("Riff F", "E F5 E G5 | A5 G5 E -", "chromatic/diatonic color"),
            ("Riff G", "E E E E | G5 - A5 -", "density contrast"),
            ("Riff H", "E - G5 - | A5 E D5 E", "space-heavy riff"),
        ],
        "field_names": ("riff_label", "cell_literal", "identity_literal"),
        "guidance": ("For each riff create exactly three variations: change accent only; change final chord only; change note density only. Preserve the original rhythmic identity.",),
        "variation_types": ("change accent only", "change final chord only", "change note density only"),
    },
    "H": {
        "unit_kind": "study",
        "rows": [
            ("Study 1 - Rock eighth-note drive", "| E5 | G5 | A5 | E5 | E5 | D5 | A5 | E5 |", "steady eighths; medium mute; open chorus hits"),
            ("Study 2 - Hard-rock pedal riff", "| E5 | G5 A5 | E5 | D5 | E5 | G5 | A5 D5 | E5 |", "low-E pedal plus chord punctuation"),
            ("Study 3 - Gallop study", "| E5 | E5 | G5 | A5 | E5 | D5 | A5 | E5 |", "gallop verse; reverse-gallop response"),
            ("Study 4 - Breakdown/chorus contrast", "| E5 | D5 | C5 | B5 | E5 | G5 | A5 | E5 |", "bars 1-4 sparse breakdown; 5-8 open chorus"),
        ],
        "field_names": ("study_label", "chord_cells_literal", "descriptor_literal"),
        "guidance": (),
        "shared_pass_requirements": H_PASS_REQUIREMENTS,
        "unresolved": "The TXT calls these four eight-bar studies. Do not assign each extracted chord cell to an event, bar, or count unit; only Study 4 explicitly names bars 1-4 and 5-8 in its descriptor.",
    },
    "I": {
        "unit_kind": "capstone_segment",
        "rows": [
            ("1-4", "E5-G5-A5-E5", "rock drive", "medium mute", "mf"),
            ("5-8", "E pedal + G5/A5", "hard rock", "pedal punctuation", "mf"),
            ("9-12", "E5-G5-A5-D5", "gallop", "heavy mute", "f"),
            ("13-16", "E5-D5-C5-B5", "breakdown", "rests + low hits", "f"),
            ("17-20", "E5-G5-A5-E5", "open chorus", "light/open", "f"),
            ("21-24", "E pedal + D5/C5", "reverse gallop", "heavy/medium", "mf"),
            ("25-28", "E5-G5-A5-D5", "syncopated riff", "displaced chords", "f"),
            ("29-32", "E5-D5-A5-E5", "outro", "open -> mute -> sustain", "f -> p"),
        ],
        "field_names": ("bar_range_literal", "harmony_literal", "riff_role_literal", "texture_literal", "dynamic_literal"),
        "guidance": ("One master tempo. No neutral bar between sections. The last bar of each section must prepare the next mute depth, register, and rhythmic behavior.",),
    },
    "J": {
        "unit_kind": "failure_repair",
        "rows": [
            ("Palm mute kills pitch", "move hand slightly away from bridge; reduce pressure"),
            ("Gallop rushes", "one beat at a time; foot marks quarter notes"),
            ("Pedal/chord balance unclear", "mute pedal harder; open chord punctuation"),
            ("Power-chord shift late", "end pedal one sixteenth early, then restore full cell"),
            ("Accent changes tempo", "play all notes equal, then re-add accent"),
            ("Breakdown becomes slower", "keep silent subdivision with picking hand/foot"),
            ("Gain hides articulation", "return to clean tone and reduce note density"),
            ("Form lost", "quarter-note E pedal until next 4-bar boundary"),
        ],
        "field_names": ("failure_literal", "immediate_repair_literal"),
        "guidance": (),
    },
}

PDF_PAGE_HEADINGS = {
    1: "Guitar Exercises - Section XII, Level 88",
    2: "Reference - Attack and Mute Vocabulary",
    3: "Module A - Eighth-Note Drive and Mute Depth",
    4: "Module B - Gallops and Reverse Gallops",
    5: "Module C - Pedal-Tone Riffs",
    6: "Module D - Power-Chord Displacement",
    7: "Module E - Accent Architecture",
    8: "Module F - Open/Muted Contrast and Section Lift",
    9: "Module G - Riff Construction and Variation",
    10: "Module H - Study 1 - Rock eighth-note drive",
    11: "Module H - Study 2 - Hard-rock pedal riff",
    12: "Module H - Study 3 - Gallop study",
    13: "Module H - Study 4 - Breakdown/chorus contrast",
    14: "Module I - Thirty-Two-Bar Riff-Performance Capstone",
    15: "Module J - Recovery and Groove Audit",
}

PDF_TABLE_HEADERS = {
    "A": ("Pass", "Grid", "Mute target"),
    "B": ("Cell", "Sixteenth grid", "Picking goal"),
    "C": ("Riff", "Pedal", "Chord punctuation", "Pattern"),
    "D": ("Cell", "Chord attacks", "Purpose"),
    "E": ("Accent cycle", "Effect"),
    "F": ("Section", "Pedal behavior", "Chord behavior", "Dynamic"),
    "G": ("Riff", "Cell", "Identity"),
    "I": ("Bars", "Harmony", "Riff role", "Texture", "Dynamic"),
    "J": ("Failure", "Immediate repair"),
}

CAPSTONE_TXT_MOTIFS = (
    "rock drive",
    "hard-rock pedal riff",
    "gallops",
    "breakdown",
    "open chorus",
    "reverse gallop",
    "syncopated riff",
    "outro",
)
CAPSTONE_PDF_ROLES = (
    "rock drive",
    "hard rock",
    "gallop",
    "breakdown",
    "open chorus",
    "reverse gallop",
    "syncopated riff",
    "outro",
)
CAPSTONE_ROWS = (
    ("1-4", "E5-G5-A5-E5", "rock drive", "medium mute", "mf"),
    ("5-8", "E pedal + G5/A5", "hard rock", "pedal punctuation", "mf"),
    ("9-12", "E5-G5-A5-D5", "gallop", "heavy mute", "f"),
    ("13-16", "E5-D5-C5-B5", "breakdown", "rests + low hits", "f"),
    ("17-20", "E5-G5-A5-E5", "open chorus", "light/open", "f"),
    ("21-24", "E pedal + D5/C5", "reverse gallop", "heavy/medium", "mf"),
    ("25-28", "E5-G5-A5-D5", "syncopated riff", "displaced chords", "f"),
    ("29-32", "E5-D5-A5-E5", "outro", "open -> mute -> sustain", "f -> p"),
)
TXT_MODULE_RE = re.compile(r"([A-J])\. (.+) - ([0-9]+) events")


class CandidateError(ValueError):
    pass


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def safe_input(root: Path, relative: str) -> Path:
    rel = Path(relative)
    if rel.is_absolute() or not rel.parts or any(part in ("", ".", "..") for part in rel.parts):
        raise CandidateError(f"UNSAFE_INPUT_PATH {relative}")
    current = root
    for part in rel.parts:
        current = current / part
        if current.is_symlink():
            raise CandidateError(f"INPUT_SYMLINK {relative}")
    try:
        path = (root / rel).resolve(strict=True)
    except OSError as exc:
        raise CandidateError(f"INPUT_MISSING {relative}: {exc}") from exc
    if not path.is_relative_to(root) or not path.is_file() or not stat.S_ISREG(path.stat().st_mode):
        raise CandidateError(f"INPUT_NOT_REGULAR_OR_ESCAPES_ROOT {relative}")
    return path


def assert_git_root(root: Path) -> None:
    try:
        root = root.resolve(strict=True)
    except OSError as exc:
        raise CandidateError(f"GIT_ROOT_UNAVAILABLE {exc}") from exc
    proc = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise CandidateError(f"GIT_ROOT_UNAVAILABLE {proc.stderr.strip()}")
    actual = Path(proc.stdout.strip()).resolve(strict=True)
    if actual != root:
        raise CandidateError(f"GIT_ROOT_MISMATCH expected-top-level={actual} supplied={root}")


def read_pinned_inputs(root: Path) -> tuple[dict[str, bytes], dict[str, dict[str, Any]]]:
    raw_inputs: dict[str, bytes] = {}
    identities: dict[str, dict[str, Any]] = {}
    for relative, (expected_size, expected_sha) in PINNED.items():
        identity_path = str(relative)
        raw = safe_input(root, relative).read_bytes()
        actual_sha = sha(raw)
        if (expected_size is not None and len(raw) != expected_size) or actual_sha != expected_sha:
            raise CandidateError(f"PINNED_INPUT_DRIFT {relative}")
        raw_inputs[identity_path] = raw
        identities[identity_path] = {"bytes": len(raw), "sha256": actual_sha}
    return raw_inputs, identities


def parse_txt(txt_raw: bytes) -> dict[str, Any]:
    try:
        text = txt_raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CandidateError("TXT_NOT_UTF8") from exc
    if "\r" in text or not text.endswith("\n"):
        raise CandidateError("TXT_LINE_ENDING_OR_TERMINAL_NEWLINE")
    lines = text.splitlines()
    if len(lines) != 43:
        raise CandidateError(f"TXT_LINE_COUNT {len(lines)}")
    expected_literals = {
        4: "LEVEL 88 OF 105 - HARD STOP AFTER LEVEL 105",
        10: "COMPLETE WRITTEN WORKLOAD: 1536 events",
        12: "MODULES",
        24: "KEY SKILLS",
        35: "CAPSTONE",
        36: "32 bars moving through rock drive, hard-rock pedal riff, gallops, breakdown, open chorus, reverse gallop, syncopated riff, and outro at one tempo.",
        38: "MASTERY",
        39: "14/16 or better on two separate days.",
        40: "No zero in pulse, gallop control, pedal/chord balance, or recovery.",
        42: "NEXT",
        43: "Level 89: country, Americana, and hybrid-picking groove principles.",
    }
    for line_number, expected in expected_literals.items():
        if lines[line_number - 1] != expected:
            raise CandidateError(f"TXT_LITERAL_DRIFT line={line_number}")
    modules = []
    for line_number, expected in enumerate(EXPECTED_MODULES, 13):
        match = TXT_MODULE_RE.fullmatch(lines[line_number - 1])
        if not match or (match.group(1), match.group(2), int(match.group(3))) != expected[:3]:
            raise CandidateError(f"TXT_MODULE_DRIFT line={line_number}")
        modules.append({
            "module_label": expected[0],
            "title_literal": expected[1],
            "declared_workload": {"value": expected[2], "unit_literal": "events"},
            "txt_line_number": line_number,
            "source_line_sha256": sha(lines[line_number - 1].encode("utf-8")),
        })
    if sum(item["declared_workload"]["value"] for item in modules) != 1536:
        raise CandidateError("TXT_TOTAL_ARITHMETIC_DRIFT")
    return {
        "line_count": len(lines),
        "hard_stop_line": 4,
        "declared_total": {"value": 1536, "unit_literal": "events", "line_number": 10},
        "modules": modules,
        "capstone_statement": {
            "line_number": 36,
            "literal": lines[35],
            "ordered_motifs": list(CAPSTONE_TXT_MOTIFS),
        },
        "mastery_literals": [lines[38], lines[39]],
        "next_level_boundary": {"line_number": 43, "literal": lines[42]},
    }


def parse_json(raw: bytes, name: str) -> dict[str, Any]:
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CandidateError(f"JSON_INVALID {name}") from exc
    if not isinstance(data, dict):
        raise CandidateError(f"JSON_ROOT_NOT_OBJECT {name}")
    return data


def exactly_one(rows: list[dict[str, Any]], predicate, name: str) -> dict[str, Any]:
    found = [row for row in rows if predicate(row)]
    if len(found) != 1:
        raise CandidateError(f"EXPECTED_ONE {name} got={len(found)}")
    return found[0]


def verify_sources(root: Path) -> dict[str, Any]:
    assert_git_root(root)
    raw, identities = read_pinned_inputs(root)
    txt = parse_txt(raw[TXT])
    source_map = parse_json(raw[SOURCE_MAP], SOURCE_MAP)
    inventory = parse_json(raw[INVENTORY], INVENTORY)
    coverage = parse_json(raw[COVERAGE], COVERAGE)
    package = parse_json(raw[PACKAGE], PACKAGE)
    p01 = parse_json(raw[P01_CANDIDATE], P01_CANDIDATE)
    p03 = parse_json(raw[P03_CANDIDATE_A], P03_CANDIDATE_A)
    p03_b = parse_json(raw[P03_CANDIDATE_B], P03_CANDIDATE_B)

    if sha(raw[P03_CANDIDATE_A]) != sha(raw[P03_CANDIDATE_B]):
        raise CandidateError("P03_TWIN_CANDIDATES_DIFFER")
    if inventory.get("source_count") != 105 or source_map.get("base_inventory_sha256") != identities[INVENTORY]["sha256"]:
        raise CandidateError("SOURCE_INVENTORY_BINDING_DRIFT")

    source_row = exactly_one(source_map["rows"], lambda row: row.get("level") == 88, "source map Level88")
    if (
        source_row.get("wbs_owner") != "2.3.1.3.1"
        or source_row.get("txt_path") != TXT
        or source_row.get("pdf_path") != PDF
        or source_row.get("txt_bytes") != len(raw[TXT])
        or source_row.get("txt_sha256") != identities[TXT]["sha256"]
        or source_row.get("pdf_bytes") != len(raw[PDF])
        or source_row.get("pdf_sha256") != identities[PDF]["sha256"]
        or source_row.get("representative_status") != "outside_representative_package"
        or source_row.get("review") != "Pending"
        or source_row.get("conversion_status") != "not_converted"
        or source_row.get("stable_ids_assigned") is not False
        or source_row.get("runtime_eligible") is not False
        or source_row.get("imported") is not False
        or source_row.get("admitted") is not False
    ):
        raise CandidateError("SOURCE_MAP_LEVEL88_STATUS_OR_BINDING_DRIFT")

    workbook_catalog = package.get("workbook_catalog", {})
    if (
        package.get("content_version") != "curriculum-v1-level009-659-build-only-candidate.1"
        or len(package.get("records", [])) != 659
        or workbook_catalog.get("catalog_version") != "curriculum-v1-workbook-source-catalog.5"
    ):
        raise CandidateError("CURRENT_PACKAGE_VERSION_DRIFT")
    entry = exactly_one(workbook_catalog.get("entries", []), lambda row: row.get("workbook_id") == "fg:workbook:000088", "catalog Level88")
    if (
        entry.get("review") != "Pending"
        or entry.get("conversion_status") != "not_converted"
        or entry.get("runtime_eligible") is not False
        or entry.get("runtime_admitted") is not False
        or entry.get("imported") is not False
        or entry.get("admitted") is not False
        or entry.get("whole_workbook_complete") is not False
        or entry.get("representative_status") != "outside_representative_package"
    ):
        raise CandidateError("CATALOG_LEVEL88_STATUS_DRIFT")
    if entry.get("txt", {}).get("sha256") != identities[TXT]["sha256"] or entry.get("pdf", {}).get("bytes") != len(raw[PDF]):
        raise CandidateError("CATALOG_SOURCE_BINDING_DRIFT")
    projection = entry.get("playable_projection", {})
    if (
        projection.get("status") != "explicitly_empty_unresolved"
        or any(projection.get(key) for key in ("events", "items", "modules", "passages", "records", "variants"))
    ):
        raise CandidateError("CATALOG_PLAYABLE_PROJECTION_NOT_EMPTY")

    pdf_pages = entry.get("pdf", {}).get("pages", [])
    if len(pdf_pages) != 15 or entry.get("pdf", {}).get("page_count") != 15:
        raise CandidateError("CATALOG_PAGE_COUNT_DRIFT")
    p01_workbook = exactly_one(p01.get("workbooks", []), lambda row: row.get("level") == 88, "P01 Level88 appendix")
    if p01_workbook.get("page_count") != 15 or len(p01_workbook.get("pages", [])) != 15:
        raise CandidateError("P01_PAGE_COUNT_DRIFT")
    p03_pages = p03.get("pdf", {}).get("pages", [])
    if len(p03_pages) != 15:
        raise CandidateError("P03_PAGE_COUNT_DRIFT")
    for number in range(1, 16):
        expected_hash = EXPECTED_PAGE_HASHES[number]
        if (
            entry["pdf"]["pages"][number - 1].get("page_number") != number
            or entry["pdf"]["pages"][number - 1].get("extracted_text_sha256") != expected_hash
            or p01_workbook["pages"][number - 1].get("literal_extracted_text_sha256") != expected_hash
            or p03_pages[number - 1].get("literal_extracted_text_sha256") != expected_hash
        ):
            raise CandidateError(f"PREDECESSOR_PAGE_HASH_DRIFT page={number}")

    if p03.get("candidate_status") != "pending_source_reconciliation" or p03.get("current_source_status", {}).get("review") != "Pending":
        raise CandidateError("P03_STATUS_DRIFT")
    if any(p03.get(flag) is not False for flag in ("canonical_ids_allocated", "canonical_record_emitted", "runtime_eligible", "imported", "admitted", "whole_workbook_complete")):
        raise CandidateError("P03_RUNTIME_BOUNDARY_DRIFT")

    coverage_workbook = exactly_one(coverage.get("workbooks", []), lambda row: row.get("level") == 88, "lexical coverage Level88")
    if coverage_workbook.get("page_classification_counts") != {
        "no_exact_five_token_window_found": 6,
        "partial_literal_overlap": 9,
    }:
        raise CandidateError("LEXICAL_COVERAGE_COUNTS_DRIFT")

    try:
        import pypdf
        from pypdf import PdfReader
    except ImportError as exc:
        raise CandidateError("PYPDF_UNAVAILABLE") from exc
    if pypdf.__version__ != "6.10.0":
        raise CandidateError(f"PYPDF_VERSION_DRIFT {pypdf.__version__}")
    from io import BytesIO
    pages = [page.extract_text() or "" for page in PdfReader(BytesIO(raw[PDF])).pages]
    if len(pages) != 15:
        raise CandidateError(f"PDF_PAGE_COUNT {len(pages)}")
    appendix_pages = p01_workbook["pages"]
    for index, page_text in enumerate(pages):
        number = index + 1
        page_hash = sha(page_text.encode("utf-8"))
        if page_hash != EXPECTED_PAGE_HASHES[number]:
            raise CandidateError(f"PDF_PAGE_TEXT_HASH_DRIFT page={number}")
        if page_text != pdf_pages[index].get("extracted_text"):
            raise CandidateError(f"CATALOG_PAGE_TEXT_DRIFT page={number}")
        if page_text != appendix_pages[index].get("literal_extracted_text"):
            raise CandidateError(f"P01_PAGE_TEXT_DRIFT page={number}")
        if p03_pages[index].get("literal_extracted_text_sha256") != page_hash:
            raise CandidateError(f"P03_PAGE_TEXT_DRIFT page={number}")
        heading = PDF_PAGE_HEADINGS[number]
        if heading not in page_text:
            raise CandidateError(f"PDF_HEADING_DRIFT page={number}")

    index_rows = p03.get("pdf", {}).get("module_index", {}).get("rows", [])
    if len(index_rows) != 10:
        raise CandidateError("P03_MODULE_INDEX_COUNT_DRIFT")
    for index, expected in enumerate(EXPECTED_MODULES):
        row = index_rows[index]
        if (
            row.get("module_label") != expected[0]
            or row.get("pdf_index_title_literal") != expected[1]
            or row.get("pdf_index_workload_literal") != str(expected[2])
        ):
            raise CandidateError(f"P03_MODULE_INDEX_DRIFT module={expected[0]}")
    if p03.get("pdf", {}).get("module_index", {}).get("module_workload_sum") != 1536:
        raise CandidateError("P03_MODULE_TOTAL_DRIFT")

    return {
        "raw": raw,
        "identities": identities,
        "txt": txt,
        "source_map_row": source_row,
        "catalog_entry": entry,
        "coverage_workbook": coverage_workbook,
        "p01_workbook": p01_workbook,
        "p03_candidate": p03,
        "p03_candidate_b": p03_b,
        "pdf_pages": pages,
    }


def ensure_fragments_in_order(page_text: str, fragments: list[str], page: int) -> None:
    cursor = 0
    for fragment in fragments:
        position = page_text.find(fragment, cursor)
        if position < 0:
            raise CandidateError(f"PDF_TASK_FRAGMENT_MISSING page={page} fragment={fragment!r}")
        cursor = position + len(fragment)


def build_task_rows(module: str, page_text: str, page: int, page_hash: str) -> list[dict[str, Any]]:
    spec = TASK_SPECS[module]
    fragments = [PDF_PAGE_HEADINGS[page]]
    if module == "B":
        # Page 4 prints one instruction before the table and the other after it.
        fragments.append(spec["guidance"][0])
        fragments.extend(PDF_TABLE_HEADERS[module])
    elif module == "E":
        # Page 7 places one instruction between its two table headers.
        fragments.append(PDF_TABLE_HEADERS[module][0])
        fragments.append(spec["guidance"][0])
        fragments.append(PDF_TABLE_HEADERS[module][1])
    else:
        fragments.extend(PDF_TABLE_HEADERS[module])
    rows = spec["rows"]
    output = []
    if module == "H":
        for ordinal, row in enumerate(rows, 1):
            label, chord_cells, descriptor = row
            fragments.extend([label, chord_cells, descriptor, "Pass", "Requirement"])
            fragments.extend(f"{index}" for index in range(1, 7))
            fragments.extend(H_PASS_REQUIREMENTS)
            output.append({
                "task_unit_ordinal": ordinal,
                "task_unit_kind": "study",
                "fields": dict(zip(spec["field_names"], row)),
                "pass_requirements": [
                    {"pass_ordinal": number, "requirement_literal": text}
                    for number, text in enumerate(H_PASS_REQUIREMENTS, 1)
                ],
                "source_ref": {"page_number": page + ordinal - 1, "page_text_sha256": EXPECTED_PAGE_HASHES[page + ordinal - 1]},
            })
        # Study headings/chord cells and pass scaffold are checked page-by-page outside this call.
        return output

    for ordinal, row in enumerate(rows, 1):
        fragments.extend(row)
        output.append({
            "task_unit_ordinal": ordinal,
            "task_unit_kind": spec["unit_kind"],
            "fields": dict(zip(spec["field_names"], row)),
            "source_ref": {
                "page_number": page,
                "page_text_sha256": page_hash,
                "table_row_ordinal": ordinal,
            },
        })
    if module in {"B", "E"}:
        fragments.append(spec["guidance"][1])
    else:
        fragments.extend(spec.get("guidance", ()))
    ensure_fragments_in_order(page_text, fragments, page)
    return output


def build_candidate(root: Path = ROOT) -> dict[str, Any]:
    source = verify_sources(root)
    page_hashes = EXPECTED_PAGE_HASHES
    modules = []
    for index, (label, title, workload, page, heading) in enumerate(EXPECTED_MODULES):
        page_text = source["pdf_pages"][page - 1]
        spec = TASK_SPECS[label]
        if label == "H":
            studies = []
            for study_ordinal, (study_label, chord_cells, descriptor) in enumerate(spec["rows"], 1):
                study_page = page + study_ordinal - 1
                study_text = source["pdf_pages"][study_page - 1]
                ensure_fragments_in_order(study_text, [
                    PDF_PAGE_HEADINGS[study_page], chord_cells, descriptor, "Pass", "Requirement",
                    *[fragment for number, requirement in enumerate(H_PASS_REQUIREMENTS, 1) for fragment in (str(number), requirement)],
                ], study_page)
                studies.append({
                    "task_unit_ordinal": study_ordinal,
                    "task_unit_kind": "study",
                    "fields": dict(zip(spec["field_names"], (study_label, chord_cells, descriptor))),
                    "pass_requirements": [
                        {"pass_ordinal": n, "requirement_literal": req}
                        for n, req in enumerate(H_PASS_REQUIREMENTS, 1)
                    ],
                    "source_ref": {"page_number": study_page, "page_text_sha256": page_hashes[study_page]},
                })
            task_rows = studies
            guidance = list(spec.get("shared_pass_requirements", ()))
        else:
            task_rows = build_task_rows(label, page_text, page, page_hashes[page])
            guidance = list(spec.get("guidance", ()))

        txt_module = source["txt"]["modules"][index]
        p03_crosswalk = source["p03_candidate"]["module_crosswalk"][index]
        if p03_crosswalk.get("module_label") != label or p03_crosswalk.get("txt_summary_title_literal") != title:
            raise CandidateError(f"P03_CROSSWALK_DRIFT module={label}")
        detail_pages = [10, 11, 12, 13] if label == "H" else [page]
        modules.append({
            "module_label": label,
            "title_relationship": {
                "txt_title_literal": title,
                "pdf_p1_title_literal": p03_crosswalk["pdf_p1_index_title_literal"],
                "pdf_detail_heading_literals": [PDF_PAGE_HEADINGS[n] for n in detail_pages],
                "link_basis": "Explicit printed A-J module letter/index relation and PDF detail heading.",
                "titles_exactly_equal": all(PDF_PAGE_HEADINGS[n] == title for n in detail_pages),
            },
            "declared_workload": txt_module["declared_workload"],
            "pdf_index_workload": {"value": workload, "unit_literal": "events", "page_number": 1},
            "task_unit_kind": spec["unit_kind"],
            "task_unit_count": len(task_rows),
            "task_rows": task_rows,
            "explicit_guidance_literals": guidance,
            "source_task_to_event_mapping": None,
            "source_ref": {
                "txt_line_number": txt_module["txt_line_number"],
                "pdf_detail_pages": detail_pages,
                "pdf_page_text_sha256": {str(n): page_hashes[n] for n in detail_pages},
            },
        })

    capstone_segments = []
    for ordinal, (txt_motif, row) in enumerate(zip(CAPSTONE_TXT_MOTIFS, CAPSTONE_ROWS), 1):
        bars, harmony, pdf_role, texture, dynamic = row
        capstone_segments.append({
            "sequence_ordinal": ordinal,
            "txt_motif_literal": txt_motif,
            "pdf_riff_role_literal": pdf_role,
            "pdf_fields": {
                "bar_range_literal": bars,
                "harmony_literal": harmony,
                "texture_literal": texture,
                "dynamic_literal": dynamic,
            },
            "relationship": "ordered motif correspondence only; no event or performance equivalence",
            "source_ref": {"txt_line_number": 36, "pdf_page_number": 14, "pdf_page_text_sha256": page_hashes[14]},
        })
    ensure_fragments_in_order(source["pdf_pages"][13], [
        PDF_PAGE_HEADINGS[14], "Bars", "Harmony", "Riff role", "Texture", "Dynamic",
        *[field for row in CAPSTONE_ROWS for field in row],
        TASK_SPECS["I"]["guidance"][0],
    ], 14)

    index_total = source["p03_candidate"]["pdf"]["module_index"]["module_workload_sum"]
    total_declared = source["txt"]["declared_total"]["value"]
    module_sum = sum(m["declared_workload"]["value"] for m in modules)
    if module_sum != total_declared or index_total != total_declared:
        raise CandidateError("PRINTED_TOTAL_PARITY_DRIFT")

    shared_text = source["pdf_pages"][1]
    shared_symbols = (
        ("O", "open/full power-chord attack", "allow controlled sustain"),
        ("M", "palm-muted pitched attack", "bridge-hand mute; pitch remains clear"),
        ("x", "dead/muted contact", "no stable pitch"),
        ("-", "rest/air stroke", "no contact"),
        (">", "accent", "more attack, not necessarily more duration"),
        ("~", "sustain", "no new attack"),
    )
    ensure_fragments_in_order(shared_text, [
        PDF_PAGE_HEADINGS[2], "Symbol", "Meaning", "Execution",
        *[field for row in shared_symbols for field in row],
        "Practice every rhythm first on one low E note. Add power chords only after the attack pattern is stable.",
    ], 2)

    mastery_match = re.search(r"Mastery: (.*?)(?=\nNext:)", source["pdf_pages"][14], flags=re.DOTALL)
    if not mastery_match:
        raise CandidateError("PDF_MASTERY_TEXT_MISSING")

    return {
        "artifact_type": "detached_level88_semantic_pdf_task_block_candidate",
        "candidate_format_version": 1,
        "candidate_status": "pending_task_to_event_reconciliation",
        "wbs_id": "2.3.1.3.1",
        "workbook_id": "fg:workbook:000088",
        "level": 88,
        "section": "XII",
        "source_review": "Pending",
        "canonical_ids_allocated": False,
        "canonical_record_emitted": False,
        "runtime_eligible": False,
        "runtime_admitted": False,
        "imported": False,
        "admitted": False,
        "whole_workbook_complete": False,
        "input_identities": source["identities"],
        "source_status": {
            "source_map_review": source["source_map_row"]["review"],
            "source_map_conversion_status": source["source_map_row"]["conversion_status"],
            "catalog_review": source["catalog_entry"]["review"],
            "catalog_conversion_status": source["catalog_entry"]["conversion_status"],
            "representative_status": source["source_map_row"]["representative_status"],
            "prior_staging_found_in_map": source["source_map_row"]["prior_staging_found"],
            "prior_staging_used": False,
        },
        "pdf_page_references": [
            {
                "page_number": number,
                "heading_literal": PDF_PAGE_HEADINGS[number],
                "extracted_text_sha256": page_hashes[number],
                "source_path": PDF,
            }
            for number in range(1, 16)
        ],
        "shared_unassigned_reference": {
            "page_number": 2,
            "heading_literal": PDF_PAGE_HEADINGS[2],
            "module_label": None,
            "task_unit_kind": "attack_mute_vocabulary",
            "symbols": [
                {"symbol_literal": symbol, "meaning_literal": meaning, "execution_literal": execution}
                for symbol, meaning, execution in shared_symbols
            ],
            "guidance_literal": "Practice every rhythm first on one low E note. Add power chords only after the attack pattern is stable.",
            "assignment_status": "shared reference; no printed A-J module label",
            "source_ref": {"pdf_page_number": 2, "pdf_page_text_sha256": page_hashes[2]},
        },
        "modules": modules,
        "mastery_comparison": {
            "txt_literals": source["txt"]["mastery_literals"],
            "pdf_literal": mastery_match.group(1),
            "scoring_allocation": None,
            "source_refs": {
                "txt_lines": [39, 40],
                "pdf_page_number": 15,
                "pdf_page_text_sha256": page_hashes[15],
            },
            "interpretation_limit": "Preserve both source statements; scoring-point allocation is not authored.",
        },
        "capstone_order_relation": {
            "txt_line_number": 36,
            "pdf_page_number": 14,
            "txt_motifs": list(CAPSTONE_TXT_MOTIFS),
            "pdf_roles": list(CAPSTONE_PDF_ROLES),
            "segments": capstone_segments,
            "ordered_correspondence": True,
            "bar_ranges": [row[0] for row in CAPSTONE_ROWS],
            "total_printed_bars": 32,
            "event_mapping": None,
            "event_declaration": {
                "txt_line_number": 21,
                "txt_literal": "256 events",
                "pdf_p1_value": 256,
                "reconciliation_status": "blocked_unresolved",
                "reason": "The source does not map declared events to the eight four-bar rows or define a time signature, event density, or event instances.",
            },
        },
        "workload_reconciliation": {
            "txt_total_declaration": {"line_number": 10, "value": total_declared, "unit_literal": "events"},
            "txt_module_sum": module_sum,
            "pdf_p1_total": index_total,
            "module_counts_match_pdf_index": True,
            "printed_total_arithmetic": "matched",
            "task_to_event_reconciliation": "blocked_unresolved",
            "reason": "Printed counts match arithmetically, but PDF passes, cells, riffs, section rows, studies, bar ranges, and repair pairs are not defined as enumerated events or mapped to the declared counts.",
        },
        "lexical_coverage": {
            "report_path": COVERAGE,
            "classification_counts": source["coverage_workbook"]["page_classification_counts"],
            "claim_limit": "lexical matching is not semantic equivalence or task-to-event proof",
        },
        "source_specific_ambiguities": [
            "TXT event totals match the PDF index but do not enumerate event instances or define how PDF task rows contribute to event counts.",
            "Module H declares 192 events across four eight-bar studies; no allocation to studies, chord-cell positions, or six-step passes is authored.",
            "Module I declares 256 events and a 32-bar capstone; page 14 has eight four-bar rows but no event mapping or time signature.",
            "Module J's 64-event declaration is not mapped to eight failure/repair rows or mastery checks.",
            "The page-2 vocabulary and practice note are shared reference text with no printed A-J assignment.",
            "The mastery threshold 14/16 has no authored scoring allocation; the no-zero list is retained literally without scoring implementation.",
            "Page-9 variation instruction requires three changes per example, but the source does not author those variations.",
            "Level 89 text is a boundary only; no Level89 tasks are represented.",
        ],
        "limits": [
            "Task rows are structured source blocks, not event records, playable material, performance evidence, or Curriculum approval.",
            "No pitch/fret realization, numeric tempo, event timing, duration, onset, event identifiers, schedule, or playable projection is created.",
            "The candidate describes block-level source relationships; all event-count reconciliation remains blocked/unresolved.",
        ],
    }


def validate_output_path(root: Path, output_path: Path) -> Path:
    if not output_path.is_absolute():
        output_path = root / output_path
    try:
        lexical = output_path.relative_to(root)
    except ValueError as exc:
        raise CandidateError("OUTPUT_OUTSIDE_LANE_BUILD_ROOT") from exc
    if not lexical.parts or any(part in ("", ".", "..") for part in lexical.parts):
        raise CandidateError("OUTPUT_PARENT_TRAVERSAL")
    if not lexical.is_relative_to(BUILD_REL):
        raise CandidateError("OUTPUT_OUTSIDE_LANE_BUILD_ROOT")
    current = root
    for part in lexical.parts:
        current = current / part
        if current.is_symlink():
            raise CandidateError("OUTPUT_PATH_SYMLINK")
    parent = output_path.parent
    if not parent.exists():
        parent.mkdir(parents=True, exist_ok=True)
    if not parent.resolve(strict=True).is_relative_to((root / BUILD_REL).resolve(strict=False)):
        raise CandidateError("OUTPUT_PARENT_ESCAPES_LANE_BUILD")
    if output_path.exists():
        raise CandidateError("OUTPUT_OVERWRITE_REFUSED")
    return output_path


def write_candidate(root: Path, output_path: Path, candidate: dict[str, Any]) -> dict[str, Any]:
    target = validate_output_path(root, output_path)
    encoded = (json.dumps(candidate, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    target.write_bytes(encoded)
    return {"path": str(target.relative_to(root)), "bytes": len(encoded), "sha256": sha(encoded)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build detached Level 88 semantic PDF task-block candidates.")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--write-candidates", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve(strict=True)
    try:
        candidate = build_candidate(root)
        if not args.write_candidates:
            print(json.dumps({
                "workbook_id": candidate["workbook_id"],
                "module_count": len(candidate["modules"]),
                "total": candidate["workload_reconciliation"],
                "candidate_status": candidate["candidate_status"],
            }, ensure_ascii=False, indent=2))
            return 0
        outputs = [
            write_candidate(root, root / BUILD_REL / "candidate-a.json", candidate),
            write_candidate(root, root / BUILD_REL / "candidate-b.json", candidate),
        ]
        print(json.dumps({"outputs": outputs}, ensure_ascii=False, indent=2))
        return 0
    except CandidateError as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
