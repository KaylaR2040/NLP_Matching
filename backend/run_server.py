#!/usr/bin/env python3
"""
Run the NCSU Mentorship Matching API server.

Usage:
    cd backend/
    source venv/bin/activate
    python run_server.py

The server will start on http://localhost:8000
API docs available at http://localhost:8000/docs
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)