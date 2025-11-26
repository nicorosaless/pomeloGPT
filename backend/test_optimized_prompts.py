"""
Test optimized prompts with Spanish queries
"""

import asyncio
import sys
sys.path.append('/Users/testnico/Documents/GitHub/pomeloGPT/backend')

from api.chat import generate_search_queries


async def test_spanish_query():
    """Test that queries are generated in Spanish when user speaks Spanish"""
    
    print("="*70)
    print("TEST: Spanish query about Deep Learning repositories")
    print("="*70)
    
    messages = [
        {"role": "user", "content": "quiero ser el mejor ingeniero de deep learning, búscame repositorios y/o papers sobre los que aprender"}
    ]
    
    decision = await generate_search_queries(messages)
    
    print(f"\n✅ Decision: {decision}")
    
    if decision.get("type") == "search":
        queries = decision.get("queries", [])
        print(f"\n📝 Generated Queries ({len(queries)}):")
        for idx, query in enumerate(queries, 1):
            print(f"   {idx}. {query}")
        
        # Check if queries are in Spanish
        has_spanish = any(any(word in q.lower() for word in ["repositorio", "aprender", "deep", "learning", "mejor"]) for q in queries)
        print(f"\n✅ Contains relevant Spanish/technical terms: {has_spanish}")
    else:
        print(f"❌ FAIL: Expected search but got: {decision.get('type')}")
    
    print()


async def test_english_query():
    """Test that queries work for English too"""
    
    print("="*70)
    print("TEST: English query about Machine Learning books")
    print("="*70)
    
    messages = [
        {"role": "user", "content": "I want to learn machine learning, find me the best books"}
    ]
    
    decision = await generate_search_queries(messages)
    
    print(f"\n✅ Decision: {decision}")
    
    if decision.get("type") == "search":
        queries = decision.get("queries", [])
        print(f"\n📝 Generated Queries ({len(queries)}):")
        for idx, query in enumerate(queries, 1):
            print(f"   {idx}. {query}")
    
    print()


async def main():
    print("\n" + "="*70)
    print("TESTING OPTIMIZED PROMPTS")
    print("="*70 + "\n")
    
    await test_spanish_query()
    await test_english_query()
    
    print("="*70)
    print("TESTS COMPLETED")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(main())
