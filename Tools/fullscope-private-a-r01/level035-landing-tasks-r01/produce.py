#!/usr/bin/env python3
"""Six landing-task records, exact source preservation and private evidence."""
import copy, datetime, hashlib, json, re, resource, time
from pathlib import Path
import pdfplumber
from landing import build
ROOT = Path(__file__).resolve().parents[3]
LANE = 'fullscope-private-a-r01'
OLD, OUT = [ROOT / f'Build/{LANE}/level035-{r}' for r in ('r05', 'r06')]
RES = ROOT / f'Results/{LANE}/level035-r06'
PROMPT = ROOT / f'Prompts/{LANE}/level035-landing-tasks-r01/full-template-prompt.md'


def ref(path):
    path = Path(path)
    return {'path': str(path.relative_to(ROOT)), 'bytes': path.stat().st_size, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def dump(path, value):
    with path.open('x') as out:
        json.dump(value, out, indent=2, ensure_ascii=False)
        out.write('\n')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def main():
    start = datetime.datetime.now(datetime.timezone.utc)
    timer = time.perf_counter()
    assert ref(OLD / 'packet.jsonl')['sha256'] == 'de1b66347d6feed5b48608392c09b00975a16142a83ba035c0cfd33f84940f22'
    manifest = ROOT / f'Results/{LANE}/level035-r05/artifact-manifest.json'
    assert ref(manifest)['sha256'] == '2790a1179e8517b1ad28103c65e510e449eb457155f3dca6c1ef5c923d81a105'
    assert ref(PROMPT)['sha256'] == 'e8dda2d90704be9e232ffb6ed246074c56c42655d524f13828b2fae9a9f8e7f2'
    if OUT.exists() or RES.exists():
        raise FileExistsError('Fresh roots required; no overwrite')
    raw = (OLD / 'packet.jsonl').read_text().splitlines(keepends=True)
    records = [json.loads(s) for s in raw]
    originals = [{k: v for k, v in x.items() if k != 'locator'} for x in records[30]['source_refs'][:2]]
    assert all(ref(ROOT / x['path']) == x for x in originals)
    text = (ROOT / originals[0]['path']).read_text().splitlines()
    with pdfplumber.open(ROOT / originals[1]['path']) as pdf:
        pages = {n: pdf.pages[n - 1].extract_text() for n in [1, 2, 8, 9, 10, 13]}
    checks, audit = 0, []
    for row in range(31, 37):
        record = records[row - 1]
        before = copy.deepcopy(record)
        loc = record['source_refs'][0]['locator']
        assert text[loc['line_start'] - 1:loc['line_end']] == record['source_payload']['exact_unit_lines']
        page_number = 8 + (row - 31) // 2
        local = (row - 31) % 2
        page = pages[page_number]
        norm = ' '.join(page.split())
        contract = build(before)
        lane = contract['string_label']
        for phrase in [contract['source_target_matching']['literal_standard'],
                       contract['later_mirror_duty']['pdf_instruction'],
                       'The gap between notes may be silent; the shift itself may not be audible.',
                       'Eyes-up pass: identify the target before leaving the launch note.',
                       'First pass: finger 1 on every note; no slide or scrape.']:
            assert phrase in norm, (row, phrase)
            checks += 1
        assert any(contract['later_mirror_duty']['txt_instruction'] in line for line in text)
        for label in ('Nte', 'Deg', lane, 'Pck'):
            source_rows = [line.split('|', 1)[1] for line in record['source_payload']['exact_unit_lines'] if '|' in line and line.split('|', 1)[0].strip() == label]
            assert len(source_rows) == 1
            pdf_rows = re.findall(r'^' + re.escape(label) + r'\s*\|([^\n]+)', page, re.M)
            pdf_body = pdf_rows[local if label in ('Nte', 'Deg', 'Pck') else 0]
            assert ''.join(source_rows[0].split()) == ''.join(pdf_body.split()), (row, label)
            checks += 1
        for cell in contract['cells']:
            target = cell['target']
            assert f"{target['note']} {target['fret']} {target['degree']} {target['distance_frets']} frets" in norm
            checks += 1
        contract['source_authority'] = {'originals': originals, 'txt_unit_locator': loc,
                                        'pdf_grid_page': page_number, 'pdf_context_pages': [1, 2, 8, 9, 10, 13]}
        record['implementation']['source_landing_task'] = contract
        record['provenance']['landing_task_supplement'] = {
            'predecessor_packet': ref(OLD / 'packet.jsonl'), 'predecessor_record_sha256': digest(before),
            'producer': ref(Path(__file__)), 'task_code': ref(Path(__file__).with_name('landing.py')),
            'source_originals': originals, 'independent_review': False}
        assert {k: v for k, v in record['implementation'].items() if k != 'source_landing_task'} == before['implementation']
        for key in ('source_payload', 'timing_authority', 'status', 'unresolved_reasons'):
            assert record[key] == before[key]
        checks += 6
        audit.append({'row': row, 'package_key': record['package_key'], 'source_identity': record['source_identity'],
            'previous_record_sha256': digest(before), 'new_record_sha256': digest(record), 'landing_cells': 4,
            'source_music_variants_timing_status_unchanged': True})
    assert len(records) == 39 and sum(len(r['implementation']['ordered_contacts']) for r in records) == 384
    OUT.mkdir()
    RES.mkdir()
    dump(OUT / 'original-landing-context.json', {'originals': originals, 'full_pdf_pages': pages,
        'txt_module_c': {'start': 171, 'end': 225, 'lines': text[170:225]},
        'mirror_scope': 'Both original instructions retained; no derived route, timing or fingering selected; no conflict adjudication.'})
    dump(OUT / 'changed-key-audit.json', audit)
    with (OUT / 'packet.jsonl').open('x') as out:
        for row, record in enumerate(records, 1):
            out.write(json.dumps(record, ensure_ascii=False, separators=(',', ':')) + '\n' if 31 <= row <= 36 else raw[row - 1])
    actual = (OUT / 'packet.jsonl').read_text().splitlines(keepends=True)
    assert all(actual[row - 1] == raw[row - 1] for row in range(1, 40) if not 31 <= row <= 36)
    context = json.loads((OLD / 'level-source-context.json').read_text())
    context['landing_task_supplement'] = {'rows': list(range(31, 37)), 'source_context': ref(OUT / 'original-landing-context.json'),
        'cells': 24, 'existing_contacts': 96, 'additional_sounding_events': 0, 'readiness_changes': 0}
    dump(OUT / 'level-source-context.json', context)
    dump(OUT / 'remaining-keys.json', [])
    dump(RES / 'semantic-checks.json', {'status': 'PASS', 'source_preservation_checks': checks,
        'changed_rows': list(range(31, 37)), 'byte_identical_other_records': 33, 'landing_cells': 24,
        'preserved_picked_contacts': 96, 'unchanged_whole_level_contacts': 384,
        'source_supported_implemented': 7, 'partial_source_unresolved': 32, 'new_native_integrated_accepted': 0})
    previous = json.loads((ROOT / f'Results/{LANE}/level035-r05/seal.json').read_text())
    inputs = {x['path']: x for x in previous['source_inputs']}
    for path in [OLD / 'packet.jsonl', OLD / 'level-source-context.json', manifest, PROMPT, Path(__file__),
                 Path(__file__).with_name('landing.py'), OUT / 'original-landing-context.json', OUT / 'changed-key-audit.json']:
        entry = ref(path)
        inputs[entry['path']] = entry
    seal = {**previous, 'started_utc': start.isoformat(), 'ended_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'elapsed_seconds': time.perf_counter() - timer, 'process_peak_rss_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        'packet': ref(OUT / 'packet.jsonl'), 'context': ref(OUT / 'level-source-context.json'),
        'remaining_keys_reference': ref(OUT / 'remaining-keys.json'), 'source_inputs': list(inputs.values()),
        'targeted_checks': ref(RES / 'semantic-checks.json'),
        'command': 'Bundled Python -B Tools/fullscope-private-a-r01/level035-landing-tasks-r01/produce.py',
        'limits': 'Printed first-pass task semantics only. No invented mirror route, clocks, acoustic gates, fixed silent rests, numeric matching tolerances or observed learner result.'}
    dump(RES / 'seal.json', seal)
    (RES / 'handoff.md').write_text('# Level 35 r06 — printed landing tasks\n\n'
        'Six Module C rows 31–36 now bind twenty-four four-contact cells to source eyes-up preparation, direct landing, distinct target re-pick and return. All ninety-six picked contacts and D/U variants remain intact. Target pitch/volume/timing matching is qualitative; silent gaps are allowed without inventing fixed rests or acoustic gates.\n\n'
        'Both original later mirror-pass wordings are retained with no selected fret sequence, fingering or timing, and no source-conflict adjudication. Source first-pass finger-one and no-slide/no-scrape duties remain explicit. No eye movement, accuracy or performed response is claimed.\n\n'
        'All thirty-nine identities and 384 contacts persist; thirty-three unrelated record bytes are identical. Counts remain seven complete private contracts and thirty-two partial. No independent acceptance, native/integrated/Accepted or learner credit is added; app/native/GUI/performance checks NOT_RUN. Producer remains OPEN_CONTINUING_IMPLEMENTATION_BACKLOG.\n')
    print(json.dumps({'packet': seal['packet'], 'checks': checks, 'runtime_seconds': seal['elapsed_seconds'],
                      'peak_rss_bytes': seal['process_peak_rss_bytes']}))


if __name__ == '__main__':
    main()
