import json
import time
import uuid
import hashlib
import threading
from fastapi import HTTPException
from .config import SESSIONS, SCHEMA, MODELS, MEDIA,CONTROLLER_VERSION
from .identity import fingerprint,source_identity
from .limiter import Limiter
from .summary import summarize
from . import model as model_files

active = {}
SOURCE_ID=source_identity()

def write(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False), encoding='utf-8')

def create(config):
    if len(active) >= 32: raise HTTPException(429, 'Too many active sessions; finish old sessions first')
    sid = uuid.uuid4().hex
    path = SESSIONS / sid; path.mkdir(parents=True)
    meta = {'id':sid,'schema':SCHEMA,'status':'created','created_unix':time.time(), **config.model_dump()}
    meta['asset_fingerprint']=fingerprint((MEDIA/'inventory.json').stat().st_mtime_ns)
    meta['source_identity']=SOURCE_ID
    meta['controller_version']=CONTROLLER_VERSION
    model_status=model_files.status()
    meta['model_checksum']=model_status.get('checksum') if model_status['ready'] else None
    meta['model_file_sha256']=hashlib.sha256((MODELS/'forest.json').read_bytes()).hexdigest() if (MODELS/'forest.json').exists() else None
    write(path/'meta.json',meta)
    active[sid] = {'meta':meta,'limiter':Limiter(config.profile,config.seed,config.scale),'lock':threading.RLock(),'closed':False,'last_seq':-1,'client_gone':False}
    return meta

def path_for(sid):
    if len(sid)!=32 or any(c not in '0123456789abcdef' for c in sid): raise HTTPException(404,'Unknown session')
    path = SESSIONS/sid
    if not (path/'meta.json').is_file(): raise HTTPException(404,'Unknown session')
    return path

def get(sid):
    path = path_for(sid)
    meta = dict(active[sid]['meta']) if sid in active else json.loads((path/'meta.json').read_text())
    if sid not in active and meta['status'] in ('created','starting','playing'): meta['status']='partial'
    if (path/'summary.json').exists(): meta['summary']=json.loads((path/'summary.json').read_text())
    return meta

def append(sid, name, rows):
    with (path_for(sid)/f'{name}.jsonl').open('a',encoding='utf-8') as f:
        for row in rows: f.write(json.dumps(row,allow_nan=False)+'\n')

def load(sid,name):
    p=path_for(sid)/f'{name}.jsonl'
    return [json.loads(line) for line in p.read_text().splitlines()] if p.exists() else []

def ingest(sid,rows):
    state=active.get(sid)
    if not state:path_for(sid);raise HTTPException(409,'Session is closed')
    with state['lock']:
        if state['closed']:raise HTTPException(409,'Session is closed')
        file=path_for(sid)/'events.jsonl'
        if file.exists() and file.stat().st_size>32_000_000:raise HTTPException(413,'Event retention limit')
        accepted=[];last=state['last_seq']
        for row in rows:
            seq=row.get('seq')
            if seq is not None:
                if seq<=last:continue # Safe retry of an acknowledged/lost-ack batch.
                if seq!=last+1:raise HTTPException(409,'Missing telemetry sequence; retry pending batch')
                last=seq
            accepted.append(row)
        append(sid,'events',accepted);state['last_seq']=last
        if any(e['kind']=='playing' for e in accepted):state['meta']['status']='playing'
        for e in accepted:
            if e['kind']=='configuration':
                settings=e.get('settings',{})
                state['meta']['settings_identity']=hashlib.sha256(json.dumps(settings,sort_keys=True).encode()).hexdigest()
                common={k:v for k,v in settings.items() if k!='abr'}
                state['meta']['common_settings_identity']=hashlib.sha256(json.dumps(common,sort_keys=True).encode()).hexdigest()
                state['meta']['loaded_model_checksum']=e.get('model_checksum')
        return len(accepted)

def finish(sid,status):
    state=active.get(sid)
    if not state: return get(sid)
    with state['lock']:
        if state['closed']:return get(sid)
        if state['limiter'].active: raise HTTPException(409,'Media transfers still draining; retry finish')
        state['closed']=True
        meta=state['meta']; meta['status']=status
        write(path_for(sid)/'summary.json',summarize(load(sid,'events'),load(sid,'delivery')))
        write(path_for(sid)/'meta.json',meta)
        active.pop(sid,None)
    return get(sid)

def abandon(sid,rows):
    state=active.get(sid)
    if not state:return get(sid)
    ingest(sid,rows)
    with state['lock']:state['client_gone']=True
    if not state['limiter'].active:return finish(sid,'partial')
    return {'status':'draining'}
