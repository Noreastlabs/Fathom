# Exact generated-code include precedence from the adopted target graph.
# Every path points inside this private stage; no active build/evidence workspace is used.
target_include_directories(fathom_compiled_procedure_tasks BEFORE PRIVATE
    "${CMAKE_CURRENT_SOURCE_DIR}/GeneratedSources/graph-final-private-integration-r12/Source17-final4094-r08/generated"
    "${CMAKE_CURRENT_SOURCE_DIR}/GeneratedSources/graph-final-private-integration-r12/Source-r11"
    "${CMAKE_CURRENT_SOURCE_DIR}/GeneratedSources/graph-final-private-integration-r12/final4094-r08/generated"
    "${CMAKE_CURRENT_SOURCE_DIR}/GeneratedSources/graph-final-private-integration-r12/final4094-r08/capacity"
    "${CMAKE_CURRENT_SOURCE_DIR}/GeneratedSources/graph-final-private-integration-r12/generated-r07"
    "${CMAKE_CURRENT_SOURCE_DIR}/GeneratedSources/graph-final-private-integration-r12/support-headers-r11"
    "${CMAKE_CURRENT_SOURCE_DIR}/GeneratedSources/graph-successor-private-integration-r10/generated"
    "${CMAKE_CURRENT_SOURCE_DIR}/GeneratedSources/graph-successor-private-integration-r10/Source"
    "${CMAKE_CURRENT_SOURCE_DIR}/GeneratedSources/graph-successor-private-integration-r10/capacity"
    "${CMAKE_CURRENT_SOURCE_DIR}/GeneratedSources/graph-hidden-seven-carrier-private-r01/generated"
    "${CMAKE_CURRENT_SOURCE_DIR}/GeneratedSources/graph-successor-private-integration-r09/Source-r09"
    "${CMAKE_CURRENT_SOURCE_DIR}/GeneratedSources/graph-successor-private-integration-r09/generated-r09"
    "${CMAKE_CURRENT_SOURCE_DIR}/GeneratedSources/graph-successor-private-integration-r09/capacity-final-r09"
    "${CMAKE_CURRENT_SOURCE_DIR}/GeneratedSources/graph-successor-private-integration-r08/generated-r08"
    "${CMAKE_CURRENT_SOURCE_DIR}/GeneratedSources/graph-successor-private-integration-r07/generated-r07"
    "${CMAKE_CURRENT_SOURCE_DIR}/GeneratedSources/graph-next-private-integration-r01/generated-r06"
    "${CMAKE_CURRENT_SOURCE_DIR}/GeneratedSources/graph2174-private-integration-r01/generated-r01"
    "${CMAKE_CURRENT_SOURCE_DIR}/GeneratedSources/graph1965-private-integration-r01/generated-r01"
    "${CMAKE_CURRENT_SOURCE_DIR}/GeneratedSources/graph1672-private-integration-r01/generated-r01"
    "${CMAKE_CURRENT_SOURCE_DIR}/GeneratedSources"
    "${CMAKE_CURRENT_SOURCE_DIR}/GeneratedSources/level068-generation-r01"
    "${CMAKE_CURRENT_SOURCE_DIR}/GeneratedSources/piecewise-contact-family-r01"
    "${CMAKE_CURRENT_SOURCE_DIR}/GeneratedSources/harmonic-contact-family118-r01"
)
target_include_directories(fathom_source_library BEFORE PRIVATE
    "${CMAKE_CURRENT_SOURCE_DIR}/GeneratedSources"
)
