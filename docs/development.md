# Build the full clean candidate

Use macOS with Apple C/C++17/Objective-C++ tools, CMake 3.22+ and Python 3. All current source, dependencies, generated data and clean runtime inputs are staged locally. No private QA folder, old-stage binary or network fetch is a normal build input. The delivered working tree is hydrated; future Git clones need [Git LFS setup and hydration](git-lfs.md) before building.

```sh
cmake -S . -B build/clean -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON
cmake --build build/clean --parallel 2
ctest --test-dir build/clean --output-on-failure
```

Output: build/clean/Fathom_artefacts/Release/Fathom.app. Do not launch over an existing app/profile. Use disposable synthetic fixtures; no native user acceptance is inferred from component checks.

The new clean transport uses a compiled pin plus strict payload/projection hashes and closed physical inventory. Original logical package/decision/source identities remain stable. Archived proof has an explicit integrity API, and predecessor validation has an explicit typed projection API. No global missing-file or fake-byte fallback is allowed.

Projection generation preserves canonical numeric tokens and validates every preserved-record digest with the actual C++ JSON implementation. Source data and accepted decisions remain unchanged. Do not rewrite trust pins, schemas or source IDs merely to make tests pass.

Historical tests requiring old private oracles are preserved where reproducible, not silently included as supported native actors. Final supported clean-stage suite/results are listed in release status; do not transfer the prior stages' 17/17results wholesale.

Observed host is Apple silicon macOS 26.5.2, Apple clang 21, SDK 26.5 and CMake 4.2.3. Configured macOS 11 is not a tested minimum OS; other platforms/Intel/universal/install distribution remain unverified.
