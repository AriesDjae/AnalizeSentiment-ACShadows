"""Pipeline analisis sentimen end-to-end (PySpark).

    python -m acs_sentiment.pipeline

Langkah:
  1. Baca data mentah semua platform (data/raw/) ke satu DataFrame dokumen.
  2. Cleaning + tokenisasi, buang dokumen non-Inggris.
  3. Label sentimen tiap dokumen dengan lexicon yang sama untuk semua platform
     (seed word + penanganan negasi).
  4. Hitung kemunculan kata di konteks positif/negatif, lalu PMI per platform.
  5. Validasi lexicon terhadap label asli Steam (Recommended / Not Recommended)
     dan, bila tersedia, terhadap sampel berlabel manual.
  6. Tulis hasil ke output/.
"""
import json
import logging
import os
import sys

import pandas as pd
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql import types as T

from . import config, text
from .evaluation import classification_report
from .pmi import compute_pmi

log = logging.getLogger("acs_sentiment")

ANALYSIS_SCHEMA = T.StructType([
    T.StructField("tokens", T.ArrayType(T.StringType())),
    T.StructField("content_tokens", T.ArrayType(T.StringType())),
    T.StructField("lexicon_score", T.IntegerType()),
    T.StructField("is_english", T.BooleanType()),
])


@F.udf(ANALYSIS_SCHEMA)
def analyze_udf(raw_text):
    tokens = text.tokenize(raw_text)
    return (
        tokens,
        text.content_tokens(tokens),
        text.lexicon_score(tokens),
        text.looks_english(raw_text),
    )


def get_spark(app_name="acs-sentiment"):
    # Worker Python harus sama dengan driver (penting di Windows / virtualenv)
    os.environ.setdefault("PYSPARK_PYTHON", sys.executable)
    os.environ.setdefault("PYSPARK_DRIVER_PYTHON", sys.executable)
    # Worker Python harus bisa meng-import paket ini (UDF memanggil acs_sentiment.text),
    # termasuk saat dijalankan dari notebook tanpa `pip install -e .`
    src_dir = str(config.PROJECT_ROOT / "src")
    paths = os.environ.get("PYTHONPATH", "").split(os.pathsep)
    if src_dir not in paths:
        os.environ["PYTHONPATH"] = os.pathsep.join([src_dir, *filter(None, paths)])
    spark = (
        SparkSession.builder
        .appName(app_name)
        .master("local[*]")
        .config("spark.driver.memory", "4g")
        .config("spark.sql.shuffle.partitions", "8")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.sql.legacy.timeParserPolicy", "CORRECTED")
        .config("spark.ui.showConsoleProgress", "false")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("ERROR")
    return spark


def _read_source(spark, source):
    path = config.RAW_DIR / source.file
    raw = (
        spark.read
        .option("header", True)
        .option("multiLine", True)   # komentar bisa berisi baris baru
        .option("quote", '"')
        .option("escape", '"')
        .option("encoding", "UTF-8")
        .csv(str(path))
        .coalesce(1)                 # urutan baris stabil -> doc_id stabil
    )
    gold = (
        F.col(source.gold_col) if source.gold_col else F.lit(None).cast("string")
    )
    return raw.select(
        F.format_string(f"{source.name}-%05d", F.monotonically_increasing_id()).alias("doc_id"),
        F.lit(source.name).alias("source"),
        F.col(source.text_col).alias("text"),
        F.to_date(F.col(source.date_col), source.date_format).alias("date"),
        gold.alias("gold_raw"),
    )


def load_documents(spark):
    """Satu baris per komentar/ulasan dari semua platform, sudah dilabeli."""
    frames = [_read_source(spark, s) for s in config.SOURCES]
    docs = frames[0]
    for frame in frames[1:]:
        docs = docs.unionByName(frame)

    gold_map = F.create_map(*[F.lit(x) for kv in config.STEAM_GOLD_MAP.items() for x in kv])
    docs = (
        docs
        .filter(F.col("text").isNotNull() & (F.length(F.trim("text")) > 0))
        .withColumn("analysis", analyze_udf("text"))
        .select(
            "doc_id", "source", "text", "date",
            gold_map[F.col("gold_raw")].alias("gold_label"),
            F.col("analysis.content_tokens").alias("content_tokens"),
            F.size("analysis.tokens").alias("n_tokens"),
            F.col("analysis.lexicon_score").alias("lexicon_score"),
            F.col("analysis.is_english").alias("is_english"),
        )
        .filter(F.col("n_tokens") > 0)
        .withColumn(
            "label",
            F.when(F.col("lexicon_score") > 0, "positive")
            .when(F.col("lexicon_score") < 0, "negative")
            .otherwise("neutral"),
        )
    )
    return docs.cache()


def word_counts(docs: DataFrame) -> pd.DataFrame:
    """Jumlah kemunculan tiap kata di dokumen positif & negatif, per platform."""
    return (
        docs
        .filter(F.col("label").isin("positive", "negative"))
        .select("source", "label", F.explode("content_tokens").alias("word"))
        .groupBy("source", "word")
        .agg(
            F.sum(F.when(F.col("label") == "positive", 1).otherwise(0)).alias("pos_count"),
            F.sum(F.when(F.col("label") == "negative", 1).otherwise(0)).alias("neg_count"),
        )
        .toPandas()
    )


def word_sentiment(counts: pd.DataFrame) -> pd.DataFrame:
    frames = []
    for source, group in counts.groupby("source"):
        frames.append(compute_pmi(group).assign(source=source))
    return pd.concat(frames, ignore_index=True)


def summarize(docs_pd: pd.DataFrame, dropped: pd.Series) -> pd.DataFrame:
    rows = []
    for source in config.SOURCES:
        d = docs_pd[docs_pd["source"] == source.name]
        counts = d["label"].value_counts()
        pos, neg, neu = (int(counts.get(k, 0)) for k in ("positive", "negative", "neutral"))
        gold = d["gold_label"].dropna()
        dates = pd.to_datetime(d["date"]).dropna()
        rows.append({
            "source": source.name,
            "platform": source.label,
            "documents": len(d),
            "dropped_non_english": int(dropped.get(source.name, 0)),
            "positive": pos,
            "negative": neg,
            "neutral": neu,
            "positive_share": round(pos / (pos + neg), 4) if pos + neg else None,
            "gold_positive_share": round((gold == "positive").mean(), 4) if len(gold) else None,
            "date_min": dates.min().date().isoformat() if len(dates) else None,
            "date_max": dates.max().date().isoformat() if len(dates) else None,
        })
    return pd.DataFrame(rows)


def evaluate(docs_pd: pd.DataFrame) -> dict:
    result = {"lexicon_size": {"positive": len(config.POSITIVE_SEEDS), "negative": len(config.NEGATIVE_SEEDS)}}

    steam = docs_pd[docs_pd["gold_label"].notna()]
    result["steam_recommendation"] = {
        "description": "Label lexicon vs label asli Steam (Recommended / Not Recommended).",
        **classification_report(steam["gold_label"], steam["label"]),
    }

    if config.ANNOTATION_SAMPLE_FILE.exists():
        manual = pd.read_csv(config.ANNOTATION_SAMPLE_FILE)
        manual = manual[manual["gold_label"].isin(["positive", "negative", "neutral"])]
        if len(manual):
            merged = manual.merge(docs_pd[["doc_id", "label"]], on="doc_id")
            result["manual_annotation"] = {
                "description": "Label lexicon vs label manual (Reddit & YouTube).",
                **classification_report(merged["gold_label"], merged["label"]),
            }
    return result


def write_annotation_sample(docs_pd: pd.DataFrame, per_source=100):
    """Sampel acak Reddit & YouTube untuk dilabeli manual. Tidak menimpa file yang sudah ada."""
    if config.ANNOTATION_SAMPLE_FILE.exists():
        return
    sample = pd.concat([
        g.sample(min(per_source, len(g)), random_state=config.RANDOM_SEED)
        for _, g in docs_pd[docs_pd["source"].isin(["reddit", "youtube"])].groupby("source")
    ])
    sample = sample[["doc_id", "source", "text"]].assign(gold_label="")
    config.ANNOTATION_DIR.mkdir(parents=True, exist_ok=True)
    sample.to_csv(config.ANNOTATION_SAMPLE_FILE, index=False)
    log.info("Sampel anotasi ditulis ke %s", config.ANNOTATION_SAMPLE_FILE)


def run(spark=None):
    spark = spark or get_spark()
    config.OUTPUT_DIR.mkdir(exist_ok=True)

    all_docs = load_documents(spark)
    dropped = (
        all_docs.filter(~F.col("is_english")).groupBy("source").count()
        .toPandas().set_index("source")["count"]
    )
    docs = all_docs.filter(F.col("is_english"))

    log.info("Menghitung PMI ...")
    words = word_sentiment(word_counts(docs))

    docs_pd = docs.select(
        "doc_id", "source", "date", "label", "lexicon_score", "gold_label", "n_tokens", "text"
    ).toPandas()
    summary = summarize(docs_pd, dropped)
    evaluation = evaluate(docs_pd)
    write_annotation_sample(docs_pd)

    docs_pd.to_csv(config.DOCUMENTS_FILE, index=False)
    words.to_csv(config.WORD_SENTIMENT_FILE, index=False, float_format="%.4f")
    summary.to_csv(config.SUMMARY_FILE, index=False)
    config.EVALUATION_FILE.write_text(json.dumps(evaluation, indent=2), encoding="utf-8")

    log.info("\n%s", summary.to_string(index=False))
    steam_eval = evaluation["steam_recommendation"]
    log.info(
        "Validasi lexicon vs Steam: accuracy=%.3f macro-F1=%.3f coverage=%.3f",
        steam_eval["accuracy"], steam_eval["macro_f1"], steam_eval["coverage"],
    )
    return summary, words, evaluation


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    spark = get_spark()
    try:
        run(spark)
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
