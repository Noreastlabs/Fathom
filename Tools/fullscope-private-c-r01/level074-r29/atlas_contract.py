"""Finite reference-review model; acknowledgments are neither practice nor grading."""
from dataclasses import dataclass
from copy import deepcopy

@dataclass(frozen=True)
class Token:
    instance: object
    key: str
    generation: int
    cycle: int
    step: int
    action: int
    stage: str

class AtlasReview:
    def __init__(self, contract):
        if contract.get('mode') != 'manual_source_reference_review' or len(contract['review_steps']) != 8:
            raise ValueError('exact reference contract required')
        self.contract=deepcopy(contract);self.instance=object();self.key=contract['package_key']
        self.generation=self.cycle=1;self.step=self.action=0;self.stage='review'
        self.resume_stage=None;self.responses=[]

    def token(self):
        return Token(self.instance,self.key,self.generation,self.cycle,self.step,self.action,self.stage)

    def _check(self,token,stages):
        if token!=self.token() or self.stage not in stages:raise ValueError('stale/foreign/wrong-stage review action')

    def _move(self,stage):self.stage=stage;self.action+=1

    def view(self):
        return deepcopy(self.contract['review_steps'][self.step])

    def respond(self,token,acknowledgments,notes):
        self._check(token,('review',));fields=self.view()['response_fields']
        if (not isinstance(acknowledgments,dict) or set(acknowledgments)!=set(fields)
                or any(v not in ('yes','no','uncertain') for v in acknowledgments.values())
                or not isinstance(notes,str)):
            raise ValueError('exact manual acknowledgment fields required')
        self.responses.append({'cycle':self.cycle,'step':self.step,'step_id':self.view()['id'],
                               'acknowledgments':deepcopy(acknowledgments),'notes':notes,
                               'performance_claim':False})
        if not all(v=='yes' for v in acknowledgments.values()):self._move('needs_review')
        elif self.step==7:self._move('complete_reference_review')
        else:self.step+=1;self._move('review')

    def review_again(self,token,reason):
        self._check(token,('needs_review','complete_reference_review'))
        if not isinstance(reason,str) or not reason.strip():raise ValueError('explicit review reason required')
        self.responses.append({'cycle':self.cycle,'step':self.step,'review_reason':reason})
        if self.stage=='complete_reference_review':self.cycle+=1;self.step=0
        self._move('review')

    def cancel(self,token):
        self._check(token,('review','needs_review','complete_reference_review'))
        self.resume_stage=self.stage;self.generation+=1;self._move('cancelled')

    def reopen(self,token):
        self._check(token,('cancelled',));stage,self.resume_stage=self.resume_stage,None
        self.generation+=1;self._move(stage)

    def snapshot(self):
        return deepcopy({'key':self.key,'generation':self.generation,'cycle':self.cycle,
                         'step':self.step,'action':self.action,'stage':self.stage,
                         'resume_stage':self.resume_stage,'responses':self.responses,'view':self.view(),
                         'reference_review_complete':self.stage=='complete_reference_review',
                         'practice_performed':False,'audio_supplied':False,'knowledge_graded':False,
                         'Attempt_credit':False,'mastery_awarded':False,'persistence_supplied':False})
