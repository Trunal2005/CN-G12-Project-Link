import numpy as np
NAMES=['tp_lag5_bps','tp_lag4_bps','tp_lag3_bps','tp_lag2_bps','tp_lag1_bps','mean_bps','std_bps','trend_bps','last_duration_s','last_idle_s','last_bytes']

def features(history):
    if len(history)<5:return None
    a=history[-5:];v=np.array([s['throughput'] for s in a],dtype=np.float64);last=a[-1]
    return [*v.tolist(),float(v.mean()),float(v.std()),float((v[-1]-v[0])/4),last['duration'],last['idle'],last['size']]

def rows(events):
    """No profile/capacity/identity enters features; a new history per session."""
    history=[];result=[];epoch=None
    for s in sorted((e for e in events if e['kind']=='segment'),key=lambda e:e['t']):
        if s.get('epoch',0)!=epoch:history=[];epoch=s.get('epoch',0)
        if s.get('size',0)<=0 or s.get('duration',0)<=0:continue
        if history and s['start']<history[-1]['t']:continue
        x=features(history)
        if x is not None:result.append({'x':x,'y':s['throughput'],'target_start':s['start'],'history_end':history[-1]['t'],'boundary':len(history),'epoch':epoch})
        s=dict(s);s['idle']=max(0,s['start']-history[-1]['t']) if history else 0
        history.append(s)
    return result
