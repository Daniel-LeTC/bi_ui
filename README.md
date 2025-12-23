# Performance Analysis Assistant (Headless BI Core)

This repository hosts the **Application Layer** of the Performance Analysis Assistant. It follows a **Headless BI** architecture, separating Core Logic from Presentation, enabling multiple interfaces (Streamlit, n8n, API) to consume the same secure data intelligence.

## 🏗 System Architecture

The system supports two modes of interaction: **Direct (Blackbox)** and **Orchestrated (Whitebox)**.

```mermaid
graph TD
    %% Actors
    User([User])
    n8n_Trigger([n8n Trigger])

    %% Components
    subgraph UI [Streamlit Interfaces]
        DevUI[02_Dev_Assistant.py<br>(Direct Mode)]
        ProdUI[03_n8n_Chat.py<br>(n8n Mode)]
    end

    subgraph API [FastAPI Server]
        QueryEP["POST /query<br>(Blackbox Wrapper)"]
        
        subgraph Whitebox [Micro-Endpoints]
            AuthEP["POST /auth/context"]
            SchemaEP["POST /agent/schema"]
            GenSQLEP["POST /agent/generate-sql"]
            ExecEP["POST /data/execute"]
        end
    end

    subgraph Core [Core Logic]
        Context[Context Manager]
        Engine[Data Engine]
        AI[AI Engine]
    end

    %% Flows
    User --> DevUI
    User --> ProdUI
    
    %% Flow 1: Blackbox (Simple)
    DevUI -->|Direct Call| QueryEP
    QueryEP --> Context & Engine & AI

    %% Flow 2: Whitebox (n8n Orchestration)
    ProdUI -->|Webhook| n8n_Trigger
    n8n_Trigger -->|1. Auth| AuthEP
    n8n_Trigger -->|2. Get Schema| SchemaEP
    n8n_Trigger -->|3. Gen SQL| GenSQLEP
    n8n_Trigger -->|4. Execute| ExecEP
    
    AuthEP --> Context
    SchemaEP --> Engine
    GenSQLEP --> AI
    ExecEP --> Engine

    %% Data
    Engine -->|Polars/DuckDB| Parquet[(Big Data Parquet)]
```

## 🧩 Module Status

| Module | Path | Status | Description |
| :--- | :--- | :--- | :--- |
| **Orchestrator** | `core/agent.py` | ✅ **DONE** | Connects User, AI, and Data Engine. Handles **Self-Correction** (Auto-Retry). |
| **Data Shield** | `core/engine.py` | ✅ **DONE** | **Shadow View** security, SQL Injection prevention (`sqlglot`), Dynamic Schema. |
| **The Brain** | `core/ai.py` | ✅ **DONE** | Integrated `google-genai` (Gemini 2.5 Flash), Token optimization. Temperature=0. |
| **API Bridge** | `api/server.py` | ✅ **DONE** | FastAPI server exposing both **Blackbox** (`/query`) and **Whitebox** endpoints. |
| **Identity** | `core/context.py` | ⚠️ *Mockup* | Implements Group Logic (Group AB, BC, AC) for testing permissions. |
| **Knowledge** | `core/knowledge_base.py` | ⚠️ *Mockup* | Business definitions (Bleeding, TACOS, etc.) - Needs verification. |

## 🚀 Performance Benchmark

Tested on **1,000,000 Rows** (Parquet) with complex analytical queries (Window Functions, Aggregations, Joins):

*   **Engine Execution Time:** ~0.5s (DuckDB + Polars Zero-Copy).
*   **AI SQL Generation:** ~10-20s (Gemini 2.5 Flash).
*   **Total End-to-End Latency:** ~22s (via n8n).

## 🔒 Security Features

1.  **Row-Level Security (Shadow View)**:
    *   Data is filtered dynamically via `CREATE VIEW secure_sales AS SELECT * FROM raw WHERE ...`.
    *   **Mock Logic:** Users are assigned groups (A-B, B-C) matching the first letter of the Niche.

2.  **SQL Guardrails**:
    *   Strictly Read-Only.
    *   Block destructive commands (`DROP`, `DELETE`) via AST parsing.
    *   Robust handling of SQL Injection attempts (Single Quote escaping).

## 🛠️ Quick Start

### 1. Setup Environment
```bash
cp .env.example .env
# Fill in GEMINI_API_KEY & N8N_WEBHOOK_URL
uv sync
```

### 2. Generate Dummy Big Data (Optional)
```bash
uv run python app/gen_big_data_v2.py
# Creates 1M rows in scrape_tool/exports/Big_Master_PPC_Data.parquet
```

### 3. Run Tests (TDD Verified)
```bash
uv run pytest app/tests/
```

### 4. Launch System
```bash
# Start API Server (Background) - Port 8001
uv run uvicorn app.api.server:app --port 8001 --reload

# Start UI
uv run streamlit run app/main.py
```
