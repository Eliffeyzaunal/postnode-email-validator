from fastapi.testclient import TestClient

from app.main import app, get_service


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

