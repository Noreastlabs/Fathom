"""Independent complete-model tests for the single64-tone two-register child."""
from copy import deepcopy
from source_oracles import H_BARS,PC,TUNING_NAME
PASSES=('contour','degrees','exact_notes','chord_function')
COMMON=('sung_once','played_immediately','one_chosen_position','no_searching','note_lengths_even','comfortable_pulse','normal_beat_one_accent')
RELEASE={'learner_released':True,'external_source_stopped':True}
PLAN={'prerequisites':{'original_workbook':True,'own_instrument':True},
      'recording':{'kind':'external_recording','reference':'Independent synthetic recording reference; audio not inspected.','declared_sha256':None,'ready':True},
      'source_declarations':{'recorded_once':'yes','transcriber_did_not_study_source_card':'yes'}}

def written(name,unknown_contour=False,wrong_pitch=False,unknown_pitch=False):
    if name=='exact_notes':
        bars=[notes.split('-') for chord,notes,target in H_BARS]
        if wrong_pitch:bars[0][0]='D'
        if unknown_pitch:bars[0][0]=None
    elif name=='chord_function':bars=[{'chord':chord,'function':'Manual unassessed function declaration.'} for chord,notes,target in H_BARS]
    else:bars=['Manual unassessed response.' for _ in H_BARS]
    if name=='contour' and unknown_contour:bars[0]=None
    return {'bars':bars,'notes':'Independent synthetic response; no hearing observation.'}

def position(f,shift=0):
    names=[n for bar in f.responses['exact_notes']['bars'] for n in bar]
    contacts=[]
    for note in names:
        if note is None:note='E' # Negative test choice is explicit; model must reject it.
        fret=(PC[note]-TUNING_NAME['D'])%12+shift
        contacts.append({'string':'D','fret':fret,'midi':TUNING_NAME['D']+fret})
    return {'position':{'minimum_fret':shift,'maximum_fret':shift+11,'rationale':'Independent chosen fixture position, no source-fixed fingering claim.'},
            'contacts':contacts,'source_scope_ack':True}

def write_all(f,m,q=None,unknown_contour=False,wrong_pitch=False,unknown_pitch=False,hearing='yes'):
    f.set_source(f.token(),PLAN)
    for name in PASSES:
        confirmation={'key':f.key,'pass':name,'recording_reference':PLAN['recording']['reference'],'ready':True}
        f.begin_written(f.token(),confirmation)
        if q:q.refuse(lambda:f.commit_written(f.token(),written(name)),m.Refusal,'H cannot write before source stopped',f)
        f.heard(f.token(),{'heard_source':hearing});f.request_stop(f.token())
        if q:q.refuse(lambda:f.release(f.token(),dict(RELEASE,external_source_stopped=False)),m.Refusal,'H external source release fence',f)
        f.release(f.token(),RELEASE)
        before=f.token();f.commit_written(f.token(),written(name,unknown_contour,wrong_pitch,unknown_pitch))
        if q:q.refuse(lambda:f.next_written(before),m.Refusal,'H stale written-pass owner',f)
        f.next_written(f.token())

def bar_report(f,common='yes',diagnosis=''):
    return {'key':f.key,'bar':f.bar+1,'contacts':f.target()['contacts'],'sing_count':1,'attack_counts':[1]*4,
            'common':dict.fromkeys(COMMON,common),'diagnosis':diagnosis,'notes':'Independent manual fixture; no actual playing observation.'}

def play_register(f,m,q=None,states=None,exercise_failure=False):
    for bar in range(16):
        if q:q.check(f.target()['bar']==bar+1 and len(f.target()['contacts'])==4,'H exact current bar order/width')
        if states is not None and bar==0:states.append(deepcopy(f))
        f.sung_bar(f.token(),True);f.play_bar(f.token(),True)
        if q:q.refuse(lambda:f.next_bar(f.token()),m.Refusal,'H no advance while physical release/report pending',f)
        f.release(f.token(),RELEASE)
        if states is not None and bar==0:states.append(deepcopy(f))
        if exercise_failure and bar==0:
            if q:q.refuse(lambda:f.report_bar(f.token(),bar_report(f,'uncertain')),m.Refusal,'H uncertain manual duty needs diagnosis',f)
            f.report_bar(f.token(),bar_report(f,'uncertain','Manual uncertainty; repeat the same bar.'))
            if q:q.check(f.state=='needs_bar_retry','H uncertainty enters retry')
            f.retry_bar(f.token(),'Repeat exactly current chosen bar after diagnosis.')
            if q:q.check(f.bar==bar and f.state=='sing_bar','H retry keeps same current bar')
            f.sung_bar(f.token(),True);f.play_bar(f.token(),True);f.release(f.token(),RELEASE)
        f.report_bar(f.token(),bar_report(f));f.next_bar(f.token())

def transfer(f):
    choice=position(f,12);choice['octave_shift_semitones']=12
    f.begin_second_register(f.token(),choice)

def run(m,rows,q):
    q.check(len(rows)==1,'H exact one-key whole child')
    c=m.contract();q.check(c['source_authority_supported_tones']==64 and c['complete_manual_contract'] is True,'H exact full-source private contract')
    f=m.FullModelReconstructionFlow(rows[0]['package_key']);states=[deepcopy(f)]
    source=f.source_player_view()
    q.check([(b['chord'],'-'.join(b['pitches']),b['structural_target']) for b in source['bars']]==H_BARS,'H exact16 original source bars/targets')
    q.check('source_reference' not in f.learner_view() and 'visible_source_reference' not in f.learner_view(),'H source card hidden before learner attempt')
    q.refuse(lambda:f.reveal_source(f.token()),m.Refusal,'H initial early reveal',f)
    write_all(f,m,q);states.append(deepcopy(f))
    q.check(f.state=='choose_first_position' and len(f.responses)==4,'H four written passes before playing')
    q.refuse(lambda:f.begin_final_bar(f.token()),m.Refusal,'H inherited final-bar skip disabled',f)
    q.refuse(lambda:f.choose_partial_position(f.token(),{}),m.Refusal,'H partial15-bar escape disabled',f)
    plan=position(f)
    bad=deepcopy(plan);bad['contacts'].pop()
    q.refuse(lambda:f.choose_first_position(f.token(),bad),m.Refusal,'H incomplete63 contacts',f)
    bad=deepcopy(plan);bad['contacts'][0]['fret']=True
    q.refuse(lambda:f.choose_first_position(f.token(),bad),m.Refusal,'H boolean fret',f)
    bad=deepcopy(plan);bad['bpm']=120
    q.refuse(lambda:f.choose_first_position(f.token(),bad),m.Refusal,'H hidden chosen clock',f)
    f.choose_first_position(f.token(),plan)
    q.check('source_reference' not in f.learner_view(),'H chosen contacts do not reveal correct source')
    play_register(f,m,q,states,True);states.append(deepcopy(f))
    q.check(f.state=='first_register_reported' and f.bar==16,'H complete16 first-register bars')
    f.reveal_source(f.token());states.append(deepcopy(f))
    q.check(f.pitch_matches is True and len(f.learner_view()['source_reference'])==16,'H full source reveal after all16 bars')
    choice=position(f,12);choice['octave_shift_semitones']=12
    for shift in [0,True,7]:
        q.refuse(lambda:f.begin_second_register(f.token(),dict(choice,octave_shift_semitones=shift)),m.Refusal,'H invalid second-register shift',f)
    bad=deepcopy(choice);bad['contacts'][-1]=deepcopy(plan['contacts'][-1])
    q.refuse(lambda:f.begin_second_register(f.token(),bad),m.Refusal,'H nonuniform/incomplete octave transfer',f)
    f.begin_second_register(f.token(),choice);play_register(f,m,q,states);states.append(deepcopy(f))
    q.check(f.state=='both_registers_reported','H both complete16-bar registers')
    scores={b:{'hearing_accuracy':2,'first_attack_fretboard_accuracy':2} for b in ['1-4','5-8','9-12','13-16']}
    bad=deepcopy(scores);bad['13-16']['hearing_accuracy']=True
    q.refuse(lambda:f.declare_scores(f.token(),bad),m.Refusal,'H boolean manual score',f)
    bad=deepcopy(scores);bad['13-16']['hearing_accuracy']=3
    q.refuse(lambda:f.declare_scores(f.token(),bad),m.Refusal,'H out-of-range score',f)
    unknown=deepcopy(scores);unknown['13-16']['hearing_accuracy']=None
    f.declare_scores(f.token(),unknown);q.check(f.history[-1]['data']['declared_total'] is None,'H unknown score remains incomplete')
    q.refuse(lambda:f.finish(f.token()),m.Refusal,'H no finish with unknown score',f)
    f.declare_scores(f.token(),scores);q.check(f.history[-1]['data']['declared_total']==16,'H printed manual maximum16')
    f.finish(f.token());states.append(deepcopy(f))
    q.check(f.state=='completed' and f.history[-1]['data']['mastery_awarded'] is False and f.history[-1]['data']['official_acceptance'] is False,'H manual completion without mastery/official acceptance')
    q.refuse(lambda:f.play_bar(f.token(),True),m.Refusal,'H no play after completed',f)
    # Every chosen state snapshot has a physical release fence for cancellation/reopen.
    stable={'setup','choose_first_position','reporting_bar','first_register_reported','verification','both_registers_reported','completed'}
    for at in states:
        original=at.state;old=at.token();at.cancel(at.token());at.reopen(at.token())
        q.check(at.state=='reopen_release','H cancel/reopen release fence '+original)
        q.refuse(lambda:at.release(old,RELEASE),m.Refusal,'H stale token through cancel/reopen',at)
        at.release(at.token(),RELEASE)
        q.check(at.state==(original if original in stable else 'sing_bar'),'H safe resume '+original)
    # Wrong notes remain playable until explicit source comparison, then retry preserves prior reveal/history.
    wrong=m.FullModelReconstructionFlow(f.key);write_all(wrong,m,wrong_pitch=True)
    wrong.choose_first_position(wrong.token(),position(wrong));play_register(wrong,m)
    wrong.reveal_source(wrong.token());q.check(wrong.pitch_matches is False,'H wrong reconstruction compared only post-playing')
    q.refuse(lambda:transfer(wrong),m.Refusal,'H wrong exact notes cannot transfer',wrong)
    oldhistory=deepcopy(wrong.reference_history);wrong.restart_written(wrong.token(),'Correct the written pitch after diagnosis.')
    q.check(wrong.state=='ready_written' and wrong.revealed is True and wrong.reference_history==oldhistory,'H wrong-note reconstruction retry retains reveal/history')
    unknown=m.FullModelReconstructionFlow(f.key);write_all(unknown,m,unknown_pitch=True)
    q.refuse(lambda:unknown.choose_first_position(unknown.token(),position(unknown)),m.Refusal,'H unknown exact note cannot become invented contact',unknown)
    unknown.diagnose_unable(unknown.token(),'Unknown first pitch requires reconstruction.');unknown.restart_written(unknown.token(),'Retry from the recording.')
    q.check(unknown.state=='ready_written' and unknown.responses=={},'H unknown exact-note diagnosis/retry')
    heard=m.FullModelReconstructionFlow(f.key);write_all(heard,m,hearing='uncertain')
    heard.choose_first_position(heard.token(),position(heard));play_register(heard,m);heard.reveal_source(heard.token())
    q.refuse(lambda:transfer(heard),m.Refusal,'H uncertain hearing cannot transfer even with exact notes',heard)
    # Causal nullable-worksheet branch: reaching full play must still allow stated reconstruction recovery.
    nullable=m.FullModelReconstructionFlow(f.key);write_all(nullable,m,unknown_contour=True)
    nullable.choose_first_position(nullable.token(),position(nullable));play_register(nullable,m)
    nullable.reveal_source(nullable.token());transfer(nullable);play_register(nullable,m)
    nullable.declare_scores(nullable.token(),scores)
    q.refuse(lambda:nullable.finish(nullable.token()),m.Refusal,'H unknown contour cannot finish',nullable)
    try:
        nullable.restart_written(nullable.token(),'Resolve the retained unknown contour through reconstruction.')
    except m.Refusal as error:
        q.failures.append({'family':q.family,'criterion':'H explicit unknown worksheet field recovery after both registers',
          'result':'CORRECT_REQUIRED','state':nullable.state,'error':str(error),
          'causal_sequence':'contour bar1=None -> four written passes ->16 first-register bars -> source reveal ->16 second-register bars -> all scores -> finish refuses unknown -> restart_written refuses same current token',
          'required_bounded_correction':'Either refuse second-register transfer while any required worksheet field is unknown and retain verification restart, or permit diagnosed restart_written from both_registers_reported; preserve prior response/reference history and no-credit/release fences.'})
    else:q.check(nullable.state=='ready_written','H diagnosed nullable-field retry returns to written stage')
