"""Scoped real-server/Chrome re-verification; acquire the heavy slot before running."""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
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

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "audit/reverify"
HERE = Path(__file__).resolve().parent
BASE = "http://127.0.0.1:8740"
CHROME = "/Users/jaibajrang/Library/Caches/ms-playwright/chromium-1248/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
SLOT = "/Volumes/Extreme SSD/Projects/grokbot/tools/heavy-slot.sh"
TITLE = "Synthetic corner · red top · lit hallway"
DEMO = {"id": "demo", "title": TITLE, "kind": "synthetic", "frames": 380}
RESULTS = {}
LIFECYCLE = {"slot": "periscope-audit-runlist", "servers": [], "slot_released": False}


def write(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def protected_hashes():
    files = [ROOT / "server.py", ROOT / "web/index.html"]
    files += list((ROOT / "web/runs/demo").rglob("*"))
    files += list((ROOT / "results").glob("sweep.*"))
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(files) if p.is_file()}


@contextmanager
def serve(runs, stage):
    with socket.socket() as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("127.0.0.1", 8740))
    env = dict(os.environ)
    env.pop("PERISCOPE_RUNS", None)
    env.pop("PERISCOPE_ALERT_TOKEN", None)
    env["WEB_CONCURRENCY"] = "1"
    if runs is not None:
        env["PERISCOPE_RUNS"] = str(runs)
    with (HERE / f"server-{stage}.log").open("w") as log:
        proc = subprocess.Popen([str(ROOT / ".venv/bin/python"), "-m", "uvicorn", "server:app",
                                 "--host", "127.0.0.1", "--port", "8740", "--workers", "1"],
                                cwd=ROOT, env=env, stdout=log, stderr=log)
        record = {"stage": stage, "pid": proc.pid, "killed": False}
        LIFECYCLE["servers"].append(record)
        write(HERE / "lifecycle.json", LIFECYCLE)
        try:
            deadline = time.monotonic() + 20
            while True:
                if proc.poll() is not None:
                    raise RuntimeError(f"uvicorn exited: {stage}")
                try:
                    with urllib.request.urlopen(BASE + "/api/health", timeout=1) as response:
                        assert response.status == 200
                    break
                except OSError:
                    if time.monotonic() > deadline:
                        raise
                    time.sleep(0.1)
            yield
        finally:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=5)
            record.update(killed=proc.poll() is not None, exit_code=proc.returncode)
            write(HERE / "lifecycle.json", LIFECYCLE)


def check(browser, row, case, action):
    directory = OUT / row / "run-list-fix" / case
    directory.mkdir(parents=True, exist_ok=True)
    context = browser.new_context(viewport={"width": 1280, "height": 800})
    page = context.new_page()
    messages, errors, network, failed, issues = [], [], [], [], []
    page.on("console", lambda m: messages.append({"type": m.type, "text": m.text}))
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("response", lambda r: network.append({"url": r.url, "method": r.request.method, "status": r.status}))
    page.on("requestfailed", lambda r: failed.append({"url": r.url, "failure": r.failure}))
    observed = {}
    try:
        action(page, observed)
    except Exception as exc:
        issues.append(f"{type(exc).__name__}: {exc}")
    page.wait_for_timeout(1000)
    issues.extend("console error: " + m["text"] for m in messages if m["type"] == "error")
    issues.extend("page error: " + e for e in errors)
    issues.extend("unexpected HTTP: " + str(r) for r in network if r["status"] >= 400)
    issues.extend("failed request: " + str(r) for r in failed)
    page.screenshot(path=str(directory / "screenshot.png"), full_page=True)
    write(directory / "console.json", {"messages": messages, "page_errors": errors})
    write(directory / "network.json", {"responses": network, "failed": failed})
    result = {"row": row, "case": case, "status": "FAIL" if issues else "PASS",
              "observed": observed, "issues": issues, "viewport": page.viewport_size,
              "browser": "Chrome for Testing", "browser_version": browser.version,
              "timestamp_utc": datetime.now(timezone.utc).isoformat()}
    write(directory / "result.json", result)
    RESULTS.setdefault(row, []).append(result)
    context.close()
    print(f"{row} / {case}: {result['status']}", flush=True)


def empty(page, observed):
    with page.expect_response(lambda r: r.url == BASE + "/api/runs") as pending:
        assert page.goto(BASE + "/?autoplay=0").status == 200
    response = pending.value
    observed.update(catalog_status=response.status, catalog=response.json())
    assert response.status == 200 and response.json() == [], "Expected HTTP 200 []"
    page.locator("#console b").wait_for()
    observed["options"] = page.locator("#runSel option").evaluate_all("els => els.map(e => ({value:e.value,text:e.textContent}))")
    observed["panel"] = page.locator("#console").inner_text()
    assert observed["options"] == [], f"Expected no demo option; observed {observed['options']}"


def normal(page, observed):
    with page.expect_response(lambda r: r.url == BASE + "/api/runs") as pending:
        assert page.goto(BASE + "/?autoplay=0").status == 200
    response = pending.value
    observed.update(catalog_status=response.status, catalog=response.json())
    assert response.status == 200 and isinstance(response.json(), list) and DEMO in response.json(), "Expected HTTP 200 array containing demo metadata"
    page.wait_for_function("document.querySelector('#clock')?.textContent.includes('/ 19.00 s')")
    page.wait_for_function("['vFloor','vShadow','vHidden'].every(id => document.getElementById(id).readyState >= 2)")
    observed["options"] = page.locator("#runSel option").evaluate_all("els => els.map(e => ({value:e.value,text:e.textContent}))")
    observed["selected_value"] = page.locator("#runSel").input_value()
    observed["selected_text"] = page.locator("#runSel option:checked").inner_text()
    assert observed["options"] == [{"value": r["id"], "text": r["title"]} for r in observed["catalog"]], "Options differ from real catalog"
    assert observed["selected_value"] == "demo" and observed["selected_text"] == TITLE, "Wrong selected option"


def missing(page, observed, metadata):
    def delete_then_continue(route):
        # Pass the original HTTP request through; no response mocking or synthetic failure.
        metadata.unlink()
        observed["metadata_deleted_before_resolve"] = not metadata.exists()
        route.continue_()
    page.route("**/api/runs/vanishing", delete_then_continue)
    with page.expect_response(lambda r: r.url == BASE + "/api/runs") as catalog:
        with page.expect_response(lambda r: r.url == BASE + "/api/runs/vanishing") as resolved:
            assert page.goto(BASE + "/?autoplay=0&run=vanishing").status == 200
    observed.update(catalog_status=catalog.value.status, catalog=catalog.value.json(),
                    resolve_status=resolved.value.status, resolve_body=resolved.value.json())
    assert catalog.value.status == 200 and any(r["id"] == "vanishing" for r in observed["catalog"]), "Missing run was not listed before deletion"
    assert resolved.value.status == 200 and resolved.value.json() == {"run": None}, "Expected normal unavailable response, no 404"
    page.locator("#console b").wait_for()
    observed["heading"] = page.locator("#console b").inner_text()
    observed["panel_html"] = page.locator("#console").inner_html()
    observed["panel"] = page.locator("#console").inner_text()
    assert observed["heading"] == "That run could not be loaded.", "Missing bold heading"
    assert page.locator("#console [role=status]").evaluate("el => el.childNodes[1].textContent") == "Check that runs/vanishing/run.json exists, or pick another run.", "Wrong recovery detail"


def update_rows():
    audit = ROOT / "AUDIT.md"
    before = audit.read_text().splitlines()
    after = []
    for line in before:
        cells = line.split("|")
        if len(cells) == 8 and cells[1].strip() in RESULTS:
            row = cells[1].strip()
            results = RESULTS[row]
            passed = all(r["status"] == "PASS" for r in results)
            cells[4] = " PASS " if passed else " FAIL "
            descriptions = {
                "EDGE-RUNS-EMPTY-FALLBACK": "Cases A (empty directory) and B (directory removed after startup): real GET /api/runs returned HTTP 200 []; no selector options; missing directory recreated.",
                "API-RUNS": "Normal web/runs catalog returned HTTP 200 and a JSON array containing the exact demo id, title, synthetic kind and 380-frame count.",
                "UI-RUN-SELECT": "Fresh Chrome page: options exactly matched real GET /api/runs; selected value demo and text Synthetic corner · red top · lit hallway.",
                "EDGE-RUN-LOAD-NOT-FOUND": "Temporary vanishing run was listed, then its run.json deleted before real resolve; HTTP 200 {run: null}; bold heading and recovery detail matched exactly, no 404.",
            }
            detail = descriptions[row] if passed else "; ".join(issue for r in results for issue in r["issues"])
            cells[5] = f" [Chrome recheck](audit/reverify/{row}/run-list-fix/) — {detail} Zero console/page errors, failed requests or unexpected 4xx/5xx." + " " if passed else f" [Chrome recheck](audit/reverify/{row}/run-list-fix/) — {detail} "
            changed = "|".join(cells)
            assert all(cells[i] == line.split("|")[i] for i in (0, 1, 2, 3, 6, 7))
            after.append(changed)
        else:
            after.append(line)
    audit.write_text("\n".join(after) + "\n")


before_hashes = protected_hashes()
try:
    old = OUT / "EDGE-RUNS-EMPTY-FALLBACK"
    archive = old / "attempt-500"
    archive.mkdir(exist_ok=True)
    for path in old.iterdir():
        if path.is_file():
            assert not (archive / path.name).exists(), "Refuse to overwrite previous evidence"
            shutil.move(str(path), str(archive / path.name))
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=CHROME, headless=True)
        try:
            with tempfile.TemporaryDirectory(prefix="periscope-runlist-") as temp:
                runs = Path(temp) / "runs"
                runs.mkdir()
                with serve(runs, "empty-and-missing-catalog"):
                    check(browser, "EDGE-RUNS-EMPTY-FALLBACK", "case-A-empty", empty)
                    shutil.rmtree(runs)
                    assert not runs.exists()
                    check(browser, "EDGE-RUNS-EMPTY-FALLBACK", "case-B-removed-after-startup", empty)
                    assert runs.is_dir(), "Server did not recreate missing catalog"
            with serve(None, "normal-catalog"):
                check(browser, "API-RUNS", "normal-catalog", normal)
                check(browser, "UI-RUN-SELECT", "normal-catalog", normal)
            with tempfile.TemporaryDirectory(prefix="periscope-missing-run-") as temp:
                runs = Path(temp) / "runs"
                for run_id in ("demo", "vanishing"):
                    (runs / run_id).mkdir(parents=True)
                    shutil.copyfile(ROOT / "web/runs/demo/run.json", runs / run_id / "run.json")
                with serve(runs, "missing-run"):
                    check(browser, "EDGE-RUN-LOAD-NOT-FOUND", "deleted-metadata", lambda p, o: missing(p, o, runs / "vanishing/run.json"))
        finally:
            browser.close()
    with (HERE / "pytest.txt").open("w") as log:
        tests = subprocess.run([str(ROOT / ".venv/bin/python"), "-m", "pytest", "-q"], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
    LIFECYCLE["pytest_exit_code"] = tests.returncode
    after_hashes = protected_hashes()
    write(HERE / "protected-files.json", {"before": before_hashes, "after": after_hashes, "unchanged": before_hashes == after_hashes})
    assert before_hashes == after_hashes, "Protected product files changed"
    update_rows()
    write(HERE / "results.json", RESULTS)
finally:
    released = subprocess.run([SLOT, "release", "periscope-audit-runlist"], capture_output=True, text=True)
    LIFECYCLE["slot_released"] = released.returncode == 0
    write(HERE / "lifecycle.json", LIFECYCLE)
    print(json.dumps(LIFECYCLE), flush=True)
