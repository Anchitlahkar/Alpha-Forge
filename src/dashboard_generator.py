import glob
import os
import markdown
from jinja2 import Environment, FileSystemLoader
from src.config import TEMPLATES_DIR, DASHBOARD_DIR, WEEKLY_DIR
from src.utils import get_today_str

def generate_dashboard(insights: list[dict]):
    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
    template = env.get_template("dashboard.html")
    
    categorized = {}
    for insight in insights:
        cat = insight.get("category", "Other")
        if cat not in categorized:
            categorized[cat] = []
        categorized[cat].append(insight)
        
    weekly_files = glob.glob(str(WEEKLY_DIR / "*.md"))
    weekly_content = ""
    if weekly_files:
        latest_weekly = max(weekly_files, key=os.path.getctime)
        with open(latest_weekly, "r", encoding="utf-8") as f:
            weekly_content = markdown.markdown(f.read())
            
    html_content = template.render(
        date=get_today_str(),
        top_insights=insights[:5],
        categorized_insights=categorized,
        weekly_content=weekly_content
    )
    
    output_path = DASHBOARD_DIR / "index.html"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print(f"Dashboard generated at {output_path}")
