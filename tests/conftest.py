"""Shared test fixtures.

These let the whole pipeline run with no network, no API key and no ChromaDB:
a fake LLM returns scripted JSON and a fake store returns canned policy text.
"""
import json
from pathlib import Path

import pytest

TEST_CASE_DIR = Path(__file__).resolve().parent.parent / "test_cases"


class FakeMessage:
    def __init__(self, content: str):
        self.content = content


class FakeLLM:
    """Returns queued responses in order; records prompts it received."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.prompts = []

    def invoke(self, prompt):
        self.prompts.append(prompt)
        if self._responses:
            return FakeMessage(self._responses.pop(0))
        return FakeMessage("{}")


class FakeStore:
    """Stand-in for PolicyVectorStore.retrieve."""

    def __init__(self, text="Policy excerpt: standard coverage applies."):
        self.text = text
        self.queries = []

    def retrieve(self, query, top_k=5):
        self.queries.append(query)
        return self.text


def queries_json(*queries):
    return json.dumps(list(queries))


def recommendation_json(decision, reasoning="because policy says so"):
    return json.dumps({"recommendation": decision, "reasoning": reasoning})


@pytest.fixture
def fake_store():
    return FakeStore()


def load_test_case(name: str) -> dict:
    with open(TEST_CASE_DIR / name, encoding="utf-8") as fh:
        return json.load(fh)
