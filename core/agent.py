from typing import Dict, Any, List, Optional
from .models import AgentConfig, Task, AgentOutput, TaskStatus, DelegationRequest
from .llm_provider import LLMProvider
import logging

logger = logging.getLogger("AgentVerse")

class Agent:
    def __init__(self, config: AgentConfig, provider: LLMProvider):
        self.config = config
        self.provider = provider

    def _sanitize_data(self, data: Any) -> Any:
        """Recursively convert sets to lists to ensure JSON compatibility."""
        if isinstance(data, dict):
            return {k: self._sanitize_data(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._sanitize_data(i) for i in data]
        elif isinstance(data, set):
            return [self._sanitize_data(i) for i in list(data)]
        return data

    def execute_task(self, task: Task, context: str = "", available_roles: List[str] = None, mission_log: List[str] = None) -> AgentOutput:
        logger.info(f"Agent {self.config.name} ({self.config.role}) is working on task: {task.description}")
        
        roles_hint = f"\nAvailable specialists you can delegate to: {', '.join(available_roles)}" if available_roles else ""
        
        shared_memory = "\n".join(mission_log[-5:]) if mission_log else "No previous steps yet."
        
        system_instruction = f"""
        Role: {self.config.role}
        Goal: {self.config.goal}
        Backstory: {self.config.backstory}
        {roles_hint}
        
        Instructions:
        1. EFFICIENCY: Complete the workflow in the fewest steps possible. Avoid redundant delegations.
        2. ACCURACY & POLISH: Summarize and polish the final information provided. Ensure it is professional and accurate.
        3. DECISIVENESS: If you have enough information from previous steps (shared memory), provide a 'FINAL_ANSWER' instead of delegating again.
        4. Always start with a 'thought' explaining your reasoning.
        5. Decide on an 'action': Either 'FINAL_ANSWER' (finish) or 'DELEGATE' (need more data).
        
        Recent Mission Progression (Shared Memory):
        {shared_memory}
        4. JSON COMPLIANCE (STRICT):
           - Your output MUST be a valid JSON object.
           - NEVER use Python-specific syntax like sets (e.g., {"val"}), single quotes for strings, or trailing commas.
           - All strings MUST use double quotes.
           - Lists MUST use square brackets [].
           - The 'context' field MUST be a flat dictionary of key-value pairs.

        Example of DELEGATION:
        {{
            "thought": "I need research on topic X. I will ask the Lead Researcher.",
            "action": "DELEGATE",
            "delegation": {{
                "target_role": "Lead Researcher",
                "sub_task_description": "Search for latest data on topic X",
                "context": {{"topic": "X", "existing_data": ["data1", "data2"]}}
            }}
        }}

        Example of FINAL ANSWER:
        {{
            "thought": "I have all the research. I can now provide the final report.",
            "action": "FINAL_ANSWER",
            "answer": "Here is the final technical report..."
        }}
        """
        
        sanitized_input = self._sanitize_data(task.input_data)
        
        prompt = f"""
        Current Task: {task.description}
        Input Data: {sanitized_input}
        Context from previous steps: {context}
        
        Think step-by-step: What is the next logical step to achieve the goal?
        """
        
        try:
            output = self.provider.generate(
                prompt=prompt,
                system_instruction=system_instruction,
                response_model=AgentOutput
            )
            return output
        except Exception as e:
            logger.error(f"Error in agent {self.config.name}: {e}")
            return AgentOutput(
                thought=f"I encountered an error: {e}",
                action="FINAL_ANSWER",
                answer=f"Error: {e}"
            )

class Orchestrator:
    def __init__(self, step_callback=None, max_iterations: int = 12):
        self.agents: Dict[str, Agent] = {} # role -> Agent
        self.tasks: List[Task] = []
        self.global_context: str = ""
        self.mission_log: List[str] = [] # Shared Memory: Records thoughts/actions
        self.step_callback = step_callback
        self.max_iterations = max_iterations
        self.current_iteration = 0

    def register_agent(self, agent: Agent):
        self.agents[agent.config.role] = agent
        logger.info(f"Registered agent: {agent.config.name} as {agent.config.role}")

    def run_task(self, task_description: str, initial_role: str) -> str:
        self.current_iteration = 0 # Reset counter for a fresh mission
        self.mission_log = [] # Clear shared memory
        root_task = Task(description=task_description, assigned_role=initial_role)
        self.tasks.append(root_task)
        
        return self._process_task(root_task)

    def _find_agent(self, role_name: str) -> Optional[Agent]:
        """Finds an agent by role using case-insensitive and fuzzy matching."""
        if not role_name:
            return None
            
        # 1. Exact match (case-insensitive)
        roles_map = {k.lower(): v for k, v in self.agents.items()}
        target = role_name.lower()
        
        if target in roles_map:
            return roles_map[target]
            
        # 2. Substring match (e.g. "Lead Researcher Specialist" matches "Lead Researcher")
        for role, agent in self.agents.items():
            if role.lower() in target or target in role.lower():
                logger.info(f"Fuzzy matched requested role '{role_name}' to registered role '{role}'")
                return agent
                
        # 3. Clean and match (strip 'specialist', 'expert', etc.)
        junk_words = ["specialist", "expert", "agent", "pro", "special"]
        cleaned_target = target
        for word in junk_words:
            cleaned_target = cleaned_target.replace(word, "").strip()
            
        if cleaned_target in roles_map:
            return roles_map[cleaned_target]
            
        return None

    def _process_task(self, task: Task) -> str:
        agent = self._find_agent(task.assigned_role)
        
        if not agent:
            # AUTO-ASSIGNMENT LOGIC: Fallback to the first available agent if no match
            if self.agents:
                fallback_role, agent = next(iter(self.agents.items()))
                logger.warning(f"No match for '{task.assigned_role}'. Auto-assigning to {fallback_role}.")
            else:
                error_msg = f"No agents registered in the system."
                task.status = TaskStatus.FAILED
                task.output = error_msg
                return error_msg

        task.status = TaskStatus.IN_PROGRESS
        available_roles = list(self.agents.keys())
        
        # Continuous Execution Loop
        while self.current_iteration < self.max_iterations:
            self.current_iteration += 1
            
            # Injection: Anti-Loop Warning
            local_context = self.global_context
            if task.delegated_by == agent.config.name:
                local_context += "\n\nCRITICAL: You are trying to delegate back to yourself. STOP and provide a final answer."
            elif task.delegated_by:
                 local_context += f"\n\nNOTE: You were assigned this by {task.delegated_by}. Solve it yourself; do not delegate back to them."

            # Adaptive throttle: TURBO cloud throttle (1s)
            is_cloud = "Ollama" not in str(type(agent.provider))
            if is_cloud:
                import time
                time.sleep(1) 
                
            output = agent.execute_task(task, context=local_context, available_roles=available_roles, mission_log=self.mission_log)
            
            # Record in shared memory
            self.mission_log.append(f"Turn {self.current_iteration}: {agent.config.name} ({agent.config.role}) thought: {output.thought} | Action: {output.action}")

            # Fire callback for UI
            if self.step_callback:
                self.step_callback(agent.config.name, output.thought, output.action, step=self.current_iteration)
            
            if output.action == "DELEGATE" and output.delegation:
                # ANTI-PING-PONG: Check if we are delegating back to the person who just asked us
                if output.delegation.target_role == task.delegated_by or output.delegation.target_role == task.assigned_role:
                    logger.warning(f"Detected potential loop: {task.assigned_role} tried to delegate back to {output.delegation.target_role}. Forcing internal thought.")
                    # We continue the loop but don't actually delegate yet, allowing the agent to 'think again' with the warning injected next turn
                    self.global_context += f"\n[System]: Loop detected. You cannot delegate back to {output.delegation.target_role}. Please solve the task yourself or pick a DIFFERENT specialist."
                    continue

                logger.info(f"Delegating from {task.assigned_role} to {output.delegation.target_role}")
                
                sub_task = Task(
                    description=output.delegation.sub_task_description,
                    assigned_role=output.delegation.target_role,
                    parent_task_id=task.id,
                    delegated_by=agent.config.name,
                    input_data=output.delegation.context
                )
                self.tasks.append(sub_task)
                
                # Execute sub-task
                sub_result = self._process_task(sub_task)
                
                # Update context with the result and loop again
                self.global_context += f"\n[Result from {output.delegation.target_role}]: {sub_result}"
                continue # Let the agent think again with the new information
            
            else:
                # FINAL_ANSWER
                if output.answer is None:
                    # Guard against empty answers
                    output.answer = f"Task completed, but no detailed answer was provided. Thought was: {output.thought}"
                
                # Ensure answer is a string (even if model returned a dict)
                if not isinstance(output.answer, str):
                    import json
                    output.answer = json.dumps(output.answer, indent=2)
                
                task.status = TaskStatus.COMPLETED
                task.output = output.answer
                self.global_context += f"\n[Final Answer from {task.assigned_role}]: {task.output}"
                return task.output

        # If loop exits due to max_iterations
        if self.current_iteration >= self.max_iterations:
            logger.warning(f"Max iterations ({self.max_iterations}) reached. Forcing final answer.")
            return f"The mission was suspended after {self.max_iterations} steps to prevent an infinite loop. Current context collected:\n{self.global_context}"
