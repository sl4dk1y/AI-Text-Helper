import re
import csv
from typing import List, Tuple, Optional
from rank_bm25 import BM25Okapi
import nltk
from nltk.stem.snowball import SnowballStemmer

# Скачиваем данные для токенизации (один раз)
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')


class LexicalRetriever:
    """
    Лексический ретривер на основе BM25 с русским стеммингом.
    
    BM25 (Okapi BM25) — это улучшенная версия TF-IDF.
    Она учитывает:
    - Частоту слова в документе (TF)
    - Редкость слова в корпусе (IDF)
    - Нормализует по длине документа
    """
    
    def __init__(self, knowledge_base_path: str = "data/knowledge_base.csv"):
        self.stemmer = SnowballStemmer("russian")
        self.knowledge_base = []
        self.bm25 = None
        self.load_knowledge_base(knowledge_base_path)
    
    def preprocess_text(self, text: str) -> str:
        """
        Предобработка текста: токенизация и стемминг.
        
        Стемминг (приведение к основе) нужен, чтобы слова
        'пашел', 'пошёл' и 'пошли' считались похожими.
        """
        # Приводим к нижнему регистру
        text = text.lower()
        # Токенизация (разбиваем на слова)
        tokens = nltk.word_tokenize(text, language='russian')
        # Удаляем пунктуацию
        tokens = [re.sub(r'[^\w\s]', '', token) for token in tokens]
        tokens = [token for token in tokens if token]
        # Стемминг
        tokens = [self.stemmer.stem(token) for token in tokens]
        return " ".join(tokens)
    
    def load_knowledge_base(self, path: str):
        """Загрузка базы знаний из CSV и инициализация BM25"""
        self.knowledge_base = []
        documents = []
        
        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.knowledge_base.append({
                    "error": row["error"],
                    "correction": row["correction"],
                    "context": row.get("context", "")
                })
                # Для поиска используем текст ошибки + контекст
                doc_text = f"{row['error']} {row.get('context', '')}"
                documents.append(self.preprocess_text(doc_text))
        
        # Инициализируем BM25
        tokenized_docs = [doc.split() for doc in documents]
        self.bm25 = BM25Okapi(tokenized_docs)
        
        print(f"Загружено {len(self.knowledge_base)} записей в базу знаний")
    
    def search(self, query: str, top_k: int = 3, min_score: float = 0.5) -> List[Tuple[dict, float]]:
        """Поиск с минимальным порогом score"""
        if not self.bm25:
            return []
        
        processed_query = self.preprocess_text(query)
        query_tokens = processed_query.split()
        scores = self.bm25.get_scores(query_tokens)
        
        indexed_scores = list(enumerate(scores))
        indexed_scores.sort(key=lambda x: x[1], reverse=True)
        
        results = []
        for idx, score in indexed_scores[:top_k]:
            if score >= min_score:  # ← только результаты выше порога
                results.append((self.knowledge_base[idx], score))
        
        return results
    
    def get_correction(self, text: str) -> Optional[str]:
        """Получение исправления для текста"""
        words = text.lower().split()
        
        for word in words:
            results = self.search(word, top_k=1)
            if results:
                error_entry, score = results[0]
                if score > 0:
                    return error_entry["correction"]
        
        return None