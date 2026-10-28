![Fathom — practice with intention](docs/assets/fathom-banner.svg)

# Fathom v0.0.1 — full clean staging candidate

**Offline guitar practice, source reading and recoverable local work—with private planning prose separated from the runtime.**

> **Full content, publication pending.** This candidate retains the functional curriculum and does not use empty lesson interfaces. Known private planning/review prose and verifier artifacts are archived separately. Original curriculum and derived content remain private pending publication-rights decisions; no repository, upload or license selection is authorized here.

[User guide](docs/user-guide.md) · [Build](docs/development.md) · [Architecture](docs/architecture.md) · [Data & recovery](docs/data-and-recovery.md) · [Publication status](docs/licensing.md)

## Choose your path

| Home destination | Functions |
| --- | --- |
| **Learn** | Existing levels/exercises, source explanations, queue resume, admitted Practice and Learn-only clear queue. Exercise library opens from Learn. |
| **Free play** | Independent timer/resume, metronome, rhythm preview, reference tones and shared audio settings. |
| **User profile** ↗ | Named profile and recovery identity, setup, Progress/history, default BPM and guitar configuration. |
| **Settings** | Presentation, appearance and preview information. |
| **Quit** ↘ | Existing save/discard/cancel and original-operation release/recovery workflow. |

New Guided entry stays disabled; retained originals keep their protected resolution route. Default BPM 20–300 seeds new Learn choices without retiming retained work. Presentation changes disclosure, not admission or credit. Fathom does not automatically assess guitar performance or infer mastery from reading a source.

## Build locally

Use macOS with Apple C/C++17/Objective-C++ tools, CMake 3.22+ and Python 3. Pinned dependencies and runtime data are local. No network fetch, historical QA folder or original sealed package is needed by the build.

```sh
cmake -S . -B build/clean -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON
cmake --build build/clean --parallel 2
ctest --test-dir build/clean --output-on-failure
```

Output: `build/clean/Fathom_artefacts/Release/Fathom.app`. Building does not launch it. Do not open a new app over an existing Fathom/profile; use explicit disposable fixtures for development. Actual clean-build/test results are recorded in [release status](docs/release-status.md), separately from the prior full-private and restricted candidates.

Observed host: Apple silicon macOS 26.5.2, Apple clang 21, SDK 26.5 and CMake 4.2.3. macOS 11 is a configured target, not a verified minimum OS. Intel/universal, other operating systems, clean installation and distribution qualification are unverified.

## Full curriculum, clean transport

The existing source library represents 105 workbooks. Source representation, admitted Practice, manual declarations and learner completion remain separate; required unavailable external resources and qualified cases remain explicit.

This packaging removes 368 original evidence/report/tool files: 340 Markdown documents, 26 QA JSON reports and 2 verifier artifacts. Sixteen semantic predecessor-report paths are replaced by three typed machine projections, retaining the exact required record identities/revisions/digests/preserved records. It does not replace curriculum with placeholders.

RuntimeAssets contains 1,379 byte-identical original payloads, three projections and one clean transport manifest. Existing machine package/profile/registry/decision and legacy logical-manifest bytes remain unchanged. Historical path/hash/role references remain as minimal machine metadata, not the original narratives.

The new transport manifest is protected by a compiled integrity pin. Retained payloads and projections are hashed; strict closure, path/symlink and cache-reverification rules remain enforced. Missing/tampered payloads or metadata refuse. Raw-byte readers do not fabricate archived prose; predecessor projection has an explicit typed API. Logical bundle/decision/source identities remain distinct from the new physical packaging hash, preserving existing admission and recovery bindings.

Before/after source checks compare 184 catalog cases, 349 admission objects and 621 refusals exactly. Those are objects/refusal outcomes, not counts of playable workbooks. Focused negative tests cover missing/altered metadata, payloads/projections, wrong roles, path escape, symlinks, unexpected files and cache tampering. Final full-build results must be read with their exact scope.

## Code orientation

| Area | Responsibility |
| --- | --- |
| `Source/desktop` | Main composition, five Home routes, setup and view owners. |
| `Source/core`, `platform`, `metronome` | Musical time, device/lifecycle ownership and reference/rhythm output. |
| `Source/content` | Exact source/admission readers and explicit clean transport capability. |
| `Source/tasks`, `GeneratedSources` | Original finite source-bound definitions and manual/recipe policy; no empty replacements. |
| `Source/practice`, `progression`, `storage` | Activity ownership, confirmed history, one profile writer, checkpoints and original-operation recovery. |

Start at [Main.cpp](Source/desktop/Main.cpp), [HomeView.hpp](Source/desktop/HomeView.hpp) and [CleanRuntimeEnvelope.hpp](Source/content/CleanRuntimeEnvelope.hpp). Persistence contracts begin in [ProfileStore.hpp](Source/storage/ProfileStore.hpp).

An uncertain save may have happened. Keep its original owner, operation and immutable bytes until reconciliation. Recovery Back changes presentation, not the held original. A CSV/worksheet is not a restorable profile archive.

## Publication decisions

No project publication license was found in inspected metadata; that does not prove the owner lacks rights. The retained modified JUCE 9.0.1 official license states AGPLv3/commercial options and includes third-party notices. No terms, purchase or license path were selected.

Confirm authority for implementation/prompts/rules/fixtures and original/derived curriculum, choose the project/JUCE distribution path and verify compliance before publication. Genuine curriculum/source interpretation remains retained private content pending those decisions. Clean packaging and engineering checks do not grant redistribution rights.


The 137,376,520-byte runtime definition file has narrow [Git LFS tracking and clone/build instructions](docs/git-lfs.md). Local clean/index-pointer/smudge verification passes with the working bytes and integrity pins unchanged; no remote or global Git settings were changed. The supplied folder is fully hydrated and builds offline. Future hosting LFS availability, quota/budget and remote object availability remain unverified; project/JUCE/content publication decisions also remain open.

## Verification limits

No new production native launch, hearing/physical test, beta, clean install, signing or notarization is implied. The existing full-private stage and original sealed resources remain unchanged for rollback. The restricted public-source candidate is separate and is not the full product.

The local SVG and relative links receive source/accessibility checks. Browser visual preview was denied; no reroute/upload/workaround is used, and rendered visual QA remains unverified.
