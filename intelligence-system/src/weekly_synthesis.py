import glob
import json
from src.config import DAILY_DIR, WEEKLY_DIR
from src.utils import get_today_str
from src.gemini_client import synthesize_weekly

def generate_weekly_synthesis():
    daily_files = glob.glob(str(DAILY_DIR / "*.json"))
    
    all_insights = []
    for fpath in daily_files:
        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)
            all_insights.extend(data)
            
    if not all_insights:
        print("No insights to synthesize.")
        return
        
    synthesis_markdown = synthesize_weekly(all_insights)
    
    today = get_today_str()
    output_path = WEEKLY_DIR / f"weekly_{today}.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(synthesis_markdown)
        
    print(f"Weekly synthesis saved to {output_path}")
