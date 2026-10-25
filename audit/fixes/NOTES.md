# Phase 3 fix evidence

All eight FAIL rows have root-cause fixes and focused checks. Their statuses remain **FAIL** for the separate re-verification task. Expected cells and PASS rows are unchanged. No row was moved to UNTESTED; none of these failures needs footage or a credential.

The authoritative Loom worker instructions prohibit commits in this worktree and say Loom commits and merges the changes. Consequently there are **no fix commit hashes yet**. The fix cells contain the proposed subjects below, for Loom to use when committing the corresponding diffs.

| FAIL ID | Proposed commit subject | Check / evidence |
|---|---|---|
| UI-SERVE-LOCAL | Serve the Periscope favicon on console and API pages | B: exact title/H1 and HTTP 200; favicon SVG and legacy favicon URL return 200. [console/network](favicon-console-health-network.json), [desktop](console-desktop.png). |
| API-HEALTH | Serve the Periscope favicon on console and API pages | B: exact `{"ok": true}` and favicon responses; P: `tests/test_run_api.py::test_favicon_and_health`. |
| API-ALERTS-STREAM-HEARTBEAT | Send alert heartbeats before the maximum interval | B: three received intervals 4.0004, 4.0025, 4.0035 s, all below 5.0 s; matching server timestamp intervals. P: strengthened `test_heartbeat_carries_liveness` and existing starvation test. [measurements](results.json). |
| EDGE-375PX-SYNTHETIC-LABEL | Keep synthetic disclosure visible on narrow screens | B: visible exact “Synthetic scene” label, document width 375 px. [screenshot](synthetic-375px.png), [console](synthetic-375px-console.json). |
| EDGE-RUNS-EMPTY-FALLBACK | Populate run selection only from persisted metadata | B: genuinely empty directory and malformed persisted JSON both produce GET `/api/runs` = `[]`, no options, disabled selector, honest empty state. No hardcoded demo fallback. [empty](empty-run-list-network.json), [corrupt](corrupt-run-list-network.json). P: run-list/disk deletion/corrupt metadata tests. |
| EDGE-RUN-LOAD-NOT-FOUND | Recover cleanly when a selected run disappears | B: delete selected run's real metadata after listing, select it, assert exact error copy, resize and press keys, then select demo and play/pause successfully. Availability lookup returns 200 with `run: null`; no missing static-file request, page errors or resource errors. [error](missing-run-error.png), [network](missing-run-recovery-network.json), [console](missing-run-recovery-console.json). |
| EDGE-ALERT-MALFORMED-BODY | Return the specified alert level validation detail | B: real POST returns 422 with exact string detail. P: both inconsistent state/level combinations assert the exact response; other field validation retains its existing details. |
| EDGE-ALERT-KEEPALIVE-TIMEOUT | Include live=false in stale alert events | B: real SSE watchdog event has `reason: "timeout"`, `live: false`, `run: "demo"`. P: timeout plus pause/run-switch tests assert the field. [measurements](results.json). |

## Commands run

P (after acquiring the heavy slot; fixture configured to bind 8740):

```sh
"/Volumes/Extreme SSD/Projects/grokbot/tools/heavy-slot.sh" acquire periscope-audit-fix
PERISCOPE_TEST_PORT=8740 "/Volumes/Extreme SSD/Projects/wave1/periscope-opencv/.venv/bin/python" -m pytest -q
"/Volumes/Extreme SSD/Projects/grokbot/tools/heavy-slot.sh" release periscope-audit-fix
```

Observed: **81 passed in 49.04 s**. The initial focused selection also passed: `6 passed, 23 deselected` for `tests/test_run_api.py tests/test_alerts.py -k 'run_list or corrupt_metadata or favicon or exact_detail or field_details'`.

B (only the failed browser surfaces; no whole-audit rerun):

```sh
python3 audit/fixes/check_fixes.py \
  --python "/Volumes/Extreme SSD/Projects/wave1/periscope-opencv/.venv/bin/python" \
  --chrome "/Users/jaibajrang/Library/Caches/ms-playwright/chromium-1248/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
```

The script acquires/releases `periscope-audit-fix`, starts each uvicorn on `127.0.0.1:8740`, and terminates/waits for its PID. Chrome for Testing **156.0.8078.4** passed all six check groups. Final console logs have zero errors/page errors; network logs have zero unexpected 4xx/5xx or failed requests. The deliberately invalid alert POST is made through Playwright's API client and asserts the required 422. [Results](results.json), [check implementation](check_fixes.py).

Both HTML scripts also passed `node --check` after extracting their inline `<script>` content. `git diff --check` passed.

## Implementation notes

- Run options are created with DOM `Option` objects from the actual server response. A corrupt run is unavailable, never replaced with demo data.
- GET `/api/runs/{run_id}` is an availability lookup over the persisted metadata. A normal unavailable result is `{"run": null}`. It avoids requesting a file already removed from disk. The original static run assets remain available at their existing URLs.
- Failed load cleanup clears the active run, hides stale readings and preserves the console nodes and handlers for recovery. Resize/keyboard callbacks stop when no run is loaded. Concurrent loads cannot apply stale results.
- Heartbeats are scheduled at 80% of their maximum interval, reserving time for event-loop/network delay. Tests now enforce the maximum instead of the former generous tolerance.
- No mock routes, fallback runs, invented footage, keys, deploys, pushes, or changes to `results/sweep.*` were used. Temporary run-list checks copy the existing synthetic demo metadata unchanged; rendered synthetic content remains labelled synthetic.

Earlier browser-check artifacts are retained under [attempt1](attempt1/). That attempt verified the product assertions but the harness then counted its own explicit `EventSource.close()` as `net::ERR_ABORTED`. The final harness closes the browser after assertions/evidence capture. Startup retries also corrected a stale Playwright default executable path and enabled address reuse in the port preflight; neither required a product change.
