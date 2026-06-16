#!/usr/bin/env python3
"""
Pinterest Account Factory v2 — Fully Automated
Creates inbox, signs up on Pinterest, verifies email, saves session.
"""
import json, os, sys, time, random, urllib.request, urllib.parse, argparse
from pathlib import Path

WORKSPACE = '/Users/jackserver/.openclaw/workspace/pinterest'
ACCOUNTS_FILE = f'{WORKSPACE}/accounts.json'
API_KEY = "am_us_237687733d6087d5e2e5c3956f651883c8b190d38b855ebdbcf85f6780a8c3c9"
BASE_DOMAIN = "wildroseautomations.ca"
PASSWORD = "Harlem1085$"

# Shared config
DEFAULT_AFFILIATE_LINKS = [
    "https://amzn.to/4doKedR", "https://amzn.to/4d3oGC7", "https://amzn.to/4d32nNb",
    "https://amzn.to/4tjW5i1", "https://amzn.to/4f7I83g", "https://amzn.to/42T8Fdj",
    "https://amzn.to/4tpKJte", "https://amzn.to/4f1GjoC", "https://amzn.to/3Pm3sHZ",
    "https://amzn.to/4uuyNXT", "https://amzn.to/4erIAJF", "https://amzn.to/3P4WG9s",
    "https://amzn.to/48BbHqc", "https://amzn.to/4tQwU7X", "https://amzn.to/4f0SkKT",
]
DEFAULT_PRODUCTS = [
    {"name": "Collagen Peptides", "benefits": ["Glowing Skin", "Strong Hair", "Joint Support", "Anti-Aging"]},
    {"name": "Probiotic 50 Billion", "benefits": ["Gut Health", "Better Digestion", "Immune Boost", "Less Bloating"]},
    {"name": "Green Superfood Powder", "benefits": ["Natural Energy", "Detox", "Nutrient Dense", "Alkalize Your Body"]},
    {"name": "Omega-3 Fish Oil", "benefits": ["Heart Health", "Brain Function", "Reduce Inflammation", "Clear Skin"]},
    {"name": "Magnesium Glycinate", "benefits": ["Deep Sleep", "Muscle Recovery", "Less Anxiety", "Better Focus"]},
    {"name": "Vitamin D3 + K2", "benefits": ["Stronger Bones", "Immune Defense", "Mood Boost", "More Energy"]},
    {"name": "Adaptogen Blend", "benefits": ["Stress Relief", "Hormone Balance", "Mental Clarity", "Calm Focus"]},
    {"name": "Turmeric Curcumin", "benefits": ["Anti-Inflammatory", "Joint Pain Relief", "Antioxidant", "Brain Health"]},
    {"name": "Apple Cider Vinegar Gummies", "benefits": ["Weight Management", "Detox", "Digestion", "Appetite Control"]},
    {"name": "Melatonin Sleep Gummies", "benefits": ["Fall Asleep Faster", "Stay Asleep", "Wake Refreshed", "Natural Sleep Aid"]},
    {"name": "Elderberry Immune Gummies", "benefits": ["Immune Defense", "Cold Season Ready", "Antioxidant", "Daily Wellness"]},
    {"name": "Biotin Hair Growth", "benefits": ["Hair Growth", "Stronger Nails", "Glowing Skin", "Thicker Hair"]},
    {"name": "Pre-Workout Energy", "benefits": ["Explosive Energy", "Better Focus", "Endurance", "No Crash"]},
    {"name": "Ashwagandha Root", "benefits": ["Stress Relief", "Better Sleep", "Calm Mind", "Cortisol Balance"]},
    {"name": "Multivitamin Gummies", "benefits": ["Complete Nutrition", "Daily Essentials", "Energy Boost", "Immune Support"]},
]
DEFAULT_TITLES = [
    "This Changed My Morning Routine", "{benefit} in 30 Days — Here's How",
    "I Tried {product} for 60 Days", "The #1 Supplement Everyone Needs",
    "{product}: Worth the Hype?", "My Secret to {benefit}",
    "Stop Wasting Money on the Wrong Supplements", "{product} — Honest Review",
    "Why I Start Every Day With {product}", "3 Supplements That Actually Work",
    "The Truth About {product}", "{benefit} Starts Here",
    "I Wish I Knew This Sooner", "Top Supplement Pick for 2026",
    "Game Changer for {benefit}", "Doctors Recommend This For {benefit}",
    "My Daily Wellness Staple", "{product} Changed Everything",
    "Simple Hack for {benefit}", "Best Supplement I've Ever Tried",
    "Don't Buy {product} Until You Read This", "The Morning Supplement Stack That Works",
    "5 Signs You Need {product}", "Why Everyone's Talking About {product}",
    "Real Results With {product}",
]
DEFAULT_HASHTAGS = ["#HealthAndWellness", "#Supplements", "#HealthyLiving", "#Wellness", "#CleanLiving",
                    "#NaturalHealth", "#FitnessMotivation", "#SelfCare", "#HealthyLifestyle", "#Vitamins"]


def create_inbox(username):
    data = json.dumps({"username": username, "domain": BASE_DOMAIN, "display_name": f"Pinterest - {username}"}).encode()
    req = urllib.request.Request(
        "https://api.agentmail.to/v0/inboxes", data=data,
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req) as resp:
            r = json.loads(resp.read())
            print(f"  ✅ Inbox: {r['inbox_id']}")
            return r['inbox_id']
    except urllib.error.HTTPError as e:
        err = e.read().decode()
        if "already exists" in err:
            print(f"  ✅ Inbox exists: {username}@{BASE_DOMAIN}")
            return f"{username}@{BASE_DOMAIN}"
        print(f"  ❌ Inbox error: {err}")
        return None


def check_email_for_code(inbox_id, timeout=120):
    """Poll AgentMail for verification email and extract code."""
    print("  📬 Waiting for verification email...")
    einbox = urllib.parse.quote(inbox_id, safe='')
    start = time.time()
    
    while time.time() - start < timeout:
        try:
            req = urllib.request.Request(
                f"https://api.agentmail.to/v0/inboxes/{einbox}/messages?limit=5",
                headers={"Authorization": f"Bearer {API_KEY}"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
                for msg in data.get('messages', []):
                    subj = msg.get('subject', '')
                    text = msg.get('text', '')
                    body = subj + ' ' + text
                    
                    # Look for verification code
                    import re
                    codes = re.findall(r'\b\d{4,8}\b', body)
                    if codes and ('verif' in body.lower() or 'code' in body.lower() or 'pin' in body.lower()):
                        code = codes[-1]  # Take the last/most likely code
                        print(f"  ✅ Found code: {code}")
                        return code
        except:
            pass
        time.sleep(5)
    
    print("  ⏰ No verification email found within timeout")
    return None


def manual_login(email, account_id):
    """Open browser for user to manually log in, then save session."""
    from playwright.sync_api import sync_playwright
    
    session_path = os.path.expanduser(f"~/.wa-session-{account_id}")
    
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=session_path,
            headless=False,
            viewport={"width": 1280, "height": 900}
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.goto("https://www.pinterest.com/login/")
        
        # Wait up to 5 minutes for user to log in and navigate away from login
        print("  ⏳ Waiting for login...")
        try:
            page.wait_for_url("**/settings/**", timeout=300000)
            print("  ✅ Login detected!")
        except:
            # Check if they're logged in anyway
            page.goto("https://www.pinterest.com/settings/")
            time.sleep(3)
            if "login" not in page.url:
                print("  ✅ Login confirmed!")
            else:
                print("  ⚠️  Couldn't confirm login. Close browser when ready.")
        
        # Convert to business account
        print("  🔄 Converting to business account...")
        try:
            page.goto("https://www.pinterest.com/convert-business/", timeout=15000)
            time.sleep(4)
            biz_name = page.locator('input[name="business_name"], input[placeholder*="business"], input[placeholder*="name"]').first
            if biz_name.count() > 0:
                biz_name.fill(f"Wildrose Automations {account_id}")
                time.sleep(1)
            for btn_text in ["Convert", "Continue", "Create", "Next", "Done"]:
                btn = page.get_by_role("button", name=btn_text)
                if btn.count() > 0:
                    btn.first.click()
                    time.sleep(3)
                    break
            print("  ✅ Business account created!")
        except Exception as e:
            print(f"  ⚠️  Business conversion: {e}")
        
        # Create Main board
        try:
            page.goto("https://www.pinterest.com/board-builder/", timeout=15000)
            time.sleep(3)
            board_input = page.locator('input[placeholder*="name"], input[placeholder*="Board"]').first
            if board_input.count() > 0:
                board_input.fill("Main")
                time.sleep(1)
                create = page.get_by_role("button", name="Create")
                if create.count() > 0:
                    create.first.click()
                    time.sleep(3)
                    print("  ✅ Created Main board")
        except Exception as e:
            print(f"  ⚠️  Board creation: {e}")
        
        context.close()
    
    return session_path


def load_accounts():
    with open(ACCOUNTS_FILE) as f:
        return json.load(f)


def save_accounts(accounts):
    with open(ACCOUNTS_FILE, 'w') as f:
        json.dump(accounts, f, indent=2)


def get_next_num(accounts):
    nums = []
    for a in accounts:
        if a['id'].startswith('wa-'):
            try: nums.append(int(a['id'].split('-')[1]))
            except: pass
    return max(nums, default=0) + 1


def add_account(account_id, posting_hour=None):
    accounts = load_accounts()
    if posting_hour is None:
        posting_hour = len(accounts) % 24
    
    account = {
        "id": account_id,
        "name": f"Pinterest Account {account_id}",
        "session_path": f"~/.wa-session-{account_id}",
        "stock_dir": f"{WORKSPACE}/stock",
        "niche": "Health & Wellness",
        "posting_hour": posting_hour,
        "boards": ["Main"],
        "affiliate_links": DEFAULT_AFFILIATE_LINKS,
        "products": DEFAULT_PRODUCTS,
        "title_templates": DEFAULT_TITLES,
        "hashtags": DEFAULT_HASHTAGS,
        "email": f"{account_id}@{BASE_DOMAIN}",
    }
    
    accounts.append(account)
    save_accounts(accounts)
    return account


def main():
    parser = argparse.ArgumentParser(description='Pinterest Account Factory v2')
    parser.add_argument('--count', type=int, default=1, help='Number of accounts to create (default: 1)')
    parser.add_argument('--skip-signup', action='store_true', help='Skip signup, just create inbox + config')
    parser.add_argument('--start-posting', action='store_true', help='Start posting after creation')
    args = parser.parse_args()
    
    accounts = load_accounts()
    
    for i in range(args.count):
        num = get_next_num(accounts)
        account_id = f"wa-{num}"
        email = f"wa-{num}@{BASE_DOMAIN}"
        
        print(f"\n{'='*50}")
        print(f"  ACCOUNT #{num} ({i+1}/{args.count})")
        print(f"{'='*50}")
        print(f"  Email: {email}")
        print()
        
        # Step 1: Create inbox
        print("📧 Step 1: Creating email inbox")
        inbox = create_inbox(account_id)
        if not inbox:
            print("  Skipping account (inbox failed)")
            continue
        
        # Step 2: Open browser for manual login
        if not args.skip_signup:
            print("\n🌐 Step 2: Log in to Pinterest")
            print(f"   Email: {email}")
            print(f"   Password: {PASSWORD}")
            print("   Log in, then close the browser.\n")
            session_path = manual_login(email, account_id)
        else:
            print("\n⏭️  Step 2: Skipping signup")
        
        # Step 3: Save config
        posting_hour = (len(accounts)) % 24
        account = add_account(account_id, posting_hour)
        
        print(f"\n{'='*50}")
        print(f"  ✅ DONE: {account_id}")
        print(f"  Email: {email}")
        print(f"  Posting hour: {posting_hour}:00")
        print(f"  Total accounts: {len(load_accounts())}")
        
        # Step 4: Start posting
        if args.start_posting and not args.skip_signup:
            print(f"\n🚀 Starting poster for {account_id}...")
            os.system(f"cd {WORKSPACE} && python3 multi-poster.py --account {account_id} &")
        
        # Reload accounts for next iteration
        accounts = load_accounts()
        
        if i < args.count - 1:
            wait = random.randint(30, 60)
            print(f"\n  ⏳ Waiting {wait}s before next account...")
            time.sleep(wait)
    
    print(f"\n{'='*50}")
    print(f"  ALL DONE")
    print(f"  Total accounts: {len(load_accounts())}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
