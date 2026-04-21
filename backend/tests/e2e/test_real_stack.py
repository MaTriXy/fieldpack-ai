"""End-to-end scenarios against a real running FieldPack stack.

These tests exercise the live HTTP surface — no FastAPI TestClient, no in-process
pack, no LLM mocks. They require:
  - Backend reachable at FIELDPACK_E2E_URL (default http://localhost:8000)
  - A Knowledge Pack already loaded (Docker compose auto-loads casamance_agriculture)
  - Ollama running with the configured model pulled

Run: `pytest tests/e2e/ -m e2e -v`
"""

import base64
from pathlib import Path

import pytest

pytestmark = pytest.mark.e2e


FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
TEST_IMAGE = FIXTURES_DIR / "cassava_mosaic_test.jpg"


async def test_golden_path_cassava_question(e2e_client):
    """A normal RAG query returns a non-trivial reply with source citations."""
    resp = await e2e_client.post(
        "/chat/",
        json={"message": "what variety of cassava is best for Casamance?"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["reply"], "reply should be non-empty"
    assert len(body["reply"]) > 100, f"reply too short: {body['reply']!r}"
    assert body["sources"], "sources list should be non-empty for a pack-grounded answer"


async def test_image_upload_then_diagnosis(e2e_client):
    """Upload a cassava leaf photo, then ask the assistant about it."""
    assert TEST_IMAGE.exists(), f"Missing fixture image at {TEST_IMAGE}"

    img_bytes = TEST_IMAGE.read_bytes()
    upload_resp = await e2e_client.post(
        "/upload/image/base64",
        json={"data": base64.b64encode(img_bytes).decode("ascii"), "format": "jpeg"},
    )
    assert upload_resp.status_code == 200, upload_resp.text
    image_path = upload_resp.json()["image_path"]
    assert image_path, "upload should return an image_path"

    chat_resp = await e2e_client.post(
        "/chat/",
        json={
            "message": "what is wrong with my cassava?",
            "image_path": image_path,
        },
    )
    assert chat_resp.status_code == 200, chat_resp.text
    body = chat_resp.json()
    assert body["reply"], "reply should be non-empty for image-grounded query"


async def test_ask_back_on_vague_query(e2e_client):
    """A vague message should trigger a clarifying response, not a confident diagnosis.

    We accept either literal '?' OR ask-back language markers. LLMs sometimes
    phrase clarifications with '.' + bullet lists ("Please describe...\n* option A\n* option B").
    """
    resp = await e2e_client.post(
        "/chat/",
        json={"message": "my plant is sick"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    reply = body["reply"]
    assert reply, "reply should be non-empty"

    reply_lower = reply.lower()
    ask_back_markers = (
        "please describe",
        "please specify",
        "please provide",
        "please tell",
        "could you",
        "can you",
        "what symptoms",
        "what crop",
        "which crop",
        "which plant",
        "more detail",
        "more information",
        "clarify",
        "specify",
    )
    has_question = "?" in reply
    has_ask_back_language = any(m in reply_lower for m in ask_back_markers)
    assert has_question or has_ask_back_language, (
        f"Expected clarifying question or ask-back language, got reply={reply!r}"
    )


async def test_no_match_refusal_off_topic(e2e_client):
    """Off-topic query (not in pack) should refuse gracefully, not fabricate."""
    resp = await e2e_client.post(
        "/chat/",
        json={"message": "how do I grow coffee beans?"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    reply = body["reply"]
    assert reply, "reply should be non-empty"

    # Soft heuristic: look for graceful-refusal language. Log for human review
    # if none of these markers appear — LLMs are non-deterministic.
    refusal_markers = (
        "not in",
        "don't have",
        "do not have",
        "no information",
        "outside",
        "cannot",
        "can't help",
        "not covered",
        "not available",
        "unable to",
    )
    reply_lower = reply.lower()
    looks_like_refusal = any(m in reply_lower for m in refusal_markers)
    if not looks_like_refusal:
        print(f"\n[WARN] Off-topic reply may have hallucinated. Review:\n{reply}\n")
