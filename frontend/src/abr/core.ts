export const FEATURE_NAMES=['tp_lag5_bps','tp_lag4_bps','tp_lag3_bps','tp_lag2_bps','tp_lag1_bps','mean_bps','std_bps','trend_bps','last_duration_s','last_idle_s','last_bytes'];
export type Observation={throughput:number,duration:number,size:number,start:number,end:number,idle:number};
export function features(h:Observation[]):number[]|null {
  if(h.length<5)return null;
  const a=h.slice(-5),v=a.map(x=>x.throughput),mean=v.reduce((a,b)=>a+b)/5,last=a[4];
  return [...v,mean,Math.sqrt(v.reduce((s,x)=>s+(x-mean)**2,0)/5),(v[4]-v[0])/4,last.duration,last.idle,last.size];
}
export function ewma(h:Observation[]):number {return h.slice(-5).reduce((v,x)=>.6*x.throughput+.4*v,h.at(-5)?.throughput??h[0]?.throughput??450000);}
export type Tree={left:number[],right:number[],feature:number[],threshold:number[],value:number[]};
export type Forest={schema:string,feature_names:string[],trees:Tree[],provenance:Record<string,unknown>};
export function validateModel(m:Forest):boolean {
  try{return m?.schema==='forest-v1'&&JSON.stringify(m.feature_names)===JSON.stringify(FEATURE_NAMES)&&Array.isArray(m.trees)&&m.trees.length>0&&m.trees.length<=64&&m.trees.every(t=>Array.isArray(t.left)&&t.left.length>0&&t.left.length<=1024&&['left','right','feature','threshold','value'].every(k=>Array.isArray((t as any)[k])&&(t as any)[k].length===t.left.length)&&t.left.every((l,i)=>Number.isFinite(t.value[i])&&Number.isFinite(t.threshold[i])&&(l===-1?t.right[i]===-1:(Number.isInteger(l)&&l>i&&l<t.left.length&&Number.isInteger(t.right[i])&&t.right[i]>i&&t.right[i]<t.left.length&&Number.isInteger(t.feature[i])&&t.feature[i]>=0&&t.feature[i]<FEATURE_NAMES.length))));}catch{return false;}
}
export function predict(m:Forest,x:number[]):number {
  if(x.length!==FEATURE_NAMES.length||!x.every(Number.isFinite))throw Error('Invalid feature vector');
  const f=x.map(Math.fround);
  return m.trees.reduce((s,t)=>{let n=0;while(t.left[n]!==-1)n=f[t.feature[n]]<=t.threshold[n]?t.left[n]:t.right[n];return s+t.value[n];},0)/m.trees.length;
}
export type Rep={id:string,bandwidth:number,height:number};
export class Controller {
  boundary=-1; selected=0; upgrades=0; cached:{index:number,reason:string}|null=null;
  decide(reps:Rep[],forecast:number,buffer:number,boundary:number) {
    if(boundary===this.boundary&&this.cached)return this.cached;
    let index=0,reason='cold start';
    if(boundary>0){
      const budget=Math.max(0,forecast*.8-80000);
      reps.forEach((r,i)=>{if(r.bandwidth<=budget)index=i;});
      reason=index===0&&reps[0].bandwidth>budget?'no sustainable representation':'80% forecast less 80 kbps audio/overhead reserve';
      if(buffer<4){index=0;reason='low buffer protection (<4 s)';}
      if(index>this.selected){this.upgrades++;if(this.upgrades<2){index=this.selected;reason='upgrade waits for two observation boundaries';}else{index=Math.min(index,this.selected+1);this.upgrades=0;}}
      else this.upgrades=0;
    }
    this.selected=index;this.boundary=boundary;return this.cached={index,reason};
  }
}
