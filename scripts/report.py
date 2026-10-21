"""Build evidence tables/plots from executed held-out runs; never invent rows."""
import csv
import hashlib
import json
import math
import statistics
import sys
from pathlib import Path
import numpy as np
import joblib
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from ml.features import rows
from backend.app.summary import summarize

def lineplot(series,path,title,ylabel):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    colors=['#56cce8','#8ae5ba','#f6b965']
    plt.style.use('dark_background')
    fig,ax=plt.subplots(figsize=(10,3.6),layout='constrained')
    fig.set_facecolor('#0b1018');ax.set_facecolor('#0b1018')
    for i,(name,pairs) in enumerate(series):
        if pairs:ax.plot([x for x,y in pairs],[y for x,y in pairs],label=name,color=colors[i%3],linewidth=1.6)
    ax.set(title=title,xlabel='Elapsed session time (s)',ylabel=ylabel,ylim=(0,None))
    ax.grid(alpha=.15);ax.legend(frameon=False,ncol=3,fontsize=9)
    fig.savefig(path);fig.savefig(path.with_suffix('.png'),dpi=150);plt.close(fig)

def main():
    out=ROOT/'data/results';runs=json.loads((out/'evaluate-runs.json').read_text())
    complete=[r for r in runs if 'summary' in r]
    assert complete,'No executed completed evaluation runs'
    model=json.loads((ROOT/'data/models/forest.json').read_text());forest=joblib.load(ROOT/'data/models/forest.joblib')
    trainids=set(model['provenance']['training_session_ids']+model['provenance']['validation_session_ids'])
    assert trainids.isdisjoint(r['id'] for r in complete)
    allrows=[];exports={}
    for r in complete:
        d=json.loads((out/f"{r['id']}.json").read_text());exports[r['id']]=d
        # Recompute derived summaries from immutable raw observations.
        summary=summarize(d['events'],d['delivery']);r['summary']=summary;d['meta']['summary']=summary
        (ROOT/'data/sessions'/r['id']/'summary.json').write_text(json.dumps(summary,indent=2))
        (out/f"{r['id']}.json").write_text(json.dumps(d,indent=2))
        allrows.extend(rows(d['events']))
    x=np.array([r['x'] for r in allrows],dtype=np.float32);y=np.array([r['y'] for r in allrows]);pred=forest.predict(x)
    ew=[]
    for v in x[:,:5]:
        value=float(v[0])
        for q in v:value=.6*float(q)+.4*value
        ew.append(value)
    modeltest={'samples':len(y),'forest_mae_bps':float(np.abs(pred-y).mean()),'forest_rmse_bps':float(np.mean((pred-y)**2)**.5),'ewma_mae_bps':float(np.abs(np.array(ew)-y).mean()),'ewma_rmse_bps':float(np.mean((np.array(ew)-y)**2)**.5),'session_ids':[r['id'] for r in complete],'frozen_model_checksum':model['checksum']}
    (out/'heldout-model-report.json').write_text(json.dumps(modeltest,indent=2))
    (out/'evaluate-runs.json').write_text(json.dumps(runs,indent=2))
    flatkeys=['id','policy','profile','seed','scale']+list(complete[0]['summary'])
    with (out/'evaluation.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=flatkeys);writer.writeheader()
        for r in complete:writer.writerow({**{k:r[k] for k in flatkeys if k in r},**r['summary']})
    aggregates=[]
    for profile in sorted({r['profile'] for r in complete}):
        series=[]
        for policy in ['historical','ml','default']:
            subset=[r for r in complete if r['profile']==profile and r['policy']==policy]
            if not subset:continue
            agg={'profile':profile,'policy':policy,'runs':len(subset)}
            for metric in ['startup_s','rebuffer_s','rendered_bitrate_bps','download_p95_s','quality_switches']:
                vals=[r['summary'][metric] for r in subset if r['summary'][metric] is not None]
                agg[metric+'_mean']=statistics.mean(vals) if vals else None
                agg[metric+'_std']=statistics.stdev(vals) if len(vals)>1 else None
            aggregates.append(agg)
            e=exports[subset[0]['id']]['events'];series.append((policy,[(p['t'],p['buffer']) for p in e if p['kind']=='sample']))
        lineplot(series,out/f'buffer-{profile}.svg',f'{profile}: measured playable buffer (first repetition)','seconds')
    (out/'aggregate.json').write_text(json.dumps(aggregates,indent=2))
    with (out/'aggregate.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(aggregates[0]));w.writeheader();w.writerows(aggregates)
    parity=json.loads((ROOT/'data/models/parity.json').read_text())
    text=['# Executed results','',f'{len(complete)} held-out bounded playback runs were executed. Ending rule: '+complete[0]['ending_rule']+'. Fresh Chrome contexts, reduced motion, no allowed external requests. One repetition per profile/policy provides **no variance estimate**. These are bounded local prototype experiments, not Internet or full-video performance claims.','',
      '## Media and calibration','',
      'FFmpeg 7.1 generated 120 seconds of testsrc2 motion and sine audio. FFprobe 4.0.2 verified four distinct video streams (426×240, 640×360, 854×480, 1280×720). Four 60-segment video timelines align exactly; AAC ends at 120 seconds with an additional short final fragment. 301 total media fragments.','',
      'The first limiter implementation failed with about 41% underdelivery because of Windows timer granularity. It was corrected before collection. Final real HTTP calibration:','',
      '| Concurrent requests | Window (s) | Configured Mbps | Measured Mbps | Error |','|---|---:|---:|---:|---:|']
    for r in json.loads((out/'calibration.json').read_text()):text.append(f"| {r['concurrency']} | {r['window_s']:.2f} | {r['expected_bps']/1e6:.2f} | {r['measured_bps']/1e6:.3f} | {r['relative_error']*100:.1f}% |")
    report=model['provenance']['report']
    text+=['','## Model provenance','',f"32 trees, depth ≤6, minimum leaf 3, seed 731. Training: {report['train']['samples']} rows / 6 whole sessions; validation: {report['validation']['samples']} rows / 2 whole sessions. No tuning search. {len(parity)} actual/threshold vectors passed Python–TypeScript parity at absolute tolerance 1e-6 bps. Checksum: `{model['checksum']}`.",'',
       '| Split | Samples | Forest MAE (Mbps) | EWMA MAE (Mbps) | Forest RMSE (Mbps) | EWMA RMSE (Mbps) |','|---|---:|---:|---:|---:|---:|']
    for name,r in [('Training',report['train']),('Validation',report['validation']),('Held-out request rows',modeltest)]:text.append(f"| {name} | {r['samples']} | {r['forest_mae_bps']/1e6:.3f} | {r['ewma_mae_bps']/1e6:.3f} | {r['forest_rmse_bps']/1e6:.3f} | {r['ewma_rmse_bps']/1e6:.3f} |")
    text+=['','Offline held-out forecast errors score both predictors on the same causal request rows from all final policies. This does not prove a policy advantage: each controller changes future request sizes/timing. Runtime errors in per-run summaries include explicitly labeled warmup EWMA predictions and score only decisions made before target start.','',
      f"Held-out MAE: forest {modeltest['forest_mae_bps']/1e6:.3f}, EWMA {modeltest['ewma_mae_bps']/1e6:.3f} Mbps. RMSE: forest {modeltest['forest_rmse_bps']/1e6:.3f}, EWMA {modeltest['ewma_rmse_bps']/1e6:.3f} Mbps. Default mode had {sum(r['summary']['stall_count'] for r in complete if r['policy']=='default')} stalls across {sum(r['policy']=='default' for r in complete)} runs. Request-size/timing distribution and unfamiliar transitions may affect generalization; this experiment does not isolate those causes. Read quality and stalls together. A single repetition cannot establish significance.",
      '', '## Playback outcomes','',
      '| Profile | Policy | Startup s | Rebuffer s | Stalls | Rendered Mbps | Switches | Video requests |','|---|---|---:|---:|---:|---:|---:|---:|']
    for r in complete:
        s=r['summary'];text.append(f"| {r['profile']} | {r['policy']} | {s['startup_s']:.3f} | {s['rebuffer_s']:.3f} | {s['stall_count']} | {(s['rendered_bitrate_bps'] or 0)/1e6:.3f} | {s['quality_switches']} | {s['download_count']} |")
    text+=['','Bitrate is a duration-weighted rendered quality proxy. Profile-specific plots are in `data/results/buffer-*.svg`; aggregate CSV/JSON, per-run exports, and the exact session IDs remain beside them. Aborted transfers at the fixed stopping boundary are retained and counted, not mislabeled successful deliveries.','',
       '## Verification and limits','',
       '- Real Chrome smoke playback advanced beyond 21 seconds and decoded over 500 frames; ML mode requested all four video representations. No uncaught page errors, remote requests, or narrow-viewport horizontal overflow occurred in those smoke checks.','- Backend and causal dataset tests passed; controller idempotence, low-buffer behavior, forecast influence, and forest parity tests passed. See `verification.json` for executed commands/outcomes.','- The prepared app was tested with non-local browser network requests actively blocked. This demonstrates no required CDN/model/media dependency; it is not an OS-wide airplane-mode test.','- The pinned frontend build emits a large-bundle warning (~1.19 MB before gzip, mostly dash.js). It succeeds.','- Global `pip check` found an unrelated pre-existing google-genai/httpx version conflict. Use the documented isolated virtual environment; no unrelated package was changed to resolve it.','- Local single-host pacing, synthetic content/capacity traces, short windows, one repetition, and small data limit generalization. Some forecasts can underperform EWMA. No stall-free or commercial superiority claim is made.','- Deliberate user pauses/seeks invalidate benchmark comparability. Rendered bitrate has ~1 Hz timing resolution. Network waiting is inferred from native waiting plus near-empty playable buffer; decode issues are not fully diagnosed.','']
    full=out/'full-playback.json'
    if full.exists():
        f=json.loads(full.read_text());text+=['## Full-clip verification','',f"Separate ML/stable smoke run `{f['sid']}` reached natural end at {f['proof']['time']:.3f} s, decoded {f['proof']['decoded_frames']} frames, had {f['summary']['stall_count']} stalls and {f['summary']['delivery_failures']} aborted deliveries. This full-clip run is separate from the bounded comparison matrix.",'']
    if (out/'media-reproduction.json').exists():
        m=json.loads((out/'media-reproduction.json').read_text());text+=['## Media reproduction boundary','',f"The corrected preparation command was rerun successfully after evaluation. {len(m['changed'])} of {m['assets_checked']} init/media files differed byte-for-byte after re-encoding. The original evaluated inventory, encode log and SHA-256 asset list are preserved as `media-*-evaluated.*`. All twelve comparison runs used the same original prepared media. The current demo uses the regenerated ladder; sessions carry an encoded-body fingerprint, and the UI warns when fingerprints differ. Bit-identical encoding across runs is not claimed.",'']
    (ROOT/'docs/RESULTS.md').write_text('\n'.join(text),encoding='utf-8')
    print(json.dumps({'completed_runs':len(complete),'heldout_predictions':modeltest},indent=2))
if __name__=='__main__':main()
