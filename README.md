# QuerySentinel — Agentic Text-to-SQL Pipeline

A production-grade, agentic **Natural Language to SQL (Text-to-SQL)** system built with **FastAPI**, **LangGraph**, **PostgreSQL**, and **RedisVL**, featuring **QuerySentinel** — a sleek, developer-grade interactive web interface.

QuerySentinel incorporates **parallelized multi-agent guardrails** (concurrent regex filtering and DeBERTa-v3 ML classification), **parallelized triple SQL validation** (AST safety via `sqlglot`, PostgreSQL `EXPLAIN` engine verification, and LLM semantic intent evaluation), **dual-track self-correcting SQL execution** (syntax and semantic repair loops), **Human-in-the-Loop (HITL) clarification**, **dynamic schema reflection with real sample values**, **case-insensitive root-stem SQL generation**, **LangSmith observability & tracing**, **PostgreSQL conversation state checkpointing**, and an advanced **Semantic Cache with structured filter guards** to eliminate false hits across differing numeric or temporal entities.

---

## 🌟 Key Features

- **Parallelized Dual-Guard Input Security (Fan-out / Fan-in)**:
  - **Layer 1 — Regex Input Guard**: Concurrently inspects incoming questions for prompt injection, jailbreaks, instruction overrides, system prompt leakage, delimiter injections, and destructive SQL patterns. Also fast-tracks greetings to conversational responses.
  - **Layer 2 — ML Meta Guard**: Simultaneously evaluates inputs using a fine-tuned **DeBERTa-v3** transformer model (`protectai/deberta-v3-base-prompt-injection-v2`) to capture subtle semantic injections that evade regex rules.
  - **Combine Guards Node**: Synthesizes the parallel outputs of both guards before routing — blocking malicious inputs, delivering friendly greetings, or proceeding to clarification. Also validates resumed user clarifications on resume loops.

- **Parallelized Triple SQL Validation**:
  - Once SQL is generated, the pipeline executes three validation layers concurrently:
    1. **Structural AST Safety (`sqlglot`)**: Parses the query AST to enforce strict read-only compliance — only single `SELECT` statements are permitted. Destructive operations (INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, GRANT, REVOKE) and multi-statement queries are instantly rejected without touching the database.
    2. **Engine Syntax & Permissions (`EXPLAIN`)**: Tests the query directly against the live PostgreSQL database using `EXPLAIN` to catch syntax errors, missing columns, invalid data type operations, and database-level permission denials.
    3. **Semantic Intent Evaluation (`llm_eval`)**: Compares the generated SQL against the user's intent, domain schema, and clarification context to detect logic flaws (e.g., wrong tables, missing or improper JOINs, incorrect aggregations, or missing filters).
  - **Combine SQL Validations Node**: Unifies the three validation streams and intelligently routes to execution, syntax self-correction, semantic self-correction, or safe rejection.

- **Dual-Track Self-Correcting SQL Loops**:
  - **Syntax Self-Correction**: When PostgreSQL `EXPLAIN` detects syntax or schema errors, queries are routed to an LLM syntax repair node (up to 3 retries) with live database error diagnostics.
  - **Semantic Self-Correction**: When intent mismatches or logical discrepancies are discovered, queries are routed to a dedicated semantic repair node (up to 2 retries) with actionable error context.
  - **Automated Re-Validation**: Any corrected query immediately fans out again through the full parallel triple-validation suite before execution.

- **Multi-Vector Output Guardrail (PII, Secrets & Toxicity)**:
  - **Targeted PII Detection**: Regex scanning for sensitive identifiers, including Pakistani CNICs (`\d{5}-\d{7}-\d`), emails, phone numbers, and street addresses.
  - **Secret & Credential Scanning**: Intercepts leaked API keys (OpenAI, Anthropic), GitHub tokens, AWS access keys, Bearer tokens, and database connection strings.
  - **Deep-Learning Toxicity Scanning**: Leverages [Detoxify](https://github.com/unitaryai/detoxify) to evaluate toxicity, severe toxicity, threats, and identity attacks, replacing non-compliant responses with a safe redaction notice.

- **Dynamic Schema Reflection with Real Sample Grounding**:
  - Dynamically inspects the live PostgreSQL schema via SQLAlchemy, filtering out internal LangGraph checkpoint tables (`checkpoints`, `checkpoint_blobs`, `checkpoint_writes`).
  - Automatically queries and extracts distinct sample values (up to 6 per text column) directly from domain tables and injects them as schema comments (`-- sample values: ['...']`), giving the LLM concrete linking anchors.

- **Robust SQL Generation (Case-Insensitive & Stem Matching)**:
  - Enforces case-insensitivity guidelines to prevent strict `=` comparisons on string/text columns (roles, statuses, titles, names, departments) that cause empty results.
  - Matches singular/plural variations and compound roles to root database forms using `ILIKE '%stem%'` (e.g., a query for "pharmacists" reliably matches `'pharmacist'`, `'Pharmacist'`, and `'Chief Pharmacist'`).

- **Semantic Caching with Value Guards (RedisVL)**:
  - High-performance vector similarity search using embedding models (e.g., `nomic-embed-text` via Ollama).
  - **Structured Filter Isolation**: Extracts query dimensions (years, metrics, entities, date ranges) into a structured schema (`QueryFilters`). Cache hits require both vector similarity and exact alignment on all concrete dimensions, eliminating false hits on queries differing only by numbers or dates (e.g., 2025 vs 2026).
  - **Instant Cache Short-Circuiting**: On cache hit, the graph short-circuits directly to `END`, bypassing redundant LLM and database calls.

- **Human-in-the-Loop (HITL) Clarification**:
  - Assesses query clarity against the live database schema and conversation history.
  - Pauses graph execution with LangGraph's `interrupt()` when user queries are ambiguous or underspecified, prompting the user for targeted clarification and resuming seamlessly with `Command(resume=...)`.

- **Comprehensive Observability & Tracing (LangSmith)**:
  - Native integration with LangSmith for full lifecycle tracking, token metrics, step-by-step latency profiling, and graph run inspection under the `QuerySentinel` project.

- **Persistent State & Resumability**:
  - Checkpointed using `PostgresSaver` with connection pooling, preserving conversational context, message history, and interrupted state across multi-turn sessions.

- **FastAPI Backend with CORS Middleware**:
  - Clean REST API interface with built-in `CORSMiddleware` enabling seamless cross-origin requests from frontend clients, local servers, or development origins.

- **QuerySentinel Web UI**:
  - Developer-grade dark-mode interface built with Tailwind CSS and Lucide icons.
  - **Tabbed Result Viewers**: Seamlessly toggle between natural-language answers, syntax-highlighted SQL with one-click copy, and structured tabular data grids with CSV export.
  - **Session Management**: Multi-turn conversation threads stored in browser `localStorage` with search filtering, `Ctrl+K` shortcut, and collapsible sidebar (`Ctrl+\`).
  - **Real-Time Backend Health Monitoring**: Live connection indicator polling `GET /` to verify PostgreSQL backend readiness.

---

## 🏗️ Architecture & Workflow

```mermaid
flowchart TD
    START([Start]) --> InputGuard[Input Guard Node\nRegex: injection / jailbreak / greeting]
    START --> MetaGuard[Meta Guard Node\nDeBERTa-v3 ML classifier]

    InputGuard --> CombineGuards[Combine Guards Node\nFan-in validation synthesis]
    MetaGuard --> CombineGuards

    CombineGuards -->|Unsafe or Greeting| GenerateAnswer[Generate Answer Node]
    CombineGuards -->|Safe Query| Clarification[Clarification Node]

    Clarification -->|Unclear / Missing Info| AskUser[Ask User Node\nLangGraph interrupt]
    AskUser -->|User Clarification Received| InputGuard
    AskUser -->|User Clarification Received| MetaGuard

    Clarification -->|Clear or Max Retries Met| ExtractFilters[Extract Filters Node\nStructured Dimensions]

    ExtractFilters --> CheckCache{Check Cache Node\nRedisVL + Filter Guard}

    CheckCache -->|Cache HIT| END_CACHE([Return Cached Response])
    CheckCache -->|Cache MISS| GenerateSQL[Generate SQL Node\nILIKE Stem Matching]

    GenerateSQL --> SQLSafety[SQL Safety Node\nsqlglot AST Check]
    GenerateSQL --> ValidateSyntax[Validate SQL Syntax\nEXPLAIN Query]
    GenerateSQL --> ValidateSemantic[Validate SQL Semantic\nLLM Intent Evaluation]

    SQLSafety --> CombineValidations[Combine SQL Validations Node\nFan-in reconciliation]
    ValidateSyntax --> CombineValidations
    ValidateSemantic --> CombineValidations

    CombineValidations -->|AST Unsafe / Permission Denied| GenerateAnswer
    CombineValidations -->|Syntax Error & Retries < 3| CorrectSyntax[Correct SQL Syntax Node]
    CombineValidations -->|Semantic Error & Retries < 2| CorrectSemantic[Correct SQL Semantic Node]

    CorrectSyntax --> SQLSafety
    CorrectSyntax --> ValidateSyntax
    CorrectSyntax --> ValidateSemantic

    CorrectSemantic --> SQLSafety
    CorrectSemantic --> ValidateSyntax
    CorrectSemantic --> ValidateSemantic

    CombineValidations -->|All Valid| ExecuteSQL[Execute SQL Node]
    ExecuteSQL --> GenerateAnswer

    GenerateAnswer --> OutputGuard[Output Guard Node\nPII / CNIC + Secrets + Detoxify]

    OutputGuard -->|Harmful Content| END_REDACTED([Return Redacted Response])
    OutputGuard -->|Safe Response| CacheStore[Store in Semantic Cache\nwith Filter Metadata]
    CacheStore --> END_SUCCESS([Return Verified Response])
```

---

## 📁 Project Structure

```text
text-to-sql/
├── backend/
│   ├── app/
│   │   ├── db/
│   │   │   └── database.py                   # SQLAlchemy engine — reads READONLY_DATABASE_URL
│   │   ├── guardrails/
│   │   │   ├── input_guard.py                # Regex injection / jailbreak / greeting detector
│   │   │   ├── meta_guard.py                 # DeBERTa-v3 ML prompt-injection classifier
│   │   │   ├── sql_safety.py                 # sqlglot read-only AST structural validator
│   │   │   └── ouput_guardrail.py            # PII (CNIC/Email/Phone/Address) + secret + Detoxify scanner
│   │   ├── nodes/
│   │   │   ├── input_guard_node.py           # LangGraph node wrapping regex input_guard
│   │   │   ├── meta_guard_node.py            # LangGraph node wrapping DeBERTa meta_guard
│   │   │   ├── combine_guards_node.py        # Fan-in node merging parallel input guard evaluations
│   │   │   ├── ask_user_node.py              # HITL interrupt handler for user clarification
│   │   │   ├── clarification_node.py         # Assesses query clarity against schema and history
│   │   │   ├── extract_filters_node.py       # Structured extraction of dimensions & canonical prompt
│   │   │   ├── check_cache_node.py           # Semantic cache lookup with filter matching (hits route to END)
│   │   │   ├── generate_sql_node.py          # SQL query generator with ILIKE stem matching
│   │   │   ├── sql_safety_node.py            # AST structural safety node (sqlglot)
│   │   │   ├── correct_sql_syntax_node.py    # Self-correction node for malformed SQL syntax (up to 3 retries)
│   │   │   ├── correct_sql_semantic_node.py  # Self-correction node for semantic logic errors (up to 2 retries)
│   │   │   ├── validate_sql_semantic_node.py # Validates logical and schema correctness
│   │   │   ├── combine_sql_validations_node.py # Fan-in node merging parallel SQL validation checks
│   │   │   ├── generate_answer_node.py       # Formulates natural language response or safe rejection
│   │   │   └── output_guard_node.py          # Post-generation PII/toxicity/secret redaction node
│   │   ├── prompts/
│   │   │   ├── clarification.py              # Clarity evaluation prompts
│   │   │   ├── correct_sql.py                # SQL syntax correction prompts
│   │   │   ├── correct_sql_semantic.py       # SQL semantic error correction prompts
│   │   │   ├── generate_answer.py            # Answer formatting prompts
│   │   │   ├── generate_sql.py               # Text-to-SQL generation with ILIKE stem guidelines
│   │   │   └── validate_sql.py               # Semantic evaluation & permission check prompts
│   │   ├── services/
│   │   │   ├── llm_service.py                # Groq / Ollama / Gemini model configs
│   │   │   ├── redis_service.py              # RedisVL SemanticCache setup, filter builder, lookup & store
│   │   │   └── schema_service.py             # Dynamic schema reflection with sample values
│   │   ├── graph.py                          # LangGraph workflow compilation with parallel fan-out/fan-in & checkpointing
│   │   ├── main.py                           # FastAPI app, CORS, LangSmith tracing, and /query endpoint
│   │   ├── querying_db.py                    # Database execution and syntax checking via EXPLAIN
│   │   ├── state.py                          # Shared Pydantic state definition for parallel branches
│   │   └── structured_ouput.py               # Pydantic schemas (ClarificationResult, QueryFilters, etc.)
│   ├── tests/
│   │   └── test_main_resume.py               # Tests for clarification resume flow
│   ├── .env                                  # Environment configuration (not committed)
│   ├── .env.example                          # Environment configuration template with LangSmith tracing
│   ├── .gitignore                            # Backend gitignore
│   └── graph.png                             # Generated LangGraph workflow visualization
├── frontend/
│   ├── index.html                            # Query Sentinel SaaS UI with message threads & settings modal
│   ├── app.js                                # Frontend controller: state, API calls, tabbed panes, tables, CSV export
│   ├── config.js                             # Configurable API endpoint & health check interval
│   └── style.css                             # Minimalist dark theme with syntax highlighting & data tables
├── graph.png                                 # Root LangGraph workflow visualization
├── .gitignore                                # Root gitignore
└── README.md                                 # Central project documentation
```

---

## ⚙️ Tech Stack

| Category | Technologies |
|---|---|
| **API Framework** | [FastAPI](https://fastapi.tiangolo.com/) + Uvicorn with `CORSMiddleware` |
| **Agent Orchestration** | [LangGraph](https://langchain-ai.github.io/langgraph/) (StateGraph with Parallel Fan-Out / Fan-In) & [LangChain Core](https://python.langchain.com/) |
| **LLM Providers** | [Groq](https://groq.com/) (`openai/gpt-oss-120b` primary, `openai/gpt-oss-20b` evaluator) · [Google Gemini](https://ai.google.dev/) (`gemini-2.5-flash`) · [Ollama](https://ollama.com/) (`qwen2.5-coder:7b`) — switchable in `llm_service.py` |
| **Semantic Caching & Vectors** | [RedisVL](https://redisvl.com/) with Redis Stack & `nomic-embed-text` embeddings |
| **Database & Persistence** | [PostgreSQL](https://www.postgresql.org/) via [SQLAlchemy](https://www.sqlalchemy.org/), `psycopg_pool`, `PostgresSaver` |
| **Observability & Tracing** | [LangSmith](https://smith.langchain.com/) tracing & execution monitoring |
| **Input Security** | Regex rules + [DeBERTa-v3](https://huggingface.co/protectai/deberta-v3-base-prompt-injection-v2) (HuggingFace Transformers) |
| **SQL Safety** | [sqlglot](https://github.com/tobymao/sqlglot) (AST read-only structural enforcement) + PostgreSQL `EXPLAIN` |
| **Output Security** | Regex PII Scanner (CNIC, Email, Phone, Address) + Secret Detection + [Detoxify](https://github.com/unitaryai/detoxify) |
| **Data Validation** | [Pydantic v2](https://docs.pydantic.dev/) |
| **Frontend** | Modern HTML5, [Tailwind CSS](https://tailwindcss.com/), Modular JavaScript (ES6+), [Lucide Icons](https://lucide.dev/) |

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
- *(Optional)* LangSmith API Key for tracing and observability

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

# LangSmith Tracing & Observability
LANGSMITH_TRACING=true
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_API_KEY=your_langsmith_api_key
LANGSMITH_PROJECT=QuerySentinel
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
    sqlglot detoxify transformers torch

# Start the FastAPI server
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The interactive OpenAPI documentation will be available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

### 4. Running the QuerySentinel Frontend

The frontend is a lightweight, zero-build client:

1. Navigate to the `frontend/` directory:
   ```bash
   cd frontend
   ```
2. Start the HTTP server:
   ```bash
   python -m http.server 3000
   ```
3. Open your browser and navigate to [http://127.0.0.1:3000](http://127.0.0.1:3000).
4. The sidebar displays a **PostgreSQL Live** status pill once connected to the running backend. If your backend runs on a different port or host, click **Settings** to update the API endpoint.

---

## 🖥️ Query Sentinel Minimalist Frontend Highlights

- **Developer-Grade Minimalist UI**: Polished dark theme inspired by Linear and ChatGPT with deep charcoal tones, subtle borders, and restrained indigo accents.
- **Tabbed Query Inspection**: Clean separation across three distinct tabs per response:
  - 💬 **Answer**: rich natural-language response.
  - ⚡ **SQL**: syntax-highlighted SQL code blocks with one-click copy.
  - 📊 **Results**: structured data grid with column headers, row counts, and one-click CSV export.
- **Collapsible Sidebar & Session Persistence**: Manage multi-turn query threads stored in browser `localStorage` with fast title search filtering, `Ctrl+K` shortcut, and collapsible navigation (`Ctrl+\`).
- **Real-Time Backend Health Monitoring**: Live connection indicator polling `GET /` to verify PostgreSQL backend readiness with no mock data.
- **Human-in-the-Loop Clarification**: Dedicated disambiguation cards with inline continuation inputs and automatic resume via `clarification_answer`.
- **Configurable Environment**: Backend URL configurable via `config.js` or through the in-app Connection Settings modal with built-in connection testing.

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

The pipeline resumes execution from the LangGraph checkpoint, runs the clarified input through the parallel input guards, extracts filters, checks the semantic cache, generates and validates SQL in parallel, and returns the final response.
