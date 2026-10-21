# Beginner-friendly viva notes

**What is a segment?** A short encoded piece of the video. Here it covers about two seconds. Different representations show the same time at different resolutions and bitrates.

**What is an MPD?** The DASH manifest. It tells the player which tracks, representations, timelines, and segment URLs exist. It contains instructions and metadata, not the video itself.

**Bitrate vs throughput?** Bitrate is how many bits per second of video were encoded. Throughput is how fast a particular HTTP request actually delivered bytes. A 1.2 Mbps video cannot remain sustainable if delivery stays below its combined video/audio need.

**Where are HTTP and TCP?** The browser asks FastAPI for fragments over local HTTP. TCP carries them reliably. StallGuard delays application response bytes; it does not change TCP's congestion-control algorithm or simulate a real wireless network.

**Why have a buffer?** Downloaded media can play while a later segment is being fetched. Playable buffer seconds measure how long the player can continue without more data. Startup is the first wait before playback; rebuffering is a later empty-buffer wait. A manual pause is not a network stall.

**What is ABR?** Adaptive bitrate selection chooses the representation for upcoming video requests. Lower quality can download faster and reduce risk; higher quality spends more bandwidth. Buffer, throughput and cautious upgrade rules balance those choices.

**One segment's lifecycle:** Read its URL from the MPD → ask the session media endpoint → server grants small paced chunks → browser completes the request → append compressed samples to Media Source → browser decodes and renders frames. Requested quality and rendered quality can differ because earlier segments are still buffered.

**One forecast's lifecycle:** A video request completes → record exact body bytes and elapsed request time → after five observations form 11 causal features → evaluate 32 regression trees locally → average their leaf estimates → apply the same buffer-aware controller as EWMA → return a valid Representation to dash.js → link the decision boundary to the next actual request. If the forecast happened after that request started, it is not scored as a valid prediction for it.

**What is regression?** Predicting a numeric value, here next-request effective throughput in bps. A forest averages several decision trees. It learns from actual local transfer outcomes, not from the known future profile.

**What is leakage?** Accidentally supplying future data to the predictor or using related windows in both training and testing. This project splits whole sessions, keeps traces distinct, uses only completed past requests, and reserves an unfamiliar transition for final tests. A model that reads future configured capacity would be cheating.

**Why compare with EWMA?** Recent throughput is a strong simple baseline. Both custom modes share exactly the same controller; only the predictor changes. The third policy is the real dash.js default. A forecast counterfactual test proves wiring, not performance superiority.

**What would make the evidence stronger?** Longer clips, repeated independent runs, unfamiliar real measured traces, more hardware/browser environments, well-designed policy tuning on validation only, and perceptual metrics if actually computed. A small local dataset and one repetition cannot justify broad claims.
