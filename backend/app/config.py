from pathlib import Path
import os
ROOT = Path(__file__).resolve().parents[2]
MEDIA = ROOT / 'media'
SESSIONS = Path(os.environ.get('STALLGUARD_SESSION_DIR',str(ROOT / 'data' / 'sessions'))).resolve()
SESSIONS.mkdir(parents=True,exist_ok=True)
MODELS = ROOT / 'data' / 'models'
SCHEMA = 'stallguard-v1'
CONTROLLER_VERSION = 'shared-buffer-v2-append-only'
