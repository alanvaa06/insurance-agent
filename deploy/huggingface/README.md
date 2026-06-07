---
title: Insurance Claims Processing Agent
emoji: 🗂️
colorFrom: gray
colorTo: indigo
sdk: docker
app_port: 8501
pinned: false
license: mit
---

# Insurance Claims Processing Agent

Automated adjudication of auto-repair insurance claims. A LangGraph workflow
parses and validates a claim, checks policy coverage, retrieves relevant policy
text, and produces a decision: Approved, Denied, Requires review, or Invalid.

This Space runs in **demo mode** (no API key): local keyword retrieval over the
policy document plus a rule-based adjudicator, so it works with no secrets. Set
an `OPENAI_API_KEY` secret to enable live LLM adjudication.

Source: https://github.com/alanvaa06/insurance-agent
