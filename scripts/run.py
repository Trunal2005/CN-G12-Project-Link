"""Single managed local app. Ctrl+C lets Uvicorn shut down cleanly."""
import argparse
import socket
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=8000);a=p.parse_args()
    for required in ['media/stream.mpd','media/inventory.json','frontend/dist/index.html']:
        if not (ROOT/required).is_file():raise SystemExit(f'Missing {required}. See README preparation commands.')
    if not (ROOT/'data/models/forest.json').exists():print('Model missing: historical fallback will be shown.')
    try:
        with socket.socket() as sock:sock.bind(('127.0.0.1',a.port))
    except OSError:raise SystemExit(f'Port {a.port} unavailable. Stop the existing server or choose --port.')
    import uvicorn
    print(f'StallGuard: http://127.0.0.1:{a.port} (Ctrl+C to stop)',flush=True)
    uvicorn.run('backend.app.main:app',host='127.0.0.1',port=a.port,log_level='warning')
