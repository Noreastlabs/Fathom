"""Exact first-pass preservation and causal source-duty refusals."""
import copy, hashlib, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'Tools/fullscope-private-a-r01/level035-landing-tasks-r01'))
from landing import build, validate
old_path = ROOT / 'Build/fullscope-private-a-r01/level035-r05/packet.jsonl'
new_path = ROOT / 'Build/fullscope-private-a-r01/level035-r06/packet.jsonl'
old_raw = old_path.read_text().splitlines(keepends=True)
new_raw = new_path.read_text().splitlines(keepends=True)
old, new = [[json.loads(s) for s in values] for values in (old_raw, new_raw)]
positive = []
for row in range(1, 40):
    if not 31 <= row <= 36:
        assert old_raw[row - 1] == new_raw[row - 1]
        continue
    source, emitted = old[row - 1], new[row - 1]
    contract = copy.deepcopy(emitted['implementation']['source_landing_task'])
    authority = contract.pop('source_authority')
    assert validate(contract, source) and contract == build(copy.deepcopy(source))
    assert [c['contact_ordinals'] for c in contract['cells']] == [[1,2,3,4],[5,6,7,8],[9,10,11,12],[13,14,15,16]]
    assert [c['repeated_target_contact'] for c in contract['cells']] == [3,7,11,15]
    assert {k:v for k,v in emitted['implementation'].items() if k != 'source_landing_task'} == source['implementation']
    for key in ('package_key','source_identity','source_payload','timing_authority','status','unresolved_reasons'):
        assert emitted[key] == source[key]
    positive.append({'row':row,'package_key':source['package_key'],'deterministic':True,'source_and_D_U_variants_preserved':True})


def mutate(value, path, replacement):
    value = copy.deepcopy(value)
    target = value
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = replacement
    return value


refusals = []


def refuse(name, call):
    try:
        call()
    except ValueError as error:
        refusals.append({'case':name,'refused':True,'reason':str(error)})
    else:
        raise AssertionError(name)


source = old[30]
contract = build(source)
for name,path,value in [
    ('collapse_repeated_target',['cells',0,'contact_ordinals'],[1,2,4]),
    ('extra_attack',['picked_contact_count'],17),
    ('wrong_distance',['cells',0,'target','distance_frets'],5),
    ('look_after_departure',['cells',0,'manual_predeparture_duty'],'look after arrival'),
    ('invent_gaze_observation',['cells',0,'look_or_accuracy_observed'],True),
    ('allow_audible_shift',['source_motion_constraint','shift_must_not_be_audible'],False),
    ('invent_fixed_rest',['source_motion_constraint','fixed_rest_events_generated'],[{'duration_q':[1,4]}]),
    ('invent_gate',['source_motion_constraint','numeric_gap_or_gate'],[1,4]),
    ('invent_velocity',['source_target_matching','numeric_velocity_or_tolerance'],96),
    ('simultaneous_target_attacks',['source_target_matching','identical_absolute_onsets_required'],True),
    ('invent_clock',['selected_numeric_clock'],[1,1]),
    ('invent_mirror_sequence',['later_mirror_duty','generated_contact_sequence'],[17,12,12,17]),
    ('invent_mirror_finger',['later_mirror_duty','selected_fingering'],1),
    ('invent_conflict_adjudication',['later_mirror_duty','source_conflict_adjudicated'],True),
    ('native_ready',['native_projection_complete'],True),
    ('claim_credit',['learner_performance_or_credit_claimed'],True),
]:
    refuse(name,lambda p=path,v=value:validate(mutate(contract,p,v),source))
refuse('source_contact_removed',lambda:build(mutate(source,['implementation','ordered_contacts'],source['implementation']['ordered_contacts'][:-1])))
refuse('source_legato_repick',lambda:build(mutate(source,['implementation','ordered_contacts',2,'pick_attack'],False)))
refuse('source_wrong_first_pass_finger',lambda:build(mutate(source,['implementation','ordered_contacts',1,'finger'],3)))
refuse('source_clock_injection',lambda:build(mutate(source,['implementation','ordered_contacts',0,'onset_q'],[0,1])))
assert len(positive)==6 and len(refusals)==20
report={'status':'PASS','positive_count':6,'causal_refusal_count':20,'positive_cases':positive,'causal_refusals':refusals,
        'unrelated_record_bytes_identical':33,'packet_sha256':hashlib.sha256(new_path.read_bytes()).hexdigest(),
        'native_runtime_performance':'NOT_RUN','scope':'Source task constraints and source-conservation only.'}
with (ROOT/'Results/fullscope-private-a-r01/level035-r06/task-tests.json').open('x') as out:
    json.dump(report,out,indent=2)
    out.write('\n')
print(json.dumps({'status':'PASS','positive':6,'causal_refusals':20}))
