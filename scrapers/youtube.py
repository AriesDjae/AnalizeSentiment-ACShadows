from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.common.exceptions import NoSuchElementException, WebDriverException
import pandas as pd
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
import re

# Profil Firefox yang sudah login YouTube. Set lewat env var FIREFOX_PROFILE_PATH.
PROFILE_PATH = os.getenv("FIREFOX_PROFILE_PATH", "")
OUTPUT_FILE = Path(__file__).resolve().parents[1] / "data" / "raw" / "youtube_comments_full.csv"

# Satuan waktu relatif YouTube (UI bahasa Inggris & Indonesia) -> timedelta per 1 satuan
TIME_UNITS = [
    (("second", "detik", "just now", "baru saja"), timedelta(seconds=1)),
    (("minute", "menit"), timedelta(minutes=1)),
    (("hour", "jam"), timedelta(hours=1)),
    (("day", "hari"), timedelta(days=1)),
    (("week", "minggu"), timedelta(weeks=1)),
    (("month", "bulan"), timedelta(days=30)),
    (("year", "tahun"), timedelta(days=365)),
]


# Convert “3 days ago” / “3 hari yang lalu” → perkiraan tanggal (relatif terhadap waktu scraping)
def convert_timestamp(text, now=None):
    text = text.lower()
    now = now or datetime.now()

    num = re.findall(r"\d+", text)
    num = int(num[0]) if num else 1

    for keywords, unit in TIME_UNITS:
        if any(k in text for k in keywords):
            return (now - unit * num).strftime("%Y-%m-%d")

    return ""


# Convert "977", "1.2K", "1,2 rb", "3 jt" → int
def parse_like_count(text):
    text = text.strip().lower().replace(" ", "")
    if not text:
        return 0

    multiplier = 1
    for suffix, mult in (("rb", 1_000), ("k", 1_000), ("jt", 1_000_000), ("m", 1_000_000)):
        if text.endswith(suffix):
            multiplier = mult
            text = text[: -len(suffix)]
            break

    try:
        return int(float(text.replace(",", ".")) * multiplier)
    except ValueError:
        return 0


def scrape_youtube_comments(url, max_scroll=2000):
    options = Options()
    options.headless = False
    if PROFILE_PATH:
        options.add_argument("-profile")
        options.add_argument(PROFILE_PATH)

    print("[INFO] Opening Firefox with user profile...")
    driver = webdriver.Firefox(options=options)
    driver.get(url)
    time.sleep(6)

    driver.execute_script("window.scrollTo(0, 1200);")
    time.sleep(3)

    print("[INFO] Scrolling comments...")
    last_len = 0
    stagnant = 0

    for i in range(max_scroll):
        driver.execute_script("""
            let sec = document.querySelector('ytd-item-section-renderer#sections');
            if (sec) sec.scrollBy(0, 4000);
        """)
        time.sleep(2)

        comments = driver.find_elements(By.CSS_SELECTOR, "ytd-comment-thread-renderer")
        print(f"[INFO] Scroll {i+1} | Comments loaded: {len(comments)}")

        if len(comments) == last_len:
            stagnant += 1
        else:
            stagnant = 0

        if stagnant >= 30:  # stop after 30 scrolls with no growth
            print("[INFO] No more comments appear.")
            break

        last_len = len(comments)

    print("[INFO] Extracting data...")

    scraped_at = datetime.now()
    all_data = []

    for thread in comments:
        # main comment
        try:
            user = thread.find_element(By.CSS_SELECTOR, "#header-author yt-formatted-string").text
        except NoSuchElementException:
            user = ""

        try:
            timestamp_raw = thread.find_element(By.CSS_SELECTOR, "#published-time-text a").text
            timestamp_real = convert_timestamp(timestamp_raw, now=scraped_at)
        except NoSuchElementException:
            timestamp_raw = ""
            timestamp_real = ""

        try:
            text = thread.find_element(By.CSS_SELECTOR, "#content #content-text").text
        except NoSuchElementException:
            text = ""

        # like count
        try:
            like_txt = thread.find_element(By.CSS_SELECTOR, "#vote-count-middle").text
            like_count = parse_like_count(like_txt)
        except NoSuchElementException:
            like_count = 0

        # replies
        replies_text = []
        reply_count = 0

        # click "View replies"
        try:
            more_replies = thread.find_element(By.CSS_SELECTOR, "#more-replies")
            driver.execute_script("arguments[0].scrollIntoView(true);", more_replies)
            time.sleep(1)
            more_replies.click()
            time.sleep(2)
        except (NoSuchElementException, WebDriverException):
            pass

        # collect replies
        try:
            replies = thread.find_elements(By.CSS_SELECTOR, "ytd-comment-replies-renderer #content-text")
            reply_count = len(replies)
            replies_text = [r.text for r in replies]
        except NoSuchElementException:
            pass

        all_data.append({
            "user": user,
            "timestamp_raw": timestamp_raw,
            "timestamp_date": timestamp_real,
            "scraped_at": scraped_at.strftime("%Y-%m-%d"),
            "comment": text,
            "like_count": like_count,
            "reply_count": reply_count,
            "reply_text": replies_text
        })

    driver.quit()
    return all_data


if __name__ == "__main__":
    url = "https://www.youtube.com/watch?v=Uc_TaeF9Yks"

    data = scrape_youtube_comments(url)

    df = pd.DataFrame(data)
    OUTPUT_FILE.parent.mkdir(exist_ok=True)
    df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8")

    print(f"[INFO] Saved {len(df)} comments to {OUTPUT_FILE}")
