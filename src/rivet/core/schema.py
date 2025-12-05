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
    status: Literal["idle", "ingested", "generated_code", "error"] = "idle"
    error: Optional[str] = None
    generated_code: Optional[str] = ""
    generated_test_code: Optional[str] = ""
    # msgs_exchanged: Optional[List[Message]] = None    # NOTE: Commenting it out for now, will see if it is needed later
