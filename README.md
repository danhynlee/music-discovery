# Music Discovery

A command-line tool that recommends similar artists you haven't listened to yet, each with a short AI-written reason it fits.

## Setup

Requires Python 3.11+.

```bash
git clone https://github.com/danhynlee/music-discovery.git
cd music-discovery
python -m venv .venv
source .venv/Scripts/activate   # Windows (Git Bash); use .venv/bin/activate on macOS/Linux
pip install -e ".[dev]"
cp .env.example .env            # then fill in LASTFM_API_KEY and LLM_API_KEY
pytest
```

## Usage

_Coming soon._
