"""Literal model targets and conditional source recovery examples."""
import re
FORM = ['A7', 'A7', 'A7', 'A7', 'D7', 'D7', 'A7', 'A7', 'E7', 'D7', 'A7', 'E7']


def event_ref(event):
    return {'event_ordinal': event['ordinal'], 'note': event['source_note'], 'position': event['relative_position'],
            'source_harmonic_role': event['harmonic_role'], 'new_pick_attack': event['pick_attack']}


def model(record):
    headings = [s for s in record['source_payload']['exact_unit_lines'] if s.startswith('BAR ')]
    if len(headings) != 12:
        raise ValueError('Expected twelve exact modelG headings')
    events = record['implementation']['sounding_events']
    bars, mismatches = [], []
    for n, heading in enumerate(headings, 1):
        match = re.fullmatch(r'BAR (\d+) - (A7|D7|E7) (CALL|RESPONSE|ANSWER|TURNAROUND) - (P[1-5]) - beat-1 target ([ADE]) root', heading)
        if not match or int(match[1]) != n or match[2] != FORM[n - 1]:
            raise ValueError('Source modelG bar form changed')
        local = [e for e in events if e['relative_position']['bar'] == n]
        downbeat = [e for e in local if e['relative_position']['beat'] == 1 and e['relative_position']['phase'] == 'beat']
        targets = [e for e in local if e['source_note'] == match[5]]
        if len(downbeat) != 1 or not targets:
            raise ValueError('Printed downbeat/target notes are incomplete')
        value = {'bar': n, 'chord': match[2], 'phrase_role': match[3], 'position': match[4],
                 'source_heading': heading, 'declared_beat_one_target': match[5],
                 'written_downbeat': event_ref(downbeat[0]), 'written_target_occurrences': [event_ref(e) for e in targets],
                 'target_is_on_beat_one': downbeat[0]['source_note'] == match[5]}
        if not value['target_is_on_beat_one']:
            mismatches.append({'bar': n, 'source_heading': heading, 'written_downbeat': value['written_downbeat'],
                               'written_target_occurrences': value['written_target_occurrences'],
                               'status': 'SOURCE_GUIDANCE_RECONCILIATION_PENDING', 'source_pitch_or_timing_repair_applied': False})
        bars.append(value)
    if [x['bar'] for x in mismatches] != [2, 4, 6, 8] or [x['written_downbeat']['note'] for x in mismatches] != ['G', 'G', 'C', 'G']:
        raise ValueError('Exact retained source target discrepancies differ')
    return {'schema_version': 'fathom-expressive-source-model.1', 'module': 'G', 'bars': bars,
            'source_guidance_reconciliation': mismatches, 'source_articulation_pulse_duty': 'Do not hide the barline or target.',
            'fixed_expressive_pitch_trajectory_selected': False, 'performance_or_credit_claimed': False}


def recovery(record, row, actions):
    events = record['implementation']['sounding_events']
    notes = [e['source_note'] for e in events]
    result = {'schema_version': 'fathom-written-recovery-contract.1',
        'source_instruction': record['source_payload']['printed_label'], 'trigger': 'source conditional/manual recovery example',
        'trigger_observed': False, 'automatic_error_detection': False, 'automatic_branch_selection': False,
        'actual_source_event_sequence': [event_ref(e) for e in events], 'fixed_bpm_or_timing_tolerance': None,
        'numeric_acoustic_or_pitch_release_curve': None, 'performance_or_credit_claimed': False}
    if row in (45, 46, 47):
        expected = {45: ('C', 'C#', 1), 46: ('G', 'F#', -1), 47: ('G', 'G#', 1)}[row]
        if tuple(notes[:2]) != expected[:2] or events[1]['pitch_encoding_midi'] - events[0]['pitch_encoding_midi'] != expected[2]:
            raise ValueError('Written semitone recovery differs')
        if events[0]['string_label'] != events[1]['string_label'] or events[1]['attack'] != 'slide_arrival' or events[1]['pick_attack']:
            raise ValueError('Recovery resolution must remain its printed unpicked slide')
        result.update(kind='written_semitone_resolution', source_event_ordinal=1, resolution_event_ordinal=2,
                      source_semitone_delta=expected[2], preserve_counted_pulse=True)
    elif row == 48:
        if notes != ['C#', 'A'] or events[0]['relative_position'] != {'bar': 1, 'beat': 3, 'phase': 'beat'}:
            raise ValueError('Late-response written target/resolution differs')
        result.update(kind='late_response_reduce', selected_printed_target_event=1, printed_tonic_resolution_event=2,
                      initial_rest_slot_ordinals=[1, 2, 3, 4], no_resolution_attack_removed=True)
    elif row == 49:
        if notes != ['C~', 'C', 'C#', 'E', 'A'] or (events[0]['string_label'], events[0]['physical_fret']) != (events[1]['string_label'], events[1]['physical_fret']):
            raise ValueError('Missed-shade physical-source return changed')
        if not all(e['pick_attack'] for e in events) or 'expressive_source_constraint' not in actions['actions'][0]:
            raise ValueError('Source return/continuation picked actions differ')
        result.update(kind='missed_shade_source_return', expressive_event=1, source_return_event=2,
                      major_third_resolution_event=3, source_return_has_printed_new_pick=True,
                      forcing_unselected_bend_not_required=True)
    elif row == 50:
        if notes != ['A', 'A', 'E', 'A']:
            raise ValueError('Printed tonic-reset example changed')
        result.update(kind='lost_position_tonic_reset', printed_tonic_reset_event=1,
                      general_any_A_choice_unselected=True, general_nearest_secure_frame_choice_unselected=True,
                      printed_example_not_unique_required_route=True)
    else:
        raise ValueError('Outside six written recovery cells')
    return result
