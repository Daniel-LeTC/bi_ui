import pytest
import pandas as pd
import polars as pl
import os
from core.engine import DataEngine
from core.context import UserContext

@pytest.fixture
def complex_data_path(tmp_path):
    d = tmp_path / "data"
    d.mkdir()
    p = d / "complex_sales.parquet"
    df = pd.DataFrame({
        "Date": pd.to_datetime(["2025-01-01", "2025-01-02", "2025-01-03", "2025-01-04"]),
        "Brand": ["Brand_A", "Brand_B", "Brand_A", "Brand_C"],
        "Product Name": ["Prod 1", "Prod 2", "Prod 3", None],
        "Revenue": [100.5, 200.0, 50.0, 0.0],
        "Clicks": [10, 20, 5, 0]
    })
    df.to_parquet(p)
    return str(p)

def test_engine_initialization_fail():
    engine = DataEngine("path/to/ghost/file.parquet")
    with pytest.raises(Exception):
        ctx = UserContext(user_id="test", role="admin", allowed_brands=["ALL"])
        engine.execute_query("SELECT 1", ctx)

def test_secure_view_multi_brand(complex_data_path):
    """Test user được quyền xem nhiều Brand một lúc."""
    engine = DataEngine(complex_data_path)
    # User được xem BrandA và BrandB, nhưng không được xem BrandC
    ctx = UserContext(user_id="u1", role="sales", allowed_brands=["Brand_A", "Brand_B"])
    
    df = engine.execute_query("SELECT DISTINCT Brand FROM secure_sales ORDER BY Brand", ctx)
    
    brands = df["Brand"].to_list()
    assert "Brand_A" in brands
    assert "Brand_B" in brands
    assert "Brand_C" not in brands
    assert len(brands) == 2

def test_aggregation_precision(complex_data_path):
    """Test tính toán số học có bị lệch số không (Floating point issues)."""
    engine = DataEngine(complex_data_path)
    ctx = UserContext(user_id="admin", role="admin", allowed_brands=["ALL"])
    
    # 100.5 + 200.0 + 50.0 + 0.0 = 350.5
    df = engine.execute_query("SELECT SUM(Revenue) as TotalRev FROM secure_sales", ctx)
    
    assert float(df["TotalRev"][0]) == 350.5

def test_schema_extraction_format(complex_data_path):
    engine = DataEngine(complex_data_path)
    ctx = UserContext(user_id="admin", role="admin", allowed_brands=["ALL"])
    schema_info = engine.get_schema_info(ctx)
    assert "- Revenue (DOUBLE)" in schema_info
    assert "- Brand (VARCHAR)" in schema_info

def test_brand_name_injection_and_quotes(complex_data_path):
    engine = DataEngine(complex_data_path)
    ctx_quote = UserContext(user_id="u2", role="sales", allowed_brands=["Brand's A"])
    df = engine.execute_query("SELECT * FROM secure_sales", ctx_quote)
    assert len(df) == 0
    # Kiểm tra xem table raw_sales có còn đó không (vẫn query được admin là ok)
    ctx_admin = UserContext(user_id="admin", role="admin", allowed_brands=["ALL"])
    df_check = engine.execute_query("SELECT COUNT(*) FROM secure_sales", ctx_admin)
    assert df_check.item(0, 0) == 4