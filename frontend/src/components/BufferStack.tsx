import type {Snapshot} from '../player/lab';
export function BufferStack({snapshot:s}:{snapshot:Snapshot}){
 return <section className="panel depthpanel"><div className="sectionlabel">BUFFER RESERVE <span>02</span></div><div className="stackscene"><div className="stack">{Array.from({length:8},(_,i)=><div key={i} className={`slab ${i<Math.ceil(s.buffer/2)?'filled':''}`} style={{transform:`translateZ(${i*15}px)`}}/>)}</div></div><div className="stacktext"><strong>{s.buffer.toFixed(1)}<small> seconds</small></strong><p>Approximate buffer visualization<br/>One layer ≈ 2 seconds · up to 16 s shown</p></div><div className="decision"><span>LATEST DECISION</span><p>{s.reason}</p><small>{s.predictor} · boundary {s.decisions.at(-1)?.boundary??'—'}</small></div></section>;
}
