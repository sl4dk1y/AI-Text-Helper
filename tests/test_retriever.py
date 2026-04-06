import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.retriever import LexicalRetriever


def test_retriever():
    """Тестирование лексического ретривера"""
    
    print("=" * 60)
    print("ТЕСТИРОВАНИЕ ЛЕКСИЧЕСКОГО РЕТРИВЕРА (BM25)")
    print("=" * 60)
    
    retriever = LexicalRetriever("data/knowledge_base.csv")
    
    test_queries = [
        "нагода",
        "пашел",
        "малако",
        "севодня",
        "нормальное слово"
    ]
    
    for query in test_queries:
        print(f"\nЗапрос: '{query}'")
        results = retriever.search(query, top_k=1)
        
        if results:
            entry, score = results[0]
            print(f"  → Найдено: '{entry['error']}' → '{entry['correction']}'")
            print(f"  → Score: {score:.2f}")
        else:
            print("  → Ничего не найдено")


if __name__ == "__main__":
    test_retriever()