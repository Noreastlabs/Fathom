#pragma once
#include "desktop/HomeView.hpp"
#include <fstream>
namespace fathom::desktop {
struct PracticeViewTestAccess {
 static bool canLeave(const PracticeView& v){return v.canReturn();}
 static void tick(PracticeView& v){v.timerCallback();}
 static void halt(PracticeView& v){v.stopTimer();}
 static platform::AudioOutputMac& output(PracticeView& v){return v.output_;}
 static bool posted(const PracticeView& v){return v.returnPosted_;}
 static bool intent(const PracticeView& v){return v.returnAfterSave_;}
 static bool panel(const PracticeView& v){return v.returnPanel_;}
 static void queueReturn(PracticeView& v){v.requestBack();}
 static std::uint64_t stopStamp(const PracticeView& v){return v.lastStopRequestNs_;}
 static std::string assessment(const PracticeView& v){return v.assessment_.getText().toStdString();}
};
struct MetronomeViewTestAccess {
 static void halt(MetronomeView& v){v.stopTimer();}
 static platform::AudioOutputMac& output(MetronomeView& v){return v.output_;}
 static std::string statusText(const MetronomeView& v){return v.status_.getText().toStdString();}
};
struct SharedAudioViewTestAccess {
 static bool startupReadSettled(const HomeView& h){return !h.learnFuture_&&h.learnMutation_==HomeView::LearnMutation::None;}

 static std::string navigationFacts(const HomeView& h){return "page="+std::to_string(static_cast<int>(h.page_))+" learnFuture="+std::to_string(bool(h.learnFuture_))+" learnMutation="+std::to_string(static_cast<int>(h.learnMutation_))+" queue="+std::to_string(bool(h.learnQueue_))+" suite="+std::to_string(bool(h.learnSuite_))+" suiteReviewed="+std::to_string(h.suiteReviewSaved_)+" practiceRelease="+std::to_string(h.practiceView->audioCanRelease())+" metronomeRelease="+std::to_string(h.metronomeView.audioCanRelease())+" referenceRelease="+std::to_string(h.referenceView.audioCanRelease())+" rhythmRelease="+std::to_string(h.scheduleView.audioCanRelease())+" metroPrefsInFlight="+std::to_string(h.metronomeView.preferenceInFlight())+" metroPrefsPending="+std::to_string(h.metronomeView.preferencesPending());}

 static LessonView& lessons(HomeView& h){return h.lessonView;}
 static ProgressView& progress(HomeView& h){return h.progressView;}
 static GuitarSetupView& setup(HomeView& h){return h.setup;}
 static PracticeView& practice(HomeView& h){return *h.practiceView;}
 static GuidedSessionView& guided(HomeView& h){return h.guidedView;}
 static MetronomeView& metronome(HomeView& h){return h.metronomeView;}
 static FreeplayView& freeplay(HomeView& h){return h.freeplayView;}
 static ReferenceView& reference(HomeView& h){return h.referenceView;}
 static SchedulerView& rhythm(HomeView& h){return h.scheduleView;}
 static AudioOutputView& settings(HomeView& h){return h.outputView;}
 static void halt(HomeView& h){h.stopTimer();h.progressView.stopTimer();h.outputView.stopTimer();PracticeViewTestAccess::halt(*h.practiceView);MetronomeViewTestAccess::halt(h.metronomeView);h.referenceView.stopTimer();h.scheduleView.stopTimer();h.freeplayView.stopTimer();}
 static void tick(HomeView& h){h.progressView.service();h.metronomeView.service();h.referenceView.timerCallback();h.scheduleView.timerCallback();PracticeViewTestAccess::tick(*h.practiceView);h.freeplayView.timerCallback();h.timerCallback();h.outputView.timerCallback();}
 static void inactiveFirst(HomeView& h){h.metronomeView.service();h.referenceView.timerCallback();PracticeViewTestAccess::tick(*h.practiceView);}
 static platform::AudioOutputMac& output(HomeView& h){switch(h.audio_.active()){case SharedAudioSettings::Consumer::Practice:return PracticeViewTestAccess::output(*h.practiceView);case SharedAudioSettings::Consumer::Metronome:return MetronomeViewTestAccess::output(h.metronomeView);case SharedAudioSettings::Consumer::Reference:return h.referenceView.output_;case SharedAudioSettings::Consumer::Rhythm:return h.scheduleView.output;case SharedAudioSettings::Consumer::Count:break;}throw std::runtime_error("Invalid consumer");}
 static std::size_t visiblePages(HomeView& h){std::size_t n{};for(auto* c:std::initializer_list<juce::Component*>{&h.setup,&h.outputView,&h.scheduleView,&h.referenceView,h.practiceView.get(),&h.metronomeView,&h.lessonView,&h.progressView,&h.freeplayView})n+=c->isVisible();return n;}
 static bool pollers(HomeView& h){int n=0;n+=h.practiceView->audioPolling_;n+=h.metronomeView.audioPolling_;n+=h.referenceView.audioPolling_;n+=h.scheduleView.audioPolling_;return n==1;}
 static const scheduler::StreamView& rhythmFinal(HomeView& h){return h.scheduleView.retainedTimeline;}
 static const output::Snapshot& rhythmOutput(HomeView& h){return h.scheduleView.retainedOutput;}
 static AudioEndpoint practiceEndpoint(HomeView& h){return audioEndpoint(*h.practiceView,"Old Practice");}
};
}
