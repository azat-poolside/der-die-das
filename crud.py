"""CRUD operations for Der Die Das app."""

import uuid
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from models import Word, SessionResult
from schema import WordInDB, WordResult


async def get_scheduled_words(db: AsyncSession, now: datetime) -> List[Word]:
    """Get words that are scheduled for practice (next_practice <= now)."""
    result = await db.execute(
        select(Word)
        .where(Word.next_practice <= now)
        .order_by(Word.interval.asc())
        .limit(30)
    )
    return result.scalars().all()


async def get_new_words(db: AsyncSession, exclude_word_ids: List[int]) -> List[Word]:
    """Get random new words that haven't been practiced yet."""
    query = select(Word).where(Word.next_practice.is_(None))
    
    if exclude_word_ids:
        query = query.where(Word.id.not_in(exclude_word_ids))
    
    result = await db.execute(query.order_by(func.random()).limit(30))
    return result.scalars().all()


async def get_session_words(db: AsyncSession, session_id: str = None) -> List[WordInDB]:
    """
    Get 30 words for a session.
    - First, get scheduled words (next_practice <= now) ordered by interval
    - If insufficient, fill with random new words (next_practice is None)
    """
    now = datetime.utcnow()
    
    # Get scheduled words first
    scheduled_words = await get_scheduled_words(db, now)
    
    # If we don't have enough words, get new ones
    if len(scheduled_words) < 30:
        existing_ids = [w.id for w in scheduled_words]
        needed = 30 - len(scheduled_words)
        
        new_words = await db.execute(
            select(Word)
            .where(Word.next_practice.is_(None))
            .where(Word.id.not_in(existing_ids))
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


async def update_word_sm2(db: AsyncSession, word_id: int, quality_rating: int) -> Word:
    """
    Update word's next_practice, ease_factor, and interval based on SM-2 algorithm.
    
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
    result = await db.execute(select(Word).where(Word.id == word_id))
    word = result.scalar_one_or_none()
    
    if not word:
        return None
    
    now = datetime.utcnow()
    
    # Update ease factor based on quality rating
    # Formula: new_ef = ef + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    new_ef = word.ease_factor + (0.1 - (5 - quality_rating) * (0.08 + (5 - quality_rating) * 0.02))
    word.ease_factor = max(1.3, new_ef)  # Ensure ease factor doesn't go below 1.3
    
    if quality_rating >= 3:
        # Correct response (quality 3-5) - increment repetitions and calculate interval
        word.repetitions += 1
        
        if word.repetitions == 1:
            word.interval = 1
        elif word.repetitions == 2:
            word.interval = 6
        else:
            # Subsequent repetitions: multiply previous interval by ease factor
            word.interval = int(word.interval * word.ease_factor)
    else:
        # Incorrect response (quality 0-2) - reset repetitions and interval
        word.repetitions = 0
        word.interval = 1  # SM-2 spec: incorrect answers should be scheduled for 1 day later
    
    # Set next_practice based on calculated interval
    word.next_practice = now + timedelta(days=word.interval)
    
    db.add(word)
    await db.commit()
    await db.refresh(word)
    return word


async def create_session_and_get_words(db: AsyncSession) -> tuple[str, List[WordInDB]]:
    """Create a new session and return session_id with 30 words."""
    session_id = str(uuid.uuid4())
    words = await get_session_words(db)
    return session_id, words


async def process_session_results(
    db: AsyncSession, 
    session_id: str, 
    results: List[WordResult]
) -> int:
    """
    Process session results - create records and update word SM-2 values.
    Returns the number of words practiced.
    """
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
        
        # Update word's SM-2 values
        await update_word_sm2(
            db=db,
            word_id=result.word_id,
            quality_rating=result.quality_rating
        )
    
    return len(results)