"""Check historical scope, native spatial series, source photos and report content."""
import asyncio,json,os
from pathlib import Path
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1];BASE=os.environ.get('ATLAS_QA_URL','http://127.0.0.1:8765/')
async def main():
 errors=[];results={}
 async with async_playwright() as p:
  browser=await p.chromium.launch();page=await browser.new_page(viewport={'width':1600,'height':1100},reduced_motion='reduce')
  page.on('pageerror',lambda e:errors.append(str(e)))
  for species,station in [('longissima','303833'),('japonica','JAP_OCC_000001')]:
   await page.goto(BASE+f'kelp/?lang=en&species={species}&station={station}&v=context-qa')
   await page.wait_for_function("document.documentElement.dataset.contextReady==='true'",timeout=180000)
   await page.locator('#openStation').click();await page.wait_for_function("document.querySelector('#exposurePlot').data?.length===2")
   data=await page.evaluate("({heat:document.querySelector('#exposurePlot').data.map(t=>[t.x[0],t.x.at(-1)]),years:KelpContext.spatial.years,grids:Object.keys(KelpContext.spatial.records).length,lowYear:KelpContext.year,lowRows:document.querySelectorAll('#lowYears tr').length})")
   assert all(v[-1]<=2020 for v in data['heat']);assert data['lowRows']==7
   assert data['years'][-1]==2020;assert data['grids']>50
   await page.locator('[data-context-link="historicalContext"]').click();await page.screenshot(path=str(ROOT/f'qa/kelp-{species}-historical-context.png'))
   await page.locator('#diagnosticYear').select_option('2019');assert '2019' in await page.locator('#diagnosticSummary').inner_text()
   await page.locator('#heatProduct').select_option('mur');await page.wait_for_function("document.documentElement.dataset.contextReady==='true'&&KelpContext.exposure.product==='mur'")
   assert await page.evaluate("document.querySelector('#exposurePlot').data[1].x[0]")==2003
   await page.locator('#gridSelect').select_option(index=1);await page.wait_for_function("document.querySelector('#spatialPlot').data[0].y.length===KelpContext.spatial.years.length")
   await page.locator('[data-context-link="stationSources"]').click();await page.locator('#stationSources img').first.scroll_into_view_if_needed()
   await page.evaluate("Promise.all([...document.querySelectorAll('#stationSources img')].map(async i=>{i.loading='eager';await i.decode()}))")
   assert await page.evaluate("[...document.querySelectorAll('#stationSources img')].every(i=>i.naturalWidth>0)")
   await page.screenshot(path=str(ROOT/f'qa/kelp-{species}-sources.png'))
   assert await page.locator('#stationSources .context-list li').count()>=5
   await page.emulate_media(media='print');await page.evaluate('KelpContext.prepareReport()');await page.wait_for_timeout(600)
   await page.pdf(path=str(ROOT/f'qa/kelp-{species}-context-report.pdf'),format='A4',print_background=True,margin={'top':'12mm','bottom':'12mm','left':'10mm','right':'10mm'})
   await page.emulate_media(media='screen');await page.keyboard.press('Escape')
   if species=='longissima':
    await page.locator('#scenario').select_option('ssp585');await page.locator('#openStation').click();await page.locator('#seasonPeriod').select_option('late');assert await page.evaluate("document.querySelector('#factorsPlot').data.every(t=>t.name.endsWith('1996–2020'))");await page.keyboard.press('Escape')
   await page.locator('#gridLayer').check();assert await page.evaluate("KelpPortal.map.hasLayer([...Object.values(KelpPortal.map._layers)].find(l=>l.feature?.properties?.grid_2km_id))")
   results[species]=data
  for lang in ['ar','ja']:
   await page.goto(BASE+'kelp/?lang='+lang+'&species=japonica');await page.wait_for_function("document.documentElement.dataset.contextReady==='true'",timeout=120000)
   await page.set_viewport_size({'width':390,'height':844});await page.locator('#openStation').click();await page.locator('[data-context-link="historicalContext"]').click();await page.wait_for_function("document.querySelector('#exposurePlot')._fullLayout.width<=document.querySelector('#exposurePlot').clientWidth+2");await page.screenshot(path=str(ROOT/f'qa/kelp-context-mobile-{lang}.png'))
   assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth+2');await page.keyboard.press('Escape')
  await browser.close()
 assert not errors,errors
 (ROOT/'qa/kelp_context_browser.json').write_text(json.dumps({'passed':True,'results':results,'errors':errors},indent=2))
 print(json.dumps(results,indent=2))
if __name__=='__main__':asyncio.run(main())
