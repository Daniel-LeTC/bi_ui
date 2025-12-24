import pytest
import pandas as pd
import polars as pl
import os
from unittest.mock import MagicMock
from core.agent import PerformanceAgent
from core.engine import DataEngine
from core.ai import AIEngine
from core.context import UserContext

@pytest.fixture
def mocked_agent_setup(tmp_path):
    # 1. Setup Mock Data
    d = tmp_path / "data"
    d.mkdir()
    p = d / "sales.parquet"
    df = pd.DataFrame({
        "Date": pd.to_datetime(["2025-01-01", "2025-01-01", "2025-01-02"]),
        "Brand": ["Brand_A", "Brand_B", "Brand_A"],
        "Product Name": ["Mug A", "Shirt B", "Mug A"],
        "Revenue": [100.0, 50.0, 150.0],
        "Ads Spend": [20.0, 10.0, 30.0],
        "Units Sold": [5, 2, 7]
    })
    df.to_parquet(p)
    
    # 2. Setup DataEngine
    data_engine = DataEngine(str(p), brand_col="Brand")
    
    # 3. Setup Mocked AIEngine
    mock_ai = MagicMock(spec=AIEngine)
    
    return PerformanceAgent(data_engine, mock_ai), mock_ai

def test_full_flow_revenue_query(mocked_agent_setup):
    agent, mock_ai = mocked_agent_setup
    ctx = UserContext(user_id="u1", role="sales", allowed_brands=["Brand_A"])
    
    # Setup AI Mock response
    mock_ai.generate_sql.return_value = {
        "sql": "SELECT SUM(Revenue) FROM secure_sales WHERE Brand = 'Brand_A'",
        "explanation": "Mocked success"
    }
    
    question = "Tổng doanh thu của Brand_A?"
    result = agent.process_request(question, ctx)
    
    assert result["status"] == "success"
    df = result["data"]
    assert df.item(0, 0) == 250.0

def test_full_flow_permission_block(mocked_agent_setup):
    agent, mock_ai = mocked_agent_setup
    ctx = UserContext(user_id="u1", role="sales", allowed_brands=["Brand_A"])
    
    # AI có thể gen SQL đúng nhưng DataEngine sẽ filter Brand_B ra vì context
    mock_ai.generate_sql.return_value = {
        "sql": "SELECT SUM(Revenue) FROM secure_sales WHERE Brand = 'Brand_B'",
        "explanation": "Mocked Brand B query"
    }
    
    question = "Doanh thu của Brand_B?"
    result = agent.process_request(question, ctx)
    
    assert result["status"] == "success"
    df = result["data"]
    # Kết quả phải là 0 hoặc NULL vì Brand_A không được xem Brand_B
    val = df.item(0, 0)
    assert val is None or val == 0
