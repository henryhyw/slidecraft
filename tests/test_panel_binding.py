from pathlib import Path
import json
import threading
import urllib.request
import urllib.error
from http.server import ThreadingHTTPServer

import pytest

from framework import panel_binding, run_events
from framework import panel as framework_panel
from webapp import panel
from framework.storage import ConflictError, write


@pytest.fixture
def runs(tmp_path, monkeypatch):
    monkeypatch.setenv("SLIDEPOISE_HOME", str(tmp_path / "home"))
    result = [tmp_path / "one", tmp_path / "two"]
    for root in result:
        write(root / "session.json", {"name": root.name})
    return result


def test_initial_selection_is_shared_and_survives_reopen(runs):
    initial = panel_binding.ensure()
    assert initial["run"] is None
    selected = panel_binding.select(initial["id"], runs[0], initial["revision"])
    assert panel_binding.get(initial["id"]) == selected
    assert panel_binding.ensure(initial["id"])["run"] == str(runs[0])


def test_browser_cannot_switch_after_selection(runs):
    initial = panel_binding.ensure()
    selected = panel_binding.select(initial["id"], runs[0], initial["revision"])
    with pytest.raises(ConflictError):
        panel_binding.select(initial["id"], runs[1], selected["revision"])
    with pytest.raises(ConflictError):
        panel_binding.select(initial["id"], runs[1], initial["revision"])
    assert panel_binding.get(initial["id"])["run"] == str(runs[0])


def test_agent_switch_preserves_other_conversations(runs):
    first = panel_binding.ensure(run=runs[0])
    second = panel_binding.ensure(run=runs[1])
    switched = panel_binding.ensure(first["id"], runs[1])
    assert switched["run"] == str(runs[1])
    assert switched["revision"] != first["revision"]
    assert panel_binding.get(second["id"]) == second


def test_moved_run_cannot_reopen_picker_or_silently_switch(runs):
    initial = panel_binding.ensure(run=runs[0])
    runs[0].rename(runs[0].with_name("moved"))
    assert panel_binding.ensure(initial["id"])["run"] == str(runs[0])
    with pytest.raises(ConflictError):
        panel_binding.select(initial["id"], runs[1], initial["revision"])


def test_invalid_binding_and_missing_run_are_rejected(runs):
    with pytest.raises(ValueError):
        panel_binding.ensure("../../config")
    with pytest.raises(FileNotFoundError):
        panel_binding.select("missing", runs[0], "")
    with pytest.raises(FileNotFoundError):
        panel_binding.ensure(run=runs[0] / "absent")


def test_active_panel_has_no_standalone_session_controls():
    ui = Path(__file__).resolve().parents[1] / "webapp/ui"
    source = "\n".join((ui / name).read_text() for name in ("index.html", "session-panel.js"))
    for removed in ("panel-brand-row", "session-menu", "new-run", "attach-run", "open-run-folder", "Conversation companion", "Your slide, alongside", "This tab follows its own run"):
        assert removed not in source
    assert "data-continue-run" in source
    source += (Path(__file__).resolve().parents[1] / "webapp/panel.py").read_text()
    for stage in ("Plan", "Style & Assets", "Design & Analysis", "PowerPoint"):
        assert stage in source


def test_agent_can_open_each_reader_stage_directly(runs, monkeypatch):
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return b'{"service":"slidepoise"}'

    monkeypatch.setattr(framework_panel.urllib.request, "urlopen", lambda *_args, **_kwargs: Response())
    for stage in ("plan", "style", "design", "powerpoint"):
        result = framework_panel.open_panel(str(runs[0]), view=stage)
        assert result["url"].endswith("#" + stage)
    with pytest.raises(ValueError):
        framework_panel.open_panel(str(runs[0]), view="resources")


def test_style_and_rollback_events_are_persistent(runs):
    root = runs[0]
    (root / "work").mkdir()
    event = run_events.record(root, "style_applied", "Session style changed", {"density": "spacious"})
    pending = run_events.pending(root)
    assert pending["events"] == [event]
    assert run_events.acknowledge(root, [event["id"]], pending["revision"])["events"] == []
    history = root / "history/iteration-01"
    history.mkdir(parents=True)
    write(history / "slide-intent.json", {"dominant_message": "Earlier direction"})
    selected = panel.select_version(root, "plan", "iteration-01")
    assert selected == {"plan": "iteration-01", "style": "previous", "design": "previous", "powerpoint": "previous"}
    assert (root / "work/stage-selections.json").is_file()


def test_http_selection_and_agent_rebinding_share_the_same_record(runs, monkeypatch, tmp_path):
    from webapp import server
    registry = tmp_path / "registry.json"
    write(registry, [{"id": root.name, "name": root.name, "path": str(root)} for root in runs])
    monkeypatch.setattr(server, "REGISTRY", registry)
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    worker = threading.Thread(target=httpd.serve_forever, daemon=True)
    worker.start()
    base = f"http://127.0.0.1:{httpd.server_port}"
    def request(path, body=None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(base + path, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as response:
            return json.load(response)
    try:
        listed = request("/api/runs")
        assert {item["path"] for item in listed} == {str(root) for root in runs}
        binding = request("/api/panel/new", {})
        selected = request("/api/panel/select", {"id": binding["id"], "run": str(runs[0]), "revision": binding["revision"]})
        assert panel_binding.get(binding["id"])["run"] == str(runs[0])
        with pytest.raises(urllib.error.HTTPError) as error:
            request("/api/panel/select", {"id": binding["id"], "run": str(runs[1]), "revision": selected["revision"]})
        assert error.value.code == 409
        panel_binding.ensure(binding["id"], runs[1])
        assert request("/api/panel/binding?id=" + binding["id"])["run"] == str(runs[1])
        write(runs[1] / "session.json", {"name": "two", "state": "hidden"})
        assert [item["path"] for item in request("/api/runs")] == [str(runs[0])]
    finally:
        httpd.shutdown()
        worker.join(timeout=2)
        httpd.server_close()
