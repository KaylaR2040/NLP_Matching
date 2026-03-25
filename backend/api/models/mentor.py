from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from datetime import datetime
from uuid import uuid4

class Mentor(BaseModel):
    """Mentor data model - mirrors the mentee form structure for matching"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    submitted_at: datetime = Field(default_factory=datetime.now)
    
    # Personal Information
    email: str
    firstName: str
    lastName: str
    pronouns: str
    
    # Academic / Professional
    educationLevel: str  # BS, ABM, MS, PhD, Alumni
    graduationSemester: Optional[str] = None
    graduationYear: Optional[str] = None
    degreePrograms: List[str]
    academicInterests: List[str]
    
    # Experience + Involvement
    previousMentorship: bool = False
    studentOrgs: List[str]
    experienceLevel: str
    currentRole: Optional[str] = None  # Student, Alumni, Faculty, Staff
    yearsExperience: Optional[int] = None
    
    # Career and Professional
    industriesOfInterest: List[str]
    aboutYourself: Optional[str] = None
    careerPath: Optional[str] = None
    
    # Mentoring capability
    helpTopics: List[str]  # Topics they can advise on
    maxMentees: int = Field(ge=1, le=5, default=2)
    availability: Optional[str] = None
    meetingPreference: Optional[str] = None  # Virtual, In-person, Both
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        if '@' not in v:
            raise ValueError('Invalid email address')
        return v
    
    def to_dict(self):
        """Convert to dictionary for storage"""
        data = self.model_dump()
        data['submitted_at'] = data['submitted_at'].isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data):
        """Create from dictionary"""
        if isinstance(data.get('submitted_at'), str):
            data['submitted_at'] = datetime.fromisoformat(data['submitted_at'])
        return cls(**data)
    
    def get_searchable_text(self):
        """Generate text for NLP embedding"""
        text_parts = [
            f"Name: {self.firstName} {self.lastName}",
            f"Pronouns: {self.pronouns}",
            f"Education Level: {self.educationLevel}",
            f"Degrees: {', '.join(self.degreePrograms)}",
            f"Academic Interests: {', '.join(self.academicInterests)}",
            f"Student Organizations: {', '.join(self.studentOrgs) if self.studentOrgs else 'None'}",
            f"Experience Level: {self.experienceLevel}",
            f"Industries: {', '.join(self.industriesOfInterest)}",
            f"Can help with: {', '.join(self.helpTopics)}",
        ]
        
        if self.graduationYear:
            text_parts.append(f"Graduated: {self.graduationSemester or ''} {self.graduationYear}")
        if self.careerPath:
            text_parts.append(f"Career path: {self.careerPath}")
        if self.aboutYourself:
            text_parts.append(f"About: {self.aboutYourself}")
            
        return " | ".join(text_parts)