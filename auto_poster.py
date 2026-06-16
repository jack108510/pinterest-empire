#!/usr/bin/env python3
"""
Pinterest Auto-Poster v2 — 100 pins/day using stock images
No DALL-E needed. Reuses stock images with different titles/descriptions.
Posts every 15 minutes = 96 pins/day
"""
import json, os, time, random
from datetime import datetime

WORKSPACE = '/Users/jackserver/.openclaw/workspace/pinterest'
STOCK_DIR = f'{WORKSPACE}/stock'
LOG_FILE = f'{WORKSPACE}/poster.log'
SESSION = os.path.expanduser('~/.pinterest-session')

# Affiliate products — update URLs with your real affiliate links
AFFILIATE_LINKS = [
    "https://amzn.to/4doKedR",
    "https://amzn.to/4d3oGC7",
    "https://amzn.to/4d32nNb",
    "https://amzn.to/4tjW5i1",
    "https://amzn.to/4f7I83g",
    "https://amzn.to/42T8Fdj",
    "https://amzn.to/4tpKJte",
    "https://amzn.to/4f1GjoC",
    "https://amzn.to/3Pm3sHZ",
    "https://amzn.to/4uuyNXT",
    "https://amzn.to/4erIAJF",
    "https://amzn.to/3P4WG9s",
    "https://amzn.to/48BbHqc",
    "https://amzn.to/4tQwU7X",
    "https://amzn.to/4f0SkKT",
]

PRODUCTS = [
    {"name": "Collagen Peptides", "url": AFFILIATE_LINKS[0], "benefits": ["Glowing Skin", "Strong Hair", "Joint Support", "Anti-Aging"]},
    {"name": "Probiotic 50 Billion", "url": AFFILIATE_LINKS[1], "benefits": ["Gut Health", "Better Digestion", "Immune Boost", "Less Bloating"]},
    {"name": "Green Superfood Powder", "url": AFFILIATE_LINKS[2], "benefits": ["Natural Energy", "Detox", "Nutrient Dense", "Alkalize Your Body"]},
    {"name": "Omega-3 Fish Oil", "url": AFFILIATE_LINKS[3], "benefits": ["Heart Health", "Brain Function", "Reduce Inflammation", "Clear Skin"]},
    {"name": "Magnesium Glycinate", "url": AFFILIATE_LINKS[4], "benefits": ["Deep Sleep", "Muscle Recovery", "Less Anxiety", "Better Focus"]},
    {"name": "Vitamin D3 + K2", "url": AFFILIATE_LINKS[5], "benefits": ["Stronger Bones", "Immune Defense", "Mood Boost", "More Energy"]},
    {"name": "Adaptogen Blend", "url": AFFILIATE_LINKS[6], "benefits": ["Stress Relief", "Hormone Balance", "Mental Clarity", "Calm Focus"]},
    {"name": "Turmeric Curcumin", "url": AFFILIATE_LINKS[7], "benefits": ["Anti-Inflammatory", "Joint Pain Relief", "Antioxidant", "Brain Health"]},
    {"name": "Apple Cider Vinegar Gummies", "url": AFFILIATE_LINKS[8], "benefits": ["Weight Management", "Detox", "Digestion", "Appetite Control"]},
    {"name": "Melatonin Sleep Gummies", "url": AFFILIATE_LINKS[9], "benefits": ["Fall Asleep Faster", "Stay Asleep", "Wake Refreshed", "Natural Sleep Aid"]},
    {"name": "Elderberry Immune Gummies", "url": AFFILIATE_LINKS[10], "benefits": ["Immune Defense", "Cold Season Ready", "Antioxidant", "Daily Wellness"]},
    {"name": "Biotin Hair Growth", "url": AFFILIATE_LINKS[11], "benefits": ["Hair Growth", "Stronger Nails", "Glowing Skin", "Thicker Hair"]},
    {"name": "Pre-Workout Energy", "url": AFFILIATE_LINKS[12], "benefits": ["Explosive Energy", "Better Focus", "Endurance", "No Crash"]},
    {"name": "Ashwagandha Root", "url": AFFILIATE_LINKS[13], "benefits": ["Stress Relief", "Better Sleep", "Calm Mind", "Cortisol Balance"]},
    {"name": "Multivitamin Gummies", "url": AFFILIATE_LINKS[14], "benefits": ["Complete Nutrition", "Daily Essentials", "Energy Boost", "Immune Support"]},
]

HASHTAGS = ["#HealthAndWellness", "#Supplements", "#HealthyLiving", "#Wellness", "#CleanLiving", 
            "#NaturalHealth", "#FitnessMotivation", "#SelfCare", "#HealthyLifestyle", "#Vitamins",
            "#GutHealth", "#ImmuneSupport", "#EnergyBoost", "#BetterSleep", "#AntiAging"]

TITLES = [
    "This Changed My Morning Routine",
    "{benefit} in 30 Days — Here's How",
    "I Tried {product} for 60 Days",
    "The #1 Supplement Everyone Needs",
    "{product}: Worth the Hype?",
    "My Secret to {benefit}",
    "Stop Wasting Money on the Wrong Supplements",
    "{product} — Honest Review",
    "Why I Start Every Day With {product}",
    "3 Supplements That Actually Work",
    "The Truth About {product}",
    "{benefit} Starts Here",
    "I Wish I Knew This Sooner",
    "Top Supplement Pick for 2026",
    "Game Changer for {benefit}",
    "Doctors Recommend This For {benefit}",
    "My Daily Wellness Staple",
    "{product} Changed Everything",
    "Simple Hack for {benefit}",
    "Best Supplement I've Ever Tried",
    "Don't Buy {product} Until You Read This",
    "The Morning Supplement Stack That Works",
    "5 Signs You Need {product}",
    "Why Everyone's Talking About {product}",
    "Real Results With {product}",
]

DESCRIPTIONS = [
    "{product} has been a game changer for {benefit_lower}. See why thousands are switching. Link below! {tags}",
    "I've tried everything for {benefit_lower} and {product} is the only thing that worked. Here's my experience. {tags}",
    "If you're struggling with {benefit_lower}, you need to see this. {product} delivers real results. {tags}",
    "Top pick for 2026: {product}. Here's why it works for {benefit_lower}. Link in bio! {tags}",
    "My #1 wellness secret: {product}. {benefit} in weeks, not months. See the science. {tags}",
    "Honest review after 60 days of {product}. The {benefit_lower} results speak for themselves. {tags}",
    "Stop scrolling if you want {benefit_lower}. {product} is the real deal. Link below. {tags}",
    "After years of trying supplements, {product} finally gave me {benefit_lower}. Here's why. {tags}",
    "The supplement that actually delivers {benefit_lower}. {product} — worth every penny. {tags}",
    "3 months on {product} and the {benefit_lower} is incredible. Full breakdown in link. {tags}",
]

BOARDS = ["Healthy Living Tips", "Clean Beauty", "Fitness Motivation", "Self Care Essentials", "Supplement Reviews"]

def log(msg):
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, 'a') as f:
        f.write(line + '\n')

def get_stock_image():
    """Pick a random stock image"""
    files = [f for f in os.listdir(STOCK_DIR) if f.endswith(('.jpg', '.png'))]
    if not files:
        return None
    return os.path.join(STOCK_DIR, random.choice(files))

def generate_pin():
    """Generate random pin content"""
    product = random.choice(PRODUCTS)
    benefit = random.choice(product["benefits"])
    title = random.choice(TITLES).format(product=product["name"], benefit=benefit)
    desc = random.choice(DESCRIPTIONS).format(
        product=product["name"],
        benefit=benefit,
        benefit_lower=benefit.lower(),
        tags=" ".join(random.sample(HASHTAGS, 4))
    )
    board = random.choice(BOARDS)
    image = get_stock_image()
    
    return {
        "image": image,
        "title": title,
        "description": desc,
        "link": product["url"],
        "board": board,
        "product": product["name"]
    }

def post_pin(pin):
    """Post a pin to Pinterest"""
    from playwright.sync_api import sync_playwright
    
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=SESSION,
            headless=True,
            viewport={'width': 1280, 'height': 900}
        )
        page = context.pages[0] if context.pages else context.new_page()
        
        try:
            page.goto('https://ca.pinterest.com/pin-builder/', timeout=60000)
            time.sleep(5)
            for _ in range(5):
                page.keyboard.press('Escape')
                time.sleep(0.2)
            
            # Upload image
            page.locator('input[type=file]').first.set_input_files(pin['image'])
            time.sleep(3)
            
            # Fill title
            page.locator('textarea[placeholder="Add your title"]').first.fill(pin['title'][:100])
            
            # Fill link
            page.locator('textarea[placeholder="Add a destination link"]').first.fill(pin['link'])
            time.sleep(1)
            
            # Select board
            board_btn = page.evaluate('''() => {
                const all = document.querySelectorAll('div, button, span');
                for (const el of all) {
                    const t = el.textContent.trim();
                    if (t === 'Main' || t === 'Select') {
                        const rect = el.getBoundingClientRect();
                        if (rect.height > 0 && rect.x > 700) return {x: rect.x + rect.width/2, y: rect.y + rect.height/2};
                    }
                }
                return null;
            }''')
            
            if board_btn:
                page.mouse.click(board_btn['x'], board_btn['y'])
                time.sleep(2)
                
                target = page.evaluate(f'''() => {{
                    const all = document.querySelectorAll('div, span, li');
                    for (const el of all) {{
                        if (el.textContent.trim() === '{pin["board"]}') {{
                            const rect = el.getBoundingClientRect();
                            if (rect.height > 0) return {{x: rect.x + rect.width/2, y: rect.y + rect.height/2}};
                        }}
                    }}
                    return null;
                }}''')
                
                if target:
                    page.mouse.click(target['x'], target['y'])
                    time.sleep(1)
            
            # Click Publish
            publish_btn = page.get_by_role('button', name='Publish')
            if publish_btn.count() > 0:
                publish_btn.first.click()
                time.sleep(5)
                return True
            return False
            
        except Exception as e:
            log(f"  Error: {e}")
            return False
        finally:
            context.close()

def run(count=100):
    log(f"Starting batch of {count} pins...")
    posted = 0
    failed = 0
    
    for i in range(count):
        pin = generate_pin()
        log(f"[{i+1}/{count}] {pin['product']} → {pin['board']}")
        
        if post_pin(pin):
            posted += 1
            log(f"  ✅ Posted: {pin['title'][:50]}")
        else:
            # Retry once
            log(f"  ⏳ Retrying: {pin['title'][:50]}")
            time.sleep(10)
            if post_pin(pin):
                posted += 1
                log(f"  ✅ Posted on retry: {pin['title'][:50]}")
            else:
                failed += 1
                log(f"  ❌ Failed: {pin['title'][:50]}")
        
        # Wait between pins (Pinterest rate limiting)
        wait = random.randint(5, 15)
        time.sleep(wait)
    
    log(f"Batch done: {posted} posted, {failed} failed")
    return posted

if __name__ == '__main__':
    import sys
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    run(count)
