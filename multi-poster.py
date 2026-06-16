#!/usr/bin/env python3
"""
Pinterest Multi-Account Poster
Reads accounts from accounts.json, runs scheduled accounts sequentially.
Usage:
  python multi-poster.py --all              # Run all accounts scheduled for current hour
  python multi-poster.py --account <id>     # Run a single account
  python multi-poster.py --account <id> --dry-run
"""
import json, os, sys, time, random, argparse, signal
from datetime import datetime
from pathlib import Path

PIN_TIMEOUT = 90  # seconds before a single pin attempt is killed

WORKSPACE = '/Users/jackserver/.openclaw/workspace/pinterest'
LOGS_DIR = '/Users/jackserver/.openclaw/workspace/logs'
ACCOUNTS_FILE = f'{WORKSPACE}/accounts.json'
HISTORY_FILE = f'{WORKSPACE}/posted_history.json'
TIMEOUT = 60000  # 60s page load timeout
DEDUP_DAYS = 7
PRUNE_DAYS = 30
DEFAULT_PIN_COUNT = 100

os.makedirs(LOGS_DIR, exist_ok=True)


def get_logger(account_id):
    log_file = f'{LOGS_DIR}/pinterest-{account_id}.log'

    def log(msg):
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        line = f"[{ts}] {msg}"
        print(line)
        with open(log_file, 'a') as f:
            f.write(line + '\n')

    return log


def load_accounts():
    with open(ACCOUNTS_FILE) as f:
        accounts = json.load(f)
    return [account for account in accounts if account.get('enabled', True)]


def get_stock_images(stock_dir):
    exts = ('.jpg', '.jpeg', '.png', '.webp')
    return [os.path.join(stock_dir, f) for f in os.listdir(stock_dir)
            if f.lower().endswith(exts)]


def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE) as f:
            return json.load(f)
    return {}


def save_history(history):
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2)


def prune_history(history):
    """Remove entries older than PRUNE_DAYS for each account."""
    from datetime import timedelta
    cutoff = (datetime.now() - timedelta(days=PRUNE_DAYS)).isoformat()
    for acct_id in history:
        history[acct_id] = [e for e in history[acct_id] if e.get('date', '') >= cutoff]
    return history


def is_recently_posted(history, account_id, product, title, image=None):
    """Check if same product+title OR same image was posted in last DEDUP_DAYS."""
    from datetime import timedelta
    cutoff = (datetime.now() - timedelta(days=DEDUP_DAYS)).isoformat()
    image_base = os.path.basename(image) if image else None
    for entry in history.get(account_id, []):
        if entry.get('date', '') < cutoff:
            continue
        # Same title+product = duplicate
        if entry.get('product') == product and entry.get('title') == title:
            return True
        # Same image = duplicate
        if image_base and entry.get('image') == image_base:
            return True
    return False


def record_post(history, account_id, pin):
    history.setdefault(account_id, []).append({
        'title': pin['title'],
        'product': pin['product'],
        'image': os.path.basename(pin['image']) if pin.get('image') else '',
        'date': datetime.now().isoformat(),
    })
    history = prune_history(history)
    save_history(history)


def create_working_page(context):
    """Always use a fresh tab to avoid stale Pinterest builder state."""
    page = context.new_page()
    page.set_default_timeout(15000)
    return page


def page_body_text(page):
    try:
        return page.locator('body').inner_text(timeout=5000)
    except Exception:
        return ''


def ensure_logged_in(page):
    if 'login' in page.url.lower():
        raise RuntimeError('Pinterest session is logged out')
    body = page_body_text(page).lower()
    if 'log in' in body and 'create pin' not in body:
        raise RuntimeError('Pinterest session needs login')


def ensure_pin_builder_ready(page):
    """Navigate to the builder and recover if Pinterest lands on an odd state."""
    last_error = None
    for _ in range(3):
        try:
            page.goto('https://ca.pinterest.com/pin-builder/', timeout=TIMEOUT, wait_until='domcontentloaded')
            time.sleep(3)
            for _ in range(5):
                page.keyboard.press('Escape')
                time.sleep(0.2)

            ensure_logged_in(page)

            file_input = page.locator('input[type=file]').first
            title_input = page.locator('textarea[id^="pin-draft-title"], textarea[placeholder="Add your title"], #storyboard-selector-title').first
            link_input = page.locator('textarea[id^="pin-draft-link"], textarea[placeholder="Add a destination link"], #WebsiteField').first
            file_input.wait_for(state='attached', timeout=10000)
            title_input.wait_for(state='visible', timeout=10000)
            link_input.wait_for(state='visible', timeout=10000)
            return
        except Exception as e:
            last_error = e
            try:
                page.goto('https://ca.pinterest.com/pin-creation-tool/', timeout=TIMEOUT, wait_until='domcontentloaded')
                time.sleep(2)
                page.evaluate("""() => {
                    const all = Array.from(document.querySelectorAll('button, div, span, a'));
                    const candidate = all.find((el) => {
                        const text = (el.textContent || '').trim();
                        return text === 'Create new' || text === 'Create Pin';
                    });
                    if (candidate) candidate.click();
                }""")
                time.sleep(2)
            except Exception:
                pass
    raise RuntimeError(f'pin builder not ready: {last_error}')


def fill_first_visible(page, selectors, value):
    for selector in selectors:
        try:
            el = page.locator(selector).first
            if el.count() == 0 or not el.is_visible():
                continue
            el.fill('')
            el.fill(value)
            return True
        except Exception:
            continue
    return False


def find_current_board_label(page):
    for selector in [
        'button[aria-label*="board" i]',
        'button:has-text("Main")',
        'button:has-text("Choose a board")',
        'button:has-text("Select")'
    ]:
        try:
            el = page.locator(selector).first
            if el.count() == 0 or not el.is_visible():
                continue
            text = (el.inner_text(timeout=2000) or '').strip()
            if text:
                return text
        except Exception:
            continue
    return ''


def select_board(page, board_name):
    current_board = find_current_board_label(page)
    if current_board and board_name.lower() in current_board.lower():
        return True

    board_button = None
    for selector in [
        'button[aria-label*="board" i]',
        'button:has-text("Main")',
        'button:has-text("Choose a board")',
        'button:has-text("Select")'
    ]:
        try:
            el = page.locator(selector).first
            if el.count() > 0 and el.is_visible():
                board_button = el
                break
        except Exception:
            continue

    if board_button is None:
        return True

    try:
        board_button.click()
        time.sleep(2)
    except Exception:
        return True

    for selector in [
        f'button:has-text("{board_name}")',
        f'li:has-text("{board_name}")',
        f'span:has-text("{board_name}")',
        f'div[role="option"]:has-text("{board_name}")'
    ]:
        try:
            target = page.locator(selector).first
            if target.count() > 0 and target.is_visible():
                target.click()
                time.sleep(1)
                return True
        except Exception:
            continue

    # If the desired board is unavailable, use the current/default board instead of blocking the post.
    page.keyboard.press('Escape')
    time.sleep(0.5)
    return True


def clear_drafts(page, log):
    try:
        page.goto('https://ca.pinterest.com/pin-creation-tool/', timeout=TIMEOUT, wait_until='domcontentloaded')
        time.sleep(3)
        select_all = page.locator('#storyboard-drafts-sidebar-bulk-select-checkbox')
        if select_all.count() == 0 or not select_all.first.is_visible():
            return
        select_all.first.click()
        time.sleep(1)
        delete_btn = page.locator('button[aria-label*="delete" i], button[aria-label*="Delete" i], button:has-text("Delete")')
        if delete_btn.count() == 0:
            return
        delete_btn.first.click()
        time.sleep(1)
        confirm = page.locator('button:has-text("Delete")')
        if confirm.count() > 1:
            confirm.last.click()
        elif confirm.count() > 0:
            confirm.first.click()
        time.sleep(2)
        log('  Cleared drafts')
    except Exception as e:
        log(f'  Draft clear skipped: {e}')


def generate_pin(account, history=None):
    images = get_stock_images(account['stock_dir'])
    # Try up to 20 times to find a non-duplicate combo
    for _ in range(20):
        product = random.choice(account['products'])
        benefit = random.choice(product['benefits'])
        template = random.choice(account['title_templates'])
        title = template.format(product=product['name'], benefit=benefit)[:100]
        image = random.choice(images) if images else None
        if history is None or not is_recently_posted(history, account['id'], product['name'], title, image):
            break
    board = random.choice(account['boards'])
    link = random.choice(account['affiliate_links'])

    return {
        'image': image,
        'title': title,
        'link': link,
        'board': board,
        'product': product['name'],
        'benefit': benefit,
    }


def post_pin(context, pin):
    """Post a single pin in a fresh page. Returns True on success."""
    page = create_working_page(context)
    try:
        ensure_pin_builder_ready(page)

        if not pin['image']:
            return False

        # Upload image after the form is definitely present.
        page.locator('input[type=file]').first.set_input_files(pin['image'])
        time.sleep(5)

        title_filled = fill_first_visible(page, [
            'textarea[id^="pin-draft-title"]',
            '#storyboard-selector-title',
            'textarea[placeholder="Add your title"]',
            'textarea[placeholder="Add your title."]',
            'h1[contenteditable]',
            'div[role="textbox"]:first-of-type'
        ], pin['title'])
        if not title_filled:
            print(f"   ⚠ Could not fill title — UI changed?")
            return False

        link_filled = fill_first_visible(page, [
            'textarea[id^="pin-draft-link"]',
            '#WebsiteField',
            'textarea[placeholder="Add a destination link"]'
        ], pin['link'])
        if not link_filled:
            print("   ⚠ Could not fill destination link")
            return False
        time.sleep(1)

        if not select_board(page, pin['board']):
            print("   ⚠ Could not confirm board selection")
            return False

        # Publish
        publish_btn = page.get_by_role('button', name='Publish')
        if publish_btn.count() > 0:
            publish_btn.first.click()
            time.sleep(6)
            
            # Verify the pin was actually created — look for confirmation
            for _ in range(3):
                confirmed = page.evaluate("""() => {
                    const text = document.body.innerText;
                    return text.includes('You created a Pin') || text.includes('You created a Pin!') || text.includes('Your Pin is now');
                }""")
                if confirmed:
                    return True
                time.sleep(2)

            # If no confirmation, check if we're still on pin-builder (failed)
            if 'pin-builder' in page.url:
                print("    ⚠ Publish failed — still on pin builder (board not selected?)")
                return False
            
            return True
        print("    ⚠ No Publish button found")
        return False

    except Exception as e:
        print(f"    Error: {e}")
        return False
    finally:
        page.close()


def _post_pin_with_timeout(context, pin, log, timeout_sec):
    """Wrapper that runs post_pin with a hard SIGALRM timeout. Returns 'ok', 'retry', or 'timeout'."""
    def _handler(signum, frame):
        raise TimeoutError(f"pin timed out after {timeout_sec}s")

    old_handler = signal.signal(signal.SIGALRM, _handler)
    signal.alarm(timeout_sec)
    try:
        if post_pin(context, pin):
            return 'ok'
        else:
            return 'retry'
    except TimeoutError:
        log(f"    ⏱ Pin timed out after {timeout_sec}s — killing stuck page")
        try:
            for pg in context.pages:
                pg.close()
        except Exception:
            pass
        time.sleep(2)
        return 'timeout'
    except Exception as e:
        log(f"    Error: {str(e)[:120]}")
        return 'retry'
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)


def run_account(account, dry_run=False, count=DEFAULT_PIN_COUNT):
    log = get_logger(account['id'])
    log(f"=== Starting {account['name']} ({account['id']}) — {count} pins ===")
    history = load_history()

    if dry_run:
        for i in range(3):
            pin = generate_pin(account, history)
            log(f"[DRY {i+1}] {pin['product']} | {pin['benefit']} | {pin['board']} | {pin['title'][:60]}")
        log(f"[DRY RUN] Would post {count} pins for {account['id']}")
        return

    from playwright.sync_api import sync_playwright

    session = os.path.expanduser(account['session_path'])
    posted = 0
    failed = 0

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=session,
            headless=True,
            viewport={'width': 1280, 'height': 900}
        )
        context.set_default_timeout(15000)

        try:
            draft_page = create_working_page(context)
            clear_drafts(draft_page, log)
            draft_page.close()

            for i in range(count):
                pin = generate_pin(account, history)
                log(f"[{i+1}/{count}] {pin['product']} → {pin['board']}")

                result = _post_pin_with_timeout(context, pin, log, PIN_TIMEOUT)

                if result == 'ok':
                    posted += 1
                    record_post(history, account['id'], pin)
                    log(f"  ✅ {pin['title'][:60]}")
                elif result == 'retry':
                    log(f"  ⏳ Retrying...")
                    time.sleep(10)
                    result2 = _post_pin_with_timeout(context, pin, log, PIN_TIMEOUT)
                    if result2 == 'ok':
                        posted += 1
                        record_post(history, account['id'], pin)
                        log(f"  ✅ Retry OK: {pin['title'][:60]}")
                    else:
                        failed += 1
                        log(f"  ❌ Failed: {pin['title'][:60]} (after retry: {result2})")
                else:
                    failed += 1
                    log(f"  ❌ Failed: {pin['title'][:60]} ({result})")

                wait = random.randint(5, 15)
                time.sleep(wait)

        finally:
            context.close()

    log(f"=== Done {account['id']}: {posted} posted, {failed} failed ===")


def main():
    parser = argparse.ArgumentParser(description='Pinterest Multi-Account Poster')
    parser.add_argument('--account', help='Run a single account by ID')
    parser.add_argument('--all', action='store_true', help='Run all accounts scheduled for current hour')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be posted without posting')
    parser.add_argument('--count', type=int, default=DEFAULT_PIN_COUNT, help='Number of pins to post')
    args = parser.parse_args()

    accounts = load_accounts()

    if args.account:
        acct = next((a for a in accounts if a['id'] == args.account), None)
        if not acct:
            print(f"Account '{args.account}' not found in {ACCOUNTS_FILE}")
            sys.exit(1)
        run_account(acct, dry_run=args.dry_run, count=args.count)

    elif args.all:
        current_hour = datetime.now().hour
        scheduled = [a for a in accounts if a.get('posting_hour') == current_hour]
        if not scheduled:
            print(f"No accounts scheduled for hour {current_hour}")
            sys.exit(0)
        for acct in scheduled:
            run_account(acct, dry_run=args.dry_run, count=args.count)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
