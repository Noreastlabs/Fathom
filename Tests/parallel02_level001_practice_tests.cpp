// Actual JUCE Learn/Practice/Store views with only device I/O substituted.
#define main retained_shared_audio_campaign_main
#include "shared_audio_settings_tests.cpp"
#undef main
#include <array>
int main(int argc,char** argv){int checks=0;try{
    if(argc!=35)throw std::runtime_error("Expected base, 32 finite extensions and fresh output");
    const std::filesystem::path out=argv[34];
    if(!out.is_absolute()||std::filesystem::exists(out))throw std::runtime_error("Fresh absolute evidence directory required");
    std::filesystem::create_directories(out);std::ofstream trace(out/"checks.tsv");juce::ScopedJuceInitialiser_GUI gui;
    auto ck=[&](bool yes,const std::string& name){++checks;trace<<name<<'\t'<<(yes?"PASS":"FAIL")<<std::endl;if(!yes)throw std::runtime_error(name);};
    Harness h(out,"private-profile");auto& learn=A::lessons(*h.home);
    std::vector<std::filesystem::path> extensions;for(int i=2;i<=33;++i)extensions.emplace_back(argv[i]);
    ck(learn.load(argv[1],extensions),"load exact 32-extension app Catalog");
    auto snapshot=[&](const std::string& name){auto reply=capture_fixture::confirmed(h.store->snapshot(storage::newUuid()));
        capture_fixture::write(out/(name+".json"),storage::canonical(reply.data));return reply;};
    ck(snapshot("before").data.object().at("authoritative").object().at("identity").array().empty(),
       "fresh profile starts without Attempt");
    click(*h.home,"Learn");
    const std::array<std::pair<std::string,std::string>,6> picks{{
        {"fg:item:000001","fg:variant:007478"},
        {"fg:item:000040","fg:variant:007533"},
        {"fg:item:000067","fg:variant:007586"},
        {"fg:item:000094","fg:variant:007641"},
        {"fg:item:000119","fg:variant:007690"},
        {"fg:item:000120","fg:variant:007693"}}};
    for(std::size_t k=0;k<picks.size();++k){
        ck(learn.selectLesson(picks[k].first)&&learn.selectVariant(picks[k].second),"select exact Level1 full48 D/U source unit");
        const auto admitted=learn.catalog()->admit(picks[k].first,picks[k].second);
        ck(admitted&&admitted->practiceAllowed()&&admitted->span()==Rational{48},"Practice admission exact q48");
        click(learn,"Practice selected case");h.wait([&]{return h.home->page()==H::Page::Practice;},"queued Level1 Practice navigation");
        ck(h.home->page()==H::Page::Practice,"Learn opened actual Practice view");
        const auto token=h.practice().lessonAdmission();
        ck(token&&token->identity()==admitted->identity()&&token->model()->source().events.size()==48,
           "Practice retains immutable source-bound D/U identity and 48 contacts");
        const auto* instructions=dynamic_cast<juce::Label*>(h.practice().findChildWithID("practice-authored-source"));
        ck(instructions&&instructions->getText().toStdString().find(learn.catalog()->variant(picks[k].first,picks[k].second).label)!=std::string::npos,
           "Practice shows selected authored variant");
        ck(snapshot("navigation-"+std::to_string(k)).data.object().at("authoritative").object().at("identity").array().empty(),
           "navigation alone creates no Attempt or credit");
        click(h.practice(),"Back");h.wait([&]{return h.home->page()==H::Page::Learn;},"queued Back to Learn");
        ck(learn.selectedVariant()==picks[k].second,"Back preserves exact variant");
    }
    ck(snapshot("after").data.object().at("authoritative").object().at("identity").array().empty(),
       "unsaved Practice creates no Attempt");
    std::cout<<"PASS "<<checks<<" Level1 full48 Learn-to-Practice no-credit checks\n";return 0;
}catch(const std::exception& e){std::cerr<<"FAIL after "<<checks<<" checks: "<<e.what()<<'\n';return 1;}}
