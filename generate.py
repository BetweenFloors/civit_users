"""Generate a Civitai user profile report."""

import sys
import os

TOKEN    = os.environ.get("CIVITAI_TOKEN", "")
USERNAME = "BetweenFloors"
OUTPUT   = "report_BetweenFloors.html"
THEME    = "dark"

from fetch import fetch_all
from report import generate_html

if not TOKEN:
    print("Set CIVITAI_TOKEN env var or edit TOKEN in this file.")
    sys.exit(1)

print(f"Fetching data for @{USERNAME}…")
data = fetch_all(TOKEN, USERNAME)
print(f"  {len(data['posts'])} posts, {len(data['images'])} images")

generate_html(data, USERNAME, OUTPUT, theme=THEME)
print(f"Report saved → {OUTPUT}")
