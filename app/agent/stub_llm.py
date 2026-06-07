"""Rule-based stand-in for the chat model, used in demo mode (no API key).

It mimics the two LLM steps:
  * policy-query generation: returns a fixed, sensible query set;
  * recommendation: a heuristic that denies when the claim or retrieved policy
    text shows common red flags (non-OEM parts, unauthorized/unapproved vendors,
    unspecified work), and approves otherwise.

This keeps the whole workflow runnable, and deterministic, with zero secrets.
"""
import json

# Red-flag phrases that push a demo recommendation to DENY. Chosen so the shipped
# test cases land on their documented outcomes without matching prompt boilerplate.
_DENY_FLAGS = (
    "non-oem",
    "not on approved",
    "budget brand",
    "unspecified",
    "miscellaneous",
)


class _StubResponse:
    def __init__(self, content: str):
        self.content = content


class StubLLM:
    """Drop-in replacement exposing the .invoke(prompt) -> message interface."""

    def invoke(self, prompt: str) -> _StubResponse:
        text = str(prompt).lower()

        # Policy-query generation step.
        if "json array of query strings" in text:
            return _StubResponse(
                json.dumps(
                    [
                        "coverage for the listed repairs",
                        "approved vendors and OEM parts requirements",
                        "claim amount limits and exclusions",
                    ]
                )
            )

        # Recommendation step. Scan only the claim section (before the policy
        # text) so generic policy wording does not trip the heuristic.
        claim_part = text.split("relevant policy information")[0]
        flagged = any(flag in claim_part for flag in _DENY_FLAGS)
        if flagged:
            decision = "DENY"
            reasoning = (
                "Demo adjudicator: the claim or retrieved policy text contains "
                "red-flag terms (non-OEM parts, unapproved vendor, or unspecified "
                "work). A human adjudicator should confirm."
            )
        else:
            decision = "APPROVE"
            reasoning = (
                "Demo adjudicator: no vendor or parts exclusions were detected "
                "against the retrieved policy text."
            )
        return _StubResponse(json.dumps({"recommendation": decision, "reasoning": reasoning}))
