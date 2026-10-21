# A repeatable 3–5 minute demonstration

> This is the original shorter outline. For the verified repaired interface and current audit evidence, follow [PROFESSOR_DEMO.md](PROFESSOR_DEMO.md) (6–8 minute Hinglish) and [PAGE_MAP.md](PAGE_MAP.md).

1. Run `python scripts/run.py`, open http://127.0.0.1:8000, and show media/model readiness. Explain that the clip is generated calibration content.
2. Select Historical EWMA and Drop & recovery, seed 42, scale 1. Enable benchmark mode. Start. Watch requested and rendered quality differ, because buffered segments may render later. At 12 seconds capacity drops; at 28 it recovers. Let the run finish or stop/save after ~40 seconds.
3. Select StallGuard ML and repeat the same profile/seed/scale in a fresh run. The first five completed video requests warm up the model. Expand decision evidence; show the predictor switching from warmup EWMA to random forest and explain the history boundary/reason. A model forecast may be wrong.
4. Open Compare Sessions. Select two compatible completed runs from the experiment runner, or two full-length interactive runs. Show startup, stalls and rendered bitrate together. Export JSON or CSV. Avoid claiming that one visibly smoother run proves general superiority.
5. Open How It Works. Describe a two-second segment traveling from HTTP response to the playback buffer. Show the 3D stack follows measured seconds, rather than being a fake animation. Explain that emulation paces application bytes, not radio/packet loss.

For the strongest repeatability, use saved runner results and their exact ending rules. Interactive Stop produces a cancelled run, excluded from the completed-session comparison. Let interactive videos end naturally when you want comparable finished runs. The runner explicitly finalizes bounded experiments as finished and records their wall-clock ending rule.
