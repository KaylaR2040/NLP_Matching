from fastapi import APIRouter, HTTPException, Body
from typing import List, Dict
import json

from ..models.mentor import Mentor
from ..config import MENTORS_FILE
from ..services.google_forms import GoogleFormSubmissionError, submit_google_form

router = APIRouter()

def load_mentors() -> List[Dict]:
    """Load mentors from storage"""
    if not MENTORS_FILE.exists():
        return []
    
    try:
        with open(MENTORS_FILE, 'r') as f:
            data = json.load(f)
            return data
    except Exception as e:
        print(f"Error loading mentors: {e}")
        return []

def save_mentors(mentors: List[Dict]):
    """Save mentors to storage"""
    try:
        MENTORS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(MENTORS_FILE, 'w') as f:
            json.dump(mentors, f, indent=2)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving data: {str(e)}")

@router.post("/", response_model=Dict)
async def submit_mentor(mentor_data: Dict = Body(...)):
    """Submit a new mentor application"""
    try:
        # Validate and create mentor object
        mentor = Mentor(**mentor_data)
        mentor_record = mentor.to_dict()
        google_form_result = submit_google_form("mentor", mentor_record)
        
        # Load existing mentors
        mentors = load_mentors()
        
        # Add new mentor
        mentors.append(mentor_record)
        
        # Save updated list
        save_mentors(mentors)
        
        return {
            "success": True,
            "message": "Mentor application submitted successfully",
            "mentor_id": mentor.id,
            "data": mentor_record,
            "google_form": google_form_result.to_dict(),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid data: {str(e)}")
    except GoogleFormSubmissionError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Google Form submission failed: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error submitting application: {str(e)}")

@router.get("/", response_model=List[Dict])
async def get_all_mentors():
    """Get all mentor applications"""
    try:
        mentors = load_mentors()
        return mentors
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving mentors: {str(e)}")

@router.get("/{mentor_id}", response_model=Dict)
async def get_mentor(mentor_id: str):
    """Get a specific mentor by ID"""
    try:
        mentors = load_mentors()
        for mentor_data in mentors:
            if mentor_data.get('id') == mentor_id:
                return mentor_data
        
        raise HTTPException(status_code=404, detail="Mentor not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving mentor: {str(e)}")

@router.delete("/{mentor_id}")
async def delete_mentor(mentor_id: str):
    """Delete a mentor application"""
    try:
        mentors = load_mentors()
        original_count = len(mentors)
        
        # Filter out the mentor to delete
        mentors = [m for m in mentors if m.get('id') != mentor_id]
        
        if len(mentors) == original_count:
            raise HTTPException(status_code=404, detail="Mentor not found")
        
        # Save updated list
        save_mentors(mentors)
        
        return {
            "success": True,
            "message": "Mentor deleted successfully",
            "mentor_id": mentor_id
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting mentor: {str(e)}")

@router.get("/count/total")
async def get_mentor_count():
    """Get total count of mentors"""
    try:
        mentors = load_mentors()
        return {"count": len(mentors)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error counting mentors: {str(e)}")
