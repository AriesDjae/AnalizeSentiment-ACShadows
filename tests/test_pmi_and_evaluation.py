import math

import pandas as pd
import pytest

from acs_sentiment.evaluation import classification_report
from acs_sentiment.pmi import combine_counts, compute_pmi, top_topics


@pytest.fixture
def counts():
    return pd.DataFrame({
        "word": ["kyoto", "stutter", "combat", "good", "rare"],
        "pos_count": [40, 2, 30, 50, 1],
        "neg_count": [2, 30, 10, 5, 0],
    })


def test_sentiment_score_matches_closed_form(counts):
    df = compute_pmi(counts, alpha=1.0).set_index("word")
    n_pos, n_neg = counts["pos_count"].sum(), counts["neg_count"].sum()
    for word, row in counts.set_index("word").iterrows():
        expected = math.log2((row.pos_count + 1) / (row.neg_count + 1)) - math.log2(n_pos / n_neg)
        assert df.loc[word, "sentiment_score"] == pytest.approx(expected)


def test_scores_have_expected_direction(counts):
    df = compute_pmi(counts).set_index("word")
    assert df.loc["kyoto", "sentiment_score"] > 0
    assert df.loc["stutter", "sentiment_score"] < 0
    # Bug lama: semua kata non-seed mendapat skor sama. Pastikan skor bervariasi.
    assert df["sentiment_score"].nunique() == len(df)


def test_top_topics_excludes_seed_words_and_rare_words(counts):
    df = compute_pmi(counts)
    top = top_topics(df, n=5, min_count=10, polarity="positive")["word"].tolist()
    assert "good" not in top          # seed word
    assert "rare" not in top          # di bawah min_count
    assert top[0] == "kyoto"
    assert top_topics(df, n=1, min_count=10, polarity="negative")["word"].tolist() == ["stutter"]


def test_compute_pmi_requires_both_classes():
    with pytest.raises(ValueError):
        compute_pmi(pd.DataFrame({"word": ["a"], "pos_count": [3], "neg_count": [0]}))


def test_combine_counts_sums_per_word():
    a = pd.DataFrame({"word": ["x", "y"], "pos_count": [1, 2], "neg_count": [0, 1]})
    b = pd.DataFrame({"word": ["x"], "pos_count": [4], "neg_count": [5]})
    combined = combine_counts([a, b]).set_index("word")
    assert combined.loc["x"].tolist() == [5, 5]
    assert combined.loc["y"].tolist() == [2, 1]


def test_classification_report():
    gold = ["positive", "positive", "negative", "negative", "positive"]
    pred = ["positive", "negative", "negative", "neutral", "positive"]
    report = classification_report(gold, pred)
    assert report["n_evaluated"] == 4
    assert report["coverage"] == 0.8
    assert report["accuracy"] == 0.75
    assert report["confusion_matrix"]["positive"]["negative"] == 1
    assert report["per_class"]["negative"]["precision"] == 0.5
    assert report["per_class"]["negative"]["recall"] == 1.0
