# airpulse_wa/schemas.py
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class VenueCheckRequest(BaseModel):
    venue_name: str
    latitude: float
    longitude: float
    sport_type: str
    event_time: datetime

class VenueCheckResponse(BaseModel):
    venue_name: str
    current_aqi: int
    data_source_used: str
    status: str             # e.g., "CANCELLED_OR_INDOORS", "RESTRICTED", "CLEAR"
    status_color: str       # e.g., "RED", "ORANGE", "GREEN"
    actionable_advice: str
    projected_clearing_time: Optional[str] = None

class HealthAdvisoryRequest(BaseModel):
    user_profile: str       # e.g., "asthma", "outdoor_worker", "elderly", "general"
    latitude: float
    longitude: float

class HealthAdvisoryResponse(BaseModel):
    user_profile: str
    current_aqi: int
    risk_level: str
    personalized_guidelines: List[str]

class SatelliteFirePoint(BaseModel):
    latitude: float
    longitude: float
    satellite_source: str   # e.g., "NASA VIIRS", "MODIS"
    frp_intensity: float
    location_name: Optional[str] = None