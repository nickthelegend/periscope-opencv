"""Rerun checks after correcting runner timing, video sizing and selector issues; complete isolated server cases."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from playwright.sync_api import sync_playwright
import run_checks as a

a.RESULTS.update(json.loads((a.OUT/'summary.json').read_text()))
a.LIFECYCLE.update(json.loads((a.OUT/'lifecycle.json').read_text()))
a.LIFECYCLE['slot_released']=False
ids=['UI-CALIBRATE-COPY','API-ANALYZE-SUCCESS','ENG-DEMO-FRAME-127-COMING','ENG-DEMO-FRAME-194-WALKING-AWAY','ENG-GROUND-TRUTH-SCORES','EDGE-ALERT-SUBSCRIBER-OVERFLOW']
for id in ids:
    d=a.OUT/id;archive=d/'attempt-1';archive.mkdir(exist_ok=True)
    for f in list(d.iterdir()):
        if f.is_file():shutil.move(str(f),archive/f.name)
subprocess.run([a.SLOT,'acquire','periscope-audit-reverify'],check=True)
try:
    with tempfile.TemporaryDirectory(prefix='periscope-reverify-final-') as temporary,sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,executable_path=a.CHROME)
        try:
            with a.serve(stage='retry'):
                for id in ids:
                    fn=a.calibration if id=='UI-CALIBRATE-COPY' else a.engine if id.startswith('ENG-') else a.api
                    a.run(browser,id,fn)
            a.special_missing(browser,Path(temporary));a.special_token(browser);a.special_multi(browser)
        finally:browser.close()
finally:
    subprocess.run([a.SLOT,'release','periscope-audit-reverify'],check=True);a.LIFECYCLE['slot_released']=True;a.write_json(a.OUT/'lifecycle.json',a.LIFECYCLE)
print(json.dumps({'checked':len(a.RESULTS),'pass':sum(r['status']=='PASS' for r in a.RESULTS.values()),'fail':sum(r['status']=='FAIL' for r in a.RESULTS.values())}),flush=True)
