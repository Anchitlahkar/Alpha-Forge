import time
import json
import re
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

def clean_json_response(text: str) -> str:
    """Removes markdown code blocks and cleans the response text."""
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```\s*", "", text)
    return text.strip()

def call_gemini_structured(prompt: str, schema_model: type[BaseModel], model: str = "gemini-2.5-flash", retries: int = 3) -> Any:
    # Injecting the schema directly into the prompt to bypass SDK schema conversion bugs
    schema_json = json.dumps(schema_model.model_json_schema(), indent=2)
    full_prompt = (
        f"{prompt}\n\n"
        "IMPORTANT: You must return valid JSON that strictly conforms to the following JSON schema:\n"
        f"{schema_json}\n"
        "Return ONLY the JSON. No explanations, no markdown blocks."
    )

    for attempt in range(retries):
        try:
            response = client.models.generate_content(
                model=model,
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    # We avoid response_schema here to fix the 400 INVALID_ARGUMENT error
                )
            )
            
            if not response or not response.text:
                continue

            cleaned_text = clean_json_response(response.text)
            
            # Use Pydantic to validate and parse the response
            parsed_data = schema_model.model_validate_json(cleaned_text)
            return parsed_data
        except Exception as e:
            print(f"Gemini API failure (attempt {attempt+1}): {e}")
            if "429" in str(e): # Rate limit backoff
                time.sleep(10 * (attempt + 1))
            else:
                time.sleep(2 * (attempt + 1))
    return None

def extract_insights(text: str, source_url: str) -> dict[str, Any] | None:
    prompt = f"""
    Analyze the following article text.
    Extract the core facts and insights. Determine a signal score (1-10) where 10 is groundbreaking and 1 is fluff.
    Determine personal relevance (1-10) based on these topics: AI Research, Quantum Computing, Software Engineering, Semiconductors, Investing, Startups.
    
    Source URL: {source_url}
    
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
    try:
        response = client.models.generate_content(
            model="gemini-2.5-pro",
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.3)
        )
        return response.text if response.text else "Synthesis empty."
    except Exception as e:
        print(f"Weekly synthesis error: {e}")
        return "Failed to generate weekly synthesis due to API error."
