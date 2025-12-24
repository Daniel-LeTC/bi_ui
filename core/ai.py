import json
import os
import re
from google import genai
from google.genai import types
from .knowledge_base import BusinessKnowledgeBase

class AIEngine:
    def __init__(self, api_key: str):
        # New SDK syntax (2025 style)
        self.client = genai.Client(api_key=api_key)
        self.model_id = "gemini-2.5-flash"
        self.kb = BusinessKnowledgeBase()
    
    def _extract_json(self, text: str) -> dict:
        """
        Robust JSON Extractor: Finds the first valid JSON object in a string.
        Handles Markdown blocks, introductory text, and messy formatting.
        """
        try:
            # 1. Try direct parsing first (Fast path)
            clean_text = text.strip()
            if clean_text.startswith("```json"):
                clean_text = clean_text.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_text)
        except json.JSONDecodeError:
            pass

        # 2. Regex Search (Robust path)
        # re.DOTALL ensures '.' matches newlines
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            json_str = match.group(0)
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass
        
        # 3. Give up
        return None

    def _build_system_prompt(self, schema_info: str) -> str:
        business_context = self.kb.get_injectable_context()
        
        return f"""
        You are a DuckDB SQL Expert. Table: 'secure_sales'
        
        ### SCHEMA INFO:
        {schema_info}
        
        {business_context}
        
        ### RULES:
        1. Return JSON: {{'sql': 'SELECT...', 'explanation': '...'}}
        2. No Markdown.
        3. Use double quotes for column names with spaces.
        4. IF question is ambiguous, return {{'sql': null, 'explanation': 'Ask clarifying question...'}}
        5. **DUCKDB DATE RULES**:
           - Use `STRPTIME(col, '%Y-%m-%d')` to parse string dates. Do NOT use `TO_DATE`.
           - Use `DATE_TRUNC('month', date_col)` or `STRFTIME(date_col, '%Y-%m')` for month grouping.
           - Current Date: Use `CURRENT_DATE`.
           - **PERFORMANCE**: Use `QUALIFY` for filtering Window Functions (Rank/Row_Number) instead of subqueries/joins if possible.
           - Avoid self-joins for calculating growth if `LAG` window function suffices.
        """

    def generate_sql(self, question: str, schema_info: str, history: list = None):
        system_prompt = self._build_system_prompt(schema_info)

        # Build context
        chat_context = ""
        if history:
            for msg in history[-4:]:
                role = "User" if msg['role'] == "user" else "Assistant"
                chat_context += f"{role}: {msg['content']}\n"

        full_prompt = f"{system_prompt}\n\nHistory:\n{chat_context}\nUser: {question}\nJSON Response:"

        try:
            # New SDK call syntax with config
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    temperature=0.0
                )
            )
            
            raw_text = response.text
            result = self._extract_json(raw_text)
            
            if result:
                return result
            else:
                return {"sql": None, "explanation": "AI returned invalid format.", "raw": raw_text}

        except Exception as e:
            return {"sql": None, "explanation": f"AI Error: {str(e)}"}