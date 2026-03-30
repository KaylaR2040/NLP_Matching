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
    interests: List[str] = field(default_factory=list)
    goals: str = ""
    topics: List[str] = field(default_factory=list)
    style: List[str] = field(default_factory=list)
    availability: List[str] = field(default_factory=list)
    background: str = ""
    source_mentor_id: str = ""
    source_row_index: Optional[int] = None
    ranking_weights: Dict[str, float] = field(default_factory=dict)
    nlp: ParticipantNLP = field(default_factory=ParticipantNLP)
    embedding: List[float] = field(default_factory=list)

    def profile_text(self) -> str:
        """Concatenate free-text fields for NLP embedding."""
        return " ".join(
            part
            for part in [self.goals, self.background, " ".join(self.interests), " ".join(self.topics)]
            if part
        ).strip()


@dataclass
class Mentor:
    """Mentor profile used by the matching pipeline."""

    mentor_id: str
    name: str
    role: str
    expertise: List[str] = field(default_factory=list)
    goals: str = ""
    topics: List[str] = field(default_factory=list)
    style: List[str] = field(default_factory=list)
    availability: List[str] = field(default_factory=list)
    bio: str = ""
    prior_mentoring_experience: str = ""
    mentorship_motivation: str = ""
    professional_experience: str = ""
    personal_interests: List[str] = field(default_factory=list)
    domain_tags: List[str] = field(default_factory=list)
    source_row_index: Optional[int] = None
    nlp: ParticipantNLP = field(default_factory=ParticipantNLP)
    embedding: List[float] = field(default_factory=list)

    def profile_text(self) -> str:
        """Concatenate free-text fields for NLP embedding."""
        return " ".join(
            part
            for part in [
                self.goals,
                self.bio,
                self.professional_experience,
                self.mentorship_motivation,
                " ".join(self.expertise),
                " ".join(self.topics),
                " ".join(self.personal_interests),
                " ".join(self.domain_tags),
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
    match_score: float
    locked: bool = False

    def to_dict(self) -> Dict[str, object]:
        return {
            "mentee_id": self.mentee_id,
            "mentee_name": self.mentee_name,
            "mentor_id": self.mentor_id,
            "mentor_name": self.mentor_name,
            "component_scores": self.component_scores,
            "effective_weights": self.effective_weights,
            "match_score": self.match_score,
            "match_percent": round(self.match_score * 100, 2),
            "locked": self.locked,
        }
