# QuerySentinel — Agentic Text-to-SQL Pipeline

A production-grade, agentic **Natural Language to SQL (Text-to-SQL)** system built with **FastAPI**, **LangGraph**, **PostgreSQL**, and **RedisVL**, featuring **QuerySentinel** — a sleek, interactive frontend interface.

QuerySentinel features a **four-layer security model** (regex guardrails, DeBERTa-v3 ML classifier, SQL structural safety via `sqlglot`, and Presidio + Detoxify output guardrails), **Human-in-the-Loop (HITL) clarification**, **dynamic schema reflection with real sample values**, **case-insensitive root-stem SQL generation**, **self-correcting SQL execution**, **PostgreSQL conversation state checkpointing**, and an advanced **Semantic Cache with structured filter guards** to eliminate false hits across differing numeric or temporal entities.

---

## 🌟 Key Features

- **Four-Layer Security Model**:
  - **Layer 1 — Regex Input Guard**: Detects and intercepts prompt injection, jailbreaks, instruction overrides, system prompt leakage, delimiter injections, and destructive SQL patterns using categorized regex rules. Also routes greetings directly to friendly conversational answers.
  - **Layer 2 — ML Meta Guard**: Employs a fine-tuned **DeBERTa-v3** transformer model (`protectai/deberta-v3-base-prompt-injection-v2`) to catch semantically subtle prompt injections that bypass rule-based filters.
  - **Layer 3 — SQL Structural Safety (sqlglot)**: Parses and inspects LLM-generated SQL queries using `sqlglot` prior to database execution. Strictly enforces read-only access — only single `SELECT` statements are permitted; write, DDL, and administrative queries are instantly blocked.
  - **Layer 4 — Output Guardrail (Presidio + Detoxify)**: Inspects generated answers for sensitive PII (names, emails, phone numbers, CNICs, employee IDs), secrets (tokens, API keys, database URLs), and toxic content. Harmful answers are automatically replaced with a safe redaction notice.

- **Dynamic Schema Reflection with Real Sample Grounding**:
  - Dynamically inspects the live PostgreSQL database schema via SQLAlchemy while filtering out internal LangGraph checkpoint tables.
  - Automatically queries and extracts distinct sample values (up to 6 per text column) directly from domain tables and injects them as schema comments (`-- sample values: ['...']`). This provides concrete schema linking anchors for the LLM without guessing column values.

- **Robust SQL Generation (Case-Insensitive & Stem Matching)**:
  - Enforces PostgreSQL case-insensitivity guidelines: prevents strict `=` comparisons on string/text columns (roles, statuses, titles, names, departments) that cause empty results.
  - Automatically matches singular/plural queries and variations to database root forms using `ILIKE '%stem%'` (e.g., a query for "pharmacists" reliably matches `'pharmacist'`, `'Pharmacist'`, and `'Chief Pharmacist'`).

- **Semantic Caching with Value Guards (RedisVL)**:
  - High-performance vector similarity search using embedding models (e.g., `nomic-embed-text` via Ollama).
  - **Structured Filter Isolation**: Extracts query dimensions (years, metrics, entities, date ranges) into a structured schema. Cache hits are only validated when vector similarity matches *and* all concrete filter dimensions align, eliminating false cache hits on queries differing only by numbers or years (e.g., 2025 vs 2026).

- **Human-in-the-Loop (HITL) Clarification**:
  - Assesses query clarity against the live database schema and conversational history.
  - Pauses graph execution with LangGraph's `interrupt()` when user queries are ambiguous or underspecified, prompting the user for targeted clarification and resuming seamlessly upon input.

- **Self-Correcting SQL Loop**:
  - Validates generated SQL syntax against the active database using PostgreSQL's `EXPLAIN`.
  - Automatically routes malformed queries to an LLM syntax correction node (up to 3 retries) with live error feedback before retrying.
  - Performs semantic validation prior to final query execution.

- **Persistent State & Resumability**:
  - Checkpointed using `PostgresSaver` with connection pooling, preserving conversational context, message history, and interrupted state across multi-turn sessions.

- **FastAPI Backend with CORS Middleware**:
  - Clean REST API interface with built-in `CORSMiddleware` enabling seamless cross-origin requests from frontend clients, local servers, or development origins.

- **QuerySentinel Web UI**:
  - Modern, responsive dark-mode interface built with Tailwind CSS, Lucide icons, and Chart.js.
  - Decoupled into modular `index.html`, `app.js`, and `style.css` files (no heavy build toolchain required).
  - Features real-time backend health monitoring, multi-session management with `localStorage` persistence, copyable SQL syntax blocks, automated data charts, tabular views, and interactive HITL clarification cards.

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
    CheckCache -->|Cache MISS| GenerateSQL[Generate SQL Node\nILIKE Stem Matching]

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
│   │   │   └── ouput_guardrail.py           # Presidio PII + secret + Detoxify toxicity scanner
│   │   ├── nodes/
│   │   │   ├── input_guard_node.py          # LangGraph node wrapping input_guard
│   │   │   ├── meta_guard_node.py           # LangGraph node wrapping meta_guard
│   │   │   ├── ask_user_node.py             # HITL interrupt handler for user clarification
│   │   │   ├── clarification_node.py        # Assesses query clarity and formulates questions
│   │   │   ├── extract_filters_node.py      # Structured extraction of years, entities, and canonical prompt
│   │   │   ├── check_cache_node.py          # Semantic cache lookup with filter matching
│   │   │   ├── generate_sql_node.py         # SQL query generator (case-insensitive stem matching)
│   │   │   ├── sql_safety_node.py           # LangGraph node wrapping sql_safety (sqlglot)
│   │   │   ├── correct_sql_syntax_node.py   # Self-correction node for malformed SQL
│   │   │   ├── validate_sql_semantic_node.py # Validates logical and schema correctness
│   │   │   ├── generate_answer_node.py      # Formulates natural language response from DB records
│   │   │   └── output_guard_node.py         # LangGraph node wrapping ouput_guardrail
│   │   ├── prompts/
│   │   │   ├── clarification.py             # Clarity evaluation prompts
│   │   │   ├── correct_sql.py               # SQL syntax correction & ILIKE stem prompts
│   │   │   ├── generate_answer.py           # Answer formatting prompts
│   │   │   ├── generate_sql.py              # Text-to-SQL generation with ILIKE stem guidelines
│   │   │   └── validate_sql.py              # Semantic evaluation prompts
│   │   ├── services/
│   │   │   ├── llm_service.py               # Groq / Ollama / Gemini model configs
│   │   │   ├── redis_service.py             # RedisVL SemanticCache setup, filter builder, lookup & store
│   │   │   └── schema_service.py            # Dynamic schema reflection with sample values
│   │   ├── graph.py                         # LangGraph workflow compilation and Postgres checkpointing
│   │   ├── main.py                          # FastAPI app, CORSMiddleware, and endpoint definitions
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
│   ├── index.html                           # QuerySentinel web UI layout & markup
│   ├── app.js                               # Frontend logic: state, API calls, Chart.js & markdown rendering
│   └── style.css                            # UI styling, animations, glassmorphism & dark grid effects
├── .gitignore                               # Root-level gitignore
└── README.md                                # Central project documentation
```

---

## ⚙️ Tech Stack

| Category | Technologies |
|---|---|
| **API Framework** | [FastAPI](https://fastapi.tiangolo.com/) + Uvicorn with `CORSMiddleware` |
| **Agent Orchestration** | [LangGraph](https://langchain-ai.github.io/langgraph/) & [LangChain Core](https://python.langchain.com/) |
| **LLM Providers** | [Groq](https://groq.com/) (`openai/gpt-oss-120b` primary, `openai/gpt-oss-20b` evaluator) · [Google Gemini](https://ai.google.dev/) (`gemini-2.5-flash`) · [Ollama](https://ollama.com/) (`qwen2.5-coder:7b`) — switchable in `llm_service.py` |
| **Semantic Caching & Vectors** | [RedisVL](https://redisvl.com/) with Redis Stack & `nomic-embed-text` embeddings |
| **Database & Persistence** | [PostgreSQL](https://www.postgresql.org/) via [SQLAlchemy](https://www.sqlalchemy.org/), `psycopg_pool`, `PostgresSaver` |
| **Input Security** | Regex rules + [DeBERTa-v3](https://huggingface.co/protectai/deberta-v3-base-prompt-injection-v2) (HuggingFace Transformers) |
| **SQL Safety** | [sqlglot](https://github.com/tobymao/sqlglot) — read-only AST structural enforcement |
| **Output Security** | [Presidio Analyzer](https://microsoft.github.io/presidio/) (PII) + [Detoxify](https://github.com/unitaryai/detoxify) (toxicity) |
| **Data Validation** | [Pydantic v2](https://docs.pydantic.dev/) |
| **Frontend** | Modern HTML5, [Tailwind CSS](https://tailwindcss.com/), Modular JavaScript (ES6+), [Lucide Icons](https://lucide.dev/), [Chart.js](https://www.chartjs.org/) |

---

## 🚀 Getting Started

### 1. Prerequisites

- Python 3.10+
- PostgreSQL instance running (with target domain database and permissions for LangGraph checkpoint tables)
- Redis Stack instance running (supports the vector search module)
- Ollama running locally with `nomic-embed-text` installed:
  ```bash
  ollama pull nomic-embed-text
  ```
- Groq API Key (or alternative LLM API key / Ollama model)

### 2. Environment Configuration

Create a `.env` file in the `backend/` directory (or copy from `backend/.env.example`):

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

Activate your virtual environment and install the required dependencies:

```bash
# Navigate to the backend directory
cd backend

# On Windows
.\myenv\Scripts\activate

# On Linux / macOS
source myenv/bin/activate

# Install required packages
pip install fastapi uvicorn langgraph langchain-core langchain-groq langchain-ollama \
    redis redisvl sqlalchemy psycopg[pool] pydantic python-dotenv \
    sqlglot presidio-analyzer presidio-anonymizer detoxify transformers

# Start the FastAPI server
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The interactive OpenAPI documentation will be available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

### 4. Running the QuerySentinel Frontend

The frontend is a lightweight, zero-build client:

1. Serve the `frontend/` directory using any static file server:
   ```bash
   # From the project root
   python -m http.server 3000 --directory frontend
   ```
2. Open your browser and navigate to [http://127.0.0.1:3000](http://127.0.0.1:3000) (or open `frontend/index.html` directly).
3. The top navbar displays a **Live (8000)** status pill once connected to the running backend. If your backend runs on a different port or host, click the slider icon in the header to update the API endpoint.

---

## 🖥️ QuerySentinel Frontend Highlights

- **Conversational Chat & Starter Prompts**: Ask questions in plain English or select from pre-configured domain starter queries.
- **Tabular Data Presentation & Auto-Generated Charts**: Query results automatically render as clean tables, with automated bar, line, or doughnut charts generated via Chart.js for aggregated metrics.
- **Syntax-Highlighted SQL Cards**: View generated SQL queries with single-click copy-to-clipboard functionality.
- **Human-in-the-Loop Clarification**: When an ambiguous query triggers LangGraph's interrupt, an interactive clarification card appears with follow-up questions and direct response submission.
- **Session History**: Create, switch between, and persist multiple query sessions in browser `localStorage`.
- **API Settings & Demo Fallback**: Easily modify backend connection endpoints and toggle demo fallback mode for offline testing.

---

## 📡 API Usage

### 1. Health Check

**`GET /`**

```json
{
  "message": "Text-to-SQL API is running"
}
```

### 2. Submit a New Query

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

#### Case C: Harmful Content / PII Detected
```json
"I couldn't provide this response because it may contain sensitive information."
```

### 3. Resume After Clarification

When `requires_clarification` is `true`, submit the user's answer with the same `conversation_id`:

**`POST /query`**

```json
{
  "clarification_answer": "Count them using visit dates.",
  "conversation_id": "conv-101"
}
```

The pipeline resumes execution from the LangGraph checkpoint, runs filter extraction, checks cache, generates and executes SQL, and returns the final response.

