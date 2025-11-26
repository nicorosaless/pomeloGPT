"""
Test fast-path optimization and response quality
"""

import asyncio
import sys
import time
sys.path.append('/Users/testnico/Documents/GitHub/pomeloGPT/backend')

from api.chat import generate_search_queries


async def test_fast_path():
    """Test that fast-path activates when no URLs present"""
    
    print("="*70)
    print("TEST 1: Fast-path (no URLs)")
    print("="*70)
    
    messages = [
        {"role": "user", "content": "cuales son los mejores libros de deep learning?"}
    ]
    
    start = time.time()
    decision = await generate_search_queries(messages)
    elapsed = time.time() - start
    
    print(f"\n✅ Decision: {decision}")
    print(f"⏱️  Time: {elapsed:.2f}s")
    
    if "[Fast Path]" in str(decision) or decision.get("type") == "search":
        print(f"✅ Fast path activated")
        queries = decision.get("queries", [])
        print(f"📝 Generated {len(queries)} queries:")
        for idx, q in enumerate(queries, 1):
            print(f"   {idx}. {q}")
    
    print()


async def test_with_url():
    """Test that normal path is used when URL present"""
    
    print("="*70)
    print("TEST 2: Normal path (URL present)")
    print("="*70)
    
    messages = [
        {"role": "user", "content": "lee esto: https://github.com/openai/gpt-3"},
        {"role": "assistant", "content": "Ok, leyendo..."},
        {"role": "user", "content": "que dice?"}
    ]
    
    start = time.time()
    decision = await generate_search_queries(messages)
    elapsed = time.time() - start
    
    print(f"\n✅ Decision: {decision}")
    print(f"⏱️  Time: {elapsed:.2f}s")
    
    if decision.get("type") == "url":
        print(f"✅ Correctly chose URL path")
    else:
        print(f"⚠️  Expected URL but got: {decision.get('type')}")
    
    print()


async def main():
    print("\n" + "="*70)
    print("TESTING FAST-PATH OPTIMIZATION")
    print("="*70 + "\n")
    
    await test_fast_path()
    await test_with_url()
    
    print("="*70)
    print("TESTS COMPLETED")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(main())
