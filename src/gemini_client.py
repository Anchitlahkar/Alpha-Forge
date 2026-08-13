import time
import json
import re
from typing import Any
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from src.config import GEMINI_API_KEYS

def _category_list() -> str:
    """The exact category keys the ranker scores against, so Gemini cannot drift."""
    try:
        from src.config import load_scoring
        return ", ".join(load_scoring().get("categories", {}).keys())
    except Exception:
        return ("AI Research, Quantum Computing, Software Engineering, Semiconductors, "
                "Investing, Startups, Geopolitics, Consumer Tech")


class ArticleAnalysis(BaseModel):
    title: str = Field(description="The title of the insight")
    category: str = Field(description="One of the predefined categories")
    signal_score: float = Field(description="Signal score from 1 to 10")
    personal_relevance: float = Field(description="Personal relevance score from 1 to 10")
    why_it_matters: str = Field(description="Why this article matters")
    tldr: str = Field(description="A short TLDR summary")
    key_points: list[str] = Field(description="List of key points")
    action_items: list[str] = Field(description="List of action items")
    source_name: str = Field(description="Name of the source")
    source_url: str = Field(description="Original article URL")
    date: str = Field(description="Publication or retrieval date")

class DeduplicationItem(BaseModel):
    event: str = Field(description="Name of the underlying event or topic")
    summary: str = Field(description="A unified summary of the overlapping stories")
    original_indices: list[int] = Field(description="List of original article indices belonging to this group")

class DeduplicationResponse(BaseModel):
    groups: list[DeduplicationItem]

def repair_json(text: str) -> str:
    """Cleans up markdown artifacts and repairs common malformed JSON errors from LLMs."""
    text = text.strip()
    
    # Remove markdown code blocks if any
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```\s*", "", text)
    text = text.strip()
    
    # Locate first '{' and last '}' to strip surrounding text
    first_brace = text.find('{')
    last_brace = text.rfind('}')
    if first_brace != -1 and last_brace != -1:
        text = text[first_brace:last_brace+1]
        
    # Remove trailing commas before closing braces/brackets
    text = re.sub(r',\s*([\]}])', r'\1', text)
    
    # Replace actual unescaped newlines inside JSON string literals
    in_string = False
    escape = False
    chars = []
    for c in text:
        if c == '"' and not escape:
            in_string = not in_string
            chars.append(c)
        elif c == '\\' and in_string:
            escape = not escape
            chars.append(c)
        elif c == '\n' and in_string:
            chars.append('\\n')
            escape = False
        else:
            escape = False
            chars.append(c)
    text = "".join(chars)
    
    # Balance braces and brackets if truncated
    open_braces = text.count('{')
    close_braces = text.count('}')
    open_brackets = text.count('[')
    close_brackets = text.count(']')
    
    if open_braces > close_braces:
        text += '}' * (open_braces - close_braces)
    if open_brackets > close_brackets:
        text += ']' * (open_brackets - close_brackets)
        
    return text

RATE_LIMIT_MARKERS = ["RESOURCE_EXHAUSTED", "QUOTA_EXCEEDED", "429", "RATE LIMIT", "RATE_LIMIT"]

# Markers that mean the key is done for the day, not for the minute. A per-day
# quota will not recover inside a run, so waiting on it is pointless.
DAILY_QUOTA_MARKERS = ["PERDAY", "PER DAY", "PER_DAY", "REQUESTSPERDAY", "DAILY LIMIT"]

# Markers that mean the key is bad, not throttled. No amount of waiting helps.
DEAD_KEY_MARKERS = ["API_KEY_INVALID", "API KEY NOT VALID", "PERMISSION_DENIED", "UNAUTHENTICATED"]

DEFAULT_COOLDOWN_SECONDS = 60.0
# Ceiling on cumulative sleeping across a whole process, so a genuinely dry day
# ends the run instead of idling in CI for an hour.
MAX_TOTAL_WAIT_SECONDS = 300.0


def is_rate_limit_error(err: str) -> bool:
    return any(m in err.upper() for m in RATE_LIMIT_MARKERS)


def is_daily_quota_error(err: str) -> bool:
    return any(m in err.upper().replace("-", "") for m in DAILY_QUOTA_MARKERS)


def is_dead_key_error(err: str) -> bool:
    return any(m in err.upper() for m in DEAD_KEY_MARKERS)


def parse_retry_delay(err: str) -> float | None:
    """Gemini returns the wait it wants in the 429 body; honour it when present."""
    for pattern in (r"retryDelay['\"]?\s*[:=]\s*['\"]?(\d+(?:\.\d+)?)s",
                    r"retry[_ ]after['\"]?\s*[:=]\s*['\"]?(\d+(?:\.\d+)?)"):
        m = re.search(pattern, err, re.IGNORECASE)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                pass
    return None


class GeminiClientManager:
    """
    Rotates across keys and, when every key is throttled, waits for the soonest
    one to come back instead of aborting.

    Most free-tier 429s are per-minute, not per-day, so treating the last 429 as
    permanent exhaustion threw away a whole run while key 1 was already usable
    again. Keys are cooled down individually and reused; only per-day quota and
    genuinely bad keys are retired for the process.
    """

    def __init__(self, keys: list[str] | None = None, sleep=time.sleep, monotonic=time.monotonic):
        self.keys = list(GEMINI_API_KEYS if keys is None else keys)
        self._sleep = sleep
        self._monotonic = monotonic

        # index -> monotonic timestamp before which the key must not be used
        self.cooldown_until: dict[int, float] = {}
        # indices retired for this process (daily quota exhausted, or invalid)
        self.retired: set[int] = set()
        self.total_waited = 0.0

        print(f"Loaded {len(self.keys)} Gemini keys")
        for i, key in enumerate(self.keys):
            masked = key[:4] + "..." if len(key) > 4 else "xxxx..."
            print(f"Key {i + 1}: {masked}")
        print()

        # Keys are validated lazily. The old startup sweep spent one live request
        # per key on every import, which burned quota before any work and could
        # trip the very per-minute limit it was checking for.
        self.current_index = 0
        self.client = None
        self._init_client()

    def _init_client(self):
        if not self.keys or self.current_index >= len(self.keys):
            print("[Gemini] No API keys available.")
            self.client = None
            return
        print(f"[Gemini] Using key {self.current_index + 1}/{len(self.keys)}")
        self.client = genai.Client(api_key=self.keys[self.current_index])
        print("[Gemini] New client created\n")

    def _usable_now(self, i: int) -> bool:
        return i not in self.retired and self.cooldown_until.get(i, 0.0) <= self._monotonic()

    def mark_failed(self, error: str):
        """Record why the current key failed so rotation can pick sensibly."""
        i = self.current_index
        if is_dead_key_error(error):
            print(f"[Gemini] Key {i + 1} rejected (invalid credentials); retiring it")
            self.retired.add(i)
        elif is_daily_quota_error(error):
            print(f"[Gemini] Key {i + 1} out of daily quota; retiring it for this run")
            self.retired.add(i)
        else:
            delay = parse_retry_delay(error) or DEFAULT_COOLDOWN_SECONDS
            self.cooldown_until[i] = self._monotonic() + delay
            print(f"[Gemini] Key {i + 1} throttled; cooling down {delay:.0f}s")

    def rotate_key(self) -> bool:
        """
        Move to the next usable key. If every key is merely cooling down, wait
        for the soonest and carry on. Raises only when nothing can recover.
        """
        if not self.keys:
            raise RuntimeError("All Gemini API keys exhausted")

        n = len(self.keys)
        # Prefer a key that is ready right now, scanning forward from the current one.
        for step in range(1, n + 1):
            candidate = (self.current_index + step) % n
            if self._usable_now(candidate):
                self.current_index = candidate
                print(f"[Gemini] Rotating to key {candidate + 1}/{n}")
                self._init_client()
                return True

        # Nothing ready. Anything still cooling down?
        waiting = {i: t for i, t in self.cooldown_until.items()
                   if i not in self.retired and t > self._monotonic()}
        if not waiting:
            self.client = None
            raise RuntimeError("All Gemini API keys exhausted")

        soonest = min(waiting, key=lambda i: waiting[i])
        wait = max(0.0, waiting[soonest] - self._monotonic())

        if self.total_waited + wait > MAX_TOTAL_WAIT_SECONDS:
            self.client = None
            raise RuntimeError(
                f"All Gemini API keys exhausted (waited {self.total_waited:.0f}s, "
                f"next key needs {wait:.0f}s more)"
            )

        print(f"[Gemini] All {n} keys throttled; waiting {wait:.0f}s for key {soonest + 1}")
        self._sleep(wait)
        self.total_waited += wait
        self.cooldown_until.pop(soonest, None)
        self.current_index = soonest
        self._init_client()
        return True

client_manager = GeminiClientManager()

def call_gemini_structured(prompt: str, schema_model: type[BaseModel], model: str = "gemini-2.5-flash", retries: int = 3) -> Any:
    # Injecting the schema directly into the prompt to bypass SDK schema conversion bugs
    schema_json = json.dumps(schema_model.model_json_schema(), indent=2)
    full_prompt = (
        f"{prompt}\n\n"
        "IMPORTANT: You must return valid JSON that strictly conforms to the following JSON schema:\n"
        f"{schema_json}\n"
        "Return ONLY the JSON. No explanations, no markdown blocks."
    )

    while True:
        if not client_manager.client:
            print("[Gemini] No active client available.")
            return None
            
        is_rate_limited = False
        limit_error = ""
        parsed_data = None

        for attempt in range(retries):
            try:
                response = client_manager.client.models.generate_content(
                    model=model,
                    contents=full_prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.1,
                    )
                )
                
                if not response or not response.text:
                    continue

                cleaned_text = repair_json(response.text)
                parsed_data = schema_model.model_validate_json(cleaned_text)
                return parsed_data
            except Exception as e:
                err_str = str(e)
                print(f"Gemini API failure (attempt {attempt+1}): {err_str}")
                
                # Rate limits and bad credentials are key problems, not prompt
                # problems: stop retrying this key and let rotation handle it.
                if is_rate_limit_error(err_str) or is_dead_key_error(err_str):
                    is_rate_limited = True
                    limit_error = err_str
                    break
                else:
                    time.sleep(2 * (attempt + 1))

        if is_rate_limited:
            client_manager.mark_failed(limit_error)
            # Raises only when no key can recover; main.py treats that as fatal.
            client_manager.rotate_key()
            continue  # Retry the same prompt with the new key
        else:
            # Non-rate-limit errors exhausted all retries
            return None

def extract_insights(text: str, source_url: str, article_source_name: str = "", article_title: str = "", article_published: str = "") -> dict[str, Any] | None:
    prompt = f"""
    Analyze the following article text.
    Extract the core facts and insights. Determine a signal score (1-10) where 10 is groundbreaking and 1 is fluff.

    The category MUST be copied verbatim from this list, with no additions,
    qualifiers or slashes. Pick the single closest one:
    {_category_list()}
    Do not invent categories like "Quantum Computing Research" or
    "Semiconductors & Geopolitics"; those break scoring. Anything about markets,
    funds, banks, fintech or the economy goes under Investing.
    Determine a single personal relevance score (float from 1 to 10) representing the overall relevance to these topics: AI Research, Quantum Computing, Software Engineering, Semiconductors, Investing, Startups. Do NOT return a dictionary of individual scores.

    WHO YOU ARE WRITING FOR
    One person: a software engineer who follows AI research, quantum computing,
    semiconductors, startups and investing, and who reads this alone each morning.
    Write to him directly. Never address investors, companies, startups,
    researchers, developers, or "engineers" as a group.

    action_items: address him in the second person, and only include things he
    could start within an hour - a specific paper to read, a repo to clone, a
    name to look up, a number to check. Never write "monitor", "stay informed
    on", "assess the implications of", "explore the potential of", "keep an eye
    on", or "consider implementing"; those are not actions. If the article
    implies nothing concrete to do, return an empty list rather than filling it.

    why_it_matters: do not mention the article, announcement, development, or
    news, and do not open with "This". State the consequence directly, as a
    claim about the world, in at most two sentences. Do not assert that
    something is significant, important, critical, major, or a breakthrough -
    state the fact that makes it so and let him judge. If the consequence is
    uncertain, say what would have to be true for it to matter.

    STYLE
    - Do not use em-dashes anywhere.
    - Do not end tldr, why_it_matters, or any key point with a trailing "-ing"
      clause that restates the point at a higher level (", representing...",
      ", marking...", ", enabling...", ", highlighting...", ", underscoring...").
      End on the last fact.
    - Vary sentence length. At least one sentence under eight words per summary.
    - Banned words: significant, leverage, utilize, streamline, seamless,
      empower, robust, crucial, comprehensive, holistic, landscape, ecosystem,
      game-changing, cutting-edge, revolutionize, underscore, delve.
      Use the plain verb for the plain thing: "uses" not "utilizes",
      "simplified its interview process" not "streamlined hiring".
    - Prefer a number over an adjective. Where the source gives a figure, a date,
      a name, or a price, put it in the summary instead of describing its importance.
    - Use a vendor's coined term without quotation marks, and define it in the
      same sentence the first time it appears. If you cannot say what it means,
      leave it out.

    Article Title: {article_title}
    Source URL: {source_url}
    Source Name: {article_source_name}
    Date: {article_published}
    
    Text:
    {text[:15000]}
    """
    res = call_gemini_structured(prompt, ArticleAnalysis, model="gemini-2.5-flash")
    return res.model_dump() if res else None

def synthesize_weekly(daily_insights: list[dict]) -> str:
    prompt = f"""
    Synthesize the following daily insights from the past week into a comprehensive Weekly Deep Dive.
    Highlight the most important trends, cross-cutting themes, and actionable conclusions.
    Output formatted in Markdown.
    
    Insights:
    {json.dumps(daily_insights)}
    """
    while True:
        if not client_manager.client:
            return "Failed to generate weekly synthesis: Gemini is unavailable."
            
        try:
            response = client_manager.client.models.generate_content(
                model="gemini-2.5-pro",
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.3)
            )
            return response.text if response.text else "Synthesis empty."
        except Exception as e:
            err_str = str(e)
            print(f"Weekly synthesis error: {err_str}")
            if any(x in err_str.upper() for x in ["RESOURCE_EXHAUSTED", "QUOTA_EXCEEDED", "429", "RATE LIMIT", "RATE_LIMIT"]):
                has_next = client_manager.rotate_key()
                if not has_next:
                    print("All Gemini API keys exhausted.")
                    return "Failed to generate weekly synthesis: All Gemini keys exhausted."
                continue
            else:
                return "Failed to generate weekly synthesis due to API error."
