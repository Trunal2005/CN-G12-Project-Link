const colors=['#56cce8','#8ae5ba','#f6b965','#b898ed'];
export function ComparisonOverlay({sessions}:{sessions:any[]}){
 const series=sessions.map(s=>({id:s.meta.id,name:s.meta.policy,points:s.events.filter((e:any)=>e.kind==='sample')}));
 const maxT=Math.max(1,...series.flatMap(s=>s.points.map((p:any)=>p.t)));
 const maxB=Math.max(1,...series.flatMap(s=>s.points.map((p:any)=>p.buffer??0)));
 return <div className="chart overlay"><div className="charttitle"><span>Overlaid playable buffer · same elapsed session clock</span><small>{maxB.toFixed(1)} s</small></div><svg viewBox="0 0 600 150" role="img" aria-label="Overlaid buffer timelines">{[10,50,90,130].map(y=><line key={y} x1="0" x2="600" y1={y} y2={y} stroke="#ffffff0c"/>)}{series.map((s,i)=><path key={s.id} d={s.points.map((p:any,j:number)=>`${j?'L':'M'} ${p.t/maxT*600} ${130-(p.buffer??0)/maxB*120}`).join(' ')} fill="none" stroke={colors[i%4]} strokeWidth="2"/>)}</svg><div className="axis"><span>0 s</span>{series.map((s,i)=><span key={s.id} style={{color:colors[i%4]}}>{s.name} · {s.id.slice(0,6)}</span>)}<span>{maxT.toFixed(0)} s</span></div></div>;
}
