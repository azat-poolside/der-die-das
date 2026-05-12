"""CRUD operations for Der Die Das app."""

import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
import jwt

from passlib.context import CryptContext

from models import User, Word, Progress, SessionResult
from schema import WordInDB, WordResult, UserCreate, UserInDB, ProgressInDB

# Password hashing context (singleton)
# Using sha256_crypt as fallback since bcrypt 5.0 has compatibility issues with passlib
pwd_context = CryptContext(schemes=["sha256_crypt"], deprecated="auto")

# JWT Configuration
SECRET_KEY = os.environ.get("SECRET_KEY", "your-secret-key-change-in-production")  # Should be from environment variable
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


def generate_jwt_token(user_id: int, username: str) -> str:
    """Generate a JWT token with user_id and username in payload.

    Args:
        user_id: The user's database ID
        username: The user's username

    Returns:
        Encoded JWT token string
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {
        "sub": username,  # Subject (standard JWT claim)
        "user_id": user_id,
        "username": username,
        "exp": expire,
        "iat": datetime.now(timezone.utc)  # Issued at
    }
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_jwt_token(token: str) -> dict:
    """Decode and validate a JWT token.

    Args:
        token: The JWT token string to decode

    Returns:
        Decoded payload dictionary

    Raises:
        HTTPException: If token is invalid or expired
    """
    from fastapi import HTTPException, status
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ==================== User CRUD Operations ====================

async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    """Get a user by ID."""
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    """Get a user by username."""
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """Get a user by email."""
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, user_create: UserCreate) -> User:
    """Create a new user."""
    hashed_password = pwd_context.hash(user_create.password)

    db_user = User(
        username=user_create.username,
        email=user_create.email,
        hashed_password=hashed_password,
        is_active=True,
        is_superuser=False
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user


async def authenticate_user(db: AsyncSession, username: str, password: str) -> Optional[User]:
    """Authenticate a user by username and password."""
    user = await get_user_by_username(db, username)
    if not user:
        return None

    if not pwd_context.verify(password, user.hashed_password):
        return None

    # Update last login time
    user.last_login_at = datetime.utcnow()
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user


async def update_user_last_login(db: AsyncSession, user_id: int) -> Optional[User]:
    """Update user's last login timestamp."""
    user = await get_user_by_id(db, user_id)
    if user:
        user.last_login_at = datetime.utcnow()
        db.add(user)
        await db.commit()
        await db.refresh(user)
    return user


# ==================== Progress CRUD Operations ====================

async def get_or_create_progress(db: AsyncSession, user_id: int, word_id: int) -> Progress:
    """Get existing progress record or create a new one for user-word pair."""
    result = await db.execute(
        select(Progress).where(Progress.user_id == user_id, Progress.word_id == word_id)
    )
    progress = result.scalar_one_or_none()

    if not progress:
        progress = Progress(user_id=user_id, word_id=word_id)
        db.add(progress)
        await db.commit()
        await db.refresh(progress)

    return progress


async def get_user_progress(db: AsyncSession, user_id: int) -> List[ProgressInDB]:
    """Get all progress records for a user."""
    result = await db.execute(select(Progress).where(Progress.user_id == user_id))
    return [ProgressInDB.model_validate(p) for p in result.scalars().all()]


async def get_progress_for_word(db: AsyncSession, user_id: int, word_id: int) -> Optional[Progress]:
    """Get progress record for a specific user-word pair."""
    result = await db.execute(
        select(Progress).where(Progress.user_id == user_id, Progress.word_id == word_id)
    )
    return result.scalar_one_or_none()


# ==================== Word CRUD Operations ====================

async def get_scheduled_words(db: AsyncSession, now: datetime, user_id: int) -> List[Word]:
    """Get words that are scheduled for practice for a specific user."""
    result = await db.execute(
        select(Word)
        .join(Progress, Word.id == Progress.word_id)
        .where(Progress.user_id == user_id)
        .where(Progress.next_practice <= now)
        .order_by(Progress.interval.asc())
        .limit(30)
    )
    return result.scalars().all()


async def get_new_words(db: AsyncSession, user_id: int, exclude_word_ids: List[int] = None) -> List[Word]:
    """Get random new words that the user hasn't practiced yet (no Progress record)."""
    # Get word IDs that user already has progress for
    progress_result = await db.execute(
        select(Progress.word_id).where(Progress.user_id == user_id)
    )
    known_word_ids = [row[0] for row in progress_result.fetchall()]

    query = select(Word)

    # Combine already known words with excluded IDs
    all_excluded = list(set(known_word_ids + (exclude_word_ids or [])))

    if all_excluded:
        query = query.where(Word.id.not_in(all_excluded))

    result = await db.execute(query.order_by(func.random()).limit(30))
    return result.scalars().all()


async def get_session_words(db: AsyncSession, user_id: int, session_id: str = None) -> List[WordInDB]:
    """
    Get 30 words for a session for a specific user.
    - First, get scheduled words (next_practice <= now) ordered by interval
    - If insufficient, fill with random new words (no Progress record)
    """
    now = datetime.utcnow()

    # Get scheduled words first (user-specific)
    scheduled_words = await get_scheduled_words(db, now, user_id)

    # If we don't have enough words, get new ones
    if len(scheduled_words) < 30:
        existing_ids = [w.id for w in scheduled_words]
        needed = 30 - len(scheduled_words)

        new_words = await db.execute(
            select(Word)
            .where(Word.id.not_in(existing_ids))
            .where(~Word.id.in_(
                select(Progress.word_id).where(Progress.user_id == user_id)
            ))
            .order_by(func.random())
            .limit(needed)
        )
        new_words = new_words.scalars().all()
        all_words = scheduled_words + list(new_words)
    else:
        all_words = scheduled_words[:30]

    return [WordInDB.model_validate(word) for word in all_words]


async def create_session_result(
    db: AsyncSession,
    word_id: int,
    session_id: str,
    quality_rating: int,
    attempts: int,
    response_time_ms: int
) -> SessionResult:
    """Create a session result record."""
    db_result = SessionResult(
        word_id=word_id,
        session_id=session_id,
        quality_rating=quality_rating,
        attempts=attempts,
        response_time_ms=response_time_ms
    )
    db.add(db_result)
    await db.commit()
    await db.refresh(db_result)
    return db_result


async def update_progress_sm2(db: AsyncSession, user_id: int, word_id: int, quality_rating: int) -> Progress:
    """
    Update user's progress for a word using SM-2 algorithm.

    SM-2 Algorithm:
    - If quality_rating >= 3 (correct): increment repetitions, calculate new interval based on ease_factor
    - If quality_rating < 3 (incorrect): reset repetitions to 0, set interval to 1
    - Update ease_factor based on quality_rating

    Quality ratings (0-5):
    - 5: perfect response
    - 4: correct after hesitation
    - 3: correct with difficulty
    - 2-0: incorrect responses
    """
    progress = await get_or_create_progress(db, user_id, word_id)
    now = datetime.utcnow()

    # Update ease factor based on quality rating
    # Formula: new_ef = ef + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    new_ef = progress.ease_factor + (0.1 - (5 - quality_rating) * (0.08 + (5 - quality_rating) * 0.02))
    progress.ease_factor = max(1.3, new_ef)  # Ensure ease factor doesn't go below 1.3

    if quality_rating >= 3:
        # Correct response (quality 3-5) - increment repetitions and calculate interval
        progress.repetitions += 1

        if progress.repetitions == 1:
            progress.interval = 1
        elif progress.repetitions == 2:
            progress.interval = 6
        else:
            # Subsequent repetitions: multiply previous interval by ease factor
            progress.interval = int(progress.interval * progress.ease_factor)
    else:
        # Incorrect response (quality 0-2) - reset repetitions and interval
        progress.repetitions = 0
        progress.interval = 1  # SM-2 spec: incorrect answers should be scheduled for 1 day later

    # Set next_practice and next_review based on calculated interval
    progress.next_practice = now + timedelta(days=progress.interval)
    progress.next_review = progress.next_practice  # Alias for spaced repetition terminology

    db.add(progress)
    await db.commit()
    await db.refresh(progress)
    return progress


async def create_session_and_get_words(db: AsyncSession, user_id: int) -> tuple[str, List[WordInDB]]:
    """Create a new session and return session_id with 30 words for a specific user."""
    session_id = str(uuid.uuid4())
    words = await get_session_words(db, user_id)
    return session_id, words


async def process_session_results(
    db: AsyncSession,
    session_id: str,
    user_id: int,
    results: List[WordResult]
) -> tuple[int, List[int], Optional[List[WordInDB]]]:
    """
    Process session results - create records and update user's word progress (SM-2).
    Returns a tuple of (words_practiced, retry_words, retry_words_details) where retry_words contains
    word_ids that should be immediately retried (quality_rating < 3), and retry_words_details
    contains the full WordInDB objects for those words.
    """
    retry_words: List[int] = []
    retry_words_details: List[WordInDB] = []

    for result in results:
        # Create session result record
        await create_session_result(
            db=db,
            word_id=result.word_id,
            session_id=session_id,
            quality_rating=result.quality_rating,
            attempts=result.attempts,
            response_time_ms=result.response_time_ms
        )

        # Track words that need immediate retry (quality_rating < 3 means incorrect)
        if result.quality_rating < 3:
            retry_words.append(result.word_id)

        # Update user's progress SM-2 values for this word
        await update_progress_sm2(
            db=db,
            user_id=user_id,
            word_id=result.word_id,
            quality_rating=result.quality_rating
        )

    # Fetch full word details for retry_words
    if retry_words:
        words_result = await db.execute(
            select(Word).where(Word.id.in_(retry_words))
        )
        retry_words_details = [WordInDB.model_validate(word) for word in words_result.scalars().all()]

    return len(results), retry_words, retry_words_details if retry_words_details else None
