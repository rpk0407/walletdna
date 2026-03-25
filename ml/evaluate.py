"""Cluster quality evaluation: silhouette score, archetype separation."""

from pathlib import Path

import joblib
import numpy as np
from sklearn.metrics import silhouette_score  # type: ignore[import-untyped]

MODEL_DIR = Path(__file__).parent / "models"


def evaluate(feature_matrix: np.ndarray) -> dict[str, float]:
    """Evaluate the trained HDBSCAN model on a feature matrix.

    Args:
        feature_matrix: (n_wallets, n_features) float array.

    Returns:
        Dict of evaluation metrics.
    """
    scaler_path = MODEL_DIR / "scaler.pkl"
    model_path = MODEL_DIR / "hdbscan_model.pkl"

    if not model_path.exists():
        raise FileNotFoundError("Model not trained. Run ml/train.py first.")

    scaler = joblib.load(scaler_path)
    clusterer = joblib.load(model_path)
    scaled = scaler.transform(feature_matrix)

    labels = clusterer.labels_
    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    noise_ratio = (labels == -1).sum() / len(labels)

    # Silhouette score on non-noise points
    mask = labels != -1
    sil_score = 0.0
    if mask.sum() > 1 and n_clusters > 1:
        sil_score = float(silhouette_score(scaled[mask], labels[mask], sample_size=min(5000, mask.sum())))

    metrics = {
        "n_clusters": float(n_clusters),
        "noise_ratio": float(noise_ratio),
        "silhouette_score": sil_score,
        "total_wallets": float(len(labels)),
    }

    print("=== Cluster Evaluation ===")
    for k, v in metrics.items():
        print(f"  {k}: {v:.4f}")

    return metrics


if __name__ == "__main__":
    import argparse
    import polars as pl

    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True, help="Path to feature CSV")
    args = parser.parse_args()

    df = pl.read_csv(args.data)
    feature_cols = [c for c in df.columns if c not in ("wallet_address", "archetype")]
    evaluate(df.select(feature_cols).to_numpy())
