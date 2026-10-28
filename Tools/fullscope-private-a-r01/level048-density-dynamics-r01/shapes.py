"""Finite printed density and qualitative dynamics, with no audio realization."""
import re


def density(record, source_row, sparse):
    levels = {18: ('sparse', 3), 19: ('medium', 5), 20: ('dense', 7)}
    if source_row not in levels:
        raise ValueError('Outside three source density cards')
    name, count = levels[source_row]
    events = record['implementation']['sounding_events']
    bars = []
    for bar in range(1, 5):
        found = [e for e in events if e['relative_position']['bar'] == bar]
        if len(found) != count:
            raise ValueError('Source sounding-tone density differs')
        start = [e for e in found if e['relative_position']['beat'] == 1 and e['relative_position']['phase'] == 'beat']
        if len(start) != 1:
            raise ValueError('Expected a single printed bar downbeat')
        bars.append({'bar': bar, 'sounding_event_count': len(found),
                     'picked_attack_count': sum(e['pick_attack'] for e in found),
                     'source_event_ordinals': [e['ordinal'] for e in found],
                     'downbeat': {'event_ordinal': start[0]['ordinal'], 'note': start[0]['source_note'],
                                  'harmonic_role': start[0]['harmonic_role']}})
    base = [e['source_note'] for e in sparse['implementation']['sounding_events']
            if e['relative_position']['beat'] == 1 and e['relative_position']['phase'] == 'beat']
    actual = [b['downbeat']['note'] for b in bars]
    if base != ['A', 'F#', 'G#', 'A'] or actual != (['A', 'F#', 'G', 'A'] if source_row == 20 else base):
        raise ValueError('Printed density downbeat sequence differs')
    comparison = {'baseline_package_key': sparse['package_key'], 'baseline_downbeat_notes': base,
                  'actual_downbeat_notes': actual, 'same_downbeat_pitch_sequence': actual == base,
                  'status': 'SOURCE_GUIDANCE_RECONCILIATION_PENDING' if actual != base else 'SOURCE_TARGETS_AGREE',
                  'source_pitch_or_timing_repair_applied': False}
    if actual != base:
        arrival = [e for e in events if e['relative_position'] == {'bar': 3, 'beat': 1, 'phase': 'offbeat'}]
        if len(arrival) != 1 or arrival[0]['source_note'] != 'G#' or arrival[0]['attack'] != 'slide_arrival' or arrival[0]['pick_attack']:
            raise ValueError('Printed G-to-G# unpicked arrival differs')
        comparison.update(source_instruction=record['source_payload']['printed_label'],
                          written_bar3_downbeat=bars[2]['downbeat'],
                          written_target_arrival={'event_ordinal': arrival[0]['ordinal'], 'note': 'G#',
                              'position': arrival[0]['relative_position'], 'new_pick_attack': False},
                          unresolved_question='Dense instruction preserves the target schedule, but G# arrives offbeat rather than on the sparse/medium downbeat. No correction or interpretation is selected.')
    return {'schema_version': 'fathom-source-density-contract.1', 'level': name,
            'source_tones_per_bar': count, 'bars': bars, 'source_position_route': ['P1', 'P2', 'P3', 'P1'],
            'target_comparison': comparison, 'count_empty_subdivisions': True,
            'maintain_pulse_while_changing_density': True, 'numeric_clock_selected': False,
            'generated_events': False, 'performance_or_credit_claimed': False}


def dynamics(record, source_row, action_contract):
    schedules = {21: ['p', 'f'], 22: ['p', 'p', 'mf', 'mf', 'f', 'f'], 23: ['f', 'mf', 'mp', 'p']}
    routes = {21: ['P1', 'P2'], 22: ['P1', 'P3', 'P5'], 23: ['P5', 'P4', 'P3', 'P1']}
    spans = {21: [[1], [2]], 22: [[1, 2], [3, 4], [5, 6]], 23: [[1], [2], [3], [4]]}
    if source_row not in schedules:
        raise ValueError('Outside three source dynamic-shape cards')
    lines = [s for s in record['source_payload']['exact_unit_lines'] if s.startswith('Dyn|')]
    if len(lines) != 1:
        raise ValueError('Expected exactly one original dynamic row')
    parts = lines[0].split('|')[1:]
    if len(parts) != len(schedules[source_row]):
        raise ValueError('Dynamic bar count differs')
    slots = record['implementation']['symbolic_count_slots']
    actions = action_contract['actions']
    bindings = []
    for bar, (part, expected) in enumerate(zip(parts, schedules[source_row]), 1):
        marks = {}
        for match in re.finditer(r'[^-]+', part):
            if match.start() % 4 or match.group() not in ('p', 'mp', 'mf', 'f'):
                raise ValueError('Unsupported or unaligned printed dynamic')
            local = match.start() // 4
            if local > 7 or match.group() != expected:
                raise ValueError('Dynamic disagrees with explicit source shape')
            marks[local] = match.group()
        for local, slot in enumerate(slots[(bar - 1) * 8:bar * 8]):
            action = actions[(bar - 1) * 8 + local]
            if slot['kind'] == 'rest':
                if local in marks:
                    raise ValueError('Rest has a printed dynamic attack binding')
                continue
            if local not in marks:
                raise ValueError('Source sounding/held slot has no dynamic marker')
            bindings.append({'source_position': action['source_position'], 'qualitative_dynamic': marks[local],
                             'event_ordinal': action.get('event_ordinal', action.get('owner_event_ordinal')),
                             'binding_kind': 'held_event' if slot['kind'] == 'hold' else 'sounding_event',
                             'new_pick_attack': action['new_pick_attack'],
                             'numeric_velocity': None, 'numeric_amplitude': None, 'acoustic_envelope': None})
    return {'schema_version': 'fathom-source-qualitative-dynamics.1', 'source_instruction': record['source_payload']['printed_label'],
            'bar_dynamics': [{'bar': i, 'mark': mark} for i, mark in enumerate(schedules[source_row], 1)],
            'phrases': [{'source_bars': bars, 'source_position': route} for bars, route in zip(spans[source_row], routes[source_row])],
            'slot_bindings': bindings, 'maintain_subdivision_and_pulse': True,
            'numeric_velocity_mapping': None, 'numeric_amplitude_curve': None, 'shuffle_ratio': None,
            'source_dynamics_are_performance_instructions': True, 'performance_or_credit_claimed': False}
