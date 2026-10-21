import importlib.metadata
import json
import shutil
import socket
import subprocess
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.prepare_media import binary

def main():
    checks=[]
    def check(name,fn,required=True):
        try:value=fn();checks.append({'name':name,'ok':True,'value':value})
        except Exception as e:checks.append({'name':name,'ok':False,'required':required,'error':str(e)})
    check('Python',lambda:sys.version)
    for package in ['fastapi','uvicorn','numpy','pandas','scikit-learn','joblib','pytest','playwright']:
        check(package,lambda p=package:importlib.metadata.version(p))
    for exe in ['node','npm']:
        check(exe,lambda e=exe:subprocess.check_output([shutil.which(e) or e,'--version'],text=True).strip())
    for exe in ['ffmpeg','ffprobe']:
        check(exe,lambda e=exe:subprocess.check_output([binary(e),'-version'],text=True).splitlines()[0])
    def encoders():
        result=subprocess.check_output([binary('ffmpeg'),'-hide_banner','-encoders'],text=True)
        assert 'libx264' in result and 'aac' in result
        return 'libx264 and AAC available'
    check('Encoders',encoders)
    def media():
        inv=json.loads((ROOT/'media/inventory.json').read_text())
        assert (ROOT/'media/stream.mpd').exists()
        assert len([r for r in inv['representations'] if r['type']=='video'])==4
        assert all((ROOT/'media'/s['asset']).stat().st_size==s['bytes'] for s in inv['segments'])
        return f"{len(inv['segments'])} verified media segments"
    check('Prepared media',media)
    def model():
        m=json.loads((ROOT/'data/models/forest.json').read_text());assert m['schema']=='forest-v1';return {'trees':len(m['trees']),'checksum':m['checksum']}
    check('Trained model',model,False)
    check('Frontend build',lambda: 'ready' if (ROOT/'frontend/dist/index.html').exists() else (_ for _ in ()).throw(RuntimeError('npm --prefix frontend run build')))
    def port():
        with socket.socket() as s:s.bind(('127.0.0.1',8000))
        return '8000 available'
    check('Port',port,False)
    check('Chrome',lambda:next(str(p) for p in [Path('C:/Program Files/Google/Chrome/Application/chrome.exe'),Path('/usr/bin/google-chrome'),Path('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')] if p.exists()),False)
    print(json.dumps(checks,indent=2));return int(any(not c['ok'] and c.get('required',True) for c in checks))
if __name__=='__main__':raise SystemExit(main())
