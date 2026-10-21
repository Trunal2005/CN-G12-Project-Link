> Publication note: the original prepared workstation and archived raw sessions described below are historical. A fresh clone starts with empty session history and regenerated media. See [publication notes](PUBLICATION.md) for included evidence, fresh setup and verification.

# StallGuard technical audit — 20 October 2026

Audit evidence: `data/audits/20261020T142828Z/`. This continues the existing application. No media regeneration, model fitting or parameter search was performed. Original data/results and model files were not rewritten. New sessions, failed attempts, checks and comparisons are separated from historical measurements.

## Preservation and environment

`baseline.zip` preserves 581 original source/document/media/model/session/result files. `baseline-hashes.json` records their SHA-256 hashes; `versions.json` and `baseline-runtime.json` record Python 3.13.5, Node 20.19.4, npm 10.8.2, dash.js 5.0.3, Playwright 1.56.0 and installed Chrome 155.0.8059.85, plus Python package versions. Setup was inspected, not executed. A fresh environment installation and other operating systems were not tested.

`frozen.json` records the repaired runtime, whole bundle, model file and tree identities before comparison. It checks 534 protected original data/media/model/result files. One already-open paused legacy browser continued appending sample events to `dc4abd50.../events.jsonl` during initial inspection. The original prefix is unchanged in the archive; the 1,849-byte append-only tail and its provenance are preserved separately. The old server was stopped before the frozen matrix. This tail is not comparison evidence.

Frozen comparison identities:

- Source: `9806f3f2fafe6cd7b44b8a61f57a15e32c1fb15e8f9955d4d014fe3870fc5880`
- Whole bundle: `bundle-v2:ff3bf778eca735432709c7cbed130ece84a685a386229bf6bd291f2bc6ca1360`
- Model JSON file: `cb98ce38c9350210b17eb83b1a05754f015cc591a91b28bbf48f1971969b449d`
- Forest trees: `4629d8c36753afdc88dad71586ac52b59f8dc7a4019d0518307261b8e560b45e`

The final runnable release has source identity `3051b5e8b6e77f24a622408061fc32cb2fe54a7e5aa0aa13cb7690e59d59bc1a`. `release.json` records the later **measurement-only** v2.1 correction, unchanged controller/pacer/media/feature source hashes, and unchanged media/model identities. The matched matrix was completed on the frozen v2 source above before this correction. `frozen-runtime.zip` preserves the exact measured implementation; raw matrix records remain v2 and are not relabeled.

## A. Genuine media and delivery pacing

FFprobe verified four real H.264 streams: 426×240, 640×360, 854×480 and 1280×720. Each has 60 video fragments. All 240 video `tfdt` decode timestamps were parsed from the actual MP4 bodies and match the aligned two-second timeline; each representation's first fragment begins with a keyframe. Audio is one AAC track. `media-verified.json` contains the evidence. Actual Chrome request/decoding checks, not a mocked video element, establish playback.

The earlier ~10% underdelivery was reproduced using the current frozen video body and a separate baseline server. The cause was capped earned credit: while continuously backlogged, asynchronous timer wakeups could exceed the 20 ms credit cap and repeatedly discard budget. The repaired limiter retains bounded wakeup credit while backlogged, still starts with zero credit, still shares one FIFO budget, and retains at most one 2 KiB grant after long idle periods. Backlogged credit is capped at 50 ms of current rate, minimum 2 KiB, maximum 64 KiB. No configured rate rescaling or relaxed tolerance was used.

| Concurrent requests | Actual bytes | Baseline measured Mbps | Repaired measured Mbps | Repaired error |
|---|---:|---:|---:|---:|
| 1 | 1,347,384 | 1.57485 | 1.74396 | −0.345% |
| 2 | 2,694,768 | 1.57945 | 1.74576 | −0.242% |

Configured capacity was 1.750 Mbps in both cases. Repaired windows were 6.181 and 12.349 seconds. Health requests during these transfers had maximum observed latency 0.0215 seconds. These are finite local calibration windows, not universal timing guarantees.

A single video response began around 11.52 seconds of profile time and continued across the 12-second drop; its 13–18 s window delivered 0.4784 Mbps against 0.480 Mbps configured. Mixed audio/video/two repeated ranged responses measured 1.7434 Mbps aggregate against 1.750 configured. Both ranges returned 206 with correct 65,536-byte bodies; all payload bytes matched delivery accounting. Audio completed in 0.296 s despite the competing bodies. A deliberately cancelled transfer retained its aborted record; a subsequent init request completed in 0.00665 s and finalization drained successfully. Ordinary/ranged/repeated media all pass through the same budget. Manifest, health, model, frontend and telemetry traffic remain unshaped.

Media-transfer slots are now reserved before response headers, and finalization shares a lock with reservation/telemetry. Response-level cleanup releases slots even when streaming is cancelled before the generator completes. This prevents finalization racing a late body or leaving a reservation stuck.

This is **application-level HTTP delivery pacing**. It does not simulate packet loss, radio interference, real router queues or a modified TCP congestion-control algorithm. Payload-byte counts represent bytes yielded to the HTTP stack, not TCP acknowledgments; disconnect detection can lag by a small grant.

## B. The 26-switch / 76-request result

The historical original stable/historical raw trace contains:

- 76 completed video requests, covering 24 unique presentation intervals;
- 63 distinct representation/interval pairs and 13 exact-asset repeats;
- 27 rendered callbacks: one initial assignment and 26 genuine transitions;
- 30 requested-quality callbacks, 77 decision boundaries, 32 init requests;
- one aborted video transfer at the fixed stopping boundary.

Extra requests were largely real replacement downloads, not invented throughput samples or repeated initialization of the whole player. dash.js up-switch fast replacement fetched higher quality near the playhead; the controller's buffer subsequently crossed its low-buffer threshold, downgraded, then upgraded again as small bodies refilled the buffer. Init segment caching was disabled, so quality switches also requested init fragments. One decision per completed-observation boundary shows that repeated rule invocations did not themselves advance hysteresis.

An isolated baseline on the **current** bundle reproduced 26 transitions with 70 completed video requests in 40 seconds. The repaired append-only common buffer setting, with the original controller/estimators unchanged, produced three transitions and 25 total video requests in a 40-second candidate. Do not directly subtract 70 completed requests from 25 total requests; the raw summaries distinguish completed and aborted requests. Pacing was also corrected between baseline and candidate, so not every bitrate/latency difference can be assigned solely to fast switching.

`streaming.buffer.fastSwitchEnabled=false` is now shared by historical, ML and default modes. Default means the real default **ABR rules** with documented common experimental buffer settings, not untouched player defaults. The two custom modes retain the same safety factor, reserve, low-buffer behavior and observation-based hysteresis. Initial assignments, requested transitions, rendered transitions, replacement intervals, exact-asset repeats, retries and aborts have separate counters. The original 26 genuine transitions are preserved, not relabeled as a counter bug.

## C. Real forest usage and causality

The same frozen genuine 32-tree model is retained. All eight training/validation export hashes match its saved provenance; no new test run is included in fitting. Numerical tests cover the 11 feature names/order/units, five-observation warmup and float32 tree threshold behavior. Actual browser forest decisions were additionally checked against the sklearn artifact. Different forecasts with the same non-protected state can choose different representations in a counterfactual test.

New decision records carry an epoch, decision ID and model checksum. Completed targets associate only with a matching representation/epoch decision made before actual request start. Late, overlapping, incomplete, cached, non-200 or body-size-mismatched observations are excluded explicitly rather than counted as player errors or scored as valid targets. The model never receives profile identity, seed, future capacity or the target's eventual size/throughput as a feature. Seek resets the feature history and increments epoch, avoiding boundary collisions. The offline feature builder now respects epoch resets too.

The full frozen run had 60 custom-rule invocations, 60 distinct decisions and zero duplicate decision IDs. Idempotence on artificially repeated calls is separately unit-tested; no claim is made that this particular full run exercised duplicate invocations.

The browser audit verified missing and structurally malformed models produce visible historical fallback; a later valid run on the same page used actual forest inference. Default mode after custom mode had zero registered custom rules and zero custom decisions, while its throughput/BOLA settings remained active. All built-in ABR/abandon rules are disabled in the two custom modes. Effective settings are recorded per run.

## D. Measurement and session lifecycle repairs

- Telemetry now carries monotonic sequence IDs. Retrying a batch is idempotent; gaps are rejected, and queued rows remain until acknowledged. Silent queue truncation/reordering was removed.
- Per-session locking serializes ingestion/finalization/media reservation. Finalized sessions reject late events; repeated finish returns the same saved result.
- Stop records final playback progress and pending Resource Timing entries **before** player reset, then flushes and waits for transfers to drain. Stop calls share one completion promise.
- Synthetic stop is a separate `close` event. A native `ended` event is separately identifiable; an early stopped bounded run is not mistaken for full playback.
- Normal pagehide/refresh beacons pending telemetry and marks the interrupted session partial after bodies drain. The UI restores a prior session ID for history/export rather than silently resuming it.
- v2 quality weighting splits media progress at actual rendered-transition media times and includes the final stop sample. Initial quality assignment is separate from a genuine transition. Exposed buffered ranges are measured only at the current playhead, not summed across gaps.
- Pauses/seeks remain excluded from stall incidents. The v2 ratio denominator excludes their deliberate intervals too. Open stalls are closed at the last observation and flagged as right-censored if no resume/terminal event was observed.
- A comparison checkbox race introduced during error handling was reproduced and fixed using immediate selection and versioned async responses. Failed create requests re-enable Start; valid and fallback model labels remain explicit.

Read-only recomputations are in `original-summary-recompute.json` and `analysis/original-summary-recompute.json`. Original results have **not** been overwritten. Old logs lacked transition media times and a final progress sample; a different legacy weighting approximation cannot recover those missing measurements. Therefore v2 recalculations of old bitrate are an audit sensitivity check, not newly discovered perceptual ground truth. Rebuffer seconds and genuine transition counts can be checked directly from their raw event intervals. New v2 metrics are reported separately.

`played_seconds` means maximum observed playhead position. In no-seek benchmark runs this is actual media-time progress; after seeking it is not total watched duration. `quality_weighted_media_s` is the observed forward progress with known rendered quality. Native waiting plus near-empty exposed buffer is a practical network-stall classifier, not complete decode-fault diagnosis.

### Initial requested assignment correction (audit-v2.1)

The final metric cross-check reproduced one remaining undercount: dash.js emitted change callbacks for requested representations 1 and 2, but no callback for initial representation 0. Treating the first change as the initial assignment incorrectly reported one transition instead of two. Existing actual MediaSegment request-start records show `0 → 1 → 2` unambiguously. A targeted regression failed (1 versus 2), then passed after deriving initial assignment and transitions from those request records. The live requested-quality display now explicitly logs its first actual assignment. Legacy records without request starts report the requested transition counter unavailable rather than guessing.

This correction does not affect selection, pacing, causal inputs or rendered-quality metrics. `analysis/requested-counter-corrections.json` keeps corrected derived counters separate from the immutable saved v2 summaries; all other saved matrix metrics were asserted identical when recomputed. The final release also gives actual API error badges an error colour. No comparison was rerun or relabeled to manufacture a better performance outcome.

## E. Bundle and experiment identity

The original fingerprint already covered all `.mp4`/`.m4s` files in the media directory, **not a per-session subset**. That suspected subset bug was not present. It did omit MPD/inventory and cached on inventory mtime, so changed bodies could be missed. Bundle-v2 hashes the entire permitted manifest/inventory/init/media set, independent of requests, without that mtime-only cache. Tests verify different requested subsets retain the same identity, changing an unrequested body changes identity, and changing MPD changes identity. Unlisted stray files are not served as assets.

Sessions additionally record model file/tree, source, controller and effective/common-settings identities and bounded ending rule. UI comparison warns for unknown historical identities, differing bundles/settings/source/model/endings, interactions, incomplete runs, or an ML run with no genuine forest targets. Intended policy-specific ABR differences are not compared as if the ABR settings must be identical.

Original evaluated bytes from the earlier experiment are unavailable; only their recorded inventory/hashes/results remain. This audit preserves that historical limitation and runs new comparisons entirely on the current frozen bundle. No attempt was made to regenerate approximate bytes and pass them off as the original.

## F. Verification and results

The UI audit exercised actual control selection/start/live playback/stop, parsed JSON/CSV exports, repeated historical/ML/default sessions, visible missing/malformed-model fallback, pause/seek, refresh-to-partial state, injected API failure recovery, desktop/phone layout, low-effects and reduced motion. Non-local browser requests were blocked with localhost permitted; no unexpected external attempt or uncaught page error occurred. The only failed HTTP responses in the passing fault-injection run were the intentionally injected missing-model 404 and create-error 500.

Executed final automated suite: **16 Python tests and 7 TypeScript tests passed**, including 124 model parity vectors. An earlier cancellation unit test intermittently tried to cancel an already-completed 2 KiB grant after two Windows timer sleeps; it now deterministically queues the task before cancellation. Real in-flight HTTP cancellation was tested separately and passed. Read-only FFprobe verification passed after using approved execution for the temporary probe file; the first restricted-sandbox attempt was blocked by temp-file permissions, not a codec defect. The frontend production build passed with the existing large dash.js bundle warning.

The frozen full-clip ML/stable run `5305c480da2b42dc8454255d8a175089` waited for native ended with a 180-second safety timeout: 119.999999 s media duration, zero stalls, two rendered transitions and 60 video requests. This is distinct from bounded comparisons.

The final runnable v2.1 release was separately checked again: `c1fe3f44aacf418bbb5f86f15c61dbc6` reached native ended at 119.999999 s with **2,880 decoded frames**, zero stalls, two rendered transitions, 60 video requests and no aborted deliveries. Its requested counter correctly records one initial assignment and two transitions. The exact professor-view selection of three finished fluctuating/seed-502 matrix rows also passed on this final build, with no incompatibility warning and successfully parsed three-session JSON/four-row CSV exports.

Executed **27 sequential 40-second runs**, three repetitions per policy/profile, with fresh Chrome contexts and one shared frozen source/media/model/settings reference. Actual no-seek media-time progress ranged from **37.824 to 39.573 seconds**. All had zero stalls, no unexpected HTTP failures/page errors/external requests. This is bounded evidence, not 27 full-video completions.

| Profile | Historical rendered Mbps | ML rendered Mbps | Default rendered Mbps | Rebuffering |
|---|---:|---:|---:|---|
| stable | 1.612 ± 0.001 | 0.910 ± 0.003 | 2.397 ± 0.000 | 0 s in all runs |
| step | 0.800 ± 0.021 | 0.555 ± 0.000 | 1.207 ± 0.000 | 0 s in all runs |
| fluctuate | 0.676 ± 0.067 | 0.744 ± 0.007 | 0.612 ± 0.157 | 0 s in all runs |

Values are mean ± sample SD, n=3 per cell. Full startup, switching, latency, bytes, played-time and variability fields are in `analysis/aggregate.csv` and `analysis/RESULTS.md`; per-run/raw records remain in `matrix/`.

Across **525 causal held-out request rows**, forest MAE was **0.463 Mbps**, EWMA **0.353 Mbps**; forest RMSE **0.622 Mbps**, EWMA **0.663 Mbps**. **179 actual runtime forest predictions** matched sklearn with maximum absolute difference **0.0 bps**. The forest again underperformed on MAE. No tuning/retraining was performed.

The model delivered higher mean bitrate on fluctuations but lower bitrate on stable/step; all policies were stall-free. No overall superiority or stall-reduction claim follows. Three repetitions provide sample variability, not confidence of Internet generalization.

## Remaining limits

Single Windows/Chrome host; generated calibration content; synthetic application capacity; small frozen training set; original evaluated bodies unavailable; possible distribution shift from the original training pacing/media; finite repetitions and ~1 Hz chart sampling. Hard process/browser kills may lose the unflushed event tail. A Windows asyncio connection-reset callback was observed when abruptly closing a test browser; later requests and cleanup passed. No paid service or API key is required. No WAN, packet-loss, perceptual-quality or commercial superiority claim is justified.

See PAGE_MAP.md for actual controls, PROFESSOR_DEMO.md for the 6–8 minute Hinglish walkthrough, VIVA_VERIFIED.md for tested explanations and STATUS.md for the working launch command and latest evidence paths.
