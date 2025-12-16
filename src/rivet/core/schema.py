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

    status: Literal[
        "idle",
        "ingested",
        "sliced",
        "error",
        "success",
        "sdk_generated",
        "sdk_invalid",
        "sdk_valid",
        "tests_generated",
        "test_failed",
        "sdk_fixed",
        "tests_fixed",
    ] = "idle"
    error: Optional[str] = None
    error_analysis: Dict = Field(default_factory=dict)

    sdk_code: Optional[str] = ""
    test_code: Optional[str] = ""

    sdk_retry_count: int = 0
    test_retry_count: int = 0
