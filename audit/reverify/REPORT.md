# Phase 4 re-verification

Integration HEAD: `4456dc6` (includes Phase 3 fixes). All 65 previously PASS/FAIL rows were re-run against the real local server and Chrome for Testing 156.0.8078.4. Desktop viewport: 1280×800; narrow viewport: 375×812. No route interception, fabricated HTTP responses, mocked server transport, or product-source edits were used.

Final AUDIT.md totals: **64 PASS, 1 FAIL, 12 TODO, 0 UNTESTED**. The 12 assigned TODO rows, every expected-result cell, and all fix-cell text remain byte-for-byte unchanged. Each of the 65 rechecked rows has a screenshot, console/page-error log, network log, and result JSON in its own directory. Progress was flushed after every row; no commits were made under the Loom no-commit instruction.

## Remaining failure

**EDGE-RUNS-EMPTY-FALLBACK** — Expected: both an empty and a failed GET /api/runs must avoid the fabricated “Synthetic corner · red top · lit hallway” option, with zero console errors (and the audit's zero-unexpected-HTTP-failure requirement).

Observed: the empty case used a temporary PERISCOPE_RUNS directory, returned HTTP 200 `[]`, displayed “No recorded runs yet.” and had zero options/errors. For the failed case, removing only that temporary directory made the real server return HTTP 500. The UI displayed “Runs could not be listed.” and still had zero options. Chrome nevertheless emitted `Failed to load resource: the server responded with a status of 500 (Internal Server Error)`. This fails the required console/network gate. No demo files were removed or overwritten. See [evidence](EDGE-RUNS-EMPTY-FALLBACK/).

## Verification highlights

- The other seven former FAIL rows passed from fresh checks: UI-SERVE-LOCAL, API-HEALTH, API-ALERTS-STREAM-HEARTBEAT, EDGE-375PX-SYNTHETIC-LABEL, EDGE-RUN-LOAD-NOT-FOUND, EDGE-ALERT-MALFORMED-BODY, EDGE-ALERT-KEEPALIVE-TIMEOUT.
- Three browser heartbeat gaps (seconds): [4.00219999999553, 4.00170000000298, 4.00220000000298]. Server timestamp gaps: [4.002319097518921, 4.001550912857056, 4.0022971630096436]. Every gap was <=5.0 seconds.
- API-ANALYZE-TOO-LARGE streamed a real 525,336,576-byte file via HTTP multipart, returned 413 with exact detail `clip too large (500 MB max)`, deleted the fixture, and left no up-* directory.
- API-ANALYZE-SUCCESS analyzed an 80-frame clip decoded from the demo and resized to the calibration's 480×360 dimensions, created the required artifacts, and appeared in the real run listing. Generated uploads were removed after verification.
- API-ALERTS-AUTH-TOKEN used a random throwaway token solely in its server process. Missing/invalid bearer returned 401, valid bearer returned 200. No token value or Authorization header was saved in evidence.
- API-ALERTS-AUTH-LOOPBACK used real HTTP with Uvicorn's trusted-loopback proxy header to assign a non-loopback request.client address; the production dependency returned the exact 403 detail.
- Subscriber overflow was exercised with 768 real concurrent HTTP posts; the stream emitted the required resync reason and closed.
- Pytest: **81 passed in 58.79s**. Full stdout: [pytest.txt](pytest.txt). Pytest was not used to mark UI rows PASS.

## Cleanup and audit-runner corrections

Server PIDs **71504, 1406, 14517, 19104, 19296, 19390, 19401** all exited. PID 19390 was the intentionally rejected multi-worker startup (exit 3); every serving instance was terminated by its recorded PID. Chrome was closed. The heavy slot `periscope-audit-reverify` was released after both invocations; the slot directory is empty. See [lifecycle.json](lifecycle.json).

No up-* directory, switch-run fixture, temporary oversized file, or temporary runs directory remains. Product source, web/runs/demo, and results/sweep.* were not changed. Only AUDIT.md and audit/reverify/ were changed. No deploy, commit or push was performed.

Initial harness defects were corrected and those rows re-run from fresh pages/HTTP: clipboard completion needed awaiting; the valid upload writer needed resized frames; `.big` needed scoping to the alert panel; score numbers/units needed separate DOM reads because CSS supplies their spacing; the async HTTP flood needed a thread outside Playwright's event loop. Their initial evidence remains in each row's `attempt-1/`, while the row directory's root result/log/screenshot is the final check. A port preflight required SO_REUSEADDR between isolated server runs; the final three cases completed in the second invocation. The first run's traceback is retained transparently in runner.log.

No console/page errors or unexpected HTTP failures remain in the 64 passing checks. The genuine failed-run-list request described above is the sole remaining failing surface.
