#!/usr/bin/env python3
"""Bounded build-time family compiler. No runtime loader or admission changes."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import time

BASE = 'Tools/manager-resume-r01/typed-manual-task-core-r01/generate_representative.py'
MODEL = 'Tools/fullscope-private-b-r01/coherent-level053-moduleb-r04/triad_task_model.py'
ORACLE = 'Build/manager-resume-r02/private-coherent-bulk-review-r02/level053-original-oracle.json'
FROZEN = 'Build/fullscope-private-b-r01/coherent-level053-moduleb-r04/implementation-overlay.jsonl'
PILOT = 'manager-resume-r02/level053-family-compiler-pilot-r01'


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode()


def sha(value):
    return hashlib.sha256(value).hexdigest()


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def identity(root, path):
    data = (root / path).read_bytes()
    return {'path': path, 'bytes': len(data), 'sha256': sha(data)}


def quote(value):
    return json.dumps(value, ensure_ascii=False)


def compile_family(root, config_path, output):
    started = time.perf_counter()
    root, output = Path(root).absolute(), Path(output).absolute()
    checkout = subprocess.run(['git', '-C', str(root), 'rev-parse', '--show-toplevel'],
                              capture_output=True, text=True, check=False)
    if (checkout.returncode or root.resolve() != root or
            Path(checkout.stdout.strip()) != root):
        raise ValueError('ROOT_SCOPE: Exact canonical checkout Git root required')
    base = load(root / BASE, 'pilot_original_generator')
    config = base.strict_json(Path(config_path).read_bytes())
    base.require(config['schema'] == 'fathom.private.family-compiler-pilot.1' and
                 config['expected_rows'] == 167 and config['expected_behavior_classes'] == 24,
                 'PILOT_CONFIG', 'Exact bounded pilot required')
    pins = {pin['path']: pin for pin in config['pins']}
    mandatory = {BASE, MODEL, ORACLE, FROZEN,
                 'Results/manager-resume-r02/private-coherent-bulk-review-r02/final-decisions.json',
                 'Results/manager-resume-r02/private-source-bulk-review-r01/final-decisions.json',
                 'Content/runtime/typed-manual-tasks-v1/manifest.json',
                 'Content/runtime/typed-manual-tasks-v1/level053-moduleb-cmajrp/task-definition.json',
                 'Source/core/Quantity.hpp', 'Source/core/Quantity.cpp',
                 *('Source/tasks/' + name for name in ['TaskContract.hpp', 'TaskContract.cpp',
                   'ManualTaskAdapter.hpp', 'ManualTaskAdapter.cpp', 'GeneratedRepresentative.hpp',
                   'InstalledManualTaskRegistry.cpp'])}
    base.require(set(pins) == mandatory and len(config['pins']) == len(pins),
                 'INPUT_CLOSURE', 'Complete unique approved input closure required')
    for path, digest in [(MODEL, '6b9d34fa5211040527ab240fb139147bf8623ff7aeba9fd05273814830aa59ef'),
                         (ORACLE, '3489b5a2cf03181a6deb1fcf97f2adfc5e0b0b03017ca3398f08e4eaf43a51a1'),
                         (FROZEN, '448db87c0b1a7f8f95c8f5579edce6e946653dcd2e3c0c2c468c58b776fa1a00')]:
        base.require(pins[path]['sha256'] == digest, 'REVIEWED_FAMILY', path)
    for pin in pins.values():
        base.no_symlinks(root / pin['path'])
        base.require(identity(root, pin['path']) == pin, 'INPUT_DRIFT', pin['path'])
    base.require(output.resolve() == output and output.is_relative_to(root / 'Build' / PILOT)
                 and not output.exists(), 'OUTPUT_SCOPE', 'Fresh private pilot output only')
    base.no_symlinks(output)
    # The original one-key generator remains intact and is a regression oracle.
    raw = base.read_pinned(root)
    representative = base.definition(raw, base.KEY)
    installed = (root / 'Content/runtime/typed-manual-tasks-v1/level053-moduleb-cmajrp/task-definition.json').read_bytes()
    base.require(base.canonical(representative) + b'\n' == installed,
                 'REPRESENTATIVE_PARITY', 'Installed representative definition must be byte-identical')
    model = load(root / MODEL, 'pilot_frozen_family')
    family = model.Family(root)
    frozen = {r['package_key']: r['implementation']['manual_execution_contract']
              for r in map(base.strict_json, (root / FROZEN).read_bytes().splitlines())}
    oracle = {r['package_key']: r for r in base.strict_json((root / ORACLE).read_bytes())}
    accepted = base.strict_json((root / 'Results/manager-resume-r02/private-coherent-bulk-review-r02/final-decisions.json').read_bytes())
    accepted_keys = set(next(d['package_keys'] for d in accepted['decisions']
                             if d['family'] == 'Level53 ModuleB siblings' and
                             d['private_source_model_QA_decision'] == 'Accept'))
    base.require(set(family.keys) == set(frozen) == accepted_keys and len(oracle) == 168,
                 'EXACT_REVIEWED_FAMILY', 'Only frozen167 siblings and168 source oracle')
    source_read_seconds = time.perf_counter() - started
    closure = {'schema': 'fathom.private.compiled-family-closure.1',
               'input_pins': config['pins'], 'source_pins': family.source_refs,
               'policy_sha256': model.PINS[model.POLICY], 'runtime_admitted': False,
               'official_accepted': False, 'source_numeric_clock': None, 'source_acoustic_gates': None,
               'authored_cue_onsets_q': [[0, 1], [1, 1], [2, 1], [3, 1]],
               'authored_cue_end_q': [4, 1], 'context_groups': {}}
    rows, classes = [], {}
    for key in family.keys:
        c, o = family.contract(key), oracle[key]
        base.require(canonical(c) == canonical(frozen[key]), 'FROZEN_CONTRACT_PARITY', key)
        voices = c['voices_low_to_high']
        for field, values in [('strings', [v['string'] for v in voices]),
                              ('frets', [v['fret'] for v in voices]),
                              ('literal_notes_low_to_high', [v['printed_note'] for v in voices]),
                              ('degrees_low_to_high', [v['printed_degree'] for v in voices]),
                              ('derived_standard_tuning_midi', [v['derived_standard_tuning_midi'] for v in voices])]:
            base.require(values == o[field], 'ORIGINAL_ORACLE_PARITY', key + ':' + field)
        base.require(o['source_clock'] is None and o['source_identity'] == c['source_identity'],
                     'SOURCE_AUTHORITY', key)
        context = [t['instruction'] for t in c['source_context']]
        context_key = sha(canonical(context))
        closure['context_groups'][context_key] = context
        group = str(o['physical_page']) + '/' + c['quality'] + '/' + c['inversion']
        classes.setdefault(group, key)
        row = {'source_key': key, 'source_identity': c['source_identity'],
               'label': c['root'] + ' ' + c['quality'] + ' · ' + c['inversion'] + ' · strings ' +
                        '–'.join(map(str, o['strings'])),
               'behavior_class': group, 'root': c['root'], 'quality': c['quality'],
               'inversion': c['inversion'], 'voices_low_to_high': voices,
               'suggested_fingers_low_to_high': c['suggested_fingers_low_to_high'],
               'context_ref': context_key, 'source_binding_sha256': c['source_binding_sha256'],
               'source_record_sha256': c['source_record_sha256'],
               'source_contract_sha256': sha(canonical(c))}
        rows.append(row)
    base.require(len(rows) == len({r['source_key'] for r in rows}) == 167 and len(classes) == 24,
                 'FAMILY_COVERAGE', '167 distinct rows and24 classes required')
    closure['shared_setup'] = family.policy['source_facts']['source_setup']
    closure['shared_context'] = [family.policy['source_facts']['suggested_fingering'],
                                family.policy['source_facts']['page_workout_order'],
                                representative['context'][-1]]
    closure['release'] = representative['release']
    closure['paced_explanation'] = representative['paced_explanation']
    closure['class_representatives'] = classes
    closure_bytes = canonical(closure) + b'\n'
    closure_hash = sha(closure_bytes)
    lines = ['#pragma once', '#include "tasks/TaskContract.hpp"', '#include <array>', '#include <map>',
             'namespace fathom::tasks::compiled_family {',
             'struct Row { const char* key; const char* label; const char* provenance; '
             'const char* context; const char* naming; const char* fingers; std::array<Contact,3> voices; };',
             'inline const std::array<Row,167> rows = {{']
    for row in rows:
        provenance = {'family_closure_sha256': closure_hash, 'source_identity': row['source_identity'],
                      'binding_sha256': row['source_binding_sha256'], 'record_sha256': row['source_record_sha256'],
                      'contract_sha256': row['source_contract_sha256'], 'runtime_admitted': False,
                      'source_clock': None, 'audio_contract': None}
        naming = 'Written low/middle/high: ' + ', '.join(v['printed_note'] + ' (' + v['printed_degree'] + ')'
                                                       for v in row['voices_low_to_high'])
        fingers = 'Source suggested fingers low/middle/high: ' + '-'.join(row['suggested_fingers_low_to_high']) + '; open-string adaptations remain permitted.'
        contacts = '{{' + ','.join('{' + ','.join(str(v[k]) for k in ('string', 'fret', 'derived_standard_tuning_midi')) + '}'
                                   for v in row['voices_low_to_high']) + '}}'
        lines.append('{' + ','.join(quote(x) for x in [row['source_key'], row['label'], canonical(provenance).decode(),
                                                     row['context_ref'], naming, fingers]) + ',' + contacts + '},')
    lines.extend(['}};', 'inline const std::map<std::string,std::vector<std::string>> contexts = {'])
    for key, context in closure['context_groups'].items():
        lines.append('{' + quote(key) + ',{' + ','.join(map(quote, context)) + '}},')
    lines.extend(['};'])
    for name, values in [('setup', closure['shared_setup']), ('commonContext', closure['shared_context'])]:
        lines.append('inline const std::vector<std::string> ' + name + ' = {' + ','.join(map(quote, values)) + '};')
    for name, value in [('policy', closure['policy_sha256']), ('release', closure['release']),
                         ('pacedExplanation', closure['paced_explanation'])]:
        lines.append('inline constexpr const char* ' + name + ' = ' + quote(value) + ';')
    lines.append('}')
    generated_header = ('\n'.join(lines) + '\n').encode()
    header = (root / 'Source/tasks/TaskContract.hpp').read_text()
    needle = '    friend const Definition& representativeDefinition(const std::string&);'
    base.require(header.count(needle) == 1, 'CORE_EXTENSION', 'Single private trusted-factory friend')
    header = header.replace(needle, needle + '\n    friend const Definition& compiledFamilyDefinition(const std::string&);')
    needle = 'const Definition& representativeDefinition(const std::string& exactSourceKey);'
    base.require(header.count(needle) == 1, 'CORE_EXTENSION', 'Exact private factory declaration point')
    header = header.replace(needle, needle + '\n// Private pilot only: exact frozen167 sibling table.\n'
                            'const Definition& compiledFamilyDefinition(const std::string&);\n'
                            'const std::vector<std::string>& compiledFamilyKeys();')
    payloads = {'family-closure.json': closure_bytes,
                'definitions.jsonl': b''.join(canonical(row) + b'\n' for row in rows),
                'GeneratedFamilyData.hpp': generated_header,
                'include/tasks/TaskContract.hpp': header.encode()}
    for name in ['TaskContract.cpp', 'ManualTaskAdapter.hpp', 'ManualTaskAdapter.cpp', 'GeneratedRepresentative.hpp']:
        payloads['include/tasks/' + name] = (root / 'Source/tasks' / name).read_bytes()
    for name in ['CompiledFamily.cpp']:
        payloads[name] = (root / 'Tools' / PILOT / name).read_bytes()
    output.mkdir(parents=True)
    for name, data in payloads.items():
        path = output / name
        path.parent.mkdir(parents=True, exist_ok=True)
        base.write_exclusive(path, data)
    receipt = {'schema': 'fathom.private.compiler-generation.1', 'rows': len(rows),
               'behavior_classes': len(classes), 'context_groups_cached': len(closure['context_groups']),
               'cached_input_check_seconds': round(source_read_seconds, 6),
               'generation_seconds': round(time.perf_counter() - started, 6),
               'payloads': [identity(output, path) for path in payloads],
               'representative_byte_parity': True, 'source_contract_and_original_oracle_parity': 167,
               'new_business_logic_per_row': 0, 'runtime_admitted': False, 'official_accepted': False}
    base.write_exclusive(output / 'generation-receipt.json', canonical(receipt) + b'\n')
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True)
    parser.add_argument('--config', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    result = compile_family(args.root, args.config, args.output)
    print(json.dumps({k: v for k, v in result.items() if k != 'payloads'}, sort_keys=True))
