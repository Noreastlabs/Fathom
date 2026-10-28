#!/usr/bin/env python3
"""Project sealed Level64 printed positions into detached unallocated schema1 fields."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from curriculum_level064_whole_candidate import build_candidate


ROOT = Path(__file__).resolve().parents[1]
OUT_REL = Path("Build/parallel-06/level064-schema1-unallocated-r01")
WHOLE = "Build/parallel-09/2.3.1.2.1-level064-whole-r01/level064-whole-candidate-03.json"
INDEX = "Build/parallel-01/2.3-level064-whole-coverage-index-r01/candidate-r01.json"
STEM = "Guitar_Exercises_Section_VII_Level_64_Long_Form_Arpeggio_Solo_Construction_Secondary_Dominants_Key_Changes_and_System_Aware_Phrase_Orchestration"
TXT = f"Notes/music/guitar project/TXT version/{STEM}.txt"
PDF = f"Notes/music/guitar project/PDF version/{STEM}.pdf"
PACKAGE = "Content/controls/curriculum-v1/package.json"
REGISTRY = "Content/controls/curriculum-v1/identity-registry.json"
SOURCE_MAP = "Results/parallel-01/exercises/inventory/20260922T180500Z-2.3-curriculum-v1-source-inventory-evidence/curriculum-source-map.json"
FREEZE = "Results/primary/20260912T100538Z-2.1.1.2.1-r02-evidence/schema-freeze.json"
SCHEMA_SOURCE = "Source/content/Canonical.cpp"
DEGREE_ANCHOR = '    const auto& degrees=at(j,"degree_contexts");'
DEGREE_EXCERPT_SHA256 = "02f06217071778b10761cf64b9613e96f2b3d6fa3827a95f95d088f15e1b80e9"
INPUTS = {
    WHOLE: "684e272826c8b9403ea3d9b2a159c7be1c48c19b3ad951119ffb5620fe2dc65d",
    "Tools/curriculum_level064_whole_candidate.py": "be5bcad696178d0e390fc365a1b76b472eb676206cf8e4763f4ac4b9c62f5b02",
    INDEX: "9e9256c41c65656298c97d0e45f88e7430a4256e955f562e5739cef3bbd12c23",
    TXT: "f00e6ef35a1971a91aab67103c69338c4b4a041ca37a100ec857b8537f3f6f24",
    PDF: "70c3179403ca12179f99f072911a76c56c88279e40534030184415e8f6d8a145",
    PACKAGE: "766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255",
    REGISTRY: "5d265859e1e8a5a530a0e53d88b019a1c920f3bba6cccb4ef0fef2f7640007e5",
    SOURCE_MAP: "bad5581a04f43ba8baf14db430449e1ccff5cf88f0f7e42198328073b27053d6",
    FREEZE: "0659fa962a5c933a2bcf3045772b6fe5b05b4deefb3511f5dcb68af51088de95",
    SCHEMA_SOURCE: "7b8e8f0f7c9e1c9a604255bba543712690d03c71cda12b3a241ee9a8350eb938",
}
COUNTS = {"A": 40, "B": 40, "C": 40, "D": 64, "E": 64,
          "F": 64, "G": 128, "H": 64, "I": 64, "J": 72}
DISCREPANCIES = {"PDF_ONLY_PRACTICE_LOG_FIELDS", "P01_D_PAGE8_PART_LABEL"}
EXCEPTIONS = {"LEVEL64-PAGES-01-02-REFERENCE-ONLY", "LEVEL64-PAGE20-PRACTICE-LOG-PDF-ONLY",
              "LEVEL64-MODULE-D-PAGE-8-PART-METADATA", "LEVEL64-MODULE-B-PAGE-5-RASTER-LIMIT",
              "LEVEL64-MODULE-J-CARD-TAB-ABSENCE", "LEVEL64-TUNING-UNSPECIFIED"}
UNRESOLVED = [
    "Canonical workbook/module/item/event/variant identities and lineage remain unallocated.",
    "Tuning is unspecified, so printed note and TAB tokens do not establish sounding MIDI pitch.",
    "Numeric onset/duration, fixed BPM, note-per-click, pick execution and performed result remain unresolved.",
    "PDF-only practice-log labels, D-page-8 part label and page-5 raster qualification await source review.",
    "Module J recovery-card note/role positions have no printed TAB; playable contact is unspecified.",
]


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def encoded(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False,
                       separators=(",", ":")) + "\n").encode()


def checked_file(root: Path, rel: str, expected: str) -> bytes:
    path = root / rel
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"missing or symlink input: {rel}")
    data = path.read_bytes()
    if sha(data) != expected:
        raise ValueError(f"input drift: {rel}")
    return data


def read_inputs(root: Path) -> tuple[dict, dict, dict, dict, list[dict]]:
    raw = {rel: checked_file(root, rel, expected) for rel, expected in INPUTS.items()}
    whole = json.loads(raw[WHOLE])
    index = json.loads(raw[INDEX])
    freeze = json.loads(raw[FREEZE])
    if (freeze.get("decision") != "Technical schema1 FROZEN"
            or freeze.get("schema_version") != "1.0.0-curriculum-candidate"):
        raise ValueError("schema freeze drift")
    schema_source = raw[SCHEMA_SOURCE].decode()
    if schema_source.count(DEGREE_ANCHOR) != 1:
        raise ValueError("degree contract anchor drift")
    begin = schema_source.index(DEGREE_ANCHOR)
    excerpt = schema_source[begin:schema_source.index("\n}", begin)].encode()
    if sha(excerpt) != DEGREE_EXCERPT_SHA256 or 'if(!degrees.isObject())' not in excerpt.decode():
        raise ValueError("frozen degree context object contract drift")
    entries = index["module_candidate_union"]
    if len(entries) != 12 or [s["slice_key"] for s in whole["p01_slices"]] != [e["candidate_key"] for e in entries]:
        raise ValueError("P01 slice union/order drift")
    slice_pins = []
    for entry, whole_ref in zip(entries, whole["p01_slices"]):
        ref = entry["candidate_ref"]
        if whole_ref["candidate_ref"] != ref or whole_ref["result_ref"] != entry["result_ref"]:
            raise ValueError("P01 slice reference drift")
        data = checked_file(root, ref["path"], ref["sha256"])
        if len(data) != ref["bytes"]:
            raise ValueError("P01 slice byte-length drift")
        slice_pins.append({"path": ref["path"], "bytes": len(data),
                           "sha256": ref["sha256"], "slice_key": entry["candidate_key"]})
    if whole != build_candidate():
        raise ValueError("sealed whole candidate differs from original TXT/PDF/P01 replay")
    return whole, index, json.loads(raw[PACKAGE]), json.loads(raw[REGISTRY]), slice_pins


def identity_boundary(package: dict, registry: dict) -> dict:
    wid = "fg:workbook:000064"
    if any(r.get("legacy_level") == 64 or r.get("workbook_id") == wid
           for r in package["records"]):
        raise ValueError("unexpected canonical Level64 record")
    if any(e.get("id") == wid for e in registry["entities"]):
        raise ValueError("unexpected Level64 registry entity")
    entries = [e for e in package["workbook_catalog"]["entries"]
               if e.get("workbook_id") == wid]
    if len(entries) != 1:
        raise ValueError("Level64 catalog identity drift")
    entry = entries[0]
    if (entry.get("conversion_status") != "not_converted"
            or entry.get("whole_workbook_complete") is not False
            or entry.get("admitted") is not False
            or entry.get("runtime_eligible") is not False
            or entry.get("representative_item_id") is not None):
        raise ValueError("Level64 source-only catalog drift")
    return entry


def check_boundary(whole: dict, index: dict) -> None:
    if (whole.get("schema") != "fathom-level064-whole-detached-candidate-v1"
            or whole.get("level") != 64 or whole.get("wbs_id") != "2.3.1.2.1"
            or whole.get("complete_written_workout_printed_positions") != 640
            or whole.get("module_printed_position_counts") != COUNTS
            or len(whole.get("positions", [])) != 640
            or list(whole.get("modules", {})) != list(COUNTS)
            or whole.get("source_only_reference_pages") != [1, 2, 20]
            or len(whole.get("pdf_page_texts", [])) != 20
            or {x["code"] for x in whole.get("source_discrepancies", [])} != DISCREPANCIES
            or {x["id"] for x in index["coverage_exceptions"]} != EXCEPTIONS
            or index["coverage_scope"]["printed_position_count"] != 640
            or index["coverage_scope"]["module_candidate_pdf_pages"] != list(range(3, 20))):
        raise ValueError("whole Level64 source coverage/exception drift")
    if any(whole.get(k) is not None for k in ("canonical_item_id", "canonical_variant_id",
              "fixed_bpm", "note_per_click", "onset_q", "duration_q", "performed_result")):
        raise ValueError("candidate invented identity/timing/performance")
    if any(whole.get(k) is not False for k in ("runtime_eligible", "runtime_admitted",
              "imported", "admitted", "curriculum_signoff")):
        raise ValueError("candidate admission drift")
    if (whole["source"]["txt_sha256"] != INPUTS[TXT]
            or whole["source"]["pdf_sha256"] != INPUTS[PDF]
            or whole["source"]["pdf_pages"] != 20
            or whole["p01_index_ref"]["sha256"] != INPUTS[INDEX]):
        raise ValueError("source identity drift")
    if (whole["pdf_only_practice_log_fields"] != ["Date", "Study / key change", "System",
            "BPM", "Clean?", "Weak harmony / phrase / system", "Next target"]):
        raise ValueError("PDF-only practice-log field drift")
    if len(whole["other_source_limits"]) != 4:
        raise ValueError("source limit drift")


def source_contact(pos: dict, module: str, ordinal: int, slice_keys: set[str]) -> dict:
    expected = {"canonical_event_id", "duration_q", "module", "note_token", "onset_q",
                "path_in_slice", "pick_token", "role_token", "slice_key", "sounding_pitch",
                "source_local_key", "source_order", "source_refs", "source_tab"}
    if (set(pos) != expected or pos["module"] != module or pos["source_order"] != ordinal
            or pos["slice_key"] not in slice_keys or not pos["path_in_slice"]
            or not isinstance(pos["note_token"], str) or not pos["note_token"]
            or not isinstance(pos["role_token"], str) or not pos["role_token"]
            or not isinstance(pos["source_refs"], dict) or not pos["source_refs"]
            or (pos["pick_token"] is not None and not isinstance(pos["pick_token"], str))):
        raise ValueError("position token/order/provenance drift")
    if any(pos[k] is not None for k in ("canonical_event_id", "onset_q", "duration_q", "sounding_pitch")):
        raise ValueError("position invented identity/timing/pitch")
    tab = pos["source_tab"]
    if tab is not None and (not isinstance(tab, dict) or set(tab) != {"string_label", "fret_token"}
                            or tab["string_label"] not in ("E", "A", "D", "G", "B", "e")
                            or not str(tab["fret_token"]).isdigit()):
        raise ValueError("printed TAB token drift")
    return {
        "source_position": pos,
        "source_role_token": pos["role_token"],
        "source_pick_token": pos["pick_token"],
        "source_tab": tab,
        "performed_result": None,
        "schema1_fields": {
            "event_id": None, "kind": "note", "attack": None,
            "spelling": pos["note_token"], "midi": None,
            "string": None, "fret": None, "finger": None,
            "degree_contexts": {}, "onset_q": None, "duration_q": None,
            "tie_from": None,
        },
    }


def project(whole: dict, index: dict, package: dict, registry: dict) -> tuple[dict, dict]:
    catalog = identity_boundary(package, registry)
    check_boundary(whole, index)
    slice_entries = {e["candidate_key"]: e for e in index["module_candidate_union"]}
    records, all_positions = [], []
    card_count = bridge_count = 0
    for module, expected_count in COUNTS.items():
        source = whole["modules"][module]
        if source["module"] != module or len(source["positions"]) != expected_count:
            raise ValueError("module position count drift")
        slice_keys = {s["slice_key"] for s in source["slices"]}
        if not slice_keys <= set(slice_entries):
            raise ValueError("module slice key drift")
        contacts = []
        for ordinal, pos in enumerate(source["positions"], 1):
            if module not in slice_entries[pos["slice_key"]]["modules"]:
                raise ValueError("module/slice membership drift")
            contacts.append(source_contact(pos, module, ordinal, slice_keys))
            all_positions.append(pos)
            if module == "J":
                path = pos["path_in_slice"]
                if path[0] == "recovery_cards":
                    if pos["source_tab"] is not None:
                        raise ValueError("J card invented TAB")
                    card_count += 1
                elif path[0] == "modulation_bridges":
                    if pos["source_tab"] is None:
                        raise ValueError("J bridge missing printed TAB")
                    bridge_count += 1
                else:
                    raise ValueError("J source order/path drift")
        slices, variants = [], []
        for slice_source in source["slices"]:
            key = slice_source["slice_key"]
            entry = slice_entries[key]
            if (slice_source["candidate_ref"] != entry["candidate_ref"]
                    or slice_source["pdf_pages"] != entry["pdf_pages"]
                    or slice_source["txt_lines"] != entry["txt_lines"]):
                raise ValueError("module slice metadata drift")
            ordinals = [n for n, pos in enumerate(source["positions"], 1)
                        if pos["slice_key"] == key]
            if len(ordinals) != slice_source["printed_position_count"]:
                raise ValueError("module slice contact count drift")
            slices.append(slice_source)
            variants.append({"id": None, "source_slice_key": key,
                             "source_event_ordinals": ordinals,
                             "event_ids": None, "runtime_eligible": False})
        records.append({"source_component": module, "identity_state": "unallocated",
                        "source_slices": slices,
                        "schema1_fields": {
                            "id": None, "workbook_id": None, "module_id": None,
                            "legacy_level": 64, "title": f"Level 64 module {module}",
                            "kind": "mixed", "content_revision": None, "lineage": None,
                            "runtime_eligible": False, "source_refs": None,
                            "events": contacts, "variants": variants,
                            "resource_requirements": [],
                            "timing": {"status": "unresolved", "unit": "quarter", "fixed_bpm": None},
                            "ambiguities": UNRESOLVED,
                        }})
    if all_positions != whole["positions"]:
        raise ValueError("whole normalized position union/order drift")
    if (card_count, bridge_count) != (24, 48):
        raise ValueError("J card/bridge TAB boundary drift")
    if ([p["path_in_slice"][0] for p in whole["modules"]["J"]["positions"]]
            != ["recovery_cards"] * 24 + ["modulation_bridges"] * 48):
        raise ValueError("J printed order drift")
    proposal = {
        "proposal_version": "level064-unallocated-schema1-fields.1", "wbs_id": "2.3.1.2.1",
        "classification": "Build-only, nonimportable schema1 field proposal",
        "legacy_level": 64, "canonical_ids_allocated": False,
        "schema1_importable": False, "whole_workbook_complete": False,
        "runtime_eligible": False, "admitted": False,
        "counts": {"provisional_components": 10, "p01_slices": 12,
                   "source_described_printed_positions": 640, "by_module": COUNTS,
                   "j_recovery_note_role_positions_without_tab": 24,
                   "j_bridge_positions_with_tab": 48},
        "source": whole["source"], "source_catalog_level": catalog,
        "source_map_boundary": whole["source_map_boundary"],
        "source_p01_index_ref": whole["p01_index_ref"],
        "source_p01_slices": whole["p01_slices"],
        "source_only_reference_pages": whole["source_only_reference_pages"],
        "source_txt_document_text": whole["txt_document_text"],
        "source_pdf_page_texts": whole["pdf_page_texts"],
        "source_only_references": index["source_only_references"],
        "source_pdf_only_practice_log_fields": whole["pdf_only_practice_log_fields"],
        "source_discrepancies": whole["source_discrepancies"],
        "source_coverage_exceptions": index["coverage_exceptions"],
        "source_other_limits": whole["other_source_limits"],
        "records": records,
    }
    handoff = {
        "handoff_version": "level064-allocation-handoff.1", "wbs_id": "2.3.1.2.1",
        "catalog_workbook_id": catalog["workbook_id"],
        "existing_level064_records": 0, "existing_level064_workbook_entities": 0,
        "proposed_component_partition": list(COUNTS),
        "source_described_printed_positions": 640,
        "canonical_ids_allocated": False, "admitted": False,
        "required_decisions": [
            "Disposition PDF-only page-20 log labels, D-page-8 part label and page-5 raster qualification.",
            "Review P01 module-specific semantic limits, including literal F6 role A and J card TAB absence.",
            "Allocate stable workbook/module/item/event/variant identities and revision lineage.",
            "Authorize tuning, pitch binding, timing, click, pick execution and mastery semantics before native import.",
            "Complete musical correctness and Curriculum review for all A–J source structures.",
        ],
    }
    return proposal, handoff


def products(root: Path) -> dict[str, object]:
    whole, index, package, registry, slice_pins = read_inputs(root)
    proposal, handoff = project(whole, index, package, registry)
    manifest = {"manifest_version": "level064-input-pins.1", "inputs": [
        {"path": rel, "bytes": (root / rel).stat().st_size, "sha256": expected}
        for rel, expected in INPUTS.items()] + slice_pins}
    summary = {"summary_version": "level064-schema1-unallocated-summary.1",
               "proposal_sha256": sha(encoded(proposal)),
               "handoff_sha256": sha(encoded(handoff)),
               "source_described_printed_positions": 640,
               "j_without_tab": 24, "native_run": False,
               "runtime_eligible": False, "admitted": False}
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
    print("LEVEL64 " + mode.upper() + " PASS modules=10 slices=12 positions=640 admitted=false")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("mode", choices=("build", "verify"))
    ap.add_argument("--root", type=Path, default=ROOT)
    args = ap.parse_args()
    run(args.mode, args.root.resolve(strict=True))


if __name__ == "__main__":
    main()
