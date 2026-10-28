"""Ordered manual dictation; literal final-I omission guarded by printed source."""
from copy import deepcopy
from uuid import uuid4
RAW=(('C','C-F-G-C','I-IV-V-I','T-P-D-T'),('G','G-C-D-G','I-IV-V-I','T-P-D-T'),
 ('D','Em-A-D-D','ii-V-I-I','P-D-T-T'),('A','A-E-F#m-D','I-V-vi-IV','T-D-T-P'),
 ('E','C#m-A-E-B','vi-IV-I-V','T-P-T-D'),('F','F-Gm-Bb-C','I-ii-IV-V','T-P-P-D'),
 ('C','C-Am-F-G','I-vi-IV-V','T-T-P-D'),('G','Am-D-G-G','ii-V-I-I','P-D-T-T'),
 ('D','D-A-Bm-G','I-V-vi-IV','T-D-T-P'),('A','F#m-D-A-E','vi-IV-I-V','T-P-T-D'),
 ('E','E-F#m-A-B','I-ii-IV-V','T-P-P-D'),('F','Dm-Bb-F-C','vi-IV-I-V','T-P-T-D'))
KEYS=tuple(f'exercise-completeness-r01/level077/moduleb/p006-t1-r{i+1}/{r[0].lower()}' for i,r in enumerate(RAW))
PC={'C':0,'G':7,'D':2,'A':9,'E':4,'F':5};TUNING={'E':40,'A':45,'D':50,'G':55,'B':59,'e':64}
ROMANS=('I','ii','iii','IV','V','vi','vii dim');YN=('yes','no','uncertain')
FIRST=('heard_all_four','source_order','function_shape_before_roman')
SECOND=('heard_exact_omission','sung_tonic_correct','nearest_triad_in_context','no_searching','single_silent_setup','tonic_triad_correct','source_order')
FOOTER='Second pass: source performer omits the tonic chord at the end. Player sings the tonic root, then plays the nearest tonic triad without searching.'
NO_SEARCH='After the target is sung, use one silent setup and one attack. Diagnose a wrong attack; do not slide around until the note is found.'
def literal(i):return RAW[i][2].split('-')[-1]=='I'
class Refusal(ValueError):pass
def require(ok,msg):
    if not ok:raise Refusal(msg)
def fields(o,keys):require(type(o) is dict and set(o)==set(keys),'exact field set')
def text(v):return type(v) is str and bool(v.strip())
def validate_plan(p,i):
    require(type(i) is int and 0<=i<12,'exact source index')
    fields(p,('prerequisites','provider','tonic_realization'));fields(p['prerequisites'],('own_instrument','original_workbook'))
    require(all(x is True for x in p['prerequisites'].values()),'manual prerequisites')
    v=p['provider'];fields(v,('kind','full_reference','omission_reference','ready'))
    require(type(v['kind']) is str and v['kind'] in ('external_human','external_recording') and text(v['full_reference']) and v['ready'] is True,'capable external full-progression source')
    if not literal(i):
        require(v['omission_reference'] is None and p['tonic_realization'] is None,'non-I ending: secondary interpretation Pending; no invented omission/tonic')
        return
    require(text(v['omission_reference']),'source of exact prefix with terminal tonic omitted')
    c=p['tonic_realization'];fields(c,('sung_tonic_midi','current_hand_context','nearest_basis','triad'))
    require(type(c['sung_tonic_midi']) is int and 0<=c['sung_tonic_midi']<=127 and c['sung_tonic_midi']%12==PC[RAW[i][0]],'chosen sung tonic pitch class')
    require(text(c['current_hand_context']) and text(c['nearest_basis']),'contextual nearest judgement declared, no automatic distance metric')
    triad=c['triad'];require(type(triad) is list and len(triad)==3,'chosen three-tone tonic triad');strings=[];pcs=[]
    for contact in triad:
        fields(contact,('string','fret'));s=contact['string'];f=contact['fret']
        require(type(s) is str and s in TUNING and type(f) is int and 0<=f<=24,'chosen standard-tuning fret contact')
        strings.append(s);pcs.append((TUNING[s]+f)%12)
    root=PC[RAW[i][0]];require(len(set(strings))==3 and set(pcs)=={root,(root+4)%12,(root+7)%12},'three distinct strings, all exact major-tonic triad pitch classes')

class ProgressionFlow:
    def __init__(self,key):
        require(type(key) is str and key in KEYS,'exact twelve source keys');self.key=key;self.index=KEYS.index(key);self.instance=uuid4().hex
        self.generation=self.phase=self.cycle=self.action=0;self.state='setup';self.plan=None;self.resume=None
        self.history=[];self.answers={};self.answer_history=[];self.ever_revealed=False;self.current_revealed=False
    def token(self):return (self.instance,self.key,self.generation,self.phase,self.cycle,self.action,self.state)
    def check(self,t,states):require(type(t) is tuple and t==self.token(),'current source/pass/action owner');require(self.state in states,'wrong state')
    def record(self,kind,data,state):
        self.history.append({'kind':kind,'generation':self.generation,'pass':self.phase,'cycle':self.cycle,'data':deepcopy(data)});self.action+=1;self.state=state
    def set_plan(self,t,p):
        self.check(t,('setup','ready','reported','needs_retry','completed'));validate_plan(p,self.index);self.plan=deepcopy(p)
        self.generation+=1;self.phase=self.cycle=0;self.answers={};self.current_revealed=False;self.record('plan',p,'ready')
    def source_view(self):
        key,chords,roman,functions=RAW[self.index];full=chords.split('-')
        if self.phase:require(literal(self.index),'no secondary script before source interpretation')
        return {'key':key,'full_printed_chords':full,'roman':roman.split('-'),'function':functions.split('-'),
          'performed_chord_script':full if self.phase==0 else full[:-1],
          'removed_only_final_source_index':None if self.phase==0 else 4,'audio_supplied':False,'source_fixed_note_events':[],
          'secondary_available':literal(self.index),'secondary_barrier':None if literal(self.index) else 'printed terminal chord is not I; footer omission interpretation Pending'}
    def learner_view(self):
        out={'key':RAW[self.index][0],'pass':self.phase,'state':self.state,'answers':deepcopy(self.answers) if self.phase==0 else {},
          'previously_revealed':self.ever_revealed,'prior_answers_retained':bool(self.answer_history),'blind_assessment_claim':False,
          'secondary_available':literal(self.index)}
        if self.current_revealed:out['reference_answer']=self.source_view()
        if self.phase:out['chosen_tonic_realization']=deepcopy(self.plan['tonic_realization'])
        return out
    def begin(self,t,ready):
        self.check(t,('ready',));require(ready is True,'current source readiness');self.cycle+=1
        if self.phase==0:self.answers={};self.current_revealed=False
        self.record('begin',{'script':self.source_view()['performed_chord_script'],'audio_observed':False},'listening')
    def end_listening(self,t,ack):self.check(t,('listening',));require(ack is True,'external listening ended');self.record('end_listening',{},'listening_release')
    def release(self,t,ack):
        self.check(t,('listening_release','attack_release','reopen_release'));require(ack is True,'manual physical release')
        if self.state=='reopen_release':
            state=self.resume;require(state is not None,'resume state');self.resume=None;self.record('reopen_release',{},state)
        elif self.state=='attack_release':self.record('release',{},'tonic_report')
        else:self.record('release',{},'answer_function' if self.phase==0 else 'sing_tonic')
    def answer(self,t,kind,value):
        require(type(kind) is str and kind in ('function','roman'),'answer kind');self.check(t,('answer_'+kind,))
        allowed=('T','P','D') if kind=='function' else ROMANS
        require(type(value) is list and len(value)==4 and all(type(x) is str and x in allowed for x in value),'four typed ordered responses')
        self.answers[kind]=deepcopy(value);self.answer_history.append({'generation':self.generation,'cycle':self.cycle,'kind':kind,'value':deepcopy(value)})
        self.record('answer_'+kind,{'value':value},'answer_roman' if kind=='function' else 'committed')
    def reveal(self,t):
        self.check(t,('committed',));require(set(self.answers)=={'function','roman'},'function then Roman responses required')
        self.ever_revealed=self.current_revealed=True;self.record('reveal',{'source':self.source_view()},'dictation_report')
    def report_dictation(self,t,r):
        self.check(t,('dictation_report',));fields(r,('key','duties','diagnosis','notes'));fields(r['duties'],FIRST)
        require(r['key']==RAW[self.index][0] and all(type(x) is str and x in YN for x in r['duties'].values()) and type(r['diagnosis']) is str and text(r['notes']),'complete bound manual dictation report')
        source=self.source_view();matches={k:self.answers[k]==source[k] for k in ('function','roman')};ok=all(matches.values()) and all(x=='yes' for x in r['duties'].values())
        if not ok:require(text(r['diagnosis']),'wrong/uncertain dictation diagnosis')
        self.record('dictation_report',{'response':r,'answers':self.answers,'symbolic_matches':matches,'manual_requirements_reported':ok,'performance_verified':False},'reported' if ok else 'needs_retry')
    def next_pass(self,t):
        self.check(t,('reported',));require(self.phase==0,'only two passes');require(literal(self.index),'terminal source chord is not I; secondary interpretation Pending')
        self.phase=1;self.cycle=0;self.current_revealed=False;self.record('next_pass',{},'ready')
    def sung(self,t,ack):self.check(t,('sing_tonic',));require(ack is True,'tonic singing attempted');self.record('sing_tonic',{},'silent_setup')
    def setup_target(self,t,ack):self.check(t,('silent_setup',));require(ack is True,'single silent setup');self.record('silent_setup',{},'attack')
    def attempt_attack(self,t,ack):self.check(t,('attack',));require(ack is True,'one tonic triad attack attempted');self.record('attack_attempt',{'actual_attack_count_observed':None},'attack_release')
    def report_tonic(self,t,r):
        self.check(t,('tonic_report',));fields(r,('key','chosen_triad','attack_count','duties','diagnosis','notes'));fields(r['duties'],SECOND)
        require(r['key']==RAW[self.index][0] and r['chosen_triad']==self.plan['tonic_realization']['triad'],'exact source/key/chosen triad response binding')
        require(type(r['chosen_triad']) is list and all(type(c) is dict and set(c)=={'string','fret'} and type(c['fret']) is int for c in r['chosen_triad']),'typed triad response')
        require(type(r['attack_count']) is int and r['attack_count']>=0 and all(type(x) is str and x in YN for x in r['duties'].values()) and type(r['diagnosis']) is str and text(r['notes']),'complete manual tonic report')
        ok=r['attack_count']==1 and all(x=='yes' for x in r['duties'].values())
        if not ok:require(text(r['diagnosis']),'failed/uncertain/extra attack diagnosis')
        self.record('tonic_report',{'response':r,'manual_requirements_reported':ok,'performance_verified':False,'nearest_distance_automatically_evaluated':False},'reported' if ok else 'needs_retry')
    def retry(self,t,diagnosis):self.check(t,('reported','needs_retry'));require(text(diagnosis),'retry diagnosis');self.record('retry',{'diagnosis':diagnosis},'ready')
    def finish(self,t):
        self.check(t,('reported',));require(self.phase==1 and literal(self.index),'whole contract requires resolved source omission and both passes')
        self.record('finish',{'manual_only':True,'mastery_awarded':False,'source_acceptance':False},'completed')
    def cancel(self,t):
        self.check(t,('setup','ready','listening','listening_release','answer_function','answer_roman','committed','dictation_report','sing_tonic','silent_setup','attack','attack_release','tonic_report','reported','needs_retry','completed','reopen_release'))
        if self.state!='reopen_release':self.resume=self.state if self.state in ('setup','ready','reported','needs_retry','completed') else 'ready'
        self.generation+=1;self.record('cancel',{},'cancelled')
    def reopen(self,t):self.check(t,('cancelled',));self.generation+=1;self.record('reopen',{},'reopen_release')

def contract(i):
    key,chords,roman,functions=RAW[i]
    return {'schema_version':'fathom-private-progression-dictation-manual.1','key':KEYS[i],
      'source_fields':{'Key':key,'Source progression':chords,'Roman answer':roman,'Function answer':functions},
      'source_heading':'WRITE T-P-D-T SHAPE BEFORE ROMAN NUMERALS','source_extent_header':'12 PROGRESSIONS | 96 CHORD EVENTS',
      'ordered_harmonic_slots':[{'source_order':j+1,'chord':c,'roman':r,'function':f,'onset':None,'duration':None} for j,(c,r,f) in enumerate(zip(chords.split('-'),roman.split('-'),functions.split('-')))],
      'source_footer':FOOTER,'source_no_search':NO_SEARCH,'source_note_events':[],'source_fixed_note_octave_fret_timing':None,
      'primary_dictation_available':True,'secondary_literal_omission_available':literal(i),
      'secondary_source_prefix':chords.split('-')[:-1] if literal(i) else None,
      'secondary_pending_reason':None if literal(i) else {'printed_final_chord':chords.split('-')[-1],'printed_final_roman':roman.split('-')[-1],'missing_interpretation':'How to omit a terminal tonic when printed final chord is not I; no source rewrite adopted.'},
      'plan_schema':{'external_source':['external_human','external_recording'],'primary_reference':'exact printed four-chord performance',
        'secondary_reference':'exact first three source chords only for literal terminal-I rows; otherwise None',
        'tonic_realization':'authored sung tonic MIDI, hand context, nearest-basis explanation and three distinct standard-tuning string/fret contacts containing I major triad; otherwise None'},
      'response_schema':{'dictation_order':['four function letters','four Roman answers','explicit reveal','manual hearing report'],
        'primary_duties':list(FIRST),'secondary_duties':list(SECOND),'manual_enum':list(YN),'secondary_actual_attack_count':'nonnegative integer; positive report exactly one'},
      'authored_policies':['First-pass answers are symbolic typed sequences; actual hearing is self-report. Learner current reference withheld until explicit reveal, previous reveal/history retained.',
        'Only final printed chord is omitted in second pass; any penultimate I remains. Non-I final rows permit primary dictation but refuse whole completion pending source interpretation.',
        'Chosen sung MIDI and tonic triad contacts are not source-fixed notes. Nearest is a contextual manual judgement; no invented physical distance metric.',
        'One silent setup and attack; failed count/no/uncertain duties require diagnosis/retry of current pass; no search correction.',
        'Current action tokens/release/cancel/reopen/new-plan fences; source-player script retained; views are not security against reading source files.',
        'Literal96 CHORD EVENTS heading retained separately from48 printed chord tokens; no extra source events manufactured.'],
      'automatic_evaluation':False,'performance_observed':False,'audio_supplied':False,'audio_inspected':False,'timing_scheduled':False,
      'credit_awarded':False,'mastery_awarded':False,'persistence':False,'canonical_binding':None}
