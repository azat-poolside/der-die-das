"""Pydantic schemas for Word, User, Progress, and SessionResult models."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


# User schemas
class UserBase(BaseModel):
    """Base schema for User."""
    username: str
    email: str


class UserCreate(UserBase):
    """Schema for creating a new user."""
    password: str  # Plain password, will be hashed


class UserUpdate(BaseModel):
    """Schema for updating a user."""
    username: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None


class UserInDB(UserBase):
    """Schema for User in database."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    hashed_password: str
    created_at: datetime
    is_active: bool
    is_superuser: bool
    last_login_at: Optional[datetime] = None


class UserResponse(BaseModel):
    """Schema for User response (without sensitive data)."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    username: str
    email: str
    created_at: datetime
    is_active: bool


# Progress schemas
class ProgressBase(BaseModel):
    """Base schema for Progress."""
    user_id: int
    word_id: int


class ProgressCreate(ProgressBase):
    """Schema for creating a progress record."""
    pass


class ProgressUpdate(BaseModel):
    """Schema for updating progress."""
    ease_factor: Optional[float] = None
    interval: Optional[int] = None
    repetitions: Optional[int] = None
    next_practice: Optional[datetime] = None


class ProgressInDB(ProgressBase):
    """Schema for Progress in database."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    ease_factor: float
    interval: int
    repetitions: int
    next_practice: Optional[datetime] = None
    next_review: Optional[datetime] = None  # Alias for next_practice (spaced repetition terminology)
    created_at: datetime


# Word schemas
class WordBase(BaseModel):
    """Base schema for Word."""
    noun: str
    article: str
    english_translation: str


class WordCreate(WordBase):
    """Schema for creating a new word."""
    pass


class WordUpdate(BaseModel):
    """Schema for updating a word."""
    noun: Optional[str] = None
    article: Optional[str] = None
    english_translation: Optional[str] = None


class WordInDB(WordBase):
    """Schema for Word in database."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int


class WordInDBWithProgress(WordInDB):
    """Schema for Word with user progress."""
    progress: Optional[ProgressInDB] = None


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
    user_id: int
    results: List[WordResult]


class SessionEndResponse(BaseModel):
    """Response for ending a session."""
    message: str
    words_practiced: int
    retry_words: List[int]  # Word IDs that should be immediately retried (quality_rating < 3)
    retry_words_details: Optional[List[WordInDB]] = None  # Full word details for immediate retry


# Reviews endpoint response
class ReviewResponse(BaseModel):
    """Response for getting words due for review."""
    words_due: List[WordInDBWithProgress]
    total_due: int
    next_review_at: Optional[datetime] = None


# Authentication schemas
class Token(BaseModel):
    """Schema for authentication token response."""
    access_token: str
    token_type: str


class TokenData(BaseModel):
    """Schema for token payload data."""
    user_id: Optional[int] = None
    username: Optional[str] = None