"""Pure symbolic ownership for the four Level48 ModuleB seams; no clock policy."""
import copy


def position(slot):
    return {k: slot[k] for k in ('bar', 'beat', 'phase')}


def build(record):
    impl = record['implementation']
    slots = impl['symbolic_count_slots']
    events = impl['sounding_events']
    if len(slots) != 32 or len(events) != 23:
        raise ValueError('Expected an exact four-bar ModuleB seam')
    expected_positions = [(bar, beat, phase) for bar in (1, 2, 3, 4) for beat in (1, 2, 3, 4) for phase in ('beat', 'offbeat')]
    if [(s['bar'], s['beat'], s['phase']) for s in slots] != expected_positions:
        raise ValueError('Source slot order/coverage differs')
    by_contacts = {}
    for e in events:
        key = tuple(e['source_contact_ordinals'])
        if key in by_contacts or not key:
            raise ValueError('Duplicate/empty sounding-event join')
        by_contacts[key] = e
    actions, segments, groups, seen = [], [], [], []
    current = None
    active_group = None
    previous_event = None

    def close_segment(at, reason):
        if current is not None:
            current['end_boundary'] = at
            current['end_reason'] = reason
            current['end_is_numeric_acoustic_noteoff'] = False

    def close_group(at, reason):
        if active_group is not None:
            active_group['logical_end_boundary'] = at
            active_group['logical_end_reason'] = reason
            active_group['source_requires_silence_at_end'] = reason == 'explicit_rest'

    for index, slot in enumerate(slots, 1):
        pos = position(slot)
        action = {'slot_ordinal': index, 'source_position': pos,
                  'source_count_line': slot['source_count_line'], 'source_attack_mark': slot['attack_mark']}
        if slot['kind'] == 'sounded':
            key = tuple(slot['source_contact_ordinals'])
            if key not in by_contacts or key in seen:
                raise ValueError('Sounded slot has no unique event')
            e = by_contacts[key]
            if e['relative_position'] != pos or e['source_note'] != slot['note']:
                raise ValueError('Source event/pitch/position mismatch')
            mark = slot['attack_mark']
            mapping = {'P': ('picked', True), 'h': ('hammer_on', False), 'p': ('pull_off', False), 's': ('slide_arrival', False)}
            if mark not in mapping or (e['attack'], e['pick_attack']) != mapping[mark]:
                raise ValueError('Attack mark differs from sounding action')
            if mark != 'P' and (current is None or previous_event is None or previous_event['string_label'] != e['string_label']):
                raise ValueError('Unpicked arrival has no active preceding same-string contact')
            close_segment(pos, 'new_picked_event' if mark == 'P' else 'legato_pitch_transition')
            if mark == 'P':
                close_group(pos, 'next_picked_attack')
                active_group = {'group_ordinal': len(groups) + 1, 'picked_event_ordinal': e['ordinal'],
                                'source_start': pos, 'member_event_ordinals': [], 'held_slot_ordinals': []}
                groups.append(active_group)
            active_group['member_event_ordinals'].append(e['ordinal'])
            current = {'event_ordinal': e['ordinal'], 'source_contact_ordinals': e['source_contact_ordinals'],
                       'source_start': pos, 'excitation_group_ordinal': active_group['group_ordinal'],
                       'held_slot_ordinals': [], 'numeric_onset': None, 'numeric_acoustic_gate': None}
            segments.append(current)
            action.update(kind=e['attack'], event_ordinal=e['ordinal'],
                          excitation_group_ordinal=active_group['group_ordinal'], new_pick_attack=mark == 'P',
                          preceding_event_ordinal=None if previous_event is None else previous_event['ordinal'])
            previous_event = e
            seen.append(key)
        elif slot['kind'] == 'hold':
            if slot['note'] != '=' or slot['attack_mark'] != '=' or slot['source_contact_ordinals'] or current is None:
                raise ValueError('Orphan or malformed hold')
            current['held_slot_ordinals'].append(index)
            active_group['held_slot_ordinals'].append(index)
            action.update(kind='hold', owner_event_ordinal=current['event_ordinal'],
                          excitation_group_ordinal=active_group['group_ordinal'], new_pick_attack=False)
        elif slot['kind'] == 'rest':
            if slot['note'] != 'r' or slot['attack_mark'] != 'r' or slot['source_contact_ordinals']:
                raise ValueError('Rest contains an attack/contact')
            close_segment(pos, 'explicit_rest')
            close_group(pos, 'explicit_rest')
            action.update(kind='explicit_silence', stopped_event_ordinal=None if current is None else current['event_ordinal'],
                          stopped_group_ordinal=None if active_group is None else active_group['group_ordinal'], new_pick_attack=False)
            current = active_group = previous_event = None
        else:
            raise ValueError('Unsupported source slot kind')
        actions.append(action)
    if len(seen) != len(events):
        raise ValueError('Source event omitted from slots')
    if current is not None:
        boundary = {'bar': 5, 'beat': 1, 'phase': 'beat'}
        close_segment(boundary, 'printed_scope_ends_release_unselected')
        close_group(boundary, 'printed_scope_ends_release_unselected')
    counts = {'sounding_events': len(events), 'picked_excitation_groups': len(groups),
              'unpicked_arrivals': sum(not e['pick_attack'] for e in events),
              'holds': sum(a['kind'] == 'hold' for a in actions),
              'rest_slots': sum(a['kind'] == 'explicit_silence' for a in actions)}
    if counts['picked_excitation_groups'] != impl['picked_attack_count']:
        raise ValueError('Printed picked-attack count differs')
    return {'schema_version': 'fathom-symbolic-source-actions.1', 'scope': 'written_four_bar_seam',
            'actions': actions, 'contact_segments': segments, 'picked_excitation_groups': groups,
            'counts': counts, 'source_gate_constraint':
            'Explicit r requires silence; = continues its preceding source event. Other segment ends describe pitch/action transitions and do not supply acoustic noteoffs.',
            'capabilities': {'source_slot_order_complete': True, 'hold_ownership_complete': True,
                'rest_boundaries_complete': True, 'unpicked_arrival_ownership_complete': True,
                'shuffle_ratio': None, 'numeric_onsets': None, 'numeric_acoustic_gates': None,
                'fixed_bpm': None, 'native_projection_complete': False, 'playback_available': False}}
