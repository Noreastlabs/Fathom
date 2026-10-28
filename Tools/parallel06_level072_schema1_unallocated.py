#!/usr/bin/env python3
"""Project sealed Level72 source into a detached, unallocated schema1 field view."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from curriculum_level072_whole_candidate import build_candidate


ROOT = Path(__file__).resolve().parents[1]
OUT_REL = Path("Build/parallel-06/level072-schema1-unallocated-r01")
INPUTS = {
    "Build/parallel-09/2.3.1.2.1-level072-whole-r01/level072-whole-candidate-01.json": "808ee690b90a9e82ec14308ec9375119a1d68c622b3f4251e976427e271abc36",
    "Build/parallel-06/2.3-level072-whole-coverage-r01/index-01.json": "9e82c33d8c416f46ead288b99b9c57321b2b39bf6da9e11ed2e365684a1c8a8c",
    "Content/controls/curriculum-v1/package.json": "766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255",
    "Content/controls/curriculum-v1/identity-registry.json": "5d265859e1e8a5a530a0e53d88b019a1c920f3bba6cccb4ef0fef2f7640007e5",
    "Results/primary/20260912T100538Z-2.1.1.2.1-r02-evidence/schema-freeze.json": "0659fa962a5c933a2bcf3045772b6fe5b05b4deefb3511f5dcb68af51088de95",
    "Tools/curriculum_level072_whole_candidate.py": "60013b78505e3248501aa9ae3961c5d275a56a2a1f3591bd1b5ba5a84e7cf747",
}
COUNTS = {"A": 80, "B": 48, "C": 80, "D": 48, "E": 40, "F": 80,
          "G": 80, "H": 64, "I": 32, "J": 64, "K": 24}
OPEN = {"E": (1, 40), "A": (2, 45), "D": (3, 50), "G": (4, 55),
        "B": (5, 59), "e": (6, 64)}
PC = {"C": 0, "B#": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3,
      "Eb": 3, "E": 4, "Fb": 4, "F": 5, "F#": 6, "G": 7,
      "G#": 8, "Ab": 8, "A": 9, "Bb": 10, "B": 11, "Cb": 11}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def encoded(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False,
                       separators=(",", ":")) + "\n").encode()


def read_inputs(root: Path) -> tuple[dict, dict, dict, dict, dict]:
    raw = {}
    for rel, expected in INPUTS.items():
        path = root / rel
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"missing or symlink input: {rel}")
        data = path.read_bytes()
        if digest(data) != expected:
            raise ValueError(f"input drift: {rel}")
        raw[rel] = data
    whole = json.loads(raw[next(iter(INPUTS))])
    if whole != build_candidate():
        raise ValueError("sealed candidate differs from original TXT/PDF replay")
    index = json.loads(raw[list(INPUTS)[1]])
    package = json.loads(raw[list(INPUTS)[2]])
    registry = json.loads(raw[list(INPUTS)[3]])
    freeze = json.loads(raw[list(INPUTS)[4]])
    if freeze.get("decision") != "Technical schema1 FROZEN" or freeze.get("schema_version") != "1.0.0-curriculum-candidate":
        raise ValueError("schema freeze drift")
    return whole, index, package, registry, freeze


def identity_boundary(package: dict, registry: dict) -> dict:
    wid = "fg:workbook:000072"
    if any(r.get("legacy_level") == 72 or r.get("workbook_id") == wid
           for r in package["records"]):
        raise ValueError("unexpected canonical Level72 record")
    if any(e.get("id") == wid for e in registry["entities"]):
        raise ValueError("unexpected Level72 registry entity")
    entries = [e for e in package["workbook_catalog"]["entries"]
               if e.get("workbook_id") == wid]
    if len(entries) != 1:
        raise ValueError("Level72 catalog identity drift")
    entry = entries[0]
    if (entry.get("conversion_status") != "not_converted"
            or entry.get("whole_workbook_complete") is not False
            or entry.get("admitted") is not False
            or entry.get("runtime_eligible") is not False
            or entry.get("representative_item_id") is not None):
        raise ValueError("Level72 source-only catalog drift")
    return entry


def event(contact: dict) -> dict:
    if (contact["canonical_event_id"] is not None
            or contact["onset_q"] is not None
            or contact["duration_q"] is not None
            or contact["performed_result"] is not None):
        raise ValueError("source contact identity or timing drift")
    note, string, fret = contact["printed_note"], contact["string"], contact["fret"]
    if note not in PC or string not in OPEN or type(fret) is not int or fret < 0:
        raise ValueError("invalid printed note or TAB")
    string_number, base = OPEN[string]
    midi = base + fret
    if midi % 12 != PC[note]:
        raise ValueError("printed note/TAB pitch mismatch")
    refs = contact["source_refs"]
    if not 1 <= refs["pdf_page"] <= 20 or not 1 <= refs["txt_note_line"] <= 614:
        raise ValueError("contact source reference drift")
    return {
        "source_module": contact["module"],
        "qualified_source_key": contact["qualified_source_key"],
        "source_local_ordinal": contact["source_order"],
        "printed_note": note,
        "printed_role_or_degree": contact["printed_role_or_degree"],
        "printed_pick": contact["printed_pick"],
        "source_string": string,
        "source_fret": fret,
        "source_refs": refs,
        "performed_result": None,
        "schema1_fields": {
            "event_id": None, "kind": "note", "attack": None,
            "spelling": note, "midi": midi, "string": string_number,
            "fret": fret, "finger": None, "degree_contexts": {},
            "onset_q": None, "duration_q": None, "tie_from": None,
        },
    }


def project(whole: dict, index: dict, package: dict, registry: dict) -> tuple[dict, dict]:
    catalog = identity_boundary(package, registry)
    if (whole.get("schema") != "fathom-level072-whole-detached-candidate-v1"
            or whole.get("wbs_id") != "2.3.1.2.1" or whole.get("level") != 72
            or whole.get("record_count") != 73
            or whole.get("complete_written_workout_contacts") != 640
            or whole.get("module_printed_contact_counts") != COUNTS):
        raise ValueError("whole Level72 scope/count drift")
    for key in ("admitted", "imported", "runtime_eligible", "runtime_admitted", "curriculum_signoff"):
        if whole.get(key) is not False:
            raise ValueError(f"source admission drift: {key}")
    for key in ("canonical_item_id", "canonical_variant_id", "fixed_bpm", "note_per_click", "onset_q", "duration_q", "performed_result"):
        if whole.get(key) is not None:
            raise ValueError(f"source allocation/timing drift: {key}")
    if (index.get("indexed_record_count") != 73
            or index.get("indexed_printed_contacts") != 640
            or index.get("indexed_module_count") != 11
            or index.get("whole_workbook_complete") is not False
            or index.get("runtime_eligible") is not False):
        raise ValueError("whole coverage boundary drift")
    if [r["qualified_source_key"] for r in whole["records"]] != [e["qualified_source_key"] for e in index["source_order_entries"]]:
        raise ValueError("source order differs from coverage index")
    records = []
    by_module = {m: [] for m in COUNTS}
    seen = set()
    for record, source_entry in zip(whole["records"], index["source_order_entries"]):
        key = record["qualified_source_key"]
        if key in seen or key != record["module"] + "/" + record["source_local_key"]:
            raise ValueError("duplicate or unqualified source record")
        seen.add(key)
        if (record["contact_count"] != len(record["contacts"])
                or record["contact_count"] != source_entry["printed_contact_count"]
                or record["pdf_page"] != source_entry["source_pdf_page"]
                or record["txt_line_span"] != source_entry["source_txt_line_span"]):
            raise ValueError("record coverage drift")
        events = [event(c) for c in record["contacts"]]
        for ordinal, e in enumerate(events, 1):
            if (e["qualified_source_key"] != key or e["source_module"] != record["module"]
                    or e["source_local_ordinal"] != ordinal
                    or e["source_refs"]["pdf_page"] != record["pdf_page"]
                    or not record["txt_line_span"][0] <= e["source_refs"]["txt_note_line"] <= record["txt_line_span"][1]):
                raise ValueError("event source pointer drift")
        by_module[record["module"]].extend(events)
        records.append({
            "source_order": record["source_order"], "source_component": record["module"],
            "qualified_source_key": key, "source_local_key": record["source_local_key"],
            "source_pdf_page": record["pdf_page"], "source_txt_line_span": record["txt_line_span"],
            "identity_state": "unallocated", "source_record": record["structured_source_record"],
            "schema1_fields": {
                "id": None, "workbook_id": None, "module_id": None,
                "legacy_level": 72, "title": record["structured_source_record"].get("printed_heading", key),
                "kind": "mixed", "content_revision": None, "lineage": None,
                "runtime_eligible": False, "source_refs": None,
                "events": events, "variants": [{"id": None, "source_key": key,
                                                 "source_event_ordinals": list(range(1, len(events) + 1)),
                                                 "event_ids": None, "runtime_eligible": False}],
                "resource_requirements": [],
                "timing": {"status": "unresolved", "unit": "quarter", "fixed_bpm": None},
                "ambiguities": ["canonical identities and lineage unallocated",
                                "onset/duration, fixed BPM and performed result unresolved",
                                "printed guidance and source differences require Curriculum review"],
            },
        })
    if list(by_module) != list(COUNTS) or {m: len(v) for m, v in by_module.items()} != COUNTS:
        raise ValueError("module event parity drift")
    if len(records) != 73 or sum(len(v) for v in by_module.values()) != 640:
        raise ValueError("whole record/event parity drift")
    proposal = {
        "proposal_version": "level072-unallocated-schema1-fields.1", "wbs_id": "2.3.1.2.1",
        "classification": "Build-only, nonimportable schema1 field proposal",
        "legacy_level": 72, "canonical_ids_allocated": False,
        "schema1_importable": False, "whole_workbook_complete": False,
        "runtime_eligible": False, "admitted": False,
        "counts": {"provisional_components": 11, "source_records": 73,
                   "distinct_printed_contacts": 640, "by_module": COUNTS},
        "source": whole["source"], "source_catalog_level": catalog,
        "coverage_index_ref": whole["coverage_index_ref"],
        "source_map_boundary": whole["source_map_boundary"],
        "source_differences": whole["source_differences"],
        "pdf_only_practice_log": whole["pdf_only_practice_log"],
        "three_pass_capstone": whole["three_pass_capstone"],
        "source_count_interpretation": whole["source_count_interpretation"],
        "source_module_context": {m: whole["modules"][m]["structured_source_module"] for m in COUNTS},
        "records": records,
    }
    handoff = {
        "handoff_version": "level072-allocation-handoff.1", "wbs_id": "2.3.1.2.1",
        "catalog_workbook_id": catalog["workbook_id"],
        "existing_level072_records": 0, "existing_level072_workbook_entities": 0,
        "source_records": 73, "distinct_printed_contacts": 640,
        "proposed_component_partition": list(COUNTS),
        "canonical_ids_allocated": False, "admitted": False,
        "required_decisions": [
            "Review four preserved TXT/PDF differences, including K card grids and practice wording.",
            "Allocate stable workbook/module/item/event/variant identities and revision lineage.",
            "Resolve quarter-note timing, BPM, picking and performance semantics before native import.",
            "Review musical correctness, three-pass capstone and mastery under Curriculum authority.",
        ],
    }
    return proposal, handoff


def products(root: Path) -> dict[str, object]:
    whole, index, package, registry, _freeze = read_inputs(root)
    proposal, handoff = project(whole, index, package, registry)
    manifest = {"manifest_version": "level072-input-pins.1", "inputs": [
        {"path": rel, "bytes": (root / rel).stat().st_size, "sha256": sha}
        for rel, sha in INPUTS.items()]}
    summary = {"summary_version": "level072-schema1-unallocated-summary.1",
               "proposal_sha256": digest(encoded(proposal)),
               "handoff_sha256": digest(encoded(handoff)),
               "source_records": 73, "distinct_printed_contacts": 640,
               "native_run": False, "runtime_eligible": False, "admitted": False}
    return {"field-proposal.json": proposal, "allocation-handoff.json": handoff,
            "input-manifest.json": manifest, "summary.json": summary}


def run(mode: str, root: Path) -> None:
    git_root = Path(subprocess.run(["git", "rev-parse", "--show-toplevel"],
                                   cwd=root, capture_output=True, text=True,
                                   check=True).stdout.strip()).resolve(strict=True)
    if root != git_root:
        raise ValueError("root must equal Git top level")
    built = products(root)
    out = root
    for part in OUT_REL.parts:
        out /= part
        if out.is_symlink():
            raise ValueError("output symlink path")
    if mode == "build":
        if out.exists():
            raise ValueError("output already exists")
        out.mkdir(parents=True)
        for name, value in built.items():
            with (out / name).open("xb") as f:
                f.write(encoded(value))
    else:
        contents = {p.name for p in out.iterdir()}
        if contents not in (set(built), set(built) | {"focused-tests.log"}):
            raise ValueError("output file set drift")
        if "focused-tests.log" in contents and (out / "focused-tests.log").is_symlink():
            raise ValueError("output test log symlink")
        for name, value in built.items():
            path = out / name
            if path.is_symlink() or path.read_bytes() != encoded(value):
                raise ValueError(f"output drift: {name}")
    print(f"LEVEL72 {mode.upper()} PASS records=73 contacts=640 admitted=false")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("mode", choices=("build", "verify"))
    ap.add_argument("--root", type=Path, default=ROOT)
    args = ap.parse_args()
    run(args.mode, args.root.resolve(strict=True))


if __name__ == "__main__":
    main()
