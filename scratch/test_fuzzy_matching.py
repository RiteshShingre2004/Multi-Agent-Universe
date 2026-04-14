import sys
import os

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.agent import Agent, Orchestrator
from core.models import AgentConfig, Task, LLMProvider
from typing import Type
from pydantic import BaseModel

class MockProvider:
    def generate(self, prompt, system_instruction, response_model):
        return None # Not used for this logic test

def test_fuzzy_matching():
    orch = Orchestrator()
    
    # Register agents
    a1 = Agent(AgentConfig(name="Dr. Data", role="Lead Researcher", goal="Facts", backstory="..."), None)
    a2 = Agent(AgentConfig(name="Sarah", role="Chief Project Manager", goal="Coord", backstory="..."), None)
    
    orch.register_agent(a1)
    orch.register_agent(a2)
    
    # Test 1: Case-insensitivity
    match1 = orch._find_agent("lead researcher")
    print(f"Match 'lead researcher': {match1.config.name if match1 else 'None'}")
    assert match1 == a1
    
    # Test 2: Substring / Specialist
    match2 = orch._find_agent("Lead Researcher Specialist")
    print(f"Match 'Lead Researcher Specialist': {match2.config.name if match2 else 'None'}")
    assert match2 == a1
    
    # Test 3: Substring reverse
    match3 = orch._find_agent("Researcher")
    print(f"Match 'Researcher': {match3.config.name if match3 else 'None'}")
    assert match3 == a1
    
    # Test 4: Junk words stripping
    match4 = orch._find_agent("Lead Research Expert")
    # Our logic: 'Lead Research Expert' -> 'Lead Research' -> substring match for 'Lead Researcher'
    print(f"Match 'Lead Research Expert': {match4.config.name if match4 else 'None'}")
    assert match4 == a1
    
    # Test 5: Auto-assignment (No match)
    task = Task(description="Something weird", assigned_role="Ghost Writer")
    # This should auto-assign to the first agent (Lead Researcher in this case because of the order)
    # Actually Orchestrator.agents order depends on registration
    result = orch._process_task(task)
    print(f"Auto-assignment result role: {task.assigned_role} -> result? {result is not None}")
    
    print("All fuzzy matching tests passed!")

if __name__ == "__main__":
    test_fuzzy_matching()
