#!/usr/bin/env python3
"""One read-only effective-A scan of untyped root-R rest metadata."""
import collections, datetime, hashlib, json, re, resource, subprocess, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
LANE = 'fullscope-private-a-r01'
NAME = 'effective-a-root-role-scan-r01'
BASE = ROOT / f'Build/{LANE}/semantic-overlay-index-r09/effective-range-index.jsonl'
CURRENT48 = ROOT / f'Build/{LANE}/level048-r10/packet.jsonl'
PROMPT = ROOT / f'Prompts/{LANE}/{NAME}/full-template-prompt.md'
OUT, RES = [ROOT / f'{area}/{LANE}/{NAME}' for area in ('Build', 'Results')]


def ref(path):
    path = Path(path)
    if not path.is_absolute():
        path = ROOT / path
    h = hashlib.sha256()
    with path.open('rb') as inp:
        for block in iter(lambda: inp.read(1024 * 1024), b''):
            h.update(block)
    return {'path': str(path.relative_to(ROOT)), 'bytes': path.stat().st_size, 'sha256': h.hexdigest()}


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def dump(path, value):
    with path.open('x') as out:
        json.dump(value, out, indent=2, ensure_ascii=False)
        out.write('\n')


def intersections(record):
    found = []
    for block in record['source_payload']['notation_blocks']:
        hints = set(block['printed_rest_columns'])
        notes = collections.defaultdict(list)
        for row in block['notation_rows']:
            if row['label'] == 'Nte':
                for token in row['tokens']:
                    notes[token['column']].append(token['text'])
        for row in block['notation_rows']:
            if row['label'] in ('Nte', 'E', 'A', 'D', 'G', 'B', 'e', 'S'):
                continue
            for token in row['tokens']:
                col = token['column']
                if token['text'] != 'R' or col not in hints:
                    continue
                names = notes[col]
                if any(name in ('R', 'r') for name in names):
                    status = 'GENUINE_NOTE_REST_COLLISION_REVIEW_ONLY'
                elif row['label'] in ('Rol', 'Job') and len(names) == 1 and re.fullmatch(r'[A-G](?:#|b)?', names[0]):
                    status = 'HARMONIC_ROOT_FALSE_REST_HINT'
                else:
                    status = 'OTHER_R_HINT_TYPED_REVIEW_REQUIRED'
                found.append({'block_index': block['block_index'], 'column': col, 'role_label': row['label'],
                    'source_line': row['line'], 'role_body': row['body'], 'note_tokens_at_column': names,
                    'classification': status, 'generic_implementation_rest_hint_present':
                        {'block_index': block['block_index'], 'column': col} in record['implementation']['ordered_rest_locations']})
    return found


def controls():
    r = {'source_payload': {'notation_blocks': [{'block_index': 1, 'printed_rest_columns': [0, 4],
        'notation_rows': [{'label': 'Rol', 'line': 1, 'body': 'R---3', 'tokens': [{'text': 'R', 'column': 0}]},
                          {'label': 'Nte', 'tokens': [{'text': 'A', 'column': 0}, {'text': 'r', 'column': 4}]}]}]},
        'implementation': {'ordered_rest_locations': [{'block_index': 1, 'column': 0}]}}
    x = intersections(r)
    assert len(x) == 1 and x[0]['classification'] == 'HARMONIC_ROOT_FALSE_REST_HINT'
    r['source_payload']['notation_blocks'][0]['notation_rows'][1]['tokens'][0]['text'] = 'R'
    assert intersections(r)[0]['classification'] == 'GENUINE_NOTE_REST_COLLISION_REVIEW_ONLY'
    r['source_payload']['notation_blocks'][0]['printed_rest_columns'] = [4]
    assert not intersections(r)
    return ['pitched root hint detected', 'actual note R kept distinct', 'corrected root hint absent; real r is not flagged']


def main():
    started = datetime.datetime.now(datetime.timezone.utc)
    timer = time.perf_counter()
    assert ref(BASE)['sha256'] == '241c404267db4407210d510a6bce631525849eb6355a03c16cba94c36e558c41'
    assert ref(CURRENT48)['sha256'] == '76cf6c3f8121cedc36542ead4e31bda3fd16c6f0d168aa7d07326d8721c6dd6b'
    assert ref(PROMPT)['sha256'] == '3a02f0539115a2564b44dd6abddf44d3e0b3890a6190ce2327acda4a68e532bf'
    if OUT.exists() or RES.exists():
        raise FileExistsError('Fresh scan outputs required')
    entries = [json.loads(s) for s in BASE.read_text().splitlines()]
    assert len(entries) == 2566
    assert digest([[e['package_key'], e['source_identity']] for e in entries]) == '7cdeb5340db49f56b944aff2b58118a33a86e125a9b5a4dc75e0d35cb21fe66f'
    inputs = {}
    for path in [BASE, CURRENT48, PROMPT, Path(__file__),
                 ROOT / f'Results/{LANE}/semantic-overlay-index-r09/artifact-manifest.json',
                 ROOT / f'Results/{LANE}/level048-r10/artifact-manifest.json']:
        z = ref(path)
        inputs[z['path']] = z
    by_packet = collections.defaultdict(list)
    for e in entries:
        path = str(CURRENT48.relative_to(ROOT)) if e['level'] == 48 else e['packet']['path']
        by_packet[path].append(e)
    OUT.mkdir()
    RES.mkdir()
    findings, level_counts = [], collections.defaultdict(collections.Counter)
    checked, block_count, source_joins = 0, 0, 0
    with (OUT / 'all2566-record-audit.jsonl').open('x') as audit:
        for path, selected in by_packet.items():
            packet = ref(path)
            inputs[path] = packet
            if selected[0]['level'] != 48:
                assert all(e['packet'] == packet for e in selected)
            targets = {e['line']: e for e in selected}
            txt_cache = {}
            for lineno, line in enumerate((ROOT / path).open(), 1):
                if lineno not in targets:
                    continue
                record, entry = json.loads(line), targets[lineno]
                assert record['package_key'] == entry['package_key'] and record['source_identity'] == entry['source_identity']
                row_sha = digest(record)
                if record['level'] != 48:
                    assert row_sha == entry['record_canonical_sha256']
                found = intersections(record)
                n = record['level']
                checked += 1
                block_count += len(record['source_payload']['notation_blocks'])
                level_counts[n]['records_checked'] += 1
                for x in found:
                    textrefs = [r for r in record['source_refs'] if r['path'].endswith('.txt')]
                    if len(textrefs) != 1:
                        raise ValueError('Candidate lacks unique original TXT authority')
                    original = {k: v for k, v in textrefs[0].items() if k != 'locator'}
                    if original['path'] not in txt_cache:
                        assert ref(original['path']) == original
                        inputs[original['path']] = original
                        txt_cache[original['path']] = (ROOT / original['path']).read_text().splitlines()
                    source_line = txt_cache[original['path']][x['source_line'] - 1]
                    assert source_line.split('|', 1)[1].startswith(x['role_body'])
                    x['source_original'] = original
                    x['source_line_text'] = source_line
                    source_joins += 1
                    level_counts[n][x['classification']] += 1
                if found:
                    level_counts[n]['records_with_intersections'] += 1
                    findings.append({'level': n, 'packet': packet, 'line': lineno, 'package_key': record['package_key'],
                        'source_identity': record['source_identity'], 'record_canonical_sha256': row_sha, 'intersections': found})
                audit.write(json.dumps({'level': n, 'package_key': record['package_key'], 'source_identity': record['source_identity'],
                    'packet': packet, 'line': lineno, 'record_canonical_sha256': row_sha,
                    'notation_blocks_checked': len(record['source_payload']['notation_blocks']),
                    'retained_R_metadata_intersections': len(found)}, ensure_ascii=False, separators=(',', ':')) + '\n')
    assert checked == 2566 and len(level_counts) == 43
    dump(OUT / 'remaining-root-role-hints.json', findings)
    summary = {'status': 'SCAN_COMPLETE_READ_ONLY', 'started_utc': started.isoformat(),
        'ended_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'elapsed_seconds': time.perf_counter() - timer,
        'process_peak_rss_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        'exact_effective_records_checked': checked, 'levels_checked': len(level_counts), 'notation_blocks_checked': block_count,
        'source_role_row_joins': source_joins, 'records_with_remaining_intersections': len(findings),
        'classification_counts': dict(collections.Counter(x['classification'] for f in findings for x in f['intersections'])),
        'level_results': {str(n): dict(v) for n, v in sorted(level_counts.items())},
        'positive_controls': controls(), 'packet_writes': 0, 'source_changes': 0, 'readiness_or_status_changes': 0,
        'limits': 'Only retained untyped uppercase non-note R/rest-hint intersections. No broader source accuracy, admission, native, integration or app/GUI evidence.'}
    dump(RES / 'summary.json', summary)
    (RES / 'handoff.md').write_text('# Effective A root-role metadata scan\n\n'
        f'Checked all2,566 exact effective identities in43 levels and{block_count} notation blocks, using frozen r09 index plus Level48r10. Remaining intersections occur in{len(findings)} records; exact keys/row hashes/original source-role lines are in the bounded findings artifact.\n\n'
        'This read-only scan does not change source packets, typed events, timing, status or counts. Harmonic-root false-rest candidates, genuine note-rest collisions and other typed ambiguities are classified separately. Prior Level37/40/46/47 seals and L47 retained exception remain frozen. Native/compiler/app/GUI and source acceptance NOT_RUN.\n')
    scopes = [f'{area}/{LANE}/{NAME}/' for area in ('Prompts', 'Results', 'Build', 'Tools', 'Tests')]
    subprocess.run(['git', 'diff', '--check', '--', *scopes], cwd=ROOT, check=True, capture_output=True)
    cmd = [sys.executable, '-B', 'Tools/fathom_evidence.py', 'git-summary', '--root', str(ROOT), '--output', str(RES / 'git-state.json')]
    for scope in scopes:
        cmd += ['--scope', scope]
    subprocess.run(cmd, cwd=ROOT, check=True, capture_output=True)
    audit = subprocess.run([sys.executable, '-B', 'Tools/fathom_evidence.py', 'audit', '--root', str(ROOT), '--evidence-dir', str(RES)],
                           cwd=ROOT, check=True, capture_output=True, text=True)
    dump(RES / 'integrity.json', {'status': 'PASS', 'source_input_rehashes': len(inputs),
        'packet_write_count': 0, 'git_diff_check_exit': 0, 'evidence_audit': json.loads(audit.stdout)})
    for entry in inputs.values():
        assert ref(entry['path']) == entry
    paths = {p: 'read-only exact source/packet authority' for p in inputs}
    for path in [*OUT.iterdir(), *RES.iterdir()]:
        paths[str(path.relative_to(ROOT))] = 'bounded same-cause scan evidence'
    cmd = [sys.executable, '-B', 'Tools/fathom_evidence.py', 'manifest', '--root', str(ROOT), '--output', str(RES / 'artifact-manifest.json')]
    for path, role in sorted(paths.items()):
        cmd += ['--artifact', path + '|' + role]
    subprocess.run(cmd, cwd=ROOT, check=True, capture_output=True)
    manifest = json.loads((RES / 'artifact-manifest.json').read_text())
    assert all(all(ref(x['path'])[key] == x[key] for key in ('path', 'bytes', 'sha256')) for x in manifest['artifacts'])
    print(json.dumps({'summary': ref(RES / 'summary.json'), 'manifest': ref(RES / 'artifact-manifest.json'),
        'findings': ref(OUT / 'remaining-root-role-hints.json'), 'manifest_entries': len(manifest['artifacts']),
        'records_with_intersections': len(findings), 'classification_counts': summary['classification_counts'],
        'affected_levels': {n: v for n, v in summary['level_results'].items() if v.get('records_with_intersections')}}))


if __name__ == '__main__':
    main()
