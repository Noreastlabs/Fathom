"""Describe only the eight printed seed/variant examples, without generating notes."""
def slot(e):
    p=e['relative_position']
    return (p['bar']-1)*8+(p['beat']-1)*2+(p['phase']=='offbeat')


def relation(seed,record,source_row):
    a=seed['implementation']['sounding_events'];b=record['implementation']['sounding_events']
    notes=lambda es:[e['source_note'] for e in es]
    positions=lambda es:[slot(e) for e in es]
    strikes=lambda es:[e['attack'] for e in es]
    physical=lambda es:[(e['string_label'],e['physical_fret'],e['pitch_encoding_midi']) for e in es]
    base={'schema_version':'fathom-printed-motif-relation.1',
          'seed_package_key':seed['package_key'],'variant_package_key':record['package_key'],
          'description_scope':'exact source examples, not a general automatic transformation generator',
          'source_instruction':record['source_payload']['printed_label'],
          'source_seed_notes':notes(a),'source_variant_notes':notes(b),
          'source_seed_slot_ordinals_0based':positions(a),'source_variant_slot_ordinals_0based':positions(b),
          'numeric_elapsed_shift':None,'shuffle_ratio':None,'new_source_events_generated':False,
          'performance_or_credit_claimed':False}
    if source_row==10:
        assert record['package_key']==seed['package_key']
        base.update(kind='printed_seed',recognized_opening_event_ordinals=[1,2])
    elif source_row==11:
        assert notes(a)==notes(b) and positions(a)==positions(b) and strikes(a)==strikes(b) and physical(a)==physical(b)
        base.update(kind='exact_echo',seed_to_variant_event_pairs=[[i,i] for i in range(1,7)])
    elif source_row==12:
        assert notes(a)==notes(b) and physical(a)==physical(b) and strikes(a)==strikes(b)
        assert all(slot(y)-slot(x)==1 for x,y in zip(a,b))
        base.update(kind='one_printed_subdivision_displacement',printed_slot_delta=1,
                    constant_elapsed_duration_claimed=False,seed_to_variant_event_pairs=[[i,i] for i in range(1,7)],
                    initial_rest_introduced=True,final_seed_rest_not_carried_outside_printed_bar=True)
    elif source_row==13:
        assert notes(b)==list(reversed(notes(a))) and physical(b)==list(reversed(physical(a)))
        base.update(kind='printed_contour_reversal',seed_to_variant_event_pairs=[[7-i,i] for i in range(1,7)],
                    articulation_is_independently_printed=True,original_pick_vector_reversed=False)
    elif source_row==14:
        assert notes(a)==notes(b) and positions(a)==positions(b)
        deltas=[y['pitch_encoding_midi']-x['pitch_encoding_midi'] for x,y in zip(a,b)]
        assert deltas==[24,24,24,24,24,12]
        base.update(kind='printed_register_shift',seed_to_variant_event_pairs=[[i,i] for i in range(1,7)],
                    per_event_semitone_changes=deltas,uniform_octave_transpose=False,
                    source_articulation_changes=[{'event_ordinal':i,'seed':x['attack'],'variant':y['attack']}
                        for i,(x,y) in enumerate(zip(a,b),1) if x['attack']!=y['attack']])
    elif source_row==15:
        assert positions(a)==positions(b) and notes(b)==['A','B','C#','E','F#','G']
        base.update(kind='printed_major_minor_recolor',rhythmic_slot_pattern_preserved=True,
                    pitch_replacements=[{'event_ordinal':i,'seed':x['source_note'],'variant':y['source_note']}
                        for i,(x,y) in enumerate(zip(a,b),1) if x['source_note']!=y['source_note']],
                    source_articulation_independently_printed=True)
    elif source_row==16:
        assert notes(b)==notes(a)+['A','C'] and positions(b)==list(range(8))
        assert physical(a)==physical(b[:6])
        base.update(kind='printed_expansion',opening_event_ordinals_retained=[1,2],
                    original_seed_events_preserved_in_order=True,seed_to_variant_event_pairs=[[i,i] for i in range(1,7)],
                    retimed_seed_event_ordinals=[i for i,(x,y) in enumerate(zip(a,b),1) if slot(x)!=slot(y)],
                    source_added_tail_event_ordinals=[7,8],numeric_onset_shift_claimed=False)
    elif source_row==17:
        assert notes(b)==['A','C#','A'] and positions(b)==[0,2,4]
        base.update(kind='printed_reduction_with_major_third_answer',source_function_sequence=['tonic','major-third answer','final tonic'],
                    literal_seed_subsequence=False,new_C_sharp_is_printed_not_generated=True,
                    discarded_seed_event_mapping_not_invented=True)
    else:
        raise ValueError('Not one of the eight finite printed motif examples')
    return base
