from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from datetime import datetime
from uuid import uuid4

RANKING_TO_PRIORITY = {
    1: 0.0,
    2: 11.0,
    3: 44.0,
    4: 100.0,
}

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
    
    # Experience + Involvement
    previousMentorship: bool
    studentOrgs: List[str]  # Multi-select organizations
    experienceLevel: str
    
    # Career Interests
    industriesOfInterest: List[str]  # Multi-select chips
    aboutYourself: Optional[str] = None
    
    # Matching Priorities (1-4 Likert scale)
    matchByIndustry: float = Field(default=2.0, ge=1.0, le=4.0)
    matchByDegree: float = Field(default=2.0, ge=1.0, le=4.0)
    matchByClubs: float = Field(default=2.0, ge=1.0, le=4.0)
    matchByIdentity: float = Field(default=2.0, ge=1.0, le=4.0)
    matchByGradYears: float = Field(default=2.0, ge=1.0, le=4.0)
    
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
        """Return final 50/50 scoring weights for direct-match fields plus NLP."""
        priorities = {
            'industry': self._ranking_to_priority(self.matchByIndustry),
            'degree': self._ranking_to_priority(self.matchByDegree),
            'clubs': self._ranking_to_priority(self.matchByClubs),
            'identity': self._ranking_to_priority(self.matchByIdentity),
            'gradYears': self._ranking_to_priority(self.matchByGradYears),
        }
        total_priority = sum(priorities.values())

        if total_priority == 0:
            direct_weights = {key: 0.0 for key in priorities}
        else:
            direct_weights = {
                key: 0.5 * (value / total_priority)
                for key, value in priorities.items()
            }

        direct_weights['nlp'] = 0.5
        return direct_weights

    @staticmethod
    def _ranking_to_priority(value: float) -> float:
        ranking = min(4, max(1, int(round(float(value)))))
        return RANKING_TO_PRIORITY[ranking]
