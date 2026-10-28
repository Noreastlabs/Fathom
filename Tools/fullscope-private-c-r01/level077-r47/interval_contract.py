"""Twelve source interval-atlas routes; manual hearing/singing, no audio engine."""
from copy import deepcopy
from uuid import uuid4
LABELS=('m2','M2','m3','M3','P4','TT','P5','m6','M6','m7','M7','P8')
UPPER=('Db','D','Eb','E','F','F#','G','Ab','A','Bb','B','C')
KEYS=tuple(f'exercise-completeness-r01/level077/modulea/p002-t1-r{i}/{label.lower()}' for i,label in enumerate(LABELS,1))
TUNING={'E':40,'A':45,'D':50,'G':55,'B':59,'e':64}
PRACTICE='Practice: hear root -> sing interval -> play it. Then hear the upper note -> sing downward to the root. Use C only as the first reference; later modules randomize the root.'
NO_SEARCH='After the target is sung, use one silent setup and one attack. Diagnose a wrong attack; do not slide around until the note is found.'
COMMON=('heard_correct_reference','sung_correct_pitch','source_order_followed','direction_followed')
UP_DUTIES=('single_silent_setup','no_searching','played_target_correctly');YN=('yes','no','uncertain')
class Refusal(ValueError):pass
def require(ok,msg):
    if not ok:raise Refusal(msg)
def fields(o,keys):require(type(o) is dict and set(o)==set(keys),'field set')
def text(x):return type(x) is str and bool(x.strip())
def validate_plan(p,i):
    fields(p,('prerequisites','provider','root_midi','upper_midi','target_contact'))
    fields(p['prerequisites'],('own_instrument','original_workbook'));require(all(x is True for x in p['prerequisites'].values()),'manual prerequisites')
    provider=p['provider'];fields(provider,('kind','reference','ready'));require(provider['kind'] in ('external_human','external_recording') and text(provider['reference']) and provider['ready'] is True,'external pitch provider')
    root=p['root_midi'];upper=p['upper_midi'];require(type(root) is int and type(upper) is int and 0<=root<=127 and 0<=upper<=127 and root%12==0 and upper-root==i+1,'chosen C root and exact semitone distance')
    c=p['target_contact'];fields(c,('string','fret'));require(type(c['string']) is str and c['string'] in TUNING and type(c['fret']) is int and 0<=c['fret']<=24 and TUNING[c['string']]+c['fret']==upper,'chosen contact realizes upper pitch')
class IntervalFlow:
    def __init__(self,key):
        require(key in KEYS,'exact twelve atlas keys');self.key=key;self.index=KEYS.index(key);self.instance=uuid4().hex
        self.generation=self.phase=self.cycle=self.action=0;self.state='setup';self.plan=None;self.history=[];self.resume=None
    def token(self):return (self.instance,self.key,self.generation,self.phase,self.cycle,self.action,self.state)
    def check(self,t,states):require(type(t) is tuple and t==self.token(),'stale/foreign token');require(self.state in states,'wrong state')
    def record(self,kind,data,state):
        self.history.append({'kind':kind,'generation':self.generation,'direction':self.direction(),'cycle':self.cycle,'data':deepcopy(data)});self.action+=1;self.state=state
    def direction(self):return 'upward' if self.phase==0 else 'downward'
    def set_plan(self,t,p):
        self.check(t,('setup','ready','needs_retry','reported','completed'));validate_plan(p,self.index)
        self.plan=deepcopy(p);self.generation+=1;self.phase=self.cycle=0;self.record('plan',p,'ready')
    def provider_view(self):
        require(self.plan is not None,'plan required');return {'direction':self.direction(),'supply_midi':self.plan['root_midi'] if self.phase==0 else self.plan['upper_midi'],
          'learner_sings_midi':self.plan['upper_midi'] if self.phase==0 else self.plan['root_midi'],'actual_audio_supplied':False,'reference_public_for_atlas':True}
    def begin(self,t,source_ready):
        self.check(t,('ready',));require(source_ready is True,'current provider readiness');self.cycle+=1;self.record('begin',self.provider_view(),'hearing')
    def heard(self,t,ack):self.check(t,('hearing',));require(ack is True,'reference heard declaration');self.record('heard',{},'singing')
    def sung(self,t,attempted):
        self.check(t,('singing',));require(attempted is True,'singing attempted');self.record('sung',{'acoustic_pitch_verified':False},'silent_setup' if self.phase==0 else 'await_release')
    def setup_target(self,t,ack):self.check(t,('silent_setup',));require(ack is True,'silent setup declaration');self.record('silent_setup',{},'attack')
    def attempt_attack(self,t,ack):self.check(t,('attack',));require(ack is True,'one target attack attempt');self.record('attack_attempt',{'observed_attack_count':None},'await_release')
    def release(self,t,ack):
        self.check(t,('await_release','reopen_release'));require(ack is True,'physical release')
        if self.state=='await_release':self.record('release',{},'reporting')
        else:
            state=self.resume;require(state is not None,'resume');self.resume=None;self.record('reopen_release',{},state)
    def report(self,t,r):
        self.check(t,('reporting',));required=('source_interval','direction','learner_label','common','diagnosis','notes')+(('attack_count','upward_duties') if self.phase==0 else ())
        fields(r,required);require(r['source_interval']==LABELS[self.index] and r['direction']==self.direction() and text(r['learner_label']) and type(r['diagnosis']) is str and text(r['notes']),'source response binding')
        fields(r['common'],COMMON);require(all(x in YN for x in r['common'].values()),'manual source duties')
        symbolic=r['learner_label']==LABELS[self.index];ok=symbolic and all(x=='yes' for x in r['common'].values())
        if self.phase==0:
            fields(r['upward_duties'],UP_DUTIES);require(all(x in YN for x in r['upward_duties'].values()) and type(r['attack_count']) is int and r['attack_count']>=0,'actual manual attack count/duties')
            ok=ok and r['attack_count']==1 and all(x=='yes' for x in r['upward_duties'].values())
        if not ok:require(text(r['diagnosis']),'wrong/uncertain attempt must be diagnosed')
        self.record('report',{'response':r,'symbolic_label_matches':symbolic,'manual_requirements_reported':ok,
          'performance_verified':False,'audio_inspected':False,'automatic_score':False},'reported' if ok else 'needs_retry')
    def next_direction(self,t):self.check(t,('reported',));require(self.phase==0,'no third direction');self.phase=1;self.cycle=0;self.record('next_direction',{},'ready')
    def retry(self,t,note):self.check(t,('reported','needs_retry'));require(text(note),'retry diagnosis');self.record('retry',{'note':note},'ready')
    def finish(self,t):self.check(t,('reported',));require(self.phase==1,'both directions required');self.record('finish',{'manual_only':True,'source_acceptance':False,'mastery_awarded':False},'completed')
    def cancel(self,t):
        self.check(t,('setup','ready','hearing','singing','silent_setup','attack','await_release','reporting','reported','needs_retry','completed','reopen_release'))
        if self.state!='reopen_release':self.resume='ready' if self.state in ('hearing','singing','silent_setup','attack','await_release','reporting') else self.state
        self.generation+=1;self.record('cancel',{},'cancelled')
    def reopen(self,t):self.check(t,('cancelled',));self.generation+=1;self.record('reopen',{},'reopen_release')
def contract(i):
    return {'schema_version':'fathom-private-interval-atlas-manual.1','key':KEYS[i],
      'source_fields':{'Interval':LABELS[i],'Semitones':i+1,'Reference':'C-'+UPPER[i],'Sing upward':'','Sing downward':''},
      'source_practice':PRACTICE,'source_no_search_rule':NO_SEARCH,
      'source_heading':'LEARN THE SOUND IN BOTH DIRECTIONS; SONG MNEMONICS ARE OPTIONAL, NOT THE FINAL SKILL',
      'source_reference':[{'pitch_class':'C','octave':None,'fret':None,'onset':None},{'pitch_class':UPPER[i],'octave':None,'fret':None,'onset':None}],
      'source_note_events':[],'source_reference_direction_extent':'upward reference pair and reverse singing; P8 retains12semitones',
      'plan_schema':{'provider':['external_human','external_recording'],'root':'chosen MIDI C','upper':'chosen root+source semitones','target_contact':'standard tuning chosen string/fret0..24'},
      'response_schema':{'source_interval':LABELS[i],'directions':['upward','downward'],'common':list(COMMON),'upward_only':list(UP_DUTIES),
        'actual_attack_count':'nonnegative manual count; exactly1required for upward reported success','diagnosis':'required for all unmet/uncertain criteria','enum':list(YN)},
      'authored_policies':['External source supplies chosenroot/upper; reference visible atlas practice, not claimed blind/randomized test.',
        'Hear→sing→silent setup→one attack→release/review upward; hearupper→singroot→release/review downward. No mandatory downward guitar attack.',
        'Typed label comparison is symbolic, not acoustic validation; all actual performance outcomes are self-report.',
        'Multiple/zero attacks or searching remain recorded failures requiring diagnosis/retry; no slide-to-answer success.',
        'Current action/direction ownership, release fences, cancel/reopen repeats interrupted route; new plan resets upward with history.'],
      'automatic_evaluation':False,'performance_observed':False,'audio_supplied':False,'audio_inspected':False,'timing_scheduled':False,
      'credit_awarded':False,'mastery_awarded':False,'persistence':False,'canonical_binding':None}
