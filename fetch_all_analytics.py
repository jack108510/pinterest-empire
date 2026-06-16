#!/usr/bin/env python3
"""
Pinterest Analytics Fetcher — pulls metrics for all accounts via Playwright.
Stores results as JSON for the dashboard API.

Usage:
  python3.14 fetch_all_analytics.py                    # All enabled accounts
  python3.14 fetch_all_analytics.py --account supplements  # Single account
"""
import json, os, sys, time, argparse, re
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright

WORKSPACE = '/Users/jackserver/.openclaw/workspace/pinterest'
ACCOUNTS_FILE = f'{WORKSPACE}/accounts.json'
DATA_DIR = f'{WORKSPACE}/dashboard/data'
TIMEOUT = 60000

os.makedirs(DATA_DIR, exist_ok=True)


def load_accounts():
    with open(ACCOUNTS_FILE) as f:
        return [a for a in json.load(f) if a.get('enabled', True)]


def parse_number(text):
    """Parse strings like '190.05k', '1.2M', '38' into numbers."""
    text = text.strip().replace(',', '').replace('\n', '').strip()
    if not text:
        return 0
    multipliers = {'k': 1_000, 'K': 1_000, 'M': 1_000_000, 'B': 1_000_000_000}
    try:
        if text[-1] in multipliers:
            return float(text[:-1]) * multipliers[text[-1]]
        return float(text)
    except ValueError:
        return 0


def parse_percent(text):
    """Parse '1170%' or '-5%' into number."""
    text = text.strip().replace('%', '').replace('+', '').replace(',', '')
    try:
        return float(text)
    except ValueError:
        return 0


def fetch_account_analytics(account, context_label=None):
    """Fetch analytics for a single account using an existing browser context."""
    session = os.path.expanduser(account['session_path'])
    acct_id = account['id']
    today = datetime.now().strftime('%Y-%m-%d')

    print(f"  [{acct_id}] Fetching...")

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=session,
            headless=True,
            viewport={'width': 1280, 'height': 900}
        )
        context.set_default_timeout(30000)

        page = context.new_page()

        try:
            # Go to analytics overview (last 30 days default)
            page.goto('https://analytics.pinterest.com/overview/?aggregation=last30d', 
                      timeout=TIMEOUT, wait_until='domcontentloaded')
            time.sleep(6)

            # Extract account handle/name
            handle = page.evaluate("""() => {
                const el = document.querySelector('[data-test-id="business-account-switcher"]');
                return el ? el.innerText.trim().split('\\n')[0] : '';
            }""") or account.get('name', acct_id)

            # Extract overview metrics
            metrics = page.evaluate("""() => {
                const result = {};
                
                // Get all topline metrics
                const metricBoxes = document.querySelectorAll('[data-test-id="topline-metric"]');
                const summaryBox = document.querySelector('[data-test-id="metrics-summary-box"]');
                
                const sourceEl = summaryBox || (metricBoxes.length > 0 ? metricBoxes[0].parentElement : null);
                if (!sourceEl) return result;
                
                const items = (summaryBox || document.body).querySelectorAll('[data-test-id="topline-metric"]');
                const labels = ['impressions', 'engagements', 'outbound_clicks', 'saves', 'total_audience', 'engaged_audience'];
                
                items.forEach((item, i) => {
                    const text = item.innerText.trim();
                    const lines = text.split('\\n').map(s => s.trim()).filter(Boolean);
                    if (lines.length >= 2) {
                        const label = lines[0].toLowerCase().replace(/\\s+/g, '_');
                        const value = lines[1];
                        const change = lines.length >= 3 ? lines[2] : '';
                        result[label] = { value: value, change: change };
                    }
                });
                
                return result;
            }""")

            # Extract top pins
            top_pins = page.evaluate("""() => {
                const pins = [];
                const rows = document.querySelectorAll('[data-test-id="top-pins-table"] tr, table tr');
                let currentPin = null;
                
                // Alternative: look for pin entries by scanning for links to pins
                const pinLinks = document.querySelectorAll('a[href*="/pin/"]');
                const seen = new Set();
                pinLinks.forEach(link => {
                    const href = link.getAttribute('href');
                    if (seen.has(href)) return;
                    
                    // Walk up to find the row
                    let row = link;
                    for (let i = 0; i < 8; i++) {
                        if (row.nextElementSibling || row.parentElement) {
                            const parent = row.parentElement;
                            if (parent && parent.tagName === 'TR') { row = parent; break; }
                            row = parent;
                            if (!row) break;
                        }
                    }
                    
                    // Find the metric value near this link
                    let valueText = '';
                    let sib = link.parentElement;
                    while (sib && !valueText) {
                        sib = sib.nextElementSibling;
                        if (sib) {
                            const nums = sib.innerText?.trim();
                            if (nums && /^[\d,]+$/.test(nums.replace(/\s/g, ''))) {
                                valueText = nums;
                            }
                        }
                    }
                    
                    const title = link.innerText?.trim() || '';
                    if (title && title.length > 3 && !seen.has(href)) {
                        seen.add(href);
                        pins.push({ title: title.substring(0, 100), url: href, impressions: valueText });
                    }
                });
                
                return pins.slice(0, 15);
            }""")

            # Also grab raw text for fallback parsing
            raw_metrics = page.evaluate("""() => {
                const box = document.querySelector('[data-test-id="metrics-summary-box"]');
                return box ? box.innerText : '';
            }""")

            # Always run fallback parser — Pinterest puts values on odd lines
            parsed = {}
            if not metrics or all(v.get('display', '') in (',', '') for v in metrics.values()):
                lines = [l.strip() for l in raw_metrics.split('\n') if l.strip()]
                # Pinterest raw format: [Label, ',', value, ',', changePct, ...]
                # So value is at index+2, change at index+4
                metric_names = {
                    'Impressions': 'impressions',
                    'Engagements': 'engagements', 
                    'Outbound clicks': 'outbound_clicks',
                    'Saves': 'saves',
                    'Total audience': 'total_audience',
                    'Engaged audience': 'engaged_audience'
                }
                for i, line in enumerate(lines):
                    if line in metric_names and i + 2 < len(lines):
                        key = metric_names[line]
                        # Skip stray commas, find the actual value
                        value = None
                        change = ''
                        for j in range(i + 1, min(i + 5, len(lines))):
                            if lines[j] != ',' and not lines[j].endswith('%'):
                                value = lines[j]
                                # Change is next non-comma after value
                                for k in range(j + 1, min(j + 3, len(lines))):
                                    if lines[k] != ',' and lines[k].endswith('%'):
                                        change = lines[k]
                                        break
                                break
                            elif lines[j] == ',' and not value:
                                continue
                        if value:
                            parsed[key] = {'value': value, 'change': change}

            final_metrics = parsed if parsed else (metrics if metrics else {})

            # Normalize metric values to numbers
            clean_metrics = {}
            for key, val in final_metrics.items():
                v = val.get('value', val) if isinstance(val, dict) else val
                c = val.get('change', '') if isinstance(val, dict) else ''
                clean_metrics[key] = {
                    'value': parse_number(str(v)),
                    'display': str(v),
                    'change_pct': parse_percent(str(c))
                }

            # Clean top pins
            clean_pins = []
            for pin in top_pins:
                clean_pins.append({
                    'title': pin.get('title', ''),
                    'impressions': pin.get('impressions', ''),
                    'url': pin.get('url', '')
                })

            result = {
                'account_id': acct_id,
                'account_name': account.get('name', acct_id),
                'handle': handle,
                'fetched_at': datetime.now().isoformat(),
                'date_range': 'last_30_days',
                'metrics': clean_metrics,
                'top_pins': clean_pins,
                'raw_summary': raw_metrics[:1000]
            }

            # Save individual account data
            outfile = f'{DATA_DIR}/{acct_id}.json'
            with open(outfile, 'w') as f:
                json.dump(result, f, indent=2)
            print(f"  [{acct_id}] ✅ Saved → {outfile}")
            
            # Print summary
            imp = clean_metrics.get('impressions', {}).get('display', 'N/A')
            eng = clean_metrics.get('engagements', {}).get('display', 'N/A')
            clicks = clean_metrics.get('outbound_clicks', {}).get('display', 'N/A')
            saves = clean_metrics.get('saves', {}).get('display', 'N/A')
            print(f"         Impressions: {imp} | Engagements: {eng} | Clicks: {clicks} | Saves: {saves}")

            return result

        except Exception as e:
            print(f"  [{acct_id}] ❌ Error: {e}")
            try:
                page.screenshot(path=f'{WORKSPACE}/analytics-error-{acct_id}.png', full_page=True)
            except:
                pass
            return None
        finally:
            context.close()


def main():
    parser = argparse.ArgumentParser(description='Fetch Pinterest Analytics for All Accounts')
    parser.add_argument('--account', help='Single account ID (default: all)')
    args = parser.parse_args()

    accounts = load_accounts()
    if args.account:
        accounts = [a for a in accounts if a['id'] == args.account]
        if not accounts:
            print(f"Account '{args.account}' not found")
            sys.exit(1)

    print(f"\n📊 Fetching analytics for {len(accounts)} accounts...\n")

    results = []
    for acct in accounts:
        result = fetch_account_analytics(acct)
        if result:
            results.append(result)
        time.sleep(3)  # Brief pause between accounts

    # Save combined summary
    summary = {
        'fetched_at': datetime.now().isoformat(),
        'total_accounts': len(results),
        'accounts': results
    }

    summary_file = f'{DATA_DIR}/summary.json'
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)

    # Print empire-wide totals
    print(f"\n{'='*60}")
    print(f"📊 EMPIRE SUMMARY — {len(results)} accounts")
    print(f"{'='*60}")
    
    total_imp = sum(r.get('metrics', {}).get('impressions', {}).get('value', 0) for r in results)
    total_eng = sum(r.get('metrics', {}).get('engagements', {}).get('value', 0) for r in results)
    total_clicks = sum(r.get('metrics', {}).get('outbound_clicks', {}).get('value', 0) for r in results)
    total_saves = sum(r.get('metrics', {}).get('saves', {}).get('value', 0) for r in results)
    total_audience = sum(r.get('metrics', {}).get('total_audience', {}).get('value', 0) for r in results)

    print(f"Total Impressions:  {total_imp:,.0f}")
    print(f"Total Engagements:  {total_eng:,.0f}")
    print(f"Total Clicks:       {total_clicks:,.0f}")
    print(f"Total Saves:        {total_saves:,.0f}")
    print(f"Total Audience:     {total_audience:,.0f}")
    print(f"\nSummary saved → {summary_file}")


if __name__ == '__main__':
    main()
