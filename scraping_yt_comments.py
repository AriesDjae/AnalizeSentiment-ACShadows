from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
import pandas as pd
import time
from datetime import datetime, timedelta
import re

PROFILE_PATH = r"C:\Users\LENOVO\AppData\Roaming\Mozilla\Firefox\Profiles\9rpyj1xv.default-release-1759910200430"


# Convert “3 days ago” → real date
def convert_timestamp(text):
    text = text.lower()
    now = datetime.now()

    num = re.findall(r"\d+", text)
    num = int(num[0]) if num else 0

    if "second" in text or "just now" in text:
        return now.strftime("%Y-%m-%d")
    if "minute" in text:
        return (now - timedelta(minutes=num)).strftime("%Y-%m-%d")
    if "hour" in text:
        return (now - timedelta(hours=num)).strftime("%Y-%m-%d")
    if "day" in text:
        return (now - timedelta(days=num)).strftime("%Y-%m-%d")
    if "week" in text:
        return (now - timedelta(weeks=num)).strftime("%Y-%m-%d")
    if "month" in text:
        return (now - timedelta(days=num * 30)).strftime("%Y-%m-%d")
    if "year" in text:
        return (now - timedelta(days=num * 365)).strftime("%Y-%m-%d")

    return text


def scrape_youtube_comments(url, max_scroll=2000):
    options = Options()
    options.headless = False
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

    all_data = []

    for thread in comments:
        # main comment
        try:
            user = thread.find_element(By.CSS_SELECTOR, "#header-author yt-formatted-string").text
        except:
            user = ""

        try:
            timestamp_raw = thread.find_element(By.CSS_SELECTOR, "#published-time-text a").text
            timestamp_real = convert_timestamp(timestamp_raw)
        except:
            timestamp_raw = ""
            timestamp_real = ""

        try:
            text = thread.find_element(By.CSS_SELECTOR, "#content #content-text").text
        except:
            text = ""

        # like count
        try:
            like_txt = thread.find_element(By.CSS_SELECTOR, "#vote-count-middle").text.strip()
            like_count = int(like_txt.replace("K", "000").replace(".", "")) if like_txt else 0
        except:
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
        except:
            pass

        # collect replies
        try:
            replies = thread.find_elements(By.CSS_SELECTOR, "ytd-comment-replies-renderer #content-text")
            reply_count = len(replies)
            replies_text = [r.text for r in replies]
        except:
            pass

        all_data.append({
            "user": user,
            "timestamp_raw": timestamp_raw,
            "timestamp_date": timestamp_real,
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
    df.to_csv("youtube_comments_full.csv", index=False, encoding="utf-8")

    print(f"[INFO] Saved {len(df)} comments to youtube_comments_full.csv")
