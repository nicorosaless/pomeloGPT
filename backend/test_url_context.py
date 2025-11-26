"""
Test the new LLM-driven URL context awareness feature
"""

import asyncio
import sys
sys.path.append('/Users/testnico/Documents/GitHub/pomeloGPT/backend')

from api.chat import generate_search_queries


async def test_url_in_context():
    """Test that LLM detects URL in conversation context"""
    
    print("="*70)
    print("TEST 1: URL mentioned in context, follow-up question about it")
    print("="*70)
    
    messages = [
        {"role": "user", "content": "puedes leer este enlace?: https://github.com/nicorosaless?tab=repositories"},
        {"role": "assistant", "content": "Sí, puedo leer ese enlace. Está mostrando los repositorios de nicorosaless en GitHub. ¿Hay algo específico que quieras que haga con la información?"},
        {"role": "user", "content": "dime qué repositorios hay"}
    ]
    
    decision = await generate_search_queries(messages)
    
    print(f"\n✅ Decision: {decision}")
    
    if decision.get("type") == "url":
        print(f"✅ SUCCESS: LLM correctly decided to read URL: {decision.get('url')}")
    else:
        print(f"❌ FAIL: LLM decided to do web search instead of reading URL")
    
    print()


async def test_web_search():
    """Test that LLM chooses web search for general queries"""
    
    print("="*70)
    print("TEST 2: General query without URL context")
    print("="*70)
    
    messages = [
        {"role": "user", "content": "quiero libros de machine learning para empezar"}
    ]
    
    decision = await generate_search_queries(messages)
    
    print(f"\n✅ Decision: {decision}")
    
    if decision.get("type") == "search":
        print(f"✅ SUCCESS: LLM correctly decided to do web search")
        print(f"   Queries: {decision.get('queries')}")
    else:
        print(f"❌ FAIL: LLM decided to read URL instead of web search")
    
    print()


async def test_url_in_current_message():
    """Test that LLM detects URL in current message"""
    
    print("="*70)
    print("TEST 3: URL directly in current message")
    print("="*70)
    
    messages = [
        {"role": "user", "content": "lee esto: https://www.example.com/article"}
    ]
    
    decision = await generate_search_queries(messages)
    
    print(f"\n✅ Decision: {decision}")
    
    if decision.get("type") == "url":
        print(f"✅ SUCCESS: LLM correctly decided to read URL: {decision.get('url')}")
    else:
        print(f"❌ FAIL: LLM decided to do web search instead of reading URL")
    
    print()


async def main():
    print("\n" + "="*70)
    print("TESTING LLM-DRIVEN URL CONTEXT AWARENESS")
    print("="*70 + "\n")
    
    await test_url_in_context()
    await test_web_search()
    await test_url_in_current_message()
    
    print("="*70)
    print("TESTS COMPLETED")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(main())
