"""Google Places API (New) integration for nearby gym/fitness facility search."""

import math
import os

import requests

PLACES_URL = "https://places.googleapis.com/v1/places:searchNearby"
FIELD_MASK = (
    "places.displayName,places.formattedAddress,places.rating,"
    "places.userRatingCount,places.location,places.currentOpeningHours.openNow"
)


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance between two lat/lng points, in km - computed
    locally rather than asking the model to do this arithmetic."""
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def search_nearby_gyms(lat: float, lng: float, radius_m: int = 5000, max_results: int = 8) -> list[dict]:
    """Search Google Places for gyms/fitness centers near (lat, lng).
    Returns results sorted by distance, closest first."""
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return [{"error": "GOOGLE_MAPS_API_KEY is not set"}]

    try:
        response = requests.post(
            PLACES_URL,
            headers={
                "Content-Type": "application/json",
                "X-Goog-Api-Key": api_key,
                "X-Goog-FieldMask": FIELD_MASK,
            },
            json={
                "includedTypes": ["gym"],
                "maxResultCount": max_results,
                "locationRestriction": {
                    "circle": {"center": {"latitude": lat, "longitude": lng}, "radius": radius_m},
                },
            },
            timeout=10,
        )
        response.raise_for_status()
    except requests.RequestException as e:
        return [{"error": f"Places API request failed: {e}"}]

    places = response.json().get("places", [])

    results = []
    for place in places:
        location = place.get("location") or {}
        distance_km = None
        if "latitude" in location and "longitude" in location:
            distance_km = round(_haversine_km(lat, lng, location["latitude"], location["longitude"]), 2)
        results.append(
            {
                "name": place.get("displayName", {}).get("text"),
                "address": place.get("formattedAddress"),
                "rating": place.get("rating"),
                "rating_count": place.get("userRatingCount"),
                "open_now": (place.get("currentOpeningHours") or {}).get("openNow"),
                "distance_km": distance_km,
            }
        )

    results.sort(key=lambda r: (r["distance_km"] is None, r["distance_km"]))
    return results
