# Full private production graph; runtime packages are normalized local inputs.
# No active planning/QA/build evidence workspace is consulted.
set(FATHOM_JUCE "${CMAKE_CURRENT_SOURCE_DIR}/Dependencies/JUCE-e18f7f506c0b96f2c738a0bcd7fe6467a5005ad8")

if(NOT EXISTS "${FATHOM_JUCE}/CMakeLists.txt")

    message(FATAL_ERROR "Pinned local JUCE source is missing; see docs/development.md. No automatic download.")

endif()

add_subdirectory("${FATHOM_JUCE}" "${CMAKE_BINARY_DIR}/juce-build")

add_library(fathom_output STATIC Source/platform/AudioOutputMac.mm)

target_include_directories(fathom_output PUBLIC Source PRIVATE Source/platform)

set_source_files_properties(Source/platform/AudioOutputMac.mm PROPERTIES COMPILE_FLAGS "-fobjc-arc")

target_compile_definitions(fathom_output PUBLIC JUCE_WEB_BROWSER=0 JUCE_USE_CURL=0 JUCE_MODAL_LOOPS_PERMITTED=0)

target_link_libraries(fathom_output PUBLIC fathom_core juce::juce_audio_devices juce::juce_gui_basics "-framework AppKit")

juce_add_gui_app(Fathom PRODUCT_NAME "Fathom" COMPANY_NAME "Fathom" BUNDLE_ID "local.fathom.guitar")

option(FATHOM_ONBOARDING_RECEIVER_TRACE "Private non-consuming setup receiver diagnostic" OFF)

if(FATHOM_ONBOARDING_RECEIVER_TRACE)

    set_source_files_properties(Source/desktop/OnboardingView.cpp PROPERTIES COMPILE_DEFINITIONS FATHOM_ONBOARDING_RECEIVER_TRACE=1)

endif()

target_sources(Fathom PRIVATE Source/desktop/Main.cpp Source/desktop/GuitarSetupView.cpp Source/desktop/AudioOutputView.cpp Source/desktop/SchedulerView.cpp Source/desktop/ReferenceView.cpp)

target_compile_definitions(Fathom PRIVATE JUCE_WEB_BROWSER=0 JUCE_USE_CURL=0 JUCE_MODAL_LOOPS_PERMITTED=0)

target_include_directories(Fathom PRIVATE Source/platform)

target_link_libraries(Fathom PRIVATE fathom_reference_playback fathom_output fathom_core juce::juce_gui_basics juce::juce_recommended_config_flags juce::juce_recommended_warning_flags)

include("${CMAKE_CURRENT_SOURCE_DIR}/cmake/CleanRuntimePin.cmake")
add_library(fathom_content STATIC Source/content/CleanRuntimeEnvelope.cpp Source/content/StrictJson.cpp Source/content/Canonical.cpp Source/content/SourceRealization.cpp)

target_include_directories(fathom_content PUBLIC Source)
target_compile_definitions(fathom_content PRIVATE FATHOM_CLEAN_RUNTIME_MANIFEST_SHA="${FATHOM_CLEAN_RUNTIME_MANIFEST_SHA}")

target_link_libraries(fathom_content PUBLIC fathom_core PRIVATE juce::juce_cryptography)

target_compile_definitions(fathom_content PRIVATE JUCE_WEB_BROWSER=0 JUCE_USE_CURL=0)

target_compile_options(fathom_content PRIVATE -Wall -Wextra -Wpedantic -Werror)

set(FATHOM_CONTENT_IDENTITIES "")

foreach(FATHOM_CONTENT_FILE Source/content/CleanRuntimeEnvelope.hpp Source/content/CleanRuntimeEnvelope.cpp cmake/CleanRuntimePin.cmake Source/content/StrictJson.hpp Source/content/StrictJson.cpp Source/content/Canonical.hpp Source/content/Canonical.cpp Source/core/MusicModel.hpp Source/core/MusicModel.cpp Source/core/Quantity.hpp Source/core/Quantity.cpp Dependencies/lock.json)

    set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/${FATHOM_CONTENT_FILE}")

    file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/${FATHOM_CONTENT_FILE}" FATHOM_CONTENT_HASH)

    string(APPEND FATHOM_CONTENT_IDENTITIES "${FATHOM_CONTENT_FILE}:${FATHOM_CONTENT_HASH}\n")

endforeach()

string(SHA256 FATHOM_CONTENT_SOURCE_ID "${FATHOM_CONTENT_IDENTITIES}")

target_compile_definitions(fathom_content PRIVATE FATHOM_CONTENT_SOURCE_ID="${FATHOM_CONTENT_SOURCE_ID}")

add_executable(fathom_content_validate Tools/content_validate.cpp)

target_link_libraries(fathom_content_validate PRIVATE fathom_content)

target_compile_options(fathom_content_validate PRIVATE -Wall -Wextra -Wpedantic -Werror)

add_executable(fathom_level001_validate Tools/level001_validate.cpp)

target_link_libraries(fathom_level001_validate PRIVATE fathom_content)

target_compile_options(fathom_level001_validate PRIVATE -Wall -Wextra -Wpedantic -Werror)

add_library(fathom_sqlite STATIC Dependencies/SQLite-3.53.4/sqlite3.c)

target_include_directories(fathom_sqlite PUBLIC Dependencies/SQLite-3.53.4)

target_compile_definitions(fathom_sqlite PRIVATE SQLITE_THREADSAFE=1 SQLITE_OMIT_LOAD_EXTENSION SQLITE_DQS=0 SQLITE_DEFAULT_FOREIGN_KEYS=1)

file(READ "${CMAKE_CURRENT_SOURCE_DIR}/Source/storage/ProfileSchema.sql" FATHOM_PROFILE_SCHEMA)

set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/Source/storage/ProfileSchema.sql")

configure_file("${CMAKE_CURRENT_SOURCE_DIR}/Source/storage/ProfileSchema.generated.hpp.in"
    "${CMAKE_CURRENT_BINARY_DIR}/ProfileSchema.generated.hpp" @ONLY)

find_package(Threads REQUIRED)

add_library(fathom_storage STATIC Source/storage/StorageEnvelope.cpp Source/storage/ArchiveManifest.cpp Source/storage/StoredZip64.cpp Source/storage/ArchiveReader.cpp Source/storage/BackupPublication.cpp Source/storage/RestorePreparation.cpp Source/storage/RestoreApply.cpp Source/storage/ProfileStore.cpp Source/platform/ProfileAccessMac.mm)

target_include_directories(fathom_storage PUBLIC Source PRIVATE "${CMAKE_CURRENT_BINARY_DIR}" "${FATHOM_JUCE}/modules")

set_source_files_properties(Source/platform/ProfileAccessMac.mm PROPERTIES COMPILE_FLAGS "-fobjc-arc")

target_link_libraries(fathom_storage PUBLIC fathom_content PRIVATE fathom_sqlite Threads::Threads "-framework Foundation")

target_compile_options(fathom_storage PRIVATE -Wall -Wextra -Wpedantic -Werror)

add_library(fathom_portable_restore_workflow STATIC Source/desktop/PortableRestoreWorkflow.cpp)

target_include_directories(fathom_portable_restore_workflow PUBLIC Source)

target_link_libraries(fathom_portable_restore_workflow PUBLIC fathom_storage)

target_compile_options(fathom_portable_restore_workflow PRIVATE -Wall -Wextra -Wpedantic -Werror)

target_link_libraries(Fathom PRIVATE fathom_portable_restore_workflow)

add_library(fathom_recovery STATIC Source/storage/Recovery.cpp Source/storage/CheckpointCoordinator.cpp)

target_include_directories(fathom_recovery PUBLIC Source)

target_link_libraries(fathom_recovery PUBLIC fathom_storage)

target_compile_options(fathom_recovery PRIVATE -Wall -Wextra -Wpedantic -Werror)

file(READ "${CMAKE_CURRENT_SOURCE_DIR}/Source/progression/InitialRules.json" FATHOM_PROGRESSION_RULES)

file(READ "${CMAKE_CURRENT_SOURCE_DIR}/Source/progression/SourceRubrics.json" FATHOM_PROGRESSION_SOURCE)

set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS
    "${CMAKE_CURRENT_SOURCE_DIR}/Source/progression/InitialRules.json"
    "${CMAKE_CURRENT_SOURCE_DIR}/Source/progression/SourceRubrics.json")

configure_file("${CMAKE_CURRENT_SOURCE_DIR}/Source/progression/ProgressionRules.generated.hpp.in"
    "${CMAKE_CURRENT_BINARY_DIR}/ProgressionRules.generated.hpp" @ONLY)

add_library(fathom_progression STATIC Source/progression/Progression.cpp Source/progression/ProgressionAdapter.cpp Source/progression/ProgressionRepository.cpp)

target_include_directories(fathom_progression PUBLIC Source PRIVATE "${CMAKE_CURRENT_BINARY_DIR}")

target_link_libraries(fathom_progression PUBLIC fathom_storage)

target_compile_options(fathom_progression PRIVATE -Wall -Wextra -Wpedantic -Werror)

add_executable(fathom_progression_project Tools/progression_project.cpp)

target_link_libraries(fathom_progression_project PRIVATE fathom_progression)

target_compile_options(fathom_progression_project PRIVATE -Wall -Wextra -Wpedantic -Werror)

add_library(fathom_recommendations STATIC Source/progression/Recommendations.cpp)

target_include_directories(fathom_recommendations PUBLIC Source)

target_link_libraries(fathom_recommendations PUBLIC fathom_progression)

target_compile_options(fathom_recommendations PRIVATE -Wall -Wextra -Wpedantic -Werror)

add_library(fathom_compatibility STATIC Source/storage/ProfileCompatibility.cpp)

target_include_directories(fathom_compatibility PUBLIC Source)

target_link_libraries(fathom_compatibility PUBLIC fathom_storage PRIVATE fathom_sqlite)

target_compile_options(fathom_compatibility PRIVATE -Wall -Wextra -Wpedantic -Werror)

add_executable(fathom_profile_compatibility Tools/profile_compatibility.cpp)

target_link_libraries(fathom_profile_compatibility PRIVATE fathom_compatibility)

target_compile_definitions(fathom_profile_compatibility PRIVATE FATHOM_COMPATIBILITY_VERSION="${PROJECT_VERSION}")

target_compile_options(fathom_profile_compatibility PRIVATE -Wall -Wextra -Wpedantic -Werror)

add_library(fathom_history_export STATIC Source/storage/HistoryCsv.cpp)

target_include_directories(fathom_history_export PUBLIC Source)

target_link_libraries(fathom_history_export PUBLIC fathom_storage)

target_compile_options(fathom_history_export PRIVATE -Wall -Wextra -Wpedantic -Werror)

add_executable(fathom_history_csv Tools/history_csv.cpp)

target_link_libraries(fathom_history_csv PRIVATE fathom_history_export)

target_compile_options(fathom_history_csv PRIVATE -Wall -Wextra -Wpedantic -Werror)

add_library(fathom_practice STATIC Source/core/PracticeTransport.cpp Source/core/PracticeTimeline.cpp Source/platform/PracticePlayback.cpp)

target_include_directories(fathom_practice PUBLIC Source)

target_link_libraries(fathom_practice PUBLIC fathom_core fathom_metronome)

target_compile_options(fathom_practice PRIVATE -Wall -Wextra -Wpedantic -Werror)

target_sources(Fathom PRIVATE Source/desktop/PracticeView.cpp)

target_link_libraries(Fathom PRIVATE fathom_practice)

add_library(fathom_attempt_capture STATIC Source/practice/AttemptCapture.cpp)

target_include_directories(fathom_attempt_capture PUBLIC Source)

target_link_libraries(fathom_attempt_capture PUBLIC fathom_practice fathom_recovery fathom_progression)

target_compile_options(fathom_attempt_capture PRIVATE -Wall -Wextra -Wpedantic -Werror)

add_library(fathom_practice_session STATIC Source/practice/PracticeSession.cpp)

target_include_directories(fathom_practice_session PUBLIC Source)

target_link_libraries(fathom_practice_session PUBLIC fathom_attempt_capture)

target_compile_options(fathom_practice_session PRIVATE -Wall -Wextra -Wpedantic -Werror)

target_link_libraries(Fathom PRIVATE fathom_practice_session)

add_library(fathom_metronome STATIC Source/metronome/Metronome.cpp)

target_include_directories(fathom_metronome PUBLIC Source)

target_link_libraries(fathom_metronome PUBLIC fathom_core)

target_compile_options(fathom_metronome PRIVATE -Wall -Wextra -Wpedantic -Werror)

add_library(fathom_metronome_preferences STATIC Source/metronome/MetronomePreferences.cpp)

target_include_directories(fathom_metronome_preferences PUBLIC Source)

target_link_libraries(fathom_metronome_preferences PUBLIC fathom_metronome fathom_storage)

target_compile_options(fathom_metronome_preferences PRIVATE -Wall -Wextra -Wpedantic -Werror)

add_library(fathom_metronome_playback STATIC Source/platform/MetronomePlayback.cpp)

target_sources(fathom_metronome_playback PRIVATE Source/metronome/Polyrhythm.cpp)

target_include_directories(fathom_metronome_playback PUBLIC Source)

target_link_libraries(fathom_metronome_playback PUBLIC fathom_metronome)

target_compile_options(fathom_metronome_playback PRIVATE -Wall -Wextra -Wpedantic -Werror)

target_sources(Fathom PRIVATE Source/desktop/MetronomeView.cpp Source/desktop/FreeplayView.cpp)

target_link_libraries(Fathom PRIVATE fathom_metronome_playback fathom_metronome_preferences)

add_library(fathom_tab STATIC Source/core/TabPresentation.cpp)

target_include_directories(fathom_tab PUBLIC Source)

target_link_libraries(fathom_tab PUBLIC fathom_core)

target_compile_options(fathom_tab PRIVATE -Wall -Wextra -Wpedantic -Werror)

add_library(fathom_tab_playback STATIC Source/core/TabPlayback.cpp)

target_include_directories(fathom_tab_playback PUBLIC Source)

target_link_libraries(fathom_tab_playback PUBLIC fathom_tab fathom_practice)

target_compile_options(fathom_tab_playback PRIVATE -Wall -Wextra -Wpedantic -Werror)

target_sources(Fathom PRIVATE Source/desktop/TabView.cpp)

target_link_libraries(Fathom PRIVATE fathom_tab_playback)

add_library(fathom_practice_keyboard STATIC Source/desktop/PracticeKeyboardMac.mm)

target_include_directories(fathom_practice_keyboard PUBLIC Source)

target_compile_options(fathom_practice_keyboard PRIVATE -Wall -Wextra -Wpedantic -Werror)

set_source_files_properties(Source/desktop/PracticeKeyboardMac.mm PROPERTIES COMPILE_FLAGS "-fobjc-arc")

target_link_libraries(fathom_practice_keyboard PUBLIC juce::juce_gui_basics "-framework AppKit")

target_compile_definitions(fathom_practice_keyboard PUBLIC JUCE_WEB_BROWSER=0 JUCE_USE_CURL=0 JUCE_MODAL_LOOPS_PERMITTED=0)

target_link_libraries(Fathom PRIVATE fathom_practice_keyboard)

if(APPLE)

endif()

file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/representative-v1-manifest.json" FATHOM_LESSON_MANIFEST_SHA)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/representative-v1-manifest.json")

add_library(fathom_lessons STATIC Source/content/LessonCatalog.cpp Source/content/SelectedCatalogStore.cpp)

target_link_libraries(fathom_lessons PUBLIC fathom_content)

target_compile_definitions(fathom_lessons PRIVATE FATHOM_LESSON_MANIFEST_SHA="${FATHOM_LESSON_MANIFEST_SHA}")

file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/rung02-extension-v1/manifest.json" FATHOM_RUNG02_MANIFEST_SHA)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/rung02-extension-v1/manifest.json")

target_compile_definitions(fathom_lessons PRIVATE FATHOM_RUNG02_MANIFEST_SHA="${FATHOM_RUNG02_MANIFEST_SHA}")

file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/rung03-extension-v1/manifest.json" FATHOM_RUNG03_MANIFEST_SHA)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/rung03-extension-v1/manifest.json")

target_compile_definitions(fathom_lessons PRIVATE FATHOM_RUNG03_MANIFEST_SHA="${FATHOM_RUNG03_MANIFEST_SHA}")

file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/rung04-extension-v1/manifest.json" FATHOM_RUNG04_MANIFEST_SHA)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/rung04-extension-v1/manifest.json")

target_compile_definitions(fathom_lessons PRIVATE FATHOM_RUNG04_MANIFEST_SHA="${FATHOM_RUNG04_MANIFEST_SHA}")

file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level006-extension-v1/manifest.json" FATHOM_LEVEL006_MANIFEST_SHA)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level006-extension-v1/manifest.json")

target_compile_definitions(fathom_lessons PRIVATE FATHOM_LEVEL006_MANIFEST_SHA="${FATHOM_LEVEL006_MANIFEST_SHA}")

file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/rung05-extension-v1/manifest.json" FATHOM_RUNG05_MANIFEST_SHA)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/rung05-extension-v1/manifest.json")

target_compile_definitions(fathom_lessons PRIVATE FATHOM_RUNG05_MANIFEST_SHA="${FATHOM_RUNG05_MANIFEST_SHA}")

file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level008-extension-v1/manifest.json" FATHOM_LEVEL008_MANIFEST_SHA)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level008-extension-v1/manifest.json")

target_compile_definitions(fathom_lessons PRIVATE FATHOM_LEVEL008_MANIFEST_SHA="${FATHOM_LEVEL008_MANIFEST_SHA}")

file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level010-extension-v1/manifest.json" FATHOM_LEVEL010_MANIFEST_SHA)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level010-extension-v1/manifest.json")

target_compile_definitions(fathom_lessons PRIVATE FATHOM_LEVEL010_MANIFEST_SHA="${FATHOM_LEVEL010_MANIFEST_SHA}")

file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level007-extension-v1/manifest.json" FATHOM_LEVEL007_MANIFEST_SHA)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level007-extension-v1/manifest.json")

target_compile_definitions(fathom_lessons PRIVATE FATHOM_LEVEL007_MANIFEST_SHA="${FATHOM_LEVEL007_MANIFEST_SHA}")

file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level009-extension-v1/manifest.json" FATHOM_LEVEL009_MANIFEST_SHA)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level009-extension-v1/manifest.json")

target_compile_definitions(fathom_lessons PRIVATE FATHOM_LEVEL009_MANIFEST_SHA="${FATHOM_LEVEL009_MANIFEST_SHA}")

file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level011-extension-v1/manifest.json" FATHOM_LEVEL011_MANIFEST_SHA)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level011-extension-v1/manifest.json")

target_compile_definitions(fathom_lessons PRIVATE FATHOM_LEVEL011_MANIFEST_SHA="${FATHOM_LEVEL011_MANIFEST_SHA}")

file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level013-extension-v1/manifest.json" FATHOM_LEVEL013_MANIFEST_SHA)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level013-extension-v1/manifest.json")

target_compile_definitions(fathom_lessons PRIVATE FATHOM_LEVEL013_MANIFEST_SHA="${FATHOM_LEVEL013_MANIFEST_SHA}")

file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level014-extension-v1/manifest.json" FATHOM_LEVEL014_MANIFEST_SHA)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level014-extension-v1/manifest.json")

target_compile_definitions(fathom_lessons PRIVATE FATHOM_LEVEL014_MANIFEST_SHA="${FATHOM_LEVEL014_MANIFEST_SHA}")

file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level015-extension-v1/manifest.json" FATHOM_LEVEL015_MANIFEST_SHA)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level015-extension-v1/manifest.json")

target_compile_definitions(fathom_lessons PRIVATE FATHOM_LEVEL015_MANIFEST_SHA="${FATHOM_LEVEL015_MANIFEST_SHA}")

file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level016-extension-v1/manifest.json" FATHOM_LEVEL016_MANIFEST_SHA)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level016-extension-v1/manifest.json")

target_compile_definitions(fathom_lessons PRIVATE FATHOM_LEVEL016_MANIFEST_SHA="${FATHOM_LEVEL016_MANIFEST_SHA}")

file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level017-extension-v1/manifest.json" FATHOM_LEVEL017_MANIFEST_SHA)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level017-extension-v1/manifest.json")

target_compile_definitions(fathom_lessons PRIVATE FATHOM_LEVEL017_MANIFEST_SHA="${FATHOM_LEVEL017_MANIFEST_SHA}")

file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level018-extension-v1/manifest.json" FATHOM_LEVEL018_MANIFEST_SHA)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level018-extension-v1/manifest.json")

target_compile_definitions(fathom_lessons PRIVATE FATHOM_LEVEL018_MANIFEST_SHA="${FATHOM_LEVEL018_MANIFEST_SHA}")

file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level019-extension-v1/manifest.json" FATHOM_LEVEL019_MANIFEST_SHA)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level019-extension-v1/manifest.json")

target_compile_definitions(fathom_lessons PRIVATE FATHOM_LEVEL019_MANIFEST_SHA="${FATHOM_LEVEL019_MANIFEST_SHA}")

file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level020-extension-v1/manifest.json" FATHOM_LEVEL020_MANIFEST_SHA)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level020-extension-v1/manifest.json")

target_compile_definitions(fathom_lessons PRIVATE FATHOM_LEVEL020_MANIFEST_SHA="${FATHOM_LEVEL020_MANIFEST_SHA}")

file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level021-extension-v1/manifest.json" FATHOM_LEVEL021_MANIFEST_SHA)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level021-extension-v1/manifest.json")

target_compile_definitions(fathom_lessons PRIVATE FATHOM_LEVEL021_MANIFEST_SHA="${FATHOM_LEVEL021_MANIFEST_SHA}")

file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level022-extension-v1/manifest.json" FATHOM_LEVEL022_MANIFEST_SHA)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level022-extension-v1/manifest.json")

target_compile_definitions(fathom_lessons PRIVATE FATHOM_LEVEL022_MANIFEST_SHA="${FATHOM_LEVEL022_MANIFEST_SHA}")

file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level023-extension-v1/manifest.json" FATHOM_LEVEL023_MANIFEST_SHA)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level023-extension-v1/manifest.json")

target_compile_definitions(fathom_lessons PRIVATE FATHOM_LEVEL023_MANIFEST_SHA="${FATHOM_LEVEL023_MANIFEST_SHA}")

file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level024-extension-v1/manifest.json" FATHOM_LEVEL024_MANIFEST_SHA)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level024-extension-v1/manifest.json")

target_compile_definitions(fathom_lessons PRIVATE FATHOM_LEVEL024_MANIFEST_SHA="${FATHOM_LEVEL024_MANIFEST_SHA}")

file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level030-extension-v1/manifest.json" FATHOM_LEVEL030_MANIFEST_SHA)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level030-extension-v1/manifest.json")

target_compile_definitions(fathom_lessons PRIVATE FATHOM_LEVEL030_MANIFEST_SHA="${FATHOM_LEVEL030_MANIFEST_SHA}")

file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level029-extension-v1/manifest.json" FATHOM_LEVEL029_MANIFEST_SHA)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level029-extension-v1/manifest.json")

target_compile_definitions(fathom_lessons PRIVATE FATHOM_LEVEL029_MANIFEST_SHA="${FATHOM_LEVEL029_MANIFEST_SHA}")

file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level025-extension-v1/manifest.json" FATHOM_LEVEL025_MANIFEST_SHA)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level025-extension-v1/manifest.json")

target_compile_definitions(fathom_lessons PRIVATE FATHOM_LEVEL025_MANIFEST_SHA="${FATHOM_LEVEL025_MANIFEST_SHA}")

file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level026-extension-v1/manifest.json" FATHOM_LEVEL026_MANIFEST_SHA)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level026-extension-v1/manifest.json")

target_compile_definitions(fathom_lessons PRIVATE FATHOM_LEVEL026_MANIFEST_SHA="${FATHOM_LEVEL026_MANIFEST_SHA}")

file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level012-rung08-extension-v1/manifest.json" FATHOM_LEVEL012_R08_MANIFEST_SHA)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level012-rung08-extension-v1/manifest.json")

target_compile_definitions(fathom_lessons PRIVATE FATHOM_LEVEL012_R08_MANIFEST_SHA="${FATHOM_LEVEL012_R08_MANIFEST_SHA}")

file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level013-rung03-extension-v1/manifest.json" FATHOM_LEVEL013_R03_MANIFEST_SHA)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level013-rung03-extension-v1/manifest.json")

target_compile_definitions(fathom_lessons PRIVATE FATHOM_LEVEL013_R03_MANIFEST_SHA="${FATHOM_LEVEL013_R03_MANIFEST_SHA}")

file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level013-rung04-extension-v1/manifest.json" FATHOM_LEVEL013_R04_MANIFEST_SHA)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level013-rung04-extension-v1/manifest.json")

target_compile_definitions(fathom_lessons PRIVATE FATHOM_LEVEL013_R04_MANIFEST_SHA="${FATHOM_LEVEL013_R04_MANIFEST_SHA}")

file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level013-rung05-extension-v1/manifest.json" FATHOM_LEVEL013_R05_MANIFEST_SHA)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level013-rung05-extension-v1/manifest.json")

target_compile_definitions(fathom_lessons PRIVATE FATHOM_LEVEL013_R05_MANIFEST_SHA="${FATHOM_LEVEL013_R05_MANIFEST_SHA}")

file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level015-rung05-extension-v1/manifest.json" FATHOM_LEVEL015_R05_MANIFEST_SHA)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level015-rung05-extension-v1/manifest.json")

target_compile_definitions(fathom_lessons PRIVATE FATHOM_LEVEL015_R05_MANIFEST_SHA="${FATHOM_LEVEL015_R05_MANIFEST_SHA}")

file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level015-rung04-extension-v1/manifest.json" FATHOM_LEVEL015_R04_MANIFEST_SHA)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level015-rung04-extension-v1/manifest.json")

target_compile_definitions(fathom_lessons PRIVATE FATHOM_LEVEL015_R04_MANIFEST_SHA="${FATHOM_LEVEL015_R04_MANIFEST_SHA}")

file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level015-rung06-extension-v1/manifest.json" FATHOM_LEVEL015_R06_MANIFEST_SHA)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level015-rung06-extension-v1/manifest.json")

file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level003-modeb001-extension-v1/manifest.json" FATHOM_LEVEL003_MODEB001_MANIFEST_SHA)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level003-modeb001-extension-v1/manifest.json")

target_compile_definitions(fathom_lessons PRIVATE FATHOM_LEVEL003_MODEB001_MANIFEST_SHA="${FATHOM_LEVEL003_MODEB001_MANIFEST_SHA}")

file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level004-ex002-extension-v1/manifest.json" FATHOM_LEVEL004_EX002_MANIFEST_SHA)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level004-ex002-extension-v1/manifest.json")

target_compile_definitions(fathom_lessons PRIVATE FATHOM_LEVEL004_EX002_MANIFEST_SHA="${FATHOM_LEVEL004_EX002_MANIFEST_SHA}")

file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level004-ex003-extension-v1/manifest.json" FATHOM_LEVEL004_EX003_MANIFEST_SHA)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level004-ex003-extension-v1/manifest.json")

target_compile_definitions(fathom_lessons PRIVATE FATHOM_LEVEL004_EX003_MANIFEST_SHA="${FATHOM_LEVEL004_EX003_MANIFEST_SHA}")

file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level004-ex004-extension-v1/manifest.json" FATHOM_LEVEL004_EX004_MANIFEST_SHA)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level004-ex004-extension-v1/manifest.json")

target_compile_definitions(fathom_lessons PRIVATE FATHOM_LEVEL004_EX004_MANIFEST_SHA="${FATHOM_LEVEL004_EX004_MANIFEST_SHA}")

file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level004-ex005-extension-v1/manifest.json" FATHOM_LEVEL004_EX005_MANIFEST_SHA)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level004-ex005-extension-v1/manifest.json")

target_compile_definitions(fathom_lessons PRIVATE FATHOM_LEVEL004_EX005_MANIFEST_SHA="${FATHOM_LEVEL004_EX005_MANIFEST_SHA}")

file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level004-ex006-extension-v1/manifest.json" FATHOM_LEVEL004_EX006_MANIFEST_SHA)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level004-ex006-extension-v1/manifest.json")

target_compile_definitions(fathom_lessons PRIVATE FATHOM_LEVEL004_EX006_MANIFEST_SHA="${FATHOM_LEVEL004_EX006_MANIFEST_SHA}")

file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level004-ex007-extension-v1/manifest.json" FATHOM_LEVEL004_EX007_MANIFEST_SHA)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level004-ex007-extension-v1/manifest.json")

target_compile_definitions(fathom_lessons PRIVATE FATHOM_LEVEL004_EX007_MANIFEST_SHA="${FATHOM_LEVEL004_EX007_MANIFEST_SHA}")

file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level004-ex008-extension-v1/manifest.json" FATHOM_LEVEL004_EX008_MANIFEST_SHA)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level004-ex008-extension-v1/manifest.json")

target_compile_definitions(fathom_lessons PRIVATE FATHOM_LEVEL004_EX008_MANIFEST_SHA="${FATHOM_LEVEL004_EX008_MANIFEST_SHA}")

file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level004-ex009-extension-v1/manifest.json" FATHOM_LEVEL004_EX009_MANIFEST_SHA)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level004-ex009-extension-v1/manifest.json")

target_compile_definitions(fathom_lessons PRIVATE FATHOM_LEVEL004_EX009_MANIFEST_SHA="${FATHOM_LEVEL004_EX009_MANIFEST_SHA}")

file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level004-ex010-extension-v1/manifest.json" FATHOM_LEVEL004_EX010_MANIFEST_SHA)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level004-ex010-extension-v1/manifest.json")

target_compile_definitions(fathom_lessons PRIVATE FATHOM_LEVEL004_EX010_MANIFEST_SHA="${FATHOM_LEVEL004_EX010_MANIFEST_SHA}")

file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level004-ex011-extension-v1/manifest.json" FATHOM_LEVEL004_EX011_MANIFEST_SHA)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level004-ex011-extension-v1/manifest.json")

target_compile_definitions(fathom_lessons PRIVATE FATHOM_LEVEL004_EX011_MANIFEST_SHA="${FATHOM_LEVEL004_EX011_MANIFEST_SHA}")

file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level004-ex012-extension-v1/manifest.json" FATHOM_LEVEL004_EX012_MANIFEST_SHA)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level004-ex012-extension-v1/manifest.json")

target_compile_definitions(fathom_lessons PRIVATE FATHOM_LEVEL004_EX012_MANIFEST_SHA="${FATHOM_LEVEL004_EX012_MANIFEST_SHA}")

file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level004-ex013-extension-v1/manifest.json" FATHOM_LEVEL004_EX013_MANIFEST_SHA)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level004-ex013-extension-v1/manifest.json")

target_compile_definitions(fathom_lessons PRIVATE FATHOM_LEVEL004_EX013_MANIFEST_SHA="${FATHOM_LEVEL004_EX013_MANIFEST_SHA}")

file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level004-ex014-extension-v1/manifest.json" FATHOM_LEVEL004_EX014_MANIFEST_SHA)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level004-ex014-extension-v1/manifest.json")

target_compile_definitions(fathom_lessons PRIVATE FATHOM_LEVEL004_EX014_MANIFEST_SHA="${FATHOM_LEVEL004_EX014_MANIFEST_SHA}")

file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level004-ex015-extension-v1/manifest.json" FATHOM_LEVEL004_EX015_MANIFEST_SHA)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level004-ex015-extension-v1/manifest.json")

target_compile_definitions(fathom_lessons PRIVATE FATHOM_LEVEL004_EX015_MANIFEST_SHA="${FATHOM_LEVEL004_EX015_MANIFEST_SHA}")

file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level002-ex002-extension-v1/manifest.json" FATHOM_LEVEL002_EX002_MANIFEST_SHA)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level002-ex002-extension-v1/manifest.json")

target_compile_definitions(fathom_lessons PRIVATE FATHOM_LEVEL002_EX002_MANIFEST_SHA="${FATHOM_LEVEL002_EX002_MANIFEST_SHA}")

target_compile_definitions(fathom_lessons PRIVATE FATHOM_LEVEL015_R06_MANIFEST_SHA="${FATHOM_LEVEL015_R06_MANIFEST_SHA}")

file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level014-rung03-extension-v1/manifest.json" FATHOM_LEVEL014_R03_MANIFEST_SHA)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level014-rung03-extension-v1/manifest.json")

target_compile_definitions(fathom_lessons PRIVATE FATHOM_LEVEL014_R03_MANIFEST_SHA="${FATHOM_LEVEL014_R03_MANIFEST_SHA}")

file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level015-rungs02-03-extension-v1/manifest.json" FATHOM_LEVEL015_R0203_MANIFEST_SHA)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level015-rungs02-03-extension-v1/manifest.json")

target_compile_definitions(fathom_lessons PRIVATE FATHOM_LEVEL015_R0203_MANIFEST_SHA="${FATHOM_LEVEL015_R0203_MANIFEST_SHA}")

file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level001-extension-v1/manifest.json" FATHOM_LEVEL001_MANIFEST_SHA)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level001-extension-v1/manifest.json")

target_compile_definitions(fathom_lessons PRIVATE FATHOM_LEVEL001_MANIFEST_SHA="${FATHOM_LEVEL001_MANIFEST_SHA}")

file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level080-module-a-pass1-r02-extension-v1/manifest.json" FATHOM_LEVEL080_R02_MANIFEST_SHA)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/level080-module-a-pass1-r02-extension-v1/manifest.json")

target_compile_definitions(fathom_lessons PRIVATE FATHOM_LEVEL080_R02_MANIFEST_SHA="${FATHOM_LEVEL080_R02_MANIFEST_SHA}")

target_compile_options(fathom_lessons PRIVATE -Wall -Wextra -Wpedantic -Werror)

target_sources(Fathom PRIVATE Source/desktop/LessonView.cpp Source/desktop/GuidedSessionView.cpp)

target_link_libraries(Fathom PRIVATE fathom_lessons)

find_package(Python3 COMPONENTS Interpreter REQUIRED)

file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/RuntimeAssets/curriculum-shards/handoff.json" FATHOM_SHARD_HANDOFF_SHA)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/RuntimeAssets/curriculum-shards/handoff.json")

file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/RuntimeAssets/curriculum-shards/bundle/bundle-inventory.json" FATHOM_SHARD_INVENTORY_SHA)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/RuntimeAssets/curriculum-shards/bundle/bundle-inventory.json")

file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/RuntimeAssets/curriculum-shards/bundle/Build/parallel-02/four-real-shard-manifest-r01/manifest.json" FATHOM_SHARD_MANIFEST_SHA)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/RuntimeAssets/curriculum-shards/bundle/Build/parallel-02/four-real-shard-manifest-r01/manifest.json")

add_library(fathom_curriculum_shards STATIC Source/content/CurriculumShardCatalog.cpp)

target_link_libraries(fathom_curriculum_shards PUBLIC fathom_content)

target_compile_definitions(fathom_curriculum_shards PRIVATE
    FATHOM_SHARD_HANDOFF_SHA="${FATHOM_SHARD_HANDOFF_SHA}"
    FATHOM_SHARD_INVENTORY_SHA="${FATHOM_SHARD_INVENTORY_SHA}"
    FATHOM_SHARD_MANIFEST_SHA="${FATHOM_SHARD_MANIFEST_SHA}")

target_compile_options(fathom_curriculum_shards PRIVATE -Wall -Wextra -Wpedantic -Werror)

target_link_libraries(Fathom PRIVATE fathom_curriculum_shards)

add_library(fathom_source_library STATIC Source/content/SourceLibraryCatalog.cpp)

target_link_libraries(fathom_source_library PUBLIC fathom_content)

target_compile_definitions(fathom_source_library PRIVATE
    FATHOM_SOURCE_LIBRARY_HANDOFF_SHA="e796142858f7649e2e3189110265b1bf7346bd055971a92f6519b446d0dc0696"
    FATHOM_SOURCE_LIBRARY_INDEX_SHA="8c5ef69740505e92176943b94c4da25a04178e7707190f061dbba923dbbcebbf")

target_compile_options(fathom_source_library PRIVATE -Wall -Wextra -Wpedantic -Werror)

target_sources(Fathom PRIVATE Source/desktop/SourceLibraryView.cpp)

target_link_libraries(Fathom PRIVATE fathom_source_library)

target_sources(Fathom PRIVATE Source/desktop/FretboardView.cpp)

if(TARGET fathom_lesson_view_tests)

endif()

if(APPLE)

endif()

target_sources(fathom_practice PRIVATE Source/content/LessonAdmission.cpp)

target_link_libraries(fathom_practice PUBLIC fathom_content)

target_link_libraries(fathom_lessons PUBLIC fathom_practice)

add_library(fathom_lesson_attempt STATIC Source/practice/LessonAttempt.cpp)

target_link_libraries(fathom_lesson_attempt PUBLIC fathom_lessons fathom_practice_session)

target_compile_options(fathom_lesson_attempt PRIVATE -Wall -Wextra -Wpedantic -Werror)

foreach(target Fathom          )

    if(TARGET ${target})

        target_link_libraries(${target} PRIVATE fathom_lesson_attempt)

    endif()

endforeach()

if(APPLE)

endif()

if(APPLE)

endif()

add_library(fathom_desktop_progress STATIC Source/desktop/ProgressPresentation.cpp Source/desktop/ProgressView.cpp
    Source/progression/SelectedCaseComparison.cpp
    Source/progression/ProgressDomainCoverage.cpp Source/progression/InstalledDomainCatalog.cpp)

target_include_directories(fathom_desktop_progress PUBLIC Source)

target_link_libraries(fathom_desktop_progress PUBLIC fathom_progression fathom_lessons juce::juce_gui_basics)

target_compile_definitions(fathom_desktop_progress PUBLIC JUCE_WEB_BROWSER=0 JUCE_USE_CURL=0)

target_compile_options(fathom_desktop_progress PRIVATE -Wall -Wextra -Wpedantic -Werror)

foreach(progress_consumer Fathom      )

    if(TARGET ${progress_consumer})

        target_link_libraries(${progress_consumer} PRIVATE fathom_desktop_progress)

    endif()

endforeach()

if(APPLE)

endif()

add_library(fathom_preview_resume STATIC Source/desktop/PreviewResume.cpp)

target_include_directories(fathom_preview_resume PUBLIC Source)

target_link_libraries(fathom_preview_resume PUBLIC fathom_progression fathom_metronome_preferences)

target_compile_options(fathom_preview_resume PRIVATE -Wall -Wextra -Wpedantic -Werror)

target_link_libraries(Fathom PRIVATE fathom_preview_resume)

if(APPLE)

endif()

if(APPLE)

endif()

if(APPLE)

endif()

if(APPLE)

endif()

if(APPLE)

endif()

if(APPLE)

endif()

if(APPLE)

endif()

foreach(fretboard_lesson_consumer
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
)

    if(TARGET ${fretboard_lesson_consumer})

        target_sources(${fretboard_lesson_consumer} PRIVATE Source/desktop/FretboardView.cpp)

    endif()

endforeach()

target_sources(fathom_lessons PRIVATE Source/content/LearnSourceIndex.cpp)

file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/learn-source-index-v1/index.json" FATHOM_LEARN_PIN_0)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/learn-source-index-v1/index.json")

file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/learn-source-index-v1/exercises.jsonl" FATHOM_LEARN_PIN_1)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/learn-source-index-v1/exercises.jsonl")

file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/learn-source-index-v1/accepted-overlay.json" FATHOM_LEARN_PIN_2)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/learn-source-index-v1/accepted-overlay.json")

file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/typed-manual-tasks-v1/manifest.json" FATHOM_TYPED_MANUAL_MANIFEST_SHA)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/typed-manual-tasks-v1/manifest.json")

file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/compiled-manual-families-v1/manifest.json" FATHOM_COMPILED_MANUAL_MANIFEST_SHA)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/compiled-manual-families-v1/manifest.json")

file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/Source/tasks/GeneratedTriadFamily.hpp" FATHOM_COMPILED_MANUAL_TABLE_SHA)

add_library(fathom_manual_tasks STATIC Source/tasks/TaskContract.cpp Source/tasks/InstalledManualTaskRegistry.cpp Source/tasks/ManualTaskAdapter.cpp Source/tasks/CompiledFamily.cpp)

target_include_directories(fathom_manual_tasks PUBLIC Source)

target_link_libraries(fathom_manual_tasks PUBLIC fathom_content fathom_core)

target_compile_definitions(fathom_manual_tasks PRIVATE FATHOM_TYPED_MANUAL_MANIFEST_SHA="${FATHOM_TYPED_MANUAL_MANIFEST_SHA}" FATHOM_COMPILED_MANUAL_MANIFEST_SHA="${FATHOM_COMPILED_MANUAL_MANIFEST_SHA}" FATHOM_COMPILED_MANUAL_TABLE_SHA="${FATHOM_COMPILED_MANUAL_TABLE_SHA}")

target_compile_options(fathom_manual_tasks PRIVATE -Wall -Wextra -Wpedantic -Werror)

add_library(fathom_manual_view STATIC Source/desktop/ManualTaskView.cpp)

target_include_directories(fathom_manual_view PUBLIC Source)

target_link_libraries(fathom_manual_view PUBLIC fathom_manual_tasks juce::juce_gui_basics)

target_compile_options(fathom_manual_view PRIVATE -Wall -Wextra -Wpedantic -Werror)

target_link_libraries(Fathom PRIVATE fathom_manual_view)

foreach(manual_home_target        )

    if(TARGET ${manual_home_target})

        target_link_libraries(${manual_home_target} PRIVATE fathom_manual_view)

    endif()

endforeach()

file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/compiled-recipe-families-v1/level068/manifest.json" FATHOM_LEVEL068_RECIPE_MANIFEST_SHA)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/compiled-recipe-families-v1/level068/manifest.json")

add_library(fathom_recipe_tasks STATIC Source/tasks/RecipeTask.cpp Source/tasks/InstalledRecipeTaskRegistry.cpp)

target_include_directories(fathom_recipe_tasks PUBLIC Source)

target_link_libraries(fathom_recipe_tasks PUBLIC fathom_content fathom_core)

target_compile_definitions(fathom_recipe_tasks PRIVATE FATHOM_LEVEL068_RECIPE_MANIFEST_SHA="${FATHOM_LEVEL068_RECIPE_MANIFEST_SHA}")

target_compile_options(fathom_recipe_tasks PRIVATE -Wall -Wextra -Wpedantic -Werror)

target_sources(fathom_manual_view PRIVATE Source/desktop/RecipeTaskView.cpp)

target_link_libraries(fathom_manual_view PUBLIC fathom_recipe_tasks)

file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/compiled-recipe-families-v1/advanced/manifest.json" FATHOM_ADVANCED_RECIPE_MANIFEST_SHA)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/compiled-recipe-families-v1/advanced/manifest.json")

add_library(fathom_advanced_recipe_tasks STATIC Source/tasks/AdvancedRecipeTask.cpp Source/tasks/InstalledAdvancedRecipeRegistry.cpp)

target_include_directories(fathom_advanced_recipe_tasks PUBLIC Source)

target_link_libraries(fathom_advanced_recipe_tasks PUBLIC fathom_recipe_tasks fathom_content fathom_core)

target_compile_definitions(fathom_advanced_recipe_tasks PRIVATE FATHOM_ADVANCED_RECIPE_MANIFEST_SHA="${FATHOM_ADVANCED_RECIPE_MANIFEST_SHA}")

target_compile_options(fathom_advanced_recipe_tasks PRIVATE -Wall -Wextra -Wpedantic -Werror)

target_sources(fathom_manual_view PRIVATE Source/desktop/AdvancedRecipeTaskView.cpp)

target_link_libraries(fathom_manual_view PUBLIC fathom_advanced_recipe_tasks)

file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/compiled-recipe-families-v1/curriculum/manifest.json" FATHOM_MANUAL_CURRICULUM_MANIFEST_SHA)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/compiled-recipe-families-v1/curriculum/manifest.json")

file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/compiled-recipe-families-v1/manual-procedure-graph/manifest.json" FATHOM_MANUAL_PROCEDURE_GRAPH_MANIFEST_SHA)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/Content/runtime/compiled-recipe-families-v1/manual-procedure-graph/manifest.json")

add_library(fathom_compiled_procedure_tasks STATIC
    Source/tasks/OrderedContactFamily.cpp
    Source/tasks/OrderedContactTask.cpp
    Source/tasks/OrderedContactTaskFormAdapter.cpp
    Source/tasks/InstalledOrderedContactTaskRegistry.cpp
    Source/tasks/ManualCurriculumTask.cpp
    Source/tasks/InstalledManualCurriculumRegistry.cpp
    Source/tasks/ManualProcedureGraph.cpp
    Source/tasks/C111CountryStudyOperators.cpp
    Source/tasks/DimContextControls.cpp
    Source/tasks/IntervalRecoveryControls.cpp
    Source/tasks/L97ListeningSixControls.cpp
    Source/tasks/MelodicFunctionControls.cpp
    Source/tasks/PhraseApplicationControls.cpp
    Source/tasks/QualifiedSourceControls.cpp
    Source/tasks/RootlessSeventhControls.cpp
    Source/tasks/SourceFormControls.cpp
    Source/tasks/SourceMapControls.cpp
    Source/tasks/SourceTaskControls.cpp
    Source/tasks/TimedAssessmentControls.cpp
    Source/tasks/C1661HiddenSourceSeven.cpp
    Source/tasks/CompiledChordSessionControls.cpp
    Source/tasks/PracticalTriadControls.cpp
    Source/tasks/TimedChordChangeControls.cpp
    Source/tasks/WholeChordFormControls.cpp
    Source/tasks/AnticipationGridControls.cpp
    Source/tasks/AnticipationLadderControls.cpp
    Source/tasks/DiagonalRouteControls.cpp
    Source/tasks/ProgressionCircleControls.cpp
    Source/tasks/SourcePhraseControls.cpp
    Source/tasks/BeginnerSourceControls.cpp
    Source/tasks/BoundSourceUnits.cpp
    Source/tasks/C1661SourceOperators.cpp
    Source/tasks/HarmonizedTriadControls.cpp
    Source/tasks/Level68SourceControls.cpp
    Source/tasks/RhythmGridControls.cpp
    Source/tasks/SeventhFamilyControls.cpp
    Source/tasks/ManualProcedureSharedContexts.cpp
    Source/tasks/ManualProcedureDomainReports.cpp
    Source/tasks/ManualProcedureAdvancedReports.cpp
    Source/tasks/ManualProcedureProtocolSupport.cpp
    Source/tasks/ManualProcedureSourceContracts.cpp
    Source/tasks/ManualProcedureSourcePolicies.cpp
    Source/tasks/ManualProcedureCapstoneReports.cpp
    Source/tasks/ManualProcedureLearnerSchemas.cpp
    Source/tasks/InstalledManualProcedureGraphRegistry.cpp
    Source/tasks/PhysicalContactFamily.cpp
    Source/tasks/PiecewiseContactFamily.cpp
    Source/tasks/InstalledPiecewiseContactTaskRegistry.cpp
    Source/tasks/HarmonicContactFamily.cpp
    Source/tasks/InstalledHarmonicContactTaskRegistry.cpp
    Source/tasks/SourceContactFamily.cpp
    Source/tasks/SourceContactChoiceOperators.cpp
    Source/tasks/InstalledSourceContactTaskRegistry.cpp
    Source/tasks/ManualContactSourceHandle.cpp
    Source/tasks/InstalledPhysicalContactTaskRegistry.cpp)

target_include_directories(fathom_compiled_procedure_tasks PUBLIC Source)

target_link_libraries(fathom_compiled_procedure_tasks PUBLIC fathom_recipe_tasks fathom_content fathom_core)

target_compile_definitions(fathom_compiled_procedure_tasks PRIVATE FATHOM_MANUAL_CURRICULUM_MANIFEST_SHA="${FATHOM_MANUAL_CURRICULUM_MANIFEST_SHA}")

target_compile_definitions(fathom_compiled_procedure_tasks PRIVATE FATHOM_MANUAL_PROCEDURE_GRAPH_MANIFEST_SHA="${FATHOM_MANUAL_PROCEDURE_GRAPH_MANIFEST_SHA}")

target_compile_options(fathom_compiled_procedure_tasks PRIVATE -Wall -Wextra -Wpedantic -Werror)

set_property(SOURCE Source/tasks/ManualCurriculumTask.cpp APPEND PROPERTY COMPILE_OPTIONS -Wno-overlength-strings)

set_property(SOURCE Source/tasks/ManualProcedureGraph.cpp Source/tasks/BoundSourceUnits.cpp Source/tasks/InstalledManualProcedureGraphRegistry.cpp APPEND PROPERTY COMPILE_OPTIONS -O2)

set_property(SOURCE Source/tasks/TimedAssessmentControls.cpp Source/tasks/BoundSourceUnits.cpp Source/tasks/ManualProcedureGraph.cpp Source/tasks/PhysicalContactFamily.cpp Source/tasks/PiecewiseContactFamily.cpp Source/tasks/HarmonicContactFamily.cpp Source/tasks/SourceContactFamily.cpp APPEND PROPERTY COMPILE_OPTIONS -Wno-overlength-strings)

target_sources(fathom_manual_view PRIVATE Source/desktop/TypedManualForm.cpp Source/desktop/CompiledManualProcedureView.cpp)

target_link_libraries(fathom_manual_view PUBLIC fathom_compiled_procedure_tasks fathom_storage)

add_library(fathom_ear234_tasks STATIC
    Source/tasks/ear234/Ear234.cpp
    Source/tasks/ear234/ClosedKernel.cpp
    Source/tasks/ear234/ClosedPackage.cpp)

target_include_directories(fathom_ear234_tasks PUBLIC Source Source/tasks/ear234)

target_link_libraries(fathom_ear234_tasks PUBLIC fathom_content fathom_core PRIVATE fathom_compiled_procedure_tasks)

target_compile_features(fathom_ear234_tasks PUBLIC cxx_std_17)

target_compile_options(fathom_ear234_tasks PRIVATE -Wall -Wextra -Wpedantic -Werror -Wno-overlength-strings)

target_sources(fathom_manual_view PRIVATE Source/desktop/EarSourceProcedureView.cpp)

target_link_libraries(fathom_manual_view PUBLIC fathom_ear234_tasks)

add_library(fathom_c43_tasks STATIC
    Source/tasks/c43/C43.cpp
    Source/tasks/c43/ClosedPackage.cpp)

target_include_directories(fathom_c43_tasks PUBLIC Source Source/tasks/c43)

target_link_libraries(fathom_c43_tasks PUBLIC fathom_ear234_tasks fathom_content)

target_compile_features(fathom_c43_tasks PUBLIC cxx_std_17)

target_compile_options(fathom_c43_tasks PRIVATE -Wall -Wextra -Wpedantic -Werror -Wno-overlength-strings -Wno-misleading-indentation)

target_sources(fathom_manual_view PRIVATE Source/desktop/C43SourceProcedureView.cpp)

target_link_libraries(fathom_manual_view PUBLIC fathom_c43_tasks)

target_sources(fathom_compiled_procedure_tasks PRIVATE Source/tasks/InstalledExtraSource17Registry.cpp)

target_sources(fathom_source_library PRIVATE Source/content/BookContextSourceCatalog.cpp)

if(APPLE)

endif()

option(FATHOM_ENABLE_UI_AUDIT_FIXTURE "Build the reviewed software-only native UI audit capability" OFF)

get_property(FATHOM_SETUP_TARGETS DIRECTORY PROPERTY BUILDSYSTEM_TARGETS)

foreach(FATHOM_SETUP_TARGET IN LISTS FATHOM_SETUP_TARGETS)

    get_target_property(FATHOM_SETUP_SOURCES ${FATHOM_SETUP_TARGET} SOURCES)

    if(FATHOM_SETUP_SOURCES)

        foreach(FATHOM_SETUP_SOURCE IN LISTS FATHOM_SETUP_SOURCES)

            if(FATHOM_SETUP_SOURCE MATCHES "(^|/)GuitarSetupView\\.cpp$")

                target_sources(${FATHOM_SETUP_TARGET} PRIVATE Source/desktop/OnboardingView.cpp)

                break()

            endif()

        endforeach()

    endif()

endforeach()

get_property(FATHOM_PLAYBACK_BOARD_TARGETS DIRECTORY PROPERTY BUILDSYSTEM_TARGETS)

foreach(playback_board_consumer IN LISTS FATHOM_PLAYBACK_BOARD_TARGETS)

    get_target_property(playback_board_sources ${playback_board_consumer} SOURCES)

    if(playback_board_sources)

        foreach(playback_board_source IN LISTS playback_board_sources)

            if(playback_board_source MATCHES "(^|/)PracticeView\\.cpp$")

                target_sources(${playback_board_consumer} PRIVATE Source/desktop/PlaybackFretboardView.cpp)

                break()

            endif()

        endforeach()

    endif()

endforeach()

include("${CMAKE_CURRENT_SOURCE_DIR}/cmake/GeneratedSourceIncludes.cmake")
