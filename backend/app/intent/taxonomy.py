"""F5 - Business type classification, sector taxonomy, and routing flags.

Produces the two booleans that drive dynamic routing (F10): `is_physical` and
`requires_operations`.

These flags are derived deterministically rather than trusted from the LLM,
because RQ2 ("does dynamic routing improve efficiency without degrading
quality?") compares a dynamic-routing run against an all-departments run on the
same prompt set. If the routing decision itself were stochastic, the two arms of
that experiment would not be comparable and the measured token savings would be
meaningless.
"""

from __future__ import annotations

import re

from app.models.intent import Sector

# Keyword -> sector. Tuned for Indian small-business vocabulary.
SECTOR_KEYWORDS: dict[Sector, tuple[str, ...]] = {
    Sector.FOOD_AND_BEVERAGE: (
        "ice cream", "icecream", "gelato", "kulfi", "bakery", "cafe", "coffee",
        "restaurant", "eatery", "dhaba", "tiffin", "cloud kitchen", "food truck",
        "juice", "smoothie", "chai", "tea stall", "sweet shop", "mithai",
        "catering", "dairy", "bar", "pub", "brewery", "pizzeria", "canteen",
        "confectionery", "chocolate", "snack", "biryani", "food",
    ),
    Sector.RETAIL: (
        "kirana", "grocery", "supermarket", "general store", "boutique",
        "clothing store", "apparel", "footwear", "shoe store", "stationery",
        "bookstore", "book shop", "mobile shop", "electronics store",
        "hardware store", "furniture store", "toy store", "gift shop",
        "jewellery", "jewelry", "optical", "pet shop", "nursery", "florist",
        "retail", "showroom", "d2c", "reseller",
    ),
    Sector.SERVICES: (
        "salon", "parlour", "parlor", "spa", "barber", "gym", "fitness",
        "yoga studio", "laundry", "dry clean", "car wash", "repair",
        "consulting", "consultancy", "agency", "travel agency", "tour operator",
        "event management", "wedding planner", "courier", "logistics",
        "real estate", "broker", "insurance", "accounting", "legal",
        "recruitment", "staffing", "cleaning", "pest control", "tailor",
        "service",
    ),
    Sector.TECHNOLOGY: (
        "saas", "software", "app", "mobile app", "web app", "platform",
        "marketplace", "fintech", "edtech", "healthtech", "ai ", "ml ",
        "startup", "it services", "web development", "cybersecurity",
        "cloud", "api", "dashboard", "crm", "erp", "chatbot",
    ),
    Sector.EDUCATION: (
        "coaching", "tuition", "tutoring", "tutor", "school", "preschool",
        "playschool", "daycare", "academy", "institute", "training centre",
        "training center", "test prep", "iit coaching", "neet coaching",
        "language class", "music class", "dance class", "skill development",
        "e-learning", "online course", "education",
    ),
    Sector.HEALTHCARE: (
        "clinic", "hospital", "pharmacy", "chemist", "medical store",
        "diagnostic", "pathology", "lab", "dental", "dentist", "physiotherapy",
        "ayurveda", "homeopathy", "nursing", "eye care", "veterinary",
        "wellness centre", "wellness center", "healthcare", "doctor",
    ),
    Sector.MANUFACTURING: (
        "manufacturing", "factory", "production unit", "plant", "assembly",
        "fabrication", "textile mill", "garment unit", "packaging unit",
        "processing unit", "workshop", "foundry", "printing press", "brewing",
    ),
    Sector.CREATIVE: (
        "design studio", "graphic design", "interior design", "photography",
        "photographer", "videography", "film production", "advertising",
        "media house", "content studio", "animation", "music production",
        "art studio", "gallery", "influencer", "podcast",
    ),
}

# Sectors whose businesses occupy premises and/or hold inventory by default.
_PHYSICAL_BY_DEFAULT: frozenset[Sector] = frozenset(
    {
        Sector.FOOD_AND_BEVERAGE,
        Sector.RETAIL,
        Sector.MANUFACTURING,
        Sector.HEALTHCARE,
        Sector.SERVICES,
        Sector.EDUCATION,
        Sector.CREATIVE,
    }
)

# Explicit signals that the business has no premises.
_DIGITAL_MARKERS: tuple[str, ...] = (
    "online", "virtual", "remote", "saas", "web-based", "web based",
    "mobile app", "app-based", "app based", "digital-only", "digital only",
    "e-learning", "elearning", "work from home", "cloud-based", "cloud based",
    "no storefront", "dropship",
)

# Overrides a digital marker: these still need physical fulfilment.
_PHYSICAL_OVERRIDE_MARKERS: tuple[str, ...] = (
    "cloud kitchen", "dark store", "warehouse", "delivery", "inventory",
    "hardware", "device", "manufacturing", "kitchen", "d2c",
)


def _contains(text: str, phrase: str) -> bool:
    if phrase.endswith(" "):  # e.g. "ai " must not match "airport"
        return phrase in text
    return re.search(rf"\b{re.escape(phrase)}", text) is not None


def classify_sector(text: str) -> tuple[Sector, str]:
    """Keyword-vote sector classification.

    Scored by (number of distinct keyword hits, longest hit). Hit count comes
    first because a single long keyword from the wrong sector should not outvote
    several corroborating signals: "saas platform for logistics" hits
    TECHNOLOGY twice (saas, platform) but SERVICES only once (logistics), even
    though "logistics" is the longest single match.

    Returns (sector, longest_matched_keyword). The keyword is reused as a
    business-type fallback when the LLM does not supply one.
    """
    lowered = text.lower()
    best_sector = Sector.UNSPECIFIED
    best_keyword = ""
    best_score: tuple[int, int] = (0, 0)

    for sector, keywords in SECTOR_KEYWORDS.items():
        hits = [kw for kw in keywords if _contains(lowered, kw)]
        if not hits:
            continue
        longest = max(hits, key=len)
        score = (len(hits), len(longest))
        if score > best_score:
            best_sector, best_keyword, best_score = sector, longest, score

    return best_sector, best_keyword.strip()


def derive_routing_flags(text: str, sector: Sector) -> tuple[bool, bool]:
    """F10 input - returns (is_physical, requires_operations).

    Operations is the only conditional department. It runs when the business
    occupies premises or moves physical goods, because its four agents
    (supply chain, staffing, tech stack, process flow) have nothing meaningful
    to produce for a one-person digital service.
    """
    lowered = text.lower()

    is_physical = sector in _PHYSICAL_BY_DEFAULT

    if sector is Sector.TECHNOLOGY:
        is_physical = False

    if any(_contains(lowered, marker) for marker in _DIGITAL_MARKERS):
        is_physical = False

    if any(_contains(lowered, marker) for marker in _PHYSICAL_OVERRIDE_MARKERS):
        is_physical = True

    if sector is Sector.MANUFACTURING:
        is_physical = True

    requires_operations = is_physical or sector is Sector.MANUFACTURING
    return is_physical, requires_operations


def fallback_business_type(text: str, matched_keyword: str) -> tuple[str, str]:
    """Derive (snake_case_type, human_label) without an LLM.

    Used when every provider is unavailable, so the pipeline still produces a
    usable intent instead of failing outright.
    """
    keyword = matched_keyword or ""
    if not keyword:
        # First two meaningful words of the prompt.
        words = re.findall(r"[a-zA-Z]+", text.lower())
        stop = {"a", "an", "the", "i", "want", "to", "start", "open", "my", "new", "in", "for"}
        meaningful = [w for w in words if w not in stop][:2]
        keyword = " ".join(meaningful) if meaningful else "unspecified"

    snake = re.sub(r"[^a-z0-9]+", "_", keyword.lower()).strip("_") or "unspecified"
    label = " ".join(word.capitalize() for word in keyword.split())
    return snake, label
