#include "content/LearnSourceIndex.hpp"
#include "content/LearnSourceIndexPins.hpp"
#include "content/Canonical.hpp"
#include <sstream>
#include <map>
#include <set>

namespace fathom::learn {
namespace {
using V=json::Value;
void need(bool okay,const std::string& message){if(!okay)throw std::runtime_error(message);}
const V& at(const V& value,const char* key){return value.object().at(key);}
std::string text(const V& value,const char* key){const auto& s=at(value,key).string();need(!s.empty(),std::string{"Empty source field: "}+key);return s;}
std::uint32_t ordinal(const V& value,const char* key){std::int64_t n=0;need(at(value,key).integer(n)&&n>0&&n<=100000,"Invalid source ordinal");return static_cast<std::uint32_t>(n);}
void pin(const std::string& value){need(value.size()==64&&value.find_first_not_of("0123456789abcdef")==std::string::npos,"Invalid source SHA-256");}
json::Limits limits(std::size_t bytes){json::Limits result;result.bytes=bytes;result.values=500000;result.depth=40;result.stringBytes=65536;return result;}
Binding binding(const V& value,const std::string& source,const std::set<std::string>& candidates){
    Binding result{text(value,"item_id"),text(value,"package_sha256"),{},false};pin(result.packageHash);
    std::set<std::string> variants;
    for(const auto& v:at(value,"variant_ids").array()){need(!v.string().empty()&&variants.insert(v.string()).second,"Duplicate or empty source variant");result.variants.push_back(v.string());}
    need(!result.variants.empty(),"Source binding has no variants");
    const auto& covered=at(value,"covered_source_identities").array();
    result.exact=candidates.count(result.itemId)&&text(value,"source_extent_kind")=="exact_single_printed_unit_candidate"&&covered.size()==1&&covered[0].string()==source;
    result.supplemental=candidates.count(result.itemId)&&text(value,"source_extent_kind")=="supplemental_worked_example"&&covered.size()==1&&covered[0].string()==source;
    return result;
}
}
std::shared_ptr<const SourceIndex> SourceIndex::load(const std::filesystem::path& directory,
    const content::CancellationCheck& canceled){
    content::checkLoadCanceled(canceled);
    const auto index=content::readBounded(directory/"index.json",4*1024*1024,canceled);
    content::checkLoadCanceled(canceled);
    const auto exercises=content::readBounded(directory/"exercises.jsonl",32*1024*1024,canceled);
    content::checkLoadCanceled(canceled);
    const auto overlay=content::readBounded(directory/"accepted-overlay.json",1024*1024,canceled);
    content::checkLoadCanceled(canceled);
    auto result=parse(index,exercises,overlay,installedSourceIndexPins,canceled);
    content::checkLoadCanceled(canceled);
    return std::make_shared<const SourceIndex>(std::move(result));
}
SourceIndex SourceIndex::parse(const std::string& indexBytes,const std::string& exerciseBytes,const std::string& overlayBytes,const Pins& pins,
    const content::CancellationCheck& canceled){
    const auto checkpoint=[&]{content::checkLoadCanceled(canceled);};
    checkpoint();
    pin(pins.index);pin(pins.exercises);pin(pins.overlay);
    need(indexBytes.size()<=4*1024*1024&&exerciseBytes.size()<=32*1024*1024&&overlayBytes.size()<=1024*1024,"Learn index exceeds its byte bound");
    need(content::sha256(indexBytes)==pins.index&&content::sha256(exerciseBytes)==pins.exercises&&content::sha256(overlayBytes)==pins.overlay,"Learn source resources differ from the reviewed version");
    checkpoint();
    const auto index=json::parse(indexBytes,limits(4*1024*1024));
    checkpoint();
    need(text(index,"schema_version")=="fathom-private-learn-source-index.1","Unsupported Learn source index");
    SourceIndex result;
    std::map<std::string,std::pair<std::size_t,std::size_t>> sublevels;
    std::map<std::string,std::vector<std::pair<std::uint32_t,std::uint32_t>>> segments;
    std::map<std::string,std::size_t> expectedCounts;
    std::map<int,std::pair<std::string,std::string>> originals;
    for(const auto& level:at(index,"levels").array()){
        checkpoint();
        const auto number=ordinal(level,"level");need(number==result.levels_.size()+1&&number<=105,"Learn levels must retain numeric source order1 through105");
        Level next{static_cast<int>(number),text(level,"display_title"),{}};
        const auto& original=at(level,"originals");originals[next.number]={text(at(original,"txt"),"sha256"),text(at(original,"pdf"),"sha256")};
        for(const auto& sub:at(level,"sublevels").array()){
            Sublevel group{text(sub,"key"),text(sub,"label"),{}};
            need(sublevels.emplace(group.key,std::make_pair(result.levels_.size(),next.sublevels.size())).second,"Duplicate source sublevel identity");
            expectedCounts[group.key]=ordinal(sub,"exercise_count");
            for(const auto& segment:at(sub,"source_segments").array()){
                const auto first=ordinal(segment,"first_level_ordinal"),last=ordinal(segment,"last_level_ordinal");
                need(first<=last&&(segments[group.key].empty()||segments[group.key].back().second<first),"Invalid source segment order");
                segments[group.key].push_back({first,last});
            }
            next.sublevels.push_back(std::move(group));
        }
        result.levels_.push_back(std::move(next));
    }
    need(result.levels_.size()==105,"Learn index must retain all105 source levels");
    std::istringstream input(exerciseBytes);std::string line;std::set<std::string> sources;
    std::map<int,std::uint32_t> levelOrder;std::map<std::string,std::uint32_t> sublevelOrder;
    while(std::getline(input,line)){
        checkpoint();
        need(!line.empty()&&line.size()<=256*1024,"Empty or oversized source exercise row");
        need(result.exercises_.size()<100000,"Learn source row count exceeds limit");
        const auto row=json::parse(line,limits(256*1024));const auto level=ordinal(row,"level");
        Exercise exercise;auto& source=exercise.source;
        source.levelKey=std::to_string(level);source.sublevelKey=text(row,"sublevel_key");source.sourceExerciseKey=text(row,"source_identity");
        source.sourceOrder=ordinal(row,"sublevel_ordinal");source.levelOrder=ordinal(row,"level_ordinal");
        need(sources.insert(source.sourceExerciseKey).second,"Duplicate source exercise key");
        const auto group=sublevels.find(source.sublevelKey);need(group!=sublevels.end()&&group->second.first+1==level,"Exercise sublevel differs from source level");
        need(source.sourceOrder==++sublevelOrder[source.sublevelKey]&&source.levelOrder==++levelOrder[static_cast<int>(level)],"Source exercise order is missing, duplicated or reversed");
        const auto txt=text(row,"txt_sha256"),pdf=text(row,"pdf_sha256");pin(txt);pin(pdf);
        need(originals.at(static_cast<int>(level))==std::make_pair(txt,pdf),"Exercise originals differ from source level");
        source.sourceRevision=txt+":"+pdf;source.indexRevision=pins.index+":"+pins.exercises+":"+pins.overlay;
        exercise.label=text(row,"printed_label");exercise.auditStatus=text(row,"audit_status");
        const auto& txtLocator=at(row,"txt_locator");const auto& pdfLocator=at(row,"pdf_locator");
        exercise.locator=txtLocator.isObject()?"Original TXT lines "+json::stringify(at(txtLocator,"line_start"))+"–"+json::stringify(at(txtLocator,"line_end")):"Original TXT locator unavailable";
        exercise.locator+=pdfLocator.isObject()?"; PDF pages "+json::stringify(at(pdfLocator,"physical_pages")):"; original PDF locator unavailable";
        std::set<std::string> candidates;
        for(const auto& candidate:at(row,"single_exercise_binding_candidates").array())need(candidates.insert(candidate.string()).second,"Duplicate exact-unit candidate");
        std::set<std::string> bindingIds;
        for(const auto& b:at(row,"frozen_installed_bindings").array()){
            auto bound=binding(b,source.sourceExerciseKey,candidates);need(bindingIds.insert(bound.itemId).second,"Duplicate source binding");
            exercise.bindings.push_back(std::move(bound));
        }
        for(const auto& candidate:candidates)need(bindingIds.count(candidate),"Exact-unit candidate has no binding");
        bool inSegment=false;for(const auto& segment:segments.at(source.sublevelKey))if(source.levelOrder>=segment.first&&source.levelOrder<=segment.second)inSegment=true;
        need(inSegment,"Source exercise falls outside its reviewed segment");
        result.levels_[group->second.first].sublevels[group->second.second].exercises.push_back(result.exercises_.size());
        result.exercises_.push_back(std::move(exercise));
    }
    need(result.exercises_.size()==ordinal(index,"exercise_count"),"Source exercise count differs from reviewed index");
    for(const auto& level:result.levels_)for(const auto& sub:level.sublevels)need(sub.exercises.size()==expectedCounts.at(sub.key),"Source sublevel count mismatch");
    const auto overlay=json::parse(overlayBytes,limits(1024*1024));
    checkpoint();
    need(text(overlay,"schema_version")=="fathom-learn-accepted-overlay.1"&&text(overlay,"base_exercises_sha256")==pins.exercises,"Learn overlay differs from frozen source index");
    std::set<std::string> overlaid;
    for(const auto& entry:at(overlay,"entries").array()){
        checkpoint();
        const auto key=text(entry,"source_identity");need(overlaid.insert(key).second,"Duplicate accepted source overlay");
        auto found=std::find_if(result.exercises_.begin(),result.exercises_.end(),[&](const auto& e){return e.source.sourceExerciseKey==key;});
        need(found!=result.exercises_.end(),"Accepted overlay source is absent");
        const auto& b=at(entry,"binding");auto next=binding(b,key,{text(b,"item_id")});
        if(key=="level080/modulea/p003-card01/cmaj7melodyefge")
            need(next.supplemental&&!next.exact&&next.itemId=="fg:item:001179"&&
                 next.variants==std::vector<std::string>{"fg:variant:007696"}&&
                 next.packageHash=="cf7b66d9bf1382cc18de099bdd4e404e2065ba0a4690e01f864b4efbfefd3106",
                 "Level80 overlay must be the reviewed non-exact supplemental example");
        else need(next.exact&&!next.supplemental,"Overlay must name exactly one complete original source unit");
        pin(text(entry,"acceptance_sha256"));pin(text(entry,"mapping_decision_sha256"));
        need(std::none_of(found->bindings.begin(),found->bindings.end(),[&](const auto& old){return old.itemId==next.itemId;}),"Overlay duplicates existing admitted mapping");
        found->bindings.push_back(std::move(next));found->auditStatus+="; accepted installed overlay";
    }
    checkpoint();
    return result;
}
const Level& SourceIndex::level(int number)const{if(number<1||number>static_cast<int>(levels_.size()))throw std::out_of_range("Unknown source level");return levels_[static_cast<std::size_t>(number-1)];}
const Sublevel& SourceIndex::sublevel(int number,const std::string& key)const{for(const auto& s:level(number).sublevels)if(s.key==key)return s;throw std::out_of_range("Unknown source sublevel");}
std::vector<const Exercise*> SourceIndex::range(int number,const std::string& key,const std::string& first,const std::string& last)const{
    const auto& group=sublevel(number,key);const Exercise* a=nullptr;const Exercise* b=nullptr;
    for(const auto& e:exercises_){if(e.source.sourceExerciseKey==first)a=&e;if(e.source.sourceExerciseKey==last)b=&e;}
    need(a&&b,"Choose both source exercises");
    need(a->source.levelKey==std::to_string(number)&&b->source.levelKey==std::to_string(number)&&a->source.sublevelKey==key&&b->source.sublevelKey==key,"Choose exercises within one source sublevel");
    need(a->source.sourceOrder<=b->source.sourceOrder,"End exercise precedes start exercise");
    std::vector<const Exercise*> selected;
    for(auto i:group.exercises){const auto& e=exercises_[i];if(e.source.sourceOrder>=a->source.sourceOrder&&e.source.sourceOrder<=b->source.sourceOrder)selected.push_back(&e);}
    need(selected.size()==b->source.sourceOrder-a->source.sourceOrder+1,"Selected source range contains a gap");
    for(std::size_t i=1;i<selected.size();++i)need(selected[i]->source.levelOrder==selected[i-1]->source.levelOrder+1,"Range crosses separate source segments");
    return selected;
}
}
