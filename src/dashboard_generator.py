import glob
import os
import json
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse

import markdown
from jinja2 import Environment, FileSystemLoader

from src.config import TEMPLATES_DIR, DASHBOARD_DIR, WEEKLY_DIR, DAILY_DIR
from src.utils import get_today_str

# How many items get the full card treatment. The rest are listed, not repeated.
TOP_N = 5


def _parse_date(raw: str):
    """Feeds emit RFC-822, ISO-8601 with Z, and bare dates. Accept all three."""
    if not raw:
        return None
    raw = str(raw).strip()
    try:
        return parsedate_to_datetime(raw)
    except Exception:
        pass
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except Exception:
        pass
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(raw, fmt)
        except Exception:
            continue
    return None


def _source_label(entry: str) -> str:
    """A merged source is either a bare URL or a titled reference. Show each as itself."""
    entry = str(entry).strip()
    if entry.startswith("http://") or entry.startswith("https://"):
        host = urlparse(entry).netloc
        return host[4:] if host.startswith("www.") else host
    return entry


def _normalize(insight: dict, today: datetime) -> dict:
    """
    Older archives use `facts`/`takeaways` and carry no source_url, date, or
    why_it_matters. Re-rendering one of those days must not produce blank cards,
    so map the old shape onto the current one on read.
    """
    item = dict(insight)

    if not item.get("key_points"):
        item["key_points"] = item.get("facts") or []
    if not item.get("action_items"):
        item["action_items"] = item.get("takeaways") or []

    raw_sources = [s for s in (item.get("sources") or []) if s]

    # Pre-2026-06-19 records have no source_url; the first URL in `sources` is the real link.
    if not item.get("source_url"):
        for entry in raw_sources:
            if str(entry).startswith("http"):
                item["source_url"] = entry
                break

    item["source_host"] = _source_label(item["source_url"]) if item.get("source_url") else ""

    # Only the merged citations beyond the primary link are worth listing.
    primary = item.get("source_url")
    item["merged_sources"] = [_source_label(s) for s in raw_sources if s != primary]

    published = _parse_date(item.get("date"))
    if published:
        if published.tzinfo is None:
            published = published.replace(tzinfo=timezone.utc)
        item["published_display"] = published.strftime("%-d %b") if os.name != "nt" else published.strftime("%#d %b")
        item["age_days"] = (today - published).days
    else:
        item["published_display"] = ""
        item["age_days"] = None

    # The classifier's raw feed bucket is only interesting where it disagrees
    # with the display category. Otherwise it is the same word twice.
    original = item.get("original_category") or ""
    item["show_original_category"] = bool(original) and original != item.get("category")

    return item


def _latest_archive_before(today_str: str):
    """
    Most recent daily archive that actually holds insights, ignoring today's.
    Used when a run produces nothing so the page falls back instead of emptying.
    """
    candidates = []
    for path in glob.glob(str(DAILY_DIR / "*.json")):
        stem = os.path.splitext(os.path.basename(path))[0]
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", stem) or stem >= today_str:
            continue
        candidates.append((stem, path))

    for stem, path in sorted(candidates, reverse=True):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"Could not read archive {path}: {e}")
            continue
        if data:
            return data, stem
    return [], None


def _dedupe_by_title(insights: list[dict]) -> list[dict]:
    seen = set()
    out = []
    for item in insights:
        key = re.sub(r"\s+", " ", str(item.get("title", ""))).strip().lower()
        if key and key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def generate_dashboard(insights: list[dict], run_stats: dict | None = None):
    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
    template = env.get_template("dashboard.html")

    today_str = get_today_str()
    today_dt = datetime.now(timezone.utc)

    # If today produced nothing, show the last day that did rather than an empty page.
    showing_date = today_str
    stale_from = None
    if not insights:
        insights, fallback_date = _latest_archive_before(today_str)
        if fallback_date:
            stale_from = fallback_date
            showing_date = fallback_date
            print(f"No insights today; falling back to archive from {fallback_date}")

    insights = _dedupe_by_title(insights or [])
    sorted_insights = sorted(insights, key=lambda x: x.get("final_score", 0), reverse=True)
    normalized = [_normalize(item, today_dt) for item in sorted_insights]

    top_insights = normalized[:TOP_N]
    # Everything below the fold is the REMAINDER. Nothing here appears above.
    remainder = normalized[TOP_N:]

    stale_days = None
    if stale_from:
        parsed = _parse_date(stale_from)
        if parsed:
            stale_days = (today_dt - parsed.replace(tzinfo=timezone.utc)).days

    weekly_files = glob.glob(str(WEEKLY_DIR / "*.md"))
    weekly_content = ""
    if weekly_files:
        latest_weekly = max(weekly_files, key=os.path.getctime)
        with open(latest_weekly, "r", encoding="utf-8") as f:
            weekly_content = markdown.markdown(f.read())

    html_content = template.render(
        date=showing_date,
        generated_on=today_str,
        stale_from=stale_from,
        stale_days=stale_days,
        top_insights=top_insights,
        remainder=remainder,
        total_count=len(normalized),
        weekly_content=weekly_content,
        run_stats=run_stats or {},
    )

    output_path = DASHBOARD_DIR / "index.html"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"Dashboard generated at {output_path}")
