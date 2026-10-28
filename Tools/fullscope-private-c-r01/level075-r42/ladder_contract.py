"""Eight source passes with structural-error gate and manual incident handling."""
from copy import deepcopy
from math import isfinite
from uuid import uuid4
from master_source import PROFILES,MASTER_BARS
KEY='exercise-completeness-r01/level075/moduleg/p014-u001/modulegcompleteperformancerehearsalladder'
PASSES=(('Speak chart + tap pulse','form'),('Roots only','harmony'),('Shells / triads','voice leading'),
 ('Written rhythm textures','groove'),('Cues + fills','transitions'),('Dynamics + register','arrangement'),
 ('Lead / rhythm role changes','orchestration'),('One uninterrupted take','performance'))
MATERIAL_DUTIES=(('chart_spoken','pulse_tapped'),('roots_only_followed',),('shells_or_triads_followed',),
 ('written_rhythm_textures_followed',),('cues_and_fills_followed',),('dynamics_and_register_followed',),
 ('lead_rhythm_role_changes_followed',),('one_uninterrupted_take',))
COMMON=('pulse_and_tempo_held','complete_form_traversed','finish_without_discretionary_restart')
ERRORS={'structural':(('lost form','missed cue','stopped performance'),'Repair immediately.'),
 'functional':(('wrong chord quality','wrong section texture','missed target'),'Simplify until function returns.'),
 'cosmetic':(('weak articulation','imperfect note'),'Continue and review after the take.')}
HIERARCHY=('1. Structural error: lost form, missed cue, stopped performance. Repair immediately. '
 '2. Functional error: wrong chord quality, wrong section texture, missed target. Simplify until function returns. '
 '3. Cosmetic error: weak articulation or imperfect note. Continue and review after the take.')
FOOTER=('The rehearsal ladder is intentionally biased toward finishing. A complete imperfect take produces more useful diagnostic information than repeatedly restarting the first sixteen bars.')
CHOICES=('root_realization','shell_or_triad','written_texture','cue_or_fill','dynamic_register','role_change')
YN=('yes','no','uncertain')
class Refusal(ValueError):pass
def require(ok,msg):
    if not ok:raise Refusal(msg)
def fields(o,names):require(type(o) is dict and set(o)==set(names),'field set')
def text(x):return type(x) is str and bool(x.strip())
def bpm(x):
    if type(x) not in (int,float):return False
    try:return isfinite(x) and x>0
    except OverflowError:return False
def validate_plan(p):
    fields(p,('prerequisites','bpm','cue_provision','bars'))
    fields(p['prerequisites'],('own_instrument','original_workbook'));require(all(x is True for x in p['prerequisites'].values()),'manual prerequisite')
    require(bpm(p['bpm']),'chosen external tempo');fields(p['cue_provision'],('mode','description'))
    require(p['cue_provision']['mode'] in ('written_chart','partner','external_media') and text(p['cue_provision']['description']),'actual cue provision description')
    require(type(p['bars']) is list and len(p['bars'])==60,'complete source form choice')
    for pbar,source in zip(p['bars'],MASTER_BARS):
        fields(pbar,('bar','source_chord',*CHOICES))
        require(type(pbar['bar']) is int and pbar['bar']==source['bar'] and pbar['source_chord']==source['source_chord'],'source bar/chord binding')
        require(all(text(pbar[k]) for k in CHOICES),'complete realization choices')
class LadderFlow:
    def __init__(self,key=KEY):
        require(key==KEY,'one existing source ladder');self.key=key;self.instance=uuid4().hex
        self.generation=self.phase=self.cycle=self.action=0;self.state='setup';self.plan=None;self.history=[];self.resume=None
    def token(self):return (self.instance,self.key,self.generation,self.phase,self.cycle,self.action,self.state)
    def check(self,t,states):require(type(t) is tuple and t==self.token(),'stale/foreign token');require(self.state in states,'wrong state')
    def record(self,kind,data,state):
        self.history.append({'kind':kind,'generation':self.generation,'phase':self.phase,'cycle':self.cycle,'data':deepcopy(data)});self.action+=1;self.state=state
    def set_plan(self,t,p):
        self.check(t,('setup','ready','needs_retry','reported','completed'));validate_plan(p)
        self.plan=deepcopy(p);self.generation+=1;self.phase=self.cycle=0;self.record('plan',p,'ready')
    def begin(self,t):
        self.check(t,('ready',));self.cycle+=1;self.record('begin',{'source_pass':self.phase+1,'material':PASSES[self.phase][0],
            'error_hierarchy_reference':HIERARCHY,'source_bar_count':60,'host_clock_used':False,'audio_supplied':False},'performing')
    def end_take(self,t,ended):self.check(t,('performing',));require(ended is True,'take end before review');self.record('take_end',{},'await_release')
    def release(self,t,ack):
        self.check(t,('await_release','reopen_release'));require(ack is True,'physical release')
        if self.state=='await_release':self.record('release',{},'reporting')
        else:
            state=self.resume;require(state is not None,'resume state');self.resume=None;self.record('reopen_release',{},state)
    def report(self,t,r):
        self.check(t,('reporting',));fields(r,('source_pass','source_material','source_primary_test','bars','common','material_duties','incidents','notes'))
        require(type(r['source_pass']) is int and r['source_pass']==self.phase+1 and r['source_material']==PASSES[self.phase][0] and r['source_primary_test']==PASSES[self.phase][1],'current source stage')
        fields(r['common'],COMMON);fields(r['material_duties'],MATERIAL_DUTIES[self.phase]);answers=[*r['common'].values(),*r['material_duties'].values()]
        require(all(v in YN for v in answers) and text(r['notes']),'full source response');ok=all(v=='yes' for v in answers)
        require(type(r['bars']) is list and len(r['bars'])==60,'full source bar traversal report')
        for answer,source in zip(r['bars'],MASTER_BARS):
            fields(answer,('bar','source_chord','traversed'))
            require(type(answer['bar']) is int and answer['bar']==source['bar'] and answer['source_chord']==source['source_chord'] and answer['traversed'] in YN,'source bar report')
            ok=ok and answer['traversed']=='yes'
        require(type(r['incidents']) is list,'typed source incident list');counts=dict.fromkeys(ERRORS,0);policies=[]
        for i,e in enumerate(r['incidents'],1):
            fields(e,('incident','class','kind','bar','handled_per_source','description'))
            require(type(e['incident']) is int and e['incident']==i and type(e['class']) is str and e['class'] in ERRORS,'ordered incident source class')
            kinds,policy=ERRORS[e['class']]
            require(e['kind'] in kinds and type(e['bar']) is int and 1<=e['bar']<=60 and e['handled_per_source'] in YN and text(e['description']),'source error kind/bar/handling')
            counts[e['class']]+=1;policies.append({'incident':i,'source_policy':policy,'performance_verified':False})
            ok=ok and e['handled_per_source']=='yes'
        structural_clear=counts['structural']==0;ok=ok and structural_clear
        self.record('report',{'response':r,'reported_error_counts':counts,'incident_source_policies':policies,
            'source_no_structural_errors_reported':structural_clear,'manual_requirements_reported':ok,
            'performance_verified':False,'automatic_score':False},'reported' if ok else 'needs_retry')
    def advance(self,t):
        self.check(t,('reported',))
        if self.phase<7:self.phase+=1;self.cycle=0;self.record('next_pass',{},'ready')
        else:self.record('finish',{'manual_only':True,'source_acceptance':False},'completed')
    def retry(self,t,note):self.check(t,('reported','needs_retry'));require(text(note),'retry note');self.record('retry',{'note':note},'ready')
    def cancel(self,t):
        self.check(t,('setup','ready','performing','await_release','reporting','reported','needs_retry','completed','reopen_release'))
        if self.state!='reopen_release':self.resume='ready' if self.state in ('performing','await_release','reporting') else self.state
        self.generation+=1;self.record('cancel',{},'cancelled')
    def reopen(self,t):self.check(t,('cancelled',));self.generation+=1;self.record('reopen',{},'reopen_release')
def contract():
    return {'schema_version':'fathom-private-complete-rehearsal-ladder.1','key':KEY,
        'source_passes':[{'pass':i,'material':x[0],'primary_test':x[1],'advance_when':'no structural errors'} for i,x in enumerate(PASSES,1)],
        'source_heading':'ADD COMPLEXITY ONLY AFTER THE FORM SURVIVES THE PREVIOUS PASS','source_context_header':'240 CONTACTS',
        'source_error_hierarchy':HIERARCHY,'source_finishing_footer':FOOTER,'source_profiles':deepcopy(PROFILES),'source_master_bars':deepcopy(MASTER_BARS),
        'source_note_events':[],'fixed_source_contact_count':None,
        'plan_schema':{'prerequisites':['own_instrument','original_workbook'],'bpm':'finite positive external choice',
            'cue_provision':'written_chart/partner/external_media with description; no app cue implied',
            'bars':'60exact source bar/chord bindings with learner choices for'+','.join(CHOICES)},
        'response_schema':{'source_pass':'exact current1..8','source_material_primary_test':'exact source bindings','bars':'60source-bound traversed yes/no/uncertain',
            'common':list(COMMON),'material_duties':[list(x) for x in MATERIAL_DUTIES],
            'incidents':'ordered source class/kind/bar1..60/handling/description; empty allowed as manual no-errors report','notes':'required','enum':list(YN)},
        'authored_policies':['Each source pass uses full60-bar TXT master form; this association is explicit and pending distinct review.',
            'Source error rules are instructions before playing, not detected or automatically remedied by the app.',
            'Structural incidents block advancement even if repaired; source handling remains recorded.',
            'Handled functional/cosmetic incidents alone do not block advancement; no invented zero-error score.',
            'Take end plus release precedes reports and cosmetic review; material/form failures still require retry.',
            'No stage skip; retry current pass; current instance/key/generation/phase/cycle/action/state ownership.',
            'Cancel/reopen repeats interrupted stage after release; new plan resets stage1 and preserves history.',
            'No saved progress/Attempt/mastery/credit or source/native acceptance.'],
        'automatic_evaluation':False,'performance_observed':False,'audio_supplied':False,'timing_scheduled':False,
        'mastery_awarded':False,'credit_awarded':False,'persistence':False,'canonical_binding':None}
