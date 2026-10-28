# Local data and recovery

The desktop app uses explicit named local profiles backed by SQLite. The profile name, internal UUID and recovery file are shown under User profile. A profile file is personal data, not a repository fixture.

`ProfileStore` serializes accepted work on its writer. Reply status is not Boolean: **Unresolved** means the original write may have happened. Keep the same owner, operation identity and immutable bytes until a check establishes Confirmed or DefinitelyAbsent. Do not manufacture a replacement Session after a lost receipt.

Recovery validates the original owner, source context and retained bytes. Back hides recovery presentation without releasing the held original. Unsupported work remains preserved rather than silently migrated or replaced. New Guided entry is disabled; retained originals keep their resolution route.

Stopping output is separate from resolving an activity's persistence obligation. Quit asks consumer owners to finish their gates before stopping Store admission and draining accepted writes. A readable CSV or copied worksheet is a projection, not a restorable profile archive.

Setup preferences contain presentation, guitar and mix choices. They do not save a device connection, Enable request, or permission to start sound. New BPM preferences seed new Learn work only. Reading legacy supported preferences does not write/migrate them; older binaries can reject newer saved shapes.

No personal profile, credential store, local log or private QA evidence belongs in Git. Use disposable synthetic profiles for tests and preserve originals before recovery or compatibility experiments. Source code preparation introduced no telemetry or network service; dependency code and future distribution should be reviewed separately.
