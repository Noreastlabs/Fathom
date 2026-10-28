#!/usr/bin/env python3
"""Six finite source turnaround action and ending contracts."""
import copy, datetime, hashlib, json, re, resource, time
from pathlib import Path
import pdfplumber
from actions import build as actions
from endings import build as endings
ROOT = Path(__file__).resolve().parents[3]
LANE = 'fullscope-private-a-r01'
OLD, OUT = [ROOT / f'Build/{LANE}/level048-{r}' for r in ('r11', 'r12')]
RES = ROOT / f'Results/{LANE}/level048-r12'
PROMPT = ROOT / f'Prompts/{LANE}/level048-turnaround-actions-r01/full-template-prompt.md'


def ref(path):
    path = Path(path)
    return {'path': str(path.relative_to(ROOT)), 'bytes': path.stat().st_size, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def dump(path, value):
    with path.open('x') as out:
        json.dump(value, out, indent=2, ensure_ascii=False)
        out.write('\n')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def grid(body, width):
    result = []
    for bar, part in enumerate(body.split('|'), 1):
        if len(part) != width * 8:
            raise ValueError('Source bar width differs from eight count columns')
        for slot in range(8):
            token = part[slot * width:(slot + 1) * width].strip('-')
            if token:
                result.append([bar, slot, token])
    return result


def main():
    start = datetime.datetime.now(datetime.timezone.utc)
    timer = time.perf_counter()
    assert ref(OLD / 'packet.jsonl')['sha256'] == '56ba846bc14cc99b1f041e36f92a9cc39b587b723e5e29f07f3eff6e3613f7e4'
    assert ref(PROMPT)['sha256'] == '9fff543492bc14687c7983e3ec8fb1d259b26584c1b291404a50d8dda96bafc0'
    if OUT.exists() or RES.exists():
        raise FileExistsError('Fresh output roots required')
    raw = (OLD / 'packet.jsonl').read_text().splitlines(keepends=True)
    records = [json.loads(s) for s in raw]
    originals = [{k: v for k, v in x.items() if k != 'locator'} for x in records[26]['source_refs'][:2]]
    assert all(ref(ROOT / x['path']) == x for x in originals)
    text = (ROOT / originals[0]['path']).read_text().splitlines()
    with pdfplumber.open(ROOT / originals[1]['path']) as pdf:
        page = pdf.pages[17].extract_text()
    counts = {'sounding_events': 0, 'picked_excitation_groups': 0, 'unpicked_arrivals': 0, 'holds': 0, 'rest_slots': 0}
    audit, mismatches = [], []
    checks = 0
    for row in range(27, 33):
        record = records[row - 1]
        before = copy.deepcopy(record)
        loc = record['source_refs'][0]['locator']
        assert text[loc['line_start'] - 1:loc['line_end']] == record['source_payload']['exact_unit_lines']
        assert len(record['source_payload']['notation_blocks']) == 1
        block = record['source_payload']['notation_blocks'][0]
        checks += 2
        for label in ('Cnt', 'Nte', 'Deg', 'Rol', 'Atk', 'e', 'B', 'G', 'D', 'A', 'E'):
            original = [r for r in block['notation_rows'] if r['label'] == label]
            pdf_rows = re.findall(r'(?:^|\s)' + label + r'\|([^\s]+)', page)
            assert len(original) == 1 and len(pdf_rows) == 6
            assert grid(original[0]['body'], 5) == grid(pdf_rows[row - 27], 3), (row, label)
            checks += 1
        action = actions(record, row)
        ending = endings(record, row, action)
        assert record['source_payload']['printed_label'].split(': ', 1)[1] in page
        assert ending['source_closing_guidance'] in page
        checks += 2
        ending['source_pdf'] = originals[1]
        ending['physical_page'] = 18
        record['implementation']['symbolic_action_segments'] = action
        record['implementation']['source_gate_rule'] = action['source_gate_constraint']
        record['implementation']['source_turnaround_contract'] = ending
        if row == 32:
            mismatches.append({'row': row, 'package_key': record['package_key'], 'source_identity': record['source_identity'],
                'source_originals': originals, 'txt_line_locator': loc, 'physical_pdf_page': 18,
                'approach_event': ending['approach_event'], 'arrival_event': ending['arrival_event'],
                'reconciliation': ending['source_guidance_reconciliation']})
            record['unresolved_reasons'].append({'field': 'chromatic_approach_direction_wording', 'code': 'SOURCE_UNRESOLVED',
                'reason': 'Both original TXT/PDF say lower approach F to E, while literal A8(F3) to A7(E3) descends one semitone from above. Exact source text/traversal retained; no wording or pitch repair, Curriculum reconciliation pending.'})
        record['provenance']['turnaround_actions_supplement'] = {'predecessor': ref(OLD / 'packet.jsonl'),
            'producer': ref(Path(__file__)), 'action_code': ref(Path(__file__).with_name('actions.py')),
            'ending_code': ref(Path(__file__).with_name('endings.py')), 'source_originals': originals, 'independent_review': False}
        assert record['implementation']['ordered_contacts'] == before['implementation']['ordered_contacts']
        assert record['implementation']['sounding_events'] == before['implementation']['sounding_events']
        assert record['source_payload'] == before['source_payload']
        assert record['unresolved_reasons'][:len(before['unresolved_reasons'])] == before['unresolved_reasons']
        assert record['timing_authority'] == before['timing_authority'] and record['status'] == before['status']
        checks += 5
        for key, value in action['counts'].items():
            counts[key] += value
        audit.append({'row': row, 'package_key': record['package_key'], 'source_identity': record['source_identity'],
            'old_record_canonical_sha256': digest(before), 'new_record_canonical_sha256': digest(record),
            'source_counts': action['counts'], 'source_music_timing_status_unchanged': True,
            'new_source_guidance_reconciliation': row == 32})
    assert counts['sounding_events'] == 60 and counts['picked_excitation_groups'] == 57
    OUT.mkdir()
    RES.mkdir()
    dump(OUT / 'original-module-i-page.json', {'source_pdf': originals[1], 'physical_page': 18, 'full_page_text': page,
        'grid_method': 'Fixed source count-column widths TXT5/PDF3; preserves adjacent full-width Deg b6* and following5 as separate slots.'})
    dump(OUT / 'changed-key-audit.json', audit)
    dump(OUT / 'source-approach-wording-mismatch.json', mismatches)
    with (OUT / 'packet.jsonl').open('x') as out:
        for number, record in enumerate(records, 1):
            out.write(json.dumps(record, ensure_ascii=False, separators=(',', ':')) + '\n' if 27 <= number <= 32 else raw[number - 1])
    actual = (OUT / 'packet.jsonl').read_text().splitlines(keepends=True)
    assert all(actual[n - 1] == raw[n - 1] for n in range(1, 63) if not 27 <= n <= 32)
    context = json.loads((OLD / 'level-source-context.json').read_text())
    context['module_i_actions'] = {'rows': list(range(27, 33)), 'source': ref(OUT / 'original-module-i-page.json'),
        'guidance_reconciliation': ref(OUT / 'source-approach-wording-mismatch.json'), 'next_chorus_events_generated': False}
    dump(OUT / 'level-source-context.json', context)
    dump(OUT / 'remaining-keys.json', [])
    info = {'status': 'PASS', 'source_grid_instruction_preservation_checks': checks, 'changed_rows': list(range(27, 33)),
        'unchanged_record_bytes': 56, 'source_counts': counts, 'symbolic_slots': 96,
        'new_source_guidance_reconciliation_items': 1, 'readiness_and_status_changes': 0, 'new_independent_native_integrated_accepted': 0}
    dump(RES / 'semantic-checks.json', info)
    previous = json.loads((ROOT / f'Results/{LANE}/level048-r11/seal.json').read_text())
    inputs = {x['path']: x for x in previous['source_inputs']}
    for path in [OLD / 'packet.jsonl', OLD / 'level-source-context.json', PROMPT, Path(__file__), Path(__file__).with_name('actions.py'),
        Path(__file__).with_name('endings.py'), OUT / 'original-module-i-page.json', OUT / 'changed-key-audit.json', OUT / 'source-approach-wording-mismatch.json']:
        entry = ref(path)
        inputs[entry['path']] = entry
    seal = {**previous, 'started_utc': start.isoformat(), 'ended_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'elapsed_seconds': time.perf_counter() - timer, 'process_peak_rss_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        'packet': ref(OUT / 'packet.jsonl'), 'context': ref(OUT / 'level-source-context.json'),
        'remaining_keys_reference': ref(OUT / 'remaining-keys.json'), 'source_inputs': list(inputs.values()),
        'targeted_checks': ref(RES / 'semantic-checks.json'),
        'command': 'Bundled Python -B Tools/fullscope-private-a-r01/level048-turnaround-actions-r01/produce.py',
        'limits': 'Source ending/action semantics only; no next chorus, numeric groove/gates or source wording/pitch repair generated.'}
    dump(RES / 'seal.json', seal)
    (RES / 'handoff.md').write_text('# Level48 r12 — source turnaround actions\n\n'
        'Six exact ModuleI rows27–32 now bind60 events/57 picked groups across96 symbolic slots to source closing, re-entry, guide-tone, counted-silence and chromatic-support duties. Stop-time retains ten consecutive rest slots followed by the two printed G#/B attacks on bar2 beat4/offbeat. Eb resolves by source legato before E7; no numeric release curve is supplied. No new chorus or tonic event is generated.\n\n'
        'Row32 retains a concrete original wording seam: F is called a lower approach to E, while TAB A8(F3)→A7(E3) descends from one semitone above. Exact original text/notes remain and SOURCE_GUIDANCE_RECONCILIATION_PENDING is explicit; Curriculum disposition is required before any correction.\n\n'
        'All62 identities persist;56 unrelated records are byte-identical. Source music, typed source payload, timing and statuses are unchanged. Counts remain3manual/21choice/38partial. Numeric shuffle/onsets/gates and native playback remain unavailable; source acceptance/native/integrated/Accepted and learner credit do not increase. App/native/GUI/performance checks NOT_RUN.\n')
    print(json.dumps({'packet': seal['packet'], 'source_counts': counts, 'checks': checks,
        'runtime_seconds': seal['elapsed_seconds'], 'peak_rss_bytes': seal['process_peak_rss_bytes']}))


if __name__ == '__main__':
    main()
