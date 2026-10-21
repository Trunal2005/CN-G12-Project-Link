# Architecture

> Repaired-app audit update: pacing now retains bounded backlogged wakeup credit (50 ms / 64 KiB cap, at least one 2 KiB grant), with one-grant long-idle credit. All policies use an explicit shared `fastSwitchEnabled=false` buffer strategy. Sequenced telemetry, locked finalization, decision IDs/seek epochs, whole-bundle/source/model/settings identities, final progress samples and pagehide-to-partial handling are documented in AUDIT_REPORT.md. New evidence is separate from the historical architecture/results below.

Offline: `prepare_media.py` generates motion/audio or reads an owned clip, runs FFmpeg, checks FFprobe streams and MPD timelines, then writes the segment inventory. `experiments.py collect` runs sequential actual Chrome playback. `ml/features.py` makes causal next-request rows. `train.py` fits a small random forest and exports trees, numerical parity vectors, and provenance.

Runtime: FastAPI serves one built frontend origin. Every run receives a new UUID and immutable profile parameters. Relative manifest URLs naturally resolve under `/media/<session>/`. A safe flat-name resolver rejects arbitrary paths and non-media files. Manifests are unpaced. Init/audio/video/range/repeated requests all share the session limiter. Assets, model JSON, health, and telemetry remain unshaped.

`Limiter.grant` queues 2 KiB grants under a fair asynchronous lock. It uses monotonic time, integrates elapsed byte credit, carries OS timer overshoot into the next grant, and caps credit at 20 ms of rate (minimum one 2 KiB grant, maximum 8 KiB). Initial credit is zero. Rate is resampled during transfer. The clock starts on the first non-manifest media response body. Media cancellation releases the lock and appends a delivery record. A run allows up to 12 active media transfers and at most 32 active sessions; browser event files cap at 32 MB. This is a bounded single-user MVP; long-lived stale active sessions require a server restart and become partial.

The browser Resource Timing observer measures completed video media requests. At each new observation boundary, the custom rule computes a synchronous forecast, runs one common controller, and returns a dash.js representation object. Repeated calls at the same boundary reuse its decision. Both custom policies disable all built-in ABR decision/abandon rules. The default mode retains dash.js ABR defaults; common 12-second buffer settings and telemetry are the same. Audio has one representation.

The UI updates charts once per second. Its CSS perspective stack represents measured playable seconds, capped visually at eight layers. Native video is geometrically stable. Benchmark/reduced-motion modes disable decorative transitions. Controls are locked during a run; a new policy/profile starts a new session. User pause/seek marks interaction and never pauses the external profile clock.

## API

| Route | Purpose |
|---|---|
| GET `/api/health` | backend/media/model readiness and dash.js version |
| GET `/api/assets`, `/api/profiles` | prepared inventory / profile descriptions |
| POST `/api/sessions` | validate immutable asset, policy, profile, seed, scale, purpose |
| GET `/api/sessions`, `/api/sessions/{id}` | recorded run metadata/status/summary |
| POST `/api/sessions/{id}/telemetry` | validated batches, maximum 500 events |
| POST `/api/sessions/{id}/finish` | flush/finalize; 409 while transfers drain |
| GET `/api/sessions/{id}/export` | raw events/deliveries and versioned metadata |
| GET `/api/models/status`, `/api/models/current` | provenance / safe tree JSON |
| GET `/media/{id}/{asset}` | no-store session-aware DASH/media with byte ranges |

Invalid requests use FastAPI's JSON errors. Media suffixes are explicitly permitted. Missing segments never return the SPA. Range requests return 206/416 with appropriate Content-Range. Event timestamps are seconds relative to browser session creation; server durations are relative to its own profile start. These clocks are never subtracted from each other.

Append-only events and deliveries persist immediately; derived summaries are separate. Finalization waits for media cancellation to drain. If the process exits unexpectedly, existing unfinished metadata is reported as partial, not finished. The UI's current preview state is not authoritative evidence; exports and summary calculation are.
