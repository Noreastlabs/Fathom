"""Source-bound sibling triad tasks, source order only, no app/audio/credit.

The reviewed representative remains excluded. Four written actions are manual
reports, never observed playing. Ephemeral tokens are capabilities within one
serialized in-memory task; they are not allocated curriculum identities.
"""
from __future__ import annotations

import copy
import hashlib
import itertools
import json
from pathlib import Path
import re
import threading

SCHEMA = "fathom.private.l053-triad-source-order.v1"
PREFIX = "exercise-completeness-r01/level053/moduleb/"
REPRESENTATIVE = PREFIX + "p003-t1-r1-c2/cmajrp"
POLICY = "Build/manager-resume-r01/level053-moduleb-realization-policy-r01/policy-proposal-r02.json"
BINDINGS = "Build/manager-resume-r01/level053-moduleb-realization-policy-r01/eligible-bindings.jsonl"
PACKET = "Build/fullscope-private-b-r01/level053-r02/implementation.jsonl"
CONTEXT = "Build/fullscope-private-b-r01/level053-r02/source-context.json"
TXT = ("Notes/music/guitar project/TXT version/Guitar_Exercises_Section_VI_Level_53_"
       "Major_and_Minor_Triads_Across_Four_Adjacent_Three_String_Sets.txt")
PDF = TXT.replace("TXT version", "PDF version").replace(".txt", ".pdf")
PINS = {
    POLICY: "5ca30eef84e88134336e01ec7ee6b23d81b531125c76a62023c0b2f8005af63b",
    BINDINGS: "e5a959e7e4a25d4f3a234a8e61c3065f06ffffe7babcb46d1bf9c0ec8161d5d7",
    PACKET: "2c6648fe908f62ce0096c8b2635e154be93c9547e27a1ebcd3db9ad0dc2e0c69",
    CONTEXT: "9a9bce017bec387abe1cacd0e93f3c7fa9c9482707c6db8d16dd41470c55ee0f",
    TXT: "eeedc261db89d3421fafc116e7352bbf8a3e3f6b7eddfd822ed6e4c731e0538e",
    PDF: "5e016f98623dc4362b2e3fc9b2d1cf1fb6c8692d6312d5b30a65234d47fa20ae",
}
TUNING = {1: 64, 2: 59, 3: 55, 4: 50, 5: 45, 6: 40}
ROOTS = ["C", "D", "E", "F", "G", "A", "B"]
QUALITIES = ["Maj RP", "Maj 1st", "Maj 2nd", "Min RP", "Min 1st", "Min 2nd"]
PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
_instances = itertools.count(1)


class Refusal(ValueError):
    pass


def require(condition, code):
    if not condition:
        raise Refusal(code)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def strict_json(data):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "DUPLICATE_JSON_KEY")
            result[key] = value
        return result

    def bad_number(value):
        raise Refusal("NONFINITE_JSON")
    return json.loads(data, object_pairs_hook=pairs, parse_constant=bad_number)


def pitch_class(note):
    require(type(note) is str and re.fullmatch(r"[A-G](?:#|b)?", note) is not None,
            "PRINTED_PITCH_SPELLING")
    return (PC[note[0]] + (1 if note.endswith("#") else -1 if note.endswith("b") else 0)) % 12


class Family:
    """Read a fixed trusted source closure; do not widen existing generators."""

    def __init__(self, root: Path):
        self.root = root
        raw = {}
        for path, expected in PINS.items():
            file = root / path
            require(not file.is_symlink(), "SOURCE_SYMLINK")
            data = file.read_bytes()
            require(hashlib.sha256(data).hexdigest() == expected, "SOURCE_PIN_DRIFT")
            raw[path] = data
        self.policy = strict_json(raw[POLICY])
        self.bindings = {b["package_key"]: b for b in
                         map(strict_json, raw[BINDINGS].splitlines())}
        all_records = list(map(strict_json, raw[PACKET].splitlines()))
        self.records = {r["package_key"]: r for r in all_records}
        require(len(self.bindings) == 168 and len(self.records) == 222, "SOURCE_FAMILY_SIZE")
        self.keys = [key for key in self.bindings if key != REPRESENTATIVE]
        require(len(self.keys) == 167 and all(k.startswith(PREFIX) for k in self.keys),
                "SIBLING_SCOPE")
        self.lines = raw[TXT].decode().splitlines()
        self.context = strict_json(raw[CONTEXT])
        self.source_refs = [{"path": p, "sha256": h} for p, h in PINS.items()]

    def contract(self, key):
        require(type(key) is str and key in self.keys, "EXACT_SIBLING_SCOPE")
        binding = self.bindings[key]
        row = self.records[key]
        require(digest(row) == binding["record_canonical_sha256"] and
                row["source_identity"] == binding["source_identity"], "SOURCE_RECORD_BINDING")
        components = binding["printed_components"]
        require(type(components) is list and len(components) == 3, "PRINTED_COMPONENTS")
        root, quality, frets = components
        require(root in ROOTS and quality in QUALITIES, "ROOT_QUALITY")
        page = binding["pdf_page"]
        require(type(page) is int and 3 <= page <= 6, "SOURCE_PAGE")
        selected_strings = list(range(page, page - 3, -1))
        members = binding["members_low_to_high"]
        require(type(members) is list and len(members) == 3, "THREE_WRITTEN_VOICES")
        fret_numbers = [int(x) for x in frets.split("-")]
        require(len(fret_numbers) == 3, "SOURCE_FRETS")
        for contact, string, fret in zip(members, selected_strings, fret_numbers):
            require(type(contact) is dict and set(contact) == {"string", "fret", "muted"},
                    "CONTACT_SCHEMA")
            require(type(contact["string"]) is int and contact["string"] == string and
                    type(contact["fret"]) is int and contact["fret"] == fret and
                    0 <= fret <= 24 and contact["muted"] is False, "WRITTEN_CONTACT")
        events = row["implementation"]["events"]
        expected = [{"order": 1, "kind": "blocked_triad", "onset_q": None,
                     "duration_q": None, "members": members}]
        expected.extend({"order": i + 2, "kind": "string_contact", "onset_q": None,
                         "duration_q": None, **c} for i, c in enumerate(members))
        require(canonical(events) == canonical(expected), "FOUR_EXACT_WRITTEN_ACTIONS")
        literal = self.lines[binding["txt_line"] - 1]
        # Original family table: root | major/minor spelling | six fixed shapes.
        cells = [x.strip() for x in literal.split("|")]
        require(len(cells) == 8 and cells[0] == root and
                cells[2 + QUALITIES.index(quality)] == frets, "TXT_CELL_BINDING")
        spelling = cells[1].split("/")[0 if quality.startswith("Maj") else 1].strip().split("-")
        inversion = quality.split()[1]
        order = {"RP": [0, 1, 2], "1st": [1, 2, 0], "2nd": [2, 0, 1]}[inversion]
        degrees = ["1", "3" if quality.startswith("Maj") else "b3", "5"]
        ordered_notes, ordered_degrees = [spelling[i] for i in order], [degrees[i] for i in order]
        midi = [TUNING[c["string"]] + c["fret"] for c in members]
        require(midi == binding["derived_standard_tuning_midi"] and
                all(a < b for a, b in zip(midi, midi[1:])) and
                all(m % 12 == pitch_class(n) for m, n in zip(midi, ordered_notes)),
                "VOICE_ORDER_SPELLING_INVERSION")
        set_header = "STRINGS " + "-".join(str(i) for i in reversed(selected_strings))
        start = next(i for i, line in enumerate(self.lines) if line.startswith(set_header))
        finger_formula = self.lines[start + 1 + QUALITIES.index(quality)]
        finger_match = re.search(r"fingers ([1-4]-[1-4]-[1-4])$", finger_formula)
        require(finger_match is not None, "SOURCE_FINGER_SUGGESTION")
        voices = [{"printed_note": note, "printed_degree": degree, **contact,
                   "derived_standard_tuning_midi": pitch}
                  for note, degree, contact, pitch in zip(ordered_notes, ordered_degrees, members, midi)]
        return {
            "schema": SCHEMA, "package_key": key, "source_identity": binding["source_identity"],
            "source_policy_sha256": PINS[POLICY], "source_refs": copy.deepcopy(self.source_refs),
            "source_binding_sha256": digest(binding), "source_record_sha256": digest(row),
            "root": root, "quality": "major" if quality.startswith("Maj") else "minor",
            "inversion": {"RP": "root position", "1st": "first inversion", "2nd": "second inversion"}[inversion],
            "printed_components": components.copy(), "printed_spelling_root_order": spelling,
            "voices_low_to_high": voices, "bass_degree": ordered_degrees[0],
            "written_source_events": copy.deepcopy(events), "source_timing_authority": copy.deepcopy(row["timing_authority"]),
            "actions": [{"order": 1, "kind": "blocked_triad", "voices": voices},
                        *[{"order": i + 2, "kind": "string_contact", "voices": [voice]}
                          for i, voice in enumerate(voices)]],
            "setup": copy.deepcopy(self.policy["source_facts"]["source_setup"]),
            "source_context": copy.deepcopy(row["implementation"]["context_tasks"]),
            "suggested_fingers_low_to_high": finger_match.group(1).split("-"),
            "suggested_finger_source": {"physical_page": 2, "TXT_line": start + 2 + QUALITIES.index(quality),
                                      "exact_formula": finger_formula, "may_adapt_open_strings": True},
            "mute_outside_strings": sorted(set(TUNING) - set(selected_strings)),
            "release_instruction": self.policy["source_facts"]["source_release"],
            "page_workout_order": self.policy["source_facts"]["page_workout_order"],
            "broader_session_set_transfer_progression_mastery_completed": None,
            "execution_mode": "source_order_only", "numeric_clock": None, "bpm": None,
            "source_pick_direction": None, "acoustic_gates": None,
            "optional_authored_pulse_policy_reference": {"path": POLICY, "sha256": PINS[POLICY],
                                                        "execution_implemented_by_this_model": False},
            "physical_reports_verified": False, "performance_observed": False, "automatic_assessment": False,
            "persistence_or_attempt": False, "grants_credit": False, "runtime_admitted": False,
            "official_child_accepted": False,
        }

    def validate(self, contract):
        require(type(contract) is dict and type(contract.get("package_key")) is str, "CONTRACT_SCHEMA")
        require(canonical(contract) == canonical(self.contract(contract["package_key"])), "EXACT_SOURCE_CONTRACT")

    def load_packet(self, path, expected_sha):
        data = Path(path).read_bytes()
        require(hashlib.sha256(data).hexdigest() == expected_sha, "PACKET_CUSTODY")
        rows = list(map(strict_json, data.splitlines()))
        require([r["package_key"] for r in rows] == self.keys, "EXACT_167_ORDER")
        for row in rows:
            c = row["implementation"]["manual_execution_contract"]
            self.validate(c)
            require(row["source_identity"] == c["source_identity"] and
                    canonical(row["implementation"]["events"]) == canonical(c["written_source_events"]) and
                    row["status"] == "IMPLEMENTED_PRIVATE_QA_PENDING", "PACKET_SOURCE_STATUS")
        return rows


class Task:
    """One serialized owner with retained diagnosis and manual-release fences."""

    def __init__(self, family, contract):
        family.validate(contract)
        self.family, self.contract = family, copy.deepcopy(contract)
        self.instance, self.generation, self.revision = next(_instances), 1, 1
        self.phase, self.action, self.pending, self.outcome = "CHOOSE", None, None, "NONE"
        self.history, self.diagnosis = [], None
        self._lock = threading.RLock()

    def snapshot(self):
        with self._lock:
            return copy.deepcopy({"instance": self.instance, "pass_generation": self.generation,
                                  "revision": self.revision, "phase": self.phase, "action_order": self.action,
                                  "pending_outcome": self.pending, "outcome": self.outcome,
                                  "diagnosis": self.diagnosis, "history": self.history,
                                  "performance_observed": False, "grants_credit": False})

    def capture(self, kind):
        with self._lock:
            require(kind in ["select", "ready", "respond", "release", "again", "cancel", "navigate", "reopen"], "INTENT_KIND")
            return {"instance": self.instance, "package_key": self.contract["package_key"],
                    "contract_sha256": digest(self.contract), "source_policy_sha256": PINS[POLICY],
                    "pass_generation": self.generation, "revision": self.revision,
                    "phase": self.phase, "action_order": self.action, "kind": kind}

    def expected_payload(self, kind):
        c = self.contract
        if kind == "select":
            return {"mode": "source_order_only"}
        if kind == "ready":
            return {"root": c["root"], "quality": c["quality"], "inversion": c["inversion"],
                    "bass_degree": c["bass_degree"], "named_notes_low_to_high": [v["printed_note"] for v in c["voices_low_to_high"]],
                    "named_degrees_low_to_high": [v["printed_degree"] for v in c["voices_low_to_high"]],
                    "silent_look_name_form_release_reported": True, "minimum_pressure_reported": True,
                    "outside_strings_muted_reported": True, "source_setup_acknowledged": True}
        if kind == "respond":
            require(self.phase == "MANUAL_STEPS", "NO_CURRENT_ACTION")
            return {"response": "acknowledged", "action_order": self.action,
                    "written_action": copy.deepcopy(c["actions"][self.action - 1]),
                    "performed_action_reported": True}
        if kind == "release":
            return {"released_completely_reported": True}
        return {}

    def _release(self, outcome, diagnosis):
        self.phase, self.pending, self.diagnosis = "RELEASE", outcome, diagnosis

    def apply(self, token, payload):
        with self._lock:
            require(type(token) is dict and type(token.get("kind")) is str, "TOKEN_SCHEMA")
            require(canonical(token) == canonical(self.capture(token["kind"])), "FOREIGN_OR_STALE_INTENT")
            require(type(payload) is dict, "PAYLOAD_SCHEMA")
            kind = token["kind"]
            before = {"phase": self.phase, "action": self.action, "revision": self.revision, "generation": self.generation}
            if kind == "select":
                require(self.phase == "CHOOSE" and payload == {"mode": "source_order_only"}, "MODE_CHOICE")
                self.phase = "SETUP"
            elif kind == "ready":
                require(self.phase == "SETUP", "READY_PHASE")
                expected = self.expected_payload(kind)
                require(set(payload) == set(expected), "SETUP_FIELDS")
                for field, value in expected.items():
                    require(type(payload[field]) is type(value), "SETUP_VALUE_TYPE")
                if canonical(payload) != canonical(expected):
                    self._release("RETRY_REQUESTED", {"code": "SETUP_NAME_OR_MANUAL_REPORT_MISMATCH", "expected": expected,
                                                      "reported": copy.deepcopy(payload), "observed_failure": False})
                else:
                    self.phase, self.action = "MANUAL_STEPS", 1
            elif kind == "respond":
                require(self.phase == "MANUAL_STEPS", "RESPONSE_PHASE")
                require(payload.get("response") in ["acknowledged", "needs_retry", "stopped", "unknown"], "RESPONSE_VALUE")
                if payload["response"] != "acknowledged":
                    require(set(payload) == {"response"}, "STOP_RETRY_FIELDS")
                    self._release("CANCELLED" if payload["response"] == "stopped" else "RETRY_REQUESTED",
                                  {"code": "MANUAL_" + payload["response"].upper(), "observed_failure": False})
                else:
                    expected = self.expected_payload(kind)
                    require(set(payload) == set(expected) and type(payload["action_order"]) is int and
                            payload["action_order"] == self.action and type(payload["performed_action_reported"]) is bool,
                            "RESPONSE_FIELDS_OR_ORDER")
                    if canonical(payload) != canonical(expected):
                        self._release("RETRY_REQUESTED", {"code": "WRITTEN_CONTACT_DEGREE_OR_MANUAL_REPORT_MISMATCH",
                                                          "expected": expected, "reported": copy.deepcopy(payload), "observed_failure": False})
                    elif self.action == 4:
                        self._release("USER_REPORTED_STEPS_FINISHED", None)
                    else:
                        self.action += 1
            elif kind == "release":
                require(self.phase == "RELEASE" and canonical(payload) == canonical(self.expected_payload(kind)),
                        "EXPLICIT_PHYSICAL_RELEASE_REQUIRED")
                self.phase, self.outcome = "CLOSED", self.pending
                self.pending, self.action = None, None
            elif kind in ["cancel", "navigate"]:
                require(self.phase not in ["RELEASE", "CLOSED"] and payload == {}, "CANCEL_PHASE")
                self._release("CANCELLED", {"code": kind.upper(), "observed_failure": False})
            elif kind in ["again", "reopen"]:
                require(self.phase == "CLOSED" and payload == {}, "RETRY_REOPEN_REQUIRES_RELEASE")
                self.generation += 1
                self.phase, self.action, self.pending, self.outcome, self.diagnosis = "CHOOSE", None, None, "NONE", None
            self.revision += 1
            self.history.append({"token": copy.deepcopy(token), "reported": copy.deepcopy(payload), "before": before,
                                 "after": {"phase": self.phase, "action": self.action, "generation": self.generation},
                                 "diagnosis": copy.deepcopy(self.diagnosis), "observed_performance": False})
            return self.snapshot()
