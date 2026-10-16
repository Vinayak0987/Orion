"""F3 - Location parsing and normalization.

A small gazetteer, not an LLM. Two reasons:

1. Google Places (F38) is queried with `Location.query_string`. A hallucinated
   locality returns zero competitors, which would silently destroy the
   Competitor Coverage Rate (F55) - the headline metric for RQ3.
2. The evaluation set (evaluation/prompts.json) reuses the same localities across
   prompts. Deterministic normalization means the same locality always produces
   the same Places query, so cached results stay valid and the run is repeatable.

The gazetteer covers Mumbai (the project's primary evaluation region) plus major
Indian metros. Unknown localities fall through to the LLM's suggestion.
"""

from __future__ import annotations

import re

from app.generation.models.intent import Location

# Primary evaluation region. Lowercase keys.
MUMBAI_LOCALITIES: frozenset[str] = frozenset(
    {
        "andheri", "bandra", "borivali", "byculla", "chembur", "colaba",
        "dadar", "dahisar", "dharavi", "fort", "ghatkopar", "girgaon",
        "goregaon", "grant road", "juhu", "kandivali", "khar", "kurla",
        "lower parel", "malad", "marine lines", "matunga", "mahim",
        "mira road", "mulund", "nariman point", "parel", "powai",
        "prabhadevi", "santacruz", "sion", "vasai", "versova", "vikhroli",
        "vile parle", "virar", "wadala", "worli", "bhandup", "kanjurmarg",
        "marol", "sakinaka", "seepz", "bkc", "bandra kurla complex",
        "churchgate", "cst", "masjid bunder", "antop hill", "chunabhatti",
    }
)

# city keyword -> (canonical city, state)
CITIES: dict[str, tuple[str, str]] = {
    "navi mumbai": ("Navi Mumbai", "Maharashtra"),
    "mumbai": ("Mumbai", "Maharashtra"),
    "bombay": ("Mumbai", "Maharashtra"),
    "thane": ("Thane", "Maharashtra"),
    "pune": ("Pune", "Maharashtra"),
    "nashik": ("Nashik", "Maharashtra"),
    "nagpur": ("Nagpur", "Maharashtra"),
    "new delhi": ("New Delhi", "Delhi"),
    "delhi": ("Delhi", "Delhi"),
    "gurgaon": ("Gurugram", "Haryana"),
    "gurugram": ("Gurugram", "Haryana"),
    "noida": ("Noida", "Uttar Pradesh"),
    "bengaluru": ("Bengaluru", "Karnataka"),
    "bangalore": ("Bengaluru", "Karnataka"),
    "hyderabad": ("Hyderabad", "Telangana"),
    "chennai": ("Chennai", "Tamil Nadu"),
    "kolkata": ("Kolkata", "West Bengal"),
    "ahmedabad": ("Ahmedabad", "Gujarat"),
    "surat": ("Surat", "Gujarat"),
    "jaipur": ("Jaipur", "Rajasthan"),
    "indore": ("Indore", "Madhya Pradesh"),
    "lucknow": ("Lucknow", "Uttar Pradesh"),
    "kochi": ("Kochi", "Kerala"),
    "coimbatore": ("Coimbatore", "Tamil Nadu"),
    "chandigarh": ("Chandigarh", "Chandigarh"),
}

DEFAULT_CITY = "Mumbai"
DEFAULT_STATE = "Maharashtra"

# Directional qualifiers that are part of the locality name ("Andheri West").
_DIRECTION = r"(?:\s+(?:east|west|north|south))?"


def _title_case(value: str) -> str:
    """'andheri west' -> 'Andheri West'; preserves known acronyms."""
    acronyms = {"bkc", "cst", "seepz"}
    return " ".join(
        word.upper() if word.lower() in acronyms else word.capitalize()
        for word in value.split()
    )


def find_locality(text: str) -> tuple[str, str] | None:
    """Return (normalized_area, matched_raw_text) or None."""
    lowered = text.lower()
    # Longest first so "bandra kurla complex" beats "bandra".
    for locality in sorted(MUMBAI_LOCALITIES, key=len, reverse=True):
        pattern = re.compile(rf"\b{re.escape(locality)}{_DIRECTION}\b", re.IGNORECASE)
        match = pattern.search(lowered)
        if match:
            matched = match.group(0)
            return _title_case(matched), matched
    return None


def find_city(text: str) -> tuple[str, str, str] | None:
    """Return (canonical_city, state, matched_raw_text) or None."""
    lowered = text.lower()
    for keyword in sorted(CITIES, key=len, reverse=True):
        if re.search(rf"\b{re.escape(keyword)}\b", lowered):
            city, state = CITIES[keyword]
            return city, state, keyword
    return None


def parse_location(
    text: str,
    llm_area: str = "",
    llm_city: str = "",
    llm_state: str = "",
) -> Location:
    """Normalize a location from the raw prompt, using LLM hints only as backup.

    Resolution order:
      1. Known locality in the prompt (gazetteer)   -> highest confidence
      2. Known city in the prompt                   -> city-level only
      3. LLM-suggested area / city                  -> unverified fallback
      4. Project default (Mumbai, Maharashtra)
    """
    locality = find_locality(text)
    city_hit = find_city(text)

    area = "unspecified"
    raw_parts: list[str] = []

    if locality is not None:
        area, raw = locality
        raw_parts.append(raw)
    elif llm_area and llm_area.strip().lower() not in ("", "unspecified", "none", "null"):
        area = _title_case(llm_area.strip())
        raw_parts.append(llm_area.strip())

    if city_hit is not None:
        city, state, raw_city = city_hit
        raw_parts.append(raw_city)
    elif locality is not None:
        # A known Mumbai locality implies Mumbai even when the city is unstated.
        city, state = DEFAULT_CITY, DEFAULT_STATE
    elif llm_city.strip():
        resolved = CITIES.get(llm_city.strip().lower())
        if resolved is not None:
            city, state = resolved
        else:
            city = _title_case(llm_city.strip())
            state = llm_state.strip() or DEFAULT_STATE
    else:
        city, state = DEFAULT_CITY, DEFAULT_STATE

    return Location(
        area=area,
        city=city,
        state=state,
        country="India",
        raw=", ".join(dict.fromkeys(raw_parts)),
    )
