#pragma once
#include "tasks/ManualProcedureDomainReports.hpp"

namespace fathom::tasks::manual_procedure_graph_support {
// Closed future comparison helpers. Results are trusted private expectations;
// callers still own tokens, explicit reporting, diagnosis and release history.
Projection projectSourceOrderedPDirections(const json::Value& closedOperator,
                                           const json::Value& reportedDirections);
// Strict finite nonnegative JSON numbers, mathematical decimal comparison.
// Null is unresolved. No binary rounding, measured duration or source clock.
bool reportedSecondsAtLeast(const json::Value& reported,
                            const json::Value& sourceOrPriorReportedLowerBound);
bool trimmedTextExact(const json::Value& reported);
// Bind only original_contract.steps[index] or the five retained seventh actions.
// This reference does not perform the source action or discharge native debt.
const json::Value& boundProtocolSourceAction(const json::Value& originalContract,
                                            const json::Value& exactReference);
json::Value boundTableSourceRecords(const json::Value& originalRecord,
                                    const json::Value& exactGraphNode);
json::Value boundAssessmentSourceInstructions(const json::Value& originalContract,
                                              const json::Value& exactGraphNode);
} // namespace fathom::tasks::manual_procedure_graph_support
