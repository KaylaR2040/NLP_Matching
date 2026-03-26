from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import json

from .routes import mentee_routes, mentor_routes, matching_routes
from .config import MENTEES_FILE, MENTORS_FILE


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize app resources on startup"""
    # Create storage files if they don't exist
    if not MENTEES_FILE.exists():
        MENTEES_FILE.write_text("[]")
    if not MENTORS_FILE.exists():
        MENTORS_FILE.write_text("[]")
    
    yield
    # Cleanup on shutdown if needed

app = FastAPI(
    title="NCSU Mentorship Matching API",
    description="API for submitting mentee/mentor forms and running NLP matching",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS for Flutter web
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your Flutter app's URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(mentee_routes.router, prefix="/api/mentees", tags=["mentees"])
app.include_router(mentor_routes.router, prefix="/api/mentors", tags=["mentors"])
app.include_router(matching_routes.router, prefix="/api/matching", tags=["matching"])

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "running",
        "message": "NCSU Mentorship Matching API",
        "endpoints": {
            "mentees": "/api/mentees",
            "mentors": "/api/mentors",
            "matching": "/api/matching"
        }
    }

@app.get("/api/stats")
async def get_stats():
    """Get statistics about stored data"""
    try:
        with open(MENTEES_FILE, 'r') as f:
            mentees = json.load(f)
        with open(MENTORS_FILE, 'r') as f:
            mentors = json.load(f)
            
        return {
            "mentee_count": len(mentees),
            "mentor_count": len(mentors),
            "ready_to_match": len(mentees) > 0 and len(mentors) > 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading data: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
