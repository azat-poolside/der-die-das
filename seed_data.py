"""Script to seed the database with initial German words."""

import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import async_session, engine, Base
from models import Word


GERMAN_WORDS = [
    # der words
    {"noun": "Hund", "article": "der", "english_translation": "dog"},
    {"noun": "Tisch", "article": "der", "english_translation": "table"},
    {"noun": "Stuhl", "article": "der", "english_translation": "chair"},
    {"noun": "Apfel", "article": "der", "english_translation": "apple"},
    {"noun": "Buch", "article": "der", "english_translation": "book"},
    {"noun": "Haus", "article": "der", "english_translation": "house"},
    {"noun": "Baum", "article": "der", "english_translation": "tree"},
    {"noun": "Wasser", "article": "der", "english_translation": "water"},
    {"noun": "Tag", "article": "der", "english_translation": "day"},
    {"noun": "Mann", "article": "der", "english_translation": "man"},
    {"noun": "Jahr", "article": "der", "english_translation": "year"},
    {"noun": "Zeit", "article": "der", "english_translation": "time"},
    {"noun": "Weg", "article": "der", "english_translation": "way"},
    {"noun": "Kopf", "article": "der", "english_translation": "head"},
    {"noun": "Arbeit", "article": "der", "english_translation": "work"},
    
    # die words
    {"noun": "Katze", "article": "die", "english_translation": "cat"},
    {"noun": "Frau", "article": "die", "english_translation": "woman"},
    {"noun": "Maus", "article": "die", "english_translation": "mouse"},
    {"noun": "Blume", "article": "die", "english_translation": "flower"},
    {"noun": "Hand", "article": "die", "english_translation": "hand"},
    {"noun": "Schule", "article": "die", "english_translation": "school"},
    {"noun": "Stadt", "article": "die", "english_translation": "city"},
    {"noun": "Nacht", "article": "die", "english_translation": "night"},
    {"noun": "Zeit", "article": "die", "english_translation": "time"},
    {"noun": "Welt", "article": "die", "english_translation": "world"},
    {"noun": "Farbe", "article": "die", "english_translation": "color"},
    {"noun": "Sprache", "article": "die", "english_translation": "language"},
    {"noun": "Frage", "article": "die", "english_translation": "question"},
    {"noun": "Antwort", "article": "die", "english_translation": "answer"},
    {"noun": "Musik", "article": "die", "english_translation": "music"},
    
    # das words
    {"noun": "Kind", "article": "das", "english_translation": "child"},
    {"noun": "Auto", "article": "das", "english_translation": "car"},
    {"noun": "Bild", "article": "das", "english_translation": "picture"},
    {"noun": "Haus", "article": "das", "english_translation": "house"},
    {"noun": "Spiel", "article": "das", "english_translation": "game"},
    {"noun": "Licht", "article": "das", "english_translation": "light"},
    {"noun": "Herz", "article": "das", "english_translation": "heart"},
    {"noun": "Kind", "article": "das", "english_translation": "child"},
    {"noun": "Wort", "article": "das", "english_translation": "word"},
    {"noun": "Jahr", "article": "das", "english_translation": "year"},
    {"noun": "Ticket", "article": "das", "english_translation": "ticket"},
    {"noun": "Radio", "article": "das", "english_translation": "radio"},
    {"noun": "Telefon", "article": "das", "english_translation": "telephone"},
    {"noun": "Bett", "article": "das", "english_translation": "bed"},
    {"noun": "Fenster", "article": "das", "english_translation": "window"},
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