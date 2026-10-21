"""Verify the professor's exact three-run selection against finished evidence."""
import argparse,asyncio,json,csv
from pathlib import Path
from playwright.async_api import async_playwright
async def main(base,out):
 out=Path(out);target=out/'professor-view';target.mkdir(exist_ok=False);runs=json.loads((out/'matrix/runs.json').read_text());selected=[r for r in runs if r['profile']=='fluctuate' and r['seed']==502];assert len(selected)==3
 errors=[];external=[]
 async with async_playwright() as p:
  b=await p.chromium.launch(channel='chrome',headless=True);c=await b.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce',accept_downloads=True)
  async def route(r):
   if r.request.url.startswith(base+'/'):await r.continue_()
   else:external.append(r.request.url);await r.abort()
  await c.route('**/*',route);page=await c.new_page();page.on('pageerror',lambda e:errors.append(str(e)));await page.goto(base);await page.get_by_role('button',name='Compare Sessions').click()
  for r in selected:await page.locator('.sessionlist label').filter(has_text=r['id'][:8]).locator('input').check()
  await page.wait_for_function('document.querySelectorAll(".compare table thead th").length===4')
  assert await page.locator('.warning').count()==0
  async with page.expect_download() as info:await page.get_by_role('button',name='↓ Summary CSV').click()
  dl=await info.value;rows=list(csv.reader(Path(await dl.path()).read_text().splitlines()));assert len(rows)==4 and len({len(r) for r in rows})==1
  await dl.save_as(str(target/'selected-summary.csv'))
  async with page.expect_download() as info:await page.get_by_role('button',name='↓ Comparison JSON').click()
  dl=await info.value;data=json.loads(Path(await dl.path()).read_text());assert {r['meta']['id'] for r in data}=={r['id'] for r in selected};await dl.save_as(str(target/'selected-comparison.json'))
  for width,height in [(1440,1000),(390,844)]:
   await page.set_viewport_size({'width':width,'height':height});assert not await page.evaluate('document.documentElement.scrollWidth>innerWidth');await page.screenshot(path=str(target/f'Compare-{width}.png'),full_page=True)
  assert not errors and not external;await b.close()
 report={'selected_ids':[r['id'] for r in selected],'profile':'fluctuate','seed':502,'no_incompatibility_warning':True,'csv_rows_including_header':len(rows),'json_sessions':len(data),'page_errors':errors,'external_attempts':external};(target/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',required=True);p.add_argument('--base-url',default='http://127.0.0.1:8002');a=p.parse_args();asyncio.run(main(a.base_url,a.out))
