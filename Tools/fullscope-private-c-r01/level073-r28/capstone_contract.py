"""Private manual three-pass source contract, with no playback or graded outcome."""
from dataclasses import dataclass
from copy import deepcopy

@dataclass(frozen=True)
class Token:
    instance: object
    route: str
    generation: int
    cycle: int
    pass_number: int
    action: int
    stage: str

class CapstoneSession:
    block_fields = ('current_tonic', 'shared_pivot', 'next_dominant',
                    'new_tonic', 'destination_announced_on_pivot_beat4')

    def __init__(self, contract):
        if not contract.get('complete_manual_contract'):
            raise ValueError('incomplete contract')
        self.contract = deepcopy(contract)
        self.instance = object()
        self.route = contract['package_key']
        self.generation = self.cycle = self.pass_number = 1
        self.action = 0
        self.stage = 'setup'
        self.resume_stage = self.timing_choice = self.phrase_choice = self.current_report = None
        self.completed_passes = {}
        self.history = []

    def token(self):
        return Token(self.instance, self.route, self.generation, self.cycle,
                     self.pass_number, self.action, self.stage)

    def _check(self, token, stages):
        if token != self.token() or self.stage not in stages:
            raise ValueError('invalid current instance/route/pass/action/stage')

    def _move(self, stage):
        self.stage = stage
        self.action += 1

    @staticmethod
    def _text(x):
        if not isinstance(x, str) or not x.strip():
            raise ValueError('nonempty learner choice/reason required')

    def configure(self, token, own_instrument, timing_plan):
        self._check(token, ('setup', 'ready', 'choose_phrase'))
        if own_instrument is not True:
            raise ValueError('own instrument prerequisite')
        self._text(timing_plan)
        if self.timing_choice is not None:
            self.history.append({'kind': 'prior_timing_choice', 'value': self.timing_choice})
        self.timing_choice = timing_plan
        self._move('choose_phrase' if self.pass_number == 3 and self.phrase_choice is None else 'ready')

    def choose_phrase(self, token, description_or_reference):
        self._check(token, ('setup', 'ready', 'choose_phrase'))
        self._text(description_or_reference)
        if self.phrase_choice is not None:
            self.history.append({'kind': 'prior_phrase_choice', 'value': self.phrase_choice})
        self.phrase_choice = description_or_reference
        self._move('setup' if self.timing_choice is None else 'ready')

    def begin(self, token):
        self._check(token, ('ready',))
        if self.timing_choice is None or (self.pass_number == 3 and self.phrase_choice is None):
            raise ValueError('current pass choice required')
        self._move('perform')

    def release(self, token, instrument_released):
        self._check(token, ('perform',))
        if instrument_released is not True:
            raise ValueError('manual release required')
        self._move('report')

    def respond(self, token, response):
        self._check(token, ('report',))
        if not isinstance(response, dict) or set(response) != {'performed_pass_form', 'sixteen_bar_schedule', 'blocks', 'reflection'}:
            raise ValueError('exact pass response required')
        flags = [response['performed_pass_form'], response['sixteen_bar_schedule']]
        blocks = response['blocks']
        if not isinstance(blocks, list) or len(blocks) != 4:
            raise ValueError('all four block reports required')
        for i, block in enumerate(blocks, 1):
            if (not isinstance(block, dict) or set(block) != {'block'} | set(self.block_fields)
                    or type(block['block']) is not int or block['block'] != i):
                raise ValueError('exact source block order1..4 required')
            flags.extend(block[k] for k in self.block_fields)
        if any(v not in ('yes', 'no', 'uncertain') for v in flags) or not isinstance(response['reflection'], str):
            raise ValueError('explicit manual replies required')
        self.current_report = deepcopy(response)
        self.history.append({'kind': 'manual_pass_report', 'cycle': self.cycle, 'pass': self.pass_number,
                             'timing_choice': self.timing_choice, 'phrase_choice': self.phrase_choice,
                             'response': deepcopy(response)})
        if not all(x == 'yes' for x in flags):
            self._move('retry_required')
        else:
            self.completed_passes[self.pass_number] = deepcopy(response)
            if self.pass_number == 3:
                self._move('complete_manual_reports')
            else:
                self.pass_number += 1
                self.current_report = None
                self._move('choose_phrase' if self.pass_number == 3 and self.phrase_choice is None else 'ready')

    def request_retry(self, token, reason):
        self._check(token, ('retry_required',))
        self._text(reason)
        self.history.append({'kind': 'retry', 'cycle': self.cycle, 'pass': self.pass_number, 'reason': reason})
        self._move('retry_release')

    def retry_release(self, token, instrument_released):
        self._check(token, ('retry_release',))
        if instrument_released is not True:
            raise ValueError('manual release required')
        self.current_report = None
        self._move('ready')

    def repeat_cycle(self, token, reason):
        self._check(token, ('complete_manual_reports',))
        self._text(reason)
        self.history.append({'kind': 'repeat_cycle', 'cycle': self.cycle, 'reason': reason})
        self._move('repeat_release')

    def repeat_release(self, token, instrument_released):
        self._check(token, ('repeat_release',))
        if instrument_released is not True:
            raise ValueError('manual release required')
        self.cycle += 1
        self.pass_number = 1
        self.completed_passes = {}
        self.current_report = None
        self._move('ready')

    def cancel(self, token):
        self._check(token, ('setup','ready','choose_phrase','perform','report','retry_required',
                            'retry_release','complete_manual_reports','repeat_release'))
        self.resume_stage = self.stage
        self.generation += 1
        self._move('cancelled')

    def reopen(self, token, instrument_released):
        self._check(token, ('cancelled',))
        if instrument_released is not True:
            raise ValueError('manual release required')
        stage, self.resume_stage = self.resume_stage, None
        self.generation += 1
        self._move(stage)

    def snapshot(self):
        return deepcopy({'route':self.route,'stage':self.stage,'generation':self.generation,'cycle':self.cycle,
                         'pass':self.pass_number,'action':self.action,'resume_stage':self.resume_stage,
                         'timing_choice':self.timing_choice,'phrase_choice':self.phrase_choice,
                         'current_report':self.current_report,'completed_passes':self.completed_passes,
                         'history':self.history,'source_script':self.contract['source_script'],
                         'manual_reports_complete':self.stage == 'complete_manual_reports',
                         'performance_observed':False,'audio_supplied':False,'automatic_evaluation':False,
                         'Attempt_credit':False,'mastery_awarded':False,'persistence_supplied':False})
