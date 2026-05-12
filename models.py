"""SQLAlchemy models for Der Die Das app."""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    """Model for app users with authentication."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default="CURRENT_TIMESTAMP")
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    last_login_at = Column(DateTime, nullable=True)

    # Relationships
    progress_records = relationship("Progress", back_populates="user", cascade="all, delete-orphan")


class Word(Base):
    """Model for German words with their articles."""

    __tablename__ = "words"

    id = Column(Integer, primary_key=True, index=True)
    noun = Column(String, index=True, nullable=False)
    article = Column(String, nullable=False)  # der, die, or das
    english_translation = Column(String, nullable=False)

    # Relationship to user progress and session results
    progress_records = relationship("Progress", back_populates="word", cascade="all, delete-orphan")
    session_results = relationship("SessionResult", back_populates="word")


class Progress(Base):
    """Model for tracking user-specific progress per word with SM-2 scheduling."""

    __tablename__ = "progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    word_id = Column(Integer, ForeignKey("words.id"), nullable=False)
    next_practice = Column(DateTime, nullable=True)
    ease_factor = Column(Float, default=2.5)  # SM-2 algorithm ease factor (2.5 default)
    interval = Column(Integer, default=0)  # Days until next practice
    repetitions = Column(Integer, default=0)  # Consecutive correct answers (SM-2)
    created_at = Column(DateTime, nullable=False, server_default="CURRENT_TIMESTAMP")

    # Relationships
    user = relationship("User", back_populates="progress_records")
    word = relationship("Word", back_populates="progress_records")

    # Ensure unique user-word combination (one progress record per user per word)
    __table_args__ = (
        UniqueConstraint("user_id", "word_id", name="uix_user_word"),
    )


class SessionResult(Base):
    """Model for tracking session results."""

    __tablename__ = "session_results"

    id = Column(Integer, primary_key=True, index=True)
    word_id = Column(Integer, ForeignKey("words.id"), nullable=False)
    session_id = Column(String, index=True, nullable=False)
    quality_rating = Column(Integer, nullable=False)  # SM-2 quality rating (0-5)
    attempts = Column(Integer, nullable=False)
    response_time_ms = Column(Integer, nullable=False)

    # Relationship to word
    word = relationship("Word", back_populates="session_results")
