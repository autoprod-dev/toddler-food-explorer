import json, sys, os
from playwright.sync_api import sync_playwright, expect
URL = 'file://' + os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'index.html'))
SHOTS = '/workspace/food-explorer-shots'
errors = []; results = []
def check(name, cond, detail=''):
    results.append((name, bool(cond), detail)); print(('PASS' if cond else 'FAIL'), name, detail)


def fullshot(pg, path):
    vw = pg.viewport_size
    hgt = pg.evaluate('document.documentElement.scrollHeight')
    pg.set_viewport_size({'width':vw['width'],'height':max(hgt, vw['height'])})
    pg.wait_for_timeout(400); pg.screenshot(path=path)
    pg.set_viewport_size(vw)

def log(page, food, result, date=None, pick_ac=False, attrs=None, notes=''):
    page.click('#nav button[data-view=log]')
    if date: page.fill('#fDate', date)
    if pick_ac:
        page.fill('#fFood', '')
        page.type('#fFood', food[:3])
        page.click(f'#acList button:has-text("{food}")')
    else:
        page.fill('#fFood', food)
        page.locator('#fNotes').focus()  # blur -> auto-fill attributes for exact match
    if attrs:
        for grp, v in attrs.items(): page.click(f'#{grp} [data-v={v}]')
    page.click(f'#fResult [data-v={result}]')
    if notes: page.fill('#fNotes', notes)
    page.click('#saveBtn')
    err = page.inner_text('#formErr')
    assert not err, f'form error for {food}: {err}'

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={'width':390,'height':844}, locale='en-AU', timezone_id='Australia/Sydney', device_scale_factor=2, is_mobile=True, has_touch=True, accept_downloads=True)
    page = ctx.new_page()
    page.on('console', lambda m: errors.append(f'console.{m.type}: {m.text}') if m.type in ('error','warning') else None)
    page.on('pageerror', lambda e: errors.append(f'pageerror: {e}'))
    page.on('dialog', lambda d: d.accept())
    page.goto(URL)
    check('intro modal on first launch', page.locator('.modal').is_visible() and 'not medical advice' in page.inner_text('.modal'))
    page.wait_for_timeout(350); page.screenshot(path=f'{SHOTS}/phone-0-first-launch.png')
    page.click('.modal button')
    check('footer disclaimer visible', page.locator('#footerNote').is_visible() and 'This is a tracker, not medical advice' in page.inner_text('#footerNote'))
    check('date defaults to today', page.input_value('#fDate') == '2026-09-29', page.input_value('#fDate'))
    check('generic header', page.inner_text('h1')=='Toddler Food Explorer' and page.title()=='Toddler Food Explorer' and 'one little try at a time' in page.inner_text('#tagline'), page.inner_text('#tagline'))
    # validation
    page.click('#saveBtn'); check('validation message', 'food name' in page.inner_text('#formErr'))
    # autocomplete + auto-fill
    page.type('#fFood', 'toa')
    ac = page.inner_text('#acList'); check('autocomplete shows library foods', 'Toast' in ac and 'Vegemite toast' in ac, ac.replace('\n',' | '))
    page.click('#acList button:has-text("Toast")')
    check('attrs autofilled from library', page.locator('#fTexture .chip.on').inner_text()=='Crunchy' and 'Beige' in page.locator('#fColour .chip.on').inner_text())
    page.fill('#fFood','')
    # hazard caution
    page.fill('#fFood','Grapes (quartered)'); check('caution for grapes', 'quarter' in page.inner_text('#foodCaution').lower())
    page.fill('#fFood','whole grapes'); check('caution for whole grapes', 'choking' in page.inner_text('#foodCaution').lower())
    page.fill('#fFood','Carrot, raw (grated)'); check('caution for raw carrot', 'grate' in page.inner_text('#foodCaution').lower())
    page.fill('#fFood','')
    # Log several foods
    log(page, 'Toast', 'ate', pick_ac=True, notes='With butter')
    log(page, 'Rice crackers', 'ate', date='2026-09-28')
    log(page, 'Banana', 'touched', date='2026-09-29')
    log(page, 'Broccoli, steamed', 'refused', date='2026-09-29')
    log(page, 'Weet-Bix', 'refused', date='2026-09-24')
    log(page, 'Pumpkin mash', 'touched', date='2026-09-28')
    check('date hint shown for past date', page.locator('#dateHint').is_visible() and 'Mon 28 Sep' in page.inner_text('#dateHint'))
    page.click('#useToday'); check('use today resets date', page.input_value('#fDate')=='2026-09-29' and not page.locator('#dateHint').is_visible())
    log(page, "Homemade cheesy scroll", 'ate', date='2026-09-29', attrs={'fCategory':'grain','fTexture':'chewy','fColour':'yellow','fFlavour':'savoury'})
    log(page, 'Custard', 'refused', date='2026-09-20')
    # autocomplete now includes logged food
    page.fill('#fFood',''); page.type('#fFood','homemade chee')
    check('autocomplete includes logged custom food', "Homemade cheesy scroll" in page.inner_text('#acList'))
    page.fill('#fFood',''); page.keyboard.press('Escape')
    page.wait_for_timeout(350); page.screenshot(path=f'{SHOTS}/phone-1-log-form-top.png')
    # form with a selection for screenshot
    page.fill('#fDate','2026-09-29'); page.wait_for_timeout(2700); page.fill('#fFood','Potato gems'); page.locator('#fNotes').focus(); page.click('#fResult [data-v=touched]'); page.fill('#fNotes','Served next to toast')
    page.evaluate('window.scrollTo(0,0)')
    fullshot(page, f'{SHOTS}/phone-1-log-form.png')
    # reset the form (don't save)
    page.evaluate("document.querySelector('#fFood').value='';document.querySelector('#fNotes').value=''")
    page.reload(); page.wait_for_load_state()

    st = page.evaluate('window.__LFE.state.logs.length'); check('8 logs saved', st==8, str(st))
    # Suggestions
    page.click('#nav button[data-view=next]')
    names = page.eval_on_selector_all('.sugg', 'els=>els.map(e=>e.dataset.sugg)')
    whys = page.eval_on_selector_all('.sugg .why', 'els=>els.map(e=>e.innerText)')
    print('SUGGESTIONS:'); [print('  ', n, '—', w) for n,w in zip(names, whys)]
    check('5-8 suggestions', 5 <= len(names) <= 8, str(len(names)))
    check('Toast-chained suggestion w/ crunchy, beige reason', any('Similar to Toast' in w and 'crunchy' in w and 'beige' in w for w in whys))
    check('working-on foods boosted (Banana or Pumpkin in list)', 'Banana' in names or 'Pumpkin mash' in names)
    check('recently refused broccoli not in suggestions', 'Broccoli, steamed' not in names)
    check('no accepted foods suggested', not any(n in names for n in ['Toast','Rice crackers',"Homemade cheesy scroll"]))
    check('popcorn/whole nuts never suggested', all(n not in ('Popcorn','Whole nuts','Whole grapes') for n in names))
    check('each suggestion has tips', page.locator('.sugg ul.tips li').count() >= 2*len(names))
    allsug = page.evaluate("window.__LFE.getSuggestions().list.map(x=>x.name)")
    full = page.evaluate("(()=>{const s=window.__LFE.getSuggestions; return true})()")
    page.wait_for_timeout(350); page.screenshot(path=f'{SHOTS}/phone-2-suggestions.png')
    fullshot(page, f'{SHOTS}/phone-2-suggestions-full.png')
    # History
    page.click('#nav button[data-view=history]')
    check('all logs count', page.inner_text('#nAll')=='8')
    page.click('#histSeg [data-h=accepted]')
    acc = page.eval_on_selector_all('#histList .food-card', 'els=>els.map(e=>e.dataset.food)')
    check('accepted list', sorted(acc)==sorted(['Toast','Rice crackers',"Homemade cheesy scroll"]), str(acc))
    toast_card = page.locator('#histList .food-card[data-food="Toast"]').inner_text()
    check('accepted counts & last tried', '1 ate' in toast_card and '0 refused' in toast_card and 'today' in toast_card, toast_card.replace('\n',' | '))
    page.click('#histSeg [data-h=working]')
    work = page.eval_on_selector_all('#histList .food-card', 'els=>els.map(e=>e.dataset.food)')
    check('working-on list', sorted(work)==['Banana','Pumpkin mash'], str(work))
    page.click('#histSeg [data-h=refused]')
    ref = page.eval_on_selector_all('#histList .food-card', 'els=>els.map(e=>e.dataset.food)')
    check('not-yet list', sorted(ref)==['Broccoli, steamed','Custard','Weet-Bix'], str(ref))
    page.wait_for_timeout(350); page.screenshot(path=f'{SHOTS}/phone-3-history-notyet.png')
    # Week view (Mon 28 Sep - Sun 4 Oct 2026)
    page.click('#nav button[data-view=week]')
    wk = {k: page.inner_text(f'#{k}') for k in ('wkDistinct','wkTotal','wkNew')}
    check('week distinct/total/new', wk=={'wkDistinct':'6','wkTotal':'6','wkNew':'6'}, str(wk))
    rc = {k: page.inner_text(f'#wkByResult [data-k={k}] .cnt') for k in ('ate','touched','refused')}
    check('week by result', rc=={'ate':'3','touched':'2','refused':'1'}, str(rc))
    cats = {k: page.inner_text(f'#wkByCat [data-k={k}] .cnt') for k in ('grain','fruit','veg')}
    check('week by category', cats=={'grain':'3','fruit':'1','veg':'2'}, str(cats))
    days = page.eval_on_selector_all('#wkDays .d', 'els=>els.map(e=>[e.dataset.day,e.dataset.n])')
    check('day grid', days[0]==['2026-09-28','2'] and days[1]==['2026-09-29','4'] and len(days)==7, str(days))
    check('week label', 'Mon 28 Sep' in page.inner_text('#wkRange'), page.inner_text('#wkRange'))
    fullshot(page, f'{SHOTS}/phone-4-weekly.png')
    page.click('#wkPrev')
    check('prev week counts', page.inner_text('#wkTotal')=='1' and page.inner_text('#wkLabel')=='Last week', page.inner_text('#wkTotal'))
    page.click('#wkNext'); page.click('#wkNext')
    check('next week empty', page.inner_text('#wkTotal')=='0')
    page.click('#wkPrev')
    # Edit: Broccoli refused -> touched
    page.click('#nav button[data-view=history]'); page.click('#histSeg [data-h=all]')
    bid = page.evaluate("window.__LFE.state.logs.find(l=>l.food==='Broccoli, steamed').id")
    page.click(f'#histList [data-edit="{bid}"]')
    check('edit loads form', page.input_value('#fFood')=='Broccoli, steamed' and page.locator('#editBanner').is_visible())
    page.click('#fResult [data-v=touched]'); page.fill('#fNotes','Licked a floret')
    page.click('#saveBtn')
    l = page.evaluate(f"window.__LFE.state.logs.find(l=>l.id==='{bid}')")
    check('edit saved', l['result']=='touched' and l['notes']=='Licked a floret' and page.evaluate('window.__LFE.state.logs.length')==8)
    page.click('#histSeg [data-h=working]')
    work = page.eval_on_selector_all('#histList .food-card', 'els=>els.map(e=>e.dataset.food)')
    check('edit reflected in working-on', 'Broccoli, steamed' in work, str(work))
    page.click('#nav button[data-view=next]')
    names2 = page.eval_on_selector_all('.sugg', 'els=>els.map(e=>e.dataset.sugg)')
    wk2 = page.evaluate("window.__LFE.getSuggestions().list.filter(x=>x.s&&x.s.touched>0).map(x=>x.name)"); check('2 working-on foods kept in suggestions after edit', len(wk2)==2, str(wk2))
    # Delete Weet-Bix
    page.click('#nav button[data-view=history]'); page.click('#histSeg [data-h=all]')
    wid = page.evaluate("window.__LFE.state.logs.find(l=>l.food==='Weet-Bix').id")
    page.click(f'#histList [data-del="{wid}"]')
    check('delete works', page.evaluate('window.__LFE.state.logs.length')==7 and page.inner_text('#nAll')=='7')
    # Reload persists
    page.reload(); page.wait_for_load_state()
    check('data persists after reload', page.evaluate('window.__LFE.state.logs.length')==7 and not page.locator('.modal').count())
    page.click('#nav button[data-view=history]')
    check('history after reload', page.inner_text('#nAll')=='7' and page.inner_text('#nAcc')=='3')
    before = page.evaluate('JSON.stringify(window.__LFE.state.logs.slice().sort((a,b)=>a.id<b.id?-1:1))')
    # Export
    page.click('#nav button[data-view=data]')
    with page.expect_download() as dl: page.click('#exportBtn')
    d = dl.value; os.makedirs('/workspace/fe-test', exist_ok=True); path = '/workspace/fe-test/' + d.suggested_filename; d.save_as(path)
    data = json.load(open(path)); check('export file', data['app']=='toddler-food-explorer' and 'child' not in data and len(data['logs'])==7 and d.suggested_filename=='toddler-food-log-2026-09-29.json', d.suggested_filename)
    # Clear
    page.click('#clearBtn')
    check('clear all', page.evaluate('window.__LFE.state.logs.length')==0 and 'no accepted foods' in page.evaluate("document.querySelector('#suggIntro').innerText.toLowerCase()"))
    page.reload()
    check('cleared persists; no intro again', page.evaluate('window.__LFE.state.logs.length')==0 and not page.locator('.modal').count())
    # Import (replace)
    page.click('#nav button[data-view=data]')
    page.set_input_files('#importFile', path)
    page.wait_for_selector('.modal')
    check('import modal', 'Found 7 logs' in page.inner_text('.modal'))
    page.click('.modal button:has-text("Replace")')
    after = page.evaluate('JSON.stringify(window.__LFE.state.logs.slice().sort((a,b)=>a.id<b.id?-1:1))')
    check('import restores identical data', after==before)
    # Merge duplicate import adds nothing
    page.set_input_files('#importFile', path); page.wait_for_selector('.modal'); page.click('.modal button:has-text("Merge")')
    check('merge skips duplicates', page.evaluate('window.__LFE.state.logs.length')==7)
    # bad import
    open('/workspace/fe-test/bad.json','w').write('{nope')
    page.set_input_files('#importFile', '/workspace/fe-test/bad.json')
    page.wait_for_timeout(300)
    check('bad import rejected gracefully', 'valid JSON' in page.inner_text('#toast') and page.evaluate('window.__LFE.state.logs.length')==7)
    page.reload()
    check('imported data persists', page.evaluate('window.__LFE.state.logs.length')==7)
    # XSS safety
    log(page, '<img src=x onerror=alert(1)>', 'refused', attrs={'fCategory':'other','fTexture':'soft','fColour':'mixed'})
    check('HTML escaped', page.locator('#todayList img').count()==0)
    page.evaluate("(()=>{const s=window.__LFE.state; s.logs=s.logs.filter(l=>!l.food.startsWith('<')); localStorage.setItem('toddlerFoodExplorer.v1',JSON.stringify(s));})()")
    page.reload()
    # Example data
    page.click('#nav button[data-view=data]'); page.click('#loadExample')
    n = page.evaluate('window.__LFE.state.logs.length'); check('example data loads (with confirm)', n==7+28, str(n))
    check('demo banner shown', page.locator('#demoBanner').is_visible())
    page.click('#nav button[data-view=next]'); page.wait_for_timeout(350); page.screenshot(path=f'{SHOTS}/phone-5-suggestions-example-data.png')
    page.click('#nav button[data-view=week]'); fullshot(page, f'{SHOTS}/phone-6-weekly-example-data.png')
    page.click('#nav button[data-view=data]'); page.click('#removeExample')
    check('remove example keeps real logs', page.evaluate('window.__LFE.state.logs.length')==7)
    # layout: no horizontal overflow on phone at each view
    for v in ['log','next','history','week','data']:
        page.click(f'#nav button[data-view={v}]')
        ov = page.evaluate('document.documentElement.scrollWidth - window.innerWidth')
        check(f'no horizontal overflow 390px ({v})', ov<=0, str(ov))
    # 375 width check
    page.set_viewport_size({'width':375,'height':740})
    for v in ['log','next','history','week','data']:
        page.click(f'#nav button[data-view={v}]')
        ov = page.evaluate('document.documentElement.scrollWidth - window.innerWidth')
        check(f'no horizontal overflow 375px ({v})', ov<=0, str(ov))
    # tap targets
    small = page.evaluate("""(()=>{page=[];document.querySelectorAll('#view-log button, #nav button').forEach(b=>{const r=b.getBoundingClientRect(); if(r.width&&r.height<40) page.push(b.innerText+':'+r.height)});return page})()""")
    page.click('#nav button[data-view=log]')
    small = page.evaluate("""(()=>{const out=[];document.querySelectorAll('#view-log button:not(.hidden *), #nav button').forEach(b=>{const r=b.getBoundingClientRect(); if(r.width && r.height<40) out.push(b.innerText.trim()+':'+Math.round(r.height))});return out})()""")
    check('tap targets >= 40px on log view', not small, str(small))
    ctx.storage_state(path='/workspace/fe-test/state.json')
    ctx.close()

    # Desktop
    ctx2 = b.new_context(viewport={'width':1280,'height':900}, locale='en-AU', timezone_id='Australia/Sydney')
    pg = ctx2.new_page()
    pg.on('console', lambda m: errors.append(f'[desktop] console.{m.type}: {m.text}') if m.type in ('error','warning') else None)
    pg.on('pageerror', lambda e: errors.append(f'[desktop] pageerror: {e}'))
    pg.on('dialog', lambda d: d.accept())
    pg.goto(URL); pg.click('.modal button')
    pg.click('#nav button[data-view=data]'); pg.set_input_files('#importFile', path); pg.wait_for_selector('.modal'); pg.click('.modal button:has-text("Replace")')
    pg.click('#nav button[data-view=next]'); pg.wait_for_timeout(2700)
    check('desktop suggestions render', pg.locator('.sugg').count()>=5)
    fullshot(pg, f'{SHOTS}/desktop-overview-suggestions.png')
    pg.click('#nav button[data-view=week]'); fullshot(pg, f'{SHOTS}/desktop-weekly.png')
    pg.click('#nav button[data-view=log]'); pg.wait_for_timeout(350); pg.screenshot(path=f'{SHOTS}/desktop-log.png')
    ov = pg.evaluate('document.documentElement.scrollWidth - window.innerWidth'); check('desktop no overflow', ov<=0)
    ctx2.close()

    # Migration: data saved under an older *FoodExplorer.v1 key is picked up and copied to the new key
    ctx3 = b.new_context(viewport={'width':390,'height':844}, locale='en-AU', timezone_id='Australia/Sydney')
    pm = ctx3.new_page()
    pm.on('pageerror', lambda e: errors.append(f'[migrate] pageerror: {e}'))
    pm.goto(URL)
    pm.evaluate("""localStorage.clear(); localStorage.setItem('oldFoodExplorer.v1', JSON.stringify({version:1,logs:[{id:'m1',date:'2026-09-28',food:'Toast',category:'grain',texture:'crunchy',colour:'beige',flavour:'savoury',result:'ate',notes:'',created:1}],settings:{introSeen:true}}))""")
    pm.reload()
    check('legacy key migrated', pm.evaluate('window.__LFE.state.logs.length')==1 and pm.evaluate("!!localStorage.getItem('toddlerFoodExplorer.v1') && !!localStorage.getItem('oldFoodExplorer.v1')"))
    ctx3.close()
    b.close()

print('\nCONSOLE/PAGE ERRORS:', errors or 'none')
fails = [r for r in results if not r[1]]
print(f'\n{len(results)-len(fails)}/{len(results)} checks passed')
sys.exit(1 if fails or errors else 0)
