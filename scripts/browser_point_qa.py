from pathlib import Path
import json
from playwright.sync_api import sync_playwright
import fitz

root=Path(__file__).resolve().parents[1];qa=root/'qa';qa.mkdir(exist_ok=True)
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True)
    page=browser.new_page(viewport={'width':1440,'height':1050})
    errors=[];http=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('response',lambda r:http.append([r.status,r.url]) if r.status>=400 else None)
    page.goto('http://127.0.0.1:8765/?basin=redsea',wait_until='networkidle')
    page.wait_for_function("document.documentElement.dataset.ready==='true'",timeout=60000)
    page.wait_for_function("document.querySelector('#pointProbability').textContent!=='—'")
    page.locator('#outlookScope').select_option('overall')
    page.wait_for_function("document.querySelectorAll('.outlook-card').length===3")
    page.locator('#outlookScope').select_option('ecoregion')
    page.wait_for_function("document.querySelectorAll('.outlook-card').length===9")
    page.locator('#metric').select_option('outlook_probability')
    page.wait_for_function("window.AtlasDebug.state.mapMode==='probability' && document.querySelector('#year').hidden")
    page.locator('#showPointOutlook').click()
    page.wait_for_function("document.querySelectorAll('.outlook-card').length===1")
    assert 'pixel' in page.locator('.outlook-card h3').inner_text().lower()
    page.locator('#pointProbability').screenshot(path=str(qa/'point_probability.png'))
    page.locator('.atlas-layout').screenshot(path=str(qa/'probability_map.png'))
    page.locator('#product').select_option('oisst',force=True)
    page.wait_for_function("document.querySelector('#pointValidationYears').textContent.includes('13 test')")
    assert 'mailto:ahmed.eladawy@jamstec.go.jp'==page.locator('#contact a').first.get_attribute('href')
    with page.expect_download(timeout=60000) as item:
        page.locator('#createReport').click()
    path=qa/'point_report_oisst.pdf';item.value.save_as(str(path))
    doc=fitz.open(path)
    assert 6<=len(doc)<=10,len(doc)
    texts='\n'.join(p.get_text() for p in doc)
    assert 'Observed annual history' in texts and 'Contacts' in texts and 'Brier' in texts
    for i,pdf_page in enumerate(doc):pdf_page.get_pixmap(dpi=100).save(qa/f'point_report_p{i+1}.png')
    page.screenshot(path=str(qa/'desktop_point_update.png'),full_page=True)
    page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(700)
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
    page.screenshot(path=str(qa/'mobile_point_update.png'),full_page=True)
    assert not errors,errors
    assert not http,http
    (qa/'point_browser_results.json').write_text(json.dumps({'passed':True,'pdfPages':len(doc),'pageErrors':errors,'httpErrors':http},indent=2))
    browser.close()
print('PASS: overall/ecoregion/pixel scopes, probability map, point validation, contact links, PDF report and mobile layout.')
