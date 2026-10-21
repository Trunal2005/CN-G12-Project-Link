"""Read-only raw-log analysis; reports go only to the chosen audit directory."""
import argparse,json,statistics,hashlib,sys,csv
from pathlib import Path
import numpy as np
import joblib
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.app.summary import summarize
from ml.features import rows

def write(p,data):p.write_text(json.dumps(data,indent=2,allow_nan=False),encoding='utf-8')
def main(out):
 out=Path(out).resolve();analysis=out/'analysis';analysis.mkdir(exist_ok=True)
 old=json.loads((ROOT/'data/results/evaluate-runs.json').read_text());recomputed=[]
 for run in old:
  raw=json.loads((ROOT/'data/results'/f"{run['id']}.json").read_text());new=summarize(raw['events'],raw['delivery']);before=raw['meta']['summary']
  changes={k:{'original':v,'recomputed':new.get(k)} for k,v in before.items() if k in new and isinstance(v,(float,int)) and v is not None and abs(v-(new[k] or 0))>1e-7}
  recomputed.append({'id':run['id'],'policy':run['policy'],'profile':run['profile'],'original_summary':before,'audit_v2_summary':new,'changed_numeric_fields':changes})
 write(analysis/'original-summary-recompute.json',recomputed)
 baseline=json.loads((out/'baseline-historical-stable.json').read_text());bs=summarize(baseline['events'],baseline['delivery'])
 candidate=json.loads((out/'candidate/runs.json').read_text())[0];write(analysis/'switching-before-after.json',{'same_current_bundle':True,'baseline_old_behavior_40s':bs,'candidate_append_only_40s':candidate['summary'],'note':'Baseline/candidate also differ in repaired delivery pacing and metric version; do not attribute all throughput/quality changes solely to fast switching.'})
 frozen=json.loads((out/'frozen.json').read_text());model=json.loads((ROOT/'data/models/forest.json').read_text());forest=joblib.load(ROOT/'data/models/forest.joblib')
 # Trained artifacts must remain exactly frozen, including metadata.
 assert hashlib.sha256((ROOT/'data/models/forest.json').read_bytes()).hexdigest()==frozen['model_file_sha256']
 trainids=set(model['provenance']['training_session_ids']+model['provenance']['validation_session_ids'])
 if not (out/'matrix/runs.json').exists():return
 runs=json.loads((out/'matrix/runs.json').read_text());assert trainids.isdisjoint(r['id'] for r in runs)
 raws={r['id']:json.loads((out/'matrix'/f"{r['id']}.json").read_text()) for r in runs};allrows=[];runtime_diffs=[];trace=None
 for run in runs:
  raw=raws[run['id']];derived=summarize(raw['events'],raw['delivery'])
  # v2.1 fixes initial-request counters from existing request starts. Frozen v2
  # raw files/summaries stay immutable; every other saved metric must match.
  assert all(derived[k]==v for k,v in run['summary'].items() if k not in ['metric_version','requested_initial_assignments','requested_quality_switches'])
  assert run['identities']['source_identity']==frozen['source_identity'];assert run['identities']['asset_fingerprint']==frozen['asset_fingerprint'];assert run['identities']['model_checksum']==frozen['tree_checksum']
  rr=rows(raw['events']);allrows+=rr;decisions={e['decision_id']:e for e in raw['events'] if e['kind']=='decision'}
  segments=[e for e in raw['events'] if e['kind']=='segment']
  for s in segments:
   d=decisions.get(s.get('decision_id'))
   if d:
    assert d['t']<=s['start'] and d['epoch']==s['epoch'] and d['representation']==s['representation']
    if d['predictor']=='random forest':
     expected=float(forest.predict(np.array([d['features']],dtype=np.float32))[0]);runtime_diffs.append(abs(d['value']-expected));assert runtime_diffs[-1]<1e-6
  if trace is None and run['policy']=='ml' and run['profile']=='step':
   for i,s in enumerate(segments):
    d=decisions.get(s.get('decision_id'))
    if not d or d['predictor']!='random forest' or i==0:continue
    rendered=[e for e in raw['events'] if e['kind']=='rendered' and e['representation']==s['representation'] and s['media_start']-.1<=e.get('media_time',-999)<s['media_start']+s['media_duration']+.1]
    if not rendered:continue
    delivery=[x for x in raw['delivery'] if x['asset']==s['asset'] and x['status']=='complete']
    trace={'session':run['id'],'profile':run['profile'],'seed':run['seed'],'previous_observation':segments[i-1],'forecast_decision':d,'target_segment':s,'server_delivery':delivery,'rendered_transition':rendered[0],'feature_names':model['feature_names']};break
 assert runtime_diffs and trace is not None
 write(analysis/'real-segment-trace.json',trace)
 x=np.array([r['x'] for r in allrows],dtype=np.float32);y=np.array([r['y'] for r in allrows]);pred=forest.predict(x);ew=[]
 for v in x[:,:5]:
  value=float(v[0])
  for z in v:value=.6*float(z)+.4*value
  ew.append(value)
 report={'completed_runs':len(runs),'repetitions_per_cell':{},'causal_rows':len(y),'forest_mae_bps':float(np.abs(pred-y).mean()),'ewma_mae_bps':float(np.abs(np.array(ew)-y).mean()),'forest_rmse_bps':float(np.mean((pred-y)**2)**.5),'ewma_rmse_bps':float(np.mean((np.array(ew)-y)**2)**.5),'runtime_forest_predictions_checked':len(runtime_diffs),'runtime_parity_max_abs_bps':max(runtime_diffs),'aggregate':[]}
 corrections=[]
 for run in runs:
  raw=raws[run['id']];derived=summarize(raw['events'],raw['delivery']);corrections.append({'id':run['id'],'saved_metric_version':run['summary']['metric_version'],'derived_metric_version':derived['metric_version'],'saved_requested_switches':run['summary']['requested_quality_switches'],'derived_requested_switches':derived['requested_quality_switches'],'derived_requested_initial_assignments':derived['requested_initial_assignments']})
 write(analysis/'requested-counter-corrections.json',corrections)
 metrics=['startup_s','rebuffer_s','stall_count','rendered_bitrate_bps','quality_switches','download_p95_s','video_request_count','payload_bytes','played_seconds']
 for profile in ['stable','step','fluctuate']:
  for policy in ['historical','ml','default']:
   group=[r for r in runs if r['profile']==profile and r['policy']==policy];key=profile+'/'+policy;report['repetitions_per_cell'][key]=len(group)
   agg={'profile':profile,'policy':policy,'n':len(group)}
   for metric in metrics:
    vals=[r['summary'][metric] for r in group if r['summary'][metric] is not None]
    agg[metric+'_mean']=statistics.mean(vals) if vals else None;agg[metric+'_std']=statistics.stdev(vals) if len(vals)>1 else None
   report['aggregate'].append(agg)
 write(analysis/'results.json',report)
 with (analysis/'aggregate.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(report['aggregate'][0]));w.writeheader();w.writerows(report['aggregate'])
 import matplotlib
 matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 plt.style.use('dark_background');fig,axes=plt.subplots(1,2,figsize=(11,4),layout='constrained');colors={'historical':'#56cce8','ml':'#8ae5ba','default':'#f6b965'}
 for ax,metric,label,scale in [(axes[0],'rebuffer_s','Rebuffering (s)',1),(axes[1],'rendered_bitrate_bps','Rendered bitrate proxy (Mbps)',1e6)]:
  for pi,policy in enumerate(colors):
   a=[r for r in report['aggregate'] if r['policy']==policy];pos=np.arange(3)+(pi-1)*.23;ax.bar(pos,[r[metric+'_mean']/scale for r in a],width=.22,yerr=[(r[metric+'_std'] or 0)/scale for r in a],label=policy,color=colors[policy],capsize=3)
  ax.set_xticks(range(3),['stable','step','fluctuate']);ax.set_ylabel(label);ax.grid(axis='y',alpha=.15);ax.legend(fontsize=8);ax.set_ylim(bottom=0)
  if metric=='rebuffer_s' and all(r['rebuffer_s_mean']==0 for r in report['aggregate']):ax.set_ylim(0,1);ax.text(.5,.5,f'All {len(runs)} runs: 0 s rebuffering',ha='center',transform=ax.transAxes)
 fig.suptitle('Frozen bundle · sequential 40 s runs · mean ± sample SD (n=3 per cell)');fig.savefig(analysis/'comparison.png',dpi=150);fig.savefig(analysis/'comparison.svg');plt.close(fig)
 lines=['# Audit: matched measured results','',f"Executed {len(runs)} sequential fresh-Chrome runs. Each cell has three repetitions; ending rule is 40 seconds wall clock after start returns, not natural video completion. Actual played seconds are retained per run. All use the same frozen encoded bundle, model, source and common buffer settings.",'','| Profile | Policy | n | Startup s (mean ± SD) | Rebuffer s (mean ± SD) | Rendered Mbps (mean ± SD) | Switches (mean) | Played s (mean) |','|---|---|---:|---:|---:|---:|---:|---:|']
 for a in report['aggregate']:lines.append(f"| {a['profile']} | {a['policy']} | {a['n']} | {a['startup_s_mean']:.3f} ± {a['startup_s_std']:.3f} | {a['rebuffer_s_mean']:.3f} ± {a['rebuffer_s_std']:.3f} | {a['rendered_bitrate_bps_mean']/1e6:.3f} ± {a['rendered_bitrate_bps_std']/1e6:.3f} | {a['quality_switches_mean']:.2f} | {a['played_seconds_mean']:.3f} |")
 lines+=['',f"Same-row next-request prediction test: {len(y)} causal rows. Forest MAE {report['forest_mae_bps']/1e6:.3f} Mbps vs EWMA {report['ewma_mae_bps']/1e6:.3f}; RMSE {report['forest_rmse_bps']/1e6:.3f} vs {report['ewma_rmse_bps']/1e6:.3f} Mbps. No new fitting or tuning occurred. {len(runtime_diffs)} runtime forest decisions matched sklearn within {max(runtime_diffs):.3g} bps.",'','Error bars are sample standard deviations, not confidence intervals. Stable/step seeds do not change their capacity curves; repetitions are independent browser runs of the same prescribed curve. Synthetic local pacing and three repetitions do not establish Internet generalization. The model was trained on older preparation/pacing data; this distribution shift is retained and discussed, not hidden by retraining.','',f"Real segment trace: `{trace['session']}` · `{trace['target_segment']['asset']}`. See `real-segment-trace.json` for causal features, timestamps, request body bytes, prediction and actual rendered transition."]
 (analysis/'RESULTS.md').write_text('\n'.join(lines),encoding='utf-8');print(json.dumps({k:v for k,v in report.items() if k!='aggregate'},indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',required=True);main(p.parse_args().out)
