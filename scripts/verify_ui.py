"""Real Chrome controls, exports, offline routing, fallback and fresh-session checks."""
import asyncio
import json
import csv
from pathlib import Path
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1]

async def main():
    evidence={};errors=[];external=[];bad=[]
    async with async_playwright() as p:
        browser=await p.chromium.launch(channel='chrome',headless=True,args=['--autoplay-policy=no-user-gesture-required'])
        context=await browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce',accept_downloads=True)
        invalid_model=False
        async def route(r):
            if not r.request.url.startswith('http://127.0.0.1:8000'):
                external.append(r.request.url);await r.abort()
            elif invalid_model and r.request.url.endswith('/api/models/current'):
                await r.fulfill(status=200,content_type='application/json',body='{"schema":"invalid","trees":[]}')
            else:await r.continue_()
        await context.route('**/*',route)
        page=await context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('response',lambda r:bad.append({'url':r.url,'status':r.status}) if r.status>=400 else None)
        await page.goto('http://127.0.0.1:8000');await page.wait_for_function('window.stallguard')
        await page.get_by_role('button',name='Compare Sessions').click()
        boxes=page.locator('.sessionlist input:not(:disabled)')
        assert await boxes.count()>=2
        await boxes.nth(0).check();await boxes.nth(1).check()
        await page.get_by_role('button',name='↓ Summary CSV').wait_for()
        async with page.expect_download() as info:await page.get_by_role('button',name='↓ Summary CSV').click()
        dl=await info.value
        evidence['comparison_csv']=dl.suggested_filename
        csvrows=list(csv.reader(Path(await dl.path()).read_text().splitlines()))
        assert len(csvrows)==3 and all(len(row)==len(csvrows[0]) for row in csvrows)
        async with page.expect_download() as info:await page.get_by_role('button',name='↓ Comparison JSON').click()
        dl=await info.value;evidence['comparison_json']=dl.suggested_filename
        assert len(json.loads(Path(await dl.path()).read_text()))==2
        await page.get_by_role('button',name='How It Works').click()
        assert await page.get_by_text('Observe. Forecast. Adapt. Repeat.').is_visible()
        await page.get_by_role('button',name='Playback Lab').click()
        await page.get_by_text('Low effects',exact=False).check()
        evidence['low_effects']=await page.locator('.app').evaluate('(e)=>e.classList.contains("low")')
        evidence['reduced_motion']=await page.evaluate('matchMedia("(prefers-reduced-motion: reduce)").matches')
        # Deliberately corrupt only model loading; actual media remains unmodified.
        invalid_model=True
        await page.locator('select').nth(0).select_option('ml')
        await page.get_by_role('button',name='Start new session').click()
        await page.wait_for_function('document.querySelector("video").currentTime>3',timeout=30000)
        fallback=await page.evaluate('window.stallguard.snapshot.predictor')
        assert 'fallback' in fallback,evidence
        evidence['invalid_model_predictor']=fallback
        sid1=await page.evaluate('window.stallguard.sid')
        await page.get_by_role('button',name='Stop & save').click()
        await page.get_by_text('Session saved',exact=True).wait_for()
        invalid_model=False
        await page.get_by_role('button',name='Start new session').click()
        await page.wait_for_function('document.querySelector("video").currentTime>3',timeout=30000)
        sid2=await page.evaluate('window.stallguard.sid');assert sid1!=sid2
        await page.wait_for_function('window.stallguard.snapshot.predictor==="random forest"',timeout=30000)
        await page.get_by_role('button',name='Stop & save').click();await page.get_by_text('Session saved',exact=True).wait_for()
        for sid in [sid1,sid2]:
            data=await (await context.request.get(f'http://127.0.0.1:8000/api/sessions/{sid}/export')).json()
            assert data['delivery'] and all(d['bytes']>0 for d in data['delivery'])
        evidence['fresh_session_ids']=[sid1,sid2];evidence['fresh_deliveries_verified']=True
        async with page.expect_download() as info:await page.get_by_role('button',name='Export JSON').click()
        dl=await info.value;evidence['session_export']=dl.suggested_filename
        assert json.loads(Path(await dl.path()).read_text())['meta']['id']==sid2
        out=ROOT/'data/results/screenshots';out.mkdir(exist_ok=True)
        for width,height,name in [(1440,1000,'verified-desktop.png'),(390,844,'verified-mobile.png')]:
            await page.set_viewport_size({'width':width,'height':height})
            assert not await page.evaluate('document.documentElement.scrollWidth>innerWidth')
            await page.screenshot(path=str(out/name),full_page=True)
        evidence['responsive_overflow']=False;evidence['page_errors']=errors;evidence['external_attempts']=external;evidence['bad_core_responses']=bad
        assert not errors and not external and not bad
        await browser.close()
    (ROOT/'data/results/ui-verification.json').write_text(json.dumps(evidence,indent=2));print(json.dumps(evidence,indent=2))
if __name__=='__main__':asyncio.run(main())
