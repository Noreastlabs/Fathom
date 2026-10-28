"""Source bar roles and target joins, without generating a musical realization."""
import re
FORM = ['A7', 'A7', 'A7', 'A7', 'D7', 'D7', 'A7', 'A7', 'E7', 'D7', 'A7', 'E7']
ROLES = {'root': ['R'], 'third': ['3', '3*'], 'fifth': ['5'], 'flat seventh': ['b7']}


def build(record, source_row):
    if source_row not in (24, 26):
        raise ValueError('Outside the two printed model choruses')
    headings = [s for s in record['source_payload']['exact_unit_lines'] if s.startswith('BAR ')]
    if len(headings) != 12:
        raise ValueError('Expected twelve source bar headings')
    events = record['implementation']['sounding_events']
    bars = []
    for number, heading in enumerate(headings, 1):
        match = re.fullmatch(r'BAR (\d+) - (A7|D7|E7) (CALL|RESPONSE|ANSWER|TURNAROUND) - (P[1-5]) - beat-1 target ([A-G](?:#|b)?) (root|third|fifth|flat seventh)', heading)
        if not match or int(match[1]) != number or match[2] != FORM[number - 1]:
            raise ValueError('Printed twelve-bar form/order differs')
        local = [e for e in events if e['relative_position']['bar'] == number]
        target = [e for e in local if e['relative_position']['beat'] == 1 and e['relative_position']['phase'] == 'beat']
        if len(target) != 1 or target[0]['source_note'] != match[5] or target[0]['harmonic_role'] not in ROLES[match[6]]:
            raise ValueError('Beat-one source target differs from written sounding event')
        if source_row == 24 and any(e['source_note'] not in ('A', 'C', 'D', 'E', 'G') for e in local):
            raise ValueError('Minor-only source model contains an outside pitch')
        if source_row == 26 and any(e['source_note'] == 'G#' and match[2] != 'E7' for e in local):
            raise ValueError('G# completion tone appears outside its source E7 scope')
        bars.append({'bar': number, 'chord': match[2], 'phrase_role': match[3], 'position': match[4],
                     'source_heading': heading, 'beat_one_target': {'source_note': match[5], 'role_text': match[6],
                         'event_ordinal': target[0]['ordinal'], 'source_harmonic_role': target[0]['harmonic_role']},
                     'source_event_ordinals': [e['ordinal'] for e in local], 'sounding_tone_count': len(local),
                     'picked_attack_count': sum(e['pick_attack'] for e in local)})
    return {'schema_version': 'fathom-source-model-chorus-contract.1',
            'module': 'F' if source_row == 24 else 'H', 'source_form': FORM, 'bars': bars,
            'pitch_pool_constraint': 'A C D E G only' if source_row == 24 else 'Major/minor source mixture; G# only over E7. F# over A7 is printed as13 and is retained.',
            'source_constraints_observed_in_printed_model': True,
            'source_instruction_is_not_learner_performance': True,
            'free_capstone_density_and_position_constraints_are_separate': True,
            'capstone_completed_or_qualified': False, 'numeric_shuffle_ratio': None,
            'numeric_onsets': None, 'numeric_acoustic_gates': None,
            'automatic_reentry_or_new_chorus_generated': False, 'performance_or_credit_claimed': False}
