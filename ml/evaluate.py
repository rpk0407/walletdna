"""Cluster quality evaluation with comprehensive metrics.

Research upgrades:
- Davies-Bouldin Index (lower is better, measures cluster separation)
- Calinski-Harabasz Index (higher is better, ratio of between/within variance)
- Per-archetype cluster purity analysis
"""

from pathlib import Path

import joblib
import numpy as np
from sklearn.metrics import (  # type: ignore[import-untyped]
    calinski_harabasz_score,
    davies_bouldin_score,
    silhouette_score,
)

MODEL_DIR = Path(__file__).parent / "models"


def evaluate(
    feature_matrix: np.ndarray,
    archetype_labels: list[str] | None = None,
) -> dict[str, float]:
    """Evaluate the trained HDBSCAN model with comprehensive metrics.

    Args:
        feature_matrix: (n_wallets, n_features) float array.
        archetype_labels: Optional ground-truth labels for purity analysis.

    Returns:
        Dict of evaluation metrics.
    """
    scaler_path = MODEL_DIR / "scaler.pkl"
    model_path = MODEL_DIR / "hdbscan_model.pkl"

    if not model_path.exists():
        raise FileNotFoundError("Model not trained. Run ml/train.py first.")

    scaler = joblib.load(scaler_path)
    clusterer = joblib.load(model_path)

    # Apply log-transform if config exists
    log_features_path = MODEL_DIR / "log_features.pkl"
    feature_names_path = MODEL_DIR / "feature_names.pkl"
    if log_features_path.exists() and feature_names_path.exists():
        log_features = joblib.load(log_features_path)
        feature_names = joblib.load(feature_names_path)
        matrix = feature_matrix.copy()
        for i, name in enumerate(feature_names):
            if name in log_features and i < matrix.shape[1]:
                matrix[:, i] = np.log1p(np.abs(matrix[:, i])) * np.sign(matrix[:, i])
        scaled = scaler.transform(matrix)
    else:
        scaled = scaler.transform(feature_matrix)

    labels = clusterer.labels_
    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    noise_ratio = (labels == -1).sum() / len(labels)

    # Filter to non-noise points for cluster metrics
    mask = labels != -1
    non_noise_scaled = scaled[mask]
    non_noise_labels = labels[mask]

    metrics: dict[str, float] = {
        "n_clusters": float(n_clusters),
        "noise_ratio": float(noise_ratio),
        "total_wallets": float(len(labels)),
        "non_noise_wallets": float(mask.sum()),
    }

    if mask.sum() > 1 and n_clusters > 1:
        # Silhouette Score: [-1, 1], higher = better defined clusters
        metrics["silhouette_score"] = float(
            silhouette_score(
                non_noise_scaled,
                non_noise_labels,
                sample_size=min(5000, mask.sum()),
                random_state=42,
            )
        )

        # Davies-Bouldin Index: lower = better cluster separation
        metrics["davies_bouldin_index"] = float(
            davies_bouldin_score(non_noise_scaled, non_noise_labels)
        )

        # Calinski-Harabasz Index: higher = denser, well-separated clusters
        metrics["calinski_harabasz_index"] = float(
            calinski_harabasz_score(non_noise_scaled, non_noise_labels)
        )
    else:
        metrics["silhouette_score"] = 0.0
        metrics["davies_bouldin_index"] = float("inf")
        metrics["calinski_harabasz_index"] = 0.0

    # Cluster purity analysis (if ground-truth labels provided)
    if archetype_labels is not None:
        purity = _compute_cluster_purity(labels, archetype_labels)
        metrics["cluster_purity"] = purity

    print("=== Cluster Evaluation ===")
    for k, v in metrics.items():
        print(f"  {k}: {v:.4f}")

    return metrics


def _compute_cluster_purity(
    cluster_labels: np.ndarray, archetype_labels: list[str]
) -> float:
    """Compute cluster purity: fraction of wallets whose cluster's majority
    archetype matches their ground-truth label."""
    from collections import Counter

    unique_clusters = set(cluster_labels)
    unique_clusters.discard(-1)

    if not unique_clusters:
        return 0.0

    correct = 0
    total = 0

    for cluster_id in unique_clusters:
        mask = cluster_labels == cluster_id
        cluster_archetypes = [
            archetype_labels[i] for i in range(len(archetype_labels)) if mask[i]
        ]
        if not cluster_archetypes:
            continue
        majority_archetype = Counter(cluster_archetypes).most_common(1)[0][0]
        correct += sum(1 for a in cluster_archetypes if a == majority_archetype)
        total += len(cluster_archetypes)

    return correct / total if total > 0 else 0.0


if __name__ == "__main__":
    import argparse

    import polars as pl

    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True, help="Path to feature CSV")
    args = parser.parse_args()

    df = pl.read_csv(args.data)
    feature_cols = [c for c in df.columns if c not in ("wallet_address", "archetype")]
    labels = df["archetype"].to_list() if "archetype" in df.columns else None
    evaluate(df.select(feature_cols).to_numpy(), archetype_labels=labels)
