# Using the desktop source preview

This guide describes the implemented controls and explicit content limits. The prepared app is compiled and component-tested separately from native user acceptance. No personal profile is included. This full private stage retains the existing curriculum and source assets.

## Start and choose a profile

An ordinary launch does not automatically open a learner profile or start audio. Initial setup covers presentation, appearance, guitar configuration, audio settings and a summary. Back retains the draft; Skip for now returns Home. User profile can reopen setup later.

Create a **named new profile** explicitly, or choose **Open existing profile** explicitly. Finish setup must not silently switch to an existing profile. User profile shows the profile name, UUID and recovery file. Preserve that file and its recovery records; do not edit SQLite by hand. With no open profile, presentation choices can remain session-only.

## Home destinations

| Page | Use |
| --- | --- |
| Learn | Browse the existing installed levels/exercises and source explanations, prepare/resume a queue and enter admitted Practice explicitly. |
| Free play | Timer/resume, metronome, rhythm preview, reference tones and audio settings. |
| User profile | Profile identity, setup, Progress/history, default BPM, guitar setup and any retained-original recovery. |
| Settings | Beginner/Advanced/Developer presentation, Default/Light/Dark appearance, save/check/reset controls and preview details. |
| Quit | Normal save/discard/cancel decisions with unresolved operations protected. |

Default BPM must be a whole number from20 to300. It seeds new Learn choices only, not retained queues, recorded tempos or metronome presets. Presentation levels change disclosure; they never grant admission or credit.

## Audio and Free play

Opening a tool starts no sound. Audio settings use explicit Connect and Enable controls; Start or Play begins output. Stop/Finish and return navigation follow the activity's release/save gates. A device or format fault can require stopped recovery and reconnection. Reconnecting is not permission to restart old work automatically.

Free play activity is separate from curriculum progression. Its timer can be resumed in its section; opening another page does not invent elapsed time or musical performance. Metronome, reference and rhythm tools share audio ownership and settings.

## Learn and workbook content

Choose an installed level/sublevel/exercise, review its source/instructions and prepare a selection. Practice requires that exact selection/version's existing admission. Start remains explicit. Learn-only Clear queue preserves saved attempts/completed members and uses existing unresolved-operation/recovery guards.

Exercise library provides original PDF/TXT access and supported source context. Full originals supplement explanations. Source representation, runtime admission, manual declaration and learner completion are separate; not every indexed source unit is an ordinary playable exercise. Required unavailable external resources and qualified cases remain explicit. Reading source or showing a note earns no credit.

The current closed package is retained exactly; arbitrary files cannot replace its source/version bindings. Do not edit manifests or hashes to invent admission.

New Guided entry is disabled. A retained original can remain visible under User profile for its existing recovery/close workflow. Unsupported originals are preserved for support rather than replaced with a new plan.

## Save and recover

Wait for confirmed saves. An uncertain outcome may mean the original write happened: keep the same profile/operation and use its check/recovery action. Back from recovery changes presentation, not ownership of the held original. Do not force a replacement write or delete recovery files to make a warning disappear.

A CSV or copied worksheet is readable output, not a restorable profile backup. Use only disposable synthetic profiles while developing, especially when testing interrupted operations or newer preference shapes. Older binaries can reject newer stored preferences.

See [data and recovery](data-and-recovery.md) and [release status](release-status.md) for exact boundaries.
