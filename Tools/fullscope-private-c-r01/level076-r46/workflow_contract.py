"""Ordered manual transcription worksheet; source audio and truth remain external."""
from copy import deepcopy
from uuid import uuid4
KEY='exercise-completeness-r01/level076/workbookfoundations/p002-u001/thetranscriptionworkflowanduncertaintynotation'
STAGES=(('FORM','How many bars? What repeats? Where is the strongest arrival?',('bar_count','repeats','strongest_arrival')),
 ('PULSE','Can I clap the beat? Is the subdivision straight, swung, triplet, or sixteenth-based?',('clap_beat','subdivision')),
 ('TONIC','Which pitch sounds finished when the excerpt stops?',('finished_pitch',)),
 ('BASS','What is the lowest structural pitch at each change?',('structural_bass_at_each_change',)),
 ('QUALITY','Major, minor, dominant, diminished, suspended, or uncertain?',('chord_quality',)),
 ('RHYTHM','Where are the contacts, rests, ties, anticipations, and releases?',('contacts','rests','ties','anticipations','releases')),
 ('MELODY','Which notes are structural targets and which are approaches?',('structural_targets','approaches')),
 ('ARRANGEMENT','What register, density, articulation, dynamics, and cue behavior define the part?',('register','density','articulation','dynamics','cue_behavior')))
TXT_STACK=('Form','Pulse','Bass','Harmony','Rhythm','Melody','Arrangement')
PDF_MARKS='Uncertainty marks: ? = unresolved; / = two plausible answers; ( ) = optional or ornamental; ! = verified by at least two independent clues.'
TXT_MARKS=('? = unresolved','/ = two plausible answers','( ) = optional or ornamental','! = verified by two independent clues')
MARKS=('hypothesis','?','/','()','!')
class Refusal(ValueError):pass
def require(ok,msg):
    if not ok:raise Refusal(msg)
def fields(o,names):require(type(o) is dict and set(o)==set(names),'field set')
def text(x):return type(x) is str and bool(x.strip())
def normalized(x):return x.strip().casefold()
def validate_answer(a):
    fields(a,('mark','answers','clues','independence_self_report','notes','next_check'))
    require(a['mark'] in MARKS and text(a['notes']) and type(a['next_check']) is str,'mark and explanation')
    values=a['answers'];require(type(values) is list and all(text(x) for x in values),'manual answer texts')
    require(len({normalized(x) for x in values})==len(values),'distinct plausible answers')
    mark=a['mark'];require((mark=='?' and len(values)<=1) or (mark=='/' and len(values)==2) or (mark in ('hypothesis','()','!') and len(values)==1),'mark-specific answer arity')
    if mark in ('?','/'):require(text(a['next_check']),'uncertainty requires next check')
    clues=a['clues'];require(type(clues) is list and type(a['independence_self_report']) is bool,'clue list and explicit self-report')
    ids=[];families=[]
    for clue in clues:
        fields(clue,('id','family','observation'));require(all(text(x) for x in clue.values()),'specific clue evidence')
        ids.append(normalized(clue['id']));families.append(normalized(clue['family']))
    require(len(set(ids))==len(ids),'duplicate clue identity')
    if mark=='!':require(len(clues)>=2 and len(set(families))>=2 and a['independence_self_report'] is True,'at least two distinct clue families plus learner independence assertion')
    else:require(a['independence_self_report'] is False,'only verified-mark evidence may assert independence')
    return {'manual_status':{'hypothesis':'learner_hypothesis','?':'unresolved','/':'two_plausible_answers','()':'optional_or_ornamental','!':'learner_marked_verified'}[mark],
      'app_verified':False,'independence_verified':False,'audio_inspected':False}
def validate_plan(p):
    fields(p,('original_workbook','provider','reference','excerpt_boundaries','source_ready'))
    require(p['original_workbook'] is True and p['source_ready'] is True,'workbook/external source prerequisites')
    require(p['provider'] in ('external_recording','external_human_player') and text(p['reference']) and text(p['excerpt_boundaries']),'identified external excerpt')
class Workflow:
    def __init__(self,key):
        require(key==KEY,'one exact source workflow');self.key=key;self.instance=uuid4().hex
        self.generation=self.stage=self.cycle=self.action=0;self.state='setup';self.plan=None;self.history=[];self.resume=None;self.latest={}
    def token(self):return (self.instance,self.key,self.generation,self.stage,self.cycle,self.action,self.state)
    def check(self,t,states):require(type(t) is tuple and t==self.token(),'stale/foreign token');require(self.state in states,'wrong state')
    def record(self,kind,data,state):
        self.history.append({'kind':kind,'generation':self.generation,'stage':self.stage+1,'cycle':self.cycle,'data':deepcopy(data)});self.action+=1;self.state=state
    def set_plan(self,t,p):
        self.check(t,('setup','ready','reported','completed'));validate_plan(p);self.plan=deepcopy(p);self.generation+=1;self.stage=self.cycle=0;self.latest={};self.record('plan',p,'ready')
    def begin(self,t,source_ready):
        self.check(t,('ready',));require(source_ready is True,'current external excerpt readiness');self.cycle+=1
        self.record('begin',{'source_stage':STAGES[self.stage][0],'question':STAGES[self.stage][1],'audio_supplied':False},'listening')
    def end_stage(self,t,ended):self.check(t,('listening',));require(ended is True,'listening/manual experiment complete');self.record('stage_end',{},'await_release')
    def release(self,t,ack):
        self.check(t,('await_release','reopen_release'));require(ack is True,'manual release')
        if self.state=='await_release':self.record('release',{},'responding')
        else:
            state=self.resume;require(state is not None,'resume');self.resume=None;self.record('reopen_release',{},state)
    def submit(self,t,r):
        self.check(t,('responding',));fields(r,('source_stage','source_question','responses'))
        stage,question,questions=STAGES[self.stage];require(r['source_stage']==stage and r['source_question']==question,'exact current source stage/question')
        fields(r['responses'],questions);dispositions={k:validate_answer(a) for k,a in r['responses'].items()}
        data={'response':r,'dispositions':dispositions,'unresolved_fields':sum(x['mark'] in ('?','/') for x in r['responses'].values()),
          'learner_marked_verified_fields':sum(x['mark']=='!' for x in r['responses'].values()),'app_verified':False,'credit_awarded':False}
        self.latest[self.stage]=deepcopy(data);self.record('submission',data,'reported')
    def repeat(self,t,note):self.check(t,('reported',));require(text(note),'repeat purpose');self.record('repeat',{'note':note},'ready')
    def next_stage(self,t):
        self.check(t,('reported',));require(self.stage<7,'final stage has no successor');self.stage+=1;self.cycle=0;self.record('next',{},'ready')
    def finish(self,t):
        self.check(t,('reported',));require(self.stage==7 and set(self.latest)==set(range(8)),'all eight source stages required')
        self.record('finish',{'manual_workflow_recorded':True,'unresolved_fields':sum(r['unresolved_fields'] for r in self.latest.values()),
         'learner_marked_verified_fields':sum(r['learner_marked_verified_fields'] for r in self.latest.values()),
         'app_verified':False,'source_acceptance':False,'credit_awarded':False,'mastery_awarded':False},'completed')
    def cancel(self,t):
        self.check(t,('setup','ready','listening','await_release','responding','reported','completed','reopen_release'))
        if self.state!='reopen_release':self.resume='ready' if self.state in ('listening','await_release','responding') else self.state
        self.generation+=1;self.record('cancel',{},'cancelled')
    def reopen(self,t):self.check(t,('cancelled',));self.generation+=1;self.record('reopen',{},'reopen_release')
def contract():
    return {'schema_version':'fathom-private-transcription-workflow.1','key':KEY,'source_heading':'DO NOT SOLVE ALL LAYERS AT ONCE',
      'source_stages':[{'number':i,'name':n,'question':q,'authored_response_fields':list(f)} for i,(n,q,f) in enumerate(STAGES,1)],
      'source_pdf_uncertainty':PDF_MARKS,'source_txt_stack':list(TXT_STACK),'source_txt_uncertainty':list(TXT_MARKS),
      'workflow_basis':'Exact PDFp2 eight-stage route; TXTseven-pass stack retained separately, no equivalence/correction adjudicated.',
      'source_note_events':[],'source_answers_prefilled':False,
      'plan_schema':{'provider':['external_recording','external_human_player'],'reference':'learner source description, not inspected','excerpt_boundaries':'required manual excerpt locator','source_ready':'explicit plan and begin acknowledgment'},
      'response_schema':{'source_stage':'exact current stage','source_question':'exact complete source question','responses':'exact authored fieldset for every subquestion',
         'marks':list(MARKS),'clues':'id/family/observation, actual content self-reported','verification_label':'learner_marked_verified; app_verifiedFalse'},
      'authored_policies':['All eight stages are recorded sequentially; unresolved/alternative answers retain next-check plans and do not fabricate resolution.',
        'Distinct clue IDs/families plus independence self-report guard !, not proof of clue independence or acoustic truth.',
        'Hypothesis is explicit unmarked-answer mode; optional/ornamental does not remove required fields.',
        'External excerpt/provider supplies actual audio; no playback, recording, media inspection or recognition.',
        'Current action/stage tokens, end/release before response; repeat/cancel/reopen preserves history; new excerpt resets first stage.',
        'Completed manual workflow can retain unresolved fields and carries no score, mastery or credit.'],
      'automatic_evaluation':False,'performance_observed':False,'audio_supplied':False,'audio_inspected':False,'app_verified':False,
      'timing_scheduled':False,'credit_awarded':False,'mastery_awarded':False,'persistence':False,'canonical_binding':None}
