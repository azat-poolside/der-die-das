"""FastAPI application for Der Die Das app."""

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime
from typing import Optional
import os
import uuid

from database import get_db
from crud import create_session_and_get_words, process_session_results, authenticate_user, create_user, get_user_by_username, generate_jwt_token, decode_jwt_token, get_user_by_id, update_progress_sm2, get_new_words
from models import User, Word, Progress, SessionResult
from schema import (
    SessionStartResponse, SessionEndRequest, SessionEndResponse,
    Token, UserCreate, UserResponse, ReviewResponse, WordInDBWithProgress,
    QuizNextResponse, QuizAnswerRequest, QuizAnswerResponse, QuizSessionResponse, QuizSessionStatistics
)

app = FastAPI()

# OAuth2 scheme for password flow
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# Authentication dependency to get current user
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Extract and validate JWT token, return current User object.

    Args:
        token: JWT token from Authorization header
        db: Database session

    Returns:
        User object if token is valid

    Raises:
        HTTPException: 401 if token is invalid/missing
    """
    # Decode and validate the token
    payload = decode_jwt_token(token)

    # Extract user_id from token payload
    user_id: Optional[int] = payload.get("user_id")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing user_id",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Fetch user from database
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


# Authentication routes
@app.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """Authenticate user and return JWT access token."""
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # Generate proper JWT token with user_id and username in payload
    access_token = generate_jwt_token(user.id, user.username)
    return Token(access_token=access_token, token_type="bearer")


@app.post("/users", response_model=UserResponse)
async def register_user(user_create: UserCreate, db: AsyncSession = Depends(get_db)):
    """Register a new user."""
    # Check if username already exists
    existing_user = await get_user_by_username(db, user_create.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )

    user = await create_user(db, user_create)
    return UserResponse.model_validate(user)


@app.post("/sessions/start", response_model=SessionStartResponse)
async def start_session(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Start a new session and return session_id with 30 words for a specific user."""
    session_id, words = await create_session_and_get_words(db, current_user.id)
    return SessionStartResponse(session_id=session_id, words=words)


@app.post("/sessions/end", response_model=SessionEndResponse)
async def end_session(
    request: SessionEndRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Process session results and return summary with retry words."""
    words_practiced, retry_words, retry_words_details = await process_session_results(db, request.session_id, current_user.id, request.results)
    return SessionEndResponse(
        message="Session completed successfully",
        words_practiced=words_practiced,
        retry_words=retry_words,
        retry_words_details=retry_words_details
    )


@app.get("/reviews", response_model=ReviewResponse)
async def get_reviews(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get words due for review for a specific user."""
    now = datetime.utcnow()

    # Get scheduled words with their progress data
    result = await db.execute(
        select(Word, Progress)
        .join(Progress, Word.id == Progress.word_id)
        .where(Progress.user_id == current_user.id)
        .where(Progress.next_practice <= now)
        .order_by(Progress.interval.asc())
        .limit(30)
    )

    words_with_progress = []
    next_review_at = None

    for word, progress in result.all():
        word_dict = {
            "id": word.id,
            "noun": word.noun,
            "article": word.article,
            "english_translation": word.english_translation,
            "progress": {
                "id": progress.id,
                "user_id": progress.user_id,
                "word_id": progress.word_id,
                "ease_factor": progress.ease_factor,
                "interval": progress.interval,
                "repetitions": progress.repetitions,
                "next_practice": progress.next_practice,
                "next_review": progress.next_review,
                "created_at": progress.created_at
            }
        }
        words_with_progress.append(word_dict)
        if next_review_at is None:
            next_review_at = progress.next_practice

    return ReviewResponse(
        words_due=[WordInDBWithProgress(**w) for w in words_with_progress],
        total_due=len(words_with_progress),
        next_review_at=next_review_at
    )


# ==================== Quiz Endpoints ====================

# In-memory session state storage (keyed by session_id)
# Structure: {session_id: {user_id, words_practiced_count, current_position, pending_retry_words, session_statistics}}
_quiz_sessions: dict = {}
# Mapping from user_id to session_id for quick lookup
_user_sessions: dict = {}


@app.get("/quiz/next", response_model=QuizNextResponse)
async def get_quiz_next(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get next word to review.

    Returns a single word that is due for review (next_practice <= now),
    ordered by interval (shortest first) for spaced repetition.
    If no words due, returns a new random word without progress.
    Also returns session_id for tracking quiz session state.
    """
    now = datetime.utcnow()

    # Check if a session already exists for the user before creating a new one
    session_id = _user_sessions.get(current_user.id)
    if not session_id or session_id not in _quiz_sessions:
        # Generate a new session_id
        session_id = str(uuid.uuid4())
        _quiz_sessions[session_id] = {
            "user_id": current_user.id,
            "words_practiced_count": 0,
            "current_position": 0,
            "pending_retry_words": [],
            "session_statistics": QuizSessionStatistics(session_start_time=datetime.utcnow())
        }
        _user_sessions[current_user.id] = session_id

    # Get the next scheduled word with its progress data
    result = await db.execute(
        select(Word, Progress)
        .join(Progress, Word.id == Progress.word_id)
        .where(Progress.user_id == current_user.id)
        .where(Progress.next_practice <= now)
        .order_by(Progress.interval.asc())
        .limit(1)
    )

    word_with_progress = result.first()

    if word_with_progress:
        word, progress = word_with_progress
        word_dict = {
            "id": word.id,
            "noun": word.noun,
            "article": word.article,
            "english_translation": word.english_translation,
            "progress": {
                "id": progress.id,
                "user_id": progress.user_id,
                "word_id": progress.word_id,
                "ease_factor": progress.ease_factor,
                "interval": progress.interval,
                "repetitions": progress.repetitions,
                "next_practice": progress.next_practice,
                "next_review": progress.next_review,
                "created_at": progress.created_at
            }
        }
        return QuizNextResponse(session_id=session_id, word=WordInDBWithProgress(**word_dict))

    # No words due - get a random new word without progress
    new_word = await db.execute(
        select(Word)
        .where(~Word.id.in_(
            select(Progress.word_id).where(Progress.user_id == current_user.id)
        ))
        .order_by(func.random())
        .limit(1)
    )
    word = new_word.scalar_one_or_none()

    if word:
        return QuizNextResponse(session_id=session_id, word=WordInDBWithProgress(
            id=word.id,
            noun=word.noun,
            article=word.article,
            english_translation=word.english_translation,
            progress=None
        ))

    # No words available at all
    return QuizNextResponse(session_id=session_id, word=None)


@app.post("/quiz/answer", response_model=QuizAnswerResponse)
async def quiz_answer(
    request: QuizAnswerRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Submit answer and trigger immediate retry or schedule next review.

    - Calls update_progress_sm2() to update scheduling
    - If quality_rating < 3 (incorrect): returns retry_word with same word for immediate retry
    - If quality_rating >= 3 (correct): returns success, word is scheduled normally
    - Updates quiz session state
    """
    # Validate that the session_id is valid
    # Check if a session with this session_id exists in database
    session_check = await db.execute(
        select(SessionResult).where(SessionResult.session_id == request.session_id)
    )
    existing_session_result = session_check.scalar_one_or_none()

    # Validate session_id is a valid UUID format
    try:
        uuid.UUID(request.session_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session_id format. Must be a valid UUID."
        )

    # Session validation:
    # 1. If session exists in SessionResult table -> it's a valid session
    # 2. If not, check if user has a quiz session with this session_id -> belongs to user
    # 3. Otherwise, create a new session entry for this user (first answer creates the session)
    session_exists_in_db = existing_session_result is not None
    user_owns_session = (
        request.session_id in _quiz_sessions and
        _quiz_sessions[request.session_id].get("user_id") == current_user.id
    )

    # Initialize session if needed (only create QuizSessionStatistics once)
    if not session_exists_in_db and not user_owns_session:
        # Create a new session entry for this user
        _quiz_sessions[request.session_id] = {
            "user_id": current_user.id,
            "words_practiced_count": 0,
            "current_position": 0,
            "pending_retry_words": [],
            "session_statistics": QuizSessionStatistics(session_start_time=datetime.utcnow())
        }
        _user_sessions[current_user.id] = request.session_id

    # Get existing session entry (don't overwrite)
    user_session = _quiz_sessions[request.session_id]

    # Update progress using SM-2 algorithm
    progress = await update_progress_sm2(
        db=db,
        user_id=current_user.id,
        word_id=request.word_id,
        quality_rating=request.quality_rating
    )

    # Get the word for potential retry response
    word_result = await db.execute(select(Word).where(Word.id == request.word_id))
    word = word_result.scalar_one_or_none()

    # Update statistics (QuizSessionStatistics is a Pydantic model, update directly)
    stats = user_session["session_statistics"]
    stats.total_answers += 1
    stats.avg_response_time_ms = (
        (stats.avg_response_time_ms * (stats.total_answers - 1) + request.response_time_ms) / stats.total_answers
        if stats.total_answers > 0 else 0.0
    )
    if request.quality_rating < 3:
        stats.incorrect_answers += 1
    else:
        stats.correct_answers += 1

    user_session["words_practiced_count"] += 1
    user_session["current_position"] += 1

    if request.quality_rating < 3:
        # Incorrect answer - add to pending retry and return retry word
        user_session["pending_retry_words"].append(request.word_id)

        if word:
            word_dict = {
                "id": word.id,
                "noun": word.noun,
                "article": word.article,
                "english_translation": word.english_translation,
                "progress": {
                    "id": progress.id,
                    "user_id": progress.user_id,
                    "word_id": progress.word_id,
                    "ease_factor": progress.ease_factor,
                    "interval": progress.interval,
                    "repetitions": progress.repetitions,
                    "next_practice": progress.next_practice,
                    "next_review": progress.next_review,
                    "created_at": progress.created_at
                }
            }
            return QuizAnswerResponse(
                success=False,
                retry_word=WordInDBWithProgress(**word_dict),
                next_review_at=progress.next_practice
            )
        else:
            # Word not found, return success anyway
            return QuizAnswerResponse(
                success=False,
                retry_word=None,
                next_review_at=progress.next_practice
            )

    # Correct answer - return success
    return QuizAnswerResponse(
        success=True,
        retry_word=None,
        next_review_at=progress.next_practice
    )


@app.get("/quiz/session", response_model=QuizSessionResponse)
async def get_quiz_session(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current session state.

    Returns current quiz session state including:
    - Words practiced count
    - Current position
    - Any pending retry words
    - Session statistics
    """
    # Find the user's most recent quiz session using _user_sessions mapping
    session_id = _user_sessions.get(current_user.id)

    if session_id and session_id in _quiz_sessions:
        user_session = _quiz_sessions[session_id]
    else:
        # No session exists, create a default one
        session_id = str(uuid.uuid4())
        user_session = {
            "user_id": current_user.id,
            "words_practiced_count": 0,
            "current_position": 0,
            "pending_retry_words": [],
            "session_statistics": QuizSessionStatistics(session_start_time=datetime.utcnow())
        }
        _quiz_sessions[session_id] = user_session
        _user_sessions[current_user.id] = session_id

    return QuizSessionResponse(
        session_id=session_id,
        words_practiced_count=user_session["words_practiced_count"],
        current_position=user_session["current_position"],
        pending_retry_words=user_session["pending_retry_words"],
        session_statistics=user_session["session_statistics"]
    )

# Serve frontend static files
frontend_dist = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dist")
if os.path.exists(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
