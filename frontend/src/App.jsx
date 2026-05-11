import React, { useState, useEffect } from 'react'
import './index.css'

const API_BASE = 'http://localhost:8000'

function App() {
  const [session, setSession] = useState(null)
  const [initialWords, setInitialWords] = useState([]) // Original 30 words
  const [wordQueue, setWordQueue] = useState([]) // Queue of words to show (includes repeats)
  const [currentIndex, setCurrentIndex] = useState(0)
  const [selectedAnswer, setSelectedAnswer] = useState(null)
  const [showTranslation, setShowTranslation] = useState(false)
  const [results, setResults] = useState([])
  const [sessionComplete, setSessionComplete] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // Start a new session
  const startSession = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch(`${API_BASE}/sessions/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      })
      if (!response.ok) throw new Error('Failed to start session')
      const data = await response.json()
      setSession({ id: data.session_id })
      setInitialWords(data.words)
      setWordQueue([...data.words]) // Initialize queue with all words
      setCurrentIndex(0)
      setResults([])
      setSessionComplete(false)
      setSelectedAnswer(null)
      setShowTranslation(false)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  // Handle article selection
  const handleAnswer = (article) => {
    const currentWord = wordQueue[currentIndex]
    const isCorrect = article === currentWord.article
    
    setSelectedAnswer(article)
    setShowTranslation(true)

    // Record result (quality_rating: correct=4, incorrect=1)
    const result = {
      word_id: currentWord.id,
      quality_rating: isCorrect ? 4 : 1,
      attempts: isCorrect ? 1 : 1, // Track attempts
      response_time_ms: 1000
    }

    const newResults = [...results, result]
    setResults(newResults)

    // If wrong, immediately add the word back to the queue for repetition
    // This implements: "Immediately repeat wrong answers within the same session"
    if (!isCorrect) {
      setWordQueue(prev => [...prev, currentWord])
    }

    // Move to next word after a short delay
    setTimeout(() => {
      setShowTranslation(false)
      setSelectedAnswer(null)
      
      if (currentIndex + 1 < wordQueue.length) {
        setCurrentIndex(currentIndex + 1)
      } else {
        // Session complete - send final results
        endSession(newResults)
      }
    }, 1500)
  }

  // End the session and send results
  const endSession = async (finalResults) => {
    setLoading(true)
    try {
      const response = await fetch(`${API_BASE}/sessions/end`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: session.id,
          results: finalResults
        })
      })
      if (!response.ok) throw new Error('Failed to end session')
      const data = await response.json()
      setSession({ id: session.id, summary: data })
      setSessionComplete(true)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  // Get current word
  const currentWord = wordQueue[currentIndex]

  // Start Screen
  if (!session) {
    return (
      <div className="app">
        <div className="start-screen">
          <h1>Der Die Das</h1>
          <p>Learn German articles with spaced repetition</p>
          <button onClick={startSession} disabled={loading}>
            {loading ? 'Loading...' : 'Start Learning'}
          </button>
          {error && <p className="error">{error}</p>}
        </div>
      </div>
    )
  }

  // End Screen
  if (sessionComplete) {
    const correctCount = results.filter(r => r.quality_rating === 4).length
    const totalCount = results.length
    
    return (
      <div className="app">
        <div className="end-screen">
          <h1>Session Complete!</h1>
          <div className="summary">
            <p>Words Practiced: {totalCount}</p>
            <p>Correct Answers: {correctCount}</p>
            <p>Accuracy: {Math.round((correctCount / totalCount) * 100)}%</p>
          </div>
          <button onClick={startSession}>Start New Session</button>
        </div>
      </div>
    )
  }

  // Quiz Screen
  return (
    <div className="app">
      <div className="quiz-screen">
        <div className="progress">
          Word {currentIndex + 1} of {wordQueue.length}
        </div>
        
        {currentWord && (
          <>
            <div className="word-container">
              <h2 className="german-word">{currentWord.german_word}</h2>
              {showTranslation && (
                <p className="english-translation">{currentWord.english_translation}</p>
              )}
            </div>

            {!showTranslation ? (
              <div className="article-buttons">
                <button 
                  className="article-btn der" 
                  onClick={() => handleAnswer('der')}
                >
                  der
                </button>
                <button 
                  className="article-btn die" 
                  onClick={() => handleAnswer('die')}
                >
                  die
                </button>
                <button 
                  className="article-btn das" 
                  onClick={() => handleAnswer('das')}
                >
                  das
                </button>
              </div>
            ) : (
              <div className="feedback">
                {selectedAnswer === currentWord.article ? (
                  <p className="correct-feedback">✓ Correct!</p>
                ) : (
                  <p className="incorrect-feedback">
                    ✗ Incorrect. The correct answer is "{currentWord.article}"
                  </p>
                )}
              </div>
            )}
          </>
        )}
        
        {error && <p className="error">{error}</p>}
      </div>
    </div>
  )
}

export default App
