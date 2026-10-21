# Executed results

> **Historical experiment, preserved.** These measurements predate the repaired-app audit and used earlier evaluated media bytes that are no longer available. Do not present this table as the latest repaired app or combine it with current-bundle runs. See [AUDIT_REPORT.md](AUDIT_REPORT.md) and `../data/audits/20261020T142828Z/analysis/RESULTS.md` for new matched evidence. Recomputed metrics are separate sensitivity checks; the original numbers below remain unchanged.

12 held-out bounded playback runs were executed. Ending rule: 40 s wall clock after start. Fresh Chrome contexts, reduced motion, no allowed external requests. One repetition per profile/policy provides **no variance estimate**. These are bounded local prototype experiments, not Internet or full-video performance claims.

## Media and calibration

FFmpeg 7.1 generated 120 seconds of testsrc2 motion and sine audio. FFprobe 4.0.2 verified four distinct video streams (426×240, 640×360, 854×480, 1280×720). Four 60-segment video timelines align exactly; AAC ends at 120 seconds with an additional short final fragment. 301 total media fragments.

The first limiter implementation failed with about 41% underdelivery because of Windows timer granularity. It was corrected before collection. Final real HTTP calibration:

| Concurrent requests | Window (s) | Configured Mbps | Measured Mbps | Error |
|---|---:|---:|---:|---:|
| 1 | 7.11 | 1.75 | 1.579 | 9.8% |
| 2 | 14.27 | 1.75 | 1.573 | 10.1% |

## Model provenance

32 trees, depth ≤6, minimum leaf 3, seed 731. Training: 143 rows / 6 whole sessions; validation: 53 rows / 2 whole sessions. No tuning search. 124 actual/threshold vectors passed Python–TypeScript parity at absolute tolerance 1e-6 bps. Checksum: `4629d8c36753afdc88dad71586ac52b59f8dc7a4019d0518307261b8e560b45e`.

| Split | Samples | Forest MAE (Mbps) | EWMA MAE (Mbps) | Forest RMSE (Mbps) | EWMA RMSE (Mbps) |
|---|---:|---:|---:|---:|---:|
| Training | 143 | 0.182 | 0.289 | 0.342 | 0.603 |
| Validation | 53 | 0.408 | 0.451 | 0.586 | 0.763 |
| Held-out request rows | 466 | 0.400 | 0.325 | 0.578 | 0.613 |

Offline held-out forecast errors score both predictors on the same causal request rows from all final policies. This does not prove a policy advantage: each controller changes future request sizes/timing. Runtime errors in per-run summaries include explicitly labeled warmup EWMA predictions and score only decisions made before target start.

Held-out MAE: forest 0.400, EWMA 0.325 Mbps. RMSE: forest 0.578, EWMA 0.613 Mbps. Default mode had 0 stalls across 4 runs. Request-size/timing distribution and unfamiliar transitions may affect generalization; this experiment does not isolate those causes. Read quality and stalls together. A single repetition cannot establish significance.

## Playback outcomes

| Profile | Policy | Startup s | Rebuffer s | Stalls | Rendered Mbps | Switches | Video requests |
|---|---|---:|---:|---:|---:|---:|---:|
| stable | historical | 0.689 | 0.000 | 0 | 0.618 | 26 | 76 |
| stable | ml | 0.435 | 0.000 | 0 | 1.100 | 8 | 41 |
| stable | default | 0.506 | 0.000 | 0 | 1.890 | 9 | 28 |
| step | historical | 0.343 | 6.811 | 1 | 0.561 | 17 | 56 |
| step | ml | 0.347 | 3.993 | 1 | 0.634 | 12 | 55 |
| step | default | 0.530 | 0.000 | 0 | 1.238 | 7 | 35 |
| fluctuate | historical | 1.090 | 0.000 | 0 | 0.861 | 16 | 45 |
| fluctuate | ml | 1.041 | 0.000 | 0 | 0.798 | 12 | 41 |
| fluctuate | default | 1.649 | 0.000 | 0 | 0.987 | 8 | 32 |
| unfamiliar | historical | 0.418 | 0.646 | 1 | 0.704 | 19 | 41 |
| unfamiliar | ml | 0.442 | 0.644 | 1 | 0.705 | 19 | 43 |
| unfamiliar | default | 0.656 | 0.000 | 0 | 0.992 | 7 | 33 |

Bitrate is a duration-weighted rendered quality proxy. Profile-specific plots are in `data/results/buffer-*.svg`; aggregate CSV/JSON, per-run exports, and the exact session IDs remain beside them. Aborted transfers at the fixed stopping boundary are retained and counted, not mislabeled successful deliveries.

## Verification and limits

- Real Chrome smoke playback advanced beyond 21 seconds and decoded over 500 frames; ML mode requested all four video representations. No uncaught page errors, remote requests, or narrow-viewport horizontal overflow occurred in those smoke checks.
- Backend and causal dataset tests passed; controller idempotence, low-buffer behavior, forecast influence, and forest parity tests passed. See `verification.json` for executed commands/outcomes.
- The prepared app was tested with non-local browser network requests actively blocked. This demonstrates no required CDN/model/media dependency; it is not an OS-wide airplane-mode test.
- The pinned frontend build emits a large-bundle warning (~1.19 MB before gzip, mostly dash.js). It succeeds.
- Global `pip check` found an unrelated pre-existing google-genai/httpx version conflict. Use the documented isolated virtual environment; no unrelated package was changed to resolve it.
- Local single-host pacing, synthetic content/capacity traces, short windows, one repetition, and small data limit generalization. Some forecasts can underperform EWMA. No stall-free or commercial superiority claim is made.
- Deliberate user pauses/seeks invalidate benchmark comparability. Rendered bitrate has ~1 Hz timing resolution. Network waiting is inferred from native waiting plus near-empty playable buffer; decode issues are not fully diagnosed.

## Full-clip verification

Separate ML/stable smoke run `8710b60a76a6427696ad60e9d892fb96` reached natural end at 120.000 s, decoded 2880 frames, had 0 stalls and 0 aborted deliveries. This full-clip run is separate from the bounded comparison matrix.

## Media reproduction boundary

The corrected preparation command was rerun successfully after evaluation. 240 of 306 init/media files differed byte-for-byte after re-encoding. The original evaluated inventory, encode log and SHA-256 asset list are preserved as `media-*-evaluated.*`. All twelve comparison runs used the same original prepared media. The current demo uses the regenerated ladder; sessions carry an encoded-body fingerprint, and the UI warns when fingerprints differ. Bit-identical encoding across runs is not claimed.
