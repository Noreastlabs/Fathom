"""Construct exactly12 existing PDF19 recovery keys; producer guards only."""
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter
import copy
import hashlib
import importlib.util
import json
import sys
import time

sys.dont_write_bytecode = True
import pdfplumber
import recovery_pair_model as model

ROOT = Path(__file__).resolve().parents[3]
NAME = "finite-level068-recovery-pairs-manual-r03"
RES = ROOT / "Results/fullscope-private-b-r01" / NAME
OUT = ROOT / "Build/fullscope-private-b-r01" / NAME
PROMPTS = ROOT / "Prompts/fullscope-private-b-r01" / NAME
PREV = ROOT / "Results/fullscope-private-b-r01/finite-level068-mode-mirrors-manual-r02/handoff.json"
PREV_SHA = "47c8cda6777ce56b58a89dc0c8ea4118ea57d0fc82559952302aa8e012f666ac"
OLD = ROOT / "Tools/fullscope-private-b-r01/finite_level068_mode_mirrors_manual_r01.py"
OLD_SHA = "336b170b275d476ca02b689bf32fa02d8334622b5ad6c64fd3c78e7fcc9a8a02"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pin(path):
    return {"path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size, "sha256": sha(path)}


def check_pin(ref):
    model.require(pin(ROOT / ref["path"]) == {k: ref[k] for k in ["path", "bytes", "sha256"]}, "PIN_DRIFT")


def save(path, value):
    model.require(not path.exists(), "OUTPUT_EXISTS")
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def import_file(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def construct(old, source_row):
    new = copy.deepcopy(old)
    key = new["package_key"]
    number, pair = model.pair_for_key(key)
    model.require(source_row["package_key"] == key and source_row["source_identity"] == old["source_identity"]
                  and source_row["pdf_page"] == 19, "SOURCE_ROW_KEY_PAGE")
    label = pair[1] + ": " + pair[2] + " -> " + pair[3]
    role = pair[4] + " -> " + pair[5]
    model.require(source_row["pdf_three_line_card"] == label + "\n" + role + "\n2 tones" and
                  source_row["txt_literal"] == label + "   " + role, "SOURCE_MEANING")
    model.check_source_events(key, old["implementation"]["events"])
    locator = {"line_start": source_row["txt_line"], "line_end": source_row["txt_line"],
               "module": "K", "label": label}
    new["source_refs"][0]["locator"] = locator
    new["source_payload"]["txt_excerpt"] = source_row["txt_literal"]
    new["source_payload"]["source_discrepancy"] = [{
        "class": "recovery_pair_original_pdf_txt_exact_semantics",
        "previous_diagnostic": old["source_payload"].get("source_discrepancy"),
        "previous_source_scope": old["implementation"]["source_scope"],
        "resolution": "Exact three-line original PDF19 card matches one TXT recovery line. New54-point card height excludes neighboring ear-test/error text. Printed pitches and null positions/clocks are unchanged; chosen positions remain derived performer choices.",
        "interpretation": "B producer provisional, independent review pending",
        "TXT": locator,
    }]
    scope = new["implementation"]["source_scope"]
    scope["locator"] = {"physical_page": 19, "derived_bbox": source_row["pdf_bbox"],
                        "supplemental_txt_locator": locator,
                        "method": "original PDF exact three-line recovery card; TXT exact one-line semantic pair"}
    scope["pdf_excerpt"] = source_row["pdf_three_line_card"]
    scope["selected_source_text"] = source_row["txt_literal"]
    new["implementation"]["instructions"] = source_row["pdf_three_line_card"].splitlines()
    new["implementation"]["ordered_steps"] = [{"order": i, "instruction": text} for i, text in
                                              enumerate(new["implementation"]["instructions"], 1)]
    new["implementation"]["context_tasks"] = [{"order": 1, "instruction": model.SOURCE_RULE,
                                              "source": {"physical_page": 19, "location": "recovery source heading"},
                                              "response": "manual declaration; no observed performance or credit"}]
    new["implementation"]["kind"] = "manual_explicit_recovery_contacts_and_existing_bar_simplification"
    new["implementation"]["manual_execution_contract"] = model.make_contract(key, new["source_identity"],
                                                                             new["implementation"]["events"])
    new["unresolved_reasons"] = [{"field": "printed recovery-pair position/octave/fingering/timing",
                                 "reason": "Not specified by source. The private manual task has an explicit typed performer-choice interface and derived bounded menu; no printed string/fret/onsets/duration or fixed physical-security claim is invented.",
                                 "implementation_disposition": "Choice interface implemented; source unknowns retained"}]
    new["provenance"]["conversion"] = str(Path(__file__).relative_to(ROOT))
    new["provenance"]["producer_role"] = "B resumed private recovery producer; independent source/behavior review pending"
    new["provenance"]["qa_disposition"] = "QA_PENDING"
    new["status"] = "IMPLEMENTED_PRIVATE_QA_PENDING"
    return new


def verify_record(old, new, source_row):
    model.require(model.compact(new) == model.compact(construct(old, source_row)) and
                  new["implementation"]["events"] == old["implementation"]["events"] and
                  new["timing_authority"] == old["timing_authority"], "EXACT_SOURCE_BOUND_RECORD")


def main():
    timer = time.monotonic(); started = datetime.now(timezone.utc).isoformat()
    model.require(not (RES / "handoff.json").exists() and sha(PREV) == PREV_SHA and sha(OLD) == OLD_SHA,
                  "PRIOR_CUSTODY_OR_OUTPUT")
    reservation = json.loads((PROMPTS / "exact-key-reservation.json").read_text())
    for ref in [reservation["governing_corrected_prompt"], reservation["superseded_reference_error_prompt"],
                reservation["prior_overlay_handoff"]] + reservation["source_refs"]:
        check_pin(ref)
    old_module = import_file(OLD, "historical_source_tools")
    for path, expected in old_module.PINS:
        model.require(sha(path) == expected, "HISTORICAL_INPUT_PIN")
    folder = old_module.module(old_module.FOLD, "guarded_folder")
    index, previous, effective, categories, used, operations = folder.fold_chain(old_module.BASE, PREV)
    model.require(len(effective) == 2133 and len(used) == 801 and operations == 939, "CURRENT_CHAIN")
    entries = [e for e in index["children"] if e["level"] == 68 and 50 <= e["line"] <= 61]
    identities = [[e["package_key"], e["source_identity"]] for e in entries]
    model.require(identities == reservation["keys"] and model.digest(identities) == reservation["ordered_identity_sha256"]
                  and len(entries) == 12, "EXACT_TWELVE_KEY_CUSTODY")
    old_rows = [effective[e["package_key"]] for e in entries]
    model.require(all(categories[e["package_key"]] == "performer_choice_missing_fixed_realization" and
                      e["package_key"] not in used for e in entries), "GENUINELY_UNCONSTRUCTED_CHOICES")
    refs = reservation["source_refs"]
    lines = (ROOT / refs[0]["path"]).read_text().splitlines()
    context = json.loads((ROOT / refs[2]["path"]).read_text())
    pages = {p["physical_page"]: p["text"] for p in context["pdf_pages"]}
    checks = []
    with pdfplumber.open(ROOT / refs[1]["path"]) as pdf:
        model.require(len(pdf.pages) == 20, "ORIGINAL_PAGE_COUNT")
        for page in [1, 19, 20]:
            raw = pdf.pages[page - 1].extract_text(x_tolerance=1)
            model.require(old_module.norm(raw) == old_module.norm(pages[page]), "ORIGINAL_CONTEXT")
        model.require(model.SOURCE_RULE in pages[19] and model.SAFETY in old_module.norm(pages[1]) and
                      model.TARGET_RULE in lines, "ORIGINAL_RECOVERY_RULES")
        for old, source_row in zip(old_rows, reservation["source_rows"]):
            model.require(model.digest(old) == source_row["previous_effective_record_sha256"] and
                          old["package_key"] == source_row["package_key"], "PREDECESSOR_RECORD")
            raw = pdf.pages[18].crop(source_row["pdf_bbox"]).extract_text(x_tolerance=1)
            model.require(raw == source_row["pdf_three_line_card"] and len(raw.splitlines()) == 3 and
                          lines[source_row["txt_line"] - 1] == source_row["txt_literal"], "EXACT_SOURCE_CARD_AND_TXT")
            row = construct(old, source_row); verify_record(old, row, source_row)
            # Cheap menu arithmetic prevents empty/nonimplementable packets. No state/permutation campaign.
            contract = row["implementation"]["manual_execution_contract"]
            for origin in contract["source_contact_menu"]:
                choices = model.nearest_targets(origin, contract["source_pitch_events"][1]["printed_note"])
                model.require(choices and all(model.contact_midi(c) % 12 == model.PC[contract["source_pitch_events"][1]["printed_note"]]
                                              for c in choices), "DERIVED_TARGET_MENU")
            checks.append({"key": old["package_key"], "TXT_line": source_row["txt_line"], "PDF_page": 19,
                           "PDF_bbox": source_row["pdf_bbox"], "printed_pitch_count": 2,
                           "source_contacts_unchanged": True, "origin_menu_count": len(contract["source_contact_menu"]),
                           "all_origins_have_bounded_nearest_named_target": True})
    rows = [construct(old, source_row) for old, source_row in zip(old_rows, reservation["source_rows"])]
    keys = {e["package_key"] for e in entries}
    unchanged = model.digest([[e["package_key"], model.digest(effective[e["package_key"]])]
                              for e in index["children"] if e["package_key"] not in keys])
    changes = []
    for old, row in zip(old_rows, rows):
        key = row["package_key"]
        changes.append({"package_key": key, "source_identity": row["source_identity"],
                        "base_record_sha256": model.digest(old), "overlay_line": len(changes) + 1,
                        "overlay_record_sha256": model.digest(row), "old_category": categories[key],
                        "new_category": "complete_manual_nonplayback_contract"})
        effective[key], categories[key] = row, "complete_manual_nonplayback_contract"; used.add(key)
    model.require(unchanged == model.digest([[e["package_key"], model.digest(effective[e["package_key"]])]
                                           for e in index["children"] if e["package_key"] not in keys]), "OTHER_RECORDS_UNCHANGED")
    ordered = [[e["package_key"], effective[e["package_key"]]["source_identity"]] for e in index["children"]]
    model.require(model.digest(ordered) == index["ordered_identity_sha256"], "ORDERED_RANGE_IDENTITY")
    for ref in refs + [reservation["prior_overlay_handoff"], reservation["governing_corrected_prompt"]]:
        check_pin(ref)
    RES.mkdir(parents=True, exist_ok=True); OUT.mkdir(parents=True, exist_ok=True)
    packet = OUT / "implementation-overlay.jsonl"
    model.require(not packet.exists(), "OUTPUT_EXISTS")
    packet.write_text("".join(model.compact(row) + "\n" for row in rows))
    save(RES / "source-integrity.json", {
        "result": "PASS", "fresh_original_pages": [1, 19, 20], "source_refs": refs,
        "source_checks": checks, "card_count": 12, "printed_pitch_count": 24,
        "unchanged_other_rows": 2121, "unchanged_other_records_sha256": unchanged,
        "final_input_drift": 0, "derived_origin_menu_arithmetic_checks": sum(c["origin_menu_count"] for c in checks),
        "source_rule_and_safety_exact": True, "independent_QA": "NOT_RUN / QA_PENDING"})
    counts = dict(Counter(categories.values()))
    save(RES / "handoff.json", {
        "schema_version": 2, "status": "IMPLEMENTED_PRIVATE_QA_PENDING; complete12-card producer construction sealed",
        "start_utc": started, "end_utc": datetime.now(timezone.utc).isoformat(),
        "converter_seconds": round(time.monotonic() - timer, 6), "base_index": pin(old_module.BASE),
        "prior_overlay_handoff": pin(PREV), "overlay": pin(packet), "changes": changes,
        "effective_categories": counts, "effective_child_count": 2133,
        "effective_overlay_record_count": len(used), "unique_replaced_children": len(used),
        "total_replacement_operations": operations + 12, "ordered_identity_sha256": model.digest(ordered),
        "source_inputs": refs, "outside_child_ambiguities_unchanged": 6, "level57_unresolved_records_unchanged": 6,
        "attempted_keys": 12, "new_implemented_private_keys": 12, "implementation_unresolved_family_keys": 0,
        "unattempted_family_keys": 0, "printed_position_timing_unknown_keys": 12,
        "new_native_valid": 0, "new_integrated": 0, "new_independently_reviewed": 0, "new_accepted": 0,
        "agent_decision_owner": "B producer /root/private_b_mode_mirrors_resume",
        "independent_reviewer": "UNASSIGNED; required downstream",
        "deferred_QA": ["Independent source/nearest-policy interpretation", "Bulk contact/choice/workflow campaigns",
                        "Native/app integration", "Listening/physical security and musical quality", "Regression/release gates"],
        "no_next_package_dispatched": True})
    _, _, final_effective, _, final_used, final_operations = folder.fold_chain(old_module.BASE, RES / "handoff.json")
    model.require(len(final_used) == 813 and final_operations == 951 and
                  all(final_effective[row["package_key"]] == row for row in rows), "FINAL_GUARDED_CHAIN")
    save(RES / "final-fold.json", {"result": "PASS", "identities": 2133, "unique_replacements": 813,
                                  "replacement_operations": 951, "new_records": 12, "other_rows_unchanged": 2121,
                                  "ordered_identity_sha256": model.digest(ordered)})
    print(model.compact({"result": "IMPLEMENTED_PRIVATE_QA_PENDING", "packet": pin(packet), "handoff": pin(RES / "handoff.json"),
                         "new_keys": 12, "printed_pitch_count": 24, "categories": counts}))


if __name__ == "__main__":
    main()
