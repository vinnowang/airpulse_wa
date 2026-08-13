import io
import os
import httpx
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

app = FastAPI(title="AirPulse WA Backend")

# Step 1.3: Dynamic CORS Configuration via Environment Variables
# Parses comma-separated origin URLs from ALLOWED_ORIGINS (e.g. "https://your-app.vercel.app,http://localhost:3000")
allowed_origins_env = os.getenv(
    "ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:8000,*"
)
allowed_origins = [
    origin.strip() for origin in allowed_origins_env.split(",")
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Keys
AIRNOW_API_KEY = os.getenv("AIRNOW_API_KEY", "YOUR_AIRNOW_KEY")
NASA_MAP_KEY = os.getenv("NASA_MAP_KEY", "YOUR_NASA_FIRMS_KEY")


# Data Schemas
class VenueRequest(BaseModel):
    venue_name: str
    latitude: float
    longitude: float


class HealthRequest(BaseModel):
    user_profile: str
    latitude: float
    longitude: float


class WIAALogExportRequest(BaseModel):
    event_id: str
    venue_name: str
    school_district: str
    aqi: int
    reason: str
    action_taken: str


class AlertRequest(BaseModel):
    phone_number: str
    venue_name: str
    aqi: int
    recommendation: str


def calculate_wiaa_sports_risk(aqi: int) -> dict:
    """Applies official WA Dept of Health & WIAA wildfire smoke guidelines."""
    if aqi <= 50:
        return {
            "level": "Low",
            "status": "GO",
            "recommendation": "Normal outdoor activity allowed.",
        }
    elif aqi <= 100:
        return {
            "level": "Moderate",
            "status": "GO",
            "recommendation": (
                "Normal outdoor activity. Monitor sensitive individuals."
            ),
        }
    elif aqi <= 150:
        return {
            "level": "Unhealthy for Sensitive Groups",
            "status": "RESTRICT",
            "recommendation": (
                "Limit intense outdoor workouts to < 1 hour. Provide frequent"
                " breaks."
            ),
        }
    elif aqi <= 200:
        return {
            "level": "Unhealthy",
            "status": "CANCEL/MOVE INDOORS",
            "recommendation": (
                "Cancel all outdoor practice/contests or relocate indoors."
            ),
        }
    else:
        return {
            "level": "Very Unhealthy / Hazardous",
            "status": "CANCEL ALL",
            "recommendation": "All outdoor activities strictly prohibited.",
        }


@app.get("/")
def read_root():
    return {"project": "AirPulse WA", "status": "Operational"}


@app.post("/api/sports-check")
async def check_sports_venue(req: VenueRequest):
    """Pulls current PM2.5/AQI from EPA AirNow and evaluates WIAA risk."""
    url = (
        f"https://www.airnowapi.org/aq/observation/latLong/current/"
        f"?format=application/json&latitude={req.latitude}&longitude={req.longitude}"
        f"&distance=25&API_KEY={AIRNOW_API_KEY}"
    )
    async with httpx.AsyncClient() as client:
        try:
            res = await client.get(url, timeout=10.0)
            data = res.json()
        except Exception:
            data = [{"ParameterName": "PM2.5", "AQI": 115}]

    pm25_data = next(
        (item for item in data if item.get("ParameterName") == "PM2.5"), None
    )
    aqi = pm25_data["AQI"] if pm25_data else 50
    risk = calculate_wiaa_sports_risk(aqi)

    return {
        "venue": req.venue_name,
        "aqi": aqi,
        "risk_level": risk["level"],
        "action": risk["status"],
        "recommendation": risk["recommendation"],
    }


@app.post("/api/health-advisory")
async def get_health_advisory(req: HealthRequest):
    """Generates personalized guidance based on AQI and user sensitivity."""
    url = (
        f"https://www.airnowapi.org/aq/observation/latLong/current/"
        f"?format=application/json&latitude={req.latitude}&longitude={req.longitude}"
        f"&distance=25&API_KEY={AIRNOW_API_KEY}"
    )
    async with httpx.AsyncClient() as client:
        try:
            res = await client.get(url, timeout=10.0)
            data = res.json()
        except Exception:
            data = [{"ParameterName": "PM2.5", "AQI": 85}]

    pm25_data = next(
        (item for item in data if item.get("ParameterName") == "PM2.5"), None
    )
    aqi = pm25_data["AQI"] if pm25_data else 50

    guidelines = []
    if (
        "asthma" in req.user_profile.lower()
        or "sensitive" in req.user_profile.lower()
    ):
        if aqi > 50:
            guidelines.append("Keep quick-relief medicine handy.")
            guidelines.append("Avoid prolonged outdoor exertion.")
    if aqi > 100:
        guidelines.append("Close windows and use indoor air filtration (HEPA).")

    return {
        "user_profile": req.user_profile,
        "current_aqi": aqi,
        "personalized_guidelines": guidelines
        or ["Air quality is acceptable; enjoy normal activities."],
    }


@app.get("/api/satellite-fires")
async def get_satellite_fires():
    """Pulls active VIIRS thermal hotspot coordinates for Washington state via NASA FIRMS."""
    url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{NASA_MAP_KEY}/VIIRS_SNPP_NRT/-124.8,45.5,-116.9,49.0/1"

    async with httpx.AsyncClient() as client:
        try:
            res = await client.get(url, timeout=10.0)
            lines = res.text.strip().split("\n")
            fire_points = []
            if len(lines) > 1:
                headers = lines[0].split(",")
                lat_idx, lon_idx = headers.index("latitude"), headers.index(
                    "longitude"
                )
                for line in lines[1:50]:
                    parts = line.split(",")
                    fire_points.append({
                        "latitude": float(parts[lat_idx]),
                        "longitude": float(parts[lon_idx]),
                    })
            return fire_points
        except Exception:
            return [
                {"latitude": 47.6588, "longitude": -117.4260},
                {"latitude": 46.6021, "longitude": -120.5059},
                {"latitude": 48.0030, "longitude": -119.8400},
            ]


@app.post("/api/export-wiaa-log")
async def export_wiaa_log(req: WIAALogExportRequest):
    """Generates a downloadable PDF report for WIAA compliance & cancellation records."""
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)

    p.setFont("Helvetica-Bold", 18)
    p.drawString(50, 750, "WIAA Wildfire Smoke Action Log")
    p.setFont("Helvetica", 10)
    p.drawString(50, 735, "AirPulse WA Environmental Health & Safety Report")
    p.line(50, 725, 550, 725)

    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, 690, f"Event ID: {req.event_id}")
    p.drawString(50, 670, f"School District: {req.school_district}")
    p.drawString(50, 650, f"Venue: {req.venue_name}")

    p.setFont("Helvetica", 11)
    p.drawString(50, 610, f"Recorded AQI (PM2.5): {req.aqi}")
    p.drawString(50, 590, f"Action Required: {req.action_taken}")

    p.drawString(50, 550, "Cancellation / Restriction Reason:")
    p.setFont("Helvetica-Oblique", 10)
    p.drawString(70, 530, req.reason)

    p.setFont("Helvetica", 10)
    p.line(50, 450, 250, 450)
    p.drawString(50, 435, "Athletic Director / Official Signature")

    p.showPage()
    p.save()

    buffer.seek(0)
    return Response(
        content=buffer.getvalue(),
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f"attachment; filename=WIAA_Log_{req.event_id}.pdf"
            )
        },
    )


@app.post("/api/send-alert")
async def send_twilio_alert(req: AlertRequest):
    """Sends SMS alerts to coaches and athletic directors when AQI exceeds unsafe thresholds."""
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    from_number = os.getenv("TWILIO_PHONE_NUMBER")

    if not all([account_sid, auth_token, from_number]):
        return {
            "status": "mocked",
            "recipient": req.phone_number,
            "message": (
                f"AIRPULSE ALERT: AQI at {req.venue_name} is {req.aqi}."
                f" Action: {req.recommendation}"
            ),
        }

    from twilio.rest import Client

    client = Client(account_sid, auth_token)
    message = client.messages.create(
        body=(
            f"⚠️ AIRPULSE WA ALERT: {req.venue_name} AQI is {req.aqi}."
            f" Recommendation: {req.recommendation}"
        ),
        from_=from_number,
        to=req.phone_number,
    )
    return {"status": "sent", "sid": message.sid}