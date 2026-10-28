"""Private manual response model; no audio, tempo control, file inspection or storage."""
from copy import deepcopy
from math import isfinite
from uuid import uuid4

KEY='exercise-completeness-r01/level075/moduleb/p005-u001/modulebdensityregisterandtextureladder'
CHORDS=('Cmaj7','Am7','Dm7','G7')
LEVELS=(('single roots','low','p','whole notes'),('shell dyads','middle-low','mp','half notes'),
        ('triads','middle','mf','quarters'),('partial 7ths','upper','mf','8ths'),
        ('full comping','wide','f','16ths'),('lead + rests','upper','f -> mp','motif / space'))
BLOCKS=('roots only','shell dyads','triads','partial seventh chords','full comping','lead answers with rests')
FOOTER=('Use Cmaj7-Am7-Dm7-G7. The tempo never changes. Only density and register change. Record the pass '
        'and verify that the form becomes larger without becoming louder by accident.')
LADDER_REPORTS=('voicing_matched','register_matched','dynamic_matched','rhythm_matched','one_variable_at_a_time','tempo_held')
RAMP_REPORTS=('recording_made','lead_rests_retained','progression_covered','full_twelve_bars','tempo_held',
              'only_planned_density_register_changes','form_larger','no_accidental_loudness')
ANSWERS=('yes','no','uncertain')
class Refusal(ValueError):pass
def require(ok, why):
    if not ok:raise Refusal(why)
def fields(obj, names):require(type(obj) is dict and set(obj)==set(names),'field set')
def nonempty(x):return type(x) is str and bool(x.strip())
def position(x,n):return type(x) is int and 1<=x<=n
def positive_finite(x):
    if type(x) not in (int,float):return False
    try:return isfinite(x) and x>0
    except OverflowError:return False
def validate_plan(p):
    fields(p,('prerequisites','bpm','ladder_realizations','ramp_blocks','ramp_loudness_plan','bar_allocation'))
    fields(p['prerequisites'],('own_instrument','original_workbook','external_recorder'))
    require(all(x is True for x in p['prerequisites'].values()),'external manual prerequisite')
    require(positive_finite(p['bpm']),'finite positive external BPM')
    require(nonempty(p['ramp_loudness_plan']),'intentional stable ramp loudness')
    require(type(p['ladder_realizations']) is list and len(p['ladder_realizations'])==6,'six source levels')
    for i,level in enumerate(p['ladder_realizations'],1):
        fields(level,('level','chords','isolated_variable_preparation'))
        require(type(level['level']) is int and level['level']==i and nonempty(level['isolated_variable_preparation']),'level/preparation')
        require(type(level['chords']) is list and len(level['chords'])==4,'four chord realizations')
        for c,symbol in zip(level['chords'],CHORDS):
            fields(c,('source_chord','realization'))
            require(c['source_chord']==symbol and nonempty(c['realization']),'source chord/choice')
    require(type(p['ramp_blocks']) is list and len(p['ramp_blocks'])==6,'six two-bar choices')
    for i,b in enumerate(p['ramp_blocks']):
        fields(b,('bars','source_texture','chosen_register','realization'))
        require(b['bars']==[2*i+1,2*i+2] and all(type(x) is int for x in b['bars']),'source bar extent')
        require(b['source_texture']==BLOCKS[i] and nonempty(b['chosen_register']) and nonempty(b['realization']),'ramp source/choices')
    require(type(p['bar_allocation']) is list and len(p['bar_allocation'])==12,'twelve explicit bar choices')
    flat=[]
    for i,b in enumerate(p['bar_allocation'],1):
        fields(b,('bar','progression_positions','within_bar_placement'))
        require(type(b['bar']) is int and b['bar']==i and nonempty(b['within_bar_placement']),'bar/placement')
        ps=b['progression_positions']
        require(type(ps) is list and bool(ps) and all(position(x,4) for x in ps),'progression positions')
        flat.extend(ps)
    require(flat[0]==1 and flat[-1]==4 and set(flat)=={1,2,3,4},'chosen complete progression extent')
    require(all(b==a or b==a%4+1 for a,b in zip(flat,flat[1:])),'source progression order')

class TextureFlow:
    def __init__(self,key=KEY):
        require(key==KEY,'finite exact child only')
        self.key=key;self.instance=uuid4().hex;self.generation=self.stage=self.cycle=self.action=0
        self.state='setup';self.plan=None;self.history=[];self.resume=None
    def token(self):return (self.instance,self.key,self.generation,self.stage,self.cycle,self.action,self.state)
    def check(self,t,states):
        require(type(t) is tuple and t==self.token(),'stale/foreign token')
        require(self.state in states,'wrong state')
    def record(self,kind,data,state):
        self.history.append({'kind':kind,'stage':self.stage,'cycle':self.cycle,'generation':self.generation,'data':deepcopy(data)})
        self.action+=1;self.state=state
    def set_plan(self,t,p):
        self.check(t,('setup','ready','needs_retry','reported','completed'));validate_plan(p)
        self.plan=deepcopy(p);self.generation+=1;self.stage=self.cycle=0;self.record('plan',p,'ready')
    def begin(self,t):
        self.check(t,('ready',));require(self.plan is not None,'plan required')
        self.cycle+=1;self.record('begin',{'chosen_external_bpm':self.plan['bpm'],'host_tempo_changed':False},'performing')
    def release(self,t,ack):
        self.check(t,('performing','reopen_release'));require(ack is True,'manual instrument release')
        if self.state=='performing':self.record('release',{},'reporting')
        else:
            state=self.resume;require(state is not None,'resume state');self.resume=None;self.record('reopen_release',{},state)
    def report(self,t,r):
        self.check(t,('reporting',))
        fields(r,('coverage','obligations','notes','recording'))
        require(nonempty(r['notes']),'response notes')
        count=4 if self.stage<6 else 6
        require(type(r['coverage']) is list and len(r['coverage'])==count,'complete source scope reports')
        for i,c in enumerate(r['coverage'],1):
            fields(c,('position','covered'))
            require(type(c['position']) is int and c['position']==i and c['covered'] in ANSWERS,'ordered coverage')
        names=LADDER_REPORTS if self.stage<6 else RAMP_REPORTS;fields(r['obligations'],names)
        require(all(x in ANSWERS for x in r['obligations'].values()),'typed manual obligation')
        if self.stage==6:
            fields(r['recording'],('kind','value'))
            require(r['recording']['kind'] in ('external_reference','self_report') and nonempty(r['recording']['value']),'external recording reference or honest self-report')
        else:require(r['recording'] is None,'recording is ramp obligation')
        ok=all(c['covered']=='yes' for c in r['coverage']) and all(x=='yes' for x in r['obligations'].values())
        self.record('report',{'response':r,'manual_requirements_reported':ok,'recording_inspected':False,'performance_verified':False},'reported' if ok else 'needs_retry')
    def retry(self,t,note):
        self.check(t,('reported','needs_retry'));require(nonempty(note),'retry note');self.record('retry',{'note':note},'ready')
    def advance(self,t):
        self.check(t,('reported',));self.record('advance',{},'completed' if self.stage==6 else 'ready')
        if self.stage<6:self.stage+=1;self.cycle=0
    def cancel(self,t):
        self.check(t,('setup','ready','performing','reporting','reported','needs_retry','completed','reopen_release'))
        if self.state!='reopen_release':self.resume='ready' if self.state in ('performing','reporting') else self.state
        self.generation+=1;self.record('cancel',{'incomplete_cycle_not_counted':True},'cancelled')
    def reopen(self,t):
        self.check(t,('cancelled',));self.generation+=1;self.record('reopen',{},'reopen_release')

def contract():
    return {'schema_version':'fathom-private-texture-ladder-manual.1','key':KEY,
        'source_ladder':[{'level':i,'voicing':v,'register':r,'dynamic':d,'rhythm':h} for i,(v,r,d,h) in enumerate(LEVELS,1)],
        'source_ramp':[{'bars':[2*i+1,2*i+2],'texture':x} for i,x in enumerate(BLOCKS)],
        'source_progression':list(CHORDS),'source_heading':'CHANGE ONE ARRANGEMENT VARIABLE AT A TIME','full_source_footer':FOOTER,
        'source_contacts_header':'128 CONTACTS','fixed_source_event_count':None,
        'plan_schema':{'prerequisites':['own_instrument','original_workbook','external_recorder'],
            'bpm':'finite positive chosen external setting, held per pass; no host control',
            'ladder_realizations':'six levels × four source-ordered chord descriptions; isolated-variable preparation per level',
            'ramp_blocks':'six exact bar-pair textures, learner register/realization description',
            'ramp_loudness_plan':'intended stable loudness, separate from ladder dynamics',
            'bar_allocation':'12 bars, chosen ordered progression positions and within-bar placement; source bar mapping unprinted'},
        'response_schema':{'ladder':{'coverage':'four chords','obligations':list(LADDER_REPORTS)},
            'ramp':{'coverage':'six two-bar blocks','obligations':list(RAMP_REPORTS),'recording':'external/local reference or explicit self-report'},
            'enum':['yes','no','uncertain'],'notes':'required'},
        'authored_policies':['Seven-stage workflow: six ladder preparations followed by the distinct twelve-bar ramp.',
            'Ladder dynamic/rhythm columns remain ladder targets; not silently imported into ramp.',
            'Chosen bar allocation preserves cyclic four-chord order allowing holds, starts first chord and ends fourth; this is a chosen realization, not printed bar placement.',
            'Release before report; all obligations must be reported yes; negative/uncertain reports require explicit retry.',
            'Current instance/key/generation/stage/cycle/action/state token; plan revisions restart stage0 but retain history.',
            'Cancel/reopen preserves source/plan/history, requires release and repeats interrupted cycles.'],
        'automatic_evaluation':False,'performance_observed':False,'audio_supplied':False,'recording_inspected':False,
        'mastery_awarded':False,'credit_awarded':False,'persistence':False,'canonical_binding':None}
