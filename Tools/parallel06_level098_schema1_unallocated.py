#!/usr/bin/env python3
"""Project sealed Level98 semantic source into detached unallocated schema1 fields."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from curriculum_level098_whole_semantic_candidate import build


ROOT = Path(__file__).resolve().parents[1]
OUT_REL = Path("Build/parallel-06/level098-schema1-unallocated-r01")
INPUTS = {
    "Build/parallel-09/2.3.1.3.1-level098-whole-semantic-r01/level098-whole-semantic-candidate.json": "b3df6fa41b94d007a40de2a3c512175f27863887f4858b4e9043c24342abcab2",
    "Tools/curriculum_level098_whole_semantic_candidate.py": "bb305a4d4b40f270ef40489d1fdbf56b0b25437e589623d759c01b82fb47522a",
    "Content/controls/curriculum-v1/package.json": "766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255",
    "Content/controls/curriculum-v1/identity-registry.json": "5d265859e1e8a5a530a0e53d88b019a1c920f3bba6cccb4ef0fef2f7640007e5",
    "Results/primary/20260912T100538Z-2.1.1.2.1-r02-evidence/schema-freeze.json": "0659fa962a5c933a2bcf3045772b6fe5b05b4deefb3511f5dcb68af51088de95",
}
COUNTS = dict(zip("ABCDEFGHIJ", (128, 128, 144, 128, 128, 112, 144, 216, 336, 64)))
PAGES = {"A": [3, 4], "B": [5, 6], "C": [7, 8], "D": [9, 10],
         "E": [11, 12], "F": [13, 14], "G": [15], "H": [16, 17, 18],
         "I": [19], "J": [20]}
UNRESOLVED_SLOT_FIELDS = ("pitch", "string", "fret", "onset", "duration", "performed_result")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def encoded(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False,
                       separators=(",", ":")) + "\n").encode()


def read_inputs(root: Path) -> tuple[dict, dict, dict]:
    raw = {}
    for rel, expected in INPUTS.items():
        path = root / rel
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"missing or symlink input: {rel}")
        data = path.read_bytes()
        if digest(data) != expected:
            raise ValueError(f"input drift: {rel}")
        raw[rel] = data
    candidate = json.loads(raw[next(iter(INPUTS))])
    if candidate != build(root):
        raise ValueError("sealed candidate differs from original TXT/PDF replay")
    package = json.loads(raw[list(INPUTS)[2]])
    registry = json.loads(raw[list(INPUTS)[3]])
    freeze = json.loads(raw[list(INPUTS)[4]])
    if freeze.get("decision") != "Technical schema1 FROZEN" or freeze.get("schema_version") != "1.0.0-curriculum-candidate":
        raise ValueError("schema freeze drift")
    return candidate, package, registry


def identity_boundary(package: dict, registry: dict) -> dict:
    wid = "fg:workbook:000098"
    if any(r.get("legacy_level") == 98 or r.get("workbook_id") == wid
           for r in package["records"]):
        raise ValueError("unexpected canonical Level98 record")
    if any(e.get("id") == wid for e in registry["entities"]):
        raise ValueError("unexpected Level98 registry entity")
    entries = [e for e in package["workbook_catalog"]["entries"]
               if e.get("workbook_id") == wid]
    if len(entries) != 1:
        raise ValueError("Level98 catalog identity drift")
    entry = entries[0]
    if (entry.get("conversion_status") != "not_converted"
            or entry.get("whole_workbook_complete") is not False
            or entry.get("admitted") is not False
            or entry.get("runtime_eligible") is not False
            or entry.get("representative_item_id") is not None):
        raise ValueError("Level98 source-only catalog drift")
    return entry


def unresolved_event(slot: dict) -> dict:
    if set(slot) != {"slot", *UNRESOLVED_SLOT_FIELDS}:
        raise ValueError("source slot shape drift")
    if any(slot[k] is not None for k in UNRESOLVED_SLOT_FIELDS):
        raise ValueError("source slot unexpectedly resolved")
    return {"source_slot": slot, "source_row": None, "source_bar": None,
            "source_pass": None, "source_version": None, "performed_result": None,
            "schema1_fields": {
                "event_id": None, "kind": None, "attack": None,
                "spelling": None, "midi": None, "string": None, "fret": None,
                "finger": None, "degree_contexts": {}, "onset_q": None,
                "duration_q": None, "tie_from": None,
            }}


def project(candidate: dict, package: dict, registry: dict) -> tuple[dict, dict]:
    catalog = identity_boundary(package, registry)
    if (candidate.get("schema_status") != "detached_whole_source_semantic_candidate_not_curriculum_record"
            or candidate.get("candidate_status") != "pending_source_reconciliation"
            or candidate.get("workbook_id") != "fg:workbook:000098"
            or candidate.get("legacy_level") != 98
            or candidate.get("wbs_owner") != "2.3.1.3.1"
            or candidate.get("written_event_total") != 1528):
        raise ValueError("whole Level98 scope/count drift")
    for key in ("admitted", "imported", "runtime_eligible", "whole_workbook_complete",
                "stable_ids_assigned_by_this_candidate"):
        if candidate.get(key) is not False:
            raise ValueError(f"source admission/identity drift: {key}")
    if candidate.get("curriculum_review") != "Pending":
        raise ValueError("source review drift")
    recon = candidate["source_reconciliation"]
    if not all(recon.values()) or set(recon) != {
            "module_totals_match_txt_and_pdf", "module_A_triples_match_P06_narrow_candidate",
            "no_destination_chords_or_student_solutions_computed",
            "capstone_three_versions_are_assignments_not_performed",
            "module_counts_not_allocated_to_rows_bars_passes_or_versions",
            "no_representative_id"}:
        raise ValueError("source reconciliation drift")
    if candidate["frozen_catalog"]["representative_item_id"] is not None:
        raise ValueError("source representative identity drift")
    pages = candidate["pdf_pages"]
    if [p["page"] for p in pages] != list(range(1, 21)):
        raise ValueError("PDF page order drift")
    by_page = {p["page"]: p for p in pages}
    capstone = by_page[19]["semantic"]
    if (capstone.get("kind") != "forty_eight_bar_capstone"
            or len(capstone["section_rows"]) != 6
            or capstone["required_versions"] != ["solo/acoustic", "electric trio", "full-band support"]
            or capstone["complete_arrangement_notes"] is not None
            or capstone["performed_versions"] is not None):
        raise ValueError("capstone assignment/performance drift")
    audit = by_page[20]["semantic"]
    if audit.get("kind") != "adaptation_audit" or len(audit["rubric"]) != 8 or audit["performed_score"] is not None:
        raise ValueError("source audit/performance drift")
    modules = candidate["modules"]
    if [m["module"] for m in modules] != list(COUNTS):
        raise ValueError("module order drift")
    records = []
    for module in modules:
        letter = module["module"]
        if (module["written_event_count"] != COUNTS[letter]
                or module["pdf_pages"] != PAGES[letter]
                or module["slot_allocation"] != "module_count_only_unresolved_per_row_bar_and_version"
                or module["txt_line"] != 13 + list(COUNTS).index(letter)):
            raise ValueError("module scope/allocation drift")
        source_slots = module["written_event_slots"]
        if len(source_slots) != COUNTS[letter] or [s["slot"] for s in source_slots] != list(range(1, COUNTS[letter] + 1)):
            raise ValueError("module slot count/order drift")
        events = [unresolved_event(s) for s in source_slots]
        source_pages = [by_page[n] for n in PAGES[letter]]
        records.append({
            "source_component": letter, "identity_state": "unallocated",
            "source_module": {k: v for k, v in module.items() if k != "written_event_slots"},
            "source_task_pages": source_pages,
            "schema1_fields": {
                "id": None, "workbook_id": None, "module_id": None,
                "legacy_level": 98, "title": module["title"], "kind": "mixed",
                "content_revision": None, "lineage": None, "runtime_eligible": False,
                "source_refs": None, "events": events, "variants": [],
                "unassigned_source_event_ordinals": list(range(1, len(events) + 1)),
                "resource_requirements": [],
                "timing": {"status": "unresolved", "unit": "quarter", "fixed_bpm": None},
                "ambiguities": ["canonical identities and lineage unallocated",
                                "all written slots are module counts, not allocated to rows, bars, passes or versions",
                                "note-level pitch/TAB, onset/duration and performed outcome unresolved"],
            },
        })
    if sum(len(r["schema1_fields"]["events"]) for r in records) != 1528:
        raise ValueError("whole slot parity drift")
    proposal = {
        "proposal_version": "level098-unallocated-schema1-fields.1", "wbs_id": "2.3.1.3.1",
        "classification": "Build-only, nonimportable schema1 field proposal",
        "legacy_level": 98, "canonical_ids_allocated": False,
        "schema1_importable": False, "whole_workbook_complete": False,
        "runtime_eligible": False, "admitted": False,
        "counts": {"provisional_components": 10, "source_described_written_event_slots": 1528,
                   "by_module": COUNTS, "slots_allocated_to_rows_bars_passes_versions": 0},
        "source_pair": candidate["source_pair"], "source_catalog_level": catalog,
        "source_catalog_ref": candidate["frozen_catalog"],
        "source_predecessor": candidate["predecessor"],
        "source_txt": candidate["txt"], "source_pdf_pages": pages,
        "source_reconciliation": recon, "visual_review": candidate["visual_review"],
        "records": records,
    }
    handoff = {
        "handoff_version": "level098-allocation-handoff.1", "wbs_id": "2.3.1.3.1",
        "catalog_workbook_id": catalog["workbook_id"],
        "existing_level098_records": 0, "existing_level098_workbook_entities": 0,
        "source_described_written_event_slots": 1528,
        "module_count_partition": COUNTS, "slots_allocated_to_rows_bars_passes_versions": 0,
        "canonical_ids_allocated": False, "admitted": False,
        "required_decisions": [
            "Allocate the 1,528 module counts to source tasks, rows, bars, passes and versions only after source review.",
            "Review the page-19 baseline and three required version assignments; no completed arrangements are present.",
            "Specify note-level pitch/TAB, timing, performance and audit-score semantics before native import.",
            "Allocate stable identities/revision lineage and complete Curriculum musical review.",
        ],
    }
    return proposal, handoff


def products(root: Path) -> dict[str, object]:
    candidate, package, registry = read_inputs(root)
    proposal, handoff = project(candidate, package, registry)
    manifest = {"manifest_version": "level098-input-pins.1", "inputs": [
        {"path": rel, "bytes": (root / rel).stat().st_size, "sha256": sha}
        for rel, sha in INPUTS.items()]}
    summary = {"summary_version": "level098-schema1-unallocated-summary.1",
               "proposal_sha256": digest(encoded(proposal)),
               "handoff_sha256": digest(encoded(handoff)),
               "source_described_written_event_slots": 1528,
               "slots_allocated_to_rows_bars_passes_versions": 0,
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
    print("LEVEL98 " + mode.upper() + " PASS slots=1528 module-only admitted=false")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("mode", choices=("build", "verify"))
    ap.add_argument("--root", type=Path, default=ROOT)
    args = ap.parse_args()
    run(args.mode, args.root.resolve(strict=True))


if __name__ == "__main__":
    main()
