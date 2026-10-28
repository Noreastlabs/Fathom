"""Eight printed phrases: three written layers before chosen manual guitar targets."""
from copy import deepcopy
from uuid import uuid4
import re

RAW=(('C major','1-2-3-5-3-2-1','C-D-E-G-E-D-C'),
 ('C major','5-6-5-3-2-1','G-A-G-E-D-C'),
 ('G major','1-3-2-5-4-3-2-1','G-B-A-D-C-B-A-G'),
 ('D major','5-3-2-1-7-1','A-F#-E-D-C#-D'),
 ('A minor','1-b3-4-5-b7-5-b3-1','A-C-D-E-G-E-C-A'),
 ('E minor','5-4-b3-2-1','B-A-G-F#-E'),
 ('A harmonic minor','5-b6-7-1-7-5','E-F-G#-A-G#-E'),
 ('A melodic minor','1-2-b3-5-6-7-1','A-B-C-E-F#-G#-A'))
KEYS=tuple(f'exercise-completeness-r01/level077/moduled/p009-t1-r{i+1}/{r[0].lower().replace(" ","")}' for i,r in enumerate(RAW))
TUNING={'E':40,'A':45,'D':50,'G':55,'B':59,'e':64}
LAYERS=('contour','degrees','notes');YN=('yes','no','uncertain');CONFIDENCE=('low','medium','high','uncertain')
DICTATION_DUTIES=('heard_same_chosen_phrase','heard_all_source_notes','source_order','no_guitar_before_three_commits')
TARGET_DUTIES=('heard_target_before_hand_moves','sung_target_correct','single_silent_setup','no_searching','played_target_correct','source_order')
FOOTER='Three passes: 1) U/D/S contour only. 2) scale degrees. 3) exact notes. The guitar is used only after all three written layers are committed.'
NO_SEARCH='After the target is sung, use one silent setup and one attack. Diagnose a wrong attack; do not slide around until the note is found.'
class Refusal(ValueError):pass
def require(ok,msg):
    if not ok:raise Refusal(msg)
def fields(x,names):require(type(x) is dict and set(x)==set(names),'exact typed field set')
def text(x):return type(x) is str and bool(x.strip())
def pitch(x):
    require(type(x) is str and re.fullmatch(r'[A-G](?:#|b)?',x) is not None,'symbolic pitch spelling')
    return ({'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}[x[0]]+({'#':1,'b':-1}.get(x[1:],0)))%12
def contour(midi):return ['U' if b>a else 'D' if b<a else 'S' for a,b in zip(midi,midi[1:])]
def validate_source_plan(p,i):
    require(type(i) is int and 0<=i<8,'exact source index')
    fields(p,('prerequisites','provider'));fields(p['prerequisites'],('own_instrument','original_workbook'))
    require(all(v is True for v in p['prerequisites'].values()),'manual prerequisites')
    q=p['provider'];fields(q,('kind','reference','ready','chosen_midi','chosen_timing'))
    require(q['kind']=='external_human' and text(q['reference']) and q['ready'] is True and text(q['chosen_timing']),'actual external source player and chosen timing')
    notes=RAW[i][2].split('-');m=q['chosen_midi']
    require(type(m) is list and len(m)==len(notes) and all(type(n) is int and 0<=n<=127 for n in m),'chosen source MIDI sequence')
    require([n%12 for n in m]==[pitch(n) for n in notes],'exact printed source pitch-class order')
def validate_guitar_plan(p,midi):
    fields(p,('sung_midi','contacts'));m=p['sung_midi'];c=p['contacts']
    require(type(m) is list and len(m)==len(midi) and all(type(n) is int and 0<=n<=127 for n in m),'chosen sung MIDI sequence')
    shifts=[a-b for a,b in zip(m,midi)];require(len(set(shifts))==1 and shifts[0]%12==0,'uniform authored octave transposition preserving heard contour')
    require(type(c) is list and len(c)==len(m),'one chosen contact for each source note')
    for n,x in zip(m,c):
        fields(x,('string','fret'));s=x['string'];f=x['fret']
        require(type(s) is str and s in TUNING and type(f) is int and 0<=f<=24 and TUNING[s]+f==n,'exact chosen standard-tuning contact')

class MelodyFlow:
    def __init__(self,key):
        require(type(key) is str and key in KEYS,'exact eight page-9 source keys');self.key=key;self.index=KEYS.index(key);self.instance=uuid4().hex
        self.generation=self.layer=self.target=self.cycle=self.action=0;self.state='setup';self.plan=self.guitar=None;self.resume=None
        self.answers={};self.answer_history=[];self.history=[];self.ever_revealed=False;self.current_revealed=False
        self.source_release_required=False;self.source_stop_requested=False
    def token(self):return (self.instance,self.key,self.generation,self.layer,self.target,self.cycle,self.action,self.state)
    def check(self,t,states):require(type(t) is tuple and t==self.token(),'current source/layer/target/action owner');require(self.state in states,'wrong state')
    def record(self,kind,data,state):
        self.history.append({'kind':kind,'generation':self.generation,'layer':self.layer,'target':self.target,'cycle':self.cycle,'data':deepcopy(data)})
        self.action+=1;self.state=state
    def set_source_plan(self,t,p):
        self.check(t,('setup','dictation_retry','completed'));require(not self.source_release_required,'source release pending');validate_source_plan(p,self.index)
        self.plan=deepcopy(p);self.guitar=None;self.generation+=1;self.layer=self.target=self.cycle=0;self.answers={};self.current_revealed=False
        self.record('source_plan',p,'ready_listen')
    def source_player_view(self):
        context,degrees,notes=RAW[self.index]
        out={'key':self.key,'context':context,'printed_degrees':degrees.split('-'),'printed_notes':notes.split('-'),
          'chosen_midi':None if self.plan is None else deepcopy(self.plan['provider']['chosen_midi']),
          'chosen_timing':None if self.plan is None else self.plan['provider']['chosen_timing'],
          'printed_octave_rhythm':None,'audio_supplied_by_app':False,'source_stop_requested':self.source_stop_requested,
          'source_release_required':self.source_release_required,
          'instruction':'Stop source sound and confirm manually' if self.source_stop_requested else 'Repeat the same chosen source phrase for contour, degrees and notes; learner guitar remains unused until all three written commits.'}
        if self.plan:out['chosen_contour']=contour(self.plan['provider']['chosen_midi'])
        return out
    def learner_view(self):
        out={'context':RAW[self.index][0],'state':self.state,'layer':LAYERS[self.layer],'answers':deepcopy(self.answers),
          'previously_revealed':self.ever_revealed,'prior_answers_retained':bool(self.answer_history),'blind_assessment_claim':False}
        if self.current_revealed:out['reference_answer']=self.source_player_view()
        if self.guitar is not None:out['current_target']={'source_order':self.target+1,'note':RAW[self.index][2].split('-')[self.target],
          'chosen_sung_midi':self.guitar['sung_midi'][self.target],'chosen_contact':deepcopy(self.guitar['contacts'][self.target])}
        return out
    def begin_listening(self,t,confirmation):
        self.check(t,('ready_listen',));fields(confirmation,('key','ready','same_chosen_phrase'))
        require(confirmation['key']==self.key and confirmation['ready'] is True and confirmation['same_chosen_phrase'] is True,'current source-player readiness and same chosen phrase')
        self.cycle+=1;self.source_release_required=True;self.source_stop_requested=False
        self.record('listen',{'confirmation':confirmation,'audio_observed':False},'listening')
    def end_listening(self,t,ack):
        self.check(t,('listening',));require(ack is True,'listening ended and external stop requested');self.source_stop_requested=True
        self.record('request_source_stop',{'actual_sound_stop_observed':False},'listening_release')
    def release(self,t,r):
        self.check(t,('listening_release','attack_release','reopen_release'));fields(r,('learner_released','source_stopped'))
        require(r['learner_released'] is True,'manual learner release')
        require(r['source_stopped'] is True if self.source_release_required else r['source_stopped'] is None,'manual pending source stop, no invented source confirmation')
        self.source_release_required=self.source_stop_requested=False
        if self.state=='reopen_release':
            state=self.resume;require(state is not None,'resume state');self.resume=None
        else:state='writing' if self.state=='listening_release' else 'target_report'
        self.record('release',{'manual_confirmation':r,'sound_stop_verified':False},state)
    def commit(self,t,kind,value,confidence):
        self.check(t,('writing',));require(type(kind) is str and kind==LAYERS[self.layer],'current ordered written layer')
        n=len(RAW[self.index][2].split('-'))-(kind=='contour')
        require(type(value) is list and len(value)==n and all(type(x) is str for x in value),'complete typed ordered response')
        if kind=='contour':require(all(x in ('U','D','S','?') for x in value),'U/D/S or explicit unknown')
        elif kind=='degrees':require(all(x=='?' or re.fullmatch(r'(?:b|#)?[1-7]',x) for x in value),'degree tokens or explicit unknown')
        else:
            for x in value:
                if x!='?':pitch(x)
        require(type(confidence) is str and confidence in CONFIDENCE,'manual confidence')
        r={'tokens':deepcopy(value),'confidence':confidence};self.answers[kind]=r
        self.answer_history.append({'generation':self.generation,'cycle':self.cycle,'kind':kind,'response':deepcopy(r)})
        state='committed' if self.layer==2 else 'ready_listen'
        if self.layer<2:self.layer+=1
        self.record('commit_'+kind,r,state)
    def reveal(self,t):
        self.check(t,('committed',));require(set(self.answers)==set(LAYERS),'all three written layers committed')
        self.current_revealed=self.ever_revealed=True;self.record('reveal',{'source_reference':self.source_player_view()},'dictation_report')
    def symbolic_matches(self):
        require(set(self.answers)==set(LAYERS) and self.plan is not None,'committed symbolic responses')
        notes=self.answers['notes']['tokens']
        return {'contour':self.answers['contour']['tokens']==contour(self.plan['provider']['chosen_midi']),
          'degrees':self.answers['degrees']['tokens']==RAW[self.index][1].split('-'),
          'notes':all(x!='?' for x in notes) and [pitch(x) for x in notes]==[pitch(x) for x in RAW[self.index][2].split('-')]}
    def report_dictation(self,t,r):
        self.check(t,('dictation_report',));fields(r,('key','duties','diagnosis','notes'));fields(r['duties'],DICTATION_DUTIES)
        require(r['key']==self.key and all(type(x) is str and x in YN for x in r['duties'].values()) and type(r['diagnosis']) is str and text(r['notes']),'complete bound manual dictation report')
        matches=self.symbolic_matches();ok=all(matches.values()) and all(x=='yes' for x in r['duties'].values())
        if not ok:require(text(r['diagnosis']),'wrong/unknown/uncertain response diagnosis')
        self.record('dictation_report',{'response':r,'symbolic_matches':matches,'manual_requirements_reported':ok,'performance_verified':False},'guitar_plan' if ok else 'dictation_retry')
    def repeat_dictation(self,t,diagnosis):
        self.check(t,('dictation_retry',));require(text(diagnosis),'repeat diagnosis');self.layer=self.target=0;self.answers={};self.current_revealed=False
        self.record('repeat_three_passes',{'diagnosis':diagnosis},'ready_listen')
    def set_guitar_plan(self,t,p):
        self.check(t,('guitar_plan',));validate_guitar_plan(p,self.plan['provider']['chosen_midi']);self.guitar=deepcopy(p);self.target=0
        self.record('chosen_guitar_realization',p,'target_ready')
    def begin_target(self,t,ready):
        self.check(t,('target_ready',));require(ready is True,'current target ready');self.cycle+=1;self.record('begin_target',{},'sing_target')
    def sung(self,t,ack):self.check(t,('sing_target',));require(ack is True,'target singing attempted');self.record('sung',{},'silent_setup')
    def setup_target(self,t,ack):self.check(t,('silent_setup',));require(ack is True,'one silent setup');self.record('silent_setup',{},'attack')
    def attack(self,t,ack):self.check(t,('attack',));require(ack is True,'one decisive attack attempted');self.record('attack_attempt',{'actual_attack_count_observed':None},'attack_release')
    def report_target(self,t,r):
        self.check(t,('target_report',));fields(r,('key','source_order','chosen_contact','attack_count','duties','diagnosis','notes'));fields(r['duties'],TARGET_DUTIES)
        fields(r['chosen_contact'],('string','fret'))
        require(r['key']==self.key and type(r['source_order']) is int and r['source_order']==self.target+1 and type(r['chosen_contact']['fret']) is int and r['chosen_contact']==self.guitar['contacts'][self.target],'exact source/target/chosen contact binding')
        require(type(r['attack_count']) is int and r['attack_count']>=0 and all(type(x) is str and x in YN for x in r['duties'].values()) and type(r['diagnosis']) is str and text(r['notes']),'complete manual target report')
        ok=r['attack_count']==1 and all(x=='yes' for x in r['duties'].values())
        if not ok:require(text(r['diagnosis']),'failed/uncertain/count diagnosis')
        self.record('target_report',{'response':r,'manual_requirements_reported':ok,'performance_verified':False},'target_reported' if ok else 'target_retry')
    def repeat_target(self,t,diagnosis):self.check(t,('target_retry','target_reported'));require(text(diagnosis),'repeat diagnosis');self.record('repeat_target',{'diagnosis':diagnosis},'target_ready')
    def next_target(self,t):
        self.check(t,('target_reported',));require(self.target+1<len(RAW[self.index][2].split('-')),'no extra source note');self.target+=1;self.record('next_target',{},'target_ready')
    def finish(self,t):
        self.check(t,('target_reported',));require(self.target+1==len(RAW[self.index][2].split('-')),'all source note targets required')
        self.record('finish',{'manual_only':True,'mastery_awarded':False,'source_acceptance':False},'completed')
    def cancel(self,t):
        stable=('setup','ready_listen','writing','committed','dictation_report','dictation_retry','guitar_plan','target_ready','target_reported','target_retry','completed')
        self.check(t,stable+('listening','listening_release','sing_target','silent_setup','attack','attack_release','target_report','reopen_release'))
        if self.state!='reopen_release':self.resume=self.state if self.state in stable else 'ready_listen' if self.state in ('listening','listening_release') else 'target_ready'
        if self.source_release_required:self.source_stop_requested=True
        self.generation+=1;self.record('cancel',{'source_stop_requested':self.source_stop_requested,'actual_sound_stop_observed':False},'cancelled')
    def reopen(self,t):self.check(t,('cancelled',));self.generation+=1;self.record('reopen',{},'reopen_release')

def contract(i):
    context,degrees,notes=RAW[i]
    return {'schema_version':'fathom-private-three-layer-melodic-dictation.1','key':KEYS[i],
      'printed_context':context,'printed_degrees':degrees.split('-'),'printed_notes':notes.split('-'),
      'printed_page_footer':FOOTER,'source_no_search':NO_SEARCH,'source_extent_header':'8 PHRASES | 64 TONES',
      'actual_eight_row_pitch_token_count':53,'source_note_events':[],'printed_octave_rhythm_tempo_fret':None,
      'plan_schema':{'source':'external human reference/readiness, chosen MIDI matching printed pitch classes, descriptive chosen timing repeated unchanged across three passes',
        'guitar':'available only after three commits and manual reference review; chosen sung MIDI as uniform octave shift of source-player realization plus exact standard-tuning fret0..24 contacts'},
      'response_schema':{'ordered_written_layers':list(LAYERS),'contour_length':'N-1 transitions','degree_note_lengths':'N source tokens',
        'unknown_token':'?','confidence':list(CONFIDENCE),'dictation_duties':list(DICTATION_DUTIES),'target_duties':list(TARGET_DUTIES),
        'manual_enum':list(YN),'actual_attack_count':'nonnegative integer; positive target report exactly one'},
      'authored_policies':['Three external hearings, each followed by stop/release and commitment of only its current written layer; all three required before reference reveal or guitar.',
        'The printed pitch classes do not fix octave direction. Contour is derived only from the explicitly chosen external source MIDI realization; timing remains source-player chosen, unscored and unscheduled.',
        'Source-player answer/realization stays available to that role. Learner reference requires explicit reveal; previous reveal and answer history persist. Views do not prevent reading the workbook.',
        'Symbolic reference comparisons and manual duties gate later guitar; this gate is authored, while commitment before guitar is printed. No acoustic verification or numeric outcome.',
        'One sung target, silent setup, decisive attack and release per note applies the paired TXT no-search rule. Chosen contacts and octave shift are not printed source facts.',
        'Explicit unknown/wrong/uncertain written results require diagnosis and repeat of all three passes; negative/uncertain/extra-attack guitar results require same-note diagnosis/repeat.',
        'Cancel requests external stop without claiming actual silence; manual release is required before resume. Current owner/action tokens refuse stale callbacks.',
        'Literal64-tone heading retained separately from53 printed pitch tokens. No extra source notes or keys are manufactured.'],
      'automatic_evaluation':False,'performance_observed':False,'audio_supplied':False,'audio_inspected':False,'timing_scheduled':False,
      'credit_awarded':False,'mastery_awarded':False,'persistence':False,'canonical_binding':None}
