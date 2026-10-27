"""Dashboard sentimen Assassin's Creed Shadows.

    streamlit run dashboard/app.py

Membaca hasil `python -m acs_sentiment.pipeline` dari folder output/.
"""
import json
import sys
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from acs_sentiment import config  # noqa: E402
from acs_sentiment.pmi import combine_counts, compute_pmi, top_topics  # noqa: E402

# Pasangan divergen: positif (biru) <-> netral (abu) <-> negatif (merah)
COLORS = {"positive": "#2a78d6", "neutral": "#a8a69f", "negative": "#e34948"}
LABEL_ID = {"positive": "Positif", "neutral": "Netral", "negative": "Negatif"}
ALL_PLATFORMS = "Semua platform"
MIN_MONTHLY_DOCS = 20

st.set_page_config(page_title="Sentimen AC Shadows", page_icon="🎮", layout="wide")


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
@st.cache_data
def load_outputs():
    missing = [p.name for p in (config.DOCUMENTS_FILE, config.WORD_SENTIMENT_FILE,
                                config.SUMMARY_FILE, config.EVALUATION_FILE) if not p.exists()]
    if missing:
        return None
    docs = pd.read_csv(config.DOCUMENTS_FILE, parse_dates=["date"])
    words = pd.read_csv(config.WORD_SENTIMENT_FILE)
    summary = pd.read_csv(config.SUMMARY_FILE)
    evaluation = json.loads(config.EVALUATION_FILE.read_text(encoding="utf-8"))
    return docs, words, summary, evaluation


@st.cache_data
def pmi_for(words, sources):
    subset = words[words["source"].isin(sources)]
    if len(sources) == 1:
        return subset
    return compute_pmi(combine_counts([g for _, g in subset.groupby("source")]))


outputs = load_outputs()
if outputs is None:
    st.error("Hasil analisis belum ada. Jalankan dulu: `python -m acs_sentiment.pipeline`")
    st.stop()
docs, words, summary, evaluation = outputs

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
st.sidebar.title("🎮 AC Shadows")
st.sidebar.caption("Analisis sentimen komentar pemain")
platform_options = [ALL_PLATFORMS] + [s.label for s in config.SOURCES]
selected = st.sidebar.radio("Platform", platform_options)
selected_sources = (
    [s.name for s in config.SOURCES] if selected == ALL_PLATFORMS
    else [s.name for s in config.SOURCES if s.label == selected]
)
min_count = st.sidebar.slider(
    "Minimal kemunculan kata (topik)", 5, 50, config.MIN_WORD_COUNT, step=5,
    help="Kata yang lebih jarang dari ini tidak masuk daftar topik karena skornya tidak stabil.",
)
st.sidebar.divider()
st.sidebar.caption(
    "Label sentimen tiap komentar ditentukan dengan lexicon yang sama di semua platform "
    "(seed word + penanganan negasi). Lihat **Metodologi & validasi** di bawah."
)

view_docs = docs[docs["source"].isin(selected_sources)]
view_pmi = pmi_for(words, tuple(selected_sources))

# ---------------------------------------------------------------------------
# Header & KPI
# ---------------------------------------------------------------------------
st.title("Sentimen Pemain Assassin's Creed Shadows")
dated = view_docs["date"].dropna()
period = f"{dated.min():%b %Y} – {dated.max():%b %Y}" if len(dated) else "tanggal tidak tersedia"
st.caption(f"{selected} · {len(view_docs):,} komentar · periode {period}")

counts = view_docs["label"].value_counts()
n_pos, n_neg, n_neu = (int(counts.get(k, 0)) for k in ("positive", "negative", "neutral"))
labeled = n_pos + n_neg

k1, k2, k3, k4 = st.columns(4)
k1.metric("Komentar dianalisis", f"{len(view_docs):,}")
k2.metric("Positif", f"{n_pos / labeled:.0%}" if labeled else "–", help=f"{n_pos:,} komentar positif dari {labeled:,} komentar bersentimen")
k3.metric("Negatif", f"{n_neg / labeled:.0%}" if labeled else "–", help=f"{n_neg:,} komentar negatif dari {labeled:,} komentar bersentimen")
k4.metric("Netral / tanpa kata sentimen", f"{n_neu / len(view_docs):.0%}" if len(view_docs) else "–", help=f"{n_neu:,} komentar")

# ---------------------------------------------------------------------------
# Perbandingan platform & tren
# ---------------------------------------------------------------------------
left, right = st.columns([1, 1.3])

with left:
    st.subheader("Komposisi sentimen per platform")
    comp = (
        docs.groupby(["source", "label"]).size().rename("n").reset_index()
        .assign(
            platform=lambda d: d["source"].map(config.SOURCE_LABELS),
            sentimen=lambda d: d["label"].map(LABEL_ID),
            share=lambda d: d["n"] / d.groupby("source")["n"].transform("sum"),
            order=lambda d: d["label"].map({"positive": 0, "neutral": 1, "negative": 2}),
        )
    )
    bars = (
        alt.Chart(comp)
        .mark_bar()
        .encode(
            y=alt.Y(
                "platform:N", title=None, sort=[s.label for s in config.SOURCES],
                scale=alt.Scale(paddingInner=0.35), axis=alt.Axis(labelOverlap=False),
            ),
            x=alt.X("n:Q", stack="normalize", title=None, axis=alt.Axis(format="%", grid=False)),
            color=alt.Color(
                "sentimen:N", title=None, legend=alt.Legend(orient="top"),
                scale=alt.Scale(domain=list(LABEL_ID.values()), range=list(COLORS.values())),
            ),
            order=alt.Order("order:Q"),
            tooltip=[
                alt.Tooltip("platform:N", title="Platform"),
                alt.Tooltip("sentimen:N", title="Sentimen"),
                alt.Tooltip("n:Q", title="Komentar", format=","),
                alt.Tooltip("share:Q", title="Porsi", format=".1%"),
            ],
        )
        .properties(height=alt.Step(44))
    )
    st.altair_chart(bars, use_container_width=True)
    steam_row = summary.set_index("source").loc["steam"]
    st.caption(
        f"Pembanding: {steam_row['gold_positive_share']:.0%} ulasan Steam memberi *Recommended*. "
        "Netral = komentar tanpa kata sentimen dari lexicon."
    )

with right:
    st.subheader("Tren porsi komentar positif per bulan")
    monthly = (
        view_docs.dropna(subset=["date"])
        .loc[lambda d: d["label"] != "neutral"]
        .assign(month=lambda d: d["date"].dt.to_period("M").dt.to_timestamp())
        .groupby(["source", "month"])
        .agg(n=("label", "size"), positive=("label", lambda s: (s == "positive").mean()))
        .reset_index()
        .loc[lambda d: d["n"] >= MIN_MONTHLY_DOCS]
        .assign(platform=lambda d: d["source"].map(config.SOURCE_LABELS))
    )
    if monthly.empty:
        st.info("Tidak ada data bertanggal yang cukup untuk platform ini (YouTube hanya punya tanggal relatif).")
    else:
        base = alt.Chart(monthly).encode(
            x=alt.X("month:T", title=None, axis=alt.Axis(format="%b %y", grid=False)),
            y=alt.Y("positive:Q", title="Porsi positif", scale=alt.Scale(domain=[0, 1]), axis=alt.Axis(format="%")),
            tooltip=[
                alt.Tooltip("platform:N", title="Platform"),
                alt.Tooltip("month:T", title="Bulan", format="%B %Y"),
                alt.Tooltip("positive:Q", title="Positif", format=".1%"),
                alt.Tooltip("n:Q", title="Komentar bersentimen", format=","),
            ],
        )
        line = base.mark_line(strokeWidth=2, color=COLORS["positive"]) + base.mark_point(
            size=64, filled=True, color=COLORS["positive"]
        )
        trend = line.properties(height=150).facet(
            row=alt.Row("platform:N", title=None, header=alt.Header(labelAngle=0, labelAlign="left"))
        )
        st.altair_chart(trend, use_container_width=True)
        st.caption(f"Hanya bulan dengan minimal {MIN_MONTHLY_DOCS} komentar bersentimen.")

# ---------------------------------------------------------------------------
# Topik (PMI)
# ---------------------------------------------------------------------------
st.divider()
st.subheader("Topik yang paling terkait dengan sentimen")
st.caption(
    "Skor PMI = log₂ P(kata | positif) / P(kata | negatif) setelah dikoreksi proporsi kelas. "
    "Skor > 0 berarti kata lebih sering muncul di komentar positif. Seed word lexicon tidak ditampilkan."
)


def topic_chart(frame, polarity):
    frame = frame.assign(abs_score=frame["sentiment_score"].abs())
    return (
        alt.Chart(frame)
        .mark_bar(cornerRadiusEnd=4, color=COLORS[polarity])
        .encode(
            y=alt.Y(
                "word:N", sort="-x", title=None,
                scale=alt.Scale(paddingInner=0.4), axis=alt.Axis(labelOverlap=False, labelLimit=180),
            ),
            x=alt.X("abs_score:Q", title="|skor PMI|", axis=alt.Axis(grid=False)),
            tooltip=[
                alt.Tooltip("word:N", title="Kata"),
                alt.Tooltip("sentiment_score:Q", title="Skor PMI", format="+.2f"),
                alt.Tooltip("pos_count:Q", title="Di komentar positif", format=","),
                alt.Tooltip("neg_count:Q", title="Di komentar negatif", format=","),
            ],
        )
        .properties(height=alt.Step(28))
    )


c_pos, c_neg = st.columns(2)
with c_pos:
    st.markdown("**Positif**")
    st.altair_chart(topic_chart(top_topics(view_pmi, 12, min_count, "positive"), "positive"), use_container_width=True)
with c_neg:
    st.markdown("**Negatif**")
    st.altair_chart(topic_chart(top_topics(view_pmi, 12, min_count, "negative"), "negative"), use_container_width=True)

# ---------------------------------------------------------------------------
# Cari kata
# ---------------------------------------------------------------------------
st.divider()
st.subheader("Cari kata")
vocab = view_pmi.sort_values("context_count", ascending=False)["word"].tolist()
default_word = "combat" if "combat" in vocab else vocab[0]
word = st.selectbox("Pilih atau ketik kata", vocab, index=vocab.index(default_word))
row = view_pmi.set_index("word").loc[word]

m1, m2, m3, m4 = st.columns(4)
m1.metric("Kemunculan (komentar bersentimen)", f"{int(row['context_count']):,}")
m2.metric("Di komentar positif", f"{int(row['pos_count']):,}")
m3.metric("Di komentar negatif", f"{int(row['neg_count']):,}")
m4.metric("Skor PMI", f"{row['sentiment_score']:+.2f}",
          help="> 0 condong positif, < 0 condong negatif" + (" · seed word lexicon" if row["is_seed"] else ""))

examples = view_docs[
    (view_docs["label"] != "neutral")
    & view_docs["text"].str.contains(rf"\b{word}\b", case=False, regex=True, na=False)
]
if len(examples):
    sample = examples.sample(min(6, len(examples)), random_state=config.RANDOM_SEED)
    st.markdown("**Contoh komentar**")
    for _, ex in sample.iterrows():
        snippet = ex["text"] if len(ex["text"]) <= 320 else ex["text"][:320] + "…"
        icon = "🔵" if ex["label"] == "positive" else "🔴"
        st.markdown(f"{icon} *{config.SOURCE_LABELS[ex['source']]}* — {snippet}")

# ---------------------------------------------------------------------------
# Metodologi & validasi
# ---------------------------------------------------------------------------
st.divider()
with st.expander("Metodologi & validasi", expanded=False):
    steam_eval = evaluation["steam_recommendation"]
    st.markdown(
        f"""
1. **Data**: ulasan Steam, posting & komentar Reddit, dan komentar YouTube (lihat tabel di bawah).
   Komentar panjang yang bukan bahasa Inggris dibuang.
2. **Cleaning**: lowercase, hapus URL/simbol/angka, gabungkan kontraksi (*don't → dont*),
   buang stopword dan kata umum (*game, play, …*).
3. **Label sentimen** (sama untuk semua platform): jumlah seed word positif − negatif
   ({evaluation['lexicon_size']['positive']} positif, {evaluation['lexicon_size']['negative']} negatif);
   polaritas dibalik bila didahului negasi dalam 3 kata (*not good*, *don't recommend*).
   Skor 0 = netral dan tidak dipakai untuk PMI.
4. **Topik**: PMI antara kata dan label sentimen komentar tempat kata itu muncul (Laplace smoothing).
5. **Validasi**: label lexicon dibandingkan dengan label asli Steam (*Recommended / Not Recommended*).
"""
    )
    v1, v2, v3, v4 = st.columns(4)
    v1.metric("Akurasi", f"{steam_eval['accuracy']:.1%}")
    v2.metric("Macro-F1", f"{steam_eval['macro_f1']:.2f}")
    v3.metric("Baseline (selalu kelas mayoritas)", f"{steam_eval['majority_baseline_accuracy']:.1%}")
    v4.metric("Cakupan (tidak netral)", f"{steam_eval['coverage']:.1%}")

    cm = pd.DataFrame(steam_eval["confusion_matrix"]).T
    cm.index = [f"Asli: {LABEL_ID[i]}" for i in cm.index]
    cm.columns = [f"Lexicon: {LABEL_ID[c]}" for c in cm.columns]
    st.markdown("**Confusion matrix (Steam)**")
    st.dataframe(cm, use_container_width=True)

    per_class = pd.DataFrame(steam_eval["per_class"]).T
    per_class.index = [LABEL_ID[i] for i in per_class.index]
    st.dataframe(per_class, use_container_width=True)

    if "manual_annotation" in evaluation:
        manual = evaluation["manual_annotation"]
        st.markdown(
            f"**Validasi manual (Reddit & YouTube)**: akurasi {manual['accuracy']:.1%}, "
            f"macro-F1 {manual['macro_f1']:.2f} dari {manual['n_evaluated']} komentar."
        )
    else:
        st.caption(
            "Validasi manual Reddit/YouTube belum tersedia: isi kolom `gold_label` di "
            "`data/annotation/sample_for_labeling.csv`, lalu jalankan ulang pipeline."
        )

    st.markdown("**Ringkasan data**")
    st.dataframe(
        summary.drop(columns=["source"]).rename(columns={
            "platform": "Platform", "documents": "Komentar", "dropped_non_english": "Dibuang (non-Inggris)",
            "positive": "Positif", "negative": "Negatif", "neutral": "Netral",
            "positive_share": "Porsi positif", "gold_positive_share": "Porsi Recommended (Steam)",
            "date_min": "Dari", "date_max": "Sampai",
        }),
        hide_index=True, use_container_width=True,
    )
    st.caption(
        "Keterbatasan: sarkasme dan konteks kompleks tidak tertangkap lexicon; data YouTube berasal dari "
        "satu video dan hanya punya tanggal relatif; tiap platform punya demografi pengguna berbeda."
    )
