#!/usr/bin/env python3
"""Bounded finite-export checks; no input mutation, native code, app or audio."""
from pathlib import Path
import argparse
import copy
import datetime
from fractions import Fraction
import hashlib
import importlib.util
import json
import math
import resource
import subprocess
import sys
import time
from unittest.mock import patch

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
BASE = 'fullscope-private-a-r01/level004-finite-exporter-r01'
spec = importlib.util.spec_from_file_location('level004_private_exporter', ROOT/'Tools'/BASE/'export_level004.py')
ex = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ex)
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--repeat-output', type=Path, default=ROOT/'Build'/BASE/'export-repeat-r01')
parser.add_argument('--result', type=Path, default=ROOT/'Results'/BASE/'validation-r01.json')
args = parser.parse_args()
repeat_output = args.repeat_output if args.repeat_output.is_absolute() else ROOT/args.repeat_output
result_output = args.result if args.result.is_absolute() else ROOT/args.result
if (ROOT/'Build'/BASE).resolve() not in repeat_output.resolve().parents or (ROOT/'Results'/BASE).resolve() not in result_output.resolve().parents:
    parser.error('Use exclusive output paths inside this private exporter Build/Results root')
if repeat_output.exists() or result_output.exists():
    parser.error('Retain prior evidence; choose fresh repeat/result paths')
checks = []
started = time.monotonic()

def check(name, condition):
    if not condition:
        raise AssertionError(name)
    checks.append({'check': name, 'result': 'PASS'})


def refuses(name, expected, call):
    try:
        call()
    except ex.Refusal as error:
        check(name + ' causal refusal', error.code == expected)
        checks[-1]['refusal_code'] = error.code
    else:
        raise AssertionError(name + ' unexpectedly succeeded')

raw = {p: ex.verify_input_bytes(p, ex.read_bounded(ROOT, p)) for p in ex.PINS}
rows = [ex.strict_json(line) for line in raw[ex.PACKET].splitlines()]
bindings = ex.strict_json(raw[ex.BINDINGS])
guidance = ex.strict_json(raw[ex.GUIDANCE])
original_txt = raw[ex.TXT].decode()
records, policy = ex.compile_projection(rows, bindings, original_txt, guidance)
check('exact108 unique source key coverage', len(records) == len({r['package_key'] for r in records}) == 108)
check('exact3456 contact coverage', sum(len(r['events']) for r in records) == 3456)
check('exact216 variants and6912 memberships', sum(len(r['variants']) for r in records) == 216 and
      sum(len(v['event_ordinals']) for r in records for v in r['variants']) == 6912)
check('trusted binding preserves ordered108 keys', [(r['package_key'],r['source_identity']) for r in records] ==
      [(r['package_key'],r['source_identity']) for r in bindings['records']])
all_rationals = [q for r in records for e in r['events'] for q in (e['onset_q'],e['metric_duration_q'])]
all_rationals += [v['end_q'] for r in records for v in r['variants']]
check('all executable rational fields use bounded reduced integer pairs', all(
    len(q)==2 and all(type(x) is int for x in q) and 0<=q[0]<=ex.MAX_INT and 0<q[1]<=ex.MAX_INT and math.gcd(*q)==1 for q in all_rationals))
check('all starts serialize canonical zero', all(r['events'][0]['onset_q']==[0,1] for r in records))
check('formerq2/4 contact nowq1/2', all(r['events'][2]['onset_q']==[1,2] for r in records))
check('exact original relative-time values preserved', all(Fraction(*e['onset_q'])==Fraction(i,4) and Fraction(*e['metric_duration_q'])==Fraction(1,4)
      for r in records for i,e in enumerate(r['events'])))
check('original source contact line/fret/string/pitch retained', all(
    e['fret']==source['fret'] and e['finger']==source['finger'] and e['string_low_to_high']==source['string_low_to_high'] and
    e['written_standard_tuning_midi']==source['midi'] and e['source_token']['txt_line']==source['source_line']
    for r,src in zip(records,rows) for e,source in zip(r['events'],src['implementation']['ordered_contacts'])))
check('every output explicitlyNOT_ADMITTED/no credit', all(r['status']=='NOT_ADMITTED' and not r['runtime_admitted'] and not r['canonical_ids_allocated'] and
      not r['learner_performance_observed'] and not r['credit_awarded'] for r in records))
check('unprinted sounding gates remainnull', all(e['acoustic_gate_q'] is None for r in records for e in r['events']))
check('unknown BPM/meter/capo/performance preserved', all(v is None for v in policy['unspecified'].values()))
check('source strict alternation retained', policy['source_pick_rule']['name']=='strict_continuous_alternate_picking')
check('14 complete guidance clauses retained', len(policy['source_guidance']['obligations'])==14 and policy['source_guidance']['limits']['automatic_credit'] is False)
check('unselected required rhythms and accent retained', policy['unselected_required_semantics']['other_rhythms']==['triplet','quintuplet'] and policy['unselected_required_semantics']['first_pass_landing_accents']==[2,4] and policy['unselected_required_semantics']['completion_claimed'] is False)
check('selected second pass distinct from first pass', all(r['selected_pass']=='second_equal_volume_equal_duration' and r['unselected_first_pass']['required_source_semantics'] and r['unselected_first_pass']['numeric_velocity'] is None and r['unselected_first_pass']['completed'] is False for r in records))
check('landing accent ordinals both crossings in all eight triples', all(r['unselected_first_pass']['accent_event_ordinals']==list(range(2,33,2)) for r in records))
check('all exact1+2+1 routes and only two start variants', all(r['note_count_split']==[1,2,1] and r['adjacent_triples']==['EAD','ADG','DGB','GBe','eBG','BGD','GDA','DAE'] and len(r['variants'])==2 for r in records))
check('equal-duration selection does not invent acoustic duration', all(r['duration_semantics']=='metric_slot_not_acoustic_note_off' and all(e['acoustic_gate_q'] is None for e in r['events']) for r in records))
check('muting physical guidance explicitly retained', 'Mute every unused string.' in next(x['text'] for x in guidance['obligations'] if x['key']=='quality_and_muting'))
check('later rhythms require unobserved crossing stability', guidance['unselected_required_semantics']['other_rhythms_condition']=='only after crossings stable; stability not observed' and guidance['limits']['observed_crossing_stability'] is None)
check('all physical baseline values remain unknown', all(guidance['limits'][k] is None for k in ['observed_clean_loops','observed_clean_days','observed_errors','observed_tension','observed_crossing_stability','observed_clean_level3_bpm']))
check('two alternatives do not imply generated opposite-start practice completion', guidance['unselected_required_semantics']['completion_claimed'] is False and 'not a generated64-contact session' in policy['two_variants_mean'])
check('qualitative volume never numeric velocity', policy['selected_source_option']['numeric_velocity'] is None and policy['unspecified']['numeric_velocity'] is None)
check('source PDF p1 retained fully', 'Advance after the complete set is clean with both pick starts' in policy['source_guidance']['original_pdf_page1_text'])
check('source-local variant labels are not canonical IDs', not policy['source_local_labels_are_canonical_ids'] and
      all(v['source_local_label'] in ('start-D','start-U') for r in records for v in r['variants']) and b'fg:item:' not in ex.canonical(records))
for pair,want in [((2,4),[1,2]),((0,4),[0,1]),((31,4),[31,4]),((ex.MAX_INT,ex.MAX_INT),[1,1])]:
    check('reduced pair '+str(pair),ex.reduced(*pair)==want)
for name,pair,code in [('zero denominator',(1,0),'RATIONAL_SIGN'),('negative denominator',(1,-4),'RATIONAL_SIGN'),
                       ('negative numerator',(-1,4),'RATIONAL_SIGN'),('float pair',(0.5,1),'RATIONAL_INTEGER'),
                       ('boolean pair',(True,4),'RATIONAL_INTEGER'),('numerator overflow',(ex.MAX_INT+1,4),'RATIONAL_OVERFLOW'),
                       ('denominator overflow',(0,ex.MAX_INT+1),'RATIONAL_OVERFLOW')]:
    refuses(name,code,lambda p=pair:ex.reduced(*p))
refuses('nonfinite legacy source','RATIONAL_NONFINITE',lambda:ex.source_quarter(float('inf')))
refuses('legacy decimal overflow','RATIONAL_OVERFLOW',lambda:ex.source_quarter(1e30))
refuses('duplicate JSON key','JSON_DUPLICATE_KEY',lambda:ex.strict_json(b'{"x":1,"x":2}'))
refuses('JSON NaN','JSON_NONFINITE',lambda:ex.strict_json(b'{"x":NaN}'))
for source in (ex.PACKET,ex.TXT,ex.PDF,ex.BINDINGS,ex.GUIDANCE):
    refuses('altered pin '+source,'INPUT_SHA',lambda source=source:ex.verify_input_bytes(source,raw[source]+b' '))
refuses('unknown input path','UNREVIEWED_INPUT',lambda:ex.verify_input_bytes('unknown.json',b'{}'))

def mutated(name, code, change):
    changed=copy.deepcopy(rows)
    change(changed)
    refuses(name,code,lambda:ex.compile_projection(changed,bindings,original_txt,guidance))

mutated('missing last record','RECORD_COUNT',lambda r:r.pop())
mutated('duplicate first key','DUPLICATE_OR_MISSING_KEY',lambda r:r.__setitem__(1,copy.deepcopy(r[0])))
mutated('unknown key','SOURCE_IDENTITY_ORDER',lambda r:r[1].__setitem__('package_key','unknown'))
mutated('wrong source order','SOURCE_IDENTITY_ORDER',lambda r:r.__setitem__(slice(0,2),list(reversed(r[:2]))))
mutated('unsupported record field','UNSUPPORTED_FIELD',lambda r:r[1].__setitem__('runtime_override',True))
mutated('unsupported contact kind','UNSUPPORTED_KIND',lambda r:r[1]['implementation']['ordered_contacts'][0].__setitem__('kind','guessed'))
mutated('changed fret','CONTACT_ORDER_VALUE',lambda r:r[1]['implementation']['ordered_contacts'][0].__setitem__('fret',8))
mutated('wrong written MIDI','CONTACT_PITCH',lambda r:r[1]['implementation']['ordered_contacts'][0].__setitem__('midi',46))
mutated('wrong source coordinate','CONTACT_SOURCE_TOKEN',lambda r:r[1]['implementation']['ordered_contacts'][0].__setitem__('source_line',100))
mutated('wrong note grid','METRIC_GRID',lambda r:r[1]['implementation']['ordered_contacts'][1].__setitem__('onset_q',0.5))
mutated('invented turn gap','METRIC_GRID',lambda r:r[1]['implementation']['ordered_contacts'][16].__setitem__('onset_q',5.0))
mutated('zero duration','METRIC_GRID',lambda r:r[1]['implementation']['ordered_contacts'][1].__setitem__('duration_q',0.0))
mutated('unknown contact field','UNSUPPORTED_FIELD',lambda r:r[1]['implementation']['ordered_contacts'][1].__setitem__('gate_q',[1,4]))
mutated('variant wrong start','VARIANT_ORDER',lambda r:r[1]['implementation']['relative_variants'][1]['strokes'].__setitem__(0,'D'))
mutated('variant missing event','VARIANT_ORDER',lambda r:r[1]['implementation']['relative_variants'][0]['contact_ordinals'].pop())
mutated('invented fixed BPM','TIMING_AUTHORITY',lambda r:r[1]['timing_authority'].__setitem__('fixed_bpm',120))
mutated('invented credit','NO_CREDIT',lambda r:r[1]['implementation'].__setitem__('mastery_or_credit',True))
mutated('unresolved source conflict','SOURCE_UNRESOLVED',lambda r:r[1].__setitem__('unresolved_reasons',['source conflict']))
mutated('unsupported nonprojected metadata','BINDING_RECORD_SHA',lambda r:r[1]['provenance'].__setitem__('admission','override'))
bad_guidance=copy.deepcopy(guidance);bad_guidance['obligations'].pop()
refuses('omit source guidance', 'GUIDANCE_SHA', lambda:ex.compile_projection(rows,bindings,original_txt,bad_guidance))
bad_binding=copy.deepcopy(bindings);bad_binding['records'][0]['record_sha256_sorted_keys']='0'*64
refuses('changed trusted binding', 'BINDING_SHA', lambda:ex.compile_projection(rows,bad_binding,original_txt,guidance))
for value,code in [([0,4],'RATIONAL_NOT_REDUCED'),([2,4],'RATIONAL_NOT_REDUCED'),([False,1],'RATIONAL_INTEGER'),([0.0,1],'RATIONAL_INTEGER'),([1,0],'RATIONAL_SIGN'),([1,ex.MAX_INT+1],'RATIONAL_OVERFLOW'),([1],'RATIONAL_SHAPE'),((1,4),'RATIONAL_SHAPE')]:
    refuses('strict serialized rational '+repr(value),code,lambda value=value:ex.rational_pair(value))
for value in ([0,1],[1,4],[1,2],[31,4]):check('canonical serialized rational '+repr(value),ex.rational_pair(value)==value)
for raw_json,code in [(b'{"x":1e999}','JSON_NONFINITE'),(b'{"x":Infinity}','JSON_NONFINITE'),(b'{"x":-Infinity}','JSON_NONFINITE'),(b'{"x":9223372036854775808}','JSON_INTEGER_OVERFLOW'),(b'{"x":-9223372036854775808}','JSON_INTEGER_OVERFLOW')]:
    refuses('strict JSON '+repr(raw_json),code,lambda raw_json=raw_json:ex.strict_json(raw_json))
mutated('boolean onset','RATIONAL_INTEGER',lambda r:r[0]['implementation']['ordered_contacts'][0].__setitem__('onset_q',False))
mutated('nonfinite duration','RATIONAL_NONFINITE',lambda r:r[0]['implementation']['ordered_contacts'][0].__setitem__('duration_q',float('nan')))
mutated('overflow onset','RATIONAL_OVERFLOW',lambda r:r[0]['implementation']['ordered_contacts'][0].__setitem__('onset_q',ex.MAX_INT+1))
mutated('first landing placed on first string','CONTACT_ORDER_VALUE',lambda r:r[0]['implementation']['ordered_contacts'][1].__setitem__('string_label','E'))
mutated('second landing placed on middle string','CONTACT_ORDER_VALUE',lambda r:r[0]['implementation']['ordered_contacts'][3].__setitem__('string_label','A'))
mutated('1+3 mode substituted for1+2+1 relay','CONTACT_ORDER_VALUE',lambda r:r[0]['implementation']['ordered_contacts'][3].__setitem__('string_label','A'))
mutated('repeat preceding stroke at first crossing landing2','VARIANT_ORDER',lambda r:r[0]['implementation']['relative_variants'][0]['strokes'].__setitem__(1,'D'))
mutated('repeat preceding stroke at second crossing landing4','VARIANT_ORDER',lambda r:r[0]['implementation']['relative_variants'][0]['strokes'].__setitem__(3,'D'))
mutated('wrong emitted stroke at turn17','VARIANT_ORDER',lambda r:r[0]['implementation']['relative_variants'][0]['strokes'].__setitem__(16,'U'))
equivalent=copy.deepcopy(rows)
for row in equivalent:
    for v in row['implementation']['relative_variants']:
        # A same-start calculation at either even16contact direction is identical.
        start=v['start_stroke'];other='U' if start=='D' else 'D'
        v['strokes']=[start if (i%16)%2==0 else other for i in range(32)]
check('equivalent even-boundary calculation is accepted',ex.compile_projection(equivalent,bindings,original_txt,guidance)==(records,policy))
mutated('invented acoustic gate field','UNSUPPORTED_FIELD',lambda r:r[0]['implementation']['ordered_contacts'][0].__setitem__('acoustic_gate_q',[1,4]))
mutated('invented numeric velocity','UNSUPPORTED_FIELD',lambda r:r[0]['implementation']['ordered_contacts'][0].__setitem__('velocity',96))
mutated('source first pass obligation deleted in full row','BINDING_RECORD_SHA',lambda r:r[0]['source_payload'].__setitem__('instruction_lines',[]))
first=ROOT/'Build'/BASE/'export-r01';repeat=repeat_output
check('first CLI export complete',first.is_dir())
result=ex.export_bundle(ROOT,repeat)
check('deterministic repeat exact file set and bytes',sorted(p.name for p in first.iterdir())==sorted(p.name for p in repeat.iterdir()) and
      all(p.read_bytes()==(repeat/p.name).read_bytes() for p in first.iterdir()))
manifest=ex.strict_json((repeat/'manifest.json').read_bytes())
check('self-excluding output manifest validates every included payload', {x['path'] for x in manifest['files']}=={'records.jsonl','source-policy.json'} and
      all(len((repeat/x['path']).read_bytes())==x['bytes'] and ex.sha((repeat/x['path']).read_bytes())==x['sha256'] for x in manifest['files']))
check('every input pin and exporter source represented',{x['path'] for x in manifest['inputs']}==set(ex.PINS)|{ex.SELF})
refuses('existing output refused','OUTPUT_EXISTS',lambda:ex.export_bundle(ROOT,first))
refuses('outside private output scope','OUTPUT_SCOPE',lambda:ex.export_bundle(ROOT,ROOT/'Build'/'outside-private-level004-export'))
failed=ROOT/'Build'/BASE/'negative-input-must-not-exist'
original_reader=ex.read_bounded
with patch.object(ex,'read_bounded',side_effect=lambda root,path:raw[ex.PACKET]+b' ' if path==ex.PACKET else original_reader(root,path)):
    refuses('corrupt live-read before publication','INPUT_SHA',lambda:ex.export_bundle(ROOT,failed))
check('input refusal published no output',not failed.exists())
symlink=ROOT/'Build'/BASE/'negative-output-symlink'
symlink.symlink_to(first,target_is_directory=True)
refuses('output symlink refused','OUTPUT_EXISTS',lambda:ex.export_bundle(ROOT,symlink))
refuses('output parent symlink refused','OUTPUT_PATH',lambda:ex.export_bundle(ROOT,symlink/'new-child'))
refuses('input symlink refused','INPUT_PATH',lambda:ex.read_bounded(ROOT,str((symlink/'records.jsonl').relative_to(ROOT))))
refuses('oversized input','INPUT_SIZE',lambda:ex.verify_input_bytes(ex.TXT,b'0'*(ex.MAX_FILE_BYTES+1)))
refuses('invalid JSON encoding','JSON_SYNTAX',lambda:ex.strict_json(b'\xff'))
refuses('invalid JSON syntax','JSON_SYNTAX',lambda:ex.strict_json(b'{'))
first_failure=ROOT/'Build'/BASE/'negative-payload-write'
original_open=Path.open
def failed_payload_open(path,*args,**kwargs):
    if path==first_failure/'source-policy.json' and args and args[0]=='xb':raise OSError('injected payload write refusal')
    return original_open(path,*args,**kwargs)
with patch.object(Path,'open',new=failed_payload_open):
    refuses('payload I/O failure','OUTPUT_WRITE_INCOMPLETE',lambda:ex.export_bundle(ROOT,first_failure))
check('payload I/O refusal has no final manifest',not (first_failure/'manifest.json').exists())
second_failure=ROOT/'Build'/BASE/'negative-manifest-publication'
with patch.object(ex.os,'link',side_effect=OSError('injected manifest publication failure')):
    refuses('manifest publication I/O failure','OUTPUT_WRITE_INCOMPLETE',lambda:ex.export_bundle(ROOT,second_failure))
check('manifest refusal retains diagnostic payloads without publication',(second_failure/'records.jsonl').is_file() and (second_failure/'manifest.pending').is_file() and not (second_failure/'manifest.json').exists())
refuses('partial directory cannot be overwritten','OUTPUT_EXISTS',lambda:ex.export_bundle(ROOT,second_failure))
check('sealed input packet and source still exact',all(ex.sha(ex.read_bounded(ROOT,p))==h for p,h in ex.PINS.items()))
output={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'result':'PASS','checks':checks,
        'check_count':len(checks),'causal_refusals':sum('refusal_code' in c for c in checks),
        'elapsed_seconds':round(time.monotonic()-started,4),'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        'counts':result['counts'],'deterministic_repeat':True,'exports':result['files'],
        'native_app_audio_broad_qa':'NOT_RUN: outside private exporter release','test_data':'Negative cases are in-memory mutations; sealed source inputs untouched'}
path=result_output
with path.open('x') as stream:json.dump(output,stream,indent=2);stream.write('\n')
print(json.dumps({k:output[k] for k in ('result','check_count','causal_refusals','elapsed_seconds','process_peak_rss_bytes','counts')}))
