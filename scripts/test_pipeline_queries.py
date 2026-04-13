"""Run real pipeline queries against the live server to test data quality.

Tests new chunks (millet, groundnut practices, new tomato diseases),
rewritten chunks (cassava mosaic NL format), and edge cases.
"""
import json
import time
import sys
import websocket

BASE_URL = "ws://localhost:8002/chat/ws"


def run_query(message: str, timeout: int = 60) -> dict:
    """Send a chat message via WebSocket and collect the full response."""
    result = {
        "question": message,
        "answer": "",
        "sources": [],
        "steps": [],
        "error": None,
        "latency_ms": 0,
    }

    ws = websocket.create_connection(BASE_URL, timeout=timeout)
    start = time.perf_counter()

    # Send the chat message
    ws.send(json.dumps({
        "message": message,
        "conversation_history": [],
        "conversation_summary": "",
    }))

    # Collect events
    while True:
        try:
            raw = ws.recv()
            data = json.loads(raw)
            event_type = data.get("type")

            if event_type == "status":
                result["steps"].append(data.get("step", ""))
            elif event_type == "token":
                result["answer"] += data.get("token", "")
            elif event_type == "sources":
                result["sources"] = data.get("sources", [])
            elif event_type == "done":
                result["answer"] = data.get("final_answer", result["answer"])
                break
            elif event_type == "error":
                result["error"] = data.get("message", "unknown error")
                break
        except websocket.WebSocketTimeoutException:
            result["error"] = "TIMEOUT"
            break
        except Exception as e:
            result["error"] = str(e)
            break

    result["latency_ms"] = round((time.perf_counter() - start) * 1000)
    ws.close()
    return result


def evaluate(result: dict, test_name: str, must_contain: list[str], must_not_contain: list[str] = None, min_sources: int = 0) -> bool:
    """Check if result passes quality criteria."""
    passed = True
    issues = []

    if result["error"]:
        issues.append(f"ERROR: {result['error']}")
        passed = False

    if not result["answer"]:
        issues.append("EMPTY ANSWER")
        passed = False

    answer_lower = result["answer"].lower()

    for term in must_contain:
        if term.lower() not in answer_lower:
            issues.append(f"MISSING: '{term}'")
            passed = False

    if must_not_contain:
        for term in must_not_contain:
            if term.lower() in answer_lower:
                issues.append(f"UNWANTED: '{term}'")
                passed = False

    if len(result["sources"]) < min_sources:
        issues.append(f"SOURCES: got {len(result['sources'])}, need >= {min_sources}")
        passed = False

    if len(result["sources"]) > 5:
        issues.append(f"TOO MANY SOURCES: {len(result['sources'])} (max 5)")
        passed = False

    # Check source format — no structured labels in source content
    for s in result["sources"]:
        content = s.get("content", "")
        if content.startswith("Treatment:") or content.startswith("Type:") or '["' in content:
            issues.append(f"BAD SOURCE FORMAT: starts with structured label or has JSON array")
            passed = False
            break

    status = "PASS" if passed else "FAIL"
    print(f"\n{'='*60}")
    print(f"[{status}] {test_name}")
    print(f"  Question: {result['question']}")
    print(f"  Latency: {result['latency_ms']}ms")
    print(f"  Sources: {len(result['sources'])}")
    for s in result["sources"]:
        print(f"    - {s.get('title', '?')} (score: {s.get('score', '?')})")
    print(f"  Answer preview: {result['answer'][:200]}...")
    if issues:
        print(f"  Issues: {', '.join(issues)}")

    return passed


def main():
    tests = [
        # Test 1: NEW DATA — millet disease (brand new crop + disease)
        {
            "name": "T1: Millet disease (new crop, new data)",
            "message": "What diseases affect millet in Casamance?",
            "must_contain": ["millet"],
            "min_sources": 1,
        },
        # Test 2: NEW DATA — groundnut farming practice (was 0 practices before)
        {
            "name": "T2: Groundnut planting (new practice data)",
            "message": "How do I prepare my field for planting groundnuts?",
            "must_contain": ["groundnut"],
            "min_sources": 1,
        },
        # Test 3: NEW DATA — tomato early blight (new disease)
        {
            "name": "T3: Tomato early blight treatment (new disease+treatment)",
            "message": "My tomato has brown spots with ring patterns on lower leaves. How do I treat it?",
            "must_contain": ["blight"],
            "min_sources": 1,
        },
        # Test 4: REWRITTEN DATA — cassava mosaic (existing, now NL format)
        {
            "name": "T4: Cassava mosaic (rewritten chunks, NL format)",
            "message": "How do I treat cassava mosaic disease?",
            "must_contain": ["cassava", "mosaic"],
            "must_not_contain": ["Type:", "Severity:", 'Materials needed:\n["'],
            "min_sources": 1,
        },
        # Test 5: REWRITTEN DATA — rice disease (was failing before fixes)
        {
            "name": "T5: Rice diseases (regression test — was failing)",
            "message": "What diseases affect rice in Casamance?",
            "must_contain": ["rice"],
            "must_not_contain": ["I don't have information"],
            "min_sources": 1,
        },
        # Test 6: NEW DATA — maize fall armyworm (new pest entry)
        {
            "name": "T6: Maize fall armyworm (new pest data)",
            "message": "How do I protect my maize from fall armyworm?",
            "must_contain": ["armyworm"],
            "min_sources": 1,
        },
        # Test 7: CONVERSATIONAL — no RAG needed
        {
            "name": "T7: Conversational (no RAG, should not search)",
            "message": "Hi, what can you help me with?",
            "must_contain": [],
            "must_not_contain": ["I don't have information"],
            "min_sources": 0,
        },
    ]

    print("=" * 60)
    print("FIELDPACK AI — PIPELINE QUALITY TEST")
    print(f"Server: http://localhost:8002")
    print(f"Tests: {len(tests)}")
    print("=" * 60)

    results = []
    for test in tests:
        result = run_query(test["message"])
        passed = evaluate(
            result,
            test["name"],
            test["must_contain"],
            test.get("must_not_contain"),
            test.get("min_sources", 0),
        )
        results.append(passed)

    # Summary
    passed_count = sum(results)
    total = len(results)
    print(f"\n{'='*60}")
    print(f"RESULTS: {passed_count}/{total} passed")
    if passed_count == total:
        print("ALL TESTS PASSED")
    else:
        print("SOME TESTS FAILED")
        for i, (test, passed) in enumerate(zip(tests, results)):
            if not passed:
                print(f"  FAILED: {test['name']}")
    print("=" * 60)

    sys.exit(0 if passed_count == total else 1)


if __name__ == "__main__":
    main()
