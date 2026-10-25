# Run-list fix re-verification

All four requested rows passed against real uvicorn at `127.0.0.1:8740` and Chrome for Testing 156.0.8078.4, using a fresh browser context/page for each case and a 1280×800 viewport. No HTTP responses were mocked. Every case had zero console errors, page errors, failed requests, and unexpected HTTP 4xx/5xx responses.

- `EDGE-RUNS-EMPTY-FALLBACK`: Both an empty temporary catalog and that catalog removed after server startup returned HTTP 200 `[]`, with no run options. The missing directory was recreated. Previous evidence is preserved byte-for-byte in `../EDGE-RUNS-EMPTY-FALLBACK/attempt-500/`.
- `API-RUNS`: The normal `web/runs` catalog returned HTTP 200 and the required demo metadata, including 380 frames.
- `UI-RUN-SELECT`: Selector options matched the real catalog; the selected value was `demo` with the required title.
- `EDGE-RUN-LOAD-NOT-FOUND`: The temporary catalog contained copies of demo metadata in `demo/` and `vanishing/`. After the catalog response, the browser's original resolve request was briefly intercepted to delete only the temporary `vanishing/run.json`, then continued unmodified to uvicorn. The server returned HTTP 200 `{"run": null}`; the required bold heading and detail were displayed, with no 404.

The per-row `run-list-fix/` directories contain screenshots, console and network logs, and observed results. `results.json` collects those results. `check.py` is the executed verification harness; system Python supplied Playwright and `.venv/bin/python` supplied uvicorn and pytest. A temporary untracked `.venv` symlink pointed at the main repository environment and was removed afterward.

`.venv/bin/python -m pytest -q`: **82 passed in 51.28s**, exit code 0 (`pytest.txt`). Pytest did not determine any UI row status.

The first harness attempt passed both empty-catalog cases, then its port availability check encountered TCP address reuse while switching servers. That check was corrected to use `SO_REUSEADDR`, and the complete verification passed. Its uvicorn PID 56363 was terminated and its slot released (`attempt1-lifecycle.json`). The complete run terminated only its own uvicorn PIDs 60546, 60914, and 61194; the `periscope-audit-runlist` heavy slot was released (`lifecycle.json`).

`protected-files.json` confirms identical before/after hashes for the server, console source, all demo files, and existing sweep artifacts. Only the four requested status/evidence cells in `AUDIT.md` were updated. No product source or expected-result cells changed. No deployment or push was performed. Changes are left uncommitted under the authoritative Loom worker instruction.
