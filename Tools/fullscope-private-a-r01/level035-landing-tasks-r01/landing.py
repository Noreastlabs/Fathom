"""Printed landing-cell tasks; later mirror realization intentionally unselected."""


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def build(record):
    impl = record['implementation']
    route = impl['route_contract']
    require(record['level'] == 35 and route['family'] == 'destination_landings', 'Wrong source family')
    events = impl['ordered_contacts']
    require(len(events) == 16 and route['no_slide'] is True, 'Wrong printed landing scope')
    cells = []
    for index in range(4):
        group = events[index * 4:index * 4 + 4]
        launch, target, repeated, returned = group
        expected = route['targets'][index]
        physical = lambda event: (event['string_label'], event['fret'], event['midi'], event['note_spelling'], event['degree'])
        require(physical(target) == physical(repeated) and physical(launch) == physical(returned), 'Repeat or return physical identity changed')
        require(target['string_label'] == launch['string_label'] == route['launch']['string'], 'A landing moved to another string')
        require(launch['fret'] == route['launch']['fret'] and target['fret'] == expected['fret'] and target['note_spelling'] == expected['note'] and target['degree'] == expected['degree'], 'Wrong source destination')
        require(target['fret'] - launch['fret'] == expected['distance_frets'] > 0, 'Wrong source distance')
        for offset, event in enumerate(group):
            require(event['ordinal'] == index * 4 + offset + 1, 'Contact order changed')
            require(event['pick_attack'] is True and event['attack'] == 'picked' and event['finger'] == 1, 'First pass requires four separate finger-one picked contacts')
            require(event['onset_q'] is None and event['duration_q'] is None and event['acoustic_gate_q'] is None, 'Numeric clock or gate selected')
        cells.append({'cell_ordinal': index + 1, 'contact_ordinals': [e['ordinal'] for e in group],
            'source_roles': ['launch', 'direct_target', 'separately_repicked_target', 'return_launch'],
            'target': {k: expected[k] for k in ('note', 'degree', 'fret', 'distance_frets')},
            'first_target_contact': target['ordinal'], 'repeated_target_contact': repeated['ordinal'],
            'manual_predeparture_duty': 'name and look at the target before leaving the launch note',
            'look_or_accuracy_observed': False, 'four_distinct_picked_attacks': True})
    return {'schema_version': 'fathom-source-landing-task.1', 'string_label': route['launch']['string'],
        'selected_pass': 'printed_lower_endpoint_first_pass_finger_one', 'cells': cells,
        'picked_contact_count': 16, 'source_target_matching': {
            'literal_standard': 'The first target attack and repeated target must match in pitch, volume, and timing.',
            'qualitative_only': True, 'numeric_velocity_or_tolerance': None,
            'identical_absolute_onsets_required': False},
        'source_motion_constraint': {'no_slide_or_scrape': True, 'shift_must_not_be_audible': True,
            'inter_note_gap_may_be_silent': True, 'fixed_rest_events_generated': [], 'numeric_gap_or_gate': None},
        'later_mirror_duty': {
            'txt_instruction': 'After the printed pass, begin at the upper endpoint and mirror the target order downward.',
            'pdf_instruction': 'After the printed launch, begin at the upper endpoint and reverse the target order.',
            'source_duty_retained': True, 'selected': False, 'generated_contact_sequence': None,
            'selected_fingering': None, 'selected_numeric_clock': None,
            'source_conflict_adjudicated': False},
        'selected_numeric_clock': None, 'numeric_acoustic_gates': None,
        'native_projection_complete': False, 'learner_performance_or_credit_claimed': False}


def validate(candidate, source):
    require(candidate == build(source), 'Landing task differs from source-derived constraints')
    return True
