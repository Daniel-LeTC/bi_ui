import os
import polars as pl
from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel
from typing import Optional, List, Any, Dict
from dotenv import load_dotenv

# Import Core
from core.context import get_user_context, UserContext
from core.engine import DataEngine
from core.ai import AIEngine
from core.agent import PerformanceAgent

load_dotenv()

app = FastAPI(title="PPC Analysis AI API", version="1.1")

# --- INITIALIZATION ---
DATA_PATH = os.path.abspath("../scrape_tool/exports/Big_Master_PPC_Data.parquet")
if not os.path.exists(DATA_PATH):
    DATA_PATH = os.path.abspath("../scrape_tool/exports/Master_PPC_Data.parquet")

api_key = os.getenv("GEMINI_API_KEY")

# Engine & Agent Setup
data_engine = DataEngine(DATA_PATH, brand_col="Main niche")
ai_engine = AIEngine(api_key)
agent = PerformanceAgent(data_engine, ai_engine)

# Cache all niches for context mapping
ALL_NICHES = data_engine.get_all_brands()

# --- DTO MODELS (Request/Response) ---
class QueryRequest(BaseModel):
    question: str
    token: str
    history: Optional[List[dict]] = []

class QueryResponse(BaseModel):
    status: str
    message: str
    data: Optional[Any] = None
    sql: Optional[str] = None

# Models cho Whitebox Endpoints
class AuthRequest(BaseModel):
    token: str

class GenSQLRequest(BaseModel):
    question: str
    schema_info: str
    history: Optional[List[dict]] = []

class ExecuteSQLRequest(BaseModel):
    sql: str
    user_context: UserContext # FastAPI sẽ tự parse JSON thành object UserContext

# --- 1. BLACKBOX ENDPOINT (Backward Compatibility) ---
@app.post("/query", response_model=QueryResponse)
async def query_agent(request: QueryRequest):
    """
    All-in-one endpoint: Auth -> AI -> Execute -> Result.
    Dùng cho: Quick Demo, Simple Apps.
    """
    try:
        user_ctx = get_user_context(request.token, ALL_NICHES)
        
        if user_ctx.role == "viewer" and not user_ctx.allowed_brands:
             raise HTTPException(status_code=401, detail="Invalid Token or No Permissions")

        result = agent.process_request(request.question, user_ctx, request.history)
        
        # Convert Polars to Dict
        if "data" in result and isinstance(result["data"], pl.DataFrame):
            result["data"] = result["data"].to_dicts()
            
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- 2. WHITEBOX ENDPOINTS (Granular Control) ---

@app.post("/auth/context", response_model=UserContext)
async def get_auth_context(req: AuthRequest):
    """
    Step 1: Exchange Token for UserContext (Role, Permissions).
    n8n Node: Authentication
    """
    ctx = get_user_context(req.token, ALL_NICHES)
    return ctx

@app.post("/agent/schema")
async def get_schema(user_context: UserContext):
    """
    Step 2: Get Secure Schema based on UserContext.
    n8n Node: Context Loader
    """
    try:
        # Note: DataEngine logic might need IO, usually fast but keep in mind
        schema = data_engine.get_schema_info(user_context)
        return {"schema": schema}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Schema Error: {str(e)}")

@app.post("/agent/generate-sql")
async def generate_sql(req: GenSQLRequest):
    """
    Step 3: Generate SQL from Question + Schema.
    n8n Node: AI Brain
    """
    try:
        response = ai_engine.generate_sql(req.question, req.schema_info, req.history)
        return response # {"sql": "...", "explanation": "..."}
    except Exception as e:
         raise HTTPException(status_code=500, detail=f"AI Error: {str(e)}")

@app.post("/data/execute")
async def execute_sql(req: ExecuteSQLRequest):
    """
    Step 4: Execute SQL with Guardrails & Shadow View.
    n8n Node: Data Execution
    """
    try:
        # DataEngine handles Security & Validation
        df = data_engine.execute_query(req.sql, req.user_context)
        
        return {
            "status": "success",
            "rows": len(df),
            "data": df.to_dicts() # Polars -> JSON
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Execution Error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    # Start on 8001
    uvicorn.run(app, host="0.0.0.0", port=8001)