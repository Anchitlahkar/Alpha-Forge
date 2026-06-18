def filter_high_signal(insights: list[dict], min_score: int = 5) -> list[dict]:
    if not insights:
        return []
        
    filtered = []
    for insight in insights:
        if not insight:
            continue
            
        score = insight.get("signal_score", 0)
        try:
            # Ensure score is numeric
            score = float(score)
        except (ValueError, TypeError):
            score = 0
            
        if score >= min_score:
            filtered.append(insight)
        else:
            print(f"Filtered out low signal: {insight.get('title', 'Unknown')} (Score: {score})")
    return filtered
