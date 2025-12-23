import json
import google.generativeai as genai
from .knowledge_base import BusinessKnowledgeBase

class AIEngine:
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-2.5-flash") # Use efficient model
        self.kb = BusinessKnowledgeBase() # Init Knowledge Base
    
    def _build_system_prompt(self, schema_info: str) -> str:
        """
        TODO: Build System Prompt tối ưu token.
        Logic:
        - Role: Data Analyst DuckDB Expert.
        - Context: Schema info + BUSINESS KNOWLEDGE.
        - Rule: JSON Output ONLY.
        """
        business_context = self.kb.get_injectable_context()
        
        return f"""
        You are a DuckDB SQL Expert working for an Amazon FBA Company (Teecom).
        
        ### SCHEMA INFO:
        Table: 'secure_sales'
        {schema_info}
        
        {business_context}
        
        ### RULES:
        1. Return JSON: {{'sql': 'SELECT...', 'explanation': '...'}}
        2. No Markdown.
        3. Use double quotes for column names with spaces.
        4. IF question is ambiguous, return {{'sql': null, 'explanation': 'Ask clarifying question...'}}
        """

    def generate_sql(self, question: str, schema_info: str, history: list = None):
        """
        Main function to turn text -> SQL.

        TODO:
        1. Build Prompt (System + History + Question).
        2. Call Gemini.
        3. Parse JSON.
        4. (Optional) Retry Logic if JSON broken.
        """
        system_prompt = self._build_system_prompt(schema_info)

        # Simple history formatting
        chat_context = ""
        if history:
            for msg in history[-4:]:
                chat_context += f"{msg['role'].upper()}: {msg['content']}\n"

        full_prompt = f"{system_prompt}\n\nHistory:\n{chat_context}\nUser: {question}\nJSON Response:"

        try:
            response = self.model.generate_content(full_prompt)
            clean_text = response.text.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_text)
        except Exception as e:
            return {{"sql": None, "explanation": f"AI Error: {str(e)}"}}
