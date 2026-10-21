"""Record source/media/model identities and verify preserved baseline artifacts."""
import argparse,hashlib,json,sys,datetime,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.app.identity import source_identity,fingerprint
def main(out):
    out=Path(out).resolve();baseline=json.loads((out/'baseline-hashes.json').read_text());protected={k:v for k,v in baseline.items() if k.replace('\\','/').startswith(('media/','data/models/','data/sessions/','data/results/'))}
    changed=[name for name,h in protected.items() if not (ROOT/name).exists() or hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=h]
    appended=[]
    with zipfile.ZipFile(out/'baseline.zip') as archive:
        for name in list(changed):
            normalized=name.replace('\\','/');current=ROOT/name
            if normalized.startswith('data/sessions/') and normalized.endswith('/events.jsonl') and current.exists():
                old=archive.read(normalized);now=current.read_bytes()
                if now.startswith(old):
                    appended.append({'path':normalized,'baseline_bytes':len(old),'additional_bytes':len(now)-len(old),'reason':'Already-open paused legacy browser continued sending samples before server replacement'})
                    (out/'legacy-appended-events.jsonl').write_bytes(now[len(old):]);changed.remove(name)
    assert not changed,changed
    files={str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ['backend','frontend/src','ml','scripts','tests'] for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    report={'frozen_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_identity':source_identity(),'asset_fingerprint':fingerprint(),'model_file_sha256':hashlib.sha256((ROOT/'data/models/forest.json').read_bytes()).hexdigest(),'tree_checksum':json.loads((ROOT/'data/models/forest.json').read_text())['checksum'],'protected_original_files_checked':len(protected),'protected_original_files_changed':changed,'observed_legacy_append_only':appended,'source_hashes':files}
    target=out/'frozen.json'
    if target.exists():raise SystemExit('Freeze already exists; use a new audit directory rather than replacing evidence')
    target.write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='source_hashes'},indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);main(p.parse_args().out)
