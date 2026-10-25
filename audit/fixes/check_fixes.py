"""Focused real-browser checks for Phase 3 fixes; no route interception or synthetic API responses.

Run with a Python that has Playwright, passing the app environment via --python.
The script owns the heavy slot and every server/browser process it starts.
"""

import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import time
import urllib.request

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
BASE = "http://127.0.0.1:8740"
SLOT = Path("/Volumes/Extreme SSD/Projects/grokbot/tools/heavy-slot.sh")
RESULTS = {}
parser = argparse.ArgumentParser()
parser.add_argument("--python", default=str(ROOT / ".venv/bin/python"))
parser.add_argument("--chrome", help="installed Chrome for Testing executable, if different from Playwright's default")
ARGS = parser.parse_args()


@contextmanager
def serve(runs, stage):
    with socket.socket() as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("127.0.0.1", 8740))
    with (OUT / f"server-{stage}.log").open("w") as log:
        proc = subprocess.Popen(
            [ARGS.python, "-m", "uvicorn", "server:app", "--host", "127.0.0.1", "--port", "8740", "--workers", "1"],
            cwd=ROOT, env={**os.environ, "PERISCOPE_RUNS": str(runs), "WEB_CONCURRENCY": "1"}, stdout=log, stderr=log,
        )
        try:
            deadline = time.monotonic() + 15
            while True:
                assert proc.poll() is None, f"server exited: {stage}"
                try:
                    with urllib.request.urlopen(BASE + "/api/health", timeout=1) as response:
                        assert response.status == 200
                    break
                except OSError:
                    assert time.monotonic() < deadline, "server start timed out"
                    time.sleep(0.1)
            yield
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=8)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)


@contextmanager
def page_check(browser, name, width=1280):
    context = browser.new_context(viewport={"width": width, "height": 812})
    page = context.new_page()
    console, errors, network, failed = [], [], [], []
    page.on("console", lambda msg: console.append({"type": msg.type, "text": msg.text}))
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("response", lambda response: network.append({"url": response.url, "status": response.status}))
    page.on("requestfailed", lambda request: failed.append({"url": request.url, "failure": request.failure}))
    try:
        yield page
        page.wait_for_timeout(150)
        assert not errors, errors
        assert not [msg for msg in console if msg["type"] == "error"], console
        assert not [response for response in network if response["status"] >= 400], network
        assert not failed, failed
        RESULTS[name] = {"check": "passed", **RESULTS.get(name, {})}
    finally:
        page.screenshot(path=str(OUT / f"{name}.png"), full_page=True)
        (OUT / f"{name}-console.json").write_text(json.dumps({"messages": console, "page_errors": errors}, indent=2))
        (OUT / f"{name}-network.json").write_text(json.dumps({"responses": network, "failed": failed}, indent=2))
        context.close()


def ready(page):
    page.wait_for_function("document.querySelector('#clock')?.textContent.includes('/ 19.00 s')")


def normal(browser, runs):
    with page_check(browser, "favicon-console-health") as page:
        assert page.goto(BASE + "/?autoplay=0").status == 200
        ready(page)
        assert page.title() == "Periscope · see who's coming around the corner"
        assert page.locator("h1").inner_text() == "See who's coming around the corner."
        assert page.request.get(BASE + "/api/health").json() == {"ok": True}
        assert page.request.get(BASE + "/favicon.ico").status == 200
        assert page.request.get(BASE + "/favicon.svg").status == 200
        page.screenshot(path=str(OUT / "console-desktop.png"), full_page=True)
        assert page.goto(BASE + "/calibrate.html").status == 200

    with page_check(browser, "synthetic-375px", width=375) as page:
        page.goto(BASE + "/?run=demo&autoplay=0")
        ready(page)
        assert page.locator("#kindTag").is_visible()
        assert page.locator("#kindTag").inner_text() == "Synthetic scene"
        assert page.evaluate("document.documentElement.scrollWidth") == 375

    with page_check(browser, "missing-run-recovery") as page:
        page.goto(BASE + "/?run=demo&autoplay=0")
        ready(page)
        (runs / "vanishing/run.json").unlink()
        page.select_option("#runSel", "vanishing")
        page.locator("#console .empty b").wait_for()
        assert page.locator("#console .empty b").inner_text() == "That run could not be loaded."
        assert page.locator("#console .empty").inner_text() == (
            "That run could not be loaded.\nCheck that runs/vanishing/run.json exists, or pick another run."
        )
        page.set_viewport_size({"width": 375, "height": 812})
        page.keyboard.press("ArrowRight")
        page.keyboard.press("Space")
        page.wait_for_timeout(200)
        assert not page.locator(".lower").is_visible()
        page.screenshot(path=str(OUT / "missing-run-error.png"), full_page=True)
        page.select_option("#runSel", "demo")
        ready(page)
        assert page.locator(".lower").is_visible()
        page.click("#playBtn")
        page.wait_for_function("vFloor.currentTime > 0.2 && !vFloor.paused")
        page.click("#playBtn")
        assert page.evaluate("vFloor.paused")

    with page_check(browser, "heartbeat-and-timeout") as page:
        page.goto(BASE + "/calibrate.html")
        page.evaluate("""() => {
            window.events = [];
            window.feed = new EventSource('/api/alerts/stream');
            for (const event of ['heartbeat', 'stale']) feed.addEventListener(event, e =>
                events.push({event, data: JSON.parse(e.data), received: performance.now()}));
        }""")
        page.wait_for_function("events.filter(e => e.event === 'heartbeat').length >= 4", timeout=16000)
        heartbeats = page.evaluate("events.filter(e => e.event === 'heartbeat')")
        gaps = [(b["received"] - a["received"]) / 1000 for a, b in zip(heartbeats, heartbeats[1:])]
        server_gaps = [b["data"]["t"] - a["data"]["t"] for a, b in zip(heartbeats, heartbeats[1:])]
        assert all(0 < gap <= 5 for gap in gaps + server_gaps), (gaps, server_gaps)
        for heartbeat in heartbeats:
            data = heartbeat["data"]
            assert set(data) == {"t", "live", "run", "age_s"}
            assert isinstance(data["t"], (int, float)) and isinstance(data["live"], bool)
        response = page.request.post(BASE + "/api/alerts/status", data={"run": "demo", "live": True})
        assert response.status == 200
        page.wait_for_function("events.some(e => e.event === 'stale' && e.data.reason === 'timeout')", timeout=5000)
        stale = page.evaluate("events.find(e => e.event === 'stale' && e.data.reason === 'timeout')")
        assert stale["data"]["live"] is False and stale["data"]["run"] == "demo"
        response = page.request.post(BASE + "/api/alerts", data={"run": "demo", "state": "someone", "confidence": 0.9, "t": 1})
        assert response.status == 422
        assert response.json() == {"detail": "level is required for someone and must be null for clear"}
        RESULTS["heartbeat-and-timeout"] = {"received_gaps_s": gaps, "server_gaps_s": server_gaps, "stale": stale}


def empty(browser, name):
    with page_check(browser, name) as page:
        page.goto(BASE + "/?autoplay=0")
        page.wait_for_function("document.querySelector('#console .empty b')?.textContent === 'No recorded runs yet.'")
        assert page.locator("#runSel option").count() == 0
        assert page.locator("#runSel").is_disabled()
        assert page.request.get(BASE + "/api/runs").json() == []
        assert not page.locator("#kindTag").is_visible()


subprocess.run([str(SLOT), "acquire", "periscope-audit-fix"], check=True)
try:
    with tempfile.TemporaryDirectory(prefix="periscope-fix-check-") as temporary, sync_playwright() as playwright:
        temporary = Path(temporary)
        browser = playwright.chromium.launch(headless=True, executable_path=ARGS.chrome or playwright.chromium.executable_path)
        try:
            runs = temporary / "normal"
            for name in ("demo", "vanishing"):
                (runs / name).mkdir(parents=True)
                shutil.copyfile(ROOT / "web/runs/demo/run.json", runs / name / "run.json")
            with serve(runs, "normal"):
                normal(browser, runs)
            with serve(temporary / "empty", "empty"):
                empty(browser, "empty-run-list")
            corrupt = temporary / "corrupt/broken"
            corrupt.mkdir(parents=True)
            (corrupt / "run.json").write_text("{broken")
            with serve(corrupt.parent, "corrupt"):
                empty(browser, "corrupt-run-list")
            RESULTS["browser"] = browser.version
        finally:
            browser.close()
finally:
    subprocess.run([str(SLOT), "release", "periscope-audit-fix"], check=True)
    (OUT / "results.json").write_text(json.dumps(RESULTS, indent=2) + "\n")

print(json.dumps(RESULTS, indent=2))
