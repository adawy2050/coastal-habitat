"""Exercise both-species visibility, hover graphs and cross-species reports."""
import asyncio,json,os
from pathlib import Path
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1];BASE=os.environ.get('ATLAS_QA_URL','http://127.0.0.1:8765/')
async def main():
 errors=[]
 async with async_playwright() as p:
  b=await p.chromium.launch();page=await b.new_page(viewport={'width':1550,'height':1050},reduced_motion='reduce');page.on('pageerror',lambda e:errors.append(str(e)))
  await page.goto(BASE+'kelp/?lang=en&species=japonica&station=JAP_OCC_001080&v=both-hover-r1');await page.wait_for_function("document.documentElement.dataset.mixedReady==='true'&&document.documentElement.dataset.contextReady==='true'",timeout=120000)
  assert await page.evaluate('KelpPortal.combined&&KelpMixed.pointLayer.getLayers().length===2029')
  assert await page.evaluate("Object.keys(KelpMixed.spaces).length===2")
  await page.screenshot(path=str(ROOT/'qa/kelp-mixed-map.png'))
  # Hover real DOM square and verify the preview without opening a report.
  await page.evaluate("()=>{const s=KelpPortal.catalogue.stations.find(s=>s.species==='longissima');KelpPortal.map.setView([s.lat,s.lon],11)}")
  await page.locator('#moeLayer').uncheck();await page.locator('.mixed-station-square').first.hover();await page.wait_for_selector('.kelp-hover .kelp-mini svg');assert not await page.locator('#stationDialog').is_visible();assert 'Individual biomass' in await page.locator('.kelp-hover').inner_text();await page.screenshot(path=str(ROOT/'qa/kelp-point-hover.png'))
  await page.locator('.mixed-station-square').first.click();await page.wait_for_function("document.querySelector('#stationDialog').open&&KelpPortal.state.species==='longissima'");assert await page.locator('#massPlot').is_visible();await page.keyboard.press('Escape')
  await page.locator('#moeLayer').check()
  # Hover a polygon through its Leaflet event path; no detail dialog until click.
  await page.evaluate("()=>{const f=Object.values(KelpPortal.map._layers).find(l=>l.feature?.properties?.polygon_id&&l.options.color==='#8b557e');const p=f.getBounds().getCenter();KelpPortal.map.setView(p,11);f.fire('mouseover',{latlng:p});f.openTooltip(p)}")
  await page.wait_for_selector('.kelp-hover .kelp-mini svg');assert await page.locator('.kelp-hover svg').count()==2;assert not await page.locator('#stationDialog').is_visible();await page.screenshot(path=str(ROOT/'qa/kelp-polygon-hover.png'))
  await page.evaluate("()=>{const f=Object.values(KelpPortal.map._layers).find(l=>l.feature?.properties?.polygon_id&&l.options.color==='#8b557e');f.fire('click')}")
  await page.wait_for_function("document.querySelector('#stationDialog').dataset.view==='area'&&KelpPortal.state.species==='japonica'",timeout=60000);assert await page.locator('#spatialBiomassPlot').is_visible();await page.keyboard.press('Escape')
  await page.locator('#bothSpecies').uncheck();await page.wait_for_function('!KelpPortal.combined');assert await page.evaluate("Object.values(KelpPortal.map._layers).some(l=>l.options.radius===4.2)")
  await page.locator('#bothSpecies').check();await page.wait_for_function('KelpPortal.combined');assert await page.evaluate('KelpPortal.map.hasLayer(KelpMixed.pointLayer)')
  await page.locator('#gridLayer').check();assert await page.evaluate("Object.values(KelpPortal.map._layers).some(l=>l.feature?.properties?.grid_2km_id&&l.options.color==='#267d6f')&&Object.values(KelpPortal.map._layers).some(l=>l.feature?.properties?.grid_2km_id&&l.options.color==='#8b557e')")
  await page.locator('#openStation').click();await page.locator('[data-context-link="stationSources"]').click();await page.evaluate("Promise.all([...document.querySelectorAll('#stationSources img')].map(async i=>{i.loading='eager';await i.decode()}))");assert await page.locator('#stationSources img').count()==6
  await page.keyboard.press('Escape');await page.set_viewport_size({'width':390,'height':844});await page.goto(BASE+'kelp/?lang=ar');await page.wait_for_function("document.documentElement.dataset.mixedReady==='true'",timeout=120000);assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth+2')
  await b.close()
 assert not errors,errors
 (ROOT/'qa/kelp_mixed_browser.json').write_text(json.dumps({'passed':True,'stations':2029,'species':2,'hoverGraphs':True,'crossSpeciesReports':True,'browserErrors':errors},indent=2));print('PASS: both species, hover plots, cross-species reports, layer switches, six photos, mobile Arabic.')
if __name__=='__main__':asyncio.run(main())
