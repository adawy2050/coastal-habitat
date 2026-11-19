"""Check polygon totals, visual stacking, point-first navigation and reports."""
import asyncio,json,os
from pathlib import Path
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1];BASE=os.environ.get('ATLAS_QA_URL','http://127.0.0.1:8765/')
async def main():
 errors=[];result={}
 async with async_playwright() as p:
  browser=await p.chromium.launch();page=await browser.new_page(viewport={'width':1550,'height':1050},reduced_motion='reduce')
  page.on('pageerror',lambda e:errors.append(str(e)))
  for species,station in [('longissima','303833'),('japonica','JAP_OCC_000001')]:
   await page.goto(BASE+f'kelp/?lang=en&species={species}&station={station}&v=polygons-r1')
   await page.wait_for_function("document.documentElement.dataset.contextReady==='true'",timeout=120000)
   assert await page.evaluate("+KelpPortal.map.getPane('kelpHabitat').style.zIndex>400")
   await page.locator('#openStation').click();await page.locator('[data-context-link="historicalContext"]').click()
   await page.keyboard.press('Escape');await page.locator('#openStation').click()
   assert await page.locator('#stationDialog').get_attribute('data-view')=='point'
   assert await page.locator('#massPlot').is_visible()
   assert await page.evaluate("document.querySelector('#stationDialog .dialog-body').scrollTop<5")
   await page.keyboard.press('Escape')
   poly=await page.evaluate("Object.keys(KelpContext.spatial.polygons)[0]")
   await page.evaluate("id=>KelpContext.openArea('polygon:'+id)",poly)
   await page.wait_for_function("document.querySelector('#stationDialog').dataset.view==='area'")
   assert not await page.locator('#historyPanel').is_visible()
   assert await page.locator('#spatialBiomassPlot').is_visible()
   data=await page.evaluate("({id:KelpContext.selectedArea,standing:document.querySelector('#spatialBiomassPlot').data[0].y,erosion:document.querySelector('#spatialPlot').data[0].y,expected:KelpContext.spatial.polygons[KelpContext.selectedArea.slice(8)].series,panels:[...document.querySelectorAll('#stationDialog .figure-panel')].filter(e=>getComputedStyle(e).display!=='none').map(e=>e.id)})")
   assert all(abs(v-e/1e6)<1e-10 for v,e in zip(data['standing'],data['expected']['standing']))
   assert all(abs(v-e/1e6)<1e-10 for v,e in zip(data['erosion'],data['expected']['erosion']))
   await page.screenshot(path=str(ROOT/f'qa/kelp-{species}-polygon-results.png'))
   await page.emulate_media(media='print');await page.evaluate('KelpContext.prepareReport()');await page.pdf(path=str(ROOT/f'qa/kelp-{species}-polygon-report.pdf'),format='A4',print_background=True,margin={'top':'12mm','bottom':'12mm','left':'10mm','right':'10mm'});await page.emulate_media(media='screen')
   await page.keyboard.press('Escape');await page.locator('#openStation').click();assert await page.locator('#historyPanel').is_visible();assert await page.evaluate("document.querySelector('#stationDialog .dialog-body').scrollTop<5")
   await page.keyboard.press('Escape')
   # Use the rendered Leaflet polygon event handler, not only the helper API.
   await page.evaluate("()=>{const l=Object.values(KelpPortal.map._layers).find(l=>l.feature?.properties?.polygon_id);l.fire('click');}")
   await page.wait_for_function("document.querySelector('#stationDialog').dataset.view==='area'")
   result[species]={'polygon':poly,'years':len(data['standing']),'stockAndFluxMatched':True}
   await page.keyboard.press('Escape')
  for lang in ['ar','ja']:
   await page.goto(BASE+'kelp/?lang='+lang+'&species=longissima');await page.wait_for_function("document.documentElement.dataset.contextReady==='true'",timeout=120000);await page.set_viewport_size({'width':390,'height':844});await page.evaluate("KelpContext.openArea('polygon:'+Object.keys(KelpContext.spatial.polygons)[0])");await page.wait_for_function("document.querySelector('#spatialBiomassPlot')._fullLayout.width<=document.querySelector('#spatialBiomassPlot').clientWidth+2");await page.screenshot(path=str(ROOT/f'qa/kelp-polygon-mobile-{lang}.png'));assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth+2');await page.keyboard.press('Escape')
  await browser.close()
 assert not errors,errors
 (ROOT/'qa/kelp_polygon_browser.json').write_text(json.dumps({'passed':True,'result':result},indent=2));print(json.dumps(result,indent=2))
if __name__=='__main__':asyncio.run(main())
