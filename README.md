# Text-to-SQL Agentic Pipeline

A production-grade, agentic **Natural Language to SQL (Text-to-SQL)** system built with **FastAPI**, **LangGraph**, **PostgreSQL**, and **RedisVL**, featuring a modern interactive frontend UI.

The system features a **four-layer security model** (input guardrails, SQL structural safety, and output guardrails), **Human-in-the-Loop (HITL) clarification**, **self-correcting SQL generation**, **PostgreSQL conversation state checkpointing**, and an advanced **Semantic Cache with structured filter guards** to prevent false cache hits across queries with differing numeric or temporal entities (e.g., 2025 vs 2026).

---

## 🌟 Key Features

- **Four-Layer Security Model**:
  - **Layer 1 — Regex Input Guard**: Detects and blocks prompt injection, jailbreaks, instruction overrides, system prompt leakage, delimiter injections, and destructive SQL patterns using categorised regex rules. Also routes greetings to a friendly response path.
  - **Layer 2 — ML Meta Guard**: A fine-tuned **DeBERTa-v3** model (`protectai/deberta-v3-base-prompt-injection-v2`) catches semantically sophisticated injection attempts that regex cannot cover.
  - **Layer 3 — SQL Structural Safety (sqlglot)**: Parses the LLM-generated SQL using `sqlglot` before any database contact. Enforces read-only access — only a single `SELECT` statement is permitted; any write, DDL, or administrative construct is rejected immediately.
  - **Layer 4 — Output Guardrail (Presidio + Detoxify)**: Scans every generated answer for PII (names, emails, phone numbers, Pakistan CNICs, employee IDs), secrets (API keys, tokens, database URLs), and toxic content before it reaches the client. Harmful answers are replaced with a safe redaction message.

- **Semantic Caching with Value Guards (RedisVL)**:
  - Vector similarity search using embedding models (e.g., `nomic-embed-text` via Ollama).
  - **Structured Filter Isolation**: Extracts query metadata (years, numbers, entities, date ranges) into a structured schema. Cache hits are only approved if vector similarity matches *and* all concrete filter dimensions align, eliminating false hits on value-differing queries.

- **Human-in-the-Loop (HITL) Clarification**:
  - Automatically assesses whether the user's inquiry is clear enough given the database schema and conversation history.
  - Pauses execution using LangGraph `interrupt()` to request targeted clarification from the user when inputs are ambiguous or underspecified.

- **Self-Correcting SQL Loop**:
  - Validates generated SQL syntax against the live database using `EXPLAIN`.
  - Automatically loops through an LLM syntax correction node on syntax failures (up to 3 retries).
  - Performs semantic verification prior to execution.

- **Persistent State & Resumability**:
  - Checkpointed using `PostgresSaver` with connection pooling, preserving conversational context, message history, and interrupted state across multi-turn sessions.

- **REST API via FastAPI**:
  - Clean API interface to submit questions and resume pending clarification prompts.

- **Minimalist Modern Frontend**:
  - Interactive web UI with real-time status, SQL syntax highlighting, HITL clarification cards, query history, and guardrail telemetry.

---

## 🏗️ Architecture & Workflow

```mermaid
flowchart TD
    START([Start]) --> InputGuard[Input Guard Node\nRegex: injection / jailbreak / SQL]

    InputGuard -->|Unsafe or Greeting| GenerateAnswer[Generate Answer Node]
    InputGuard -->|Safe| MetaGuard[Meta Guard Node\nDeBERTa-v3 ML classifier]

    MetaGuard -->|Injection Detected| GenerateAnswer
    MetaGuard -->|Safe| Clarification[Clarification Node]

    Clarification -->|Unclear / Missing Info| AskUser[Ask User Node\nLangGraph interrupt]
    AskUser -->|User Clarification Received| InputGuard

    Clarification -->|Clear or Max Retries Met| ExtractFilters[Extract Filters Node\nStructured Output]

    ExtractFilters --> CheckCache{Check Cache Node\nRedisVL + Filter Guard}

    CheckCache -->|Cache HIT| GenerateAnswer
    CheckCache -->|Cache MISS| GenerateSQL[Generate SQL Node]

    GenerateSQL --> SQLSafety[SQL Safety Node\nsqlglot structural check]

    SQLSafety -->|Unsafe SQL| GenerateAnswer
    SQLSafety -->|Safe SQL| ValidateSyntax[Validate SQL Syntax\nEXPLAIN query]

    ValidateSyntax -->|Invalid Syntax & Retries < 3| CorrectSyntax[Correct SQL Syntax Node]
    CorrectSyntax --> ValidateSyntax

    ValidateSyntax -->|Permission Denied| GenerateAnswer
    ValidateSyntax -->|Valid Syntax| ValidateSemantic[Validate SQL Semantic Node]

    ValidateSemantic --> ExecuteSQL[Execute SQL Node]
    ExecuteSQL --> GenerateAnswer

    GenerateAnswer --> OutputGuard[Output Guard Node\nPresidio PII + Detoxify]

    OutputGuard -->|Harmful Content| END([Return Redacted Response])
    OutputGuard -->|Safe| CacheStore[Store in Semantic Cache\nwith Filter Metadata]
    CacheStore --> END
```

---

## 📁 Project Structure

```text
text-to-sql/
├── backend/
│   ├── app/
│   │   ├── db/
│   │   │   └── database.py                  # SQLAlchemy engine — reads READONLY_DATABASE_URL
│   │   ├── guardrails/
│   │   │   ├── input_guard.py               # Regex-based injection / jailbreak / SQL attack detection
│   │   │   ├── meta_guard.py                # DeBERTa-v3 ML prompt-injection classifier
│   │   │   ├── sql_safety.py                # sqlglot read-only SQL structural validator
│   │   │   └── ouput_guardrail.py           # Presidio PII + secret + Detoxify toxicity output scanner
│   │   ├── nodes/
│   │   │   ├── input_guard_node.py          # LangGraph node wrapping input_guard
│   │   │   ├── meta_guard_node.py           # LangGraph node wrapping meta_guard
│   │   │   ├── ask_user_node.py             # HITL interrupt handler for user clarification
│   │   │   ├── clarification_node.py        # Assesses query clarity and formulates questions
│   │   │   ├── extract_filters_node.py      # Structured extraction of years, entities, and canonical prompt
│   │   │   ├── check_cache_node.py          # Semantic cache lookup with filter matching
│   │   │   ├── generate_sql_node.py         # SQL query generator
│   │   │   ├── sql_safety_node.py           # LangGraph node wrapping sql_safety (sqlglot)
│   │   │   ├── correct_sql_syntax_node.py   # Self-correction node for malformed SQL
│   │   │   ├── validate_sql_semantic_node.py # Validates logical and schema correctness
│   │   │   ├── generate_answer_node.py      # Formulates natural language response from DB records
│   │   │   └── output_guard_node.py         # LangGraph node wrapping ouput_guardrail
│   │   ├── prompts/
│   │   │   ├── clarification.py             # Clarity evaluation prompts
│   │   │   ├── correct_sql.py               # SQL syntax correction prompts
│   │   │   ├── generate_answer.py           # Answer formatting prompts
│   │   │   ├── generate_sql.py              # Text-to-SQL generation prompts
│   │   │   └── validate_sql.py              # Semantic evaluation prompts
│   │   ├── services/
│   │   │   ├── llm_service.py               # Groq / Ollama / Gemini model configs
│   │   │   ├── redis_service.py             # RedisVL SemanticCache setup, filter builder, lookup & store
│   │   │   └── schema_service.py            # SQLAlchemy schema reflection and formatting
│   │   ├── graph.py                         # LangGraph workflow compilation and Postgres checkpointing
│   │   ├── main.py                          # FastAPI application and endpoint definitions
│   │   ├── querying_db.py                   # Database execution and syntax checking via EXPLAIN
│   │   ├── state.py                         # LangGraph shared Pydantic state definition
│   │   └── structured_ouput.py              # Pydantic schemas (ClarificationResult, QueryFilters, etc.)
│   ├── tests/
│   │   └── test_main_resume.py              # Tests for clarification resume flow
│   ├── .env                                 # Environment configuration (not committed)
│   ├── .env.example                         # Environment configuration template
│   ├── .gitignore                           # Backend-specific gitignore
│   └── graph.png                            # LangGraph visualization artifact
├── frontend/
│   └── index.html                           # Modern dark UI for interacting with Text-to-SQL
├── .gitignore                               # Root-level gitignore
└── README.md                                # Central project documentation
```

---

## ⚙️ Tech Stack

| Category | Technologies |
|---|---|
| API Framework | [FastAPI](https://fastapi.tiangolo.com/) + Uvicorn |
| Agent Orchestration | [LangGraph](https://langchain-ai.github.io/langgraph/) & [LangChain Core](https://python.langchain.com/) |
| LLM Providers | [Groq](https://groq.com/) (`openai/gpt-oss-120b` primary, `openai/gpt-oss-20b` evaluator) · [Google Gemini](https://ai.google.dev/) (`gemini-2.5-flash`) · [Ollama](https://ollama.com/) (`qwen2.5-coder:7b`) — switchable in `llm_service.py` |
| Semantic Caching & Vectors | [RedisVL](https://redisvl.com/) with Redis Stack & `nomic-embed-text` embeddings |
| Database & Persistence | [PostgreSQL](https://www.postgresql.org/) via [SQLAlchemy](https://www.sqlalchemy.org/), `psycopg_pool`, `PostgresSaver` |
| Input Security | Regex rules + [DeBERTa-v3](https://huggingface.co/protectai/deberta-v3-base-prompt-injection-v2) (HuggingFace Transformers) |
| SQL Safety | [sqlglot](https://github.com/tobymao/sqlglot) — read-only structural enforcement |
| Output Security | [Presidio Analyzer](https://microsoft.github.io/presidio/) (PII) + [Detoxify](https://github.com/unitaryai/detoxify) (toxicity) |
| Data Validation | [Pydantic v2](https://docs.pydantic.dev/) |
| Frontend | Modern HTML5 / CSS3 / Vanilla JS (No build step required) |

---

## 🚀 Getting Started

### 1. Prerequisites

- Python 3.10+
- PostgreSQL instance running (with target database schema and permissions for checkpointing)
- Redis Stack instance running (supports vector search module)
- Ollama running locally with `nomic-embed-text` installed:
  ```bash
  ollama pull nomic-embed-text
  ```
- Groq API Key (or alternative LLM configuration)

### 2. Environment Configuration

Create a `.env` file in the `backend/` folder (or copy from `backend/.env.example`):

```env
# Used by PostgresSaver (LangGraph checkpointing) — needs read/write access
DB_URI=postgresql://username:password@localhost:5432/your_database

# Used by SQLAlchemy engine for query execution — use a read-only DB user
READONLY_DATABASE_URL=postgresql+psycopg://readonly_user:password@localhost:5432/your_database

# LLM Providers
GROQ_API_KEY=your_groq_api_key

# Optional: Google GenAI key if switching to Gemini
GOOGLE_API_KEY=your_google_api_key
```

### 3. Backend Installation & Startup

Activate your virtual environment and install dependencies:

```bash
# Navigate to backend
cd backend

# Windows
.\myenv\Scripts\activate

# Install required packages
pip install fastapi uvicorn langgraph langchain-core langchain-groq langchain-ollama \
    redis redisvl sqlalchemy psycopg[pool] pydantic python-dotenv \
    sqlglot presidio-analyzer presidio-anonymizer detoxify transformers

# Start the FastAPI server
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The interactive OpenAPI docs will be accessible at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

### 4. Running the Frontend

The frontend is a lightweight web interface with zero build dependencies:

- Open `frontend/index.html` directly in your web browser, or serve it via a simple static file server:
  ```bash
  # From project root
  python -m http.server 3000 --directory frontend
  ```
- Access the UI at [http://127.0.0.1:3000](http://127.0.0.1:3000).

---

## 📡 API Usage

### 1. Submit a Query

**`POST /query`**

```json
{
  "question": "How many patients were admitted in 2025?",
  "conversation_id": "conv-101"
}
```

#### Case A: Response Ready (or Cache Hit)
```json
"There were 150 patients admitted in 2025."
```

#### Case B: Clarification Required (Human-in-the-Loop)
```json
{
  "conversation_id": "conv-101",
  "requires_clarification": true,
  "clarification_question": "Do you want to count patients based on their visit dates or appointment dates?"
}
```

#### Case C: Harmful Output Detected
```json
"I couldn't provide this response because it may contain sensitive information."
```

### 2. Resume After Clarification

When `requires_clarification` is `true`, submit the clarification answer with the same `conversation_id`:

**`POST /query`**

```json
{
  "clarification_answer": "Count them using visit dates.",
  "conversation_id": "conv-101"
}
```

The graph resumes from the checkpointed interrupt, proceeds through filter extraction, cache evaluation, SQL execution, and returns the final answer.
