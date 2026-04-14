import sys
import os

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.agent import Agent
from core.models import AgentConfig
from core.llm_provider import GeminiProvider # Mock or existing

def test_sanitization():
    agent = Agent(
        config=AgentConfig(name="Test", role="Tester", goal="Test", backstory="Test"),
        provider=None # Not needed for sanitization test
    )
    
    dirty_data = {
        "database_lists": {"ScienceDirect", "PubMed"}, # Set
        "nested": {
            "more_sets": {"val1", "val2"},
            "list": [{"set_in_list"}]
        }
    }
    
    clean_data = agent._sanitize_data(dirty_data)
    print("Cleaned Data:", clean_data)
    
    # Assertions
    assert isinstance(clean_data["database_lists"], list)
    assert "ScienceDirect" in clean_data["database_lists"]
    assert isinstance(clean_data["nested"]["more_sets"], list)
    assert isinstance(clean_data["nested"]["list"][0], list)
    print("Sanitization test passed!")

if __name__ == "__main__":
    test_sanitization()
