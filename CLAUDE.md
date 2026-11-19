# Music Discovery CLI

## What this is
A Python command-line tool: give it an artist you like, and it recommends similar artists
you haven't listened to yet, each with a short AI-written reason it fits.

Example:
    discover "Frank Ocean" --user <lastfm_username> --n 10

## How it works (v1 pipeline)
1. Last.fm `artist.getSimilar` for the seed artist (limit ~30, autocorrect=1).
2. If `--user` is given: Last.fm `user.getTopArtists` (period=overall, limit=200) and
   remove any candidate the user already listens to (case-insensitive name match).
3. Last.fm `artist.getTopTags` for the seed and the top ~10 remaining candidates.
4. One LLM call: pick the best N candidates and write a one-sentence reason for each.
   - The LLM may ONLY use the provided names, match scores, and tags. No invented facts
     (no album names, years, or collaborations that aren't in the input).
   - Response must be JSON matching a Pydantic model; validate it, and drop any artist
     that isn't in the candidate list.
5. Print a readable table: rank, artist, match score, reason.

## Stack
- Python 3.11+, `requests`, `pydantic`, `python-dotenv`, `typer` (CLI)
- LLM: one provider SDK (OpenAI or Anthropic) behind a small `llm.py` wrapper
- Tests: `pytest`; mock all HTTP and LLM calls. Tests must never hit the network.
- CI: GitHub Actions runs `pytest` on every push and PR.

## Layout
    src/discover/
        lastfm.py     # API client: similar artists, user top artists, top tags
        filter.py     # remove already-known artists
        llm.py        # prompt building, LLM call, JSON validation
        cli.py        # typer entry point
    tests/
        test_lastfm.py
        test_filter.py
        test_llm.py

## Config
- Secrets live in `.env` (never commit it): `LASTFM_API_KEY`, `LLM_API_KEY`
- `.env.example` documents the variables with empty values.
- Send a descriptive User-Agent header on Last.fm requests.

## Conventions
- Small functions with type hints. Keep API parsing separate from business logic
  so it can be tested with fixture JSON.
- Handle errors clearly: unknown artist (Last.fm error 6), invalid API key (error 10),
  network timeout, and LLM output that fails validation (retry once, then fall back to
  showing candidates ranked by match score without reasons).
- Work in small steps. Propose a plan before writing code for a new module.
- Dev environment is Windows with Git Bash. Use forward-slash paths; activate the
  venv with `source .venv/Scripts/activate`.

## Out of scope for v1
Web UI, Spotify integration, track-level recommendations, caching, mood/natural-language queries.
