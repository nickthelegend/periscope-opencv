# Testing

Date: 2026-10-26

Counts are from the 77 data rows in `AUDIT.md` after the run-list re-check. Expected-result cells were not changed.

| Status | Count |
|---|---|
| PASS | 76 |
| FAIL | 0 |
| UNTESTED | 1 |
| TODO | 0 |

## Pytest

Fresh run in this worktree: `uv venv .venv -p 3.12`, `uv pip install -p .venv/bin/python -r requirements.txt`, then `.venv/bin/python -m pytest -q`. Exit code 0.

```
82 passed in 55.68s
```

## UNTESTED

- **CLI-SCORE-FOOTAGE-REAL** — needs a real corner clip and a hidden-hallway clip as FILMING.md describes (`data/raw/take1_corner.mov` and `data/raw/take1_hidden.mov` are absent; no footage invented). Evidence: `audit/cli/reverify/footage-absent.txt`.

## Mocks, stubs, console and network errors

No mock, stub, or console/network error remains. No row is FAIL. Browser and HTTP evidence cells record zero console/page errors and no unexpected HTTP failures. The only open item is CLI-SCORE-FOOTAGE-REAL, which is UNTESTED because those two clips are absent.
