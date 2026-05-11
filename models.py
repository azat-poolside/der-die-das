"""SQLAlchemy models for Der Die Das app."""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, Boolean
from sqlalchemy.orm import relationship
from database import Base


class Word(Base):
    """Model for German words with their articles."""

    __tablename__ = "words"

    id = Column(Integer, primary_key=True, index=True)
    german_word = Column(String, index=True, nullable=False)
    article = Column(String, nullable=False)  # der, die, or das
    english_translation = Column(String, nullable=False)
    next_practice = Column(DateTime, nullable=True)
    ease_factor = Column(Float, default=2.5)  # SM-2 algorithm ease factor (2.5 default)
    interval = Column(Integer, default=0)  # Days until next practice
    repetitions = Column(Integer, default=0)  # Consecutive correct answers (SM-2)

    # Relationship to session results
    session_results = relationship("SessionResult", back_populates="word")


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
