"""Typed Pydantic schemas for multi-agent contracts and structural validation."""
from typing import Any, List, Optional
from pydantic import BaseModel, Field


class PlanSchema(BaseModel):
    approach: str = Field(default="", description="High-level technical strategy and assumptions")
    logic_contract: str = Field(default="", description="Programmatic contract for automated pytest verification")
    operational_contract: str = Field(default="", description="Human interaction model, CLI/GUI entrypoint design")
    files: List[str] = Field(default_factory=list, description="Target file paths to create or modify")
    steps: List[str] = Field(default_factory=list, description="Ordered implementation steps")


class ReviewerSchema(BaseModel):
    approved: bool = Field(description="True if both Gate 1 (tests) and Gate 2 (usability) pass")
    summary: str = Field(default="", description="Short verdict summary")
    feedback: str = Field(default="", description="Diagnostic feedback and root cause analysis")
    suggested_fixes: List[str] = Field(default_factory=list, description="Concrete fixes for Coder")
    user_explanation: str = Field(default="", description="Plain-English explanation with test/run instructions")


def validate_schema(data: dict, schema_cls: type[BaseModel]) -> tuple[dict, Optional[str]]:
    """Validate data against a Pydantic schema, tolerating minor field omissions with defaults.

    Returns:
        (validated_dict, error_message_if_fatal)
    """
    try:
        instance = schema_cls.model_validate(data)
        return instance.model_dump(), None
    except Exception as e:
        return data, str(e)

