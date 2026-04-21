"""Image analysis tool for plant disease identification.

Uses Gemma E2B vision to extract visual symptoms from plant photos.
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
from app.models.offline_llm import get_resolved_provider


# Supported image formats
_SUPPORTED_FORMATS = {".jpg", ".jpeg", ".png", ".webp"}

# Maximum dimension for resize (saves CPU inference time)
_MAX_IMAGE_DIM = 1024

# Maximum file size (20 MB) to prevent OOM on edge devices
_MAX_FILE_SIZE = 20 * 1024 * 1024

# Symptom vocabulary hints — matches our child chunk keywords
_SYMPTOM_HINTS = (
    "yellow spots, yellow mosaic pattern, leaf curl, leaf rolling, wilting, "
    "brown spots, brown streaks, necrotic lesions, white powder, grey mold, "
    "stunted growth, deformed leaves, holes in leaves, discoloration, "
    "black rot, stem canker, root rot, fruit spots, bacterial ooze, "
    "ring spots, chlorosis, tip burn, vein clearing, leaf scorch"
)

# Vision analysis prompt — extracts maximum relevant info for later matching
_ANALYSIS_PROMPT = """Analyze this plant image for disease symptoms.
{crop_hint}
First, identify the crop from its leaf shape and growth pattern.

Then describe visible disease symptoms:
- Leaf color changes (yellowing, browning, spots, mosaic patterns)
- Leaf shape changes (curling, rolling, wilting, deformation)
- Stem, root, or fruit issues
- Patterns (mosaic, streaks, rings, uniform vs patchy)

Common symptoms: {symptoms}

Output JSON:
{{
  "visual_description": "Detailed description of visible symptoms",
  "suspected_symptoms": ["symptom1", "symptom2"],
  "affected_parts": ["leaves", "stem", "roots", "fruit"],
  "severity_estimate": "mild or moderate or severe",
  "crop_guess": "crop name or unknown",
  "confidence": "low or medium or high"
}}
Do not guess disease names. Focus on observable symptoms."""


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


def _call_ollama_vision(prompt: str, image_b64: str, resolved: str = "") -> str:
    """Send image to Ollama vision API."""
    if not resolved:
        resolved = get_resolved_provider()
    base_url = settings.ollama_base_url

    headers = {}
    if settings.ollama_tunnel_token and resolved != "local":
        headers["Authorization"] = f"Bearer {settings.ollama_tunnel_token}"
    # Build options — apply CPU-only fix for Intel iGPU (prevents garbage output)
    options = {
        "temperature": 0.3,
        "num_predict": 512,
        "num_ctx": settings.ollama_num_ctx,
    }
    is_local = not (settings.ollama_tunnel_token and resolved != "local")
    if is_local and settings.ollama_num_gpu >= 0:
        options["num_gpu"] = settings.ollama_num_gpu

    response = httpx.post(
        f"{base_url}/api/generate",
        headers=headers,
        json={
            "model": settings.ollama_model,
            "prompt": prompt,
            "images": [image_b64],
            "stream": False,
            "think": False,
            "options": options,
        },
        timeout=120.0,
    )
    response.raise_for_status()
    data = response.json()
    text = data.get("response", "")

    # Extract Ollama eval metrics for performance display (Ollama-specific fields)
    eval_count = data.get("eval_count", 0)
    eval_duration = data.get("eval_duration", 0)  # nanoseconds
    if eval_count > 0 and eval_duration > 0:
        tok_per_sec = round(eval_count / (eval_duration / 1e9), 1)
        log.log_step(Step.IMAGE_ANALYSIS, "ollama_vision_metrics", details={
            "eval_count": eval_count,
            "eval_duration_ms": round(eval_duration / 1e6),
            "tok_per_sec": tok_per_sec,
            "model": settings.ollama_model,
        })

    return text


def _call_google_vision(prompt: str, image_bytes: bytes) -> str:
    """Send image to Google AI Studio via LangChain multimodal message.

    Uses the same ChatGoogleGenerativeAI path as all other pipeline nodes,
    sending the image as an inline base64 part in a HumanMessage.
    This ensures the hero shot is a real LLM vision call, not a separate API.
    """
    from langchain_core.messages import HumanMessage
    from app.models.offline_llm import get_field_llm

    image_b64 = base64.b64encode(image_bytes).decode("utf-8")
    llm = get_field_llm(temperature=0.3, num_predict=512)
    message = HumanMessage(
        content=[
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
            {"type": "text", "text": prompt},
        ],
    )
    response = llm.invoke([message])
    from app.agents.models import extract_text
    return extract_text(response)


def analyze_plant_image(
    image_path: str | Path,
    crop_hint: str | None = None,
) -> dict:
    """Analyze a plant image for disease symptoms using E2B vision.

    Resizes the image, sends it to E2B with a structured prompt,
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

    # Validate file size
    file_size = image_path.stat().st_size
    if file_size > _MAX_FILE_SIZE:
        log.log_step(Step.IMAGE_ANALYSIS, "file_too_large", level="ERROR",
                     details={"size_mb": round(file_size / 1024 / 1024, 1), "max_mb": 20})
        raise ValueError(f"Image too large ({file_size // 1024 // 1024}MB). Max: 20MB.")

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

        # Call vision model via configured/resolved provider
        try:
            resolved = get_resolved_provider()
            if settings.field_llm_provider == "google" or resolved == "google":
                result_text = _call_google_vision(prompt, image_bytes)
            else:
                result_text = _call_ollama_vision(prompt, image_b64, resolved=resolved)
        except Exception as e:
            log.log_step(Step.IMAGE_ANALYSIS, "vision_error", level="ERROR",
                         details={"error": str(e), "provider": resolved})
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
