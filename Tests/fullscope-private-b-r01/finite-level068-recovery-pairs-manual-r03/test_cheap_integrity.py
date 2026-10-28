"""Bounded necessary choice/provenance/refusal sample, not exhaustive QA."""
from pathlib import Path
from datetime import datetime, timezone
import copy
import json
import sys
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
NAME = "finite-level068-recovery-pairs-manual-r03"
sys.path.insert(0, str(ROOT / "Tools/fullscope-private-b-r01" / NAME))
import recovery_pair_model as m
import produce as producer


def request_for(contract, start):
    origin = contract["source_contact_menu"][0]
    destination = contract["source_pitch_events"][1]["printed_note"]
    target = m.nearest_targets(origin, destination)[0]
    return {"package_key": contract["package_key"], "contract_sha256": m.digest(contract),
            "source_contact": copy.deepcopy(origin), "target_contact": copy.deepcopy(target),
            "start_stroke": start, "rest_of_bar_plan": "Simplify my existing bar while preserving its pulse; manual performer plan."}


def main():
    timer = time.monotonic(); started = datetime.now(timezone.utc).isoformat()
    res = ROOT / "Results/fullscope-private-b-r01" / NAME
    handoff = json.loads((res / "handoff.json").read_text())
    rows = m.load_packet(ROOT / handoff["overlay"]["path"], handoff["overlay"]["sha256"])
    positives, workflows, refusals, contents, source_refusals = [], [], [], [], []
    for row in rows:
        c = row["implementation"]["manual_execution_contract"]
        for start in ["D", "U"]:
            r = request_for(c, start); plan = m.selection(c, r)
            m.require(len(plan["chosen_pair"]) == 2 and [e["source_event_order"] for e in plan["chosen_pair"]] == [1, 2]
                      and [e["required_source_pitch"] for e in plan["chosen_pair"]] == [e["printed_note"] for e in c["source_pitch_events"]],
                      "PRINTED_PAIR_ORDER")
            m.require([e["selected_pick"] for e in plan["chosen_pair"]] == list("DU" if start == "D" else "UD")
                      and all(e["onset_q"] is None and e["duration_q"] is None for e in plan["chosen_pair"]), "PICKS_NOT_CLOCKS")
            m.require(all(e["string"] is None and e["fret"] is None for e in row["implementation"]["events"])
                      and plan["remainder_notes_or_attacks_generated"] is False and plan["grants_credit"] is False, "NO_FORGED_PRINTED_POSITION")
            positives.append({"key": row["package_key"], "start": start, "selection_sha256": m.digest(plan),
                              "chosen_source": r["source_contact"], "chosen_target": r["target_contact"]})
        state = m.workflow_state(c, r, m.done_responses(c, r))
        m.require(state["state"] == "USER_REPORTED_STEPS_FINISHED" and state["performance_observed"] is False
                  and state["grants_credit"] is False, "UNOBSERVED_MANUAL_COMPLETION")
        workflows.append({"key": row["package_key"], "state": state["state"]})
    c = rows[0]["implementation"]["manual_execution_contract"]; r = request_for(c, "D"); done = m.done_responses(c, r)
    false_report = copy.deepcopy(done[:1]); false_report[0]["chosen_contacts_safe_and_secure_reported"] = False
    for request, responses, expected in [(None, [], "AWAITING_SELECTION"),
                                         (r, false_report, "NEEDS_RETRY"),
                                         (r, [{"step": 1, "response": "stopped"}], "STOPPED")]:
        m.require(m.workflow_state(c, request, responses)["state"] == expected, "BOUNDARY_STATE")
        workflows.append({"representative_state": expected})
    bool_fret = copy.deepcopy(r); bool_fret["source_contact"]["fret"] = True
    wrong_target = copy.deepcopy(r); wrong_target["target_contact"] = {"string": 1, "fret": 1}
    farther_target = copy.deepcopy(r); farther_target["target_contact"] = {"string": 1, "fret": 12}
    wrong_origin = copy.deepcopy(r); wrong_origin["source_contact"] = {"string": 1, "fret": 0}
    false_timing = copy.deepcopy(r); false_timing["target_contact"]["duration_q"] = [1, 4]
    nonbool = copy.deepcopy(done[:1]); nonbool[0]["target_named_before_origin_reported"] = 1
    changed_plan = copy.deepcopy(done); changed_plan[3]["rest_of_bar_plan"] = "Different plan"
    controls = [
        ("wrong_key", dict(r, package_key="other"), []),
        ("stale_contract", dict(r, contract_sha256="0" * 64), []),
        ("invented_tempo", dict(r, bpm=90), []),
        ("bool_source_fret", bool_fret, []), ("wrong_source_pitch", wrong_origin, []),
        ("wrong_target_pitch", wrong_target, []), ("farther_target_octave", farther_target, []),
        ("forged_selected_clock", false_timing, []),
        ("empty_remainder_plan", dict(r, rest_of_bar_plan=" "), []),
        ("missing_target_choice", {k: v for k, v in r.items() if k != "target_contact"}, []),
        ("invalid_start", dict(r, start_stroke=True), []),
        ("nonboolean_declaration", r, nonbool), ("different_remainder_report", r, changed_plan),
        ("responses_before_selection", None, done[:1]),
        ("skip_target", r, done[:2] + done[3:]),
        ("after_false_security", r, false_report + done[1:2]),
        ("after_stop", r, [{"step": 1, "response": "stopped"}, done[1]]),
        ("terminal_extra_fields", r, [{"step": 1, "response": "stopped", "safe": True}]),
    ]
    for label, request, responses in controls:
        try:
            m.workflow_state(c, request, responses)
        except m.Refusal as error:
            refusals.append({"control": label, "refusal": str(error)})
        else:
            raise AssertionError("CONTROL_ACCEPTED " + label)
    mutations = [
        ("wrong_source_pitch", lambda x: x["source_pitch_events"][0].update(printed_note="G")),
        ("deleted_target", lambda x: x["source_pitch_events"].pop()),
        ("forged_printed_position", lambda x: x["source_pitch_events"][0].update(string=1, fret=1)),
        ("forged_source_clock", lambda x: x["source_pitch_events"][0].update(onset_q=[0, 1])),
        ("hidden_source_tempo", lambda x: x["source_pitch_events"][0].update(bpm=90)),
        ("wrong_source_page", lambda x: x["source_reference"].update(physical_pages=[1, 18, 20])),
        ("wrong_source_digest", lambda x: x["source_reference"].update(sha256="0" * 64)),
        ("false_fixed_provenance", lambda x: x["selection_policy"].update(printed_fixed_octave_string_fret=[1, 1])),
        ("physical_certification", lambda x: x["selection_policy"].update(physical_security="automatically certified")),
        ("omitted_bar_simplification", lambda x: x["steps"].pop(3)),
        ("automatic_credit", lambda x: x.update(grants_credit=True)),
        ("fabricated_performance", lambda x: x.update(performance_observed=True)),
    ]
    for label, mutate in mutations:
        bad = copy.deepcopy(c); mutate(bad)
        try:
            m.validate_contract(bad)
        except m.Refusal as error:
            contents.append({"control": label, "refusal": str(error)})
        else:
            raise AssertionError("CONTENT_ACCEPTED " + label)
    # Causal producer source-bound record sample against exact immutable base row.
    reservation = json.loads((ROOT / "Prompts/fullscope-private-b-r01" / NAME / "exact-key-reservation.json").read_text())
    source_row = reservation["source_rows"][0]
    base_packet = ROOT / "Build/fullscope-private-b-r01/level068-r02/implementation.jsonl"
    old = json.loads(base_packet.read_text().splitlines()[49])
    m.require(m.digest(old) == source_row["previous_effective_record_sha256"], "EXACT_BASE_ROW")
    producer.verify_record(old, rows[0], source_row)
    for label, mutate in [("source_card_missing_pitch", lambda x: x.update(pdf_three_line_card="E7: F ->\nb9 -> root\n2 tones")),
                          ("adjacent_ear_text_as_card", lambda x: x.update(pdf_three_line_card=x["pdf_three_line_card"] + "\nEar tests")),
                          ("wrong_source_key", lambda x: x.update(package_key="other")),
                          ("wrong_original_card_page", lambda x: x.update(pdf_page=18))]:
        bad = copy.deepcopy(source_row); mutate(bad)
        try:
            producer.construct(old, bad)
        except m.Refusal as error:
            source_refusals.append({"control": label, "refusal": str(error)})
        else:
            raise AssertionError("SOURCE_ACCEPTED " + label)
    try:
        m.load_packet(ROOT / handoff["overlay"]["path"], "0" * 64)
    except m.Refusal:
        source_refusals.append({"control": "packet_hash_drift", "refusal": "PACKET_HASH"})
    else:
        raise AssertionError("PACKET_DRIFT_ACCEPTED")
    borrowed = rows[2]["implementation"]["manual_execution_contract"]
    m.require(borrowed["chord_context"] == "E7" and borrowed["borrowed_G_natural_scope"] is not None,
              "BORROWED_G_CONTEXT")
    counts = {"positive_selection_plans": len(positives), "workflow_state_samples": len(workflows),
              "request_response_refusals": len(refusals), "content_schema_refusals": len(contents),
              "malformed_source_packet_refusals": len(source_refusals), "borrowed_G_scope_checks": 1}
    result = {"result": "PASS", "start_utc": started, "end_utc": datetime.now(timezone.utc).isoformat(),
              "elapsed_seconds": round(time.monotonic() - timer, 6), "counts": counts,
              "positive_plans": positives, "workflow_samples": workflows, "request_response_refusals": refusals,
              "content_refusals": contents, "source_refusals": source_refusals, "packet": handoff["overlay"],
              "scope": "Producer necessary guard sample only; no state/permutation campaign or independent QA",
              "independent_native_app_listening_bulk_regression": "NOT_RUN / QA_PENDING"}
    producer.save(res / "cheap-validation.json", result)
    print(m.compact({"result": "PASS", "counts": counts, "elapsed_seconds": result["elapsed_seconds"]}))


if __name__ == "__main__":
    main()
