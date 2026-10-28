"""Finite source task relationships; no clock or performed response is selected."""
import hashlib
import json
import re

MAJOR = {'A': '1', 'B': '2', 'C#': '3', 'E': '5', 'F#': '6'}
MINOR = {'F#': '1', 'A': 'b3', 'B': '4', 'C#': '5', 'E': 'b7'}
OPEN = {'E': 40, 'A': 45, 'D': 50, 'G': 55, 'B': 59, 'e': 64}
PC = {'A': 9, 'B': 11, 'C#': 1, 'E': 4, 'F#': 6}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def contacts(record, count, module):
    require(record['level'] == 39 and record['implementation']['source_module'] == module, 'Wrong source family')
    events = record['implementation']['ordered_contacts']
    require(len(events) == count, 'Wrong exact source contact count')
    for ordinal, event in enumerate(events, 1):
        require(event['ordinal'] == ordinal and event['pick_attack'] is True, 'Source contact order/attack changed')
        note = event['note_spelling']
        require(note in PC and event['midi'] == OPEN[event['string_label']] + event['fret'] and event['midi'] % 12 == PC[note], 'Source physical pitch mismatch')
        require(event['major_degree'] == MAJOR[note] and event['minor_degree'] == MINOR[note], 'Wrong active-tonic degree')
        require(event['onset_q'] is None and event['duration_q'] is None and event['acoustic_gate_q'] is None, 'Unexpected clock or gate')
    return events


def root_duty():
    return {'authority': 'original PDF physical page 2, Root-location rule',
            'before_phrase': 'point to the nearest F# root',
            'after_phrase': ['sing F# without touching the guitar', 'verify it on the instrument'],
            'root_register_or_fret_selected': None, 'generated_events': [],
            'learner_action_observed': False, 'automatic_hearing_assessment': False}


def box(record):
    events = contacts(record, 24, 'B')
    pos = record['implementation']['route_contract']['position']
    require(pos in range(1, 6), 'Unknown position')
    physical = [(e['string_label'], e['fret'], e['finger']) for e in events]
    require(physical[:12] == list(reversed(physical[12:])), 'Source ascent/descent or repeated endpoint changed')
    roots = [e for e in events if e['note_spelling'] == 'F#']
    require(bool(roots), 'Missing F# roots')
    all_ordinals = list(range(1, 25))
    return {'schema_version': 'fathom-source-task-passes.1', 'kind': 'separate_dual_degree_then_root_accent_passes',
            'position_label': f'P{pos}', 'contacts_are_unchanged_between_passes': True,
            'passes': [
                {'pass_ordinal': 1, 'task': 'say_A_major_degrees', 'contact_ordinals': all_ordinals,
                 'spoken_degrees_by_contact': [e['major_degree'] for e in events]},
                {'pass_ordinal': 2, 'task': 'say_F_sharp_minor_degrees', 'contact_ordinals': all_ordinals,
                 'spoken_degrees_by_contact': [e['minor_degree'] for e in events]},
                {'pass_ordinal': 3, 'task': 'accent_only_F_sharp_roots', 'contact_ordinals': all_ordinals,
                 'accent_contact_ordinals': [e['ordinal'] for e in roots],
                 'qualitative_accent': True, 'numeric_velocity': None}],
            'root_contacts': [{'ordinal': e['ordinal'], 'string_label': e['string_label'], 'fret': e['fret'],
                               'minor_degree': '1', 'major_degree': '6'} for e in roots],
            'repeated_high_endpoint_ordinals': [12, 13], 'printed_contact_count': 24,
            'task_pass_memberships': 72, 'printed_module_workout_count': 120,
            'pass_memberships_are_not_additional_printed_notes': True,
            'root_location_manual_duty': root_duty(), 'selected_numeric_clock': None,
            'numeric_acoustic_gates': None, 'native_projection_complete': False,
            'performance_or_credit_claimed': False}


def cadence(record, partner, partner_binding):
    events = contacts(record, 6, 'E')
    other = contacts(partner, 6, 'E')
    label, other_label = [x['source_payload']['printed_label'] for x in (record, partner)]
    position = re.fullmatch(r'P([1-5]) (A-MAJOR|F#-MINOR) CADENCE', label)
    peer_position = re.fullmatch(r'P([1-5]) (A-MAJOR|F#-MINOR) CADENCE', other_label)
    require(position and peer_position and position[1] == peer_position[1] and position[2] != peer_position[2], 'Wrong paired source identity')
    center = 'A' if position[2] == 'A-MAJOR' else 'F#'
    require(record['implementation']['cadence_contract']['center'] == center, 'Wrong cadence center')
    expected = ['B', 'C#', 'E', 'C#'] + (['B', 'A'] if center == 'A' else ['A', 'F#'])
    require([e['note_spelling'] for e in events] == expected, 'Shared seed or selected ending changed')
    fields = ('string_label', 'fret', 'finger', 'midi', 'note_spelling')
    require([[e[k] for k in fields] for e in events[:4]] == [[e[k] for k in fields] for e in other[:4]], 'Same-position physical shared seed differs')
    require(partner_binding['package_key'] == partner['package_key'] and partner_binding['source_identity'] == partner['source_identity'] and partner_binding['record_canonical_sha256'] == digest(partner), 'Wrong immutable partner binding')
    return {'schema_version': 'fathom-source-cadence-relationship.1', 'kind': 'same_seed_two_source_destinations',
            'position_label': f'P{position[1]}', 'center': center, 'partner_predecessor_binding': partner_binding,
            'shared_seed': {'contact_ordinals': [1, 2, 3, 4], 'notes': expected[:4],
                            'physical_contact_and_finger_match': True},
            'source_ending': {'contact_ordinals': [5, 6], 'notes': expected[4:], 'final_tonic': center},
            'ordered_manual_tasks': [
                {'step': 1, 'instruction': 'play the same-position A and F# cadence pair back to back',
                 'pair_contact_memberships': 12, 'numeric_clock_or_inter_cadence_gap': None},
                {'step': 2, 'instruction': 'ask a partner to call the destination at the last possible moment',
                 'eligible_destinations': ['A', 'F#'], 'selected_destination': None,
                 'partner_or_call_generated': False, 'numeric_call_time': None,
                 'both_branches_execute_automatically': False}],
            'ending_constraint': {'no_extra_notes_after_cadence': True,
                                  'postcadence_silence_required_qualitatively': True,
                                  'numeric_note_release_or_silence_duration': None},
            'conditional_repair': {'trigger': 'cadence feels added on', 'trigger_observed': False,
                'steps': [{'action': 'loop_final_two_notes_alone', 'contact_ordinals': [5, 6], 'repeat_count': None},
                          {'action': 'attach_only_last_two_seed_notes', 'contact_ordinals': [3, 4, 5, 6]}],
                'selected_numeric_clock': None, 'learner_branch_automatically_selected': False},
            'root_location_manual_duty': root_duty(), 'generated_new_notes': [],
            'selected_numeric_clock': None, 'numeric_acoustic_gates': None,
            'native_projection_complete': False, 'performance_or_credit_claimed': False}


def validate(candidate, source, partner=None, binding=None):
    expected = box(source) if partner is None else cadence(source, partner, binding)
    require(candidate == expected, 'Task contract differs from exact source-derived relationship')
    return True
