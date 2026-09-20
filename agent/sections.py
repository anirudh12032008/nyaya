"""Section-ID guard: a draft may only cite IDs that exist in data/*.json."""
import re
from functools import lru_cache

from agent.data import load

_SOURCES = {  # module -> (json file, key holding the list)
    "consumer": ("cpa_rules", "sections"),
    "police": ("bns_sections", "sections"),
    "tenant": ("tenancy_rules", "rules"),
    "labour": ("labour_rules", "sections"),
}


def norm(sid: str) -> str:
    """'Section 2(7)' / 's. 2 (7)' / 'BNSS  173' -> '2(7)' / 'bnss 173' (lowercase, tight)."""
    s = re.sub(r"^\s*(sections?|secs?\.?|s\.)\s*", "", str(sid).strip(), flags=re.I)
    return re.sub(r"\s+", " ", s.replace(" (", "(")).strip().lower()


@lru_cache(maxsize=None)
def _by_norm(module: str) -> dict:
    if module not in _SOURCES:
        return {}
    name, key = _SOURCES[module]
    return {norm(e["id"]): e for e in load(name).get(key, [])}


def valid_ids(module: str) -> set[str]:
    return set(_by_norm(module))


def entries(module: str) -> list[dict]:
    return list(_by_norm(module).values())


def filter_sections(module: str, sections: list) -> tuple[list, list]:
    """-> (kept, dropped_ids). Sections may be dicts with an 'id' or bare id strings."""
    ok = _by_norm(module)
    kept, dropped = [], []
    for s in sections or []:
        sid = s.get("id") if isinstance(s, dict) else s
        if norm(sid or "") in ok:
            kept.append(s)
        else:
            dropped.append(sid)
    return kept, dropped
