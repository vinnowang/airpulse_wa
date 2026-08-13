# airpulse_wa/test_main.py
from datetime import datetime, timedelta
import respx
import httpx
from fastapi.testclient import TestClient
from main import app
from schemas import VenueCheckRequest
from core_logic import evaluate_wiaa_sports_risk

client = TestClient(app)
FUTURE_TIME = datetime.now() + timedelta(days=1)

# ==========================================
# Unit Tests for Core Logic
# ==========================================

def test_evaluate_wiaa_sports_risk_clear():
    """Tests that AQI below 101 returns GO / GREEN."""
    req = VenueCheckRequest(
        venue_name="Spokane Track",
        latitude=47.65,
        longitude=-117.42,
        sport_type="Track and Field",
        event_time=FUTURE_TIME
    )
    res = evaluate_wiaa_sports_risk(req, current_aqi=45, data_source="AirNow")
    assert res.status in ["GO", "CLEAR"]
    assert res.status_color == "GREEN"

def test_evaluate_wiaa_sports_risk_caution():
    """Tests that AQI between 101 and 150 returns RESTRICTED / ORANGE."""
    req = VenueCheckRequest(
        venue_name="Yakima Soccer Field",
        latitude=46.60,
        longitude=-120.50,
        sport_type="Soccer",
        event_time=FUTURE_TIME
    )
    res = evaluate_wiaa_sports_risk(req, current_aqi=120, data_source="AirNow")
    assert "RESTRICTED" in res.status
    assert res.status_color == "ORANGE"

def test_evaluate_wiaa_sports_risk_cancelled():
    """Tests that AQI >= 151 triggers WIAA cancellation / RED."""
    req = VenueCheckRequest(
        venue_name="Walla Walla Tennis Courts",
        latitude=46.06,
        longitude=-118.33,
        sport_type="Tennis",
        event_time=FUTURE_TIME
    )
    res = evaluate_wiaa_sports_risk(req, current_aqi=165, data_source="AirNow")
    assert res.status == "CANCELLED_OR_INDOORS"
    assert res.status_color == "RED"


# ==========================================
# Integration & Mocked Network Tests
# ==========================================

def test_get_dashboard_summary():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"project": "AirPulse WA", "status": "Operational"}

@respx.mock
def test_mocked_airnow_api_call():
    """Mocks AirNow external response to test pipeline under API success."""
    respx.get("https://www.airnowapi.org/aq/observation/latLong/current/").mock(
        return_value=httpx.Response(200, json=[{"ReportingArea": "Walla Walla", "AQI": 175}])
    )
    
    payload = {
        "user_profile": "asthma",
        "latitude": 46.06,
        "longitude": -118.33
    }
    response = client.post("/api/health-advisory", json=payload)
    assert response.status_code == 200
    assert response.json()["current_aqi"] == 175

def test_satellite_fires_endpoint():
    response = client.get("/api/satellite-fires")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "satellite_source" in data[0]

def test_export_wiaa_log_endpoint():
    response = client.post("/api/export-wiaa-log?venue_name=Ellensburg%20High&aqi=165")
    assert response.status_code == 200
    assert "OFFICIAL WIAA AIR QUALITY COMPLIANCE CANCELLATION LOG" in response.text