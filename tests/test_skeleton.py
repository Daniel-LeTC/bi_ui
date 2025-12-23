import pytest
from core.context import UserContext
from core.engine import DataEngine

@pytest.fixture
def mock_db_path(tmp_path):
    d = tmp_path / "data"
    d.mkdir()
    p = d / "test.parquet"
    import pandas as pd
    df = pd.DataFrame({
        "Brand": ["Brand_A", "Brand_B", "Brand_A"],
        "Revenue": [100, 200, 300]
    })
    df.to_parquet(p)
    return str(p)

def test_security_context_logic():
    ctx = UserContext(user_id="u1", role="sales", allowed_brands=["Brand_A"])
    assert ctx.can_view_brand("Brand_A") == True
    assert ctx.can_view_brand("Brand_B") == False

def test_shadow_view_isolation(mock_db_path):
    engine = DataEngine(mock_db_path)
    ctx = UserContext(user_id="u1", role="sales", allowed_brands=["Brand_A"])
    df = engine.execute_query("SELECT * FROM secure_sales", ctx)
    assert len(df) == 2 
    assert "Brand_B" not in df["Brand"].to_list()

def test_sql_injection_guard(mock_db_path):
    engine = DataEngine(mock_db_path)
    ctx = UserContext(user_id="admin", role="admin", allowed_brands=["ALL"])
    with pytest.raises(ValueError, match="Forbidden"):
        engine.execute_query("DROP TABLE secure_sales", ctx)

def test_knowledge_base_injection():
    from core.knowledge_base import BusinessKnowledgeBase
    kb = BusinessKnowledgeBase()
    context = kb.get_injectable_context()
    assert "Bleeding" in context