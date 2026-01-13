#!/usr/bin/env python3
"""
Reddit Scraper for Assassin's Creed SHADOWS Reviews/Critiques
NO API CREDENTIALS REQUIRED - Uses Reddit's public JSON endpoints

OPTIMIZED FOR UNATTENDED RUNNING:
- Long delays to avoid rate limits
- Auto-retry on rate limit (waits 2 minutes)
- Progress tracking
- Safe to leave running

Usage:
    python reddit_scraper_no_api.py          # Full scrape (slow but complete)
    python reddit_scraper_no_api.py --test   # Quick test
    python reddit_scraper_no_api.py --fast   # Faster but may hit limits
"""

import argparse
import csv
import sys
import time
import random
from datetime import datetime
from pathlib import Path

try:
    import requests
    import pandas as pd
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Run: pip install requests pandas")
    sys.exit(1)

# =============================================================================
# CONFIGURATION
# =============================================================================

SUBREDDITS = [
    "assassinscreed",
    "gaming",
    "Games",
    "patientgamers",
]

SEARCH_KEYWORDS = [
    "Shadows review",
    "AC Shadows",
    "Assassin's Creed Shadows",
]

REQUIRED_TERMS = ["shadows", "naoe", "yasuke"]
MIN_TEXT_LENGTH = 100
OUTPUT_FILE = "../data/reddit_posts.csv"

# Timing settings
DELAY_NORMAL = (15, 20)      # Normal delay range (seconds)
DELAY_FAST = (3, 5)          # Fast mode delay
RETRY_WAIT = 120             # Wait 2 minutes on rate limit
MAX_RETRIES = 3              # Max retries per request

# =============================================================================
# Headers
# =============================================================================
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json',
}


def print_progress(current, total, prefix="Progress"):
    """Show progress bar."""
    bar_length = 30
    filled = int(bar_length * current / total)
    bar = "█" * filled + "░" * (bar_length - filled)
    percent = current / total * 100
    print(f"\r{prefix}: [{bar}] {percent:.0f}% ({current}/{total})", end="", flush=True)


def make_request(url, params, delay_range, retry_count=0):
    """Make request with retry logic."""
    
    # Wait before request
    delay = random.uniform(*delay_range)
    print(f" (waiting {delay:.0f}s)", end="", flush=True)
    time.sleep(delay)
    
    try:
        response = requests.get(url, headers=HEADERS, params=params, timeout=30)
        
        if response.status_code == 429:
            if retry_count < MAX_RETRIES:
                print(f"\n    ⚠️  Rate limited! Waiting {RETRY_WAIT}s before retry {retry_count + 1}/{MAX_RETRIES}...")
                time.sleep(RETRY_WAIT)
                return make_request(url, params, delay_range, retry_count + 1)
            else:
                print(f"\n    ❌ Max retries reached, skipping...")
                return None
        
        response.raise_for_status()
        return response.json()
        
    except requests.exceptions.Timeout:
        print(f"\n    ⚠️  Timeout, retrying...")
        if retry_count < MAX_RETRIES:
            return make_request(url, params, delay_range, retry_count + 1)
        return None
    except Exception as e:
        print(f"\n    ❌ Error: {e}")
        return None


def search_subreddit(subreddit, query, delay_range, limit=50):
    """Search a subreddit."""
    url = f"https://www.reddit.com/r/{subreddit}/search.json"
    params = {
        'q': query,
        'restrict_sr': 'on',
        'sort': 'relevance',
        't': 'year',
        'limit': min(limit, 100),
        'raw_json': 1
    }
    return make_request(url, params, delay_range)


def fetch_post_comments(permalink, delay_range, limit=30):
    """Fetch comments from a post."""
    url = f"https://www.reddit.com{permalink}.json"
    params = {'limit': limit, 'raw_json': 1, 'depth': 2}
    return make_request(url, params, delay_range)


def contains_required_terms(text):
    """Check if text contains required terms."""
    text_lower = text.lower()
    return any(term.lower() in text_lower for term in REQUIRED_TERMS)


def is_review_like(text):
    """Check if text looks like a review."""
    if len(text) < MIN_TEXT_LENGTH:
        return False
    
    review_indicators = [
        'game', 'play', 'story', 'gameplay', 'combat', 'stealth',
        'think', 'feel', 'opinion', 'review', 'recommend', 'worth',
        'good', 'bad', 'great', 'terrible', 'love', 'hate', 'enjoy',
        'ubisoft', 'assassin', 'creed'
    ]
    
    text_lower = text.lower()
    matches = sum(1 for ind in review_indicators if ind in text_lower)
    return matches >= 3


def parse_post(post_data, subreddit):
    """Parse a post."""
    data = post_data.get('data', {})
    
    title = data.get('title', '')
    text = data.get('selftext', '')
    combined = f"{title} {text}"
    
    if not contains_required_terms(combined):
        return None
    if len(text) < MIN_TEXT_LENGTH:
        return None
    if not is_review_like(combined):
        return None
    
    created = data.get('created_utc', 0)
    post_date = datetime.fromtimestamp(created) if created else datetime.now()
    
    return {
        'user': data.get('author', '[deleted]'),
        'date': post_date.strftime('%Y-%m-%d'),
        'comment': f"[{title}] {text}".strip()[:5000],
        'score': data.get('score', 0),
        'type': 'post',
    }


def parse_comment(comment_data, subreddit, post_title):
    """Parse a comment."""
    data = comment_data.get('data', {})
    
    if data.get('body') is None:
        return None
    
    text = data.get('body', '')
    
    if not contains_required_terms(text):
        return None
    if len(text) < MIN_TEXT_LENGTH:
        return None
    if not is_review_like(text):
        return None
    
    created = data.get('created_utc', 0)
    comment_date = datetime.fromtimestamp(created) if created else datetime.now()
    
    return {
        'user': data.get('author', '[deleted]'),
        'date': comment_date.strftime('%Y-%m-%d'),
        'comment': text[:5000],
        'score': data.get('score', 0),
        'type': 'comment',
    }


def extract_comments(children, subreddit, post_title):
    """Extract comments recursively."""
    comments = []
    
    for child in children:
        if child.get('kind') != 't1':
            continue
        
        comment = parse_comment(child, subreddit, post_title)
        if comment:
            comments.append(comment)
        
        replies = child.get('data', {}).get('replies')
        if replies and isinstance(replies, dict):
            reply_children = replies.get('data', {}).get('children', [])
            comments.extend(extract_comments(reply_children, subreddit, post_title))
    
    return comments


def main():
    parser = argparse.ArgumentParser(description='Scrape Reddit for AC Shadows reviews')
    parser.add_argument('--test', action='store_true', help='Test mode (quick)')
    parser.add_argument('--fast', action='store_true', help='Fast mode (may hit limits)')
    args = parser.parse_args()
    
    # Set delay based on mode
    if args.test:
        delay_range = DELAY_FAST
        subreddits = SUBREDDITS[:1]
        keywords = SEARCH_KEYWORDS[:1]
        mode = "TEST"
    elif args.fast:
        delay_range = DELAY_FAST
        subreddits = SUBREDDITS
        keywords = SEARCH_KEYWORDS
        mode = "FAST"
    else:
        delay_range = DELAY_NORMAL
        subreddits = SUBREDDITS
        keywords = SEARCH_KEYWORDS
        mode = "FULL (safe for unattended running)"
    
    total_tasks = len(subreddits) * len(keywords)
    estimated_time = total_tasks * (sum(delay_range) / 2 + 10)  # rough estimate
    
    print("=" * 60)
    print("🎮 Reddit Scraper for AC Shadows Reviews")
    print("=" * 60)
    print(f"Mode: {mode}")
    print(f"Delay: {delay_range[0]}-{delay_range[1]}s per request")
    print(f"Retry wait: {RETRY_WAIT}s on rate limit")
    print(f"Estimated time: ~{estimated_time/60:.0f} minutes")
    print("=" * 60)
    print("Safe to leave running! Progress will be shown below.\n")
    
    all_results = []
    task_count = 0
    
    for subreddit in subreddits:
        print(f"\n📍 Scraping r/{subreddit}...")
        
        for keyword in keywords:
            task_count += 1
            print(f"   🔍 [{task_count}/{total_tasks}] '{keyword}'", end="")
            
            result = search_subreddit(subreddit, keyword, delay_range, limit=50)
            
            if result and 'data' in result:
                posts = result['data'].get('children', [])
                posts_found = 0
                comments_found = 0
                
                for post in posts:
                    parsed_post = parse_post(post, subreddit)
                    if parsed_post:
                        all_results.append(parsed_post)
                        posts_found += 1
                    
                    permalink = post['data'].get('permalink', '')
                    title = post['data'].get('title', '')
                    
                    if permalink and contains_required_terms(title):
                        print(f"\n      📝 Fetching comments...", end="")
                        comment_result = fetch_post_comments(permalink, delay_range, limit=30)
                        if comment_result and len(comment_result) > 1:
                            comment_children = comment_result[1].get('data', {}).get('children', [])
                            comments = extract_comments(comment_children, subreddit, title)
                            all_results.extend(comments)
                            comments_found += len(comments)
                
                print(f"\n      ✅ {posts_found} posts, {comments_found} comments")
            else:
                print(f"\n      ⚪ No results")
    
    # Process and save
    df = pd.DataFrame(all_results)
    
    if not df.empty:
        df = df.drop_duplicates(subset=['comment'])
        df = df.sort_values('score', ascending=False)
    
    output_path = Path(__file__).parent / OUTPUT_FILE
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, quoting=csv.QUOTE_ALL)
    
    print("\n" + "=" * 60)
    print("🎉 SCRAPING COMPLETE!")
    print("=" * 60)
    print(f"Total reviews: {len(df)}")
    if not df.empty:
        print(f"  Posts: {len(df[df['type'] == 'post'])}")
        print(f"  Comments: {len(df[df['type'] == 'comment'])}")
    print(f"Saved to: {output_path.absolute()}")
    print("=" * 60)
    
    if not df.empty:
        print("\n📊 Top 3 reviews by score:")
        for i, row in df.head(3).iterrows():
            preview = row['comment'][:100] + "..." if len(row['comment']) > 100 else row['comment']
            print(f"\n  [{row['score']}] {row['user']}: {preview}")


if __name__ == "__main__":
    main()
