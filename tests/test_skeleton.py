import pytest
from core.context import UserContext
from core.engine import DataEngine
# from core.ai import AIEngine (Mock this)

# TODO: Fixture setup (Mock DB Path)
@pytest.fixture
def mock_db_path(tmp_path):
    d = tmp_path / "data"
    d.mkdir()
    p = d / "test.parquet"
    # Create dummy parquet
    import pandas as pd
    df = pd.DataFrame({
        "Brand": ["Sandjest", "Coquella", "Sandjest"],
        "Revenue": [100, 200, 300]
    })
    df.to_parquet(p)
    return str(p)

def test_security_context_logic():
    """
    Test logic phân quyền context.
    Happy Path: User có quyền -> True
    Edge Case: User 'ALL' -> True
    """
    ctx = UserContext(user_id="u1", role="sales", allowed_brands=["Sandjest"])
    assert ctx.can_view_brand("Sandjest") == True
    assert ctx.can_view_brand("Coquella") == False

def test_shadow_view_isolation(mock_db_path):
    """
    Test quan trọng nhất: Shadow View.
    Expectation: User chỉ thấy data của Brand mình được cấp quyền.
    """
    engine = DataEngine(mock_db_path)
    ctx = UserContext(user_id="u1", role="sales", allowed_brands=["Sandjest"])
    
    # Run query
    df = engine.execute_query("SELECT * FROM secure_sales", ctx)
    
    # Assert
    assert len(df) == 2 # 2 dòng Sandjest
    assert "Coquella" not in df["Brand"].values

def test_sql_injection_guard(mock_db_path):
    """
    Test chặn SQL bẩn.
    """
    engine = DataEngine(mock_db_path)
    ctx = UserContext(user_id="admin", role="admin", allowed_brands=["ALL"])
    
    with pytest.raises(ValueError, match="Forbidden"):
        engine.execute_query("DROP TABLE secure_sales", ctx)

def test_knowledge_base_injection():
    """
    Test xem Knowledge Base có trả về string chứa key words quan trọng không.
    """
    from core.knowledge_base import BusinessKnowledgeBase
    kb = BusinessKnowledgeBase()
    context = kb.get_injectable_context()
    
    assert "Bleeding" in context
    assert "Phase 1" in context
    assert "ROAS" in context
