"""ML training pipeline: train HDBSCAN + build archetype centroid map."""

import argparse
import pickle
from pathlib import Path

import joblib
import numpy as np
from sklearn.preprocessing import StandardScaler  # type: ignore[import-untyped]

MODEL_DIR = Path(__file__).parent / "models"
MODEL_DIR.mkdir(exist_ok=True)

_ARCHETYPE_FEATURE_SIGNATURES: dict[str, dict[str, float]] = {
    # centroid feature weights per archetype (relative)
    "sniper": {"txn_frequency_daily": 0.9, "hold_duration_avg": 0.05, "entry_speed": 0.1, "new_token_ratio": 0.7},
    "conviction_holder": {"hold_duration_avg": 0.95, "txn_frequency_daily": 0.1, "buy_sell_ratio": 0.8},
    "degen": {"txn_frequency_daily": 0.95, "new_token_ratio": 0.9, "unique_tokens_touched": 0.9},
    "researcher": {"protocol_category_entropy": 0.9, "defi_protocol_count": 0.8, "governance_participation_count": 0.7},
    "follower": {"token_overlap_score_max": 0.9, "temporal_correlation_max": 0.85},
    "extractor": {"cluster_size": 0.9, "is_funded_by_hub": 1.0, "funding_source_count": 0.8},
}


def train(
    feature_matrix: np.ndarray,
    labels: list[str],
    feature_names: list[str],
) -> None:
    """Train HDBSCAN model and save artifacts.

    Args:
        feature_matrix: (n_wallets, n_features) float array.
        labels: List of archetype labels for seed wallets.
        feature_names: Ordered list of feature column names.
    """
    import hdbscan  # type: ignore[import-untyped]

    print(f"Training on {feature_matrix.shape[0]} wallets, {feature_matrix.shape[1]} features")

    # Normalize
    scaler = StandardScaler()
    scaled = scaler.fit_transform(feature_matrix)
    joblib.dump(scaler, MODEL_DIR / "scaler.pkl")
    print("Saved scaler.pkl")

    # HDBSCAN clustering
    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=50,
        min_samples=10,
        metric="euclidean",
        prediction_data=True,
    )
    clusterer.fit(scaled)
    joblib.dump(clusterer, MODEL_DIR / "hdbscan_model.pkl")
    print(f"Saved hdbscan_model.pkl — {len(set(clusterer.labels_))} clusters")

    # Build archetype centroid map from labeled seed data
    centroid_map: dict[str, np.ndarray] = {}
    unique_labels = set(labels)
    for archetype in unique_labels:
        mask = np.array([l == archetype for l in labels])
        if mask.sum() > 0:
            centroid_map[archetype] = scaled[mask].mean(axis=0)
    joblib.dump(centroid_map, MODEL_DIR / "centroid_map.pkl")
    print(f"Saved centroid_map.pkl — {len(centroid_map)} archetypes")


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

    train(feature_matrix, labels, feature_names)
    print("Training complete.")


if __name__ == "__main__":
    main()
