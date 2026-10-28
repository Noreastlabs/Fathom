"""Source-grounded untimed recovery tasks with explicit derived contact choices.

Nearest is this provisional model's minimum semitone-distance interpretation,
not a printed string/fret or a claim of physical security. Every performance,
pulse and rest-of-bar result is a manual declaration. Load sealed packet custody
before using a contract. This module has no audio, persistence or credit path.
"""
from __future__ import annotations
import copy
import hashlib
import json
from pathlib import Path

SCHEMA = "fathom.private-manual-chosen-recovery-pair.v1"
TUNING = {1: 64, 2: 59, 3: 55, 4: 50, 5: 45, 6: 40}
PC = {"A": 9, "B": 11, "C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "G#": 8}
PAIRS = [
    ("e7fe", "E7", "F", "E", "b9", "root"),
    ("e7fg#", "E7", "F", "G#", "b9", "3"),
    ("e7gg#", "E7", "G", "G#", "#9*", "3"),
    ("e7ag#", "E7", "A", "G#", "11", "3"),
    ("e7ab", "E7", "A", "B", "11", "5"),
    ("e7cb", "E7", "C", "B", "b13", "5"),
    ("e7de", "E7", "D", "E", "b7", "root"),
    ("amg#a", "Am", "G#", "A", "7", "1"),
    ("ambc", "Am", "B", "C", "2", "b3"),
    ("amfe", "Am", "F", "E", "b6", "5"),
    ("dmg#a", "Dm", "G#", "A", "#4", "5"),
    ("g#dim7fe", "G#dim7", "F", "E", "bb7", "Am fifth"),
]
SOURCE_RULE = "PRESERVE THE PULSE; MOVE TO THE NEAREST SECURE TARGET; SIMPLIFY THE REST OF THE BAR"
SAFETY = "Safety: use slides instead of forced bends on heavy strings; stop for pain or persistent tension."
TARGET_RULE = "TENSION SOUNDS RANDOM: name the target before playing the tension."
PDF_PATH = ("Notes/music/guitar project/PDF version/Guitar_Exercises_Section_VIII_Level_68_"
            "E_Phrygian_Dominant_Diminished_Seventh_Symmetry_Altered_Dominant_Colors_and_"
            "Harmonic_Minor_Improvisation_Synthesis.pdf")
PDF_REF = {"path": PDF_PATH, "bytes": 53385,
           "sha256": "4db7d55cd64c1b038dfce68dfc3eda60fc82077fcf21532d96ad79457031a378",
           "physical_pages": [1, 19, 20]}
REPORTS = ["chosen_target_secure_reported", "pulse_preserved_reported",
           "named_destination_heard_reported", "two_selected_pair_contacts_played_reported",
           "rest_of_existing_bar_simplified_reported", "final_target_released_reported",
           "source_safety_followed_reported"]


class Refusal(ValueError):
    pass


def require(condition, reason):
    if not condition:
        raise Refusal(reason)


def compact(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def digest(value):
    return hashlib.sha256(compact(value).encode()).hexdigest()


def identity(number):
    suffix = PAIRS[number - 1][0]
    source = "level068/modulek/p019-card" + f"{number:02d}" + "/" + suffix
    return "exercise-completeness-r01/" + source, source


def pair_for_key(key):
    for number, pair in enumerate(PAIRS, 1):
        if identity(number)[0] == key:
            return number, pair
    raise Refusal("EXACT_KEY_SCOPE")


def contact_midi(contact):
    require(type(contact) is dict and set(contact) == {"string", "fret"}, "CONTACT_FIELDS")
    require(type(contact["string"]) is int and contact["string"] in TUNING and
            type(contact["fret"]) is int and 0 <= contact["fret"] <= 24, "CONTACT_TYPE_RANGE")
    return TUNING[contact["string"]] + contact["fret"]


def pitch_menu(note):
    require(note in PC, "PITCH_SPELLING")
    return [{"string": string, "fret": fret}
            for string, open_midi in sorted(TUNING.items()) for fret in range(25)
            if (open_midi + fret) % 12 == PC[note]]


def nearest_targets(source_contact, destination_note):
    source_midi = contact_midi(source_contact)
    options = pitch_menu(destination_note)
    smallest = min(abs(contact_midi(contact) - source_midi) for contact in options)
    return [contact for contact in options if abs(contact_midi(contact) - source_midi) == smallest]


def check_source_events(key, events):
    _, pair = pair_for_key(key)
    require(type(events) is list and len(events) == 2, "TWO_SOURCE_PITCHES")
    for order, (event, note) in enumerate(zip(events, pair[2:4]), 1):
        require(type(event) is dict and set(event) == {"order", "kind", "onset_q", "duration_q",
                                                      "printed_note", "string", "fret"}, "SOURCE_EVENT_SCHEMA")
        require(type(event["order"]) is int and event["order"] == order and
                event["kind"] == "recovery_note_contact" and event["printed_note"] == note,
                "SOURCE_PITCH_ORDER")
        require(all(event[field] is None for field in ["onset_q", "duration_q", "string", "fret"]),
                "PRINTED_POSITION_AND_CLOCK_UNKNOWN")


def make_contract(key, source_identity, events):
    number, pair = pair_for_key(key)
    require(identity(number)[1] == source_identity, "SOURCE_IDENTITY")
    check_source_events(key, events)
    label = pair[1] + ": " + pair[2] + " -> " + pair[3]
    roles = pair[4] + " -> " + pair[5]
    return {
        "schema": SCHEMA, "package_key": key, "source_identity": source_identity,
        "source_reference": copy.deepcopy(PDF_REF),
        "printed_label": label, "printed_roles": roles,
        "chord_context": pair[1], "source_pitch_events": copy.deepcopy(events),
        "printed_pitch_count": 2, "printed_contact_positions": None,
        "source_rule": {"physical_page": 19, "exact_text": SOURCE_RULE},
        "source_safety": {"physical_page": 1, "exact_text": SAFETY},
        "source_target_naming_rule": TARGET_RULE,
        "source_contact_menu": pitch_menu(pair[2]),
        "selection_policy": {
            "tuning": "standard", "fret_bound": [0, 24],
            "origin": "explicit performer-selected realization of first printed pitch",
            "destination": "explicit performer-selected realization of second printed pitch, minimum absolute MIDI semitone distance from selected origin within this bounded menu",
            "nearest_policy_is_provisional_implementation_interpretation": True,
            "printed_fixed_octave_string_fret": None,
            "physical_security": "manual declaration; no automatic certification",
            "exhaustive_source_fingering_or_physical_viability_claim": False,
        },
        "borrowed_G_natural_scope": "Borrowed #9* only in E7; not a scale tone outside E7." if pair[2] == "G" else None,
        "destination_harmonic_context": "Am fifth" if pair[5] == "Am fifth" else pair[1],
        "steps": [
            {"order": 1, "action": "name_chord_pitch_roles_target_then_prepare_existing_bar_and_safe_contacts"},
            {"order": 2, "action": "play_chosen_origin_pitch", "contact_from_selection": "origin"},
            {"order": 3, "action": "move_to_chosen_nearest_named_target_preserving_pulse", "contact_from_selection": "target"},
            {"order": 4, "action": "simplify_rest_of_existing_bar_using_explicit_performer_plan",
             "fixed_source_notes_or_attacks": None},
            {"order": 5, "action": "release_and_report_recovery_pulse_security_simplification_safety",
             "required_reports": REPORTS.copy()},
        ],
        "source_remainder_of_bar_notes": None, "source_remainder_of_bar_duration": None,
        "numeric_clock": None, "fixed_bpm": None, "fixed_fingers": None,
        "selected_picking": "Two D/U alternating attacks are a selected implementation choice, not printed picking.",
        "source_ear_tests_and_whole_workbook_mastery_completed": None,
        "automatic_assessment": False, "performance_observed": False,
        "runtime_admitted": False, "grants_credit": False,
    }


def validate_contract(contract):
    require(type(contract) is dict, "CONTRACT_OBJECT")
    try:
        expected = make_contract(contract["package_key"], contract["source_identity"], contract["source_pitch_events"])
    except (KeyError, TypeError) as error:
        raise Refusal("CONTRACT_SCHEMA") from error
    require(compact(contract) == compact(expected), "EXACT_SOURCE_CONTRACT")


def selection(contract, request):
    validate_contract(contract)
    require(type(request) is dict and set(request) == {"package_key", "contract_sha256", "source_contact",
                                                      "target_contact", "start_stroke", "rest_of_bar_plan"},
            "SELECTION_FIELDS")
    require(type(request["package_key"]) is str and request["package_key"] == contract["package_key"] and
            type(request["contract_sha256"]) is str and request["contract_sha256"] == digest(contract),
            "SELECTION_IDENTITY_HASH")
    require(type(request["start_stroke"]) is str and request["start_stroke"] in ["D", "U"], "START_STROKE")
    require(type(request["rest_of_bar_plan"]) is str and 1 <= len(request["rest_of_bar_plan"].strip()) <= 500,
            "EXPLICIT_REMAINDER_PLAN")
    origin_midi = contact_midi(request["source_contact"])
    target_midi = contact_midi(request["target_contact"])
    require(request["source_contact"] in contract["source_contact_menu"], "ORIGIN_PITCH_MENU")
    destination = contract["source_pitch_events"][1]["printed_note"]
    require(request["target_contact"] in nearest_targets(request["source_contact"], destination),
            "NEAREST_NAMED_TARGET")
    selected = []
    for order, contact, midi in [(1, request["source_contact"], origin_midi), (2, request["target_contact"], target_midi)]:
        selected.append({"source_event_order": order, "required_source_pitch": contract["source_pitch_events"][order - 1]["printed_note"],
                         "kind": "chosen_contact_realization", **copy.deepcopy(contact), "midi": midi,
                         "selected_pick": ("DU" if request["start_stroke"] == "D" else "UD")[order - 1],
                         "onset_q": None, "duration_q": None,
                         "provenance": "explicit performer choice; not printed TAB position or observed playing"})
    return {"origin": selected[0], "target": selected[1], "chosen_pair": selected,
            "target_pitch_distance_semitones": abs(target_midi - origin_midi),
            "rest_of_bar_plan": request["rest_of_bar_plan"], "remainder_notes_or_attacks_generated": False,
            "performance_observed": False, "grants_credit": False}


def done_responses(contract, request):
    return [
        {"step": 1, "response": "acknowledged", "printed_label": contract["printed_label"],
         "printed_roles": contract["printed_roles"], "target_named_before_origin_reported": True,
         "existing_bar_and_pulse_prepared_reported": True, "chosen_contacts_safe_and_secure_reported": True},
        {"step": 2, "response": "acknowledged", "chosen_origin_played_reported": True},
        {"step": 3, "response": "acknowledged", "chosen_named_target_reached_preserving_pulse_reported": True},
        {"step": 4, "response": "acknowledged", "rest_of_bar_plan": request["rest_of_bar_plan"],
         "rest_of_existing_bar_simplified_reported": True},
        {"step": 5, "response": "acknowledged", **dict.fromkeys(REPORTS, True)},
    ]


def workflow_state(contract, request, responses):
    validate_contract(contract)
    require(type(responses) is list and len(responses) <= 5, "RESPONSE_SEQUENCE")
    if request is None:
        require(responses == [], "RESPONSES_BEFORE_CHOICE")
        return {"state": "AWAITING_SELECTION", "performance_observed": False, "grants_credit": False}
    plan = selection(contract, request)
    expected = done_responses(contract, request)
    terminal, state = False, "IN_PROGRESS"
    for i, response in enumerate(responses):
        require(not terminal, "AFTER_TERMINAL")
        require(type(response) is dict and type(response.get("step")) is int and response["step"] == i + 1, "RESPONSE_ORDER")
        require(response.get("response") in ["acknowledged", "needs_retry", "stopped"], "RESPONSE_VALUE")
        if response["response"] != "acknowledged":
            require(set(response) == {"step", "response"}, "TERMINAL_FIELDS")
            terminal = True; state = "STOPPED" if response["response"] == "stopped" else "NEEDS_RETRY"
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
    if not terminal and len(responses) == 5:
        state = "USER_REPORTED_STEPS_FINISHED"
    step = copy.deepcopy(contract["steps"][len(responses)]) if state == "IN_PROGRESS" else None
    if step and "contact_from_selection" in step:
        step["chosen_contact"] = copy.deepcopy(plan[step["contact_from_selection"]])
    if step and step["order"] == 4:
        step["rest_of_bar_plan"] = plan["rest_of_bar_plan"]
    return {"state": state, "next_step": step, "selection": plan,
            "performance_observed": False, "grants_credit": False}


def load_packet(path: Path, expected_sha256: str):
    data = path.read_bytes()
    require(hashlib.sha256(data).hexdigest() == expected_sha256, "PACKET_HASH")
    rows = [json.loads(line) for line in data.splitlines() if line]
    require([row["package_key"] for row in rows] == [identity(i)[0] for i in range(1, 13)], "TWELVE_EXACT_KEYS")
    for row in rows:
        validate_contract(row["implementation"]["manual_execution_contract"])
        require(row["status"] == "IMPLEMENTED_PRIVATE_QA_PENDING", "PRIVATE_STATUS")
    return rows
