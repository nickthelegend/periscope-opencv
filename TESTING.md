# Testing

Date: 2026-10-26

Counts are from the 77 data rows in `AUDIT.md` after the CLI re-verify statuses were copied in. Expected-result cells were not changed.

| Status | Count |
|---|---|
| PASS | 75 |
| FAIL | 1 |
| UNTESTED | 1 |
| TODO | 0 |

## Pytest

This worktree has no `.venv`. A fresh run used the project virtualenv at `/Volumes/Extreme SSD/Projects/wave1/periscope-opencv/.venv/bin/python -m pytest -q`. Exit code 0.

```
81 passed in 52.45s
```

`audit/reverify/pytest.txt` is present. Its summary is:

```
81 passed in 58.79s
```

CLI re-verify note (`audit/cli/reverify/ROW-STATUS.md`, log `audit/cli/reverify/pytest.txt`): `.venv/bin/python -m pytest -q` exited 0 with 81 passed in 56.67s.

## UNTESTED

- **CLI-SCORE-FOOTAGE-REAL** — needs a real corner clip and a hidden-hallway clip as FILMING.md describes (`data/raw/take1_corner.mov` and `data/raw/take1_hidden.mov` are absent; no footage invented). Evidence: `audit/cli/reverify/footage-absent.txt`.

## Mocks, stubs, console and network errors

No FAIL row names a remaining mock or stub.

One console/network error remains on the tested surface, from **EDGE-RUNS-EMPTY-FALLBACK**: console error `Failed to load resource: the server responded with a status of 500 (Internal Server Error)`; unexpected HTTP `GET http://127.0.0.1:8740/api/runs` status 500. Evidence: `audit/reverify/EDGE-RUNS-EMPTY-FALLBACK/`.
