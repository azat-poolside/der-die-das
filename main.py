"""FastAPI application for Der Die Das app."""

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import timedelta
import os

from database import get_db
from crud import create_session_and_get_words, process_session_results, authenticate_user, create_user, get_user_by_username
from schema import (
    SessionStartResponse, SessionEndRequest, SessionEndResponse,
    Token, UserCreate, UserResponse
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
    """Process session results and return summary."""
    words_practiced = await process_session_results(db, request.session_id, request.user_id, request.results)
    return SessionEndResponse(
        message="Session completed successfully",
        words_practiced=words_practiced
    )

# Serve frontend static files
frontend_dist = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dist")
if os.path.exists(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
