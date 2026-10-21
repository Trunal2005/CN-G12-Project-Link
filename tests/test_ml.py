from ml.features import rows,features

def test_causal_target_alignment_and_session_isolation():
    def event(i):return {'kind':'segment','t':i*2+1,'start':i*2,'throughput':(i+1)*100000,'duration':1,'size':12500}
    events=[event(i) for i in range(8)]
    a=rows(events);assert len(a)==3
    assert a[0]['x'][:5]==[100000,200000,300000,400000,500000]
    assert a[0]['y']==600000
    assert all(r['history_end']<=r['target_start'] for r in a)
    assert rows(events[:4])==[]
    # A fresh session never borrows previous-session windows.
    assert rows(events[4:])==[]

def test_actual_browser_feature_vectors_match_python():
    import json
    from pathlib import Path
    import pytest
    root=Path(__file__).resolve().parents[1]
    runs=json.loads((root/'data/results/collect-runs.json').read_text())
    count=0
    for run in runs:
        events=json.loads((root/'data/results'/f"{run['id']}.json").read_text())['events']
        expected={r['boundary']:r for r in rows(events)}
        for e in events:
            if e['kind']=='decision' and e.get('features') is not None and e['boundary'] in expected:
                assert e['features']==pytest.approx(expected[e['boundary']]['x'],rel=1e-10,abs=1e-7)
                count+=1
    assert count>20
