import requests
from bs4 import BeautifulSoup
import pandas as pd
import datetime
import os
import re
import json

# --- CONFIGURATION ---
DATA_FILE = "data/tweets.json"
KEYWORDS = [
    '"Russian Navy" OR "VMF"',
    '"Chinese Navy" OR "PLAN Navy" OR "PLA Navy"',
    '"Northern Fleet" Russia',
    '"South Sea Fleet" China'
]
MAX_RESULTS_PER_KEYWORD = 5

def load_existing_data():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def save_data(data):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def search_twitter_via_google(keyword):
    """
    Searches Google for recent Twitter links to avoid direct X scraping blocks.
    """
    query = f'site:twitter.com {keyword}'
    # We use a standard User-Agent to look like a browser
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    # Note: Google may rate limit this if run too frequently.
    # In a production env, consider using an API like Serper or SerpApi if this fails.
    url = f"https://www.google.com/search?q={query}&tbs=qdr:d" # tbs=qdr:d means "past 24 hours"
    
    print(f"Searching for: {keyword}...")
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        
        links = []
        # Parse Google search results
        for a in soup.find_all('a', href=True):
            href = a['href']
            # Look for actual tweet links
            if "twitter.com" in href or "x.com" in href:
                if "/status/" in href:
                    # Clean the URL (remove Google tracking params)
                    clean_url = re.search(r'(https?://(www\.)?(twitter|x)\.com/[^&]+)', href)
                    if clean_url:
                        full_url = clean_url.group(1)
                        # Create a readable title from the URL or anchor text
                        title = a.get_text(strip=True) or full_url
                        links.append({
                            "url": full_url,
                            "text": title,
                            "keyword": keyword,
                            "date": datetime.datetime.now().strftime("%Y-%m-%d")
                        })
        return links[:MAX_RESULTS_PER_KEYWORD]
    except Exception as e:
        print(f"Error searching for {keyword}: {e}")
        return []

def update_readme(tweets):
    """
    Regenerates the README.md file to display the dashboard.
    """
    # Sort tweets by date (newest first)
    tweets.sort(key=lambda x: x['date'], reverse=True)
    
    # Keep only the last 50 tweets to keep README clean
    display_tweets = tweets[:50]
    
    markdown_content = f"""
# 🚢 Naval OSINT Monitor (Russia & China)
**Automated Daily X (Twitter) Tracker**

> Last Updated: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M UTC")}

This repository tracks open-source intelligence on Russian and Chinese naval activities.

## 📡 Latest Intercepts
| Date | Topic | Tweet / Source |
|------|-------|----------------|
"""
    
    for t in display_tweets:
        # Format the link to look nice
        clean_text = t['text'].replace(" - Twitter", "").replace("Twitter", "")[:60] + "..."
        cleaned_keyword = t['keyword'].replace(' OR ', '/').replace('"', '')

        markdown_content += "| {0} | {1} | [{2}]({3}) |\n".format(
            t['date'],
            cleaned_keyword,
            clean_text,
            t['url']
        )
        
    markdown_content += """
---
*Automated by GitHub Actions & Python. Data is sourced via Search Engine Indexing to respect platform limitations.*
"""
    
    with open("README.md", "w") as f:
        f.write(markdown_content)

def main():
    existing_data = load_existing_data()
    existing_urls = {item['url'] for item in existing_data}
    
    new_data = []
    
    for keyword in KEYWORDS:
        results = search_twitter_via_google(keyword)
        for res in results:
            if res['url'] not in existing_urls:
                new_data.append(res)
                existing_urls.add(res['url'])
    
    if new_data:
        print(f"Found {len(new_data)} new items.")
        all_data = new_data + existing_data
        save_data(all_data)
        update_readme(all_data)
    else:
        print("No new relevant items found today.")

if __name__ == "__main__":
    main()