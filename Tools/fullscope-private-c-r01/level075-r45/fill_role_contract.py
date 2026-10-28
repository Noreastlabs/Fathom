"""One source fill role; chosen spacing remains separate from source note timing."""
from copy import deepcopy
from fractions import Fraction
from math import isfinite
from uuid import uuid4
KEY='exercise-completeness-r01/level075/moduleb/p004-card04/fillafterspacerole'
CONTACTS=(('G',4),('G',5),('G',7),('B',5),('B',6),('B',8),('e',5),('e',7),('e',8),('e',7),('e',5))
TABLE=(('Foundation','Roots + shell','Verse','Leave upper register open'),('Comping','Triads / 7th shells','Chorus','Support groove, avoid lead register'),
 ('Counterline','2-4 note answer','Pre / Bridge','Answer vocal-space only'),('Lead','Motif + targets','Solo','Rhythm guitar reduces density'),
 ('Silence','Rest / cue watch','Transitions','Prepare next entrance'))
COMMON=('started_after_beat_three','space_before_fill','source_order_followed','chosen_spacing_followed','chosen_ending_followed',
 'pulse_and_tempo_held','chosen_density_register_followed','chosen_role_context_followed')
DESCRIPTIONS=('prior_available_space','section_role_context','density_register_plan','spacing_rationale');YN=('yes','no','uncertain')
class Refusal(ValueError):pass
def require(ok,msg):
    if not ok:raise Refusal(msg)
def fields(o,names):require(type(o) is dict and set(o)==set(names),'field set')
def text(x):return type(x) is str and bool(x.strip())
def tempo(x):
    if type(x) not in (int,float):return False
    try:return isfinite(x) and x>0
    except OverflowError:return False
def rational(x):
    require(type(x) is list and len(x)==2 and all(type(v) is int for v in x) and x[1]>0,'integer rational beat');return Fraction(x[0],x[1])
def validate_plan(p):
    fields(p,('prerequisites','bpm','chosen_note_beats','chosen_ending_beat','descriptions'))
    fields(p['prerequisites'],('own_instrument','original_workbook'));require(all(x is True for x in p['prerequisites'].values()),'manual prerequisites')
    require(tempo(p['bpm']),'chosen external tempo');fields(p['descriptions'],DESCRIPTIONS);require(all(text(x) for x in p['descriptions'].values()),'complete context/choice descriptions')
    require(type(p['chosen_note_beats']) is list and len(p['chosen_note_beats'])==11,'eleven exact source contacts')
    beats=[rational(x) for x in p['chosen_note_beats']];end=rational(p['chosen_ending_beat'])
    require(3<beats[0] and all(a<b for a,b in zip(beats,beats[1:])) and beats[-1]<end<=5,'source after3, chosen ordered one-bar ending')
class FillRoleFlow:
    def __init__(self,key):
        require(key==KEY,'one exact source role');self.key=key;self.instance=uuid4().hex;self.generation=self.cycle=self.action=0
        self.state='setup';self.plan=None;self.history=[];self.resume=None
    def token(self):return (self.instance,self.key,self.generation,self.cycle,self.action,self.state)
    def check(self,t,states):require(type(t) is tuple and t==self.token(),'stale/foreign token');require(self.state in states,'wrong state')
    def record(self,kind,data,state):
        self.history.append({'kind':kind,'generation':self.generation,'cycle':self.cycle,'data':deepcopy(data)});self.action+=1;self.state=state
    def set_plan(self,t,p):
        self.check(t,('setup','ready','needs_retry','reported','completed'));validate_plan(p);self.plan=deepcopy(p)
        self.generation+=1;self.cycle=0;self.record('plan',p,'ready')
    def begin(self,t):
        self.check(t,('ready',));self.cycle+=1;self.record('begin',{'source_contacts':[list(x) for x in CONTACTS],
         'timing_choice_is_source':False,'source_target_added':False,'audio_supplied':False,'clock_used':False},'performing')
    def end_take(self,t,ended):self.check(t,('performing',));require(ended is True,'complete take end');self.record('take_end',{},'await_release')
    def release(self,t,ack):
        self.check(t,('await_release','reopen_release'));require(ack is True,'physical release')
        if self.state=='await_release':self.record('release',{},'reporting')
        else:
            state=self.resume;require(state is not None,'resume');self.resume=None;self.record('reopen_release',{},state)
    def report(self,t,r):
        self.check(t,('reporting',));fields(r,('source_contacts','common','notes'));fields(r['common'],COMMON)
        require(all(v in YN for v in r['common'].values()) and text(r['notes']),'full manual duties')
        require(type(r['source_contacts']) is list and len(r['source_contacts'])==11,'all eleven contact reports');ok=all(v=='yes' for v in r['common'].values())
        for i,(c,(string,fret)) in enumerate(zip(r['source_contacts'],CONTACTS),1):
            fields(c,('source_order','string','fret','played'));require(type(c['source_order']) is int and c['source_order']==i and c['string']==string and type(c['fret']) is int and c['fret']==fret and c['played'] in YN,'source order/string/fret binding');ok=ok and c['played']=='yes'
        self.record('report',{'response':r,'manual_requirements_reported':ok,'performance_verified':False,'automatic_score':False},'reported' if ok else 'needs_retry')
    def retry(self,t,note):self.check(t,('reported','needs_retry'));require(text(note),'retry note');self.record('retry',{'note':note},'ready')
    def finish(self,t):self.check(t,('reported',));self.record('finish',{'manual_only':True,'source_acceptance':False},'completed')
    def cancel(self,t):
        self.check(t,('setup','ready','performing','await_release','reporting','reported','needs_retry','completed','reopen_release'))
        if self.state!='reopen_release':self.resume='ready' if self.state in ('performing','await_release','reporting') else self.state
        self.generation+=1;self.record('cancel',{},'cancelled')
    def reopen(self,t):self.check(t,('cancelled',));self.generation+=1;self.record('reopen',{},'reopen_release')
def contract():
    return {'schema_version':'fathom-private-fill-role-manual.1','key':KEY,'source_instruction':'fill begins after beat 3',
      'source_role_context':[list(x) for x in TABLE],'source_role_mapping':None,'source_context_header':'8 ROLE CELLS | 128 CONTACTS',
      'source_contacts':[{'source_order':i,'string':s,'fret':f} for i,(s,f) in enumerate(CONTACTS,1)],
      'source_target':None,'source_fixed_timing':False,'source_extent_question':'Four enumerated cards versus8ROLECELLS/128CONTACTS remains Pending; no invented contacts/children.',
      'plan_schema':{'prerequisites':['own_instrument','original_workbook'],'bpm':'positive external choice',
        'chosen_note_beats':'eleven increasing integer rationals, first>3; chosen ending>last and<=5',
        'descriptions':list(DESCRIPTIONS),'source_contacts_editable':False},
      'response_schema':{'source_contacts':'eleven exact order/string/fret plus manual played','common':list(COMMON),'enum':list(YN),'notes':'required'},
      'authored_policies':['One-bar finish bound is authored finite realization; source specifies afterbeat3 only, not exact spacing/end.',
        'Spacing/ending choices are not source onsets or acoustic gates; no scheduler or audio.',
        'Do not borrow another module\'s resolution target or truncate eleven notes to context counterline2–4notes.',
        'Title space retained as manual obligation, not a measured source silence duration or dash-derived rest.',
        'Current action ownership; end/release before report, negative/uncertain retry, cancel/reopen repeats interrupted take; plan changes reset completion with history.'],
      'automatic_evaluation':False,'performance_observed':False,'audio_supplied':False,'timing_scheduled':False,
      'credit_awarded':False,'mastery_awarded':False,'persistence':False,'canonical_binding':None}
