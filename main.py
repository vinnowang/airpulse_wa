from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI(title="AirPulse WA Backend")

# Enable CORS for browser requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SubscribeRequest(BaseModel):
    phone_number: str

# ---------------------------------------------------------
# Serve Frontend UI
# ---------------------------------------------------------
@app.get("/")
def read_index():
    """Serves the dashboard index.html at the root URL."""
    return FileResponse("index.html")

# ---------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------
@app.get("/api/health")
def health_monitor():
    return {"status": "ok", "message": "API Connected"}

@app.get("/api/air-quality")
def get_air_quality():
    return {
        "aqi": 26,
        "category": "Good",
        "pm25": 4.2
    }

@app.get("/api/sports-safety")
def get_sports_safety():
    return {
        "status": "Unrestricted",
        "guideline": "AQI is under 100. Normal practice and game conditions apply. Ensure athletes stay hydrated."
    }

@app.get("/api/wildfires")
def get_wildfires():
    return [
        {"latitude": 47.112, "longitude": -120.450, "brightness": 310.5},
        {"latitude": 46.996, "longitude": -120.547, "brightness": 325.2},
        {"latitude": 47.334, "longitude": -120.678, "brightness": 308.1}
    ]

@app.post("/api/subscribe")
def subscribe_sms(request: SubscribeRequest):
    return {"status": "success", "message": f"Successfully subscribed {request.phone_number}"}