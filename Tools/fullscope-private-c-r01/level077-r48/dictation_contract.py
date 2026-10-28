"""Exact interval dictation and named fretboard passes; source/player custody is explicit."""
from copy import deepcopy
from uuid import uuid4
LABELS=('m2','M2','m3','M3','P4','TT','P5','m6','M6','m7','M7','P8')
RAW=(('C','Db','up','m2'),('D','E','up','M2'),('E','G','up','m3'),('F','A','up','M3'),('G','C','up','P4'),('A','D#','up','TT'),
 ('B','F#','up','P5'),('C','Ab','up','m6'),('D','B','up','M6'),('E','D','up','m7'),('F','E','up','M7'),('G','G','up','P8'),
 ('B','Bb','down','m2'),('A','G','down','M2'),('G','E','down','m3'),('F#','D','down','M3'),('E','B','down','P4'),('D','Ab','down','TT'),
 ('C','F','down','P5'),('B','D','down','m6'),('A','C','down','M6'),('E','E','down','P8'))
CARD=tuple(range(1,22))+(24,)
KEYS=tuple(f'exercise-completeness-r01/level077/modulea/p003-t1-r{n}/{n}' for n in range(1,22))+('exercise-completeness-r01/level077/modulea/p003-t1-r25/24',)
PC={'C':0,'B#':0,'C#':1,'Db':1,'D':2,'D#':3,'Eb':3,'E':4,'Fb':4,'E#':5,'F':5,'F#':6,'Gb':6,'G':7,'G#':8,'Ab':8,'A':9,'A#':10,'Bb':10,'B':11,'Cb':11}
TUNING={'E':40,'A':45,'D':50,'G':55,'B':59,'e':64};YN=('yes','no','uncertain')
FOOTER='Fretboard pass: source names only the starting note and interval. Player sings the destination, then plays it on a specified string without first playing the root.'
NO_SEARCH='After the target is sung, use one silent setup and one attack. Diagnose a wrong attack; do not slide around until the note is found.'
FRET_DUTIES=('prompt_named_only_start_interval','sung_destination','single_silent_setup','no_first_root_play','no_searching','played_correct_target','played_on_specified_string')
class Refusal(ValueError):pass
def require(ok,msg):
    if not ok:raise Refusal(msg)
def fields(o,keys):require(type(o) is dict and set(o)==set(keys),'field set')
def text(x):return type(x) is str and bool(x.strip())
def delta(i):return (LABELS.index(RAW[i][3])+1)*(1 if RAW[i][2]=='up' else -1)
def validate_plan(p,i):
    require(i!=19,'card20 source interval/pitch reconciliation Pending')
    fields(p,('prerequisites','provider','start_midi','destination_midi','specified_string'))
    fields(p['prerequisites'],('own_instrument','original_workbook'));require(all(x is True for x in p['prerequisites'].values()),'manual prerequisites')
    provider=p['provider'];fields(provider,('kind','reference','ready'));require(provider['kind'] in ('external_human','external_recording') and text(provider['reference']) and provider['ready'] is True,'capable external source')
    a=p['start_midi'];b=p['destination_midi'];require(type(a) is int and type(b) is int and 0<=a<=127 and 0<=b<=127 and a%12==PC[RAW[i][0]] and b%12==PC[RAW[i][1]] and b-a==delta(i),'exact chosen signed source interval')
    string=p['specified_string'];require(type(string) is str and string in TUNING and 0<=b-TUNING[string]<=24,'specified string can realize destination')
class DictationFlow:
    def __init__(self,key):
        require(key in KEYS,'exact22officialchildren');require(KEYS.index(key)!=19,'card20 source interval/pitch reconciliation Pending');self.key=key;self.index=KEYS.index(key);self.instance=uuid4().hex
        self.generation=self.phase=self.cycle=self.action=0;self.state='setup';self.plan=None;self.history=[];self.resume=None;self.answers={};self.ever_revealed=False
    def token(self):return (self.instance,self.key,self.generation,self.phase,self.cycle,self.action,self.state)
    def check(self,t,states):require(type(t) is tuple and t==self.token(),'stale/foreign token');require(self.state in states,'wrong state')
    def record(self,kind,data,state):
        self.history.append({'kind':kind,'generation':self.generation,'pass':self.phase,'cycle':self.cycle,'data':deepcopy(data)});self.action+=1;self.state=state
    def set_plan(self,t,p):
        self.check(t,('setup','ready','needs_retry','reported','completed'));validate_plan(p,self.index);self.plan=deepcopy(p)
        self.generation+=1;self.phase=self.cycle=0;self.answers={};self.record('plan',p,'ready')
    def source_view(self):
        require(self.plan is not None,'plan required');a,b,d,q=RAW[self.index]
        return {'card':CARD[self.index],'start':a,'destination':b,'direction':d,'interval':q,'chosen_start_midi':self.plan['start_midi'],
          'chosen_destination_midi':self.plan['destination_midi'],'specified_string':self.plan['specified_string'],
          'chosen_destination_fret':self.plan['destination_midi']-TUNING[self.plan['specified_string']],
          'supply':'actual interval pair' if self.phase==0 else 'name only starting note and interval; retain direction and specified string context',
          'audio_supplied':False}
    def learner_view(self):
        out={'card':CARD[self.index],'pass':'dictation' if self.phase==0 else 'fretboard','state':self.state,'previously_revealed':self.ever_revealed,'learner_answers':deepcopy(self.answers) if self.phase==0 else {},'prior_responses_retained':bool(self.answers)}
        if self.phase==1 and self.plan is not None:out['prompt']={'start':RAW[self.index][0],'interval':RAW[self.index][3],'direction':RAW[self.index][2],'specified_string':self.plan['specified_string']}
        if self.state in ('review','reported','needs_retry','completed') and self.ever_revealed:out['source_answer']=self.source_view()
        return out
    def begin(self,t,ready):
        self.check(t,('ready',));require(ready is True,'current external source readiness');self.cycle+=1
        if self.phase==0:self.answers={}
        self.record('begin',{'actual_audio_supplied':False},'listening' if self.phase==0 else 'hearing_prompt')
    def end_listening(self,t,ack):self.check(t,('listening',));require(ack is True,'pair listening ended');self.record('end_listening',{},'await_release')
    def release(self,t,ack):
        self.check(t,('await_release','reopen_release'));require(ack is True,'manual physical release')
        if self.state=='await_release':self.record('release',{},'answer_quality' if self.phase==0 else 'fret_report')
        else:
            state=self.resume;require(state is not None,'resume');self.resume=None;self.record('reopen_release',{},state)
    def answer_quality(self,t,value):
        self.check(t,('answer_quality',));require(text(value),'manual interval answer');self.answers['quality']=value;self.record('quality_answer',{'value':value},'answer_pitch')
    def answer_pitch(self,t,value):
        self.check(t,('answer_pitch',));require(type(value) is str and value in PC,'recognized manual pitch name');self.answers['pitch']=value;self.record('pitch_answer',{'value':value},'committed')
    def reveal(self,t):
        self.check(t,('committed',));require(self.phase==0 and set(self.answers)=={'quality','pitch'},'both responses before reveal');self.ever_revealed=True;self.record('reveal',{'source':self.source_view()},'review')
    def review_dictation(self,t,r):
        self.check(t,('review',));fields(r,('heard_pair','diagnosis','notes'));require(r['heard_pair'] in YN and type(r['diagnosis']) is str and text(r['notes']),'manual hearing report')
        quality=self.answers['quality']==RAW[self.index][3];pitch=PC[self.answers['pitch']]==PC[RAW[self.index][1]];ok=quality and pitch and r['heard_pair']=='yes'
        if not ok:require(text(r['diagnosis']),'wrong/uncertain response diagnosis')
        self.record('dictation_review',{'response':r,'answers':self.answers,'quality_symbolic_match':quality,'pitch_class_symbolic_match':pitch,
          'source_spelling_match':self.answers['pitch']==RAW[self.index][1],'manual_requirements_reported':ok,'performance_verified':False},'reported' if ok else 'needs_retry')
    def next_pass(self,t):self.check(t,('reported',));require(self.phase==0,'no third pass');self.phase=1;self.cycle=0;self.record('next_pass',{},'ready')
    def heard_prompt(self,t,ack):self.check(t,('hearing_prompt',));require(ack is True,'named prompt heard');self.record('heard_prompt',{},'singing')
    def sung(self,t,ack):self.check(t,('singing',));require(ack is True,'destination singing attempted');self.record('sung',{},'silent_setup')
    def setup_target(self,t,ack):self.check(t,('silent_setup',));require(ack is True,'silent setup attempted');self.record('silent_setup',{},'attack')
    def attempt_attack(self,t,ack):self.check(t,('attack',));require(ack is True,'single attack attempt');self.record('attack_attempt',{'actual_attack_count_observed':None},'await_release')
    def report_fretboard(self,t,r):
        self.check(t,('fret_report',));fields(r,('specified_string','attack_count','duties','diagnosis','notes'));fields(r['duties'],FRET_DUTIES)
        require(r['specified_string']==self.plan['specified_string'] and type(r['attack_count']) is int and r['attack_count']>=0 and all(x in YN for x in r['duties'].values()) and type(r['diagnosis']) is str and text(r['notes']),'full bound manual fretboard report')
        ok=r['attack_count']==1 and all(x=='yes' for x in r['duties'].values())
        if not ok:require(text(r['diagnosis']),'failed/uncertain attempt diagnosis')
        self.record('fretboard_report',{'response':r,'manual_requirements_reported':ok,'performance_verified':False,'automatic_score':False},'reported' if ok else 'needs_retry')
    def retry(self,t,note):self.check(t,('reported','needs_retry'));require(text(note),'retry diagnosis');self.record('retry',{'note':note},'ready')
    def finish(self,t):self.check(t,('reported',));require(self.phase==1,'both passes required');self.record('finish',{'manual_only':True,'source_acceptance':False,'mastery_awarded':False},'completed')
    def cancel(self,t):
        self.check(t,('setup','ready','listening','await_release','answer_quality','answer_pitch','committed','review','reported','needs_retry','hearing_prompt','singing','silent_setup','attack','fret_report','completed','reopen_release'))
        if self.state!='reopen_release':self.resume='ready' if self.state in ('listening','await_release','answer_quality','answer_pitch','committed','hearing_prompt','singing','silent_setup','attack','fret_report') else self.state
        self.generation+=1;self.record('cancel',{},'cancelled')
    def reopen(self,t):self.check(t,('cancelled',));self.generation+=1;self.record('reopen',{},'reopen_release')
def contract(i):
    a,b,d,q=RAW[i]
    if i==19:return {'schema_version':'fathom-private-source-reconciliation-pending.1','key':KEYS[i],'source_fields':{'Card':CARD[i],'Start':a,'Destination':b,'Direction':d,'Answer':q},'printed_signed_semitones':-8,'pitch_pair_descending_semitones':9,'private_workflow_available':False,'source_correction_adopted':False,'source_note_events':[]}
    return {'schema_version':'fathom-private-interval-dictation-manual.1','key':KEYS[i],
      'source_fields':{'Card':CARD[i],'Start':a,'Destination':b,'Direction':d,'Answer':q},'derived_signed_semitones':delta(i),
      'source_heading':'ANSWER INTERVAL QUALITY BEFORE NAMING THE SECOND PITCH','source_footer':FOOTER,'source_no_search':NO_SEARCH,
      'source_context_header':'24 CELLS | 96 TONES','source_note_events':[],'source_octave_fret_timing':None,
      'official_extent':'22existingchildren:printed1–21and24;22/23outside-childambiguitiesunchanged;card24officialrow25retained',
      'plan_schema':{'external_source':['external_human','external_recording'],'realization':'chosen start/destinationMIDI at exact signed source interval; specified string fret0..24'},
      'response_schema':{'dictation':'intervalquality then secondpitch, explicit reveal and manual hearing/diagnosis','fretboard_duties':list(FRET_DUTIES),'enum':list(YN)},
      'authored_policies':['Separate pairdictation and named-start/interval fretboard passes; external provider supplies actual sound/prompts.',
        'Source/player view retains complete script; learner view withholds destination/answer until committed dictation reveal; prior reveal remains sticky across retries/newplans.',
        'Fretboard initial prompt gives start/interval/direction/string, no destination/fret; previousrevealflag prevents false unseen claim.',
        'Recognized enharmonic pitch-class answer accepted symbolically; original spelling retained and spelling match recorded separately.',
        'No first root play, no slidesearch, one silentsetup/attack; failed counts/outcomes require diagnosis and retry.',
        'Current pass/action tokens and release fences; cancel/reopen repeats interrupted pass with history, newplan resets dictation while preserving ever_revealed.',
        'Views are a manual presentation contract, not a security boundary against inspecting source files.'],
      'automatic_evaluation':False,'performance_observed':False,'audio_supplied':False,'audio_inspected':False,'timing_scheduled':False,
      'credit_awarded':False,'mastery_awarded':False,'persistence':False,'canonical_binding':None}
