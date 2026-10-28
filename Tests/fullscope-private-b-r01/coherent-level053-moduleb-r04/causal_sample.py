"""Bounded causal sample; all-key construction integrity is a separate guard."""
from pathlib import Path
import copy
import hashlib
import importlib.util
import json
import sys
import time
from datetime import datetime, timezone
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
NAME = "coherent-level053-moduleb-r04"
RES = ROOT / "Results/fullscope-private-b-r01" / NAME
MODEL = ROOT / "Tools/fullscope-private-b-r01" / NAME / "triad_task_model.py"

def load(name, path):
    s = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def pin(p): return {"path": str(p.relative_to(ROOT)), "bytes": p.stat().st_size, "sha256": sha(p)}

def main():
    start = datetime.now(timezone.utc).isoformat(); timer = time.monotonic()
    m = load("triad_task_model", MODEL); family = m.Family(ROOT)
    assert sha(MODEL) == "6b9d34fa5211040527ab240fb139147bf8623ff7aeba9fd05273814830aa59ef"
    handoff = json.loads((RES / "handoff.json").read_text())
    packet = ROOT / handoff["overlay"]["path"]; rows = family.load_packet(packet, handoff["overlay"]["sha256"])
    checks = []
    def ok(name, condition):
        assert condition, name
        checks.append({"check": name, "result": "PASS"})
    def refuse(name, task, fn):
        before = task.snapshot()
        try: fn()
        except m.Refusal as e:
            ok(name, task.snapshot() == before)
            checks[-1]["code"] = str(e)
        else: raise AssertionError("ACCEPTED_REFUSAL: " + name)
    def act(t, kind, p=None): return t.apply(t.capture(kind), t.expected_payload(kind) if p is None else p)
    def ready(t): act(t, "select"); act(t, "ready")
    samples = []
    for page in range(3, 7):
        for quality, inversion in (("Maj", (page - 3) % 3), ("Min", (page - 2) % 3)):
            label = quality + " " + ["RP", "1st", "2nd"][inversion]
            key = next(k for k in family.keys if family.bindings[k]["pdf_page"] == page and family.bindings[k]["printed_components"][:2] == ["D", label])
            samples.append(key)
            t = m.Task(family, family.contract(key)); ready(t)
            first = t.capture("respond")
            for order in range(1, 5):
                ok(f"{page}.{quality}.action{order}.source_order", t.action == order)
                act(t, "respond")
            ok(f"{page}.{quality}.pending_manual_release", t.phase == "RELEASE" and t.outcome == "NONE")
            refuse(f"{page}.{quality}.retry_before_release", t, lambda: act(t, "again"))
            refuse(f"{page}.{quality}.stale_first_ack", t, lambda: t.apply(first, {}))
            act(t, "release")
            ok(f"{page}.{quality}.finished_is_unobserved_manual_report", t.outcome == "USER_REPORTED_STEPS_FINISHED" and not t.snapshot()["performance_observed"] and not t.snapshot()["grants_credit"])
            old = t.capture("reopen"); history = len(t.history); act(t, "again")
            ok(f"{page}.{quality}.new_pass_retains_history", t.generation == 2 and len(t.history) == history + 1 and t.phase == "CHOOSE")
            refuse(f"{page}.{quality}.old_pass_refused", t, lambda: t.apply(old, {}))
    key = samples[0]; c = family.contract(key)
    for name, mutation in (
        ("changed_written_contact", lambda d: d["voices_low_to_high"][0].update(fret=23)),
        ("changed_degree", lambda d: d["voices_low_to_high"][0].update(printed_degree="b3")),
        ("invent_clock", lambda d: d.update(numeric_clock=120)),
        ("forge_credit", lambda d: d.update(grants_credit=True)),
        ("foreign_key", lambda d: d.update(package_key=m.REPRESENTATIVE)),
        ("missing_setup", lambda d: d.pop("setup")),
    ):
        bad = copy.deepcopy(c); mutation(bad)
        try: family.validate(bad)
        except m.Refusal: ok("contract." + name, True)
        else: raise AssertionError("UNBOUND_CONTRACT")
    a, b = m.Task(family, c), m.Task(family, c)
    foreign = a.capture("select")
    refuse("token.cross_instance", b, lambda: b.apply(foreign, {"mode": "source_order_only"}))
    for name, mutation in (("key", lambda x: x.update(package_key=samples[-1])),
                           ("policy", lambda x: x.update(source_policy_sha256="0" * 64)),
                           ("contract", lambda x: x.update(contract_sha256="0" * 64)),
                           ("generation", lambda x: x.update(pass_generation=2)),
                           ("revision", lambda x: x.update(revision=0)),
                           ("phase", lambda x: x.update(phase="MANUAL_STEPS")),
                           ("action", lambda x: x.update(action_order=1)),
                           ("extra", lambda x: x.update(unknown=True))):
        token = a.capture("select"); mutation(token)
        refuse("token." + name, a, lambda: a.apply(token, {"mode": "source_order_only"}))
    refuse("premature.release", a, lambda: act(a, "release"))
    refuse("premature.finish", a, lambda: a.capture("finish"))
    refuse("malformed.mode", a, lambda: act(a, "select", {"mode": "even_pulse", "bpm": 90}))
    act(a, "select"); wrong = a.expected_payload("ready"); wrong["named_notes_low_to_high"][0] = "C#"
    act(a, "ready", wrong)
    ok("setup.wrong_name_diagnosed", a.phase == "RELEASE" and a.diagnosis["code"] == "SETUP_NAME_OR_MANUAL_REPORT_MISMATCH" and not a.diagnosis["observed_failure"])
    refuse("setup.retry_release_fence", a, lambda: act(a, "again"))
    refuse("setup.false_release", a, lambda: act(a, "release", {"released_completely_reported": False}))
    act(a, "release"); ok("setup.retry_closure", a.outcome == "RETRY_REQUESTED")
    act(a, "again"); ready(a)
    token = a.capture("respond"); payload = a.expected_payload("respond")
    for name, mutation in (("wrong_order", lambda p: p.update(action_order=4)),
                           ("bool_order", lambda p: p.update(action_order=True)),
                           ("missing_action", lambda p: p.pop("written_action")),
                           ("extra_bpm", lambda p: p.update(bpm=100)),
                           ("nonbool_report", lambda p: p.update(performed_action_reported=1))):
        bad = copy.deepcopy(payload); mutation(bad)
        refuse("response." + name, a, lambda: a.apply(token, bad))
    bad = copy.deepcopy(payload); bad["written_action"]["voices"][0]["printed_degree"] = "0"
    act(a, "respond", bad)
    ok("response.contact_degree_mismatch_diagnosed", a.phase == "RELEASE" and a.diagnosis["code"] == "WRITTEN_CONTACT_DEGREE_OR_MANUAL_REPORT_MISMATCH")
    act(a, "release"); act(a, "again"); ready(a)
    act(a, "respond", {"response": "unknown"})
    ok("unknown.diagnosed_retry", a.phase == "RELEASE" and a.pending == "RETRY_REQUESTED" and a.diagnosis["code"] == "MANUAL_UNKNOWN")
    act(a, "release"); act(a, "again"); ready(a)
    for _ in range(4): act(a, "respond")
    act(a, "release")
    ok("diagnosed_retry.actual_successful_manual_recovery_with_retained_lineage", a.outcome == "USER_REPORTED_STEPS_FINISHED" and len([h for h in a.history if h["diagnosis"]]) >= 3 and a.generation == 4)
    act(a, "again"); stale = a.capture("select"); act(a, "navigate")
    refuse("navigation.old_input", a, lambda: a.apply(stale, {"mode": "source_order_only"}))
    refuse("navigation.reopen_before_release", a, lambda: act(a, "reopen"))
    act(a, "release"); ok("navigation.cancelled", a.outcome == "CANCELLED")
    act(a, "reopen"); act(a, "cancel"); act(a, "release")
    ok("cancel.manual_release_completed", a.outcome == "CANCELLED")
    for raw in ('{"x":1,"x":2}', '{"x":NaN}', '{"x":Infinity}'):
        try: m.strict_json(raw)
        except m.Refusal: ok("strict_json." + raw, True)
        else: raise AssertionError("MALFORMED_JSON_ACCEPTED")
    generator = ROOT / "Tools/manager-resume-r01/typed-manual-task-core-r01/generate_representative.py"
    assert sha(generator) == "dc95949c561f93347829e152dac85c8b10d5c6dacb0a679309ff5803eb1b4a76"
    g = load("frozen_representative_generator", generator)
    try: g.validate({}, key)
    except Exception as e: ok("original_generator.sibling_scope_refusal_preserved", "REPRESENTATIVE_SCOPE" in str(e))
    else: raise AssertionError("REPRESENTATIVE_GENERATOR_SCOPE_EXPANDED")
    scope = json.loads((ROOT / "Results/fullscope-private-b-r01/remaining-backlog-resume-r04/installed-representative-scope.json").read_text())
    for ref in scope["pins"]:
        p = ROOT / ref["path"]
        ok("preserved_representative." + ref["path"], pin(p) == {k: ref[k] for k in ("path", "bytes", "sha256")})
    output = RES / "causal-sample-checks.json"
    assert not output.exists()
    result = {"result": "PASS", "start_utc": start, "end_utc": datetime.now(timezone.utc).isoformat(),
              "seconds": round(time.monotonic() - timer, 6), "model": pin(MODEL), "packet": pin(packet),
              "small_causal_sample_keys": samples, "sample_keys": 8, "check_count": len(checks), "checks": checks,
              "all_key_integrity": pin(RES / "source-and-integrity-checks.json"),
              "sample_limit": "Eight diverse key workflows plus targeted owner/diagnosis/release/refusal cases; not exhaustive state/permutation or independent QA.",
              "broad_qa": "DEFERRED to /root/private_source_bulk_review", "independent_accepts": 0, "official_child_accepts": 0}
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"result": "PASS", "checks": len(checks), "sample_keys": 8, "seconds": result["seconds"], "evidence": pin(output)}))

if __name__ == "__main__": main()
