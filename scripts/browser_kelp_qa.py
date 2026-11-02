"""Exercise the home, both kelp species, station records and legacy atlas links."""
import asyncio,json,os
from pathlib import Path
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1];BASE=os.environ.get('ATLAS_QA_URL','http://127.0.0.1:8765/')

async def main():
 errors=[];result={}
 async with async_playwright() as p:
  browser=await p.chromium.launch();page=await browser.new_page(viewport={'width':1600,'height':1100},reduced_motion='reduce',accept_downloads=True)
  page.on('pageerror',lambda e:errors.append(str(e)))
  await page.goto(BASE+'?lang=en');assert await page.locator('.portal-row').count()==3
  assert await page.locator('.portal-row.pending a').count()==0
  assert 'Under construction' in await page.locator('.portal-row.pending').inner_text()
  await page.screenshot(path=str(ROOT/'qa/observatory-home.png'),full_page=True)
  await page.locator('a[href*="kelp/"]').click()
  await page.wait_for_function("document.documentElement.dataset.ready==='true'",timeout=90000)
  assert await page.locator('#station option').count()==99
  data=await page.evaluate("({state:KelpPortal.state,counts:Object.fromEntries(Object.entries(KelpPortal.catalogue.species).map(([k,v])=>[k,v.stations])),records:Object.fromEntries(Object.entries(KelpPortal.records).map(([k,v])=>[k,[v.monthly.dates[0],v.monthly.dates.at(-1),v.monthly.dates.length]]))})")
  assert data['counts']=={'longissima':99,'japonica':1930}
  assert data['records']['historical']==['1996-01-15','2020-12-15',300]
  assert data['records']['ssp126']==['2021-01-15','2100-12-15',960]
  assert data['records']['ssp585']==data['records']['ssp126']
  await page.wait_for_function("document.documentElement.dataset.shorelineReady==='true'",timeout=60000)
  await page.wait_for_function("document.querySelectorAll('#kelpMap img.leaflet-tile-loaded').length>0",timeout=30000)
  result['longissima']=data
  await page.screenshot(path=str(ROOT/'qa/kelp-map-longissima.png'))
  await page.locator('#openStation').click();await page.wait_for_function("document.querySelector('#massPlot').data?.length===3")
  await page.screenshot(path=str(ROOT/'qa/kelp-longissima-station.png'))
  await page.locator('#budgetRecord').select_option('ssp585')
  await page.wait_for_function("document.querySelector('#budgetPlot').data[0].x.at(-1).startsWith('2100')")
  await page.locator('#budgetRecord').select_option('historical')
  await page.locator('#seasonPeriod').select_option('late')
  assert await page.evaluate("document.querySelector('#seasonPlot').data.length===6")
  assert await page.evaluate("document.querySelector('#factorsPlot').data.length===8")
  await page.locator('#seasonPanel').evaluate('(e)=>e.scrollIntoView({block:"start"})')
  await page.screenshot(path=str(ROOT/'qa/kelp-future-factors.png'))
  async with page.expect_download() as download:await page.locator('#downloadStation').click()
  await (await download.value).save_as(str(ROOT/'qa/kelp-longissima.csv'))
  await page.keyboard.press('Escape')
  await page.locator('#scenario').select_option('ssp585');await page.locator('#mapYear').fill('2100');await page.locator('#mapYear').dispatch_event('input')
  await page.wait_for_function('KelpPortal.state.year===2100')
  await page.locator('#species').select_option('japonica')
  await page.wait_for_function("KelpPortal.state.species==='japonica'&&Object.keys(KelpPortal.records).join(',')==='historical'")
  assert await page.locator('#station option').count()==1930
  assert await page.locator('#scenario option').count()==1
  assert not await page.locator('#futureCurves').is_enabled()
  await page.locator('#station').select_option('JAP_OCC_001019')
  await page.wait_for_function("document.querySelector('#dialogTitle').textContent.includes('JAP_OCC_001019')&&document.querySelector('#densityPlot').data?.length===2")
  assert await page.locator('#densityPanel').is_visible()
  assert await page.evaluate("KelpPortal.records.historical.monthly.dates.length===360")
  assert await page.evaluate("document.querySelector('#factorsPlot').data.length===3")
  assert await page.evaluate("document.querySelector('#massPlot')._fullLayout.width>document.querySelector('#massPlot').clientWidth-10")
  await page.screenshot(path=str(ROOT/'qa/kelp-japonica-station.png'))
  await page.locator('#densityPanel').evaluate('(e)=>e.scrollIntoView({block:"start"})')
  await page.screenshot(path=str(ROOT/'qa/kelp-japonica-density.png'))
  result['japonica']=await page.evaluate('({state:KelpPortal.state,first:KelpPortal.records.historical.monthly.dates[0],last:KelpPortal.records.historical.monthly.dates.at(-1)})')
  await page.emulate_media(media='print');assert await page.locator('#stationDialog').is_visible();assert not await page.locator('.dialog-nav').is_visible();await page.emulate_media(media='screen')
  await page.keyboard.press('Escape')
  for lang in ['ar','ja']:
   await page.set_viewport_size({'width':390,'height':844})
   await page.goto(BASE+'kelp/?lang='+lang+'&species=japonica&station=JAP_OCC_000033')
   await page.wait_for_function("document.documentElement.dataset.ready==='true'",timeout=90000)
   assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
   await page.locator('#openStation').click();await page.screenshot(path=str(ROOT/f'qa/kelp-mobile-{lang}.png'))
   assert await page.evaluate('document.querySelector("#stationDialog").scrollWidth<=innerWidth+1')
   await page.keyboard.press('Escape')
   await page.goto(BASE+'?lang='+lang);assert await page.locator('.portal-row').count()==3
   assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
  await page.set_viewport_size({'width':1600,'height':1100})
  await page.goto(BASE+'?lang=en&lat=32.03&lon=128.38&product=oisst&variable=mhw_days#explore')
  await page.wait_for_function("document.documentElement.dataset.ready==='true'",timeout=90000)
  assert 'heatwaves.html' in page.url
  assert await page.locator('.study-coverage-box').count()==3
  result['legacyAtlasLinks']=True
  assert not errors,errors
  result.update(passed=True,browserErrors=errors)
  (ROOT/'qa/kelp_browser_results.json').write_text(json.dumps(result,indent=2))
  await browser.close();print('PASS: home navigation, both kelp species, 2,029 stations, future factors, point CSV, print layout, Arabic/Japanese mobile, and legacy atlas links.')

if __name__=='__main__':asyncio.run(main())
