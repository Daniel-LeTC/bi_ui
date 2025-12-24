import pytest
import sys
import os

# Add 'app' to python path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.ai import AIEngine

# Mock AIEngine to test _extract_json without needing API Key
class MockAIEngine(AIEngine):
    def __init__(self):
        # Bypass __init__ to avoid client setup
        pass

def test_parser_clean_json():
    engine = MockAIEngine()
    raw = '{"sql": "SELECT *", "explanation": "ok"}'
    res = engine._extract_json(raw)
    assert res["sql"] == "SELECT *"

def test_parser_markdown_block():
    engine = MockAIEngine()
    raw = """
    Here is the code:
    ```json
    {
        "sql": "SELECT 1",
        "explanation": "markdown"
    }
    ```
    """
    res = engine._extract_json(raw)
    assert res["sql"] == "SELECT 1"

def test_parser_messy_text():
    engine = MockAIEngine()
    raw = """
    Sure, I can help.
    {
        "sql": "SELECT 2",
        "explanation": "messy"
    }
    Hope this helps!
    """
    res = engine._extract_json(raw)
    assert res["sql"] == "SELECT 2"

def test_parser_nested_braces():
    # This is tricky for regex, usually greedy match works for outer object
    # but simple regex might fail if not careful.
    # Our simple regex r"\{.*\}" with DOTALL is greedy, so it should catch the last closing brace.
    engine = MockAIEngine()
    raw = """
    {
        "sql": "SELECT 3",
        "explanation": "nested {brackets} here"
    }
    """
    res = engine._extract_json(raw)
    assert res["explanation"] == "nested {brackets} here"

def test_parser_broken_json():
    engine = MockAIEngine()
    raw = "This is just text no json here"
    res = engine._extract_json(raw)
    assert res is None

def test_parser_partial_json_fail():
    engine = MockAIEngine()
    raw = "{ 'sql': ... incomplete"
    res = engine._extract_json(raw)
    # JSONDecodeError should be caught and return None
    assert res is None
