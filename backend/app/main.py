import json
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from .config import ROOT, MEDIA, MODELS, SESSIONS, SCHEMA
from .schemas import SessionCreate, Batch, Finish
from .profiles import PROFILES
from . import sessions
from .media import serve
from . import model as model_files

app=FastAPI(title='StallGuard',version='1.0.0')

def model():
    try:return model_files.read_model()
    except (OSError,ValueError,KeyError,TypeError) as e:raise HTTPException(404,f'Model unavailable/incompatible; historical fallback: {e}')

@app.get('/api/health')
def health(): return {'backend':'ready','schema':SCHEMA,'media_ready':(MEDIA/'stream.mpd').exists(),'model_ready':model_files.status()['ready'],'dashjs':'5.0.3','source_identity':sessions.SOURCE_ID}

@app.get('/api/assets')
def assets():
    p=MEDIA/'inventory.json'
    return json.loads(p.read_text()) if p.exists() else {'representations':[]}

@app.get('/api/profiles')
def profiles(): return PROFILES

@app.post('/api/sessions')
def create(config:SessionCreate):
    if not (MEDIA/'stream.mpd').exists(): raise HTTPException(409,'Prepare media first')
    return sessions.create(config)

@app.get('/api/sessions')
def listing(): return [sessions.get(p.parent.name) for p in sorted(SESSIONS.glob('*/meta.json'),key=lambda p:p.stat().st_mtime,reverse=True)]

@app.get('/api/sessions/{sid}')
def detail(sid:str): return sessions.get(sid)

@app.post('/api/sessions/{sid}/telemetry')
def telemetry(sid:str,batch:Batch):
    rows=[e.model_dump(exclude_none=True) for e in batch.events]
    return {'accepted':sessions.ingest(sid,rows)}

@app.post('/api/sessions/{sid}/abandon')
def abandon(sid:str,batch:Batch):return sessions.abandon(sid,[e.model_dump(exclude_none=True) for e in batch.events])

@app.post('/api/sessions/{sid}/finish')
def finish(sid:str,body:Finish): return sessions.finish(sid,body.status)

@app.get('/api/sessions/{sid}/export')
def export(sid:str):
    return {'schema':SCHEMA,'meta':sessions.get(sid),'events':sessions.load(sid,'events'),'delivery':sessions.load(sid,'delivery')}

@app.get('/api/models/status')
def model_status():
    return model_files.status()

@app.get('/api/models/current')
def current(): return model()

@app.get('/media/{sid}/{asset:path}')
async def media(sid:str,asset:str,request:Request): return await serve(sid,asset,request)

if (ROOT/'frontend/dist').exists():
    app.mount('/assets',StaticFiles(directory=ROOT/'frontend/dist/assets'),name='assets')
    @app.get('/')
    def index(): return FileResponse(ROOT/'frontend/dist/index.html',headers={'Cache-Control':'no-store'})
