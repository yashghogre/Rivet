from typing import Dict, Literal, Optional

from pydantic import BaseModel, Field


class Message(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class AgentState(BaseModel):
    url: str
    requirement: str
    doc_text: str = ""
    spec_json: Dict = Field(default_factory=dict)
    generated_code: str = ""
    status: Literal["idle", "ingested", "generating", "error"] = "idle"
    error: Optional[str] = None
    # msgs_exchanged: Optional[List[Message]] = None    # NOTE: Commenting it out for now
    # Will see if it is needed later
