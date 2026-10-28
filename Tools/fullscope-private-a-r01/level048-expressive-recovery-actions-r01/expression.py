"""Only source bend constraints; never an invented sounding trajectory."""
import copy
OPEN = dict(zip('EADGBe', [40, 45, 50, 55, 59, 64]))


def constraint(event, mark):
    if mark not in ('b', 'b<'):
        raise ValueError('Not a printed expressive attack')
    if not event['pick_attack'] or event['selected_sounding_pitch_trajectory'] is not None or event['selected_fixed_playback_midi'] is not None:
        raise ValueError('Expressive source must remain picked with no selected sounding trajectory')
    if event['expressive_pitch_realization_complete'] is not False or event['numeric_onset_or_gate_selected'] is not False:
        raise ValueError('Unselected expression cannot claim numeric realization')
    source = OPEN[event['string_label']] + event['physical_fret']
    if source != event['physical_reference_midi']:
        raise ValueError('Physical source/reference MIDI differs')
    bend = event['bend']
    facts = event['source_pitch_constraints']
    if mark == 'b':
        if event['attack'] != 'picked_bend' or len(event['source_contact_ordinals']) != 2:
            raise ValueError('Full bend must retain one event and two source/reference fret tokens')
        if bend['source_fret'] != event['physical_fret'] or bend['target_pitch_equivalent_fret'] - bend['source_fret'] != 2:
            raise ValueError('Printed two-semitone endpoint changed')
        if event['pitch_encoding_midi'] != source + 2 or facts['target_midi'] != source + 2 or facts['source_midi'] != source:
            raise ValueError('Full-bend endpoint/source relation differs')
        if facts['continuous_curve'] is not None or facts['arrival_phase_within_source_slot'] is not None or bend['continuous_path_and_arrival_within_slot'] is not None:
            raise ValueError('No source bend curve or arrival phase has been selected')
    else:
        if event['attack'] != 'picked_blue_third_shade' or event['source_note'] != 'C~' or source % 12 != 0:
            raise ValueError('Blue-third shade must retain its physical C reference')
        if bend['direction'] != 'toward C#' or facts['direction'] != 'toward C#':
            raise ValueError('Printed shade direction changed')
        if any(x is not None for x in (bend['exact_cents'], facts['exact_cents'], facts['selected_midi'], facts['continuous_curve'])):
            raise ValueError('Printed shade supplies no exact extent or curve')
        if event['pitch_encoding_midi'] != source:
            raise ValueError('Shade reference scalar is not a selected altered pitch')
    return {'event_ordinal': event['ordinal'], 'kind': event['attack'], 'source_contact_ordinals': event['source_contact_ordinals'],
            'physical_reference_midi': source, 'pitch_encoding_role': event['pitch_encoding_role'],
            'source_constraints': copy.deepcopy(facts), 'source_bend_metadata': copy.deepcopy(bend),
            'one_picked_excitation': True, 'numeric_trajectory': None,
            'constant_source_or_target_scalar_playback_permitted': False, 'native_realization_complete': False}
