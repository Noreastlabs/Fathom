"""Source beat anchors and harmonic duties without a complete metric realization."""
import re

POOL = ['F#', 'A', 'B', 'C#', 'E']
NOTES = ['D', 'F#', 'A', 'F#', 'G#', 'B', 'E', 'B', 'F#', 'A', 'C#', 'F#']
JOBS = ['R', '3', '5', '3', '3', '5', 'R', '5', 'R', 'b3', '5', 'R']
DEGREES = ['*', '1', 'b3', '1', '*', '4', 'b7', '4', '1', 'b3', '5', '1']
PC = {'D': 2, 'F#': 6, 'A': 9, 'G#': 8, 'B': 11, 'E': 4, 'C#': 1}
OPEN = {'E': 40, 'A': 45, 'D': 50, 'G': 55, 'B': 59, 'e': 64}


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def build(record):
    impl = record['implementation']
    require(record['level'] == 40 and impl['source_module'] == 'E', 'Wrong source family')
    match = re.fullmatch(r'P([1-5]) - \| D \| E \| F#m \|', record['source_payload']['printed_label'])
    require(match is not None, 'Wrong source card')
    pos = int(match[1])
    events = impl['ordered_contacts']
    require(len(events) == 12, 'Twelve printed contacts required')
    roles, anchors = [], []
    for i, event in enumerate(events):
        bar, slot = i // 4 + 1, i % 4 + 1
        harmony = ['D', 'E', 'F#m'][bar - 1]
        require(event['ordinal'] == i + 1 and event['source_group'] == bar and event['slot_in_group'] == slot, 'Printed contact grouping changed')
        require(event['note_spelling'] == NOTES[i] and event['harmonic_role'] == JOBS[i] and event['degree'] == DEGREES[i], 'Pitch/role/completion degree mismatch')
        require(event['harmony'] == harmony, 'Wrong active chord')
        require(event['midi'] == OPEN[event['string_label']] + event['fret'] and event['midi'] % 12 == PC[NOTES[i]], 'Wrong physical source pitch')
        require(event['completion_tone'] is (i in [0, 4]), 'Wrong outside tone')
        require(event['pick_attack'] is True and event['attack'] == 'picked', 'Direct fretted pass requires source picked contacts')
        require(event['onset_q'] is None and event['duration_q'] is None and event['acoustic_gate_q'] is None, 'Clock or gate was selected')
        roles.append({'contact_ordinal': i + 1, 'bar': bar, 'within_bar_source_order': slot,
                      'source_beat': 1 if slot == 1 else None,
                      'note': NOTES[i], 'active_chord': harmony, 'chord_role': JOBS[i],
                      'pentatonic_degree': DEGREES[i], 'outside_completion_tone': i in [0, 4],
                      'R_means_harmonic_root_not_rest': JOBS[i] == 'R'})
        if slot == 1:
            anchors.append({'bar': bar, 'source_beat': 1, 'contact_ordinal': i + 1,
                            'note': NOTES[i], 'active_chord': harmony, 'quarter_onset': None})
    result = {'schema_version': 'fathom-source-completion-cadence.1', 'position': f'P{pos}',
              'governing_tonic': 'F#', 'pentatonic_pool': POOL,
              'selected_pass': 'direct_fretted_source_first_pass',
              'direct_pass_contacts': list(range(1, 13)), 'contact_roles': roles,
              'explicit_source_beat_one_anchors': anchors,
              'remaining_contact_beats_selected': False, 'time_unit': 'source bar and beat; complete metric projection unselected',
              'meter_numerator_denominator': None, 'quarter_unit_mapping': None,
              'completion_targets': [
                  {'contact_ordinal': index + 1, 'note': NOTES[index],
                   'string_label': events[index]['string_label'], 'fret': events[index]['fret'],
                   'finger': events[index]['finger'], 'chord': events[index]['harmony'],
                   'role': JOBS[index], 'new_pentatonic_degree': False,
                   'return_to_pool_contact_ordinal': index + 2, 'return_note': NOTES[index + 1]}
                  for index in [0, 4]],
              'intonation_duty': 'Fret D and G# cleanly before using bends or slides; a vague approximation is not a precisely targeted chord tone.',
              'conditional_blur_repair': {'trigger': 'completion tone blurs', 'trigger_observed': False,
                                         'action': 'fret D or G# directly before sliding or bending',
                                         'automatic_branch_execution': False},
              'final_source_contact': {'ordinal': 12, 'note': 'F#', 'active_chord': 'F#m', 'role': 'R'},
              'selected_numeric_onsets': None, 'selected_numeric_acoustic_gates': None,
              'native_projection_complete': False, 'generated_extra_events': [],
              'performance_or_credit_claimed': False}
    if pos >= 3:
        result['later_source_pass'] = {
            'source': 'original PDF physical page 13, per-position Pass 2',
            'required_source_duty': 'approach one completion tone by a slide while preserving its beat-1 arrival',
            'eligible_completion_contact_ordinals': [1, 5], 'completion_tones_to_approach': 1,
            'selected_completion_contact': None, 'selected_approach_origin': None,
            'selected_approach_finger_or_attack': None, 'selected_curve_or_start_time': None,
            'destination_beat_one_required': True, 'source_pass_completed': False,
            'generated_approach_events': [], 'selected': False}
    else:
        result['later_source_pass'] = None
        result['later_pass_scope_note'] = 'The explicit page 13 second-pass prescription belongs to P3–P5; it is not imposed on P1–P2 by analogy.'
    return result


def validate(candidate, source):
    require(candidate == build(source), 'Completion task differs from source-bound contract')
    return True
