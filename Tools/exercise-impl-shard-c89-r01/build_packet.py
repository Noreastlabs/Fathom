#!/usr/bin/env python3
"""Build the exact private Level 89 interpretation packet from pinned source rows."""
import hashlib
import json
import re
import resource
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NAME = 'exercise-impl-shard-c89-r01'
RES = ROOT / 'Prompts/manager-resume-r01/mass-implementation-shards-r03/shard-c89-reservation.json'
BASE = ROOT / 'Build/fullscope-private-c-r01/level089-r06/implementation-packet.jsonl'
OUT = ROOT / 'Build' / NAME
RESULT = ROOT / 'Results' / NAME
PINS = {
    'Prompts/manager-resume-r01/mass-implementation-shards-r03/shard-c89-reservation.json': '4562628000ac5784dd7fed7273326d219f0fc3f09d3b1170bb2ce3541c78aeb6',
    'Prompts/manager-resume-r01/mass-implementation-shards-r03/shard-c89-full-template-prompt.md': 'ee6248c7a9a6ba4f72e51c272172566388d5baaff742187cd69349d035f75016',
    'Results/level-oracle/exercise-completeness-r01/reviewed-handoff-r01/wbs-annex-candidate.jsonl': 'dc285a946a929ba08a7e0e1075d56f9c2eb53ce2dfa9c70ea67d34270d2bda6c',
    'Planning/Fathom-Exercise-WBS-Annex-v1.json': 'a76f5ca0b6bae1bf793cd9867b67f27dfa35e95f8a0596bc0eb1fe756ea67ce1',
    'Results/fullscope-private-c-r01/range-category-index-r06.json': 'f282df4d03d28ca8590ea3ca20ac0466c876390fbdd1309f186b9899bd3261d7',
    'Build/fullscope-private-c-r01/level089-r06/implementation-packet.jsonl': '7cbe6475332f9be880e0b9990adbd2fc6f5b2b0315d9c42be0fcce2d03734a85',
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify():
    for rel, digest in PINS.items():
        assert sha(ROOT / rel) == digest, f'pinned input drift: {rel}'
    assert 'OPEN_AT_MANAGER_DISPATCH' in (ROOT / 'Prompts/parallel-02/Lane-Reservations-Current.md').read_text().split('## ', 2)[1]
    reservation = json.loads(RES.read_text())
    keys = reservation['keys']
    assert len(keys) == len(set(keys)) == 78
    joined = ('\n'.join(sorted(keys))+'\n').encode()
    assert hashlib.sha256(joined).hexdigest() == reservation['key_set_sha256']
    rows = {row['package_key']: row for row in map(json.loads, BASE.read_text().splitlines()) if row['package_key'] in keys}
    assert set(rows) == set(keys)
    for row in rows.values():
        assert row['source_identity'] == row['package_key'].split('/', 1)[1]
        assert row['level'] == 89
        for ref in row['source_refs']:
            p = ROOT / ref['path']
            assert p.stat().st_size == ref['bytes'] and sha(p) == ref['sha256'], f'original drift: {p}'
        assert row['source_payload']['pdf_region_text']
        assert row['source_refs'][0]['locator']['physical_pages']
    return keys, rows


def contact(role, label, pos=None, timing=None, technique=None, strings=None, frets=None, fingers=None, condition=None):
    return {k: v for k, v in {'role': role, 'printed': label, 'position': pos, 'timing': timing,
                             'technique': technique, 'strings': strings, 'frets': frets,
                             'right_hand': fingers, 'condition': condition}.items() if v is not None}


def interpret(row):
    identity = row['source_identity']
    page = int(re.search(r'/p(\d+)', identity).group(1))
    task = row['implementation']['task']
    fields = task.get('printed_components', [])
    line = row['source_payload']['pdf_region_text']
    contacts, roles, choices, unresolved, conflicts = [], [], [], [], []
    timing = {'absolute_bpm': None, 'relative_authority': None, 'fixed_onsets': False, 'fixed_durations': False}
    delivery = 'manual_parameterized_practice'
    if page == 3:
        notes = fields[1].split('-')
        contacts = [contact('bass', n, i + 1, f'count {i+1}') for i, n in enumerate(notes)]
        timing['relative_authority'] = 'four printed count positions 1-2-3-4'
        roles = ['play bass pattern alone before adding any chord']
        choices = ['bass octave, string, fret, fingering, tempo, and any later chord voicing']
    elif page == 4:
        contacts = [contact('rest' if v == 'rest' else ('bass' if 'bass' in v else 'upper'), v, i + 1, f'beat {i+1}') for i, v in enumerate(fields[1:5])]
        timing['relative_authority'] = 'printed Beat 1 through Beat 4 table columns'
        choices = ['specific chord, voicing, octave, string, fret and tempo']
        if 'next-chord pickup' in fields: unresolved.append('pickup subdivision and destination chord are not fixed')
    elif page == 5:
        pattern = fields[1]
        if pattern == 'Boom - Chuck - Boom - Chuck -':
            labels = pattern.split()
        elif pattern == 'Boom high-chuck Boom low-chuck':
            labels = ['Boom', 'high-chuck', 'Boom', 'low-chuck']
        else:
            labels = pattern.split()
        for i, v in enumerate(labels):
            role = 'rest_or_sustain' if v == '-' else 'muted' if v == 'x' else 'bass' if v == 'Boom' else 'upper'
            contacts.append(contact(role, v, i + 1, 'ordered source cell position'))
        timing['relative_authority'] = fields[2]
        if len(labels) == 4 and not ('&' in pattern): timing['relative_authority'] += '; four ordered quarter-pulse roles'
        choices = ['chord and bass pitch realization, tempo and exact contact duration']
        if '&' in pattern: unresolved.append('late & pickup is named but full within-bar onset map is not supplied')
    elif page == 6:
        grid = fields[1].split()
        contacts = [contact('accented_contact' if v == 'P' else 'muted_subdivision', v, i+1, 'ordered grid slot') for i, v in enumerate(grid)]
        timing['relative_authority'] = f'{len(grid)} ordered printed grid slots; {fields[2]}'
        roles = ['keep hand moving through muted subdivisions and rests']
        choices = ['accent pitch, chord/bass selection, tempo and exact grid-to-clock realization']
    elif page == 7:
        harmony = fields[0].split('-')
        contacts = [contact('harmony_landmark', h, i+1, 'printed progression order') for i, h in enumerate(harmony)]
        roles = [fields[1], fields[2]]
        if 'guitar rests during fill' in fields[2]:
            contacts.append(contact('upper_guitar_rest', 'guitar rests during fill', len(contacts)+1, 'during beat-4 bass fill'))
        timing['relative_authority'] = fields[2] if ('beat' in fields[2] or '&' in fields[2]) else 'progression order only'
        choices = ['number of bars per harmony, bass pitches/octaves, chord voicings and tempo']
    elif page == 8:
        axes, hand = fields[1], fields[2]
        if page == 8 and len(re.findall(r'\b(?:low E|A|D|G|B|e)\b', axes)) >= 3:
            string_order = re.findall(r'low E|\b[ADGBe]\b', axes)
            finger_order = hand.split('-')
            contacts = [contact('string_contact', s, i+1, 'printed contact order', strings=[s], fingers=[finger_order[i]]) for i, s in enumerate(string_order)]
        elif fields[0] == '7':
            contacts = [contact('simultaneous_bass_and_upper_dyad', axes, 1, 'simultaneous', fingers=['P','m','a'])]
        else:
            finger_order = hand.split('-')
            labels = [x.strip() for x in axes.split(' - ')]
            contacts = [contact('bass' if 'bass' in v else 'upper', v, i+1, 'printed contact order', fingers=[finger_order[i]]) for i,v in enumerate(labels)]
        timing['relative_authority'] = 'printed order/simultaneity only'
        choices = ['actual bass/high/middle strings where generic, all frets and pitches, tempo and spacing']
    elif page == 9:
        pairs = fields[1].split(' -> ')
        for i, pair in enumerate(pairs):
            m = re.fullmatch(r'([GBe])(\d+)/([GBe])(\d+)', pair)
            assert m, pair
            contacts.append(contact('simultaneous_double_stop', pair, i+1, 'printed route order', strings=[m[1],m[3]], frets=[int(m[2]),int(m[4])]))
        timing['relative_authority'] = 'printed double-stop route order; no fixed onset spacing'
        choices = ['rhythmic spacing, technique/finger assignment, tempo and relationship to bass']
    elif page == 10:
        roles = fields[1:]
        timing['relative_authority'] = fields[2]
        if 'held chord' in fields[1]:
            contacts.append(contact('held_chord', fields[1], 1, 'before pickup'))
        if 'rested beat 4' in fields[1]:
            contacts.append(contact('rest', fields[1], 1, 'beat 4'))
        contacts.append(contact('double_stop_answer', fields[2], len(contacts)+1, fields[2], condition='only if bass is silent' if 'only if bass is silent' in fields[2] else None))
        choices = ['double-stop pitch, string/fret, preceding question realization and tempo']
        if 'pickup' in fields[2]: unresolved.append('pickup onset and destination voicing are not fixed')
    elif page == 11:
        notes = fields[1].split('-')
        contacts = [contact('bass_run', n, i+1, 'printed run order') for i,n in enumerate(notes)]
        timing['relative_authority'] = fields[2]
        choices = ['octave/string/fret/fingering and pre-arrival spacing']
        if len(notes) != 4: unresolved.append('five-note run has no fixed subdivision map')
    elif page == 12:
        roles = fields
        timing['relative_authority'] = f'fill window {fields[0]}; return {fields[2]}'
        if fields[0] == 'no window':
            contacts = [contact('rest', 'do not force a fill', 1, 'entire unavailable window')]
        else:
            contacts = [contact('bounded_fill', fields[1], 1, fields[0])]
        choices = ['actual fill pitches/voicing, spacing and tempo'] if fields[0] != 'no window' else []
    elif page == 13:
        harmony = fields[1].split('-')
        contacts = [contact('harmony_landmark', h, i+1, 'progression order') for i,h in enumerate(harmony)]
        roles = [fields[0], fields[2]]
        timing['relative_authority'] = 'four printed harmony landmarks; pocket behavior text'
        choices = ['bar allocation, notes/voicings and tempo']
    elif page == 14:
        roles = ['use | G | C | D | G |', *fields[1:]]
        contacts = [contact('harmony_bar', h, i+1, f'bar {i+1}') for i,h in enumerate(['G','C','D','G'])]
        if fields[-1]=='none': contacts.append(contact('fill_rest', 'none', 5, 'no fill in this version'))
        timing['relative_authority'] = 'four printed bars | G | C | D | G |'
        choices = ['specific bass/upper contacts, voicings, fill notes and tempo']
    elif page == 19:
        delivery = 'manual_parameterized_32_bar_study'
        table = task['table_fields'][0]
        for source_row in table['rows']:
            bars, harmony, groove, engine, dynamic = source_row
            start,end=map(int,bars.split('-'))
            hs=harmony.split('-')
            assert len(hs)==4 and end-start==3
            for offset,h in enumerate(hs):
                contacts.append(contact('harmony_bar',h,start+offset,f'bar {start+offset}',technique=groove))
            roles.append({'bars':bars,'groove':groove,'primary_engine':engine,'dynamic':dynamic})
        timing['relative_authority'] = '32 printed bars in eight four-bar sections; announce each new groove on beat 4 of preceding section; no reset bar; first five passes one master tempo'
        choices = ['master tempo value, meter/grid, bass notes/octaves, chord voicings, dyad locations, fills and exact subdivisions']
        unresolved.append('source table fixes form and groove role, not 32 bars of playable contact events')
    elif page == 20:
        delivery = 'manual_recovery_instruction'
        roles = [{'failure':fields[0], 'immediate_repair':fields[1]}]
        contacts = [contact('repair_action', fields[1], 1, 'on detected failure')]
        timing['relative_authority'] = 'conditional recovery; no fixed musical onset'
        choices = ['learner detection and execution']
    else:
        raise AssertionError(identity)
    if not contacts: raise AssertionError(f'empty semantics: {identity}')
    return {
        'schema_version':'fathom-private-level089-performance-contract.1',
        'package_key':row['package_key'], 'source_identity':identity,
        'source_refs':row['source_refs'], 'source_text':line,
        'source_context':task.get('page_introduction',''),
        'printed_fields':fields, 'source_roles':roles,
        'ordered_contacts':contacts, 'timing_authority':timing,
        'performer_choices':choices, 'unresolved':unresolved,
        'source_conflicts':conflicts, 'delivery_type':delivery,
        'refusals':{'automatic_score':False,'learner_performance_observed':False,
                    'credit_awarded':False,'mastery_awarded':False,'native_valid':False,
                    'installed_accepted':False,'invented_fixed_playback':False},
        'prior_c_packet_sha256':PINS['Build/fullscope-private-c-r01/level089-r06/implementation-packet.jsonl'],
    }


def main():
    keys, rows = verify()
    OUT.mkdir(parents=True, exist_ok=True)
    RESULT.mkdir(parents=True, exist_ok=True)
    all_rows = [interpret(rows[key]) for key in keys]
    completed=[]
    for batch_no, start in enumerate(range(0,78,26),1):
        batch=all_rows[start:start+26]
        p=OUT/f'packet-batch-{batch_no:02d}.jsonl'
        p.write_text(''.join(json.dumps(x,separators=(',',':'),ensure_ascii=False)+'\n' for x in batch))
        completed += [x['package_key'] for x in batch]
        checkpoint={'schema_version':'fathom-private-shard-checkpoint.1','batch':batch_no,
                    'packet':{'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':sha(p)},
                    'completed_count':len(completed),'completed_key_set_sha256':hashlib.sha256('\n'.join(sorted(completed)).encode()).hexdigest(),
                    'remaining_keys':keys[len(completed):],
                    'memory':memory_proxy()}
        (RESULT/f'checkpoint-batch-{batch_no:02d}.json').write_text(json.dumps(checkpoint,indent=2)+'\n')
        if checkpoint['memory']['projected_gib']>=13: raise RuntimeError('13GiB memory guard reached; partial checkpoint retained')
    assert completed==keys
    manifest={'schema_version':'fathom-private-shard-seal.1','status':'PRIVATE_COMPLETE_LEASE_RELEASE_REQUESTED',
              'reservation_sha256':sha(RES),'key_count':78,'attempted':78,
              'source_backed_implemented':78,'manual_or_choice':78,'unresolved_or_conflict':sum(bool(x['unresolved'] or x['source_conflicts']) for x in all_rows),
              'remaining_keys':[],'packets':[{'path':str(p.relative_to(ROOT)),'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(OUT.glob('packet-batch-*.jsonl'))],
              'native_valid':0,'integrated':0,'independently_reviewed':0,'installed_accepted':0,'accepted_count_increment':0,
              'later_admission_candidate':{'key':keys[0], 'reason':'four printed bass tones on four count positions',
                 'missing_gates':['independent source review','chosen register/string/fret/fingering and tempo','controlled P02 identity/queue admission','native validation','installed no-credit proof','different acceptance review']}}
    (RESULT/'seal.json').write_text(json.dumps(manifest,indent=2)+'\n')


def memory_proxy():
    vm=subprocess.run(['vm_stat'],capture_output=True,text=True,check=True).stdout
    values={}
    for line in vm.splitlines():
        m=re.match(r'(Pages active|Pages wired down|Pages occupied by compressor):\s+(\d+)',line)
        if m: values[m[1]]=int(m[2])
    gib=sum(values.values())*16384/2**30
    peak=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/2**30
    return {'active_wired_compressor_gib':round(gib,3),'process_peak_rss_gib':round(peak,3),'projected_gib':round(gib+peak,3)}


if __name__=='__main__': main()
