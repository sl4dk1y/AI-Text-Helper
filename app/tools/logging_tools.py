import logging
from ..models.tools import LogRequest, LogResponse

logger = logging.getLogger(__name__)


async def log_action(request: LogRequest) -> LogResponse:
    """
    Инструмент логирования действий агента.
    
    Тип: Инструмент записи
    Политики: P3 (логирование)
    HitL: ❌
    """
    log_method = {
        "info": logger.info,
        "warning": logger.warning,
        "error": logger.error,
        "debug": logger.debug
    }.get(request.level.value, logger.info)
    
    log_method(f"Action: {request.action} | Status: {request.status} | Details: {request.details}")
    
    return LogResponse(logged=True)