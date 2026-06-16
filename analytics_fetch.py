#!/usr/bin/env python3
"""
Fetch Pinterest Analytics via Playwright using existing authenticated sessions.
Usage:
  python3.14 analytics_fetch.py --account supplements
  python3.14 analytics_fetch.py --account supplements --days 30
"""
import json, os, sys, time, argparse
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright

WORKSPACE = '/Users/jackserver/.openclaw/workspace/pinterest'
ACCOUNTS_FILE = f'{WORKSPACE}/accounts.json'
TIMEOUT = 60000


def load_account(account_id):
    with open(ACCOUNTS_FILE) as f:
        accounts = json.load(f)
    for a in accounts:
        if a['id'] == account_id:
            return a
    print(f"Account '{account_id}' not found")
    sys.exit(1)


def fetch_analytics(account, days=7):
    session = os.path.expanduser(account['session_path'])
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

    # Pinterest Analytics URL with date range
    analytics_url = f"https://analytics.pinterest.com/?startDate={start_date}&endDate={end_date}"

    print(f"Fetching analytics for {account['id']} ({start_date} → {end_date})...")

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=session,
            headless=True,
            viewport={'width': 1280, 'height': 900}
        )
        context.set_default_timeout(30000)

        page = context.new_page()

        try:
            # Go to analytics page
            page.goto(analytics_url, timeout=TIMEOUT, wait_until='domcontentloaded')
            time.sleep(5)

            # Take a screenshot for debugging
            screenshot_path = f'{WORKSPACE}/analytics-{account["id"]}-{datetime.now().strftime("%Y%m%d")}.png'
            page.screenshot(path=screenshot_path, full_page=True)
            print(f"Screenshot saved: {screenshot_path}")

            # Try to extract analytics data from the page
            data = page.evaluate("""() => {
                const result = {};

                // Try to get text content from the page
                const bodyText = document.body.innerText;

                // Look for common analytics metrics in the page text
                // Pinterest Analytics typically shows: impressions, saves, clicks, closeups, engagement rate
                result.rawText = bodyText.substring(0, 5000);

                // Try to find metric cards/values
                const metricElements = document.querySelectorAll('[data-test-id], [class*="metric"], [class*="stat"], [class*="overview"] h1, [class*="overview"] h2, [class*="overview"] h3, [class*="value"]');
                const metrics = [];
                metricElements.forEach(el => {
                    const text = el.innerText?.trim();
                    if (text && text.length < 200) {
                        metrics.push({
                            testId: el.getAttribute('data-test-id') || '',
                            className: el.className?.substring(0, 100) || '',
                            text: text
                        });
                    }
                });
                result.metrics = metrics;

                // Also try to grab any JSON embedded in script tags
                const scripts = document.querySelectorAll('script[type="application/json"]');
                const jsonBlobs = [];
                scripts.forEach(s => {
                    const content = s.textContent || '';
                    if (content.includes('impression') || content.includes('click') || content.includes('save') || content.includes('engagement')) {
                        jsonBlobs.push(content.substring(0, 3000));
                    }
                });
                result.jsonBlobs = jsonBlobs;

                return result;
            }""")

            # Print what we found
            print(f"\n=== Analytics for {account['id']} ===")
            print(f"Page URL: {page.url}")
            print(f"\nRaw page text (first 3000 chars):")
            print(data.get('rawText', 'N/A')[:3000])
            print(f"\nMetric elements found: {len(data.get('metrics', []))}")
            for m in data.get('metrics', [])[:30]:
                print(f"  [{m['testId'] or m['className'][:40]}] {m['text']}")
            print(f"\nJSON blobs found: {len(data.get('jsonBlobs', []))}")

            # Save raw data
            output_file = f'{WORKSPACE}/analytics-{account["id"]}-{datetime.now().strftime("%Y%m%d")}.json'
            with open(output_file, 'w') as f:
                json.dump({
                    'account': account['id'],
                    'url': page.url,
                    'date_range': f'{start_date} to {end_date}',
                    'fetched_at': datetime.now().isoformat(),
                    'data': data
                }, f, indent=2)
            print(f"\nFull data saved: {output_file}")

            return data

        except Exception as e:
            print(f"Error: {e}")
            # Still try to screenshot on error
            try:
                screenshot_path = f'{WORKSPACE}/analytics-error-{account["id"]}.png'
                page.screenshot(path=screenshot_path, full_page=True)
                print(f"Error screenshot: {screenshot_path}")
            except:
                pass
            return None
        finally:
            context.close()


def main():
    parser = argparse.ArgumentParser(description='Pinterest Analytics Fetcher')
    parser.add_argument('--account', required=True, help='Account ID')
    parser.add_argument('--days', type=int, default=7, help='Number of days (default 7)')
    args = parser.parse_args()

    account = load_account(args.account)
    fetch_analytics(account, args.days)


if __name__ == '__main__':
    main()
