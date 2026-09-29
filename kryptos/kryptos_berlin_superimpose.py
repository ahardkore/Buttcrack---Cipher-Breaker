#!/usr/bin/env python3
"""BERLIN ALEXANDERPLATZ SUPERIMPOSITION ENGINE
Computes the exact location of 'Point X' in Berlin if the Kryptos coordinate
system from Langley is superimposed onto the Urania-Weltzeituhr at Alexanderplatz.
"""

import math

def calculate_coords(lat0, lon0, dy_meters, dx_meters):
    m_lat = 111270.0
    m_lon = 111413.0 * math.cos(math.radians(lat0))
    lat = lat0 + (dy_meters / m_lat)
    lon = lon0 + (dx_meters / m_lon)
    return lat, lon

def main():
    print("=" * 78)
    print(" SUPERIMPOSING KRYPTOS COORDINATES ONTO BERLIN (ALEXANDERPLATZ)")
    print("=" * 78)

    # 1. Langley baseline
    kryptos_lat, kryptos_lon = 38.952278, -77.145722
    k2_lat, k2_lon = 38.951806, -77.145556

    m_lat_langley = 111030.0
    m_lon_langley = 111413.0 * math.cos(math.radians(kryptos_lat))

    dy_langley = (k2_lat - kryptos_lat) * m_lat_langley # -52.41 m
    dx_langley = (k2_lon - kryptos_lon) * m_lon_langley # +14.38 m

    dist_langley = math.hypot(dy_langley, dx_langley)
    bearing_langley = (math.degrees(math.atan2(dx_langley, dy_langley)) + 360) % 360

    print("\n1. THE LANGLEY BASELINE:")
    print(f"   - Kryptos Center (Courtyard) : 38° 57' 08.2\" N, 77° 08' 44.6\" W ({kryptos_lat:.6f}, {kryptos_lon:.6f})")
    print(f"   - K2 Benchmark Marker ('X')   : 38° 57' 06.5\" N, 77° 08' 44.0\" W ({k2_lat:.6f}, {k2_lon:.6f})")
    print(f"   - Offset Vector (dy, dx)     : dy = {dy_langley:+.2f} m, dx = {dx_langley:+.2f} m")
    print(f"   - Distance & Bearing to X    : {dist_langley:.2f} m ({dist_langley*3.28084:.1f} ft) on bearing {bearing_langley:.1f}° (SSE)")

    # 2. Berlin Weltzeituhr Origin
    uhr_lat, uhr_lon = 52.521172, 13.413308
    print("\n2. THE BERLIN ORIGIN (WELTZEITUHR):")
    print(f"   - Center of Weltzeituhr      : 52° 31' 16.2\" N, 13° 24' 47.9\" E ({uhr_lat:.6f}, {uhr_lon:.6f})")
    print(f"   - Physical Foundation        : Stone Windrose (Compass Rose) Mosaic")

    # Transformation 1: Direct translation vector (same distance & bearing: 54.34m, 164.65° SSE)
    x1_lat, x1_lon = calculate_coords(uhr_lat, uhr_lon, dy_langley, dx_langley)
    print("\n3. CANDIDATE LOCATIONS FOR 'X' IN BERLIN:")
    print(f"   A. DIRECT VECTOR TRANSLATION (54.3 m, 164.7° SSE):")
    print(f"      Coordinates : 52° 31' 14.5\" N, 13° 24' 48.7\" E ({x1_lat:.6f}° N, {x1_lon:.6f}° E)")
    print(f"      Physical Spot: Central pedestrian plaza of Alexanderplatz, directly in front")
    print(f"                     of the historic Alexanderhaus and above the U-Bahn concourse.")

    # Transformation 2: Along K4 East-Northeast Azimuth (44.42°, 54.34m)
    dy_ne = dist_langley * math.cos(math.radians(44.42))
    dx_ne = dist_langley * math.sin(math.radians(44.42))
    x2_lat, x2_lon = calculate_coords(uhr_lat, uhr_lon, dy_ne, dx_ne)
    print(f"\n   B. ALIGNED WITH K4 BEARING (54.3 m, 44.4° ENE):")
    print(f"      Coordinates : 52° 31' 17.5\" N, 13° 24' 49.9\" E ({x2_lat:.6f}° N, {x2_lon:.6f}° E)")
    print(f"      Physical Spot: Northeast toward the Berolinahaus along the Alexanderstraße axis.")

    # Transformation 3: Reverse Azimuth toward Langley (224.42° SW, 54.34m)
    x3_lat, x3_lon = calculate_coords(uhr_lat, uhr_lon, -dy_ne, -dx_ne)
    print(f"\n   C. REVERSE AZIMUTH TOWARD LANGLEY (54.3 m, 224.4° WSW):")
    print(f"      Coordinates : 52° 31' 15.0\" N, 13° 24' 45.9\" E ({x3_lat:.6f}° N, {x3_lon:.6f}° E)")
    print(f"      Physical Spot: Southwest toward the base of the Berliner Fernsehturm (TV Tower).")

    print("\n4. THE COLD WAR MIRROR ('ONLY WW'):")
    print("   - Langley / West : William Webster (WW) — Director of Central Intelligence")
    print("   - Berlin / East  : Walter Womacka (WW) — Head of Alexanderplatz Design Team &")
    print("                      creator of the 'Brunnen der Völkerfreundschaft' (101 m away)")

if __name__ == "__main__":
    main()
