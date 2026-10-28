"""Full private model under exact independent source Accept; original partial revision preserved."""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
_path = Path(__file__).with_name('reconstruction_contract.py')
_spec = importlib.util.spec_from_file_location('fathom_c_r63_partial_reference', _path)
_legacy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_legacy)
KEY, RAW, PASSES, BLOCKS, COMMON = _legacy.KEY, _legacy.RAW, _legacy.PASSES, _legacy.BLOCKS, _legacy.COMMON
PC, Refusal, require, fields, validate_contact = _legacy.PC, _legacy.Refusal, _legacy.require, _legacy.fields, _legacy.validate_contact
DECISION = 'Results/manager-resume-r02/private-source-bulk-review-r01/source-decisions.json'
DECISION_SHA = '80abbfbaedf4393d44fe2aac21329ca2382892263e23f69c1943037a41bad8d0'

def source_authority():
    data = (ROOT / DECISION).read_bytes()
    require(len(data) == 6619 and hashlib.sha256(data).hexdigest() == DECISION_SHA,
            'exact independent source-decision identity')
    decision = json.loads(data)
    rows = [row for row in decision['decisions'] if row['package_key'] == KEY]
    require(len(rows) == 1 and rows[0]['source_decision'] == 'Accept'
            and rows[0]['exact_source_literal'] == {'bar16': ['Gmaj7', 'F#-D-B-G', 'F#'], 'worksheet_block': '13-16'},
            'exact one-key independent source Accept, no broader approval')
    return {'path': DECISION, 'bytes': len(data), 'sha256': DECISION_SHA,
            'reviewer': decision['decision_owner_and_distinct_independent_reviewer'], 'utc': decision['utc']}

def validate_position(plan, expected_names, count=64):
    fields(plan, ('position', 'contacts', 'source_scope_ack'))
    position = plan['position']
    fields(position, ('minimum_fret', 'maximum_fret', 'rationale'))
    require(type(position['minimum_fret']) is int and type(position['maximum_fret']) is int
            and 0 <= position['minimum_fret'] <= position['maximum_fret'] <= 24
            and _legacy.nonempty(position['rationale']) and plan['source_scope_ack'] is True,
            'one explicitly chosen private fret position; whole-model scope')
    contacts = plan['contacts']
    require(type(contacts) is list and len(contacts) == count, 'exact complete64-contact chosen realization')
    for name, contact in zip(expected_names, contacts):
        validate_contact(contact)
        require(name is not None and contact['midi'] % 12 == PC[name],
                'chosen contact matches actual written response; unknown needs diagnosis')
        require(position['minimum_fret'] <= contact['fret'] <= position['maximum_fret'], 'one chosen position')

class FullModelReconstructionFlow(_legacy.ModelReconstructionFlow):
    def __init__(self, key):
        self.source_decision = source_authority()
        super().__init__(key)
        self.register = 0
        self.first_contacts = None
        self.pitch_matches = None
        self.reference_history = []
        self.response_history = []
        self.hearing_reports = {}

    def token(self):
        return (*super().token(), self.register)

    def source_player_view(self):
        view = super().source_player_view()
        view['independent_source_accept'] = deepcopy(self.source_decision)
        view['full_source_authority_supported'] = True
        return view

    def learner_view(self):
        view = super().learner_view()
        view['source_limit'] = 'Original render occlusion preserved; musical source supported by pinned independent Accept.'
        view['full_source_verified'] = False
        view['full_source_authority_supported'] = True
        view['register'] = self.register + 1
        if self.revealed:
            view['source_reference'] = deepcopy(self.source_player_view()['bars'])
            view.pop('visible_source_reference', None)
        return view

    def commit_written(self, token, response):
        super().commit_written(token, response)
        self.response_history.append({'pass': PASSES[self.pass_index], 'response': deepcopy(response)})

    def heard(self, token, declaration):
        super().heard(token, declaration)
        self.hearing_reports[PASSES[self.pass_index]] = deepcopy(declaration)

    def next_written(self, token):
        self.check(token, ('written_committed',))
        if self.pass_index < 3:
            self.pass_index += 1
            state = 'ready_written'
        else:
            state = 'choose_first_position'
        self.record('next_worksheet_pass', {'source_scope': 'Complete16-bar/64-tone source'}, state)

    def choose_first_position(self, token, plan):
        self.check(token, ('choose_first_position',))
        written = [name for row in self.responses['exact_notes']['bars'] for name in row]
        validate_position(plan, written)
        self.position = deepcopy(plan['position'])
        self.contacts = self.first_contacts = deepcopy(plan['contacts'])
        self.record('chosen_first_register_realization', {'plan': plan, 'hidden_source_compared': False}, 'sing_bar')

    def diagnose_unable(self, token, diagnosis):
        self.check(token, ('choose_first_position',))
        require(_legacy.nonempty(diagnosis), 'unresolved learner response requires diagnosis')
        self.record('unable_to_realize', {'diagnosis': diagnosis, 'answer_invented': False}, 'needs_written_retry')

    def target(self):
        require(self.contacts is not None and self.bar < 16, 'chosen whole-source realization required')
        return {'bar': self.bar + 1, 'contacts': deepcopy(self.contacts[4 * self.bar:4 * self.bar + 4]),
                'chosen_position': deepcopy(self.position), 'register': self.register + 1}

    def next_bar(self, token):
        self.check(token, ('bar_reported',))
        self.bar += 1
        state = 'sing_bar' if self.bar < 16 else ('first_register_reported' if self.register == 0 else 'both_registers_reported')
        self.record('next_bar', {'source_model_bars': 16, 'performance_verified': False}, state)

    def reveal_source(self, token):
        self.check(token, ('first_register_reported',))
        written = self.responses['exact_notes']['bars']
        comparison = [all(name is not None and PC[name] == PC[expected]
                          for name, expected in zip(actual, source[1].split('-')))
                      for actual, source in zip(written, RAW)]
        self.pitch_matches = all(comparison)
        self.revealed = True
        self.reference_history.append({'symbolic_matches': comparison, 'source_decision': deepcopy(self.source_decision)})
        self.record('post_first_register_reference_reveal', {'symbolic_pitch_matches_by_bar': comparison,
                    'degrees_functions_contour_and_performance_verified': False}, 'verification')

    def restart_written(self, token, diagnosis):
        self.check(token, ('needs_written_retry', 'verification', 'both_registers_reported'))
        require(_legacy.nonempty(diagnosis), 'explicit reconstruction diagnosis')
        self.pass_index = self.bar = self.register = 0
        self.responses = {}
        self.position = self.contacts = self.first_contacts = None
        self.pitch_matches = None
        self.score_declarations = None
        self.hearing_reports = {}
        # Reveal/history survives; this is no fresh blind-assessment claim.
        self.generation += 1
        self.record('restart_written_after_diagnosis', {'diagnosis': diagnosis, 'earlier_reveal_retained': self.revealed}, 'ready_written')

    def begin_second_register(self, token, plan):
        self.check(token, ('verification',))
        require(self.pitch_matches is True, 'wrong/unknown exact-note reconstruction needs diagnosis/retry before transfer')
        require(all(v == 'yes' for v in self.plan['source_declarations'].values())
                and set(self.hearing_reports) == set(PASSES)
                and all(r['heard_source'] == 'yes' for r in self.hearing_reports.values()),
                'negative/uncertain recording/hearing declaration needs diagnosis/reconstruction retry')
        fields(plan, ('position', 'contacts', 'source_scope_ack', 'octave_shift_semitones'))
        shift = plan['octave_shift_semitones']
        require(type(shift) is int and shift != 0 and shift % 12 == 0,
                'explicit nonzero chosen octave shift, not a source-fixed register')
        common = {name: plan[name] for name in ('position', 'contacts', 'source_scope_ack')}
        written = [name for row in self.responses['exact_notes']['bars'] for name in row]
        validate_position(common, written)
        require(all(new['midi'] - old['midi'] == shift for old, new in zip(self.first_contacts, plan['contacts'])),
                'all64 chosen second-register targets transfer by the chosen octave shift')
        self.register, self.bar = 1, 0
        self.position, self.contacts = deepcopy(plan['position']), deepcopy(plan['contacts'])
        self.record('chosen_second_register', {'plan': plan, 'source_fixed_register': False}, 'sing_bar')

    def declare_scores(self, token, scores):
        self.check(token, ('both_registers_reported',))
        fields(scores, BLOCKS)
        for values in scores.values():
            fields(values, ('hearing_accuracy', 'first_attack_fretboard_accuracy'))
            require(all(value is None or (type(value) is int and 0 <= value <= 2) for value in values.values()),
                    'printed manual0–2 score or explicit unknown, no inferred accuracy')
        self.score_declarations = deepcopy(scores)
        complete = all(v is not None for row in scores.values() for v in row.values())
        self.record('manual_score_declarations', {'scores': scores, 'printed_maximum': 16,
                    'declared_total': sum(v for row in scores.values() for v in row.values()) if complete else None,
                    'performance_verified': False, 'mastery_awarded': False}, 'both_registers_reported')

    def finish(self, token):
        self.check(token, ('both_registers_reported',))
        require(all(n is not None for name in ('contour', 'degrees') for n in self.responses[name]['bars'])
                and all(v is not None for row in self.responses['chord_function']['bars'] for v in row.values()),
                'unknown written worksheet fields require manual diagnosis/reconstruction')
        require(self.score_declarations is not None
                and all(v is not None for row in self.score_declarations.values() for v in row.values()),
                'all eight manual score declarations, unknown remains incomplete')
        self.record('manual_exercise_finish', {'registers': 2, 'bars_per_register': 16,
                    'performance_verified': False, 'mastery_awarded': False, 'official_acceptance': False,
                    'automatic_pass_threshold': None}, 'completed')

    def begin_final_bar(self, token):
        # The previous partial-source escape surface cannot skip the full model's bar order.
        self.check(token, ())

    def reveal_supported_source(self, token):
        # Exact full-source verification must use reveal_source after all16 first-register bars.
        self.check(token, ())

    def choose_partial_position(self, token, plan):
        self.check(token, ())

    def cancel(self, token):
        stable = ('setup', 'ready_written', 'writing', 'written_committed', 'choose_first_position',
                  'needs_written_retry', 'reporting_bar', 'bar_reported', 'needs_bar_retry',
                  'first_register_reported', 'verification', 'both_registers_reported', 'completed')
        self.check(token, stable + ('hearing', 'need_source_stop', 'await_release', 'sing_bar', 'ready_play_bar', 'played_bar', 'reopen_release'))
        if self.state != 'reopen_release':
            self.resume = self.state if self.state in stable else ('ready_written' if self.contacts is None else 'sing_bar')
        self.generation += 1
        self.record('cancel_external_stop_requested', {'silence_observed': False}, 'cancelled')

def contract():
    result = _legacy.contract()
    result.update({'schema_version': 'fathom-private-model-reconstruction-source-reviewed.3',
                   'independent_source_authority': source_authority(), 'visible_supported_tones': 60,
                   'source_authority_supported_tones': 64, 'complete_manual_contract': True,
                   'original_render_occlusions_preserved': _legacy.OCCLUSION,
                   'source_limits': ['Comfortable pulse/even lengths/immediate playing supply no fixed BPM, meter, onsets or durations.',
                                     'Contour/degree/function notation and degree-key basis stay manual; no invented oracle.',
                                     'Manual0–2 declarations, maximum16; no automatic pass/mastery threshold or actual observation.'],
                   'implemented_supported_scope': 'All16/64, four written passes, complete chosen64-contact first position, post-playing source reveal, second chosen octave register, all four manual score blocks, manual finish.',
                   'authored_choices': ['Four written passes follow printed column order; same external record-once source can be replayed.',
                                        'Nullable answers are retained; chosen contacts match written answers before source verification, including wrong choices.',
                                        'Uniform nonzero octave shift is one finite authored second-register option, not every valid source realization.',
                                        'Each second-register bar is sung/played/reported again as a conservative practice option; no fixed physical timing measured.',
                                        'Manual failure/uncertainty needs diagnosis/retry; current owners and physical release fence cancellation.',
                                        'All eight printed score declarations required for manual finish; scores0through16 imply no automatic acceptance threshold.',
                                        'Diagnosed written restart remains available after both registers; earlier response/source-reveal histories remain retained.'],
                   'manual_model': 'FullModelReconstructionFlow'})
    return result
