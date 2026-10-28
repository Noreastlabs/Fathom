"""Private five-pass manual model. Relative source data does not run an audio clock."""
from dataclasses import dataclass
from copy import deepcopy
import math

@dataclass(frozen=True)
class Token:
    instance: object
    key: str
    generation: int
    cycle: int
    pass_number: int
    action: int
    stage: str

class RhythmCapstone:
    choice_fields=('register_fret_voice_plan','muted_voice_plan','later_section_accent_plan','closing_cmaj7_voicing')
    report_fields=('pass_form','group3_section','group5_section','displacement_section','distinct_3_to_2_voices',
                   'pre_entry_three_cue','five_cue_bar3_beat4','shift_cue_bar8_beat4','three_over_two_cue_bar12_beat4',
                   'no_pause_or_extra_countin','whole_note_cmaj7_close','stopped_after_close')

    def __init__(self,contract):
        if not contract.get('complete_manual_contract'):raise ValueError('incomplete contract')
        self.contract=deepcopy(contract);self.instance=object();self.key=contract['package_key']
        self.generation=self.cycle=self.pass_number=1;self.action=0;self.stage='setup'
        self.choice=self.current_report=self.resume_stage=None;self.completed_passes={};self.history=[]

    def token(self):return Token(self.instance,self.key,self.generation,self.cycle,self.pass_number,self.action,self.stage)
    def _check(self,t,stages):
        if t!=self.token() or self.stage not in stages:raise ValueError('invalid current token/stage')
    def _move(self,stage):self.stage=stage;self.action+=1
    @staticmethod
    def _text(v):
        if not isinstance(v,str) or not v.strip():raise ValueError('explicit nonempty choice/reason required')

    def configure(self,t,choice):
        self._check(t,('setup','ready'))
        if not isinstance(choice,dict) or set(choice)!=set(self.choice_fields)|{'own_instrument','tempo_bpm'}:
            raise ValueError('exact choice schema required')
        if choice['own_instrument'] is not True:raise ValueError('own instrument required')
        bpm=choice['tempo_bpm']
        if type(bpm) not in (int,float) or not math.isfinite(bpm) or bpm<=0:raise ValueError('finite positive learner tempo')
        for k in self.choice_fields:self._text(choice[k])
        if self.choice is not None:self.history.append({'kind':'prior_choice','value':deepcopy(self.choice)})
        self.choice=deepcopy(choice);self._move('ready')

    def begin(self,t):self._check(t,('ready',));self._move('perform')
    def release(self,t,released):
        self._check(t,('perform',))
        if released is not True:raise ValueError('manual instrument release required')
        self._move('report')

    def respond(self,t,reply):
        self._check(t,('report',))
        flags=list(self.report_fields)+(['added_chord_changes'] if self.pass_number>=4 else [])
        if not isinstance(reply,dict) or set(reply)!=set(flags)|{'close_timing','recording','notes'}:
            raise ValueError('exact current-pass report required')
        if any(reply[k] not in ('yes','no','uncertain') for k in flags):raise ValueError('manual replies required')
        if reply['close_timing'] not in ('on_time','early','late','uncertain') or not isinstance(reply['notes'],str):
            raise ValueError('close timing/manual notes schema')
        recorded=True
        if self.pass_number==5:
            rec=reply['recording']
            if not isinstance(rec,dict) or set(rec)!= {'recorded','mechanism','reference_or_statement'}:
                raise ValueError('recording response required')
            if rec['recorded'] not in ('yes','no','uncertain') or rec['mechanism'] not in ('external_artifact_reference','self_report'):
                raise ValueError('explicit recording origin required')
            self._text(rec['reference_or_statement']);recorded=rec['recorded']=='yes'
        elif reply['recording'] is not None:raise ValueError('recording response belongs to pass5')
        self.current_report=deepcopy(reply)
        self.history.append({'kind':'pass_report','cycle':self.cycle,'pass':self.pass_number,
                             'choice':deepcopy(self.choice),'reply':deepcopy(reply),'recording_inspected':False})
        if reply['close_timing']!='on_time':self._move('isolate_bars13_16')
        elif not all(reply[k]=='yes' for k in flags) or not recorded:self._move('retry_required')
        else:
            self.completed_passes[self.pass_number]=deepcopy(reply)
            if self.pass_number==5:self._move('complete_manual_reports')
            else:self.pass_number+=1;self.current_report=None;self._move('ready')

    def report_isolation(self,t,released,performed,notes):
        self._check(t,('isolate_bars13_16',))
        if released is not True or performed not in ('yes','no','uncertain') or not isinstance(notes,str):
            raise ValueError('isolated13–16 performance/release response required')
        self.history.append({'kind':'isolation_report','cycle':self.cycle,'pass':self.pass_number,
                             'bars':[13,14,15,16],'performed':performed,'notes':notes})
        self._move('retry_required' if performed=='yes' else 'isolate_bars13_16')

    def request_retry(self,t,reason):
        self._check(t,('retry_required',));self._text(reason)
        self.history.append({'kind':'retry','cycle':self.cycle,'pass':self.pass_number,'reason':reason})
        self._move('retry_release')
    def retry_release(self,t,released):
        self._check(t,('retry_release',))
        if released is not True:raise ValueError('manual release required')
        self.current_report=None;self._move('ready')
    def repeat_cycle(self,t,reason):
        self._check(t,('complete_manual_reports',));self._text(reason)
        self.history.append({'kind':'repeat_cycle','cycle':self.cycle,'reason':reason});self._move('repeat_release')
    def repeat_release(self,t,released):
        self._check(t,('repeat_release',))
        if released is not True:raise ValueError('manual release required')
        self.cycle+=1;self.pass_number=1;self.current_report=None;self.completed_passes={};self._move('ready')
    def cancel(self,t):
        self._check(t,('setup','ready','perform','report','isolate_bars13_16','retry_required','retry_release','complete_manual_reports','repeat_release'))
        self.resume_stage=self.stage;self.generation+=1;self._move('cancelled')
    def reopen(self,t,released):
        self._check(t,('cancelled',))
        if released is not True:raise ValueError('manual release required')
        stage,self.resume_stage=self.resume_stage,None;self.generation+=1;self._move(stage)
    def snapshot(self):
        return deepcopy({'key':self.key,'generation':self.generation,'cycle':self.cycle,'pass':self.pass_number,
                         'action':self.action,'stage':self.stage,'resume_stage':self.resume_stage,'choice':self.choice,
                         'current_report':self.current_report,'completed_passes':self.completed_passes,'history':self.history,
                         'source_script':self.contract['source_script'],
                         'manual_reports_complete':self.stage=='complete_manual_reports','performance_observed':False,
                         'audio_supplied':False,'recording_inspected':False,'automatic_evaluation':False,
                         'Attempt_credit':False,'mastery_awarded':False,'persistence_supplied':False})
