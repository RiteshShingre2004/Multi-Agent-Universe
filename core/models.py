from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
import uuid

class TaskStatus(str, Enum):
    CREATED = "created"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class Task(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    description: str
    assigned_role: str
    status: TaskStatus = TaskStatus.CREATED
    input_data: Dict[str, Any] = {}
    output: Optional[str] = None
    parent_task_id: Optional[str] = None
    delegated_by: Optional[str] = None # Name of the agent who delegated this

class AgentConfig(BaseModel):
    name: str
    role: str
    goal: str
    backstory: str
    llm_provider: str = "gemini" # or "ollama"
    model_name: Optional[str] = None

class DelegationRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    sub_task_description: str
    target_role: str
    context: Dict[str, Any] = {}

class AgentOutput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    thought: str = Field(description="Your step-by-step reasoning")
    action: str = Field(description="Either 'FINAL_ANSWER' or 'DELEGATE'")
    delegation: Optional[DelegationRequest] = None
    answer: Optional[Any] = None
