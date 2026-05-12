"""FastAPI application for Der Die Das app."""

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
import os

from database import get_db
from crud import create_session_and_get_words, process_session_results, authenticate_user, create_user, get_user_by_username, get_scheduled_words, get_user_progress
from models import Word, Progress
from schema import (
    SessionStartResponse, SessionEndRequest, SessionEndResponse,
    Token, UserCreate, UserResponse, ReviewResponse, WordInDBWithProgress
)

app = FastAPI()

# OAuth2 scheme for password flow
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# Authentication routes
@app.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """Authenticate user and return access token."""
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # For now, return a simple token (in production, use JWT)
    return Token(access_token=user.username, token_type="bearer")


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
    user_id: int,  # In production, extract from token
    db: AsyncSession = Depends(get_db)
):
    """Start a new session and return session_id with 30 words for a specific user."""
    session_id, words = await create_session_and_get_words(db, user_id)
    return SessionStartResponse(session_id=session_id, words=words)


@app.post("/sessions/end", response_model=SessionEndResponse)
async def end_session(request: SessionEndRequest, db: AsyncSession = Depends(get_db)):
    """Process session results and return summary with retry words."""
    words_practiced, retry_words, retry_words_details = await process_session_results(db, request.session_id, request.user_id, request.results)
    return SessionEndResponse(
        message="Session completed successfully",
        words_practiced=words_practiced,
        retry_words=retry_words,
        retry_words_details=retry_words_details
    )


@app.get("/reviews", response_model=ReviewResponse)
async def get_reviews(user_id: int, db: AsyncSession = Depends(get_db)):
    """Get words due for review for a specific user."""
    now = datetime.utcnow()

    # Get scheduled words with their progress data
    result = await db.execute(
        select(Word, Progress)
        .join(Progress, Word.id == Progress.word_id)
        .where(Progress.user_id == user_id)
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
