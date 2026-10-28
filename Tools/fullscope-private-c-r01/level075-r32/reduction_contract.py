"""Private finite Level75 card response model. No clock, audio, storage or grading."""
from copy import deepcopy
from dataclasses import dataclass
from uuid import uuid4

CARDS = (
    ('verseskeleton', 'Verse skeleton', ('Cmaj7', 'Am7', 'Fmaj7', 'G7')),
    ('prechorus', 'Pre-chorus', ('Am7', 'Em7', 'Fmaj7', 'G7')),
    ('chorus', 'Chorus', ('Cmaj7', 'G7', 'Am7', 'Fmaj7')),
    ('bridgea', 'Bridge A', ('Am7', 'Fmaj7', 'Cmaj7', 'G7')),
    ('bridgeb', 'Bridge B', ('Am7', 'Fmaj7', 'D7', 'G7')),
    ('soloa', 'Solo A', ('Dm7', 'G7', 'Cmaj7', 'Cmaj7')),
    ('solob', 'Solo B', ('Am7', 'D7', 'Gmaj7', 'G7')),
    ('outro', 'Outro', ('Cmaj7', 'Am7', 'Dm7', 'Cmaj7')),
)
KEYS = tuple(f'exercise-completeness-r01/level075/modulea/p003-card{i:02d}/{x[0]}'
             for i, x in enumerate(CARDS, 1))
ROLES = ('R', '3', '7', '5', 'R', '3', '7', '5')
PHASES = ('roots', 'guide_tones', 'bass_motion', 'complete_voicings')
CRITERIA = ('only_roots', 'guide_tones', 'only_lowest_structural_note_every_measure', 'complete_voicings')
INSTRUCTION = 'Play roots first, then guide tones, then complete voicings.'
FOOTER = ('Bass-motion pass: play only the lowest structural note of every measure. '
          'If the form becomes unclear, the arrangement is not yet ready for full texture.')
ANALYSIS = ('96 contacts. Reduce sections to roots, guide tones, then complete voicings. '
            'Mark dominants, repeated sections, and high-risk transitions.')
YES_NO = ('yes', 'no', 'uncertain')

class Refusal(ValueError):
    pass

def require(value, reason):
    if not value:
        raise Refusal(reason)

def fields(obj, names):
    require(type(obj) is dict and set(obj) == set(names), 'field set')

def text(value):
    return type(value) is str and bool(value.strip())

def ordinal(value, count):
    return type(value) is int and 1 <= value <= count

def validate_analysis(choice, kind):
    fields(choice, ('mode', 'values', 'notes'))
    require(choice['mode'] in ('none', 'list', 'uncertain') and text(choice['notes']), 'analysis mode/notes')
    require(type(choice['values']) is list, 'analysis values')
    if choice['mode'] != 'list':
        require(choice['values'] == [], 'non-list analysis has values')
    else:
        require(bool(choice['values']), 'empty list')
        if kind == 'dominants':
            require(all(ordinal(v, 4) for v in choice['values']), 'dominant source position')
            require(len(set(choice['values'])) == len(choice['values']), 'duplicate dominant position')
        else:
            require(all(text(v) for v in choice['values']), 'analysis reference text')

def validate_plan(plan, chord_symbols):
    fields(plan, ('prerequisites', 'chords', 'measure_pulse_plan', 'role_pattern', 'analysis'))
    fields(plan['prerequisites'], ('own_instrument', 'original_workbook'))
    require(all(v is True for v in plan['prerequisites'].values()), 'manual prerequisite unavailable')
    require(text(plan['measure_pulse_plan']), 'explicit learner measure/pulse plan')
    require(type(plan['chords']) is list and len(plan['chords']) == 4, 'four chord choices')
    for i, (choice, symbol) in enumerate(zip(plan['chords'], chord_symbols), 1):
        fields(choice, ('source_position', 'source_chord', 'root', 'guide_tones', 'voicing', 'bass'))
        require(type(choice['source_position']) is int and choice['source_position'] == i
                and choice['source_chord'] == symbol, 'source chord order')
        require(text(choice['root']) and text(choice['bass']), 'root/bass choice')
        for name in ('guide_tones', 'voicing'):
            require(type(choice[name]) is list and bool(choice[name]) and all(text(v) for v in choice[name]), 'tone choices')
    role = plan['role_pattern']
    fields(role, ('mode', 'rationale', 'mapping'))
    require(role['mode'] in ('reference_only', 'learner_realization') and text(role['rationale']), 'role policy')
    require(type(role['mapping']) is list, 'role mapping type')
    if role['mode'] == 'reference_only':
        require(role['mapping'] == [], 'reference role policy contains projection')
    else:
        require(len(role['mapping']) == 8, 'eight role choices')
        for i, (choice, literal) in enumerate(zip(role['mapping'], ROLES), 1):
            fields(choice, ('source_role_position', 'source_role', 'chosen_chord_position', 'realization'))
            require(type(choice['source_role_position']) is int and choice['source_role_position'] == i
                    and choice['source_role'] == literal, 'source role order')
            require(ordinal(choice['chosen_chord_position'], 4) and text(choice['realization']), 'learner role mapping')
    fields(plan['analysis'], ('dominants', 'repeated_sections', 'high_risk_transitions'))
    for kind, choice in plan['analysis'].items():
        validate_analysis(choice, kind)

@dataclass(frozen=True)
class Token:
    instance: str
    key: str
    generation: int
    phase: int
    cycle: int
    action: int
    stage: str

class ReductionFlow:
    """Structural manual reports only; all answers and acoustic truth are unverified."""
    def __init__(self, key):
        require(key in KEYS, 'unsupported card')
        self.key = key
        self.chords = CARDS[KEYS.index(key)][2]
        self.instance = uuid4().hex
        self.generation = self.phase = self.cycle = self.action = 0
        self.stage = 'setup'
        self.plan = None
        self.history = []
        self._resume_stage = None

    def token(self):
        return Token(self.instance, self.key, self.generation, self.phase, self.cycle, self.action, self.stage)

    def check(self, token, stages):
        require(type(token) is Token and token == self.token(), 'stale or foreign action')
        require(self.stage in stages, 'wrong stage')

    def record(self, kind, data, stage):
        self.history.append({'kind': kind, 'phase': PHASES[self.phase], 'cycle': self.cycle,
                             'generation': self.generation, 'data': deepcopy(data)})
        self.action += 1
        self.stage = stage

    def set_plan(self, token, plan):
        self.check(token, ('setup', 'ready', 'needs_plan_revision', 'needs_retry', 'pass_reported', 'completed'))
        validate_plan(plan, self.chords)
        self.plan = deepcopy(plan)
        self.generation += 1
        self.phase = self.cycle = 0
        unresolved = any(c['mode'] == 'uncertain' for c in plan['analysis'].values())
        self.record('plan', plan, 'needs_plan_revision' if unresolved else 'ready')

    def begin(self, token):
        self.check(token, ('ready',))
        require(self.plan is not None, 'missing plan')
        self.cycle += 1
        self.record('begin', {'manual_only': True}, 'performing')

    def release(self, token, released):
        self.check(token, ('performing', 'release_after_reopen'))
        require(released is True, 'explicit instrument release required')
        if self.stage == 'performing':
            self.record('release', {'self_report': True}, 'awaiting_report')
        else:
            stage = self._resume_stage
            require(stage is not None, 'missing reopen stage')
            self._resume_stage = None
            self.record('reopen_release', {'self_report': True}, stage)

    def report(self, token, response):
        self.check(token, ('awaiting_report',))
        fields(response, ('chords', 'full_scope', 'criterion', 'criterion_report', 'form_clear', 'notes'))
        require(response['criterion'] == CRITERIA[self.phase], 'wrong pass criterion')
        require(response['full_scope'] in YES_NO and response['criterion_report'] in YES_NO and text(response['notes']), 'report fields')
        require(type(response['chords']) is list and len(response['chords']) == 4, 'four chord reports')
        for i, choice in enumerate(response['chords'], 1):
            fields(choice, ('source_position', 'covered'))
            require(type(choice['source_position']) is int and choice['source_position'] == i
                    and choice['covered'] in YES_NO, 'ordered chord report')
        if self.phase == 2:
            require(response['form_clear'] in YES_NO, 'bass form clarity')
        else:
            require(response['form_clear'] is None, 'form clarity belongs to bass pass')
        ok = (response['full_scope'] == response['criterion_report'] == 'yes'
              and all(c['covered'] == 'yes' for c in response['chords'])
              and (self.phase != 2 or response['form_clear'] == 'yes'))
        self.record('report', {'response': response, 'all_required_manual_reports_yes': ok,
                               'performance_verified': False}, 'pass_reported' if ok else 'needs_retry')

    def retry(self, token, adjustment):
        self.check(token, ('needs_retry', 'pass_reported'))
        require(text(adjustment), 'manual retry note')
        self.record('retry', {'adjustment': adjustment}, 'ready')

    def advance(self, token):
        self.check(token, ('pass_reported',))
        self.record('advance', {'manual_only': True}, 'completed' if self.phase == 3 else 'ready')
        if self.phase < 3:
            self.phase += 1
            self.cycle = 0

    def cancel(self, token):
        self.check(token, ('setup', 'ready', 'performing', 'awaiting_report', 'pass_reported',
                           'needs_retry', 'needs_plan_revision', 'release_after_reopen', 'completed'))
        if self.stage != 'release_after_reopen':
            self._resume_stage = ('ready' if self.stage in ('performing', 'awaiting_report') else self.stage)
        self.generation += 1
        self.record('cancel', {'incomplete_cycle_has_no_completion': True}, 'cancelled')

    def reopen(self, token):
        self.check(token, ('cancelled',))
        self.generation += 1
        self.record('reopen', {'old_responses_retained': True}, 'release_after_reopen')

def contract(index):
    slug, label, chords = CARDS[index]
    return {
        'schema_version': 'fathom-private-harmonic-reduction-manual-contract.1',
        'label': label, 'key': KEYS[index], 'source_chords': list(chords),
        'source_role_occurrences': [{'position': i, 'group': (i - 1) // 4 + 1,
                                     'literal': role, 'kind': 'harmonic_degree',
                                     'root_not_rest': role == 'R'} for i, role in enumerate(ROLES, 1)],
        'source_instructions': [INSTRUCTION, FOOTER], 'module_txt_analysis_instruction': ANALYSIS,
        'source_scope': {'pdf_page': 3, 'card': index + 1, 'txt_module_a': 'module-wide analysis; not fixed card timing',
                         'source_event_count': 0, 'fixed_contact_count': None,
                         'role_to_chord_alignment': None, 'source_measure_timing': None},
        'extent': {'literal_header': '12 CELLS | 96 CONTACTS', 'visible_card_count': 8,
                   'official_card_keys': list(KEYS), 'status': 'PAGE_EXTENT_RECONCILIATION_REQUIRED',
                   'larger_page_extent_complete': False, 'new_children_inferred': 0},
        'ordered_manual_phases': [{'phase': name, 'criterion_field': CRITERIA[i]} for i, name in enumerate(PHASES)],
        'learner_choice_schema': {
            'prerequisites': ['own_instrument', 'original_workbook'],
            'chords': {'ordered_count': 4, 'fields': ['source_position', 'source_chord', 'root', 'guide_tones', 'voicing', 'bass']},
            'measure_pulse_plan': 'required learner text; not source timing',
            'role_pattern': {'modes': ['reference_only', 'learner_realization'], 'rationale': 'required',
                             'learner_mapping_count_if_selected': 8, 'source_alignment_claim': False},
            'analysis': {'fields': ['dominants', 'repeated_sections', 'high_risk_transitions'],
                         'modes': ['none', 'list', 'uncertain'], 'notes': 'required',
                         'dominants': 'source chord positions 1..4', 'other_values': 'learner source references/descriptions'}},
        'response_schema': {'ordered_chord_coverage': {'count': 4, 'values': list(YES_NO)},
                            'full_scope': list(YES_NO), 'criterion_report': list(YES_NO),
                            'form_clear_bass_only': list(YES_NO), 'notes': 'required'},
        'authored_interface_policy': [
            'Bass-motion check is inserted after guide tones and before full voicings to enforce printed form-clarity boundary.',
            'Manual source choice schemas and pass ordering beyond the printed roots/guides/voicings are Fathom-authored.',
            'Role reference/mapping choice never asserts unprinted source alignment or eight performed attacks.',
            'Uncertain analysis and negative/uncertain reports remain recorded and require explicit revision/retry.',
            'Completion records required self-reports, not their musical/acoustic correctness.'],
        'state_semantics': {'initial': 'setup', 'performance': 'manual begin/release/report',
                            'completion': 'completed (manual reports only)',
                            'tokens': 'instance/key/generation/phase/cycle/action/stage',
                            'cancel_reopen': 'retain source/plan/history; invalidate callbacks; explicit release; interrupted pass repeats',
                            'plan_revision': 'retain prior plan and reports; restart roots with new generation'},
        'automatic_evaluation': False, 'performance_observed': False, 'credit_awarded': False,
        'mastery_awarded': False, 'audio_supplied': False, 'persistence': False,
        'canonical_binding': None, 'fixed_playback_realization_complete': False,
    }
