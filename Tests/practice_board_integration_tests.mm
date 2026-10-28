// Reuse the reviewed software-device/Store harness, not its baseline test main.
// No physical device opens: SoftwareDevice::open/start count forbidden calls.
#define main retained_practice_navigation_test_main
#include "practice_navigation_tests.cpp"
#undef main
#include "playback_fretboard_fixtures.hpp"
int main(int argc,char**argv){int checks=0;try{
 if(argc!=2||std::filesystem::exists(argv[1]))throw std::runtime_error("fresh output directory required");std::filesystem::create_directory(argv[1]);const std::filesystem::path root(argv[1]);std::ofstream log(root/"checks.tsv");
 auto ck=[&](bool b,const char*n){++checks;log<<n<<'\t'<<(b?"PASS":"FAIL")<<'\n';if(!b)throw std::runtime_error(n);};
 juce::ScopedJuceInitialiser_GUI gui;
 {
 auto contact=playback_fretboard_fixtures::checked(playback_fretboard_fixtures::contacts());
 practice::Configuration config;config.countIn=practice::CountIn::Off;config.faithfulWholeSpan=true;config.span=Rational{3};config.targetCycles=1;
 practice::Coordinator coordinator;coordinator.begin(reference_fixtures::owner(),practice::Kind::Attempt,"synthetic:contact-gate-oracle",config);
 const auto& timeline=coordinator.timeline(coordinator.owner());desktop::PlaybackFretboardView board;guitar::Setup guitar;guitar.fretCount=24;board.setSetup(guitar);board.setModel(contact);
 for(auto through:{1ULL,5513ULL,22050ULL,22051ULL,44100ULL,44101ULL}){
  const auto keys=desktop::PracticeView::soundingTonesAt(*contact,timeline,0,through-1);board.setActiveTones(keys);
  const auto expected=through<=22050?2U:through<=44100?1U:0U;
  ck(keys.size()==expected,"actualproduction selector respects eachsoundinggate beyondhandspan");
  for(const auto& key:keys)ck(key.eventId=="pitched-contact"&&key.relativeFret==0&&(key.internalString==2||through<=22050),"exact per-tone source key andindependentgate");
  ck(std::count_if(board.projection().begin(),board.projection().end(),[](const auto& c){return c.active;})==int(expected),"actualrenderer accepts contacttonekeys withoutguessing air/rest");
 }
 board.setActiveTones({{"unknown-contact",1,0}});ck(std::none_of(board.projection().begin(),board.projection().end(),[](const auto& c){return c.active;}),"unknown per-tonekey cannot invent source marker");
 auto air=playback_fretboard_fixtures::contacts();air.events[0].contact=music::Contact::Air;air.events[0].tones.clear();air.events[0].handDirection="D";
 auto silent=playback_fretboard_fixtures::checked(air);ck(desktop::PracticeView::soundingTonesAt(*silent,timeline,0,0).empty(),"aircontact no guessed soundingpitches");
 for(auto kind:{music::Contact::Muted,music::Contact::Release}){auto unpitched=air;unpitched.events[0].contact=kind;unpitched.events[0].scopeStrings={1,2,3,4,5,6};auto checked=playback_fretboard_fixtures::checked(unpitched);ck(desktop::PracticeView::soundingTonesAt(*checked,timeline,0,0).empty(),"muted/release scopedcontact never invent soundingmarker");}

 }

 auto active=[](desktop::PracticeView&v){return std::count_if(v.playbackFretboardView().projection().begin(),v.playbackFretboardView().projection().end(),[](const auto&c){return c.active;});};
 {Harness h(root,"layout-and-lifecycle");auto&v=*h.view;desktop::setup::BoardDisplay settings{true,desktop::setup::BoardMode::Note,desktop::setup::NoteSpelling::Flat};v.setBoardDisplay(settings);
 for(auto size:{std::pair{620,680},std::pair{920,680},std::pair{1280,800}})for(double zoom:{0.1,2.0}){
  v.setSize(size.first,size.second);ck(v.tabView().setZoom(zoom),"actualTABzoom accepted10/200");v.resized();
  ck(v.boardBounds().getWidth()>0&&v.boardBounds().getHeight()>0&&v.getLocalBounds().contains(v.boardBounds()),"board positive and contained");
  ck(v.tabView().isVisible()&&v.tabView().getWidth()>0&&v.tabView().getHeight()>0&&v.getLocalBounds().contains(v.tabView().getBounds())&&!v.boardBounds().intersects(v.tabView().getBounds()),"TABpositive separate fromboard");
  juce::Viewport*viewport=nullptr;for(auto*c:v.tabView().getChildren())if(auto*p=dynamic_cast<juce::Viewport*>(c))viewport=p;
  ck(viewport&&viewport->getWidth()>0&&viewport->getHeight()>0&&viewport->getViewedComponent()&&viewport->getViewedComponent()->getWidth()>0&&viewport->getViewedComponent()->getHeight()>0,"actualTABviewport andcanvas positive notmerely outerbounds");
  for(auto b:v.boardControlBounds())ck(b.getWidth()>0&&b.getHeight()>0&&v.getLocalBounds().contains(b)&&!b.intersects(v.boardBounds())&&!b.intersects(v.tabView().getBounds()),"board controls positive contained no canvas/board overlap");
  for(auto*c:v.getChildren())if(c->isVisible()&&dynamic_cast<juce::Button*>(c))ck(v.getLocalBounds().contains(c->getBounds()),"visibletransport/save/navigationbutton contained");
  ck(v.boardDisplay()==settings&&active(v)==0,"zoomresize leaves preferences andstopped projection unchanged");
 }
 v.setSize(920,680);h.start();h.blocks(400);
 ck(!v.isShowing()&&active(v)==0,"peerless software Practice never paints native-only board highlights");
 const auto firstOwner=v.coordinator().owner();const auto firstTones=Access::acceptedBoardTones(v);
 ck(v.coordinator().state()==practice::State::Running&&Access::boardLatch(v)&&!firstTones.empty(),"real accepted currentowner Running selects sounding tones with armed latch");
 // The production accepted model is verified through its exact tone keys; standalone contact projections above cover painted marker cells.
 ck(!v.againSample()&&Access::boardLatch(v)&&v.coordinator().owner()==firstOwner&&Access::acceptedBoardTones(v)==firstTones,"rejectedAgain preserves currentowner accepted tones and latch");
 const auto back=v.onBack;v.onBack={};Access::queue(v);ck(Access::boardLatch(v)&&v.coordinator().owner()==firstOwner&&Access::acceptedBoardTones(v)==firstTones,"unavailableBack preserves currentowner accepted tones and latch");v.onBack=back;
 h.click("Pause");ck(!Access::boardLatch(v)&&active(v)==0&&Access::acceptedBoardTones(v).empty(),"Pause request immediately disarms sounding gate");h.blocks(1);ck(v.coordinator().state()==practice::State::Paused&&!Access::boardLatch(v)&&Access::acceptedBoardTones(v).empty(),"acceptedPaused keeps sounding gate clear");
 ck(v.resumeSample(),"actualResume admitted");ck(active(v)==0&&!(v.coordinator().owner()==firstOwner),"Resume binds fresh owner without headless painted highlights");h.blocks(400);ck(v.coordinator().state()==practice::State::Running&&Access::boardLatch(v)&&!Access::acceptedBoardTones(v).empty()&&active(v)==0,"resumed accepted currentowner selects tones while native paint stays gated");
 v.setVisible(false);ck(active(v)==0,"navigationhide immediately clearsboard");h.blocks(1);ck(active(v)==0,"hidden acceptedfacts cannot relight");v.setVisible(true);
 h.click("Stop");ck(active(v)==0,"Stop request immediately clearsboard");h.review();ck(active(v)==0,"terminalreview boardclear");
 ck(v.saveSample(nullptr),"originalAttempt savedwithout inventedassessment");h.wait([&]{return v.captureSession()->phase()==capture::SessionPhase::Saved;},"savedoriginal");ck(v.againSample()&&active(v)==0,"Again freshowner doesnot retain completednotes");const bool closedImmediately=v.requestClose();if(!closedImmediately)h.wait([&]{return Access::canLeave(v);},"original unused restart output shutdown completes before close confirmation");ck(closedImmediately||v.requestClose(),"unusedrestart safelyclosed after original asynchronous output cleanup");
 }
 ck(opened==0,"software tests neveropen/start physicaldevice");std::cout<<"PASS "<<checks<<" Practice board integration checks\n";return 0;
}catch(const std::exception&e){std::cerr<<"FAIL after "<<checks<<": "<<e.what()<<'\n';return 1;}}
