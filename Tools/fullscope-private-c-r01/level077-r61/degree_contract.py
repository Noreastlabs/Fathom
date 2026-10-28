"""Private spoken-degree / three-register manual task. No sound, clock or credit."""
from copy import deepcopy
from uuid import uuid4
RAW=(('C major','3','E'),('C major','7','B'),('G major','3','B'),('D major','7','C#'),('A major','6','F#'),('E major','2','F#'),('F major','4','Bb'),('A minor','b3','C'),('A minor','b7','G'),('E minor','5','B'),('D minor','b6','Bb'),('A harmonic minor','7','G#'),('A melodic minor','6','F#'),('A melodic minor','7','G#'))
KEYS=tuple(f'exercise-completeness-r01/level077/modulef/p013-t1-r{n}/{context.replace(" ","").lower()}' for n,(context,_,_) in zip((*range(1,14),15),RAW))
PC={'C':0,'B#':0,'C#':1,'Db':1,'D':2,'D#':3,'Eb':3,'E':4,'Fb':4,'E#':5,'F':5,'F#':6,'Gb':6,'G':7,'G#':8,'Ab':8,'A':9,'A#':10,'Bb':10,'B':11,'Cb':11}
TUNING={'E':40,'A':45,'D':50,'G':55,'B':59,'e':64};REGISTERS=('low','mid','high');YN=('yes','no','uncertain')
CUE_DUTIES=('only_context_and_degree','no_guitar_root_reference')
COMMON=('pitch_correct','degree_function_maintained','single_silent_setup','no_searching','no_guitar_root_reference','register_order')
INITIAL=('pitch_name_sung','sung_pitch_correct');TRANSFER=('same_function','new_sounding_register')
FOOTER='Partner names only context + degree. Player sings pitch name, then plays low/mid/high locations. No root note is supplied by the guitar.'
HEADING='ONE SILENT SETUP, ONE ATTACK; THEN TRANSFER THE SAME FUNCTION TO ANOTHER REGISTER'
class Refusal(ValueError):pass
def require(ok,msg):
    if not ok:raise Refusal(msg)
def fields(x,n):require(type(x) is dict and set(x)==set(n),'exact typed field set')
def text(x):return type(x) is str and bool(x.strip())
def enums(x,n):fields(x,n);require(all(type(v) is str and v in YN for v in x.values()),'manual yes/no/uncertain duties')
def validate_plan(p):
    fields(p,('prerequisites','partner'));fields(p['prerequisites'],('original_workbook','own_instrument'));require(all(x is True for x in p['prerequisites'].values()),'manual prerequisites')
    v=p['partner'];fields(v,('kind','reference','ready'));require(v['kind']=='external_human' and text(v['reference']) and v['ready'] is True,'actual external spoken-cue partner')
def validate_contact(c):
    fields(c,('midi','string','fret'));require(type(c['midi']) is int and type(c['fret']) is int and type(c['string']) is str and c['string'] in TUNING and 0<=c['fret']<=24 and TUNING[c['string']]+c['fret']==c['midi'],'exact standard-tuning chosen contact')
def validate_locations(p):
    fields(p,REGISTERS)
    for c in p.values():validate_contact(c)
    m=[p[k]['midi'] for k in REGISTERS];require(m[0]<m[1]<m[2] and len({x%12 for x in m})==1,'three increasing sounding registers of chosen pitch class')

class DegreeFlow:
    def __init__(self,key):
        require(type(key) is str and key in KEYS,'exact fourteen source children');self.key=key;self.index=KEYS.index(key);self.instance=uuid4().hex
        self.generation=self.stage=self.cycle=self.action=0;self.state='setup';self.plan=self.resume=self.locations=self.named_pitch=self.cue_report=None
        self.history=[];self.response_history=[];self.location_history=[];self.first_correct=False;self.current_revealed=self.ever_revealed=False
    def token(self):return (self.instance,self.key,self.generation,self.stage,self.cycle,self.action,self.state)
    def check(self,t,states):require(type(t) is tuple and t==self.token(),'current instance/source/generation/stage/action owner');require(self.state in states,'wrong state')
    def record(self,kind,data,state):self.history.append({'kind':kind,'generation':self.generation,'stage':self.stage,'cycle':self.cycle,'data':deepcopy(data)});self.action+=1;self.state=state
    def clear_initial(self):self.named_pitch=self.cue_report=self.locations=None;self.first_correct=False;self.current_revealed=False
    def set_plan(self,t,p):
        self.check(t,('setup','completed'));validate_plan(p);self.plan=deepcopy(p);self.generation+=1;self.stage=self.cycle=0;self.clear_initial();self.record('chosen_partner_plan',p,'ready')
    def target(self):require(self.locations is not None,'chosen locations required');return {'register':REGISTERS[self.stage],'contact':deepcopy(self.locations[REGISTERS[self.stage]])}
    def source_player_view(self):
        c,d,a=RAW[self.index];return {'key':self.key,'spoken_cue':{'context':c,'degree':d},'reference_answer':a,'instruction':'Speak only context and degree; do not supply a guitar root note or answer pitch.','audio_supplied':False}
    def learner_view(self):
        out={'key':self.key,'state':self.state,'context':RAW[self.index][0],'degree':RAW[self.index][1],'register':REGISTERS[self.stage],
          'captured_sung_name':self.named_pitch,'chosen_locations':deepcopy(self.locations),'previously_revealed':self.ever_revealed,'prior_responses_retained':bool(self.response_history),'blind_assessment_claim':False}
        if self.current_revealed:out['reference_answer']=RAW[self.index][2]
        return out
    def begin(self,t,confirmation=None):
        self.check(t,('ready',))
        if self.stage==0:
            fields(confirmation,('key','context','degree','ready'));require(confirmation=={'key':self.key,'context':RAW[self.index][0],'degree':RAW[self.index][1],'ready':True} and confirmation['ready'] is True,'exact current partner cue confirmation')
            self.clear_initial();state='hearing'
        else:require(confirmation is None and self.first_correct,'transfer retains current source/name after first manual success');state='silent_setup'
        self.cycle+=1;self.record('begin',{'confirmation':confirmation,'source_observed':False},state)
    def heard(self,t,r):self.check(t,('hearing',));enums(r,CUE_DUTIES);self.cue_report=deepcopy(r);self.record('manual_spoken_cue_report',r,'singing')
    def sung_name(self,t,r):
        self.check(t,('singing',));fields(r,('pitch_name','singing_attempted'));v=r['pitch_name'];require((v is None or (type(v) is str and v in PC)) and r['singing_attempted'] is True,'typed sung pitch-name response or unknown')
        self.named_pitch=v;self.response_history.append({'generation':self.generation,'cycle':self.cycle,'response':deepcopy(r)});self.record('sung_name',{'response':r,'compared_to_hidden_answer':False},'choose_locations')
    def choose_locations(self,t,p):
        self.check(t,('choose_locations',));validate_locations(p);self.locations=deepcopy(p);self.location_history.append({'generation':self.generation,'cycle':self.cycle,'locations':deepcopy(p)})
        self.record('chosen_response_locations',{'locations':p,'compared_to_hidden_answer':False},'silent_setup')
    def cannot_respond(self,t,diagnosis,learner_released):
        self.check(t,('singing','choose_locations'));require(text(diagnosis) and learner_released is True,'unable-to-respond diagnosis and manual release');self.record('unable_to_respond',{'diagnosis':diagnosis,'no_response_invented':True},'needs_retry')
    def setup_target(self,t,ack):self.check(t,('silent_setup',));require(ack is True,'one silent setup attempted');self.record('silent_setup',self.target(),'attack')
    def attack(self,t,ack):self.check(t,('attack',));require(ack is True,'one decisive attack attempted');self.record('attack_attempt',{'observed_attack_count':None},'await_release')
    def release(self,t,ack):
        self.check(t,('await_release','reopen_release'));require(ack is True,'manual physical release')
        if self.state=='reopen_release':
            state=self.resume;require(state is not None,'saved resume state');self.resume=None
            if state=='ready' and self.stage==0:self.clear_initial()
        else:state='reveal' if self.stage==0 else 'reporting'
        self.record('manual_release',{'sound_stop_observed':False},state)
    def reveal(self,t):self.check(t,('reveal',));self.current_revealed=self.ever_revealed=True;self.record('post_playing_reveal',{},'reporting')
    def report(self,t,r):
        self.check(t,('reporting',));fields(r,('key','context','degree','register','contact','named_pitch','attack_count','common','stage_duties','diagnosis','notes'))
        enums(r['common'],COMMON);enums(r['stage_duties'],INITIAL if self.stage==0 else TRANSFER);validate_contact(r['contact']);target=self.target()
        require(r['key']==self.key and r['context']==RAW[self.index][0] and r['degree']==RAW[self.index][1] and r['register']==target['register'] and r['contact']==target['contact'] and r['named_pitch']==self.named_pitch,'exact source/register/chosen-response binding')
        require(type(r['attack_count']) is int and r['attack_count']>=0 and type(r['diagnosis']) is str and text(r['notes']),'actual manual count and report')
        expected=PC[RAW[self.index][2]];matches={'sung_name':self.named_pitch is not None and PC[self.named_pitch]==expected,'chosen_pitch_class':target['contact']['midi']%12==expected}
        ok=all(matches.values()) and all(v=='yes' for v in self.cue_report.values()) and r['attack_count']==1 and all(v=='yes' for v in (*r['common'].values(),*r['stage_duties'].values()))
        if not ok:require(text(r['diagnosis']),'wrong/unknown response, cue failure, count or manual duty needs diagnosis')
        if ok and self.stage==0:self.first_correct=True
        self.record('manual_report',{'response':r,'symbolic_reference_matches':matches,'manual_requirements_reported':ok,'performance_verified':False},'reported' if ok else 'needs_retry')
    def next_register(self,t):self.check(t,('reported',));require(self.stage<2 and self.first_correct,'first positive report and no fourth register');self.stage+=1;self.record('next_register',{},'ready')
    def retry(self,t,diagnosis):
        self.check(t,('reported','needs_retry'));require(text(diagnosis),'explicit retry diagnosis')
        if self.stage==0:self.clear_initial()
        self.record('retry',{'diagnosis':diagnosis},'ready')
    def finish(self,t):self.check(t,('reported',));require(self.stage==2 and self.first_correct,'all three registers manually reported');self.record('finish',{'manual_only':True,'mastery_awarded':False,'source_acceptance':False},'completed')
    def cancel(self,t):
        stable=('setup','ready','reporting','reported','needs_retry','completed')
        self.check(t,stable+('hearing','singing','choose_locations','silent_setup','attack','await_release','reveal','reopen_release'))
        if self.state!='reopen_release':self.resume=self.state if self.state in stable else 'ready'
        self.generation+=1;self.record('cancel',{},'cancelled')
    def reopen(self,t):self.check(t,('cancelled',));self.generation+=1;self.record('reopen',{},'reopen_release')

def contract(i):
    c,d,a=RAW[i]
    return {'schema_version':'fathom-private-spoken-degree-realization.1','key':KEYS[i],'source_fields':{'Context':c,'Requested degree':d,'Answer pitch':a,'Low':'','Mid':'','High':''},
      'printed_heading':HEADING,'printed_footer':FOOTER,'source_extent_header':'14 COMMANDS | 56 REALIZATIONS','actual_commands':14,'register_columns':list(REGISTERS),'chosen_register_realizations':42,
      'source_note_events':[],'source_absolute_register_contact_timing':None,
      'plan_schema':{'partner':'actual external human speaking only context+degree; no guitar root reference','prerequisites':'original workbook and own instrument',
        'locations':'after sung-name response, three same-pitch-class standard-tuning contacts fret0..24 with strictly increasing MIDI; no hidden-answer comparison before playing'},
      'response_schema':{'pitch_name':'finite chromatic spellings or null/unknown; singing_attempted true','cue_duties':list(CUE_DUTIES),'common_duties':list(COMMON),'initial_duties':list(INITIAL),'transfer_duties':list(TRANSFER),
        'enum':list(YN),'attack_count':'nonnegative actual manual count; positive report requires1','failure':'diagnosis/retry after manual release; unable-to-respond allows no invented answer'},
      'authored_policies':['Original exact answer pitch is source-role reference until after initial playing/release and explicit reveal. Wrong/unknown sung names and structurally valid wrong chosen pitch classes are retained without early correction.',
        'Low/mid/high are chosen relative sounding registers, not source-fixed octaves. Same MIDI on a different string is not another register. Three registers only;56heading does not invent a fourth.',
        'Source exact context/degree confirmation, no guitar root reference, sung name then chosen locations, single setup/attack/release/report. First positive manual report opens ordered mid/high transfer.',
        'Initial singing is required; no unprinted ban on optional re-singing is imposed. All performance/cue/attack statements are manual, not sound inspection.',
        'First-register retry repeats spoken cue/name/locations; later retry repeats current register. Current source/generation/stage/action ownership and release/cancel/reopen preserve history and earlier reveal.',
        'Final official row15 key remains unchanged although this page contains14printedcommands; no locator correction claimed.'],
      'automatic_evaluation':False,'performance_observed':False,'audio_supplied':False,'audio_inspected':False,'timing_scheduled':False,'credit_awarded':False,'mastery_awarded':False,'persistence':False,'canonical_binding':None}
