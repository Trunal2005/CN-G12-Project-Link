# Third-party components and generated content

StallGuard uses React, dash.js, Vite, TypeScript, FastAPI, Uvicorn, NumPy, pandas, scikit-learn, joblib, Playwright, pytest, Matplotlib, imageio-ffmpeg and their dependencies. Their upstream licenses and notices remain with installed distributions; consult pinned package metadata and distribution notices. Installed package trees, encoders and browsers are not redistributed here.

Setup obtains FFprobe through `ffprobe-static@3.1.0` when needed and FFmpeg through `imageio-ffmpeg==0.6.0` unless on PATH. FFmpeg builds have build-dependent LGPL/GPL obligations; inspect `-version`, `-L` and upstream notices before redistributing binaries. This repository distributes preparation code, not executables.

Default media is generated locally using FFmpeg `testsrc2` and `sine`, with no external footage, music or paid service. Optional `--source` clips require the user's distribution rights. Generation commands and fingerprints are recorded in inventory/evidence.

The forest JSON, parity vectors and eight collection exports come from executed project experiments with synthetic local content, without an external dataset or hosted model. Provenance includes exact input hashes, features, split and estimator settings.

The destination initially contained only the title `CN-G12-Project-Link`; its initial commit remains in history. No team members, copyright ownership or project license have been invented. Publication assigns no new project license.
