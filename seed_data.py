"""Script to seed the database with initial German words."""

import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import async_session, engine, Base
from models import Word


GERMAN_WORDS = [
    # der words
    {"german_word": "Hund", "article": "der", "english_translation": "dog"},
    {"german_word": "Tisch", "article": "der", "english_translation": "table"},
    {"german_word": "Stuhl", "article": "der", "english_translation": "chair"},
    {"german_word": "Apfel", "article": "der", "english_translation": "apple"},
    {"german_word": "Buch", "article": "der", "english_translation": "book"},
    {"german_word": "Haus", "article": "der", "english_translation": "house"},
    {"german_word": "Baum", "article": "der", "english_translation": "tree"},
    {"german_word": "Wasser", "article": "der", "english_translation": "water"},
    {"german_word": "Tag", "article": "der", "english_translation": "day"},
    {"german_word": "Mann", "article": "der", "english_translation": "man"},
    {"german_word": "Jahr", "article": "der", "english_translation": "year"},
    {"german_word": "Zeit", "article": "der", "english_translation": "time"},
    {"german_word": "Weg", "article": "der", "english_translation": "way"},
    {"german_word": "Kopf", "article": "der", "english_translation": "head"},
    {"german_word": "Arbeit", "article": "der", "english_translation": "work"},
    
    # die words
    {"german_word": "Katze", "article": "die", "english_translation": "cat"},
    {"german_word": "Frau", "article": "die", "english_translation": "woman"},
    {"german_word": "Maus", "article": "die", "english_translation": "mouse"},
    {"german_word": "Blume", "article": "die", "english_translation": "flower"},
    {"german_word": "Hand", "article": "die", "english_translation": "hand"},
    {"german_word": "Schule", "article": "die", "english_translation": "school"},
    {"german_word": "Stadt", "article": "die", "english_translation": "city"},
    {"german_word": "Nacht", "article": "die", "english_translation": "night"},
    {"german_word": "Zeit", "article": "die", "english_translation": "time"},
    {"german_word": "Welt", "article": "die", "english_translation": "world"},
    {"german_word": "Farbe", "article": "die", "english_translation": "color"},
    {"german_word": "Sprache", "article": "die", "english_translation": "language"},
    {"german_word": "Frage", "article": "die", "english_translation": "question"},
    {"german_word": "Antwort", "article": "die", "english_translation": "answer"},
    {"german_word": "Musik", "article": "die", "english_translation": "music"},
    
    # das words
    {"german_word": "Kind", "article": "das", "english_translation": "child"},
    {"german_word": "Auto", "article": "das", "english_translation": "car"},
    {"german_word": "Bild", "article": "das", "english_translation": "picture"},
    {"german_word": "Haus", "article": "das", "english_translation": "house"},
    {"german_word": "Spiel", "article": "das", "english_translation": "game"},
    {"german_word": "Licht", "article": "das", "english_translation": "light"},
    {"german_word": "Herz", "article": "das", "english_translation": "heart"},
    {"german_word": "Kind", "article": "das", "english_translation": "child"},
    {"german_word": "Wort", "article": "das", "english_translation": "word"},
    {"german_word": "Jahr", "article": "das", "english_translation": "year"},
    {"german_word": "Ticket", "article": "das", "english_translation": "ticket"},
    {"german_word": "Radio", "article": "das", "english_translation": "radio"},
    {"german_word": "Telefon", "article": "das", "english_translation": "telephone"},
    {"german_word": "Bett", "article": "das", "english_translation": "bed"},
    {"german_word": "Fenster", "article": "das", "english_translation": "window"},
]


async def seed_database():
    """Seed the database with German words."""
    async with engine.begin() as conn:
        # Create tables
        await conn.run_sync(Base.metadata.create_all)
    
    async with async_session() as session:
        # Check if words already exist
        result = await session.execute(select(Word).limit(1))
        existing_word = result.scalar_one_or_none()
        
        if existing_word:
            print("Database already seeded. Skipping...")
            return
        
        # Add words
        for word_data in GERMAN_WORDS:
            word = Word(**word_data)
            session.add(word)
        
        await session.commit()
        print(f"Seeded {len(GERMAN_WORDS)} German words into the database.")


if __name__ == "__main__":
    asyncio.run(seed_database())