from fastapi.testclient import TestClient

from app.blocklist.scheduler import BlocklistScheduler
from app.main import (
    app,
    get_blocklist_scheduler,
    get_blocklist_service,
    get_service,
)


def test_health():
    assert TestClient(app).get("/health").status_code == 200


def test_validate_endpoint(service):
    app.dependency_overrides = {}
    original = get_service
    get_service.cache_clear()
    # Route fonksiyonu doğrudan get_service kullandığı için cache'e test nesnesini yerleştiriyoruz.
    import app.main as main_module
    main_module.get_service = lambda: service
    try:
        response = TestClient(app).post("/api/v1/validate", json={"email": "user@gmial.com"})
        assert response.status_code == 200
        body = response.json()
        assert body["results"][0]["status"] == "supheli"
        assert body["results"][0]["masked_email"] == "u***r@gmial.com"
        assert "user@gmial.com" not in response.text
    finally:
        main_module.get_service = original
        get_service.cache_clear()


def test_file_upload(service):
    import app.main as main_module
    original = main_module.get_service
    main_module.get_service = lambda: service
    try:
        response = TestClient(app).post(
            "/api/v1/validate/file",
            files={"file": ("emails.csv", b"email\na@gmail.com\nb@example.com\n", "text/csv")},
        )
        assert response.status_code == 200
        assert response.json()["summary"]["total"] == 2
    finally:
        main_module.get_service = original


def test_blocklist_api_and_history(blocklist_service):
    import app.main as main_module

    original = main_module.get_blocklist_service
    original_scheduler = main_module.get_blocklist_scheduler
    main_module.get_blocklist_service = lambda: blocklist_service
    main_module.get_blocklist_scheduler = lambda: BlocklistScheduler(blocklist_service)
    try:
        client = TestClient(app)
        response = client.post("/api/v1/blocklists/check")
        assert response.status_code == 200
        body = response.json()
        assert body["summary"]["total"] == 10

        history = client.get(f"/api/v1/blocklists/runs/{body['run_id']}")
        assert history.status_code == 200
        assert history.json()["total_checks"] == 10

        notifications = client.get(
            f"/api/v1/blocklists/runs/{body['run_id']}/notifications"
        )
        assert notifications.status_code == 200
        assert len(notifications.json()) == 5

        status = client.get("/api/v1/blocklists/monitor/status")
        assert status.status_code == 200
        assert status.json()["status"] == "not_started"

        BlocklistScheduler(blocklist_service).run_cycle()
        history_report = client.get("/api/v1/blocklists/reports/history?days=30")
        assert history_report.status_code == 200
        assert history_report.json()["total_runs"] == 2
    finally:
        main_module.get_blocklist_service = original
        main_module.get_blocklist_scheduler = original_scheduler
        get_blocklist_service.cache_clear()
        get_blocklist_scheduler.cache_clear()
