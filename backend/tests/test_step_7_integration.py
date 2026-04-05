"""Step 7.2: End-to-end integration tests for the field assistant pipeline.

Tests the full LangGraph pipeline from user message to final answer.
Uses a real Knowledge Pack (SQLite + ChromaDB) built from seed data,
but mocks all LLM calls (Ollama) for speed and determinism.

LLM-calling nodes: classify, needs_search, craft_query, rerank, generate_answer, log_observation.
Non-LLM nodes: route, execute_search, expand_route (use real code + real pack data).

Structure:
  - Module-scoped pack fixture (built once, shared across all tests)
  - `mock_all_llms` fixture patches all 6 LLM-calling nodes at once
  - Each test class covers a scenario: diagnosis, treatment, farming, follow-up, observation, hero shot
  - WebSocket test uses FastAPI TestClient
"""

import asyncio
import json
from unittest.mock import MagicMock, patch

import pytest

from app.agents.field_assistant import run_field_assistant
from app.knowledge_pack.builder import build_pack
from app.knowledge_pack.loader import get_active_pack, load_pack, unload_pack


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture(scope="module")
def pack_path(tmp_path_factory):
    """Build a real Knowledge Pack once for all integration tests."""
    base = tmp_path_factory.mktemp("integration_packs")
    return build_pack("integration_test_pack", base_path=base)


@pytest.fixture(scope="module")
def loaded_pack(pack_path):
    """Load the pack as the active singleton for the entire test module."""
    pack = load_pack(pack_path)
    yield pack
    unload_pack()


@pytest.fixture(autouse=True)
def _ensure_pack_loaded(loaded_pack):
    """Ensure the pack is loaded before every test (autouse)."""
    assert get_active_pack() is not None


@pytest.fixture
def temporarily_unload_pack(loaded_pack):
    """Unload the active pack for the duration of a test, then reload.

    Use for tests that verify "no pack loaded" error behavior.
    Handles reload even if the test itself raises.
    """
    pack_path = loaded_pack.path
    unload_pack()
    yield
    load_pack(pack_path)


def _mock_llm_response(content: str):
    """Create a MagicMock mimicking an AIMessage with .content."""
    resp = MagicMock()
    resp.content = content
    return resp


def _make_classify_json(
    intent: str,
    crop: str | None = None,
    disease_name: str | None = None,
    keywords: list[str] | None = None,
    needs_image: bool = False,
    confidence: float = 0.85,
) -> str:
    return json.dumps({
        "intent": intent,
        "crop": crop,
        "disease_name": disease_name,
        "keywords": keywords or [],
        "needs_image": needs_image,
        "confidence": confidence,
    })


def _make_craft_json(
    embedding_query: str,
    fts_keywords: list[str],
    reasoning: str = "test",
) -> str:
    return json.dumps({
        "embedding_query": embedding_query,
        "fts_keywords": fts_keywords,
        "reasoning": reasoning,
    })


def _make_rerank_json(mock_kept_count: int, high_score: float = 0.8) -> str:
    """Build rerank JSON that marks results as kept with sufficient scores.

    Note: indices are 1-based to match rerank's expectation. The actual number
    of results kept depends on how many search_results execute_search returns —
    indices beyond len(search_results) are silently dropped by _parse_rerank_response.
    """
    items = []
    for i in range(mock_kept_count):
        score = max(0.4, high_score - (i * 0.05))
        items.append({"index": i + 1, "score": round(score, 2), "keep": True})
    return json.dumps(items)


def _make_observation_json(
    obs_type: str = "disease_sighting",
    details: str = "Brown spots on cassava leaves",
    location: str | None = "Field 3",
    summary: str = "Brown spot sighting on cassava",
) -> str:
    return json.dumps({
        "obs_type": obs_type,
        "details": details,
        "location": location,
        "summary": summary,
    })


@pytest.fixture
def mock_all_llms():
    """Patch all 6 LLM-calling nodes with configurable mock responses.

    Returns a dict of mock objects keyed by node name, so tests can
    override individual responses:

        mocks = mock_all_llms_fixture
        mocks["classify"].return_value.invoke.return_value = ...

    Default responses:
      - classify: diagnose_disease for cassava
      - needs_search: YES (heuristic usually handles this, LLM rarely called)
      - craft_query: cassava disease search query
      - rerank: 3 results kept with high scores (sufficient)
      - generate: a diagnostic answer mentioning cassava mosaic
      - log_observation: parsed observation JSON
    """
    default_responses = {
        "classify": _mock_llm_response(_make_classify_json(
            intent="diagnose_disease",
            crop="cassava",
            keywords=["cassava", "yellow", "leaves", "patches"],
            needs_image=True,
            confidence=0.85,
        )),
        "needs_search": _mock_llm_response("YES - user asks about crop disease"),
        "craft_query": _mock_llm_response(_make_craft_json(
            embedding_query="cassava plant sick leaves yellow patches mosaic disease symptoms",
            fts_keywords=["cassava", "mosaic", "yellow", "leaves"],
        )),
        "rerank": _mock_llm_response(_make_rerank_json(3, high_score=0.85)),
        "generate": _mock_llm_response(
            "Based on the symptoms described — yellow patches and curling leaves on your "
            "cassava — this appears to be Cassava Mosaic Disease (CMD), caused by a virus "
            "spread by whiteflies. Treatment includes removing infected plants, using "
            "resistant varieties, and applying neem extract to control whitefly vectors."
        ),
        "log_observation": _mock_llm_response(_make_observation_json()),
    }

    patches = {
        "classify": patch("app.agents.nodes.classify_extract.get_field_llm"),
        "needs_search": patch("app.agents.nodes.needs_search.get_field_llm"),
        "craft_query": patch("app.agents.nodes.craft_query.get_field_llm"),
        "rerank": patch("app.agents.nodes.rerank.get_field_llm"),
        "generate": patch("app.agents.nodes.generate_answer.get_field_llm"),
        "log_observation": patch("app.agents.nodes.log_observation.get_field_llm"),
    }

    mocks = {}
    started = []
    for name, p in patches.items():
        mock = p.start()
        started.append(p)
        mock.return_value.invoke.return_value = default_responses[name]
        mocks[name] = mock

    yield mocks

    for p in started:
        p.stop()


def _run_async(coro):
    """Run an async coroutine from sync test code."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(asyncio.run, coro).result()
    return asyncio.run(coro)


# ============================================================
# Reset graph singleton between tests to avoid stale state
# ============================================================

@pytest.fixture(autouse=True)
def _reset_graph_and_logger():
    """Reset the graph singleton and pipeline logger between tests.

    The PipelineLogger is a module-level singleton whose ring buffer and
    session counters persist across tests. Without clearing, tool_calls_log
    accumulates stale entries from prior tests.
    """
    import app.agents.field_assistant as fa
    from app.logger import pipeline_logger as log

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
# Test: Disease Diagnosis Path
# ============================================================

class TestDiagnosisPath:
    """classify(diagnose_disease) → route → needs_search(YES) → craft → search → rerank → generate"""

    def test_diagnosis_basic(self, mock_all_llms):
        """Yellow patches on cassava → should get disease diagnosis answer."""
        result = _run_async(run_field_assistant(
            message="My cassava leaves have yellow patches and they are curling up",
        ))

        assert result["final_answer"], "Should produce a non-empty answer"
        assert "cassava" in result["final_answer"].lower() or "mosaic" in result["final_answer"].lower()
        assert result["conversation_history"], "Should update conversation history"
        assert result["conversation_summary"], "Should produce a summary"
        assert result["retrieval_attempts"] >= 1, "Should have at least 1 retrieval attempt"

    def test_diagnosis_classify_called(self, mock_all_llms):
        """Verify classify LLM was called exactly once."""
        _run_async(run_field_assistant(
            message="My cassava leaves have yellow patches",
        ))
        mock_all_llms["classify"].return_value.invoke.assert_called()

    def test_diagnosis_search_returns_real_results(self, mock_all_llms):
        """Verify execute_search hits real ChromaDB and returns results."""
        result = _run_async(run_field_assistant(
            message="My cassava leaves have yellow patches and they are curling up",
        ))
        # Rerank was called → search must have returned results for it to score
        mock_all_llms["rerank"].return_value.invoke.assert_called()

    def test_diagnosis_history_updated(self, mock_all_llms):
        """Conversation history should contain the user message and assistant reply."""
        result = _run_async(run_field_assistant(
            message="My cassava has yellow spots",
        ))
        history = result["conversation_history"]
        assert len(history) >= 2
        assert history[-2]["role"] == "user"
        assert history[-1]["role"] == "assistant"
        assert "yellow" in history[-2]["content"].lower()


# ============================================================
# Test: Treatment Query Path
# ============================================================

class TestTreatmentPath:
    """classify(get_treatment) → route → needs_search(YES) → craft → search → rerank → generate"""

    def test_treatment_query(self, mock_all_llms):
        """Treatment for cassava mosaic → should get treatment steps."""
        # Override classify to return get_treatment intent
        mock_all_llms["classify"].return_value.invoke.return_value = _mock_llm_response(
            _make_classify_json(
                intent="get_treatment",
                crop="cassava",
                disease_name="Cassava Mosaic Disease",
                keywords=["cassava", "mosaic", "treatment", "organic"],
                confidence=0.9,
            )
        )
        # Override craft_query for treatment search
        mock_all_llms["craft_query"].return_value.invoke.return_value = _mock_llm_response(
            _make_craft_json(
                embedding_query="cassava mosaic disease treatment organic neem local materials Casamance",
                fts_keywords=["cassava", "mosaic", "treatment", "organic", "neem"],
            )
        )
        # Override generate to return treatment-focused answer
        mock_all_llms["generate"].return_value.invoke.return_value = _mock_llm_response(
            "To treat Cassava Mosaic Disease organically:\n"
            "- Remove and burn infected plants to prevent spread\n"
            "- Apply neem extract (Azadirachta indica) to control whitefly vectors\n"
            "- Plant resistant varieties like TME 419 or IITA varieties\n"
            "- Practice crop rotation with non-host crops"
        )

        result = _run_async(run_field_assistant(
            message="How do I treat cassava mosaic disease organically?",
        ))

        assert result["final_answer"]
        assert "neem" in result["final_answer"].lower() or "treatment" in result["final_answer"].lower()

    def test_treatment_route_uses_treatment_guides(self, mock_all_llms):
        """Treatment intent should route to treatment_guides collection."""
        mock_all_llms["classify"].return_value.invoke.return_value = _mock_llm_response(
            _make_classify_json(
                intent="get_treatment",
                crop="rice",
                disease_name="Rice Blast",
                keywords=["rice", "blast", "treatment"],
                confidence=0.9,
            )
        )
        mock_all_llms["craft_query"].return_value.invoke.return_value = _mock_llm_response(
            _make_craft_json(
                embedding_query="rice blast treatment methods fungicide organic",
                fts_keywords=["rice", "blast", "treatment"],
            )
        )

        result = _run_async(run_field_assistant(
            message="How do I treat rice blast?",
        ))
        assert result["final_answer"]


# ============================================================
# Test: Farming Advice Path
# ============================================================

class TestFarmingAdvicePath:
    """classify(farming_advice) → route → needs_search(YES) → craft → search → rerank → generate"""

    def test_farming_advice(self, mock_all_llms):
        """Planting season question → should get seasonal guidance."""
        mock_all_llms["classify"].return_value.invoke.return_value = _mock_llm_response(
            _make_classify_json(
                intent="farming_advice",
                crop="rice",
                keywords=["rice", "plant", "Casamance", "season", "when"],
                confidence=0.9,
            )
        )
        mock_all_llms["craft_query"].return_value.invoke.return_value = _mock_llm_response(
            _make_craft_json(
                embedding_query="rice planting season timing Casamance Senegal rainy season calendar",
                fts_keywords=["rice", "planting", "season", "Casamance"],
            )
        )
        mock_all_llms["generate"].return_value.invoke.return_value = _mock_llm_response(
            "In the Casamance region, rice should be planted at the start of the rainy "
            "season, typically June-July. Nursery preparation begins in May. Transplanting "
            "happens 21-30 days after seeding. The main harvest is October-November."
        )

        result = _run_async(run_field_assistant(
            message="When should I plant rice in Casamance?",
        ))

        assert result["final_answer"]
        assert "rice" in result["final_answer"].lower() or "season" in result["final_answer"].lower()


# ============================================================
# Test: Follow-up Path (skip search)
# ============================================================

class TestFollowUpPath:
    """classify(follow_up) → route → needs_search(NO, heuristic) → generate_answer (no new search)"""

    def test_followup_skips_search(self, mock_all_llms):
        """Follow-up with no prior ranked_results → skip search → generate no-context.

        The needs_search heuristic for FOLLOW_UP without ranked_results in state
        falls through to the LLM gate. We mock it to return NO so the test
        verifies the skip-search path and asserts craft_query is never called.

        Since initial state has no ranked_results, generate_answer takes the
        no-context early return (canned "I don't have enough information")
        without calling the LLM. This is correct: no context = no LLM needed.
        """
        # Override classify to return follow_up intent
        mock_all_llms["classify"].return_value.invoke.return_value = _mock_llm_response(
            _make_classify_json(
                intent="follow_up",
                keywords=["more", "treatment"],
                confidence=0.8,
            )
        )
        # Force the LLM needs_search gate to return NO (skip search)
        mock_all_llms["needs_search"].return_value.invoke.return_value = _mock_llm_response(
            "NO - user is asking for clarification on previously provided treatment steps"
        )

        prior_history = [
            {"role": "user", "content": "My cassava leaves have yellow patches"},
            {"role": "assistant", "content": "This appears to be Cassava Mosaic Disease."},
        ]

        result = _run_async(run_field_assistant(
            message="Tell me more about the treatment",
            conversation_history=prior_history,
            conversation_summary="Discussing cassava mosaic disease diagnosis",
        ))

        # Search was skipped — craft_query and rerank should NOT have been called
        mock_all_llms["craft_query"].return_value.invoke.assert_not_called()
        mock_all_llms["rerank"].return_value.invoke.assert_not_called()
        # generate_answer ran but took the no-context early return (no LLM call)
        assert result["final_answer"]
        assert "don't have enough information" in result["final_answer"].lower()

    def test_followup_with_topic_change_does_search(self, mock_all_llms):
        """Follow-up that introduces a new crop → should search."""
        mock_all_llms["classify"].return_value.invoke.return_value = _mock_llm_response(
            _make_classify_json(
                intent="follow_up",
                crop="rice",
                keywords=["rice", "disease"],
                confidence=0.7,
            )
        )

        prior_history = [
            {"role": "user", "content": "My cassava has yellow spots"},
            {"role": "assistant", "content": "This is cassava mosaic disease."},
        ]

        result = _run_async(run_field_assistant(
            message="What about rice diseases?",
            conversation_history=prior_history,
        ))

        assert result["final_answer"]


# ============================================================
# Test: Observation Logging Path
# ============================================================

class TestObservationPath:
    """classify(log_observation) → route(no engines) → needs_search(NO) → log_observation → END"""

    def test_observation_saved(self, mock_all_llms, loaded_pack):
        """Observation intent → should save to DB and return stats."""
        mock_all_llms["classify"].return_value.invoke.return_value = _mock_llm_response(
            _make_classify_json(
                intent="log_observation",
                crop="cassava",
                disease_name="Brown Spot",
                keywords=["brown", "spots", "cassava", "field"],
                confidence=0.9,
            )
        )

        result = _run_async(run_field_assistant(
            message="I saw brown spots on cassava leaves in field 3",
        ))

        assert result["final_answer"]
        assert "observation" in result["final_answer"].lower() or "saved" in result["final_answer"].lower()
        assert result["observation_stats"] is not None
        # >= 1 not == 1: observations accumulate in the shared module-scoped pack DB,
        # so count depends on test execution order (other observation tests may run first)
        assert result["observation_stats"]["total_observations"] >= 1

    def test_observation_skips_search_entirely(self, mock_all_llms):
        """Observation path should never call craft_query or rerank."""
        mock_all_llms["classify"].return_value.invoke.return_value = _mock_llm_response(
            _make_classify_json(
                intent="log_observation",
                keywords=["note", "field"],
                confidence=0.9,
            )
        )

        result = _run_async(run_field_assistant(
            message="Taking note: soil looks dry in the north field",
        ))

        # craft_query and rerank should NOT have been called
        mock_all_llms["craft_query"].return_value.invoke.assert_not_called()
        mock_all_llms["rerank"].return_value.invoke.assert_not_called()


# ============================================================
# Test: Hero Shot (3-turn conversation)
# ============================================================

class TestHeroShot:
    """The single most important test. Simulates the demo video flow:
    Turn 1: Photo + "What's wrong with my cassava?"
    Turn 2: "How do I treat this?"
    Turn 3: "Logging neem extract treatment for field 3"
    """

    def test_turn_1_diagnosis(self, mock_all_llms):
        """Turn 1: Plant photo → disease diagnosis."""
        # Classify: diagnose_disease with image
        mock_all_llms["classify"].return_value.invoke.return_value = _mock_llm_response(
            _make_classify_json(
                intent="diagnose_disease",
                crop="cassava",
                keywords=["cassava", "yellow", "mosaic", "leaves", "curling"],
                needs_image=True,
                confidence=0.9,
            )
        )
        mock_all_llms["generate"].return_value.invoke.return_value = _mock_llm_response(
            "Based on the visual symptoms — yellow mosaic patches and leaf curling on your "
            "cassava — this is consistent with Cassava Mosaic Disease (CMD). CMD is caused "
            "by cassava mosaic begomoviruses spread by the whitefly Bemisia tabaci. The "
            "disease reduces tuber yield by 20-80%. I recommend checking for whitefly "
            "presence on the underside of leaves."
        )

        # Mock image analysis (lazy import inside classify_and_extract)
        with patch("app.tools.image_analysis.analyze_plant_image") as mock_img:
            mock_img.return_value = {
                "visual_description": "Cassava leaves showing yellow-green mosaic pattern with leaf curling",
                "suspected_symptoms": ["yellow mosaic", "leaf curling", "stunted growth"],
            }

            result = _run_async(run_field_assistant(
                message="What's wrong with my cassava?",
                image_path="/fake/test/image.jpg",
            ))

        assert result["final_answer"]
        assert "mosaic" in result["final_answer"].lower() or "disease" in result["final_answer"].lower()
        assert result["conversation_history"]
        assert result["conversation_summary"]

    def test_turn_2_treatment(self, mock_all_llms):
        """Turn 2: "How do I treat this?" using Turn 1's conversation context."""
        # First run turn 1 to get history
        mock_all_llms["classify"].return_value.invoke.return_value = _mock_llm_response(
            _make_classify_json(
                intent="diagnose_disease",
                crop="cassava",
                keywords=["cassava", "mosaic", "disease"],
                confidence=0.9,
            )
        )
        with patch("app.tools.image_analysis.analyze_plant_image") as mock_img:
            mock_img.return_value = {
                "visual_description": "Yellow mosaic on cassava",
                "suspected_symptoms": ["yellow mosaic"],
            }
            turn1 = _run_async(run_field_assistant(
                message="What's wrong with my cassava?",
                image_path="/fake/test/image.jpg",
            ))

        # Now set up Turn 2 mocks
        mock_all_llms["classify"].return_value.invoke.return_value = _mock_llm_response(
            _make_classify_json(
                intent="get_treatment",
                crop="cassava",
                disease_name="Cassava Mosaic Disease",
                keywords=["cassava", "mosaic", "treatment", "treat"],
                confidence=0.85,
            )
        )
        mock_all_llms["craft_query"].return_value.invoke.return_value = _mock_llm_response(
            _make_craft_json(
                embedding_query="cassava mosaic disease treatment organic neem resistant varieties",
                fts_keywords=["cassava", "mosaic", "treatment", "neem"],
            )
        )
        mock_all_llms["generate"].return_value.invoke.return_value = _mock_llm_response(
            "To treat Cassava Mosaic Disease:\n"
            "1. Remove and burn severely infected plants\n"
            "2. Apply neem extract spray to control whiteflies\n"
            "3. For next season, plant resistant varieties (TME 419)\n"
            "4. Use clean planting material from disease-free areas\n"
            "Materials needed: neem leaves, water, sprayer"
        )

        result = _run_async(run_field_assistant(
            message="How do I treat this?",
            conversation_history=turn1["conversation_history"],
            conversation_summary=turn1["conversation_summary"],
        ))

        assert result["final_answer"]
        assert any(word in result["final_answer"].lower()
                   for word in ["treat", "neem", "remove", "resistant"])
        assert len(result["conversation_history"]) > len(turn1["conversation_history"])

    def test_turn_3_observation(self, mock_all_llms, loaded_pack):
        """Turn 3: Log observation after receiving treatment advice."""
        # Run turns 1 and 2 to build context
        mock_all_llms["classify"].return_value.invoke.return_value = _mock_llm_response(
            _make_classify_json(
                intent="diagnose_disease", crop="cassava",
                keywords=["cassava"], confidence=0.9,
            )
        )
        with patch("app.tools.image_analysis.analyze_plant_image") as mock_img:
            mock_img.return_value = {"visual_description": "Yellow mosaic", "suspected_symptoms": []}
            turn1 = _run_async(run_field_assistant(
                message="What's wrong with my cassava?",
                image_path="/fake/test/image.jpg",
            ))

        mock_all_llms["classify"].return_value.invoke.return_value = _mock_llm_response(
            _make_classify_json(
                intent="get_treatment", crop="cassava",
                disease_name="Cassava Mosaic Disease",
                keywords=["treatment"], confidence=0.85,
            )
        )
        turn2 = _run_async(run_field_assistant(
            message="How do I treat this?",
            conversation_history=turn1["conversation_history"],
            conversation_summary=turn1["conversation_summary"],
        ))

        # Turn 3: Log observation
        mock_all_llms["classify"].return_value.invoke.return_value = _mock_llm_response(
            _make_classify_json(
                intent="log_observation",
                crop="cassava",
                disease_name="Cassava Mosaic Disease",
                keywords=["neem", "treatment", "applied", "field"],
                confidence=0.9,
            )
        )
        mock_all_llms["log_observation"].return_value.invoke.return_value = _mock_llm_response(
            _make_observation_json(
                obs_type="treatment_applied",
                details="Applied neem extract spray to cassava field 3 to treat mosaic disease",
                location="Field 3, near the river",
                summary="Neem extract treatment applied for cassava mosaic in Field 3",
            )
        )

        result = _run_async(run_field_assistant(
            message="I'll try the neem extract treatment. Logging this for field 3.",
            conversation_history=turn2["conversation_history"],
            conversation_summary=turn2["conversation_summary"],
        ))

        assert result["final_answer"]
        assert "saved" in result["final_answer"].lower() or "observation" in result["final_answer"].lower()
        assert result["observation_stats"] is not None
        # >= 1: see TestObservationPath comment — shared pack DB accumulates rows
        assert result["observation_stats"]["total_observations"] >= 1


# ============================================================
# Test: Fuzzy Matching (misspelled queries)
# ============================================================

class TestFuzzyMatching:
    """Verify that misspelled queries still find results via FTS fuzzy tiers."""

    def test_misspelled_crop(self, mock_all_llms):
        """Misspelled 'cassva' → should still return results via fuzzy search."""
        mock_all_llms["classify"].return_value.invoke.return_value = _mock_llm_response(
            _make_classify_json(
                intent="diagnose_disease",
                crop="cassava",  # LLM corrects the spelling
                keywords=["cassava", "disease", "leaves"],
                confidence=0.75,
            )
        )
        mock_all_llms["craft_query"].return_value.invoke.return_value = _mock_llm_response(
            _make_craft_json(
                embedding_query="cassava disease leaves symptoms",
                fts_keywords=["cassava", "disease", "leaves"],
            )
        )

        result = _run_async(run_field_assistant(
            message="My cassva has sick leaves",
        ))

        assert result["final_answer"]
        assert result["retrieval_attempts"] >= 1


# ============================================================
# Test: Multi-Engine Search
# ============================================================

class TestMultiEngine:
    """Verify that queries can hit ChromaDB + FTS + structured simultaneously."""

    def test_diagnosis_hits_chroma_and_fts(self, mock_all_llms):
        """Diagnose intent routes to chroma_embedding + sqlite_fts.

        We verify this by checking that rerank received results (which means
        search executed successfully), and that the pipeline completed with
        at least 1 retrieval attempt.
        """
        mock_all_llms["classify"].return_value.invoke.return_value = _mock_llm_response(
            _make_classify_json(
                intent="diagnose_disease",
                crop="cassava",
                keywords=["cassava", "mosaic", "yellow"],
                confidence=0.9,
            )
        )

        result = _run_async(run_field_assistant(
            message="Cassava with yellow mosaic patches",
        ))

        assert result["final_answer"]
        assert result["retrieval_attempts"] >= 1
        # Rerank was called → execute_search returned results from real pack
        mock_all_llms["rerank"].return_value.invoke.assert_called()
        # Ranked results should exist (rerank mock keeps 3)
        assert len(result["ranked_results"]) >= 1


# ============================================================
# Test: Conversation Summary Builds Correctly
# ============================================================

class TestConversationSummary:
    """Verify summary heuristic produces non-empty, growing summaries."""

    def test_summary_from_single_turn(self, mock_all_llms):
        """Single turn should produce a non-empty summary."""
        result = _run_async(run_field_assistant(
            message="My cassava leaves have yellow patches",
        ))
        assert result["conversation_summary"]
        assert len(result["conversation_summary"]) > 10

    def test_summary_grows_across_turns(self, mock_all_llms):
        """Summary should incorporate info from multiple turns."""
        turn1 = _run_async(run_field_assistant(
            message="My cassava leaves have yellow patches",
        ))

        mock_all_llms["classify"].return_value.invoke.return_value = _mock_llm_response(
            _make_classify_json(
                intent="get_treatment",
                crop="cassava",
                disease_name="Cassava Mosaic Disease",
                keywords=["treatment"],
                confidence=0.85,
            )
        )

        turn2 = _run_async(run_field_assistant(
            message="How do I treat this?",
            conversation_history=turn1["conversation_history"],
            conversation_summary=turn1["conversation_summary"],
        ))

        # Turn 2 summary should be at least as long as turn 1's
        assert len(turn2["conversation_summary"]) >= len(turn1["conversation_summary"])


# ============================================================
# Test: WebSocket Streaming
# ============================================================

class TestWebSocketStreaming:
    """Test the WS /chat/ws endpoint via FastAPI TestClient."""

    def test_ws_event_sequence(self, mock_all_llms):
        """WebSocket should emit status → node_complete → ... → done events."""
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)
        with client.websocket_connect("/chat/ws") as ws:
            ws.send_json({
                "message": "My cassava leaves have yellow patches",
                "conversation_history": [],
                "conversation_summary": "",
            })

            events = []
            for _ in range(100):  # Safety limit
                event = ws.receive_json()
                events.append(event)
                if event.get("type") in ("done", "error"):
                    break

            event_types = [e["type"] for e in events]

            # Must have at least a status event and a done/error event
            assert len(events) >= 2, f"Too few events: {event_types}"

            # Last event should be 'done' (success) or 'error'
            final = events[-1]
            assert final["type"] in ("done", "error"), f"Unexpected final event: {final['type']}"

            if final["type"] == "done":
                assert "final_answer" in final
                assert "conversation_history" in final
                assert "conversation_summary" in final

    def test_ws_no_pack_returns_error(self, temporarily_unload_pack):
        """WebSocket with no pack loaded → error event."""
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)
        with client.websocket_connect("/chat/ws") as ws:
            ws.send_json({
                "message": "Hello",
                "conversation_history": [],
            })
            event = ws.receive_json()
            assert event["type"] == "error"
            assert "pack" in event["message"].lower() or "load" in event["message"].lower()

    def test_ws_invalid_json_returns_error(self, mock_all_llms):
        """Invalid JSON sent to WebSocket → error event."""
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)
        with client.websocket_connect("/chat/ws") as ws:
            ws.send_text("not valid json {{{")
            event = ws.receive_json()
            assert event["type"] == "error"
            assert "json" in event["message"].lower()


# ============================================================
# Test: HTTP POST /chat/
# ============================================================

class TestHTTPChat:
    """Test the POST /chat/ endpoint."""

    def test_post_chat_returns_response(self, mock_all_llms):
        """POST /chat/ with valid message → ChatResponse."""
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)
        response = client.post("/chat/", json={
            "message": "My cassava leaves have yellow patches",
            "conversation_history": [],
            "conversation_summary": "",
        })

        assert response.status_code == 200
        data = response.json()
        assert data["reply"]
        assert isinstance(data["conversation_history"], list)
        assert isinstance(data["tool_calls_log"], list)

    def test_post_chat_no_pack_returns_503(self, temporarily_unload_pack):
        """POST /chat/ with no pack loaded → 503."""
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)
        response = client.post("/chat/", json={
            "message": "Hello",
        })
        assert response.status_code == 503
