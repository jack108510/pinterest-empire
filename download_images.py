#!/usr/bin/env python3
"""Download stock images from Unsplash (no API key needed - uses source URLs)."""
import os, time, random, urllib.request

STOCK_DIR = '/Users/jackserver/.openclaw/workspace/pinterest/stock'
os.makedirs(STOCK_DIR, exist_ok=True)

# Count existing
existing = len([f for f in os.listdir(STOCK_DIR) if f.lower().endswith(('.jpg','.jpeg','.png','.webp'))])
print(f"Existing images: {existing}")

# Unsplash source allows free downloads via topic URLs
# Format: https://source.unsplash.com/800x800/?{query}
# Each request returns a random image matching the query

searches = [
    'supplements', 'wellness', 'vitamins', 'health', 'fitness',
    'nutrition', 'green+powder', 'collagen', 'yoga', 'self+care',
    'smoothie', 'healthy+food', 'workout', 'natural+remedies', 'herbal+tea',
    'superfood', 'protein', 'detox', 'meditation', 'healthy+lifestyle',
    'gym', 'fruits+vegetables', 'green+juice', 'health+supplement',
    'probiotics', 'omega3', 'turmeric', 'magnesium', 'adaptogens',
]

TARGET = 500
downloaded = 0
failed = 0

headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}

for i in range(TARGET):
    query = random.choice(searches)
    filename = f"unsplash_{i+1:04d}.jpg"
    filepath = os.path.join(STOCK_DIR, filename)
    
    if os.path.exists(filepath):
        continue
    
    url = f"https://source.unsplash.com/800x800/?{query}"
    
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
            if len(data) > 5000:  # Valid image
                with open(filepath, 'wb') as f:
                    f.write(data)
                downloaded += 1
                if downloaded % 50 == 0:
                    print(f"  Downloaded {downloaded}/{TARGET}")
            else:
                failed += 1
    except Exception as e:
        failed += 1
        if failed <= 5:
            print(f"  Error: {e}")
    
    # Rate limit - be polite
    time.sleep(0.3)

total = len([f for f in os.listdir(STOCK_DIR) if f.lower().endswith(('.jpg','.jpeg','.png','.webp'))])
print(f"\nDone! Downloaded: {downloaded}, Failed: {failed}")
print(f"Total images in stock: {total}")
