# Hackathon project

Team project for the GDG Agentic AI Hackathon (University of Debrecen). We have one day,
so working, demoable code beats perfect code.

## How to work

- Keep code simple and readable. Every teammate must be able to explain it to the judges.
- Small steps: build the smallest thing that works, run it, then add the next piece.
- Python: use `uv` (`uv add <package>`, `uv run <script>`). Don't use plain `pip`.
- Before adding a new library, say which one and why in one sentence.
- After each change, tell me how to run or test it.

## Secrets

- API keys and passwords live only in `.env` (never committed). `.env.example` lists the variable names with empty values.
- Never print, log or hard-code a key.

## Git

- You may run `git add`, `git commit` and `git push` yourself when a step is done and the demo works.
- Before committing, run `git status` and make sure `.env` and other secrets are not staged. Stop and tell me if they are.
- Use short conventional messages (`feat:`, `fix:`, `chore:`). Never force-push, and never rewrite history.

## Demo

- Keep a working version at all times. If a change breaks the demo, revert it first, then fix.
