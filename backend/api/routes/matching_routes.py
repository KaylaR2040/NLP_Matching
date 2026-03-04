from fastapi import APIRouter, HTTPException
from typing import List, Dict
import json
from pathlib import Path

from ..models.mentee import Mentee
from ..models.mentor import Mentor
router = APIRouter()

# Lazy-initialize matcher so server starts even without ML libs installed
_matcher = None

def get_matcher():
    global _matcher
    if _matcher is None:
        from ..matcher import MentorMatcher
        _matcher = MentorMatcher()
    return _matcher

# Storage paths - reads from the SAME storage that Flutter writes to
MENTEES_FILE = Path(__file__).parent.parent / "storage" / "mentees.json"
MENTORS_FILE = Path(__file__).parent.parent / "storage" / "mentors.json"

def load_data():
    """Load mentees and mentors from JSON storage (written by Flutter form submissions)"""
    mentees = []
    mentors = []
    
    try:
        if MENTEES_FILE.exists():
            with open(MENTEES_FILE, 'r') as f:
                mentee_data = json.load(f)
                mentees = [Mentee.from_dict(m) for m in mentee_data]
                
        if MENTORS_FILE.exists():
            with open(MENTORS_FILE, 'r') as f:
                mentor_data = json.load(f)
                mentors = [Mentor.from_dict(m) for m in mentor_data]
                
        return mentees, mentors
    except Exception as e:
        print(f"Error loading data: {e}")
        return [], []

@router.post("/run")
async def run_matching(top_k: int = 5):
    """Run NLP matching for all mentees against all mentors"""
    try:
        mentees, mentors = load_data()
        
        if not mentees:
            raise HTTPException(status_code=404, detail="No mentees found in storage")
        if not mentors:
            raise HTTPException(status_code=404, detail="No mentors found in storage")
        
        all_matches = get_matcher().match_all_mentees(mentees, mentors, top_k=top_k)
        
        return {
            "success": True,
            "message": f"Matching completed for {len(mentees)} mentees against {len(mentors)} mentors",
            "total_mentees": len(mentees),
            "total_mentors": len(mentors),
            "matches": all_matches
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error running matching: {str(e)}")

@router.get("/mentee/{mentee_id}")
async def get_mentee_matches(mentee_id: str, top_k: int = 5):
    """Get matches for a specific mentee"""
    try:
        mentees, mentors = load_data()
        
        mentee = None
        for m in mentees:
            if m.id == mentee_id:
                mentee = m
                break
        
        if not mentee:
            raise HTTPException(status_code=404, detail="Mentee not found")
        
        if not mentors:
            raise HTTPException(status_code=404, detail="No mentors available")
        
        matches = get_matcher().match_mentee(mentee, mentors, top_k=top_k)
        
        return {
            "success": True,
            "mentee_id": mentee_id,
            "mentee_name": f"{mentee.firstName} {mentee.lastName}",
            "matches": matches
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting matches: {str(e)}")

@router.get("/stats")
async def get_matching_stats():
    """Get statistics about available data for matching"""
    try:
        mentees, mentors = load_data()
        
        # Group mentors by help topics
        mentor_topics = {}
        for mentor in mentors:
            for topic in mentor.helpTopics:
                if topic not in mentor_topics:
                    mentor_topics[topic] = 0
                mentor_topics[topic] += 1
        
        # Group mentees by help topics
        mentee_topics = {}
        for mentee in mentees:
            for topic in mentee.helpTopics:
                if topic not in mentee_topics:
                    mentee_topics[topic] = 0
                mentee_topics[topic] += 1
        
        return {
            "total_mentees": len(mentees),
            "total_mentors": len(mentors),
            "total_possible_matches": len(mentees) * len(mentors),
            "mentor_help_topics": mentor_topics,
            "mentee_help_topics": mentee_topics,
            "ready_to_match": len(mentees) > 0 and len(mentors) > 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating stats: {str(e)}")