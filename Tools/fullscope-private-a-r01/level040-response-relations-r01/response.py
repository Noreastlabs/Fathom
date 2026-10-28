"""Printed phrase relationships; no inferred metric or acoustic realization."""
import re

NOTES = ['B', 'C#', 'E', 'C#', 'B', 'A', 'B', 'C#', 'E', 'C#', 'A', 'F#']
JOBS = ['9', '3', '5', '3', '9', 'R', '4', '5', 'b7', '5', 'b3', 'R']
DEGREES = ['4', '5', 'b7', '5', '4', 'b3', '4', '5', 'b7', '5', 'b3', '1']
PC = {'F#': 6, 'A': 9, 'B': 11, 'E': 4, 'C#': 1}
OPEN = {'E': 40, 'A': 45, 'D': 50, 'G': 55, 'B': 59, 'e': 64}


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def build(record):
    impl = record['implementation']
    require(record['level'] == 40 and impl['source_module'] == 'D', 'Wrong source family')
    match = re.fullmatch(r'P([1-5]) - CALL OVER A \| ANSWER OVER F#m', record['source_payload']['printed_label'])
    require(match is not None, 'Wrong source card')
    pos = int(match[1])
    identity = f'printed:l040:section-v:level-40:module-d-relative-center-responses:p{pos}-call-over-a-answer-over-f-m'
    require(record['source_identity'] == identity and record['package_key'] == 'proposed-' + identity.replace(':', '-'), 'Wrong finite identity')
    events = impl['ordered_contacts']
    require(len(events) == 12, 'Twelve printed contacts required')
    block = record['source_payload']['notation_blocks'][0]
    require(block['printed_rest_columns'] == [], 'No printed rest in these two phrases')
    notation = {r['label']: {t['column']: t['text'] for t in r['tokens']} for r in block['notation_rows']}
    physical = {c['column']: c for c in block['printed_contacts']}
    roles = []
    for i, event in enumerate(events):
        phase, slot = i // 6 + 1, i % 6 + 1
        column = (phase - 1) * 25 + (slot - 1) * 4
        chord = 'A' if phase == 1 else 'F#m'
        require(event['ordinal'] == i + 1 and event['source_group'] == phase and event['slot_in_group'] == slot and event['grid_column'] == column, 'Printed phrase ordering changed')
        require(event['note_spelling'] == NOTES[i] and event['harmonic_role'] == JOBS[i] and event['degree'] == DEGREES[i] and event['harmony'] == chord, 'Pitch or active-chord role changed')
        for label, expected in [('Nte', NOTES[i]), ('Job', JOBS[i]), ('F#m', DEGREES[i]), ('Chd', chord), ('Fng', str(event['finger']))]:
            require(notation[label][column] == expected and event['annotations'][label] == expected, 'Printed metadata differs from contact')
        p = physical[column]
        require(all(event[k] == p[k] for k in ['string_label', 'fret', 'source_line', 'source_column_1based']), 'Printed physical contact changed')
        require(event['midi'] == OPEN[event['string_label']] + event['fret'] and event['midi'] % 12 == PC[NOTES[i]], 'Wrong physical source pitch')
        require(event['completion_tone'] is False, 'No outside completion tone in response card')
        require(event['pick_attack'] is True and event['attack'] == 'picked' and event['technique_symbols'] == '', 'Selected existing plain pass changed')
        require(event['onset_q'] is None and event['duration_q'] is None and event['acoustic_gate_q'] is None, 'Clock or gate was selected')
        roles.append({'contact_ordinal': i + 1, 'phrase': 'call' if phase == 1 else 'answer',
                      'within_phrase_source_order': slot, 'note': NOTES[i], 'active_chord': chord,
                      'chord_role': JOBS[i], 'F_sharp_minor_degree': DEGREES[i],
                      'R_means_harmonic_root_not_rest': JOBS[i] == 'R'})
    shared = []
    for i in range(4):
        call, answer = events[i], events[i + 6]
        require(all(call[k] == answer[k] for k in ['note_spelling', 'midi', 'string_label', 'fret', 'finger']), 'Opening must preserve exact four physical contacts')
        shared.append({'call_ordinal': i + 1, 'answer_ordinal': i + 7,
                       'note': NOTES[i], 'midi': call['midi'], 'string_label': call['string_label'],
                       'fret': call['fret'], 'finger': call['finger'],
                       'call_chord_role': JOBS[i], 'answer_chord_role': JOBS[i + 6]})
    return {'schema_version': 'fathom-source-relative-center-response.1', 'position': f'P{pos}',
            'governing_workbook_tonic': 'F#', 'selected_pass': 'existing_plain_fretted_picked_pass',
            'phrases': [
                {'phase': 'call', 'source_order': 1, 'active_chord': 'A', 'contact_ordinals': list(range(1, 7)),
                 'ending_contact_ordinals': [5, 6], 'ending_notes': ['B', 'A'], 'final_root_contact': 6, 'final_root_note': 'A'},
                {'phase': 'answer', 'source_order': 2, 'active_chord': 'F#m', 'contact_ordinals': list(range(7, 13)),
                 'ending_contact_ordinals': [11, 12], 'ending_notes': ['A', 'F#'], 'final_root_contact': 12, 'final_root_note': 'F#'}],
            'shared_opening_joins': shared, 'contact_roles': roles,
            'source_task_duty': 'Make the A call and F#m answer sound related but differently centered; preserve the shared opening and redirect the ending to F#.',
            'perceived_centers_observed': None, 'source_task_completed': False,
            'phrase_boundary_meaning': 'Two printed six-contact phrases; bar duration and meter are not selected.',
            'time_unit': 'ordered source contacts and phrase groups; no numeric clock',
            'meter_numerator_denominator': None, 'quarter_unit_mapping': None,
            'selected_numeric_onsets': None, 'selected_numeric_acoustic_gates': None,
            'interphrase_silence_duration': None, 'numeric_velocity': None,
            'generated_accompaniment_events': [], 'generated_extra_events': [],
            'native_projection_complete': False, 'performance_or_credit_claimed': False}


def validate(candidate, source):
    require(candidate == build(source), 'Response contract differs from source-bound relationships')
    return True
