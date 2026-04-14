import sys
import os
import time

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.agent import Agent, Orchestrator
from core.models import AgentConfig, Task, AgentOutput

class MockProvider:
    def generate(self, prompt, system_instruction, response_model):
        # Always output a delegation to keep the loop going
        return AgentOutput(
            thought="Still thinking...",
            action="DELEGATE",
            delegation={
                "target_role": "Tester",
                "sub_task_description": "Keep looping",
                "context": {}
            }
        )

def test_infinite_loop_prevention():
    def dummy_callback(name, thought, action, step=None):
        print(f"Callback: {name} - Step {step}")

    orch = Orchestrator(step_callback=dummy_callback, max_iterations=5)
    
    # Mock Provider that never gives a final answer
    provider = MockProvider()
    agent = Agent(AgentConfig(name="Looper", role="Tester", goal="Test", backstory="Test"), provider)
    orch.register_agent(agent)
    
    print("Starting mission that should be capped at 5 steps...")
    start_time = time.time()
    result = orch.run_task("Loop forever please", initial_role="Tester")
    end_time = time.time()
    
    print(f"\nResult:\n{result}")
    print(f"\nTotal Time: {end_time - start_time:.2f} seconds")
    
    # Check if it stopped at step 5
    assert "suspended after 5 steps" in result
    print("\nLoop prevention test passed!")

if __name__ == "__main__":
    test_infinite_loop_prevention()
