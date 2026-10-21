> Publication note: the original prepared workstation and archived raw sessions described below are historical. A fresh clone starts with empty session history and regenerated media. See [publication notes](PUBLICATION.md) for included evidence, fresh setup and verification.

# Verified 6–8 minute professor demo (Hinglish)

Use the repaired prepared app. Do **not** run setup, re-encode media or retrain immediately before presenting. Close other playback tabs. Launch instructions and the final audit path are in STATUS.md. Test the local URL once before the viva.

## 0:00–0:45 — opening, Playback Lab

**Tab:** `◉ Playback Lab` · heading **Every segment. A smarter decision.**

**Point at:** video, policy/profile controls, requested/rendered footer, live cards.

**Say:** “StallGuard ek Computer Networks streaming lab hai. Browser actual MPEG-DASH video segments HTTP se download karta hai. Python server real response bytes ko ek shared per-session delivery budget se pace karta hai. Hum throughput, buffer, startup aur rebuffering observe karke next video quality choose karte hain. ML next-request throughput estimate karta hai; Data Science causal dataset aur honest comparison provide karti hai. Ye packet-loss ya real Wi-Fi simulator nahi hai.”

“Video generated moving calibration content hai: four actual H.264 encodings aur ek shared AAC track. Koi paid API, cloud inference ya internet video dependency nahi hai.”

## 0:45–1:50 — a controlled historical run

**Exact controls:** **Adaptation policy → Historical EWMA**; **Delivery profile → Drop & recovery**; **Seed → 500**; **Capacity scale → 1**; check **Benchmark mode**. Click **▷ Start new session**.

**Point at:** Requested/Rendered, **Effective throughput**, **Playable buffer**, **BUFFER RESERVE**, **Decision evidence**.

**Say while it runs:** “Ye measured throughput hai, configured capacity nahi. Numerator actual video response-body bytes ×8 hai, denominator full request duration hai, including first-byte latency. Isliye short request aur audio competition ki wajah se number configured rate se different ho sakta hai.”

“Profile first non-manifest media body se clock start karta hai. **12 seconds elapsed profile time par 3.5 Mbps se 0.48 Mbps drop**, **28 seconds par 3.5 Mbps recovery**. Ye video playhead se alag clock hai; stall ya user pause profile ko stop nahi karta. Seed stable/step curve ko change nahi karta; fluctuations ke liye relevant hai.”

At the drop, explain the next completed request may take longer before the chart updates. Forecast uses past transfers, so it cannot know the future drop. The buffer may absorb it; a stall is possible, not mandatory. At recovery, observation also waits for an actual completion. Do not promise an immediate graph jump.

After roughly 40 seconds click **□ Stop & save**, then **↓ Export JSON** if useful. Say: “Ye cancelled exploratory playback hai, saved evidence hai. Isko completed benchmark bolkar compare nahi karenge.” The button does not claim natural end.

## 1:50–3:00 — ML is real, same controller

**Controls:** **Adaptation policy → StallGuard ML**, keep **Drop & recovery**, seed 500, scale 1 and Benchmark mode. Click **▷ Start new session**.

**Point at:** **Next-request forecast**, its source label, and expand **Decision evidence**.

**Say:** “First five valid completed video requests tak `warmup EWMA` use hota hai. Uske baad loaded random forest locally browser mein inference karta hai; label `random forest` hota hai. 32 regression trees hain, maximum depth 6. Is rule ke andar network/API inference call nahi hai.”

“Historical aur ML mode ka controller same hai: estimate ×0.8, 80 kbps reserve, buffer low ho to lowest quality, fast downgrade aur observation-based cautious upgrade. Sirf estimator change hota hai. Repeated rule calls ko new observation nahi maana jata.”

“Requested quality upcoming request ki hai. Rendered quality abhi visible decoded media ki hai. Buffered old-quality segments pehle play ho sakte hain. Shared append-only setting ab already-buffered media ko unnecessarily replace nahi karti.”

**Reasonable alternatives:** if still warmup, let several more video requests complete; do not relabel it ML. If **Historical fallback · model unavailable or invalid** appears, say exactly that and use the recorded valid ML session below. If the network drop causes a stall, point at the recorded reason and explain uncertainty. Stop/save after ~40 seconds.

## 3:00–3:40 — real dash.js default

Click **□ Stop & save** if necessary, select **Adaptation policy → dash.js default**, keep the same profile/seed/scale, and click **▷ Start new session**. Let it run for ~20 seconds, then stop/save.

**Say:** “Ye third mode dash.js ka actual built-in ABR hai: throughput aur BOLA plus its normal auxiliary rules. Custom StallGuard rule is mode mein registered nahi hai. Isliye Decision evidence mein custom forecasts dikhna expected nahi. Same shared delivery profile aur common buffer settings apply hoti hain.”

Do not say the absence of custom decisions is a failure. Do not run three players simultaneously. Stop/save before the next part.

## 3:40–4:50 — fair comparison, not a cherry-picked win

**Tab:** `▥ Compare Sessions` · heading **Let the measurements speak.** Click **Refresh**.

Select **finished** rows from the prepared matrix with the **same profile, seed and ×1 scale**—prefer the three most recent **fluctuate · seed 502 · ×1** rows, one for each policy. Skip the cancelled live demonstration rows. The short IDs and precise prepared run results are recorded in the audit's `matrix/runs.json` and `analysis/RESULTS.md`.

**Point at:** startup, rebuffer seconds, stall count, rendered bitrate, switch count, download p95, observed duration; then the overlaid buffer plot. **↓ Comparison JSON** and **↓ Summary CSV** download the selected measurements.

**Say:** “Ye three selected runs ek illustration hain. Audit mein 27 sequential fresh-browser runs execute kiye: three policies × three profiles × three repetitions. Har bounded run ka ending rule 40-second wall clock tha; actual media-time progress separately log kiya. Mean aur sample standard deviation offline audit report mein hain. Single selected run overall superiority prove nahi karta.”

“Fair comparison ke liye entire bundle fingerprint, frozen source, model, common settings, profile aur ending rule match karne chahiye. Different policies same bundle ke different subsets download kar sakti hain; wo asset mismatch nahi hai. Warning aaye to us selection ko controlled benchmark mat bolo.”

**Current measured outcome (not a win claim):** all 27 bounded runs had zero rebuffering. Mean rendered bitrate was Historical/ML/default **1.612/0.910/2.397 Mbps on stable**, **0.800/0.555/1.207 Mbps on step**, and **0.676/0.744/0.612 Mbps on fluctuations**. The aggregate report includes sample SD and n=3 per cell. Forest same-row MAE was **0.463 Mbps vs EWMA 0.353 Mbps**; RMSE was **0.622 vs 0.663 Mbps**. All **179 actual runtime forest forecasts** matched sklearn numerically.

**Hinglish:** “Sab runs stall-free the, isliye yahan ML stall reduction prove nahi hota. Stable aur step par default ne higher bitrate diya; fluctuations par ML ka bitrate higher tha. Forest ka MAE phir bhi EWMA se worse hai. Quality, switching aur error metrics ko saath dekhna zaroori hai—ek chosen run ko overall win nahi bolenge.”

**Fallback:** if the comparison view is unavailable, open the saved `analysis/RESULTS.md`, `aggregate.csv` and `comparison.png` in a file viewer. Those are evidence files, not invented app tabs. If only a partial/cancelled session exists, show its warning and raw export, then use a prepared finished run.

## 4:50–6:00 — trace one recorded segment, How It Works

**Tab:** `⌘ How It Works` · heading **From bytes to better decisions.** Point at **Observe. Forecast. Adapt. Repeat.** and the CN/ML/DS cards. Expand **Model & training provenance** if asked.

**Real frozen audit session:** `ddd7669b9af348b5aa649f333cce8d0e` (ML / step / seed 500). Open its saved JSON, or `analysis/real-segment-trace.json` alongside this tab.

1. Previous `chunk-0-00005.m4s` covered media 8–10 s at 240p. It delivered **77,708 bytes** from browser time **1.3398 to 1.5208 s**: `8 × 77708 / 0.181 = 3.434608 Mbps`.
2. At **1.5244 s**, decision **`0:5`** used the five completed video observations, last duration 0.181 s, idle gap 0.0046 s and last size 77,708 bytes. The actual forest predicted **3.385364 Mbps**. Its model checksum is recorded; future profile/capacity was not a feature.
3. The common rule selected representation **1 / 360p / 600 kbps**. Although the throughput budget permits more, the cautious upgrade step moves at most one level from the previous 240p selection after the required observation boundaries.
4. Target **`chunk-1-00006.m4s`**, media 10–12 s, began at **1.5481 s**, after the forecast. It completed at **1.8490 s**, delivering **143,059 bytes in 0.3009 s**, or **3.803496 Mbps**. That target outcome was unavailable at decision time. Short request throughput can exceed nominal capacity because bounded token credit carries across nearby requests; configured capacity is not the prediction label.
5. A separate native rendered-quality event recorded representation 1 at **wall-relative 11.0959 s**, **media time 10.237483 s**. The request completed much earlier because its segment was buffered. No subtraction of browser and server absolute clocks is involved.

**Hinglish:** “Pehle actual response measure hua. Uske baad forecast bana. Next request us forecast ke baad start hua. Uska actual result later aaya; aur render aur bhi later hua. Ye future data ko input banane wala circular graph nahi hai.”

**Say:** “Previous request ka measured outcome feature history mein available tha. Forecast ka timestamp next target request start se pehle hai. Target ka future throughput, profile name, seed ya future capacity model features mein nahi gaya. Request complete hone ke baad prediction error score kiya. Actual rendered transition alag event se logged hai. Ye request → observation → forecast → next request → render causal chain hai.”

## 6:00–7:15 — explain contribution and limitations

**CN:** genuine DASH/HTTP request lifecycle, one shared asynchronous media-payload budget, capacity transitions during responses, audio/video concurrency, init/range/retry/cancellation accounting, buffer and stall observation. Localhost exercises these mechanisms on a real browser/server connection; it does not demonstrate real WAN congestion behavior.

**ML:** supervised regression of **next completed video request effective throughput**, using only completed past transfers. Small frozen local forest, warmup/fallback, float32-compatible browser interpretation. The model was not retrained for a better-looking demo.

**DS:** raw events separate from derived summaries; session-level splits; identities and source hashes; same-profile sequential comparisons; actual sample counts, MAE/RMSE, quality/stall tradeoff and variability. Historical evaluated bytes are no longer available; those old results are preserved with that limitation. New comparisons use the current frozen bundle throughout.

**Say:** “Humne dash.js ko invent nahi kiya. Contribution integrated, explainable and reproducible networking experiment hai: byte pacing + causal measurements + local prediction + common controller + fair comparison and export. ML ka win guarantee nahi hai. Older held-out result mein forest MAE 0.400 Mbps tha aur EWMA 0.325 Mbps, although forest RMSE lower tha. Request size/timing distribution, abrupt changes aur small training set possible reasons hain; experiment un causes ko isolate nahi karta.”

“Application pacing wireless interference, packet loss, router queues, RTT dynamics ya TCP congestion-control modification simulate nahi karti. Encoded bitrate quality proxy hai, VMAF/MOS nahi. Three repetitions bhi broad Internet claim ke liye insufficient hain.”

## Optional 7:15–8:00 — full completion and recovery proof

Show the prepared `release-check/full/runs.json` evidence: final-build run `c1fe3f44aacf418bbb5f86f15c61dbc6` waited for native **ended**, with a 180-second safety timeout. It reached 120 seconds, decoded **2,880 frames**, had zero stalls and 60 video requests. A wall timer of 120 seconds alone would not prove this. `full/runs.json` separately preserves the earlier frozen-comparison implementation's full-clip proof.

Refresh behavior: a normal refresh sends pending telemetry and makes the interrupted session **partial**, not silently finished. Missing/incompatible models visibly fall back. Abrupt kills can still lose the pending tail; no crash-proof-storage claim.

If asked to demonstrate natural completion live, start **StallGuard ML / Stable capacity** and let it end normally while answering questions. Do not seek to the end and call that full playback. This extends the talk unless started earlier; the recorded proof keeps the main walkthrough within 6–8 minutes.
