import os
from pathlib import Path

import google.generativeai as genai
import streamlit as st
from dotenv import load_dotenv

# Tìm .env ngay trong thư mục app/
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)


class GeminiSQLEngine:
    def __init__(self, api_key=None):
        # 1. Ưu tiên tham số truyền vào hoặc Biến môi trường (.env)
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        source = "Env/Arg"

        # Debug console (UNCOMMENTED NOW)
        print(f"DEBUG: Looking for .env at: {env_path}")
        print(f"DEBUG: .env exists? {env_path.exists()}")

        # 2. Fallback sang st.secrets
        if not self.api_key:
            try:
                if "GEMINI_API_KEY" in st.secrets:
                    self.api_key = st.secrets["GEMINI_API_KEY"]
                    source = "Streamlit Secrets"
            except Exception:
                pass

        if self.api_key:
            masked_key = (
                self.api_key[:5] + "..." + self.api_key[-5:]
                if len(self.api_key) > 10
                else "***"
            )
            print(f"DEBUG: API Key Loaded from {source}. Key: {masked_key}")
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel("gemini-2.5-flash")
        else:
            print("DEBUG: NO API KEY FOUND IN ENV OR SECRETS")
            self.model = None

    def generate_response(self, question, data_path, columns_info, chat_history=None):
        """
        Generates a JSON response (SQL or Chat Message) based on user question, schema, and HISTORY.
        """
        if not self.model:
            return {"action": "chat", "content": "API Key missing."}

        # Format History
        history_text = ""
        if chat_history:
            # Lấy 6 tin nhắn gần nhất để giữ context mà không tốn token
            recent_msgs = chat_history[-6:] 
            for msg in recent_msgs:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                history_text += f"- {role.upper()}: {content}\n"

        # 1. Construct the System Prompt (The "Brain")
        prompt = f"""
        You are an expert Data Analyst and DuckDB SQL Specialist.
        Your task is to analyze the user's question against the available database schema and decide the next best action.

        ### DATABASE CONTEXT:
        - Table: read_parquet('{data_path}')
        - Schema (Columns):
        {columns_info}

        ### CONVERSATION HISTORY (Use this to understand context like "Do it", "Yes", or follow-up questions):
        {history_text}

        ### DECISION LOGIC:
        1. **CHECK SCHEMA**: Does the user ask for columns that exist? (e.g. 'Profit' is NOT in schema -> You must explain that we only have Revenue and Spend).
        2. **CHECK AMBIGUITY**: Is the question clear? (e.g. "Best product" -> Ask "Best by Revenue, Units Sold, or ROAS?").
        3. **GENERATE SQL**: Only if the question is clear and columns exist.
        4. **CALCULATIONS**: If User accepts a proposal to calculate (e.g., Profit = Rev - Spend), GENERATE THE SQL.

        ### OUTPUT FORMAT (JSON ONLY):
        You must return a valid JSON object with two keys: "action" and "content".
        
        **Case 1: Ambiguous Question / Missing Data / General Chat**
        {{
            "action": "chat",
            "content": "Your explanation or clarification question here..."
        }}

        **Case 2: Valid SQL Query**
        {{
            "action": "sql",
            "content": "SELECT ... (DuckDB Syntax)"
        }}

        ### BUSINESS RULES:
        - "Bleeding" = Sales=0 AND Spend>30.
        - Always use double quotes for columns like "Revenue (Actual)".
        - LIMIT 20 for lists.

        ### USER QUESTION:
        "{question}"
        
        ### JSON RESPONSE:
        """

        try:
            response = self.model.generate_content(prompt)
            raw_text = response.text.strip()
            
            # Cleanup JSON (Gemini often wraps in ```json ... ```)
            clean_text = raw_text.replace("```json", "").replace("```", "").strip()
            
            import json
            result = json.loads(clean_text)
            return result
            
        except Exception as e:
            # Fallback if JSON fails
            return {"action": "chat", "content": f"System Error (JSON Parsing): {str(e)}. Raw: {raw_text[:50]}..."}
