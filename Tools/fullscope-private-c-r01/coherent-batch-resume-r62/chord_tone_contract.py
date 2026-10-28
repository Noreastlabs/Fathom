"""Private page14 chord-tone task; no audio, recognition, clock, persistence or credit."""
from copy import deepcopy
import importlib.util
from pathlib import Path
from uuid import uuid4

# Reuse immutable r61 schema/contact primitives, not its page13 task semantics.
_path = Path(__file__).resolve().parents[1] / 'level077-r61/degree_contract.py'
_spec = importlib.util.spec_from_file_location('fathom_c_r61_primitives', _path)
_base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_base)
Refusal, require, fields = _base.Refusal, _base.require, _base.fields
validate_contact, enums = _base.validate_contact, _base.enums
PC, TUNING = dict(_base.PC), dict(_base.TUNING)
RAW = (('Cmaj7', '3', 'E'), ('Cmaj7', '7', 'B'), ('Dm7', 'b3', 'F'),
       ('Dm7', 'b7', 'C'), ('G7', '3', 'B'), ('G7', 'b7', 'F'),
       ('Am7', 'b3', 'C'), ('Am7', 'b7', 'G'), ('Bm7b5', 'b5', 'F'),
       ('E7', '3', 'G#'), ('E7', 'b7', 'D'), ('AmMaj7', '7', 'G#'),
       ('D7#11', '#11', 'G#'), ('G#7alt', '3', 'B# / C'))
KEYS = tuple(f'exercise-completeness-r01/level077/modulef/p014-t1-r{n}/{c.lower()}'
             for n, (c, _, _) in zip((*range(1, 14), 15), RAW))
OCCLUDED_KEY = KEYS[-1]
SETS = ('string_set_1', 'string_set_2')
HEADING = 'HEAR THE ROLE, SING THE NOTE, THEN PLACE IT INSIDE THE CHORD'
PRIORITY = ('Guide-tone priority: if response time is slow, practice only thirds and sevenths '
            'until they are immediate; roots and fifths are added afterward.')
COMMON = ('chord_context_correct', 'target_placed_inside_chord', 'sung_before_playing',
          'single_silent_setup', 'no_searching', 'selected_string_set_used')
TRANSFER = ('same_chord_role', 'same_target_pitch_class', 'second_string_set_used')

def validate_plan(plan):
    fields(plan, ('prerequisites', 'cue_provider'))
    fields(plan['prerequisites'], ('original_workbook', 'own_instrument'))
    require(all(v is True for v in plan['prerequisites'].values()), 'manual prerequisites')
    cue = plan['cue_provider']
    fields(cue, ('kind', 'reference', 'ready'))
    require(cue['kind'] == 'external_human' and type(cue['reference']) is str
            and bool(cue['reference'].strip()) and cue['ready'] is True,
            'chosen external human cue delivery; no application audio supplied')

def validate_arrangements(arrangements):
    fields(arrangements, SETS)
    for choice in arrangements.values():
        fields(choice, ('strings', 'target', 'voicing'))
        strings, voicing = choice['strings'], choice['voicing']
        require(type(strings) is list and 1 <= len(strings) <= 6
                and all(type(s) is str and s in TUNING for s in strings)
                and len(set(strings)) == len(strings), 'unique chosen guitar string set')
        require(type(voicing) is list and len(voicing) == len(strings),
                'one chosen contact per selected string; no prescribed chord size')
        for contact in voicing:
            validate_contact(contact)
        validate_contact(choice['target'])
        require({c['string'] for c in voicing} == set(strings)
                and len({c['string'] for c in voicing}) == len(voicing)
                and choice['target'] in voicing, 'chosen target belongs to chosen arrangement')
    first, second = (arrangements[name] for name in SETS)
    require(set(first['strings']) != set(second['strings']), 'two distinct chosen string sets')
    require(first['target']['midi'] % 12 == second['target']['midi'] % 12,
            'transfer preserves chosen target pitch class; source answer not yet compared')

def answer_pc(index):
    # Final extraction retains B# / C literally; its source visibility is still unresolved.
    spellings = RAW[index][2].split(' / ')
    require(all(name in PC for name in spellings)
            and len({PC[name] for name in spellings}) == 1, 'source pitch spelling schema')
    return PC[spellings[0]]

class ChordToneFlow:
    def __init__(self, key):
        require(type(key) is str and key in KEYS, 'exact fourteen existing source keys')
        self.key, self.index, self.instance = key, KEYS.index(key), uuid4().hex
        self.generation = self.stage = self.cycle = self.action = 0
        self.state = 'setup'
        self.plan = self.resume = self.arrangements = self.named_pitch = self.cue_report = None
        self.history, self.response_history, self.arrangement_history = [], [], []
        self.first_reported = self.current_revealed = self.ever_revealed = False

    def token(self):
        return (self.instance, self.key, self.generation, self.stage,
                self.cycle, self.action, self.state)

    def check(self, token, states):
        require(type(token) is tuple and token == self.token(), 'current source/action owner')
        require(self.state in states, 'wrong task state')

    def record(self, kind, data, state):
        self.history.append({'kind': kind, 'generation': self.generation,
                             'stage': self.stage, 'cycle': self.cycle, 'data': deepcopy(data)})
        self.action += 1
        self.state = state

    def clear_initial(self):
        self.named_pitch = self.cue_report = self.arrangements = None
        self.first_reported = self.current_revealed = False

    def source_player_view(self):
        chord, role, pitch = RAW[self.index]
        return {'key': self.key, 'cue': {'chord': chord, 'role': role},
                'reference_pitch': pitch, 'audio_supplied': False,
                'source_visibility': 'OCCLUDED_SOURCE_UNRESOLVED' if self.key == OCCLUDED_KEY else 'VISIBLE',
                'delivery_policy': 'Chosen human speaks chord and role; pitch reference is withheld until after playing.'}

    def learner_view(self):
        result = {'key': self.key, 'state': self.state, 'chord': RAW[self.index][0],
                  'role': RAW[self.index][1], 'stage': SETS[self.stage],
                  'sung_name': self.named_pitch, 'arrangements': deepcopy(self.arrangements),
                  'previously_revealed': self.ever_revealed, 'blind_assessment_claim': False,
                  'source_visibility': 'OCCLUDED_SOURCE_UNRESOLVED' if self.key == OCCLUDED_KEY else 'VISIBLE'}
        if self.current_revealed:
            result['reference_pitch'] = RAW[self.index][2]
        return result

    def set_plan(self, token, plan):
        self.check(token, ('setup', 'completed'))
        validate_plan(plan)
        self.plan = deepcopy(plan)
        self.generation += 1
        self.stage = self.cycle = 0
        self.clear_initial()
        self.record('chosen_delivery_plan', plan, 'ready')

    def begin(self, token, confirmation=None):
        self.check(token, ('ready',))
        require(self.key != OCCLUDED_KEY, 'SOURCE_UNRESOLVED: final row occluded in original PDF rendering')
        if self.stage == 0:
            fields(confirmation, ('key', 'chord', 'role', 'ready'))
            require(confirmation == {'key': self.key, 'chord': RAW[self.index][0],
                                     'role': RAW[self.index][1], 'ready': True}
                    and confirmation['ready'] is True, 'exact current cue confirmation')
            self.clear_initial()
            state = 'hearing'
        else:
            require(confirmation is None and self.first_reported, 'first string-set report before transfer')
            state = 'silent_setup'
        self.cycle += 1
        self.record('begin', {'cue_confirmation': confirmation, 'hearing_observed': False}, state)

    def heard(self, token, report):
        self.check(token, ('hearing',))
        enums(report, ('heard_chord_and_role',))
        self.cue_report = deepcopy(report)
        self.record('manual_cue_report', report, 'singing')

    def sung_name(self, token, response):
        self.check(token, ('singing',))
        fields(response, ('pitch_name', 'singing_attempted'))
        name = response['pitch_name']
        require((name is None or (type(name) is str and name in PC))
                and response['singing_attempted'] is True, 'typed sung name or explicit unknown')
        self.named_pitch = name
        self.response_history.append(deepcopy(response))
        self.record('sung_response', {'response': response, 'hidden_answer_compared': False}, 'choose_arrangements')

    def choose_arrangements(self, token, arrangements):
        self.check(token, ('choose_arrangements',))
        validate_arrangements(arrangements)
        self.arrangements = deepcopy(arrangements)
        self.arrangement_history.append(deepcopy(arrangements))
        self.record('chosen_arrangements', {'arrangements': arrangements, 'hidden_answer_compared': False}, 'silent_setup')

    def cannot_respond(self, token, diagnosis, released):
        self.check(token, ('singing', 'choose_arrangements'))
        require(type(diagnosis) is str and bool(diagnosis.strip()) and released is True,
                'unable response requires manual release and diagnosis')
        self.record('unable_to_respond', {'diagnosis': diagnosis, 'answer_invented': False}, 'needs_retry')

    def target(self):
        require(self.arrangements is not None, 'chosen arrangements required')
        return {'string_set': SETS[self.stage], 'arrangement': deepcopy(self.arrangements[SETS[self.stage]])}

    def setup_target(self, token, ack):
        self.check(token, ('silent_setup',))
        require(ack is True, 'silent setup attempted')
        self.record('silent_setup', self.target(), 'attack')

    def attack(self, token, ack):
        self.check(token, ('attack',))
        require(ack is True, 'one manual decisive attack attempt')
        self.record('attack_attempt', {'actual_attack_count_observed': None}, 'await_release')

    def release(self, token, ack):
        self.check(token, ('await_release', 'reopen_release'))
        require(ack is True, 'manual physical release required')
        if self.state == 'reopen_release':
            state = self.resume
            require(state is not None, 'saved resume state')
            self.resume = None
            if state == 'ready' and self.stage == 0:
                self.clear_initial()
        else:
            state = 'reveal' if self.stage == 0 else 'reporting'
        self.record('manual_release', {'sound_stop_observed': False}, state)

    def reveal(self, token):
        self.check(token, ('reveal',))
        self.current_revealed = self.ever_revealed = True
        self.record('post_playing_reference_reveal', {}, 'reporting')

    def report(self, token, report):
        self.check(token, ('reporting',))
        fields(report, ('key', 'chord', 'role', 'string_set', 'target', 'named_pitch',
                        'attack_count', 'common', 'stage_duties', 'response_speed', 'diagnosis', 'notes'))
        enums(report['common'], COMMON)
        enums(report['stage_duties'], ('sung_pitch_correct',) if self.stage == 0 else TRANSFER)
        validate_contact(report['target'])
        target = self.target()
        require(report['key'] == self.key and report['chord'] == RAW[self.index][0]
                and report['role'] == RAW[self.index][1] and report['string_set'] == target['string_set']
                and report['target'] == target['arrangement']['target']
                and report['named_pitch'] == self.named_pitch, 'exact source/chosen-response binding')
        require(type(report['attack_count']) is int and report['attack_count'] >= 0
                and type(report['diagnosis']) is str and type(report['notes']) is str
                and bool(report['notes'].strip()), 'actual manual count, notes and diagnosis')
        require(type(report['response_speed']) is str
                and report['response_speed'] in ('immediate', 'slow', 'uncertain'), 'qualitative manual response speed')
        matches = {'sung_name': self.named_pitch is not None and PC[self.named_pitch] == answer_pc(self.index),
                   'chosen_pitch_class': report['target']['midi'] % 12 == answer_pc(self.index)}
        ok = (all(matches.values()) and self.cue_report['heard_chord_and_role'] == 'yes'
              and report['attack_count'] == 1
              and all(value == 'yes' for value in (*report['common'].values(), *report['stage_duties'].values())))
        if not ok:
            require(bool(report['diagnosis'].strip()), 'wrong/unknown response or negative/uncertain duty requires diagnosis')
        if ok and self.stage == 0:
            self.first_reported = True
        self.record('manual_report', {'response': report, 'symbolic_reference_matches': matches,
                                     'manual_requirements_reported': ok, 'performance_verified': False,
                                     'source_priority_guidance': PRIORITY if report['response_speed'] != 'immediate' else None,
                                     'automatic_timing_or_mastery': False}, 'reported' if ok else 'needs_retry')

    def next_set(self, token):
        self.check(token, ('reported',))
        require(self.stage == 0 and self.first_reported, 'exactly two chosen string sets')
        self.stage = 1
        self.record('transfer_to_second_string_set', {}, 'ready')

    def retry(self, token, diagnosis):
        self.check(token, ('reported', 'needs_retry'))
        require(type(diagnosis) is str and bool(diagnosis.strip()), 'retry diagnosis required')
        if self.stage == 0:
            self.clear_initial()
        self.record('retry', {'diagnosis': diagnosis}, 'ready')

    def finish(self, token):
        self.check(token, ('reported',))
        require(self.stage == 1 and self.first_reported, 'both string sets manually reported')
        self.record('finish', {'manual_only': True, 'mastery_awarded': False,
                               'performance_verified': False, 'source_acceptance': False}, 'completed')

    def cancel(self, token):
        stable = ('setup', 'ready', 'reporting', 'reported', 'needs_retry', 'completed')
        self.check(token, stable + ('hearing', 'singing', 'choose_arrangements', 'silent_setup',
                                   'attack', 'await_release', 'reveal', 'reopen_release'))
        if self.state != 'reopen_release':
            self.resume = self.state if self.state in stable else 'ready'
        self.generation += 1
        self.record('cancel', {}, 'cancelled')

    def reopen(self, token):
        self.check(token, ('cancelled',))
        self.generation += 1
        self.record('reopen', {}, 'reopen_release')

def contract(index):
    require(type(index) is int and 0 <= index < len(KEYS), 'exact source row index')
    chord, role, pitch = RAW[index]
    return {
        'schema_version': 'fathom-private-chord-tone-realization.1', 'key': KEYS[index],
        'source_fields': {'Chord': chord, 'Role': role, 'Pitch': pitch, 'Sing': '',
                          'String set 1': '', 'String set 2': ''},
        'printed_heading': HEADING, 'printed_priority': PRIORITY,
        'literal_extent_header': '14 COMMANDS | 56 TONES', 'actual_commands': 14,
        'source_visibility': 'OCCLUDED_SOURCE_UNRESOLVED' if index == 13 else 'VISIBLE',
        'source_note_events': [], 'source_absolute_contact_voicing_timing': None,
        'manual_model': 'ChordToneFlow', 'ordered_stages': ['hear chord/role', 'sing pitch name',
            'choose two arrangements', 'silent setup', 'one attack attempt', 'manual physical release',
            'explicit reference reveal', 'manual report/diagnose', 'second-set transfer', 'manual finish'],
        'plan_schema': {'cue_provider': 'chosen external human, authored manual delivery policy',
                        'arrangements': 'two distinct chosen string sets, chosen target inside each chosen voicing, same chosen pitch class'},
        'response_schema': {'pitch_name': 'chromatic spelling or null/unknown; attempt singing before choosing arrangements',
                            'common_duties': list(COMMON), 'transfer_duties': list(TRANSFER),
                            'manual_enum': ['yes', 'no', 'uncertain'], 'attack_count': 'actual nonnegative integer',
                            'response_speed': ['immediate', 'slow', 'uncertain'],
                            'failure': 'release and diagnosis; retry; never fill unknown learner answers'},
        'authored_policies': [
            'Source answer retained separately until initial playing/release and explicit reveal; wrong response remains playable beforehand.',
            'Two different chosen string sets form a private representation of the two blank source columns; no printed set membership or voicing is asserted.',
            'Contacts reuse r61 standard-tuning fret0..24 domain; chord correctness is manual, with no source-fixed voicing or automatic chord oracle.',
            'Qualitative slow/uncertain self-report returns printed priority guidance; no numeric timing, score or mastery threshold is invented.',
            'Literal56TONES does not create a four-tone sequence, extra attacks or another string-set stage.',
            'Page13 context-only/no-guitar-root/three-register commands are not imported into page14.',
            'Final official row15 key and PDF-extracted B# / C remain unchanged; practice start refuses pending occlusion adjudication.'],
        'automatic_evaluation': False, 'performance_observed': False, 'audio_supplied': False,
        'audio_inspected': False, 'timing_scheduled': False, 'credit_awarded': False,
        'mastery_awarded': False, 'persistence': False, 'canonical_binding': None}
