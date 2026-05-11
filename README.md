# Der Die Das - German Articles Learning App

A web-based spaced repetition app for learning German articles (der, die, das). Similar to Anki, but specifically designed for German noun articles.

## Features

- **Article Quiz**: Users select the correct article (der/die/das) for each noun
- **Immediate Feedback**: Wrong answers are repeated within the same session
- **Spaced Repetition**: Incorrect words are scheduled for review the next day
- **Multi-user Support**: User authentication and individual progress tracking
- **Web-based**: Accessible from any device with a browser

## Tech Stack

- **Frontend**: React/Vue.js (TBD)
- **Backend**: Node.js/Express or Python/FastAPI (TBD)
- **Database**: PostgreSQL or SQLite
- **Authentication**: JWT-based auth
- **Deployment**: Docker-ready

## How It Works

1. User sees a German noun and selects an article
2. If correct → word is scheduled for later review based on spaced repetition
3. If wrong → word repeats immediately in the same session and is scheduled for next-day review
4. Progress is saved per user and syncs across sessions

## Getting Started

```bash
# Clone the repository
git clone https://github.com/yourusername/der-die-das.git
cd der-die-das

# Install dependencies
npm install  # or pip install -r requirements.txt

# Set up environment variables
cp .env.example .env

# Run the development server
npm run dev  # or python main.py
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License