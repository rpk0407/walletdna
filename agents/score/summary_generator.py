"""Generate a behavioral summary using the Claude API (Sonnet)."""

import anthropic
import structlog

from api.config import settings

logger = structlog.get_logger()

_MODEL = "claude-sonnet-4-6"
_MAX_TOKENS = 200

_PROMPT_TEMPLATE = """\
You are WalletDNA's behavioral analyst. Given a wallet's archetype classification \
and dimension scores, generate a 2-3 sentence personality summary.

Archetype: {primary_archetype} (confidence: {confidence_pct}%)
Secondary: {secondary_archetype}
Dimensions: Speed={speed}, Conviction={conviction}, Risk={risk_appetite}, \
Sophistication={sophistication}, Originality={originality}, Consistency={consistency}
Key Stats: {total_txns} transactions, {unique_tokens} unique tokens, \
{active_days} active days

Write in third person. Be specific about behavioral patterns. No generic filler.

Example style: "A methodical sniper who enters positions within minutes of token \
deployment but exits with unusual patience — average holds of 4.2 hours suggest \
calculated exit strategies rather than panic selling."
"""


class SummaryGenerator:
    """Call Claude Sonnet once per wallet to generate a behavioral summary."""

    def __init__(self) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def generate(
        self,
        primary_archetype: str,
        secondary_archetype: str,
        dimensions: dict[str, int],
        features: dict[str, float],
        confidence: float,
    ) -> str:
        """Generate a 2-3 sentence behavioral summary via Claude API.

        Args:
            primary_archetype: Primary archetype name.
            secondary_archetype: Secondary archetype name.
            dimensions: 6-dimension score dict.
            features: Scalar feature dict for key stats.
            confidence: Primary archetype confidence (0-1).

        Returns:
            Natural language behavioral summary string.
        """
        prompt = _PROMPT_TEMPLATE.format(
            primary_archetype=primary_archetype.replace("_", " ").title(),
            secondary_archetype=secondary_archetype.replace("_", " ").title(),
            confidence_pct=int(confidence * 100),
            speed=dimensions.get("speed", 0),
            conviction=dimensions.get("conviction", 0),
            risk_appetite=dimensions.get("risk_appetite", 0),
            sophistication=dimensions.get("sophistication", 0),
            originality=dimensions.get("originality", 0),
            consistency=dimensions.get("consistency", 0),
            total_txns=int(features.get("txn_frequency_daily", 0) * features.get("first_to_last_active_days", 1)),
            unique_tokens=int(features.get("unique_tokens_touched", 0)),
            active_days=int(features.get("first_to_last_active_days", 0)),
        )

        try:
            message = await self._client.messages.create(
                model=_MODEL,
                max_tokens=_MAX_TOKENS,
                messages=[{"role": "user", "content": prompt}],
            )
            summary = message.content[0].text.strip()
            logger.info("summary.generated", archetype=primary_archetype)
            return summary
        except Exception as exc:
            logger.error("summary.error", error=str(exc))
            return f"A {primary_archetype.replace('_', ' ')} with {int(confidence * 100)}% confidence."
