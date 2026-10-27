"""Fungsi teks murni (tanpa Spark): cleaning, tokenisasi, filter bahasa, dan skor lexicon.

Dipakai sebagai UDF di pipeline Spark dan bisa dites langsung dengan pytest.
"""
import re
import unicodedata

from . import config

ENGLISH_STOPWORDS = frozenset("""
a about above after again against all am an and any are as at be because been before
being below between both but by can could did do does doing down during each few for
from further had has have having he her here hers herself him himself his how i if in
into is it its itself just me more most my myself no nor not now of off on once only or
other our ours ourselves out over own same she should so some such than that the their
theirs them themselves then there these they this those through to too under until up
very was we were what when where which while who whom why will with you your yours
yourself yourselves im ive id ill youre youve youll hes shes its were theyre theyve
weve dont doesnt didnt isnt wasnt arent werent cant couldnt wont wouldnt shouldnt
havent hasnt hadnt thats theres whats lets also get got would could
""".split())

# Kata fungsi umum bahasa lain yang muncul di ulasan Steam (DE, FR, ES, PT, IT, TR, ID, NL, PL).
# Kata yang juga lazim di bahasa Inggris (die, con, non, ...) sengaja tidak dimasukkan,
# begitu juga "ve" (Turki) karena regex memecah "I've" menjadi "i" + "ve".
FOREIGN_FUNCTION_WORDS = frozenset("""
und der das ist nicht ich ein eine mit auf auch sehr aber spiel
les des est une pas pour qui dans avec mais tres jeu
el los las una por para pero muy juego es lo del
nao voce uma com mais muito jogo isso
della che gioco molto sono
bir icin cok oyun ile ama
yang dengan tidak ini sangat
het een niet van
jest sie nie gra
""".split())

_WORD_RE = re.compile(r"[^\W\d_]+")
_URL_RE = re.compile(r"https?://\S+|www\.\S+")
_APOSTROPHE_RE = re.compile(r"['’`]")
_NON_LETTER_RE = re.compile(r"[^a-z]+")


def clean_text(text):
    """Lowercase, buang URL, gabungkan kontraksi (don't -> dont), sisakan huruf a-z."""
    if not text:
        return ""
    text = _URL_RE.sub(" ", str(text).lower())
    text = _APOSTROPHE_RE.sub("", text)
    return _NON_LETTER_RE.sub(" ", text).strip()


def tokenize(text):
    """Semua token hasil cleaning (termasuk stopword & negasi) — dipakai untuk pelabelan."""
    cleaned = clean_text(text)
    return cleaned.split() if cleaned else []


def content_tokens(tokens):
    """Token bermakna untuk analisis topik/PMI: tanpa stopword, noise, dan token pendek."""
    return [
        t for t in tokens
        if len(t) >= config.MIN_TOKEN_LENGTH
        and t not in ENGLISH_STOPWORDS
        and t not in config.NOISE_WORDS
    ]


def _strip_accents(word):
    return unicodedata.normalize("NFKD", word).encode("ascii", "ignore").decode()


def looks_english(raw_text):
    """Heuristik bahasa untuk membuang ulasan non-Inggris.

    Non-Inggris jika (a) mayoritas hurufnya bukan huruf Latin dasar (Mandarin, Thai, Rusia, ...)
    atau (b) kata fungsi bahasa lain lebih banyak daripada stopword Inggris.
    Teks pendek atau berupa daftar ("Good gameplay, bad story") tetap dianggap Inggris.
    """
    if not raw_text:
        return True
    letters = [c for c in str(raw_text) if c.isalpha()]
    if letters and sum(not c.isascii() for c in letters) / len(letters) > config.NON_LATIN_MAX_RATIO:
        return False

    words = [_strip_accents(w) for w in _WORD_RE.findall(str(raw_text).lower())]
    if len(words) < config.ENGLISH_CHECK_MIN_TOKENS:
        return True
    foreign = sum(w in FOREIGN_FUNCTION_WORDS for w in words)
    english = sum(w in ENGLISH_STOPWORDS for w in words)
    return not (foreign >= 2 and foreign > english)


def lexicon_score(tokens):
    """Jumlah seed positif - seed negatif, dengan polaritas dibalik bila didahului negasi."""
    score = 0
    for i, token in enumerate(tokens):
        if token in config.POSITIVE_SEEDS:
            polarity = 1
        elif token in config.NEGATIVE_SEEDS:
            polarity = -1
        else:
            continue
        window = tokens[max(0, i - config.NEGATION_WINDOW):i]
        if any(w in config.NEGATIONS for w in window):
            polarity = -polarity
        score += polarity
    return score


def label_from_score(score):
    if score > 0:
        return "positive"
    if score < 0:
        return "negative"
    return "neutral"
