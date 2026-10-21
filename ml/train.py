"""Train only from executed, independently grouped collection runs."""
import hashlib
import json
import platform
import sys
from pathlib import Path
import joblib
import numpy as np
import sklearn
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error,mean_squared_error
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from ml.features import rows,NAMES

def train(collection_dir=ROOT/'data/results'):
    collection_dir=Path(collection_dir).resolve()
    manifest=json.loads((collection_dir/'collect-runs.json').read_text())
    groups={'train':[],'validation':[]};ids={k:[] for k in groups};provenance=[]
    for run in manifest:
        if 'error' in run:continue
        split=run['purpose'];sid=run['id']
        if split not in groups:continue
        raw=(collection_dir/f'{sid}.json').read_bytes();data=json.loads(raw)
        assert data['meta']['status']=='finished'
        rs=rows(data['events']);groups[split]+=rs;ids[split].append(sid)
        provenance.append({'id':sid,'split':split,'profile':run['profile'],'seed':run['seed'],'scale':run['scale'],'policy':run['policy'],'samples':len(rs),'raw_sha256':hashlib.sha256(raw).hexdigest()})
    assert set(ids['train']).isdisjoint(ids['validation']) and min(map(len,groups.values()))>=10
    x=np.array([r['x'] for r in groups['train']],dtype=np.float32);y=np.array([r['y'] for r in groups['train']])
    forest=RandomForestRegressor(n_estimators=32,max_depth=6,min_samples_leaf=3,random_state=731,n_jobs=1).fit(x,y)
    report={}
    for split,rs in groups.items():
        sx=np.array([r['x'] for r in rs],dtype=np.float32);sy=np.array([r['y'] for r in rs]);pred=forest.predict(sx)
        # Same last-five EWMA estimator as browser, no model feature leakage.
        hist=[]
        for v in sx[:,:5]:
            value=float(v[0])
            for q in v:value=.6*float(q)+.4*value
            hist.append(value)
        report[split]={'samples':len(rs),'forest_mae_bps':mean_absolute_error(sy,pred),'forest_rmse_bps':float(mean_squared_error(sy,pred)**.5),'ewma_mae_bps':mean_absolute_error(sy,hist),'ewma_rmse_bps':float(mean_squared_error(sy,hist)**.5)}
    trees=[]
    for estimator in forest.estimators_:
        t=estimator.tree_;trees.append({'left':t.children_left.tolist(),'right':t.children_right.tolist(),'feature':t.feature.tolist(),'threshold':t.threshold.tolist(),'value':t.value[:,0,0].tolist()})
    model={'schema':'forest-v1','feature_names':NAMES,'dtype':'float32 before threshold comparison','trees':trees,'provenance':{'sessions':provenance,'training_session_ids':ids['train'],'validation_session_ids':ids['validation'],'test_session_ids':[],'hyperparameters':forest.get_params(),'command':'python ml/train.py','python':platform.python_version(),'sklearn':sklearn.__version__,'selection':'Fixed initial specification; no hyperparameter search or validation tuning','target':'Next completed sequential video request effective throughput bps','exclusions':'non-video, init, zero-size/duration, overlapping or incomplete requests; five-observation warmup','report':report}}
    model['checksum']=hashlib.sha256(json.dumps(trees,sort_keys=True).encode()).hexdigest()
    out=ROOT/'data/models';out.mkdir(exist_ok=True)
    (out/'forest.json').write_text(json.dumps(model,separators=(',',':')));joblib.dump(forest,out/'forest.joblib')
    # Real vectors plus values either side of exported thresholds catch float32 errors.
    vectors=[r['x'] for rs in groups.values() for r in rs][:100]
    for t in trees[:8]:
        for i,f in enumerate(t['feature']):
            if f>=0:
                for offset in [-.01,0,.01]:
                    v=list(vectors[0]);v[f]=t['threshold'][i]+offset;vectors.append(v)
                break
    parity=[{'x':v,'expected':float(forest.predict(np.array([v],dtype=np.float32))[0])} for v in vectors]
    (out/'parity.json').write_text(json.dumps(parity));(collection_dir/'model-report.json').write_text(json.dumps(report,indent=2))
    (collection_dir/'dataset.json').write_text(json.dumps({'groups':groups,'session_ids':ids},indent=2))
    print(json.dumps(report,indent=2));print('Model checksum:',model['checksum'])
if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--collection-dir',type=Path,default=ROOT/'data/results',help='Folder containing collect-runs.json and its raw exports; model files are replaced')
    train(parser.parse_args().collection_dir)
