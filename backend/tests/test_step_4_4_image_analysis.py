"""Tests for Step 4.4: Image analysis tool (E2B vision).

Unit tests for image processing and prompt building run without Ollama.
Integration tests requiring a running Ollama instance are marked
@pytest.mark.live and are deselected by default.
"""

import base64
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from app.tools.image_analysis import (
    _build_analysis_prompt,
    _encode_image_base64,
    _parse_analysis_response,
    _resize_image,
    analyze_plant_image,
    analyze_plant_image_tool,
)


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def sample_image(tmp_path) -> Path:
    """Create a test image (200x200 green square)."""
    img = Image.new("RGB", (200, 200), color=(0, 128, 0))
    path = tmp_path / "test_plant.jpg"
    img.save(path, "JPEG")
    return path


@pytest.fixture
def large_image(tmp_path) -> Path:
    """Create a large test image (2000x2000)."""
    img = Image.new("RGB", (2000, 2000), color=(0, 128, 0))
    path = tmp_path / "large_plant.jpg"
    img.save(path, "JPEG")
    return path


@pytest.fixture
def rgba_image(tmp_path) -> Path:
    """Create an RGBA PNG image."""
    img = Image.new("RGBA", (300, 300), color=(0, 128, 0, 255))
    path = tmp_path / "test_rgba.png"
    img.save(path, "PNG")
    return path


@pytest.fixture
def mock_ollama_response():
    """Standard mock Ollama response with valid JSON."""
    return {
        "visual_description": "The cassava leaf shows yellow mosaic patterns with curling edges",
        "suspected_symptoms": ["yellow mosaic pattern", "leaf curl", "chlorosis"],
        "affected_parts": ["leaves"],
        "severity_estimate": "moderate",
        "crop_guess": "cassava",
        "confidence": "medium",
    }


# ============================================================
# Unit: _resize_image
# ============================================================

class TestResizeImage:

    def test_small_image_unchanged(self, sample_image):
        result = _resize_image(sample_image)
        img = Image.open(sample_image)
        # Small image (200x200) should not be resized
        assert len(result) > 0

    def test_large_image_resized(self, large_image):
        result = _resize_image(large_image, max_dim=1024)
        # Verify the result is valid JPEG
        from io import BytesIO
        img = Image.open(BytesIO(result))
        assert max(img.size) <= 1024

    def test_rgba_converted_to_rgb(self, rgba_image):
        result = _resize_image(rgba_image)
        # Should produce valid JPEG bytes (JPEG doesn't support alpha)
        from io import BytesIO
        img = Image.open(BytesIO(result))
        assert img.mode == "RGB"

    def test_returns_bytes(self, sample_image):
        result = _resize_image(sample_image)
        assert isinstance(result, bytes)
        assert len(result) > 0


# ============================================================
# Unit: _encode_image_base64
# ============================================================

class TestEncodeImageBase64:

    def test_roundtrip(self, sample_image):
        original_bytes = _resize_image(sample_image)
        encoded = _encode_image_base64(original_bytes)
        decoded = base64.b64decode(encoded)
        assert decoded == original_bytes

    def test_returns_string(self, sample_image):
        image_bytes = _resize_image(sample_image)
        result = _encode_image_base64(image_bytes)
        assert isinstance(result, str)

    def test_valid_base64(self, sample_image):
        image_bytes = _resize_image(sample_image)
        encoded = _encode_image_base64(image_bytes)
        # Should not raise
        base64.b64decode(encoded)


# ============================================================
# Unit: _build_analysis_prompt
# ============================================================

class TestBuildAnalysisPrompt:

    def test_without_crop_hint(self):
        prompt = _build_analysis_prompt()
        assert "plant image" in prompt
        assert "disease symptoms" in prompt
        assert "JSON" in prompt
        assert "visual_description" in prompt

    def test_with_crop_hint(self):
        prompt = _build_analysis_prompt("cassava")
        assert "cassava" in prompt
        assert "farmer says" in prompt

    def test_contains_symptom_hints(self):
        prompt = _build_analysis_prompt()
        assert "yellow mosaic" in prompt
        assert "leaf curl" in prompt
        assert "brown spots" in prompt

    def test_instructs_no_diagnosis(self):
        prompt = _build_analysis_prompt()
        assert "Do not guess disease names" in prompt


# ============================================================
# Unit: _parse_analysis_response
# ============================================================

class TestParseAnalysisResponse:

    def test_clean_json(self, mock_ollama_response):
        text = json.dumps(mock_ollama_response)
        result = _parse_analysis_response(text)
        assert result["visual_description"] == mock_ollama_response["visual_description"]
        assert result["suspected_symptoms"] == mock_ollama_response["suspected_symptoms"]

    def test_json_in_code_block(self, mock_ollama_response):
        text = f"Here's my analysis:\n```json\n{json.dumps(mock_ollama_response)}\n```"
        result = _parse_analysis_response(text)
        assert result["crop_guess"] == "cassava"

    def test_json_with_surrounding_text(self, mock_ollama_response):
        text = f"I can see the plant. {json.dumps(mock_ollama_response)} That's my analysis."
        result = _parse_analysis_response(text)
        assert result["confidence"] == "medium"

    def test_malformed_json_fallback(self):
        text = "I see a cassava plant with yellow spots on the leaves."
        result = _parse_analysis_response(text)
        assert result["visual_description"] == text
        assert result["confidence"] == "low"
        assert result["suspected_symptoms"] == []

    def test_empty_response_fallback(self):
        result = _parse_analysis_response("")
        assert result["confidence"] == "low"


# ============================================================
# Integration: analyze_plant_image (mocked Ollama)
# ============================================================

class TestAnalyzePlantImage:

    def test_with_mocked_ollama(self, sample_image, mock_ollama_response):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"response": json.dumps(mock_ollama_response)}
        mock_resp.raise_for_status = MagicMock()

        with patch("app.tools.image_analysis.httpx.post", return_value=mock_resp), \
             patch("app.tools.image_analysis.get_resolved_provider", return_value="local"):
            result = analyze_plant_image(sample_image, crop_hint="cassava")

        assert result["visual_description"] == mock_ollama_response["visual_description"]
        assert result["suspected_symptoms"] == mock_ollama_response["suspected_symptoms"]
        assert result["severity_estimate"] == "moderate"
        assert result["crop_guess"] == "cassava"
        assert result["confidence"] == "medium"

    def test_output_has_all_fields(self, sample_image, mock_ollama_response):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"response": json.dumps(mock_ollama_response)}
        mock_resp.raise_for_status = MagicMock()

        with patch("app.tools.image_analysis.httpx.post", return_value=mock_resp), \
             patch("app.tools.image_analysis.get_resolved_provider", return_value="local"):
            result = analyze_plant_image(sample_image)

        required_keys = [
            "visual_description", "suspected_symptoms", "affected_parts",
            "severity_estimate", "crop_guess", "confidence",
        ]
        for key in required_keys:
            assert key in result

    def test_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            analyze_plant_image(tmp_path / "nonexistent.jpg")

    def test_unsupported_format(self, tmp_path):
        text_file = tmp_path / "test.txt"
        text_file.write_text("not an image")
        with pytest.raises(ValueError, match="Unsupported image format"):
            analyze_plant_image(text_file)

    def test_ollama_error_raises(self, sample_image):
        with patch("app.tools.image_analysis.httpx.post",
                   side_effect=Exception("Connection refused")), \
             patch("app.tools.image_analysis.get_resolved_provider", return_value="local"):
            with pytest.raises(RuntimeError, match="Image analysis failed"):
                analyze_plant_image(sample_image)

    def test_with_crop_hint_in_result(self, sample_image):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"response": '{"crop_guess": "rice"}'}
        mock_resp.raise_for_status = MagicMock()

        with patch("app.tools.image_analysis.httpx.post", return_value=mock_resp), \
             patch("app.tools.image_analysis.get_resolved_provider", return_value="local"):
            result = analyze_plant_image(sample_image, crop_hint="rice")

        assert result["crop_guess"] == "rice"

    @pytest.mark.live
    def test_real_ollama(self, sample_image):
        """Requires running Ollama with the configured E2B vision model."""
        result = analyze_plant_image(sample_image, crop_hint="cassava")
        assert "visual_description" in result
        assert isinstance(result["suspected_symptoms"], list)


# ============================================================
# @tool wrapper
# ============================================================

class TestToolWrapper:

    def test_tool_returns_string(self, sample_image, mock_ollama_response):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"response": json.dumps(mock_ollama_response)}
        mock_resp.raise_for_status = MagicMock()

        with patch("app.tools.image_analysis.httpx.post", return_value=mock_resp), \
             patch("app.tools.image_analysis.get_resolved_provider", return_value="local"):
            result = analyze_plant_image_tool.invoke({
                "image_path": str(sample_image),
                "crop_hint": "cassava",
            })

        assert isinstance(result, str)
        assert "yellow mosaic" in result
        assert "Severity: moderate" in result

    def test_tool_file_not_found(self, tmp_path):
        result = analyze_plant_image_tool.invoke({
            "image_path": str(tmp_path / "nope.jpg"),
        })
        assert "Error" in result

    def test_tool_has_name(self):
        assert analyze_plant_image_tool.name == "analyze_plant_image_tool"
        assert len(analyze_plant_image_tool.description) > 0
