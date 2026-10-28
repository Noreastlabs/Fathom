// The test compiles the exact production adapter in this translation unit to inspect
// its private mechanics. The test capture seam is absent from production builds.
#include <CoreAudio/CoreAudio.h>
#import <AppKit/AppKit.h>
#include <array>
#include <atomic>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <iomanip>
#include <sstream>
#include <thread>
#include <vector>
namespace {
constexpr std::size_t captureLimit=48000*30*2;
std::array<float,captureLimit> capture{};
std::size_t captured{};
bool captureOverflow{};
bool captureEnabled{true};
void captureNative(int,const AudioBufferList* data) noexcept {
    if(!captureEnabled)return;
    if(!data || data->mNumberBuffers==0)return;
    // Selected JUCE native float output; keep raw interleaving, not DAC samples.
    for(UInt32 b=0;b<data->mNumberBuffers;++b) {
        const auto& buf=data->mBuffers[b];const auto n=buf.mDataByteSize/sizeof(float);
        if(!buf.mData)continue;
        if(n>captureLimit-captured) {captureOverflow=true;return;}
        const auto* samples=static_cast<const float*>(buf.mData);
        for(UInt32 i=0;i<n;++i)capture[captured++]=samples[i];
    }
}
}
#define FATHOM_TEST_NATIVE_CAPTURE captureNative
#include "../Source/platform/AudioOutputMac.mm"
// This test target compiles SchedulerView.cpp directly; retain its polyrhythm
// implementation in the test translation unit without changing shared CMake.
#include "../Source/metronome/Polyrhythm.cpp"


#include "desktop/SchedulerView.hpp"
namespace {
using namespace fathom;
std::string uuid(const scheduler::Owner& o){std::ostringstream text;text<<std::hex<<std::setfill('0');for(auto b:o.id)text<<std::setw(2)<<static_cast<unsigned>(b);return text.str();}
int accessibilityCapture(const std::filesystem::path& root){
    if(!root.is_absolute()||std::filesystem::exists(root))return 2;
    std::filesystem::create_directories(root);
    std::ofstream checks(root/"checks.tsv"),trace(root/"focus.tsv");
    int count=0,failures=0;
    const auto check=[&](bool okay,const std::string& name){++count;failures+=!okay;checks<<name<<'\t'<<(okay?"PASS":"FAIL")<<'\n';};
    [NSApplication sharedApplication];[NSApp setActivationPolicy:NSApplicationActivationPolicyRegular];
    juce::ScopedJuceInitialiser_GUI gui;
    for(const int width:{640,920}){
        desktop::SchedulerView view;view.setSize(width,680);
        view.addToDesktop(juce::ComponentPeer::windowHasTitleBar);view.setVisible(true);
        auto* native=(__bridge NSView*)view.getPeer()->getNativeHandle();
        [native.window makeKeyAndOrderFront:nil];
        check(native&&native.window&&view.isShowing(),"Rhythm native peer showing at "+std::to_string(width));
        const auto picture=view.createComponentSnapshot(view.getLocalBounds());
        juce::FileOutputStream image{juce::File((root/("rhythm-"+std::to_string(width)+".png")).string())};
        juce::PNGImageFormat png;
        check(image.openedOk()&&png.writeImageToStream(picture,image),"Rhythm snapshot written at "+std::to_string(width));
        image.flush();check(!image.getStatus().failed(),"Rhythm snapshot flushed at "+std::to_string(width));
        const auto* heading=dynamic_cast<const juce::Label*>(view.findChildWithID("rhythm-title"));
        const auto* layerA=dynamic_cast<const juce::Label*>(view.findChildWithID("rhythm-layer-a"));
        const auto* layerB=dynamic_cast<const juce::Label*>(view.findChildWithID("rhythm-layer-b"));
        check(heading&&heading->getText().contains(juce::String::fromUTF8("—"))
                  && heading->getText().containsIgnoreCase("Synthetic sound-check preview"),
              "Rhythm identity renders the UTF-8 separator at "+std::to_string(width));
        check(layerA&&layerB
                  && layerA->getText().contains(juce::String::fromUTF8("▲"))
                  && layerB->getText().contains(juce::String::fromUTF8("●"))
                  && layerA->getText().contains("3 hits")&&layerB->getText().contains("2 hits")
                  && layerA->getTitle().contains("triangle markers")
                  && layerB->getTitle().contains("circle markers"),
              "Rhythm layers render distinct non-color shape cues at "+std::to_string(width));
        juce::KeyboardFocusTraverser traverser;const auto order=traverser.getAllComponents(&view);
        trace<<width<<"\tconstructed";
        for(const auto* item:order)trace<<'\t'<<item->getComponentID().toStdString();
        trace<<'\n';
        check(order.size()==3&&order[0]->getComponentID()=="rhythm-ratio-preset"
                  && order[1]->getComponentID()=="rhythm-audio-settings"
                  && order[2]->getComponentID()=="rhythm-back",
              "Rhythm stopped focus path follows visible ratio, Audio and Back at "+std::to_string(width));
        if(order.size()>1){
            order.front()->grabKeyboardFocus();
            const auto* before=juce::Component::getCurrentlyFocusedComponent();
            auto* down=[NSEvent keyEventWithType:NSEventTypeKeyDown location:NSZeroPoint modifierFlags:0 timestamp:NSProcessInfo.processInfo.systemUptime windowNumber:native.window.windowNumber context:nil characters:@"\t" charactersIgnoringModifiers:@"\t" isARepeat:NO keyCode:48];
            auto* up=[NSEvent keyEventWithType:NSEventTypeKeyUp location:NSZeroPoint modifierFlags:0 timestamp:NSProcessInfo.processInfo.systemUptime windowNumber:native.window.windowNumber context:nil characters:@"\t" charactersIgnoringModifiers:@"\t" isARepeat:NO keyCode:48];
            [NSApp sendEvent:down];[NSApp sendEvent:up];
            const auto* after=juce::Component::getCurrentlyFocusedComponent();
            trace<<width<<"\tAppKit Tab\t"<<(before?before->getComponentID().toStdString():"<none>")<<'\t'<<(after?after->getComponentID().toStdString():"<none>")<<'\n';
            check(before==order[0]&&after==order[1],"Injected AppKit Tab follows Rhythm focus path at "+std::to_string(width));
        }
        check(!order.empty(),"Rhythm constructed focus path exists at "+std::to_string(width));
        check(view.audioSnapshot().state==output::State::Closed&&view.audioCanRelease(),"Rhythm accessibility capture retains closed output at "+std::to_string(width));
        view.removeFromDesktop();
    }
    trace.flush();checks.flush();const bool evidenceOkay=trace.good()&&checks.good();
    std::ofstream(root/"summary.json")<<"{\"checks\":"<<count<<",\"failures\":"<<failures<<",\"evidenceFlushed\":"<<(evidenceOkay?"true":"false")<<",\"injectedAppKitEvents\":true,\"nativeAudioRun\":false}\n";
    std::cout<<(failures||!evidenceOkay?"FAIL ":"PASS ")<<count<<" Rhythm accessibility capture checks; failures="<<failures<<'\n';
    return failures||!evidenceOkay?1:0;
}
int actionKeyCapture(const std::filesystem::path& root){
    if(!root.is_absolute()||std::filesystem::exists(root))return 2;
    std::filesystem::create_directories(root);
    std::ofstream checks(root/"checks.tsv"),trace(root/"action-keys.tsv");
    int count=0;std::string failure;
    const auto check=[&](bool okay,const std::string& name){++count;checks<<count<<'\t'<<name<<'\t'<<(okay?"PASS":"FAIL")<<'\n';if(!okay)throw std::runtime_error(name);};
    try {
        [NSApplication sharedApplication];[NSApp setActivationPolicy:NSApplicationActivationPolicyRegular];
        juce::ScopedJuceInitialiser_GUI gui;
        trace<<"width\taction\tkey\tratio\tback_callbacks\n";
        for(const int width:{640,920}){
            desktop::SchedulerView view;view.setSize(width,680);view.addToDesktop(juce::ComponentPeer::windowHasTitleBar);view.setVisible(true);
            auto* peer=view.getPeer();auto* native=peer?(__bridge NSView*)peer->getNativeHandle():nil;
            if(native.window)[native.window makeKeyAndOrderFront:nil];
            check(peer&&native&&native.window&&view.isShowing(),"Rhythm visible native peer at "+std::to_string(width));
            auto* preset=dynamic_cast<juce::ComboBox*>(view.findChildWithID("rhythm-ratio-preset"));
            auto* x=dynamic_cast<juce::TextEditor*>(view.findChildWithID("rhythm-ratio-x"));
            auto* y=dynamic_cast<juce::TextEditor*>(view.findChildWithID("rhythm-ratio-y"));
            auto* apply=dynamic_cast<juce::TextButton*>(view.findChildWithID("rhythm-ratio-apply"));
            auto* heading=dynamic_cast<juce::Label*>(view.findChildWithID("rhythm-shared-cycle"));
            auto* layerA=dynamic_cast<juce::Label*>(view.findChildWithID("rhythm-layer-a"));
            auto* layerB=dynamic_cast<juce::Label*>(view.findChildWithID("rhythm-layer-b"));
            auto* audioSettings=dynamic_cast<juce::TextButton*>(view.findChildWithID("rhythm-audio-settings"));
            auto* back=dynamic_cast<juce::TextButton*>(view.findChildWithID("rhythm-back"));
            check(preset&&x&&y&&apply&&heading&&layerA&&layerB&&audioSettings&&back,"Rhythm actual ratio, Audio and Back controls exist at "+std::to_string(width));
            preset->setSelectedId(9,juce::sendNotificationSync);x->setText("5");y->setText("7");
            check(apply->isShowing()&&apply->isEnabled()&&x->isShowing()&&y->isShowing(),"Rhythm Custom 5:7 Apply visible and enabled at "+std::to_string(width));
            apply->grabKeyboardFocus();check(juce::Component::getCurrentlyFocusedComponent()==apply,"Rhythm Apply receives focus at "+std::to_string(width));
            check(peer->handleKeyPress(juce::KeyPress{juce::KeyPress::spaceKey}),"Rhythm focused Apply consumes Space at "+std::to_string(width));
            check(heading->getText().contains("5:7")&&layerA->getText().contains("5 hits")&&layerB->getText().contains("7 hits"),"Rhythm focused Apply shows accepted 5:7 and layer hits at "+std::to_string(width));
            trace<<width<<"\tApply ratio\tSpace\t5:7\t0\n";
            int openedAudio=0;view.onAudioSettings=[&]{++openedAudio;};
            check(audioSettings->isShowing()&&audioSettings->isEnabled(),"Rhythm shared Audio settings visible at "+std::to_string(width));
            audioSettings->grabKeyboardFocus();check(juce::Component::getCurrentlyFocusedComponent()==audioSettings,"Rhythm Audio settings receives focus at "+std::to_string(width));
            check(peer->handleKeyPress(juce::KeyPress{juce::KeyPress::spaceKey}),"Rhythm focused Audio settings consumes Space at "+std::to_string(width));
            check(openedAudio==1&&view.audioSnapshot().state==output::State::Closed,"Rhythm Audio handoff occurs once while output Closed at "+std::to_string(width));
            trace<<width<<"\tAudio settings\tSpace\t5:7\t0\n";
            int returned=0;view.onBack=[&]{++returned;};
            check(back->isShowing()&&back->isEnabled()&&view.audioSnapshot().state==output::State::Closed,"Rhythm Back visible and output Closed at "+std::to_string(width));
            back->grabKeyboardFocus();check(juce::Component::getCurrentlyFocusedComponent()==back,"Rhythm Back receives focus at "+std::to_string(width));
            check(peer->handleKeyPress(juce::KeyPress{juce::KeyPress::returnKey}),"Rhythm focused Back consumes Return at "+std::to_string(width));
            check(returned==1&&view.audioSnapshot().state==output::State::Closed,"Rhythm Back returns once with output Closed at "+std::to_string(width));
            trace<<width<<"\tBack\tReturn\t5:7\t"<<returned<<'\n';
            auto image=view.createComponentSnapshot(view.getLocalBounds());juce::FileOutputStream file{juce::File((root/("rhythm-action-"+std::to_string(width)+".png")).string())};juce::PNGImageFormat png;
            check(file.openedOk()&&png.writeImageToStream(image,file),"Rhythm action screenshot at "+std::to_string(width));
            view.removeFromDesktop();
        }
    } catch(const std::exception& e){failure=e.what();}
    trace.flush();checks.flush();const bool evidenceOkay=trace.good()&&checks.good();
    std::ofstream(root/"summary.json")<<"{\"checks\":"<<count<<",\"status\":\""<<(failure.empty()&&evidenceOkay?"PASS":"FAIL")<<"\",\"nativeAudioRun\":false,\"physicalKeyboard\":false}\n";
    std::cout<<(failure.empty()&&evidenceOkay?"PASS ":"FAIL ")<<count<<" Rhythm action keyboard checks"<<(failure.empty()?"":"; "+failure)<<'\n';
    return failure.empty()&&evidenceOkay?0:1;
}
class Run final:private juce::Timer {
public:
    Run(std::string root):root_(std::move(root)),events_(root_+"/events.csv"),facts_(root_+"/facts.csv"),views_(root_+"/views.csv"),states_(root_+"/states.csv") {
        events_<<"ns,epoch,kind,serial,object,selector,scope,element,frames,flags,status,sample_time,rate_scalar,peak,raw_host,text\n";
        facts_<<"kind,uuid,epoch,generation,binding,frame,cycle,event,role,action\n";
        views_<<"observed_ns,block,begin,prefix,state,processed,cycles,tempo,phase_origin,phase_n,phase_d,accepted,rejected,drops,failed\n";
        states_<<"ns,step,state,submitted,confirmed,uncertain,first_silent,callbacks,rendered\n";
        start_=platform::monotonicNs();startTimer(20);
    }
    int result()const{return done_&&!failed_?0:1;}
private:
    void drain(){
        platform::NativeEvent e;while(output_.nextEvent(e)) {
            std::string text=e.text.data();for(auto& c:text)if(c==','||c=='\n'||c=='\r')c=' ';
            events_<<e.ns<<','<<e.epoch<<','<<e.kind<<','<<e.serial<<','<<e.object<<','<<e.selector<<','<<e.scope<<','<<e.element<<','<<e.frames<<','<<e.flags<<','<<e.status<<','<<std::setprecision(17)<<e.sampleTime<<','<<e.rateScalar<<','<<e.peak<<','<<e.rawHost<<','<<text<<'\n';
        }
        scheduler::Fact f;while(sound_.stream.nextFact(f))facts_<<static_cast<int>(f.kind)<<','<<uuid(f.owner)<<','<<f.owner.epoch<<','<<f.owner.generation<<','<<f.binding<<','<<f.frame<<','<<f.cycle<<','<<f.sourceEvent<<','<<static_cast<int>(f.role)<<','<<static_cast<int>(f.action)<<'\n';
        scheduler::StreamView v;while(sound_.stream.nextView(v)) {
            latest_=v;views_<<platform::monotonicNs()<<','<<v.block<<','<<v.blockBegin<<','<<v.prefix<<','<<static_cast<int>(v.cursor.state)<<','<<v.cursor.processedThrough<<','<<v.cursor.completedCycles<<','<<v.tempoIndex<<','<<v.phaseOrigin<<','<<v.phaseSpan.n<<','<<v.phaseSpan.d<<','<<v.acceptedCommands<<','<<v.rejectedCommands<<','<<v.displayDrops<<','<<v.failed<<'\n';
        }
        const auto ov=output_.status();const auto s=ov.lifecycle;states_<<platform::monotonicNs()<<','<<step_<<','<<static_cast<int>(s.state)<<','<<s.submittedFrames<<','<<s.confirmedFrames<<','<<s.uncertainThrough<<','<<ov.firstSilentCallbackNs<<','<<ov.callbacks<<','<<ov.renderedBlocks<<'\n';
    }
    void finish(bool fail,const char* reason){
        if(done_)return;done_=true;stopTimer();const auto out=output_.shutdown();const auto s=sound_.stream.quiescentView();drain();failed_=fail||captureOverflow||output_.status().cleanupFailed;
        std::ofstream pcm(root_+"/native-output-f32.raw",std::ios::binary);pcm.write(reinterpret_cast<const char*>(capture.data()),static_cast<std::streamsize>(captured*sizeof(float)));
        std::ofstream json(root_+"/run-result.json");json<<"{\"failed\":"<<(failed_?"true":"false")<<",\"done\":true,\"step\":"<<step_<<",\"capturedFloats\":"<<captured<<",\"overflow\":"<<(captureOverflow?"true":"false")<<",\"processed\":"<<s.cursor.processedThrough<<",\"cycles\":"<<s.cursor.completedCycles<<",\"tempo\":"<<s.tempoIndex<<",\"submitted\":"<<out.submittedFrames<<",\"confirmed\":"<<out.confirmedFrames<<",\"hasConfirmation\":"<<(out.hasConfirmation?"true":"false")<<",\"pending\":"<<(out.pendingOutcome?"true":"false")<<",\"uuid\":\""<<uuid(out.owner)<<"\",\"epoch\":"<<out.owner.epoch<<",\"generation\":"<<out.owner.generation<<",\"requestedStopNs\":"<<out.requestedStopNs<<",\"firstStopMarkerNs\":"<<out.firstSilenceNs<<",\"uncertainThrough\":"<<out.uncertainThrough<<",\"outputState\":"<<static_cast<int>(out.state)<<",\"fault\":"<<static_cast<int>(out.fault)<<",\"ownsOutcome\":"<<(out.ownsOutcome?"true":"false")<<",\"firstSilentCallbackNs\":"<<output_.status().firstSilentCallbackNs<<",\"cursorState\":"<<static_cast<int>(s.cursor.state)<<",\"cursorReason\":"<<static_cast<int>(s.cursor.reason)<<",\"cursorConfirmed\":"<<s.cursor.confirmedThrough<<",\"cursorHasConfirmation\":"<<(s.cursor.hasConfirmation?"true":"false")<<",\"cursorUncertain\":"<<s.cursor.uncertainThrough<<",\"boundaryFactPending\":"<<(s.cursor.boundaryFactPending?"true":"false")<<",\"cursorUUID\":\""<<uuid(s.cursor.owner)<<"\",\"cursorGeneration\":"<<s.cursor.owner.generation<<",\"cursorEpoch\":"<<s.cursor.owner.epoch<<",\"cursorBinding\":"<<s.cursor.binding<<",\"reason\":\""<<reason<<"\"}\n";
        // Synthetic coordinator retains actual immutable outcome above. There is no learner save receipt.
        std::cout<<(failed_?"FAIL ":"PASS ")<<reason<<std::endl;juce::MessageManager::getInstance()->stopDispatchLoop();
    }
    void send(platform::OutputCommand op){platform::Control c;c.op=op;c.owner=owner_;c.epoch=output_.status().lifecycle.request.epoch;c.token=output_.status().lifecycle.observationToken;c.requestedNs=platform::monotonicNs();if(!output_.send(c))finish(true,"output queue refusal");}
    void timerCallback()override {
        output_.service();drain();const auto s=output_.status().lifecycle;
        if(platform::monotonicNs()-start_>30000000000ULL){finish(true,"30 second watchdog");return;}
        if(s.state==output::State::Fault || captureOverflow){finish(true,"unexpected native fault or capture overflow");return;}
        switch(step_) {
            case 0:{const auto cap=platform::defaultOutputCapability();if(!cap.valid||cap.uid!="BuiltInSpeakerDevice"||cap.rate!=44100||cap.minFrames>256||cap.maxFrames<256){finish(true,"frozen capability unavailable");return;}if(!output_.connect(cap,{44100,256},nullptr,&sound_,desktop::PreviewSound::observe,desktop::PreviewSound::render)){finish(true,"connect failed");return;}++step_;break;}
            case 1:if(s.state==output::State::Observed){observed_=platform::monotonicNs();++step_;}break;
            case 2:if(platform::monotonicNs()-observed_>=250000000ULL){send(platform::OutputCommand::Acknowledge);++step_;}break;
            case 3:if(s.state==output::State::Ready){owner_.id={1,2,3,4,5,6,0x47,8,0x89,10,11,12,13,14,15,16};owner_.generation=1;owner_.epoch=s.request.epoch;sound_.stream.prepare(desktop::previewPlans(owner_,44100),4,2,1);send(platform::OutputCommand::Start);++step_;}break;
            case 4:if(latest_.cursor.completedCycles>=1) {
                sound_.stream.tempo({owner_,1,1,2});sound_.stream.tempo({owner_,1,1,1});auto stale=owner_;++stale.generation;sound_.stream.tempo({stale,1,2,1});
                std::ofstream load(root_+"/ui-load.json");const auto before=platform::monotonicNs();std::this_thread::sleep_for(std::chrono::milliseconds(350));const auto after=platform::monotonicNs();load<<"{\"messageThreadStallBeginNs\":"<<before<<",\"endNs\":"<<after<<",\"beforeCopiedFrame\":"<<latest_.cursor.processedThrough<<",\"requestedMs\":350}\n";++step_;
            }break;
            case 5:if(s.state==output::State::Unresolved){stopped_=platform::monotonicNs();++step_;}break;
            case 6:if(platform::monotonicNs()-stopped_>=200000000ULL){if(latest_.cursor.completedCycles!=4 || latest_.tempoIndex!=2 || latest_.failed || latest_.acceptedCommands!=1 || latest_.rejectedCommands!=2){finish(true,"final scheduler facts incorrect");return;}finish(false,"four shared native cycles and bounded message-thread load completed");}break;
            default:finish(true,"invalid step");
        }
    }
    desktop::PreviewSound sound_;platform::AudioOutputMac output_;scheduler::Owner owner_;scheduler::StreamView latest_;
    std::string root_;std::ofstream events_,facts_,views_,states_;std::uint64_t start_{},observed_{},stopped_{};int step_{};bool done_{},failed_{};
};

// Opt-in available-host reliability check. It keeps callback facts, not raw PCM.
class ReliabilityRun final:private juce::Timer {
public:
    ReliabilityRun(std::string root,polyrhythm::Ratio ratio):root_(std::move(root)),ratio_(ratio) {
        startedNs_=platform::monotonicNs();startTimer(20);
    }
    int result()const{return done_&&!failed_?0:1;}
private:
    void drain() {
        platform::NativeEvent event;while(output_.nextEvent(event)) {
            ++nativeEvents_;
            if(event.kind==26) {++nativeBuffers_;if(event.status)++invalidNativeBuffers_;}
            if(event.kind==68 || event.kind==69)++sleepEvents_;
        }
        scheduler::Fact fact;while(sound_.stream.nextFact(fact))facts_.push_back(fact);
        scheduler::StreamView view;while(sound_.stream.nextView(view))latest_=view;
    }
    void command(platform::OutputCommand op) {
        platform::Control c;c.op=op;c.owner=owner_;
        const auto s=output_.status().lifecycle;
        c.epoch=s.request.epoch;c.token=s.observationToken;
        c.requestedNs=platform::monotonicNs();
        if(!output_.send(c))finish(true,"native command queue refusal");
    }
    bool verify(std::uint64_t& finalFrame,std::array<std::uint64_t,4>& counts)const {
        if(plans_.size()<2 || !plans_[0].compatibleTempo(plans_[1]))return false;
        std::vector<scheduler::Fact> expected;
        expected.reserve(4+1+32*(plans_[0].events().size()+1));
        scheduler::FramePosition anchor{};
        const auto append=[&](scheduler::FactKind kind,std::uint64_t frame,
                              std::uint64_t cycle,const scheduler::TimedEvent* event) {
            scheduler::Fact fact{};fact.kind=kind;fact.owner=owner_;fact.binding=1;
            fact.frame=frame;fact.cycle=cycle;
            if(event) {fact.sourceEvent=event->sourceEvent;fact.role=event->role;
                       fact.action=event->action;}
            expected.push_back(fact);
        };
        for(const auto& event:plans_[0].countIn()) {
            scheduler::FramePosition at;std::uint64_t frame{};
            if(!scheduler::add(anchor,event.offset,at)||!scheduler::round(at,frame))return false;
            append(scheduler::FactKind::Event,frame,0,&event);
        }
        if(!scheduler::add(anchor,plans_[0].introDuration(),anchor) ||
           !scheduler::round(anchor,finalFrame))return false;
        append(scheduler::FactKind::CountInEnded,finalFrame,0,nullptr);
        for(std::uint64_t cycle=0;cycle<32;++cycle) {
            const auto& plan=plans_[cycle<16?0:1];
            for(const auto& event:plan.events()) {
                scheduler::FramePosition at;std::uint64_t frame{};
                if(!scheduler::add(anchor,event.offset,at)||!scheduler::round(at,frame))return false;
                append(scheduler::FactKind::Event,frame,cycle,&event);
            }
            if(!scheduler::add(anchor,plan.duration(),anchor) ||
               !scheduler::round(anchor,finalFrame))return false;
            append(scheduler::FactKind::CycleCompleted,finalFrame,cycle+1,nullptr);
        }
        if(facts_.size()!=expected.size())return false;
        std::uint64_t previousFrame{};
        for(std::size_t i=0;i<facts_.size();++i) {
            const auto& actual=facts_[i],want=expected[i];
            if(actual.kind!=want.kind || !(actual.owner==want.owner) ||
               actual.binding!=want.binding || actual.frame!=want.frame ||
               actual.cycle!=want.cycle || actual.sourceEvent!=want.sourceEvent ||
               actual.role!=want.role || actual.action!=want.action ||
               actual.frame<previousFrame)return false;
            previousFrame=actual.frame;
            if(actual.kind==scheduler::FactKind::Event) {
                if(actual.role==scheduler::Role::CountIn)++counts[0];
                else if(actual.role==scheduler::Role::Reference)++counts[1];
                else if(actual.role==scheduler::Role::LayerA)++counts[2];
                else if(actual.role==scheduler::Role::LayerB)++counts[3];
            }
        }
        return counts[0]==4 && counts[1]==32*4 &&
               counts[2]==32*static_cast<std::uint64_t>(ratio_.x) &&
               counts[3]==32*static_cast<std::uint64_t>(ratio_.y);
    }
    void finish(bool fail,const char* reason) {
        if(done_)return;done_=true;stopTimer();
        output_.service();drain();
        const auto before=output_.status();
        const auto retained=output_.shutdown();
        const auto after=output_.status();
        failed_=fail || before.cleanupFailed || after.cleanupFailed;
        std::ofstream facts(root_+"/facts.csv");
        facts<<"kind,uuid,epoch,generation,binding,frame,cycle,event,role,action\n";
        for(const auto& f:facts_)
            facts<<static_cast<int>(f.kind)<<','<<uuid(f.owner)<<','<<f.owner.epoch<<','
                 <<f.owner.generation<<','<<f.binding<<','<<f.frame<<','<<f.cycle<<','
                 <<f.sourceEvent<<','<<static_cast<int>(f.role)<<','
                 <<static_cast<int>(f.action)<<'\n';
        if(!facts.good())failed_=true;
        std::ofstream result(root_+"/summary.json");
        result<<"{\"failed\":"<<(failed_?"true":"false")
              <<",\"reason\":\""<<reason<<"\",\"ratio\":\""<<ratio_.x<<':'<<ratio_.y
              <<"\",\"rate\":"<<cap_.rate<<",\"uid\":\""<<cap_.uid
              <<"\",\"physicalFrames\":"<<cap_.physicalFrames
              <<",\"bufferFrames\":"<<selectedFrames_
              <<",\"factCount\":"<<facts_.size()
              <<",\"countIn\":"<<counts_[0]<<",\"reference\":"<<counts_[1]
              <<",\"layerA\":"<<counts_[2]<<",\"layerB\":"<<counts_[3]
              <<",\"expectedFinalFrame\":"<<finalFrame_
              <<",\"processed\":"<<latest_.cursor.processedThrough
              <<",\"cycles\":"<<latest_.cursor.completedCycles
              <<",\"tempoIndex\":"<<latest_.tempoIndex
              <<",\"cursorReason\":"<<static_cast<int>(latest_.cursor.reason)
              <<",\"cursorState\":"<<static_cast<int>(latest_.cursor.state)
              <<",\"streamFailed\":"<<(latest_.failed?"true":"false")
              <<",\"nativeEvents\":"<<nativeEvents_
              <<",\"nativeBuffers\":"<<nativeBuffers_
              <<",\"invalidNativeBuffers\":"<<invalidNativeBuffers_
              <<",\"sleepEvents\":"<<sleepEvents_
              <<",\"loadBeginNs\":"<<loadBeginNs_
              <<",\"loadEndNs\":"<<loadEndNs_
              <<",\"loadBeforeFrames\":"<<loadBeforeFrames_
              <<",\"loadAfterFrames\":"<<loadAfterFrames_
              <<",\"loadBeforeCallbacks\":"<<loadBeforeCallbacks_
              <<",\"loadAfterCallbacks\":"<<loadAfterCallbacks_
              <<",\"outputStateBeforeShutdown\":"<<static_cast<int>(before.lifecycle.state)
              <<",\"pendingBeforeShutdown\":"<<(before.lifecycle.pendingOutcome?"true":"false")
              <<",\"retainedStopState\":"<<static_cast<int>(retainedState_)
              <<",\"retainedStopPending\":"<<(retainedPending_?"true":"false")
              <<",\"resolvedState\":"<<static_cast<int>(resolvedState_)
              <<",\"resolvedOwnsOutcome\":"<<(resolvedOwned_?"true":"false")
              <<",\"outputStateAfterShutdown\":"<<static_cast<int>(retained.state)
              <<",\"ownsOutcomeAfterShutdown\":"<<(retained.ownsOutcome?"true":"false")
              <<",\"cleanupFailed\":"<<(after.cleanupFailed?"true":"false")
              <<",\"wallSeconds\":"<<std::setprecision(6)
              <<static_cast<double>(platform::monotonicNs()-startedNs_)/1e9<<"}\n";
        if(!result.good())failed_=true;
        std::cout<<(failed_?"FAIL ":"PASS ")<<reason<<std::endl;
        juce::MessageManager::getInstance()->stopDispatchLoop();
    }
    void timerCallback()override {
        output_.service();drain();
        const auto status=output_.status();
        const auto s=status.lifecycle;
        if(platform::monotonicNs()-startedNs_>100000000000ULL) {
            finish(true,"native long-run watchdog");return;
        }
        if(s.state==output::State::Fault || status.cleanupFailed ||
           latest_.failed || invalidNativeBuffers_) {
            finish(true,"native output or stream fault");return;
        }
        switch(step_) {
            case 0: {
                cap_=platform::defaultOutputCapability();
                if(!cap_.valid || cap_.rate<8000 || cap_.rate>192000 ||
                   cap_.minFrames>256 || cap_.maxFrames<256) {
                    finish(true,"current native output capability unavailable");return;
                }
                selectedFrames_=256;
                if(!output_.connect(cap_,{cap_.rate,selectedFrames_},nullptr,&sound_,
                                    desktop::PreviewSound::observe,
                                    desktop::PreviewSound::render)) {
                    finish(true,"native output connect refused");return;
                }
                ++step_;break;
            }
            case 1:if(s.state==output::State::Observed) {command(platform::OutputCommand::Acknowledge);++step_;}break;
            case 2:if(s.state==output::State::Ready) {
                owner_.id={1,2,3,4,5,6,0x47,8,0x89,10,11,12,13,14,15,16};
                owner_.generation=1;owner_.epoch=s.request.epoch;
                plans_=desktop::previewPlans(owner_,cap_.rate,ratio_);
                std::ofstream plans(root_+"/plans.tsv");
                for(std::size_t index=0;index<2;++index) {
                    const auto& plan=plans_[index];
                    plans<<"plan\t"<<index<<'\t'<<plan.sourceBinding()<<'\t'
                         <<plan.sampleRate()<<'\t'<<plan.duration().n<<'/'
                         <<plan.duration().d<<'\t'<<plan.introDuration().n<<'/'
                         <<plan.introDuration().d<<'\n';
                    for(const auto& event:plan.countIn())
                        plans<<"count-in\t"<<index<<'\t'<<event.sourceEvent<<'\t'
                             <<static_cast<int>(event.role)<<'\t'
                             <<event.offset.n<<'/'<<event.offset.d<<'\n';
                    for(const auto& event:plan.events())
                        plans<<"event\t"<<index<<'\t'<<event.sourceEvent<<'\t'
                             <<static_cast<int>(event.role)<<'\t'
                             <<static_cast<int>(event.action)<<'\t'
                             <<event.structural.numerator()<<'/'
                             <<event.structural.denominator()<<'\t'
                             <<event.offset.n<<'/'<<event.offset.d<<'\n';
                }
                plans.flush();
                if(!plans.good()) {finish(true,"native plan manifest write failed");return;}
                sound_.stream.prepare(plans_,32,16,1);
                command(platform::OutputCommand::Start);++step_;
            }break;
            case 3:
                if(latest_.cursor.completedCycles>=8 && !loadEndNs_) {
                    loadBeforeFrames_=latest_.cursor.processedThrough;
                    loadBeforeCallbacks_=status.callbacks;
                    loadBeginNs_=platform::monotonicNs();
                    std::this_thread::sleep_for(std::chrono::milliseconds(350));
                    loadEndNs_=platform::monotonicNs();
                    output_.service();drain();
                    loadAfterFrames_=latest_.cursor.processedThrough;
                    loadAfterCallbacks_=output_.status().callbacks;
                }
                if(s.state==output::State::Unresolved) {
                    const bool exact=verify(finalFrame_,counts_);
                    if(!exact || latest_.cursor.completedCycles!=32 ||
                       latest_.cursor.processedThrough!=finalFrame_ ||
                       latest_.cursor.state!=scheduler::State::Terminal ||
                       latest_.cursor.reason!=scheduler::StopReason::Requested ||
                       latest_.tempoIndex!=1 || !s.pendingOutcome ||
                       !(s.owner==owner_) || status.renderedBlocks==0 ||
                       nativeBuffers_==0 || sleepEvents_!=0 ||
                       loadAfterFrames_<=loadBeforeFrames_ ||
                       loadAfterCallbacks_<=loadBeforeCallbacks_) {
                        finish(true,"native facts load or retained stop incorrect");return;
                    }
                    retainedState_=s.state;retainedPending_=s.pendingOutcome;
                    command(platform::OutputCommand::ResolveOutcome);++step_;
                }
                break;
            case 4:
                if(s.state==output::State::Ready && !s.ownsOutcome && !s.pendingOutcome) {
                    resolvedState_=s.state;resolvedOwned_=s.ownsOutcome;
                    if(!output_.disconnect()) {finish(true,"native disconnect refused");return;}
                    finish(false,"32 native shared-clock cycles and resolved stop completed");
                }
                break;
            default:finish(true,"invalid native reliability step");
        }
    }
    desktop::PreviewSound sound_;platform::AudioOutputMac output_;
    scheduler::Owner owner_;scheduler::StreamView latest_;
    platform::OutputCapability cap_;std::vector<scheduler::Plan> plans_;
    std::vector<scheduler::Fact> facts_;std::string root_;polyrhythm::Ratio ratio_;
    std::array<std::uint64_t,4> counts_{};
    std::uint64_t startedNs_{},loadBeginNs_{},loadEndNs_{},loadBeforeFrames_{},
                  loadAfterFrames_{},loadBeforeCallbacks_{},loadAfterCallbacks_{},
                  nativeEvents_{},nativeBuffers_{},invalidNativeBuffers_{},sleepEvents_{},
                  finalFrame_{};
    std::uint32_t selectedFrames_{};int step_{};bool done_{},failed_{};
    output::State retainedState_{output::State::Closed},resolvedState_{output::State::Closed};
    bool retainedPending_{},resolvedOwned_{};
};
}
int main(int argc,char** argv){
    if(argc==3&&std::string(argv[1])=="--accessibility-capture")return accessibilityCapture(argv[2]);
    if(argc==3&&std::string(argv[1])=="--action-keys")return actionKeyCapture(argv[2]);
    if(argc==2&&std::string(argv[1])=="--preflight"){auto c=fathom::platform::defaultOutputCapability();std::cout<<"valid="<<c.valid<<" uid="<<c.uid<<" rate="<<c.rate<<" physicalFrames="<<c.physicalFrames<<" min="<<c.minFrames<<" max="<<c.maxFrames<<" channels="<<c.outputChannels<<'\n';return c.valid?0:1;}
    if(argc==4 && std::string(argv[1])=="--reliability") {
        fathom::polyrhythm::Ratio ratio{};
        if(std::string(argv[2])=="5:7")ratio={5,7};
        else if(std::string(argv[2])=="3:2")ratio={3,2};
        else return 2;
        if(std::filesystem::exists(argv[3]))return 2;
        std::filesystem::create_directories(argv[3]);
        captureEnabled=false;
        [NSApplication sharedApplication];
        [NSApp setActivationPolicy:NSApplicationActivationPolicyProhibited];
        juce::ScopedJuceInitialiser_GUI gui;
        ReliabilityRun run(argv[3],ratio);
        juce::MessageManager::getInstance()->runDispatchLoop();
        return run.result();
    }
    if(argc!=3||std::string(argv[1])!="--run")return 2;
    [NSApplication sharedApplication];[NSApp setActivationPolicy:NSApplicationActivationPolicyProhibited];juce::ScopedJuceInitialiser_GUI gui;
    Run run(argv[2]);juce::MessageManager::getInstance()->runDispatchLoop();return run.result();
}
