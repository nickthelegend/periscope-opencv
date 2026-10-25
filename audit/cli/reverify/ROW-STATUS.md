# CLI re-verify

AUDIT.md was not edited. Status is PASS only when the command observation matches that row's expected cell, with the output paths this run was told to use.

CLI-CALIBRATE-FRAME-ONLY, PASS, audit/cli/reverify/calibrate-frame-only.txt, exit 0; stdout contains "wrote .../calib/frame-only/first_frame.png"; that file exists; calib.json was not created.
CLI-CALIBRATE-AUTO, PASS, audit/cli/reverify/calibrate-auto.txt, exit 0 on the synthetic frame; stdout is auto-detection JSON then {"calib","preview"}; calib/auto/calib.json has "source": "auto".
CLI-CALIBRATE-MARKS, PASS, audit/cli/reverify/calibrate-marks.txt, exit 0; --marks used the five Scene.marks_px() points; wrote calib/marks/calib.json ("source": "marks") and calib_preview.png; stdout is one {"calib","preview"} line.
EDGE-CLI-CALIB-MISSING-FLAGS, PASS, audit/cli/reverify/calibrate-missing-flags.txt, exit 1; stderr is "give --marks or --auto"; calib/missing-flags/calib.json was not written.
EDGE-CLI-CALIB-UNREADABLE-VIDEO, PASS, audit/cli/reverify/calibrate-unreadable.txt, exit 1 on audit/cli/reverify/does-not-exist.mov --auto; stderr contains "cannot read audit/cli/reverify/does-not-exist.mov".
EDGE-CLI-CALIB-AUTO-REFUSED, PASS, audit/cli/reverify/calibrate-auto-refused.txt, exit 1 for --auto --min-confidence 1.1 (detected 1.00); stderr contains "auto calibration refused" and "click the tape marks and use --marks"; calib.json was not written.
CLI-BENCH, PASS, audit/cli/reverify/bench.txt, exit 0; stdout JSON has numeric ms_640x360_stabilised, ms_640x360_no_stab, ms_1080p_in_stabilised, ms_phase_correlate_640x360, and ms_binning_640x360.
CLI-SNR-SWEEP-QUICK, PASS, audit/cli/reverify/snr-sweep.txt, exit 0; --out audit/cli/reverify/sweep-quick wrote sweep.json, sweep.md, and sweep.png; stdout has per-row metrics and "signal floor (per-pixel SNR at 3 m):"; results/ was left untouched.
CLI-MAKE-DEMO, PASS, audit/cli/reverify/make-demo.txt, exit 0 in 21s; audit/cli/reverify/demo-rerun has run.json, floor.mp4, shadow.mp4, spacetime.png, hidden.mp4, and the three .webm copies; stdout prints score JSON and events; web/runs/demo was not rewritten.
CLI-SCORE-FOOTAGE-REAL, UNTESTED, audit/cli/reverify/footage-absent.txt, needs a real corner clip and a hidden-hallway clip as FILMING.md describes (data/raw/take1_corner.mov and data/raw/take1_hidden.mov are absent; no footage invented).
API-NO-ONCHAIN, PASS, audit/cli/reverify/grep-onchain.txt, search of *.py *.html *.js *.toml *.yml excluding AUDIT.md and audit/ found no web3, ethers, wallet, blockchain, or contract client.
CLI-NO-MCP, PASS, audit/cli/reverify/grep-mcp.txt, same search found no MCP server, FastMCP definition, or MCP config; the word mcp inside AUDIT.md and audit/ was ignored.

pytest note (not an AUDIT row): .venv/bin/python -m pytest -q exited 0 with 81 passed in 56.67s (audit/cli/reverify/pytest.txt).
