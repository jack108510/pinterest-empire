#!/usr/bin/env python3
"""
Pinterest Empire — Daily Analytics Report
Fetches metrics for all accounts, compares to yesterday,
tracks pace toward 50M monthly impressions by Dec 1, 2026.

Usage:
  python3 daily_report.py              # Fetch + print report
  python3 daily_report.py --no-fetch   # Report from cached data only
"""
import json, os, sys, subprocess, time
from datetime import datetime, timedelta

WORKSPACE = '/Users/jackserver/.openclaw/workspace/pinterest'
DATA_DIR = f'{WORKSPACE}/dashboard/data'
HISTORY_DIR = f'{WORKSPACE}/dashboard/data/history'
ACCOUNTS_FILE = f'{WORKSPACE}/accounts.json'

# ─── Goal tracking ───
GOAL_MONTHLY_IMPRESSIONS = 50_000_000
GOAL_DATE = datetime(2026, 12, 1)
START_DATE = datetime(2026, 6, 7)   # Empire plan start
START_IMPRESSIONS = 170_000          # Known starting point (Day 0)

os.makedirs(HISTORY_DIR, exist_ok=True)


def fetch_analytics():
    """Run the analytics fetcher for all accounts."""
    print("📊 Fetching analytics for all accounts...\n")
    script = f'{WORKSPACE}/fetch_all_analytics.py'
    result = subprocess.run(
        [sys.executable, script],
        capture_output=True, text=True, timeout=600,
        cwd=WORKSPACE
    )
    print(result.stdout[-500:] if len(result.stdout) > 500 else result.stdout)
    if result.returncode != 0:
        print(f"⚠️  Fetcher stderr: {result.stderr[-300:]}")


def load_summary():
    """Load the current summary.json."""
    path = f'{DATA_DIR}/summary.json'
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None


def load_yesterday():
    """Load yesterday's snapshot for comparison."""
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    path = f'{HISTORY_DIR}/{yesterday}.json'
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None


def save_snapshot(summary):
    """Save today's metrics as a daily snapshot."""
    today = datetime.now().strftime('%Y-%m-%d')
    path = f'{HISTORY_DIR}/{today}.json'

    # Build flat snapshot
    snapshot = {
        'date': today,
        'saved_at': datetime.now().isoformat(),
        'accounts': {}
    }

    for acct in summary.get('accounts', []):
        aid = acct.get('account_id', 'unknown')
        metrics = acct.get('metrics', {})
        snapshot['accounts'][aid] = {
            'name': acct.get('account_name', aid),
            'impressions': metrics.get('impressions', {}).get('value', 0),
            'engagements': metrics.get('engagements', {}).get('value', 0),
            'outbound_clicks': metrics.get('outbound_clicks', {}).get('value', 0),
            'saves': metrics.get('saves', {}).get('value', 0),
            'total_audience': metrics.get('total_audience', {}).get('value', 0),
        }

    with open(path, 'w') as f:
        json.dump(snapshot, f, indent=2)
    print(f"📁 Snapshot saved: {path}")


def load_account_names():
    """Load account names from accounts.json."""
    with open(ACCOUNTS_FILE) as f:
        return {a['id']: a.get('name', a['id']) for a in json.load(f)}


def get_followers(summary):
    """Try to extract follower count from total_audience metric."""
    # total_audience is the closest proxy to followers in Pinterest analytics
    return sum(
        a.get('metrics', {}).get('total_audience', {}).get('value', 0)
        for a in summary.get('accounts', [])
    )


def format_num(n):
    """Format large numbers: 1.2M, 340K, 1,234."""
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    elif n >= 1_000:
        return f"{n/1_000:.0f}K"
    return f"{int(n):,}"


def format_change(current, previous):
    """Format day-over-day change."""
    if previous == 0:
        return "+∞"
    pct = ((current - previous) / previous) * 100
    sign = "+" if pct >= 0 else ""
    delta = current - previous
    return f"{sign}{format_num(delta)} ({sign}{pct:.1f}%)"


def calc_pace(current_monthly):
    """
    Calculate whether we're on pace for 50M by Dec 1.
    Uses linear interpolation between start and goal.
    """
    now = datetime.now()
    total_days = (GOAL_DATE - START_DATE).days
    days_elapsed = (now - START_DATE).days
    days_remaining = (GOAL_DATE - now).days

    # Expected impressions today (linear pace)
    expected_today = START_IMPRESSIONS + (
        (GOAL_MONTHLY_IMPRESSIONS - START_IMPRESSIONS) * (days_elapsed / total_days)
    )

    # How far ahead/behind
    variance_pct = ((current_monthly - expected_today) / expected_today) * 100

    # Required daily growth to hit goal
    if days_remaining > 0 and current_monthly > 0:
        # Need to grow from current to goal in remaining days
        growth_needed = GOAL_MONTHLY_IMPRESSIONS / current_monthly
        if growth_needed > 1:
            # Daily multiplier needed (compound)
            import math
            daily_growth_rate = growth_needed ** (1 / days_remaining) - 1
            daily_growth_pct = daily_growth_rate * 100
        else:
            daily_growth_pct = 0
    else:
        daily_growth_pct = 0

    return {
        'expected_today': expected_today,
        'variance_pct': variance_pct,
        'days_elapsed': days_elapsed,
        'days_remaining': days_remaining,
        'daily_growth_needed': daily_growth_pct,
        'on_track': variance_pct >= -10,  # Within 10% = on track
    }


def generate_report(summary, yesterday):
    """Generate the text report."""
    now = datetime.now()
    accounts_data = summary.get('accounts', [])
    account_names = load_account_names()

    # ─── Empire totals ───
    totals = {
        'impressions': sum(a.get('metrics', {}).get('impressions', {}).get('value', 0) for a in accounts_data),
        'engagements': sum(a.get('metrics', {}).get('engagements', {}).get('value', 0) for a in accounts_data),
        'clicks': sum(a.get('metrics', {}).get('outbound_clicks', {}).get('value', 0) for a in accounts_data),
        'saves': sum(a.get('metrics', {}).get('saves', {}).get('value', 0) for a in accounts_data),
        'audience': sum(a.get('metrics', {}).get('total_audience', {}).get('value', 0) for a in accounts_data),
    }

    # ─── Yesterday comparison ───
    y_totals = {'impressions': 0, 'engagements': 0, 'clicks': 0, 'saves': 0, 'audience': 0}
    if yesterday:
        for aid, data in yesterday.get('accounts', {}).items():
            for k in y_totals:
                y_totals[k] += data.get(k, 0)

    # ─── Pace calculation ───
    pace = calc_pace(totals['impressions'])

    # ─── Active vs broken accounts ───
    active_accounts = [a for a in accounts_data if a.get('metrics', {}).get('impressions', {}).get('value', 0) > 0]
    dead_accounts = [a for a in accounts_data if a.get('metrics', {}).get('impressions', {}).get('value', 0) == 0]

    # ─── Build report ───
    lines = []
    lines.append("📊 PINTEREST EMPIRE — DAILY REPORT")
    lines.append(f"📅 {now.strftime('%A, %b %d, %Y')}")
    lines.append("")

    # Empire totals table
    lines.append("┌─────────────────┬──────────────┬─────────────────────┐")
    lines.append("│ Metric          │ Current (30d)│ vs Yesterday        │")
    lines.append("├─────────────────┼──────────────┼─────────────────────┤")

    metrics_display = [
        ('Impressions', totals['impressions'], y_totals['impressions']),
        ('Engagements', totals['engagements'], y_totals['engagements']),
        ('Clicks', totals['clicks'], y_totals['clicks']),
        ('Saves', totals['saves'], y_totals['saves']),
        ('Followers', totals['audience'], y_totals['audience']),
    ]

    for name, current, prev in metrics_display:
        change = format_change(current, prev) if prev > 0 else "—"
        lines.append(f"│ {name:<15} │ {format_num(current):>12} │ {change:<19} │")

    lines.append("└─────────────────┴──────────────┴─────────────────────┘")
    lines.append("")

    # Per-account breakdown
    lines.append(f"ACCOUNTS ({len(active_accounts)} active, {len(dead_accounts)} dead)")
    lines.append("")

    for acct in sorted(accounts_data, key=lambda x: x.get('metrics', {}).get('impressions', {}).get('value', 0), reverse=True):
        aid = acct.get('account_id', '?')
        name = account_names.get(aid, acct.get('account_name', aid))
        m = acct.get('metrics', {})
        imp = m.get('impressions', {}).get('value', 0)
        clicks = m.get('outbound_clicks', {}).get('value', 0)
        saves = m.get('saves', {}).get('value', 0)
        aud = m.get('total_audience', {}).get('value', 0)
        imp_change = m.get('impressions', {}).get('change_pct', 0)

        status = "✅" if imp > 0 else "❌"
        growth = f"+{imp_change:.0f}%" if imp_change > 0 else f"{imp_change:.0f}%"

        lines.append(f"  {status} {name}")
        lines.append(f"     {format_num(imp)} impressions ({growth}) | {clicks} clicks | {saves} saves | {format_num(aud)} followers")

    lines.append("")

    # ─── Pace to goal ───
    lines.append("🎯 GOAL TRACKING — 50M Monthly by Dec 1")
    lines.append("")

    pct_of_goal = (totals['impressions'] / GOAL_MONTHLY_IMPRESSIONS) * 100
    pace_status = "🟢 ON TRACK" if pace['on_track'] else "🔴 BEHIND PACE"
    if pace['variance_pct'] > 10:
        pace_status = "🟢 AHEAD OF PACE"
    elif pace['variance_pct'] > -10:
        pace_status = "🟡 ON TRACK"

    lines.append(f"  Current: {format_num(totals['impressions'])} / 50M ({pct_of_goal:.1f}%)")
    lines.append(f"  Expected today: {format_num(pace['expected_today'])} ({pace['variance_pct']:+.1f}% variance)")
    lines.append(f"  Status: {pace_status}")
    lines.append(f"  Days elapsed: {pace['days_elapsed']} / {(GOAL_DATE - START_DATE).days}")
    lines.append(f"  Days remaining: {pace['days_remaining']}")

    if pace['daily_growth_needed'] > 0:
        lines.append(f"  Required daily growth: {pace['daily_growth_needed']:.2f}%/day to hit goal")
        # At current account count, what does this mean?
        if active_accounts:
            per_account_needed = GOAL_MONTHLY_IMPRESSIONS / len(active_accounts)
            lines.append(f"  Per active account needed: {format_num(per_account_needed)}/mo")
            lines.append(f"  Accounts needed (at 500K each): {GOAL_MONTHLY_IMPRESSIONS // 500_000}")

    lines.append("")
    lines.append(f"  Last updated: {summary.get('fetched_at', 'unknown')}")

    report = '\n'.join(lines)
    return report


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--no-fetch', action='store_true', help='Skip analytics fetch, use cached data')
    args = parser.parse_args()

    # Step 1: Fetch fresh analytics
    if not args.no_fetch:
        fetch_analytics()

    # Step 2: Load data
    summary = load_summary()
    if not summary:
        print("❌ No analytics data found. Run fetch_all_analytics.py first.")
        sys.exit(1)

    yesterday = load_yesterday()

    # Step 3: Save today's snapshot
    save_snapshot(summary)

    # Step 4: Generate report
    report = generate_report(summary, yesterday)
    print('\n' + report)

    # Step 5: Save report
    report_file = f'{HISTORY_DIR}/report-{datetime.now().strftime("%Y-%m-%d")}.txt'
    with open(report_file, 'w') as f:
        f.write(report)

    return report


if __name__ == '__main__':
    main()
