#!/usr/bin/env python3
"""
Convert a Pinterest personal account to a Business account via Playwright.
Usage:
  python3 convert_business.py --account beauty
  python3 convert_business.py --account beauty --headless false
"""
import json, os, sys, time, argparse
from playwright.sync_api import sync_playwright

WORKSPACE = '/Users/jackserver/.openclaw/workspace/pinterest'
ACCOUNTS_FILE = f'{WORKSPACE}/accounts.json'
TIMEOUT = 60000


def load_account(acct_id):
    with open(ACCOUNTS_FILE) as f:
        accounts = json.load(f)
    for a in accounts:
        if a['id'] == acct_id:
            return a
    print(f"Account '{acct_id}' not found")
    sys.exit(1)


def convert_to_business(account, headless=True):
    session = os.path.expanduser(account['session_path'])
    acct_id = account['id']
    acct_name = account.get('name', acct_id)

    print(f"[{acct_id}] Launching browser (session: {session})...")

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=session,
            headless=headless,
            viewport={'width': 1280, 'height': 900}
        )
        context.set_default_timeout(20000)
        page = context.pages[0] if context.pages else context.new_page()

        try:
            # Step 1: Check if already a business account
            print(f"[{acct_id}] Checking current account status...")
            page.goto('https://ca.pinterest.com/settings/', timeout=TIMEOUT, wait_until='domcontentloaded')
            time.sleep(4)

            # Look for "Convert to business account" or business settings
            body_text = page.locator('body').inner_text(timeout=10000).lower()

            if 'business' in body_text and 'convert to personal' in body_text:
                print(f"[{acct_id}] Already a business account! Nothing to do.")
                return True

            # Step 2: Navigate to business conversion page
            print(f"[{acct_id}] Navigating to business conversion...")
            page.goto('https://ca.pinterest.com/business/convert/', timeout=TIMEOUT, wait_until='domcontentloaded')
            time.sleep(4)

            # Check if we need to log in
            if 'login' in page.url.lower():
                print(f"[{acct_id}] ❌ Session expired — needs re-login")
                return False

            body_text = page.locator('body').inner_text(timeout=10000)
            print(f"[{acct_id}] Page loaded. Looking for conversion form...")

            # Screenshot for debugging
            screenshot_path = f'{WORKSPACE}/convert-{acct_id}-step1.png'
            page.screenshot(path=screenshot_path)
            print(f"[{acct_id}] Screenshot: {screenshot_path}")

            # Step 3: Fill business name if field exists
            business_name_filled = False
            for selector in [
                'input[name="businessName"]',
                'input[placeholder*="business" i]',
                'input[placeholder*="name" i]',
                'input[id*="business"]',
                'input[type="text"]'
            ]:
                try:
                    el = page.locator(selector).first
                    if el.count() > 0 and el.is_visible():
                        el.fill(acct_name)
                        business_name_filled = True
                        print(f"[{acct_id}] Filled business name: {acct_name}")
                        break
                except Exception:
                    continue

            # Step 4: Select business type (Creator / Blogger / etc.)
            for selector in [
                'select[name*="type" i]',
                'select[id*="type" i]',
                'div[role="listbox"]',
                'button:has-text("Business type")',
                'button:has-text("Select")'
            ]:
                try:
                    el = page.locator(selector).first
                    if el.count() > 0 and el.is_visible():
                        el.click()
                        time.sleep(1)
                        # Look for "Creator" or "Blogger" or "Online store"
                        for option_text in ['Creator', 'Blogger', 'Online store', 'Influencer', 'Ecommerce']:
                            try:
                                opt = page.locator(f'div[role="option"]:has-text("{option_text}"), li:has-text("{option_text}"), button:has-text("{option_text}")').first
                                if opt.count() > 0 and opt.is_visible():
                                    opt.click()
                                    print(f"[{acct_id}] Selected business type: {option_text}")
                                    time.sleep(1)
                                    break
                            except Exception:
                                continue
                        break
                except Exception:
                    continue

            # Step 5: Fill website if field exists
            for selector in [
                'input[name*="website" i]',
                'input[placeholder*="website" i]',
                'input[type="url"]'
            ]:
                try:
                    el = page.locator(selector).first
                    if el.count() > 0 and el.is_visible():
                        el.fill('https://wildroseautomations.ca')
                        print(f"[{acct_id}] Filled website")
                        break
                except Exception:
                    continue

            # Screenshot before clicking convert
            screenshot_path2 = f'{WORKSPACE}/convert-{acct_id}-step2.png'
            page.screenshot(path=screenshot_path2)
            print(f"[{acct_id}] Screenshot before submit: {screenshot_path2}")

            # Step 6: Click the convert/create button
            clicked = False
            for selector in [
                'button:has-text("Convert")',
                'button:has-text("Create")',
                'button:has-text("Get started")',
                'button:has-text("Continue")',
                'button:has-text("Next")',
                'button[type="submit"]',
                'div[role="button"]:has-text("Convert")'
            ]:
                try:
                    btn = page.locator(selector).first
                    if btn.count() > 0 and btn.is_visible():
                        btn.click()
                        clicked = True
                        print(f"[{acct_id}] Clicked: {selector}")
                        break
                except Exception:
                    continue

            if not clicked:
                print(f"[{acct_id}] ⚠️ Could not find conversion button — may need manual intervention")
                screenshot_path3 = f'{WORKSPACE}/convert-{acct_id}-manual.png'
                page.screenshot(path=screenshot_path3)
                print(f"[{acct_id}] Screenshot for manual review: {screenshot_path3}")
                # Keep browser open for 60 seconds so we can inspect
                print(f"[{acct_id}] Waiting 30s for inspection...")
                time.sleep(30)
                return False

            time.sleep(5)

            # Step 7: Handle any additional steps (terms, welcome modal, etc.)
            for _ in range(5):
                for sel in ['button:has-text("Next")', 'button:has-text("Done")',
                            'button:has-text("Got it")', 'button:has-text("Finish")',
                            'button:has-text("Skip")', 'button:has-text("OK")',
                            'button:has-text("Continue")', '[aria-label="Close"]']:
                    try:
                        el = page.locator(sel).first
                        if el.count() > 0 and el.is_visible(timeout=2000):
                            el.click()
                            print(f"[{acct_id}] Dismissed: {sel}")
                            time.sleep(2)
                            break
                    except Exception:
                        continue
                else:
                    break

            # Final screenshot
            screenshot_path3 = f'{WORKSPACE}/convert-{acct_id}-done.png'
            page.screenshot(path=screenshot_path3)
            print(f"[{acct_id}] Final screenshot: {screenshot_path3}")

            # Verify
            page.goto('https://ca.pinterest.com/settings/', timeout=TIMEOUT, wait_until='domcontentloaded')
            time.sleep(3)
            body = page.locator('body').inner_text(timeout=10000).lower()
            if 'business' in body:
                print(f"[{acct_id}] ✅ Conversion appears successful!")
                return True
            else:
                print(f"[{acct_id}] ⚠️ Conversion status unclear — check screenshots")
                return False

        except Exception as e:
            print(f"[{acct_id}] ❌ Error: {e}")
            try:
                page.screenshot(path=f'{WORKSPACE}/convert-{acct_id}-error.png')
            except Exception:
                pass
            return False
        finally:
            context.close()


def main():
    parser = argparse.ArgumentParser(description='Convert Pinterest personal account to Business')
    parser.add_argument('--account', required=True, help='Account ID from accounts.json')
    parser.add_argument('--headless', default='true', help='Run headless (default: true)')
    args = parser.parse_args()

    account = load_account(args.account)
    headless = args.headless.lower() != 'false'

    success = convert_to_business(account, headless=headless)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
