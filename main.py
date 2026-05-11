"""FastAPI application for Der Die Das app."""

from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
import os

from database import get_db
from crud import create_session_and_get_words, process_session_results
from schema import SessionStartResponse, SessionEndRequest, SessionEndResponse

app = FastAPI()

# API routes (defined before static files to take precedence)
@app.post("/sessions/start", response_model=SessionStartResponse)
async def start_session(db: AsyncSession = Depends(get_db)):
    """Start a new session and return session_id with 30 words."""
    session_id, words = await create_session_and_get_words(db)
    return SessionStartResponse(session_id=session_id, words=words)


@app.post("/sessions/end", response_model=SessionEndResponse)
async def end_session(request: SessionEndRequest, db: AsyncSession = Depends(get_db)):
    """Process session results and return summary."""
    words_practiced = await process_session_results(db, request.session_id, request.results)
    return SessionEndResponse(
        message="Session completed successfully",
        words_practiced=words_practiced
    )

# Serve frontend static files
frontend_dist = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dist")
if os.path.exists(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
