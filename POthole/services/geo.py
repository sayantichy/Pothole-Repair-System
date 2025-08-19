import math, re

def normalize_address(addr: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", (addr or "").strip().lower())

def haversine_m(lat1, lon1, lat2, lon2):
    if None in (lat1,lon1,lat2,lon2): return None
    R = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2-lat1)
    dl = math.radians(lon2-lon1)
    a = math.sin(dphi/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*R*math.atan2(math.sqrt(a), math.sqrt(1-a))
