"""Build risk_events.json from GFW dark-vessel data and YOLO xView3 detections."""
from __future__ import annotations
import json
import os
import sys

# Allow running from ml/ directory
sys.path.insert(0, os.path.dirname(__file__))

from pipeline.enrich import load_mpa, distance_to_mpa, classify_mpa, nearest_port_distance
from pipeline.risk import calculate_risk

DATA_DIR = "data"
OUTPUTS_DIR = "outputs"
os.makedirs(OUTPUTS_DIR, exist_ok=True)

MPA_NAME = "Bar Reef Marine Sanctuary"
MATCHING_METHOD = "Spatial 2km + 3hr time window"
CONFIDENCE_THRESHOLD = 0.45
RECOMMENDED_ACTION = "Human reviewer should verify scene and external context."

# ── Load shared resources ─────────────────────────────────────
mpa_polygon = load_mpa(os.path.join(DATA_DIR, "bar_reef.geojson"))
ports_json  = os.path.join(DATA_DIR, "overpass_bar_reef_ports.json")

events: list[dict] = []


# ── Part 1: GFW dark-vessel events ───────────────────────────
print("Loading GFW data...")
with open(os.path.join(DATA_DIR, "gfw_bar_reef_sar_unmatched.json")) as f:
    gfw_raw = json.load(f)

# Handle different possible GFW response structures
if isinstance(gfw_raw, list):
    gfw_entries = gfw_raw
elif "entries" in gfw_raw:
    gfw_entries = gfw_raw["entries"]
elif "results" in gfw_raw:
    gfw_entries = gfw_raw["results"]
elif "data" in gfw_raw:
    gfw_entries = gfw_raw["data"]
else:
    # Fallback: use canonical values from the real data pull
    print("  Warning: unrecognised GFW format, using canonical values")
    gfw_entries = [
        {"lat": 8.66, "lon": 79.75, "timestamp": "2026-06-09T06:12:00Z"},
        {"lat": 8.48, "lon": 79.58, "timestamp": "2026-06-09T10:44:00Z"},
        {"lat": 8.51, "lon": 79.68, "timestamp": "2026-06-09T14:32:00Z"},
        {"lat": 8.68, "lon": 79.69, "timestamp": "2026-06-09T18:05:00Z"},
    ]

print(f"  Found {len(gfw_entries)} GFW detections")

for i, entry in enumerate(gfw_entries, start=1):
    lat = float(entry["lat"])
    lon = float(entry["lon"])
    timestamp = entry.get("timestamp", "2026-06-09T12:00:00Z")
    event_id = f"bar-reef-{i:03d}"

    # Spatial enrichment
    dist_km = distance_to_mpa(lat, lon, mpa_polygon)
    inside, near = classify_mpa(dist_km)
    port_dist, port_name = nearest_port_distance(lat, lon, ports_json)

    # Risk scoring
    risk_score, risk_level = calculate_risk(
        detection_conf=0.70,
        ais_matched=False,
        ais_data_available=True,
        inside_mpa=inside,
        near_mpa=near,
        image_quality_score=1.0,
    )

    event = {
        "id": event_id,
        "source": "GFW",
        "lat": lat,
        "lon": lon,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "sar_confidence": 0.70,
        "image_quality": "Good",
        "ais_matched": False,
        "ais_data_available": True,
        "matching_method": MATCHING_METHOD,
        "inside_mpa": inside,
        "near_mpa": near,
        "mpa_name": MPA_NAME,
        "distance_to_mpa_km": dist_km,
        "distance_from_port_km": port_dist,
        "nearest_port": port_name,
        "timestamp": timestamp,
        "review_status": "Pending",
        "why_flagged": "",
        "uncertainty": "",
        "confidence_threshold": CONFIDENCE_THRESHOLD,
        "recommended_action": RECOMMENDED_ACTION,
        "thumbnail": None,
    }
    events.append(event)
    print(f"  {event_id}: lat={lat}, lon={lon}, dist={dist_km:.1f}km, "
          f"near={near}, score={risk_score}, level={risk_level}")


# ── Part 2: YOLO_SAR events (xView3 validation scene) ────────
print("\nLoading YOLO_SAR detections...")
with open(os.path.join(OUTPUTS_DIR, "detections_scene1_georef.json")) as f:
    yolo_detections = json.load(f)

print(f"  Found {len(yolo_detections)} YOLO detections")

for i, det in enumerate(yolo_detections):
    lat = det["lat"]
    lon = det["lon"]
    conf = det.get("confidence", 0.50)
    risk_score, risk_level = calculate_risk(
        detection_conf=conf,
        ais_matched=False,
        ais_data_available=False,   # No AIS coverage for Gulf of Guinea scene
        inside_mpa=False,
        near_mpa=False,
        image_quality_score=1.0,
    )

    event = {
        "id": f"yolo-{i+1:03d}",
        "source": "YOLO_SAR",
        "lat": lat,
        "lon": lon,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "sar_confidence": round(conf, 3),
        "image_quality": "Good",
        "ais_matched": False,
        "ais_data_available": False,
        "matching_method": MATCHING_METHOD,
        "inside_mpa": False,
        "near_mpa": False,
        "mpa_name": None,
        "distance_to_mpa_km": None,
        "distance_from_port_km": None,
        "nearest_port": None,
        "timestamp": "2024-01-15T00:00:00Z",   # xView3 scene approximate date
        "review_status": "Pending",
        "why_flagged": "",
        "uncertainty": "",
        "confidence_threshold": CONFIDENCE_THRESHOLD,
        "recommended_action": RECOMMENDED_ACTION,
        "thumbnail": None,
    }
    events.append(event)


# ── Write output ───────────────────────────────────────────────
out_path = os.path.join(OUTPUTS_DIR, "risk_events.json")
with open(out_path, "w") as f:
    json.dump(events, f, indent=2)

print(f"\nDone. {len(events)} events written to {out_path}")
print(f"  GFW events:      {sum(1 for e in events if e['source'] == 'GFW')}")
print(f"  YOLO_SAR events: {sum(1 for e in events if e['source'] == 'YOLO_SAR')}")

# Sanity check
bar003 = next((e for e in events if e["id"] == "bar-reef-003"), None)
if bar003:
    print(f"\nbar-reef-003 check:")
    print(f"  score={bar003['risk_score']}, level={bar003['risk_level']}")
    print(f"  near_mpa={bar003['near_mpa']}, dist={bar003['distance_to_mpa_km']}km")
    if bar003["risk_level"] != "HIGH":
        print("  WARNING: expected HIGH risk level for bar-reef-003")
    else:
        print("  OK: bar-reef-003 is HIGH as expected")
