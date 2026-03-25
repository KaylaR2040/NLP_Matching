from fastapi import APIRouter, HTTPException, Body
from typing import List, Dict
import json
from pathlib import Path
from datetime import datetime

from ..models.mentee import Mentee

router = APIRouter()

# Storage path
STORAGE_FILE = Path(__file__).parent.parent / "storage" / "mentees.json"

def load_mentees() -> List[Dict]:
    """Load mentees from storage"""
    if not STORAGE_FILE.exists():
        return []
    
    try:
        with open(STORAGE_FILE, 'r') as f:
            data = json.load(f)
            return data
    except Exception as e:
        print(f"Error loading mentees: {e}")
        return []

def save_mentees(mentees: List[Dict]):
    """Save mentees to storage"""
    try:
        STORAGE_FILE.parent.mkdir(exist_ok=True)
        with open(STORAGE_FILE, 'w') as f:
            json.dump(mentees, f, indent=2)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving data: {str(e)}")

@router.post("/", response_model=Dict)
async def submit_mentee(mentee_data: Dict = Body(...)):
    """Submit a new mentee application from Flutter"""
    try:
        # Validate and create mentee object
        mentee = Mentee(**mentee_data)
        
        # Load existing mentees
        mentees = load_mentees()
        
        # Add new mentee
        mentees.append(mentee.to_dict())
        
        # Save updated list
        save_mentees(mentees)
        
        return {
            "success": True,
            "message": "Mentee application submitted successfully",
            "mentee_id": mentee.id,
            "data": mentee.to_dict()
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid data: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error submitting application: {str(e)}")

@router.get("/", response_model=List[Dict])
async def get_all_mentees():
    """Get all mentee applications"""
    try:
        mentees = load_mentees()
        return mentees
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving mentees: {str(e)}")

@router.get("/{mentee_id}", response_model=Dict)
async def get_mentee(mentee_id: str):
    """Get a specific mentee by ID"""
    try:
        mentees = load_mentees()
        for mentee_data in mentees:
            if mentee_data.get('id') == mentee_id:
                return mentee_data
        
        raise HTTPException(status_code=404, detail="Mentee not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving mentee: {str(e)}")

@router.delete("/{mentee_id}")
async def delete_mentee(mentee_id: str):
    """Delete a mentee application"""
    try:
        mentees = load_mentees()
        original_count = len(mentees)
        
        # Filter out the mentee to delete
        mentees = [m for m in mentees if m.get('id') != mentee_id]
        
        if len(mentees) == original_count:
            raise HTTPException(status_code=404, detail="Mentee not found")
        
        # Save updated list
        save_mentees(mentees)
        
        return {
            "success": True,
            "message": "Mentee deleted successfully",
            "mentee_id": mentee_id
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting mentee: {str(e)}")

@router.get("/count/total")
async def get_mentee_count():
    """Get total count of mentees"""
    try:
        mentees = load_mentees()
        return {"count": len(mentees)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error counting mentees: {str(e)}")