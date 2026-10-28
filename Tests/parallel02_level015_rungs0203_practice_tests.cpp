// Actual JUCE Learn/Practice/Store views with only device I/O substituted.
#define main retained_shared_audio_campaign_main
#include "shared_audio_settings_tests.cpp"
#undef main
#include <array>
int main(int argc,char** argv){int checks=0;try{
    if(argc!=34)throw std::runtime_error("Expected base, 31 finite extensions and fresh output");
    const std::filesystem::path out=argv[33];
    if(!out.is_absolute()||std::filesystem::exists(out))throw std::runtime_error("Fresh absolute evidence directory required");
    std::filesystem::create_directories(out);std::ofstream trace(out/"checks.tsv");juce::ScopedJuceInitialiser_GUI gui;
    auto ck=[&](bool yes,const std::string& name){++checks;trace<<name<<'\t'<<(yes?"PASS":"FAIL")<<std::endl;if(!yes)throw std::runtime_error(name);};
    Harness h(out,"private-profile");auto& learn=A::lessons(*h.home);
    std::vector<std::filesystem::path> extensions;for(int i=2;i<=32;++i)extensions.emplace_back(argv[i]);
    ck(learn.load(argv[1],extensions),"load exact 31-extension app Catalog");
    auto snapshot=[&](const std::string& name){auto reply=capture_fixture::confirmed(h.store->snapshot(storage::newUuid()));
        capture_fixture::write(out/(name+".json"),storage::canonical(reply.data));return reply;};
    ck(snapshot("before").data.object().at("authoritative").object().at("identity").array().empty(),
       "fresh profile starts without Attempt");
    click(*h.home,"Learn");
    const std::array<std::pair<std::string,std::string>,4> picks{{
        {"fg:item:001181","fg:variant:007702"},{"fg:item:001181","fg:variant:007703"},
        {"fg:item:001182","fg:variant:007704"},{"fg:item:001182","fg:variant:007705"}}};
    for(std::size_t k=0;k<picks.size();++k){
        ck(learn.selectLesson(picks[k].first)&&learn.selectVariant(picks[k].second),"select exact Level15 cell D/U case");
        const auto admitted=learn.catalog()->admit(picks[k].first,picks[k].second);
        ck(admitted&&admitted->practiceAllowed()&&admitted->span()==Rational{26},"Practice admission exact q26");
        click(learn,"Practice selected case");h.wait([&]{return h.home->page()==H::Page::Practice;},"queued Level15 Practice navigation");
        ck(h.home->page()==H::Page::Practice,"Learn opened actual Practice view");
        const auto token=h.practice().lessonAdmission();
        ck(token&&token->identity()==admitted->identity()&&token->model()->source().events.size()==78,
           "Practice retains immutable source-bound D/U identity and 78 contacts");
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
    std::cout<<"PASS "<<checks<<" Level15 Rungs02-03 Learn-to-Practice no-credit checks\n";return 0;
}catch(const std::exception& e){std::cerr<<"FAIL after "<<checks<<" checks: "<<e.what()<<'\n';return 1;}}
