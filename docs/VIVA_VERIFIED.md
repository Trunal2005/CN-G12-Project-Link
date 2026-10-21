# Verified viva answers

## Opening explanation

“StallGuard ek local-first adaptive streaming experiment hai. Browser actual DASH segments download aur decode karta hai. Server media bytes ko shared capacity profile ke according pace karta hai. Historical ya ML estimate aur measured buffer se upcoming quality choose hoti hai. Raw measurements aur sequential comparisons se hum behavior honestly evaluate karte hain.”

## Why is this a CN project?

The central behavior is HTTP media delivery, shared-rate scheduling, concurrent audio/video/init/range requests, buffering, adaptive selection and measured startup/rebuffering. ML is a supporting throughput estimator. Data Science prepares causal examples and evaluates results. A prediction chart alone would not make it a CN project; the actual paced bytes and decoded playback do.

## What does localhost demonstrate?

The browser really fetches MPD/init/media HTTP responses, Media Source appends compressed fragments, and Chrome decodes them. The application limiter really delays body bytes and shares its budget across concurrent requests. Same-host operation makes controlled experiments convenient. It does not recreate a mobile network, physical link capacity, packet loss, WAN RTT, router queues or TCP congestion-control changes.

## What does ML predict?

The next completed sequential video-media request's **effective throughput in bps**: `8 × encoded response body bytes / full request duration`. It includes request/first-byte latency. It does not predict a quality label, perceptual quality, future configured capacity or guaranteed playback success. The common controller converts a forecast plus buffer into a valid manifest representation.

The 11 features are the last five completed video throughputs, their mean and population standard deviation, endpoint trend divided by four, last request duration, last observed inter-request idle gap, and last completed body size. No profile ID, seed, future capacity or target size/outcome is supplied. Five observations are needed; cold start uses historical EWMA. Seek resets history and increments the decision epoch.

## How do you prove the forest is used?

Actual decision logs say `random forest`, contain features, decision ID/epoch, forecast and model checksum. The browser audit compared genuine runtime forecasts with the saved sklearn model; the recorded model parity test also covers float32 threshold cases. Completed target requests link only to decisions made before request start, with matching epoch and representation. Missing, malformed or incompatible models visibly use `historical fallback`. Default mode has no custom rule or custom decisions.

Both custom modes use the same rule/controller: forecast safety factor 0.8, 80 kbps reserve, low-buffer protection below four seconds, immediate downgrade and two-observation cautious upgrades. Repeated ABR calls reuse the boundary decision. A counterfactual unit test demonstrates different valid forecasts can select different representations when buffer protection does not dominate; that proves wiring, not real-world superiority.

## Why did ML underperform EWMA on MAE?

In the original held-out request analysis, MAE was forest 0.400 vs EWMA 0.325 Mbps; RMSE was forest 0.578 vs EWMA 0.613 Mbps. It is valid for MAE and RMSE rankings to differ because RMSE weighs larger errors more. A small forest can smooth large errors yet have greater typical bias. Request sizes, request timing, unfamiliar transitions and limited training coverage are plausible contributors; these experiments do not isolate a cause. The audit retains the original model, so changed pacing/encoding distribution is an additional limitation. See current audit results separately; do not substitute new values into the old experiment.

## What is the contribution beyond dash.js?

dash.js supplies the DASH implementation, MSE integration and default ABR baseline. StallGuard supplies the deterministic shared application delivery limiter, typed session/evidence lifecycle, causal measurement/features and forest export/interpreter, one common explainable custom controller, frozen identities, sequential evaluation and teaching UI. This is an undergraduate engineering prototype, not a claim of novel commercial ABR superiority.

## Why requested and rendered quality differ?

Requested quality belongs to an upcoming HTTP request. Rendered quality belongs to the video currently visible after buffering and decoding. Already-buffered old-quality fragments play before later choices. Old fast switching intentionally re-downloaded buffered intervals on up-switch; that was legitimate player behavior, but it interacted badly with low-buffer cycling. The repaired common append-only setting avoids that replacement churn. It also means quality changes can take longer to become visible.

## Were the 26 switches just a bad counter?

The original stable/historical trace contained 27 rendered callbacks, an initial assignment plus 26 genuine transitions. There were 76 completed video requests but only 24 unique presentation intervals, 63 representation/interval pairs, 13 exact-asset repeat requests, 32 init requests and one aborted video transfer at the stopping boundary. Up-switch replacement and repeated upgrades/low-buffer drops explain the excess. There was one decision per observation boundary, not a repeated-callback inflation. A new baseline on the current bundle reproduced 26 transitions. The append-only candidate then had three transitions and 25 total video requests in 40 seconds. Pacing was also repaired, so do not attribute every quality/latency difference to only one setting.

## How do you distinguish throughput, bitrate and configured capacity?

Bitrate is encoded video bits per second from the manifest. Configured capacity is the server's synthetic pacing signal. Effective throughput is an actual body/timing observation. Audio, request latency, variable segment size, idle gaps, scheduler timing and response cancellation affect it. Bytes multiplied by eight become bits; 1 Mbps means 1,000,000 bps. The nominal ladder is 300/600/1200/2500 kbps video plus a shared ~64 kbps AAC track; actual fragment byte sizes vary.

## What changed in pacing?

The old limiter capped earned credit at 20 ms while asynchronous wakeups could arrive later, repeatedly discarding capacity under backlog. Real downloads reproduced ~10% underdelivery. The repaired limiter retains bounded wakeup credit while backlogged (50 ms rate credit, cap 64 KiB, minimum one 2 KiB grant) and caps long-idle credit at one grant. It does not multiply configured rates to fake agreement. Same-tolerance measurements improved to about 0.24–0.35% underdelivery. A single response spanning the 12-second step measured about 0.478 Mbps in the low window against 0.480 Mbps configured.

## What counts as a stall?

Startup is play intent to first native playing. Rebuffering is deduplicated post-start native waiting with near-empty playable buffer, excluding intentional pause/seek and normal end. Intervals close on resume/stop/error. A zero buffer card alone is not proof of a stall: decoded data can continue playing despite discontinuities in exposed buffered ranges. Raw event times permit audit. Decode/render problems are not completely diagnosed by this rule.

The v2 rebuffer ratio divides by observed time after startup excluding deliberate pause/seek intervals; it is versioned separately from the historical denominator. Rendered bitrate weights media-time progress, splitting at recorded rendered transitions. Initial quality assignment is separate from transitions. Final stop records the final progress sample. `played_seconds` is the maximum observed playhead position; with seeking it is not total watched duration. Use no-seek benchmark runs for that interpretation.

## What happens on stop, retries and refresh?

Requested quality has an additional initial-assignment subtlety: dash.js change callbacks do not emit the initial request. The final v2.1 logger explicitly records that first assignment, and requested transition counts derive from actual video MediaSegment request starts. The frozen full-run sequence `0 → 1 → 2` therefore means one initial assignment plus two transitions, not one. The immutable v2 records and separate corrected derived counters show this repair without changing adaptation or pacing.

Stop/save captures final progress and pending resource timings, resets the player, flushes events, waits for media cancellation to drain and finalizes. Sequenced batches can be retried safely without duplicate events; closed sessions reject late ingestion. A normal refresh beacons pending observations and becomes partial. A hard kill can lose the last unflushed events; after server restart unfinished runs remain partial. Server payload accounting includes init/audio/ranges/repeats and attempted body bytes up to disconnect detection, not TCP acknowledgments.

## Are session identities based on what a policy happened to request?

No. The bundle-v2 identity hashes the entire permitted MPD, inventory, init and media bundle. Policies requesting different subsets still share an identity. Altering a body or manifest changes it. Model file/tree hashes, source identity, controller version and settings identities are recorded separately. Comparing different prepared bundles is not a controlled same-asset comparison.

## What can you conclude from the results?

Correct mechanisms and reproducible local experiments are demonstrated. Three repetitions per current profile/policy report variability; they do not establish broad Internet generalization or statistical significance. The full-clip proof is separate from 40-second comparisons. Bitrate is a quality proxy, not VMAF/SSIM/MOS. Show stalls, quality and switching together, including negative outcomes.
