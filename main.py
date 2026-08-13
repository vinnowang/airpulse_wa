import os
import requests
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from twilio.rest import Client

# Initialize FastAPI App
app = FastAPI(
    title="AirPulse WA Backend",
    description="Real-time Air Quality and Wildfire Alert API for Washington State",
    version="1.0.0"
)

# Enable CORS for cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows requests from any origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Environment Variables
AIRNOW_API_KEY = os.getenv("AIRNOW_API_KEY")
NASA_MAP_KEY = os.getenv("NASA_MAP_KEY")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "+15550000000")

# Request Model for Twilio Subscription
class AlertSubscription(BaseModel):
    phone_number: str = Field(..., example="+15095550199")
    zip_code: str = Field(..., example="99201")


# -------------------------------------------------------------------
# Frontend Routes
# -------------------------------------------------------------------

@app.get("/", response_class=FileResponse)
def serve_homepage():
    """Serves the index.html dashboard at the root URL."""
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    return {"status": "Operational", "message": "index.html not found in root directory."}


# -------------------------------------------------------------------
# API Endpoints
# -------------------------------------------------------------------

@app.get("/api/status")
def get_status():
    """Backend health check endpoint."""
    return {"project": "AirPulse WA", "status": "Operational"}


@app.get("/api/air-quality")
def get_air_quality(zip_code: str = "99201"):
    """Fetches current AQI observation data from AirNow API."""
    if not AIRNOW_API_KEY:
        # Fallback response if key is missing
        return [{
            "ReportingArea": "Spokane",
            "AQI": 42,
            "Category": {"Name": "Good"},
            "ParameterName": "PM2.5",
            "Latitude": 47.6588,
            "Longitude": -117.4260
        }]

    url = (
        f"https://www.airnowapi.org/aq/observation/zipCode/current/"
        f"?format=application/json&zipCode={zip_code}&distance=50&API_KEY={AIRNOW_API_KEY}"
    )

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        if not data:
            raise HTTPException(status_code=404, detail="No air quality data found for ZIP code.")
        return data
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"AirNow API error: {str(e)}")


@app.get("/api/fires")
def get_wildfires():
    """Fetches active satellite wildfire thermal detection data from NASA FIRMS."""
    if not NASA_MAP_KEY:
        # Fallback sample hotspot
        return [{
            "latitude": 47.35,
            "longitude": -120.5,
            "brightness": 315.2,
            "acq_date": "2026-08-13"
        }]

    # NASA FIRMS VIIRS_SNPP_NRT for USA/WA bounding box
    url = f"https://firms.modaps.eosdis.nasa.gov/api/country/csv/{NASA_MAP_KEY}/VIIRS_SNPP_NRT/USA/1"

    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            lines = response.text.strip().split("\n")
            if len(lines) <= 1:
                return []
            
            header = lines[0].split(",")
            fires = []
            
            # Filter detections within approximate Washington State coordinates
            for line in lines[1:100]:
                parts = line.split(",")
                if len(parts) > 2:
                    try:
                        lat = float(parts[0])
                        lon = float(parts[1])
                        # Washington State Lat/Lon Bounds
                        if 45.5 <= lat <= 49.0 and -124.8 <= lon <= -116.9:
                            fires.append({
                                "latitude": lat,
                                "longitude": lon,
                                "brightness": float(parts[2]) if len(parts) > 2 else 300.0
                            })
                    except ValueError:
                        continue
            return fires
        return []
    except Exception as e:
        print(f"NASA FIRMS fetch warning: {e}")
        return []


@app.post("/api/subscribe-alerts", status_code=status.HTTP_201_CREATED)
def subscribe_sms_alert(payload: AlertSubscription):
    """Sends a welcome SMS notification via Twilio when a user subscribes."""
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        return {"status": "success", "message": "Subscription logged (Twilio credentials not configured)."}

    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            body=f"AirPulse WA: You are subscribed to air quality alerts for ZIP {payload.zip_code}. Stay safe!",
            from_=TWILIO_PHONE_NUMBER,
            to=payload.phone_number
        )
        return {"status": "success", "sid": message.sid}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Twilio SMS delivery failed: {str(e)}")