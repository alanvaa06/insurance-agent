"""Security tests for the UI decision renderer.

LLM-generated reasoning is injected into HTML with unsafe_allow_html=True, so it
must be escaped to prevent script injection in the browser.
"""
from app.main import decision_html


def test_reasoning_is_html_escaped():
    payload = '<script>alert("xss")</script>'
    out = decision_html("APPROVED", payload)
    assert "<script>" not in out
    assert "&lt;script&gt;" in out


def test_img_onerror_payload_escaped():
    payload = '<img src=x onerror=alert(1)>'
    out = decision_html("DENIED", payload)
    assert "<img" not in out
    assert "onerror=alert(1)" not in out or "&lt;img" in out


def test_unknown_decision_label_escaped():
    # Fallback label uses the raw decision string.
    out = decision_html('<b>HACK</b>', "ok")
    assert "<b>HACK</b>" not in out


def test_known_decision_renders_clean_label():
    out = decision_html("APPROVED", "meets policy")
    assert "Approved" in out
    assert "meets policy" in out
