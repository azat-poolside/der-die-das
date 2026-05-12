"""FastAPI application for Der Die Das app."""

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from typing import Optional
import os

from database import get_db
from crud import create_session_and_get_words, process_session_results, authenticate_user, create_user, get_user_by_username, generate_jwt_token, decode_jwt_token, get_user_by_id
from models import User, Word, Progress
from schema import (
    SessionStartResponse, SessionEndRequest, SessionEndResponse,
    Token, UserCreate, UserResponse, ReviewResponse, WordInDBWithProgress
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

# Serve frontend static files
frontend_dist = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dist")
if os.path.exists(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
