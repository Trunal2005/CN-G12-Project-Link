import hashlib
import json
from .config import MEDIA,ROOT

def bundle_assets():
    inventory=json.loads((MEDIA/'inventory.json').read_text())
    return {'stream.mpd',*[s['asset'] for s in inventory['segments']],*[f"init-{r['id']}.mp4" for r in inventory['representations']]}

def fingerprint(inventory_mtime=None):
    """Entire permitted bundle, independent of requested subset; no mtime cache."""
    hashes={name:hashlib.sha256((MEDIA/name).read_bytes()).hexdigest() for name in sorted(bundle_assets()|{'inventory.json'})}
    return 'bundle-v2:'+hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()

def source_identity():
    files=[]
    for folder in ['backend/app','frontend/src','frontend/dist','ml']:
        files += [p for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    files += [ROOT/'requirements.txt',ROOT/'frontend/package-lock.json']
    return hashlib.sha256(json.dumps({str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)},sort_keys=True).encode()).hexdigest()
