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
    required_spec: Dict = Field(default_factory=dict)
    status: Literal["idle", "ingested", "sliced", "generated_code", "error", "success"] = "idle"
    error: Optional[str] = None
    sdk_code: Optional[str] = ""
    test_code: Optional[str] = ""
