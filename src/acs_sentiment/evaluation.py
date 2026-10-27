"""Evaluasi pelabelan lexicon terhadap label acuan (gold label)."""
from collections import Counter

LABELS = ("positive", "negative")


def classification_report(gold, predicted, labels=LABELS):
    """Akurasi, precision/recall/F1 per kelas, macro-F1, dan confusion matrix.

    Pasangan dengan prediksi di luar `labels` (mis. "neutral" = lexicon tidak menemukan
    seed word) tidak dihitung ke metrik, tapi dilaporkan sebagai `coverage`.
    """
    pairs = list(zip(gold, predicted))
    if not pairs:
        raise ValueError("Tidak ada data untuk dievaluasi")
    covered = [(g, p) for g, p in pairs if p in labels and g in labels]

    confusion = {g: {p: 0 for p in labels} for g in labels}
    for g, p in covered:
        confusion[g][p] += 1

    per_class = {}
    for label in labels:
        tp = confusion[label][label]
        fp = sum(confusion[g][label] for g in labels if g != label)
        fn = sum(confusion[label][p] for p in labels if p != label)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[label] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "support": tp + fn,
        }

    correct = sum(g == p for g, p in covered)
    gold_counts = Counter(g for g, _ in covered)
    majority = gold_counts.most_common(1)[0][1] / len(covered) if covered else 0.0

    return {
        "n_total": len(pairs),
        "n_evaluated": len(covered),
        "coverage": round(len(covered) / len(pairs), 4),
        "accuracy": round(correct / len(covered), 4) if covered else 0.0,
        "macro_f1": round(sum(c["f1"] for c in per_class.values()) / len(labels), 4),
        "majority_baseline_accuracy": round(majority, 4),
        "per_class": per_class,
        "confusion_matrix": confusion,
    }
