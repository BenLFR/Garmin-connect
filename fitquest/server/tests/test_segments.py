"""Segments — re-runnable routes from the player's own tracks."""

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from game import geo_cache, quests, segments  # noqa: E402


def _cache_with(entries):
    cache = {"version": geo_cache.CACHE_VERSION, "origin": None,
             "activities": {}, "hexes": {}}
    for act_id, hexes, d in entries:
        geo_cache.record_hexes(cache, act_id, hexes, d,
                               points=[[48.85 + i * 1e-3, 2.35] for i in range(len(hexes))],
                               name=f"Course {act_id}")
    return cache


def _line(n, offset=0):
    return [(q + offset, 0) for q in range(n)]


def test_short_tracks_make_no_segment():
    cache = _cache_with([(1, _line(3), "2026-06-01")])
    assert segments.build_segments(cache) == []


def test_near_identical_routes_are_deduped_keeping_most_recent():
    cache = _cache_with([
        (1, _line(10), "2026-06-01"),
        (2, _line(10), "2026-06-15"),   # same route re-run later
        (3, _line(10, offset=50), "2026-06-10"),  # different place
    ])
    segs = segments.build_segments(cache)
    assert len(segs) == 2
    route = next(s for s in segs if s["sourceActivityId"] == "2")
    assert route["firstDate"] == "2026-06-01"  # the route's age = oldest run


def test_rerun_covering_80pct_completes_segment_this_week():
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    wk = quests.week_key(today)
    cache = _cache_with([
        (1, _line(10), "2026-01-05"),                 # the original route
        (2, _line(9), monday.isoformat()),            # 90 % re-covered this week
    ])
    segs = segments.build_segments(cache)
    assert len(segs) == 1                              # deduped into one route
    assert segs[0]["firstDate"] == "2026-01-05"        # known itinerary
    assert segments.runs_this_week(cache, segs[0], wk) is True
    assert segments.completed_this_week(cache, segs, wk) == 1


def test_brand_new_route_this_week_is_not_a_rerun():
    today = date.today()
    wk = quests.week_key(today)
    cache = _cache_with([(1, _line(10), today.isoformat())])
    segs = segments.build_segments(cache)
    assert segments.completed_this_week(cache, segs, wk) == 0


def test_partial_rerun_does_not_complete():
    today = date.today()
    wk = quests.week_key(today)
    cache = _cache_with([
        (1, _line(10), "2026-01-05"),
        (2, _line(5), today.isoformat()),  # only 50 % of the route
    ])
    target = next(s for s in segments.build_segments(cache)
                  if s["sourceActivityId"] == "1")
    assert segments.runs_this_week(cache, target, wk) is False


def test_segment_quest_joins_geo_pool():
    qs = quests.weekly_quests("rodeur", with_geo=True, with_segments=True)
    assert len(qs) == 4
    assert qs[3]["metric"] in ("new_hexes", "segments_done")


def test_payload_shape():
    cache = _cache_with([(1, _line(10), "2026-06-01")])
    out = segments.payload(cache, quests.week_key())
    assert len(out) == 1
    seg = out[0]
    assert {"id", "name", "date", "distanceKm", "points", "doneThisWeek"} <= set(seg)
    assert seg["doneThisWeek"] is False
