"""Versioned derived metrics. Never mutate raw observations when recalculating."""
import math
import statistics
from collections import Counter,defaultdict

def summarize(events,delivery):
    seen=set();clean=[]
    for e in events:
        seq=e.get('seq')
        if seq is not None:
            if seq in seen:continue
            seen.add(seq)
        clean.append(e)
    events=sorted(clean,key=lambda e:e['t'])
    intent=first=wait=None;paused=seeking=False;last_t=0.;eligible=0.;stalls=[]
    for e in events:
        k,t=e['kind'],e['t']
        if first is not None and not paused and not seeking:eligible+=max(0,t-last_t)
        last_t=t
        if k=='intent' and intent is None:intent=t
        if k=='playing':
            if first is None:first=t
            if wait is not None:stalls.append([wait,t]);wait=None
            paused=seeking=False
        elif k=='waiting' and first is not None and not paused and not seeking and wait is None and e.get('buffer',float('inf'))<.25:wait=t
        elif k in ('pause','seeking','ended','close','error'):
            if wait is not None:stalls.append([wait,t]);wait=None
            if k=='pause':paused=True
            if k=='seeking':seeking=True
    end=events[-1]['t'] if events else 0
    open_stall=wait is not None
    if wait is not None:stalls.append([wait,end])
    segments=[e for e in events if e['kind']=='segment']
    rendered=[e for e in events if e['kind']=='rendered' and e.get('value') is not None]
    requested=[e for e in events if e['kind']=='requested' and e.get('representation') is not None]
    network_requested=[e for e in events if e['kind']=='request' and e.get('stream_type')=='video' and e.get('request_type')=='MediaSegment' and e.get('representation') is not None]
    def transitions(rows):
        values=[]
        for e in rows:
            key=(e.get('representation'),e.get('value'))
            if not values or values[-1][0]!=key:values.append((key,e.get('value',0)))
        return values
    qualities=transitions(rendered);requests=transitions(network_requested)
    # Split progress at actual rendered transitions, including the final sample.
    # New records carry media_time at transition; legacy records retain ~1 Hz resolution.
    weighted=duration=0.;current=None;previous=None
    for e in events:
        k=e['kind']
        if k=='seeking':previous=None
        progress=e.get('media_time') if k=='rendered' else e.get('value') if k=='sample' else None
        if progress is not None:
            if previous is not None and current is not None:
                delta=progress-previous
                if 0<delta<3:weighted+=delta*current;duration+=delta
            previous=progress
        if k=='rendered':current=e.get('value')
    lat=sorted(e['duration'] for e in segments if e.get('duration') is not None)
    decisions=[e for e in events if e['kind']=='decision']
    by_id={e['decision_id']:e for e in decisions if e.get('decision_id')}
    pairs=[]
    for i,s in enumerate(segments):
        d=by_id.get(s.get('decision_id'))
        if d is None and not s.get('decision_id'):
            candidates=[d for d in decisions if d.get('epoch',0)==s.get('epoch',0) and d.get('boundary')==s.get('boundary',i) and d['t']<=s.get('start',-1)]
            d=candidates[-1] if candidates else None
        if d is not None and d.get('value') is not None and d['t']<=s.get('start',-1) and d.get('epoch',0)==s.get('epoch',0):pairs.append((d,s))
    def error(metric,source=None):
        diffs=[d['value']-s['throughput'] for d,s in pairs if source is None or d.get('predictor')==source]
        return (statistics.mean(abs(x) for x in diffs) if metric=='mae' else statistics.mean(x*x for x in diffs)**.5) if diffs else None
    totals=Counter(d['asset'] for d in delivery if d['asset'].startswith('chunk-') and not d['asset'].startswith('chunk-4-'))
    intervals=defaultdict(set)
    for asset in totals:
        _,rep,num=asset.removesuffix('.m4s').split('-');intervals[num].add(rep)
    inference=[e['inference_ms'] for e in decisions if e.get('inference_ms') is not None]
    total=sum(b-a for a,b in stalls)
    return {'metric_version':'audit-v2.1','startup_s':None if first is None or intent is None else first-intent,
      'rebuffer_s':total,'stall_count':len(stalls),'stall_intervals':stalls,'open_stall_at_last_observation':open_stall,
      'rebuffer_ratio':total/max(.001,eligible) if first is not None else None,'playback_observation_s':eligible,
      'rendered_bitrate_bps':weighted/duration if duration else None,'quality_weighted_media_s':duration,
      'quality_initial_assignments':int(bool(qualities)),'quality_switches':max(0,len(qualities)-1),
      'switch_magnitude_bps':sum(abs(a[1]-b[1]) for a,b in zip(qualities,qualities[1:])),
      'rendered_callbacks':len(rendered),'requested_initial_assignments':1 if requests else None,'requested_quality_switches':max(0,len(requests)-1) if requests else None,
      'requested_quality_events':len(requested),'requested_transition_basis':'actual video media request starts' if requests else 'unavailable in legacy observations',
      'download_count':len(lat),'download_mean_s':statistics.mean(lat) if lat else None,'download_median_s':statistics.median(lat) if lat else None,
      'download_p95_s':lat[max(0,math.ceil(.95*len(lat))-1)] if lat else None,
      'unique_video_intervals':len(intervals),'replacement_intervals':sum(len(v)>1 for v in intervals.values()),
      'repeated_video_assets':sum(max(0,n-1) for n in totals.values()),'video_request_count':sum(totals.values()),
      'init_requests':sum(d['asset'].startswith('init-') for d in delivery),
      'client_retry_starts':sum(e.get('retry_attempts',0)>0 for e in events if e['kind']=='request'),
      'payload_bytes':sum(d.get('bytes',0) for d in delivery),'delivery_failures':sum(d.get('status')!='complete' for d in delivery),
      'prediction_count':len(pairs),'prediction_mae_bps':error('mae'),'prediction_rmse_bps':error('rmse'),
      'forest_prediction_count':sum(d.get('predictor')=='random forest' for d,s in pairs),
      'forest_mae_bps':error('mae','random forest'),'forest_rmse_bps':error('rmse','random forest'),
      'predictor_decision_counts':dict(Counter(d.get('predictor','unknown') for d in decisions)),
      'inference_mean_ms':statistics.mean(inference) if inference else None,
      'browser_errors':sum(e['kind']=='error' for e in events),'excluded_requests':sum(e['kind']=='excluded' for e in events),
      'interacted':any(e['kind']=='interaction' for e in events),'observed_s':end,
      'played_seconds':max([e.get('value',0) for e in events if e['kind']=='sample'] or [0]),
      'natural_end':any(e['kind']=='ended' and not e.get('reason','').startswith('session ') for e in events)}
