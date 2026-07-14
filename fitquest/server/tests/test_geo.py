"""World-map geometry & geo cache — decoder, hex grid, ingestion rules."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from game import geo, geo_cache, quests  # noqa: E402


# -- Google polyline decoder ------------------------------------------------------

def test_decode_polyline_google_reference_vector():
    """The reference vector from Google's encoded-polyline spec."""
    points = geo.decode_polyline("_p~iF~ps|U_ulLnnqC_mqNvxq`@")
    expected = [(38.5, -120.2), (40.7, -120.95), (43.252, -126.453)]
    assert len(points) == 3
    for (lat, lon), (elat, elon) in zip(points, expected):
        assert abs(lat - elat) < 1e-5 and abs(lon - elon) < 1e-5


# -- Hex grid ----------------------------------------------------------------------

def test_xy_hex_roundtrip():
    for q in range(-5, 6):
        for r in range(-5, 6):
            x, y = geo.hex_to_xy(q, r)
            assert geo.xy_to_hex(x, y) == (q, r)


def test_track_interpolation_leaves_no_gaps():
    """Two sparse GPS points 10 hexes apart must yield a contiguous path."""
    origin = {"lat": 59.0, "lon": 18.0}
    x1, y1 = geo.hex_to_xy(10, 0)
    lat1 = origin["lat"] + y1 / geo.M_PER_DEG_LAT
    import math

    lon1 = origin["lon"] + x1 / (geo.M_PER_DEG_LAT * math.cos(math.radians(origin["lat"])))
    hexes = geo.hexes_for_track([(origin["lat"], origin["lon"]), (lat1, lon1)], origin)
    assert hexes[0] == (0, 0) and hexes[-1] == (10, 0)
    for (q0, r0), (q1, r1) in zip(hexes, hexes[1:]):
        assert (q1 - q0, r1 - r0) in geo.HEX_NEIGHBOURS  # contiguous


def test_empty_track_yields_no_hexes():
    assert geo.hexes_for_track([], {"lat": 0, "lon": 0}) == []


# -- Geo cache ---------------------------------------------------------------------

def _fresh():
    return {"origin": None, "activities": {}, "hexes": {}}


def test_record_hexes_idempotent():
    cache = _fresh()
    geo_cache.record_hexes(cache, 42, [(0, 0), (1, 0)], "2026-06-30")
    geo_cache.record_hexes(cache, 42, [(0, 0), (1, 0)], "2026-06-30")
    assert cache["hexes"]["0,0"]["visits"] == 1


def test_record_hexes_counts_one_visit_per_activity():
    cache = _fresh()
    geo_cache.record_hexes(cache, 1, [(0, 0), (0, 0), (1, 0)], "2026-06-29")
    geo_cache.record_hexes(cache, 2, [(0, 0)], "2026-06-30")
    assert cache["hexes"]["0,0"]["visits"] == 2  # once per activity, not per pass
    assert cache["hexes"]["0,0"]["firstDate"] == "2026-06-29"
    assert cache["hexes"]["0,0"]["lastDate"] == "2026-06-30"


def test_no_gps_marker_prevents_refetch():
    cache = _fresh()
    geo_cache.mark_no_gps(cache, 7)
    assert geo_cache.has_activity(cache, 7)
    assert geo_cache.has_activity(cache, "7")  # id types normalised


def test_new_hexes_counted_per_first_visit_week():
    from datetime import date, timedelta

    cache = _fresh()
    today = date.today()
    last_week = today - timedelta(days=7)
    geo_cache.record_hexes(cache, 1, [(0, 0)], last_week.isoformat())
    geo_cache.record_hexes(cache, 2, [(0, 0), (1, 0)], today.isoformat())
    wk = quests.week_key(today)
    # (0,0) was first seen last week; only (1,0) is new this week
    assert geo_cache.new_hexes_in_week(cache, wk) == 1


def test_player_hex_is_end_of_most_recent_track():
    cache = _fresh()
    geo_cache.record_hexes(cache, 1, [(0, 0), (1, 0)], "2026-06-01")
    geo_cache.record_hexes(cache, 2, [(1, 0), (2, -1)], "2026-06-30")
    assert geo_cache.player_hex(cache) == {"q": 2, "r": -1}


# -- Demo fallback -----------------------------------------------------------------

def _hist():
    return [
        {"activityId": 1, "activityType": "running", "durationMinutes": 40,
         "startDate": "2026-06-01"},
        {"activityId": 2, "activityType": "strength_training",
         "durationMinutes": 45, "startDate": "2026-06-02"},
        {"activityId": 3, "activityType": "cycling", "durationMinutes": 60,
         "startDate": "2026-06-03"},
    ]


def test_demo_hexes_deterministic_and_outdoor_only():
    t1, t2 = geo.demo_hexes(_hist()), geo.demo_hexes(_hist())
    assert t1 == t2                       # stable across reloads
    assert "2" not in t1                  # indoor activity → no track
    assert {"1", "3"} == set(t1)


def test_demo_tracks_form_a_connected_world():
    tracks = geo.demo_hexes(_hist())
    assert tracks["3"][0] == tuple(tracks["1"][-1])  # next starts where last ended


# -- cache v2 migration -------------------------------------------------------------

def test_old_cache_version_is_rebuilt(monkeypatch, tmp_path):
    import json

    f = tmp_path / "geo_cache.json"
    f.write_text(json.dumps({"origin": {"lat": 1, "lon": 2},
                             "activities": {"1": {"noGps": True}}, "hexes": {}}))
    monkeypatch.setattr(geo_cache, "GEO_FILE", f)
    cache = geo_cache.load()   # v1 (no version field) -> fresh v2
    assert cache["activities"] == {} and cache["version"] == geo_cache.CACHE_VERSION


def test_hex_to_latlon_roundtrip():
    origin = {"lat": 59.24, "lon": 18.0}
    lat, lon = geo.hex_to_latlon(4, -2, origin)
    assert geo.xy_to_hex(*geo.to_xy(lat, lon, origin)) == (4, -2)


def test_simplify_track_keeps_endpoints():
    pts = [(float(i), float(i)) for i in range(500)]
    out = geo.simplify_track(pts, max_points=50)
    assert len(out) == 50
    assert out[0] == pts[0] and out[-1] == pts[-1]
    assert geo.simplify_track(pts[:10], max_points=50) == pts[:10]
