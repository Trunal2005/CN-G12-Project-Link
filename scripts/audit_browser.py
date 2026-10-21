"""Exercise current UI and actual media, with deliberate API/model fault injection."""
import argparse,asyncio,json,csv,sys
from pathlib import Path
import numpy as np
import joblib
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.app.summary import summarize
from ml.features import rows

async def run(base,out):
    Path(out).mkdir(parents=True,exist_ok=True);target=Path(out)/'integration';target.mkdir(exist_ok=False);evidence={};errors=[];external=[];bad=[];model_mode='valid';fail_create=False
    forest=joblib.load(ROOT/'data/models/forest.joblib')
    async with async_playwright() as p:
        browser=await p.chromium.launch(channel='chrome',headless=True,args=['--autoplay-policy=no-user-gesture-required']);ctx=await browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce',accept_downloads=True)
        async def route(r):
            nonlocal fail_create
            if not r.request.url.startswith(base+'/'):external.append(r.request.url);await r.abort()
            elif r.request.url.endswith('/api/models/current') and model_mode!='valid':
                await r.fulfill(status=404 if model_mode=='missing' else 200,content_type='application/json',body='{"schema":"invalid","trees":{"length":1}}')
            elif fail_create and r.request.url.endswith('/api/sessions') and r.request.method=='POST':
                fail_create=False;await r.fulfill(status=500,content_type='application/json',body='{"detail":"injected recoverable API failure"}')
            else:await r.continue_()
        await ctx.route('**/*',route);page=await ctx.new_page();page.on('pageerror',lambda e:errors.append(str(e)));page.on('response',lambda r:bad.append([r.url,r.status]) if r.status>=400 else None)
        await page.goto(base);await page.wait_for_function('window.stallguard')
        async def choose(policy,profile='stable'):
            await page.get_by_label('Adaptation policy').select_option(policy);await page.get_by_label('Delivery profile').select_option(profile)
        async def start():
            await page.get_by_role('button',name='Start new session').click();await page.wait_for_function('document.querySelector("video").currentTime>3',timeout=30000);return await page.evaluate('window.stallguard.sid')
        async def saved(sid):
            raw=await (await ctx.request.get(base+f'/api/sessions/{sid}/export')).json();(target/f'{sid}.json').write_text(json.dumps(raw,indent=2));assert summarize(raw['events'],raw['delivery'])==raw['meta']['summary'];return raw
        await choose('historical');sid=await start();await page.wait_for_timeout(370)
        before=await page.evaluate('document.querySelector("video").currentTime');await page.get_by_role('button',name='Stop & save').click();await page.get_by_text('Session saved',exact=True).wait_for();raw=await saved(sid)
        assert raw['meta']['status']=='cancelled' and abs(raw['meta']['summary']['played_seconds']-before)<.4
        assert len({e['seq'] for e in raw['events']})==len(raw['events'])
        evidence['stop_final_sample']={'id':sid,'time_before_click':before,'saved_played_s':raw['meta']['summary']['played_seconds'],'summary_recomputed_equal':True}
        model_mode='missing';await choose('ml');sid_missing=await start();assert 'fallback' in await page.evaluate('window.stallguard.snapshot.predictor');await page.get_by_role('button',name='Stop & save').click();await page.get_by_text('Session saved',exact=True).wait_for();await saved(sid_missing)
        model_mode='invalid';sid_invalid=await start();assert 'fallback' in await page.evaluate('window.stallguard.snapshot.predictor');assert await page.get_by_text('Historical fallback · model unavailable or invalid',exact=True).is_visible();await page.get_by_role('button',name='Stop & save').click();await page.get_by_text('Session saved',exact=True).wait_for();await saved(sid_invalid)
        model_mode='valid';sid_ml=await start();await page.wait_for_function('window.stallguard.snapshot.predictor==="random forest"',timeout=30000);await page.wait_for_timeout(3000)
        assert await page.evaluate('window.stallguard.customRules.length')==1
        await page.get_by_role('button',name='Stop & save').click();await page.get_by_text('Session saved',exact=True).wait_for();raw=await saved(sid_ml)
        expected={r['boundary']:r for r in rows(raw['events'])};count=0
        for e in raw['events']:
            if e['kind']=='decision' and e.get('predictor')=='random forest':
                pred=float(forest.predict(np.array([e['features']],dtype=np.float32))[0]);assert abs(e['value']-pred)<1e-6;count+=1
                if e['boundary'] in expected:assert np.allclose(e['features'],expected[e['boundary']]['x'],rtol=1e-10,atol=1e-7)
        assert count>0 and raw['meta']['summary']['forest_prediction_count']>0
        decisions={e['decision_id']:e for e in raw['events'] if e['kind']=='decision'}
        for s in raw['events']:
            if s['kind']=='segment' and s.get('decision_id'):
                d=decisions[s['decision_id']];assert d['t']<=s['start'] and d['epoch']==s['epoch'] and d['representation']==s['representation']
        evidence['fallback_and_real_forest']={'missing_id':sid_missing,'invalid_id':sid_invalid,'valid_id':sid_ml,'actual_forest_vectors_checked':count,'causal_association_checked':True}
        await choose('default');sid_default=await start();assert await page.evaluate('window.stallguard.customRules.length')==0
        await page.locator('video').evaluate('(v)=>v.pause()');await page.wait_for_timeout(1500);await page.locator('video').evaluate('(v)=>v.play()');await page.wait_for_timeout(1000);await page.locator('video').evaluate('(v)=>v.currentTime=15');await page.wait_for_timeout(1500)
        await page.get_by_role('button',name='Stop & save').click();await page.get_by_text('Session saved',exact=True).wait_for();raw=await saved(sid_default)
        assert not any(e['kind']=='decision' for e in raw['events']) and raw['meta']['summary']['interacted'] and raw['meta']['summary']['stall_count']==0
        settings=next(e['settings'] for e in raw['events'] if e['kind']=='configuration');assert settings['abr']['rules']['throughputRule']['active'] and settings['abr']['rules']['bolaRule']['active']
        evidence['default_after_custom']={'id':sid_default,'custom_rule_count':0,'pause_seek_excluded_from_stalls':True}
        await choose('historical');sid_refresh=await start();await page.reload();await page.wait_for_function('window.stallguard')
        for _ in range(50):
            meta=await (await ctx.request.get(base+f'/api/sessions/{sid_refresh}')).json()
            if meta['status']=='partial':break
            await page.wait_for_timeout(100)
        assert meta['status']=='partial';await saved(sid_refresh);evidence['refresh_partial_id']=sid_refresh
        fail_create=True;await page.get_by_role('button',name='Start new session').click();await page.get_by_text('injected recoverable API failure',exact=False).wait_for();assert await page.get_by_role('button',name='Start new session').is_enabled();evidence['recoverable_create_error']=True
        await page.get_by_role('button',name='Compare Sessions').click();await page.locator('.sessionlist input:not(:disabled)').first.check();await page.locator('.sessionlist input:not(:disabled)').nth(1).check();await page.get_by_role('button',name='↓ Summary CSV').wait_for()
        async with page.expect_download() as info:await page.get_by_role('button',name='↓ Summary CSV').click()
        dl=await info.value;csvrows=list(csv.reader(Path(await dl.path()).read_text().splitlines()));assert len(csvrows)==3 and all(len(x)==len(csvrows[0]) for x in csvrows)
        async with page.expect_download() as info:await page.get_by_role('button',name='↓ Comparison JSON').click()
        dl=await info.value;assert len(json.loads(Path(await dl.path()).read_text()))==2
        evidence['comparison_exports_parsed']=True;assert await page.locator('.warning').is_visible()
        headings={}
        for tab in ['Playback Lab','Compare Sessions','How It Works']:
            await page.get_by_role('button',name=tab).click();headings[tab]={'heading':await page.locator('h1').inner_text(),'buttons':await page.get_by_role('button').all_text_contents()}
            for width,height in [(1440,1000),(390,844)]:
                await page.set_viewport_size({'width':width,'height':height});assert not await page.evaluate('document.documentElement.scrollWidth>innerWidth');await page.screenshot(path=str(target/f'{tab.replace(" ","-")}-{width}.png'),full_page=True)
        evidence['page_map_observed']=headings;evidence['reduced_motion']=await page.evaluate('matchMedia("(prefers-reduced-motion: reduce)").matches')
        await page.get_by_text('Low effects',exact=False).check();assert await page.locator('.app').evaluate('(e)=>e.classList.contains("low")');evidence['low_effects']=True
        evidence['external_attempts']=external;evidence['page_errors']=errors;evidence['http_errors_including_injected']=bad
        assert not external and not errors
        await browser.close()
    (target/'report.json').write_text(json.dumps(evidence,indent=2));print(json.dumps(evidence,indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);p.add_argument('--base-url',default='http://127.0.0.1:8002');a=p.parse_args();asyncio.run(run(a.base_url,a.out))
