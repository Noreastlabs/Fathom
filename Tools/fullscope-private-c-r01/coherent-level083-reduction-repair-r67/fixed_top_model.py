"""41 exact Level83 fixed-top tasks. Private manual declarations, no sound/clock/credit."""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import re
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[3]
LANE = Path('fullscope-private-c-r01/coherent-level083-fixed-top-r65')
PRIMITIVE = 'Tools/fullscope-private-c-r01/level077-r61/degree_contract.py'
PRIMITIVE_SHA = '147a170f0adefb093ea90b2f518c0e11a69ec3cb241ede55fa450e44479e9141'
DATA = str(Path('Build') / LANE / 'source-cards.json')
DATA_SHA = '0cd6ca0f7fc86508fae0555881a8ed3565b12171d867dc665118823d8d6e3779'
assert hashlib.sha256((ROOT / PRIMITIVE).read_bytes()).hexdigest() == PRIMITIVE_SHA
_spec = importlib.util.spec_from_file_location('fathom_r65_contact_primitives', ROOT / PRIMITIVE)
_p = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_p)
PC, TUNING, Refusal = _p.PC, _p.TUNING, _p.Refusal
require, fields, text, validate_contact = _p.require, _p.fields, _p.text, _p.validate_contact
STAGES = ('melody', 'root_melody', 'shell_melody', 'full_voicing')
QUALITIES = {'maj7': (0, 4, 7, 11), 'm7': (0, 3, 7, 10), '7': (0, 4, 7, 10), 'm7b5': (0, 3, 6, 10)}
QUALITY_ROLES = {'maj7': ('root', '3', '5', '7'), 'm7': ('root', 'b3', '5', 'b7'),
                 '7': ('root', '3', '5', 'b7'), 'm7b5': ('root', 'b3', 'b5', 'b7')}
YN = ('yes', 'no', 'uncertain')
AB_AUDIT = ('smoothest_bass', 'strongest_cadence', 'key_center_change', 'rejected_candidate_and_why')
C_AUDIT = ('fixed_top_relationships', 'bass_and_inner_motion', 'additional_substitute_reason')


def chord(symbol):
    require(type(symbol) is str, 'literal chord symbol')
    match = re.fullmatch(r'([A-G][#b]?)(maj7|m7b5|m7|7)', symbol)
    require(match is not None and match[1] in PC, 'finite authored seventh-chord spelling vocabulary')
    root, quality = match.groups()
    return [(PC[root] + n) % 12 for n in QUALITIES[quality]], QUALITY_ROLES[quality]


def cards():
    data = (ROOT / DATA).read_bytes()
    require(len(data) == 17364 and hashlib.sha256(data).hexdigest() == DATA_SHA, 'exact41 original-derived source-card pin')
    rows = json.loads(data)
    require(len(rows) == 41 and len({r['package_key'] for r in rows}) == 41, 'exact41 source keys')
    for row in rows:
        require(row['literal_top'] in PC and row['module'] in ('AB', 'C'), 'literal top/module')
        require(len(row['source_harmonies']) == (1 if row['module'] == 'AB' else 3), 'whole original harmony sequence')
        for i, symbol in enumerate(row['source_harmonies']):
            pcs, roles = chord(symbol)
            require(PC[row['literal_top']] in pcs, 'source fixed top belongs to stated harmony')
            if row['module'] == 'C':
                require(row['literal_roles'][i] == roles[pcs.index(PC[row['literal_top']])], 'exact printed changing role')
    return rows


def contract(key):
    rows = cards()
    row = next((r for r in rows if r['package_key'] == key), None)
    require(row is not None, 'exact reserved existing key')
    candidates = [r['source_harmonies'][0] for r in rows if r['module'] == 'AB' and r['literal_top'] == row['literal_top']]
    return {'schema_version': 'fathom-private-fixed-top-contract.1', 'source_card': deepcopy(row),
            'source_sibling_candidates': candidates, 'stages': STAGES,
            'instruction': 'Sing the melody before forming each voicing; keep literal top fixed. Name its role before each chord. If melody disappears, reduce to bass+melody.',
            'module_C': 'All three source harmonies/roles in order, bass/inner motion manually audited, then one explicit additional chosen substitute.' if row['module'] == 'C' else None,
            'audit_questions': C_AUDIT if row['module'] == 'C' else AB_AUDIT,
            'authored_realization_limits': ['Standard tuning/frets0–24 are chosen interface options, not source contacts.',
                'A single chosen sounding top MIDI stays fixed; source spelling retained separately; different string contact at same sounding pitch is permitted.',
                'Root+melody uses lower root plus fixed top; shell+melody uses chosen third+seventh below top; full voicing uses four distinct seventh-chord pitch classes with melody highest.',
                'The three-note rootless shell and four-note full voicing are finite authored options, not every possible source realization.',
                'ModuleC practices all four texture passes for each source harmony and chosen additional substitute; no attack timing schedule is asserted.',
                'Additional substitute chosen from source page2 candidate vocabulary for this top, outside the original three; not a new official identity.',
                'Smallest available bass/inner motion remains a manual declaration; this model makes no global fingering-optimality or audible-performance claim.'],
            'source_limits': ['No fixed source BPM/meter/onsets/durations/register/fingering/picking.',
                'Hold/repeat attack counts are manual declarations, not observed or source-fixed.',
                'Role pitch-class arithmetic is symbolic; actual singing/hearing/pulse/voice leading are not measured.',
                'Workbook14/16 on two days and no-zero mastery gate is retained outside this41-row task; no automatic acceptance/credit.'],
            'manual_model': 'FixedTopFlow', 'complete_manual_contract': True}


class FixedTopFlow:
    def __init__(self, key):
        self.contract = contract(key)
        self.key = key
        self.card = self.contract['source_card']
        self.instance = uuid4().hex
        self.action = self.generation = self.harmony_index = self.stage_index = 0
        self.state = 'setup'
        self.top = self.plan = self.role_response = self.resume = self.retry_target = None
        self.recovery = False
        self.reduction_required = False
        self.restart_after_reduction = False
        self.harmonies = list(self.card['source_harmonies'])
        self.history, self.response_history, self.realization_history, self.audit_history = [], [], [], []
        self.audit_answers = None

    def token(self):
        return (self.instance, self.key, self.generation, self.action, self.harmony_index, self.stage_index, self.recovery, self.state)

    def check(self, token, states):
        require(type(token) is tuple and token == self.token(), 'current instance/key/generation/action/harmony/texture owner')
        require(self.state in states, 'wrong fixed-top state')

    def record(self, kind, data, state):
        self.history.append({'kind': kind, 'generation': self.generation, 'harmony': self.harmony_index,
                             'stage': self.stage_index, 'recovery': self.recovery, 'data': deepcopy(data)})
        self.action += 1
        self.state = state

    def current(self):
        return {'key': self.key, 'literal_top': self.card['literal_top'],
                'harmony': self.harmonies[self.harmony_index],
                'stage': 'bass_melody_reduction' if self.recovery else STAGES[self.stage_index]}

    def expected_role(self):
        pcs, roles = chord(self.harmonies[self.harmony_index])
        return roles[pcs.index(PC[self.card['literal_top']])]

    def learner_view(self):
        return dict(self.current(), state=self.state, chosen_top=deepcopy(self.top),
                    chosen_plan=deepcopy(self.plan), literal_source_roles=deepcopy(self.card['literal_roles']),
                    source_harmonies=list(self.card['source_harmonies']), authored_harmonies=list(self.harmonies[len(self.card['source_harmonies']):]),
                    source_sibling_candidates=list(self.contract['source_sibling_candidates']),
                    source_clocks=None, actual_performance_verified=False, mastery_awarded=False)

    def set_top(self, token, choice):
        self.check(token, ('setup',))
        fields(choice, ('key', 'literal_top', 'contact', 'original_workbook', 'own_instrument'))
        require(choice['key'] == self.key and choice['literal_top'] == self.card['literal_top']
                and choice['original_workbook'] is True and choice['own_instrument'] is True, 'exact source/prerequisite declaration')
        validate_contact(choice['contact'])
        require(choice['contact']['midi'] % 12 == PC[self.card['literal_top']], 'chosen sounding top matches literal source')
        self.top = deepcopy(choice['contact'])
        self.record('chosen_fixed_sounding_top', choice, 'need_sing')

    def restart_top(self, token, choice):
        self.check(token, ('needs_retry', 'needs_reduction', 'audit', 'ready_finish'))
        fields(choice, ('key', 'literal_top', 'contact', 'original_workbook', 'own_instrument', 'diagnosis'))
        require(choice['key'] == self.key and choice['literal_top'] == self.card['literal_top']
                and choice['original_workbook'] is True and choice['own_instrument'] is True
                and text(choice['diagnosis']), 'explicit full same-key re-realization diagnosis')
        validate_contact(choice['contact'])
        require(choice['contact']['midi'] % 12 == PC[self.card['literal_top']], 'replacement sounding top still matches source spelling')
        self.top = deepcopy(choice['contact'])
        # A pending source obligation belongs to the interrupted harmony, even
        # when the learner must choose a higher register to realize the reduction.
        if self.reduction_required:
            self.recovery = True
            self.restart_after_reduction = True
        else:
            self.harmonies = list(self.card['source_harmonies'])
            self.harmony_index = self.stage_index = 0
            self.recovery = False
            self.restart_after_reduction = False
        self.plan = self.role_response = self.audit_answers = None
        self.generation += 1
        self.record('full_same_key_chosen_register_restart', {'choice': choice, 'prior_histories_retained': True,
                    'fresh_assessment_claim': False}, 'need_sing')

    def sing_top(self, token, declaration):
        self.check(token, ('need_sing',))
        fields(declaration, ('sung_before_voicing', 'notes'))
        require(declaration['sung_before_voicing'] in YN and text(declaration['notes']), 'manual sung-before-voicing declaration')
        self.response_history.append({'current': self.current(), 'singing': deepcopy(declaration)})
        self.retry_target = 'need_sing'
        self.record('manual_sing_fixed_top', declaration, 'choose_voicing' if declaration['sung_before_voicing'] == 'yes' else 'needs_retry')

    def validate_voicing(self, plan):
        fields(plan, ('key', 'harmony', 'stage', 'contacts', 'rationale'))
        require(all(plan[n] == self.current()[n] for n in ('key', 'harmony', 'stage')) and text(plan['rationale']), 'exact current source/texture and chosen realization rationale')
        contacts = plan['contacts']
        require(type(contacts) is list and len(contacts) in (1, 2, 3, 4), 'finite chosen texture contacts')
        for contact in contacts:
            validate_contact(contact)
        require(len({c['string'] for c in contacts}) == len(contacts), 'distinct strings for simultaneous chosen voicing')
        top = max(contacts, key=lambda c: c['midi'])
        require(top['midi'] == self.top['midi'] and sum(c['midi'] == top['midi'] for c in contacts) == 1, 'literal top unchanged and highest sounding voice')
        pcs, _ = chord(plan['harmony'])
        stage = plan['stage']
        target = [PC[self.card['literal_top']]] if stage == 'melody' else (
            [pcs[0], PC[self.card['literal_top']]] if stage in ('root_melody', 'bass_melody_reduction') else
            [pcs[1], pcs[3], PC[self.card['literal_top']]] if stage == 'shell_melody' else pcs)
        require(sorted(c['midi'] % 12 for c in contacts) == sorted(target), 'chosen texture matches current chord/root/shell/full pitch classes')
        if stage in ('root_melody', 'bass_melody_reduction'):
            require(min(contacts, key=lambda c: c['midi'])['midi'] % 12 == pcs[0], 'root below the unchanged top')

    def choose_voicing(self, token, plan):
        self.check(token, ('choose_voicing',))
        self.validate_voicing(plan)
        self.plan = deepcopy(plan)
        self.realization_history.append({'current': self.current(), 'plan': deepcopy(plan)})
        self.record('chosen_voicing_after_singing', {'plan': plan, 'source_fixed_contacts': False}, 'need_role')

    def cannot_realize(self, token, diagnosis):
        self.check(token, ('choose_voicing',))
        require(text(diagnosis), 'explicit unresolved chosen realization diagnosis')
        self.retry_target = 'need_sing'
        self.record('unable_to_realize_without_invention', {'diagnosis': diagnosis}, 'needs_retry')

    def name_role(self, token, response):
        self.check(token, ('need_role',))
        fields(response, ('role', 'notes'))
        require((response['role'] is None or text(response['role'])) and text(response['notes']), 'typed literal role response or retained unknown')
        self.role_response = deepcopy(response)
        self.response_history.append({'current': self.current(), 'role': deepcopy(response)})
        self.record('manual_role_named_before_chord', response, 'ready_play')

    def play(self, token, ready):
        self.check(token, ('ready_play',))
        require(ready is True, 'explicit manual external play request')
        self.record('external_chosen_voicing_play_requested', {'plan': self.plan, 'observed_attack_counts': None}, 'await_release')

    def release(self, token, declaration):
        self.check(token, ('await_release', 'reopen_release'))
        fields(declaration, ('learner_released',))
        require(declaration['learner_released'] is True, 'physical learner release required; no clock/silence inference')
        state = 'report' if self.state == 'await_release' else self.resume
        self.record('manual_physical_release', declaration, state)

    def duties(self):
        common = ('fixed_top_preserved', 'melody_clear', 'no_melody_change_for_easier_grip', 'role_named_before_chord')
        return common + (('smallest_available_bass_inner_motion',) if self.card['module'] == 'C' else ())

    def report(self, token, report):
        self.check(token, ('report',))
        fields(report, ('key', 'harmony', 'stage', 'contacts', 'attack_counts', 'duties', 'diagnosis', 'notes'))
        require(all(report[n] == self.current()[n] for n in ('key', 'harmony', 'stage'))
                and report['contacts'] == self.plan['contacts'] and text(report['notes']), 'current exact chosen realization report')
        counts = report['attack_counts']
        require(type(counts) is list and len(counts) == len(self.plan['contacts'])
                and all(v is None or (type(v) is int and v >= 0) for v in counts), 'manual hold/repeat counts or explicit unknown; source schedule unasserted')
        fields(report['duties'], self.duties())
        require(all(type(v) is str and v in YN for v in report['duties'].values()) and type(report['diagnosis']) is str, 'manual source duties/diagnosis')
        good = all(v is not None and v > 0 for v in counts) and all(v == 'yes' for v in report['duties'].values()) and self.role_response['role'] == self.expected_role()
        require(good or text(report['diagnosis']), 'failed/unknown declaration or role needs diagnosis')
        self.retry_target = 'need_sing'
        state = 'stage_reported' if good else ('needs_reduction' if report['duties']['melody_clear'] == 'no' and not self.recovery else 'needs_retry')
        if report['duties']['melody_clear'] == 'no':
            self.reduction_required = True
        self.response_history.append({'current': self.current(), 'report': deepcopy(report)})
        self.record('manual_voicing_report', {'report': report, 'symbolic_reference_role': self.expected_role(),
                    'symbolic_role_matches': self.role_response['role'] == self.expected_role(), 'performance_verified': False}, state)

    def advance(self, token):
        self.check(token, ('stage_reported',))
        if self.recovery:
            # Only a positive reported bass+melody reduction discharges debt.
            self.reduction_required = False
            self.recovery = False
            if self.restart_after_reduction:
                self.harmonies = list(self.card['source_harmonies'])
                self.harmony_index = self.stage_index = 0
                self.restart_after_reduction = False
            state = 'need_sing'
        elif self.stage_index < 3:
            self.stage_index += 1
            state = 'need_sing'
        elif self.harmony_index + 1 < len(self.harmonies):
            self.harmony_index += 1
            self.stage_index = 0
            state = 'need_sing'
        elif self.card['module'] == 'C' and len(self.harmonies) == 3:
            state = 'need_additional'
        else:
            state = 'audit'
        self.plan = self.role_response = None
        self.record('explicit_next_texture_or_harmony', {'source_harmonies_unchanged': True}, state)

    def choose_additional(self, token, choice):
        self.check(token, ('need_additional',))
        fields(choice, ('key', 'harmony', 'rationale'))
        require(choice['key'] == self.key and choice['harmony'] in self.contract['source_sibling_candidates']
                and choice['harmony'] not in self.card['source_harmonies'] and text(choice['rationale']), 'one explicit additional authored substitute for the same fixed top')
        self.harmonies.append(choice['harmony'])
        self.harmony_index += 1
        self.stage_index = 0
        self.record('additional_chosen_substitute', {'choice': choice, 'new_official_identity': False}, 'need_sing')

    def audit(self, token, audit):
        self.check(token, ('audit',))
        fields(audit, ('answers', 'notes', 'diagnosis'))
        fields(audit['answers'], C_AUDIT if self.card['module'] == 'C' else AB_AUDIT)
        require(all(v is None or text(v) for v in audit['answers'].values()) and text(audit['notes'])
                and type(audit['diagnosis']) is str, 'literal manual source-choice audit or retained unknown')
        complete = all(v is not None for v in audit['answers'].values())
        require(complete or text(audit['diagnosis']), 'unknown choice audit needs explicit diagnosis')
        self.audit_answers = deepcopy(audit)
        self.audit_history.append(deepcopy(audit))
        self.retry_target = 'audit'
        self.record('manual_choice_audit', {'audit': audit, 'audible_harmonic_judgment_verified': False}, 'ready_finish' if complete else 'needs_retry')

    def diagnose(self, token, diagnosis):
        self.check(token, ('needs_retry', 'needs_reduction'))
        require(text(diagnosis), 'explicit same-step manual recovery diagnosis')
        if self.reduction_required:
            self.recovery = True
        self.plan = self.role_response = None
        self.generation += 1
        self.record('diagnosed_same_step_recovery', {'diagnosis': diagnosis, 'prior_histories_retained': True}, self.retry_target)

    def finish(self, token):
        self.check(token, ('ready_finish',))
        require(not self.reduction_required, 'source immediate bass+melody reduction still pending')
        self.record('private_manual_task_finish', {'whole_workbook_complete': False, 'performance_verified': False,
                    'mastery_awarded': False, 'learner_credit': False, 'official_acceptance': False,
                    'source_two_day14of16_gate_satisfied': False}, 'completed')

    def cancel(self, token):
        states = ('setup', 'need_sing', 'choose_voicing', 'need_role', 'ready_play', 'await_release', 'report',
                  'stage_reported', 'needs_retry', 'needs_reduction', 'need_additional', 'audit', 'ready_finish', 'completed', 'reopen_release')
        self.check(token, states)
        if self.state != 'reopen_release':
            self.resume = 'need_sing' if self.state in ('need_role', 'ready_play', 'await_release') else self.state
        self.generation += 1
        self.record('external_stop_requested', {'silence_or_release_verified': False}, 'cancelled')

    def reopen(self, token):
        self.check(token, ('cancelled',))
        self.record('reopen_requires_release', {'histories_retained': True}, 'reopen_release')
