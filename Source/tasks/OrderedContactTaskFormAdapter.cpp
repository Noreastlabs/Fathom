#include "tasks/OrderedContactTaskFormAdapter.hpp"
#include "content/Canonical.hpp"
#include <chrono>
#include <type_traits>
#include <algorithm>
#include <atomic>
#include <limits>
#include <map>

namespace fathom::tasks::ordered_contacts::manual {
namespace {
using J = json::Value;
void need(bool condition, const char* learnerMessage) {
    if (!condition) throw std::invalid_argument(learnerMessage);
}
const J& at(const J& v, const std::string& key) {
    need(v.isObject() && v.find(key), "A required report field is missing."); return *v.find(key);
}
const std::map<FieldId, std::string> names{
    {FieldId::Branch,"branch"},{FieldId::Rhythm,"rhythm"},{FieldId::FirstStart,"first_start"},
    {FieldId::SetupRead,"setup_read"},{FieldId::OneSet,"one_set"},{FieldId::PrintedMode,"printed_mode"},
    {FieldId::StableLandings,"stable_landings"},{FieldId::ChosenBpm,"chosen_bpm"},
    {FieldId::PreviousCleanBpm,"previous_clean_bpm"},{FieldId::OtherModeCleanBpm,"other_mode_clean_bpm"},
    {FieldId::ContactReported,"contact_reported"},{FieldId::PressureReleased,"pressure_released"},
    {FieldId::FrameRelocated,"frame_relocated"},{FieldId::PauseReported,"pause_reported"},
    {FieldId::HandReleaseReported,"hand_release_reported"},{FieldId::Observation,"observation"},
    {FieldId::NextPass,"next_pass"},{FieldId::PriorPrintedPasses,"prior_printed_passes"},
    {FieldId::FullSetClean,"full_set_clean"},{FieldId::BothRoutesClean,"both_routes_clean"},
    {FieldId::BothStartsClean,"both_starts_clean"},{FieldId::BothModesClean,"both_modes_clean"},
    {FieldId::SeparateDays,"separate_days"},{FieldId::NextSessionRhythm,"next_session_rhythm"},
    {FieldId::TempoDrop,"tempo_drop"},{FieldId::AppliedReduction,"applied_reduction"},
    {FieldId::PlannedIncrease,"planned_increase"},{FieldId::ExtensionChoice,"extension"},
    {FieldId::MasteryReported,"mastery_reported"},{FieldId::PositionOne,"position_one"},
    {FieldId::PositionTwo,"position_two"},{FieldId::PositionThree,"position_three"},
    {FieldId::SourceDutyChoice,"source_duty"},{FieldId::SourcePracticeReported,"source_practice_reported"},
    {FieldId::SourceReleaseReported,"source_release_reported"}};
J value(const ChoiceValue& v) {
    return std::visit([](const auto& typed) { return J::fromInteger(static_cast<std::int64_t>(typed)); }, v);
}
std::int64_t integer(const J& v) {
    std::int64_t n = 0; need(v.integer(n), "Use an exact integer for this report field."); return n;
}
void validate(const J& schema, const J& payload) {
    need(payload.isObject(), "Report fields must be an object.");
    const auto& properties = at(schema,"properties");
    for (const auto& key : at(schema,"required").array()) (void)at(payload,key.string());
    for (const auto& item : payload.object()) {
        need(properties.find(item.first), "This report contains an unsupported field.");
        const auto& field = *properties.find(item.first);
        const auto& type = at(field,"type").string();
        if (type == "integer") {
            const auto n = integer(item.second);
            if (const auto* minimum = field.find("minimum")) need(n >= integer(*minimum), "The reported integer is below its allowed range.");
            if (const auto* maximum = field.find("maximum")) need(n <= integer(*maximum), "The reported integer is above its allowed range.");
            if (const auto* choices = field.find("enum"))
                need(std::find(choices->array().begin(), choices->array().end(), item.second) != choices->array().end(), "Choose one of the displayed report options.");
            if (const auto* fixed = field.find("const")) need(item.second == *fixed, "Keep the extension choice you explicitly selected.");
        } else if (type == "array") {
            need(item.second.isArray() && item.second.array().size() <= 2, "Report at most two distinct source practice days.");
            for (const auto& day : item.second.array()) need(day.isString() && day.string().size() == 10, "Use YYYY-MM-DD for each reported practice day.");
        } else throw std::invalid_argument("This report field type is unsupported.");
    }
}
int input(const J& payload, FieldId field) { return static_cast<int>(integer(at(payload,names.at(field)))); }
std::optional<int> optionalInput(const J& payload, FieldId field) {
    const auto* found = payload.find(names.at(field)); return found ? std::optional<int>(static_cast<int>(integer(*found))) : std::nullopt;
}
Claim claimInput(const J& payload, FieldId field) {
    const auto* found = payload.find(names.at(field)); return found ? static_cast<Claim>(integer(*found)) : Claim::Unknown;
}
std::atomic<std::uint64_t> owners{1};
}
OrderedContactTaskFormAdapter::OrderedContactTaskFormAdapter(Task& task) : task_(task), owner_(owners.fetch_add(1)) {
    trackable_=task_.history().empty()&&task_.view().revision==0;
    need(owner_ != 0 && owner_ != std::numeric_limits<std::uint64_t>::max(), "Report form ownership is unavailable.");
}
void OrderedContactTaskFormAdapter::invalidate() noexcept { nativeToken_.reset(); }
bool OrderedContactTaskFormAdapter::current(const FormToken& token) const noexcept {
    return nativeToken_ && token.owner_ == owner_ && token.generation_ == generation_ && task_.view().revision == openedRevision_;
}
void OrderedContactTaskFormAdapter::fence(const FormToken& token) const {
    need(current(token), "This form is no longer current. Open the action again.");
}
OpenForm OrderedContactTaskFormAdapter::open(Action action) {
    const auto descriptions = task_.actionDescriptors();
    const auto found = std::find_if(descriptions.begin(), descriptions.end(), [action](const auto& d) { return d.action == action; });
    need(found != descriptions.end(), "This action is not available at the current source step.");
    descriptor_ = *found; nativeToken_.emplace(task_.capture(action));
    openedRevision_ = task_.view().revision; openedOrdinal_ = task_.view().nextOrdinal; selectedExtension_.reset();
    return rebuild();
}
OpenForm OrderedContactTaskFormAdapter::rebuild() {
    need(generation_ != std::numeric_limits<std::uint64_t>::max(), "Report form generation is unavailable.");
    ++generation_;
    if (descriptor_.typedReportSchema) {
        schema_ = *descriptor_.typedReportSchema;
        return {FormToken(owner_,generation_),schema_,descriptor_.label,descriptor_.instructions,descriptor_.contact};
    }
    J::Object properties; J::Array required;
    for (const auto& field : descriptor_.fields) {
        if (field.onlyForExtension && field.onlyForExtension != selectedExtension_) continue;
        J::Object data{{"label", field.label}};
        if (field.kind == FieldKind::Choice) {
            J::Array values, labels;
            for (const auto& choice : field.choices) { values.push_back(value(choice.value)); labels.emplace_back(choice.label); }
            data.emplace("type","integer"); data.emplace("enum",std::move(values)); data.emplace("enumLabels",std::move(labels));
            if (field.id == FieldId::ExtensionChoice && selectedExtension_) {
                const auto chosen = J::fromInteger(static_cast<int>(*selectedExtension_));
                data.emplace("const",chosen);
                data["label"] = J("Extension you explicitly selected");
                data.emplace("literal_binding_label","prior_learner_choice_binding");
                data.emplace("input_role","prior_learner_choice_binding");
            }
        } else if (field.kind == FieldKind::PositiveInteger) {
            data.emplace("type","integer"); data.emplace("minimum",J::fromInteger(field.minimum.value_or(1)));
            data.emplace("maximum",J::fromInteger(field.maximum.value_or(std::numeric_limits<int>::max())));
        } else {
            data.emplace("type","array"); data.emplace("minItems",J::fromInteger(0)); data.emplace("maxItems",J::fromInteger(2));
            data.emplace("items",J::Object{{"type","string"},{"minLength",J::fromInteger(10)},{"maxLength",J::fromInteger(10)}});
        }
        properties.emplace(names.at(field.id),std::move(data));
        if (field.required) required.emplace_back(names.at(field.id));
    }
    schema_ = J::Object{{"type","object"},{"properties",std::move(properties)},
        {"required",std::move(required)},{"additionalProperties",false}};
    return {FormToken(owner_,generation_),schema_,descriptor_.label,descriptor_.instructions,descriptor_.contact};
}
OpenForm OrderedContactTaskFormAdapter::selectExtension(const FormToken& token, Extension choice) {
    fence(token); need(descriptor_.action == Action::ExtensionReport, "Open the source extension action first.");
    const auto field = std::find_if(descriptor_.fields.begin(),descriptor_.fields.end(),[](const auto& f) { return f.id == FieldId::ExtensionChoice; });
    const auto requested = J::fromInteger(static_cast<int>(choice));
    need(field != descriptor_.fields.end() && std::any_of(field->choices.begin(),field->choices.end(),[&](const auto& c) { return value(c.value) == requested; }),
         "Choose an extension printed for this source exercise.");
    selectedExtension_ = choice; return rebuild();
}
void OrderedContactTaskFormAdapter::apply(const FormToken& token, const J& payload) {
    fence(token);
    if (descriptor_.typedReportSchema) {
        need(payload.isObject(),"Report fields must be an object.");
        const auto& properties=at(schema_,"properties");
        for(const auto& key:at(schema_,"required").array()) (void)at(payload,key.string());
        for(const auto& item:payload.object()) need(properties.find(item.first),"This report contains an unsupported field.");
    } else validate(schema_,payload);
    J command=J::Object{{"kind","apply"},{"action",J::fromInteger(static_cast<int>(descriptor_.action))},{"input",payload},{"extension",selectedExtension_?J::fromInteger(static_cast<int>(*selectedExtension_)):J{}}};
    prepareJournalSlot();
    const auto native = *nativeToken_;
    try {
        switch (descriptor_.action) {
        case Action::Begin: {
            SetupReport r{static_cast<Branch>(input(payload,FieldId::Branch)), static_cast<Rhythm>(input(payload,FieldId::Rhythm)),
                static_cast<Start>(input(payload,FieldId::FirstStart))};
            r.sourceSetupRead = claimInput(payload,FieldId::SetupRead); r.onePrintedSetChosen = claimInput(payload,FieldId::OneSet);
            r.printedModeChosen = claimInput(payload,FieldId::PrintedMode); r.stableLandings = claimInput(payload,FieldId::StableLandings);
            r.chosenBpm = optionalInput(payload,FieldId::ChosenBpm); r.previousCleanBpm = optionalInput(payload,FieldId::PreviousCleanBpm);
            r.otherPreviousModeCleanBpm = optionalInput(payload,FieldId::OtherModeCleanBpm); task_.begin(native,r); break;
        }
        case Action::Contact: task_.confirmContact(native,openedOrdinal_,claimInput(payload,FieldId::ContactReported)); break;
        case Action::BoundaryReport: task_.reportBoundary(native,{claimInput(payload,FieldId::PressureReleased),
            claimInput(payload,FieldId::FrameRelocated),claimInput(payload,FieldId::PauseReported)}); break;
        case Action::Release: task_.release(native,claimInput(payload,FieldId::HandReleaseReported)); break;
        case Action::LoopReport: task_.reportLoop(native,{static_cast<Observation>(input(payload,FieldId::Observation)),claimInput(payload,FieldId::StableLandings)}); break;
        case Action::SourceIssueReport:
            if(descriptor_.typedReportSchema) {
                need(at(payload,"repair_id").isString(),"Choose one of the printed source diagnoses.");
                task_.reportHarmonicSourceIssue(native,at(payload,"repair_id").string(),at(payload,"evidence"));
            } else task_.reportSourceIssue(native,static_cast<Observation>(input(payload,FieldId::Observation)));
            break;
        case Action::SourcePhaseReport: task_.reportSourcePhase(native,payload);break;
        case Action::SourceRepairReport: task_.reportSourceRepair(native,payload);break;
        case Action::OppositeStart: task_.oppositeStart(native); break;
        case Action::Repeat: task_.repeat(native); break;
        case Action::Retry: task_.retry(native); break;
        case Action::AdvancePass:
            if(descriptor_.typedReportSchema){source_contacts::validateReport(schema_,payload);task_.advanceSourceRoute(native,static_cast<std::size_t>(integer(at(payload,"source_route"))),static_cast<Start>(integer(at(payload,"first_start"))));}
            else task_.advancePass(native,static_cast<Pass>(input(payload,FieldId::NextPass)),static_cast<Rhythm>(input(payload,FieldId::Rhythm)));break;
        case Action::Finish: task_.finish(native); break;
        case Action::Cancel: task_.cancel(native); break;
        case Action::Restart: task_.restart(native); break;
        case Action::SessionReport: {
            SessionReport r;
            r.priorPrintedPassesReported = claimInput(payload,FieldId::PriorPrintedPasses); r.fullPrintedSetClean = claimInput(payload,FieldId::FullSetClean);
            r.bothRoutesClean = claimInput(payload,FieldId::BothRoutesClean); r.bothStartsClean = claimInput(payload,FieldId::BothStartsClean);
            r.bothModesClean = claimInput(payload,FieldId::BothModesClean);
            if (const auto* days = payload.find(names.at(FieldId::SeparateDays))) for (const auto& day : days->array()) r.separateDayLabels.push_back(day.string());
            if (const auto chosen = optionalInput(payload,FieldId::NextSessionRhythm)) r.nextSessionRhythm = static_cast<Rhythm>(*chosen);
            task_.reportSession(native,r); break;
        }
        case Action::ReduceTempo: task_.reduceTempo(native,input(payload,FieldId::TempoDrop),claimInput(payload,FieldId::AppliedReduction)); break;
        case Action::PlanIncrease: task_.planIncreaseNextSession(native,claimInput(payload,FieldId::PlannedIncrease)); break;
        case Action::SourcePracticeReport:
            task_.reportSourcePractice(native,static_cast<SourceDuty>(input(payload,FieldId::SourceDutyChoice)),claimInput(payload,FieldId::SourcePracticeReported),
                {claimInput(payload,FieldId::SourceReleaseReported),claimInput(payload,FieldId::FrameRelocated),claimInput(payload,FieldId::PauseReported)});break;
        case Action::ExtensionReport: {
            const auto choice = static_cast<Extension>(input(payload,FieldId::ExtensionChoice));
            if (choice == Extension::OtherPositionDistance) {
                need(selectedExtension_ == choice, "Explicitly choose the custom-distance extension before reporting its frames.");
                task_.reportDistanceExtension(native,{input(payload,FieldId::PositionOne),input(payload,FieldId::PositionTwo),input(payload,FieldId::PositionThree)},
                    claimInput(payload,FieldId::MasteryReported));
            } else task_.reportExtension(native,choice,claimInput(payload,FieldId::MasteryReported));
            break;
        }
        }
    } catch (const Refusal&) {
        throw std::invalid_argument("The report did not satisfy this source action. Review its displayed instructions and required choices.");
    }
    journal_.push_back(std::move(command));
    invalidate();
}
void OrderedContactTaskFormAdapter::prepareJournalSlot(){
    static_assert(std::is_nothrow_move_constructible<J>::value,"Post-commit journal append must not allocate");
    if(journal_.size()==journal_.capacity()){need(journal_.size()<journal_.max_size(),"Private command journal capacity unavailable");const auto next=journal_.capacity()?journal_.capacity()+journal_.capacity()/2+1:16;journal_.reserve(std::max(next,journal_.size()+1));}
}
void OrderedContactTaskFormAdapter::cancelForNavigation(){
    J command=J::Object{{"kind","cancel"}};prepareJournalSlot();task_.cancel(task_.capture(Action::Cancel));journal_.push_back(std::move(command));invalidate();
}
void OrderedContactTaskFormAdapter::deactivateForNavigation(){
    J command=J::Object{{"kind","inactive_fence"}};prepareJournalSlot();task_.deactivateForNavigation();journal_.push_back(std::move(command));invalidate();
}
std::string OrderedContactTaskFormAdapter::continuation()const{
    need(trackable_,"This owner predates command tracking; original work remains intact");need(journal_.size()<=100000,"Private save journal exceeds capacity; original work remains intact");
    const bool opened=nativeToken_&&task_.view().revision==openedRevision_;
    const J body=J::Object{{"format","fathom-contact-adapter-continuation-v1"},{"binding",J::Object{{"source_key",task_.sourceKey()},{"source_identity",task_.sourceHandle().sourceIdentity()},{"source_record_sha256",task_.sourceHandle().sourceRecordSha256()},{"contract_sha256",task_.continuationSourceSha256()}}},{"journal",J::Array(journal_.begin(),journal_.end())},{"native_state_sha256",task_.continuationStateSha256()},{"open_action",opened?J::fromInteger(static_cast<int>(descriptor_.action)):J{}},{"selected_extension",opened&&selectedExtension_?J::fromInteger(static_cast<int>(*selectedExtension_)):J{}},{"form_schema_sha256",opened?J(content::sha256(json::stringify(schema_))):J("")}};
    const auto bytes=json::stringify(J::Object{{"body",body},{"sha256",content::sha256(json::stringify(body))}});json::Limits limits;limits.bytes=64*1024*1024;limits.stringBytes=4*1024*1024;limits.depth=96;limits.values=2000000;json::parse(bytes,limits);
    // Verify all native state through legal replay. No raw state assignment,
    // untracked direct mutation, or inferred completed work can become Saved.
    auto verified=restoreContinuation(task_.sourceHandle(),bytes);need(verified.task->continuationStateSha256()==task_.continuationStateSha256(),"Private continuation replay differs from current original owner");return bytes;
}
RestoredContactOwner OrderedContactTaskFormAdapter::restoreContinuation(const manual_contacts::SourceHandle& source,const std::string& bytes){
    json::Limits limits;limits.bytes=64*1024*1024;limits.stringBytes=4*1024*1024;limits.depth=96;limits.values=2000000;const auto envelope=json::parse(bytes,limits);
    need(envelope.isObject()&&envelope.object().size()==2&&envelope.find("body")&&envelope.find("sha256"),"Private contact continuation envelope");const auto& body=at(envelope,"body");need(at(envelope,"sha256").isString()&&at(envelope,"sha256").string()==content::sha256(json::stringify(body)),"Private contact continuation checksum differs");
    need(body.isObject()&&body.object().size()==7&&at(body,"format")==J("fathom-contact-adapter-continuation-v1"),"Unsupported private contact continuation");const auto& binding=at(body,"binding");
    RestoredContactOwner result;result.task=std::make_unique<Task>(source);result.adapter=std::make_unique<OrderedContactTaskFormAdapter>(*result.task);
    need(binding.isObject()&&binding.object().size()==4&&at(binding,"source_key")==J(source.sourceKey())&&at(binding,"source_identity")==J(source.sourceIdentity())&&at(binding,"source_record_sha256")==J(source.sourceRecordSha256())&&at(binding,"contract_sha256")==J(result.task->continuationSourceSha256()),"Original contact source binding differs; no migration performed");
    const auto& journal=at(body,"journal").array();need(journal.size()<=100000,"Private contact replay capacity");const auto started=std::chrono::steady_clock::now();
    for(const auto& command:journal){need(std::chrono::steady_clock::now()-started<std::chrono::seconds(10),"Private contact replay budget exceeded; original bytes preserved");need(command.isObject(),"Private contact command shape");const auto kind=at(command,"kind").string();
        if(kind=="apply"){
            need(command.object().size()==4,"Private contact apply shape");const auto action=integer(at(command,"action"));need(action>=0&&action<=static_cast<int>(Action::SourceRepairReport),"Private contact action range");auto form=result.adapter->open(static_cast<Action>(action));const auto& extension=at(command,"extension");if(!extension.null()){const auto n=integer(extension);need(n>=0&&n<=static_cast<int>(Extension::OtherPositionDistance),"Private contact extension range");form=result.adapter->selectExtension(form.token,static_cast<Extension>(n));}result.adapter->apply(form.token,at(command,"input"));
        }else if(kind=="cancel"){need(command.object().size()==1,"Private cancellation shape");result.adapter->cancelForNavigation();}
        else if(kind=="inactive_fence"){need(command.object().size()==1,"Private navigation fence shape");result.adapter->deactivateForNavigation();}
        else need(false,"Unknown private contact command");
    }
    need(result.adapter->journal_==journal&&at(body,"native_state_sha256")==J(result.task->continuationStateSha256()),"Private native contact history/state differs after replay");
    const auto& selected=at(body,"open_action");const auto& extension=at(body,"selected_extension");const auto& schemaHash=at(body,"form_schema_sha256");
    if(!selected.null()){const auto action=integer(selected);need(action>=0&&action<=static_cast<int>(Action::SourceRepairReport),"Saved contact form action range");auto form=result.adapter->open(static_cast<Action>(action));if(!extension.null()){const auto n=integer(extension);need(n>=0&&n<=static_cast<int>(Extension::OtherPositionDistance),"Saved contact extension range");form=result.adapter->selectExtension(form.token,static_cast<Extension>(n));}need(schemaHash==J(content::sha256(json::stringify(form.schema))),"Saved contact form schema differs");}
    else need(extension.null()&&schemaHash==J(""),"Inactive saved contact form differs");
    return result;
}
} // namespace fathom::tasks::ordered_contacts::manual
