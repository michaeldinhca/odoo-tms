import math

from app.services.planning.haversine import estimate_duration_min, haversine_distance_km


def test_same_point_is_zero_distance():
    assert haversine_distance_km(43.65, -79.38, 43.65, -79.38) == 0.0


def test_known_distance_toronto_to_ottawa():
    # Toronto (43.6532 N, 79.3832 W) to Ottawa (45.4215 N, 75.6972 W) ~ 351 km great-circle
    distance = haversine_distance_km(43.6532, -79.3832, 45.4215, -75.6972)
    assert math.isclose(distance, 351, rel_tol=0.02)


def test_estimate_duration_scales_with_distance():
    assert estimate_duration_min(80.0, average_speed_kmh=40.0) == 120.0


def test_estimate_duration_rejects_non_positive_speed():
    try:
        estimate_duration_min(10.0, average_speed_kmh=0)
        raise AssertionError("expected ValueError")
    except ValueError:
        pass
