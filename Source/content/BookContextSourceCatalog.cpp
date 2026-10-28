#include "content/BookContextSourceCatalog.hpp"
#include "content/Canonical.hpp"
#include "GeneratedBookContextPins.hpp"
#include <algorithm>
#include <cctype>
#include <cstdio>
#include <set>
#include <sstream>
#include <stdexcept>

namespace fathom::curriculum {
namespace {
using J=json::Value;
void require(bool v,const std::string& s){if(!v)throw std::runtime_error(s);}
const J::Object& object(const J& v){require(v.isObject(),"Book context object required");return v.object();}
const J::Array& array(const J& v){require(v.isArray(),"Book context array required");return v.array();}
const J& at(const J& v,const std::string& k){const auto& o=object(v);const auto i=o.find(k);require(i!=o.end(),"Missing book context field: "+k);return i->second;}
std::string text(const J& v){require(v.isString(),"Book context text required");return v.string();}
bool flag(const J& v){require(v.isBool(),"Book context boolean required");return v.boolean();}
std::size_t count(const J& v,std::size_t max){std::int64_t n=0;require(v.integer(n)&&n>=0&&static_cast<std::uint64_t>(n)<=max,"Book context integer outside closed bounds");return static_cast<std::size_t>(n);}
void keys(const J& v,std::initializer_list<const char*> allowed){std::set<std::string> expected;for(const auto* x:allowed)expected.insert(x);std::set<std::string> actual;for(const auto& [k,unused]:object(v)){(void)unused;actual.insert(k);}require(actual==expected,"Book context field set differs from closed schema");}
std::vector<int> pages(const J& v,int max){std::vector<int> out;for(const auto& p:array(v)){auto n=count(p,static_cast<std::size_t>(max));require(n>0,"Physical source pages are one-based");out.push_back(static_cast<int>(n));}return out;}
std::optional<int> line(const J& v,std::size_t max){if(v.null())return std::nullopt;auto n=count(v,max);require(n>0,"Original TXT lines are one-based");return static_cast<int>(n);}
std::filesystem::path checkedRoot(const std::filesystem::path& p){require(p.is_absolute(),"Book context root must be absolute");auto q=std::filesystem::path{};for(const auto& part:p){require(part!=".."&&part!=".","Unsafe book context root");q/=part;require(!std::filesystem::is_symlink(std::filesystem::symlink_status(q)),"Book context root symlink refused");}require(std::filesystem::is_directory(p),"Book context package missing");return std::filesystem::canonical(p);}
std::string exactFile(const std::filesystem::path& root,const char* name,std::size_t size,const char* sha,const content::CancellationCheck& canceled){content::checkLoadCanceled(canceled);auto p=root/name;require(!std::filesystem::is_symlink(std::filesystem::symlink_status(p))&&std::filesystem::is_regular_file(p),"Book context file missing or linked");require(std::filesystem::file_size(p)==size,"Book context file byte size changed");auto b=content::readBounded(p,size,canceled);require(b.size()==size&&content::sha256(b)==sha,"Book context file hash changed");content::checkLoadCanceled(canceled);return b;}
J parse(const std::string& b){json::Limits limits;limits.bytes=b.size();limits.depth=48;limits.values=650000;limits.stringBytes=256*1024;return json::parse(b,limits);}
const J& referenced(const J& map,const J& r){auto n=count(at(r,"reference_slot"),465);const auto& refs=array(at(map,"reference_catalog"));require(n<refs.size(),"Book context custody slot out of range");return refs[n];}
void original(const J& map,const J& source,const J& publicRef,const std::filesystem::path& path,std::size_t bytes,const std::string& sha){
    const auto& pinned=referenced(map,source);
    require(text(at(pinned,"path"))==text(at(publicRef,"path"))&&count(at(pinned,"bytes"),1024*1024)==bytes&&count(at(publicRef,"bytes"),1024*1024)==bytes&&text(at(pinned,"sha256"))==sha&&text(at(publicRef,"sha256"))==sha,"Book source pair differs from verified original library");
    const auto relative=text(at(publicRef,"path"));require(path.generic_string().size()>=relative.size()&&path.generic_string().compare(path.generic_string().size()-relative.size(),relative.size(),relative)==0,"Book original asset location differs");
}
std::vector<std::string> strings(const J& v){std::vector<std::string> out;std::set<std::string> seen;for(const auto& x:array(v)){auto t=text(x);require(!t.empty()&&seen.insert(t).second,"Empty or duplicate public metadata term");out.push_back(std::move(t));}return out;}
std::string lower(std::string v){for(auto& c:v)c=static_cast<char>(std::tolower(static_cast<unsigned char>(c)));return v;}
std::string trim(std::string v){const auto first=v.find_first_not_of(" \t\r\n");if(first==std::string::npos)return {};return v.substr(first,v.find_last_not_of(" \t\r\n")-first+1);}
void unchangedInvariants(const J& flags){
    keys(flags,{"raw_source_facts_unchanged","caller_program_allowed","caller_source_role_allowed","automatic_answer_reveal","actual_source_supplied","hosted_dependency","audio_recording_import_added","new_numeric_ids","learner_credit","global_release","book_or_parent_rollup","full_PDF_context_and_continuations_retained"});
    for(const auto& [k,v]:object(flags)){const bool expected=k=="raw_source_facts_unchanged"||k=="full_PDF_context_and_continuations_retained";require(flag(v)==expected,"Book context scope invariant changed");}
}
} // namespace

BookContextSourceCatalog BookContextSourceCatalog::load(const std::filesystem::path& closedPackage,const SourceLibrary& originals,
    const content::CancellationCheck& canceled){
    using namespace book105pins;
    const auto checkpoint=[&]{content::checkLoadCanceled(canceled);};
    checkpoint();
    const auto root=checkedRoot(closedPackage);std::set<std::string> actual;
    for(const auto& e:std::filesystem::directory_iterator(root)){checkpoint();require(!e.is_symlink()&&e.is_regular_file(),"Unexpected book context package entry");actual.insert(e.path().filename().string());}
    require(actual==std::set<std::string>{"book-context-source-map.json","book-context-source-map.schema.json","public-projection.json"},"Book context package file set changed");
    const auto map=parse(exactFile(root,"book-context-source-map.json",kMapBytes,kMapSha,canceled));
    checkpoint();
    const auto schema=parse(exactFile(root,"book-context-source-map.schema.json",kSchemaBytes,kSchemaSha,canceled));
    checkpoint();
    require(text(at(schema,"$id"))=="fathom.closed-book-context-source-map.1.schema","Book context schema identity changed");
    const auto projected=parse(exactFile(root,"public-projection.json",kPublicBytes,kPublicSha,canceled));
    checkpoint();
    require(text(at(map,"schema"))=="fathom.closed-book-context-source-map.1"&&text(at(projected,"schema"))=="fathom.closed-book-context-public-projection.1","Book context package identity changed");
    const auto& metadataAuthority=at(projected,"metadata_authority");
    keys(metadataAuthority,{"source_content_sha256","accepted_plan_sha256","scope","context_links_are_task_admission"});
    require(text(at(metadataAuthority,"source_content_sha256"))=="8e14d1df140dfd329ba6fe6d993489b1407b0a39d50f1920fc1a8db8abc57d56"&&text(at(metadataAuthority,"accepted_plan_sha256"))=="cb3c3f7a47343ac0255dbdb8bf53411af6dd7b929c101b04d00ed62d6e3f637a"&&text(at(metadataAuthority,"scope"))=="reviewed_public_card_metadata_only"&&!flag(at(metadataAuthority,"context_links_are_task_admission")),"Public metadata source/authority changed");
    unchangedInvariants(at(map,"collection_invariants"));unchangedInvariants(at(projected,"invariants"));
    const auto& bind=at(projected,"bindings");
    require(text(at(bind,"map_sha256"))==kMapSha&&text(at(bind,"schema_sha256"))==kSchemaSha&&text(at(bind,"descriptor_sha256"))==kDescriptorSha&&text(at(bind,"source_index_sha256"))==kSourceIndexSha&&text(at(bind,"map_review_sha256"))==kMapReviewSha,"Book context authority binding changed");
    require(text(at(bind,"map_review"))=="EXACT_SOURCE_DATA_ACCEPTED_NATIVE_PRESENTATION_PENDING"&&text(at(bind,"notice_review"))=="EXACT_NOTICE_SOURCE_ACCEPTED_NATIVE_PRESENTATION_PENDING","Book context review scope changed");
#if defined(FATHOM_CONTENT_FREE_DISTRIBUTION)
    static_assert(kChildDenominator==0 && kSnapshotAcceptedChildren==0 && kSnapshotPendingChildren==0
        && kManualAcceptedChildren==0 && kOrdinaryRuntimeAcceptedChildren==0,
        "Content-free distribution must contain no accepted source records");
#else
    static_assert(kChildDenominator==7271 && kSnapshotAcceptedChildren+kSnapshotPendingChildren==kChildDenominator && kManualAcceptedChildren+kOrdinaryRuntimeAcceptedChildren==kSnapshotAcceptedChildren,"Closed trusted snapshot denominator");
#endif
    require(text(at(bind,"snapshot_adoption_sha256"))==kSnapshotAdoptionSha&&text(at(bind,"snapshot_rebind_version"))==kSnapshotRebindVersion&&text(at(bind,"snapshot_rebind_review"))==kSnapshotRebindReview,"Book context additive snapshot authority changed");
    require(count(at(bind,"snapshot_accepted_children"),7271)==kSnapshotAcceptedChildren&&count(at(bind,"snapshot_pending_children"),7271)==kSnapshotPendingChildren&&count(at(bind,"child_denominator"),7271)==7271,"Book context child snapshot changed");
    require(array(at(map,"reference_catalog")).size()==466&&array(at(map,"book_rows")).size()==105&&array(at(projected,"books")).size()==105&&originals.workbooks().size()==105,"Closed105 book set missing");
    BookContextSourceCatalog candidate;std::set<std::string> ids;
    for(const auto& value:array(at(projected,"public_cards"))){
        checkpoint();
        keys(value,{"card_id","kind","title","summary","levels","paragraphs","authored_public_excerpts","attribution","external_availability","native_presentation_pending","metadata"});
        BookPublicCard card;card.id=text(at(value,"card_id"));require(ids.insert(card.id).second,"Duplicate book context card");card.title=text(at(value,"title"));card.summary=text(at(value,"summary"));card.attribution=text(at(value,"attribution"));
        const auto kind=text(at(value,"kind"));require(kind=="bridge"||kind=="resource","Unknown book context card kind");card.externalResource=kind=="resource";require(text(at(value,"external_availability"))==(card.externalResource?"required_unsupplied":"not_supplied_by_this_context"),"Book context supplied resource refused");require(flag(at(value,"native_presentation_pending")),"Book context cannot claim installed acceptance");
        card.levels=pages(at(value,"levels"),105);
        for(const auto& p:array(at(value,"paragraphs")))card.paragraphs.push_back(text(p));
        for(const auto& p:array(at(value,"authored_public_excerpts"))){keys(p,{"passage_id","text","literal_text_sha256"});const auto t=text(at(p,"text"));require(content::sha256(t)==text(at(p,"literal_text_sha256")),"Book public excerpt changed");card.authoredPublicExcerpts.push_back({text(at(p,"passage_id")),t});}
        const auto& metadata=at(value,"metadata");
        keys(metadata,{"source_order","legacy_level","domains","topic_tags","search_terms","difficulty","context_links","prerequisite_refs","public_source_refs","context_links_are_task_admission"});
        require(!flag(at(metadata,"context_links_are_task_admission")),"Context links cannot admit tasks");
        card.sourceOrder=count(at(metadata,"source_order"),105);require(card.sourceOrder>0,"Public metadata source order missing");
        card.legacyLevel=line(at(metadata,"legacy_level"),105);
        card.domains=strings(at(metadata,"domains"));card.topicTags=strings(at(metadata,"topic_tags"));card.searchTerms=strings(at(metadata,"search_terms"));card.prerequisiteRefs=strings(at(metadata,"prerequisite_refs"));card.publicSourceRefs=strings(at(metadata,"public_source_refs"));
        require(!card.domains.empty()&&!card.searchTerms.empty()&&card.topicTags==card.domains,"Public metadata domain/terms missing");
        for(const auto& domain:card.domains)require(std::set<std::string>{"Technique","Fretboard","Scales","Rhythm","Harmony","Application","Musicianship"}.count(domain)==1,"Unknown approved public domain");
        const auto& difficulty=at(metadata,"difficulty");keys(difficulty,{"value","basis"});card.difficultyValue=text(at(difficulty,"value"));card.difficultyBasis=text(at(difficulty,"basis"));require(card.difficultyValue=="unknown"&&!card.difficultyBasis.empty(),"Unreviewed public difficulty refused");
        for(const auto& link:array(at(metadata,"context_links"))){
            keys(link,{"relation","item_id","workbook_id","module_id","content_revision","title","package_sha256","scope"});
            BookContextLink c;c.relation=text(at(link,"relation"));c.itemId=text(at(link,"item_id"));c.workbookId=text(at(link,"workbook_id"));c.moduleId=text(at(link,"module_id"));c.contentRevision=count(at(link,"content_revision"),100000);c.title=text(at(link,"title"));c.packageSha256=text(at(link,"package_sha256"));c.scope=text(at(link,"scope"));
            require(c.relation=="same_workbook_representative_context_only"&&c.itemId.rfind("fg:item:",0)==0&&c.moduleId.rfind("fg:module:",0)==0&&c.workbookId.rfind("fg:workbook:",0)==0&&c.contentRevision>0&&!c.title.empty()&&c.packageSha256=="0ecd2b1466a7b16e10ca6221299b3b1b21c197ff13cd5df9f038e307673aea8b"&&!c.scope.empty(),"Public context link lost exact historical scope");
            card.contextLinks.push_back(std::move(c));
        }
        candidate.cards_.push_back(std::move(card));
    }
    require(ids==std::set<std::string>{"G01","G02","G03","G04","G05","R39","R48","R73","R74","R75","R76","R77","R78","R79","R95","R96","R97A","R97B","R97C","R99","R105"},"Closed21 card set changed");
    std::size_t sourceUnits=0,accepted=0,pending=0,only=0,qualified=0,limited=0,continuationPages=0;
    const auto& books=array(at(projected,"books"));const auto& mapBooks=array(at(map,"book_rows"));
    for(std::size_t i=0;i<books.size();++i){
        checkpoint();
        const auto& value=books[i];const auto& source=mapBooks[i];const auto& authored=originals.workbooks()[i];
        keys(value,{"workbook_id","level","title","txt","pdf","txt_lines","pdf_pages","source_unit_count","snapshot_accepted_children","snapshot_pending_children","source_only_count","source_tasks","context_locations","composite_continuations","public_card_ids","source17_notices","book_complete","learner_credit","actual_source_supplied"});
        BookPublicContext book;book.level=static_cast<int>(count(at(value,"level"),105));require(book.level==static_cast<int>(i+1)&&book.level==authored.level,"Book context order changed");book.workbookId=text(at(value,"workbook_id"));require(book.workbookId==authored.id&&book.workbookId==text(at(source,"workbook_id")),"Book context identity changed");book.title=text(at(value,"title"));require(!book.title.empty(),"Book context title missing");
        original(map,at(at(source,"originals"),"txt"),at(value,"txt"),authored.txt,authored.txtBytes,authored.txtSha256);original(map,at(at(source,"originals"),"pdf"),at(value,"pdf"),authored.pdf,authored.pdfBytes,authored.pdfSha256);
        book.txtLines=count(at(value,"txt_lines"),100000);book.pdfPages=count(at(value,"pdf_pages"),1000);require(book.txtLines==authored.lines&&book.pdfPages==authored.pages,"Book context full source extent changed");
        book.sourceUnits=count(at(value,"source_unit_count"),10000);book.snapshotAcceptedChildren=count(at(value,"snapshot_accepted_children"),7271);book.snapshotPendingChildren=count(at(value,"snapshot_pending_children"),7271);book.sourceOnlyUnits=count(at(value,"source_only_count"),50);
        require(book.sourceUnits==array(at(source,"tasks")).size()&&book.sourceUnits==book.snapshotAcceptedChildren+book.snapshotPendingChildren+book.sourceOnlyUnits,"Book source unit coverage differs");
        require(!flag(at(value,"book_complete"))&&!flag(at(value,"learner_credit"))&&!flag(at(value,"actual_source_supplied")),"Book context cannot admit or complete work");
        for(const auto& task:array(at(value,"source_tasks"))){
            checkpoint();
            keys(task,{"source_unit_ordinal","source_identity","first_txt_line","last_txt_line","physical_pages","qualification"});
            BookSourceTask t;t.sourceUnitOrdinal=count(at(task,"source_unit_ordinal"),book.sourceUnits);require(t.sourceUnitOrdinal==book.sourceTasks.size()+1,"Closed source task ordering changed");
            t.sourceIdentity_=text(at(task,"source_identity"));require(t.sourceIdentity_==text(at(array(at(source,"tasks"))[t.sourceUnitOrdinal-1],"source_identity")),"Closed source task identity changed");
            t.firstTxtLine=line(at(task,"first_txt_line"),book.txtLines);t.lastTxtLine=line(at(task,"last_txt_line"),book.txtLines);require(t.firstTxtLine.has_value()==t.lastTxtLine.has_value()&&(!t.firstTxtLine||*t.firstTxtLine<=*t.lastTxtLine),"Source task TXT extent invalid");t.physicalPages=pages(at(task,"physical_pages"),static_cast<int>(book.pdfPages));
            const auto q=text(at(task,"qualification"));if(q=="ordinary_task_source")t.qualification=BookSourceTaskQualification::OrdinaryTaskSource;else if(q=="qualified_workflow")t.qualification=BookSourceTaskQualification::QualifiedWorkflow;else if(q=="limited_reference")t.qualification=BookSourceTaskQualification::LimitedReference;else{require(q=="source_only_context","Unknown source task qualification");t.qualification=BookSourceTaskQualification::SourceOnlyContext;}
            book.sourceTasks.push_back(std::move(t));
        }
        require(book.sourceTasks.size()==book.sourceUnits,"Missing closed source task selector row");
        for(const auto& location:array(at(value,"context_locations"))){keys(location,{"kind","first_line","last_line","physical_pages"});BookContextLocation p;p.kind=text(at(location,"kind"));require(std::set<std::string>{"authored_TXT_context","authored_hierarchy_location","authored_PDF_context_page","authored_PDF_outline"}.count(p.kind)==1,"Unknown book context location");p.firstLine=line(at(location,"first_line"),book.txtLines);p.lastLine=line(at(location,"last_line"),book.txtLines);require(p.firstLine.has_value()==p.lastLine.has_value()&&(!p.firstLine||*p.firstLine<=*p.lastLine),"Book context TXT range invalid");p.physicalPages=pages(at(location,"physical_pages"),static_cast<int>(book.pdfPages));book.contextLocations.push_back(std::move(p));}
        for(const auto& continuation:array(at(value,"composite_continuations"))){keys(continuation,{"physical_page","complete_source_unit_count"});const auto p=count(at(continuation,"physical_page"),book.pdfPages);const auto units=count(at(continuation,"complete_source_unit_count"),book.sourceUnits);require(p>0&&units>0,"Incomplete book source continuation");book.compositeContinuations.push_back({static_cast<int>(p),units});++continuationPages;}
        for(const auto& id:array(at(value,"public_card_ids"))){auto name=text(id);require(ids.count(name)==1&&std::find(book.publicCardIds.begin(),book.publicCardIds.end(),name)==book.publicCardIds.end(),"Book context card unavailable/duplicate");auto found=std::find_if(candidate.cards_.begin(),candidate.cards_.end(),[&](const auto& c){return c.id==name;});require(std::find(found->levels.begin(),found->levels.end(),book.level)!=found->levels.end(),"Book card outside original level scope");book.publicCardIds.push_back(name);}
        for(const auto& q:array(at(value,"source17_notices"))){keys(q,{"case_binding_sha256","source_unit_ordinal","physical_pages","qualified_full_workflow","notice","qualification_details"});require(text(at(q,"case_binding_sha256")).size()==64,"Source qualification binding missing");BookSourceQualification n;n.sourceUnitOrdinal=count(at(q,"source_unit_ordinal"),book.sourceUnits);require(n.sourceUnitOrdinal>0,"Source qualification unit missing");n.qualifiedFullWorkflow=flag(at(q,"qualified_full_workflow"));n.physicalPages=pages(at(q,"physical_pages"),static_cast<int>(book.pdfPages));n.notice=text(at(q,"notice"))+" "+text(at(q,"qualification_details"));require(!n.notice.empty(),"Source qualification notice missing");if(n.qualifiedFullWorkflow)++qualified;else ++limited;book.sourceQualifications.push_back(std::move(n));}
        sourceUnits+=book.sourceUnits;accepted+=book.snapshotAcceptedChildren;pending+=book.snapshotPendingChildren;only+=book.sourceOnlyUnits;candidate.books_.push_back(std::move(book));
    }
    require(sourceUnits==7321&&accepted==kSnapshotAcceptedChildren&&pending==kSnapshotPendingChildren&&only==50&&qualified==13&&limited==4&&continuationPages==37,"Book context scope/exception totals changed");
    checkpoint();
    return candidate; // No member is published until every file, original pair and row passed.
}
const BookPublicContext& BookContextSourceCatalog::book(int level) const {require(level>=1&&level<=105,"Unknown existing workbook level");return books_.at(static_cast<std::size_t>(level-1));}
void BookContextSourceCatalog::requireOwned(const BookPublicContext& b) const {require(b.level>=1&&b.level<=static_cast<int>(books_.size())&&&books_[static_cast<std::size_t>(b.level-1)]==&b,"Book public context is not owned by this catalog");}
std::vector<const BookPublicCard*> BookContextSourceCatalog::publicCards(const BookPublicContext& b) const {requireOwned(b);std::vector<const BookPublicCard*> out;for(const auto& id:b.publicCardIds){const auto i=std::find_if(cards_.begin(),cards_.end(),[&](const auto& c){return c.id==id;});require(i!=cards_.end(),"Closed public card missing");out.push_back(&*i);}return out;}
std::string BookContextSourceCatalog::publicInstructions(const BookPublicContext& b) const {
    requireOwned(b);std::ostringstream s;s<<"Level "<<b.level<<" — "<<b.title<<"\n\nOriginal source: "<<b.txtLines<<" TXT lines and "<<b.pdfPages<<" PDF pages. The complete PDF is retained separately from the TXT.\n\n";
    s<<"Context and source structure: "<<b.contextLocations.size()<<" indexed locations; "<<b.compositeContinuations.size()<<" complete task continuation pages. Use the explicit original text/PDF controls for full notation, diagrams and worked examples. Reading preparation can affect a no-chart or unfamiliar listening task.\n\n";
    s<<"This context does not supply an external recording or partner, verify hearing/performance, grant progress credit or complete a workbook. Follow each Learn task's complete instructions and source requirements. Unavailable required work remains incomplete.\n";
    for(const auto& q:b.sourceQualifications){s<<"\nSource qualification";if(!q.physicalPages.empty()){s<<" at original PDF page"<<(q.physicalPages.size()>1?"s ":" ");for(std::size_t i=0;i<q.physicalPages.size();++i){if(i)s<<", ";s<<q.physicalPages[i];}}s<<": "<<q.notice<<"\n";}
    for(const auto* c:publicCards(b)){s<<"\n"<<c->id<<" — "<<c->title<<"\n"<<c->summary<<"\n";s<<"Topics: ";for(std::size_t i=0;i<c->domains.size();++i){if(i)s<<", ";s<<c->domains[i];}s<<". Difficulty: "<<c->difficultyValue<<" ("<<c->difficultyBasis<<").\n";s<<"Prerequisites are advisory; ";if(c->prerequisiteRefs.empty())s<<"none specified in this metadata.\n";else{for(const auto& p:c->prerequisiteRefs)s<<p<<" ";s<<"\n";}for(const auto& link:c->contextLinks)s<<"Related source context: "<<link.title<<" (revision "<<link.contentRevision<<"; contextual reference, not task admission).\n";for(const auto& p:c->paragraphs)s<<"\n"<<p<<"\n";for(const auto& p:c->authoredPublicExcerpts)s<<"\nAuthored source excerpt ("<<p.passageId<<"):\n"<<p.text<<"\n";}
    return s.str();
}
std::vector<const BookPublicCard*> BookContextSourceCatalog::searchCards(const std::string& query,const std::string& domain) const {
    const auto needle=lower(trim(query));const auto wantedDomain=lower(trim(domain));std::vector<const BookPublicCard*> out;
    if(needle.empty()&&wantedDomain.empty())return out;
    for(const auto& card:cards_){
        if(!wantedDomain.empty()&&std::none_of(card.domains.begin(),card.domains.end(),[&](const auto& d){return lower(d)==wantedDomain;}))continue;
        std::string safe=card.id+"\n"+card.title+"\n"+card.summary;
        for(const auto* fields:{&card.domains,&card.topicTags,&card.searchTerms})for(const auto& term:*fields)safe+="\n"+term;
        if(needle.empty()||lower(safe).find(needle)!=std::string::npos)out.push_back(&card);
    }
    return out;
}
std::vector<int> BookContextSourceCatalog::searchBooks(const std::string& query,const std::string& domain) const {
    std::set<int> levels;for(const auto* card:searchCards(query,domain))for(const auto level:card->levels)levels.insert(level);
    return {levels.begin(),levels.end()};
}
std::string BookContextSourceCatalog::sourceIdentity(const BookPublicContext& b,const BookSourceTask& t) const {
    requireOwned(b);require(t.sourceUnitOrdinal>=1&&t.sourceUnitOrdinal<=b.sourceTasks.size()&&&b.sourceTasks[t.sourceUnitOrdinal-1]==&t,"Source task is not owned by this exact catalog book");return t.sourceIdentity_;
}
std::string BookContextSourceCatalog::sourceTaskLabel(const BookPublicContext& b,const BookSourceTask& t) const {
    sourceIdentity(b,t);std::ostringstream s;s<<"Source unit "<<t.sourceUnitOrdinal;
    if(t.firstTxtLine)s<<" · TXT lines "<<*t.firstTxtLine<<"–"<<*t.lastTxtLine;
    if(!t.physicalPages.empty()){s<<" · original PDF page"<<(t.physicalPages.size()>1?"s ":" ");for(std::size_t i=0;i<t.physicalPages.size();++i){if(i)s<<", ";s<<t.physicalPages[i];}}
    if(t.qualification==BookSourceTaskQualification::LimitedReference)s<<" · limited reference";else if(t.qualification==BookSourceTaskQualification::QualifiedWorkflow)s<<" · qualified source workflow";else if(t.qualification==BookSourceTaskQualification::SourceOnlyContext)s<<" · source context";
    return s.str();
}
BookSnapshotCompatibility BookContextSourceCatalog::snapshotCompatibility(const std::string& d,const std::string& i) const noexcept {return d==book105pins::kDescriptorSha&&i==book105pins::kSourceIndexSha?BookSnapshotCompatibility::ExactFrozenBindings:BookSnapshotCompatibility::RequiresReviewedAdditiveRebind;}
const char* BookContextSourceCatalog::snapshotDescriptorSha() noexcept{return book105pins::kDescriptorSha;}
const char* BookContextSourceCatalog::sourceIndexSha() noexcept{return book105pins::kSourceIndexSha;}
} // namespace fathom::curriculum
