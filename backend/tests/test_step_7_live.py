"""Step 7.3: Live Ollama calibration tests.

Tests the full pipeline against real Ollama E2B and E4B models.
No mocks — every LLM call hits a real model running locally.

Run: cd backend && PYTHONPATH=. ../venv/Scripts/pytest.exe tests/test_step_7_live.py -m live -v --tb=short
Skip: normal pytest runs exclude these via marker (no -m live flag).

Each test is parametrized across both models via the `live_llm` fixture.
Soft assertions: check that answers mention relevant keywords, not exact text.
Latency: PipelineLogger's TimedContext captures per-node timing automatically;
we print a timing summary at the end of each test.
"""

import asyncio
import time
from pathlib import Path

import pytest

from app.agents.field_assistant import run_field_assistant
from app.knowledge_pack.builder import build_pack
from app.knowledge_pack.loader import get_active_pack, load_pack, unload_pack
from app.logger import pipeline_logger as log


pytestmark = pytest.mark.live


# ============================================================
# Module-scoped pack (built once, used by all live tests)
# ============================================================

@pytest.fixture(scope="module")
def live_pack_path(tmp_path_factory):
    """Build a real Knowledge Pack once for all live tests."""
    base = tmp_path_factory.mktemp("live_packs")
    return build_pack("live_test_pack", base_path=base)


@pytest.fixture(scope="module")
def live_loaded_pack(live_pack_path):
    """Load the pack as the active singleton for live tests."""
    pack = load_pack(live_pack_path)
    yield pack
    unload_pack()


@pytest.fixture(autouse=True)
def _ensure_live_pack(live_loaded_pack):
    """Ensure pack is loaded before every live test."""
    assert get_active_pack() is not None


# ============================================================
# Reset graph + logger between tests (same as integration tests)
# ============================================================

@pytest.fixture(autouse=True)
def _reset_graph_and_logger():
    """Reset graph singleton and PipelineLogger between tests."""
    import app.agents.field_assistant as fa

    fa._graph = None
    log._buffer.clear()
    log._session_id = None
    log._pipeline_start = None
    log._total_llm_calls = 0
    log._total_tokens_in = 0
    log._total_tokens_out = 0
    yield
    fa._graph = None


# ============================================================
# Helpers
# ============================================================

def _run(coro):
    """Run async from sync test code."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(asyncio.run, coro).result()
    return asyncio.run(coro)


def _print_timing(result: dict, model: str, scenario: str):
    """Print a timing summary from PipelineLogger's buffer."""
    tool_log = result.get("tool_calls_log", [])
    print(f"\n{'='*60}")
    print(f"  {scenario} | Model: {model}")
    print(f"{'='*60}")
    total = 0.0
    for entry in tool_log:
        step = entry.get("step", "?")
        action = entry.get("action", "?")
        elapsed = entry.get("elapsed_ms", 0)
        if elapsed:
            total += elapsed
            print(f"  {step:20s} | {action:20s} | {elapsed:>8.0f}ms")
    print(f"  {'TOTAL':20s} | {'':20s} | {total:>8.0f}ms")
    print(f"{'='*60}\n")


def _soft_assert_answer_mentions(answer: str, keywords: list[str], min_matches: int = 1):
    """Assert the answer mentions at least min_matches of the given keywords."""
    answer_lower = answer.lower()
    matches = [kw for kw in keywords if kw.lower() in answer_lower]
    assert len(matches) >= min_matches, (
        f"Expected answer to mention at least {min_matches} of {keywords}, "
        f"but only found {matches}.\n"
        f"Answer: {answer[:500]}"
    )


# ============================================================
# Test: Text-only Disease Diagnosis
# ============================================================

class TestLiveDiagnosis:
    """Text query → classify → route → search → rerank → generate.

    No image. Tests whether the LLM can:
    1. Parse the classify JSON format correctly
    2. Generate meaningful search queries
    3. Score and keep relevant results
    4. Produce a grounded answer mentioning the disease
    """

    def test_cassava_yellow_leaves(self, live_llm):
        """Classic CMD symptom description → should mention mosaic or disease."""
        start = time.time()
        result = _run(run_field_assistant(
            message="My cassava leaves have yellow patches and they are curling up. What is wrong?",
        ))
        wall_time = time.time() - start

        _print_timing(result, live_llm[0], "Cassava Yellow Leaves")
        print(f"  Wall time: {wall_time:.1f}s")
        print(f"  Answer: {result['final_answer'][:300]}")

        assert result["final_answer"], "Should produce a non-empty answer"
        _soft_assert_answer_mentions(
            result["final_answer"],
            ["cassava", "mosaic", "disease", "virus", "yellow", "leaf", "whitefly"],
            min_matches=2,
        )
        assert result["retrieval_attempts"] >= 1

    def test_rice_blast_symptoms(self, live_llm):
        """Rice blast description → should mention blast or fungal."""
        start = time.time()
        result = _run(run_field_assistant(
            message="My rice plants have diamond-shaped lesions on the leaves with grey centers. What disease is this?",
        ))
        wall_time = time.time() - start

        _print_timing(result, live_llm[0], "Rice Blast Symptoms")
        print(f"  Wall time: {wall_time:.1f}s")
        print(f"  Answer: {result['final_answer'][:300]}")

        assert result["final_answer"]
        _soft_assert_answer_mentions(
            result["final_answer"],
            ["rice", "blast", "fungal", "fungus", "lesion", "disease"],
            min_matches=2,
        )


# ============================================================
# Test: Hero Shot (Image + Diagnosis)
# ============================================================

class TestLiveHeroShot:
    """THE demo scenario: photo → diagnosis → treatment.

    Tests the full image pipeline:
    1. image_analysis.py sends image to Ollama vision
    2. classify_and_extract uses visual description
    3. Pipeline searches knowledge base
    4. generate_answer produces diagnosis
    """

    def test_image_diagnosis(self, live_llm, test_image_path):
        """Plant photo → should describe symptoms and attempt diagnosis."""
        start = time.time()
        result = _run(run_field_assistant(
            message="What's wrong with my cassava plant?",
            image_path=str(test_image_path),
        ))
        wall_time = time.time() - start

        _print_timing(result, live_llm[0], "Hero Shot — Image Diagnosis")
        print(f"  Wall time: {wall_time:.1f}s")
        print(f"  Answer: {result['final_answer'][:500]}")

        assert result["final_answer"], "Should produce a non-empty answer"
        # Soft: the model should at least try to discuss the plant
        _soft_assert_answer_mentions(
            result["final_answer"],
            ["cassava", "leaf", "leaves", "disease", "mosaic", "plant",
             "yellow", "spot", "symptom", "crop"],
            min_matches=2,
        )

    def test_treatment_followup(self, live_llm, test_image_path):
        """Turn 1: image diagnosis. Turn 2: ask for treatment."""
        # Turn 1
        turn1 = _run(run_field_assistant(
            message="What's wrong with my cassava?",
            image_path=str(test_image_path),
        ))
        print(f"  Turn 1 answer: {turn1['final_answer'][:200]}")

        # Turn 2: treatment follow-up
        start = time.time()
        turn2 = _run(run_field_assistant(
            message="How do I treat this disease?",
            conversation_history=turn1["conversation_history"],
            conversation_summary=turn1["conversation_summary"],
        ))
        wall_time = time.time() - start

        _print_timing(turn2, live_llm[0], "Hero Shot — Treatment Follow-up")
        print(f"  Wall time: {wall_time:.1f}s")
        print(f"  Turn 2 answer: {turn2['final_answer'][:500]}")

        assert turn2["final_answer"]
        _soft_assert_answer_mentions(
            turn2["final_answer"],
            ["treat", "treatment", "remove", "neem", "resistant", "plant",
             "spray", "organic", "control", "variety"],
            min_matches=2,
        )
        # History should grow
        assert len(turn2["conversation_history"]) > len(turn1["conversation_history"])


# ============================================================
# Test: Treatment Query (text only)
# ============================================================

class TestLiveTreatment:
    """Direct treatment question — no prior context."""

    def test_organic_treatment_query(self, live_llm):
        """Ask for organic cassava mosaic treatment → actionable steps."""
        start = time.time()
        result = _run(run_field_assistant(
            message="How do I treat cassava mosaic disease using organic methods and local materials?",
        ))
        wall_time = time.time() - start

        _print_timing(result, live_llm[0], "Organic Treatment Query")
        print(f"  Wall time: {wall_time:.1f}s")
        print(f"  Answer: {result['final_answer'][:500]}")

        assert result["final_answer"]
        _soft_assert_answer_mentions(
            result["final_answer"],
            ["cassava", "mosaic", "neem", "organic", "treatment", "remove",
             "resistant", "whitefly", "plant", "spray"],
            min_matches=2,
        )


# ============================================================
# Test: Farming Advice
# ============================================================

class TestLiveFarmingAdvice:
    """Seasonal farming question."""

    def test_planting_season(self, live_llm):
        """When to plant rice in Casamance → seasonal guidance."""
        start = time.time()
        result = _run(run_field_assistant(
            message="When is the best time to plant rice in the Casamance region of Senegal?",
        ))
        wall_time = time.time() - start

        _print_timing(result, live_llm[0], "Planting Season Advice")
        print(f"  Wall time: {wall_time:.1f}s")
        print(f"  Answer: {result['final_answer'][:500]}")

        assert result["final_answer"]
        _soft_assert_answer_mentions(
            result["final_answer"],
            ["rice", "plant", "season", "rain", "june", "july", "casamance",
             "senegal", "month", "harvest"],
            min_matches=2,
        )


# ============================================================
# Test: Observation Logging
# ============================================================

class TestLiveObservation:
    """Observation intent → LLM parses → saves to DB."""

    def test_log_field_observation(self, live_llm, live_loaded_pack):
        """Natural language observation → parsed and saved to SQLite."""
        start = time.time()
        result = _run(run_field_assistant(
            message="I'm noting that in field 3 near the river, I found several cassava plants showing brown spots on the lower leaves. About 10 plants affected.",
        ))
        wall_time = time.time() - start

        _print_timing(result, live_llm[0], "Observation Logging")
        print(f"  Wall time: {wall_time:.1f}s")
        print(f"  Answer: {result['final_answer'][:300]}")

        assert result["final_answer"]
        # Should confirm the observation was saved
        _soft_assert_answer_mentions(
            result["final_answer"],
            ["observation", "saved", "recorded", "logged", "noted", "field"],
            min_matches=1,
        )
        # Stats should be present
        assert result.get("observation_stats") is not None


# ============================================================
# Test: Retry Loop Termination
# ============================================================

class TestLiveRetryLoop:
    """Ensure the retry loop terminates within 3 attempts."""

    def test_obscure_query_terminates(self, live_llm):
        """A query unlikely to find good results should still terminate.

        The pipeline should try up to 3 search attempts, then generate
        a best-effort answer or "I don't have enough information."
        """
        start = time.time()
        result = _run(run_field_assistant(
            message="Tell me about advanced genetic engineering techniques for drought-resistant cassava cultivars using CRISPR-Cas9 gene editing.",
        ))
        wall_time = time.time() - start

        _print_timing(result, live_llm[0], "Obscure Query (Retry Termination)")
        print(f"  Wall time: {wall_time:.1f}s")
        print(f"  Retrieval attempts: {result['retrieval_attempts']}")
        print(f"  Answer: {result['final_answer'][:300]}")

        assert result["final_answer"], "Should produce an answer even if search fails"
        assert result["retrieval_attempts"] <= 3, (
            f"Retry loop should terminate at 3, got {result['retrieval_attempts']}"
        )


# ============================================================
# Test: Multi-Turn Conversation (3 turns)
# ============================================================

class TestLiveMultiTurn:
    """Full 3-turn conversation mirroring the demo video arc."""

    def test_three_turn_conversation(self, live_llm, test_image_path, live_loaded_pack):
        """Turn 1: diagnose. Turn 2: treat. Turn 3: log observation."""
        # --- Turn 1: Image diagnosis ---
        print("\n--- Turn 1: Image Diagnosis ---")
        t1_start = time.time()
        turn1 = _run(run_field_assistant(
            message="I found this sick cassava plant in my field. What disease does it have?",
            image_path=str(test_image_path),
        ))
        t1_time = time.time() - t1_start
        print(f"  [{t1_time:.1f}s] {turn1['final_answer'][:200]}")

        assert turn1["final_answer"]
        assert turn1["conversation_summary"]

        # --- Turn 2: Treatment ---
        print("\n--- Turn 2: Treatment Request ---")
        t2_start = time.time()
        turn2 = _run(run_field_assistant(
            message="What treatment do you recommend? I'd like to use organic methods.",
            conversation_history=turn1["conversation_history"],
            conversation_summary=turn1["conversation_summary"],
        ))
        t2_time = time.time() - t2_start
        print(f"  [{t2_time:.1f}s] {turn2['final_answer'][:200]}")

        assert turn2["final_answer"]
        assert len(turn2["conversation_history"]) > len(turn1["conversation_history"])

        # --- Turn 3: Log observation ---
        print("\n--- Turn 3: Log Observation ---")
        t3_start = time.time()
        turn3 = _run(run_field_assistant(
            message="I'm going to try the neem treatment. Logging this observation for field 3.",
            conversation_history=turn2["conversation_history"],
            conversation_summary=turn2["conversation_summary"],
        ))
        t3_time = time.time() - t3_start
        print(f"  [{t3_time:.1f}s] {turn3['final_answer'][:200]}")

        assert turn3["final_answer"]

        # Summary
        total = t1_time + t2_time + t3_time
        print(f"\n  Total 3-turn time: {total:.1f}s ({live_llm[0]} via {live_llm[1]})")
        print(f"  Turn 1 (diagnosis):   {t1_time:.1f}s")
        print(f"  Turn 2 (treatment):   {t2_time:.1f}s")
        print(f"  Turn 3 (observation): {t3_time:.1f}s")


# ============================================================
# Test: JSON Parse Reliability
# ============================================================

class TestLiveJSONParsing:
    """Verify that the LLM consistently returns parseable JSON.

    This is a calibration concern: small models may wrap JSON in
    markdown code blocks, add preamble text, or produce malformed
    output. Our parsing has fallbacks, but we want to know how
    often they trigger.
    """

    def test_classify_returns_valid_json(self, live_llm):
        """Run 3 diverse queries and check classify_result is populated."""
        queries = [
            "My cassava leaves have yellow patches",
            "How do I treat rice blast?",
            "I saw brown spots on tomato leaves in field 2",
        ]
        for query in queries:
            result = _run(run_field_assistant(message=query))
            assert result.get("classify_result") is not None, (
                f"classify_result was None for query: {query}"
            )
            cr = result["classify_result"]
            assert cr.intent is not None, f"Intent was None for: {query}"
            assert cr.confidence > 0, f"Confidence was 0 for: {query}"
            print(f"  [{live_llm[0]}] '{query[:40]}...' -> "
                  f"intent={cr.intent.value}, conf={cr.confidence:.2f}")
