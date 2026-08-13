import re

from src.config import load_scoring

# The old shape hid a category term inside "personal":
#   adjusted = (personal + category) / 2
#   final    = signal*0.7 + adjusted*0.3
# which expands to signal*0.7 + personal*0.15 + category*0.15. The config said
# "personal: 0.3" while only half of that was actually personal. The three terms
# are now explicit and tunable; these defaults reproduce the old numbers exactly.
DEFAULT_WEIGHTS = {"signal": 0.7, "personal": 0.15, "category": 0.15}

# Used when a category cannot be resolved to a configured one.
FALLBACK_CATEGORY_WEIGHT = 5

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokens(value: str) -> set[str]:
    return set(_TOKEN_RE.findall(str(value).lower()))


def _clamp(value, low=1.0, high=10.0) -> float:
    """Gemini occasionally returns out-of-range or non-numeric scores."""
    try:
        value = float(value)
    except (TypeError, ValueError):
        return low
    return max(low, min(high, value))


def resolve_category_weight(raw_category: str, categories: dict) -> tuple[float, str]:
    """
    Gemini writes categories freehand, so it returns things like
    "Quantum Computing Research", "Semiconductors & Geopolitics" and
    "Platform Engineering / Data Management" that match no key in scoring.json.
    Those used to fall through to a flat 5, which silently discarded the
    category weights for roughly a third of all articles.

    Resolution order: exact (case-insensitive), then containment, then token
    overlap. Ties and multi-topic categories resolve to the highest-weighted
    match, since an article about two subjects is at least as relevant as one
    about the lower-weighted of them.

    Returns (weight, resolved_name); resolved_name is "" when nothing matched.
    """
    raw = str(raw_category or "").strip()
    if not raw or not categories:
        return FALLBACK_CATEGORY_WEIGHT, ""

    lookup = {name.lower(): name for name in categories}

    exact = lookup.get(raw.lower())
    if exact:
        return categories[exact], exact

    raw_lower = raw.lower()
    contained = [
        name for key, name in lookup.items()
        if key in raw_lower or raw_lower in key
    ]
    if contained:
        best = max(contained, key=lambda n: categories[n])
        return categories[best], best

    raw_tokens = _tokens(raw)
    overlapping = [
        name for name in categories
        if _tokens(name) & raw_tokens
    ]
    if overlapping:
        best = max(overlapping, key=lambda n: (len(_tokens(n) & raw_tokens), categories[n]))
        return categories[best], best

    return FALLBACK_CATEGORY_WEIGHT, ""


def rank_insights(insights: list[dict]) -> list[dict]:
    scoring_config = load_scoring()
    categories = scoring_config.get("categories", {})

    configured = scoring_config.get("weights", {}) or {}
    weights = dict(DEFAULT_WEIGHTS)
    if "category" in configured:
        weights.update({k: v for k, v in configured.items() if k in weights})
    else:
        # Legacy two-term config: split "personal" across personal and category.
        personal = configured.get("personal", DEFAULT_WEIGHTS["personal"] * 2)
        weights["signal"] = configured.get("signal", DEFAULT_WEIGHTS["signal"])
        weights["personal"] = personal / 2
        weights["category"] = personal / 2

    unresolved = []

    for insight in insights:
        signal_score = _clamp(insight.get("signal_score", 0))
        personal = _clamp(insight.get("personal_relevance", 0))

        raw_category = insight.get("category") or ""
        cat_weight, resolved = resolve_category_weight(raw_category, categories)
        if not resolved and raw_category:
            unresolved.append(raw_category)

        # Record what the ranking actually used, so the decision is inspectable.
        insight["category_weight"] = cat_weight
        insight["category_resolved"] = resolved or None

        final_score = (
            signal_score * weights["signal"]
            + personal * weights["personal"]
            + cat_weight * weights["category"]
        )
        insight["final_score"] = round(final_score, 2)

    if unresolved:
        print(
            f"⚠️ {len(unresolved)} article(s) had no matching category in scoring.json "
            f"and used the fallback weight {FALLBACK_CATEGORY_WEIGHT}: "
            f"{', '.join(sorted(set(unresolved)))}"
        )

    insights.sort(key=lambda x: x.get("final_score", 0), reverse=True)
    return insights
