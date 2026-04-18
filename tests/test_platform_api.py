from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_signup_login_and_listing_flow():
    signup = client.post("/api/auth/signup", json={"email": "a@example.com", "password": "pass1234"})
    assert signup.status_code == 200
    user_id = signup.json()["user_id"]

    add_source = client.post(
        "/api/vault/sources",
        json={"user_id": user_id, "category": "social", "source_name": "X", "metadata": {}},
    )
    assert add_source.status_code == 200

    listing = client.post(
        "/api/marketplace/listings",
        json={
            "user_id": user_id,
            "title": "Anonymized shopping trends",
            "anonymized_summary": "Aggregated weekly categories",
            "dataset_type": "purchases",
            "pricing_mode": "bids",
        },
    )
    assert listing.status_code == 200
    listing_id = listing.json()["listing_id"]

    offer = client.post(
        "/api/marketplace/offers",
        json={"user_id": user_id, "listing_id": listing_id, "buyer_id": "buyer_1", "amount": 20.0},
    )
    assert offer.status_code == 200


def test_privacy_redaction():
    res = client.post("/api/privacy/redact", json={"email": "a@example.com", "city": "Berlin"})
    assert res.status_code == 200
    body = res.json()
    assert body["email"] == "[REDACTED]"
    assert body["city"] == "Berlin"
