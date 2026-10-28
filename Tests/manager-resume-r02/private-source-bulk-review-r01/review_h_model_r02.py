"""Affected ModuleH regression plus complete causal recovery; previous review preserved."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import review_h_model as prior
from source_oracles import H_BARS
ROOT=Path(__file__).resolve().parents[3]

def run(m,rows,q):
    # Reuse the existing affected-family matrix, without B/F or original-source replay.
    prior.run(m,rows,q)
    f=m.FullModelReconstructionFlow(rows[0]['package_key'])
    prior.write_all(f,m,unknown_contour=True)
    f.choose_first_position(f.token(),prior.position(f));prior.play_register(f,m)
    f.reveal_source(f.token());prior.transfer(f);prior.play_register(f,m)
    scores={b:{'hearing_accuracy':0,'first_attack_fretboard_accuracy':0} for b in ['1-4','5-8','9-12','13-16']}
    f.declare_scores(f.token(),scores)
    q.refuse(lambda:f.finish(f.token()),m.Refusal,'H corrected model still refuses unknown contour finish',f)
    before=deepcopy(f.__dict__);old=f.token()
    q.refuse(lambda:f.restart_written(f.token(),' '),m.Refusal,'H correction requires nonempty diagnosis',f)
    f.restart_written(f.token(),'Resolve the retained unknown contour by transcribing again.')
    q.check(f.state=='ready_written' and f.responses=={} and f.register==f.bar==f.pass_index==0,'H causal complete retry resets exact written/playing state')
    q.check(f.key==before['key'] and f.instance==before['instance'] and f.plan==before['plan'],'H retry retains exact child/flow/source identity')
    q.check(f.response_history==before['response_history'] and f.reference_history==before['reference_history'],'H correction retains response/source-reference histories')
    q.check(f.response_history[0]['response']['bars'][0] is None and f.revealed is True,'H original unknown and previous source reveal remain retained')
    q.check(f.contacts is None and f.position is None and f.score_declarations is None and f.pitch_matches is None,'H retry clears chosen contacts/scores/previous comparison')
    confirmation={'key':f.key,'pass':'contour','recording_reference':prior.PLAN['recording']['reference'],'ready':True}
    q.refuse(lambda:f.begin_written(old,confirmation),m.Refusal,'H stale pre-retry token',f)
    q.refuse(lambda:f.finish(f.token()),m.Refusal,'H no finish at restarted written boundary',f)
    # Supply four replacement responses to the same retained source and finish both full registers.
    for name in prior.PASSES:
        confirmation={'key':f.key,'pass':name,'recording_reference':prior.PLAN['recording']['reference'],'ready':True}
        f.begin_written(f.token(),confirmation);f.heard(f.token(),{'heard_source':'yes'});f.request_stop(f.token())
        f.release(f.token(),prior.RELEASE);f.commit_written(f.token(),prior.written(name));f.next_written(f.token())
    q.check(len(f.response_history)==8 and len(f.reference_history)==1,'H all four replacement written responses append without erasing prior attempt')
    f.choose_first_position(f.token(),prior.position(f));prior.play_register(f,m)
    f.reveal_source(f.token());prior.transfer(f);prior.play_register(f,m)
    f.declare_scores(f.token(),scores)
    q.check(f.history[-1]['data']['declared_total']==0,'H printed zero manual total implies no invented pass threshold')
    f.finish(f.token())
    q.check(f.state=='completed' and len(f.reference_history)==2,'H complete same-flow causal recovery through both new registers')
    q.check(f.history[-1]['data']['performance_verified'] is False and f.history[-1]['data']['mastery_awarded'] is False and f.history[-1]['data']['official_acceptance'] is False,'H correction completion remains manual/unverified/no acceptance')
    q.check(f.response_history[0]['response']['bars'][0] is None and f.responses['contour']['bars'][0] is not None,'H retained unknown evidence and corrected latest response stay distinct')
    q.check(f.learner_view()['blind_assessment_claim'] is False,'H correction never restores a blind assessment claim after reveal')
    # The original frozen r03 remains failed; keep its distinct exception class in the negative control.
    p=ROOT/'Tools/fullscope-private-c-r01/coherent-batch-resume-r63/reconstruction_contract_r03.py'
    spec=importlib.util.spec_from_file_location('independent_prior_r03_control',p)
    oldmodule=importlib.util.module_from_spec(spec);spec.loader.exec_module(oldmodule)
    q.check(oldmodule.Refusal is not m.Refusal,'H original/corrected imported Refusal classes stay distinct')
    oldflow=oldmodule.FullModelReconstructionFlow(f.key)
    prior.write_all(oldflow,oldmodule,unknown_contour=True)
    oldflow.choose_first_position(oldflow.token(),prior.position(oldflow));prior.play_register(oldflow,oldmodule)
    oldflow.reveal_source(oldflow.token());prior.transfer(oldflow);prior.play_register(oldflow,oldmodule)
    oldflow.declare_scores(oldflow.token(),scores)
    q.refuse(lambda:oldflow.restart_written(oldflow.token(),'Same diagnosed recovery request.'),oldmodule.Refusal,'H original r03 trap remains reproducible and unchanged',oldflow)
