import json
from src.gemini_client import call_gemini_structured, DeduplicationResponse

def deduplicate_insights(insights: list[dict]) -> list[dict]:
    if not insights or len(insights) <= 1:
        return insights
        
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
        if not res:
            return insights
            
        # Handle both dict and Pydantic model response
        groups = res.groups if hasattr(res, 'groups') else res.get("groups", [])
        
        deduped = []
        handled_indices = set()
        
        for group in groups:
            # Handle both dict and Pydantic model
            if hasattr(group, 'model_dump'):
                g_dict = group.model_dump()
            else:
                g_dict = group
                
            indices = g_dict.get("original_indices", [])
            if not indices: continue
            
            # Find first valid index to use as base
            base_idx = -1
            for idx in indices:
                if 0 <= idx < len(insights):
                    base_idx = idx
                    break
            
            if base_idx == -1: continue
            
            base_insight = insights[base_idx].copy()
            base_insight["title"] = g_dict.get("event", base_insight["title"])
            base_insight["tldr"] = g_dict.get("summary", base_insight.get("tldr", ""))
            
            all_sources = set()
            for idx in indices:
                if 0 <= idx < len(insights):
                    all_sources.update(insights[idx].get("sources", []))
                    handled_indices.add(idx)
                    
            base_insight["sources"] = list(all_sources)
            deduped.append(base_insight)
            
        # Add remaining articles that weren't grouped
        for i, ins in enumerate(insights):
            if i not in handled_indices:
                deduped.append(ins)
                
        return deduped
    except Exception as e:
        print(f"Deduplication error: {e}")
        return insights
