import asyncio
import sys
sys.path.append('/Users/testnico/Documents/GitHub/pomeloGPT/backend')

from api.chat import generate_search_queries

async def test_query_generation():
    """Test the new query optimization feature"""
    
    test_queries = [
        "quiero empezar a leer libros de machine learning",
        "¿cuál es el precio del iPhone 16?",
        "best restaurants in Madrid",
        "últimas noticias de la champions league"
    ]
    
    print("Testing Query Optimization\n" + "="*60)
    
    for user_query in test_queries:
        print(f"\n📝 User Query: {user_query}")
        optimized = await generate_search_queries(user_query)
        print(f"🔍 Optimized Queries ({len(optimized)}):")
        for idx, opt_query in enumerate(optimized, 1):
            print(f"   {idx}. {opt_query}")
        print("-" * 60)

if __name__ == "__main__":
    asyncio.run(test_query_generation())
