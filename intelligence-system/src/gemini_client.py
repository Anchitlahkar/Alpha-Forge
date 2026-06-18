import time
import json
from typing import Any
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from src.config import GEMINI_API_KEY

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is not set.")

client = genai.Client(api_key=GEMINI_API_KEY)

class ArticleAnalysis(BaseModel):
    title: str = Field(description="The title of the insight")
    category: str = Field(description="One of the predefined categories")
    signal_score: int = Field(description="Signal score from 1 to 10")
    personal_relevance: int = Field(description="Personal relevance score from 1 to 10")
    tldr: str = Field(description="A short TLDR summary")
    facts: list[str] = Field(description="List of key facts extracted")
    takeaways: list[str] = Field(description="List of actionable takeaways")
    sources: list[str] = Field(description="List of source URLs or names")

class DeduplicationItem(BaseModel):
    event: str = Field(description="Name of the underlying event or topic")
    summary: str = Field(description="A unified summary of the overlapping stories")
    original_indices: list[int] = Field(description="List of original article indices belonging to this group")

class DeduplicationResponse(BaseModel):
    groups: list[DeduplicationItem]

def call_gemini_structured(prompt: str, schema_model: type[BaseModel], model: str = "gemini-2.5-flash", retries: int = 3) -> Any:
    for attempt in range(retries):
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=schema_model,
                    temperature=0.2
                )
            )
            # Some versions return an object that can be converted to dict directly
            if hasattr(response, 'parsed'):
                return response.parsed
            return json.loads(response.text)
        except Exception as e:
            print(f"Gemini API error (attempt {attempt+1}): {e}")
            if attempt < retries - 1:
                time.sleep(2 * (attempt + 1))
    return None

def extract_insights(text: str, source_url: str) -> dict[str, Any] | None:
    prompt = f"""
    Analyze the following article text.
    Extract the core facts and insights. Determine a signal score (1-10) where 10 is groundbreaking and 1 is fluff.
    Determine personal relevance (1-10) based on these topics: AI Research, Quantum Computing, Software Engineering, Semiconductors, Investing, Startups.
    Return JSON matching the schema.
    
    Source URL: {source_url}
    
    Text:
    {text[:15000]}
    """
    res = call_gemini_structured(prompt, ArticleAnalysis, model="gemini-2.5-flash")
    return res if isinstance(res, dict) else res.model_dump() if res else None

def synthesize_weekly(daily_insights: list[dict]) -> str:
    prompt = f"""
    Synthesize the following daily insights from the past week into a comprehensive Weekly Deep Dive.
    Highlight the most important trends, cross-cutting themes, and actionable conclusions.
    Output formatted in Markdown.
    
    Insights:
    {json.dumps(daily_insights)}
    """
    try:
        response = client.models.generate_content(
            model="gemini-2.5-pro",
            contents=prompt
        )
        return response.text
    except Exception as e:
        print(f"Weekly synthesis error: {e}")
        return "Failed to generate weekly synthesis."
