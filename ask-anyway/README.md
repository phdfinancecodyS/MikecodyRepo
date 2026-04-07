# MikecodyRepo

Shared workspace for Cody & Mike  - Ask Anyway platform, CCE backend, creator tools, and planning docs.

---

## What's in here

| Folder / File | What it is |
|---|---|
| `ask-anyway-chat.html` | Main Ask Anyway chatbot UI  - runs in the browser |
| `cce-backend/` | FastAPI conversation engine (CCE)  - powers the chatbot |
| `ask-anyway-workspace/` | Full platform  - content, guides, quiz, marketing, API routes |
| `ask-anyway-cody-handoff-2026-03-20-final/` | Handoff archive with brand, content, and planning docs |
| `ask-anyway-deploy/` | Static deploy files (landing page, dashboard) |
| `CreatorScraper/` | Instagram + TikTok scraper scripts |
| `tax-prep-strategy.html` | Tax prep strategy tool |
| `typewriter-demo.html` | Typewriter animation style demos |

---

## Prerequisites

Make sure you have these installed before starting:

- [Git](https://git-scm.com/)
- [Python 3.9+](https://www.python.org/)
- A terminal (zsh on Mac, bash or WSL on Windows)

---

## First-time setup (clone the repo)

```bash
git clone https://github.com/phdfinancecodyS/MikecodyRepo.git
cd MikecodyRepo
```

---

## Starting the local environment

Quick start for shared work:

```bash
./run-shared-workspace.sh
```

This starts both services with standard ports:
- Frontend static server at `http://127.0.0.1:3131/ask-anyway-deploy/index.html`
- CCE backend at `http://127.0.0.1:8000`

Run the API smoke test any time:

```bash
./cce-backend/smoke-test.sh
```

**Step 1  - Start the file server** (serves the HTML tools at localhost:3131)

```bash
python3 -m http.server 3131 &
```

Then open your browser to: `http://localhost:3131/ask-anyway-chat.html`

---

**Step 2  - Start the CCE backend** (powers the chatbot API)

```bash
cd cce-backend
./start.sh
```

This will:
- Create a Python virtual environment (`.venv/`) if it doesn't exist
- Install all dependencies from `requirements.txt`
- Start the API at `http://localhost:8000`

To verify it's running:
```bash
curl http://localhost:8000/health
# → {"status":"ok","version":"1.0.0"}
```

> **Note:** The file server and CCE backend both need to be running for the chatbot to work fully. If the backend is offline, the chatbot falls back to its built-in local engine automatically.

---

## Day-to-day workflow

### Before you start working

Always pull the latest changes first so you don't overwrite each other's work:

```bash
git pull
```

---

### While you work

Edit any files normally  - VS Code, Cursor, whatever you use.

---

### When you're done (commit + push)

```bash
git add .
git commit -m "short description of what you changed"
git push
```

**Examples of good commit messages:**
- `add anxiety guide worksheet`
- `fix crisis detection regex in cce-backend`
- `update tiktok script templates`
- `refactor chatbot recommendation cards`

---

### If you get a conflict

When two people edit the same file, Git will tell you on `git pull`. Open the file, look for the conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`), keep the version you want, then:

```bash
git add .
git commit -m "resolve merge conflict"
git push
```

---

## CCE Backend  - quick reference

The backend lives at `http://localhost:8000` when running.

| Endpoint | Method | What it does |
|---|---|---|
| `/health` | GET | Check if server is up |
| `/trees` | GET | List available conversation trees |
| `/session/start` | POST | Start a new chat session |
| `/session/{id}/respond` | POST | Send a user message or option choice |
| `/session/{id}/outcome` | GET | Get the final outcome/recommendations |
| `/docs` | GET | Swagger UI  - interactive API docs |

**Conversation trees available:**
- `main-flow`  - emoji check-in → topic matching (default)
- `mental-health-triage`  - 10-question scored assessment
- `psychoeducational-flow`  - open-ended exploration

---

## Adding Python dependencies

If you need to add a new Python package to the backend:

```bash
cd cce-backend
python3 -m venv .venv  # first run only, if needed
source .venv/bin/activate
pip install <package-name>
pip freeze > requirements.txt
git add requirements.txt
git commit -m "add <package-name> to requirements"
git push
```

The other person just runs `./start.sh` and it will install automatically.

Rule:
- Treat `ask-anyway/cce-backend/.venv` as the only backend Python environment.
- Do not use a repo-root `.venv` for the live Ask Anyway app.

---

## What's ignored (not tracked by git)

These are excluded via `.gitignore` and will never be committed:

- `.venv/`  - Python virtual environment (rebuilt locally by `start.sh`)
- `__pycache__/`  - Python bytecode
- `.DS_Store`  - Mac system files
- `Zoom/`  - Zoom recordings
- `*.zip`  - Archive files
- `.env` files  - Secrets and API keys

---

## Questions / issues

Open a GitHub Issue on the repo or just message each other directly.
