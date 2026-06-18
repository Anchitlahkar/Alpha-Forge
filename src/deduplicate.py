import json
from src.gemini_client import call_gemini_structured, DeduplicationResponse

def deduplicate_insights(insights: list[dict]) -> list[dict]:
    if not insights or len(insights) <= 1:
        return insights
        
    # Simplify payload to avoid token bloat
    payload = [{"index": i, "title": ins["title"], "tldr": ins.get("tldr", "")} for i, ins in enumerate(insights)]
    prompt_text = f"""
    Group the following articles if they discuss the exact same underlying event or news.
    Merge them into a single coherent insight.
    Return a list of grouped events.
    Articles:
    {json.dumps(payload)}
    """
    
    try:
        res = call_gemini_structured(prompt_text, DeduplicationResponse, model="gemini-2.5-flash")
        if not res or not res.groups:
            return insights
            
        deduped = []
        handled_indices = set()
        
        for group in res.groups:
            indices = group.original_indices
            if not indices: continue
            
            # Determine base index safely
            valid_indices = [idx for idx in indices if 0 <= idx < len(insights)]
            if not valid_indices: continue
            
            base_idx = valid_indices[0]
            base_insight = insights[base_idx].copy()
            base_insight["title"] = group.event
            base_insight["tldr"] = group.summary
            
            # Combine sources
            all_sources = set()
            for idx in valid_indices:
                all_sources.update(insights[idx].get("sources", []))
                handled_indices.add(idx)
                    
            base_insight["sources"] = list(all_sources)
            deduped.append(base_insight)
            
        # Retain articles that weren't part of any group
        for i, ins in enumerate(insights):
            if i not in handled_indices:
                deduped.append(ins)
                
        return deduped
    except Exception as e:
        print(f"Deduplication processing error: {e}")
        return insights
