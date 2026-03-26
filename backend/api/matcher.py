from typing import List, Dict, Tuple
from .models.mentee import Mentee
from .models.mentor import Mentor


def _load_ml_libs():
    """Lazy-load heavy ML libraries so the server can start without them."""
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    return SentenceTransformer, cosine_similarity, np


class MentorMatcher:
    """NLP-based mentor matching system
    
    Uses sentence transformer embeddings for semantic similarity
    plus weighted scoring based on mentee priority preferences.
    
    Data flow:
    1. Flutter form submits mentee/mentor JSON to FastAPI
    2. FastAPI stores in backend/api/storage/*.json
    3. Matcher reads from that storage (NOT from data/ CSVs)
    4. Embeddings are generated from get_searchable_text() on each model
    5. Weighted combination of NLP similarity + field overlap = final score
    """
    
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        """Initialize with sentence transformer model (lazy loaded)"""
        self._model_name = model_name
        self._model = None
        self._cosine_similarity = None
        self._np = None
        self._mentor_embeddings = None
        self._mentor_list = None

    def _ensure_loaded(self):
        """Load ML models on first use"""
        if self._model is None:
            SentenceTransformer, cosine_similarity, np = _load_ml_libs()
            self._model = SentenceTransformer(self._model_name)
            self._cosine_similarity = cosine_similarity
            self._np = np

    @property
    def model(self):
        self._ensure_loaded()
        return self._model
    
    def _jaccard(self, set_a: List[str], set_b: List[str]) -> float:
        """Calculate Jaccard similarity between two lists"""
        if not set_a or not set_b:
            return 0.0
        a = set(set_a)
        b = set(set_b)
        intersection = a.intersection(b)
        union = a.union(b)
        return len(intersection) / len(union) if union else 0.0
    
    def _grad_year_closeness(self, mentee: Mentee, mentor: Mentor) -> float:
        """Score based on how close graduation years are (closer = higher)"""
        try:
            mentee_year = int(mentee.graduationYear)
            mentor_year = int(mentor.graduationYear) if mentor.graduationYear else None
            if mentor_year is None:
                return 0.5  # neutral if unknown
            diff = abs(mentee_year - mentor_year)
            if diff <= 5:
                return 1.0 - (diff * 0.15)  # 0 diff = 1.0, 5 diff = 0.25
            return 0.1
        except (ValueError, TypeError):
            return 0.5
    
    def _embed_mentors(self, mentors: List[Mentor]):
        """Pre-compute mentor embeddings"""
        mentor_texts = [mentor.get_searchable_text() for mentor in mentors]
        self._mentor_embeddings = self.model.encode(mentor_texts)
        self._mentor_list = mentors
    
    def match_mentee(self, mentee: Mentee, mentors: List[Mentor], top_k: int = 5) -> List[Dict]:
        """Find top K mentors for a mentee using NLP + weighted scoring
        
        Scoring components:
        - NLP semantic similarity (base, from sentence embeddings)
        - Industry overlap (weighted by matchByIndustry)
        - Degree overlap (weighted by matchByDegree)
        - Club/org overlap (weighted by matchByClubs)
        - Pronoun/identity match (weighted by matchByIdentity)
        - Graduation year proximity (weighted by matchByGradYears)
        """
        
        # Embed mentors if not already done or if list changed
        if self._mentor_list is not mentors:
            self._embed_mentors(mentors)
        
        # Get mentee embedding
        mentee_text = mentee.get_searchable_text()
        mentee_embedding = self.model.encode([mentee_text])
        
        # Calculate cosine similarities (base NLP score)
        nlp_similarities = self._cosine_similarity(mentee_embedding, self._mentor_embeddings)[0]
        
        # Get priority weights from the mentee's Likert selections
        weights = mentee.get_priority_weights()
        
        scores = []
        for idx, mentor in enumerate(mentors):
            base_nlp = float(nlp_similarities[idx])
            
            # Compute component scores
            industry_score = self._jaccard(mentee.industriesOfInterest, mentor.industriesOfInterest)
            degree_score = self._jaccard(mentee.degreePrograms, mentor.degreePrograms)
            clubs_score = self._jaccard(mentee.studentOrgs, mentor.studentOrgs)
            identity_score = 1.0 if mentee.pronouns == mentor.pronouns else 0.3
            grad_score = self._grad_year_closeness(mentee, mentor)
            
            # Also compute help topic overlap (always important)
            help_score = self._jaccard(mentee.helpTopics, mentor.helpTopics)
            
            # Weighted priority score
            priority_score = (
                weights['industry'] * industry_score +
                weights['degree'] * degree_score +
                weights['clubs'] * clubs_score +
                weights['identity'] * identity_score +
                weights['gradYears'] * grad_score
            )
            
            # Final combined score:
            # 40% NLP semantic similarity
            # 35% priority-weighted field matching
            # 25% help topic overlap
            total_score = (
                0.40 * base_nlp +
                0.35 * priority_score +
                0.25 * help_score
            )
            
            scores.append({
                'mentor_id': mentor.id,
                'mentor_name': f"{mentor.firstName} {mentor.lastName}",
                'mentor_email': mentor.email,
                'total_score': round(total_score, 4),
                'nlp_similarity': round(base_nlp, 4),
                'priority_weighted_score': round(priority_score, 4),
                'component_scores': {
                    'industry_overlap': round(industry_score, 4),
                    'degree_overlap': round(degree_score, 4),
                    'club_overlap': round(clubs_score, 4),
                    'identity_match': round(identity_score, 4),
                    'grad_year_closeness': round(grad_score, 4),
                    'help_topic_overlap': round(help_score, 4),
                },
                'matching_help_topics': list(set(mentee.helpTopics).intersection(set(mentor.helpTopics))),
                'common_organizations': list(set(mentee.studentOrgs).intersection(set(mentor.studentOrgs))),
                'common_industries': list(set(mentee.industriesOfInterest).intersection(set(mentor.industriesOfInterest))),
                'common_degrees': list(set(mentee.degreePrograms).intersection(set(mentor.degreePrograms))),
                'mentor_availability': mentor.availability,
                'mentor_max_mentees': mentor.maxMentees,
            })
        
        # Sort by total score descending
        scores.sort(key=lambda x: x['total_score'], reverse=True)
        return scores[:top_k]
    
    def match_all_mentees(self, mentees: List[Mentee], mentors: List[Mentor], top_k: int = 5) -> Dict:
        """Match all mentees to mentors"""
        results = {}
        
        # Pre-compute mentor embeddings once
        self._embed_mentors(mentors)
        
        for mentee in mentees:
            results[mentee.id] = {
                'mentee_name': f"{mentee.firstName} {mentee.lastName}",
                'mentee_email': mentee.email,
                'matches': self.match_mentee(mentee, mentors, top_k)
            }
        
        return results