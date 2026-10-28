#!/usr/bin/env python3
"""Trusted finite private Level3 exporter. No canonical IDs or runtime authority."""
from __future__ import annotations
import argparse
from fractions import Fraction
import hashlib,itertools,json,math,os,re,subprocess,sys
from pathlib import Path
BASE = 'fullscope-private-a-r01/level003-finite-exporter-r01'
SELF = 'Tools/' + BASE + '/export_level003.py'
PACKET = 'Build/fullscope-private-a-r01/level003-r01/packet.jsonl'
TXT = 'Notes/music/guitar project/TXT version/108_Finger_Permutations_Level_3_Odd_Count_String_Transfer.txt'
PDF = 'Notes/music/guitar project/PDF version/108_Finger_Permutations_Level_3_Odd_Count_String_Transfer.pdf'
BINDINGS = 'Build/' + BASE + '/trusted-bindings.json'
GUIDANCE = 'Build/' + BASE + '/source-guidance.json'
MAX_INT = (1 << 63) - 1
MAX_FILE_BYTES = 8 * 1024 * 1024
LOW_STRINGS = 'EADGBe'
OPEN_MIDI = dict(zip(LOW_STRINGS, (40,45,50,55,59,64)))
CODES = [''.join(x) for x in itertools.product('1234', repeat=4) if all(x[i] != x[i+1] for i in range(3))]
PAIRS = list(zip(LOW_STRINGS[:-1], LOW_STRINGS[1:])) + list(zip(LOW_STRINGS[:0:-1], LOW_STRINGS[-2::-1]))
PINS = {'Build/fullscope-private-a-r01/level003-r01/packet.jsonl': '17a6b272e593717b6eebca6f8f5f0affb58b04df3f3f2da145065f7243330af4', 'Notes/music/guitar project/TXT version/108_Finger_Permutations_Level_3_Odd_Count_String_Transfer.txt': '1bb8d5225f2db8df2b3ce518f10f28e11158592e0b5cbbb4c28af2742c861b4f', 'Notes/music/guitar project/PDF version/108_Finger_Permutations_Level_3_Odd_Count_String_Transfer.pdf': 'f04c1e49ce939ec83e5c80f9ad8cc81fd49da62e2039c25cac5367cea0fa6234', 'Build/fullscope-private-a-r01/level003-finite-exporter-r01/trusted-bindings.json': '2ac8aa7a9034c04218d00b562119905b37c6d7ae89e76e4cfae5299ff84110b8', 'Build/fullscope-private-a-r01/level003-finite-exporter-r01/source-guidance.json': '090e4231cdf09723956320dca90fb445246cac41207f264af981588214274b1c', 'Build/fullscope-private-a-r01/level003-finite-exporter-r01/original-pdf-page1.txt': '95319e4735664b0c2fe6efc6e04eb1d52db275d080c8955cd0a43330c9ad3edb'}
ROOT_KEYS = set('schema_version package_key source_identity level existing_parent_id source_refs source_payload implementation timing_authority unresolved_reasons provenance status'.split())
IMPLEMENTATION_KEYS = set('kind ordered_contacts task_steps ordered_rest_locations ordering_basis runtime_eligible canonical_ids_allocated mastery_or_credit relative_variants'.split())
CONTACT_KEYS = set('ordinal kind block_index grid_column string_label string_low_to_high fret finger onset_q duration_q midi annotations source_line source_column_1based technique_symbols same_column_contact_count attack_authority midi_basis'.split())
VARIANT_KEYS = set('start_stroke contact_ordinals strokes end_q basis'.split())

class Refusal(ValueError):
    def __init__(self, code: str, detail: str):
        self.code = code
        super().__init__(detail)

def need(condition, code, detail):
    if not condition:
        raise Refusal(code, detail)

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def canonical(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')

def strict_json(raw: bytes):
    need(len(raw) <= MAX_FILE_BYTES, 'INPUT_SIZE', 'JSON exceeds private input bound')
    def pairs(items):
        obj = {}
        for key, value in items:
            need(key not in obj, 'JSON_DUPLICATE_KEY', key)
            obj[key] = value
        return obj
    def nonfinite(token):
        raise Refusal('JSON_NONFINITE', token)
    def finite_float(token):
        value = float(token)
        need(math.isfinite(value), 'JSON_NONFINITE', token)
        return value
    def bounded_int(token):
        value = int(token)
        need(-MAX_INT <= value <= MAX_INT, 'JSON_INTEGER_OVERFLOW', token[:32])
        return value
    try:
        return json.loads(raw.decode('utf-8'), object_pairs_hook=pairs, parse_constant=nonfinite,
                          parse_float=finite_float, parse_int=bounded_int)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as error:
        raise Refusal('JSON_SYNTAX', str(error)) from error

def shape(value, keys, detail):
    need(type(value) is dict and set(value) == keys, 'UNSUPPORTED_FIELD', detail)

def reduced(n, d):
    need(type(n) is int and type(d) is int, 'RATIONAL_INTEGER', 'Exact integer pair required')
    need(n >= 0 and d > 0, 'RATIONAL_SIGN', 'Nonnegative numerator and positive denominator required')
    need(n <= MAX_INT and d <= MAX_INT, 'RATIONAL_OVERFLOW', 'Signed64 input component exceeded')
    divisor = math.gcd(n, d)
    return [n // divisor, d // divisor]

def source_quarter(value):
    need(type(value) in (int, float), 'RATIONAL_INTEGER', 'Legacy source metric value must be numeric')
    need(type(value) is int or math.isfinite(value), 'RATIONAL_NONFINITE', 'Finite source metric value required')
    q = Fraction(str(value))
    return reduced(q.numerator, q.denominator)

def verify_input_bytes(path, raw):
    need(path in PINS, 'UNREVIEWED_INPUT', path)
    need(len(raw) <= MAX_FILE_BYTES, 'INPUT_SIZE', path)
    need(sha(raw) == PINS[path], 'INPUT_SHA', path)
    return raw

def project_record(record, spec, binding):
    shape(record, ROOT_KEYS, 'source record')
    need(record['schema_version'] == 'fathom-private-source-implementation.1', 'UNSUPPORTED_SCHEMA', 'Source packet version')
    need(record['package_key'] == spec['package_key'] and record['source_identity'] == spec['source_identity'],
         'SOURCE_IDENTITY_ORDER', 'Missing/unreviewed/reordered source key')
    need(type(record['level']) is int and record['level'] == 3 and record['existing_parent_id'] == '2.3.1.1.1', 'SOURCE_SCOPE', 'Level/parent differs')
    need(record['source_payload']['exact_unit_lines'] == spec['unit'], 'SOURCE_TEXT', 'Exact original unit differs')
    need(record['unresolved_reasons'] == [], 'SOURCE_UNRESOLVED', 'No source conflict may be silently normalized')
    implementation = record['implementation']
    shape(implementation, IMPLEMENTATION_KEYS, 'implementation')
    need(implementation['kind'] == 'ordered_contact_transcription', 'UNSUPPORTED_KIND', 'Contact transcription required')
    need(all(implementation[key] is False for key in ('runtime_eligible', 'canonical_ids_allocated', 'mastery_or_credit')),
         'NO_CREDIT', 'No capability, canonical IDs or credit may be asserted')
    need(implementation['ordered_rest_locations'] == [], 'SOURCE_REST', 'Selected continuous traversal has no rest')
    contacts = implementation['ordered_contacts']
    need(type(contacts) is list and len(contacts) == 40, 'CONTACT_COUNT', 'Exactly40 source contacts required')
    events = []
    for i, (contact, expected, token) in enumerate(zip(contacts, spec['contacts'], spec['tokens'])):
        shape(contact, CONTACT_KEYS, 'contact')
        string, fret, finger = expected
        need(contact['kind'] == 'printed_fret_contact', 'UNSUPPORTED_KIND', 'Printed contact required')
        need(contact['ordinal'] == i+1 and contact['string_label'] == string and contact['fret'] == fret and contact['finger'] == finger,
             'CONTACT_ORDER_VALUE', f"{spec['ordinal']}:{i+1}")
        need(contact['midi'] == OPEN_MIDI[string]+fret and contact['string_low_to_high'] == LOW_STRINGS.index(string)+1,
             'CONTACT_PITCH', f"{spec['ordinal']}:{i+1}")
        need((contact['grid_column'], contact['source_line'], contact['source_column_1based'], contact['block_index']) ==
             (token[0], token[3], token[4], token[5]), 'CONTACT_SOURCE_TOKEN', str(i+1))
        onset, duration = source_quarter(contact['onset_q']), source_quarter(contact['duration_q'])
        need(onset == reduced(i, 4) and duration == [1, 4], 'METRIC_GRID', 'Selected straight-sixteenth source metric changed')
        need(contact['annotations'] == {} and contact['technique_symbols'] == '' and contact['same_column_contact_count'] == 1,
             'CONTACT_TECHNIQUE', 'Unreviewed articulation or simultaneous contact')
        events.append({'source_ordinal': i+1, 'string_label': string, 'string_low_to_high': LOW_STRINGS.index(string)+1,
                       'fret': fret, 'finger': finger, 'written_standard_tuning_midi': OPEN_MIDI[string]+fret,
                       'onset_q': onset, 'metric_duration_q': duration, 'acoustic_gate_q': None,
                       'attack': 'picked', 'source_token': {'txt_line': token[3], 'column_1based': token[4], 'block': token[5]}})
    variants = implementation['relative_variants']
    need(type(variants) is list and len(variants) == 2, 'VARIANT_COUNT', 'Exactly two start variants required')
    output_variants = []
    for variant, start in zip(variants, ('D', 'U')):
        shape(variant, VARIANT_KEYS, 'variant')
        expected_strokes = [start if i % 2 == 0 else ('U' if start == 'D' else 'D') for i in range(40)]
        need(variant['start_stroke'] == start and variant['contact_ordinals'] == list(range(1, 41)) and variant['strokes'] == expected_strokes,
             'VARIANT_ORDER', 'Start, membership or declared alternating continuation differs')
        need(source_quarter(variant['end_q']) == [10, 1], 'METRIC_EXTENT', 'Full selected traversal ends atq10')
        output_variants.append({'source_local_label': 'start-'+start, 'start_stroke': start,
                                'event_ordinals': list(range(1, 41)), 'declared_strokes': expected_strokes, 'end_q': [10, 1]})
    timing = record['timing_authority']
    need(timing['fixed_bpm'] is None and timing['ascii_spacing_is_duration'] is False and
         timing['selected_projection'] == 'straight_sixteenth',
         'TIMING_AUTHORITY', 'Source option/BPM/ASCII timing assertion changed')
    need(source_quarter(timing['duration_q']) == [1, 4] and source_quarter(timing['end_q']) == [10, 1],
         'METRIC_EXTENT', 'Timing authority disagrees')
    need(binding['package_key'] == spec['package_key'] and binding['source_identity'] == spec['source_identity'] and
         binding['packet_line'] == spec['packet_line'], 'BINDING_IDENTITY', 'Review source binding differs')
    # Complete bound record equality also covers fields not projected by this adapter.
    need(sha(canonical(record)) == binding['record_sha256_sorted_keys'], 'BINDING_RECORD_SHA', 'Complete source record differs from trusted producer binding')
    return {'schema': 'fathom-private-level003-projection.1', 'status': 'NOT_ADMITTED',
            'package_key': spec['package_key'], 'source_identity': spec['source_identity'], 'level': 3,
            'mode': spec['mode'], 'split': [spec['split'], 4-spec['split']], 'set': spec['set'], 'source_exercise_ordinal': spec['ordinal'], 'printed_code': spec['code'],
            'source_refs': record['source_refs'], 'source_packet_line': spec['packet_line'],
            'source_record_sha256': binding['record_sha256_sorted_keys'], 'producer_binding_sha256': PINS[BINDINGS], 'independent_review': 'PENDING',
            'metric_unit': 'quarter', 'selected_projection': 'straight_sixteenth', 'selected_pass': 'second_equal_volume',
            'duration_semantics': 'metric_slot_not_acoustic_note_off', 'events': events, 'variants': output_variants,
            'unselected_first_pass': {'required_source_semantics': True, 'accent_event_ordinals': list(range(spec['split']+1,41,4)), 'accent': 'light landing accent; qualitative only', 'numeric_velocity': None, 'completed': False},
            'policy_ref': 'source-policy.json', 'runtime_admitted': False, 'canonical_ids_allocated': False,
            'learner_performance_observed': False, 'credit_awarded': False}

def read_bounded(root, relative):
    path = root / relative
    need(path.is_file() and not any(p.is_symlink() for p in [path, *path.parents] if p != root.parent),
         'INPUT_PATH', relative)
    with path.open('rb') as stream:
        data = stream.read(MAX_FILE_BYTES + 1)
    need(len(data) <= MAX_FILE_BYTES, 'INPUT_SIZE', relative)
    return data

def rational_pair(value):
    """Validate serialized rationals without accepting bools or noncanonical zero."""
    need(type(value) is list and len(value) == 2, 'RATIONAL_SHAPE', 'Pair required')
    normalized = reduced(*value)
    need(value == normalized, 'RATIONAL_NOT_REDUCED', 'Reduced pair required; zero is [0,1]')
    return normalized

def expected_source(txt):
    lines=txt.splitlines(); units=[]; mode=None; set_number=None
    for i,line in enumerate(lines):
        m=re.fullmatch(r'SET (\d) OF 9 - EXERCISES (\d{3})-(\d{3})',line)
        if m:
            set_number=int(m[1])
            need((int(m[2]),int(m[3]))==((set_number-1)*12+1,set_number*12),'SOURCE_SET','Range changed')
        m=re.fullmatch(r'MODE ([AB]) - (?:3\+1 LATE|1\+3 EARLY) TRANSFER',line)
        if m:mode=m[1]
        m=re.fullmatch(r'Exercise (\d{3}): ([1-4]{4})',line)
        if m:units.append((set_number,mode,int(m[1]),m[2],i))
    expected=[(s,m,i+1,CODES[i]) for s in range(1,10) for m in 'AB' for i in range((s-1)*12,s*12)]
    need([u[:4] for u in units]==expected,'SOURCE_CODE_ORDER','Exact 216 printed units required')
    specs=[]
    for packet_line,(set_number,mode,ordinal,code,start) in enumerate(units,1):
        unit=lines[start:start+15]
        need(unit[1]=='ASCEND' and unit[8]=='DESCEND','SOURCE_DIRECTION','Both directions required')
        tokens=[]
        for block,offset in enumerate((2,9),1):
            group=[]
            for local_row,line in enumerate(unit[offset:offset+6]):
                m=re.fullmatch(r'([eBGDAE])\|([5-8|\-]+)',line)
                need(m is not None,'SOURCE_GRAMMAR',line)
                for token in re.finditer('[5-8]',m[2]):
                    group.append((token.start(),m[1],int(token[0]),start+offset+local_row+1,token.start()+3,block))
            need(len(group)==20 and len({t[0] for t in group})==20,'SOURCE_CONTACT_COUNT',str(ordinal))
            tokens.extend(sorted(group))
        split=3 if mode=='A' else 1
        contacts=[(s,int(f)+4,int(f)) for pair in PAIRS for s,f in zip([pair[0]]*split+[pair[1]]*(4-split),code)]
        need([(t[1],t[2]) for t in tokens]==[(s,f) for s,f,_ in contacts],'SOURCE_ROUTE',str(ordinal))
        mode_slug='a-3-1-late-transfer' if mode=='A' else 'b-1-3-early-transfer'
        identity=f'printed:l003:set-{set_number}-of-9-exercises-{(set_number-1)*12+1:03}-{set_number*12:03}:mode-{mode_slug}:exercise-{ordinal:03}-{code}'
        specs.append(dict(source_identity=identity,package_key='proposed-'+identity.replace(':','-'),set=set_number,mode=mode,split=split,ordinal=ordinal,packet_line=packet_line,code=code,unit=unit,tokens=tokens,contacts=contacts))
    return specs

def compile_projection(rows, bindings, original_txt, guidance):
    need(type(rows) is list and len(rows)==216,'RECORD_COUNT','Exactly216 mode units required')
    keys=[row.get('package_key') if type(row) is dict else None for row in rows]
    need(all(type(k) is str for k in keys) and len(set(keys))==216,'DUPLICATE_OR_MISSING_KEY','216 unique keys required')
    need(sha(canonical(bindings)+b'\n')==PINS[BINDINGS],'BINDING_SHA','Trusted producer binding changed; independent review remains pending')
    need(sha(canonical(guidance)+b'\n')==PINS[GUIDANCE],'GUIDANCE_SHA','Exact complete source guidance required')
    need(sha(original_txt.encode())==PINS[TXT],'SOURCE_SHA','Exact source text required')
    specs=expected_source(original_txt)
    records=[project_record(r,s,b) for r,s,b in zip(rows,specs,bindings['records'])]
    need(len(records)==216,'BINDING_COVERAGE','Missing source binding')
    policy={'schema':'fathom-private-level003-policy.1','status':'NOT_ADMITTED',
        'printed':{'tuning':'standard','open_midi_low_to_high':[40,45,50,55,59,64],'fifth_position_finger_frets':{'1':5,'2':6,'3':7,'4':8},'mode_splits':{'A':[3,1],'B':[1,3]},'start_strokes':['D','U']},
        'selected_source_option':{'rhythm':'straight_sixteenth','metric_slot_q':[1,4],'pass':'second_equal_volume','numeric_velocity':None,'basis_txt_lines':[17,18,19]},
        'source_pick_rule':{'name':'strict_continuous_alternate_picking','basis_txt_lines':[12,13,17],'boundary_reset_claim':'Only emitted stroke sequence is specified; an observationally identical even-boundary calculation is equivalent.'},
        'unselected_required_semantics':guidance['unselected_required_semantics'],
        'source_guidance':guidance,
        'unspecified':{'fixed_bpm':None,'meter':None,'acoustic_sounding_gates':None,'active_capo':None,'performance_outcome':None,'numeric_velocity':None},
        'source_local_labels_are_canonical_ids':False,'canonical_ids_allocated':False,'runtime_admitted':False,'credit_awarded':False,'independent_review':'PENDING'}
    return records,policy

def load_inputs(root):
    raw={p:verify_input_bytes(p,read_bounded(root,p)) for p in PINS}
    rows=[strict_json(line) for line in raw[PACKET].splitlines()]
    records,policy=compile_projection(rows,strict_json(raw[BINDINGS]),raw[TXT].decode(),strict_json(raw[GUIDANCE]))
    inputs=[{'path':p,'bytes':len(b),'sha256':sha(b)} for p,b in sorted(raw.items())]
    code=read_bounded(root,SELF);inputs.append({'path':SELF,'bytes':len(code),'sha256':sha(code)})
    return records,policy,inputs

def export_bundle(root:Path,destination:Path):
    root=root.resolve(strict=True)
    try:git_root=Path(subprocess.check_output(['git','-C',str(root),'rev-parse','--show-toplevel'],text=True).strip()).resolve()
    except subprocess.CalledProcessError as error:raise Refusal('ROOT','Git root required') from error
    need(root==git_root,'ROOT','Use repository root')
    allowed=root/'Build'/BASE
    destination=destination if destination.is_absolute() else root/destination
    need(not destination.exists() and not destination.is_symlink(),'OUTPUT_EXISTS',str(destination))
    resolved=destination.parent.resolve(strict=True)/destination.name
    need(allowed.resolve() in resolved.parents,'OUTPUT_SCOPE','Exclusive private Build root required')
    need(all(not p.is_symlink() for p in [destination.parent,*destination.parent.parents]),'OUTPUT_PATH','Symlink parent refused')
    records,policy,inputs=load_inputs(root)
    files={'records.jsonl':b''.join(canonical(r)+b'\n' for r in records),'source-policy.json':canonical(policy)+b'\n'}
    counts={'records':len(records),'contacts':sum(len(r['events']) for r in records),'variants':sum(len(r['variants']) for r in records),'variant_memberships':sum(len(v['event_ordinals']) for r in records for v in r['variants'])}
    need(counts=={'records':216,'contacts':8640,'variants':432,'variant_memberships':17280},'OUTPUT_COUNTS','Finite coverage mismatch')
    manifest={'schema':'fathom-private-finite-export-manifest.1','status':'NOT_ADMITTED','counts':counts,'inputs':inputs,'files':[{'path':n,'bytes':len(b),'sha256':sha(b)} for n,b in sorted(files.items())],'manifest_self_excluded':True,'canonical_ids_allocated':False,'runtime_admitted':False,'credit_awarded':False,'independent_review':'PENDING'}
    manifest_bytes=canonical(manifest)+b'\n'
    # No directory on input refusal. Payloads are exclusive creations; only a fully
    # written, verified manifest is linked to its final name as publication marker.
    try:
        resolved.mkdir()
        for name,data in files.items():
            with (resolved/name).open('xb') as stream:stream.write(data)
            need((resolved/name).read_bytes()==data,'OUTPUT_WRITE_INCOMPLETE',name)
        pending=resolved/'manifest.pending'
        with pending.open('xb') as stream:
            stream.write(manifest_bytes);stream.flush();os.fsync(stream.fileno())
        need(pending.read_bytes()==manifest_bytes,'OUTPUT_WRITE_INCOMPLETE','manifest')
        os.link(pending,resolved/'manifest.json',follow_symlinks=False)
    except FileExistsError as error:raise Refusal('OUTPUT_EXISTS',str(resolved)) from error
    except OSError as error:raise Refusal('OUTPUT_WRITE_INCOMPLETE',str(resolved)) from error
    # Publication succeeded. Cleanup failure is not a failed publication; the
    # pending marker is explicitly nonauthoritative and excluded from payloads.
    try:pending.unlink()
    except OSError:pass
    files['manifest.json']=manifest_bytes
    return {'status':'NOT_ADMITTED','output':str(resolved.relative_to(root)),'counts':counts,'files':[{'path':n,'bytes':len(b),'sha256':sha(b)} for n,b in sorted(files.items())]}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    try:result=export_bundle(a.root,a.output)
    except (Refusal,KeyError,TypeError,IndexError,OSError,ValueError,RecursionError) as error:
        print(json.dumps({'status':'REFUSED','code':getattr(error,'code','INPUT_SHAPE_OR_IO'),'detail':str(error)},sort_keys=True));return 2
    print(json.dumps(result,sort_keys=True));return 0
if __name__=='__main__':sys.exit(main())
