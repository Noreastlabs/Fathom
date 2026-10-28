#!/usr/bin/env python3
"""Factored, source-bound Level100 A–G DATA. No native factory admission.

64 exact source bindings share ten finite programs. Musical realization remains
learner authorship; known source literals and manual reports have separate roles.
"""
import argparse,copy,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SELECTION=ROOT/'Build/manager-resume-r03/manual-composition64-r01/selection.json'
SELECTION_SHA='d87e503c46f80ea8b86228bae1f13f130a4650b034dccd53621b763d713d8e9f'
COMMON_PARAMETERS={'constraint_text','constraint_instruction','constraint_schema','constraint_expected','constraint_guards'}
PROGRAM_PARAMETERS={'motif_seed':{'degrees','rhythm'},'rhythm_motif':{'rhythm'},'transformation':{'keep','change'},'harmony_first':set(),'melody_first':set(),'bass_first':set(),'independence':set(),'rhythm_first':set(),'fixed_harmony':set(),'constraint_lab':{'starting_method'}}
def compact(v):return json.dumps(v,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()
def sha(v):return hashlib.sha256(v).hexdigest()
def pin(p):
 raw=p.read_bytes();return dict(path=str(p.relative_to(ROOT)),bytes=len(raw),sha256=sha(raw))
def read_ref(ref):
 p=ROOT/ref['path'];assert not p.is_symlink() and pin(p)=={k:ref[k] for k in ['path','bytes','sha256']};return p.read_bytes()
def param(name):return {'$parameter':name}
def text(limit=2048,nullable=True):return dict(type=['string','null'] if nullable else 'string',minLength=1,maxLength=limit,input_role='manual_report')
def boolean():return dict(type=['boolean','null'],input_role='manual_report')
def integer(lo,hi):return dict(type=['integer','null'],minimum=lo,maximum=hi,input_role='manual_report')
def enumeration(values):return dict(type=['string','null'],enum=values+[None],input_role='manual_report')
def source(value):return dict(const=value,input_role='source_binding',source_constant=True)
def schema(fields):return dict(type='object',properties=fields,required=list(fields),additionalProperties=False)
def nonempty(field,limit=4096):return dict(kind='nonempty_trimmed_text',field=field,minimum=1,maximum=limit)
def same(field,record,oldfield):return dict(kind='same_as_saved',left=dict(scope='payload',path=[field]),right=dict(scope='saved',path=[record,oldfield]))
def different(a,b):return dict(kind='different',fields=[a,b])
def report(instruction,fields,expected=None,guards=None,physical=False,save=None,next='end'):
 guards=copy.deepcopy(guards or []);manual=[key for key,value in fields.items() if value.get('input_role')=='manual_report'];guards.append(dict(kind='required_manual_fields_resolved',fields=manual))
 guarded={g.get('field') for g in guards if g['kind']=='nonempty_trimmed_text'}
 for key,value in fields.items():
  if value.get('minLength') and key not in guarded:guards.append(nonempty(key,value['maxLength']))
 return dict(kind='report',action='submit',instruction=instruction,schema=schema(fields),expected=expected or {},constraints=guards,save_as=save,physical=physical,pass_tag=None,next=next,completion_effects=[])
def choice(instruction,field,values,routes):
 return dict(kind='choice',action='choose',instruction=instruction,schema=schema({field:dict(type='string',enum=values,input_role='manual_report')}),expected={},constraints=[],route_field=field,routes={key:dict(next=value) for key,value in routes.items()},save_as=None,physical=False,completion_effects=[])
def graph(name,nodes,entry):
 nodes['end']=dict(kind='end',instruction='This source-specific procedure has manual reports only; it establishes no observed performance or whole-workbook completion.')
 return dict(name=name,manual_only=True,fixed_bpm=None,performance_observed=False,grants_credit=False,automatic_mastery=False,runtime_admitted=False,hidden_self_check=None,steps=[],graph=dict(entry=entry,nodes=nodes,domains={}),unknown_or_negative='retain raw report; diagnose; native retry/cancel/navigation must preserve history and discharge explicit owned release; never infer playing or hearing')
def constraint_node(next='end'):
 return dict(kind='report',action='submit',instruction=param('constraint_instruction'),schema=param('constraint_schema'),expected=param('constraint_expected'),constraints=param('constraint_guards'),save_as='constraint_report',physical=False,pass_tag=None,next=next,completion_effects=[])
def performance(instruction,fields,next='end',guards=None,save=None):
 fields={'own_source_performance_reported':boolean(),**fields};expected={'own_source_performance_reported':True};expected.update({key:True for key,value in fields.items() if value.get('type')==['boolean','null']})
 return report(instruction,fields,expected,guards,True,save=save,next=next)
def programs():
 out={}
 n={
 'sing':performance('Sing the printed contour and rhythm before choosing a key. No key choice is exposed until your own positive report.',{'contour_and_rhythm_sung':boolean()},next='realization'),
 'realization':report('Now choose a key and write two register realizations of the exact source seed. Key, pitches, frets and timing are learner choices, not generated source facts.',{'chosen_key':text(),'source_degrees':source(param('degrees')),'source_rhythm':source(param('rhythm')),'first_register':text(),'second_register':text(),'first_realization':text(4096),'second_realization':text(4096),'two_distinct_registers_reported':boolean()},{'two_distinct_registers_reported':True},[different('first_register','second_register'),nonempty('chosen_key'),nonempty('first_realization'),nonempty('second_realization')],save='realization',next='first'),
 'first':performance('Realize the source seed in your first chosen register; report after the whole seed and release manually.',{'register_reentry':text(),'realization_reentry':text(4096),'printed_contour_and_rhythm_retained':boolean()},next='second',guards=[same('register_reentry','realization','first_register'),same('realization_reentry','realization','first_realization')]),
 'second':performance('Realize the same source seed in the second chosen register. No uniform octave or fret geometry is inferred.',{'register_reentry':text(),'realization_reentry':text(4096),'printed_contour_and_rhythm_retained':boolean()},guards=[same('register_reentry','realization','second_register'),same('realization_reentry','realization','second_realization')])}
 out['motif_seed']=graph('l100_motif_seed_sing_then_key_two_registers',n,'sing')
 n={'write':report('Write three distinct pitch contours for the same printed rhythm. Text equality checks are custody checks; musical distinctness remains your separate report.',{'source_rhythm':source(param('rhythm')),'contour1':text(),'contour2':text(),'contour3':text(),'three_distinct_pitch_contours_reported':boolean()},{'three_distinct_pitch_contours_reported':True},[different('contour1','contour2'),different('contour1','contour3'),different('contour2','contour3')],save='contours',next='perform'),
 'perform':performance('Apply the same printed rhythm to all three chosen contours before reporting. Each rhythm identity must remain recognizable; no clock or pitches are supplied.',{'contour1':text(),'contour2':text(),'contour3':text(),'first_rhythm_recognizable':boolean(),'second_rhythm_recognizable':boolean(),'third_rhythm_recognizable':boolean()},guards=[same('contour1','contours','contour1'),same('contour2','contours','contour2'),same('contour3','contours','contour3')])}
 out['rhythm_motif']=graph('l100_same_rhythm_three_contours',n,'write')
 n={'write':report('Retain an original motif and write the selected transformation. State the printed Keep/Change relationship without silently substituting a different original.',{'original_motif':text(4096),'variant_motif':text(4096),'source_keep':source(param('keep')),'source_change':source(param('change')),'kept_identity_evidence':text(),'changed_feature_evidence':text()},guards=[different('original_motif','variant_motif'),nonempty('kept_identity_evidence'),nonempty('changed_feature_evidence')],save='material',next='constraint'),
 'constraint':constraint_node('pair'),
 'pair':performance('Play original then variant as one ordered comparison before entering reports. No intervening application input or release splits the source pair.',{'original_reentry':text(4096),'variant_reentry':text(4096),'original_then_variant_reported':boolean()},next='audibility',guards=[same('original_reentry','material','original_motif'),same('variant_reentry','material','variant_motif')]),
 'audibility':choice('Report whether the original/variant relationship remains audible. A negative report requires restoring one identity feature; unknown remains unresolved.','relationship',['audible','not_audible','unknown'],{'audible':'end','not_audible':'restore','unknown':'unresolved'}),
 'restore':report('Restore one chosen identity feature, retaining the original and both previous statements in native history. Write the revised variant before repeating the comparison.',{'identity_feature_restored':text(),'revised_variant':text(4096),'original_reentry':text(4096)},guards=[nonempty('identity_feature_restored'),same('original_reentry','material','original_motif')],save='restored',next='recompare'),
 'recompare':performance('After restoring one identity feature, play the original then revised variant again before judging the relationship.',{'original_reentry':text(4096),'revised_variant_reentry':text(4096),'original_then_variant_reported':boolean()},next='audibility',guards=[same('original_reentry','material','original_motif'),same('revised_variant_reentry','restored','revised_variant')]),
 'unresolved':report('Unknown audibility is retained and diagnosed. It cannot be reported as an audible relationship.',{'relationship':enumeration(['unknown'])},{'relationship':'audible'})}
 out['transformation']=graph('l100_original_variant_conditional_identity_restore',n,'write')
 n={'functions':report('Write the functional eight-bar progression first, with the exact selected source constraint. Do not jump ahead to melody or voicings.',{'functional_progression':text(4096),'eight_bars_reported':integer(8,8),'source_constraint':source(param('constraint_text'))},{'eight_bars_reported':8},[nonempty('functional_progression')],save='functions',next='voicings'),
 'voicings':report('Write voicings for your retained functional progression before writing the melody.',{'functional_progression_reentry':text(4096),'voicings':text(4096)},guards=[same('functional_progression_reentry','functions','functional_progression'),nonempty('voicings')],save='voicings',next='melody'),
 'melody':report('Now write the melody over your retained progression and voicings.',{'functional_progression_reentry':text(4096),'voicings_reentry':text(4096),'melody':text(4096)},guards=[same('functional_progression_reentry','functions','functional_progression'),same('voicings_reentry','voicings','voicings'),nonempty('melody')],save='melody',next='perform'),
 'perform':performance('Perform the complete chosen eight-bar composition; eight chord symbols alone do not finish this source task.',{'whole_eight_bars_reported':integer(8,8),'musical_form_preserved':boolean()},next='constraint'),
 'constraint':constraint_node('audit'),
 'audit':report('Answer the six source harmonic-direction questions from your actual listening: home, departure, cadence, clearest voice, optional chord and bar8 intention. Departure may be a section or bar; no fixed bar is required.',{'listener_can_identify_home':boolean(),'home_evidence':text(),'strongest_departure_location':text(),'departure_evidence':text(),'arrival_audible':boolean(),'cadence_evidence':text(),'clearest_voice':enumeration(['bass','guide','common_tone']),'voice_leading_evidence':text(),'optional_chord_identity':text(),'bar8_intention':enumeration(['close','turn_around']),'bar8_intention_evidence':text()},{'listener_can_identify_home':True,'arrival_audible':True},[nonempty('home_evidence'),nonempty('cadence_evidence'),nonempty('voice_leading_evidence')],save='audit',next='remove_compare'),
 'remove_compare':performance('Remove the named optional chord and compare the original and reduced progression before reporting. This is a real manual comparison duty, not synthesized listening.',{'optional_chord_identity_reentry':text(),'original_then_removed_chord_comparison_reported':boolean(),'comparison_evidence':text()},guards=[same('optional_chord_identity_reentry','audit','optional_chord_identity'),nonempty('comparison_evidence')])}
 out['harmony_first']=graph('l100_function_voicing_melody_harmonic_audit',n,'functions')
 n={'sing':performance('Sing a4–8bar melody with no guitar before harmony choices. No notes or melody are invented by the application.',{'no_guitar_used':boolean(),'reported_melody_bars':integer(4,8)},next='write'),
 'write':report('Write contour and rhythm, then identify strong-beat notes. Preserve the chosen melody even when the first chord grip is inconvenient.',{'melody':text(4096),'contour':text(),'rhythm':text(),'strong_beat_notes':text(),'melody_not_changed_for_grip':boolean()},{'melody_not_changed_for_grip':True},[nonempty('melody'),nonempty('strong_beat_notes')],save='melody',next='chords'),
 'chords':report('Choose chords supporting the retained strong-beat notes and selected harmonization constraint.',{'melody_reentry':text(4096),'supporting_harmony':text(4096),'initial_bass':text(),'source_constraint':source(param('constraint_text'))},guards=[same('melody_reentry','melody','melody'),nonempty('supporting_harmony')],save='harmony',next='constraint'),
 'constraint':constraint_node('alternate_bass'),
 'alternate_bass':report('Choose an alternate bass under the same retained melody, before testing it.',{'melody_reentry':text(4096),'initial_bass_reentry':text(),'alternate_bass':text()},guards=[same('melody_reentry','melody','melody'),same('initial_bass_reentry','harmony','initial_bass'),different('initial_bass_reentry','alternate_bass')],save='alternate',next='test'),
 'test':performance('Test the alternate bass under the same melody. Report after the complete chosen melody.',{'same_melody_retained':boolean(),'alternate_bass_tested':boolean()},next='reduction'),
 'reduction':performance('Reduce the harmony to bass plus melody before deciding whether inner voices are useful. Do not bypass this reduction by restarting another stage.',{'bass_plus_melody_reduction_performed':boolean(),'same_melody_retained':boolean(),'reduction_evidence':text()},next='inner_choice'),
 'inner_choice':choice('Add inner voices only if useful; an unknown judgment remains unresolved.','inner_voice_usefulness',['useful','not_useful','unknown'],{'useful':'inner','not_useful':'rank','unknown':'unresolved'}),
 'inner':performance('Add only useful inner voices while retaining bass/melody identity.',{'inner_voices_useful_reported':boolean(),'same_melody_retained':boolean(),'inner_voice_evidence':text()},next='rank'),
 'rank':report('Rank the six source harmonizations of the SAME melody by melody support, bass direction, cadence strength and distinctiveness using your actual manuscripts/evidence. This does not infer sibling execution or acceptance.',{'six_source_versions_reference':source(['diatonic only','one secondary dominant','one borrowed/chromatic chord','bass line determines reharmonization','sparse: maximum two chords per four bars','dense: one chord per bar']),'melody_reentry':text(4096),'all_six_versions_use_same_melody_reported':boolean(),'six_versions_manually_available':boolean(),'melody_support_ranking':text(),'bass_direction_ranking':text(),'cadence_strength_ranking':text(),'distinctiveness_ranking':text(),'version_evidence':text(4096)},{'six_versions_manually_available':True,'all_six_versions_use_same_melody_reported':True},[same('melody_reentry','melody','melody'),nonempty('version_evidence')]),
 'unresolved':report('Unknown usefulness cannot authorize inner voices or complete the source judgment.',{'usefulness':enumeration(['unknown'])},{'usefulness':'useful'})}
 out['melody_first']=graph('l100_sing_write_harmonize_alternate_reduce_useful_inner_rank',n,'sing')
 n={'bass':report('Choose/write the selected source bass design before any chord choices.',{'source_bass_design':source(param('constraint_text')),'chosen_bass':text(4096)},guards=[nonempty('chosen_bass')],save='bass',next='sing_top'),
 'sing_top':performance('Sing a possible top line while playing the retained bass BEFORE adding chords. Enter the possible top line only after this manual source action.',{'bass_reentry':text(4096),'top_line_sung_while_bass_played':boolean(),'possible_top_line':text(4096)},next='harmony',guards=[same('bass_reentry','bass','chosen_bass')],save='topline'),
 'harmony':report('Now add harmony above the retained bass design. The application supplies no source-fixed pitches, grips or clock.',{'bass_reentry':text(4096),'top_line_reentry':text(4096),'harmony':text(4096)},guards=[same('bass_reentry','bass','chosen_bass'),same('top_line_reentry','topline','possible_top_line'),nonempty('harmony')],save='harmony',next='perform'),
 'perform':performance('Perform your bass-driven composition with the chosen possible top line.',{'bass_reentry':text(4096),'top_line_reentry':text(4096),'harmony_reentry':text(4096),'bass_design_preserved':boolean(),'top_line_and_bass_relationship_evidence':text()},next='constraint',guards=[same('bass_reentry','bass','chosen_bass'),same('top_line_reentry','topline','possible_top_line'),same('harmony_reentry','harmony','harmony')]),
 'constraint':constraint_node()}
 out['bass_first']=graph('l100_bass_then_sung_top_line_then_harmony',n,'bass')
 n={'material':report('Choose the bass, top melody and harmonic function before the six ordered independence passes.',{'fixed_bass':text(4096),'top_melody':text(4096),'harmonic_function':text()},guards=[nonempty('fixed_bass'),nonempty('top_melody'),nonempty('harmonic_function')],save='material',next='pass1')}
 for i,harmony in enumerate(['roots only','triads','7th chords','alternate inversions'],1):
  n['pass'+str(i)]=performance('Source pass'+str(i)+': retain the fixed bass with '+harmony+'. Report after the whole chosen material.',{'bass_reentry':text(4096),'source_harmony':source(harmony),'fixed_bass_retained':boolean(),'harmony_evidence':text()},next='pass'+str(i+1),guards=[same('bass_reentry','material','fixed_bass')])
 n['pass5']=performance('Source pass5: simplify the bass while retaining harmonic function.',{'simplified_bass':text(4096),'harmonic_function_reentry':text(),'bass_simplified_reported':boolean(),'harmonic_function_retained':boolean()},next='pass6',guards=[same('harmonic_function_reentry','material','harmonic_function')])
 n['pass6']=performance('Source pass6: choose a new bass while retaining the top melody.',{'fixed_bass_reentry':text(4096),'new_bass':text(4096),'top_melody_reentry':text(4096),'top_melody_retained':boolean()},guards=[same('fixed_bass_reentry','material','fixed_bass'),same('top_melody_reentry','material','top_melody'),different('fixed_bass_reentry','new_bass')])
 out['independence']=graph('l100_six_ordered_bass_harmony_independence_passes',n,'material')
 n={'muted':performance('Write rhythm first on muted strings. Harmony choices remain unavailable until you report groove identity.',{'written_rhythm':text(4096),'muted_strings_used':boolean(),'groove_has_identity_reported':boolean()},next='harmony',save='muted'),
 'harmony':report('Add harmony only after the muted-string rhythm has identity; retain the chosen source groove engine.',{'source_groove_engine':source(param('constraint_text')),'rhythm':text(4096),'harmony':text(4096)},guards=[same('rhythm','muted','written_rhythm'),nonempty('rhythm'),nonempty('harmony')],save='material',next='perform'),
 'perform':performance('Perform the source-specific rhythm-driven composition; declared source lengths/agents stay separate from any chosen music or clock.',{'rhythm_identity_retained':boolean(),'rhythm_is_structural_evidence':text()},next='constraint'),
 'constraint':constraint_node()}
 out['rhythm_first']=graph('l100_muted_rhythm_identity_before_harmony',n,'muted')
 n={'write':report('Write the selected rhythmic identity over the unchanged printed progression; choose no replacement chords.',{'source_progression':source(['Am7','Fmaj7','Cmaj7','G7','Am7','Fmaj7','Cmaj7','G7']),'source_rhythmic_identity':source(param('constraint_text')),'chosen_rhythm':text(4096),'comparison_rhythm':text(4096)},guards=[different('chosen_rhythm','comparison_rhythm')],save='material',next='compare'),
 'compare':performance('Compare the chosen rhythmic version with your retained comparison under the SAME eight-bar source harmony. This manual comparison method is an authored audit of the printed structural-rhythm requirement, not a source-fixed playback order.',{'chosen_rhythm_reentry':text(4096),'comparison_rhythm_reentry':text(4096),'source_harmony_unchanged':boolean(),'comparison_heard_or_performed_by_learner':boolean(),'substantially_different_due_to_rhythm_reported':boolean(),'rhythmic_structure_evidence':text()},guards=[same('chosen_rhythm_reentry','material','chosen_rhythm'),same('comparison_rhythm_reentry','material','comparison_rhythm'),nonempty('rhythmic_structure_evidence')])}
 out['fixed_harmony']=graph('l100_fixed_eight_bar_harmony_distinct_rhythmic_identity',n,'write')
 n={'material':report('Choose the source-required initial material/method for this card, before generating a first draft. Source constraints do not supply notes or grips.',{'source_constraints':source(param('constraint_text')),'starting_method':source(param('starting_method')),'initial_material':text(4096)},guards=[nonempty('initial_material')],save='material',next='draft'),
 'draft':report('Generate a COMPLETE eight-bar first draft before any revision. Keep the original manuscript in history; this is an authored report, not inferred composition.',{'initial_material_reentry':text(4096),'draft_bars':integer(8,8),'first_draft':text(8192),'revision_started_before_full_draft':boolean()},{'draft_bars':8,'revision_started_before_full_draft':False},[same('initial_material_reentry','material','initial_material'),nonempty('first_draft',8192)],save='draft',next='constraint'),
 'constraint':constraint_node('perform'),
 'perform':performance('Perform/listen to the complete eight-bar draft with the exact card constraints before considering revision.',{'whole_eight_bar_form_retained':boolean(),'constraint_evidence':text()},next='revise_choice'),
 'revise_choice':choice('Revision is permitted only after the full eight-bar draft exists. No blanket H/I/J recording or rubric gate is added.','revision',['revise','retain_draft','unknown'],{'revise':'revision','retain_draft':'end','unknown':'unresolved'}),
 'revision':report('Retain the original eight-bar draft and write your separate revision. Same-material substitution cannot count as revision.',{'original_draft_reentry':text(8192),'revised_draft':text(8192),'revision_reason':text()},guards=[same('original_draft_reentry','draft','first_draft'),different('original_draft_reentry','revised_draft'),nonempty('revision_reason')],save='revision',next='revised_performance'),
 'revised_performance':performance('Perform/listen to the separately retained revision; the original report remains in history.',{'revised_eight_bar_form_retained':boolean(),'source_constraints_retained':boolean(),'revision_comparison_evidence':text()}),
 'unresolved':report('Unknown revision intention cannot substitute for the full original draft or a separate revision.',{'revision':enumeration(['unknown'])},{'revision':'retain_draft'})}
 out['constraint_lab']=graph('l100_eight_bar_complete_draft_before_revision',n,'material')
 assert len(out)==10;return out

def constraint_parameters(row,page):
 components=row['implementation']['task']['printed_components'];label=components[0];fields={};expected={}
 def yes(name):fields[name]=boolean();expected[name]=True
 def no(name):fields[name]=boolean();expected[name]=False
 def count(name,n):fields[name]=integer(n,n);expected[name]=n
 def evidence(name):fields[name]=text()
 if page==5:
  if label=='Transposition':yes('interval_identity_retained');yes('rhythm_identity_retained');yes('starting_pitch_changed_reported')
  elif label=='Sequence':yes('contour_retained');yes('scale_degree_level_changed_reported')
  elif label=='Rhythmic augmentation':yes('pitch_order_retained');yes('durations_longer_reported')
  elif label=='Rhythmic diminution':yes('pitch_order_retained');yes('durations_shorter_reported')
  elif label=='Inversion':yes('rhythmic_identity_retained');yes('up_down_contour_inverted_reported')
  elif label=='Retrograde':fields['retained_identity']=enumeration(['rhythm','pitch_set']);yes('order_reversed_reported')
  elif label=='Register shift':yes('pitch_classes_retained');yes('rhythm_retained');yes('octave_changed_reported')
  elif label=='Truncation':yes('opening_identity_retained');yes('ending_removed_reported')
  else:raise AssertionError('foreign B transformation')
 elif page==7:
  if label=='No V-I cadence':no('v_to_i_cadence_used');evidence('alternate_arrival')
  elif label=='One common tone in every chord':yes('one_common_tone_retained_in_every_chord');evidence('chosen_common_tone');evidence('voice_leading')
  elif label=='Chromatic mediant once':count('chromatic_mediant_uses',1);evidence('intentional_mediant_evidence')
  elif label=='Descending bass only':yes('all_bass_motion_descending_reported');evidence('bass_direction_evidence')
  elif label=='Pedal tone for 4 bars':count('pedal_bars',4);yes('harmony_changed_above_fixed_note');evidence('chosen_pedal_note')
  elif label=='One secondary dominant':count('secondary_dominant_uses',1);evidence('prepared_destination')
  else:raise AssertionError('foreign C constraint')
 elif page==10:
  if label=='1':yes('diatonic_only_reported')
  elif label=='2':count('secondary_dominant_uses',1)
  elif label=='3':count('borrowed_or_chromatic_chords',1)
  elif label=='4':yes('bass_line_determines_reharmonization')
  elif label=='5':fields['maximum_chords_in_any_four_bar_group']=integer(0,2)
  elif label=='6':count('chords_per_bar',1)
  else:raise AssertionError('foreign D constraint')
 elif page==11:
  if label=='Stepwise ascent':fields['source_bass_sequence']=source('A-B-C-D-E-F-G-A');yes('printed_stepwise_ascent_retained')
  elif label=='Pedal':fields['source_pedal']=source('A');count('pedal_bars',4);yes('A_held_or_repeated_reported')
  elif label=='Root/fifth alternation':yes('root_fifth_alternation_reported')
  elif label=='Chromatic approach':yes('destination_roots_on_beats1_reported')
  elif label=='Syncopated riff':yes('harmony_implied_by_bass_rhythm_reported')
  elif label=='Contrary to melody':yes('bass_descends_while_melody_rises_reported')
  elif label=='Sparse roots':yes('melody_supplies_harmonic_color_reported')
  else:raise AssertionError('foreign E design')
 elif page==13:
  if label=='Funk':count('cell_beats',2);count('composition_bars',8);yes('syncopated_cell_reported')
  elif label=='Rock':count('pedal_accent_variations',3)
  elif label=='Reggae':yes('offbeat_pattern_reported');yes('rhythm_unchanged_through_harmony_changes')
  elif label=='Shuffle':yes('triplet_spacing_reported');count('motif_entry_every_bars',2)
  elif label=='Country':yes('alternating_bass_chord_engine_reported')
  elif label=='Interlock':yes('upper_repeated_cell_around_bass_space_reported')
  elif label=='Jam-band':yes('one_motif_retained');yes('only_density_changes_reported')
  else:raise AssertionError('foreign F engine')
 elif page==15:
  if label=='1':count('motif_notes',3);count('chord_identities',2);count('full_bar_rests',1)
  elif label=='2':yes('bass_descending_reported');yes('melody_rising_reported');no('v_to_i_cadence_used')
  elif label=='3':count('pedal_first_bar',1);count('pedal_last_bar',4);count('chromatic_mediant_bar',5)
  elif label=='4':count('same_chord_bars',4);yes('register_creates_contrast_reported')
  elif label=='5':yes('melody_written_first');yes('one_common_tone_across_all_harmony_reported');evidence('chosen_common_tone')
  elif label=='6':yes('bass_written_first');count('secondary_dominant_uses',1);yes('sparse_melody_reported')
  elif label=='7':fields['source_inversion_bars']=source([5,6]);yes('motif_inversion_in_bars5_6_reported');yes('original_motif_returns_bar8_reported');fields['original_motif_reentry']=text(4096)
  else:raise AssertionError('foreign G card')
 if fields:evidence('source_specific_constraint_evidence')
 guards=[dict(kind='required_manual_fields_resolved',fields=[name for name,spec in fields.items() if spec.get('input_role')=='manual_report'])]+[nonempty(name) for name,spec in fields.items() if spec.get('type')==['string','null'] and spec.get('minLength')]
 if page==15 and label=='7':guards.append(same('original_motif_reentry','material','initial_material'))
 return dict(constraint_text=' | '.join(components),constraint_instruction='Report this exact printed source row using your own music/evidence: '+' | '.join(components),constraint_schema=schema(fields),constraint_expected=expected,constraint_guards=guards)

def expand(value,parameters):
 if isinstance(value,dict):
  if '$parameter' in value:
   assert set(value)=={'$parameter'} and value['$parameter'] in parameters;return copy.deepcopy(parameters[value['$parameter']])
  return {k:expand(v,parameters) for k,v in value.items()}
 if isinstance(value,list):return [expand(v,parameters) for v in value]
 return value
def materialize(template,parameters,program):
 assert program in PROGRAM_PARAMETERS and set(parameters)==COMMON_PARAMETERS|PROGRAM_PARAMETERS[program],'closed parameter fields'
 return expand(template,parameters)
def generate(output):
 assert not output.exists();assert sha(SELECTION.read_bytes())==SELECTION_SHA
 selection=json.loads(SELECTION.read_text());scope=json.loads(read_ref(selection['source_scope']));lines=read_ref(selection['payload']).splitlines(keepends=True);context=json.loads(read_ref(selection['cached_context']));templates=programs();definitions=[];counts={};pages={p['physical_page']:p['text'] for p in context['pages']}
 guidance={3:['Choose a key only after the contour and rhythm can be sung. Then realize each seed in two registers.'],4:['Apply the same rhythm to three different pitch contours. The rhythm should remain recognizable.'],5:['After each transformation, play original then variant. If the relationship is no longer audible, restore one identity feature.'],7:['Write the functional progression first, then voicings, then melody.'],8:pages[8].splitlines(),9:pages[9].splitlines(),10:['Rank versions by melody support, bass direction, cadence strength, and distinctiveness.'],11:['Sing a possible top line while playing bass before adding chords.'],12:pages[12].splitlines(),13:['Write rhythm first on muted strings. Add harmony only after the groove has identity.'],14:['Use | Am7 | Fmaj7 | Cmaj7 | G7 | x2.','The chord progression stays unchanged. The composition should feel substantially different because rhythm is structural.'],15:['Complete all eight cards. Do not revise while generating the first draft; revise only after a full eight bars exist.']}
 instruction_spans={}
 for page,texts in guidance.items():
  instruction_spans[str(page)]=[]
  for textvalue in texts:
   start=pages[page].find(textvalue);assert start>=0;instruction_spans[str(page)].append(dict(start=start,end=start+len(textvalue),text_sha256=sha(textvalue.encode()),text=textvalue))
 for selected in scope['rows']:
  raw=lines[selected['current_payload']['jsonl_line']-1];assert sha(raw)==selected['raw_jsonl_line_sha256'];row=json.loads(raw);assert row['package_key']==selected['package_key'] and row['implementation']['kind']=='structured_source_prescription';page=selected['source_locator']['physical_pages'][0];assert page in row['source_payload']['page_context_refs'];program={3:'motif_seed',4:'rhythm_motif',5:'transformation',7:'harmony_first',10:'melody_first',11:'bass_first',12:'independence',13:'rhythm_first',14:'fixed_harmony',15:'constraint_lab'}[page];counts[program]=counts.get(program,0)+1;parts=row['implementation']['task']['printed_components'];parameters=constraint_parameters(row,page)
  if page==3:parameters.update(degrees=parts[1],rhythm=parts[2])
  if page==4:parameters.update(rhythm=parts[1])
  if page==5:parameters.update(keep=parts[1],change=parts[2])
  if page==15:parameters['starting_method']={'4':'rhythm-first','5':'melody-first','6':'bass-first'}.get(parts[0],'source-constrained chosen material')
  resolved=materialize(templates[program],parameters,program);context_pages={3:[3],4:[4],5:[5],7:[7,8],10:[9,10],11:[11],12:[12],13:[13],14:[14],15:[15]}[page]
  definitions.append(dict(schema='fathom.manual-procedure-shared-reference-definition.1',source_key=row['package_key'],source_identity=row['source_identity'],level=100,source_kind_preserved='structured_source_prescription',payload_ref=selected['current_payload'],raw_source_line_sha256=selected['raw_jsonl_line_sha256'],raw_source_line_encoding='including terminal newline',original_compact_sha256=sha(compact(row)),original_canonical_sha256=sha(json.dumps(row,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()),retained_contract_path=['implementation','task','contract'],source_pins=row['source_refs'],source_locator=selected['source_locator'],printed_components=parts,program_ref=program,parameters=parameters,resolved_program_sha256=sha(compact(resolved)),learner_instruction_row_refs=[['implementation','task','label']],learner_instruction_pages=context_pages,cached_context_ref=selection['cached_context'],source_task_instruction_refs=[['implementation','task','instructions',i] for i in range(len(row['implementation']['task']['instructions']))],native_executable=False,performance_observed=False,grants_credit=False))
 assert len(definitions)==64 and set(r['source_key'] for r in definitions)==set(selection['keys'])
 shared=dict(schema='fathom.manual-composition-shared-programs.1',programs=templates,closed_parameter_operator={'shape':{'$parameter':'exact field name in this row parameters'},'expressions_and_external_paths':False,'closed_fields_by_program':{name:sorted(COMMON_PARAMETERS|extra) for name,extra in PROGRAM_PARAMETERS.items()}},required_native_operator_extensions={'required_manual_fields_resolved':{'fields':'closed literal list of required manual_report schema property names','unknown_null_result':'diagnosed negative report retained in history; never malformed or completion','wrong_type':'schema refusal without mutation'}},native_normalization_pending=True)
 contexts=dict(schema='fathom.manual-composition-instruction-contexts.1',cached_context_ref=selection['cached_context'],learner_instruction_spans=instruction_spans,source_table_headings_discrepancies=[dict(page=10,heading='One Melody, Four Harmonizations',printed_versions=6),dict(page=14,heading='Same Harmony, Four Rhythmic Identities',printed_versions=6)],family_duties={'D':'Rank all six source harmonizations from actual retained manuscripts/reports; no sibling acceptance or execution inferred.','G':'Complete all eight source cards. Selected seven do not imply eighth completion; retain separate whole-family audit debt.'},supporting_context_only={'H_pages':[16,17,18,19],'I_page':20,'J_page':21,'blanket_recording_capstone_or_14of16_gate_on_selected64':False},unknowns=['Chosen notes, keys, bass/melody/harmony realizations and frets remain learner authorship.','No source-fixed BPM, durations in seconds, acoustic observations or generated recording.','Native source-instance/revision/history/explicit release and delayed input fences require future shared-engine integration and review.'])
 output.mkdir(parents=True);(output/'definitions.jsonl').write_bytes(b''.join(compact(r)+b'\n' for r in sorted(definitions,key=lambda r:r['source_key'])));(output/'programs.json').write_bytes(compact(shared)+b'\n');(output/'contexts.json').write_bytes(compact(contexts)+b'\n')
 closure=dict(schema='fathom.manual-composition64-data-closure.1',rows=64,shared_source_programs=10,program_counts=counts,keys=sorted(selection['keys']),selection=pin(SELECTION),payload=selection['payload'],source_scope=selection['source_scope'],cached_context=selection['cached_context'],compiler=pin(Path(__file__)),files=[pin(output/name) for name in ['definitions.jsonl','programs.json','contexts.json']],resolved_program_hashes={r['source_key']:r['resolved_program_sha256'] for r in definitions},perrow_model_files=0,source_files_reread=0,native_execution=False,official_acceptance_increment=0)
 (output/'family-closure.json').write_bytes(compact(closure)+b'\n');print(json.dumps({'rows':64,'programs':10,'program_counts':counts,'files_bytes':sum(p['bytes'] for p in closure['files']),'native_execution':False}))
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);args=parser.parse_args();generate(ROOT/args.output)
