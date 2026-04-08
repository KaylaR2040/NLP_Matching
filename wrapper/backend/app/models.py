from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    token_type: str = "bearer"
    expires_in: int
    is_dev: bool
    username: str


class MeResponse(BaseModel):
    username: str
    is_dev: bool
    expires_at: int


class PairRule(BaseModel):
    mentee_id: str
    mentor_id: str


class RunMatchPayload(BaseModel):
    excluded_mentee_ids: List[str] = Field(default_factory=list)
    excluded_mentor_ids: List[str] = Field(default_factory=list)
    rejected_pairs: List[PairRule] = Field(default_factory=list)
    locked_pairs: List[PairRule] = Field(default_factory=list)
    global_weights: Dict[str, float] = Field(default_factory=dict)
    mentee_weight_overrides: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    top_n: int = 50


class ScriptRequest(BaseModel):
    script_path: Optional[str] = None


class SaveMajorsRequest(BaseModel):
    text: str


class DevFileSaveRequest(BaseModel):
    file_key: str
    text: str


class DevFileRequest(BaseModel):
    file_key: str


class ExportAssignmentsRequest(BaseModel):
    rows: List[Dict[str, Any]] = Field(default_factory=list)
    filename: str = "final_assignments.xlsx"
