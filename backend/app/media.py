import re
import time
import uuid
from fastapi import HTTPException, Request
from fastapi.responses import Response, StreamingResponse
from .config import MEDIA
from . import sessions
from .identity import bundle_assets

async def serve(sid, asset, request: Request):
    sessions.path_for(sid)
    if not re.fullmatch(r'[A-Za-z0-9_.-]+',asset) or asset.startswith('.'): raise HTTPException(404,'Unknown media asset')
    path=MEDIA/asset
    if not path.is_file() or asset not in bundle_assets(): raise HTTPException(404,'Unknown media asset')
    headers={'Cache-Control':'no-store','Accept-Ranges':'bytes','Timing-Allow-Origin':'*'}
    if path.suffix=='.mpd': return Response(path.read_bytes(),media_type='application/dash+xml',headers=headers)
    state=sessions.active.get(sid)
    if state is None: raise HTTPException(409,'Session no longer active')
    limiter=state['limiter']
    size=path.stat().st_size; start,end=0,size-1; code=200
    if request.headers.get('range'):
        match=re.fullmatch(r'bytes=(\d*)-(\d*)',request.headers['range'])
        if not match or not any(match.groups()): return Response(status_code=416,headers={'Content-Range':f'bytes */{size}'})
        a,b=match.groups()
        if not a: start=max(0,size-int(b))
        else: start=int(a); end=min(end,int(b)) if b else end
        if start>end or start>=size: return Response(status_code=416,headers={'Content-Range':f'bytes */{size}'})
        code=206; headers['Content-Range']=f'bytes {start}-{end}/{size}'
    headers['Content-Length']=str(end-start+1)
    rid=uuid.uuid4().hex; headers['X-Request-ID']=rid
    with state['lock']:
        if state['closed'] or state['client_gone']:raise HTTPException(409,'Session no longer active')
        if limiter.active>=12:raise HTTPException(429,'Too many media transfers')
        limiter.active+=1 # Reserve before yielding response headers, not later.
    begun=time.monotonic();sent=0;status='aborted'
    async def body():
        nonlocal begun,sent,status
        begun=time.monotonic()
        if limiter.start is None:
            limiter.start=begun
            sessions.append(sid,'profile',[{'event':'start','rule':'first non-manifest media body','server_monotonic':begun}])
            state['meta']['status']='starting'
        try:
            with path.open('rb') as f:
                f.seek(start); remaining=end-start+1
                while remaining:
                    if await request.is_disconnected(): return
                    chunk=f.read(min(2048,remaining))
                    await limiter.grant(len(chunk))
                    sent+=len(chunk); remaining-=len(chunk)
                    yield chunk
            status='complete'
        finally:pass
    class PacedResponse(StreamingResponse):
        async def __call__(self,scope,receive,send):
            try:await super().__call__(scope,receive,send)
            finally:
                with state['lock']:
                    sessions.append(sid,'delivery',[{'request_id':rid,'asset':asset,'bytes':sent,'status':status,'range':[start,end],'start_s':begun-(limiter.start or begun),'duration_s':time.monotonic()-begun}])
                    limiter.active-=1
                    if state['client_gone'] and limiter.active==0:sessions.finish(sid,'partial')
    return PacedResponse(body(),status_code=code,media_type='audio/mp4' if asset.startswith('chunk-4-') or asset=='init-4.mp4' else 'video/mp4',headers=headers)
