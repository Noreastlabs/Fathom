#!/usr/bin/env python3
"""Project sealed whole-Level63 picking source into unallocated schema1 fields."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path

import curriculum_level063_whole_picking_candidate as source


ROOT = Path(__file__).resolve().parents[1]
OUT = Path("Build/parallel-13/level063-schema1-unallocated-r01")
CANDIDATE = Path("Build/parallel-05/2.3.1.2.1-level063-whole-r01/candidate-e.json")
FOUNDATION = Path("Content/controls/curriculum-v1/package.json")
PINS = {
    CANDIDATE: "b306c52226199025f3c39a1163c82a38fb914e8364104a17d644ee6218598e58",
    FOUNDATION: "766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255",
    Path("Results/primary/20260912T100538Z-2.1.1.2.1-r02-evidence/schema-freeze.json"): "0659fa962a5c933a2bcf3045772b6fe5b05b4deefb3511f5dcb68af51088de95",
    Path("Tools/curriculum_level063_whole_picking_candidate.py"): "89bf4ab4feab21b1cf4ab1c1edbcd44d36bce95450d0ffd54a867dad82d4c1fb",
    Path("Results/parallel-05/exercises/conversion/20260923T162500Z-2.3.1.2.1-level063-whole-picking-r01-results.md"): "b1bbde71c6b3d8c2ddba1a349a434f57cd605530db9f326be91e5a3815cf54bf",
    **{Path(rel): digest for rel, (_, digest) in source.PIN.items()},
}
UNRESOLVED = [
    "canonical workbook/module/item/event/variant IDs, lineage and revision",
    "fixed BPM, absolute onset/duration and note-per-click",
    "PDF-only J beat-one role accents require Curriculum interpretation",
    "PDF G TAB omission and J grouped layout retain TXT contact authority",
    "performed technique, endurance, mastery and runtime admission",
]


class ProposalError(ValueError):
    pass


def need(ok: bool, code: str) -> None:
    if not ok:
        raise ProposalError(code)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def encoded(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False,
                       separators=(",", ":")) + "\n").encode()


def pins() -> None:
    for rel, expected in PINS.items():
        path = ROOT / rel
        need(path.is_file() and not path.is_symlink() and
             path.resolve().is_relative_to(ROOT.resolve()), f"INPUT_PATH {rel}")
        need(sha(path.read_bytes()) == expected, f"INPUT_PIN {rel}")


def foundation_status() -> None:
    package = json.loads((ROOT / FOUNDATION).read_text())
    entry = [e for e in package["workbook_catalog"]["entries"]
             if e["workbook_id"] == "fg:workbook:000063"]
    need(len(package["records"]) == 659 and
         not any(r.get("legacy_level") == 63 for r in package["records"]) and
         len(entry) == 1 and entry[0]["representative_item_id"] is None and
         entry[0]["conversion_status"] == "not_converted" and
         entry[0]["whole_workbook_complete"] is False and
         all(entry[0][k] is False for k in
             ("admitted", "imported", "runtime_admitted", "runtime_eligible")),
         "FOUNDATION_ADMISSION")


def project(candidate: dict) -> tuple[dict, dict]:
    need(candidate["candidate_kind"] == "detached_whole_workbook_source_conversion" and
         candidate["level"] == 63 and candidate["section"] == "VII" and
         candidate["workstream"] == "2.3.1.2.1" and
         candidate["review"] == "Pending" and
         candidate["canonical_ids"] is None and
         all(candidate[k] is False for k in
             ("runtime_eligible", "imported", "admitted")) and
         candidate["workload_printed"] == source.EXPECTED and
         candidate["attack_count"] == 1016,
         "SOURCE_SCOPE")
    row = candidate["source_map_row"]
    need(row["level"] == 63 and row["section"] == "VII" and
         row["pair_status"] == "exact_stem_pair" and
         row["representative_item_id"] is None and
         row["conversion_status"] == "not_converted" and
         all(row[k] is False for k in
             ("admitted", "imported", "runtime_eligible")) and
         candidate["source_pins"] ==
         {rel: {"bytes": size, "sha256": digest}
          for rel, (size, digest) in source.PIN.items()},
         "SOURCE_LINEAGE")
    need(len(candidate["txt_source_lines"]) == 1564 and
         len(candidate["pdf_source_pages"]) == 20 and
         all(page["page"] == i and page["extracted_text_sha256"] ==
             sha(page["text"].encode())
             for i, page in enumerate(candidate["pdf_source_pages"], 1)) and
         [e["kind"] for e in candidate["source_exceptions"]] ==
         ["pdf_relayout", "pdf_relayout", "pdf_only_role_accent",
          "unquantified_performance"],
         "SOURCE_GUIDANCE")

    modules = candidate["modules"]
    need(len(modules) == 10 and [m["letter"] for m in modules] ==
         list(source.EXPECTED), "MODULE_SCOPE")
    records: list[dict] = []
    mapping: list[dict] = []
    module_counts: dict[str, dict] = {}
    txt_accents = pdf_accents = 0
    for module in modules:
        letter = module["letter"]
        cells = module["cells"]
        expected_cells = sum(n for _, n in source.PAGE_SPANS[letter])
        need(len(cells) == expected_cells and
             module["attack_count"] == source.EXPECTED[letter],
             f"MODULE_COUNT {letter}")
        module_attacks = 0
        for index, cell in enumerate(cells, 1):
            attacks = cell["attacks"]
            grid = cell["grid"]
            need(len(attacks) == cell["attack_count"] and
                 grid["pdf_page"] == source.page_for(letter, index) and
                 grid["txt_end_line"] == grid["txt_start_line"] + 8 and
                 grid["pdf_grid_relationship"] ==
                 ("PDF omits TAB" if letter == "G" else
                  "PDF combines four TXT bars" if letter == "J" else
                  "printed grid"), f"GRID_SOURCE {letter}{index}")
            if letter == "J":
                need(cell.get("pdf_beat_one_role_accent") is True,
                     f"J_PDF_ACCENT {index}")
                pdf_accents += 1
            else:
                need("pdf_beat_one_role_accent" not in cell,
                     f"PDF_ACCENT_SCOPE {letter}{index}")
            projected = []
            for ordinal, attack in enumerate(attacks, 1):
                refs = attack["source"]
                line_refs = refs["txt_lines"]
                need(attack["ordinal"] == ordinal and
                     attack["bar"] in (1, 2, 3, 4) and
                     attack["slot"] >= 1 and
                     attack["string"] in source.OPEN and
                     isinstance(attack["fret"], int) and
                     0 <= attack["fret"] <= 24 and
                     attack["midi"] == source.OPEN[attack["string"]] + attack["fret"] and
                     attack["midi"] % 12 == source.pitch_class(attack["spelling"]) and
                     source.NOTE.fullmatch(attack["spelling"]) is not None and
                     source.ROLE.fullmatch(attack["printed_role"]) is not None and
                     source.PICK.fullmatch(attack["printed_pick"]) is not None and
                     refs["pdf_page"] == grid["pdf_page"] and
                     len(line_refs) == 4 and
                     line_refs[:3] == list(range(grid["txt_start_line"],
                                                grid["txt_start_line"] + 3)) and
                     grid["txt_start_line"] + 3 <= line_refs[3] <=
                     grid["txt_end_line"] and
                     all(attack[k] is None for k in
                         ("canonical_event_id", "onset_q", "duration_q")),
                     f"ATTACK_SOURCE {letter}{index}:{ordinal}")
                if attack["printed_role"].startswith(">"):
                    need(letter == "H" and attack["slot"] == 1,
                         f"TXT_ACCENT_SCOPE {letter}{index}:{ordinal}")
                    txt_accents += 1
                projected.append({
                    "source_local_ordinal": ordinal,
                    "schema1_fields": {"event_id": None, "kind": "picked_note",
                                       "midi": attack["midi"],
                                       "string": attack["string"],
                                       "fret": attack["fret"],
                                       "onset_q": None, "duration_q": None},
                    "source_attack": copy.deepcopy(attack),
                    "printed_spelling": attack["spelling"],
                    "printed_chord_role": attack["printed_role"],
                    "printed_pick": attack["printed_pick"],
                    "pdf_only_beat_one_role_accent":
                        letter == "J" and attack["bar"] == 1 and
                        attack["slot"] == 1,
                })
            if letter == "J":
                need(sum(a["pdf_only_beat_one_role_accent"] for a in projected) == 1,
                     f"J_ACCENT_TARGET {index}")
            module_attacks += len(projected)
            key = f"L63-{letter}-{index:02d}"
            provenance = {"txt_path": source.TXT,
                          "txt_start_line": grid["txt_start_line"],
                          "txt_end_line": grid["txt_end_line"],
                          "pdf_path": source.PDF,
                          "pdf_page": grid["pdf_page"],
                          "source_candidate_sha256": PINS[CANDIDATE]}
            payload = {"source_local_key": key,
                       "identity_state": "unallocated",
                       "source_cell_sha256": sha(encoded(cell)),
                       "source_cell": copy.deepcopy(cell),
                       "source_provenance": provenance,
                       "schema1_fields": {
                           "id": None, "workbook_id": None, "module_id": None,
                           "lineage": None, "content_revision": None,
                           "legacy_level": 63,
                           "title": f"Level 63 module {letter} grid {index}",
                           "kind": "picking_grid",
                           "runtime_eligible": False,
                           "source_refs": [f"L63-TXT-{grid['txt_start_line']}-{grid['txt_end_line']}",
                                           f"L63-PDF-p{grid['pdf_page']}"],
                           "events": projected, "variants": [],
                           "timing": {"status": "unresolved",
                                      "onset_q": None, "duration_q": None,
                                      "fixed_bpm": None, "note_per_click": None},
                           "resource_requirements": [],
                           "ambiguities": UNRESOLVED}}
            records.append(payload)
            mapping.append({"source_local_key": key,
                            "source_cell_sha256": payload["source_cell_sha256"],
                            "module": letter, "grid": index,
                            "attacks": len(projected),
                            "txt_start_line": grid["txt_start_line"],
                            "pdf_page": grid["pdf_page"],
                            "pdf_only_beat_one_role_accent": letter == "J"})
        need(module_attacks == source.EXPECTED[letter],
             f"MODULE_ATTACKS {letter}")
        module_counts[letter] = {"grids": len(cells), "attacks": module_attacks}
    need(len(records) == 132 and sum(v["attacks"] for v in module_counts.values()) ==
         1016 and txt_accents == 36 and pdf_accents == 32,
         "WHOLE_COUNTS_ACCENTS")
    proposal = {"schema": "fathom-level063-schema1-field-proposal.1",
                "classification": "build_only_unallocated_nonimportable",
                "wbs_id": "2.3.1.2.1", "legacy_level": 63,
                "source_candidate_sha256": PINS[CANDIDATE],
                "source_map_row": copy.deepcopy(row),
                "source_pins": copy.deepcopy(candidate["source_pins"]),
                "txt_source_lines": copy.deepcopy(candidate["txt_source_lines"]),
                "pdf_source_pages": copy.deepcopy(candidate["pdf_source_pages"]),
                "source_exceptions": copy.deepcopy(candidate["source_exceptions"]),
                "pending": candidate["pending"],
                "module_counts": module_counts, "records": records,
                "txt_H_beat_one_role_accents": txt_accents,
                "pdf_only_J_beat_one_role_accents": pdf_accents,
                "canonical_ids_allocated": False, "runtime_eligible": False,
                "admitted": False, "whole_workbook_complete": False,
                "timing_resolved": False, "curriculum_signoff": False}
    handoff = {"schema": "fathom-level063-schema1-allocation-handoff.1",
               "field_proposal_sha256": sha(encoded(proposal)),
               "source_candidate_sha256": PINS[CANDIDATE],
               "records": mapping, "module_counts": module_counts,
               "txt_H_beat_one_role_accents": txt_accents,
               "pdf_only_J_beat_one_role_accents": pdf_accents,
               "unresolved": UNRESOLVED,
               "next_step": "independent source/music review before ID allocation or import",
               "admitted": False, "runtime_eligible": False,
               "whole_workbook_complete": False}
    return proposal, handoff


def derive() -> tuple[dict, dict]:
    pins()
    foundation_status()
    sealed = json.loads((ROOT / CANDIDATE).read_text())
    need(sealed == source.convert(ROOT), "P05_REPLAY_DRIFT")
    return project(sealed)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "verify"))
    args = parser.parse_args()
    proposal, handoff = derive()
    files = {"field-proposal.json": encoded(proposal),
             "allocation-handoff.json": encoded(handoff)}
    if args.command == "build":
        target = ROOT / OUT
        need(not target.exists() and not target.is_symlink(), "OUTPUT_EXISTS")
        target.mkdir(parents=True)
        for name, raw in files.items():
            (target / name).write_bytes(raw)
    for name, raw in files.items():
        need((ROOT / OUT / name).read_bytes() == raw, f"OUTPUT_DRIFT {name}")
    print(json.dumps({"status": "verified_unallocated_nonadmitted",
                      "grids": len(proposal["records"]), "attacks": 1016,
                      "txt_H_role_accents": 36, "pdf_only_J_role_accents": 32,
                      "field_proposal_sha256": sha(files["field-proposal.json"]),
                      "handoff_sha256": sha(files["allocation-handoff.json"])},
                     sort_keys=True))


if __name__ == "__main__":
    main()
