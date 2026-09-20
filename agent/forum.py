"""Money and jurisdiction are computed here, in Python. The model never does this."""
from agent.data import load


def compute(amount_inr: int | None) -> dict:
    rules = load("cpa_rules")
    years = rules.get("limitation", {}).get("years", 2)

    if amount_inr is None:
        f = _forum_for(rules, 0)
        return {"forum": f["name"], "forum_id": f["id"], "fee_inr": 0,
                "limitation_years": years, "amount_unknown": True}

    f = _forum_for(rules, amount_inr)
    return {"forum": f["name"], "forum_id": f["id"], "fee_inr": _fee_for(rules, amount_inr),
            "limitation_years": years}


def _forum_for(rules: dict, amount: int) -> dict:
    forums = rules["forums"]
    for f in forums:
        lo = f.get("min_inr") or 0
        hi = f.get("max_inr")
        if amount >= lo and (hi is None or amount <= hi):
            return f
    return forums[-1]  # above every ceiling -> National


def _fee_for(rules: dict, amount: int) -> int:
    for slab in sorted(rules["fee_slabs"], key=lambda s: s.get("max_inr") or float("inf")):
        hi = slab.get("max_inr")
        if hi is None or amount <= hi:
            return int(slab["fee_inr"])
    return int(rules["fee_slabs"][-1]["fee_inr"])
