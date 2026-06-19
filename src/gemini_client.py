import time
import json
import re
from typing import Any
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from src.config import GEMINI_API_KEYS

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

class GeminiClientManager:
    def __init__(self):
        self.keys = GEMINI_API_KEYS
        self.current_index = 0
        self.client = None
        self._init_client()

    def _init_client(self):
        if not self.keys:
            print("[Gemini] No API keys available.")
            self.client = None
            return
        if self.current_index >= len(self.keys):
            self.client = None
            return
        key = self.keys[self.current_index]
        print(f"[Gemini]\nUsing Key #{self.current_index + 1}\n")
        self.client = genai.Client(api_key=key)

    def rotate_key(self) -> bool:
        if not self.keys:
            return False
        print(f"[Gemini]\nKey #{self.current_index + 1} exhausted\n")
        self.current_index += 1
        if self.current_index < len(self.keys):
            print(f"[Gemini]\nSwitching to Key #{self.current_index + 1}\n")
            self._init_client()
            return True
        else:
            print("[Gemini] All keys exhausted.")
            self.client = None
            return False

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
                
                # Check for rate-limiting errors
                if any(x in err_str.upper() for x in ["RESOURCE_EXHAUSTED", "QUOTA_EXCEEDED", "429", "RATE LIMIT", "RATE_LIMIT"]):
                    is_rate_limited = True
                    break  # Break out of attempts loop to rotate key
                else:
                    time.sleep(2 * (attempt + 1))
        
        if is_rate_limited:
            has_next = client_manager.rotate_key()
            if not has_next:
                print("All Gemini API keys exhausted.")
                return None
            continue  # Retry with the new key in the outer loop
        else:
            # Non-rate-limit errors exhausted all retries
            return None

def extract_insights(text: str, source_url: str, article_source_name: str = "", article_title: str = "", article_published: str = "") -> dict[str, Any] | None:
    prompt = f"""
    Analyze the following article text.
    Extract the core facts and insights. Determine a signal score (1-10) where 10 is groundbreaking and 1 is fluff.
    Determine personal relevance (1-10) based on these topics: AI Research, Quantum Computing, Software Engineering, Semiconductors, Investing, Startups.
    
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
