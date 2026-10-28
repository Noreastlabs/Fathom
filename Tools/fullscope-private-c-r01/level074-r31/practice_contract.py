"""Private manual workflow. No host tempo, audio, persistence or performance inference."""
from dataclasses import dataclass
from copy import deepcopy
import math

@dataclass(frozen=True)
class Token:
    instance: object
    key: str
    generation: int
    phase: int
    cycle: int
    action: int
    stage: str

class PracticeFlow:
    common_fields=('complete_scope','clean','small_dynamic_difference','note_length_preserved','no_gripping_or_breath_holding')
    def __init__(self,contract):
        self.contract=deepcopy(contract);self.instance=object();self.key=contract['package_key']
        self.generation=self.phase=1;self.cycle=self.action=self.clean_cycles=0;self.stage='setup'
        self.bpm=self.mode=self.resume_stage=self.current_report=self.repair_selection=self.last_quarter_click=None
        self.external_click=self.recorder=False;self.history=[]
    def token(self):return Token(self.instance,self.key,self.generation,self.phase,self.cycle,self.action,self.stage)
    def _check(self,t,stages):
        if t!=self.token() or self.stage not in stages:raise ValueError('stale/foreign/wrong-stage action')
    def _move(self,s):self.stage=s;self.action+=1
    def source_phase(self):return deepcopy(self.contract['phases'][self.phase-1])
    @staticmethod
    def _text(x):
        if not isinstance(x,str) or not x.strip():raise ValueError('explicit choice/reason required')
    @staticmethod
    def _bpm(x):
        if type(x) not in (int,float) or not math.isfinite(x) or x<=0:raise ValueError('finite positive manual BPM')
    def configure(self,t,bpm,instrument,workbook,external_click,recorder):
        self._check(t,('setup','ready','cycle_complete'));self._bpm(bpm)
        if instrument is not True or workbook is not True or type(external_click) is not bool or type(recorder) is not bool:
            raise ValueError('manual prerequisites')
        if self.bpm!=bpm:self.clean_cycles=0;self.last_quarter_click=None
        self.history.append({'kind':'manual_configuration','bpm':bpm,'external_click':external_click,'recorder':recorder})
        self.bpm=bpm;self.external_click=external_click;self.recorder=recorder;self._move('ready')
    def begin(self,t,mode='full'):
        self._check(t,('ready','cycle_complete'))
        if mode not in ('full','diagnostic_two_bars') or (mode=='diagnostic_two_bars' and self.phase not in (2,3)):
            raise ValueError('diagnosis only printed5/7 full-cycle phases')
        if self.phase==6 and not self.external_click:raise ValueError('external quarter-click prerequisite')
        if self.phase==10 and not self.recorder:raise ValueError('external recording capability prerequisite')
        self.mode=mode;self.current_report=None;self.cycle+=1;self._move('perform')
    def release(self,t,released):
        self._check(t,('perform',))
        if released is not True:raise ValueError('manual release required')
        self._move('report')
    def report_diagnostic(self,t,completed,notes):
        self._check(t,('report',))
        if self.mode!='diagnostic_two_bars' or completed not in ('yes','no','uncertain') or not isinstance(notes,str):
            raise ValueError('exact diagnostic report')
        self.history.append({'kind':'two_bar_diagnosis','phase':self.phase,'cycle':self.cycle,'completed':completed,'notes':notes})
        self.last_quarter_click=None;self._move('return_to_full_required')
    def return_to_full(self,t):
        self._check(t,('return_to_full_required',));self.mode='full';self._move('ready')
    def respond(self,t,reply):
        self._check(t,('report',))
        fields=set(self.common_fields)|set(self.source_phase()['obligation_fields'])
        if self.mode!='full' or not isinstance(reply,dict) or set(reply)!=fields|{'quarter_click_exact','recording','notes'}:
            raise ValueError('exact full-scope current-phase reply')
        if any(reply[k] not in ('yes','no','uncertain') for k in fields) or not isinstance(reply['notes'],str):
            raise ValueError('manual replies required')
        if self.phase==6:
            if reply['quarter_click_exact'] not in ('yes','no','uncertain'):raise ValueError('explicit next-quarter click response')
        elif reply['quarter_click_exact'] is not None:raise ValueError('quarter-click reply belongs to odd subdivision phase')
        recorded=True
        if self.phase==10:
            rec=reply['recording']
            if not isinstance(rec,dict) or set(rec)!={'recorded','mechanism','reference_or_statement'} or rec['recorded'] not in ('yes','no','uncertain') or rec['mechanism'] not in ('external_reference','self_report'):
                raise ValueError('explicit recording self-report')
            self._text(rec['reference_or_statement']);recorded=rec['recorded']=='yes'
        elif reply['recording'] is not None:raise ValueError('recording belongs to finalphase')
        self.current_report=deepcopy(reply);self.last_quarter_click=reply['quarter_click_exact']
        self.history.append({'kind':'full_scope_report','phase':self.phase,'cycle':self.cycle,'bpm':self.bpm,'reply':deepcopy(reply)})
        if reply['no_gripping_or_breath_holding']!='yes':self._move('physical_stop')
        elif not all(reply[k]=='yes' for k in fields) or not recorded:self._move('repair_required')
        else:self.clean_cycles+=1;self._move('cycle_complete')
    def report_physical_stop(self,t,reason):
        self._check(t,('perform',));self._text(reason)
        self.history.append({'kind':'physical_stop','phase':self.phase,'cycle':self.cycle,'reason':reason})
        self.last_quarter_click=None;self._move('physical_stop')
    def resolve_physical(self,t,released,resolved):
        self._check(t,('physical_stop',))
        if released is not True or resolved!='yes':raise ValueError('explicit release/resolved self-report before retry')
        self.history.append({'kind':'physical_release_self_report','phase':self.phase,'cycle':self.cycle});self._move('ready')
    def choose_repair(self,t,error):
        self._check(t,('repair_required','repair_review'))
        if error!='uncertain' and error not in self.contract['error_repairs']:raise ValueError('exact source error or explicit uncertain')
        self.repair_selection=error
        self.history.append({'kind':'earliest_layer_selected','error':error,'phase':self.phase,'cycle':self.cycle})
        self._move('repair_review')
    def repair_done(self,t,released,performed,notes):
        self._check(t,('repair_review',))
        if released is not True or performed not in ('yes','no','uncertain') or not isinstance(notes,str):raise ValueError('manualrepair/release report')
        self.history.append({'kind':'repair_report','error':self.repair_selection,'performed':performed,'notes':notes})
        self._move('ready' if performed=='yes' else 'repair_review')
    def tempo_suggestion(self):
        if self.stage!='cycle_complete' or self.clean_cycles<3 or (self.phase==6 and self.last_quarter_click!='yes'):
            return None
        proposed=self.bpm+2
        return proposed if math.isfinite(proposed) and proposed-self.bpm==2 else None
    def acknowledge_external_increase(self,t,external_setting_ack):
        self._check(t,('cycle_complete',));suggestion=self.tempo_suggestion()
        if suggestion is None or external_setting_ack is not True:raise ValueError('qualified +2 suggestion and manual external acknowledgment required')
        self.history.append({'kind':'external_tempo_change_self_report','old':self.bpm,'new':suggestion,'host_tempo_changed':False})
        self.bpm=suggestion;self.clean_cycles=0;self.last_quarter_click=None;self._move('ready')
    def advance_phase(self,t):
        self._check(t,('cycle_complete',))
        self.history.append({'kind':'phase_manually_completed','phase':self.phase})
        if self.phase==10:self._move('complete_manual_workflow')
        else:self.phase+=1;self.clean_cycles=0;self.last_quarter_click=None;self.current_report=None;self._move('ready')
    def cancel(self,t):
        self._check(t,('setup','ready','perform','report','cycle_complete','repair_required','repair_review','physical_stop','return_to_full_required','complete_manual_workflow'))
        self.resume_stage=self.stage;self.generation+=1;self._move('cancelled')
    def reopen(self,t,released):
        self._check(t,('cancelled',))
        if released is not True:raise ValueError('manual release required')
        stage,self.resume_stage=self.resume_stage,None;self.generation+=1;self._move(stage)
    def snapshot(self):
        return deepcopy({'key':self.key,'generation':self.generation,'phase':self.phase,'cycle':self.cycle,'action':self.action,
                         'stage':self.stage,'resume_stage':self.resume_stage,'bpm':self.bpm,'mode':self.mode,
                         'clean_cycles':self.clean_cycles,'last_quarter_click':self.last_quarter_click,
                         'external_click':self.external_click,'recorder':self.recorder,'current_report':self.current_report,
                         'repair_selection':self.repair_selection,'history':self.history,'source_phase':self.source_phase(),
                         'source_complete_report':self.stage=='complete_manual_workflow','performance_observed':False,
                         'host_tempo_changed':False,'audio_supplied':False,'recording_inspected':False,
                         'Attempt_credit':False,'mastery_awarded':False,'persistence_supplied':False})
