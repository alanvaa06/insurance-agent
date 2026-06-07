"""Prompt templates for the LLM-driven steps of the claims agent.

Only two steps call the LLM: generating policy search queries and producing the
policy-grounded recommendation. Parsing, validation and the final decision are
deterministic Python (see app.agent.tools).
"""

GENERATE_POLICY_QUERIES_PROMPT = """You are a policy research assistant. Generate \
search queries to retrieve the policy sections relevant to this claim.

Claim Details:
- Vendor: {vendor_name}
- Items: {invoice_items}
- Amount: ${claim_amount}

Generate 2-3 specific search queries covering:
- Coverage for these types of services/repairs
- Vendor / repair-shop requirements (e.g. approved networks, OEM parts)
- Claim amount limits and exclusions

Return ONLY a JSON array of query strings:
["query 1", "query 2", "query 3"]"""


GENERATE_RECOMMENDATION_PROMPT = """You are a claims adjudication assistant. Decide \
whether to APPROVE or DENY this claim using ONLY the policy text provided. Do not \
invent policy terms.

Claim Details:
- Claim ID: {claim_id}
- Vendor: {vendor_name}
- Amount: ${claim_amount}
- Items: {invoice_items}

Relevant Policy Information:
{policy_text}

Guidance:
- DENY if the policy excludes the service, the vendor is not authorized, parts are
  not on the approved list, or required conditions are unmet.
- APPROVE only if the claim clearly satisfies the policy terms.
- Base every conclusion on a specific statement in the policy text above.

Return ONLY a JSON object:
{{
  "recommendation": "APPROVE" or "DENY",
  "reasoning": "detailed explanation citing the relevant policy terms"
}}"""
