#!/usr/bin/env python3
"""Independently audit P04 Level88 against all original pages before detached projection."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
from io import BytesIO
import json
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
OUT = Path("Build/parallel-07/2.3.1.3.1-level088-semantic-independent-review-r01")
STEM = "Guitar_Exercises_Section_XII_Level_88_Rock_Hard_Rock_and_Metal_Groove_Control_Eighth_Note_Drive_Gallops_Pedal_Tones_Power_Chord_Displacement_and_Riff_Architecture"
TXT = f"Notes/music/guitar project/TXT version/{STEM}.txt"
PDF = f"Notes/music/guitar project/PDF version/{STEM}.pdf"
P04_TOOL = "Tools/curriculum_level088_semantic_expansion_candidate.py"
P04 = "Build/parallel-04/2.3.1.3.1-level088-semantic-pdf-expansion-r07-source-wording-and-json-stability/candidate-a.json"
P03 = "Build/parallel-03/2.3.1.3.1-level-088-whole-source-index-r01/candidate-a.json"
MAP = "Results/parallel-01/exercises/inventory/20260922T180500Z-2.3-curriculum-v1-source-inventory-evidence/curriculum-source-map.json"
PACKAGE = "Content/controls/curriculum-v1/package.json"
REGISTRY = "Content/controls/curriculum-v1/identity-registry.json"
GENERATION = "Content/controls/curriculum-v1/generation.json"
INPUTS = {
    P04_TOOL: "f4416d907a6cb575ee4fa71f06e5da3daf193869625d7edcf13ca59868c7b87a",
    P04: "77d33a51c8af4267850c2f838f5f8561fffb7dd3967de0bf8d6e42b6fa822f3d",
    P03: "96d9ccbe08fc38c020c9a982e1ddf3c6419128ed39ceaffc7774d8c20dcbeecc",
    TXT: "0cbaa5ea7950658dc89eec8b484792d05a640d9532ef7add0442b571a07a2aac",
    PDF: "c2e71c0f2391c29d713f6992c9149e43ec599f9eb1cd1f08bf09d915f1a8971f",
    MAP: "bad5581a04f43ba8baf14db430449e1ccff5cf88f0f7e42198328073b27053d6",
    PACKAGE: "766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255",
    REGISTRY: "5d265859e1e8a5a530a0e53d88b019a1c920f3bba6cccb4ef0fef2f7640007e5",
    GENERATION: "fc6cec9f9d67eb82c97c5f4c3fb95d285178fb7fce7bd147d9ae0296d21b4c1c",
}
LABELS = tuple("ABCDEFGHIJ")
HEADERS = {"A": ["Pass", "Grid", "Mute target"], "B": ["Cell", "Sixteenth grid", "Picking goal"],
           "C": ["Riff", "Pedal", "Chord punctuation", "Pattern"],
           "D": ["Cell", "Chord attacks", "Purpose"], "E": ["Accent cycle", "Effect"],
           "F": ["Section", "Pedal behavior", "Chord behavior", "Dynamic"],
           "G": ["Riff", "Cell", "Identity"],
           "I": ["Bars", "Harmony", "Riff role", "Texture", "Dynamic"],
           "J": ["Failure", "Immediate repair"]}
FIELDS = {"A": ["pass", "grid_literal", "mute_target_literal"],
          "B": ["cell", "sixteenth_grid_literal", "picking_goal_literal"],
          "C": ["riff", "pedal_literal", "chord_punctuation_literal", "pattern_literal"],
          "D": ["cell", "chord_attacks_literal", "purpose_literal"],
          "E": ["accent_cycle_literal", "attack_pattern_literal", "effect_literal"],
          "F": ["section_literal", "pedal_behavior_literal", "chord_behavior_literal", "dynamic_literal"],
          "G": ["riff_label", "cell_literal", "identity_literal"],
          "I": ["bar_range_literal", "harmony_literal", "riff_role_literal", "texture_literal", "dynamic_literal"],
          "J": ["failure_literal", "immediate_repair_literal"]}


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise ValueError(reason)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def encoded(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def read_inputs(root: Path) -> dict:
    raw = {}
    for rel, expected in INPUTS.items():
        path = root / rel
        require(not path.is_symlink() and path.is_file() and path.resolve().is_relative_to(root), f"unsafe input: {rel}")
        value = path.read_bytes()
        require(sha(value) == expected, f"input drift: {rel}")
        raw[rel] = value
    page_text = [(page.extract_text() or "") for page in PdfReader(BytesIO(raw[PDF]), strict=True).pages]
    pages = [text.splitlines() for text in page_text]
    return {"root": root, "raw": raw, "candidate": json.loads(raw[P04]), "p03": json.loads(raw[P03]),
            "map": json.loads(raw[MAP]), "package": json.loads(raw[PACKAGE]),
            "registry": json.loads(raw[REGISTRY]), "generation": json.loads(raw[GENERATION]),
            "txt_lines": raw[TXT].decode().splitlines(), "pages": pages, "page_text": page_text}


def check_catalog(data: dict) -> None:
    package, registry, generation = data["package"], data["registry"], data["generation"]
    workbook = "fg:workbook:000088"
    require(len(package["records"]) == generation["records"] == 659, "current659 foundation drift")
    require(not any(r.get("legacy_level") == 88 or r.get("workbook_id") == workbook for r in package["records"]),
            "Level88 canonical record exists")
    require(not any(e.get("id") == workbook for e in registry["entities"]), "Level88 registry entity exists")
    entry = next((x for x in package["workbook_catalog"]["entries"] if x.get("workbook_id") == workbook), None)
    require(entry is not None and entry.get("catalog_role") == "read_only_source_preservation"
            and entry.get("conversion_status") == "not_converted" and entry.get("review") == "Pending"
            and entry.get("playable_projection", {}).get("status") == "explicitly_empty_unresolved"
            and all(entry.get(k) is False for k in ("admitted", "imported", "runtime_eligible", "runtime_admitted", "whole_workbook_complete")),
            "Level88 source-only catalog boundary drift")
    row = next((x for x in data["map"]["rows"] if x.get("level") == 88), None)
    require(row is not None and row.get("txt_sha256") == INPUTS[TXT] and row.get("pdf_sha256") == INPUTS[PDF]
            and row.get("txt_path") == TXT and row.get("pdf_path") == PDF
            and row.get("conversion_status") == "not_converted" and row.get("review") == "Pending"
            and all(row.get(k) is False for k in ("stable_ids_assigned", "runtime_eligible", "imported", "admitted")),
            "Level88 frozen source-map boundary drift")


def check_page_refs(data: dict) -> list[dict]:
    c, p03, pages = data["candidate"], data["p03"], data["pages"]
    require(len(pages) == len(c["pdf_page_references"]) == len(p03["pdf"]["pages"]) == 15,
            "15-page coverage drift")
    checks = []
    for n, lines in enumerate(pages, 1):
        hash_text = sha(data["page_text"][n-1].encode())
        ref, structural = c["pdf_page_references"][n-1], p03["pdf"]["pages"][n-1]
        require(ref["page_number"] == n and ref["source_path"] == PDF
                and ref["extracted_text_sha256"] == hash_text
                and structural["literal_extracted_text_sha256"] == hash_text
                and lines and lines[0] == ref["heading_literal"], f"page {n} PDF/P03/candidate parity drift")
        checks.append({"page_number": n, "line_count": len(lines), "extracted_text_sha256": hash_text,
                       "heading": lines[0]})
    require([x["literal"] for x in p03["txt"]["literal_lines"]] == data["txt_lines"]
            and len(data["txt_lines"]) == 43, "P03/TXT whole-line parity drift")
    return checks


def row_values(module: dict) -> list[str]:
    label = module["module_label"]
    return [str(row["fields"][field]) for row in module["task_rows"] for field in FIELDS[label]]


def check_task_pages(data: dict) -> list[dict]:
    c, pages = data["candidate"], data["pages"]
    modules = c["modules"]
    require([m["module_label"] for m in modules] == list(LABELS), "A-J module coverage drift")
    p1 = pages[0]
    require(p1[6:9] == ["Module", "Exercise", "Events"] and p1[-3:-1] == ["TOTAL", "1536"],
            "page 1 index/total drift")
    for i, module in enumerate(modules):
        label, title, count = module["module_label"], module["title_relationship"]["pdf_p1_title_literal"], module["declared_workload"]["value"]
        require(p1[9+3*i:12+3*i] == [label, title, str(count)]
                and module["pdf_index_workload"]["value"] == count
                and data["txt_lines"][module["source_ref"]["txt_line_number"]-1].endswith(f"- {count} events"),
                f"page 1/TXT module {label} workload parity drift")
    shared = c["shared_unassigned_reference"]
    p2 = [shared["heading_literal"], "Symbol", "Meaning", "Execution"]
    p2.extend(str(symbol[key]) for symbol in shared["symbols"]
              for key in ("symbol_literal", "meaning_literal", "execution_literal"))
    p2.append(shared["guidance_literal"])
    require(pages[1] == p2 and shared["module_label"] is None, "page 2 unassigned vocabulary drift")
    checks = [{"page": 1, "kind": "index", "rows": 10}, {"page": 2, "kind": "unassigned_vocabulary", "rows": 6}]
    for module in modules:
        label = module["module_label"]
        if label == "H":
            for row in module["task_rows"]:
                page = row["source_ref"]["page_number"]
                expected = [module["title_relationship"]["pdf_detail_heading_literals"][page-10],
                            row["fields"]["chord_cells_literal"], row["fields"]["descriptor_literal"],
                            "Pass", "Requirement"]
                expected.extend(str(v) for pair in row["pass_requirements"]
                                for v in (pair["pass_ordinal"], pair["requirement_literal"]))
                require(pages[page-1] == expected, f"page {page} H study task-table parity drift")
                checks.append({"page": page, "kind": "H_study", "rows": 6})
            continue
        page = module["source_ref"]["pdf_detail_pages"][0]
        heading = module["title_relationship"]["pdf_detail_heading_literals"][0]
        guide = module["explicit_guidance_literals"]
        if label == "B":
            expected = [heading, guide[0], *HEADERS[label], *row_values(module), guide[1]]
        elif label == "E":
            expected = [heading, HEADERS[label][0], guide[0], HEADERS[label][1], *row_values(module), guide[1]]
        elif label == "I":
            expected = [heading, *HEADERS[label], *row_values(module), guide[0]]
        elif label == "J":
            expected = [heading, *HEADERS[label], *row_values(module)]
            mastery = c["mastery_comparison"]
            expected += ["Mastery: " + mastery["pdf_literal"].splitlines()[0], *mastery["pdf_literal"].splitlines()[1:]]
            require(pages[page-1][:len(expected)] == expected
                    and len(pages[page-1]) == len(expected)+2
                    and pages[page-1][-2].startswith("Next: Level 89"), "page 15 J rubric/table parity drift")
            checks.append({"page": page, "kind": "J_repair_and_rubric", "rows": len(module["task_rows"])})
            continue
        else:
            expected = [heading, *HEADERS[label], *row_values(module), *guide]
        require(pages[page-1] == expected, f"page {page} module {label} full task-table parity drift")
        checks.append({"page": page, "kind": f"module_{label}_task_table", "rows": len(module["task_rows"])})
    require(sorted(x["page"] for x in checks) == list(range(1,16)), "task page coverage gap")
    return sorted(checks, key=lambda x:x["page"])


def check_ambiguities(data: dict) -> None:
    c, pages = data["candidate"], data["pages"]
    require(sum(m["declared_workload"]["value"] for m in c["modules"]) == 1536
            and c["workload_reconciliation"]["task_to_event_reconciliation"] == "blocked_unresolved"
            and all(m["source_task_to_event_mapping"] is None for m in c["modules"]),
            "invented task/event mapping")
    relation = c["capstone_order_relation"]
    require(relation["bar_ranges"] == [f"{i}-{i+3}" for i in range(1,33,4)]
            and relation["event_mapping"] is None
            and relation["event_declaration"]["pdf_p1_value"] == 256
            and relation["event_declaration"]["reconciliation_status"] == "blocked_unresolved"
            and "time signature" in relation["event_declaration"]["reason"]
            and not any("time signature" in line.lower() for line in pages[13]),
            "page 14 I event/time-signature ambiguity drift")
    rubric = c["mastery_comparison"]
    require(rubric["scoring_allocation"] is None
            and rubric["txt_literals"] == [data["txt_lines"][38], data["txt_lines"][39]]
            and "14/16 or better" in rubric["pdf_literal"]
            and "No zero in pulse, gallop control, pedal/chord balance, or recovery." in rubric["pdf_literal"],
            "page 15 J scoring-allocation ambiguity drift")


def replay_p04(root: Path, candidate: dict) -> None:
    spec = importlib.util.spec_from_file_location("sealed_level088_builder", root / P04_TOOL)
    require(spec is not None and spec.loader is not None, "P04 builder unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    require(module.build_candidate(root) == candidate, "P04 sealed-candidate/source replay drift")


def review(data: dict, *, replay: bool = True) -> dict:
    check_catalog(data)
    c = data["candidate"]
    require(c["candidate_status"] == "pending_task_to_event_reconciliation"
            and c["wbs_id"] == "2.3.1.3.1" and c["level"] == 88
            and all(c[k] is False for k in ("canonical_ids_allocated", "canonical_record_emitted",
                                           "runtime_eligible", "runtime_admitted", "imported", "admitted",
                                           "whole_workbook_complete")), "candidate authority/scope drift")
    pages = check_page_refs(data)
    task_pages = check_task_pages(data)
    check_ambiguities(data)
    if replay:
        replay_p04(data["root"], c)
    return {"review_version": "level088-p07-independent-semantic-review.1", "parity": "pass",
            "source_pdf_pages": pages, "task_page_checks": task_pages,
            "source_task_units": sum(m["task_unit_count"] for m in c["modules"]),
            "declared_events_unmapped": 1536, "module_I_events_unmapped": 256,
            "page14_time_signature": None, "module_J_point_allocation": None,
            "parent_status": "Pending", "projection_condition_satisfied": True}



def output_dir(root: Path) -> Path:
    path = root
    for part in OUT.parts:
        path /= part
        require(not path.is_symlink(), "output symlink path")
    return path


def run(mode: str, root: Path) -> None:
    verdict = review(read_inputs(root))
    out = output_dir(root)
    payload = encoded(verdict)
    if mode == "review":
        out.mkdir(parents=True, exist_ok=True)
        (out / "review.json").write_bytes(payload)
    else:
        path = out / "review.json"
        require(not path.is_symlink() and path.read_bytes() == payload, "review output drift")
    print(f"LEVEL88 {mode.upper()} PASS pages=15 tasks=70 mapped_events=0 projection=parked")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("review", "verify"))
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    run(args.mode, args.root.resolve())
