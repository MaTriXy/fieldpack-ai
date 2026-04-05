"""Image analysis tool for plant disease identification.

Uses Gemma E4B vision to extract visual symptoms from plant photos.
The tool describes what it sees — it does NOT diagnose. Diagnosis happens
when the pipeline cross-references symptoms against the knowledge base.

Output is structured for downstream matching: symptoms list, affected parts,
severity estimate, and a rich visual description using vocabulary that
matches our child chunk search targets.
"""

import base64
import io
from pathlib import Path

import httpx
from langchain_core.tools import tool
from PIL import Image

from app.config import settings
from app.logger import Step, pipeline_logger as log


# Supported image formats
_SUPPORTED_FORMATS = {".jpg", ".jpeg", ".png", ".webp"}

# Maximum dimension for resize (saves CPU inference time)
_MAX_IMAGE_DIM = 1024

# Symptom vocabulary hints — matches our child chunk keywords
_SYMPTOM_HINTS = (
    "yellow spots, yellow mosaic pattern, leaf curl, leaf rolling, wilting, "
    "brown spots, brown streaks, necrotic lesions, white powder, grey mold, "
    "stunted growth, deformed leaves, holes in leaves, discoloration, "
    "black rot, stem canker, root rot, fruit spots, bacterial ooze, "
    "ring spots, chlorosis, tip burn, vein clearing, leaf scorch"
)

# Vision analysis prompt — extracts maximum relevant info for later matching
_ANALYSIS_PROMPT = """You are a plant disease visual analyst working in Casamance, Senegal.
Examine this image of a plant carefully and extract as much relevant information as possible.

{crop_hint}

Describe everything you observe that could help identify a plant disease or condition.
Pay attention to:
- Leaf color changes (yellowing, browning, spots, patterns)
- Leaf shape changes (curling, rolling, wilting, deformation)
- Stem or root visible issues
- Any patterns (mosaic, streaks, rings, uniform vs patchy)
- Overall plant vigor and growth stage

Common symptoms to look for: {symptoms}

Output your analysis as JSON with these fields:
{{
  "visual_description": "Detailed paragraph describing everything visible that is relevant to plant health",
  "suspected_symptoms": ["symptom1", "symptom2", "symptom3"],
  "affected_parts": ["leaves", "stem", "roots", "fruit"],
  "severity_estimate": "mild or moderate or severe",
  "crop_guess": "crop name or unknown",
  "confidence": "low or medium or high"
}}

Only describe what is visible. Do not guess disease names. Focus on observable symptoms."""


def _resize_image(image_path: Path, max_dim: int = _MAX_IMAGE_DIM) -> bytes:
    """Resize an image to fit within max_dim, preserving aspect ratio.

    Returns the image as JPEG bytes.
    """
    with Image.open(image_path) as img:
        # Convert RGBA/palette to RGB for JPEG
        if img.mode in ("RGBA", "P", "LA"):
            img = img.convert("RGB")

        # Only resize if larger than max_dim
        if max(img.size) > max_dim:
            img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)

        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=85)
        return buffer.getvalue()


def _encode_image_base64(image_bytes: bytes) -> str:
    """Encode image bytes to base64 string."""
    return base64.b64encode(image_bytes).decode("utf-8")


def _build_analysis_prompt(crop_hint: str | None = None) -> str:
    """Build the vision analysis prompt with optional crop hint."""
    hint_text = ""
    if crop_hint:
        hint_text = f"The farmer says this is a {crop_hint} plant."

    return _ANALYSIS_PROMPT.format(
        crop_hint=hint_text,
        symptoms=_SYMPTOM_HINTS,
    )


def _parse_analysis_response(response_text: str) -> dict:
    """Parse the LLM's vision analysis response into a structured dict.

    Handles clean JSON, JSON in code blocks, and malformed responses.
    """
    import json
    import re

    # Try to extract JSON from code blocks first
    code_block = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", response_text, re.DOTALL)
    if code_block:
        try:
            return json.loads(code_block.group(1))
        except json.JSONDecodeError:
            pass

    # Try direct JSON parse
    json_match = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", response_text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

    # Fallback: return raw text as description with low confidence
    return {
        "visual_description": response_text.strip()[:500],
        "suspected_symptoms": [],
        "affected_parts": [],
        "severity_estimate": "unknown",
        "crop_guess": "unknown",
        "confidence": "low",
    }


def analyze_plant_image(
    image_path: str | Path,
    crop_hint: str | None = None,
) -> dict:
    """Analyze a plant image for disease symptoms using E4B vision.

    Resizes the image, sends it to E4B with a structured prompt,
    and returns parsed symptom analysis. Does NOT diagnose — only
    describes what is visible for downstream matching.

    Args:
        image_path: Path to the image file (jpg, png, webp).
        crop_hint: Optional hint from the user about which crop this is.

    Returns:
        Dict with keys: visual_description, suspected_symptoms,
        affected_parts, severity_estimate, crop_guess, confidence.
    """
    image_path = Path(image_path)

    # Validate file exists
    if not image_path.exists():
        log.log_step(Step.IMAGE_ANALYSIS, "file_not_found", level="ERROR",
                     details={"path": str(image_path)})
        raise FileNotFoundError(f"Image not found: {image_path}")

    # Validate format
    suffix = image_path.suffix.lower()
    if suffix not in _SUPPORTED_FORMATS:
        log.log_step(Step.IMAGE_ANALYSIS, "unsupported_format", level="ERROR",
                     details={"format": suffix, "supported": list(_SUPPORTED_FORMATS)})
        raise ValueError(f"Unsupported image format: {suffix}. Use: {_SUPPORTED_FORMATS}")

    with log.timed(Step.IMAGE_ANALYSIS, "analyze_image") as t:
        # Resize and encode
        try:
            image_bytes = _resize_image(image_path)
        except Exception as e:
            raise ValueError(f"Could not read image: {e}") from e
        image_b64 = _encode_image_base64(image_bytes)

        # Build prompt
        prompt = _build_analysis_prompt(crop_hint)

        # Call E4B vision via Ollama
        try:
            response = httpx.post(
                f"{settings.ollama_base_url}/api/generate",
                json={
                    "model": settings.ollama_model,
                    "prompt": prompt,
                    "images": [image_b64],
                    "stream": False,
                    "options": {"temperature": 0.3},
                },
                timeout=120.0,
            )
            response.raise_for_status()
            result_text = response.json().get("response", "")
        except Exception as e:
            log.log_step(Step.IMAGE_ANALYSIS, "ollama_error", level="ERROR",
                         details={"error": str(e)})
            return {
                "visual_description": f"Image analysis failed: {e}",
                "suspected_symptoms": [],
                "affected_parts": [],
                "severity_estimate": "unknown",
                "crop_guess": crop_hint or "unknown",
                "confidence": "low",
                "error": str(e),
            }

        # Parse response
        analysis = _parse_analysis_response(result_text)

        # Ensure all expected keys exist
        analysis.setdefault("visual_description", "")
        analysis.setdefault("suspected_symptoms", [])
        analysis.setdefault("affected_parts", [])
        analysis.setdefault("severity_estimate", "unknown")
        analysis.setdefault("crop_guess", crop_hint or "unknown")
        analysis.setdefault("confidence", "low")

        t.set(details={
            "image_path": str(image_path),
            "crop_hint": crop_hint,
            "resized_bytes": len(image_bytes),
            "symptoms_found": len(analysis["suspected_symptoms"]),
            "confidence": analysis["confidence"],
            "response_length": len(result_text),
        })

    log.log_step(Step.IMAGE_ANALYSIS, "analysis_complete", details={
        "image": image_path.name,
        "symptoms": analysis["suspected_symptoms"][:5],
        "severity": analysis["severity_estimate"],
        "confidence": analysis["confidence"],
    })

    return analysis


# ============================================================
# @tool wrapper for LangGraph
# ============================================================

@tool
def analyze_plant_image_tool(
    image_path: str,
    crop_hint: str = "",
) -> str:
    """Analyze a photo of a plant to identify visible symptoms.

    Upload a photo of a sick plant. The tool will describe what it sees:
    leaf discoloration, spots, wilting, and other visual symptoms.
    This information is then used to search the knowledge base for a diagnosis.

    Args:
        image_path: Path to the plant photo (jpg, png, or webp).
        crop_hint: Optional: what crop this is (e.g., "cassava", "rice").
    """
    hint = crop_hint if crop_hint and crop_hint.strip() else None

    try:
        analysis = analyze_plant_image(image_path, hint)
    except (FileNotFoundError, ValueError, OSError) as e:
        return f"Error: {e}"

    parts = [f"Visual description: {analysis['visual_description']}"]

    if analysis["suspected_symptoms"]:
        parts.append(f"Symptoms: {', '.join(analysis['suspected_symptoms'])}")
    if analysis["affected_parts"]:
        parts.append(f"Affected parts: {', '.join(analysis['affected_parts'])}")

    parts.append(f"Severity: {analysis['severity_estimate']}")
    parts.append(f"Crop: {analysis['crop_guess']}")
    parts.append(f"Confidence: {analysis['confidence']}")

    return "\n".join(parts)
