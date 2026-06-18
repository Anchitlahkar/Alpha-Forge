def filter_high_signal(insights: list[dict], min_score: int = 5) -> list[dict]:
    filtered = []
    for insight in insights:
        score = insight.get("signal_score", 0)
        if score >= min_score:
            filtered.append(insight)
        else:
            print(f"Filtered out low signal: {insight.get('title')} (Score: {score})")
    return filtered
