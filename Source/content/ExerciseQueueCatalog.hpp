#pragma once
#include "ExerciseQueue.hpp"
#include "content/LessonCatalog.hpp"

namespace fathom::navigation {

inline AdmissionIdentity snapshotAdmission(const lesson::Admission& admission) {
    if (!admission.practiceAllowed())
        throw std::invalid_argument("This exact admitted reference cannot enter Practice.");
    const auto& identity = admission.identity().object();
    AdmissionIdentity result{identity.at("item_id").string(), identity.at("variant_id").string(),
                             identity.at("content_version").string(), admission.sourceBinding()};
    if (!result.complete()) throw std::invalid_argument("Incomplete runtime admission identity.");
    return result;
}

// The reviewed installed mapping supplies item/variant, never title matching.
// Preserve the returned immutable object through the existing onPractice seam.
inline std::shared_ptr<const lesson::Admission> resolveExerciseAdmission(
    const lesson::Catalog& catalog, const ExerciseEntry& exercise) {
    if (exercise.mappingExtent != ExerciseMappingExtent::ExactSourceUnit ||
        !exercise.admission || !exercise.admission->complete())
        throw std::invalid_argument("This source exercise has no selected Practice admission.");
    auto admission = catalog.admit(exercise.admission->itemId, exercise.admission->variantId);
    if (!admission || !(snapshotAdmission(*admission) == *exercise.admission))
        throw std::invalid_argument("The selected admission changed; rebuild the source selection.");
    return admission;
}

} // namespace fathom::navigation
