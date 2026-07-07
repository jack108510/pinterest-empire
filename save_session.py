#!/usr/bin/env python3
"""
Save a Pinterest account as a PERSISTENT profile (not just cookies).
This is more reliable for long-term posting.
Usage: python3 save_session.py wa-7
"""
import sys, json, time, os
from playwright.sync_api import sync_playwright

account = sys.argv[1] if len(sys.argv) > 1 else "account"
profile_dir = os.path.expanduser(f"~/.wa-session-{account}")

os.makedirs(profile_dir, exist_ok=True)

print(f"Opening Pinterest for {account}...")
print(f"Profile will be saved to: {profile_dir}")

with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(
        user_data_dir=profile_dir,
        headless=False,
        viewport={'width': 1280, 'height': 900}
    )
    page = context.new_page()
    page.goto("https://www.pinterest.com/login/")

    print("Log in on screen, then wait for the home feed...")
    while True:
        time.sleep(3)
        url = page.url
        cookies = context.cookies()
        has_auth = any(c["name"] == "_auth" and c["value"] not in ("", "0") for c in cookies)
        on_home = (url.rstrip("/") in ("https://www.pinterest.com", "https://pinterest.com")
                   or "/following" in url or url.endswith("/?_auto"))
        if has_auth and on_home:
            time.sleep(2)
            print(f"Logged in. Saving profile to {profile_dir}")
            break

    context.close()

print(f"✅ Session saved for {account}")
print(f"   Profile: {profile_dir}")
