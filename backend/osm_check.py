"""
One-minute diagnostic for the free hospital search. Run from the backend folder:
    python osm_check.py
It prints what each free server answers, so we can see exactly what is failing.
"""
import requests

from app.services.integrations import osm_places as osm

HEAD = {"User-Agent": osm.USER_AGENT}
print("1) Location service (Nominatim): PIN 400001")
try:
    lat, lon = osm.geocode("400001", None)
    print("   OK ->", lat, lon)
except Exception as exc:
    print("   FAILED ->", type(exc).__name__, exc)
    raise SystemExit

query = osm.build_overpass_query("eye", lat, lon, 5000, emergency=False)
print("\n2) Hospital servers (Overpass). Query sent:\n  ", query)
for url in osm.OVERPASS_URLS:
    try:
        r = requests.post(url, data={"data": query}, headers=HEAD, timeout=15)
        print(f"   {url}\n     status={r.status_code}  bytes={len(r.content)}")
        if r.status_code == 200:
            print("     eye facilities found:", len(r.json().get("elements", [])))
        else:
            print("     body starts:", r.text[:300].replace("\n", " "))
    except Exception as exc:
        print(f"   {url}\n     FAILED -> {type(exc).__name__}: {exc}")

print("\n3) Fallback (Nominatim category search)")
try:
    found = osm._nominatim_nearby("eye", lat, lon)
    print("   OK ->", len(found), "result(s)")
    for p in found[:5]:
        print("    -", p["name"], f'({p["distance_km"]} km)')
except Exception as exc:
    print("   FAILED ->", type(exc).__name__, exc)
