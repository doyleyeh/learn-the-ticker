from datetime import timedelta

from fastapi.testclient import TestClient

from backend.app.api import create_app
from backend.app.backup import make_backup, preview_backup, restore_backup
from backend.app.contracts import ResearchRequest, now
from backend.app.db import Database, Job
from tests.desktop.test_application import FakeRuntime, StaticIdentityResolver, TOKEN, payload


def test_bounded_research_only_projection_keeps_active_jobs_first():
    db = Database("sqlite://", testing=True)
    at = now()
    with db.session.begin() as session:
        for index in range(75):
            session.add(Job(id=f"research-{index:03}", status="completed", created_at=at + timedelta(seconds=index),
                request=ResearchRequest(query=f"Question {index}").model_dump(mode="json"), result={"raw_marker": "Do not project results"}, error="Do not project diagnostics"))
        session.add(Job(id="active", status="running", created_at=at - timedelta(days=1), request={"query": "Older active work"}))
        session.add(Job(id="term", status="running", request={"purpose": "term_explanation"}))
        session.add(Job(id="import", status="running", request={"purpose": "import_explanation"}))
    rows = db.research_jobs()
    assert len(rows) == 50 and rows[0]["id"] == "active" and rows[1]["id"] == "research-074"
    assert all(set(row) == {"schema_version", "id", "status", "request", "created_at"} for row in rows)
    assert not {"term", "import"} & {row["id"] for row in rows}
    assert all(row["created_at"].endswith("Z") for row in rows)


def test_auth_origin_and_reopen_recovery_never_start_inference(tmp_path):
    db = Database("sqlite://", testing=True)
    runtime = FakeRuntime(payload(), wait=True)
    with db.session.begin() as session:
        session.add(Job(id="stopped", status="running", request={"query": "Recover original question"}))
    app = create_app(db, TOKEN, tmp_path, adapters={"codex": runtime}, identity_resolver=StaticIdentityResolver())
    with TestClient(app) as client:
        assert client.get("/api/research/jobs").status_code == 401
        client.headers["Authorization"] = "Bearer " + TOKEN
        assert client.get("/api/research/jobs", headers={"Origin": "https://untrusted.example"}).status_code == 403
        response = client.get("/api/research/jobs")
        assert response.status_code == 200 and response.headers["cache-control"] == "no-store"
        assert response.json()[0]["status"] == "interrupted"
        assert client.get("/api/jobs/stopped").json()["status"] == "interrupted"
        assert not runtime.calls and not app.state.service.tasks
        assert not db.list("asset") and not db.list("bundle")


def test_active_job_can_be_rediscovered_and_cancelled_without_replay(tmp_path):
    db = Database("sqlite://", testing=True)
    db.put("settings", "settings", {"cloud_enabled": True})
    runtime = FakeRuntime(payload(), wait=True)
    app = create_app(db, TOKEN, tmp_path, adapters={"codex": runtime}, identity_resolver=StaticIdentityResolver())
    with TestClient(app, headers={"Authorization": "Bearer " + TOKEN}) as client:
        result = client.post("/api/research", json={"query": "Explain the synthetic company"}).json()
        # Read-only recovery can occur while the task is still resolving, queued or running.
        for _ in range(4):
            jobs = client.get("/api/research/jobs").json()
            assert len(jobs) == 1 and jobs[0]["id"] == result["id"]
            assert client.get("/api/jobs/" + result["id"]).json()["status"] in ("running", "queued")
        before = runtime.calls
        cancelled = client.post("/api/jobs/" + result["id"] + "/cancel").json()
        assert cancelled["status"] == "cancelled"
        assert client.get("/api/research/jobs").json()[0]["status"] == "cancelled"
        assert runtime.calls == before and runtime.calls <= 1
        assert not db.list("bundle")


def test_restored_job_history_retains_requests_without_replay():
    source, target = Database("sqlite://", testing=True), Database("sqlite://", testing=True)
    with source.session.begin() as session:
        for status in ("queued", "running", "cancelled", "failed", "interrupted"):
            session.add(Job(id=status, status=status, request={"query": f"Original {status}"}))
    archive = make_backup(source)
    restore_backup(target, archive, preview_backup(target, archive).fingerprint)
    rows = {row["id"]: row for row in target.research_jobs()}
    assert len(rows) == 5 and rows["running"]["status"] == rows["queued"]["status"] == "interrupted"
    assert rows["cancelled"]["status"] == "cancelled" and rows["failed"]["request"]["query"] == "Original failed"
    assert not target.list("asset") and not target.list("bundle")
