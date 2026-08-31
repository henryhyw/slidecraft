from framework import run_activity, sessions
from framework.storage import read, write


def test_activity_records_user_facing_step(tmp_path):
    root = sessions.create("Activity", location=str(tmp_path / "run"), workspace=tmp_path / "workspace", registry_file=tmp_path / "runs.json")
    result = run_activity.record(root, "semantic_mapping", "running", "Reading the approved design")
    assert result["current"]["stage"] == "design"
    assert result["current"]["message"] == "Reading the approved design"
    assert "meaningful regions" in result["current"]["purpose"]
    assert result["revision"]


def test_activity_rejects_unknown_state(tmp_path):
    root = sessions.create("Activity", location=str(tmp_path / "run"), workspace=tmp_path / "workspace", registry_file=tmp_path / "runs.json")
    try:
        run_activity.record(root, "semantic_mapping", "passed")
    except ValueError as error:
        assert "Unknown activity status" in str(error)
    else:
        raise AssertionError("A workflow activity must not become a verdict")


def test_saved_activity_uses_current_labels_without_changing_history(tmp_path):
    root = sessions.create("Activity", location=str(tmp_path / "run"), workspace=tmp_path / "workspace", registry_file=tmp_path / "runs.json")
    entry = {"step": "understand_request", "label": "Old label", "purpose": "Old description",
             "message": "Keep this authored message", "status": "running", "stage": "plan"}
    target = run_activity.path(root)
    saved = {"current": entry, "entries": [entry]}
    write(target, saved)
    result = run_activity.snapshot(root)
    for item in [result["current"], *result["entries"]]:
        assert item["label"] == run_activity.STEPS["understand_request"][1]
        assert item["purpose"] == run_activity.STEPS["understand_request"][2]
        assert item["message"] == entry["message"]
    assert read(target) == saved
