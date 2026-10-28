"""Private supported rehearsal; full ModuleH completion refuses original-source occlusion."""
from copy import deepcopy
import importlib.util
from pathlib import Path
from uuid import uuid4

_path = Path(__file__).resolve().parents[1] / 'level077-r61/degree_contract.py'
_spec = importlib.util.spec_from_file_location('fathom_c_r61_reconstruction_primitives', _path)
_base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_base)
Refusal, require, fields, enums = _base.Refusal, _base.require, _base.fields, _base.enums
PC, TUNING, validate_contact = dict(_base.PC), dict(_base.TUNING), _base.validate_contact
KEY = 'exercise-completeness-r01/level077/moduleh/p017-u001/modulehsixteenbareartohandmodelreconstruction'
RAW = (('Cmaj7', 'E-G-B-C', 'E'), ('Am7', 'C-E-G-A', 'C'), ('Dm7', 'F-A-C-D', 'F'),
       ('G7', 'B-F-D-G', 'B'), ('Cmaj7', 'B-G-E-C', 'B'), ('E7', 'G#-B-D-E', 'G#'),
       ('Am7', 'C-E-G-A', 'C'), ('A7', 'C#-E-G-A', 'C#'), ('Dm7', 'F-A-C-D', 'F'),
       ('G7', 'B-D-F-G', 'B'), ('Cmaj7', 'E-G-B-C', 'E'), ('D7', 'F#-A-C-D', 'F#'),
       ('Gmaj7', 'B-D-F#-G', 'B'), ('Am7', 'C-E-G-A', 'C'), ('D7', 'F#-C-A-D', 'F#'),
       ('Gmaj7', 'F#-D-B-G', 'F#'))
PASSES = ('contour', 'degrees', 'exact_notes', 'chord_function')
BLOCKS = ('1-4', '5-8', '9-12', '13-16')
COMMON = ('sung_once', 'played_immediately', 'one_chosen_position', 'no_searching',
          'note_lengths_even', 'comfortable_pulse', 'normal_beat_one_accent')
OCCLUSION = 'SOURCE_UNRESOLVED: page17 finalbar16 and page18 final13–16 worksheet block covered by original footer panels'
PULSE = 'Perform at one comfortable pulse. Keep note lengths even and avoid emphasizing the first pitch beyond the normal beat-one accent.'
REALIZATION = 'After the exact notes are written, sing each four-note bar once and play it immediately in one chosen position. Then repeat the complete 16-bar source in a second register.'
SCORING = 'Score each block 0-2 for hearing accuracy and 0-2 for first-attack fretboard accuracy. Maximum = 16.'

def nonempty(value):
    return type(value) is str and bool(value.strip())

def validate_source_plan(plan):
    fields(plan, ('prerequisites', 'recording', 'source_declarations'))
    fields(plan['prerequisites'], ('original_workbook', 'own_instrument'))
    require(all(value is True for value in plan['prerequisites'].values()), 'manual prerequisites')
    recording = plan['recording']
    fields(recording, ('kind', 'reference', 'declared_sha256', 'ready'))
    digest = recording['declared_sha256']
    require(recording['kind'] == 'external_recording' and nonempty(recording['reference'])
            and recording['ready'] is True
            and (digest is None or (type(digest) is str and len(digest) == 64
                                   and all(c in '0123456789abcdef' for c in digest))),
            'actual external recording reference; declared hash or explicit unknown')
    enums(plan['source_declarations'], ('recorded_once', 'transcriber_did_not_study_source_card'))

def validate_written(pass_name, response):
    fields(response, ('bars', 'notes'))
    require(type(response['bars']) is list and len(response['bars']) == 16
            and nonempty(response['notes']), 'sixteen exact bar slots and manual notes')
    for bar in response['bars']:
        if pass_name in ('contour', 'degrees'):
            require(bar is None or nonempty(bar), 'manual contour/degree text or unknown')
        elif pass_name == 'exact_notes':
            require(type(bar) is list and len(bar) == 4
                    and all(n is None or (type(n) is str and n in PC) for n in bar),
                    'four typed pitch names or unknowns per bar')
        else:
            fields(bar, ('chord', 'function'))
            require(all(v is None or nonempty(v) for v in bar.values()), 'manual chord/function text or unknown')

class ModelReconstructionFlow:
    def __init__(self, key):
        require(type(key) is str and key == KEY, 'exact one existing source child')
        self.key, self.instance = key, uuid4().hex
        self.generation = self.action = self.pass_index = self.bar = 0
        self.state = 'setup'
        self.plan = self.position = self.contacts = self.resume = None
        self.responses, self.history = {}, []
        self.revealed = False
        self.score_declarations = None

    def token(self):
        return (self.instance, self.key, self.generation, self.action,
                self.pass_index, self.bar, self.state)

    def check(self, token, states):
        require(type(token) is tuple and token == self.token(), 'current exact source/action owner')
        require(self.state in states, 'wrong reconstruction state')

    def record(self, kind, data, state):
        self.history.append({'kind': kind, 'pass': self.pass_index, 'bar': self.bar + 1,
                             'generation': self.generation, 'data': deepcopy(data)})
        self.action += 1
        self.state = state

    def source_player_view(self):
        return {'key': self.key, 'source_card_only': True,
                'bars': [{'bar': i + 1, 'chord': c, 'pitches': p.split('-'), 'structural_target': t,
                          'visibility': 'VISIBLE' if i < 15 else 'EXTRACTED_BUT_OCCLUDED_SOURCE_UNRESOLVED'}
                         for i, (c, p, t) in enumerate(RAW)],
                'record_once_instruction': 'RECORD ONCE; TRANSCRIBER SHOULD NOT STUDY THIS PAGE BEFORE THE TEST',
                'pulse_instruction': PULSE, 'source_audio_supplied': False, 'source_audio_validated': False}

    def learner_view(self):
        view = {'key': self.key, 'state': self.state, 'written_pass': PASSES[self.pass_index],
                'bar': self.bar + 1, 'responses': deepcopy(self.responses),
                'chosen_position': deepcopy(self.position), 'chosen_contacts': deepcopy(self.contacts),
                'source_limit': OCCLUSION, 'full_source_verified': False, 'blind_assessment_claim': False}
        if self.revealed:
            view['visible_source_reference'] = deepcopy(self.source_player_view()['bars'][:15])
        return view

    def set_source(self, token, plan):
        self.check(token, ('setup',))
        validate_source_plan(plan)
        self.plan = deepcopy(plan)
        self.generation += 1
        self.record('chosen_external_recording', {'plan': plan, 'recording_inspected': False}, 'ready_written')

    def begin_written(self, token, confirmation):
        self.check(token, ('ready_written',))
        fields(confirmation, ('key', 'pass', 'recording_reference', 'ready'))
        require(confirmation == {'key': self.key, 'pass': PASSES[self.pass_index],
                                 'recording_reference': self.plan['recording']['reference'], 'ready': True}
                and confirmation['ready'] is True, 'current pass and same external recording confirmation')
        self.record('hear_recording_for_written_pass', {'confirmation': confirmation, 'sound_observed': False}, 'hearing')

    def heard(self, token, declaration):
        self.check(token, ('hearing',))
        enums(declaration, ('heard_source',))
        self.record('manual_hearing', declaration, 'need_source_stop')

    def request_stop(self, token):
        self.check(token, ('need_source_stop',))
        self.record('external_stop_requested', {'observed_silence': False}, 'await_release')

    def release(self, token, declaration):
        self.check(token, ('await_release', 'played_bar', 'reopen_release'))
        fields(declaration, ('learner_released', 'external_source_stopped'))
        require(declaration['learner_released'] is True and declaration['external_source_stopped'] is True,
                'manual learner and external-source release, not observed silence')
        state = 'writing' if self.state == 'await_release' else 'reporting_bar'
        if self.state == 'reopen_release':
            state = self.resume
            require(state is not None, 'saved resume state')
            self.resume = None
        self.record('manual_release', {'declaration': declaration, 'silence_verified': False}, state)

    def commit_written(self, token, response):
        self.check(token, ('writing',))
        name = PASSES[self.pass_index]
        validate_written(name, response)
        self.responses[name] = deepcopy(response)
        self.record('written_response', {'pass': name, 'response': response, 'source_answer_compared': False}, 'written_committed')

    def next_written(self, token):
        self.check(token, ('written_committed',))
        if self.pass_index < 3:
            self.pass_index += 1
            state = 'ready_written'
        else:
            state = 'choose_partial_position'
        self.record('next_worksheet_pass', {'play_scope': 'Supported15-bar rehearsal; whole16-bar source remains unresolved'}, state)

    def choose_partial_position(self, token, plan):
        self.check(token, ('choose_partial_position',))
        fields(plan, ('position', 'contacts', 'partial_scope_ack'))
        position = plan['position']
        fields(position, ('minimum_fret', 'maximum_fret', 'rationale'))
        require(type(position['minimum_fret']) is int and type(position['maximum_fret']) is int
                and 0 <= position['minimum_fret'] <= position['maximum_fret'] <= 24
                and nonempty(position['rationale']) and plan['partial_scope_ack'] is True,
                'one explicitly chosen private fret position, partial scope acknowledged')
        contacts = plan['contacts']
        require(type(contacts) is list and len(contacts) == 60, 'exactly60 chosen contacts for visible15bars, no hidden finalbar fill')
        written = [n for row in self.responses['exact_notes']['bars'][:15] for n in row]
        for note, contact in zip(written, contacts):
            validate_contact(contact)
            require(note is not None and contact['midi'] % 12 == PC[note],
                    'chosen contact matches actual written response; unknown needs diagnosis')
            require(position['minimum_fret'] <= contact['fret'] <= position['maximum_fret'], 'within one chosen position')
        self.position, self.contacts = deepcopy(position), deepcopy(contacts)
        self.record('chosen_partial_realization', {'plan': plan, 'hidden_source_compared': False}, 'sing_bar')

    def diagnose_unable(self, token, diagnosis):
        self.check(token, ('choose_partial_position',))
        require(nonempty(diagnosis), 'unresolved learner response requires explicit diagnosis')
        self.record('unable_to_realize', {'diagnosis': diagnosis, 'answer_invented': False}, 'needs_written_retry')

    def target(self):
        require(self.contacts is not None and self.bar < 15, OCCLUSION)
        return {'bar': self.bar + 1, 'contacts': deepcopy(self.contacts[4 * self.bar:4 * self.bar + 4]),
                'chosen_position': deepcopy(self.position)}

    def sung_bar(self, token, ack):
        self.check(token, ('sing_bar',))
        require(ack is True, 'attempt singing current four-note bar once')
        self.record('sing_current_bar', {'bar': self.bar + 1, 'singing_observed': False}, 'ready_play_bar')

    def play_bar(self, token, ack):
        self.check(token, ('ready_play_bar',))
        require(ack is True, 'attempt immediate ordered four-contact realization')
        self.record('play_current_bar', {'targets': self.target(), 'attacks_observed': False}, 'played_bar')

    def report_bar(self, token, report):
        self.check(token, ('reporting_bar',))
        fields(report, ('key', 'bar', 'contacts', 'sing_count', 'attack_counts', 'common', 'diagnosis', 'notes'))
        target = self.target()
        require(type(report['contacts']) is list and len(report['contacts']) == 4, 'four typed reported contacts')
        for contact in report['contacts']:
            validate_contact(contact)
        require(report['key'] == self.key and type(report['bar']) is int
                and report['bar'] == target['bar'] and report['contacts'] == target['contacts'], 'exact current bar/response/contact binding')
        enums(report['common'], COMMON)
        counts = report['attack_counts']
        require(type(counts) is list and len(counts) == 4
                and all(type(n) is int and n >= 0 for n in counts)
                and type(report['sing_count']) is int and report['sing_count'] >= 0
                and type(report['diagnosis']) is str and nonempty(report['notes']), 'actual manual counts/notes')
        ok = report['sing_count'] == 1 and counts == [1, 1, 1, 1] and all(v == 'yes' for v in report['common'].values())
        if not ok:
            require(nonempty(report['diagnosis']), 'manual failure/uncertainty requires diagnosis')
        self.record('manual_bar_report', {'report': report, 'manual_requirements_reported': ok,
                                         'pitch_source_compared': False, 'performance_verified': False}, 'bar_reported' if ok else 'needs_bar_retry')

    def next_bar(self, token):
        self.check(token, ('bar_reported',))
        self.bar += 1
        self.record('next_bar', {'whole_source_complete': False}, 'sing_bar' if self.bar < 15 else 'source_review_pending')

    def retry_bar(self, token, diagnosis):
        self.check(token, ('needs_bar_retry', 'bar_reported'))
        require(nonempty(diagnosis), 'explicit same-bar diagnosis')
        self.record('repeat_current_bar', {'diagnosis': diagnosis}, 'sing_bar')

    def reveal_supported_source(self, token):
        self.check(token, ('source_review_pending',))
        self.revealed = True
        written = self.responses['exact_notes']['bars'][:15]
        comparison = [all(n is not None and PC[n] == PC[expected] for n, expected in zip(actual, source[1].split('-')))
                      for actual, source in zip(written, RAW[:15])]
        self.record('explicit_supported_reference_reveal', {'symbolic_pitch_matches_by_bar': comparison,
                    'degrees_functions_contour_and_performance_verified': False, 'unverified_final_bar_compared': False}, 'source_review_pending')

    def declare_scores(self, token, scores):
        self.check(token, ('source_review_pending',))
        fields(scores, BLOCKS)
        for block, values in scores.items():
            fields(values, ('hearing_accuracy', 'first_attack_fretboard_accuracy'))
            require(all(v is None or (type(v) is int and 0 <= v <= 2) for v in values.values()), 'printed manual0–2 score or unknown')
            if block == '13-16':
                require(all(v is None for v in values.values()), 'incomplete final block stays unknown, no whole-model score')
        self.score_declarations = deepcopy(scores)
        self.record('manual_score_declarations', {'scores': scores, 'printed_maximum': 16,
                    'full_score': None, 'performance_verified': False, 'mastery_awarded': False}, 'source_review_pending')

    def begin_final_bar(self, token):
        self.check(token, ('source_review_pending',))
        require(False, OCCLUSION)

    def begin_second_register(self, token):
        self.check(token, ('source_review_pending',))
        require(False, OCCLUSION + '; complete16-bar first realization required before whole-source register transfer')

    def finish(self, token):
        self.check(token, ('source_review_pending',))
        require(False, OCCLUSION + '; no whole exercise completion/credit')

    def cancel(self, token):
        stable = ('setup', 'ready_written', 'writing', 'written_committed', 'choose_partial_position',
                  'needs_written_retry', 'reporting_bar', 'bar_reported', 'needs_bar_retry', 'source_review_pending')
        self.check(token, stable + ('hearing', 'need_source_stop', 'await_release', 'sing_bar', 'ready_play_bar', 'played_bar', 'reopen_release'))
        if self.state != 'reopen_release':
            self.resume = self.state if self.state in stable else ('ready_written' if self.pass_index < 3 or not self.contacts else 'sing_bar')
        self.generation += 1
        self.record('cancel_external_stop_requested', {'silence_observed': False}, 'cancelled')

    def reopen(self, token):
        self.check(token, ('cancelled',))
        self.generation += 1
        self.record('reopen', {}, 'reopen_release')

def contract():
    return {'schema_version': 'fathom-private-model-reconstruction-partial.1', 'key': KEY,
            'source_bars': [{'bar': i + 1, 'chord': c, 'pitches': p.split('-'), 'structural_target': t,
                             'visibility': 'VISIBLE' if i < 15 else 'EXTRACTED_BUT_OCCLUDED'}
                            for i, (c, p, t) in enumerate(RAW)],
            'printed_tones': 64, 'actual_extracted_tones': 64, 'visible_supported_tones': 60,
            'written_passes': list(PASSES), 'fifth_pass': 'Play: sing each bar once, one chosen position, then complete second register',
            'worksheet_blocks': list(BLOCKS), 'last_block_visibility': 'EXTRACTED_BUT_OCCLUDED',
            'printed_pulse': PULSE, 'printed_realization': REALIZATION, 'printed_scoring': SCORING,
            'source_note_events': [], 'source_fixed_bpm_meter_onset_duration_register_contacts': None,
            'source_limits': [OCCLUSION, 'Contour/degree/function notation and degree-key basis are not assigned an automatic oracle.',
                              'No numeric immediate-response tolerance or full-pass/mastery threshold is printed here.'],
            'implemented_supported_scope': 'Four typed16-bar written passes, unknowns/wrong responses retained;60-contact15-bar partial manual realization; post-playing15-bar reference comparison; source-debt fences.',
            'authored_choices': ['Replay one externally recorded source for four written passes; record-once does not assert one hearing only.',
                                 'Typed nullable responses and chosen standard-tuning fret0..24 contacts/position are private representation choices.',
                                 'Partial rehearsal preserves the whole existing child identity; it is not a substitute15-bar exercise.',
                                 'Source comparison withheld until the15 visible bars are played; no pre-correction of wrong written notes.',
                                 'Full final-bar/second-register/finish and final-block score remain refused/unknown pending independent source adjudication.'],
            'manual_model': 'ModelReconstructionFlow', 'automatic_evaluation': False,
            'performance_observed': False, 'audio_supplied': False, 'audio_inspected': False,
            'timing_scheduled': False, 'credit_awarded': False, 'mastery_awarded': False,
            'persistence': False, 'canonical_binding': None, 'complete_manual_contract': False}
