import time
from typing import List, Tuple
from ..models.tools import (
    SearchRequest, SearchResponse, SearchResult,
    GetCorrectionRequest, GetCorrectionResponse
)
from ..services.retriever import LexicalRetriever

# Глобальный экземпляр ретривера
_retriever = None


def get_retriever() -> LexicalRetriever:
    """Получение экземпляра ретривера (синглтон)"""
    global _retriever
    if _retriever is None:
        _retriever = LexicalRetriever("data/knowledge_base.csv")
    return _retriever


def search(request: SearchRequest) -> SearchResponse:
    """
    Инструмент поиска в базе знаний.
    
    Тип: Инструмент чтения
    Риски: R5 (ложные срабатывания)
    Политики: P4 (порог уверенности)
    HitL: ❌
    """
    start_time = time.time()
    
    retriever = get_retriever()
    results = retriever.search(
        query=request.query,
        top_k=request.top_k,
        min_score=request.min_score
    )
    
    processing_time_ms = int((time.time() - start_time) * 1000)
    
    search_results = []
    for entry, score in results:
        search_results.append(SearchResult(
            error=entry["error"],
            correction=entry["correction"],
            score=score,
            context=entry.get("context")
        ))
    
    return SearchResponse(
        results=search_results,
        total_found=len(search_results),
        processing_time_ms=processing_time_ms
    )


def get_correction(request: GetCorrectionRequest) -> GetCorrectionResponse:
    """
    Инструмент получения исправления для слова.
    
    Тип: Инструмент чтения
    Риски: R5 (ложные срабатывания)
    Политики: P4 (порог уверенности)
    HitL: ❌
    """
    start_time = time.time()
    
    retriever = get_retriever()
    correction = retriever.get_correction(request.text)
    
    # Если найдено, получаем также score
    score = None
    if correction:
        results = retriever.search(request.text, top_k=1, min_score=0.0)
        if results:
            _, score = results[0]
    
    return GetCorrectionResponse(
        original=request.text,
        correction=correction,
        found=correction is not None,
        score=score
    )