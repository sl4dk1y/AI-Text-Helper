import sys
import os
import json
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.retriever import LexicalRetriever


def load_qrels(filepath: str):
    """Загрузка данных для оценки из JSON"""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['queries'], data['qrels']


def precision_at_k(results, qrels, k=1):
    """
    Вычисление Precision@k.
    
    Precision@k = (количество релевантных документов в top-k) / k
    """
    if not results:
        return 0.0
    
    top_k = results[:k]
    relevant = 0
    for doc, score in top_k:
        doc_id = doc.get('error', '')
        for qrel in qrels:
            if qrel['doc_id'] == doc_id and qrel['relevance'] >= 1:
                relevant += 1
                break
    
    return relevant / k


def recall_at_k(results, qrels, total_relevant, k=5):
    """
    Вычисление Recall@k.
    
    Recall@k = (количество найденных релевантных документов) / (всего релевантных документов)
    """
    if total_relevant == 0:
        return 0.0
    
    top_k = results[:k]
    found_relevant = 0
    for doc, score in top_k:
        doc_id = doc.get('error', '')
        for qrel in qrels:
            if qrel['doc_id'] == doc_id and qrel['relevance'] >= 1:
                found_relevant += 1
                break
    
    return found_relevant / total_relevant


def mrr_at_k(results, k=5):
    """
    Вычисление MRR@k (Mean Reciprocal Rank).
    
    MRR = 1 / (позиция первого релевантного документа)
    """
    for i, (doc, score) in enumerate(results[:k]):
        if score > 0:
            return 1.0 / (i + 1)
    return 0.0


def evaluate_retriever():
    """Основная функция оценки качества ретривера"""
    
    print("=" * 60)
    print("ОЦЕНКА КАЧЕСТВА РЕТРИВЕРА")
    print("=" * 60)
    
    # Загружаем данные
    queries, qrels = load_qrels("data/qrels.json")
    
    # Инициализируем ретривер
    retriever = LexicalRetriever("data/knowledge_base.csv")
    
    # Результаты
    precisions = []
    recalls = []
    mrrs = []
    
    # Детальные результаты по каждому запросу
    detailed_results = []
    
    for query in queries:
        query_text = query['text']
        query_id = query['id']
        
        # Получаем результаты поиска
        results = retriever.search(query_text, top_k=5)
        
        # Фильтруем qrels для этого запроса
        query_qrels = [q for q in qrels if q['query_id'] == query_id]
        total_relevant = sum(1 for q in query_qrels if q['relevance'] >= 1)
        
        # Вычисляем метрики
        p = precision_at_k(results, query_qrels, k=1)
        r = recall_at_k(results, query_qrels, total_relevant, k=5)
        m = mrr_at_k(results, k=5)
        
        precisions.append(p)
        recalls.append(r)
        mrrs.append(m)
        
        detailed_results.append({
            "query_id": query_id,
            "query_text": query_text,
            "precision_at_1": p,
            "recall_at_5": r,
            "mrr_at_5": m,
            "num_results": len(results)
        })
        
        print(f"\nЗапрос: '{query_text}'")
        print(f"  Precision@1: {p:.2f}")
        print(f"  Recall@5: {r:.2f}")
        print(f"  MRR@5: {m:.2f}")
        if results:
            print(f"  Найдено: {len(results)} результатов")
            for doc, score in results[:3]:
                print(f"    → {doc['error']} -> {doc['correction']} (score: {score:.2f})")
    
    # Средние значения
    avg_precision = sum(precisions) / len(precisions) if precisions else 0
    avg_recall = sum(recalls) / len(recalls) if recalls else 0
    avg_mrr = sum(mrrs) / len(mrrs) if mrrs else 0
    
    print("\n" + "=" * 60)
    print("ИТОГОВЫЕ МЕТРИКИ")
    print("=" * 60)
    print(f"Средний Precision@1: {avg_precision:.2f}")
    print(f"Средний Recall@5: {avg_recall:.2f}")
    print(f"Средний MRR@5: {avg_mrr:.2f}")
    
    # Сохраняем результаты
    results_summary = {
        "timestamp": datetime.now().isoformat(),
        "total_queries": len(queries),
        "avg_precision_at_1": avg_precision,
        "avg_recall_at_5": avg_recall,
        "avg_mrr_at_5": avg_mrr,
        "detailed_results": detailed_results
    }
    
    with open("data/evaluation_results.json", "w", encoding="utf-8") as f:
        json.dump(results_summary, f, ensure_ascii=False, indent=2)
    
    print("\nРезультаты сохранены в: data/evaluation_results.json")
    
    return results_summary


if __name__ == "__main__":
    evaluate_retriever()