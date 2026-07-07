#!/usr/bin/env python3
"""Create a 'Main' board on Pinterest accounts that need it."""
import json, sys, time
from playwright.sync_api import sync_playwright

WORKSPACE = '/Users/jackserver/.openclaw/workspace/pinterest'

def create_board(account_id, cookie_path):
    print(f"\n[{account_id}] Creating board...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        with open(cookie_path) as f:
            context.add_cookies(json.load(f))
        page = context.new_page()
        page.goto("https://www.pinterest.com/", timeout=30000)
        time.sleep(3)

        if 'login' in page.url.lower():
            print(f"  ❌ Session expired for {account_id}")
            browser.close()
            return False

        # Go to board creation URL
        page.goto("https://www.pinterest.com/board/create/", timeout=30000)
        time.sleep(3)

        # Try the board creation dialog
        try:
            name_input = page.locator('input[placeholder*="board name" i], input[name="name"], input[id*="board" i]').first
            name_input.wait_for(timeout=8000)
            name_input.fill("Main")
            time.sleep(1)
            # Click Create
            create_btn = page.locator('button:has-text("Create"), button[type="submit"]').last
            create_btn.click()
            time.sleep(3)
            print(f"  ✅ Board created for {account_id}")
            browser.close()
            return True
        except Exception as e:
            # Fallback: use pin builder to trigger board creation
            print(f"  ⚠ Dialog method failed: {e}")
            browser.close()
            return False

accounts = [
    ("wa-7",  f"{WORKSPACE}/cookies/wa-7.json"),
    ("wa-8",  f"{WORKSPACE}/cookies/wa-8.json"),
    ("wa-9",  f"{WORKSPACE}/cookies/wa-9.json"),
    ("wa-10", f"{WORKSPACE}/cookies/wa-10.json"),
    ("wa-11", f"{WORKSPACE}/cookies/wa-11.json"),
]

if len(sys.argv) > 1:
    target = sys.argv[1]
    accounts = [(a, p) for a, p in accounts if a == target]

for acct_id, cookie_path in accounts:
    create_board(acct_id, cookie_path)
