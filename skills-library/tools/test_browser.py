#!/usr/bin/env python3
"""Chromium smoke tests; pip install playwright && playwright install chromium."""
import functools,http.server,threading
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
class Quiet(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*a):pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(ROOT/'docs')))
threading.Thread(target=server.serve_forever,daemon=True).start()
url=f'http://127.0.0.1:{server.server_port}'
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=True)
  page=browser.new_page(viewport={'width':1440,'height':1000})
  errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto(url);page.emulate_media(color_scheme='dark');assert page.evaluate('getComputedStyle(document.body).backgroundColor')=='rgb(255, 255, 255)'
  page.locator('.hero-search input').fill('code-review');page.locator('.hero-search button').click();page.wait_for_selector('.skill-row');assert 'q=code-review' in page.url
  page.locator('#reset').click();total=int(page.locator('#count').inner_text().split(' of ')[1].split()[0].replace(',',''));assert total>0
  page.locator('#q').fill('no-such-guide-xyzz');assert page.locator('.empty').count()==1
  page.locator('#reset').click();page.locator('#collection').select_option('mattpocock');page.locator('#q').fill('code-review');assert page.locator('.skill-row').count()==1
  page.reload();page.wait_for_selector('.skill-row');assert page.locator('.skill-row').count()==1
  page.get_by_role('button',name='View details for',exact=False).click();assert page.locator('#skill-dialog').is_visible();assert page.locator('#detail-license').inner_text()=='MIT';page.keyboard.press('Escape');assert not page.locator('#skill-dialog').is_visible()
  page.locator('.row-actions button').last.click();page.locator('#saved-view').click();assert page.locator('.skill-row').count()==1
  page.reload();page.wait_for_selector('.skill-row');assert page.locator('#saved-count').inner_text()=='1'
  page.locator('#reset').click();page.locator('#sort').select_option('name-desc');names=page.locator('.skill-row h2').all_text_contents();assert names[0]!=names[-1]
  page.locator('#reset').click();page.keyboard.press('/');assert page.locator('#q').evaluate('(e)=>e===document.activeElement');page.locator('#q').fill('planning');page.keyboard.press('Escape');assert page.locator('#q').input_value()==''
  for width in [375,768,1440]:
   page.set_viewport_size({'width':width,'height':900})
   for path in ['/','/skills.html','/api.html']:
    page.goto(url+path)
    if path=='/skills.html':page.wait_for_selector('.skill-row')
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),(width,path)
  page.goto(url+'/skills.html');page.wait_for_selector('.skill-row')
  page.locator('#more').click();assert page.locator('.skill-row').count()==80
  page.route('**/api/v1/skills.json',lambda r:r.fulfill(status=500,body='unavailable'));page.reload();page.wait_for_selector('.empty');assert 'SKILLS.md' in page.locator('.empty').inner_text()
  assert not errors,errors
  browser.close()
 print('PASS browser: homepage search, filtering, URL state, sorting, saved persistence, details, keyboard, pagination, 3 responsive widths, API fallback, light-only rendering; no JS errors')
finally:server.shutdown()
