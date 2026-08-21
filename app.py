import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI()

# Mount static files for the frontend
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_index():
    return FileResponse('static/index.html')

@app.get("/api/events")
async def get_events():
    # TODO: Implement email fetching and AI processing
    # For now, returning mock data
    return [
        {
            "id": 1,
            "title": "Dentist Appointment",
            "date": "2026-08-25T10:00:00Z",
            "description": "Routine checkup"
        },
        {
            "id": 2,
            "title": "Lunch with Bob",
            "date": "2026-08-26T12:30:00Z",
            "description": "Discuss project at downtown cafe"
        }
    ]
