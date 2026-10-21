"""Executed HTTP pacing calibration, separate from playback/model evidence."""
import asyncio
import json
import time
import sys
from pathlib import Path
import httpx
ROOT=Path(__file__).resolve().parents[1]

async def main():
    async with httpx.AsyncClient(base_url='http://127.0.0.1:8000',timeout=60,trust_env=False) as c:
        outcomes=[]
        for concurrency in [1,2]:
            sid=(await c.post('/api/sessions',json={'profile':'stable','scale':.5,'purpose':'calibration'})).json()['id']
            async def transfer(i):
                total=0
                # Two video-sized bodies per worker, >4 s aggregate observation.
                for _ in range(2):
                    r=await c.get(f'/media/{sid}/chunk-3-00001.m4s'); r.raise_for_status();total+=len(r.content)
                return total
            begin=time.perf_counter()
            sizes=await asyncio.gather(*(transfer(i) for i in range(concurrency)))
            duration=time.perf_counter()-begin; observed=sum(sizes)*8/duration; expected=1_750_000
            outcome={'concurrency':concurrency,'bytes':sum(sizes),'window_s':duration,'expected_bps':expected,'measured_bps':observed,'relative_error':abs(observed/expected-1)}
            outcomes.append(outcome);print(outcome,flush=True)
            await c.post(f'/api/sessions/{sid}/finish',json={'status':'finished'})
        (ROOT/'data/results/calibration.json').write_text(json.dumps(outcomes,indent=2))
        assert all(r['relative_error']<.15 for r in outcomes),'Limiter calibration failed'
if __name__=='__main__':asyncio.run(main())
