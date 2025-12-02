from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class AgentState(BaseModel):
    url: str
    requirement: str
    doc_text: str = ""
    spec_json: Dict = Field(default_factory=dict)
    status: Literal["idle", "ingested", "generating", "error"] = "idle"
    error: Optional[str] = None
    msgs_exchanged: List[Message]
