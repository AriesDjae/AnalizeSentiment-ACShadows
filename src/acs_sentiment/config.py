"""Konfigurasi bersama: lokasi file, sumber data, lexicon, dan parameter analisis.

Semua notebook, pipeline, dan dashboard membaca nilai dari sini supaya
metode yang dipakai di setiap platform benar-benar sama.
"""
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
ANNOTATION_DIR = PROJECT_ROOT / "data" / "annotation"
OUTPUT_DIR = PROJECT_ROOT / "output"

DOCUMENTS_FILE = OUTPUT_DIR / "documents.csv"
WORD_SENTIMENT_FILE = OUTPUT_DIR / "word_sentiment.csv"
SUMMARY_FILE = OUTPUT_DIR / "summary.csv"
EVALUATION_FILE = OUTPUT_DIR / "evaluation.json"

ANNOTATION_SAMPLE_FILE = ANNOTATION_DIR / "sample_for_labeling.csv"


@dataclass(frozen=True)
class Source:
    name: str            # id internal (dipakai di file output)
    label: str           # nama yang ditampilkan
    file: str            # nama file di data/raw/
    text_col: str
    date_col: str
    date_format: str     # format Spark (to_date); kosong = tanggal tidak tersedia
    gold_col: str = ""   # kolom label asli (hanya Steam)


SOURCES = (
    Source("steam", "Steam", "steam_reviews.csv", "comment", "date", "d MMMM yyyy", gold_col="recommended"),
    Source("reddit", "Reddit", "reddit_posts.csv", "comment", "date", "yyyy-MM-dd"),
    Source("youtube", "YouTube", "youtube_comments_full.csv", "comment", "timestamp_date", "yyyy-MM-dd"),
)
SOURCE_LABELS = {s.name: s.label for s in SOURCES}

# Nilai kolom `recommended` Steam -> label sentimen
STEAM_GOLD_MAP = {"Recommended": "positive", "Not Recommended": "negative"}

# ---------------------------------------------------------------------------
# Lexicon (seed word) — satu daftar untuk SEMUA platform.
# Dipilih untuk konteks ulasan game: kualitas umum, rekomendasi, dan masalah teknis.
# ---------------------------------------------------------------------------
POSITIVE_SEEDS = frozenset({
    "good", "great", "love", "loved", "loving", "amazing", "awesome", "excellent",
    "fantastic", "incredible", "beautiful", "gorgeous", "stunning", "perfect",
    "fun", "enjoy", "enjoyed", "enjoying", "enjoyable", "best", "masterpiece",
    "recommend", "recommended", "solid", "worth", "impressive", "wonderful",
    "brilliant", "addictive", "polished", "nice", "liked",
})

NEGATIVE_SEEDS = frozenset({
    "bad", "terrible", "awful", "worst", "boring", "hate", "hated",
    "disappointing", "disappointed", "disappointment", "broken", "buggy",
    "bug", "bugs", "glitch", "glitches", "crash", "crashes", "crashing",
    "unplayable", "garbage", "trash", "waste", "mediocre", "repetitive",
    "bland", "sucks", "refund", "lazy", "frustrating", "annoying", "overpriced",
})

SEED_WORDS = POSITIVE_SEEDS | NEGATIVE_SEEDS

# Kata negasi: membalik polaritas seed word dalam jendela NEGATION_WINDOW token sebelumnya
# ("not good", "don't recommend", "never boring").
NEGATIONS = frozenset({
    "not", "no", "never", "dont", "doesnt", "didnt", "isnt", "wasnt", "arent",
    "werent", "cant", "cannot", "couldnt", "wont", "wouldnt", "shouldnt",
    "aint", "nothing", "hardly", "barely", "without", "nor",
})
NEGATION_WINDOW = 3

# Kata yang terlalu umum di domain ini sehingga tidak informatif sebagai "topik"
NOISE_WORDS = frozenset({
    "game", "games", "play", "played", "playing", "plays", "also", "really",
    "much", "many", "one", "even", "still", "lot", "way", "got", "get", "gets",
    "going", "say", "see", "know", "think", "would", "could", "just", "thing",
    "things", "something", "make", "made", "makes", "want", "actually", "ive",
    "youre", "theyre", "thats", "theres", "lets", "gonna", "http", "https", "www",
    "com", "amp", "gt", "lt",
    # kata pengisi umum (bukan topik)
    "quite", "though", "well", "far", "enough", "last", "completely", "personally",
    "everyone", "anyone", "someone", "already", "maybe", "probably", "pretty", "almost",
    "around", "back", "since", "ever", "every", "take", "took", "come", "came", "give",
    "need", "feel", "feels", "felt", "look", "looks", "seem", "seems", "said", "says",
    "use", "used", "put", "keep", "time", "times", "year", "years", "people", "point",
    "part", "lol", "imo", "yeah", "etc",
})

MIN_TOKEN_LENGTH = 3

# Filter bahasa (lihat text.looks_english): ulasan Steam "english" masih memuat
# ulasan Mandarin, Thai, Portugis, Turki, dll.
NON_LATIN_MAX_RATIO = 0.3
ENGLISH_CHECK_MIN_TOKENS = 4

# PMI
SMOOTHING_ALPHA = 1.0     # Laplace smoothing
MIN_WORD_COUNT = 10       # kata lebih jarang dari ini skornya tidak stabil

RANDOM_SEED = 42
