#!/usr/bin/env python3
"""Five completion-tone task contracts with exact source beat anchors."""
import copy
import datetime
import hashlib
import json
import re
import resource
import time
from pathlib import Path
import pdfplumber
from completion import build

ROOT = Path(__file__).resolve().parents[3]
LANE = 'fullscope-private-a-r01'
OLD, OUT = [ROOT / f'Build/{LANE}/level040-{r}' for r in ('r05', 'r06')]
RES = ROOT / f'Results/{LANE}/level040-r06'
PROMPT = ROOT / f'Prompts/{LANE}/level040-completion-actions-r01/full-template-prompt.md'


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
    assert ref(OLD / 'packet.jsonl')['sha256'] == '8a218a469bcb7e8c9de626dbaf473be85978703c66ab072e65916f23b29c9cf7'
    manifest = ROOT / f'Results/{LANE}/level040-r05/artifact-manifest.json'
    assert ref(manifest)['sha256'] == 'd78329c42cbbfb1fe1af92ebbf5d6e070d60e83c95b9463c94bb6cc784f8e155'
    assert ref(PROMPT)['sha256'] == 'd3428f2b6b0790f1360bc182ebec1a2ee6e26fd2419279e3568d5e58aac0825a'
    if OUT.exists() or RES.exists():
        raise FileExistsError('Fresh output roots required')
    raw = (OLD / 'packet.jsonl').read_text().splitlines(keepends=True)
    records = [json.loads(s) for s in raw]
    originals = [{k: v for k, v in x.items() if k != 'locator'} for x in records[47]['source_refs'][:2]]
    assert all(ref(ROOT / x['path']) == x for x in originals)
    text = (ROOT / originals[0]['path']).read_text().splitlines()
    with pdfplumber.open(ROOT / originals[1]['path']) as pdf:
        pages = {n: pdf.pages[n - 1].extract_text() for n in [1, 2, 12, 13, 16]}
    normalized = {n: ' '.join(value.split()) for n, value in pages.items()}
    for n, phrase in [(12, 'D completes D major; G# completes E major.'),
                      (12, 'D and G# are chord-completion tones, not new pentatonic degrees.'),
                      (12, 'Beat 1 states D, then G#, then F#.'),
                      (13, 'Pass 1: fret D and G# directly. Pass 2: approach one completion tone by a slide while preserving its beat-1 arrival.'),
                      (16, 'COMPLETION TONE BLURS: fret D or G# directly before sliding or bending.')]:
        assert phrase in normalized[n], (n, phrase)
    checks = 5
    audit = []
    for row in range(48, 53):
        record = records[row - 1]
        before = copy.deepcopy(record)
        loc = record['source_refs'][0]['locator']
        assert text[loc['line_start'] - 1:loc['line_end']] == record['source_payload']['exact_unit_lines']
        page, local = (12, row - 48) if row <= 49 else (13, row - 50)
        notation = {x['label']: x['body'] for x in record['source_payload']['notation_blocks'][0]['notation_rows']}
        for label in ('Nte', 'F#m', 'Chd', 'Job', 'Out', 'Fng', 'e', 'B', 'G', 'D', 'A', 'E'):
            found = re.findall(r'^' + re.escape(label) + r'\|([^\s]+)', pages[page], re.M)
            assert found[local] == notation[label], (row, label)
            checks += 1
        contract = build(before)
        p = row - 47
        mapping = next(line for line in text if line.startswith(f'P{p}: D root at '))
        parsed = re.fullmatch(r'P\d: D root at ([EADGBe])(\d+) finger (\d); G# third at ([EADGBe])(\d+) finger (\d)\.', mapping)
        assert parsed
        d, sharp = contract['completion_targets']
        assert (d['string_label'], d['fret'], d['finger']) == (parsed[1], int(parsed[2]), int(parsed[3]))
        assert (sharp['string_label'], sharp['fret'], sharp['finger']) == (parsed[4], int(parsed[5]), int(parsed[6]))
        assert f'D({parsed[1]}{parsed[2]}) finger {parsed[3]}' in normalized[12]
        assert f'G#({parsed[4]}{parsed[5]}) finger {parsed[6]}' in normalized[12]
        contract['source_authority'] = {'originals': originals, 'txt_locator': loc,
            'pdf_grid_page': page, 'pdf_context_pages': [1, 2, 12, 13, 16],
            'scope': 'direct fretted pass, explicit beat-one anchors, completion boundary and unselected later duty'}
        record['implementation']['source_completion_cadence'] = contract
        record['provenance']['completion_cadence_supplement'] = {
            'predecessor_packet': ref(OLD / 'packet.jsonl'), 'predecessor_record_sha256': digest(before),
            'producer': ref(Path(__file__)), 'completion_code': ref(Path(__file__).with_name('completion.py')),
            'source_originals': originals, 'independent_review': False}
        assert {k: v for k, v in record['implementation'].items() if k != 'source_completion_cadence'} == before['implementation']
        for key in ('source_payload', 'timing_authority', 'status', 'unresolved_reasons'):
            assert record[key] == before[key]
        checks += 10
        audit.append({'row': row, 'package_key': record['package_key'], 'source_identity': record['source_identity'],
            'prior_record_canonical_sha256': digest(before), 'new_record_canonical_sha256': digest(record),
            'source_anchors': contract['explicit_source_beat_one_anchors'], 'later_slide_duty_present': p >= 3,
            'existing_source_music_timing_status_unchanged': True})
    assert sum(len(r['implementation']['ordered_contacts']) for r in records) == 580 and len(records) == 58
    OUT.mkdir()
    RES.mkdir()
    dump(OUT / 'original-completion-context.json', {'originals': originals, 'full_pdf_pages': pages,
        'source_txt_module_E_lines': {'start': 512, 'end': 590, 'lines': text[511:590]},
        'source_rhythm_repair_scope': 'PDF16 one quarter note per click is conditional rhythm-collapse repair, not selected for the printed cadence.',
        'later_source_pass_scope': 'Explicit per-position PDF13 slide pass applies P3–P5; no approach realization supplied.'})
    dump(OUT / 'changed-key-audit.json', audit)
    with (OUT / 'packet.jsonl').open('x') as out:
        for row, record in enumerate(records, 1):
            out.write(json.dumps(record, ensure_ascii=False, separators=(',', ':')) + '\n' if 48 <= row <= 52 else raw[row - 1])
    actual = (OUT / 'packet.jsonl').read_text().splitlines(keepends=True)
    assert all(actual[row - 1] == raw[row - 1] for row in range(1, 59) if not 48 <= row <= 52)
    context = json.loads((OLD / 'level-source-context.json').read_text())
    context['completion_cadence_source_actions'] = {'rows': list(range(48, 53)),
        'source_context': ref(OUT / 'original-completion-context.json'), 'beat_one_anchors': 15,
        'other_contact_beats_unselected': 45, 'later_slide_duties_unselected': 3,
        'native_projection_complete': False, 'readiness_changes': 0}
    dump(OUT / 'level-source-context.json', context)
    dump(OUT / 'remaining-keys.json', [])
    dump(RES / 'semantic-checks.json', {'status': 'PASS', 'source_and_preservation_checks': checks,
        'changed_rows': list(range(48, 53)), 'byte_identical_unrelated': 53, 'affected_contacts': 60,
        'explicit_source_beat_one_anchors': 15, 'other_contact_beats_unselected': 45,
        'outside_completion_occurrences': 10, 'later_slide_duties_unselected': 3,
        'whole_level_contacts_unchanged': 580, 'new_native_integrated_accepted': 0})
    previous = json.loads((ROOT / f'Results/{LANE}/level040-r05/seal.json').read_text())
    inputs = {x['path']: x for x in previous['source_inputs']}
    for path in [OLD / 'packet.jsonl', OLD / 'level-source-context.json', manifest, PROMPT, Path(__file__),
                 Path(__file__).with_name('completion.py'), OUT / 'original-completion-context.json', OUT / 'changed-key-audit.json']:
        entry = ref(path)
        inputs[entry['path']] = entry
    seal = {**previous, 'started_utc': start.isoformat(), 'ended_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'elapsed_seconds': time.perf_counter() - timer, 'process_peak_rss_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        'packet': ref(OUT / 'packet.jsonl'), 'context': ref(OUT / 'level-source-context.json'),
        'remaining_keys_reference': ref(OUT / 'remaining-keys.json'), 'source_inputs': list(inputs.values()),
        'targeted_checks': ref(RES / 'semantic-checks.json'),
        'command': 'Bundled Python -B Tools/fullscope-private-a-r01/level040-completion-actions-r01/produce.py',
        'limits': 'Only explicit source beat-one anchors known; metric spacing and acoustic gates unavailable. Later slide duty is unselected. Source notes/status/root-role correction unchanged.'}
    dump(RES / 'seal.json', seal)
    (RES / 'handoff.md').write_text('# Level 40 r06 — completion-tone task semantics\n\n'
        'Five Module E rows 48–52 bind the sixty existing notes to exact D-root, G#-third and F#-tonic duties. Fifteen bar/beat-one anchors are explicit source facts; the other forty-five contact beat positions and complete metric realization remain unselected. D/G# stay outside completion tones, with immediate return to the pentatonic pool, exact direct-fretted locations and fingers, and no invented additional tones. Job R remains harmonic root.\n\n'
        'The required later slide pass printed for P3–P5 is retained as an unselected duty: one D or G# arrival must keep beat one, while approach origin, attack, curve and time remain unknown. P1–P2 are not assigned that page-specific pass by analogy. The direct-fretting and conditional completion-blur instructions remain; no observed error, branch, scoring or performance is invented.\n\n'
        'All 58 identities and 580 contacts remain, with 53 unrelated record bytes identical. The earlier root-R correction seal stays immutable. Existing categories and source timing fields are unchanged; no independent acceptance, native/integrated/Accepted or learner credit is added. App/native/GUI and performed-music checks NOT_RUN. Producer remains OPEN_CONTINUING_IMPLEMENTATION_BACKLOG.\n')
    print(json.dumps({'packet': seal['packet'], 'checks': checks, 'runtime_seconds': seal['elapsed_seconds'],
                      'peak_rss_bytes': seal['process_peak_rss_bytes']}))


if __name__ == '__main__':
    main()
