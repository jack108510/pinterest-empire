#!/usr/bin/env python3
"""
Open Pinterest in a browser, wait for the user to log in, then save cookies.
Usage: python3 save_cookies.py <account_name>
e.g.:  python3 save_cookies.py wa-4
"""
import sys, json, time
from playwright.sync_api import sync_playwright

account = sys.argv[1] if len(sys.argv) > 1 else "account"
output = f"/Users/jackserver/.openclaw/workspace/pinterest/cookies/{account}.json"

import os
os.makedirs(os.path.dirname(output), exist_ok=True)

print(f"Opening Pinterest... Log in then come back here.")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    page.goto("https://www.pinterest.com/signup/")

    # Wait until the user is fully logged in (home feed or following feed)
    # Must have _auth cookie AND be on the home feed — avoids triggering mid-signup
    print("Waiting for you to finish signup and reach the home feed...")
    while True:
        time.sleep(3)
        url = page.url
        cookies_now = context.cookies()
        has_auth = any(c["name"] == "_auth" and c["value"] not in ("", "0") for c in cookies_now)
        on_home = url.rstrip("/") in ("https://www.pinterest.com", "https://pinterest.com") or "/following" in url or "/feed" in url or url.endswith("/?_auto")
        if has_auth and on_home:
            time.sleep(2)  # let page settle
            print(f"Detected home feed at: {url}")
            break

    cookies = context.cookies()
    with open(output, "w") as f:
        json.dump(cookies, f, indent=2)

    print(f"✅ Cookies saved to {output} ({len(cookies)} cookies)")
    browser.close()
