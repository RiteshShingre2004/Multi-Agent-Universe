import sys
import os
import time

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.agent import Agent, Orchestrator
from core.models import AgentConfig, Task, AgentOutput

class LoopProvider:
    def __init__(self):
        self.call_count = 0

    def generate(self, prompt, system_instruction, response_model):
        self.call_count += 1
        
        # If the system warns about a loop, give a final answer
        if "Loop detected" in prompt or "CRITICAL" in prompt:
            return AgentOutput(
                thought="System warned me about a loop. I must finish now.",
                action="FINAL_ANSWER",
                answer="Final report based on best judgment since looping is blocked."
            )
            
        # Otherwise, try to ping-pong back to 'Sarah' (who we assume is the manager)
        return AgentOutput(
            thought="I'm not sure, let me ask Sarah again.",
            action="DELEGATE",
            delegation={
                "target_role": "Sarah",
                "sub_task_description": "Clarify the production methods",
                "context": {}
            }
        )

def test_anti_ping_pong():
    orch = Orchestrator(max_iterations=5)
    
    provider = LoopProvider()
    sarah = Agent(AgentConfig(name="Sarah", role="Sarah", goal="Test", backstory="Test"), provider)
    dr_data = Agent(AgentConfig(name="Dr. Data", role="Dr. Data", goal="Test", backstory="Test"), provider)
    
    orch.register_agent(sarah)
    orch.register_agent(dr_data)
    
    print("Starting mission with a 'Ping-Pong' agent...")
    # Sarah delegates to Dr. Data
    task = Task(description="Research H2", assigned_role="Dr. Data", delegated_by="Sarah")
    
    result = orch._process_task(task)
    
    print(f"\nFinal Result:\n{result}")
    
    # Assertions
    # We expect the 'continue' logic in Orchestrator to have triggered
    # The agent should have received the warning and then given the FINAL_ANSWER
    assert "Final report" in result
    print("\nAnti-Ping-Pong detection test passed!")

if __name__ == "__main__":
    test_anti_ping_pong()
