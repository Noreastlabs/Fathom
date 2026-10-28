"""Four-bar dynamic targets with manual reports; no measured dynamics or audio."""
from copy import deepcopy
from math import isfinite
from uuid import uuid4
ROWS=(('flat','Flat',('mp','mp','mp','mp'),'diagnostic only'),
      ('rampup','Ramp up',('p','mp','mf','f'),'pre-chorus'),
      ('rampdown','Ramp down',('f','mf','mp','p'),'outro'),
      ('arch','Arch',('p','mf','f','mp'),'solo phrase'),
      ('terrace','Terrace',('p','p','f','f'),'section contrast'),
      ('echo','Echo',('f','p','f','p'),'call/response'))
KEYS=tuple(f'exercise-completeness-r01/level075/modulee/p010-t1-r{i}/{r[0]}' for i,r in enumerate(ROWS,1))
OBLIGATIONS=('tempo_held','material_and_rhythm_unchanged','full_four_bars')
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
def count(x):return type(x) is int and x>=0
def validate_plan(p):
    fields(p,('prerequisites','bpm','comparison_material','bars'))
    fields(p['prerequisites'],('own_instrument','original_workbook'))
    require(all(v is True for v in p['prerequisites'].values()),'manual prerequisite')
    require(finite_bpm(p['bpm']) and text(p['comparison_material']),'tempo/material choice')
    require(type(p['bars']) is list and len(p['bars'])==4,'four planned bars')
    for i,b in enumerate(p['bars'],1):
        fields(b,('bar','material','rhythm','planned_note_count'))
        require(type(b['bar']) is int and b['bar']==i and text(b['material']) and text(b['rhythm']),'bar material/rhythm')
        require(count(b['planned_note_count']),'nonnegative chosen count')
    require(sum(b['planned_note_count'] for b in p['bars'])>0,'at least one note in chosen phrase')
class ContourFlow:
    def __init__(self,key):
        require(key in KEYS,'finite source contour only');self.key=key;self.index=KEYS.index(key)
        self.instance=uuid4().hex;self.generation=self.cycle=self.action=0
        self.state='setup';self.plan=None;self.history=[];self.resume=None
    def token(self):return (self.instance,self.key,self.generation,self.cycle,self.action,self.state)
    def check(self,t,states):
        require(type(t) is tuple and t==self.token(),'stale/foreign token');require(self.state in states,'wrong state')
    def record(self,kind,data,state):
        self.history.append({'kind':kind,'generation':self.generation,'cycle':self.cycle,'data':deepcopy(data)})
        self.action+=1;self.state=state
    def set_plan(self,t,p):
        self.check(t,('setup','ready','needs_retry','reported','completed'));validate_plan(p)
        self.plan=deepcopy(p);self.generation+=1;self.cycle=0;self.record('plan',p,'ready')
    def begin(self,t):
        self.check(t,('ready',));self.cycle+=1
        self.record('begin',{'source_dynamics':list(ROWS[self.index][2]),'chosen_external_bpm':self.plan['bpm'],'host_tempo_changed':False},'performing')
    def release(self,t,ack):
        self.check(t,('performing','reopen_release'));require(ack is True,'manual instrument release')
        if self.state=='performing':self.record('release',{},'reporting')
        else:
            state=self.resume;require(state is not None,'resume state');self.resume=None;self.record('reopen_release',{},state)
    def report(self,t,r):
        self.check(t,('reporting',));fields(r,('bars','obligations','notes'))
        require(type(r['bars']) is list and len(r['bars'])==4 and text(r['notes']),'full source response')
        fields(r['obligations'],OBLIGATIONS);require(all(x in YN for x in r['obligations'].values()),'typed source obligation')
        ok=all(x=='yes' for x in r['obligations'].values());comparisons=[]
        for i,(b,target,chosen) in enumerate(zip(r['bars'],ROWS[self.index][2],self.plan['bars']),1):
            fields(b,('bar','source_dynamic','dynamic_match','reported_note_count'))
            require(type(b['bar']) is int and b['bar']==i and b['source_dynamic']==target,'exact source bar/target')
            require(b['dynamic_match'] in YN and count(b['reported_note_count']),'manual dynamic/count report')
            same=b['reported_note_count']==chosen['planned_note_count'];comparisons.append(same)
            ok=ok and same and b['dynamic_match']=='yes'
        self.record('report',{'response':r,'reported_count_matches_plan':comparisons,'manual_requirements_reported':ok,
            'performance_verified':False,'dynamics_measured':False},'reported' if ok else 'needs_retry')
    def retry(self,t,note):
        self.check(t,('reported','needs_retry'));require(text(note),'retry note');self.record('retry',{'note':note},'ready')
    def finish(self,t):self.check(t,('reported',));self.record('finish',{'manual_only':True},'completed')
    def cancel(self,t):
        self.check(t,('setup','ready','performing','reporting','reported','needs_retry','completed','reopen_release'))
        if self.state!='reopen_release':self.resume='ready' if self.state in ('performing','reporting') else self.state
        self.generation+=1;self.record('cancel',{},'cancelled')
    def reopen(self,t):self.check(t,('cancelled',));self.generation+=1;self.record('reopen',{},'reopen_release')
def contract(index):
    row=ROWS[index]
    return {'schema_version':'fathom-private-dynamic-contour-manual.1','key':KEYS[index],'source_label':row[1],
        'source_bar_targets':[{'bar':i,'dynamic':v,'pitch':None,'onset_q':None,'velocity':None,'decibels':None} for i,v in enumerate(row[2],1)],
        'source_best_use':row[3],'source_constraint':'tempo and note count fixed',
        'source_heading':'DYNAMICS ARE A FORM PARAMETER, NOT AN AFTERTHOUGHT',
        'source_context_header':'20 CELLS | 160 CONTACTS','fixed_source_contact_count':None,
        'plan_schema':{'prerequisites':['own_instrument','original_workbook'],'bpm':'finite positive chosen external tempo',
            'comparison_material':'learner material name/description, not canonical ID',
            'bars':'four ordered material/rhythm descriptions and nonnegative planned note counts; nonzero total'},
        'response_schema':{'bars':'four exact source-target bindings, dynamic-match yes/no/uncertain and manually reported note count',
            'obligations':list(OBLIGATIONS),'notes':'required','enum':list(YN)},
        'authored_policies':['Compare each reported bar count to its chosen plan; unequal counts between bars are allowed.',
            'A rest bar keeps the intended source dynamic target; a self-report never proves audible dynamics.',
            'Material/rhythm/tempo are held during the pass; idle changes reset completion and retain history.',
            'Plans may be reused across contours; no app-wide comparison-session lock is claimed.',
            'Release before reporting. Negative/uncertain replies and changed reported counts require explicit retry.',
            'Current instance/key/generation/cycle/action/state tokens; cancel/reopen release and repeat interrupted pass.'],
        'diagnostic_only':index==0,'automatic_evaluation':False,'performance_observed':False,'dynamics_measured':False,
        'audio_supplied':False,'mastery_awarded':False,'credit_awarded':False,'persistence':False,'canonical_binding':None}
