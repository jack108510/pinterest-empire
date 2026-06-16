#!/usr/bin/env python3
"""
Pinterest Analytics Checker
Scrapes monthly views for all accounts and outputs a summary.

Usage:
  python3 analytics.py                  # Check all accounts
  python3 analytics.py --account beauty # Check single account
"""
import json, os, sys, time
from pathlib import Path

WORKSPACE = '/Users/jackserver/.openclaw/workspace/pinterest'
ACCOUNTS_FILE = f'{WORKSPACE}/accounts.json'
LOGS_DIR = f'{WORKSPACE}/analytics'
os.makedirs(LOGS_DIR, exist_ok=True)


def get_account_stats(session_path, headless=True):
    """Scrape profile stats from Pinterest."""
    from playwright.sync_api import sync_playwright
    
    session = os.path.expanduser(session_path)
    
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=session,
            headless=headless,
            viewport={"width": 1280, "height": 900}
        )
        page = context.pages[0] if context.pages else context.new_page()
        
        try:
            page.goto("https://www.pinterest.com/analytics/", timeout=20000)
            time.sleep(5)
            
            body = page.inner_text("body")
            
            # Extract monthly views
            views = "N/A"
            followers = "N/A"
            
            # Look for patterns like "1.4k monthly views" or "120K monthly views"
            import re
            
            views_match = re.search(r'([\d,.]+[kKmM]?)\s+monthly\s+views', body)
            if views_match:
                views = views_match.group(1)
            
            followers_match = re.search(r'([\d,.]+[kKmM]?)\s+followers', body)
            if followers_match:
                followers = followers_match.group(1)
            
            # Get handle from page
            handle = "unknown"
            url = page.url
            # Try navigating to settings to get handle
            page.goto("https://www.pinterest.com/settings/", timeout=15000)
            time.sleep(3)
            settings_text = page.inner_text("body")[:500]
            
            # Extract username from settings
            handle_match = re.search(r'@(\w+)', settings_text)
            if handle_match:
                handle = handle_match.group(1)
            
            return {
                "views": views,
                "followers": followers,
                "handle": handle,
                "logged_in": "login" not in page.url
            }
            
        except Exception as e:
            return {"error": str(e), "logged_in": False}
        finally:
            context.close()


def parse_views(views_str):
    """Convert view string to number for comparison."""
    if views_str == "N/A":
        return 0
    views_str = views_str.replace(",", "")
    if views_str.lower().endswith("k"):
        return float(views_str[:-1]) * 1000
    elif views_str.lower().endswith("m"):
        return float(views_str[:-1]) * 1000000
    return float(views_str)


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--account', help='Check single account')
    parser.add_argument('--save', action='store_true', help='Save results to file')
    args = parser.parse_args()
    
    with open(ACCOUNTS_FILE) as f:
        accounts = json.load(f)
    
    if args.account:
        accounts = [a for a in accounts if a['id'] == args.account]
        if not accounts:
            print(f"Account '{args.account}' not found")
            sys.exit(1)
    
    results = []
    
    print(f"Checking {len(accounts)} accounts...\n")
    print(f"{'Account':<20} {'Handle':<15} {'Views':<12} {'Followers':<10} {'Status'}")
    print("-" * 70)
    
    for acct in accounts:
        stats = get_account_stats(acct['session_path'])
        
        if stats.get("error"):
            print(f"{acct['id']:<20} {'?':<15} {'N/A':<12} {'N/A':<10} ❌ {stats['error'][:30]}")
            results.append({"id": acct['id'], **stats})
        else:
            status = "✅" if stats["logged_in"] else "❌ Logged out"
            print(f"{acct['id']:<20} {'@'+stats['handle']:<15} {stats['views']:<12} {stats['followers']:<10} {status}")
            results.append({
                "id": acct['id'],
                "handle": stats["handle"],
                "views": stats["views"],
                "followers": stats["followers"],
                "logged_in": stats["logged_in"]
            })
        
        time.sleep(2)  # Don't hammer Pinterest
    
    print("-" * 70)
    
    # Summary
    total_views = sum(parse_views(r.get("views", "N/A")) for r in results)
    active = sum(1 for r in results if r.get("logged_in"))
    
    if total_views >= 1000000:
        views_str = f"{total_views/1000000:.1f}M"
    elif total_views >= 1000:
        views_str = f"{total_views/1000:.1f}K"
    else:
        views_str = str(int(total_views))
    
    print(f"\nTotal: {views_str} monthly views across {active} active accounts")
    print(f"Target: 50M by Dec 1, 2026")
    
    if total_views > 0:
        pct = (total_views / 50000000) * 100
        bar_len = 30
        filled = int(bar_len * pct / 100)
        bar = "█" * filled + "░" * (bar_len - filled)
        print(f"Progress: [{bar}] {pct:.2f}%")
    
    # Save if requested
    if args.save:
        from datetime import datetime
        date_str = datetime.now().strftime("%Y-%m-%d")
        save_path = f"{LOGS_DIR}/analytics-{date_str}.json"
        with open(save_path, 'w') as f:
            json.dump({
                "date": date_str,
                "total_views": total_views,
                "active_accounts": active,
                "accounts": results
            }, f, indent=2)
        print(f"\n💾 Saved to {save_path}")


if __name__ == "__main__":
    main()
