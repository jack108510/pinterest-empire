#!/usr/bin/env python3
"""
Pinterest Bulk Pin Generator
Creates a CSV file for Pinterest bulk upload + downloads all pin images
Pinterest bulk upload: https://help.pinterest.com/en/business/article/bulk-create-pins
"""
import csv, os, random, json
from datetime import datetime

WORKSPACE = '/Users/jackserver/.openclaw/workspace/pinterest'
STOCK_DIR = f'{WORKSPACE}/stock'
OUTPUT_DIR = f'{WORKSPACE}/bulk_upload'
CSV_FILE = f'{OUTPUT_DIR}/bulk_pins.csv'

PRODUCTS = [
    {"name": "Collagen Peptides Powder", "url": "https://amzn.to/YOUR_LINK", "benefits": ["Glowing Skin", "Strong Hair", "Joint Support", "Anti-Aging", "Wrinkle Reduction"]},
    {"name": "Probiotic 50 Billion CFU", "url": "https://amzn.to/YOUR_LINK", "benefits": ["Gut Health", "Better Digestion", "Immune Boost", "Less Bloating", "More Energy"]},
    {"name": "Green Superfood Powder", "url": "https://amzn.to/YOUR_LINK", "benefits": ["Natural Energy", "Detox Cleanse", "Nutrient Dense", "Alkalize Body", "Immune Support"]},
    {"name": "Omega-3 Fish Oil Capsules", "url": "https://amzn.to/YOUR_LINK", "benefits": ["Heart Health", "Brain Function", "Reduce Inflammation", "Clear Skin", "Joint Mobility"]},
    {"name": "Magnesium Glycinate", "url": "https://amzn.to/YOUR_LINK", "benefits": ["Deep Sleep", "Muscle Recovery", "Less Anxiety", "Better Focus", "Calm Mind"]},
    {"name": "Vitamin D3 K2 Drops", "url": "https://amzn.to/YOUR_LINK", "benefits": ["Stronger Bones", "Immune Defense", "Mood Boost", "More Energy", "Calcium Absorption"]},
    {"name": "Adaptogen Ashwagandha", "url": "https://amzn.to/YOUR_LINK", "benefits": ["Stress Relief", "Hormone Balance", "Mental Clarity", "Calm Focus", "Better Sleep"]},
    {"name": "Turmeric Curcumin", "url": "https://amzn.to/YOUR_LINK", "benefits": ["Anti-Inflammatory", "Joint Pain Relief", "Antioxidant", "Brain Health", "Heart Health"]},
    {"name": "Apple Cider Vinegar Gummies", "url": "https://amzn.to/YOUR_LINK", "benefits": ["Weight Management", "Detox", "Digestion", "Appetite Control", "Gut Health"]},
    {"name": "Melatonin Sleep Gummies", "url": "https://amzn.to/YOUR_LINK", "benefits": ["Fall Asleep Faster", "Stay Asleep", "Wake Refreshed", "Natural Sleep", "Restful Nights"]},
    {"name": "Biotin Gummies for Hair Growth", "url": "https://amzn.to/YOUR_LINK", "benefits": ["Hair Growth", "Stronger Nails", "Glowing Skin", "Thicker Hair", "Beauty Boost"]},
    {"name": "Elderberry Immune Gummies", "url": "https://amzn.to/YOUR_LINK", "benefits": ["Immune Defense", "Cold Prevention", "Antioxidant", "Daily Wellness", "Vitamin C Boost"]},
    {"name": "Pre-Workout Powder", "url": "https://amzn.to/YOUR_LINK", "benefits": ["Explosive Energy", "Better Focus", "Muscle Pumps", "Endurance", "Fat Burn"]},
    {"name": "Whey Protein Isolate", "url": "https://amzn.to/YOUR_LINK", "benefits": ["Muscle Growth", "Recovery", "Lean Body", "Protein Boost", "Meal Replacement"]},
    {"name": "Dainty Gold Necklace", "url": "https://amzn.to/YOUR_LINK", "benefits": ["Everyday Elegance", "Layered Look", "Minimalist Style", "Gift Ready", "Tarnish Free"]},
    {"name": "Gold Hoop Earrings", "url": "https://amzn.to/YOUR_LINK", "benefits": ["Classic Style", "Effortless Chic", "Versatile", "Lightweight", "Timeless"]},
    {"name": "Silk Pillowcase Set", "url": "https://amzn.to/YOUR_LINK", "benefits": ["Better Hair", "Clearer Skin", "Luxury Sleep", "Anti-Aging", "Cool Sleep"]},
    {"name": "Aesthetic Tote Bag", "url": "https://amzn.to/YOUR_LINK", "benefits": ["Everyday Carry", "Minimalist Design", "Eco Friendly", "Versatile", "Trendy"]},
    {"name": "Matching Lounge Set", "url": "https://amzn.to/YOUR_LINK", "benefits": ["Cozy Comfort", "Aesthetic Vibes", "Matching Set", "Lounging", "Cute Fit"]},
    {"name": "Perfume Discovery Set", "url": "https://amzn.to/YOUR_LINK", "benefits": ["Signature Scent", "Luxury Fragrance", "Gift Idea", "Travel Size", "Aesthetic"]},
]

TITLES = [
    "This Changed My Morning Routine",
    "{benefit} in 30 Days",
    "I Tried {product} for 60 Days",
    "The #1 Supplement for {benefit}",
    "{product} - Worth the Hype?",
    "My Secret to {benefit}",
    "Stop Wasting Money on Wrong Products",
    "{product} - Honest Review",
    "Why I Start Every Day With This",
    "3 Products That Actually Work",
    "The Truth About {product}",
    "{benefit} Starts Here",
    "I Wish I Knew This Sooner",
    "Top Pick for 2026",
    "Game Changer for {benefit}",
    "My Daily Staple",
    "This Changed Everything",
    "Simple Hack for {benefit}",
    "Best I've Ever Tried",
    "Don't Buy Until You Read This",
    "The Morning Stack That Works",
    "5 Signs You Need This",
    "Why Everyone's Talking About It",
    "Real Results With {product}",
    "This Is What Healthy Looks Like",
    "How I Got My Glow Back",
    "From Tired to Radiant",
    "The Routine Behind This Look",
    "Effortless Aesthetic Everyday",
    "My Exact Routine Revealed",
]

DESCRIPTIONS = [
    "{product} has been a game changer for {benefit_lower}. Link in bio to get yours! {tags}",
    "If you want {benefit_lower}, you need to see this. {product} delivers real results. {tags}",
    "After trying everything for {benefit_lower}, {product} is the only thing that worked. {tags}",
    "Top pick for 2026: {product}. Here's why it works for {benefit_lower}. Link below! {tags}",
    "Honest review: {product} gave me {benefit_lower} in just 30 days. See my results. {tags}",
    "Stop scrolling if you want {benefit_lower}. This is the real deal. Link below. {tags}",
    "The product that actually delivers {benefit_lower}. {product} - worth every penny. {tags}",
    "My #1 wellness secret for {benefit_lower}. Full breakdown in link. {tags}",
]

HASHTAGS = ["#HealthAndWellness", "#Supplements", "#HealthyLiving", "#Wellness", 
            "#CleanLiving", "#NaturalHealth", "#FitnessMotivation", "#SelfCare",
            "#HealthyLifestyle", "#Vitamins", "#GutHealth", "#ImmuneSupport",
            "#EnergyBoost", "#BetterSleep", "#AntiAging", "#Aesthetic",
            "#CleanGirlAesthetic", "#ThatGirl", "#WellnessGirlie", "#HealthyHabits"]

BOARDS = ["Healthy Living Tips", "Clean Beauty", "Fitness Motivation", 
          "Self Care Essentials", "Supplement Reviews"]

def generate_pins(count=1000):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    stock_files = [f for f in os.listdir(STOCK_DIR) if f.endswith(('.jpg', '.png'))]
    print(f"Stock images: {len(stock_files)}")
    
    pins = []
    used = set()  # Avoid exact duplicates
    
    for i in range(count):
        product = random.choice(PRODUCTS)
        benefit = random.choice(product["benefits"])
        title = random.choice(TITLES).format(product=product["name"], benefit=benefit)
        desc = random.choice(DESCRIPTIONS).format(
            product=product["name"],
            benefit=benefit,
            benefit_lower=benefit.lower(),
            tags=" ".join(random.sample(HASHTAGS, random.randint(3, 6)))
        )
        board = random.choice(BOARDS)
        stock = random.choice(stock_files)
        
        # Create unique filename
        out_img = f'{OUTPUT_DIR}/pin_{i+1:04d}.jpg'
        
        # Copy stock image to output with pin name
        import shutil
        shutil.copy2(os.path.join(STOCK_DIR, stock), out_img)
        
        pins.append({
            'Image': out_img,
            'Title': title,
            'Description': desc,
            'Destination Link': product["url"],
            'Board': board,
        })
    
    # Write CSV
    with open(CSV_FILE, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['Image', 'Title', 'Description', 'Destination Link', 'Board'])
        writer.writeheader()
        writer.writerows(pins)
    
    print(f"Generated {len(pins)} pins")
    print(f"CSV: {CSV_FILE}")
    print(f"Images: {OUTPUT_DIR}/")
    return pins

if __name__ == '__main__':
    import sys
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    generate_pins(count)
