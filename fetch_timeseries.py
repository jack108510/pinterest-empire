#!/usr/bin/env python3
"""
Fetch 30-day daily impression timeseries from Pinterest Analytics.
Extracts data from the GraphQL API responses.
"""
import json, os, sys, time
from playwright.sync_api import sync_playwright

WORKSPACE = '/Users/jackserver/.openclaw/workspace/pinterest'
OUTPUT = f'{WORKSPACE}/dashboard/public/data/timeseries.json'

ACCOUNTS = [
    ('supplements', '~/.pinterest-session'),
    ('cooking', '~/.pinterest-session-cooking'),
    ('beauty', '~/.pinterest-session-beauty'),
]

def fetch_timeseries(acct_id, session_path):
    session = os.path.expanduser(session_path)
    daily_data = []

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=session, headless=True, 
            viewport={'width': 1280, 'height': 900}
        )
        page = ctx.new_page()

        # Intercept GraphQL responses
        graphql_responses = []
        def handle_response(response):
            if '_/graphql/' in response.url:
                try:
                    body = response.json()
                    graphql_responses.append(body)
                except:
                    pass

        page.on('response', handle_response)

        page.goto('https://analytics.pinterest.com/overview/?aggregation=last30d',
                  timeout=60000, wait_until='networkidle')
        time.sleep(10)

        # Find the metrics graph response with daily data
        for resp in graphql_responses:
            try:
                data = resp.get('data', {})
                for key, val in data.items():
                    if 'MetricsGraph' in key and isinstance(val, dict):
                        series_data = val.get('data', [])
                        for series in series_data:
                            daily = series.get('series', {}).get('dailyMetrics', [])
                            if daily:
                                for day in daily:
                                    d = day.get('date', '')
                                    imp = day.get('metrics', {}).get('impressionFloat', 0)
                                    eng = day.get('metrics', {}).get('engagementFloat', 0)
                                    clicks = day.get('metrics', {}).get('outboundClickFloat', 0)
                                    saves = day.get('metrics', {}).get('saveFloat', 0)
                                    if d:
                                        daily_data.append({
                                            'date': d,
                                            'impressions': int(imp or 0),
                                            'engagements': int(eng or 0),
                                            'clicks': int(clicks or 0),
                                            'saves': int(saves or 0),
                                        })
            except:
                continue

        ctx.close()

    # Deduplicate by date
    seen = {}
    for d in daily_data:
        if d['date'] not in seen or d['impressions'] > seen[d['date']]['impressions']:
            seen[d['date']] = d
    daily_data = sorted(seen.values(), key=lambda x: x['date'])

    print(f"  [{acct_id}] {len(daily_data)} days captured")
    return daily_data


def main():
    print("Fetching 30-day timeseries for all accounts...\n")

    all_data = {}
    for acct_id, session_path in ACCOUNTS:
        print(f"  [{acct_id}] Fetching...")
        daily = fetch_timeseries(acct_id, session_path)
        all_data[acct_id] = daily
        time.sleep(2)

    # Build combined daily totals
    combined = {}
    for acct_id, daily in all_data.items():
        for d in daily:
            date = d['date']
            if date not in combined:
                combined[date] = {'impressions': 0, 'engagements': 0, 'clicks': 0, 'saves': 0}
            combined[date]['impressions'] += d['impressions']
            combined[date]['engagements'] += d['engagements']
            combined[date]['clicks'] += d['clicks']
            combined[date]['saves'] += d['saves']

    combined_list = [{'date': d, **v} for d, v in sorted(combined.items())]

    result = {
        'combined': combined_list,
        'accounts': all_data,
        'fetched_at': __import__('datetime').datetime.now().isoformat(),
    }

    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, 'w') as f:
        json.dump(result, f, indent=2)

    # Print summary
    total_imp = sum(d['impressions'] for d in combined_list)
    print(f"\nTotal combined impressions: {total_imp:,}")
    print(f"Days: {len(combined_list)}")
    if combined_list:
        print(f"First day: {combined_list[0]['date']} = {combined_list[0]['impressions']:,}")
        print(f"Last day: {combined_list[-1]['date']} = {combined_list[-1]['impressions']:,}")

    # Yesterday's stats
    from datetime import datetime, timedelta
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    yest = next((d for d in combined_list if d['date'] == yesterday), None)
    if yest:
        print(f"\nYesterday ({yesterday}): {yest['impressions']:,} impressions, {yest['clicks']} clicks")

    print(f"\nSaved → {OUTPUT}")


if __name__ == '__main__':
    main()
