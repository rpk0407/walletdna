"""Map archetype_scores dict to primary/secondary named archetypes."""


ARCHETYPE_EMOJIS: dict[str, str] = {
    "sniper": "\U0001f43a",           # wolf
    "conviction_holder": "\U0001f48e",  # diamond
    "degen": "\U0001f3b0",             # slot machine
    "researcher": "\U0001f9e0",        # brain
    "follower": "\U0001f411",          # sheep
    "extractor": "\U0001f577",         # spider
}


class ArchetypeMapper:
    """Map archetype confidence scores to primary and secondary archetypes."""

    def map(
        self,
        archetype_scores: dict[str, float],
        sybil_data: dict,
        copytrade_data: dict,
    ) -> tuple[str, str, float]:
        """Determine primary and secondary archetypes from scores and signals.

        Sybil and copy-trade data can override or boost specific archetypes.

        Args:
            archetype_scores: Dict of {archetype: confidence_0_to_1}.
            sybil_data: Sybil detection results.
            copytrade_data: Copy-trade detection results.

        Returns:
            Tuple of (primary_archetype, secondary_archetype, confidence).
        """
        scores = dict(archetype_scores)

        # Override boosts from special detectors
        if sybil_data.get("is_sybil"):
            scores["extractor"] = max(scores.get("extractor", 0), 0.85)

        if copytrade_data.get("is_follower"):
            overlap = copytrade_data.get("token_overlap_jaccard", 0)
            scores["follower"] = max(scores.get("follower", 0), 0.6 + overlap * 0.3)

        if not scores:
            return "unknown", "unknown", 0.0

        sorted_archetypes = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        primary, primary_conf = sorted_archetypes[0]
        secondary = sorted_archetypes[1][0] if len(sorted_archetypes) > 1 else primary

        return primary, secondary, round(primary_conf, 3)

    @staticmethod
    def get_emoji(archetype: str) -> str:
        """Return the display emoji for an archetype."""
        return ARCHETYPE_EMOJIS.get(archetype, "\u2753")
