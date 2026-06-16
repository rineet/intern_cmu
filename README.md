# Research Finder

Research Finder is a research discovery platform that converts natural-language research ideas into academic search queries and retrieves relevant papers from OpenAlex and arXiv.

The current implementation focuses on research intent understanding, keyword expansion, paper retrieval, storage, and presentation.

Future versions will introduce semantic search, RAG pipelines, PDF ingestion, citation analysis, and research assistance features.

---

## Features

### Current Features

* Natural-language research queries
* Gemini-powered keyword expansion
* OpenAlex integration
* arXiv integration
* Paper deduplication
* Search history persistence
* Timeline-based filtering
* Paper metadata exploration
* FastAPI backend
* React frontend
* DuckDB persistence layer

### Planned Features

* Vector embeddings
* Semantic reranking
* Retrieval-Augmented Generation (RAG)
* PDF ingestion and chunking
* Research gap analysis
* Citation graph generation
* Bibliography generation
* Saved paper collections
* Research summaries

---

## System Architecture

### High-Level Flow

User Query
→ Gemini Keyword Expansion
→ OpenAlex Search
→ arXiv Search
→ Result Normalization
→ Deduplication
→ DuckDB Persistence
→ Frontend Presentation

---

## Repository Structure

backend/

src/
api/ # FastAPI routes
core/ # configuration and logging
db/ # database setup
repositories/ # persistence layer
services/ # business logic
schemas.py # API contracts
contracts.py # future extension contracts

frontend/

src/
api/ # API communication
components/ # reusable UI components
hooks/ # React Query hooks
pages/ # page-level components
lib/ # utilities and API client

---

## Technology Stack

Frontend

* React
* Vite
* TailwindCSS
* React Query
* Axios

Backend

* FastAPI
* Gemini API
* OpenAlex API
* arXiv API
* DuckDB
* SQLAlchemy

---

## Getting Started

### Backend

```bash
cd backend

python -m venv .venv

# Windows
.venv\Scripts\activate

pip install -r requirements.txt

copy .env.example .env

uvicorn src.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend

npm install

copy .env.example .env

npm run dev
```

---

## Environment Variables

Backend

```env
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.0-flash
DATABASE_PATH=./data/research_finder.duckdb
FRONTEND_ORIGIN=http://localhost:5173
```

Frontend

```env
VITE_API_BASE_URL=http://localhost:8000
```

---

## API Endpoints

### Search Papers

POST /api/search

Request

```json
{
  "query": "Federated Learning for Healthcare"
}
```

### Search History

GET /api/search-history

### Paper Details

GET /api/papers/{id}

---

## Future Extension Points

The following interfaces are intentionally reserved for future contributors:

### PDF Retrieval

```python
class PdfRetrievalContract
```

Responsible for downloading and caching paper PDFs.

### RAG Indexing

```python
class RagIndexingContract
```

Responsible for embedding generation and vector indexing.

### Bibliography Generation

```python
class BibliographyGenerationContract
```

Responsible for generating formatted citations and references.

These contracts allow future modules to be added without modifying existing search functionality.

---

## Roadmap

### Phase 1 (Current)

* Keyword expansion
* OpenAlex integration
* arXiv integration
* Search history
* Frontend UI

### Phase 2

* Embeddings
* Semantic reranking
* Vector database
* RAG
* PDF chunking
* Research summaries

### Phase 3

* Citation graphs
* Bibliography generation
---

## License

MIT License
