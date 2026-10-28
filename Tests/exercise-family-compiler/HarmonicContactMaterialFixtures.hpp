#pragma once
// Test-only synthetic manual reports. Never use this header in production UI.
#include "tasks/OrderedContactTaskFormAdapter.hpp"
#include <algorithm>
#include <stdexcept>

namespace fathom::test::harmonic_contact_material {
namespace M=tasks::ordered_contacts::manual;
using J=json::Value;
inline const J& at(const J& v,const char* key) {
    if(!v.isObject()||!v.find(key))throw std::invalid_argument("TEST_FIXTURE_FIELD");return *v.find(key);
}
inline J positiveFor(const M::Task& task,const M::OpenForm& form,M::Action action) {
    if(task.sourceHandle().family()!=tasks::manual_contacts::Family::HarmonicContact)
        throw std::invalid_argument("TEST_FIXTURE_HARMONIC_FAMILY_ONLY");
    const auto program=json::parse(task.sourceHandle().harmonicProgramJson());
    J::Object result;
    for(const auto& required:at(form.schema,"required").array()) {
        const auto& name=required.string();const auto& shape=*at(form.schema,"properties").find(name);
        J value=nullptr;
        if(name=="evidence") value="Synthetic manual source report; no measured performance";
        else if(const auto* options=shape.find("enum")) {
            value=options->array().front();
            const auto met=std::find(options->array().begin(),options->array().end(),J("reported_met"));
            if(met!=options->array().end())value=*met;
            if(name=="setup_read"||name=="one_set"||name=="contact_reported"||name=="hand_release_reported")value=J::fromInteger(2);
        } else if(shape.find("minimum")) value=*shape.find("minimum");
        else throw std::invalid_argument("TEST_FIXTURE_CLOSED_SHAPE");
        result.emplace(name,std::move(value));
    }
    if(action==M::Action::SourceRepairReport) {
        const auto& debt=task.view().sourceRepairDue;
        if(!debt)throw std::invalid_argument("TEST_FIXTURE_REPAIR_DEBT");
        for(const auto& repair:at(program,"repair_options").array())if(at(repair,"id")==J(*debt))
            for(const auto& guard:at(repair,"guards").array())if(at(guard,"kind")==J("minimum"))
                result[at(guard,"field").string()]=at(guard,"value");
    }
    return result;
}
inline J unresolvedFor(const M::Task& task,const M::OpenForm& form,M::Action action,const std::string& field="evidence") {
    auto report=positiveFor(task,form,action);
    if(!report.find(field))throw std::invalid_argument("TEST_FIXTURE_UNKNOWN_FIELD");
    report.object()[field]=nullptr;return report;
}
} // namespace fathom::test::harmonic_contact_material
