"""Run availability comes from persisted files, including corrupt/deleted selections."""

import asyncio
import json

import httpx

import server


def get(path):
    async def go():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(server.app), base_url="http://periscope.local") as c:
            return await c.get(path)
    return asyncio.run(go())


def test_favicon_and_health():
    assert get("/api/health").json() == {"ok": True}
    for path in ("/favicon.ico", "/favicon.svg"):
        response = get(path)
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("image/svg+xml")
        assert "<svg" in response.text


def test_missing_runs_directory_is_an_empty_catalog(tmp_path, monkeypatch):
    runs_dir = tmp_path / "missing" / "runs"
    monkeypatch.setattr(server, "RUNS", runs_dir)
    assert not runs_dir.exists()

    response = get("/api/runs")

    assert response.status_code == 200
    assert response.json() == []
    assert runs_dir.is_dir()
    assert get("/api/runs/demo").json() == {"run": None}


def test_run_list_and_resolution_follow_files(tmp_path, monkeypatch):
    metadata = json.loads((server.WEB / "runs/demo/run.json").read_text())
    monkeypatch.setattr(server, "RUNS", tmp_path)
    assert get("/api/runs").json() == []
    assert get("/api/runs/demo").json() == {"run": None}
    demo = tmp_path / "demo"
    demo.mkdir()
    f = demo / "run.json"
    f.write_text(json.dumps(metadata))
    assert get("/api/runs").json() == [{"id": "demo", "title": metadata["title"], "kind": "synthetic", "frames": 380}]
    assert get("/api/runs/demo").json() == {"run": metadata}
    f.unlink()
    response = get("/api/runs/demo")
    assert response.status_code == 200
    assert response.json() == {"run": None}
    assert get("/api/runs").json() == []


def test_corrupt_metadata_cannot_break_run_list(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "RUNS", tmp_path)
    for i, contents in enumerate(("{broken", "[]", '{"scene": null}', '{"frames": 1}', '{"title": null}')):
        d = tmp_path / f"corrupt-{i}"
        d.mkdir()
        (d / "run.json").write_text(contents)
        response = get(f"/api/runs/{d.name}")
        assert response.status_code == 200
        assert response.json() == {"run": None}
    response = get("/api/runs")
    assert response.status_code == 200
    assert response.json() == []
