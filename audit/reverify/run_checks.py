"""Phase 4 browser and HTTP audit. Uses real Chrome, HTTP, disk and SSE; no route mocks."""
import asyncio
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import socket
import subprocess
import tempfile
import time
import traceback
import urllib.request

import httpx
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'audit/reverify'
BASE = 'http://127.0.0.1:8740'
PYTHON = str(ROOT / '.venv/bin/python')
SLOT = '/Volumes/Extreme SSD/Projects/grokbot/tools/heavy-slot.sh'
CHROME = '/Users/jaibajrang/Library/Caches/ms-playwright/chromium-1248/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing'
ROWS = {p[1].strip(): p for line in (ROOT/'AUDIT.md').read_text().splitlines() if (p:=line.split('|')) and len(p)==8 and p[4].strip() in ('PASS','FAIL')}
RESULTS = {}
LIFECYCLE = {'servers': [], 'slot_released': False}

def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False)+'\n')

def flush(id, status, observation):
    lines=(ROOT/'AUDIT.md').read_text().splitlines()
    for i,line in enumerate(lines):
        p=line.split('|')
        if len(p)==8 and p[1].strip()==id:
            p[4]=' '+status+' '
            p[5]=f' [{id}](audit/reverify/{id}/) — '+observation.replace('|','/').replace('\n',' ')[:1800]+' '
            lines[i]='|'.join(p)
    (ROOT/'AUDIT.md').write_text('\n'.join(lines)+'\n')
    write_json(OUT/'summary.json', RESULTS)

@contextmanager
def serve(runs=None, stage='normal', token=None, concurrency='1'):
    with socket.socket() as s:
        s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        s.bind(('127.0.0.1',8740))
    env={**os.environ,'WEB_CONCURRENCY':concurrency}
    env.pop('PERISCOPE_ALERT_TOKEN',None)
    if runs is not None: env['PERISCOPE_RUNS']=str(runs)
    else: env.pop('PERISCOPE_RUNS',None)
    if token: env['PERISCOPE_ALERT_TOKEN']=token
    log=(OUT/f'server-{stage}.log').open('w')
    proc=subprocess.Popen([PYTHON,'-m','uvicorn','server:app','--host','127.0.0.1','--port','8740','--workers','1'],cwd=ROOT,env=env,stdout=log,stderr=log)
    record={'stage':stage,'pid':proc.pid,'killed':False}
    LIFECYCLE['servers'].append(record); write_json(OUT/'lifecycle.json',LIFECYCLE)
    try:
        deadline=time.monotonic()+20
        while True:
            assert proc.poll() is None, f'server exited during {stage}'
            try:
                with urllib.request.urlopen(BASE+'/api/health', timeout=1) as r: assert r.status==200
                break
            except OSError:
                assert time.monotonic()<deadline,'startup timeout'
                time.sleep(.1)
        yield proc
    finally:
        if proc.poll() is None:
            proc.terminate()
            try: proc.wait(timeout=8)
            except subprocess.TimeoutExpired: proc.kill();proc.wait(timeout=5)
        record.update(killed=proc.poll() is not None,exit_code=proc.returncode)
        log.close();write_json(OUT/'lifecycle.json',LIFECYCLE)

class Check:
    def __init__(self,browser,id,width=1280,reduced=None):
        self.id=id;self.dir=OUT/id;self.dir.mkdir(exist_ok=True)
        self.context=browser.new_context(viewport={'width':width,'height':812 if width==375 else 800},permissions=['clipboard-read','clipboard-write'],reduced_motion=reduced or 'no-preference')
        self.page=self.context.new_page();self.console=[];self.errors=[];self.network=[];self.failed=[];self.observed={};self.issues=[];self.allowed=set();self.allowed_failed=[]
        self.page.on('console',lambda m:self.console.append({'type':m.type,'text':m.text}))
        self.page.on('pageerror',lambda e:self.errors.append(str(e)))
        self.page.on('response',lambda r:self.network.append({'event':'response','url':r.url,'status':r.status,'method':r.request.method,'post_data':r.request.post_data if r.request.method=='POST' and r.request.url.endswith(('/alerts','/alerts/status')) else None}))
        self.page.on('requestfailed',lambda r:self.failed.append({'url':r.url,'failure':r.failure}))
    def eq(self,a,b,label):
        if a!=b: self.issues.append(f'{label}: observed {a!r}; expected {b!r}')
    def ok(self,a,label):
        if not a:self.issues.append(label)
    def text(self,sel):return self.page.locator(sel).inner_text()
    def attr(self,sel,name):return self.page.locator(sel).get_attribute(name)
    def goto(self,path='/calibrate.html',ready=False):
        r=self.page.goto(BASE+path);self.eq(r.status,200,'navigation HTTP')
        if ready:
            self.page.wait_for_function("document.querySelector('#clock')?.textContent.includes('/ 19.00 s')")
            self.page.wait_for_function("['vFloor','vShadow','vHidden'].every(id=>document.getElementById(id).readyState>=2)")
        self.page.wait_for_timeout(120)
    def request(self,method,path,status=200,**kwargs):
        with httpx.Client(timeout=180,trust_env=False) as client:r=client.request(method,BASE+path,**kwargs)
        try:body=r.json()
        except ValueError:body=r.text[:1000]
        self.network.append({'event':'http','method':method,'url':BASE+path,'status':r.status_code,'body':body,'request_bytes':int(r.request.headers.get('content-length','0'))})
        self.eq(r.status_code,status,f'{method} {path} HTTP')
        self.allowed.add(status)
        return r
    def finish(self):
        p=self.page
        p.wait_for_timeout(150)
        self.issues.extend('console error: '+m['text'] for m in self.console if m['type']=='error')
        self.issues.extend('page error: '+e for e in self.errors)
        self.issues.extend('unexpected HTTP: '+str(r) for r in self.network if r['status']>=400 and r['status'] not in self.allowed)
        self.issues.extend('failed network request: '+str(r) for r in self.failed if not any(x in r['url'] for x in self.allowed_failed))
        if p.locator('#clock').count():
            self.observed['screen']=p.evaluate("""() => {let o={};for(let id of ['alertH','alertP','statusTxt','aPhi','aEta','aZ','decA','decW','clock','hudT','playTxt'])o[id]=document.getElementById(id)?.textContent; o.state=document.getElementById('alert')?.dataset.s;o.action=document.getElementById('decision')?.dataset.a;return o;}""")
        try:p.screenshot(path=str(self.dir/'screenshot.png'),full_page=True)
        except Exception as e:self.issues.append('screenshot: '+str(e))
        write_json(self.dir/'console.json',{'messages':self.console,'page_errors':self.errors})
        write_json(self.dir/'network.json',{'requests':self.network,'failed':self.failed})
        result={'id':self.id,'status':'FAIL' if self.issues else 'PASS','expected':ROWS[self.id][3].strip(),'observed':self.observed,'issues':self.issues,'viewport':self.page.viewport_size,'browser':self.context.browser.version,'timestamp_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
        write_json(self.dir/'result.json',result);RESULTS[self.id]=result
        observation='; '.join(self.issues) if self.issues else self.observed.get('summary','Fresh check matched expected result; zero console/page errors and unexpected HTTP failures.')
        flush(self.id,result['status'],observation)
        self.context.close();print(f'{self.id}: {result["status"]}',flush=True)

def run(browser,id,fn,**kwargs):
    c=Check(browser,id,**kwargs)
    try:fn(c)
    except Exception as e:c.issues.append(f'{type(e).__name__}: {e}');(c.dir/'traceback.txt').write_text(traceback.format_exc())
    finally:c.finish()

def times(c):return c.page.evaluate("['vFloor','vShadow','vHidden'].map(id=>({time:document.getElementById(id).currentTime,paused:document.getElementById(id).paused,rate:document.getElementById(id).playbackRate}))")
def paused(c):c.ok(all(v['paused'] for v in times(c)),'all videos paused')
def frame(c,n):
    c.page.locator('#stBox').focus();c.page.keyboard.press('Home')
    for _ in range(n):c.page.keyboard.press('ArrowRight')
    c.page.wait_for_function('(n)=>document.querySelector("#clock").textContent.startsWith((n/20).toFixed(2)+" / ")',arg=n)
    c.page.wait_for_timeout(100)

def feed(c):
    c.page.evaluate("""() => {window.events=[];window.feed=new EventSource('/api/alerts/stream');for(let event of ['heartbeat','alert','stale','resync'])feed.addEventListener(event,e=>events.push({event,data:JSON.parse(e.data),received:performance.now()}));} """)
    c.page.wait_for_function("events.some(e=>e.event==='heartbeat')")
def event(c,name,reason=None):
    c.page.wait_for_function("([name,reason])=>events.some(e=>e.event===name&&(!reason||e.data.reason===reason))",arg=[name,reason],timeout=8000)
    e=c.page.evaluate("([name,reason])=>events.filter(e=>e.event===name&&(!reason||e.data.reason===reason)).at(-1)",[name,reason]);c.observed.setdefault('events',[]).append(e);return e

def reset(c,live=True):
    c.request('POST','/api/alerts/status',json={'run':None,'live':False,'reason':'switched'})
    if live:c.request('POST','/api/alerts/status',json={'run':'demo','live':True})
def alert(c,state='clear',level=None,t=1,bearing=None,status=200):return c.request('POST','/api/alerts',status=status,json={'run':'demo','state':state,'level':level,'t':t,'bearing_deg':bearing,'confidence':.9})


def console_ui(c):
    id=c.id;p=c.page
    autoplay=id in ['UI-AUTOPLAY','UI-PLAY-PAUSE','UI-RESTART','UI-REPLAY-LOOP','UI-KEY-SHORTCUTS'] or id.startswith('EDGE-INTERRUPT-') and id!='EDGE-INTERRUPT-REDUCED-MOTION'
    c.goto('/' if autoplay else '/?autoplay=0',True)
    if autoplay:p.wait_for_function('!vFloor.paused && vFloor.currentTime > .1')
    if id=='UI-SERVE-LOCAL':
        c.eq(p.title(),"Periscope · see who's coming around the corner",'title');c.eq(c.text('h1'),"See who's coming around the corner.",'h1')
    elif id=='UI-RUN-SELECT':
        listed=c.request('GET','/api/runs').json();options=p.locator('#runSel option').evaluate_all('(els)=>els.map(e=>({id:e.value,title:e.textContent}))')
        c.eq(options,[{'id':r['id'],'title':r['title']} for r in listed],'listed options');c.eq(p.locator('#runSel').input_value(),'demo','selected id');c.eq(c.text('#runSel option:checked'),'Synthetic corner · red top · lit hallway','selected title')
    elif id in ('UI-SYNTH-TAG','EDGE-375PX-SYNTHETIC-LABEL'):
        c.ok(p.locator('#kindTag').is_visible(),'Synthetic scene visible');c.eq(c.text('#kindTag'),'Synthetic scene','label')
        if id=='UI-SYNTH-TAG':c.eq(c.text('#sceneFoot'),'Synthetic: per-pixel SNR 0.224 at 3 m · noise 2.29 DN · signal 0.513 DN','scene foot')
    elif id=='UI-AUTOPLAY':
        c.eq(times(c)[0]['paused'],False,'playing');c.eq(times(c)[0]['rate'],1,'rate');c.eq(c.text('#playTxt'),'Pause','play text');c.eq(c.attr('#playBtn','aria-label'),'Pause','aria label')
    elif id in ('UI-PLAY-PAUSE','EDGE-INTERRUPT-PAUSE'):
        if id.startswith('EDGE'):feed(c)
        p.click('#playBtn');paused(c);c.eq(c.text('#playTxt'),'Resume','paused text');c.eq(c.attr('#playBtn','aria-label'),'Play','paused aria')
        if id.startswith('EDGE'):
            p.wait_for_timeout(200);c.ok(any(n.get('post_data') and '"reason":"paused"' in n['post_data'] for n in c.network),'real paused status POST');c.eq(event(c,'stale','paused')['data']['live'],False,'stale live')
        else:p.click('#playBtn');p.wait_for_function('!vFloor.paused');c.eq(c.text('#playTxt'),'Pause','resumed text');c.eq(c.attr('#playBtn','aria-label'),'Pause','resumed aria')
    elif id=='UI-RESTART':
        p.wait_for_function('vFloor.currentTime>.5');p.locator('#restartBtn').evaluate('(e)=>e.click()')
        c.eq(c.text('#clock'),'0.00 / 19.00 s','clock');c.eq(c.text('#hudT'),'t 0.00 s','hud');p.wait_for_function('!vFloor.paused')
    elif id=='UI-REPLAY-LOOP':
        p.evaluate('vFloor.currentTime=vFloor.duration-.2');p.wait_for_function("document.querySelector('#playTxt').textContent==='Replay'")
        start=time.monotonic();p.wait_for_function('!vFloor.paused && vFloor.currentTime < 1',timeout=4000);elapsed=time.monotonic()-start
        c.observed['restart_delay_s']=elapsed;c.ok(2.35<elapsed<2.9,'2500ms kiosk restart')
    elif id=='UI-KEY-SHORTCUTS':
        p.locator('h1').click();p.keyboard.press('Space');paused(c);p.keyboard.press('Space');p.wait_for_function('!vFloor.paused');p.keyboard.press('Space');p.wait_for_timeout(100)
        old=float(c.attr('#stBox','aria-valuenow'));p.keyboard.press('ArrowRight');c.eq(float(c.attr('#stBox','aria-valuenow')),round(old+.05,2),'one frame right');p.keyboard.press('ArrowLeft');c.eq(float(c.attr('#stBox','aria-valuenow')),old,'one frame left');paused(c)
    elif id=='UI-SPEED-CONTROL':
        p.click('[data-rate="2"]');c.eq([v['rate'] for v in times(c)],[2,2,2],'all rates');c.eq(p.locator('[data-rate]').evaluate_all('(es)=>es.map(e=>e.getAttribute("aria-pressed"))'),['false','false','true'],'pressed')
    elif id=='UI-FLOOR-VIEW':
        for view,hidden in [('camera','#vShadow'),('shadow','#vFloor'),('split',None)]:
            p.click('button[data-view="'+view+'"]');c.eq(c.attr('#stage','data-view'),view,'stage view')
            if hidden:c.ok(not p.locator(hidden).is_visible(),hidden+' hidden')
            else:c.ok(p.locator('#wipeBtn').is_visible(),'divider visible')
    elif id=='UI-WIPE-DIVIDER':
        p.locator('#wipeBtn').focus();old=int(c.attr('#wipeBtn','aria-valuenow'));p.keyboard.press('ArrowRight');c.eq(int(c.attr('#wipeBtn','aria-valuenow')),old+5,'arrow movement')
        for _ in range(24):p.keyboard.press('ArrowRight')
        c.eq(c.attr('#wipeBtn','aria-valuenow'),'96','upper clamp')
        for _ in range(24):p.keyboard.press('ArrowLeft')
        c.eq(c.attr('#wipeBtn','aria-valuenow'),'4','lower clamp');c.eq(p.locator('#stage').evaluate('(e)=>e.style.getPropertyValue("--split")'),'4%','CSS split')
        box=p.locator('#stage').bounding_box();b=p.locator('#wipeBtn').bounding_box();p.mouse.move(b['x']+b['width']/2,b['y']+b['height']/2);p.mouse.down();p.mouse.move(box['x']+box['width']*.6,b['y']+b['height']/2,steps=8);p.mouse.up();c.eq(c.attr('#wipeBtn','aria-valuenow'),'60','drag split')
    elif id in ('UI-SPACETIME-SCRUB','EDGE-INTERRUPT-SEEK'):
        if id.startswith('EDGE'):feed(c)
        p.locator('#stBox').focus();p.keyboard.press('ArrowRight');paused(c)
        t=float(c.attr('#stBox','aria-valuenow'));c.eq(c.attr('#stBox','aria-valuetext'),f'{t:.1f} seconds','aria text');c.ok(all(abs(v['time']-t)<.051 for v in times(c)),'videos seek target frame')
        if id.startswith('EDGE'):
            p.wait_for_timeout(200);c.ok(any(n.get('post_data') and '"reason":"seek"' in n['post_data'] for n in c.network),'real seek POST')
        else:
            box=p.locator('#stBox').bounding_box();p.mouse.move(box['x']+box['width']*.3,box['y']+box['height']/2);p.mouse.down();p.mouse.move(box['x']+box['width']*.5,box['y']+box['height']/2,steps=5);p.mouse.up();p.wait_for_timeout(100);t=float(c.attr('#stBox','aria-valuenow'));c.eq(c.attr('#stBox','aria-valuetext'),f'{t:.1f} seconds','drag aria');c.ok(all(abs(v['time']-t)<.051 for v in times(c)),'drag videos target')
        c.observed.update(target_t=t,videos=times(c))
    elif id=='UI-OVERLAY-TOGGLE':
        frame(c,127)
        for sel in ['[data-ov="track"]','#truthBtn']:
            before=p.locator('#st').evaluate('(e)=>e.toDataURL()') if p.locator('#st').count() else p.locator('#stBox canvas').first.evaluate('(e)=>e.toDataURL()')
            p.click(sel);c.eq(c.attr(sel,'aria-pressed'),'false','toggle off');after=p.locator('#stBox canvas').first.evaluate('(e)=>e.toDataURL()');c.ok(before!=after,'canvas overlay redraw');p.click(sel);c.eq(c.attr(sel,'aria-pressed'),'true','toggle on')
    elif id=='UI-MAP-VIEW':
        p.click('#hiddenBtn');c.eq(p.locator('#plan').evaluate('(e)=>getComputedStyle(e).visibility'),'hidden','plan hidden');c.ok(p.locator('#vHidden').is_visible(),'hidden video');c.eq(c.text('#mapNote'),'Ground-truth camera. Periscope never sees this view.','map note');p.click('[data-map="plan"]');c.eq(p.locator('#plan').evaluate('(e)=>getComputedStyle(e).visibility'),'visible','plan restored')
    elif id=='UI-DECISION-LOG':
        p.locator('#log li').filter(has_text='16.8 s').click();paused(c);c.ok(all(abs(v['time']-16.8)<.051 for v in times(c)),'event video times');c.observed['videos']=times(c)
    elif id=='EDGE-375PX-CONSOLE-LAYOUT':
        dimensions=p.evaluate('({viewport:innerWidth,width:document.documentElement.scrollWidth,body:document.body.scrollWidth})');c.observed['dimensions']=dimensions;c.eq(dimensions,{'viewport':375,'width':375,'body':375},'width');c.ok(p.locator('#console').evaluate('(e)=>getComputedStyle(e).gridTemplateColumns.split(" ").length===1'),'console single column')
    elif id=='EDGE-INTERRUPT-TAB-CLOSE':
        # A separate observer survives the actual page navigation; browser pagehide sends the real keepalive.
        observer=c.context.new_page();observer.goto(BASE+'/calibrate.html');observer.evaluate("window.events=[];window.feed=new EventSource('/api/alerts/stream');feed.addEventListener('stale',e=>events.push(JSON.parse(e.data)))")
        p.wait_for_timeout(300);p.goto(BASE+'/calibrate.html');observer.wait_for_function("events.some(e=>e.reason==='closed')")
        data=observer.evaluate("events.find(e=>e.reason==='closed')");c.eq(data['live'],False,'closed stale');c.observed['server_stale']=data;observer.close()
    elif id=='EDGE-INTERRUPT-RUN-SWITCH':
        feed(c);p.select_option('#runSel','reverify-switch');event(c,'stale','switched');p.wait_for_function("document.querySelector('#clock').textContent.startsWith('0.00 /')");c.eq(c.text('#clock'),'0.00 / 19.00 s','new run frame 0')
    elif id=='EDGE-INTERRUPT-REDUCED-MOTION':
        paused(c);c.eq(c.text('#playTxt'),'Play run','play text');c.eq(c.attr('#playBtn','aria-label'),'Play','aria');p.goto(BASE+'/');p.wait_for_function("document.querySelector('#clock')?.textContent.includes('19.00')");p.wait_for_timeout(300);paused(c);c.eq(c.text('#playTxt'),'Play run','reduced motion text')
    else:raise ValueError('unhandled '+id)


def calibration(c):
    p=c.page;id=c.id;c.goto()
    if id=='UI-CALIBRATE-PAGE':
        c.eq(p.title(),'Periscope · mark the tape','title');c.eq(c.text('h1'),'Mark the tape','h1');c.eq(c.attr('a','href'),'./','back href');c.eq(c.text('a'),'Back to the console','back text');return
    if id=='EDGE-CALIB-EMPTY-STATE':
        c.eq(c.text('#drop'),'No frame loaded yet.\nChoose an image, or drop one here.','drop text');c.ok(p.locator('#drop').is_visible(),'drop visible');c.ok(p.locator('#cv').evaluate('(e)=>e.hidden'),'canvas hidden');c.ok(p.locator('#copy').is_disabled(),'copy disabled');c.eq(p.locator('#out').input_value(),'','output');return
    if id=='EDGE-CALIB-INVALID-FILE':
        p.locator('#file').set_input_files({'name':'invalid.txt','mimeType':'text/plain','buffer':b'not an image'});c.ok(p.locator('#drop').is_visible(),'drop remains visible');c.ok(p.locator('#cv').evaluate('(e)=>e.hidden'),'canvas remains hidden');c.eq(p.locator('#list li.done').count(),0,'marked list empty');return
    if id=='EDGE-375PX-CALIBRATE-LAYOUT':
        d=p.evaluate('({viewport:innerWidth,width:document.documentElement.scrollWidth,body:document.body.scrollWidth})');c.eq(d,{'viewport':375,'width':375,'body':375},'width');c.observed['dimensions']=d;c.ok(p.locator('.grid').evaluate('(e)=>getComputedStyle(e).gridTemplateColumns.split(" ").length===1'),'single column');return
    p.locator('#file').set_input_files(str(ROOT/'audit/cli/calib-out/frame.png'));p.wait_for_function('!cv.hidden');c.observed['image_dimensions']=p.locator('#cv').evaluate('(e)=>[e.width,e.height]')
    if id=='UI-CALIBRATE-LOAD':
        import cv2
        im=cv2.imread(str(ROOT/'audit/cli/calib-out/frame.png'));c.eq(c.observed['image_dimensions'],[im.shape[1],im.shape[0]],'loaded image dimensions');c.ok(not p.locator('#drop').is_visible(),'drop hidden');c.eq(p.locator('#list li.done').count(),0,'empty marks');return
    def mark(n):
        for i in range(n):p.locator('#cv').click(position={'x':60+i*30,'y':70+i*18})
    if id=='UI-CALIBRATE-MODE':
        mark(2);p.click('[data-mode="gt"]');c.eq(c.attr('[data-mode="gt"]','aria-pressed'),'true','gt pressed');c.eq(p.locator('#list li b').all_text_contents(),['A','B','C','D'],'gt rows');c.eq(p.locator('#out').input_value(),'','points cleared');p.click('[data-mode="corner"]');c.eq(p.locator('#list li b').all_text_contents(),list('123456'),'corner rows')
    elif id=='UI-CALIBRATE-CLICK':
        before=p.locator('#cv').evaluate('(e)=>e.toDataURL()');mark(1);c.eq(p.locator('#list li.done').count(),1,'done point');out=p.locator('#out').input_value();c.ok(re.fullmatch(r'\d+\.\d,\d+\.\d',out),'one-decimal coordinates');c.ok(p.locator('#out').evaluate('(e)=>e.readOnly'),'readonly');c.ok(before!=p.locator('#cv').evaluate('(e)=>e.toDataURL()'),'marker drawn');c.observed.update(output=out,row=c.text('#list li.done'))
    elif id=='UI-CALIBRATE-UNDO':
        mark(1);first=p.locator('#out').input_value();first_canvas=p.locator('#cv').evaluate('(e)=>e.toDataURL()');mark(1);p.click('#undo');c.eq(p.locator('#out').input_value(),first,'undo output');c.eq(p.locator('#list li.done').count(),1,'undo rows');c.eq(p.locator('#cv').evaluate('(e)=>e.toDataURL()'),first_canvas,'undo canvas')
    elif id=='UI-CALIBRATE-COPY':
        mark(5);c.ok(p.locator('#copy').is_enabled(),'copy enabled');out=p.locator('#out').input_value();p.click('#copy');p.wait_for_function("document.querySelector('#copy').textContent==='Copied'");c.eq(c.text('#copy'),'Copied','copy label');c.eq(p.evaluate('navigator.clipboard.readText()'),out,'clipboard');p.wait_for_timeout(1450);c.eq(c.text('#copy'),'Copy marks','revert label')
    elif id=='EDGE-CALIB-COPY-INCOMPLETE':
        mark(4);c.ok(p.locator('#copy').is_disabled(),'4 corner points disabled');p.click('[data-mode="gt"]');mark(3);c.ok(p.locator('#copy').is_disabled(),'3 gt points disabled')
    else:raise ValueError(id)


def engine(c):
    c.goto('/?autoplay=0',True);p=c.page;id=c.id
    if id.startswith('ENG-DEMO-FRAME-'):
        n=int(id.split('-')[3]);frame(c,n)
        baseline=json.loads((ROOT/'audit/browser'/id/'result.json').read_text())['observed_frame']
        for key in ['alertH','alertP','statusTxt','aPhi','aEta','aZ','decA','decW']:
            if key in baseline:c.eq(p.locator('#'+key).text_content(),baseline[key],key)
        c.eq(c.attr('#alert','data-s'),baseline['state'],'state');c.eq(c.attr('#decision','data-a'),baseline['action'],'action')
        if n in (127,194):c.eq(p.locator('#alert .big').evaluate('(e)=>getComputedStyle(e).display'),'block' if n==127 else 'none','STOP display');c.eq(c.text('#alert .big'),'STOP','STOP text')
        if n==127:c.eq(p.locator('#alert').evaluate('(e)=>getComputedStyle(e).backgroundImage'),'linear-gradient(rgb(232, 56, 45), rgb(196, 42, 33))','red gradient')
        if n==335:
            row=p.locator('#log li').filter(has_text='16.8 s');text=row.inner_text();c.ok(all(t in text for t in ['Re-learn the background','lighting or exposure changed; the empty-hallway reference is stale']),'relearn log')
    elif id=='ENG-CHECKS-ASSESSMENT':
        frame(c,40);text=c.text('#checks');c.observed['checks']=text
        for v in ['Predicted range','5.2 m','Pixel noise','1.58 %','Camera shake','0.01 px','View drift','0.0 px','Light change','-0.02 %','Clipped pixels','0.00 %','Wedge pixels','29,623']:c.ok(v in text,'check '+v)
        c.eq(p.locator('#checks > *').count(),7,'seven checks');c.eq(p.locator('#checks .bad').count(),0,'no bad checks')
    elif id=='ENG-GROUND-TRUTH-SCORES':
        text=p.locator('#scores').evaluate("(e)=>Array.from(e.children).map(row=>row.querySelector('dt').textContent+' '+row.querySelector('dd').firstChild.textContent+' '+row.querySelector('small').textContent).join('\\n')");c.observed['scores']=text
        for v in ['First detection','4.4 m from corner','Warning lead','2.1 s','Bearing error','2.1 ° mean','Detected within 3 m','100 % of frames','False alarms','0.0 % empty frames','Bearing error p90','5.4 °']:c.ok(v in text,'score '+v)
        c.ok("Synthetic run, scored against the renderer's truth." in c.text('#fine'),'synthetic truth statement')


def api(c):
    c.goto();id=c.id
    if id=='API-HEALTH':c.eq(c.request('GET','/api/health').json(),{'ok':True},'health JSON')
    elif id=='API-RUNS':c.ok({'id':'demo','title':'Synthetic corner · red top · lit hallway','kind':'synthetic','frames':380} in c.request('GET','/api/runs').json(),'demo in persisted runs')
    elif id.startswith('API-ANALYZE-'):analyze(c)
    elif id=='API-ALERTS-AUTH-ORIGIN':c.eq(c.request('POST','/api/alerts/status',status=403,json={'run':'demo','live':True},headers={'Origin':'https://foreign.example'}).json(),{'detail':'cross-origin publisher refused'},'origin refusal')
    elif id=='API-ALERTS-AUTH-LOOPBACK':
        # Uvicorn accepts X-Forwarded-For only from trusted loopback, assigning this real HTTP request a non-loopback client IP.
        c.eq(c.request('POST','/api/alerts/status',status=403,json={'run':'demo','live':True},headers={'X-Forwarded-For':'192.0.2.10'}).json(),{'detail':'alerts can only be published from this machine (or set PERISCOPE_ALERT_TOKEN)'},'non-loopback refusal')
    elif id=='API-ALERTS-STATUS-LIVE':
        reset(c);first=c.request('POST','/api/alerts/status',json={'run':'demo','live':True}).json();c.eq(first['live'],True,'live');c.eq(first['run'],'demo','run');c.ok(isinstance(first['t'],(float,int)) and isinstance(first['age_s'],(float,int)),'numeric t/age');c.page.wait_for_timeout(1800);c.request('POST','/api/alerts/status',json={'run':'demo','live':True});c.page.wait_for_timeout(1500);feed(c);c.eq(event(c,'heartbeat')['data']['live'],True,'renewed beyond original 3s watchdog');c.observed['status']=first
    elif id=='API-ALERTS-STATUS-STALE':
        reset(c);feed(c);r=c.request('POST','/api/alerts/status',json={'run':'demo','live':False,'reason':'paused'}).json();c.eq(r['live'],False,'live');c.eq(r['run'],'demo','run');c.ok(isinstance(r['t'],(float,int)) and isinstance(r['age_s'],(float,int)),'t/age numeric');c.eq(event(c,'stale','paused')['data']['live'],False,'stale')
    elif id.startswith('API-ALERTS-PUBLISH-') or id=='API-ALERTS-DEDUP':
        reset(c);feed(c);kind=id.removeprefix('API-ALERTS-PUBLISH-');state='clear' if kind in ('CLEAR','API-ALERTS-DEDUP') else 'someone';level=None if state=='clear' else 'stop' if kind=='STOP' else 'watch';bearing=None if state=='clear' else 73.4 if kind=='STOP' else 75.0
        r=alert(c,state,level,bearing=bearing).json();c.eq(r['sent'],True,'sent');c.ok(isinstance(r['subscribers'],int) and r['subscribers']>=1,'subscriber count');e=event(c,'alert')['data']
        for k,v in {'run':'demo','state':state,'level':level,'bearing_deg':bearing}.items():c.eq(e[k],v,k)
        if id=='API-ALERTS-DEDUP':
            count=c.page.evaluate("events.filter(e=>e.event==='alert').length");r=alert(c,state,level,t=2,bearing=bearing).json();c.eq(r['sent'],False,'dedup sent');c.page.wait_for_timeout(300);c.eq(c.page.evaluate("events.filter(e=>e.event==='alert').length"),count,'no duplicate event')
    elif id=='API-ALERTS-STREAM-CONNECT':
        reset(c);alert(c,'someone','watch',bearing=75);feed(c);event(c,'alert');c.eq(c.page.evaluate('events.slice(0,2).map(e=>e.event)'),['heartbeat','alert'],'initial event order')
        # Real stream headers independently recorded, without consuming the endless body.
        with httpx.Client(trust_env=False) as client:
            with client.stream('GET',BASE+'/api/alerts/stream') as r:
                c.network.append({'event':'http','method':'GET','url':BASE+'/api/alerts/stream','status':r.status_code,'headers':dict(r.headers)});c.eq(r.status_code,200,'SSE HTTP');c.ok(r.headers['content-type'].startswith('text/event-stream'),'content type');c.eq(r.headers.get('cache-control'),'no-cache','cache');c.eq(r.headers.get('x-accel-buffering'),'no','buffering')
    elif id=='API-ALERTS-STREAM-HEARTBEAT':
        reset(c,False);feed(c);c.page.wait_for_function("events.filter(e=>e.event==='heartbeat').length>=4",timeout=16000);hs=c.page.evaluate("events.filter(e=>e.event==='heartbeat')");gaps=[(b['received']-a['received'])/1000 for a,b in zip(hs,hs[1:])];sg=[b['data']['t']-a['data']['t'] for a,b in zip(hs,hs[1:])];c.observed.update(received_gaps_s=gaps,server_gaps_s=sg,heartbeats=hs)
        c.ok(len(gaps)>=3 and all(0<g<=5 for g in gaps+sg),'at least three gaps <=5.0 seconds')
        for h in hs:
            d=h['data'];c.eq(set(d),{'t','live','run','age_s'},'fields');c.ok(isinstance(d['t'],(int,float)) and isinstance(d['live'],bool) and (d['run'] is None or isinstance(d['run'],str)) and (d['age_s'] is None or isinstance(d['age_s'],(int,float))),'heartbeat types')
    elif id=='EDGE-ALERT-NOT-LIVE':
        reset(c,False);c.eq(alert(c,status=409).json(),{'detail':'that run is not playing; post /api/alerts/status first'},'not live detail')
    elif id=='EDGE-ALERT-BACKWARD-T':
        reset(c);alert(c,t=2);c.eq(alert(c,t=1,status=409).json(),{'detail':'alert is older than the last one in this live span'},'backward detail')
    elif id=='EDGE-ALERT-MALFORMED-BODY':
        c.eq(c.request('POST','/api/alerts',status=422,json={'run':'demo','state':'someone','confidence':.9,'t':1}).json(),{'detail':'level is required for someone and must be null for clear'},'validation detail')
        c.eq(c.request('POST','/api/alerts',status=422,json={'run':'demo','state':'clear','level':'watch','confidence':.9,'t':1}).json(),{'detail':'level is required for someone and must be null for clear'},'clear level detail')
    elif id=='EDGE-ALERT-KEEPALIVE-TIMEOUT':
        reset(c);feed(c);start=time.monotonic();e=event(c,'stale','timeout');c.eq(e['data']['live'],False,'timeout live');c.observed['elapsed_s']=time.monotonic()-start
    elif id=='EDGE-ALERT-SUBSCRIBER-OVERFLOW':overflow(c)
    else:raise ValueError(id)


def analyze(c):
    id=c.id;runs=ROOT/'web/runs';before=set(p.name for p in runs.glob('up-*'));cal=(ROOT/'audit/cli/calib-out/auto/calib.json').read_text();fixture=ROOT/'web/runs/demo/floor.mp4'
    try:
        if id=='API-ANALYZE-TOO-LARGE':
            with tempfile.TemporaryDirectory(prefix='periscope-large-') as tmp:
                f=Path(tmp)/'501MiB.mp4';size=501*1024*1024
                with f.open('wb') as out:out.truncate(size)
                with f.open('rb') as stream:r=c.request('POST','/api/analyze',status=413,data={'calib':cal},files={'video':('501MiB.mp4',stream,'video/mp4')})
                c.eq(r.json(),{'detail':'clip too large (500 MB max)'},'too-large detail');c.observed['video_bytes_streamed']=size
            c.observed['temporary_fixture_deleted']=not f.exists()
        elif id=='API-ANALYZE-BAD-CALIB':
            with fixture.open('rb') as stream:r=c.request('POST','/api/analyze',status=400,data={'calib':'{bad'},files={'video':('clip.mp4',stream,'video/mp4')})
            c.ok(r.json()['detail'].startswith('bad calibration:'),'bad calib detail')
        elif id=='API-ANALYZE-UNREADABLE':
            r=c.request('POST','/api/analyze',status=422,data={'calib':cal},files={'video':('broken.mp4',b'corrupt-video','video/mp4')});c.ok(r.json()['detail'].startswith('cannot open video:'),'unreadable detail')
        else:
            # Eighty real decoded frames keep this analysis finite while exercising the full real pipeline.
            import cv2
            with tempfile.TemporaryDirectory(prefix='periscope-valid-') as tmp:
                clip=Path(tmp)/'valid.mp4';cap=cv2.VideoCapture(str(fixture));writer=cv2.VideoWriter(str(clip),cv2.VideoWriter_fourcc(*'mp4v'),20,(480,360))
                for _ in range(80):
                    ok,im=cap.read()
                    if not ok:break
                    writer.write(cv2.resize(im,(480,360)))
                cap.release();writer.release()
                with clip.open('rb') as stream:r=c.request('POST','/api/analyze',data={'calib':cal},files={'video':('valid.mp4',stream,'video/mp4')})
            body=r.json();c.ok(re.fullmatch('up-[a-f0-9]+',body.get('id','')),'new upload id');run_id=body['id'];d=runs/run_id;c.observed['created_run']=run_id
            for name in ['run.json','floor.mp4','shadow.mp4','spacetime.png']:c.ok((d/name).is_file(),name+' created')
            c.ok(any(x['id']==run_id for x in c.request('GET','/api/runs').json()),'new run listed')
    finally:
        created=set(p.name for p in runs.glob('up-*'))-before
        if id!='API-ANALYZE-SUCCESS':c.eq(created,set(),'no temporary upload directory remains')
        for name in created:shutil.rmtree(runs/name)
        c.observed['new_up_directories_after_cleanup']=sorted(set(p.name for p in runs.glob('up-*'))-before)


def overflow(c):
    reset(c)
    async def flood():
        limits=httpx.Limits(max_connections=768,max_keepalive_connections=768)
        async with httpx.AsyncClient(timeout=45,limits=limits,trust_env=False) as client:
            async with client.stream('GET',BASE+'/api/alerts/stream') as response:
                lines=response.aiter_lines();initial=[]
                async for line in lines:
                    initial.append(line)
                    if line=='':break
                payload={'run':'demo','state':'someone','level':'watch','bearing_deg':75,'confidence':.9,'t':1}
                # Alternating states on hundreds of real concurrent requests overflow the server subscriber queue.
                responses=await asyncio.gather(*(client.post(BASE+'/api/alerts',json={**payload,'state':'clear' if i%2 else 'someone','level':None if i%2 else 'watch'}) for i in range(768)))
                for r in responses:c.network.append({'event':'http','method':'POST','url':BASE+'/api/alerts','status':r.status_code,'body':r.json()})
                text=[];closed=False
                try:
                    async with asyncio.timeout(8):
                        async for line in lines:text.append(line)
                    closed=True
                except TimeoutError:pass
                return text,closed
    with ThreadPoolExecutor(max_workers=1) as executor:lines,closed=executor.submit(lambda:asyncio.run(flood())).result()
    c.observed.update(stream_lines=lines,stream_closed=closed);c.ok('event: resync' in lines,'stream resync event');c.ok(any('subscriber too slow; reconnect' in x for x in lines),'overflow reason');c.ok(closed,'overflow stream closes')


def special_empty(browser,tmp):
    empty=tmp/'empty';empty.mkdir()
    with serve(empty,'empty'):
        def check(c):
            c.goto('/?autoplay=0');c.page.wait_for_function("document.querySelector('#console .empty b')?.textContent==='No recorded runs yet.'");c.eq(c.request('GET','/api/runs').json(),[],'real empty list');c.eq(c.page.locator('#runSel option').count(),0,'empty has no options');c.observed['empty_case']='HTTP 200 [], no fabricated option'
            empty.rmdir()
            try:
                c.goto('/?autoplay=0');c.page.wait_for_function("document.querySelector('#console .empty b')?.textContent==='Runs could not be listed.'");c.eq(c.page.locator('#runSel option').count(),0,'failed request has no options');c.observed['failed_case']='Real missing runs directory caused HTTP 500; unavailable panel and zero options'
            finally:empty.mkdir()
        run(browser,'EDGE-RUNS-EMPTY-FALLBACK',check)


def special_missing(browser,tmp):
    runs=tmp/'missing';(runs/'demo').mkdir(parents=True);(runs/'vanishing').mkdir()
    for name in ['demo','vanishing']:shutil.copyfile(ROOT/'web/runs/demo/run.json',runs/name/'run.json')
    with serve(runs,'missing'):
        def check(c):
            c.goto('/?autoplay=0',True);(runs/'vanishing/run.json').unlink();c.page.select_option('#runSel','vanishing');c.page.wait_for_function("document.querySelector('#console .empty b')?.textContent==='That run could not be loaded.'")
            c.eq(c.text('#console .empty b'),'That run could not be loaded.','bold text');c.eq(c.page.locator('#console .empty').evaluate('(e)=>e.childNodes[1].textContent'),'Check that runs/vanishing/run.json exists, or pick another run.','following text');c.eq(c.page.locator('#console > *').count(),1,'console replaced by one panel');c.observed['panel']=c.text('#console');c.page.keyboard.press('ArrowRight');c.page.keyboard.press('Space')
        run(browser,'EDGE-RUN-LOAD-NOT-FOUND',check)


def special_token(browser):
    token=secrets.token_urlsafe(24)
    with serve(stage='token',token=token):
        def check(c):
            c.goto()
            for headers in [{},{'Authorization':'Bearer invalid-throwaway'}]:c.eq(c.request('POST','/api/alerts/status',status=401,json={'run':'demo','live':True},headers=headers).json(),{'detail':'alert token required'},'token refused')
            r=c.request('POST','/api/alerts/status',json={'run':'demo','live':True},headers={'Authorization':'Bearer '+token});c.eq(r.json()['live'],True,'valid token accepted');c.observed['summary']='Throwaway process token: missing/invalid bearer 401 exact detail; valid bearer 200. Token excluded from evidence.'
        run(browser,'API-ALERTS-AUTH-TOKEN',check)


def special_multi(browser):
    env={**os.environ,'WEB_CONCURRENCY':'2'};env.pop('PERISCOPE_ALERT_TOKEN',None)
    with (OUT/'multi-worker-startup.log').open('w') as log:
        proc=subprocess.Popen([PYTHON,'-m','uvicorn','server:app','--host','127.0.0.1','--port','8740','--workers','1'],cwd=ROOT,env=env,stdout=log,stderr=log)
        record={'stage':'multi-worker-refusal','pid':proc.pid,'killed':False};LIFECYCLE['servers'].append(record)
        try:proc.wait(timeout=15)
        finally:
            if proc.poll() is None:proc.terminate();proc.wait(timeout=8)
            record.update(killed=proc.poll() is not None,exit_code=proc.returncode);write_json(OUT/'lifecycle.json',LIFECYCLE)
    with serve(stage='single-worker'):
        def check(c):
            c.goto();log=(OUT/'multi-worker-startup.log').read_text();c.ok('RuntimeError: the alert feed is process-local: run a single worker' in log,'startup raises required RuntimeError');c.ok('Application startup failed' in log,'startup fails');c.eq(c.request('GET','/api/health').json(),{'ok':True},'single worker starts');shutil.copyfile(OUT/'multi-worker-startup.log',c.dir/'startup.log')
        run(browser,'API-MULTI-WORKER-REFUSED',check)


def main():
    subprocess.run([SLOT,'acquire','periscope-audit-reverify'],check=True)
    try:
        with tempfile.TemporaryDirectory(prefix='periscope-reverify-') as temporary,sync_playwright() as pw:
            tmp=Path(temporary);browser=pw.chromium.launch(headless=True,executable_path=CHROME)
            switch=ROOT/'web/runs/reverify-switch'
            try:
                # Real persisted second run for the run-switch row; use the demo media without overwriting demo.
                switch.mkdir()
                for f in (ROOT/'web/runs/demo').iterdir():
                    if f.is_file():shutil.copyfile(f,switch/f.name)
                with serve():
                    for id in ROWS:
                        if id in ('EDGE-RUNS-EMPTY-FALLBACK','EDGE-RUN-LOAD-NOT-FOUND','API-ALERTS-AUTH-TOKEN','API-MULTI-WORKER-REFUSED'):continue
                        width=375 if '375PX' in id else 1280
                        if id.startswith('ENG-'):fn=engine
                        elif id.startswith('UI-CALIBRATE-') or 'CALIB-' in id or id=='EDGE-375PX-CALIBRATE-LAYOUT':fn=calibration
                        elif id.startswith('UI-') or id=='EDGE-375PX-CONSOLE-LAYOUT' or id=='EDGE-375PX-SYNTHETIC-LABEL' or id.startswith('EDGE-INTERRUPT-'):fn=console_ui
                        else:fn=api
                        run(browser,id,fn,width=width,reduced='reduce' if id=='EDGE-INTERRUPT-REDUCED-MOTION' else None)
                special_empty(browser,tmp);special_missing(browser,tmp);special_token(browser);special_multi(browser)
            finally:
                shutil.rmtree(switch,ignore_errors=True);browser.close()
    finally:
        subprocess.run([SLOT,'release','periscope-audit-reverify'],check=True);LIFECYCLE['slot_released']=True;write_json(OUT/'lifecycle.json',LIFECYCLE)
    missing=set(ROWS)-set(RESULTS)
    print(json.dumps({'checked':len(RESULTS),'missing':sorted(missing),'pass':sum(r['status']=='PASS' for r in RESULTS.values()),'fail':sum(r['status']=='FAIL' for r in RESULTS.values())}),flush=True)

if __name__=='__main__':main()
