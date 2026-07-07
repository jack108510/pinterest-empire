#!/bin/bash
# Fetch fresh Pinterest analytics and push to GitHub Pages

cd /Users/jackserver/.openclaw/workspace/pinterest

echo "[$(date)] Starting Pinterest analytics sync..."

# 1. Fetch analytics for all accounts
python3 fetch_all_analytics.py 2>&1 | tail -20

# 2. Copy data files to dashboard/public/data (what GitHub Pages serves)
cp dashboard/data/*.json dashboard/public/data/ 2>/dev/null

# 3. Push to GitHub
cd /Users/jackserver/.openclaw/workspace
git add pinterest/dashboard/public/data/
git add pinterest/dashboard/data/
git commit -m "Pinterest analytics update $(date '+%Y-%m-%d %H:%M')" 2>/dev/null

# Push to pinterest-empire repo directly via API for each file
python3 - << 'PYEOF'
import json, os, base64, subprocess, glob

TOKEN = os.environ.get("GITHUB_TOKEN", "")
REPO = "jack108510/pinterest-empire"
DATA_DIR = "/Users/jackserver/.openclaw/workspace/pinterest/dashboard/public/data"

import urllib.request

def gh_put(path, content_bytes):
    url = f"https://api.github.com/repos/{REPO}/contents/{path}"
    # Get current SHA
    req = urllib.request.Request(url, headers={"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github+json"})
    try:
        resp = urllib.request.urlopen(req)
        current = json.loads(resp.read())
        sha = current.get("sha", "")
    except:
        sha = ""
    
    payload = {
        "message": f"Analytics update {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "content": base64.b64encode(content_bytes).decode(),
    }
    if sha:
        payload["sha"] = sha
    
    req = urllib.request.Request(url, 
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"token {TOKEN}", "Content-Type": "application/json", "Accept": "application/vnd.github+json"},
        method="PUT"
    )
    try:
        urllib.request.urlopen(req)
        print(f"  ✅ Pushed {path}")
    except Exception as e:
        print(f"  ❌ Failed {path}: {e}")

for f in glob.glob(f"{DATA_DIR}/*.json"):
    fname = os.path.basename(f)
    with open(f, "rb") as fh:
        content = fh.read()
    gh_put(f"dashboard/public/data/{fname}", content)

print("Done.")
PYEOF

echo "[$(date)] Sync complete."
