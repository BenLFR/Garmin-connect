"""Geometry for the world map — pure python, zero dependencies.

GPS tracks are projected onto a local equirectangular plane around the
player's first-ever point (`origin`), then bucketed into a pointy-top
axial hex grid (circumradius HEX_RADIUS_M). Precision beyond a few
metres is irrelevant here: a hex is ~430 m flat-to-flat and only
visited/not-visited matters (fog of war), so the flat-earth local
projection is exactly good enough.
"""

from __future__ import annotations

import math
import random
from typing import Any, Dict, List, Optional, Tuple

HEX_RADIUS_M = 250.0          # circumradius; flat-to-flat ≈ 433 m
M_PER_DEG_LAT = 111_320.0
SQRT3 = math.sqrt(3.0)

# 6 axial neighbours of a pointy-top hex
HEX_NEIGHBOURS = [(1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1)]


# -- Google encoded polyline ---------------------------------------------------


def decode_polyline(encoded: str, precision: int = 5) -> List[Tuple[float, float]]:
    """Standard Google polyline decoding → [(lat, lon), ...]."""
    factor = 10 ** precision
    points: List[Tuple[float, float]] = []
    index = lat = lon = 0
    while index < len(encoded):
        for is_lon in (False, True):
            shift = result = 0
            while True:
                b = ord(encoded[index]) - 63
                index += 1
                result |= (b & 0x1F) << shift
                shift += 5
                if b < 0x20:
                    break
            delta = ~(result >> 1) if result & 1 else result >> 1
            if is_lon:
                lon += delta
            else:
                lat += delta
        points.append((lat / factor, lon / factor))
    return points


# -- Local projection & hex grid -----------------------------------------------


def to_xy(lat: float, lon: float,
          origin: Dict[str, float]) -> Tuple[float, float]:
    """Local equirectangular projection (metres east/north of origin)."""
    x = (lon - origin["lon"]) * M_PER_DEG_LAT * math.cos(math.radians(origin["lat"]))
    y = (lat - origin["lat"]) * M_PER_DEG_LAT
    return x, y


def _cube_round(qf: float, rf: float) -> Tuple[int, int]:
    sf = -qf - rf
    q, r, s = round(qf), round(rf), round(sf)
    dq, dr, ds = abs(q - qf), abs(r - rf), abs(s - sf)
    if dq > dr and dq > ds:
        q = -r - s
    elif dr > ds:
        r = -q - s
    return int(q), int(r)


def xy_to_hex(x: float, y: float) -> Tuple[int, int]:
    """Pointy-top axial coordinates of the hex containing (x, y)."""
    qf = (SQRT3 / 3.0 * x - y / 3.0) / HEX_RADIUS_M
    rf = (2.0 / 3.0 * y) / HEX_RADIUS_M
    return _cube_round(qf, rf)


def hex_to_xy(q: int, r: int) -> Tuple[float, float]:
    """Centre of an axial hex, in metres (inverse of xy_to_hex)."""
    x = HEX_RADIUS_M * SQRT3 * (q + r / 2.0)
    y = HEX_RADIUS_M * 1.5 * r
    return x, y


def hexes_for_track(points: List[Tuple[float, float]],
                    origin: Dict[str, float]) -> List[Tuple[int, int]]:
    """Ordered, deduplicated hexes a GPS track passes through.

    Segments are sampled every HEX_RADIUS_M/2 metres so a fast/sparse
    track cannot skip over a hex; the last hex is the player's position.
    """
    if not points:
        return []
    xys = [to_xy(lat, lon, origin) for lat, lon in points]
    step = HEX_RADIUS_M / 2.0
    hexes: List[Tuple[int, int]] = []
    seen: set = set()

    def push(x: float, y: float) -> None:
        h = xy_to_hex(x, y)
        if h not in seen:
            seen.add(h)
            hexes.append(h)
        elif hexes and hexes[-1] != h:
            # revisiting an old hex still moves the "current position"
            hexes.append(h)

    push(*xys[0])
    for (x0, y0), (x1, y1) in zip(xys, xys[1:]):
        dist = math.hypot(x1 - x0, y1 - y0)
        for i in range(1, max(int(dist / step), 1) + 1):
            t = i / max(int(dist / step), 1)
            push(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t)

    # dedupe consecutive repeats introduced by the revisit rule
    out: List[Tuple[int, int]] = []
    for h in hexes:
        if not out or out[-1] != h:
            out.append(h)
    return out


def hex_to_latlon(q: int, r: int,
                  origin: Dict[str, float]) -> Tuple[float, float]:
    """Centre of an axial hex back in (lat, lon) — inverse of the ingestion
    projection, used to draw hex overlays on the real map."""
    x, y = hex_to_xy(q, r)
    lat = origin["lat"] + y / M_PER_DEG_LAT
    lon = origin["lon"] + x / (M_PER_DEG_LAT * math.cos(math.radians(origin["lat"])))
    return lat, lon


def simplify_track(points: List[Tuple[float, float]],
                   max_points: int = 80) -> List[Tuple[float, float]]:
    """Uniform decimation for map display (keeps first & last point).
    Good enough visually at running scales; keeps the cache tiny."""
    if len(points) <= max_points:
        return list(points)
    step = (len(points) - 1) / (max_points - 1)
    out = [points[round(i * step)] for i in range(max_points - 1)]
    out.append(points[-1])
    return out


def hex_distance(a: Tuple[int, int], b: Tuple[int, int]) -> int:
    dq, dr = a[0] - b[0], a[1] - b[1]
    return (abs(dq) + abs(dr) + abs(dq + dr)) // 2


def exploration_targets(visited: set, player: Tuple[int, int], seed: str,
                        count: int = 3, min_dist: int = 5,
                        max_dist: int = 8) -> List[Tuple[int, int]]:
    """Weekly beacons: unexplored hexes 5-8 hexes (~2-3.5 km) from the
    player, stable within a week (seeded draw) — concrete real-world
    targets that pull the player toward terra incognita."""
    candidates = []
    pq, pr = player
    for dq in range(-max_dist, max_dist + 1):
        for dr in range(-max_dist, max_dist + 1):
            cand = (pq + dq, pr + dr)
            if cand in visited:
                continue
            if min_dist <= hex_distance(cand, player) <= max_dist:
                candidates.append(cand)
    if not candidates:
        return []
    rng = random.Random(seed)
    candidates.sort()  # deterministic base order before the seeded draw
    return rng.sample(candidates, min(count, len(candidates)))


# -- Demo fallback ---------------------------------------------------------------

DEMO_ORIGIN = {"lat": 48.8566, "lon": 2.3522}
_OUTDOOR = {
    "running", "trail_running", "track_running", "cycling", "gravel_cycling",
    "mountain_biking", "hiking", "walking", "open_water_swimming",
    "stair_climbing", "mountaineering",
}


def demo_hexes(history: List[Dict[str, Any]]) -> Dict[str, List]:
    """Deterministic fake tracks for demo mode (demo activities carry no
    GPS): one persistent-direction hex walk per outdoor activity, each
    starting where the previous one ended — a connected little world.

    Returns {activityId: [(q, r), ...]} for outdoor activities, oldest
    first, so the caller can ingest it exactly like real tracks.
    """
    start = (0, 0)
    tracks: Dict[str, List] = {}
    for act in sorted(history, key=lambda a: a.get("startDate", "")):
        if act.get("activityType") not in _OUTDOOR:
            continue
        rng = random.Random(act.get("activityId"))
        # ~100 m covered per minute → hexes are ~R*sqrt(3) apart
        steps = max(int((act.get("durationMinutes") or 30) * 100
                        / (HEX_RADIUS_M * SQRT3)), 2)
        q, r = start
        heading = rng.randrange(6)
        track = [(q, r)]
        for _ in range(steps):
            if rng.random() > 0.7:  # 70 % chance to keep the heading
                heading = (heading + rng.choice((-1, 1))) % 6
            dq, dr = HEX_NEIGHBOURS[heading]
            q, r = q + dq, r + dr
            track.append((q, r))
        tracks[str(act.get("activityId"))] = track
        start = (q, r)
    return tracks
