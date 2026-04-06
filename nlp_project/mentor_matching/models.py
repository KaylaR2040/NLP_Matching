"""Core datatypes for matching inputs, scoring, and outputs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ParticipantNLP:
    """Holds deterministic NLP artifacts for traceable scoring."""

    sentences: List[str] = field(default_factory=list)
    tokens: List[str] = field(default_factory=list)
    filtered_tokens: List[str] = field(default_factory=list)
    stemmed_tokens: List[str] = field(default_factory=list)
    lemmatized_tokens: List[str] = field(default_factory=list)
    normalized_text: str = ""


@dataclass
class Mentee:
    """Mentee profile used by the matching pipeline."""

    mentee_id: str
    name: str
    role: str
    pronouns: str = ""
    degree_programs: List[str] = field(default_factory=list)
    student_orgs: List[str] = field(default_factory=list)
    graduation_year: str = ""
    education_level: str = ""
    help_topics: List[str] = field(default_factory=list)
    interests: List[str] = field(default_factory=list)
    goals: str = ""
    background: str = ""
    source_mentor_id: str = ""
    source_row_index: Optional[int] = None
    ranking_weights: Dict[str, float] = field(default_factory=dict)
    ranking_preferences: Dict[str, int] = field(default_factory=dict)
    nlp: ParticipantNLP = field(default_factory=ParticipantNLP)
    industry_embedding: List[float] = field(default_factory=list)
    degree_embedding: List[float] = field(default_factory=list)
    personality_embedding: List[float] = field(default_factory=list)
    embedding: List[float] = field(default_factory=list)

    def profile_text(self) -> str:
        """Concatenate free-text fields for NLP embedding."""
        return " ".join(
            part
            for part in [
                self.goals,
                self.background,
                self.pronouns,
                self.education_level,
                self.graduation_year,
                " ".join(self.degree_programs),
                " ".join(self.student_orgs),
                " ".join(self.interests),
                " ".join(self.help_topics),
            ]
            if part
        ).strip()

    def industry_profile_text(self) -> str:
        """Technical/professional bucket for semantic vetting."""
        return " ".join(
            part
            for part in [
                self.role,
                self.goals,
                self.background,
                " ".join(self.interests),
                " ".join(self.help_topics),
            ]
            if part
        ).strip()

    def degree_profile_text(self) -> str:
        """Academic bucket used for major/degree alignment."""
        return " ".join(
            part
            for part in [
                self.education_level,
                self.graduation_year,
                " ".join(self.degree_programs),
            ]
            if part
        ).strip()

    def personality_profile_text(self) -> str:
        """Personal bucket used for style/hobby alignment."""
        return " ".join(
            part
            for part in [
                self.background,
                " ".join(self.student_orgs),
                " ".join(self.interests),
            ]
            if part
        ).strip()


@dataclass
class Mentor:
    """Mentor profile used by the matching pipeline."""

    mentor_id: str
    name: str
    role: str
    pronouns: str = ""
    degree_programs: List[str] = field(default_factory=list)
    student_orgs: List[str] = field(default_factory=list)
    graduation_year: str = ""
    help_topics: List[str] = field(default_factory=list)
    max_mentees: int = 1
    expertise: List[str] = field(default_factory=list)
    goals: str = ""
    bio: str = ""
    prior_mentoring_experience: str = ""
    mentorship_motivation: str = ""
    professional_experience: str = ""
    personal_interests: List[str] = field(default_factory=list)
    domain_tags: List[str] = field(default_factory=list)
    source_row_index: Optional[int] = None
    nlp: ParticipantNLP = field(default_factory=ParticipantNLP)
    industry_embedding: List[float] = field(default_factory=list)
    degree_embedding: List[float] = field(default_factory=list)
    personality_embedding: List[float] = field(default_factory=list)
    embedding: List[float] = field(default_factory=list)

    def profile_text(self) -> str:
        """Concatenate free-text fields for NLP embedding."""
        return " ".join(
            part
            for part in [
                self.goals,
                self.bio,
                self.pronouns,
                self.graduation_year,
                self.professional_experience,
                self.mentorship_motivation,
                " ".join(self.degree_programs),
                " ".join(self.student_orgs),
                " ".join(self.expertise),
                " ".join(self.help_topics),
                " ".join(self.personal_interests),
                " ".join(self.domain_tags),
            ]
            if part
        ).strip()

    def industry_profile_text(self) -> str:
        """Technical/professional bucket for semantic vetting."""
        return " ".join(
            part
            for part in [
                self.role,
                self.professional_experience,
                self.goals,
                " ".join(self.expertise),
                " ".join(self.help_topics),
                " ".join(self.domain_tags),
            ]
            if part
        ).strip()

    def degree_profile_text(self) -> str:
        """Academic bucket used for major/degree alignment."""
        return " ".join(
            part
            for part in [
                self.graduation_year,
                " ".join(self.degree_programs),
            ]
            if part
        ).strip()

    def personality_profile_text(self) -> str:
        """Personal bucket used for style/hobby alignment."""
        return " ".join(
            part
            for part in [
                self.bio,
                self.prior_mentoring_experience,
                self.mentorship_motivation,
                " ".join(self.personal_interests),
                " ".join(self.student_orgs),
            ]
            if part
        ).strip()


@dataclass
class PairScore:
    """Scored mentor-mentee candidate pair."""

    mentee_id: str
    mentee_name: str
    mentor_id: str
    mentor_name: str
    component_scores: Dict[str, float]
    effective_weights: Dict[str, float]
    display_weights: Dict[str, float]
    match_score: float
    match_band: str = ""
    locked: bool = False

    def to_dict(self) -> Dict[str, object]:
        return {
            "mentee_id": self.mentee_id,
            "mentee_name": self.mentee_name,
            "mentor_id": self.mentor_id,
            "mentor_name": self.mentor_name,
            "component_scores": self.component_scores,
            "effective_weights": self.effective_weights,
            "display_weights": self.display_weights,
            "match_score": self.match_score,
            "match_percent": round(self.match_score * 100, 2),
            "match_band": self.match_band,
            "locked": self.locked,
        }
