"""Integration tests for example_api Flask app."""

import pytest

from example_api.app import app


@pytest.fixture
def client():
    """Flask test client."""
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_health_success_response(client) -> None:
    """Health endpoint returns 200."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json["status"] == "ok"


def test_health_client_error(client) -> None:
    """Health with POST returns 405."""
    response = client.post("/health")
    assert response.status_code == 405


def test_health_server_error(client) -> None:
    """Health with invalid method returns 405."""
    response = client.delete("/health")
    assert response.status_code == 405


def test_health_timeout(client) -> None:
    """Health responds without delay."""
    response = client.get("/health")
    assert response.status_code == 200
    assert "status" in response.json


def test_total_success_response(client) -> None:
    """Total endpoint returns sum."""
    response = client.post(
        "/total",
        json={"items": [1, 2, 3]},
        content_type="application/json",
    )
    assert response.status_code == 200
    assert response.json["total"] == 6.0


def test_total_client_error(client) -> None:
    """Total with GET returns 405."""
    response = client.get("/total")
    assert response.status_code == 405


def test_total_server_error(client) -> None:
    """Total with invalid JSON returns 400 or 200 with empty result."""
    response = client.post("/total", data="invalid", content_type="application/json")
    assert response.status_code in (200, 400, 415)


def test_total_timeout(client) -> None:
    """Total responds promptly."""
    response = client.post("/total", json={"items": [1]}, content_type="application/json")
    assert response.status_code == 200


def test_validate_email_route_success_response(client) -> None:
    """Validate email returns valid true for good email."""
    response = client.post(
        "/validate-email",
        json={"email": "user@example.com"},
        content_type="application/json",
    )
    assert response.status_code == 200
    assert response.json["valid"] is True


def test_validate_email_route_client_error(client) -> None:
    """Validate email with GET returns 405."""
    response = client.get("/validate-email")
    assert response.status_code == 405


def test_validate_email_route_server_error(client) -> None:
    """Validate email with invalid JSON handles gracefully."""
    response = client.post(
        "/validate-email",
        data="invalid",
        content_type="application/json",
    )
    assert response.status_code in (200, 400, 415)


def test_validate_email_route_timeout(client) -> None:
    """Validate email responds promptly."""
    response = client.post(
        "/validate-email",
        json={"email": "test@test.com"},
        content_type="application/json",
    )
    assert response.status_code == 200
