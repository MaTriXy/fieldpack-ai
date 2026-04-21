"""Tests for Step 5.1: CLASSIFY + EXTRACT node (LLM call #1)."""

import json
from unittest.mock import MagicMock, patch

import pytest

from app.agents.models import ClassifyExtractOutput, IntentType
from app.agents.nodes.classify_extract import (
    _build_classify_prompt,
    _parse_classify_response,
    classify_and_extract,
)


# ============================================================
# Unit: _parse_classify_response
# ============================================================

class TestParseClassifyResponse:

    def test_clean_json(self):
        data = {
            "intent": "diagnose_disease",
            "crop": "cassava",
            "disease_name": None,
            "keywords": ["cassava", "yellow", "leaves"],
            "needs_image": True,
            "confidence": 0.85,
        }
        result = _parse_classify_response(json.dumps(data))
        assert result.intent == IntentType.DIAGNOSE_DISEASE
        assert result.crop == "cassava"
        assert result.confidence == 0.85
        assert result.needs_image is True

    def test_json_in_code_block(self):
        text = '```json\n{"intent": "get_treatment", "crop": "rice", "confidence": 0.9}\n```'
        result = _parse_classify_response(text)
        assert result.intent == IntentType.GET_TREATMENT
        assert result.crop == "rice"

    def test_json_with_surrounding_text(self):
        text = 'Here is the classification:\n{"intent": "farming_advice", "crop": "maize", "confidence": 0.7}\nDone.'
        result = _parse_classify_response(text)
        assert result.intent == IntentType.FARMING_ADVICE
        assert result.crop == "maize"

    def test_malformed_json_fallback(self):
        text = "I think this is about cassava disease"
        result = _parse_classify_response(text)
        assert result.intent == IntentType.GENERAL_QUESTION
        assert result.confidence == 0.2

    def test_empty_response_fallback(self):
        result = _parse_classify_response("")
        assert result.intent == IntentType.GENERAL_QUESTION
        assert result.confidence == 0.2

    def test_partial_json_fills_defaults(self):
        text = '{"intent": "diagnose_disease"}'
        result = _parse_classify_response(text)
        assert result.intent == IntentType.DIAGNOSE_DISEASE
        assert result.crop is None
        assert result.keywords == []
        assert result.confidence == 0.5  # default

    def test_invalid_intent_fallback(self):
        text = '{"intent": "invalid_intent_value", "confidence": 0.5}'
        result = _parse_classify_response(text)
        # Pydantic validation fails → falls to regex → fails → defaults
        assert result.intent == IntentType.GENERAL_QUESTION

    def test_all_intents_parseable(self):
        for intent in IntentType:
            text = json.dumps({"intent": intent.value, "confidence": 0.8})
            result = _parse_classify_response(text)
            assert result.intent == intent

    def test_null_fields_handled(self):
        text = '{"intent": "diagnose_disease", "crop": null, "disease_name": null}'
        result = _parse_classify_response(text)
        assert result.crop is None
        assert result.disease_name is None


# ============================================================
# Unit: _build_classify_prompt
# ============================================================

class TestBuildClassifyPrompt:

    def test_basic_prompt_structure(self):
        messages = _build_classify_prompt("My cassava is sick", None, [])
        # System prompt + 2 few-shot pairs (2 Human + 2 AI) + final user message = 6
        assert len(messages) == 6
        assert "Classify an agricultural field question" in messages[0].content

    def test_includes_few_shot_examples(self):
        messages = _build_classify_prompt("test", None, [])
        all_text = " ".join(m.content for m in messages)
        assert "yellow patches" in all_text  # example 1
        assert "rice blast" in all_text  # example 2

    def test_includes_image_description(self):
        messages = _build_classify_prompt(
            "What's wrong with this plant?",
            "Yellow mosaic pattern on leaves, moderate severity",
            [],
        )
        last_msg = messages[-1].content
        assert "Yellow mosaic pattern" in last_msg
        assert "Image analysis" in last_msg

    def test_includes_conversation_history(self):
        history = [
            {"role": "user", "content": "My cassava has yellow leaves"},
            {"role": "assistant", "content": "That sounds like it could be CMD."},
        ]
        messages = _build_classify_prompt("What about treatment?", None, history)
        all_text = " ".join(m.content for m in messages)
        assert "CMD" in all_text
        assert "Recent conversation" in all_text

    def test_history_capped_at_2(self):
        history = [
            {"role": "user", "content": "msg1"},
            {"role": "assistant", "content": "resp1"},
            {"role": "user", "content": "msg2"},
            {"role": "assistant", "content": "resp2"},
            {"role": "user", "content": "msg3"},
        ]
        messages = _build_classify_prompt("test", None, history)
        # Should only include last 2 messages
        all_text = " ".join(m.content for m in messages)
        assert "msg3" in all_text or "resp2" in all_text
        # msg1 should NOT be in the history context
        # (it's in the few-shot portion which is separate)

    def test_no_history_no_context_message(self):
        messages = _build_classify_prompt("test", None, [])
        # No "Recent conversation" section when history is empty
        all_text = " ".join(m.content for m in messages)
        assert "Recent conversation" not in all_text


# ============================================================
# Integration: classify_and_extract (mocked LLM)
# ============================================================

class TestClassifyAndExtract:

    def _make_state(self, message="My cassava has yellow leaves", image_path=None, history=None):
        return {
            "user_message": message,
            "image_path": image_path,
            "conversation_history": history or [],
        }

    def test_basic_classification(self):
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "intent": "diagnose_disease",
            "crop": "cassava",
            "keywords": ["cassava", "yellow", "leaves"],
            "confidence": 0.85,
        })

        with patch("app.agents.nodes.classify_extract.get_field_llm") as mock_llm:
            mock_llm.return_value.invoke.return_value = mock_response
            result = classify_and_extract(self._make_state())

        assert "classify_result" in result
        assert result["classify_result"].intent == IntentType.DIAGNOSE_DISEASE
        assert result["classify_result"].crop == "cassava"

    def test_with_image_path(self):
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "intent": "identify_image",
            "crop": "cassava",
            "confidence": 0.8,
        })

        mock_analysis = {
            "visual_description": "Yellow mosaic on leaves",
            "suspected_symptoms": ["yellow mosaic", "leaf curl"],
        }

        with patch("app.agents.nodes.classify_extract.get_field_llm") as mock_llm, \
             patch("app.tools.image_analysis.analyze_plant_image",
                   return_value=mock_analysis):
            mock_llm.return_value.invoke.return_value = mock_response
            result = classify_and_extract(
                self._make_state(image_path="/photo/plant.jpg"),
            )

        assert result["classify_result"].intent == IntentType.IDENTIFY_IMAGE

    def test_llm_error_returns_safe_defaults(self):
        with patch("app.agents.nodes.classify_extract.get_field_llm") as mock_llm:
            mock_llm.return_value.invoke.side_effect = Exception("Connection refused")
            result = classify_and_extract(self._make_state())

        assert result["classify_result"].intent == IntentType.GENERAL_QUESTION
        assert result["classify_result"].confidence == 0.1
        assert "error" in result

    def test_malformed_llm_response(self):
        mock_response = MagicMock()
        mock_response.content = "I don't understand the format"

        with patch("app.agents.nodes.classify_extract.get_field_llm") as mock_llm:
            mock_llm.return_value.invoke.return_value = mock_response
            result = classify_and_extract(self._make_state())

        assert result["classify_result"].intent == IntentType.GENERAL_QUESTION
        assert result["classify_result"].confidence == 0.2

    def test_result_is_pydantic_model(self):
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "intent": "get_treatment",
            "crop": "rice",
            "disease_name": "Rice Blast",
            "keywords": ["rice", "blast"],
            "confidence": 0.9,
        })

        with patch("app.agents.nodes.classify_extract.get_field_llm") as mock_llm:
            mock_llm.return_value.invoke.return_value = mock_response
            result = classify_and_extract(self._make_state("How to treat rice blast?"))

        assert isinstance(result["classify_result"], ClassifyExtractOutput)
        assert result["classify_result"].disease_name == "Rice Blast"

    def test_image_analysis_failure_continues(self):
        """If image analysis fails, classification still proceeds."""
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "intent": "identify_image",
            "confidence": 0.6,
        })

        with patch("app.agents.nodes.classify_extract.get_field_llm") as mock_llm, \
             patch("app.tools.image_analysis.analyze_plant_image",
                   side_effect=FileNotFoundError("Image not found")):
            mock_llm.return_value.invoke.return_value = mock_response
            result = classify_and_extract(
                self._make_state(image_path="/bad/path.jpg"),
            )

        # Should still classify, just without image description
        assert "classify_result" in result
        assert "error" not in result  # image failure is a warning, not an error

    def test_follow_up_with_history(self):
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "intent": "get_treatment",
            "crop": "cassava",
            "disease_name": "Cassava Mosaic Disease",
            "keywords": ["treatment", "cassava", "mosaic"],
            "confidence": 0.75,
        })

        history = [
            {"role": "user", "content": "My cassava has yellow mosaic leaves"},
            {"role": "assistant", "content": "That looks like Cassava Mosaic Disease."},
        ]

        with patch("app.agents.nodes.classify_extract.get_field_llm") as mock_llm:
            mock_llm.return_value.invoke.return_value = mock_response
            result = classify_and_extract(
                self._make_state("What about treatment?", history=history),
            )

        # Follow-up resolved to actual intent
        assert result["classify_result"].intent == IntentType.GET_TREATMENT


# ============================================================
# Unit: ask-back short-circuit
# ============================================================

class _FakeManifest:
    def __init__(self, crops):
        self.crops = crops


class _FakePack:
    def __init__(self, crops):
        self.manifest = _FakeManifest(crops)


class TestAskBackShortCircuit:
    """The prior assistant turn asked for a crop — current reply should
    skip the LLM classify when it resolves to a pack crop.
    """

    from app.agents.nodes.classify_extract import ASK_BACK_SENTINEL as _SENTINEL

    def _state(self, message, history):
        return {
            "user_message": message,
            "image_path": None,
            "conversation_history": history,
        }

    def _ask_back_history(self):
        return [
            {"role": "user", "content": "what's wrong with my plant"},
            {"role": "assistant",
             "content": f"{self._SENTINEL}, but I'm not sure which crop this is. "
                        "Could you tell me the crop name?"},
        ]

    def test_short_crop_reply_skips_llm(self):
        pack = _FakePack(["cassava", "rice", "maize"])
        with patch("app.agents.nodes.classify_extract.get_field_llm") as mock_llm, \
             patch("app.knowledge_pack.loader.get_active_pack", return_value=pack):
            result = classify_and_extract(self._state("cassava", self._ask_back_history()))

        # LLM must not have been consulted
        mock_llm.assert_not_called()
        assert result["classify_result"].crop == "cassava"
        assert result["classify_result"].intent == IntentType.DIAGNOSE_DISEASE
        assert result["image_description"] is None

    def test_phrased_crop_reply_also_resolves(self):
        pack = _FakePack(["cassava", "rice"])
        with patch("app.agents.nodes.classify_extract.get_field_llm") as mock_llm, \
             patch("app.knowledge_pack.loader.get_active_pack", return_value=pack):
            result = classify_and_extract(
                self._state("it's rice", self._ask_back_history()),
            )

        mock_llm.assert_not_called()
        assert result["classify_result"].crop == "rice"

    def test_long_reply_does_not_short_circuit(self):
        # A long reply is a new question, not a crop follow-up — LLM must run.
        pack = _FakePack(["cassava"])
        long_msg = (
            "Actually forget the photo, I have a different question about "
            "how to fertilize my cassava field in the dry season"
        )
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "intent": "farming_advice", "crop": "cassava",
            "keywords": ["fertilize", "cassava"], "confidence": 0.7,
        })
        with patch("app.agents.nodes.classify_extract.get_field_llm") as mock_llm, \
             patch("app.knowledge_pack.loader.get_active_pack", return_value=pack):
            mock_llm.return_value.invoke.return_value = mock_response
            classify_and_extract(self._state(long_msg, self._ask_back_history()))

        mock_llm.assert_called_once()

    def test_unknown_crop_reply_falls_through_to_llm(self):
        # User replies with a crop not in the pack — can't short-circuit, LLM runs.
        pack = _FakePack(["cassava", "rice"])
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "intent": "diagnose_disease", "crop": None,
            "keywords": ["potato"], "confidence": 0.4,
        })
        with patch("app.agents.nodes.classify_extract.get_field_llm") as mock_llm, \
             patch("app.knowledge_pack.loader.get_active_pack", return_value=pack):
            mock_llm.return_value.invoke.return_value = mock_response
            classify_and_extract(self._state("potato", self._ask_back_history()))

        mock_llm.assert_called_once()

    def test_no_ask_back_in_history_does_not_short_circuit(self):
        # Plain first-turn user message, same content — should NOT skip LLM.
        pack = _FakePack(["cassava"])
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "intent": "general_question", "crop": "cassava",
            "keywords": ["cassava"], "confidence": 0.5,
        })
        with patch("app.agents.nodes.classify_extract.get_field_llm") as mock_llm, \
             patch("app.knowledge_pack.loader.get_active_pack", return_value=pack):
            mock_llm.return_value.invoke.return_value = mock_response
            classify_and_extract(self._state("cassava", history=[]))

        mock_llm.assert_called_once()

    def test_longest_crop_wins_when_both_are_substrings(self):
        # Pack has both "rice" and "upland_rice"; reply "upland rice" must
        # resolve to the specific variety, not the generic one.
        pack = _FakePack(["rice", "upland_rice"])
        with patch("app.agents.nodes.classify_extract.get_field_llm") as mock_llm, \
             patch("app.knowledge_pack.loader.get_active_pack", return_value=pack):
            result = classify_and_extract(
                self._state("upland rice", self._ask_back_history()),
            )

        mock_llm.assert_not_called()
        assert result["classify_result"].crop == "upland_rice"

    def test_word_boundary_prevents_spurious_substring_hit(self):
        # "pricey" contains the substring "rice" but shouldn't match the crop.
        pack = _FakePack(["rice"])
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "intent": "general_question", "crop": None,
            "keywords": [], "confidence": 0.3,
        })
        with patch("app.agents.nodes.classify_extract.get_field_llm") as mock_llm, \
             patch("app.knowledge_pack.loader.get_active_pack", return_value=pack):
            mock_llm.return_value.invoke.return_value = mock_response
            classify_and_extract(self._state("pricey", self._ask_back_history()))

        # No short-circuit — LLM must run (and return no crop).
        mock_llm.assert_called_once()

    def test_short_circuit_returns_needs_search_true(self):
        # Explicit flag so downstream routing doesn't rely on a missing-key default.
        pack = _FakePack(["cassava"])
        with patch("app.agents.nodes.classify_extract.get_field_llm"), \
             patch("app.knowledge_pack.loader.get_active_pack", return_value=pack):
            result = classify_and_extract(
                self._state("cassava", self._ask_back_history()),
            )

        assert result.get("needs_search") is True
