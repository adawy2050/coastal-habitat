"""Browser checks against the local preview; no credentials or external services."""
from pathlib import Path
import json
import numpy as np
from playwright.sync_api import sync_playwright

root = Path(__file__).resolve().parents[1]
qa = root / 'qa'
qa.mkdir(exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe', headless=True)
    page = browser.new_page(viewport={'width': 1440, 'height': 1100}, device_scale_factor=1)
    errors, failures = [], []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.on('response', lambda r: failures.append([r.status,r.url]) if r.status >= 400 else None)
    page.goto('http://127.0.0.1:8765/?basin=redsea', wait_until='networkidle')
    page.wait_for_function("document.documentElement.dataset.ready === 'true'", timeout=60000)
    page.screenshot(path=str(qa/'desktop.png'), full_page=True)
    assert page.locator('#pixelValue').inner_text() != '—'
    assert page.locator('#modelR2').inner_text() != '—'
    assert page.locator('.outlook-card').count() == 9
    assert '2026' in page.locator('#outlookSubtitle').inner_text()
    assert 'satellite' == page.locator('#basemap').input_value()
    page.locator('#filtersOpen').click()
    page.locator('#showPixels').uncheck()
    page.locator('#pixelOpacity').fill('0.4')
    page.locator('input[name="coverage"][value="coral"]').uncheck()
    page.locator('input[name="coverage"][value="coral"]').check()
    page.locator('#showPixels').check(force=True)
    page.locator('#filtersClose').click()
    page.locator('#outlookRecord').select_option('OISST')
    assert page.locator('.outlook-card').count() == 9
    page.locator('.outlook-card details').first.locator('summary').click()
    page.locator('#outlook').screenshot(path=str(qa/'outlook.png'))
    with page.expect_download() as info:
        page.locator('#downloadOutlook').click()
    info.value.save_as(str(qa/'outlook_download.json'))
    initial = page.locator('#pixelTitle').inner_text()
    page.locator('#pinPixel').click()
    page.locator('#locate').fill('15.8, 41.5')
    page.locator('#locateForm button').click()
    page.wait_for_timeout(800)
    assert page.locator('#pixelTitle').inner_text() != initial
    assert page.locator('.pin').count() == 1
    with page.expect_download() as info:
        page.locator('#downloadPixel').click()
    info.value.save_as(str(qa/'selected_pixel.csv'))
    page.locator('#product').select_option('oisst',force=True)
    page.wait_for_function("window.AtlasDebug.state.product==='oisst' && document.querySelector('#modelSample').textContent.includes('44 complete years')")
    page.locator('#metric').select_option('mhw_cumulative_intensity')
    page.wait_for_timeout(1000)
    page.locator('#benchmark').select_option('sst')
    page.locator('#lag').select_option('2')
    page.wait_for_timeout(800)
    assert '42 complete years' in page.locator('#modelSample').inner_text()
    actual = page.evaluate('window.AtlasDebug.model')
    target = np.array([r['observed'] for r in actual['rows']])
    design = np.array([[1, r['reference'], *r['indices']] for r in actual['rows']])
    expected = design @ np.linalg.lstsq(design, target, rcond=None)[0]
    assert np.max(np.abs(expected - actual['model']['pred'])) < 1e-7
    assert abs(sum(actual['model']['shares'])-actual['model']['r2']) < 1e-10
    (qa/'actual_model_check.json').write_text(json.dumps({'maxPredictionDifferenceVsNumpy':float(np.max(np.abs(expected-actual['model']['pred']))),'sumShares':sum(actual['model']['shares']),'r2':actual['model']['r2']}))
    page.locator('#pairedIndex').select_option('localSst')
    page.wait_for_timeout(250)
    assert 'OISST' in page.locator('#pairedTitle').inner_text()
    page.locator('#climateSource').select_option('study')
    page.locator('#climateStep').select_option('monthly')
    page.locator('#climateScale').select_option('raw')
    for checkbox in page.locator('#indexChips input').all():
        checkbox.check()
    with page.expect_download() as info:
        page.locator('#downloadClimate').click()
    info.value.save_as(str(qa/'climate.csv'))
    with page.expect_download() as info:
        page.locator('#downloadModel').click()
    info.value.save_as(str(qa/'model.csv'))
    page.locator('#methodsOpen').click()
    assert page.locator('#methodsDialog').is_visible()
    page.keyboard.press('Escape')
    page.locator('#product').select_option('mur',force=True)
    page.locator('#metric').select_option('mhw_days')
    page.locator('#lag').select_option('0')
    page.locator('#benchmark').select_option('trend')
    page.wait_for_timeout(1000)
    page.locator('#play').click()
    page.wait_for_timeout(1700)
    assert int(page.locator('#yearLabel').inner_text()) < 2025
    page.locator('#play').click()
    page.locator('#year').fill('2025')
    page.locator('#year').dispatch_event('input')
    assert page.locator('#climateYearLabel').inner_text() == 'Climate in 2025'
    with page.expect_download() as info:
        page.locator('#mapDownload').click()
    info.value.save_as(str(qa/'map_export.png'))
    page.locator('#connections').screenshot(path=str(qa/'connections.png'))
    page.set_viewport_size({'width':390,'height':844})
    page.wait_for_timeout(1000)
    page.screenshot(path=str(qa/'mobile.png'),full_page=True)
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1')
    assert not errors, errors
    assert not failures, failures
    (qa/'browser_results.json').write_text(json.dumps({'passed':True,'pageErrors':errors,'httpErrors':failures,'checks':[
        'Initial real-data load','Cell search and pin comparison','All-metric pixel CSV',
        'OISST historical range','Two-year lead complete-case filtering','Local SST covariate',
        'Monthly climate chart/export','Model export','Methods dialog','Annual playback','390px responsive layout']},indent=2))
    browser.close()
print('BROWSER QA PASSED')
