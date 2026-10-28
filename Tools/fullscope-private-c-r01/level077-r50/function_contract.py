"""Manual partner-source function hearing; symbolic answers are not audio evidence."""
from copy import deepcopy
from uuid import uuid4
ROMAN=('I','ii','iii','IV','V','vi','vii dim')
FAMILY=('tonic','predominant','tonic family','predominant','dominant','tonic family','dominant')
SENSATION=('home / rest','moves toward V','weak tonic substitute','opens away from I','strong return pressure','relative-minor color','leading-tone tension')
COMPRESSED=('tonic','predominant','tonic','predominant','dominant','tonic','dominant')
QUALITY=('major','minor','minor','major','major','minor','diminished')
SCALES={'C':('C','D','E','F','G','A','B'),'G':('G','A','B','C','D','E','F#'),
 'D':('D','E','F#','G','A','B','C#'),'A':('A','B','C#','D','E','F#','G#'),
 'E':('E','F#','G#','A','B','C#','D#'),'F':('F','G','A','Bb','C','D','E')}
PC={'C':0,'B#':0,'C#':1,'Db':1,'D':2,'D#':3,'Eb':3,'E':4,'Fb':4,'E#':5,'F':5,'F#':6,'Gb':6,'G':7,'G#':8,'Ab':8,'A':9,'A#':10,'Bb':10,'B':11,'Cb':11}
KEYS=tuple('exercise-completeness-r01/level077/moduleb/p005-t1-r'+str(n)+'/'+suffix for n,suffix in ((1,'i'),(2,'ii'),(3,'iii'),(4,'iv'),(5,'v'),(6,'vi'),(8,'viidim')))+('exercise-completeness-r01/level077/moduleb/p005-supplement01/blindtest',)
BLIND='Partner plays one diatonic chord in C, G, D, A, E, or F major. Answer function family first; Roman numeral second; chord name third.'
REPEAT='Do not infer function from fretboard shape. Repeat the test with rootless triads or shell voicings.'
DUTIES=('chord_heard','root_then_third_performed','root_correct','third_correct','tonic_resolution_heard','no_fret_shape_inference','declared_form_used','source_order')
YN=('yes','no','uncertain')

class Refusal(ValueError):pass
def require(ok,message):
    if not ok:raise Refusal(message)
def fields(value,names):require(type(value) is dict and set(value)==set(names),'exact typed field set')
def text(value):return type(value) is str and bool(value.strip())
def validate_plan(p,index):
    require(type(index) is int and 0<=index<8,'source child index')
    fields(p,('prerequisites','partner','key','source_roman','repeat_form','presentation_descriptions'))
    fields(p['prerequisites'],('instrument_access','original_workbook'))
    require(all(x is True for x in p['prerequisites'].values()),'source/task prerequisites')
    fields(p['partner'],('kind','reference','ready'))
    require(p['partner']['kind']=='external_human' and text(p['partner']['reference']) and p['partner']['ready'] is True,'actual external partner required')
    require(type(p['key']) is str and p['key'] in SCALES,'one of six printed major keys')
    require(type(p['source_roman']) is str and p['source_roman'] in ROMAN and (index==7 or p['source_roman']==ROMAN[index]),'exact table row or supplement source-player choice')
    require(type(p['repeat_form']) is str and p['repeat_form'] in ('rootless_triad','shell_voicing'),'printed repeat alternatives')
    fields(p['presentation_descriptions'],('ordinary','repeat'))
    require(all(text(x) for x in p['presentation_descriptions'].values()),'partner descriptions for both actual presentations')

class FunctionFlow:
    def __init__(self,key):
        require(type(key) is str and key in KEYS,'exact eight existing children')
        self.key=key;self.index=KEYS.index(key);self.instance=uuid4().hex
        self.generation=self.phase=self.cycle=self.action=0;self.state='setup';self.plan=None;self.resume=None
        self.history=[];self.answers={};self.answer_history=[];self.ever_revealed=False;self.current_revealed=False
    def token(self):return (self.instance,self.key,self.generation,self.phase,self.cycle,self.action,self.state)
    def check(self,t,states):
        require(type(t) is tuple and t==self.token(),'current source/instance/generation/presentation/action token')
        require(self.state in states,'wrong state')
    def record(self,kind,data,state):
        self.history.append({'kind':kind,'generation':self.generation,'presentation':self.phase,'cycle':self.cycle,'data':deepcopy(data)})
        self.action+=1;self.state=state
    def set_plan(self,t,p):
        self.check(t,('setup','ready','reported','needs_retry','completed'));validate_plan(p,self.index)
        self.plan=deepcopy(p);self.generation+=1;self.phase=self.cycle=0;self.answers={};self.current_revealed=False;self.record('plan',p,'ready')
    def form(self):
        require(self.plan is not None,'plan required');return 'ordinary_diatonic_chord' if self.phase==0 else self.plan['repeat_form']
    def source_view(self):
        require(self.plan is not None,'plan required');i=ROMAN.index(self.plan['source_roman']);scale=SCALES[self.plan['key']]
        return {'key':self.plan['key'],'roman':ROMAN[i],'printed_family':FAMILY[i],'compressed_family':COMPRESSED[i],'functional_sensation':SENSATION[i],
          'chord':{'root':scale[i],'quality':QUALITY[i]},'sing_order':[{'role':'root','pitch_class':scale[i]},{'role':'third','pitch_class':scale[(i+2)%7]}],
          'resolution':{'roman':'I','chord':{'root':scale[0],'quality':'major'},'performer':'external partner, authored interface choice'},
          'presentation':self.form(),'partner_description':self.plan['presentation_descriptions']['ordinary' if self.phase==0 else 'repeat'],
          'voicing_notes':None,'octave_fret_timing':None,'sound_supplied_by_app':False}
    def learner_view(self):
        out={'state':self.state,'key':None if self.plan is None else self.plan['key'],'presentation':None if self.plan is None else self.form(),
          'learner_answers':deepcopy(self.answers),'previously_revealed':self.ever_revealed,'prior_answers_retained':bool(self.answer_history),
          'preset_roman_visible':ROMAN[self.index] if self.index<7 else None,'blind_assessment_claim':False}
        if self.current_revealed:out['reference_answer']=self.source_view()
        return out
    def begin(self,t,ready,form_confirmed):
        self.check(t,('ready',));require(ready is True and form_confirmed is True,'current partner readiness and presentation confirmation')
        self.cycle+=1;self.answers={};self.current_revealed=False;self.record('begin',{'declared_form':self.form(),'audio_observed':False},'listening')
    def end_listening(self,t,ack):
        self.check(t,('listening',));require(ack is True,'listening ended');self.record('end_listening',{},'answer_release')
    def release(self,t,ack):
        self.check(t,('answer_release','report_release','reopen_release'));require(ack is True,'manual release required')
        if self.state=='reopen_release':
            state=self.resume;require(state is not None,'resume state');self.resume=None;self.record('reopen_release',{},state)
        else:self.record('release',{},'answer_family' if self.state=='answer_release' else 'reporting')
    def answer(self,t,kind,value):
        require(type(kind) is str and kind in ('family','roman','chord'),'response kind')
        self.check(t,('answer_'+kind,))
        if kind=='family':require(type(value) is str and value in ('tonic','predominant','dominant'),'typed family response')
        elif kind=='roman':require(type(value) is str and value in ROMAN,'typed Roman response')
        else:
            fields(value,('root','quality'));require(type(value['root']) is str and value['root'] in PC and type(value['quality']) is str and value['quality'] in ('major','minor','diminished'),'typed chord root/quality response')
        self.answers[kind]=deepcopy(value);self.answer_history.append({'generation':self.generation,'presentation':self.phase,'cycle':self.cycle,'kind':kind,'value':deepcopy(value)})
        self.record('answer_'+kind,{'value':value},{'family':'answer_roman','roman':'answer_chord','chord':'committed'}[kind])
    def reveal(self,t):
        self.check(t,('committed',));require(set(self.answers)=={'family','roman','chord'},'all answers committed')
        self.ever_revealed=self.current_revealed=True;self.record('reveal',{'source':self.source_view()},'sing_root')
    def sing_root(self,t,ack):
        self.check(t,('sing_root',));require(ack is True,'root singing attempted');self.record('sing_root',{},'sing_third')
    def sing_third(self,t,ack):
        self.check(t,('sing_third',));require(ack is True,'third singing attempted');self.record('sing_third',{},'resolve_tonic')
    def resolve_tonic(self,t,ack):
        self.check(t,('resolve_tonic',));require(ack is True,'external partner tonic resolution attempted');self.record('resolve_tonic',{'source_target':'I','audio_observed':False},'report_release')
    def report(self,t,r):
        self.check(t,('reporting',));fields(r,('key','source_roman','presentation','duties','diagnosis','notes'));fields(r['duties'],DUTIES)
        require(r['key']==self.plan['key'] and r['source_roman']==self.plan['source_roman'] and r['presentation']==self.form(),'source/form report binding')
        require(all(type(x) is str and x in YN for x in r['duties'].values()) and type(r['diagnosis']) is str and text(r['notes']),'full manual report')
        source=self.source_view();chord=self.answers['chord']
        symbolic={'family':self.answers['family']==source['compressed_family'],'roman':self.answers['roman']==source['roman'],
          'chord':PC[chord['root']]==PC[source['chord']['root']] and chord['quality']==source['chord']['quality']}
        ok=all(symbolic.values()) and all(x=='yes' for x in r['duties'].values())
        if not ok:require(text(r['diagnosis']),'wrong/uncertain response diagnosis')
        self.record('report',{'response':r,'answers':self.answers,'symbolic_matches':symbolic,'root_spelling_match':chord['root']==source['chord']['root'],
          'manual_requirements_reported':ok,'acoustically_verified':False,'automatic_score':False},'reported' if ok else 'needs_retry')
    def next_presentation(self,t):
        self.check(t,('reported',));require(self.phase==0,'only one printed repeat');self.phase=1;self.cycle=0;self.answers={};self.current_revealed=False;self.record('next_presentation',{},'ready')
    def retry(self,t,diagnosis):
        self.check(t,('reported','needs_retry'));require(text(diagnosis),'explicit retry diagnosis');self.record('retry',{'diagnosis':diagnosis},'ready')
    def finish(self,t):
        self.check(t,('reported',));require(self.phase==1,'ordinary and repeat required');self.record('finish',{'manual_only':True,'mastery_awarded':False,'source_acceptance':False},'completed')
    def cancel(self,t):
        self.check(t,('setup','ready','listening','answer_release','answer_family','answer_roman','answer_chord','committed','sing_root','sing_third','resolve_tonic','report_release','reporting','reported','needs_retry','completed','reopen_release'))
        if self.state!='reopen_release':self.resume=self.state if self.state in ('setup','ready','reported','needs_retry','completed') else 'ready'
        self.generation+=1;self.record('cancel',{},'cancelled')
    def reopen(self,t):
        self.check(t,('cancelled',));self.generation+=1;self.record('reopen',{},'reopen_release')

def contract(index):
    fields_=[{'Roman':ROMAN[i],'Family':FAMILY[i],'Functional sensation':SENSATION[i],'Sing after chord':'root then 3rd','Resolve':'I'} for i in range(7)]
    return {'schema_version':'fathom-private-function-hearing-manual.1','key':KEYS[index],
      'source_fields':fields_ if index==7 else fields_[index],'source_blind_instruction':BLIND,'source_repeat_instruction':REPEAT,
      'source_compression':{'tonic':['I','iii','vi'],'predominant':['ii','IV'],'dominant':['V','vii dim']},
      'source_keys':list(SCALES),'source_heading':'7 FUNCTIONS | TONIC / PREDOMINANT / DOMINANT',
      'source_note_events':[],'source_fixed_voicing_octave_timing':None,'harmonic_rest_is_silence':False,
      'plan_schema':{'partner':'actual external human with current readiness and form confirmation','key':list(SCALES),
        'target':'fixed source table row' if index<7 else 'provider-selected one of seven existing Roman functions',
        'presentations':['ordinary_diatonic_chord','chosen rootless_triad or shell_voicing'],'voicing':'partner supplied/confirmed; description retained, no generated note recipe'},
      'response_schema':{'order':['family','roman','chord'],'family':['tonic','predominant','dominant'],'roman':list(ROMAN),'chord':['recognized root pitch-class spelling','major/minor/diminished'],
        'manual_duties':list(DUTIES),'manual_enum':list(YN),'failed_or_uncertain':'diagnosis and retry current presentation'},
      'authored_policies':['Answer-before-singing merges table practice with blind-test response order; explicit reveal follows all three answers, then root singing, third singing and I resolution.',
        'External partner performing tonic resolution is an authored interface choice; source says Resolve I without fixing performer. No mandatory guitar attack is invented.',
        'Table target Roman is already visible through its source identity; no blind-assessment claim. Supplement withholds current reference answers until explicit reveal; prior reveal/history remain sticky.',
        'Major-key chord/root/third pitch classes are symbolic derivations; conventional spelling retained, equivalent enharmonic typed roots accepted separately from spelling match.',
        'Source-player view retains full chosen script. Views are presentation boundaries, not security against reading original source files.',
        'Rootless triads is the literal source term. Actual source voicing remains an external partner prerequisite, not a newly asserted automatic realization.',
        'Release and current-action tokens; cancel/reopen repeats interrupted presentation, preserving plans/history/reveal status; new plan resets ordinary presentation only.'],
      'automatic_evaluation':False,'performance_observed':False,'audio_supplied':False,'audio_inspected':False,'timing_scheduled':False,
      'credit_awarded':False,'mastery_awarded':False,'persistence':False,'canonical_binding':None}
