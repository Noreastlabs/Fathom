#!/usr/bin/env python3
"""Freeze the reserved Level 59 source-grounded private manual contracts."""
import collections
import hashlib
import json
import pathlib
import re
import resource
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
RES = ROOT / 'Prompts/manager-resume-r01/mass-implementation-shards-r03/shard-b59-reservation.json'
INDEX = ROOT / 'Results/fullscope-private-b-r01/checkpoint-r03/range-index.json'
BASE = ROOT / 'Results/level-oracle/exercise-completeness-r01/reviewed-handoff-r01/wbs-annex-candidate.jsonl'
DESCRIPTOR = ROOT / 'Planning/Fathom-Exercise-WBS-Annex-v1.json'
SRC_DIR = ROOT / 'Notes/music/guitar project'
STEM = 'Guitar_Exercises_Section_VII_Level_59_Major_and_Minor_Triad_Arpeggios_Inversion_Starts_Alternate_and_Economy_Picking_and_Chord_Tone_Connections'
TXT = SRC_DIR / 'TXT version' / (STEM + '.txt')
PDF = SRC_DIR / 'PDF version' / (STEM + '.pdf')
OUT = ROOT / 'Results/exercise-impl-shard-b59-r01'
BUILD = ROOT / 'Build/exercise-impl-shard-b59-r01'
PINS = {
    RES: '773b0e486a389ba2e10ab2610fc1057166b8bf22ac56b5b595d277bccc46e212',
    INDEX: '3a367221ea2f831c7774720730a9876eb59bb2656766336047270c8e0ae22ce8',
    BASE: 'dc285a946a929ba08a7e0e1075d56f9c2eb53ce2dfa9c70ea67d34270d2bda6c',
    DESCRIPTOR: 'a76f5ca0b6bae1bf793cd9867b67f27dfa35e95f8a0596bc0eb1fe756ea67ce1',
    TXT: '7eea221134b4308f384c27d5ebd40c21430c44fe2aaca9332dadb0a6d6b77adb',
    PDF: '43b1b70a42f05b80aa575bf377735aa0ccec27889485864750b169ccef4305ba',
}
NOTES = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
OPEN = {6: 4, 5: 9, 4: 2, 3: 7, 2: 11, 1: 4}

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def rel(path):
    return path.relative_to(ROOT).as_posix()

def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n')

def memory_gib():
    data = subprocess.check_output(['vm_stat'], text=True)
    page = 16384
    m = re.search(r'page size of (\d+) bytes', data)
    if m:
        page = int(m.group(1))
    values = {}
    for line in data.splitlines():
        m = re.match(r'(.+?):\s+(\d+)\.', line)
        if m:
            values[m.group(1)] = int(m.group(2))
    active = values.get('Pages active', 0)
    wired = values.get('Pages wired down', 0)
    compressor = values.get('Pages occupied by compressor', 0)
    proxy = (active + wired + compressor) * page / 1024**3
    # macOS getrusage ru_maxrss is bytes.
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024**3
    return {'active_wired_occupied_compressor_gib': round(proxy, 3),
            'process_peak_rss_gib': round(peak, 3),
            'projected_gib': round(proxy + peak, 3)}

def main():
    assert all(sha(path) == digest for path, digest in PINS.items()), 'Pinned input/source hash drift'
    reservation = json.loads(RES.read_text())
    keys = reservation['keys']
    assert len(keys) == 106 and len(set(keys)) == 106
    assert hashlib.sha256(('\n'.join(sorted(keys)) + '\n').encode()).hexdigest() == reservation['key_set_sha256']
    index = json.loads(INDEX.read_text())
    indexed = {x['package_key']: x for x in index['children'] if x['package_key'] in keys}
    assert len(indexed) == 106 and all(x['category'] == 'implementation_or_interpretation_pending' for x in indexed.values())
    official = {}
    for line in BASE.read_text().splitlines():
        row = json.loads(line)
        if row['package_key'] in keys:
            assert row['package_key'] not in official
            official[row['package_key']] = row
    assert set(official) == set(keys), 'Official base key mismatch'
    overlays = {}
    for path in sorted((ROOT / 'Build/fullscope-private-b-r01').glob('finite-level059-*/implementation-overlay.jsonl')):
        for number, line in enumerate(path.read_text().splitlines(), 1):
            value = json.loads(line)
            key = value['package_key']
            if key in keys:
                assert key not in overlays, ('duplicate prior overlay', key)
                overlays[key] = (path, number, line, value)
    assert set(overlays) == set(keys), 'Missing prior finite implementation'
    txt_lines = TXT.read_text().splitlines()
    counts = collections.Counter()
    records = []
    for key in keys:
        path, number, line, old = overlays[key]
        refs = old['source_refs']
        txt_ref = next(r for r in refs if r['path'] == rel(TXT))
        pdf_ref = next(r for r in refs if r['path'] == rel(PDF))
        assert txt_ref['sha256'] == PINS[TXT] and pdf_ref['sha256'] == PINS[PDF]
        assert official[key]['exercise']['level'] == 59
        assert official[key]['existing_parent_id'] == old['existing_parent_id']
        assert official[key]['exercise']['pdf_sha256'] == PINS[PDF]
        tl = txt_ref.get('locator')
        pl = pdf_ref.get('locator')
        assert (pl and pl.get('physical_page') in range(1, 21)) or (
            pl is None and '/modulee/txt-l' in key), ('missing PDF locator', key)
        matches = []
        if tl:
            start, end = tl['line_start'], tl['line_end']
            assert 1 <= start <= end <= len(txt_lines)
            source_lines = txt_lines[start-1:end]
            excerpt = old['source_payload']['txt_excerpt'].splitlines()
            assert source_lines == excerpt, ('TXT source excerpt drift', key)
        else:
            # PDF9/10 cards have no unique TXT card. Preserve that difference.
            assert '/moduled/' in key or '/modulee/' in key
            source_lines = old['source_payload']['txt_excerpt'].splitlines()
            if source_lines:
                matches = [i+1 for i in range(len(txt_lines)-len(source_lines)+1)
                           if txt_lines[i:i+len(source_lines)] == source_lines]
                assert len(matches) >= 2, ('unlocated TXT excerpt was expected to be nonunique', key, matches)
        events = old['implementation']['events']
        assert events and [e['order'] for e in events] == list(range(1, len(events)+1)), key
        assert all(e.get('onset_q') is None and e.get('duration_q') is None for e in events), key
        contact_count = 0
        conflicts = []
        for event in events:
            for contact in event.get('members', [event]):
                if not {'string', 'fret', 'printed_note'} <= contact.keys():
                    continue
                contact_count += 1
                note = contact['printed_note']
                m = re.fullmatch(r'([A-G])([#b]?)', note)
                if m:
                    expected = (NOTES[m[1]] + {'':0, '#':1, 'b':-1}[m[2]]) % 12
                    actual = (OPEN[contact['string']] + contact['fret']) % 12
                    if expected != actual:
                        conflicts.append({'event_order': event['order'], 'printed_note': note,
                                          'string': contact['string'], 'fret': contact['fret'],
                                          'reason': 'printed note and standard-tuning contact disagree'})
        assert not conflicts, ('source contact conflict', key, conflicts)
        manual = old['implementation'].get('manual_execution_contract')
        assert manual and manual.get('steps') and manual.get('package_key') == key
        kind = old['implementation']['kind']
        counts[kind] += 1
        record = {
            'schema_version': 'fathom.private-level059-manual-contract.1',
            'package_key': key, 'source_identity': old['source_identity'], 'level': 59,
            'parent_wbs_id': old['existing_parent_id'],
            'delivery_type': 'source_grounded_manual_parameterized_nonplayback',
            'source': {'authority': ('matching_original_txt_and_pdf' if tl and pl else
                                     'original_txt_card_pdf_not_equated' if tl else
                                     'original_pdf_card_primary_txt_not_equated'),
                       'original_txt': {'path': rel(TXT), 'sha256': PINS[TXT], 'locator': tl,
                                        'exact_lines': source_lines,
                                        'nonunique_candidate_line_starts': matches},
                       'original_pdf': {'path': rel(PDF), 'sha256': PINS[PDF], 'locator': pl},
                       'source_discrepancy': old['source_payload'].get('source_discrepancy') or []},
            'printed_score': {'kind': kind, 'events': events,
                              'source_grids': old['implementation'].get('source_grids', []),
                              'contact_memberships': contact_count},
            'articulation_authority': {
                'printed_roles_in_event_order': [e.get('role') for e in events],
                'printed_pick_or_system_in_event_order': [e.get('pick') or e.get('system') for e in events],
                'rests': 'no numbered rest event in this card; no rest duration inferred',
                'holds': ('sustain final answer root for the remainder of the second bar; '
                          'numeric duration unavailable' if '/modulek/' in key else
                          'no numeric hold duration printed for this card'),
                'left_hand_fingering': 'unavailable; printed string and fret contacts do not prescribe fingers',
                'technique': kind,
            },
            'performer_contract': manual,
            'timing_authority': {'absolute_bpm': None, 'numeric_onsets': None,
                                 'numeric_durations': None,
                                 'relative': 'printed event order, pick sequence, bars or passes where explicitly printed',
                                 'unavailable': 'No local fixed BPM or numeric onset/duration authority; manual performance is not clock-scored.'},
            'performer_choices': {'tempo': 'performer_selected; source does not fix BPM',
                                  'silent_preparation_duration': 'performer_selected',
                                  'expression_and_contact_duration': 'performer_selected unless local hold instruction applies',
                                  'fixed_realization_claimed': False},
            'unresolved': old['unresolved_reasons'], 'conflicts': conflicts,
            'refusal': {'corrupt_or_identity_drift': 'reject',
                        'numeric_timing_or_unprinted_contact': 'reject',
                        'automatic_mastery_or_credit': 'reject'},
            'prior_private_implementation': {'path': rel(path), 'line': number,
                                              'record_sha256': hashlib.sha256(line.encode()).hexdigest()},
            'status': 'SOURCE_BACKED_PRIVATE_MANUAL_IMPLEMENTATION',
            'native_valid': False, 'installed_accepted': False, 'earned_credit': False,
        }
        records.append(record)
    assert sum(counts.values()) == 106
    OUT.mkdir(parents=True, exist_ok=True)
    BUILD.mkdir(parents=True, exist_ok=True)
    batch_size = 16
    batch_manifest = []
    for i in range(0, len(records), batch_size):
        batch = records[i:i+batch_size]
        ordinal = i // batch_size + 1
        path = OUT / f'contracts-batch-{ordinal:02}.jsonl'
        path.write_text(''.join(json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(',', ':'))+'\n' for x in batch))
        remaining = keys[i+len(batch):]
        measurement = memory_gib()
        checkpoint = {'batch': ordinal, 'first_key': batch[0]['package_key'],
                      'last_key': batch[-1]['package_key'], 'implemented': len(batch),
                      'cumulative_implemented': i+len(batch), 'remaining_count': len(remaining),
                      'remaining_keys_sha256': hashlib.sha256(('\n'.join(remaining)+'\n').encode()).hexdigest(),
                      'packet_path': rel(path), 'packet_sha256': sha(path), 'memory': measurement}
        cpath = OUT / f'checkpoint-batch-{ordinal:02}.json'
        write(cpath, checkpoint)
        batch_manifest.append({'packet_path': rel(path), 'packet_sha256': sha(path),
                               'checkpoint_path': rel(cpath), 'checkpoint_sha256': sha(cpath),
                               'key_count': len(batch)})
        if measurement['projected_gib'] >= 13:
            write(OUT/'resource_stop.json', {'reason': '13GiB resource guard', 'checkpoint': checkpoint})
            raise SystemExit('13GiB resource guard reached after checkpoint')
    final = {'schema_version': 'fathom.private-level059-packet-manifest.1',
             'reservation_path': rel(RES), 'reservation_sha256': PINS[RES],
             'key_set_sha256': reservation['key_set_sha256'], 'key_count': 106,
             'implemented': 106, 'manual_or_parameterized': 106,
             'unresolved': sum(bool(x['unresolved']) for x in records),
             'conflicts': sum(bool(x['conflicts']) for x in records), 'remaining_count': 0,
             'delivery_types': {'source_grounded_manual_parameterized_nonplayback': 106},
             'kinds': dict(counts), 'batches': batch_manifest,
             'candidate': {'key': keys[0], 'reason': 'Exact blocked triad and six-note mirror with source-bound contacts and manual preparation',
                           'missing_gates': ['independent musical/source review', 'P02 controlled case selection and ID allocation',
                                             'native reference validation and refusal proof', 'agent Curriculum admission',
                                             'installed Learn/Practice/Attempt/no-credit proof and independent installed review']},
             'accepted_increments': {'native_valid': 0, 'queue_selected': 0,
                                      'installed_accepted': 0, 'workbook': 0, 'wbs_parent': 0}}
    write(OUT/'packet-manifest.json', final)
    print(json.dumps({'manifest': rel(OUT/'packet-manifest.json'), 'manifest_sha256': sha(OUT/'packet-manifest.json'),
                      'implemented': 106, 'remaining': 0, 'kinds': dict(counts)}, sort_keys=True))

if __name__ == '__main__':
    main()
