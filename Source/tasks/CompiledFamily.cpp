#include "tasks/TaskContract.hpp"
#include "GeneratedTriadFamily.hpp"

namespace fathom::tasks {
const std::vector<std::string>& compiledFamilyKeys() {
    static const auto keys=[] {std::vector<std::string> result;
        for(const auto& row:compiled_family::rows)result.push_back(row.key);return result;}();
    return keys;
}
const Definition& compiledFamilyDefinition(const std::string& key) {
    const auto& keys=compiledFamilyKeys();std::size_t selected=0;
    while(selected<keys.size()&&keys[selected]!=key)++selected;
    if(selected==keys.size())throw Error("COMPILED_FAMILY_SCOPE","Only exact compiled source keys are available");
    static const auto definitions=[] {
        std::vector<Definition> result;result.reserve(compiled_family::rows.size());
        for(const auto& row:compiled_family::rows) {
            const auto reports=json::parse(row.reports);
            ReportContract contract{reports.object().at("setup"),reports.object().at("actions").array(),reports.object().at("release")};
            auto setup=compiled_family::setup;
            setup.push_back(row.fingers);
            std::string written="Written low/middle/high: ";
            const auto& notes=contract.setup.object().at("named_notes_low_to_high").array();
            const auto& degrees=contract.setup.object().at("named_degrees_low_to_high").array();
            for(std::size_t n=0;n<notes.size();++n){if(n)written+=", ";written+=notes[n].string()+" ("+degrees[n].string()+")";}
            setup.push_back(std::move(written));
            std::string contacts="Source contacts low/middle/high: ";
            for(std::size_t n=0;n<row.voices.size();++n){if(n)contacts+=", ";contacts+="string "+std::to_string(row.voices[n].sourceString)+" fret "+std::to_string(row.voices[n].fret);}
            setup.push_back(std::move(contacts));
            auto context=compiled_family::commonContext;
            const auto& local=compiled_family::contexts.at(row.context);
            context.insert(context.end(),local.begin(),local.end());
            const std::vector<Action> actions{
                {"Play the blocked triad",{row.voices[0],row.voices[1],row.voices[2]},Rational{0,1}},
                {"Play the low note",{row.voices[0]},Rational{1,1}},
                {"Play the middle note",{row.voices[1]},Rational{2,1}},
                {"Play the high note",{row.voices[2]},Rational{3,1}}};
            result.push_back(Definition{row.key,row.label,compiled_family::policy,row.provenance,
                std::move(setup),std::move(context),compiled_family::release,
                compiled_family::pacedExplanation,actions,Rational{4,1},std::move(contract)});
        }
        return result;
    }();
    return definitions[selected];
}
} // namespace fathom::tasks
