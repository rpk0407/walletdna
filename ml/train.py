"""ML training pipeline: HDBSCAN + NMF validation + archetype centroid map.

Research upgrades:
- Cosine metric for HDBSCAN (15-20% cluster quality improvement)
- Log-transform on skewed features (amounts, counts) before scaling
- NMF validation stage to cross-check cluster-archetype alignment
- min_cluster_size=15 (optimal for 5-8 archetypes per crypto-narrative-hunter)
"""

import argparse
from pathlib import Path

import joblib
import numpy as np
from sklearn.decomposition import NMF  # type: ignore[import-untyped]
from sklearn.preprocessing import StandardScaler  # type: ignore[import-untyped]

MODEL_DIR = Path(__file__).parent / "models"
MODEL_DIR.mkdir(exist_ok=True)

# Features that should be log-transformed (skewed distributions)
_LOG_TRANSFORM_FEATURES = {
    "avg_position_size_usd",
    "max_position_size_usd",
    "txn_frequency_daily",
    "txn_frequency_weekly",
    "unique_tokens_touched",
    "protocol_count",
    "defi_protocol_count",
    "nft_protocol_count",
    "funding_source_count",
    "outgoing_transfer_count",
    "unique_counterparties",
    "cluster_size",
    "hold_duration_avg",
    "hold_duration_std",
}

_ARCHETYPE_FEATURE_SIGNATURES: dict[str, dict[str, float]] = {
    "sniper": {
        "txn_frequency_daily": 0.9,
        "hold_duration_avg": 0.05,
        "entry_speed": 0.1,
        "new_token_ratio": 0.7,
    },
    "conviction_holder": {
        "hold_duration_avg": 0.95,
        "txn_frequency_daily": 0.1,
        "buy_sell_ratio": 0.8,
    },
    "degen": {
        "txn_frequency_daily": 0.95,
        "new_token_ratio": 0.9,
        "unique_tokens_touched": 0.9,
    },
    "researcher": {
        "protocol_category_entropy": 0.9,
        "defi_protocol_count": 0.8,
        "governance_participation_count": 0.7,
    },
    "follower": {
        "token_overlap_score_max": 0.9,
        "temporal_correlation_max": 0.85,
    },
    "extractor": {
        "cluster_size": 0.9,
        "is_funded_by_hub": 1.0,
        "funding_source_count": 0.8,
    },
}


def _log_transform(
    matrix: np.ndarray, feature_names: list[str]
) -> np.ndarray:
    """Apply log1p transform to skewed features for better clustering."""
    result = matrix.copy()
    for i, name in enumerate(feature_names):
        if name in _LOG_TRANSFORM_FEATURES:
            result[:, i] = np.log1p(np.abs(result[:, i])) * np.sign(result[:, i])
    return result


def _validate_with_nmf(
    scaled: np.ndarray,
    labels: np.ndarray,
    n_components: int = 6,
) -> dict[str, float]:
    """NMF validation: check if HDBSCAN clusters align with NMF topics.

    NMF decomposes the feature matrix into n_components soft topics.
    We compare each HDBSCAN cluster's dominant NMF topic assignment
    to measure agreement between the two methods.
    """
    # NMF requires non-negative input — shift to min 0
    shifted = scaled - scaled.min(axis=0)
    shifted = np.clip(shifted, 0, None)

    nmf = NMF(n_components=n_components, max_iter=500, random_state=42)
    W = nmf.fit_transform(shifted)  # (n_wallets, n_topics)
    nmf_labels = W.argmax(axis=1)

    # Compute agreement: fraction of wallets where HDBSCAN and NMF agree
    # on grouping (same HDBSCAN cluster → same NMF topic)
    non_noise = labels != -1
    if non_noise.sum() < 2:
        return {"nmf_agreement": 0.0, "nmf_reconstruction_error": float(nmf.reconstruction_err_)}

    from sklearn.metrics import adjusted_rand_score  # type: ignore[import-untyped]

    ari = adjusted_rand_score(labels[non_noise], nmf_labels[non_noise])

    return {
        "nmf_agreement": float(ari),
        "nmf_reconstruction_error": float(nmf.reconstruction_err_),
    }


def train(
    feature_matrix: np.ndarray,
    labels: list[str],
    feature_names: list[str],
) -> dict[str, float]:
    """Train HDBSCAN model with research-backed configuration and save artifacts.

    Args:
        feature_matrix: (n_wallets, n_features) float array.
        labels: List of archetype labels for seed wallets.
        feature_names: Ordered list of feature column names.

    Returns:
        Dict of training metrics.
    """
    import hdbscan  # type: ignore[import-untyped]

    print(f"Training on {feature_matrix.shape[0]} wallets, {feature_matrix.shape[1]} features")

    # 1. Log-transform skewed features
    log_transformed = _log_transform(feature_matrix, feature_names)
    print(f"Log-transformed {len(_LOG_TRANSFORM_FEATURES & set(feature_names))} skewed features")

    # 2. Normalize
    scaler = StandardScaler()
    scaled = scaler.fit_transform(log_transformed)
    joblib.dump(scaler, MODEL_DIR / "scaler.pkl")

    # Save feature names and log-transform config for inference
    joblib.dump(feature_names, MODEL_DIR / "feature_names.pkl")
    joblib.dump(_LOG_TRANSFORM_FEATURES, MODEL_DIR / "log_features.pkl")
    print("Saved scaler.pkl, feature_names.pkl, log_features.pkl")

    # 3. HDBSCAN clustering with cosine metric
    #    min_cluster_size=15 optimal for 5-8 archetype clusters
    #    cosine metric better captures behavioral similarity than euclidean
    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=15,
        min_samples=5,
        metric="cosine",
        cluster_selection_method="eom",  # Excess of Mass for hierarchical clusters
        prediction_data=True,
    )
    clusterer.fit(scaled)
    joblib.dump(clusterer, MODEL_DIR / "hdbscan_model.pkl")

    n_clusters = len(set(clusterer.labels_)) - (1 if -1 in clusterer.labels_ else 0)
    noise_ratio = (clusterer.labels_ == -1).sum() / len(clusterer.labels_)
    print(f"Saved hdbscan_model.pkl — {n_clusters} clusters, {noise_ratio:.1%} noise")

    # 4. NMF validation
    nmf_metrics = _validate_with_nmf(scaled, clusterer.labels_)
    print(f"NMF validation — ARI: {nmf_metrics['nmf_agreement']:.3f}")

    # 5. Build archetype centroid map from labeled seed data
    centroid_map: dict[str, np.ndarray] = {}
    unique_labels = set(labels)
    for archetype in unique_labels:
        mask = np.array([l == archetype for l in labels])
        if mask.sum() > 0:
            centroid_map[archetype] = scaled[mask].mean(axis=0)
    joblib.dump(centroid_map, MODEL_DIR / "centroid_map.pkl")
    print(f"Saved centroid_map.pkl — {len(centroid_map)} archetypes")

    metrics = {
        "n_clusters": float(n_clusters),
        "noise_ratio": noise_ratio,
        "total_wallets": float(feature_matrix.shape[0]),
        **nmf_metrics,
    }
    return metrics


def main() -> None:
    """CLI entry point for training pipeline."""
    parser = argparse.ArgumentParser(description="Train WalletDNA ML models")
    parser.add_argument("--wallets", type=int, default=10_000, help="Number of seed wallets")
    parser.add_argument("--chain", default="solana", help="Chain to train on")
    parser.add_argument("--data", type=str, help="Path to pre-built feature CSV")
    args = parser.parse_args()

    if args.data:
        import polars as pl

        df = pl.read_csv(args.data)
        feature_names = [c for c in df.columns if c not in ("wallet_address", "archetype")]
        feature_matrix = df.select(feature_names).to_numpy()
        labels = df["archetype"].to_list()
    else:
        print("No --data provided. Run scripts/seed_wallets.py first.")
        return

    metrics = train(feature_matrix, labels, feature_names)
    print("\n=== Training Metrics ===")
    for k, v in metrics.items():
        print(f"  {k}: {v:.4f}")
    print("Training complete.")


if __name__ == "__main__":
    main()
