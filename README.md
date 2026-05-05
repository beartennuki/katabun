# Katabun

An AI-powered quiz platform built with Flask. Users can generate multiple-choice quizzes on any topic, take quizzes from a curated bank, and receive detailed assessments with personalised feedback.

## Features

- **Auto Quiz Generation** — generate MCQ quizzes on any topic using AI
- **Quiz Bank** — browse and take quizzes organised by category
- **Assessments** — detailed scoring with per-question advice and overall feedback
- **Google OAuth** — sign in with Google
- **Credit System** — credit-based usage (quiz generation costs 5 credits)

## Tech Stack

- **Backend:** Python, Flask, Gunicorn
- **Database:** MongoDB (PyMongo)
- **Cache:** Redis
- **Auth:** Google OAuth via Authlib
- **Encryption:** Fernet (cryptography)

## Getting Started

### Prerequisites

- Python 3.10+
- MongoDB instance
- Redis instance
- Google OAuth credentials

### Installation

```bash
git clone https://github.com/qunox-01/katabun.git
cd katabun
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Environment Variables

Copy `.env.example` to `.env` and fill in the values:

```bash
cp .env.example .env
```

| Variable | Description |
|---|---|
| `KATABUN_ENV_TYPE` | `DEV` or `PROD` |
| `KATABUN_KEY` | Flask secret key |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret |
| `REHAL_URI` | Base URL of the backend AI/job API |
| `REDIS_CACHE_URL` | Redis connection URL |
| `GOOGLE_ANALYTICS_KEY` | GA4 measurement ID (optional) |
| `LOADING_SALT` | Salt for Fernet encryption |
| `LOADING_PASSWORD` | Password for Fernet encryption |

### Running Locally

```bash
python app.py
```

The app will start on `http://0.0.0.0:5010`.

### Production

```bash
gunicorn app:application
```

## Project Structure

```
katabun/
├── app.py              # Entry point
├── katabun.py          # App factory and routes
├── src/
│   ├── api.py          # Job/task API client
│   ├── mongoio.py      # MongoDB interface
│   ├── googleauth.py   # Google OAuth handler
│   ├── util.py         # ID generators and helpers
│   └── pages/          # Page-level logic (quiz, bank, account, etc.)
├── templates/          # Jinja2 HTML templates
├── static/             # CSS, images
└── inj/                # Quiz injection scripts
```

## License

MIT
