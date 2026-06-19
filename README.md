# CloudRag

CloudRag is a document-grounded RAG application for enterprise-style question answering. Users can upload documents, ask questions against them, inspect source-backed answers, control document visibility, and review chat history with citations.

It is built as a full-stack capstone-style system rather than a single demo script: React frontend, FastAPI backend, PostgreSQL metadata store, ChromaDB vector retrieval, and Ollama-based local model inference.

## What It Does

- Upload PDF, DOCX, TXT, CSV, and LOG files
- Extract and chunk document text
- Embed and index chunks in ChromaDB
- Retrieve and rerank relevant chunks at question time
- Generate source-grounded answers with Ollama
- Return citations, page references, and source excerpts
- Persist documents, sessions, messages, and citations in PostgreSQL
- Support private vs shared documents
- Require login before using the app
- Open original uploaded files from the source panel
- Jump to cited PDF pages


### Public Repo Note

As this project is maintained as a public repository, it is not directly connected to the live AWS deployment. This repository is intended for code sharing, portfolio presentation, and documentation purposes only.

The live deployment pipeline is managed separately in a secured private environment, such as a private repository, private GitHub Actions workflow, or protected CI/CD configuration.

AWS deployment secrets, repository variables, and sensitive configuration values are intentionally not included in this public repository. To run your own deployment, you will need to set up your own AWS credentials, IAM permissions, and repository variables in your private environment.


High-level AWS steps:

1. build and push API image to ECR
2. build and push frontend image to ECR
3. store sensitive auth values in SSM Parameter Store
4. register backend and frontend ECS task definitions
5. deploy ECS services
6. route them through an ALB
7. keep PostgreSQL on RDS and uploads in S3


## Tech Stack

### Frontend
<img width="1911" height="1052" alt="image" src="https://github.com/user-attachments/assets/5ca92f2c-f313-4774-af53-aed0c1c564fe" />
<img width="1000" height="494" alt="image" src="https://github.com/user-attachments/assets/6707794e-9872-484b-ac70-d9c73b176756" />
- React
- Vite
- Lucide icons
- Nginx container for production frontend serving

### Backend

- Python 3.10
- FastAPI
- SQLAlchemy
- AsyncPG
- HTTPX

### AI / Retrieval

- Ollama
- `qwen2:1.5b`
- `sentence-transformers/all-MiniLM-L6-v2`
- `cross-encoder/ms-marco-MiniLM-L6-v2`
- ChromaDB
- BM25
- NLTK

### Data / Storage

- PostgreSQL
- local uploads volume in development
- S3 object storage in AWS

### Infrastructure

- Docker
- Docker Compose
- AWS ECS / Fargate
- AWS ALB
- AWS RDS PostgreSQL
- AWS S3
- AWS ECR
- AWS SSM Parameter Store

## Architecture

```text
Browser
  |
  v
React Frontend
  |
  v
FastAPI API
  |-------------------------> PostgreSQL
  |                            - users
  |                            - documents
  |                            - chat_sessions
  |                            - chat_messages
  |                            - message_citations
  |
  |-------------------------> ChromaDB
  |                            - chunk embeddings
  |                            - chunk metadata
  |
  |-------------------------> Ollama
  |                            - local LLM inference
  |
  \-------------------------> Local upload storage / S3 object storage
```

## Authentication

CloudRagAWS uses **login-based authentication**.

The auth flow is:

1. user logs in with email and password
2. backend returns a bearer token
3. frontend stores the token in local storage
4. protected API requests send `Authorization: Bearer <token>`

Relevant backend files:

- [services/rag_api/app/routers/auth.py](services/rag_api/app/routers/auth.py)
- [services/rag_api/app/services/auth_service.py](services/rag_api/app/services/auth_service.py)
- [services/rag_api/app/middleware/auth.py](services/rag_api/app/middleware/auth.py)
- [services/rag_api/app/auth_context.py](services/rag_api/app/auth_context.py)



## Main Components

### Frontend

- [frontend/src/App.jsx](frontend/src/App.jsx)
  app shell and authenticated workspace
- [frontend/src/components/LoginScreen.jsx](frontend/src/components/LoginScreen.jsx)
  login form
- [frontend/src/components/Sidebar.jsx](frontend/src/components/Sidebar.jsx)
  document list, visibility toggles, sessions, uploads
- [frontend/src/components/ChatPanel.jsx](frontend/src/components/ChatPanel.jsx)
  prompt input, ask flow, cancel flow
- [frontend/src/components/MessageBubble.jsx](frontend/src/components/MessageBubble.jsx)
  answer rendering and inline citation clicks
- [frontend/src/components/SourcesPanel.jsx](frontend/src/components/SourcesPanel.jsx)
  citation cards, excerpts, PDF open, page jump
- [frontend/src/api.js](frontend/src/api.js)
  frontend API client and token handling

### Backend

- [services/rag_api/app/main.py](services/rag_api/app/main.py)
  FastAPI entrypoint, health/readiness, warmup
- [services/rag_api/app/routers/upload.py](services/rag_api/app/routers/upload.py)
  upload, parse, index, local/S3 persistence
- [services/rag_api/app/routers/ask.py](services/rag_api/app/routers/ask.py)
  retrieval, reranking, prompt assembly, answer generation, citation construction
- [services/rag_api/app/routers/documents.py](services/rag_api/app/routers/documents.py)
  documents, sessions, file serving, visibility updates
- [services/rag_api/app/services/rag_service.py](services/rag_api/app/services/rag_service.py)
  chunking, embeddings, hybrid retrieval, reranking
- [services/rag_api/app/services/file_parser.py](services/rag_api/app/services/file_parser.py)
  PDF, DOCX, and text parsing
- [services/rag_api/app/services/prompt_templates.py](services/rag_api/app/services/prompt_templates.py)
  prompt routing for direct QA, comparisons, and team-ranking questions

## Functional Flow

### Upload Flow

1. user uploads a document
2. FastAPI validates type and size
3. text is parsed and cleaned
4. text is chunked
5. chunks are embedded and stored in ChromaDB
6. metadata is stored in PostgreSQL
7. original file is stored locally in development or uploaded to S3 in AWS

### Ask Flow

1. user asks a question
2. backend creates one or more retrieval variants
3. ChromaDB retrieves candidate chunks
4. BM25 and cross-encoder reranking improve relevance
5. accessible chunks are filtered by ownership / visibility rules
6. prompt context is assembled
7. Ollama generates an answer from retrieved context
8. citations and source metadata are returned
9. frontend shows inline citations and source cards

## Local Development

## Prerequisites

- Docker Desktop
- Git
- enough RAM/CPU to run Ollama plus the rest of the stack

Optional if running pieces outside Docker:

- Python 3.10
- Node.js 20+

## Environment Configuration

Create a `.env` file in the project root. See [`.env.example`](.env.example).

Important variables include:

```env
ENV=development
DEBUG=True

AUTH_SECRET=replace_with_a_random_64_hex_key
AUTH_ADMIN_EMAIL=admin@cloudrag.local
AUTH_ADMIN_PASSWORD=ChangeMe123!
AUTH_ADMIN_NAME=CloudRAG Admin
AUTH_TOKEN_TTL_HOURS=12

OLLAMA_URL=http://ollama:11434/api/generate
OLLAMA_MODEL=qwen2:1.5b
OLLAMA_KEEP_ALIVE=45m
OLLAMA_NUM_THREAD=2
OLLAMA_NUM_CTX=3072

ASK_TOP_K=5
ASK_MAX_QUERY_VARIANTS=3
ASK_MAX_CONTEXT_WORDS=650
ASK_FACTUAL_NUM_PREDICT=120
ASK_ANALYTICAL_NUM_PREDICT=320
ASK_GROUND_CITATIONS=true

CHROMA_DIR=./chroma_db
VITE_API_BASE_URL=
VITE_API_PROXY_TARGET=http://localhost:8000
FRONTEND_API_BASE_URL=http://localhost:8000
```

## Run Locally

### Development mode

```cmd
cd /d C:\GitHub\cloudRagAWS
docker compose up -d --build
```

Frontend:

```text
http://localhost:5173
```

Backend API:

```text
http://localhost:8000
```

Swagger:

```text
http://localhost:8000/docs
```

Default local login:

- email: `admin@cloudrag.local`
- password: `ChangeMe123!`

Stop the stack:

```cmd
docker compose down
```

Rebuild after backend/frontend changes:

```cmd
docker compose up -d --build api frontend
```
```


## API Examples

Login:

```cmd
curl -X POST "http://localhost:8000/api/auth/login" -H "Content-Type: application/json" -d "{\"email\":\"admin@cloudrag.local\",\"password\":\"ChangeMe123!\"}"
```

## Core Endpoints

- `POST /api/auth/login`
- `GET /api/auth/me`
- `POST /api/auth/logout`
- `POST /api/upload`
- `GET /api/documents`
- `DELETE /api/documents/{doc_id}`
- `PATCH /api/documents/{doc_id}/visibility`
- `GET /api/documents/{doc_id}/file`
- `POST /api/ask/with-sources`
- `GET /api/sessions`
- `GET /api/sessions/{session_id}/messages`
- `DELETE /api/sessions/{session_id}`
- `GET /health`
- `GET /ready`

## AWS Deployment

It has already been deployed successfully on AWS in this project shape:

```text
Browser
  |
  v
Application Load Balancer
  |-----------------------> Frontend ECS service
  \-----------------------> Backend ECS service
                                 |
                                 |--> Ollama container
                                 |--> PostgreSQL on RDS
                                 |--> Chroma data volume
                                 \--> Uploaded files in S3
```

Deployment-related files:

- [task-definition.json](task-definition.json)
- [task-definition.frontend.json](task-definition.frontend.json)
- [frontend/Dockerfile](frontend/Dockerfile)
- [frontend/docker-entrypoint.sh](frontend/docker-entrypoint.sh)



### Frontend runtime config

The production frontend reads runtime settings from `/config.js`.

Current expected shape:

```js
window.__APP_CONFIG__ = {
  API_BASE_URL: "",
}
```


## Answer Quality Notes

CloudRagAWS supports more than plain extraction. The prompt router includes:

- direct QA
- document summaries
- evidence-based comparisons
- people/team ranking questions with explicit assumptions

That said, answer quality is still sensitive to:

- retrieved chunk quality
- prompt context size
- Ollama inference speed
- ambiguity in the user’s question


## Known Limitations

- Ollama inference on AWS is still CPU-sensitive
- answer quality for complex rankings and vague judgments can still vary
- exact PDF coordinate-level highlighting is not implemented
- this is authenticated and deployable, but not yet a full multi-role enterprise security platform

## Project Maturity

### Done

- full local stack
- login-based authentication
- private/shared document model
- PostgreSQL metadata persistence
- AWS ECS frontend/backend deployment
- AWS RDS integration
- S3-backed original file access
- source cards and page jumps


### Future Improvements

- stronger user and role management
- better rate limiting and abuse protection
- separate Ollama service for cleaner scaling
- improved observability and monitoring
- richer citation visualization

## Repository Structure

```text
cloudRagAWS/
├── db/
│   └── schema.sql
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   ├── api.js
│   │   └── App.jsx
│   ├── Dockerfile
│   └── nginx.conf
├── services/
│   └── rag_api/
│       └── app/
│           ├── middleware/
│           ├── routers/
│           ├── services/
│           ├── auth_context.py
│           ├── config.py
│           ├── db.py
│           └── main.py
├── docker-compose.yml
├── task-definition.json
├── task-definition.frontend.json
└── README.md
```

## Why This Project Matters

Many RAG demos stop at “upload a file and ask a question.” CloudRagAWS goes further by bringing in product and systems concerns:

- who can access which documents
- how answers are verified
- where citations come from
- how history is persisted
- how the system behaves in a real cloud deployment
