import pytest
import pandas as pd
import polars as pl
import os
from dotenv import load_dotenv
from core.agent import PerformanceAgent
from core.engine import DataEngine
from core.ai import AIEngine
from core.context import UserContext

load_dotenv(dotenv_path=".env")

@pytest.fixture
def real_engine_setup(tmp_path):
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
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        pytest.skip("No API Key")
    data_engine = DataEngine(str(p), brand_col="Brand")
    ai_engine = AIEngine(api_key)
    return PerformanceAgent(data_engine, ai_engine)

def test_full_flow_revenue_query(real_engine_setup):
    agent = real_engine_setup
    ctx = UserContext(user_id="u1", role="sales", allowed_brands=["Brand_A"])
    question = "Tổng doanh thu của Brand_A là bao nhiêu?"
    result = agent.process_request(question, ctx)
    assert result["status"] == "success"
    df = result["data"]
    # AI có thể gen: SELECT SUM(Revenue) ...
    assert len(df) > 0
    # Polars access: df[0, 0] or df.item(0, 0)
    if "sum" in df.columns[0].lower() or "revenue" in df.columns[0].lower():
         val = df.item(0, 0)
         assert val == 250.0

def test_full_flow_permission_block(real_engine_setup):
    agent = real_engine_setup
    ctx = UserContext(user_id="u1", role="sales", allowed_brands=["Brand_A"])
    question = "Doanh thu của Brand_B thế nào?"
    result = agent.process_request(question, ctx)
    assert result["status"] == "success"
    df = result["data"]
    # DuckDB SUM() on empty set returns NULL (NaN in Pandas), rows=1.
    # Regular SELECT * returns rows=0.
    if len(df) == 0:
        assert True
    else:
        # Nếu có dòng, check xem giá trị có phải NaN/None không
        val = df.item(0, 0)
        # Polars: None check
        assert val is None or val == 0