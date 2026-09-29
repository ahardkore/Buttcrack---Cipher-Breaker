#!/usr/bin/env python3
"""PARADIGM CYPHER OPENING DATE VS SOLAR SHADOW ALIGNMENT
Calculates the exact solar altitude, azimuth, and shadow direction at CIA Langley
(38.9523° N, 77.1457° W) on:
1. Dedication Day: November 3, 1990 (The First Ceremony)
2. Auction Day: November 20, 2025 (Sanborn's 80th Birthday & Archive Sale)
3. Paradigm CTF Opening: June 12, 2026 (The Public Cypher Launch)
"""

import math
from datetime import datetime, timedelta

def solar_pos_exact(lat, lon, dt_utc):
    rad = math.radians
    deg = math.degrees
    y, m, d = dt_utc.year, dt_utc.month, dt_utc.day
    h, mn, s = dt_utc.hour, dt_utc.minute, dt_utc.second
    if m <= 2:
        y -= 1
        m += 12
    A = math.floor(y / 100)
    B = 2 - A + math.floor(A / 4)
    jd = math.floor(365.25 * (y + 4716)) + math.floor(30.6001 * (m + 1)) + d + B - 1524.5
    jd += (h + mn/60.0 + s/3600.0) / 24.0
    n = jd - 2451545.0
    L = (280.460 + 0.9856474 * n) % 360.0
    g = (357.528 + 0.9856003 * n) % 360.0
    lambda_sun = (L + 1.915 * math.sin(rad(g)) + 0.020 * math.sin(rad(2 * g))) % 360.0
    eps = 23.439 - 0.0000004 * n
    alpha = deg(math.atan2(math.cos(rad(eps)) * math.sin(rad(lambda_sun)), math.cos(rad(lambda_sun))))
    delta = deg(math.asin(math.sin(rad(eps)) * math.sin(rad(lambda_sun))))
    gmst = (280.46061837 + 360.98564736629 * n) % 360.0
    lst = (gmst + lon) % 360.0
    H = (lst - alpha) % 360.0
    if H > 180: H -= 360
    sin_alt = math.sin(rad(lat)) * math.sin(rad(delta)) + math.cos(rad(lat)) * math.cos(rad(delta)) * math.cos(rad(H))
    alt = deg(math.asin(sin_alt))
    cos_az = (math.sin(rad(delta)) - math.sin(rad(lat)) * sin_alt) / (math.cos(rad(lat)) * math.cos(rad(alt)))
    cos_az = max(-1.0, min(1.0, cos_az))
    az = deg(math.acos(cos_az))
    if math.sin(rad(H)) > 0:
        az = 360.0 - az
    shadow_az = (az + 180.0) % 360.0
    return alt, az, shadow_az

lat_cia = 38.9523
lon_cia = -77.1457

# Target vectors:
TARGET_BERLIN = 44.42   # East-Northeast
TARGET_K2     = 164.7   # East-Southeast / South-Southeast

dates = [
    ("Dedication Day (First Ceremony)", 1990, 11, 3, 5),   # EST (UTC-5)
    ("RR Auction Day (80th Birthday)", 2025, 11, 20, 5),  # EST (UTC-5)
    ("Paradigm Cypher Opening Day",   2026, 6,  12, 4),   # EDT (UTC-4)
    ("Summer Solstice 2026",          2026, 6,  21, 4),   # EDT (UTC-4)
    ("Berlin Wall Speech Anniv (1987)", 1987, 6, 12, 4)   # EDT (UTC-4)
]

print("=" * 80)
print("ASTRONOMICAL SOLAR SHADOW SIMULATION AT CIA LANGLEY COURTYARD")
print("=" * 80)

for event_name, y, m, d, tz_offset in dates:
    print(f"\n--- {event_name}: {y:04d}-{m:02d}-{d:02d} (UTC-{tz_offset}) ---")
    best_berlin = (999, None, None, None)
    best_k2 = (999, None, None, None)
    
    # Sweep through day minute by minute
    for minute_of_day in range(5 * 60, 20 * 60):
        h = minute_of_day // 60
        mn = minute_of_day % 60
        dt_utc = datetime(y, m, d, h, mn) + timedelta(hours=tz_offset)
        alt, az, sh = solar_pos_exact(lat_cia, lon_cia, dt_utc)
        if alt <= 0: continue
        
        diff_b = min(abs(sh - TARGET_BERLIN), 360 - abs(sh - TARGET_BERLIN))
        diff_k = min(abs(sh - TARGET_K2), 360 - abs(sh - TARGET_K2))
        
        if diff_b < best_berlin[0]:
            best_berlin = (diff_b, h, mn, alt, az, sh)
        if diff_k < best_k2[0]:
            best_k2 = (diff_k, h, mn, alt, az, sh)
            
    # Report best alignments
    print(f"  Target 1: 44.4° NE (Berlin Clock Sighting Vector):")
    diff, h, mn, alt, az, sh = best_berlin
    shadow_len_12ft = 12.0 / math.tan(math.radians(alt))
    print(f"    Exact Time: {h:02d}:{mn:02d} (Local) | Sun Alt: {alt:4.1f}° | Sun Az: {az:5.1f}° | "
          f"Shadow Az: {sh:5.2f}° (Error: {diff:.2f}°) | 12ft Shadow Length: {shadow_len_12ft:5.1f} ft")
          
    print(f"  Target 2: 164.7° SSE (K2 Survey Marker Sighting Vector):")
    diff, h, mn, alt, az, sh = best_k2
    shadow_len_12ft = 12.0 / math.tan(math.radians(alt))
    print(f"    Exact Time: {h:02d}:{mn:02d} (Local) | Sun Alt: {alt:4.1f}° | Sun Az: {az:5.1f}° | "
          f"Shadow Az: {sh:5.2f}° (Error: {diff:.2f}°) | 12ft Shadow Length: {shadow_len_12ft:5.1f} ft")
