# Text-to-SQL Agentic Pipeline

A production-grade, agentic **Natural Language to SQL (Text-to-SQL)** system built with **FastAPI**, **LangGraph**, **PostgreSQL**, and **RedisVL**.

The system features **Human-in-the-Loop (HITL) clarification**, **self-correcting SQL generation**, **PostgreSQL conversation state checkpointing**, and an advanced **Semantic Cache with structured filter guards** to prevent false cache hits across queries with differing numeric or temporal entities (e.g., 2025 vs 2026).

---

## 🌟 Key Features

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

---

## 🏗️ Architecture & Workflow

```mermaid
flowchart TD
    START([Start]) --> Clarification[Clarification Node]
    
    Clarification -->|Unclear / Missing Info| AskUser[Ask User Node<br/><i>LangGraph interrupt</i>]
    AskUser -->|User Clarification Received| Clarification
    
    Clarification -->|Clear or Max Retries Met| ExtractFilters[Extract Filters Node<br/><i>Structured Output</i>]
    
    ExtractFilters --> CheckCache{Check Cache Node<br/><i>RedisVL + Filter Guard</i>}
    
    CheckCache -->|Cache HIT| END([Return Cached Answer])
    
    CheckCache -->|Cache MISS| GenerateSQL[Generate SQL Node]
    
    GenerateSQL --> ValidateSyntax[Validate SQL Syntax<br/><i>EXPLAIN query</i>]
    
    ValidateSyntax -->|Invalid Syntax & Retries < 3| CorrectSyntax[Correct SQL Syntax Node]
    CorrectSyntax --> ValidateSyntax
    
    ValidateSyntax -->|Valid Syntax| ValidateSemantic[Validate SQL Semantic Node]
    
    ValidateSemantic --> ExecuteSQL[Execute SQL Node]
    ExecuteSQL --> GenerateAnswer[Generate Answer Node]
    
    GenerateAnswer --> CacheStore[Store in Semantic Cache<br/><i>with Filter Metadata</i>]
    CacheStore --> END
```

---

## 📁 Project Structure

```text
text-to-sql/
├── app/
│   ├── db/
│   │   └── database.py              # SQLAlchemy engine initialization
│   ├── nodes/
│   │   ├── ask_user_node.py          # HITL interrupt handler for user clarification
│   │   ├── check_cache_node.py      # Semantic cache lookup with filter matching
│   │   ├── clarification_node.py    # Assesses query clarity and formulates questions
│   │   ├── correct_sql_syntax_node.py # Self-correction node for malformed SQL
│   │   ├── extract_filters_node.py  # Structured extraction of years, entities, and canonical prompt
│   │   ├── generate_answer_node.py  # Formulates natural language response from DB records
│   │   ├── generate_sql_node.py     # SQL query generator
│   │   └── validate_sql_semantic_node.py # Validates logical and schema correctness
│   ├── prompts/
│   │   ├── clarification.py         # Clarity evaluation prompts
│   │   ├── correct_sql.py           # SQL syntax correction prompts
│   │   ├── generate_answer.py       # Answer formatting prompts
│   │   ├── generate_sql.py          # Text-to-SQL generation prompts
│   │   └── validate_sql.py          # Semantic evaluation prompts
│   ├── services/
│   │   ├── llm_service.py           # Groq / Ollama / Gemini model configs
│   │   ├── redis_service.py         # RedisVL SemanticCache setup, filter builder, lookup & store
│   │   └── schema_service.py        # SQLAlchemy schema reflection and formatting
│   ├── graph.py                     # LangGraph workflow compilation and Postgres checkpointing
│   ├── main.py                      # FastAPI application and endpoint definitions
│   ├── querying_db.py               # Database execution and syntax checking via EXPLAIN
│   ├── state.py                     # LangGraph shared Pydantic state definition
│   └── structured_ouput.py          # Pydantic schemas (ClarificationResult, QueryFilters, etc.)
├── .env                             # Environment configuration (not committed)
├── graph.png                        # Mermaid/graph visualization artifact
├── README.md                        # Project documentation
└── test.py                          # Verification test script for semantic cache & filter guard
```

---

## ⚙️ Tech Stack

- **Framework**: [FastAPI](https://fastapi.tiangolo.com/)
- **Orchestration**: [LangGraph](https://langchain-ai.github.io/langgraph/) & [LangChain Core](https://python.langchain.com/)
- **LLM Providers**: [Groq](https://groq.com/) (`openai/gpt-oss-120b`, `openai/gpt-oss-20b`), with Ollama and Google Gemini support
- **Semantic Caching & Vectors**: [RedisVL](https://redisvl.com/) with Redis and `nomic-embed-text` embeddings
- **Database & Persistence**: [PostgreSQL](https://www.postgresql.org/) via [SQLAlchemy](https://www.sqlalchemy.org/), `psycopg_pool`, and `PostgresSaver`
- **Data Validation**: [Pydantic v2](https://docs.pydantic.dev/)

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

Create a `.env` file in the project root:

```env
# Database connection strings
DATABASE_URL=postgresql://username:password@localhost:5432/your_database
DB_URI=postgresql://username:password@localhost:5432/your_database

# LLM Providers
GROQ_API_KEY=your_groq_api_key

# Optional: Ollama / Google GenAI keys if using alternative providers
# GEMINI_API_KEY=your_gemini_key
```

### 3. Installation

Activate your virtual environment and install dependencies:

```bash
# Windows
.\myenv\Scripts\activate

# Install required packages
pip install fastapi uvicorn langgraph langchain-core langchain-groq langchain-ollama redis redisvl sqlalchemy psycopg[pool] pydantic python-dotenv
```

### 4. Running the Application

Start the FastAPI server with Uvicorn:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The interactive OpenAPI docs will be accessible at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

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

---

## 🧪 Testing the Semantic Cache

To verify how the semantic cache handles queries with high vector similarity but differing values (such as dates/years), run [test.py](file:///r:/text-to-sql/test.py):

```bash
python test.py
```

### Expected Behavior

1. **Exact Query**:
   `"How many patients were admitted in 2025?"` (Year: 2025)
   → **HIT ✅** (Matching intent and matching year tag)
2. **Different Year**:
   `"How many patients were admitted in 2026?"` (Year: 2026)
   → **MISS ✅** (Vector similarity is high, but filter guard rejects due to year mismatch)
3. **Paraphrase with Same Year**:
   `"Total number of patient admissions during 2025?"` (Year: 2025)
   → **HIT ✅** (Semantically aligned and filter tags match)