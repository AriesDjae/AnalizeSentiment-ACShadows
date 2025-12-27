import random
import time
import os
import re
import json
from dotenv import load_dotenv
import pandas as pd
from instagrapi import Client
from tenacity import retry, stop_after_attempt, wait_random
from instagrapi.extractors import extract_media_v1 as original_extract_media_v1

load_dotenv()

cl = Client()

USERNAME = os.getenv("INSTAGRAM_USERNAME")
PASSWORD = os.getenv("INSTAGRAM_PASSWORD")

SESSION_FILE = "session.json"


# =====================================================
# PATCH INSTAGRAPI UNTUK FIX ValidationError BARU IG
# =====================================================
def safe_extract_media_v1(data):
    try:
        # IG kadang kirim "audio_filter_infos": null → harus list
        if "clips_metadata" in data and data["clips_metadata"]:
            c = data["clips_metadata"]
            if "original_sound_info" in c and c["original_sound_info"] is not None:
                osi = c["original_sound_info"]
                if osi.get("audio_filter_infos") is None:
                    osi["audio_filter_infos"] = []  # FIX utama
        return original_extract_media_v1(data)

    except Exception as e:
        print("⚠ Extract error bypassed:", e)
        # fallback: hapus clipping metadata
        return original_extract_media_v1({**data, "clips_metadata": None})


import instagrapi.extractors
instagrapi.extractors.extract_media_v1 = safe_extract_media_v1

# =====================================================
# GLOBAL PATCH SEMUA EXTRACTOR MEDIA
# =====================================================
import instagrapi.extractors

def patch_media_dict(data):
    """
    Membersihkan clips_metadata agar selalu valid & aman dari ValidationError.
    """
    try:
        if data is None:
            return data

        cm = data.get("clips_metadata")
        if cm and isinstance(cm, dict):
            osi = cm.get("original_sound_info")

            # audio_filter_infos HARUS list (IG sering kirim null)
            if isinstance(osi, dict):
                if osi.get("audio_filter_infos") is None:
                    osi["audio_filter_infos"] = []

            # hapus field bermasalah lainnya jika ada
            if "audio_filter_bounding_boxes" in osi and osi["audio_filter_bounding_boxes"] is None:
                osi["audio_filter_bounding_boxes"] = []

        return data

    except:
        return data


# PATCH semua extractor terkait
original_extract_media_v1 = instagrapi.extractors.extract_media_v1
def safe_extract_media_v1(data):
    return original_extract_media_v1(patch_media_dict(data))

original_extract_media_v1_item = instagrapi.extractors.extract_media_v1_xma
def safe_extract_media_v1_item(data):
    return original_extract_media_v1_item(patch_media_dict(data))

# original_extract_media_v2 = instagrapi.extractors.extract_media_v2
# def safe_extract_media_v2(data):
#     return original_extract_media_v2(patch_media_dict(data))

# original_extract_media_v0 = instagrapi.extractors.extract_media_v0
# def safe_extract_media_v0(data):
#     return original_extract_media_v0(patch_media_dict(data))

# Replace extractor globally
instagrapi.extractors.extract_media_v1 = safe_extract_media_v1
instagrapi.extractors.extract_media_v1_item = safe_extract_media_v1_item
# instagrapi.extractors.extract_media_v2 = safe_extract_media_v2
# instagrapi.extractors.extract_media_v0 = safe_extract_media_v0

print("✅ Extractor patched: semua clips_metadata sudah aman")



# =====================================================
# LOAD SESSION
# =====================================================
def load_session():
    if not os.path.exists(SESSION_FILE):
        return False

    try:
        print("🔐 Load session.json ...")
        cl.load_settings(SESSION_FILE)
        cl.login(USERNAME, PASSWORD, relogin=False)
        print("✅ Login via session berhasil")
        return True

    except Exception as e:
        print("⚠️ Session rusak:", e)
        return False


def save_session():
    print("💾 Menyimpan session.json ...")
    cl.dump_settings(SESSION_FILE)


# =====================================================
# LOGIN INSTAGRAM ANTI ERROR
# =====================================================
@retry(stop=stop_after_attempt(5), wait=wait_random(min=3, max=7))
def login():
    print("🔄 Login dengan username + password ...")

    cl.set_device()         # wajib untuk generate UUID
    cl.set_locale("en_US")
    cl.set_country("ID")

    cl.login(USERNAME, PASSWORD)

    save_session()


# =====================================================
# START LOGIN
# =====================================================
if not load_session():
    login()


# =====================================================
# FUNGSI UTIL
# =====================================================
def clean_shortcode(url_or_code):
    # Extract shortcode dari URL IG
    match = re.search(r"/(p|reel|tv)/([A-Za-z0-9_-]+)", url_or_code)
    if match:
        return match.group(2)

    # Jika shortcode langsung
    code = url_or_code.strip()
    code = re.sub(r"[^A-Za-z0-9_-]", "", code)
    return code


def get_media_id(input_value):
    code = clean_shortcode(input_value)

    # Instagram hanya perlu 11 char pertama untuk decode PK
    if len(code) >= 11:
        code = code[:11]

    return cl.media_pk_from_code(code)


# =====================================================
# SCRAPE KOMENTAR & REPLY + RETRY
# =====================================================
@retry(stop=stop_after_attempt(5), wait=wait_random(min=2, max=5))
def get_comments(media_id):
    return cl.media_comments(media_id, amount=0)


@retry(stop=stop_after_attempt(5), wait=wait_random(min=2, max=5))
def get_replies(media_id, cid):
    return cl.comment_replies(media_id, cid)


def scrape_comments(shortcode):

    media_id = get_media_id(shortcode)
    comments = get_comments(media_id)

    data = []

    print(f"Total komentar ditemukan: {len(comments)}")

    for c in comments:
        time.sleep(random.uniform(1.5, 4.0))

        data.append({
            "type": "comment",
            "parent_id": None,
            "comment_id": c.pk,
            "username": c.user.username,
            "text": c.text,
            "timestamp": c.created_at_utc.isoformat(),
            "like_count": c.like_count,
        })

        # SCRAPE REPLY
        if c.child_comment_count > 0:
            replies = get_replies(media_id, c.pk)
            for r in replies:
                time.sleep(random.uniform(1.0, 2.5))

                data.append({
                    "type": "reply",
                    "parent_id": c.pk,
                    "comment_id": r.pk,
                    "username": r.user.username,
                    "text": r.text,
                    "timestamp": r.created_at_utc.isoformat(),
                    "like_count": r.like_count,
                })

    return data


def save_to_csv(data, filename="comments_output.csv"):
    df = pd.DataFrame(data)
    df.to_csv(filename, index=False, encoding="utf-8-sig")
    print(f"📁 File tersimpan: {filename}")


# =====================================================
# MAIN
# =====================================================
if __name__ == "__main__":
    shortcode = "https://www.instagram.com/p/C-5ByQHsUa_/?utm_source=ig_web"
    hasil = scrape_comments(shortcode)
    save_to_csv(hasil)
    print("🎉 Selesai scraping!")
