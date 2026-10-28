#!/usr/bin/env python3
"""Level48 metadata-only correction; all implementation fields remain exact."""
import copy, datetime, hashlib, json, resource, time
from pathlib import Path
import pdfplumber
from correct import correct, validate
ROOT = Path(__file__).resolve().parents[3]
LANE = 'fullscope-private-a-r01'
OLD = ROOT / f'Build/{LANE}/level048-r09'
OUT = ROOT / f'Build/{LANE}/level048-r10'
RES = ROOT / f'Results/{LANE}/level048-r10'
PROMPT = ROOT / f'Prompts/{LANE}/level048-root-role-metadata-r01/full-template-prompt.md'


def ref(path):
    path = Path(path)
    return {'path': str(path.relative_to(ROOT)), 'bytes': path.stat().st_size, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def dump(path, value):
    with path.open('x') as out:
        json.dump(value, out, indent=2, ensure_ascii=False)
        out.write('\n')


def main():
    start = datetime.datetime.now(datetime.timezone.utc)
    timer = time.perf_counter()
    assert ref(OLD / 'packet.jsonl')['sha256'] == 'f8586bd61b4dd11672a8e35a50807c99cf837a0a4848ddcb6333a7723d0b136e'
    assert ref(PROMPT)['sha256'] == '32d8959df7bcdb5f2c58dde1b76731d0846095e17eb59fe2cb5087e70959f82d'
    if OUT.exists() or RES.exists():
        raise FileExistsError('Fresh output roots required')
    raw = (OLD / 'packet.jsonl').read_text().splitlines(keepends=True)
    records = [json.loads(x) for x in raw]
    originals = [{k: v for k, v in x.items() if k != 'locator'} for x in records[0]['source_refs'][:2]]
    assert all(ref(ROOT / x['path']) == x for x in originals)
    source = (ROOT / originals[0]['path']).read_text().splitlines()
    assert 'r = rest' in source[29]
    with pdfplumber.open(ROOT / originals[1]['path']) as pdf:
        pages = {n: pdf.pages[n - 1].extract_text() for n in (2, 12)}
    assert 'A roots' in pages[2] and 'Beat-1 target: A root' in pages[12]
    audit, changed = [], []
    checks = 2
    genuine_rest_tokens = 0
    for number, before in enumerate(records, 1):
        after, removed = correct(before)
        real = []
        for block in before['source_payload']['notation_blocks']:
            for row in block['notation_rows']:
                if row['label'] not in ('Rol', 'Job', 'Nte'):
                    continue
                assert source[row['line'] - 1].split('|', 1)[1] == row['body']
                checks += 1
                if row['label'] == 'Nte':
                    real += [{'block_index': block['block_index'], 'column': t['column'], 'token': t['text']}
                             for t in row['tokens'] if t['text'] in ('r', 'R')]
        genuine_rest_tokens += len(real)
        new_blocks = {b['block_index']: b for b in after['source_payload']['notation_blocks']}
        assert all(x['column'] in new_blocks[x['block_index']]['printed_rest_columns'] for x in real)
        assert after['implementation'] == before['implementation']
        assert after['unresolved_reasons'] == before['unresolved_reasons']
        assert after['status'] == before['status'] and after['timing_authority'] == before['timing_authority']
        checks += 4
        if removed:
            after['provenance']['root_role_metadata_correction'] = {
                'predecessor': ref(OLD / 'packet.jsonl'), 'producer': ref(Path(__file__)),
                'correction_code': ref(Path(__file__).with_name('correct.py')), 'source_originals': originals,
                'rest_legend_txt_lines': [29, 30], 'root_source_context_pdf_pages': [2, 12],
                'scope': 'source_payload.notation_blocks[].printed_rest_columns only; implementation unchanged',
                'independent_review': False}
            changed.append(number)
        validate(before, after)
        audit.append({'row': number, 'package_key': before['package_key'], 'source_identity': before['source_identity'],
            'old_record_canonical_sha256': digest(before), 'new_record_canonical_sha256': digest(after),
            'removed_false_rest_hints': removed, 'genuine_note_row_rests_retained': real,
            'implementation_sha256_unchanged': digest(before['implementation']),
            'actual_typed_rest_actions_unchanged': True, 'status_timing_unresolved_unchanged': True})
        records[number - 1] = after
    assert len(changed) == 38 and sum(len(x['removed_false_rest_hints']) for x in audit) == 158
    OUT.mkdir()
    RES.mkdir()
    with (OUT / 'packet.jsonl').open('x') as out:
        for number, record in enumerate(records, 1):
            out.write(json.dumps(record, ensure_ascii=False, separators=(',', ':')) + '\n' if number in changed else raw[number - 1])
    actual = (OUT / 'packet.jsonl').read_text().splitlines(keepends=True)
    assert all(actual[n - 1] == raw[n - 1] for n in range(1, 63) if n not in changed)
    dump(OUT / 'all62-typed-rest-audit.json', {'source_originals': originals, 'predecessor': ref(OLD / 'packet.jsonl'),
        'source_context_pdf_pages': pages, 'source_rest_legend_txt_lines': source[28:30], 'records': audit,
        'removed_false_hints': 158, 'changed_records': 38, 'genuine_note_row_rest_tokens_retained': genuine_rest_tokens,
        'scope': 'Only untyped metadata hints changed; all actual implementation fields byte-semantically exact.'})
    context = json.loads((OLD / 'level-source-context.json').read_text())
    context['root_role_metadata_correction'] = {'audit': ref(OUT / 'all62-typed-rest-audit.json'),
                                               'implementation_fields_unchanged': True}
    dump(OUT / 'level-source-context.json', context)
    dump(OUT / 'remaining-keys.json', [])
    info = {'status': 'PASS', 'source_and_delta_checks': checks, 'changed_rows': changed,
            'changed_keys': [x['package_key'] for x in audit if x['removed_false_rest_hints']],
            'removed_false_rest_hints': 158, 'genuine_note_row_rest_tokens_retained': genuine_rest_tokens,
            'unchanged_record_bytes': 24, 'all62_implementation_fields_unchanged': True,
            'readiness_and_status_changes': 0, 'new_independent_native_integrated_accepted': 0}
    dump(RES / 'semantic-checks.json', info)
    previous = json.loads((ROOT / f'Results/{LANE}/level048-r09/seal.json').read_text())
    inputs = {x['path']: x for x in previous['source_inputs']}
    for path in [OLD / 'packet.jsonl', OLD / 'level-source-context.json', PROMPT, Path(__file__),
                 Path(__file__).with_name('correct.py'), OUT / 'all62-typed-rest-audit.json']:
        entry = ref(path)
        inputs[entry['path']] = entry
    seal = {**previous, 'started_utc': start.isoformat(), 'ended_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'elapsed_seconds': time.perf_counter() - timer, 'process_peak_rss_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        'packet': ref(OUT / 'packet.jsonl'), 'context': ref(OUT / 'level-source-context.json'),
        'remaining_keys_reference': ref(OUT / 'remaining-keys.json'), 'source_inputs': list(inputs.values()),
        'targeted_checks': ref(RES / 'semantic-checks.json'),
        'command': 'Bundled Python -B Tools/fullscope-private-a-r01/level048-root-role-metadata-r01/produce.py',
        'limits': 'Exact root-role metadata-only correction; all62 implementation fields, timing, source guidance, unresolved conditions and status remain unchanged.'}
    dump(RES / 'seal.json', seal)
    (RES / 'handoff.md').write_text('# Level48 r10 — root-role metadata correction\n\n'
        f'Removed158 false rest hints in38 exact children from source_payload notation metadata. Each removed uppercase Rol R has a sounding A/D/E Nte token at the same column; all{genuine_rest_tokens} genuine Nte rest tokens remain represented. The literal rest legend is TXT29–30; PDF2/12 provides root context.\n\n'
        'Every implementation field in all62 records is unchanged, including typed rests/holds/actions, source traversal, symbolic timing, motif relationships, density/dynamics and guidance discrepancies.24 unrelated records are byte-identical. No original source text, contact, note, attack, timing, unresolved reason or status changed.\n\n'
        'Counts remain3manual/21choice/38partial. Native/app/GUI/performance checks NOT_RUN; no independent review, admission, integrated or Accepted promotion. A separate read-only effective-A same-cause scan follows.\n')
    print(json.dumps({'packet': seal['packet'], 'changed_records': 38, 'removed_false_hints': 158,
        'genuine_note_row_rests': genuine_rest_tokens, 'runtime_seconds': seal['elapsed_seconds'], 'peak_rss_bytes': seal['process_peak_rss_bytes']}))


if __name__ == '__main__':
    main()
