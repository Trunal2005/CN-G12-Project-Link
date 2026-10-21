# Audit: matched measured results

Executed 27 sequential fresh-Chrome runs. Each cell has three repetitions; ending rule is 40 seconds wall clock after start returns, not natural video completion. Actual played seconds are retained per run. All use the same frozen encoded bundle, model, source and common buffer settings.

| Profile | Policy | n | Startup s (mean ± SD) | Rebuffer s (mean ± SD) | Rendered Mbps (mean ± SD) | Switches (mean) | Played s (mean) |
|---|---|---:|---:|---:|---:|---:|---:|
| stable | historical | 3 | 0.471 ± 0.046 | 0.000 ± 0.000 | 1.612 ± 0.001 | 3.00 | 39.542 |
| stable | ml | 3 | 0.439 ± 0.020 | 0.000 ± 0.000 | 0.910 ± 0.003 | 2.00 | 39.572 |
| stable | default | 3 | 0.556 ± 0.008 | 0.000 ± 0.000 | 2.397 ± 0.000 | 1.00 | 39.443 |
| step | historical | 3 | 0.449 ± 0.012 | 0.000 ± 0.000 | 0.800 ± 0.021 | 4.67 | 39.558 |
| step | ml | 3 | 0.448 ± 0.023 | 0.000 ± 0.000 | 0.555 ± 0.000 | 3.00 | 39.561 |
| step | default | 3 | 0.566 ± 0.045 | 0.000 ± 0.000 | 1.207 ± 0.000 | 2.00 | 39.459 |
| fluctuate | historical | 3 | 1.040 ± 0.373 | 0.000 ± 0.000 | 0.676 ± 0.067 | 3.00 | 38.967 |
| fluctuate | ml | 3 | 1.035 ± 0.385 | 0.000 ± 0.000 | 0.744 ± 0.007 | 4.67 | 38.961 |
| fluctuate | default | 3 | 1.630 ± 0.571 | 0.000 ± 0.000 | 0.612 ± 0.157 | 3.67 | 38.357 |

Same-row next-request prediction test: 525 causal rows. Forest MAE 0.463 Mbps vs EWMA 0.353; RMSE 0.622 vs 0.663 Mbps. No new fitting or tuning occurred. 179 runtime forest decisions matched sklearn within 0 bps.

Error bars are sample standard deviations, not confidence intervals. Stable/step seeds do not change their capacity curves; repetitions are independent browser runs of the same prescribed curve. Synthetic local pacing and three repetitions do not establish Internet generalization. The model was trained on older preparation/pacing data; this distribution shift is retained and discussed, not hidden by retraining.

Real segment trace: `ddd7669b9af348b5aa649f333cce8d0e` · `chunk-1-00006.m4s`. See `real-segment-trace.json` for causal features, timestamps, request body bytes, prediction and actual rendered transition.