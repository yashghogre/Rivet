from typing import Dict, Literal, Optional

from pydantic import BaseModel, Field


class Message(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class AgentState(BaseModel):
    url: str
    requirement: Optional[str] = None
    doc_text: str = ""
    spec_json: Dict = Field(default_factory=dict)
    status: Literal["idle", "ingested", "generating", "error"] = "idle"
    error: Optional[str] = None
    # msgs_exchanged: Optional[List[Message]] = None    # NOTE: Commenting it out for now, will see if it is needed later
    # generated_code: str = ""                          # NOTE: This will also be looked afterwards
