"""Perhitungan PMI dari tabel jumlah kata (pandas).

Untuk setiap kata w:
    PMI(w, pos) = log2( P(w, pos) / (P(w) * P(pos)) )
    PMI(w, neg) = log2( P(w, neg) / (P(w) * P(neg)) )
    sentiment_score = PMI(w, pos) - PMI(w, neg)

P(w, pos) dihitung dari kemunculan w di dokumen berlabel positif dengan Laplace smoothing.
Karena P(w) saling menghapus, sentiment_score = log2((pos+a)/(neg+a)) - log2(N_pos/N_neg):
skor > 0 berarti kata lebih sering muncul di konteks positif daripada yang diharapkan.
"""
import numpy as np
import pandas as pd

from . import config


def compute_pmi(counts, alpha=config.SMOOTHING_ALPHA):
    """counts: DataFrame dengan kolom word, pos_count, neg_count (satu baris per kata).

    Mengembalikan salinan dengan kolom context_count, pmi_positive, pmi_negative,
    sentiment_score, dan is_seed, diurutkan dari skor tertinggi.
    """
    df = counts[["word", "pos_count", "neg_count"]].copy()
    df[["pos_count", "neg_count"]] = df[["pos_count", "neg_count"]].astype("int64")
    df = df[(df["pos_count"] + df["neg_count"]) > 0]

    n_pos = df["pos_count"].sum()
    n_neg = df["neg_count"].sum()
    if n_pos == 0 or n_neg == 0:
        raise ValueError("PMI butuh token di konteks positif dan negatif")

    vocab = len(df)
    total = n_pos + n_neg + 2 * alpha * vocab   # total setelah smoothing

    df["context_count"] = df["pos_count"] + df["neg_count"]
    p_w = (df["context_count"] + 2 * alpha) / total
    p_w_pos = (df["pos_count"] + alpha) / total
    p_w_neg = (df["neg_count"] + alpha) / total
    p_pos = n_pos / (n_pos + n_neg)
    p_neg = n_neg / (n_pos + n_neg)

    df["pmi_positive"] = np.log2(p_w_pos / (p_w * p_pos))
    df["pmi_negative"] = np.log2(p_w_neg / (p_w * p_neg))
    df["sentiment_score"] = df["pmi_positive"] - df["pmi_negative"]
    df["is_seed"] = df["word"].isin(config.SEED_WORDS)

    return df.sort_values("sentiment_score", ascending=False).reset_index(drop=True)


def top_topics(pmi_df, n=10, min_count=config.MIN_WORD_COUNT, polarity="positive"):
    """Kata non-seed dengan skor paling positif / negatif, minimal `min_count` kemunculan."""
    candidates = pmi_df[(~pmi_df["is_seed"]) & (pmi_df["context_count"] >= min_count)]
    if polarity == "positive":
        return candidates.nlargest(n, "sentiment_score")
    return candidates.nsmallest(n, "sentiment_score")


def combine_counts(frames):
    """Jumlahkan count per kata dari beberapa platform (untuk view gabungan)."""
    combined = pd.concat(frames, ignore_index=True)
    return combined.groupby("word", as_index=False)[["pos_count", "neg_count"]].sum()
