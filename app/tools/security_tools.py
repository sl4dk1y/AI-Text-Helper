import re
from ..models.tools import (
    ValidationRequest, ValidationResponse,
    SuspiciousCheckRequest, SuspiciousCheckResponse
)


SUSPICIOUS_PATTERNS = [
    (r"игнорируй\s*(все|предыдущие|инструкции)", "prompt_injection"),
    (r"ignore\s*(all|previous|instructions)", "prompt_injection"),
    (r"теперь\s*ты", "role_change"),
    (r"now\s*you\s*are", "role_change"),
    (r"забудь\s*(все|предыдущие)", "memory_attack"),
    (r"forget\s*(all|previous)", "memory_attack"),
    (r"системный\s*промпт", "prompt_extraction"),
    (r"system\s*prompt", "prompt_extraction"),
]


def validate_input(request: ValidationRequest) -> ValidationResponse:
    """Инструмент валидации входных данных"""
    text = request.text
    max_length = request.max_length
    
    if len(text) > max_length:
        return ValidationResponse(
            is_valid=False,
            error_message=f"Текст превышает максимальную длину {max_length} символов",
            sanitized_text=text[:max_length]
        )
    
    sanitized = re.sub(r'[^\w\s\.,!?\-–—()"\'«»]', '', text)
    
    return ValidationResponse(
        is_valid=True,
        sanitized_text=sanitized
    )


def check_suspicious(request: SuspiciousCheckRequest) -> SuspiciousCheckResponse:
    """Инструмент проверки на подозрительные паттерны"""
    text = request.text.lower()
    matched = []
    
    for pattern, pattern_type in SUSPICIOUS_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            matched.append(pattern_type)
    
    return SuspiciousCheckResponse(
        is_suspicious=len(matched) > 0,
        matched_patterns=matched,
        requires_human_review=len(matched) > 0
    )