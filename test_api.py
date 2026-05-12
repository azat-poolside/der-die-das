#!/usr/bin/env python3
"""Test script to verify the API endpoints."""

import requests
import json

BASE_URL = "http://127.0.0.1:8000"


def get_auth_token(username: str, password: str) -> str:
    """Get JWT token by authenticating."""
    response = requests.post(
        f"{BASE_URL}/token",
        data={"username": username, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    if response.status_code == 200:
        return response.json().get("access_token")
    return None


def test_start_session():
    """Test POST /sessions/start endpoint."""
    print("Testing POST /sessions/start...")

    # First, create a user
    user_data = {"username": "test_api_user", "email": "api_test@example.com", "password": "testpass123"}
    user_resp = requests.post(f"{BASE_URL}/users", json=user_data)
    user_id = user_resp.json().get("id", 1)

    # Get authentication token
    token = get_auth_token("test_api_user", "testpass123")
    if not token:
        # Try to login with existing user if registration failed (user already exists)
        token = get_auth_token("test_api_user", "testpass123")

    if not token:
        print("⚠ Could not get auth token, skipping test")
        return None, None

    # Call sessions/start with JWT token
    response = requests.post(
        f"{BASE_URL}/sessions/start",
        headers={"Authorization": f"Bearer {token}"}
    )

    print(f"Status Code: {response.status_code}")
    data = response.json()
    print(f"Response: {json.dumps(data, indent=2, default=str)}")

    # Verify response
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert "session_id" in data, "Response should contain 'session_id'"
    assert "words" in data, "Response should contain 'words'"
    assert len(data["words"]) == 30, f"Expected 30 words, got {len(data['words'])}"

    print("✓ POST /sessions/start - PASSED\n")
    return data["session_id"], data["words"], token


def test_end_session(session_id, words, token):
    """Test POST /sessions/end endpoint."""
    print("Testing POST /sessions/end...")

    # Create some sample results
    results = []
    for i, word in enumerate(words[:5]):  # Test with 5 words
        results.append({
            "word_id": word["id"],
            "quality_rating": 4,  # Correct with hesitation (quality >= 3 is correct)
            "attempts": 1,
            "response_time_ms": 2000
        })

    payload = {
        "session_id": session_id,
        "results": results
    }

    response = requests.post(
        f"{BASE_URL}/sessions/end",
        json=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
    )

    print(f"Status Code: {response.status_code}")
    data = response.json()
    print(f"Response: {json.dumps(data, indent=2, default=str)}")

    # Verify response
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert "message" in data, "Response should contain 'message'"
    assert "words_practiced" in data, "Response should contain 'words_practiced'"
    assert data["words_practiced"] == 5, f"Expected 5 words practiced, got {data['words_practiced']}"

    print("✓ POST /sessions/end - PASSED\n")
    return True


def test_reviews_endpoint(token):
    """Test GET /reviews endpoint."""
    print("Testing GET /reviews...")

    response = requests.get(
        f"{BASE_URL}/reviews",
        headers={"Authorization": f"Bearer {token}"}
    )

    print(f"Status Code: {response.status_code}")
    data = response.json()
    print(f"Response: {json.dumps(data, indent=2, default=str)}")

    # Verify response
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert "words_due" in data, "Response should contain 'words_due'"
    assert "total_due" in data, "Response should contain 'total_due'"

    print("✓ GET /reviews - PASSED\n")
    return True


if __name__ == "__main__":
    print("=" * 50)
    print("Testing Der Die Das API Endpoints")
    print("=" * 50 + "\n")

    try:
        session_id, words, token = test_start_session()
        if session_id and token:
            test_end_session(session_id, words, token)
            test_reviews_endpoint(token)

        print("=" * 50)
        print("All API tests PASSED! ✓")
        print("=" * 50)
    except AssertionError as e:
        print(f"\n✗ Test FAILED: {e}")
        exit(1)
    except Exception as e:
        print(f"\n✗ Test ERROR: {e}")
        exit(1)
