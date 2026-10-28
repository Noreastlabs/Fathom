"""Exact source ending/entry relationships; no continuation event generator."""


def scalar(event):
    return {'event_ordinal': event['ordinal'], 'note': event['source_note'],
            'position': event['relative_position'], 'source_midi': event['pitch_encoding_midi']}


def build(record, row, actions):
    if row not in range(27, 33):
        raise ValueError('Outside six printed turnaround cards')
    events = record['implementation']['sounding_events']
    slots = record['implementation']['symbolic_count_slots']
    bars = {n: [e for e in events if e['relative_position']['bar'] == n] for n in (1, 2)}
    instruction = record['source_payload']['printed_label']
    base = {'schema_version': 'fathom-source-turnaround-contract.1', 'source_instruction': instruction,
            'source_closing_guidance': record['source_payload']['exact_unit_lines'][-1],
            'written_bars': 2, 'next_chorus_event_generated': False, 'performance_or_credit_claimed': False,
            'numeric_shuffle_ratio': None, 'numeric_acoustic_gates': None}
    if row == 27:
        if events[-1]['source_note'] != 'A' or slots[-1]['kind'] != 'rest':
            raise ValueError('Printed final tonic close changed')
        base.update(kind='tonic_close', final_destination=scalar(events[-1]),
                    begin_another_chorus=False, explicit_final_rest=True)
    elif row == 28:
        if any(e['source_note'] in ('G#', 'B') for e in bars[1]) or bars[2][0]['source_note'] != 'G#' or events[-1]['source_note'] != 'E':
            raise ValueError('E7 entry or final E changed')
        base.update(kind='low_E7_reentry', E7_entry_source_bar=2, final_destination=scalar(events[-1]),
                    next_chorus_tonic_expectation='A', next_chorus_actual_pitch_route_and_onset_unselected=True)
    elif row == 29:
        if events[0]['source_note'] != 'C#' or [e['source_note'] for e in bars[2][:2]] != ['D', 'G#']:
            raise ValueError('Written guide-tone relationship changed')
        base.update(kind='guide_tone_turn', source_guide=scalar(events[0]),
                    destination_guides=[scalar(e) for e in bars[2][:2]],
                    source_roles=['3 of A7', 'b7 of E7', '3 of E7'])
    elif row == 30:
        blues = [e for e in events if e['source_note'] == 'Eb']
        if len(blues) != 1 or blues[0]['relative_position']['bar'] != 1 or bars[2][0]['source_note'] != 'G#':
            raise ValueError('Blue-note/E7 source relationship changed')
        segment = next(s for s in actions['contact_segments'] if s['event_ordinal'] == blues[0]['ordinal'])
        if segment['end_reason'] != 'legato_pitch_transition' or segment['end_boundary']['bar'] != 1:
            raise ValueError('Eb source action does not resolve before E7')
        base.update(kind='high_blues_turn', blue_note=scalar(blues[0]), E7_entry=scalar(bars[2][0]),
                    source_gate_constraint='Do not sustain Eb across the E7 downbeat.',
                    Eb_symbolic_pitch_end=segment['end_boundary'], numeric_Eb_release_curve=None)
    elif row == 31:
        if [e['source_note'] for e in bars[2]] != ['G#', 'B'] or [e['relative_position'] for e in bars[2]] != [
                {'bar': 2, 'beat': 4, 'phase': 'beat'}, {'bar': 2, 'beat': 4, 'phase': 'offbeat'}]:
            raise ValueError('Exact two-note stop-time pickup changed')
        rest_positions = [s for s in slots[4:14] if s['kind'] == 'rest']
        if len(rest_positions) != 10:
            raise ValueError('Counted source silence changed')
        base.update(kind='stop_time_reentry', first_bar_beat4_empty=True,
                    counted_silence_slot_ordinals=list(range(5, 15)), written_pickup_events=[scalar(e) for e in bars[2]],
                    instruction_scope_note='Literal wording retained; bar1 beat4 is empty, while bar2 has a beat4 G# attack and an offbeat B attack. Neither attack is removed or retimed.',
                    constant_elapsed_silence_duration=None)
    else:
        approach = [e for e in events if e['source_note'] == 'F']
        if len(approach) != 1:
            raise ValueError('Expected one printed chromatic F')
        f = approach[0]
        e = events[f['ordinal']]
        if e['source_note'] != 'E' or f['string_label'] != 'A' or e['string_label'] != 'A' or (f['physical_fret'], e['physical_fret']) != (8, 7) or e['attack'] != 'slide_arrival' or e['pick_attack']:
            raise ValueError('Written same-string F8-to-E7 unpicked approach changed')
        delta = e['pitch_encoding_midi'] - f['pitch_encoding_midi']
        if delta != -1:
            raise ValueError('Printed chromatic approach no longer descends one semitone')
        base.update(kind='chromatic_V_approach', approach_event=scalar(f), arrival_event=scalar(e),
                    source_support_note_not_new_scale_degree=True, emitted_semitone_delta=delta,
                    source_guidance_reconciliation={
                        'status': 'SOURCE_GUIDANCE_RECONCILIATION_PENDING',
                        'source_direction_wording': 'one-time lower approach to E',
                        'printed_physical_relation': 'F on A-string fret8 to E on A-string fret7; approach F is one semitone above E',
                        'source_pitch_or_wording_repair_applied': False,
                        'disposition': 'Preserve literal text and traversal; Curriculum source-wording reconciliation pending.'})
    return base
