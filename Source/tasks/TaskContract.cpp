#include "TaskContract.hpp"
#include "GeneratedRepresentative.hpp"
#include <utility>

namespace fathom::tasks {
Error::Error(std::string value, const std::string& detail)
    : std::runtime_error(detail), code(std::move(value)) {}

Definition::Definition(std::string key, std::string label, std::string policy,
                       std::string provenance, std::vector<std::string> setup,
                       std::vector<std::string> context, std::string release,
                       std::string explanation, std::vector<Action> actions,
                       Rational end, std::optional<ReportContract> reports)
    : sourceKey_(std::move(key)), label_(std::move(label)), policySha256_(std::move(policy)),
      provenanceJson_(std::move(provenance)), setup_(std::move(setup)), context_(std::move(context)),
      release_(std::move(release)), pacedExplanation_(std::move(explanation)),
      actions_(std::move(actions)), cueEnd_(end), reports_(std::move(reports)) {
    if (sourceKey_.empty() || policySha256_.size() != 64 || setup_.empty() || release_.empty()
        || actions_.empty() || !(Rational{} < cueEnd_))
        throw Error("DEFINITION_INCOMPLETE", "Trusted definition must contain source, policy, instructions and actions");
    for (std::size_t i = 0; i < actions_.size(); ++i) {
        const auto& action = actions_[i];
        if (action.label.empty() || action.contacts.empty() || !(action.authoredCueOnset < cueEnd_)
            || (i == 0 && !(action.authoredCueOnset == Rational{}))
            || (i != 0 && !(actions_[i-1].authoredCueOnset < action.authoredCueOnset)))
            throw Error("DEFINITION_ACTION", "Actions need explicit contacts and increasing authored cue coordinates");
        for (const auto& contact : action.contacts) {
            if (contact.sourceString < 1 || contact.sourceString > 6 || contact.fret < 0
                || contact.writtenStandardTuningMidi < 0 || contact.writtenStandardTuningMidi > 127)
                throw Error("DEFINITION_CONTACT", "Invalid trusted written contact");
        }
    }
    if (reports_) {
        if (!reports_->setup.isObject() || reports_->actions.size() != actions_.size() ||
            !reports_->release.isObject() || reports_->release !=
                json::Value(json::Value::Object{{"released_completely_reported", true}}))
            throw Error("REPORT_CONTRACT", "Trusted reports must match setup, action count and explicit release");
        for (std::size_t i=0; i<reports_->actions.size(); ++i) {
            const auto& report=reports_->actions[i];std::int64_t order{};
            const auto* n=report.find("action_order");const auto* response=report.find("response");
            if (!report.isObject() || !n || !n->integer(order) || order!=static_cast<std::int64_t>(i+1) ||
                !response || !response->isString() || response->string()!="acknowledged")
                throw Error("REPORT_CONTRACT_ACTION", "Trusted reports require exact source action order");
        }
    }
}

const Definition& representativeDefinition(const std::string& key) {
#if defined(FATHOM_CONTENT_FREE_DISTRIBUTION)
    // The unavailable dataset has no trusted task, including its sentinel key.
    // Refuse explicitly before any Definition is constructed or interpreted.
    (void)key;
    throw Error("CONTENT_NOT_INSTALLED", "Optional curriculum content is not installed");
#else
    if (key != generated::sourceKey)
        throw Error("REPRESENTATIVE_SCOPE", "Only the exact reviewed representative is available");
    static const Definition definition{
        generated::sourceKey, generated::label, generated::policySha256,
        generated::provenanceJson, generated::setup(), generated::context(),
        generated::releaseInstruction, generated::pacedExplanation,
        generated::actions(), Rational{4, 1}};
    return definition;
#endif
}

Task::Task(const Definition& definition) : definition_(definition) {}

View Task::view() const noexcept {
    return {mode_, phase_, outcome_, bpm_, action_, phase_ == Phase::Release,
            phase_ == Phase::Choose || phase_ == Phase::Setup};
}

void Task::requireSelectable() const {
    if (phase_ != Phase::Choose && phase_ != Phase::Setup)
        throw Error("SELECTION_STATE", "Choose a mode only before Ready on a fresh pass");
}

void Task::validateTempo(int bpm, TempoRange range) {
    if (range.minimumBpm <= 0 || range.maximumBpm < range.minimumBpm)
        throw Error("HOST_TEMPO_CAPABILITY", "The host must supply a valid current tempo range");
    if (bpm < range.minimumBpm || bpm > range.maximumBpm)
        throw Error("UNSUPPORTED_TEMPO", "Explicit tempo is outside the current host capability");
}

void Task::chooseSourceOrder() {
    requireSelectable();
    mode_ = Mode::SourceOrder;
    phase_ = Phase::Setup;
    bpm_.reset();
}

void Task::chooseEvenPulse(int bpm, TempoRange range) {
    requireSelectable();
    validateTempo(bpm, range); // validate before changing any task state
    mode_ = Mode::FathomEvenPulse;
    bpm_ = bpm;
    phase_ = Phase::Setup;
}

void Task::ready(TempoRange range) {
    if (definition_.reportContract()) throw Error("TYPED_REPORT_REQUIRED", "Report source naming and setup explicitly");
    readyImpl(range);
}
void Task::readyImpl(TempoRange range) {
    if (phase_ != Phase::Setup || mode_ == Mode::Unselected)
        throw Error("READY_STATE", "Explicit mode selection and setup are required before Ready");
    if (mode_ == Mode::FathomEvenPulse) {
        if (!bpm_) throw Error("POLICY_NOT_SELECTED", "An explicit current tempo is required");
        validateTempo(*bpm_, range);
    }
    action_ = 0;
    lastCuePosition_.reset();
    manuallyAcknowledgedAll_ = false;
    outcome_ = Outcome::None;
    pendingOutcome_ = Outcome::None;
    diagnosis_.reset();
    phase_ = mode_ == Mode::SourceOrder ? Phase::ManualSteps : Phase::Cues;
    if (phase_ == Phase::Cues) lastCuePosition_ = Rational{};
}

void Task::enterRelease(Outcome pending) {
    phase_ = Phase::Release;
    action_.reset();
    pendingOutcome_ = pending;
    outcome_ = Outcome::None;
    lastCuePosition_.reset();
}

void Task::respond(Response response) {
    if (definition_.reportContract()) throw Error("TYPED_REPORT_REQUIRED", "Report the exact current written action");
    respondImpl(response);
}
void Task::respondImpl(Response response) {
    if (phase_ != Phase::ManualSteps || !action_)
        throw Error("MANUAL_RESPONSE_STATE", "Responses apply only to the current source-order action");
    switch (response) {
        case Response::NeedsRetry: enterRelease(Outcome::RetryRequested); return;
        case Response::Stopped: enterRelease(Outcome::Cancelled); return;
        case Response::Acknowledged: break;
        default: throw Error("MANUAL_RESPONSE", "Unsupported manual response");
    }
    if (*action_ + 1 == definition_.actions().size()) {
        manuallyAcknowledgedAll_ = true;
        enterRelease(Outcome::UserReportedStepsFinished);
    } else {
        ++*action_;
    }
}

void Task::followCuePosition(QuarterTime position) {
    if (phase_ != Phase::Cues || mode_ != Mode::FathomEvenPulse)
        throw Error("CUE_STATE", "Cue positions require a selected, explicitly started paced guide");
    const Rational q = position.value;
    if (lastCuePosition_ && q < *lastCuePosition_)
        throw Error("CUE_REGRESSION", "A pass cannot move its cue clock backwards");
    if (!(q < definition_.cueEnd())) {
        // Cue time is never evidence that a learner played the actions.
        enterRelease(Outcome::None);
        return;
    }
    std::size_t current = 0;
    for (std::size_t i = 1; i < definition_.actions().size(); ++i) {
        if (q < definition_.actions()[i].authoredCueOnset) break;
        current = i;
    }
    lastCuePosition_ = q;
    action_ = current;
}

void Task::cancel() {
    if (phase_ == Phase::Closed || phase_ == Phase::Release)
        throw Error("CANCEL_STATE", "A closed or release-waiting pass cannot be cancelled again");
    if(definition_.reportContract())diagnosis_=json::Value::Object{{"code","CANCEL"},{"observed_failure",false}};
    enterRelease(Outcome::Cancelled);
}

void Task::requestRetry() {
    if (phase_ != Phase::ManualSteps && phase_ != Phase::Cues)
        throw Error("RETRY_STATE", "Retry applies only to an explicitly started guide");
    if(definition_.reportContract())diagnosis_=json::Value::Object{{"code","MANUAL_NEEDS_RETRY"},{"observed_failure",false}};
    enterRelease(Outcome::RetryRequested);
}

void Task::acknowledgeRelease() {
    if (definition_.reportContract()) throw Error("TYPED_REPORT_REQUIRED", "Explicit reported physical release required");
    releaseImpl();
}
void Task::releaseImpl() {
    if (phase_ != Phase::Release)
        throw Error("RELEASE_STATE", "No release boundary is awaiting acknowledgment");
    if (pendingOutcome_ == Outcome::UserReportedStepsFinished && !manuallyAcknowledgedAll_)
        throw Error("UNSUPPORTED_COMPLETION", "Paced cue completion cannot become reported manual steps");
    phase_ = Phase::Closed;
    outcome_ = pendingOutcome_;
    pendingOutcome_ = Outcome::None;
}

void Task::beginAnotherPass() {
    if (phase_ != Phase::Closed)
        throw Error("REPEAT_STATE", "A new pass requires closing the manual release boundary first");
    mode_ = Mode::Unselected;
    phase_ = Phase::Choose;
    outcome_ = Outcome::None;
    pendingOutcome_ = Outcome::None;
    bpm_.reset();
    action_.reset();
    lastCuePosition_.reset();
    manuallyAcknowledgedAll_ = false;
    diagnosis_.reset();
}

namespace {
// Match the reviewed model's exact top-level field/type contract. Nested value
// differences are retained as learner reports and produce a release/retry.
void reportSchema(const json::Value& actual, const json::Value& expected) {
    if (!actual.isObject() || !expected.isObject() || actual.object().size()!=expected.object().size())
        throw Error("REPORT_FIELDS", "Report the exact source-bound fields");
    for (const auto& field:expected.object()) {
        const auto* value=actual.find(field.first);
        if (!value || value->data.index()!=field.second.data.index())
            throw Error("REPORT_VALUE_TYPE", "Report field type differs");
        std::int64_t ignored{};
        if (field.second.isNumber() && field.second.integer(ignored) && !value->integer(ignored))
            throw Error("REPORT_VALUE_TYPE", "Integer report field required");
    }
}
}
void Task::mismatch(const char* code, const json::Value& expected, const json::Value& reported) {
    diagnosis_=json::Value::Object{{"code",code},{"expected",expected},{"reported",reported},{"observed_failure",false}};
    enterRelease(Outcome::RetryRequested);
}
void Task::readyReported(const json::Value& report, TempoRange range) {
    if (!definition_.reportContract() || phase_!=Phase::Setup)
        throw Error("READY_PHASE", "A source-bound setup report requires the current setup phase");
    if (mode_==Mode::FathomEvenPulse) {
        if (!bpm_) throw Error("POLICY_NOT_SELECTED", "Explicit current tempo required");
        validateTempo(*bpm_,range);
    }
    const auto& expected=definition_.reportContract()->setup;
    reportSchema(report,expected);
    if (report!=expected) { mismatch("SETUP_NAME_OR_MANUAL_REPORT_MISMATCH",expected,report); return; }
    readyImpl(range);
}
void Task::respondReported(const json::Value& report) {
    if (!definition_.reportContract() || phase_!=Phase::ManualSteps || !action_ || !report.isObject())
        throw Error("RESPONSE_PHASE", "Report only the current source-order action");
    const auto* response=report.find("response");
    if (!response || !response->isString()) throw Error("RESPONSE_VALUE", "Explicit manual response required");
    const auto& value=response->string();
    if (value!="acknowledged") {
        if (report.object().size()!=1 || (value!="needs_retry" && value!="stopped" && value!="unknown"))
            throw Error("STOP_RETRY_FIELDS", "Retry, stop or unknown has only its explicit response");
        diagnosis_=json::Value::Object{{"code",value=="stopped"?"MANUAL_STOPPED":value=="unknown"?"MANUAL_UNKNOWN":"MANUAL_NEEDS_RETRY"},{"observed_failure",false}};
        enterRelease(value=="stopped"?Outcome::Cancelled:Outcome::RetryRequested);return;
    }
    const auto& expected=definition_.reportContract()->actions[*action_];
    reportSchema(report,expected);
    if (*report.find("action_order")!=*expected.find("action_order"))
        throw Error("RESPONSE_FIELDS_OR_ORDER", "Only the current source action may be reported");
    if (report!=expected) { mismatch("WRITTEN_CONTACT_DEGREE_OR_MANUAL_REPORT_MISMATCH",expected,report);return; }
    respondImpl(Response::Acknowledged);
}
void Task::acknowledgeReleaseReported(const json::Value& report) {
    if (!definition_.reportContract() || phase_!=Phase::Release || report!=definition_.reportContract()->release)
        throw Error("EXPLICIT_PHYSICAL_RELEASE_REQUIRED", "Explicit reported release must close this boundary");
    releaseImpl();
}

void Task::reopen() {
    if(definition_.reportContract()) {
        if(phase_==Phase::Release)throw Error("RETRY_REOPEN_REQUIRES_RELEASE","Close the explicit release boundary first");
        if(phase_==Phase::Closed){beginAnotherPass();return;}
        diagnosis_=json::Value::Object{{"code","NAVIGATE"},{"observed_failure",false}};
    }
    // Navigation/reopen is an interruption, not a resume token or history load.
    // Require release before any fresh choice; no clock or previous cue restarts.
    mode_ = Mode::Unselected;
    bpm_.reset();
    manuallyAcknowledgedAll_ = false;
    enterRelease(definition_.reportContract()?Outcome::Cancelled:Outcome::Interrupted);
}
} // namespace fathom::tasks
