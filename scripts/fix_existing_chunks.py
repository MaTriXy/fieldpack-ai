"""Rewrite existing ChromaDB chunks from structured format to clean natural language.

Reads all parent+child chunks, applies string transformations to convert
structured labels into flowing NL paragraphs, then updates in-place.
ChromaDB re-embeds automatically when embedding_function is set.
"""
import re
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

CHROMA_PATH = "packs/casamance_agriculture/chroma_db"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"


def _fix_encoding(text: str) -> str:
    """Fix common encoding artifacts."""
    return text.replace("\ufffd", "\u2014").replace("\u00e2\u0080\u0094", "\u2014").replace("\u00e2\u0080\u0093", "\u2013")


def _json_array_to_text(text: str) -> str:
    """Convert JSON array strings like '["item1", "item2"]' to 'item1, and item2'."""
    import json as _json

    def _replace_array(match):
        try:
            items = _json.loads(match.group(0))
            if isinstance(items, list):
                items = [str(i) for i in items]
                if len(items) == 1:
                    return items[0]
                elif len(items) == 2:
                    return f"{items[0]} and {items[1]}"
                else:
                    return ", ".join(items[:-1]) + f", and {items[-1]}"
        except Exception:
            pass
        return match.group(0)

    return re.sub(r'\["[^"]+(?:",\s*"[^"]+)*"\]', _replace_array, text)


def _rewrite_disease_parent(doc: str, meta: dict) -> str:
    """Rewrite a disease parent chunk from structured to NL."""
    disease_name = meta.get("disease_name", "")
    severity = meta.get("severity", "")
    dtype = meta.get("type", "")
    crop = meta.get("crop", "")

    doc = _fix_encoding(doc)
    doc = _json_array_to_text(doc)

    # Parse sections from structured format
    sections = {}
    current_section = "intro"
    current_lines = []

    for line in doc.split("\n"):
        line = line.strip()
        if not line:
            continue
        # Detect section headers
        lower = line.lower()
        if lower.startswith("symptoms:"):
            sections[current_section] = " ".join(current_lines)
            current_section = "symptoms"
            remainder = line.split(":", 1)[1].strip()
            current_lines = [remainder] if remainder else []
        elif lower.startswith("visual identification:"):
            sections[current_section] = " ".join(current_lines)
            current_section = "visual"
            remainder = line.split(":", 1)[1].strip()
            current_lines = [remainder] if remainder else []
        elif lower.startswith("how it spreads:"):
            sections[current_section] = " ".join(current_lines)
            current_section = "spreads"
            remainder = line.split(":", 1)[1].strip()
            current_lines = [remainder] if remainder else []
        elif lower.startswith("prevention:") or lower.startswith("how to prevent:"):
            sections[current_section] = " ".join(current_lines)
            current_section = "prevention"
            remainder = line.split(":", 1)[1].strip()
            current_lines = [remainder] if remainder else []
        else:
            # Skip header lines that are just metadata
            if line == disease_name:
                continue
            if lower.startswith("type:") or lower.startswith("severity:") or lower.startswith("crops affected:"):
                continue
            current_lines.append(line)

    sections[current_section] = " ".join(current_lines)

    # Build NL paragraphs
    paragraphs = []

    # Intro + symptoms paragraph
    severity_text = f"a {'highly ' if severity == 'high' else ''}severe" if severity else "a"
    intro = f"{disease_name} is {severity_text} {dtype} disease affecting {crop}."
    symptoms = sections.get("symptoms", "").strip()
    if symptoms:
        intro += f" {symptoms}"
    paragraphs.append(intro)

    # Visual identification paragraph
    visual = sections.get("visual", "").strip()
    if visual:
        paragraphs.append(f"To identify this disease visually, look for {visual[0].lower()}{visual[1:]}")

    # Spread paragraph
    spreads = sections.get("spreads", "").strip()
    if spreads:
        paragraphs.append(f"This disease spreads through {spreads[0].lower()}{spreads[1:]}" if not spreads[0].isupper() or len(spreads.split()) > 3 else f"This disease spreads through {spreads[0].lower()}{spreads[1:]}")

    # Prevention paragraph (for prevention chunks)
    prevention = sections.get("prevention", "").strip()
    if prevention:
        paragraphs.append(prevention)

    # Fallback: if we couldn't parse sections well, keep cleaned original
    result = "\n\n".join(p for p in paragraphs if p.strip())
    if len(result) < 50:
        # Parsing failed — just clean the original
        result = doc
        # Remove label lines
        for label in ["Type:", "Severity:", "Crops affected:", "Symptoms:", "Visual identification:", "How it spreads:"]:
            result = result.replace(label, "")
        result = re.sub(r'\n{3,}', '\n\n', result).strip()

    return result


def _rewrite_treatment_parent(doc: str, meta: dict) -> str:
    """Rewrite a treatment parent chunk from structured to NL."""
    disease_name = meta.get("disease_name", "")
    crop = meta.get("crop", "")
    difficulty = meta.get("difficulty", "")
    is_organic = meta.get("is_organic", "false")

    doc = _fix_encoding(doc)
    doc = _json_array_to_text(doc)

    # Parse sections
    sections = {}
    current_section = "intro"
    current_lines = []

    for line in doc.split("\n"):
        line = line.strip()
        if not line:
            continue
        lower = line.lower()

        if lower.startswith("description:"):
            sections[current_section] = " ".join(current_lines)
            current_section = "description"
            remainder = line.split(":", 1)[1].strip()
            current_lines = [remainder] if remainder else []
        elif lower.startswith("materials needed:"):
            sections[current_section] = " ".join(current_lines)
            current_section = "materials"
            remainder = line.split(":", 1)[1].strip()
            current_lines = [remainder] if remainder else []
        elif lower.startswith("local availability:"):
            sections[current_section] = " ".join(current_lines)
            current_section = "availability"
            remainder = line.split(":", 1)[1].strip()
            current_lines = [remainder] if remainder else []
        elif lower.startswith("when to apply:"):
            sections[current_section] = " ".join(current_lines)
            current_section = "when"
            remainder = line.split(":", 1)[1].strip()
            current_lines = [remainder] if remainder else []
        elif lower.startswith("safety notes:"):
            sections[current_section] = " ".join(current_lines)
            current_section = "safety"
            remainder = line.split(":", 1)[1].strip()
            current_lines = [remainder] if remainder else []
        else:
            # Skip header metadata lines
            if lower.startswith("treatment:") or lower.startswith("for:") or \
               lower.startswith("difficulty:") or lower.startswith("organic:") or \
               lower.startswith("effectiveness:"):
                # Extract treatment name from first Treatment: line
                if lower.startswith("treatment:") and "treatment_name" not in sections:
                    sections["treatment_name"] = line.split(":", 1)[1].strip()
                elif lower.startswith("effectiveness:"):
                    sections["effectiveness"] = line.split(":", 1)[1].strip()
                continue
            current_lines.append(line)

    sections[current_section] = " ".join(current_lines)

    treatment_name = sections.get("treatment_name", "this treatment")
    effectiveness = sections.get("effectiveness", "")
    description = sections.get("description", "").strip()
    materials = sections.get("materials", "").strip()
    availability = sections.get("availability", "").strip()
    when = sections.get("when", "").strip()
    safety = sections.get("safety", "").strip()

    # Build NL
    paragraphs = []

    organic_text = "organic" if is_organic == "true" else ""
    diff_text = f"{difficulty}" if difficulty else ""
    eff_text = f" with {effectiveness} effectiveness" if effectiveness else ""
    method_desc = ", ".join(filter(None, [diff_text, organic_text]))
    method_desc = f"This is {'an' if method_desc and method_desc[0] in 'aeiou' else 'a'} {method_desc} method{eff_text}." if method_desc else ""

    intro = f"To treat {disease_name} in {crop}, use {treatment_name.lower()}. {method_desc}"
    if description:
        intro += f" {description}"
    paragraphs.append(intro.strip())

    # Materials + availability + timing + safety
    details_parts = []
    if materials:
        details_parts.append(f"You will need {materials}.")
    if availability:
        details_parts.append(availability)
    if when:
        details_parts.append(f"Apply {when[0].lower()}{when[1:]}." if not when.endswith(".") else f"Apply {when[0].lower()}{when[1:]}")
    if safety:
        details_parts.append(f"Important: {safety}" if not safety.startswith("Important") else safety)

    if details_parts:
        paragraphs.append(" ".join(details_parts))

    result = "\n\n".join(p for p in paragraphs if p.strip())
    if len(result) < 50:
        result = doc
    return result


def _rewrite_disease_child(doc: str, meta: dict) -> str:
    """Rewrite a disease child chunk — fix truncation and make natural."""
    doc = _fix_encoding(doc)
    disease_name = meta.get("disease_name", "")
    crop = meta.get("crop", "")
    topic_id = meta.get("topic_id", "")

    # If truncated (ends abruptly mid-word/sentence), rebuild from content
    if not doc.endswith((".", "?", "!")):
        # It's truncated — rebuild as natural farmer questions
        is_prevention = "prevention" in topic_id
        if is_prevention:
            return (
                f"How do I prevent {disease_name.lower()} in my {crop} field? "
                f"What steps can I take to protect my {crop} crop from {disease_name.lower()}? "
                f"What are the best prevention methods for {disease_name.lower()} in Casamance?"
            )
        else:
            # Keep what we have but complete it
            # Trim to last complete sentence
            sentences = re.split(r'(?<=[.!?])\s+', doc)
            complete = [s for s in sentences if s.endswith((".", "?", "!"))]
            if complete:
                base = " ".join(complete)
                return f"{base} What disease is this and how do I treat it?"
            else:
                return (
                    f"My {crop} plant looks sick with signs of {disease_name.lower()}. "
                    f"What disease is this and how do I treat it?"
                )

    return doc


def _rewrite_treatment_child(doc: str, meta: dict) -> str:
    """Rewrite a treatment child chunk — fix truncation and make natural."""
    doc = _fix_encoding(doc)
    disease_name = meta.get("disease_name", "")
    crop = meta.get("crop", "")

    if not doc.endswith((".", "?", "!")):
        return (
            f"How do I treat {disease_name.lower()} in my {crop}? "
            f"What treatment options are available for {disease_name.lower()}? "
            f"Is there an organic way to control {disease_name.lower()} in {crop}? "
            f"What materials do I need to treat {disease_name.lower()}?"
        )

    return doc


def _rewrite_practice_parent(doc: str, meta: dict) -> str:
    """Fix farming practice parent — mostly encoding fixes."""
    return _fix_encoding(_json_array_to_text(doc))


def _rewrite_practice_child(doc: str, meta: dict) -> str:
    """Fix farming practice child — mostly encoding, ensure not truncated."""
    doc = _fix_encoding(doc)
    if not doc.endswith((".", "?", "!")):
        topic = meta.get("topic", "").replace("_", " ")
        crop = meta.get("crop", "")
        return (
            f"How do I handle {topic} for {crop} in Casamance? "
            f"What are the best practices for {topic} when growing {crop}? "
            f"When and how should I do {topic} for my {crop} crop?"
        )
    return doc


def _rewrite_regional_parent(doc: str, meta: dict) -> str:
    """Fix regional context — mostly encoding."""
    return _fix_encoding(doc)


def _rewrite_regional_child(doc: str, meta: dict) -> str:
    """Fix regional context child — encoding + truncation."""
    doc = _fix_encoding(doc)
    if not doc.endswith((".", "?", "!")):
        topic = meta.get("topic", "").replace("_", " ")
        return f"What is the {topic} in Casamance? Tell me about agriculture and climate in the Casamance region of Senegal."
    return doc


REWRITERS = {
    "disease_knowledge": {
        "parent": _rewrite_disease_parent,
        "child": _rewrite_disease_child,
    },
    "treatment_guides": {
        "parent": _rewrite_treatment_parent,
        "child": _rewrite_treatment_child,
    },
    "farming_practices": {
        "parent": _rewrite_practice_parent,
        "child": _rewrite_practice_child,
    },
    "regional_context": {
        "parent": _rewrite_regional_parent,
        "child": _rewrite_regional_child,
    },
}


def main():
    print("Loading embedding model...")
    ef = SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)

    client = chromadb.PersistentClient(path=CHROMA_PATH)

    total_updated = 0

    for col_name in ["disease_knowledge", "treatment_guides", "farming_practices", "regional_context"]:
        collection = client.get_collection(col_name, embedding_function=ef)
        results = collection.get(include=["metadatas", "documents"])

        ids = results["ids"]
        metadatas = results["metadatas"]
        documents = results["documents"]

        update_ids = []
        update_docs = []

        rewriters = REWRITERS[col_name]

        for i, doc_id in enumerate(ids):
            meta = metadatas[i]
            doc = documents[i]
            chunk_type = meta.get("chunk_type", "parent")

            rewriter = rewriters.get(chunk_type)
            if not rewriter:
                continue

            new_doc = rewriter(doc, meta)

            if new_doc != doc:
                update_ids.append(doc_id)
                update_docs.append(new_doc)
                print(f"  [{col_name}] {doc_id}: {new_doc[:80]}...")

        if update_ids:
            # Batch update in groups of 10
            for batch_start in range(0, len(update_ids), 10):
                batch_ids = update_ids[batch_start:batch_start + 10]
                batch_docs = update_docs[batch_start:batch_start + 10]
                collection.update(ids=batch_ids, documents=batch_docs)

            print(f"\n  {col_name}: updated {len(update_ids)} / {len(ids)} chunks")
            total_updated += len(update_ids)
        else:
            print(f"\n  {col_name}: no changes needed (0 / {len(ids)})")

    print(f"\n=== DONE: {total_updated} chunks updated across all collections ===")


if __name__ == "__main__":
    main()
