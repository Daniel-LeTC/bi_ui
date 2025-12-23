import pytest
import os
from dotenv import load_dotenv
from core.ai import AIEngine

load_dotenv(dotenv_path=".env")

@pytest.fixture
def ai_engine():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        pytest.skip("GEMINI_API_KEY không tìm thấy trong .env")
    return AIEngine(api_key)

def test_ai_generate_simple_sql(ai_engine):
    schema = "- Revenue (DOUBLE)\n- Brand (VARCHAR)\n- Date (TIMESTAMP)"
    question = "Tổng doanh thu của Brand_A là bao nhiêu?"
    result = ai_engine.generate_sql(question, schema)
    assert "sql" in result
    assert result["sql"] is not None
    assert "Brand_A" in result["sql"]

def test_ai_bleeding_knowledge(ai_engine):
    schema = "- Revenue (DOUBLE)\n- Brand (VARCHAR)\n- Ads Spend (DOUBLE)\n- Units Sold (INTEGER)"
    question = "Tìm các sản phẩm đang bị bleeding"
    result = ai_engine.generate_sql(question, schema)
    assert result["sql"] is not None
    sql = result["sql"].upper()
    assert "0" in sql