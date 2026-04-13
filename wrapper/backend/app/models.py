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


class MentorRecord(BaseModel):
    mentor_id: str
    email: str = ""
    first_name: str = ""
    last_name: str = ""
    full_name: str = ""
    linkedin_url: str = ""
    profile_photo_url: str = ""
    current_company: str = ""
    current_job_title: str = ""
    current_location: str = ""
    current_city: str = ""
    current_state: str = ""
    degrees_text: str = ""
    industry_focus_area: str = ""
    professional_experience: str = ""
    about_yourself: str = ""
    students_interested: int = 0
    phone: str = ""
    preferred_contact_method: str = ""
    is_active: bool = True
    source_csv_path: str = ""
    source_timestamp: str = ""
    last_modified_at: str = ""
    last_modified_by: str = ""
    last_enriched_at: str = ""
    enrichment_status: str = ""
    extra_fields: Dict[str, Any] = Field(default_factory=dict)


class MentorCreateRequest(BaseModel):
    email: str = ""
    first_name: str = ""
    last_name: str = ""
    full_name: str = ""
    linkedin_url: str = ""
    profile_photo_url: str = ""
    current_company: str = ""
    current_job_title: str = ""
    current_location: str = ""
    current_city: str = ""
    current_state: str = ""
    degrees_text: str = ""
    industry_focus_area: str = ""
    professional_experience: str = ""
    about_yourself: str = ""
    students_interested: int = 0
    phone: str = ""
    preferred_contact_method: str = ""
    is_active: bool = True
    source_csv_path: str = ""
    source_timestamp: str = ""
    enrichment_status: str = ""
    extra_fields: Dict[str, Any] = Field(default_factory=dict)


class MentorUpdateRequest(BaseModel):
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    linkedin_url: Optional[str] = None
    profile_photo_url: Optional[str] = None
    current_company: Optional[str] = None
    current_job_title: Optional[str] = None
    current_location: Optional[str] = None
    current_city: Optional[str] = None
    current_state: Optional[str] = None
    degrees_text: Optional[str] = None
    industry_focus_area: Optional[str] = None
    professional_experience: Optional[str] = None
    about_yourself: Optional[str] = None
    students_interested: Optional[int] = None
    phone: Optional[str] = None
    preferred_contact_method: Optional[str] = None
    is_active: Optional[bool] = None
    source_csv_path: Optional[str] = None
    source_timestamp: Optional[str] = None
    last_enriched_at: Optional[str] = None
    enrichment_status: Optional[str] = None
    extra_fields: Optional[Dict[str, Any]] = None


class MentorsListResponse(BaseModel):
    items: List[MentorRecord] = Field(default_factory=list)
    total: int = 0


class MentorImportResponse(BaseModel):
    rows_read: int
    created: int
    updated: int
    unchanged: int
    skipped: int
    errors: int
    error_rows: List[Dict[str, Any]] = Field(default_factory=list)


class MentorSyncResponse(BaseModel):
    rows: int
    columns: List[str] = Field(default_factory=list)
    output_path: str
    backup_path: str = ""


class MentorEnrichmentResponse(BaseModel):
    mentor_id: str
    enrichment_status: str
    message: str
    updated_fields: List[str] = Field(default_factory=list)
    mentor: Optional[MentorRecord] = None


class MentorBulkDeleteRequest(BaseModel):
    mentor_ids: List[str] = Field(default_factory=list)


class MentorBulkDeleteResponse(BaseModel):
    requested: int
    deleted: int
    deleted_mentor_ids: List[str] = Field(default_factory=list)
    not_found_mentor_ids: List[str] = Field(default_factory=list)


class LinkedInEnrichmentConfigResponse(BaseModel):
    enabled: bool
    provider: str
    disabled_reason: str = ""
    min_interval_seconds: int = 0
