import time
from typing import Dict, Any, Union
import polars as pl
from .engine import DataEngine
from .ai import AIEngine
from .context import UserContext

class PerformanceAgent:
    def __init__(self, data_engine: DataEngine, ai_engine: AIEngine):
        self.data_engine = data_engine
        self.ai_engine = ai_engine
    
    def process_request(self, question: str, user_context: UserContext, history: list = None, max_retries: int = 2) -> Dict[str, Any]:
        """
        Main Agent Loop with Self-Correction & Manual SQL Support.
        """
        # 1. Lấy Schema
        try:
            schema_info = self.data_engine.get_schema_info(user_context)
        except Exception as e:
            return {"status": "error", "message": f"Data Access Error: {str(e)}"}
        
        # --- LOGIC BYPASS AI (MANUAL SQL) ---
        clean_q = question.strip().upper()
        if clean_q.startswith("SELECT") or clean_q.startswith("WITH") or clean_q.startswith("DESCRIBE") or clean_q.startswith("SHOW"):
            sql = question
            explanation = "🚀 Manual SQL Execution Mode (AI Bypassed)"
            is_manual = True
        else:
            # Normal AI Flow
            ai_response = self.ai_engine.generate_sql(question, schema_info, history)
            sql = ai_response.get("sql")
            explanation = ai_response.get("explanation")
            is_manual = False
        
        if not sql:
            return {"status": "chat", "message": explanation}

        # Retry Loop (Only for AI mode, Manual mode fails immediately)
        last_error = None
        # Manual mode runs once, AI mode retries
        attempts = 1 if is_manual else (max_retries + 1)
        
        for attempt in range(attempts):
            try:
                # 4. Thực thi SQL & Đo Time
                start_time = time.time()
                
                # Returns Polars DataFrame
                df = self.data_engine.execute_query(sql, user_context)
                
                exec_time = time.time() - start_time
                
                # Success!
                msg = f"Found {len(df)} records in {exec_time:.4f}s." if not df.is_empty() else f"Query executed successfully in {exec_time:.4f}s but returned no data."
                
                return {
                    "status": "success",
                    "data": df,
                    "sql": sql,
                    "message": msg,
                    "exec_time": exec_time
                }
            
            except Exception as e:
                last_error = str(e)
                print(f"⚠️ SQL Execution Failed (Attempt {attempt+1}/{attempts}): {last_error}")
                
                if not is_manual and attempt < max_retries:
                    # Self-Correction: Ask AI to fix it
                    fix_prompt = f"""
                    The previous SQL query failed with this error: "{last_error}".
                    
                    Original Question: "{question}"
                    Failed SQL: {sql}
                    
                    Please CORRECT the SQL to fix the error. 
                    - Ensure you use valid DuckDB syntax.
                    - Do NOT use TO_DATE, use STRPTIME.
                    - Return ONLY JSON with the fixed 'sql'.
                    """
                    retry_response = self.ai_engine.generate_sql(fix_prompt, schema_info)
                    new_sql = retry_response.get("sql")
                    if new_sql:
                        sql = new_sql
                    else:
                        break
                else:
                    pass

        return {
            "status": "sql_error",
            "sql": sql,
            "message": f"SQL Execution Failed. Error: {last_error}",
            "original_explanation": explanation
        }
