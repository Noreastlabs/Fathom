// Actual JUCE Learn/Practice/Store views with only device I/O substituted.
#define main retained_shared_audio_campaign_main
#include "shared_audio_settings_tests.cpp"
#undef main
#include <array>
int main(int argc,char** argv){int checks=0;try{
    if(argc!=32)throw std::runtime_error("Expected base, 29 finite extensions and fresh output");
    const std::filesystem::path out=argv[31];
    if(!out.is_absolute()||std::filesystem::exists(out))throw std::runtime_error("Fresh absolute evidence directory required");
    std::filesystem::create_directories(out);std::ofstream trace(out/"checks.tsv");juce::ScopedJuceInitialiser_GUI gui;
    auto ck=[&](bool yes,const std::string& name){++checks;trace<<name<<'\t'<<(yes?"PASS":"FAIL")<<std::endl;if(!yes)throw std::runtime_error(name);};
    Harness h(out,"private-profile");auto& learn=A::lessons(*h.home);
    std::vector<std::filesystem::path> extensions;for(int i=2;i<=30;++i)extensions.emplace_back(argv[i]);
    ck(learn.load(argv[1],extensions),"load exact 29-extension app Catalog");
    auto snapshot=[&](const std::string& name){auto reply=capture_fixture::confirmed(h.store->snapshot(storage::newUuid()));
        capture_fixture::write(out/(name+".json"),storage::canonical(reply.data));return reply;};
    ck(snapshot("before").data.object().at("authoritative").object().at("identity").array().empty(),
       "fresh profile starts without Attempt");
    click(*h.home,"Learn");
    const std::array<std::string,2> variants{"fg:variant:007382","fg:variant:007383"};
    for(std::size_t pick=0;pick<variants.size();++pick){
        ck(learn.selectLesson("fg:item:001130")&&learn.selectVariant(variants[pick]),"select exact Rung03 B-major D/U cell");
        const auto admitted=learn.catalog()->admit("fg:item:001130",variants[pick]);
        ck(admitted&&admitted->practiceAllowed()&&admitted->span()==Rational{15},"Practice admission is exact nominal q15");
        click(learn,"Practice selected case");h.wait([&]{return h.home->page()==H::Page::Practice;},"queued Rung03 Practice navigation");
        ck(h.home->page()==H::Page::Practice,"Learn opened actual Practice view");
        const auto token=h.practice().lessonAdmission();
        ck(token&&token->identity()==admitted->identity()&&token->model()->source().events.size()==30,
           "Practice retains immutable source-bound D/U case and 30 contacts");
        const auto* instructions=dynamic_cast<juce::Label*>(h.practice().findChildWithID("practice-authored-source"));
        ck(instructions&&instructions->getText().toStdString().find(learn.catalog()->variant("fg:item:001130",variants[pick]).label)!=std::string::npos,
           "Practice displays selected authored D/U variant");
        ck(snapshot("navigation-"+std::to_string(pick)).data.object().at("authoritative").object().at("identity").array().empty(),
           "navigation alone creates no Attempt or credit");
        click(h.practice(),"Back");h.wait([&]{return h.home->page()==H::Page::Learn;},"queued Back to Learn");
        ck(learn.selectedVariant()==variants[pick],"Back preserves exact D/U variant");
    }
    ck(snapshot("after").data.object().at("authoritative").object().at("identity").array().empty(),
       "unsaved Practice makes no Attempt");
    std::cout<<"PASS "<<checks<<" Level13 Rung03 Learn-to-Practice no-credit checks\n";return 0;
}catch(const std::exception& e){std::cerr<<"FAIL after "<<checks<<" checks: "<<e.what()<<'\n';return 1;}}
