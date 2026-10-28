"""Manual fill plan and source-obligation reports. Chosen timing is not source timing."""
from copy import deepcopy
from fractions import Fraction
from math import isfinite
from uuid import uuid4
SUFFIXES=('p008-card01/fill1chordtoneconnectortarget','p008-supplement01/fill2chordtoneconnectortarget',
          'p008-card02/fill3chordtoneconnectortarget','p008-card03/fill4chordtoneconnectortarget')
KEYS=tuple('exercise-completeness-r01/level075/moduled/'+s for s in SUFFIXES)
TARGETS=('C','A','D','G');PCS=(0,9,2,7)
TUNING={'e':64,'B':59,'G':55,'D':50,'A':45,'E':40}
TABLE=(('Beat 1','4-beat fill','high risk'),('Beat 2','3-beat fill','medium'),
       ('Beat 3','2-beat fill','recommended'),('Beat 4','1-beat fill','safe'),
       ('& of 3','3 eighths','safe'),('& of 4','pickup only','very safe'))
OBLIGATIONS=('started_after_beat_three','fill_ended_before_next_structural_attack',
             'source_target_on_next_bar_one','pulse_held','chosen_spacing_followed','no_overrun')
YN=('yes','no','uncertain')
class Refusal(ValueError):pass
def require(ok,msg):
    if not ok:raise Refusal(msg)
def fields(o,names):require(type(o) is dict and set(o)==set(names),'field set')
def text(x):return type(x) is str and bool(x.strip())
def finite_bpm(x):
    if type(x) not in (int,float):return False
    try:return isfinite(x) and x>0
    except OverflowError:return False
def rational(x):
    require(type(x) is list and len(x)==2 and all(type(v) is int for v in x) and x[1]>0,'integer rational beat')
    return Fraction(x[0],x[1])
def validate_plan(p,index):
    fields(p,('prerequisites','bpm','chosen_note_beats','spacing_rationale','target_choice'))
    fields(p['prerequisites'],('own_instrument','original_workbook'))
    require(all(x is True for x in p['prerequisites'].values()),'manual prerequisite')
    require(finite_bpm(p['bpm']) and text(p['spacing_rationale']),'external tempo/spacing choice')
    require(type(p['chosen_note_beats']) is list and len(p['chosen_note_beats'])==11,'eleven chosen note onsets')
    beats=[rational(x) for x in p['chosen_note_beats']]
    require(beats[0]>3 and beats[-1]<5 and all(a<b for a,b in zip(beats,beats[1:])),'after beat3, ordered before next barline')
    t=p['target_choice'];fields(t,('source_pitch_class','string','fret','register_rationale'))
    require(t['source_pitch_class']==TARGETS[index] and type(t['string']) is str and t['string'] in TUNING,'source target/string')
    require(type(t['fret']) is int and 0<=t['fret']<=24 and text(t['register_rationale']),'chosen target fret/register')
    require((TUNING[t['string']]+t['fret'])%12==PCS[index],'chosen target must realize printed pitch class')
class FillFlow:
    def __init__(self,key):
        require(key in KEYS,'exact finite source fill');self.key=key;self.index=KEYS.index(key);self.instance=uuid4().hex
        self.generation=self.cycle=self.action=0;self.state='setup';self.plan=None;self.history=[];self.resume=None
    def token(self):return (self.instance,self.key,self.generation,self.cycle,self.action,self.state)
    def check(self,t,states):
        require(type(t) is tuple and t==self.token(),'stale/foreign token');require(self.state in states,'wrong state')
    def record(self,kind,data,state):
        self.history.append({'kind':kind,'generation':self.generation,'cycle':self.cycle,'data':deepcopy(data)})
        self.action+=1;self.state=state
    def set_plan(self,t,p):
        self.check(t,('setup','ready','needs_retry','reported','completed'));validate_plan(p,self.index)
        self.plan=deepcopy(p);self.generation+=1;self.cycle=0;self.record('plan',p,'ready')
    def begin(self,t):
        self.check(t,('ready',));self.cycle+=1
        choice=self.plan['target_choice']
        self.record('begin',{'chosen_target_midi':TUNING[choice['string']]+choice['fret'],
            'chosen_note_beats_are_source_facts':False,'audio_scheduled':False},'performing')
    def release(self,t,ack):
        self.check(t,('performing','reopen_release'));require(ack is True,'manual instrument release')
        if self.state=='performing':self.record('release',{},'reporting')
        else:
            state=self.resume;require(state is not None,'resume state');self.resume=None;self.record('reopen_release',{},state)
    def report(self,t,r):
        self.check(t,('reporting',));fields(r,('source_contacts','target_report','obligations','notes'))
        require(type(r['source_contacts']) is list and len(r['source_contacts'])==11 and text(r['notes']),'full source report')
        for i,c in enumerate(r['source_contacts'],1):
            fields(c,('source_order','played'));require(type(c['source_order']) is int and c['source_order']==i and c['played'] in YN,'ordered source contacts')
        fields(r['target_report'],('source_pitch_class','matched'))
        require(r['target_report']['source_pitch_class']==TARGETS[self.index] and r['target_report']['matched'] in YN,'source target report')
        fields(r['obligations'],OBLIGATIONS);require(all(x in YN for x in r['obligations'].values()),'typed temporal duties')
        ok=all(x['played']=='yes' for x in r['source_contacts']) and r['target_report']['matched']=='yes' and all(x=='yes' for x in r['obligations'].values())
        self.record('report',{'response':r,'manual_requirements_reported':ok,'performance_verified':False},'reported' if ok else 'needs_retry')
    def retry(self,t,note):
        self.check(t,('reported','needs_retry'));require(text(note),'retry note');self.record('retry',{'note':note},'ready')
    def finish(self,t):self.check(t,('reported',));self.record('finish',{'manual_only':True},'completed')
    def cancel(self,t):
        self.check(t,('setup','ready','performing','reporting','reported','needs_retry','completed','reopen_release'))
        if self.state!='reopen_release':self.resume='ready' if self.state in ('performing','reporting') else self.state
        self.generation+=1;self.record('cancel',{},'cancelled')
    def reopen(self,t):self.check(t,('cancelled',));self.generation+=1;self.record('reopen',{},'reopen_release')
def contract(index):
    return {'schema_version':'fathom-private-fill-resolution-manual.1','key':KEYS[index],
        'source_instruction':'fill begins after beat 3','source_resolution_instruction':f'Resolve to {TARGETS[index]} on next bar 1.',
        'source_resolution_target':{'pitch_class':TARGETS[index],'next_bar_beat':1,'octave':None,'string':None,'fret':None},
        'source_heading':'A FILL MUST END BEFORE THE NEXT STRUCTURAL ATTACK',
        'source_start_table':[{'start':a,'available_space':b,'risk':c,'rule':'land on next section beat 1'} for a,b,c in TABLE],
        'source_context_header':'16 FILL CELLS | 128 CONTACTS','fixed_source_contact_total':None,
        'plan_schema':{'prerequisites':['own_instrument','original_workbook'],'bpm':'finite positive external choice',
            'chosen_note_beats':'11 increasing integer rationals, first>3 and last<5; numbered beats1..4/nextbarline5',
            'spacing_rationale':'required learner choice, never source timing',
            'target_choice':'source pitch class plus chosen string/fret/register rationale; standard-tuning pitch-class check'},
        'response_schema':{'source_contacts':11,'target':'printed pitch class, matched yes/no/uncertain',
            'obligations':list(OBLIGATIONS),'notes':'required','enum':list(YN)},
        'authored_policies':['Numbered-beat coordinate1..4/nextbarline5 represents this chosen manual realization, not a printed exact source grid.',
            'Source note gates remain unknown; chosen last attack before5 does not assert a silent gap or acoustic gate.',
            'Target octave/string/fret is chosen; the source target remains pitch class only.',
            'Manual release before report; negative/uncertain report requires explicit retry.',
            'Current instance/key/generation/cycle/action/state; cancel/reopen preserves history, requires release and repeats interrupted pass.',
            'Idle plan changes reset completion but preserve previous choices/replies.'],
        'automatic_evaluation':False,'performance_observed':False,'audio_supplied':False,'timing_scheduled':False,
        'mastery_awarded':False,'credit_awarded':False,'persistence':False,'canonical_binding':None}
