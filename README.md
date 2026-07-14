# Wiring Harness Troubleshooting Agent

An AI agent for wiring harness manufacturing, assembly, and troubleshooting. It answers technical questions from documentation and past cases, ingests new documents, and can send email reports, all orchestrated through an **n8n** workflow that sits between a **React** frontend and a **FastAPI** backend agent.

## Architecture

```
React (Vite) Frontend
        │  POST /webhook/chatbot2  (multipart: session_id, message, file)
        ▼
n8n workflow (wiring-harness-agent-Workflow.json)
        │  calls the backend agent
        ▼
FastAPI backend (api.py → /agent)
        │
        ├── agent/planner.py   → decides next action (LLM: Qwen via OpenRouter)
        ├── agent/executor.py  → runs the chosen tool
        │       ├── tools/search_docs.py   → Qdrant vector search (Ollama embeddings)
        │       ├── tools/search_cases.py  → SQLite troubleshooting cases DB
        │       ├── upload_document        → forwards file to n8n upload endpoint
        │       └── send_email             → forwards to n8n email endpoint
        └── ingest_Docling.py  → pulls files from Google Drive, chunks them
                                  (Docling) and indexes them into Qdrant
```

The frontend never talks to the FastAPI backend directly — it talks to the **n8n webhook**, and n8n calls the backend (and other services such as email/upload) from there.

## Repository structure

```
.
├── wiring-backend/                       # FastAPI agent backend
│   ├── api.py                            # FastAPI app, /agent endpoint
│   ├── agent/
│   │   ├── loop.py                       # main agent loop (plan → execute → answer)
│   │   ├── planner.py                    # LLM-based planner (tool selection)
│   │   └── executor.py                   # tool execution, email, uploads
│   ├── tools/
│   │   ├── search_docs.py                # Qdrant semantic search over documents
│   │   └── search_cases.py               # SQLite troubleshooting case search
│   ├── ingest_Docling.py                 # Google Drive ingestion + Docling chunking
│   ├── documents/                        # sample source documents
│   ├── database/troubleshooting.db       # SQLite troubleshooting cases
│   ├── qdrant_storage/                   # local Qdrant data (if run locally)
│   ├── credentials.json                  # Google service account (DO NOT COMMIT)
│   └── Dockerfile
├── frontend/                             # React + Vite chat UI
│   ├── src/services/api.js               # calls the n8n webhook
│   ├── vite.config.js                    # dev proxy to local n8n (port 5678)
│   └── .env                              # VITE_API_URL
└── wiring-harness-agent-Workflow.json    # n8n workflow (import into n8n)
```

## Prerequisites

- Python 3.11
- Node.js 18+ and npm
- [n8n](https://n8n.io/) (running locally, e.g. `npx n8n` or Docker)
- [Ollama](https://ollama.com/) running locally with `nomic-embed-text` (embeddings) pulled
- A [Qdrant](https://qdrant.tech/) instance (local or cloud)
- An [OpenRouter](https://openrouter.ai/) API key (used for the `qwen` planning/answering model)
- A Google Cloud service account with Drive read access (for document ingestion)
- [cloudflared](https://github.com/cloudflare/cloudflared) if you want to expose your local n8n publicly

## Environment variables

### `wiring-backend/.env`

| Variable | Description |
|---|---|
| `QDRANT_URL` | URL of your Qdrant instance |
| `QDRANT_API_KEY` | Qdrant API key |
| `OPENROUTER_API_KEY` | OpenRouter API key (Qwen model calls) |
| `DRIVE_FOLDER_ID` | Google Drive folder ID to ingest documents from |
| `upload_path` | n8n endpoint the backend forwards uploaded files to |
| `email_path` | n8n endpoint the backend forwards email requests to |
| `admin_email` / `ADMIN_EMAIL` | Fallback recipient when no valid address is given ⚠️ *code currently reads both casings in different files — set both, or align them (see Known Issues)* |

Place your Google service account key at `wiring-backend/credentials.json` (already referenced by `ingest_Docling.py`).

### `frontend/.env`

| Variable | Description |
|---|---|
| `VITE_API_URL` | Public URL of the Cloudflare tunnel pointing to your local n8n (only used in "deployed frontend" mode, see below) |

## Running locally

### 1. Backend

```bash
cd wiring-backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn api:app --reload --port 8000
```

Or with Docker:

```bash
cd wiring-backend
docker build -t wiring-backend .
docker run -p 8000:8000 --env-file .env wiring-backend
```

### 2. n8n

Start n8n locally and import `wiring-harness-agent-Workflow.json`. Make sure the workflow's HTTP Request nodes point to your backend (`http://localhost:8000/agent` if running outside Docker, or the appropriate host if n8n and the backend are both containerized).

If you get the following error:
> **"Unrecognized node type: n8n-nodes-base.executeCommand"**

it means that the version of n8n you have installed does not have the **Run Command** node enabled.
To fix it, run the following commands in your terminal:
```bash
set NODES_EXCLUDE=ExecuteCommand,LocalFileTrigger
set NODES_INCLUDE=ExecuteCommand,LocalFileTrigger
```
Then start n8n normally.


### 3. Frontend

The frontend can run in two modes, controlled by `src/services/api.js`:

```js
const BASE_URL = "/webhook";
//const BASE_URL = import.meta.env.VITE_API_URL;
```

**Mode A — Local dev (recommended while developing):**
Keep `BASE_URL = "/webhook"` (uncommented). Vite's dev proxy (`vite.config.js`) forwards any `/webhook/*` request to `http://localhost:5678` (your local n8n), so you just run:

```bash
cd frontend
npm install
npm run dev
```

**Mode B — Deployed frontend (e.g. Vercel):**
A deployed frontend has no Vite dev proxy, so it can't reach `localhost:5678`. Instead:
1. Comment out `const BASE_URL = "/webhook"` and uncomment `const BASE_URL = import.meta.env.VITE_API_URL;`.
2. Expose your local n8n with a Cloudflare tunnel:
   ```bash
   cloudflared tunnel --url http://localhost:5678
   ```
3. Set `VITE_API_URL` in `frontend/.env` (and in your Vercel project's environment variables) to that tunnel URL, e.g.:
   ```
   VITE_API_URL=https://patrick-delivers-telephony-floppy.trycloudflare.com
   ```
4. Deploy/redeploy the frontend.

> Note: Cloudflare's free `trycloudflare.com` tunnels are temporary — the URL changes every time you restart `cloudflared`, so you'll need to update `VITE_API_URL` (and redeploy) each time.

## LLM configuration (`call_qwen`)

`agent/executor.py` defines **two** implementations of `call_qwen` (used by both the planner and the answer generator). Only one should be active at a time — comment/uncomment as needed:

```python
"""def call_qwen(prompt):
    # Local Ollama version
    response = ollama.chat(model="qwen2.5:7b", ...)
    ...
"""

def call_qwen(prompt):
    # OpenRouter version (currently active)
    response = client.chat.completions.create(model="qwen/qwen3.6-27b", ...)
    ...
```

| | **Ollama (local)** | **OpenRouter (cloud)** |
|---|---|---|
| Model | `qwen2.5:7b` | `qwen/qwen3.6-27b` (stronger) |
| Token limit | None — runs on your own machine, so no hard cap | Limited by `max_tokens` / provider quota (currently `14788`) |
| Quality | Lower — smaller local model | Higher — larger, more capable model |
| Requirements | Ollama running locally with the model pulled (`ollama pull qwen2.5:7b`) | `OPENROUTER_API_KEY` with available quota |
| Cost | Free (local compute) | Paid per token via OpenRouter |

**Trade-off:** the local Ollama option removes the token-limit/quota problem entirely since nothing is metered, but gives up model quality. The OpenRouter option gives a stronger, more accurate model, at the cost of being bound by `max_tokens` and your OpenRouter plan's quota.

To switch, comment out the version you don't want to use and uncomment the other — only one `call_qwen` definition should be active in the file at a time.
