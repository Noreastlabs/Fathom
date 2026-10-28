"""Private untimed paired-phrase tasks; manual reports never grant learner credit.

Load a producer-sealed packet by its hash before selecting a task. Construction
does not supply timing, physical observation, admission, Attempt or persistence.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

SCHEMA = "fathom.private-manual-minor-call-dominant-answer.v1"
NOTES = ["A", "C", "E", "F", "E", "D", "C", "A",
         "E", "F", "G#", "B", "D", "C", "B", "A"]
DEGREES = ["1", "b3", "5", "b6", "5", "4", "b3", "1",
           "5", "b6", "7", "2", "4", "b3", "2", "1"]
ROLES = ["CAL"] * 8 + ["ANS"] * 7 + [">A"]
TUNING = {1: 64, 2: 59, 3: 55, 4: 50, 5: 45, 6: 40}
PC = {"A": 9, "B": 11, "C": 0, "D": 2, "E": 4, "F": 5, "G#": 8}
CONTEXT = ("The call and answer use eight tones each. Preserve the rhythmic "
           "identity while changing harmonic function. The final A must sound "
           "like the completion of the answer, not an extra note after the phrase.")
VARIATION = ("Variation: leave two beats of silence between call and answer. "
             "The internal bar count must continue through the gap.")
SAFETY = ("Safety: use slides instead of forced bends on heavy strings; "
          "stop for pain or persistent tension.")
REPORTS = ["minor_call_dominant_answer_distinguished_reported",
           "rhythmic_identity_preserved_reported",
           "two_silent_beats_counted_with_internal_bar_count_reported",
           "final_A_completed_answer_without_extra_attack_reported",
           "final_A_released_reported", "source_safety_followed_reported"]
PDF_PATH = ("Notes/music/guitar project/PDF version/Guitar_Exercises_Section_VIII_Level_68_"
            "E_Phrygian_Dominant_Diminished_Seventh_Symmetry_Altered_Dominant_Colors_and_"
            "Harmonic_Minor_Improvisation_Synthesis.pdf")
PDF_REF = {"path": PDF_PATH, "bytes": 53385,
           "sha256": "4db7d55cd64c1b038dfce68dfc3eda60fc82077fcf21532d96ad79457031a378",
           "physical_pages": [1, 15, 20]}


class Refusal(ValueError):
    """Explicit invalid source/contract/choice/response refusal."""


def require(condition, reason):
    if not condition:
        raise Refusal(reason)


def compact(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def digest(value):
    return hashlib.sha256(compact(value).encode()).hexdigest()


def check_events(events):
    require(type(events) is list and len(events) == 16, "SIXTEEN_CONTACTS_REQUIRED")
    for i, event in enumerate(events):
        require(type(event) is dict, "EVENT_OBJECT")
        require(set(event) == {"order", "kind", "onset_q", "duration_q", "printed_note",
                               "printed_column", "string", "fret", "muted", "degree", "role"},
                "EXACT_EVENT_SCHEMA")
        require(type(event["printed_column"]) is int and event["printed_column"] == i * 3,
                "PRINTED_PDF_COLUMN")
        require(type(event.get("order")) is int and event["order"] == i + 1,
                "SOURCE_ORDER")
        require(event.get("kind") == "note_contact" and event.get("muted") is False,
                "SOUNDED_CONTACT")
        require(event.get("printed_note") == NOTES[i] and
                event.get("degree") == DEGREES[i] and event.get("role") == ROLES[i],
                "PRINTED_NOTE_DEGREE_ROLE")
        require(type(event.get("string")) is int and event["string"] in TUNING and
                type(event.get("fret")) is int and 0 <= event["fret"] <= 24,
                "TYPED_STRING_FRET")
        require((TUNING[event["string"]] + event["fret"]) % 12 == PC[NOTES[i]],
                "CONTACT_PITCH")
        require(event.get("onset_q") is None and event.get("duration_q") is None,
                "UNAUTHORED_CLOCK")


def make_contract(key, source_identity, events, source_refs):
    check_events(events)
    identities = ["level068/modulei/p015-card0" + str(i) + "/p" + str(i) for i in range(1, 6)]
    require(type(source_identity) is str and source_identity in identities and
            type(key) is str and key == "exercise-completeness-r01/" + source_identity, "KEY_SCOPE")
    require(type(source_refs) is list and compact(source_refs) == compact([PDF_REF]),
            "EXACT_ORIGINAL_SOURCE")
    gap = {"source_beats": 2, "beat_to_quarter_note_mapping": None,
           "duration_q": None, "seconds": None, "fixed_bpm": None,
           "automatic_scheduling": False, "counting": "manual declaration only"}
    return {
        "schema": SCHEMA, "package_key": key, "source_identity": source_identity,
        "source_refs": copy.deepcopy(source_refs),
        "ordered_contacts": copy.deepcopy(events),
        "source_rules": {"physical_page": 15, "exact_context": CONTEXT,
                         "exact_variation": VARIATION,
                         "safety": {"physical_page": 1, "exact_text": SAFETY}},
        "steps": [
            {"order": 1, "action": "name_minor_call_and_dominant_answer_then_prepare_safely"},
            {"order": 2, "action": "play_complete_printed_call_then_answer",
             "contacts_from_selection": "paired", "source_orders": list(range(1, 17))},
            {"order": 3, "action": "play_variation_call",
             "contacts_from_selection": "variation_call", "source_orders": list(range(1, 9))},
            {"order": 4, "action": "count_two_silent_source_beats_with_internal_bar_count",
             "gap": gap, "attack_count": 0},
            {"order": 5, "action": "play_variation_answer_ending_on_existing_A",
             "contacts_from_selection": "variation_answer", "source_orders": list(range(9, 17)),
             "additional_final_A_attack": False},
            {"order": 6, "action": "release_and_report_phrase_gap_and_safety",
             "required_reports": REPORTS.copy()},
        ],
        "printed_contacts": 16, "additional_variation_replay_contacts": 16,
        "selected_picking": "D/U alternation with selected start is an implementation choice; gap has no attack.",
        "numeric_clock": None, "fixed_bpm": None, "fixed_fingers": None,
        "source_rhythm": "Preserve identity by manual report; note onsets/durations and meter are unknown.",
        "automatic_assessment": False, "performance_observed": False,
        "source_full_book_mastery_observed": False,
        "runtime_admitted": False, "grants_credit": False,
    }


def validate_contract(contract):
    require(type(contract) is dict, "CONTRACT_OBJECT")
    try:
        expected = make_contract(contract["package_key"], contract["source_identity"],
                                 contract["ordered_contacts"], contract["source_refs"])
    except (KeyError, TypeError) as error:
        raise Refusal("CONTRACT_SCHEMA") from error
    require(compact(contract) == compact(expected), "EXACT_CONTRACT_SCHEMA")


def selection(contract, request):
    validate_contract(contract)
    require(type(request) is dict and set(request) ==
            {"package_key", "contract_sha256", "start_stroke"}, "SELECTION_FIELDS")
    require(type(request["package_key"]) is str and request["package_key"] ==
            contract["package_key"] and type(request["contract_sha256"]) is str and
            request["contract_sha256"] == digest(contract), "SELECTION_IDENTITY_HASH")
    require(type(request["start_stroke"]) is str and request["start_stroke"] in ["D", "U"],
            "START_STROKE")
    contacts = copy.deepcopy(contract["ordered_contacts"])
    for i, event in enumerate(contacts):
        event["selected_pick"] = ("DU" if request["start_stroke"] == "D" else "UD")[i % 2]
        event["selected_pass_order"] = i + 1
    return {"paired": contacts, "variation_call": copy.deepcopy(contacts[:8]),
            "silent_gap": copy.deepcopy(contract["steps"][3]["gap"]),
            "variation_answer": copy.deepcopy(contacts[8:]),
            "printed_contacts": 16, "replay_contacts": 16,
            "performance_observed": False, "grants_credit": False}


def done_responses():
    """Producer fixture for user-declaration schema; not a performance observation."""
    return [
        {"step": 1, "response": "acknowledged", "ordered_names": ["A-minor call", "E-dominant answer -> A"], "prepared_safely_reported": True},
        {"step": 2, "response": "acknowledged", "complete_printed_pair_played_reported": True},
        {"step": 3, "response": "acknowledged", "eight_contact_call_played_reported": True},
        {"step": 4, "response": "acknowledged", "silent_source_beats": 2, "internal_bar_count_continued_reported": True},
        {"step": 5, "response": "acknowledged", "eight_contact_answer_ended_on_existing_A_reported": True},
        {"step": 6, "response": "acknowledged", **dict.fromkeys(REPORTS, True)},
    ]


def workflow_state(contract, request, responses):
    validate_contract(contract)
    require(type(responses) is list and len(responses) <= 6, "RESPONSE_SEQUENCE")
    if request is None:
        require(responses == [], "RESPONSES_BEFORE_SELECTION")
        return {"state": "AWAITING_SELECTION", "performance_observed": False, "grants_credit": False}
    plan = selection(contract, request)
    expected = done_responses()
    terminal = False
    state = "IN_PROGRESS"
    for i, response in enumerate(responses):
        require(not terminal, "AFTER_TERMINAL")
        require(type(response) is dict and type(response.get("step")) is int and
                response["step"] == i + 1, "RESPONSE_ORDER")
        require(response.get("response") in ["acknowledged", "needs_retry", "stopped"],
                "RESPONSE_VALUE")
        if response["response"] != "acknowledged":
            require(set(response) == {"step", "response"}, "TERMINAL_FIELDS")
            terminal = True
            state = "STOPPED" if response["response"] == "stopped" else "NEEDS_RETRY"
            continue
        wanted = expected[i]
        require(set(response) == set(wanted), "RESPONSE_FIELDS")
        for field, value in wanted.items():
            require(type(response[field]) is type(value), "RESPONSE_VALUE_TYPE")
            if type(value) is bool:
                if not response[field]:
                    terminal, state = True, "NEEDS_RETRY"
            else:
                require(response[field] == value, "EXACT_RESPONSE_VALUE")
    if not terminal and len(responses) == 6:
        state = "USER_REPORTED_STEPS_FINISHED"
    step = copy.deepcopy(contract["steps"][len(responses)]) if state == "IN_PROGRESS" else None
    if step and "contacts_from_selection" in step:
        step["selected_contacts"] = copy.deepcopy(plan[step["contacts_from_selection"]])
    return {"state": state, "next_step": step, "selection": plan,
            "performance_observed": False, "grants_credit": False}


def load_packet(path: Path, expected_sha256: str):
    """Refuse packet drift before returning contracts from trusted producer custody."""
    data = path.read_bytes()
    require(hashlib.sha256(data).hexdigest() == expected_sha256, "PACKET_HASH")
    rows = [json.loads(line) for line in data.splitlines() if line]
    require(len(rows) == 5 and len({r["package_key"] for r in rows}) == 5, "PACKET_KEYS")
    for row in rows:
        validate_contract(row["implementation"]["manual_execution_contract"])
        require(row["status"] == "IMPLEMENTED_PRIVATE_QA_PENDING", "PACKET_STATUS")
    return rows
