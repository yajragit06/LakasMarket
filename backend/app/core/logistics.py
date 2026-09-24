"""Distance-fair logistics engine.

Computes a fair delivery fee between two Brunei districts using an approximate
road-distance matrix (km) and a simple base + per-km tariff. This ends the
entitlement that a seller in Bandar should deliver to Seria/KB for free.
"""
from app.models.enums import District

# Approximate one-way road distances (km) between district centres.
# Symmetric matrix; only the meaningful pairs are represented.
_DISTANCE_KM: dict[frozenset[District], float] = {
    frozenset({District.BANDAR, District.BRUNEI_MUARA}): 8,
    frozenset({District.BANDAR, District.TUTONG}): 48,
    frozenset({District.BANDAR, District.SERIA}): 95,
    frozenset({District.BANDAR, District.KUALA_BELAIT}): 100,
    frozenset({District.BANDAR, District.TEMBURONG}): 65,
    frozenset({District.BRUNEI_MUARA, District.TUTONG}): 45,
    frozenset({District.BRUNEI_MUARA, District.SERIA}): 92,
    frozenset({District.BRUNEI_MUARA, District.KUALA_BELAIT}): 97,
    frozenset({District.BRUNEI_MUARA, District.TEMBURONG}): 62,
    frozenset({District.TUTONG, District.SERIA}): 50,
    frozenset({District.TUTONG, District.KUALA_BELAIT}): 55,
    frozenset({District.TUTONG, District.TEMBURONG}): 105,
    frozenset({District.SERIA, District.KUALA_BELAIT}): 12,
    frozenset({District.SERIA, District.TEMBURONG}): 150,
    frozenset({District.KUALA_BELAIT, District.TEMBURONG}): 160,
}

# Tariff (BND). A short local hop stays cheap; long hauls to Belait cost fairly.
BASE_FEE = 3.0
PER_KM = 0.15
# Distances at or below this are treated as "same neighbourhood" — no fee.
FREE_RADIUS_KM = 10.0


def distance_km(a: District, b: District) -> float:
    if a == b:
        return 0.0
    return _DISTANCE_KM.get(frozenset({a, b}), 50.0)  # conservative default


def delivery_fee(seller: District, buyer: District) -> float:
    """Return a fair one-way delivery fee (BND) for a seller->buyer route."""
    km = distance_km(seller, buyer)
    if km <= FREE_RADIUS_KM:
        return 0.0
    return round(BASE_FEE + km * PER_KM, 2)
