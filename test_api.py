#!/usr/bin/env python3
"""Test script to verify the API endpoints."""

import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def test_start_session():
    """Test POST /sessions/start endpoint."""
    print("Testing POST /sessions/start...")
    
    # First, create a user
    user_data = {"username": "test_api_user", "email": "api_test@example.com", "password": "testpass123"}
    user_resp = requests.post(f"{BASE_URL}/users", json=user_data)
    user_id = user_resp.json().get("id", 1)
    
    response = requests.post(f"{BASE_URL}/sessions/start?user_id={user_id}")
    
    print(f"Status Code: {response.status_code}")
    data = response.json()
    print(f"Response: {json.dumps(data, indent=2, default=str)}")
    
    # Verify response
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert "session_id" in data, "Response should contain 'session_id'"
    assert "words" in data, "Response should contain 'words'"
    assert len(data["words"]) == 30, f"Expected 30 words, got {len(data['words'])}"
    
    print("✓ POST /sessions/start - PASSED\n")
    return data["session_id"], data["words"]


def test_end_session(session_id, words, user_id):
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
        "user_id": user_id,
        "results": results
    }
    
    response = requests.post(
        f"{BASE_URL}/sessions/end",
        json=payload,
        headers={"Content-Type": "application/json"}
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


if __name__ == "__main__":
    print("=" * 50)
    print("Testing Der Die Das API Endpoints")
    print("=" * 50 + "\n")
    
    try:
        session_id, words = test_start_session()
        user_id = 1  # Will be created by test_start_session
        try:
            user_data = {"username": "test_api_user", "email": "api_test@example.com", "password": "testpass123"}
            user_resp = requests.post(f"{BASE_URL}/users", json=user_data)
            user_id = user_resp.json().get("id", 1)
        except:
            pass  # Use default user_id = 1
        
        test_end_session(session_id, words, user_id)
        
        print("=" * 50)
        print("All API tests PASSED! ✓")
        print("=" * 50)
    except AssertionError as e:
        print(f"\n✗ Test FAILED: {e}")
        exit(1)
    except Exception as e:
        print(f"\n✗ Test ERROR: {e}")
        exit(1)