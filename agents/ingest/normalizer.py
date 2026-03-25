"""Normalize chain-specific transaction formats into the unified WalletDNA schema."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def normalize_transactions(raw_txns: list[dict], chain: str) -> list[dict]:
    """Convert raw chain transactions into the unified WalletDNA format.

    Args:
        raw_txns: List of chain-native transaction records.
        chain: Source chain identifier ("solana", "ethereum", etc.).

    Returns:
        List of normalized transaction dicts conforming to the WalletDNA schema.
    """
    if chain == "solana":
        return [_normalize_helius(t) for t in raw_txns if t]
    return [_normalize_alchemy(t) for t in raw_txns if t]


def _normalize_helius(tx: dict[str, Any]) -> dict:
    """Normalize a Helius-enriched Solana transaction."""
    return {
        "hash": tx.get("signature", ""),
        "chain": "solana",
        "block_number": tx.get("slot", 0),
        "timestamp": _parse_ts(tx.get("timestamp", 0)),
        "from_address": tx.get("feePayer", ""),
        "to_address": _extract_solana_to(tx),
        "type": _map_helius_type(tx.get("type", "UNKNOWN")),
        "token_in": _extract_token_in_helius(tx),
        "token_out": _extract_token_out_helius(tx),
        "amount_usd": float(tx.get("nativeTransfers", [{}])[0].get("amount", 0)) / 1e9,
        "fee_usd": float(tx.get("fee", 0)) / 1e9,
        "protocol": tx.get("source", None),
        "is_contract_interaction": tx.get("type") not in ("TRANSFER", None),
        "decoded_method": tx.get("type"),
        "raw": tx,
    }


def _normalize_alchemy(tx: dict[str, Any]) -> dict:
    """Normalize an Alchemy EVM asset transfer record."""
    return {
        "hash": tx.get("hash", ""),
        "chain": tx.get("network", "ethereum"),
        "block_number": int(tx.get("blockNum", "0x0"), 16),
        "timestamp": tx.get("metadata", {}).get("blockTimestamp", ""),
        "from_address": tx.get("from", ""),
        "to_address": tx.get("to", ""),
        "type": _map_alchemy_category(tx.get("category", "external")),
        "token_in": None,
        "token_out": {
            "symbol": tx.get("asset"),
            "address": tx.get("rawContract", {}).get("address"),
        },
        "amount_usd": float(tx.get("value") or 0),
        "fee_usd": 0.0,
        "protocol": None,
        "is_contract_interaction": tx.get("category") != "external",
        "decoded_method": None,
        "raw": tx,
    }


def _parse_ts(ts: int | str) -> str:
    if isinstance(ts, int):
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
    return str(ts)


def _extract_solana_to(tx: dict) -> str:
    transfers = tx.get("nativeTransfers", [])
    return transfers[0].get("toUserAccount", "") if transfers else ""


def _extract_token_in_helius(tx: dict) -> dict | None:
    swaps = tx.get("tokenTransfers", [])
    return {"symbol": swaps[0].get("mint"), "address": swaps[0].get("mint")} if len(swaps) > 1 else None


def _extract_token_out_helius(tx: dict) -> dict | None:
    swaps = tx.get("tokenTransfers", [])
    return {"symbol": swaps[-1].get("mint"), "address": swaps[-1].get("mint")} if swaps else None


def _map_helius_type(t: str) -> str:
    mapping = {
        "SWAP": "swap", "TRANSFER": "transfer", "TOKEN_MINT": "mint",
        "NFT_SALE": "nft_trade", "STAKE": "stake", "UNKNOWN": "unknown",
    }
    return mapping.get(t, "unknown")


def _map_alchemy_category(c: str) -> str:
    mapping = {"external": "transfer", "erc20": "transfer", "erc721": "nft_trade", "erc1155": "nft_trade"}
    return mapping.get(c, "unknown")
