"""Normalize chain-specific transaction formats into unified WalletDNA schema."""

from datetime import datetime, timezone
from typing import Any


class NormalizedTransaction:
    """Unified transaction schema across all supported chains."""

    __slots__ = (
        "hash", "chain", "block_number", "timestamp", "from_address", "to_address",
        "type", "token_in", "token_out", "amount_usd", "fee_usd",
        "protocol", "is_contract_interaction", "decoded_method", "raw",
    )

    def __init__(
        self,
        hash: str,
        chain: str,
        block_number: int,
        timestamp: datetime,
        from_address: str,
        to_address: str,
        type: str,
        token_in: dict | None,
        token_out: dict | None,
        amount_usd: float,
        fee_usd: float,
        protocol: str | None,
        is_contract_interaction: bool,
        decoded_method: str | None,
        raw: dict,
    ) -> None:
        self.hash = hash
        self.chain = chain
        self.block_number = block_number
        self.timestamp = timestamp
        self.from_address = from_address
        self.to_address = to_address
        self.type = type
        self.token_in = token_in
        self.token_out = token_out
        self.amount_usd = amount_usd
        self.fee_usd = fee_usd
        self.protocol = protocol
        self.is_contract_interaction = is_contract_interaction
        self.decoded_method = decoded_method
        self.raw = raw

    def to_dict(self) -> dict[str, Any]:
        """Serialize to plain dict for LangGraph state storage."""
        return {
            "hash": self.hash,
            "chain": self.chain,
            "block_number": self.block_number,
            "timestamp": self.timestamp.isoformat(),
            "from_address": self.from_address,
            "to_address": self.to_address,
            "type": self.type,
            "token_in": self.token_in,
            "token_out": self.token_out,
            "amount_usd": self.amount_usd,
            "fee_usd": self.fee_usd,
            "protocol": self.protocol,
            "is_contract_interaction": self.is_contract_interaction,
            "decoded_method": self.decoded_method,
        }


def normalize_transactions(raw: list[dict], chain: str) -> list[dict]:
    """Convert chain-specific transaction lists to unified WalletDNA format.

    Args:
        raw: Raw transaction dicts from Helius or Alchemy.
        chain: Chain identifier to select the correct normalizer.

    Returns:
        List of normalized transaction dicts.
    """
    if chain == "solana":
        return [_normalize_helius(tx).to_dict() for tx in raw]
    return [_normalize_alchemy(tx, chain).to_dict() for tx in raw]


def _normalize_helius(tx: dict) -> NormalizedTransaction:
    """Normalize a Helius enhanced transaction."""
    ts = datetime.fromtimestamp(tx.get("timestamp", 0), tz=timezone.utc)
    tx_type = tx.get("type", "UNKNOWN").lower()
    fee_lamports = tx.get("fee", 0)

    return NormalizedTransaction(
        hash=tx.get("signature", ""),
        chain="solana",
        block_number=tx.get("slot", 0),
        timestamp=ts,
        from_address=tx.get("feePayer", ""),
        to_address=_extract_helius_to(tx),
        type=_map_helius_type(tx_type),
        token_in=_extract_helius_token_in(tx),
        token_out=_extract_helius_token_out(tx),
        amount_usd=_extract_helius_usd(tx),
        fee_usd=fee_lamports / 1_000_000_000 * 150,  # rough SOL price estimate
        protocol=tx.get("source"),
        is_contract_interaction=tx_type not in ("transfer", "unknown"),
        decoded_method=tx.get("type"),
        raw=tx,
    )


def _normalize_alchemy(tx: dict, chain: str) -> NormalizedTransaction:
    """Normalize an Alchemy asset transfer."""
    ts_str = tx.get("metadata", {}).get("blockTimestamp", "1970-01-01T00:00:00Z")
    ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    category = tx.get("category", "external")

    return NormalizedTransaction(
        hash=tx.get("hash", ""),
        chain=chain,
        block_number=int(tx.get("blockNum", "0x0"), 16),
        timestamp=ts,
        from_address=tx.get("from", ""),
        to_address=tx.get("to", ""),
        type=_map_alchemy_category(category),
        token_in=None,
        token_out=_extract_alchemy_token(tx),
        amount_usd=float(tx.get("value") or 0),
        fee_usd=0.0,  # Alchemy transfers don't include fee
        protocol=None,
        is_contract_interaction=category not in ("external", "internal"),
        decoded_method=None,
        raw=tx,
    )


# --- Helius helpers ---

def _extract_helius_to(tx: dict) -> str:
    events = tx.get("events", {})
    swap = events.get("swap", {})
    if swap:
        return swap.get("innerSwaps", [{}])[0].get("programInfo", {}).get("programName", "")
    return ""


def _map_helius_type(tx_type: str) -> str:
    mapping = {
        "swap": "swap",
        "transfer": "transfer",
        "nft_sale": "nft_trade",
        "stake": "stake",
        "compressed_nft_mint": "nft_trade",
        "bridge": "bridge",
        "governance_vote": "governance",
    }
    return mapping.get(tx_type, "unknown")


def _extract_helius_token_in(tx: dict) -> dict | None:
    swap = tx.get("events", {}).get("swap", {})
    if swap and swap.get("tokenInputs"):
        t = swap["tokenInputs"][0]
        return {"symbol": t.get("symbol"), "mint": t.get("mint"), "amount": t.get("tokenAmount")}
    return None


def _extract_helius_token_out(tx: dict) -> dict | None:
    swap = tx.get("events", {}).get("swap", {})
    if swap and swap.get("tokenOutputs"):
        t = swap["tokenOutputs"][0]
        return {"symbol": t.get("symbol"), "mint": t.get("mint"), "amount": t.get("tokenAmount")}
    return None


def _extract_helius_usd(tx: dict) -> float:
    swap = tx.get("events", {}).get("swap", {})
    return float(swap.get("nativeInput", {}).get("amount", 0)) / 1e9 * 150


# --- Alchemy helpers ---

def _map_alchemy_category(category: str) -> str:
    mapping = {"erc20": "transfer", "erc721": "nft_trade", "erc1155": "nft_trade", "external": "transfer", "internal": "transfer"}
    return mapping.get(category, "unknown")


def _extract_alchemy_token(tx: dict) -> dict | None:
    asset = tx.get("asset")
    if not asset:
        return None
    return {"symbol": asset, "address": tx.get("rawContract", {}).get("address"), "amount": tx.get("value")}
