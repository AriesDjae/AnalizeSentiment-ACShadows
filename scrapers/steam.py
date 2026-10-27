import requests
import csv
import time
import sys
from datetime import datetime, timezone
from pathlib import Path

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"


def convert_timestamp(ts):
    """Convert UNIX timestamp → '27 March 2024' """
    try:
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        return dt.strftime("%d %B %Y")  # ex: 27 March 2024
    except (TypeError, ValueError, OverflowError, OSError):
        return ""


def fetch_reviews_api(appid, max_per_page=100, language="english"):
    url = f"https://store.steampowered.com/appreviews/{appid}"
    cursor = "*"
    all_reviews = []
    seen_ids = set()
    page = 1

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Referer": f"https://store.steampowered.com/app/{appid}/",
    }

    while True:
        params = {
            "json": 1,
            "filter": "all",
            "language": language,
            "day_range": 9223372036854775807,
            "num_per_page": max_per_page,
            "cursor": cursor
        }

        print(f"[INFO] Fetching page {page} ...")

        # Retry attempts
        for attempt in range(5):
            try:
                resp = requests.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=50
                )
                resp.raise_for_status()
                data = resp.json()
                break
            except Exception as e:
                print(f"[WARN] Attempt {attempt+1}/5 error: {e}")
                time.sleep(3)
        else:
            print("[ERROR] Failed after 5 retries")
            break

        reviews = data.get("reviews", [])
        if not reviews:
            print("[INFO] No more reviews.")
            break

        new_on_page = 0
        for r in reviews:
            # Steam cursor kadang mengulang halaman -> dedup berdasarkan ID review
            review_id = r.get("recommendationid")
            if review_id in seen_ids:
                continue
            seen_ids.add(review_id)
            new_on_page += 1

            unix_time = r.get("timestamp_created", 0)

            all_reviews.append({
                "user": r.get("author", {}).get("steamid", ""),
                "date": convert_timestamp(unix_time),
                "comment": r.get("review", "").replace("\r", " ").replace("\n", " "),
                "helpful": r.get("votes_up", 0),
                "recommended": "Recommended" if r.get("voted_up") else "Not Recommended"
            })

        next_cursor = data.get("cursor")
        if not next_cursor or next_cursor == cursor or new_on_page == 0:
            break
        cursor = next_cursor

        page += 1
        time.sleep(1)

    return all_reviews


def save_csv(appid, rows):
    OUTPUT_DIR.mkdir(exist_ok=True)
    filename = OUTPUT_DIR / "steam_reviews.csv"  # nama yang dibaca pipeline (acs_sentiment.config)

    with open(filename, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["user", "date", "comment", "helpful", "recommended"]
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n✅ Saved {len(rows)} reviews to {filename}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scrapers/steam.py <appid>")
        sys.exit(1)

    appid = sys.argv[1]
    reviews = fetch_reviews_api(appid, language="english")
    save_csv(appid, reviews)
