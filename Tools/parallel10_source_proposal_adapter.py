#!/usr/bin/env python3
"""Pinned, unallocated schema1 source-proposal boundary; Level 7 is its first adapter."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
AGG = Path("Build/parallel-04/2.3.1.1.1-level007-whole-r04/candidate-01.json")
TXT = Path("Notes/music/guitar project/TXT version/108_Finger_Permutations_Level_7_Three_String_Skip_Relay.txt")
PDF = Path("Notes/music/guitar project/PDF version/108_Finger_Permutations_Level_7_Three_String_Skip_Relay.pdf")
SCHEMA = Path("Results/primary/20260912T100538Z-2.1.1.2.1-r02-evidence/schema-freeze.json")
CATALOG = Path("Content/controls/curriculum-v1/workbook-coverage.json")
OUT = Path("Build/parallel-10/level007-source-proposal-adapter-r01")
PINS = {
    AGG: "8812010a99b12afbcfb8df00c40a7d05b329cc2031f9950d8f346ccf84f2f128",
    TXT: "467d1401237e34633efc4c517fa98d8190f0b47346a7b34be9d2548924883b61",
    PDF: "5c8607cff40801acb13f5e08dd2988b2ff943593eb084de2801f05f507a6c4ea",
    SCHEMA: "0659fa962a5c933a2bcf3045772b6fe5b05b4deefb3511f5dcb68af51088de95",
    CATALOG: "d8e492101c97c60add858799c77da4db3f0c528d348c9cf66105c2dc37df4eeb",
}
OPEN_MIDI = {"E": (1, 40), "A": (2, 45), "D": (3, 50), "G": (4, 55), "B": (5, 59), "e": (6, 64)}
FINGERS = {"1": "index", "2": "middle", "3": "ring", "4": "pinky"}
ROUTES = (("E", "D", "B"), ("A", "G", "e"), ("e", "G", "A"), ("B", "D", "E"))
NULL_FIELDS = ("canonical_item_id", "canonical_variant_id", "fixed_bpm", "note_per_click", "onset_q", "duration_q")
FALSE_FIELDS = ("admitted", "imported", "runtime_admitted", "runtime_eligible")


class ProposalError(ValueError):
    """A pinned source or proposal invariant failed."""


def require(condition: bool, code: str) -> None:
    if not condition:
        raise ProposalError(code)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def serialized(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")


def value_sha(value: object) -> str:
    return sha(serialized(value))


@dataclass(frozen=True)
class Context:
    txt_lines: tuple[str, ...]
    pdf_cards: dict[int, tuple[int, str, list[str]]]
    schema_version: str
    catalog_workbook_id: str


class SourceAdapter(Protocol):
    """Format-specific checks stay outside the reusable proposal/authority core."""

    name: str
    wbs_id: str
    level: int
    expected_records: int
    expected_routes: int
    expected_contacts: int
    gaps: tuple[str, ...]

    def check_aggregate(self, aggregate: dict, context: Context) -> None: ...

    def expected_key(self, index: int) -> str: ...

    def normalize(self, row: dict, index: int, context: Context) -> dict: ...

    def guidance(self, aggregate: dict) -> list[dict]: ...


def pdf_cards(reader: PdfReader) -> dict[int, tuple[int, str, list[str]]]:
    require(len(reader.pages) == 10, "PDF_PAGE_COUNT")
    cards = {}
    for page in range(2, 11):
        text = reader.pages[page - 1].extract_text()
        parts = re.split(r"(?m)^(\d{3})\s+(\d{4})\s*$", text)
        require(len(parts) == 37, f"PDF_CARD_COUNT_PAGE_{page}")
        for slot in range(12):
            number = int(parts[slot * 3 + 1])
            code = parts[slot * 3 + 2]
            body = parts[slot * 3 + 3]
            require(number == (page - 2) * 12 + slot + 1, "PDF_CARD_ORDER")
            require(number not in cards, "PDF_DUPLICATE_CARD")
            rows = [line.strip() for line in body.splitlines() if re.match(r"^[eBGDAE]\|", line)]
            require(len(rows) == 12, "PDF_TAB_ROWS")
            cards[number] = (page, code, rows)
    require(len(cards) == 108, "PDF_WHOLE_LEVEL")
    return cards


def read_inputs(root: Path = ROOT) -> tuple[dict, Context]:
    for rel, expected in PINS.items():
        actual = sha((root / rel).read_bytes())
        require(actual == expected, f"PIN_DRIFT {rel}")
    aggregate = json.loads((root / AGG).read_text())
    schema = json.loads((root / SCHEMA).read_text())
    require(schema["decision"] == "Technical schema1 FROZEN", "SCHEMA_AUTHORITY")
    catalog = json.loads((root / CATALOG).read_text())
    entries = [e for e in catalog["workbook_catalog"]["entries"] if e["workbook_id"] == "fg:workbook:000007"]
    require(len(entries) == 1, "CATALOG_LEVEL7")
    entry = entries[0]
    require(entry["conversion_status"] == "not_converted" and entry["stable_identity_status"] == "evidenced_source_only", "CATALOG_AUTHORITY")
    require(all(entry[k] is False for k in ("admitted", "imported", "runtime_eligible", "runtime_admitted", "whole_workbook_complete")), "CATALOG_AUTHORITY")
    require(entry["txt"]["sha256"] == PINS[TXT] and entry["pdf"]["sha256"] == PINS[PDF], "CATALOG_SOURCE")
    context = Context(tuple((root / TXT).read_text().splitlines()), pdf_cards(PdfReader(str(root / PDF))),
                      schema["schema_version"], entry["workbook_id"])
    return aggregate, context


def unallocated(row: dict) -> None:
    require(all(k in row and row[k] is None for k in NULL_FIELDS), "INVENTED_ID_OR_TIMING")
    require(all(k in row and row[k] is False for k in FALSE_FIELDS), "INVALID_ADMISSION")


class Level7Adapter:
    name = "level007-three-string-skip-relay.1"
    wbs_id = "2.3.1.1.1"
    level = 7
    expected_records = 108
    expected_routes = 432
    expected_contacts = 1728
    gaps = (
        "P02 independent Level7 aggregate/source review and Curriculum musical review are pending.",
        "Canonical item/event/variant IDs, lineage and content revision require a reviewed authority transaction.",
        "Source does not define a fixed quarter-note event grid, onset/duration or absolute starting BPM.",
        "Pick-start variant design, runtime validation, import, admission and performed audio are pending.",
    )

    def check_aggregate(self, aggregate: dict, context: Context) -> None:
        require(aggregate["schema"] == "fathom-level007-whole-detached-candidate-v1" and aggregate["level"] == 7,
                "AGGREGATE_SCHEMA")
        require(aggregate["wbs_id"] == "2.3.1.1.1" and aggregate["source_coverage_verified"] is True,
                "AGGREGATE_SCOPE")
        require(aggregate["whole_workbook_complete"] is False and not aggregate["exceptions"], "AGGREGATE_AUTHORITY")
        require(all(aggregate[k] is False for k in FALSE_FIELDS), "AGGREGATE_AUTHORITY")
        coverage = aggregate["coverage"]
        require((coverage["record_count"], coverage["route_count"], coverage["contact_count"]) == (108, 432, 1728),
                "AGGREGATE_COUNTS")
        require(coverage["contiguous_source_local_sequence"] is True and coverage["set_numbers"] == list(range(1, 10)),
                "AGGREGATE_COVERAGE")
        source = aggregate["source"]
        require(source["txt_sha256"] == PINS[TXT] and source["pdf_sha256"] == PINS[PDF], "AGGREGATE_SOURCE")
        require(aggregate["source_map"]["stable_ids_assigned"] is False and
                aggregate["source_map"]["conversion_status"] == "not_converted", "AGGREGATE_SOURCE_MAP")
        require(len(aggregate["set_provenance"]) == 9, "SET_PROVENANCE")
        for number, prov in enumerate(aggregate["set_provenance"], 1):
            require(prov["set"] == number and prov["exercise_start"] == f"{(number - 1) * 12 + 1:03d}" and
                    prov["exercise_end"] == f"{number * 12:03d}", "SET_PROVENANCE")
            instructions = prov["instructions"]
            require(instructions["movement_rule_ref"] == "L7-TXT1-5-9" and
                    instructions["practice_rule_ref"] == "L7-TXT1-16-24", "GUIDANCE_REF")
            require(instructions["movement_rule_text"] == "\n".join(context.txt_lines[4:9]) and
                    instructions["practice_rule_text"] == "\n".join(context.txt_lines[15:24]), "GUIDANCE_DRIFT")
            require(prov["exceptions"] == [], "SET_EXCEPTION")

    def expected_key(self, index: int) -> str:
        return f"L7-set{index // 12 + 1:02d}-ex{index + 1:03d}"

    def guidance(self, aggregate: dict) -> list[dict]:
        return [{"set": p["set"], "instructions": p["instructions"]}
                for p in aggregate["set_provenance"]]

    def normalize(self, row: dict, index: int, context: Context) -> dict:
        number = index + 1
        require(row["exercise_number"] == f"{number:03d}" and row["source_local_key"] == self.expected_key(index),
                "SOURCE_LOCAL_ORDER")
        code = row["code"]
        require(re.fullmatch(r"[1-4]{4}", code) is not None, "FINGER_CODE")
        txt_ref, pdf_ref = row["source_refs"]["txt"], row["source_refs"]["pdf"]
        match = re.fullmatch(r"L7-TXT1-(\d+)-(\d+)", txt_ref)
        require(match is not None, "TXT_REF")
        start, end = map(int, match.groups())
        require(1 <= start <= end <= len(context.txt_lines), "TXT_SPAN")
        span = list(context.txt_lines[start - 1:end])
        require(span[0] == f"Exercise {number:03d}: {code}", "TXT_CARD_HEADING")
        require(span[1] == "ASCEND - E-D-B, A-G-e" and span[8] == "DESCEND - e-G-A, B-D-E", "TXT_DIRECTION")
        require(re.fullmatch(r"L7-PDF1-p\d+", pdf_ref) is not None, "PDF_REF")
        page, pdf_code, pdf_rows = context.pdf_cards[number]
        require(pdf_ref == f"L7-PDF1-p{page}" and page == index // 12 + 2 and pdf_code == code, "PDF_CARD")
        directions = row["directions"]
        require(len(directions) == 2 and [d["direction"] for d in directions] == ["ascending", "descending"],
                "DIRECTION_ORDER")
        txt_rows = span[2:8] + span[9:15]
        require(txt_rows == directions[0]["tab_rows"] + directions[1]["tab_rows"] == pdf_rows, "TAB_SOURCE_FIDELITY")
        projected_routes = []
        projected_events = []
        for direction_index, direction in enumerate(directions):
            require(len(direction["routes"]) == 2, "ROUTE_COUNT")
            printed_routes = [[], []]
            for string_name, tab_row in zip(("e", "B", "G", "D", "A", "E"), direction["tab_rows"], strict=True):
                tab = re.fullmatch(rf"{string_name}\|([0-9-]{{8}})\|([0-9-]{{8}})\|", tab_row)
                require(tab is not None, "TAB_GRID_SHAPE")
                for route_index in range(2):
                    printed_routes[route_index].extend(
                        (column, string_name, int(symbol))
                        for column, symbol in enumerate(tab.group(route_index + 1)) if symbol.isdigit()
                    )
            for printed in printed_routes:
                printed.sort(key=lambda value: value[0])
                require(len(printed) == 4, "TAB_ROUTE_CONTACTS")
            for route_index, route in enumerate(direction["routes"]):
                strings = ROUTES[direction_index * 2 + route_index]
                require(route["strings"] == list(strings) and route["silent_intervening_strings"] == 2,
                        "SILENT_STRING_GEOMETRY")
                require(len(route["notes"]) == 4, "ROUTE_NOTES")
                occurrence_keys = []
                for ordinal, note in enumerate(route["notes"], 1):
                    string_name = (strings[0], strings[1], strings[1], strings[2])[ordinal - 1]
                    digit = code[ordinal - 1]
                    require(note["ordinal"] == ordinal and note["string"] == string_name and
                            note["finger_digit"] == digit and note["finger_name"] == FINGERS[digit] and
                            note["fret"] == 4 + int(digit) and note["ascii_column"] == (ordinal - 1) * 2,
                            "SOURCE_NOTE")
                    require(note["onset_q"] is None and note["duration_q"] is None, "INVENTED_TIMING")
                    require(printed_routes[route_index][ordinal - 1] ==
                            (note["ascii_column"], string_name, note["fret"]), "TAB_NOTE_FIDELITY")
                    string_number, open_pitch = OPEN_MIDI[string_name]
                    occurrence = f"{row['source_local_key']}:{direction['direction']}:{route_index + 1}:{ordinal}"
                    occurrence_keys.append(occurrence)
                    projected_events.append({"source_occurrence_key": occurrence, "event_id": None, "kind": "note",
                                             "string": string_number, "source_string": string_name,
                                             "fret": note["fret"], "midi": open_pitch + note["fret"],
                                             "finger": int(digit), "source_finger_name": note["finger_name"],
                                             "ascii_column": note["ascii_column"], "onset_q": None,
                                             "duration_q": None, "attack": None, "spelling": None,
                                             "degree_contexts": {}, "tie_from": None})
                projected_routes.append({"direction": direction["direction"], "route_ordinal": route_index + 1,
                                         "played_strings": list(strings), "silent_intervening_strings": 2,
                                         "source_occurrence_keys": occurrence_keys,
                                         "source_tab_rows": list(direction["tab_rows"])})
        require(len(projected_routes) == 4 and len(projected_events) == 16, "PROJECTED_COUNTS")
        timing_gap = "Source gives relative practice BPM and straight-16th/grouping guidance but no fixed BPM, quarter-note grid, onset or duration."
        return {"source_local_key": row["source_local_key"], "source_record_sha256": value_sha(row),
                "exercise_number": row["exercise_number"], "source_code": code,
                "source_refs": {"txt": txt_ref, "pdf": pdf_ref},
                "source_span_sha256": sha("\n".join(span).encode("utf-8")),
                "record_proposal": {"id": None, "workbook_id": None, "module_id": None,
                                    "legacy_level": 7, "title": span[0], "kind": "notation",
                                    "content_revision": None, "lineage": None,
                                    "status": "source_mapped_unallocated", "runtime_eligible": False,
                                    "source_refs": [txt_ref, pdf_ref, "L7-TXT1-5-9", "L7-TXT1-16-24"],
                                    "context": {"local_code": code, "position": "fifth",
                                                "tuning_open_midi": [40, 45, 50, 55, 59, 64],
                                                "pick_start": None},
                                    "events": projected_events, "route_proposals": projected_routes,
                                    "variants": [], "timing": {"status": "unresolved", "unit": None,
                                                               "fixed_bpm": None, "note_per_click": None},
                                    "rubric": None, "resource_requirements": [],
                                    "ambiguities": [timing_gap,
                                                    "Canonical item/event/variant allocation and pick-start variant design require a separate reviewed transaction."]}}


def build_proposal(aggregate: dict, context: Context, adapter: SourceAdapter) -> dict:
    adapter.check_aggregate(aggregate, context)
    records = aggregate["records"]
    require(len(records) == adapter.expected_records, "RECORD_COUNT")
    seen = set()
    proposals = []
    for index, row in enumerate(records):
        unallocated(row)
        key = row["source_local_key"]
        require(key not in seen, "DUPLICATE_SOURCE_LOCAL_KEY")
        seen.add(key)
        require(key == adapter.expected_key(index), "SOURCE_LOCAL_ORDER")
        proposals.append(adapter.normalize(row, index, context))
    routes = sum(len(p["record_proposal"]["route_proposals"]) for p in proposals)
    contacts = sum(len(p["record_proposal"]["events"]) for p in proposals)
    require((routes, contacts) == (adapter.expected_routes, adapter.expected_contacts), "PROPOSAL_COUNTS")
    return {"schema": "fathom-source-to-schema1-proposal.1", "adapter": adapter.name,
            "schema1_contract_version": context.schema_version, "wbs_id": adapter.wbs_id,
            "classification": "source_mapped_unallocated_nonadmitted_proposal",
            "input_sha256": {str(path): digest for path, digest in PINS.items()},
            "source_catalog_workbook_id": context.catalog_workbook_id,
            "authority": {"canonical_ids_allocated": False, "runtime_eligible": False,
                          "imported": False, "admitted": False, "native_schema1_package": False},
            "coverage": {"record_count": len(proposals), "route_count": routes,
                         "contact_count": contacts, "source_coverage_verified": True,
                         "whole_workbook_complete": False},
            "set_guidance": adapter.guidance(aggregate), "gaps": list(adapter.gaps),
            "records": proposals}


def build(root: Path = ROOT) -> dict:
    aggregate, context = read_inputs(root)
    return build_proposal(aggregate, context, Level7Adapter())


def write_proposal(output: Path, root: Path = ROOT) -> tuple[int, str]:
    allowed = (root / OUT).resolve()
    require(output.parent.resolve().is_relative_to(allowed), "OUTPUT_OUTSIDE_BUILD")
    require(not output.exists() and not output.is_symlink(), "OUTPUT_EXISTS_OR_SYMLINK")
    data = serialized(build(root))
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as stream:
        stream.write(data)
    return len(data), sha(data)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    size, digest = write_proposal(args.output)
    print(f"LEVEL7 SOURCE PROPOSAL PASS bytes={size} sha256={digest} output={args.output}")


if __name__ == "__main__":
    main()
