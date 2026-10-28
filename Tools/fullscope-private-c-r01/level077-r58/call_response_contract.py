"""Exact echo before chosen variations; four manual passes, no app audio or clock."""
from copy import deepcopy
from fractions import Fraction
from uuid import uuid4
import math,re
RAW=(('Cmaj7','C-E-G-E','G-B-E-C'),('Dm7','D-F-A-F','A-C-F-D'),('G7','G-B-D-F','F-D-B-G'),
 ('Am7','A-C-E-G','G-E-C-A'),('Fmaj7','F-A-C-E','E-C-A-F'),('Bm7b5','B-D-F-A','A-F-D-B'),
 ('E7','E-G#-B-D','D-B-G#-E'),('AmMaj7','A-C-E-G#','G#-E-C-A'))
KEYS=tuple(f'exercise-completeness-r01/level077/modulee/p011-t1-r{i+1}/{r[0].lower()}' for i,r in enumerate(RAW))
CHORD_PCS={'Cmaj7':(0,4,7,11),'Dm7':(2,5,9,0),'G7':(7,11,2,5),'Am7':(9,0,4,7),'Fmaj7':(5,9,0,4),'Bm7b5':(11,2,5,9),'E7':(4,8,11,2),'AmMaj7':(9,0,4,8)}
TUNING={'E':40,'A':45,'D':50,'G':55,'B':59,'e':64};YN=('yes','no','uncertain')
ECHO_DUTIES=('heard_exact_question','written_before_playing','source_order')
PLAY_DUTIES=('heard_question','sung_response_correct','one_silent_setup_per_target','no_searching','played_pitches_correct','played_rhythm_correct','source_order')
FOOTER='Pass 1: exact echo. Pass 2: same rhythm, new pitches. Pass 3: same contour, new register. Pass 4: answer on the next chord while preserving phrase length.'
NO_SEARCH='After the target is sung, use one silent setup and one attack. Diagnose a wrong attack; do not slide around until the note is found.'
class Refusal(ValueError):pass
def require(ok,msg):
    if not ok:raise Refusal(msg)
def fields(x,n):require(type(x) is dict and set(x)==set(n),'exact typed field set')
def text(x):return type(x) is str and bool(x.strip())
def pitch(x):
    require(type(x) is str and re.fullmatch(r'[A-G](?:#|b)?',x) is not None,'pitch spelling')
    return ({'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}[x[0]]+{'#':1,'b':-1}.get(x[1:],0))%12
def qtime(x,zero=False):
    require(type(x) is list and len(x)==2 and all(type(v) is int for v in x) and x[1]>0 and (x[0]>=0 if zero else x[0]>0) and math.gcd(*x)==1,'canonical rational time')
    return Fraction(*x)
def rhythm_signature(r):
    fields(r,('onsets_q','durations_q','length_q'));on=r['onsets_q'];dur=r['durations_q'];length=qtime(r['length_q'])
    require(type(on) is list and type(dur) is list and len(on)==len(dur)==4,'four chosen note times')
    starts=tuple(qtime(x,True) for x in on);spans=tuple(qtime(x) for x in dur)
    require(all(a+d<=length for a,d in zip(starts,spans)) and all(starts[i]+spans[i]<=starts[i+1] for i in range(3)),'ordered nonoverlap within chosen phrase length')
    return starts,spans,length
def midi4(m):require(type(m) is list and len(m)==4 and all(type(x) is int and 0<=x<=127 for x in m),'four chosen MIDI targets')
def validate_source_plan(p,i):
    fields(p,('prerequisites','provider'));fields(p['prerequisites'],('original_workbook','own_instrument'));require(all(v is True for v in p['prerequisites'].values()),'manual prerequisites')
    v=p['provider'];fields(v,('kind','reference','ready','question_midi','question_rhythm','can_hold_next_chord'))
    require(v['kind']=='external_human' and text(v['reference']) and v['ready'] is True and v['can_hold_next_chord'] is True,'actual capable external human source player')
    midi4(v['question_midi']);require([x%12 for x in v['question_midi']]==[pitch(x) for x in RAW[i][1].split('-')],'exact printed question pitch order');rhythm_signature(v['question_rhythm'])
    require(all(40<=x<=88 for x in v['question_midi']) and (max(v['question_midi'])<=76 or min(v['question_midi'])>=52),'chosen guitar range and at least one feasible nonzero octave-shift pass')
def validate_response(p,phase,i,source):
    fields(p,('basis','midi','rhythm','contacts','next_chord'));m=p['midi'];midi4(m);sig=rhythm_signature(p['rhythm']);src=source['provider'];question=src['question_midi'];base=rhythm_signature(src['question_rhythm'])
    require(type(p['basis']) is str,'explicit chosen response basis')
    if phase==0:require(p['basis']=='exact_echo' and m==question and sig==base and p['next_chord'] is None,'exact source realization echo')
    elif phase==1:
        require(p['basis'] in ('answer_model','own_new_pitch_order') and sig==base and p['next_chord'] is None,'new pitches with same chosen rhythm')
        require([x%12 for x in m]!=[x%12 for x in question],'at least one new pitch class; octave-only change belongs to register pass')
        if p['basis']=='answer_model':require([x%12 for x in m]==[pitch(x) for x in RAW[i][2].split('-')],'exact printed answer-model pitch order')
    elif phase==2:
        shift=m[0]-question[0];require(p['basis']=='original_question_octave' and shift!=0 and shift%12==0 and all(a-b==shift for a,b in zip(m,question)) and sig==base and p['next_chord'] is None,'selected nonzero octave shift of original question; same contour/rhythm')
    else:
        chord=p['next_chord'];require(phase==3 and p['basis']=='chosen_next_chord' and type(chord) is str and chord in CHORD_PCS and all(x%12 in CHORD_PCS[chord] for x in m) and sig[2]==base[2],'explicit finite chord-tone response on chosen next chord, same phrase length')
    require(type(p['contacts']) is list and len(p['contacts'])==4,'one chosen guitar contact per target')
    for x,n in zip(p['contacts'],m):
        fields(x,('string','fret'));require(type(x['string']) is str and x['string'] in TUNING and type(x['fret']) is int and 0<=x['fret']<=24 and TUNING[x['string']]+x['fret']==n,'exact standard-tuning target contact')

class CallResponseFlow:
    def __init__(self,key):
        require(type(key) is str and key in KEYS,'exact eight page11 keys');self.key=key;self.index=KEYS.index(key);self.instance=uuid4().hex
        self.generation=self.phase=self.cycle=self.action=0;self.state='setup';self.plan=None;self.responses={};self.resume=None
        self.history=[];self.written=None;self.written_history=[];self.ever_revealed=self.current_revealed=self.echo_passed=False
        self.source_release_required=self.source_stop_requested=False;self.source_role=None
    def token(self):return (self.instance,self.key,self.generation,self.phase,self.cycle,self.action,self.state)
    def check(self,t,states):require(type(t) is tuple and t==self.token(),'current source/pass/action owner');require(self.state in states,'wrong state')
    def record(self,kind,data,state):
        self.history.append({'kind':kind,'generation':self.generation,'pass':self.phase+1,'cycle':self.cycle,'data':deepcopy(data)});self.action+=1;self.state=state
    def set_source_plan(self,t,p):
        self.check(t,('setup','completed'));validate_source_plan(p,self.index);require(not self.source_release_required,'source release pending')
        self.plan=deepcopy(p);self.generation+=1;self.phase=self.cycle=0;self.responses={};self.written=None;self.current_revealed=self.echo_passed=False;self.record('source_plan',p,'ready_listen')
    def source_player_view(self):
        return {'key':self.key,'chord':RAW[self.index][0],'printed_question':RAW[self.index][1].split('-'),'printed_answer_model':RAW[self.index][2].split('-'),
          'chosen_question':None if self.plan is None else deepcopy(self.plan['provider']),'pass':self.phase+1,
          'chosen_next_chord':self.responses.get(3,{}).get('next_chord') if self.phase==3 else None,'source_role':self.source_role,
          'manual_stop_requested':self.source_stop_requested,'manual_release_required':self.source_release_required,'audio_supplied_by_app':False,
          'instruction':'Stop source sound and confirm manually' if self.source_stop_requested else 'Supply question; in pass4 hold the explicitly chosen next chord through the response when requested.'}
    def learner_view(self):
        out={'chord':RAW[self.index][0],'pass':self.phase+1,'state':self.state,'written_echo':deepcopy(self.written),'previously_revealed':self.ever_revealed,
          'prior_written_retained':bool(self.written_history),'blind_assessment_claim':False,'exact_echo_reported':self.echo_passed}
        if self.current_revealed:out['question_reference']={'notes':RAW[self.index][1].split('-'),'chosen_midi':deepcopy(self.plan['provider']['question_midi']),'chosen_rhythm':deepcopy(self.plan['provider']['question_rhythm'])}
        if self.echo_passed:out['answer_model']=RAW[self.index][2].split('-')
        if self.phase in self.responses:out['chosen_response']=deepcopy(self.responses[self.phase])
        return out
    def begin_question(self,t,c):
        self.check(t,('ready_listen',));fields(c,('key','ready','same_chosen_question'));require(c['key']==self.key and c['ready'] is True and c['same_chosen_question'] is True,'current external question confirmed')
        require(self.phase==0 or self.phase in self.responses,'current response plan required after exact echo');self.cycle+=1
        if self.phase==0:self.written=None;self.current_revealed=False
        self.source_release_required=True;self.source_stop_requested=False;self.source_role='question';self.record('begin_question',{'confirmation':c,'audio_observed':False},'listening')
    def end_question(self,t,ack):
        self.check(t,('listening',));require(ack is True,'question ended/stop requested');self.source_stop_requested=True;self.record('stop_question',{'actual_stop_observed':False},'question_release')
    def release(self,t,c):
        self.check(t,('question_release','response_release','reopen_release'));fields(c,('learner_released','source_stopped'));require(c['learner_released'] is True,'manual learner release')
        require(c['source_stopped'] is True if self.source_release_required else c['source_stopped'] is None,'manual pending external stop, no invented source confirmation')
        self.source_release_required=self.source_stop_requested=False;self.source_role=None
        if self.state=='reopen_release':
            s=self.resume;require(s is not None,'resume state');self.resume=None
        elif self.state=='response_release':s='reporting'
        else:s='write_echo' if self.phase==0 else 'next_chord' if self.phase==3 else 'sing_response'
        self.record('release',{'manual_confirmation':c,'actual_stop_verified':False},s)
    def commit_echo(self,t,notes):
        self.check(t,('write_echo',));require(type(notes) is list and len(notes)==4,'four written echo notes')
        for n in notes:
            require(type(n) is str,'typed written pitch')
            if n!='?':pitch(n)
        self.written=deepcopy(notes);self.written_history.append({'generation':self.generation,'cycle':self.cycle,'notes':deepcopy(notes)});self.record('written_echo',{'notes':notes},'committed')
    def reveal_question(self,t):self.check(t,('committed',));self.current_revealed=self.ever_revealed=True;self.record('reveal_question',{},'review_echo')
    def review_echo(self,t,r):
        self.check(t,('review_echo',));fields(r,('key','duties','diagnosis','notes'));fields(r['duties'],ECHO_DUTIES)
        require(r['key']==self.key and all(type(x) is str and x in YN for x in r['duties'].values()) and type(r['diagnosis']) is str and text(r['notes']),'complete written echo manual review')
        match=all(x!='?' for x in self.written) and [pitch(x) for x in self.written]==[pitch(x) for x in RAW[self.index][1].split('-')];ok=match and all(x=='yes' for x in r['duties'].values())
        if not ok:require(text(r['diagnosis']),'wrong/unknown/uncertain echo diagnosis')
        self.record('written_echo_review',{'response':r,'symbolic_pitch_match':match,'acoustic_performance_verified':False},'echo_plan' if ok else 'needs_retry')
    def choose_response(self,t,p):
        self.check(t,('echo_plan','response_plan'));require(self.phase==0 or self.echo_passed,'exact echo must be reproduced before invention');validate_response(p,self.phase,self.index,self.plan)
        self.responses[self.phase]=deepcopy(p);self.record('chosen_response',p,'sing_response' if self.phase==0 else 'ready_listen')
    def begin_next_chord(self,t,c):
        self.check(t,('next_chord',));fields(c,('chord','ready','held'));require(self.phase==3 and c['chord']==self.responses[3]['next_chord'] and c['ready'] is True and c['held'] is True,'exact chosen next chord present')
        self.source_release_required=True;self.source_stop_requested=False;self.source_role='held_next_chord';self.record('next_chord_present',{'confirmation':c,'audio_observed':False},'sing_response')
    def sung(self,t,ack):self.check(t,('sing_response',));require(ack is True,'chosen response singing attempted');self.record('sung_response',{},'silent_setup')
    def setup_targets(self,t,ack):self.check(t,('silent_setup',));require(ack is True,'silent preparation of each target');self.record('silent_setup',{},'play_response')
    def play_response(self,t,ack):self.check(t,('play_response',));require(ack is True,'four ordered target attacks attempted');self.record('play_response',{'actual_attack_counts_observed':None},'end_response')
    def end_response(self,t,ack):
        self.check(t,('end_response',));require(ack is True,'response ended/request source stop')
        if self.source_release_required:self.source_stop_requested=True
        self.record('end_response',{'manual_source_stop_requested':self.source_stop_requested,'actual_stop_observed':False},'response_release')
    def report(self,t,r):
        self.check(t,('reporting',));fields(r,('key','pass','midi','next_chord','attack_counts','duties','diagnosis','notes'));duties=PLAY_DUTIES+(('next_chord_present_during_response',) if self.phase==3 else ())
        fields(r['duties'],duties);midi4(r['midi']);response=self.responses[self.phase]
        require(r['key']==self.key and type(r['pass']) is int and r['pass']==self.phase+1 and r['midi']==response['midi'] and r['next_chord']==response['next_chord'],'exact current response report binding')
        require(type(r['attack_counts']) is list and len(r['attack_counts'])==4 and all(type(x) is int and x>=0 for x in r['attack_counts']),'four actual nonnegative attack counts')
        require(all(type(x) is str and x in YN for x in r['duties'].values()) and type(r['diagnosis']) is str and text(r['notes']),'complete manual response duties')
        ok=all(x==1 for x in r['attack_counts']) and all(x=='yes' for x in r['duties'].values())
        if not ok:require(text(r['diagnosis']),'failed/uncertain/attack-count diagnosis')
        if ok and self.phase==0:self.echo_passed=True
        self.record('response_report',{'response':r,'manual_requirements_reported':ok,'acoustic_performance_verified':False,'delayed_echo_mastery_claimed':False},'reported' if ok else 'needs_retry')
    def next_pass(self,t):
        self.check(t,('reported',));require(self.phase<3 and self.echo_passed,'four passes after exact echo');self.phase+=1;self.record('next_pass',{},'response_plan')
    def retry(self,t,diagnosis):self.check(t,('needs_retry','reported'));require(text(diagnosis),'same-pass retry diagnosis');self.record('retry',{'diagnosis':diagnosis},'ready_listen')
    def finish(self,t):self.check(t,('reported',));require(self.phase==3 and self.echo_passed,'all four passes required');self.record('finish',{'manual_only':True,'credit_awarded':False,'source_acceptance':False},'completed')
    def cancel(self,t):
        stable=('setup','ready_listen','write_echo','committed','review_echo','echo_plan','response_plan','reported','needs_retry','completed')
        self.check(t,stable+('listening','question_release','next_chord','sing_response','silent_setup','play_response','end_response','response_release','reporting','reopen_release'))
        if self.state!='reopen_release':self.resume=self.state if self.state in stable else 'ready_listen'
        if self.source_release_required:self.source_stop_requested=True
        self.generation+=1;self.record('cancel',{'manual_source_stop_requested':self.source_stop_requested,'actual_stop_observed':False},'cancelled')
    def reopen(self,t):self.check(t,('cancelled',));self.generation+=1;self.record('reopen',{},'reopen_release')

def contract(i):
    return {'schema_version':'fathom-private-four-pass-call-response.1','key':KEYS[i],'printed_chord':RAW[i][0],
      'printed_question':RAW[i][1].split('-'),'printed_answer_model':RAW[i][2].split('-'),'printed_exact_echo':'write/play exact',
      'printed_heading':'REPRODUCE THE QUESTION EXACTLY BEFORE INVENTING AN ANSWER','printed_footer':FOOTER,'paired_no_search':NO_SEARCH,
      'source_extent_header':'8 PAIRS | 64 SOURCE + 64 RESPONSE TONES','actual_printed_question_tokens':32,'actual_printed_answer_model_tokens':32,
      'source_note_events':[],'source_fixed_octave_rhythm_meter_fret_next_chord':None,
      'plan_schema':{'source':'actual external human, exact chosen question MIDI in guitar range40..88 with a feasible nonzero octave shift, four rational nonoverlapping note onsets/durations within chosen phrase length; capable of holding chosen next chord',
        'response':'four chosen MIDI and exact standard-tuning fret0..24 contacts; explicit basis; next_chord=None except pass4',
        'pass1':'exact question MIDI and rhythm, chosen only after written echo review',
        'pass2':'answer_model pitch order or own new pitch order, at least one changed pitch class; exact question rhythm',
        'pass3':'original question as explicit basis, nonzero uniform octave shift; same rhythm as authored finite option',
        'pass4':'explicit selected next chord from finite page vocabulary, four chosen chord tones and chosen rhythm with same total phrase length'},
      'response_schema':{'written_echo':'four pitch names or ?; explicit reveal and review before exact playing','echo_duties':list(ECHO_DUTIES),
        'playing_duties':list(PLAY_DUTIES),'pass4_extra_duty':'next_chord_present_during_response','manual_enum':list(YN),'attack_counts':'four nonnegative integers, positive report requires each exactly1'},
      'authored_policies':['No invention plan or answer-model learner display before exact echo has been played/reported. Source-player script remains available; prior reveal/written history retained, no blind/security claim.',
        'Chosen registers/rhythm/contacts are not source-fixed. Pass3 uses original question and uniform octave shift; pass4 uses four chord tones from an explicitly chosen next chord, never inferred from table adjacency. These finite options do not forbid other valid improvisation.',
        'External question ends/releases before response. In pass4 a separately confirmed next chord stays present while learner sings/plays; stop requested afterward/cancel, manual release required. No actual sound-stop or acoustic verification.',
        'One silent setup and one actual attack per target are manually reported; failed counts/no/uncertain require diagnosis and same-pass repeat. All four pass reports required.',
        'The answer model is a usable reference/choice, not automatically substituted for the learner response. Literal heading counts retained separately from32+32 printed pitch tokens.',
        'No clock or timed reaction/delayed-echo mastery claim; manual page11 completion is not workbook-wide mastery.'],
      'automatic_evaluation':False,'performance_observed':False,'audio_supplied':False,'audio_inspected':False,'timing_scheduled':False,
      'credit_awarded':False,'mastery_awarded':False,'persistence':False,'canonical_binding':None}
