#!/usr/bin/env python3
"""Five source-bound A-call/F#m-answer contracts; preserve unknown timing."""
import copy
import datetime
import hashlib
import json
import re
import resource
import time
from pathlib import Path
import pdfplumber
from response import build

ROOT = Path(__file__).resolve().parents[3]
LANE = 'fullscope-private-a-r01'
OLD, OUT = [ROOT / f'Build/{LANE}/level040-{r}' for r in ('r06', 'r07')]
RES = ROOT / f'Results/{LANE}/level040-r07'
PROMPT = ROOT / f'Prompts/{LANE}/level040-response-relations-r01/full-template-prompt.md'


def ref(path):
    path = Path(path)
    return {'path': str(path.relative_to(ROOT)), 'bytes': path.stat().st_size, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def dump(path, value):
    with path.open('x') as out:
        json.dump(value, out, ensure_ascii=False, indent=2)
        out.write('\n')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def main():
    start = datetime.datetime.now(datetime.timezone.utc)
    timer = time.perf_counter()
    assert ref(OLD / 'packet.jsonl')['sha256'] == 'fd3e73863c8dba95302167ff508f4568e2a9c52ddb476096641097cc9a663576'
    manifest = ROOT / f'Results/{LANE}/level040-r06/artifact-manifest.json'
    assert ref(manifest)['sha256'] == '9d0b230da85673ffe712dad7a9f5ae74b7260a4e992eff593c00b2978a8a26e7'
    assert ref(PROMPT)['sha256'] == 'd6777dced83024788e807d3891185be81e843c22f10cea56c1f1001b8d2d4585'
    if OUT.exists() or RES.exists():
        raise FileExistsError('Fresh output roots required')
    raw = (OLD / 'packet.jsonl').read_text().splitlines(keepends=True)
    records = [json.loads(s) for s in raw]
    originals = [{k: v for k, v in x.items() if k != 'locator'} for x in records[42]['source_refs'][:2]]
    assert all(ref(ROOT / x['path']) == x for x in originals)
    assert [x['sha256'] for x in originals] == ['e9e4db6227e4d3ea0ccb15162ccde0c4da337b1dcf65b67a2401e1aab63a6da7', '99484a66ca087544322c922f75c037649ac21b80a355d117b9ad9c524cf76923']
    text = (ROOT / originals[0]['path']).read_text().splitlines()
    crops = {}
    with pdfplumber.open(ROOT / originals[1]['path']) as pdf:
        pages = {n: pdf.pages[n - 1].extract_text() for n in [1, 2, 11, 16]}
        page = pdf.pages[10]
        heads = {w['text']: w for w in page.extract_words() if w['text'] in ['P1', 'P2', 'P3', 'P4', 'P5']}
        assert len(heads) == 5
        for pos in range(1, 6):
            head = heads[f'P{pos}']
            following = heads.get(f'P{pos + 2}')
            bottom = following['top'] if following else 590
            bbox = [head['x0'] - 2, head['top'], min(head['x0'] + 335, page.width), bottom]
            extracted = page.crop(bbox).filter(lambda char: char.get('fontname') == 'Courier').extract_text()
            crops[pos] = {'bbox_from_heading': bbox, 'font_filter': 'Courier', 'text': extracted}
    normalized = {n: ' '.join(value.split()) for n, value in pages.items()}
    phrases = [(11, 'Each call and answer share the same opening. The call resolves to A; the answer redirects the ending to F#.'),
               (11, 'The answer should sound related to the call, not like an unrelated lick with a different final note.'),
               (16, 'Pair its A call with its F#m answer.'),
               (16, 'make the A call and F#m answer sound like related but differently centered phrases'),
               (2, 'The same pitch changes function whenever the harmony changes.')]
    for n, phrase in phrases:
        assert phrase in normalized[n], (n, phrase)
    checks = len(phrases)
    audit = []
    for row in range(43, 48):
        record = records[row - 1]
        before = copy.deepcopy(record)
        loc = record['source_refs'][0]['locator']
        assert text[loc['line_start'] - 1:loc['line_end']] == record['source_payload']['exact_unit_lines']
        notation = {x['label']: x['body'] for x in record['source_payload']['notation_blocks'][0]['notation_rows']}
        pos = row - 42
        for label in ('Nte', 'F#m', 'Chd', 'Job', 'Fng', 'e', 'B', 'G', 'D', 'A', 'E'):
            found = re.findall(r'^' + re.escape(label) + r'\|([^\s]+)', crops[pos]['text'], re.M)
            assert found == [notation[label]], (row, label, found)
            checks += 1
        contract = build(before)
        contract['source_authority'] = {'originals': originals, 'txt_locator': loc,
            'pdf_grid_page': 11, 'pdf_context_pages': [1, 2, 11, 16],
            'scope': 'shared physical opening, changed chord roles, ordered call/answer endings and manual hearing duty',
            'pdf_grid_extraction': 'Original heading-derived column box; Courier-only glyphs separate the P5 empty E row from overlapping prose.'}
        record['implementation']['source_response_relationship'] = contract
        record['provenance']['relative_center_response_supplement'] = {
            'predecessor_packet': ref(OLD / 'packet.jsonl'), 'predecessor_record_sha256': digest(before),
            'producer': ref(Path(__file__)), 'response_code': ref(Path(__file__).with_name('response.py')),
            'source_originals': originals, 'independent_review': False}
        assert {k: v for k, v in record['implementation'].items() if k != 'source_response_relationship'} == before['implementation']
        for key in ('source_payload', 'timing_authority', 'status', 'unresolved_reasons'):
            assert record[key] == before[key]
        checks += 6
        audit.append({'row': row, 'package_key': record['package_key'], 'source_identity': record['source_identity'],
            'prior_record_canonical_sha256': digest(before), 'new_record_canonical_sha256': digest(record),
            'shared_opening_joins': 4, 'final_harmonic_root_duties': 2,
            'existing_source_music_timing_status_unchanged': True})
    assert sum(len(r['implementation']['ordered_contacts']) for r in records) == 580 and len(records) == 58
    OUT.mkdir()
    RES.mkdir()
    dump(OUT / 'original-response-context.json', {'originals': originals, 'full_pdf_pages': pages,
        'pdf_11_heading_derived_grid_extraction': crops,
        'source_txt_module_D_lines': {'start': 441, 'end': 508, 'lines': text[440:508]},
        'extraction_note': 'P5 empty low-E staff overlaps the prose footer in the original PDF. Courier glyph filtering recovers the unchanged printed row. This is layout separation, not a musical-source correction.',
        'source_rhythm_scope': 'PDF16 quarter note per click is conditional rhythm-collapse repair; not selected for these response cards. Six contacts do not establish six-eighth meter.',
        'context_scope': 'Full workbook progression/mastery context retained. No completed prior phase, backing track, perceived center, or learner result is inferred.'})
    dump(OUT / 'changed-key-audit.json', audit)
    with (OUT / 'packet.jsonl').open('x') as out:
        for row, record in enumerate(records, 1):
            out.write(json.dumps(record, ensure_ascii=False, separators=(',', ':')) + '\n' if 43 <= row <= 47 else raw[row - 1])
    actual = (OUT / 'packet.jsonl').read_text().splitlines(keepends=True)
    assert all(actual[row - 1] == raw[row - 1] for row in range(1, 59) if not 43 <= row <= 47)
    context = json.loads((OLD / 'level-source-context.json').read_text())
    context['relative_center_response_source_actions'] = {'rows': list(range(43, 48)),
        'source_context': ref(OUT / 'original-response-context.json'), 'shared_opening_joins': 20,
        'final_harmonic_root_duties': 10, 'numeric_clock_selected': False,
        'native_projection_complete': False, 'readiness_changes': 0}
    dump(OUT / 'level-source-context.json', context)
    dump(OUT / 'remaining-keys.json', [])
    dump(RES / 'semantic-checks.json', {'status': 'PASS', 'source_and_preservation_checks': checks,
        'changed_rows': list(range(43, 48)), 'byte_identical_unrelated': 53, 'affected_contacts': 60,
        'shared_opening_joins': 20, 'final_harmonic_root_duties': 10, 'pdf_notation_rows_checked': 55,
        'whole_level_contacts_unchanged': 580, 'new_native_integrated_accepted': 0})
    previous = json.loads((ROOT / f'Results/{LANE}/level040-r06/seal.json').read_text())
    inputs = {x['path']: x for x in previous['source_inputs']}
    for path in [OLD / 'packet.jsonl', OLD / 'level-source-context.json', manifest, PROMPT, Path(__file__),
                 Path(__file__).with_name('response.py'), OUT / 'original-response-context.json', OUT / 'changed-key-audit.json']:
        entry = ref(path)
        inputs[entry['path']] = entry
    seal = {**previous, 'started_utc': start.isoformat(), 'ended_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'elapsed_seconds': time.perf_counter() - timer, 'process_peak_rss_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        'packet': ref(OUT / 'packet.jsonl'), 'context': ref(OUT / 'level-source-context.json'),
        'remaining_keys_reference': ref(OUT / 'remaining-keys.json'), 'source_inputs': list(inputs.values()),
        'targeted_checks': ref(RES / 'semantic-checks.json'),
        'command': 'Bundled Python -B Tools/fullscope-private-a-r01/level040-response-relations-r01/produce.py',
        'limits': 'Phrase order and chord relationships resolved; no metric clock, acoustic gates or perceived hearing outcome. Existing source/status/root-role correction and completion supplement unchanged.'}
    dump(RES / 'seal.json', seal)
    (RES / 'handoff.md').write_text('# Level 40 r07 — relative-center response tasks\n\n'
        'Five Module D rows 43–47 bind sixty existing contacts into ordered A-call and F#m-answer phrases. Twenty shared-opening joins retain pitch, string, fret and finger while the chord roles change. Ten final contacts carry harmonic-root duties; Job R does not mean rest. The changed endings remain B→A and A→F#.\n\n'
        'The manual source duty is to make these related phrases sound differently centered. No hearing outcome or completed practice phase is claimed. Two six-contact groups do not establish a meter or duration. Numeric timing, acoustic gates, interphrase silence, velocity and accompaniment remain unselected. All 55 PDF notation rows matched TXT, including the P5 empty low-E row recovered by separating original Courier staff glyphs from overlapping prose. Full PDF 1/2/11/16 context remains pinned.\n\n'
        'All 58 identities and 580 contacts remain, with 53 unrelated record bytes identical, including the r06 completion-tone contracts. Categories remain 20 timed / 2 manual / 2 learner-choice / 34 partial. The r06 and earlier root-R seals stay immutable. Independent review/native/integrated/Accepted and learner credit are not added; app/native/GUI and performed-music checks are NOT_RUN. Producer remains OPEN_CONTINUING_IMPLEMENTATION_BACKLOG.\n')
    print(json.dumps({'packet': seal['packet'], 'checks': checks, 'runtime_seconds': seal['elapsed_seconds'],
                      'peak_rss_bytes': seal['process_peak_rss_bytes']}))


if __name__ == '__main__':
    main()
