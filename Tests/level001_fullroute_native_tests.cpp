#include "content/Level001Extension.hpp"
#include <filesystem>
#include <iostream>
#include <stdexcept>
#include <string>

using J=fathom::json::Value;
using namespace fathom;
namespace {
void check(bool condition,const char* message){if(!condition)throw std::runtime_error(message);std::cout<<"PASS "<<message<<'\n';}
const J& at(const J& v,const char* key){return v.object().at(key);}
J& at(J& v,const char* key){return v.object().at(key);}
bool issue(const content::Result& r,const std::string& code){
    for(const auto& row:at(r.report,"issues").array())if(at(row,"code").string()==code)return true;
    return false;
}
content::Input input(const std::filesystem::path& root){
    const auto read=[&](const char* path){return content::readBounded(root/path,32*1024*1024);};
    auto package=read("Build/manager-resume-r01/level001-whole-candidate-r01/candidate-r01/package.json");
    auto registry=read("Build/manager-resume-r01/level001-whole-candidate-r01/candidate-r01/identity-registry.json");
    auto profile=read("Build/manager-resume-r01/level001-final-profile-r01/expected-profile.final.json");
    return {package,registry,profile,content::sha256(profile),root};
}
void rebound(content::Input& in,const J& altered){
    auto profile=json::parse(in.profile);at(profile,"reference_package")=altered;
    in.package=json::stringify(altered);in.profile=json::stringify(profile);
    in.expectedProfileSha256=content::sha256(in.profile);
}
}
int main(){
    try{
        const std::filesystem::path root=FATHOM_SOURCE_ROOT;
        {
            const auto fixture=root/"Tests/fixtures/canonical_controls";
            const auto package=content::readBounded(fixture/"examples.json",32*1024*1024);
            const auto registry=content::readBounded(fixture/"identity-registry.json",32*1024*1024);
            const auto profile=json::stringify(json::parse(content::readBounded(fixture/"expected-profile.json",32*1024*1024)));
            auto generic=content::validate({package,registry,profile,content::sha256(profile),root});
            check(generic.validReference&&generic.exitCode==2&&generic.records.size()==13,
                "existing Canonical 13-control fixture remains valid/nonadmitted");
        }
        {
            auto in=input(root);auto r=lesson::validateLevel001Extension(in);
            check(r.validReference&&r.exitCode==2&&r.records.size()==108&&r.variants.size()==648,"finite positive valid/nonadmitted 108/648");
            check(!at(r.report,"curriculum_playback_authorized").boolean(),"finite positive playback withheld");
            const auto& f=at(r.report,"finite_level001");
            check(at(f,"new_variants_checked")==J::fromInteger(216)&&at(f,"old_variants_checked")==J::fromInteger(432)&&
                at(f,"emitted_contacts")==J::fromInteger(10368),"all finite routes and contacts checked");
            auto find=[&](const std::string& id)->const content::VariantResult&{
                for(const auto& v:r.variants)if(v.id==id)return v;
                throw std::runtime_error("variant absent");
            };
            for(const auto* id:{"fg:variant:007478","fg:variant:007479"}) {
                const auto& v=find(id);check(v.source.events.size()==48&&v.validation.validReference(),"new D/U model has 48 valid projected contacts");
                const bool down=std::string(id)=="fg:variant:007478";
                for(std::size_t i=0;i<48;++i) {
                    const auto& e=v.source.events[i];const auto expected=((i%2==0)==down)?"D":"U";
                    if(e.handDirection!=expected||!e.span.onset||!(*e.span.onset==Rational{static_cast<std::int64_t>(i),1})||
                        !e.span.duration||!(*e.span.duration==Rational{1,1}))
                        throw std::runtime_error("positive projected contact/grid/parity mismatch");
                }
            }
            check(true,"both starting strokes and quarter grids include turnaround");
            const auto package=json::parse(in.package);std::size_t checked=0;
            for(const auto& record:at(package,"records").array()){
                const auto& source=at(record,"events").array();const auto& variants=at(record,"variants").array();
                for(std::size_t vi=4;vi<6;++vi){
                    const auto id=at(variants[vi],"id").string();const auto& v=find(id);
                    if(v.source.events.size()!=48||source.size()!=48)throw std::runtime_error("full-route coverage differs");
                    for(std::size_t i=0;i<48;++i){
                        const auto& e=v.source.events[i];const auto expected=((i%2==0)==(vi==4))?"D":"U";
                        if(e.id!=at(source[i],"event_id").string()||e.handDirection!=expected||!e.span.onset||
                            !(*e.span.onset==Rational{static_cast<std::int64_t>(i),1})||!e.span.duration||
                            !(*e.span.duration==Rational{1,1}))throw std::runtime_error("full-route source/grid/pick parity differs");
                        ++checked;
                    }
                }
            }
            check(checked==10368,"all 216 projected D/U routes match original occurrence order and quarter parity");
        }
        {
            auto in=input(root);auto package=json::parse(in.package);
            auto& ids=at(at(package,"records").array()[0],"variants").array()[4].object().at("event_ids").array();
            check(ids.size()==48,"membership mutation has frozen 48 predecessor");ids.pop_back();rebound(in,package);
            content::Limits genericLimits;genericLimits.json.values=1100000;
            check(content::validate(in,genericLimits).validReference,"generic Canonical remains workbook-neutral for rebound subset");
            auto r=lesson::validateLevel001Extension(in);
            check(!r.validReference&&r.exitCode==1&&issue(r,"LEVEL001_MEMBERSHIP")&&!issue(r,"PROFILE_HASH"),"rebound 47-contact semantic refusal");
        }
        {
            auto in=input(root);auto package=json::parse(in.package);
            at(at(at(package,"records").array()[0],"variants").array()[4],"grouping").object().at("beat_unit_q")=J::Array{J::fromInteger(1),J::fromInteger(2)};
            rebound(in,package);
            content::Limits genericLimits;genericLimits.json.values=1100000;
            check(content::validate(in,genericLimits).validReference,"generic Canonical retains positive rational grouping semantics");
            auto r=lesson::validateLevel001Extension(in);
            check(!r.validReference&&r.exitCode==1&&issue(r,"LEVEL001_QUARTER_GRID")&&!issue(r,"PROFILE_HASH"),"rebound half-quarter semantic refusal");
        }
        {
            auto in=input(root);
            lesson::Level001StrokeFault fault{"fg:variant:007478",24,"U"};
            auto r=lesson::validateLevel001Extension(in,fault);
            check(!r.validReference&&r.exitCode==1&&issue(r,"LEVEL001_PICK_PARITY"),"actual emitted contact25 repeated stroke refusal");
            for(const auto& v:r.variants)if(v.id==fault.variantId) {
                check(v.source.events[23].handDirection=="U"&&v.source.events[24].handDirection=="U","fault changes emitted model before guard");
                break;
            }
        }
        return 0;
    }catch(const std::exception& e){std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}
}
