"""Bounded producer guard sample; intentionally no exhaustive state campaign."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import copy
import importlib.util
import json
import sys
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
NAME = "finite-level068-mode-mirrors-manual-r02"
sys.path.insert(0, str(ROOT / "Tools/fullscope-private-b-r01" / NAME))
import call_answer_model as m
import produce as producer


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="cheap-validation.json")
    args = parser.parse_args()
    timer = time.monotonic()
    started = datetime.now(timezone.utc).isoformat()
    res = ROOT / "Results/fullscope-private-b-r01" / NAME
    handoff = json.loads((res / "handoff.json").read_text())
    rows = m.load_packet(ROOT / handoff["overlay"]["path"], handoff["overlay"]["sha256"])
    positives, workflows, refusals, contents, source_refusals = [], [], [], [], []
    for row in rows:
        contract = row["implementation"]["manual_execution_contract"]
        for start in ["D", "U"]:
            request = {"package_key": row["package_key"], "contract_sha256": m.digest(contract), "start_stroke": start}
            plan = m.selection(contract, request)
            m.require(len(plan["paired"]) == 16 and len(plan["variation_call"]) == len(plan["variation_answer"]) == 8,
                      "PLAN_CONTACT_COUNTS")
            m.require([e["order"] for e in plan["variation_call"] + plan["variation_answer"]] == list(range(1, 17)),
                      "PLAN_SOURCE_ORDER")
            m.require([e["selected_pick"] for e in plan["paired"]] == list(("DU" if start == "D" else "UD") * 8),
                      "CHOSEN_PICK_ALTERNATION")
            m.require(plan["variation_answer"][-1]["printed_note"] == "A" and plan["silent_gap"]["source_beats"] == 2
                      and plan["silent_gap"]["duration_q"] is None and plan["grants_credit"] is False, "GAP_FINAL_A_NO_CREDIT")
            positives.append({"key": row["package_key"], "start": start, "plan_sha256": m.digest(plan)})
        request["start_stroke"] = "D"
        state = m.workflow_state(contract, request, m.done_responses())
        m.require(state["state"] == "USER_REPORTED_STEPS_FINISHED" and state["performance_observed"] is False
                  and state["grants_credit"] is False, "MANUAL_COMPLETION_ONLY")
        workflows.append({"key": row["package_key"], "state": state["state"]})
    c = rows[0]["implementation"]["manual_execution_contract"]
    r = {"package_key": c["package_key"], "contract_sha256": m.digest(c), "start_stroke": "D"}
    done = m.done_responses()
    false_report = copy.deepcopy(done[:1]); false_report[0]["prepared_safely_reported"] = False
    m.require(m.workflow_state(c, r, false_report)["state"] == "NEEDS_RETRY", "FALSE_REPORT_RETRY")
    m.require(m.workflow_state(c, r, [{"step": 1, "response": "stopped"}])["state"] == "STOPPED", "STOP_NOW")
    m.require(m.workflow_state(c, None, [])["state"] == "AWAITING_SELECTION", "AWAITING_EXPLICIT_CHOICE")
    workflows.extend([{"representative_state": state} for state in ["NEEDS_RETRY", "STOPPED", "AWAITING_SELECTION"]])
    bool_beat = copy.deepcopy(done); bool_beat[3]["silent_source_beats"] = True
    wrong_beat = copy.deepcopy(done); wrong_beat[3]["silent_source_beats"] = 3
    nonbool = copy.deepcopy(done[:1]); nonbool[0]["prepared_safely_reported"] = 1
    controls = [
        ("wrong_key", dict(r, package_key="other"), []),
        ("stale_contract", dict(r, contract_sha256="0" * 64), []),
        ("invented_clock", dict(r, bpm=120), []),
        ("bool_start", dict(r, start_stroke=True), []),
        ("unavailable_start", dict(r, start_stroke="X"), []),
        ("missing_explicit_choice", {k: v for k, v in r.items() if k != "start_stroke"}, []),
        ("bool_gap_count", r, bool_beat), ("wrong_gap_count", r, wrong_beat),
        ("nonboolean_report", r, nonbool),
        ("answers_before_choice", None, done[:1]),
        ("skip_silence_step", r, done[:3] + done[4:]),
        ("after_stop", r, [{"step": 1, "response": "stopped"}, done[1]]),
        ("after_failed_report", r, false_report + done[1:2]),
        ("terminal_extra_fields", r, [{"step": 1, "response": "stopped", "credit": True}]),
    ]
    for reason, request, responses in controls:
        try:
            m.workflow_state(c, request, responses)
        except m.Refusal as error:
            refusals.append({"control": reason, "refusal": str(error)})
        else:
            raise AssertionError("CONTROL_ACCEPTED " + reason)
    mutations = [
        ("deleted_core_contact", lambda x: x["ordered_contacts"].pop(8)),
        ("wrong_pitch", lambda x: x["ordered_contacts"][0].update(printed_note="B")),
        ("bool_fret", lambda x: x["ordered_contacts"][0].update(fret=True)),
        ("invented_source_duration", lambda x: x["ordered_contacts"][0].update(duration_q=[1, 4])),
        ("hidden_source_tempo", lambda x: x["ordered_contacts"][0].update(bpm=120)),
        ("merged_role", lambda x: x["ordered_contacts"][0].update(role="CALCALCAL")),
        ("wrong_original_source", lambda x: x["source_refs"][0].update(sha256="0" * 64)),
        ("wrong_source_page", lambda x: x["source_refs"][0].update(physical_pages=[1, 14, 20])),
        ("extra_final_A_attack", lambda x: x["steps"][4].update(additional_final_A_attack=True)),
        ("forged_quarter_gap", lambda x: x["steps"][3]["gap"].update(duration_q=[2, 1])),
        ("fabricated_credit", lambda x: x.update(grants_credit=True)),
        ("fabricated_observation", lambda x: x.update(performance_observed=True)),
        ("missing_variation", lambda x: x["steps"].pop(3)),
    ]
    for reason, mutate in mutations:
        bad = copy.deepcopy(c); mutate(bad)
        try:
            m.validate_contract(bad)
        except m.Refusal as error:
            contents.append({"control": reason, "refusal": str(error)})
        else:
            raise AssertionError("CONTENT_ACCEPTED " + reason)
    # Small causal malformed-source grid sample; full semantic review is deferred.
    spec = importlib.util.spec_from_file_location("old", producer.HIST_CODE)
    old_module = importlib.util.module_from_spec(spec); spec.loader.exec_module(old_module)
    grid = old_module.b.grid(rows[0]["implementation"]["source_scope"]["pdf_excerpt"])
    for label, mutate in [("missing_source_cell", lambda g: g.update(Nte=g["Nte"][:-3])),
                          ("wrong_source_note", lambda g: g.update(Nte="B" + g["Nte"][1:]))]:
        bad = copy.deepcopy(grid); mutate(bad)
        try:
            producer.check_grid(bad, c["ordered_contacts"], 3, m.ROLES)
        except m.Refusal as error:
            source_refusals.append({"control": label, "refusal": str(error)})
        else:
            raise AssertionError("SOURCE_ACCEPTED " + label)
    try:
        m.load_packet(ROOT / handoff["overlay"]["path"], "0" * 64)
    except m.Refusal:
        source_refusals.append({"control": "wrong_packet_hash", "refusal": "PACKET_HASH"})
    else:
        raise AssertionError("PACKET_DRIFT_ACCEPTED")
    counts = {"positive_selection_plans": len(positives), "workflow_state_samples": len(workflows),
              "request_response_refusals": len(refusals), "content_source_schema_refusals": len(contents),
              "malformed_source_or_packet_refusals": len(source_refusals)}
    result = {"result": "PASS", "start_utc": started, "end_utc": datetime.now(timezone.utc).isoformat(),
              "elapsed_seconds": round(time.monotonic() - timer, 6), "counts": counts,
              "positive_plans": positives, "workflow_samples": workflows,
              "request_response_refusals": refusals, "content_refusals": contents,
              "source_refusals": source_refusals, "packet": handoff["overlay"],
              "scope": "Producer sample only; no independent or exhaustive state QA",
              "bulk_independent_native_app_listening_regression_QA": "NOT_RUN / QA_PENDING"}
    output = res / args.output
    m.require(output.parent == res and output.suffix == ".json", "RESULT_OUTPUT_SCOPE")
    producer.save(output, result)
    print(m.compact({"result": "PASS", "counts": counts, "elapsed_seconds": result["elapsed_seconds"]}))


if __name__ == "__main__":
    main()
