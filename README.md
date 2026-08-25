# Research Finder

Research Finder turns a natural-language research topic into a ranked, deduplicated set of academic papers. It has a React web UI, a FastAPI API, DuckDB storage, Gemini-assisted query planning, and two reranking options: a local NVIDIA GPU or a Google Colab GPU service.

## Architecture and workflow

```text
React + Vite (port 5173)
        |
        | POST /api/search, then poll /api/search/status/{job_id}
        v
FastAPI (port 8000)
        |
        +-- Gemini: search-query expansion, seed selection, ranking configuration
        +-- OpenAlex: keyword searches (concurrent)
        +-- Semantic Scholar: keyword and citation-expansion searches (rate-limited)
        +-- Normalization + deduplication
        +-- Reranker: Google Colab GPU OR local CUDA GPU OR disabled
        +-- DuckDB: search history and all ranked papers
        `-- search_outputs/: per-search diagnostic JSON files
```

A search is submitted as a background job so the browser is not held open by the retrieval and reranking work. When the job completes, the API returns the ranked result set; the UI initially displays 50 papers and lets the user raise that display limit. Every ranked paper is also saved to DuckDB.

## Prerequisites

- Python 3.10 or newer
- Node.js with npm
- A Gemini API key for the full search and reranking-configuration workflow
- One reranking option:
  - Google Colab with a GPU (recommended when the local machine has no CUDA GPU), or
  - a local NVIDIA CUDA-capable GPU

Semantic Scholar and OpenAlex credentials are optional but recommended. The app can make unauthenticated requests, though the public APIs are more rate-limited.

## Configure environment

Create the two local environment files from the committed templates. Do not commit the resulting `.env` files.

```powershell
Copy-Item backend\.env.example backend\.env
Copy-Item frontend\.env.example frontend\.env
```

Set these values in `backend/.env`:

```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash

SEMANTIC_SCHOLAR_API_KEY=
OPENALEX_API_KEY=
MAIL=you@example.com

DATABASE_PATH=../data/research_finder.duckdb
FRONTEND_ORIGIN=http://localhost:5173
SEARCH_TIMEOUT_SECONDS=20
SEARCH_LIMIT_PER_SOURCE=15
MAX_EXPANDED_TERMS=15

RERANKER_MODE=remote
COLAB_RERANKER_URL=
BI_ENCODER_MODEL=Alibaba-NLP/gte-modernbert-base
CROSS_ENCODER_MODEL=BAAI/bge-reranker-v2-m3
```

The frontend only needs this in `frontend/.env`:

```env
VITE_API_BASE_URL=http://localhost:8000
```

`RERANKER_MODE` accepts `remote`, `local`, or `disabled`:

- `remote`: sends papers to the running Colab service. `COLAB_RERANKER_URL` is required.
- `local`: loads the bi-encoder and cross-encoder on this computer. Use this only with a working CUDA-enabled PyTorch installation.
- `disabled`: skips model reranking. This is useful for a quick API/UI smoke test, but search quality will be lower.

## Run with Google Colab GPU (no local GPU)

1. Open [colab.ipynb](colab.ipynb) in Google Colab.
2. Select **Runtime → Change runtime type → T4 GPU** (or another GPU), then run the notebook cells in order.
3. Wait for the final cell to print `COLAB_RERANKER_URL=https://...trycloudflare.com`.
4. In `backend/.env`, set:

   ```env
   RERANKER_MODE=remote
   COLAB_RERANKER_URL=https://the-url-printed-by-colab.trycloudflare.com
   ```

5. Keep the Colab runtime running, then start the backend and frontend as shown below.

The tunnel address changes whenever the Colab runtime restarts. Copy the new address into `backend/.env` and restart the backend each time. The tunnel is suitable for development, not a permanent deployment.

## Run with a local GPU

1. Install the CUDA-enabled PyTorch build appropriate for the machine before installing the local-GPU extras.
2. In `backend/.env`, set:

   ```env
   RERANKER_MODE=local
   ```

3. Leave `COLAB_RERANKER_URL` empty; it is ignored in local mode.
4. Install the additional local-GPU packages after the standard backend requirements:

   ```powershell
   pip install -r requirements-local-gpu.txt
   ```

5. Start the backend and frontend below. The first search downloads the configured Hugging Face models, so it needs internet access and may take longer.

If PyTorch cannot see the GPU, do not use `local`; switch to the Colab setup above or set `RERANKER_MODE=disabled`.

## Start the application

Open two terminals from the repository root.

**Terminal 1 — backend**

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
uvicorn src.main:app --reload --port 8000
```

**Terminal 2 — frontend**

```powershell
cd frontend
npm install
npm run dev
```

Open the URL Vite prints (normally `http://localhost:5173`). Confirm the backend is available at `http://localhost:8000/health`.

## API used by the web app

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/search` | Starts a search; returns a `job_id`. |
| `GET` | `/api/search/status/{job_id}` | Polls the search job until it completes or fails. |
| `GET` | `/api/papers/{paper_id}` | Gets a saved paper. |
| `GET` | `/api/search-history` | Lists prior searches. |
| `GET` | `/health` | Backend health check. |

## Generated files

- `data/research_finder.duckdb`: local DuckDB search history and paper records.
- `search_outputs/<timestamp>/`: raw source results and diagnostic JSON for each search.

Both are intentionally ignored by Git. The `.env` files, virtual environments, Node modules, builds, logs, and notebook checkpoints are also ignored. `backend/.env.example` and `frontend/.env.example` are the shareable configuration templates.
