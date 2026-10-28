// Requirement-derived repeat cases; retained helper renders actual provider with synthetic acknowledgments.
#define main retained_pulse_campaign_main
#include "m1_lesson_pulse_tests.cpp"
#undef main
#include "core/TabPlayback.hpp"
#include <tuple>
int main(int argc,char** argv){try{
 if(argc!=3)throw std::invalid_argument("Expected accepted bundle and new absolute evidence directory");const std::filesystem::path out(argv[2]);if(!out.is_absolute()||std::filesystem::exists(out))throw std::invalid_argument("Use new absolute evidence directory");std::filesystem::create_directories(out);checkTrace.open(out/"checks.tsv");
 auto catalog=lesson::Catalog::load(argv[1]);auto a=catalog->admit("fg:item:000002","fg:variant:000006");auto b=catalog->admit("fg:item:000003","fg:variant:000029");A cases;
 for(const auto& admitted:{a,b}){
  check(admitted->practiceConfiguration(44100,60).targetCycles==1,"new selection defaults one without changing source");
  for(std::uint64_t count:{1ULL,2ULL,32ULL}){
   auto cfg=admitted->practiceConfiguration(44100,137);cfg.targetCycles=count;auto co=original(*admitted,cfg,true);admitted->validateOriginal(co);platform::PracticePlayback provider;
   check(provider.prepareLesson(*admitted,admitted->referenceConfiguration(co.owner(),1,cfg.rate,cfg.bpm),co,count),"finite full-span generation prepared from original");
   const auto terminal=frames(Rational{static_cast<std::int64_t>(cfg.span.numerator()*count),cfg.span.denominator()},cfg);
   auto data=drive(provider,co,terminal,false);
   using Tuple=std::tuple<int,std::uint64_t,std::uint64_t,std::uint32_t,int,int>;std::vector<Tuple> expectedReference,actualReference;
   const auto program=reference::compile(admitted->model(),admitted->referenceConfiguration(owner(),1,cfg.rate,cfg.bpm));
   for(std::uint64_t cycle=0;cycle<count;++cycle){const Rational base{static_cast<std::int64_t>(cycle)*cfg.span.numerator(),cfg.span.denominator()};
    for(std::size_t i=0;i<program.voices().size();++i){const auto& voice=program.voices()[i];expectedReference.emplace_back(0,frames(base+voice.onset,cfg),cycle,static_cast<std::uint32_t>(i+1),0,0);expectedReference.emplace_back(0,frames(base+voice.end,cfg),cycle,static_cast<std::uint32_t>(i+1),0,1);}
    expectedReference.emplace_back(1,frames(base+cfg.span,cfg),cycle+1,0,0,0);
   }
   for(const auto& f:data.reference)actualReference.emplace_back(static_cast<int>(f.kind),f.frame,f.cycle,f.sourceEvent,static_cast<int>(f.role),static_cast<int>(f.action));
   std::sort(expectedReference.begin(),expectedReference.end());std::sort(actualReference.begin(),actualReference.end());check(actualReference==expectedReference,"all source attacks/releases and cycle boundaries match global rational positions");check(co.completedCycles()==count&&co.activeFrames()==terminal,"exact selected terminal prefix and completed count");
   const auto context=json::parse(co.context());check(context.object().at("target").object().at("cycles")==n(static_cast<std::int64_t>(count))&&context.object().at("configuration").object().at("values").object().at("target_cycles")==n(static_cast<std::int64_t>(count)),"two existing target fields agree with immutable original");
   std::vector<std::uint64_t> expected;for(std::uint64_t cycle=0;cycle<count;++cycle)for(std::int64_t q=0;Rational{q}<cfg.span;++q)expected.push_back(frames(Rational{static_cast<std::int64_t>(cycle)*cfg.span.numerator()+q*cfg.span.denominator(),cfg.span.denominator()},cfg));
   check(data.pulseFrames==expected,"all quarter pulses remain inside their selected cycles, none beyond terminal");
   check(context.object().at("configuration").object().at("source_task_completion")==V(false),"scheduled passes do not complete source task");
   cases.push_back(O{{"variant",admitted->identity().object().at("variant_id")},{"count",n(static_cast<std::int64_t>(count))},{"frames",n(static_cast<std::int64_t>(terminal))},{"notes_sha256",digest(data.notes)},{"click_sha256",digest(data.clicks)}});
  }
  for(std::uint64_t bad:{0ULL,33ULL,1000000ULL,~0ULL}){auto cfg=admitted->practiceConfiguration(44100,60);cfg.targetCycles=bad;refuses([&]{admitted->validatePractice(cfg);},"invalid finite repeat selection refused");}
  auto cfg=admitted->practiceConfiguration(44100,60);cfg.targetCycles=2;
  {auto req=capture::lessonStart(*admitted,cfg,"00000000-0000-4000-8000-000000000001","2026-09-12T13:00:00Z","America/New_York",1,true);auto wrong=cfg;wrong.targetCycles=3;practice::Coordinator other;other.begin(owner(),practice::Kind::Attempt,storage::canonical(req.binding.context),wrong);refuses([&]{admitted->validateOriginal(other);},"coordinator target differs from both original fields");}
  for(const auto field:{"target","values"}){auto req=capture::lessonStart(*admitted,cfg,"00000000-0000-4000-8000-000000000001","2026-09-12T13:00:00Z","America/New_York",1,true);
   if(std::string(field)=="target")req.binding.context.object().at("target").object()["cycles"]=n(1);else req.binding.context.object().at("configuration").object().at("values").object()["target_cycles"]=n(1);
   practice::Coordinator co;co.begin(owner(),practice::Kind::Attempt,storage::canonical(req.binding.context),cfg);refuses([&]{admitted->validateOriginal(co);},"mismatched original repeat field refused before preparation");
  }
 }
 // Actual TAB consumer at consecutive exclusive prefixes around a cycle boundary.
 {auto tc=a->practiceConfiguration(44100,137);tc.targetCycles=2;auto control=original(*a,tc,true);auto doc=std::make_shared<const tab::Document>(a->model());tab::Playback tab;tab.bind(doc,a->model(),control);const auto boundary=frames(tc.span,tc);std::uint64_t seq{};
  for(auto through:{boundary,boundary+1}){practice::Progress p;p.owner=control.owner();p.sequence=++seq;p.clientAcceptedThrough=p.scheduledThrough=p.activeFrames=through;p.completedCycles=1;p.cursorFrames=through-boundary;p.partial=p.cursorFrames!=0;p.state=practice::State::Running;check(control.progress(p)&&tab.update(control),"TAB accepts original boundary fact");check(tab.position().cycle==(through==boundary?0U:1U)&&tab.position().events==std::vector<std::string>{through==boundary?doc->source().events.back().id:doc->source().events.front().id},"exclusive endpoint keeps last source note; next accepted sample selects first note of next cycle");}
 }
 {auto goldenConfig=a->practiceConfiguration(44100,60);goldenConfig.targetCycles=2;auto goldenOwner=original(*a,goldenConfig,true);platform::PracticePlayback goldenProvider;check(goldenProvider.prepareLesson(*a,a->referenceConfiguration(goldenOwner.owner(),1,44100,60),goldenOwner,2),"pre-native exact two-cycle golden prepared");auto golden=drive(goldenProvider,goldenOwner,441000,false);
  for(const auto& bus:std::vector<std::pair<std::string,const std::vector<float>*>>{{"reference.f32",&golden.notes},{"pulse.f32",&golden.clicks}}){std::ofstream file(out/bus.first,std::ios::binary);file.write(reinterpret_cast<const char*>(bus.second->data()),static_cast<std::streamsize>(bus.second->size()*sizeof(float)));file.close();check(bool(file),"golden bus retained "+bus.first);}
 }
 auto cfg=a->practiceConfiguration(44100,60);cfg.targetCycles=2;auto co=original(*a,cfg,true);platform::PracticePlayback provider;
 check(provider.prepareLesson(*a,a->referenceConfiguration(co.owner(),1,cfg.rate,cfg.bpm),co,2),"two-cycle interrupted original prepared");
 const auto span=frames(cfg.span,cfg),cut=span+13777;auto partial=drive(provider,co,cut,true);check(co.completedCycles()==1&&co.activeFrames()==cut,"pause in second traversal retains one completed span plus partial time");
 const auto originalKey=co.originalKey();co.resume();check(provider.prepareLesson(*a,a->referenceConfiguration(co.owner(),2,cfg.rate,cfg.bpm),co,1),"resume only remaining complete span from safe start");auto replay=drive(provider,co,span,false);
 check(co.originalKey()==originalKey&&co.completedCycles()==2&&co.activeFrames()==cut+span,"replay does not duplicate completed first span or erase interrupted time");
 // Stop exactly at first boundary: retain one completed cycle and no attack from the next.
 auto stopped=original(*a,cfg,true);platform::PracticePlayback stopProvider;check(stopProvider.prepareLesson(*a,a->referenceConfiguration(stopped.owner(),1,cfg.rate,cfg.bpm),stopped,2),"boundary stop prepared");auto stoppedData=drive(stopProvider,stopped,span,true);stopped.stoppedAcknowledged(stopped.owner(),practice::State::Ended,1000);
 check(stopped.completedCycles()==1&&stopped.activeFrames()==span&&stoppedData.pulseFrames.back()<span,"boundary stop retains only confirmed previous cycle");
 write(out/"cases.json",storage::canonical(cases));write(out/"summary.json",storage::canonical(O{{"status","PASS"},{"checks",n(checks)},{"matrix_cases",n(6)},{"native",false},{"classification","actual provider; synthetic callback acknowledgments"}}));std::cout<<"PASS "<<checks<<" repeat checks\n";return 0;
}catch(const std::exception& e){std::cerr<<"FAIL after "<<checks<<": "<<e.what()<<'\n';return 1;}}
