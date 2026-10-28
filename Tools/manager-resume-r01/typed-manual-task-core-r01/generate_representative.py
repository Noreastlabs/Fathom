#!/usr/bin/env python3
"""Finite build-time source adapter. No runtime JSON loading or identity allocation."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

BASE = 'manager-resume-r01/typed-manual-task-core-r01'
POL = 'Build/manager-resume-r01/level053-moduleb-realization-policy-r01/'
KEY = 'exercise-completeness-r01/level053/moduleb/p003-t1-r1-c2/cmajrp'
POLICY = POL + 'policy-proposal-r02.json'
BINDINGS = POL + 'eligible-bindings.jsonl'
REP = POL + 'representative-case-proposal-r02.json'
PACKET = 'Build/fullscope-private-b-r01/level053-r02/implementation.jsonl'
TXT = 'Notes/music/guitar project/TXT version/Guitar_Exercises_Section_VI_Level_53_Major_and_Minor_Triads_Across_Four_Adjacent_Three_String_Sets.txt'
PDF = TXT.replace('TXT version', 'PDF version').replace('.txt', '.pdf')
REVIEW = 'Results/manager-resume-r01/level053-moduleb-realization-policy-r01/independent-review-r02/final-report.md'
ADOPTION = 'Results/primary/20260927T1334Z-level053-moduleb-private-cue-policy-adoption.md'
CONTEXT = 'Build/fullscope-private-b-r01/level053-r02/source-context.json'
PINS = {
    POLICY: '5ca30eef84e88134336e01ec7ee6b23d81b531125c76a62023c0b2f8005af63b',
    BINDINGS: 'e5a959e7e4a25d4f3a234a8e61c3065f06ffffe7babcb46d1bf9c0ec8161d5d7',
    REP: 'dadfe114d8f554c30b557418620a374cc6d2c28f02ded205a5f9891e3c5790ef',
    PACKET: '2c6648fe908f62ce0096c8b2635e154be93c9547e27a1ebcd3db9ad0dc2e0c69',
    TXT: 'eeedc261db89d3421fafc116e7352bbf8a3e3f6b7eddfd822ed6e4c731e0538e',
    PDF: '5e016f98623dc4362b2e3fc9b2d1cf1fb6c8692d6312d5b30a65234d47fa20ae',
    REVIEW: 'a6640f37a2595116b0e465404e0221b016ab65c75ea743a3371f6c8e457432b8',
    ADOPTION: 'fa983245336287620e9ed8fc95ff2cdb31ceec25564df0491ec110aa723e0213',
    CONTEXT: '9a9bce017bec387abe1cacd0e93f3c7fa9c9482707c6db8d16dd41470c55ee0f',
    'Source/core/Quantity.hpp': 'af25feac7ef5ce9e58a94b19405f016f6acfbb7d6ec89feba72889e9045b9a69',
    'Source/core/Quantity.cpp': 'caa98504162f0456f69502bb114cc3aa8b68f4d1ac5ee98f655ca1830f6d7c89',
}

class Refusal(ValueError):
    def __init__(self, code, detail):
        super().__init__(code + ': ' + detail)
        self.code = code

def require(condition, code, detail):
    if not condition:
        raise Refusal(code, detail)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()

def strict_json(data):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'DUPLICATE_JSON_KEY', key)
            result[key] = value
        return result
    def bad_number(value):
        raise Refusal('NONFINITE_JSON', value)
    return json.loads(data, object_pairs_hook=pairs, parse_constant=bad_number)

def no_symlinks(path):
    for part in [path, *path.parents]:
        require(not part.is_symlink(), 'SYMLINK', str(part))

def read_pinned(root):
    raw = {}
    for name, digest in PINS.items():
        path = root / name
        no_symlinks(path)
        require(path.is_file(), 'MISSING_INPUT', name)
        require(path.stat().st_size < 3_000_000, 'INPUT_SIZE', name)
        data = path.read_bytes()
        require(sha(data) == digest, 'INPUT_HASH', name)
        raw[name] = data
    return raw

def validate(raw, key):
    require(key == KEY, 'REPRESENTATIVE_SCOPE', 'Only one exact representative is released')
    # Production callers must use read_pinned; pure validation is exposed for causal tests.
    policy, rep = strict_json(raw[POLICY]), strict_json(raw[REP])
    bindings = [strict_json(line) for line in raw[BINDINGS].splitlines()]
    records = [strict_json(line) for line in raw[PACKET].splitlines()]
    require(len(bindings) == 168 and len({b['package_key'] for b in bindings}) == 168,
            'BINDING_SCOPE', 'Require the exact unique eligibility family')
    require(len(records) == 222 and len({r['package_key'] for r in records}) == 222,
            'PACKET_SCOPE', 'Require the exact producer packet')
    candidates = [b for b in bindings if b['package_key'] == key]
    require(len(candidates) == 1, 'BINDING_SCOPE', key)
    binding = candidates[0]
    require(binding == rep['binding'] and binding['jsonl_line'] == 1,
            'REPRESENTATIVE_BINDING', 'Representative must match the complete binding')
    require(sha(canonical(binding)) == 'ba7a6d4cad7123362037e0953830f4fd33065856faa69b34c5dcfc43bdd86df5',
            'BINDING_CONTENT', 'Exact full binding required')
    record = records[0]
    require(record['package_key'] == key and sha(canonical(record)) == binding['record_canonical_sha256'],
            'RECORD_CONTENT', 'Complete original record differs')
    require(rep['policy_path'] == POLICY and rep['policy_sha256'] == PINS[POLICY],
            'POLICY_BINDING', 'Unreviewed policy')
    require(policy['eligibility']['bindings_sha256'] == PINS[BINDINGS], 'POLICY_BINDING', 'Eligibility drift')
    # These checks document the semantic boundary; exact byte pins remain authoritative.
    p = policy['authored_projection']
    require(p['onsets_q'] == [[0,1],[1,1],[2,1],[3,1]] and p['end_of_cue_sequence_q'] == [4,1],
            'CUE_COORDINATES', 'Only the reviewed four cue positions')
    require(p['acoustic_gate_q'] is None and p['sounding_note_offs'] is None
            and p['complete_sounding_playback_contract'] is False and p['source_rhythm_claim'] is False,
            'ACOUSTIC_OR_SOURCE_CLAIM', 'Visual cue policy cannot authorize sound or printed rhythm')
    require(policy['visible_selection']['default_numeric_selection'] is None
            and policy['visible_selection']['explicit_choice_required'] is True
            and policy['tempo_and_audio']['default_bpm'] is None
            and policy['manual_boundaries']['automatic_repeat'] is False
            and policy['manual_boundaries']['automatic_next_shape'] is False,
            'AUTOMATIC_SELECTION', 'No automatic clock or source transition')
    setup = policy['source_facts']['source_setup']
    require(len(setup) == 4 and 'one progression' in setup[0] and 'relax the hand fully' in setup[0],
            'SOURCE_CONTEXT', 'Full reviewed broader-session context required')
    expected = [{'string':3,'fret':5,'muted':False}, {'string':2,'fret':5,'muted':False}, {'string':1,'fret':3,'muted':False}]
    events = record['implementation']['events']
    require(len(events) == 4 and events[0]['members'] == expected and events[0]['kind'] == 'blocked_triad',
            'ACTION_GROUP', 'One simultaneous written group followed by three contacts')
    for i, event in enumerate(events):
        require(event['order'] == i+1 and event['onset_q'] is None and event['duration_q'] is None,
                'SOURCE_CLOCK', 'Source order is not a numeric clock')
        if i:
            require(event['kind'] == 'string_contact' and {k:event[k] for k in expected[0]} == expected[i-1],
                    'ACTION_ORDER', 'Low/middle/high source contact order')
    return policy, rep, binding, record

def definition(raw, key):
    policy, rep, binding, record = validate(raw, key)
    contacts = [{'source_string':m['string'], 'fret':m['fret'], 'written_standard_tuning_midi':pitch}
                for m, pitch in zip(binding['members_low_to_high'], binding['derived_standard_tuning_midi'])]
    context = [policy['source_facts']['suggested_fingering'], policy['source_facts']['page_workout_order'],
               *[t['instruction'] for t in record['implementation']['context_tasks']],
               'The workbook gives source order only. Numeric rhythm, meter, acoustic gates, pick direction, capo and performed timing are unspecified. Cue slots are not note-offs.']
    provenance = {'binding':binding, 'inputs':[{'path':p,'bytes':len(b),'sha256':sha(b)} for p,b in sorted(raw.items())],
                  'policy_source_facts':policy['source_facts'], 'policy_unknowns':policy['tempo_and_audio'],
                  'source_discrepancy':record['source_payload']['source_discrepancy'], 'runtime_admitted':False}
    return {'schema':'fathom.private.typed-manual-task.1', 'source_key':key, 'label':rep['visible_name'],
            'policy_sha256':PINS[POLICY], 'provenance':provenance,
            'setup':[*policy['source_facts']['source_setup'], rep['source_finger_guidance']],
            'context':context, 'release':policy['source_facts']['source_release'],
            'paced_explanation':policy['visible_selection']['choices'][1]['explanation'],
            'actions':[{'label':label, 'contacts':cs, 'authored_cue_onset_q':[i,1]} for i,(label,cs) in enumerate([
                ('Play the blocked triad',contacts),('Play the low note',[contacts[0]]),
                ('Play the middle note',[contacts[1]]),('Play the high note',[contacts[2]])])],
            'cue_end_q':[4,1], 'initial_mode':'unselected', 'initial_bpm':None,
            'audio_contract':None, 'runtime_admitted':False, 'official_accepted':False}

def header(d):
    quote = lambda x: json.dumps(x, ensure_ascii=False)
    lines = ['#pragma once', '// Generated trusted display/cue data; no canonical runtime identity or sound.',
             '#include "TaskContract.hpp"', 'namespace fathom::tasks::generated {']
    for name, value in [('sourceKey',d['source_key']),('label',d['label']),('policySha256',d['policy_sha256']),
                        ('provenanceJson',canonical(d['provenance']).decode()),('releaseInstruction',d['release']),
                        ('pacedExplanation',d['paced_explanation'])]:
        lines.append('inline constexpr const char* ' + name + ' = ' + quote(value) + ';')
    for name in ['setup','context']:
        lines.append('inline std::vector<std::string> ' + name + '() { return {' + ','.join(map(quote,d[name])) + '}; }')
    lines.append('inline std::vector<Action> actions() { return {')
    for a in d['actions']:
        contacts = ','.join('{'+','.join(str(c[k]) for k in ['source_string','fret','written_standard_tuning_midi'])+'}' for c in a['contacts'])
        lines.append('{'+quote(a['label'])+', {'+contacts+'}, Rational{'+','.join(map(str,a['authored_cue_onset_q']))+'}},')
    lines.extend(['}; }', '} // namespace fathom::tasks::generated', ''])
    return '\n'.join(lines).encode()

def write_exclusive(path, data):
    with path.open('xb') as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    require(path.read_bytes() == data, 'OUTPUT_READBACK', str(path))

def generate(root, output, key=KEY):
    root = Path(root).absolute()
    no_symlinks(root)
    git = subprocess.check_output(['git','-C',str(root),'rev-parse','--show-toplevel'], text=True).strip()
    require(Path(git) == root, 'ROOT_SCOPE', 'Must use the Git root')
    output = Path(output)
    if not output.is_absolute():
        output = root / output
    no_symlinks(output)
    allowed = root / 'Build' / BASE
    require(output == output.resolve() and output.is_relative_to(allowed) and output != allowed,
            'OUTPUT_SCOPE', 'Fresh private build subdirectory required')
    require(not output.exists(), 'OUTPUT_EXISTS', str(output))
    raw = read_pinned(root)
    d = definition(raw, key)
    payload = {'GeneratedRepresentative.hpp':header(d), 'task-definition.json':canonical(d)+b'\n'}
    code = []
    for name in ['generate_representative.py','TaskContract.hpp','TaskContract.cpp']:
        path = root / 'Tools' / BASE / name
        no_symlinks(path)
        data = path.read_bytes()
        code.append({'path':path.relative_to(root).as_posix(),'bytes':len(data),'sha256':sha(data)})
    manifest = {'schema':'fathom.private.generated-task-bundle.1','runtime_admitted':False,
                'source_key':key,'inputs':d['provenance']['inputs'],'generator_and_core':code,
                'payloads':[{'path':name,'bytes':len(data),'sha256':sha(data)} for name,data in sorted(payload.items())]}
    # Validate first, publish last. Failed output is retained for diagnosis, never reusable.
    output.mkdir(parents=True)
    for name, data in payload.items():
        write_exclusive(output/name, data)
    staged = output/'manifest.pending'
    write_exclusive(staged, canonical(manifest)+b'\n')
    os.link(staged, output/'manifest.json')
    staged.unlink()
    return manifest

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--source-key', default=KEY)
    args = parser.parse_args()
    try:
        m = generate(args.root,args.output,args.source_key)
        print(json.dumps({'result':'generated_private_not_admitted','payload_count':len(m['payloads']),'source_key':KEY}))
    except (Refusal, OSError, ValueError, KeyError) as exc:
        raise SystemExit(str(exc))
