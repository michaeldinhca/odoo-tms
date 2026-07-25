import math

EARTH_RADIUS_KM = 6371.0088

# MVP assumption — no real-world routing/traffic data. Revisit if road-network
# accuracy becomes a blocker (see DECISIONS.md).
AVERAGE_SPEED_KMH = 40.0


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return EARTH_RADIUS_KM * c


def estimate_duration_min(
    distance_km: float, average_speed_kmh: float = AVERAGE_SPEED_KMH
) -> float:
    if average_speed_kmh <= 0:
        raise ValueError("average_speed_kmh must be positive")
    return (distance_km / average_speed_kmh) * 60.0
