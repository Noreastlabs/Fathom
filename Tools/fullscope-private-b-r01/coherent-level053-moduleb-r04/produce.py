"""Build one exactly released family; read old custody, write only new roots."""
from pathlib import Path
from datetime import datetime, timezone
import collections
import copy
import hashlib
import importlib.util
import json
import re
import sys
import time
import pdfplumber

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
NAME = "coherent-level053-moduleb-r04"
RES = ROOT / "Results/fullscope-private-b-r01" / NAME
OUT = ROOT / "Build/fullscope-private-b-r01" / NAME
PROMPT = ROOT / "Prompts/fullscope-private-b-r01" / NAME
BASE = ROOT / "Results/fullscope-private-b-r01/checkpoint-r03/range-index.json"
GUARD = ROOT / "Tools/fullscope-private-b-r01/finite_level062_both_start_duty_r01.py"


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def pin(p): return {"path": str(p.relative_to(ROOT)), "bytes": p.stat().st_size, "sha256": sha(p)}
def checkpin(ref):
    assert pin(ROOT / ref["path"]) == {k: ref[k] for k in ("path", "bytes", "sha256")}, "INPUT_PIN_DRIFT"
def compact(x): return json.dumps(x, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
def save(p, x):
    assert not p.exists(), "PRESERVE_EXISTING_OUTPUT"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(x, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m
def norm(s): return re.sub(r"\s+", " ", s).strip()


def main():
    start = datetime.now(timezone.utc).isoformat(); timer = time.monotonic()
    assert not (RES / "handoff.json").exists() and not (OUT / "implementation-overlay.jsonl").exists()
    model = module("triad_model", Path(__file__).with_name("triad_task_model.py"))
    reservation = model.strict_json((PROMPT / "exact-key-reservation.json").read_bytes())
    assert sha(PROMPT / "exact-key-reservation.json") == "db814e13cc6f766313331a7adc07fd706064906a2c51c9147280a7e5644b0ce3"
    assert sha(PROMPT / "full-template-prompt.md") == "d4972d28eb84d6030ed8be8ce6f70d7b9d8009795a5dbb5cb4118e42b4a24c57"
    for field in ("governing_prompt", "coordinator_release", "candidate_scope", "census", "remaining_refs", "prior_handoff", "installed_representative_scope"):
        checkpin(reservation[field])
    for ref in reservation["source_refs"] + reservation["reuse_refs"]: checkpin(ref)
    assert sha(GUARD) == "f182c4c6a48140d0c7dc7a0a370e96ac862965f6859f0b6c5234137d85479d9d"
    assert sha(BASE) == "3a367221ea2f831c7774720730a9876eb59bb2656766336047270c8e0ae22ce8"
    guard = module("guarded_fold", GUARD)
    family = model.Family(ROOT)
    assert family.keys == reservation["keys"] and len(family.keys) == 167
    index, prior, effective, categories, used, operations = guard.fold_chain(BASE, ROOT / reservation["prior_handoff"]["path"])
    assert len(used) == 813 and operations == 951 and len(effective) == 2133
    assert collections.Counter(categories.values()) == prior["effective_categories"]
    installed_scope = model.strict_json((ROOT / reservation["installed_representative_scope"]["path"]).read_bytes())
    # Rehash every installed representative closure reference without constructing it.
    rep_refs = installed_scope.get("refs", installed_scope.get("artifact_refs", []))
    for ref in rep_refs: checkpin(ref)
    before_other = {k: guard.rh(v) for k, v in effective.items() if k not in family.keys}
    source_timer = time.monotonic(); pages = []
    with pdfplumber.open(ROOT / model.PDF) as pdf:
        assert len(pdf.pages) == 20
        for page in range(1, 7):
            text = pdf.pages[page - 1].extract_text(x_tolerance=1)
            expected = next(x["text"] for x in family.context["pdf_pages"] if x["physical_page"] == page)
            assert norm(text) == norm(expected), "ORIGINAL_PDF_CONTEXT_MISMATCH"
            pages.append({"physical_page": page, "normalized_text_sha256": hashlib.sha256(norm(text).encode()).hexdigest()})
            if page >= 3:
                for root in model.ROOTS:
                    matches = [s for s in text.splitlines() if re.match(r"^" + root + r"\s+" + root + r"-", s)]
                    assert len(matches) == 1, "ORIGINAL_TABLE_ROOT_ROW"
                    for quality in model.QUALITIES:
                        matches_b = [b for b in family.bindings.values() if b["pdf_page"] == page and b["printed_components"][:2] == [root, quality]]
                        assert len(matches_b) == 1
                        b = matches_b[0]
                        literal = family.lines[b["txt_line"] - 1]
                        assert norm(matches[0]) == norm(" ".join(s.strip() for s in literal.split("|"))), "ORIGINAL_PDF_TXT_ROW"
                        assert matches[0].split()[-6 + model.QUALITIES.index(quality)] == b["printed_components"][2], "ORIGINAL_PDF_CELL"
    source_seconds = time.monotonic() - source_timer
    rows, changes = [], []
    for key, released in zip(family.keys, reservation["rows"]):
        old = effective[key]
        assert key not in used and key != model.REPRESENTATIVE
        assert categories[key] == "implementation_or_interpretation_pending" and released["package_key"] == key
        assert guard.rh(old) == released["current_record_sha256"]
        checkpin(released["current_payload"])
        assert model.digest(family.bindings[key]) == released["binding_canonical_sha256"]
        contract = family.contract(key); family.validate(contract)
        new = copy.deepcopy(old)
        new["implementation"]["kind"] = "private_manual_source_order_triad_task"
        new["implementation"]["manual_execution_contract"] = contract
        new["status"] = "IMPLEMENTED_PRIVATE_QA_PENDING"
        new["provenance"]["coherent_sibling_task_r04"] = {
            "owner": "/root/private_b_mode_mirrors_resume", "independent_reviewer": "/root/private_source_bulk_review",
            "decision": "producer construction only; distinct QA pending", "canonical_ids_allocated": False,
            "reservation": pin(PROMPT / "exact-key-reservation.json"), "reused_policy": pin(ROOT / model.POLICY),
            "model": pin(Path(__file__).with_name("triad_task_model.py")),
            "source_order_actions": 4, "written_contacts": 3, "source_numeric_clock": None,
            "optional_authored_pulse_implemented": False, "installed_or_official_child_acceptance": False,
        }
        new["unresolved_reasons"] = copy.deepcopy(old["unresolved_reasons"]) + [
            "Independent source/semantics/behavior QA pending for this new sibling implementation.",
            "Source-order execution has no source-fixed numeric onset, duration, BPM or pick direction; optional authored pulse is referenced only.",
            "Acknowledgments are manual reports; physical, acoustic, workbook/session/mastery performance remains unobserved; runtime/admission/official child gates unexecuted.",
        ]
        assert new["implementation"]["events"] == old["implementation"]["events"]
        assert new["source_payload"] == old["source_payload"] and new["timing_authority"] == old["timing_authority"]
        rows.append(new)
        changes.append({"package_key": key, "source_identity": old["source_identity"], "base_record_sha256": guard.rh(old),
                        "overlay_line": len(rows), "overlay_record_sha256": guard.rh(new),
                        "old_category": categories[key], "new_category": "complete_manual_nonplayback_contract"})
        effective[key] = new; categories[key] = "complete_manual_nonplayback_contract"
    OUT.mkdir(parents=True, exist_ok=True)
    packet = OUT / "implementation-overlay.jsonl"
    packet.write_text("".join(compact(row) + "\n" for row in rows))
    family.load_packet(packet, sha(packet))
    identity = [[e["package_key"], effective[e["package_key"]]["source_identity"]] for e in index["children"]]
    assert guard.rh(identity) == index["ordered_identity_sha256"]
    assert all(guard.rh(effective[k]) == h for k, h in before_other.items()), "OUT_OF_SCOPE_MUTATION"
    check_counts = {"fresh_original_pdf_context_pages": 6, "pdf_txt_cell_bindings_including_preserved_representative": 168,
                    "all_key_exact_reservation_source_current_record_checks": 167, "all_key_exact_contract_packet_reload_checks": 167,
                    "all_key_voice_arithmetic_sets": 167, "written_unique_contacts": 501, "written_actions": 668,
                    "written_attack_member_occurrences": 1002, "unchanged_outside_scope_effective_records": 1966}
    save(RES / "source-and-integrity-checks.json", {"result": "PASS", "checks": check_counts, "original_page_refs": pages,
        "source_read_seconds": round(source_seconds, 6), "originals": family.source_refs,
        "representative_excluded": model.REPRESENTATIVE, "source_ambiguities_in_this_exact_map": 0,
        "unknown_source_clocks_per_key": 167, "all_actions_source_order_only": True,
        "historical_source_audit_reused_by_ref_not_rerun": reservation["reuse_refs"][2], "broad_independent_qa": "NOT_RUN"})
    elapsed = time.monotonic() - timer
    handoff = {"schema_version": 2, "status": "IMPLEMENTED_PRIVATE_QA_PENDING; coherent167-sibling producer construction sealed",
        "start_utc": start, "end_utc": datetime.now(timezone.utc).isoformat(), "converter_seconds": round(elapsed, 6),
        "source_read_seconds": round(source_seconds, 6), "base_index": pin(BASE), "prior_overlay_handoff": reservation["prior_handoff"],
        "overlay": pin(packet), "changes": changes, "revision_of_existing_overlay": False, "newly_replaced_keys": 167,
        "effective_categories": dict(collections.Counter(categories.values())), "effective_child_count": 2133,
        "effective_overlay_record_count": 980, "unique_replaced_children": 980, "total_replacement_operations": 1118,
        "ordered_identity_sha256": guard.rh(identity), "outside_child_ambiguities_unchanged": 6, "level57_unresolved_records_unchanged": 6,
        "excluded_installed_representative": model.REPRESENTATIVE, "model": pin(Path(__file__).with_name("triad_task_model.py")),
        "reservation": pin(PROMPT / "exact-key-reservation.json"), "source_inputs": family.source_refs,
        "producer_integrity": check_counts, "independent_reviewer": "/root/private_source_bulk_review; assigned, pending",
        "new_native_valid": 0, "new_integrated": 0, "new_independently_reviewed": 0, "new_accepted": 0,
        "fold_category_limit": "manual-contract category means producer behavior implemented; it is not QA or acceptance",
        "prior_32_key_reviewed_wave": "preserved; no repeated construction", "new_official_child_accepts": 0}
    save(RES / "handoff.json", handoff)
    _, _, again, cat, seen, total = guard.fold_chain(BASE, RES / "handoff.json")
    assert len(seen) == 980 and total == 1118 and cat == categories and all(again[r["package_key"]] == r for r in rows)
    for ref in reservation["source_refs"] + reservation["reuse_refs"]: checkpin(ref)
    print(compact({"handoff": pin(RES / "handoff.json"), "packet": pin(packet), "model": pin(Path(__file__).with_name("triad_task_model.py")),
                   "construction_seconds": round(elapsed, 6), "source_read_seconds": round(source_seconds, 6), "counts": check_counts}))


if __name__ == "__main__": main()
