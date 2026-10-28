// Actual JUCE Learn/Practice/Store views with only device I/O substituted.
#define main retained_shared_audio_campaign_main
#include "shared_audio_settings_tests.cpp"
#undef main
#include <array>

int main(int argc,char** argv){int checks=0;try{
    if(argc!=31)throw std::runtime_error("Expected base, 28 finite extensions and fresh output");
    const std::filesystem::path out=argv[30];
    if(!out.is_absolute()||std::filesystem::exists(out))throw std::runtime_error("Fresh absolute evidence directory required");
    std::filesystem::create_directories(out);std::ofstream trace(out/"checks.tsv");juce::ScopedJuceInitialiser_GUI gui;
    auto ck=[&](bool yes,const std::string& name){++checks;trace<<name<<'\t'<<(yes?"PASS":"FAIL")<<std::endl;if(!yes)throw std::runtime_error(name);};
    Harness h(out,"private-profile");auto& learn=A::lessons(*h.home);
    std::vector<std::filesystem::path> extensions;for(int i=2;i<=29;++i)extensions.emplace_back(argv[i]);
    ck(learn.load(argv[1],extensions),"load exact 28-extension app Catalog");
    auto snapshot=[&](const std::string& name){auto reply=capture_fixture::confirmed(h.store->snapshot(storage::newUuid()));
        capture_fixture::write(out/(name+".json"),storage::canonical(reply.data));return reply;};
    auto headingText=[&]{
        for(auto* child:h.practice().getChildren()){
            if(const auto* label=dynamic_cast<juce::Label*>(child)){
                auto text=label->getText().toStdString();
                if(text.rfind("Level ",0)==0)return text;
            }
        }
        return std::string{};
    };
    auto before=snapshot("before");
    ck(before.data.object().at("authoritative").object().at("identity").array().empty(),"fresh profile starts without Attempt");
    click(*h.home,"Learn");
    const std::array<std::string,1> variants{"fg:variant:007696"};
    for(std::size_t pick=0;pick<variants.size();++pick){
        ck(learn.selectLesson("fg:item:001179")&&learn.selectVariant(variants[pick]),"select exact supplemental melody case");
        const auto admitted=learn.catalog()->admit("fg:item:001179",variants[pick]);
        ck(admitted&&admitted->practiceAllowed()&&admitted->span()==Rational{4},"Practice admission is exact q4");
        click(learn,"Practice selected case");
        if(const auto* summary=dynamic_cast<juce::Label*>(learn.findChildWithID("summary")))
            trace<<"post-click summary\t"<<summary->getText().toStdString()<<std::endl;
        h.wait([&]{return h.home->page()==H::Page::Practice;},"queued supplemental Practice navigation");
        ck(h.home->page()==H::Page::Practice,"Learn opened actual Practice view");
        const auto token=h.practice().lessonAdmission();
        ck(token&&token->identity()==admitted->identity()&&token->model()->source().events.size()==4,
           "Practice retains immutable source-bound one-variant example and 4 events");
        const auto* instructions=dynamic_cast<juce::Label*>(h.practice().findChildWithID("practice-authored-source"));
        ck(instructions&&instructions->getText().toStdString().find(learn.catalog()->variant("fg:item:001179",variants[pick]).label)!=std::string::npos,
           "Practice displays selected authored variant");
        const auto heading=headingText();trace<<"supplemental heading\t"<<heading<<std::endl;
        ck(heading.find("picking direction unspecified")!=std::string::npos,
           "null source pick displays truthful unspecified direction");
        ck(snapshot("navigation-"+std::to_string(pick)).data.object().at("authoritative").object().at("identity").array().empty(),
           "navigation alone creates no Attempt or credit");
        click(h.practice(),"Back");h.wait([&]{return h.home->page()==H::Page::Learn;},"queued Back to Learn");
        ck(learn.selectedVariant()==variants[pick],"Back preserves exact supplemental variant");
    }
    for(const auto& [variant,direction]:std::array<std::pair<const char*,const char*>,2>{{
        {"fg:variant:007694","D"},{"fg:variant:007695","U"}}}){
        ck(learn.selectLesson("fg:item:001178")&&learn.selectVariant(variant),"select retained non-null Rung08 pick");
        click(learn,"Practice selected case");h.wait([&]{return h.home->page()==H::Page::Practice;},"retained pick Practice navigation");
        ck(headingText().find(std::string(" | ")+direction+" start")!=std::string::npos,
           "retained D/U Practice heading unchanged");
        click(h.practice(),"Back");h.wait([&]{return h.home->page()==H::Page::Learn;},"retained pick Back");
    }
    ck(snapshot("after").data.object().at("authoritative").object().at("identity").array().empty(),
       "unsaved Practice makes no Attempt");
    std::cout<<"PASS "<<checks<<" Level80 supplemental Learn-to-Practice no-credit checks\n";return 0;
}catch(const std::exception& e){std::cerr<<"FAIL after "<<checks<<" checks: "<<e.what()<<'\n';return 1;}}
