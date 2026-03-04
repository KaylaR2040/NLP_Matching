from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from datetime import datetime
from uuid import uuid4

class Mentee(BaseModel):
    """Mentee data model matching the Flutter MenteeFormData.toJson() output"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    submitted_at: datetime = Field(default_factory=datetime.now)
    
    # Personal Information (from Contact + Identity section)
    email: str
    firstName: str
    lastName: str
    pronouns: str
    
    # Education + Academic Status
    educationLevel: str  # BS, ABM, MS, PhD
    graduationSemester: str  # Spring, Summer, Fall
    graduationYear: str  # e.g., "2025"
    degreePrograms: List[str]  # Multi-select list
    academicInterests: List[str]  # Multi-select chips
    
    # Experience + Involvement
    previousMentorship: bool
    studentOrgs: List[str]  # Multi-select organizations
    experienceLevel: str
    
    # Career Interests
    industriesOfInterest: List[str]  # Multi-select chips
    aboutYourself: Optional[str] = None
    
    # Matching Priorities (1-4 Likert scale)
    matchByIndustry: float = 2.0
    matchByDegree: float = 2.0
    matchByClubs: float = 2.0
    matchByIdentity: float = 2.0
    matchByGradYears: float = 2.0
    
    # Mentoring Preferences
    helpTopics: List[str]  # Multi-select chips
    
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
        """Generate text for NLP embedding - used by the matcher"""
        text_parts = [
            f"Name: {self.firstName} {self.lastName}",
            f"Pronouns: {self.pronouns}",
            f"Education Level: {self.educationLevel}",
            f"Degree Programs: {', '.join(self.degreePrograms)}",
            f"Graduating: {self.graduationSemester} {self.graduationYear}",
            f"Academic Interests: {', '.join(self.academicInterests)}",
            f"Previous Mentorship: {'Yes' if self.previousMentorship else 'No'}",
            f"Student Organizations: {', '.join(self.studentOrgs) if self.studentOrgs else 'None'}",
            f"Experience Level: {self.experienceLevel}",
            f"Industries of Interest: {', '.join(self.industriesOfInterest)}",
            f"Help Topics: {', '.join(self.helpTopics)}",
        ]
        
        if self.aboutYourself:
            text_parts.append(f"About: {self.aboutYourself}")
            
        return " | ".join(text_parts)
    
    def get_priority_weights(self):
        """Return normalized priority weights for matching"""
        total = (self.matchByIndustry + self.matchByDegree + 
                self.matchByClubs + self.matchByIdentity + self.matchByGradYears)
        
        if total == 0:
            return {
                'industry': 0.2,
                'degree': 0.2,
                'clubs': 0.2,
                'identity': 0.2,
                'gradYears': 0.2,
            }
        
        return {
            'industry': self.matchByIndustry / total,
            'degree': self.matchByDegree / total,
            'clubs': self.matchByClubs / total,
            'identity': self.matchByIdentity / total,
            'gradYears': self.matchByGradYears / total,
        }