"""Finite source-order bridge/tonic repeat/manual repair. No playback or credit."""
from copy import deepcopy
from dataclasses import dataclass

@dataclass(frozen=True)
class Token:
    instance: object
    route: str
    generation: int
    loop: int
    revision: int
    stage: str

class BridgeSession:
    def __init__(self, contract):
        self.c=deepcopy(contract); self.instance=object()
        self.generation=1; self.loop=1; self.revision=0; self.stage='setup'
        self.context=None; self.reports=[]; self.summary=None; self.repair=None
        self.history=[]; self.cancelled=False

    def token(self):
        return Token(self.instance,self.c['package_key'],self.generation,self.loop,self.revision,self.stage)

    def guard(self,token,stages):
        if self.cancelled or type(token) is not Token or token!=self.token() or self.stage not in stages:
            raise ValueError('exact current instance/route/generation/loop/action required')

    def move(self,stage):
        self.stage=stage; self.revision+=1

    @staticmethod
    def text(v):
        if type(v) is not str or not v.strip(): raise ValueError('learner text required')

    @staticmethod
    def report(v):
        if type(v) is not str or v not in ('yes','no','uncertain'): raise ValueError('yes/no/uncertain report required')

    def setup(self,token,own_instrument,pulse,articulation):
        self.guard(token,('setup',))
        if own_instrument is not True: raise ValueError('own instrument required; app supplies no sound')
        self.text(pulse);self.text(articulation)
        self.context={'pulse_self_report':pulse,'articulation_self_report':articulation,'own_instrument_self_report':True}
        self.move('ready')

    def begin(self,token):
        self.guard(token,('ready',));self.move('segment')

    def current(self):
        if self.cancelled or self.stage!='segment': return None
        segment=deepcopy(self.c['segments'][len(self.reports)])
        source={e['source_order']:e for e in self.c['printed_contacts']}
        segment['contacts']=[deepcopy(source[n]) for n in segment['source_orders']]
        return segment

    def report_segment(self,token,segment_number,complete_arpeggio,explanation):
        self.guard(token,('segment',))
        current=self.current()
        if type(segment_number) is not int or segment_number!=current['segment_number']:
            raise ValueError('complete each displayed arpeggio and the tonic repeat in order')
        self.report(complete_arpeggio);self.text(explanation)
        self.reports.append({'segment_number':segment_number,'source_orders':current['source_orders'],
                             'complete_arpeggio_self_report':complete_arpeggio,'explanation_self_report':explanation,
                             'performance_observed':False})
        self.move('summary' if len(self.reports)==4 else 'segment')

    def report_bridge(self,token,connected_bridge,destination_dominant_heard,explanation):
        self.guard(token,('summary',));self.report(connected_bridge);self.report(destination_dominant_heard);self.text(explanation)
        self.summary={'connected_bridge_self_report':connected_bridge,'destination_dominant_heard_self_report':destination_dominant_heard,
                      'explanation_self_report':explanation,'performance_observed':False}
        self.move('release')

    def release(self,token,released):
        self.guard(token,('release',))
        if released is not True: raise ValueError('manual release required before choice, repair or retry')
        self.history.append({'kind':'released_bridge','loop':self.loop,'reports':deepcopy(self.reports),'summary':deepcopy(self.summary),
                             'manual_release_self_report':True})
        if self.summary['connected_bridge_self_report']!='yes' or self.summary['destination_dominant_heard_self_report']!='yes':
            self.move('repair_required')
        elif any(r['complete_arpeggio_self_report']!='yes' for r in self.reports): self.move('retry_required')
        else: self.move('choice')

    def choose(self,token,choice):
        self.guard(token,('choice',))
        if choice not in ('loop','finish') or type(choice) is not str: raise ValueError('explicit loop or finish choice')
        self.history.append({'kind':'learner_choice','loop':self.loop,'choice':choice})
        if choice=='finish': self.move('complete_manual_reports')
        else:
            self.loop+=1;self.generation+=1;self.reports=[];self.summary=None;self.repair=None;self.move('ready')

    def request_retry(self,token,reason):
        self.guard(token,('segment','summary','release','retry_required','choice','complete_manual_reports'))
        # A diagnosed lack of connection must use the printed repair, even before release.
        if self.summary and (self.summary['connected_bridge_self_report']!='yes' or self.summary['destination_dominant_heard_self_report']!='yes'):
            raise ValueError('release and complete source repair before replay')
        self.text(reason)
        self.history.append({'kind':'retry_requested','loop':self.loop,'reason':reason,'reports':deepcopy(self.reports),'summary':deepcopy(self.summary)})
        self.move('retry_release')

    def retry_release(self,token,released):
        self.guard(token,('retry_release',))
        if released is not True: raise ValueError('manual release before retry')
        self.history.append({'kind':'retry_release','manual_release_self_report':True})
        self.generation+=1;self.reports=[];self.summary=None;self.move('ready')

    def choose_repair(self,token,source_order,relation_and_hold_plan):
        self.guard(token,('repair_required',))
        if type(source_order) is not int or source_order not in [c['source_order'] for c in self.c['repair_candidates']]:
            raise ValueError('choose an existing common/guide-tone source contact')
        self.text(relation_and_hold_plan)
        self.repair={'chosen_source_order':source_order,'relation_and_hold_plan_self_report':relation_and_hold_plan}
        self.move('repair_report')

    def report_repair(self,token,sustained_chosen_tone,heard_destination_dominant,explanation):
        self.guard(token,('repair_report',));self.report(sustained_chosen_tone);self.report(heard_destination_dominant);self.text(explanation)
        self.repair.update({'sustained_chosen_tone_self_report':sustained_chosen_tone,
                            'heard_destination_dominant_self_report':heard_destination_dominant,
                            'explanation_self_report':explanation,'performance_observed':False})
        self.move('repair_release')

    def release_repair(self,token,released):
        self.guard(token,('repair_release',))
        if released is not True: raise ValueError('manual release before replay')
        self.history.append({'kind':'released_repair','repair':deepcopy(self.repair),'manual_release_self_report':True})
        if self.repair['sustained_chosen_tone_self_report']=='yes' and self.repair['heard_destination_dominant_self_report']=='yes':
            self.generation+=1;self.reports=[];self.summary=None;self.move('ready')
        else: self.move('repair_required')

    def cancel(self,token):
        self.guard(token,('setup','ready','segment','summary','release','choice','retry_required','retry_release',
                          'repair_required','repair_report','repair_release','complete_manual_reports'))
        self.history.append({'kind':'cancel','instruction':'Stop/release your own instrument; no app sound is playing.'})
        self.cancelled=True;self.generation+=1;self.revision+=1

    def reopen(self,token,released):
        if not self.cancelled or type(token) is not Token or token!=self.token():raise ValueError('current cancelled instance token required')
        if released is not True:raise ValueError('manual release before reopening')
        self.cancelled=False;self.generation+=1;self.revision+=1
        self.history.append({'kind':'reopen','manual_release_self_report':True})

    def snapshot(self):
        return deepcopy({'route':self.c['package_key'],'loop':self.loop,'stage':self.stage,'context':self.context,
                         'reports':self.reports,'summary':self.summary,'repair':self.repair,'history':self.history,'cancelled':self.cancelled,
                         'manual_task_reports_complete':not self.cancelled and self.stage=='complete_manual_reports',
                         'performance_observed':False,'app_audio_supplied':False,'Attempt_credit':False,'mastery_awarded':False,'persistence_supplied':False})
