#!/usr/bin/env python3
"""Project sealed whole-Level100 composition source into unallocated schema1 fields."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = Path("Build/parallel-07/2.3.1.3.1-level100-schema1-unallocated-r01")
STEM = "Guitar_Exercises_Section_XV_Level_100_Motif_Generation_Harmonic_Constraints_Bass_First_Melody_First_Writing_and_Eight_Bar_Composition"
TXT = f"Notes/music/guitar project/TXT version/{STEM}.txt"
PDF = f"Notes/music/guitar project/PDF version/{STEM}.pdf"
WHOLE = "Build/parallel-07/2.3.1.3.1-level100-whole-r01/level100_whole_candidate.json"
MAP = "Results/parallel-01/exercises/inventory/20260922T180500Z-2.3-curriculum-v1-source-inventory-evidence/curriculum-source-map.json"
PACKAGE = "Content/controls/curriculum-v1/package.json"
REGISTRY = "Content/controls/curriculum-v1/identity-registry.json"
GENERATION = "Content/controls/curriculum-v1/generation.json"
INPUTS = {
    WHOLE: "e31d27961f08fe47bc68f6397f458313cd567499823d889190ea642bc1e4ebb2",
    TXT: "d9d156ed64317d7567dcb57bbdaa630afb3861da43a70a77f25fbf8613b867d5",
    PDF: "4d4efa497b1fe782a89cbb22e935ea5cdf9d3ec6b7c94c609b5a36b631fb6a31",
    MAP: "bad5581a04f43ba8baf14db430449e1ccff5cf88f0f7e42198328073b27053d6",
    PACKAGE: "766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255",
    REGISTRY: "5d265859e1e8a5a530a0e53d88b019a1c920f3bba6cccb4ef0fef2f7640007e5",
    GENERATION: "fc6cec9f9d67eb82c97c5f4c3fb95d285178fb7fce7bd147d9ae0296d21b4c1c",
}
DECLARED = {"A": 144, "B": 144, "C": 128, "D": 128, "E": 128,
            "F": 112, "G": 160, "H": 192, "I": 320, "J": 64}
TASKS = {"A": 26, "B": 14, "C": 15, "D": 14, "E": 15,
         "F": 15, "G": 9, "H": 28, "I": 5, "J": 8}
EXPLICIT = {"A": 43, "B": 0, "C": 0, "D": 0, "E": 16,
            "F": 0, "G": 0, "H": 0, "I": 0, "J": 0}
UNRESOLVED = [
    "Canonical workbook/module/item/task/event/variant IDs, revision and lineage are unallocated.",
    "1,520 declared workload events are not 1,520 pre-authored pitches or contacts; most material is learner-composed.",
    "59 source-supported seeds/contacts/routes and 32 blank portfolio bars are distinct from authored compositions.",
    "Key, authored pitch/chord/bass/rhythm, meter, string/fret, onset/duration, lead sheet, take, score and mastery remain unresolved.",
    "Page-10 and page-14 headings say four while their tables each print six versions; retain all six.",
]


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def encoded(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def read_inputs(root: Path) -> dict:
    raw = {}
    for rel, expected in INPUTS.items():
        data = (root / rel).read_bytes()
        if sha(data) != expected:
            raise ValueError(f"input drift: {rel}")
        raw[rel] = data
    parsed = {rel: json.loads(raw[rel]) for rel in (WHOLE, MAP, PACKAGE, REGISTRY, GENERATION)}
    parsed[TXT] = raw[TXT].decode("utf-8").splitlines()
    return parsed


def identity_boundary(data: dict) -> dict:
    foundation, registry, generation = data[PACKAGE], data[REGISTRY], data[GENERATION]
    workbook = "fg:workbook:000100"
    if len(foundation["records"]) != 659 or generation["records"] != 659:
        raise ValueError("current659 foundation drift")
    if any(r.get("legacy_level") == 100 or r.get("workbook_id") == workbook for r in foundation["records"]):
        raise ValueError("Level100 canonical record already exists")
    if any(e.get("id") == workbook for e in registry["entities"]):
        raise ValueError("Level100 workbook registry entity already exists")
    entry = next((x for x in foundation["workbook_catalog"]["entries"] if x.get("workbook_id") == workbook), None)
    if (not entry or entry.get("catalog_role") != "read_only_source_preservation"
        or entry.get("conversion_status") != "not_converted" or entry.get("review") != "Pending"
        or entry.get("representative_item_id") is not None
        or any(entry.get(k) is not False for k in ("runtime_eligible", "runtime_admitted", "imported", "admitted", "whole_workbook_complete"))
        or entry.get("playable_projection", {}).get("status") != "explicitly_empty_unresolved"):
        raise ValueError("Level100 source-only catalog boundary drift")
    return entry


def validate_source(candidate: dict, source_map: dict, lines: list[str]) -> None:
    if (candidate.get("schema") != "fathom.detached_curriculum_source_candidate.v1" or candidate.get("level") != 100
        or candidate.get("wbs_owner") != "2.3.1.3.1" or candidate.get("status") != "candidate_only"
        or candidate.get("admission_claim") is not False):
        raise ValueError("Level100 candidate scope/authority drift")
    for label, rel in (("txt", TXT), ("pdf", PDF)):
        pin = candidate["source_pins"][label]
        if pin["path"] != rel or pin["sha256"] != INPUTS[rel]:
            raise ValueError("Level100 original source identity drift")
    archived = candidate["source_archive"]["txt_lines"]
    if len(lines) != 48 or archived != [{"line": i, "text": line} for i, line in enumerate(lines, 1)]:
        raise ValueError("Level100 original TXT/archive drift")
    pages = candidate["source_archive"]["pdf_pages"]
    if len(pages) != 21 or any(page.get("page") != i for i, page in enumerate(pages, 1)):
        raise ValueError("Level100 PDF page archive drift")
    if (len(candidate["pdf_tables"]) != 17 or candidate["module_workload_declared"] != DECLARED
        or candidate["declared_workload_total"] != 1520 or len(candidate["tasks"]) != 149
        or len(candidate["source_supported_seed_or_contact_events"]) != 59
        or len(candidate["portfolio_bar_allocations"]) != 32):
        raise ValueError("Level100 table/task/event/allocation/workload drift")
    if (len(candidate["h_studies"]) != 4 or any(len(study["passes"]) != 6 for study in candidate["h_studies"])):
        raise ValueError("H study/pass ladder drift")
    tables = candidate["pdf_tables"]
    if (len(tables["harmonizations"]["rows"]) != 6 or len(tables["rhythmic_identities"]["rows"]) != 6
        or "four" not in pages[9]["text"].lower() or "four" not in pages[13]["text"].lower()):
        raise ValueError("four-versus-six heading/table conflict drift")
    tensions = candidate["source_tensions"]
    if (len(tensions) != 4 or tensions[0].get("pdf_page") != 10 or tensions[1].get("pdf_page") != 14
        or tensions[0].get("resolution") != "convert all six printed versions"
        or tensions[1].get("resolution") != "convert all six printed versions"
        or tensions[-1].get("resolution") != "retain declared workload apart from source-supported seeds and blank portfolio allocations"):
        raise ValueError("Level100 source tension ledger drift")
    if candidate["unresolved_performance_fields"] != ["key", "authored_pitch", "authored_chord",
        "authored_bass", "authored_rhythm", "meter", "onset_q", "duration_q", "string", "fret",
        "lead_sheet", "recorded_take", "score", "canonical_task_id", "canonical_event_id"]:
        raise ValueError("Level100 unresolved performance fields drift")
    row = next((r for r in source_map["rows"] if r.get("level") == 100), None)
    if (row is None or row != candidate["source_map"] or row.get("txt_sha256") != INPUTS[TXT]
        or row.get("pdf_sha256") != INPUTS[PDF] or row.get("conversion_status") != "not_converted"
        or row.get("representative_item_id") is not None or any(row.get(k) is not False for k in
            ("stable_ids_assigned", "runtime_eligible", "imported", "admitted"))):
        raise ValueError("Level100 frozen source-map boundary drift")


def task_field(task: dict, module: str, global_ordinal: int, lines: list[str]) -> dict:
    if (set(task) != {"local_key", "module", "kind", "source", "fields", "canonical_task_id",
                      "authored_response", "observed_score"} or task["module"] != module
        or any(task[k] is not None for k in ("canonical_task_id", "authored_response", "observed_score"))):
        raise ValueError("source task identity/authorship drift")
    page, line = task["source"]["pdf_page"], task["source"]["txt_line"]
    if not isinstance(page, int) or not 1 <= page <= 21:
        raise ValueError("task PDF page ref drift")
    if line is not None and (not isinstance(line, int) or not 1 <= line <= len(lines) or not lines[line - 1]):
        raise ValueError("task TXT line ref drift")
    return {"source_global_ordinal": global_ordinal, "source_task": task,
            "schema1_fields": {"id": None, "kind": "task", "runtime_eligible": False,
                               "source_refs": None, "authored_response": None, "observed_score": None}}


def event_field(event: dict, module: str) -> dict:
    expected = {"local_key", "module", "kind", "source", "slot", "bar", "degree", "pitch",
                "pitch_class", "contact_mark", "fields", "octave", "string", "fret", "onset_q",
                "duration_q", "canonical_event_id", "performed_result"}
    if set(event) != expected or event["module"] != module or event["kind"] not in ("seed_degree", "rhythm_contact", "printed_bass_route"):
        raise ValueError("source-supported event field/module drift")
    if any(event[k] is not None for k in ("octave", "string", "fret", "onset_q", "duration_q",
                                              "canonical_event_id", "performed_result")):
        raise ValueError("source-supported event invented performance")
    if (not isinstance(event["slot"], int) or event["slot"] < 1
        or not 1 <= event["source"]["pdf_page"] <= 21 or event["source"]["row"] < 1):
        raise ValueError("source-supported event PDF row/slot drift")
    if event["kind"] == "seed_degree" and (event["degree"] is None or event["pitch"] is not None):
        raise ValueError("seed-degree pitch/authorship drift")
    if event["kind"] == "printed_bass_route" and not isinstance(event["pitch"], str):
        raise ValueError("printed bass route pitch lost")
    return {"source_event": event,
            "source_tone": {"printed_degree": event["degree"], "printed_pitch": event["pitch"],
                            "theory_pitch_class": event["pitch_class"],
                            "printed_contact_mark": event["contact_mark"], "sounding_midi": None},
            "schema1_fields": {"event_id": None, "kind": None, "contact": None,
                               "pick": None, "pitch_binding": None, "onset_q": None, "duration_q": None}}


def portfolio_field(allocation: dict, ordinal: int) -> dict:
    expected = {"bar", "piece", "starting_method", "authored_chord", "authored_melody",
                "authored_bass", "authored_rhythm", "source"}
    if set(allocation) != expected or allocation["bar"] != ordinal:
        raise ValueError("portfolio bar identity/order drift")
    if any(allocation[k] is not None for k in ("authored_chord", "authored_melody", "authored_bass", "authored_rhythm")):
        raise ValueError("portfolio bar invented learner authorship")
    if allocation["source"]["pdf_page"] != 20 or allocation["source"]["section_row"] not in range(1, 5):
        raise ValueError("portfolio bar PDF source ref drift")
    return {"source_portfolio_bar": allocation,
            "schema1_fields": {"id": None, "kind": "composition_slot", "runtime_eligible": False,
                               "authored_chord": None, "authored_melody": None,
                               "authored_bass": None, "authored_rhythm": None}}


def project(data: dict) -> tuple[dict, dict]:
    candidate, lines = data[WHOLE], data[TXT]
    entry = identity_boundary(data)
    validate_source(candidate, data[MAP], lines)
    task_ordinals = {task["local_key"]: i for i, task in enumerate(candidate["tasks"], 1)}
    event_ordinals = {event["local_key"]: i for i, event in enumerate(candidate["source_supported_seed_or_contact_events"], 1)}
    if len(task_ordinals) != 149 or len(event_ordinals) != 59:
        raise ValueError("source local-key duplication")
    portfolio = [portfolio_field(x, i) for i, x in enumerate(candidate["portfolio_bar_allocations"], 1)]
    if (Counter(x["source_portfolio_bar"]["piece"] for x in portfolio)
        != {"Piece A": 8, "Piece B": 8, "Piece C": 8, "Piece D": 8}
        or {x["source_portfolio_bar"]["starting_method"] for x in portfolio}
        != {"motif-first", "melody-first", "bass-first", "rhythm-first"}):
        raise ValueError("four-original portfolio allocation drift")
    records = []
    seen_tasks, seen_events = [], []
    for module in DECLARED:
        tasks = [t for t in candidate["tasks"] if t["module"] == module]
        events = [e for e in candidate["source_supported_seed_or_contact_events"] if e["module"] == module]
        if len(tasks) != TASKS[module] or len(events) != EXPLICIT[module]:
            raise ValueError("module task/explicit-event partition drift")
        source_tasks = [task_field(t, module, task_ordinals[t["local_key"]], lines) for t in tasks]
        source_events = [event_field(e, module) for e in events]
        seen_tasks.extend(tasks)
        seen_events.extend(events)
        records.append({"source_component": module, "identity_state": "unallocated",
                        "source_declared_workload": DECLARED[module], "source_tasks": source_tasks,
                        "source_portfolio_bars": portfolio if module == "I" else [],
                        "schema1_fields": {"id": None, "workbook_id": None, "module_id": None,
                                           "legacy_level": 100, "title": f"Level 100 component {module}",
                                           "kind": "mixed", "content_revision": None, "lineage": None,
                                           "runtime_eligible": False, "source_refs": None,
                                           "events": source_events,
                                           "variants": [{"id": None, "source_component": module,
                                                         "source_event_ordinals": [event_ordinals[e["local_key"]] for e in events],
                                                         "event_ids": None, "runtime_eligible": False}],
                                           "resource_requirements": [],
                                           "timing": {"status": "unresolved", "unit": "quarter", "fixed_bpm": None},
                                           "ambiguities": UNRESOLVED}})
    if (Counter(t["local_key"] for t in seen_tasks) != Counter(t["local_key"] for t in candidate["tasks"])
        or Counter(e["local_key"] for e in seen_events) != Counter(e["local_key"] for e in candidate["source_supported_seed_or_contact_events"])):
        raise ValueError("source task/event union lost or duplicated")
    proposal = {"proposal_version": "level100-unallocated-schema1-fields.1", "wbs_id": "2.3.1.3.1",
                "classification": "Build-only, nonimportable schema1 field proposal", "legacy_level": 100,
                "canonical_ids_allocated": False, "schema1_importable": False,
                "whole_workbook_complete": False, "runtime_eligible": False, "admitted": False,
                "counts": {"components": 10, "core_tables": 17, "h_pass_ladders": 4,
                           "authored_tasks": 149, "source_supported_seed_contact_events": 59,
                           "blank_portfolio_bar_allocations": 32, "source_declared_workload": 1520,
                           "declared_by_module": DECLARED, "tasks_by_module": TASKS,
                           "explicit_events_by_module": EXPLICIT},
                "source_pins": candidate["source_pins"], "source_map": candidate["source_map"],
                "source_archive": candidate["source_archive"], "pdf_tables": candidate["pdf_tables"],
                "source_task_order": [t["local_key"] for t in candidate["tasks"]],
                "source_event_order": [e["local_key"] for e in candidate["source_supported_seed_or_contact_events"]],
                "h_studies": candidate["h_studies"], "source_tensions": candidate["source_tensions"],
                "unresolved_performance_fields": candidate["unresolved_performance_fields"],
                "records": records}
    handoff = {"handoff_version": "level100-allocation-handoff.1", "wbs_id": "2.3.1.3.1",
               "catalog_workbook_id": entry["workbook_id"], "catalog_role": entry["catalog_role"],
               "existing_representative_item_id": None, "existing_level100_records": 0,
               "existing_level100_workbook_entities": 0, "proposed_component_partition": list(DECLARED),
               "authored_tasks": 149, "source_supported_seed_contact_events": 59,
               "blank_portfolio_bar_allocations": 32, "source_declared_workload": 1520,
               "canonical_ids_allocated": False, "admitted": False,
               "required_decisions": ["Preserve both four-versus-six heading conflicts while using the six printed rows in each table.",
                                      "Keep 1,520 workload declaration separate from 59 seeds/contacts/routes and 32 blank portfolio bars.",
                                      "Have the learner author composition pitch/chord/bass/rhythm, then define lead sheet, recording, timing and scoring before runtime mapping.",
                                      "Allocate stable identities and lineage only after registry review and Curriculum acceptance."]}
    return proposal, handoff


def products(root: Path) -> dict[str, object]:
    proposal, handoff = project(read_inputs(root))
    manifest = {"manifest_version": "level100-input-pins.1", "inputs": [
        {"path": rel, "bytes": (root / rel).stat().st_size, "sha256": digest}
        for rel, digest in INPUTS.items()]}
    summary = {"summary_version": "level100-schema1-unallocated-summary.1",
               "proposal_sha256": sha(encoded(proposal)), "handoff_sha256": sha(encoded(handoff)),
               "authored_tasks": 149, "source_supported_seed_contact_events": 59,
               "blank_portfolio_bar_allocations": 32, "source_declared_workload": 1520,
               "native_run": False, "runtime_eligible": False, "admitted": False}
    return {"field-proposal.json": proposal, "allocation-handoff.json": handoff,
            "input-manifest.json": manifest, "summary.json": summary}


def output_dir(root: Path) -> Path:
    part = root
    for component in OUT.parts:
        part /= component
        if part.is_symlink():
            raise ValueError("output symlink path")
    return part


def run(mode: str, root: Path) -> None:
    built = products(root)
    out = output_dir(root)
    if mode == "build":
        out.mkdir(parents=True, exist_ok=True)
        for name, value in built.items():
            (out / name).write_bytes(encoded(value))
    else:
        for name, value in built.items():
            path = out / name
            if path.is_symlink() or path.read_bytes() != encoded(value):
                raise ValueError(f"output drift: {name}")
    print(f"LEVEL100 {mode.upper()} PASS tasks=149 explicit=59 portfolio=32 declared=1520 admitted=false")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("build", "verify"))
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    run(args.mode, args.root.resolve())
