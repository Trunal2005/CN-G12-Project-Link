# Verified page map

Observed in installed Chrome 155.0.8059.85, desktop 1440×1000 and phone 390×844. The app has **one route, `/`, with three tabs**. There are no `/compare` or `/learn` app routes. `/docs` is FastAPI's API documentation, not a product tab.

## Shared header/navigation

Brand: **StallGuard**, subtitle **NETWORK-AWARE ADAPTIVE VIDEO STREAMING**. The brand link returns to Playback Lab. Tab buttons (including visible symbols): **◉ Playback Lab**, **▥ Compare Sessions**, **⌘ How It Works**. **Low effects** is a global checkbox. It disables decorative transitions/tilt; reduced-motion preferences and Benchmark mode also suppress these effects. Tab changes do not stop an active player or create another player.

## Playback Lab

Heading: **Every segment. A smarter decision.** The title is a UI slogan, not evidence that ML outperforms a baseline.

Panel labels: **PLAYBACK MONITOR**, **GENERATED CALIBRATION · 120 s**, **SESSION CONFIGURATION**. The video has native Chrome media controls. It is muted initially but still downloads the AAC track. The footer shows status, **Requested**, **Rendered**, and media time `/ 120 s`.

| Exact label | Control/options and action |
|---|---|
| Adaptation policy | Select **Historical EWMA**, **StallGuard ML**, or **dash.js default**. Changing the selection affects the next session, not an active run. |
| Delivery profile | Select **Stable capacity**, **Drop & recovery**, **Gradual change**, **Correlated fluctuations**, or **Unfamiliar double transition**. |
| Seed | Integer 0–1,000,000. Affects fluctuations; changing it does not alter the stable/step trace. |
| Capacity scale | Number 0.2–3. Multiplies the profile, with server rate bounds. |
| Benchmark mode | Checkbox, followed by **quiet visuals**. Same media/measurements, no decorative transitions. |
| ▷ Start new session | Creates a new UUID, loads inventory/model, initializes one real DASH player and starts actual media requests. Disabled while a run is active or media is unavailable. |
| □ Stop & save | Cancels the current playback experiment, captures its final sample, drains/persists telemetry and finalizes it as **cancelled**. It is saved and inspectable, not a completed full-video benchmark. |
| ↓ Export JSON | Downloads metadata, raw browser events, server delivery records and saved summary for the displayed session ID. Works after stop and after restoring a prior ID on refresh. |

Live cards: **Rendered quality**, **Playable buffer**, **Effective throughput**, **Next-request forecast**, **Rebuffer incidents**. Values are observations/forecasts, not configured capacity. The requested/rendered strip contains the requested value in its tooltip and rendered value as its visible segment label. Throughput/forecast and buffer charts update at approximately 1 Hz.

**TRANSFER INTELLIGENCE** contains **Completed requests & their causal forecasts** and **Playable buffer · amber lines mark stalls**. **BUFFER RESERVE** is an approximate CSS 3D visualization of measured seconds: one layer ≈2 seconds, maximum eight visible layers. It is not a decoded-frame inventory. **LATEST DECISION** gives the controller reason and estimator.

**Decision evidence** is expandable. Table headings are **Time**, **Boundary**, **Predictor**, **Forecast**, **Rep ID**, **Reason**. It displays up to 25 recent decisions. `warmup EWMA`, `EWMA`, `historical fallback` and `random forest` are distinct labels. Default mode deliberately has no custom-controller decision table entries.

Readiness text includes **Trained model available**, **Model unavailable · historical fallback**, and, when the browser rejected the selected ML model, **Historical fallback · model unavailable or invalid**. Natural completion changes the session/header to finished. A refreshed active run is retained as partial; the page does not resume it silently.

## Compare Sessions

Heading: **Let the measurements speak.** Panel: **RECORDED SESSIONS**. **Refresh** fetches session history. Each row has a checkbox, policy, profile/seed/scale, short ID and status.

Saved summaries, including cancelled/partial runs, can be inspected. A warning means the selection is **not a controlled comparison**: incomplete/interacted runs, missing forest usage, unknown historical identity, differing bundle/source/model/common settings/profile/seed/scale/ending rule, or unequal observed durations. Different requested subsets of the same bundle do not themselves cause a mismatch.

The table shows startup, rebuffering, stalls, rendered bitrate, switches, download p95, payload bytes, prediction MAE/targets and observed duration. It includes an overlaid buffer plot and individual plots. **↓ Comparison JSON** exports selected raw sessions; **↓ Summary CSV** exports their summaries with proper CSV escaping. Buttons appear after selection. No sessions produces an honest empty state.

## How It Works

Heading: **From bytes to better decisions.** Sections: **THE LIFECYCLE OF A SEGMENT**, **Observe. Forecast. Adapt. Repeat.**, **CN / Delivery**, **ML / Prediction**, **DS / Evidence**, **Know your measurements**. The definitions cover bitrate, effective throughput, buffer, startup, rebuffer and limits. **Model & training provenance** expands the actual loaded model metadata. There is no additional run or export action on this tab.

## Error/partial behavior

API errors are shown in the page status badge. A failed create request re-enables Start; a failed telemetry batch remains queued for retry and is not silently dropped. Finalized sessions reject late telemetry. Page refresh/unload sends pending events via beacon and marks an interrupted run partial after media transfers drain. A forced process/browser kill can lose the unflushed tail; after restart unfinished metadata is reported partial. This is not crash-proof storage.
