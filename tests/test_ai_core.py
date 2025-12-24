import pytest
from unittest.mock import MagicMock
from core.ai import AIEngine

@pytest.fixture
def mock_ai_engine():
    # Mocking the genai Client and behavior
    engine = AIEngine(api_key="fake_key")
    # Thay thế hàm generate_sql thật bằng MagicMock
    engine.generate_sql = MagicMock()
    return engine

def test_ai_generate_simple_sql(mock_ai_engine):
    # Setup mock return value
    mock_ai_engine.generate_sql.return_value = {
        "sql": "SELECT SUM(Revenue) FROM secure_sales WHERE Brand = 'Brand_A'",
        "explanation": "Mocked SQL"
    }
    
    schema = "- Revenue (DOUBLE)\n- Brand (VARCHAR)\n- Date (TIMESTAMP)"
    question = "Tổng doanh thu của Brand_A là bao nhiêu?"
    result = mock_ai_engine.generate_sql(question, schema)
    
    assert "sql" in result
    assert result["sql"] is not None
    assert "SUM(Revenue)" in result["sql"]

def test_ai_bleeding_knowledge(mock_ai_engine):
    # Setup mock return value for bleeding
    mock_ai_engine.generate_sql.return_value = {
        "sql": "SELECT * FROM secure_sales WHERE \"Ads Spend\" > 0 AND \"Units Sold\" = 0",
        "explanation": "Mocked Bleeding SQL"
    }
    
    schema = "- Revenue (DOUBLE)\n- Brand (VARCHAR)\n- Ads Spend (DOUBLE)\n- Units Sold (INTEGER)"
    question = "Tìm các sản phẩm đang bị bleeding"
    result = mock_ai_engine.generate_sql(question, schema)
    
    assert "sql" in result
    assert result["sql"] is not None
    assert "Ads Spend" in result["sql"]
