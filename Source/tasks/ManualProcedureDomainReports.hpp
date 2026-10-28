#pragma once
#include "content/StrictJson.hpp"
namespace fathom::tasks::manual_procedure_graph_support {
// Pure future-owner support. Inputs are trusted cached program/source data;
// returned values are private comparison expectations, never learner defaults.
// Null selection is explicitly unresolved; malformed/foreign selections throw.
struct Projection final {bool resolved{};json::Value values;};
Projection projectClosedDomainReports(const json::Value& operatorDefinition,
                                     const json::Value& ownedSelection,
                                     const json::Value& trustedFiniteDomain);
// A source-action pointer is restricted to exactly original_contract.steps[i].
// The release witness remains separate; this API never performs or reports it.
const json::Value& boundSourceAction(const json::Value& originalContract,
                                   const json::Value& exactSourceActionReference);
// Copy a finite source unit as one ordered physical obligation; never insert
// a release or input boundary between its constituent source actions.
json::Value boundSourceUnit(const json::Value& originalContract,
                           const json::Value& exactGraphNode);
// Python/source string.strip semantics over strict UTF-8 Unicode codepoints.
// Return false for a valid whitespace-only/out-of-bounds manual report; retain
// raw history at the owner. Wrong types/bounds refuse, without normalization.
std::size_t utf8TextLength(const std::string&);
std::string utf8TextSlice(const std::string&,std::size_t start,std::size_t end);
bool nonemptyTrimmedText(const json::Value& rawReport,
                         std::size_t minimum,std::size_t maximum);
} // namespace fathom::tasks::manual_procedure_graph_support
