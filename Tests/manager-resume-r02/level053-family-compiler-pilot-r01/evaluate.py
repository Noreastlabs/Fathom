#!/usr/bin/env python3
"""Cached independent source checks, deterministic build and shared-core tests."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import time

PILOT = 'manager-resume-r02/level053-family-compiler-pilot-r01'
ORACLE = 'Build/manager-resume-r02/private-coherent-bulk-review-r02/level053-original-oracle.json'
REP = 'exercise-completeness-r01/level053/moduleb/p003-t1-r1-c2/cmajrp'


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def evaluate(root, config, output):
    begin = time.perf_counter()
    root, output = Path(root).resolve(), Path(output).absolute()
    if output.resolve() != output or not output.is_relative_to(root / 'Build' / PILOT) or output.exists():
        raise ValueError('Fresh private evaluation output required')
    output.mkdir(parents=True)
    generator = root / 'Tools' / PILOT / 'compile_family.py'
    spec = importlib.util.spec_from_file_location('pilot_compiler', generator)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    builds = []
    for n in [1, 2]:
        generated = output / ('generated-' + str(n))
        result = module.compile_family(root, config, generated)
        builds.append((generated, result))
    first, second = [item[1]['payloads'] for item in builds]
    if first != second:
        raise ValueError('Deterministic generated payloads differ')
    generated = builds[0][0]
    rows = [json.loads(x) for x in (generated / 'definitions.jsonl').read_bytes().splitlines()]
    closure = json.loads((generated / 'family-closure.json').read_text())
    oracle = {x['package_key']: x for x in json.loads((root / ORACLE).read_text())}
    checks = 0
    classes, expected = {}, []
    for row in rows:
        o = oracle[row['source_key']]
        voices = row['voices_low_to_high']
        tests = [row['source_identity'] == o['source_identity'], row['root'] == o['root'],
                 row['quality'] == o['quality'], row['context_ref'] in closure['context_groups'],
                 [v['string'] for v in voices] == o['strings'],
                 [v['fret'] for v in voices] == o['frets'],
                 [v['derived_standard_tuning_midi'] for v in voices] == o['derived_standard_tuning_midi'],
                 [v['printed_note'] for v in voices] == o['literal_notes_low_to_high'],
                 [v['printed_degree'] for v in voices] == o['degrees_low_to_high'],
                 closure['source_numeric_clock'] is None, closure['source_acoustic_gates'] is None,
                 closure['runtime_admitted'] is False, closure['official_accepted'] is False,
                 len(row['source_contract_sha256']) == 64]
        checks += len(tests)
        if not all(tests):
            raise ValueError('Independent row/source parity: ' + row['source_key'])
        klass = (o['physical_page'], o['quality'], o['inversion'])
        classes.setdefault(klass, row['source_key'])
        contacts = '{{' + ','.join('{' + ','.join(map(str, triple)) + '}'
                                 for triple in zip(o['strings'], o['frets'], o['derived_standard_tuning_midi'])) + '}}'
        expected.append('{' + json.dumps(row['source_key']) + ',' + contacts + '},')
    if len(rows) != 167 or len(classes) != 24 or REP in {r['source_key'] for r in rows}:
        raise ValueError('Wrong source/family/class denominator')
    header = ['#pragma once', '#include "tasks/TaskContract.hpp"', '#include <array>', 'namespace expected {',
              'struct Row { const char* key; std::array<fathom::tasks::Contact,3> voices; };',
              'inline constexpr const char* representative = ' + json.dumps(REP) + ';',
              'inline const std::array<Row,167> rows = {{', *expected, '}};',
              'inline const std::array<const char*,24> classes = {{' + ','.join(map(json.dumps, classes.values())) + '}};', '}']
    (output / 'ExpectedRows.hpp').write_text('\n'.join(header) + '\n')
    commands = []
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')

    def run(name, args):
        start = time.perf_counter()
        result = subprocess.run(args, cwd=root, env=env, text=True, capture_output=True)
        (output / (name + '.stdout')).write_text(result.stdout)
        (output / (name + '.stderr')).write_text(result.stderr)
        entry = {'name': name, 'argv': [str(x) for x in args], 'exit': result.returncode,
                 'seconds': round(time.perf_counter() - start, 6)}
        commands.append(entry)
        if result.returncode:
            (output / 'failed-command.json').write_text(json.dumps(entry, indent=2) + '\n')
            raise RuntimeError(name + ': ' + result.stderr[-2500:])
        return result.stdout

    compiler = run('compiler-path', ['xcrun', '--find', 'clang++']).strip()
    version = run('compiler-version', [compiler, '--version']).splitlines()[0]
    sdk = run('sdk-path', ['xcrun', '--sdk', 'macosx', '--show-sdk-path']).strip()
    std_headers = Path(sdk) / 'usr/include/c++/v1'
    if not (std_headers / 'cstdint').is_file():
        raise RuntimeError('Installed SDK lacks the required C++ standard headers')
    sources = [root / 'Tests' / PILOT / 'family_core_tests.cpp', generated / 'CompiledFamily.cpp',
               generated / 'include/tasks/TaskContract.cpp', generated / 'include/tasks/ManualTaskAdapter.cpp',
               root / 'Source/core/Quantity.cpp', root / 'Source/core/Scheduler.cpp',
               root / 'Source/core/FramePosition.cpp']
    flags = ['-std=c++17', '-O0', '-Wall', '-Wextra', '-Werror', '-isysroot', sdk,
             '-isystem', str(std_headers),
             '-I' + str(generated / 'include'), '-I' + str(generated), '-I' + str(root / 'Source'), '-I' + str(output)]
    dependency_text = run('dependencies', [compiler, *flags, '-MM', *map(str, sources)])
    dependencies = set()
    for item in dependency_text.replace('\\\n', ' ').splitlines():
        if ': ' not in item:
            continue
        # clang escapes spaces in dependency paths; preserve them before splitting.
        import shlex
        dependencies.update(shlex.split(item.split(': ', 1)[1]))
    dependency_pins = []
    for name in sorted(dependencies):
        path = Path(name)
        if not path.is_absolute():
            path = root / path
        data = path.read_bytes()
        dependency_pins.append({'path': str(path.relative_to(root)), 'bytes': len(data), 'sha256': sha(data)})
    run('compile', [compiler, *flags, *map(str, sources), '-o', str(output / 'family-core-tests')])
    core = json.loads(run('core-tests', [str(output / 'family-core-tests')]))
    if core['result'] != 'PASS' or core['rows'] != 167 or core['behavior_classes'] != 24:
        raise ValueError('Shared core tests failed')
    # Existing single-key generation remains a refusing, byte-identical boundary.
    base = module.load(root / module.BASE, 'pilot_original_refusal')
    raw = base.read_pinned(root)
    negative = 0
    for key in [rows[0]['source_key'], 'foreign']:
        try:
            base.validate(raw, key)
        except base.Refusal as error:
            if error.code != 'REPRESENTATIVE_SCOPE':
                raise
            negative += 1
        else:
            raise ValueError('Original generator scope widened')
    # Source drift must refuse before a generated table can be emitted.
    bad = json.loads(Path(config).read_text())
    bad['pins'][0]['sha256'] = '0' * 64
    bad_path = output / 'bad-config.json'
    bad_path.write_text(json.dumps(bad))
    try:
        module.compile_family(root, bad_path, output / 'must-not-exist')
    except base.Refusal:
        negative += 1
    except ValueError as error:
        if 'INPUT_DRIFT' not in str(error):
            raise
        negative += 1
    else:
        raise ValueError('Compiler accepted source drift')
    if (output / 'must-not-exist').exists():
        raise ValueError('Failed generation published partial output')
    bad['pins'] = bad['pins'][1:]
    bad_path.write_text(json.dumps(bad))
    try:
        module.compile_family(root, bad_path, output / 'must-not-exist')
    except ValueError as error:
        if 'INPUT_CLOSURE' not in str(error):
            raise
        negative += 1
    else:
        raise ValueError('Compiler accepted a dropped input pin')
    try:
        module.compile_family(root / 'Build' / PILOT, config, output / 'must-not-exist')
    except ValueError as error:
        if 'ROOT_SCOPE' not in str(error):
            raise
        negative += 1
    else:
        raise ValueError('Compiler accepted a repository subdirectory as root')
    config_data = json.loads(Path(config).read_text())
    for pin in config_data['pins']:
        if module.identity(root, pin['path']) != pin:
            raise ValueError('Retained input changed: ' + pin['path'])
    receipt = {'schema': 'fathom.private.compiler-evaluation.1', 'result': 'PASS', 'rows': 167,
               'source_row_assertions': checks, 'behavior_classes': 24, 'shared_core': core,
               'negative_generator_controls': negative, 'deterministic_payloads': len(first),
               'generation_runs': [b[1]['generation_seconds'] for b in builds],
               'evaluation_seconds': round(time.perf_counter() - begin, 6),
               'compiler': version, 'sdk': sdk, 'commands': commands, 'dependency_pins': dependency_pins,
               'input_pins_unchanged': len(config_data['pins']),
               'generated_payload_bytes': sum(x['bytes'] for x in first),
               'definition_data_bytes': (generated / 'definitions.jsonl').stat().st_size,
               'generated_cpp_table_bytes': (generated / 'GeneratedFamilyData.hpp').stat().st_size,
               'generator_code_bytes': generator.stat().st_size,
               'factory_code_bytes': (root / 'Tools' / PILOT / 'CompiledFamily.cpp').stat().st_size,
               'per_row_models_or_prompts': 0,
               'parity_scope': 'Exact frozen source facts/contracts; unchanged representative core Task+Adapter behavior on24classes andall167source-order paths. Private rich typed naming-report/history semantics are retained in frozen contracts, not exposed by this core.',
               'gates': 'PRIVATE_PILOT_ONLY; installed integration/admission/native release/listening/physical/performance/persistence unexecuted; no source clock/audio/credit claims.'}
    (output / 'evaluation.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True)
    parser.add_argument('--config', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    result = evaluate(args.root, args.config, args.output)
    print(json.dumps({k: result[k] for k in ['result', 'rows', 'behavior_classes', 'source_row_assertions',
                                          'generation_runs', 'evaluation_seconds', 'generated_payload_bytes',
                                          'definition_data_bytes', 'generator_code_bytes', 'factory_code_bytes']}))
