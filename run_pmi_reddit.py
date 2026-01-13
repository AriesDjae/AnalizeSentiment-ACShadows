#!/usr/bin/env python3
"""
PMI Sentiment Analysis for Reddit Data
Using native PySpark (no SparkNLP dependency)
"""

import os
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, length, lower, regexp_replace, explode, split,
    log2, lit, trim
)
from pyspark.ml.feature import StopWordsRemover
import matplotlib.pyplot as plt

# ============================================================
# SETUP SPARK (Mac-compatible)
# ============================================================
print("Starting PySpark...")
spark = (SparkSession.builder
         .appName("PMI_Reddit")
         .config("spark.driver.memory", "4G")
         .getOrCreate())
spark.sparkContext.setLogLevel("WARN")
print("Spark started successfully!")

# ============================================================
# LOAD DATA
# ============================================================
print("\nLoading Reddit data...")
df = (spark.read
      .option("header", "true")
      .option("multiLine", "true")
      .option("quote", '"')
      .option("escape", '"')
      .option("inferSchema", "true")
      .csv("data/reddit_posts.csv"))

print(f"Total rows: {df.count()}")

# ============================================================
# CLEAN DATA
# ============================================================
print("\nCleaning data...")
df_clean = (df
    .filter(col("comment").isNotNull())
    .filter(length(col("comment")) > 20)
)
print(f"Rows after cleaning: {df_clean.count()}")

# Lowercase and remove special characters  
df_text = df_clean.withColumn(
    "text",
    lower(
        regexp_replace(col("comment"), "[^a-zA-Z\\s]", " ")
    )
)

# Tokenize using split
df_text = df_text.withColumn(
    "tokens",
    split(trim(col("text")), "\\s+")
)

# ============================================================
# REMOVE STOPWORDS (using PySpark native)
# ============================================================
print("\nRemoving stopwords...")
stopwords_remover = StopWordsRemover(inputCol="tokens", outputCol="clean_tokens")
result = stopwords_remover.transform(df_text)

# ============================================================
# WORD FREQUENCY
# ============================================================
print("\nCalculating word frequency...")
custom_noise_words = [
    "im", "ive", "dont", "didnt", "thats", "theres", "cant", "doesnt",
    "also", "really", "much", "many", "one", "even", "still", "lot",
    "way", "got", "get", "going", "go", "say", "see", "know", "think",
    "", "would", "could", "just", "like", "game", "games", "play",
    "played", "playing", "its", "thats", "youre", "theyre", "weve"
]

clean_words_df = (
    result
    .select(explode(col("clean_tokens")).alias("word"))
    .filter(~col("word").isin(custom_noise_words))
    .filter(length(col("word")) > 2)
    .filter(~col("word").rlike("http"))
    .filter(~col("word").rlike("www"))
    .filter(~col("word").rlike("https"))
)

word_freq_clean = (
    clean_words_df
    .groupBy("word")
    .count()
    .orderBy(col("count").desc())
)

print("\nTop 30 words:")
word_freq_clean.show(30, truncate=False)

# ============================================================
# PMI SENTIMENT ANALYSIS
# ============================================================
print("\nCalculating PMI...")
positive_words = [
    "good", "great", "love", "amazing", "fun", "best",
    "better", "awesome", "excellent", "beautiful", "perfect",
    "incredible", "fantastic", "wonderful", "enjoy", "enjoyed"
]

negative_words = [
    "bad", "terrible", "awful", "worst", "boring",
    "hate", "issue", "problem", "disappointing", "broken",
    "bug", "bugs", "glitch", "crash", "frustrating", "repetitive"
]

total_tokens = clean_words_df.count()
print(f"Total tokens: {total_tokens}")

word_counts = (
    clean_words_df
    .groupBy("word")
    .count()
    .withColumnRenamed("count", "context_count")
)

pos_counts = (
    clean_words_df
    .filter(col("word").isin(positive_words))
    .groupBy("word")
    .count()
    .withColumnRenamed("count", "pos_count")
)

neg_counts = (
    clean_words_df
    .filter(col("word").isin(negative_words))
    .groupBy("word")
    .count()
    .withColumnRenamed("count", "neg_count")
)

total_pos = pos_counts.agg({"pos_count": "sum"}).collect()[0][0] or 1
total_neg = neg_counts.agg({"neg_count": "sum"}).collect()[0][0] or 1
print(f"Total positive tokens: {total_pos}, Total negative tokens: {total_neg}")

# Calculate PMI with smoothing
alpha = 1  # smoothing factor

pmi_df = (
    word_counts
    .join(pos_counts, "word", "left")
    .join(neg_counts, "word", "left")
    .na.fill(0)
    .withColumn("pos_count_s", col("pos_count") + alpha)
    .withColumn("neg_count_s", col("neg_count") + alpha)
    .withColumn("p_w", col("context_count") / lit(total_tokens))
    .withColumn("p_pos", lit(total_pos) / lit(total_tokens))
    .withColumn("p_neg", lit(total_neg) / lit(total_tokens))
    .withColumn("p_w_pos_s", col("pos_count_s") / lit(total_tokens))
    .withColumn("p_w_neg_s", col("neg_count_s") / lit(total_tokens))
    .withColumn(
        "pmi_positive",
        log2(col("p_w_pos_s") / (col("p_w") * col("p_pos")))
    )
    .withColumn(
        "pmi_negative",
        log2(col("p_w_neg_s") / (col("p_w") * col("p_neg")))
    )
    .withColumn(
        "sentiment_score",
        col("pmi_positive") - col("pmi_negative")
    )
)

# ============================================================
# GET TOP POSITIVE & NEGATIVE WORDS
# ============================================================
print("\nFiltering results...")
pmi_filtered = pmi_df.filter(col("context_count") >= 5)

# Filter ambiguous words
ambiguous_words = [
    "never", "since", "think", "going", "way", "say", "something", "put",
    "actually", "still", "see", "odyssey", "shadows", "assassin", "creed",
    "understand", "buy", "japanese", "thing", "video", "channel",
    "missions", "much", "want", "know", "people", "ubisoft", "naoe", "yasuke",
    "time", "first", "new", "world", "feel", "combat", "stealth", "series",
    "make", "well", "main", "hours", "feels", "back", "japan", "story",
    "character", "characters", "graphics", "gameplay"
]
pmi_filtered = pmi_filtered.filter(~col("word").isin(ambiguous_words))

print("\n=== Top 10 Positive Sentiment Words ===")
top_pos = (pmi_filtered
    .orderBy(col("sentiment_score").desc())
    .select("word", "context_count", "sentiment_score")
    .limit(10)
    .toPandas())
print(top_pos)

print("\n=== Top 10 Negative Sentiment Words ===")
top_neg = (pmi_filtered
    .orderBy(col("sentiment_score").asc())
    .select("word", "context_count", "sentiment_score")
    .limit(10)
    .toPandas())
print(top_neg)

# ============================================================
# SAVE TO CSV
# ============================================================
print("\nSaving results to CSV...")
os.makedirs("results/pmi", exist_ok=True)
top_pos.to_csv("results/pmi/reddit_pmi_positive.csv", index=False)
top_neg.to_csv("results/pmi/reddit_pmi_negative.csv", index=False)
word_freq_clean.limit(100).toPandas().to_csv("results/pmi/reddit_word_freq.csv", index=False)

# ============================================================
# CREATE VISUALIZATION
# ============================================================
print("\nCreating visualizations...")

fig, axes = plt.subplots(1, 2, figsize=(14, 6))

# Positive sentiment
axes[0].barh(top_pos["word"], top_pos["sentiment_score"], color='#27AE60')
axes[0].set_xlabel("PMI Sentiment Score")
axes[0].set_title("Top 10 Positive Sentiment Words (Reddit)", fontweight='bold')
axes[0].invert_yaxis()
axes[0].axvline(x=0, color='gray', linestyle='--', alpha=0.5)

# Negative sentiment
colors_neg = ['#E74C3C' if x < 0 else '#95A5A6' for x in top_neg["sentiment_score"]]
axes[1].barh(top_neg["word"], top_neg["sentiment_score"], color=colors_neg)
axes[1].set_xlabel("PMI Sentiment Score")
axes[1].set_title("Top 10 Negative Sentiment Words (Reddit)", fontweight='bold')
axes[1].invert_yaxis()
axes[1].axvline(x=0, color='gray', linestyle='--', alpha=0.5)

plt.tight_layout()
plt.savefig("results/pmi/reddit_pmi_chart.png", dpi=150, bbox_inches='tight')
print("Saved: results/pmi/reddit_pmi_chart.png")

print("\n" + "="*50)
print("✅ Reddit PMI analysis complete!")
print("="*50)
print("\nOutput files:")
print("  - results/pmi/reddit_pmi_positive.csv")
print("  - results/pmi/reddit_pmi_negative.csv")
print("  - results/pmi/reddit_word_freq.csv")
print("  - results/pmi/reddit_pmi_chart.png")

spark.stop()
