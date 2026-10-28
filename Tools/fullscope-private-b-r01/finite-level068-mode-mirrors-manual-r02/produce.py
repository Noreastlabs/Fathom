"""Close old ModuleA by reference; construct only new ModuleI pending records.

Run with the existing bundled Python, PYTHONDONTWRITEBYTECODE=1. This calls
the pinned historical folder and constructors, never their exhaustive main().
"""
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
import call_answer_model as model

ROOT = Path(__file__).resolve().parents[3]
NAME = "finite-level068-mode-mirrors-manual-r02"
RES = ROOT / "Results/fullscope-private-b-r01" / NAME
OUT = ROOT / "Build/fullscope-private-b-r01" / NAME
PROMPT = ROOT / "Prompts/fullscope-private-b-r01" / NAME
HIST = ROOT / "Results/fullscope-private-b-r01/finite-level068-mode-mirrors-manual-r01"
HIST_CODE = ROOT / "Tools/fullscope-private-b-r01/finite_level068_mode_mirrors_manual_r01.py"
HIST_CODE_SHA = "336b170b275d476ca02b689bf32fa02d8334622b5ad6c64fd3c78e7fcc9a8a02"
HIST_HANDOFF_SHA = "3eecedbf87ca6c4c5051c069207dc48d8c340b8c09c927063910d27ffd9e1f65"
HIST_SEAL_SHA = "154af36b0c5997fe88f63134596c540ff4cc750f2a2c7f2916db233f7d0766ae"
HIST_PACKET_SHA = "1224c8749330875cb597c5bb4377b6f3a00793108d0dd42766263357386dbe49"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pin(path):
    return {"path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size,
            "sha256": sha(path)}


def save(path, value):
    model.require(not path.exists(), "OUTPUT_EXISTS: " + str(path))
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def guard_pin(reference):
    model.require(pin(ROOT / reference["path"]) ==
                  {k: reference[k] for k in ["path", "bytes", "sha256"]}, "INPUT_DRIFT")


def import_file(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check_grid(grid, events, width, roles):
    # R is a sounded root where relevant; no rest/timing inferred from role rows.
    model.require(all(len(value) == len(events) * width for value in grid.values()), "GRID_WIDTH")
    strings = {"e": 1, "B": 2, "G": 3, "D": 4, "A": 5, "E": 6}
    for i, event in enumerate(events):
        values = {s: text[i * width:(i + 1) * width].strip("-") for s, text in grid.items()}
        contacts = [(strings[s], int(value)) for s, value in values.items() if s in strings and value]
        model.require(contacts == [(event["string"], event["fret"])] and
                      values["Nte"] == event["printed_note"] and
                      values["Deg"] == event["degree"] and values["Rol"] == roles[i], "GRID_EVENT")


def txt_segment(lines, label, lo, hi):
    hits = [i for i in range(lo, hi) if lines[i] == label]
    model.require(len(hits) == 1, "EXACT_TXT_LABEL")
    n = hits[0]
    end = next(i for i in range(n + 1, hi) if not lines[i].strip())
    return {"line_start": n + 1, "line_end": end, "label": label}, "\n".join(lines[n:end])


def construct(old, segments, contract_source_refs):
    new = copy.deepcopy(old)
    for i, event in enumerate(new["implementation"]["events"]):
        event["role"] = model.ROLES[i]
    new["source_refs"][0]["locator"] = {"module": "I", "segments": [x[0] for x in segments]}
    new["source_payload"]["txt_excerpt"] = "\n\n".join(x[1] for x in segments)
    new["source_payload"]["source_discrepancy"] = [{
        "class": "paired_pdf_separate_txt_semantics_reconciled",
        "previous_diagnostic": old["source_payload"].get("source_discrepancy"),
        "resolution": "PDF15 pairs16 contacts in3-column cells; TXT has CALL/ANSWER8 each in4-column cells. Notes/degrees/contacts agree. PDF CAL/ANS/>A fixed-width role cells are segmented per contact; prior first-event merged role is corrected.",
        "source_interpretation": "producer provisional; independent review pending",
        "TXT": new["source_refs"][0]["locator"],
    }]
    new["implementation"]["source_scope"]["locator"]["supplemental_txt_locator"] = copy.deepcopy(new["source_refs"][0]["locator"])
    new["implementation"]["kind"] = "manual_minor_call_dominant_answer_and_two_beat_silence"
    new["implementation"]["manual_execution_contract"] = model.make_contract(
        new["package_key"], new["source_identity"], new["implementation"]["events"], contract_source_refs)
    new["provenance"]["conversion"] = str(Path(__file__).relative_to(ROOT))
    new["provenance"]["producer_role"] = "B resumed private implementation producer; independent review pending"
    new["provenance"]["qa_disposition"] = "QA_PENDING"
    new["status"] = "IMPLEMENTED_PRIVATE_QA_PENDING"
    return new


def verify_record(old, new, segments, refs):
    model.require(model.compact(new) == model.compact(construct(old, segments, refs)),
                  "EXACT_SOURCE_BOUND_RECORD")


def main():
    started = datetime.now(timezone.utc).isoformat()
    timer = time.monotonic()
    model.require(not (RES / "handoff.json").exists(), "OUTPUT_EXISTS")
    model.require(sha(HIST_CODE) == HIST_CODE_SHA and
                  sha(HIST / "handoff.json") == HIST_HANDOFF_SHA and
                  sha(HIST / "targeted-validation.json") == HIST_SEAL_SHA, "HISTORICAL_PIN")
    old_module = import_file(HIST_CODE, "historical_modes")
    hist = json.loads((HIST / "handoff.json").read_text())
    model.require(hist["overlay"]["sha256"] == HIST_PACKET_SHA, "HISTORICAL_PACKET_IDENTITY")
    guard_pin(hist["overlay"])
    prior_refs = [pin(HIST_CODE), pin(HIST / "handoff.json"), pin(HIST / "targeted-validation.json"), hist["overlay"]]
    for path, expected in old_module.PINS:
        model.require(sha(path) == expected, "ORIGINAL_DEPENDENCY_PIN")
    folder = old_module.module(old_module.FOLD, "guarded_folder")
    index, prior, effective, categories, used, operations = folder.fold_chain(old_module.BASE, HIST / "handoff.json")
    model.require(len(effective) == 2133 and len(used) == 796 and operations == 934, "PRIOR_FOLD_COUNTS")
    entries = [e for e in index["children"] if e["level"] == 68 and 43 <= e["line"] <= 47]
    reserved = json.loads((PROMPT / "modulei-exact-key-reservation.json").read_text())
    identity = [[e["package_key"], e["source_identity"]] for e in entries]
    model.require(identity == reserved["keys"] and model.digest(identity) == reserved["ordered_family_identity_sha256"], "FAMILY_KEY_CUSTODY")
    model.require(len(entries) == 5 and all(categories[e["package_key"]] == "implementation_or_interpretation_pending"
                  and e["package_key"] not in used for e in entries), "GENUINELY_PENDING_FAMILY")
    old_rows = [effective[e["package_key"]] for e in entries]
    refs = old_rows[0]["source_refs"]
    for ref in refs:
        guard_pin(ref)
    lines = (ROOT / refs[0]["path"]).read_text().splitlines()
    context = json.loads((ROOT / refs[2]["path"]).read_text())
    contexts = {p["physical_page"]: p["text"] for p in context["pdf_pages"]}
    lo = next(i for i, line in enumerate(lines) if line.startswith("MODULE I -"))
    hi = next(i for i, line in enumerate(lines) if line.startswith("MODULE J -"))
    data, source_checks, closure_checks = [], [], []
    # Fresh original text/card evidence only, not independent visual/semantic acceptance.
    with pdfplumber.open(ROOT / refs[1]["path"]) as pdf:
        model.require(len(pdf.pages) == 20, "ORIGINAL_PAGE_COUNT")
        for page in [1, 2, 3, 4, 15, 20]:
            raw = pdf.pages[page - 1].extract_text(x_tolerance=1)
            model.require(old_module.norm(raw) == old_module.norm(contexts[page]), "CONTEXT_DRIFT")
        model.require(model.CONTEXT in old_module.norm(contexts[15]) and model.VARIATION in old_module.norm(contexts[15])
                      and model.SAFETY in old_module.norm(contexts[1]), "EXACT_SOURCE_DUTY")
        for row in [effective[e["package_key"]] for e in index["children"] if e["level"] == 68 and 2 <= e["line"] <= 6]:
            scope = row["implementation"]["source_scope"]
            page = scope["locator"]["physical_page"]
            raw = pdf.pages[page - 1].crop(scope["locator"]["derived_bbox"]).extract_text(x_tolerance=1)
            model.require(raw == scope["pdf_excerpt"], "HISTORICAL_SOURCE_CARD")
            ev = row["implementation"]["events"]
            check_grid(old_module.b.grid(raw), ev, 4, old_module.ROLES)
            txt_loc = row["source_refs"][0]["locator"]
            literal = "\n".join(lines[txt_loc["line_start"] - 1:txt_loc["line_end"]])
            model.require(literal == row["source_payload"]["txt_excerpt"], "HISTORICAL_TXT_CARD")
            closure_checks.append({"key": row["package_key"], "printed_contacts": len(ev), "PDF_page": page, "source_card_pass": True})
        for j, old in enumerate(old_rows, 1):
            scope = old["implementation"]["source_scope"]
            model.require(scope["locator"]["physical_page"] == 15, "WRONG_SOURCE_PAGE")
            raw = pdf.pages[14].crop(scope["locator"]["derived_bbox"]).extract_text(x_tolerance=1)
            model.require(raw == scope["pdf_excerpt"], "EXACT_PDF_CARD")
            segments = [txt_segment(lines, "P" + str(j) + " " + duty, lo, hi) for duty in ["CALL", "ANSWER"]]
            fixed = copy.deepcopy(old["implementation"]["events"])
            for i, event in enumerate(fixed):
                event["role"] = model.ROLES[i]
            model.check_events(fixed)
            check_grid(old_module.b.grid(raw), fixed, 3, model.ROLES)
            check_grid(old_module.b.grid(segments[0][1]), fixed[:8], 4, ["CALL"] * 8)
            check_grid(old_module.b.grid(segments[1][1]), fixed[8:], 4, ["ANS"] * 7 + [">A"])
            source_refs = [{**{k: ref[k] for k in ["path", "bytes", "sha256"]},
                            "physical_pages": pages} for ref, pages in [(refs[1], [1, 15, 20])]]
            data.append((segments, source_refs))
            source_checks.append({"key": old["package_key"], "TXT": [x[0] for x in segments], "PDF_page": 15,
                                  "PDF_bbox": scope["locator"]["derived_bbox"], "contacts_checked": 16,
                                  "TXT_PDF_note_degree_contact_equivalence": True, "fixed_width_PDF_roles": model.ROLES})
    rows = [construct(old, *d) for old, d in zip(old_rows, data)]
    for old, row, d in zip(old_rows, rows, data):
        verify_record(old, row, *d)
    keys = {e["package_key"] for e in entries}
    other_before = model.digest([[e["package_key"], model.digest(effective[e["package_key"]])]
                                 for e in index["children"] if e["package_key"] not in keys])
    changes = []
    for old, row in zip(old_rows, rows):
        key = row["package_key"]
        changes.append({"package_key": key, "source_identity": row["source_identity"],
                        "base_record_sha256": model.digest(old), "overlay_line": len(changes) + 1,
                        "overlay_record_sha256": model.digest(row), "old_category": categories[key],
                        "new_category": "complete_manual_nonplayback_contract"})
        effective[key], categories[key] = row, "complete_manual_nonplayback_contract"
        used.add(key)
    other_after = model.digest([[e["package_key"], model.digest(effective[e["package_key"]])]
                                for e in index["children"] if e["package_key"] not in keys])
    ordered = [[e["package_key"], effective[e["package_key"]]["source_identity"]] for e in index["children"]]
    model.require(other_before == other_after and model.digest(ordered) == index["ordered_identity_sha256"], "OTHER_ROWS_AND_IDENTITIES")
    for ref in refs + prior_refs:
        guard_pin(ref)
    RES.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    packet = OUT / "implementation-overlay.jsonl"
    model.require(not packet.exists(), "OUTPUT_EXISTS")
    packet.write_text("".join(model.compact(row) + "\n" for row in rows))
    save(RES / "source-integrity.json", {
        "result": "PASS", "fresh_original_pages": [1, 2, 3, 4, 15, 20], "source_refs": refs,
        "historical_ModuleA_closure_checks": closure_checks, "historical_reused_code": pin(HIST_CODE),
        "historical_implementation_delta": 0, "new_ModuleI_source_checks": source_checks,
        "new_printed_contacts": 80, "additional_variation_replay_contacts": 80,
        "unchanged_other_rows": 2128, "unchanged_other_records_sha256": other_before,
        "final_input_drift": 0, "exhaustive_historical_campaign_rerun": False,
        "independent_source_review": "NOT_RUN / QA_PENDING", "visual_layout_review": "NOT_RUN / QA_PENDING"})
    save(RES / "historical-modulea-closeout.json", {
        "result": "Historical construction and producer seal verified; narrative gap closed by reference",
        "original_start_utc": hist["start_utc"], "original_seal_utc": hist["end_utc"],
        "original_handoff": pin(HIST / "handoff.json"), "original_packet": hist["overlay"],
        "original_producer_seal": pin(HIST / "targeted-validation.json"), "original_model": pin(HIST_CODE),
        "newly_implemented_keys": 0, "already_implemented_keys": 5, "fresh_source_cards": 5,
        "independent_reviewed": 0, "native_valid": 0, "integrated": 0, "accepted": 0,
        "disposition": "IMPLEMENTED_PRIVATE_QA_PENDING; original bytes preserved"})
    categories = dict(Counter(categories.values()))
    save(RES / "handoff.json", {
        "schema_version": 2, "status": "IMPLEMENTED_PRIVATE_QA_PENDING; bounded producer construction sealed",
        "start_utc": started, "end_utc": datetime.now(timezone.utc).isoformat(),
        "converter_seconds": round(time.monotonic() - timer, 3),
        "base_index": pin(old_module.BASE), "prior_overlay_handoff": pin(HIST / "handoff.json"),
        "overlay": pin(packet), "changes": changes, "effective_categories": categories,
        "effective_child_count": 2133, "effective_overlay_record_count": len(used),
        "unique_replaced_children": len(used), "total_replacement_operations": operations + len(rows),
        "ordered_identity_sha256": model.digest(ordered), "source_inputs": refs,
        "outside_child_ambiguities_unchanged": 6, "level57_unresolved_records_unchanged": 6,
        "attempted_keys": 5, "new_implemented_private_keys": 5, "unresolved_family_keys": 0,
        "unattempted_family_keys": 0, "historical_ModuleA_implemented_delta": 0,
        "new_native_valid": 0, "new_integrated": 0, "new_independently_reviewed": 0, "new_accepted": 0,
        "agent_decision_owner": "B producer /root/private_b_mode_mirrors_resume",
        "independent_reviewer": "UNASSIGNED; required before source/behavior acceptance",
        "deferred_QA": ["Independent source/semantic review", "Bulk workflow/choice campaigns", "Native validation",
                        "App/TAB/audio/fretboard integration", "Listening and physical performance", "Regression and release gates"]})
    # Replay the actual retained packet through the same frozen guarded chain.
    _, _, replayed, _, replay_used, replay_ops = folder.fold_chain(old_module.BASE, RES / "handoff.json")
    model.require(len(replay_used) == 801 and replay_ops == 939 and
                  all(replayed[row["package_key"]] == row for row in rows), "FINAL_CHAIN_REPLAY")
    save(RES / "final-fold.json", {"result": "PASS", "identities": 2133, "unique_replacements": 801,
                                  "replacement_operations": 939, "new_family_records": 5,
                                  "ordered_identity_sha256": model.digest(ordered), "other_rows_unchanged": 2128})
    print(model.compact({"result": "IMPLEMENTED_PRIVATE_QA_PENDING", "handoff": pin(RES / "handoff.json"),
                         "packet": pin(packet), "new_keys": 5, "historical_key_delta": 0, "categories": categories}))


if __name__ == "__main__":
    main()
