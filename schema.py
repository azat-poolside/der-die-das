"""Pydantic schemas for Word and SessionResult models."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class WordBase(BaseModel):
    """Base schema for Word."""
    german_word: str
    article: str
    english_translation: str


class WordCreate(WordBase):
    """Schema for creating a new word."""
    pass


class WordUpdate(BaseModel):
    """Schema for updating a word."""
    german_word: Optional[str] = None
    article: Optional[str] = None
    english_translation: Optional[str] = None
    next_practice: Optional[datetime] = None
    ease_factor: Optional[float] = None
    interval: Optional[int] = None


class WordInDB(WordBase):
    """Schema for Word in database."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    next_practice: Optional[datetime] = None
    ease_factor: float
    interval: int


class WordInDBWithResults(WordInDB):
    """Schema for Word with session results."""
    session_results: List["SessionResultInDB"] = []


# SessionResult schemas
class SessionResultBase(BaseModel):
    """Base schema for SessionResult."""
    word_id: int
    quality_rating: int  # SM-2 quality rating (0-5)
    attempts: int
    response_time_ms: int


class SessionResultCreate(SessionResultBase):
    """Schema for creating a session result."""
    session_id: str


class SessionResultInDB(SessionResultBase):
    """Schema for SessionResult in database."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    session_id: str


# Session schemas
class SessionStartResponse(BaseModel):
    """Response for starting a session."""
    session_id: str
    words: List[WordInDB]


class WordResult(BaseModel):
    """Result for a single word in a session."""
    word_id: int
    quality_rating: int  # SM-2 quality rating (0-5)
    attempts: int
    response_time_ms: int


class SessionEndRequest(BaseModel):
    """Request body for ending a session."""
    session_id: str
    results: List[WordResult]


class SessionEndResponse(BaseModel):
    """Response for ending a session."""
    message: str
    words_practiced: int


# Update forward reference
WordInDBWithResults.model_rebuild()