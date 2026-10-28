#!/usr/bin/env python3
"""Build source-bound, unallocated whole-Level53 schema1 field proposals."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from curriculum_level053_whole_triad_sets_candidate import COUNTS, build_candidate


ROOT = Path(__file__).resolve().parents[1]
OUT_REL = Path("Build/parallel-10/level053-schema1-unallocated-r01")
INPUTS = {
    "Tools/curriculum_level053_whole_triad_sets_candidate.py": "1909fdf2efb8f6763183ed1293d0f82f36499cdcbfec7c237a1848db0f77fa0c",
    "Results/parallel-05/exercises/conversion/20260923T160200Z-2.3.1.2.1-level053-whole-triad-sets-r01-results.md": "1e8881d1fe50e23335921d21265696d63cb267b6b70ec452c4012d823f994da1",
    "Build/parallel-05/2.3.1.2.1-level053-whole-r01/candidate-c.json": "f6331233431a8897cb97466231fa5b5678955ad122931cdcf2735cf40832ca4c",
    "Content/controls/curriculum-v1/package.json": "766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255",
    "Content/controls/curriculum-v1/identity-registry.json": "5d265859e1e8a5a530a0e53d88b019a1c920f3bba6cccb4ef0fef2f7640007e5",
    "Content/controls/curriculum-v1/generation.json": "fc6cec9f9d67eb82c97c5f4c3fb95d285178fb7fce7bd147d9ae0296d21b4c1c",
    "Notes/music/guitar project/TXT version/Guitar_Exercises_Section_VI_Level_53_Major_and_Minor_Triads_Across_Four_Adjacent_Three_String_Sets.txt": "eeedc261db89d3421fafc116e7352bbf8a3e3f6b7eddfd822ed6e4c731e0538e",
    "Notes/music/guitar project/PDF version/Guitar_Exercises_Section_VI_Level_53_Major_and_Minor_Triads_Across_Four_Adjacent_Three_String_Sets.pdf": "5e016f98623dc4362b2e3fc9b2d1cf1fb6c8692d6312d5b30a65234d47fa20ae",
    "Results/parallel-01/exercises/inventory/20260922T180500Z-2.3-curriculum-v1-source-inventory-evidence/curriculum-source-map.json": "bad5581a04f43ba8baf14db430449e1ccff5cf88f0f7e42198328073b27053d6",
}
SOURCE_ATTACK_KEYS = {"chord", "degree", "fret", "kind", "module", "ordinal", "pdf_page",
                      "performed_duration", "performed_onset", "performed_pick", "performed_quality",
                      "printed_symbol", "string", "txt_line", "unit"}
KIND_COUNTS = {"individual arpeggio pick": 600, "blocked triad": 542,
               "individual melodic pick": 64, "individual voice pick": 38, "muted stroke": 4}
UNRESOLVED = ["canonical workbook/module/item/event/variant IDs and lineage",
              "performed triad member pitches, picking direction and note MIDI",
              "quarter-note onset/duration, fixed BPM and note-per-click",
              "Curriculum review of PDF additions, octave register and human mastery"]


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def encoded(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def pinned(root: Path, rel: str, sha: str) -> bytes:
    raw = (root / rel).read_bytes()
    if digest(raw) != sha:
        raise ValueError(f"input drift: {rel}")
    return raw


def read_inputs(root: Path) -> tuple[dict, dict, dict]:
    raw = {rel: pinned(root, rel, sha) for rel, sha in INPUTS.items()}
    candidate = json.loads(raw["Build/parallel-05/2.3.1.2.1-level053-whole-r01/candidate-c.json"])
    # P05 keeps some in-memory tuples; the sealed JSON stores their array form.
    if candidate != json.loads(json.dumps(build_candidate(root))):
        raise ValueError("P05 Level53 candidate differs from original TXT/PDF/map replay")
    foundation = json.loads(raw["Content/controls/curriculum-v1/package.json"])
    registry = json.loads(raw["Content/controls/curriculum-v1/identity-registry.json"])
    generation = json.loads(raw["Content/controls/curriculum-v1/generation.json"])
    if len(foundation["records"]) != 659 or generation["records"] != 659:
        raise ValueError("current659 foundation drift")
    return candidate, foundation, registry


def identity_boundary(foundation: dict, registry: dict) -> dict:
    workbook = "fg:workbook:000053"
    if any(r.get("legacy_level") == 53 or r.get("workbook_id") == workbook for r in foundation["records"]):
        raise ValueError("unexpected canonical Level53 record")
    if any(e.get("id") == workbook for e in registry["entities"]):
        raise ValueError("unexpected Level53 registry entity")
    entry = next((x for x in foundation["workbook_catalog"]["entries"] if x.get("workbook_id") == workbook), None)
    if (not entry or entry.get("representative_item_id") is not None or entry.get("whole_workbook_complete") is not False
        or entry.get("admitted") is not False or entry.get("conversion_status") != "not_converted"):
        raise ValueError("Level53 source-only catalog drift")
    return entry


def _attack_field(attack: dict, module: str, unit_number: int) -> dict:
    if set(attack) != SOURCE_ATTACK_KEYS or attack["module"] != module or attack["ordinal"] < 1:
        raise ValueError("source attack field/order drift")
    if any(attack[k] is not None for k in ("performed_onset", "performed_duration", "performed_pick", "performed_quality")):
        raise ValueError("source attack invented performance")
    kind = attack["kind"]
    if kind not in KIND_COUNTS:
        raise ValueError("unmapped source attack kind")
    if kind in ("blocked triad", "muted stroke"):
        if attack["string"] is not None or attack["fret"] is not None or attack["degree"] is not None:
            raise ValueError("blocked/muted attack acquired invented member")
        tone = None
    else:
        if attack["string"] not in ("E", "A", "D", "G", "B", "e"):
            raise ValueError("individual source string drift")
        if kind == "individual voice pick":
            if attack["fret"] is not None or attack["degree"] is not None:
                raise ValueError("voice-emphasis pick acquired unprinted fret/degree")
        elif not isinstance(attack["fret"], int) or attack["degree"] is None:
            raise ValueError("individual source contact drift")
        tone = {"string": attack["string"], "fret": attack["fret"],
                "printed_degree": attack["degree"], "sounding_midi": None}
    return {"source_module": module, "source_unit_number": unit_number,
            "source_local_ordinal": attack["ordinal"], "source_attack": attack,
            "source_tone": tone, "performed_member_pitches": None,
            "schema1_fields": {"event_id": None, "kind": "contact",
                               "contact": "muted" if kind == "muted stroke" else "pitched",
                               "pick": None, "pitch_binding": None, "onset_q": None, "duration_q": None}}


def project(candidate: dict, foundation: dict, registry: dict) -> tuple[dict, dict]:
    entry = identity_boundary(foundation, registry)
    if candidate.get("schema") != "fathom.detached-source-candidate.1" or candidate.get("level") != 53 or candidate.get("wbs_id") != "2.3.1.2.1" or candidate.get("module_count") != 8:
        raise ValueError("Level53 source candidate scope drift")
    if candidate.get("canonical_ids") is not None or any(candidate.get(k) is not False for k in ("runtime_eligible", "imported", "admitted")) or any(candidate.get(k) is not None for k in ("performed_bpm", "performed_quality", "performed_mastery")):
        raise ValueError("source candidate invented authority/performance")
    if candidate.get("printed_attack_count") != 1248 or candidate.get("silent_formation_count") != 168 or list(candidate["modules"]) != list(COUNTS):
        raise ValueError("1248/168 source workload drift")
    exceptions = candidate.get("source_exceptions")
    required = {"F7_F8_PDF_EXPLICIT_GRID", "PDF_ADDITIONAL_PRACTICE_PASSES",
                "PDF_SESSION_AND_COMPLETION_AUDIT", "D_C_MAJOR_SECOND_INVERSION_OCTAVE"}
    if not isinstance(exceptions, list) or {x.get("code") for x in exceptions} != required or any(x.get("status") != "Pending Curriculum review" for x in exceptions):
        raise ValueError("source-specific exceptions lost")
    modules = candidate["modules"]
    a = modules["A"]
    if (len(a["formulas"]) != 24 or len(a["formations"]) != 168 or a["silent_formation_count"] != 168
        or a["printed_attack_count"] != 0 or a["units"] != []
        or any(x.get("performed") is not None or x.get("kind") != "silent formation" for x in a["formations"])):
        raise ValueError("silent formation source drift")
    b_c2 = next((u for u in modules["B"]["units"] if u["set"] == "123" and u["chord"] == "C" and u["inversion"] == "2nd"), None)
    d_c2 = next((u for u in modules["D"]["units"] if u["set"] == "123" and u["inversion"] == "2nd"), None)
    if not b_c2 or b_c2["frets"] != [0, 1, 0] or not d_c2 or d_c2["major_frets"] != [12, 13, 12] or d_c2["minor_frets"] != [12, 13, 11]:
        raise ValueError("C major second-inversion source register drift")
    f = modules["F"]["units"]
    if len(f) != 8 or not all(x["pdf_only_detail"] is True for x in f[6:8]):
        raise ValueError("F7/F8 PDF-only grid detail lost")
    records = []
    unit_total = 0
    total = 0
    kinds = {k: 0 for k in KIND_COUNTS}
    for module, count in COUNTS.items():
        source_module = modules[module]
        events = []
        variants = []
        if module != "A":
            for unit_number, unit in enumerate(source_module["units"], 1):
                attacks = unit["attacks"]
                start = len(events) + 1
                for index, attack in enumerate(attacks, 1):
                    if attack["ordinal"] != index or attack["txt_line"] < source_module["txt_start_line"] or attack["txt_line"] > source_module["txt_end_line"] or not 1 <= attack["pdf_page"] <= 20:
                        raise ValueError("source attack ordinal/span drift")
                    kinds[attack["kind"]] += 1
                    events.append(_attack_field(attack, module, unit_number))
                meta = {key: value for key, value in unit.items() if key != "attacks"}
                variants.append({"id": None, "source_unit_number": unit_number, "source_unit": meta,
                                 "source_event_ordinals": list(range(start, len(events) + 1)),
                                 "event_ids": None, "runtime_eligible": False})
                unit_total += 1
        if len(events) != count or source_module["printed_attack_count"] != count:
            raise ValueError(f"{module} module attack count drift")
        total += len(events)
        records.append({"source_component": module, "source_txt_start_line": source_module["txt_start_line"],
                        "source_txt_end_line": source_module["txt_end_line"],
                        "source_full_lines": source_module["full_source_lines"],
                        "identity_state": "unallocated",
                        "silent_tasks": {"formulas": a["formulas"], "formations": a["formations"]} if module == "A" else None,
                        "schema1_fields": {"id": None, "workbook_id": None, "module_id": None,
                            "legacy_level": 53, "title": f"Level 53 component {module}", "kind": "mixed",
                            "content_revision": None, "lineage": None, "runtime_eligible": False,
                            "source_refs": None, "events": events, "variants": variants,
                            "resource_requirements": [], "timing": {"status": "unresolved", "unit": "quarter", "fixed_bpm": None},
                            "ambiguities": UNRESOLVED}})
    if total != 1248 or unit_total != 248 or kinds != KIND_COUNTS:
        raise ValueError("whole-Level53 projected attack total drift")
    proposal = {"proposal_version": "level053-unallocated-schema1-fields.1", "wbs_id": "2.3.1.2.1",
                "classification": "Build-only, nonimportable schema1 field proposal", "legacy_level": 53,
                "canonical_ids_allocated": False, "schema1_importable": False, "whole_workbook_complete": False,
                "runtime_eligible": False, "admitted": False,
                "counts": {"components": 8, "attack_units": unit_total, "silent_formulas": 24,
                           "silent_formations": 168, "printed_attacks": total, "attack_kinds": kinds},
                "source": {k: candidate["source"][k] for k in ("txt_path", "txt_sha256", "pdf_path", "pdf_sha256", "pdf_pages", "source_map_path", "source_map_sha256")},
                "source_exceptions": exceptions, "printed_guidance": candidate["printed_guidance"],
                "records": records}
    handoff = {"handoff_version": "level053-allocation-handoff.1", "wbs_id": "2.3.1.2.1",
               "catalog_workbook_id": entry["workbook_id"], "catalog_role": entry["catalog_role"],
               "existing_level053_records": 0, "existing_level053_workbook_entities": 0,
               "printed_attacks": 1248, "silent_formations_not_events": 168,
               "proposed_component_partition": list(COUNTS), "canonical_ids_allocated": False,
               "admitted": False,
               "required_decisions": ["Review all four source-specific notes and printed chord/pitch forms with Curriculum.",
                  "Allocate stable identities after current registry reservations are sealed.",
                  "Authorize exact performed pick, voicing and timing before native import or runtime admission."]}
    return proposal, handoff


def products(root: Path) -> dict[str, object]:
    candidate, foundation, registry = read_inputs(root)
    proposal, handoff = project(candidate, foundation, registry)
    manifest = {"manifest_version": "level053-input-pins.1", "inputs": [
        {"path": rel, "bytes": (root / rel).stat().st_size, "sha256": sha} for rel, sha in INPUTS.items()]}
    summary = {"summary_version": "level053-schema1-unallocated-summary.1",
               "proposal_sha256": digest(encoded(proposal)), "handoff_sha256": digest(encoded(handoff)),
               "printed_attacks": 1248, "silent_formations": 168,
               "native_run": False, "runtime_eligible": False, "admitted": False}
    return {"field-proposal.json": proposal, "allocation-handoff.json": handoff,
            "input-manifest.json": manifest, "summary.json": summary}


def output_dir(root: Path) -> Path:
    part = root
    for component in OUT_REL.parts:
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
    print(f"LEVEL53 {mode.upper()} PASS attacks=1248 silent=168 admitted=false")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("build", "verify"))
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    run(args.mode, args.root.resolve())


if __name__ == "__main__":
    main()
