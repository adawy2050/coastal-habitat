"""Check final study outlines and marine-proximity legend across map views."""
import asyncio,json,os
from pathlib import Path
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1]
BASE=os.environ.get('ATLAS_QA_URL','http://127.0.0.1:8765/')

async def main():
    errors=[];checks=[]
    async with async_playwright() as p:
        browser=await p.chromium.launch();page=await browser.new_page(viewport={'width':1600,'height':1100},reduced_motion='reduce')
        page.on('pageerror',lambda e:errors.append(str(e)))
        await page.goto(BASE+'?lang=en&lat=32.03&lon=128.38&product=oisst&v=20261101-final-coverage-r1')
        await page.wait_for_function('window.AtlasStudyCoverage?.outlines.length===3',timeout=90000)
        assert await page.locator('input[name="habitat"][value="4"]').locator('..').inner_text()=='Mangrove (near)'
        assert await page.locator('input[name="coverage"][value="mangrove"]').locator('..').inner_text()=='Mangroves (near)'
        assert not await page.locator('input[name="habitat"][value="2"]').is_checked()
        assert not await page.locator('input[name="coverage"][value="seagrass"]').is_checked()
        await page.evaluate('AtlasUI.map.fitBounds(L.latLngBounds(AtlasUI.snapshot().meta.bounds),{animate:false})')
        await page.locator('#map').scroll_into_view_if_needed()
        for mode in ['blend','coastline','satellite']:
            await page.locator('#filtersOpen').click()
            await page.locator('#basemap').select_option(mode)
            await page.locator('#filtersClose').click()
            data=await page.evaluate('AtlasStudyCoverage.outlines.map(v=>({id:v.id,visible:AtlasUI.map.hasLayer(v.layer),fill:v.layer.options.fill,interactive:v.layer.options.interactive,dash:v.layer.options.dashArray,bounds:v.layer.getBounds().toBBoxString()}))')
            assert len(data)==3 and all(d['visible'] and not d['fill'] and not d['interactive'] and d['dash']=='1 7' for d in data)
            await page.wait_for_function("document.querySelectorAll('.study-coverage-box').length===3")
            await page.screenshot(path=str(ROOT/f'qa/final-map-{mode}.png'))
            checks.append({'basemap':mode,'outlines':data})
        await page.locator('#filtersOpen').click()
        await page.locator('#basemap').select_option('blend')
        await page.locator('#filtersClose').click()
        for basin in ['redsea','gulf','eastasia']:
            await page.locator('#basin').select_option(basin)
            assert await page.locator('.study-coverage-box').count()==3
        await page.locator('#basin').select_option('all')
        await page.locator('#openPointAnalysis').click()
        await page.locator('#outlookCombinations').evaluate('(e)=>e.scrollIntoView({block:"start"})')
        await page.wait_for_function("document.querySelectorAll('#combinationRows tr').length===12")
        await page.screenshot(path=str(ROOT/'qa/final-point-view.png'))
        await page.keyboard.press('Escape')
        for lang in ['ar','ja']:
            await page.set_viewport_size({'width':390,'height':844})
            await page.goto(BASE+f'?lang={lang}&lat=26.73&lon=33.94&product=mur&v=20261101-final-coverage-r1')
            await page.wait_for_function('window.AtlasStudyCoverage?.outlines.length===3',timeout=90000)
            text=await page.locator('input[name="habitat"][value="4"]').locator('..').inner_text()
            assert '(' in text and ')' in text and 'near' not in text
            await page.locator('#map').scroll_into_view_if_needed()
            assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
            await page.screenshot(path=str(ROOT/f'qa/final-map-mobile-{lang}.png'))
        assert not errors,errors
        (ROOT/'qa/final_coverage_browser.json').write_text(json.dumps({'passed':True,'checks':checks,'browserErrors':errors,'nearLabels':['en','ar','ja'],'defaultSeagrassOff':True},indent=2))
        await browser.close();print('PASS: three nonblocking dotted study bounds on every basemap/filter, translated near labels, mobile layout, point comparisons, no browser errors.')

if __name__=='__main__':asyncio.run(main())
