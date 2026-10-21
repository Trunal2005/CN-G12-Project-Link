import asyncio,json,hashlib
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app import sessions,identity,model
from backend.app.summary import summarize

@pytest.fixture(autouse=True)
def isolated(tmp_path,monkeypatch):
    monkeypatch.setattr(sessions,'SESSIONS',tmp_path/'sessions');monkeypatch.setattr(sessions,'active',{})

def test_idempotent_telemetry_and_closed_session_immutable():
    c=TestClient(app);sid=c.post('/api/sessions',json={}).json()['id']
    batch={'events':[{'kind':'intent','t':0,'seq':0},{'kind':'playing','t':1,'seq':1},{'kind':'sample','t':2,'seq':2,'value':1}]}
    assert c.post(f'/api/sessions/{sid}/telemetry',json=batch).json()['accepted']==3
    assert c.post(f'/api/sessions/{sid}/telemetry',json=batch).json()['accepted']==0
    assert c.post(f'/api/sessions/{sid}/telemetry',json={'events':[{'kind':'sample','t':3,'seq':4}]}).status_code==409
    a=c.post(f'/api/sessions/{sid}/finish',json={'status':'finished'}).json()
    before=(sessions.path_for(sid)/'events.jsonl').read_bytes()
    assert c.post(f'/api/sessions/{sid}/telemetry',json=batch).status_code==409
    assert c.post(f'/api/sessions/{sid}/finish',json={'status':'cancelled'}).json()==a
    assert (sessions.path_for(sid)/'events.jsonl').read_bytes()==before

def test_final_progress_and_render_boundary_weighting():
    events=[{'kind':'rendered','t':0,'media_time':0,'value':300000,'representation':'0'},
      {'kind':'sample','t':0,'value':0},{'kind':'rendered','t':.5,'media_time':.5,'value':600000,'representation':'1'},
      {'kind':'rendered','t':.6,'media_time':.6,'value':600000,'representation':'1'},
      {'kind':'sample','t':1,'value':1},{'kind':'sample','t':1.5,'value':1.5},{'kind':'close','t':1.5}]
    s=summarize(events,[])
    assert s['rendered_bitrate_bps']==500000 and s['quality_weighted_media_s']==1.5
    assert s['quality_initial_assignments']==1 and s['quality_switches']==1 and s['rendered_callbacks']==3
    assert s['played_seconds']==1.5 and not s['natural_end']

def test_epoch_and_late_prediction_alignment():
    e=[{'kind':'decision','t':0,'decision_id':'0:0','epoch':0,'boundary':0,'value':100,'predictor':'random forest'},
       {'kind':'segment','t':2,'epoch':0,'boundary':0,'decision_id':'0:0','start':1,'throughput':120,'duration':1},
       {'kind':'decision','t':3,'decision_id':'1:0','epoch':1,'boundary':0,'value':200,'predictor':'random forest'},
       {'kind':'segment','t':5,'epoch':1,'boundary':0,'decision_id':'1:0','start':4,'throughput':180,'duration':1},
       {'kind':'segment','t':6,'epoch':1,'boundary':0,'decision_id':'1:0','start':2,'throughput':900,'duration':1}]
    s=summarize(e,[]);assert s['prediction_count']==2 and s['forest_prediction_count']==2 and s['forest_mae_bps']==20

def test_whole_bundle_fingerprint_not_request_subset_or_mtime(tmp_path,monkeypatch):
    m=tmp_path/'media';m.mkdir();monkeypatch.setattr(identity,'MEDIA',m)
    inv={'segments':[{'asset':'chunk-0-00001.m4s'},{'asset':'chunk-1-00001.m4s'}],'representations':[{'id':'0'},{'id':'1'}]}
    (m/'inventory.json').write_text(json.dumps(inv))
    for name in ['stream.mpd','init-0.mp4','init-1.mp4','chunk-0-00001.m4s','chunk-1-00001.m4s']:(m/name).write_bytes(name.encode())
    a=identity.fingerprint(1);assert identity.fingerprint(2)==a
    (m/'chunk-0-00001.m4s').read_bytes();assert identity.fingerprint(1)==a
    (m/'chunk-1-00001.m4s').write_bytes(b'changed body, same inventory mtime');assert identity.fingerprint(1)!=a
    b=identity.fingerprint();(m/'stream.mpd').write_text('changed MPD');assert identity.fingerprint()!=b

def test_invalid_model_readiness_without_touching_frozen_model(tmp_path,monkeypatch):
    monkeypatch.setattr(model,'MODELS',tmp_path);c=TestClient(app)
    assert not c.get('/api/models/status').json()['ready']
    (tmp_path/'forest.json').write_text('{bad')
    assert not c.get('/api/health').json()['model_ready'] and c.get('/api/models/current').status_code==404
    (tmp_path/'forest.json').write_text(json.dumps({'schema':'wrong','feature_names':[]}));assert not c.get('/api/models/status').json()['ready']

def test_partial_abandon_closes_without_late_events():
    c=TestClient(app);sid=c.post('/api/sessions',json={}).json()['id']
    r=c.post(f'/api/sessions/{sid}/abandon',json={'events':[{'kind':'intent','t':0,'seq':0},{'kind':'close','t':1,'seq':1}]})
    assert r.status_code==200 and c.get(f'/api/sessions/{sid}').json()['status']=='partial'
    assert c.post(f'/api/sessions/{sid}/telemetry',json={'events':[]}).status_code==409

def test_requested_initial_assignment_comes_from_actual_media_requests():
    # dash.js quality-change callbacks omit initial rep 0. Two later transitions
    # must not be undercounted as one by treating the first callback as initial.
    events=[{'kind':'request','t':0,'stream_type':'video','request_type':'MediaSegment','representation':'0'},
      {'kind':'requested','t':1,'representation':'1','value':600000},
      {'kind':'request','t':1.1,'stream_type':'video','request_type':'MediaSegment','representation':'1'},
      {'kind':'requested','t':2,'representation':'2','value':1200000},
      {'kind':'request','t':2.1,'stream_type':'video','request_type':'MediaSegment','representation':'2'}]
    s=summarize(events,[])
    assert s['requested_initial_assignments']==1
    assert s['requested_quality_switches']==2
