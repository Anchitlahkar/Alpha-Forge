from src.config import load_scoring

def rank_insights(insights: list[dict]) -> list[dict]:
    scoring_config = load_scoring()
    weights = scoring_config.get("weights", {"signal": 0.7, "personal": 0.3})
    categories = scoring_config.get("categories", {})
    
    for insight in insights:
        signal_score = insight.get("signal_score", 0)
        llm_personal = insight.get("personal_relevance", 0)
        
        cat_weight = categories.get(insight.get("category", "Consumer Tech"), 5)
        
        adjusted_personal = (llm_personal + cat_weight) / 2
        
        final_score = (signal_score * weights["signal"]) + (adjusted_personal * weights["personal"])
        insight["final_score"] = round(final_score, 2)
        
    insights.sort(key=lambda x: x.get("final_score", 0), reverse=True)
    return insights
