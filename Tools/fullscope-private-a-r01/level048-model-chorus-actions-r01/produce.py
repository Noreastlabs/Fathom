#!/usr/bin/env python3
"""Two source model-chorus action/form contracts, no clock or gate invention."""
import copy, datetime, hashlib, json, re, resource, time
from pathlib import Path
import pdfplumber
from actions import build as actions
from chorus import build as chorus
ROOT = Path(__file__).resolve().parents[3]
LANE = 'fullscope-private-a-r01'
OLD = ROOT / f'Build/{LANE}/level048-r10'
OUT = ROOT / f'Build/{LANE}/level048-r11'
RES = ROOT / f'Results/{LANE}/level048-r11'
PROMPT = ROOT / f'Prompts/{LANE}/level048-model-chorus-actions-r01/full-template-prompt.md'


def ref(path):
    path = Path(path)
    return {'path': str(path.relative_to(ROOT)), 'bytes': path.stat().st_size, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def dump(path, value):
    with path.open('x') as out:
        json.dump(value, out, ensure_ascii=False, indent=2)
        out.write('\n')


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def grid(body, width):
    result = []
    for match in re.finditer(r'[^-]+', body):
        if match.start() % width:
            raise ValueError('Original grid token is not aligned with a count slot')
        result.append([match.start() // width, match.group()])
    return result


def main():
    start = datetime.datetime.now(datetime.timezone.utc)
    timer = time.perf_counter()
    assert ref(OLD / 'packet.jsonl')['sha256'] == '76cf6c3f8121cedc36542ead4e31bda3fd16c6f0d168aa7d07326d8721c6dd6b'
    assert ref(PROMPT)['sha256'] == '7cf57186b41121552bb74b84d37474e5d39d9bff083234e1ecc58e0843ed1d73'
    if OUT.exists() or RES.exists():
        raise FileExistsError('Fresh output roots required')
    raw = (OLD / 'packet.jsonl').read_text().splitlines(keepends=True)
    records = [json.loads(s) for s in raw]
    originals = [{k: v for k, v in x.items() if k != 'locator'} for x in records[23]['source_refs'][:2]]
    assert all(ref(ROOT / x['path']) == x for x in originals)
    source = (ROOT / originals[0]['path']).read_text().splitlines()
    with pdfplumber.open(ROOT / originals[1]['path']) as doc:
        pages = {n: doc.pages[n - 1].extract_text() for n in (12, 13, 16, 17)}
    audit = []
    checks = 0
    counts = {'sounding_events': 0, 'picked_excitation_groups': 0, 'unpicked_arrivals': 0, 'holds': 0, 'rest_slots': 0}
    for row, firstpage in [(24, 12), (26, 16)]:
        record = records[row - 1]
        before = copy.deepcopy(record)
        loc = record['source_refs'][0]['locator']
        assert source[loc['line_start'] - 1:loc['line_end']] == record['source_payload']['exact_unit_lines']
        assert len(record['source_payload']['notation_blocks']) == 12
        checks += 2
        for number, block in enumerate(record['source_payload']['notation_blocks'], 1):
            page = firstpage + (number - 1) // 6
            card = (number - 1) % 6
            for label in ('Cnt', 'Nte', 'Deg', 'Col', 'Rol', 'Atk', 'e', 'B', 'G', 'D', 'A', 'E'):
                original = [r for r in block['notation_rows'] if r['label'] == label]
                pdf_rows = re.findall(r'(?:^|\s)' + re.escape(label) + r'\|([^\s]+)', pages[page])
                assert len(original) == 1 and len(pdf_rows) == 6
                assert grid(original[0]['body'], 5) == grid(pdf_rows[card], 4), (row, number, label)
                checks += 1
        action = actions(record, row)
        form = chorus(record, row)
        for bar in form['bars']:
            page = firstpage + (bar['bar'] - 1) // 6
            assert f"{bar['bar']}. {bar['chord']} {bar['phrase_role']} - {bar['position']}" in pages[page]
            target = bar['beat_one_target']
            assert f"Beat-1 target: {target['source_note']} {target['role_text']}" in pages[page]
            checks += 2
        form['source_pdf'] = originals[1]
        form['physical_pages'] = [firstpage, firstpage + 1]
        record['implementation']['symbolic_action_segments'] = action
        record['implementation']['source_gate_rule'] = action['source_gate_constraint']
        record['implementation']['source_model_chorus'] = form
        record['provenance']['model_chorus_actions_supplement'] = {
            'predecessor': ref(OLD / 'packet.jsonl'), 'producer': ref(Path(__file__)),
            'action_code': ref(Path(__file__).with_name('actions.py')), 'form_code': ref(Path(__file__).with_name('chorus.py')),
            'source_originals': originals, 'independent_review': False}
        assert record['implementation']['ordered_contacts'] == before['implementation']['ordered_contacts']
        assert record['implementation']['sounding_events'] == before['implementation']['sounding_events']
        assert record['unresolved_reasons'] == before['unresolved_reasons']
        assert record['status'] == before['status'] and record['timing_authority'] == before['timing_authority']
        assert record['source_payload'] == before['source_payload']
        checks += 5
        for key, value in action['counts'].items():
            counts[key] += value
        audit.append({'row': row, 'package_key': record['package_key'], 'source_identity': record['source_identity'],
            'old_record_canonical_sha256': digest(before), 'new_record_canonical_sha256': digest(record),
            'source_counts': action['counts'], 'source_bars': 12, 'target_joins': 12,
            'contacts_timing_unresolved_status_unchanged': True})
    assert counts['sounding_events'] == 141 and counts['picked_excitation_groups'] == 130
    OUT.mkdir()
    RES.mkdir()
    dump(OUT / 'original-model-fh-pages.json', {'source_pdf': originals[1], 'pages': pages,
         'scope': 'Full physical-page text and finite column/token/header audit; no raster review claimed.'})
    dump(OUT / 'changed-key-audit.json', audit)
    with (OUT / 'packet.jsonl').open('x') as out:
        for number, record in enumerate(records, 1):
            out.write(json.dumps(record, ensure_ascii=False, separators=(',', ':')) + '\n' if number in (24, 26) else raw[number - 1])
    actual = (OUT / 'packet.jsonl').read_text().splitlines(keepends=True)
    assert all(actual[n - 1] == raw[n - 1] for n in range(1, 63) if n not in (24, 26))
    context = json.loads((OLD / 'level-source-context.json').read_text())
    context['model_chorus_actions_fh'] = {'rows': [24, 26], 'source_pages': ref(OUT / 'original-model-fh-pages.json'),
        'written_models_do_not_establish_free_capstone_completion': True, 'shuffle_ratio_selected': False}
    dump(OUT / 'level-source-context.json', context)
    dump(OUT / 'remaining-keys.json', [])
    info = {'status': 'PASS', 'source_grid_target_preservation_checks': checks, 'changed_rows': [24, 26],
        'unchanged_record_bytes': 60, 'source_counts': counts, 'symbolic_slots': 192, 'source_bar_target_joins': 24,
        'readiness_and_status_changes': 0, 'new_independent_native_integrated_accepted': 0}
    dump(RES / 'semantic-checks.json', info)
    previous = json.loads((ROOT / f'Results/{LANE}/level048-r10/seal.json').read_text())
    inputs = {x['path']: x for x in previous['source_inputs']}
    for path in [OLD / 'packet.jsonl', OLD / 'level-source-context.json', PROMPT, Path(__file__),
        Path(__file__).with_name('actions.py'), Path(__file__).with_name('chorus.py'),
        OUT / 'original-model-fh-pages.json', OUT / 'changed-key-audit.json']:
        entry = ref(path)
        inputs[entry['path']] = entry
    seal = {**previous, 'started_utc': start.isoformat(), 'ended_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'elapsed_seconds': time.perf_counter() - timer, 'process_peak_rss_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        'packet': ref(OUT / 'packet.jsonl'), 'context': ref(OUT / 'level-source-context.json'),
        'remaining_keys_reference': ref(OUT / 'remaining-keys.json'), 'source_inputs': list(inputs.values()),
        'targeted_checks': ref(RES / 'semantic-checks.json'),
        'command': 'Bundled Python -B Tools/fullscope-private-a-r01/level048-model-chorus-actions-r01/produce.py',
        'limits': 'Two printed model action/form contracts only; free capstone separate, numeric groove/gates unavailable, existing source guidance seams unchanged.'}
    dump(RES / 'seal.json', seal)
    (RES / 'handoff.md').write_text('# Level48 r11 — source model chorus actions F/H\n\n'
        'Exact rows24 and26 now implement141 source sounding events/130 picked groups across192 symbolic slots and24 source bars. Each bar joins chord, call/response role, printed position and beat-one target to its sounding event. ModelF minor-only pool and modelH G#-only-E7 scope are explicit; F# over A7 remains permitted where printed as13. Rest/hold/legato ownership is resolved symbolically.\n\n'
        'Original TXT and four full PDF pages were compared across all twelve table rows and24 bar headers/targets.60 unrelated records remain byte-identical; all contacts, source events, source_payload, unknown timing, unresolved guidance and statuses remain unchanged. ModelG expressive curves remain unselected and untouched.\n\n'
        'These printed demonstrations do not establish the free capstone task or learner completion. Exact shuffle ratio/numeric onsets/acoustic gates and native playback remain unavailable. Counts remain3manual/21choice/38partial; no source acceptance, native/integrated/Accepted or learner credit. App/native/GUI/performance checks NOT_RUN.\n')
    print(json.dumps({'packet': seal['packet'], 'source_counts': counts, 'checks': checks,
                      'runtime_seconds': seal['elapsed_seconds'], 'peak_rss_bytes': seal['process_peak_rss_bytes']}))


if __name__ == '__main__':
    main()
