"""Check the light design, local content, motion controls and point PDFs."""
import asyncio,json,os
from pathlib import Path
from playwright.async_api import async_playwright

ROOT=Path(__file__).resolve().parents[1]
BASE=os.environ.get('ATLAS_QA_URL','http://127.0.0.1:8765/')
POINTS=[('egypt',26.73,33.94),('saudi',22.30,38.90),('abudhabi',24.45,54.35),('iran',26.80,56.20),('japan',33.50,135.82),('jeju',33.30,126.50),('philippines',11.50,123.50)]

async def main():
    results=[];errors=[]
    async with async_playwright() as p:
        browser=await p.chromium.launch()
        context=await browser.new_context(viewport={'width':1600,'height':1100},accept_downloads=True,color_scheme='dark')
        await context.add_init_script("localStorage.setItem('atlas-theme','dark')")
        page=await context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
        for name,lat,lon in POINTS:
            await page.goto(f'{BASE}?lang=en&lat={lat}&lon={lon}&product=mur&v=20261101-light-coasts-r1')
            await page.wait_for_function("document.documentElement.dataset.ready==='true'",timeout=90000)
            await page.wait_for_function("document.querySelector('#pointPapers .paper-row')&&document.querySelector('#pointCoastPhotos img')",timeout=30000)
            assert await page.evaluate("document.documentElement.dataset.theme==='light'")
            assert 'Research preview' in await page.title()
            assert 'Under testing' in await page.locator('.site-status').inner_text()
            assert await page.locator('.site-status a').get_attribute('href')=='mailto:ahmed.eladawy@jamstec.go.jp'
            assert await page.locator('.habitat-story').count()==0
            assert await page.locator('#map').evaluate('e=>e.getBoundingClientRect().width>=innerWidth*.97')
            data=await page.evaluate('''async()=>{const s=AtlasUI.snapshot(),area=s.meta.basins.find(b=>b.regions.includes(s.point[3])),sources=await AtlasResources.forPoint(s.state.pixel),photo=AtlasPhotos.forPoint(s.point[1],s.point[0],1,area.id,s.point[2])[0];return {basin:area.id,point:s.point.slice(0,2),photo:photo.photo.id,photoBasin:photo.photo.basin,photoHabitat:photo.photo.habitat,photoAuthor:photo.photo.author,photoDistance:photo.distance,news:sources.news.map(v=>v.id),paperDOIs:sources.papers.map(v=>v.doi),allMatch:sources.news.concat(sources.papers).every(v=>v.basins.includes(area.id)),metadata:sources};}''')
            assert data['photoBasin']==data['basin'] and data['allMatch']
            assert data['news'] and data['paperDOIs'],(name,data)
            results.append({'name':name,**data})
            if name=='egypt':await page.screenshot(path=str(ROOT/'qa/light-coast-map.png'))
            await page.locator('#openPointAnalysis').click()
            await page.get_by_role('button',name='Photos & sources',exact=True).click()
            await page.wait_for_function("[...document.querySelectorAll('#pointCoastPhotos img')].every(i=>i.complete&&i.naturalWidth>0)",timeout=30000)
            await page.wait_for_timeout(450)
            assert await page.locator('#pointCoastPhotos img').evaluate_all('nodes=>nodes.every(e=>e.getBoundingClientRect().width>innerWidth*.2)')
            if name in ['egypt','abudhabi','japan']:
                await page.screenshot(path=str(ROOT/f'qa/light-coast-{name}.png'))
                await page.get_by_role('button',name='Overview',exact=True).click()
                async with page.expect_download(timeout=90000) as event:await page.locator('#createReport').click()
                await (await event.value).save_as(ROOT/f'qa/light-coast-{name}.pdf')
            await page.keyboard.press('Escape')
        by={r['name']:r for r in results}
        for a,b in [('egypt','saudi'),('abudhabi','iran'),('japan','philippines'),('japan','jeju')]:
            assert by[a]['photo']!=by[b]['photo'],(a,b)
            assert by[a]['news']!=by[b]['news'] and by[a]['paperDOIs']!=by[b]['paperDOIs'],(a,b)
        await page.locator('#motionToggle').click();assert await page.evaluate("document.documentElement.dataset.motion==='off'")
        await page.wait_for_timeout(100);assert await page.evaluate('AtlasPresentation.activeAnimations.size===0')
        await page.locator('#resourceScope').select_option('all');await page.locator('#paperList').scroll_into_view_if_needed()
        assert await page.locator('#paperList .paper-row').count()==10
        await page.locator('#papersNext').click();assert await page.locator('#papersPosition').inner_text()=='2 / 5'
        await page.locator('#motionToggle').click();assert await page.evaluate("document.documentElement.dataset.motion==='on'")
        await page.set_viewport_size({'width':390,'height':900});await page.locator('#languageSelect').select_option('ar')
        await page.locator('#openPointAnalysis').click();await page.get_by_role('button',name='الصور والمصادر',exact=True).click();await page.wait_for_timeout(500)
        assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
        assert await page.locator('#pointAnalysis').evaluate('e=>e.scrollWidth<=e.clientWidth+1')
        await page.screenshot(path=str(ROOT/'qa/light-coast-mobile-ar.png'))
        reduced=await browser.new_context(reduced_motion='reduce');rp=await reduced.new_page();await rp.goto(BASE+'?lang=en');await rp.wait_for_function("document.documentElement.dataset.ready==='true'",timeout=90000);assert await rp.evaluate("document.documentElement.dataset.motion==='off'");assert await rp.locator('#motionToggle').is_disabled();await reduced.close()
        assert not errors,errors
        (ROOT/'qa/light-coasts-results.json').write_text(json.dumps({'base':BASE,'passed':True,'points':results,'lightEvenWithOldDarkPreference':True,'pointSourcesDiffer':True,'paperPagesOfTen':True,'motionPauseAndReducedMotion':True,'arabicMobile':True,'browserErrors':errors},indent=2),encoding='utf8')
        await browser.close()
    print('PASS: seven coasts have local photos/news/papers; light theme, testing/email labels, three point PDFs, motion controls, reduced motion and Arabic mobile.')

if __name__=='__main__':asyncio.run(main())
