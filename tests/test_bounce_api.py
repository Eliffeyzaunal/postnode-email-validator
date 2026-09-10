from fastapi.testclient import TestClient

from app.main import app, get_event_classifier


def test_event_classification_endpoints_do_not_expose_email():
    get_event_classifier.cache_clear()
    client = TestClient(app)
    response = client.post("/api/v1/events/classify", json={
        "event": {
            "event_type": "bounce",
            "recipient": "person@example.com",
            "enhanced_status": "4.2.2",
            "diagnostic_code": "452 person@example.com mailbox full",
        }
    })
    assert response.status_code == 200
    assert response.json()["category"] == "mailbox_full"
    assert "person@example.com" not in response.text

    batch = client.post("/api/v1/events/classify/batch", json={
        "events": [{"event_type": "complaint"}, {"diagnostic_code": "new code"}]
    })
    assert batch.status_code == 200
    assert batch.json()["unknown_rate"] == 0.5

    rules = client.get("/api/v1/events/rules")
    assert rules.status_code == 200
    assert len(rules.json()) == 22
    assert all(rule["sources"] for rule in rules.json())


def test_event_batch_limit_is_validated():
    response = TestClient(app).post("/api/v1/events/classify/batch", json={"events": []})
    assert response.status_code == 422


def test_single_endpoint_rejects_multi_recipient_notification_and_batch_expands_it():
    event = {
        "notificationType": "Bounce",
        "mail": {"messageId": "ses-api-1"},
        "bounce": {
            "bounceType": "Permanent",
            "bounceSubType": "General",
            "bouncedRecipients": [
                {"emailAddress": "one@example.com", "status": "4.2.2"},
                {"emailAddress": "two@example.net", "status": "5.1.1"},
            ],
        },
    }
    client = TestClient(app)
    single = client.post("/api/v1/events/classify", json={"event": event})
    assert single.status_code == 422
    assert "toplu API" in single.json()["detail"]

    batch = client.post("/api/v1/events/classify/batch", json={"events": [event]})
    assert batch.status_code == 200
    assert batch.json()["total"] == 2
    assert "one@example.com" not in batch.text
    assert "two@example.net" not in batch.text
