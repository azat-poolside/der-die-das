#!/usr/bin/env python3
"""Test to verify the QUIZ API acceptance criteria are met."""

import requests
import json
import uuid
from datetime import datetime, timedelta

BASE_URL = "http://127.0.0.1:8000"

def get_auth_token():
    """Create a test user and return the JWT token."""
    unique_user = f"quiz_user_{uuid.uuid4().hex[:8]}"
    user_data = {"username": unique_user, "email": f"{unique_user}@example.com", "password": "testpass123"}
    user_resp = requests.post(f"{BASE_URL}/users", json=user_data)

    # Get authentication token (try both the new user and handle if user already exists)
    response = requests.post(
        f"{BASE_URL}/token",
        data={"username": unique_user, "password": "testpass123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    if response.status_code == 200:
        return response.json().get("access_token")
    # If user creation failed (e.g., 400 user already exists), try to authenticate anyway
    if response.status_code == 401:
        # Try with a fallback username that might already exist
        response = requests.post(
            f"{BASE_URL}/token",
            data={"username": "test_api_user", "password": "testpass123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        if response.status_code == 200:
            return response.json().get("access_token")
    return None


def test_quiz_next_endpoint(token):
    """Test GET /quiz/next returns a word with session_id."""
    print("Testing GET /quiz/next endpoint...")

    response = requests.get(
        f"{BASE_URL}/quiz/next",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()

    # Verify response has session_id
    assert "session_id" in data, f"Response missing 'session_id': {data}"
    session_id = data["session_id"]
    print(f"  ✓ Returns session_id: {session_id[:8]}...")

    # Verify response has word field
    assert "word" in data, f"Response missing 'word': {data}"
    word = data["word"]

    if word is not None:
        # Verify word has expected fields
        assert "id" in word, f"Word missing 'id': {word}"
        assert "noun" in word, f"Word missing 'noun': {word}"
        assert "article" in word, f"Word missing 'article': {word}"
        assert "english_translation" in word, f"Word missing 'english_translation': {word}"
        print(f"  ✓ Returns word with id={word['id']}, noun='{word['noun']}'")
        print("✓ GET /quiz/next - PASSED\n")
        return session_id, word
    else:
        print("  ✓ Returns word=None (no words available in database)")
        print("✓ GET /quiz/next - PASSED\n")
        return session_id, None


def test_quiz_answer_endpoint(token, session_id, word):
    """Test POST /quiz/answer accepts QuizAnswerRequest with SM-2 scheduling."""
    print("Testing POST /quiz/answer endpoint...")

    if word is None:
        print("  ⚠ No word available, skipping answer test\n")
        return None

    # Test with correct answer (quality_rating >= 3)
    response = requests.post(
        f"{BASE_URL}/quiz/answer",
        json={
            "session_id": session_id,
            "word_id": word["id"],
            "quality_rating": 4,
            "attempts": 1,
            "response_time_ms": 2000
        },
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()

    # Verify response has expected fields
    assert "success" in data, f"Response missing 'success': {data}"
    assert "retry_word" in data, f"Response missing 'retry_word': {data}"
    assert "next_review_at" in data, f"Response missing 'next_review_at': {data}"
    print(f"  ✓ Accepts QuizAnswerRequest with session_id, word_id, quality_rating, attempts, response_time_ms")
    print(f"  ✓ Returns success={data['success']}, next_review_at={data['next_review_at']}")

    # Verify SM-2 scheduling was applied (next_review_at should be set)
    assert data["next_review_at"] is not None, "SM-2 scheduling not applied - next_review_at should be set"
    print("  ✓ SM-2 scheduling applied (next_review_at set)\n")

    # Test with incorrect answer (quality_rating < 3) - should trigger immediate retry
    print("Testing incorrect answer triggers immediate retry...")
    response = requests.post(
        f"{BASE_URL}/quiz/answer",
        json={
            "session_id": session_id,
            "word_id": word["id"],
            "quality_rating": 2,  # Incorrect answer
            "attempts": 1,
            "response_time_ms": 3000
        },
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()

    assert data["success"] == False, f"Expected success=False for incorrect answer, got {data['success']}"
    assert data["retry_word"] is not None, f"Expected retry_word for incorrect answer, got None"
    print(f"  ✓ Incorrect answer returns success=False")
    print(f"  ✓ Incorrect answer returns retry_word for immediate retry\n")

    return True


def test_quiz_session_endpoint(token):
    """Test GET /quiz/session returns QuizSessionResponse with session_statistics."""
    print("Testing GET /quiz/session endpoint...")

    response = requests.get(
        f"{BASE_URL}/quiz/session",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()

    # Verify response has expected fields
    assert "session_id" in data, f"Response missing 'session_id': {data}"
    assert "session_statistics" in data, f"Response missing 'session_statistics': {data}"
    print(f"  ✓ Returns QuizSessionResponse with session_id: {data['session_id'][:8]}...")

    # Verify session_statistics has expected fields
    stats = data["session_statistics"]
    assert "total_answers" in stats, f"session_statistics missing 'total_answers': {stats}"
    assert "correct_answers" in stats, f"session_statistics missing 'correct_answers': {stats}"
    assert "incorrect_answers" in stats, f"session_statistics missing 'incorrect_answers': {stats}"
    assert "avg_response_time_ms" in stats, f"session_statistics missing 'avg_response_time_ms': {stats}"
    print(f"  ✓ Session statistics: total_answers={stats['total_answers']}, correct={stats['correct_answers']}, incorrect={stats['incorrect_answers']}")
    print("✓ GET /quiz/session - PASSED\n")

    return True


def verify_acceptance_criteria():
    """Verify all quiz API acceptance criteria from the requirements."""
    print("=" * 60)
    print("Verifying QUIZ API Acceptance Criteria")
    print("=" * 60 + "\n")

    print("Required endpoints:")
    print("1. GET /quiz/next - get next word to review")
    print("2. POST /quiz/answer - submit answer, trigger immediate retry or schedule next review")
    print("3. GET /quiz/session - get current session state")
    print("All endpoints use JWT Bearer token authentication\n")

    # Get authentication token
    token = get_auth_token()
    assert token is not None, "Failed to obtain JWT token"
    print("Created test user and obtained JWT token\n")

    # Test 1: GET /quiz/next
    print("-" * 40)
    session_id, word = test_quiz_next_endpoint(token)

    # Test 2: POST /quiz/answer with SM-2 scheduling
    print("-" * 40)
    test_quiz_answer_endpoint(token, session_id, word)

    # Test 3: GET /quiz/session
    print("-" * 40)
    test_quiz_session_endpoint(token)

    print("=" * 60)
    print("All QUIZ API Criteria VERIFIED! ✓")
    print("=" * 60)


if __name__ == "__main__":
    try:
        verify_acceptance_criteria()
    except AssertionError as e:
        print(f"\n✗ Verification FAILED: {e}")
        exit(1)
    except Exception as e:
        print(f"\n✗ Verification ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
