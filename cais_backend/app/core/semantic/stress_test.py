# app/core/semantic/stress_test.py - Stress test for SemanticEngine
# Production-ready test script to validate 10K-25K+ concurrent request handling,
# measure throughput, latency distribution, and auto-healing telemetry.

import os
import sys
import json
import time
import random
import logging
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Tuple
from collections import defaultdict

# Add parent directory to path to import engine
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.core.semantic.engine import SemanticEngine

# ------------------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------------------
LOG_LEVEL = logging.INFO
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("StressTest")

# Sample texts for language detection and translation
TEXTS = {
    "en": "The building must comply with all construction standards and regulations.",
    "es": "El edificio debe cumplir con todas las normas y regulaciones de construcción.",
    "fr": "Le bâtiment doit être conforme à toutes les normes et réglementations de construction.",
    "de": "Das Gebäude muss allen Bauvorschriften und -normen entsprechen.",
    "it": "L'edificio deve conformarsi a tutte le norme e regolamenti edilizi.",
    "pt": "O edifício deve cumprir todas as normas e regulamentos de construção.",
}

TERMS = ["building", "wall", "beam", "column", "foundation", "roof", "compliance", "inspection", "permit"]

LANGUAGES = list(TEXTS.keys())

# ------------------------------------------------------------------------------
# Worker function
# ------------------------------------------------------------------------------
def worker(engine: SemanticEngine) -> Tuple[str, float, bool]:
    """
    Simulate a random user request: either language detection or translation.
    Returns (operation_type, latency_ms, is_fallback_used).
    """
    start = time.perf_counter()
    operation = random.choice(["detect", "translate"])
    try:
        if operation == "detect":
            # Pick a random text and detect its language
            lang = random.choice(LANGUAGES)
            text = TEXTS[lang]
            detected, _ = engine.detect_language(text)
            is_fallback = detected != lang  # heuristic: if detected differs, maybe fallback? not perfect
        else:
            # Translation: pick a random term, source and target languages
            source_lang = random.choice(LANGUAGES)
            target_lang = random.choice(LANGUAGES)
            term = random.choice(TERMS)
            # For variety, sometimes try reverse translation
            if random.random() < 0.3:
                # Try translating from non-English to English
                source_lang, target_lang = target_lang, source_lang
            result = engine.translate_term(term, source_lang, target_lang)
            is_fallback = (result is None)  # if None, fallback likely used
        elapsed = (time.perf_counter() - start) * 1000.0  # ms
        return (operation, elapsed, is_fallback)
    except Exception as e:
        elapsed = (time.perf_counter() - start) * 1000.0
        logger.error(f"Worker error: {e}")
        return (operation, elapsed, True)  # treat error as fallback/failure

# ------------------------------------------------------------------------------
# Test runner
# ------------------------------------------------------------------------------
def run_stress_test(
    engine: SemanticEngine,
    num_requests: int,
    concurrency: int,
    description: str = ""
) -> Dict[str, Any]:
    """
    Run stress test with given number of requests and concurrency level.
    Returns statistics dictionary.
    """
    logger.info(f"Starting stress test: {description} with {num_requests} requests, concurrency={concurrency}")

    latencies: List[float] = []
    fallback_count = 0
    failure_count = 0
    operation_counts = defaultdict(int)

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(worker, engine) for _ in range(num_requests)]
        start_time = time.time()
        for future in as_completed(futures):
            op, latency, is_fallback = future.result()
            latencies.append(latency)
            if is_fallback:
                fallback_count += 1
            if latency > 1000:  # consider >1s as failure for this test
                failure_count += 1
            operation_counts[op] += 1

    total_time = time.time() - start_time
    throughput = num_requests / total_time if total_time > 0 else 0

    # Compute statistics
    avg_latency = statistics.mean(latencies) if latencies else 0
    p95 = statistics.quantiles(latencies, n=100)[94] if len(latencies) >= 100 else max(latencies) if latencies else 0
    p99 = statistics.quantiles(latencies, n=100)[98] if len(latencies) >= 100 else max(latencies) if latencies else 0
    max_latency = max(latencies) if latencies else 0
    min_latency = min(latencies) if latencies else 0

    results = {
        "description": description,
        "num_requests": num_requests,
        "concurrency": concurrency,
        "total_time_sec": total_time,
        "throughput_rps": throughput,
        "avg_latency_ms": avg_latency,
        "p95_latency_ms": p95,
        "p99_latency_ms": p99,
        "min_latency_ms": min_latency,
        "max_latency_ms": max_latency,
        "fallback_count": fallback_count,
        "failure_count": failure_count,
        "operation_counts": dict(operation_counts),
    }
    return results

# ------------------------------------------------------------------------------
# Main test execution
# ------------------------------------------------------------------------------
def main():
    # Initialize engine with production config (non-blocking)
    engine = SemanticEngine(
        dict_dir="./semantic_dictionaries",  # adjust if needed
        block_on_missing=False,
        max_block_wait=0.5,
        hydration_threads=8,
    )
    logger.info("SemanticEngine initialized for stress test.")

    # Define test scenarios: (num_requests, concurrency, description)
    scenarios = [
        (10000, 100, "10K requests, 100 concurrency"),
        (15000, 150, "15K requests, 150 concurrency"),
        (20000, 200, "20K requests, 200 concurrency"),
        (25000, 250, "25K requests, 250 concurrency"),
    ]

    all_results = []
    for num, conc, desc in scenarios:
        # We can add a warm-up period between tests? Not necessary.
        result = run_stress_test(engine, num, conc, desc)
        all_results.append(result)

        # Print intermediate results
        logger.info(f"Test complete: {desc}")
        logger.info(f"  Throughput: {result['throughput_rps']:.2f} req/s")
        logger.info(f"  Avg latency: {result['avg_latency_ms']:.2f} ms")
        logger.info(f"  p95: {result['p95_latency_ms']:.2f} ms, p99: {result['p99_latency_ms']:.2f} ms")
        logger.info(f"  Fallback count: {result['fallback_count']} / {num}")
        logger.info("  Operation counts: " + json.dumps(result['operation_counts']))

        # Retrieve engine metrics to check scaling signals
        metrics = engine.get_metrics()
        logger.info("  Engine metrics:")
        logger.info(f"    avg_latency_ms (overall): {metrics['avg_latency_ms']:.2f}")
        logger.info(f"    error_rate: {metrics['error_rate']:.4f}")
        logger.info(f"    recommended_tier: {metrics['recommended_tier']}")
        logger.info(f"    scale_up_required: {metrics['scale_up_required']}")
        logger.info(f"    current_load_level: {metrics['current_load_level']:.2f}")
        logger.info(f"    pool_saturation: {metrics['pool_saturation']}")

    # Final summary
    logger.info("\n" + "="*80)
    logger.info("STRESS TEST SUMMARY")
    for res in all_results:
        logger.info(f"{res['description']}: throughput={res['throughput_rps']:.2f} req/s, avg={res['avg_latency_ms']:.2f}ms, p95={res['p95_latency_ms']:.2f}ms, p99={res['p99_latency_ms']:.2f}ms")
    logger.info("="*80)

    # Clean up
    engine.shutdown()
    logger.info("Stress test completed.")

if __name__ == "__main__":
    main()
