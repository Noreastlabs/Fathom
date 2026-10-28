#!/usr/bin/env python3
"""Convert pinned Level 70 P1-P5 cells to an unadmitted schema1 record proposal."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
SPECS = (
    ("p1", "Build/parallel-05/2.3-level070-music-r01/candidate-01.json", "c34f32197db15736e3ccef80f49fafeae53bc3e4236c8a8490ff68e0a00acf46"),
    ("p2", "Build/parallel-05/2.3-level070-p2-r01/candidate-01.json", "590aba968d761418617f51a048440c270baac406cc450e84cf81b6c1f772fabb"),
    ("p3", "Build/parallel-05/2.3-level070-p3-r01/candidate-01.json", "8de478cfe6de9e08f8286b87edd1a1df92fb2697603e59196d64138ced287508"),
    ("p4", "Build/parallel-05/2.3-level070-p4-r01/candidate-01.json", "5c4d6b35691a0aa837c0e909e1544409fd035924bec4763c1f68c66b15e38c19"),
    ("p5", "Build/parallel-05/2.3-level070-p5-r01/candidate-01.json", "6d1e4926be9c4616966a6ac21653d2622fbecc11355cb73d1654a1161ec46ecb"),
)
MODULE_B_SPEC = ("module-b-p1-p2", "Build/parallel-05/2.3-level070-moduleb-r01/candidate-01.json",
                 "ce1a4f99cdc0da622a05895fb29beb5dcdd990c8c4e098543b8b1255c1e08968")
MODULE_B_SPECS = {
    "p1-p2": (MODULE_B_SPEC, 37043, 8, 92, 0),
    "p2-p3": (("module-b-p2-p3", "Build/parallel-05/2.3-level070-moduleb-p2p3-r01/candidate-01.json",
               "f87c69ae43bc9864c7a1f2fc3f7ae67bab4fca2e02d8fdfc4ee4194137dac19a"), 37124, 8, 101, 1),
    "p3-p4": (("module-b-p3-p4", "Build/parallel-05/2.3-level070-moduleb-p3p4-r01/candidate-01.json",
               "20888f033c1b87cfcbc79a44b3c0e319ef94e5f5bd2f8a533957c62ba6a232bc"), 37140, 9, 110, 0),
    "p4-p5": (("module-b-p4-p5", "Build/parallel-05/2.3-level070-moduleb-p4p5-r01/candidate-01.json",
               "77a87c40ed70796b71dc6860e2b817f70246e119bb0489c170d8aef5d8e50ab8"), 37153, 9, 119, 1),
}
MODULE_CD_SPECS = {
    "c-low": ("Build/parallel-05/2.3-level070-modulec-low-r01/candidate-01.json",
              "3d0cf3e66a88a9bc2f4800d96b939d686426ffc2f188e56f3df04981fdc89b8e", 39179, 10,
              (132, 142, 152), (16, 16, 14), (1, 2, 3)),
    "c-upper": ("Build/parallel-05/2.3-level070-modulec-upper-r01/candidate-01.json",
                "65a086e0de3502c62597393b4928a4eafd488b9378d976c18653545e6ba7acd3", 40665, 11,
                (162, 172, 182), (16, 16, 16), (4, 5, 6)),
    "d-p1-p3": ("Build/parallel-05/2.3-level070-moduled-p1p3-r01/candidate-01.json",
                "8b890c727b9284a8b989292b658e3628340399e0bbbcb3d6882dd2a549ed4930", 44485, 12,
                (196, 207, 218), (18, 20, 12), (1, 2, 3)),
    "d-p4-p5": ("Build/parallel-05/2.3-level070-moduled-p4p5-r01/candidate-01.json",
                "a06577619b75c110172c4059514b578705299f3a3ef3dd1c03a55e490b981d1e", 34743, 13,
                (229, 240), (18, 20), (4, 5)),
}
MODULE_EFGH_SPECS = {
    "e-forward": ("Build/parallel-05/2.3-level070-modulee-forward-r01/candidate-01.json",
                  "ce96a706c83ecc0fce2ce3346c235dadab6d378fc33ad689b6342b56b1dbe423", 83519, 14,
                  (257, 268, 279, 290, 301), (18, 18, 18, 18, 18)),
    "e-reverse": ("Build/parallel-05/2.3-level070-modulee-reverse-r01/candidate-01.json",
                  "24834cb7ba909bfed6dee0b365ce9afa03e432f5ae62b63f9ab8dc430bb346ac", 83523, 15,
                  (313, 324, 335, 346, 357), (18, 18, 18, 18, 18)),
    "f-directional": ("Build/parallel-05/2.3-level070-modulef-directional-r01/candidate-01.json",
                      "1b9493de59727d679bd015bac3f39570afb0db471dde59df7103cb5772210f75", 53409, 16,
                      (372, 378, 384, 390, 396), (12, 12, 12, 12, 12)),
    "g-lower": ("Build/parallel-05/2.3-level070-moduleg-lower-seams-r01/candidate-01.json",
                "81876a3eb622f43accdf7b0088bd75fb99f1f69760a09e9f56b06e8f95dc9ba3", 34486, 17,
                (406, 417), (16, 16)),
    "g-upper": ("Build/parallel-05/2.3-level070-moduleg-upper-seams-r01/candidate-01.json",
                "5d72a0920f0f7e2d5c77ceb090da1f337efc69d47dc1d93ad851320ec0743f7e", 34489, 18,
                (428, 439), (16, 16)),
    "h-capstone": ("Build/parallel-05/2.3-level070-moduleh-capstone-r01/candidate-01.json",
                   "f2fd5021ae676c96b6279fc93dc526e83c6fcf5e5d6e64f710925cd48c9f6781", 73493, 19,
                   (454, 465, 476, 487), (16, 16, 16, 16)),
}
OPEN_MIDI = (40, 45, 50, 55, 59, 64)
NOTE_KEYS = {"kind", "string", "fret", "midi", "spelling", "degree_contexts", "finger", "onset_q", "duration_q", "attack", "tie_from"}
SOURCE_SHA = {"txt": "13ed1a46b87e74c3b3fb78161281268f79ed710b5bd7f12195378f3b247c4b9b", "pdf": "4b95c98c91c35f132954f2452104280f40d8e96b46ca431344e6b4de007c764f"}
SOURCE_BYTES = {"txt": 36082, "pdf": 56679}


class AdapterError(ValueError):
    """Untrusted or incomplete pre-admission input."""


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def read_pinned(root: Path, relative: str, expected: str, size: int | None = None) -> bytes:
    path = root / relative
    try:
        resolved = path.resolve(strict=True)
    except FileNotFoundError as exc:
        raise AdapterError(f"missing pinned input: {relative}") from exc
    if path.is_symlink() or not resolved.is_relative_to(root):
        raise AdapterError(f"unsafe input path: {relative}")
    raw = path.read_bytes()
    if sha(raw) != expected or (size is not None and len(raw) != size):
        raise AdapterError(f"pinned input drift: {relative}")
    return raw


def load_candidates(root: Path, specs: tuple[tuple[str, str, str], ...] = SPECS) -> list[dict[str, Any]]:
    if len(specs) != 5 or [row[0] for row in specs] != [f"p{i}" for i in range(1, 6)]:
        raise AdapterError("expected one ordered P1-P5 candidate specification")
    loaded = []
    for position, relative, digest in specs:
        raw = read_pinned(root, relative, digest)
        def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
            obj: dict[str, Any] = {}
            for key, value in pairs:
                if key in obj:
                    raise AdapterError(f"duplicate JSON key: {relative}:{key}")
                obj[key] = value
            return obj
        try:
            candidate = json.loads(raw, object_pairs_hook=unique_object)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise AdapterError(f"invalid candidate JSON: {relative}") from exc
        loaded.append({"position": position, "path": relative, "sha256": digest, "bytes": len(raw), "candidate": candidate})
    return loaded


def load_moduleb_candidate(root: Path, spec: tuple[str, str, str] = MODULE_B_SPEC) -> dict[str, Any]:
    position, relative, digest = spec
    known = [entry for entry in MODULE_B_SPECS.values() if entry[0] == spec]
    if len(known) != 1:
        raise AdapterError("wrong Module B candidate position")
    raw = read_pinned(root, relative, digest, known[0][1])
    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                raise AdapterError(f"duplicate JSON key: {relative}:{key}")
            value[key] = item
        return value
    try:
        candidate = json.loads(raw, object_pairs_hook=unique_object)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AdapterError(f"invalid candidate JSON: {relative}") from exc
    return {"position": position, "path": relative, "sha256": digest, "bytes": len(raw), "candidate": candidate}


def load_modulecd_candidate(root: Path, block: str) -> dict[str, Any]:
    if block not in MODULE_CD_SPECS:
        raise AdapterError("unknown Module C/D block")
    relative, digest, size, *_ = MODULE_CD_SPECS[block]
    raw = read_pinned(root, relative, digest, size)
    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                raise AdapterError(f"duplicate JSON key: {relative}:{key}")
            value[key] = item
        return value
    try:
        candidate = json.loads(raw, object_pairs_hook=unique_object)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AdapterError(f"invalid candidate JSON: {relative}") from exc
    return {"position": block, "path": relative, "sha256": digest, "bytes": len(raw), "candidate": candidate}


def load_moduleefgh_candidate(root: Path, block: str) -> dict[str, Any]:
    if block not in MODULE_EFGH_SPECS:
        raise AdapterError("unknown Module E-H block")
    relative, digest, size, *_ = MODULE_EFGH_SPECS[block]
    raw = read_pinned(root, relative, digest, size)
    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                raise AdapterError(f"duplicate JSON key: {relative}:{key}")
            value[key] = item
        return value
    try:
        candidate = json.loads(raw, object_pairs_hook=unique_object)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AdapterError(f"invalid candidate JSON: {relative}") from exc
    return {"position": block, "path": relative, "sha256": digest, "bytes": len(raw), "candidate": candidate}


def validate_sources(root: Path, loaded: list[dict[str, Any]], pdf_pages: dict[int, str] | None = None) -> tuple[dict[str, Any], list[str], dict[int, str]]:
    pairs = [row["candidate"].get("source_pair") for row in loaded]
    if not pairs or any(pair != pairs[0] for pair in pairs):
        raise AdapterError("source pair differs across P1-P5")
    pair = pairs[0]
    if not isinstance(pair, dict) or set(pair) != {"txt", "pdf"}:
        raise AdapterError("missing source pair")
    sources: dict[str, bytes] = {}
    for kind in ("txt", "pdf"):
        entry = pair[kind]
        if not isinstance(entry, dict) or set(entry) != {"path", "sha256", "bytes"}:
            raise AdapterError(f"invalid {kind} source identity")
        if entry["sha256"] != SOURCE_SHA[kind] or entry["bytes"] != SOURCE_BYTES[kind]:
            raise AdapterError(f"unrecognized {kind} source identity")
        sources[kind] = read_pinned(root, entry["path"], entry["sha256"], entry["bytes"])
    try:
        lines = sources["txt"].decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise AdapterError("source TXT is not UTF-8") from exc
    if pdf_pages is None:
        reader = PdfReader(root / pair["pdf"]["path"])
        pdf_pages = {index: page.extract_text() or "" for index, page in enumerate(reader.pages, 1)}
    return pair, lines, pdf_pages


def require_cell(row: dict[str, Any], lines: list[str], pdf_pages: dict[int, str], seen_keys: set[str]) -> dict[str, Any]:
    candidate, position = row["candidate"], row["position"]
    if not isinstance(candidate, dict) or candidate.get("workstream") != "2.3.1.2.1" or candidate.get("review") != "Pending":
        raise AdapterError(f"wrong workstream or review state: {position}")
    if candidate.get("candidate_kind") != "detached_schema_shaped_source_conversion" or candidate.get("schema_basis") != "1.0.0-curriculum-candidate; local key only, no canonical identity allocation" or candidate.get("source_pdf_pages") != 20:
        raise AdapterError(f"wrong detached candidate basis: {position}")
    for flag in ("admitted", "imported", "runtime_eligible", "whole_workbook_complete"):
        if candidate.get(flag) is not False:
            raise AdapterError(f"unsafe admission flag {flag}: {position}")
    if candidate.get("contradictions") != [] or not isinstance(candidate.get("pending"), list) or any(not isinstance(item, dict) or not isinstance(item.get("reason"), str) or not item["reason"] for item in candidate["pending"]):
        raise AdapterError(f"unresolved candidate contradiction/shape: {position}")
    cells = candidate.get("selected_cells")
    if not isinstance(cells, list) or len(cells) != 1 or not isinstance(cells[0], dict):
        raise AdapterError(f"expected one cell: {position}")
    cell = cells[0]
    if cell.get("key") != "A melodic minor" or not isinstance(cell.get("position"), str) or not isinstance(cell.get("turnaround"), str):
        raise AdapterError(f"unexpected scale or position: {position}")
    local_key = cell.get("local_key")
    if local_key != f"level070-module-a-{position}" or local_key in seen_keys:
        raise AdapterError(f"duplicate or wrong local key: {local_key}")
    seen_keys.add(local_key)
    source = cell.get("source")
    if not isinstance(source, dict) or not isinstance(source.get("pdf_page"), int) or not isinstance(source.get("txt_lines"), list):
        raise AdapterError(f"missing cell source: {position}")
    page = source["pdf_page"]
    if page != int(position[1:]) + 2 or page not in pdf_pages:
        raise AdapterError(f"wrong/missing PDF page: {position}")
    page_hash = sha(pdf_pages[page].encode("utf-8"))
    if source.get("pdf_page_text_sha256") != page_hash or candidate.get("selected_pdf_pages") != [page]:
        raise AdapterError(f"PDF page text drift: {position}")
    selected_lines = source["txt_lines"]
    if not selected_lines or any(type(n) is not int or n < 1 or n > len(lines) for n in selected_lines):
        raise AdapterError(f"TXT source line missing: {position}")
    if selected_lines != list(range(min(selected_lines), max(selected_lines) + 1)):
        raise AdapterError(f"TXT source lines not contiguous: {position}")
    events = cell.get("tone_events")
    if cell.get("ascent_count") != 18 or cell.get("descent_count") != 18 or cell.get("printed_tone_count") != 36 or not isinstance(events, list) or len(events) != 36:
        raise AdapterError(f"wrong tone count: {position}")
    if cell.get("timing_basis") != "unresolved: ordered tones only; no numeric onset or duration":
        raise AdapterError(f"unexpected timing basis: {position}")
    if cell.get("symmetric_descent") is not True or not cell.get("printed_passes") or not cell.get("printed_pick_reset_instruction"):
        raise AdapterError(f"missing printed instructions: {position}")
    for number, event in enumerate(events, 1):
        if not isinstance(event, dict) or event.get("ordinal") != number or event.get("half") != ("ascent" if number <= 18 else "descent"):
            raise AdapterError(f"duplicate/missing event ordinal: {position}:{number}")
        if event.get("pdf_page") != page or event.get("pdf_page_text_sha256") != page_hash or event.get("pick_stroke") is not None:
            raise AdapterError(f"source or performed pick drift: {position}:{number}")
        refs = event.get("txt_lines")
        if not isinstance(refs, list) or not refs or any(type(n) is not int or n not in selected_lines for n in refs):
            raise AdapterError(f"event TXT source missing: {position}:{number}")
        note = event.get("schema_event_without_canonical_id")
        if not isinstance(note, dict) or set(note) != NOTE_KEYS or note.get("kind") != "note" or note.get("attack") != "picked" or note.get("onset_q") is not None or note.get("duration_q") is not None or note.get("tie_from") is not None:
            raise AdapterError(f"non-schema note or invented timing: {position}:{number}")
        string, fret = note.get("string"), note.get("fret")
        if type(string) is not int or not 1 <= string <= 6 or type(fret) is not int or not 0 <= fret <= 24 or note.get("midi") != OPEN_MIDI[string - 1] + fret:
            raise AdapterError(f"tone pitch/contact drift: {position}:{number}")
        if note.get("finger") != event.get("printed_finger") or type(note.get("finger")) is not int or not 1 <= note["finger"] <= 4 or not isinstance(note.get("spelling"), str) or note.get("degree_contexts") != {} or not isinstance(event.get("printed_degree"), str) or not event["printed_degree"]:
            raise AdapterError(f"printed finger/degree drift: {position}:{number}")
    if events[18]["schema_event_without_canonical_id"] != events[17]["schema_event_without_canonical_id"]:
        raise AdapterError(f"turnaround re-attack missing: {position}")
    if [e["schema_event_without_canonical_id"] for e in events[18:]] != [e["schema_event_without_canonical_id"] for e in events[:18][::-1]]:
        raise AdapterError(f"descent order changed: {position}")
    return cell


def source_catalog_entry(kind: str, pair: dict[str, Any], lines: list[str], pages: dict[int, str], cell: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    source = cell["source"]
    if kind == "txt":
        first, last = source["txt_lines"][0], source["txt_lines"][-1]
        content = "\n".join(lines[first - 1:last])
        ref = f"L70-TXT{first}-{last}"
        return ref, {"path": pair["txt"]["path"], "sha256": pair["txt"]["sha256"], "format": "txt", "first_line": first, "last_line": last, "text": content, "text_sha256": sha(content.encode("utf-8"))}
    page = source["pdf_page"]
    content = pages[page]
    ref = f"L70-PDF{page}"
    return ref, {"path": pair["pdf"]["path"], "sha256": pair["pdf"]["sha256"], "format": "pdf", "page": page, "text": content, "text_sha256": sha(content.encode("utf-8"))}


def project_record(cell: dict[str, Any], pending: list[dict[str, Any]], refs: list[str]) -> dict[str, Any]:
    unresolved = [str(item["reason"]) for item in pending]
    unresolved += ["Opaque course/workbook/module/item/event/variant IDs require explicit reviewed allocation.", "Curriculum interpretation and expected-profile authority remain Pending."]
    events = [{**copy.deepcopy(event["schema_event_without_canonical_id"]), "event_id": None} for event in cell["tone_events"]]
    variants = []
    for pick in ("D", "U"):
        variants.append({
            "id": None, "label": f"continuous-{pick}", "event_ids": [None] * 36,
            "source_refs": refs, "route": "ascent_then_descent_continuous", "pick_start": pick,
            "pick_start_origin": "source_authored", "accent_policy": "source_unspecified",
            "role": "notation_practice", "grouping": {"kind": "unresolved", "notes_per_beat": None,
            "beat_unit_q": None, "marking_factor": [1, 1], "source_label": "No authored numeric beat unit for the selected cell"},
            "tail_pause": None, "unresolved": ["No per-event pick/accent realization or numeric timing is authored."],
        })
    return {
        "id": None, "workbook_id": None, "module_id": None, "legacy_level": 70,
        "title": f"Level 70 Module A {cell['position']}", "kind": "notation",
        "content_revision": None, "status": "converted_candidate", "runtime_eligible": False,
        "source_refs": refs, "authored_text_refs": refs, "normalization": [],
        "context": {"local_code": cell["local_key"], "route": cell["turnaround"], "position": cell["position"], "pick_start_variants": ["D", "U"]},
        "events": events, "timing": {"status": "unresolved", "unit": "quarter", "basis": cell["timing_basis"]},
        "rubric": None, "resource_requirements": [], "ambiguities": unresolved,
        "control_scope": {"local_case": cell["local_key"], "extent": "selected_illustration", "whole_workbook_complete": False,
        "source_event_count": 36, "basis_refs": refs, "unresolved": unresolved},
        "variants": variants, "lineage": None,
    }


def bind_explicit_identity(record: dict[str, Any], allocation: dict[str, Any]) -> dict[str, Any]:
    """Apply an external allocation to one draft; does not authorize or emit a package."""
    required = {"workbook_id", "module_id", "item_id", "event_ids", "variant_ids", "content_revision", "lineage"}
    if set(allocation) != required:
        raise AdapterError("explicit identity allocation fields differ")
    for field in ("workbook_id", "module_id", "item_id"):
        if not isinstance(allocation[field], str) or not re.fullmatch(r"fg:" + ("item" if field == "item_id" else field.removesuffix("_id")) + r":\d{6}", allocation[field]):
            raise AdapterError(f"invalid explicit {field}")
    item_id = allocation["item_id"]
    event_ids = allocation["event_ids"]
    variant_ids = allocation["variant_ids"]
    if not isinstance(event_ids, list) or len(event_ids) != len(record["events"]) or event_ids != [f"{item_id}:event:{n:04d}" for n in range(1, len(event_ids) + 1)]:
        raise AdapterError("event IDs do not match explicit item allocation")
    if not isinstance(variant_ids, list) or len(variant_ids) != 2 or len(set(variant_ids)) != 2 or any(not isinstance(v, str) or not re.fullmatch(r"fg:variant:\d{6}", v) for v in variant_ids):
        raise AdapterError("variant IDs invalid or duplicated")
    if type(allocation["content_revision"]) is not int or allocation["content_revision"] != 1 or allocation["lineage"] != {"kind": "new"}:
        raise AdapterError("new-item revision and lineage require reviewed allocation")
    bound = copy.deepcopy(record)
    bound["workbook_id"] = allocation["workbook_id"]
    bound["module_id"] = allocation["module_id"]
    bound["id"] = item_id
    bound["content_revision"] = 1
    bound["lineage"] = {"kind": "new"}
    for event, event_id in zip(bound["events"], event_ids):
        event["event_id"] = event_id
    for variant, variant_id in zip(bound["variants"], variant_ids):
        variant["id"] = variant_id
        variant["event_ids"] = list(event_ids)
    return bound


def build_proposal(root: Path, specs: tuple[tuple[str, str, str], ...] = SPECS, pdf_pages: dict[int, str] | None = None) -> dict[str, Any]:
    root = root.resolve(strict=True)
    loaded = load_candidates(root, specs)
    pair, lines, pages = validate_sources(root, loaded, pdf_pages)
    source_catalog: dict[str, Any] = {}
    positions = []
    seen: set[str] = set()
    for row in loaded:
        cell = require_cell(row, lines, pages, seen)
        refs = []
        for kind in ("txt", "pdf"):
            ref, passage = source_catalog_entry(kind, pair, lines, pages, cell)
            if ref in source_catalog and source_catalog[ref] != passage:
                raise AdapterError(f"source passage collision: {ref}")
            source_catalog[ref] = passage
            refs.append(ref)
        record = project_record(cell, row["candidate"]["pending"], refs)
        positions.append({
            "position": row["position"], "candidate_path": row["path"], "candidate_sha256": row["sha256"],
            "record_projection": record, "source_cell": cell, "candidate_pending": row["candidate"]["pending"],
            "event_provenance": [{key: value for key, value in event.items() if key != "schema_event_without_canonical_id"} for event in cell["tone_events"]],
        })
    # Recheck mutable input paths after conversion; a mixed snapshot is never emitted.
    load_candidates(root, specs)
    validate_sources(root, loaded, pages)
    return {
        "schema": "fathom-level070-batch-adapter-proposal.1", "schema_target": "1.0.0-curriculum-candidate",
        "workstream": "2.3.1.2.1", "status": "Pending", "admitted": False,
        "runtime_eligible": False, "whole_workbook_complete": False, "canonical_package": False,
        "source_pair": pair, "source_catalog": source_catalog, "positions": positions,
        "counts": {"positions": 5, "source_tones": 180, "record_projections": 5, "source_passages": len(source_catalog)},
        "schema_mapping": {
            "tone_events[].schema_event_without_canonical_id": "record.events[] note fields copied exactly; event_id remains null until explicit allocation",
            "tone_events[].printed_degree/printed_finger/txt_lines/pdf_page": "event_provenance[] retained outside record; degree_contexts stays empty pending reviewed tonal binding",
            "cell.source": "source_catalog TXT line passage and PDF page passage with exact text hashes; record.source_refs/authored_text_refs",
            "cell.printed_passes/printed_pick_reset_instruction/hand_note/position_dna/root_locations/turnaround": "source_cell retained verbatim; record.context uses only printed position/turnaround and authored D/U variant availability",
            "cell.timing_basis": "record.timing unresolved; note onset_q/duration_q remain null",
        },
        "required_decisions": [
            "Explicit current-head stable course/workbook/module/item/event/variant allocation and lineage, with no reused IDs",
            "Curriculum review of all five cells, instrument tuning/capo basis, printed degree/root interpretation and source instructions",
            "Expected-profile, event-source and authority bindings for a schema1 validation package",
            "Playback beat unit, per-event timing, pick/accent realization and admission decision, if ever supported",
            "Remaining Level 70 seams, horizontal lanes, descents, full-register routes and workout coverage",
        ],
        "validator_ready": False,
        "validator_block": "Required stable IDs, allocation baseline, lineage and independently bound expected profile are absent; null identity fields intentionally refuse canonical validation.",
    }


def require_moduleb_cell(row: dict[str, Any], pair: dict[str, Any], lines: list[str], pages: dict[int, str]) -> dict[str, Any]:
    candidate = row["candidate"]
    seam = row["position"].removeprefix("module-b-")
    if seam not in MODULE_B_SPECS or row["position"] != f"module-b-{seam}":
        raise AdapterError("Module B seam position drift")
    _, _, page, first_line, panel = MODULE_B_SPECS[seam]
    label = seam.upper()
    if not isinstance(candidate, dict) or candidate.get("workstream") != "2.3.1.2.1" or candidate.get("review") != "Pending":
        raise AdapterError("Module B workstream/review drift")
    if candidate.get("candidate_kind") != "detached_schema_shaped_source_conversion" or candidate.get("schema_basis") != "1.0.0-curriculum-candidate; local key only, no canonical identity allocation" or candidate.get("source_pdf_pages") != 20:
        raise AdapterError("Module B detached candidate basis drift")
    if any(candidate.get(flag) is not False for flag in ("admitted", "imported", "runtime_eligible", "whole_workbook_complete")):
        raise AdapterError("Module B false admission flag drift")
    if candidate.get("contradictions") != [] or not isinstance(candidate.get("pending"), list) or not candidate["pending"]:
        raise AdapterError("Module B pending/contradiction drift")
    cells = candidate.get("selected_cells")
    if not isinstance(cells, list) or len(cells) != 1 or not isinstance(cells[0], dict):
        raise AdapterError("Module B requires one selected seam")
    cell = cells[0]
    source = cell.get("source")
    if cell.get("local_key") != f"level070-module-b-seam-{seam}" or cell.get("key") != "A melodic minor" or cell.get("seam") != label or cell.get("structure") != "six ordered single-string seven-tone exact-return loops" or cell.get("printed_tone_count") != 42:
        raise AdapterError("Module B seam identity/count drift")
    if not isinstance(source, dict) or source.get("pdf_page") != page or source.get("txt_lines") != list(range(first_line, first_line + 8)) or candidate.get("selected_pdf_pages") != [page]:
        raise AdapterError("Module B selected source span drift")
    if source.get("pdf_page_text_sha256") != sha(pages[page].encode("utf-8")):
        raise AdapterError("Module B PDF page text drift")
    if lines[first_line - 1] != f"SEAM {label}" or "42 tones" not in lines[first_line + 6] or cell.get("printed_repeat_instruction_txt") not in lines[first_line + 6]:
        raise AdapterError("Module B TXT instruction drift")
    page_text = pages[page]
    if cell.get("printed_orientation_and_shift_instruction_pdf") not in page_text or f"Seam {label} - 6 strings x 7 tones = 42 tones" not in page_text:
        raise AdapterError("Module B PDF instruction drift")
    if cell.get("performed_repeat_count") is not None or cell.get("timing_basis") != "unresolved: ordered printed tones and shift instruction only; no numeric onset, duration or shift event":
        raise AdapterError("Module B invented repeat or timing")
    deg_lines = [text for text in page_text.splitlines() if text.startswith("Deg|")]
    finger_lines = [text for text in page_text.splitlines() if text.startswith("Fng|")]
    if len(deg_lines) < 2 or len(finger_lines) < 2:
        raise AdapterError("Module B PDF grid missing")
    pdf_degrees = [re.findall(r"b3|[1-7]", part) for part in deg_lines[panel].split("|")[1:-1]]
    pdf_fingers = [re.findall(r"[1-4]", part) for part in finger_lines[panel].split("|")[1:-1]]
    loops = cell.get("string_loops")
    if not isinstance(loops, list) or len(loops) != 6 or len(pdf_degrees) != 6 or len(pdf_fingers) != 6:
        raise AdapterError("Module B six-loop PDF coverage missing")
    for index, loop in enumerate(loops):
        string = index + 1
        name = ("E", "A", "D", "G", "B", "e")[index]
        txt_line = first_line + 1 + index
        if not isinstance(loop, dict) or loop.get("string") != string or loop.get("string_name") != name or loop.get("source_txt_line") != txt_line or loop.get("printed_tone_count") != 7 or loop.get("exact_return") is not True:
            raise AdapterError(f"Module B loop identity drift: {string}")
        parts = lines[txt_line - 1].split(" | ")
        if len(parts) != 3 or not parts[0].startswith(f"{name}: frets ") or not parts[1].startswith("notes ") or not parts[2].startswith("degrees "):
            raise AdapterError(f"Module B TXT loop syntax drift: {string}")
        frets = [int(value) for value in parts[0].split("frets ", 1)[1].split("-")]
        spellings = parts[1][6:].split("-")
        degrees = parts[2][8:].split("-")
        notes = loop.get("notes")
        if not isinstance(notes, list) or len(notes) != 7 or len(frets) != 7 or len(spellings) != 7 or len(degrees) != 7 or len(pdf_degrees[index]) != 7 or len(pdf_fingers[index]) != 7:
            raise AdapterError(f"Module B seven-note loop missing: {string}")
        if frets != frets[::-1] or loop.get("lower_outer_fret") != frets[0] or loop.get("new_destination_fret") != frets[3] or loop.get("shared_anchor_frets") != frets[1:3]:
            raise AdapterError(f"Module B shared-anchor return drift: {string}")
        for ordinal, note in enumerate(notes, 1):
            value = note.get("schema_event_without_canonical_id") if isinstance(note, dict) else None
            if not isinstance(value, dict) or set(value) != NOTE_KEYS or value.get("kind") != "note" or value.get("attack") != "picked" or value.get("onset_q") is not None or value.get("duration_q") is not None or value.get("tie_from") is not None:
                raise AdapterError(f"Module B non-schema note or invented timing: {string}:{ordinal}")
            if note.get("ordinal_in_loop") != ordinal or note.get("txt_line") != txt_line or note.get("pdf_page") != page or note.get("pdf_page_text_sha256") != source["pdf_page_text_sha256"] or note.get("pick_stroke") is not None:
                raise AdapterError(f"Module B note provenance or performed pick drift: {string}:{ordinal}")
            fret, spelling, degree = frets[ordinal - 1], spellings[ordinal - 1], degrees[ordinal - 1]
            finger = int(pdf_fingers[index][ordinal - 1])
            if note.get("printed_degree") != degree or note.get("printed_degree") != pdf_degrees[index][ordinal - 1] or note.get("printed_finger") != finger or value.get("finger") != finger:
                raise AdapterError(f"Module B degree/finger drift: {string}:{ordinal}")
            if value.get("string") != string or value.get("fret") != fret or value.get("spelling") != spelling or value.get("midi") != OPEN_MIDI[index] + fret or value.get("degree_contexts") != {}:
                raise AdapterError(f"Module B pitch/source drift: {string}:{ordinal}")
    return cell


def build_moduleb_extension(root: Path, pdf_pages: dict[int, str] | None = None,
                            seams: tuple[str, ...] = ("p1-p2",)) -> dict[str, Any]:
    root = root.resolve(strict=True)
    if not seams or len(seams) != len(set(seams)) or any(seam not in MODULE_B_SPECS for seam in seams):
        raise AdapterError("Module B seam selection invalid or duplicated")
    if list(seams) != [seam for seam in MODULE_B_SPECS if seam in seams]:
        raise AdapterError("Module B seams must follow printed order")
    proposal = build_proposal(root, pdf_pages=pdf_pages)
    rows = [load_moduleb_candidate(root, MODULE_B_SPECS[seam][0]) for seam in seams]
    pair, lines, pages = validate_sources(root, rows, pdf_pages)
    if pair != proposal["source_pair"]:
        raise AdapterError("Module B source pair differs from P1-P5")
    proposal["schema"] = "fathom-level070-batch-adapter-proposal.2"
    proposal["module_b_blocks"] = []
    for row in rows:
        cell = require_moduleb_cell(row, pair, lines, pages)
        refs: list[str] = []
        for kind in ("txt", "pdf"):
            ref, passage = source_catalog_entry(kind, pair, lines, pages, cell)
            if ref in proposal["source_catalog"]:
                if proposal["source_catalog"][ref] != passage:
                    raise AdapterError(f"Module B source passage collision: {ref}")
            else:
                proposal["source_catalog"][ref] = passage
            refs.append(ref)
        notes = [note for loop in cell["string_loops"] for note in loop["notes"]]
        unresolved = [item["reason"] for item in row["candidate"]["pending"]]
        unresolved += ["Opaque item/event identities, numeric timing and performed repeat/pick/shift mechanics require explicit review."]
        record = {
            "id": None, "workbook_id": None, "module_id": None, "legacy_level": 70,
            "title": f"Level 70 Module B {cell['seam']} shared-anchor seam", "kind": "notation",
            "content_revision": None, "status": "converted_candidate", "runtime_eligible": False,
            "source_refs": refs, "authored_text_refs": refs, "normalization": [],
            "context": {"local_code": cell["local_key"], "seam": cell["seam"], "printed_repeat_instruction": cell["printed_repeat_instruction_txt"]},
            "events": [{**copy.deepcopy(note["schema_event_without_canonical_id"]), "event_id": None} for note in notes],
            "timing": {"status": "unresolved", "unit": "quarter", "basis": cell["timing_basis"]},
            "rubric": None, "resource_requirements": [], "ambiguities": unresolved,
            "control_scope": {"local_case": cell["local_key"], "extent": "selected_seam", "whole_workbook_complete": False,
                              "source_event_count": 42, "basis_refs": refs, "unresolved": unresolved},
            "variants": [], "lineage": None,
        }
        proposal["module_b_blocks"].append({"key": cell["local_key"], "candidate_path": row["path"],
            "candidate_sha256": row["sha256"], "record_projection": record, "source_cell": cell,
            "candidate_pending": row["candidate"]["pending"],
            "event_provenance": [{key: value for key, value in note.items() if key != "schema_event_without_canonical_id"} for note in notes]})
        proposal["required_decisions"].append(f"Module B {cell['seam']} repeat orientation, shift and per-event pick/timing decisions remain unadmitted")
    proposal["counts"] = {"positions": 5, "module_b_blocks": len(rows), "source_tones": 180 + 42 * len(rows),
                          "record_projections": 5 + len(rows), "source_passages": len(proposal["source_catalog"])}
    proposal["validator_block"] = "Module B and P1-P5 lack reviewed stable IDs, timing, current-head allocation, lineage and independently bound expected profile."
    for seam in seams:
        load_moduleb_candidate(root, MODULE_B_SPECS[seam][0])
    validate_sources(root, rows, pages)
    return proposal


def require_modulecd_block(row: dict[str, Any], lines: list[str], pages: dict[int, str]) -> list[dict[str, Any]]:
    block = row["position"]
    if block not in MODULE_CD_SPECS:
        raise AdapterError("unknown Module C/D block")
    _, _, _, page, starts, counts, identities = MODULE_CD_SPECS[block]
    candidate = row["candidate"]
    if not isinstance(candidate, dict) or candidate.get("workstream") != "2.3.1.2.1" or candidate.get("review") != "Pending" or candidate.get("candidate_kind") != "detached_schema_shaped_source_conversion":
        raise AdapterError(f"Module C/D candidate identity drift: {block}")
    if candidate.get("schema_basis") != "1.0.0-curriculum-candidate; local keys only, no canonical identity allocation" or candidate.get("source_pdf_pages") != 20 or candidate.get("selected_pdf_pages") != [page]:
        raise AdapterError(f"Module C/D schema/page drift: {block}")
    if any(candidate.get(flag) is not False for flag in ("admitted", "imported", "runtime_eligible", "whole_workbook_complete")) or candidate.get("contradictions") != []:
        raise AdapterError(f"Module C/D admission/contradiction drift: {block}")
    pending = candidate.get("pending")
    if not isinstance(pending, list) or not pending or any(not isinstance(item, dict) or not isinstance(item.get("reason"), str) or not item["reason"] for item in pending):
        raise AdapterError(f"Module C/D unresolved ledger missing: {block}")
    cells = candidate.get("selected_cells")
    if not isinstance(cells, list) or len(cells) != len(counts) or candidate.get("printed_tone_count") != sum(counts):
        raise AdapterError(f"Module C/D selected cell count drift: {block}")
    page_text = pages.get(page)
    if not isinstance(page_text, str) or not page_text:
        raise AdapterError(f"Module C/D PDF page absent: {block}")
    page_hash = sha(page_text.encode("utf-8"))
    family = "c" if block.startswith("c-") else "d"
    for index, (cell, first, count, identity) in enumerate(zip(cells, starts, counts, identities)):
        if not isinstance(cell, dict) or cell.get("printed_tone_count") != count:
            raise AdapterError(f"Module C/D cell count drift: {block}:{index}")
        source = cell.get("source")
        span = 9 if family == "c" else 10
        if not isinstance(source, dict) or source.get("pdf_page") != page or source.get("pdf_page_text_sha256") != page_hash or source.get("txt_lines") != list(range(first, first + span)):
            raise AdapterError(f"Module C/D source span or PDF drift: {block}:{index}")
        if family == "c":
            name = ("E", "A", "D", "G", "B", "e")[identity - 1]
            side = block.removeprefix("c-")
            if cell.get("local_key") != f"level070-module-c-{side}-{name.lower()}-lane" or cell.get("string") != identity or cell.get("string_name") != name:
                raise AdapterError(f"Module C lane identity drift: {block}:{index}")
            if cell.get("exact_reverse_descent") is not True or cell.get("upper_endpoint_repeated_in_print") is not True or cell.get("ascent_count") != count // 2 or cell.get("descent_count") != count // 2 or cell.get("performed_pass_count") is not None:
                raise AdapterError(f"Module C lane/pass drift: {block}:{index}")
            instructions = ("printed_pass_instruction_pdf", "printed_shift_instruction_pdf")
        else:
            if cell.get("local_key") != f"level070-module-d-p{identity}-grouped-pattern" or cell.get("printed_label") != f"P{identity}" or cell.get("performed_translation_count") is not None:
                raise AdapterError(f"Module D pattern/translation drift: {block}:{index}")
            instructions = ("printed_pick_cycle_and_contour_instruction_pdf", "printed_translation_instruction_pdf") if page == 12 else (
                "printed_descent_start_instruction_pdf", "printed_overlap_pick_instruction_pdf", "printed_translation_instruction_pdf")
        for key in instructions:
            instruction = cell.get(key)
            if not isinstance(instruction, str) or not instruction or instruction not in page_text:
                raise AdapterError(f"Module C/D PDF instruction drift: {block}:{index}:{key}")
        if page == 13:
            txt_instruction = cell.get("printed_translation_instruction_txt")
            if not isinstance(txt_instruction, str) or not any(txt_instruction in line for line in lines):
                raise AdapterError(f"Module D TXT translation instruction drift: {block}:{index}")
        if not lines[first - 1].lstrip().startswith((f"{name} STRING" if family == "c" else f"P{identity} -")):
            raise AdapterError(f"Module C/D TXT heading drift: {block}:{index}")
        source_notes = re.findall(r"[A-G](?:#|b)?", lines[first].split("|", 1)[1])
        source_degrees = re.findall(r"b3|[1-7]", lines[first + 1].split("|", 1)[1])
        source_fingers = re.findall(r"[1-4]", lines[first + 2].split("|", 1)[1]) if family == "d" else []
        notes = cell.get("notes")
        if not isinstance(notes, list) or len(notes) != count or len(source_notes) != count or len(source_degrees) != count or (family == "d" and len(source_fingers) != count):
            raise AdapterError(f"Module C/D printed note rows missing: {block}:{index}")
        for ordinal, note in enumerate(notes, 1):
            value = note.get("schema_event_without_canonical_id") if isinstance(note, dict) else None
            if not isinstance(value, dict) or set(value) != NOTE_KEYS or value.get("kind") != "note" or value.get("attack") is not None or value.get("onset_q") is not None or value.get("duration_q") is not None or value.get("tie_from") is not None or value.get("degree_contexts") != {}:
                raise AdapterError(f"Module C/D invented note mechanics: {block}:{index}:{ordinal}")
            ordinal_key = "ordinal_in_printed_lane" if family == "c" else "ordinal_in_printed_pattern"
            locators = note.get("txt_lines")
            required_locators = {"note", "degree", "tab"} if family == "c" else {"note", "degree", "finger", "tab"}
            if note.get(ordinal_key) != ordinal or note.get("pdf_page") != page or note.get("pdf_page_text_sha256") != page_hash or note.get("pick_stroke") is not None or not isinstance(locators, dict) or set(locators) != required_locators or any(type(n) is not int or n not in source["txt_lines"] for n in locators.values()):
                raise AdapterError(f"Module C/D note provenance drift: {block}:{index}:{ordinal}")
            if locators["note"] != first + 1 or locators["degree"] != first + 2 or (family == "d" and locators["finger"] != first + 3):
                raise AdapterError(f"Module C/D TXT row locator drift: {block}:{index}:{ordinal}")
            string, fret = value.get("string"), value.get("fret")
            if type(string) is not int or not 1 <= string <= 6 or type(fret) is not int or not 0 <= fret <= 24 or value.get("midi") != OPEN_MIDI[string - 1] + fret or value.get("spelling") != source_notes[ordinal - 1] or note.get("printed_degree") != source_degrees[ordinal - 1]:
                raise AdapterError(f"Module C/D source note drift: {block}:{index}:{ordinal}")
            tab_name = ("E", "A", "D", "G", "B", "e")[string - 1]
            if not lines[locators["tab"] - 1].lstrip().startswith(tab_name + "|"):
                raise AdapterError(f"Module C/D TAB locator drift: {block}:{index}:{ordinal}")
            if family == "c":
                if string != identity or value.get("finger") is not None or "printed_finger" in note:
                    raise AdapterError(f"Module C unsupported finger drift: {block}:{index}:{ordinal}")
            elif note.get("printed_finger") != int(source_fingers[ordinal - 1]) or value.get("finger") != note["printed_finger"]:
                raise AdapterError(f"Module D printed finger drift: {block}:{index}:{ordinal}")
        if family == "c":
            values = [note["schema_event_without_canonical_id"] for note in notes]
            if values[count // 2:] != values[:count // 2][::-1] or cell.get("printed_fret_range") != [min(v["fret"] for v in values), max(v["fret"] for v in values)]:
                raise AdapterError(f"Module C reversed endpoint/fret range drift: {block}:{index}")
    return cells


def build_modulecd_extension(root: Path, blocks: tuple[str, ...],
                             moduleb_seams: tuple[str, ...] = (),
                             pdf_pages: dict[int, str] | None = None) -> dict[str, Any]:
    root = root.resolve(strict=True)
    if not blocks or len(blocks) != len(set(blocks)) or any(block not in MODULE_CD_SPECS for block in blocks):
        raise AdapterError("Module C/D block selection invalid or duplicated")
    if list(blocks) != [block for block in MODULE_CD_SPECS if block in blocks]:
        raise AdapterError("Module C/D blocks must follow source order")
    proposal = build_moduleb_extension(root, pdf_pages, moduleb_seams) if moduleb_seams else build_proposal(root, pdf_pages=pdf_pages)
    rows = [load_modulecd_candidate(root, block) for block in blocks]
    pair, lines, pages = validate_sources(root, rows, pdf_pages)
    if pair != proposal["source_pair"]:
        raise AdapterError("Module C/D source pair differs from prior blocks")
    proposal["schema"] = "fathom-level070-batch-adapter-proposal.3"
    proposal["module_c_blocks"] = []
    proposal["module_d_blocks"] = []
    tone_count = proposal["counts"]["source_tones"]
    record_count = proposal["counts"]["record_projections"]
    for row in rows:
        cells = require_modulecd_block(row, lines, pages)
        family = "c" if row["position"].startswith("c-") else "d"
        target = proposal["module_c_blocks"] if family == "c" else proposal["module_d_blocks"]
        for cell in cells:
            refs: list[str] = []
            for kind in ("txt", "pdf"):
                ref, passage = source_catalog_entry(kind, pair, lines, pages, cell)
                if ref in proposal["source_catalog"]:
                    if proposal["source_catalog"][ref] != passage:
                        raise AdapterError(f"Module C/D source passage collision: {ref}")
                else:
                    proposal["source_catalog"][ref] = passage
                refs.append(ref)
            notes = cell["notes"]
            unresolved = [item["reason"] for item in row["candidate"]["pending"]]
            unresolved += ["Opaque identities, performed pass/translation, pick/shift mechanics and numeric timing remain Pending."]
            instructions = [value for key, value in cell.items() if key.startswith("printed_") and "instruction" in key and isinstance(value, str)]
            record = {
                "id": None, "workbook_id": None, "module_id": None, "legacy_level": 70,
                "title": "Level 70 " + ("Module C lane " if family == "c" else "Module D pattern ") + cell["local_key"],
                "kind": "notation", "content_revision": None, "status": "converted_candidate", "runtime_eligible": False,
                "source_refs": refs, "authored_text_refs": refs, "normalization": [],
                "context": {"local_code": cell["local_key"], "printed_instructions": instructions},
                "events": [{**copy.deepcopy(note["schema_event_without_canonical_id"]), "event_id": None} for note in notes],
                "timing": {"status": "unresolved", "unit": "quarter", "basis": "Printed source order only; no per-event numeric onset or duration"},
                "rubric": None, "resource_requirements": [], "ambiguities": unresolved,
                "control_scope": {"local_case": cell["local_key"], "extent": "selected_source_block",
                                  "whole_workbook_complete": False, "source_event_count": len(notes),
                                  "basis_refs": refs, "unresolved": unresolved},
                "variants": [], "lineage": None,
            }
            target.append({"key": cell["local_key"], "candidate_path": row["path"],
                "candidate_sha256": row["sha256"], "record_projection": record, "source_cell": cell,
                "candidate_pending": row["candidate"]["pending"],
                "event_provenance": [{key: value for key, value in note.items() if key != "schema_event_without_canonical_id"} for note in notes]})
            tone_count += len(notes)
            record_count += 1
    proposal["counts"] = {**proposal["counts"], "module_c_blocks": len(proposal["module_c_blocks"]),
                          "module_d_blocks": len(proposal["module_d_blocks"]),
                          "source_tones": tone_count, "record_projections": record_count,
                          "source_passages": len(proposal["source_catalog"])}
    proposal["required_decisions"].append("Module C/D performed passes, translations, fingering where unprinted, shift/pick realization, timing and admission remain unresolved")
    proposal["validator_block"] = "Module C/D and preceding blocks lack reviewed stable IDs, timing, current-head allocation, lineage and independently bound expected profile."
    for block in blocks:
        load_modulecd_candidate(root, block)
    validate_sources(root, rows, pages)
    return proposal


def require_moduleefgh_block(row: dict[str, Any], lines: list[str], pages: dict[int, str]) -> list[dict[str, Any]]:
    block = row["position"]
    if block not in MODULE_EFGH_SPECS:
        raise AdapterError("unknown Module E-H block")
    _, _, _, page, starts, counts = MODULE_EFGH_SPECS[block]
    family = block[0]
    candidate = row["candidate"]
    if not isinstance(candidate, dict) or candidate.get("workstream") != "2.3.1.2.1" or candidate.get("review") != "Pending" or candidate.get("candidate_kind") != "detached_schema_shaped_source_conversion":
        raise AdapterError(f"Module E-H candidate identity drift: {block}")
    if candidate.get("schema_basis") != "1.0.0-curriculum-candidate; local keys only, no canonical identity allocation" or candidate.get("source_pdf_pages") != 20 or candidate.get("selected_pdf_pages") != [page]:
        raise AdapterError(f"Module E-H schema/page drift: {block}")
    if any(candidate.get(flag) is not False for flag in ("admitted", "imported", "runtime_eligible", "whole_workbook_complete")) or candidate.get("contradictions") != []:
        raise AdapterError(f"Module E-H admission/contradiction drift: {block}")
    pending = candidate.get("pending")
    if not isinstance(pending, list) or not pending or any(not isinstance(item, dict) or not isinstance(item.get("reason"), str) or not item["reason"] for item in pending):
        raise AdapterError(f"Module E-H unresolved ledger missing: {block}")
    selection = "selected_panels" if family == "h" else "selected_cells"
    cells = candidate.get(selection)
    if not isinstance(cells, list) or len(cells) != len(counts) or candidate.get("printed_tone_count") != sum(counts) or (family == "h" and candidate.get("printed_bar_count") != 16):
        raise AdapterError(f"Module E-H selected cell count drift: {block}")
    page_text = pages.get(page)
    if not isinstance(page_text, str) or not page_text:
        raise AdapterError(f"Module E-H PDF page absent: {block}")
    page_hash = sha(page_text.encode("utf-8"))
    for index, (cell, first, count) in enumerate(zip(cells, starts, counts)):
        if not isinstance(cell, dict) or cell.get("printed_tone_count") != count or not isinstance(cell.get("local_key"), str) or not cell["local_key"].startswith(f"level070-module-{family}-"):
            raise AdapterError(f"Module E-H cell identity/count drift: {block}:{index}")
        span = 5 if family == "f" else 10
        source = cell.get("source")
        if not isinstance(source, dict) or source.get("pdf_page") != page or source.get("pdf_page_text_sha256") != page_hash or source.get("txt_lines") != list(range(first, first + span)):
            raise AdapterError(f"Module E-H source span or PDF drift: {block}:{index}")
        if first + span - 1 > len(lines) or not isinstance(cell.get("printed_label"), str) or not lines[first - 1].strip().startswith(cell["printed_label"]):
            raise AdapterError(f"Module E-H TXT heading drift: {block}:{index}")
        if family == "e":
            expected_position = (index + 1) if page == 14 else (5 - index)
            direction = ("ASC" if index % 2 == 0 else "DESC") if page == 14 else ("DESC" if index % 2 == 0 else "ASC")
            if cell.get("local_key") != f"level070-module-e-{'forward' if page == 14 else 'reverse'}-p{expected_position}-{direction.lower()}" or cell.get("direction") != direction or cell.get("performed_repair_count") is not None:
                raise AdapterError(f"Module E segment/repair drift: {block}:{index}")
            instructions = ("printed_boundary_instruction_pdf", "printed_connection_audit_pdf", "printed_preview_instruction_pdf")
        elif family == "f":
            if cell.get("performed_descent_choice") is not None or cell.get("observed_error") is not None or cell.get("printed_formula_txt") != lines[first + 3]:
                raise AdapterError(f"Module F choice/formula drift: {block}:{index}")
            instructions = ("printed_choice_instruction_pdf", "printed_formula_pdf", "printed_stop_rule_pdf")
        elif family == "g":
            if any(cell.get(key) is not None for key in ("performed_pass", "observed_barline_delay", "observed_cadence")) or cell.get("printed_chords") != ["AmMaj7", "D7", "E7", "AmMaj7"]:
                raise AdapterError(f"Module G pass/cadence drift: {block}:{index}")
            instructions = ("printed_barline_instruction_pdf", "printed_cadence_instruction_pdf", "printed_rhythm_instruction_pdf")
        else:
            if any(cell.get(key) is not None for key in ("performed_ending", "observed_region_change")) or cell.get("printed_bar_range") != [4 * index + 1, 4 * index + 4] or cell.get("printed_position") != ("P1", "P2", "P4", "P5")[index]:
                raise AdapterError(f"Module H panel/ending drift: {block}:{index}")
            if len(lines) < 498 or lines[497] != "Final bar: " + cell.get("printed_final_bar_instruction_pdf", ""):
                raise AdapterError(f"Module H TXT final-bar instruction drift: {block}:{index}")
            instructions = ("printed_capstone_instruction_pdf", "printed_final_bar_instruction_pdf", "printed_harmonic_region_instruction_pdf")
        for key in instructions:
            value = cell.get(key)
            if not isinstance(value, str) or not value or value not in page_text:
                raise AdapterError(f"Module E-H PDF instruction drift: {block}:{index}:{key}")
        for key in ("printed_chords",) if family in ("g", "h") else ():
            if not isinstance(cell.get(key), list) or len(cell[key]) != 4:
                raise AdapterError(f"Module E-H chord context drift: {block}:{index}")
        note_row = lines[first].split("|", 1)
        degree_row = lines[first + 1].split("|", 1)
        if len(note_row) != 2 or len(degree_row) != 2:
            raise AdapterError(f"Module E-H note/degree TXT row missing: {block}:{index}")
        source_notes = re.findall(r"[A-G](?:#|b)?", note_row[1])
        source_degrees = re.findall(r"b[367]|[1-7]", degree_row[1])
        source_fingers = re.findall(r"[1-4]", lines[first + 2].split("|", 1)[1]) if family == "e" else []
        source_roles = re.findall(r">?(?:b3|b5|b7|#5|R|[1-7])", lines[first + 2].split("|", 1)[1]) if family in ("g", "h") else []
        notes = cell.get("notes")
        if not isinstance(notes, list) or len(notes) != count or len(source_notes) != count or len(source_degrees) != count or (family == "e" and len(source_fingers) != count) or (family in ("g", "h") and len(source_roles) != count):
            raise AdapterError(f"Module E-H printed rows missing: {block}:{index}")
        for ordinal, note in enumerate(notes, 1):
            value = note.get("schema_event_without_canonical_id") if isinstance(note, dict) else None
            if not isinstance(value, dict) or set(value) != NOTE_KEYS or value.get("kind") != "note" or any(value.get(key) is not None for key in ("attack", "onset_q", "duration_q", "tie_from")) or value.get("degree_contexts") != {}:
                raise AdapterError(f"Module E-H invented note mechanics: {block}:{index}:{ordinal}")
            locators = note.get("txt_lines")
            expected_locators = {"note", "degree", "tab"} | ({"finger"} if family == "e" else set()) | ({"role"} if family in ("g", "h") else set())
            if not isinstance(locators, dict) or set(locators) != expected_locators or any(type(n) is not int or n not in source["txt_lines"] for n in locators.values()):
                raise AdapterError(f"Module E-H note provenance drift: {block}:{index}:{ordinal}")
            if locators["note"] != first + 1 or locators["degree"] != first + 2 or (family == "e" and locators["finger"] != first + 3) or (family in ("g", "h") and locators["role"] != first + 3):
                raise AdapterError(f"Module E-H TXT row locator drift: {block}:{index}:{ordinal}")
            string, fret = value.get("string"), value.get("fret")
            if type(string) is not int or not 1 <= string <= 6 or type(fret) is not int or not 0 <= fret <= 24 or value.get("midi") != OPEN_MIDI[string - 1] + fret or value.get("spelling") != source_notes[ordinal - 1]:
                raise AdapterError(f"Module E-H pitch/spelling drift: {block}:{index}:{ordinal}")
            tab_name = ("E", "A", "D", "G", "B", "e")[string - 1]
            if not lines[locators["tab"] - 1].lstrip().startswith(tab_name + "|"):
                raise AdapterError(f"Module E-H TAB locator drift: {block}:{index}:{ordinal}")
            if note.get("pdf_page") != page or note.get("pdf_page_text_sha256") != page_hash or note.get("pick_stroke") is not None or note.get("printed_degree", note.get("printed_scale_degree")) != source_degrees[ordinal - 1]:
                raise AdapterError(f"Module E-H degree/PDF/pick drift: {block}:{index}:{ordinal}")
            if family == "e":
                page_ordinal = "ordinal_in_printed_forward_page" if page == 14 else "ordinal_in_printed_reverse_page"
                if note.get(page_ordinal) != 18 * index + ordinal or note.get("ordinal_in_printed_segment") != ordinal or note.get("printed_finger") != int(source_fingers[ordinal - 1]) or value.get("finger") != note["printed_finger"]:
                    raise AdapterError(f"Module E ordinal/finger drift: {block}:{index}:{ordinal}")
            elif family == "f":
                if note.get("ordinal_in_printed_cell") != ordinal or note.get("printed_form") != ("ASC", "SYM", "CLS")[(ordinal - 1) // 4] or value.get("finger") is not None:
                    raise AdapterError(f"Module F form/finger drift: {block}:{index}:{ordinal}")
            else:
                role = source_roles[ordinal - 1]
                if note.get("ordinal_in_bar") != ((ordinal - 1) % 4) + 1 or note.get("printed_chord_role") != role.lstrip(">") or value.get("finger") is not None or note.get("printed_chord") != cell["printed_chords"][(ordinal - 1) // 4]:
                    raise AdapterError(f"Module G/H chord role drift: {block}:{index}:{ordinal}")
                if family == "g":
                    if note.get("ordinal_in_printed_cell") != ordinal or note.get("printed_bar") != ((ordinal - 1) // 4) + 1 or note.get("printed_beat_one_marker") != role.startswith(">"):
                        raise AdapterError(f"Module G barline marker drift: {block}:{index}:{ordinal}")
                elif note.get("ordinal_in_printed_panel") != ordinal or note.get("ordinal_in_printed_capstone") != 16 * index + ordinal or note.get("printed_bar") != 4 * index + ((ordinal - 1) // 4) + 1 or note.get("printed_position") != cell["printed_position"] or note.get("printed_structural_target_marker") != role.startswith(">"):
                    raise AdapterError(f"Module H panel target drift: {block}:{index}:{ordinal}")
    return cells


def build_moduleefgh_extension(root: Path, blocks: tuple[str, ...],
                               modulecd_blocks: tuple[str, ...] = (),
                               moduleb_seams: tuple[str, ...] = (),
                               pdf_pages: dict[int, str] | None = None) -> dict[str, Any]:
    root = root.resolve(strict=True)
    if not blocks or len(blocks) != len(set(blocks)) or any(block not in MODULE_EFGH_SPECS for block in blocks):
        raise AdapterError("Module E-H block selection invalid or duplicated")
    if list(blocks) != [block for block in MODULE_EFGH_SPECS if block in blocks]:
        raise AdapterError("Module E-H blocks must follow source order")
    proposal = (build_modulecd_extension(root, modulecd_blocks, moduleb_seams, pdf_pages) if modulecd_blocks else
                build_moduleb_extension(root, pdf_pages, moduleb_seams) if moduleb_seams else
                build_proposal(root, pdf_pages=pdf_pages))
    rows = [load_moduleefgh_candidate(root, block) for block in blocks]
    pair, lines, pages = validate_sources(root, rows, pdf_pages)
    if pair != proposal["source_pair"]:
        raise AdapterError("Module E-H source pair differs from prior blocks")
    proposal["schema"] = "fathom-level070-batch-adapter-proposal.4"
    for family in "efgh":
        proposal[f"module_{family}_blocks"] = []
    tone_count = proposal["counts"]["source_tones"]
    record_count = proposal["counts"]["record_projections"]
    for row in rows:
        cells = require_moduleefgh_block(row, lines, pages)
        family = row["position"][0]
        target = proposal[f"module_{family}_blocks"]
        for cell in cells:
            refs: list[str] = []
            for kind in ("txt", "pdf"):
                ref, passage = source_catalog_entry(kind, pair, lines, pages, cell)
                if ref in proposal["source_catalog"]:
                    if proposal["source_catalog"][ref] != passage:
                        raise AdapterError(f"Module E-H source passage collision: {ref}")
                else:
                    proposal["source_catalog"][ref] = passage
                refs.append(ref)
            if family == "h":
                ref, passage = source_catalog_entry("txt", pair, lines, pages, {"source": {"txt_lines": [498]}})
                if ref in proposal["source_catalog"]:
                    if proposal["source_catalog"][ref] != passage:
                        raise AdapterError(f"Module H final-bar passage collision: {ref}")
                else:
                    proposal["source_catalog"][ref] = passage
                refs.append(ref)
            notes = cell["notes"]
            unresolved = [item["reason"] for item in row["candidate"]["pending"]]
            unresolved += ["Opaque identities, performed mechanics, interpretation and numeric timing remain Pending."]
            instructions = [value for key, value in cell.items() if key.startswith("printed_") and ("instruction" in key or "audit" in key or "formula" in key) and isinstance(value, str)]
            record = {
                "id": None, "workbook_id": None, "module_id": None, "legacy_level": 70,
                "title": f"Level 70 Module {family.upper()} {cell['local_key']}", "kind": "notation",
                "content_revision": None, "status": "converted_candidate", "runtime_eligible": False,
                "source_refs": refs, "authored_text_refs": refs, "normalization": [],
                "context": {"local_code": cell["local_key"], "printed_instructions": instructions,
                            **({"printed_final_bar_instruction_txt": lines[497]} if family == "h" else {})},
                "events": [{**copy.deepcopy(note["schema_event_without_canonical_id"]), "event_id": None} for note in notes],
                "timing": {"status": "unresolved", "unit": "quarter", "basis": "Printed source order only; no per-event numeric onset or duration"},
                "rubric": None, "resource_requirements": [], "ambiguities": unresolved,
                "control_scope": {"local_case": cell["local_key"], "extent": "selected_source_block",
                                  "whole_workbook_complete": False, "source_event_count": len(notes),
                                  "basis_refs": refs, "unresolved": unresolved},
                "variants": [], "lineage": None,
            }
            target.append({"key": cell["local_key"], "candidate_path": row["path"],
                "candidate_sha256": row["sha256"], "record_projection": record, "source_cell": cell,
                "candidate_pending": row["candidate"]["pending"],
                "event_provenance": [{key: value for key, value in note.items() if key != "schema_event_without_canonical_id"} for note in notes]})
            tone_count += len(notes)
            record_count += 1
    proposal["counts"] = {**proposal["counts"], **{f"module_{family}_blocks": len(proposal[f"module_{family}_blocks"]) for family in "efgh"},
                          "source_tones": tone_count, "record_projections": record_count,
                          "source_passages": len(proposal["source_catalog"])}
    proposal["required_decisions"].append("Module E-H performed mechanics, interpretation, timing and admission remain unresolved")
    proposal["validator_block"] = "Modules E-H and preceding blocks lack reviewed stable IDs, timing, current-head allocation, lineage and independently bound expected profile."
    for block in blocks:
        load_moduleefgh_candidate(root, block)
    validate_sources(root, rows, pages)
    return proposal


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--module-b-p1-p2", action="store_true", help="include the pinned Module B P1-P2 seam as a detached source block")
    parser.add_argument("--module-b-p2-p3", action="store_true", help="include the pinned Module B P2-P3 seam")
    parser.add_argument("--module-b-p3-p4", action="store_true", help="include the pinned Module B P3-P4 seam")
    parser.add_argument("--module-b-p4-p5", action="store_true", help="include the pinned Module B P4-P5 seam")
    parser.add_argument("--module-b-all", action="store_true", help="include all four pinned Module B seams")
    parser.add_argument("--module-c-low", action="store_true", help="include the pinned Module C lower-string lanes")
    parser.add_argument("--module-c-upper", action="store_true", help="include the pinned Module C upper-string lanes")
    parser.add_argument("--module-d-p1-p3", action="store_true", help="include the pinned Module D P1-P3 grouped patterns")
    parser.add_argument("--module-d-p4-p5", action="store_true", help="include the pinned Module D P4-P5 grouped patterns")
    parser.add_argument("--module-cd-all", action="store_true", help="include all four pinned Module C/D source blocks")
    parser.add_argument("--module-e-forward", action="store_true", help="include the pinned Module E forward segments")
    parser.add_argument("--module-e-reverse", action="store_true", help="include the pinned Module E reverse segments")
    parser.add_argument("--module-f-directional", action="store_true", help="include the pinned Module F directional cells")
    parser.add_argument("--module-g-lower", action="store_true", help="include the pinned Module G lower seams")
    parser.add_argument("--module-g-upper", action="store_true", help="include the pinned Module G upper seams")
    parser.add_argument("--module-h-capstone", action="store_true", help="include the pinned Module H capstone panels")
    parser.add_argument("--module-efgh-all", action="store_true", help="include all six pinned Module E-H source blocks")
    args = parser.parse_args()
    root = args.root.resolve(strict=True)
    git_root = subprocess.check_output(["git", "-C", str(root), "rev-parse", "--show-toplevel"], text=True).strip()
    if Path(git_root).resolve() != root:
        raise AdapterError("--root must be the Git checkout top level")
    try:
        selected = tuple(seam for seam, enabled in zip(MODULE_B_SPECS,
            (args.module_b_p1_p2, args.module_b_p2_p3, args.module_b_p3_p4, args.module_b_p4_p5)) if enabled)
        if args.module_b_all and selected:
            raise AdapterError("Module B all and individual seam flags conflict")
        seams = tuple(MODULE_B_SPECS) if args.module_b_all else selected
        selected_cd = tuple(block for block, enabled in zip(MODULE_CD_SPECS,
            (args.module_c_low, args.module_c_upper, args.module_d_p1_p3, args.module_d_p4_p5)) if enabled)
        if args.module_cd_all and selected_cd:
            raise AdapterError("Module C/D all and individual block flags conflict")
        blocks = tuple(MODULE_CD_SPECS) if args.module_cd_all else selected_cd
        selected_efgh = tuple(block for block, enabled in zip(MODULE_EFGH_SPECS,
            (args.module_e_forward, args.module_e_reverse, args.module_f_directional,
             args.module_g_lower, args.module_g_upper, args.module_h_capstone)) if enabled)
        if args.module_efgh_all and selected_efgh:
            raise AdapterError("Module E-H all and individual block flags conflict")
        efgh_blocks = tuple(MODULE_EFGH_SPECS) if args.module_efgh_all else selected_efgh
        report = (build_moduleefgh_extension(root, efgh_blocks, blocks, seams) if efgh_blocks else
                  build_modulecd_extension(root, blocks, seams) if blocks else
                  build_moduleb_extension(root, seams=seams) if seams else build_proposal(root))
        output = args.output if args.output.is_absolute() else root / args.output
        if efgh_blocks:
            if (root / "Build/parallel-06/2.3-level070-moduleefgh-adapter-r05").resolve() not in output.resolve(strict=False).parents:
                raise AdapterError("Module E-H output must stay in its Build lane")
        elif blocks:
            if (root / "Build/parallel-06/2.3-level070-modulecd-adapter-r04").resolve() not in output.resolve(strict=False).parents:
                raise AdapterError("Module C/D output must stay in its Build lane")
        elif seams:
            lane = "2.3-level070-moduleb-adapter-r02" if seams == ("p1-p2",) else "2.3-level070-moduleb-adapter-r03"
            if (root / "Build/parallel-06" / lane).resolve() not in output.resolve(strict=False).parents:
                raise AdapterError("Module B output must stay in its Build lane")
    except (AdapterError, FileNotFoundError) as exc:
        print(f"ADAPTER STOP: {exc}", file=sys.stderr)
        return 2
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, sort_keys=True, indent=2, ensure_ascii=False) + "\n")
    print(f"PROPOSAL PASS {output} positions={report['counts']['positions']} tones={report['counts']['source_tones']} validator_ready=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
