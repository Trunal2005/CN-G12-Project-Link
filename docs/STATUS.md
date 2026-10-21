> Publication note: the original prepared workstation and archived raw sessions described below are historical. A fresh clone starts with empty session history and regenerated media. See [publication notes](PUBLICATION.md) for included evidence, fresh setup and verification.

# DEMO READY WITH LIMITATIONS

Verified 20 October 2026 on Windows, Python 3.13.5, Node 20.19.4 and installed Chrome 155.0.8059.85. The repaired app is running at **http://127.0.0.1:8000**. Do not start a duplicate listener.

## Exact launch command

From `the repository root`, after stopping an existing listener if necessary:

```powershell
$env:STALLGUARD_SESSION_DIR = '.\data\audits\20261020T142828Z\sessions'
python scripts/run.py
```

This selects the new prepared audit history. Without the environment variable, the app reads the legacy history, which is preserved but includes older identities/metrics and partial runs. Refresh an old browser tab to load the repaired build. No setup, media regeneration or retraining is needed for the prepared demo.

## Completed repairs

- Fixed backlogged limiter credit loss; preserved zero initial credit, one shared concurrent media budget and bounded burst/idle credit. Real calibration improved from ~10% low to 0.24–0.35% low under the same tolerance.
- Disabled fast buffer replacement explicitly and consistently across policies; retained real default ABR rules for default mode. Stable candidate churn fell from 26 rendered transitions to 3; extra original requests were reconciled rather than called fake counters.
- Added idempotent sequenced telemetry, locked media reservation/finalization, final stop samples, native-end versus early-close distinction, and refresh-to-partial handling.
- Added explicit forecast IDs/seek epochs, body/cache/status validation, actual model checksums, strict model readiness/fallback and compatible whole-bundle/source/model/settings/ending identities.
- Fixed comparison selection race, initial requested-quality logging/counting and API error badge colour. Requested and rendered quality remain separate.

## Actual verification

**16 Python tests, 7 TypeScript tests, 124 numerical parity vectors.** Actual MP4 decode timestamps align across all 240 video fragments; FFprobe verifies four resolutions and keyframes. Shared concurrent/ranged/repeated transfers, a capacity drop during one active response, cancellation recovery and control responsiveness passed.

**27 sequential matched 40-second runs:** three policies × stable/step/fluctuating profiles × three repetitions, all on one frozen source/media/model/common configuration. All were stall-free; actual playhead progress, quality, switching, latency, bytes and sample SD are retained. The forest's MAE was **0.463 Mbps vs EWMA 0.353 Mbps**; RMSE was **0.622 vs 0.663 Mbps**. All **179 recorded runtime forest predictions** matched sklearn exactly. This does not show an overall ML or stall-reduction advantage.

Two separate full-clip checks reached native ended at 120 seconds and decoded 2,880 frames. The final runnable release check is `c1fe3f44aacf418bbb5f86f15c61dbc6`: zero stalls, two rendered transitions, 60 video requests and no aborted deliveries. It uses `audit-v2.1` initial-request counters. The earlier frozen comparison/full-run source and final logging-only release source are recorded separately; raw frozen summaries were not overwritten.

Actual UI checks passed for selection/start/stop/save, parsed exports, repeated modes/default rule isolation, forest and missing/malformed-model fallback, pause/seek, refresh, partial/error recovery, phone/desktop layout, reduced motion and low effects. The exact three prepared `fluctuate / seed 502` finished rows were selected and exported with no compatibility warning. Non-local requests were blocked throughout browser checks while localhost remained reachable.

## Evidence and professor preparation

- `docs/AUDIT_REPORT.md`: diagnosis, reproduced defects, fixes, metric changes and measured results.
- `docs/PAGE_MAP.md`: actual `/` tabs, headings and exact control labels.
- `docs/PROFESSOR_DEMO.md`: verified 6–8 minute Hinglish script and real segment/forecast/render trace.
- `docs/VIVA_VERIFIED.md`: CN/ML/DS responsibilities and answers to likely questions.
- `data/audits/20261020T142828Z/baseline.zip`, `baseline-hashes.json`, `versions.json`: preserved baseline.
- `frozen.json`, `frozen-runtime.zip`, `release.json`: measured versus final release identities.
- `transport/report.json`, `media-verified.json`: HTTP/codec/timeline evidence.
- `matrix/runs.json`, `matrix/runs.csv`, per-run JSON: immutable bounded experiments.
- `analysis/RESULTS.md`, `aggregate.csv`, `comparison.png`, `real-segment-trace.json`, `requested-counter-corrections.json`: derived evidence.
- `ui-r2/integration/report.json`, `professor-view/report.json`: passing UI/export checks.
- `release-check/full/runs.json`: final natural-end proof.
- `verification.json`: executed outcomes, including failed attempts and resolved causes.

## Limits / untested areas

Single local Windows/Chrome host, synthetic content/capacity, small older training dataset and distribution shift; no packet-loss/RTT/router/TCP-control simulation. Original historical evaluated media bytes are unavailable; old results remain historical. Three bounded repetitions do not establish Internet generalization, and the full-clip checks are separate from the comparison matrix. Hard kills can lose an unflushed tail. Bitrate is not perceptual quality; charts update ~1 Hz. Fresh-venv setup, macOS/Linux, other browsers, OS-wide airplane mode and a repeated full-duration policy matrix were not executed. A Windows connection-reset callback occurred after abrupt test-browser closure; subsequent cleanup/requests passed. The frontend retains a large dash.js bundle warning and the global Python environment has its pre-existing unrelated google-genai/httpx dependency conflict; an isolated venv is recommended for new installation.

No unresolved external blocker prevents the prepared local demo. First action: open the URL, use Playback Lab, then follow PROFESSOR_DEMO.md.
