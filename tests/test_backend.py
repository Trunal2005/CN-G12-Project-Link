import asyncio
import json
import math
import time
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app import sessions
from backend.app.profiles import capacity
from backend.app.limiter import Limiter
from backend.app.summary import summarize

client=TestClient(app)

@pytest.fixture(autouse=True)
def isolate_test_sessions(tmp_path,monkeypatch):
    # Hand-constructed unit timelines must never enter the live comparison UI.
    monkeypatch.setattr(sessions,'SESSIONS',tmp_path)
    monkeypatch.setattr(sessions,'active',{})

def new(): return client.post('/api/sessions',json={}).json()['id']

def test_profile_determinism_and_bounds():
    assert capacity('fluctuate',4,1,10)==capacity('fluctuate',4,1,10)
    assert capacity('fluctuate',4,1,10)!=capacity('fluctuate',5,1,10)
    for t in range(200): assert 100000<=capacity('fluctuate',100,3,t)<=20000000
    assert capacity('step',1,1,13)<capacity('step',1,1,1)
    assert capacity('step',1,1,29)>capacity('step',1,1,13)
    for body in [{'scale':0},{'scale':float('inf')},{'seed':-1},{'profile':'outside'}]:
        if math.isinf(body.get('scale',0)): continue
        assert client.post('/api/sessions',json=body).status_code==422

def test_safe_assets_range_and_reset():
    sid=new(); other=new()
    assert sessions.active[sid]['limiter'].start is None
    assert client.get(f'/media/{sid}/stream.mpd').headers['content-type'].startswith('application/dash+xml')
    assert sessions.active[sid]['limiter'].start is None
    assert client.get(f'/media/{sid}/missing.m4s').status_code==404
    assert client.get(f'/media/{sid}/inventory.json').status_code==404
    assert client.get('/media/bad/stream.mpd').status_code==404
    assert client.get(f'/media/{sid}/%2e%2e%2frequirements.txt').status_code==404
    full=client.get(f'/media/{sid}/init-0.mp4')
    r=client.get(f'/media/{sid}/init-0.mp4',headers={'Range':'bytes=0-9'})
    assert r.status_code==206 and r.content==full.content[:10] and r.headers['content-range'].startswith('bytes 0-9/')
    assert client.get(f'/media/{sid}/init-0.mp4',headers={'Range':'bytes=-10'}).content==full.content[-10:]
    assert client.get(f'/media/{sid}/init-0.mp4',headers={'Range':'bytes=999999-'}).status_code==416
    assert sessions.active[sid]['limiter'].start is not None
    assert sessions.active[other]['limiter'].start is None
    client.post(f'/api/sessions/{sid}/finish',json={'status':'cancelled'})
    client.post(f'/api/sessions/{other}/finish',json={'status':'cancelled'})

def test_telemetry_validation_persistence_finalization():
    sid=new()
    assert client.post(f'/api/sessions/{sid}/telemetry',json={'events':[{'kind':'sample','t':-1}]}).status_code==422
    assert client.post(f'/api/sessions/{sid}/telemetry',json={'events':[{'kind':'sample','t':0,'unknown':4}]}).status_code==422
    assert client.post(f'/api/sessions/{sid}/telemetry',json={'events':[{'kind':'sample','t':0}]*501}).status_code==422
    assert client.post(f'/api/sessions/{sid}/telemetry',json={'events':[{'kind':'intent','t':0},{'kind':'playing','t':2}]}).json()['accepted']==2
    data=client.post(f'/api/sessions/{sid}/finish',json={'status':'finished'}).json()
    assert data['summary']['startup_s']==2
    assert len(client.get(f'/api/sessions/{sid}/export').json()['events'])==2
    assert client.post(f'/api/sessions/{sid}/telemetry',json={'events':[]}).status_code==409
    sid=new();del sessions.active[sid]
    assert client.get(f'/api/sessions/{sid}').json()['status']=='partial'

def test_stall_state_machine_hand_timeline():
    def e(k,t,**kw):return dict(kind=k,t=t,**kw)
    events=[e('intent',0),e('waiting',1),e('playing',3),e('waiting',5,buffer=0),e('waiting',6,buffer=0),e('playing',8),e('pause',9),e('waiting',10),e('playing',12),e('seeking',13),e('waiting',14),e('playing',15),e('waiting',16,buffer=2),e('ended',20)]
    s=summarize(events,[])
    assert s['startup_s']==3 and s['rebuffer_s']==3 and s['stall_count']==1
    assert s['rebuffer_ratio']==pytest.approx(3/12) # deliberate pause/seek excluded from eligible denominator

def test_quality_weighting_switch_count_and_latency_percentile():
    events=[{'kind':'rendered','t':0,'value':300000},
            {'kind':'sample','t':0,'value':0},{'kind':'sample','t':1,'value':1},
            {'kind':'rendered','t':1,'value':600000},
            {'kind':'sample','t':2,'value':2},{'kind':'sample','t':3,'value':3},
            {'kind':'rendered','t':3.5,'value':300000}]
    for i in range(1,21):events.append({'kind':'segment','t':i+4,'duration':i,'start':i+3,'throughput':100})
    s=summarize(events,[])
    assert s['rendered_bitrate_bps']==500000
    assert s['quality_switches']==2 and s['switch_magnitude_bps']==600000
    assert s['download_p95_s']==19 # nearest rank ceil(.95 * 20)

def test_limiter_cancellation_and_control_responsiveness():
    async def run():
        l=Limiter('stable',1,.2)
        await l.lock.acquire() # Deterministically queue; a 2 KiB live grant can
        # finish before two Windows timer sleeps, which made the old test flaky.
        job=asyncio.create_task(l.grant(2048));await asyncio.sleep(.001)
        begin=time.monotonic();await asyncio.sleep(.001);assert time.monotonic()-begin<.1
        job.cancel()
        with pytest.raises(asyncio.CancelledError):await job
        l.lock.release()
        await asyncio.wait_for(l.grant(2048),1)
        assert not l.lock.locked()
    asyncio.run(run())

def test_real_media_inventory():
    from backend.app.config import MEDIA
    inv=json.loads((MEDIA/'inventory.json').read_text())
    v=[r for r in inv['representations'] if r['type']=='video']
    assert {(r['width'],r['height']) for r in v}=={(426,240),(640,360),(854,480),(1280,720)}
    ts=[[(s['start'],s['duration']) for s in inv['segments'] if s['representation']==r['id']] for r in v]
    assert all(t==ts[0] for t in ts)
    for s in inv['segments']: assert (MEDIA/s['asset']).stat().st_size==s['bytes']
