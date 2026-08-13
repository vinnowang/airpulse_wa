# airpulse_wa/core_logic.py
from schemas import VenueCheckResponse, VenueCheckRequest
from datetime import datetime

AQI_THRESHOLD_MODERATE = 101
AQI_THRESHOLD_UNHEALTHY = 151

def evaluate_wiaa_sports_risk(
    request: VenueCheckRequest, 
    current_aqi: int, 
    data_source: str
) -> VenueCheckResponse:
    if request.event_time < datetime.now():
        return VenueCheckResponse(
            venue_name=request.venue_name,
            current_aqi=current_aqi,
            data_source_used=data_source,
            status="PAST EVENT",
            status_color="GRAY",
            actionable_advice="No evaluation needed for past events."
        )

    if current_aqi >= AQI_THRESHOLD_UNHEALTHY:
        return VenueCheckResponse(
            venue_name=request.venue_name,
            current_aqi=current_aqi,
            data_source_used=data_source,
            status="CANCELLED_OR_INDOORS",
            status_color="RED",
            actionable_advice="AQI > 150. State and WIAA rules mandate moving the event indoors or canceling outdoor play."
        )

    elif current_aqi >= AQI_THRESHOLD_MODERATE:
        return VenueCheckResponse(
            venue_name=request.venue_name,
            current_aqi=current_aqi,
            data_source_used=data_source,
            status="RESTRICTED_PLAY",
            status_color="ORANGE",
            actionable_advice="Air quality is unhealthy for sensitive groups. Reduce outdoor exertion and monitor players."
        )

    else:
        return VenueCheckResponse(
            venue_name=request.venue_name,
            current_aqi=current_aqi,
            data_source_used=data_source,
            status="GO",
            status_color="GREEN",
            actionable_advice="Air quality acceptable for outdoor play."
        )